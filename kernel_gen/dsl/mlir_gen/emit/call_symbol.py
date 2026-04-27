"""Emit symbol family helper.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 收口 symbol family 的 emit 入口，覆盖 symbol.to_float/get_dim/get_stride/symbol.for 相关 lowering。
- 仅负责 symbol 相关 AST 的分发，不承载 arch/dma/nn 逻辑。

API 列表:
- `emit_symbol_call(node: object, ctx: EmitContext) -> object`
- `emit_symbol_for(node: object, ctx: EmitContext) -> object`

使用示例:
- value = emit_symbol_call(SymbolToFloatAST(source=value), ctx)
- loop = emit_symbol_for(for_ast, ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_call_symbol.py](test/dsl/mlir_gen/emit/test_call_symbol.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_symbol.py](kernel_gen/dsl/mlir_gen/emit/call_symbol.py)
"""

from __future__ import annotations

from kernel_gen.dsl.ast import ForAST, SymbolToFloatAST, TensorAxisAccessAST

from .context import EmitContext


class LoweringError(ValueError):
    """当前文件内使用的 symbol emit 失败错误。"""

    def __init__(self, message: str, location: object | None = None) -> None:
        super().__init__(message)
        self.location = location


def emit_symbol_call(node: object, ctx: EmitContext) -> object:
    """发射 symbol family AST。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 `symbol.to_float`、`symbol.get_dim`、`symbol.get_stride` 相关 AST。
    - 统一复用现有 lowering，实现最小拆分。

    使用示例:
    - value = emit_symbol_call(SymbolToFloatAST(source=value), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_call_symbol.py](test/dsl/mlir_gen/emit/test_call_symbol.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_symbol.py](kernel_gen/dsl/mlir_gen/emit/call_symbol.py)
    """

    if not isinstance(node, (SymbolToFloatAST, TensorAxisAccessAST)):
        raise LoweringError("emit_symbol_call only handles symbol family AST nodes", location=getattr(node, "location", None))
    from . import emit_mlir as public_emit_mlir

    return public_emit_mlir(node, ctx)


def emit_symbol_for(node: object, ctx: EmitContext) -> object:
    """发射最终会 lowering 为 `symbol.for` 的循环 AST。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 `ForAST`，交由既有 lowering 生成 `symbol.for`/`scf.for`。
    - 用于把 symbol family 的循环入口从 control_flow 侧独立出来。

    使用示例:
    - loop = emit_symbol_for(for_ast, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_call_symbol.py](test/dsl/mlir_gen/emit/test_call_symbol.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/call_symbol.py](kernel_gen/dsl/mlir_gen/emit/call_symbol.py)
    """

    if not isinstance(node, ForAST):
        raise LoweringError("emit_symbol_for expects ForAST", location=getattr(node, "location", None))
    from . import emit_mlir as public_emit_mlir

    return public_emit_mlir(node, ctx)
