"""DSL symbol.add expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `build_func_op` 可以将 Python `add(a, b)` 函数转换为 `FuncOp`。
- 验证静态整数 runtime args 会被转换为携带具体值的 `SymbolValueType`。
- 验证动态符号参数和符号混合常量参数会被转换为对应的符号整数类型。
- 验证函数体内生成一个 `SymbolAddOp` 和一个 `ReturnOp`。
- 验证 `SymbolAddOp` 结果类型与 `ReturnOp` 返回值类型都与期望值一致。

使用示例:
- python expectation/dsl/mlir_gen/dialect/symbol/add.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

import random
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.compare import assert_dynamic_symbol_int, assert_static_symbol_int
from expectation.utils.random import get_random_alpha_string
from kernel_gen.dialect.symbol import SymbolAddOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

lhs = random.randint(-1024, 1024)
rhs = random.randint(-1024, 1024)
dim_m = get_random_alpha_string()
dim_n = get_random_alpha_string()
symbol_lhs = SymbolDim(dim_m)
symbol_rhs = SymbolDim(dim_n)


def add_func(a, b):
    c = a + b
    return c


def add_func2(a, b):
    return a + b


def check_const_plus_const(func):
    """验证 c + c 会生成静态 symbol.int 返回值。"""
    expected_expr = lhs + rhs

    func_op = build_func_op(func, lhs, rhs)
    assert isinstance(func_op, FuncOp)

    assert_static_symbol_int(func_op.args[0].type, lhs)
    assert_static_symbol_int(func_op.args[1].type, rhs)

    add_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolAddOp)]
    assert len(add_ops) == 1
    assert_static_symbol_int(add_ops[0].result.type, expected_expr)

    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert_static_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_dynamic_plus_dynamic(func):
    """验证 d + d 会生成动态符号表达式返回值。"""
    expected_expr = symbol_lhs + symbol_rhs

    func_op = build_func_op(func, symbol_lhs, symbol_rhs)
    assert isinstance(func_op, FuncOp)

    assert_dynamic_symbol_int(func_op.args[0].type, symbol_lhs)
    assert_dynamic_symbol_int(func_op.args[1].type, symbol_rhs)

    add_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolAddOp)]
    assert len(add_ops) == 1
    assert_dynamic_symbol_int(add_ops[0].result.type, expected_expr)

    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_const_plus_dynamic(func):
    """验证 c + d 会按操作数顺序生成动态符号表达式返回值。"""
    expected_expr = SymbolDim(lhs) + symbol_rhs

    func_op = build_func_op(func, lhs, symbol_rhs)
    assert isinstance(func_op, FuncOp)

    assert_static_symbol_int(func_op.args[0].type, lhs)
    assert_dynamic_symbol_int(func_op.args[1].type, symbol_rhs)

    add_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolAddOp)]
    assert len(add_ops) == 1
    assert_dynamic_symbol_int(add_ops[0].result.type, expected_expr)

    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


def check_dynamic_plus_const(func):
    """验证 d + c 会按操作数顺序生成动态符号表达式返回值。"""
    expected_expr = symbol_lhs + SymbolDim(rhs)

    func_op = build_func_op(func, symbol_lhs, rhs)
    assert isinstance(func_op, FuncOp)

    assert_dynamic_symbol_int(func_op.args[0].type, symbol_lhs)
    assert_static_symbol_int(func_op.args[1].type, rhs)

    add_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolAddOp)]
    assert len(add_ops) == 1
    assert_dynamic_symbol_int(add_ops[0].result.type, expected_expr)

    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert_dynamic_symbol_int(return_ops[0].arguments[0].type, expected_expr)


for target_func in (add_func, add_func2):
    check_const_plus_const(target_func)
    check_dynamic_plus_dynamic(target_func)
    check_const_plus_dynamic(target_func)
    check_dynamic_plus_const(target_func)
