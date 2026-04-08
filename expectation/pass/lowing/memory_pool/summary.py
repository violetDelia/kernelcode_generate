"""Legacy expectation entry (lowing -> lowering).

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 兼容旧路径 `expectation/pass/lowing/memory_pool/summary.py`。
- 转发执行到 `expectation/pass/lowering/memory_pool/summary.py`。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/memory_pool/summary.py`
- `PYTHONPATH=. python expectation/pass/lowering/memory_pool/summary.py`

关联文件:
- spec: `spec/pass/lowering/memory_pool.md`
- test: `test/pass/test_memory_pool.py`
- 功能实现: `expectation/pass/lowering/memory_pool/summary.py`
"""

from __future__ import annotations

import runpy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
runpy.run_path(
    str(REPO_ROOT / "expectation" / "pass" / "lowering" / "memory_pool" / "summary.py"),
    run_name="__main__",
)

