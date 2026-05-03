"""DSL AST builtin registry.


功能说明:
- 提供 DSL AST parser 使用的 builtin 注册表。
- `dsl_builtin(...)` 用于注册 DSL operation 与 AST 节点的一一对应关系。
- `external_builtin(...)` 用于注册允许下沉为 Python callee 的外部函数。
- 注册表按实际 operation 对象 identity 查询，不按字符串名称查询。
- `@dsl_builtin(op, AstNode)` 的 builder 必须返回声明的精确 `AstNode` 类型。

API 列表:
- `BuiltinCall(source: ast.Call, dsl_name: str, ast_node: type | None, args: list[BuiltinArgument], kwargs: dict[str, BuiltinArgument], location: SourceLocation, launch_extents: list[BuiltinArgument] | None = None)`
- `BuiltinEntry(dsl_name: str, op: BuiltinOperation, ast_node: type | None, builder: BuiltinBuilder)`
- `dsl_builtin(op: BuiltinOperation, ast_node: type[T]) -> Callable[[Callable[[BuiltinCall], T]], Callable[[BuiltinCall], T]]`
- `external_builtin(func: BuiltinOperation, name: str | None = None) -> Callable[[BuiltinBuilder], BuiltinBuilder]`
- `lookup_builtin(op: BuiltinOperation) -> BuiltinEntry | None`
- `all_builtin_names() -> set[str]`

使用示例:
- from kernel_gen.dsl.ast.plugin import dsl_builtin, lookup_builtin
- entry = lookup_builtin(relu)

关联文件:
- spec: spec/dsl/ast/plugin/registry.md
- test: test/dsl/ast/plugin/test_registry.py
- 功能实现: kernel_gen/dsl/ast/plugin/registry.py
"""

from __future__ import annotations

import ast as py_ast
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import TypeAlias, TypeVar

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.nodes import DSLNode, SourceLocation
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


_AstNodeT = TypeVar("_AstNodeT")
BuiltinArgument: TypeAlias = (
    "DSLNode | Memory | MemorySpace | NumericType | SymbolDim | list[BuiltinArgument] | "
    "tuple[BuiltinArgument, ...] | int | float | bool | str | type | None"
)
BuiltinResult: TypeAlias = "DSLNode | BuiltinArgument"
BuiltinOperation: TypeAlias = "Callable[..., BuiltinResult]"
BuiltinBuilder: TypeAlias = "Callable[[BuiltinCall], BuiltinResult]"


@dataclass(frozen=True)
class BuiltinCall:
    """DSL builtin 显式调用数据。


    功能说明:
    - 承载 `DslAstVisitor.visit_Call(...)` 已解析出的调用信息。
    - 替代在 Python `ast.Call` 对象上动态挂载 `_kg_*` 字段的旧桥。

    使用示例:
    - BuiltinCall(source=node, dsl_name="add", ast_node=NnAddAST, args=[lhs, rhs], kwargs={}, location=loc)

    关联文件:
    - spec: spec/dsl/ast/plugin/registry.md
    - test: test/dsl/ast/plugin/test_registry.py
    - 功能实现: kernel_gen/dsl/ast/plugin/registry.py
    """

    source: py_ast.Call
    dsl_name: str
    ast_node: type | None
    args: list[BuiltinArgument]
    kwargs: dict[str, BuiltinArgument]
    location: SourceLocation
    launch_extents: list[BuiltinArgument] | None = None


@dataclass(frozen=True)
class BuiltinEntry:
    """DSL builtin 注册项。


    功能说明:
    - 保存显示名称、源 operation、目标 AST 节点与 builder。
    - `dsl_name` 只用于诊断与 AST 元信息，不作为注册表查询 key。

    使用示例:
    - BuiltinEntry("relu", relu, NnReluAST, builder)

    关联文件:
    - spec: spec/dsl/ast/parser.md
    - test: test/dsl/ast/plugin/test_registry.py
    - 功能实现: kernel_gen/dsl/ast/plugin/registry.py
    """

    dsl_name: str
    op: BuiltinOperation
    ast_node: type | None
    builder: BuiltinBuilder


_REGISTRY: dict[int, BuiltinEntry] = {}
_AST_NODE_MAP: dict[type, BuiltinOperation] = {}


def dsl_builtin(
    op: BuiltinOperation,
    ast_node: type[_AstNodeT],
) -> Callable[[Callable[[BuiltinCall], _AstNodeT]], Callable[[BuiltinCall], _AstNodeT]]:
    """注册 DSL operation builtin。


    功能说明:
    - 注册 `id(op) -> BuiltinEntry`。
    - 诊断显示名从 operation 对象 `__name__` 推断，不提供手写名称覆盖。
    - 同一 operation 对象不得重复注册到不同 builder。
    - 同一 AST 节点不得绑定到多个 DSL operation。
    - builder 必须返回 `ast_node` 声明的精确 AST 类型，不能返回其他 AST 或其子类。

    使用示例:
    - @dsl_builtin(nn.relu, NnReluAST)
    - def build_relu(node): ...

    关联文件:
    - spec: spec/dsl/ast/parser.md
    - test: test/dsl/ast/plugin/test_registry.py
    - 功能实现: kernel_gen/dsl/ast/plugin/registry.py
    """

    def decorator(builder: Callable[[BuiltinCall], _AstNodeT]) -> Callable[[BuiltinCall], _AstNodeT]:
        try:
            dsl_name = op.__name__
        except AttributeError:
            class_name = type(op).__name__
            if class_name.startswith("_") and class_name.endswith("Builder"):
                class_name = class_name[1:-7]
            chars: list[str] = []
            for index, char in enumerate(class_name):
                if char.isupper() and index > 0:
                    chars.append("_")
                chars.append(char.lower())
            dsl_name = "".join(chars)
        op_id = id(op)
        existing = _REGISTRY.get(op_id)
        if existing is not None and existing.op is op and existing.ast_node is ast_node:
            return builder
        if existing is not None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, f"dsl_builtin: operation '{dsl_name}' already registered")
        if ast_node in _AST_NODE_MAP and _AST_NODE_MAP[ast_node] is not op:
            previous = _AST_NODE_MAP[ast_node]
            try:
                previous_name = previous.__name__
            except AttributeError:
                previous_name = type(previous).__name__
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.AST,
                f"dsl_builtin: ast_node {ast_node.__name__} already bound to "
                f"'{previous_name}', cannot also bind to '{dsl_name}'",
            )
        @wraps(builder)
        def checked_builder(node: BuiltinCall) -> _AstNodeT:
            result = builder(node)
            if type(result) is not ast_node:
                actual_name = type(result).__name__
                expected_name = ast_node.__name__
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.AST,
                    f"dsl_builtin: operation '{dsl_name}' builder returned {actual_name}, expected {expected_name}",
                )
            return result

        _REGISTRY[op_id] = BuiltinEntry(dsl_name, op, ast_node, checked_builder)
        _AST_NODE_MAP[ast_node] = op
        return builder

    return decorator


def external_builtin(
    func: BuiltinOperation,
    name: str | None = None,
) -> Callable[[BuiltinBuilder], BuiltinBuilder]:
    """注册外部 Python callable builtin。


    功能说明:
    - 注册可被 parser 识别的外部 callable。
    - 外部 callable 不绑定专用 AST 节点。
    - 注册表按 `func` 对象 identity 查询，不按 `name` 字符串查询。

    使用示例:
    - @external_builtin(math.sqrt)
    - def build_sqrt(node): ...

    关联文件:
    - spec: spec/dsl/ast/parser.md
    - test: test/dsl/ast/plugin/test_registry.py
    - 功能实现: kernel_gen/dsl/ast/plugin/registry.py
    """

    def decorator(builder: BuiltinBuilder) -> BuiltinBuilder:
        dsl_name = name
        if dsl_name is None:
            inferred_name = getattr(func, "__name__", None)
            if not isinstance(inferred_name, str) or not inferred_name:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "builtin registry value must provide name or __name__")
            dsl_name = inferred_name
        func_id = id(func)
        existing = _REGISTRY.get(func_id)
        if existing is not None and existing.op is func and existing.ast_node is None and existing.builder == builder:
            return builder
        if existing is not None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, f"external_builtin: operation '{dsl_name}' already registered")
        _REGISTRY[func_id] = BuiltinEntry(dsl_name, func, None, builder)
        return builder

    return decorator


def lookup_builtin(op: BuiltinOperation) -> BuiltinEntry | None:
    """查询 builtin 注册项。


    功能说明:
    - 按实际 operation 对象 identity 返回注册项；不存在时返回 `None`。
    - 字符串名称不是注册表 key。

    使用示例:
    - entry = lookup_builtin(relu)

    关联文件:
    - spec: spec/dsl/ast/parser.md
    - test: test/dsl/ast/plugin/test_registry.py
    - 功能实现: kernel_gen/dsl/ast/plugin/registry.py
    """

    entry = _REGISTRY.get(id(op))
    if entry is not None and entry.op is op:
        return entry
    return None


def all_builtin_names() -> set[str]:
    """返回已注册 builtin 的显示名称集合。


    功能说明:
    - 仅暴露诊断用名称集合，不暴露内部注册表。
    - 注册表仍按 operation 对象 identity 查询。

    使用示例:
    - names = all_builtin_names()

    关联文件:
    - spec: spec/dsl/ast/plugin/registry.md
    - test: test/dsl/ast/plugin/test_registry.py
    - 功能实现: kernel_gen/dsl/ast/plugin/registry.py
    """

    return {entry.dsl_name for entry in _REGISTRY.values()}
