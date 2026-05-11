"""SourceBundle public behavior tests.


功能说明:
- 通过公开 `gen_kernel(...)`、`emit_c_impl(ModuleOp, target=...)` 和 `dump_dir` 验证 SourceBundle aggregate string 与 artifact 写出行为。
- 不直连 SourceBundle 内部 encode/decode/write helper。

使用示例:
- pytest -q test/dsl/gen_kernel/test_source_bundle.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/register.py
- Spec 文档: spec/dsl/gen_kernel/source_bundle.md
- 测试文件: test/dsl/gen_kernel/test_source_bundle.py
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

from kernel_gen.core.config import reset_config, set_dump_dir, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
import kernel_gen.dsl.gen_kernel.emit as emit_package
from kernel_gen.target.registry import TargetSpec, register_target


@pytest.fixture(autouse=True)
def _reset_core_config() -> None:
    reset_config()
    yield
    reset_config()


def _register_target_once(name: str) -> None:
    """注册测试 target。


    功能说明:
    - 通过公开 target registry 注册 target；重复时忽略。

    使用示例:
    - _register_target_once("dummy_generic")
    """

    try:
        register_target(TargetSpec(name, None, set(), {}))
    except ValueError:
        pass


def _module(name: str = "dummy_bundle") -> ModuleOp:
    """构造最小 ModuleOp。


    功能说明:
    - 返回包含一个空函数的 module，用于触发 ModuleOp handler。

    使用示例:
    - module = _module()
    """

    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp(name, ([], []), Region(block))
    return ModuleOp([func_op])


def _add_backend_module_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, target: str, source: str) -> None:
    """注入临时 backend 模块。


    功能说明:
    - 创建 `kernel_gen.dsl.gen_kernel.emit.<target>` 临时模块并加入 emit package 搜索路径。

    使用示例:
    - _add_backend_module_path(monkeypatch, tmp_path, "bundle_bad_path", source)
    """

    backend_root = tmp_path / "emit_backends"
    module_dir = backend_root / target
    module_dir.mkdir(parents=True)
    (module_dir / "__init__.py").write_text(source, encoding="utf-8")
    monkeypatch.setattr(emit_package, "__path__", [*list(emit_package.__path__), str(backend_root)])


def _backend_source(target: str, product_text: str) -> str:
    """生成返回指定 product 的临时 backend 源码。


    功能说明:
    - product 文本必须是 Python 表达式，作为 ModuleOp handler 的返回值。

    使用示例:
    - source = _backend_source("bundle_bad_path", "{'../x.cpp': 'x'}")
    """

    return "\n".join(
        [
            "from xdsl.dialects.builtin import ModuleOp",
            "from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl",
            "",
            f"@emit_c_impl(ModuleOp, target='{target}')",
            "def _emit(_module, _ctx):",
            f"    return {product_text}",
            "",
        ]
    )


def test_source_bundle_dump_writes_aggregate_and_artifacts(tmp_path: Path) -> None:
    _register_target_once("dummy_generic")
    set_target("dummy_generic")
    set_dump_dir(tmp_path)

    source = gen_kernel(_module(), EmitCContext())

    assert (tmp_path / "source.cpp").read_text(encoding="utf-8") == source
    assert (tmp_path / "kernel.cpp").read_text(encoding="utf-8") == "void dummy_bundle() {}\n"
    assert (tmp_path / "include" / "kernel.h").read_text(encoding="utf-8") == "#pragma once\n"


def test_source_bundle_rejects_marker_line_in_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = "bundle_marker_backend"
    _register_target_once(target)
    _add_backend_module_path(
        monkeypatch,
        tmp_path,
        target,
        _backend_source(target, "{'kernel.cpp': '// __KG_BUNDLE_FILE__:bad.cpp\\n'}"),
    )
    set_target(target)

    with pytest.raises(KernelCodeError, match="source_bundle_malformed"):
        gen_kernel(_module(), EmitCContext())


def test_source_bundle_rejects_malformed_artifact_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = "bundle_bad_path_backend"
    _register_target_once(target)
    _add_backend_module_path(
        monkeypatch,
        tmp_path,
        target,
        _backend_source(target, "{'../kernel.cpp': 'void bad() {}'}"),
    )
    set_target(target)

    with pytest.raises(KernelCodeError, match="source_bundle_malformed"):
        gen_kernel(_module(), EmitCContext())


def test_source_bundle_dump_rejects_symlink_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = "bundle_symlink_backend"
    _register_target_once(target)
    _add_backend_module_path(
        monkeypatch,
        tmp_path,
        target,
        _backend_source(target, "{'escape/kernel.cpp': 'void bad() {}'}"),
    )
    dump_dir = tmp_path / "dump"
    outside = tmp_path / "outside"
    dump_dir.mkdir()
    outside.mkdir()
    (dump_dir / "escape").symlink_to(outside, target_is_directory=True)
    set_target(target)
    set_dump_dir(dump_dir)

    with pytest.raises(KernelCodeError, match="source_bundle_path_escape"):
        gen_kernel(_module(), EmitCContext())
