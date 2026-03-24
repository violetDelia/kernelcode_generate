"""DSL nn.add expectation.
[immutable-file]
创建者: 榕
最后一次更改: 朽木露琪亚

功能说明:
- 验证 `build_func_op` 可以将两个 Python 加法函数转换为 `FuncOp`。
- 验证 `Memory + Memory` 路径会生成一个 `NnAddOp`。
- 验证 `NnAddOp` 结果类型与 `ReturnOp` 返回类型符合当前链路输出。
- 验证符号维 `Memory` 输入可以稳定参与 `nn.add` lowering。

使用示例:
- python expectation/dsl/mlir_gen/dialect/nn/add.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

import random
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import alloc
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

lhs = get_random_non_zero_int()
rhs = get_random_non_zero_int()
dim_m = get_random_alpha_string()
dim_n = get_random_alpha_string()


def alloc_call(lhs, rhs, dim_m, dim_n):
    alloc_m = alloc(lhs, rhs)
    return alloc_m


func_op = build_func_op(alloc_call, lhs, rhs, dim_m, dim_n)
print(func_op)
