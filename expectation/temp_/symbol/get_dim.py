"""symbol.get_dim expectation.

创建者: 榕
最后一次更改: 金铲铲大作战

功能说明:
- 使用函数 + `build_func_op` 组织 `symbol.get_dim` 的目标态 expectation。
- 验证从静态 shape 和符号 shape 中读取维度都可以成功 lowering 为 `symbol.get_dim`。

使用示例:
- python expectation/temp_/symbol/get_dim.py

关联文件:
- spec: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/ast.py, kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.compare import assert_dynamic_symbol_int, assert_static_symbol_int
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int
from kernel_gen.dialect.symbol import SymbolGetDimOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

STATIC_DIM0 = get_random_non_zero_int(2, 8)
STATIC_DIM1 = get_random_non_zero_int(2, 8)
STATIC_MEMORY = Memory([STATIC_DIM0, STATIC_DIM1], NumericType.Float32)

SYMBOL_DIM0_NAME = get_random_alpha_string().upper()
SYMBOL_DIM1_NAME = get_random_alpha_string().upper()
while SYMBOL_DIM1_NAME == SYMBOL_DIM0_NAME:
    SYMBOL_DIM1_NAME = get_random_alpha_string().upper()
SYMBOL_DIM0 = SymbolDim(SYMBOL_DIM0_NAME)
SYMBOL_DIM1 = SymbolDim(SYMBOL_DIM1_NAME)
DYNAMIC_MEMORY = Memory([SYMBOL_DIM0, SYMBOL_DIM1], NumericType.Float32)


def get_dim_static(value: f"Tensor[f32, {STATIC_DIM0}, {STATIC_DIM1}]") -> int:
    return value.get_shape()[1]


def get_dim_dynamic(value: f"Tensor[f32, {SYMBOL_DIM0_NAME}, {SYMBOL_DIM1_NAME}]") -> int:
    return value.get_shape()[1]


def check_static_case() -> None:
    func_op = build_func_op(get_dim_static, STATIC_MEMORY)
    assert isinstance(func_op, FuncOp)

    dim_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolGetDimOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

    assert len(dim_ops) == 1
    assert_static_symbol_int(dim_ops[0].result.type, STATIC_DIM1)
    assert len(return_ops) == 1
    assert_static_symbol_int(return_ops[0].arguments[0].type, STATIC_DIM1)


def check_dynamic_case() -> None:
    func_op = build_func_op(get_dim_dynamic, DYNAMIC_MEMORY)
    assert isinstance(func_op, FuncOp)

    dim_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolGetDimOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

    assert len(dim_ops) == 1
    assert_dynamic_symbol_int(dim_ops[0].result.type, SYMBOL_DIM1)
    assert len(return_ops) == 1
    assert_dynamic_symbol_int(return_ops[0].arguments[0].type, SYMBOL_DIM1)


check_static_case()
check_dynamic_case()
