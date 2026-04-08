"""ircheck parser tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 kernel_gen/tools/ircheck.py 的 case 文件解析行为与错误短语约束。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.tools.ircheck --cov-branch --cov-report=term-missing test/tools/test_ircheck_parser.py`

使用示例:
- pytest -q test/tools/test_ircheck_parser.py

关联文件:
- 功能实现: kernel_gen/tools/ircheck.py
- Spec 文档: spec/tools/ircheck.md
- 测试文件: test/tools/test_ircheck_parser.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.tools.ircheck import IrcheckParseError, parse_ircheck_file


# TC-IRCHECK-PARSE-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证可稳定解析 COMPILE_ARGS/CHECK 指令并提取输入 IR 正文。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_basic
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_basic(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module
// CHECK-NEXT: func.func @main
// CHECK-NOT: func.call
// some other comment

builtin.module {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "case.ircheck"
    path.write_text(content, encoding="utf-8")
    case = parse_ircheck_file(str(path))
    assert case.compile_args == "--pass no-op"
    assert case.source_path == str(path)
    assert [d.kind for d in case.checks] == ["CHECK", "CHECK-NEXT", "CHECK-NOT"]
    assert [d.text for d in case.checks] == ["builtin.module", "func.func @main", "func.call"]
    assert [d.line_no for d in case.checks] == [2, 3, 4]
    assert case.input_ir.lstrip().startswith("builtin.module")


# TC-IRCHECK-PARSE-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证缺失 COMPILE_ARGS 会报告稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_missing_compile_args_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_missing_compile_args_fails(tmp_path: Path) -> None:
    content = """// CHECK: builtin.module

builtin.module {}
"""
    path = tmp_path / "missing_compile_args.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid ircheck header$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证重复 COMPILE_ARGS 会报告稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_duplicate_compile_args_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_duplicate_compile_args_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// COMPILE_ARGS: --pass no-op

builtin.module {}
"""
    path = tmp_path / "duplicate_compile_args.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid ircheck header$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证缺失输入 IR 正文会报告稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_missing_input_ir_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_missing_input_ir_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module
"""
    path = tmp_path / "missing_input_ir.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: missing input ir$"):
        _ = parse_ircheck_file(str(path))
