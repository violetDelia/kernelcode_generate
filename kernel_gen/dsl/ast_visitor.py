"""AST visitor for DSL.

创建者: 小李飞刀
最后一次更改: ChatGPT

功能说明:
- 提供 AST 访问器与访问器阶段错误类型。
- 访问器负责遍历 AST，并将节点发射交由 `emit_mlir.py` 处理。

使用示例:
- from kernel_gen.dsl.ast_visitor import AstVisitor, AstVisitorError
- visitor = AstVisitor()

关联文件:
- spec: spec/dsl/ast_visitor.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/ast_visitor.py
"""

from __future__ import annotations

from dataclasses import dataclass

from .ast import FunctionAST, SourceLocation
from .emit_mlir import EmitContext, _LoweringError, _expr_key, emit_mlir as emit_node_mlir


@dataclass(frozen=True)
class AstVisitorError(Exception):
    """AST 访问阶段错误，携带可定位信息。

    创建者: 小李飞刀
    最后一次更改: ChatGPT

    功能说明:
    - 统一包装解析、遍历与节点发射阶段的错误。

    使用示例:
    - raise AstVisitorError("Unsupported syntax", location)

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    message: str
    location: SourceLocation | None = None

    def __init__(
        self,
        message: str,
        location: SourceLocation | None = None,
    ) -> None:
        Exception.__init__(self, message)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "location", location)

    def __str__(self) -> str:
        return self.message


class AstVisitor:
    """DSL AST 遍历访问器。

    创建者: 小李飞刀
    最后一次更改: ChatGPT

    功能说明:
    - 按 AST 语句顺序分发节点发射。
    - 维护输入参数到 SSA value 的初始映射。

    使用示例:
    - visitor = AstVisitor()
    - visitor.visit_function(func_ast, ctx)

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = config or {}

    def visit_function(self, func_ast: FunctionAST, ctx: EmitContext) -> object:
        block_args = getattr(ctx.builder, "args", ())
        for index, item in enumerate(func_ast.inputs):
            if item.name in ctx.symbols:
                value = ctx.symbols[item.name]
            elif index < len(block_args):
                value = block_args[index]
                ctx.symbols[item.name] = value
            else:
                continue
            ctx._setdefault_cache(_expr_key(item), value)
            ctx.types.setdefault(_expr_key(item), value.type)
        return self.visit_block(func_ast.body, ctx)

    def visit_block(self, block_ast: object, ctx: EmitContext) -> object:
        statements = getattr(block_ast, "statements", None)
        if statements is None:
            raise AstVisitorError("Unsupported block node", location=getattr(block_ast, "location", None))
        last_value = None
        for stmt in statements:
            last_value = self.visit_stmt(stmt, ctx)
        return last_value

    def visit_stmt(self, stmt: object, ctx: EmitContext) -> object:
        try:
            return self.visit_expr(stmt, ctx)
        except _LoweringError as exc:
            raise AstVisitorError(str(exc), location=exc.location) from exc

    def visit_expr(self, expr: object, ctx: EmitContext) -> object:
        try:
            return emit_node_mlir(expr, ctx)
        except _LoweringError as exc:
            raise AstVisitorError(str(exc), location=exc.location) from exc
