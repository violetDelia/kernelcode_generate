"""Compatibility entrypoint for emit_mlir spec path.

创建者: 摸鱼小分队
最后一次更改: 摸鱼小分队

功能说明:
- 提供 emit_mlir 相关入口的兼容路径。

使用示例:
- from kernel_gen.dsl.lowering import EmitContext, emit_mlir

关联文件:
- spec: spec/dsl/emit_mlir.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/emit_mlir.py
"""

from __future__ import annotations

from .emit_mlir import EmitContext, emit_mlir

__all__ = ["EmitContext", "emit_mlir"]
