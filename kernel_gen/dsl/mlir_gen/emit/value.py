"""Emit value 共享逻辑。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 处理变量取值、字面量与 symbol.const/index operand 等基础 value 逻辑。
- 避免在此层直接构造 nn/dma family op。

使用示例:
- value = emit_value(ConstAST(1), ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_value.py](test/dsl/mlir_gen/emit/test_value.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/value.py](kernel_gen/dsl/mlir_gen/emit/value.py)
"""

from __future__ import annotations

from xdsl.ir import SSAValue

from kernel_gen.dsl.ast import ConstAST, ScalarArgAST, TensorAST, VarAST
from kernel_gen.dsl.emit_mlir import _const_symbol_int, _resolve_index_operand, emit_mlir as _emit_mlir

from .context import EmitContext, LoweringError


def emit_value(expr: object, ctx: EmitContext) -> object:
    """下沉基础 value 节点。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 ConstAST/ScalarArgAST/TensorAST/VarAST 作为基础值。
    - 其余节点类型直接拒绝，避免混入 family 语义。

    参数说明:
    - expr: value 节点。
    - ctx: EmitContext。

    返回说明:
    - 返回 SSAValue 或 op 结果。

    使用示例:
    - value = emit_value(ConstAST(1), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_value.py](test/dsl/mlir_gen/emit/test_value.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/value.py](kernel_gen/dsl/mlir_gen/emit/value.py)
    """
    if not isinstance(expr, (ConstAST, ScalarArgAST, TensorAST, VarAST)):
        raise LoweringError("emit_value only supports ConstAST/ScalarArgAST/TensorAST/VarAST", location=getattr(expr, "location", None))
    return _emit_mlir(expr, ctx)


def emit_symbol_const(value: int | ConstAST, ctx: EmitContext) -> SSAValue:
    """生成 `symbol.const` 的 SSA value。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一 `symbol.const` 的构造入口。
    - 仅接受整型常量，避免混入非数值类型。

    参数说明:
    - value: int 或 ConstAST(int)。
    - ctx: EmitContext。

    返回说明:
    - 返回 `!symbol.int<...>` SSAValue。

    使用示例:
    - const = emit_symbol_const(4, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_value.py](test/dsl/mlir_gen/emit/test_value.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/value.py](kernel_gen/dsl/mlir_gen/emit/value.py)
    """
    if isinstance(value, ConstAST):
        if not isinstance(value.value, int):
            raise LoweringError("symbol.const requires int literal", location=value.location)
        return _const_symbol_int(value.value, ctx, value.location)
    if not isinstance(value, int):
        raise LoweringError("symbol.const requires int literal", location=None)
    return _const_symbol_int(value, ctx, None)


def emit_index_operand(expr: object, ctx: EmitContext) -> SSAValue:
    """生成索引 operand 的 SSA value。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 将 int/ConstAST/VarAST 等索引表达式下沉为 SSA value。
    - 复用 emit 共享逻辑，不扩展到 helper/family 语义。

    参数说明:
    - expr: 索引表达式。
    - ctx: EmitContext。

    返回说明:
    - 返回可作为索引 operand 的 SSAValue。

    使用示例:
    - value = emit_index_operand(ConstAST(1), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_value.py](test/dsl/mlir_gen/emit/test_value.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/value.py](kernel_gen/dsl/mlir_gen/emit/value.py)
    """
    return _resolve_index_operand(expr, ctx, getattr(expr, "location", None))
