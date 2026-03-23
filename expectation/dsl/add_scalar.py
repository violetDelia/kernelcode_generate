"""DSL add-scalar expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `build_func_op` 可以将两个整型标量参数的加法函数转换为 `FuncOp`。
- 验证整型运行时参数会 lowering 为 `SymbolValueType`，并在函数体内生成 `SymbolAddOp`。

使用示例:
- python expectation/dsl/add_scalar.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp

from kernel_gen.dialect.symbol import SymbolAddOp, SymbolValueType
from kernel_gen.dsl.mlir_gen import build_func_op
import random

lhs = random.randint(-1024, 1024)
rhs = random.randint(-1024, 1024)


def add(a, b):
    result = a + b
    return result


expected = add(lhs, rhs)

func_op = build_func_op(add, lhs, rhs)
assert isinstance(func_op, FuncOp)
print(func_op)

arg0 = func_op.args[0].type
assert isinstance(arg0, SymbolValueType)
assert not arg0.is_symbol()
assert arg0.get_value() == lhs
assert arg0.__str__() == "symbol.int<{}>".format(str(lhs))

arg1 = func_op.args[1].type
assert isinstance(arg1, SymbolValueType)
assert not arg1.is_symbol()
assert arg1.get_value() == rhs
assert arg1.__str__() == "symbol.int<{}>".format(str(rhs))

add_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolAddOp)]
assert len(add_ops) == 2

out_type = add_ops[0].result.type

assert isinstance(out_type, SymbolValueType)
assert not out_type.is_symbol()
assert out_type.get_value() == expected
assert out_type.__str__() == "symbol.int<{}>".format(str(expected))

