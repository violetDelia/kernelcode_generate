"""DSL AST plugin facade.


功能说明:
- 暴露 DSL AST builtin 注册 API。
- 导入本包时加载 NN / DMA / Arch / Kernel builtin 注册表。

API 列表:
- `BuiltinCall(source: ast.Call, dsl_name: str, ast_node: type | None, args: list[BuiltinArgument], kwargs: dict[str, BuiltinArgument], location: SourceLocation, launch_extents: list[BuiltinArgument] | None = None)`
- `BuiltinEntry(dsl_name: str, op: BuiltinOperation, ast_node: type | None, builder: BuiltinBuilder)`
- `dsl_builtin(op: BuiltinOperation, ast_node: type[T]) -> Callable[[Callable[[BuiltinCall], T]], Callable[[BuiltinCall], T]]`
- `external_builtin(func: BuiltinOperation, name: str | None = None) -> Callable[[BuiltinBuilder], BuiltinBuilder]`
- `lookup_builtin(op: BuiltinOperation) -> BuiltinEntry | None`
- `all_builtin_names() -> set[str]`

使用示例:
- from kernel_gen.dsl.ast.plugin import lookup_builtin
- assert lookup_builtin(relu) is not None

关联文件:
- spec: spec/dsl/ast/plugin/__init__.md
- test: test/dsl/ast/plugin/test_package.py
- 功能实现: kernel_gen/dsl/ast/plugin/__init__.py
"""

from __future__ import annotations

from .registry import BuiltinCall, BuiltinEntry, all_builtin_names, dsl_builtin, external_builtin, lookup_builtin

# Import registration modules for side effects.
from . import arch as _arch
from . import dma as _dma
from . import kernel as _kernel
from . import nn as _nn

__all__ = [
    "BuiltinEntry",
    "BuiltinCall",
    "dsl_builtin",
    "external_builtin",
    "lookup_builtin",
    "all_builtin_names",
]
