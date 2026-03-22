"""nn -> kernel lowering pass tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 nn_to_kernel pass 的 lowering 行为与错误路径。

使用示例:
- pytest -q test/pass/test_lowing_nn_to_kernel.py

关联文件:
- 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
- Spec 文档: spec/pass/lowing/nn_to_kernel.md
- 测试文件: test/pass/test_lowing_nn_to_kernel.py
"""

from __future__ import annotations

import sys
import importlib
from pathlib import Path
from collections.abc import Callable

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32, i1, i32
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, result_def
from xdsl.ir import Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelAddOp, KernelCastOp, KernelEqOp, KernelSelectOp
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnEqOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnNeOp,
)
pass_module = importlib.import_module("kernel_gen.pass.lowing.nn_to_kernel")
LowerNnToKernelError = pass_module.LowerNnToKernelError
LowerNnToKernelPass = pass_module.LowerNnToKernelPass


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
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    name = "nn.select"

    cond = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
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
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    name = "nn.cast"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"space": space},
        )


def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造 nn.space。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 简化测试中的 space 构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _make_memory_type(
    shape: ArrayAttr | None = None,
    stride: ArrayAttr | None = None,
    element_type=i32,
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
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    if shape is None:
        shape = ArrayAttr([IntAttr(2), IntAttr(4)])
    if stride is None:
        stride = ArrayAttr([IntAttr(4), IntAttr(1)])
    return NnMemoryType(shape, stride, element_type, _make_space(space))


def _build_module(
    arg_types: list[NnMemoryType],
    result_type: NnMemoryType,
    op_builder: Callable[[Block], list[Operation]],
) -> tuple[ModuleOp, Block]:
    """构造包含单个 func 的 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按顺序插入 ops 并追加 func.return。

    使用示例:
    - module, block = _build_module([lhs_type, rhs_type], result_type, lambda block: [nn_op])

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
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
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    return list(block.ops)


# TC-PASS-N2K-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 23:20:39 +0800
# 最近一次运行成功时间: 2026-03-21 23:20:39 +0800
# 功能说明: 验证 nn.add lower 为 kernel.add。
# 使用示例: pytest -q test/pass/test_lowing_nn_to_kernel.py -k test_lower_add_to_kernel
# 对应功能实现文件路径: kernel_gen/pass/lowing/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowing/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowing_nn_to_kernel.py
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 23:20:39 +0800
# 最近一次运行成功时间: 2026-03-21 23:20:39 +0800
# 功能说明: 验证 nn.eq lower 为 kernel.eq。
# 使用示例: pytest -q test/pass/test_lowing_nn_to_kernel.py -k test_lower_eq_to_kernel
# 对应功能实现文件路径: kernel_gen/pass/lowing/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowing/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowing_nn_to_kernel.py
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


# TC-PASS-N2K-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 23:20:39 +0800
# 最近一次运行成功时间: 2026-03-21 23:20:39 +0800
# 功能说明: 验证 nn.select lower 为 kernel.select。
# 使用示例: pytest -q test/pass/test_lowing_nn_to_kernel.py -k test_lower_select_to_kernel
# 对应功能实现文件路径: kernel_gen/pass/lowing/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowing/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowing_nn_to_kernel.py
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
# 最近一次运行测试时间: 2026-03-21 23:20:39 +0800
# 最近一次运行成功时间: 2026-03-21 23:20:39 +0800
# 功能说明: 验证 nn.cast lower 为 kernel.cast。
# 使用示例: pytest -q test/pass/test_lowing_nn_to_kernel.py -k test_lower_cast_to_kernel
# 对应功能实现文件路径: kernel_gen/pass/lowing/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowing/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowing_nn_to_kernel.py
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


# TC-PASS-N2K-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 23:20:39 +0800
# 最近一次运行成功时间: 2026-03-21 23:20:39 +0800
# 功能说明: 验证输出分配使用 dma.alloc。
# 使用示例: pytest -q test/pass/test_lowing_nn_to_kernel.py -k test_lower_inserts_dma_alloc_for_output
# 对应功能实现文件路径: kernel_gen/pass/lowing/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowing/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowing_nn_to_kernel.py
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
# 最近一次运行测试时间: 2026-03-21 23:20:39 +0800
# 最近一次运行成功时间: 2026-03-21 23:20:39 +0800
# 功能说明: 验证输出 memory 类型/空间保持一致。
# 使用示例: pytest -q test/pass/test_lowing_nn_to_kernel.py -k test_lower_preserves_memory_type_and_space
# 对应功能实现文件路径: kernel_gen/pass/lowing/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowing/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowing_nn_to_kernel.py
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


# TC-PASS-N2K-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 23:20:39 +0800
# 最近一次运行成功时间: 2026-03-21 23:20:39 +0800
# 功能说明: 验证不支持的 nn op 抛错。
# 使用示例: pytest -q test/pass/test_lowing_nn_to_kernel.py -k test_lower_unsupported_nn_op_raises
# 对应功能实现文件路径: kernel_gen/pass/lowing/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowing/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowing_nn_to_kernel.py
def test_lower_unsupported_nn_op_raises() -> None:
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type(element_type=i1)
    space = _make_space("global")

    module, _ = _build_module(
        [lhs_type, rhs_type],
        result_type,
        lambda block: [NnNeOp(block.args[0], block.args[1], result_type, space)],
    )
    with pytest.raises(LowerNnToKernelError, match="Unsupported nn op"):
        LowerNnToKernelPass().run(module)


# TC-PASS-N2K-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 23:20:39 +0800
# 最近一次运行成功时间: 2026-03-21 23:20:39 +0800
# 功能说明: 验证 lowering 后不再残留 nn op。
# 使用示例: pytest -q test/pass/test_lowing_nn_to_kernel.py -k test_lower_removes_all_nn_ops
# 对应功能实现文件路径: kernel_gen/pass/lowing/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowing/nn_to_kernel.md
# 对应测试文件路径: test/pass/test_lowing_nn_to_kernel.py
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
