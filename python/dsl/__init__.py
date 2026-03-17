"""DSL package entry.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 AST 前端入口与相关数据结构的统一导出。

使用示例:
- from python.dsl import visit_function, visit_to_nn_ir, emit_mlir

关联文件:
- spec: spec/dsl/ast_visitor.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: python/dsl/ast_visitor.py
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
)
from .ast_visitor import AstVisitorError, emit_mlir, visit_function, visit_to_nn_ir

__all__ = [
    "AstVisitorError",
    "BinaryExprAST",
    "BlockAST",
    "CompareExprAST",
    "ConstAST",
    "Diagnostic",
    "FunctionAST",
    "ModuleAST",
    "ScalarArgAST",
    "SourceLocation",
    "TensorAST",
    "VarAST",
    "emit_mlir",
    "visit_function",
    "visit_to_nn_ir",
]
