"""element binary/compare lowering 实现。

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 统一 nn element binary/compare 的 lowering 目标为 kernel.binary_elewise(kind=...)。
- mixed element binary 标量 operand 通过 dma.alloc + dma.fill 物化。
- mixed compare 标量 operand 继续通过 dma.alloc + dma.broadcast 物化。
- 输出 memory 通过 dma.alloc 显式创建。

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
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaFillOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnMemoryType
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
    ensure_operand_count,
    ensure_single_result,
    ensure_space_attr,
)


_ELEMENT_BINARY_KINDS: dict[str, str] = {
    "nn.add": "add",
    "nn.sub": "sub",
    "nn.mul": "mul",
    "nn.div": "div",
    "nn.truediv": "div",
}
_COMPARE_KINDS: dict[str, str] = {
    "nn.eq": "eq",
    "nn.ne": "ne",
    "nn.lt": "lt",
    "nn.le": "le",
    "nn.gt": "gt",
    "nn.ge": "ge",
}
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
        op.results[0].replace_by(new_op.results[0])
        new_op.results[0].name_hint = None
        cache[op.results[0]] = new_op.results[0]
        block.erase_op(op)


def _lower_element_binary_op(op: Operation, block: Block) -> None:
    """对单个 element binary/compare op 执行 lowering。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一转换为 kernel.binary_elewise(kind=...)。
    - mixed element binary 标量 operand 先 dma.fill 物化。
    - mixed compare 标量 operand 继续 dma.broadcast 物化。

    使用示例:
    - _lower_element_binary_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    if op.name not in _ELEMENT_BINARY_KINDS and op.name not in _COMPARE_KINDS:
        return

    ensure_operand_count(op, 2)
    result_type = ensure_single_result(op)
    space = ensure_space_attr(op)

    _normalize_symbol_ops(block, op)

    lhs_value = SSAValue.get(op.operands[0])
    rhs_value = SSAValue.get(op.operands[1])
    lhs_is_memory = isinstance(lhs_value.type, NnMemoryType)
    rhs_is_memory = isinstance(rhs_value.type, NnMemoryType)

    extra_ops: list[Operation] = []
    if op.name in _COMPARE_KINDS:
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
        if op.name in _ELEMENT_BINARY_KINDS:
            extra_ops, rhs_value = _materialize_element_binary_scalar_operand(
                rhs_value, lhs_value.type, dynamic_shape
            )
        else:
            extra_ops, rhs_value = _materialize_compare_scalar_operand(
                rhs_value, lhs_value.type, dynamic_shape
            )
    elif rhs_is_memory and not lhs_is_memory:
        if op.name in _ELEMENT_BINARY_KINDS:
            extra_ops, lhs_value = _materialize_element_binary_scalar_operand(
                lhs_value, rhs_value.type, dynamic_shape
            )
        else:
            extra_ops, lhs_value = _materialize_compare_scalar_operand(
                lhs_value, rhs_value.type, dynamic_shape
            )
    if op.name in _ELEMENT_BINARY_KINDS:
        kind_value = _ELEMENT_BINARY_KINDS[op.name]
    else:
        kind_value = _COMPARE_KINDS[op.name]
    kernel_op = KernelBinaryElewiseOp(
        lhs_value,
        rhs_value,
        alloc.result,
        kind=kind_value,
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
    op.results[0].replace_by(alloc.result)
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

    if op.name not in _ELEMENT_BINARY_KINDS and op.name not in _COMPARE_KINDS:
        return False
    _lower_element_binary_op(op, block)
    return True


__all__ = ["lower_element_binary_family"]
