"""Compile strategy registry tests.


功能说明:
- 验证 `register_compile_strategy(...)`、`get_compile_strategy(...)` 与 `ExecutionEngine.compile(...)` 的 target strategy 分发。
- 覆盖 dummy backend compile-only source 与 SourceBundle 行为。

使用示例:
- pytest -q test/execute_engine/test_compile_strategy.py

关联文件:
- 功能实现: kernel_gen/execute_engine/compiler.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/dummy_generic/__init__.py
- Spec 文档: spec/execute_engine/strategy.md
- 测试文件: test/execute_engine/test_compile_strategy.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.config import reset_config, set_dump_dir
from kernel_gen.core.error import KernelCodeError
from kernel_gen.execute_engine import (
    CompiledKernel,
    CompileRequest,
    ExecutionEngine,
    get_compile_strategy,
    register_compile_strategy,
)
from kernel_gen.target.registry import TargetSpec, register_target


@pytest.fixture(autouse=True)
def _reset_core_config() -> None:
    reset_config()
    yield
    reset_config()


class _StrategyForTest:
    """测试用 compile strategy。"""

    def compile(self, request: CompileRequest) -> CompiledKernel:
        """返回测试用编译产物。


        功能说明:
        - 不执行真实编译，只按 request 填充 `CompiledKernel`。

        使用示例:
        - kernel = _StrategyForTest().compile(request)
        """

        return CompiledKernel(
            target=request.target,
            soname_path="/tmp/test_strategy.so",
            function=request.function,
            entry_point=request.entry_point,
            compile_stdout="strategy",
        )


def _register_target_once(name: str) -> None:
    """注册测试 target。


    功能说明:
    - 使用公开 target registry 注册 target；重复时忽略。

    使用示例:
    - _register_target_once("strategy_backend")
    """

    try:
        register_target(TargetSpec(name, None, set(), {}))
    except ValueError:
        pass


def _ensure_dummy_backend_loaded() -> None:
    """注册并导入 dummy backend。


    功能说明:
    - 先注册 `dummy_generic` target，再导入 backend 模块触发 compile strategy 注册。

    使用示例:
    - _ensure_dummy_backend_loaded()
    """

    _register_target_once("dummy_generic")
    from kernel_gen.dsl.gen_kernel.emit import dummy_generic as _dummy_generic  # noqa: F401


def test_compile_strategy_registry_duplicate_requires_override() -> None:
    target = "strategy_backend"
    _register_target_once(target)
    strategy = _StrategyForTest()

    register_compile_strategy(target, strategy)
    with pytest.raises(KernelCodeError, match="duplicate compile strategy"):
        register_compile_strategy(target, strategy)

    register_compile_strategy(target, strategy, override=True)
    assert get_compile_strategy(target) is strategy


def test_compile_strategy_missing_target_does_not_fallback_to_cpu() -> None:
    target = "missing_strategy_backend"
    _register_target_once(target)

    with pytest.raises(KernelCodeError) as exc:
        ExecutionEngine(target=target).compile(source="void f() {}\n", function="f")

    assert exc.value.failure_phrase == "target_header_mismatch"
    assert "missing compile strategy" in str(exc.value)


def test_compile_request_rejects_source_or_function_mix() -> None:
    cases: tuple[tuple[str, str | None, str | None], ...] = (
        ("source", "void conflict() {}\n", None),
        ("function", None, "conflict"),
    )
    for case_id, source, function in cases:
        target = f"request_conflict_{case_id}_backend"
        _register_target_once(target)
        register_compile_strategy(target, _StrategyForTest(), override=True)
        request = CompileRequest(
            source="void request_func() {}\n",
            target=target,
            function="request_func",
        )

        with pytest.raises(KernelCodeError, match="request cannot be combined with source or function") as exc:
            ExecutionEngine(target=target).compile(source=source, function=function, request=request)

        assert exc.value.failure_phrase == "source_empty_or_invalid"


def test_dummy_compile_strategy_writes_single_source_and_is_compile_only(tmp_path: Path) -> None:
    _ensure_dummy_backend_loaded()
    set_dump_dir(tmp_path)

    kernel = ExecutionEngine(target="dummy_generic").compile(source="void dummy_single() {}\n", function="dummy_single")

    assert kernel.target == "dummy_generic"
    assert "dummy compile strategy" in kernel.compile_stdout
    assert (tmp_path / "compile" / "dummy_generic" / "dummy_single" / "source" / "source.cpp").is_file()
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(args=())
    assert exc.value.failure_phrase == "execution_unsupported"


def test_dummy_compile_strategy_writes_source_bundle_artifacts(tmp_path: Path) -> None:
    _ensure_dummy_backend_loaded()
    set_dump_dir(tmp_path)
    source = (
        "// __KG_BUNDLE_FILE__:kernel.cpp\n"
        "void dummy_bundle() {}\n"
        "// __KG_BUNDLE_FILE__:include/kernel.h\n"
        "#pragma once\n"
    )

    kernel = ExecutionEngine(target="dummy_generic").compile(source=source, function="dummy_bundle")

    source_root = tmp_path / "compile" / "dummy_generic" / "dummy_bundle" / "source"
    assert kernel.target == "dummy_generic"
    assert (source_root / "source.cpp").read_text(encoding="utf-8") == source
    assert (source_root / "kernel.cpp").read_text(encoding="utf-8") == "void dummy_bundle() {}\n"
    assert (source_root / "include" / "kernel.h").read_text(encoding="utf-8") == "#pragma once\n"
