"""mlir_gen package entry.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 对外暴露 build_func_op/build_func_op_from_ast/mlir_gen 等公开入口。
- 汇总解析环境、签名推导与 module 组装的兼容接口。

使用示例:
- from kernel_gen.dsl.mlir_gen import build_func_op, mlir_gen

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/__init__.py](kernel_gen/dsl/mlir_gen/__init__.py)
"""

from __future__ import annotations

from kernel_gen.dsl.ast import _parse_function_impl

from .function_builder import build_func_op, build_func_op_from_ast
from .module_builder import MlirGenModuleError, mlir_gen
from .parse_env import _build_parse_environment, _build_runtime_table_for_signature, _parse_function_with_env
from .signature import (
    _build_signature_types,
    _is_symbol_scalar_function,
    _symbol_expr_from_runtime_arg,
    _validate_return_type,
)

__all__ = [
    "MlirGenModuleError",
    "_build_parse_environment",
    "_build_runtime_table_for_signature",
    "_build_signature_types",
    "_is_symbol_scalar_function",
    "_parse_function_impl",
    "_parse_function_with_env",
    "_symbol_expr_from_runtime_arg",
    "_validate_return_type",
    "build_func_op",
    "build_func_op_from_ast",
    "mlir_gen",
]
