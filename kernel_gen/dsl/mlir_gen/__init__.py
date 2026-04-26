"""mlir_gen package entry.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 对外暴露 build_func_op/build_func_op_from_ast/mlir_gen 等公开入口。
- 汇总解析环境、签名推导与 module 组装的兼容接口。

API 列表:
- MlirGenModuleError(reason: str)
- build_func_op(fn, *runtime_args)
- build_func_op_from_ast(func_ast, runtime_args=None, config=None)
- mlir_gen(fn, *runtime_args, config=None)

使用示例:
- from kernel_gen.dsl.mlir_gen import build_func_op, mlir_gen

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/__init__.py](kernel_gen/dsl/mlir_gen/__init__.py)
"""

from __future__ import annotations

from .function_builder import build_func_op, build_func_op_from_ast
from .module_builder import MlirGenModuleError, mlir_gen

__all__ = [
    "MlirGenModuleError",
    "build_func_op",
    "build_func_op_from_ast",
    "mlir_gen",
]
