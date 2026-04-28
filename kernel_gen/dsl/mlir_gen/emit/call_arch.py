"""Emit arch family helper.

创建者: jcc你莫辜负
最后一次更改: 金铲铲大作战

功能说明:
- 收口 `emit_mlir(...)` 的 arch family 内部拆分实现，覆盖 query/get_dynamic_memory/launch_kernel。
- 当前文件不单独承载公开 API，对外公开入口仍是 `EmitContext(...)` / `emit_mlir(node, ctx)`。

API 列表:
- 无；当前文件仅提供 `emit_mlir(node, ctx)` 的 arch family 内部拆分实现。

使用示例:
- value = emit_mlir(ArchGetDynamicMemoryAST(space=MemorySpace.LM), ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_call_arch.py](test/dsl/mlir_gen/emit/test_call_arch.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_arch.py](kernel_gen/dsl/mlir_gen/emit/call_arch.py)
"""

from __future__ import annotations

from kernel_gen.dsl.ast import ArchGetDynamicMemoryAST, ArchLaunchKernelAST, ArchQueryAST

from .context import EmitContext


class LoweringError(ValueError):
    """当前文件内使用的 arch emit 失败错误。"""

    def __init__(self, message: str, location: object | None = None) -> None:
        super().__init__(message)
        self.location = location


def emit_arch_call(node: object, ctx: EmitContext) -> object:
    """发射 arch family AST。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 arch query / dynamic_memory / launch_kernel AST。
    - 统一复用现有 lowering，实现最小拆分。

    使用示例:
    - value = emit_arch_call(ArchQueryAST(query_name="get_thread_num"), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_call_arch.py](test/dsl/mlir_gen/emit/test_call_arch.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_arch.py](kernel_gen/dsl/mlir_gen/emit/call_arch.py)
    """

    if not isinstance(node, (ArchGetDynamicMemoryAST, ArchLaunchKernelAST, ArchQueryAST)):
        raise LoweringError("emit_arch_call only handles arch family AST nodes", location=getattr(node, "location", None))
    from . import emit_mlir as public_emit_mlir

    return public_emit_mlir(node, ctx)
