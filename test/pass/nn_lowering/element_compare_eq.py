"""nn_lowering element compare eq tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 验证 nn.eq lower 为 kernel.binary_elewise(kind="eq")。
- 覆盖 mixed compare 的 dma.broadcast 物化路径。

使用示例:
- pytest -q test/pass/nn_lowering/element_compare_eq.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering.md
- 测试文件: test/pass/nn_lowering/element_compare_eq.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    FunctionType,
    IntAttr,
    IntegerAttr,
    ModuleOp,
    UnrealizedConversionCastOp,
    i1,
    i32,
)
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, result_def
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.passes.lowering.nn_lowering.element_binary_lowering import LowerNnElementBinaryPass


@irdl_op_definition
class NnEqOp(IRDLOperation):
    """测试用 nn.eq op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 构造 nn.eq，用于 mixed compare 测试。

    使用示例:
    - NnEqOp(lhs, rhs, result_type, space)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    name = "nn.eq"

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs_value: SSAValue | Operation,
        rhs_value: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[lhs_value, rhs_value],
            result_types=[result_type],
            attributes={"space": space},
        )


def _make_memory_type(element_type: Attribute = i32) -> NnMemoryType:
    """构造默认 memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 rank=2 的 nn.memory 类型。

    使用示例:
    - mem_type = _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    shape = ArrayAttr([IntAttr(4), IntAttr(8)])
    stride = ArrayAttr([IntAttr(8), IntAttr(1)])
    return NnMemoryType(shape, stride, element_type, NnMemorySpaceAttr.from_name("global"))


def _make_symbol_value(expr: str, literal: int) -> tuple[list[Operation], SSAValue]:
    """构造 symbol.int 常量。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 先生成 i32 常量，再转为 symbol.int。

    使用示例:
    - ops, value = _make_symbol_value("1", 1)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    const = arith.ConstantOp(IntegerAttr(literal, i32))
    cast = UnrealizedConversionCastOp(
        operands=[const.result], result_types=[SymbolValueType.from_expr(expr)]
    )
    return [const, cast], cast.results[0]


def _build_module(
    arg_types: list[Attribute],
    result_type: NnMemoryType,
    op_builder: Callable[[Block], list[Operation]],
) -> tuple[ModuleOp, Block]:
    """构造包含单个 func 的 module。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按顺序插入 ops 并追加 func.return。

    使用示例:
    - module, block = _build_module([lhs], result_type, builder)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_compare_eq.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    block = Block(arg_types=arg_types)
    ops = op_builder(block)
    if not ops:
        raise ValueError("op_builder must return at least one operation")
    for op in ops:
        block.add_op(op)
    block.add_op(func.ReturnOp(ops[-1].results[0]))
    func_type = FunctionType.from_lists(arg_types, [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    return module, block


# TC-PASS-NNL-S2-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-11 23:00:00 +0800
# 最近一次运行成功时间: 2026-04-11 23:00:00 +0800
# 测试目的: 验证 nn.eq mixed compare 先 dma.broadcast 再 kernel.binary_elewise(kind="eq")。
# 使用示例: pytest -q test/pass/nn_lowering/element_compare_eq.py -k test_lower_eq_mixed_compare_to_kernel_binary_elewise
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/element_compare_eq.py
def test_lower_eq_mixed_compare_to_kernel_binary_elewise() -> None:
    lhs_type = _make_memory_type()
    result_type = _make_memory_type(element_type=i1)
    space = NnMemorySpaceAttr.from_name("global")

    def _build_ops(block: Block) -> list[Operation]:
        const_ops, symbol_value = _make_symbol_value("1", 1)
        nn_op = NnEqOp(block.args[0], symbol_value, result_type, space)
        return [*const_ops, nn_op]

    module, block = _build_module([lhs_type], result_type, _build_ops)
    LowerNnElementBinaryPass().run(module)

    ops = list(block.ops)
    kernel_ops = [op for op in ops if isinstance(op, KernelBinaryElewiseOp)]
    assert kernel_ops and kernel_ops[0].kind.data == "eq"
    assert any(isinstance(op, DmaBroadcastOp) for op in ops)
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)
