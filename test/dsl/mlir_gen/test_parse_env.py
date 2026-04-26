"""mlir_gen public parse environment tests.

创建者: 朽木露琪亚
最后一次更改: 金铲铲大作战

功能说明:
- 仅通过公开 parser / mlir_gen 入口验证解析环境相关行为。
- 不直接调用 parse_env 私有 helper。

使用示例:
- pytest -q test/dsl/mlir_gen/test_parse_env.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/__init__.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_parse_env.py
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import AstParseError, TensorAST
from kernel_gen.dsl.ast.parser import parse_function_with_env
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _fake_source(monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    def fake_getsource(_obj: object) -> str:
        return source

    monkeypatch.setattr(inspect, "getsource", fake_getsource)


# TC-MLIR-GEN-PARSE-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 公开 parser 入口允许通过 runtime_table 推断缺失注解。
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast/parser.md, spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_parse_function_with_env_infers_runtime_annotation
def test_parse_function_with_env_infers_runtime_annotation() -> None:
    memory = Memory([SymbolDim("M")], NumericType.Float32)

    def env_kernel(x):
        return x

    func_ast = parse_function_with_env(
        env_kernel,
        globals_table=dict(getattr(env_kernel, "__globals__", {})),
        builtins_table=(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__),
        runtime_table={"x": memory},
        config=None,
    )

    assert isinstance(func_ast.inputs[0], TensorAST)
    assert func_ast.inputs[0].memory == memory


# TC-MLIR-GEN-PARSE-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 公开 build_func_op 入口必须显式传入 runtime_args，不允许函数环境替代。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_build_func_op_requires_explicit_runtime_args_even_with_globals
def test_build_func_op_requires_explicit_runtime_args_even_with_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shadow_expr = SymbolDim("shadow")

    def only_symbol(expr: int) -> int:
        return expr

    monkeypatch.setitem(only_symbol.__globals__, "expr", shadow_expr)
    monkeypatch.setitem(only_symbol.__globals__, "__builtins__", __builtins__)

    with pytest.raises(AstVisitorError, match="requires explicit runtime args") as exc_info:
        build_func_op(only_symbol)

    assert "expected 1, got 0" in str(exc_info.value)


# TC-MLIR-GEN-PARSE-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 公开 build_func_op 入口的符号签名以 runtime_args 为准，不受同名 globals 影响。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_build_func_op_signature_uses_runtime_args_not_shadow_globals
def test_build_func_op_signature_uses_runtime_args_not_shadow_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_expr = SymbolDim("runtime")
    shadow_expr = SymbolDim("shadow")

    def only_symbol(expr: int) -> int:
        return expr

    monkeypatch.setitem(only_symbol.__globals__, "expr", shadow_expr)
    monkeypatch.setitem(only_symbol.__globals__, "__builtins__", object())

    func_op = build_func_op(only_symbol, runtime_expr)
    inputs = list(func_op.function_type.inputs)
    outputs = list(func_op.function_type.outputs)
    assert inputs == [SymbolValueType.from_expr("runtime")]
    assert outputs == [SymbolValueType.from_expr("runtime")]


# TC-MLIR-GEN-PARSE-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 公开 parser 入口对解析失败保持 AstParseError 口径。
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast/parser.md
# 示例: pytest -q test/dsl/mlir_gen/test_parse_env.py -k test_parse_function_with_env_reports_public_parse_error
def test_parse_function_with_env_reports_public_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = """\
def broken(x):
    return x
"""

    def kernel(*_args: object, **_kwargs: object) -> object:
        return None

    _fake_source(monkeypatch, source)

    with pytest.raises(AstParseError):
        parse_function_with_env(
            kernel,
            globals_table=dict(getattr(kernel, "__globals__", {})),
            builtins_table=(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__),
            runtime_table=None,
            config=None,
        )
