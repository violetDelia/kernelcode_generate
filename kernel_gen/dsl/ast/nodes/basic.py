"""DSL AST basic node definitions.


功能说明:
- 定义 DSL AST 模块、函数、值、语句与 memory 值节点。
- `symbol` dialect 相关节点由 `kernel_gen.dsl.ast.nodes.symbol` 承载。
- 控制流节点由 `kernel_gen.dsl.ast.nodes.control_flow` 承载。
- 节点只保留当前公开 AST API；不再保留旧 `TensorAST`、`ConstAST`、`BinaryExprAST` 等兼容节点。
- `emit_mlir(ctx, block)` 由当前节点递归调用成员节点实现，最终生成 xDSL MLIR operation。
- 表达式节点在传入 `block` 时插入自身产生的 op 并返回结果 SSA；`block=None` 时返回 unattached op，供节点级测试与容器节点构造使用。
- `MemoryAST.type_from_memory(...)` 在匿名动态 shape 与 stride 同轴冲突时生成稳定类型级符号，避免把非法 `[?]/[?]` 组合写入 `nn.memory`。

API 列表:
- `DSLNode.emit_mlir(ctx: Context, block: Block | None = None) -> EmitMlirResult`
- `ValueAST`
- `ValueAST.result_memory() -> Memory | None`
- `ValueAST.result_symbol() -> int | SymbolDim | None`
- `ValueAST.result_scalar() -> int | float | bool | str | SymbolDim | None`
- `ValueAST.binding_value() -> Memory | int | float | bool | str | SymbolDim | None`
- `ValueAST.bind_target(name: str, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST | ValueAST`
- `StatementAST`
- `ModuleAST(functions: list[FunctionAST], runtime_args: tuple[PythonObjectAttrAST, ...] = (), source_fn: PythonObjectAttrAST = ...)`
- `FunctionAST(name: str, inputs: list[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST], outputs: list[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST], body: BlockAST, ..., runtime_args: tuple[PythonObjectAttrAST, ...] = ())`
- `FunctionAST.input_from_runtime_arg(name: str, value: object, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST`
- `FunctionAST.input_from_bound_value(name: str, value: ValueAST, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST`
- `FunctionAST.iter_inputs() -> Iterable[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST]`
- `MemoryAST(name: str, shape: SymbolListAST, stride: SymbolListAST, type: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None, format: PythonObjectAttrAST = ...)`
- `BoolValueAST(value: bool, location: SourceLocation | None = None)`
- `MemoryAST.dtype_attr_from_numeric_type(dtype: NumericType, location: SourceLocation | None = None) -> IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST`
- `MemoryAST.numeric_type_from_dtype_attr(dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST) -> NumericType`
- `MemoryAST.from_memory(name: str, memory: Memory, location: SourceLocation | None = None) -> MemoryAST`
- `MemoryAST.type_from_memory(ctx: Context, memory: Memory, location: SourceLocation | None = None) -> NnMemoryType`
- `MemoryAST.to_mlir_type(ctx: Context) -> NnMemoryType`
- `BoundExprAST(name: str, target: MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST | ValueAST, value: ValueAST, location: SourceLocation | None = None)`
- `ReturnAST(values: ValueAST | list[ValueAST] | tuple[ValueAST, ...] | None = None, location: SourceLocation | None = None)`
- `CallAST(callee: FunctionAST, args: list[ValueAST], location: SourceLocation | None = None)`
- `BlockAST(statements: list[StatementAST], location: SourceLocation | None = None)`

使用示例:
- from kernel_gen.dsl.ast.nodes.basic import FunctionAST, BlockAST
- FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))

关联文件:
- spec: spec/dsl/ast/nodes/basic.md
- test: test/dsl/ast/nodes/test_basic.py
- 功能实现: kernel_gen/dsl/ast/nodes/basic.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from xdsl.context import Context
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    FunctionType,
    IntAttr,
    ModuleOp,
    StringAttr,
    i1,
)
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType


class DSLNode:
    """所有 DSL AST 节点的公共基类。


    功能说明:
    - 为 AST 节点提供统一 `emit_mlir(ctx, block)` 接口。
    - 基类只定义合同；具体节点必须实现该接口。

    使用示例:
    - isinstance(node, DSLNode)
    """

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将当前 AST 节点发射到 MLIR。


        功能说明:
        - 作为 AST 节点公开发射入口的抽象合同。
        - 未实现的节点直接失败，避免回退到中心化分派。

        使用示例:
        - result = node.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        raise NotImplementedError(f"{type(self).__name__}.emit_mlir not implemented")


from .attr import (  # noqa: E402
    BoolTypeAttrAST,
    Diagnostic,
    EmitMlirResult,
    FloatTypeAttrAST,
    IntTypeAttrAST,
    MemorySpaceAttrAST,
    PythonObjectAttrAST,
    SourceLocation,
)


__all__ = [
    "DSLNode",
    "ValueAST",
    "StatementAST",
    "ModuleAST",
    "MemoryAST",
    "BoolValueAST",
    "BlockAST",
    "ReturnAST",
    "BoundExprAST",
    "CallAST",
    "FunctionAST",
]


class ValueAST(DSLNode):
    """值类 DSL AST 节点基类。

    创建者: 榕
    最后一次更改: 2026-05-02

    功能说明:
    - 标记可作为表达式值、函数实参或 MLIR SSA value 来源的 AST 节点。

    使用示例:
    - isinstance(node, ValueAST)
    """

    def result_memory(self) -> Memory | None:
        """返回当前值节点在解析期可确定的 memory 语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 默认值节点不产生 memory。
        - 具体 DMA / NN / Memory 节点按自身字段覆盖该入口，visitor 不再维护跨节点推断表。

        使用示例:
        - memory = value.result_memory()
        """

        return None

    def result_symbol(self) -> int | SymbolDim | None:
        """返回当前值节点在解析期可确定的 symbol 整数语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 默认值节点不产生 symbol 整数。
        - 符号维度、整数常量与 symbol 表达式节点按自身字段覆盖该入口。

        使用示例:
        - symbol = value.result_symbol()
        """

        return None

    def result_scalar(self) -> int | float | bool | str | SymbolDim | None:
        """返回当前值节点在解析期可确定的普通标量语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 默认复用 `result_symbol()`。
        - 常量与布尔节点按自身字段覆盖该入口。

        使用示例:
        - scalar = value.result_scalar()
        """

        return self.result_symbol()

    def binding_value(self) -> Memory | int | float | bool | str | SymbolDim | None:
        """返回赋值绑定可写入 runtime table 的解析期值。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 按 memory、symbol、scalar 顺序读取当前节点公开结果语义。
        - `DslAstVisitor` 通过该入口更新名称绑定，不再在 visitor 内重复判断每类节点结果。

        使用示例:
        - runtime_value = value.binding_value()
        """

        memory_value = self.result_memory()
        if memory_value is not None:
            return memory_value
        symbol_value = self.result_symbol()
        if symbol_value is not None:
            return symbol_value
        return self.result_scalar()

    def bind_target(self, name: str, location: SourceLocation | None = None) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST | ValueAST:
        """构造赋值左侧名称对应的 AST 绑定目标。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 根据当前值节点公开结果语义生成后续 `Name` 可解析的目标节点。
        - memory 结果绑定为 `MemoryAST`，symbol 结果绑定为 `SymbolDimAST`，布尔与浮点标量绑定为对应常量节点。
        - 无解析期结果语义时返回当前值节点，保持表达式 SSA 名称绑定语义。

        使用示例:
        - target = value.bind_target("tmp", location)
        """

        from .symbol import ConstValueAST, SymbolDimAST

        memory_value = self.result_memory()
        if isinstance(memory_value, Memory):
            return MemoryAST.from_memory(name, memory_value, location)
        symbol_value = self.result_symbol()
        scalar_value = self.result_scalar()
        if isinstance(symbol_value, SymbolDim):
            return SymbolDimAST(name, location=location, runtime_symbol=symbol_value)
        if isinstance(scalar_value, bool):
            return BoolValueAST(scalar_value, location=location)
        if isinstance(symbol_value, int):
            return SymbolDimAST(name, location=location, runtime_symbol=symbol_value)
        if isinstance(scalar_value, float):
            return ConstValueAST(FloatTypeAttrAST(NumericType.Float64, location), scalar_value, location=location)
        return self


class StatementAST(DSLNode):
    """语句类 DSL AST 节点基类。

    创建者: 榕
    最后一次更改: 2026-05-02

    功能说明:
    - 标记只能放入 `BlockAST.statements` 的 AST 节点。

    使用示例:
    - isinstance(node, StatementAST)
    """


@dataclass
class ModuleAST(DSLNode):
    """DSL 模块节点。"""

    functions: list[FunctionAST]
    runtime_args: tuple[PythonObjectAttrAST, ...] = ()
    source_fn: PythonObjectAttrAST = field(default_factory=lambda: PythonObjectAttrAST(None))

    def __post_init__(self) -> None:
        self.runtime_args = tuple(arg if isinstance(arg, PythonObjectAttrAST) else PythonObjectAttrAST(arg) for arg in self.runtime_args)
        if not isinstance(self.source_fn, PythonObjectAttrAST):
            self.source_fn = PythonObjectAttrAST(self.source_fn)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射模块为 `builtin.module`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        ops: list[Operation] = []
        for function in self.functions:
            function_op = function.emit_mlir(ctx, None)
            if not isinstance(function_op, func.FuncOp):
                raise KernelCodeError(ErrorKind.INTERNAL, ErrorModule.MLIR_GEN, "function emit must return func.func")
            ops.append(function_op)
        return ModuleOp(ops)


@dataclass
class BlockAST(DSLNode):
    """语句块节点。"""

    statements: list[StatementAST | ValueAST]
    location: SourceLocation | None = None

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """按顺序发射语句块中的节点。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        last_value: EmitMlirResult = None
        for statement in self.statements:
            emitted = statement.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                last_value = emitted.results[0] if emitted.results else None
            else:
                last_value = emitted
        return last_value


@dataclass
class MemoryAST(ValueAST):
    """命名 memory 值节点。"""

    name: str
    shape: SymbolListAST
    stride: SymbolListAST
    type: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST
    space: MemorySpaceAttrAST
    location: SourceLocation | None = None
    format: PythonObjectAttrAST = field(default_factory=lambda: PythonObjectAttrAST(Farmat.Norm))

    def __post_init__(self) -> None:
        from .symbol import SymbolListAST

        if not isinstance(self.shape, SymbolListAST):
            self.shape = SymbolListAST(self.shape, self.location)
        if not isinstance(self.stride, SymbolListAST):
            self.stride = SymbolListAST(self.stride, self.location)
        if not isinstance(self.space, MemorySpaceAttrAST):
            self.space = MemorySpaceAttrAST(self.space, self.location)
        if not isinstance(self.format, PythonObjectAttrAST):
            self.format = PythonObjectAttrAST(self.format, self.location)

    @classmethod
    def dtype_attr_from_numeric_type(
        cls,
        dtype: NumericType,
        location: SourceLocation | None = None,
    ) -> IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST:
        """根据 runtime `NumericType` 构造 DSL dtype 属性节点。


        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 作为 runtime `Memory` 到 `MemoryAST` 的唯一 dtype 映射入口。
        - 未支持 dtype 直接失败，避免各调用点各自维护 fallback。

        使用示例:
        - dtype_node = MemoryAST.dtype_attr_from_numeric_type(NumericType.Float32)
        """

        dtype_map: dict[NumericType, IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST] = {
            NumericType.Bool: BoolTypeAttrAST(location),
            NumericType.Int8: IntTypeAttrAST(8, True, location),
            NumericType.Int16: IntTypeAttrAST(16, True, location),
            NumericType.Int32: IntTypeAttrAST(32, True, location),
            NumericType.Int64: IntTypeAttrAST(64, True, location),
            NumericType.Uint8: IntTypeAttrAST(8, False, location),
            NumericType.Uint16: IntTypeAttrAST(16, False, location),
            NumericType.Uint32: IntTypeAttrAST(32, False, location),
            NumericType.Uint64: IntTypeAttrAST(64, False, location),
            NumericType.Float16: FloatTypeAttrAST(NumericType.Float16, location),
            NumericType.BFloat16: FloatTypeAttrAST(NumericType.BFloat16, location),
            NumericType.Float32: FloatTypeAttrAST(NumericType.Float32, location),
            NumericType.Float64: FloatTypeAttrAST(NumericType.Float64, location),
        }
        dtype_node = dtype_map.get(dtype)
        if dtype_node is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported memory dtype")
        return dtype_node

    @classmethod
    def numeric_type_from_dtype_attr(
        cls,
        dtype: IntTypeAttrAST | FloatTypeAttrAST | BoolTypeAttrAST,
    ) -> NumericType:
        """根据 DSL dtype 属性读取 runtime `NumericType`。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 统一 AST dtype 属性到 runtime dtype 的映射。
        - DMA / NN 节点解析自身结果 memory 时不得复制 dtype 分支表。

        使用示例:
        - dtype = MemoryAST.numeric_type_from_dtype_attr(dtype_node)
        """

        if isinstance(dtype, BoolTypeAttrAST):
            return NumericType.Bool
        if isinstance(dtype, FloatTypeAttrAST):
            return dtype.dtype
        if isinstance(dtype, IntTypeAttrAST):
            dtype_value = {
                (8, True): NumericType.Int8,
                (16, True): NumericType.Int16,
                (32, True): NumericType.Int32,
                (64, True): NumericType.Int64,
                (8, False): NumericType.Uint8,
                (16, False): NumericType.Uint16,
                (32, False): NumericType.Uint32,
                (64, False): NumericType.Uint64,
            }.get((dtype.bits, dtype.signed))
            if dtype_value is not None:
                return dtype_value
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported memory dtype")

    @classmethod
    def from_memory(
        cls,
        name: str,
        memory: Memory,
        location: SourceLocation | None = None,
    ) -> MemoryAST:
        """根据 runtime `Memory` 构造 `MemoryAST`。


        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 统一 runtime memory 到 DSL AST memory 的 shape、stride、dtype、space、format 映射。
        - parser 与后续 AST 重写不再重复维护 dtype/space 表。

        使用示例:
        - memory_ast = MemoryAST.from_memory("x", memory)
        """

        from .symbol import SymbolListAST

        return cls(
            name,
            SymbolListAST(list(memory.get_shape()), location),
            SymbolListAST(list(memory.get_stride()), location),
            cls.dtype_attr_from_numeric_type(memory.get_type(), location),
            MemorySpaceAttrAST(memory.get_space(), location),
            location=location,
            format=PythonObjectAttrAST(memory.get_format(), location),
        )

    @classmethod
    def type_from_memory(
        cls,
        ctx: Context,
        memory: Memory,
        location: SourceLocation | None = None,
    ) -> NnMemoryType:
        """根据 runtime `Memory` 构造 `NnMemoryType`。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 统一 shape、stride、dtype、space 到 MLIR memory type 的映射。
        - 匿名动态 shape 与 stride 同轴均为 `?` 时，为 type attribute 生成稳定符号并重建连续 stride。
        - emit 节点不再各自维护 dtype/space 转换表。

        使用示例:
        - result_type = MemoryAST.type_from_memory(ctx, memory)
        """

        assert isinstance(ctx, Context)
        shape_values, stride_values = cls._type_layout_values(memory)
        shape_attr = ArrayAttr([IntAttr(dim) if isinstance(dim, int) else StringAttr(str(dim)) for dim in shape_values])
        stride_attr = ArrayAttr([IntAttr(dim) if isinstance(dim, int) else StringAttr(str(dim)) for dim in stride_values])
        element_type = cls.dtype_attr_from_numeric_type(memory.get_type(), location).emit_mlir(ctx, None)
        space_attr = MemorySpaceAttrAST(memory.get_space(), location).emit_mlir(ctx, None)
        if not isinstance(element_type, Attribute):
            raise KernelCodeError(ErrorKind.INTERNAL, ErrorModule.MLIR_GEN, "dtype attr emit must return Attribute")
        if not isinstance(space_attr, NnMemorySpaceAttr):
            raise KernelCodeError(ErrorKind.INTERNAL, ErrorModule.MLIR_GEN, "space attr emit must return NnMemorySpaceAttr")
        return NnMemoryType(shape_attr, stride_attr, element_type, space_attr)

    @staticmethod
    def _type_layout_values(memory: Memory) -> tuple[list[int | str], list[int | str]]:
        """生成用于 `NnMemoryType` 的 shape/stride 文本值。


        功能说明:
        - 默认直接沿用 `Memory.get_shape()` 与 `Memory.get_stride()` 的公开值。
        - 当同轴 shape/stride 均为匿名 `?` 时，为匿名 shape 生成稳定类型级符号并重建连续 stride。

        使用示例:
        - shape_values, stride_values = MemoryAST._type_layout_values(memory)

        关联文件:
        - spec: spec/dsl/ast/nodes/basic.md
        - test: test/dsl/ast/nodes/test_basic.py
        - 功能实现: kernel_gen/dsl/ast/nodes/basic.py
        """

        shape_values = list(memory.get_shape())
        stride_values = [
            value if isinstance(value, int) else str(value)
            for value in memory.get_stride()
        ]
        if not any(shape == "?" and stride == "?" for shape, stride in zip(shape_values, stride_values, strict=True)):
            return shape_values, stride_values

        named_shape_values: list[int | str] = [
            f"runtime_dim_{axis}" if shape == "?" else shape
            for axis, shape in enumerate(shape_values)
        ]
        return named_shape_values, MemoryAST._contiguous_stride_values(named_shape_values)

    @staticmethod
    def _contiguous_stride_values(shape_values: list[int | str]) -> list[int | str]:
        """根据 type 级 shape 值重建连续 stride。


        功能说明:
        - 复用 `SymbolDim` 公开算术语义生成稳定字符串，避免手写表达式优先级。

        使用示例:
        - stride_values = MemoryAST._contiguous_stride_values(["M", "N"])

        关联文件:
        - spec: spec/dsl/ast/nodes/basic.md
        - test: test/dsl/ast/nodes/test_basic.py
        - 功能实现: kernel_gen/dsl/ast/nodes/basic.py
        """

        stride_values: list[int | str] = []
        running = SymbolDim(1)
        for dim in reversed(shape_values):
            running_value = running.get_value()
            stride_values.insert(0, running_value if isinstance(running_value, str) else int(running_value))
            running = SymbolDim(dim) * running
        return stride_values

    @property
    def memory(self) -> Memory:
        """根据 AST 字段构造 runtime `Memory`。

        功能说明:
        - 逐项通过公开 `result_symbol()` / `result_scalar()` 读取 shape 与 stride 语义。
        - 支持 `SymbolDimAST`、`ConstValueAST` 与公开 symbol 表达式节点，不把 AST repr 当作符号文本。

        使用示例:
        - memory = memory_ast.memory
        """

        shape: list[int | float | bool | str | SymbolDim] = []
        for item in self.shape.values:
            symbol_value = item.result_symbol()
            scalar_value = item.result_scalar()
            shape.append(symbol_value if symbol_value is not None else scalar_value if scalar_value is not None else str(item))
        stride: list[int | float | bool | str | SymbolDim] = []
        for item in self.stride.values:
            symbol_value = item.result_symbol()
            scalar_value = item.result_scalar()
            stride.append(symbol_value if symbol_value is not None else scalar_value if scalar_value is not None else str(item))
        dtype = self.numeric_type_from_dtype_attr(self.type)
        memory_format = self.format.attr
        if not isinstance(memory_format, Farmat):
            memory_format = Farmat.Norm
        return Memory(shape, dtype, space=self.space.space, stride=stride, format=memory_format)

    def result_memory(self) -> Memory | None:
        """返回当前 memory 节点的解析期 memory 语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 直接由 `MemoryAST.memory` 构造结果。
        - 供赋值绑定、axis 访问和组合节点结果推导使用。

        使用示例:
        - memory = memory_ast.result_memory()
        """

        return self.memory

    def to_mlir_type(self, ctx: Context) -> NnMemoryType:
        """把当前 memory 字段发射为 `!nn.memory` 类型。


        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 统一 `FunctionAST` 与其他发射点构造 `NnMemoryType` 的逻辑。
        - shape/stride 文本来自 `MemoryAST.memory`，dtype/space 来自对应 attr 节点。

        使用示例:
        - memory_type = memory_ast.to_mlir_type(ctx)
        """

        assert isinstance(ctx, Context)
        return self.type_from_memory(ctx, self.memory, self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 memory 引用为已绑定 SSA value。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        current_block: Block | None = block
        while current_block is not None:
            for op in reversed(tuple(current_block.ops)):
                for result in op.results:
                    if result.name_hint == self.name:
                        return result
            for argument in current_block.args:
                if argument.name_hint == self.name:
                    return argument
            current_block = current_block.parent_block()
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unbound memory value: {self.name}")


@dataclass
class BoolValueAST(ValueAST):
    """布尔值节点。"""

    value: bool
    location: SourceLocation | None = None

    @property
    def raw_value(self) -> bool:
        """返回布尔常量。"""

        return self.value

    def result_scalar(self) -> int | float | bool | str | SymbolDim | None:
        """返回布尔标量语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 供 parser 绑定布尔别名。

        使用示例:
        - scalar = BoolValueAST(True).result_scalar()
        """

        return self.raw_value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射布尔值为 `i1` 常量。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        const_op = arith.ConstantOp.from_int_and_width(1 if self.value else 0, i1)
        if block is not None:
            block.add_op(const_op)
            return const_op.results[0]
        return const_op


@dataclass
class BoundExprAST(StatementAST):
    """绑定表达式结果的语句节点。"""

    name: str
    target: MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST | ValueAST
    value: ValueAST
    location: SourceLocation | None = None

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射表达式并写入 `name_hint`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        emitted = self.value.emit_mlir(ctx, block)
        if isinstance(emitted, Operation):
            if emitted.results:
                emitted.results[0].name_hint = self.name
            return emitted
        if isinstance(emitted, SSAValue):
            emitted.name_hint = self.name
        return emitted


@dataclass
class ReturnAST(StatementAST):
    """函数返回语句节点。"""

    values: tuple[ValueAST, ...]
    location: SourceLocation | None = None

    def __init__(
        self,
        values: ValueAST | list[ValueAST] | tuple[ValueAST, ...] | None = None,
        location: SourceLocation | None = None,
    ) -> None:
        """初始化函数返回节点。


        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 归一化 0/1/N 个返回值。
        - 返回值必须是 `ValueAST`，避免语句节点进入返回值位置。

        使用示例:
        - ret = ReturnAST([lhs, rhs])
        """

        raw_values = () if values is None else values if isinstance(values, (list, tuple)) else (values,)
        normalized: list[ValueAST] = []
        for item in raw_values:
            if not isinstance(item, ValueAST):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "return values must be ValueAST")
            normalized.append(item)
        self.values = tuple(normalized)
        self.location = location

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 `func.return`。


        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 递归发射每个返回值节点。
        - 生成 0 个、1 个或多个返回 operand 的 `func.return`。

        使用示例:
        - values = ret.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        output_values: list[SSAValue] = []
        for value in self.values:
            emitted = value.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                if not emitted.results:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "return value has no result")
                emitted = emitted.results[0]
            if not isinstance(emitted, SSAValue):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "return value must lower to SSA value")
            output_values.append(emitted)
        block.add_op(func.ReturnOp(*output_values))
        return tuple(output_values)


@dataclass
class FunctionAST(DSLNode):
    """函数节点。"""

    name: str
    inputs: list[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST]
    outputs: list[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST]
    body: BlockAST
    location: SourceLocation | None = None
    source: PythonObjectAttrAST = field(default_factory=lambda: PythonObjectAttrAST(None))
    py_ast: PythonObjectAttrAST = field(default_factory=lambda: PythonObjectAttrAST(None))
    diagnostics: PythonObjectAttrAST = field(default_factory=lambda: PythonObjectAttrAST(()))
    has_explicit_return: BoolValueAST = field(default_factory=lambda: BoolValueAST(False))
    returns_none: BoolValueAST = field(default_factory=lambda: BoolValueAST(False))
    runtime_args: tuple[PythonObjectAttrAST, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source, PythonObjectAttrAST):
            self.source = PythonObjectAttrAST(self.source, self.location)
        if not isinstance(self.py_ast, PythonObjectAttrAST):
            self.py_ast = PythonObjectAttrAST(self.py_ast, self.location)
        if not isinstance(self.diagnostics, PythonObjectAttrAST):
            self.diagnostics = PythonObjectAttrAST(tuple(self.diagnostics), self.location)
        if not isinstance(self.has_explicit_return, BoolValueAST):
            self.has_explicit_return = BoolValueAST(bool(self.has_explicit_return), self.location)
        if not isinstance(self.returns_none, BoolValueAST):
            self.returns_none = BoolValueAST(bool(self.returns_none), self.location)
        self.runtime_args = tuple(arg if isinstance(arg, PythonObjectAttrAST) else PythonObjectAttrAST(arg, self.location) for arg in self.runtime_args)

    @classmethod
    def input_from_runtime_arg(
        cls,
        name: str,
        value: object,
        location: SourceLocation | None = None,
    ) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST:
        """根据 runtime 参数构造函数输入 AST 节点。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 统一 runtime 参数到 `FunctionAST.inputs` 的构造规则。
        - visitor 只调用该公开入口，不再在 `visit_FunctionDef` 中维护 runtime 类型工厂。
        - `Memory`、`SymbolDim`、`int`、`float`、`bool` 保持当前公开解析语义。

        使用示例:
        - input_node = FunctionAST.input_from_runtime_arg("x", memory, location)
        """

        from .symbol import ConstValueAST, SymbolDimAST

        if isinstance(value, Memory):
            return MemoryAST.from_memory(name, value, location)
        if isinstance(value, SymbolDim):
            return SymbolDimAST(name, location=location, runtime_symbol=value)
        if isinstance(value, bool):
            return BoolValueAST(value, location=location)
        if isinstance(value, int):
            return SymbolDimAST(name, location=location, runtime_symbol=value)
        if isinstance(value, float):
            return ConstValueAST(FloatTypeAttrAST(NumericType.Float64, location), value, location=location)
        if isinstance(value, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "NnMemoryType runtime argument is unsupported")
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "Missing runtime argument")

    @classmethod
    def input_from_bound_value(
        cls,
        name: str,
        value: ValueAST,
        location: SourceLocation | None = None,
    ) -> MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST:
        """根据 caller 侧 DSL 值构造 callee 函数输入 AST 节点。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - Python callee 参数绑定 caller 侧 DSL 节点时，通过该公开入口复制输入语义。
        - memory、symbol、bool、const 分别转换为对应输入节点。
        - 非输入值节点直接失败，避免 callee 参数从任意表达式隐式推导。

        使用示例:
        - input_node = FunctionAST.input_from_bound_value("tile", tile_ast, location)
        """

        from .symbol import ConstValueAST, SymbolDimAST

        if isinstance(value, MemoryAST):
            return MemoryAST(
                name,
                value.shape,
                value.stride,
                value.type,
                value.space,
                location=location,
                format=value.format,
            )
        if isinstance(value, SymbolDimAST):
            return SymbolDimAST(name, location=location, runtime_symbol=value.result_symbol())
        if isinstance(value, BoolValueAST):
            return BoolValueAST(value.raw_value, location=location)
        if isinstance(value, ConstValueAST):
            return ConstValueAST(value.type, value.raw_value, location=location)
        raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.AST, "Unsupported Python callee argument")

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将函数 AST 发射为 `func.func`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        from .symbol import ConstValueAST, SymbolDimAST

        input_types: list[Attribute] = []
        for index, item in enumerate(self.inputs):
            if isinstance(item, MemoryAST):
                input_types.append(item.to_mlir_type(ctx))
            elif isinstance(item, SymbolDimAST):
                symbol_value = item.result_symbol()
                if isinstance(symbol_value, SymbolDim):
                    input_types.append(SymbolValueType.from_expr(str(symbol_value.get_symbol())))
                elif isinstance(symbol_value, int):
                    input_types.append(SymbolValueType.from_expr(str(symbol_value)))
                else:
                    input_types.append(SymbolValueType.from_expr(str(item.symbol.get_value())))
            elif isinstance(item, BoolValueAST):
                input_types.append(i1)
            elif isinstance(item, ConstValueAST):
                element_type = item.type.emit_mlir(ctx, None)
                if not isinstance(element_type, Attribute):
                    raise KernelCodeError(ErrorKind.INTERNAL, ErrorModule.MLIR_GEN, "const type emit must return Attribute")
                input_types.append(element_type)
            else:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported function argument type")

        entry_block = Block(arg_types=input_types)
        for index, item in enumerate(self.inputs):
            entry_block.args[index].name_hint = item.name if isinstance(item, (MemoryAST, SymbolDimAST)) else f"arg{index}"
        last_value = self.body.emit_mlir(ctx, entry_block)
        pending_blocks = [entry_block]
        for current_block in pending_blocks:
            for op in current_block.ops:
                for result in op.results:
                    result.name_hint = None
                for region in op.regions:
                    pending_blocks.extend(region.blocks)
        for argument in entry_block.args:
            argument.name_hint = None
        output_values: list[SSAValue] = []
        if bool(self.has_explicit_return.raw_value) and not bool(self.returns_none.raw_value):
            if isinstance(last_value, tuple) and all(isinstance(value, SSAValue) for value in last_value):
                output_values.extend(last_value)
            elif isinstance(last_value, SSAValue):
                output_values.append(last_value)
            elif isinstance(last_value, Operation) and last_value.results:
                output_values.extend(last_value.results)
            else:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "return value must lower to SSA value")
        else:
            output_values = []
        output_types = [value.type for value in output_values]
        has_return_op = any(isinstance(op, func.ReturnOp) for op in entry_block.ops)
        if not has_return_op:
            entry_block.add_op(func.ReturnOp(*output_values))
        return func.FuncOp(self.name, FunctionType.from_lists(input_types, output_types), Region(entry_block))

    def iter_inputs(self: FunctionAST) -> Iterable[MemoryAST | SymbolDimAST | ConstValueAST | BoolValueAST]:
        """迭代输入参数。"""

        return iter(self.inputs)


@dataclass
class CallAST(StatementAST):
    """Python callee 调用节点。"""

    callee: FunctionAST
    args: list[ValueAST]
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.callee, FunctionAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "CallAST callee must be FunctionAST")
        from .symbol import ConstValueAST

        self.args = [arg if isinstance(arg, ValueAST) else ConstValueAST(arg, location=self.location) for arg in self.args]
        if len(self.args) != len(self.callee.inputs):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Python callee arity mismatch")
        if bool(self.callee.has_explicit_return.raw_value) and not bool(self.callee.returns_none.raw_value):
            raise KernelCodeError(ErrorKind.UNSUPPORTED, ErrorModule.MLIR_GEN, "Python callee return value is unsupported")

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 Python callee 调用发射为 `func.call`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        operands: list[SSAValue] = []
        for arg in self.args:
            emitted = arg.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                if not emitted.results:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Python callee argument has no result")
                emitted = emitted.results[0]
            if not isinstance(emitted, SSAValue):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Python callee arguments must lower to SSA values")
            operands.append(emitted)
        call_op = func.CallOp(self.callee.name, operands, ())
        block.add_op(call_op)
        return None
