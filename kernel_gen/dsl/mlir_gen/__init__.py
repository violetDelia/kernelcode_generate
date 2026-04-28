"""mlir_gen package entry.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 对外暴露 `build_func_op`、`build_func_op_from_ast` 与 `mlir_gen` 公开入口。
- 只承接 mlir_gen family 的稳定 package-root 导出，不顺手重导出下划线 helper 或 gen_kernel API。

API 列表:
- `build_func_op(fn: Callable[..., object], *runtime_args: object, globals: dict[str, object] | None = None, builtins: dict[str, object] | object | None = None) -> func.FuncOp`
- `build_func_op_from_ast(func_ast: FunctionAST, runtime_args: tuple[object, ...] | list[object] | None = None) -> func.FuncOp`
- `mlir_gen(fn: Callable[..., object], *runtime_args: object, globals: dict[str, object] | None = None, builtins: dict[str, object] | object | None = None) -> ModuleOp`

helper 清单:
- 无

使用示例:
- from kernel_gen.dsl.mlir_gen import build_func_op, mlir_gen

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/__init__.py](kernel_gen/dsl/mlir_gen/__init__.py)
"""

from __future__ import annotations

from .function_builder import build_func_op, build_func_op_from_ast
from .module_builder import mlir_gen

__all__ = [
    "build_func_op",
    "build_func_op_from_ast",
    "mlir_gen",
]
