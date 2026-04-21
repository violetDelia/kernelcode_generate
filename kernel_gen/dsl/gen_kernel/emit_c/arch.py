"""arch dialect registration for EmitC op/value emission.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 把 `arch` 相关的节点级发射挂到 `emit_c` 注册表。
- 先维持旧输出与旧错误语义，再逐步把实现搬进包内。

使用示例:
- import kernel_gen.dsl.gen_kernel.emit_c.arch  # 触发注册

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp, ArchGetThreadIdOp, ArchGetThreadNumOp

from .._legacy import load_legacy_emit_c_module
from .register import emit_c_impl, emit_c_value_impl

_legacy_emit_c = load_legacy_emit_c_module()


@emit_c_impl(ArchGetThreadIdOp, ArchGetThreadNumOp, ArchGetDynamicMemoryOp)
def _emit_arch_op(op, ctx) -> str:
    return _legacy_emit_c.emit_c_op(op, ctx)


@emit_c_value_impl(ArchGetThreadIdOp, ArchGetThreadNumOp, ArchGetDynamicMemoryOp)
def _emit_arch_value(value, ctx) -> str:
    return _legacy_emit_c.emit_c_value(value, ctx)


__all__: list[str] = []
