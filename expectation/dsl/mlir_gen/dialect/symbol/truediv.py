"""DSL symbol.div expectation.

创建者: 榕
最后一次更改: 朽木露琪亚

功能说明:
- 验证 `build_func_op` 可以将 Python `truediv(a, b)` 函数转换为 `FuncOp`。
- 验证静态整除、动态符号与混合输入在 lowering 后保持 `symbol.int` 语义。
- 验证函数体内生成一个 `SymbolDivOp` 和一个 `ReturnOp`。

使用示例:
- python expectation/dsl/mlir_gen/dialect/symbol/truediv.py

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
from kernel_gen.dialect.symbol import SymbolDivOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

LHS = 6
RHS = 3
SYMBOL_LHS = SymbolDim("M")
SYMBOL_RHS = SymbolDim("N")


def truediv_func(a: int, b: int) -> int:
    c = a / b
    return c


def truediv_func2(a: int, b: int) -> int:
    return a / b


def check_const_div_const(func: Callable[[int, int], int]) -> None:
    expected_expr = SymbolDim(LHS) / SymbolDim(RHS)
    func_op = build_func_op(func, LHS, RHS)
    assert isinstance(func_op, FuncOp)
    assert_static_symbol_int(func_op.args[0].type, LHS)
    assert_static_symbol_int(func_op.args[1].type, RHS)
    div_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolDivOp)]
    assert len(div_ops) == 1
    assert_static_symbol_int(div_ops[0].result.type, expected_expr.get_value())
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert_static_symbol_int(return_ops[0].arguments[0].type, expected_expr.get_value())


def check_dynamic_div_dynamic(func: Callable[[int, int], int]) -> None:
    expected_expr = "M / N"
    func_op = build_func_op(func, SYMBOL_LHS, SYMBOL_RHS)
    assert isinstance(func_op, FuncOp)
    assert_dynamic_symbol_int(func_op.args[0].type, SYMBOL_LHS)
    assert_dynamic_symbol_int(func_op.args[1].type, SYMBOL_RHS)
    div_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolDivOp)]
    assert len(div_ops) == 1
    assert_dynamic_symbol_int(div_ops[0].result.type, expected_expr)
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_const_div_dynamic(func: Callable[[int, int], int]) -> None:
    expected_expr = "6 / N"
    func_op = build_func_op(func, LHS, SYMBOL_RHS)
    assert isinstance(func_op, FuncOp)
    assert_static_symbol_int(func_op.args[0].type, LHS)
    assert_dynamic_symbol_int(func_op.args[1].type, SYMBOL_RHS)
    div_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolDivOp)]
    assert len(div_ops) == 1
    assert_dynamic_symbol_int(div_ops[0].result.type, expected_expr)
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_dynamic_div_const(func: Callable[[int, int], int]) -> None:
    expected_expr = "M / 3"
    func_op = build_func_op(func, SYMBOL_LHS, RHS)
    assert isinstance(func_op, FuncOp)
    assert_dynamic_symbol_int(func_op.args[0].type, SYMBOL_LHS)
    assert_static_symbol_int(func_op.args[1].type, RHS)
    div_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolDivOp)]
    assert len(div_ops) == 1
    assert_dynamic_symbol_int(div_ops[0].result.type, expected_expr)
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


for target_func in (truediv_func, truediv_func2):
    check_const_div_const(target_func)
    check_dynamic_div_dynamic(target_func)
    check_const_div_dynamic(target_func)
    check_dynamic_div_const(target_func)
