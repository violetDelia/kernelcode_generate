"""AST visitor facade.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 兼容旧导入路径 `kernel_gen.dsl.ast_visitor`。
- 实际实现迁移至 `kernel_gen.dsl.ast.visitor`。

使用示例:
- from kernel_gen.dsl.ast_visitor import AstVisitor, AstVisitorError
- visitor = AstVisitor()

关联文件:
- spec: spec/dsl/ast_visitor.md
- test: test/dsl/ast/test_visitor.py
- 功能实现: kernel_gen/dsl/ast_visitor.py
"""

from __future__ import annotations

from kernel_gen.dsl.ast.visitor import AstVisitor, AstVisitorError

__all__ = ["AstVisitor", "AstVisitorError"]
