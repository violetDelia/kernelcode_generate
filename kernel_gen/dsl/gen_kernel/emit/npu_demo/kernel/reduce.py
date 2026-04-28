"""npu_demo kernel reduce 发射实现。

创建者: 小李飞刀
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 发射 npu_demo 目标下的 `kernel.reduce` 与 `kernel.reduce_min`。
- `kernel.reduce(kind="sum" | "min" | "max")` 分别收口到公开 `reduce_sum` / `reduce_min` / `reduce_max` helper。

API 列表:
- 无公开 API；通过 emit registry 注册 kernel reduce 发射器。

使用示例:
- stmt = emit_c_op(kernel_reduce_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit.md
- spec: spec/include/api/Kernel.md
- test: test/dsl/gen_kernel/emit/test_emit.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/reduce.py
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import KernelReduceMinOp, KernelReduceOp
from kernel_gen.dialect.nn import NnMemoryType

from ...register import emit_c_impl


def _block_arg_index(value) -> int | None:
    return value.index if hasattr(value, "index") else None


def _normalize_out_input_operands(out_value, input_value):
    out_idx = _block_arg_index(out_value)
    input_idx = _block_arg_index(input_value)
    if out_idx is not None and input_idx is not None and input_idx < out_idx:
        return input_value, out_value
    return out_value, input_value


@emit_c_impl(KernelReduceOp, target="npu_demo")
def _emit_npu_demo_kernel_reduce(op: KernelReduceOp, ctx) -> str:
    """发射 npu_demo `kernel.reduce`。

    创建者: 小李飞刀
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 校验 input/out 为 memory。
    - 按 `kind` 选择公开 reduce helper 名称。

    使用示例:
    - stmt = _emit_npu_demo_kernel_reduce(op, ctx)

    关联文件:
    - spec: spec/include/api/Kernel.md
    - test: test/dsl/gen_kernel/emit/test_emit.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/reduce.py
    """

    from ... import emit_c_value

    out_value, input_value = _normalize_out_input_operands(op.out, op.input)
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    helper_name = {
        "sum": "reduce_sum",
        "min": "reduce_min",
        "max": "reduce_max",
    }.get(op.kind.data)
    if helper_name is None:
        raise ctx.emit_error(op.name, f"unsupported kind={op.kind.data}")
    return (
        f"{ctx.current_indent}{helper_name}<{ctx.dispatch_attr(out_value.type)}, {ctx.dispatch_type(input_value.type.element_type)}, "
        f"{ctx.dispatch_type(out_value.type.element_type)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(input_value, ctx)} /*input*/, {op.axis.value.data} /*axis*/);"
    )


@emit_c_impl(KernelReduceMinOp, target="npu_demo")
def _emit_npu_demo_kernel_reduce_min(op: KernelReduceMinOp, ctx) -> str:
    """发射 npu_demo `kernel.reduce_min`。

    创建者: 小李飞刀
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 保留具名 `kernel.reduce_min` 到公开 `reduce_min` helper 的发射路径。

    使用示例:
    - stmt = _emit_npu_demo_kernel_reduce_min(op, ctx)

    关联文件:
    - spec: spec/include/api/Kernel.md
    - test: test/dsl/gen_kernel/emit/test_emit.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/reduce.py
    """

    from ... import emit_c_value

    out_value, input_value = _normalize_out_input_operands(op.out, op.input)
    if not isinstance(input_value.type, NnMemoryType) or not isinstance(out_value.type, NnMemoryType):
        raise ctx.emit_error(op.name, "unsupported op")
    return (
        f"{ctx.current_indent}reduce_min<{ctx.dispatch_attr(out_value.type)}, {ctx.dispatch_type(input_value.type.element_type)}, "
        f"{ctx.dispatch_type(out_value.type.element_type)}>"
        f"({emit_c_value(out_value, ctx)} /*out*/, {emit_c_value(input_value, ctx)} /*input*/, {op.axis.value.data} /*axis*/);"
    )
