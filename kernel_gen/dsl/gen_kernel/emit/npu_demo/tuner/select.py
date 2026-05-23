"""npu_demo tuner.select emitter.

功能说明:
- 将 `tuner.select` 发射为稳定的 `S_INT <name> = 0;`。
- 第一版 dispatcher 固定选择 pattern0，后续 tuner 接入可替换该值来源。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(TunerSelectOp(["p0", "p1"]), EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/gen_kernel.md
- test: test/dsl/gen_kernel/test_gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/select.py
"""

from __future__ import annotations

from kernel_gen.dialect.tuner import TunerSelectOp

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(TunerSelectOp, target="npu_demo")
def _emit_npu_demo_tuner_select(op: TunerSelectOp, ctx) -> str:
    """发射 npu_demo `tuner.select`。

    功能说明:
    - 通过公开 emit registry 把选择值绑定为 `S_INT` 局部变量。
    - 当前合同固定默认值为 0。

    使用示例:
    - line = _emit_npu_demo_tuner_select(op, ctx)
    """

    name = ctx.create_or_get_name(op.result)
    return f"{ctx.current_indent}S_INT {name} = 0;"


@emit_c_value_impl(TunerSelectOp, target="npu_demo")
def _emit_npu_demo_tuner_select_value(value, ctx) -> str:
    """发射 npu_demo `tuner.select` result 表达式。

    功能说明:
    - 优先复用 op 语句发射阶段绑定的局部变量名。
    - 若被条件表达式先消费，也通过公开命名入口创建同一变量名。

    使用示例:
    - expr = _emit_npu_demo_tuner_select_value(select.result, ctx)
    """

    return ctx.create_or_get_name(value)
