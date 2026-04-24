"""ircheck parser tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

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

import importlib
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.tools.ircheck import IrcheckParseError, parse_ircheck_file

ircheck_module = importlib.import_module("kernel_gen.tools.ircheck")


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


# TC-IRCHECK-PARSE-007A
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-17 00:00:00 +0800
# 最近一次运行成功时间: 待本轮验证后补充
# 功能说明: 验证旧 CHECK-REGEX 系列语法不再兼容，必须直接解析失败。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_legacy_regex_directives_fail
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
@pytest.mark.parametrize(
    "header",
    [
        "// CHECK-REGEX: func.func @main",
        "// CHECK: func.func @main\n// CHECK-NEXT-REGEX: func.return",
        "// CHECK-NOT-REGEX: func.call",
    ],
)
def test_parse_ircheck_file_legacy_regex_directives_fail(tmp_path: Path, header: str) -> None:
    content = f"""// COMPILE_ARGS: --pass no-op
{header}

builtin.module {{
  func.func @main() {{
    func.return
  }}
}}
"""
    path = tmp_path / "legacy_regex_directives.ircheck"
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
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-17 00:00:00 +0800
# 最近一次运行成功时间: 待本轮验证后补充
# 功能说明: 验证 parser 可识别 CHECK/CHECK-NEXT/CHECK-NOT 里的变量定义与引用。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_variable_directives
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_variable_directives(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK: %[[VAL:{int}]] = arith.constant [[VAL]] : i32
// CHECK-NEXT: %[[NEXT:{int}]] = arith.constant [[VAL]] : i32
// CHECK-NOT: func.call

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
        "CHECK",
        "CHECK-NEXT",
        "CHECK-NOT",
    ]
    assert case.checks[0].line_no == 2
    assert case.checks[1].line_no == 3
    assert case.checks[2].line_no == 4


# TC-IRCHECK-PARSE-010
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证非法变量 regex 写法会返回稳定错误短语 `invalid regex check`。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_invalid_variable_regex_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_invalid_variable_regex_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK: func.func @[[FN:(]]

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
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_unclosed_escaped_variable_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_unclosed_escaped_variable_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK: func.func @main\\(\\[\\[BROKEN:{reg}\\]

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
// CHECK: note = "\\[\\[LIT\\]\\]"

builtin.module attributes {note = "[[LIT]]"} {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "escaped_double_brackets_literal.ircheck"
    path.write_text(content, encoding="utf-8")
    case = parse_ircheck_file(str(path))
    assert case.checks[0].kind == "CHECK"
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
// CHECK: note = "\\[\\["

builtin.module attributes {note = "[["} {
  func.func @main() {
    func.return
  }
}
"""
    path = tmp_path / "escaped_double_open_prefix.ircheck"
    path.write_text(content, encoding="utf-8")
    case = parse_ircheck_file(str(path))
    assert case.checks[0].kind == "CHECK"
    assert case.checks[0].text == r'note = "\[\["'


# TC-IRCHECK-PARSE-011
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证引用未定义变量会返回稳定错误短语 `undefined regex variable`。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_undefined_variable_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_parse_ircheck_file_undefined_variable_fails(tmp_path: Path) -> None:
    content = """// COMPILE_ARGS: --pass no-op
// CHECK: func.func @[[FN]]

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
# 功能说明: 验证重复定义变量与 CHECK-NOT 定义变量都会返回稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_parse_ircheck_file_duplicate_or_not_variable_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
@pytest.mark.parametrize(
    ("header", "message"),
    [
        (
            "// CHECK: func.func @[[FN:{reg}]]\n// CHECK: func.func @[[FN:{reg}]]",
            r"^IrcheckParseError: duplicate regex variable$",
        ),
        (
            "// CHECK: func.func @main\n// CHECK-NOT: [[FN:{reg}]]",
            r"^IrcheckParseError: CHECK-NOT cannot define variables$",
        ),
    ],
)
def test_parse_ircheck_file_duplicate_or_not_variable_fails(
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


# TC-IRCHECK-PARSE-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 直接覆盖 regex token / literal helper 的剩余解析边界。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_ircheck_private_regex_helper_edges
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_ircheck_private_regex_helper_edges() -> None:
    tokens = ircheck_module._tokenize_check_pattern(r"func @[[FN:{reg}]] -> [[FN]]")
    assert tokens == [
        ("literal", "func @", None),
        ("define", "FN", "{reg}"),
        ("literal", " -> ", None),
        ("ref", "FN", None),
    ]

    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid regex check$"):
        ircheck_module._tokenize_check_pattern("func [[")

    assert ircheck_module._decode_literal_check_fragment(r"arith\.constant \[\[LIT\]\] \\path") == "arith.constant [[LIT]] \\path"
    assert ircheck_module._contains_invalid_regex_literal_fragment("[[") is True
    assert ircheck_module._contains_invalid_regex_literal_fragment(r"\[\[BROKEN:{reg}\]") is True
    assert ircheck_module._contains_invalid_regex_literal_fragment(r"\[\[LIT\]\]") is False
    assert ircheck_module._expand_regex_aliases("{reg}-{int}") == r"(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)--?[0-9]+"

    compiled = ircheck_module._compile_literal_fragment(r"func {{@.*}} {.*} done")
    assert re.fullmatch(compiled, "func @main anything done")

    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid regex check$"):
        ircheck_module._compile_literal_fragment("func {{")

    assert ircheck_module._validate_pattern_directive(r"@[[FN:{reg}]] -> [[FN]]", "CHECK", set()) == ["FN"]
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: undefined regex variable$"):
        ircheck_module._validate_pattern_directive("[[UNDEF]]", "CHECK", set())
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: duplicate regex variable$"):
        ircheck_module._validate_pattern_directive("[[FN:{reg}]][[FN:{reg}]]", "CHECK", set())
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: CHECK-NOT cannot define variables$"):
        ircheck_module._validate_pattern_directive("[[FN:{reg}]]", "CHECK-NOT", set())

    directive = ircheck_module.CheckDirective(kind="CHECK", text=r"%[[VAL:{int}]] = arith.constant [[VAL]] : i32", line_no=1)
    pattern, definitions = ircheck_module._compile_pattern_directive(directive, {})
    assert definitions == ["VAL"]
    match = pattern.fullmatch("%7 = arith.constant 7 : i32")
    assert match is not None
    assert match.group("VAL") == "7"


# TC-IRCHECK-PARSE-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖多 case 切分、source_path 追加与 fail-fast 汇总边界。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_ircheck_private_case_split_and_run_edges
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_ircheck_private_case_split_and_run_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    empty_blocks = ircheck_module._split_ircheck_text_into_case_blocks("")
    assert empty_blocks == [ircheck_module.IrcheckCaseBlock(text="", start_line=1)]

    suite_text = """// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
// -----
// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
"""
    blocks = ircheck_module._split_ircheck_text_into_case_blocks(suite_text)
    assert [block.start_line for block in blocks] == [1, 6]

    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid ircheck header$"):
        ircheck_module._split_ircheck_text_into_case_blocks("// -----")

    cases = ircheck_module._parse_ircheck_cases(suite_text, source_path="suite.ircheck")
    assert [case.source_path for case in cases] == ["suite.ircheck#case-1", "suite.ircheck#case-2"]

    empty_result = ircheck_module._run_ircheck_cases([])
    assert empty_result.ok is False
    assert empty_result.exit_code == 2
    assert empty_result.message == "IrcheckParseError: invalid ircheck header"

    scripted_results = iter(
        [
            ircheck_module.IrcheckResult(ok=True, exit_code=0, actual_ir="ok"),
            ircheck_module.IrcheckResult(ok=False, exit_code=1, actual_ir="bad", message="IrcheckCheckError: failed"),
        ]
    )
    monkeypatch.setattr(ircheck_module, "_run_ircheck_case", lambda case, dump_dir=None, emitc_target=None: next(scripted_results))
    merged_result = ircheck_module._run_ircheck_cases(cases)
    assert merged_result.ok is False
    assert merged_result.message == "IrcheckCheckError: failed [case 2]"

    parse_error_result = ircheck_module.run_ircheck_text("// CHECK: builtin.module")
    assert parse_error_result.ok is False
    assert parse_error_result.exit_code == 2


# TC-IRCHECK-PARSE-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 ircheck CLI 参数、irdump 根目录与 compile-args helper 的剩余边界。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_ircheck_private_cli_and_compile_helper_edges
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_ircheck_private_cli_and_compile_helper_edges() -> None:
    assert ircheck_module._parse_cli_args([]) is None
    assert ircheck_module._parse_cli_args(["-irdump", "-irdump", "case.ircheck"]) is None
    assert ircheck_module._parse_cli_args(["-emitc{target=cpu}", "-emitc{target=npu_demo}", "case.ircheck"]) is None
    assert ircheck_module._parse_cli_args(["-emitc", "case.ircheck"]) is None
    assert ircheck_module._parse_cli_args(["-unknown", "case.ircheck"]) is None
    assert ircheck_module._parse_cli_args(["case1.ircheck", "case2.ircheck"]) is None
    assert ircheck_module._parse_cli_args(["-irdump", "-emitc{target=cpu}", "case.ircheck"]) == (
        "case.ircheck",
        True,
        "cpu",
    )

    assert ircheck_module._build_irdump_root(None, enabled=False) is None
    root = ircheck_module._build_irdump_root("suite.ircheck#case-2", enabled=True)
    assert root is not None
    assert root.name == "suite"

    assert ircheck_module._parse_name_and_options("tile") == ("tile", {})
    assert ircheck_module._parse_name_and_options("tile={analysis-only=true}") == (
        "tile",
        {"analysis-only": "true"},
    )
    assert ircheck_module._parse_name_and_options("={x=y}") is None
    assert ircheck_module._parse_name_and_options("tile={}") is None
    assert ircheck_module._parse_name_and_options("tile={x=1,x=2}") is None
    assert ircheck_module._parse_name_and_options("tile{broken}") is None

    valid_steps = ircheck_module._parse_compile_args('--pass "tile={analysis-only=true}" --pipeline lower')
    assert valid_steps is not None
    assert [(step.kind, step.name, step.options) for step in valid_steps] == [
        ("pass", "tile", {"analysis-only": "true"}),
        ("pipeline", "lower", {}),
    ]
    assert ircheck_module._parse_compile_args("--pass tile={analysis-only=true}") is None
    assert ircheck_module._parse_compile_args("--pass ") is None


# TC-IRCHECK-PARSE-016
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 ircheck render/runner 的 parse、print、compile 与 emitc 失败分支。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_ircheck_private_render_and_run_error_edges
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_ircheck_private_render_and_run_error_edges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from xdsl.dialects import arith
    from xdsl.dialects import func
    from xdsl.dialects.builtin import FunctionType, ModuleOp
    from xdsl.ir import Block, Region

    empty_block = Block(arg_types=[])
    empty_block.add_op(func.ReturnOp())
    empty_func = func.FuncOp("empty", FunctionType.from_lists([], []), Region(empty_block))
    second_empty_block = Block(arg_types=[])
    second_empty_block.add_op(func.ReturnOp())
    second_empty_func = func.FuncOp("empty2", FunctionType.from_lists([], []), Region(second_empty_block))
    npu_demo_empty_block = Block(arg_types=[])
    npu_demo_empty_block.add_op(func.ReturnOp())
    npu_demo_empty_func = func.FuncOp("empty3", FunctionType.from_lists([], []), Region(npu_demo_empty_block))

    with pytest.raises(ValueError, match="unsupported emitc target"):
        ircheck_module._render_emitc_text(empty_func, "bad")
    with pytest.raises(ValueError, match="target=cpu requires func.func input"):
        ircheck_module._render_emitc_text(ircheck_module.CheckDirective(kind="CHECK", text="x", line_no=1), "cpu")
    with pytest.raises(ValueError, match="target=cpu requires a module with exactly one top-level func.func"):
        ircheck_module._render_emitc_text(ModuleOp([empty_func, second_empty_func]), "cpu")
    with pytest.raises(ValueError, match="target=npu_demo requires a non-empty npu_demo-compatible func.func"):
        ircheck_module._render_emitc_text(ModuleOp([npu_demo_empty_func]), "npu_demo")
    assert ircheck_module._is_empty_npu_demo_func(empty_func) is True

    non_empty_block = Block(arg_types=[])
    non_empty_block.add_ops([arith.ConstantOp.from_int_and_width(0, 32), func.ReturnOp()])
    non_empty_func = func.FuncOp("non_empty", FunctionType.from_lists([], []), Region(non_empty_block))
    monkeypatch.setattr(sys.modules["kernel_gen.dsl.gen_kernel"], "gen_kernel", lambda obj, ctx: f"emit:{type(obj).__name__}:{ctx.target}")
    assert ircheck_module._render_emitc_text(non_empty_func, "cpu") == "emit:FuncOp:cpu"
    assert ircheck_module._render_emitc_text(ModuleOp([non_empty_func]), "npu_demo") == "emit:FuncOp:npu_demo"

    case = ircheck_module.IrcheckCase(
        compile_args="--pass no-op",
        checks=[],
        input_ir="builtin.module {}",
        source_path="case.ircheck",
    )
    dump_dir = tmp_path / "irdump"

    class _ExplodingParser:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def parse_module(self) -> object:
            raise RuntimeError("boom")

    monkeypatch.setattr(ircheck_module, "Parser", _ExplodingParser)
    monkeypatch.setattr(ircheck_module, "load_builtin_passes", lambda: None)
    parse_failure = ircheck_module._run_ircheck_case(case, dump_dir=dump_dir)
    assert parse_failure.exit_code == 2
    assert "failed to parse input ir" in (parse_failure.message or "")

    monkeypatch.setattr(ircheck_module, "Parser", lambda *_args, **_kwargs: type("P", (), {"parse_module": lambda self: ModuleOp([])})())
    monkeypatch.setattr(ircheck_module, "_normalize_ir", lambda _op: (_ for _ in ()).throw(RuntimeError("print input failed")))
    print_input_failure = ircheck_module._run_ircheck_case(case, dump_dir=dump_dir)
    assert print_input_failure.exit_code == 2
    assert "failed to print input" in (print_input_failure.message or "")

    normalize_calls = iter(["builtin.module {}", "builtin.module {}"])
    monkeypatch.setattr(ircheck_module, "_normalize_ir", lambda _op: next(normalize_calls))
    monkeypatch.setattr(ircheck_module, "_run_compile_step", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pass failed")))
    compile_failure = ircheck_module._run_ircheck_case(case, dump_dir=dump_dir)
    assert compile_failure.exit_code == 2
    assert "pass execution failed at step 1" in (compile_failure.message or "")
    assert (dump_dir / "01-before-failed-pass-no-op.mlir").exists()

    output_counter = {"count": 0}

    def _normalize_with_output_failure(_op: object) -> str:
        output_counter["count"] += 1
        if output_counter["count"] == 1:
            return "builtin.module {}"
        raise RuntimeError("print output failed")

    monkeypatch.setattr(ircheck_module, "_normalize_ir", _normalize_with_output_failure)
    monkeypatch.setattr(ircheck_module, "_run_compile_step", lambda *_args, **_kwargs: ModuleOp([]))
    output_failure = ircheck_module._run_ircheck_case(case, dump_dir=dump_dir)
    assert output_failure.exit_code == 2
    assert "failed to print output" in (output_failure.message or "")

    normalize_calls = iter(["builtin.module {}", "builtin.module {}"])
    monkeypatch.setattr(ircheck_module, "_normalize_ir", lambda _op: next(normalize_calls))
    monkeypatch.setattr(ircheck_module, "_render_emitc_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("emitc failed")))
    emitc_failure = ircheck_module._run_ircheck_case(case, dump_dir=dump_dir, emitc_target="cpu")
    assert emitc_failure.exit_code == 2
    assert "IrcheckEmitCError" in (emitc_failure.message or "")


# TC-IRCHECK-PARSE-017
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 ircheck parser / matcher / compile helper 的剩余边界。
# 使用示例: pytest -q test/tools/test_ircheck_parser.py -k test_ircheck_private_remaining_parser_match_and_compile_edges
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_parser.py
def test_ircheck_private_remaining_parser_match_and_compile_edges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from xdsl.context import Context
    from xdsl.dialects import func
    from xdsl.dialects.builtin import i32
    from xdsl.dialects.builtin import FunctionType, ModuleOp
    from xdsl.ir import Block, Region


    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid regex check$"):
        ircheck_module._tokenize_check_pattern(r"\[\[BROKEN:{reg}\][[FN]]")
    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid regex check$"):
        ircheck_module._tokenize_check_pattern("func [[NAME:]]")

    assert ircheck_module._contains_invalid_regex_literal_fragment(r"\[\[NAME:{reg}\]\]") is False
    assert ircheck_module._contains_invalid_regex_literal_fragment(r"\[\[NAME:{reg}") is False

    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid regex check$"):
        ircheck_module._compile_literal_fragment("{{}}")

    missing_result = ircheck_module.run_ircheck_file(str(tmp_path / "missing.ircheck"))
    assert missing_result.ok is False
    assert missing_result.exit_code == 2

    with pytest.raises(IrcheckParseError, match=r"^IrcheckParseError: invalid ircheck header$"):
        ircheck_module._split_ircheck_text_into_case_blocks(
            """// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
// -----"""
        )
    assert ircheck_module._split_ircheck_text_into_case_blocks("\n") == [
        ircheck_module.IrcheckCaseBlock(text="\n", start_line=1)
    ]

    empty_block = Block(arg_types=[])
    empty_block.add_op(func.ReturnOp())
    extra_block = Block(arg_types=[])
    extra_block.add_op(func.ReturnOp())
    multi_block_func = func.FuncOp("multi", FunctionType.from_lists([], []), Region([empty_block, extra_block]))
    arg_block = Block(arg_types=[i32])
    arg_block.add_op(func.ReturnOp())
    arg_func = func.FuncOp("with_arg", FunctionType.from_lists([i32], []), Region(arg_block))
    assert ircheck_module._is_empty_npu_demo_func(multi_block_func) is False
    assert ircheck_module._is_empty_npu_demo_func(arg_func) is False

    assert ircheck_module._parse_cli_args(["-irdump"]) is None
    assert ircheck_module._parse_name_and_options("tile={x= }") is None
    assert ircheck_module._parse_name_and_options("") is None

    class _FakeMatch:
        def group(self, index: int) -> str | None:
            groups = {1: "--pass", 2: None, 3: None, 4: None}
            return groups[index]

        def end(self) -> int:
            return 6

    class _FakePattern:
        def match(self, _text: str, _pos: int) -> _FakeMatch:
            return _FakeMatch()

    monkeypatch.setattr(ircheck_module.re, "compile", lambda _pattern: _FakePattern())
    assert ircheck_module._parse_compile_args("dummy") is None
    monkeypatch.undo()

    class _FakeModulePass(ircheck_module.ModulePass):
        name = "fake-module-pass"

        def apply(self, ctx: Context, op: ModuleOp) -> None:
            del ctx, op

    class _FakeLegacyPass(ircheck_module.Pass):
        name = "fake-legacy-pass"

        def run(self, op: object) -> str:
            del op
            return "bad"

    module = ModuleOp([])
    not_module = multi_block_func
    pass_step = ircheck_module.IrcheckCompileStep(kind="pass", name="fake", options={})
    pipeline_step = ircheck_module.IrcheckCompileStep(kind="pipeline", name="fake", options={})

    monkeypatch.setattr(ircheck_module, "build_registered_pass", lambda name, options: _FakeModulePass())
    with pytest.raises(TypeError, match="built pass requires builtin.module target"):
        ircheck_module._run_compile_step(Context(), not_module, pass_step)

    monkeypatch.setattr(ircheck_module, "build_registered_pass", lambda name, options: object())
    with pytest.raises(TypeError, match="built pass is not supported pass instance"):
        ircheck_module._run_compile_step(Context(), module, pass_step)

    monkeypatch.setattr(ircheck_module, "build_registered_pass", lambda name, options: _FakeLegacyPass())
    with pytest.raises(TypeError, match="pass/pipeline did not return xdsl Operation"):
        ircheck_module._run_compile_step(Context(), module, pass_step)

    monkeypatch.setattr(ircheck_module, "build_registered_pipeline", lambda name, options: object())
    with pytest.raises(TypeError, match="built pipeline is not PassManager instance"):
        ircheck_module._run_compile_step(Context(), module, pipeline_step)

    monkeypatch.setattr(
        ircheck_module,
        "render_operation_text",
        lambda value: 'builtin.module {\n  "kernel.img2col1d"() {axis = #builtin.int<3>}\n}',
    )
    normalized = ircheck_module._normalize_ir(module)
    assert "#builtin.int<3>" not in normalized
    assert 'axis = 3' in normalized

    assert ircheck_module._match_checks("builtin.module {}", [], source_path=None) == (True, None, None)

    next_only = [ircheck_module.CheckDirective(kind="CHECK-NEXT", text="func.return", line_no=1)]
    ok, failed, message = ircheck_module._match_checks("builtin.module {}", next_only, source_path=None)
    assert ok is False
    assert failed is next_only[0]
    assert "requires previous positive check" in (message or "")

    no_next_line = [
        ircheck_module.CheckDirective(kind="CHECK", text="builtin.module", line_no=1),
        ircheck_module.CheckDirective(kind="CHECK-NEXT", text="func.return", line_no=2),
    ]
    ok, failed, message = ircheck_module._match_checks("builtin.module {}", no_next_line, source_path=None)
    assert ok is False
    assert failed is no_next_line[1]
    assert "not found on next line" in (message or "")

    forbidden_between = [
        ircheck_module.CheckDirective(kind="CHECK", text="first", line_no=1),
        ircheck_module.CheckDirective(kind="CHECK-NOT", text="second", line_no=2),
        ircheck_module.CheckDirective(kind="CHECK", text="third", line_no=3),
    ]
    ok, failed, message = ircheck_module._match_checks("first\nsecond\nthird", forbidden_between, source_path=None)
    assert ok is False
    assert failed is forbidden_between[1]
    assert "CHECK-NOT matched forbidden text" in (message or "")
