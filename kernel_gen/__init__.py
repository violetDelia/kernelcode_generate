"""Python 层模块入口。


功能说明:
- 提供 `operation` 与 `dialect` 子模块的轻量入口。
- 为了避免 `import kernel_gen` 时立刻加载可选依赖（例如 `sympy`），此文件采用惰性转发：
  - 仅在访问顶层导出符号（如 `kernel_gen.add` / `kernel_gen.NnAddOp`）时才导入对应子模块。
  - 不影响直接使用全路径 import（如 `import kernel_gen.operation.nn as nn`）。
- 当调用方显式启用 `PYTHONDONTWRITEBYTECODE=1` 且未设置外部 `PYTHONPYCACHEPREFIX` 时，为当前进程
  与后续子进程安装进程唯一 pycache prefix；若继承的是本项目自动生成的父进程 prefix，则按当前
  进程重新分配，避免 full expectation 这类长顺序运行读取或共享既有 `__pycache__` 后出现解释器级
  随机崩溃。

API 列表:
- `__getattr__(name: str) -> Any`
- `add(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `sub(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `mul(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `truediv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `eq(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `ne(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `lt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `le(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `gt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `ge(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `class Nn`
- `class NnAddOp`
- `class NnSubOp`
- `class NnMulOp`
- `class NnTrueDivOp`
- `class NnEqOp`
- `class NnNeOp`
- `class NnLtOp`
- `class NnLeOp`
- `class NnGtOp`
- `class NnGeOp`
- `class NnMemorySpaceAttr`
- `class NnMemoryType`

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
- test: test/operation/nn/test_package.py
- test: test/dialect/test_nn.py
- test: test/execute_engine/test_contract.py
- 功能实现: kernel_gen/operation/nn/__init__.py
- 功能实现: kernel_gen/dialect/nn.py
- 功能实现: kernel_gen/execute_engine/compiler.py
"""

from __future__ import annotations

import os
import sys
from importlib import import_module
from typing import Any

_PYCACHE_PREFIX_ENV = "PYTHONPYCACHEPREFIX"
_DONT_WRITE_BYTECODE_ENV = "PYTHONDONTWRITEBYTECODE"
_MANAGED_PYCACHE_PREFIX = "/tmp/kernelcode_generate_pycache_"

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


def _is_managed_pycache_prefix(prefix: str) -> bool:
    """判断 pycache prefix 是否由当前包自动生成。


    功能说明:
    - 识别 `/tmp/kernelcode_generate_pycache_<pid>` 形式的自动隔离前缀。
    - 用于区分调用方显式提供的外部 `PYTHONPYCACHEPREFIX` 与 full expectation 父进程继承下来的
      自动前缀。

    使用示例:
    - if _is_managed_pycache_prefix(prefix): ...

    关联文件:
    - spec: ARCHITECTURE/plan/full_expectation_runner_stability_green_plan.md
    - test: test/test_kernel_gen_package.py
    - 功能实现: kernel_gen/__init__.py
    """

    if not prefix.startswith(_MANAGED_PYCACHE_PREFIX):
        return False
    return prefix[len(_MANAGED_PYCACHE_PREFIX) :].isdigit()


def _install_pycache_read_isolation() -> None:
    """为禁写 bytecode 的进程安装 pycache 读取隔离。


    功能说明:
    - 仅在调用方已设置 `PYTHONDONTWRITEBYTECODE` 且未显式设置外部 `PYTHONPYCACHEPREFIX` 时生效。
    - 使用进程唯一的 `/tmp/kernelcode_generate_pycache_<pid>` 前缀，避免读取仓库或 site-packages
      中既有 `__pycache__`。
    - full expectation 父进程生成的自动前缀被子进程继承时，子进程会重新分配当前 pid 前缀，避免
      多个 case 子进程共享同一个 prefix。
    - 不创建目录；在禁写 bytecode 场景下，Python 不会写入新的 `.pyc`。

    使用示例:
    - `PYTHONDONTWRITEBYTECODE=1 python -c "import kernel_gen"`

    关联文件:
    - spec: ARCHITECTURE/plan/full_expectation_runner_stability_green_plan.md
    - test: test/test_kernel_gen_package.py
    - 功能实现: kernel_gen/__init__.py
    """

    if not os.environ.get(_DONT_WRITE_BYTECODE_ENV):
        return
    current_prefix = os.environ.get(_PYCACHE_PREFIX_ENV)
    if current_prefix and not _is_managed_pycache_prefix(current_prefix):
        return
    prefix = f"/tmp/kernelcode_generate_pycache_{os.getpid()}"
    os.environ[_PYCACHE_PREFIX_ENV] = prefix
    sys.pycache_prefix = prefix


_install_pycache_read_isolation()


def __getattr__(name: str) -> Any:  # pragma: no cover
    """模块级惰性转发钩子（PEP 562）。


    功能说明:
    - 避免 `import kernel_gen` 触发重依赖导入（例如 dialect 依赖的 sympy）。
    - 当用户访问 `kernel_gen.<symbol>` 时再转发到 `kernel_gen.operation` 或 `kernel_gen.dialect`。

    使用示例:
    - import kernel_gen
    - _ = kernel_gen.add
    - _ = kernel_gen.NnAddOp

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_contract.py
    - 功能实现: kernel_gen/__init__.py
    """

    if name in _OP_EXPORTS:
        operation_pkg = import_module("kernel_gen.operation")
        return getattr(operation_pkg, name)
    if name in _DIALECT_EXPORTS:
        dialect_pkg = import_module("kernel_gen.dialect")
        return getattr(dialect_pkg, name)
    raise AttributeError(f"module kernel_gen has no attribute {name!r}")
