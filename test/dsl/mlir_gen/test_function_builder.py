"""mlir_gen function builder tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 build_func_op/build_func_op_from_ast 的运行时参数与基础装配行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen.function_builder --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_function_builder.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_function_builder.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/function_builder.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_function_builder.py
"""

from __future__ import annotations

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, i8

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from kernel_gen.dsl.ast import (
    BlockAST,
    ConstAST,
    FunctionAST,
    ScalarArgAST,
    TensorAST,
    parse_function,
)
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
from kernel_gen.operation.dma import alloc, deslice, fill, reshape, slice
from kernel_gen.operation.nn import add, reduce_max
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _tensor_arg(shape: list[int]) -> Memory:
    """构造 Memory 测试入参。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 简化 build_func_op_from_ast 的 runtime_args 构造。

    使用示例:
    - arg = _tensor_arg([2, 2])

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return Memory(shape, NumericType.Float32)


def _memory_type(
    shape: list[int | str],
    stride: list[int | str],
    *,
    space: str = "global",
) -> NnMemoryType:
    def _attr(value: int | str) -> IntAttr | StringAttr:
        if isinstance(value, int):
            return IntAttr(value)
        return StringAttr(value)

    return NnMemoryType(
        ArrayAttr([_attr(dim) for dim in shape]),
        ArrayAttr([_attr(dim) for dim in stride]),
        i8,
        NnMemorySpaceAttr.from_name(space),
    )


# TC-MLIR-GEN-FUNC-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 运行时参数缺失时必须报错。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/function_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_function_builder.py -k test_build_func_op_requires_runtime_args
def test_build_func_op_requires_runtime_args() -> None:
    def kernel(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    with pytest.raises(AstVisitorError) as excinfo:
        build_func_op(kernel, globals={"X": 1})
    assert "globals/builtins cannot replace function runtime args" in str(excinfo.value)


# TC-MLIR-GEN-FUNC-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: build_func_op_from_ast 可生成 func.FuncOp。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/function_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_function_builder.py -k test_build_func_op_from_ast_builds_func
def test_build_func_op_from_ast_builds_func() -> None:
    def identity(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    func_ast = parse_function(identity)
    func_op = build_func_op_from_ast(func_ast, runtime_args=[_tensor_arg([2, 2])])
    assert isinstance(func_op, func.FuncOp)
    assert func_op.sym_name.data == "identity"


def test_build_func_op_from_ast_error_edges() -> None:
    with pytest.raises(AstVisitorError, match="Function return requires explicit return syntax or annotation"):
        build_func_op_from_ast(
            FunctionAST(
                name="missing_return_contract",
                inputs=[],
                outputs=[],
                body=BlockAST([ConstAST(1)]),
                returns_none=False,
            ),
        )

    value_return_ast = FunctionAST(
        name="empty_value_body",
        inputs=[],
        outputs=[ScalarArgAST("out", int)],
        body=BlockAST([]),
        returns_none=False,
    )
    with pytest.raises(AstVisitorError, match="Function body is empty"):
        build_func_op_from_ast(value_return_ast)


def test_build_func_op_from_ast_rejects_reduce_max_axis_out_of_range() -> None:
    def kernel(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2]":
        return reduce_max(x, axis=3)

    func_ast = parse_function(kernel)

    with pytest.raises(AstVisitorError, match=r"reduce_max axis must be within \[-2, 1\]"):
        build_func_op_from_ast(func_ast, runtime_args=[_tensor_arg([2, 2])])


def test_build_func_op_accepts_runtime_driven_memory_placeholder_annotation() -> None:
    runtime_arg = _tensor_arg([2, 4])

    def kernel(x: Memory) -> "Tensor[f32, 2, 4]":
        return x

    func_op = build_func_op(kernel, runtime_arg)

    assert isinstance(func_op, func.FuncOp)
    block_args = tuple(func_op.body.block.args)
    assert len(block_args) == 1
    assert isinstance(block_args[0].type, NnMemoryType)
    assert block_args[0].type.shape == _memory_type([2, 4], [4, 1]).shape


def test_build_func_op_accepts_runtime_driven_symbol_placeholder_annotation() -> None:
    runtime_arg = SymbolDim("N")

    def kernel(n: SymbolDim) -> int:
        return n

    func_op = build_func_op(kernel, runtime_arg)

    block_args = tuple(func_op.body.block.args)
    assert len(block_args) == 1
    assert block_args[0].type == SymbolValueType.from_expr("N")
    assert func_op.function_type.outputs.data[0] == SymbolValueType.from_expr("N")


def test_build_func_op_supports_kernel_contract_metadata_assert_and_shape_unpack() -> None:
    lhs = Memory(["B", "K"], NumericType.Float32)
    rhs = Memory(["B", "K"], NumericType.Float32)
    tile = SymbolDim("BR")

    def kernel(x: Memory, y: Memory, step: SymbolDim) -> int:
        assert x.dtype == y.dtype
        B, K = x.shape.get_shape()
        for b in loop(0, B, step):
            tile_buf = alloc([1, K], x.dtype, MemorySpace.TSM)
            fill(tile_buf, 0)
        return K

    func_op = build_func_op(kernel, lhs, rhs, tile)
    body_ops = list(func_op.body.block.ops)

    assert any(isinstance(op, SymbolGetDimOp) for op in body_ops)
    assert any(isinstance(op, func.ReturnOp) for op in body_ops)


def test_build_func_op_supports_kernel_contract_loop_local_rebinding() -> None:
    q = Memory(["M", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    tile = SymbolDim("TILE")

    def kernel(x: Memory, y: Memory, step: SymbolDim) -> None:
        M, N = x.shape.get_shape()
        acc = alloc([step, N], x.dtype, MemorySpace.TSM)
        fill(acc, 0)
        for m0 in loop(0, M, step):
            tile_buf = slice(x, [m0, 0], [step, N], [1, 1], MemorySpace.TSM)
            acc = add(acc, tile_buf)
        out_tile = reshape(acc, [step, N])
        deslice(out_tile, y, [0, 0], [step, N], [1, 1])

    func_op = build_func_op(kernel, q, out, tile)
    func_text = str(func_op)

    assert "symbol.for" in func_text
    assert '"dma.slice"' in func_text
    assert '"nn.add"' in func_text
    assert '"dma.reshape"' in func_text
    assert '"dma.deslice"' in func_text
