"""DSL package entry.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 汇总 DSL AST、遍历与 MLIR 生成的公开入口。
- 保持导出范围与 spec 定义一致。

使用示例:
- from kernel_gen.dsl import parse_function, build_func_op

关联文件:
- spec: spec/dsl/ast.md
- spec: spec/dsl/ast_visitor.md
- spec: spec/dsl/emit_mlir.md
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
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
from .ast.visitor import AstVisitor, AstVisitorError
from .mlir_gen.emit import EmitContext, emit_mlir
from .mlir_gen import build_func_op, build_func_op_from_ast

__all__ = [
    "AstVisitor",
    "AstVisitorError",
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
