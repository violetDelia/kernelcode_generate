"""emit_c npu_demo matmul expectation 复跑入口。

创建者: 金铲铲大作战
最后一次修改人: 金铲铲大作战
最后一次修改日期: 2026-04-20

功能说明:
- 从当前 worktree 预加载 `kernel_gen`，再执行仓根 `expectation.dsl.emit_c.npu_demo.kernel.matmul`。
- 让复跑命令稳定命中当前 build worktree 的实现，避免回退到仓根 `kernel_gen`。
- 支持 `--print-command` 输出可直接复用的命令行，便于任务记录与回报。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 python3 script/run_emitc_npu_demo_expectation.py`
- `python3 script/run_emitc_npu_demo_expectation.py --print-command`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- test: [`test/script/test_run_emitc_npu_demo_expectation.py`](test/script/test_run_emitc_npu_demo_expectation.py)
- 功能实现: [`script/run_emitc_npu_demo_expectation.py`](script/run_emitc_npu_demo_expectation.py)
"""

from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
MAIN_REPO_ROOT = WORKTREE_ROOT.parent
MODULE_NAME = "expectation.dsl.emit_c.npu_demo.kernel.matmul"


def _normalize_path(path_text: str) -> Path:
    return Path(path_text or ".").resolve()


def _prepend_path(path: Path) -> None:
    """把指定路径放到 `sys.path` 最前面，同时去重。"""

    resolved = path.resolve()
    sys.path[:] = [entry for entry in sys.path if _normalize_path(entry) != resolved]
    sys.path.insert(0, str(resolved))


def _pythonpath_value() -> str:
    value = f"{WORKTREE_ROOT}:{MAIN_REPO_ROOT}"
    extra = os.environ.get("PYTHONPATH")
    if extra:
        value = f"{value}:{extra}"
    return value


def print_command() -> None:
    """打印可直接复跑的命令行。"""

    script_path = WORKTREE_ROOT / "script/run_emitc_npu_demo_expectation.py"
    print(
        f"cd {WORKTREE_ROOT} && PYTHONDONTWRITEBYTECODE=1 "
        f"PYTHONPATH={_pythonpath_value()} python3 {script_path}"
    )


def main() -> None:
    """执行 `expectation.dsl.emit_c.npu_demo.kernel.matmul`，并优先使用当前 worktree 的 `kernel_gen`。"""

    parser = argparse.ArgumentParser(
        prog="run_emitc_npu_demo_expectation.py",
        description="Run expectation.dsl.emit_c.npu_demo with the current worktree kernel_gen.",
    )
    parser.add_argument("--print-command", action="store_true", help="print the reproducible command and exit")
    args = parser.parse_args()

    if args.print_command:
        print_command()
        return

    _prepend_path(MAIN_REPO_ROOT)
    _prepend_path(WORKTREE_ROOT)

    # 先把当前 worktree 的 kernel_gen 装进 sys.modules，再运行仓根 expectation。
    import kernel_gen  # noqa: F401

    runpy.run_module(MODULE_NAME, run_name="__main__")


if __name__ == "__main__":
    main()
