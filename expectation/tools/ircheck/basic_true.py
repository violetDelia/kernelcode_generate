"""ircheck 基础成功路径 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 定义 `ircheck` 的最小成功路径黑盒合同。
- 要求公开函数 `run_ircheck_text(...)` 能读取带 `COMPILE_ARGS:` / `CHECK:` / `CHECK-NOT:` / `CHECK-NEXT:` 的文本 case。
- 要求公开注册名 `no-op` 可用于工具自检；该 pass 运行后不得改写输入 IR。

使用示例:
- `PYTHONPATH=. python expectation/tools/ircheck/basic_true.py`

关联文件:
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/tools/test_ircheck_runner.py`](test/tools/test_ircheck_runner.py)
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
// CHECK-NOT: kernel.add
// CHECK: arith.constant 1 : i32
// CHECK-NEXT: func.return

builtin.module {
  func.func @main() {
    %0 = arith.constant 1 : i32
    func.return
  }
}
"""


def _run_case_1() -> None:
    result = run_ircheck_text(CASE_TEXT, source_path="expectation/tools/ircheck/basic_true.py")
    assert result.ok is True, f"expected ok=True, got ok={result.ok}, message={result.message!r}"
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.func @main" in result.actual_ir, "actual_ir must contain func.func @main"
    assert "arith.constant 1 : i32" in result.actual_ir, "actual_ir must contain arith.constant"
    assert result.failed_check is None, "successful ircheck must not report failed_check"
    assert result.message in (None, ""), f"successful ircheck must not report message, got {result.message!r}"


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _run_case_1)
    raise_if_failures("ircheck basic true expectation", failures)


if __name__ == "__main__":
    main()

