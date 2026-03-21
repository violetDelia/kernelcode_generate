"""Compatibility entrypoint for mlir_gen spec path.

创建者: 摸鱼小分队
最后一次更改: 摸鱼小分队

功能说明:
- 提供 mlir_gen 相关入口的兼容路径。

使用示例:
- from python.dsl.mlir_gen import build_func_op

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from __future__ import annotations

from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast

__all__ = ["build_func_op", "build_func_op_from_ast"]
