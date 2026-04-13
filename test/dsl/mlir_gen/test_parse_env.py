"""mlir_gen parse_env tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖解析环境构造与 parse 失败转译行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen.parse_env --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_parse_env.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_parse_env.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/parse_env.py
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

from kernel_gen.dsl import mlir_gen as mlir_gen_module
from kernel_gen.dsl.ast import AstParseError, _ParseFailure
from kernel_gen.dsl.mlir_gen import _build_parse_environment, _build_runtime_table_for_signature, _parse_function_with_env


# TC-MLIR-GEN-PARSE-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 globals/builtins 合并规则。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/parse_env.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_build_parse_environment_merges_globals
def test_build_parse_environment_merges_globals() -> None:
    def kernel(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    globals_table, builtins_table = _build_parse_environment(kernel, globals_table={"X": 1}, builtins_table={})
    assert globals_table["X"] == 1
    assert isinstance(builtins_table, dict)


# TC-MLIR-GEN-PARSE-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 runtime_args 数量匹配时返回 runtime_table。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/parse_env.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_build_runtime_table_for_signature
def test_build_runtime_table_for_signature() -> None:
    def kernel(x: "Tensor[f32, 4]", y: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    assert _build_runtime_table_for_signature(kernel, runtime_args=[]) is None
    table = _build_runtime_table_for_signature(kernel, runtime_args=[1, 2])
    assert table == {"x": 1, "y": 2}


# TC-MLIR-GEN-PARSE-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 _ParseFailure 会转译为 AstParseError。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/parse_env.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_parse_function_with_env_wraps_failure
def test_parse_function_with_env_wraps_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def kernel() -> None:
        return None

    def _broken_parse(*_args: object, **_kwargs: object) -> object:
        raise _ParseFailure("boom", location=None)

    monkeypatch.setattr(mlir_gen_module, "_parse_function_impl", _broken_parse)

    with pytest.raises(AstParseError) as excinfo:
        _parse_function_with_env(kernel, globals_table={}, builtins_table={}, runtime_table={}, config=None)
    assert "boom" in str(excinfo.value)
