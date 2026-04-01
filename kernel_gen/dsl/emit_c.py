"""C-like fragment emission helpers for DSL lowering.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

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
from xdsl.dialects.builtin import FloatAttr, IndexType, IntAttr, IntegerAttr, IntegerType, f32
from xdsl.ir import BlockArgument, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp, DmaLoadOp, DmaSliceOp, DmaStoreOp, DmaViewOp
from kernel_gen.dialect.nn import NnAddOp, NnImg2col2dOp, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolValueType


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


def _emit_error(ctx: EmitCContext, subject: str, reason: str) -> EmitCError:
    return EmitCError(f"target={ctx.target}: {subject}: {reason}")


_BINARY_SIGILS = {
    "arith.addi": "+",
    "arith.addf": "+",
    "arith.subi": "-",
    "arith.subf": "-",
    "arith.muli": "*",
    "arith.mulf": "*",
    "arith.divf": "/",
    "symbol.add": "+",
}

_CMPI_SIGILS = {
    0: "==",
    1: "!=",
    2: "<",
    3: "<=",
    4: ">",
    5: ">=",
}


def _type_to_c(attr: Any, ctx: EmitCContext) -> str:
    """将 xdsl/DSL 类型映射为 C 侧类型文本。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 在未提供 `ctx.type_converter` 时，按最小覆盖集把常用类型映射为 C/C++ 类型字符串。
    - 当前覆盖：`i1/bool`、`i32/int32_t`、`index/long long`、`f32/float`、`!nn.memory/Memory<T>`、`!symbol.int/long long`。
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
        if attr.width.data == 1:
            return "bool"
        return f"int{attr.width.data}_t"
    if attr == f32:
        return "float"
    if isinstance(attr, IndexType):
        return "long long"
    if isinstance(attr, NnMemoryType):
        return f"Memory<{_type_to_c(attr.element_type, ctx)}>"
    if isinstance(attr, SymbolValueType):
        return "long long"
    raise _emit_error(ctx, f"type {attr}", "unsupported type")


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
    """把 nn.memory 的 space 映射为 CPU `MemorySpace::...` 枚举。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将 `#nn.space<global/shared/local/tsm/tlm>` 映射为对应的 `MemorySpace::GM/SM/LM/TSM/TLM`。
    - 用于 `dma.alloc`/`dma.view`/`nn.img2col2d` 等内存视图声明时的 space 生成。

    使用示例:
    - _space_to_c(memory_type, EmitCContext(target=\"cpu\")) == \"MemorySpace::GM\"

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    mapping = {
        "global": "MemorySpace::GM",
        "shared": "MemorySpace::SM",
        "local": "MemorySpace::LM",
        "tsm": "MemorySpace::TSM",
        "tlm": "MemorySpace::TLM",
    }
    space_name = memory_type.space.space.data
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
    """为 `Memory<T>` 声明生成 backing storage（buffer）声明语句。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

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
    """发射 `Memory<T>` 声明语句（含 shape/stride 缓冲区与可选 backing）。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成 `shape/stride` 的 `long long[]` 声明。
    - 生成 `Memory<T> name(data, rank, shape, stride, format, space);` 声明。
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
    lines = [
        _emit_long_long_buffer(f"{name}_shape", shape_values, ctx),
        _emit_long_long_buffer(f"{name}_stride", stride_values, ctx),
        *storage_lines,
        (
            f"{ctx.current_indent}Memory<{element_type}> {name}"
            f"({data_expr}, {len(shape_values)}, {name}_shape, {name}_stride, "
            f"{format_expr}, {space_expr});"
        ),
    ]
    return "\n".join(lines)


def _is_unit_tile(memory_type: NnMemoryType) -> bool:
    if len(memory_type.shape.data) == 0:
        return False
    return all(isinstance(dim, IntAttr) and dim.data == 1 for dim in memory_type.shape.data)


def _emit_dma_load_expr(op: DmaLoadOp, ctx: EmitCContext) -> str:
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType) or not _is_unit_tile(result_type):
        raise _emit_error(ctx, op.name, "only unit-tile dma.load is supported")
    base = _memory_base_name(op.source, ctx)
    return f"{base}{_format_indices(op.offsets, ctx)}"


def _emit_dma_store_stmt(op: DmaStoreOp, ctx: EmitCContext) -> str:
    source_type = op.source.type
    if not isinstance(source_type, NnMemoryType) or not _is_unit_tile(source_type):
        raise _emit_error(ctx, op.name, "only unit-tile dma.store source is supported")
    source_expr = _memory_base_name(op.source, ctx)
    target_expr = _memory_base_name(op.target, ctx)
    return f"{ctx.current_indent}{target_expr}{_format_indices(op.offsets, ctx)} = {source_expr};"


def _emit_dma_alloc_stmt(op: DmaAllocOp, ctx: EmitCContext) -> str:
    """生成 `dma.alloc` 的 CPU 侧 `Memory<T>` 声明片段。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 在 `target=cpu` 下为 `dma.alloc` 结果发射 `shape/stride` 缓冲区与 `Memory<T>` 声明。
    - 当前阶段必须生成有效 backing storage（静态 shape 为栈上数组）。
    - 若结果 type.shape 包含符号维度，必须报错（避免 dynamic backing 生命周期不明确）。

    使用示例:
    - stmt = emit_c_op(DmaAllocOp([], alloc_type), EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target != "cpu":
        raise _emit_error(ctx, op.name, "dma ops are cpu-only")
    result_name = ctx.allocate_name(op.result)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise _emit_error(ctx, op.name, "result must be nn.memory")
    shape_values = [emit_c_value(value, ctx) for value in op.dynamic_shape]
    if not shape_values:
        shape_values = _format_static_layout(result_type.shape.data, ctx, op.name)
    return _emit_memory_decl(result_name, result_type, ctx, shape_values=shape_values, with_backing_storage=True)


def _emit_dma_view_stmt(op: DmaViewOp, ctx: EmitCContext) -> str:
    """生成 `dma.view` 的 CPU 侧 memory 视图声明片段。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 在 `target=cpu` 下基于源 `Memory<T>` 生成子视图：
      - 发射 offset 计算（以源 stride 为单位）。
      - 发射目标 `shape/stride` 缓冲区与 `Memory<T>` 视图声明。
    - 目标视图复用源 memory 的 `format/space`。

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
        space_expr=f"{source_expr}.space()",
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
    最后一次更改: 朽木露琪亚

    功能说明:
    - 在 `target=cpu` 下生成：
      1) 输出 `Memory<float>` 的声明（含 backing storage）。
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
    attr_values = [
        op.kh.value.data,
        op.kw.value.data,
        op.sh.value.data,
        op.sw.value.data,
        op.dh.value.data,
        op.dw.value.data,
        op.ph.value.data,
        op.pw.value.data,
        op.pl.value.data,
        op.pr.value.data,
    ]
    args = ", ".join([input_expr, result_expr, *(str(value) for value in attr_values)])
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


def emit_c_value(value: SSAValue, ctx: EmitCContext) -> str:
    """把 SSA value 生成为可嵌入右值位置的表达式文本。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 负责把常量、二元算术、比较、unit-tile `dma.load` 与 `symbol.add`（cpu）结果转换为右值表达式。
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
    if owner.name in _BINARY_SIGILS:
        if owner.name == "symbol.add" and ctx.target != "cpu":
            raise _emit_error(ctx, owner.name, "symbol scalar ops are cpu-only")
        lhs = emit_c_value(owner.operands[0], ctx)
        rhs = emit_c_value(owner.operands[1], ctx)
        return f"({lhs} {_BINARY_SIGILS[owner.name]} {rhs})"
    if isinstance(owner, arith.CmpiOp):
        predicate = owner.predicate.value.data
        if predicate not in _CMPI_SIGILS:
            raise _emit_error(ctx, owner.name, "unsupported comparison predicate")
        lhs = emit_c_value(owner.lhs, ctx)
        rhs = emit_c_value(owner.rhs, ctx)
        return f"({lhs} {_CMPI_SIGILS[predicate]} {rhs})"
    if isinstance(owner, DmaLoadOp):
        return _emit_dma_load_expr(owner, ctx)
    raise _emit_error(ctx, owner.name, f"invalid dependency for value {value}")


def _emit_assignment(op: Operation, ctx: EmitCContext) -> str:
    result = op.results[0]
    result_type = _type_to_c(result.type, ctx)
    if isinstance(op, DmaLoadOp) and isinstance(result.type, NnMemoryType) and _is_unit_tile(result.type):
        result_type = _type_to_c(result.type.element_type, ctx)
    expr = emit_c_value(result, ctx)
    result_name = ctx.allocate_name(result)
    return f"{ctx.current_indent}{result_type} {result_name} = {expr};"


def _emit_loop_region(
    lower: SSAValue,
    upper: SSAValue,
    step: SSAValue,
    block: Any,
    ctx: EmitCContext,
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
        f"{ctx.current_indent}for (long long {iv_name} = {lower_expr}; {iv_name} < {upper_expr}; {iv_name} += {step_expr}) {{"
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
    - 在 `target=cpu` 下生成与 `scf.for` 同风格的循环结构。
    - 迭代变量命名由 `EmitCContext.allocate_name(..., prefix=\"i\")` 分配，确保稳定且避免冲突。

    使用示例:
    - stmt = emit_c_op(symbol_for_op, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if ctx.target != "cpu":
        raise _emit_error(ctx, op.name, "symbol loops are cpu-only")
    return _emit_loop_region(op.start, op.end, op.step, op.body.block, ctx)


def emit_c_op(op: Operation, ctx: EmitCContext) -> str:
    """把单个 MLIR op 生成为目标后端的语句或语句块文本。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 负责把单个 op 转换为赋值语句、控制流语句块、访存语句、memory 视图声明或 CPU helper 调用片段。
    - 本阶段新增的 `symbol.for/dma.alloc/view/slice/deslice/nn.img2col2d` 仅支持 `target=cpu`。
    - `nn.add` 仅支持 `target=cpu` 且 `result` 已预绑定名称的节点级 `cpu::add(...)` 发射。

    使用示例:
    - stmt = emit_c_op(op, EmitCContext(target=\"cpu\"))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: kernel_gen/dsl/emit_c.py
    """

    if op.name in _BINARY_SIGILS or isinstance(op, arith.CmpiOp):
        return _emit_assignment(op, ctx)
    if isinstance(op, DmaAllocOp):
        return _emit_dma_alloc_stmt(op, ctx)
    if isinstance(op, DmaLoadOp):
        return _emit_assignment(op, ctx)
    if isinstance(op, DmaStoreOp):
        return _emit_dma_store_stmt(op, ctx)
    if isinstance(op, DmaSliceOp):
        return _emit_dma_slice_stmt(op, ctx)
    if isinstance(op, DmaDesliceOp):
        return _emit_dma_deslice_stmt(op, ctx)
    if isinstance(op, DmaViewOp):
        return _emit_dma_view_stmt(op, ctx)
    if isinstance(op, arith.ConstantOp):
        return ""
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
