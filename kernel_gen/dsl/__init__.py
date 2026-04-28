"""DSL package entry.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 汇总 DSL AST、遍历与 MLIR 生成的公开入口。
- 保持导出范围与 spec 定义一致。

API 列表:
- `BinaryExprAST(op: str, lhs: object, rhs: object, location: SourceLocation | None = None)`
- `BlockAST(statements: list[object], location: SourceLocation | None = None)`
- `CompareExprAST(op: str, lhs: object, rhs: object, location: SourceLocation | None = None)`
- `ConstAST(value: object, location: SourceLocation | None = None)`
- `Diagnostic(message: str, location: SourceLocation | None = None)`
- `FunctionAST(name: str, inputs: list[TensorAST | ScalarArgAST | PtrArgAST], outputs: list[TensorAST | ScalarArgAST], body: BlockAST, location: SourceLocation | None = None, source: str | None = None, py_ast: object | None = None, diagnostics: list[Diagnostic] = ..., has_explicit_return: bool = False, has_return_annotation: bool = False, returns_none: bool = False)`
- `ModuleAST(functions: list[FunctionAST])`
- `ScalarArgAST(name: str, value_type: type, is_symbolic: bool = False, location: SourceLocation | None = None)`
- `SourceLocation(line: int, column: int)`
- `TensorAST(name: str, memory: object, location: SourceLocation | None = None)`
- `VarAST(name: str, location: SourceLocation | None = None)`
- `AstVisitor(config: dict[str, object] | None = None)`
- `EmitContext(builder: Block, symbols: dict[str, object], types: dict[int, object], config: dict[str, object] | None = None)`
- `parse_function(fn: object) -> FunctionAST`
- `emit_mlir(node: object, ctx: EmitContext) -> object`
- `build_func_op(fn: Callable[..., object], *runtime_args: object, globals: dict[str, object] | None = None, builtins: dict[str, object] | object | None = None) -> func.FuncOp`
- `build_func_op_from_ast(func_ast: FunctionAST, runtime_args: tuple[object, ...] | list[object] | None = None) -> func.FuncOp`

helper 清单:
- 无

使用示例:
- from kernel_gen.dsl import parse_function, build_func_op

关联文件:
- spec: spec/dsl/ast/__init__.md
- spec: spec/dsl/ast/visitor.md
- spec: spec/dsl/emit_mlir.md
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/ast/test_visitor_integration.py
- 功能实现: kernel_gen/dsl/__init__.py
"""

from .ast import (
    BinaryExprAST,
    BlockAST,
    CompareExprAST,
    ConstAST,
    Diagnostic,
    FunctionAST,
    ModuleAST,
    ScalarArgAST,
    SourceLocation,
    TensorAST,
    VarAST,
    parse_function,
)
from .ast.visitor import AstVisitor
from .mlir_gen.emit import EmitContext, emit_mlir
from .mlir_gen import build_func_op, build_func_op_from_ast

__all__ = [
    "AstVisitor",
    "BinaryExprAST",
    "BlockAST",
    "CompareExprAST",
    "ConstAST",
    "Diagnostic",
    "EmitContext",
    "FunctionAST",
    "ModuleAST",
    "ScalarArgAST",
    "SourceLocation",
    "TensorAST",
    "VarAST",
    "build_func_op",
    "build_func_op_from_ast",
    "emit_mlir",
    "parse_function",
]
