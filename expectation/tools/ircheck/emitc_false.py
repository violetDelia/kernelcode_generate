"""ircheck emitc 失败路径 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 冻结 `ircheck` 在 `emitc` 模式下的最小失败合同。
- 要求不合法的 `emitc` CLI 参数继续走 `IrcheckCliError: invalid arguments` 前缀。
- 要求 `emitc_target="npu_demo"` 对普通单函数输入显式失败，并映射为 `IrcheckEmitCError: emit_c generation failed`。

使用示例:
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py`

关联文件:
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test:
  - [`test/tools/test_ircheck_runner.py`](test/tools/test_ircheck_runner.py)
  - [`test/tools/test_ircheck_cli.py`](test/tools/test_ircheck_cli.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
"""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.tools.ircheck import run_ircheck_text
from expectation.utils.case_runner import raise_if_failures, run_case

CASE_TEXT = """// COMPILE_ARGS: --pass no-op
// CHECK: unused

builtin.module {
  func.func @main() {
    func.return
  }
}
"""


def _run_case_api_npu_demo_rejects_single_func() -> None:
    """验证 `npu_demo` 目标对普通单函数输入显式失败。"""

    result = run_ircheck_text(
        CASE_TEXT,
        source_path="expectation/tools/ircheck/emitc_false.py#api_npu_demo",
        emitc_target="npu_demo",
    )
    assert result.ok is False, "npu_demo emitc on plain func must fail"
    assert result.exit_code == 2, f"expected exit_code=2, got {result.exit_code}"
    assert result.failed_check is None, "emitc generation failure must occur before failed_check is set"
    assert result.message is not None, "failed emitc run must expose message"
    assert result.message.startswith("IrcheckEmitCError: emit_c generation failed"), (
        f"unexpected message prefix: {result.message!r}"
    )


def _run_case_cli_rejects_missing_target() -> None:
    """验证 `-emitc` 缺少 `{target=...}` 时按 CLI 参数错误失败。"""

    with tempfile.TemporaryDirectory(prefix="ircheck-emitc-false-") as tmpdir:
        tmp_path = Path(tmpdir)
        case_file = tmp_path / "emitc_false.ircheck"
        case_file.write_text(CASE_TEXT, encoding="utf-8")

        env = dict(os.environ)
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else str(REPO_ROOT)
        )
        completed = subprocess.run(
            [sys.executable, "-m", "kernel_gen.tools.ircheck", "-emitc", str(case_file)],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert completed.returncode == 2, (
            "missing emitc target must fail with exit_code=2; "
            f"stdout={completed.stdout!r}, stderr={completed.stderr!r}"
        )
        stdout_lines = completed.stdout.splitlines()
        assert stdout_lines[:1] == ["false"], f"unexpected stdout: {completed.stdout!r}"
        assert len(stdout_lines) >= 2, f"stdout must include cli error prefix: {completed.stdout!r}"
        assert stdout_lines[1].startswith("IrcheckCliError: invalid arguments"), (
            f"unexpected cli error prefix: {completed.stdout!r}"
        )


def main() -> None:
    """运行本文件定义的全部 emitc 失败路径 case。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-API-NPU-DEMO-FAIL", _run_case_api_npu_demo_rejects_single_func)
    run_case(failures, "CASE-CLI-MISSING-TARGET", _run_case_cli_rejects_missing_target)
    raise_if_failures("ircheck emitc false expectation", failures)


if __name__ == "__main__":
    main()
