"""symbol dialect registration for EmitC op/value emission.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 把 `symbol` 相关的节点级发射挂到 `emit_c` 注册表。
- 当前阶段先维持旧输出完全一致，再逐步收口到包内实现。

使用示例:
- import kernel_gen.dsl.gen_kernel.emit_c.symbol  # 触发注册

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from xdsl.ir import Operation

from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolCastOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolGeOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolGtOp,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolToFloatOp,
    SymbolToIntOp,
)

from .._legacy import load_legacy_emit_c_module
from .register import emit_c_impl, emit_c_value_impl

_legacy_emit_c = load_legacy_emit_c_module()

_VALUE_TYPES = (
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolEqOp,
    SymbolNeOp,
    SymbolLtOp,
    SymbolLeOp,
    SymbolGtOp,
    SymbolGeOp,
    SymbolConstOp,
    SymbolToFloatOp,
    SymbolToIntOp,
    SymbolCastOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
)


@emit_c_impl(
    SymbolConstOp,
    SymbolToFloatOp,
    SymbolToIntOp,
    SymbolCastOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolForOp,
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolEqOp,
    SymbolNeOp,
    SymbolLtOp,
    SymbolLeOp,
    SymbolGtOp,
    SymbolGeOp,
)
def _emit_symbol_op(op: Operation, ctx) -> str:
    return _legacy_emit_c.emit_c_op(op, ctx)


@emit_c_value_impl(*_VALUE_TYPES)
def _emit_symbol_value(value, ctx) -> str:
    return _legacy_emit_c.emit_c_value(value, ctx)


__all__: list[str] = []
