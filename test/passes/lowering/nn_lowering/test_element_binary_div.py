"""nn_lowering element binary div tests.


功能说明:
- 验证 nn.div lower 为 kernel.binary_elewise(kind="div")。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_element_binary_div.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/spec.md
- 测试文件: test/passes/lowering/nn_lowering/test_element_binary_div.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, f32
from xdsl.ir import Attribute, Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnDivOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from test.passes.lowering.nn_lowering.memory_type_utils import symbol_array


def _make_memory_type(element_type: Attribute = f32) -> NnMemoryType:
    """构造默认 memory type。


    功能说明:
    - 生成 rank=2 的 nn.memory 类型。

    使用示例:
    - mem_type = _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_element_binary_div.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    shape = symbol_array([4, 8])
    stride = symbol_array([8, 1])
    return NnMemoryType(shape, stride, element_type, NnMemorySpaceAttr.from_name("global"))


def _build_module(
    arg_types: list[Attribute],
    result_type: NnMemoryType,
    op_builder: Callable[[Block], list[Operation]],
) -> tuple[ModuleOp, Block]:
    """构造包含单个 func 的 module。


    功能说明:
    - 按顺序插入 ops 并追加 func.return。

    使用示例:
    - module, block = _build_module([lhs, rhs], result_type, lambda block: [nn_op])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_element_binary_div.py
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


# TC-PASS-NNL-S2-004
# 测试目的: 验证 nn.div lower 为 kernel.binary_elewise(kind="div")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_element_binary_div.py -k test_lower_div_to_kernel_binary_elewise
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_element_binary_div.py
def test_lower_div_to_kernel_binary_elewise() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = NnMemorySpaceAttr.from_name("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnDivOp(block.args[0], block.args[1], result_type, space)],
    )
    NnLoweringPass().apply(Context(), module)

    ops = list(block.ops)
    kernel_ops = [op for op in ops if isinstance(op, KernelBinaryElewiseOp)]
    assert kernel_ops and kernel_ops[0].kind.data == "div"
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)
