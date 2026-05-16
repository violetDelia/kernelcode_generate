"""AST MLIR generation public entry.


功能说明:
- 定义 `plan/ast/mlir_gen.py` 口径下唯一公开入口。
- `mlir_gen(...)` 固定为当前文件内 module 解析后执行 `ModuleAST.emit_mlir(ctx, None)`。

API 列表:
- `mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`

使用示例:
- from kernel_gen.dsl.ast.mlir_gen import mlir_gen
- module = mlir_gen(fn, *runtime_args)

关联文件:
- spec: [spec/dsl/ast/mlir_gen.md](spec/dsl/ast/mlir_gen.md)
- test: [test/dsl/ast/test_mlir_gen.py](test/dsl/ast/test_mlir_gen.py)
- 功能实现: [kernel_gen/dsl/ast/mlir_gen.py](kernel_gen/dsl/ast/mlir_gen.py)
"""

from __future__ import annotations

import ast as py_ast
import inspect
import textwrap
from collections.abc import Callable
from typing import TypeAlias

from xdsl.dialects.builtin import ModuleOp

from kernel_gen.core.context import build_default_context
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.dsl_ast import DslAstVisitor
from kernel_gen.dsl.ast.nodes import ModuleAST
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

__all__ = ["mlir_gen"]

DslRuntimeArg: TypeAlias = "Memory | SymbolDim | int | float | bool | str"
DslFunctionReturn: TypeAlias = "DslRuntimeArg | None"


def _parse_module_for_mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleAST:
    """解析 Python DSL 函数为 `ModuleAST`。


    功能说明:
    - 当前文件内 helper，服务 `mlir_gen(...)` 的完整 module 解析需求。
    - 不调用 `parser.py` 的私有 helper，避免跨文件非公开 API 依赖。

    使用示例:
    - `_parse_module_for_mlir_gen(kernel, lhs, rhs)`
    """

    source = textwrap.dedent(inspect.getsource(fn))
    tree = py_ast.parse(source)
    visitor = DslAstVisitor(fn, tuple(runtime_args))
    visitor.source = source
    module_ast = visitor.visit(tree)
    if not isinstance(module_ast, ModuleAST):
        raise KernelCodeError(ErrorKind.INTERNAL, ErrorModule.AST, "DslAstVisitor must return ModuleAST")
    return module_ast


def mlir_gen(
    fn: Callable[..., DslFunctionReturn],
    *runtime_args: DslRuntimeArg,
) -> ModuleOp:
    """从 Python 根函数生成 `builtin.module`。


    功能说明:
    - 公开闭环固定为当前文件解析 `ModuleAST` 后执行 `emit_mlir(ctx, None)`。
    - `ctx` 由本入口创建并传入，AST emit 公共接口不接受空 Context。
    - 不接收公开 `globals` / `builtins` / `config` 字典；解析环境由 parser 和公开运行时参数统一承接。

    使用示例:
    - module = mlir_gen(main, Memory([4], NumericType.Float32))

    关联文件:
    - spec: [spec/dsl/ast/mlir_gen.md](spec/dsl/ast/mlir_gen.md)
    - test: [test/dsl/ast/test_mlir_gen.py](test/dsl/ast/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/ast/mlir_gen.py](kernel_gen/dsl/ast/mlir_gen.py)
    """

    expected_arg_count = len(inspect.signature(fn).parameters)
    if len(runtime_args) < expected_arg_count:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.MLIR_GEN,
            f"mlir_gen requires explicit runtime args for {fn.__name__}: expected {expected_arg_count}, got {len(runtime_args)}",
        )
    ctx = build_default_context()
    return _parse_module_for_mlir_gen(fn, *runtime_args).emit_mlir(ctx, None)
