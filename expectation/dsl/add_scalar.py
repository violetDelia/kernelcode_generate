"""DSL build_func_op expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `build_func_op` 可以将简单的逐元素加法函数转换为 `FuncOp`。

使用示例:
- python expectation/dsl/build_func_op.py

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

from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def add(a, b):
    result = a + b
    return result


func_op = build_func_op(add, 1, 2)
assert isinstance(func_op, FuncOp)
