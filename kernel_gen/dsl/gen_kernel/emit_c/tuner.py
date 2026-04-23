"""tuner dialect registration for EmitC op emission.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 把 `tuner.cost` 的节点级发射挂到包式 `emit_c` 注册表。
- 继续复用旧 `kernel_gen.dsl.emit_c` 的实际文本生成逻辑，保持输出与错误边界一致。

使用示例:
- import kernel_gen.dsl.gen_kernel.emit_c.tuner  # 触发注册

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from kernel_gen.dialect.tuner import TunerCostOp

from .._legacy import load_legacy_emit_c_module
from .register import emit_c_impl

_legacy_emit_c = load_legacy_emit_c_module()


@emit_c_impl(TunerCostOp)
def _emit_tuner_op(op, ctx) -> str:
    """通过包式注册表转发 `tuner.cost` 的节点级发射。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为包式 `emit_c` 注册表提供 `TunerCostOp` 的最小桥接函数。
    - 不复制第二套发射逻辑，直接委托旧 `kernel_gen.dsl.emit_c.emit_c_op(...)`，
      保持 `target="npu_demo"` 下 `tuner.cost` 的文本输出、错误边界和结果复用语义一致。

    使用示例:
    - from kernel_gen.dsl.gen_kernel import EmitCContext
    - _emit_tuner_op(cost_op, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
    - test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
    - 功能实现: [kernel_gen/dsl/emit_c.py](../../emit_c.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/tuner.py](./tuner.py)
    """
    return _legacy_emit_c.emit_c_op(op, ctx)


__all__: list[str] = []
