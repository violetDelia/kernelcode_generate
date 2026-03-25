"""symbol.eq expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用函数 + `build_func_op` 组织 `symbol.eq` 的目标态 expectation。
- 验证静态整数、动态符号以及混合输入都可以成功 lowering 为 `symbol.eq`。

使用示例:
- python expectation/temp/symbol/eq.py

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/test_symbol_dialect.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
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


def eq_func(lhs: int, rhs: int) -> bool:
    return lhs == rhs


def check_case(lhs_value: int | SymbolDim, rhs_value: int | SymbolDim) -> None:
    func_op = build_func_op(eq_func, lhs_value, rhs_value)
    assert isinstance(func_op, FuncOp)

    if isinstance(lhs_value, SymbolDim):
        assert_dynamic_symbol_int(func_op.args[0].type, lhs_value)
    else:
        assert_static_symbol_int(func_op.args[0].type, lhs_value)

    if isinstance(rhs_value, SymbolDim):
        assert_dynamic_symbol_int(func_op.args[1].type, rhs_value)
    else:
        assert_static_symbol_int(func_op.args[1].type, rhs_value)

    eq_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolEqOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

    assert len(eq_ops) == 1
    assert eq_ops[0].result.type == i1
    assert len(return_ops) == 1
    assert return_ops[0].arguments[0].type == i1


check_case(LHS, RHS)
check_case(SYMBOL_LHS, SYMBOL_RHS)
check_case(LHS, SYMBOL_RHS)
check_case(SYMBOL_LHS, RHS)
