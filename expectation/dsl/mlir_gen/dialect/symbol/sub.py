"""DSL symbol.sub expectation.
[immutable-file]
创建者: 榕
最后一次更改: 朽木露琪亚

功能说明:
- 验证 `build_func_op` 可以将 Python `sub(a, b)` 函数转换为 `FuncOp`。
- 验证静态整数、动态符号与混合输入在 lowering 后保持 `symbol.int` 语义。
- 验证函数体内生成一个 `SymbolSubOp` 和一个 `ReturnOp`。

使用示例:
- python expectation/dsl/mlir_gen/dialect/symbol/sub.py

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
from expectation.utils.random import get_random_alpha_string, get_random_int
from kernel_gen.dialect.symbol import SymbolSubOp
from kernel_gen.dsl.mlir_gen import build_func_op
import kernel_gen.operation.nn as nn
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

LHS = get_random_int()
RHS = get_random_int()
SYMBOL_LHS_NAME = get_random_alpha_string().upper()
SYMBOL_RHS_NAME = get_random_alpha_string().upper()
while SYMBOL_RHS_NAME == SYMBOL_LHS_NAME:
    SYMBOL_RHS_NAME = get_random_alpha_string().upper()
SYMBOL_LHS = SymbolDim(SYMBOL_LHS_NAME)
SYMBOL_RHS = SymbolDim(SYMBOL_RHS_NAME)


def sub_func(a: int, b: int) -> int:
    c = a - b
    return c


def sub_func2(a: int, b: int) -> int:
    return nn.sub(a, b)

TARGET_FUNCS: tuple[Callable[[int, int], int], ...] = (sub_func, sub_func2)


def check_const_minus_const() -> None:
    for target_func in TARGET_FUNCS:
        expected_expr = target_func(LHS, RHS)
        func_op = build_func_op(target_func, LHS, RHS)
        assert isinstance(func_op, FuncOp)
        assert_static_symbol_int(func_op.args[0].type, LHS)
        assert_static_symbol_int(func_op.args[1].type, RHS)
        sub_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolSubOp)]
        assert len(sub_ops) == 1
        assert_static_symbol_int(sub_ops[0].result.type, expected_expr)
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert_static_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_dynamic_minus_dynamic() -> None:
    for target_func in TARGET_FUNCS:
        expected_expr = target_func(SYMBOL_LHS, SYMBOL_RHS)
        func_op = build_func_op(target_func, SYMBOL_LHS, SYMBOL_RHS)
        assert isinstance(func_op, FuncOp)
        assert_dynamic_symbol_int(func_op.args[0].type, SYMBOL_LHS)
        assert_dynamic_symbol_int(func_op.args[1].type, SYMBOL_RHS)
        sub_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolSubOp)]
        assert len(sub_ops) == 1
        assert_dynamic_symbol_int(sub_ops[0].result.type, expected_expr)
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_const_minus_dynamic() -> None:
    for target_func in TARGET_FUNCS:
        expected_expr = target_func(LHS, SYMBOL_RHS)
        func_op = build_func_op(target_func, LHS, SYMBOL_RHS)
        assert isinstance(func_op, FuncOp)
        assert_static_symbol_int(func_op.args[0].type, LHS)
        assert_dynamic_symbol_int(func_op.args[1].type, SYMBOL_RHS)
        sub_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolSubOp)]
        assert len(sub_ops) == 1
        assert_dynamic_symbol_int(sub_ops[0].result.type, expected_expr)
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_dynamic_minus_const() -> None:
    for target_func in TARGET_FUNCS:
        expected_expr = target_func(SYMBOL_LHS, RHS)
        func_op = build_func_op(target_func, SYMBOL_LHS, RHS)
        assert isinstance(func_op, FuncOp)
        assert_dynamic_symbol_int(func_op.args[0].type, SYMBOL_LHS)
        assert_static_symbol_int(func_op.args[1].type, RHS)
        sub_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolSubOp)]
        assert len(sub_ops) == 1
        assert_dynamic_symbol_int(sub_ops[0].result.type, expected_expr)
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


check_const_minus_const()
check_dynamic_minus_dynamic()
check_const_minus_dynamic()
check_dynamic_minus_const()
