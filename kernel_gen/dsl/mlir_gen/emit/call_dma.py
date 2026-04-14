"""Emit dma family helper.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 收口 dma family 的 emit 入口，覆盖 alloc/copy/cast/view/reshape/flatten/free/read/write。
- 仅负责 dma 相关 AST 的分发，不承载 arch/symbol/nn 逻辑。

使用示例:
- value = emit_dma_call(DmaAllocAST(shape=[ConstAST(4)], dtype=NumericType.Float32), ctx)

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
from .core import emit_mlir as _emit_mlir

from .context import EmitContext, LoweringError

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
    return _emit_mlir(node, ctx)
