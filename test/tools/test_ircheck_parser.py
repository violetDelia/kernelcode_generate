"""ircheck parser tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

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


# TC-IRCHECK-PARSE-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证 COMPILE_ARGS 冒号后文本为空时必须解析失败并报告稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_empty_compile_args_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_empty_compile_args_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS:
// CHECK: builtin.module

builtin.module {}
"""
    path = tmp_path / "empty_compile_args.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid ircheck header$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证 CHECK/CHECK-NOT/CHECK-NEXT 冒号后文本为空时必须解析失败并报告稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_empty_check_text_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
@pytest.mark.parametrize(
    "header",
    [
        "// CHECK:",
        "// CHECK-NOT:",
        "// CHECK: func.func @main\n// CHECK-NEXT:",
    ],
)
def test_parse_ircheck_file_empty_check_text_fails(tmp_path: Path, header: str) -> None:
    content = f"""// COMPILE_ARGS: --pass no-op
{header}

builtin.module {{
  func.func @main() {{
    func.return
  }}
}}
"""
    path = tmp_path / "empty_check_text.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid ircheck header$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证 CHECK-NEXT 不得作为第一条 positive check；否则必须解析失败。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_check_next_first_positive_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_check_next_first_positive_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK-NOT: func.call
// CHECK-NEXT: func.return

builtin.module {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "check_next_first_positive.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid ircheck header$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-008
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-10 13:10:00 +0800
# 最近一次运行成功时间: 2026-04-10 13:10:00 +0800
# 功能说明: 验证 parse_ircheck_file 仅支持单 case；出现 `// -----` 多 case 分隔符时必须解析失败。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_rejects_multi_case_separator
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_rejects_multi_case_separator(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
// -----
// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
"""
    path = tmp_path / "multi_case.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid ircheck header$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-009
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证 parser 可识别 CHECK-REGEX/CHECK-NEXT-REGEX/CHECK-NOT-REGEX 及变量定义/引用。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_regex_directives
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_regex_directives(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: %[[VAL:{int}]] = arith.constant [[VAL]] : i32
// CHECK-NEXT-REGEX: %[[NEXT:{int}]] = arith.constant [[VAL]] : i32
// CHECK-NOT-REGEX: func\\.call

builtin.module {
  func.func @main() {
    %0 = arith.constant 7 : i32
    %1 = arith.constant 7 : i32
    func.return
  }
}
"""
    path = tmp_path / "regex.ircheck"
    path.write_text(content, encoding="utf-8")
    case = parse_ircheck_file(str(path))
    assert [directive.kind for directive in case.checks] == [
        "CHECK-REGEX",
        "CHECK-NEXT-REGEX",
        "CHECK-NOT-REGEX",
    ]
    assert case.checks[0].line_no == 2
    assert case.checks[1].line_no == 3
    assert case.checks[2].line_no == 4


# TC-IRCHECK-PARSE-010
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证非法 regex 写法会返回稳定错误短语 `invalid regex check`。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_invalid_regex_check_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_invalid_regex_check_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: func.func @[[FN:(]]

builtin.module {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "invalid_regex.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid regex check$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-010A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 15:05 +0800
# 最近一次运行成功时间: 2026-04-14 15:05 +0800
# 功能说明: 验证未闭合的转义 `[[` 变量片段也会返回稳定错误短语 `invalid regex check`。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_unclosed_escaped_regex_variable_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_unclosed_escaped_regex_variable_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: func.func @main\\(\\[\\[BROKEN:{reg}\\]

builtin.module {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "invalid_escaped_regex.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid regex check$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-010B
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 21:02 +0800
# 最近一次运行成功时间: 2026-04-14 21:02 +0800
# 功能说明: 验证按 spec 转义的字面量 `[[...]]` 不会被 parser 误判成非法变量片段。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_escaped_double_brackets_literal_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_escaped_double_brackets_literal_ok(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: note = "\\[\\[LIT\\]\\]"

builtin.module attributes {note = "[[LIT]]"} {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "escaped_double_brackets_literal.ircheck"
    path.write_text(content, encoding="utf-8")
    case = parse_ircheck_file(str(path))
    assert case.checks[0].kind == "CHECK-REGEX"
    assert case.checks[0].text == r'note = "\[\[LIT\]\]"'


# TC-IRCHECK-PARSE-010C
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 21:08 +0800
# 最近一次运行成功时间: 2026-04-14 21:08 +0800
# 功能说明: 验证按 spec 转义的字面量 `[[` 前缀不会被 parser 误判成非法变量片段。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_escaped_double_open_brackets_prefix_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_escaped_double_open_brackets_prefix_ok(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: note = "\\[\\["

builtin.module attributes {note = "[["} {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "escaped_double_open_prefix.ircheck"
    path.write_text(content, encoding="utf-8")
    case = parse_ircheck_file(str(path))
    assert case.checks[0].kind == "CHECK-REGEX"
    assert case.checks[0].text == r'note = "\[\["'


# TC-IRCHECK-PARSE-011
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证引用未定义 regex 变量会返回稳定错误短语 `undefined regex variable`。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_undefined_regex_variable_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_undefined_regex_variable_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: func.func @[[FN]]

builtin.module {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "undefined_regex_variable.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: undefined regex variable$"):
        _ = parse_ircheck_file(str(path))


# TC-IRCHECK-PARSE-012
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证重复定义 regex 变量与 CHECK-NOT-REGEX 定义变量都会返回稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_duplicate_or_not_regex_variable_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
@pytest.mark.parametrize(
    ("header", "message"),
    [
        (
            "// CHECK-REGEX: func.func @[[FN:{reg}]]\n// CHECK-REGEX: func.func @[[FN:{reg}]]",
            r"^IrcheckParseError: duplicate regex variable$",
        ),
        (
            "// CHECK: func.func @main\n// CHECK-NOT-REGEX: [[FN:{reg}]]",
            r"^IrcheckParseError: CHECK-NOT-REGEX cannot define variables$",
        ),
    ],
)
def test_parse_ircheck_file_duplicate_or_not_regex_variable_fails(
    tmp_path: Path, header: str, message: str
) -> None:
    content = f"""// COMPILE_ARGS: --pass no-op
{header}

builtin.module {{
  func.func @main() {{
    func.return
  }}
}}
"""
    path = tmp_path / "duplicate_or_not_regex.ircheck"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IrcheckParseError, match=message):
        _ = parse_ircheck_file(str(path))
