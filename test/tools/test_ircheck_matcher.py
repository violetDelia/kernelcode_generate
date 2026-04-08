"""ircheck matcher tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `kernel_gen/tools/ircheck.py` 的 matcher 语义：`CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 的子串匹配行为与失败口径。
- matcher 测试仅针对“规范化后的 IR 文本”进行 line-based 匹配，不依赖 xdsl 解析与 pass 执行链。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.tools.ircheck --cov-branch --cov-report=term-missing test/tools/test_ircheck_matcher.py`

使用示例:
- pytest -q test/tools/test_ircheck_matcher.py

关联文件:
- 功能实现: kernel_gen/tools/ircheck.py
- Spec 文档: spec/tools/ircheck.md
- 测试文件: test/tools/test_ircheck_matcher.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.tools.ircheck import CheckDirective, _match_checks


def _d(kind: str, text: str, line_no: int) -> CheckDirective:
    return CheckDirective(kind=kind, text=text, line_no=line_no)  # type: ignore[arg-type]


# TC-IRCHECK-MATCH-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 22:29:47 +0800
# 最近一次运行成功时间: 2026-04-08 22:29:47 +0800
# 功能说明: 验证 `CHECK:` 会从上一次 positive check 命中行之后继续查找。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_check_advances_search_position
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_check_advances_search_position() -> None:
    actual_ir = "\n".join(
        [
            "foo",
            "bar foo",
            "foo baz",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            _d("CHECK", "foo", 1),
            _d("CHECK", "foo baz", 2),
        ],
        source_path="inline.ir",
    )
    assert ok is True
    assert failed is None
    assert message is None


# TC-IRCHECK-MATCH-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 22:29:47 +0800
# 最近一次运行成功时间: 2026-04-08 22:29:47 +0800
# 功能说明: 验证 `CHECK:` 找不到时返回稳定错误短语前缀并指向失败指令。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_check_not_found
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_check_not_found() -> None:
    ok, failed, message = _match_checks(
        "a\nb\nc",
        [_d("CHECK", "does.not.exist", 1)],
        source_path="inline.ir",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK not found")


# TC-IRCHECK-MATCH-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 22:29:47 +0800
# 最近一次运行成功时间: 2026-04-08 22:29:47 +0800
# 功能说明: 验证 `CHECK-NEXT:` 必须命中上一条 positive check 的下一行，否则失败并给出稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_check_next_requires_next_line
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_check_next_requires_next_line() -> None:
    ok, failed, message = _match_checks(
        "a\nb\nc",
        [
            _d("CHECK", "a", 1),
            _d("CHECK-NEXT", "c", 2),
        ],
        source_path="inline.ir",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NEXT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NEXT not found on next line")


# TC-IRCHECK-MATCH-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 22:29:47 +0800
# 最近一次运行成功时间: 2026-04-08 22:29:47 +0800
# 功能说明: 验证 `CHECK-NOT:` 出现在第一条 positive check 之前时，禁止文本不得出现在文件开头到命中行之前。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_check_not_before_first_positive
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_check_not_before_first_positive() -> None:
    ok, failed, message = _match_checks(
        "forbid\nok",
        [
            _d("CHECK-NOT", "forbid", 1),
            _d("CHECK", "ok", 2),
        ],
        source_path="inline.ir",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NOT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")


# TC-IRCHECK-MATCH-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 22:29:47 +0800
# 最近一次运行成功时间: 2026-04-08 22:29:47 +0800
# 功能说明: 验证 `CHECK-NOT:` 位于最后一条 positive check 之后时，禁止文本不得出现在命中行之后。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_check_not_after_last_positive
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_check_not_after_last_positive() -> None:
    ok, failed, message = _match_checks(
        "ok\nforbid",
        [
            _d("CHECK", "ok", 1),
            _d("CHECK-NOT", "forbid", 2),
        ],
        source_path="inline.ir",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NOT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")


# TC-IRCHECK-MATCH-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 22:29:47 +0800
# 最近一次运行成功时间: 2026-04-08 22:29:47 +0800
# 功能说明: 验证 `CHECK-NOT:` 在相邻 positive check 的命中行边界上不触发（区间语义不含边界行）。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_check_not_excludes_boundary_lines
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_check_not_excludes_boundary_lines() -> None:
    ok, failed, message = _match_checks(
        "A forbid\nB",
        [
            _d("CHECK", "A", 1),
            _d("CHECK-NOT", "forbid", 2),
            _d("CHECK", "B", 3),
        ],
        source_path="inline.ir",
    )
    assert ok is True
    assert failed is None
    assert message is None

