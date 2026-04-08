"""ircheck CHECK-NEXT 失败路径 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 定义 `ircheck` 在 `CHECK-NEXT:` 未命中下一行时的最小失败合同。
- 要求公开函数 `run_ircheck_text(...)` 返回 `ok=False`、`exit_code=1`，并暴露固定错误短语。
- 要求失败结果能指出失败的是哪一条 `CHECK-NEXT:` 指令。

使用示例:
- `PYTHONPATH=. python expectation/tools/ircheck/check_next_false.py`

关联文件:
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/tools/test_ircheck_matcher.py`](test/tools/test_ircheck_matcher.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.tools.ircheck import run_ircheck_text
from expectation.utils.case_runner import raise_if_failures, run_case

CASE_TEXT = """// COMPILE_ARGS: --pass no-op
// CHECK: func.func @main
// CHECK-NEXT: func.return

builtin.module {
  func.func @main() {
    %0 = arith.constant 1 : i32
    func.return
  }
}
"""


def _run_case_1() -> None:
    result = run_ircheck_text(
        CASE_TEXT,
        source_path="expectation/tools/ircheck/check_next_false.py",
    )
    assert result.ok is False, "CHECK-NEXT mismatch must return ok=False"
    assert result.exit_code == 1, f"expected exit_code=1, got {result.exit_code}"
    assert result.failed_check is not None, "failed CHECK-NEXT must report failed_check"
    assert result.failed_check.kind == "CHECK-NEXT", (
        f"expected failed kind CHECK-NEXT, got {result.failed_check.kind!r}"
    )
    assert result.failed_check.text == "func.return", (
        f"expected failed text 'func.return', got {result.failed_check.text!r}"
    )
    assert result.message is not None, "failed ircheck must expose message"
    assert "IrcheckMatchError: CHECK-NEXT not found on next line" in result.message, (
        f"unexpected message: {result.message!r}"
    )
    assert "arith.constant 1 : i32" in result.actual_ir, "actual_ir must expose the intervening line"


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _run_case_1)
    raise_if_failures("ircheck check-next false expectation", failures)


if __name__ == "__main__":
    main()

