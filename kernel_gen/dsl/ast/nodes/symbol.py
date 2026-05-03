"""DSL AST symbol node definitions.


功能说明:
- 定义 `symbol` dialect 相关 DSL AST 节点。
- 节点只保存 DSL 语义数据，`emit_mlir(ctx, block)` 递归发射对应 `symbol.*` op。
- `basic.py` 不再承载 symbol dialect 节点实现，避免基础节点文件同时维护 symbol op 发射逻辑。

API 列表:
- `SymbolDimAST(symbol: SymbolDim | int | str, location: SourceLocation | None = None, runtime_symbol: SymbolDim | int | None = None)`
- `SymbolDimAST.result_symbol() -> int | SymbolDim | None`
- `ConstValueAST(type: IntTypeAttrAST | FloatTypeAttrAST | int | float | str, value: int | float | str | None = None, location: SourceLocation | None = None)`
- `ConstValueAST.result_symbol() -> int | SymbolDim | None`
- `ConstValueAST.result_scalar() -> int | float | bool | str | SymbolDim | None`
- `SymbolListAST(values: list[ValueAST | int | str | SymbolDim] | tuple[ValueAST | int | str | SymbolDim, ...] | ValueAST | int | str | SymbolDim, location: SourceLocation | None = None)`
- `SymbolListAST.result_symbols() -> list[int | SymbolDim] | None`
- `SymbolToFloatAST(source: ValueAST, location: SourceLocation | None = None)`
- `TensorAxisAccessAST(tensor: MemoryAST, kind: PythonObjectAttrAST, axis: ConstValueAST, location: SourceLocation | None = None)`
- `SymbolAddAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolSubAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolMulAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolTrueDivAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolFloorDivAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolBinaryAST.result_symbol() -> int | SymbolDim | None`
- `SymbolEqAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolNeAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolLtAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolLeAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolGtAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`
- `SymbolGeAST(lhs: SymbolDimAST | ConstValueAST, rhs: SymbolDimAST | ConstValueAST, location: SourceLocation | None = None)`

使用示例:
- from kernel_gen.dsl.ast.nodes.symbol import SymbolAddAST, SymbolDimAST
- expr = SymbolAddAST(SymbolDimAST("M"), ConstValueAST(1))

关联文件:
- spec: spec/dsl/ast/nodes/symbol.md
- test: test/dsl/ast/nodes/test_symbol.py
- 功能实现: kernel_gen/dsl/ast/nodes/symbol.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import arith
from xdsl.dialects.builtin import Float64Type, FloatAttr, f32, i1
from xdsl.ir import Block, Operation, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolFloorDivOp,
    SymbolGeOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolGtOp,
    SymbolIterType,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolToFloatOp,
    SymbolValueType,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

from .attr import (
    EmitMlirResult,
    FloatTypeAttrAST,
    IntTypeAttrAST,
    ListAST,
    PythonObjectAttrAST,
    SourceLocation,
    TupleAST,
)
from .basic import MemoryAST, ValueAST

__all__ = [
    "SymbolDimAST",
    "ConstValueAST",
    "SymbolListAST",
    "SymbolToFloatAST",
    "TensorAxisAccessAST",
    "SymbolBinaryAST",
    "SymbolAddAST",
    "SymbolSubAST",
    "SymbolMulAST",
    "SymbolTrueDivAST",
    "SymbolFloorDivAST",
    "SymbolCompareAST",
    "SymbolEqAST",
    "SymbolNeAST",
    "SymbolLtAST",
    "SymbolLeAST",
    "SymbolGtAST",
    "SymbolGeAST",
]


@dataclass
class SymbolDimAST(ValueAST):
    """符号维度值节点。"""

    symbol: SymbolDim
    location: SourceLocation | None = None
    runtime_symbol: SymbolDim | int | None = None

    def __init__(
        self,
        symbol: SymbolDim | int | str,
        location: SourceLocation | None = None,
        runtime_symbol: SymbolDim | int | None = None,
    ) -> None:
        self.symbol = symbol if isinstance(symbol, SymbolDim) else SymbolDim(symbol)
        self.location = location
        self.runtime_symbol = runtime_symbol

    @property
    def name(self) -> str:
        """返回符号维度的稳定名称。"""

        return str(self.symbol.get_value())

    def result_symbol(self) -> int | SymbolDim | None:
        """返回当前符号维度的解析期 symbol 语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 保留符号维度对象本身，避免 visitor 按 runtime arg 反推具体值。

        使用示例:
        - symbol = dim.result_symbol()
        """

        return self.runtime_symbol if self.runtime_symbol is not None else self.symbol

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射符号维度为 `!symbol.int` SSA value。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        symbol_text = str(self.symbol.get_value())
        current_block: Block | None = block
        while current_block is not None:
            for op in reversed(tuple(current_block.ops)):
                for result in op.results:
                    if result.name_hint == symbol_text:
                        return result
            for argument in current_block.args:
                if argument.name_hint == symbol_text:
                    return argument
            current_block = current_block.parent_block()
        value = self.symbol.get_value()
        if isinstance(value, int):
            const_op = SymbolConstOp(value)
            if block is not None:
                block.add_op(const_op)
                return const_op.results[0]
            return const_op
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unbound symbol dimension: {symbol_text}")


@dataclass
class ConstValueAST(ValueAST):
    """整数、浮点或解析期字符串常量节点。"""

    type: IntTypeAttrAST | FloatTypeAttrAST
    value: PythonObjectAttrAST
    location: SourceLocation | None = None

    def __init__(
        self,
        type: IntTypeAttrAST | FloatTypeAttrAST | int | float | str,
        value: int | float | str | None = None,
        location: SourceLocation | None = None,
    ) -> None:
        raw_value = type if value is None else value
        if value is None:
            type_node: IntTypeAttrAST | FloatTypeAttrAST = FloatTypeAttrAST(NumericType.Float64, location) if isinstance(raw_value, float) else IntTypeAttrAST(64, True, location)
        elif isinstance(type, (IntTypeAttrAST, FloatTypeAttrAST)):
            type_node = type
        else:
            type_node = FloatTypeAttrAST(NumericType.Float64, location) if isinstance(raw_value, float) else IntTypeAttrAST(64, True, location)
        self.type = type_node
        self.value = PythonObjectAttrAST(raw_value, location)
        self.location = location

    @property
    def raw_value(self) -> int | float | str | bool:
        """返回常量承载的实际 Python 值。"""

        return self.value.attr

    def result_symbol(self) -> int | SymbolDim | None:
        """返回整数常量的 symbol 语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 仅 `int` 且非 `bool` 的常量可作为 symbol 整数。

        使用示例:
        - symbol = ConstValueAST(4).result_symbol()
        """

        value = self.raw_value
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    def result_scalar(self) -> int | float | bool | str | SymbolDim | None:
        """返回常量承载的普通标量语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 供 parser 绑定不产生 IR 的常量别名。

        使用示例:
        - scalar = ConstValueAST(1).result_scalar()
        """

        return self.raw_value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射常量为 MLIR constant。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        value = self.raw_value
        if isinstance(value, bool):
            const_op = arith.ConstantOp.from_int_and_width(1 if value else 0, i1)
            if block is not None:
                block.add_op(const_op)
                return const_op.results[0]
            return const_op
        if isinstance(value, int):
            const_op = SymbolConstOp(value)
            if block is not None:
                block.add_op(const_op)
                return const_op.results[0]
            return const_op
        if isinstance(value, float):
            const_op = arith.ConstantOp(FloatAttr(value, Float64Type()))
            if block is not None:
                block.add_op(const_op)
                return const_op.results[0]
            return const_op
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported constant type")


@dataclass
class SymbolListAST(ValueAST):
    """符号列表节点。"""

    values: tuple[ValueAST, ...]
    location: SourceLocation | None = None

    def __init__(
        self,
        values: list[ValueAST | int | str | SymbolDim] | tuple[ValueAST | int | str | SymbolDim, ...] | ValueAST | int | str | SymbolDim,
        location: SourceLocation | None = None,
    ) -> None:
        if isinstance(values, (ListAST, TupleAST)):
            raw_values = values.items
        else:
            raw_values = values if isinstance(values, (list, tuple)) else (values,)
        normalized: list[ValueAST] = []
        for item in raw_values:
            if isinstance(item, ValueAST):
                normalized.append(item)
            elif isinstance(item, int):
                normalized.append(ConstValueAST(IntTypeAttrAST(64), item, location))
            elif isinstance(item, (str, SymbolDim)):
                normalized.append(SymbolDimAST(item, location))
            else:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "SymbolListAST item must be ValueAST, int or SymbolDim")
        self.values = tuple(normalized)
        self.location = location

    @property
    def items(self) -> tuple[ValueAST, ...]:
        """提供列表项读取入口。"""

        return self.values

    def result_symbols(self) -> list[int | SymbolDim] | None:
        """读取当前列表的解析期 symbol 参数。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 每一项都必须能通过自身 `result_symbol()` 解析为 `int | SymbolDim`。
        - 任一项不满足时返回 `None`，由调用节点放弃解析期结果推导。

        使用示例:
        - dims = shape.result_symbols()
        """

        result: list[int | SymbolDim] = []
        for item in self.values:
            symbol_value = item.result_symbol()
            if symbol_value is None:
                return None
            result.append(symbol_value)
        return result

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射符号列表为 SSA value 列表。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        values: list[SSAValue] = []
        for item in self.values:
            emitted = item.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                emitted = emitted.results[0]
            if not isinstance(emitted, SSAValue) or not isinstance(emitted.type, (SymbolValueType, SymbolIterType)):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol list item must lower to symbol value")
            values.append(emitted)
        return values


@dataclass
class SymbolToFloatAST(ValueAST):
    """`float(symbol.int)` 转换节点。"""

    source: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 symbol-to-float 节点发射为转换 op。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol.to_float source must lower to SSA value")
        if not isinstance(source.type, SymbolValueType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol.to_float source must have type symbol.int")
        op = SymbolToFloatOp(source, f32)
        block.add_op(op)
        return op.results[0]


@dataclass
class TensorAxisAccessAST(ValueAST):
    """memory shape/stride 访问节点。"""

    tensor: MemoryAST
    kind: PythonObjectAttrAST
    axis: ConstValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PythonObjectAttrAST):
            self.kind = PythonObjectAttrAST(self.kind, self.location)
        if not isinstance(self.axis, ConstValueAST):
            self.axis = ConstValueAST(self.axis, location=self.location)

    def result_symbol(self) -> int | SymbolDim | None:
        """返回静态可判定的 memory shape/stride 轴值。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 仅当 tensor 自身能给出解析期 memory 且 axis 为静态整数时返回。

        使用示例:
        - dim = axis_access.result_symbol()
        """

        source = self.tensor.result_memory()
        if not isinstance(source, Memory) or not isinstance(self.axis.raw_value, int):
            return None
        axis = self.axis.raw_value
        values = source.get_shape() if self.kind.attr == "shape" else source.get_stride() if self.kind.attr == "stride" else None
        if values is None or axis < 0 or axis >= len(values):
            return None
        value = values[axis]
        return value if isinstance(value, (SymbolDim, int)) else SymbolDim(value)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 memory axis 访问节点发射为 symbol 查询 op。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        tensor = self.tensor.emit_mlir(ctx, block)
        if isinstance(tensor, Operation):
            block.add_op(tensor)
            tensor = tensor.results[0]
        if not isinstance(tensor, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "tensor axis source must lower to SSA value")
        axis_value = self.axis.raw_value
        kind_value = self.kind.emit_mlir(ctx, None)
        if not isinstance(axis_value, int):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "tensor axis must be a static integer")
        if not isinstance(tensor.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "tensor axis source must be nn.memory")
        rank = len(tensor.type.shape.data if kind_value == "shape" else tensor.type.stride.data)
        if axis_value < 0 or axis_value >= rank:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "tensor axis out of range")
        if kind_value == "shape":
            op = SymbolGetDimOp(tensor, axis_value)
            block.add_op(op)
            return op.results[0]
        if kind_value == "stride":
            op = SymbolGetStrideOp(tensor, axis_value)
            block.add_op(op)
            return op.results[0]
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported tensor axis access: {kind_value}")


@dataclass
class SymbolBinaryAST(ValueAST):
    """符号二元计算抽象节点。"""

    lhs: SymbolDimAST | ConstValueAST
    rhs: SymbolDimAST | ConstValueAST
    location: SourceLocation | None = None

    def result_symbol(self) -> int | SymbolDim | None:
        """返回符号二元表达式的解析期结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 递归读取左右节点的 `result_symbol()`。
        - 结果保持 `int | SymbolDim`，供 shape/stride 与赋值绑定使用。

        使用示例:
        - symbol = SymbolAddAST(SymbolDimAST("M"), ConstValueAST(1)).result_symbol()
        """

        lhs = self.lhs.result_symbol()
        rhs = self.rhs.result_symbol()
        if lhs is None or rhs is None:
            return None
        lhs_symbol = lhs if isinstance(lhs, SymbolDim) else SymbolDim(lhs)
        rhs_symbol = rhs if isinstance(rhs, SymbolDim) else SymbolDim(rhs)
        if isinstance(self, SymbolAddAST):
            result = lhs_symbol + rhs_symbol
        elif isinstance(self, SymbolSubAST):
            result = lhs_symbol - rhs_symbol
        elif isinstance(self, SymbolMulAST):
            result = lhs_symbol * rhs_symbol
        elif isinstance(self, SymbolTrueDivAST):
            result = lhs_symbol / rhs_symbol
        elif isinstance(self, SymbolFloorDivAST):
            result = lhs_symbol // rhs_symbol
        else:
            return None
        result_value = result.get_value()
        return result_value if isinstance(result_value, int) else result

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射符号二元计算 op。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        lhs = self.lhs.emit_mlir(ctx, block)
        if isinstance(lhs, Operation):
            block.add_op(lhs)
            lhs = lhs.results[0]
        rhs = self.rhs.emit_mlir(ctx, block)
        if isinstance(rhs, Operation):
            block.add_op(rhs)
            rhs = rhs.results[0]
        if not isinstance(lhs, SSAValue) or not isinstance(rhs, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol operands must lower to SSA values")
        lhs_value = lhs.type.get_value() if isinstance(lhs.type, SymbolValueType) else None
        rhs_value = rhs.type.get_value() if isinstance(rhs.type, SymbolValueType) else None
        if lhs_value is None or rhs_value is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol operands must have !symbol.int type")
        lhs_operand = int(lhs_value) if isinstance(lhs_value, str) and lhs_value.lstrip("-").isdigit() else lhs_value
        rhs_operand = int(rhs_value) if isinstance(rhs_value, str) and rhs_value.lstrip("-").isdigit() else rhs_value
        lhs_symbol = SymbolDim(lhs_operand)
        rhs_symbol = SymbolDim(rhs_operand)
        if isinstance(self, SymbolAddAST):
            op = SymbolAddOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol + rhs_symbol).get_value())))
        elif isinstance(self, SymbolSubAST):
            op = SymbolSubOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol - rhs_symbol).get_value())))
        elif isinstance(self, SymbolMulAST):
            op = SymbolMulOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol * rhs_symbol).get_value())))
        elif isinstance(self, SymbolTrueDivAST):
            op = SymbolDivOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol / rhs_symbol).get_value())))
        elif isinstance(self, SymbolFloorDivAST):
            op = SymbolFloorDivOp(lhs, rhs, SymbolValueType.from_expr(str((lhs_symbol // rhs_symbol).get_value())))
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported symbol binary AST")
        block.add_op(op)
        return op.results[0]


class SymbolAddAST(SymbolBinaryAST):
    """符号加法节点。"""


class SymbolSubAST(SymbolBinaryAST):
    """符号减法节点。"""


class SymbolMulAST(SymbolBinaryAST):
    """符号乘法节点。"""


class SymbolTrueDivAST(SymbolBinaryAST):
    """符号真除法节点。"""


class SymbolFloorDivAST(SymbolBinaryAST):
    """符号整除节点。"""


@dataclass
class SymbolCompareAST(ValueAST):
    """符号比较抽象节点。"""

    lhs: SymbolDimAST | ConstValueAST
    rhs: SymbolDimAST | ConstValueAST
    location: SourceLocation | None = None

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射符号比较 op。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        lhs = self.lhs.emit_mlir(ctx, block)
        if isinstance(lhs, Operation):
            block.add_op(lhs)
            lhs = lhs.results[0]
        rhs = self.rhs.emit_mlir(ctx, block)
        if isinstance(rhs, Operation):
            block.add_op(rhs)
            rhs = rhs.results[0]
        if not isinstance(lhs, SSAValue) or not isinstance(rhs, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol compare operands must lower to SSA values")
        if isinstance(self, SymbolEqAST):
            op = SymbolEqOp(lhs, rhs)
        elif isinstance(self, SymbolNeAST):
            op = SymbolNeOp(lhs, rhs)
        elif isinstance(self, SymbolLtAST):
            op = SymbolLtOp(lhs, rhs)
        elif isinstance(self, SymbolLeAST):
            op = SymbolLeOp(lhs, rhs)
        elif isinstance(self, SymbolGtAST):
            op = SymbolGtOp(lhs, rhs)
        elif isinstance(self, SymbolGeAST):
            op = SymbolGeOp(lhs, rhs)
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported symbol compare AST")
        block.add_op(op)
        return op.results[0]


class SymbolEqAST(SymbolCompareAST):
    """符号相等比较节点。"""


class SymbolNeAST(SymbolCompareAST):
    """符号不等比较节点。"""


class SymbolLtAST(SymbolCompareAST):
    """符号小于比较节点。"""


class SymbolLeAST(SymbolCompareAST):
    """符号小于等于比较节点。"""


class SymbolGtAST(SymbolCompareAST):
    """符号大于比较节点。"""


class SymbolGeAST(SymbolCompareAST):
    """符号大于等于比较节点。"""
