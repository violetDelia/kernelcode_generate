"""nn_lowering matmul tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 验证 nn.matmul -> kernel.matmul 的 lowering 目标与结果类型约束。

使用示例:
- pytest -q test/pass/nn_lowering/matmul.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
- 测试文件: test/pass/nn_lowering/matmul.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMatmulOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import alloc, deslice, slice
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.scf import loop
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


# TC-PASS-NNL-020
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 09:19:46 +0800
# 最近一次运行成功时间: 2026-04-12 09:19:46 +0800
# 测试目的: 验证 nn.matmul lowering 目标为 kernel.matmul 且结果类型一致。
# 使用示例: pytest -q test/pass/nn_lowering/matmul.py -k test_nn_lowering_matmul_target
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/matmul.py
def test_nn_lowering_matmul_target() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    lhs_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(3)]),
        ArrayAttr([IntAttr(3), IntAttr(1)]),
        f32,
        space,
    )
    rhs_type = NnMemoryType(
        ArrayAttr([IntAttr(3), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        f32,
        space,
    )
    result_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        f32,
        space,
    )

    block = Block(arg_types=[lhs_type, rhs_type])
    matmul = NnMatmulOp(block.args[0], block.args[1], result_type, space)
    block.add_op(matmul)
    block.add_op(func.ReturnOp(matmul.result))
    func_type = FunctionType.from_lists([lhs_type, rhs_type], [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])

    NnLoweringPass().run(module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelMatmulOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnMatmulOp) for op in module.walk())
    kernel_op = kernel_ops[0]
    assert isinstance(kernel_op.out.type, NnMemoryType)
    assert kernel_op.out.type.shape == result_type.shape
    assert kernel_op.out.type.stride == result_type.stride


# TC-PASS-NNL-021
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-15 11:10:00 +0800
# 最近一次运行成功时间: N/A
# 测试目的: 验证 symbol.for region 内的 nn.matmul 也会 lower 为 kernel.matmul。
# 使用示例: pytest -q test/pass/nn_lowering/matmul.py -k test_nn_lowering_matmul_inside_symbol_for
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/matmul.py
def test_nn_lowering_matmul_inside_symbol_for() -> None:
    def tiled_matmul(lhs: "Tensor[f32, 32, 16]", rhs: "Tensor[f32, 16, 32]") -> "Tensor[f32, 32, 32]":
        out = alloc([32, 32], NumericType.Float32, MemorySpace.GM)
        for m0 in loop(0, 32, 16):
            for n0 in loop(0, 32, 16):
                lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
                rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
                partial = matmul(lhs_tile, rhs_tile)
                deslice(partial, out, [m0, n0], [16, 16], [1, 1])
        return out

    func_op = build_func_op(
        tiled_matmul,
        Memory([32, 16], NumericType.Float32),
        Memory([16, 32], NumericType.Float32),
    )
    module = ModuleOp([func_op])

    NnLoweringPass().run(module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelMatmulOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnMatmulOp) for op in module.walk())
    assert sum(1 for op in module.walk() if isinstance(op, SymbolForOp)) == 2
