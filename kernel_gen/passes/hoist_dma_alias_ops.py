"""hoist-dma-alias-ops pass.

功能说明:
- 提供 `hoist-dma-alias-ops` pass。
- 第一阶段只识别同一 block 内紧邻的 `dma.fill(%src, value)` 与
  `%alias = dma.reshape(%src, ...)`，并在 shape operand 已支配 `dma.fill` 时把
  `dma.reshape` 上移到 `dma.fill` 前，同时把 `dma.fill` target 改为 alias result。
- 扩展识别紧邻的 `dma.view` + `dma.deslice` 连续后缀维度分组，把可证明安全的高维
  view/deslice 降维为 reshape 后的一组低维 view/deslice。
- 变换通过当前文件公开 `RewritePattern` 与 `PatternRewriteWalker` 驱动。
- 不做 fold/combine/canonicalize，不跨 block、region 或控制流移动。

API 列表:
- `class DmaViewDesliceGroupingPattern(module: ModuleOp)`
- `DmaViewDesliceGroupingPattern.match_and_rewrite(op: DmaViewOp, rewriter: PatternRewriter) -> None`
- `class DmaReshapeThroughFillPattern(module: ModuleOp)`
- `DmaReshapeThroughFillPattern.match_and_rewrite(op: DmaReshapeOp, rewriter: PatternRewriter) -> None`
- `get_hoist_dma_alias_ops_pass_patterns(module: ModuleOp) -> list[RewritePattern]`
- `class HoistDmaAliasOpsPass(fold: bool = True)`
- `HoistDmaAliasOpsPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.hoist_dma_alias_ops import HoistDmaAliasOpsPass
- HoistDmaAliasOpsPass().apply(Context(), module)

关联文件:
- spec: [spec/pass/hoist_dma_alias_ops.md](spec/pass/hoist_dma_alias_ops.md)
- test: [test/passes/test_hoist_dma_alias_ops.py](test/passes/test_hoist_dma_alias_ops.py)
- 功能实现: [kernel_gen/passes/hoist_dma_alias_ops.py](kernel_gen/passes/hoist_dma_alias_ops.py)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, IntegerType, ModuleOp
from xdsl.ir import Attribute, Block, BlockArgument, Operation, SSAValue
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaDesliceOp, DmaFillOp, DmaReshapeOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolMulOp, SymbolValueType
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass


def _same_value(candidate: SSAValue | Operation, value: SSAValue | Operation) -> bool:
    """判断两个 operand / result 是否指向同一个 SSA value。

    功能说明:
    - 统一处理 xDSL operand 可能传入 `Operation` 或 `SSAValue` 的形态。

    使用示例:
    - if _same_value(fill.target, reshape.source): ...
    """

    return SSAValue.get(candidate) is SSAValue.get(value)


def _value_dominates_op(value: SSAValue, op: Operation) -> bool:
    """判断 value 是否在 op 之前可见。

    功能说明:
    - 接受同 block 中位于 `op` 之前的 operation result。
    - 接受当前 block 或 ancestor block 的 block argument。
    - 对 sibling / descendant region 中的 value 保守返回 False，避免跨控制流移动。

    使用示例:
    - if all(_value_dominates_op(shape, fill) for shape in reshape.shape): ...
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


@dataclass(frozen=True)
class _ViewGroupingCandidate:
    """`dma.view + dma.deslice` 连续维度分组候选。

    功能说明:
    - 保存通过静态证明的 view/deslice 对、折叠起点与相关 memory type。
    - 仅供当前文件内 rewrite pattern 使用，不作为公开 API。

    使用示例:
    - candidate = _ViewGroupingCandidate(view, deslice, 1, source_type, target_type, view_type)
    """

    view: DmaViewOp
    deslice: DmaDesliceOp
    collapse_start: int
    source_type: NnMemoryType
    target_type: NnMemoryType
    view_type: NnMemoryType


@dataclass(frozen=True)
class _DesliceOperandGroups:
    """`dma.deslice` 的 offsets/sizes/strides operand 分组。

    功能说明:
    - 兼容文本 IR 中 `operandSegmentSizes` 打印为 target+source 合并段的形态。
    - 仅按公开 operand 顺序切片，不依赖跨文件私有解析 helper。

    使用示例:
    - groups = _deslice_operand_groups(deslice, rank)
    """

    offsets: tuple[SSAValue, ...]
    sizes: tuple[SSAValue, ...]
    strides: tuple[SSAValue, ...]


def _deslice_operand_groups(deslice: DmaDesliceOp, rank: int) -> _DesliceOperandGroups | None:
    """按 rank 从 `dma.deslice` operands 切出三组动态 operands。

    功能说明:
    - `dma.deslice` operand 顺序是 target、source、offsets、sizes、strides。
    - 文本解析得到的 segment property 可能不保留为 Python accessor 可读形态，本 pass 只依赖稳定公开 operand 顺序。

    使用示例:
    - groups = _deslice_operand_groups(deslice, 3)
    """

    expected_operand_count = 2 + rank * 3
    if len(deslice.operands) != expected_operand_count:
        return None
    offsets = tuple(deslice.operands[2 : 2 + rank])
    sizes = tuple(deslice.operands[2 + rank : 2 + rank * 2])
    strides = tuple(deslice.operands[2 + rank * 2 : 2 + rank * 3])
    return _DesliceOperandGroups(offsets, sizes, strides)


def _memory_type_of(value: SSAValue | Operation) -> NnMemoryType | None:
    """读取 SSA value 的公开 `NnMemoryType`。

    功能说明:
    - 统一处理 operand 可能传入 `Operation` 或 `SSAValue` 的形态。
    - 非 memory value 返回 `None`，供 pass 保守 no-op。

    使用示例:
    - source_type = _memory_type_of(view.source)
    """

    value_type = SSAValue.get(value).type
    return value_type if isinstance(value_type, NnMemoryType) else None


def _symbol_expr_attrs(attrs: ArrayAttr[Attribute]) -> tuple[SymbolExprAttr, ...] | None:
    """把 ArrayAttr 规整为 `SymbolExprAttr` tuple。

    功能说明:
    - 当前 rewrite 只接受结构化 `SymbolExprAttr` 布局。
    - 任一元素不是 `SymbolExprAttr` 时返回 `None`，避免文本 fallback。

    使用示例:
    - shape_attrs = _symbol_expr_attrs(memory_type.shape)
    """

    result: list[SymbolExprAttr] = []
    for attr in attrs.data:
        if not isinstance(attr, SymbolExprAttr):
            return None
        result.append(attr)
    return tuple(result)


def _symbol_expr_text(attr: SymbolExprAttr) -> str:
    """返回结构化 SymbolExprAttr 的 canonical 表达式文本。

    功能说明:
    - 只读取 `SymbolExprAttr` 自身公开承载的 canonical 文本。
    - 不使用 `repr`、IR dump 或 SSA name 作为匹配 fallback。

    使用示例:
    - expr = _symbol_expr_text(SymbolExprAttr.from_expr("N*K"))
    """

    return attr.expr.data


def _factor_expr(expr: str) -> str:
    """为乘法拼接准备单个表达式 factor。

    功能说明:
    - 对复杂表达式加括号，交给 `SymbolExprAttr.from_expr(...)` 做 canonical 化。

    使用示例:
    - text = f"{_factor_expr('N+1')}*K"
    """

    if expr.lstrip("-").isdigit() or expr.replace("_", "").isalnum() or expr == "?":
        return expr
    return f"({expr})"


def _product_expr_attr(attrs: Sequence[SymbolExprAttr]) -> SymbolExprAttr:
    """构造一组维度的乘积表达式属性。

    功能说明:
    - 乘积按从左到右的维度顺序生成，最终由 `SymbolExprAttr` canonical 化。
    - 空乘积返回 `1`，用于连续 stride 推导。

    使用示例:
    - attr = _product_expr_attr((SymbolExprAttr.from_expr("N"), SymbolExprAttr.from_expr("K")))
    """

    if not attrs:
        return SymbolExprAttr.from_expr("1")
    expr = _symbol_expr_text(attrs[0])
    for attr in attrs[1:]:
        expr = f"{_factor_expr(expr)}*{_factor_expr(_symbol_expr_text(attr))}"
    return SymbolExprAttr.from_expr(expr)


def _contiguous_stride_attrs(shape_attrs: Sequence[SymbolExprAttr]) -> tuple[SymbolExprAttr, ...]:
    """根据 shape 构造行主序 contiguous stride。

    功能说明:
    - 与 `NnMemoryType` 的公开 contiguous 语义保持一致。
    - 返回的每个元素都是结构化 `SymbolExprAttr`。

    使用示例:
    - strides = _contiguous_stride_attrs(shape_attrs)
    """

    result: list[SymbolExprAttr] = []
    for index in range(len(shape_attrs)):
        result.append(_product_expr_attr(shape_attrs[index + 1 :]))
    return tuple(result)


def _is_contiguous_memory_type(memory_type: NnMemoryType) -> bool:
    """判断 memory type 是否是行主序 contiguous。

    功能说明:
    - 只比较结构化 `SymbolExprAttr`，不做文本 fallback 或代数推导。
    - 不能证明时返回 False，让 rewrite 保守 no-op。

    使用示例:
    - if not _is_contiguous_memory_type(source_type): return None
    """

    shape_attrs = _symbol_expr_attrs(memory_type.shape)
    stride_attrs = _symbol_expr_attrs(memory_type.stride)
    if shape_attrs is None or stride_attrs is None:
        return False
    if len(shape_attrs) != len(stride_attrs):
        return False
    return stride_attrs == _contiguous_stride_attrs(shape_attrs)


def _is_i8_byte_pool_memory_type(memory_type: NnMemoryType) -> bool:
    """判断 memory type 是否是一维 i8 byte pool。

    功能说明:
    - 当前 pass 不处理 byte-pool typed view；该形态由 dma dialect verifier 与后续专项负责。
    - 只使用公开 `NnMemoryType` 字段与 xDSL `IntegerType`，不调用 dma dialect 私有 helper。

    使用示例:
    - if _is_i8_byte_pool_memory_type(source_type): return None
    """

    if len(memory_type.shape.data) != 1:
        return False
    element_type = memory_type.element_type
    return isinstance(element_type, IntegerType) and int(element_type.width.data) == 8


def _symbol_value_expr_attr(value: SSAValue | Operation) -> SymbolExprAttr | None:
    """读取 symbol/int operand 的结构化表达式属性。

    功能说明:
    - 仅接受 `SymbolValueType`。
    - `symbol.iter` 或其它类型不参与当前分组证明，保持 no-op。

    使用示例:
    - expr_attr = _symbol_value_expr_attr(offset)
    """

    value_type = SSAValue.get(value).type
    return value_type.expr if isinstance(value_type, SymbolValueType) else None


def _symbol_value_matches_attr(value: SSAValue | Operation, attr: SymbolExprAttr) -> bool:
    """判断 symbol operand 的类型表达式是否等于目标属性。

    功能说明:
    - 等价关系只来自公开 `SymbolValueType` 与 `SymbolExprAttr` 的结构化参数。
    - 不使用 SSA name、name_hint、dump 文本或字符串 fallback。

    使用示例:
    - if _symbol_value_matches_attr(size, source_shape_attr): ...
    """

    value_attr = _symbol_value_expr_attr(value)
    return value_attr == attr


def _symbol_value_is_expr(value: SSAValue | Operation, expr: str) -> bool:
    """判断 symbol operand 是否等于指定常量表达式。

    功能说明:
    - 用于校验 offset 为 0、stride 为 1 等公开整数边界。

    使用示例:
    - if _symbol_value_is_expr(stride, "1"): ...
    """

    return _symbol_value_matches_attr(value, SymbolExprAttr.from_expr(expr))


def _symbol_operands_match_attrs(values: Sequence[SSAValue], attrs: Sequence[SymbolExprAttr]) -> bool:
    """判断一组 symbol operands 是否逐项匹配目标表达式。

    功能说明:
    - 只做同长度逐项精确匹配。
    - 任一 operand 类型不是 `SymbolValueType` 时返回 False。

    使用示例:
    - if _symbol_operands_match_attrs(view.shape, view_shape_attrs): ...
    """

    if len(values) != len(attrs):
        return False
    return all(_symbol_value_matches_attr(value, attr) for value, attr in zip(values, attrs, strict=True))


def _find_dominating_symbol_value(block: Block, before_op: Operation, attr: SymbolExprAttr) -> SSAValue | None:
    """查找支配 before_op 且表达式匹配的公开 symbol value。

    功能说明:
    - 先查当前 block 参数，再查同 block 内 before_op 之前的 operation result。
    - 匹配依据仅为 `SymbolValueType` 的结构化表达式参数，不使用 SSA 名称。

    使用示例:
    - value = _find_dominating_symbol_value(block, view, SymbolExprAttr.from_expr("N"))
    """

    for arg in block.args:
        if _symbol_value_matches_attr(arg, attr):
            return arg
    for candidate in block.ops:
        if candidate is before_op:
            break
        for result in candidate.results:
            if _symbol_value_matches_attr(result, attr):
                return result
    return None


def _find_dominating_symbol_values(
    block: Block,
    before_op: Operation,
    attrs: Sequence[SymbolExprAttr],
) -> tuple[SSAValue, ...] | None:
    """查找一组支配 before_op 的 symbol values。

    功能说明:
    - 任一维度缺少可见 value 时返回 `None`，让 rewrite 保守 no-op。
    - 用于为新建 `dma.reshape` 构造公开 shape operands。

    使用示例:
    - operands = _find_dominating_symbol_values(block, view, source_shape_attrs)
    """

    values: list[SSAValue] = []
    for attr in attrs:
        value = _find_dominating_symbol_value(block, before_op, attr)
        if value is None:
            return None
        values.append(value)
    return tuple(values)


def _symbol_value_type_from_attr(attr: SymbolExprAttr) -> SymbolValueType:
    """根据 SymbolExprAttr 构造 symbol.int 类型。

    功能说明:
    - 统一通过公开 `SymbolValueType.from_expr(...)` 构造结果类型。

    使用示例:
    - result_type = _symbol_value_type_from_attr(SymbolExprAttr.from_expr("N*K"))
    """

    return SymbolValueType.from_expr(_symbol_expr_text(attr))


def _build_symbol_product(
    block: Block,
    before_op: Operation,
    operands: Sequence[SSAValue],
) -> tuple[tuple[Operation, ...], SSAValue] | None:
    """构造或复用一组 symbol operands 的乘积 value。

    功能说明:
    - 单 operand 直接复用。
    - 多 operand 先尝试复用已支配的同表达式 value，找不到时新建 `symbol.mul` 链。

    使用示例:
    - new_ops, inner = _build_symbol_product(block, view, (n, k))
    """

    if not operands:
        return None
    if len(operands) == 1:
        return (), operands[0]
    attrs: list[SymbolExprAttr] = []
    for operand in operands:
        attr = _symbol_value_expr_attr(operand)
        if attr is None:
            return None
        attrs.append(attr)
    product_attr = _product_expr_attr(attrs)
    existing = _find_dominating_symbol_value(block, before_op, product_attr)
    if existing is not None:
        return (), existing
    new_ops: list[Operation] = []
    current = operands[0]
    current_attr = attrs[0]
    for rhs, rhs_attr in zip(operands[1:], attrs[1:], strict=True):
        result_attr = _product_expr_attr((current_attr, rhs_attr))
        mul = SymbolMulOp(current, rhs, _symbol_value_type_from_attr(result_attr))
        new_ops.append(mul)
        current = mul.result
        current_attr = result_attr
    return tuple(new_ops), current


def _build_scaled_offset(
    block: Block,
    before_op: Operation,
    offset: SSAValue,
    tail_operands: Sequence[SSAValue],
) -> tuple[tuple[Operation, ...], SSAValue] | None:
    """构造折叠维度的线性 offset。

    功能说明:
    - offset 为 0 时直接复用 0，避免生成无意义 `0 * K`。
    - 其它情况用 offset 与被折叠尾部 source shape 乘积构造 `symbol.mul`。

    使用示例:
    - new_ops, collapsed_offset = _build_scaled_offset(block, view, n0, (k,))
    """

    if _symbol_value_is_expr(offset, "0") or not tail_operands:
        return (), offset
    tail_product = _build_symbol_product(block, before_op, tail_operands)
    if tail_product is None:
        return None
    tail_ops, tail_value = tail_product
    if _symbol_value_is_expr(tail_value, "1"):
        return tail_ops, offset
    offset_attr = _symbol_value_expr_attr(offset)
    tail_attr = _symbol_value_expr_attr(tail_value)
    if offset_attr is None or tail_attr is None:
        return None
    scaled_attr = _product_expr_attr((offset_attr, tail_attr))
    existing = _find_dominating_symbol_value(block, before_op, scaled_attr)
    if existing is not None:
        return tail_ops, existing
    mul = SymbolMulOp(offset, tail_value, _symbol_value_type_from_attr(scaled_attr))
    return tail_ops + (mul,), mul.result


def _memory_type_with_layout(
    shape_attrs: Sequence[SymbolExprAttr],
    stride_attrs: Sequence[SymbolExprAttr],
    base_type: NnMemoryType,
) -> NnMemoryType:
    """按指定 shape/stride 构造同 element/space/template 的 memory type。

    功能说明:
    - 保留原 memory 的 element_type、space 与 template_name。
    - 只改变 view grouping 需要的 rank 与布局。

    使用示例:
    - low_type = _memory_type_with_layout(shape_attrs, stride_attrs, source_type)
    """

    return NnMemoryType(
        ArrayAttr(list(shape_attrs)),
        ArrayAttr(list(stride_attrs)),
        base_type.element_type,
        base_type.space,
        base_type.template_name,
    )


def _collapsed_layout_attrs(
    shape_attrs: Sequence[SymbolExprAttr],
    collapse_start: int,
) -> tuple[SymbolExprAttr, ...]:
    """构造折叠后的低维 shape 属性。

    功能说明:
    - 保留 `[0, collapse_start)` 外层维度。
    - 把 `[collapse_start, rank)` 连续后缀折成一个乘积维度。

    使用示例:
    - low_shape = _collapsed_layout_attrs(shape_attrs, 1)
    """

    return tuple(shape_attrs[:collapse_start]) + (_product_expr_attr(shape_attrs[collapse_start:]),)


def _candidate_deslice(view: DmaViewOp) -> DmaDesliceOp | None:
    """返回紧邻且唯一消费 view result 的 deslice。

    功能说明:
    - 只接受同 block 内 `view.next_op` 即 `DmaDesliceOp`。
    - view result 必须只有这一个直接 use，deslice result 不允许被继续使用。

    使用示例:
    - deslice = _candidate_deslice(view)
    """

    uses = tuple(view.result.uses)
    if len(uses) != 1:
        return None
    use = uses[0]
    if use.index != 1:
        return None
    deslice = use.operation
    if not isinstance(deslice, DmaDesliceOp):
        return None
    if view.next_op is not deslice:
        return None
    if tuple(deslice.result.uses):
        return None
    return deslice


def _suffix_is_groupable(
    view: DmaViewOp,
    deslice: DmaDesliceOp,
    source_shape_attrs: Sequence[SymbolExprAttr],
    target_shape_attrs: Sequence[SymbolExprAttr],
    collapse_start: int,
) -> bool:
    """判断从 collapse_start 开始的后缀维度是否可分组。

    功能说明:
    - 内层维度必须完整覆盖 source/target 对应维度，offset 为 0，logical stride 为 1。
    - collapse_start 维度允许 view offset/size 动态，但 stride 必须为 1。
    - deslice 折叠维度从 target 低维 offset 0 写入，因此后缀 target offset 也必须为 0。

    使用示例:
    - if _suffix_is_groupable(view, deslice, source_shape_attrs, target_shape_attrs, 1): ...
    """

    rank = len(source_shape_attrs)
    if len(target_shape_attrs) != rank:
        return False
    if len(view.offsets) != rank or len(view.shape) != rank or len(view.stride) != rank:
        return False
    deslice_groups = _deslice_operand_groups(deslice, rank)
    if deslice_groups is None:
        return False
    if not all(_symbol_value_is_expr(stride, "1") for stride in view.stride):
        return False
    if not all(_symbol_value_is_expr(stride, "1") for stride in deslice_groups.strides):
        return False
    if any(not _symbol_value_is_expr(offset, "0") for offset in deslice_groups.offsets[collapse_start:]):
        return False
    for index in range(collapse_start + 1, rank):
        if not _symbol_value_is_expr(view.offsets[index], "0"):
            return False
        if not _symbol_value_matches_attr(view.shape[index], source_shape_attrs[index]):
            return False
        if not _symbol_value_matches_attr(deslice_groups.sizes[index], target_shape_attrs[index]):
            return False
    return True


def _find_view_collapse_start(
    view: DmaViewOp,
    deslice: DmaDesliceOp,
    source_shape_attrs: Sequence[SymbolExprAttr],
    target_shape_attrs: Sequence[SymbolExprAttr],
) -> int | None:
    """选择 view/deslice 可分组的最大连续后缀。

    功能说明:
    - rank 为 3 及以上时至少保留第 0 维外层维度，优先选择更长的后缀。
    - rank 为 2 时允许折叠为一维。

    使用示例:
    - collapse_start = _find_view_collapse_start(view, deslice, source_shape, target_shape)
    """

    rank = len(source_shape_attrs)
    if rank < 3:
        return None
    for collapse_start in range(1, rank - 1):
        if _suffix_is_groupable(view, deslice, source_shape_attrs, target_shape_attrs, collapse_start):
            return collapse_start
    return None


def _view_grouping_candidate(view: DmaViewOp) -> _ViewGroupingCandidate | None:
    """返回当前 view 的连续维度分组候选。

    功能说明:
    - 校验紧邻唯一 deslice、source/target contiguous、布局 operand 精确匹配和后缀连续证明。
    - 任一条件无法结构化证明时返回 `None`，保持原 IR 不变。

    使用示例:
    - candidate = _view_grouping_candidate(view)
    """

    block = view.parent_block()
    if block is None:
        return None
    deslice = _candidate_deslice(view)
    if deslice is None or deslice.parent_block() is not block:
        return None
    source_type = _memory_type_of(view.source)
    target_type = _memory_type_of(deslice.target)
    view_type = _memory_type_of(view.result)
    if source_type is None or target_type is None or view_type is None:
        return None
    if _is_i8_byte_pool_memory_type(source_type):
        return None
    if not _is_contiguous_memory_type(source_type) or not _is_contiguous_memory_type(target_type):
        return None
    source_shape_attrs = _symbol_expr_attrs(source_type.shape)
    target_shape_attrs = _symbol_expr_attrs(target_type.shape)
    view_shape_attrs = _symbol_expr_attrs(view_type.shape)
    if source_shape_attrs is None or target_shape_attrs is None or view_shape_attrs is None:
        return None
    if len(source_shape_attrs) != len(view_shape_attrs) or len(target_shape_attrs) != len(view_shape_attrs):
        return None
    deslice_groups = _deslice_operand_groups(deslice, len(view_shape_attrs))
    if deslice_groups is None:
        return None
    if not _symbol_operands_match_attrs(tuple(view.shape), view_shape_attrs):
        return None
    if not _symbol_operands_match_attrs(deslice_groups.sizes, view_shape_attrs):
        return None
    collapse_start = _find_view_collapse_start(view, deslice, source_shape_attrs, target_shape_attrs)
    if collapse_start is None:
        return None
    return _ViewGroupingCandidate(view, deslice, collapse_start, source_type, target_type, view_type)


def _reshape_shape_dominates_fill(reshape: DmaReshapeOp, fill: DmaFillOp) -> bool:
    """判断 reshape 的 shape operands 是否都支配 fill。

    功能说明:
    - `dma.reshape` 上移到 `dma.fill` 前之后仍必须满足 SSA 支配关系。
    - 任一 shape operand 在 `fill` 之后或不在可见 ancestor 中定义时保持 no-op。

    使用示例:
    - if _reshape_shape_dominates_fill(reshape, fill): ...
    """

    return all(_value_dominates_op(SSAValue.get(shape), fill) for shape in reshape.shape)


def _candidate_fill(reshape: DmaReshapeOp) -> DmaFillOp | None:
    """返回可被当前 reshape 穿过的紧邻 dma.fill。

    功能说明:
    - 只接受 `reshape.prev_op` 是 `DmaFillOp` 且 fill target 等于 reshape source。
    - 其它非紧邻、不同源或跨 block 形态均保持 no-op。

    使用示例:
    - fill = _candidate_fill(reshape)
    """

    previous = reshape.prev_op
    if not isinstance(previous, DmaFillOp):
        return None
    if not _same_value(previous.target, reshape.source):
        return None
    if not _reshape_shape_dominates_fill(reshape, previous):
        return None
    return previous


def _move_reshape_before_fill(
    module: ModuleOp,
    reshape: DmaReshapeOp,
    fill: DmaFillOp,
    rewriter: PatternRewriter,
) -> bool:
    """执行一次 reshape 穿过 fill 的事务式改写。

    功能说明:
    - 复用原 `dma.reshape` op/result，不新建 alias。
    - 通过 `PatternRewriter` 把 op 插到 `dma.fill` 前，满足用户指定的 pattern rewrite 形态。
    - 先移动 op 并改写 fill target，再用 `module.verify()` 验证。
    - 验证失败时撤销本次移动与 operand 改写，保证失败原 module 零改动。

    使用示例:
    - changed = _move_reshape_before_fill(module, reshape, fill, rewriter)
    """

    block = reshape.parent_block()
    if block is None or fill.parent_block() is not block:
        return False
    original_target = fill.operands[0]
    reshape.detach()
    rewriter.insert_op(reshape, InsertPoint.before(fill))
    fill.operands[0] = reshape.result
    try:
        module.verify()
    except VerifyException:
        fill.operands[0] = original_target
        reshape.detach()
        block.insert_op_after(reshape, fill)
        return False
    rewriter.notify_op_modified(fill)
    return True


def _build_view_grouping_ops(candidate: _ViewGroupingCandidate) -> tuple[Operation, ...] | None:
    """构造 view/deslice 连续维度分组后的新 operation 序列。

    功能说明:
    - 只使用当前 block 中已支配 `dma.view` 的公开 symbol value 作为 shape operand。
    - 需要动态乘积时在当前文件内生成 `symbol.mul`，不依赖跨文件私有 helper。

    使用示例:
    - new_ops = _build_view_grouping_ops(candidate)
    """

    view = candidate.view
    deslice = candidate.deslice
    block = view.parent_block()
    if block is None:
        return None
    collapse_start = candidate.collapse_start
    source_shape_attrs = _symbol_expr_attrs(candidate.source_type.shape)
    target_shape_attrs = _symbol_expr_attrs(candidate.target_type.shape)
    view_shape_attrs = _symbol_expr_attrs(candidate.view_type.shape)
    if source_shape_attrs is None or target_shape_attrs is None or view_shape_attrs is None:
        return None
    deslice_groups = _deslice_operand_groups(deslice, len(view_shape_attrs))
    if deslice_groups is None:
        return None
    source_shape_values = _find_dominating_symbol_values(block, view, source_shape_attrs)
    target_shape_values = _find_dominating_symbol_values(block, view, target_shape_attrs)
    if source_shape_values is None or target_shape_values is None:
        return None

    source_inner = _build_symbol_product(block, view, source_shape_values[collapse_start:])
    target_inner = _build_symbol_product(block, view, target_shape_values[collapse_start:])
    source_tail = source_shape_values[collapse_start + 1 :]
    scaled_offset = _build_scaled_offset(block, view, view.offsets[collapse_start], source_tail)
    if source_inner is None or target_inner is None or scaled_offset is None:
        return None

    source_inner_ops, source_inner_value = source_inner
    target_inner_ops, target_inner_value = target_inner
    view_inner_value = target_inner_value
    offset_ops, collapsed_offset = scaled_offset

    source_low_shape_attrs = _collapsed_layout_attrs(source_shape_attrs, collapse_start)
    target_low_shape_attrs = _collapsed_layout_attrs(target_shape_attrs, collapse_start)
    view_low_shape_attrs = _collapsed_layout_attrs(view_shape_attrs, collapse_start)
    source_low_stride_attrs = _contiguous_stride_attrs(source_low_shape_attrs)
    target_low_stride_attrs = _contiguous_stride_attrs(target_low_shape_attrs)
    source_low_type = _memory_type_with_layout(source_low_shape_attrs, source_low_stride_attrs, candidate.source_type)
    target_low_type = _memory_type_with_layout(target_low_shape_attrs, target_low_stride_attrs, candidate.target_type)
    view_low_type = _memory_type_with_layout(view_low_shape_attrs, source_low_stride_attrs, candidate.view_type)

    source_reshape_shape = tuple(source_shape_values[:collapse_start]) + (source_inner_value,)
    target_reshape_shape = tuple(target_shape_values[:collapse_start]) + (target_inner_value,)
    view_offsets = tuple(view.offsets[:collapse_start]) + (collapsed_offset,)
    view_sizes = tuple(view.shape[:collapse_start]) + (view_inner_value,)
    view_strides = tuple(view.stride[:collapse_start]) + (view.stride[collapse_start],)
    deslice_offsets = tuple(deslice_groups.offsets[:collapse_start]) + (deslice_groups.offsets[collapse_start],)
    deslice_sizes = tuple(deslice_groups.sizes[:collapse_start]) + (view_inner_value,)
    deslice_strides = tuple(deslice_groups.strides[:collapse_start]) + (deslice_groups.strides[collapse_start],)

    source_reshape = DmaReshapeOp(view.source, source_reshape_shape, source_low_type)
    target_reshape = DmaReshapeOp(deslice.target, target_reshape_shape, target_low_type)
    low_view = DmaViewOp(source_reshape.result, view_offsets, view_sizes, view_strides, view_low_type)
    low_deslice = DmaDesliceOp(
        target_reshape.result,
        low_view.result,
        deslice_offsets,
        deslice_sizes,
        deslice_strides,
        target_low_type,
    )
    new_ops: list[Operation] = []
    new_ops.extend(source_inner_ops)
    new_ops.extend(target_inner_ops)
    new_ops.extend(offset_ops)
    new_ops.extend([source_reshape, target_reshape, low_view, low_deslice])
    return tuple(new_ops)


def _restore_original_view_ops(
    block: Block,
    view: DmaViewOp,
    deslice: DmaDesliceOp,
    next_after_deslice: Operation | None,
) -> None:
    """把事务失败时暂存的原始 view/deslice 插回原位置。

    功能说明:
    - 优先插到原 `deslice.next_op` 前。
    - 原位置是 block 尾部时按原顺序追加。

    使用示例:
    - _restore_original_view_ops(block, view, deslice, next_op)
    """

    if next_after_deslice is not None and next_after_deslice.parent_block() is block:
        block.insert_ops_before((view, deslice), next_after_deslice)
    else:
        block.add_ops((view, deslice))


def _rewrite_view_deslice_grouping(
    module: ModuleOp,
    candidate: _ViewGroupingCandidate,
    rewriter: PatternRewriter,
) -> bool:
    """事务式执行一次 view/deslice 连续维度分组改写。

    功能说明:
    - 先构造完整新 op 序列，再替换原紧邻 `dma.view + dma.deslice`。
    - rewrite 后用 `module.verify()` 校验最终 IR。
    - 验证失败时撤销新增 op 并恢复原 view/deslice；验证成功时通知 rewriter 移除旧 op，
      避免 worklist 继续处理已脱离 block 的 operation。

    使用示例:
    - changed = _rewrite_view_deslice_grouping(module, candidate, rewriter)
    """

    view = candidate.view
    deslice = candidate.deslice
    block = view.parent_block()
    if block is None or deslice.parent_block() is not block:
        return False
    new_ops = _build_view_grouping_ops(candidate)
    if new_ops is None:
        return False
    next_after_deslice = deslice.next_op
    rewriter.insert_op(new_ops, InsertPoint.before(view))
    deslice.detach()
    view.detach()
    try:
        module.verify()
    except VerifyException:
        for op in reversed(new_ops):
            op.detach()
            rewriter.handle_operation_removal(op)
        _restore_original_view_ops(block, view, deslice, next_after_deslice)
        return False
    rewriter.handle_operation_removal(deslice)
    rewriter.handle_operation_removal(view)
    return True


class DmaViewDesliceGroupingPattern(RewritePattern):
    """`dma.view + dma.deslice` 连续维度分组 pattern。

    功能说明:
    - 只匹配 `DmaViewOp`，候选证明与 rewrite 都限制在当前文件内。
    - IR 变换：`dma.view -> dma.deslice` 降维为 `dma.reshape -> dma.view -> dma.deslice`。
    - no-op：连续维度证明或事务式 module verify 失败时保持原 IR。
    - IR before:
      ```mlir
      %view = "dma.view"(%src, %o0, %o1, %n, %k, %s0, %s1) : (...) -> !nn.memory<[N, K], [K, 1], f32, #nn.space<tsm>>
      "dma.deslice"(%dst, %view, %o0, %o1, %n, %k, %s0, %s1) : (...) -> ()
      ```
    - IR after:
      ```mlir
      %src_low = "dma.reshape"(%src, %nk) : (...) -> !nn.memory<[N*K], [1], f32, #nn.space<tsm>>
      %dst_low = "dma.reshape"(%dst, %nk) : (...) -> !nn.memory<[N*K], [1], f32, #nn.space<tsm>>
      %view_low = "dma.view"(%src_low, %o, %nk, %s) : (...) -> !nn.memory<[N*K], [1], f32, #nn.space<tsm>>
      "dma.deslice"(%dst_low, %view_low, %o, %nk, %s) : (...) -> ()
      ```
    - no-op unchanged after：连续维度无法证明或 verify 失败时，上述 before IR 保持不变。

    使用示例:
    - pattern = DmaViewDesliceGroupingPattern(module)
    """

    def __init__(self: "DmaViewDesliceGroupingPattern", module: ModuleOp) -> None:
        """初始化 pattern 持有的 module verifier 上下文。

        功能说明:
        - 保存当前 `builtin.module`，用于事务式 rewrite 后验证。
        - 记录 verifier 拒绝的 view op，避免 greedy walker 反复重试。

        使用示例:
        - pattern = DmaViewDesliceGroupingPattern(module)
        """

        self.module = module
        self.rejected_view_ops: set[int] = set()

    @op_type_rewrite_pattern
    def match_and_rewrite(self: "DmaViewDesliceGroupingPattern", op: DmaViewOp, rewriter: PatternRewriter, /) -> None:
        """执行单个 `view -> deslice` 候选改写。

        功能说明:
        - 未满足连续维度证明时保持 no-op。
        - 满足条件时把高维 view/deslice 降维为 reshape 后的低维 view/deslice。

        使用示例:
        - DmaViewDesliceGroupingPattern(module).match_and_rewrite(view, rewriter)
        """

        if id(op) in self.rejected_view_ops:
            return
        candidate = _view_grouping_candidate(op)
        if candidate is None:
            return
        if not _rewrite_view_deslice_grouping(self.module, candidate, rewriter):
            self.rejected_view_ops.add(id(op))


class DmaReshapeThroughFillPattern(RewritePattern):
    """`dma.reshape` 穿过紧邻 `dma.fill` 的 pattern。

    功能说明:
    - 只匹配 `DmaReshapeOp`，并复用 `_candidate_fill(...)` 收口同 block、紧邻、同源与支配边界。
    - IR 变换：`dma.fill(%src); dma.reshape(%src)` 改为 `dma.reshape(%src); dma.fill(%alias)`。
    - no-op：候选条件或事务式 module verify 失败时保持原 IR。
    - IR before:
      ```mlir
      "dma.fill"(%src, %value) : (value, f32) -> ()
      %alias = "dma.reshape"(%src, %n, %k) : (...) -> !nn.memory<[N, K], [K, 1], f32, #nn.space<tsm>>
      ```
    - IR after:
      ```mlir
      %alias = "dma.reshape"(%src, %n, %k) : (...) -> !nn.memory<[N, K], [K, 1], f32, #nn.space<tsm>>
      "dma.fill"(%alias, %value) : (value, f32) -> ()
      ```
    - no-op unchanged after：reshape 与 fill 非紧邻、不同源或 verify 失败时，上述 before IR 保持不变。

    使用示例:
    - pattern = DmaReshapeThroughFillPattern(module)
    """

    def __init__(self: "DmaReshapeThroughFillPattern", module: ModuleOp) -> None:
        """初始化 pattern 持有的 module verifier 上下文。

        功能说明:
        - 保存当前 `builtin.module`，用于事务式 rewrite 后验证并在失败时回滚。
        - 记录已被 verifier 拒绝的 reshape op，避免 greedy walker 反复重试同一失败候选。

        使用示例:
        - pattern = DmaReshapeThroughFillPattern(module)
        """

        self.module = module
        self.rejected_reshape_ops: set[int] = set()

    @op_type_rewrite_pattern
    def match_and_rewrite(self: "DmaReshapeThroughFillPattern", op: DmaReshapeOp, rewriter: PatternRewriter, /) -> None:
        """执行单个 `fill -> reshape` 候选改写。

        功能说明:
        - 未满足候选条件时保持 no-op。
        - 满足条件时用 pattern rewriter 把 reshape 移到 fill 前，并将 fill target 改为 alias result。

        使用示例:
        - DmaReshapeThroughFillPattern(module).match_and_rewrite(reshape, rewriter)
        """

        if id(op) in self.rejected_reshape_ops:
            return
        fill = _candidate_fill(op)
        if fill is None:
            return
        if not _move_reshape_before_fill(self.module, op, fill, rewriter):
            self.rejected_reshape_ops.add(id(op))


def get_hoist_dma_alias_ops_pass_patterns(module: ModuleOp) -> list[RewritePattern]:
    """返回 `hoist-dma-alias-ops` pass 的公开 pattern 列表。

    功能说明:
    - 每次调用返回新的 `DmaViewDesliceGroupingPattern` 与 `DmaReshapeThroughFillPattern` 实例。
    - 返回顺序固定为 view/deslice 分组 pattern 在前、reshape/fill 上移 pattern 在后。

    使用示例:
    - patterns = get_hoist_dma_alias_ops_pass_patterns(module)
    """

    return [DmaViewDesliceGroupingPattern(module), DmaReshapeThroughFillPattern(module)]


def _rewrite_module_to_fixed_point(ctx: Context, module: ModuleOp, *, fold: bool) -> None:
    """用 pattern walker 执行 alias op 上移直到稳定。

    功能说明:
    - 注册当前文件公开 `DmaViewOp` 与 `DmaReshapeOp` pattern。
    - Greedy walker 负责对 module 内多个独立候选收敛，不做手工整段遍历搬 op。

    使用示例:
    - _rewrite_module_to_fixed_point(ctx, module, fold=True)
    """

    PatternRewriteWalker(
        GreedyRewritePatternApplier(
            get_hoist_dma_alias_ops_pass_patterns(module),
            ctx=ctx,
            folding_enabled=fold,
            dce_enabled=False,
        )
    ).rewrite_module(module)


class HoistDmaAliasOpsPass(Pass):
    """`hoist-dma-alias-ops` pass 公开入口。

    功能说明:
    - 第一阶段只让 `dma.reshape` 穿过紧邻且同源的 `dma.fill`。
    - 扩展阶段让满足连续后缀维度证明的 `dma.view + dma.deslice` 降维分组。
    - 内部通过 xDSL pattern rewrite 基础设施和公开 pattern getter 驱动。
    - 不提供 pass 专属 option；registry 只支持通用 `fold` option。

    使用示例:
    - HoistDmaAliasOpsPass().apply(Context(), module)
    """

    name = "hoist-dma-alias-ops"

    def apply(self: "HoistDmaAliasOpsPass", ctx: Context, module: ModuleOp) -> None:
        """执行 `hoist-dma-alias-ops` ModulePass。

        功能说明:
        - 校验输入为 `builtin.module`。
        - 对 module 内所有函数和 nested region 通过 pattern walker 执行紧邻 alias rewrite。

        使用示例:
        - HoistDmaAliasOpsPass(fold=False).apply(Context(), module)
        """

        _ = ctx
        module = ensure_builtin_module(module)
        _rewrite_module_to_fixed_point(ctx, module, fold=self.fold)


__all__ = [
    "DmaViewDesliceGroupingPattern",
    "DmaReshapeThroughFillPattern",
    "get_hoist_dma_alias_ops_pass_patterns",
    "HoistDmaAliasOpsPass",
]
