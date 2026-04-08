"""symbol_variable pytest shared configuration.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 统一把仓库根目录加入 `sys.path`，保证从任意工作目录运行 pytest 都能导入 `kernel_gen.*`。
- 仅承载测试侧通用配置，不引入额外业务语义。

使用示例:
- `pytest -q test/symbol_variable`

关联文件:
- Spec 文档: [`spec/symbol_variable/README.md`](spec/symbol_variable/README.md)
- 测试文件: [`test/symbol_variable`](test/symbol_variable)
- 功能实现: [`test/symbol_variable/conftest.py`](test/symbol_variable/conftest.py)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SYMPY_GMPY", "0")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
