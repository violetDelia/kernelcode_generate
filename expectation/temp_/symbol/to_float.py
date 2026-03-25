"""symbol.to_float expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用函数 + `build_func_op` 组织 `symbol.to_float` 的目标态 expectation。
- 验证静态整数与动态符号输入都可以成功 lowering 为 `symbol.to_float`。

使用示例:
- python expectation/temp/symbol/to_float.py

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

from xdsl.dialects.builtin import f32
from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.compare import assert_dynamic_symbol_int, assert_static_symbol_int
from expectation.utils.random import get_random_alpha_string, get_random_int
from kernel_gen.dialect.symbol import SymbolToFloatOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

VALUE = get_random_int()
SYMBOL_NAME = get_random_alpha_string().upper()
SYMBOL_VALUE = SymbolDim(SYMBOL_NAME)


def to_float_func(value: int) -> float:
    return float(value)


def check_case(input_value: int | SymbolDim) -> None:
    func_op = build_func_op(to_float_func, input_value)
    assert isinstance(func_op, FuncOp)

    if isinstance(input_value, SymbolDim):
        assert_dynamic_symbol_int(func_op.args[0].type, input_value)
    else:
        assert_static_symbol_int(func_op.args[0].type, input_value)

    cast_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolToFloatOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

    assert len(cast_ops) == 1
    assert cast_ops[0].result.type == f32
    assert len(return_ops) == 1
    assert return_ops[0].arguments[0].type == f32


check_case(VALUE)
check_case(SYMBOL_VALUE)
