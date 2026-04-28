"""Emit dma family helper.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 收口 `emit_mlir(...)` 的 dma family 内部拆分实现，覆盖 alloc/copy/cast/view/reshape/flatten/free/read/write。
- 当前文件不单独承载公开 API，对外公开入口仍是 `EmitContext(...)` / `emit_mlir(node, ctx)`。

API 列表:
- 无；当前文件仅提供 `emit_mlir(node, ctx)` 的 dma family 内部拆分实现。

使用示例:
- value = emit_mlir(DmaAllocAST(shape=[ConstAST(4)], dtype=NumericType.Float32), ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_call_dma.py](test/dsl/mlir_gen/emit/test_call_dma.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_dma.py](kernel_gen/dsl/mlir_gen/emit/call_dma.py)
"""

from __future__ import annotations

from kernel_gen.dsl.ast import (
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    DmaViewAST,
    LoadAST,
    StoreAST,
)

from .context import EmitContext


class LoweringError(ValueError):
    """当前文件内使用的 dma emit 失败错误。"""

    def __init__(self, message: str, location: object | None = None) -> None:
        super().__init__(message)
        self.location = location

_DMA_AST_TYPES = (
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    DmaViewAST,
    LoadAST,
    StoreAST,
)


def emit_dma_call(node: object, ctx: EmitContext) -> object:
    """发射 dma family AST。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一承接 `alloc/copy/cast/view/reshape/flatten/free/read/write` 相关 AST。
    - 复用既有 `emit_mlir(...)` lowering，作为 dma family 的最小拆分入口。

    使用示例:
    - value = emit_dma_call(DmaViewAST(source=src, offset=[ConstAST(0)], size=[ConstAST(4)], stride=[ConstAST(1)]), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_call_dma.py](test/dsl/mlir_gen/emit/test_call_dma.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_dma.py](kernel_gen/dsl/mlir_gen/emit/call_dma.py)
    """

    if not isinstance(node, _DMA_AST_TYPES):
        raise LoweringError("emit_dma_call only handles dma family AST nodes", location=getattr(node, "location", None))
    from . import emit_mlir as public_emit_mlir

    return public_emit_mlir(node, ctx)
