"""npu_demo tuner.launch emitter.

功能说明:
- 裸 `tuner.launch` 不允许进入 C++ 发射阶段。
- 该 op 必须先由 `outline-device-kernel` 降为 `arch.launch`。

API 列表:
- 无公开 API。

使用示例:
- emit_c_op(TunerLaunchOp("pattern0"), EmitCContext())  # raises

关联文件:
- spec: spec/dsl/gen_kernel/gen_kernel.md
- test: test/dsl/gen_kernel/test_gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/launch.py
"""

from __future__ import annotations

from kernel_gen.dialect.tuner import TunerLaunchOp

from ...register import emit_c_impl


@emit_c_impl(TunerLaunchOp, target="npu_demo")
def _emit_npu_demo_tuner_launch(op: TunerLaunchOp, ctx) -> str:
    """拒绝直接发射 npu_demo `tuner.launch`。

    功能说明:
    - `tuner.launch` 是 IR 中间合同，源码生成前必须 outline。
    - 错误文本固定包含 `tuner.launch` 与 `outline-device-kernel`。

    使用示例:
    - _emit_npu_demo_tuner_launch(op, ctx)
    """

    _ = op
    raise ctx.emit_error("tuner.launch", "run outline-device-kernel before gen_kernel")
