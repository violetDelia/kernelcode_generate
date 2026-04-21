"""nn -> kernel lowering pass tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 nn_lowering pass 的 lowering 行为与错误路径。

使用示例:
- pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py

当前覆盖率信息:
- `kernel_gen.passes.lowering.nn_lowering`：`100%`（2026-03-23 04:07:56 +0800，`15 passed`）。

覆盖率命令:
- `pytest --cov=kernel_gen.passes.lowering.nn_lowering --cov-report=term-missing -q test/pass/nn_lowering/test_lowering_nn_lowering.py`

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering.md
- 测试文件: test/pass/nn_lowering/test_lowering_nn_lowering.py
"""

from __future__ import annotations

import sys
import importlib
from pathlib import Path
from collections.abc import Callable

import pytest
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

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.nn import img2col1d, img2col2d, reduce_min
from kernel_gen.passes.buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
pass_module = importlib.import_module("kernel_gen.passes.lowering.nn_lowering")
compat_pass_module = importlib.import_module("kernel_gen.passes.lowering.nn_to_kernel")
LowerNnToKernelPass = compat_pass_module.LowerNnToKernelPass
NnLoweringError = pass_module.NnLoweringError
NnLoweringPass = pass_module.NnLoweringPass

SPACE_GLOBAL = NnMemorySpaceAttr(StringAttr("global"))


def nn_memory_type(
    shape: tuple[Attribute, ...],
    stride: tuple[Attribute, ...],
    element_type: Attribute,
    space: NnMemorySpaceAttr = SPACE_GLOBAL,
) -> NnMemoryType:
    """构造 nn.memory 测试类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 shape/stride 的 tuple 转为 ArrayAttr。

    使用示例:
    - nn_memory_type((IntAttr(2),), (IntAttr(1),), i32)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: test/pass/nn_lowering/test_lowering_nn_lowering.py
    """

    return NnMemoryType(ArrayAttr(list(shape)), ArrayAttr(list(stride)), element_type, space)


def add_block_arg(block: Block, arg_type: Attribute) -> SSAValue:
    """向 Block 追加参数并返回。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 insert_arg 在末尾插入 block argument。

    使用示例:
    - lhs = add_block_arg(block, nn_memory_type((IntAttr(2),), (IntAttr(1),), i32))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确保 dma.cast 紧跟在第一个 dma.alloc 后。

    使用示例:
    - _assert_single_dma_cast_after_first_alloc(block)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
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


# TC-PASS-NNL-001
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.add 的改写行为，生成 kernel.binary_elewise(kind="add")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_add_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind_after_first_alloc(block, "add")


# TC-PASS-NNL-001A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-20 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-20 00:00:00 +0800
# 测试目的: 验证 `LowerNnToKernelPass` 仅保留旧 pass 名，不回写旧具名 add op。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_nn_to_kernel_compat_keeps_binary_elewise
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_nn_to_kernel_compat_keeps_binary_elewise() -> None:
    block = Block()
    lhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    lhs = add_block_arg(block, lhs_type)
    rhs = add_block_arg(block, rhs_type)
    add_op = NnAddOp(lhs, rhs, res_type, SPACE_GLOBAL)
    block.add_op(add_op)
    block.add_op(func.ReturnOp(add_op.results[0]))
    module = ModuleOp(
        [func.FuncOp("add_compat", FunctionType.from_lists([lhs_type, rhs_type], [res_type]), Region(block))]
    )

    LowerNnToKernelPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind_after_first_alloc(block, "add")
    assert all(op.name != "kernel.binary_elewise" or op.attributes.get("kind").data == "add" for op in block.ops)


# TC-PASS-NNL-002
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.truediv 的改写行为，统一生成 kernel.binary_elewise(kind="div")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_div_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "div")


# TC-PASS-NNL-003
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.eq 的改写行为，生成 kernel.binary_elewise(kind="eq")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_eq_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "eq")


# TC-PASS-NNL-004
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.ne 的改写行为，生成 kernel.binary_elewise(kind="ne")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_ne_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "ne")


# TC-PASS-NNL-005
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.le 的改写行为，生成 kernel.binary_elewise(kind="le")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_le_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "le")


# TC-PASS-NNL-006
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.lt 的改写行为，生成 kernel.binary_elewise(kind="lt")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_lt_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "lt")


# TC-PASS-NNL-007
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.gt 的改写行为，生成 kernel.binary_elewise(kind="gt")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_gt_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "gt")


# TC-PASS-NNL-008
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.ge 的改写行为，生成 kernel.binary_elewise(kind="ge")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_ge_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_binary_kind(block, "ge")


# TC-PASS-NNL-009
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.exp 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_exp_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_exp_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    exp_op = NnExpOp(operand, res_type, SPACE_GLOBAL)
    block.add_op(exp_op)
    block.add_op(func.ReturnOp(exp_op.results[0]))
    module = ModuleOp([func.FuncOp("exp", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, KernelExpOp)


# TC-PASS-NNL-010
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.reduce_min 的改写行为，生成 kernel.reduce(kind="min")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_reduce_min_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_reduce_min_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_reduce_kind(block, "min")


# TC-PASS-NNL-010A
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 07:50:00 +0800
# 最近一次运行成功时间: 2026-04-12 07:50:00 +0800
# 测试目的: 验证 Lowering 对 nn.reduce_sum 的改写行为，生成 kernel.reduce(kind="sum")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_reduce_sum_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_reduce_sum_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(1), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceSumOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr.from_int_and_width(0, 64)]),
        IntegerAttr.from_int_and_width(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_sum", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_reduce_kind(block, "sum")


# TC-PASS-NNL-010B
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 07:50:00 +0800
# 最近一次运行成功时间: 2026-04-12 07:50:00 +0800
# 测试目的: 验证 Lowering 对 nn.reduce_max 的改写行为，生成 kernel.reduce(kind="max")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_reduce_max_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_reduce_max_to_kernel() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMaxOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_max", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_reduce_kind(block, "max")


# TC-PASS-NNL-011
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 direct `nn.softmax` 会被拒绝，并提示需要先做分解。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_softmax_requires_decompass
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_softmax_requires_decompass() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    softmax_op = NnSoftmaxOp(
        operand,
        res_type,
        IntegerAttr.from_int_and_width(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(softmax_op)
    block.add_op(func.ReturnOp(softmax_op.results[0]))
    module = ModuleOp([func.FuncOp("softmax", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(NnLoweringError, match="nn.softmax must be decomposed before lower-nn"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-012
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.matmul 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_matmul_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, KernelMatmulOp)


# TC-PASS-NNL-013
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.img2col1d 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_img2col1d_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, KernelImg2col1dOp)


# TC-PASS-NNL-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.img2col2d 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_img2col2d_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, KernelImg2col2dOp)


# TC-PASS-NNL-015
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.broadcast 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_broadcast_dma
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, DmaBroadcastOp)


# TC-PASS-NNL-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.transpose 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_transpose_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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
    perm_attr = ArrayAttr([IntegerAttr.from_int_and_width(1, 64), IntegerAttr.from_int_and_width(0, 64)])
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, DmaTransposeOp)


# TC-PASS-NNL-017
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.cast 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_cast_to_dma_cast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_cast_to_dma_cast() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    cast_op = NnCastOp(operand, result_type, SPACE_GLOBAL)
    block.add_op(cast_op)
    block.add_op(func.ReturnOp(cast_op.results[0]))
    module = ModuleOp([func.FuncOp("cast", FunctionType.from_lists([operand_type], [result_type]), Region(block))])

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_dma_cast_after_first_alloc(block)


# TC-PASS-NNL-018
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 nn.select 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_select_to_kernel_select
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_op(block, KernelSelectOp)


# TC-PASS-NNL-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对含符号维度 broadcast 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_broadcast_with_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, DmaBroadcastOp)
    _assert_single_op(block, SymbolGetDimOp)


# TC-PASS-NNL-020
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 会把 mixed symbol scalar add 物化为 dma.fill 路径，并生成 kernel.binary_elewise(kind="add")。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_add_mixed_symbol_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    assert len([op for op in block.ops if isinstance(op, DmaAllocOp)]) == 2
    _assert_single_op(block, DmaFillOp)
    _assert_single_binary_kind(block, "add")
    assert not any(isinstance(op, DmaBroadcastOp) for op in block.ops)


# TC-PASS-NNL-020A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 10:20 +0800
# 最近一次运行成功时间: 2026-04-14 10:20 +0800
# 测试目的: 验证 Lowering 对 mixed symbol eq 的改写行为，生成 dma.alloc + dma.broadcast + kernel.binary_elewise(kind="eq")，且不混入 dma.fill。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_eq_mixed_symbol_uses_broadcast_only
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    assert len([op for op in block.ops if isinstance(op, DmaAllocOp)]) == 2
    _assert_single_op(block, DmaBroadcastOp)
    _assert_single_binary_kind(block, "eq")
    assert not any(isinstance(op, DmaFillOp) for op in block.ops)


# TC-PASS-NNL-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对带符号维度的 cast 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_cast_preserves_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_dma_cast_after_first_alloc(block)


# TC-PASS-NNL-022
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 select 的符号维度保留行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_select_preserves_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_op(block, KernelSelectOp)


# TC-PASS-NNL-023
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 implicit expand broadcast 的改写行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_broadcast_with_implicit_expand
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_op(block, DmaBroadcastOp)


def _build_broadcast_exp_reduce_min_func() -> func.FuncOp:
    """构造用于测试的 broadcast/exp/reduce_min 组合函数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 broadcast -> exp -> reduce_min 组合生成测试函数。

    使用示例:
    - func_op = _build_broadcast_exp_reduce_min_func()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: test/pass/nn_lowering/test_lowering_nn_lowering.py
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
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(0, 64),
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

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统计 block 内 DmaAllocOp 的数量并与预期对齐。

    使用示例:
    - _assert_alloc_count(block, 3)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: test/pass/nn_lowering/test_lowering_nn_lowering.py
    """

    alloc_ops = [op for op in block.ops if isinstance(op, DmaAllocOp)]
    assert len(alloc_ops) == expected


# TC-PASS-NNL-024
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 在组合场景下对 alloc 的处理。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_combined_ops_alloc
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_combined_ops_alloc() -> None:
    func_op = _build_broadcast_exp_reduce_min_func()
    module = ModuleOp([func_op])

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_alloc_count(block, 3)


# TC-PASS-NNL-025
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对非法 add 形状的拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_rejects_invalid_add_shape
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    with pytest.raises(NnLoweringError, match="nn op operands must have the same shape"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-026
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 unknown dim 的拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_broadcast_rejects_unknown_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    with pytest.raises(NnLoweringError, match="nn.broadcast operand shape must not contain '\\?'"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-027
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 symbol dim cast 的行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_cast_symbol_dim_rejects_mismatch
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    with pytest.raises(NnLoweringError, match="dma.cast shape mismatch"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-028
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 select 的 symbol dim 保留。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_select_preserves_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_op(block, KernelSelectOp)


# TC-PASS-NNL-029
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 transpose 动态维度的处理。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_transpose_dynamic
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_lower_transpose_dynamic() -> None:
    operand_type = nn_memory_type(
        (StringAttr("M"), StringAttr("N")),
        (IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    result_type = nn_memory_type(
        (StringAttr("N"), StringAttr("M")),
        (IntAttr(2), IntAttr(1)),
        f32,
        SPACE_GLOBAL,
    )
    region = Region()
    block = Block(arg_types=[operand_type])
    region.add_block(block)
    perm_attr = ArrayAttr([IntegerAttr.from_int_and_width(1, 64), IntegerAttr.from_int_and_width(0, 64)])
    transpose_op = NnTransposeOp(block.args[0], result_type, perm_attr, SPACE_GLOBAL)
    block.add_op(transpose_op)
    block.add_op(func.ReturnOp(transpose_op.results[0]))
    func_op = func.FuncOp("transpose_dynamic", FunctionType.from_lists([operand_type], [result_type]), region)
    module = ModuleOp([func_op])

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_op(block, DmaTransposeOp)


# TC-PASS-NNL-030
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 bfloat16 cast 的行为。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_bfloat16_cast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    NnLoweringPass().run(module)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    block = func_op.body.block
    _assert_single_alloc(block)
    _assert_single_dma_cast_after_first_alloc(block)


# TC-PASS-NNL-031
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对未知 op 的拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_rejects_unknown_op
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    with pytest.raises(NnLoweringError, match="unknown op"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-032
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 reduce_min 维度不一致的拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_reduce_min_rejects_invalid_rank
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(0, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    func_op = func.FuncOp("reduce_min_bad_rank", FunctionType.from_lists([operand_type], [res_type]), region)
    module = ModuleOp([func_op])

    with pytest.raises(NnLoweringError, match="reduce shape rank must match"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-033
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 reduce_min keepdim 类型的拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_reduce_min_rejects_bad_keepdim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_reduce_min_rejects_bad_keepdim() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(2, 64),
        SPACE_GLOBAL,
    )
    reduce_op.attributes["keepdim"] = StringAttr("bad")
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(NnLoweringError, match="keepdim must be integer"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-033A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-21 21:40:00 +0800
# 最近一次运行成功时间: 2026-04-21 21:40:00 +0800
# 测试目的: 验证 Lowering 对 reduce_min keepdim=-1 的拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_reduce_min_rejects_keepdim_negative_one
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_reduce_min_rejects_keepdim_negative_one() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(-1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(NnLoweringError, match="keepdim must be 0 or 1"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-034
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 broadcast 形状不匹配的拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_lower_broadcast_rejects_invalid_shape
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    with pytest.raises(NnLoweringError, match="invalid broadcast target shape"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-035
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 broadcast 标量使用的拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_broadcast_rejects_invalid_scalar
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/dma_structured_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    with pytest.raises(NnLoweringError, match="broadcast scalar must be int or symbol"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-036
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 matmul stride 的验证。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_matmul_requires_contiguous_stride
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
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

    with pytest.raises(NnLoweringError, match="matmul stride must be contiguous"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-037
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 reduce axes 校验。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_reduce_axes_validation
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_reduce_axes_validation() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([]),
        IntegerAttr.from_int_and_width(1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(NnLoweringError, match="reduce axes must be non-empty"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-038
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 Lowering 对 reduce keepdim 校验。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_reduce_keepdim_validation
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_reduce_keepdim_validation() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    reduce_op = NnReduceMinOp(
        operand,
        res_type,
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(2, 64),
        SPACE_GLOBAL,
    )
    block.add_op(reduce_op)
    block.add_op(func.ReturnOp(reduce_op.results[0]))
    module = ModuleOp([func.FuncOp("reduce_min", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(NnLoweringError, match="keepdim must be 0 or 1"):
        NnLoweringPass().run(module)


# TC-PASS-NNL-039
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 direct `nn.softmax` 即使 axis 非法，也会先按“需先分解”路径拒绝。
# 使用示例: pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k test_softmax_requires_decompass_before_axis_validation
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_lowering_nn_lowering.py
def test_softmax_requires_decompass_before_axis_validation() -> None:
    block = Block()
    operand_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    res_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), f32, SPACE_GLOBAL)
    operand = add_block_arg(block, operand_type)
    softmax_op = NnSoftmaxOp(
        operand,
        res_type,
        IntegerAttr.from_int_and_width(-1, 64),
        SPACE_GLOBAL,
    )
    block.add_op(softmax_op)
    block.add_op(func.ReturnOp(softmax_op.results[0]))
    module = ModuleOp([func.FuncOp("softmax", FunctionType.from_lists([operand_type], [res_type]), Region(block))])

    with pytest.raises(NnLoweringError, match="nn.softmax must be decomposed before lower-nn"):
        NnLoweringPass().run(module)
