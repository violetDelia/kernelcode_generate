"""Emit 分发入口。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 提供 AST 节点到发射入口的统一路由。
- 仅负责分发，不承载 nn/dma/arch/symbol family 的具体细节。

使用示例:
- value = emit_mlir(node, ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/dispatch.py](kernel_gen/dsl/mlir_gen/emit/dispatch.py)
"""

from __future__ import annotations

from xdsl.ir import SSAValue

from kernel_gen.dsl.ast import PythonCalleeCallAST

from .context import EmitContext


class LoweringError(ValueError):
    """当前文件内使用的 dispatch 失败错误。"""

    def __init__(self, message: str, location: object | None = None) -> None:
        super().__init__(message)
        self.location = location


def emit_mlir(node: object, ctx: EmitContext) -> object:
    """分发 AST 节点的 emit 入口。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一对外暴露 emit_mlir 入口。
    - 路由到既有发射实现，保持行为一致。

    参数说明:
    - node: AST 节点。
    - ctx: EmitContext，上下文包含 builder/symbols/types。

    返回说明:
    - 表达式节点返回 SSAValue。
    - 语句节点返回 op 或 None（以具体实现为准）。

    使用示例:
    - value = emit_mlir(ConstAST(1), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/dispatch.py](kernel_gen/dsl/mlir_gen/emit/dispatch.py)
    """
    from . import emit_mlir as public_emit_mlir

    return public_emit_mlir(node, ctx)


def call_dispatch(node: PythonCalleeCallAST, ctx: EmitContext) -> SSAValue:
    """分发 Python callee 调用的 emit 入口。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅处理 `PythonCalleeCallAST`，确保 call 路径清晰可控。
    - 其余节点直接拒绝，避免混入 helper/表达式逻辑。

    参数说明:
    - node: PythonCalleeCallAST 调用节点。
    - ctx: EmitContext。

    返回说明:
    - 返回 call 的 SSAValue 结果。

    使用示例:
    - value = call_dispatch(call_ast, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/dispatch.py](kernel_gen/dsl/mlir_gen/emit/dispatch.py)
    """
    if not isinstance(node, PythonCalleeCallAST):
        raise LoweringError("call_dispatch expects PythonCalleeCallAST", location=getattr(node, "location", None))
    from . import emit_mlir as public_emit_mlir

    return public_emit_mlir(node, ctx)
