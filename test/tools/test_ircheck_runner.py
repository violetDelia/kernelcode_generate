"""ircheck runner tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 kernel_gen/tools/ircheck.py 的 run 行为：compile args 解析、pass/pipeline 执行、检查语义与退出码。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.tools.ircheck --cov-branch --cov-report=term-missing test/tools/test_ircheck_runner.py`

使用示例:
- pytest -q test/tools/test_ircheck_runner.py

关联文件:
- 功能实现: kernel_gen/tools/ircheck.py
- Spec 文档: spec/tools/ircheck.md
- 测试文件: test/tools/test_ircheck_runner.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

registry_module = importlib.import_module("kernel_gen.passes.registry")
_reset_registry_for_test = registry_module._reset_registry_for_test

from kernel_gen.tools.ircheck import run_ircheck_text


@pytest.fixture(autouse=True)
def _isolate_registry_state() -> None:
    _reset_registry_for_test()
    yield
    _reset_registry_for_test()


_SIMPLE_IR = """builtin.module {
  func.func @main() {
    func.return
  }
}
"""


# TC-IRCHECK-RUN-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 --pass no-op 可执行，并能通过 CHECK/CHECK-NEXT/CHECK-NOT 组合检查。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_pass_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_pass_ok() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module
// CHECK: func.func @main
// CHECK-NEXT: func.return
// CHECK-NOT: func.call

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
    assert "builtin.module" in result.actual_ir


# TC-IRCHECK-RUN-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证不支持的 COMPILE_ARGS 会返回 exit_code=2 与稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_unsupported_compile_args
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_unsupported_compile_args() -> None:
    text = f"""// COMPILE_ARGS: --unknown arg
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckCompileArgsError: unsupported compile args")


# TC-IRCHECK-RUN-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 CHECK 找不到时返回 exit_code=1 与稳定错误短语前缀，并给出 failed_check。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_check_not_found
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_check_not_found() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: does.not.exist

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 1
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK not found")
    assert result.failed_check is not None
    assert result.failed_check.kind == "CHECK"


# TC-IRCHECK-RUN-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 CHECK-NEXT 必须在下一行命中，否则返回稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_check_next_failure
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_check_next_failure() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: func.func @main
// CHECK-NEXT: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 1
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK-NEXT not found on next line")
    assert result.failed_check is not None
    assert result.failed_check.kind == "CHECK-NEXT"


# TC-IRCHECK-RUN-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 CHECK-NOT 在相邻 positive check 命中行之间命中会失败，并报告稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_check_not_failure_between_positives
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_check_not_failure_between_positives() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module
// CHECK-NOT: func.func
// CHECK: func.return

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 1
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")
    assert result.failed_check is not None
    assert result.failed_check.kind == "CHECK-NOT"


# TC-IRCHECK-RUN-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 --pipeline 可通过 pass registry 构造并执行。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_pipeline_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_pipeline_ok() -> None:
    text = f"""// COMPILE_ARGS: --pipeline no-op-pipeline
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
