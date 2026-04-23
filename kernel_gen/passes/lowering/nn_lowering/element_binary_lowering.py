"""element binary/compare lowering 实现。

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 统一 nn element binary/compare 的 lowering 目标为 kernel.binary_elewise(kind=...)。
- mixed element binary 标量 operand 通过 dma.alloc + dma.fill 物化。
- mixed compare 标量 operand 继续通过 dma.alloc + dma.broadcast 物化。
- 输出 memory 通过 dma.alloc 显式创建。
- 主 lowering driver 按单个 nn op 注册独立 RewritePattern，不再通过 family pattern 做名称分发。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.element_binary_lowering import lower_element_binary_family
- lower_element_binary_family(block, op)

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/element_binary_add.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntAttr, StringAttr
from xdsl.ir import Block, Operation, SSAValue
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern, op_type_rewrite_pattern
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaFillOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnDivOp,
    NnEqOp,
    NnGeOp,
    NnGtOp,
    NnLeOp,
    NnLtOp,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnSubOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolGetDimOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
)
from .nn_lowering_utility import (
    NnLoweringError,
    ensure_expected_op_name,
    ensure_operand_count,
    ensure_single_result,
    ensure_space_attr,
)


_SYMBOL_ARITH_OPS: dict[str, type[Operation]] = {
    "symbol.add": SymbolAddOp,
    "symbol.sub": SymbolSubOp,
    "symbol.mul": SymbolMulOp,
    "symbol.div": SymbolDivOp,
    "symbol.floordiv": SymbolFloorDivOp,
}


def _select_memory_operand(op: Operation) -> SSAValue:
    """选择 element binary 的 memory operand 作为 shape 来源。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 从 operands 中选择第一个 nn.memory 作为 shape 来源。
    - 若不存在 nn.memory 则抛出 NnLoweringError。

    使用示例:
    - shape_source = _select_memory_operand(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    for operand in op.operands:
        value = SSAValue.get(operand)
        if isinstance(value.type, NnMemoryType):
            return value
    raise NnLoweringError("nn element binary requires at least one nn.memory operand")


def _build_alloc_dynamic_shape_from_source(
    source: SSAValue,
    result_type: NnMemoryType,
) -> tuple[list[Operation], list[SSAValue]]:
    """基于 memory operand 构造 dma.alloc 的 dynamic_shape。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 逐维使用 symbol.get_dim 读取 shape 对应维度。
    - 禁止结果 shape 包含匿名维度 '?'。
    - source 与 result rank 不一致时抛出 NnLoweringError。

    使用示例:
    - ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(source, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise NnLoweringError("dynamic_shape source must be nn.memory")
    if len(source_type.shape.data) != len(result_type.shape.data):
        raise NnLoweringError("nn element binary operand/result rank mismatch")

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    has_dynamic = False
    for dim in result_type.shape.data:
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                raise NnLoweringError("nn element binary result shape must not contain '?'")
            has_dynamic = True
            continue
        if isinstance(dim, IntAttr):
            continue
        raise NnLoweringError("nn element binary result shape must be int or symbol")

    if not has_dynamic:
        return ops, operands

    for axis, _ in enumerate(result_type.shape.data):
        get_dim = SymbolGetDimOp(source, IntAttr(axis))
        ops.append(get_dim)
        operands.append(get_dim.result)
    return ops, operands


def _materialize_element_binary_scalar_operand(
    scalar: SSAValue,
    source_type: NnMemoryType,
    dynamic_shape: list[SSAValue],
) -> tuple[list[Operation], SSAValue]:
    """把 element binary 标量 operand 物化为 memory。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为标量创建与 source 同布局的临时 memory。
    - 通过 dma.fill 写入标量值。

    使用示例:
    - ops, value = _materialize_element_binary_scalar_operand(scalar, source_type, dynamic_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    if not isinstance(source_type, NnMemoryType):
        raise NnLoweringError("compare materialize source must be nn.memory")
    if isinstance(scalar.type, SymbolValueType):
        pass
    elif source_type.element_type != scalar.type:
        raise NnLoweringError("nn element binary scalar type mismatch")
    alloc = DmaAllocOp(dynamic_shape, source_type)
    fill = DmaFillOp(alloc.result, scalar)
    return [alloc, fill], alloc.result


def _materialize_compare_scalar_operand(
    scalar: SSAValue,
    source_type: NnMemoryType,
    dynamic_shape: list[SSAValue],
) -> tuple[list[Operation], SSAValue]:
    """把 compare 标量 operand 物化为 memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 compare 标量创建与 source 同布局的临时 memory。
    - 保留当前公开行为，继续通过 dma.broadcast 写入标量值。

    使用示例:
    - ops, value = _materialize_compare_scalar_operand(scalar, source_type, dynamic_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    if not isinstance(source_type, NnMemoryType):
        raise NnLoweringError("compare materialize source must be nn.memory")
    if isinstance(scalar.type, SymbolValueType):
        pass
    elif source_type.element_type != scalar.type:
        raise NnLoweringError("nn compare scalar type mismatch")
    alloc = DmaAllocOp(dynamic_shape, source_type)
    broadcast = DmaBroadcastOp(alloc.result, scalar)
    return [alloc, broadcast], alloc.result


def _normalize_symbol_ops(block: Block, anchor: Operation) -> None:
    """规范化 anchor 之前的 symbol 常量/算术 op。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 将 symbol.const 与符号算术 op 规范化为可重复使用的形式。
    - 避免 symbol 常量与算术链条在 lowering 前产生名称污染。

    使用示例:
    - _normalize_symbol_ops(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    cache: dict[SSAValue, SSAValue] = {}
    for op in list(block.ops):
        if op is anchor:
            break
        name = getattr(op, "name", None)
        if name == "symbol.const":
            value_attr = op.attributes.get("value")
            if not isinstance(value_attr, IntAttr):
                continue
            new_op = SymbolConstOp(value_attr, op.results[0].type)
        elif name in _SYMBOL_ARITH_OPS:
            lhs = cache.get(SSAValue.get(op.operands[0]), SSAValue.get(op.operands[0]))
            rhs = cache.get(SSAValue.get(op.operands[1]), SSAValue.get(op.operands[1]))
            new_op = _SYMBOL_ARITH_OPS[name](lhs, rhs, op.results[0].type)
        else:
            continue
        block.insert_op_before(new_op, op)
        op.results[0].replace_all_uses_with(new_op.results[0])
        new_op.results[0].name_hint = None
        cache[op.results[0]] = new_op.results[0]
        block.erase_op(op)


_ELEMENT_BINARY_PATTERN_KINDS: tuple[tuple[type[Operation], str], ...] = (
    (NnAddOp, "add"),
    (NnSubOp, "sub"),
    (NnMulOp, "mul"),
    (NnDivOp, "div"),
    (NnTrueDivOp, "div"),
)
_COMPARE_PATTERN_KINDS: tuple[tuple[type[Operation], str], ...] = (
    (NnEqOp, "eq"),
    (NnNeOp, "ne"),
    (NnLtOp, "lt"),
    (NnLeOp, "le"),
    (NnGtOp, "gt"),
    (NnGeOp, "ge"),
)


def _lower_element_binary_op(
    op: Operation,
    block: Block,
    *,
    kind: str,
    is_compare: bool,
) -> None:
    """对单个 element binary/compare op 执行 lowering。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一转换为 kernel.binary_elewise(kind=...)。
    - mixed element binary 标量 operand 先 dma.fill 物化。
    - mixed compare 标量 operand 继续 dma.broadcast 物化。
    - kind 与 compare 标记由单 op pattern 显式传入，避免 helper 内再按 nn op 名称分发。

    使用示例:
    - _lower_element_binary_op(op, block, kind="add", is_compare=False)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    ensure_operand_count(op, 2)
    result_type = ensure_single_result(op)
    space = ensure_space_attr(op)

    _normalize_symbol_ops(block, op)

    lhs_value = SSAValue.get(op.operands[0])
    rhs_value = SSAValue.get(op.operands[1])
    lhs_is_memory = isinstance(lhs_value.type, NnMemoryType)
    rhs_is_memory = isinstance(rhs_value.type, NnMemoryType)

    extra_ops: list[Operation] = []
    if is_compare:
        if lhs_is_memory and rhs_is_memory:
            if lhs_value.type.shape != rhs_value.type.shape:
                raise NnLoweringError("nn op operands must have the same shape")
        elif lhs_is_memory and not rhs_is_memory:
            pass
        elif rhs_is_memory and not lhs_is_memory:
            pass
        else:
            raise NnLoweringError("nn compare must provide at least one nn.memory operand")
    else:
        if lhs_is_memory and rhs_is_memory:
            if lhs_value.type.shape != rhs_value.type.shape:
                raise NnLoweringError("nn op operands must have the same shape")
        elif lhs_is_memory and not rhs_is_memory:
            pass
        elif rhs_is_memory and not lhs_is_memory:
            pass
        else:
            raise NnLoweringError("nn element binary must provide at least one nn.memory operand")

    shape_source = _select_memory_operand(op)
    shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(shape_source, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    if lhs_is_memory and not rhs_is_memory:
        if is_compare:
            extra_ops, rhs_value = _materialize_compare_scalar_operand(
                rhs_value, lhs_value.type, dynamic_shape
            )
        else:
            extra_ops, rhs_value = _materialize_element_binary_scalar_operand(
                rhs_value, lhs_value.type, dynamic_shape
            )
    elif rhs_is_memory and not lhs_is_memory:
        if is_compare:
            extra_ops, lhs_value = _materialize_compare_scalar_operand(
                lhs_value, rhs_value.type, dynamic_shape
            )
        else:
            extra_ops, lhs_value = _materialize_element_binary_scalar_operand(
                lhs_value, rhs_value.type, dynamic_shape
            )
    kernel_op = KernelBinaryElewiseOp(
        alloc.result,
        lhs_value,
        rhs_value,
        kind=kind,
        space=space,
    )

    try:
        for extra_op in extra_ops:
            extra_op.verify()
        alloc.verify()
        kernel_op.verify()
    except VerifyException as exc:
        raise NnLoweringError(str(exc)) from exc

    block.insert_ops_before([*shape_ops, alloc, *extra_ops, kernel_op], op)
    op.results[0].replace_all_uses_with(alloc.result)
    block.erase_op(op)


def lower_element_binary_family(block: Block, op: Operation) -> bool:
    """执行 element binary/compare family lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅处理 element binary/compare family op。
    - 成功处理返回 True；非本 family op 返回 False。

    使用示例:
    - handled = lower_element_binary_family(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    for op_type, kind in _ELEMENT_BINARY_PATTERN_KINDS:
        if isinstance(op, op_type):
            ensure_expected_op_name(op, op_type.name)
            _lower_element_binary_op(op, block, kind=kind, is_compare=False)
            return True
    for op_type, kind in _COMPARE_PATTERN_KINDS:
        if isinstance(op, op_type):
            ensure_expected_op_name(op, op_type.name)
            _lower_element_binary_op(op, block, kind=kind, is_compare=True)
            return True
    return False


def _lower_typed_element_binary_pattern(
    op: Operation,
    rewriter: PatternRewriter,
    *,
    expected_name: str,
    kind: str,
    is_compare: bool,
) -> None:
    """执行单 op element binary/compare pattern 的公共动作。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据具体 pattern 传入的 kind 与 compare 标记调用 lowering helper。
    - 在执行 lowering 前校验 op 实例名称仍与具体 dialect op 一致。
    - 统一校验 op 必须位于 block 内，并标记 rewriter 已完成改写。

    使用示例:
    - _lower_typed_element_binary_pattern(op, rewriter, expected_name="nn.sub", kind="sub", is_compare=False)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/element_binary_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    block = op.parent_block()
    if block is None:
        raise NnLoweringError("nn op must be inside a block")
    ensure_expected_op_name(op, expected_name)
    _lower_element_binary_op(op, block, kind=kind, is_compare=is_compare)
    rewriter.has_done_action = True


class _LowerNnAddPattern(RewritePattern):
    """将单个 nn.add lowering 为 kernel.binary_elewise(kind="add")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnAddOp，并调用共享 helper 生成 kind="add" 的 kernel.binary_elewise。
    - 仅覆盖 nn.add，不承担其他 elementwise/compare op 分支选择。

    使用示例:
    - pattern = _LowerNnAddPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnAddOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.add", kind="add", is_compare=False
        )


class _LowerNnSubPattern(RewritePattern):
    """将单个 nn.sub lowering 为 kernel.binary_elewise(kind="sub")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnSubOp，并调用共享 helper 生成 kind="sub" 的 kernel.binary_elewise。
    - 仅覆盖 nn.sub，不承担其他 elementwise/compare op 分支选择。

    使用示例:
    - pattern = _LowerNnSubPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_sub.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnSubOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.sub", kind="sub", is_compare=False
        )


class _LowerNnMulPattern(RewritePattern):
    """将单个 nn.mul lowering 为 kernel.binary_elewise(kind="mul")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnMulOp，并调用共享 helper 生成 kind="mul" 的 kernel.binary_elewise。
    - 仅覆盖 nn.mul，不承担其他 elementwise/compare op 分支选择。

    使用示例:
    - pattern = _LowerNnMulPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_mul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnMulOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.mul", kind="mul", is_compare=False
        )


class _LowerNnDivPattern(RewritePattern):
    """将单个 nn.div lowering 为 kernel.binary_elewise(kind="div")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnDivOp，并调用共享 helper 生成 kind="div" 的 kernel.binary_elewise。
    - 仅覆盖 nn.div，不承担其他 elementwise/compare op 分支选择。

    使用示例:
    - pattern = _LowerNnDivPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_div.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnDivOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.div", kind="div", is_compare=False
        )


class _LowerNnTrueDivPattern(RewritePattern):
    """将单个 nn.truediv lowering 为 kernel.binary_elewise(kind="div")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnTrueDivOp，并调用共享 helper 生成 kind="div" 的 kernel.binary_elewise。
    - 仅覆盖 nn.truediv，不承担其他 elementwise/compare op 分支选择。

    使用示例:
    - pattern = _LowerNnTrueDivPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_truediv.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnTrueDivOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.truediv", kind="div", is_compare=False
        )


class _LowerNnEqPattern(RewritePattern):
    """将单个 nn.eq lowering 为 kernel.binary_elewise(kind="eq")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnEqOp，并调用共享 helper 生成 kind="eq" 的 kernel.binary_elewise。
    - 标记 compare 路径，保留 mixed compare 的 dma.broadcast 物化规则。

    使用示例:
    - pattern = _LowerNnEqPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnEqOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.eq", kind="eq", is_compare=True
        )


class _LowerNnNePattern(RewritePattern):
    """将单个 nn.ne lowering 为 kernel.binary_elewise(kind="ne")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnNeOp，并调用共享 helper 生成 kind="ne" 的 kernel.binary_elewise。
    - 标记 compare 路径，保留 mixed compare 的 dma.broadcast 物化规则。

    使用示例:
    - pattern = _LowerNnNePattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_ne.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnNeOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.ne", kind="ne", is_compare=True
        )


class _LowerNnLtPattern(RewritePattern):
    """将单个 nn.lt lowering 为 kernel.binary_elewise(kind="lt")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnLtOp，并调用共享 helper 生成 kind="lt" 的 kernel.binary_elewise。
    - 标记 compare 路径，保留 mixed compare 的 dma.broadcast 物化规则。

    使用示例:
    - pattern = _LowerNnLtPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_lt.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnLtOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.lt", kind="lt", is_compare=True
        )


class _LowerNnLePattern(RewritePattern):
    """将单个 nn.le lowering 为 kernel.binary_elewise(kind="le")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnLeOp，并调用共享 helper 生成 kind="le" 的 kernel.binary_elewise。
    - 标记 compare 路径，保留 mixed compare 的 dma.broadcast 物化规则。

    使用示例:
    - pattern = _LowerNnLePattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_le.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnLeOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.le", kind="le", is_compare=True
        )


class _LowerNnGtPattern(RewritePattern):
    """将单个 nn.gt lowering 为 kernel.binary_elewise(kind="gt")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnGtOp，并调用共享 helper 生成 kind="gt" 的 kernel.binary_elewise。
    - 标记 compare 路径，保留 mixed compare 的 dma.broadcast 物化规则。

    使用示例:
    - pattern = _LowerNnGtPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_gt.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnGtOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.gt", kind="gt", is_compare=True
        )


class _LowerNnGePattern(RewritePattern):
    """将单个 nn.ge lowering 为 kernel.binary_elewise(kind="ge")。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接匹配 NnGeOp，并调用共享 helper 生成 kind="ge" 的 kernel.binary_elewise。
    - 标记 compare 路径，保留 mixed compare 的 dma.broadcast 物化规则。

    使用示例:
    - pattern = _LowerNnGePattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_ge.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnGeOp, rewriter: PatternRewriter, /) -> None:
        _lower_typed_element_binary_pattern(
            op, rewriter, expected_name="nn.ge", kind="ge", is_compare=True
        )


def element_binary_patterns() -> list[RewritePattern]:
    """返回 element binary/compare rewrite pattern 集合。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 提供 nn_lowering 主 driver 的单 op pattern 注册入口。
    - 每个受支持 element binary/compare op 都有独立 pattern；helper 仅复用构造逻辑。

    使用示例:
    - patterns = element_binary_patterns()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/element_binary_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    return [
        _LowerNnAddPattern(),
        _LowerNnSubPattern(),
        _LowerNnMulPattern(),
        _LowerNnDivPattern(),
        _LowerNnTrueDivPattern(),
        _LowerNnEqPattern(),
        _LowerNnNePattern(),
        _LowerNnLtPattern(),
        _LowerNnLePattern(),
        _LowerNnGtPattern(),
        _LowerNnGePattern(),
    ]


__all__ = ["element_binary_patterns", "lower_element_binary_family"]
