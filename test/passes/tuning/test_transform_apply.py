"""transform-apply pass public tests.

功能说明:
- 覆盖 `TransformApplyPass` 对 `kernel.transform_pipeline` 的公开消费、attr 移除与失败回滚。

使用示例:
- pytest -q test/passes/tuning/test_transform_apply.py

关联文件:
- 功能实现: kernel_gen/passes/tuning/transform_apply.py
- Spec 文档: spec/pass/tuning/transform_apply.md
- 测试文件: test/passes/tuning/test_transform_apply.py
"""

from __future__ import annotations

import importlib
from io import StringIO
from pathlib import Path
import sys

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.parser import Parser
from xdsl.printer import Printer

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.context import build_default_context
from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.tuning import TransformApplyPass


def test_transform_apply_public_import_path_rehomed() -> None:
    """验证 transform-apply 公开导入路径已迁移。

    功能说明:
    - 只通过公开 package 与 canonical module 路径验证新入口可达、旧根模块失败。

    使用示例:
    - pytest -q test/passes/tuning/test_transform_apply.py -k public_import_path_rehomed
    """

    module = importlib.import_module("kernel_gen.passes.tuning.transform_apply")
    assert module.TransformApplyPass is TransformApplyPass
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("kernel_gen.passes.transform_apply")


def _parse_module(text: str) -> ModuleOp:
    """解析 transform-apply 测试 IR。

    功能说明:
    - 使用默认公开 context，测试只通过 pass 的 `apply(ctx, module)` 入口观察行为。

    使用示例:
    - module = _parse_module("builtin.module {...}")
    """

    return Parser(build_default_context(), text).parse_module()


def _print_ir(module: ModuleOp) -> str:
    """打印 module 为稳定文本。

    功能说明:
    - 避免测试直连 transform-apply 内部 helper。

    使用示例:
    - text = _print_ir(module)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(module)
    return stream.getvalue()


def test_transform_apply_consumes_canonicalize_pipeline_attr() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @pattern() attributes {kernel.transform_pipeline = "--pass canonicalize"} {
    func.return
  }
}
"""
    )

    TransformApplyPass().apply(Context(), module)
    text = _print_ir(module)

    assert "kernel.transform_pipeline" not in text
    assert "func.func @pattern" in text


def test_transform_apply_rolls_back_on_invalid_pipeline() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @pattern() attributes {kernel.transform_pipeline = "--pass missing-pass"} {
    func.return
  }
}
"""
    )
    before = _print_ir(module)

    with pytest.raises(KernelCodeError, match="transform-apply"):
        TransformApplyPass().apply(Context(), module)

    assert _print_ir(module) == before


def test_transform_apply_reports_pipeline_syntax_error() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @pattern() attributes {kernel.transform_pipeline = "--pass"} {
    func.return
  }
}
"""
    )
    before = _print_ir(module)

    with pytest.raises(KernelCodeError, match="transform-apply pipeline syntax"):
        TransformApplyPass().apply(Context(), module)

    assert _print_ir(module) == before


def test_transform_apply_wraps_step_execution_failure() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @pattern() attributes {kernel.transform_pipeline = "--pass \\"attach-arch-information={target=missing_target}\\""} {
    func.return
  }
}
"""
    )
    before = _print_ir(module)

    with pytest.raises(KernelCodeError, match="transform-apply step pass 'attach-arch-information' failed"):
        TransformApplyPass().apply(Context(), module)

    assert _print_ir(module) == before


def test_transform_apply_rejects_unknown_options() -> None:
    with pytest.raises(KernelCodeError, match="transform-apply options unknown: extra"):
        TransformApplyPass.from_options({"extra": "1"})
