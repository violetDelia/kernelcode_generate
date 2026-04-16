"""Emit 包根公开入口。

创建者: jcc你莫辜负
最后一次更改: 金铲铲大作战

功能说明:
- 收口 `kernel_gen.dsl.mlir_gen.emit` 包根的稳定公开集合。
- 包根暴露 `EmitContext`、`emit_mlir`，以及供 expectation/tooling 复用的稳定 memory type 转换 helper。
- family/helper 入口仍需从对应子模块访问。

使用示例:
- from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
- from kernel_gen.dsl.mlir_gen.emit import memory_type_from_memory

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_dispatch.py](test/dsl/mlir_gen/emit/test_dispatch.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/__init__.py](kernel_gen/dsl/mlir_gen/emit/__init__.py)
"""

from __future__ import annotations

from kernel_gen.symbol_variable.memory import Memory

from .context import EmitContext
from .dispatch import emit_mlir
from .core import _memory_to_nn_type


def memory_type_from_memory(memory: Memory):
    """将 `Memory` 描述转换为稳定的 `NnMemoryType`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 expectation / tooling 提供通过 `emit` 包根可见的稳定 memory type 转换入口。
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

    return _memory_to_nn_type(memory)

__all__ = [
    "EmitContext",
    "emit_mlir",
    "memory_type_from_memory",
]
