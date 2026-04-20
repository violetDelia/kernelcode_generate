"""Worktree Python bootstrap.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 在 Python 解释器启动阶段优先把当前 worktree 根目录放到 `sys.path` 最前面。
- 清理已缓存的 `kernel_gen` 相关模块，避免 pytest 或脚本复用主仓旧实现。
- 让从主仓根目录启动的测试进程也能稳定命中当前 worktree 的 `kernel_gen` 包。

使用示例:
- PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-tile-elewise-modulepass python3 -m pytest -q test/pass/test_lowering_tile_elewise.py

关联文件:
- spec: [ARCHITECTURE/plan/tile_pass_split_green_plan.md](ARCHITECTURE/plan/tile_pass_split_green_plan.md)
- test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
- 功能实现: [sitecustomize.py](sitecustomize.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parent
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))
else:
    sys.path.remove(str(WORKTREE_ROOT))
    sys.path.insert(0, str(WORKTREE_ROOT))

for module_name in list(sys.modules):
    if module_name == "kernel_gen" or module_name.startswith("kernel_gen."):
        del sys.modules[module_name]

# 预热 worktree 版 kernel_gen，避免后续由当前目录 `''` 重新捞到主仓同名包。
importlib.import_module("kernel_gen")
