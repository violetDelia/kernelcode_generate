"""DSL symbol.floordiv expectation.

创建者: 榕
最后一次更改: 朽木露琪亚

功能说明:
- 验证 `build_func_op` 可以将 Python `floordiv(a, b)` 函数转换为 `FuncOp`。
- 验证静态整除、动态符号与混合输入在 lowering 后保持 `symbol.int` 语义。
- 验证函数体内生成一个 `SymbolFloorDivOp` 和一个 `ReturnOp`。

使用示例:
- python expectation/dsl/mlir_gen/dialect/symbol/floordiv.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.compare import assert_dynamic_symbol_int, assert_static_symbol_int
from expectation.utils.random import get_random_alpha_string, get_random_int, get_random_non_zero_int
from kernel_gen.dialect.symbol import SymbolFloorDivOp
from kernel_gen.dsl.mlir_gen import build_func_op
import kernel_gen.operation.nn as nn
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

LHS = get_random_int()
RHS = get_random_non_zero_int()
SYMBOL_LHS_NAME = get_random_alpha_string().upper()
SYMBOL_RHS_NAME = get_random_alpha_string().upper()
while SYMBOL_RHS_NAME == SYMBOL_LHS_NAME:
    SYMBOL_RHS_NAME = get_random_alpha_string().upper()
SYMBOL_LHS = SymbolDim(SYMBOL_LHS_NAME)
SYMBOL_RHS = SymbolDim(SYMBOL_RHS_NAME)


def floordiv_func(a: int, b: int) -> int:
    c = a // b
    return c


def floordiv_func2(a: int, b: int) -> int:
    return nn.floordiv(a, b)

TARGET_FUNCS: tuple[Callable[[int, int], int], ...] = (floordiv_func, floordiv_func2)


def check_const_floordiv_const() -> None:
    for target_func in TARGET_FUNCS:
        expected_expr = target_func(LHS, RHS)
        func_op = build_func_op(target_func, LHS, RHS)
        assert isinstance(func_op, FuncOp)
        assert_static_symbol_int(func_op.args[0].type, LHS)
        assert_static_symbol_int(func_op.args[1].type, RHS)
        floordiv_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolFloorDivOp)]
        assert len(floordiv_ops) == 1
        assert_static_symbol_int(floordiv_ops[0].result.type, expected_expr)
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert_static_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_dynamic_floordiv_dynamic() -> None:
    for target_func in TARGET_FUNCS:
        expected_expr = target_func(SYMBOL_LHS, SYMBOL_RHS)
        func_op = build_func_op(target_func, SYMBOL_LHS, SYMBOL_RHS)
        assert isinstance(func_op, FuncOp)
        assert_dynamic_symbol_int(func_op.args[0].type, SYMBOL_LHS)
        assert_dynamic_symbol_int(func_op.args[1].type, SYMBOL_RHS)
        floordiv_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolFloorDivOp)]
        assert len(floordiv_ops) == 1
        assert_dynamic_symbol_int(floordiv_ops[0].result.type, expected_expr)
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_const_floordiv_dynamic() -> None:
    for target_func in TARGET_FUNCS:
        expected_expr = target_func(LHS, SYMBOL_RHS)
        func_op = build_func_op(target_func, LHS, SYMBOL_RHS)
        assert isinstance(func_op, FuncOp)
        assert_static_symbol_int(func_op.args[0].type, LHS)
        assert_dynamic_symbol_int(func_op.args[1].type, SYMBOL_RHS)
        floordiv_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolFloorDivOp)]
        assert len(floordiv_ops) == 1
        assert_dynamic_symbol_int(floordiv_ops[0].result.type, expected_expr)
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_dynamic_floordiv_const() -> None:
    for target_func in TARGET_FUNCS:
        expected_expr = target_func(SYMBOL_LHS, RHS)
        func_op = build_func_op(target_func, SYMBOL_LHS, RHS)
        assert isinstance(func_op, FuncOp)
        assert_dynamic_symbol_int(func_op.args[0].type, SYMBOL_LHS)
        assert_static_symbol_int(func_op.args[1].type, RHS)
        floordiv_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolFloorDivOp)]
        assert len(floordiv_ops) == 1
        assert_dynamic_symbol_int(floordiv_ops[0].result.type, expected_expr)
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


check_const_floordiv_const()
check_dynamic_floordiv_dynamic()
check_const_floordiv_dynamic()
check_dynamic_floordiv_const()
