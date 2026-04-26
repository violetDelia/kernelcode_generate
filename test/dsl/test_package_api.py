"""dsl package public api tests.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 只通过公开包入口验证 `kernel_gen.dsl` 与 `kernel_gen.dsl.gen_kernel` 的导出边界。
- 不直连跨文件非公开 helper，作为 repo_conformance S2 的公开 API 证据链。

使用示例:
- pytest -q test/dsl/test_package_api.py

关联文件:
- 功能实现: kernel_gen/dsl/__init__.py
- 功能实现: kernel_gen/dsl/gen_kernel/__init__.py
- Spec 文档: spec/dsl/mlir_gen.md
- Spec 文档: spec/dsl/gen_kernel/gen_kernel.md
- 测试文件: test/dsl/test_package_api.py
"""

from __future__ import annotations

import importlib

import pytest


def test_dsl_package_public_exports() -> None:
    """TC-DSL-PKG-001: `kernel_gen.dsl` should expose the documented public symbols."""

    dsl_package = importlib.import_module("kernel_gen.dsl")
    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl import *", namespace)
    public_names = sorted(name for name in namespace if not name.startswith("__"))

    assert public_names == sorted(
        [
            "AstVisitor",
            "AstVisitorError",
            "BinaryExprAST",
            "BlockAST",
            "CompareExprAST",
            "ConstAST",
            "Diagnostic",
            "EmitContext",
            "FunctionAST",
            "ModuleAST",
            "ScalarArgAST",
            "SourceLocation",
            "TensorAST",
            "VarAST",
            "build_func_op",
            "build_func_op_from_ast",
            "emit_mlir",
            "parse_function",
        ]
    )
    assert namespace["AstVisitor"] is dsl_package.AstVisitor
    assert namespace["EmitContext"] is dsl_package.EmitContext
    assert callable(namespace["parse_function"])
    assert callable(namespace["emit_mlir"])
    assert callable(namespace["build_func_op"])
    assert callable(namespace["build_func_op_from_ast"])


def test_gen_kernel_package_public_exports_and_legacy_rejection() -> None:
    """TC-DSL-PKG-002: `kernel_gen.dsl.gen_kernel` should keep only canonical public entries."""

    gen_kernel_package = importlib.import_module("kernel_gen.dsl.gen_kernel")
    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl.gen_kernel import *", namespace)
    public_names = sorted(name for name in namespace if not name.startswith("__"))

    assert public_names == [
        "EmitCContext",
        "EmitCError",
        "GenKernelError",
        "KernelEmitter",
        "dsl_gen_kernel",
        "emit_c",
        "emit_c_op",
        "emit_c_value",
        "gen_kernel",
    ]
    assert "gen_signature" not in public_names
    assert "gen_body" not in public_names
    assert namespace["GenKernelError"] is gen_kernel_package.GenKernelError
    assert namespace["EmitCContext"] is gen_kernel_package.EmitCContext
    assert namespace["KernelEmitter"] is gen_kernel_package.KernelEmitter
    assert callable(namespace["dsl_gen_kernel"])
    assert callable(namespace["gen_kernel"])
    assert callable(namespace["emit_c"])
    assert callable(namespace["emit_c_op"])
    assert callable(namespace["emit_c_value"])

    with pytest.raises(AttributeError):
        getattr(gen_kernel_package, "gen_signature")
    with pytest.raises(AttributeError):
        getattr(gen_kernel_package, "gen_body")
