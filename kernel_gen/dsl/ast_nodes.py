"""DSL AST nodes legacy facade.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 兼容旧导入路径 `kernel_gen.dsl.ast_nodes`。
- 实际节点定义迁移至 `kernel_gen.dsl.ast.nodes`。

使用示例:
- from kernel_gen.dsl.ast_nodes import FunctionAST, BlockAST
- func_ast = FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))

关联文件:
- spec: spec/dsl/ast.md
- test: test/dsl/ast/test_parser.py
- 功能实现: kernel_gen/dsl/ast_nodes.py
"""

from __future__ import annotations

from kernel_gen.dsl.ast.nodes import *  # noqa: F401,F403
from kernel_gen.dsl.ast import nodes as _nodes

__all__ = [name for name in dir(_nodes) if not name.startswith("_")]
