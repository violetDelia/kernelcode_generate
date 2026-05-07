"""nn_lowering matmul tests.


功能说明:
- 验证 nn.matmul -> kernel.matmul 的 lowering 目标与结果类型约束。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_matmul.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
- 测试文件: test/passes/lowering/nn_lowering/test_matmul.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32, i32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMatmulOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolGetDimOp
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.operation.dma import alloc, deslice, slice
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.scf import loop
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType
from test.passes.lowering.nn_lowering.memory_type_utils import memory_type


# TC-PASS-NNL-020
# 测试目的: 验证 nn.matmul lowering 目标为 kernel.matmul 且结果类型一致。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_matmul.py -k test_nn_lowering_matmul_target
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_matmul.py
def test_nn_lowering_matmul_target() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    lhs_type = memory_type([2, 3], [3, 1], f32, space)
    rhs_type = memory_type([3, 4], [4, 1], f32, space)
    result_type = memory_type([2, 4], [4, 1], f32, space)

    block = Block(arg_types=[lhs_type, rhs_type])
    matmul = NnMatmulOp(block.args[0], block.args[1], result_type, space)
    block.add_op(matmul)
    block.add_op(func.ReturnOp(matmul.result))
    func_type = FunctionType.from_lists([lhs_type, rhs_type], [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])

    NnLoweringPass().apply(Context(), module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelMatmulOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnMatmulOp) for op in module.walk())
    kernel_op = kernel_ops[0]
    assert isinstance(kernel_op.out.type, NnMemoryType)
    assert kernel_op.out.type.shape == result_type.shape
    assert kernel_op.out.type.stride == result_type.stride


# TC-PASS-NNL-021
# 测试目的: 验证 mlir_gen 生成的 symbol.for region 内 nn.matmul 也会 lower 为 kernel.matmul。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_matmul.py -k test_nn_lowering_matmul_inside_symbol_for
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_matmul.py
def test_nn_lowering_matmul_inside_symbol_for() -> None:
    def tiled_matmul(lhs: "Tensor[f32, 32, 16]", rhs: "Tensor[f32, 16, 32]") -> "Tensor[f32, 32, 32]":
        out = alloc([32, 32], NumericType.Float32, MemorySpace.GM)
        for m0 in loop(0, 32, 16):
            for n0 in loop(0, 32, 16):
                lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
                rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
                partial = matmul(lhs_tile, rhs_tile)
                deslice(out, partial, [m0, n0], [16, 16], [1, 1])
        return out

    module = mlir_gen(
        tiled_matmul,
        Memory([32, 16], NumericType.Float32),
        Memory([16, 32], NumericType.Float32),
    )

    NnLoweringPass().apply(Context(), module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelMatmulOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnMatmulOp) for op in module.walk())
    assert sum(1 for op in module.walk() if isinstance(op, SymbolForOp)) == 2


# TC-PASS-NNL-020A
# 测试目的: 验证 nn.matmul 动态输出维度通过公开 NnLoweringPass 生成 symbol.get_dim 与 kernel.matmul。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_matmul.py -k test_nn_lowering_matmul_dynamic_output_dims
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_matmul.py
def test_nn_lowering_matmul_dynamic_output_dims() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    lhs_type = memory_type(["M", 3], ["K", 1], f32, space)
    rhs_type = memory_type([3, "N"], ["N", 1], f32, space)
    result_type = memory_type(["M", "N"], ["N", 1], f32, space)

    block = Block(arg_types=[lhs_type, rhs_type])
    matmul_op = NnMatmulOp(block.args[0], block.args[1], result_type, space)
    block.add_op(matmul_op)
    block.add_op(func.ReturnOp(matmul_op.result))
    module = ModuleOp(
        [
            func.FuncOp(
                "matmul_dynamic_output",
                FunctionType.from_lists([lhs_type, rhs_type], [result_type]),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelMatmulOp)]
    symbol_dims = [op for op in module.walk() if isinstance(op, SymbolGetDimOp)]
    assert len(kernel_ops) == 1
    assert len(symbol_dims) == 2
    assert not any(isinstance(op, NnMatmulOp) for op in module.walk())

    symbolic_stride_lhs_type = memory_type([2, 3], ["K", 1], f32, space)
    symbolic_stride_rhs_type = memory_type([3, 4], ["N", 1], f32, space)
    symbolic_stride_result_type = memory_type([2, 4], ["N", 1], f32, space)
    symbolic_stride_block = Block(arg_types=[symbolic_stride_lhs_type, symbolic_stride_rhs_type])
    symbolic_stride_op = NnMatmulOp(
        symbolic_stride_block.args[0],
        symbolic_stride_block.args[1],
        symbolic_stride_result_type,
        space,
    )
    symbolic_stride_block.add_op(symbolic_stride_op)
    symbolic_stride_block.add_op(func.ReturnOp(symbolic_stride_op.result))
    symbolic_stride_module = ModuleOp(
        [
            func.FuncOp(
                "matmul_symbolic_stride",
                FunctionType.from_lists(
                    [symbolic_stride_lhs_type, symbolic_stride_rhs_type],
                    [symbolic_stride_result_type],
                ),
                Region(symbolic_stride_block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), symbolic_stride_module)

    assert len([op for op in symbolic_stride_module.walk() if isinstance(op, KernelMatmulOp)]) == 1


# TC-PASS-NNL-020C
# 测试目的: 验证 DSL runtime type-level 维度在 matmul contracting 轴同名时可通过公开 NnLoweringPass。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_matmul.py -k test_nn_lowering_matmul_accepts_runtime_contract_dims
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_matmul.py
def test_nn_lowering_matmul_accepts_runtime_contract_dims() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    lhs_type = memory_type(["runtime_dim_0", "runtime_dim_1"], ["runtime_dim_1", 1], f32, space)
    rhs_type = memory_type(["runtime_dim_1", "runtime_dim_2"], ["runtime_dim_2", 1], f32, space)
    result_type = memory_type(["runtime_dim_0", "runtime_dim_2"], ["runtime_dim_2", 1], f32, space)
    block = Block(arg_types=[lhs_type, rhs_type])
    matmul_op = NnMatmulOp(block.args[0], block.args[1], result_type, space)
    block.add_op(matmul_op)
    block.add_op(func.ReturnOp(matmul_op.result))
    module = ModuleOp(
        [
            func.FuncOp(
                "matmul_runtime_contract_dims",
                FunctionType.from_lists([lhs_type, rhs_type], [result_type]),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    assert len([op for op in module.walk() if isinstance(op, KernelMatmulOp)]) == 1
    assert not any(isinstance(op, NnMatmulOp) for op in module.walk())


# TC-PASS-NNL-020A2
# 测试目的: 验证 nn.matmul lowering 不把不同 runtime_dim_* contracting 维度互相匹配。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_matmul.py -k test_nn_lowering_matmul_rejects_unrelated_runtime_contract_dims
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_matmul.py
def test_nn_lowering_matmul_rejects_unrelated_runtime_contract_dims() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    lhs_type = memory_type(["runtime_dim_0", "runtime_dim_1"], ["runtime_dim_1", 1], f32, space)
    rhs_type = memory_type(["runtime_dim_2", "runtime_dim_3"], ["runtime_dim_3", 1], f32, space)
    result_type = memory_type(["runtime_dim_0", "runtime_dim_3"], ["runtime_dim_3", 1], f32, space)
    block = Block(arg_types=[lhs_type, rhs_type])
    matmul_op = NnMatmulOp(block.args[0], block.args[1], result_type, space)
    block.add_op(matmul_op)
    block.add_op(func.ReturnOp(matmul_op.result))
    module = ModuleOp(
        [
            func.FuncOp(
                "matmul_unrelated_runtime_contract_dims",
                FunctionType.from_lists([lhs_type, rhs_type], [result_type]),
                Region(block),
            )
        ]
    )

    with pytest.raises(KernelCodeError, match="matmul contracting dimensions must match"):
        NnLoweringPass().apply(Context(), module)


# TC-PASS-NNL-020B
# 测试目的: 验证 nn.matmul shape/stride/operand 错误经公开 NnLoweringPass 保持稳定错误语义。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_matmul.py -k test_nn_lowering_matmul_public_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_matmul.py
def test_nn_lowering_matmul_public_error_matrix() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    lhs_type = memory_type([2, 3], [3, 1], f32, space)
    rhs_type = memory_type([3, 4], [4, 1], f32, space)
    result_type = memory_type([2, 4], [4, 1], f32, space)

    non_memory_block = Block(arg_types=[lhs_type, i32])
    non_memory_op = NnMatmulOp(non_memory_block.args[0], non_memory_block.args[1], result_type, space)
    non_memory_block.add_op(non_memory_op)
    non_memory_block.add_op(func.ReturnOp(non_memory_op.result))
    non_memory_module = ModuleOp(
        [
            func.FuncOp(
                "matmul_non_memory_operand",
                FunctionType.from_lists([lhs_type, i32], [result_type]),
                Region(non_memory_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn.matmul operands must be nn.memory"):
        NnLoweringPass().apply(Context(), non_memory_module)

    rank_lhs_type = memory_type([6], [1], f32, space)
    rank_block = Block(arg_types=[rank_lhs_type, rhs_type])
    rank_op = NnMatmulOp(rank_block.args[0], rank_block.args[1], result_type, space)
    rank_block.add_op(rank_op)
    rank_block.add_op(func.ReturnOp(rank_op.result))
    rank_module = ModuleOp(
        [
            func.FuncOp(
                "matmul_rank_error",
                FunctionType.from_lists([rank_lhs_type, rhs_type], [result_type]),
                Region(rank_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="matmul requires rank-2 memory types"):
        NnLoweringPass().apply(Context(), rank_module)

    bad_contract_rhs_type = memory_type([5, 4], [4, 1], f32, space)
    contract_block = Block(arg_types=[lhs_type, bad_contract_rhs_type])
    contract_op = NnMatmulOp(contract_block.args[0], contract_block.args[1], result_type, space)
    contract_block.add_op(contract_op)
    contract_block.add_op(func.ReturnOp(contract_op.result))
    contract_module = ModuleOp(
        [
            func.FuncOp(
                "matmul_contract_error",
                FunctionType.from_lists([lhs_type, bad_contract_rhs_type], [result_type]),
                Region(contract_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="matmul contracting dimensions must match"):
        NnLoweringPass().apply(Context(), contract_module)

    bad_result_type = memory_type([2, 5], [5, 1], f32, space)
    result_block = Block(arg_types=[lhs_type, rhs_type])
    result_op = NnMatmulOp(result_block.args[0], result_block.args[1], bad_result_type, space)
    result_block.add_op(result_op)
    result_block.add_op(func.ReturnOp(result_op.result))
    result_module = ModuleOp(
        [
            func.FuncOp(
                "matmul_result_error",
                FunctionType.from_lists([lhs_type, rhs_type], [bad_result_type]),
                Region(result_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="matmul output shape must match operands"):
        NnLoweringPass().apply(Context(), result_module)

    bad_stride_rhs_type = memory_type([3, 4], [1, 4], f32, space)
    stride_value_block = Block(arg_types=[lhs_type, bad_stride_rhs_type])
    stride_value_op = NnMatmulOp(stride_value_block.args[0], stride_value_block.args[1], result_type, space)
    stride_value_block.add_op(stride_value_op)
    stride_value_block.add_op(func.ReturnOp(stride_value_op.result))
    stride_value_module = ModuleOp(
        [
            func.FuncOp(
                "matmul_stride_value_error",
                FunctionType.from_lists([lhs_type, bad_stride_rhs_type], [result_type]),
                Region(stride_value_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="matmul stride must be contiguous"):
        NnLoweringPass().apply(Context(), stride_value_module)
