"""DSL symbol.eq expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `build_func_op` 可以将 Python `eq(a, b)` 函数转换为 `FuncOp`。
- 验证静态整数 runtime args 会被转换为携带具体值的 `SymbolValueType`。
- 验证动态符号参数会被转换为对应的动态符号整数类型。
- 验证函数体内生成一个 `SymbolEqOp` 和一个 `ReturnOp`，且返回值类型为 `i1`。

使用示例:
- python expectation/dsl/mlir_gen/dialect/symbol/eq.py

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

from xdsl.dialects.builtin import i1
from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.compare import assert_dynamic_symbol_int, assert_static_symbol_int
from expectation.utils.random import get_random_alpha_string, get_random_int
from kernel_gen.dialect.symbol import SymbolEqOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

LHS = get_random_int()
RHS = get_random_int()
SYMBOL_LHS_NAME = get_random_alpha_string().upper()
SYMBOL_RHS_NAME = get_random_alpha_string().upper()
while SYMBOL_RHS_NAME == SYMBOL_LHS_NAME:
    SYMBOL_RHS_NAME = get_random_alpha_string().upper()
SYMBOL_LHS = SymbolDim(SYMBOL_LHS_NAME)
SYMBOL_RHS = SymbolDim(SYMBOL_RHS_NAME)


def eq_func(a: int, b: int) -> bool:
    c = a == b
    return c


def eq_func2(a: int, b: int) -> bool:
    return a == b


TARGET_FUNCS: tuple[Callable[[int, int], bool], ...] = (eq_func, eq_func2)


def check_const_eq_const() -> None:
    for target_func in TARGET_FUNCS:
        func_op = build_func_op(target_func, LHS, RHS)
        assert isinstance(func_op, FuncOp)
        assert_static_symbol_int(func_op.args[0].type, LHS)
        assert_static_symbol_int(func_op.args[1].type, RHS)
        eq_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolEqOp)]
        assert len(eq_ops) == 1
        assert eq_ops[0].result.type == i1
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert return_ops[0].arguments[0].type == i1


def check_dynamic_eq_dynamic() -> None:
    for target_func in TARGET_FUNCS:
        func_op = build_func_op(target_func, SYMBOL_LHS, SYMBOL_RHS)
        print(func_op)
        assert isinstance(func_op, FuncOp)
        assert_dynamic_symbol_int(func_op.args[0].type, SYMBOL_LHS)
        assert_dynamic_symbol_int(func_op.args[1].type, SYMBOL_RHS)
        eq_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolEqOp)]
        assert len(eq_ops) == 1
        assert eq_ops[0].result.type == i1
        return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
        assert len(return_ops) == 1
        assert return_ops[0].arguments[0].type == i1


check_const_eq_const()
check_dynamic_eq_dynamic()
