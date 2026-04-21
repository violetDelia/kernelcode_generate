"""kernel dialect registration for EmitC op emission.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 把 `kernel` 相关的节点级发射挂到 `emit_c` 注册表。
- 保留旧输出与旧 helper 名称不变。

使用示例:
- import kernel_gen.dsl.gen_kernel.emit_c.kernel  # 触发注册

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from kernel_gen.dialect.kernel import (
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceMinOp,
    KernelReduceOp,
    KernelSelectOp,
)

from .._legacy import load_legacy_emit_c_module
from .register import emit_c_impl

_legacy_emit_c = load_legacy_emit_c_module()


@emit_c_impl(
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelSelectOp,
    KernelReduceOp,
    KernelReduceMinOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
)
def _emit_kernel_op(op, ctx) -> str:
    return _legacy_emit_c.emit_c_op(op, ctx)


__all__: list[str] = []
