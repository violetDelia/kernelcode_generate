"""nn -> kernel lowering pass tests.

创建者: 金铲铲大作战
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 nn_to_kernel pass 的 lowering 行为与错误路径。

使用示例:
- pytest -q test/pass/test_lowering_nn_to_kernel.py

当前覆盖率信息:
- `kernel_gen.passes.lowering.nn_to_kernel`：`100%`（2026-03-23 04:07:56 +0800，`15 passed`）。

覆盖率命令:
- `pytest --cov=kernel_gen.passes.lowering.nn_to_kernel --cov-report=term-missing -q test/pass/test_lowering_nn_to_kernel.py`

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
- Spec 文档: spec/pass/lowering/nn_to_kernel.md
- 测试文件: test/pass/test_lowering_nn_to_kernel.py
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
from xdsl.irdl import (
    IRDLOperation,
    attr_def,
    irdl_op_definition,
    operand_def,
    region_def,
    result_def,
)
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaFillOp, DmaTransposeOp
from kernel_gen.dialect.kernel import (
    KernelAddOp,
    KernelCastOp,
    KernelDivOp,
    KernelEqOp,
    KernelExpOp,
    KernelGeOp,
    KernelGtOp,
    KernelLeOp,
    KernelNeOp,
    KernelMatmulOp,
    KernelReduceMaxOp,
    KernelSelectOp,
)
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnEqOp,
    NnExpOp,
    NnGeOp,
    NnGtOp,
    NnLeOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnNeOp,
    NnReduceMaxOp,
    NnSoftmaxOp,
    NnTransposeOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.nn import reduce_max, softmax
from kernel_gen.passes.lowering.buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.target import registry as target_registry
pass_module = importlib.import_module("kernel_gen.passes.lowering.nn_to_kernel")
LowerNnToKernelError = pass_module.LowerNnToKernelError
LowerNnToKernelPass = pass_module.LowerNnToKernelPass
pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
PassManager = pass_manager_module.PassManager
build_default_lowering_pass_manager = pass_manager_module.build_default_lowering_pass_manager


@irdl_op_definition
class NnSelectOp(IRDLOperation):
    """测试用 nn.select op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造 nn.select，用于 pass 单元测试。

    使用示例:
    - NnSelectOp(cond, lhs, rhs, result_type, space)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "nn.select"

    cond = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self: "NnSelectOp",
        cond: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[cond, lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class NnCastOp(IRDLOperation):
    """测试用 nn.cast op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造 nn.cast，用于 pass 单元测试。

    使用示例:
    - NnCastOp(input_value, result_type, space)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "nn.cast"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self: "NnCastOp",
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class NnNoSpaceOp(IRDLOperation):
    """测试用缺少 space 的 nn.add op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造缺失 nn.space 的 nn.add，用于错误路径测试。

    使用示例:
    - NnNoSpaceOp(lhs, rhs, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "nn.add"

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)

    def __init__(
        self: "NnNoSpaceOp",
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
    ) -> None:
        super().__init__(operands=[lhs, rhs], result_types=[result_type], attributes={})


@irdl_op_definition
class NnBadResultTypeOp(IRDLOperation):
    """测试用返回类型非 nn.memory 的 nn.add op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造结果类型非 nn.memory 的 nn.add。

    使用示例:
    - NnBadResultTypeOp(lhs, rhs, space)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "nn.add"

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(i32)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self: "NnBadResultTypeOp",
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[lhs, rhs],
            result_types=[i32],
            attributes={"space": space},
        )


@irdl_op_definition
class NnUnsupportedOp(IRDLOperation):
    """测试用不支持的 nn op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造不在支持列表中的 nn op，用于错误路径测试。

    使用示例:
    - NnUnsupportedOp(lhs, rhs, result_type, space)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "nn.unsupported"

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self: "NnUnsupportedOp",
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class NnMultiResultOp(IRDLOperation):
    """测试用多结果的 nn.add op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造包含两个结果的 nn.add。

    使用示例:
    - NnMultiResultOp(lhs, rhs, result_type, space)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "nn.add"

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result0 = result_def(NnMemoryType)
    result1 = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self: "NnMultiResultOp",
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[lhs, rhs],
            result_types=[result_type, result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class NnBadOperandOp(IRDLOperation):
    """测试用缺少 rhs 的 nn.add op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造缺少 operand 的 nn.add。

    使用示例:
    - NnBadOperandOp(lhs, result_type, space)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "nn.add"

    lhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self: "NnBadOperandOp",
        lhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[lhs],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class RegionWrapperOp(IRDLOperation):
    """测试用包含 region 的封装 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造包含 region 的 wrapper op，用于覆盖递归 lowering。

    使用示例:
    - RegionWrapperOp(region)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "test.wrapper"

    body = region_def()

    def __init__(self: "RegionWrapperOp", region: Region) -> None:
        super().__init__(regions=[region])


def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造 nn.space。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 简化测试中的 space 构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _make_memory_type(
    shape: ArrayAttr | None = None,
    stride: ArrayAttr | None = None,
    element_type: Attribute = i32,
    space: str = "global",
) -> NnMemoryType:
    """构造 nn.memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 提供默认合法的 nn.memory type。

    使用示例:
    - _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if shape is None:
        shape = ArrayAttr([IntAttr(2), IntAttr(4)])
    if stride is None:
        stride = ArrayAttr([IntAttr(4), IntAttr(1)])
    return NnMemoryType(shape, stride, element_type, _make_space(space))


def _tensor_arg(shape: list[int | str], dtype: NumericType = NumericType.Int32) -> Memory:
    return Memory(shape, dtype)


def _build_module(
    arg_types: list[Attribute],
    result_type: NnMemoryType,
    op_builder: Callable[[Block], list[Operation]],
) -> tuple[ModuleOp, Block]:
    """构造包含单个 func 的 module。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 按顺序插入 ops 并追加 func.return。

    使用示例:
    - module, block = _build_module([lhs_type, rhs_type], result_type, lambda block: [nn_op])

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
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


def _collect_ops(block: Block) -> list[Operation]:
    """收集 block 内的 op 列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 便于测试中查找 op 类型。

    使用示例:
    - ops = _collect_ops(block)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    return list(block.ops)


# TC-PASS-N2K-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 nn.add lower 为 kernel.add。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_add_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_add_to_kernel() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    assert any(isinstance(op, KernelAddOp) for op in ops)


# TC-PASS-N2K-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 17:41:56 +0800
# 最近一次运行成功时间: 2026-04-07 17:41:56 +0800
# 测试目的: 验证 nn.broadcast lower 为 dma.broadcast。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_broadcast_to_dma_broadcast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_broadcast_to_dma_broadcast() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    space = _make_space("global")

    module, block = _build_module(
        [source_type],
        result_type,
        lambda block: [NnBroadcastOp(block.args[0], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    assert any(isinstance(op, DmaBroadcastOp) for op in ops)


# TC-PASS-N2K-024
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 19:01:20 +0800
# 最近一次运行成功时间: 2026-04-07 19:01:20 +0800
# 测试目的: 验证 nn.transpose lower 为 dma.transpose。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_transpose_to_dma_transpose
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_transpose_to_dma_transpose() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(2)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
    )
    space = _make_space("global")

    module, block = _build_module(
        [source_type],
        result_type,
        lambda block: [NnTransposeOp(block.args[0], result_type, perm=[1, 0], space=space)],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    assert any(isinstance(op, DmaTransposeOp) for op in ops)
# COV-N2K-026
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 19:26:12 +0800
# 最近一次运行成功时间: 2026-04-02 19:26:12 +0800
# 测试目的: 验证 nn.add(memory, const(i32)) 会通过 dma.alloc + dma.fill + kernel.add 完成真实 rhs 物化。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_add_mixed_const_materializes_rhs_via_dma_fill
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_add_mixed_const_materializes_rhs_via_dma_fill() -> None:
    lhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    def _build_ops(block: Block) -> list[Operation]:
        const_op = arith.ConstantOp(IntegerAttr(1, i32))
        add_op = NnAddOp(block.args[0], const_op.result, result_type, space)
        return [const_op, add_op]

    module, block = _build_module([lhs_type], result_type, _build_ops)
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    alloc_ops = [op for op in ops if isinstance(op, DmaAllocOp)]
    fill_ops = [op for op in ops if isinstance(op, DmaFillOp)]
    kernel_ops = [op for op in ops if isinstance(op, KernelAddOp)]
    const_ops = [op for op in ops if isinstance(op, arith.ConstantOp)]

    assert len(alloc_ops) == 2
    assert len(fill_ops) == 1
    assert len(kernel_ops) == 1
    assert len(const_ops) == 1

    fill_op = fill_ops[0]
    kernel_op = kernel_ops[0]
    const_op = const_ops[0]

    assert fill_op.value == const_op.result
    assert any(use.operation is fill_op for use in const_op.result.uses)
    assert isinstance(fill_op.target.owner, DmaAllocOp)
    assert fill_op.target.owner is not kernel_op.out.owner
    assert kernel_op.rhs == fill_op.target
    assert any(use.operation is kernel_op for use in fill_op.target.uses)
    assert not any(op.name.startswith("nn.") for op in ops)


# COV-N2K-027
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 19:26:12 +0800
# 最近一次运行成功时间: 2026-04-02 19:26:12 +0800
# 测试目的: 验证 nn.add(memory, !symbol.int) 会通过 dma.alloc + dma.fill + kernel.add 完成真实 rhs 物化。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_add_mixed_symbol_materializes_rhs_via_dma_fill
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_add_mixed_symbol_materializes_rhs_via_dma_fill() -> None:
    lhs_type = _make_memory_type()
    result_type = _make_memory_type()
    rhs_type = SymbolValueType.from_expr("BIAS")
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    alloc_ops = [op for op in ops if isinstance(op, DmaAllocOp)]
    fill_ops = [op for op in ops if isinstance(op, DmaFillOp)]
    kernel_ops = [op for op in ops if isinstance(op, KernelAddOp)]

    assert len(alloc_ops) == 2
    assert len(fill_ops) == 1
    assert len(kernel_ops) == 1

    fill_op = fill_ops[0]
    kernel_op = kernel_ops[0]

    assert fill_op.value == block.args[1]
    assert any(use.operation is fill_op for use in block.args[1].uses)
    assert isinstance(fill_op.target.owner, DmaAllocOp)
    assert fill_op.target.owner is not kernel_op.out.owner
    assert kernel_op.rhs == fill_op.target
    assert any(use.operation is kernel_op for use in fill_op.target.uses)
    assert not any(op.name.startswith("nn.") for op in ops)


# COV-N2K-028
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 测试目的: 验证公开链路 `build_func_op -> LowerNnToKernelPass` 可统一覆盖 add 的三条成功路径。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_build_func_op_nn_add_variants_through_public_chain
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_build_func_op_nn_add_variants_through_public_chain() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + rhs

    def add_const_direct(lhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + 1

    def add_symbol_direct(lhs: "Tensor[i32, 2, 2]", bias: int) -> "Tensor[i32, 2, 2]":
        return lhs + bias

    pair_module = ModuleOp([build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))])
    LowerNnToKernelPass().run(pair_module)
    pair_block = next(op for op in pair_module.ops if isinstance(op, func.FuncOp)).body.block
    pair_ops = _collect_ops(pair_block)
    assert not any(op.name.startswith("nn.") for op in pair_ops)
    assert len([op for op in pair_ops if isinstance(op, DmaAllocOp)]) == 1
    assert len([op for op in pair_ops if isinstance(op, KernelAddOp)]) == 1

    const_module = ModuleOp([build_func_op(add_const_direct, _tensor_arg([2, 2]))])
    LowerNnToKernelPass().run(const_module)
    const_block = next(op for op in const_module.ops if isinstance(op, func.FuncOp)).body.block
    const_ops = _collect_ops(const_block)
    const_fill = next(op for op in const_ops if isinstance(op, DmaFillOp))
    const_add = next(op for op in const_ops if isinstance(op, KernelAddOp))
    const_literal = next(op for op in const_ops if isinstance(op, arith.ConstantOp))
    assert const_fill.value == const_literal.result
    assert const_add.rhs == const_fill.target
    assert not any(op.name.startswith("nn.") for op in const_ops)

    symbol_module = ModuleOp([build_func_op(add_symbol_direct, _tensor_arg([2, 2]), SymbolDim("bias"))])
    LowerNnToKernelPass().run(symbol_module)
    symbol_block = next(op for op in symbol_module.ops if isinstance(op, func.FuncOp)).body.block
    symbol_ops = _collect_ops(symbol_block)
    symbol_fill = next(op for op in symbol_ops if isinstance(op, DmaFillOp))
    symbol_add = next(op for op in symbol_ops if isinstance(op, KernelAddOp))
    assert symbol_fill.value == symbol_block.args[1]
    assert symbol_add.rhs == symbol_fill.target
    assert not any(op.name.startswith("nn.") for op in symbol_ops)


# TC-PASS-N2K-029
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证推荐调用链 `LowerNnToKernelPass -> BufferResultsToOutParamsPass` 可把 raw nn memory-return 函数稳定改写成前置 out 参数。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_pass_manager_buffer_results_to_out_params_rewrites_lowered_memory_return
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_pass_manager_buffer_results_to_out_params_rewrites_lowered_memory_return() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + rhs

    module = ModuleOp([build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))])
    target_name = "test_sm_lm"
    previous_target = target_registry._get_current_target()
    try:
        target_registry.register_target(
            target_registry.TargetSpec(
                target_name,
                None,
                set(),
                {"sm_memory_size": 1, "lm_memory_size": 1},
            )
        )
    except ValueError as exc:
        if "target already registered" not in str(exc):
            raise

    try:
        target_registry._set_current_target(target_name)
        pm = build_default_lowering_pass_manager()
        pm.run(module)
    finally:
        target_registry._set_current_target(previous_target)

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    body_ops = list(func_op.body.block.ops)
    kernel_add = next(op for op in body_ops if isinstance(op, KernelAddOp))
    return_op = next(op for op in body_ops if isinstance(op, func.ReturnOp))

    assert len(list(func_op.function_type.inputs)) == 3
    assert list(func_op.function_type.outputs) == []
    assert func_op.arg_attrs.data[0].data["name"] == StringAttr("arg0")
    assert len(return_op.arguments) == 0


# TC-PASS-N2K-030
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 raw nn memory-return 函数不能跳过 `LowerNnToKernelPass` 直接进入 out-param pass 链路。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_buffer_results_to_out_params_rejects_pre_lowered_nn_function
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_buffer_results_to_out_params_rejects_pre_lowered_nn_function() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + rhs

    module = ModuleOp([build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))])

    pm = PassManager(name="lowering")
    pm.add_pass(BufferResultsToOutParamsPass())

    with pytest.raises(ValueError, match="lowered IR"):
        pm.run(module)


# TC-PASS-N2K-031
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证半改半留 IR 会被 `BufferResultsToOutParamsPass` 显式拒绝，不能假装 rewrite 完成。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_buffer_results_to_out_params_rejects_half_rewritten_ir
# 对应功能实现文件路径: kernel_gen/passes/lowering/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/pass/lowering/buffer_results_to_out_params.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_buffer_results_to_out_params_rejects_half_rewritten_ir() -> None:
    mem_type = _make_memory_type()

    callee_block = Block(arg_types=[mem_type])
    callee_block.add_op(func.ReturnOp(callee_block.args[0]))
    callee = func.FuncOp(
        "callee",
        FunctionType.from_lists([mem_type], [mem_type]),
        Region(callee_block),
    )

    caller_block = Block(arg_types=[mem_type])
    out_alloc = DmaAllocOp([], mem_type)
    half_rewritten_call = func.CallOp("callee", [out_alloc.result, caller_block.args[0]], [])
    caller_block.add_ops([out_alloc, half_rewritten_call, func.ReturnOp()])
    caller = func.FuncOp(
        "caller",
        FunctionType.from_lists([mem_type], []),
        Region(caller_block),
    )

    module = ModuleOp([callee, caller])

    with pytest.raises(BufferResultsToOutParamsError, match="half-rewritten"):
        BufferResultsToOutParamsPass().run(module)


# TC-PASS-N2K-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 nn.eq lower 为 kernel.eq。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_eq_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_eq_to_kernel() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type(element_type=i1)
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnEqOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)
    ops = _collect_ops(block)
    assert any(isinstance(op, KernelEqOp) for op in ops)


# TC-PASS-N2K-020
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 02:48:07 +0800
# 最近一次运行成功时间: 2026-03-28 02:48:07 +0800
# 测试目的: 验证 nn.ne lower 为 kernel.ne。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_ne_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_ne_to_kernel() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type(element_type=i1)
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnNeOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)
    ops = _collect_ops(block)
    assert any(isinstance(op, KernelNeOp) for op in ops)


# TC-PASS-N2K-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 02:48:07 +0800
# 最近一次运行成功时间: 2026-03-28 02:48:07 +0800
# 测试目的: 验证 nn.le lower 为 kernel.le。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_le_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_le_to_kernel() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type(element_type=i1)
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnLeOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)
    ops = _collect_ops(block)
    assert any(isinstance(op, KernelLeOp) for op in ops)


# TC-PASS-N2K-022
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 02:48:07 +0800
# 最近一次运行成功时间: 2026-03-28 02:48:07 +0800
# 测试目的: 验证 nn.ge lower 为 kernel.ge。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_ge_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_ge_to_kernel() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type(element_type=i1)
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnGeOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)
    ops = _collect_ops(block)
    assert any(isinstance(op, KernelGeOp) for op in ops)


# TC-PASS-N2K-025
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 02:57:02 +0800
# 最近一次运行成功时间: 2026-04-08 02:57:02 +0800
# 测试目的: 验证 nn.gt lower 为 kernel.gt。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_gt_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_gt_to_kernel() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type(element_type=i1)
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnGtOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)
    ops = _collect_ops(block)
    assert any(isinstance(op, KernelGtOp) for op in ops)


# TC-PASS-N2K-026
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 13:13:24 +0800
# 最近一次运行成功时间: 2026-04-08 13:13:24 +0800
# 测试目的: 验证 nn.matmul lower 为 kernel.matmul。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_matmul_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_matmul_to_kernel() -> None:
    lhs_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(3)]))
    rhs_type = _make_memory_type(shape=ArrayAttr([IntAttr(3), IntAttr(4)]))
    result_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnMatmulOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)
    ops = _collect_ops(block)
    assert any(isinstance(op, KernelMatmulOp) for op in ops)


# TC-PASS-N2K-023
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 02:48:07 +0800
# 最近一次运行成功时间: 2026-03-28 02:48:07 +0800
# 测试目的: 验证 nn.truediv lower 为 kernel.div。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_truediv_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_truediv_to_kernel() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnTrueDivOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)
    ops = _collect_ops(block)
    assert any(isinstance(op, KernelDivOp) for op in ops)


# TC-PASS-N2K-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 nn.select lower 为 kernel.select。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_select_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_select_to_kernel() -> None:
    cond_type = _make_memory_type(element_type=i1)
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, block = _build_module(
        [cond_type, lhs_type, rhs_type],
        result_type,
        lambda block: [
            NnSelectOp(
                block.args[0],
                block.args[1],
                block.args[2],
                result_type,
                space,
            )
        ],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    assert any(isinstance(op, KernelSelectOp) for op in ops)


# TC-PASS-N2K-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 nn.cast lower 为 kernel.cast。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_cast_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_cast_to_kernel() -> None:
    input_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=f32)
    space = _make_space("global")

    module, block = _build_module(
        [input_type],
        result_type,
        lambda block: [NnCastOp(block.args[0], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    assert any(isinstance(op, KernelCastOp) for op in ops)


# TC-PASS-N2K-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 10:20:49 +0800
# 最近一次运行成功时间: 2026-04-08 10:20:49 +0800
# 测试目的: 验证 nn.exp lower 为 kernel.exp。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_exp_to_kernel
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_exp_to_kernel() -> None:
    input_type = _make_memory_type(element_type=f32)
    result_type = _make_memory_type(element_type=f32)
    space = _make_space("global")

    module, block = _build_module(
        [input_type],
        result_type,
        lambda block: [NnExpOp(block.args[0], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    assert any(isinstance(op, KernelExpOp) for op in ops)


# TC-PASS-N2K-007-BF16
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 10:51:30 +0800
# 最近一次运行成功时间: 2026-04-08 10:51:30 +0800
# 测试目的: 验证 nn.exp(bf16) lower 为 kernel.exp。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_exp_to_kernel_bf16
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_exp_to_kernel_bf16() -> None:
    input_type = _make_memory_type(element_type=BFloat16Type())
    result_type = _make_memory_type(element_type=BFloat16Type())
    space = _make_space("global")

    module, block = _build_module(
        [input_type],
        result_type,
        lambda block: [NnExpOp(block.args[0], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    assert any(isinstance(op, KernelExpOp) for op in ops)


# TC-PASS-N2K-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证输出分配使用 dma.alloc。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_inserts_dma_alloc_for_output
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_inserts_dma_alloc_for_output() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    ops = _collect_ops(block)
    assert any(isinstance(op, DmaAllocOp) for op in ops)


# TC-PASS-N2K-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证输出 memory 类型/空间保持一致。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_preserves_memory_type_and_space
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_preserves_memory_type_and_space() -> None:
    lhs_type = _make_memory_type(space="global")
    rhs_type = _make_memory_type(space="global")
    result_type = _make_memory_type(space="global")
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    alloc_ops = [op for op in _collect_ops(block) if isinstance(op, DmaAllocOp)]
    assert len(alloc_ops) == 1
    assert alloc_ops[0].result.type == result_type


# COV-N2K-008
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 04:17:04 +0800
# 最近一次运行成功时间: 2026-03-28 04:17:04 +0800
# 测试目的: 验证 dma.alloc 保留静态 shape 维度值，并确保 dynamic_shape 与 stride 约束一致。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_preserves_static_shape_in_alloc
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_preserves_static_shape_in_alloc() -> None:
    shape = ArrayAttr([IntAttr(3), IntAttr(5)])
    stride = ArrayAttr([IntAttr(5), IntAttr(1)])
    lhs_type = _make_memory_type(shape=shape, stride=stride)
    rhs_type = _make_memory_type(shape=shape, stride=stride)
    result_type = _make_memory_type(shape=shape, stride=stride)
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    alloc_ops = [op for op in _collect_ops(block) if isinstance(op, DmaAllocOp)]
    assert len(alloc_ops) == 1
    alloc_shape = alloc_ops[0].result.type.shape.data
    alloc_dynamic_shape = alloc_ops[0].dynamic_shape
    assert len(alloc_shape) == 2
    assert len(alloc_dynamic_shape) == 2
    assert isinstance(alloc_shape[0], IntAttr)
    assert isinstance(alloc_shape[1], IntAttr)
    assert alloc_shape[0].data == 3
    assert alloc_shape[1].data == 5
    assert isinstance(alloc_dynamic_shape[0].type, SymbolValueType)
    assert isinstance(alloc_dynamic_shape[1].type, SymbolValueType)
    assert alloc_dynamic_shape[0].type.get_value() == 3
    assert alloc_dynamic_shape[1].type.get_value() == 5

    non_contig_stride = ArrayAttr([IntAttr(6), IntAttr(1)])
    bad_type = _make_memory_type(shape=shape, stride=non_contig_stride)
    module, _ = _build_module(
        [bad_type, bad_type],
        bad_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], bad_type, space)],
    )
    with pytest.raises(LowerNnToKernelError, match="dma.alloc requires contiguous result stride"):
        LowerNnToKernelPass().run(module)


# COV-N2K-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 04:17:04 +0800
# 最近一次运行成功时间: 2026-03-28 04:17:04 +0800
# 测试目的: 验证 dma.alloc 保留符号 shape 维度值，并生成对应 dynamic_shape。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_preserves_symbol_shape_in_alloc
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_preserves_symbol_shape_in_alloc() -> None:
    shape = ArrayAttr([StringAttr("M"), StringAttr("N")])
    stride = ArrayAttr([StringAttr("N"), IntAttr(1)])
    lhs_type = _make_memory_type(shape=shape, stride=stride)
    rhs_type = _make_memory_type(shape=shape, stride=stride)
    result_type = _make_memory_type(shape=shape, stride=stride)
    space = _make_space("global")

    module, block = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )
    LowerNnToKernelPass().run(module)

    alloc_ops = [op for op in _collect_ops(block) if isinstance(op, DmaAllocOp)]
    assert len(alloc_ops) == 1
    alloc_shape = alloc_ops[0].result.type.shape.data
    alloc_dynamic_shape = alloc_ops[0].dynamic_shape
    assert len(alloc_shape) == 2
    assert len(alloc_dynamic_shape) == 2
    assert isinstance(alloc_shape[0], StringAttr)
    assert isinstance(alloc_shape[1], StringAttr)
    assert alloc_shape[0].data == "M"
    assert alloc_shape[1].data == "N"
    assert isinstance(alloc_dynamic_shape[0].type, SymbolValueType)
    assert isinstance(alloc_dynamic_shape[1].type, SymbolValueType)
    assert alloc_dynamic_shape[0].type.get_value() == "M"
    assert alloc_dynamic_shape[1].type.get_value() == "N"


# TC-PASS-N2K-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证不支持的 nn op 抛错。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_unsupported_nn_op_raises
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_unsupported_nn_op_raises() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type(element_type=i1)
    space = _make_space("global")

    module, _ = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnUnsupportedOp(block.args[0], block.args[1], result_type, space)],
    )
    with pytest.raises(LowerNnToKernelError, match="Unsupported nn op"):
        LowerNnToKernelPass().run(module)


# TC-PASS-N2K-030
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-08 00:00:00 +0800
# 测试目的: 验证 nn.softmax 被 lower 为 kernel.softmax 并保留 axis。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_softmax_direct_dialect_op_to_kernel_softmax
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_softmax_direct_dialect_op_to_kernel_softmax() -> None:
    input_type = _make_memory_type(element_type=f32)
    result_type = _make_memory_type(element_type=f32)
    space = _make_space("global")

    module, _ = _build_module(
        [input_type],
        result_type,
        lambda block: [NnSoftmaxOp(block.args[0], result_type, axis=1, space=space)],
    )

    LowerNnToKernelPass().run(module)
    after_ir = str(module)
    assert "kernel.softmax" in after_ir
    assert "axis = 1" in after_ir
    assert "nn.softmax" not in after_ir
    assert "Unsupported call expression" not in after_ir


# TC-PASS-N2K-031
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-08 00:00:00 +0800
# 测试目的: 验证公开链路 softmax helper lower 为 kernel.softmax 并保留 axis。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_softmax_public_chain_to_kernel_softmax
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_softmax_public_chain_to_kernel_softmax() -> None:
    def softmax_direct(value: "Tensor[f32, 2, 3]") -> "Tensor[f32, 2, 3]":
        return softmax(value, axis=1)

    module = ModuleOp([build_func_op(softmax_direct, _tensor_arg([2, 3], NumericType.Float32))])
    raw_ir = str(module)

    assert "nn.softmax" in raw_ir
    assert "-> !nn.memory<[2, 3], [3, 1], f32, #nn.space<global>>" in raw_ir

    LowerNnToKernelPass().run(module)
    after_ir = str(module)
    assert "kernel.softmax" in after_ir
    assert "axis = 1" in after_ir
    assert "nn.softmax" not in after_ir
    assert "Unsupported call expression" not in after_ir


# TC-PASS-N2K-032
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-09 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-09 00:00:00 +0800
# 测试目的: 验证 nn.reduce_max 被 lower 为 kernel.reduce_max 并保留 axis/keepdim。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_reduce_max_direct_dialect_op_to_kernel_reduce_max
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_reduce_max_direct_dialect_op_to_kernel_reduce_max() -> None:
    input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(3), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(12), IntAttr(4), IntAttr(1)]),
        element_type=f32,
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(1), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(4), IntAttr(1)]),
        element_type=f32,
    )
    space = _make_space("global")

    module, block = _build_module(
        [input_type],
        result_type,
        lambda current_block: [
            NnReduceMaxOp(current_block.args[0], result_type, axes=[1], keepdim=True, space=space)
        ],
    )

    LowerNnToKernelPass().run(module)
    after_ir = str(module)
    assert "kernel.reduce_max" in after_ir
    assert "axis = 1" in after_ir
    assert "keepdim = true" in after_ir
    assert "nn.reduce_max" not in after_ir

    reduced_ops = [op for op in _collect_ops(block) if isinstance(op, KernelReduceMaxOp)]
    assert len(reduced_ops) == 1


# COV-N2K-028
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-09 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-09 00:00:00 +0800
# 测试目的: 验证公开链路 reduce_max helper lower 为 kernel.reduce_max，并保留符号维 dynamic_shape。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_reduce_max_public_chain_to_kernel_reduce_max
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_reduce_max_public_chain_to_kernel_reduce_max() -> None:
    def reduce_max_symbol_kernel(value: "Tensor[f32, B, W]") -> "Tensor[f32, W]":
        return reduce_max(value, axis=0, keepdim=False)

    module = ModuleOp(
        [build_func_op(reduce_max_symbol_kernel, _tensor_arg(["B", "W"], NumericType.Float32))]
    )
    raw_ir = str(module)

    assert "nn.reduce_max" in raw_ir
    assert "axes = [0 : i64]" in raw_ir
    assert "keepdim = false" in raw_ir

    LowerNnToKernelPass().run(module)
    after_ir = str(module)
    assert "kernel.reduce_max" in after_ir
    assert "axis = 0" in after_ir
    assert "keepdim = false" in after_ir
    assert "nn.reduce_max" not in after_ir

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    alloc_op = next(op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp))
    assert len(alloc_op.dynamic_shape) == 1
    assert isinstance(alloc_op.dynamic_shape[0].type, SymbolValueType)
    assert alloc_op.dynamic_shape[0].type.get_value() == "W"


# TC-PASS-N2K-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 lowering 后不再残留 nn op。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_removes_all_nn_ops
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_removes_all_nn_ops() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    block = Block(arg_types=[lhs_type, rhs_type])
    add_op = NnAddOp(block.args[0], block.args[1], result_type, space)
    block.add_op(add_op)
    eq_result_type = _make_memory_type(element_type=i1)
    eq_op = NnEqOp(add_op.results[0], add_op.results[0], eq_result_type, space)
    block.add_op(eq_op)
    block.add_op(func.ReturnOp(eq_op.results[0]))
    func_type = FunctionType.from_lists([lhs_type, rhs_type], [eq_result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])

    LowerNnToKernelPass().run(module)

    for op in _collect_ops(block):
        assert not op.name.startswith("nn.")


# COV-N2K-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证缺失 nn.space attribute 会触发错误。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_missing_space_attribute_raises
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_missing_space_attribute_raises() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()

    module, _ = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnNoSpaceOp(block.args[0], block.args[1], result_type)],
    )
    with pytest.raises(LowerNnToKernelError, match="nn op must provide nn.space attribute"):
        LowerNnToKernelPass().run(module)


# COV-N2K-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 nn op 多结果时抛错。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_rejects_multi_result_op
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_rejects_multi_result_op() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, _ = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnMultiResultOp(block.args[0], block.args[1], result_type, space)],
    )
    with pytest.raises(LowerNnToKernelError, match="exactly one result"):
        LowerNnToKernelPass().run(module)


# COV-N2K-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 nn op 结果类型非 nn.memory 时抛错。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_rejects_non_memory_result_type
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_rejects_non_memory_result_type() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, _ = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnBadResultTypeOp(block.args[0], block.args[1], space)],
    )
    with pytest.raises(LowerNnToKernelError, match="nn op result must be nn.memory"):
        LowerNnToKernelPass().run(module)


# COV-N2K-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 nn op operand 数量不匹配时抛错。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_rejects_operand_count_mismatch
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_rejects_operand_count_mismatch() -> None:
    lhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, _ = _build_module(
        [lhs_type],
        result_type,
        lambda block: [NnBadOperandOp(block.args[0], result_type, space)],
    )
    with pytest.raises(LowerNnToKernelError, match="expects 2 operands, got 1"):
        LowerNnToKernelPass().run(module)


# COV-N2K-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 kernel op 校验失败时抛 LowerNnToKernelError。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_wraps_kernel_verify_exception
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_wraps_kernel_verify_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, _ = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )

    def _raise_verify(self: KernelAddOp) -> None:
        raise VerifyException("kernel verify failed")

    monkeypatch.setattr(KernelAddOp, "verify", _raise_verify)
    with pytest.raises(LowerNnToKernelError, match="kernel verify failed"):
        LowerNnToKernelPass().run(module)


# COV-N2K-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证包含 region 的 op 会触发递归 lowering。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_lower_recurses_into_regions
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_lower_recurses_into_regions() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    inner_block = Block(arg_types=[lhs_type, rhs_type])
    inner_block.add_op(NnAddOp(inner_block.args[0], inner_block.args[1], result_type, space))
    inner_region = Region(inner_block)
    wrapper = RegionWrapperOp(inner_region)

    outer_block = Block()
    outer_block.add_op(wrapper)

    pass_module._lower_block(outer_block)
    nested_ops = list(inner_block.ops)
    assert any(isinstance(op, KernelAddOp) for op in nested_ops)
    assert any(isinstance(op, DmaAllocOp) for op in nested_ops)
    assert not any(op.name.startswith("nn.") for op in nested_ops)


# COV-N2K-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 04:07:56 +0800
# 最近一次运行成功时间: 2026-03-23 04:07:56 +0800
# 测试目的: 验证 module 内残留 nn op 时直接抛错。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_ensure_no_nn_ops_raises
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_ensure_no_nn_ops_raises() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")

    module, _ = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnAddOp(block.args[0], block.args[1], result_type, space)],
    )
    with pytest.raises(LowerNnToKernelError, match="nn op remains after lowering"):
        pass_module._ensure_no_nn_ops(module)


# COV-N2K-024
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 19:54:50 +0800
# 最近一次运行成功时间: 2026-03-28 19:54:50 +0800
# 测试目的: 验证 module 非 builtin.module 时归因 AST 发射失败。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_run_rejects_non_module_input
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_run_rejects_non_module_input() -> None:
    with pytest.raises(LowerNnToKernelError, match="module must be builtin.module"):
        LowerNnToKernelPass().run(123)  # type: ignore[arg-type]


# COV-N2K-025
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 19:54:50 +0800
# 最近一次运行成功时间: 2026-03-28 19:54:50 +0800
# 测试目的: 验证 module ops 不可遍历时归因 AST 发射失败。
# 使用示例: pytest -q test/pass/test_lowering_nn_to_kernel.py -k test_run_rejects_non_iterable_module_ops
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowering_nn_to_kernel.py
def test_run_rejects_non_iterable_module_ops(monkeypatch: pytest.MonkeyPatch) -> None:
    module = ModuleOp([])
    monkeypatch.setattr(ModuleOp, "ops", None, raising=False)
    with pytest.raises(LowerNnToKernelError, match="module ops must be iterable"):
        LowerNnToKernelPass().run(module)
