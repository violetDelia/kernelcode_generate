"""dma-alias-to-reinterpret pass.

功能说明:
- 提供 `dma-alias-to-reinterpret` pass，把 `dma.view`、`dma.reshape` 与 `dma.subview`
  归一为 root source 上的 `dma.reinterpret`。
- pass 沿 `dma.view` / `dma.reshape` / `dma.subview` / `dma.reinterpret` alias 链追到 root source，
  并组合线性 offset，避免生成嵌套 alias。
- 无法物化 exact offset、shape 或 stride operand 时保持 no-op；module verifier 失败时回滚。

API 列表:
- `class DmaAliasToReinterpretPass(fold: bool = True)`
- `DmaAliasToReinterpretPass.name: str`
- `DmaAliasToReinterpretPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.dma_alias_to_reinterpret import DmaAliasToReinterpretPass
- DmaAliasToReinterpretPass().apply(Context(), module)

关联文件:
- spec: spec/pass/dma_alias_to_reinterpret.md
- test: test/passes/test_dma_alias_to_reinterpret.py
- 功能实现: kernel_gen/passes/dma_alias_to_reinterpret.py
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntegerType, ModuleOp
from xdsl.ir import Attribute, Block, BlockArgument, Operation, SSAValue
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import DmaReinterpretOp, DmaReshapeOp, DmaSubviewOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import Symbol, SymbolAddOp, SymbolConstOp, SymbolExprAttr, SymbolIterType, SymbolMulOp, SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass


@dataclass(frozen=True)
class _SymbolMaterial:
    """当前文件内 symbol SSA material。

    功能说明:
    - 绑定一个 `!symbol.int` 或 `!symbol.iter` SSA value 及其公开表达文本。
    - 仅服务本 pass 的 offset/stride 物化，不作为公开 API。

    使用示例:
    - material = _SymbolMaterial(value, "I*N")

    关联文件:
    - spec: spec/pass/dma_alias_to_reinterpret.md
    - test: test/passes/test_dma_alias_to_reinterpret.py
    - 功能实现: kernel_gen/passes/dma_alias_to_reinterpret.py
    """

    value: SSAValue
    expr_text: str


@dataclass(frozen=True)
class _AliasInfo:
    """alias 链 root 与 base offset。

    功能说明:
    - `root` 是最早的 non-alias source。
    - `offset` 已按 `root` 的 offset 单位表达；root 为 i8 byte pool 时单位为 byte，否则为 root element。
    - `ops` 是为了物化 offset 需要插到当前 alias op 前的 symbol op。
    - `cleanup_ops` 是 source alias 链上的旧 alias op，终端 rewrite 后若无 use 可删除。

    使用示例:
    - info = _AliasInfo(root, offset, tuple(new_ops))

    关联文件:
    - spec: spec/pass/dma_alias_to_reinterpret.md
    - test: test/passes/test_dma_alias_to_reinterpret.py
    - 功能实现: kernel_gen/passes/dma_alias_to_reinterpret.py
    """

    root: SSAValue
    offset: _SymbolMaterial
    ops: tuple[Operation, ...]
    cleanup_ops: tuple[Operation, ...]


@dataclass(frozen=True)
class _RewritePlan:
    """单个 alias op 的 reinterpret rewrite 计划。

    功能说明:
    - `ops` 包含需插在 `dma.reinterpret` 前的 symbol op。
    - `reinterpret` 是替换原 alias op 的新 memory alias op。
    - `cleanup_ops` 是该 rewrite 后可尝试删除的 source alias 链中间节点。

    使用示例:
    - plan = _RewritePlan((*symbol_ops, reinterpret), reinterpret)

    关联文件:
    - spec: spec/pass/dma_alias_to_reinterpret.md
    - test: test/passes/test_dma_alias_to_reinterpret.py
    - 功能实现: kernel_gen/passes/dma_alias_to_reinterpret.py
    """

    ops: tuple[Operation, ...]
    reinterpret: DmaReinterpretOp
    cleanup_ops: tuple[Operation, ...]


def _is_zero(material: _SymbolMaterial) -> bool:
    """判断 material 是否为公开常量 0。

    功能说明:
    - 只读取 symbol 表达文本，避免依赖 SSA 名称或 IR 打印。

    使用示例:
    - if _is_zero(offset): ...
    """

    return material.expr_text == "0"


def _is_one(material: _SymbolMaterial) -> bool:
    """判断 material 是否为公开常量 1。

    功能说明:
    - 用于消除乘以 1 的无意义 symbol op。

    使用示例:
    - if _is_one(stride): ...
    """

    return material.expr_text == "1"


def _symbol_operand_expr_text(value: SSAValue) -> str | None:
    """读取 symbol operand 的公开表达文本。

    功能说明:
    - `!symbol.int` 返回 `SymbolValueType.get_value()`。
    - `!symbol.iter` 转成公开 `iter<start,end,step>` token，供 symbol 算术 result type 使用。
    - 其它 operand 返回 None，调用方保持 no-op。

    使用示例:
    - text = _symbol_operand_expr_text(value)
    """

    value_type = SSAValue.get(value).type
    if isinstance(value_type, SymbolValueType):
        return str(value_type.get_value())
    if isinstance(value_type, SymbolIterType):
        return (
            "iter<"
            f"{value_type.start.expr.data},"
            f"{value_type.end.expr.data},"
            f"{value_type.step.expr.data}>"
        )
    return None


def _material_from_operand(value: SSAValue) -> _SymbolMaterial | None:
    """把已有 symbol operand 包装成 material。

    功能说明:
    - 不新增 IR，只保留 value 与公开表达文本。
    - 非 symbol operand 返回 None，使当前 rewrite no-op。

    使用示例:
    - material = _material_from_operand(op.offset)
    """

    expr_text = _symbol_operand_expr_text(SSAValue.get(value))
    if expr_text is None:
        return None
    return _SymbolMaterial(SSAValue.get(value), expr_text)


def _parenthesize_factor(expr_text: str) -> str:
    """为乘法表达式拼接准备 factor。

    功能说明:
    - 简单整数、标识符和 `iter<...>` token 原样保留。
    - 复合加减表达式加括号，交给 `SymbolValueType.from_expr(...)` 做最终 canonical 化。

    使用示例:
    - text = _parenthesize_factor("I*N + J")
    """

    if expr_text == "?" or expr_text.lstrip("-").isdigit():
        return expr_text
    if expr_text.replace("_", "").isalnum():
        return expr_text
    if expr_text.startswith("iter<") and expr_text.endswith(">"):
        return expr_text
    return f"({expr_text})"


def _const_material(value: int) -> tuple[SymbolConstOp, _SymbolMaterial]:
    """构造 symbol.const material。

    功能说明:
    - 用于缺少支配当前 alias op 的静态 stride/offset SSA 时物化常量。

    使用示例:
    - op, material = _const_material(0)
    """

    op = SymbolConstOp(value)
    return op, _SymbolMaterial(op.result, str(value))


def _mul_material(lhs: _SymbolMaterial, rhs: _SymbolMaterial) -> tuple[tuple[Operation, ...], _SymbolMaterial]:
    """物化两个 symbol material 的乘积。

    功能说明:
    - 消除乘以 0/1 的冗余 op。
    - 非平凡乘法生成 `symbol.mul`，result type 使用公开 symbol 表达式。

    使用示例:
    - ops, material = _mul_material(offset, stride)
    """

    if _is_zero(lhs) or _is_zero(rhs):
        op, material = _const_material(0)
        return (op,), material
    if _is_one(lhs):
        return (), rhs
    if _is_one(rhs):
        return (), lhs
    if lhs.expr_text.lstrip("-").isdigit() and rhs.expr_text.lstrip("-").isdigit():
        op, material = _const_material(int(lhs.expr_text) * int(rhs.expr_text))
        return (op,), material
    expr = f"{_parenthesize_factor(lhs.expr_text)}*{_parenthesize_factor(rhs.expr_text)}"
    op = SymbolMulOp(lhs.value, rhs.value, SymbolValueType.from_expr(expr))
    return (op,), _SymbolMaterial(op.result, str(op.result.type.get_value()))


def _add_material(lhs: _SymbolMaterial, rhs: _SymbolMaterial) -> tuple[tuple[Operation, ...], _SymbolMaterial]:
    """物化两个 symbol material 的和。

    功能说明:
    - 消除加 0 的冗余 op。
    - 非平凡加法生成 `symbol.add`，result type 使用公开 symbol 表达式。

    使用示例:
    - ops, material = _add_material(base, inner)
    """

    if _is_zero(lhs):
        return (), rhs
    if _is_zero(rhs):
        return (), lhs
    if lhs.expr_text.lstrip("-").isdigit() and rhs.expr_text.lstrip("-").isdigit():
        op, material = _const_material(int(lhs.expr_text) + int(rhs.expr_text))
        return (op,), material
    op = SymbolAddOp(lhs.value, rhs.value, SymbolValueType.from_expr(f"{lhs.expr_text} + {rhs.expr_text}"))
    return (op,), _SymbolMaterial(op.result, str(op.result.type.get_value()))


def _value_dominates_op(value: SSAValue, op: Operation) -> bool:
    """判断 value 是否在 op 之前可见。

    功能说明:
    - 支持当前 block、ancestor block 参数以及当前 block 或 ancestor block 中位于 op 前的 producer。
    - sibling/descendant region 中的 value 保守视为不可见。

    使用示例:
    - if _value_dominates_op(stride_value, view_op): ...
    """

    op_block = op.parent_block()
    if op_block is None:
        return False
    if isinstance(value, BlockArgument):
        return value.owner is op_block or value.owner.is_ancestor(op)
    owner = value.owner
    if not isinstance(owner, Operation):
        return True
    owner_block = owner.parent_block()
    if owner_block is None:
        return True
    if owner_block is op_block:
        return owner.is_before_in_block(op)
    ancestor = owner_block.find_ancestor_op_in_block(op)
    if ancestor is None or owner is ancestor:
        return False
    return owner.is_before_in_block(ancestor)


def _root_operation(op: Operation) -> Operation:
    """返回 op 所在 IR 树的顶层 operation。

    功能说明:
    - 用于在当前 module / func 范围内查找可见的同表达 symbol value。

    使用示例:
    - root = _root_operation(op)
    """

    current = op
    block = current.parent_block()
    while block is not None and block.parent_op() is not None:
        current = block.parent_op()
        block = current.parent_block()
    return current


def _ancestor_blocks(op: Operation) -> tuple[Block, ...]:
    """收集 op 所在 block 与 ancestor block。

    功能说明:
    - block 参数是 symbol 值的常见来源，必须参与可见值查找。

    使用示例:
    - blocks = _ancestor_blocks(op)
    """

    blocks: list[Block] = []
    block = op.parent_block()
    while block is not None:
        blocks.append(block)
        parent = block.parent_op()
        block = parent.parent_block() if parent is not None else None
    return tuple(blocks)


def _find_visible_symbol_value_by_expr(expr_text: str, anchor: Operation) -> SSAValue | None:
    """查找支配 anchor 的同表达 symbol SSA。

    功能说明:
    - 优先返回 block/func/loop 参数，再扫描顶层 operation 树中已支配 anchor 的 op result。
    - 不从 SSA name 反推语义，只比较 `SymbolValueType.get_value()`。

    使用示例:
    - value = _find_visible_symbol_value_by_expr("N", view_op)
    """

    for block in _ancestor_blocks(anchor):
        for arg in block.args:
            if isinstance(arg.type, SymbolValueType) and str(arg.type.get_value()) == expr_text:
                return arg
    for op in _root_operation(anchor).walk():
        for result in op.results:
            if (
                isinstance(result.type, SymbolValueType)
                and str(result.type.get_value()) == expr_text
                and _value_dominates_op(result, anchor)
            ):
                return result
    return None


def _materialize_expr(expr_text: str, anchor: Operation) -> tuple[tuple[Operation, ...], _SymbolMaterial] | None:
    """为表达式获取可用于 anchor 前的 symbol material。

    功能说明:
    - 可见的同表达 SSA 直接复用。
    - 静态整数字面量缺失时物化 `symbol.const`。
    - 动态表达式缺少可见 SSA 时返回 None，使 rewrite no-op。

    使用示例:
    - material = _materialize_expr("N", op)
    """

    visible = _find_visible_symbol_value_by_expr(expr_text, anchor)
    if visible is not None:
        return (), _SymbolMaterial(visible, expr_text)
    if expr_text.lstrip("-").isdigit():
        op, material = _const_material(int(expr_text))
        return (op,), material
    return None


def _symbol_expr_attr_text(attr: Attribute) -> str | None:
    """读取 SymbolExprAttr 文本。

    功能说明:
    - 非 SymbolExprAttr 返回 None，当前 pass 保持 no-op。

    使用示例:
    - text = _symbol_expr_attr_text(memory_type.stride.data[0])
    """

    if not isinstance(attr, SymbolExprAttr):
        return None
    return attr.expr.data


def _materialize_layout(layout: Sequence[Attribute], anchor: Operation) -> tuple[tuple[Operation, ...], tuple[_SymbolMaterial, ...]] | None:
    """物化 memory layout 对应的 symbol operands。

    功能说明:
    - 每个 layout 维度必须是 `SymbolExprAttr`，并能找到可见 SSA 或物化为静态 const。
    - 用于 `dma.reinterpret` 的 stride operand 生成。

    使用示例:
    - ops, strides = _materialize_layout(result_type.stride.data, op)
    """

    ops: list[Operation] = []
    values: list[_SymbolMaterial] = []
    for attr in layout:
        expr_text = _symbol_expr_attr_text(attr)
        if expr_text is None:
            return None
        materialized = _materialize_expr(expr_text, anchor)
        if materialized is None:
            return None
        new_ops, material = materialized
        ops.extend(new_ops)
        values.append(material)
    return tuple(ops), tuple(values)


def _memory_type(value: SSAValue) -> NnMemoryType | None:
    """读取 SSA value 的 nn.memory 类型。

    功能说明:
    - 非 memory value 返回 None，让当前 rewrite no-op。

    使用示例:
    - mem_type = _memory_type(op.source)
    """

    value_type = SSAValue.get(value).type
    return value_type if isinstance(value_type, NnMemoryType) else None


def _element_byte_size(element_type: Attribute) -> int | None:
    """解析 memory element 的 byte size。

    功能说明:
    - 只在当前 pass 内用于 byte-pool root offset 单位转换。
    - 支持仓库公开 numeric dtype 集合。

    使用示例:
    - size = _element_byte_size(memory_type.element_type)
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


def _is_i8_byte_pool(memory_type: NnMemoryType) -> bool:
    """判断 memory type 是否为一维 i8 byte pool。

    功能说明:
    - 当前 pass 只需要公开类型结构判断 offset 单位，不跨文件调用 dma package 内部 helper。

    使用示例:
    - if _is_i8_byte_pool(root_type): ...
    """

    element_type = memory_type.element_type
    return (
        len(memory_type.shape.data) == 1
        and isinstance(element_type, IntegerType)
        and int(element_type.width.data) == 8
    )


def _alias_source_value(op: Operation) -> SSAValue | None:
    """读取受支持 alias op 的 source value。

    功能说明:
    - `dma.view`、`dma.reshape`、`dma.reinterpret` 使用单 source。
    - `dma.subview` 的 source 是一元素 variadic segment。

    使用示例:
    - source = _alias_source_value(alias_op)
    """

    if isinstance(op, (DmaViewOp, DmaReshapeOp, DmaReinterpretOp)):
        return SSAValue.get(op.source)
    if isinstance(op, DmaSubviewOp) and len(op.source) == 1:
        return SSAValue.get(op.source[0])
    return None


def _combine_offsets(
    base: _SymbolMaterial,
    inner: _SymbolMaterial,
    *,
    root_type: NnMemoryType,
    inner_source_type: NnMemoryType,
) -> tuple[tuple[Operation, ...], _SymbolMaterial] | None:
    """组合 root base offset 与当前层 offset。

    功能说明:
    - root 为 i8 byte pool 且当前 source 是 typed memory 时，当前层 offset 先乘以 source element byte size。
    - 其它场景直接相加。

    使用示例:
    - ops, offset = _combine_offsets(base, own, root_type=root_type, inner_source_type=source_type)
    """

    ops: list[Operation] = []
    scaled_inner = inner
    if _is_i8_byte_pool(root_type) and not _is_i8_byte_pool(inner_source_type) and not _is_zero(inner):
        size = _element_byte_size(inner_source_type.element_type)
        if size is None:
            return None
        const_op, size_material = _const_material(size)
        mul_ops, scaled_inner = _mul_material(inner, size_material)
        ops.append(const_op)
        ops.extend(mul_ops)
    add_ops, result = _add_material(base, scaled_inner)
    ops.extend(add_ops)
    return tuple(ops), result


def _view_offset_material(op: DmaViewOp) -> tuple[tuple[Operation, ...], _SymbolMaterial] | None:
    """计算 `dma.view` 相对 source 的线性 offset。

    功能说明:
    - offset 按 source physical stride 线性化。
    - 任一 source stride 无法物化时保持 no-op。

    使用示例:
    - ops, offset = _view_offset_material(view_op)
    """

    source_type = _memory_type(SSAValue.get(op.source))
    if source_type is None or len(source_type.stride.data) != len(op.offsets):
        return None
    stride_materialized = _materialize_layout(source_type.stride.data, op)
    if stride_materialized is None:
        return None
    stride_ops, stride_values = stride_materialized
    ops: list[Operation] = list(stride_ops)
    zero_materialized = _materialize_expr("0", op)
    if zero_materialized is None:
        return None
    zero_ops, current = zero_materialized
    ops.extend(zero_ops)
    for offset_value, stride_value in zip(op.offsets, stride_values, strict=True):
        offset = _material_from_operand(SSAValue.get(offset_value))
        if offset is None:
            return None
        if _is_zero(offset):
            continue
        mul_ops, term = _mul_material(offset, stride_value)
        ops.extend(mul_ops)
        add_ops, current = _add_material(current, term)
        ops.extend(add_ops)
    return tuple(ops), current


def _zero_offset_material(anchor: Operation) -> tuple[tuple[Operation, ...], _SymbolMaterial] | None:
    """返回支配 anchor 的 zero offset material。

    功能说明:
    - reshape 没有局部 offset，统一使用 0。

    使用示例:
    - ops, zero = _zero_offset_material(reshape_op)
    """

    return _materialize_expr("0", anchor)


def _single_operand_material(values: Sequence[SSAValue], field_name: str) -> _SymbolMaterial | None:
    """读取单元素 operand segment 的 symbol material。

    功能说明:
    - `dma.subview` 的 offset/size/stride 均为单元素 segment。
    - 长度不为 1 时保持 no-op。

    使用示例:
    - offset = _single_operand_material(op.offset, "offset")
    """

    _ = field_name
    if len(values) != 1:
        return None
    return _material_from_operand(SSAValue.get(values[0]))


def _source_alias_info(value: SSAValue, anchor: Operation, visited: frozenset[Operation]) -> _AliasInfo | None:
    """沿 alias 链追踪 root source 与 base offset。

    功能说明:
    - 支持 `dma.view`、`dma.reshape`、`dma.subview` 与 `dma.reinterpret`。
    - 遇到自环、非 memory 或无法物化 offset 时保持 no-op。

    使用示例:
    - info = _source_alias_info(op.source, op, frozenset())
    """

    root_type = _memory_type(value)
    if root_type is None:
        return None
    owner = value.owner
    if not isinstance(owner, Operation) or not isinstance(owner, (DmaViewOp, DmaReshapeOp, DmaSubviewOp, DmaReinterpretOp)):
        zero = _zero_offset_material(anchor)
        if zero is None:
            return None
        zero_ops, zero_material = zero
        return _AliasInfo(value, zero_material, tuple(zero_ops), ())
    if owner in visited:
        return None
    source = _alias_source_value(owner)
    if source is None:
        return None
    parent_info = _source_alias_info(source, anchor, visited | frozenset((owner,)))
    if parent_info is None:
        return None
    source_type = _memory_type(source)
    parent_root_type = _memory_type(parent_info.root)
    if source_type is None or parent_root_type is None:
        return None
    own_offset = _own_offset_material(owner)
    if own_offset is None:
        return None
    own_ops, own_material = own_offset
    combined = _combine_offsets(
        parent_info.offset,
        own_material,
        root_type=parent_root_type,
        inner_source_type=source_type,
    )
    if combined is None:
        return None
    combined_ops, combined_material = combined
    return _AliasInfo(
        parent_info.root,
        combined_material,
        (*parent_info.ops, *own_ops, *combined_ops),
        (*parent_info.cleanup_ops, owner),
    )


def _own_offset_material(op: Operation) -> tuple[tuple[Operation, ...], _SymbolMaterial] | None:
    """计算单层 alias op 相对自身 source 的 offset。

    功能说明:
    - `dma.reshape` 使用 0。
    - `dma.view` 使用 source physical stride 线性化 offset。
    - `dma.subview` / `dma.reinterpret` 直接使用其 offset operand。

    使用示例:
    - ops, offset = _own_offset_material(op)
    """

    if isinstance(op, DmaReshapeOp):
        return _zero_offset_material(op)
    if isinstance(op, DmaViewOp):
        return _view_offset_material(op)
    if isinstance(op, DmaSubviewOp):
        offset = _single_operand_material(tuple(op.offset), "offset")
        if offset is None:
            return None
        return (), offset
    if isinstance(op, DmaReinterpretOp):
        offset = _material_from_operand(SSAValue.get(op.offset))
        if offset is None:
            return None
        return (), offset
    return None


def _rewrite_plan(
    op: DmaViewOp | DmaReshapeOp | DmaSubviewOp,
    shape_operands: Sequence[SSAValue],
) -> _RewritePlan | None:
    """构造 alias op 到 `dma.reinterpret` 的 rewrite 计划。

    功能说明:
    - 追踪 source alias root 并组合 offset。
    - shape 复用原 alias op 的公开 shape/size operand。
    - stride 从 result type 物化，确保 `dma.reinterpret` verifier 的 result type 是合同真源。

    使用示例:
    - plan = _rewrite_plan(view_op, view_op.shape)
    """

    source = _alias_source_value(op)
    if source is None:
        return None
    source_info = _source_alias_info(source, op, frozenset())
    if source_info is None:
        return None
    source_type = _memory_type(source)
    root_type = _memory_type(source_info.root)
    result_type = _memory_type(SSAValue.get(op.result))
    if source_type is None or root_type is None or result_type is None:
        return None
    own_offset = _own_offset_material(op)
    if own_offset is None:
        return None
    own_ops, own_material = own_offset
    combined = _combine_offsets(
        source_info.offset,
        own_material,
        root_type=root_type,
        inner_source_type=source_type,
    )
    if combined is None:
        return None
    offset_ops, offset = combined
    stride_materialized = _materialize_layout(result_type.stride.data, op)
    if stride_materialized is None:
        return None
    stride_ops, stride_values = stride_materialized
    reinterpret = DmaReinterpretOp(
        source_info.root,
        offset.value,
        tuple(SSAValue.get(value) for value in shape_operands),
        tuple(material.value for material in stride_values),
        result_type,
    )
    try:
        reinterpret.verify()
    except VerifyException:
        return None
    return _RewritePlan(
        (*source_info.ops, *own_ops, *offset_ops, *stride_ops, reinterpret),
        reinterpret,
        source_info.cleanup_ops,
    )


def _erase_dead_cleanup_ops(rewriter: PatternRewriter, ops: Sequence[Operation]) -> None:
    """删除 source alias 链上已无 use 的中间 alias op。

    功能说明:
    - 只清理当前 rewrite 证明为 source alias 链的 op，不做全局 DCE。
    - 保留终端 `dma.reinterpret`，即使其结果暂时未使用，也能被 ircheck 合同观察。

    使用示例:
    - _erase_dead_cleanup_ops(rewriter, plan.cleanup_ops)
    """

    for op in reversed(ops):
        if op.parent_block() is None:
            continue
        if any(result.uses for result in op.results):
            continue
        rewriter.erase_op(op)


class _DmaViewToReinterpretPattern(RewritePattern):
    """`dma.view` 到 `dma.reinterpret` 的私有 pattern。

    功能说明:
    - 仅在 offset/shape/stride 可 exact 物化时改写。

    使用示例:
    - pattern = _DmaViewToReinterpretPattern()
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaViewOp, rewriter: PatternRewriter, /) -> None:
        plan = _rewrite_plan(op, tuple(op.shape))
        if plan is None:
            return
        rewriter.replace_matched_op(plan.ops, [plan.reinterpret.result])
        _erase_dead_cleanup_ops(rewriter, plan.cleanup_ops)


class _DmaReshapeToReinterpretPattern(RewritePattern):
    """`dma.reshape` 到 `dma.reinterpret` 的私有 pattern。

    功能说明:
    - reshape 的局部 offset 固定为 0；source 若为 alias 会继续追到 root。

    使用示例:
    - pattern = _DmaReshapeToReinterpretPattern()
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaReshapeOp, rewriter: PatternRewriter, /) -> None:
        plan = _rewrite_plan(op, tuple(op.shape))
        if plan is None:
            return
        rewriter.replace_matched_op(plan.ops, [plan.reinterpret.result])
        _erase_dead_cleanup_ops(rewriter, plan.cleanup_ops)


class _DmaSubviewToReinterpretPattern(RewritePattern):
    """`dma.subview` 到 `dma.reinterpret` 的私有 pattern。

    功能说明:
    - subview 的 offset/size/stride 原样进入 `dma.reinterpret`，source alias 会继续追到 byte pool root。

    使用示例:
    - pattern = _DmaSubviewToReinterpretPattern()
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaSubviewOp, rewriter: PatternRewriter, /) -> None:
        plan = _rewrite_plan(op, tuple(op.size))
        if plan is None:
            return
        rewriter.replace_matched_op(plan.ops, [plan.reinterpret.result])
        _erase_dead_cleanup_ops(rewriter, plan.cleanup_ops)


def _rewrite_module(ctx: Context, module: ModuleOp) -> None:
    """对 module 执行 alias-to-reinterpret rewrite。

    功能说明:
    - 使用 greedy walker 收敛三类 alias op。
    - 不在 pass 内执行 DCE；pipeline 级死代码清理由 PassManager 的通用 fold 开关控制。
    - 保留未使用但可归一化的 alias 结果，便于 ircheck 合同观察 pass 的直接 rewrite 结果。

    使用示例:
    - _rewrite_module(ctx, module)
    """

    PatternRewriteWalker(
        GreedyRewritePatternApplier(
            [
                _DmaViewToReinterpretPattern(),
                _DmaReshapeToReinterpretPattern(),
                _DmaSubviewToReinterpretPattern(),
            ],
            ctx=ctx,
            folding_enabled=True,
            dce_enabled=False,
        )
    ).rewrite_module(module)


def _replace_module_body(target: ModuleOp, source: ModuleOp) -> None:
    """把 source module body 移入 target。

    功能说明:
    - rewrite 在 clone 上完成并验证通过后才替换原 module body。
    - 该步骤保证 verifier 失败时原 module 文本保持不变。

    使用示例:
    - _replace_module_body(original, rewritten_clone)
    """

    for block in list(target.body.blocks):
        target.body.erase_block(block, safe_erase=False)
    source.body.move_blocks(target.body)


class DmaAliasToReinterpretPass(Pass):
    """dma alias 归一化 pass。

    功能说明:
    - 固定公开 pass name 为 `dma-alias-to-reinterpret`。
    - 把 `dma.view` / `dma.reshape` / `dma.subview` 改写为 root source 上的单个 `dma.reinterpret`。
    - 对无法 exact 物化的 alias 保持 no-op；module verifier 失败时回滚并报稳定错误。

    使用示例:
    - DmaAliasToReinterpretPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/dma_alias_to_reinterpret.md
    - test: test/passes/test_dma_alias_to_reinterpret.py
    - 功能实现: kernel_gen/passes/dma_alias_to_reinterpret.py
    """

    name = "dma-alias-to-reinterpret"

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 `dma-alias-to-reinterpret`。

        功能说明:
        - 在 clone 上执行 rewrite，验证成功后替换原 module body。
        - 确保 `Symbol` dialect 已加载，使新增 `symbol.add/mul/const` 可验证。

        使用示例:
        - DmaAliasToReinterpretPass(fold=False).apply(Context(), module)

        关联文件:
        - spec: spec/pass/dma_alias_to_reinterpret.md
        - test: test/passes/test_dma_alias_to_reinterpret.py
        - 功能实现: kernel_gen/passes/dma_alias_to_reinterpret.py
        """

        module = ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        rewritten = module.clone()
        try:
            _rewrite_module(ctx, rewritten)
            rewritten.verify()
        except VerifyException as exc:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"DmaAliasToReinterpretVerifierError: {exc}",
            ) from exc
        _replace_module_body(module, rewritten)


__all__ = ["DmaAliasToReinterpretPass"]
