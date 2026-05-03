"""DMA DSL AST builtin registration.


功能说明:
- 注册 `kernel_gen.operation.dma` helper 到 AST parser builtin 注册表。
- 每个 DMA operation 使用一个 `@dsl_builtin(...)` builder 函数直接构造对应 AST 节点。
- 本文件无公开 API；导入本文件只触发 DMA builtin 注册。

API 列表:
- 无；导入本文件只触发 DMA builtin 注册。

使用示例:
- import kernel_gen.dsl.ast.plugin.dma

关联文件:
- spec: spec/dsl/ast/plugin/dma.md
- test: test/dsl/ast/plugin/test_dma.py
- 功能实现: kernel_gen/dsl/ast/plugin/dma.py
"""

from __future__ import annotations

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.nodes import (
    ConstValueAST,
    Diagnostic,
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaDesliceAST,
    DmaFillAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaLoadAST,
    DmaReshapeAST,
    DmaSliceAST,
    DmaStoreAST,
    DmaViewAST,
    MemorySpaceAttrAST,
    MemoryAST,
    PythonObjectAttrAST,
    SymbolDimAST,
    BoolValueAST,
)
from kernel_gen.dsl.ast.plugin.registry import BuiltinCall, dsl_builtin
from kernel_gen.operation import dma
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


@dsl_builtin(dma.alloc, DmaAllocAST)
def _build_alloc(node: BuiltinCall) -> DmaAllocAST:
    """功能说明: 构造 dma.alloc AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 2 or len(args) > 3 or (len(args) == 3 and "space" in kwargs):
        diagnostic = Diagnostic("Unsupported alloc arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    dtype_arg = args[1]
    if isinstance(dtype_arg, ConstValueAST):
        dtype = dtype_arg.raw_value
    elif isinstance(dtype_arg, PythonObjectAttrAST):
        dtype = dtype_arg.attr
    else:
        dtype = dtype_arg
    space_arg = kwargs.get("space", args[2] if len(args) > 2 else MemorySpace.GM)
    if isinstance(space_arg, ConstValueAST):
        space = space_arg.raw_value
    elif isinstance(space_arg, PythonObjectAttrAST):
        space = space_arg.attr
    elif isinstance(space_arg, MemorySpaceAttrAST):
        space = space_arg.space
    else:
        space = space_arg
    if not isinstance(dtype, NumericType):
        diagnostic = Diagnostic("alloc dtype must be NumericType", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if not isinstance(space, MemorySpace):
        diagnostic = Diagnostic("alloc space must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return DmaAllocAST(args[0], dtype, space, kwargs.get("stride"), location=location)


@dsl_builtin(dma.copy, DmaCopyAST)
def _build_copy(node: BuiltinCall) -> DmaCopyAST:
    """功能说明: 构造 dma.copy AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 1 or len(args) > 2 or kwargs:
        diagnostic = Diagnostic("Unsupported copy arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    space_arg = args[1] if len(args) > 1 else MemorySpace.GM
    if isinstance(space_arg, ConstValueAST):
        space = space_arg.raw_value
    elif isinstance(space_arg, PythonObjectAttrAST):
        space = space_arg.attr
    elif isinstance(space_arg, MemorySpaceAttrAST):
        space = space_arg.space
    else:
        space = space_arg
    if not isinstance(space, MemorySpace):
        diagnostic = Diagnostic("copy space must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return DmaCopyAST(args[0], space, location=location)


@dsl_builtin(dma.cast, DmaCastAST)
def _build_cast(node: BuiltinCall) -> DmaCastAST:
    """功能说明: 构造 dma.cast AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 2 or len(args) > 3 or any(key != "memoryspace" for key in kwargs):
        diagnostic = Diagnostic("Unsupported cast arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    dtype_arg = args[1]
    if isinstance(dtype_arg, ConstValueAST):
        dtype = dtype_arg.raw_value
    elif isinstance(dtype_arg, PythonObjectAttrAST):
        dtype = dtype_arg.attr
    else:
        dtype = dtype_arg
    if not isinstance(dtype, NumericType):
        diagnostic = Diagnostic("cast dtype must be NumericType", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if len(args) == 3 and "memoryspace" in kwargs:
        diagnostic = Diagnostic("Unsupported cast arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    memoryspace_arg = kwargs.get("memoryspace", args[2] if len(args) > 2 else None)
    if isinstance(memoryspace_arg, ConstValueAST):
        memoryspace = memoryspace_arg.raw_value
    elif isinstance(memoryspace_arg, PythonObjectAttrAST):
        memoryspace = memoryspace_arg.attr
    elif isinstance(memoryspace_arg, MemorySpaceAttrAST):
        memoryspace = memoryspace_arg.space
    else:
        memoryspace = memoryspace_arg
    if memoryspace is not None and not isinstance(memoryspace, MemorySpace):
        diagnostic = Diagnostic("cast memoryspace must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return DmaCastAST(args[0], dtype, memoryspace, location=location)


@dsl_builtin(dma.view, DmaViewAST)
def _build_view(node: BuiltinCall) -> DmaViewAST:
    """功能说明: 构造 dma.view AST；使用示例: registry 调用该 builder。"""

    args = node.args
    return DmaViewAST(args[0], args[1], args[2], args[3], location=node.location)


@dsl_builtin(dma.reshape, DmaReshapeAST)
def _build_reshape(node: BuiltinCall) -> DmaReshapeAST:
    """功能说明: 构造 dma.reshape AST；使用示例: registry 调用该 builder。"""

    args = node.args
    return DmaReshapeAST(args[0], args[1], location=node.location)


@dsl_builtin(dma.flatten, DmaFlattenAST)
def _build_flatten(node: BuiltinCall) -> DmaFlattenAST:
    """功能说明: 构造 dma.flatten AST；使用示例: registry 调用该 builder。"""

    return DmaFlattenAST(node.args[0], location=node.location)


@dsl_builtin(dma.free, DmaFreeAST)
def _build_free(node: BuiltinCall) -> DmaFreeAST:
    """功能说明: 构造 dma.free AST；使用示例: registry 调用该 builder。"""

    return DmaFreeAST(node.args[0], location=node.location)


@dsl_builtin(dma.fill, DmaFillAST)
def _build_fill(node: BuiltinCall) -> DmaFillAST:
    """功能说明: 构造 dma.fill AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) != 2 or kwargs:
        diagnostic = Diagnostic("Unsupported fill arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if isinstance(args[1], ConstValueAST):
        fill_value = args[1].raw_value
    elif isinstance(args[1], PythonObjectAttrAST):
        fill_value = args[1].attr
    else:
        fill_value = args[1]
    if isinstance(fill_value, str) and fill_value not in {"inf", "-inf"}:
        diagnostic = Diagnostic('fill string literal must be "inf" or "-inf"', location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return DmaFillAST(args[0], args[1], location=location)


@dsl_builtin(dma.load, DmaLoadAST)
def _build_load(node: BuiltinCall) -> DmaLoadAST:
    """功能说明: 构造 dma.load AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 3 or len(args) > 5 or kwargs:
        diagnostic = Diagnostic("Unsupported load arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if not isinstance(args[0], MemoryAST):
        diagnostic = Diagnostic("load source must be MemoryAST", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    space_arg = args[4] if len(args) > 4 else None
    if isinstance(space_arg, ConstValueAST):
        space = space_arg.raw_value
    elif isinstance(space_arg, PythonObjectAttrAST):
        space = space_arg.attr
    elif isinstance(space_arg, MemorySpaceAttrAST):
        space = space_arg.space
    else:
        space = space_arg
    if space is not None and not isinstance(space, MemorySpace):
        diagnostic = Diagnostic("load space must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return DmaLoadAST(args[0], args[1], args[2], args[3] if len(args) > 3 else None, space, location)


@dsl_builtin(dma.slice, DmaSliceAST)
def _build_slice(node: BuiltinCall) -> DmaSliceAST:
    """功能说明: 构造 dma.slice AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 3 or len(args) > 5 or kwargs:
        diagnostic = Diagnostic("Unsupported slice arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if not isinstance(args[0], MemoryAST):
        diagnostic = Diagnostic("slice source must be MemoryAST", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    space_arg = args[4] if len(args) > 4 else None
    if isinstance(space_arg, ConstValueAST):
        space = space_arg.raw_value
    elif isinstance(space_arg, PythonObjectAttrAST):
        space = space_arg.attr
    elif isinstance(space_arg, MemorySpaceAttrAST):
        space = space_arg.space
    else:
        space = space_arg
    if space is not None and not isinstance(space, MemorySpace):
        diagnostic = Diagnostic("slice space must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return DmaSliceAST(args[0], args[1], args[2], args[3] if len(args) > 3 else None, space, location)


@dsl_builtin(dma.store, DmaStoreAST)
def _build_store(node: BuiltinCall) -> DmaStoreAST:
    """功能说明: 构造 dma.store AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 4 or len(args) > 6 or kwargs:
        diagnostic = Diagnostic("Unsupported store arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if isinstance(args[0], (SymbolDimAST, ConstValueAST, BoolValueAST)):
        diagnostic = Diagnostic("store target must be MemoryAST", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    space_arg = args[5] if len(args) > 5 else None
    if isinstance(space_arg, ConstValueAST):
        space = space_arg.raw_value
    elif isinstance(space_arg, PythonObjectAttrAST):
        space = space_arg.attr
    elif isinstance(space_arg, MemorySpaceAttrAST):
        space = space_arg.space
    else:
        space = space_arg
    if space is not None and not isinstance(space, MemorySpace):
        diagnostic = Diagnostic("store space must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return DmaStoreAST(args[0], args[1], args[2], args[3], args[4] if len(args) > 4 else None, space, location)


@dsl_builtin(dma.deslice, DmaDesliceAST)
def _build_deslice(node: BuiltinCall) -> DmaDesliceAST:
    """功能说明: 构造 dma.deslice AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 4 or len(args) > 6 or kwargs:
        diagnostic = Diagnostic("Unsupported deslice arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if isinstance(args[0], (SymbolDimAST, ConstValueAST, BoolValueAST)):
        diagnostic = Diagnostic("deslice target must be MemoryAST", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    space_arg = args[5] if len(args) > 5 else None
    if isinstance(space_arg, ConstValueAST):
        space = space_arg.raw_value
    elif isinstance(space_arg, PythonObjectAttrAST):
        space = space_arg.attr
    elif isinstance(space_arg, MemorySpaceAttrAST):
        space = space_arg.space
    else:
        space = space_arg
    if space is not None and not isinstance(space, MemorySpace):
        diagnostic = Diagnostic("deslice space must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return DmaDesliceAST(args[0], args[1], args[2], args[3], args[4] if len(args) > 4 else None, space, location)

__all__: list[str] = []
