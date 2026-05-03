"""Arch operation API.


功能说明:
- 提供 operation 层的 arch helper，覆盖执行维度查询、动态片上内存入口、barrier 与 kernel 启动描述。
- 区分真实内存空间 `MemorySpace` 与聚合可见域 `BarrierVisibility`，补充 launched body 内的 launch extent 查询语义。

API 列表:
- `class BarrierVisibility()`
- `class BarrierScope()`
- `get_block_id() -> SymbolDim`
- `get_block_num() -> SymbolDim`
- `get_thread_id() -> SymbolDim`
- `get_thread_num() -> SymbolDim`
- `get_subthread_id() -> SymbolDim`
- `get_subthread_num() -> SymbolDim`
- `get_dynamic_memory(space: MemorySpace) -> Memory`
- `barrier(*, visibility: list[BarrierVisibility] | tuple[BarrierVisibility, ...], scope: BarrierScope) -> None`
- `launch_kernel[block: int | SymbolDim, thread: int | SymbolDim, subthread: int | SymbolDim, shared_memory_size: int | SymbolDim](callee: FunctionType, *args: KernelArgument) -> None`

使用示例:
- from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier, get_block_id, get_dynamic_memory, launch_kernel
- bid = get_block_id()
- smem = get_dynamic_memory(MemorySpace.SM)
- barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)
- launch_kernel[1, 128, 4, 0](my_kernel, lhs, rhs, out)

关联文件:
- spec: spec/operation/arch.md
- test: test/operation/test_arch.py
- 功能实现: kernel_gen/operation/arch.py
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
import inspect
from types import FunctionType

from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_ACTUAL,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.target import registry as target_registry

LaunchExtent = int | SymbolDim
LaunchSharedMemorySize = int | SymbolDim
BarrierVisibilityInput = list["BarrierVisibility"] | tuple["BarrierVisibility", ...]
KernelArgument = Memory | SymbolDim | int | float | str | bool | None
_DYNAMIC_MEMORY_SPACES = (
    MemorySpace.SM,
    MemorySpace.LM,
    MemorySpace.TSM,
    MemorySpace.TLM1,
    MemorySpace.TLM2,
    MemorySpace.TLM3,
)
_TARGET_ERROR_SCENE = "arch helper target registry 校验"
_DYNAMIC_MEMORY_HARDWARE_KEYS = {
    MemorySpace.SM: "sm_memory_size",
    MemorySpace.LM: "lm_memory_size",
    MemorySpace.TSM: "tsm_memory_size",
    MemorySpace.TLM1: "tlm1_memory_size",
    MemorySpace.TLM2: "tlm2_memory_size",
    MemorySpace.TLM3: "tlm3_memory_size",
}
_DYNAMIC_MEMORY_FALLBACK_SYMBOLS = {
    MemorySpace.SM: "SM_SIZE",
    MemorySpace.LM: "LM_SIZE",
    MemorySpace.TSM: "TSM_SIZE",
    MemorySpace.TLM1: "TLM1_SIZE",
    MemorySpace.TLM2: "TLM2_SIZE",
    MemorySpace.TLM3: "TLM3_SIZE",
}

class _MissingArgument:
    """标记 barrier 必填关键字未传入。"""


_MISSING_ARGUMENT = _MissingArgument()


class BarrierVisibility(Enum):
    """operation 层 barrier 聚合可见域枚举。


    功能说明:
    - 区分 barrier 聚合可见域与真实内存空间。
    - `TLM` 固定表示覆盖 `TLM1/TLM2/TLM3` 三块真实空间的聚合可见域。

    使用示例:
    - BarrierVisibility.TLM.value

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    TSM = "tsm"
    TLM = "tlm"


_BARRIER_VISIBILITY_SPACES = (BarrierVisibility.TSM, BarrierVisibility.TLM)


class BarrierScope(Enum):
    """operation 层 barrier scope 枚举。"""

    BLOCK = "block"
    THREAD = "thread"
    SUBTHREAD = "subthread"
    GLOBAL = "global"


@dataclass(frozen=True)
class _LaunchContext:
    """记录当前 Python launched body 的 launch extent。"""

    block: LaunchExtent
    thread: LaunchExtent
    subthread: LaunchExtent


_ACTIVE_LAUNCH_CONTEXT: ContextVar[_LaunchContext | None] = ContextVar(
    "kernel_gen.operation.arch.active_launch_context",
    default=None,
)


def _verify_target_registry_support(op_name: str) -> None:
    """按当前 target registry 配置校验 arch helper 支持性。


    功能说明:
    - 在启用 target registry 校验时，阻止不支持的 helper 被调用。

    使用示例:
    - _verify_target_registry_support("arch.get_thread_id")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    current_target = target_registry.get_current_target()
    if current_target is None:
        return
    try:
        supported = target_registry.is_arch_op_supported(current_target, op_name)
    except ValueError as exc:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=_TARGET_ERROR_SCENE,
                expected=str(exc),
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        ) from exc
    except (AttributeError, TypeError, KeyError) as exc:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=_TARGET_ERROR_SCENE,
                expected="current target registry missing required arch fields",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        ) from exc
    if not supported:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=_TARGET_ERROR_SCENE,
                expected=f"{op_name} is not supported by target {current_target}",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )


def _get_current_target_hardware_value(key: str) -> int | None:
    """安全读取当前 target registry 的设备字段。


    功能说明:
    - 复用 `target_registry.get_current_target_hardware(...)` 读取设备值。
    - 当当前 target 资产缺少 `hardware` 等关键字段时，统一抛出显式 `KernelCodeError`。

    使用示例:
    - _get_current_target_hardware_value("thread_num")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    try:
        return target_registry.get_current_target_hardware(key)
    except ValueError as exc:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=_TARGET_ERROR_SCENE,
                expected=str(exc),
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        ) from exc
    except (AttributeError, TypeError, KeyError) as exc:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene=_TARGET_ERROR_SCENE,
                expected=f"current target registry missing required hardware field: {key}",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        ) from exc


def _build_query_symbol(name: str) -> SymbolDim:
    """构造执行维度查询返回的 SymbolDim。


    功能说明:
    - 为六个执行维度查询 helper 复用统一的 SymbolDim 构造路径。

    使用示例:
    - _build_query_symbol("block_id")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return SymbolDim(name)


def _coerce_launch_extent_symbol(value: LaunchExtent) -> SymbolDim:
    """把 launch extent 统一规整为 `SymbolDim`。


    功能说明:
    - launched body 查询命中当前 launch 上下文时，统一返回 `SymbolDim`。
    - `int` extent 转为静态 `SymbolDim(int)`；`SymbolDim` 直接复用。

    使用示例:
    - _coerce_launch_extent_symbol(8)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if isinstance(value, SymbolDim):
        return value
    return SymbolDim(value)


def _resolve_launch_context_symbol(symbol_name: str) -> SymbolDim | None:
    """读取当前 launched body 的 launch extent 语义。


    功能说明:
    - 在 `launch_kernel[...]` 启动请求执行期间，把 `block/thread/subthread` extent 暴露给数量类 helper。
    - 若当前不存在 launch 上下文，则返回 `None`。

    使用示例:
    - _resolve_launch_context_symbol("thread_num")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    context = _ACTIVE_LAUNCH_CONTEXT.get()
    if context is None:
        return None
    if symbol_name == "block_num":
        return _coerce_launch_extent_symbol(context.block)
    if symbol_name == "thread_num":
        return _coerce_launch_extent_symbol(context.thread)
    if symbol_name == "subthread_num":
        return _coerce_launch_extent_symbol(context.subthread)
    return None


def _require_current_target_hardware(op_name: str, hardware_key: str) -> int | None:
    """读取当前 target 需要的硬件字段，缺失时抛出一致错误。


    功能说明:
    - 未启用 current target 时返回 `None`，保持 helper 的符号回退语义。
    - 启用 current target 且字段缺失时，统一抛出 target registry 缺字段错误。

    使用示例:
    - _require_current_target_hardware("arch.get_thread_num", "thread_num")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    current_target = target_registry.get_current_target()
    if current_target is None:
        return None
    hardware_value = _get_current_target_hardware_value(hardware_key)
    if hardware_value is not None:
        return hardware_value
    raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
        ERROR_TEMPLATE.format(
            scene=_TARGET_ERROR_SCENE,
            expected=f"{op_name} requires target {current_target} hardware.{hardware_key}",
            actual=ERROR_ACTUAL,
            action=ERROR_ACTION,
        )
    )


def _resolve_query_symbol(op_name: str, symbol_name: str, hardware_key: str | None = None) -> SymbolDim:
    """构造执行维度查询 helper 的返回 SymbolDim。


    功能说明:
    - 先执行 target registry 支持性校验。
    - 当硬件值存在时优先使用硬件数值，否则回退到符号名称。
    - 已启用 target registry 但缺失必需硬件字段时，抛出一致错误。

    使用示例:
    - _resolve_query_symbol("arch.get_block_num", "block_num", "block_num")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    _verify_target_registry_support(op_name)
    launch_symbol = _resolve_launch_context_symbol(symbol_name)
    if launch_symbol is not None:
        return launch_symbol
    if hardware_key is not None:
        hardware_value = _require_current_target_hardware(op_name, hardware_key)
        if hardware_value is not None:
            return SymbolDim(hardware_value)
    return _build_query_symbol(symbol_name)


def _resolve_dynamic_memory_shape(space: MemorySpace) -> list[int | str]:
    """解析动态内存 helper 的 shape 返回。


    功能说明:
    - 优先使用 target hardware 中的容量信息。
    - 已启用 target registry 但缺失容量字段时，抛出一致错误。
    - 未启用 target registry 时，回退为空间对应的一维容量符号。

    使用示例:
    - _resolve_dynamic_memory_shape(MemorySpace.SM)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    hardware_key = _DYNAMIC_MEMORY_HARDWARE_KEYS.get(space)
    if hardware_key is None:
        return ["?"]
    hardware_value = _require_current_target_hardware("arch.get_dynamic_memory", hardware_key)
    if hardware_value is not None:
        return [hardware_value]
    return [_DYNAMIC_MEMORY_FALLBACK_SYMBOLS[space]]


def _ensure_dynamic_memory_space(space: MemorySpace) -> MemorySpace:
    """校验动态内存 helper 的空间参数。


    功能说明:
    - 仅接受 `MemorySpace`。
    - 仅允许片上空间 `SM/LM/TSM/TLM1/TLM2/TLM3`。

    使用示例:
    - _ensure_dynamic_memory_space(MemorySpace.SM)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if not isinstance(space, MemorySpace):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.get_dynamic_memory 参数校验",
                expected="space must be MemorySpace",
                actual=type(space).__name__,
                action=ERROR_ACTION,
            )
        )
    if space not in _DYNAMIC_MEMORY_SPACES:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.get_dynamic_memory 参数校验",
                expected="space must be on-chip MemorySpace",
                actual=str(space),
                action=ERROR_ACTION,
            )
        )
    return space


def _ensure_launch_extent(value: LaunchExtent, name: str) -> LaunchExtent:
    """校验 kernel 启动规模参数。


    功能说明:
    - 仅接受正整数或 `SymbolDim`。
    - 静态整数要求 `> 0`。

    使用示例:
    - _ensure_launch_extent(128, "thread")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if isinstance(value, bool) or not isinstance(value, (int, SymbolDim)):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.launch 参数校验",
                expected=f"{name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    if isinstance(value, int) and value <= 0:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.launch 参数校验",
                expected=f"{name} must be > 0",
                actual=str(value),
                action=ERROR_ACTION,
            )
    )
    return value


def _ensure_launch_shared_memory_size(value: LaunchSharedMemorySize, name: str) -> LaunchSharedMemorySize:
    """校验 kernel launch 的共享内存规模参数。


    功能说明:
    - 仅接受非负整数或 `SymbolDim`。
    - 静态整数要求 `>= 0`。

    使用示例:
    - _ensure_launch_shared_memory_size(0, "shared_memory_size")

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if isinstance(value, bool) or not isinstance(value, (int, SymbolDim)):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.launch 参数校验",
                expected=f"{name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    if isinstance(value, int) and value < 0:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.launch 参数校验",
                expected=f"{name} must be >= 0",
                actual=str(value),
                action=ERROR_ACTION,
            )
        )
    return value


def _ensure_launch_callee(callee: FunctionType) -> FunctionType:
    """校验 `launch_kernel` 的 `callee` 参数。


    功能说明:
    - 仅接受 Python 函数对象。
    - 显式拒绝字符串名称、`Memory`、`SymbolDim` 与其他 callable/object。

    使用示例:
    - _ensure_launch_callee(my_kernel)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if not inspect.isfunction(callee):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.launch 参数校验",
                expected="callee must be function object",
                actual=type(callee).__name__,
                action=ERROR_ACTION,
            )
        )
    return callee


def _ensure_barrier_visibility(visibility: BarrierVisibilityInput) -> tuple[BarrierVisibility, ...]:
    """校验 barrier 的 visibility 列表。


    功能说明:
    - 仅接受 `list[BarrierVisibility] | tuple[BarrierVisibility, ...]`。
    - 当前公开合同要求元素唯一，且必须且只能包含 `TSM/TLM`。

    使用示例:
    - _ensure_barrier_visibility([BarrierVisibility.TSM, BarrierVisibility.TLM])

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if not isinstance(visibility, (list, tuple)):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.barrier 参数校验",
                expected="visibility must be list[BarrierVisibility] or tuple[BarrierVisibility, ...]",
                actual=type(visibility).__name__,
                action=ERROR_ACTION,
            )
        )
    normalized_visibility = tuple(visibility)
    if not normalized_visibility:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.barrier 参数校验",
                expected="visibility must not be empty",
                actual="empty",
                action=ERROR_ACTION,
            )
        )
    if any(not isinstance(space, BarrierVisibility) for space in normalized_visibility):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.barrier 参数校验",
                expected="visibility items must be BarrierVisibility",
                actual=str(tuple(type(space).__name__ for space in normalized_visibility)),
                action=ERROR_ACTION,
            )
        )
    if len(set(normalized_visibility)) != len(normalized_visibility):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.barrier 参数校验",
                expected="visibility must not contain duplicates",
                actual=str([visibility_item.name for visibility_item in normalized_visibility]),
                action=ERROR_ACTION,
            )
        )
    if set(normalized_visibility) != set(_BARRIER_VISIBILITY_SPACES):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.barrier 参数校验",
                expected="visibility must contain TSM and TLM exactly once",
                actual=str([visibility_item.name for visibility_item in normalized_visibility]),
                action=ERROR_ACTION,
            )
        )
    return normalized_visibility


def _ensure_barrier_scope(scope: BarrierScope) -> BarrierScope:
    """校验 barrier 的 scope 参数。


    功能说明:
    - 仅接受 `BarrierScope` 枚举。
    - operation 合同允许 `BLOCK/THREAD/SUBTHREAD/GLOBAL` 四个公开 scope。

    使用示例:
    - _ensure_barrier_scope(BarrierScope.THREAD)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if not isinstance(scope, BarrierScope):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.barrier 参数校验",
                expected="scope must be BarrierScope",
                actual=type(scope).__name__,
                action=ERROR_ACTION,
            )
        )
    return scope


@contextmanager
def _launch_context(block: LaunchExtent, thread: LaunchExtent, subthread: LaunchExtent):
    """在 Python helper 中建立一次临时 launch 上下文。


    功能说明:
    - 供 `launch_kernel[...]` 在调用 Python 函数对象时临时暴露 launch extent。
    - 离开上下文后恢复上一层 launch 语义，支持嵌套 launch。

    使用示例:
    - with _launch_context(1, 128, 4): ...

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    token = _ACTIVE_LAUNCH_CONTEXT.set(_LaunchContext(block=block, thread=thread, subthread=subthread))
    try:
        yield
    finally:
        _ACTIVE_LAUNCH_CONTEXT.reset(token)


def get_block_id() -> SymbolDim:
    """返回当前 block 的执行索引语义。


    功能说明:
    - 对外表现为 `SymbolDim("block_id")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 KernelCodeError。

    使用示例:
    - get_block_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_block_id", "block_id")


def get_block_num() -> SymbolDim:
    """返回当前 launch 的 block 数量语义。


    功能说明:
    - 对外表现为 `SymbolDim("block_num")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 KernelCodeError。
    - launched body 内优先返回当前 launch 的 block extent。
    - 无 launch 上下文时，若当前 target 提供硬件 block_num，则优先使用硬件值。

    使用示例:
    - get_block_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_block_num", "block_num", "block_num")


def get_thread_id() -> SymbolDim:
    """返回当前 block 内 thread 执行索引语义。


    功能说明:
    - 对外表现为 `SymbolDim("thread_id")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 KernelCodeError。

    使用示例:
    - get_thread_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_thread_id", "thread_id")


def get_thread_num() -> SymbolDim:
    """返回当前 block 内 thread 数量语义。


    功能说明:
    - 对外表现为 `SymbolDim("thread_num")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 KernelCodeError。
    - launched body 内优先返回当前 launch 的 thread extent。
    - 无 launch 上下文时，若当前 target 提供硬件 thread_num，则优先使用硬件值。

    使用示例:
    - get_thread_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_thread_num", "thread_num", "thread_num")


def get_subthread_id() -> SymbolDim:
    """返回当前 thread 内 subthread 执行索引语义。


    功能说明:
    - 对外表现为 `SymbolDim("subthread_id")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 KernelCodeError。

    使用示例:
    - get_subthread_id()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_subthread_id", "subthread_id")


def get_subthread_num() -> SymbolDim:
    """返回当前 thread 内 subthread 数量语义。


    功能说明:
    - 对外表现为 `SymbolDim("subthread_num")` 风格标量。
    - 当 target registry 启用且不支持该 op，抛 KernelCodeError。
    - launched body 内优先返回当前 launch 的 subthread extent。
    - 无 launch 上下文时，若当前 target 提供硬件 subthread_num，则优先使用硬件值。

    使用示例:
    - get_subthread_num()

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    return _resolve_query_symbol("arch.get_subthread_num", "subthread_num", "subthread_num")


def get_dynamic_memory(space: MemorySpace) -> Memory:
    """返回指定片上空间的动态字节缓冲语义。


    功能说明:
    - 返回 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8` 的一维动态内存描述。
    - 仅允许片上空间 `SM/LM/TSM/TLM1/TLM2/TLM3`。
    - 当 target registry 启用且不支持该 op，抛 KernelCodeError。
    - 若当前 target 提供硬件容量，优先使用硬件 size 作为 shape。

    使用示例:
    - get_dynamic_memory(MemorySpace.SM)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    _verify_target_registry_support("arch.get_dynamic_memory")
    normalized_space = _ensure_dynamic_memory_space(space)
    shape = _resolve_dynamic_memory_shape(normalized_space)
    return Memory(shape, NumericType.Int8, space=normalized_space, stride=[1])


def barrier(
    *,
    visibility: BarrierVisibilityInput | _MissingArgument = _MISSING_ARGUMENT,
    scope: BarrierScope | _MissingArgument = _MISSING_ARGUMENT,
) -> None:
    """记录一次 block 级 barrier 请求。


    功能说明:
    - 仅接受 `visibility=[TSM, TLM]` 与公开 `BarrierScope` 枚举成员。
    - 对外只表达同步语义，不返回句柄或状态值。
    - 当 target registry 启用且不支持该 op，抛 KernelCodeError。

    使用示例:
    - barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    if visibility is _MISSING_ARGUMENT:
        raise kernel_code_error(
            ErrorKind.CONTRACT,
            ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.barrier 参数校验",
                expected="visibility is required",
                actual="missing",
                action=ERROR_ACTION,
            ),
        )
    if scope is _MISSING_ARGUMENT:
        raise kernel_code_error(
            ErrorKind.CONTRACT,
            ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="arch.barrier 参数校验",
                expected="scope is required",
                actual="missing",
                action=ERROR_ACTION,
            ),
        )
    _verify_target_registry_support("arch.barrier")
    _ensure_barrier_visibility(visibility)
    _ensure_barrier_scope(scope)
    return None


def _launch_kernel_impl(
    callee: FunctionType,
    block: LaunchExtent,
    thread: LaunchExtent,
    subthread: LaunchExtent,
    shared_memory_size: LaunchSharedMemorySize,
    args: tuple[KernelArgument, ...],
) -> None:
    """执行一次 kernel 启动请求的共有实现。


    功能说明:
    - 校验 `callee` 与 launch 规模，并保留尾部 kernel 参数顺序。
    - 只在调用 Python 函数对象时临时建立 launch 上下文，让数量类 helper 暴露本次 launch extent。
    - 仅保留 operation 层启动语义，返回 `None`，不返回事件、句柄或状态值。
    - 当 target registry 启用且不支持该 op，抛 `KernelCodeError`。

    使用示例:
    - _launch_kernel_impl(my_kernel, 1, 128, 4, 0, (lhs, rhs, out))

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    _verify_target_registry_support("arch.launch")
    normalized_callee = _ensure_launch_callee(callee)
    normalized_block = _ensure_launch_extent(block, "block")
    normalized_thread = _ensure_launch_extent(thread, "thread")
    normalized_subthread = _ensure_launch_extent(subthread, "subthread")
    _ensure_launch_shared_memory_size(shared_memory_size, "shared_memory_size")
    with _launch_context(normalized_block, normalized_thread, normalized_subthread):
        normalized_callee(*args)
    return None


@dataclass(frozen=True)
class _LaunchKernelInvocation:
    """记录一次 `launch_kernel[...]` 下标式调用的 launch extent。


    功能说明:
    - 绑定 `block/thread/subthread/shared_memory_size` 四个编译期 extent。
    - 调用时再接收 `callee` 与尾部 kernel 参数。

    使用示例:
    - launch_kernel[1, 4, 1, 0](kernel_body, lhs, rhs, out)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    block: LaunchExtent
    thread: LaunchExtent
    subthread: LaunchExtent
    shared_memory_size: LaunchSharedMemorySize

    def __call__(self, callee: FunctionType, *args: KernelArgument) -> None:
        """按绑定好的 extent 执行一次 kernel 启动请求。"""

        return _launch_kernel_impl(callee, self.block, self.thread, self.subthread, self.shared_memory_size, args)


class _LaunchKernelBuilder:
    """公开 `launch_kernel` 入口的 builder 对象。


    功能说明:
    - 公开入口固定为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`。
    - 直调用 `launch_kernel(...)` 不再属于公开合同，必须在调用边界显式失败。

    使用示例:
    - launch_kernel[1, 4, 1, 0](kernel_body, lhs, rhs, out)

    关联文件:
    - spec: spec/operation/arch.md
    - test: test/operation/test_arch.py
    - 功能实现: kernel_gen/operation/arch.py
    """

    def __call__(self, *args: KernelArgument, **kwargs: KernelArgument) -> None:
        """拒绝旧直调用，要求使用下标式公开入口。"""

        del args, kwargs
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            "launch_kernel public API is "
            "launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)"
        )

    def __getitem__(
        self,
        extents: LaunchExtent | tuple[LaunchExtent, LaunchExtent, LaunchExtent, LaunchSharedMemorySize],
    ) -> _LaunchKernelInvocation:
        """绑定 `launch_kernel[...]` 的四个 launch extent。"""

        if not isinstance(extents, tuple):
            extents = (extents,)
        if len(extents) != 4:
            raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
                ERROR_TEMPLATE.format(
                    scene="arch.launch 参数校验",
                    expected="launch_kernel extents must contain block, thread, subthread, shared_memory_size",
                    actual=str(len(extents)),
                    action=ERROR_ACTION,
                )
            )
        block = _ensure_launch_extent(extents[0], "block")
        thread = _ensure_launch_extent(extents[1], "thread")
        subthread = _ensure_launch_extent(extents[2], "subthread")
        shared_memory_size = _ensure_launch_shared_memory_size(extents[3], "shared_memory_size")
        return _LaunchKernelInvocation(block, thread, subthread, shared_memory_size)


launch_kernel = _LaunchKernelBuilder()


__all__ = [
    "BarrierVisibility",
    "BarrierScope",
    "get_block_id",
    "get_block_num",
    "get_thread_id",
    "get_thread_num",
    "get_subthread_id",
    "get_subthread_num",
    "get_dynamic_memory",
    "barrier",
    "launch_kernel",
]
