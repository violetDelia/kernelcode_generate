"""nn_lowering cast tests.


功能说明:
- 验证 nn.cast lower 为 dma.alloc + dma.cast。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_cast.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/spec.md
- 测试文件: test/passes/lowering/nn_lowering/test_cast.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    FunctionType,
    IntAttr,
    ModuleOp,
    StringAttr,
    f32,
    i1,
    i32,
)
from xdsl.ir import Attribute, Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaCastOp
from kernel_gen.dialect.nn import NnCastOp, NnMemorySpaceAttr, NnMemoryType
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
    - test: test/passes/lowering/nn_lowering/test_cast.py
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
    - module, block = _build_module([input_type], result_type, lambda block: [nn_op])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/passes/lowering/nn_lowering/test_cast.py
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


# TC-PASS-NNL-S2-013
# 测试目的: 验证 nn.cast lower 为 dma.alloc + dma.cast。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_cast.py -k test_lower_cast_to_dma_cast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_cast.py
def test_lower_cast_to_dma_cast() -> None:
    input_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=f32)
    space = NnMemorySpaceAttr.from_name("global")

    module, block = _build_module(
        [input_type],
        result_type,
        lambda block: [NnCastOp(block.args[0], result_type, space)],
    )
    NnLoweringPass().apply(Context(), module)

    ops = list(block.ops)
    assert any(isinstance(op, DmaCastOp) for op in ops)
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)


# TC-PASS-NNL-S3-001
# 测试目的: 验证 nn.cast 支持 bfloat16 并 lower 为 dma.cast。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_cast.py -k test_lower_cast_bfloat16_to_dma_cast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_cast.py
def test_lower_cast_bfloat16_to_dma_cast() -> None:
    input_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=BFloat16Type())
    space = NnMemorySpaceAttr.from_name("global")

    module, block = _build_module(
        [input_type],
        result_type,
        lambda block: [NnCastOp(block.args[0], result_type, space)],
    )
    NnLoweringPass().apply(Context(), module)

    ops = list(block.ops)
    assert any(isinstance(op, DmaCastOp) for op in ops)
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)


# TC-PASS-NNL-S2-013A
# 测试目的: 验证 nn.cast 非法 input、element type、shape/rank 与 dma.cast verifier 错误保持公开语义。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_cast.py -k test_lower_cast_public_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/select_cast_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_cast.py
def test_lower_cast_public_error_matrix() -> None:
    space = NnMemorySpaceAttr.from_name("global")
    input_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=f32)

    non_memory_block = Block(arg_types=[i32])
    non_memory_op = NnCastOp(non_memory_block.args[0], result_type, space)
    non_memory_block.add_op(non_memory_op)
    non_memory_block.add_op(func.ReturnOp(non_memory_op.result))
    non_memory_module = ModuleOp(
        [
            func.FuncOp(
                "cast_non_memory_input",
                FunctionType.from_lists([i32], [result_type]),
                Region(non_memory_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn.cast input must be nn.memory"):
        NnLoweringPass().apply(Context(), non_memory_module)

    i1_input_type = _make_memory_type(element_type=i1)
    i1_block = Block(arg_types=[i1_input_type])
    i1_op = NnCastOp(i1_block.args[0], result_type, space)
    i1_block.add_op(i1_op)
    i1_block.add_op(func.ReturnOp(i1_op.result))
    i1_module = ModuleOp(
        [
            func.FuncOp(
                "cast_i1_input",
                FunctionType.from_lists([i1_input_type], [result_type]),
                Region(i1_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn.cast element_type must be integer or float and not i1"):
        NnLoweringPass().apply(Context(), i1_module)

    rank_result_type = NnMemoryType(symbol_array([4]), symbol_array([1]), f32, space)
    rank_block = Block(arg_types=[input_type])
    rank_op = NnCastOp(rank_block.args[0], rank_result_type, space)
    rank_block.add_op(rank_op)
    rank_block.add_op(func.ReturnOp(rank_op.result))
    rank_module = ModuleOp(
        [
            func.FuncOp(
                "cast_rank_error",
                FunctionType.from_lists([input_type], [rank_result_type]),
                Region(rank_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn select/cast operand/result rank mismatch"):
        NnLoweringPass().apply(Context(), rank_module)

    unknown_result_type = NnMemoryType(symbol_array(["?", 8]), symbol_array([8, 1]), f32, space)
    unknown_block = Block(arg_types=[input_type])
    unknown_op = NnCastOp(unknown_block.args[0], unknown_result_type, space)
    unknown_block.add_op(unknown_op)
    unknown_block.add_op(func.ReturnOp(unknown_op.result))
    unknown_module = ModuleOp(
        [
            func.FuncOp(
                "cast_unknown_shape_error",
                FunctionType.from_lists([input_type], [unknown_result_type]),
                Region(unknown_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn select/cast result shape must not contain"):
        NnLoweringPass().apply(Context(), unknown_module)

    stride_result_type = NnMemoryType(symbol_array([4, 8]), symbol_array([1, 8]), f32, space)
    stride_block = Block(arg_types=[input_type])
    stride_op = NnCastOp(stride_block.args[0], stride_result_type, space)
    stride_block.add_op(stride_op)
    stride_block.add_op(func.ReturnOp(stride_op.result))
    stride_module = ModuleOp(
        [
            func.FuncOp(
                "cast_stride_error",
                FunctionType.from_lists([input_type], [stride_result_type]),
                Region(stride_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError):
        NnLoweringPass().apply(Context(), stride_module)
