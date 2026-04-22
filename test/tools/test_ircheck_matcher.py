"""ircheck matcher tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 kernel_gen/tools/ircheck.py 的检查语义实现：
  - `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 的 FileCheck 风格“字面量 + 变量”约束。

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


# TC-IRCHECK-MATCH-005A
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-17 00:00:00 +0800
# 最近一次运行成功时间: 待本轮验证后补充
# 功能说明: 验证 CHECK 支持 `[[NAME:REGEX]]` 捕获、`[[NAME]]` 复用，且普通文本按字面量匹配无需写 `\.`。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_literal_check_supports_variable_capture_and_plain_dot
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_literal_check_supports_variable_capture_and_plain_dot() -> None:
    actual_ir = "\n".join(
        [
            "%0 = arith.constant 7 : i32",
            "%1 = arith.constant 7 : i32",
            "func.return",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="%[[ID:{int}]] = arith.constant [[VAL:{int}]] : i32", line_no=1),
            CheckDirective(kind="CHECK-NEXT", text="%[[NEXT:{int}]] = arith.constant [[VAL]] : i32", line_no=2),
        ],
        source_path="inline.ircheck",
    )
    assert ok is True
    assert failed is None
    assert message is None


# TC-IRCHECK-MATCH-005B
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-17 00:00:00 +0800
# 最近一次运行成功时间: 待本轮验证后补充
# 功能说明: 验证 CHECK-NOT 可引用前序 CHECK 捕获的变量。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_literal_check_not_can_reference_bound_variable
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_literal_check_not_can_reference_bound_variable() -> None:
    actual_ir = "\n".join(
        [
            "%0 = arith.constant 7 : i32",
            "%1 = arith.constant 8 : i32",
            "func.return",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="%[[ID:{int}]] = arith.constant [[VAL:{int}]] : i32", line_no=1),
            CheckDirective(kind="CHECK-NOT", text="%[[OTHER:{int}]] = arith.constant [[VAL]] : i32", line_no=2),
            CheckDirective(kind="CHECK", text="func.return", line_no=3),
        ],
        source_path="inline.ircheck",
    )
    assert ok is True
    assert failed is None
    assert message is None


# TC-IRCHECK-MATCH-006
# 创建者: 朽木露琪亚
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-17 00:00:00 +0800
# 最近一次运行成功时间: 待本轮验证后补充
# 功能说明: 验证 CHECK 与 CHECK-NEXT 支持 alias、变量捕获与引用。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_capture_and_reference_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_capture_and_reference_ok() -> None:
    actual_ir = "\n".join(
        [
            "%0 = arith.constant 7 : i32",
            "%1 = arith.constant 7 : i32",
            "func.return",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="%[[ID:{int}]] = arith.constant [[VAL:{int}]] : i32", line_no=1),
            CheckDirective(kind="CHECK-NEXT", text="%[[NEXT_ID:{int}]] = arith.constant [[VAL]] : i32", line_no=2),
        ],
        source_path="inline.ircheck",
    )
    assert ok is True
    assert failed is None
    assert message is None


# TC-IRCHECK-MATCH-006A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 15:05 +0800
# 最近一次运行成功时间: 2026-04-14 15:05 +0800
# 功能说明: 验证 `{reg}` 同时支持符号名与数字 SSA id，满足合同中的 memory/alloc 场景。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_reg_alias_matches_symbol_and_ssa_ids
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_reg_alias_matches_symbol_and_ssa_ids() -> None:
    actual_ir = "\n".join(
        [
            'func.func @main(%arg0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, N], [N, 1], f32, #nn.space<global>> {',
            '  %0 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>',
            '  func.return %0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>',
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(
                kind="CHECK",
                text=(
                    "func.func @main(%arg0 : !nn.memory<[[[M:{reg}]], [[N:{reg}]]], [[[N]], 1], "
                    "f32, #nn.space<global>>) -> !nn.memory<[[[M]], [[N]]], [[[N]], 1], "
                    "f32, #nn.space<global>> {"
                ),
                line_no=1,
            ),
            CheckDirective(
                kind="CHECK-NEXT",
                text=(
                    '%[[ALLOC:{reg}]] = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : '
                    "() -> !nn.memory<[[[M]], [[N]]], [[[N]], 1], f32, #nn.space<global>>"
                ),
                line_no=2,
            ),
            CheckDirective(
                kind="CHECK-NEXT",
                text="func.return %[[ALLOC]] : !nn.memory<[[[M]], [[N]]], [[[N]], 1], f32, #nn.space<global>>",
                line_no=3,
            ),
        ],
        source_path="inline.ircheck",
    )
    assert ok is True
    assert failed is None
    assert message is None


# TC-IRCHECK-MATCH-006B
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 待本轮验证后补充
# 最近一次运行成功时间: 待本轮验证后补充
# 功能说明: 验证 `{val}` 只匹配标识符名，适合 emit_c C++ 局部变量场景。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_val_alias_matches_identifiers
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_val_alias_matches_identifiers() -> None:
    actual_ir = "\n".join(
        [
            "void dma_alloc_case() {",
            "  Memory<GM, int32_t> v0 = alloc<GM, int32_t>({4, 8}, {8, 1});",
            "}",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="void dma_alloc_case() {", line_no=1),
            CheckDirective(
                kind="CHECK-NEXT",
                text="Memory<GM, int32_t> [[OUT:{val}]] = alloc<GM, int32_t>({4, 8}, {8, 1});",
                line_no=2,
            ),
            CheckDirective(kind="CHECK-NEXT", text="}", line_no=3),
        ],
        source_path="inline.ircheck",
    )
    assert ok is True
    assert failed is None
    assert message is None


# TC-IRCHECK-MATCH-007
# 创建者: 朽木露琪亚
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-17 00:00:00 +0800
# 最近一次运行成功时间: 待本轮验证后补充
# 功能说明: 验证带变量的 CHECK-NEXT 只能在下一行命中，否则返回稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_check_next_variable_failure
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_check_next_variable_failure() -> None:
    actual_ir = "\n".join(
        [
            "%0 = arith.constant 7 : i32",
            "func.return",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="%[[ID:{int}]] = arith.constant [[VAL:{int}]] : i32", line_no=1),
            CheckDirective(kind="CHECK-NEXT", text="%[[NEXT_ID:{int}]] = arith.constant [[VAL]] : i32", line_no=2),
        ],
        source_path="inline.ircheck",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NEXT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NEXT not found on next line")


# TC-IRCHECK-MATCH-008
# 创建者: 朽木露琪亚
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-17 00:00:00 +0800
# 最近一次运行成功时间: 待本轮验证后补充
# 功能说明: 验证 CHECK-NOT 可引用已有变量，并在禁止区间命中时报稳定错误短语。
# 使用示例: pytest -q test/tools/test_ircheck_matcher.py -k test_match_checks_check_not_variable_failure
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_matcher.py
def test_match_checks_check_not_variable_failure() -> None:
    actual_ir = "\n".join(
        [
            "%0 = arith.constant 7 : i32",
            "%1 = arith.constant 7 : i32",
            "func.return",
        ]
    )
    ok, failed, message = _match_checks(
        actual_ir,
        [
            CheckDirective(kind="CHECK", text="%[[ID:{int}]] = arith.constant [[VAL:{int}]] : i32", line_no=1),
            CheckDirective(kind="CHECK-NOT", text="%[[NEXT_ID:{int}]] = arith.constant [[VAL]] : i32", line_no=2),
            CheckDirective(kind="CHECK", text="func.return", line_no=3),
        ],
        source_path="inline.ircheck",
    )
    assert ok is False
    assert failed is not None
    assert failed.kind == "CHECK-NOT"
    assert message is not None
    assert message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")
