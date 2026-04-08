"""Legacy expectation entry (lowing -> lowering).

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 兼容旧路径 `expectation/pass/lowing/decompose_nn_softmax.py`。
- 转发执行到 `expectation/pass/lowering/decompose_nn_softmax.py`。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/decompose_nn_softmax.py`
- `PYTHONPATH=. python expectation/pass/lowering/decompose_nn_softmax.py`

关联文件:
- spec: `spec/pass/lowering/decompose_nn_softmax.md`
- test: `test/pass/test_decompose_nn_softmax.py`
- 功能实现: `expectation/pass/lowering/decompose_nn_softmax.py`
"""

from __future__ import annotations

import runpy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
runpy.run_path(
    str(REPO_ROOT / "expectation" / "pass" / "lowering" / "decompose_nn_softmax.py"),
    run_name="__main__",
)

