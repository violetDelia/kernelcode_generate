"""DSL package entry.


功能说明:
- 汇总 DSL 包根公开入口。
- AST Node 类不从 `kernel_gen.dsl` 包根导出；需要节点类型时使用 `kernel_gen.dsl.ast`。
- 保持导出范围与 spec 定义一致。

API 列表:
- `parse_function(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> FunctionAST`

helper 清单:
- 无

使用示例:
- from kernel_gen.dsl import parse_function

关联文件:
- spec: spec/dsl/ast/__init__.md
- test: test/dsl/test_package.py
- 功能实现: kernel_gen/dsl/__init__.py
"""

from .ast import parse_function

__all__ = [
    "parse_function",
]
