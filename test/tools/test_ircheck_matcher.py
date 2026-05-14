"""ircheck matcher public contract tests.


功能说明:
- 通过 `run_ircheck_text(...)` 公开入口覆盖 CHECK / CHECK-NEXT / CHECK-NOT 的可观察语义。
- 不直连 `kernel_gen.tools.ircheck` 私有 matcher helper。

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

from kernel_gen.tools.ircheck import run_ircheck_text


def _ircheck_case(*, checks: list[str], input_ir: str) -> str:
    """组装最小 public ircheck case 文本。


    功能说明:
    - 为 `run_ircheck_text(...)` 统一生成 `--pass no-op` 的 inline case。

    使用示例:
    - text = _ircheck_case(checks=["// CHECK: builtin.module"], input_ir="builtin.module {}")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_matcher.py](test/tools/test_ircheck_matcher.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    lines = ["// COMPILE_ARGS: --pass no-op", *checks, "", input_ir]
    return "\n".join(lines)


# TC-IRCHECK-MATCH-001
# 测试目的: 验证 CHECK 继续从上一条 positive 命中行之后搜索。
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 示例: pytest -q test/tools/test_ircheck_matcher.py -k test_run_ircheck_text_reports_sequential_check_search_failure
def test_run_ircheck_text_reports_sequential_check_search_failure() -> None:
    result = run_ircheck_text(
        _ircheck_case(
            checks=[
                "// CHECK: beta",
                "// CHECK: alpha",
            ],
            input_ir="builtin.module {\n  \"test.first\"() : () -> ()\n  \"test.second\"() : () -> ()\n}",
        ),
        source_path="inline.ircheck",
    )
    assert result.ok is False
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK not found")


# TC-IRCHECK-MATCH-002
# 测试目的: 验证 CHECK-NEXT 只能命中下一行。
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 示例: pytest -q test/tools/test_ircheck_matcher.py -k test_run_ircheck_text_reports_check_next_failure
def test_run_ircheck_text_reports_check_next_failure() -> None:
    result = run_ircheck_text(
        _ircheck_case(
            checks=[
                "// CHECK: test.first",
                "// CHECK-NEXT: test.third",
            ],
            input_ir="builtin.module {\n  \"test.first\"() : () -> ()\n  \"test.second\"() : () -> ()\n}",
        ),
        source_path="inline.ircheck",
    )
    assert result.ok is False
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK-NEXT not found on next line")


# TC-IRCHECK-MATCH-003
# 测试目的: 验证 CHECK-NOT 在两个 positive 命中之间出现时失败。
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 示例: pytest -q test/tools/test_ircheck_matcher.py -k test_run_ircheck_text_reports_check_not_between_positives_failure
def test_run_ircheck_text_reports_check_not_between_positives_failure() -> None:
    result = run_ircheck_text(
        _ircheck_case(
            checks=[
                "// CHECK: test.first",
                "// CHECK-NOT: forbidden",
                "// CHECK: test.second",
            ],
            input_ir='builtin.module {\n  "test.first"() : () -> ()\n  "forbidden"() : () -> ()\n  "test.second"() : () -> ()\n}',
        ),
        source_path="inline.ircheck",
    )
    assert result.ok is False
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")


# TC-IRCHECK-MATCH-004
# 测试目的: 验证首条 positive 之前的 CHECK-NOT 仍约束起始区间。
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 示例: pytest -q test/tools/test_ircheck_matcher.py -k test_run_ircheck_text_reports_check_not_before_first_positive_failure
def test_run_ircheck_text_reports_check_not_before_first_positive_failure() -> None:
    result = run_ircheck_text(
        _ircheck_case(
            checks=[
                "// CHECK-NOT: forbidden",
                "// CHECK: test.first",
            ],
            input_ir='builtin.module {\n  "forbidden"() : () -> ()\n  "test.first"() : () -> ()\n}',
        ),
        source_path="inline.ircheck",
    )
    assert result.ok is False
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")


# TC-IRCHECK-MATCH-005
# 测试目的: 验证末尾 CHECK-NOT 约束最后一条 positive 命中后的区间。
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 示例: pytest -q test/tools/test_ircheck_matcher.py -k test_run_ircheck_text_reports_check_not_after_last_positive_failure
def test_run_ircheck_text_reports_check_not_after_last_positive_failure() -> None:
    result = run_ircheck_text(
        _ircheck_case(
            checks=[
                "// CHECK: test.first",
                "// CHECK-NOT: forbidden",
            ],
            input_ir='builtin.module {\n  "test.first"() : () -> ()\n  "forbidden"() : () -> ()\n}',
        ),
        source_path="inline.ircheck",
    )
    assert result.ok is False
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")


# TC-IRCHECK-MATCH-006
# 测试目的: 验证公开入口支持 `[[NAME:REGEX]]` 捕获与 `[[NAME]]` 复用。
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 示例: pytest -q test/tools/test_ircheck_matcher.py -k test_run_ircheck_text_supports_variable_capture_and_reuse
def test_run_ircheck_text_supports_variable_capture_and_reuse() -> None:
    result = run_ircheck_text(
        _ircheck_case(
            checks=[
                "// CHECK: %[[ID:{int}]] = arith.constant [[VAL:{int}]] : i32",
                "// CHECK-NEXT: %[[NEXT:{int}]] = arith.constant [[VAL]] : i32",
            ],
            input_ir=(
                "builtin.module {\n"
                "  func.func @main() {\n"
                "    %0 = arith.constant 7 : i32\n"
                "    %1 = arith.constant 7 : i32\n"
                "    func.return\n"
                "  }\n"
                "}"
            ),
        ),
        source_path="inline.ircheck",
    )
    assert result.ok is True
    assert result.message is None


# TC-IRCHECK-MATCH-007
# 测试目的: 验证公开入口支持 `[[NAME:{{REGEX}}]]` FileCheck 风格捕获正则。
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 示例: pytest -q test/tools/test_ircheck_matcher.py -k test_run_ircheck_text_supports_filecheck_wrapped_capture_regex
def test_run_ircheck_text_supports_filecheck_wrapped_capture_regex() -> None:
    result = run_ircheck_text(
        _ircheck_case(
            checks=[
                '// CHECK: "test.first"() {name = "[[NAME:{{[A-Za-z_][A-Za-z0-9_]*}}]]"} : () -> ()',
                '// CHECK-NEXT: "test.second"() {name = "[[NAME]]"} : () -> ()',
            ],
            input_ir=(
                "builtin.module {\n"
                '  "test.first"() {name = "TAlpha"} : () -> ()\n'
                '  "test.second"() {name = "TAlpha"} : () -> ()\n'
                "}"
            ),
        ),
        source_path="inline.ircheck",
    )
    assert result.ok is True
    assert result.message is None


# TC-IRCHECK-MATCH-008
# 测试目的: 验证公开入口按 SymbolExprAttr canonical 语义匹配 literal 中的旧符号表达文本。
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 示例: pytest -q test/tools/test_ircheck_matcher.py -k test_run_ircheck_text_matches_canonical_symbol_expr_literals
def test_run_ircheck_text_matches_canonical_symbol_expr_literals() -> None:
    result = run_ircheck_text(
        _ircheck_case(
            checks=[
                "// CHECK: %[[VAL:{reg}]] = symbol.add %[[ONE:{reg}]], %[[ARG:{reg}]] : !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<N>> -> !symbol.int<#symbol.expr<1 + N>>",
                "// CHECK-NEXT: %[[DIV:{reg}]] = symbol.floordiv %[[VAL]], %[[ARG]] : !symbol.int<#symbol.expr<1 + N>>, !symbol.int<#symbol.expr<N>> -> !symbol.int<#symbol.expr<(1 + N) // N>>",
                "// CHECK-NEXT: func.return %[[DIV]] : !symbol.int<#symbol.expr<(1 + N) // N>>",
            ],
            input_ir=(
                "builtin.module {\n"
                "  func.func @main(%arg0 : !symbol.int<#symbol.expr<N>>) -> !symbol.int<#symbol.expr<(N + 1) floordiv N>> {\n"
                "    %0 = symbol.const 1 : !symbol.int<#symbol.expr<1>>\n"
                "    %1 = symbol.add %0, %arg0 : !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<N>> -> !symbol.int<#symbol.expr<N + 1>>\n"
                "    %2 = symbol.floordiv %1, %arg0 : !symbol.int<#symbol.expr<N + 1>>, !symbol.int<#symbol.expr<N>> -> !symbol.int<#symbol.expr<(N + 1) floordiv N>>\n"
                "    func.return %2 : !symbol.int<#symbol.expr<(N + 1) floordiv N>>\n"
                "  }\n"
                "}"
            ),
        ),
        source_path="inline.ircheck",
    )
    assert result.ok is True
    assert result.message is None
