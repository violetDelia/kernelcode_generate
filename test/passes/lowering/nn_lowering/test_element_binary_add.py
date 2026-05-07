"""nn_lowering element binary add tests.


功能说明:
- 验证 nn.add lower 为 kernel.binary_elewise(kind="add")。
- 覆盖 mixed scalar 的 dma.fill 物化路径。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_element_binary_add.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/spec.md
- 测试文件: test/passes/lowering/nn_lowering/test_element_binary_add.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

from xdsl.context import Context
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, IntegerAttr, ModuleOp, StringAttr, f32, i32
from xdsl.ir import Attribute, Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaFillOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
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
    - test: test/passes/lowering/nn_lowering/test_element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    shape = symbol_array([4, 8])
    stride = symbol_array([8, 1])
    return NnMemoryType(shape, stride, element_type, NnMemorySpaceAttr.from_name("global"))


def _make_anonymous_dynamic_memory_type(element_type: Attribute = i32) -> NnMemoryType:
    """构造匿名动态一维 memory type。


    功能说明:
    - 生成 shape 为 `?` 且 stride 为 1 的 nn.memory 类型，用于公开 lowering 链路测试。

    使用示例:
    - mem_type = _make_anonymous_dynamic_memory_type()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    shape = symbol_array(["?"])
    stride = symbol_array([1])
    return NnMemoryType(shape, stride, element_type, NnMemorySpaceAttr.from_name("global"))


def _build_anonymous_dynamic_add_ops(block: Block) -> list[Operation]:
    """构造匿名动态 alloc 输入的 nn.add op 列表。


    功能说明:
    - 通过公开 DmaAllocOp full-rank dynamic_shape 物化两个 `?` memory operand。
    - 返回包含两个 alloc 与一个 nn.add 的 op 列表，供公开 NnLoweringPass 测试使用。

    使用示例:
    - ops = _build_anonymous_dynamic_add_ops(block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_element_binary_add.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
    """

    memory_type = _make_anonymous_dynamic_memory_type()
    lhs_alloc = DmaAllocOp([block.args[0]], memory_type)
    rhs_alloc = DmaAllocOp([block.args[0]], memory_type)
    nn_op = NnAddOp(
        lhs_alloc.result,
        rhs_alloc.result,
        memory_type,
        NnMemorySpaceAttr.from_name("global"),
    )
    return [lhs_alloc, rhs_alloc, nn_op]


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
    - test: test/passes/lowering/nn_lowering/test_element_binary_add.py
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
# 测试目的: 验证 nn.add lower 为 kernel.binary_elewise(kind="add")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_element_binary_add.py -k test_lower_add_to_kernel_binary_elewise
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_element_binary_add.py
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
    NnLoweringPass().apply(Context(), module)

    ops = list(block.ops)
    kernel_ops = [op for op in ops if isinstance(op, KernelBinaryElewiseOp)]
    assert kernel_ops and kernel_ops[0].kind.data == "add"
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)


# TC-PASS-NNL-S2-001A
# 测试目的: 验证 nn.add mixed scalar 走 dma.fill，且不再落回 dma.broadcast。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_element_binary_add.py -k test_lower_add_mixed_scalar_uses_dma_fill
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_element_binary_add.py
def test_lower_add_mixed_scalar_uses_dma_fill() -> None:
    lhs_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=i32)
    space = NnMemorySpaceAttr.from_name("global")

    def _build_ops(block: Block) -> list[Operation]:
        scalar = arith.ConstantOp(IntegerAttr(3, i32))
        nn_op = NnAddOp(block.args[0], scalar.result, result_type, space)
        return [scalar, nn_op]

    module, block = _build_module([lhs_type], result_type, _build_ops)
    NnLoweringPass().apply(Context(), module)

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


# TC-PASS-NNL-S2-001B
# 测试目的: 验证 runtime tail 形态的匿名动态 alloc 输入可 lower 为 kernel.binary_elewise。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_element_binary_add.py -k test_lower_add_reuses_anonymous_dynamic_alloc_shape
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_element_binary_add.py
def test_lower_add_reuses_anonymous_dynamic_alloc_shape() -> None:
    result_type = _make_anonymous_dynamic_memory_type()
    module, block = _build_module(
        [SymbolValueType.from_expr("?")],
        result_type,
        _build_anonymous_dynamic_add_ops,
    )

    NnLoweringPass().apply(Context(), module)

    ops = list(block.ops)
    alloc_ops = [op for op in ops if isinstance(op, DmaAllocOp)]
    kernel_ops = [op for op in ops if isinstance(op, KernelBinaryElewiseOp)]
    assert len(alloc_ops) == 3
    assert alloc_ops[-1].dynamic_shape[0] is block.args[0]
    assert kernel_ops and kernel_ops[0].kind.data == "add"
    assert not any(op.name.startswith("nn.") for op in ops)
