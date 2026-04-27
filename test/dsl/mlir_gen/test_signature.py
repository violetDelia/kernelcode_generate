"""mlir_gen signature public contract tests.

创建者: 朽木露琪亚
最后一次更改: 小李飞刀

功能说明:
- 通过 `build_func_op(...)` / `build_func_op_from_ast(...)` 公开入口覆盖签名推导与返回校验的稳定行为。
- 不直连 `signature.py` 私有 helper，不把内部实现细节当测试合同。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_signature.py

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

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import parse_function
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _tensor_arg(shape: list[int | str], dtype: NumericType = NumericType.Float32) -> Memory:
    """构造公开 `build_func_op(...)` 入参。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为签名公开回归统一生成连续布局 `Memory`。

    使用示例:
    - arg = _tensor_arg([2, 2])

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/__init__.py](kernel_gen/dsl/mlir_gen/__init__.py)
    """

    return Memory(shape, dtype)


# TC-MLIR-GEN-SIG-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 build_func_op_from_ast 在提供 SymbolDim runtime_args 时按公开合同生成 symbol 签名。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_func_op_from_ast_uses_runtime_args_for_symbol_signature
def test_build_func_op_from_ast_uses_runtime_args_for_symbol_signature() -> None:
    def only_symbol(expr: int) -> int:
        return expr

    func_ast = parse_function(only_symbol)
    func_op = build_func_op_from_ast(func_ast, runtime_args=[SymbolDim("expr")])
    assert list(func_op.function_type.inputs) == [SymbolValueType.from_expr("expr")]
    assert list(func_op.function_type.outputs) == [SymbolValueType.from_expr("expr")]


# TC-MLIR-GEN-SIG-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 alloc-only kernel 在 symbol shape runtime_args 下保持公开符号签名与结果 shape。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_func_op_supports_dma_alloc_helper_with_symbol_shape_args
def test_build_func_op_supports_dma_alloc_helper_with_symbol_shape_args() -> None:
    from kernel_gen.operation.dma import alloc

    symbol_lhs = SymbolDim("M")
    symbol_rhs = SymbolDim("N")
    lhs_expr = str(symbol_lhs.get_symbol())
    rhs_expr = str(symbol_rhs.get_symbol())

    def alloc_kernel(rank1: int, rank2: int) -> f"Tensor[f32, {lhs_expr}, {rhs_expr}]":
        return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)

    func_op = build_func_op(
        alloc_kernel,
        symbol_lhs,
        symbol_rhs,
        globals={"lhs_expr": lhs_expr, "rhs_expr": rhs_expr},
    )
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]

    assert list(func_op.function_type.inputs) == [
        SymbolValueType.from_expr(lhs_expr),
        SymbolValueType.from_expr(rhs_expr),
    ]
    assert len(alloc_ops) == 1
    assert [attr.data for attr in alloc_ops[0].result.type.shape.data] == [lhs_expr, rhs_expr]
    assert list(func_op.function_type.outputs) == [alloc_ops[0].result.type]


# TC-MLIR-GEN-SIG-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 alloc-only kernel 仍拒绝非连续 stride。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_func_op_rejects_dma_alloc_helper_with_non_contiguous_stride
def test_build_func_op_rejects_dma_alloc_helper_with_non_contiguous_stride() -> None:
    from kernel_gen.operation.dma import alloc

    def alloc_kernel(rank1: int, rank2: int, stride1: int, stride2: int) -> "Tensor[f32, 2, 3]":
        return alloc(
            [rank1, rank2],
            NumericType.Float32,
            MemorySpace.SM,
            stride=[stride1, stride2],
        )

    with pytest.raises(AstVisitorError, match="dma.alloc only supports contiguous stride"):
        build_func_op(alloc_kernel, 2, 3, 3, 2)


# TC-MLIR-GEN-SIG-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 mixed dtype 返回注解必须来自实际操作数 element_type。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_mixed_dtype_return_annotation_requires_operand_element_type
def test_mixed_dtype_return_annotation_requires_operand_element_type() -> None:
    def mul_mixed_invalid(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[i32, 2, 2]",
    ) -> "Tensor[f16, 2, 2]":
        return lhs * rhs

    with pytest.raises(AstVisitorError, match="Return type does not match annotation"):
        build_func_op(
            mul_mixed_invalid,
            _tensor_arg([2, 2], NumericType.Float32),
            _tensor_arg([2, 2], NumericType.Int32),
        )


# TC-MLIR-GEN-SIG-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 flatten 的返回 shape 仍按公开合同归一为一维 numel。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_func_op_supports_flatten_return_annotation
def test_build_func_op_supports_flatten_return_annotation() -> None:
    from kernel_gen.operation.dma import flatten

    def flatten_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 16]":
        return flatten(src)

    func_op = build_func_op(flatten_kernel, _tensor_arg([4, 4]))
    result_type = list(func_op.function_type.outputs)[0]
    assert [attr.data for attr in result_type.shape.data] == [16]
    assert [attr.data for attr in result_type.stride.data] == [1]
