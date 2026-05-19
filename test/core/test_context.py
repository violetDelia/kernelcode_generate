"""core context tests.


功能说明:
- 覆盖 `build_default_context()` 的公开 dialect 加载合同。

使用示例:
- pytest -q test/core/test_context.py

关联文件:
- 功能实现: kernel_gen/core/context.py
- Spec 文档: spec/core/context.md
- 测试文件: test/core/test_context.py
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from xdsl.parser import Parser

from kernel_gen.core.context import build_default_context

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_default_context_loads_memory_dialect() -> None:
    """默认 Context 加载 memory dialect 并可解析 `memory.get_data`。"""

    ctx = build_default_context()

    assert ctx.get_optional_dialect("memory") is not None
    module = Parser(
        ctx,
        """
builtin.module {
  func.func @get_data(%mem: !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<global>, template = T_bias>) {
    %ptr = memory.get_data %mem : !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<global>, template = T_bias> -> !symbol.ptr<f32, template = T_bias>
    func.return
  }
}
""",
    ).parse_module()
    module.verify()


def test_legacy_kernel_gen_context_import_path_is_removed() -> None:
    """旧 context 子模块不再作为公开导入路径。"""

    legacy_module = ".".join(("kernel_gen", "context"))
    script = f"import importlib; importlib.import_module({legacy_module!r})"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "ModuleNotFoundError" in result.stderr
