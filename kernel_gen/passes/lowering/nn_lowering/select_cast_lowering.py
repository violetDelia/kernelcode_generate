"""select/cast lowering 实现。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- nn.select -> dma.alloc + kernel.select
- nn.cast -> dma.alloc + dma.cast

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.select_cast_lowering import LowerNnSelectCastPass
- module = LowerNnSelectCastPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/select.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
"""

from __future__ import annotations

from xdsl.dialects import func
from xdsl.dialects.builtin import IntAttr, StringAttr
from xdsl.ir import Block, Operation, SSAValue
from xdsl.irdl import IRDLOperation, irdl_op_definition, operand_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelSelectOp
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


@irdl_op_definition
class _DmaCastOutOp(IRDLOperation):
    """dma.cast（out 参数风格）。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 通过 out + source 形式表达 cast，匹配 nn_lowering 的输出约束。
    - 仅用于 select_cast_lowering 内部构造与校验。

    使用示例:
    - _DmaCastOutOp(out, source)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/pass/nn_lowering/cast.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    name = "dma.cast"

    out = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)

    def __init__(self, out: SSAValue | Operation, source: SSAValue | Operation) -> None:
        super().__init__(operands=[out, source])

    def verify_(self) -> None:
        out_type = self.out.type
        source_type = self.source.type
        if not isinstance(out_type, NnMemoryType):
            raise VerifyException("dma.cast output must be nn.memory")
        if not isinstance(source_type, NnMemoryType):
            raise VerifyException("dma.cast source must be nn.memory")
        out_type.verify()
        source_type.verify()
        if source_type.shape != out_type.shape:
            raise VerifyException("dma.cast shape mismatch")
        if source_type.stride != out_type.stride:
            raise VerifyException("dma.cast stride mismatch")
        if source_type.space.space.data != out_type.space.space.data:
            raise VerifyException("dma.cast space mismatch")


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
    - test: test/pass/nn_lowering/select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise NnLoweringError("dynamic_shape source must be nn.memory")
    if len(source_type.shape.data) != len(result_type.shape.data):
        raise NnLoweringError("nn select/cast operand/result rank mismatch")

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if isinstance(dim, StringAttr) and dim.data == "?":
            raise NnLoweringError("nn select/cast result shape must not contain '?'")
        get_dim = SymbolGetDimOp(source, IntAttr(axis))
        ops.append(get_dim)
        operands.append(get_dim.result)
    return ops, operands


def _lower_select_op(op: Operation, block: Block) -> None:
    """对 nn.select 执行 lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 输出 memory 通过 dma.alloc 创建。
    - 使用 kernel.select 完成写入。

    使用示例:
    - _lower_select_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    ensure_operand_count(op, 3)
    result_type = ensure_single_result(op)
    space = ensure_space_attr(op)

    cond_value = SSAValue.get(op.operands[0])
    lhs_value = SSAValue.get(op.operands[1])
    rhs_value = SSAValue.get(op.operands[2])
    if not isinstance(cond_value.type, NnMemoryType):
        raise NnLoweringError("nn.select cond must be nn.memory")
    if not isinstance(lhs_value.type, NnMemoryType):
        raise NnLoweringError("nn.select lhs must be nn.memory")
    if not isinstance(rhs_value.type, NnMemoryType):
        raise NnLoweringError("nn.select rhs must be nn.memory")

    shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(lhs_value, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    kernel_op = KernelSelectOp(cond_value, lhs_value, rhs_value, alloc.result, space)

    try:
        alloc.verify()
        kernel_op.verify()
    except VerifyException as exc:
        raise NnLoweringError(str(exc)) from exc

    block.insert_ops_before([*shape_ops, alloc, kernel_op], op)
    op.results[0].replace_by(alloc.result)
    block.erase_op(op)


def _lower_cast_op(op: Operation, block: Block) -> None:
    """对 nn.cast 执行 lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 输出 memory 通过 dma.alloc 创建。
    - 使用 dma.cast 完成写入。

    使用示例:
    - _lower_cast_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/cast.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    ensure_operand_count(op, 1)
    result_type = ensure_single_result(op)
    space = ensure_space_attr(op)

    input_value = SSAValue.get(op.operands[0])
    if not isinstance(input_value.type, NnMemoryType):
        raise NnLoweringError("nn.cast input must be nn.memory")

    shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_source(input_value, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    cast_op = _DmaCastOutOp(alloc.result, input_value)

    try:
        alloc.verify()
        cast_op.verify()
    except VerifyException as exc:
        raise NnLoweringError(str(exc)) from exc

    block.insert_ops_before([*shape_ops, alloc, cast_op], op)
    op.results[0].replace_by(alloc.result)
    block.erase_op(op)


def _lower_block(block: Block) -> None:
    """遍历 block 执行 select/cast lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按顺序处理 block 内的 nn.select 与 nn.cast。

    使用示例:
    - _lower_block(block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    for op in list(block.ops):
        if op.name == "nn.select":
            _lower_select_op(op, block)
        elif op.name == "nn.cast":
            _lower_cast_op(op, block)


class LowerNnSelectCastPass(Pass):
    """select/cast lowering pass。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对 module 中的 nn.select 与 nn.cast 执行 lowering。
    - 仅处理 func.func 内的 op。

    使用示例:
    - module = LowerNnSelectCastPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    name = "lower-nn-select-cast"

    def run(self: "LowerNnSelectCastPass", module: Operation) -> Operation:
        """执行 select/cast lowering。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 校验 module 类型并遍历 func.func。

        使用示例:
        - LowerNnSelectCastPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_lowering.md
        - test: test/pass/nn_lowering/select.py
        - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
        """

        module_op = ensure_module_op(module)
        for op in module_op.ops:
            if isinstance(op, func.FuncOp):
                for block in op.body.blocks:
                    _lower_block(block)
        return module_op


__all__ = ["LowerNnSelectCastPass"]
