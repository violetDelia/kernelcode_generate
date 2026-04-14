"""Emit arch family helper.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 收口 arch family 的 emit 入口，覆盖 query/get_dynamic_memory/launch_kernel。
- 仅负责 arch 相关 AST 的分发，不承载 symbol/dma/nn 逻辑。

使用示例:
- value = emit_arch_call(ArchGetDynamicMemoryAST(space=MemorySpace.LM), ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_call_arch.py](test/dsl/mlir_gen/emit/test_call_arch.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_arch.py](kernel_gen/dsl/mlir_gen/emit/call_arch.py)
"""

from __future__ import annotations

from kernel_gen.dsl.ast import ArchGetDynamicMemoryAST, ArchLaunchKernelAST, ArchQueryAST
from .core import emit_mlir as _emit_mlir

from .context import EmitContext, LoweringError


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
    return _emit_mlir(node, ctx)
