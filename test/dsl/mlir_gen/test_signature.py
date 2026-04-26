"""mlir_gen public signature tests.

创建者: 朽木露琪亚
最后一次更改: 金铲铲大作战

功能说明:
- 仅通过公开 build_func_op/build_func_op_from_ast 入口验证签名相关行为。
- 不直接调用 signature 私有 helper。

使用示例:
- pytest -q test/dsl/mlir_gen/test_signature.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/__init__.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_signature.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntAttr

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import parse_function
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
from kernel_gen.operation.dma import alloc
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _tensor_arg(shape: list[int]) -> Memory:
    return Memory(shape, NumericType.Float32)


# TC-MLIR-GEN-SIG-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: runtime SymbolDim 通过公开 build_func_op 入口落到 !symbol.int 签名。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_func_op_symbol_dim_uses_symbol_value_signature
def test_build_func_op_symbol_dim_uses_symbol_value_signature() -> None:
    def kernel(s: int) -> int:
        return s

    func_op = build_func_op(kernel, SymbolDim("S"))
    arg_types = list(func_op.function_type.inputs)
    result_types = list(func_op.function_type.outputs)
    assert arg_types == [SymbolValueType.from_expr("S")]
    assert result_types == [SymbolValueType.from_expr("S")]


# TC-MLIR-GEN-SIG-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 公开 build_func_op_from_ast 入口在符号标量函数缺失 runtime_args 时返回错误。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_func_op_from_ast_rejects_missing_runtime_args_for_symbol_scalar_function
def test_build_func_op_from_ast_rejects_missing_runtime_args_for_symbol_scalar_function() -> None:
    def kernel(s: int) -> int:
        return s

    func_ast = parse_function(kernel)
    with pytest.raises(AstVisitorError, match="requires explicit runtime args"):
        build_func_op_from_ast(func_ast)


# TC-MLIR-GEN-SIG-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 公开 build_func_op 入口在 dma.alloc-only 场景下按 runtime_args 构造返回类型。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_func_op_builds_dma_alloc_only_result_type_from_runtime_args
def test_build_func_op_builds_dma_alloc_only_result_type_from_runtime_args() -> None:
    def kernel(size: int) -> "Tensor[f32, 2, size]":
        return alloc([2, size], NumericType.Float32, MemorySpace.GM)

    func_op = build_func_op(kernel, 4)
    result_types = list(func_op.function_type.outputs)
    assert len(result_types) == 1
    assert isinstance(result_types[0], NnMemoryType)
    assert list(result_types[0].shape.data) == [IntAttr(2), IntAttr(4)]
    assert any(isinstance(op, DmaAllocOp) for op in func_op.body.block.ops)


# TC-MLIR-GEN-SIG-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 公开 build_func_op 在常规 tensor 输入场景保持 func.func 入口。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_func_op_tensor_input_keeps_func_public_contract
def test_build_func_op_tensor_input_keeps_func_public_contract() -> None:
    def kernel(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    func_op = build_func_op(kernel, _tensor_arg([4]))
    assert isinstance(func_op, func.FuncOp)
    assert len(list(func_op.function_type.inputs)) == 1
    assert len(list(func_op.function_type.outputs)) == 1
