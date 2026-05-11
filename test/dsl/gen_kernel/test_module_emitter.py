"""ModuleOp backend emitter tests.


功能说明:
- 验证 `emit_c_impl(ModuleOp, target=...)` 是 module 源码生成的唯一扩展入口。
- 覆盖单文件源码、多文件 SourceProduct 与非法返回类型。

使用示例:
- pytest -q test/dsl/gen_kernel/test_module_emitter.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/__init__.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/register.py
- Spec 文档: spec/dsl/gen_kernel/emit/register.md
- 测试文件: test/dsl/gen_kernel/test_module_emitter.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.config import reset_config, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c
import kernel_gen.dsl.gen_kernel.emit as emit_package
from kernel_gen.target.registry import TargetSpec, register_target


@pytest.fixture(autouse=True)
def _reset_core_config() -> None:
    reset_config()
    yield
    reset_config()


def _register_target_once(name: str) -> None:
    """按公开 target registry 注册测试 target。


    功能说明:
    - 重复注册时忽略已有 target，便于同一进程内多测试复用固定 dummy target。

    使用示例:
    - _register_target_once("dummy_generic")
    """

    try:
        register_target(TargetSpec(name, None, set(), {}))
    except ValueError:
        pass


def _module(func_name: str) -> ModuleOp:
    """构造包含指定函数名的最小 ModuleOp。


    功能说明:
    - 生成一个空 body 的 `func.func` 并包入 `ModuleOp`。

    使用示例:
    - module = _module("dummy_single")
    """

    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp(func_name, ([], []), Region(block))
    return ModuleOp([func_op])


def _add_backend_module_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, target: str, source: str) -> None:
    """注入临时 backend 模块。


    功能说明:
    - 将临时 backend 搜索目录加入当前 emit package 的 Python package 路径。

    使用示例:
    - _add_backend_module_path(monkeypatch, tmp_path, "invalid_backend", source)
    """

    backend_root = tmp_path / "emit_backends"
    module_dir = backend_root / target
    module_dir.mkdir(parents=True)
    (module_dir / "__init__.py").write_text(source, encoding="utf-8")
    monkeypatch.setattr(emit_package, "__path__", [*list(emit_package.__path__), str(backend_root)])


def test_module_handler_returns_single_source_string() -> None:
    _register_target_once("dummy_generic")
    set_target("dummy_generic")

    source = emit_c(_module("dummy_single"), EmitCContext())

    assert source == "void dummy_single() {}\n"


def test_module_handler_returns_mapping_as_source_bundle() -> None:
    _register_target_once("dummy_generic")
    set_target("dummy_generic")

    source = emit_c(_module("dummy_bundle"), EmitCContext())

    assert source.startswith("// __KG_BUNDLE_FILE__:kernel.cpp")
    assert "// __KG_BUNDLE_FILE__:include/kernel.h" in source
    assert "void dummy_bundle()" in source


def test_module_handler_rejects_invalid_source_product(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = "invalid_product_backend"
    _register_target_once(target)
    _add_backend_module_path(
        monkeypatch,
        tmp_path,
        target,
        "\n".join(
            [
                "from xdsl.dialects.builtin import ModuleOp",
                "from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl",
                "",
                "@emit_c_impl(ModuleOp, target='invalid_product_backend')",
                "def _emit(_module, _ctx):",
                "    return 123",
                "",
            ]
        ),
    )
    set_target(target)

    with pytest.raises(KernelCodeError, match="source_product_invalid"):
        emit_c(_module("invalid_product"), EmitCContext())
