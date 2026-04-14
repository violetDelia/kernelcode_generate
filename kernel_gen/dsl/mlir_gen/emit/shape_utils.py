"""Emit shape/stride 工具。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 提供 shape/stride/index 的统一构造入口。
- 聚合 emit 共享逻辑，避免在 family 逻辑中重复实现。

使用示例:
- offsets = build_index_attrs(None, 2, ctx, default_value=0)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_shape_utils.py](test/dsl/mlir_gen/emit/test_shape_utils.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/shape_utils.py](kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
"""

from __future__ import annotations

from xdsl.ir import Attribute, SSAValue

from kernel_gen.dsl.ast import SourceLocation
from .core import (
    _build_index_attrs,
    _build_index_operands_exact,
    _build_index_operands_from_layout,
    _build_stride_attrs,
    _resolve_index_expr,
)

from .context import EmitContext


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
    return _resolve_index_expr(expr, ctx)


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
    return _build_index_attrs(value, rank, ctx, default_value=default_value, location=location)


def build_index_operands_from_layout(
    layout: Attribute,
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
    return _build_index_operands_from_layout(layout, ctx, location=location)


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
    return _build_stride_attrs(value, rank, ctx, location=location)


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
    return _build_index_operands_exact(value, ctx, location=location)
