"""Emit shape/stride 工具。

创建者: jcc你莫辜负
最后一次更改: 金铲铲大作战

功能说明:
- 提供 `emit_mlir(...)` 共享的 shape/stride/index 内部辅助逻辑。
- 当前文件不单独承载公开 API，对外公开入口仍是 `EmitContext(...)` / `emit_mlir(node, ctx)`。

API 列表:
- 无；当前文件仅提供 `emit_mlir(node, ctx)` 共享的内部 shape/index helper。

使用示例:
- offsets = emit_mlir(node, ctx)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_shape_utils.py](test/dsl/mlir_gen/emit/test_shape_utils.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/shape_utils.py](kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
"""

from __future__ import annotations

from xdsl.dialects import arith
from xdsl.dialects.builtin import ArrayAttr, IntegerAttr, IntAttr, StringAttr
from xdsl.ir import Attribute, SSAValue

from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import BinaryExprAST, ConstAST, ScalarArgAST, SourceLocation, VarAST
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

from .context import EmitContext
from .value import emit_index_operand


class LoweringError(ValueError):
    """当前文件内使用的 shape/stride 失败错误。"""

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        super().__init__(message)
        self.location = location


def _loop_vars(ctx: EmitContext) -> dict[str, object]:
    """读取当前上下文里的 loop_vars。"""

    if ctx.config is None:
        ctx.config = {}
    loop_vars = ctx.config.setdefault("loop_vars", {})
    if not isinstance(loop_vars, dict):
        raise LoweringError("loop_vars must be a dict", location=None)
    return loop_vars


def _normalize_index_value(value: int | str | SymbolDim, location: SourceLocation | None) -> int | str:
    """将符号索引值收口成公开 `int | str`。"""

    if isinstance(value, SymbolDim):
        value = value.get_value()
    if isinstance(value, (int, str)):
        return value
    raise LoweringError("Unsupported index expression", location=location)


def _apply_symbolic_index_binary_op(
    lhs_value: int | SymbolDim,
    rhs_value: int | SymbolDim,
    op: str,
    location: SourceLocation | None,
) -> int | SymbolDim:
    """在当前文件内解析 shape/stride 公开索引的二元表达式。"""

    if op == "add":
        return lhs_value + rhs_value
    if op == "sub":
        return lhs_value - rhs_value
    if op == "mul":
        return lhs_value * rhs_value
    if op == "div":
        if isinstance(lhs_value, int) and isinstance(rhs_value, int):
            if rhs_value == 0:
                raise LoweringError("Unsupported index expression", location=location)
            return lhs_value / rhs_value
        if isinstance(lhs_value, int):
            lhs_value = SymbolDim(lhs_value)
        return lhs_value / rhs_value
    if op == "floordiv":
        if isinstance(lhs_value, int) and isinstance(rhs_value, int):
            if rhs_value == 0:
                raise LoweringError("Unsupported index expression", location=location)
            return lhs_value // rhs_value
        if isinstance(lhs_value, int):
            lhs_value = SymbolDim(lhs_value)
        return lhs_value // rhs_value
    raise LoweringError("Unsupported index expression", location=location)


def resolve_index_expr(expr: object, ctx: EmitContext) -> int | str:
    """解析索引表达式为 int/str。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 复用 emit 内部的 index 解析逻辑。
    - 仅返回静态可解析的 int/str 结果。

    参数说明:
    - expr: 索引表达式。
    - ctx: EmitContext。

    返回说明:
    - 返回 int 或 str 表达式。

    使用示例:
    - value = resolve_index_expr(ConstAST(1), ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_shape_utils.py](test/dsl/mlir_gen/emit/test_shape_utils.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/shape_utils.py](kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
    """
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, (int, str)):
            return _normalize_index_value(SymbolDim(expr.value) if isinstance(expr.value, str) else expr.value, expr.location)
        raise LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, ScalarArgAST):
        return expr.name
    if isinstance(expr, VarAST):
        loop_vars = _loop_vars(ctx)
        if expr.name not in loop_vars:
            raise LoweringError("Unknown loop variable", location=expr.location)
        value = loop_vars[expr.name]
        if isinstance(value, SymbolDim):
            return _normalize_index_value(value, expr.location)
        if isinstance(value, (int, str)):
            return value
        raise LoweringError("Unsupported index expression", location=expr.location)
    if isinstance(expr, BinaryExprAST):
        lhs = resolve_index_expr(expr.lhs, ctx)
        rhs = resolve_index_expr(expr.rhs, ctx)
        lhs_value = SymbolDim(lhs) if isinstance(lhs, str) else lhs
        rhs_value = SymbolDim(rhs) if isinstance(rhs, str) else rhs
        return _normalize_index_value(
            _apply_symbolic_index_binary_op(lhs_value, rhs_value, expr.op, expr.location),
            expr.location,
        )
    if isinstance(expr, int):
        return expr
    if isinstance(expr, str):
        return _normalize_index_value(SymbolDim(expr), None)
    raise LoweringError("Unsupported index expression", location=getattr(expr, "location", None))


def build_index_attrs(
    value: object | None,
    rank: int,
    ctx: EmitContext,
    *,
    default_value: int = 0,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    """构造索引 operand 列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按 rank 广播/校验索引表达式并转为 SSA operand。

    参数说明:
    - value: 单值或列表索引。
    - rank: 目标 rank。
    - ctx: EmitContext。
    - default_value: 默认补值。
    - location: 诊断位置。

    返回说明:
    - 返回 SSAValue 列表。

    使用示例:
    - attrs = build_index_attrs(None, 2, ctx, default_value=0)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_shape_utils.py](test/dsl/mlir_gen/emit/test_shape_utils.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/shape_utils.py](kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
    """
    if value is None:
        values = [default_value for _ in range(rank)]
    elif isinstance(value, (list, tuple)):
        if len(value) != rank:
            raise LoweringError("Index rank mismatch", location=location or getattr(value, "location", None))
        values = list(value)
    else:
        values = [value for _ in range(rank)]
    return [emit_index_operand(item, ctx) for item in values]


def build_index_operands_from_layout(
    layout: ArrayAttr[Attribute],
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    """将 layout 属性下沉为索引 operand。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 `ArrayAttr` 的 shape/stride 转换为 SSA operand 列表。

    参数说明:
    - layout: ArrayAttr 布局。
    - ctx: EmitContext。
    - location: 诊断位置。

    返回说明:
    - 返回 SSAValue 列表。

    使用示例:
    - operands = build_index_operands_from_layout(layout, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_shape_utils.py](test/dsl/mlir_gen/emit/test_shape_utils.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/shape_utils.py](kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
    """
    values: list[object] = []
    for dim in layout.data:
        if isinstance(dim, IntAttr):
            values.append(dim.data)
            continue
        if isinstance(dim, StringAttr):
            values.append(dim.data)
            continue
        raise LoweringError("Unsupported layout attribute", location=location)
    return [emit_index_operand(item, ctx) for item in values]


def build_stride_attrs(
    value: object | None,
    rank: int,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    """构造 stride operand 列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 复用 emit 内部 stride 构造逻辑。

    参数说明:
    - value: stride 表达式。
    - rank: 目标 rank。
    - ctx: EmitContext。
    - location: 诊断位置。

    返回说明:
    - 返回 SSAValue 列表。

    使用示例:
    - strides = build_stride_attrs(None, 2, ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_shape_utils.py](test/dsl/mlir_gen/emit/test_shape_utils.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/shape_utils.py](kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
    """
    stride = build_index_attrs(value, rank, ctx, default_value=1, location=location)
    for entry in stride:
        if isinstance(entry.type, SymbolValueType):
            if entry.type.get_value() != 1:
                raise LoweringError("Only unit stride is supported", location=location)
            continue
        owner = entry.owner
        if not isinstance(owner, arith.ConstantOp) or not isinstance(owner.value, IntegerAttr):
            raise LoweringError("Only unit stride is supported", location=location)
        if owner.value.value.data != 1:
            raise LoweringError("Only unit stride is supported", location=location)
    return stride


def build_index_operands_exact(
    value: object,
    ctx: EmitContext,
    *,
    location: SourceLocation | None = None,
) -> list[SSAValue]:
    """构造精确索引 operand 列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受单值或显式列表，不进行默认补值。

    参数说明:
    - value: 单值或列表。
    - ctx: EmitContext。
    - location: 诊断位置。

    返回说明:
    - 返回 SSAValue 列表。

    使用示例:
    - operands = build_index_operands_exact([ConstAST(1), ConstAST(2)], ctx)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_shape_utils.py](test/dsl/mlir_gen/emit/test_shape_utils.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/shape_utils.py](kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
    """
    values = list(value) if isinstance(value, (list, tuple)) else [value]
    return [emit_index_operand(item, ctx) for item in values]
