"""execute_engine contract tests (P0 skeleton).


功能说明:
- 验证 execute_engine 的目录骨架、公开接口命名与公共失败短语合同（P0）。
- 本阶段不要求真实编译/运行，仅验证输入校验与失败短语稳定匹配。

使用示例:
- pytest -q test/execute_engine/test_contract.py

当前覆盖率信息:
- `kernel_gen.execute_engine.compiler`：`85%`（Stmts=117 Miss=12 Branch=28 BrPart=8；最近一次统计：2026-04-07 10:25:00 +0800）。

覆盖率命令:
- `pytest -q --cov=kernel_gen.execute_engine.compiler --cov-branch --cov-report=term-missing test/execute_engine/test_contract.py`

关联文件:
- 功能实现: kernel_gen/execute_engine/compiler.py
- 功能实现: kernel_gen/execute_engine/strategy.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/__init__.py
- Spec 文档: spec/execute_engine/execute_engine.md
- Spec 文档: spec/execute_engine/execute_engine_api.md
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_contract.py
- 测试文件: test/execute_engine/test_builtin_strategy.py
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import itertools
import os
import subprocess
import sys
from pathlib import Path
from typing import get_type_hints

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
import kernel_gen.execute_engine as execute_engine
from kernel_gen.execute_engine import (
    ExecuteRequest,
    ExecutionEngine,
)


# EE-S1-000
# 测试目的: 确认 S1 约定的 spec/test 骨架文件存在。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_contract_files_exist() -> None:
    execute_engine_dir = REPO_ROOT / "kernel_gen/execute_engine"
    old_target_module = execute_engine_dir / ("target" + "_support.py")
    old_target_test = REPO_ROOT / "test/execute_engine" / ("test_" + "target" + "_support.py")
    assert (REPO_ROOT / "spec/execute_engine/execute_engine.md").is_file()
    assert (REPO_ROOT / "spec/execute_engine/execute_engine_api.md").is_file()
    assert (REPO_ROOT / "spec/execute_engine/execute_engine_target.md").is_file()
    assert (REPO_ROOT / "spec/execute_engine/strategy.md").is_file()
    assert (execute_engine_dir / "strategy.py").is_file()
    assert (execute_engine_dir / "builtin_strategy").is_dir()
    assert (execute_engine_dir / "builtin_strategy" / "__init__.py").is_file()
    assert (execute_engine_dir / "builtin_strategy" / "cpu.py").is_file()
    assert (execute_engine_dir / "builtin_strategy" / "npu_demo.py").is_file()
    assert (execute_engine_dir / "builtin_strategy" / "cuda_sm86.py").is_file()
    assert (execute_engine_dir / "runtime_args.py").is_file()
    assert not old_target_module.exists()
    assert (REPO_ROOT / "test/execute_engine/test_contract.py").is_file()
    assert (REPO_ROOT / "test/execute_engine/test_builtin_strategy.py").is_file()
    assert not old_target_test.exists()


# EE-S1-000A
# 测试目的: 锁定 execute_engine 包根公开 API 集合，避免旧 helper/常量重新外露。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_public_api_exports_only_runtime_contract() -> None:
    assert execute_engine.__all__ == [
        "CompileStrategy",
        "CompiledKernel",
        "CompileRequest",
        "ExecuteRequest",
        "ExecuteResult",
        "ExecutionEngine",
        "get_compile_strategy",
        "register_compile_strategy",
    ]
    hidden_helper_names = (
        "target" + "_includes",
        "default" + "_compiler",
        "build" + "_compile_unit",
        "build" + "_compile_command",
        "compile" + "_source",
        "needs" + "_entry_shim",
        "build" + "_entry_shim_source",
        "Target" + "Name",
    )
    for name in (
        "RuntimeArg",
        "KgArgSlot",
        "CompileArtifacts",
        "FAILURE_PHRASES",
        "Builtin" + "TargetSupportArtifacts",
        "build" + "_builtin_" + "target" + "_support_artifacts",
        "install_builtin_compile" + "_strategies",
        "BuiltinCompileArtifacts",
        "build_builtin_compile_artifacts",
        "RuntimeScalarArgInfo",
        "RuntimeMemoryArgInfo",
        "RuntimeArgInfo",
        "describe_runtime_arg",
        "AllowAbsentMemoryArg",
        "RuntimeInput",
        "invoke_compiled_kernel",
        *hidden_helper_names,
    ):
        assert not hasattr(execute_engine, name)
    assert not any(name.startswith("FAILURE_") for name in dir(execute_engine))


# EE-S1-000B
# 测试目的: 锁定 strategy registry 的新真源与旧公开导入路径保持同一对象。
# 对应功能实现文件路径: kernel_gen/execute_engine/strategy.py
# 对应 spec 文件路径: spec/execute_engine/strategy.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_strategy_registry_reexport_identity() -> None:
    compiler_module = importlib.import_module("kernel_gen.execute_engine.compiler")
    strategy_module = importlib.import_module("kernel_gen.execute_engine.strategy")
    assert execute_engine.CompileStrategy is strategy_module.CompileStrategy
    assert execute_engine.register_compile_strategy is strategy_module.register_compile_strategy
    assert execute_engine.get_compile_strategy is strategy_module.get_compile_strategy
    assert compiler_module.CompileStrategy is strategy_module.CompileStrategy
    assert compiler_module.register_compile_strategy is strategy_module.register_compile_strategy
    assert compiler_module.get_compile_strategy is strategy_module.get_compile_strategy


# EE-S1-000C
# 测试目的: 验证内置 strategy 安装模块不进入包根公开 API，且安装调用只存在于 compiler.py。
# 对应功能实现文件路径: kernel_gen/execute_engine/builtin_strategy/__init__.py
# 对应 spec 文件路径: spec/execute_engine/strategy.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_builtin_strategy_static_install_boundary() -> None:
    install_name = "install_builtin_compile" + "_strategies"
    install_alias_name = "_" + install_name
    builtin_path = REPO_ROOT / "kernel_gen/execute_engine/builtin_strategy" / "__init__.py"
    compiler_path = REPO_ROOT / "kernel_gen/execute_engine/compiler.py"
    builtin_source = builtin_path.read_text(encoding="utf-8")
    builtin_tree = ast.parse(builtin_source)
    assert "kernel_gen.execute_engine.compiler" not in builtin_source
    assert install_name not in execute_engine.__all__
    assert not hasattr(execute_engine, install_name)
    assert not hasattr(execute_engine, "BuiltinCompileArtifacts")
    assert not hasattr(execute_engine, "build_builtin_compile_artifacts")

    for node in builtin_tree.body:
        if isinstance(node, ast.ImportFrom):
            assert node.module != "kernel_gen.execute_engine.compiler"
        if isinstance(node, ast.Import):
            assert all(alias.name != "kernel_gen.execute_engine.compiler" for alias in node.names)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            assert getattr(node.value.func, "id", None) not in {install_name, "register_compile_strategy"}
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            assert getattr(node.value.func, "id", None) not in {install_name, "register_compile_strategy"}
    compiled_kernel_calls = [
        node
        for node in ast.walk(builtin_tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "CompiledKernel"
    ]
    assert compiled_kernel_calls == []
    dynamic_import_calls = [
        node
        for node in ast.walk(builtin_tree)
        if isinstance(node, ast.Call)
        and (
            getattr(node.func, "id", None) in {"__import__", "getattr"}
            or (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
            )
        )
    ]
    assert dynamic_import_calls == []

    compiler_tree = ast.parse(compiler_path.read_text(encoding="utf-8"))
    install_calls = [
        node
        for node in ast.walk(compiler_tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == install_alias_name
    ]
    assert len(install_calls) == 1


# EE-S1-000D
# 测试目的: 验证 strategy/compiler/builtin_strategy/package root 任意导入顺序不产生循环导入。
# 对应功能实现文件路径: kernel_gen/execute_engine/strategy.py
# 对应 spec 文件路径: spec/execute_engine/strategy.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_strategy_import_order_matrix() -> None:
    modules = (
        "kernel_gen.execute_engine.strategy",
        "kernel_gen.execute_engine.builtin_strategy",
        "kernel_gen.execute_engine.runtime_args",
        "kernel_gen.execute_engine.compiler",
        "kernel_gen.execute_engine",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    for order in itertools.permutations(modules):
        script = "import importlib\n" + "\n".join(f'importlib.import_module("{module}")' for module in order)
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


# EE-S1-000E
# 测试目的: 锁定 compiler facade 不再承载 target include / entry shim / runtime ABI 实现细节。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_compiler_facade_static_boundary() -> None:
    compiler_path = REPO_ROOT / "kernel_gen/execute_engine/compiler.py"
    compiler_tree = ast.parse(compiler_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    defined_classes: set[str] = set()
    function_names: set[str] = set()
    call_names: set[str] = set()
    forbidden_imports = {"ctypes", "subprocess", "tempfile", "shutil"}
    forbidden_defs = {"_CArgSlot", "_ParamSpec", "BuiltinCompileArtifacts"}

    for node in ast.walk(compiler_tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module.split(".")[0])
        if isinstance(node, ast.ClassDef):
            defined_classes.add(node.name)
        if isinstance(node, ast.FunctionDef):
            function_names.add(node.name)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                call_names.add(node.func.id)
            if isinstance(node.func, ast.Attribute):
                call_names.add(node.func.attr)

    assert imported_modules.isdisjoint(forbidden_imports)
    assert defined_classes.isdisjoint(forbidden_defs)
    assert function_names.isdisjoint(forbidden_defs)
    assert "_invoke_compiled_kernel" in call_names
    assert "_build_builtin_compile_artifacts" in call_names
    compiler_module = importlib.import_module("kernel_gen.execute_engine.compiler")
    for name in (
        "RuntimeScalarArgInfo",
        "RuntimeMemoryArgInfo",
        "RuntimeArgInfo",
        "describe_runtime_arg",
        "AllowAbsentMemoryArg",
        "RuntimeInput",
        "invoke_compiled_kernel",
        "BuiltinCompileArtifacts",
        "build_builtin_compile_artifacts",
        "install_builtin_compile_strategies",
    ):
        assert not hasattr(compiler_module, name)


# EE-S1-000E2
# 测试目的: 锁定 compiler.py 公开注解可解析，同时不恢复旧 internal API 公开绑定。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_compiler_public_type_hints_resolve_without_internal_exports() -> None:
    compiler_module = importlib.import_module("kernel_gen.execute_engine.compiler")

    execute_request_hints = get_type_hints(compiler_module.ExecuteRequest)
    compiled_kernel_hints = get_type_hints(compiler_module.CompiledKernel)
    execute_hints = get_type_hints(compiler_module.CompiledKernel.execute)

    assert "args" in execute_request_hints
    assert "allow_absent_memory_args" in compiled_kernel_hints
    assert "args" in execute_hints
    for name in (
        "AllowAbsentMemoryArg",
        "RuntimeInput",
        "invoke_compiled_kernel",
        "BuiltinCompileArtifacts",
        "build_builtin_compile_artifacts",
        "install_builtin_compile_strategies",
    ):
        assert not hasattr(compiler_module, name)


# EE-S1-000F
# 测试目的: 锁定 target_support 旧文件和旧接口退场，且只以公开负例证明。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_target_support_old_module_absent() -> None:
    assert not (REPO_ROOT / "kernel_gen/execute_engine/target_support.py").exists()
    assert importlib.util.find_spec("kernel_gen.execute_engine.target_support") is None


# EE-S1-000G
# 测试目的: 锁定 builtin/runtime 包内文件级 API 不进入包根公开 API。
# 对应功能实现文件路径: kernel_gen/execute_engine/builtin_strategy/__init__.py
# 对应功能实现文件路径: kernel_gen/execute_engine/runtime_args.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_internal_module_file_api_exact_sets() -> None:
    builtin_module = importlib.import_module("kernel_gen.execute_engine.builtin_strategy")
    runtime_module = importlib.import_module("kernel_gen.execute_engine.runtime_args")
    assert builtin_module.__all__ == [
        "BuiltinCompileArtifacts",
        "build_builtin_compile_artifacts",
        "install_builtin_compile_strategies",
    ]
    assert runtime_module.__all__ == [
        "RuntimeScalarArgInfo",
        "RuntimeMemoryArgInfo",
        "RuntimeArgInfo",
        "describe_runtime_arg",
        "AllowAbsentMemoryArg",
        "RuntimeInput",
        "invoke_compiled_kernel",
        "invoke_compiled_kernel_capture_output",
    ]
    for name in (*builtin_module.__all__, *runtime_module.__all__):
        assert name not in execute_engine.__all__

    allowed_defined_names = {
        REPO_ROOT / "kernel_gen/execute_engine/builtin_strategy" / "__init__.py": set(builtin_module.__all__),
        REPO_ROOT / "kernel_gen/execute_engine/runtime_args.py": set(runtime_module.__all__),
    }
    for path, allowed_names in allowed_defined_names.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        defined_names: set[str] = set()
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                defined_names.add(node.name)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)
        unexpected_names = {
            name
            for name in defined_names
            if not name.startswith("_") and name != "__all__" and name not in allowed_names
        }
        assert unexpected_names == set()


# EE-S1-000H
# 测试目的: 锁定本轮 execute_engine 文件的 private callable 边界。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应功能实现文件路径: kernel_gen/execute_engine/strategy.py
# 对应功能实现文件路径: kernel_gen/execute_engine/builtin_strategy/__init__.py
# 对应功能实现文件路径: kernel_gen/execute_engine/runtime_args.py
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_private_callable_gate() -> None:
    target_files = (
        REPO_ROOT / "kernel_gen/execute_engine/compiler.py",
        REPO_ROOT / "kernel_gen/execute_engine/strategy.py",
        REPO_ROOT / "kernel_gen/execute_engine/builtin_strategy" / "__init__.py",
        REPO_ROOT / "kernel_gen/execute_engine/builtin_strategy" / "cpu.py",
        REPO_ROOT / "kernel_gen/execute_engine/builtin_strategy" / "npu_demo.py",
        REPO_ROOT / "kernel_gen/execute_engine/builtin_strategy" / "cuda_sm86.py",
        REPO_ROOT / "kernel_gen/execute_engine/builtin_strategy" / "common.py",
        REPO_ROOT / "kernel_gen/execute_engine/runtime_args.py",
    )
    violations: list[str] = []
    private_names_by_file: dict[Path, set[str]] = {}
    trees: dict[Path, ast.AST] = {}
    for path in target_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        trees[path] = tree
        private_names_by_file[path] = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("_")
            and not node.name.startswith("__")
        }

    for path, tree in trees.items():
        private_names = private_names_by_file[path]
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_") and not node.name.startswith("__"):
                effective_lines = [
                    child
                    for child in node.body
                    if not isinstance(child, (ast.Expr,))
                    or not isinstance(getattr(child, "value", None), ast.Constant)
                    or not isinstance(child.value.value, str)
                ]
                if len(effective_lines) < 5:
                    violations.append(f"{path.name}:{node.lineno}: {node.name} shorter than 5 effective statements")
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id in private_names:
                    violations.append(f"{path.name}:{child.lineno}: {node.name} calls private {child.func.id}")
    assert violations == []


# EE-S1-001
# 测试目的: 验证 compile->execute 最小闭环的成功口径（骨架版）。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_compile_execute_ok() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    try:
        result = kernel.execute(args=())
        assert result.ok is True
        assert result.status_code == 0
        assert result.failure_phrase is None
    finally:
        kernel.close()


# EE-S1-002
# 测试目的: 验证 stream 非空会触发固定失败短语 stream_not_supported。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_stream_not_supported() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    try:
        with pytest.raises(KernelCodeError) as exc:
            kernel.execute(request=ExecuteRequest(args=(), stream=object()))
        assert exc.value.failure_phrase == "stream_not_supported"
    finally:
        kernel.close()


# EE-S1-003
# 测试目的: 验证 capture_function_output=True 会触发固定失败短语 function_output_capture_not_supported。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_function_output_capture_not_supported() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    try:
        with pytest.raises(KernelCodeError) as exc:
            kernel.execute(request=ExecuteRequest(args=(), capture_function_output=True))
        assert exc.value.failure_phrase == "function_output_capture_not_supported"
    finally:
        kernel.close()


# EE-S1-004
# 测试目的: 验证空/非法 source 会触发固定失败短语 source_empty_or_invalid。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_source_empty_or_invalid() -> None:
    engine = ExecutionEngine(target="cpu")
    with pytest.raises(KernelCodeError) as exc:
        engine.compile(source="  ", function="cpu::add")
    assert exc.value.failure_phrase == "source_empty_or_invalid"


# EE-S1-005
# 测试目的: 验证不支持的 target 会触发固定失败短语 target_header_mismatch。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_target_header_mismatch() -> None:
    engine = ExecutionEngine(target="unknown-target")
    with pytest.raises(KernelCodeError) as exc:
        engine.compile(source="int main(){}", function="cpu::add")
    assert exc.value.failure_phrase == "target_header_mismatch"


# EE-S1-006
# 测试目的: 验证失败短语固定集合不变且可机械比较。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_failure_phrases_frozen() -> None:
    expected = {
        "target_header_mismatch",
        "source_empty_or_invalid",
        "compile_failed",
        "symbol_resolve_failed",
        "runtime_throw_or_abort",
        "stream_not_supported",
        "function_output_capture_not_supported",
        "execution_unsupported",
    }
    assert len(expected) == 8
