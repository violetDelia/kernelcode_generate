"""DSL add-scalar expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `build_func_op` 可以将两个整型标量参数的加法函数转换为 `FuncOp`。
- 验证整型运行时参数会被转换为 `SymbolValueType`。
- 验证函数体内只生成一个 `SymbolAddOp` 和一个 `ReturnOp`。
- 验证 `ReturnOp` 返回值类型与 `expected` 一致。

使用示例:
- python expectation/dsl/mlir_gen/add_scalar.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

import random
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp, ReturnOp

from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolValueType
from expectation.utils.random import get_random_alpha_string
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.memory import Memory,NumericType

lhs = random.randint(-1024, 1024)
rhs = random.randint(-1024, 1024)
s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
s1_d = SymbolDim(s1)
s2_d = SymbolDim(s2)
s1_s2_int = Memory([s1, s2], NumericType.Int32)
s1_s2_float = Memory([s1, s2], NumericType.Float32)


def add(a, b):
    result = a + b
    return result


def assert_static_symbol_int(value_type, expected_value):
    assert isinstance(value_type, SymbolValueType)
    assert value_type.is_symbol() == False
    assert value_type.get_value() == expected_value
    assert str(value_type) == "symbol.int<\"{}\">".format(str(expected_value))

def assert_symbol_int(value_type, expected_value):
    assert isinstance(value_type, SymbolValueType)
    assert value_type.is_symbol() == True
    print(value_type.get_value())
    print(expected_value.get_value())
    assert value_type.get_value() == expected_value.get_value()
    assert str(value_type) == "symbol.int<\"{}\">".format(str(expected_value))

expected = add(lhs, rhs)
excepted_symbol = add(s1_d, s2_d)
print(excepted_symbol)

func_op = build_func_op(add, lhs, rhs)
assert isinstance(func_op, FuncOp)
print(func_op)

arg0 = func_op.args[0].type
assert_static_symbol_int(arg0, lhs)

arg1 = func_op.args[1].type
assert_static_symbol_int(arg1, rhs)

add_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolAddOp)]
assert len(add_ops) == 1

out_type = add_ops[0].result.type
assert_static_symbol_int(out_type, expected)

return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
assert len(return_ops) == 1

return_value_type = return_ops[0].arguments[0].type
assert_static_symbol_int(return_value_type, expected)

func_op = build_func_op(add, s1_d, s2_d)
print(func_op)
return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
assert len(return_ops) == 1

return_value_type = return_ops[0].arguments[0].type
assert_symbol_int(return_value_type, excepted_symbol)


