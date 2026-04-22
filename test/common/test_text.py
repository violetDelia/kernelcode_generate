"""Common text helper tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen.common.text 中的文本拼接与 module 归一化辅助。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.common.text --cov-branch --cov-report=term-missing test/common/test_text.py

使用示例:
- pytest -q test/common/test_text.py

关联文件:
- 功能实现: [kernel_gen/common/text.py](kernel_gen/common/text.py)
- Spec 文档:
  - [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
  - [spec/tools/ircheck.md](spec/tools/ircheck.md)
  - [spec/execute_engine/execute_engine_target.md](spec/execute_engine/execute_engine_target.md)
- 测试文件: [test/common/test_text.py](test/common/test_text.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.parser import Parser

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.common.text import join_text_sections, normalize_module_text, render_operation_text
from kernel_gen.context import build_default_context


_SIMPLE_MODULE_TEXT = """builtin.module {
  func.func @main() {
    func.return
  }
}
"""


def test_join_text_sections_merges_sections() -> None:
    assert join_text_sections("#include <a>", "", "int main() {}") == "#include <a>\n\nint main() {}\n"


def test_render_operation_text_strips_trailing_newline() -> None:
    ctx = build_default_context()
    module = Parser(ctx, _SIMPLE_MODULE_TEXT).parse_module()

    rendered = render_operation_text(module)

    assert rendered == _SIMPLE_MODULE_TEXT.rstrip()
    assert not rendered.endswith("\n")


def test_normalize_module_text_roundtrips_builtin_module() -> None:
    ctx = build_default_context()
    module = Parser(ctx, _SIMPLE_MODULE_TEXT).parse_module()

    normalized = normalize_module_text(module, ctx)

    assert normalized == _SIMPLE_MODULE_TEXT.rstrip()
