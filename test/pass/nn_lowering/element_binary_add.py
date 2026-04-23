"""nn_lowering element binary add tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 验证 nn.add lower 为 kernel.binary_elewise(kind="add")。
- 覆盖 mixed scalar 的 dma.fill 物化路径。

使用示例:
- pytest -q test/pass/nn_lowering/element_binary_add.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering.md
- 测试文件: test/pass/nn_lowering/element_binary_add.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

from xdsl.dialects import arith, func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, IntegerAttr, ModuleOp, f32, i32
from xdsl.ir import Attribute, Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaFillOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass


def _make_memory_type(element_type: Attribute = f32) -> NnMemoryType:
    """构造默认 memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 rank=2 的 nn.memory 类型。

    使用示例:
    - mem_type = _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    shape = ArrayAttr([IntAttr(4), IntAttr(8)])
    stride = ArrayAttr([IntAttr(8), IntAttr(1)])
    return NnMemoryType(shape, stride, element_type, NnMemorySpaceAttr.from_name("global"))


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
    - module, block = _build_module([lhs, rhs], result_type, lambda block: [nn_op])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/element_binary_add.py
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


# TC-PASS-NNL-S2-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-11 23:00:00 +0800
# 最近一次运行成功时间: 2026-04-11 23:00:00 +0800
# 测试目的: 验证 nn.add lower 为 kernel.binary_elewise(kind="add")。
# 使用示例: pytest -q test/pass/nn_lowering/element_binary_add.py -k test_lower_add_to_kernel_binary_elewise
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/element_binary_add.py
def test_lower_add_to_kernel_binary_elewise() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = NnMemorySpaceAttr.from_name("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )
    NnLoweringPass().run(module)

    ops = list(block.ops)
    kernel_ops = [op for op in ops if isinstance(op, KernelBinaryElewiseOp)]
    assert kernel_ops and kernel_ops[0].kind.data == "add"
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)


# TC-PASS-NNL-S2-001A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-14 11:55:00 +0800
# 最近一次运行成功时间: 2026-04-14 11:55:00 +0800
# 测试目的: 验证 nn.add mixed scalar 走 dma.fill，且不再落回 dma.broadcast。
# 使用示例: pytest -q test/pass/nn_lowering/element_binary_add.py -k test_lower_add_mixed_scalar_uses_dma_fill
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/element_binary_add.py
def test_lower_add_mixed_scalar_uses_dma_fill() -> None:
    lhs_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=i32)
    space = NnMemorySpaceAttr.from_name("global")

    def _build_ops(block: Block) -> list[Operation]:
        scalar = arith.ConstantOp(IntegerAttr(3, i32))
        nn_op = NnAddOp(block.args[0], scalar.result, result_type, space)
        return [scalar, nn_op]

    module, block = _build_module([lhs_type], result_type, _build_ops)
    NnLoweringPass().run(module)

    ops = list(block.ops)
    kernel_ops = [op for op in ops if isinstance(op, KernelBinaryElewiseOp)]
    alloc_ops = [op for op in ops if isinstance(op, DmaAllocOp)]
    fill_ops = [op for op in ops if isinstance(op, DmaFillOp)]
    assert kernel_ops and kernel_ops[0].kind.data == "add"
    assert len(alloc_ops) == 2
    assert len(fill_ops) == 1
    assert not any(isinstance(op, DmaBroadcastOp) for op in ops)
    assert [op.name for op in ops] == [
        "arith.constant",
        "dma.alloc",
        "dma.alloc",
        "dma.fill",
        "kernel.binary_elewise",
        "func.return",
    ]
