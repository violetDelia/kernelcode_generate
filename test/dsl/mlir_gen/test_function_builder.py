"""mlir_gen function builder tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 build_func_op/build_func_op_from_ast 的运行时参数与基础装配行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen.function_builder --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_function_builder.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_function_builder.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/function_builder.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_function_builder.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dsl.ast import parse_function
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _tensor_arg(shape: list[int]) -> Memory:
    """构造 Memory 测试入参。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 简化 build_func_op_from_ast 的 runtime_args 构造。

    使用示例:
    - arg = _tensor_arg([2, 2])

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return Memory(shape, NumericType.Float32)


# TC-MLIR-GEN-FUNC-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 运行时参数缺失时必须报错。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/function_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_function_builder.py -k test_build_func_op_requires_runtime_args
def test_build_func_op_requires_runtime_args() -> None:
    def kernel(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    with pytest.raises(AstVisitorError) as excinfo:
        build_func_op(kernel, globals={"X": 1})
    assert "globals/builtins cannot replace function runtime args" in str(excinfo.value)


# TC-MLIR-GEN-FUNC-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: build_func_op_from_ast 可生成 func.FuncOp。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/function_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_function_builder.py -k test_build_func_op_from_ast_builds_func
def test_build_func_op_from_ast_builds_func() -> None:
    def identity(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    func_ast = parse_function(identity)
    func_op = build_func_op_from_ast(func_ast, runtime_args=[_tensor_arg([2, 2])])
    assert isinstance(func_op, func.FuncOp)
    assert func_op.sym_name.data == "identity"
