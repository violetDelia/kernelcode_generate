"""mlir_gen parse environment public contract tests.

创建者: 朽木露琪亚
最后一次更改: 小李飞刀

功能说明:
- 通过 `build_func_op(...)` 公开入口覆盖解析环境对 runtime_args/globals/builtins 的可观察行为。
- 不直连 `parse_env.py` 内部 helper，也不 monkeypatch 私有入口。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_parse_env.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_parse_env.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/__init__.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_parse_env.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


# TC-MLIR-GEN-PARSE-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 runtime_args 仍是公开签名真源，globals/builtins 不能覆盖同名 runtime 输入。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_build_func_op_uses_runtime_args_over_shadowed_parse_env_names
def test_build_func_op_uses_runtime_args_over_shadowed_parse_env_names() -> None:
    runtime_expr = SymbolDim("runtime")
    shadow_expr = SymbolDim("shadow")

    def only_symbol(runtime: int) -> int:
        return runtime

    func_op = build_func_op(
        only_symbol,
        runtime_expr,
        globals={"runtime": shadow_expr, "__builtins__": __builtins__},
        builtins=object(),
    )
    assert list(func_op.function_type.inputs) == [SymbolValueType.from_expr("runtime")]
    assert list(func_op.function_type.outputs) == [SymbolValueType.from_expr("runtime")]


# TC-MLIR-GEN-PARSE-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 globals/builtins 只参与解析环境，不能代替公开 runtime_args。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_build_func_op_globals_and_builtins_cannot_replace_runtime_args
def test_build_func_op_globals_and_builtins_cannot_replace_runtime_args() -> None:
    expr = SymbolDim("expr")

    def only_symbol(expr: int) -> int:
        return expr

    with pytest.raises(AstVisitorError, match="globals/builtins cannot replace function runtime args"):
        build_func_op(only_symbol, globals={"expr": expr}, builtins=__builtins__)


# TC-MLIR-GEN-PARSE-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 builtins 补充表中的外部值不会被当作函数体局部输入。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_build_func_op_rejects_builtins_external_value_reference
def test_build_func_op_rejects_builtins_external_value_reference() -> None:
    def use_builtin_value() -> int:
        return BUILTIN_EXTERNAL_VALUE

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body"):
        build_func_op(use_builtin_value, builtins={"BUILTIN_EXTERNAL_VALUE": 13})
