"""AST visitor for DSL.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 AST 访问器，访问阶段失败统一抛出 `KernelCodeError(module="ast")`。
- 访问器负责遍历 AST，并将节点发射交由 `emit_mlir` 处理。

API 列表:
- `AstVisitor(config: dict[str, object] | None = None)`
- `AstVisitor.register(node_type: type, method_name: str) -> None`
- `AstVisitor.visit(node: object, ctx: EmitContext) -> object`
- `AstVisitor.visit_function(func_ast: FunctionAST, ctx: EmitContext) -> object`
- `AstVisitor.visit_block(block_ast: object, ctx: EmitContext) -> object`
- `AstVisitor.visit_stmt(stmt: object, ctx: EmitContext) -> object`
- `AstVisitor.visit_expr(expr: object, ctx: EmitContext) -> object`

使用示例:
- from kernel_gen.dsl.ast.visitor import AstVisitor
- visitor = AstVisitor()

关联文件:
- spec: spec/dsl/ast/visitor.md
- test: test/dsl/ast/test_visitor.py
- 功能实现: kernel_gen/dsl/ast/visitor.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from typing import TYPE_CHECKING

from kernel_gen.dsl.ast import BlockAST, FunctionAST

if TYPE_CHECKING:
    from kernel_gen.dsl.mlir_gen.emit import EmitContext

class AstVisitor:
    """DSL AST 遍历访问器。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按 AST 语句顺序分发节点发射。
    - 维护输入参数到 SSA value 的初始映射。

    使用示例:
    - visitor = AstVisitor()
    - visitor.visit_function(func_ast, ctx)

    关联文件:
    - spec: spec/dsl/ast/visitor.md
    - test: test/dsl/ast/test_visitor.py
    - 功能实现: kernel_gen/dsl/ast/visitor.py
    """

    _registry: dict[type, str] = {
        FunctionAST: "visit_function",
        BlockAST: "visit_block",
    }

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = config or {}

    @classmethod
    def register(cls, node_type: type, method_name: str) -> None:
        cls._registry[node_type] = method_name

    def visit(self, node: object, ctx: EmitContext) -> object:
        handler_name = self._registry.get(type(node))
        if not handler_name:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, 
                "Unsupported AST node",
                location=getattr(node, "location", None),
            )
        handler = getattr(self, handler_name, None)
        if handler is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, 
                "Unsupported AST node",
                location=getattr(node, "location", None),
            )
        return handler(node, ctx)

    def visit_function(self, func_ast: FunctionAST, ctx: EmitContext) -> object:
        from kernel_gen.dsl.mlir_gen.emit import emit_mlir as emit_node_mlir

        block_args = getattr(ctx.builder, "args", ())
        for index, item in enumerate(func_ast.inputs):
            if item.name not in ctx.symbols:
                if index >= len(block_args):
                    continue
                ctx.symbols[item.name] = block_args[index]
            emit_node_mlir(item, ctx)
        return self.visit_block(func_ast.body, ctx)

    def visit_block(self, block_ast: object, ctx: EmitContext) -> object:
        statements = getattr(block_ast, "statements", None)
        if statements is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "Unsupported block node", location=getattr(block_ast, "location", None))
        last_value = None
        for stmt in statements:
            last_value = self.visit_stmt(stmt, ctx)
        return last_value

    def visit_stmt(self, stmt: object, ctx: EmitContext) -> object:
        try:
            return self.visit_expr(stmt, ctx)
        except KernelCodeError:
            raise
        except ValueError as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, str(exc), location=getattr(exc, "location", None)) from exc

    def visit_expr(self, expr: object, ctx: EmitContext) -> object:
        from kernel_gen.dsl.mlir_gen.emit import emit_mlir as emit_node_mlir

        try:
            return emit_node_mlir(expr, ctx)
        except KernelCodeError:
            raise
        except ValueError as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, str(exc), location=getattr(exc, "location", None)) from exc
