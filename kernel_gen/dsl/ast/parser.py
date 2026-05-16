"""DSL AST parser public entry.


功能说明:
- 提供 `parse_function(...)` 公开入口。
- 解析实现由 `DslAstVisitor` 承接；本文件仅保留 `parse_function(...)` 需要的当前文件内 helper。

API 列表:
- `parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`

使用示例:
- func_ast = parse_function(kernel, lhs)

关联文件:
- spec: spec/dsl/ast/parser.md
- test: test/dsl/ast/test_parser.py
- 功能实现: kernel_gen/dsl/ast/parser.py
"""

from __future__ import annotations

import ast as py_ast
import inspect
import textwrap
from collections.abc import Callable
from typing import TypeAlias

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor
from kernel_gen.dsl.ast.nodes import FunctionAST, ModuleAST
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


DslRuntimeArg: TypeAlias = "Memory | SymbolDim | int | float | bool | str"
DslFunctionReturn: TypeAlias = "DslRuntimeArg | None"


def _parse_module(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleAST:
    """解析 Python DSL 函数为 `ModuleAST`。


    功能说明:
    - 当前文件内 helper，为 `parse_function(...)` 复用完整 module 解析流程。
    - 使用 `inspect.getsource(...)` 读取函数源码，再用 `DslAstVisitor.visit(...)` 生成 `ModuleAST`。

    使用示例:
    - module_ast = _parse_module(kernel, lhs, rhs)

    关联文件:
    - spec: spec/dsl/ast/parser.md
    - test: test/dsl/ast/test_parser.py
    - 功能实现: kernel_gen/dsl/ast/parser.py
    """

    if not callable(fn):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "parse_function expects a callable")
    source = textwrap.dedent(inspect.getsource(fn))
    tree = py_ast.parse(source)
    visitor = DslAstVisitor(fn, tuple(runtime_args))
    visitor.source = source
    module_ast = visitor.visit(tree)
    if not isinstance(module_ast, ModuleAST):
        raise KernelCodeError(ErrorKind.INTERNAL, ErrorModule.AST, "DslAstVisitor must return ModuleAST")
    return module_ast


def parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST:
    """解析 Python DSL 函数为 `FunctionAST`。


    功能说明:
    - 调用当前文件内 module 解析 helper 并返回 module 中唯一函数。

    使用示例:
    - func_ast = parse_function(kernel, lhs)

    关联文件:
    - spec: spec/dsl/ast/parser.md
    - test: test/dsl/ast/test_parser.py
    - 功能实现: kernel_gen/dsl/ast/parser.py
    """

    module_ast = _parse_module(fn, *runtime_args)
    if len(module_ast.functions) != 1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "parse_function expects exactly one function")
    return module_ast.functions[0]
