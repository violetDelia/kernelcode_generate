"""DMA alloc root compatibility expectation.

创建者: 榕
最后一次更改: 金铲铲大作战

功能说明:
- 作为根目录兼容入口，复用 `expectation/operation/dma/alloc.py` 的 alloc expectation 语义。
- 避免在 `expectation/alloc.py` 与 `expectation/operation/dma/alloc.py` 间重复维护同一组断言。

使用示例:
- python expectation/alloc.py

关联文件:
- spec: spec/operation/dma.md
- test: test/operation/test_operation_dma.py
- 功能实现: expectation/operation/dma/alloc.py
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path = [
    search_path
    for search_path in sys.path
    if Path(search_path or ".").resolve() != SCRIPT_DIR
]

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 通过导入语义权威文件执行同一组 alloc expectation 断言，保持 root 入口兼容。
import_module("expectation.operation.dma.alloc")
