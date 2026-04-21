"""arith dialect registration for EmitC op/value emission.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 把 `arith` 相关的节点级发射挂到 `emit_c` 注册表。
- S2 阶段先复用旧实现输出，后续再逐步把真实逻辑完全迁入包内。

使用示例:
- import kernel_gen.dsl.gen_kernel.emit_c.arith  # 触发注册

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from xdsl.dialects import arith
from xdsl.ir import Operation

from .._legacy import load_legacy_emit_c_module
from .register import emit_c_impl, emit_c_value_impl

_legacy_emit_c = load_legacy_emit_c_module()


@emit_c_impl(
    arith.AddiOp,
    arith.AddfOp,
    arith.SubiOp,
    arith.SubfOp,
    arith.MuliOp,
    arith.MulfOp,
    arith.DivfOp,
    arith.CmpiOp,
)
def _emit_arith_op(op: Operation, ctx) -> str:
    return _legacy_emit_c.emit_c_op(op, ctx)


@emit_c_value_impl(
    arith.ConstantOp,
    arith.AddiOp,
    arith.AddfOp,
    arith.SubiOp,
    arith.SubfOp,
    arith.MuliOp,
    arith.MulfOp,
    arith.DivfOp,
    arith.CmpiOp,
)
def _emit_arith_value(value, ctx) -> str:
    return _legacy_emit_c.emit_c_value(value, ctx)


__all__: list[str] = []
