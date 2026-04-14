"""Emit 共享核心入口。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 收口 emit 共享层入口与职责边界，统一 dispatch/control_flow/value/type/shape 工具。
- 暴露 EmitContext 与 emit 入口，便于 mlir_gen 上层与测试调用。

使用示例:
- from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/__init__.py](kernel_gen/dsl/mlir_gen/emit/__init__.py)
"""

from __future__ import annotations

from .call_dma import emit_dma_call
from .context import EmitContext, LoweringError
from .control_flow import emit_control_flow, emit_for
from .call_nn import emit_nn_call
from .dispatch import call_dispatch, emit_mlir
from .shape_utils import (
    build_index_attrs,
    build_index_operands_exact,
    build_index_operands_from_layout,
    build_stride_attrs,
    resolve_index_expr,
)
from .type_utils import infer_expr_type, memory_type_from_parts
from .value import emit_index_operand, emit_symbol_const, emit_value

__all__ = [
    "EmitContext",
    "LoweringError",
    "emit_dma_call",
    "build_index_attrs",
    "build_index_operands_exact",
    "build_index_operands_from_layout",
    "build_stride_attrs",
    "call_dispatch",
    "emit_control_flow",
    "emit_for",
    "emit_index_operand",
    "emit_mlir",
    "emit_nn_call",
    "emit_symbol_const",
    "emit_value",
    "infer_expr_type",
    "memory_type_from_parts",
    "resolve_index_expr",
]
