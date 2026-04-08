"""ircheck matcher tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 kernel_gen/tools/ircheck.py 的检查语义实现：`CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:`
  在 line-based 子串匹配下的“顺序/相邻/区间”约束。

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


# TC-IRCHECK-MATCH-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证 CHECK 按“上一条 positive check 命中行之后”继续顺序匹配。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_sequential_check_search
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_sequential_check_search() -> None:
    actual_ir = "\n".join(
        [
            "alpha",
            "beta",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="beta", line_no=1),
            CheckDirective(kind="CHECK", text="alpha", line_no=2),
        ],
        source_path="inline.ircheck",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK not found")


# TC-IRCHECK-MATCH-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证 CHECK-NEXT 只能在“下一行”命中，否则必须返回稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_check_next_failure
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_check_next_failure() -> None:
    actual_ir = "\n".join(
        [
            "foo",
            "bar",
            "baz",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="foo", line_no=1),
            CheckDirective(kind="CHECK-NEXT", text="baz", line_no=2),
        ],
        source_path="inline.ircheck",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NEXT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NEXT not found on next line")


# TC-IRCHECK-MATCH-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证 CHECK-NOT 在相邻 positive check 命中行之间命中会失败并报告稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_check_not_between_positives_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_check_not_between_positives_fails() -> None:
    actual_ir = "\n".join(
        [
            "anchor1",
            "forbidden",
            "anchor2",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="anchor1", line_no=1),
            CheckDirective(kind="CHECK-NOT", text="forbidden", line_no=2),
            CheckDirective(kind="CHECK", text="anchor2", line_no=3),
        ],
        source_path="inline.ircheck",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NOT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")


# TC-IRCHECK-MATCH-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证首条 positive check 之前的 CHECK-NOT 会约束起始区间（从第 0 行到首次命中行之前）。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_check_not_before_first_positive_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_check_not_before_first_positive_fails() -> None:
    actual_ir = "\n".join(
        [
            "forbidden",
            "anchor",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK-NOT", text="forbidden", line_no=1),
            CheckDirective(kind="CHECK", text="anchor", line_no=2),
        ],
        source_path="inline.ircheck",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NOT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")


# TC-IRCHECK-MATCH-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证末尾 CHECK-NOT 会约束“最后一条 positive check 命中行之后到文件末尾”的区间。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_check_not_after_last_positive_fails
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_check_not_after_last_positive_fails() -> None:
    actual_ir = "\n".join(
        [
            "anchor",
            "forbidden",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="anchor", line_no=1),
            CheckDirective(kind="CHECK-NOT", text="forbidden", line_no=2),
        ],
        source_path="inline.ircheck",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NOT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")

