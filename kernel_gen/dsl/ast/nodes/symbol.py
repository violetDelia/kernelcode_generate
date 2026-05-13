"""DSL AST symbol node definitions.


功能说明:
- 定义 `symbol` dialect 相关 DSL AST 节点。
- 节点只保存 DSL 语义数据，`emit_mlir(ctx, block)` 递归发射对应 `symbol.*` op。
- `!symbol.iter<...>` 参与 symbol 二元算术时按 `iter<start,end,step>` token 生成结果；`!symbol.int<"?">` 仍传播为 `!symbol.int<"?">`。
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
- `SymbolAddAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolSubAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolMulAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolTrueDivAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolFloorDivAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolMinAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolMaxAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolBinaryAST.result_symbol() -> int | SymbolDim | None`
- `SymbolEqAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolNeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolLtAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolLeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolGtAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `SymbolGeAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`

使用示例:
- from kernel_gen.dsl.ast.nodes.symbol import SymbolAddAST, SymbolDimAST
- expr = SymbolAddAST(SymbolDimAST("M"), ConstValueAST(1))

关联文件:
- spec: spec/dsl/ast/nodes/symbol.md
- test: test/dsl/ast/nodes/test_symbol.py
- 功能实现: kernel_gen/dsl/ast/nodes/symbol.py
"""

from __future__ import annotations

import re
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
    SymbolMaxOp,
    SymbolMinOp,
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
    "SymbolMinAST",
    "SymbolMaxAST",
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


def _normalize_symbol_operand_expr(value: int | str) -> int | str:
    """把 symbol operand 表达规整为 `SymbolDim` 可消费的输入。

    功能说明:
    - 将纯整数字符串转换为 `int`，保留动态 symbol 文本不变。
    - 供 symbol 二元表达组合逻辑复用，避免每个 op 重复处理整数字面量。

    使用示例:
    - normalized = _normalize_symbol_operand_expr("4")
    - symbolic = _normalize_symbol_operand_expr("N - 1")
    """

    if isinstance(value, int):
        return value
    return int(value) if value.lstrip("-").isdigit() else value


def _symbol_expr_text_from_value(value: int | str | SymbolDim) -> str:
    """把 Python / SymbolDim 表达规整为 `SymbolExprAttr` 支持的文本。

    功能说明:
    - 将历史 `SymbolDim` 输出的 `/`、`//` 除法文本转换为 `floordiv`。
    - 仅服务当前 symbol AST 结果类型构造，不作为跨文件公开入口。

    使用示例:
    - text = _symbol_expr_text_from_value(SymbolDim("M") // 2)
    """

    if isinstance(value, SymbolDim):
        value = value.get_value()
    text = str(value).strip()
    if text.startswith("floor(") and text.endswith(")"):
        text = text[len("floor(") : -1].strip()
    text = text.replace("//", " floordiv ")
    text = re.sub(r"(?<!/)/(?!/)", " floordiv ", text)
    return " ".join(text.split())


def _parenthesize_symbol_expr_operand(value: int | str) -> str:
    """按 `SymbolExprAttr` 表达语法为复合 operand 补括号。

    功能说明:
    - 单个整数、标识符或 `?` 保持原样。
    - 复合加减乘除与 `min/max` 表达补括号，避免组合二元表达时改变优先级。

    使用示例:
    - text = _parenthesize_symbol_expr_operand("M + 1")
    """

    text = str(value)
    if re.fullmatch(r"-?\d+|[A-Za-z_][A-Za-z0-9_]*|\?|iter<[^%]*>", text):
        return text
    if text.startswith("(") and text.endswith(")"):
        return text
    return f"({text})"


def _symbol_iter_token_text(iter_type: SymbolIterType) -> str:
    """从 `SymbolIterType` 构造公开 `iter<start,end,step>` 文本。

    功能说明:
    - 只读取 type 上的 start/end/step 语义字段。
    - 用 `SymbolValueType.from_expr(...)` 校验并 canonicalize token，不依赖 SSA/name_hint/runtime 名。

    使用示例:
    - token = _symbol_iter_token_text(SymbolIterType.from_bounds("0", "N", "TILE"))
    """

    token = f"iter<{iter_type.start.expr.data},{iter_type.end.expr.data},{iter_type.step.expr.data}>"
    value = SymbolValueType.from_expr(token).get_value()
    if not isinstance(value, str):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol.iter token must lower to symbol expression")
    return value


def _symbol_expr_from_ssa(value: SSAValue) -> int | str:
    """从 symbol SSA value 提取公开表达文本。

    功能说明:
    - 从 `!symbol.int` 类型读取已记录的表达文本。
    - 对 `!symbol.iter` 从公开 type 字段构造 `iter<start,end,step>` token。
    - 非 symbol SSA value 按公开 MLIR 生成合同报错。

    使用示例:
    - expr = _symbol_expr_from_ssa(symbol_value)
    """

    if isinstance(value.type, SymbolValueType):
        return value.type.get_value()
    if isinstance(value.type, SymbolIterType):
        return _symbol_iter_token_text(value.type)
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol operands must have !symbol.int or !symbol.iter type")


def _compose_symbol_binary_expr(op_name: str, lhs: int | str, rhs: int | str) -> str:
    """按公开 symbol 算术语义生成结果类型表达。

    功能说明:
    - 任一 operand 表达为 `?` 时，结果直接传播为 `?`。
    - 对可由 `SymbolDim` 解析的表达复用解析期算术语义。
    - `min/max` 在双整数输入时直接折叠，否则生成 `min(lhs, rhs)` 或 `max(lhs, rhs)` 文本。

    使用示例:
    - expr = _compose_symbol_binary_expr("add", "N", 1)
    - min_expr = _compose_symbol_binary_expr("min", "tile", "N - i")
    """

    if lhs == "?" or rhs == "?":
        return "?"
    lhs_text = _symbol_expr_text_from_value(lhs)
    rhs_text = _symbol_expr_text_from_value(rhs)
    lhs_operand = _normalize_symbol_operand_expr(lhs_text)
    rhs_operand = _normalize_symbol_operand_expr(rhs_text)
    if op_name == "min":
        return str(min(lhs_operand, rhs_operand)) if isinstance(lhs_operand, int) and isinstance(rhs_operand, int) else f"min({lhs_operand}, {rhs_operand})"
    if op_name == "max":
        return str(max(lhs_operand, rhs_operand)) if isinstance(lhs_operand, int) and isinstance(rhs_operand, int) else f"max({lhs_operand}, {rhs_operand})"
    if isinstance(lhs_operand, int) and isinstance(rhs_operand, int):
        if op_name == "add":
            return str(lhs_operand + rhs_operand)
        if op_name == "sub":
            return str(lhs_operand - rhs_operand)
        if op_name == "mul":
            return str(lhs_operand * rhs_operand)
        if op_name in {"truediv", "floordiv"}:
            return str(lhs_operand // rhs_operand)
    sigil = {
        "add": "+",
        "sub": "-",
        "mul": "*",
        "truediv": "floordiv",
        "floordiv": "floordiv",
    }.get(op_name)
    if sigil is None:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported symbol binary AST")
    return f"{_parenthesize_symbol_expr_operand(lhs_operand)} {sigil} {_parenthesize_symbol_expr_operand(rhs_operand)}"


def _symbol_min_runtime_value(lhs: int | SymbolDim, rhs: int | SymbolDim) -> int | SymbolDim:
    """返回 `min(lhs, rhs)` 的解析期 symbol 语义。

    功能说明:
    - 双整数输入直接返回 Python `min(...)` 结果。
    - 动态 symbol 输入通过 `sympy.Min` 构造 `SymbolDim`，保持解析期表达可继续组合。
    - 缺少动态表达依赖时按 MLIR 生成合同公开失败。

    使用示例:
    - value = _symbol_min_runtime_value(4, SymbolDim("N"))
    """

    if isinstance(lhs, int) and isinstance(rhs, int):
        return min(lhs, rhs)
    try:
        import sympy as sp
    except Exception as exc:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol.min requires sympy for dynamic operands") from exc
    lhs_symbol = lhs if isinstance(lhs, int) else lhs.get_symbol()
    rhs_symbol = rhs if isinstance(rhs, int) else rhs.get_symbol()
    return SymbolDim(sp.Min(lhs_symbol, rhs_symbol))


def _symbol_max_runtime_value(lhs: int | SymbolDim, rhs: int | SymbolDim) -> int | SymbolDim:
    """返回 `max(lhs, rhs)` 的解析期 symbol 语义。

    功能说明:
    - 双整数输入直接返回 Python `max(...)` 结果。
    - 动态 symbol 输入通过 `sympy.Max` 构造 `SymbolDim`，保持解析期表达可继续组合。
    - 缺少动态表达依赖时按 MLIR 生成合同公开失败。

    使用示例:
    - value = _symbol_max_runtime_value(4, SymbolDim("N"))
    """

    if isinstance(lhs, int) and isinstance(rhs, int):
        return max(lhs, rhs)
    try:
        import sympy as sp
    except Exception as exc:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol.max requires sympy for dynamic operands") from exc
    lhs_symbol = lhs if isinstance(lhs, int) else lhs.get_symbol()
    rhs_symbol = rhs if isinstance(rhs, int) else rhs.get_symbol()
    return SymbolDim(sp.Max(lhs_symbol, rhs_symbol))


def _is_unknown_runtime_symbol(value: int | SymbolDim) -> bool:
    """判断解析期 symbol 值是否为 unknown。

    功能说明:
    - 仅在当前文件内服务 `SymbolBinaryAST.result_symbol()`。
    - 将来自 loop iterator 的 unknown runtime symbol 继续传播为 `SymbolDim("?")`。
    - 只检查 `SymbolDim.get_symbol().free_symbols` 中是否含 `?`，避免为了 unknown 判断触发公开值简化。

    使用示例:
    - is_unknown = _is_unknown_runtime_symbol(SymbolDim("?"))
    """

    return isinstance(value, SymbolDim) and any(symbol.name == "?" for symbol in value.get_symbol().free_symbols)


@dataclass
class SymbolBinaryAST(ValueAST):
    """符号二元计算抽象节点。"""

    lhs: ValueAST
    rhs: ValueAST
    location: SourceLocation | None = None

    def result_symbol(self) -> int | SymbolDim | None:
        """返回符号二元表达式的解析期结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 递归读取左右节点的 `result_symbol()`。
        - 结果保持 `int | SymbolDim`，供 shape/stride 与赋值绑定使用。
        - 任一 operand 解析期语义为 `?` 时，结果继续传播为 `SymbolDim("?")`。

        使用示例:
        - symbol = SymbolAddAST(SymbolDimAST("M"), ConstValueAST(1)).result_symbol()
        """

        lhs = self.lhs.result_symbol()
        rhs = self.rhs.result_symbol()
        if lhs is None or rhs is None:
            return None
        if _is_unknown_runtime_symbol(lhs) or _is_unknown_runtime_symbol(rhs):
            return SymbolDim("?")
        lhs_symbol = lhs if isinstance(lhs, SymbolDim) else SymbolDim(lhs)
        rhs_symbol = rhs if isinstance(rhs, SymbolDim) else SymbolDim(rhs)
        try:
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
            elif isinstance(self, SymbolMinAST):
                min_value = _symbol_min_runtime_value(lhs, rhs)
                return SymbolDim("?") if _is_unknown_runtime_symbol(min_value) else min_value
            elif isinstance(self, SymbolMaxAST):
                max_value = _symbol_max_runtime_value(lhs, rhs)
                return SymbolDim("?") if _is_unknown_runtime_symbol(max_value) else max_value
            else:
                return None
        except (TypeError, ValueError):
            return None
        result_value = result.get_value()
        return result_value if isinstance(result_value, int) else result

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射符号二元计算 op。

        功能说明:
        - 普通 symbol 二元算术按左右 operand 顺序发射对应 `symbol.*` op。
        - `SymbolMinAST` / `SymbolMaxAST` 先预物化复合 operand 中的直接整数常量，再发射算术和最终最值 op。
        - 该顺序锁定 `min/max(lhs + 1, rhs - 2)` 的 MLIR 文本合同，避免常量插入位置随递归路径漂移。

        使用示例:
        - value = SymbolMinAST(SymbolAddAST(SymbolDimAST("N"), ConstValueAST(1)), SymbolDimAST("M")).emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        if isinstance(self, (SymbolMinAST, SymbolMaxAST)):
            pre_emitted: dict[int, SSAValue] = {}
            _preemit_symbol_int_constants(self.lhs, ctx, block, pre_emitted)
            _preemit_symbol_int_constants(self.rhs, ctx, block, pre_emitted)
            lhs = _emit_symbol_value_ast(self.lhs, ctx, block, pre_emitted)
            rhs = _emit_symbol_value_ast(self.rhs, ctx, block, pre_emitted)
            return _emit_symbol_binary_op(self, lhs, rhs, block)
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
        lhs_value = _symbol_expr_from_ssa(lhs)
        rhs_value = _symbol_expr_from_ssa(rhs)
        if isinstance(self, SymbolAddAST):
            op = SymbolAddOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("add", lhs_value, rhs_value)))
        elif isinstance(self, SymbolSubAST):
            op = SymbolSubOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("sub", lhs_value, rhs_value)))
        elif isinstance(self, SymbolMulAST):
            op = SymbolMulOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("mul", lhs_value, rhs_value)))
        elif isinstance(self, SymbolTrueDivAST):
            op = SymbolDivOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("truediv", lhs_value, rhs_value)))
        elif isinstance(self, SymbolFloorDivAST):
            op = SymbolFloorDivOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("floordiv", lhs_value, rhs_value)))
        elif isinstance(self, SymbolMinAST):
            op = SymbolMinOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("min", lhs_value, rhs_value)))
        elif isinstance(self, SymbolMaxAST):
            op = SymbolMaxOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("max", lhs_value, rhs_value)))
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


class SymbolMinAST(SymbolBinaryAST):
    """符号最小值节点。"""


class SymbolMaxAST(SymbolBinaryAST):
    """符号最大值节点。"""


def _preemit_symbol_int_constants(
    value: ValueAST,
    ctx: Context,
    block: Block,
    pre_emitted: dict[int, SSAValue],
) -> None:
    """预先物化 `symbol.min/max` 两侧表达式中的整数常量。

    功能说明:
    - 递归扫描 `symbol.min/max` 左右 operand 的 `SymbolBinaryAST` 子树。
    - 只提前发射直接整数常量，动态 symbol 与其它 operand 保持原发射路径。
    - 通过 `pre_emitted` 缓存避免同一 AST 节点重复生成 `symbol.const`。

    使用示例:
    - pre_emitted: dict[int, SSAValue] = {}
    - _preemit_symbol_int_constants(expr, ctx, block, pre_emitted)
    """

    if isinstance(value, SymbolBinaryAST):
        _preemit_symbol_int_constants(value.lhs, ctx, block, pre_emitted)
        _preemit_symbol_int_constants(value.rhs, ctx, block, pre_emitted)
        return
    if id(value) in pre_emitted:
        return
    if not _is_preemittable_symbol_int_const(value):
        return
    emitted = value.emit_mlir(ctx, block)
    if isinstance(emitted, Operation):
        block.add_op(emitted)
        emitted = emitted.results[0]
    if not isinstance(emitted, SSAValue):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol const must lower to SSA value")
    pre_emitted[id(value)] = emitted


def _is_preemittable_symbol_int_const(value: ValueAST) -> bool:
    """判断 AST 节点是否会直接发射 `symbol.const`。

    功能说明:
    - 识别 `ConstValueAST` 中的非 bool 整数常量。
    - 识别承载整数值的 `SymbolDimAST`。
    - 其它节点不提前物化，避免改变动态 symbol 的发射时序。

    使用示例:
    - should_preemit = _is_preemittable_symbol_int_const(ConstValueAST(1))
    """

    if isinstance(value, ConstValueAST):
        raw_value = value.raw_value
        return isinstance(raw_value, int) and not isinstance(raw_value, bool)
    if isinstance(value, SymbolDimAST):
        raw_value = value.symbol.get_value()
        return isinstance(raw_value, int) and not isinstance(raw_value, bool)
    return False


def _emit_symbol_value_ast(
    value: ValueAST,
    ctx: Context,
    block: Block,
    pre_emitted: dict[int, SSAValue],
) -> SSAValue:
    """发射 `symbol.min/max` operand，并复用已提前物化的整数常量。

    功能说明:
    - 优先返回 `_preemit_symbol_int_constants(...)` 已缓存的 `symbol.const` SSA value。
    - 对嵌套 `SymbolBinaryAST` 递归发射左右 operand，再发射对应二元 op。
    - 对普通 `ValueAST` 走其公开 `emit_mlir(...)` 行为，并校验结果为 SSA value。

    使用示例:
    - operand = _emit_symbol_value_ast(expr, ctx, block, pre_emitted)
    """

    cached = pre_emitted.get(id(value))
    if cached is not None:
        return cached
    if isinstance(value, SymbolBinaryAST):
        lhs = _emit_symbol_value_ast(value.lhs, ctx, block, pre_emitted)
        rhs = _emit_symbol_value_ast(value.rhs, ctx, block, pre_emitted)
        return _emit_symbol_binary_op(value, lhs, rhs, block)
    emitted = value.emit_mlir(ctx, block)
    if isinstance(emitted, Operation):
        block.add_op(emitted)
        emitted = emitted.results[0]
    if not isinstance(emitted, SSAValue):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol operand must lower to SSA value")
    return emitted


def _emit_symbol_binary_op(value: SymbolBinaryAST, lhs: SSAValue, rhs: SSAValue, block: Block) -> SSAValue:
    """根据 `SymbolBinaryAST` 子类发射对应 symbol 二元 op。

    功能说明:
    - 根据具体 `SymbolBinaryAST` 子类选择 `symbol.add/sub/mul/div/floordiv/min/max` op。
    - 通过 `_compose_symbol_binary_expr(...)` 同步生成结果 `!symbol.int` 表达文本。
    - 仅在当前文件内服务 `SymbolMinAST` / `SymbolMaxAST` 递归 operand 发射，不作为跨文件公开入口。

    使用示例:
    - result = _emit_symbol_binary_op(SymbolAddAST(lhs_ast, rhs_ast), lhs_value, rhs_value, block)
    """

    lhs_value = _symbol_expr_from_ssa(lhs)
    rhs_value = _symbol_expr_from_ssa(rhs)
    if isinstance(value, SymbolAddAST):
        op = SymbolAddOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("add", lhs_value, rhs_value)))
    elif isinstance(value, SymbolSubAST):
        op = SymbolSubOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("sub", lhs_value, rhs_value)))
    elif isinstance(value, SymbolMulAST):
        op = SymbolMulOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("mul", lhs_value, rhs_value)))
    elif isinstance(value, SymbolTrueDivAST):
        op = SymbolDivOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("truediv", lhs_value, rhs_value)))
    elif isinstance(value, SymbolFloorDivAST):
        op = SymbolFloorDivOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("floordiv", lhs_value, rhs_value)))
    elif isinstance(value, SymbolMinAST):
        op = SymbolMinOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("min", lhs_value, rhs_value)))
    elif isinstance(value, SymbolMaxAST):
        op = SymbolMaxOp(lhs, rhs, SymbolValueType.from_expr(_compose_symbol_binary_expr("max", lhs_value, rhs_value)))
    else:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported symbol binary AST")
    block.add_op(op)
    return op.results[0]


@dataclass
class SymbolCompareAST(ValueAST):
    """符号比较抽象节点。"""

    lhs: ValueAST
    rhs: ValueAST
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
