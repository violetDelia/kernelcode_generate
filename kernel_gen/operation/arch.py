"""Arch operation API.

创建者: 金铲铲大作战
最后一次更改: jcc你莫辜负

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
from kernel_gen.target import registry as target_registry

LaunchExtent = int | SymbolDim
_DYNAMIC_MEMORY_SPACES = (
    MemorySpace.SM,
    MemorySpace.LM,
    MemorySpace.TSM,
    MemorySpace.TLM,
)
_ERROR_TEMPLATE = "场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"
_ERROR_ACTION = "请按接口约束传参"
_ERROR_ACTUAL = "不满足期望"
_TARGET_ERROR_SCENE = "arch helper target registry 校验"
_DYNAMIC_MEMORY_HARDWARE_KEYS = {
    MemorySpace.SM: "sm_memory_size",
    MemorySpace.LM: "lm_memory_size",
    MemorySpace.TSM: "tsm_memory_size",
    MemorySpace.TLM: "tlm_memory_size",
}


def _verify_target_registry_support(op_name: str) -> None:
    """按当前 target registry 配置校验 arch helper 支持性。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在启用 target registry 校验时，阻止不支持的 helper 被调用。

    使用示例:
    - _verify_target_registry_support("arch.get_thread_id")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    current_target = target_registry._get_current_target()
    if current_target is None:
        return
    try:
        supported = target_registry.is_arch_op_supported(current_target, op_name)
    except ValueError as exc:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene=_TARGET_ERROR_SCENE,
                expected=str(exc),
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
        ) from exc
    if not supported:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene=_TARGET_ERROR_SCENE,
                expected=f"{op_name} is not supported by target {current_target}",
                actual=_ERROR_ACTUAL,
                action=_ERROR_ACTION,
            )
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


def _resolve_query_symbol(op_name: str, symbol_name: str, hardware_key: str | None = None) -> SymbolDim:
    """构造执行维度查询 helper 的返回 SymbolDim。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 先执行 target registry 支持性校验。
    - 当硬件值存在时优先使用硬件数值，否则回退到符号名称。

    使用示例:
    - _resolve_query_symbol("arch.get_block_num", "block_num", "block_num")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    _verify_target_registry_support(op_name)
    if hardware_key is not None:
        hardware_value = target_registry.get_current_target_hardware(hardware_key)
        if hardware_value is not None:
            return SymbolDim(hardware_value)
    return _build_query_symbol(symbol_name)


def _resolve_dynamic_memory_shape(space: MemorySpace) -> list[int | str]:
    """解析动态内存 helper 的 shape 返回。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 优先使用 target hardware 中的容量信息。
    - 若缺失容量信息，回退为一维动态 `?`。

    使用示例:
    - _resolve_dynamic_memory_shape(MemorySpace.SM)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    hardware_key = _DYNAMIC_MEMORY_HARDWARE_KEYS.get(space)
    if hardware_key is None:
        return ["?"]
    hardware_value = target_registry.get_current_target_hardware(hardware_key)
    if hardware_value is not None:
        return [hardware_value]
    return ["?"]


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
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="arch.get_dynamic_memory 参数校验",
                expected="space must be MemorySpace",
                actual=type(space).__name__,
                action=_ERROR_ACTION,
            )
        )
    if space not in _DYNAMIC_MEMORY_SPACES:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="arch.get_dynamic_memory 参数校验",
                expected="space must be on-chip MemorySpace",
                actual=str(space),
                action=_ERROR_ACTION,
            )
        )
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
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="arch.launch_kernel 参数校验",
                expected=f"{name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if isinstance(value, int) and value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="arch.launch_kernel 参数校验",
                expected=f"{name} must be > 0",
                actual=str(value),
                action=_ERROR_ACTION,
            )
        )
    return value


def get_block_id() -> SymbolDim:
    """返回当前 block 的执行索引语义。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对外表现为 `SymbolDim("block_id")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 ValueError。

    使用示例:
    - get_block_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_block_id", "block_id")


def get_block_num() -> SymbolDim:
    """返回当前 launch 的 block 数量语义。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对外表现为 `SymbolDim("block_num")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 ValueError。
    - 若当前 target 提供硬件 block_num，优先使用硬件值。

    使用示例:
    - get_block_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_block_num", "block_num", "block_num")


def get_thread_id() -> SymbolDim:
    """返回当前 block 内 thread 执行索引语义。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对外表现为 `SymbolDim("thread_id")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 ValueError。

    使用示例:
    - get_thread_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_thread_id", "thread_id")


def get_thread_num() -> SymbolDim:
    """返回当前 block 内 thread 数量语义。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对外表现为 `SymbolDim("thread_num")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 ValueError。
    - 若当前 target 提供硬件 thread_num，优先使用硬件值。

    使用示例:
    - get_thread_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_thread_num", "thread_num", "thread_num")


def get_subthread_id() -> SymbolDim:
    """返回当前 thread 内 subthread 执行索引语义。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对外表现为 `SymbolDim("subthread_id")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 ValueError。

    使用示例:
    - get_subthread_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_subthread_id", "subthread_id")


def get_subthread_num() -> SymbolDim:
    """返回当前 thread 内 subthread 数量语义。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对外表现为 `SymbolDim("subthread_num")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 ValueError。
    - 若当前 target 提供硬件 subthread_num，优先使用硬件值。

    使用示例:
    - get_subthread_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_subthread_num", "subthread_num", "subthread_num")


def get_dynamic_memory(space: object) -> Memory:
    """返回指定片上空间的动态字节缓冲语义。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 返回 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8` 的一维动态内存描述。
    - 仅允许片上空间 `SM/LM/TSM/TLM`。
    - 当 target registry 启用且不支持该 op，抛 ValueError。
    - 若当前 target 提供硬件容量，优先使用硬件 size 作为 shape。

    使用示例:
    - get_dynamic_memory(MemorySpace.SM)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    _verify_target_registry_support("arch.get_dynamic_memory")
    normalized_space = _ensure_dynamic_memory_space(space)
    shape = _resolve_dynamic_memory_shape(normalized_space)
    return Memory(shape, NumericType.Int8, space=normalized_space, stride=[1])


def launch_kernel(name: str, block: LaunchExtent, thread: LaunchExtent, subthread: LaunchExtent) -> None:
    """记录一次 kernel 启动请求。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验 kernel 名称与三层执行规模。
    - 只保留 operation 层启动语义，返回 `None`。
    - 当 target registry 启用且不支持该 op，抛 ValueError。

    使用示例:
    - launch_kernel("my_kernel", SymbolDim("GRID_X"), 128, 4)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_operation_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    _verify_target_registry_support("arch.launch_kernel")
    if not isinstance(name, str):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="arch.launch_kernel 参数校验",
                expected="name must be str",
                actual=type(name).__name__,
                action=_ERROR_ACTION,
            )
        )
    if name == "":
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="arch.launch_kernel 参数校验",
                expected="name must not be empty",
                actual="empty",
                action=_ERROR_ACTION,
            )
        )
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
