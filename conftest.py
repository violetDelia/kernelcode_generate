"""Worktree test bootstrap.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 确保本 worktree 下的 pytest 先从当前 worktree 导入 `kernel_gen`，避免误用父仓旧实现。
- 在测试收集开始前清理已加载的 `kernel_gen` 相关模块，保证导入路径可复现。

使用示例:
- pytest -q test/pass/test_pass_manager.py

关联文件:
- spec: [ARCHITECTURE/plan/selected_passes_xdsl_modulepass_refactor_green_plan.md](ARCHITECTURE/plan/selected_passes_xdsl_modulepass_refactor_green_plan.md)
- test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
- 功能实现: [conftest.py](conftest.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parent
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

for module_name in list(sys.modules):
    if module_name == "kernel_gen" or module_name.startswith("kernel_gen."):
        del sys.modules[module_name]

# 重新预热 worktree 版包，确保后续测试收集期导入命中本目录实现。
importlib.import_module("kernel_gen.passes.lowering")
