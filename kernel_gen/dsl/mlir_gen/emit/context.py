"""Emit 上下文入口。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 统一 emit 共享层使用的上下文对象与错误类型。
- 通过再导出减少上层对旧入口的直接依赖。

使用示例:
- from kernel_gen.dsl.mlir_gen.emit.context import EmitContext

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/context.py](kernel_gen/dsl/mlir_gen/emit/context.py)
"""

from __future__ import annotations

from kernel_gen.dsl.emit_mlir import EmitContext as EmitContext
from kernel_gen.dsl.emit_mlir import _LoweringError as LoweringError

__all__ = ["EmitContext", "LoweringError"]
