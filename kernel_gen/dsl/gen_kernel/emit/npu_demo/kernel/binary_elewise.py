"""npu_demo `kernel.binary_elewise` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `kernel.binary_elewise` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/kernel/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/binary_elewise.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


@emit_c_impl(KernelBinaryElewiseOp, target="npu_demo")
def _emit_npu_demo_kernel_binary_elewise(op: KernelBinaryElewiseOp, ctx) -> str:
    """发射 npu_demo `kernel.binary_elewise` C++ 语句。

    功能说明:
    - 根据 `KernelBinaryElewiseOp.kind` 选择 npu_demo elewise helper，并生成模板调用。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_kernel_binary_elewise(op, ctx)
    """

    from ... import emit_c_value

    out_value = op.out
    lhs_value = op.lhs
    rhs_value = op.rhs
    out_idx = out_value.index if hasattr(out_value, "index") else None
    lhs_idx = lhs_value.index if hasattr(lhs_value, "index") else None
    rhs_idx = rhs_value.index if hasattr(rhs_value, "index") else None
    if (
        out_idx is not None
        and lhs_idx is not None
        and rhs_idx is not None
        and rhs_idx < out_idx
        and rhs_idx < lhs_idx
    ):
        out_value, lhs_value, rhs_value = rhs_value, out_value, lhs_value
    if not all(isinstance(value.type, NnMemoryType) for value in (out_value, lhs_value, rhs_value)):
        raise ctx.emit_error(op.name, "unsupported op")
    helper_map = {
        "add": "add",
        "sub": "sub",
        "mul": "mul",
        "div": "truediv",
        "truediv": "truediv",
        "eq": "eq",
        "ne": "ne",
        "lt": "lt",
        "le": "le",
        "gt": "gt",
        "ge": "ge",
    }
    helper_name = helper_map.get(op.kind.data)
    if helper_name is None:
        raise ctx.emit_error(op.name, f"unsupported kind={op.kind.data}")
    out_expr = emit_c_value(out_value, ctx)
    lhs_expr = emit_c_value(lhs_value, ctx)
    rhs_expr = emit_c_value(rhs_value, ctx)
    space_expr = ctx.dispatch_attr(out_value.type)
    input_type = ctx.dispatch_type(lhs_value.type.element_type)
    output_type = ctx.dispatch_type(out_value.type.element_type)
    return (
        f"{ctx.current_indent}{helper_name}<{space_expr}, {input_type}, {output_type}>"
        f"({out_expr} /*out*/, {lhs_expr} /*lhs*/, {rhs_expr} /*rhs*/);"
    )
