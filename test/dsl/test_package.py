"""dsl package public api tests.


功能说明:
- 只通过公开包入口验证 `kernel_gen.dsl`、`kernel_gen.dsl.ast.mlir_gen` 与 `kernel_gen.dsl.gen_kernel` 的导出边界。
- 不直连跨文件非公开 helper，作为 repo_conformance S2 的公开 API 证据链。

使用示例:
- pytest -q test/dsl/test_package.py

关联文件:
- 功能实现: kernel_gen/dsl/__init__.py
- 功能实现: kernel_gen/dsl/ast/mlir_gen.py
- 功能实现: kernel_gen/dsl/gen_kernel/__init__.py
- Spec 文档: spec/dsl/ast/mlir_gen.md
- Spec 文档: spec/dsl/gen_kernel/gen_kernel.md
- 测试文件: test/dsl/test_package.py
"""

from __future__ import annotations

import importlib

import pytest
from kernel_gen.core.error import KernelCodeError


def test_dsl_package_public_exports() -> None:
    """TC-DSL-PKG-001: `kernel_gen.dsl` should expose the documented public symbols."""

    dsl_package = importlib.import_module("kernel_gen.dsl")
    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl import *", namespace)
    public_names = sorted(name for name in namespace if not name.startswith("__"))

    assert public_names == sorted(
        [
            "parse_function",
        ]
    )
    assert callable(namespace["parse_function"])
    assert not hasattr(dsl_package, "BinaryExprAST")
    assert not hasattr(dsl_package, "BlockAST")
    assert not hasattr(dsl_package, "CompareExprAST")
    assert not hasattr(dsl_package, "ConstAST")
    assert not hasattr(dsl_package, "Diagnostic")
    assert not hasattr(dsl_package, "FunctionAST")
    assert not hasattr(dsl_package, "ModuleAST")
    assert not hasattr(dsl_package, "ScalarArgAST")
    assert not hasattr(dsl_package, "SourceLocation")
    assert not hasattr(dsl_package, "TensorAST")
    assert not hasattr(dsl_package, "VarAST")
    assert not hasattr(dsl_package, "AstVisitor")
    assert not hasattr(dsl_package, "EmitContext")
    assert not hasattr(dsl_package, "emit_mlir")
    assert not hasattr(dsl_package, "build_func_op")
    assert not hasattr(dsl_package, "build_func_op_from_ast")


def test_gen_kernel_package_public_exports_and_legacy_rejection() -> None:
    """TC-DSL-PKG-002: `kernel_gen.dsl.gen_kernel` should expose the documented package-root entries."""

    gen_kernel_package = importlib.import_module("kernel_gen.dsl.gen_kernel")
    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl.gen_kernel import *", namespace)
    public_names = sorted(name for name in namespace if not name.startswith("__"))

    assert public_names == [
        "EmitCContext",
        "KernelEmitter",
        "dsl_gen_kernel",
        "emit_c",
        "emit_c_op",
        "emit_c_value",
        "gen_kernel",
    ]
    assert "gen_signature" not in public_names
    assert "gen_body" not in public_names
    assert namespace["EmitCContext"] is gen_kernel_package.EmitCContext
    assert namespace["KernelEmitter"] is gen_kernel_package.KernelEmitter
    assert callable(namespace["gen_kernel"])
    assert callable(namespace["dsl_gen_kernel"])
    assert callable(namespace["emit_c"])
    assert callable(namespace["emit_c_op"])
    assert callable(namespace["emit_c_value"])

    with pytest.raises(AttributeError):
        getattr(gen_kernel_package, "gen_signature")
    with pytest.raises(AttributeError):
        getattr(gen_kernel_package, "gen_body")


def test_mlir_gen_package_public_exports() -> None:
    """TC-DSL-PKG-003: `kernel_gen.dsl.ast.mlir_gen` should keep only documented public entries."""

    mlir_gen_package = importlib.import_module("kernel_gen.dsl.ast.mlir_gen")
    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl.ast.mlir_gen import *", namespace)
    public_names = sorted(name for name in namespace if not name.startswith("__"))

    assert public_names == [
        "mlir_gen",
    ]
    assert callable(namespace["mlir_gen"])

    for private_name in (
        "build_func_op",
        "build_func_op_from_ast",
        "EmitCContext",
        "emit_c",
        "emit_c_op",
        "emit_c_value",
        "gen_kernel",
    ):
        with pytest.raises(AttributeError):
            getattr(mlir_gen_package, private_name)


def test_removed_legacy_dsl_facades_reject_import() -> None:
    """TC-DSL-PKG-005: deleted legacy facade modules and private submodules should not remain importable."""

    for module_name in (
        "kernel_gen.dsl.mlir_gen",
        "kernel_gen.dsl.mlir_gen.emit",
        "kernel_gen.dsl.mlir_gen.emit.core",
        "kernel_gen.dsl.emit_mlir",
        "kernel_gen.dsl.ast.visitor",
        "kernel_gen.dsl.ast.emit_context",
        "kernel_gen.dsl.ast.emit_nn",
        "kernel_gen.dsl.ast.mlir_context",
    ):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)
