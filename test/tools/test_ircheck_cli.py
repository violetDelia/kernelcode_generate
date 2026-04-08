"""ircheck CLI tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `python -m kernel_gen.tools.ircheck <case-file>` 的最小 CLI 合同：
  - 成功时仅输出 `true`；
  - 失败时首行输出 `false`，并包含失败指令与规范化后的实际 IR（actual_ir）。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.tools.ircheck --cov-branch --cov-report=term-missing test/tools/test_ircheck_cli.py`

使用示例:
- pytest -q test/tools/test_ircheck_cli.py

关联文件:
- 功能实现: kernel_gen/tools/ircheck.py
- Spec 文档: spec/tools/ircheck.md
- 测试文件: test/tools/test_ircheck_cli.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

registry_module = importlib.import_module("kernel_gen.passes.registry")
_reset_registry_for_test = registry_module._reset_registry_for_test

from kernel_gen.tools.ircheck import main


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


# TC-IRCHECK-CLI-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 23:13:57 +0800
# 最近一次运行成功时间: 2026-04-08 23:13:57 +0800
# 功能说明: 验证 CLI 匹配失败时 stdout 包含 failed_check 与 actual_ir，且退出码为 1。
# 使用示例: pytest -q test/tools/test_ircheck_cli.py -k test_ircheck_cli_match_failure_outputs_actual_ir
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_cli.py
def test_ircheck_cli_match_failure_outputs_actual_ir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = f"""// COMPILE_ARGS: --pass no-op
// CHECK: does.not.exist

{_SIMPLE_IR}"""
    case_path = tmp_path / "case.ircheck"
    case_path.write_text(content, encoding="utf-8")

    exit_code = main([str(case_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    stdout_lines = captured.out.splitlines()
    assert stdout_lines and stdout_lines[0] == "false"
    assert "IrcheckMatchError: CHECK not found" in captured.out
    assert "failed_check: CHECK" in captured.out
    assert "actual_ir:" in captured.out
    assert "func.func @main" in captured.out
