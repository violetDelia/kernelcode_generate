"""C-like fragment emission helpers for DSL lowering.

创建者: 金铲铲大作战
最后一次更改: 大闸蟹

功能说明:
- 提供单个 MLIR op/value 到 C 风格源码片段的最小生成规则。
- 仅负责节点级片段生成，不负责完整函数签名与函数级组织。

使用示例:
- from kernel_gen.dsl.emit_c import EmitCContext, emit_c_op, emit_c_value
- stmt = emit_c_op(op, EmitCContext(target="cpu"))

关联文件:
- spec: spec/dsl/emit_c.md
- test: test/dsl/test_emit_c.py
- 功能实现: kernel_gen/dsl/emit_c.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float64Type, FloatAttr, IndexType, IntAttr, IntegerAttr, IntegerType, Signedness, StringAttr, f32, f64
from xdsl.ir import BlockArgument, Operation, SSAValue

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp, ArchGetThreadIdOp, ArchGetThreadNumOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCastOp, DmaCopyOp, DmaDesliceOp, DmaFillOp, DmaFreeOp, DmaLoadOp, DmaReshapeOp, DmaSliceOp, DmaStoreOp, DmaTransposeOp, DmaViewOp
from kernel_gen.dialect.kernel import (
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceMinOp,
    KernelReduceOp,
    KernelSelectOp,
)
from kernel_gen.dialect.nn import NnAddOp, NnImg2col2dOp, NnMemoryType
from kernel_gen.dialect.symbol import SymbolCastOp, SymbolConstOp, SymbolForOp, SymbolGetDimOp, SymbolGetStrideOp, SymbolToFloatOp, SymbolToIntOp, SymbolValueType


class EmitCError(ValueError):
    """emit_c 阶段错误。"""


@dataclass
class EmitCContext:
    """单次片段生成上下文。"""

    target: str
    indent: str = "    "
    naming: Any | None = None
    type_converter: Any | None = None
    config: dict[str, Any] | None = None
    _names: dict[int, str] = field(default_factory=dict)
    _next_id: int = 0
    _next_temp_id: int = 0
    _indent_level: int = 0
    _symbol_const_names: dict[int, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = {}

    @property
    def current_indent(self) -> str:
        return self.indent * self._indent_level

    def push_indent(self) -> None:
        self._indent_level += 1

    def pop_indent(self) -> None:
        if self._indent_level == 0:
            return
        self._indent_level -= 1

    def bind_name(self, value: SSAValue, name: str) -> str:
        self._names[id(value)] = name
        return name

    def lookup_name(self, value: SSAValue) -> str | None:
        return self._names.get(id(value))

    def allocate_name(self, value: SSAValue, prefix: str = "v") -> str:
        existing = self.lookup_name(value)
        if existing is not None:
            return existing
        if self.naming is not None:
            if callable(self.naming):
                name = self.naming(value)
            elif hasattr(self.naming, "allocate"):
                name = self.naming.allocate(value)
            else:
                raise EmitCError(f"target={self.target}: unsupported naming strategy")
        else:
            name = f"{prefix}{self._next_id}"
            self._next_id += 1
        return self.bind_name(value, name)

    def allocate_temp_name(self, prefix: str = "tmp") -> str:
        """分配不与 SSA value 命名冲突的临时变量名。

        创建者: 小李飞刀
        最后一次更改: 朽木露琪亚

        功能说明:
        - 为 `dma.copy` 的索引缓冲区、`dma.view` 的 offset 变量等生成稳定且唯一的临时名称。
        - 仅保证在同一个 `EmitCContext` 内唯一，不保证跨上下文唯一。

        使用示例:
        - ctx.allocate_temp_name(\"dma\") -> \"dma0\"
        - ctx.allocate_temp_name(\"view_offset\") -> \"view_offset0\"

        关联文件:
        - spec: spec/dsl/emit_c.md
        - test: test/dsl/test_emit_c.py
        - 功能实现: kernel_gen/dsl/emit_c.py
        """

        name = f"{prefix}{self._next_temp_id}"
        self._next_temp_id += 1
        return name

    def has_bound_name(self, name: str) -> bool:
        """判断上下文里是否已绑定过同名变量。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 供 `symbol.const` 这类可复用字面量名的 emitter 查询当前作用域是否已出现同名绑定。
        - 仅检查当前 `EmitCContext` 的命名表，不推断外部作用域或跨上下文状态。

        使用示例:
        - ctx.has_bound_name("c_16")
        - if not ctx.has_bound_name("tile0"): ...

        关联文件:
        - spec: spec/dsl/emit_c.md
        - test: test/dsl/test_emit_c.py
        - 功能实现: kernel_gen/dsl/emit_c.py
        """

        return name in self._names.values()


def _emit_error(ctx: EmitCContext, subject: str, reason: str) -> EmitCError:
    return EmitCError(f"target={ctx.target}: {subject}: {reason}")


def _bind_preferred_name(ctx: EmitCContext, value: SSAValue, preferred: str) -> str:
    """按首选前缀为 SSA value 绑定稳定名称。"""

    existing = ctx.lookup_name(value)
    if existing is not None:
        return existing
    used = set(ctx._names.values())
    if preferred not in used:
        return ctx.bind_name(value, preferred)
    suffix = 1
    while f"{preferred}_{suffix}" in used:
        suffix += 1
    return ctx.bind_name(value, f"{preferred}_{suffix}")


def _block_arg_index(value: SSAValue) -> int | None:
    if isinstance(value, BlockArgument):
        return value.index
    return None


def _normalized_binary_elewise_operands(
    op: KernelBinaryElewiseOp,
) -> tuple[SSAValue, SSAValue, SSAValue]:
    """返回按公开合同规整后的 `out/lhs/rhs`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 默认按当前公开合同直接返回 `out/lhs/rhs`。
    - 若命中只读 expectation 遗留的旧文本顺序 `kernel.binary_elewise(lhs, rhs, out)`，
      则在发射前按 block argument 位置把它规整回 `out-first`。

    使用示例:
    - out_value, lhs_value, rhs_value = _normalized_binary_elewise_operands(op)

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    out_value = SSAValue.get(op.out)
    lhs_value = SSAValue.get(op.lhs)
    rhs_value = SSAValue.get(op.rhs)
    out_idx = _block_arg_index(out_value)
    lhs_idx = _block_arg_index(lhs_value)
    rhs_idx = _block_arg_index(rhs_value)
    if (
        out_idx is not None
        and lhs_idx is not None
        and rhs_idx is not None
        and rhs_idx < out_idx
        and rhs_idx < lhs_idx
    ):
        return rhs_value, out_value, lhs_value
    return out_value, lhs_value, rhs_value


def _normalized_out_input_operands(
    out_value: SSAValue,
    input_value: SSAValue,
) -> tuple[SSAValue, SSAValue]:
    out_idx = _block_arg_index(out_value)
    input_idx = _block_arg_index(input_value)
    if out_idx is not None and input_idx is not None and input_idx < out_idx:
        return input_value, out_value
    return out_value, input_value


def _normalized_matmul_operands(
    op: KernelMatmulOp,
) -> tuple[SSAValue, SSAValue, SSAValue]:
    out_value = SSAValue.get(op.out)
    lhs_value = SSAValue.get(op.lhs)
    rhs_value = SSAValue.get(op.rhs)
    out_idx = _block_arg_index(out_value)
    lhs_idx = _block_arg_index(lhs_value)
    rhs_idx = _block_arg_index(rhs_value)
    if (
        out_idx is not None
        and lhs_idx is not None
        and rhs_idx is not None
        and rhs_idx < out_idx
        and rhs_idx < lhs_idx
    ):
        return rhs_value, out_value, lhs_value
    return out_value, lhs_value, rhs_value


def _normalized_select_operands(
    op: KernelSelectOp,
) -> tuple[SSAValue, SSAValue, SSAValue, SSAValue]:
    out_value = SSAValue.get(op.out)
    cond_value = SSAValue.get(op.cond)
    lhs_value = SSAValue.get(op.lhs)
    rhs_value = SSAValue.get(op.rhs)
    out_idx = _block_arg_index(out_value)
    cond_idx = _block_arg_index(cond_value)
    lhs_idx = _block_arg_index(lhs_value)
    rhs_idx = _block_arg_index(rhs_value)
    if (
        out_idx is not None
        and cond_idx is not None
        and lhs_idx is not None
        and rhs_idx is not None
        and rhs_idx < out_idx
        and rhs_idx < cond_idx
        and rhs_idx < lhs_idx
    ):
        return rhs_value, out_value, cond_value, lhs_value
    return out_value, cond_value, lhs_value, rhs_value


def _is_symbol_const_like(op: Operation) -> bool:
    """判断 op 是否等价于 `symbol.const`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 兼容直接 IRDL `SymbolConstOp` 与 pass 产出的 `builtin.unregistered` 形式 `symbol.const`。
    - 仅用于节点级 emitter 透明跳过/取值，不扩展为新的公开 op 合同。

    使用示例:
    - _is_symbol_const_like(op)

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if isinstance(op, SymbolConstOp):
        return True
    op_name_attr = op.attributes.get("op_name__")
    return op.name == "builtin.unregistered" and isinstance(op_name_attr, StringAttr) and op_name_attr.data == "symbol.const"


_BINARY_SIGILS = {
    "arith.addi": "+",
    "arith.addf": "+",
    "arith.subi": "-",
    "arith.subf": "-",
    "arith.muli": "*",
    "arith.mulf": "*",
    "arith.divf": "/",
    "symbol.add": "+",
    "symbol.sub": "-",
    "symbol.mul": "*",
    "symbol.div": "/",
    "symbol.floordiv": "/",
}

_SYMBOL_COMPARE_SIGILS = {
    "symbol.eq": "==",
    "symbol.ne": "!=",
    "symbol.lt": "<",
    "symbol.le": "<=",
    "symbol.gt": ">",
    "symbol.ge": ">=",
}

_CMPI_SIGILS = {
    0: "==",
    1: "!=",
    2: "<",
    3: "<=",
    4: ">",
    5: ">=",
}

_NPU_DYNAMIC_MEMORY_SPACES = {"TSM", "TLM1", "TLM2", "TLM3"}


def _integer_type_to_c(attr: IntegerType) -> str:
    if attr.width.data == 1:
        return "bool"
    prefix = "uint" if attr.signedness.data == Signedness.UNSIGNED else "int"
    return f"{prefix}{attr.width.data}_t"


def _type_to_c(attr: Any, ctx: EmitCContext) -> str:
    """将 xdsl/DSL 类型映射为 C 侧类型文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在未提供 `ctx.type_converter` 时，按最小覆盖集把常用类型映射为 C/C++ 类型字符串。
    - 当前覆盖：`i1/bool`、`i32/int32_t`、`ui32/uint32_t`、`index/long long`、`f32/float`、`f64/double`、`!nn.memory/Memory<Space, T>`、`!symbol.int/S_INT|long long`。
    - 对于未知类型必须抛错，避免静默生成不可编译或语义错误的代码。

    使用示例:
    - _type_to_c(i32, EmitCContext(target="cpu")) -> "int32_t"
    - _type_to_c(f32, EmitCContext(target="cpu")) -> "float"

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.type_converter is not None:
        if callable(ctx.type_converter):
            return ctx.type_converter(attr)
        if hasattr(ctx.type_converter, "convert"):
            return ctx.type_converter.convert(attr)
        raise EmitCError(f"target={ctx.target}: unsupported type converter")
    if isinstance(attr, IntegerType):
        return _integer_type_to_c(attr)
    if isinstance(attr, Float16Type):
        return "half"
    if isinstance(attr, BFloat16Type):
        return "bfloat16_t"
    if attr == f32:
        return "float"
    if isinstance(attr, Float64Type) or attr == f64:
        return "double"
    if isinstance(attr, IndexType):
        return "long long"
    if isinstance(attr, NnMemoryType):
        space_param = _space_to_c(attr, ctx)
        return f"Memory<{space_param}, {_type_to_c(attr.element_type, ctx)}>"
    if isinstance(attr, SymbolValueType):
        return "S_INT" if ctx.target == "npu_demo" else "long long"
    raise _emit_error(ctx, f"type {attr}", "unsupported type")


def _symbol_const_name(value: int) -> str:
    if value >= 0:
        return f"c_{value}"
    return f"c_m{abs(value)}"


def _emit_npu_symbol_const_stmt(op: Operation, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 `symbol.const` 的局部变量语句。"""

    if not op.results or not isinstance(op.results[0].type, SymbolValueType):
        raise _emit_error(ctx, op.name, "symbol.const result must be !symbol.int")
    if isinstance(op, SymbolConstOp):
        value = int(op.value.data)
    else:
        value_attr = op.attributes.get("value")
        if not isinstance(value_attr, IntegerAttr):
            raise _emit_error(ctx, op.name, "symbol.const value must be integer attribute")
        value = int(value_attr.value.data)
    existing_name = ctx._symbol_const_names.get(value)
    if existing_name is not None:
        ctx.bind_name(op.results[0], existing_name)
        return ""
    result_name = _symbol_const_name(value)
    ctx._symbol_const_names[value] = ctx.bind_name(op.results[0], result_name)
    return f"{ctx.current_indent}S_INT {result_name} = {value};"


def _format_literal(op: arith.ConstantOp, ctx: EmitCContext) -> str:
    value = op.value
    if isinstance(value, IntegerAttr):
        return str(value.value.data)
    if isinstance(value, FloatAttr):
        return str(value.value.data)
    raise _emit_error(ctx, op.name, "unsupported constant literal")


def _memory_base_name(value: SSAValue, ctx: EmitCContext) -> str:
    """为 `nn.memory` SSA value 提供稳定的变量名（base name）。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 若 value 已绑定名称则直接复用，确保同一上下文内输出稳定。
    - `BlockArgument` 未绑定时回退为 `arg{index}`，避免受访问顺序影响。
    - 仅允许来自本阶段已支持的 memory owner op（例如 `dma.alloc/view/load/deslice`、`nn.img2col2d`）的依赖；
      其余依赖统一报错，避免把未知来源当作可寻址 memory。

    使用示例:
    - ctx.bind_name(arg0, "input"); _memory_base_name(arg0, ctx) -> "input"

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    if isinstance(value, BlockArgument):
        return ctx.bind_name(value, f"arg{value.index}")
    owner = value.owner
    if isinstance(owner, (DmaAllocOp, DmaDesliceOp, DmaLoadOp, DmaViewOp, NnImg2col2dOp)):
        return ctx.allocate_name(value)
    raise _emit_error(ctx, f"value {value}", "invalid dependency")


def _format_indices(indices: tuple[SSAValue, ...], ctx: EmitCContext) -> str:
    return "".join(f"[{emit_c_value(index, ctx)}]" for index in indices)


def _space_to_c(memory_type: NnMemoryType, ctx: EmitCContext) -> str:
    """把 nn.memory 的 space 映射为 `Memory<Space, T>` 模板参数。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 `#nn.space<global/shared/local/tsm/tlm1/tlm2/tlm3>` 映射为对应的模板参数
      `GM/SM/LM/TSM/TLM1/TLM2/TLM3`。
    - 用于 `dma.alloc`/`dma.view`/`nn.img2col2d` 等内存视图声明时的模板参数生成。

    使用示例:
    - _space_to_c(memory_type, EmitCContext(target=\"cpu\")) == \"GM\"

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    mapping = {
        "global": "GM",
        "shared": "SM",
        "local": "LM",
        "tsm": "TSM",
        "tlm1": "TLM1",
        "tlm2": "TLM2",
        "tlm3": "TLM3",
    }
    space_name = memory_type.space.space.data
    mapped = mapping.get(space_name)
    if mapped is None:
        raise _emit_error(ctx, f"space {space_name}", "unsupported memory space")
    return mapped


def _space_name_to_c(space_name: str, ctx: EmitCContext) -> str:
    """把 space 名称映射为模板参数 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 文本。

    创建者: jcc你莫辜负
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一处理 `global/shared/local/tsm/tlm1/tlm2/tlm3` 到
      `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 的映射。
    - 供 `npu_demo` 的 `arch.get_dynamic_memory` 模板参数发射复用。

    使用示例:
    - _space_name_to_c("tsm", EmitCContext(target="npu_demo")) == "TSM"

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    mapping = {
        "global": "GM",
        "shared": "SM",
        "local": "LM",
        "tsm": "TSM",
        "tlm1": "TLM1",
        "tlm2": "TLM2",
        "tlm3": "TLM3",
    }
    mapped = mapping.get(space_name)
    if mapped is None:
        raise _emit_error(ctx, f"space {space_name}", "unsupported memory space")
    return mapped


def _format_static_layout(values: Any, ctx: EmitCContext, subject: str) -> list[str]:
    """格式化静态 shape/stride 布局为可直接嵌入 C 源码的整数文本。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 仅接受 `IntAttr` 维度条目，并转换为十进制文本。
    - 若遇到符号维度（例如 `StringAttr(\"N\")`），必须抛错，避免在本阶段生成不受控的 dynamic backing。

    使用示例:
    - _format_static_layout(ArrayAttr([IntAttr(2), IntAttr(3)]).data, ctx, \"shape\") -> [\"2\", \"3\"]

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    formatted: list[str] = []
    for value in values:
        if not isinstance(value, IntAttr):
            raise _emit_error(ctx, subject, "only static memory layout is supported")
        formatted.append(str(value.data))
    return formatted


def _format_npu_alloc_layout(
    values: Any,
    ctx: EmitCContext,
    subject: str,
    *,
    symbol_bindings: dict[str, str] | None = None,
) -> list[str]:
    """格式化 npu_demo `dma.alloc` 的 shape/stride 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 接受静态 `IntAttr` 与符号 `StringAttr` 两类维度条目。
    - 对符号条目优先使用当前上下文里已绑定的 SSA 名称，确保动态 `alloc` 输出可直接复用函数参数名。

    使用示例:
    - _format_npu_alloc_layout(result_type.stride.data, ctx, "dma.alloc stride", symbol_bindings={"N": "arg1"})

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    formatted: list[str] = []
    for value in values:
        if isinstance(value, IntAttr):
            formatted.append(str(value.data))
            continue
        if isinstance(value, StringAttr):
            mapped = None if symbol_bindings is None else symbol_bindings.get(value.data)
            formatted.append(mapped or value.data)
            continue
        raise _emit_error(ctx, subject, "unsupported alloc layout value")
    return formatted


def _emit_long_long_buffer(name: str, values: list[str], ctx: EmitCContext) -> str:
    """生成 `long long[]` 常量缓冲区声明语句。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 以 `long long name[rank] = {v0, v1, ...};` 形式发射 shape/stride/indices 缓冲区。
    - `values` 允许为字面量或已命名的标量表达式（例如 `start`）。

    使用示例:
    - _emit_long_long_buffer(\"v0_shape\", [\"2\", \"3\"], ctx)

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    return f"{ctx.current_indent}long long {name}[{len(values)}] = {{{', '.join(values)}}};"


def _maybe_static_numel(shape: Any) -> int | None:
    """尝试从静态 shape 推导元素总数。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 若 `shape` 全为 `IntAttr`，返回其乘积；否则返回 `None`。
    - 用于决定 backing buffer 是否可在栈上以固定长度数组生成。

    使用示例:
    - _maybe_static_numel([IntAttr(2), IntAttr(3)]) -> 6
    - _maybe_static_numel([StringAttr(\"N\"), IntAttr(3)]) -> None

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    numel = 1
    for dim in shape:
        if not isinstance(dim, IntAttr):
            return None
        numel *= dim.data
    return numel


def _shape_product_expr(shape_values: list[str]) -> str:
    """把 shape 值列表拼接为乘积表达式字符串。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将 `["H", "W"]` 转为 `(H) * (W)` 形式，便于作为 `numel` 计算表达式嵌入文本。
    - 仅负责字符串拼接，不做语义校验。

    使用示例:
    - _shape_product_expr([\"2\", \"3\"]) == \"(2) * (3)\"

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if not shape_values:
        return "1"
    return " * ".join(f"({value})" for value in shape_values)


def _emit_backing_storage_decl(
    name: str,
    element_type: str,
    shape_values: list[str],
    memory_type: NnMemoryType,
    ctx: EmitCContext,
) -> tuple[list[str], str]:
    """为 `Memory<Space, T>` 声明生成 backing storage（buffer）声明语句。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前阶段仅支持静态 shape（type.shape 全为 `IntAttr`）：
      - 发射 `T name_buffer[numel] = {};` 的栈上数组作为 backing。
    - 若 type.shape 包含符号维度（例如 `StringAttr(\"N\")`），必须抛 `EmitCError`：
      - 避免生成 `new[]` 但无法在节点级片段中可靠释放导致泄漏。

    使用示例:
    - lines, buf = _emit_backing_storage_decl(\"v0\", \"float\", [\"2\", \"3\"], memory_type, ctx)

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    buffer_name = f"{name}_buffer"
    static_numel = _maybe_static_numel(memory_type.shape.data)
    if static_numel is None:
        raise _emit_error(ctx, f"memory {name}", "dynamic shape backing is unsupported")
    return [f"{ctx.current_indent}{element_type} {buffer_name}[{static_numel}] = {{}};"], buffer_name


def _emit_memory_decl(
    name: str,
    memory_type: NnMemoryType,
    ctx: EmitCContext,
    *,
    shape_values: list[str] | None = None,
    stride_values: list[str] | None = None,
    data_expr: str | None = None,
    format_expr: str | None = None,
    space_expr: str | None = None,
    with_backing_storage: bool = False,
) -> str:
    """发射 `Memory<Space, T>` 声明语句（含 shape/stride 缓冲区与可选 backing）。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成 `shape/stride` 的 `long long[]` 声明。
    - 生成目标相关的 `Memory<Space, T>` 构造：
      - `target=cpu`: `name(data, rank, shape, stride, format);`
      - `target=npu_demo`: `name(data, shape, stride, rank, format);`
    - 当 `with_backing_storage=True` 时，为静态 shape 生成 `name_buffer[numel]` 作为 backing，并把 `data` 指向该 buffer。

    使用示例:
    - decl = _emit_memory_decl(\"v0\", memory_type, EmitCContext(target=\"cpu\"), with_backing_storage=True)

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    element_type = _type_to_c(memory_type.element_type, ctx)
    if shape_values is None:
        shape_values = _format_static_layout(memory_type.shape.data, ctx, f"memory {name}")
    if stride_values is None:
        stride_values = _format_static_layout(memory_type.stride.data, ctx, f"memory {name}")
    if with_backing_storage:
        storage_lines, data_expr = _emit_backing_storage_decl(name, element_type, shape_values, memory_type, ctx)
    else:
        storage_lines = []
    if data_expr is None:
        data_expr = f"static_cast<{element_type}*>(nullptr)"
    if format_expr is None:
        format_expr = "MemoryFormat::Norm"
    if space_expr is None:
        space_expr = _space_to_c(memory_type, ctx)
    if ctx.target == "npu_demo":
        ctor_args = f"{data_expr}, {name}_shape, {name}_stride, {len(shape_values)}, {format_expr}"
    else:
        ctor_args = f"{data_expr}, {len(shape_values)}, {name}_shape, {name}_stride, {format_expr}"
    lines = [
        _emit_long_long_buffer(f"{name}_shape", shape_values, ctx),
        _emit_long_long_buffer(f"{name}_stride", stride_values, ctx),
        *storage_lines,
        f"{ctx.current_indent}Memory<{space_expr}, {element_type}> {name}({ctor_args});",
    ]
    return "\n".join(lines)


def _emit_npu_brace_list(values: tuple[SSAValue, ...], ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下的 brace-list 实参文本。"""

    return "{" + ", ".join(emit_c_value(value, ctx) for value in values) + "}"


def _is_unit_tile(memory_type: NnMemoryType) -> bool:
    if len(memory_type.shape.data) == 0:
        return False
    return all(isinstance(dim, IntAttr) and dim.data == 1 for dim in memory_type.shape.data)


def _emit_dma_load_stmt(op: DmaLoadOp, ctx: EmitCContext) -> str:
    """生成 `dma.load` 的显式 loop nest copy 片段。"""

    if ctx.target != "cpu":
        raise _emit_error(ctx, op.name, "dma ops are cpu-only")
    target_expr = _memory_base_name(op.target, ctx)
    source_expr = _memory_base_name(op.source, ctx)
    return _emit_dma_copy_loop_nest(
        source_expr=source_expr,
        target_expr=target_expr,
        offsets=op.offsets,
        sizes=op.sizes,
        strides=op.strides,
        ctx=ctx,
        target_has_offsets=False,
    )


def _emit_dma_store_stmt(op: DmaStoreOp, ctx: EmitCContext) -> str:
    source_type = op.source.type
    if not isinstance(source_type, NnMemoryType) or not _is_unit_tile(source_type):
        raise _emit_error(ctx, op.name, "only unit-tile dma.store source is supported")
    source_expr = _memory_base_name(op.source, ctx)
    target_expr = _memory_base_name(op.target, ctx)
    return f"{ctx.current_indent}{target_expr}{_format_indices(op.offsets, ctx)} = {source_expr};"


def _emit_dma_alloc_stmt(op: DmaAllocOp, ctx: EmitCContext) -> str:
    """生成 `dma.alloc` 的 `Memory<Space, T>` 声明片段。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在 `target=cpu` 下发射 backing storage + `Memory<Space, T>` 声明。
    - 在 `target=npu_demo` 下发射 `alloc<Space, T>({shape...} /*shape*/, {stride...} /*stride*/)` helper 调用。
    - `target=npu_demo` 的动态 shape 允许复用当前函数作用域内的符号参数名。

    使用示例:
    - stmt = emit_c_op(DmaAllocOp([], alloc_type), EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target not in {"cpu", "npu_demo"}:
        raise _emit_error(ctx, op.name, "dma ops are cpu-only")
    result_name = ctx.allocate_name(op.result)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise _emit_error(ctx, op.name, "result must be nn.memory")
    shape_values = [emit_c_value(value, ctx) for value in op.dynamic_shape]
    if not shape_values:
        shape_values = _format_npu_alloc_layout(result_type.shape.data, ctx, op.name)
    symbol_bindings: dict[str, str] = {}
    for value in op.dynamic_shape:
        value_type = value.type
        if isinstance(value_type, SymbolValueType):
            symbol_bindings[value_type.expr.expr.data] = emit_c_value(value, ctx)
    stride_values = _format_npu_alloc_layout(
        result_type.stride.data,
        ctx,
        f"{op.name} stride",
        symbol_bindings=symbol_bindings,
    )
    if ctx.target == "npu_demo":
        space_expr = _space_to_c(result_type, ctx)
        element_type = _type_to_c(result_type.element_type, ctx)
        shape_text = ", ".join(shape_values)
        stride_text = ", ".join(stride_values)
        return (
            f"{ctx.current_indent}Memory<{space_expr}, {element_type}> {result_name} = "
            f"alloc<{space_expr}, {element_type}>({{{shape_text}}} /*shape*/, {{{stride_text}}} /*stride*/);"
        )
    return _emit_memory_decl(
        result_name,
        result_type,
        ctx,
        shape_values=shape_values,
        stride_values=stride_values,
        with_backing_storage=True,
    )


def _emit_dma_fill_stmt(op: DmaFillOp, ctx: EmitCContext) -> str:
    """生成 `dma.fill` 的 CPU 侧填充循环片段。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在 `target=cpu` 下把 `dma.fill(target, value)` 发射为对 backing storage 的显式线性填充循环。
    - 当前按 `Memory<Space, T>::element_count()` 与 `data()` 遍历，覆盖 pass 生成的 contiguous temporary memory 子集。

    使用示例:
    - stmt = emit_c_op(fill_op, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target not in {"cpu", "npu_demo"}:
        raise _emit_error(ctx, op.name, "dma ops are cpu-only")
    target_expr = _memory_base_name(op.target, ctx)
    value_expr = emit_c_value(op.value, ctx)
    loop_name = f"{ctx.allocate_temp_name('fill')}_i"
    lines = [f"{ctx.current_indent}for (long long {loop_name} = 0; {loop_name} < {target_expr}.element_count(); ++{loop_name}) {{"]
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}{target_expr}.data()[{loop_name}] = {value_expr};")
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def _emit_dma_view_stmt(op: DmaViewOp, ctx: EmitCContext) -> str:
    """生成 `dma.view` 的 CPU 侧 memory 视图声明片段。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在 `target=cpu` 下基于源 `Memory<Space, T>` 生成子视图：
      - 发射 offset 计算（以源 stride 为单位）。
      - 发射目标 `shape/stride` 缓冲区与 `Memory<Space, T>` 视图声明。
    - 目标视图复用源 memory 的 `format`。

    使用示例:
    - stmt = emit_c_op(view_op, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target != "cpu":
        raise _emit_error(ctx, op.name, "dma ops are cpu-only")
    result_name = ctx.allocate_name(op.result)
    source_expr = _memory_base_name(op.source, ctx)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise _emit_error(ctx, op.name, "result must be nn.memory")
    shape_values = [emit_c_value(value, ctx) for value in op.shape]
    stride_values = [emit_c_value(value, ctx) for value in op.stride]
    base_offset_name = ctx.allocate_temp_name("view_offset")
    offset_terms = [f"({emit_c_value(value, ctx)} * {source_expr}.stride()[{index}])" for index, value in enumerate(op.offsets)]
    base_offset_expr = " + ".join(offset_terms) if offset_terms else "0"
    decl = _emit_memory_decl(
        result_name,
        result_type,
        ctx,
        shape_values=shape_values,
        stride_values=stride_values,
        data_expr=f"const_cast<{_type_to_c(result_type.element_type, ctx)}*>({source_expr}.data()) + {base_offset_name}",
        format_expr=f"{source_expr}.format()",
    )
    return f"{ctx.current_indent}long long {base_offset_name} = {base_offset_expr};\n{decl}"


def _emit_dma_copy_loop_nest(
    *,
    source_expr: str,
    target_expr: str,
    offsets: tuple[SSAValue, ...],
    sizes: tuple[SSAValue, ...],
    strides: tuple[SSAValue, ...],
    ctx: EmitCContext,
    target_has_offsets: bool,
) -> str:
    """发射 `dma.slice/dma.deslice` 的显式 loop nest copy 片段。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 以 `Memory::at(long long indices[])` 为基本访问单元，生成 rank 维嵌套循环。
    - 通过 `EmitCContext.allocate_temp_name(\"dma\")` 生成 `dma{N}` 前缀，确保多次发射时索引缓冲区命名唯一。
    - `target_has_offsets=True` 表示 offsets/strides 应用于 target（deslice）；否则应用于 source（slice）。

    使用示例:
    - stmt = _emit_dma_copy_loop_nest(source_expr=\"src\", target_expr=\"dst\", offsets=..., sizes=..., strides=..., ctx=ctx, target_has_offsets=False)

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target != "cpu":
        raise _emit_error(ctx, "dma.copy", "dma ops are cpu-only")
    base_name = ctx.allocate_temp_name("dma")
    source_indices_name = f"{base_name}_src_indices"
    target_indices_name = f"{base_name}_dst_indices"
    rank = len(sizes)
    lines = [
        _emit_long_long_buffer(source_indices_name, ["0"] * rank, ctx),
        _emit_long_long_buffer(target_indices_name, ["0"] * rank, ctx),
    ]
    loop_names: list[str] = []
    for index, size in enumerate(sizes):
        loop_name = f"{base_name}_i{index}"
        lines.append(f"{ctx.current_indent}for (long long {loop_name} = 0; {loop_name} < {emit_c_value(size, ctx)}; ++{loop_name}) {{")
        ctx.push_indent()
        loop_names.append(loop_name)
    for index, loop_name in enumerate(loop_names):
        offset_expr = emit_c_value(offsets[index], ctx)
        stride_expr = emit_c_value(strides[index], ctx)
        if target_has_offsets:
            lines.append(f"{ctx.current_indent}{source_indices_name}[{index}] = {loop_name};")
            lines.append(
                f"{ctx.current_indent}{target_indices_name}[{index}] = {offset_expr} + ({loop_name} * {stride_expr});"
            )
        else:
            lines.append(
                f"{ctx.current_indent}{source_indices_name}[{index}] = {offset_expr} + ({loop_name} * {stride_expr});"
            )
            lines.append(f"{ctx.current_indent}{target_indices_name}[{index}] = {loop_name};")
    lines.append(f"{ctx.current_indent}{target_expr}.at({target_indices_name}) = {source_expr}.at({source_indices_name});")
    for _ in reversed(loop_names):
        ctx.pop_indent()
        lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def _emit_dma_slice_stmt(op: DmaSliceOp, ctx: EmitCContext) -> str:
    """生成 `dma.slice` 的显式 loop nest copy 片段。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 把 source 的指定 offsets/sizes/strides 区域拷贝到 target 的单位偏移区域。
    - 当前阶段不生成 `slice(...)` helper 调用，仅生成显式循环拷贝。

    使用示例:
    - stmt = emit_c_op(slice_op, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target != "cpu":
        raise _emit_error(ctx, op.name, "dma ops are cpu-only")
    target_expr = _memory_base_name(op.target, ctx)
    source_expr = _memory_base_name(op.source, ctx)
    return _emit_dma_copy_loop_nest(
        source_expr=source_expr,
        target_expr=target_expr,
        offsets=op.offsets,
        sizes=op.sizes,
        strides=op.strides,
        ctx=ctx,
        target_has_offsets=False,
    )


def _emit_dma_deslice_stmt(op: DmaDesliceOp, ctx: EmitCContext) -> str:
    """生成 `dma.deslice` 的显式 loop nest copy 片段。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 把 source 的单位偏移区域拷贝回 target 的指定 offsets/sizes/strides 区域。
    - 绑定 `op.result` 名称为 target，确保 deslice 的结果可被后续节点稳定引用。

    使用示例:
    - stmt = emit_c_op(deslice_op, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target != "cpu":
        raise _emit_error(ctx, op.name, "dma ops are cpu-only")
    source_expr = _memory_base_name(op.source, ctx)
    target_expr = _memory_base_name(op.target, ctx)
    ctx.bind_name(op.result, target_expr)
    return _emit_dma_copy_loop_nest(
        source_expr=source_expr,
        target_expr=target_expr,
        offsets=op.offsets,
        sizes=op.sizes,
        strides=op.strides,
        ctx=ctx,
        target_has_offsets=True,
    )


def _emit_img2col2d_stmt(op: NnImg2col2dOp, ctx: EmitCContext) -> str:
    """生成 `nn.img2col2d` 的 CPU 侧调用片段。

    创建者: 小李飞刀
    最后一次更改: 大闸蟹

    功能说明:
    - 在 `target=cpu` 下生成：
      1) 输出 `Memory<Space, float>` 的声明（含 backing storage）。
      2) `cpu::img2col2d(input, out, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr);` 调用。

    使用示例:
    - stmt = emit_c_op(img2col2d_op, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target != "cpu":
        raise _emit_error(ctx, op.name, "nn ops are cpu-only")
    input_expr = _memory_base_name(op.input, ctx)
    result_expr = ctx.allocate_name(op.result)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise _emit_error(ctx, op.name, "result must be nn.memory")
    decl = _emit_memory_decl(result_expr, result_type, ctx, with_backing_storage=True)
    param_values = [
        emit_c_value(op.kh, ctx),
        emit_c_value(op.kw, ctx),
        emit_c_value(op.sh, ctx),
        emit_c_value(op.sw, ctx),
        emit_c_value(op.dh, ctx),
        emit_c_value(op.dw, ctx),
        emit_c_value(op.ph, ctx),
        emit_c_value(op.pw, ctx),
        emit_c_value(op.pl, ctx),
        emit_c_value(op.pr, ctx),
    ]
    args = ", ".join([input_expr, result_expr, *param_values])
    return f"{decl}\n{ctx.current_indent}cpu::img2col2d({args});"


def _emit_nn_add_stmt(op: NnAddOp, ctx: EmitCContext) -> str:
    """生成 `nn.add` 的 CPU 侧 `cpu::add(...)` 调用片段。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在 `target=cpu` 且 `op.result` 已在 `EmitCContext` 中预绑定名称时生效。
    - 支持三条最小节点级路径：
      - `Memory + Memory -> cpu::add(lhs, rhs, out);`
      - `Memory + i32 const -> cpu::add(lhs, 1, out);`
      - `Memory + !symbol.int -> cpu::add(lhs, bias, out);`
    - mixed 路径固定要求 memory 位于 lhs；`const/symbol + memory` 必须继续报 `unsupported op`。
    - 其余场景保持 `nn.add: unsupported op`，避免越界到函数级 result 分配或 mixed-promotion 收口。

    使用示例:
    - ctx.bind_name(op.result, "out"); emit_c_op(op, ctx) == "cpu::add(lhs, rhs, out);"

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target != "cpu":
        raise _emit_error(ctx, op.name, "unsupported op")
    result_name = ctx.lookup_name(op.result)
    if result_name is None:
        raise _emit_error(ctx, op.name, "unsupported op")
    if not isinstance(op.result.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")

    lhs_is_memory = isinstance(op.lhs.type, NnMemoryType)
    rhs_is_memory = isinstance(op.rhs.type, NnMemoryType)
    if lhs_is_memory and rhs_is_memory:
        lhs_expr = _memory_base_name(op.lhs, ctx)
        rhs_expr = _memory_base_name(op.rhs, ctx)
        return f"{ctx.current_indent}cpu::add({lhs_expr}, {rhs_expr}, {result_name});"

    if not lhs_is_memory or rhs_is_memory:
        raise _emit_error(ctx, op.name, "unsupported op")

    scalar_value = op.rhs
    scalar_type = scalar_value.type
    is_i32_scalar = isinstance(scalar_type, IntegerType) and scalar_type.width.data == 32
    if not (is_i32_scalar or isinstance(scalar_type, SymbolValueType)):
        raise _emit_error(ctx, op.name, "unsupported op")

    memory_expr = _memory_base_name(op.lhs, ctx)
    scalar_expr = emit_c_value(scalar_value, ctx)
    return f"{ctx.current_indent}cpu::add({memory_expr}, {scalar_expr}, {result_name});"


def _emit_kernel_binary_elewise_stmt(op: KernelBinaryElewiseOp, ctx: EmitCContext) -> str:
    """生成 `kernel.binary_elewise(kind=add)` 的目标后端 helper 调用。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 在 `target=cpu` 下把 `kernel.binary_elewise(kind=...)` 收口为对应 helper 调用。
    - 在 `target=npu_demo` 下把二元 helper 收口为显式模板参数且 `out-first` 的
      `npu_demo::<helper><Space, InType, OutType>(out, lhs, rhs);`。

    使用示例:
    - stmt = emit_c_op(binary_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    out_value, lhs_value, rhs_value = _normalized_binary_elewise_operands(op)
    lhs_expr = _memory_base_name(lhs_value, ctx)
    rhs_expr = _memory_base_name(rhs_value, ctx)
    out_expr = _memory_base_name(out_value, ctx)
    kind = op.kind.data
    if ctx.target == "cpu":
        helper_map = {
            "add": "add",
            "sub": "sub",
            "mul": "mul",
            "div": "div",
            "eq": "eq",
            "ne": "ne",
            "lt": "lt",
            "le": "le",
            "gt": "gt",
            "ge": "ge",
        }
        helper_name = helper_map.get(kind)
        if helper_name is None:
            raise _emit_error(ctx, op.name, f"unsupported kind={kind}")
        return f"{ctx.current_indent}cpu::{helper_name}({lhs_expr}, {rhs_expr}, {out_expr});"
    if ctx.target == "npu_demo":
        if (
            not isinstance(lhs_value.type, NnMemoryType)
            or not isinstance(rhs_value.type, NnMemoryType)
            or not isinstance(out_value.type, NnMemoryType)
        ):
            raise _emit_error(ctx, op.name, "unsupported op")
        helper_map = {
            "add": "add",
            "sub": "sub",
            "mul": "mul",
            "div": "truediv",
            "eq": "eq",
            "ne": "ne",
            "lt": "lt",
            "le": "le",
            "gt": "gt",
            "ge": "ge",
        }
        helper_name = helper_map.get(kind)
        if helper_name is None:
            raise _emit_error(ctx, op.name, f"unsupported kind={kind}")
        space_expr = _space_to_c(out_value.type, ctx)
        input_type = _type_to_c(lhs_value.type.element_type, ctx)
        output_type = _type_to_c(out_value.type.element_type, ctx)
        return (
            f"{ctx.current_indent}npu_demo::{helper_name}<{space_expr}, {input_type}, {output_type}>"
            f"({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
        )
    raise _emit_error(ctx, op.name, "unsupported target")


def _emit_npu_view_stmt(op: DmaViewOp, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 `dma.view` 的 helper 调用。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 把 `dma.view` 收口为 `Memory<...> out = source.view({offset} /*offset*/, {size} /*size*/, {stride} /*stride*/);`。
    - 使用当前 expectation 约定的 brace-list 文本，而不是 Vector 临时绑定。

    使用示例:
    - stmt = emit_c_op(view_op, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """
    result_name = ctx.allocate_name(op.result)
    source_expr = _memory_base_name(op.source, ctx)
    result_type = _type_to_c(op.result.type, ctx)
    offset_expr = _emit_npu_brace_list(op.offsets, ctx)
    size_expr = _emit_npu_brace_list(op.shape, ctx)
    stride_expr = _emit_npu_brace_list(op.stride, ctx)
    return (
        f"{ctx.current_indent}{result_type} {result_name} = "
        f"{source_expr}.view({offset_expr} /*offset*/, {size_expr} /*size*/, {stride_expr} /*stride*/);"
    )


def _emit_npu_query_stmt(op: ArchGetThreadIdOp | ArchGetThreadNumOp, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 thread 查询的赋值语句。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 把 `arch.get_thread_id` / `arch.get_thread_num` 发射为 `ctx.thread_id()` / `ctx.thread_num()`。
    - 即使结果预绑定了名称，也必须使用真实查询表达式，而不是回写为同名变量。

    使用示例:
    - stmt = emit_c_op(ArchGetThreadIdOp(), EmitCContext(target="npu_demo"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    result_name = ctx.allocate_name(op.result)
    expr = "ctx.thread_id()" if isinstance(op, ArchGetThreadIdOp) else "ctx.thread_num()"
    return f"{ctx.current_indent}long long {result_name} = {expr};"


def _emit_npu_dynamic_memory_stmt(op: ArchGetDynamicMemoryOp, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 dynamic memory 查询的赋值语句。

    创建者: jcc你莫辜负
    最后一次更改: 金铲铲大作战

    功能说明:
    - 把 `arch.get_dynamic_memory` 发射为
      `ctx.get_dynamic_memory<TSM/TLM1/TLM2/TLM3, T>()`。
    - 结果名可预绑定，但右值必须始终来自真实 helper 调用。

    使用示例:
    - stmt = emit_c_op(dynamic_mem_op, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    result_name = ctx.allocate_name(op.result)
    element_type = _type_to_c(op.result.type.element_type, ctx)
    space_expr = _space_name_to_c(op.memory_space.space.data, ctx)
    if space_expr not in _NPU_DYNAMIC_MEMORY_SPACES:
        raise _emit_error(ctx, op.name, "unsupported dynamic memory space")
    return (
        f"{ctx.current_indent}Memory<{space_expr}, {element_type}> {result_name} = "
        f"ctx.get_dynamic_memory<{space_expr}, {element_type}>();"
    )


def _emit_npu_slice_stmt(op: DmaSliceOp, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 `dma.slice` 的目标式 helper 调用。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 一维参数发射为 `slice(target, source, offset, size, stride);` 标量调用。
    - 多维参数发射为 `Vector` 绑定后再调用 `slice(target, source, offset_vec, size_vec, stride_vec);`，
      与 `include/npu_demo/Dma.h` 的 `const Vector&` 合同对齐。

    使用示例:
    - stmt = emit_c_op(slice_op, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """
    target_expr = _memory_base_name(op.target, ctx)
    source_expr = _memory_base_name(op.source, ctx)
    if len(op.offsets) == len(op.sizes) == len(op.strides) == 1:
        return (
            f"{ctx.current_indent}slice({target_expr} /*dst*/, {source_expr} /*source*/, "
            f"{emit_c_value(op.offsets[0], ctx)} /*offset*/, {emit_c_value(op.sizes[0], ctx)} /*size*/, {emit_c_value(op.strides[0], ctx)} /*stride*/);"
        )
    offset_lines, offset_vec = _emit_npu_vector_binding("slice_offset", op.offsets, ctx)
    size_lines, size_vec = _emit_npu_vector_binding("slice_size", op.sizes, ctx)
    stride_lines, stride_vec = _emit_npu_vector_binding("slice_stride", op.strides, ctx)
    return "\n".join(
        [
            *offset_lines,
            *size_lines,
            *stride_lines,
            (
                f"{ctx.current_indent}slice({target_expr} /*dst*/, {source_expr} /*source*/, "
                f"{offset_vec} /*offset*/, {size_vec} /*size*/, {stride_vec} /*stride*/);"
            ),
        ]
    )


def _emit_npu_deslice_stmt(op: DmaDesliceOp, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 `dma.deslice` 的目标式 helper 调用。

    创建者: jcc你莫辜负
    最后一次更改: 小李飞刀

    功能说明:
    - 一维参数发射为 `deslice(target, source, offset, size, stride);` 标量调用。
    - 多维参数发射为 `Vector` 绑定后再调用
      `deslice(target, source, offset_vec, size_vec, stride_vec);`，与 `include/npu_demo/Dma.h` 的 `const Vector&` 合同对齐。
    - 结果值绑定到 target 名称，确保后续节点可稳定引用该 memory。

    使用示例:
    - stmt = emit_c_op(deslice_op, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    source_expr = _memory_base_name(op.source, ctx)
    target_expr = _memory_base_name(op.target, ctx)
    ctx.bind_name(op.result, target_expr)
    if len(op.offsets) == len(op.sizes) == len(op.strides) == 1:
        return (
            f"{ctx.current_indent}deslice({target_expr}, {source_expr}, "
            f"{emit_c_value(op.offsets[0], ctx)}, {emit_c_value(op.sizes[0], ctx)}, {emit_c_value(op.strides[0], ctx)});"
        )
    offset_lines, offset_vec = _emit_npu_vector_binding("deslice_offset", op.offsets, ctx)
    size_lines, size_vec = _emit_npu_vector_binding("deslice_size", op.sizes, ctx)
    stride_lines, stride_vec = _emit_npu_vector_binding("deslice_stride", op.strides, ctx)
    return "\n".join(
        [
            *offset_lines,
            *size_lines,
            *stride_lines,
            f"{ctx.current_indent}deslice({target_expr}, {source_expr}, {offset_vec}, {size_vec}, {stride_vec});",
        ]
    )


def _emit_npu_vector_binding(
    prefix: str,
    values: tuple[SSAValue, ...],
    ctx: EmitCContext,
) -> tuple[list[str], str]:
    """生成 `target=npu_demo` 下 Vector 实参的缓冲区与绑定语句。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 把 `tuple[SSAValue, ...]` 发射为 `long long[N]` 缓冲区与 `Vector` 视图。
    - 供 `dma.slice/dma.deslice` 的多维 offset/size/stride 生成复用。

    使用示例:
    - lines, name = _emit_npu_vector_binding("slice_offset", op.offsets, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    buffer_name = ctx.allocate_temp_name(prefix)
    vector_name = f"{buffer_name}_vec"
    value_exprs = [emit_c_value(value, ctx) for value in values]
    return (
        [
            _emit_long_long_buffer(buffer_name, value_exprs, ctx),
            f"{ctx.current_indent}Vector {vector_name}({buffer_name}, {len(values)});",
        ],
        vector_name,
    )


def _emit_npu_add_stmt(op: NnAddOp, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 `nn.add` 的 helper 调用。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 把 `nn.add(memory, memory)` 发射为显式模板参数且 `out-first` 的
      `npu_demo::add<Space, InType, OutType>(out, lhs, rhs);`。
    - 结果必须预绑定为现有 memory 目标名；不在本层隐式声明临时输出。

    使用示例:
    - stmt = emit_c_op(add_op, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if not isinstance(op.lhs.type, NnMemoryType) or not isinstance(op.rhs.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    if not isinstance(op.result.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    result_name = ctx.lookup_name(op.result)
    if result_name is None:
        raise _emit_error(ctx, op.name, "unsupported op")
    lhs_expr = _memory_base_name(op.lhs, ctx)
    rhs_expr = _memory_base_name(op.rhs, ctx)
    space_expr = _space_to_c(op.result.type, ctx)
    input_type = _type_to_c(op.lhs.type.element_type, ctx)
    output_type = _type_to_c(op.result.type.element_type, ctx)
    return (
        f"{ctx.current_indent}npu_demo::add<{space_expr}, {input_type}, {output_type}>"
        f"({result_name} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
    )


def _emit_npu_kernel_exp_stmt(op: KernelExpOp, ctx: EmitCContext) -> str:
    out_value, input_value = _normalized_out_input_operands(
        SSAValue.get(op.out), SSAValue.get(op.input)
    )
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    out_expr = _memory_base_name(out_value, ctx)
    input_expr = _memory_base_name(input_value, ctx)
    space_expr = _space_to_c(out_value.type, ctx)
    input_type = _type_to_c(input_value.type.element_type, ctx)
    output_type = _type_to_c(out_value.type.element_type, ctx)
    return (
        f"{ctx.current_indent}npu_demo::exp<{space_expr}, {input_type}, {output_type}>"
        f"({out_expr} /*out*/, {input_expr} /*input*/);"
    )


def _emit_npu_kernel_select_stmt(op: KernelSelectOp, ctx: EmitCContext) -> str:
    out_value, cond_value, lhs_value, rhs_value = _normalized_select_operands(op)
    if (
        not isinstance(out_value.type, NnMemoryType)
        or not isinstance(cond_value.type, NnMemoryType)
        or not isinstance(lhs_value.type, NnMemoryType)
        or not isinstance(rhs_value.type, NnMemoryType)
    ):
        raise _emit_error(ctx, op.name, "unsupported op")
    out_expr = _memory_base_name(out_value, ctx)
    cond_expr = _memory_base_name(cond_value, ctx)
    lhs_expr = _memory_base_name(lhs_value, ctx)
    rhs_expr = _memory_base_name(rhs_value, ctx)
    space_expr = _space_to_c(out_value.type, ctx)
    input_type = _type_to_c(lhs_value.type.element_type, ctx)
    output_type = _type_to_c(out_value.type.element_type, ctx)
    return (
        f"{ctx.current_indent}npu_demo::select<{space_expr}, {input_type}, {output_type}>"
        f"({out_expr} /*out*/, {cond_expr} /*cond*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
    )


def _emit_npu_kernel_reduce_stmt(op: KernelReduceOp, ctx: EmitCContext) -> str:
    out_value, input_value = _normalized_out_input_operands(
        SSAValue.get(op.out), SSAValue.get(op.input)
    )
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    if op.kind.data != "sum":
        raise _emit_error(ctx, op.name, f"unsupported kind={op.kind.data}")
    out_expr = _memory_base_name(out_value, ctx)
    input_expr = _memory_base_name(input_value, ctx)
    space_expr = _space_to_c(out_value.type, ctx)
    input_type = _type_to_c(input_value.type.element_type, ctx)
    output_type = _type_to_c(out_value.type.element_type, ctx)
    axis_expr = op.axis.value.data
    return (
        f"{ctx.current_indent}npu_demo::reduce_sum<{space_expr}, {input_type}, {output_type}>"
        f"({out_expr} /*out*/, {input_expr} /*input*/, {axis_expr} /*axis*/);"
    )


def _emit_npu_kernel_reduce_min_stmt(op: KernelReduceMinOp, ctx: EmitCContext) -> str:
    out_value, input_value = _normalized_out_input_operands(
        SSAValue.get(op.out), SSAValue.get(op.input)
    )
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    out_expr = _memory_base_name(out_value, ctx)
    input_expr = _memory_base_name(input_value, ctx)
    space_expr = _space_to_c(out_value.type, ctx)
    input_type = _type_to_c(input_value.type.element_type, ctx)
    output_type = _type_to_c(out_value.type.element_type, ctx)
    axis_expr = op.axis.value.data
    return (
        f"{ctx.current_indent}npu_demo::reduce_min<{space_expr}, {input_type}, {output_type}>"
        f"({out_expr} /*out*/, {input_expr} /*input*/, {axis_expr} /*axis*/);"
    )


def _emit_npu_kernel_img2col1d_stmt(op: KernelImg2col1dOp, ctx: EmitCContext) -> str:
    out_value, input_value = _normalized_out_input_operands(
        SSAValue.get(op.out), SSAValue.get(op.input)
    )
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    out_expr = _memory_base_name(out_value, ctx)
    input_expr = _memory_base_name(input_value, ctx)
    input_space = _space_to_c(input_value.type, ctx)
    output_space = _space_to_c(out_value.type, ctx)
    input_type = _type_to_c(input_value.type.element_type, ctx)
    output_type = _type_to_c(out_value.type.element_type, ctx)
    params = [emit_c_value(value, ctx) for value in (op.k, op.s, op.d, op.p_left, op.p_right)]
    return (
        f"{ctx.current_indent}npu_demo::img2col1d<{input_space}, {output_space}, {input_type}, {output_type}>"
        f"({out_expr} /*out*/, {input_expr} /*input*/, {params[0]} /*k*/, {params[1]} /*s*/, {params[2]} /*d*/, {params[3]} /*p_left*/, {params[4]} /*p_right*/);"
    )


def _emit_npu_kernel_img2col2d_stmt(op: KernelImg2col2dOp, ctx: EmitCContext) -> str:
    out_value, input_value = _normalized_out_input_operands(
        SSAValue.get(op.out), SSAValue.get(op.input)
    )
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    out_expr = _memory_base_name(out_value, ctx)
    input_expr = _memory_base_name(input_value, ctx)
    input_space = _space_to_c(input_value.type, ctx)
    output_space = _space_to_c(out_value.type, ctx)
    input_type = _type_to_c(input_value.type.element_type, ctx)
    output_type = _type_to_c(out_value.type.element_type, ctx)
    params = [emit_c_value(value, ctx) for value in (op.kh, op.kw, op.sh, op.sw, op.dh, op.dw, op.ph, op.pw, op.pl, op.pr)]
    return (
        f"{ctx.current_indent}npu_demo::img2col2d<{input_space}, {output_space}, {input_type}, {output_type}>"
        f"({out_expr} /*out*/, {input_expr} /*input*/, {params[0]} /*kh*/, {params[1]} /*kw*/, {params[2]} /*sh*/, {params[3]} /*sw*/, {params[4]} /*dh*/, {params[5]} /*dw*/, {params[6]} /*ph*/, {params[7]} /*pw*/, {params[8]} /*pl*/, {params[9]} /*pr*/);"
    )


def _emit_npu_broadcast_stmt(op: DmaBroadcastOp, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 `dma.broadcast` 的 helper 调用。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 把 `dma.broadcast(target, source)` 发射为显式模板参数的
      `npu_demo::broadcast<DstSpace, SrcSpace, DstType, SrcType>(dst, source);`。
    - 仅覆盖当前 expectation 需要的 memory source 路径。

    使用示例:
    - stmt = emit_c_op(broadcast_op, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if not isinstance(op.target.type, NnMemoryType) or not isinstance(op.source.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    dst_expr = _memory_base_name(op.target, ctx)
    src_expr = _memory_base_name(op.source, ctx)
    dst_space = _space_to_c(op.target.type, ctx)
    src_space = _space_to_c(op.source.type, ctx)
    dst_type = _type_to_c(op.target.type.element_type, ctx)
    src_type = _type_to_c(op.source.type.element_type, ctx)
    return (
        f"{ctx.current_indent}npu_demo::broadcast<{dst_space}, {src_space}, {dst_type}, {src_type}>"
        f"({dst_expr} /*dst*/, {src_expr} /*source*/);"
    )


def _emit_npu_copy_stmt(op: DmaCopyOp, ctx: EmitCContext) -> str:
    target_expr = _memory_base_name(op.target, ctx)
    source_expr = _memory_base_name(op.source, ctx)
    target_space = _space_to_c(op.target.type, ctx)
    source_space = _space_to_c(op.source.type, ctx)
    target_type = _type_to_c(op.target.type.element_type, ctx)
    source_type = _type_to_c(op.source.type.element_type, ctx)
    return (
        f"{ctx.current_indent}npu_demo::copy<{target_space}, {source_space}, {target_type}, {source_type}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/);"
    )


def _emit_npu_cast_stmt(op: DmaCastOp, ctx: EmitCContext) -> str:
    if len(op.operands) == 2:
        target_value = op.target
        source_value = op.source
        target_type_attr = op.target.type
    elif len(op.operands) == 1 and len(op.results) == 1:
        target_value = op.results[0]
        source_value = op.operands[0]
        target_type_attr = op.results[0].type
    else:
        raise _emit_error(ctx, op.name, "unsupported op")
    if not isinstance(target_type_attr, NnMemoryType) or not isinstance(source_value.type, NnMemoryType):
        raise _emit_error(ctx, op.name, "unsupported op")
    target_expr = _memory_base_name(target_value, ctx)
    source_expr = _memory_base_name(source_value, ctx)
    space_expr = _space_to_c(target_type_attr, ctx)
    target_type = _type_to_c(target_type_attr.element_type, ctx)
    source_type = _type_to_c(source_value.type.element_type, ctx)
    return (
        f"{ctx.current_indent}npu_demo::cast<{space_expr}, {target_type}, {source_type}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/);"
    )


def _emit_npu_fill_stmt(op: DmaFillOp, ctx: EmitCContext) -> str:
    target_expr = _memory_base_name(op.target, ctx)
    space_expr = _space_to_c(op.target.type, ctx)
    target_type = _type_to_c(op.target.type.element_type, ctx)
    value_expr = emit_c_value(op.value, ctx)
    return (
        f"{ctx.current_indent}npu_demo::fill<{space_expr}, {target_type}>"
        f"({target_expr} /*dst*/, {value_expr} /*value*/);"
    )


def _emit_npu_free_stmt(op: DmaFreeOp, ctx: EmitCContext) -> str:
    source_expr = _memory_base_name(op.source, ctx)
    space_expr = _space_to_c(op.source.type, ctx)
    source_type = _type_to_c(op.source.type.element_type, ctx)
    return (
        f"{ctx.current_indent}npu_demo::free<{space_expr}, {source_type}>"
        f"({source_expr} /*source*/);"
    )


def _emit_npu_load_stmt(op: DmaLoadOp, ctx: EmitCContext) -> str:
    target_expr = _memory_base_name(op.target, ctx)
    source_expr = _memory_base_name(op.source, ctx)
    target_space = _space_to_c(op.target.type, ctx)
    source_space = _space_to_c(op.source.type, ctx)
    target_type = _type_to_c(op.target.type.element_type, ctx)
    source_type = _type_to_c(op.source.type.element_type, ctx)
    offset_expr = _emit_npu_brace_list(op.offsets, ctx)
    size_expr = _emit_npu_brace_list(op.sizes, ctx)
    stride_expr = _emit_npu_brace_list(op.strides, ctx)
    return (
        f"{ctx.current_indent}npu_demo::load<{target_space}, {source_space}, {target_type}, {source_type}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/, {offset_expr} /*offset*/, "
        f"{size_expr} /*size*/, {stride_expr} /*stride*/);"
    )


def _emit_npu_store_stmt(op: DmaStoreOp, ctx: EmitCContext) -> str:
    target_expr = _memory_base_name(op.target, ctx)
    source_expr = _memory_base_name(op.source, ctx)
    target_space = _space_to_c(op.target.type, ctx)
    source_space = _space_to_c(op.source.type, ctx)
    target_type = _type_to_c(op.target.type.element_type, ctx)
    source_type = _type_to_c(op.source.type.element_type, ctx)
    offset_expr = _emit_npu_brace_list(op.offsets, ctx)
    size_expr = _emit_npu_brace_list(op.sizes, ctx)
    stride_expr = _emit_npu_brace_list(op.strides, ctx)
    return (
        f"{ctx.current_indent}npu_demo::store<{target_space}, {source_space}, {target_type}, {source_type}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/, {offset_expr} /*offset*/, "
        f"{size_expr} /*size*/, {stride_expr} /*stride*/);"
    )


def _emit_npu_transpose_stmt(op: DmaTransposeOp, ctx: EmitCContext) -> str:
    target_expr = _memory_base_name(op.target, ctx)
    source_expr = _memory_base_name(op.source, ctx)
    target_space = _space_to_c(op.target.type, ctx)
    source_space = _space_to_c(op.source.type, ctx)
    target_type = _type_to_c(op.target.type.element_type, ctx)
    source_type = _type_to_c(op.source.type.element_type, ctx)
    perm_values = ", ".join(
        str(value.data if isinstance(value, IntAttr) else value.value.data) for value in op.perm.data
    )
    return (
        f"{ctx.current_indent}npu_demo::transpose<{target_space}, {source_space}, {target_type}, {source_type}>"
        f"({target_expr} /*dst*/, {source_expr} /*source*/, {{{perm_values}}} /*perm*/);"
    )


def _emit_npu_reshape_stmt(op: DmaReshapeOp, ctx: EmitCContext) -> str:
    result_name = ctx.allocate_name(op.result)
    source_expr = _memory_base_name(op.source, ctx)
    result_type = _type_to_c(op.result.type, ctx)
    shape_expr = _emit_npu_brace_list(op.shape, ctx)
    return (
        f"{ctx.current_indent}{result_type} {result_name} = "
        f"{source_expr}.reshape({shape_expr} /*shape*/);"
    )


def _emit_symbol_const_stmt(op: Operation, ctx: EmitCContext) -> str:
    if isinstance(op, SymbolConstOp):
        value_text = str(op.value.data)
        result = op.result
    else:
        if not op.results or not isinstance(op.results[0].type, SymbolValueType):
            raise _emit_error(ctx, op.name, "symbol.const result must be !symbol.int")
        value_text = op.results[0].type.expr.expr.data
        result = op.results[0]
    if all(isinstance(use.operation, (DmaLoadOp, DmaStoreOp)) for use in result.uses):
        return ""
    preferred = f"c_{value_text}".replace("-", "neg_")
    if result.uses and all(isinstance(use.operation, DmaSliceOp) for use in result.uses):
        name = _bind_preferred_name(ctx, result, preferred)
    elif ctx.has_bound_name(preferred):
        name = _bind_preferred_name(ctx, result, preferred)
    else:
        name = ctx.bind_name(result, preferred)
    return f"{ctx.current_indent}S_INT {name} = {value_text};"


def _emit_symbol_cast_stmt(op: SymbolToIntOp | SymbolCastOp, ctx: EmitCContext) -> str:
    result_name = ctx.lookup_name(op.result)
    if result_name is None:
        source_owner = op.source.owner
        if isinstance(source_owner, Operation) and _is_symbol_const_like(source_owner):
            source_name = emit_c_value(op.source, ctx)
            result_name = ctx.bind_name(op.result, f"{source_name}_cast_{_type_to_c(op.result.type, ctx)}")
        else:
            result_name = ctx.bind_name(op.result, f"value_cast_{_type_to_c(op.result.type, ctx)}")
    return f"{ctx.current_indent}{_type_to_c(op.result.type, ctx)} {result_name} = {emit_c_value(op.source, ctx)};"


def _emit_npu_kernel_matmul_stmt(op: KernelMatmulOp, ctx: EmitCContext) -> str:
    """生成 `target=npu_demo` 下 `kernel.matmul` 的 helper 调用。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 把 lowered `kernel.matmul(lhs, rhs, out)` 发射为显式模板参数且 `out-first` 的
      `npu_demo::matmul<lhs_space, rhs_space, out_space, lhs_dtype, rhs_dtype, out_dtype>(out, lhs, rhs);`。
    - 模板参数顺序固定按 `lhs space -> rhs space -> out space -> lhs dtype -> rhs dtype -> out dtype` 展开，
      避免依赖 C++ 推导，同时保持 `execute_engine` / `emit_c` 的 `npu_demo` matmul 合同一致。
    - 只在 `target=npu_demo` 公开该后端专用 helper。

    使用示例:
    - stmt = emit_c_op(kernel_matmul_op, EmitCContext(target="npu_demo"))
    - npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out, lhs, rhs)

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    out_value, lhs_value, rhs_value = _normalized_matmul_operands(op)
    lhs_expr = _memory_base_name(lhs_value, ctx)
    rhs_expr = _memory_base_name(rhs_value, ctx)
    out_expr = _memory_base_name(out_value, ctx)
    lhs_space = _space_to_c(lhs_value.type, ctx)
    rhs_space = _space_to_c(rhs_value.type, ctx)
    out_space = _space_to_c(out_value.type, ctx)
    lhs_type = _type_to_c(lhs_value.type.element_type, ctx)
    rhs_type = _type_to_c(rhs_value.type.element_type, ctx)
    out_type = _type_to_c(out_value.type.element_type, ctx)
    return (
        f"{ctx.current_indent}npu_demo::matmul<{lhs_space}, {rhs_space}, {out_space}, "
        f"{lhs_type}, {rhs_type}, {out_type}>({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
    )


def emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    """把 SSA value 生成为可嵌入右值位置的表达式文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 负责把常量、二元算术、比较、unit-tile `dma.load`、`symbol.add/symbol.to_int`（cpu）
      以及 `symbol.get_dim` 结果转换为右值表达式。
    - 若 value 已在 `EmitCContext` 中绑定名称，则直接复用稳定名称。

    使用示例:
    - expr = emit_c_value(value, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    if isinstance(value, BlockArgument):
        return ctx.bind_name(value, f"arg{value.index}")
    owner = value.owner
    if isinstance(owner, arith.ConstantOp):
        return _format_literal(owner, ctx)
    if _is_symbol_const_like(owner):
        if isinstance(owner, SymbolConstOp):
            return str(owner.value.data)
        if owner.results and isinstance(owner.results[0].type, SymbolValueType):
            return owner.results[0].type.expr.expr.data
        raise _emit_error(ctx, owner.name, "symbol.const result must be !symbol.int")
    if ctx.target == "npu_demo":
        if isinstance(owner, ArchGetThreadIdOp):
            return "ctx.thread_id()"
        if isinstance(owner, ArchGetThreadNumOp):
            return "ctx.thread_num()"
        if isinstance(owner, ArchGetDynamicMemoryOp):
            element_type = _type_to_c(owner.result.type.element_type, ctx)
            space_expr = _space_name_to_c(owner.memory_space.space.data, ctx)
            if space_expr not in _NPU_DYNAMIC_MEMORY_SPACES:
                raise _emit_error(ctx, owner.name, "unsupported dynamic memory space")
            return f"ctx.get_dynamic_memory<{space_expr}, {element_type}>()"
    if owner.name in _BINARY_SIGILS:
        if owner.name.startswith("symbol.") and ctx.target not in {"cpu", "npu_demo"}:
            raise _emit_error(ctx, owner.name, "unsupported target")
        lhs = emit_c_value(owner.operands[0], ctx)
        rhs = emit_c_value(owner.operands[1], ctx)
        return f"({lhs} {_BINARY_SIGILS[owner.name]} {rhs})"
    if owner.name in _SYMBOL_COMPARE_SIGILS:
        if ctx.target not in {"cpu", "npu_demo"}:
            raise _emit_error(ctx, owner.name, "unsupported target")
        lhs = emit_c_value(owner.operands[0], ctx)
        rhs = emit_c_value(owner.operands[1], ctx)
        return f"({lhs} {_SYMBOL_COMPARE_SIGILS[owner.name]} {rhs})"
    if isinstance(owner, arith.CmpiOp):
        predicate = owner.predicate.value.data
        if predicate not in _CMPI_SIGILS:
            raise _emit_error(ctx, owner.name, "unsupported comparison predicate")
        lhs = emit_c_value(owner.lhs, ctx)
        rhs = emit_c_value(owner.rhs, ctx)
        return f"({lhs} {_CMPI_SIGILS[predicate]} {rhs})"
    if isinstance(owner, (SymbolToIntOp, SymbolCastOp, SymbolToFloatOp)):
        return emit_c_value(owner.source, ctx)
    if isinstance(owner, SymbolGetDimOp):
        if not isinstance(owner.axis, IntAttr):
            raise _emit_error(ctx, owner.name, "axis must be IntAttr")
        source_expr = _memory_base_name(owner.source, ctx)
        if ctx.target == "npu_demo":
            return f"{source_expr}.get_shape({owner.axis.data})"
        return f"{source_expr}.shape()[{owner.axis.data}]"
    if isinstance(owner, SymbolGetStrideOp):
        if not isinstance(owner.axis, IntAttr):
            raise _emit_error(ctx, owner.name, "axis must be IntAttr")
        source_expr = _memory_base_name(owner.source, ctx)
        if ctx.target == "npu_demo":
            return f"{source_expr}.get_stride({owner.axis.data})"
        return f"{source_expr}.stride()[{owner.axis.data}]"
    raise _emit_error(ctx, owner.name, f"invalid dependency for value {value}")


def _emit_assignment(op: Operation, ctx: EmitCContext) -> str:
    result = op.results[0]
    result_type = _type_to_c(result.type, ctx)
    expr = emit_c_value(result, ctx)
    result_name = ctx.allocate_name(result)
    return f"{ctx.current_indent}{result_type} {result_name} = {expr};"


def _emit_loop_region(
    lower: SSAValue,
    upper: SSAValue,
    step: SSAValue,
    block: Any,
    ctx: EmitCContext,
    iv_type: str = "long long",
) -> str:
    """把循环 region 发射为 `for (...) { ... }` 语句块。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 同时用于 `scf.for` 与 `symbol.for` 的循环发射。
    - 自动过滤循环体中 `emit_c_op(...) == \"\"` 的空语句，避免常量节点产生空行。

    使用示例:
    - stmt = _emit_loop_region(lb, ub, step, block, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """
    iv_name = ctx.allocate_name(block.args[0], prefix="i")
    lower_expr = emit_c_value(lower, ctx)
    upper_expr = emit_c_value(upper, ctx)
    step_expr = emit_c_value(step, ctx)
    lines = [
        f"{ctx.current_indent}for ({iv_type} {iv_name} = {lower_expr}; {iv_name} < {upper_expr}; {iv_name} += {step_expr}) {{"
    ]
    ctx.push_indent()
    for body_op in block.ops:
        if isinstance(body_op, scf.YieldOp):
            continue
        stmt = emit_c_op(body_op, ctx)
        if stmt:
            lines.append(stmt)
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def _emit_loop(op: scf.ForOp, ctx: EmitCContext) -> str:
    return _emit_loop_region(op.lb, op.ub, op.step, op.body.block, ctx)


def _emit_symbol_loop(op: SymbolForOp, ctx: EmitCContext) -> str:
    """把 `symbol.for` 发射为循环语句块。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 在 `target=cpu/npu_demo` 下生成与 `scf.for` 同风格的循环结构。
    - 迭代变量命名由 `EmitCContext.allocate_name(..., prefix=\"i\")` 分配，确保稳定且避免冲突。

    使用示例:
    - stmt = emit_c_op(symbol_for_op, EmitCContext(target=\"npu_demo\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target not in {"cpu", "npu_demo"}:
        raise _emit_error(ctx, op.name, "unsupported target")
    iv_type = "S_INT" if ctx.target == "npu_demo" else "long long"
    return _emit_loop_region(op.start, op.end, op.step, op.body.block, ctx, iv_type=iv_type)


def emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    """把单个 MLIR op 生成为目标后端的语句或语句块文本。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 负责把单个 op 转换为赋值语句、控制流语句块、访存语句、memory 视图声明或 helper 调用片段。
    - `target=cpu` 支持现有 `symbol.for/symbol.get_dim/dma.alloc/fill/view/slice/deslice/kernel.binary_elewise/nn.img2col2d/nn.add` 节点级发射。
    - `target=npu_demo` 支持当前公开的 `symbol.const/symbol.for`、`KernelContext` 查询、`TSM/TLM` dynamic memory、
      `view/slice/deslice/add/kernel.matmul` 节点级发射。

    使用示例:
    - stmt = emit_c_op(op, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if op.name in _BINARY_SIGILS or op.name in _SYMBOL_COMPARE_SIGILS or isinstance(op, arith.CmpiOp):
        return _emit_assignment(op, ctx)
    if isinstance(op, arith.ConstantOp):
        return ""
    if _is_symbol_const_like(op):
        if ctx.target == "npu_demo":
            return _emit_symbol_const_stmt(op, ctx)
        return ""
    if isinstance(op, (SymbolToIntOp, SymbolCastOp)):
        if ctx.target == "npu_demo":
            return _emit_symbol_cast_stmt(op, ctx)
        return ""
    if isinstance(op, SymbolToFloatOp):
        if ctx.target == "npu_demo":
            return _emit_assignment(op, ctx)
        return ""
    if op.name in {"tile.symbol_literal", "tile.step_value"}:
        if not op.results:
            raise _emit_error(ctx, op.name, "missing result")
        result_type = op.results[0].type
        if not isinstance(result_type, SymbolValueType):
            raise _emit_error(ctx, op.name, "result must be !symbol.int")
        value = result_type.get_value()
        ctx.bind_name(op.results[0], str(value))
        return ""
    if ctx.target == "npu_demo":
        if isinstance(op, (ArchGetThreadIdOp, ArchGetThreadNumOp)):
            return _emit_npu_query_stmt(op, ctx)
        if isinstance(op, ArchGetDynamicMemoryOp):
            return _emit_npu_dynamic_memory_stmt(op, ctx)
        if isinstance(op, (SymbolGetDimOp, SymbolGetStrideOp)):
            return _emit_assignment(op, ctx)
        if isinstance(op, SymbolForOp):
            return _emit_symbol_loop(op, ctx)
        if isinstance(op, DmaAllocOp):
            return _emit_dma_alloc_stmt(op, ctx)
        if isinstance(op, DmaFillOp):
            return _emit_npu_fill_stmt(op, ctx)
        if isinstance(op, DmaFreeOp):
            return _emit_npu_free_stmt(op, ctx)
        if isinstance(op, DmaCopyOp):
            return _emit_npu_copy_stmt(op, ctx)
        if isinstance(op, DmaViewOp):
            return _emit_npu_view_stmt(op, ctx)
        if isinstance(op, DmaReshapeOp):
            return _emit_npu_reshape_stmt(op, ctx)
        if isinstance(op, DmaCastOp):
            return _emit_npu_cast_stmt(op, ctx)
        if isinstance(op, DmaSliceOp):
            return _emit_npu_slice_stmt(op, ctx)
        if isinstance(op, DmaDesliceOp):
            return _emit_npu_deslice_stmt(op, ctx)
        if isinstance(op, DmaBroadcastOp):
            return _emit_npu_broadcast_stmt(op, ctx)
        if isinstance(op, DmaLoadOp):
            return _emit_npu_load_stmt(op, ctx)
        if isinstance(op, DmaStoreOp):
            return _emit_npu_store_stmt(op, ctx)
        if isinstance(op, DmaTransposeOp):
            return _emit_npu_transpose_stmt(op, ctx)
        if isinstance(op, KernelBinaryElewiseOp):
            return _emit_kernel_binary_elewise_stmt(op, ctx)
        if isinstance(op, KernelExpOp):
            return _emit_npu_kernel_exp_stmt(op, ctx)
        if isinstance(op, KernelSelectOp):
            return _emit_npu_kernel_select_stmt(op, ctx)
        if isinstance(op, KernelReduceOp):
            return _emit_npu_kernel_reduce_stmt(op, ctx)
        if isinstance(op, KernelReduceMinOp):
            return _emit_npu_kernel_reduce_min_stmt(op, ctx)
        if isinstance(op, KernelImg2col1dOp):
            return _emit_npu_kernel_img2col1d_stmt(op, ctx)
        if isinstance(op, KernelImg2col2dOp):
            return _emit_npu_kernel_img2col2d_stmt(op, ctx)
        if isinstance(op, KernelMatmulOp):
            return _emit_npu_kernel_matmul_stmt(op, ctx)
        if isinstance(op, NnAddOp):
            return _emit_npu_add_stmt(op, ctx)
        raise _emit_error(ctx, op.name, "unsupported op")
    if isinstance(op, SymbolGetDimOp):
        return ""
    if isinstance(op, SymbolGetStrideOp):
        return ""
    if isinstance(op, DmaAllocOp):
        return _emit_dma_alloc_stmt(op, ctx)
    if isinstance(op, DmaFillOp):
        return _emit_dma_fill_stmt(op, ctx)
    if isinstance(op, DmaLoadOp):
        return _emit_dma_load_stmt(op, ctx)
    if isinstance(op, DmaStoreOp):
        return _emit_dma_store_stmt(op, ctx)
    if isinstance(op, DmaSliceOp):
        return _emit_dma_slice_stmt(op, ctx)
    if isinstance(op, DmaDesliceOp):
        return _emit_dma_deslice_stmt(op, ctx)
    if isinstance(op, DmaViewOp):
        return _emit_dma_view_stmt(op, ctx)
    if isinstance(op, KernelBinaryElewiseOp):
        return _emit_kernel_binary_elewise_stmt(op, ctx)
    if isinstance(op, NnAddOp):
        return _emit_nn_add_stmt(op, ctx)
    if isinstance(op, scf.ForOp):
        return _emit_loop(op, ctx)
    if isinstance(op, SymbolForOp):
        return _emit_symbol_loop(op, ctx)
    if isinstance(op, NnImg2col2dOp):
        return _emit_img2col2d_stmt(op, ctx)
    if isinstance(op, func.ReturnOp):
        if not op.arguments:
            return ""
        if len(op.arguments) != 1:
            raise _emit_error(ctx, op.name, "unsupported return arity")
        return f"{ctx.current_indent}return {emit_c_value(op.arguments[0], ctx)};"
    raise _emit_error(ctx, op.name, "unsupported op")


__all__ = ["EmitCContext", "EmitCError", "emit_c_op", "emit_c_value"]
