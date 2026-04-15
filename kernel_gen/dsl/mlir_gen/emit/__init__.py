"""Emit 包根公开入口。

创建者: jcc你莫辜负
最后一次更改: 金铲铲大作战

功能说明:
- 收口 `kernel_gen.dsl.mlir_gen.emit` 包根的稳定公开集合。
- 包根仅暴露 `EmitContext` 与 `emit_mlir`；family/helper 入口需从对应子模块访问。

使用示例:
- from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/__init__.py](kernel_gen/dsl/mlir_gen/emit/__init__.py)
"""

from __future__ import annotations

from .context import EmitContext
from .dispatch import emit_mlir

__all__ = [
    "EmitContext",
    "emit_mlir",
]
