"""DSL AST DMA node definitions.


功能说明:
- 定义 DMA helper 对应的 AST 节点，节点只保存 DSL 语义数据，不执行 lowering。

API 列表:
- `DmaAllocAST(shape: SymbolListAST, dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, space: MemorySpaceAttrAST = ..., stride: SymbolListAST | None = None, location: SourceLocation | None = None)`
- `DmaCopyAST(source: ValueAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- `DmaCastAST(source: ValueAST, dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, memoryspace: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `DmaViewAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST, location: SourceLocation | None = None)`
- `DmaReshapeAST(source: ValueAST, shape: SymbolListAST, location: SourceLocation | None = None)`
- `DmaFlattenAST(source: ValueAST, location: SourceLocation | None = None)`
- `DmaFreeAST(value: ValueAST, location: SourceLocation | None = None)`
- `DmaFillAST(target: ValueAST, value: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- `DmaLoadAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `DmaSliceAST(source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `DmaStoreAST(target: ValueAST, source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `DmaDesliceAST(target: ValueAST, source: ValueAST, offset: SymbolListAST, size: SymbolListAST, stride: SymbolListAST | None = None, space: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`

使用示例:
- from kernel_gen.dsl.ast.nodes.dma import DmaAllocAST
- node = DmaAllocAST(shape=[], dtype=NumericType.Float32)

关联文件:
- spec: spec/dsl/ast/nodes/dma.md
- test: test/dsl/ast/nodes/test_dma.py
- 功能实现: kernel_gen/dsl/ast/nodes/dma.py
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import ClassVar, TypeAlias

from xdsl.context import Context
from xdsl.dialects import arith
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, FloatAttr, IntAttr, IntegerType, StringAttr, i1
from xdsl.ir import Block, Operation, SSAValue
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCastOp, DmaCopyOp, DmaDesliceOp, DmaFreeOp, DmaReshapeOp, DmaSliceOp, DmaStoreOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolDivOp, SymbolFloorDivOp, SymbolGetDimOp, SymbolIterType, SymbolMulOp, SymbolSubOp, SymbolValueType
from kernel_gen.operation import dma
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from .attr import (
    BoolTypeAttrAST,
    EmitMlirResult,
    FloatTypeAttrAST,
    IntTypeAttrAST,
    MemorySpaceAttrAST,
    SourceLocation,
)
from .basic import (
    BoolValueAST,
    MemoryAST,
    StatementAST,
    ValueAST,
)
from .symbol import (
    ConstValueAST,
    SymbolAddAST,
    SymbolBinaryAST,
    SymbolDimAST,
    SymbolFloorDivAST,
    SymbolListAST,
    SymbolMulAST,
    SymbolSubAST,
    SymbolTrueDivAST,
)

SymbolRuntimeValue: TypeAlias = "int | float | str | bool | SymbolDim"


@dataclass
class DmaAllocAST(ValueAST):
    """DMA alloc 节点。


    功能说明:
    - 表示 `alloc(...)` 的 DSL 调用。

    使用示例:
    - DmaAllocAST(shape=SymbolListAST([4]), dtype=FloatTypeAttrAST(NumericType.Float32), space=MemorySpaceAttrAST(MemorySpace.SM))

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    shape: SymbolListAST
    dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST
    space: MemorySpaceAttrAST = field(default_factory=lambda: MemorySpaceAttrAST(MemorySpace.GM))
    stride: SymbolListAST | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.shape, SymbolListAST):
            self.shape = SymbolListAST(self.shape, self.location)
        if not isinstance(self.dtype, (IntTypeAttrAST, FloatTypeAttrAST, BoolTypeAttrAST)):
            dtype_node = {
                NumericType.Bool: BoolTypeAttrAST(self.location),
                NumericType.Int8: IntTypeAttrAST(8, True, self.location),
                NumericType.Int16: IntTypeAttrAST(16, True, self.location),
                NumericType.Int32: IntTypeAttrAST(32, True, self.location),
                NumericType.Int64: IntTypeAttrAST(64, True, self.location),
                NumericType.Uint8: IntTypeAttrAST(8, False, self.location),
                NumericType.Uint16: IntTypeAttrAST(16, False, self.location),
                NumericType.Uint32: IntTypeAttrAST(32, False, self.location),
                NumericType.Uint64: IntTypeAttrAST(64, False, self.location),
                NumericType.Float16: FloatTypeAttrAST(NumericType.Float16, self.location),
                NumericType.BFloat16: FloatTypeAttrAST(NumericType.BFloat16, self.location),
                NumericType.Float32: FloatTypeAttrAST(NumericType.Float32, self.location),
                NumericType.Float64: FloatTypeAttrAST(NumericType.Float64, self.location),
            }.get(self.dtype)
            if dtype_node is None:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "alloc dtype must be a public dtype attr")
            self.dtype = dtype_node
        if not isinstance(self.space, MemorySpaceAttrAST):
            self.space = MemorySpaceAttrAST(self.space, self.location)
        if self.stride is not None and not isinstance(self.stride, SymbolListAST):
            self.stride = SymbolListAST(self.stride, self.location)

    def result_memory(self) -> Memory | None:
        """返回 `dma.alloc` 的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - alloc 节点自身负责从 shape/dtype/space/stride 字段推导 memory。

        使用示例:
        - memory = alloc_ast.result_memory()
        """

        shape = self.shape.result_symbols()
        if shape is None:
            return None
        stride: list[SymbolRuntimeValue] | None = None
        if self.stride is not None:
            stride = self.stride.result_symbols()
            if stride is None:
                return None
        dtype = MemoryAST.numeric_type_from_dtype_attr(self.dtype)
        return dma.alloc(shape, dtype, self.space.space, stride=stride)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 DMA alloc 节点发射为 `dma.alloc`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        if isinstance(self.dtype, BoolTypeAttrAST):
            dtype_value = NumericType.Bool
        elif isinstance(self.dtype, FloatTypeAttrAST):
            dtype_value = self.dtype.dtype
        elif isinstance(self.dtype, IntTypeAttrAST):
            dtype_value = {
                (8, True): NumericType.Int8,
                (16, True): NumericType.Int16,
                (32, True): NumericType.Int32,
                (64, True): NumericType.Int64,
                (8, False): NumericType.Uint8,
                (16, False): NumericType.Uint16,
                (32, False): NumericType.Uint32,
                (64, False): NumericType.Uint64,
            }.get((self.dtype.bits, self.dtype.signed), NumericType.Int32)
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "alloc dtype must be a public dtype attr")
        space_value = self.space.space
        shape_items = list(self.shape.items)
        shape_values: list[SymbolRuntimeValue] = []
        shape_attr_values: list[SymbolRuntimeValue] = []
        dynamic_shape: list[SSAValue] = []
        pre_emitted_shape_values: dict[int, SSAValue] = {}
        if any(isinstance(item, SymbolBinaryAST) for item in shape_items):
            for item in shape_items:
                if isinstance(item, SymbolBinaryAST):
                    for operand in (item.lhs, item.rhs):
                        if isinstance(operand, ConstValueAST) and isinstance(operand.raw_value, int) and not isinstance(operand.raw_value, bool):
                            const_value = operand.emit_mlir(ctx, block)
                            if isinstance(const_value, Operation):
                                block.add_op(const_value)
                                const_value = const_value.results[0]
                            if not isinstance(const_value, SSAValue):
                                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "alloc shape const must lower to symbol.int")
                            pre_emitted_shape_values[id(operand)] = const_value
        for item in shape_items:
            if isinstance(item, ConstValueAST):
                shape_values.append(item.raw_value)
                shape_attr_values.append(item.raw_value)
            elif isinstance(item, SymbolBinaryAST):
                lhs = pre_emitted_shape_values.get(id(item.lhs))
                if lhs is None:
                    lhs_emitted = item.lhs.emit_mlir(ctx, block)
                    if isinstance(lhs_emitted, Operation):
                        block.add_op(lhs_emitted)
                        lhs = lhs_emitted.results[0]
                    else:
                        lhs = lhs_emitted
                rhs = pre_emitted_shape_values.get(id(item.rhs))
                if rhs is None:
                    rhs_emitted = item.rhs.emit_mlir(ctx, block)
                    if isinstance(rhs_emitted, Operation):
                        block.add_op(rhs_emitted)
                        rhs = rhs_emitted.results[0]
                    else:
                        rhs = rhs_emitted
                if not isinstance(lhs, SSAValue) or not isinstance(rhs, SSAValue):
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "alloc shape expression must lower to SSA values")
                lhs_value = lhs.type.get_value() if isinstance(lhs.type, SymbolValueType) else None
                rhs_value = rhs.type.get_value() if isinstance(rhs.type, SymbolValueType) else None
                if lhs_value is None or rhs_value is None:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "alloc shape expression must lower to symbol.int")
                lhs_operand = int(lhs_value) if isinstance(lhs_value, str) and lhs_value.lstrip("-").isdigit() else lhs_value
                rhs_operand = int(rhs_value) if isinstance(rhs_value, str) and rhs_value.lstrip("-").isdigit() else rhs_value
                lhs_symbol = SymbolDim(lhs_operand)
                rhs_symbol = SymbolDim(rhs_operand)
                if isinstance(item, SymbolAddAST):
                    shape_op = SymbolAddOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol + rhs_symbol).get_value())))
                elif isinstance(item, SymbolSubAST):
                    shape_op = SymbolSubOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol - rhs_symbol).get_value())))
                elif isinstance(item, SymbolMulAST):
                    shape_op = SymbolMulOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol * rhs_symbol).get_value())))
                elif isinstance(item, SymbolTrueDivAST):
                    shape_op = SymbolDivOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol / rhs_symbol).get_value())))
                elif isinstance(item, SymbolFloorDivAST):
                    shape_op = SymbolFloorDivOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol // rhs_symbol).get_value())))
                else:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported alloc shape expression")
                block.add_op(shape_op)
                emitted_value = shape_op.results[0]
                value = emitted_value.type.get_value()
                shape_values.append(value if isinstance(value, int) else SymbolDim(value.replace(" ", "") if isinstance(value, str) else value))
                shape_attr_values.append(value)
                dynamic_shape.append(emitted_value)
            elif isinstance(item, ValueAST):
                emitted = item.emit_mlir(ctx, block)
                if isinstance(emitted, Operation):
                    block.add_op(emitted)
                    emitted_value = emitted.results[0]
                else:
                    emitted_value = emitted
                if not isinstance(emitted_value, SSAValue) or not isinstance(emitted_value.type, SymbolValueType):
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "alloc shape must lower to symbol.int")
                value = emitted_value.type.get_value()
                shape_values.append(value if isinstance(value, int) else SymbolDim(value.replace(" ", "") if isinstance(value, str) else value))
                shape_attr_values.append(value)
                dynamic_shape.append(emitted_value)
        stride_values: list[SymbolRuntimeValue] | None = None
        if self.stride is not None:
            stride_values = []
            stride_items = list(self.stride.items)
            for item in stride_items:
                if isinstance(item, ConstValueAST):
                    stride_values.append(item.raw_value)
                elif isinstance(item, ValueAST):
                    emitted = item.emit_mlir(ctx, block)
                    if isinstance(emitted, Operation):
                        block.add_op(emitted)
                        emitted_value = emitted.results[0]
                    else:
                        emitted_value = emitted
                    if not isinstance(emitted_value, SSAValue) or not isinstance(emitted_value.type, SymbolValueType):
                        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "alloc stride must lower to symbol.int")
                    value = emitted_value.type.get_value()
                    stride_values.append(value if isinstance(value, int) else SymbolDim(value.replace(" ", "") if isinstance(value, str) else value))
            if len(stride_values) == len(shape_values) and all(isinstance(dim, int) for dim in shape_values) and all(isinstance(dim, int) for dim in stride_values):
                contiguous_stride: list[int] = []
                running_stride = 1
                for dim in reversed(shape_values):
                    contiguous_stride.insert(0, running_stride)
                    running_stride *= dim
                if stride_values != contiguous_stride:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "dma.alloc only supports contiguous stride")
        result_memory = dma.alloc(shape_values, dtype_value, space_value, stride=stride_values)
        return DmaAllocOp(dynamic_shape, MemoryAST.type_from_memory(ctx, result_memory, self.location))

@dataclass
class DmaCopyAST(ValueAST):
    """DMA copy 节点。


    功能说明:
    - 表示 `copy(...)` 的 DSL 调用。

    使用示例:
    - DmaCopyAST(source=MemoryAST(...), space=MemorySpaceAttrAST(MemorySpace.SM))

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    source: ValueAST
    space: MemorySpaceAttrAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)
        if not isinstance(self.space, MemorySpaceAttrAST):
            self.space = MemorySpaceAttrAST(self.space, self.location)

    def result_memory(self) -> Memory | None:
        """返回 `dma.copy` 的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - copy 结果继承 source 元信息并覆盖目标 space。

        使用示例:
        - memory = copy_ast.result_memory()
        """

        source = self.source.result_memory()
        return dma.copy(source, self.space.space) if isinstance(source, Memory) else None

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 DMA copy 节点发射为 `dma.copy`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "copy source must lower to SSA value")
        if not isinstance(source.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "copy source must lower to nn.memory")
        result_memory = self.result_memory()
        if not isinstance(result_memory, Memory):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "copy result memory must be known from AST")
        result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
        dynamic_shape: list[SSAValue] = []
        for axis, dim in enumerate(result_type.shape.data):
            if isinstance(dim, StringAttr):
                get_dim = SymbolGetDimOp(source, axis)
                block.add_op(get_dim)
                dynamic_shape.append(get_dim.results[0])
        alloc_op = DmaAllocOp(dynamic_shape, result_type)
        block.add_op(alloc_op)
        block.add_op(DmaCopyOp(alloc_op.results[0], source))
        return alloc_op.results[0]

@dataclass
class DmaCastAST(ValueAST):
    """DMA cast 节点。


    功能说明:
    - 表示 `cast(...)` 的 DSL 调用。

    使用示例:
    - DmaCastAST(source=MemoryAST(...), dtype=FloatTypeAttrAST(NumericType.Float16))

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    source: ValueAST
    dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST
    memoryspace: MemorySpaceAttrAST | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)
        if not isinstance(self.dtype, (IntTypeAttrAST, FloatTypeAttrAST, BoolTypeAttrAST)):
            dtype_node = {
                NumericType.Bool: BoolTypeAttrAST(self.location),
                NumericType.Int8: IntTypeAttrAST(8, True, self.location),
                NumericType.Int16: IntTypeAttrAST(16, True, self.location),
                NumericType.Int32: IntTypeAttrAST(32, True, self.location),
                NumericType.Int64: IntTypeAttrAST(64, True, self.location),
                NumericType.Uint8: IntTypeAttrAST(8, False, self.location),
                NumericType.Uint16: IntTypeAttrAST(16, False, self.location),
                NumericType.Uint32: IntTypeAttrAST(32, False, self.location),
                NumericType.Uint64: IntTypeAttrAST(64, False, self.location),
                NumericType.Float16: FloatTypeAttrAST(NumericType.Float16, self.location),
                NumericType.BFloat16: FloatTypeAttrAST(NumericType.BFloat16, self.location),
                NumericType.Float32: FloatTypeAttrAST(NumericType.Float32, self.location),
                NumericType.Float64: FloatTypeAttrAST(NumericType.Float64, self.location),
            }.get(self.dtype)
            if dtype_node is None:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "cast dtype must be a public dtype attr")
            self.dtype = dtype_node
        if self.memoryspace is not None and not isinstance(self.memoryspace, MemorySpaceAttrAST):
            self.memoryspace = MemorySpaceAttrAST(self.memoryspace, self.location)

    def result_memory(self) -> Memory | None:
        """返回 `dma.cast` 的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - cast 结果由 source memory、目标 dtype 与可选 space 决定。

        使用示例:
        - memory = cast_ast.result_memory()
        """

        source = self.source.result_memory()
        if not isinstance(source, Memory):
            return None
        dtype = MemoryAST.numeric_type_from_dtype_attr(self.dtype)
        return dma.cast(source, dtype, self.memoryspace.space if self.memoryspace is not None else None)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 DMA cast 节点发射为 `dma.cast`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "cast source must lower to SSA value")
        if not isinstance(source.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "cast source must lower to nn.memory")
        result_memory = self.result_memory()
        if not isinstance(result_memory, Memory):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "cast result memory must be known from AST")
        result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
        dynamic_shape: list[SSAValue] = []
        for axis, dim in enumerate(result_type.shape.data):
            if isinstance(dim, StringAttr):
                get_dim = SymbolGetDimOp(source, axis)
                block.add_op(get_dim)
                dynamic_shape.append(get_dim.results[0])
        alloc_op = DmaAllocOp(dynamic_shape, result_type)
        block.add_op(alloc_op)
        block.add_op(DmaCastOp(alloc_op.results[0], source))
        return alloc_op.results[0]

@dataclass
class DmaViewAST(ValueAST):
    """DMA view 节点。


    功能说明:
    - 表示 `view(...)` 的 DSL 调用。

    使用示例:
    - DmaViewAST(source=memory, offset=SymbolListAST([0]), size=SymbolListAST([4]), stride=SymbolListAST([1]))

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    source: ValueAST
    offset: SymbolListAST
    size: SymbolListAST
    stride: SymbolListAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)
        if not isinstance(self.offset, SymbolListAST):
            self.offset = SymbolListAST(self.offset, self.location)
        if not isinstance(self.size, SymbolListAST):
            self.size = SymbolListAST(self.size, self.location)
        if not isinstance(self.stride, SymbolListAST):
            self.stride = SymbolListAST(self.stride, self.location)

    def result_memory(self) -> Memory | None:
        """返回 `dma.view` 的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - view 结果只依赖 source memory 与 offset/size/stride symbol 参数。

        使用示例:
        - memory = view_ast.result_memory()
        """

        source = self.source.result_memory()
        offsets = self.offset.result_symbols()
        sizes = self.size.result_symbols()
        strides = self.stride.result_symbols()
        if not isinstance(source, Memory) or offsets is None or sizes is None or strides is None:
            return None
        return dma.view(source, offsets, sizes, strides)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 DMA view 节点发射为 `dma.view`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "view source must lower to SSA value")
        offsets: list[SSAValue] = []
        offset_values: list[SymbolRuntimeValue] = []
        offset_items = list(self.offset.items)
        for item in offset_items:
            emitted = item.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                emitted = emitted.results[0]
            if not isinstance(emitted, SSAValue) or not isinstance(emitted.type, (SymbolValueType, SymbolIterType)):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "view offset must lower to symbol.int")
            value = SymbolDim(emitted.name_hint or "it") if isinstance(emitted.type, SymbolIterType) else emitted.type.get_value()
            offsets.append(emitted)
            offset_values.append(value if isinstance(value, int) else SymbolDim(value.replace(" ", "") if isinstance(value, str) else value))
        sizes: list[SSAValue] = []
        size_values: list[SymbolRuntimeValue] = []
        static_size_cache: dict[int, SSAValue] = {}
        size_items = list(self.size.items)
        for item in size_items:
            static_value = item.raw_value if isinstance(item, ConstValueAST) else None
            if isinstance(static_value, int) and static_value in static_size_cache:
                emitted = static_size_cache[static_value]
            else:
                emitted = item.emit_mlir(ctx, block)
                if isinstance(emitted, Operation):
                    block.add_op(emitted)
                    emitted = emitted.results[0]
                if not isinstance(emitted, SSAValue) or not isinstance(emitted.type, SymbolValueType):
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "view size must lower to symbol.int")
                if isinstance(static_value, int):
                    static_size_cache[static_value] = emitted
            value = emitted.type.get_value()
            sizes.append(emitted)
            size_values.append(value if isinstance(value, int) else SymbolDim(value.replace(" ", "") if isinstance(value, str) else value))
        strides: list[SSAValue] = []
        stride_values: list[SymbolRuntimeValue] = []
        stride_items = list(self.stride.items)
        for item in stride_items:
            emitted = item.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                emitted = emitted.results[0]
            if not isinstance(emitted, SSAValue) or not isinstance(emitted.type, SymbolValueType):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "view stride must lower to symbol.int")
            value = emitted.type.get_value()
            strides.append(emitted)
            stride_values.append(value if isinstance(value, int) else SymbolDim(value.replace(" ", "") if isinstance(value, str) else value))
        if not isinstance(source.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "view source must lower to nn.memory")
        result_memory = self.result_memory()
        if not isinstance(result_memory, Memory):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "view result memory must be known from AST")
        result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
        return DmaViewOp(source, offsets, sizes, strides, result_type)

@dataclass
class DmaReshapeAST(ValueAST):
    """DMA reshape 节点。


    功能说明:
    - 表示 `reshape(...)` 的 DSL 调用。

    使用示例:
    - DmaReshapeAST(source=memory, shape=SymbolListAST([8, 8]))

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    source: ValueAST
    shape: SymbolListAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)
        if not isinstance(self.shape, SymbolListAST):
            self.shape = SymbolListAST(self.shape, self.location)

    def result_memory(self) -> Memory | None:
        """返回 `dma.reshape` 的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - reshape 结果由 source memory 与目标 shape 决定。

        使用示例:
        - memory = reshape_ast.result_memory()
        """

        source = self.source.result_memory()
        shape = self.shape.result_symbols()
        if not isinstance(source, Memory) or shape is None:
            return None
        return dma.reshape(source, shape)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 DMA reshape 节点发射为 `dma.reshape`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reshape source must lower to SSA value")
        shape_items = list(self.shape.items)
        shape_values: list[SymbolRuntimeValue] = []
        shape_operands: list[SSAValue] = []
        for item in shape_items:
            emitted = item.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                emitted_value = emitted.results[0]
            else:
                emitted_value = emitted
            if not isinstance(emitted_value, SSAValue) or not isinstance(emitted_value.type, SymbolValueType):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reshape shape must lower to symbol.int")
            value = emitted_value.type.get_value()
            shape_values.append(value if isinstance(value, int) else SymbolDim(value.replace(" ", "") if isinstance(value, str) else value))
            shape_operands.append(emitted_value)
        result_memory = self.result_memory()
        if not isinstance(source.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reshape source must be nn.memory")
        if not isinstance(result_memory, Memory):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reshape result memory must be known from AST")
        result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
        return DmaReshapeOp(source, shape_operands, result_type)

@dataclass
class DmaFlattenAST(ValueAST):
    """DMA flatten 节点。


    功能说明:
    - 表示 `flatten(...)` 的 DSL 调用。

    使用示例:
    - DmaFlattenAST(source=tensor)

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    source: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)

    def result_memory(self) -> Memory | None:
        """返回 `dma.flatten` 的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - flatten 结果只依赖 source memory。

        使用示例:
        - memory = flatten_ast.result_memory()
        """

        source = self.source.result_memory()
        return dma.flatten(source) if isinstance(source, Memory) else None

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 DMA flatten 节点发射为 `dma.reshape` 语义。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "flatten source must lower to SSA value")
        shape_operand: SSAValue | None = None
        source_type = source.type
        if not isinstance(source_type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "flatten source must be nn.memory")
        result_memory = self.result_memory()
        if not isinstance(result_memory, Memory):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "flatten result memory must be known from AST")
        if all(isinstance(dim, IntAttr) for dim in source_type.shape.data):
            flattened_size = 1
            for dim in source_type.shape.data:
                assert isinstance(dim, IntAttr)
                flattened_size *= dim.data
            flattened_const = ConstValueAST(flattened_size, location=self.location).emit_mlir(ctx, block)
            if isinstance(flattened_const, Operation):
                block.add_op(flattened_const)
                flattened_const = flattened_const.results[0]
            assert isinstance(flattened_const, SSAValue)
            shape_operand = flattened_const
        else:
            for axis, dim in enumerate(source_type.shape.data):
                if isinstance(dim, IntAttr):
                    dim_op = ConstValueAST(dim.data, location=self.location).emit_mlir(ctx, block)
                    if isinstance(dim_op, Operation):
                        block.add_op(dim_op)
                        dim_op = dim_op.results[0]
                    assert isinstance(dim_op, SSAValue)
                    dim_value = dim_op
                else:
                    get_dim = SymbolGetDimOp(source, axis)
                    block.add_op(get_dim)
                    dim_value = get_dim.results[0]
                if shape_operand is None:
                    shape_operand = dim_value
                else:
                    result_shape = result_memory.get_shape()
                    if axis == len(source_type.shape.data) - 1 and result_shape and not isinstance(result_shape[0], int):
                        result_expr = str(result_shape[0].get_value() if isinstance(result_shape[0], SymbolDim) else result_shape[0]).replace(" ", "")
                    else:
                        lhs_expr = str(shape_operand.type.get_value()).replace(" ", "")
                        rhs_expr = str(dim_value.type.get_value()).replace(" ", "")
                        result_expr = f"{lhs_expr}*{rhs_expr}"
                    mul_op = SymbolMulOp(shape_operand, dim_value, SymbolValueType.from_expr(result_expr))
                    block.add_op(mul_op)
                    shape_operand = mul_op.results[0]
        if shape_operand is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "flatten source rank must be non-zero")
        return DmaReshapeOp(source, [shape_operand], MemoryAST.type_from_memory(ctx, result_memory, self.location))

@dataclass
class DmaFreeAST(StatementAST):
    """DMA free 节点。


    功能说明:
    - 表示 `free(...)` 的 DSL 语句调用。

    使用示例:
    - DmaFreeAST(value=tensor)

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    value: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 DMA free 节点发射为 `dma.free`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "value must be Memory")
        return DmaFreeOp(value)


@dataclass
class DmaFillAST(StatementAST):
    """fill helper 专用注册节点。


    功能说明:
    - 表示 `dma.fill(target, value)` 调用。
    - 节点自身直接 emit，不再通过 `StoreAST(kind="fill")` 二次分派。

    使用示例:
    - DmaFillAST(target, 0).emit_mlir(ctx, block)

    关联文件:
    - spec: spec/dsl/ast/nodes/dma.md
    - test: test/dsl/ast/nodes/test_dma.py
    - 功能实现: kernel_gen/dsl/ast/nodes/dma.py
    """

    target: ValueAST
    value: ConstValueAST | SymbolDimAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.target, ValueAST):
            self.target = ConstValueAST(self.target, location=self.location)
        if not isinstance(self.value, (ConstValueAST, SymbolDimAST)):
            self.value = ConstValueAST(self.value, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 DMA fill 节点发射为标量 broadcast。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        target = self.target.emit_mlir(ctx, block)
        if isinstance(target, Operation):
            block.add_op(target)
            target = target.results[0]
        if not isinstance(target, SSAValue) or not isinstance(target.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "fill target must lower to nn.memory")
        value = self.value.raw_value if isinstance(self.value, ConstValueAST) else self.value
        element_type = target.type.element_type
        if isinstance(value, str):
            if value not in {"inf", "-inf"}:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, 'fill string literal must be "inf" or "-inf"')
            if not isinstance(element_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "fill string literal requires float memory")
            value_op = arith.ConstantOp(FloatAttr(float(value), element_type))
            block.add_op(value_op)
            return DmaBroadcastOp(target, value_op.results[0])
        if isinstance(value, bool):
            value_op = arith.ConstantOp.from_int_and_width(1 if value else 0, i1)
            block.add_op(value_op)
            return DmaBroadcastOp(target, value_op.results[0])
        if isinstance(value, int):
            if isinstance(element_type, IntegerType):
                value_op = ConstValueAST(value, location=self.location).emit_mlir(ctx, block)
            elif isinstance(element_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
                value_op = arith.ConstantOp(FloatAttr(float(value), element_type))
            else:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported fill target dtype")
            if isinstance(value_op, Operation):
                block.add_op(value_op)
                value_op = value_op.results[0]
            assert isinstance(value_op, SSAValue)
            return DmaBroadcastOp(target, value_op)
        if isinstance(value, float):
            if not isinstance(element_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "fill float value requires float memory")
            value_op = arith.ConstantOp(FloatAttr(value, element_type))
            block.add_op(value_op)
            return DmaBroadcastOp(target, value_op.results[0])
        if isinstance(value, ValueAST):
            value = value.emit_mlir(ctx, block)
            if isinstance(value, Operation):
                block.add_op(value)
                value = value.results[0]
            if isinstance(value, SSAValue):
                return DmaBroadcastOp(target, value)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported fill value")


@dataclass
class _ReadSliceDmaAST(ValueAST):
    """load/slice 读取类 DMA AST 的当前文件内共享实现。"""

    source: ValueAST
    offset: SymbolListAST
    size: SymbolListAST
    stride: SymbolListAST | None = None
    space: MemorySpaceAttrAST | None = None
    location: SourceLocation | None = None

    _op_name: ClassVar[str]
    _semantic_op: ClassVar[Callable[..., Memory]]

    def __post_init__(self) -> None:
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)
        if not isinstance(self.offset, SymbolListAST):
            self.offset = SymbolListAST(self.offset, self.location)
        if not isinstance(self.size, SymbolListAST):
            self.size = SymbolListAST(self.size, self.location)
        if self.stride is not None and not isinstance(self.stride, SymbolListAST):
            self.stride = SymbolListAST(self.stride, self.location)
        if self.space is not None and not isinstance(self.space, MemorySpaceAttrAST):
            self.space = MemorySpaceAttrAST(self.space, self.location)

    def result_memory(self) -> Memory | None:
        """返回读取类 DMA 节点的解析期 memory 结果。

        功能说明:
        - 通过公开 `dma.load` / `dma.slice` operation 语义推导结果。
        - stride 缺省时沿用公开 operation 默认行为。

        使用示例:
        - memory = read_dma_ast.result_memory()
        """

        source = self.source.result_memory()
        offsets = self.offset.result_symbols()
        sizes = self.size.result_symbols()
        strides = self.stride.result_symbols() if self.stride is not None else None
        if not isinstance(source, Memory) or offsets is None or sizes is None:
            return None
        if self.stride is not None and strides is None:
            return None
        return type(self)._semantic_op(source, offsets, sizes, strides, self.space.space if self.space is not None else None)

    def _stride_items(self) -> list[ValueAST]:
        """返回显式或默认 stride AST 项。

        功能说明:
        - 未传 stride 时按 size rank 生成公开常量 1。

        使用示例:
        - items = self._stride_items()
        """

        if self.stride is not None:
            return list(self.stride.items)
        return [ConstValueAST(1, location=self.location) for _ in self.size.items]

    def _emit_symbol_operands(
        self,
        ctx: Context,
        block: Block,
        items: list[ValueAST],
        message: str,
        *,
        allow_iter: bool = False,
        collect_dynamic: bool = False,
    ) -> tuple[list[SSAValue], list[SSAValue]]:
        """发射 symbol operand 列表。

        功能说明:
        - offset 可选择接受 loop iterator。
        - size 可按非静态维度收集 dynamic shape。

        使用示例:
        - operands, dynamic_shape = self._emit_symbol_operands(ctx, block, items, message)
        """

        operands: list[SSAValue] = []
        dynamic_shape: list[SSAValue] = []
        valid_types = (SymbolValueType, SymbolIterType) if allow_iter else (SymbolValueType,)
        for item in items:
            emitted = item.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                emitted_value = emitted.results[0]
            else:
                emitted_value = emitted
            if not isinstance(emitted_value, SSAValue) or not isinstance(emitted_value.type, valid_types):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, message)
            operands.append(emitted_value)
            if collect_dynamic:
                value = emitted_value.type.get_value()
                if not isinstance(value, int):
                    dynamic_shape.append(emitted_value)
        return operands, dynamic_shape

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将读取类 DMA 节点发射为 `dma.alloc + dma.slice`。

        功能说明:
        - `load` 与 `slice` 共享同一 IR 形态。
        - 结果类型必须来自当前 AST 的 `result_memory()`。

        使用示例:
        - value = read_dma_ast.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"{self._op_name} source must lower to SSA value")
        offsets, _ = self._emit_symbol_operands(
            ctx,
            block,
            list(self.offset.items),
            f"{self._op_name} offset must lower to symbol.int",
            allow_iter=True,
        )
        sizes, dynamic_shape = self._emit_symbol_operands(
            ctx,
            block,
            list(self.size.items),
            f"{self._op_name} size must lower to symbol.int",
            collect_dynamic=True,
        )
        strides, _ = self._emit_symbol_operands(
            ctx,
            block,
            self._stride_items(),
            f"{self._op_name} stride must lower to symbol.int",
        )
        if not isinstance(source.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"{self._op_name} source must lower to nn.memory")
        result_memory = self.result_memory()
        if not isinstance(result_memory, Memory):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"{self._op_name} result memory must be known from AST")
        result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
        alloc_op = DmaAllocOp(dynamic_shape, result_type)
        block.add_op(alloc_op)
        block.add_op(DmaSliceOp(alloc_op.results[0], source, offsets, sizes, strides))
        return alloc_op.results[0]


@dataclass
class DmaLoadAST(_ReadSliceDmaAST):
    """load helper 专用注册节点。"""

    _op_name: ClassVar[str] = "load"
    _semantic_op: ClassVar[Callable[..., Memory]] = dma.load


@dataclass
class DmaSliceAST(_ReadSliceDmaAST):
    """slice helper 专用注册节点。"""

    _op_name: ClassVar[str] = "slice"
    _semantic_op: ClassVar[Callable[..., Memory]] = dma.slice


@dataclass
class _WriteSliceDmaAST(StatementAST):
    """store/deslice 写回类 DMA AST 的当前文件内共享实现。"""

    target: ValueAST
    source: ValueAST
    offset: SymbolListAST
    size: SymbolListAST
    stride: SymbolListAST | None = None
    space: MemorySpaceAttrAST | None = None
    location: SourceLocation | None = None

    _op_name: ClassVar[str]

    def __post_init__(self) -> None:
        if not isinstance(self.target, ValueAST):
            self.target = ConstValueAST(self.target, location=self.location)
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)
        if not isinstance(self.offset, SymbolListAST):
            self.offset = SymbolListAST(self.offset, self.location)
        if not isinstance(self.size, SymbolListAST):
            self.size = SymbolListAST(self.size, self.location)
        if self.stride is not None and not isinstance(self.stride, SymbolListAST):
            self.stride = SymbolListAST(self.stride, self.location)
        if self.space is not None and not isinstance(self.space, MemorySpaceAttrAST):
            self.space = MemorySpaceAttrAST(self.space, self.location)

    def _stride_items(self) -> list[ValueAST]:
        """返回显式或默认 stride AST 项。

        功能说明:
        - 未传 stride 时按 size rank 生成公开常量 1。

        使用示例:
        - items = self._stride_items()
        """

        if self.stride is not None:
            return list(self.stride.items)
        return [ConstValueAST(1, location=self.location) for _ in self.size.items]

    def _emit_symbol_operands(
        self,
        ctx: Context,
        block: Block,
        items: list[ValueAST],
        message: str,
        *,
        allow_iter: bool = False,
    ) -> tuple[list[SSAValue], list[int | str | SymbolDim]]:
        """发射 symbol operand 与公开语义值列表。

        功能说明:
        - 写回类 op 需要同时构造 dialect operand 和公开 operation 校验值。

        使用示例:
        - operands, values = self._emit_symbol_operands(ctx, block, items, message)
        """

        operands: list[SSAValue] = []
        values: list[int | str | SymbolDim] = []
        valid_types = (SymbolValueType, SymbolIterType) if allow_iter else (SymbolValueType,)
        for item in items:
            emitted = item.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                emitted_value = emitted.results[0]
            else:
                emitted_value = emitted
            if not isinstance(emitted_value, SSAValue) or not isinstance(emitted_value.type, valid_types):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, message)
            if isinstance(emitted_value.type, SymbolIterType):
                value = SymbolDim(emitted_value.name_hint or "it")
            else:
                raw_value = emitted_value.type.get_value()
                value = raw_value if isinstance(raw_value, int) else SymbolDim(raw_value.replace(" ", "") if isinstance(raw_value, str) else raw_value)
            operands.append(emitted_value)
            values.append(value)
        return operands, values

    def _validate_public_semantics(
        self,
        target: SSAValue,
        source: SSAValue,
        offsets: list[int | str | SymbolDim],
        sizes: list[int | str | SymbolDim],
        strides: list[int | str | SymbolDim],
    ) -> None:
        """校验写回类 op 的公开 operation 语义。

        功能说明:
        - 子类按自身公开 operation 选择校验规则。

        使用示例:
        - self._validate_public_semantics(target, source, offsets, sizes, strides)
        """

        _ = (target, source, offsets, sizes, strides)

    def _build_dma_op(self, target: SSAValue, source: SSAValue, offsets: list[SSAValue], sizes: list[SSAValue], strides: list[SSAValue]) -> Operation:
        """构造具体 DMA dialect op。

        功能说明:
        - 子类返回 `DmaStoreOp` 或 `DmaDesliceOp`。

        使用示例:
        - op = self._build_dma_op(target, source, offsets, sizes, strides)
        """

        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported {self._op_name} op")

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将写回类 DMA 节点发射为对应 DMA op。

        功能说明:
        - `store` 与 `deslice` 共享 target/source 与 offset/size/stride 发射流程。
        - 子类保留各自公开语义校验和 dialect op 构造。

        使用示例:
        - op = write_dma_ast.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        target = self.target.emit_mlir(ctx, block)
        if isinstance(target, Operation):
            block.add_op(target)
            target = target.results[0]
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(target, SSAValue) or not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"{self._op_name} operands must lower to SSA values")
        offsets, offset_values = self._emit_symbol_operands(
            ctx,
            block,
            list(self.offset.items),
            f"{self._op_name} offset must lower to symbol.int",
            allow_iter=True,
        )
        sizes, size_values = self._emit_symbol_operands(ctx, block, list(self.size.items), f"{self._op_name} size must lower to symbol.int")
        strides, stride_values = self._emit_symbol_operands(ctx, block, self._stride_items(), f"{self._op_name} stride must lower to symbol.int")
        self._validate_public_semantics(target, source, offset_values, size_values, stride_values)
        return self._build_dma_op(target, source, offsets, sizes, strides)


@dataclass
class DmaStoreAST(_WriteSliceDmaAST):
    """store helper 专用注册节点。"""

    _op_name: ClassVar[str] = "store"

    def _validate_public_semantics(
        self,
        target: SSAValue,
        source: SSAValue,
        offsets: list[int | str | SymbolDim],
        sizes: list[int | str | SymbolDim],
        strides: list[int | str | SymbolDim],
    ) -> None:
        """校验 `dma.store` 的公开 memory 语义。

        功能说明:
        - source 必须为 memory SSA。
        - target 不是 `MemoryAST` 时保持既有公开错误。

        使用示例:
        - self._validate_public_semantics(target, source, offsets, sizes, strides)
        """

        _ = target
        if not isinstance(source.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "store source must lower to nn.memory")
        try:
            if not isinstance(self.target, MemoryAST):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "store target must be MemoryAST")
            if isinstance(self.source, MemoryAST):
                dma.store(self.target.memory, self.source.memory, offsets, sizes, strides)
        except ValueError as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, str(exc)) from exc

    def _build_dma_op(self, target: SSAValue, source: SSAValue, offsets: list[SSAValue], sizes: list[SSAValue], strides: list[SSAValue]) -> Operation:
        """构造 `DmaStoreOp`。

        功能说明:
        - 使用 target-first operand 顺序。

        使用示例:
        - op = self._build_dma_op(target, source, offsets, sizes, strides)
        """

        return DmaStoreOp(target, source, offsets, sizes, strides)


@dataclass
class DmaDesliceAST(_WriteSliceDmaAST):
    """deslice helper 专用注册节点。"""

    _op_name: ClassVar[str] = "deslice"

    def _validate_public_semantics(
        self,
        target: SSAValue,
        source: SSAValue,
        offsets: list[int | str | SymbolDim],
        sizes: list[int | str | SymbolDim],
        strides: list[int | str | SymbolDim],
    ) -> None:
        """校验 `dma.deslice` 的公开 memory 语义。

        功能说明:
        - target 必须为 memory SSA。
        - 当 target/source 均为 MemoryAST 时执行公开 operation 校验。

        使用示例:
        - self._validate_public_semantics(target, source, offsets, sizes, strides)
        """

        if isinstance(self.source, MemoryAST) and isinstance(self.target, MemoryAST):
            try:
                dma.deslice(self.target.memory, self.source.memory, offsets, sizes, strides)
            except ValueError as exc:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, str(exc)) from exc
        if not isinstance(target.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "deslice target must be nn.memory")
        _ = source

    def _build_dma_op(self, target: SSAValue, source: SSAValue, offsets: list[SSAValue], sizes: list[SSAValue], strides: list[SSAValue]) -> Operation:
        """构造 `DmaDesliceOp`。

        功能说明:
        - deslice 保留 target type 作为 out-param result type。

        使用示例:
        - op = self._build_dma_op(target, source, offsets, sizes, strides)
        """

        assert isinstance(target.type, NnMemoryType)
        return DmaDesliceOp(target, source, offsets, sizes, strides, target.type)
