"""DMA alloc expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用统一 expectation 结构描述 `alloc(...)` 的 DSL 调用方式。
- 覆盖静态整数、symbol、symbol + const 三类 shape 输入。
- 覆盖显式 stride 输入场景。
- 覆盖常量 shape（无运行时参数）输入场景。
- 覆盖错误参数的异常场景。
- 校验 `build_func_op` 生成的函数返回类型与 `dma.alloc` 结果类型一致。

使用示例:
- python expectation/dsl/mlir_gen/dialect/dma/alloc.py

关联文件:
- spec: spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/ast.py, kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
"""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path = [
    search_path
    for search_path in sys.path
    if Path(search_path or ".").resolve() != SCRIPT_DIR
]

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp

from expectation.utils.compare import assert_memory
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int
from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast_visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import alloc
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _assert_alloc_output_matches_func_return(func_op: FuncOp) -> None:
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]
    assert len(alloc_ops) == 1
    assert list(func_op.function_type.outputs) == [alloc_ops[0].result.type]


def _assert_output_memory_matches_expected(func_op: FuncOp, expected_memory: object) -> None:
    outputs = list(func_op.function_type.outputs)
    assert len(outputs) == 1
    assert_memory(outputs[0], expected_memory)


# case 1: static int shape
ALLOC_ROWS = get_random_non_zero_int(1, 8)
ALLOC_COLS = get_random_non_zero_int(1, 8)


def alloc_kernel(rank1, rank2) -> f"Tensor[f32, {ALLOC_ROWS}, {ALLOC_COLS}]":
    return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)


func_op_static = build_func_op(alloc_kernel, ALLOC_ROWS, ALLOC_COLS)
expected_static = alloc_kernel(ALLOC_ROWS, ALLOC_COLS)


assert isinstance(func_op_static, FuncOp)
assert list(func_op_static.function_type.inputs) == [
    SymbolValueType.from_expr(str(ALLOC_ROWS)),
    SymbolValueType.from_expr(str(ALLOC_COLS)),
]
_assert_alloc_output_matches_func_return(func_op_static)
_assert_output_memory_matches_expected(func_op_static, expected_static)


# case 2: symbol shape
SYMBOL_LHS_NAME = get_random_alpha_string().upper()
SYMBOL_RHS_NAME = get_random_alpha_string().upper()
SYMBOL_LHS = SymbolDim(SYMBOL_LHS_NAME)
SYMBOL_RHS = SymbolDim(SYMBOL_RHS_NAME)


def alloc_symbol_kernel(rank1, rank2) -> f"Tensor[f32, {SYMBOL_LHS_NAME}, {SYMBOL_RHS_NAME}]":
    return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)


func_op_symbol = build_func_op(alloc_symbol_kernel, SYMBOL_LHS, SYMBOL_RHS)
expected_symbol = alloc_symbol_kernel(SYMBOL_LHS, SYMBOL_RHS)
assert isinstance(func_op_symbol, FuncOp)
assert list(func_op_symbol.function_type.inputs) == [
    SymbolValueType.from_expr(SYMBOL_LHS_NAME),
    SymbolValueType.from_expr(SYMBOL_RHS_NAME),
]
alloc_ops_symbol = [op for op in func_op_symbol.body.block.ops if isinstance(op, DmaAllocOp)]
assert len(alloc_ops_symbol) == 1
assert [attr.data for attr in alloc_ops_symbol[0].result.type.shape.data] == [
    SYMBOL_LHS_NAME,
    SYMBOL_RHS_NAME,
]
_assert_alloc_output_matches_func_return(func_op_symbol)
_assert_output_memory_matches_expected(func_op_symbol, expected_symbol)


# case 3: symbol + const shape
SHAPE_CONST_LHS = get_random_non_zero_int(1, 8)
SHAPE_CONST_RHS = get_random_non_zero_int(1, 8)
SYMBOL_PLUS_CONST_LHS = SymbolDim(SYMBOL_LHS_NAME) + SHAPE_CONST_LHS
SYMBOL_PLUS_CONST_RHS = SymbolDim(SYMBOL_RHS_NAME) + SHAPE_CONST_RHS
SYMBOL_PLUS_CONST_LHS_EXPR = str(SYMBOL_PLUS_CONST_LHS.get_symbol())
SYMBOL_PLUS_CONST_RHS_EXPR = str(SYMBOL_PLUS_CONST_RHS.get_symbol())


def alloc_symbol_plus_const_kernel(
    rank1,
    rank2,
) -> f"Tensor[f32, {SYMBOL_PLUS_CONST_LHS_EXPR}, {SYMBOL_PLUS_CONST_RHS_EXPR}]":
    return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)


func_op_symbol_plus_const = build_func_op(
    alloc_symbol_plus_const_kernel,
    SYMBOL_PLUS_CONST_LHS,
    SYMBOL_PLUS_CONST_RHS,
)
expected_symbol_plus_const = alloc_symbol_plus_const_kernel(
    SYMBOL_PLUS_CONST_LHS,
    SYMBOL_PLUS_CONST_RHS,
)
assert isinstance(func_op_symbol_plus_const, FuncOp)
assert list(func_op_symbol_plus_const.function_type.inputs) == [
    SymbolValueType.from_expr(SYMBOL_PLUS_CONST_LHS_EXPR),
    SymbolValueType.from_expr(SYMBOL_PLUS_CONST_RHS_EXPR),
]
alloc_ops_symbol_plus_const = [
    op for op in func_op_symbol_plus_const.body.block.ops if isinstance(op, DmaAllocOp)
]
assert len(alloc_ops_symbol_plus_const) == 1
assert [attr.data for attr in alloc_ops_symbol_plus_const[0].result.type.shape.data] == [
    SYMBOL_PLUS_CONST_LHS_EXPR,
    SYMBOL_PLUS_CONST_RHS_EXPR,
]
_assert_alloc_output_matches_func_return(func_op_symbol_plus_const)
_assert_output_memory_matches_expected(func_op_symbol_plus_const, expected_symbol_plus_const)

print(func_op_static)
print(func_op_symbol)
print(func_op_symbol_plus_const)


# case 4: const alloc without runtime args
def alloc_const_kernel() -> "Tensor[f32, 3, 5]":
    return alloc([3, 5], NumericType.Float32, MemorySpace.SM)


func_op_const = build_func_op(alloc_const_kernel)
expected_const = alloc_const_kernel()
assert isinstance(func_op_const, FuncOp)
assert list(func_op_const.function_type.inputs) == []
_assert_alloc_output_matches_func_return(func_op_const)
_assert_output_memory_matches_expected(func_op_const, expected_const)

print(func_op_const)


# case 5: explicit stride
STRIDE_ROWS = get_random_non_zero_int(2, 8)
STRIDE_COLS = get_random_non_zero_int(2, 8)
ROW_STRIDE = STRIDE_COLS
COL_STRIDE = 1


def alloc_with_stride_kernel(
    rank1,
    rank2,
    stride1,
    stride2,
) -> f"Tensor[f32, {STRIDE_ROWS}, {STRIDE_COLS}]":
    return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM, stride=[stride1, stride2])


func_op_stride = build_func_op(alloc_with_stride_kernel, STRIDE_ROWS, STRIDE_COLS, ROW_STRIDE, COL_STRIDE)
expected_stride = alloc_with_stride_kernel(STRIDE_ROWS, STRIDE_COLS, ROW_STRIDE, COL_STRIDE)
assert isinstance(func_op_stride, FuncOp)
assert list(func_op_stride.function_type.inputs) == [
    SymbolValueType.from_expr(str(STRIDE_ROWS)),
    SymbolValueType.from_expr(str(STRIDE_COLS)),
    SymbolValueType.from_expr(str(ROW_STRIDE)),
    SymbolValueType.from_expr(str(COL_STRIDE)),
]
_assert_alloc_output_matches_func_return(func_op_stride)
_assert_output_memory_matches_expected(func_op_stride, expected_stride)


# case 6: invalid arguments in kernel should raise
def alloc_invalid_dtype_kernel(rank1, rank2) -> f"Tensor[f32, {ALLOC_ROWS}, {ALLOC_COLS}]":
    return alloc([rank1, rank2], "f32", MemorySpace.SM)


try:
    build_func_op(alloc_invalid_dtype_kernel, ALLOC_ROWS, ALLOC_COLS)
    assert False, "build_func_op should fail when alloc dtype is invalid inside kernel"
except AstVisitorError as exc:
    assert "alloc dtype must be NumericType" in str(exc)


def alloc_invalid_space_kernel(rank1, rank2) -> f"Tensor[f32, {ALLOC_ROWS}, {ALLOC_COLS}]":
    return alloc([rank1, rank2], NumericType.Float32, "shared")


try:
    build_func_op(alloc_invalid_space_kernel, ALLOC_ROWS, ALLOC_COLS)
    assert False, "build_func_op should fail when alloc space is invalid inside kernel"
except AstVisitorError as exc:
    assert "alloc space must be MemorySpace" in str(exc)


def alloc_invalid_stride_kernel(
    rank1,
    rank2,
    stride1,
    stride2,
) -> f"Tensor[f32, {ALLOC_ROWS}, {ALLOC_COLS}]":
    return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM, stride=[stride1, stride2])


try:
    build_func_op(alloc_invalid_stride_kernel, ALLOC_ROWS, ALLOC_COLS, ALLOC_COLS, 2)
    assert False, "build_func_op should fail when alloc stride is non-contiguous inside kernel"
except AstVisitorError as exc:
    assert "dma.alloc only supports contiguous stride" in str(exc)

print(func_op_stride)
