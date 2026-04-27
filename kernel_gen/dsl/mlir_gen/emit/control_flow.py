"""Emit 结构节点处理。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 处理控制流结构节点，当前聚焦 `ForAST`。
- Assign/Return 在 AST 解析阶段已被折叠为表达式，不再作为独立节点进入 emit。

API 列表:
- `emit_for(node: ForAST, ctx: EmitContext) -> object`
- `emit_control_flow(node: object, ctx: EmitContext) -> object`

使用示例:
- loop_op = emit_for(for_ast, ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_control_flow.py](test/dsl/mlir_gen/emit/test_control_flow.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/control_flow.py](kernel_gen/dsl/mlir_gen/emit/control_flow.py)
"""

from __future__ import annotations

from kernel_gen.dsl.ast import ForAST

from .context import EmitContext


class LoweringError(ValueError):
    """当前文件内使用的控制流 emit 失败错误。"""

    def __init__(self, message: str, location: object | None = None) -> None:
        super().__init__(message)
        self.location = location


def emit_for(node: ForAST, ctx: EmitContext) -> object:
    """发射 `ForAST` 控制流节点。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅处理 `ForAST` 节点，交由 emit 入口完成 lowering。
    - 其余节点类型直接拒绝，避免控制流职责偏离。

    参数说明:
    - node: ForAST 循环节点。
    - ctx: EmitContext。

    返回说明:
    - 返回对应的 loop op 或循环体最后一个表达式结果。

    使用示例:
    - loop_op = emit_for(for_ast, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_control_flow.py](test/dsl/mlir_gen/emit/test_control_flow.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/control_flow.py](kernel_gen/dsl/mlir_gen/emit/control_flow.py)
    """
    if not isinstance(node, ForAST):
        raise LoweringError("emit_for expects ForAST", location=getattr(node, "location", None))
    from . import emit_mlir as public_emit_mlir

    return public_emit_mlir(node, ctx)


def emit_control_flow(node: object, ctx: EmitContext) -> object:
    """控制流节点统一入口。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一处理 ForAST 控制流入口。
    - 未覆盖的节点类型直接报错，避免隐式扩展。

    参数说明:
    - node: 控制流节点。
    - ctx: EmitContext。

    返回说明:
    - 返回 control flow op 或最后表达式结果。

    使用示例:
    - value = emit_control_flow(for_ast, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_control_flow.py](test/dsl/mlir_gen/emit/test_control_flow.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/control_flow.py](kernel_gen/dsl/mlir_gen/emit/control_flow.py)
    """
    if isinstance(node, ForAST):
        return emit_for(node, ctx)
    raise LoweringError("emit_control_flow only handles ForAST", location=getattr(node, "location", None))
