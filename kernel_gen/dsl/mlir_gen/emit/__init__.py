"""Emit 包根公开入口。

创建者: jcc你莫辜负
最后一次更改: 金铲铲大作战

功能说明:
- 收口 `kernel_gen.dsl.mlir_gen.emit` 包根的稳定公开集合。
- 包根暴露 `EmitContext`、`emit_mlir`，以及供工具和测试复用的稳定 memory type 转换 helper。
- family/helper 入口仍需从对应子模块访问。

API 列表:
- `EmitContext(builder: Block, symbols: dict[str, object], types: dict[int, object], config: dict[str, object] | None = None)`
- `emit_mlir(node: object, ctx: EmitContext) -> object`
- `memory_type_from_memory(memory: Memory) -> NnMemoryType`

helper 清单:
- `_dim_to_attr(value: int | str | object) -> IntAttr | StringAttr`
- `_dtype_to_xdsl(dtype: NumericType) -> Attribute`
- `_space_attr_from_memory_space(space: MemorySpace) -> NnMemorySpaceAttr`

使用示例:
- from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
- from kernel_gen.dsl.mlir_gen.emit import memory_type_from_memory

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/__init__.py](kernel_gen/dsl/mlir_gen/emit/__init__.py)
"""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, BFloat16Type, Float16Type, Float64Type, IntAttr, StringAttr, f32, i1, i8, i32, i64
from xdsl.ir import Attribute

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

from .context import EmitContext
from .core import emit_mlir


def _dim_to_attr(value: int | str | object) -> IntAttr | StringAttr:
    """将公开 `Memory` 维度值转换为 `NnMemoryType` 属性。"""

    if isinstance(value, SymbolDim):
        value = value.get_value()
    if isinstance(value, int):
        return IntAttr(value)
    return StringAttr(str(value))


def _dtype_to_xdsl(dtype: NumericType) -> Attribute:
    """将公开 `NumericType` 映射到稳定 xDSL element_type。"""

    mapping = {
        NumericType.Bool: i1,
        NumericType.Int8: i8,
        NumericType.Int32: i32,
        NumericType.Int64: i64,
        NumericType.BFloat16: BFloat16Type(),
        NumericType.Float16: Float16Type(),
        NumericType.Float32: f32,
        NumericType.Float64: Float64Type(),
    }
    try:
        return mapping[dtype]
    except KeyError as exc:
        raise ValueError(f"Unsupported NumericType for emit memory conversion: {dtype}") from exc


def _space_attr_from_memory_space(space: MemorySpace) -> NnMemorySpaceAttr:
    """将公开 `MemorySpace` 映射到稳定 `NnMemorySpaceAttr`。"""

    space_name_map = {
        MemorySpace.GM: "global",
        MemorySpace.SM: "shared",
        MemorySpace.LM: "local",
        MemorySpace.TSM: "tsm",
        MemorySpace.TLM1: "tlm1",
        MemorySpace.TLM2: "tlm2",
        MemorySpace.TLM3: "tlm3",
    }
    return NnMemorySpaceAttr.from_name(space_name_map[space])


def memory_type_from_memory(memory: Memory):
    """将 `Memory` 描述转换为稳定的 `NnMemoryType`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为工具和测试提供通过 `emit` 包根可见的稳定 memory type 转换入口。
    - 对外只暴露“`Memory` -> `NnMemoryType`”这一最小能力，避免下游继续直连 `.core` 私有 helper。

    参数说明:
    - `memory`: 需要转换的 `Memory` 描述对象。

    返回说明:
    - 返回与 emit lowering 保持一致的 `NnMemoryType`。

    使用示例:
    - `mem_type = memory_type_from_memory(Memory([2, 2]))`

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/__init__.py](kernel_gen/dsl/mlir_gen/emit/__init__.py)
    """
    return NnMemoryType(
        ArrayAttr([_dim_to_attr(dim) for dim in memory.get_shape()]),
        ArrayAttr([_dim_to_attr(dim) for dim in memory.get_stride()]),
        _dtype_to_xdsl(memory.get_type()),
        _space_attr_from_memory_space(memory.get_space()),
    )

__all__ = [
    "EmitContext",
    "emit_mlir",
    "memory_type_from_memory",
]
