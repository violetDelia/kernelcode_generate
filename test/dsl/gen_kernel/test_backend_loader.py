"""Third-party backend loader tests.


功能说明:
- 验证 target backend auto-load、导入失败分类和 registry 重复注册规则。

使用示例:
- pytest -q test/dsl/gen_kernel/test_backend_loader.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/register.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/__init__.py
- Spec 文档: spec/dsl/gen_kernel/backend_loader.md
- 测试文件: test/dsl/gen_kernel/test_backend_loader.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, Region
from xdsl.ir import Operation

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.config import reset_config, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c
import kernel_gen.dsl.gen_kernel.emit as emit_package
from kernel_gen.dsl.gen_kernel.emit.register import dispatch_op_for_target, emit_c_impl
from kernel_gen.target.registry import TargetSpec, register_target


@pytest.fixture(autouse=True)
def _reset_core_config() -> None:
    reset_config()
    yield
    reset_config()


def _module() -> ModuleOp:
    """构造最小测试 module。


    功能说明:
    - 返回只包含一个空 `func.func` 的 `ModuleOp`。
    - 用于触发 ModuleOp backend handler 分发。

    使用示例:
    - module = _module()
    """

    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("dummy_bundle", ([], []), Region(block))
    return ModuleOp([func_op])


class _DefaultOnlyOp(Operation):
    """只用于验证默认 registry 不会泄漏到显式 target 查询的测试 op。"""

    name = "test.default_only"


def _register_target_once(name: str) -> None:
    """按公开 target registry 注册测试 target。


    功能说明:
    - 重复注册时忽略已有 target，避免测试顺序造成重复注册失败。

    使用示例:
    - _register_target_once("dummy_generic")
    """

    try:
        register_target(TargetSpec(name, None, set(), {}))
    except ValueError:
        pass


def _add_backend_module_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, target: str, source: str) -> None:
    """为 emit package 注入临时 backend 模块搜索路径。


    功能说明:
    - 在临时目录创建 `kernel_gen.dsl.gen_kernel.emit.<target>` 模块。
    - 将该目录加入当前已加载 emit package 的公开 Python package 搜索路径。

    使用示例:
    - _add_backend_module_path(monkeypatch, tmp_path, "tmp_backend", "...")
    """

    backend_root = tmp_path / "emit_backends"
    module_dir = backend_root / target
    module_dir.mkdir(parents=True)
    (module_dir / "__init__.py").write_text(source, encoding="utf-8")
    monkeypatch.setattr(emit_package, "__path__", [*list(emit_package.__path__), str(backend_root)])


def _duplicate_first_handler(_module_op: ModuleOp, _ctx: EmitCContext) -> str:
    """返回 duplicate 测试的第一份源码。


    功能说明:
    - 作为 `emit_c_impl(...)` 重复注册测试的第一份 handler。

    使用示例:
    - emit_c_impl(ModuleOp, target="duplicate_backend")(_duplicate_first_handler)
    """

    return "first"


def _duplicate_second_handler(_module_op: ModuleOp, _ctx: EmitCContext) -> str:
    """返回 duplicate 测试的第二份源码。


    功能说明:
    - 作为 `emit_c_impl(...)` 重复注册测试的冲突 handler。

    使用示例:
    - emit_c_impl(ModuleOp, target="duplicate_backend")(_duplicate_second_handler)
    """

    return "second"


def _duplicate_override_handler(_module_op: ModuleOp, _ctx: EmitCContext) -> str:
    """返回 duplicate 测试的覆盖源码。


    功能说明:
    - 作为 `emit_c_impl(..., override=True)` 测试的覆盖 handler。

    使用示例:
    - emit_c_impl(ModuleOp, target="duplicate_backend", override=True)(_duplicate_override_handler)
    """

    return "override"


def _default_only_handler(_op: _DefaultOnlyOp, _ctx: EmitCContext) -> str:
    """返回默认 registry handler 的哨兵文本。


    功能说明:
    - 仅注册到默认 op registry。
    - 若 `dispatch_op_for_target(...)` 错误查询默认 registry，测试会看到该哨兵文本。

    使用示例:
    - emit_c_impl(_DefaultOnlyOp)(_default_only_handler)
    """

    return "default-leaked"


def test_backend_loader_imports_registered_dummy_backend() -> None:
    _register_target_once("dummy_generic")
    set_target("dummy_generic")

    source = emit_c(_module(), EmitCContext())

    assert source.startswith("// __KG_BUNDLE_FILE__:kernel.cpp")
    assert "void dummy_bundle()" in source


def test_backend_loader_rejects_unregistered_target_without_cpu_fallback() -> None:
    set_target("missing_backend_case")

    with pytest.raises(KernelCodeError, match="backend_handler_not_found") as exc:
        emit_c(_module(), EmitCContext())
    assert "cpu::" not in str(exc.value)


def test_backend_loader_distinguishes_missing_module() -> None:
    _register_target_once("missing_backend_case")
    set_target("missing_backend_case")

    with pytest.raises(KernelCodeError, match="backend_not_found"):
        emit_c(_module(), EmitCContext())


def test_backend_loader_distinguishes_backend_import_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = "bad_import_backend"
    _register_target_once(target)
    _add_backend_module_path(monkeypatch, tmp_path, target, 'raise RuntimeError("boom")\n')
    set_target(target)

    with pytest.raises(KernelCodeError, match="backend_import_failed"):
        emit_c(_module(), EmitCContext())


def test_backend_loader_distinguishes_missing_module_handler(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = "missing_handler_backend"
    _register_target_once(target)
    _add_backend_module_path(monkeypatch, tmp_path, target, "__all__ = []\n")
    set_target(target)

    with pytest.raises(KernelCodeError, match="backend_handler_not_found"):
        emit_c(_module(), EmitCContext())


def test_emit_registry_duplicate_requires_explicit_override() -> None:
    target = "duplicate_backend"
    first_handler = emit_c_impl(ModuleOp, target=target)(_duplicate_first_handler)

    with pytest.raises(KernelCodeError, match="duplicate backend registration"):
        emit_c_impl(ModuleOp, target=target)(_duplicate_second_handler)

    override_handler = emit_c_impl(ModuleOp, target=target, override=True)(_duplicate_override_handler)
    assert callable(first_handler)
    assert callable(override_handler)


def test_dispatch_op_for_target_does_not_read_default_registry() -> None:
    target = "explicit_target_backend"
    _register_target_once(target)
    set_target(target)
    emit_c_impl(_DefaultOnlyOp, override=True)(_default_only_handler)

    result = dispatch_op_for_target(_DefaultOnlyOp(), EmitCContext(), target)

    assert result is None
