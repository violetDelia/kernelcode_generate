"""memory-pool pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 `memory-pool` pass 的生命周期摘要分析接口。
- 汇总 `dma.alloc/dma.free` 的生命周期区间与 peak 统计。
- 支持直线路径的 pool 改写：`dma.alloc -> i8 byte pool + dma.view`。

使用示例:
- from kernel_gen.passes.lowering.memory_pool import MemoryPoolPass
- module = MemoryPoolPass(rewrite=False).run(module)
- summary = MemoryPoolPass(rewrite=False).get_summary("main")

关联文件:
- spec: spec/pass/lowering/memory_pool.md
- test: test/pass/test_memory_pool.py
- 功能实现: kernel_gen/passes/lowering/memory_pool.py
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    UnrealizedConversionCastOp,
    i8,
    i32,
)
from xdsl.ir import Attribute, Block, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp, DmaViewOp, _is_contiguous
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.passes.pass_manager import Pass


class MemoryPoolError(ValueError):
    """memory-pool pass 的显式错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一收敛 memory-pool pass 的失败短语。

    使用示例:
    - raise MemoryPoolError("MemoryPoolInvalidLifetime: dma.free not found")

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """


@dataclass(frozen=True)
class MemoryPoolInterval:
    """单个 allocation 的生命周期摘要。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 记录 alloc 的 bucket、字节大小表达式、词法起止索引与复用 offset。

    使用示例:
    - interval = MemoryPoolInterval("alloc1", ("#GM",), sp.Symbol("A"), 0, 2, sp.Integer(0))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    name: str
    bucket_key: tuple[str]
    size_bytes_expr: sp.Basic
    begin_index: int
    end_index: int
    offset_bytes_expr: sp.Basic


@dataclass(frozen=True)
class _AllocInfo:
    """改写阶段使用的 alloc 生命周期信息。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 记录 alloc/free 对、bucket、字节大小表达式与词法区间，供直线路径改写使用。

    使用示例:
    - info = _AllocInfo(alloc_op, free_op, sp.Integer(8), ("#GM",), 0, 1)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    alloc_op: DmaAllocOp
    free_op: DmaFreeOp
    size_bytes_expr: sp.Basic
    bucket_key: tuple[str]
    begin_index: int
    end_index: int


@dataclass(frozen=True)
class MemoryPoolSummary:
    """memory-pool summary 结构体。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 汇总单个 func 的区间列表、peak 统计与 bucket 数量。

    使用示例:
    - summary = MemoryPoolSummary("main", intervals, peak_bytes_by_bucket, pool_count=1)
    - print(summary.to_text())

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    func_name: str
    intervals: tuple[MemoryPoolInterval, ...]
    peak_bytes_by_bucket: dict[tuple[str], sp.Basic]
    pool_count: int

    def to_text(self) -> str:
        """以稳定文本格式输出 summary。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 用于 expectation 与测试的稳定文本比对。

        使用示例:
        - text = summary.to_text()

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/pass/test_memory_pool.py
        - 功能实现: kernel_gen/passes/lowering/memory_pool.py
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


class MemoryPoolPass(Pass):
    """memory-pool pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统计 `dma.alloc/dma.free` 生命周期并生成 summary。
    - `rewrite=True` 时对直线路径执行 pool 改写。

    使用示例:
    - summary = MemoryPoolPass(rewrite=False).run(module)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    name = "memory-pool"

    def __init__(self, rewrite: bool = False) -> None:
        self.rewrite = rewrite
        self._summaries: dict[str, MemoryPoolSummary] = {}

    def get_summary(self, func_name: str) -> MemoryPoolSummary:
        """查询单个 func 的 summary。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 按函数名返回 summary；不存在则报错。

        使用示例:
        - summary = pass_obj.get_summary("main")

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/pass/test_memory_pool.py
        - 功能实现: kernel_gen/passes/lowering/memory_pool.py
        """

        if func_name not in self._summaries:
            raise MemoryPoolError(f"MemoryPoolSummaryNotFound: {func_name}")
        return self._summaries[func_name]

    def all_summaries(self) -> dict[str, MemoryPoolSummary]:
        """返回全部 summary 的拷贝。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复制返回内部缓存，避免外部修改。

        使用示例:
        - summaries = pass_obj.all_summaries()

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/pass/test_memory_pool.py
        - 功能实现: kernel_gen/passes/lowering/memory_pool.py
        """

        return dict(self._summaries)

    def run(self, module: ModuleOp) -> ModuleOp:
        """执行 memory-pool 分析。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 遍历 module 内每个 `func.func` 并生成 summary。

        使用示例:
        - module = MemoryPoolPass(rewrite=False).run(module)

        关联文件:
        - spec: spec/pass/lowering/memory_pool.md
        - test: test/pass/test_memory_pool.py
        - 功能实现: kernel_gen/passes/lowering/memory_pool.py
        """

        if not isinstance(module, ModuleOp):
            raise MemoryPoolError("MemoryPoolInvalidModule: module must be builtin.module")

        self._summaries = {}
        for op in module.ops:
            if not isinstance(op, func.FuncOp):
                continue
            summary = _summarize_func(op)
            self._summaries[summary.func_name] = summary
            if self.rewrite:
                _rewrite_func(op)
        return module


_SPACE_TOKENS = {
    "global": "#GM",
    "shared": "#SM",
    "local": "#LM",
    "tsm": "#TSM",
    "tlm": "#TLM",
}


def _expr_text(expr: sp.Basic) -> str:
    """将 sympy 表达式转为稳定文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一使用 str(expr) 输出。

    使用示例:
    - text = _expr_text(sp.Symbol("A"))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    return str(expr)


def _bucket_text(bucket: tuple[str]) -> str:
    """格式化 bucket 输出。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于 summary 文本输出。

    使用示例:
    - text = _bucket_text(("#GM",))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    if len(bucket) == 1:
        return f"({bucket[0]})"
    return f"({', '.join(bucket)})"


def _space_token(mem_type: NnMemoryType) -> str:
    """将 memory space 映射为固定 token。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 `global/shared/local/tsm/tlm` 统一映射到 `#GM/#SM/#LM/#TSM/#TLM`。

    使用示例:
    - token = _space_token(mem_type)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    raw = mem_type.space.space.data
    return _SPACE_TOKENS.get(raw, f"#{raw.upper()}")


def _dtype_string(element_type: Attribute) -> str:
    """生成稳定 dtype 字符串。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前直接复用 str(element_type)。

    使用示例:
    - text = _dtype_string(Float32Type())

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    return str(element_type)


def _element_size(element_type: Attribute) -> int | None:
    """解析 element_type 的字节大小。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。

    使用示例:
    - size = _element_size(Float32Type())

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
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


def _layout_family(mem_type: NnMemoryType) -> str:
    """解析 memory type 的 layout 族。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 第一版仅支持 contiguous layout。

    使用示例:
    - family = _layout_family(mem_type)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    if not _is_contiguous(mem_type):
        raise MemoryPoolError(
            "MemoryPoolUnsupportedLayout: function only supports contiguous dma.alloc in v1"
        )
    return "contiguous"


def _dim_expr(dim: Attribute) -> sp.Basic:
    """将 shape 维度属性转换为 sympy 表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - IntAttr 转为 Integer。
    - StringAttr 转为 Symbol；若为 "?" 则显式失败。

    使用示例:
    - expr = _dim_expr(StringAttr("M"))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    if isinstance(dim, IntAttr):
        return sp.Integer(dim.data)
    if isinstance(dim, StringAttr):
        if not dim.data or dim.data == "?":
            raise MemoryPoolError("MemoryPoolUnsupportedShape: anonymous shape is not supported")
        return sp.Symbol(dim.data)
    raise MemoryPoolError(f"MemoryPoolUnsupportedShape: {dim}")


def _shape_product(mem_type: NnMemoryType) -> sp.Basic:
    """将 memory shape 转为乘积表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐维累乘生成 size 表达式。

    使用示例:
    - size_expr = _shape_product(mem_type)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    result: sp.Basic = sp.Integer(1)
    for dim in mem_type.shape.data:
        result *= _dim_expr(dim)
    return result


def _const_symbol_int(value: int) -> tuple[arith.ConstantOp, UnrealizedConversionCastOp]:
    """构造 `!symbol.int<"value">` 常量的 IR op 对。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先创建 i32 常量，再用 `builtin.unrealized_conversion_cast` 转成 `!symbol.int<"expr">`。
    - 返回两条 op，调用者决定插入到 block 中的位置。

    使用示例:
    - const_i32, cast = _const_symbol_int(1)
    - block.insert_ops_before([const_i32, cast], anchor_op)
    - one = cast.results[0]

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    const = arith.ConstantOp(IntegerAttr(value, i32))
    result_type = SymbolValueType.from_expr(str(value))
    cast = UnrealizedConversionCastOp(operands=[const.result], result_types=[result_type])
    return const, cast


def _symbol_value_expr(expr: str) -> tuple[list[Operation], SSAValue]:
    """构造 `!symbol.int<"expr">` 的 SSA value。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当 expr 可解析为整数时，使用 `_const_symbol_int` 生成常量。
    - 否则使用 `builtin.unrealized_conversion_cast` 生成指定 expr 的 symbol 值。

    使用示例:
    - ops, value = _symbol_value_expr("M*N")
    - block.insert_ops_before(ops, anchor_op)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    try:
        int_value = int(expr)
    except ValueError:
        int_value = None
    if int_value is not None:
        const, cast = _const_symbol_int(int_value)
        return [const, cast], cast.results[0]

    const = arith.ConstantOp(IntegerAttr(0, i32))
    result_type = SymbolValueType.from_expr(expr)
    cast = UnrealizedConversionCastOp(operands=[const.result], result_types=[result_type])
    return [const, cast], cast.results[0]


def _symbol_expr(expr: sp.Basic) -> tuple[list[Operation], SSAValue]:
    """将 sympy 表达式转换为 `!symbol.int<"expr">` SSA value。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一通过 `_symbol_value_expr` 生成可插入的 IR op 列表。

    使用示例:
    - ops, value = _symbol_expr(sp.Symbol("M") * sp.Integer(2))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    return _symbol_value_expr(_expr_text(expr))


def _shape_dim_attr(expr: sp.Basic) -> Attribute:
    """将 size 表达式转换为 shape 维度 attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 整数表达式转为 `IntAttr`。
    - 其他表达式转为 `StringAttr`。

    使用示例:
    - dim_attr = _shape_dim_attr(sp.Symbol("M"))

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    if isinstance(expr, sp.Integer):
        return IntAttr(int(expr))
    return StringAttr(_expr_text(expr))


def _layout_operands(layout: ArrayAttr[Attribute]) -> tuple[list[Operation], list[SSAValue]]:
    """将 layout 属性转换为 `!symbol.int<"expr">` operand 列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - IntAttr 转为常量 `!symbol.int<"n">`。
    - StringAttr 转为符号 `!symbol.int<"expr">`。

    使用示例:
    - ops, values = _layout_operands(result_type.stride)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    ops: list[Operation] = []
    values: list[SSAValue] = []
    for attr in layout.data:
        expr_ops, expr_value = _symbol_expr(_dim_expr(attr))
        ops.extend(expr_ops)
        values.append(expr_value)
    return ops, values


def _bucket_key(mem_type: NnMemoryType) -> tuple[str]:
    """生成 bucket key。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 规则: (space,)；layout 仅用于校验。

    使用示例:
    - key = _bucket_key(mem_type)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    _layout_family(mem_type)
    return (_space_token(mem_type),)


def _collect_ops(block: Block) -> list[Operation]:
    """按词法顺序收集 block 及子 region 内 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先收集当前 block op，再递归收集其子 region 的 op。

    使用示例:
    - ops = _collect_ops(func_op.body.blocks[0])

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    ops: list[Operation] = []
    for op in block.ops:
        ops.append(op)
        for region in op.regions:
            for child in region.blocks:
                ops.extend(_collect_ops(child))
    return ops


def _collect_straight_line_ops(func_op: func.FuncOp) -> tuple[Block, list[Operation]]:
    """收集直线路径的 op 列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅允许单 block 且无嵌套 region。
    - 用于改写阶段的安全约束。

    使用示例:
    - block, ops = _collect_straight_line_ops(func_op)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    if len(func_op.body.blocks) != 1:
        raise MemoryPoolError("MemoryPoolRewriteUnsupported: function must have single block")
    block = func_op.body.blocks[0]
    ops = list(block.ops)
    for op in ops:
        if op.regions:
            raise MemoryPoolError("MemoryPoolRewriteUnsupported: nested regions are not supported")
    return block, ops


def _alloc_name(value: SSAValue, index: int) -> str:
    """生成 alloc 的稳定名称。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 优先使用 SSAValue 的 name_hint，否则使用 alloc{index}。

    使用示例:
    - name = _alloc_name(op.result, 1)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    name_hint = getattr(value, "name_hint", None)
    if isinstance(name_hint, str) and name_hint:
        return name_hint
    return f"alloc{index}"


def _peak_bytes(intervals: list[MemoryPoolInterval]) -> sp.Basic:
    """计算 bucket 内的 peak 字节数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按 begin/end 索引构造事件流，取最大并发表达式。

    使用示例:
    - peak = _peak_bytes(intervals)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
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
            current += delta
        candidates.append(current)

    if len(candidates) == 1:
        return candidates[0]
    return sp.Max(*candidates)


def _summarize_func(func_op: func.FuncOp) -> MemoryPoolSummary:
    """生成单个 func 的 summary。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 解析 alloc/free 区间并计算 peak 统计。

    使用示例:
    - summary = _summarize_func(func_op)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    ops: list[Operation] = []
    for block in func_op.body.blocks:
        ops.extend(_collect_ops(block))

    free_indices: dict[SSAValue, list[int]] = {}
    for index, op in enumerate(ops):
        if isinstance(op, DmaFreeOp):
            free_indices.setdefault(op.source, []).append(index)

    intervals: list[MemoryPoolInterval] = []
    alloc_index = 0
    for index, op in enumerate(ops):
        if not isinstance(op, DmaAllocOp):
            continue
        alloc_index += 1
        result_type = op.result.type
        if not isinstance(result_type, NnMemoryType):
            raise MemoryPoolError("MemoryPoolInvalidAlloc: dma.alloc result must be nn.memory")

        bucket = _bucket_key(result_type)
        size_numel_expr = _shape_product(result_type)
        dtype_size = _element_size(result_type.element_type)
        if dtype_size is None:
            raise MemoryPoolError(
                f"MemoryPoolUnsupportedDtype: {result_type.element_type} is not supported"
            )
        size_bytes_expr = size_numel_expr * sp.Integer(dtype_size)

        free_list = free_indices.get(op.result, [])
        free_after = [value for value in free_list if value >= index]
        if not free_after:
            raise MemoryPoolError("MemoryPoolInvalidLifetime: dma.free not found for alloc")
        if len(free_after) > 1:
            raise MemoryPoolError("MemoryPoolInvalidLifetime: multiple dma.free for alloc")
        free_index = free_after[0]
        if free_index < index:
            raise MemoryPoolError("MemoryPoolInvalidLifetime: dma.free before alloc")

        intervals.append(
            MemoryPoolInterval(
                _alloc_name(op.result, alloc_index),
                bucket,
                size_bytes_expr,
                index,
                free_index,
                sp.Integer(0),
            )
        )

    intervals_tuple = tuple(intervals)
    peak_bytes_by_bucket: dict[tuple[str], sp.Basic] = {}
    for bucket in {interval.bucket_key for interval in intervals}:
        bucket_intervals = [interval for interval in intervals if interval.bucket_key == bucket]
        peak_bytes_by_bucket[bucket] = _peak_bytes(bucket_intervals)

    return MemoryPoolSummary(
        func_op.sym_name.data,
        intervals_tuple,
        peak_bytes_by_bucket,
        pool_count=len(peak_bytes_by_bucket),
    )


def _rewrite_func(func_op: func.FuncOp) -> None:
    """对直线路径执行 pool 改写。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅支持单 block、无嵌套 region 的直线路径。
    - 仅改写同 bucket、相同 size 表达式且生命周期不重叠的 alloc/free。

    使用示例:
    - _rewrite_func(func_op)

    关联文件:
    - spec: spec/pass/lowering/memory_pool.md
    - test: test/pass/test_memory_pool.py
    - 功能实现: kernel_gen/passes/lowering/memory_pool.py
    """

    block, ops = _collect_straight_line_ops(func_op)
    if not ops:
        return

    free_indices: dict[SSAValue, list[int]] = {}
    for index, op in enumerate(ops):
        if isinstance(op, DmaFreeOp):
            free_indices.setdefault(op.source, []).append(index)

    alloc_infos: list[_AllocInfo] = []
    for index, op in enumerate(ops):
        if not isinstance(op, DmaAllocOp):
            continue
        result_type = op.result.type
        if not isinstance(result_type, NnMemoryType):
            raise MemoryPoolError("MemoryPoolInvalidAlloc: dma.alloc result must be nn.memory")
        free_list = free_indices.get(op.result, [])
        free_after = [value for value in free_list if value >= index]
        if not free_after:
            raise MemoryPoolError("MemoryPoolInvalidLifetime: dma.free not found for alloc")
        if len(free_after) > 1:
            raise MemoryPoolError("MemoryPoolInvalidLifetime: multiple dma.free for alloc")
        free_index = free_after[0]
        if free_index < index:
            raise MemoryPoolError("MemoryPoolInvalidLifetime: dma.free before alloc")
        free_op = ops[free_index]
        if not isinstance(free_op, DmaFreeOp):
            raise MemoryPoolError("MemoryPoolInvalidLifetime: dma.free op mismatch")

        dtype_size = _element_size(result_type.element_type)
        if dtype_size is None:
            raise MemoryPoolError(
                f"MemoryPoolUnsupportedDtype: {result_type.element_type} is not supported"
            )
        size_bytes_expr = _shape_product(result_type) * sp.Integer(dtype_size)

        alloc_infos.append(
            _AllocInfo(
                op,
                free_op,
                size_bytes_expr,
                _bucket_key(result_type),
                index,
                free_index,
            )
        )

    if not alloc_infos:
        return

    ref_bucket = alloc_infos[0].bucket_key
    ref_size = alloc_infos[0].size_bytes_expr
    for info in alloc_infos:
        if info.bucket_key != ref_bucket:
            raise MemoryPoolError("MemoryPoolRewriteUnsupported: multiple buckets are not supported")
        if info.size_bytes_expr != ref_size:
            raise MemoryPoolError("MemoryPoolRewriteUnsupported: size mismatch")

    ordered = sorted(alloc_infos, key=lambda item: item.begin_index)
    for prev, curr in zip(ordered, ordered[1:]):
        if curr.begin_index <= prev.end_index:
            raise MemoryPoolError("MemoryPoolRewriteUnsupported: overlapping lifetimes are not supported")

    first_type = ordered[0].alloc_op.result.type
    assert isinstance(first_type, NnMemoryType)
    pool_shape_attr = _shape_dim_attr(ref_size)
    pool_type = NnMemoryType(
        ArrayAttr([pool_shape_attr]),
        ArrayAttr([IntAttr(1)]),
        i8,
        first_type.space,
    )

    pool_shape_ops, pool_shape_value = _symbol_expr(ref_size)
    zero_ops, zero_value = _symbol_value_expr("0")
    pool_alloc = DmaAllocOp([pool_shape_value], pool_type)

    anchor_op = ops[0]
    block.insert_ops_before([*pool_shape_ops, *zero_ops, pool_alloc], anchor_op)

    for info in ordered:
        result_type = info.alloc_op.result.type
        assert isinstance(result_type, NnMemoryType)
        stride_ops, stride_values = _layout_operands(result_type.stride)
        rank = len(result_type.shape.data)
        view_op = DmaViewOp(
            pool_alloc.result,
            [zero_value] * rank,
            list(info.alloc_op.dynamic_shape),
            stride_values,
            result_type,
        )
        block.insert_ops_before([*stride_ops, view_op], info.alloc_op)
        info.alloc_op.result.replace_by(view_op.result)
        block.erase_op(info.alloc_op)
        block.erase_op(info.free_op)

    pool_free = DmaFreeOp(pool_alloc.result)
    terminator = list(block.ops)[-1]
    if isinstance(terminator, func.ReturnOp):
        block.insert_ops_before([pool_free], terminator)
    else:
        block.add_ops([pool_free])


__all__ = [
    "MemoryPoolError",
    "MemoryPoolInterval",
    "MemoryPoolPass",
    "MemoryPoolSummary",
]
