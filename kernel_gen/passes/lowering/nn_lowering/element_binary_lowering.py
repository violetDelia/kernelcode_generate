"""element binary/compare lowering 实现。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 统一 nn element binary/compare 的 lowering 目标为 kernel.binary_elewise(kind=...)。
- mixed compare 先通过 dma.alloc + dma.broadcast 物化标量 operand。
- 输出 memory 通过 dma.alloc 显式创建。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.element_binary_lowering import LowerNnElementBinaryPass
- module = LowerNnElementBinaryPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/element_binary_add.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
"""

from __future__ import annotations

from xdsl.dialects import func
from xdsl.dialects.builtin import IntAttr, StringAttr
from xdsl.ir import Block, Operation, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp
from kernel_gen.passes.pass_manager import Pass
from .nn_lowering_utility import (
    NnLoweringError,
    ensure_module_op,
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


def _select_memory_operand(op: Operation) -> SSAValue:
    """选择 element binary 的 memory operand 作为 shape 来源。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

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
    最后一次更改: 小李飞刀

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
    for axis, dim in enumerate(result_type.shape.data):
        if isinstance(dim, StringAttr) and dim.data == "?":
            raise NnLoweringError("nn element binary result shape must not contain '?'")
        get_dim = SymbolGetDimOp(source, IntAttr(axis))
        ops.append(get_dim)
        operands.append(get_dim.result)
    return ops, operands


def _materialize_compare_operand(
    scalar: SSAValue,
    source: SSAValue,
) -> tuple[list[Operation], SSAValue]:
    """把 compare 的标量 operand 物化为 memory。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为标量创建与 source 同布局的临时 memory。
    - 通过 dma.broadcast 写入标量值。

    使用示例:
    - ops, value = _materialize_compare_operand(scalar, source)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise NnLoweringError("compare materialize source must be nn.memory")
    shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(source, source_type)
    alloc = DmaAllocOp(dynamic_shape, source_type)
    broadcast = DmaBroadcastOp(alloc.result, scalar)
    return [*shape_ops, alloc, broadcast], alloc.result


def _lower_element_binary_op(op: Operation, block: Block) -> None:
    """对单个 element binary/compare op 执行 lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一转换为 kernel.binary_elewise(kind=...)。
    - compare mixed operand 先 dma.broadcast 物化标量。

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

    lhs_value = SSAValue.get(op.operands[0])
    rhs_value = SSAValue.get(op.operands[1])
    lhs_is_memory = isinstance(lhs_value.type, NnMemoryType)
    rhs_is_memory = isinstance(rhs_value.type, NnMemoryType)

    extra_ops: list[Operation] = []
    if op.name in _COMPARE_KINDS:
        if lhs_is_memory and rhs_is_memory:
            pass
        elif lhs_is_memory and not rhs_is_memory:
            extra_ops, rhs_value = _materialize_compare_operand(rhs_value, lhs_value)
        elif rhs_is_memory and not lhs_is_memory:
            extra_ops, lhs_value = _materialize_compare_operand(lhs_value, rhs_value)
        else:
            raise NnLoweringError("nn compare must provide at least one nn.memory operand")
    else:
        if not lhs_is_memory or not rhs_is_memory:
            raise NnLoweringError("nn element binary requires nn.memory operands")

    shape_source = _select_memory_operand(op)
    shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(shape_source, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
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


def _lower_block(block: Block) -> None:
    """遍历 block 执行 element binary/compare lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按顺序处理 block 内的 nn element binary/compare op。

    使用示例:
    - _lower_block(block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    for op in list(block.ops):
        if op.name.startswith("nn."):
            _lower_element_binary_op(op, block)


class LowerNnElementBinaryPass(Pass):
    """element binary/compare lowering pass。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对 module 中的 element binary/compare 执行 lowering。
    - 仅处理 func.func 内的 op。

    使用示例:
    - module = LowerNnElementBinaryPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    name = "lower-nn-element-binary"

    def run(self: "LowerNnElementBinaryPass", module: Operation) -> Operation:
        """执行 element binary/compare lowering。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 校验 module 类型并遍历 func.func。

        使用示例:
        - LowerNnElementBinaryPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_lowering.md
        - test: test/pass/nn_lowering/element_binary_add.py
        - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
        """

        module_op = ensure_module_op(module)
        for op in module_op.ops:
            if isinstance(op, func.FuncOp):
                for block in op.body.blocks:
                    _lower_block(block)
        return module_op


__all__ = ["LowerNnElementBinaryPass"]
