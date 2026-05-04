"""npu_demo `dma.alloc` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `dma.alloc` EmitC 发射实现。
- rank 等长的 `dynamic_shape` 作为完整运行期 shape 发射，避免把 type 级语义标签写成 C++ 变量。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/alloc.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntAttr, StringAttr

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from ...register import emit_c_impl


def _expr_keys(expr: str) -> tuple[str, ...]:
    """生成符号表达式可匹配的文本 key。

    功能说明:
    - 同时支持原始文本、去空格文本与外层括号文本。
    - 仅供当前文件内 `dma.alloc` shape/stride 发射复用。

    使用示例:
    - keys = _expr_keys("min(4, 6 - ho0)")
    """

    stripped = expr.strip()
    compact = stripped.replace(" ", "")
    return (stripped, f"({stripped})", compact, f"({compact})")


def _bind_symbol_expr(bindings: dict[str, str], expr: str, value_name: str) -> None:
    """把同一个符号表达式的常见文本形态绑定到 C++ 变量名。

    功能说明:
    - `dynamic_shape` operand 是 `dma.alloc` 发射动态 layout 的唯一运行期值来源。
    - 同一表达式可能在 IR type 中带空格或被外层括号包裹，统一登记后便于机械匹配。

    使用示例:
    - _bind_symbol_expr(bindings, "min(4, 6 - ho0)", "v27")
    """

    for expr_key in _expr_keys(expr):
        bindings[expr_key] = value_name


def _format_layout_expr(expr: str, bindings: dict[str, str]) -> str:
    """把 memory layout 表达式映射为 C++ 表达式。

    功能说明:
    - 若表达式来自 `dynamic_shape`，返回对应 SSA 发射变量名。
    - 未绑定表达式保持原文本，交由现有错误路径或编译链路暴露不支持场景。

    使用示例:
    - text = _format_layout_expr("M", {"M": "m"})
    """

    for expr_key in _expr_keys(expr):
        mapped = bindings.get(expr_key)
        if mapped is not None:
            return mapped
    return expr


def _format_shape_values(op: DmaAllocOp, bindings: dict[str, str], ctx) -> list[str]:
    """按 result type 重建 `alloc(...)` 的完整 shape 参数。

    功能说明:
    - `dynamic_shape` 可以只列符号维度，静态维度必须从 result type 补回。
    - 符号维度必须优先映射为已发射 C++ 变量名，避免把 IR 文本中的 loop hint 写进源码。

    使用示例:
    - shape_values = _format_shape_values(op, {"M": "m"}, ctx)
    """

    result_type = op.result.type
    shape_values: list[str] = []
    for value in result_type.shape.data:
        if isinstance(value, IntAttr):
            shape_values.append(str(value.data))
            continue
        if isinstance(value, StringAttr):
            shape_values.append(_format_layout_expr(value.data, bindings))
            continue
        raise ctx.emit_error(op.name, "unsupported alloc layout value")
    return shape_values


def _format_full_rank_dynamic_shape_values(op: DmaAllocOp, dynamic_shape_values: list[str]) -> list[str] | None:
    """按 rank 等长 `dynamic_shape` 取得完整运行期 shape。

    功能说明:
    - `runtime_dim_*` 这类 type 级语义标签不是 C++ 变量，不能直接写入 `alloc(...)`。
    - 当 `dynamic_shape` 与 result rank 等长时，它已经逐维承载真实运行期 shape，应优先用于源码发射。

    使用示例:
    - shape_values = _format_full_rank_dynamic_shape_values(op, ["m", "n"])
    """

    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        return None
    if len(dynamic_shape_values) != len(result_type.shape.data):
        return None
    return list(dynamic_shape_values)


def _stride_term(value: str) -> str:
    """格式化参与 stride 乘法的单项。

    功能说明:
    - 简单变量和整数保持原样，复合表达式加括号以稳定 C++ 优先级。

    使用示例:
    - term = _stride_term("m + 1")
    """

    if value.isidentifier() or value.isdecimal():
        return value
    return f"({value})"


def _default_stride_values(shape_values: list[str]) -> list[str]:
    """根据完整 shape 参数生成默认连续 stride 参数。

    功能说明:
    - npu_demo `dma.alloc` helper 以公开默认连续布局接收 shape/stride。
    - 使用已映射的 C++ shape 表达式生成 stride，避免重新消费 IR type 文本。

    使用示例:
    - strides = _default_stride_values(["m", "3", "n"])
    """

    stride_values: list[str] = []
    running_terms: list[str] = []
    for value in reversed(shape_values):
        stride_values.append("*".join(running_terms) if running_terms else "1")
        if value != "1":
            running_terms.insert(0, _stride_term(value))
    stride_values.reverse()
    return stride_values


@emit_c_impl(DmaAllocOp, target="npu_demo")
def _emit_npu_demo_dma_alloc(op: DmaAllocOp, ctx) -> str:
    """发射 npu_demo `dma.alloc` C++ 语句。

    功能说明:
    - 根据 `DmaAllocOp` 的 memory type、dynamic shape 与 stride 生成 `alloc<...>(...)` 语句。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_dma_alloc(op, ctx)
    """

    from ... import emit_c_value

    result_name = ctx.create_or_get_name(op.result)
    result_type = op.result.type
    if not isinstance(result_type, NnMemoryType):
        raise ctx.emit_error(op.name, "result must be nn.memory")
    symbol_bindings: dict[str, str] = {}
    dynamic_shape_values: list[str] = []
    for value in op.dynamic_shape:
        value_type = value.type
        if isinstance(value_type, SymbolValueType):
            value_expr = value_type.expr.expr.data
            value_name = emit_c_value(value, ctx)
            dynamic_shape_values.append(value_name)
            _bind_symbol_expr(symbol_bindings, value_expr, value_name)
            public_value = value_type.get_value()
            if isinstance(public_value, str):
                _bind_symbol_expr(symbol_bindings, public_value, value_name)
    shape_values = _format_full_rank_dynamic_shape_values(op, dynamic_shape_values) or _format_shape_values(
        op, symbol_bindings, ctx
    )
    stride_values = _default_stride_values(shape_values)
    space_expr = ctx.dispatch_attr(result_type)
    element_type = ctx.dispatch_type(result_type.element_type)
    shape_text = ", ".join(shape_values)
    stride_text = ", ".join(stride_values)
    return (
        f"{ctx.current_indent}Memory<{space_expr}, {element_type}> {result_name} = "
        f"alloc<{space_expr}, {element_type}>({{{shape_text}}} /*shape*/, {{{stride_text}}} /*stride*/);"
    )
