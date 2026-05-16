"""memory-pool pass.


功能说明:
- 提供 `memory-pool` pass 的生命周期摘要分析接口。
- 汇总 `dma.alloc/dma.free` 的生命周期区间与 peak 统计。
- 显式 `rewrite=True` 时，将可由 dynamic backing 承接的片上 `dma.alloc`
  改写为 `arch.get_dynamic_memory + dma.view + dma.reshape`；`global` alloc 保留为 summary-only。

API 列表:
- `class MemoryPoolPass(rewrite: bool = False, fold: bool = True, alignment: int = 1024)`
- `MemoryPoolPass.from_options(options: dict[str, str]) -> MemoryPoolPass`
- `MemoryPoolPass.apply(ctx: Context, module: ModuleOp) -> None`
- `MemoryPoolPass.get_summary(func_name: str) -> MemoryPoolSummary`
- `MemoryPoolPass.all_summaries() -> dict[str, MemoryPoolSummary]`
- `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`
- `MemoryPoolSummary.to_text() -> str`
- `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`

使用示例:
- from kernel_gen.passes.memory_pool import MemoryPoolPass
- MemoryPoolPass(rewrite=False).apply(Context(), module)
- MemoryPoolPass(rewrite=True, fold=False, alignment=0).apply(Context(), module)

关联文件:
- spec: spec/pass/lowering/memory_pool.md
- test: test/passes/test_memory_pool.py
- 功能实现: kernel_gen/passes/memory_pool.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import re
import sympy as sp
from xdsl.context import Context
from xdsl.dialects import func, scf
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntegerType,
    ModuleOp,
    i8,
)
from xdsl.ir import Attribute, Block, Operation, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp, DmaReshapeOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolExprAttr,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolMulOp,
    SymbolValueType,
)
from kernel_gen.passes.common import raise_pass_contract_error
from kernel_gen.passes.pass_manager import Pass


LoopOp: TypeAlias = SymbolForOp | scf.ForOp


@dataclass(frozen=True)
class MemoryPoolInterval:
    """单个 allocation 的生命周期摘要。


    功能说明:
    - 记录 alloc 的 bucket、字节大小表达式、词法起止索引与线性 byte offset。

    使用示例:
    - interval = MemoryPoolInterval("alloc1", ("#TSM",), sp.Integer(16), 0, 2, sp.Integer(0))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    name: str
    bucket_key: tuple[str]
    size_bytes_expr: sp.Basic
    begin_index: int
    end_index: int
    offset_bytes_expr: sp.Basic


@dataclass(frozen=True)
class MemoryPoolSummary:
    """memory-pool summary 结构体。


    功能说明:
    - 汇总单个 func 的区间列表、peak 统计与 bucket 数量。

    使用示例:
    - summary = MemoryPoolSummary("main", intervals, peak_bytes_by_bucket, pool_count=1)
    - text = summary.to_text()

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    func_name: str
    intervals: tuple[MemoryPoolInterval, ...]
    peak_bytes_by_bucket: dict[tuple[str], sp.Basic]
    pool_count: int

    def to_text(self) -> str:
        """以稳定文本格式输出 summary。


        功能说明:
        - 用于 expectation 与测试的稳定文本比对。

        使用示例:
        - text = summary.to_text()

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/passes/test_memory_pool.py
        - 功能实现: kernel_gen/passes/memory_pool.py
        """

        lines: list[str] = [f"func_name = {self.func_name}"]
        lines.append("intervals:")
        if self.intervals:
            for interval in self.intervals:
                lines.append(
                    "  - "
                    + f"{interval.name} | size_bytes={_expr_text(interval.size_bytes_expr)}"
                    + f" | begin={interval.begin_index} | end={interval.end_index}"
                    + f" | offset_bytes={_expr_text(interval.offset_bytes_expr)}"
                )
        else:
            lines.append("  - <empty>")

        lines.append("peak_bytes_by_bucket:")
        for bucket in sorted(self.peak_bytes_by_bucket):
            lines.append(
                f"  - {_bucket_text(bucket)} -> {_expr_text(self.peak_bytes_by_bucket[bucket])}"
            )

        lines.append(f"pool_count = {self.pool_count}")
        return "\n".join(lines)


@dataclass(frozen=True)
class _AllocInfo:
    """改写阶段使用的 alloc 生命周期信息。


    功能说明:
    - 记录 alloc、有效 result type、free、dtype、bucket、字节大小表达式与词法区间，供 summary 与 rewrite 共用。

    使用示例:
    - info = _AllocInfo(alloc_op, result_type, free_op, sp.Integer(8), 4, ("#TSM",), 0, 1)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    alloc_op: DmaAllocOp
    result_type: NnMemoryType
    free_op: DmaFreeOp | None
    size_bytes_expr: sp.Basic
    dtype_size: int
    bucket_key: tuple[str]
    begin_index: int
    end_index: int


@dataclass(frozen=True)
class _SymbolMaterial:
    """rewrite 内部 symbol SSA 值。


    功能说明:
    - 绑定 `!symbol.int<"expr">` SSA 值、稳定表达文本与 sympy 表达式。

    使用示例:
    - material = _SymbolMaterial(op.result, "N", sp.Symbol("N"))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    value: SSAValue
    expr_text: str
    expr: sp.Basic


@dataclass(frozen=True)
class _RewriteInfo:
    """单个 alloc 的 rewrite 物化信息。


    功能说明:
    - 保存 shape/numel/offset symbol 值与待插入 metadata op。

    使用示例:
    - rewrite_info = _RewriteInfo(info, shape_values, numel, offset, metadata_ops)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    info: _AllocInfo
    shape_values: tuple[_SymbolMaterial, ...]
    numel: _SymbolMaterial
    offset: _SymbolMaterial
    one: _SymbolMaterial
    metadata_ops: tuple[Operation, ...]


class MemoryPoolPass(Pass):
    """memory-pool pass。


    功能说明:
    - 统计 `dma.alloc/dma.free` 生命周期并生成 summary。
    - `rewrite=True` 时执行 dynamic memory rewrite。
    - `alignment` 以 byte 为单位控制线性切分偏移；`0` 表示关闭对齐。

    使用示例:
    - MemoryPoolPass(rewrite=False).apply(Context(), module)
    - MemoryPoolPass.from_options({"rewrite": "true", "alignment": "0"})

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    name = "memory-pool"

    def __init__(self, rewrite: bool = False, fold: bool = True, alignment: int = 1024) -> None:
        """初始化 memory-pool pass。


        功能说明:
        - 记录是否执行 pool 改写、通用 fold 开关与 byte alignment。
        - `alignment=0` 关闭对齐；负数或非整数直接报公开合同错误。

        使用示例:
        - pass_obj = MemoryPoolPass()
        - pass_obj = MemoryPoolPass(rewrite=True, fold=False, alignment=0)

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/passes/test_memory_pool.py
        - 功能实现: kernel_gen/passes/memory_pool.py
        """

        if not isinstance(rewrite, bool):
            raise_pass_contract_error("MemoryPoolOptionError", "rewrite must be bool")
        if not isinstance(fold, bool):
            raise_pass_contract_error("MemoryPoolOptionError", "fold must be bool")
        if isinstance(alignment, bool) or not isinstance(alignment, int):
            raise_pass_contract_error("MemoryPoolOptionError", "alignment must be non-negative integer")
        if alignment < 0:
            raise_pass_contract_error("MemoryPoolOptionError", "alignment must be non-negative integer")

        super().__init__(fold=fold)
        self.rewrite = rewrite
        self.alignment = alignment
        self._summaries: dict[str, MemoryPoolSummary] = {}

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "MemoryPoolPass":
        """从 registry/ircheck options 构造 MemoryPoolPass。


        功能说明:
        - 支持 `rewrite`、`fold` 与 `alignment` 三个公开 option。
        - 未知 option、非法 bool、负数或非整数 alignment 稳定失败。

        使用示例:
        - pass_obj = MemoryPoolPass.from_options({"rewrite": "true", "alignment": "1024"})

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/passes/test_memory_pool.py
        - 功能实现: kernel_gen/passes/memory_pool.py
        """

        allowed = {"rewrite", "fold", "alignment"}
        unknown = sorted(set(options) - allowed)
        if unknown:
            raise_pass_contract_error("MemoryPoolOptionError", f"unknown option: {unknown[0]}")

        rewrite = _parse_bool_option(options.get("rewrite", "false"), "rewrite")
        fold = _parse_bool_option(options.get("fold", "true"), "fold")
        alignment = _parse_alignment_option(options.get("alignment", "1024"))
        return cls(rewrite=rewrite, fold=fold, alignment=alignment)

    def get_summary(self, func_name: str) -> MemoryPoolSummary:
        """查询单个 func 的 summary。


        功能说明:
        - 按函数名返回 summary；不存在则报错。

        使用示例:
        - summary = pass_obj.get_summary("main")

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/passes/test_memory_pool.py
        - 功能实现: kernel_gen/passes/memory_pool.py
        """

        if func_name not in self._summaries:
            raise_pass_contract_error("MemoryPoolSummaryNotFound", func_name)
        return self._summaries[func_name]

    def all_summaries(self) -> dict[str, MemoryPoolSummary]:
        """返回全部 summary 的拷贝。


        功能说明:
        - 复制返回内部缓存，避免外部修改。

        使用示例:
        - summaries = pass_obj.all_summaries()

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/passes/test_memory_pool.py
        - 功能实现: kernel_gen/passes/memory_pool.py
        """

        return dict(self._summaries)

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 memory-pool 分析与可选改写。


        功能说明:
        - 遍历 module 内每个 `func.func` 并生成 summary。
        - `rewrite=True` 时将可由 dynamic backing 承接的片上 alloc 改写为 dynamic memory view + reshape。
        - `global` alloc 不属于 `arch.get_dynamic_memory` 输入域，仍参与 summary 但不改写。

        使用示例:
        - MemoryPoolPass(rewrite=True, fold=False, alignment=0).apply(Context(), module)

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/passes/test_memory_pool.py
        - 功能实现: kernel_gen/passes/memory_pool.py
        """

        _ = ctx
        if not isinstance(module, ModuleOp):
            raise_pass_contract_error("MemoryPoolInvalidModule", "module must be builtin.module")

        self._summaries = {}
        for op in module.ops:
            if not isinstance(op, func.FuncOp):
                continue
            block, ops, op_index, loop_bounds, op_loop = _collect_straight_line_ops(op)
            alloc_infos = _alloc_infos_from_ops(
                ops,
                op_index,
                loop_bounds,
                op_loop,
                allow_escaping_allocs=not self.rewrite,
            )
            summary = _summarize_func(
                op,
                alloc_infos,
                self.alignment,
                allow_dynamic_alignment=not self.rewrite,
            )
            self._summaries[summary.func_name] = summary
            if self.rewrite:
                _rewrite_func(
                    block,
                    _rewrite_supported_alloc_infos(alloc_infos),
                    op_loop,
                    self.alignment,
                )


_SPACE_TOKENS = {
    "global": "#GM",
    "shared": "#SM",
    "local": "#LM",
    "tsm": "#TSM",
    "tlm": "#TLM",
    "tlm1": "#TLM1",
    "tlm2": "#TLM2",
    "tlm3": "#TLM3",
}
_DYNAMIC_MEMORY_SPACES = {"shared", "local", "tsm", "tlm1", "tlm2", "tlm3"}
_SYMBOL_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ITER_TOKEN_PATTERN = re.compile(r"iter<[^<>]+>")


def _rewrite_supported_alloc_infos(alloc_infos: list[_AllocInfo]) -> list[_AllocInfo]:
    """筛选可由 dynamic backing 承接的 alloc。


    功能说明:
    - `arch.get_dynamic_memory` 不覆盖 `global`，因此 rewrite 阶段只处理
      `_DYNAMIC_MEMORY_SPACES` 内的 alloc；summary 仍保留所有 alloc。

    使用示例:
    - rewrite_infos = _rewrite_supported_alloc_infos(alloc_infos)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    supported: list[_AllocInfo] = []
    for info in alloc_infos:
        result_type = info.result_type
        if result_type.space.space.data in _DYNAMIC_MEMORY_SPACES:
            supported.append(info)
    return supported


def _parse_bool_option(value: str, name: str) -> bool:
    """解析 bool option。


    功能说明:
    - 接受常见 true/false 文本并保持非法输入稳定失败。

    使用示例:
    - enabled = _parse_bool_option("true", "rewrite")

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise_pass_contract_error("MemoryPoolOptionError", f"{name} must be bool")


def _parse_alignment_option(value: str) -> int:
    """解析 alignment option。


    功能说明:
    - 将公开字符串 option 转成非负整数。

    使用示例:
    - alignment = _parse_alignment_option("1024")

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    try:
        alignment = int(value.strip())
    except ValueError:
        raise_pass_contract_error("MemoryPoolOptionError", "alignment must be non-negative integer")
    if alignment < 0:
        raise_pass_contract_error("MemoryPoolOptionError", "alignment must be non-negative integer")
    return alignment


def _expr_text(expr: sp.Basic) -> str:
    """将 sympy 表达式转为稳定文本。


    功能说明:
    - 统一使用 str(expr) 输出。

    使用示例:
    - text = _expr_text(sp.Symbol("A"))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    return str(expr)


def _bucket_text(bucket: tuple[str]) -> str:
    """格式化 bucket 输出。


    功能说明:
    - 用于 summary 文本输出。

    使用示例:
    - text = _bucket_text(("#TSM",))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if len(bucket) == 1:
        return f"({bucket[0]})"
    return f"({', '.join(bucket)})"


def _space_token(mem_type: NnMemoryType) -> str:
    """将 memory space 映射为固定 token。


    功能说明:
    - 将 `global/shared/local/tsm/tlm1/tlm2/tlm3` 统一映射到稳定文本 token。

    使用示例:
    - token = _space_token(mem_type)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    raw = mem_type.space.space.data
    return _SPACE_TOKENS.get(raw, f"#{raw.upper()}")


def _element_size(element_type: Attribute) -> int | None:
    """解析 element_type 的字节大小。


    功能说明:
    - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。

    使用示例:
    - size = _element_size(Float32Type())

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if isinstance(element_type, IntegerType):
        width = int(element_type.width.data)
        if width in {1, 8}:
            return 1
        if width == 16:
            return 2
        if width == 32:
            return 4
        if width == 64:
            return 8
        return None
    if isinstance(element_type, (Float16Type, BFloat16Type)):
        return 2
    if isinstance(element_type, Float32Type):
        return 4
    if isinstance(element_type, Float64Type):
        return 8
    return None


def _dim_expr(dim: Attribute) -> sp.Basic:
    """将 shape/stride 维度属性转换为 sympy 表达式。


    功能说明:
    - 只接受当前公开 memory 合同中的 `SymbolExprAttr` 维度。
    - 静态整数表达式转为 `Integer`；具名符号或复合表达式转为 sympy 表达式。
    - 匿名 `?` 直接失败，不恢复旧 bare attribute 维度入口。

    使用示例:
    - expr = _dim_expr(SymbolExprAttr.from_expr("M"))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if isinstance(dim, SymbolExprAttr):
        text = dim.expr.data
        if not text or text == "?":
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "MemoryPoolUnsupportedShape: anonymous shape is not supported",
            )
        return _sympy_expr_from_text(text)
    raise KernelCodeError(
        ErrorKind.CONTRACT,
        ErrorModule.PASS,
        f"MemoryPoolUnsupportedShape: {dim}",
    )


def _opaque_iter_expr_symbol(expr_text: str) -> sp.Symbol:
    """把含 `iter<...>` 的公开 symbol 表达映射为内部不透明 sympy 符号。


    功能说明:
    - `iter<start,end,step>` 是 SymbolExprAttr 的公开 atom，不属于 Python/sympy 语法。
    - memory-pool 只需要它参与大小与 offset 的动态表达式占位，不能把它退化为 `?` 或从 SSA 名字反推。

    使用示例:
    - expr = _opaque_iter_expr_symbol("min(4, 6 - iter<0,6,4>)")

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    symbol_name = re.sub(r"[^A-Za-z0-9_]+", "_", expr_text).strip("_")
    if not symbol_name:
        symbol_name = "iter_expr"
    return sp.Symbol(f"iter_expr_{symbol_name}", integer=True, positive=True)


def _shape_product(mem_type: NnMemoryType, *, unknown_prefix: str = "anonymous") -> sp.Basic:
    """将 memory shape 转为乘积表达式。


    功能说明:
    - 逐维累乘生成元素数量表达式。
    - 匿名 `?` 使用当前函数内私有 sympy 占位符参与 offset 计算，不写回公开 IR。

    使用示例:
    - size_expr = _shape_product(mem_type)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    result: sp.Basic = sp.Integer(1)
    for axis, dim in enumerate(mem_type.shape.data):
        if isinstance(dim, SymbolExprAttr) and dim.expr.data == "?":
            dim_expr = sp.Symbol(f"{unknown_prefix}_d{axis}", integer=True, positive=True)
        else:
            dim_expr = _dim_expr(dim)
        result = _safe_simplify_expr(result * dim_expr)
    return result


def _effective_alloc_result_type(alloc_op: DmaAllocOp) -> NnMemoryType:
    """返回 memory-pool 计算大小时使用的 alloc 类型。


    功能说明:
    - `dma.alloc` result shape 可合法保留匿名 `?`。
    - memory-pool 不从后续 reshape 反推公开名字，避免把 unknown runtime 维度伪装成稳定符号。

    使用示例:
    - result_type = _effective_alloc_result_type(alloc_op)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    result_type = alloc_op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "MemoryPoolInvalidAlloc: dma.alloc result must be nn.memory",
        )
    return result_type


def _is_contiguous_memory_type(mem_type: NnMemoryType) -> bool:
    """检查 memory-pool 当前支持的默认连续布局。


    功能说明:
    - 在本文件内按 `shape` 推导默认 row-major stride，避免跨文件调用 dma 私有 helper。

    使用示例:
    - _is_contiguous_memory_type(result_type)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if len(mem_type.shape.data) != len(mem_type.stride.data):
        return False
    expected: list[sp.Basic | None] = []
    running: sp.Basic = sp.Integer(1)
    running_unknown = False
    for shape_dim in reversed(mem_type.shape.data):
        expected.insert(0, None if running_unknown else running)
        if isinstance(shape_dim, SymbolExprAttr) and shape_dim.expr.data == "?":
            running_unknown = True
            continue
        if running_unknown:
            continue
        running = _safe_simplify_expr(running * _dim_expr(shape_dim))
    for stride_dim, expected_expr in zip(mem_type.stride.data, expected, strict=True):
        if expected_expr is None:
            if not isinstance(stride_dim, SymbolExprAttr) or stride_dim.expr.data != "?":
                return False
            continue
        try:
            stride_expr = _dim_expr(stride_dim)
        except KernelCodeError:
            return False
        if _safe_simplify_expr(stride_expr - expected_expr) != 0:
            return False
    return True


def _bucket_key(mem_type: NnMemoryType) -> tuple[str]:
    """生成 bucket key。


    功能说明:
    - 规则固定为 `(space,)`；layout 仅用于校验。

    使用示例:
    - key = _bucket_key(mem_type)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if not _is_contiguous_memory_type(mem_type):
        raise KernelCodeError(
            ErrorKind.UNIMPLEMENTED,
            ErrorModule.PASS,
            "MemoryPoolUnsupportedLayout: non-contiguous/custom stride is not supported",
        )
    return (_space_token(mem_type),)


def _parent_block(op: Operation) -> Block | None:
    """安全获取 op 的 parent block。


    功能说明:
    - 在不同版本的 xdsl 上兼容 parent_block API。

    使用示例:
    - block = _parent_block(op)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    return op.parent_block()


def _visit_ops_with_loops(
    ops_list: list[Operation],
    current_loop: LoopOp | None,
    ops: list[Operation],
    loop_bounds: dict[LoopOp, tuple[int, int]],
    op_loop: dict[Operation, LoopOp | None],
    index: int,
) -> int:
    """递归收集 op 并返回最新词法索引。


    功能说明:
    - 作为 `_collect_ops_with_loops(...)` 的当前文件私有递归 helper。
    - 接受 `symbol.for` 与 `scf.for`，其余 region 直接拒绝。

    使用示例:
    - index = _visit_ops_with_loops(list(block.ops), None, ops, loop_bounds, op_loop, 0)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    for op in ops_list:
        ops.append(op)
        op_loop[op] = current_loop
        index += 1
        if not op.regions:
            continue
        if isinstance(op, (SymbolForOp, scf.ForOp)):
            blocks = list(op.body.blocks)
            if len(blocks) != 1:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "MemoryPoolUnsupportedRegionEscape: loop must have single block",
                )
            loop_start = index
            index = _visit_ops_with_loops(
                list(blocks[0].ops),
                op,
                ops,
                loop_bounds,
                op_loop,
                index,
            )
            loop_end = index - 1
            loop_bounds[op] = (loop_start, loop_end)
            continue
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "MemoryPoolUnsupportedRegionEscape: nested regions are not supported",
        )
    return index


def _collect_ops_with_loops(blocks: list[Block]) -> tuple[
    list[Operation],
    dict[LoopOp, tuple[int, int]],
    dict[Operation, LoopOp | None],
]:
    """收集 op 列表并记录 loop 的词法范围。


    功能说明:
    - 按词法顺序收集 op，并为每个 op 记录所在的最内层 loop。

    使用示例:
    - ops, loop_bounds, op_loop = _collect_ops_with_loops(blocks, reject_other_regions=True)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    ops: list[Operation] = []
    loop_bounds: dict[LoopOp, tuple[int, int]] = {}
    op_loop: dict[Operation, LoopOp | None] = {}
    index = 0
    for block in blocks:
        index = _visit_ops_with_loops(
            list(block.ops),
            None,
            ops,
            loop_bounds,
            op_loop,
            index,
        )
    return ops, loop_bounds, op_loop


def _collect_straight_line_ops(
    func_op: func.FuncOp,
) -> tuple[Block, list[Operation], dict[Operation, int], dict[LoopOp, tuple[int, int]], dict[Operation, LoopOp | None]]:
    """收集可分析/改写路径的 op 列表。


    功能说明:
    - 仅允许单 block 函数体。
    - 允许 `symbol.for` 与 `scf.for`，其余 region 直接报错。

    使用示例:
    - block, ops, op_index, loop_bounds, op_loop = _collect_straight_line_ops(func_op)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if len(func_op.body.blocks) != 1:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "MemoryPoolUnsupportedControlFlow: function must have single block",
        )
    block = func_op.body.blocks[0]
    ops, loop_bounds, op_loop = _collect_ops_with_loops([block])
    op_index = {op: idx for idx, op in enumerate(ops)}
    return block, ops, op_index, loop_bounds, op_loop


def _has_escaping_use(
    alloc_op: DmaAllocOp,
    op_index: dict[Operation, int],
    loop_bounds: dict[LoopOp, tuple[int, int]],
    op_loop: dict[Operation, LoopOp | None],
) -> bool:
    """判断 alloc 是否存在 escaping use。


    功能说明:
    - 返回 True 表示 alloc 结果逃逸到所在 loop 词法范围外或被直接 return。
    - alloc 在外层 loop 内、被内层 loop 使用仍由外层 replacement 支配，不属于 escaping use。

    使用示例:
    - if _has_escaping_use(alloc_op, op_index, loop_bounds, op_loop): ...

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    alloc_loop = op_loop.get(alloc_op)
    for use in alloc_op.result.uses:
        user = use.operation
        if isinstance(user, func.ReturnOp):
            return True
        if alloc_loop is None:
            continue
        user_index = op_index.get(user)
        if user_index is None:
            return True
        loop_start, loop_end = loop_bounds[alloc_loop]
        if user_index < loop_start or user_index > loop_end:
            return True
    return False


def _free_indices_for_ops(
    ops: list[Operation],
    op_index: dict[Operation, int],
) -> dict[SSAValue, list[int]]:
    """收集每个 SSA value 对应的 dma.free 索引。


    功能说明:
    - 为 summary 与 rewrite 共用 alloc/free 配对输入，避免两处重复扫描。

    使用示例:
    - free_indices = _free_indices_for_ops(ops, op_index)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    free_indices: dict[SSAValue, list[int]] = {}
    for op in ops:
        if isinstance(op, DmaFreeOp):
            free_indices.setdefault(op.source, []).append(op_index[op])
    return free_indices


def _alloc_infos_from_ops(
    ops: list[Operation],
    op_index: dict[Operation, int],
    loop_bounds: dict[LoopOp, tuple[int, int]],
    op_loop: dict[Operation, LoopOp | None],
    *,
    allow_escaping_allocs: bool = False,
) -> list[_AllocInfo]:
    """从词法 op 列表构造 alloc 生命周期信息。


    功能说明:
    - 统一 summary 与 rewrite 的 alloc/free 配对、dtype、shape 与 loop 生命周期校验。
    - analysis-only 路径可保留 escaping alloc 摘要，rewrite 路径仍稳定拒绝。
    - 无 free alloc 的生命周期按所在 region 结束处理。

    使用示例:
    - alloc_infos = _alloc_infos_from_ops(ops, op_index, loop_bounds, op_loop)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    free_indices = _free_indices_for_ops(ops, op_index)
    alloc_infos: list[_AllocInfo] = []
    last_index = len(ops) - 1
    for op in ops:
        if not isinstance(op, DmaAllocOp):
            continue
        result_type = _effective_alloc_result_type(op)
        if _has_escaping_use(op, op_index, loop_bounds, op_loop) and not allow_escaping_allocs:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "MemoryPoolEscapingAlloc: alloc escapes current region",
            )

        alloc_idx = op_index[op]
        free_list = free_indices.get(op.result, [])
        free_after = [value for value in free_list if value >= alloc_idx]
        free_before = [value for value in free_list if value < alloc_idx]
        if len(free_after) > 1:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "MemoryPoolLifetimeError: multiple dma.free for alloc",
            )
        if free_before and not free_after:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "MemoryPoolLifetimeError: dma.free before alloc",
            )

        free_op: DmaFreeOp | None = None
        free_index: int | None = None
        if free_after:
            free_index = free_after[0]
            candidate = ops[free_index]
            if not isinstance(candidate, DmaFreeOp):
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "MemoryPoolLifetimeError: free index does not point to dma.free",
                )
            free_op = candidate

        alloc_loop = op_loop.get(op)
        if alloc_loop is None:
            if free_op is not None and op_loop.get(free_op) is not None:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "MemoryPoolLifetimeError: dma.free inside loop",
                )
            begin_index = alloc_idx
            end_index = free_index if free_index is not None else last_index
        else:
            if free_op is not None and op_loop.get(free_op) is not alloc_loop:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "MemoryPoolLifetimeError: loop alloc/free mismatch",
                )
            begin_index, loop_end = loop_bounds[alloc_loop]
            end_index = loop_end

        dtype_size = _element_size(result_type.element_type)
        if dtype_size is None:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"MemoryPoolUnsupportedDtype: {result_type.element_type} is not supported",
            )

        alloc_infos.append(
            _AllocInfo(
                op,
                result_type,
                free_op,
                sp.simplify(_shape_product(result_type, unknown_prefix=f"alloc{alloc_idx}") * sp.Integer(dtype_size)),
                dtype_size,
                _bucket_key(result_type),
                begin_index,
                end_index,
            )
        )
    return alloc_infos


def _align_expr(expr: sp.Basic, alignment: int, *, allow_dynamic: bool = False) -> sp.Basic:
    """对 byte offset 表达式执行公开 alignment 规则。


    功能说明:
    - `alignment=0` 直接返回原表达式。
    - 静态整数表达式使用 `align_up`。
    - 动态表达式无法机械物化时默认按 unimplemented 失败；analysis-only summary 可显式允许保留原表达式。

    使用示例:
    - offset = _align_expr(sp.Integer(514), 1024)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if alignment == 0:
        return _safe_simplify_expr(expr)
    if expr == 0:
        return sp.Integer(0)
    if isinstance(expr, sp.Integer) or (expr.is_number and expr.is_integer):
        value = int(expr)
        return sp.Integer(((value + alignment - 1) // alignment) * alignment)
    if allow_dynamic:
        return _safe_simplify_expr(expr)
    raise KernelCodeError(
        ErrorKind.UNIMPLEMENTED,
        ErrorModule.PASS,
        "MemoryPoolUnsupportedAlignment: dynamic aligned offset is not supported",
    )


def _safe_simplify_expr(expr: sp.Basic) -> sp.Basic:
    """对 sympy 表达式执行保守 simplify。

    功能说明:
    - 对复杂 `Min/Max/iter` 符号组合，外部 sympy 可能触发底层异常；此时保留原表达式，
      让 memory-pool 继续按公开 symbol 语义物化 offset。

    使用示例:
    - simplified = _safe_simplify_expr(current + size)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/kernel/test_conv2d_dynamic_symbol_params.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if expr.has(sp.Min, sp.Max) or any(str(symbol).startswith("iter_expr_") for symbol in expr.free_symbols):
        return expr
    try:
        return sp.simplify(expr)
    except Exception:
        return expr


def _peak_bytes(intervals: list[MemoryPoolInterval]) -> sp.Basic:
    """计算 bucket 内的 peak 字节数量。


    功能说明:
    - 按 begin/end 索引构造事件流，取最大并发表达式。

    使用示例:
    - peak = _peak_bytes(intervals)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if not intervals:
        return sp.Integer(0)
    events: dict[int, list[sp.Basic]] = {}
    for interval in intervals:
        events.setdefault(interval.begin_index, []).append(interval.size_bytes_expr)
        events.setdefault(interval.end_index + 1, []).append(-interval.size_bytes_expr)

    current = sp.Integer(0)
    candidates: list[sp.Basic] = []
    for index in sorted(events):
        for delta in events[index]:
            current = sp.simplify(current + delta)
        candidates.append(current)

    return sp.Max(*candidates)


def _alloc_name(value: SSAValue, index: int) -> str:
    """生成 alloc 的稳定名称。


    功能说明:
    - 优先使用 SSAValue 的 name_hint，否则使用 alloc{index}。

    使用示例:
    - name = _alloc_name(op.result, 1)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    name_hint = getattr(value, "name_hint", None)
    if isinstance(name_hint, str) and name_hint:
        return name_hint
    return f"alloc{index}"


def _summarize_func(
    func_op: func.FuncOp,
    alloc_infos: list[_AllocInfo],
    alignment: int,
    *,
    allow_dynamic_alignment: bool = False,
) -> MemoryPoolSummary:
    """生成单个 func 的 summary。


    功能说明:
    - 解析 alloc/free 区间并计算线性 offset 与 peak 统计。
    - analysis-only 路径可允许动态 aligned offset 保留原表达式，避免不改写时阻断 IR 继续 lowering。

    使用示例:
    - summary = _summarize_func(func_op, alloc_infos, 1024)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    current_by_bucket: dict[tuple[str], sp.Basic] = {}
    intervals: list[MemoryPoolInterval] = []
    for alloc_index, info in enumerate(alloc_infos, start=1):
        current = current_by_bucket.get(info.bucket_key, sp.Integer(0))
        offset = _align_expr(current, alignment, allow_dynamic=allow_dynamic_alignment)
        intervals.append(
            MemoryPoolInterval(
                _alloc_name(info.alloc_op.result, alloc_index),
                info.bucket_key,
                info.size_bytes_expr,
                info.begin_index,
                info.end_index,
                offset,
            )
        )
        current_by_bucket[info.bucket_key] = sp.simplify(offset + info.size_bytes_expr)

    intervals_tuple = tuple(intervals)
    peak_bytes_by_bucket: dict[tuple[str], sp.Basic] = {}
    for bucket in {interval.bucket_key for interval in intervals_tuple}:
        peak_bytes_by_bucket[bucket] = _peak_bytes(
            [interval for interval in intervals_tuple if interval.bucket_key == bucket]
        )

    return MemoryPoolSummary(
        func_op.sym_name.data,
        intervals_tuple,
        peak_bytes_by_bucket,
        pool_count=len(peak_bytes_by_bucket),
    )


def _symbol_expr_from_type(value: SSAValue) -> str:
    """从 `!symbol.int<"expr">` SSA type 读取表达文本。


    功能说明:
    - 用于复用函数参数或已有 symbol SSA 值。

    使用示例:
    - expr = _symbol_expr_from_type(block.args[0])

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if not isinstance(value.type, SymbolValueType):
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "MemoryPoolUnsupportedShape: dynamic shape must be !symbol.int",
        )
    return value.type.expr.expr.data


def _material_from_existing(value: SSAValue) -> _SymbolMaterial:
    """把已有 symbol SSA 包装为 `_SymbolMaterial`。


    功能说明:
    - 不新增 IR op，仅记录表达文本与 sympy 表达式。
    - 匿名 `?` 不能作为命名 material 语义使用，调用方需保留 `?` 或拒绝非法输入。

    使用示例:
    - material = _material_from_existing(arg)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    expr_text = _symbol_expr_from_type(value)
    if not expr_text or expr_text == "?":
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "MemoryPoolUnsupportedShape: anonymous shape is not supported",
        )
    return _SymbolMaterial(value, expr_text, _sympy_expr_from_text(expr_text))


def _find_visible_symbol_value_by_expr(
    expr_text: str,
    target_block: Block | None,
    func_block: Block | None,
    anchor: Operation,
) -> SSAValue | None:
    """查找可见的同语义 symbol SSA。


    功能说明:
    - memory-pool metadata 可能插到一组 alloc 的首个 alloc 前。
    - 若后续 alloc 的 dynamic_shape operand 定义在插入点之后，则优先复用函数参数、目标 block 参数或目标 block 中已在插入点前出现的同表达 symbol SSA。

    使用示例:
    - value = _find_visible_symbol_value_by_expr("TILE_M", block, func_block, alloc)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    for block in (func_block, target_block):
        if block is None:
            continue
        for arg in block.args:
            if isinstance(arg.type, SymbolValueType) and arg.type.get_value() == expr_text:
                return arg
    if func_block is not None and target_block is func_block:
        for op in func_block.ops:
            if op is anchor:
                break
            for result in op.results:
                if isinstance(result.type, SymbolValueType) and result.type.get_value() == expr_text:
                    return result
    if func_block is not None and target_block is not None and target_block is not func_block:
        for op in func_block.ops:
            if _op_contains_block(op, target_block):
                break
            for result in op.results:
                if isinstance(result.type, SymbolValueType) and result.type.get_value() == expr_text:
                    return result
    if target_block is not None and target_block is not func_block:
        for op in target_block.ops:
            if op is anchor:
                break
            for result in op.results:
                if isinstance(result.type, SymbolValueType) and result.type.get_value() == expr_text:
                    return result
    return None


def _sympy_expr_from_text(expr_text: str) -> sp.Basic:
    """将公开 symbol 表达文本转成 sympy 表达式。


    功能说明:
    - 显式把标识符绑定为整数符号，避免 `N` 被 sympy 解析为内置函数。

    使用示例:
    - expr = _sympy_expr_from_text("M*N")

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    normalized_text = expr_text.replace(" floordiv ", " // ")
    for iter_token in _ITER_TOKEN_PATTERN.findall(normalized_text):
        normalized_text = normalized_text.replace(iter_token, str(_opaque_iter_expr_symbol(iter_token)))
    names = set(_SYMBOL_NAME_PATTERN.findall(normalized_text))
    local_symbols = {
        name: sp.Symbol(name, integer=True, positive=True)
        for name in names
        if name not in {"min", "max"}
    }
    local_symbols["min"] = sp.Min
    local_symbols["max"] = sp.Max
    return sp.sympify(normalized_text, locals=local_symbols)


def _const_material(value: int) -> tuple[SymbolConstOp, _SymbolMaterial]:
    """构造 symbol.const material。


    功能说明:
    - 创建一个 `symbol.const` op 和对应 `_SymbolMaterial`。

    使用示例:
    - op, material = _const_material(1)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    op = SymbolConstOp(value)
    return op, _SymbolMaterial(op.result, str(value), sp.Integer(value))


def _add_material(lhs: _SymbolMaterial, rhs: _SymbolMaterial) -> tuple[SymbolAddOp, _SymbolMaterial]:
    """构造 symbol.add material。


    功能说明:
    - 按公开 `SymbolAddOp` 物化两个 symbol 值相加。

    使用示例:
    - op, material = _add_material(lhs, rhs)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    expr = sp.simplify(lhs.expr + rhs.expr)
    if lhs.expr_text == "?" or rhs.expr_text == "?":
        expr_text = "?"
    elif expr == lhs.expr:
        expr_text = lhs.expr_text
    elif expr == rhs.expr:
        expr_text = rhs.expr_text
    elif isinstance(expr, sp.Integer) or (expr.is_number and expr.is_integer):
        expr_text = str(int(expr))
    else:
        expr_text = f"{lhs.expr_text}+{rhs.expr_text}"
    op = SymbolAddOp(lhs.value, rhs.value, SymbolValueType.from_expr(expr_text))
    return op, _SymbolMaterial(op.result, expr_text, expr)


def _mul_expr_text(lhs: _SymbolMaterial, rhs: _SymbolMaterial, expr: sp.Basic) -> str:
    """生成乘法结果类型表达文本。


    功能说明:
    - 静态值输出整数；动态加法子表达式加括号，保持 memory_pool expectation 的稳定文本。

    使用示例:
    - text = _mul_expr_text(lhs, rhs, lhs.expr * rhs.expr)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if lhs.expr_text == "?" or rhs.expr_text == "?":
        return "?"
    if isinstance(expr, sp.Integer) or (expr.is_number and expr.is_integer):
        return str(int(expr))
    lhs_text = f"({lhs.expr_text})" if "+" in lhs.expr_text or "-" in lhs.expr_text[1:] else lhs.expr_text
    rhs_text = f"({rhs.expr_text})" if "+" in rhs.expr_text or "-" in rhs.expr_text[1:] else rhs.expr_text
    return f"{lhs_text}*{rhs_text}"


def _mul_material(lhs: _SymbolMaterial, rhs: _SymbolMaterial) -> tuple[SymbolMulOp, _SymbolMaterial]:
    """构造 symbol.mul material。


    功能说明:
    - 按公开 `SymbolMulOp` 物化两个 symbol 值相乘。

    使用示例:
    - op, material = _mul_material(lhs, rhs)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    expr = sp.simplify(lhs.expr * rhs.expr)
    expr_text = _mul_expr_text(lhs, rhs, expr)
    op = SymbolMulOp(lhs.value, rhs.value, SymbolValueType.from_expr(expr_text))
    return op, _SymbolMaterial(op.result, expr_text, expr)


def _floordiv_material(
    lhs: _SymbolMaterial,
    rhs: _SymbolMaterial,
) -> tuple[SymbolFloorDivOp, _SymbolMaterial]:
    """构造 symbol.floordiv material。


    功能说明:
    - 仅在调用方已证明 byte offset 可被 dtype size 整除后使用。

    使用示例:
    - op, material = _floordiv_material(offset_bytes, dtype_size)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if rhs.expr == 0 or sp.simplify(lhs.expr % rhs.expr) != 0:
        raise KernelCodeError(
            ErrorKind.UNIMPLEMENTED,
            ErrorModule.PASS,
            "MemoryPoolTypedViewOutOfBounds: byte offset is not divisible by dtype size",
        )
    expr = sp.simplify(lhs.expr / rhs.expr)
    expr_text = _expr_text(expr)
    op = SymbolFloorDivOp(lhs.value, rhs.value, SymbolValueType.from_expr(expr_text))
    return op, _SymbolMaterial(op.result, expr_text, expr)


def _dynamic_shape_dim_text(dim: SymbolExprAttr) -> str:
    """读取 dynamic shape 维度的公开表达文本。


    功能说明:
    - 只从当前公开 memory 合同中的 `SymbolExprAttr` 读取表达文本。

    使用示例:
    - dim_text = _dynamic_shape_dim_text(SymbolExprAttr.from_expr("M"))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    return dim.expr.data


def _find_dynamic_shape_value(info: _AllocInfo, dim: SymbolExprAttr, index: int) -> SSAValue:
    """从 dma.alloc dynamic_shape 中查找指定维度的 symbol SSA。


    功能说明:
    - 支持 full-rank dynamic_shape 与仅符号维 dynamic_shape 两种公开输入形态。

    使用示例:
    - value = _find_dynamic_shape_value(info, SymbolExprAttr.from_expr("M"), 0)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    dim_text = _dynamic_shape_dim_text(dim)
    dynamic_values = list(info.alloc_op.dynamic_shape)
    if len(dynamic_values) == len(info.result_type.shape.data):
        return dynamic_values[index]
    for value in dynamic_values:
        if _symbol_expr_from_type(value) == dim_text:
            return value
    raise KernelCodeError(
        ErrorKind.CONTRACT,
        ErrorModule.PASS,
        f"MemoryPoolUnsupportedShape: dynamic shape operand not found for {dim_text}",
    )


def _shape_materials(
    info: _AllocInfo,
    target_block: Block | None = None,
    func_block: Block | None = None,
    anchor: Operation | None = None,
) -> tuple[list[Operation], tuple[_SymbolMaterial, ...]]:
    """为 alloc result shape 生成 reshape 所需 symbol 值。


    功能说明:
    - 静态维生成 `symbol.const`。
    - 动态维优先复用可见的同语义 symbol SSA；full-rank `?` operand 只保留为匿名 `?`。

    使用示例:
    - ops, dims = _shape_materials(info, block, func_block, anchor=alloc)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    result_type = info.result_type
    ops: list[Operation] = []
    values: list[_SymbolMaterial] = []
    search_anchor = anchor or info.alloc_op
    for index, dim in enumerate(result_type.shape.data):
        if isinstance(dim, SymbolExprAttr):
            dim_text = dim.expr.data
            if dim_text == "?":
                dynamic_value = _find_dynamic_shape_value(info, dim, index)
                if _symbol_expr_from_type(dynamic_value) != "?":
                    raise KernelCodeError(
                        ErrorKind.CONTRACT,
                        ErrorModule.PASS,
                        "MemoryPoolUnsupportedShape: anonymous result dim requires anonymous dynamic shape operand",
                    )
                unknown_expr = sp.Symbol(
                    f"{_alloc_name(info.alloc_op.result, 0)}_d{index}",
                    integer=True,
                    positive=True,
                )
                values.append(_SymbolMaterial(dynamic_value, "?", unknown_expr))
                continue
            if dim_text.lstrip("-").isdigit():
                op, material = _const_material(int(dim_text))
                ops.append(op)
                values.append(material)
                continue
            dynamic_value = _find_dynamic_shape_value(info, dim, index)
            dynamic_text = _symbol_expr_from_type(dynamic_value)
            visible_value = None
            if target_block is not None and func_block is not None:
                dynamic_value_visible = _symbol_value_visible_from_block(
                    dynamic_value,
                    target_block,
                    func_block,
                ) and _symbol_value_visible_at_anchor(dynamic_value, target_block, func_block, search_anchor)
                if dynamic_text == dim_text and dynamic_value_visible:
                    visible_value = dynamic_value
                elif not isinstance(dynamic_value.owner, Block) or dynamic_value_visible:
                    visible_value = _find_visible_symbol_value_by_expr(
                        dim_text,
                        target_block,
                        func_block,
                        search_anchor,
                    )
            if visible_value is not None:
                values.append(_material_from_existing(visible_value))
            elif dynamic_text == "?":
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "MemoryPoolUnsupportedShape: named result dim requires matching dynamic shape operand",
                )
            else:
                values.append(_material_from_existing(dynamic_value))
            continue
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            f"MemoryPoolUnsupportedShape: {dim}",
        )
    return ops, tuple(values)


def _symbol_value_visible_from_block(value: SSAValue, target_block: Block, func_block: Block) -> bool:
    """判断已有 symbol SSA 是否可在目标 block 中安全使用。


    功能说明:
    - 目标 block 及其词法祖先 block 中定义的 symbol 值可以被目标 block 使用。
    - 子 block 或 sibling block 内定义的 symbol 值不能泄漏到目标 block。

    使用示例:
    - if not _symbol_value_visible_from_block(dim.value, block, func_block): ...

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    owner = value.owner
    if isinstance(owner, Operation):
        owner_block = _parent_block(owner)
        return owner_block is not None and _block_contains_block(owner_block, target_block)
    if isinstance(owner, Block):
        return _block_contains_block(owner, target_block)
    return False


def _block_contains_block(block: Block, target_block: Block) -> bool:
    """判断 block 是否是 target_block 的词法祖先或自身。


    功能说明:
    - 用于 memory-pool 判断父 loop / func block 中的 SSA 是否可被嵌套 block 使用。

    使用示例:
    - if _block_contains_block(func_block, loop_body): ...

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if block is target_block:
        return True
    for op in block.ops:
        if _op_contains_block(op, target_block):
            return True
    return False


def _op_contains_block(op: Operation, target_block: Block) -> bool:
    """判断 op 的 region 树是否包含目标 block。


    功能说明:
    - 用于判断函数体 op 是否是当前嵌套 block 的父级控制流。
    - 父级控制流 op 本身及其后续结果不能作为该嵌套 block 内 metadata 的可见值。

    使用示例:
    - if _op_contains_block(loop_op, loop_body): ...

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    for region in op.regions:
        for block in region.blocks:
            if block is target_block:
                return True
            for child in block.ops:
                if _op_contains_block(child, target_block):
                    return True
    return False


def _op_precedes_target_block_parent(op: Operation, target_block: Block, block: Block) -> bool:
    """判断 op 是否位于通往 target_block 的父控制流 op 之前。


    功能说明:
    - 当 metadata 插入到嵌套 block 时，祖先 block 中只有父控制流 op 之前的 SSA 能支配目标 block。

    使用示例:
    - if _op_precedes_target_block_parent(dim_op, loop_body, outer_block): ...

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    for candidate in block.ops:
        if candidate is op:
            return True
        if _op_contains_block(candidate, target_block):
            return False
    return False


def _op_precedes_anchor(op: Operation, anchor: Operation, block: Block) -> bool:
    """判断 op 是否在同一 block 的 anchor 之前。


    功能说明:
    - memory-pool 会把一组 metadata 统一插入到 anchor 前。
    - 只有 anchor 前已定义的 SSA 才能被这些 metadata 使用。

    使用示例:
    - if _op_precedes_anchor(dim_op, alloc_op, block): ...

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    for candidate in block.ops:
        if candidate is op:
            return True
        if candidate is anchor:
            return False
    return False


def _symbol_value_visible_at_anchor(
    value: SSAValue,
    target_block: Block,
    func_block: Block,
    anchor: Operation,
) -> bool:
    """判断 symbol SSA 在 metadata anchor 前是否可用。


    功能说明:
    - block 参数在对应 block 内始终可用，函数参数也可供嵌套 block 使用。
    - op result 必须已经位于当前 metadata 插入 anchor 之前。
    - 嵌套 block 可使用位于其父控制流 op 之前的函数体 SSA，不能使用父 op 之后的函数体 SSA。

    使用示例:
    - if _symbol_value_visible_at_anchor(value, block, func_block, anchor): ...

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    owner = value.owner
    if isinstance(owner, Block):
        return _block_contains_block(owner, target_block)
    if not isinstance(owner, Operation):
        return False
    owner_block = _parent_block(owner)
    if owner_block is None or not _block_contains_block(owner_block, target_block):
        return False
    if owner_block is target_block:
        return _op_precedes_anchor(owner, anchor, target_block)
    if owner_block is func_block and target_block is func_block:
        return _op_precedes_anchor(owner, anchor, func_block)
    if owner_block is not target_block:
        return _op_precedes_target_block_parent(owner, target_block, owner_block)
    return False


def _shape_materials_for_block(
    info: _AllocInfo,
    target_block: Block,
    func_block: Block,
    anchor: Operation | None = None,
) -> tuple[list[Operation], tuple[_SymbolMaterial, ...]]:
    """为指定 block 生成 shape material 并校验动态维支配关系。


    功能说明:
    - 静态维会在目标 block 内重新生成 const。
    - 动态维只能复用对目标 block 可见的已有 `!symbol.int` SSA；不可见时公开拒绝 rewrite。

    使用示例:
    - ops, dims = _shape_materials_for_block(info, func_block, func_block, anchor=alloc)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    shape_ops, shape_values = _shape_materials(info, target_block, func_block, anchor=anchor)
    generated_ops = set(shape_ops)
    for material in shape_values:
        owner = material.value.owner
        if isinstance(owner, Operation) and owner in generated_ops:
            continue
        if _symbol_value_visible_from_block(material.value, target_block, func_block):
            continue
        raise KernelCodeError(
            ErrorKind.UNIMPLEMENTED,
            ErrorModule.PASS,
            "MemoryPoolUnsupportedControlFlow: dynamic loop alloc size does not dominate later offset",
        )
    return shape_ops, shape_values


def _numel_material(dims: tuple[_SymbolMaterial, ...]) -> tuple[list[Operation], _SymbolMaterial]:
    """生成 flat result 的元素数量 symbol 值。


    功能说明:
    - rank-1 直接复用该维度。
    - 多维场景统一使用 `symbol.mul` 链，避免在不同 metadata block 中出现两套物化策略。

    使用示例:
    - ops, numel = _numel_material(dims)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if not dims:
        op, material = _const_material(1)
        return [op], material
    if len(dims) == 1:
        return [], dims[0]

    ops: list[Operation] = []
    current = dims[0]
    for dim in dims[1:]:
        op, current = _mul_material(current, dim)
        ops.append(op)
    return ops, current


def _offset_material(
    current_bytes: sp.Basic,
    dtype_size: int,
    alignment: int,
    *,
    zero: _SymbolMaterial,
    prior_numels: list[tuple[_SymbolMaterial, int]],
    force_floordiv: bool,
    ratio_materials: dict[int, _SymbolMaterial] | None = None,
) -> tuple[list[Operation], _SymbolMaterial]:
    """生成当前 alloc 的 view offset。


    功能说明:
    - offset 以当前 target dtype 的元素为单位。
    - 只有已证明整除时才物化 `symbol.floordiv`。

    使用示例:
    - ops, offset = _offset_material(current_bytes, 4, 0, zero=zero, prior_numels=[(a, 4)], force_floordiv=False)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    aligned_bytes = _align_expr(current_bytes, alignment)
    if aligned_bytes == 0:
        return [], zero

    if alignment == 0 and prior_numels and not force_floordiv:
        if any(not isinstance(numel.expr, sp.Integer) for numel, _ in prior_numels):
            return _dynamic_offset_from_prior_numels(prior_numels, dtype_size, zero, ratio_materials)

    if sp.simplify(aligned_bytes % dtype_size) != 0:
        raise KernelCodeError(
            ErrorKind.UNIMPLEMENTED,
            ErrorModule.PASS,
            "MemoryPoolTypedViewOutOfBounds: byte offset is not divisible by dtype size",
        )

    byte_op, byte_material = _const_material(int(aligned_bytes))
    dtype_op, dtype_material = _const_material(dtype_size)
    div_op, offset = _floordiv_material(byte_material, dtype_material)
    return [byte_op, dtype_op, div_op], offset


def _dynamic_offset_from_prior_numels(
    prior_numels: list[tuple[_SymbolMaterial, int]],
    dtype_size: int,
    zero: _SymbolMaterial,
    ratio_materials: dict[int, _SymbolMaterial] | None = None,
) -> tuple[list[Operation], _SymbolMaterial]:
    """按 prior numel 与 dtype byte ratio 生成动态 offset。


    功能说明:
    - 仅处理可证明整除的整数 ratio。
    - 多个同 ratio 动态项先求和再乘 ratio，保持 IR 可读且避免 floor 截断。

    使用示例:
    - ops, offset = _dynamic_offset_from_prior_numels([(m, 4), (k, 4)], 2, zero)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    ratio_groups: dict[int, list[_SymbolMaterial]] = {}
    for numel, prior_dtype_size in prior_numels:
        if prior_dtype_size % dtype_size != 0:
            raise KernelCodeError(
                ErrorKind.UNIMPLEMENTED,
                ErrorModule.PASS,
                "MemoryPoolTypedViewOutOfBounds: byte offset is not divisible by dtype size",
            )
        ratio_groups.setdefault(prior_dtype_size // dtype_size, []).append(numel)

    ops: list[Operation] = []
    current: _SymbolMaterial | None = None
    for ratio in sorted(ratio_groups):
        group_values = ratio_groups[ratio]
        group_current = group_values[0]
        for value in group_values[1:]:
            op, group_current = _add_material(group_current, value)
            ops.append(op)
        if ratio != 1:
            if ratio_materials is not None and ratio in ratio_materials:
                ratio_material = ratio_materials[ratio]
                ratio_op = None
            else:
                ratio_op, ratio_material = _const_material(ratio)
            mul_op, group_current = _mul_material(group_current, ratio_material)
            if ratio_op is not None:
                ops.append(ratio_op)
            ops.append(mul_op)
        if current is None:
            if ratio == 1:
                op, current = _add_material(zero, group_current)
                ops.append(op)
            else:
                current = group_current
            continue
        op, current = _add_material(current, group_current)
        ops.append(op)
    if current is None:
        return [], zero
    return ops, current


def _flat_result_type(info: _AllocInfo, numel: _SymbolMaterial) -> NnMemoryType:
    """生成 dma.view 的一维 typed result type。


    功能说明:
    - 保留原 dtype/space，将 shape 收敛为 `[numel]`、stride 固定 `[1]`。

    使用示例:
    - flat_type = _flat_result_type(info, numel)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    result_type = info.result_type
    if isinstance(numel.expr, sp.Integer):
        shape_attr = SymbolExprAttr.from_expr(str(int(numel.expr)))
    else:
        shape_attr = SymbolExprAttr.from_expr(numel.expr_text)
    return NnMemoryType(
        ArrayAttr([shape_attr]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        result_type.element_type,
        result_type.space,
    )


def _metadata_group_block(info: _AllocInfo, op_loop: dict[Operation, LoopOp | None], func_block: Block) -> Block:
    """选择 metadata op 插入所在 block。


    功能说明:
    - `symbol.for` 内 alloc 的 shape/offset metadata 留在 loop 内。
    - `scf.for` 内 alloc 的 loop-invariant metadata 留在函数入口 block。

    使用示例:
    - block = _metadata_group_block(info, op_loop, func_block)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    loop = op_loop.get(info.alloc_op)
    if isinstance(loop, SymbolForOp):
        block = _parent_block(info.alloc_op)
        if block is None:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "MemoryPoolLifetimeError: alloc parent block not found",
            )
        return block
    return func_block


def _metadata_group_anchor(
    group_block: Block,
    group_infos: list[_AllocInfo],
    op_loop: dict[Operation, LoopOp | None],
    func_block: Block,
) -> Operation:
    """选择一组 metadata op 的真实插入 anchor。


    功能说明:
    - 函数体 group 插到该 group 中最早的函数体 alloc 前。
    - loop group 插到该 group 第一个 alloc 前。

    使用示例:
    - anchor = _metadata_group_anchor(block, infos, op_loop, func_block)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    anchor = group_infos[0].alloc_op
    if group_block is not func_block:
        return anchor
    candidate_indices = [
        list(func_block.ops).index(info.alloc_op)
        for info in group_infos
        if _parent_block(info.alloc_op) is func_block
    ]
    if candidate_indices:
        return list(func_block.ops)[min(candidate_indices)]
    loop_ops = [
        op_loop[info.alloc_op]
        for info in group_infos
        if op_loop.get(info.alloc_op) is not None
    ]
    if loop_ops:
        return loop_ops[0]
    return anchor


def _materialize_prior_numel_for_block(
    info: _AllocInfo,
    target_block: Block,
    func_block: Block,
    anchor: Operation,
    cache: dict[_AllocInfo, _SymbolMaterial],
    metadata_ops: list[Operation],
) -> _SymbolMaterial:
    """在目标 block 内重新物化 prior alloc 的 numel。


    功能说明:
    - 用于后续函数体 alloc 的 offset 依赖前面 loop 内动态 alloc 大小的场景。
    - 重新物化可避免函数体 `dma.view.offset` 引用 loop body 内 SSA。

    使用示例:
    - material = _materialize_prior_numel_for_block(info, func_block, func_block, anchor, cache, ops)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if info in cache:
        return cache[info]
    shape_ops, dims = _shape_materials_for_block(info, target_block, func_block, anchor=anchor)
    metadata_ops.extend(shape_ops)
    numel_ops, numel = _numel_material(dims)
    metadata_ops.extend(numel_ops)
    cache[info] = numel
    return numel


def _prior_numels_for_block(
    prior_entries: list[tuple[_AllocInfo, _SymbolMaterial, int]],
    target_block: Block,
    func_block: Block,
    anchor: Operation,
    cache: dict[_AllocInfo, _SymbolMaterial],
    metadata_ops: list[Operation],
) -> list[tuple[_SymbolMaterial, int]]:
    """返回可在目标 block 使用的 prior numel 列表。


    功能说明:
    - 已支配目标 block 的 material 直接复用。
    - 不支配目标 block 的 material 按 prior alloc 重新在目标 block 物化。

    使用示例:
    - prior_numels = _prior_numels_for_block(processed, block, func_block, anchor, cache, metadata_ops)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    result: list[tuple[_SymbolMaterial, int]] = []
    for info, material, dtype_size in prior_entries:
        owner = material.value.owner
        if isinstance(owner, Operation) and owner in metadata_ops:
            result.append((material, dtype_size))
            continue
        if _symbol_value_visible_from_block(material.value, target_block, func_block):
            result.append((material, dtype_size))
            continue
        local_material = _materialize_prior_numel_for_block(
            info,
            target_block,
            func_block,
            anchor,
            cache,
            metadata_ops,
        )
        result.append((local_material, dtype_size))
    return result


def _prepare_rewrite_infos(
    alloc_infos: list[_AllocInfo],
    op_loop: dict[Operation, LoopOp | None],
    func_block: Block,
    alignment: int,
) -> dict[_AllocInfo, _RewriteInfo]:
    """准备所有 alloc 的 rewrite metadata。


    功能说明:
    - 按 `func + space` 线性切分，不做生命周期复用。
    - 每个 alloc 独立选择自身可支配的 metadata anchor，避免后续 alloc 的 shape SSA 被提前引用。
    - 生成 metadata 时只使用公开 symbol dialect op。

    使用示例:
    - rewrite_infos = _prepare_rewrite_infos(alloc_infos, op_loop, block, 0)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    result: dict[_AllocInfo, _RewriteInfo] = {}
    current_by_bucket: dict[tuple[str], sp.Basic] = {}
    processed_numels_by_bucket: dict[tuple[str], list[tuple[_AllocInfo, _SymbolMaterial, int]]] = {}
    for info in alloc_infos:
        group_block = _metadata_group_block(info, op_loop, func_block)
        group_anchor = _metadata_group_anchor(group_block, [info], op_loop, func_block)
        zero_op, zero = _const_material(0)
        one_op, one = _const_material(1)
        metadata_ops: list[Operation] = [zero_op]

        shape_ops, shape_values = _shape_materials(
            info,
            group_block,
            func_block,
            anchor=group_anchor,
        )
        metadata_ops.extend(shape_ops)
        numel_ops, numel = _numel_material(shape_values)
        metadata_ops.extend(numel_ops)
        metadata_ops.append(one_op)

        current = current_by_bucket.get(info.bucket_key, sp.Integer(0))
        if current == 0:
            offset_ops: list[Operation] = []
            offset = zero
        else:
            prior_numels: list[tuple[_SymbolMaterial, int]] = []
            if alignment == 0 and not isinstance(current, sp.Integer):
                rematerialized_prior_numel_by_info: dict[_AllocInfo, _SymbolMaterial] = {}
                prior_numels = _prior_numels_for_block(
                    processed_numels_by_bucket.get(info.bucket_key, []),
                    group_block,
                    func_block,
                    group_anchor,
                    rematerialized_prior_numel_by_info,
                    metadata_ops,
                )
            offset_ops, offset = _offset_material(
                current,
                info.dtype_size,
                alignment,
                zero=zero,
                prior_numels=prior_numels,
                force_floordiv=alignment != 0,
                ratio_materials=None,
            )
        metadata_ops.extend(offset_ops)

        group_block.insert_ops_before(metadata_ops, group_anchor)
        result[info] = _RewriteInfo(
            info,
            shape_values,
            numel,
            offset,
            one,
            tuple(metadata_ops),
        )
        current_by_bucket[info.bucket_key] = _safe_simplify_expr(
            _align_expr(current, alignment) + info.size_bytes_expr
        )
        processed_numels_by_bucket.setdefault(info.bucket_key, []).append((info, numel, info.dtype_size))

    return result


def _dynamic_memory_backing_ops(
    alloc_infos: list[_AllocInfo],
) -> dict[tuple[str], ArchGetDynamicMemoryOp]:
    """为每个 space 构造唯一 arch.get_dynamic_memory op。


    功能说明:
    - 按 `func + memory space` 粒度创建 dynamic memory backing op。

    使用示例:
    - backings = _dynamic_memory_backing_ops(alloc_infos)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    backings: dict[tuple[str], ArchGetDynamicMemoryOp] = {}
    for info in alloc_infos:
        result_type = info.result_type
        space_name = result_type.space.space.data
        key = (space_name,)
        if key not in backings:
            backings[key] = ArchGetDynamicMemoryOp(result_type.space)
    return backings


def _rewrite_func(
    block: Block,
    alloc_infos: list[_AllocInfo],
    op_loop: dict[Operation, LoopOp | None],
    alignment: int,
) -> None:
    """对直线路径执行 dynamic memory rewrite。


    功能说明:
    - 每个 `func + memory space` 在入口生成唯一 `arch.get_dynamic_memory`。
    - 原 alloc 就地替换为 `dma.view + dma.reshape`；旧 free 被删除。

    使用示例:
    - _rewrite_func(block, alloc_infos, op_loop, alignment=0)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/passes/test_memory_pool.py
    - 功能实现: kernel_gen/passes/memory_pool.py
    """

    if not alloc_infos:
        return

    backings = _dynamic_memory_backing_ops(alloc_infos)
    first_op = list(block.ops)[0] if list(block.ops) else None
    backing_ops = list(backings.values())
    if first_op is None:
        block.add_ops(backing_ops)
    else:
        block.insert_ops_before(backing_ops, first_op)

    rewrite_infos = _prepare_rewrite_infos(alloc_infos, op_loop, block, alignment)
    for info in alloc_infos:
        rewrite_info = rewrite_infos[info]
        result_type = info.result_type
        backing = backings[(result_type.space.space.data,)]
        view = DmaViewOp(
            backing.result,
            [rewrite_info.offset.value],
            [rewrite_info.numel.value],
            [rewrite_info.one.value],
            _flat_result_type(info, rewrite_info.numel),
        )
        reshape = DmaReshapeOp(
            view.result,
            [shape.value for shape in rewrite_info.shape_values],
            result_type,
        )

        alloc_block = _parent_block(info.alloc_op)
        if alloc_block is None:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "MemoryPoolLifetimeError: alloc parent block not found",
            )
        alloc_block.insert_ops_before([view, reshape], info.alloc_op)
        info.alloc_op.result.replace_all_uses_with(reshape.result)
        alloc_block.erase_op(info.alloc_op)

        if info.free_op is not None:
            free_block = _parent_block(info.free_op)
            if free_block is None:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "MemoryPoolLifetimeError: free parent block not found",
                )
            free_block.erase_op(info.free_op)


__all__ = [
    "MemoryPoolInterval",
    "MemoryPoolPass",
    "MemoryPoolSummary",
]
