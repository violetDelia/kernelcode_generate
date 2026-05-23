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
- 功能实现: kernel_gen/execute_engine/builtin_strategy.py
- Spec 文档: spec/execute_engine/execute_engine.md
- Spec 文档: spec/execute_engine/execute_engine_api.md
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_contract.py
- 测试文件: test/execute_engine/test_builtin_strategy.py
"""

from __future__ import annotations

import ast
import importlib
import itertools
import os
import subprocess
import sys
from pathlib import Path

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
    assert (execute_engine_dir / "builtin_strategy.py").is_file()
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
# 对应功能实现文件路径: kernel_gen/execute_engine/builtin_strategy.py
# 对应 spec 文件路径: spec/execute_engine/strategy.md
# 对应测试文件路径: test/execute_engine/test_contract.py
def test_execute_engine_builtin_strategy_static_install_boundary() -> None:
    install_name = "install_builtin_compile" + "_strategies"
    builtin_path = REPO_ROOT / "kernel_gen/execute_engine/builtin_strategy.py"
    compiler_path = REPO_ROOT / "kernel_gen/execute_engine/compiler.py"
    builtin_source = builtin_path.read_text(encoding="utf-8")
    builtin_tree = ast.parse(builtin_source)
    assert "CompileRequest" not in builtin_source
    assert "CompiledKernel" not in builtin_source
    assert "kernel_gen.execute_engine.compiler" not in builtin_source
    assert install_name not in execute_engine.__all__
    assert not hasattr(execute_engine, install_name)

    for node in builtin_tree.body:
        if isinstance(node, ast.ImportFrom):
            assert node.module != "kernel_gen.execute_engine.compiler"
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            assert getattr(node.value.func, "id", None) not in {install_name, "register_compile_strategy"}
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            assert getattr(node.value.func, "id", None) not in {install_name, "register_compile_strategy"}

    compiler_tree = ast.parse(compiler_path.read_text(encoding="utf-8"))
    install_calls = [
        node
        for node in ast.walk(compiler_tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == install_name
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
