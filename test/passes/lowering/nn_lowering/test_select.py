"""nn_lowering select tests.


功能说明:
- 验证 nn.select lower 为 dma.alloc + kernel.select。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_select.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/spec.md
- 测试文件: test/passes/lowering/nn_lowering/test_select.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i1, i32
from xdsl.ir import Attribute, Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelSelectOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType, NnSelectOp
from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from test.passes.lowering.nn_lowering.memory_type_utils import symbol_array


def _make_memory_type(element_type: Attribute = i32) -> NnMemoryType:
    """构造默认 memory type。


    功能说明:
    - 生成 rank=2 的 nn.memory 类型。

    使用示例:
    - mem_type = _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
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
    - module, block = _build_module([cond, lhs, rhs], result_type, lambda block: [nn_op])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_select.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
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


# TC-PASS-NNL-S2-012
# 测试目的: 验证 nn.select lower 为 dma.alloc + kernel.select。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_select.py -k test_lower_select_to_kernel_select
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_select.py
def test_lower_select_to_kernel_select() -> None:
    cond_type = _make_memory_type(element_type=i1)
    lhs_type = _make_memory_type()
    rhs_type = _make_memory_type()
    result_type = _make_memory_type()
    space = NnMemorySpaceAttr.from_name("global")

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
    NnLoweringPass().apply(Context(), module)

    ops = list(block.ops)
    assert any(isinstance(op, KernelSelectOp) for op in ops)
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)


# TC-PASS-NNL-S2-012A
# 测试目的: 验证 nn.select 非法 operand、result shape 与 cond verifier 错误保持公开 KernelCodeError 语义。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_select.py -k test_lower_select_public_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/select_cast_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_select.py
def test_lower_select_public_error_matrix() -> None:
    cond_type = _make_memory_type(element_type=i1)
    value_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=i32)
    space = NnMemorySpaceAttr.from_name("global")

    cond_error_block = Block(arg_types=[i32, value_type, value_type])
    cond_error_op = NnSelectOp(cond_error_block.args[0], cond_error_block.args[1], cond_error_block.args[2], result_type, space)
    cond_error_block.add_op(cond_error_op)
    cond_error_block.add_op(func.ReturnOp(cond_error_op.result))
    cond_error_module = ModuleOp(
        [
            func.FuncOp(
                "select_cond_error",
                FunctionType.from_lists([i32, value_type, value_type], [result_type]),
                Region(cond_error_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn.select cond must be nn.memory"):
        NnLoweringPass().apply(Context(), cond_error_module)

    lhs_error_block = Block(arg_types=[cond_type, i32, value_type])
    lhs_error_op = NnSelectOp(lhs_error_block.args[0], lhs_error_block.args[1], lhs_error_block.args[2], result_type, space)
    lhs_error_block.add_op(lhs_error_op)
    lhs_error_block.add_op(func.ReturnOp(lhs_error_op.result))
    lhs_error_module = ModuleOp(
        [
            func.FuncOp(
                "select_lhs_error",
                FunctionType.from_lists([cond_type, i32, value_type], [result_type]),
                Region(lhs_error_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn.select lhs must be nn.memory"):
        NnLoweringPass().apply(Context(), lhs_error_module)

    rhs_error_block = Block(arg_types=[cond_type, value_type, i32])
    rhs_error_op = NnSelectOp(rhs_error_block.args[0], rhs_error_block.args[1], rhs_error_block.args[2], result_type, space)
    rhs_error_block.add_op(rhs_error_op)
    rhs_error_block.add_op(func.ReturnOp(rhs_error_op.result))
    rhs_error_module = ModuleOp(
        [
            func.FuncOp(
                "select_rhs_error",
                FunctionType.from_lists([cond_type, value_type, i32], [result_type]),
                Region(rhs_error_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn.select rhs must be nn.memory"):
        NnLoweringPass().apply(Context(), rhs_error_module)

    rank_result_type = NnMemoryType(symbol_array([4]), symbol_array([1]), i32, space)
    rank_error_block = Block(arg_types=[cond_type, value_type, value_type])
    rank_error_op = NnSelectOp(rank_error_block.args[0], rank_error_block.args[1], rank_error_block.args[2], rank_result_type, space)
    rank_error_block.add_op(rank_error_op)
    rank_error_block.add_op(func.ReturnOp(rank_error_op.result))
    rank_error_module = ModuleOp(
        [
            func.FuncOp(
                "select_rank_error",
                FunctionType.from_lists([cond_type, value_type, value_type], [rank_result_type]),
                Region(rank_error_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn select/cast operand/result rank mismatch"):
        NnLoweringPass().apply(Context(), rank_error_module)

    unknown_result_type = NnMemoryType(symbol_array(["?", 8]), symbol_array([8, 1]), i32, space)
    unknown_error_block = Block(arg_types=[cond_type, value_type, value_type])
    unknown_error_op = NnSelectOp(
        unknown_error_block.args[0],
        unknown_error_block.args[1],
        unknown_error_block.args[2],
        unknown_result_type,
        space,
    )
    unknown_error_block.add_op(unknown_error_op)
    unknown_error_block.add_op(func.ReturnOp(unknown_error_op.result))
    unknown_error_module = ModuleOp(
        [
            func.FuncOp(
                "select_unknown_shape_error",
                FunctionType.from_lists([cond_type, value_type, value_type], [unknown_result_type]),
                Region(unknown_error_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn select/cast result shape must not contain"):
        NnLoweringPass().apply(Context(), unknown_error_module)

    cond_i32_type = _make_memory_type(element_type=i32)
    cond_verify_block = Block(arg_types=[cond_i32_type, value_type, value_type])
    cond_verify_op = NnSelectOp(
        cond_verify_block.args[0],
        cond_verify_block.args[1],
        cond_verify_block.args[2],
        result_type,
        space,
    )
    cond_verify_block.add_op(cond_verify_op)
    cond_verify_block.add_op(func.ReturnOp(cond_verify_op.result))
    cond_verify_module = ModuleOp(
        [
            func.FuncOp(
                "select_cond_verify_error",
                FunctionType.from_lists([cond_i32_type, value_type, value_type], [result_type]),
                Region(cond_verify_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError):
        NnLoweringPass().apply(Context(), cond_verify_module)
