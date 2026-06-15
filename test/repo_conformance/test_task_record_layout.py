"""Task record layout conformance tests.

功能说明:
- 扫描 tracked 任务记录和计划归档文件，防止旧目录形态重新进入仓库。

API 列表:
- 无业务公开 API；本文件只提供 pytest 测试入口。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_task_record_layout.py`

关联文件:
- spec: AGENTS.md
- standard: agents/standard/任务记录约定.md
"""

from __future__ import annotations

import subprocess
from pathlib import PurePosixPath


def test_tracked_task_records_use_year_week_layout() -> None:
    """Reject tracked task records in deprecated or year-only layouts.

    功能说明:
    - 禁止 `agents/task_records/`、`task_records/<YYYY>/*.md` 和
      `done_plan/<YYYY>/*.md` 进入 tracked diff。

    使用示例:
    - `pytest -q test/repo_conformance/test_task_record_layout.py`
    """

    output = subprocess.check_output(["git", "ls-files"], text=True)
    tracked_files = [line for line in output.splitlines() if line]
    bad: list[str] = []
    for path_text in tracked_files:
        path = PurePosixPath(path_text)
        parts = path.parts
        if path_text.startswith("agents/task_records/"):
            bad.append(f"{path_text}: deprecated agents/task_records root")
            continue
        task_prefix = ("agents", "codex-multi-agents", "log", "task_records")
        if parts[:4] != task_prefix:
            continue
        if len(parts) < 5:
            continue
        if parts[4] == "done_plan":
            year_dir = len(parts[5]) == 4 and parts[5].isdigit()
            if len(parts) == 7 and year_dir and path.suffix == ".md":
                bad.append(f"{path_text}: done_plan must include <YYYY>/<WW>/")
            week_dir = len(parts) >= 8 and len(parts[6]) == 2 and parts[6].isdigit()
            if len(parts) >= 8 and year_dir and not week_dir:
                bad.append(f"{path_text}: done_plan week must be two digits")
            continue
        year_dir = len(parts[4]) == 4 and parts[4].isdigit()
        if len(parts) == 6 and year_dir and path.suffix == ".md":
            bad.append(f"{path_text}: task record must include <YYYY>/<WW>/")
        week_dir = len(parts) >= 7 and len(parts[5]) == 2 and parts[5].isdigit()
        if len(parts) >= 7 and year_dir and not week_dir:
            bad.append(f"{path_text}: task record week must be two digits")

    assert bad == []
