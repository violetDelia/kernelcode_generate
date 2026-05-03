"""nn -> kernel lowering pass tests.


功能说明:
- 覆盖 nn_lowering pass 的 lowering 行为与错误路径。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py

当前覆盖率信息:
- `kernel_gen.passes.lowering.nn_lowering`：`100%`（2026-03-23 04:07:56 +0800，`15 passed`）。

覆盖率命令:
- `pytest --cov=kernel_gen.passes.lowering.nn_lowering --cov-report=term-missing -q test/passes/lowering/nn_lowering/test_nn_lowering.py`

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/spec.md
- 测试文件: test/passes/lowering/nn_lowering/test_nn_lowering.py
"""

from __future__ import annotations

import sys
import importlib
from pathlib import Path
from collections.abc import Callable

import pytest
from xdsl.context import Context
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    FunctionType,
    IntAttr,
    IntegerAttr,
    ModuleOp,
    StringAttr,
    f32,
    i1,
    i32,
)
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCastOp, DmaFillOp, DmaTransposeOp
from kernel_gen.dialect.kernel import (
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceOp,
    KernelSelectOp,
)
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnCastOp,
    NnEqOp,
    NnExpOp,
    NnGeOp,
    NnGtOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
    NnLeOp,
    NnLtOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnNeOp,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
    NnSelectOp,
    NnSoftmaxOp,
    NnTransposeOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolConstOp, SymbolGetDimOp, SymbolValueType
from kernel_gen.operation.nn import img2col1d, img2col2d, reduce_min
from kernel_gen.passes.buffer_results_to_out_params import (
    BufferResultsToOutParamsPass,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
pass_module = importlib.import_module("kernel_gen.passes.lowering.nn_lowering")
NnLoweringPass = pass_module.NnLoweringPass

SPACE_GLOBAL = NnMemorySpaceAttr(StringAttr("global"))


def nn_memory_type(
    shape: tuple[Attribute, ...],
    stride: tuple[Attribute, ...],
    element_type: Attribute,
    space: NnMemorySpaceAttr = SPACE_GLOBAL,
) -> NnMemoryType:
    """构造 nn.memory 测试类型。


    功能说明:
    - 将 shape/stride 的 tuple 转为 ArrayAttr。

    使用示例:
    - nn_memory_type((IntAttr(2),), (IntAttr(1),), i32)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: test/passes/lowering/nn_lowering/test_nn_lowering.py
    """

    return NnMemoryType(ArrayAttr(list(shape)), ArrayAttr(list(stride)), element_type, space)


def add_block_arg(block: Block, arg_type: Attribute) -> SSAValue:
    """向 Block 追加参数并返回。


    功能说明:
    - 使用 insert_arg 在末尾插入 block argument。

    使用示例:
    - lhs = add_block_arg(block, nn_memory_type((IntAttr(2),), (IntAttr(1),), i32))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: test/passes/lowering/nn_lowering/test_nn_lowering.py
    """

    return block.insert_arg(arg_type, len(block.args))


def _extract_ops(module: ModuleOp, op_type: type[Operation]) -> list[Operation]:
    return [op for op in module.ops if isinstance(op, op_type)]


def _assert_single_op(block: Block, op_type: type[Operation]) -> None:
    matched_ops = [op for op in block.ops if isinstance(op, op_type)]
    assert len(matched_ops) == 1


def _assert_single_binary_kind(block: Block, kind: str) -> None:
    matched_ops = [op for op in block.ops if isinstance(op, KernelBinaryElewiseOp)]
    assert len(matched_ops) == 1
    assert matched_ops[0].kind.data == kind


def _assert_single_alloc(block: Block) -> None:
    alloc_ops = [op for op in block.ops if isinstance(op, DmaAllocOp)]
    assert len(alloc_ops) == 1


def _assert_single_binary_kind_after_first_alloc(block: Block, kind: str) -> None:
    op_list = list(block.ops)
    for idx, op in enumerate(op_list):
        if isinstance(op, DmaAllocOp):
            target_idx = idx + 1
            assert target_idx < len(op_list)
            target = op_list[target_idx]
            assert isinstance(target, KernelBinaryElewiseOp)
            assert target.kind.data == kind
            return
    raise AssertionError("no DmaAllocOp found in block")


def _assert_single_reduce_kind(block: Block, kind: str) -> None:
    matched_ops = [op for op in block.ops if isinstance(op, KernelReduceOp)]
    assert len(matched_ops) == 1
    assert matched_ops[0].kind.data == kind


def _assert_single_op_after_first_alloc(block: Block, op_type: type[Operation]) -> None:
    op_list = list(block.ops)
    for idx, op in enumerate(op_list):
        if isinstance(op, DmaAllocOp):
            target_idx = idx + 1
            assert target_idx < len(op_list)
            assert isinstance(op_list[target_idx], op_type)
            return
    raise AssertionError("no DmaAllocOp found in block")


def _assert_single_dma_cast_after_first_alloc(block: Block) -> None:
    """断言第一个 dma.alloc 之后紧跟 dma.cast。


    功能说明:
    - 确保 dma.cast 紧跟在第一个 dma.alloc 后。

    使用示例:
    - _assert_single_dma_cast_after_first_alloc(block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    op_list = list(block.ops)
    for idx, op in enumerate(op_list):
        if isinstance(op, DmaAllocOp):
            target_idx = idx + 1
            assert target_idx < len(op_list)
            target = op_list[target_idx]
            assert isinstance(target, DmaCastOp)
            return
    raise AssertionError("no DmaAllocOp found in block")


def _build_test_module(
    name: str,
    input_types: list[NnMemoryType],
    output_types: list[NnMemoryType],
    builder: Callable[[Block], None],
) -> ModuleOp:
    region = Region()
    block = Block(arg_types=input_types)
    region.add_block(block)
    builder(block)
    block.add_op(func.ReturnOp([block.ops[-1].results[0]]))
    func_op = func.FuncOp(
        name,
        FunctionType.from_lists(input_types, output_types),
        region,
    )
    return ModuleOp([func_op])


def _build_module_from_op(op: Operation, input_types: list[NnMemoryType], output_types: list[NnMemoryType]) -> ModuleOp:
    region = Region()
    block = Block(arg_types=input_types)
    region.add_block(block)
    block.add_op(op)
    block.add_op(func.ReturnOp(op.results[0]))
    func_op = func.FuncOp(
        "test",
        FunctionType.from_lists(input_types, output_types),
        region,
    )
    return ModuleOp([func_op])


def _module_from_block(
    name: str,
    input_types: list[Attribute],
    output_types: list[Attribute],
    block: Block,
) -> ModuleOp:
    """用已填充 block 构造 lowering 测试模块。


    功能说明:
    - 支持测试 block 中含有公开 symbol/dma/nn op 的组合场景。
    - 只依赖 xDSL 公开 ModuleOp/FuncOp 构造入口。

    使用示例:
    - module = _module_from_block("case", [input_type], [result_type], block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: test/passes/lowering/nn_lowering/test_nn_lowering.py
    """

    return ModuleOp([func.FuncOp(name, FunctionType.from_lists(input_types, output_types), Region(block))])


def _lowered_func_block(module: ModuleOp) -> Block:
    """执行公开 NnLoweringPass 并返回函数 block。


    功能说明:
    - 统一公开 pass 调用路径，避免测试直连 child lowering helper。

    使用示例:
    - block = _lowered_func_block(module)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: test/passes/lowering/nn_lowering/test_nn_lowering.py
    """

    NnLoweringPass().apply(Context(), module)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    return func_op.body.block


# TC-PASS-NNL-001
# 测试目的: 验证 Lowering 对 nn.add 的改写行为，生成 kernel.binary_elewise(kind="add")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_add_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_add_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    add_op = NnAddOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(add_op)
    block.add_op(func.ReturnOp(add_op.results[0]))
    module = ModuleOp([func.FuncOp("add", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind_after_first_alloc(block, "add")


# TC-PASS-NNL-002
# 测试目的: 验证 Lowering 对 nn.truediv 的改写行为，统一生成 kernel.binary_elewise(kind="div")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_div_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_div_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    div_op = NnTrueDivOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(div_op)
    block.add_op(func.ReturnOp(div_op.results[0]))
    module = ModuleOp([func.FuncOp("div", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "div")


# TC-PASS-NNL-003
# 测试目的: 验证 Lowering 对 nn.eq 的改写行为，生成 kernel.binary_elewise(kind="eq")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_eq_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_eq_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    eq_op = NnEqOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(eq_op)
    block.add_op(func.ReturnOp(eq_op.results[0]))
    module = ModuleOp([func.FuncOp("eq", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "eq")


# TC-PASS-NNL-004
# 测试目的: 验证 Lowering 对 nn.ne 的改写行为，生成 kernel.binary_elewise(kind="ne")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_ne_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_ne_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    ne_op = NnNeOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(ne_op)
    block.add_op(func.ReturnOp(ne_op.results[0]))
    module = ModuleOp([func.FuncOp("ne", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "ne")


# TC-PASS-NNL-005
# 测试目的: 验证 Lowering 对 nn.le 的改写行为，生成 kernel.binary_elewise(kind="le")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_le_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_le_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    le_op = NnLeOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(le_op)
    block.add_op(func.ReturnOp(le_op.results[0]))
    module = ModuleOp([func.FuncOp("le", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "le")


# TC-PASS-NNL-006
# 测试目的: 验证 Lowering 对 nn.lt 的改写行为，生成 kernel.binary_elewise(kind="lt")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_lt_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_lt_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    lt_op = NnLtOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(lt_op)
    block.add_op(func.ReturnOp(lt_op.results[0]))
    module = ModuleOp([func.FuncOp("lt", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "lt")


# TC-PASS-NNL-007
# 测试目的: 验证 Lowering 对 nn.gt 的改写行为，生成 kernel.binary_elewise(kind="gt")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_gt_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_gt_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    gt_op = NnGtOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(gt_op)
    block.add_op(func.ReturnOp(gt_op.results[0]))
    module = ModuleOp([func.FuncOp("gt", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "gt")


# TC-PASS-NNL-008
# 测试目的: 验证 Lowering 对 nn.ge 的改写行为，生成 kernel.binary_elewise(kind="ge")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_ge_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_ge_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    ge_op = NnGeOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(ge_op)
    block.add_op(func.ReturnOp(ge_op.results[0]))
    module = ModuleOp([func.FuncOp("ge", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "ge")


# TC-PASS-NNL-009
# 测试目的: 验证 Lowering 对 nn.exp 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_exp_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_exp_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    exp_op = NnExpOp(operand, res_type, SPACE_GLOBAL)
    block.add_op(exp_op)
    block.add_op(func.ReturnOp(exp_op.results[0]))
    module = ModuleOp([func.FuncOp("exp", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, KernelExpOp)


# TC-PASS-NNL-010
# 测试目的: 验证 Lowering 对 nn.reduce_min 的改写行为，生成 kernel.reduce(kind="min")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_reduce_min_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_reduce_min_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr(1, 64)]),
        IntegerAttr(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_reduce_kind(block, "min")


# TC-PASS-NNL-010A
# 测试目的: 验证 Lowering 对 nn.reduce_sum 的改写行为，生成 kernel.reduce(kind="sum")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_reduce_sum_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_reduce_sum_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(1), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceSumOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr(0, 64)]),
        IntegerAttr(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_sum", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_reduce_kind(block, "sum")


# TC-PASS-NNL-010B
# 测试目的: 验证 Lowering 对 nn.reduce_max 的改写行为，生成 kernel.reduce(kind="max")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_reduce_max_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_reduce_max_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMaxOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr(1, 64)]),
        IntegerAttr(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_max", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_reduce_kind(block, "max")


# TC-PASS-NNL-011
# 测试目的: 验证 direct `nn.softmax` 会被拒绝，并提示需要先做分解。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_softmax_requires_decompass
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_softmax_requires_decompass() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    softmax_op = NnSoftmaxOp(
        operand,
        res_type,
        IntegerAttr(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(softmax_op)
    block.add_op(func.ReturnOp(softmax_op.results[0]))
    module = ModuleOp([func.FuncOp("softmax", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="nn.softmax must be decomposed before lower-nn"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-012
# 测试目的: 验证 Lowering 对 nn.matmul 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_matmul_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_matmul_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), f32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(3), IntAttr(4)), (IntAttr(4), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(4)), (IntAttr(4), IntAttr(1)), f32, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    matmul_op = NnMatmulOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(matmul_op)
    block.add_op(func.ReturnOp(matmul_op.results[0]))
    module = ModuleOp([func.FuncOp("matmul", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, KernelMatmulOp)


# TC-PASS-NNL-013
# 测试目的: 验证 Lowering 对 nn.img2col1d 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_img2col1d_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_img2col1d_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type(
        (IntAttr(2), IntAttr(2), IntAttr(2)),
        (IntAttr(4), IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    res_type = nn_memory_type(
        (IntAttr(2), IntAttr(2), IntAttr(2)),
        (IntAttr(4), IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    operand = add_block_arg(block, operand_type)
    kw = add_block_arg(block, SymbolValueType.from_expr("KW"))
    sw = add_block_arg(block, SymbolValueType.from_expr("SW"))
    dw = add_block_arg(block, SymbolValueType.from_expr("DW"))
    pl = add_block_arg(block, SymbolValueType.from_expr("PL"))
    pr = add_block_arg(block, SymbolValueType.from_expr("PR"))
    img2col_op = NnImg2col1dOp(operand, res_type, kw, sw, dw, pl, pr, SPACE_GLOBAL)
    block.add_op(img2col_op)
    block.add_op(func.ReturnOp(img2col_op.results[0]))
    module = ModuleOp(
        [
            func.FuncOp(
                "img2col1d",
                FunctionType.from_lists(
                    [
                        operand_type,
                        SymbolValueType.from_expr("KW"),
                        SymbolValueType.from_expr("SW"),
                        SymbolValueType.from_expr("DW"),
                        SymbolValueType.from_expr("PL"),
                        SymbolValueType.from_expr("PR"),
                    ],
                    [res_type],
                ),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, KernelImg2col1dOp)


# TC-PASS-NNL-014
# 测试目的: 验证 Lowering 对 nn.img2col2d 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_img2col2d_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_img2col2d_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type(
        (IntAttr(2), IntAttr(2), IntAttr(2), IntAttr(2)),
        (IntAttr(8), IntAttr(4), IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    res_type = nn_memory_type(
        (IntAttr(2), IntAttr(2), IntAttr(2), IntAttr(2)),
        (IntAttr(8), IntAttr(4), IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    operand = add_block_arg(block, operand_type)
    kh = add_block_arg(block, SymbolValueType.from_expr("KH"))
    kw = add_block_arg(block, SymbolValueType.from_expr("KW"))
    sh = add_block_arg(block, SymbolValueType.from_expr("SH"))
    sw = add_block_arg(block, SymbolValueType.from_expr("SW"))
    dh = add_block_arg(block, SymbolValueType.from_expr("DH"))
    dw = add_block_arg(block, SymbolValueType.from_expr("DW"))
    ph = add_block_arg(block, SymbolValueType.from_expr("PH"))
    pw = add_block_arg(block, SymbolValueType.from_expr("PW"))
    pl = add_block_arg(block, SymbolValueType.from_expr("PL"))
    pr = add_block_arg(block, SymbolValueType.from_expr("PR"))
    img2col_op = NnImg2col2dOp(
        operand,
        res_type,
        kh,
        kw,
        sh,
        sw,
        dh,
        dw,
        ph,
        pw,
        pl,
        pr,
        SPACE_GLOBAL,
    )
    block.add_op(img2col_op)
    block.add_op(func.ReturnOp(img2col_op.results[0]))
    module = ModuleOp(
        [
            func.FuncOp(
                "img2col2d",
                FunctionType.from_lists(
                    [
                        operand_type,
                        SymbolValueType.from_expr("KH"),
                        SymbolValueType.from_expr("KW"),
                        SymbolValueType.from_expr("SH"),
                        SymbolValueType.from_expr("SW"),
                        SymbolValueType.from_expr("DH"),
                        SymbolValueType.from_expr("DW"),
                        SymbolValueType.from_expr("PH"),
                        SymbolValueType.from_expr("PW"),
                        SymbolValueType.from_expr("PL"),
                        SymbolValueType.from_expr("PR"),
                    ],
                    [res_type],
                ),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, KernelImg2col2dOp)


# TC-PASS-NNL-015
# 测试目的: 验证 Lowering 对 nn.broadcast 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_broadcast_dma
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_broadcast_dma() -> None:
    block = Block()
    operand_type = nn_memory_type(
        (IntAttr(2), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    result_type = nn_memory_type(
        (IntAttr(2), IntAttr(2), IntAttr(2)),
        (IntAttr(4), IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    operand = add_block_arg(block, operand_type)
    broadcast_op = NnBroadcastOp(operand, result_type, SPACE_GLOBAL)
    block.add_op(broadcast_op)
    block.add_op(func.ReturnOp(broadcast_op.results[0]))
    module = ModuleOp(
        [
            func.FuncOp(
                "broadcast",
                FunctionType.from_lists([operand_type], [result_type]),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, DmaBroadcastOp)


# TC-PASS-NNL-016
# 测试目的: 验证 Lowering 对 nn.transpose 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_transpose_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_transpose_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type(
        (IntAttr(2), IntAttr(4)),
        (IntAttr(4), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    result_type = nn_memory_type(
        (IntAttr(4), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    operand = add_block_arg(block, operand_type)
    perm_attr = ArrayAttr([IntegerAttr(1, 64), IntegerAttr(0, 64)])
    transpose_op = NnTransposeOp(operand, result_type, perm_attr, SPACE_GLOBAL)
    block.add_op(transpose_op)
    block.add_op(func.ReturnOp(transpose_op.results[0]))
    module = ModuleOp(
        [
            func.FuncOp(
                "transpose",
                FunctionType.from_lists([operand_type], [result_type]),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, DmaTransposeOp)


# TC-PASS-NNL-017
# 测试目的: 验证 Lowering 对 nn.cast 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_cast_to_dma_cast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_cast_to_dma_cast() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    cast_op = NnCastOp(operand, result_type, SPACE_GLOBAL)
    block.add_op(cast_op)
    block.add_op(func.ReturnOp(cast_op.results[0]))
    module = ModuleOp([func.FuncOp("cast", FunctionType.from_lists([operand_type], [result_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_dma_cast_after_first_alloc(block)


# TC-PASS-NNL-018
# 测试目的: 验证 Lowering 对 nn.select 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_select_to_kernel_select
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_select_to_kernel_select() -> None:
    block = Block()
    cond_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    cond = add_block_arg(block, cond_type)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    select_op = NnSelectOp(cond, lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(select_op)
    block.add_op(func.ReturnOp(select_op.results[0]))
    module = ModuleOp([func.FuncOp("select", FunctionType.from_lists([cond_type, lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_op(block, KernelSelectOp)


# TC-PASS-NNL-019
# 测试目的: 验证 Lowering 对含符号维度 broadcast 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_broadcast_with_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_broadcast_with_symbol_dim() -> None:
    block = Block()
    operand_type = nn_memory_type(
        (IntAttr(2), StringAttr("M")),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    result_type = nn_memory_type(
        (IntAttr(2), StringAttr("M")),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    operand = add_block_arg(block, operand_type)
    broadcast_op = NnBroadcastOp(operand, result_type, SPACE_GLOBAL)
    block.add_op(broadcast_op)
    block.add_op(func.ReturnOp(broadcast_op.results[0]))
    module = ModuleOp(
        [
            func.FuncOp(
                "broadcast_symbol",
                FunctionType.from_lists([operand_type], [result_type]),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, DmaBroadcastOp)
    _assert_single_op(block, SymbolGetDimOp)


# TC-PASS-NNL-020
# 测试目的: 验证 Lowering 会把 mixed symbol scalar add 物化为 dma.fill 路径，并生成 kernel.binary_elewise(kind="add")。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_add_mixed_symbol_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_add_mixed_symbol_to_kernel() -> None:
    block = Block()
    lhs_type = nn_memory_type(
        (IntAttr(2), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    rhs_type = SymbolValueType.from_expr("K")
    res_type = nn_memory_type(
        (IntAttr(2), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    add_op = NnAddOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(add_op)
    block.add_op(func.ReturnOp(add_op.results[0]))
    module = ModuleOp([func.FuncOp("add_mixed_symbol", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    assert len([op for op in block.ops if isinstance(op, DmaAllocOp)]) == 2
    _assert_single_op(block, DmaFillOp)
    _assert_single_binary_kind(block, "add")
    assert not any(isinstance(op, DmaBroadcastOp) for op in block.ops)


# TC-PASS-NNL-020A
# 测试目的: 验证 Lowering 对 mixed symbol eq 的改写行为，生成 dma.alloc + dma.broadcast + kernel.binary_elewise(kind="eq")，且不混入 dma.fill。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_eq_mixed_symbol_uses_broadcast_only
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_eq_mixed_symbol_uses_broadcast_only() -> None:
    block = Block()
    lhs_type = nn_memory_type(
        (IntAttr(2), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    rhs_type = SymbolValueType.from_expr("K")
    res_type = nn_memory_type(
        (IntAttr(2), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        i1,
        SPACE_GLOBAL,
    )
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    eq_op = NnEqOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(eq_op)
    block.add_op(func.ReturnOp(eq_op.results[0]))
    module = ModuleOp([func.FuncOp("eq_mixed_symbol", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    assert len([op for op in block.ops if isinstance(op, DmaAllocOp)]) == 2
    _assert_single_op(block, DmaBroadcastOp)
    _assert_single_binary_kind(block, "eq")
    assert not any(isinstance(op, DmaFillOp) for op in block.ops)


# TC-PASS-NNL-020B
# 测试目的: 验证 element binary 公开 lowering 对动态 shape、左侧标量与 symbol 预处理的覆盖矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_element_binary_public_dynamic_scalar_and_symbol_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/element_binary_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_element_binary_public_dynamic_scalar_and_symbol_matrix() -> None:
    dynamic_type = nn_memory_type(
        (StringAttr("M"), StringAttr("N")),
        (StringAttr("N"), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    dynamic_block = Block(arg_types=[dynamic_type, dynamic_type])
    dynamic_op = NnAddOp(dynamic_block.args[0], dynamic_block.args[1], dynamic_type, SPACE_GLOBAL)
    dynamic_block.add_op(dynamic_op)
    dynamic_block.add_op(func.ReturnOp(dynamic_op.results[0]))
    dynamic_module = _module_from_block("element_binary_dynamic", [dynamic_type, dynamic_type], [dynamic_type], dynamic_block)

    dynamic_lowered_block = _lowered_func_block(dynamic_module)

    _assert_single_binary_kind(dynamic_lowered_block, "add")
    assert len([op for op in dynamic_lowered_block.ops if isinstance(op, SymbolGetDimOp)]) == 2
    dynamic_alloc = next(op for op in dynamic_lowered_block.ops if isinstance(op, DmaAllocOp))
    assert len(dynamic_alloc.dynamic_shape) == 2

    scalar_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    scalar_block = Block(arg_types=[scalar_type])
    scalar_const = arith.ConstantOp(IntegerAttr(3, i32))
    scalar_op = NnAddOp(scalar_const.result, scalar_block.args[0], scalar_type, SPACE_GLOBAL)
    scalar_block.add_op(scalar_const)
    scalar_block.add_op(scalar_op)
    scalar_block.add_op(func.ReturnOp(scalar_op.results[0]))
    scalar_module = _module_from_block("element_binary_left_scalar", [scalar_type], [scalar_type], scalar_block)

    scalar_lowered_block = _lowered_func_block(scalar_module)

    _assert_single_binary_kind(scalar_lowered_block, "add")
    _assert_single_op(scalar_lowered_block, DmaFillOp)
    assert not any(isinstance(op, DmaBroadcastOp) for op in scalar_lowered_block.ops)

    symbol_block = Block(arg_types=[scalar_type])
    symbol_two = SymbolConstOp(2)
    symbol_three = SymbolConstOp(3)
    symbol_sum = SymbolAddOp(symbol_two.result, symbol_three.result, SymbolValueType.from_expr("5"))
    symbol_op = NnAddOp(symbol_block.args[0], symbol_sum.result, scalar_type, SPACE_GLOBAL)
    symbol_block.add_op(symbol_two)
    symbol_block.add_op(symbol_three)
    symbol_block.add_op(symbol_sum)
    symbol_block.add_op(symbol_op)
    symbol_block.add_op(func.ReturnOp(symbol_op.results[0]))
    symbol_module = _module_from_block("element_binary_symbol_normalize", [scalar_type], [scalar_type], symbol_block)

    symbol_lowered_block = _lowered_func_block(symbol_module)

    _assert_single_binary_kind(symbol_lowered_block, "add")
    _assert_single_op(symbol_lowered_block, DmaFillOp)
    assert not any(op.name.startswith("nn.") for op in symbol_lowered_block.ops)

    dynamic_symbol_block = Block(arg_types=[scalar_type, SymbolValueType.from_expr("S")])
    symbol_const = SymbolConstOp(3)
    dynamic_symbol_sum = SymbolAddOp(
        dynamic_symbol_block.args[1],
        symbol_const.result,
        SymbolValueType.from_expr("S+3"),
    )
    dynamic_symbol_op = NnAddOp(dynamic_symbol_block.args[0], dynamic_symbol_sum.result, scalar_type, SPACE_GLOBAL)
    dynamic_symbol_block.add_op(symbol_const)
    dynamic_symbol_block.add_op(dynamic_symbol_sum)
    dynamic_symbol_block.add_op(dynamic_symbol_op)
    dynamic_symbol_block.add_op(func.ReturnOp(dynamic_symbol_op.results[0]))
    dynamic_symbol_module = _module_from_block(
        "element_binary_dynamic_symbol_normalize",
        [scalar_type, SymbolValueType.from_expr("S")],
        [scalar_type],
        dynamic_symbol_block,
    )

    dynamic_symbol_lowered_block = _lowered_func_block(dynamic_symbol_module)

    _assert_single_binary_kind(dynamic_symbol_lowered_block, "add")
    _assert_single_op(dynamic_symbol_lowered_block, DmaFillOp)
    assert any(isinstance(op, SymbolAddOp) for op in dynamic_symbol_lowered_block.ops)


# TC-PASS-NNL-020C
# 测试目的: 验证 compare 公开 lowering 对左侧标量和 mixed compare 物化路径的覆盖矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_compare_public_left_scalar_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/element_binary_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_compare_public_left_scalar_matrix() -> None:
    memory_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    block = Block(arg_types=[memory_type])
    scalar_const = arith.ConstantOp(IntegerAttr(7, i32))
    compare_op = NnEqOp(scalar_const.result, block.args[0], result_type, SPACE_GLOBAL)
    block.add_op(scalar_const)
    block.add_op(compare_op)
    block.add_op(func.ReturnOp(compare_op.results[0]))
    module = _module_from_block("compare_left_scalar", [memory_type], [result_type], block)

    lowered_block = _lowered_func_block(module)

    _assert_single_binary_kind(lowered_block, "eq")
    _assert_single_op(lowered_block, DmaBroadcastOp)
    assert not any(isinstance(op, DmaFillOp) for op in lowered_block.ops)


# TC-PASS-NNL-020D
# 测试目的: 验证 element binary/compare 公开 lowering 对无 memory、rank 和 scalar 类型非法输入的错误矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_element_binary_public_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/element_binary_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_element_binary_public_error_matrix() -> None:
    memory_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    no_memory_block = Block(arg_types=[i32, i32])
    no_memory_op = NnAddOp(no_memory_block.args[0], no_memory_block.args[1], result_type, SPACE_GLOBAL)
    no_memory_block.add_op(no_memory_op)
    no_memory_block.add_op(func.ReturnOp(no_memory_op.results[0]))
    no_memory_module = _module_from_block("element_binary_no_memory", [i32, i32], [result_type], no_memory_block)
    with pytest.raises(KernelCodeError, match="nn element binary must provide at least one nn.memory operand"):
        NnLoweringPass().apply(Context(), no_memory_module)

    compare_result_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    compare_no_memory_block = Block(arg_types=[i32, i32])
    compare_no_memory_op = NnEqOp(compare_no_memory_block.args[0], compare_no_memory_block.args[1], compare_result_type, SPACE_GLOBAL)
    compare_no_memory_block.add_op(compare_no_memory_op)
    compare_no_memory_block.add_op(func.ReturnOp(compare_no_memory_op.results[0]))
    compare_no_memory_module = _module_from_block(
        "compare_no_memory",
        [i32, i32],
        [compare_result_type],
        compare_no_memory_block,
    )
    with pytest.raises(KernelCodeError, match="nn compare must provide at least one nn.memory operand"):
        NnLoweringPass().apply(Context(), compare_no_memory_module)

    compare_shape_type = nn_memory_type((IntAttr(3), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    compare_shape_block = Block(arg_types=[memory_type, compare_shape_type])
    compare_shape_op = NnEqOp(compare_shape_block.args[0], compare_shape_block.args[1], compare_result_type, SPACE_GLOBAL)
    compare_shape_block.add_op(compare_shape_op)
    compare_shape_block.add_op(func.ReturnOp(compare_shape_op.results[0]))
    compare_shape_module = _module_from_block(
        "compare_shape_mismatch",
        [memory_type, compare_shape_type],
        [compare_result_type],
        compare_shape_block,
    )
    with pytest.raises(KernelCodeError, match="nn op operands must have the same shape"):
        NnLoweringPass().apply(Context(), compare_shape_module)

    compare_bad_result_block = Block(arg_types=[memory_type, memory_type])
    compare_bad_result_op = NnEqOp(compare_bad_result_block.args[0], compare_bad_result_block.args[1], result_type, SPACE_GLOBAL)
    compare_bad_result_block.add_op(compare_bad_result_op)
    compare_bad_result_block.add_op(func.ReturnOp(compare_bad_result_op.results[0]))
    compare_bad_result_module = _module_from_block(
        "compare_bad_result_element_type",
        [memory_type, memory_type],
        [result_type],
        compare_bad_result_block,
    )
    with pytest.raises(KernelCodeError, match="kernel.binary_elewise compare output element_type must be i1"):
        NnLoweringPass().apply(Context(), compare_bad_result_module)

    rank_result_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL)
    rank_block = Block(arg_types=[memory_type, memory_type])
    rank_op = NnAddOp(rank_block.args[0], rank_block.args[1], rank_result_type, SPACE_GLOBAL)
    rank_block.add_op(rank_op)
    rank_block.add_op(func.ReturnOp(rank_op.results[0]))
    rank_module = _module_from_block("element_binary_rank_error", [memory_type, memory_type], [rank_result_type], rank_block)
    with pytest.raises(KernelCodeError, match="nn element binary operand/result rank mismatch"):
        NnLoweringPass().apply(Context(), rank_module)

    unknown_result_type = nn_memory_type((StringAttr("?"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    source_type = nn_memory_type((StringAttr("M"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    unknown_block = Block(arg_types=[source_type, source_type])
    unknown_op = NnAddOp(unknown_block.args[0], unknown_block.args[1], unknown_result_type, SPACE_GLOBAL)
    unknown_block.add_op(unknown_op)
    unknown_block.add_op(func.ReturnOp(unknown_op.results[0]))
    unknown_module = _module_from_block("element_binary_unknown_result", [source_type, source_type], [unknown_result_type], unknown_block)
    with pytest.raises(KernelCodeError, match="nn element binary result shape must not contain '\\?'"):
        NnLoweringPass().apply(Context(), unknown_module)

    scalar_mismatch_block = Block(arg_types=[nn_memory_type((IntAttr(2),), (IntAttr(1),), f32, SPACE_GLOBAL)])
    scalar_mismatch_const = arith.ConstantOp(IntegerAttr(3, i32))
    scalar_mismatch_op = NnAddOp(
        scalar_mismatch_block.args[0],
        scalar_mismatch_const.result,
        nn_memory_type((IntAttr(2),), (IntAttr(1),), f32, SPACE_GLOBAL),
        SPACE_GLOBAL,
    )
    scalar_mismatch_block.add_op(scalar_mismatch_const)
    scalar_mismatch_block.add_op(scalar_mismatch_op)
    scalar_mismatch_block.add_op(func.ReturnOp(scalar_mismatch_op.results[0]))
    scalar_mismatch_module = _module_from_block(
        "element_binary_scalar_mismatch",
        [nn_memory_type((IntAttr(2),), (IntAttr(1),), f32, SPACE_GLOBAL)],
        [nn_memory_type((IntAttr(2),), (IntAttr(1),), f32, SPACE_GLOBAL)],
        scalar_mismatch_block,
    )
    with pytest.raises(KernelCodeError, match="nn element binary scalar type mismatch"):
        NnLoweringPass().apply(Context(), scalar_mismatch_module)

    compare_mismatch_block = Block(arg_types=[nn_memory_type((IntAttr(2),), (IntAttr(1),), f32, SPACE_GLOBAL)])
    compare_mismatch_const = arith.ConstantOp(IntegerAttr(3, i32))
    compare_mismatch_result_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), i1, SPACE_GLOBAL)
    compare_mismatch_op = NnEqOp(
        compare_mismatch_block.args[0],
        compare_mismatch_const.result,
        compare_mismatch_result_type,
        SPACE_GLOBAL,
    )
    compare_mismatch_block.add_op(compare_mismatch_const)
    compare_mismatch_block.add_op(compare_mismatch_op)
    compare_mismatch_block.add_op(func.ReturnOp(compare_mismatch_op.results[0]))
    compare_mismatch_module = _module_from_block(
        "compare_scalar_mismatch",
        [nn_memory_type((IntAttr(2),), (IntAttr(1),), f32, SPACE_GLOBAL)],
        [compare_mismatch_result_type],
        compare_mismatch_block,
    )
    with pytest.raises(KernelCodeError, match="nn compare scalar type mismatch"):
        NnLoweringPass().apply(Context(), compare_mismatch_module)


# TC-PASS-NNL-021
# 测试目的: 验证 Lowering 对带符号维度的 cast 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_cast_preserves_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_cast_preserves_symbol_dim() -> None:
    block = Block()
    operand_type = nn_memory_type(
        (IntAttr(2), StringAttr("M")),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    result_type = nn_memory_type(
        (IntAttr(2), StringAttr("M")),
        (IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    operand = add_block_arg(block, operand_type)
    cast_op = NnCastOp(operand, result_type, SPACE_GLOBAL)
    block.add_op(cast_op)
    block.add_op(func.ReturnOp(cast_op.results[0]))
    module = ModuleOp([func.FuncOp("cast", FunctionType.from_lists([operand_type], [result_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_dma_cast_after_first_alloc(block)


# TC-PASS-NNL-022
# 测试目的: 验证 Lowering 对 select 的符号维度保留行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_select_preserves_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_select_preserves_symbol_dim() -> None:
    block = Block()
    cond_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    cond = add_block_arg(block, cond_type)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    select_op = NnSelectOp(cond, lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(select_op)
    block.add_op(func.ReturnOp(select_op.results[0]))
    module = ModuleOp([func.FuncOp("select", FunctionType.from_lists([cond_type, lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_op(block, KernelSelectOp)


# TC-PASS-NNL-023
# 测试目的: 验证 Lowering 对 implicit expand broadcast 的改写行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_broadcast_with_implicit_expand
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_broadcast_with_implicit_expand() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type(
        (IntAttr(1), IntAttr(2), IntAttr(2)),
        (IntAttr(4), IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    operand = add_block_arg(block, operand_type)
    broadcast_op = NnBroadcastOp(operand, result_type, SPACE_GLOBAL)
    block.add_op(broadcast_op)
    block.add_op(func.ReturnOp(broadcast_op.results[0]))
    module = ModuleOp(
        [
            func.FuncOp(
                "broadcast_implicit",
                FunctionType.from_lists([operand_type], [result_type]),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, DmaBroadcastOp)


def _build_broadcast_exp_reduce_min_func() -> func.FuncOp:
    """构造用于测试的 broadcast/exp/reduce_min 组合函数。


    功能说明:
    - 使用 broadcast -> exp -> reduce_min 组合生成测试函数。

    使用示例:
    - func_op = _build_broadcast_exp_reduce_min_func()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: test/passes/lowering/nn_lowering/test_nn_lowering.py
    """

    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    region = Region()
    block = Block(arg_types=[operand_type])
    region.add_block(block)
    broadcast_type = nn_memory_type(
        (IntAttr(2), IntAttr(2), IntAttr(2)),
        (IntAttr(4), IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    broadcast_op = NnBroadcastOp(block.args[0], broadcast_type, SPACE_GLOBAL)
    block.add_op(broadcast_op)
    exp_op = NnExpOp(broadcast_op.results[0], broadcast_type, SPACE_GLOBAL)
    block.add_op(exp_op)
    reduce_op = NnReduceMinOp(
        exp_op.results[0],
        result_type,
        ArrayAttr([IntegerAttr(1, 64)]),
        IntegerAttr(0, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    return func.FuncOp(
        "broadcast_exp_reduce_min",
        FunctionType.from_lists([operand_type], [result_type]),
        region,
    )


def _assert_alloc_count(block: Block, expected: int) -> None:
    """校验 block 内的 dma.alloc 数量。


    功能说明:
    - 统计 block 内 DmaAllocOp 的数量并与预期对齐。

    使用示例:
    - _assert_alloc_count(block, 3)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_nn_lowering.py
    - 功能实现: test/passes/lowering/nn_lowering/test_nn_lowering.py
    """

    alloc_ops = [op for op in block.ops if isinstance(op, DmaAllocOp)]
    assert len(alloc_ops) == expected


# TC-PASS-NNL-024
# 测试目的: 验证 Lowering 在组合场景下对 alloc 的处理。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_combined_ops_alloc
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_combined_ops_alloc() -> None:
    func_op = _build_broadcast_exp_reduce_min_func()
    module = ModuleOp([func_op])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_alloc_count(block, 3)


# TC-PASS-NNL-025
# 测试目的: 验证 Lowering 对非法 add 形状的拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_rejects_invalid_add_shape
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_rejects_invalid_add_shape() -> None:
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(3), IntAttr(3)), (IntAttr(3), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    region = Region()
    block = Block(arg_types=[lhs_type, rhs_type])
    region.add_block(block)

    add_op = NnAddOp(block.args[0], block.args[1], res_type, SPACE_GLOBAL)
    block.add_op(add_op)
    block.add_op(func.ReturnOp(add_op.results[0]))
    func_op = func.FuncOp("bad_add", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), region)
    module = ModuleOp([func_op])

    with pytest.raises(KernelCodeError, match="nn op operands must have the same shape"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-026
# 测试目的: 验证 Lowering 对 unknown dim 的拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_broadcast_rejects_unknown_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_broadcast_rejects_unknown_dim() -> None:
    operand_type = nn_memory_type(
        (IntAttr(2), StringAttr("?")),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    region = Region()
    block = Block(arg_types=[operand_type])
    region.add_block(block)
    broadcast_op = NnBroadcastOp(block.args[0], operand_type, SPACE_GLOBAL)
    block.add_op(broadcast_op)
    block.add_op(func.ReturnOp(broadcast_op.results[0]))
    func_op = func.FuncOp("unknown_dim", FunctionType.from_lists([operand_type], [operand_type]), region)
    module = ModuleOp([func_op])

    with pytest.raises(KernelCodeError, match="nn.broadcast operand shape must not contain '\\?'"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-027
# 测试目的: 验证 Lowering 对 symbol dim cast 的行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_cast_symbol_dim_rejects_mismatch
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_cast_symbol_dim_rejects_mismatch() -> None:
    operand_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    region = Region()
    block = Block(arg_types=[operand_type])
    region.add_block(block)
    cast_op = NnCastOp(block.args[0], result_type, SPACE_GLOBAL)
    block.add_op(cast_op)
    block.add_op(func.ReturnOp(cast_op.results[0]))
    func_op = func.FuncOp("cast_mismatch", FunctionType.from_lists([operand_type], [result_type]), region)
    module = ModuleOp([func_op])

    with pytest.raises(KernelCodeError, match="dma.cast shape mismatch"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-028
# 测试目的: 验证 Lowering 对 select 的 symbol dim 保留。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_select_preserves_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_select_preserves_symbol_dim() -> None:
    block = Block()
    cond_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    lhs_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    cond = add_block_arg(block, cond_type)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    select_op = NnSelectOp(cond, lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(select_op)
    block.add_op(func.ReturnOp(select_op.results[0]))
    module = ModuleOp([func.FuncOp("select", FunctionType.from_lists([cond_type, lhs_type, rhs_type], [res_type]), Region(block))])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_op(block, KernelSelectOp)


# TC-PASS-NNL-029
# 测试目的: 验证 Lowering 对 transpose 动态维度的处理。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_transpose_dynamic
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_transpose_dynamic() -> None:
    operand_type = nn_memory_type(
        (StringAttr("M"), StringAttr("N")),
        (IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    result_type = nn_memory_type(
        (StringAttr("N"), StringAttr("M")),
        (StringAttr("M"), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    region = Region()
    block = Block(arg_types=[operand_type])
    region.add_block(block)
    perm_attr = ArrayAttr([IntegerAttr(1, 64), IntegerAttr(0, 64)])
    transpose_op = NnTransposeOp(block.args[0], result_type, perm_attr, SPACE_GLOBAL)
    block.add_op(transpose_op)
    block.add_op(func.ReturnOp(transpose_op.results[0]))
    func_op = func.FuncOp("transpose_dynamic", FunctionType.from_lists([operand_type], [result_type]), region)
    module = ModuleOp([func_op])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_op(block, DmaTransposeOp)


# TC-PASS-NNL-030
# 测试目的: 验证 Lowering 对 bfloat16 cast 的行为。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_bfloat16_cast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_bfloat16_cast() -> None:
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type(
        (IntAttr(2), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        BFloat16Type(),
        SPACE_GLOBAL,
    )
    region = Region()
    block = Block(arg_types=[operand_type])
    region.add_block(block)
    cast_op = NnCastOp(block.args[0], result_type, SPACE_GLOBAL)
    block.add_op(cast_op)
    block.add_op(func.ReturnOp(cast_op.results[0]))
    func_op = func.FuncOp("cast_bfloat16", FunctionType.from_lists([operand_type], [result_type]), region)
    module = ModuleOp([func_op])

    NnLoweringPass().apply(Context(), module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_dma_cast_after_first_alloc(block)


# TC-PASS-NNL-031
# 测试目的: 验证 Lowering 对未知 op 的拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_rejects_unknown_op
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_rejects_unknown_op() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    unknown_op = NnAddOp(operand, operand, res_type, SPACE_GLOBAL)
    unknown_op.name = "nn.unknown"
    block.add_op(unknown_op)
    block.add_op(func.ReturnOp(unknown_op.results[0]))
    module = ModuleOp([func.FuncOp("unknown", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="unknown op"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-032
# 测试目的: 验证 Lowering 对 reduce_min 维度不一致的拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_reduce_min_rejects_invalid_rank
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_reduce_min_rejects_invalid_rank() -> None:
    operand_type = nn_memory_type(
        (IntAttr(2), StringAttr("M")),
        (IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    res_type = nn_memory_type(
        (IntAttr(2), IntAttr(1)),
        (IntAttr(1), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    region = Region()
    block = Block(arg_types=[operand_type])
    region.add_block(block)
    reduce_op = NnReduceMinOp(
        block.args[0],
        res_type,
        ArrayAttr([IntegerAttr(1, 64)]),
        IntegerAttr(0, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    func_op = func.FuncOp("reduce_min_bad_rank", FunctionType.from_lists([operand_type], [res_type]), region)
    module = ModuleOp([func_op])

    with pytest.raises(KernelCodeError, match="reduce shape rank must match"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-033
# 测试目的: 验证 Lowering 对 reduce_min keepdim 类型的拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_reduce_min_rejects_bad_keepdim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_reduce_min_rejects_bad_keepdim() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr(1, 64)]),
        IntegerAttr(2, 64),
        SPACE_GLOBAL,
    )
    reduce_op.attributes["keepdim"] = StringAttr("bad")
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="keepdim must be integer"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-033A
# 测试目的: 验证 Lowering 对 reduce_min keepdim=-1 的拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_reduce_min_rejects_keepdim_negative_one
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_reduce_min_rejects_keepdim_negative_one() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr(1, 64)]),
        IntegerAttr(-1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="keepdim must be 0 or 1"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-033B
# 测试目的: 验证 reduce 公开 lowering 对 keepdim=false、i1 keepdim 与额外 int operand 的处理矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_reduce_public_keepdim_and_scalar_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_reduce_public_keepdim_and_scalar_matrix() -> None:
    dynamic_type = nn_memory_type(
        (StringAttr("M"), StringAttr("N")),
        (StringAttr("N"), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    keep_false_result_type = nn_memory_type((StringAttr("M"),), (IntAttr(1),), f32, SPACE_GLOBAL)
    keep_false_block = Block(arg_types=[dynamic_type])
    keep_false_op = NnReduceSumOp(keep_false_block.args[0], keep_false_result_type, [1], False, SPACE_GLOBAL)
    keep_false_block.add_op(keep_false_op)
    keep_false_block.add_op(func.ReturnOp(keep_false_op.results[0]))
    keep_false_module = _module_from_block("reduce_keep_false", [dynamic_type], [keep_false_result_type], keep_false_block)

    keep_false_lowered_block = _lowered_func_block(keep_false_module)

    _assert_single_reduce_kind(keep_false_lowered_block, "sum")
    assert len([op for op in keep_false_lowered_block.ops if isinstance(op, SymbolGetDimOp)]) == 1
    keep_false_reduce = next(op for op in keep_false_lowered_block.ops if isinstance(op, KernelReduceOp))
    assert keep_false_reduce.keepdim.value.data == 0

    keep_true_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    keep_true_result_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    keep_true_block = Block(arg_types=[keep_true_type])
    keep_true_op = NnReduceMinOp(
        keep_true_block.args[0],
        keep_true_result_type,
        [1],
        IntegerAttr(-1, 1),
        SPACE_GLOBAL,
    )
    keep_true_block.add_op(keep_true_op)
    keep_true_block.add_op(func.ReturnOp(keep_true_op.results[0]))
    keep_true_module = _module_from_block("reduce_keep_true_i1", [keep_true_type], [keep_true_result_type], keep_true_block)

    keep_true_lowered_block = _lowered_func_block(keep_true_module)

    _assert_single_reduce_kind(keep_true_lowered_block, "min")
    keep_true_reduce = next(op for op in keep_true_lowered_block.ops if isinstance(op, KernelReduceOp))
    assert keep_true_reduce.keepdim.value.data in (1, -1)

    scalar_block = Block(arg_types=[keep_true_type, i32])
    scalar_op = NnReduceMaxOp(scalar_block.args[0], keep_true_result_type, [1], True, SPACE_GLOBAL)
    scalar_op.operands = (scalar_block.args[0], scalar_block.args[1])
    scalar_block.add_op(scalar_op)
    scalar_block.add_op(func.ReturnOp(scalar_op.results[0]))
    scalar_module = _module_from_block("reduce_extra_int_operand", [keep_true_type, i32], [keep_true_result_type], scalar_block)

    scalar_lowered_block = _lowered_func_block(scalar_module)

    _assert_single_reduce_kind(scalar_lowered_block, "max")

    symbol_scalar_block = Block(arg_types=[keep_true_type, SymbolValueType.from_expr("S")])
    symbol_scalar_op = NnReduceMaxOp(symbol_scalar_block.args[0], keep_true_result_type, [1], True, SPACE_GLOBAL)
    symbol_scalar_op.operands = (symbol_scalar_block.args[0], symbol_scalar_block.args[1])
    symbol_scalar_block.add_op(symbol_scalar_op)
    symbol_scalar_block.add_op(func.ReturnOp(symbol_scalar_op.results[0]))
    symbol_scalar_module = _module_from_block(
        "reduce_extra_symbol_operand",
        [keep_true_type, SymbolValueType.from_expr("S")],
        [keep_true_result_type],
        symbol_scalar_block,
    )

    symbol_scalar_lowered_block = _lowered_func_block(symbol_scalar_module)

    _assert_single_reduce_kind(symbol_scalar_lowered_block, "max")


# TC-PASS-NNL-033C
# 测试目的: 验证 reduce 公开 lowering 对 axes/keepdim/operand 属性非法输入的错误矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_reduce_public_attribute_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_reduce_public_attribute_error_matrix() -> None:
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)

    space_missing_block = Block(arg_types=[operand_type])
    space_missing_op = NnReduceSumOp(space_missing_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    space_missing_op.attributes.pop("space")
    space_missing_block.add_op(space_missing_op)
    space_missing_block.add_op(func.ReturnOp(space_missing_op.results[0]))
    space_missing_module = _module_from_block("reduce_space_missing", [operand_type], [result_type], space_missing_block)
    with pytest.raises(KernelCodeError, match="nn op must define #nn.space attribute"):
        NnLoweringPass().apply(Context(), space_missing_module)

    axes_missing_block = Block(arg_types=[operand_type])
    axes_missing_op = NnReduceSumOp(axes_missing_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    axes_missing_op.attributes.pop("axes")
    axes_missing_block.add_op(axes_missing_op)
    axes_missing_block.add_op(func.ReturnOp(axes_missing_op.results[0]))
    axes_missing_module = _module_from_block("reduce_axes_missing", [operand_type], [result_type], axes_missing_block)
    with pytest.raises(KernelCodeError, match="nn.reduce_sum axes must be ArrayAttr"):
        NnLoweringPass().apply(Context(), axes_missing_module)

    keepdim_missing_block = Block(arg_types=[operand_type])
    keepdim_missing_op = NnReduceSumOp(keepdim_missing_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    keepdim_missing_op.attributes.pop("keepdim")
    keepdim_missing_block.add_op(keepdim_missing_op)
    keepdim_missing_block.add_op(func.ReturnOp(keepdim_missing_op.results[0]))
    keepdim_missing_module = _module_from_block("reduce_keepdim_missing", [operand_type], [result_type], keepdim_missing_block)
    with pytest.raises(KernelCodeError, match="nn.reduce_sum keepdim must be bool"):
        NnLoweringPass().apply(Context(), keepdim_missing_module)

    axes_type_block = Block(arg_types=[operand_type])
    axes_type_op = NnReduceSumOp(axes_type_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    axes_type_op.attributes["axes"] = StringAttr("bad")
    axes_type_block.add_op(axes_type_op)
    axes_type_block.add_op(func.ReturnOp(axes_type_op.results[0]))
    axes_type_module = _module_from_block("reduce_axes_type", [operand_type], [result_type], axes_type_block)
    with pytest.raises(KernelCodeError, match="nn.reduce_sum axes must be ArrayAttr"):
        NnLoweringPass().apply(Context(), axes_type_module)

    empty_axes_block = Block(arg_types=[operand_type])
    empty_axes_op = NnReduceSumOp(empty_axes_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    empty_axes_op.attributes["axes"] = ArrayAttr([])
    empty_axes_block.add_op(empty_axes_op)
    empty_axes_block.add_op(func.ReturnOp(empty_axes_op.results[0]))
    empty_axes_module = _module_from_block("reduce_axes_empty", [operand_type], [result_type], empty_axes_block)
    with pytest.raises(KernelCodeError, match="reduce axes must be non-empty"):
        NnLoweringPass().apply(Context(), empty_axes_module)

    multi_axes_block = Block(arg_types=[operand_type])
    multi_axes_op = NnReduceSumOp(multi_axes_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    multi_axes_op.attributes["axes"] = ArrayAttr([IntegerAttr(0, 64), IntegerAttr(1, 64)])
    multi_axes_block.add_op(multi_axes_op)
    multi_axes_block.add_op(func.ReturnOp(multi_axes_op.results[0]))
    multi_axes_module = _module_from_block("reduce_axes_many", [operand_type], [result_type], multi_axes_block)
    with pytest.raises(KernelCodeError, match="reduce axes must contain exactly one element"):
        NnLoweringPass().apply(Context(), multi_axes_module)

    int_axes_block = Block(arg_types=[operand_type])
    int_axes_op = NnReduceSumOp(int_axes_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    int_axes_op.attributes["axes"] = ArrayAttr([IntAttr(1)])
    int_axes_block.add_op(int_axes_op)
    int_axes_block.add_op(func.ReturnOp(int_axes_op.results[0]))
    int_axes_module = _module_from_block("reduce_axes_intattr", [operand_type], [result_type], int_axes_block)
    int_axes_lowered_block = _lowered_func_block(int_axes_module)
    _assert_single_reduce_kind(int_axes_lowered_block, "sum")

    bad_axis_block = Block(arg_types=[operand_type])
    bad_axis_op = NnReduceSumOp(bad_axis_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    bad_axis_op.attributes["axes"] = ArrayAttr([StringAttr("bad")])
    bad_axis_block.add_op(bad_axis_op)
    bad_axis_block.add_op(func.ReturnOp(bad_axis_op.results[0]))
    bad_axis_module = _module_from_block("reduce_axis_bad", [operand_type], [result_type], bad_axis_block)
    with pytest.raises(KernelCodeError, match="reduce axis must be integer"):
        NnLoweringPass().apply(Context(), bad_axis_module)

    bad_keepdim_block = Block(arg_types=[operand_type])
    bad_keepdim_op = NnReduceSumOp(bad_keepdim_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    bad_keepdim_op.attributes["keepdim"] = IntAttr(2)
    bad_keepdim_block.add_op(bad_keepdim_op)
    bad_keepdim_block.add_op(func.ReturnOp(bad_keepdim_op.results[0]))
    bad_keepdim_module = _module_from_block("reduce_keepdim_bad_value", [operand_type], [result_type], bad_keepdim_block)
    with pytest.raises(KernelCodeError, match="keepdim must be 0 or 1"):
        NnLoweringPass().apply(Context(), bad_keepdim_module)

    bad_integer_keepdim_block = Block(arg_types=[operand_type])
    bad_integer_keepdim_op = NnReduceSumOp(bad_integer_keepdim_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    bad_integer_keepdim_op.attributes["keepdim"] = IntegerAttr(2, 8)
    bad_integer_keepdim_block.add_op(bad_integer_keepdim_op)
    bad_integer_keepdim_block.add_op(func.ReturnOp(bad_integer_keepdim_op.results[0]))
    bad_integer_keepdim_module = _module_from_block(
        "reduce_keepdim_bad_integer_value",
        [operand_type],
        [result_type],
        bad_integer_keepdim_block,
    )
    with pytest.raises(KernelCodeError, match="keepdim must be 0 or 1"):
        NnLoweringPass().apply(Context(), bad_integer_keepdim_module)

    arity_block = Block(arg_types=[operand_type, i32, i32])
    arity_op = NnReduceSumOp(arity_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    arity_op.operands = (arity_block.args[0], arity_block.args[1], arity_block.args[2])
    arity_block.add_op(arity_op)
    arity_block.add_op(func.ReturnOp(arity_op.results[0]))
    arity_module = _module_from_block("reduce_arity_error", [operand_type, i32, i32], [result_type], arity_block)
    with pytest.raises(KernelCodeError, match="nn.reduce_sum must have 1 operands"):
        NnLoweringPass().apply(Context(), arity_module)

    non_memory_block = Block(arg_types=[i32])
    non_memory_op = NnReduceSumOp(non_memory_block.args[0], result_type, [1], True, SPACE_GLOBAL)
    non_memory_block.add_op(non_memory_op)
    non_memory_block.add_op(func.ReturnOp(non_memory_op.results[0]))
    non_memory_module = _module_from_block("reduce_operand_error", [i32], [result_type], non_memory_block)
    with pytest.raises(KernelCodeError, match="nn.reduce operand must be nn.memory"):
        NnLoweringPass().apply(Context(), non_memory_module)


# TC-PASS-NNL-033D
# 测试目的: 验证 reduce 公开 lowering 对 keepdim 与非 keepdim 输出 shape 不匹配的错误矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_reduce_public_shape_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_reduce_public_shape_error_matrix() -> None:
    dynamic_type = nn_memory_type(
        (StringAttr("M"), StringAttr("N")),
        (StringAttr("N"), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )

    reduced_symbol_result_type = nn_memory_type((StringAttr("M"), StringAttr("N")), (StringAttr("N"), IntAttr(1)), f32, SPACE_GLOBAL)
    reduced_symbol_block = Block(arg_types=[dynamic_type])
    reduced_symbol_op = NnReduceMinOp(reduced_symbol_block.args[0], reduced_symbol_result_type, [1], True, SPACE_GLOBAL)
    reduced_symbol_block.add_op(reduced_symbol_op)
    reduced_symbol_block.add_op(func.ReturnOp(reduced_symbol_op.results[0]))
    reduced_symbol_module = _module_from_block(
        "reduce_keepdim_symbol_axis",
        [dynamic_type],
        [reduced_symbol_result_type],
        reduced_symbol_block,
    )
    with pytest.raises(KernelCodeError, match="reduce keepdim dimension must be 1"):
        NnLoweringPass().apply(Context(), reduced_symbol_module)

    reduced_static_result_type = nn_memory_type((StringAttr("M"), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    reduced_static_block = Block(arg_types=[dynamic_type])
    reduced_static_op = NnReduceMinOp(reduced_static_block.args[0], reduced_static_result_type, [1], True, SPACE_GLOBAL)
    reduced_static_block.add_op(reduced_static_op)
    reduced_static_block.add_op(func.ReturnOp(reduced_static_op.results[0]))
    reduced_static_module = _module_from_block(
        "reduce_keepdim_static_axis",
        [dynamic_type],
        [reduced_static_result_type],
        reduced_static_block,
    )
    with pytest.raises(KernelCodeError, match="reduce keepdim dimension must be 1"):
        NnLoweringPass().apply(Context(), reduced_static_module)

    keepdim_symbol_mismatch_type = nn_memory_type((StringAttr("K"), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    keepdim_symbol_block = Block(arg_types=[dynamic_type])
    keepdim_symbol_op = NnReduceMinOp(keepdim_symbol_block.args[0], keepdim_symbol_mismatch_type, [1], True, SPACE_GLOBAL)
    keepdim_symbol_block.add_op(keepdim_symbol_op)
    keepdim_symbol_block.add_op(func.ReturnOp(keepdim_symbol_op.results[0]))
    keepdim_symbol_module = _module_from_block(
        "reduce_keepdim_symbol_mismatch",
        [dynamic_type],
        [keepdim_symbol_mismatch_type],
        keepdim_symbol_block,
    )
    with pytest.raises(KernelCodeError, match="reduce shape mismatch"):
        NnLoweringPass().apply(Context(), keepdim_symbol_module)

    keepdim_static_input_type = nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), f32, SPACE_GLOBAL)
    keepdim_static_mismatch_type = nn_memory_type((IntAttr(4), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    keepdim_static_block = Block(arg_types=[keepdim_static_input_type])
    keepdim_static_op = NnReduceMinOp(keepdim_static_block.args[0], keepdim_static_mismatch_type, [1], True, SPACE_GLOBAL)
    keepdim_static_block.add_op(keepdim_static_op)
    keepdim_static_block.add_op(func.ReturnOp(keepdim_static_op.results[0]))
    keepdim_static_module = _module_from_block(
        "reduce_keepdim_static_mismatch",
        [keepdim_static_input_type],
        [keepdim_static_mismatch_type],
        keepdim_static_block,
    )
    with pytest.raises(KernelCodeError, match="reduce shape mismatch"):
        NnLoweringPass().apply(Context(), keepdim_static_module)

    keepdim_type_mismatch_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    keepdim_type_block = Block(arg_types=[dynamic_type])
    keepdim_type_op = NnReduceMinOp(keepdim_type_block.args[0], keepdim_type_mismatch_type, [1], True, SPACE_GLOBAL)
    keepdim_type_block.add_op(keepdim_type_op)
    keepdim_type_block.add_op(func.ReturnOp(keepdim_type_op.results[0]))
    keepdim_type_module = _module_from_block(
        "reduce_keepdim_type_mismatch",
        [dynamic_type],
        [keepdim_type_mismatch_type],
        keepdim_type_block,
    )
    with pytest.raises(KernelCodeError, match="reduce shape mismatch"):
        NnLoweringPass().apply(Context(), keepdim_type_module)

    no_keepdim_symbol_type = nn_memory_type((StringAttr("K"),), (IntAttr(1),), f32, SPACE_GLOBAL)
    no_keepdim_symbol_block = Block(arg_types=[dynamic_type])
    no_keepdim_symbol_op = NnReduceMinOp(no_keepdim_symbol_block.args[0], no_keepdim_symbol_type, [1], False, SPACE_GLOBAL)
    no_keepdim_symbol_block.add_op(no_keepdim_symbol_op)
    no_keepdim_symbol_block.add_op(func.ReturnOp(no_keepdim_symbol_op.results[0]))
    no_keepdim_symbol_module = _module_from_block(
        "reduce_no_keepdim_symbol_mismatch",
        [dynamic_type],
        [no_keepdim_symbol_type],
        no_keepdim_symbol_block,
    )
    with pytest.raises(KernelCodeError, match="reduce shape mismatch"):
        NnLoweringPass().apply(Context(), no_keepdim_symbol_module)

    no_keepdim_static_type = nn_memory_type((IntAttr(4),), (IntAttr(1),), f32, SPACE_GLOBAL)
    no_keepdim_static_block = Block(arg_types=[keepdim_static_input_type])
    no_keepdim_static_op = NnReduceMinOp(no_keepdim_static_block.args[0], no_keepdim_static_type, [1], False, SPACE_GLOBAL)
    no_keepdim_static_block.add_op(no_keepdim_static_op)
    no_keepdim_static_block.add_op(func.ReturnOp(no_keepdim_static_op.results[0]))
    no_keepdim_static_module = _module_from_block(
        "reduce_no_keepdim_static_mismatch",
        [keepdim_static_input_type],
        [no_keepdim_static_type],
        no_keepdim_static_block,
    )
    with pytest.raises(KernelCodeError, match="reduce shape mismatch"):
        NnLoweringPass().apply(Context(), no_keepdim_static_module)

    no_keepdim_type_mismatch_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), f32, SPACE_GLOBAL)
    no_keepdim_type_block = Block(arg_types=[dynamic_type])
    no_keepdim_type_op = NnReduceMinOp(no_keepdim_type_block.args[0], no_keepdim_type_mismatch_type, [1], False, SPACE_GLOBAL)
    no_keepdim_type_block.add_op(no_keepdim_type_op)
    no_keepdim_type_block.add_op(func.ReturnOp(no_keepdim_type_op.results[0]))
    no_keepdim_type_module = _module_from_block(
        "reduce_no_keepdim_type_mismatch",
        [dynamic_type],
        [no_keepdim_type_mismatch_type],
        no_keepdim_type_block,
    )
    with pytest.raises(KernelCodeError, match="reduce shape mismatch"):
        NnLoweringPass().apply(Context(), no_keepdim_type_module)


# TC-PASS-NNL-034
# 测试目的: 验证 Lowering 对 broadcast 形状不匹配的拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_broadcast_rejects_invalid_shape
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_broadcast_rejects_invalid_shape() -> None:
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type(
        (IntAttr(3), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    block = Block(arg_types=[operand_type])
    broadcast_op = NnBroadcastOp(block.args[0], result_type, SPACE_GLOBAL)
    block.add_op(broadcast_op)
    block.add_op(func.ReturnOp(broadcast_op.results[0]))
    func_op = func.FuncOp(
        "broadcast_invalid",
        FunctionType.from_lists([operand_type], [result_type]),
        Region(block),
    )
    module = ModuleOp([func_op])

    with pytest.raises(KernelCodeError, match="invalid broadcast target shape"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-035
# 测试目的: 验证 Lowering 对 broadcast 标量使用的拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_broadcast_rejects_invalid_scalar
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_broadcast_rejects_invalid_scalar() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    scalar = add_block_arg(block, StringAttr)
    broadcast_op = NnBroadcastOp(operand, result_type, SPACE_GLOBAL)
    broadcast_op.operands = (operand, scalar)
    block.add_op(broadcast_op)
    block.add_op(func.ReturnOp(broadcast_op.results[0]))
    module = ModuleOp([func.FuncOp("broadcast_scalar", FunctionType.from_lists([operand_type, StringAttr], [result_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="broadcast scalar must be int or symbol"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-035A
# 测试目的: 验证公开 NnLoweringPass 对 broadcast 动态维度、已有 symbol SSA 与标量 operand 的处理矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_broadcast_public_dynamic_dim_and_scalar_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_broadcast_public_dynamic_dim_and_scalar_matrix() -> None:
    operand_type = nn_memory_type((StringAttr("M"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    result_type = nn_memory_type(
        (StringAttr("K"), StringAttr("M")),
        (StringAttr("M"), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    block = Block(arg_types=[SymbolValueType.from_expr("K"), operand_type])
    broadcast_op = NnBroadcastOp(block.args[1], result_type, SPACE_GLOBAL)
    block.add_op(broadcast_op)
    block.add_op(func.ReturnOp(broadcast_op.results[0]))
    module = _module_from_block(
        "broadcast_block_symbol",
        [SymbolValueType.from_expr("K"), operand_type],
        [result_type],
        block,
    )

    lowered_block = _lowered_func_block(module)

    _assert_single_op(lowered_block, DmaBroadcastOp)
    assert len([op for op in lowered_block.ops if isinstance(op, SymbolGetDimOp)]) == 1
    alloc_op = next(op for op in lowered_block.ops if isinstance(op, DmaAllocOp))
    assert len(alloc_op.dynamic_shape) == 2

    repeated_type = nn_memory_type((StringAttr("M"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    repeated_result_type = nn_memory_type(
        (StringAttr("M"), StringAttr("M")),
        (StringAttr("M"), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    repeated_block = Block(arg_types=[repeated_type])
    repeated_op = NnBroadcastOp(repeated_block.args[0], repeated_result_type, SPACE_GLOBAL)
    repeated_block.add_op(repeated_op)
    repeated_block.add_op(func.ReturnOp(repeated_op.results[0]))
    repeated_module = _module_from_block("broadcast_repeated_symbol", [repeated_type], [repeated_result_type], repeated_block)

    repeated_lowered_block = _lowered_func_block(repeated_module)

    _assert_single_op(repeated_lowered_block, DmaBroadcastOp)
    assert len([op for op in repeated_lowered_block.ops if isinstance(op, SymbolGetDimOp)]) == 1

    source_reuse_type = nn_memory_type((IntAttr(1), StringAttr("M")), (StringAttr("M"), IntAttr(1)), i32, SPACE_GLOBAL)
    source_reuse_result_type = nn_memory_type(
        (StringAttr("M"), StringAttr("M")),
        (StringAttr("M"), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    source_reuse_block = Block(arg_types=[source_reuse_type])
    source_reuse_op = NnBroadcastOp(source_reuse_block.args[0], source_reuse_result_type, SPACE_GLOBAL)
    source_reuse_block.add_op(source_reuse_op)
    source_reuse_block.add_op(func.ReturnOp(source_reuse_op.results[0]))
    source_reuse_module = _module_from_block(
        "broadcast_reuse_source_symbol",
        [source_reuse_type],
        [source_reuse_result_type],
        source_reuse_block,
    )

    source_reuse_lowered_block = _lowered_func_block(source_reuse_module)

    _assert_single_op(source_reuse_lowered_block, DmaBroadcastOp)
    assert len([op for op in source_reuse_lowered_block.ops if isinstance(op, SymbolGetDimOp)]) == 1

    seed_type = nn_memory_type((StringAttr("K"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    expand_type = nn_memory_type((IntAttr(1), StringAttr("M")), (StringAttr("M"), IntAttr(1)), i32, SPACE_GLOBAL)
    expand_result_type = nn_memory_type(
        (StringAttr("K"), StringAttr("M")),
        (StringAttr("M"), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    expand_block = Block(arg_types=[seed_type, expand_type])
    seed_symbol = SymbolGetDimOp(expand_block.args[0], IntAttr(0))
    expand_block.add_op(seed_symbol)
    expand_op = NnBroadcastOp(expand_block.args[1], expand_result_type, SPACE_GLOBAL)
    expand_block.add_op(expand_op)
    expand_block.add_op(func.ReturnOp(expand_op.results[0]))
    expand_module = _module_from_block("broadcast_reuse_previous_symbol", [seed_type, expand_type], [expand_result_type], expand_block)

    expand_lowered_block = _lowered_func_block(expand_module)

    _assert_single_op(expand_lowered_block, DmaBroadcastOp)
    assert len([op for op in expand_lowered_block.ops if isinstance(op, SymbolGetDimOp)]) == 2

    scalar_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL)
    scalar_block = Block(arg_types=[scalar_type, i32, SymbolValueType.from_expr("S")])
    int_scalar_op = NnBroadcastOp(scalar_block.args[0], scalar_type, SPACE_GLOBAL)
    int_scalar_op.operands = (scalar_block.args[0], scalar_block.args[1])
    symbol_scalar_op = NnBroadcastOp(int_scalar_op.results[0], scalar_type, SPACE_GLOBAL)
    symbol_scalar_op.operands = (int_scalar_op.results[0], scalar_block.args[2])
    scalar_block.add_op(int_scalar_op)
    scalar_block.add_op(symbol_scalar_op)
    scalar_block.add_op(func.ReturnOp(symbol_scalar_op.results[0]))
    scalar_module = _module_from_block(
        "broadcast_scalar_matrix",
        [scalar_type, i32, SymbolValueType.from_expr("S")],
        [scalar_type],
        scalar_block,
    )

    scalar_lowered_block = _lowered_func_block(scalar_module)

    assert len([op for op in scalar_lowered_block.ops if isinstance(op, DmaBroadcastOp)]) == 2


# TC-PASS-NNL-035B
# 测试目的: 验证公开 NnLoweringPass 对 broadcast shape/operand 非法输入的稳定错误矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_broadcast_public_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_broadcast_public_error_matrix() -> None:
    rank_operand_type = nn_memory_type(
        (StringAttr("M"), StringAttr("N")),
        (StringAttr("N"), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    rank_result_type = nn_memory_type((StringAttr("M"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    rank_block = Block(arg_types=[rank_operand_type])
    rank_op = NnBroadcastOp(rank_block.args[0], rank_result_type, SPACE_GLOBAL)
    rank_block.add_op(rank_op)
    rank_block.add_op(func.ReturnOp(rank_op.results[0]))
    rank_module = _module_from_block("broadcast_rank_error", [rank_operand_type], [rank_result_type], rank_block)
    with pytest.raises(KernelCodeError, match="nn.broadcast result rank must be >= operand rank"):
        NnLoweringPass().apply(Context(), rank_module)

    int_operand_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL)
    symbol_result_type = nn_memory_type((StringAttr("M"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    int_block = Block(arg_types=[int_operand_type])
    int_op = NnBroadcastOp(int_block.args[0], symbol_result_type, SPACE_GLOBAL)
    int_block.add_op(int_op)
    int_block.add_op(func.ReturnOp(int_op.results[0]))
    int_module = _module_from_block("broadcast_int_to_symbol_error", [int_operand_type], [symbol_result_type], int_block)
    with pytest.raises(KernelCodeError, match="NnLoweringBroadcastSymbolDimNotFromSource: result dim not in source"):
        NnLoweringPass().apply(Context(), int_module)

    source_one_type = nn_memory_type((IntAttr(1), StringAttr("M")), (StringAttr("M"), IntAttr(1)), i32, SPACE_GLOBAL)
    missing_symbol_result_type = nn_memory_type(
        (StringAttr("K"), StringAttr("M")),
        (StringAttr("M"), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    missing_symbol_block = Block(arg_types=[source_one_type])
    missing_symbol_op = NnBroadcastOp(missing_symbol_block.args[0], missing_symbol_result_type, SPACE_GLOBAL)
    missing_symbol_block.add_op(missing_symbol_op)
    missing_symbol_block.add_op(func.ReturnOp(missing_symbol_op.results[0]))
    missing_symbol_module = _module_from_block(
        "broadcast_missing_block_symbol",
        [source_one_type],
        [missing_symbol_result_type],
        missing_symbol_block,
    )
    with pytest.raises(KernelCodeError, match="NnLoweringBroadcastSymbolDimNotFromSource: result dim not in source"):
        NnLoweringPass().apply(Context(), missing_symbol_module)

    source_axis_result_type = nn_memory_type(
        (StringAttr("K"), StringAttr("M")),
        (StringAttr("M"), IntAttr(1)),
        i32,
        SPACE_GLOBAL,
    )
    source_axis_block = Block(arg_types=[operand_type := nn_memory_type((StringAttr("M"),), (IntAttr(1),), i32, SPACE_GLOBAL)])
    source_axis_op = NnBroadcastOp(source_axis_block.args[0], source_axis_result_type, SPACE_GLOBAL)
    source_axis_block.add_op(source_axis_op)
    source_axis_block.add_op(func.ReturnOp(source_axis_op.results[0]))
    source_axis_module = _module_from_block("broadcast_axis_out_error", [operand_type], [source_axis_result_type], source_axis_block)
    with pytest.raises(KernelCodeError, match="NnLoweringBroadcastSymbolDimNotFromSource: axis out of range"):
        NnLoweringPass().apply(Context(), source_axis_module)

    mismatch_operand_type = nn_memory_type((StringAttr("M"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    mismatch_result_type = nn_memory_type((StringAttr("N"),), (IntAttr(1),), i32, SPACE_GLOBAL)
    mismatch_block = Block(arg_types=[mismatch_operand_type])
    mismatch_op = NnBroadcastOp(mismatch_block.args[0], mismatch_result_type, SPACE_GLOBAL)
    mismatch_block.add_op(mismatch_op)
    mismatch_block.add_op(func.ReturnOp(mismatch_op.results[0]))
    mismatch_module = _module_from_block("broadcast_symbol_mismatch", [mismatch_operand_type], [mismatch_result_type], mismatch_block)
    with pytest.raises(KernelCodeError, match="NnLoweringBroadcastSymbolDimNotFromSource: symbol mismatch"):
        NnLoweringPass().apply(Context(), mismatch_module)

    invalid_target_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL)
    invalid_target_block = Block(arg_types=[mismatch_operand_type])
    invalid_target_op = NnBroadcastOp(invalid_target_block.args[0], invalid_target_type, SPACE_GLOBAL)
    invalid_target_block.add_op(invalid_target_op)
    invalid_target_block.add_op(func.ReturnOp(invalid_target_op.results[0]))
    invalid_target_module = _module_from_block(
        "broadcast_symbol_to_int_error",
        [mismatch_operand_type],
        [invalid_target_type],
        invalid_target_block,
    )
    with pytest.raises(KernelCodeError, match="invalid broadcast target shape"):
        NnLoweringPass().apply(Context(), invalid_target_module)

    arity_block = Block(arg_types=[invalid_target_type, i32, i32])
    arity_op = NnBroadcastOp(arity_block.args[0], invalid_target_type, SPACE_GLOBAL)
    arity_op.operands = (arity_block.args[0], arity_block.args[1], arity_block.args[2])
    arity_block.add_op(arity_op)
    arity_block.add_op(func.ReturnOp(arity_op.results[0]))
    arity_module = _module_from_block("broadcast_arity_error", [invalid_target_type, i32, i32], [invalid_target_type], arity_block)
    with pytest.raises(KernelCodeError, match="nn.broadcast must have 1 operands"):
        NnLoweringPass().apply(Context(), arity_module)

    non_memory_block = Block(arg_types=[i32])
    non_memory_op = NnBroadcastOp(non_memory_block.args[0], invalid_target_type, SPACE_GLOBAL)
    non_memory_block.add_op(non_memory_op)
    non_memory_block.add_op(func.ReturnOp(non_memory_op.results[0]))
    non_memory_module = _module_from_block("broadcast_operand_error", [i32], [invalid_target_type], non_memory_block)
    with pytest.raises(KernelCodeError, match="nn.broadcast operand must be nn.memory"):
        NnLoweringPass().apply(Context(), non_memory_module)


# TC-PASS-NNL-035C
# 测试目的: 验证公开 NnLoweringPass 对 transpose 非法 operand/perm/shape 输入的稳定错误矩阵。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_lower_transpose_public_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_lower_transpose_public_error_matrix() -> None:
    static_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), f32, SPACE_GLOBAL)
    non_memory_block = Block(arg_types=[i32])
    non_memory_op = NnTransposeOp(non_memory_block.args[0], static_type, [0], SPACE_GLOBAL)
    non_memory_block.add_op(non_memory_op)
    non_memory_block.add_op(func.ReturnOp(non_memory_op.results[0]))
    non_memory_module = _module_from_block("transpose_operand_error", [i32], [static_type], non_memory_block)
    with pytest.raises(KernelCodeError, match="nn.transpose operand must be nn.memory"):
        NnLoweringPass().apply(Context(), non_memory_module)

    bad_perm_block = Block(arg_types=[static_type])
    bad_perm_op = NnTransposeOp(bad_perm_block.args[0], static_type, [0], SPACE_GLOBAL)
    bad_perm_op.attributes["perm"] = StringAttr("bad")
    bad_perm_block.add_op(bad_perm_op)
    bad_perm_block.add_op(func.ReturnOp(bad_perm_op.results[0]))
    bad_perm_module = _module_from_block("transpose_perm_attr_error", [static_type], [static_type], bad_perm_block)
    with pytest.raises(KernelCodeError, match="nn.transpose perm must be ArrayAttr"):
        NnLoweringPass().apply(Context(), bad_perm_module)

    matrix_type = nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), f32, SPACE_GLOBAL)
    matrix_result_type = nn_memory_type((IntAttr(3), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    rank_block = Block(arg_types=[matrix_type])
    rank_op = NnTransposeOp(rank_block.args[0], matrix_result_type, [1], SPACE_GLOBAL)
    rank_block.add_op(rank_op)
    rank_block.add_op(func.ReturnOp(rank_op.results[0]))
    rank_module = _module_from_block("transpose_rank_error", [matrix_type], [matrix_result_type], rank_block)
    with pytest.raises(KernelCodeError, match="nn.transpose perm rank mismatch"):
        NnLoweringPass().apply(Context(), rank_module)

    unknown_type = nn_memory_type((StringAttr("?"),), (IntAttr(1),), f32, SPACE_GLOBAL)
    unknown_block = Block(arg_types=[unknown_type])
    unknown_op = NnTransposeOp(unknown_block.args[0], unknown_type, [0], SPACE_GLOBAL)
    unknown_block.add_op(unknown_op)
    unknown_block.add_op(func.ReturnOp(unknown_op.results[0]))
    unknown_module = _module_from_block("transpose_unknown_dim_error", [unknown_type], [unknown_type], unknown_block)
    with pytest.raises(KernelCodeError, match="nn.transpose operand shape must not contain '\\?'"):
        NnLoweringPass().apply(Context(), unknown_module)

    source_symbol_type = nn_memory_type((StringAttr("M"),), (IntAttr(1),), f32, SPACE_GLOBAL)
    missing_result_type = nn_memory_type((StringAttr("N"),), (IntAttr(1),), f32, SPACE_GLOBAL)
    missing_block = Block(arg_types=[source_symbol_type])
    missing_op = NnTransposeOp(missing_block.args[0], missing_result_type, [0], SPACE_GLOBAL)
    missing_block.add_op(missing_op)
    missing_block.add_op(func.ReturnOp(missing_op.results[0]))
    missing_module = _module_from_block("transpose_result_dim_error", [source_symbol_type], [missing_result_type], missing_block)
    with pytest.raises(KernelCodeError, match="nn.transpose result dim not in source"):
        NnLoweringPass().apply(Context(), missing_module)


# TC-PASS-NNL-036
# 测试目的: 验证 Lowering 对 matmul stride 的验证。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_matmul_requires_contiguous_stride
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_matmul_requires_contiguous_stride() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), f32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(3), IntAttr(4)), (IntAttr(4), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(4)), (IntAttr(5), IntAttr(1)), f32, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    matmul_op = NnMatmulOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(matmul_op)
    block.add_op(func.ReturnOp(matmul_op.results[0]))
    module = ModuleOp([func.FuncOp("matmul", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="matmul stride must be contiguous"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-037
# 测试目的: 验证 Lowering 对 reduce axes 校验。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_reduce_axes_validation
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_reduce_axes_validation() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([]),
        IntegerAttr(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="reduce axes must be non-empty"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-038
# 测试目的: 验证 Lowering 对 reduce keepdim 校验。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_reduce_keepdim_validation
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_reduce_keepdim_validation() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr(1, 64)]),
        IntegerAttr(2, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="keepdim must be 0 or 1"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-039
# 测试目的: 验证 direct `nn.softmax` 即使 axis 非法，也会先按“需先分解”路径拒绝。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k test_softmax_requires_decompass_before_axis_validation
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_nn_lowering.py
def test_softmax_requires_decompass_before_axis_validation() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    softmax_op = NnSoftmaxOp(
        operand,
        res_type,
        IntegerAttr(-1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(softmax_op)
    block.add_op(func.ReturnOp(softmax_op.results[0]))
    module = ModuleOp([func.FuncOp("softmax", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(KernelCodeError, match="nn.softmax must be decomposed before lower-nn"):
        NnLoweringPass().apply(Context(), module)
