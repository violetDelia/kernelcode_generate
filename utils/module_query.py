"""Module query helpers.

创建者: 大哥大
最后一次更改: 大哥大

功能说明:
- 提供 has_callable 与 get_py_file_vars 工具。

使用示例:
- has_callable(str, "upper")
- get_py_file_vars("/path/to/file.py")

关联文件:
- spec: spec/utils/module_query.md
- test: test/utils/test_module_query.py
- 功能实现: utils/module_query.py
"""

from __future__ import annotations

from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import Any


def has_callable(cls: object, name: str) -> bool:
    """判断对象是否有可调用属性。"""
    return callable(getattr(cls, name, None))


def get_py_file_vars(py_file_path: str | Path) -> dict[str, Any]:
    """加载 python 文件并返回非 __ 前缀变量。"""
    path = Path(py_file_path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    if path.suffix != ".py":
        raise ValueError("py_file_path must be a .py file")

    module_name = f"_module_query_{path.stem}"
    loader = SourceFileLoader(module_name, str(path))
    module = ModuleType(module_name)
    loader.exec_module(module)

    result: dict[str, Any] = {}
    for name, value in module.__dict__.items():
        if name.startswith("__"):
            continue
        result[name] = value
    return result
