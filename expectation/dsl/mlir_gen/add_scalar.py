"""DSL add-memory expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `build_func_op` 可以将两个 `Memory` 参数的加法函数转换为 `FuncOp`。
- 验证 `Memory + Memory` 路径会生成一个 `NnAddOp`。
- 验证 `NnAddOp` 结果类型与 `ReturnOp` 返回类型都与期望值一致。

使用示例:
- python expectation/dsl/mlir_gen/add_scalar.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.random import get_random_alpha_string
from kernel_gen.dialect.nn import NnAddOp, NnMemoryType
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.nn import add as nn_add
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

shape_dim_m = get_random_alpha_string()
shape_dim_n = get_random_alpha_string()
lhs_memory = Memory([shape_dim_m, shape_dim_n], NumericType.Float32)
rhs_memory = Memory([shape_dim_m, shape_dim_n], NumericType.Float32)


def add_expr(lhs, rhs):
    return lhs + rhs


def add_assign(lhs, rhs):
    result = lhs + rhs
    return result


def assert_memory_type(value_type: NnMemoryType, expected_memory: Memory):
    assert isinstance(value_type, NnMemoryType)
    assert expected_memory.get_shape() == value_type.get_shape()
    assert expected_memory.get_type() == value_type.get_dtype()
    assert expected_memory.get_space() == value_type.get_space()
    assert expected_memory.get_stride() == value_type.get_stride()


def check_memory_plus_memory(func):
    """验证 Memory + Memory 会生成 nn.add，并保持类型信息。"""
    expected_memory = nn_add(lhs_memory, rhs_memory)

    func_op = build_func_op(func, lhs_memory, rhs_memory)
    assert isinstance(func_op, FuncOp)

    lhs_arg_type = func_op.args[0].type
    assert_memory_type(lhs_arg_type, lhs_memory)

    rhs_arg_type = func_op.args[1].type
    assert_memory_type(rhs_arg_type, rhs_memory)

    add_ops = [op for op in func_op.body.block.ops if isinstance(op, NnAddOp)]
    assert len(add_ops) == 1

    result_type = add_ops[0].result.type
    assert_memory_type(result_type, expected_memory)

    return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(return_ops) == 1
    assert len(return_ops[0].arguments) == 1
    assert_memory_type(return_ops[0].arguments[0].type, expected_memory)


for target_func in (add_expr, add_assign):
    check_memory_plus_memory(target_func)
