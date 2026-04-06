"""Python 层模块入口。

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 提供 `operation` 与 `dialect` 子模块的轻量入口。
- 为了避免 `import kernel_gen` 时立刻加载可选依赖（例如 `sympy`），此文件采用惰性转发：
  - 仅在访问顶层导出符号（如 `kernel_gen.add` / `kernel_gen.NnAddOp`）时才导入对应子模块。
  - 不影响直接使用全路径 import（如 `import kernel_gen.operation.nn as nn`）。

使用示例:
- import kernel_gen
- from kernel_gen.operation import add
- from kernel_gen.execute_engine import ExecutionEngine
- _ = add
- _ = ExecutionEngine(target="cpu")

关联文件:
- spec: spec/operation/nn.md
- spec: spec/dialect/nn.md
- spec: spec/execute_engine/execute_engine.md
- test: test/operation/test_operation_nn.py
- test: test/dialect/test_nn_dialect.py
- test: test/execute_engine/test_execute_engine_contract.py
- 功能实现: kernel_gen/operation/nn.py
- 功能实现: kernel_gen/dialect/nn.py
- 功能实现: kernel_gen/execute_engine/execution_engine.py
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_DIALECT_EXPORTS = frozenset(
    {
        "Nn",
        "NnAddOp",
        "NnEqOp",
        "NnGeOp",
        "NnGtOp",
        "NnLeOp",
        "NnLtOp",
        "NnMemorySpaceAttr",
        "NnMemoryType",
        "NnMulOp",
        "NnNeOp",
        "NnSubOp",
        "NnTrueDivOp",
    }
)
_OP_EXPORTS = frozenset(
    {
        "add",
        "sub",
        "mul",
        "truediv",
        "eq",
        "ne",
        "lt",
        "le",
        "gt",
        "ge",
    }
)

__all__ = [
    "Nn",
    "NnAddOp",
    "NnSubOp",
    "NnMulOp",
    "NnTrueDivOp",
    "NnEqOp",
    "NnNeOp",
    "NnLtOp",
    "NnLeOp",
    "NnGtOp",
    "NnGeOp",
    "NnMemorySpaceAttr",
    "NnMemoryType",
    "add",
    "sub",
    "mul",
    "truediv",
    "eq",
    "ne",
    "lt",
    "le",
    "gt",
    "ge",
]


def __getattr__(name: str) -> Any:  # pragma: no cover
    """模块级惰性转发钩子（PEP 562）。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 避免 `import kernel_gen` 触发重依赖导入（例如 dialect 依赖的 sympy）。
    - 当用户访问 `kernel_gen.<symbol>` 时再转发到 `kernel_gen.operation` 或 `kernel_gen.dialect`。

    使用示例:
    - import kernel_gen
    - _ = kernel_gen.add
    - _ = kernel_gen.NnAddOp

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_execute_engine_contract.py
    - 功能实现: kernel_gen/__init__.py
    """

    if name in _OP_EXPORTS:
        operation_pkg = import_module("kernel_gen.operation")
        return getattr(operation_pkg, name)
    if name in _DIALECT_EXPORTS:
        dialect_pkg = import_module("kernel_gen.dialect")
        return getattr(dialect_pkg, name)
    raise AttributeError(f"module kernel_gen has no attribute {name!r}")
