"""Arch operation API.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 operation 层的 arch helper，覆盖执行维度查询、动态片上内存入口与 kernel 启动描述。

使用示例:
- from kernel_gen.operation.arch import get_block_id, get_dynamic_memory, launch_kernel
- bid = get_block_id()
- smem = get_dynamic_memory(MemorySpace.SM)
- launch_kernel("my_kernel", 1, 128, 4)

关联文件:
- spec: spec/operation/arch.md
- test: test/operation/test_operation_arch.py
- 功能实现: kernel_gen/operation/arch.py
"""

from __future__ import annotations

from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

LaunchExtent = int | SymbolDim
_DYNAMIC_MEMORY_SPACES = (
    MemorySpace.SM,
    MemorySpace.LM,
    MemorySpace.TSM,
    MemorySpace.TLM,
)


def _build_query_symbol(name: str) -> SymbolDim:
    """构造执行维度查询返回的 SymbolDim。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为六个执行维度查询 helper 复用统一的 SymbolDim 构造路径。

    使用示例:
    - _build_query_symbol("block_id")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return SymbolDim(name)


def _ensure_dynamic_memory_space(space: object) -> MemorySpace:
    """校验动态内存 helper 的空间参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受 `MemorySpace`。
    - 仅允许片上空间 `SM/LM/TSM/TLM`。

    使用示例:
    - _ensure_dynamic_memory_space(MemorySpace.SM)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if not isinstance(space, MemorySpace):
        raise TypeError("space must be MemorySpace")
    if space not in _DYNAMIC_MEMORY_SPACES:
        raise ValueError("space must be on-chip MemorySpace")
    return space


def _ensure_launch_extent(value: object, name: str) -> LaunchExtent:
    """校验 kernel 启动规模参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受正整数或 `SymbolDim`。
    - 静态整数要求 `> 0`。

    使用示例:
    - _ensure_launch_extent(128, "thread")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if isinstance(value, bool) or not isinstance(value, (int, SymbolDim)):
        raise TypeError(f"{name} must be int or SymbolDim")
    if isinstance(value, int) and value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value


def get_block_id() -> SymbolDim:
    """返回当前 block 的执行索引语义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对外表现为 `SymbolDim("block_id")` 风格标量。

    使用示例:
    - get_block_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _build_query_symbol("block_id")


def get_block_num() -> SymbolDim:
    """返回当前 launch 的 block 数量语义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对外表现为 `SymbolDim("block_num")` 风格标量。

    使用示例:
    - get_block_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _build_query_symbol("block_num")


def get_thread_id() -> SymbolDim:
    """返回当前 block 内 thread 执行索引语义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对外表现为 `SymbolDim("thread_id")` 风格标量。

    使用示例:
    - get_thread_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _build_query_symbol("thread_id")


def get_thread_num() -> SymbolDim:
    """返回当前 block 内 thread 数量语义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对外表现为 `SymbolDim("thread_num")` 风格标量。

    使用示例:
    - get_thread_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _build_query_symbol("thread_num")


def get_subthread_id() -> SymbolDim:
    """返回当前 thread 内 subthread 执行索引语义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对外表现为 `SymbolDim("subthread_id")` 风格标量。

    使用示例:
    - get_subthread_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _build_query_symbol("subthread_id")


def get_subthread_num() -> SymbolDim:
    """返回当前 thread 内 subthread 数量语义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对外表现为 `SymbolDim("subthread_num")` 风格标量。

    使用示例:
    - get_subthread_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _build_query_symbol("subthread_num")


def get_dynamic_memory(space: object) -> Memory:
    """返回指定片上空间的动态字节缓冲语义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 返回 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8` 的一维动态内存描述。
    - 仅允许片上空间 `SM/LM/TSM/TLM`。

    使用示例:
    - get_dynamic_memory(MemorySpace.SM)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    normalized_space = _ensure_dynamic_memory_space(space)
    return Memory(["?"], NumericType.Int8, space=normalized_space, stride=[1])


def launch_kernel(name: object, block: object, thread: object, subthread: object) -> None:
    """记录一次 kernel 启动请求。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 kernel 名称与三层执行规模。
    - 只保留 operation 层启动语义，返回 `None`。

    使用示例:
    - launch_kernel("my_kernel", SymbolDim("GRID_X"), 128, 4)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if not isinstance(name, str):
        raise TypeError("name must be str")
    if name == "":
        raise ValueError("name must not be empty")
    _ensure_launch_extent(block, "block")
    _ensure_launch_extent(thread, "thread")
    _ensure_launch_extent(subthread, "subthread")
    return None


__all__ = [
    "get_block_id",
    "get_block_num",
    "get_thread_id",
    "get_thread_num",
    "get_subthread_id",
    "get_subthread_num",
    "get_dynamic_memory",
    "launch_kernel",
]
