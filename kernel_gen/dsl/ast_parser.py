"""DSL AST parser legacy facade.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 兼容旧导入路径 `kernel_gen.dsl.ast_parser`。
- 实际解析实现迁移至 `kernel_gen.dsl.ast.parser`。

使用示例:
- from kernel_gen.dsl.ast_parser import parse_function
- func_ast = parse_function(kernel)

关联文件:
- spec: spec/dsl/ast.md
- test: test/dsl/ast/test_parser.py
- 功能实现: kernel_gen/dsl/ast_parser.py
"""

from __future__ import annotations

from kernel_gen.dsl.ast.parser import (  # noqa: F401
    AstParseError,
    _ParseFailure,
    _parse_function_impl,
    parse_function,
)

__all__ = [
    "AstParseError",
    "_ParseFailure",
    "_parse_function_impl",
    "parse_function",
]
