"""npu_demo `kernel.select` EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `kernel.select` EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/kernel/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/select.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelSelectOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


@emit_c_impl(KernelSelectOp, target="npu_demo")
def _emit_npu_demo_kernel_select(op: KernelSelectOp, ctx) -> str:
    """发射 npu_demo `kernel.select` C++ 语句。

    功能说明:
    - 根据 `KernelSelectOp` 的 cond/lhs/rhs/out memory 生成 `select<...>(...)` 语句。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_kernel_select(op, ctx)
    """

    from ... import emit_c_value

    out_value = op.out
    cond_value = op.cond
    lhs_value = op.lhs
    rhs_value = op.rhs
    out_idx = out_value.index if hasattr(out_value, "index") else None
    cond_idx = cond_value.index if hasattr(cond_value, "index") else None
    lhs_idx = lhs_value.index if hasattr(lhs_value, "index") else None
    rhs_idx = rhs_value.index if hasattr(rhs_value, "index") else None
    if (
        out_idx is not None
        and cond_idx is not None
        and lhs_idx is not None
        and rhs_idx is not None
        and rhs_idx < out_idx
        and rhs_idx < cond_idx
        and rhs_idx < lhs_idx
    ):
        out_value, cond_value, lhs_value, rhs_value = rhs_value, out_value, cond_value, lhs_value
    if not all(
        isinstance(value.type, NnMemoryType)
        for value in (out_value, cond_value, lhs_value, rhs_value)
    ):
        raise ctx.emit_error(op.name, "unsupported op")
    return (
        f"{ctx.current_indent}select<{ctx.dispatch_attr(out_value.type)}, {ctx.dispatch_type(lhs_value.type.element_type)}, "
        f"{ctx.dispatch_type(out_value.type.element_type)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(cond_value, ctx)} /*cond*/, "
        f"{emit_c_value(lhs_value, ctx)} /*lhs*/, {emit_c_value(rhs_value, ctx)} /*rhs*/);"
    )
