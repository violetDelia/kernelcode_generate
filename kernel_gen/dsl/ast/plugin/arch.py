"""Arch DSL AST builtin registration.


功能说明:
- 注册 `kernel_gen.operation.arch` helper 到 AST parser builtin 注册表。
- 每个 arch operation 使用一个 `@dsl_builtin(...)` builder 函数直接构造对应 AST 节点。
- 本文件无公开 API；导入本文件只触发 arch builtin 注册。

API 列表:
- 无；导入本文件只触发 arch builtin 注册。

使用示例:
- import kernel_gen.dsl.ast.plugin.arch

关联文件:
- spec: spec/dsl/ast/plugin/arch.md
- test: test/dsl/ast/plugin/test_arch.py
- 功能实现: kernel_gen/dsl/ast/plugin/arch.py
"""

from __future__ import annotations

from types import FunctionType

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.nodes import (
    ArchBarrierAST,
    ArchGetBlockIdAST,
    ArchGetBlockNumAST,
    ArchGetDynamicMemoryAST,
    ArchGetSubthreadIdAST,
    ArchGetSubthreadNumAST,
    ArchGetThreadIdAST,
    ArchGetThreadNumAST,
    ArchLaunchKernelAST,
    ConstValueAST,
    Diagnostic,
    ListAST,
    PythonObjectAttrAST,
)
from kernel_gen.dsl.ast.plugin.registry import BuiltinCall, dsl_builtin
from kernel_gen.operation import arch
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility
from kernel_gen.symbol_variable.memory import MemorySpace


@dsl_builtin(arch.get_dynamic_memory, ArchGetDynamicMemoryAST)
def _build_get_dynamic_memory(node: BuiltinCall) -> ArchGetDynamicMemoryAST:
    """功能说明: 构造 get_dynamic_memory AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) != 1 or kwargs:
        diagnostic = Diagnostic("Unsupported get_dynamic_memory arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if isinstance(args[0], ConstValueAST):
        space = args[0].raw_value
    elif isinstance(args[0], PythonObjectAttrAST):
        space = args[0].attr
    else:
        space = args[0]
    if not isinstance(space, MemorySpace):
        diagnostic = Diagnostic("get_dynamic_memory space must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if space is MemorySpace.GM:
        diagnostic = Diagnostic("get_dynamic_memory space must be on-chip MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchGetDynamicMemoryAST(space, location=location)


@dsl_builtin(arch.barrier, ArchBarrierAST)
def _build_barrier(node: BuiltinCall) -> ArchBarrierAST:
    """功能说明: 构造 barrier AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if args or set(kwargs) != {"visibility", "scope"}:
        diagnostic = Diagnostic("Unsupported barrier arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    visibility = kwargs["visibility"]
    scope_arg = kwargs["scope"]
    if isinstance(scope_arg, ConstValueAST):
        scope = scope_arg.raw_value
    elif isinstance(scope_arg, PythonObjectAttrAST):
        scope = scope_arg.attr
    else:
        scope = scope_arg
    if isinstance(visibility, ListAST):
        visibility_items = []
        for item in visibility.items:
            if isinstance(item, ConstValueAST):
                visibility_items.append(item.raw_value)
            elif isinstance(item, PythonObjectAttrAST):
                visibility_items.append(item.attr)
            else:
                visibility_items.append(item)
    else:
        if isinstance(visibility, ConstValueAST):
            visibility_items = visibility.raw_value
        elif isinstance(visibility, PythonObjectAttrAST):
            visibility_items = visibility.attr
        else:
            visibility_items = visibility
    if not isinstance(visibility_items, list) or not visibility_items or not all(isinstance(item, BarrierVisibility) for item in visibility_items):
        diagnostic = Diagnostic("barrier visibility must be non-empty BarrierVisibility list", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if not isinstance(scope, BarrierScope):
        diagnostic = Diagnostic("barrier scope must be BarrierScope", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchBarrierAST(visibility_items, scope, location=location)


@dsl_builtin(arch.launch_kernel, ArchLaunchKernelAST)
def _build_launch_kernel(node: BuiltinCall) -> ArchLaunchKernelAST:
    """功能说明: 构造 launch_kernel AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    launch_extents = node.launch_extents
    if kwargs:
        diagnostic = Diagnostic("Unsupported launch_kernel arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if launch_extents is not None:
        if len(launch_extents) != 4 or len(args) < 1:
            diagnostic = Diagnostic("Unsupported launch_kernel arity", location)
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
        if isinstance(args[0], ConstValueAST):
            callee = args[0].raw_value
        elif isinstance(args[0], PythonObjectAttrAST):
            callee = args[0].attr
        else:
            callee = args[0]
        launch_args = args[1:]
        block, thread, subthread, shared_memory_size = launch_extents
    else:
        if len(args) < 5:
            diagnostic = Diagnostic("Unsupported launch_kernel arity", location)
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
        if isinstance(args[0], ConstValueAST):
            callee = args[0].raw_value
        elif isinstance(args[0], PythonObjectAttrAST):
            callee = args[0].attr
        else:
            callee = args[0]
        block, thread, subthread, shared_memory_size = args[1:5]
        launch_args = args[5:]
    if not isinstance(callee, FunctionType):
        diagnostic = Diagnostic("launch_kernel callee must be function symbol reference", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    for extent_name, extent_value in (("block", block), ("thread", thread), ("subthread", subthread)):
        if isinstance(extent_value, ConstValueAST):
            raw_extent = extent_value.raw_value
        elif isinstance(extent_value, PythonObjectAttrAST):
            raw_extent = extent_value.attr
        else:
            raw_extent = extent_value
        if isinstance(raw_extent, int) and raw_extent <= 0:
            diagnostic = Diagnostic(f"launch_kernel {extent_name} must be > 0", location)
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if isinstance(shared_memory_size, ConstValueAST):
        raw_shared = shared_memory_size.raw_value
    elif isinstance(shared_memory_size, PythonObjectAttrAST):
        raw_shared = shared_memory_size.attr
    else:
        raw_shared = shared_memory_size
    if isinstance(raw_shared, int) and raw_shared < 0:
        diagnostic = Diagnostic("launch_kernel shared_memory_size must be >= 0", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchLaunchKernelAST(callee.__name__, block, thread, subthread, launch_args, shared_memory_size, location=location)


@dsl_builtin(arch.get_block_id, ArchGetBlockIdAST)
def _build_get_block_id(node: BuiltinCall) -> ArchGetBlockIdAST:
    """功能说明: 构造 get_block_id AST；使用示例: registry 调用该 builder。"""

    if node.args or node.kwargs:
        diagnostic = Diagnostic("Unsupported get_block_id arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchGetBlockIdAST(location=node.location)


@dsl_builtin(arch.get_block_num, ArchGetBlockNumAST)
def _build_get_block_num(node: BuiltinCall) -> ArchGetBlockNumAST:
    """功能说明: 构造 get_block_num AST；使用示例: registry 调用该 builder。"""

    if node.args or node.kwargs:
        diagnostic = Diagnostic("Unsupported get_block_num arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchGetBlockNumAST(location=node.location)


@dsl_builtin(arch.get_subthread_id, ArchGetSubthreadIdAST)
def _build_get_subthread_id(node: BuiltinCall) -> ArchGetSubthreadIdAST:
    """功能说明: 构造 get_subthread_id AST；使用示例: registry 调用该 builder。"""

    if node.args or node.kwargs:
        diagnostic = Diagnostic("Unsupported get_subthread_id arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchGetSubthreadIdAST(location=node.location)


@dsl_builtin(arch.get_subthread_num, ArchGetSubthreadNumAST)
def _build_get_subthread_num(node: BuiltinCall) -> ArchGetSubthreadNumAST:
    """功能说明: 构造 get_subthread_num AST；使用示例: registry 调用该 builder。"""

    if node.args or node.kwargs:
        diagnostic = Diagnostic("Unsupported get_subthread_num arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchGetSubthreadNumAST(location=node.location)


@dsl_builtin(arch.get_thread_id, ArchGetThreadIdAST)
def _build_get_thread_id(node: BuiltinCall) -> ArchGetThreadIdAST:
    """功能说明: 构造 get_thread_id AST；使用示例: registry 调用该 builder。"""

    if node.args or node.kwargs:
        diagnostic = Diagnostic("Unsupported get_thread_id arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchGetThreadIdAST(location=node.location)


@dsl_builtin(arch.get_thread_num, ArchGetThreadNumAST)
def _build_get_thread_num(node: BuiltinCall) -> ArchGetThreadNumAST:
    """功能说明: 构造 get_thread_num AST；使用示例: registry 调用该 builder。"""

    if node.args or node.kwargs:
        diagnostic = Diagnostic("Unsupported get_thread_num arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return ArchGetThreadNumAST(location=node.location)

__all__: list[str] = []
