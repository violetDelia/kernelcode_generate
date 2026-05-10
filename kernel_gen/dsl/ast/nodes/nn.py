"""DSL AST NN node definitions.


功能说明:
- 定义 NN helper 对应的 AST 节点，节点只保存 DSL 语义数据，不执行 lowering。
- Matmul 仅在 contracting 维度可证明为同一结构化符号表达时保持动态兼容判断。
- Matmul/transpose 结果类型继承已发射 operand 的公开符号表达。
- ConvAST 在 img2col/reshape/matmul 链路中使用公开符号计算表达承接动态维度。

API 列表:
- `NnImg2Col1dAST(source: ValueAST, kw: SymbolDimAST | ConstValueAST, sw: SymbolDimAST | ConstValueAST = ..., dw: SymbolDimAST | ConstValueAST = ..., pl: SymbolDimAST | ConstValueAST = ..., pr: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`
- `NnImg2Col2dAST(source: ValueAST, kh: SymbolDimAST | ConstValueAST, kw: SymbolDimAST | ConstValueAST, sh: SymbolDimAST | ConstValueAST = ..., sw: SymbolDimAST | ConstValueAST = ..., dh: SymbolDimAST | ConstValueAST = ..., dw: SymbolDimAST | ConstValueAST = ..., ph: SymbolDimAST | ConstValueAST = ..., pw: SymbolDimAST | ConstValueAST = ..., pl: SymbolDimAST | ConstValueAST = ..., pr: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`
- `NnBroadcastAST(value: ValueAST, target: ValueAST, location: SourceLocation | None = None)`
- `NnBroadcastToAST(source: ValueAST, target_shape: SymbolListAST, space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- `NnTransposeAST(value: ValueAST, perm: SymbolListAST, location: SourceLocation | None = None)`
- `NnReluAST(value: ValueAST, location: SourceLocation | None = None)` / `NnSigmoidAST(...)` / `NnTanhAST(...)` / `NnExpAST(...)`
- `NnLeakyReluAST(value: ValueAST, alpha: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- `NnHardSigmoidAST(value: ValueAST, alpha: ConstValueAST | SymbolDimAST, beta: ConstValueAST | SymbolDimAST, location: SourceLocation | None = None)`
- `NnReduceAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)`
- `NnReduceSumAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, keepdim: BoolValueAST | None = None, location: SourceLocation | None = None)` / `NnReduceMinAST(...)` / `NnReduceMaxAST(...)`
- `NnSoftmaxAST(value: ValueAST, axis: SymbolDimAST | ConstValueAST | None = None, location: SourceLocation | None = None)`
- `MatmulAST(lhs: ValueAST, rhs: ValueAST, memoryspace: MemorySpaceAttrAST | None = None, location: SourceLocation | None = None)`
- `FCAST(value: ValueAST, weight: ValueAST, location: SourceLocation | None = None)`
- `ConvAST(value: ValueAST, weight: ValueAST, stride: SymbolListAST, padding: SymbolListAST, dilation: SymbolListAST, groups: SymbolDimAST | ConstValueAST | None = None, location: SourceLocation | None = None)`
- `NnAddAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)` / `NnSubAST(...)` / `NnMulAST(...)` / `NnTrueDivAST(...)` / `NnFloorDivAST(...)`
- `NnEqAST(lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)` / `NnNeAST(...)` / `NnLtAST(...)` / `NnLeAST(...)` / `NnGtAST(...)` / `NnGeAST(...)`

使用示例:
- from kernel_gen.dsl.ast.nodes.nn import NnReluAST
- node = NnReluAST(value)

关联文件:
- spec: spec/dsl/ast/nodes/nn.md
- test: test/dsl/ast/nodes/test_nn.py
- 功能实现: kernel_gen/dsl/ast/nodes/nn.py
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, TypeAlias

from xdsl.context import Context
from xdsl.dialects import arith
from xdsl.dialects.builtin import ArrayAttr, BFloat16Type, Float16Type, Float32Type, Float64Type, FloatAttr, IntegerType, Signedness, f32, i1, i8, i32, i64
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import DmaReshapeOp
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnCastOp,
    NnEqOp,
    NnExpOp,
    NnFloorDivOp,
    NnGeOp,
    NnGtOp,
    NnHardSigmoidOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
    NnLeOp,
    NnLeakyReluOp,
    NnLtOp,
    NnMatmulOp,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
    NnReluOp,
    NnSigmoidOp,
    NnSubOp,
    NnSoftmaxOp,
    NnTanhOp,
    NnTransposeOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolConstOp, SymbolExprAttr, SymbolGetDimOp, SymbolMulOp, SymbolToFloatOp, SymbolToIntOp, SymbolValueType
from kernel_gen.operation import dma as dma_ops
from kernel_gen.operation import nn as nn_ops
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_RANK, NumericType
from .attr import BoolTypeAttrAST, EmitMlirResult, FloatTypeAttrAST, IntTypeAttrAST, MemorySpaceAttrAST, SourceLocation
from .basic import BoolValueAST, MemoryAST, ValueAST
from .symbol import ConstValueAST, SymbolListAST

ReduceAxisElement: TypeAlias = "int | float | bool | str | SymbolDim | ValueAST"
ReduceAxisValue: TypeAlias = "ReduceAxisElement | list[ReduceAxisElement] | tuple[ReduceAxisElement, ...] | None"
ReduceKeepdimValue: TypeAlias = "bool | ValueAST | None"
def _symbol_expr_attr_from_value(value: int | str | SymbolDim) -> SymbolExprAttr:
    """把 NN 结果 type 维度值转换为 `SymbolExprAttr`。

    功能说明:
    - 当前文件内统一 `NnMemoryType` shape/stride 条目构造。
    - 避免继续用旧 `IntAttr` / `StringAttr` 作为 memory 维度。

    使用示例:
    - attr = _symbol_expr_attr_from_value("M")
    """

    return SymbolExprAttr.from_expr(_symbol_expr_text_from_value(value))


def _symbol_expr_text_from_value(value: int | str | SymbolDim) -> str:
    """把 Python / SymbolDim 表达规整为 `SymbolExprAttr` 支持的文本。

    功能说明:
    - 将历史 `SymbolDim` 输出的 `/`、`//` 除法文本转换为 `floordiv`。
    - 仅服务当前 NN AST type 构造与 symbol 结果类型，不作为跨文件公开入口。

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


def _symbol_dim_from_expr_text(text: int | str) -> SymbolDim:
    """把 `SymbolExprAttr` 文本还原为当前 operation 层可消费的 `SymbolDim`。

    功能说明:
    - `SymbolDim` 仍接受 Python 风格 `//` 表达，当前文件内只做语法桥接。
    - 保留解析期 memory 语义供当前 NN lowering 链路调用公开 operation helper。

    使用示例:
    - dim = _symbol_dim_from_expr_text("M floordiv 2")
    """

    if isinstance(text, int):
        return SymbolDim(text)
    return SymbolDim(str(text).replace(" floordiv ", "//"))


def _symbol_expr_text(dim: SymbolExprAttr) -> str:
    """读取 `SymbolExprAttr` 的 canonical 表达文本。

    功能说明:
    - 当前文件内用于动态维度识别、matmul 合同判断与连续 stride 重建。

    使用示例:
    - text = _symbol_expr_text(SymbolExprAttr.from_expr("N"))
    """

    return dim.expr.data


def _static_int_from_symbol_expr(dim: SymbolExprAttr) -> int | None:
    """读取静态整数维度。

    功能说明:
    - 对 `#symbol.expr<4>` 返回 4。
    - 动态 symbol 或 `?` 返回 None。

    使用示例:
    - value = _static_int_from_symbol_expr(SymbolExprAttr.from_expr("4"))
    """

    expr = _symbol_expr_text(dim)
    signless = expr[1:] if expr.startswith("-") else expr
    return int(expr) if signless.isdecimal() else None


def _parenthesize_symbol_expr(expr: str) -> str:
    """在乘法组合中按需为复合 symbol 表达式加括号。

    功能说明:
    - 保持 `N + 1` 这类 shape 维度参与 stride 乘法时语义不变。

    使用示例:
    - text = _parenthesize_symbol_expr("N + 1")
    """

    if expr == "?" or expr.replace("_", "").isalnum() or expr.lstrip("-").isdigit():
        return expr
    return f"({expr})"


def _symbol_expr_product(lhs: int | str, rhs: int | str) -> int | str:
    """组合两个公开 symbol 表达式乘积。

    功能说明:
    - 静态整数直接折叠。
    - 动态表达式以 `SymbolExprAttr` 可解析文本返回。

    使用示例:
    - expr = _symbol_expr_product("M", "N")
    """

    if lhs == 1:
        return rhs
    if rhs == 1:
        return lhs
    if isinstance(lhs, int) and isinstance(rhs, int):
        return lhs * rhs
    return f"{_parenthesize_symbol_expr(str(lhs))} * {_parenthesize_symbol_expr(str(rhs))}"


def _contiguous_stride_values(shape_values: list[int | str]) -> list[int | str]:
    """按公开 shape 表达生成连续 stride 值。

    功能说明:
    - 复用当前文件内 `SymbolExprAttr` 乘积文本规则。
    - 返回值继续交给 `SymbolExprAttr` 构造，避免跨文件调用非公开 stride helper。

    使用示例:
    - values = _contiguous_stride_values(["M", "N"])

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    stride_values: list[int | str] = []
    running: int | str = 1
    for dim_value in reversed(shape_values):
        stride_values.insert(0, running)
        if isinstance(dim_value, int) and isinstance(running, int):
            running = dim_value * running
        else:
            running = _symbol_expr_product(dim_value, running)
    return stride_values


def _shape_value_from_symbol_operand(value: SSAValue, axis: int) -> int | str:
    """从公开 symbol SSA 类型读取 shape 表达。

    功能说明:
    - `!symbol.int<#symbol.expr<expr>>` 优先使用公开类型表达。
    - 匿名 `?` 维度使用 SSA `name_hint` 承接 DSL 变量名。
    - 仍缺少名称时保持 `?`，等待上层显式符号表达收口。

    使用示例:
    - dim = _shape_value_from_symbol_operand(shape_operand, axis=0)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    value_type = value.type
    if isinstance(value_type, SymbolValueType):
        public_value = value_type.get_value()
        if isinstance(public_value, int):
            return public_value
        value_text = str(public_value).replace(" ", "")
        if value_text and value_text != "?":
            return value_text
    if value.name_hint:
        return value.name_hint.replace(" ", "")
    return "?"


def _symbol_operand_public_value(value: SSAValue) -> int | str:
    """读取 symbol operand 的公开表达。

    功能说明:
    - 优先使用 `!symbol.int<#symbol.expr<expr>>` 的结构化表达。
    - 当表达为匿名 `?` 时使用 `name_hint` 承接 DSL 绑定名，避免结果 type 退化为匿名维度。

    使用示例:
    - value = _symbol_operand_public_value(symbol_ssa)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    if not isinstance(value.type, SymbolValueType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "symbol operand must be symbol.int")
    public_value = value.type.get_value()
    if isinstance(public_value, int):
        return public_value
    text = str(public_value).replace(" ", "")
    if text and text != "?":
        return text
    if value.name_hint:
        return value.name_hint.replace(" ", "")
    return "?"


def _shape_value_from_type_dim(dim: Attribute) -> int | str:
    """从 memory type 维度读取公开符号表达。

    功能说明:
    - 静态整数返回 `int`；命名符号或复合表达式返回规范化文本。
    - 匿名动态维度保持 `?`，由上游显式符号计算表达继续收口。

    使用示例:
    - value = _shape_value_from_type_dim(SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    if not isinstance(dim, SymbolExprAttr):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "memory shape dim must be SymbolExprAttr")
    static_value = _static_int_from_symbol_expr(dim)
    if static_value is not None:
        return static_value
    return _symbol_expr_text(dim)


def _shape_values_from_memory_type(memory_type: NnMemoryType) -> list[int | str]:
    """从 `NnMemoryType.shape` 读取公开 shape 表达列表。

    功能说明:
    - 仅消费当前公开 `SymbolExprAttr` layout，不读取旧 IntAttr/StringAttr。
    - 用于 img2col/conv 结果类型把动态维度表达为可计算符号。

    使用示例:
    - values = _shape_values_from_memory_type(memory_type)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    return [_shape_value_from_type_dim(dim) for dim in memory_type.shape.data]


def _img2col_output_shape_value(
    size: int | str | SymbolDim,
    kernel: int | SymbolDim,
    stride: int | SymbolDim,
    dilation: int | SymbolDim,
    pad_low: int | SymbolDim,
    pad_high: int | SymbolDim,
) -> int | SymbolDim:
    """用公开符号计算表达构造 img2col 输出维度。

    功能说明:
    - 按 `(size + pad_low + pad_high - dilation * (kernel - 1) - 1) floordiv stride + 1` 计算。
    - 动态结果保留完整符号表达，避免退化成匿名 `?`。

    使用示例:
    - dim = _img2col_output_shape_value("H", SymbolDim("KH"), SymbolDim("SH"), SymbolDim("DH"), 0, 0)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    result = ((SymbolDim(size) + pad_low + pad_high - SymbolDim(dilation) * (SymbolDim(kernel) - 1) - 1) // stride) + 1
    public_value = result.get_value()
    if isinstance(public_value, int):
        return public_value
    return _symbol_dim_from_expr_text(public_value)


def _source_shape_values_for_transpose(source: SSAValue) -> list[int | str]:
    """读取 transpose source 的类型级 shape 语义。

    功能说明:
    - `dma.reshape` source 优先从公开 shape operands 读取调用点变量名。
    - 其它 source 使用 `NnMemoryType.shape` 的公开 `SymbolExprAttr` 文本。
    - 匿名 `?` 维度保持 `?`，不生成类型级占位符。

    使用示例:
    - dims = _source_shape_values_for_transpose(source)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    owner = source.owner
    if isinstance(owner, DmaReshapeOp) and owner.result is source:
        return [
            _shape_value_from_symbol_operand(SSAValue.get(operand), axis)
            for axis, operand in enumerate(owner.shape)
        ]
    if not isinstance(source.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "transpose value must lower to nn.memory")
    shape_values: list[int | str] = []
    for dim in source.type.shape.data:
        dim_text = _symbol_expr_text(dim)
        shape_values.append(dim_text)
    return shape_values


def _is_singleton_dim(dim: Attribute) -> bool:
    """判断 shape attr 是否为静态 singleton 维度。

    创建者: 榕
    最后一次更改: 2026-05-02

    功能说明:
    - 服务当前文件内 NN compare 节点的隐式 broadcast emit。

    使用示例:
    - _is_singleton_dim(SymbolExprAttr.from_expr("1"))
    """

    return isinstance(dim, SymbolExprAttr) and _static_int_from_symbol_expr(dim) == 1


def _matmul_contract_dims_match(lhs_dim: Attribute, rhs_dim: Attribute) -> bool:
    """判断 matmul contracting 维度是否可兼容。

    功能说明:
    - 静态、命名符号与结构化符号表达都必须完全一致。
    - 匿名 `?` 不能证明相等，避免放行不确定 contracting 维度。

    使用示例:
    - ok = _matmul_contract_dims_match(lhs_dim, rhs_dim)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    lhs_unknown = isinstance(lhs_dim, SymbolExprAttr) and _symbol_expr_text(lhs_dim) == "?"
    rhs_unknown = isinstance(rhs_dim, SymbolExprAttr) and _symbol_expr_text(rhs_dim) == "?"
    if lhs_unknown or rhs_unknown:
        return False
    return lhs_dim == rhs_dim


def _shape_attr_from_value(value: int | str | SymbolDim) -> SymbolExprAttr:
    """把公开 shape 值转换为 memory type 维度 attr。

    功能说明:
    - 静态整数、符号与表达式均转换为 `SymbolExprAttr`。

    使用示例:
    - attr = _shape_attr_from_value("conv_kernel_flat")

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    return _symbol_expr_attr_from_value(value)


def _semantic_dim_value(label: str, fallback: int | SymbolDim) -> int | str:
    """为匿名维度选择稳定的语义类型名。

    功能说明:
    - 静态整数与已命名符号维度保持原值，避免改变可证明的 shape。
    - 匿名 `?` 维度改写为调用点提供的语义标签。

    使用示例:
    - dim = _semantic_dim_value("conv_kernel_flat", SymbolDim("?"))

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    if isinstance(fallback, int):
        return fallback
    public_value = fallback.get_value()
    if isinstance(public_value, int):
        return public_value
    text = str(public_value)
    if text == "?":
        return label
    return text


def _memory_type_from_shape_values(
    ctx: Context,
    memory: Memory,
    shape_values: list[int | str | SymbolDim],
    location: SourceLocation | None,
) -> NnMemoryType:
    """按指定 shape 值构造连续布局 memory type。

    功能说明:
    - dtype 与 memory space 仍复用 `MemoryAST.type_from_memory(...)` 的公开映射。
    - shape 使用调用方给出的语义维度，stride 在当前文件内按连续布局重建。

    使用示例:
    - result_type = _memory_type_from_shape_values(ctx, memory, ["M", "N"], location)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    base_type = MemoryAST.type_from_memory(ctx, memory, location)
    shape_attrs = [_shape_attr_from_value(value) for value in shape_values]
    return NnMemoryType(
        ArrayAttr(shape_attrs),
        _contiguous_stride_attrs(shape_attrs),
        base_type.element_type,
        base_type.space,
    )


def _memory_type_from_shape_attrs(
    ctx: Context,
    memory: Memory,
    shape_attrs: list[SymbolExprAttr],
    location: SourceLocation | None,
) -> NnMemoryType:
    """按现有 operand shape attr 构造连续布局 memory type。

    功能说明:
    - dtype 与 memory space 复用 `MemoryAST.type_from_memory(...)` 的公开映射。
    - shape 直接继承已发射 operand 的公开 memory type，避免匿名 runtime 维度在结果类型中重新编号。

    使用示例:
    - result_type = _memory_type_from_shape_attrs(ctx, memory, [lhs_dim, rhs_dim], location)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    base_type = MemoryAST.type_from_memory(ctx, memory, location)
    return NnMemoryType(
        ArrayAttr(shape_attrs),
        _contiguous_stride_attrs(shape_attrs),
        base_type.element_type,
        base_type.space,
    )


def _memory_type_from_shape_attrs_and_stride_values(
    ctx: Context,
    memory: Memory,
    shape_attrs: list[SymbolExprAttr],
    stride_values: list[int | str | SymbolDim],
    location: SourceLocation | None,
) -> NnMemoryType:
    """按现有 shape attr 与解析期 stride 值构造 memory type。


    功能说明:
    - shape 继承已发射 operand 的公开 memory type，保持 `?` / 命名符号不被重新编号。
    - stride 使用 operation 层公开 `Memory` 结果中的语义表达。

    使用示例:
    - result_type = _memory_type_from_shape_attrs_and_stride_values(ctx, memory, shape_attrs, [\"N\", 1], location)

    关联文件:
    - spec: spec/dsl/ast/nodes/nn.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/nn.py
    """

    base_type = MemoryAST.type_from_memory(ctx, memory, location)
    return NnMemoryType(
        ArrayAttr(shape_attrs),
        ArrayAttr(
            [
                _symbol_expr_attr_from_value(value)
                for value in stride_values
            ]
        ),
        base_type.element_type,
        base_type.space,
    )


def _contiguous_stride_attrs(shape_attrs: list[SymbolExprAttr]) -> ArrayAttr[SymbolExprAttr]:
    """根据 shape attr 生成连续 stride attr。

    创建者: 榕
    最后一次更改: 2026-05-02

    功能说明:
    - 服务当前文件内 NN 节点结果类型构造。
    - shape 维度为 `?` 时保留匿名表达。

    使用示例:
    - _contiguous_stride_attrs([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("8")])
    """

    stride_attrs: list[SymbolExprAttr] = []
    running: int | str = 1
    for axis, dim in reversed(list(enumerate(shape_attrs))):
        stride_attrs.insert(0, _symbol_expr_attr_from_value(running))
        dim_value = _static_int_from_symbol_expr(dim)
        if dim_value is None:
            dim_value = _symbol_expr_text(dim)
        if isinstance(dim_value, int) and isinstance(running, int):
            running = dim_value * running
        elif running == 1:
            running = dim_value
        else:
            running = _symbol_expr_product(dim_value, running)
    return ArrayAttr(stride_attrs)


def _emit_compare_with_broadcast_and_cast(
    op_name: str,
    op_type: type[NnEqOp] | type[NnNeOp] | type[NnLtOp] | type[NnLeOp] | type[NnGtOp] | type[NnGeOp],
    lhs: SSAValue,
    rhs: SSAValue,
    block: Block,
) -> Operation:
    """发射 NN compare，并补齐隐式 broadcast 与 dtype cast。

    创建者: 榕
    最后一次更改: 2026-05-02

    功能说明:
    - compare 系列共享同一套 MLIR 文本合同：先按尾维 broadcast，再在 dtype 不一致时把 lhs cast 到 rhs dtype，最后生成 compare op。

    使用示例:
    - _emit_compare_with_broadcast_and_cast("nn.eq", NnEqOp, lhs, rhs, block)
    """

    if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported {op_name} operands")

    lhs_value = lhs
    rhs_value = rhs
    lhs_type = lhs.type
    rhs_type = rhs.type
    lhs_shape = list(lhs_type.shape.data)
    rhs_shape = list(rhs_type.shape.data)
    target_shape_reversed: list[Attribute] = []
    max_rank = max(len(lhs_shape), len(rhs_shape))
    for index in range(1, max_rank + 1):
        lhs_dim = lhs_shape[-index] if index <= len(lhs_shape) else _symbol_expr_attr_from_value(1)
        rhs_dim = rhs_shape[-index] if index <= len(rhs_shape) else _symbol_expr_attr_from_value(1)
        if lhs_dim == rhs_dim:
            target_shape_reversed.append(lhs_dim)
        elif _is_singleton_dim(lhs_dim):
            target_shape_reversed.append(rhs_dim)
        elif _is_singleton_dim(rhs_dim):
            target_shape_reversed.append(lhs_dim)
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Implicit broadcast dimension mismatch")
    target_shape_attrs = list(reversed(target_shape_reversed))
    target_shape = ArrayAttr(target_shape_attrs)
    target_stride = _contiguous_stride_attrs(target_shape_attrs)

    if lhs_type.shape != target_shape:
        lhs_type = NnMemoryType(target_shape, target_stride, lhs_type.element_type, lhs_type.space)
        lhs_broadcast = NnBroadcastOp(lhs_value, lhs_type, lhs_type.space)
        block.add_op(lhs_broadcast)
        lhs_value = lhs_broadcast.results[0]
    if rhs_type.shape != target_shape:
        rhs_type = NnMemoryType(target_shape, target_stride, rhs_type.element_type, rhs_type.space)
        rhs_broadcast = NnBroadcastOp(rhs_value, rhs_type, rhs_type.space)
        block.add_op(rhs_broadcast)
        rhs_value = rhs_broadcast.results[0]
    if lhs_type.element_type != rhs_type.element_type:
        compare_dtypes: list[NumericType] = []
        for element_type in (lhs_type.element_type, rhs_type.element_type):
            dtype = None
            for attr_value, numeric_type in (
                (i1, NumericType.Bool),
                (i8, NumericType.Int8),
                (i32, NumericType.Int32),
                (i64, NumericType.Int64),
            ):
                if element_type == attr_value:
                    dtype = numeric_type
                    break
            if dtype is None and isinstance(element_type, IntegerType):
                width = element_type.width.data
                dtype = (
                    {
                        8: NumericType.Uint8,
                        16: NumericType.Uint16,
                        32: NumericType.Uint32,
                        64: NumericType.Uint64,
                    }
                    if element_type.signedness.data == Signedness.UNSIGNED
                    else {
                        8: NumericType.Int8,
                        16: NumericType.Int16,
                        32: NumericType.Int32,
                        64: NumericType.Int64,
                    }
                ).get(width)
            if dtype is None:
                for attr_type, numeric_type in (
                    (Float16Type, NumericType.Float16),
                    (BFloat16Type, NumericType.BFloat16),
                    (Float32Type, NumericType.Float32),
                    (Float64Type, NumericType.Float64),
                ):
                    if isinstance(element_type, attr_type):
                        dtype = numeric_type
                        break
            if dtype is None:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported compare dtype")
            compare_dtypes.append(dtype)
        lhs_dtype, rhs_dtype = compare_dtypes
        if lhs_dtype not in ARITHMETIC_DTYPE_RANK or rhs_dtype not in ARITHMETIC_DTYPE_RANK:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported compare dtype")
        if ARITHMETIC_DTYPE_RANK[lhs_dtype] >= ARITHMETIC_DTYPE_RANK[rhs_dtype]:
            rhs_type = NnMemoryType(rhs_type.shape, rhs_type.stride, lhs_type.element_type, rhs_type.space)
            rhs_cast = NnCastOp(rhs_value, rhs_type, rhs_type.space)
            block.add_op(rhs_cast)
            rhs_value = rhs_cast.results[0]
        else:
            lhs_type = NnMemoryType(lhs_type.shape, lhs_type.stride, rhs_type.element_type, lhs_type.space)
            lhs_cast = NnCastOp(lhs_value, lhs_type, lhs_type.space)
            block.add_op(lhs_cast)
            lhs_value = lhs_cast.results[0]
    return op_type(lhs_value, rhs_value, NnMemoryType(lhs_type.shape, lhs_type.stride, i1, lhs_type.space), lhs_type.space)


@dataclass
class Img2ColAST(ValueAST):
    """img2col 抽象分类节点。"""

    def result_memory(self) -> Memory | None:
        """返回 img2col 节点的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 从 source memory 与 img2col 参数节点自身读取结果语义。
        - parser 赋值绑定只消费该节点入口，不再在 visitor 中央反推 img2col 结果。

        使用示例:
        - memory = img2col_ast.result_memory()
        """

        source = self.source.result_memory()
        if not isinstance(source, Memory):
            return None
        if isinstance(self, NnImg2Col1dAST):
            values = [item.result_symbol() for item in (self.kw, self.sw, self.dw, self.pl, self.pr)]
            if any(value is None for value in values):
                return None
            return nn_ops.img2col1d(source, kw=values[0], sw=values[1], dw=values[2], pl=values[3], pr=values[4])
        if isinstance(self, NnImg2Col2dAST):
            values = [item.result_symbol() for item in (self.kh, self.kw, self.sh, self.sw, self.dh, self.dw, self.ph, self.pw, self.pl, self.pr)]
            if any(value is None for value in values):
                return None
            return nn_ops.img2col2d(
                source,
                kh=values[0],
                kw=values[1],
                sh=values[2],
                sw=values[3],
                dh=values[4],
                dw=values[5],
                ph=values[6],
                pw=values[7],
                pl=values[8],
                pr=values[9],
            )
        return None

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 img2col 节点发射为对应 NN op。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source_node = self.source
        source = source_node.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue) or not isinstance(source.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "img2col source must lower to nn.memory")
        source_memory = source_node.result_memory()
        if not isinstance(source_memory, Memory):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "img2col source result memory is unavailable")

        if isinstance(self, NnImg2Col1dAST):
            param_nodes = [self.kw, self.sw, self.dw, self.pl, self.pr]
        elif isinstance(self, NnImg2Col2dAST):
            param_nodes = [self.kh, self.kw, self.sh, self.sw, self.dh, self.dw, self.ph, self.pw, self.pl, self.pr]
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported img2col AST")
        params: list[int | SymbolDim] = []
        param_operands: list[SSAValue] = []
        for item in param_nodes:
            emitted = item.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                emitted_value = emitted.results[0]
            else:
                emitted_value = emitted
            if not isinstance(emitted_value, SSAValue) or not isinstance(emitted_value.type, SymbolValueType):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "img2col parameter must lower to symbol.int")
            value = _symbol_operand_public_value(emitted_value)
            params.append(value if isinstance(value, int) else SymbolDim(value))
            param_operands.append(emitted_value)

        if isinstance(self, NnImg2Col1dAST):
            result_memory = nn_ops.img2col1d(source_memory, kw=params[0], sw=params[1], dw=params[2], pl=params[3], pr=params[4])
        elif isinstance(self, NnImg2Col2dAST):
            result_memory = nn_ops.img2col2d(
                source_memory,
                kh=params[0],
                kw=params[1],
                sh=params[2],
                sw=params[3],
                dh=params[4],
                dw=params[5],
                ph=params[6],
                pw=params[7],
                pl=params[8],
                pr=params[9],
            )
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported img2col AST")

        source_shape_values = _shape_values_from_memory_type(source.type)
        if isinstance(self, NnImg2Col1dAST):
            if source_memory.format.name == "Norm":
                n_dim, c_dim, w_dim = source_shape_values
                out_w = _img2col_output_shape_value(w_dim, params[0], params[1], params[2], params[3], params[4])
                result_shape_values: list[int | str | SymbolDim] = [n_dim, c_dim, params[0], out_w]
            else:
                n_dim, w_dim, c_dim = source_shape_values
                out_w = _img2col_output_shape_value(w_dim, params[0], params[1], params[2], params[3], params[4])
                result_shape_values = [n_dim, out_w, params[0], c_dim]
        elif isinstance(self, NnImg2Col2dAST):
            if source_memory.format.name == "Norm":
                n_dim, c_dim, h_dim, w_dim = source_shape_values
                out_h = _img2col_output_shape_value(h_dim, params[0], params[2], params[4], params[6], params[7])
                out_w = _img2col_output_shape_value(w_dim, params[1], params[3], params[5], params[8], params[9])
                result_shape_values = [n_dim, c_dim, params[0], params[1], out_h, out_w]
            else:
                n_dim, h_dim, w_dim, c_dim = source_shape_values
                out_h = _img2col_output_shape_value(h_dim, params[0], params[2], params[4], params[6], params[7])
                out_w = _img2col_output_shape_value(w_dim, params[1], params[3], params[5], params[8], params[9])
                result_shape_values = [n_dim, out_h, out_w, params[0], params[1], c_dim]
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported img2col AST")

        result_type = _memory_type_from_shape_values(ctx, result_memory, result_shape_values, self.location)
        space_attr = result_type.space
        if isinstance(self, NnImg2Col1dAST):
            return NnImg2col1dOp(source, result_type, param_operands[0], param_operands[1], param_operands[2], param_operands[3], param_operands[4], space_attr)
        return NnImg2col2dOp(
            source,
            result_type,
            param_operands[0],
            param_operands[1],
            param_operands[2],
            param_operands[3],
            param_operands[4],
            param_operands[5],
            param_operands[6],
            param_operands[7],
            param_operands[8],
            param_operands[9],
            space_attr,
        )


@dataclass
class NnBroadcastAST(ValueAST):
    """nn.broadcast helper 节点。


    功能说明:
    - 表示 `broadcast(value, target)` 的 DSL helper 调用。
    - 保留输入与目标表达式，交由 lowering 阶段验证形状/类型。

    使用示例:
    - NnBroadcastAST(value=MemoryAST("x", ...), target=MemoryAST("y", ...))

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    value: ValueAST
    target: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)
        if not isinstance(self.target, ValueAST):
            self.target = ConstValueAST(self.target, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 broadcast 节点发射为 `nn.broadcast`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        target = self.target.emit_mlir(ctx, block)
        if isinstance(target, Operation):
            block.add_op(target)
            target = target.results[0]
        if not isinstance(value, SSAValue) or not isinstance(target, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "broadcast operands must lower to SSA values")
        if not isinstance(value.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "broadcast operands must be nn.memory")
        if not isinstance(self.value, MemoryAST) or not isinstance(self.target, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "broadcast operands must be tensor arguments")
        nn_ops.broadcast(self.value.memory, self.target.memory)
        return NnBroadcastOp(value, target.type, target.type.space)

@dataclass
class NnBroadcastToAST(ValueAST):
    """nn.broadcast_to helper 节点。


    功能说明:
    - 表示 `broadcast_to(source, target_shape, space)` 的 DSL helper 调用。
    - 记录源张量、目标 shape 表达式与 MemorySpace。

    使用示例:
    - NnBroadcastToAST(source=MemoryAST("x", ...), target_shape=[ConstValueAST(2)], space=MemorySpace.GM)

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    source: ValueAST
    target_shape: SymbolListAST
    space: MemorySpaceAttrAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ValueAST):
            self.source = ConstValueAST(self.source, location=self.location)
        if not isinstance(self.target_shape, SymbolListAST):
            self.target_shape = SymbolListAST(self.target_shape, self.location)
        if not isinstance(self.space, MemorySpaceAttrAST):
            self.space = MemorySpaceAttrAST(self.space, self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 broadcast_to 节点发射为 `nn.broadcast` 组合语义。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        source = self.source.emit_mlir(ctx, block)
        if isinstance(source, Operation):
            block.add_op(source)
            source = source.results[0]
        if not isinstance(source, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "broadcast_to source must lower to SSA value")
        if not isinstance(self.source, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "broadcast_to source must be tensor argument")
        shape_items = list(self.target_shape.items)
        target_shape_values: list[int | float | str | bool | SymbolDim] = []
        for item in shape_items:
            if isinstance(item, ConstValueAST):
                target_shape_values.append(item.raw_value)
            elif isinstance(item, MemoryAST):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "broadcast_to target shape item must be scalar")
            elif isinstance(item, ValueAST):
                emitted = item.emit_mlir(ctx, block)
                if isinstance(emitted, Operation):
                    block.add_op(emitted)
                    emitted_value = emitted.results[0]
                else:
                    emitted_value = emitted
                if not isinstance(emitted_value, SSAValue) or not isinstance(emitted_value.type, SymbolValueType):
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "broadcast_to target shape must lower to symbol.int")
                value = emitted_value.type.get_value()
                target_shape_values.append(value if isinstance(value, int) else SymbolDim(value))
        result_memory = nn_ops.broadcast_to(self.source.memory, target_shape_values, self.space.space)
        result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
        return NnBroadcastOp(source, result_type, result_type.space)

@dataclass
class NnTransposeAST(ValueAST):
    """nn.transpose helper 节点。


    功能说明:
    - 表示 `transpose(value, perm)` 的 DSL helper 调用。
    - 记录输入与 perm 表达式，交由 lowering 阶段校验。

    使用示例:
    - NnTransposeAST(value=MemoryAST("x", ...), perm=[ConstValueAST(1), ConstValueAST(0)])

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    value: ValueAST
    perm: SymbolListAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)
        if not isinstance(self.perm, SymbolListAST):
            self.perm = SymbolListAST(self.perm, self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 transpose 节点发射为 `nn.transpose`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "transpose value must lower to nn.memory")
        if not isinstance(self.value, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "transpose value must be tensor argument")
        perm_items = list(self.perm.items)
        perm_values: list[int] = []
        for item in perm_items:
            if isinstance(item, ConstValueAST):
                item = item.raw_value
            if not isinstance(item, int) or isinstance(item, bool):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "transpose perm must be static int list")
            perm_values.append(item)
        result_memory = nn_ops.transpose(self.value.memory, perm_values)
        result_shape = [value.type.shape.data[axis] for axis in perm_values]
        source_shape_values = _source_shape_values_for_transpose(value)
        result_stride = _contiguous_stride_values([source_shape_values[axis] for axis in perm_values])
        result_type = _memory_type_from_shape_attrs_and_stride_values(
            ctx,
            result_memory,
            result_shape,
            result_stride,
            self.location,
        )
        return NnTransposeOp(value, result_type, perm_values, result_type.space)

@dataclass
class NnReluAST(ValueAST):
    """relu helper 专用注册节点。"""

    value: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 `nn.relu`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "relu value must lower to nn.memory")
        if not isinstance(self.value, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "relu value must be tensor argument")
        nn_ops.relu(self.value.memory)
        return NnReluOp(value, value.type, value.type.space)


@dataclass
class NnSigmoidAST(ValueAST):
    """sigmoid helper 专用注册节点。"""

    value: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 `nn.sigmoid`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "sigmoid value must lower to nn.memory")
        if not isinstance(self.value, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "sigmoid value must be tensor argument")
        nn_ops.sigmoid(self.value.memory)
        return NnSigmoidOp(value, value.type, value.type.space)


@dataclass
class NnTanhAST(ValueAST):
    """tanh helper 专用注册节点。"""

    value: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 `nn.tanh`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "tanh value must lower to nn.memory")
        if not isinstance(self.value, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "tanh value must be tensor argument")
        nn_ops.tanh(self.value.memory)
        return NnTanhOp(value, value.type, value.type.space)


@dataclass
class NnLeakyReluAST(ValueAST):
    """leaky_relu helper 专用注册节点。"""

    value: ValueAST
    alpha: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)
        if not isinstance(self.alpha, ValueAST):
            self.alpha = ConstValueAST(self.alpha, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 `nn.leaky_relu`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "leaky_relu value must lower to nn.memory")
        if not isinstance(self.value, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "leaky_relu value must be tensor argument")
        alpha_value = self.alpha.raw_value if isinstance(self.alpha, ConstValueAST) else self.alpha
        nn_ops.leaky_relu(self.value.memory, alpha=alpha_value)
        alpha_op = arith.ConstantOp(FloatAttr(float(alpha_value), f32))
        block.add_op(alpha_op)
        return NnLeakyReluOp(value, alpha_op.results[0], value.type, value.type.space)


@dataclass
class NnHardSigmoidAST(ValueAST):
    """hard_sigmoid helper 专用注册节点。"""

    value: ValueAST
    alpha: ValueAST
    beta: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)
        if not isinstance(self.alpha, ValueAST):
            self.alpha = ConstValueAST(self.alpha, location=self.location)
        if not isinstance(self.beta, ValueAST):
            self.beta = ConstValueAST(self.beta, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 `nn.hard_sigmoid`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "hard_sigmoid value must lower to nn.memory")
        if not isinstance(self.value, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "hard_sigmoid value must be tensor argument")
        alpha_value = self.alpha.raw_value if isinstance(self.alpha, ConstValueAST) else self.alpha
        beta_value = self.beta.raw_value if isinstance(self.beta, ConstValueAST) else self.beta
        nn_ops.hard_sigmoid(self.value.memory, alpha=alpha_value, beta=beta_value)
        alpha_op = arith.ConstantOp(FloatAttr(float(alpha_value), f32))
        beta_op = arith.ConstantOp(FloatAttr(float(beta_value), f32))
        block.add_op(alpha_op)
        block.add_op(beta_op)
        return NnHardSigmoidOp(value, alpha_op.results[0], beta_op.results[0], value.type, value.type.space)


@dataclass
class NnExpAST(ValueAST):
    """exp helper 专用注册节点。"""

    value: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 `nn.exp`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "exp value must lower to nn.memory")
        if not isinstance(self.value, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "exp value must be tensor argument")
        nn_ops.exp(self.value.memory)
        return NnExpOp(value, value.type, value.type.space)

@dataclass
class NnReduceAST(ValueAST):
    """reduce helper 共享基类。"""

    value: ValueAST
    axis: ValueAST | None = None
    keepdim: ValueAST | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)
        if self.axis is not None and not isinstance(self.axis, ValueAST):
            self.axis = ConstValueAST(self.axis, location=self.location)
        if self.keepdim is not None and not isinstance(self.keepdim, ValueAST):
            self.keepdim = BoolValueAST(bool(self.keepdim), location=self.location)

    def reduce_name(self) -> str:
        """返回 reduce 节点的公开 op 名。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 子类覆盖该接口，供错误文本和 emit op 选择使用。

        使用示例:
        - name = reduce_ast.reduce_name()
        """

        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reduce_name must be implemented by concrete reduce AST")

    def axis_value(self) -> ReduceAxisValue:
        """返回 reduce axis 的公开语义值。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - const axis 返回 Python 值；其它公开 ValueAST 轴保持节点对象。

        使用示例:
        - axis = reduce_ast.axis_value()
        """

        return self.axis.raw_value if isinstance(self.axis, ConstValueAST) else self.axis

    def keepdim_value(self) -> ReduceKeepdimValue:
        """返回 reduce keepdim 的公开语义值。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 未传 keepdim 时返回 False；const/bool 节点返回 Python bool。

        使用示例:
        - keepdim = reduce_ast.keepdim_value()
        """

        keepdim_value = self.keepdim.raw_value if isinstance(self.keepdim, (ConstValueAST, BoolValueAST)) else self.keepdim
        return False if keepdim_value is None else keepdim_value

    def result_memory(self) -> Memory | None:
        """返回 reduce 节点的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - reduce 结果只从输入节点公开 `result_memory()` 和子类 operation 语义推导。

        使用示例:
        - memory = reduce_ast.result_memory()
        """

        source = self.value.result_memory()
        if not isinstance(source, Memory):
            return None
        try:
            return self.reduce_memory(source, self.axis_value(), self.keepdim_value())
        except ValueError as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, str(exc)) from exc

    def reduce_memory(self, value: Memory, axis: ReduceAxisValue, keepdim: ReduceKeepdimValue) -> Memory:
        """执行具体 reduce operation 的 memory 语义。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 子类覆盖该接口，并调用对应 `kernel_gen.operation.nn.reduce_*` 公开接口。

        使用示例:
        - memory = reduce_ast.reduce_memory(value, axis, keepdim)
        """

        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reduce_memory must be implemented by concrete reduce AST")

    def emit_reduce_op(self, value: SSAValue, result_type: NnMemoryType, axes: list[ReduceAxisElement], keepdim: ReduceKeepdimValue) -> Operation:
        """发射具体 reduce dialect op。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 子类覆盖该接口，并返回对应 `nn.reduce_*` operation。

        使用示例:
        - op = reduce_ast.emit_reduce_op(value, result_type, axes, keepdim)
        """

        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "emit_reduce_op must be implemented by concrete reduce AST")

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射具体 `nn.reduce_*` op。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"{self.reduce_name()} value must lower to nn.memory")
        result_memory = self.result_memory()
        if not isinstance(result_memory, Memory):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"{self.reduce_name()} result memory is unavailable")
        result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
        axis_value = self.axis_value()
        keepdim_value = self.keepdim_value()
        axes_value = list(axis_value) if isinstance(axis_value, (list, tuple)) else ([] if axis_value is None else [axis_value])
        return self.emit_reduce_op(value, result_type, axes_value, keepdim_value)


@dataclass
class NnReduceSumAST(NnReduceAST):
    """reduce_sum helper 专用注册节点。"""

    def reduce_name(self) -> str:
        """返回 reduce_sum 的公开 op 名。"""

        return "reduce_sum"

    def reduce_memory(self, value: Memory, axis: ReduceAxisValue, keepdim: ReduceKeepdimValue) -> Memory:
        """执行 reduce_sum 的 memory 语义。

        功能说明:
        - 调用公开 `kernel_gen.operation.nn.reduce_sum(...)`，按 axis / keepdim 推导输出 memory。

        使用示例:
        - memory = reduce_ast.reduce_memory(value, axis, keepdim)
        """

        return nn_ops.reduce_sum(value, axis=axis, keepdim=keepdim)

    def emit_reduce_op(self, value: SSAValue, result_type: NnMemoryType, axes: list[ReduceAxisElement], keepdim: ReduceKeepdimValue) -> Operation:
        """发射 `nn.reduce_sum`。

        功能说明:
        - 构造 `nn.reduce_sum` dialect op，使用已推导的 result_type、axes 与 keepdim。

        使用示例:
        - op = reduce_ast.emit_reduce_op(value, result_type, axes, keepdim)
        """

        return NnReduceSumOp(value, result_type, axes, keepdim, value.type.space)


@dataclass
class NnReduceMinAST(NnReduceAST):
    """reduce_min helper 专用注册节点。"""

    def reduce_name(self) -> str:
        """返回 reduce_min 的公开 op 名。"""

        return "reduce_min"

    def reduce_memory(self, value: Memory, axis: ReduceAxisValue, keepdim: ReduceKeepdimValue) -> Memory:
        """执行 reduce_min 的 memory 语义。

        功能说明:
        - 调用公开 `kernel_gen.operation.nn.reduce_min(...)`，按 axis / keepdim 推导输出 memory。

        使用示例:
        - memory = reduce_ast.reduce_memory(value, axis, keepdim)
        """

        return nn_ops.reduce_min(value, axis=axis, keepdim=keepdim)

    def emit_reduce_op(self, value: SSAValue, result_type: NnMemoryType, axes: list[ReduceAxisElement], keepdim: ReduceKeepdimValue) -> Operation:
        """发射 `nn.reduce_min`。

        功能说明:
        - 构造 `nn.reduce_min` dialect op，使用已推导的 result_type、axes 与 keepdim。

        使用示例:
        - op = reduce_ast.emit_reduce_op(value, result_type, axes, keepdim)
        """

        return NnReduceMinOp(value, result_type, axes, keepdim, value.type.space)


@dataclass
class NnReduceMaxAST(NnReduceAST):
    """reduce_max helper 专用注册节点。"""

    def reduce_name(self) -> str:
        """返回 reduce_max 的公开 op 名。"""

        return "reduce_max"

    def reduce_memory(self, value: Memory, axis: ReduceAxisValue, keepdim: ReduceKeepdimValue) -> Memory:
        """执行 reduce_max 的 memory 语义。

        功能说明:
        - 调用公开 `kernel_gen.operation.nn.reduce_max(...)`，按 axis / keepdim 推导输出 memory。

        使用示例:
        - memory = reduce_ast.reduce_memory(value, axis, keepdim)
        """

        return nn_ops.reduce_max(value, axis=axis, keepdim=keepdim)

    def emit_reduce_op(self, value: SSAValue, result_type: NnMemoryType, axes: list[ReduceAxisElement], keepdim: ReduceKeepdimValue) -> Operation:
        """发射 `nn.reduce_max`。

        功能说明:
        - 构造 `nn.reduce_max` dialect op，使用已推导的 result_type、axes 与 keepdim。

        使用示例:
        - op = reduce_ast.emit_reduce_op(value, result_type, axes, keepdim)
        """

        return NnReduceMaxOp(value, result_type, axes, keepdim, value.type.space)

@dataclass
class NnSoftmaxAST(ValueAST):
    """nn.softmax helper 节点。


    功能说明:
    - 表示 `softmax(value, axis=...)` 的 DSL helper 调用。
    - 记录输入与 axis 表达式，交由 lowering 阶段解析 axis。

    使用示例:
    - NnSoftmaxAST(value=MemoryAST("x", ...), axis=ConstValueAST(1))

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/nodes/test_nn.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    value: ValueAST
    axis: ValueAST | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)
        if self.axis is not None and not isinstance(self.axis, ValueAST):
            self.axis = ConstValueAST(self.axis, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 softmax 节点发射为 `nn.softmax`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        if not isinstance(value, SSAValue) or not isinstance(value.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "softmax value must lower to nn.memory")
        axis_value = self.axis.raw_value if isinstance(self.axis, ConstValueAST) else self.axis
        if axis_value is None:
            axis_value = -1
        if not isinstance(axis_value, int) or isinstance(axis_value, bool):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "softmax axis must be int")
        if isinstance(self.value, MemoryAST):
            nn_ops.softmax(self.value.memory, axis=axis_value)
        rank = len(value.type.shape.data)
        if axis_value < -rank or axis_value >= rank:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "softmax axis out of range")
        if axis_value < 0:
            axis_value += rank
        return NnSoftmaxOp(value, value.type, axis_value, value.type.space)

@dataclass
class MatmulAST(ValueAST):
    """matmul helper 节点。


    功能说明:
    - 表示 `matmul(lhs, rhs, memoryspace=...)` 的 DSL helper 调用。
    - 保留左右操作数与可选 memoryspace，供 raw `func.func` lowering 直接生成 `nn.matmul`。

    使用示例:
    - MatmulAST(lhs=MemoryAST("lhs", ...), rhs=MemoryAST("rhs", ...), memoryspace=MemorySpace.GM)

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    lhs: ValueAST
    rhs: ValueAST
    memoryspace: MemorySpaceAttrAST | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.lhs, ValueAST):
            self.lhs = ConstValueAST(self.lhs, location=self.location)
        if not isinstance(self.rhs, ValueAST):
            self.rhs = ConstValueAST(self.rhs, location=self.location)
        if self.memoryspace is not None and not isinstance(self.memoryspace, MemorySpaceAttrAST):
            self.memoryspace = MemorySpaceAttrAST(self.memoryspace, self.location)

    def result_memory(self) -> Memory | None:
        """返回 matmul 节点的解析期 memory 结果。

        创建者: 榕
        最后一次更改: 2026-05-03

        功能说明:
        - 从 lhs/rhs 节点读取 memory 语义，并按可选 memoryspace 生成 matmul 结果。

        使用示例:
        - memory = matmul_ast.result_memory()
        """

        lhs = self.lhs.result_memory()
        rhs = self.rhs.result_memory()
        if not isinstance(lhs, Memory) or not isinstance(rhs, Memory):
            return None
        memoryspace = self.memoryspace.space if self.memoryspace is not None else None
        return nn_ops.matmul(lhs, rhs, memoryspace)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 matmul 节点发射为 `nn.matmul`。"""

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
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "matmul operands must lower to SSA values")
        if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "matmul operands must be nn.memory")
        lhs_shape = lhs.type.shape.data
        rhs_shape = rhs.type.shape.data
        if len(lhs_shape) != 2 or len(rhs_shape) != 2:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "matmul operands must be rank-2 Memory")
        if not _matmul_contract_dims_match(lhs_shape[1], rhs_shape[0]):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "matmul contracting dimension mismatch")
        if lhs.type.space.space.data != rhs.type.space.space.data:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "matmul space mismatch")
        if lhs.type.element_type != rhs.type.element_type:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "matmul operand/result element_type must match")
        result_memory = self.result_memory()
        if result_memory is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "matmul result memory is unavailable")
        result_type = _memory_type_from_shape_attrs(ctx, result_memory, [lhs_shape[0], rhs_shape[1]], self.location)
        return NnMatmulOp(lhs, rhs, result_type, result_type.space)

@dataclass
class FCAST(ValueAST):
    """fc helper 节点。


    功能说明:
    - 表示 `fc(value, weight)` 的 DSL helper 调用。
    - 保留输入与权重，用于 lowering 阶段生成 `nn.transpose + nn.matmul`。

    使用示例:
    - FCAST(value=MemoryAST("x", ...), weight=MemoryAST("w", ...))

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    value: ValueAST
    weight: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)
        if not isinstance(self.weight, ValueAST):
            self.weight = ConstValueAST(self.weight, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 fc 节点发射为组合 NN op。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        weight = self.weight.emit_mlir(ctx, block)
        if isinstance(weight, Operation):
            block.add_op(weight)
            weight = weight.results[0]
        if not isinstance(value, SSAValue) or not isinstance(weight, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "fc operands must lower to SSA values")
        if not isinstance(self.value, MemoryAST) or not isinstance(self.weight, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "fc operands must be tensor arguments")

        transpose_op = NnTransposeAST(self.weight, [ConstValueAST(1), ConstValueAST(0)], location=self.location).emit_mlir(ctx, block)
        if not isinstance(transpose_op, Operation):
            raise KernelCodeError(ErrorKind.INTERNAL, ErrorModule.MLIR_GEN, "fc transpose must emit operation")
        block.add_op(transpose_op)
        transpose_value = transpose_op.results[0]
        transpose_memory = nn_ops.transpose(self.weight.memory, [1, 0])
        try:
            result_memory = nn_ops.matmul(self.value.memory, transpose_memory)
        except KernelCodeError:
            raise
        except ValueError as exc:
            raise VerifyException("nn.matmul contracting dimensions must match") from exc
        result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
        return NnMatmulOp(value, transpose_value, result_type, result_type.space)

@dataclass
class ConvAST(ValueAST):
    """conv helper 节点。


    功能说明:
    - 表示 `conv(value, weight, stride=..., padding=..., dilation=..., groups=...)` 的 DSL helper 调用。
    - 当前仅承接前端分解路径，供 lowering 阶段展开为 `nn.img2col2d + dma.reshape + nn.matmul + dma.reshape`。

    使用示例:
    - ConvAST(value, weight, SymbolListAST([1, 1]), SymbolListAST([0, 0, 0, 0]), SymbolListAST([1, 1]))

    关联文件:
    - spec: spec/dsl/ast/mlir_gen.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    value: ValueAST
    weight: ValueAST
    stride: SymbolListAST
    padding: SymbolListAST
    dilation: SymbolListAST
    groups: ValueAST | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, ValueAST):
            self.value = ConstValueAST(self.value, location=self.location)
        if not isinstance(self.weight, ValueAST):
            self.weight = ConstValueAST(self.weight, location=self.location)
        if not isinstance(self.stride, SymbolListAST):
            self.stride = SymbolListAST(self.stride, self.location)
        if not isinstance(self.padding, SymbolListAST):
            self.padding = SymbolListAST(self.padding, self.location)
        if not isinstance(self.dilation, SymbolListAST):
            self.dilation = SymbolListAST(self.dilation, self.location)
        if self.groups is not None and not isinstance(self.groups, ValueAST):
            self.groups = ConstValueAST(self.groups, location=self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 conv 节点发射为组合 NN op。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        value = self.value.emit_mlir(ctx, block)
        if isinstance(value, Operation):
            block.add_op(value)
            value = value.results[0]
        weight = self.weight.emit_mlir(ctx, block)
        if isinstance(weight, Operation):
            block.add_op(weight)
            weight = weight.results[0]
        if not isinstance(value, SSAValue) or not isinstance(weight, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "conv operands must lower to SSA values")
        if not isinstance(value.type, NnMemoryType) or not isinstance(weight.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "conv operands must be nn.memory")
        if not isinstance(self.value, MemoryAST) or not isinstance(self.weight, MemoryAST):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "conv operands must be tensor arguments")

        weight_dims = self.weight.memory.get_shape()
        param_operands: dict[str, SSAValue] = {}
        param_values: dict[str, int | SymbolDim] = {}
        for name, axis in (("kh", 2), ("kw", 3)):
            dim = weight_dims[axis]
            if isinstance(dim, int):
                dim_op = SymbolConstOp(dim)
            else:
                dim_op = SymbolGetDimOp(weight, axis)
            block.add_op(dim_op)
            dim_value = dim_op.results[0]
            param_operands[name] = dim_value
            dim_public = dim_value.type.get_value()
            param_values[name] = dim_public if isinstance(dim_public, int) else SymbolDim(dim_public)
        if len(self.stride.items) != 2 or len(self.dilation.items) != 2 or len(self.padding.items) != 4:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "conv stride/dilation/padding rank mismatch")
        conv_params = {
            "sh": self.stride.items[0],
            "sw": self.stride.items[1],
            "dh": self.dilation.items[0],
            "dw": self.dilation.items[1],
            "ph": self.padding.items[0],
            "pw": self.padding.items[1],
            "pl": self.padding.items[2],
            "pr": self.padding.items[3],
        }
        for name in ("sh", "sw", "dh", "dw", "ph", "pw", "pl", "pr"):
            item = conv_params[name]
            emitted = item.emit_mlir(ctx, block)
            if isinstance(emitted, Operation):
                block.add_op(emitted)
                emitted = emitted.results[0]
            if not isinstance(emitted, SSAValue) or not isinstance(emitted.type, SymbolValueType):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "conv parameter must lower to symbol.int")
            param_operands[name] = emitted
            param_public = _symbol_operand_public_value(emitted)
            param_values[name] = param_public if isinstance(param_public, int) else SymbolDim(param_public)

        conv_result_memory = nn_ops.conv(
            self.value.memory,
            self.weight.memory,
            sh=param_values["sh"],
            sw=param_values["sw"],
            dh=param_values["dh"],
            dw=param_values["dw"],
            ph=param_values["ph"],
            pw=param_values["pw"],
            pl=param_values["pl"],
            pr=param_values["pr"],
        )
        img2col_memory = nn_ops.img2col2d(
            self.value.memory,
            kh=param_values["kh"],
            kw=param_values["kw"],
            sh=param_values["sh"],
            sw=param_values["sw"],
            dh=param_values["dh"],
            dw=param_values["dw"],
            ph=param_values["ph"],
            pw=param_values["pw"],
            pl=param_values["pl"],
            pr=param_values["pr"],
        )
        source_shape_values = _shape_values_from_memory_type(value.type)
        if self.value.memory.format.name == "Norm":
            n_dim, c_dim, h_dim, w_dim = source_shape_values
            img_out_h = _img2col_output_shape_value(
                h_dim,
                param_values["kh"],
                param_values["sh"],
                param_values["dh"],
                param_values["ph"],
                param_values["pw"],
            )
            img_out_w = _img2col_output_shape_value(
                w_dim,
                param_values["kw"],
                param_values["sw"],
                param_values["dw"],
                param_values["pl"],
                param_values["pr"],
            )
            img2col_shape_values: list[int | str | SymbolDim] = [
                n_dim,
                c_dim,
                param_values["kh"],
                param_values["kw"],
                img_out_h,
                img_out_w,
            ]
        else:
            n_dim, h_dim, w_dim, c_dim = source_shape_values
            img_out_h = _img2col_output_shape_value(
                h_dim,
                param_values["kh"],
                param_values["sh"],
                param_values["dh"],
                param_values["ph"],
                param_values["pw"],
            )
            img_out_w = _img2col_output_shape_value(
                w_dim,
                param_values["kw"],
                param_values["sw"],
                param_values["dw"],
                param_values["pl"],
                param_values["pr"],
            )
            img2col_shape_values = [
                n_dim,
                img_out_h,
                img_out_w,
                param_values["kh"],
                param_values["kw"],
                c_dim,
            ]
        img2col_type = _memory_type_from_shape_values(ctx, img2col_memory, img2col_shape_values, self.location)
        img2col_op = NnImg2col2dOp(
            value,
            img2col_type,
            param_operands["kh"],
            param_operands["kw"],
            param_operands["sh"],
            param_operands["sw"],
            param_operands["dh"],
            param_operands["dw"],
            param_operands["ph"],
            param_operands["pw"],
            param_operands["pl"],
            param_operands["pr"],
            value.type.space,
        )
        block.add_op(img2col_op)
        img2col_value = img2col_op.results[0]

        batch_op = SymbolGetDimOp(img2col_value, 0)
        out_h_op = SymbolGetDimOp(img2col_value, 4)
        out_w_op = SymbolGetDimOp(img2col_value, 5)
        block.add_op(batch_op)
        block.add_op(out_h_op)
        block.add_op(out_w_op)
        batch_value = batch_op.results[0].type.get_value()
        out_h_value = out_h_op.results[0].type.get_value()
        out_w_value = out_w_op.results[0].type.get_value()
        batch_shape_value: int | SymbolDim = batch_value if isinstance(batch_value, int) else _symbol_dim_from_expr_text(batch_value)
        out_h_shape_value: int | SymbolDim = out_h_value if isinstance(out_h_value, int) else _symbol_dim_from_expr_text(out_h_value)
        out_w_shape_value: int | SymbolDim = out_w_value if isinstance(out_w_value, int) else _symbol_dim_from_expr_text(out_w_value)

        c_out_dim = weight_dims[0]
        if isinstance(c_out_dim, int):
            c_out_weight_op = SymbolConstOp(c_out_dim)
        else:
            c_out_weight_op = SymbolGetDimOp(weight, 0)
        block.add_op(c_out_weight_op)
        c_out_weight_value = c_out_weight_op.results[0].type.get_value()
        c_out_shape_value: int | SymbolDim = c_out_weight_value if isinstance(c_out_weight_value, int) else SymbolDim(c_out_weight_value)

        c_in_dim = weight_dims[1]
        kernel_factor_values: list[int | SymbolDim] = [
            c_in_dim if isinstance(c_in_dim, int) else SymbolDim(c_in_dim.get_value() if isinstance(c_in_dim, SymbolDim) else c_in_dim),
            param_values["kh"],
            param_values["kw"],
        ]
        kernel_flat_symbol = SymbolDim(kernel_factor_values[0]) * kernel_factor_values[1] * kernel_factor_values[2]
        kernel_flat_public = kernel_flat_symbol.get_value()
        kernel_flat_shape_value: int | SymbolDim = kernel_flat_public if isinstance(kernel_flat_public, int) else SymbolDim(kernel_flat_public)
        if isinstance(kernel_flat_public, int):
            kernel_flat_weight_op = SymbolConstOp(kernel_flat_public)
            block.add_op(kernel_flat_weight_op)
            kernel_flat_weight_value = kernel_flat_weight_op.results[0]
        else:
            if isinstance(c_in_dim, int):
                c_in_weight_op = SymbolConstOp(c_in_dim)
            else:
                c_in_weight_op = SymbolGetDimOp(weight, 1)
            block.add_op(c_in_weight_op)
            first_kernel_expr = _symbol_expr_text_from_value(SymbolDim(kernel_factor_values[0]) * kernel_factor_values[1])
            first_kernel_mul = SymbolMulOp(c_in_weight_op.results[0], param_operands["kh"], SymbolValueType.from_expr(first_kernel_expr))
            block.add_op(first_kernel_mul)
            second_kernel_expr = _symbol_expr_text_from_value(kernel_flat_public)
            second_kernel_mul = SymbolMulOp(first_kernel_mul.results[0], param_operands["kw"], SymbolValueType.from_expr(second_kernel_expr))
            block.add_op(second_kernel_mul)
            kernel_flat_weight_value = second_kernel_mul.results[0]
        weight_reshape_memory = dma_ops.reshape(self.weight.memory, [c_out_shape_value, kernel_flat_shape_value])
        c_out_type_dim = _semantic_dim_value("conv_c_out", c_out_shape_value)
        kernel_flat_type_dim = _semantic_dim_value("conv_kernel_flat", kernel_flat_shape_value)
        weight_reshape_type = _memory_type_from_shape_values(ctx, weight_reshape_memory, [c_out_type_dim, kernel_flat_type_dim], self.location)
        weight_reshape_op = DmaReshapeOp(weight, [c_out_weight_op.results[0], kernel_flat_weight_value], weight_reshape_type)
        block.add_op(weight_reshape_op)

        if isinstance(kernel_flat_public, int):
            kernel_flat_img_op = SymbolConstOp(kernel_flat_public)
            block.add_op(kernel_flat_img_op)
            kernel_flat_img_value = kernel_flat_img_op.results[0]
        else:
            if isinstance(c_in_dim, int):
                c_in_img_op = SymbolConstOp(c_in_dim)
            else:
                c_in_img_op = SymbolGetDimOp(weight, 1)
            block.add_op(c_in_img_op)
            first_img_kernel_expr = _symbol_expr_text_from_value(SymbolDim(kernel_factor_values[0]) * kernel_factor_values[1])
            first_img_kernel_mul = SymbolMulOp(c_in_img_op.results[0], param_operands["kh"], SymbolValueType.from_expr(first_img_kernel_expr))
            block.add_op(first_img_kernel_mul)
            second_img_kernel_expr = _symbol_expr_text_from_value(kernel_flat_public)
            second_img_kernel_mul = SymbolMulOp(first_img_kernel_mul.results[0], param_operands["kw"], SymbolValueType.from_expr(second_img_kernel_expr))
            block.add_op(second_img_kernel_mul)
            kernel_flat_img_value = second_img_kernel_mul.results[0]
        batch_h_symbol = SymbolDim(batch_shape_value) * out_h_shape_value
        batch_h_expr = _symbol_expr_text_from_value(batch_h_symbol)
        batch_h_mul = SymbolMulOp(batch_op.results[0], out_h_op.results[0], SymbolValueType.from_expr(batch_h_expr))
        block.add_op(batch_h_mul)
        batch_h_w_expr = _symbol_expr_text_from_value(batch_h_symbol * out_w_shape_value)
        batch_h_w_mul = SymbolMulOp(batch_h_mul.results[0], out_w_op.results[0], SymbolValueType.from_expr(batch_h_w_expr))
        block.add_op(batch_h_w_mul)
        batch_h_w_public = batch_h_w_mul.results[0].type.get_value()
        batch_h_w_shape_value: int | SymbolDim = batch_h_w_public if isinstance(batch_h_w_public, int) else _symbol_dim_from_expr_text(batch_h_w_public)
        img_reshape_memory = dma_ops.reshape(img2col_memory, [kernel_flat_shape_value, batch_h_w_shape_value])
        batch_h_w_type_dim = _semantic_dim_value("conv_batch_h_w", batch_h_w_shape_value)
        img_reshape_type = _memory_type_from_shape_values(ctx, img_reshape_memory, [kernel_flat_type_dim, batch_h_w_type_dim], self.location)
        img_reshape_op = DmaReshapeOp(img2col_value, [kernel_flat_img_value, batch_h_w_mul.results[0]], img_reshape_type)
        block.add_op(img_reshape_op)

        matmul_memory = nn_ops.matmul(weight_reshape_memory, img_reshape_memory)
        matmul_type = _memory_type_from_shape_values(ctx, matmul_memory, [c_out_type_dim, batch_h_w_type_dim], self.location)
        matmul_op = NnMatmulOp(weight_reshape_op.results[0], img_reshape_op.results[0], matmul_type, value.type.space)
        block.add_op(matmul_op)

        if isinstance(c_out_dim, int):
            c_out_final_op = SymbolConstOp(c_out_dim)
        else:
            c_out_final_op = SymbolGetDimOp(weight, 0)
        block.add_op(c_out_final_op)
        result_type = MemoryAST.type_from_memory(ctx, conv_result_memory, self.location)
        return DmaReshapeOp(
            matmul_op.results[0],
            [batch_op.results[0], c_out_final_op.results[0], out_h_op.results[0], out_w_op.results[0]],
            result_type,
        )


@dataclass(init=False)
class NnImg2Col1dAST(Img2ColAST):
    """img2col1d helper 专用注册节点。"""

    source: ValueAST
    kw: ValueAST
    sw: ValueAST
    dw: ValueAST
    pl: ValueAST
    pr: ValueAST
    location: SourceLocation | None = None

    def __init__(
        self,
        source: ValueAST,
        kw: ValueAST,
        sw: ValueAST | None = None,
        dw: ValueAST | None = None,
        pl: ValueAST | None = None,
        pr: ValueAST | None = None,
        location: SourceLocation | None = None,
    ) -> None:
        args = [source, kw, sw if sw is not None else ConstValueAST(1), dw if dw is not None else ConstValueAST(1), pl if pl is not None else ConstValueAST(0), pr if pr is not None else ConstValueAST(0)]
        self.source = args[0] if isinstance(args[0], ValueAST) else ConstValueAST(args[0], location=location)
        self.kw = args[1] if isinstance(args[1], ValueAST) else ConstValueAST(args[1], location=location)
        self.sw = args[2] if isinstance(args[2], ValueAST) else ConstValueAST(args[2], location=location)
        self.dw = args[3] if isinstance(args[3], ValueAST) else ConstValueAST(args[3], location=location)
        self.pl = args[4] if isinstance(args[4], ValueAST) else ConstValueAST(args[4], location=location)
        self.pr = args[5] if isinstance(args[5], ValueAST) else ConstValueAST(args[5], location=location)
        self.location = location


@dataclass(init=False)
class NnImg2Col2dAST(Img2ColAST):
    """img2col2d helper 专用注册节点。"""

    source: ValueAST
    kh: ValueAST
    kw: ValueAST
    sh: ValueAST
    sw: ValueAST
    dh: ValueAST
    dw: ValueAST
    ph: ValueAST
    pw: ValueAST
    pl: ValueAST
    pr: ValueAST
    location: SourceLocation | None = None

    def __init__(
        self,
        source: ValueAST,
        kh: ValueAST,
        kw: ValueAST,
        sh: ValueAST | None = None,
        sw: ValueAST | None = None,
        dh: ValueAST | None = None,
        dw: ValueAST | None = None,
        ph: ValueAST | None = None,
        pw: ValueAST | None = None,
        pl: ValueAST | None = None,
        pr: ValueAST | None = None,
        location: SourceLocation | None = None,
    ) -> None:
        args = [
            source,
            kh,
            kw,
            sh if sh is not None else ConstValueAST(1),
            sw if sw is not None else ConstValueAST(1),
            dh if dh is not None else ConstValueAST(1),
            dw if dw is not None else ConstValueAST(1),
            ph if ph is not None else ConstValueAST(0),
            pw if pw is not None else ConstValueAST(0),
            pl if pl is not None else ConstValueAST(0),
            pr if pr is not None else ConstValueAST(0),
        ]
        self.source = args[0] if isinstance(args[0], ValueAST) else ConstValueAST(args[0], location=location)
        self.kh = args[1] if isinstance(args[1], ValueAST) else ConstValueAST(args[1], location=location)
        self.kw = args[2] if isinstance(args[2], ValueAST) else ConstValueAST(args[2], location=location)
        self.sh = args[3] if isinstance(args[3], ValueAST) else ConstValueAST(args[3], location=location)
        self.sw = args[4] if isinstance(args[4], ValueAST) else ConstValueAST(args[4], location=location)
        self.dh = args[5] if isinstance(args[5], ValueAST) else ConstValueAST(args[5], location=location)
        self.dw = args[6] if isinstance(args[6], ValueAST) else ConstValueAST(args[6], location=location)
        self.ph = args[7] if isinstance(args[7], ValueAST) else ConstValueAST(args[7], location=location)
        self.pw = args[8] if isinstance(args[8], ValueAST) else ConstValueAST(args[8], location=location)
        self.pl = args[9] if isinstance(args[9], ValueAST) else ConstValueAST(args[9], location=location)
        self.pr = args[10] if isinstance(args[10], ValueAST) else ConstValueAST(args[10], location=location)
        self.location = location


@dataclass
class _BinaryNnAST(ValueAST):
    """element binary AST 的当前文件内共享实现。"""

    lhs: ValueAST
    rhs: ValueAST
    location: SourceLocation | None = None

    _op_name: ClassVar[str]
    _semantic_op: ClassVar[Callable[..., Memory]]
    _dialect_op: ClassVar[Callable[..., Operation]]

    def __post_init__(self) -> None:
        if not isinstance(self.lhs, ValueAST):
            self.lhs = ConstValueAST(self.lhs, location=self.location)
        if not isinstance(self.rhs, ValueAST):
            self.rhs = ConstValueAST(self.rhs, location=self.location)

    def result_memory(self) -> Memory | None:
        """返回 element binary 节点的解析期 memory 结果。

        功能说明:
        - 通过当前公开 operation 语义计算 memory 结果。
        - memory 与符号标量混合时保持现有结果 memory 形状。

        使用示例:
        - memory = binary_ast.result_memory()
        """

        lhs = self.lhs.result_memory() or self.lhs.result_symbol()
        rhs = self.rhs.result_memory() or self.rhs.result_symbol()
        if lhs is None or rhs is None:
            return None
        try:
            return type(self)._semantic_op(lhs, rhs)
        except KernelCodeError:
            if isinstance(lhs, Memory) and isinstance(rhs, SymbolDim):
                return lhs.clone()
            if isinstance(rhs, Memory) and isinstance(lhs, SymbolDim):
                return rhs.clone()
            raise

    def _cast_symbol_for_memory(self, symbol: SSAValue, memory_type: NnMemoryType, block: Block) -> SSAValue:
        """按 memory element type 将 symbol 标量转为可参与 NN binary 的值。

        功能说明:
        - 浮点 memory 使用 `symbol.to_float`。
        - 整数/布尔 memory 使用 `symbol.to_int`。

        使用示例:
        - scalar = self._cast_symbol_for_memory(symbol_value, memory_type, block)
        """

        if isinstance(memory_type.element_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
            scalar_cast = SymbolToFloatOp(symbol, memory_type.element_type)
        else:
            scalar_cast = SymbolToIntOp(symbol, memory_type.element_type)
        block.add_op(scalar_cast)
        return scalar_cast.results[0]

    def _emit_memory_symbol(self, ctx: Context, block: Block, memory: SSAValue, symbol: SSAValue) -> Operation:
        """发射 `memory op symbol` 形态的 element binary。

        功能说明:
        - 默认使用当前 memory 类型作为结果类型。
        - 特殊 op 可在子类覆盖该当前文件内 helper。

        使用示例:
        - op = self._emit_memory_symbol(ctx, block, lhs, rhs)
        """

        _ = ctx
        if not isinstance(memory.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported {self._op_name} operands")
        scalar = self._cast_symbol_for_memory(symbol, memory.type, block)
        return type(self)._dialect_op(memory, scalar, memory.type, memory.type.space)

    def _emit_symbol_memory(self, ctx: Context, block: Block, symbol: SSAValue, memory: SSAValue) -> Operation:
        """发射 `symbol op memory` 形态的 element binary。

        功能说明:
        - 默认使用当前 memory 类型作为结果类型。
        - 特殊 op 可在子类覆盖该当前文件内 helper。

        使用示例:
        - op = self._emit_symbol_memory(ctx, block, lhs, rhs)
        """

        _ = ctx
        if not isinstance(memory.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported {self._op_name} operands")
        scalar = self._cast_symbol_for_memory(symbol, memory.type, block)
        return type(self)._dialect_op(scalar, memory, memory.type, memory.type.space)

    def _emit_memory_memory(self, lhs: SSAValue, rhs: SSAValue) -> Operation:
        """发射 `memory op memory` 形态的 element binary。

        功能说明:
        - rank 与 shape 必须一致，否则按公开隐式 broadcast 错误失败。

        使用示例:
        - op = self._emit_memory_memory(lhs, rhs)
        """

        if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported {self._op_name} operands")
        if len(lhs.type.shape.data) != len(rhs.type.shape.data):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Implicit broadcast dimension mismatch")
        for lhs_dim, rhs_dim in zip(lhs.type.shape.data, rhs.type.shape.data, strict=True):
            if lhs_dim != rhs_dim:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Implicit broadcast dimension mismatch")
        return type(self)._dialect_op(lhs, rhs, lhs.type, lhs.type.space)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 element binary NN op。

        功能说明:
        - 只接受 memory/memory、memory/symbol、symbol/memory 三类公开 DSL 结果。
        - 其它输入按公开错误语义失败。

        使用示例:
        - op = binary_ast.emit_mlir(ctx, block)
        """

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
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"{self._op_name} operands must lower to SSA values")
        if isinstance(lhs.type, NnMemoryType) and isinstance(rhs.type, SymbolValueType):
            return self._emit_memory_symbol(ctx, block, lhs, rhs)
        if isinstance(rhs.type, NnMemoryType) and isinstance(lhs.type, SymbolValueType):
            return self._emit_symbol_memory(ctx, block, lhs, rhs)
        if isinstance(lhs.type, NnMemoryType) and isinstance(rhs.type, NnMemoryType):
            return self._emit_memory_memory(lhs, rhs)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported {self._op_name} operands")


@dataclass
class NnAddAST(_BinaryNnAST):
    """nn.add helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.add"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.add
    _dialect_op: ClassVar[Callable[..., Operation]] = NnAddOp


@dataclass
class NnSubAST(_BinaryNnAST):
    """nn.sub helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.sub"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.sub
    _dialect_op: ClassVar[Callable[..., Operation]] = NnSubOp


@dataclass
class NnMulAST(_BinaryNnAST):
    """nn.mul helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.mul"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.mul
    _dialect_op: ClassVar[Callable[..., Operation]] = NnMulOp


@dataclass
class NnTrueDivAST(_BinaryNnAST):
    """nn.truediv helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.truediv"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.truediv
    _dialect_op: ClassVar[Callable[..., Operation]] = NnTrueDivOp


@dataclass
class NnFloorDivAST(_BinaryNnAST):
    """nn.floordiv helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.floordiv"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.floordiv
    _dialect_op: ClassVar[Callable[..., Operation]] = NnFloorDivOp

    def _emit_memory_symbol(self, ctx: Context, block: Block, memory: SSAValue, symbol: SSAValue) -> Operation:
        """发射 `memory // symbol`，保留常量整除的公开 dtype 推导。

        功能说明:
        - `memory // const` 使用公开 operation 结果 dtype 构造结果类型。
        - 其它 `memory // symbol` 走共享 scalar cast 路径。

        使用示例:
        - op = self._emit_memory_symbol(ctx, block, lhs, rhs)
        """

        if not isinstance(memory.type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported nn.floordiv operands")
        if isinstance(self.lhs, MemoryAST) and isinstance(self.rhs, ConstValueAST):
            result_memory = nn_ops.floordiv(self.lhs.memory, self.rhs.raw_value)
            result_type = MemoryAST.type_from_memory(ctx, result_memory, self.location)
            element_type = result_type.element_type
            floordiv_type = NnMemoryType(memory.type.shape, memory.type.stride, element_type, memory.type.space)
            return NnFloorDivOp(memory, symbol, floordiv_type, memory.type.space)
        return super()._emit_memory_symbol(ctx, block, memory, symbol)


@dataclass
class _CompareNnAST(ValueAST):
    """compare AST 的当前文件内共享实现。"""

    lhs: ValueAST
    rhs: ValueAST
    location: SourceLocation | None = None

    _op_name: ClassVar[str]
    _semantic_op: ClassVar[Callable[..., Memory]]
    _dialect_op: ClassVar[type[NnEqOp] | type[NnNeOp] | type[NnLtOp] | type[NnLeOp] | type[NnGtOp] | type[NnGeOp]]

    def __post_init__(self) -> None:
        if not isinstance(self.lhs, ValueAST):
            self.lhs = ConstValueAST(self.lhs, location=self.location)
        if not isinstance(self.rhs, ValueAST):
            self.rhs = ConstValueAST(self.rhs, location=self.location)

    def result_memory(self) -> Memory | None:
        """返回 compare 节点的解析期 bool memory 结果。

        功能说明:
        - 优先使用公开 compare operation 语义。
        - mixed/broadcast 失败时按现有 AST 合同退化为 bool memory 形状推导。

        使用示例:
        - memory = compare_ast.result_memory()
        """

        lhs = self.lhs.result_memory() or self.lhs.result_symbol()
        rhs = self.rhs.result_memory() or self.rhs.result_symbol()
        if lhs is None or rhs is None:
            return None
        try:
            return type(self)._semantic_op(lhs, rhs)
        except KernelCodeError:
            if isinstance(lhs, Memory) and isinstance(rhs, Memory):
                try:
                    arithmetic_result = nn_ops.add(lhs, rhs)
                    if isinstance(arithmetic_result, Memory):
                        return arithmetic_result.clone(dtype=NumericType.Bool)
                except KernelCodeError:
                    return lhs.clone(dtype=NumericType.Bool)
            if isinstance(lhs, Memory):
                return lhs.clone(dtype=NumericType.Bool)
            if isinstance(rhs, Memory):
                return rhs.clone(dtype=NumericType.Bool)
            raise

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 compare NN op。

        功能说明:
        - memory/memory 通过当前文件内 compare broadcast/cast helper 发射。
        - 非 memory/memory 输入按公开错误语义失败。

        使用示例:
        - op = compare_ast.emit_mlir(ctx, block)
        """

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
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"{self._op_name} operands must lower to SSA values")
        if isinstance(lhs.type, NnMemoryType) and isinstance(rhs.type, NnMemoryType):
            return _emit_compare_with_broadcast_and_cast(self._op_name, type(self)._dialect_op, lhs, rhs, block)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported {self._op_name} operands")


@dataclass
class NnEqAST(_CompareNnAST):
    """nn.eq helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.eq"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.eq
    _dialect_op: ClassVar[type[NnEqOp]] = NnEqOp


@dataclass
class NnNeAST(_CompareNnAST):
    """nn.ne helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.ne"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.ne
    _dialect_op: ClassVar[type[NnNeOp]] = NnNeOp


@dataclass
class NnLtAST(_CompareNnAST):
    """nn.lt helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.lt"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.lt
    _dialect_op: ClassVar[type[NnLtOp]] = NnLtOp


@dataclass
class NnLeAST(_CompareNnAST):
    """nn.le helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.le"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.le
    _dialect_op: ClassVar[type[NnLeOp]] = NnLeOp


@dataclass
class NnGtAST(_CompareNnAST):
    """nn.gt helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.gt"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.gt
    _dialect_op: ClassVar[type[NnGtOp]] = NnGtOp


@dataclass
class NnGeAST(_CompareNnAST):
    """nn.ge helper 专用注册节点。"""

    _op_name: ClassVar[str] = "nn.ge"
    _semantic_op: ClassVar[Callable[..., Memory]] = nn_ops.ge
    _dialect_op: ClassVar[type[NnGeOp]] = NnGeOp
