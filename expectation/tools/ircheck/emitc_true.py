"""ircheck emitc 成功路径 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 冻结 `ircheck` 在 `emitc` 成功路径下的最小公开合同。
- 要求 `run_ircheck_text(..., emitc_target="cpu")` 在 compile steps 之后匹配生成的源码文本，而不是继续匹配规范化 IR。
- 要求 CLI `-emitc{target=cpu}` 与 Python API 走同一条成功路径。

使用示例:
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py`

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
// CHECK: void main()
// CHECK-NEXT: }

builtin.module {
  func.func @main() {
    func.return
  }
}
"""


def _run_case_api_cpu() -> None:
    """验证 `run_ircheck_text(..., emitc_target="cpu")` 匹配生成源码。"""

    result = run_ircheck_text(
        CASE_TEXT,
        source_path="expectation/tools/ircheck/emitc_true.py#api_cpu",
        emitc_target="cpu",
    )
    assert result.ok is True, f"expected ok=True, got ok={result.ok}, message={result.message!r}"
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.failed_check is None, "successful emitc run must not report failed_check"
    assert result.message in (None, ""), f"successful emitc run must not report message, got {result.message!r}"
    assert result.actual_ir == "void main() {\n}", f"unexpected emitted source: {result.actual_ir!r}"


def _run_case_cli_cpu() -> None:
    """验证 CLI `-emitc{target=cpu}` 走相同成功链。"""

    with tempfile.TemporaryDirectory(prefix="ircheck-emitc-true-") as tmpdir:
        tmp_path = Path(tmpdir)
        case_file = tmp_path / "emitc_true.ircheck"
        case_file.write_text(CASE_TEXT, encoding="utf-8")

        env = dict(os.environ)
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else str(REPO_ROOT)
        )
        completed = subprocess.run(
            [sys.executable, "-m", "kernel_gen.tools.ircheck", "-emitc{target=cpu}", str(case_file)],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert completed.returncode == 0, (
            "emitc CLI must succeed for the cpu sample; "
            f"stdout={completed.stdout!r}, stderr={completed.stderr!r}"
        )
        assert completed.stdout.strip() == "true", f"unexpected stdout: {completed.stdout!r}"


def main() -> None:
    """运行本文件定义的全部 emitc 成功路径 case。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-API-CPU", _run_case_api_cpu)
    run_case(failures, "CASE-CLI-CPU", _run_case_cli_cpu)
    raise_if_failures("ircheck emitc true expectation", failures)


if __name__ == "__main__":
    main()
