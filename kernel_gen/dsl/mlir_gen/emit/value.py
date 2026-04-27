"""Emit value 共享逻辑。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 处理变量取值、字面量与 symbol.const/index operand 等基础 value 逻辑。
- 避免在此层直接构造 nn/dma family op。

API 列表:
- `emit_value(expr: object, ctx: EmitContext) -> object`
- `emit_symbol_const(value: int | ConstAST, ctx: EmitContext) -> SSAValue`
- `emit_index_operand(expr: object, ctx: EmitContext) -> SSAValue`

helper 清单:
- `_lookup_public_symbol(name: str, ctx: EmitContext, location: object | None) -> SSAValue`
- `_coerce_index_operand(value: SSAValue, ctx: EmitContext, location: object | None) -> SSAValue`

使用示例:
- value = emit_value(ConstAST(1), ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_value.py](test/dsl/mlir_gen/emit/test_value.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/value.py](kernel_gen/dsl/mlir_gen/emit/value.py)
"""

from __future__ import annotations

from xdsl.dialects import arith
from xdsl.dialects.builtin import IndexType, IntegerType
from xdsl.ir import SSAValue

from kernel_gen.dialect.symbol import SymbolConstOp, SymbolIterType, SymbolValueType
from kernel_gen.dsl.ast import ConstAST, ScalarArgAST, TensorAST, VarAST

from .context import EmitContext


class LoweringError(ValueError):
    """当前文件内使用的基础 value emit 失败错误。"""

    def __init__(self, message: str, location: object | None = None) -> None:
        super().__init__(message)
        self.location = location


def _lookup_public_symbol(name: str, ctx: EmitContext, location: object | None) -> SSAValue:
    """从公开上下文符号表读取 SSAValue。"""

    value = ctx.symbols.get(name)
    if not isinstance(value, SSAValue):
        raise LoweringError("Unknown input reference", location=location)
    return value


def _coerce_index_operand(value: SSAValue, ctx: EmitContext, location: object | None) -> SSAValue:
    """把公开 SSAValue 归一成 index/symbol 语义 operand。"""

    if isinstance(value.type, (SymbolValueType, SymbolIterType, IndexType)):
        return value
    if isinstance(value.type, IntegerType):
        op = arith.IndexCastOp(value, IndexType())
        ctx.builder.add_op(op)
        return op.result
    raise LoweringError("Index operand must be integer or index", location=location)


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
    from . import emit_mlir as public_emit_mlir

    return public_emit_mlir(expr, ctx)


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
        op = SymbolConstOp(value.value)
        ctx.builder.add_op(op)
        return op.result
    if not isinstance(value, int):
        raise LoweringError("symbol.const requires int literal", location=None)
    op = SymbolConstOp(value)
    ctx.builder.add_op(op)
    return op.result


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
    location = getattr(expr, "location", None)
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            return emit_symbol_const(expr, ctx)
        if isinstance(expr.value, str):
            return _coerce_index_operand(_lookup_public_symbol(expr.value, ctx, expr.location), ctx, expr.location)
        raise LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, int):
        return emit_symbol_const(expr, ctx)
    if isinstance(expr, str):
        if expr.lstrip("-").isdigit():
            return emit_symbol_const(int(expr), ctx)
        return _coerce_index_operand(_lookup_public_symbol(expr, ctx, location), ctx, location)
    if isinstance(expr, (ScalarArgAST, VarAST)):
        return _coerce_index_operand(_lookup_public_symbol(expr.name, ctx, location), ctx, location)
    raise LoweringError("Unsupported index expression", location=location)
