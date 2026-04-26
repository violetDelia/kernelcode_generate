"""测试包入口。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 为测试用例补齐包路径，避免标准库同名模块导致导入混淆。
- 在 worktree 中运行测试时补齐 `kernel_gen.common` 的模块搜索路径。

使用示例:
- pytest -q test/pass/nn_lowering/select.py

关联文件:
- spec: spec/pass/lowering/nn_lowering/spec.md
- test: test/pass/nn_lowering/select.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = REPO_ROOT.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if (MAIN_ROOT / "kernel_gen" / "common").exists():
    import kernel_gen

    main_kernel_gen = str(MAIN_ROOT / "kernel_gen")
    if main_kernel_gen not in kernel_gen.__path__:
        kernel_gen.__path__.append(main_kernel_gen)
