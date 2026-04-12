"""nn -> kernel lowering pass.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 将 nn dialect 的逐元素 op lower 为 kernel dialect op。
- 当结果无法复用已有输出时，为结果插入 dma.alloc。
- `nn.softmax` lower 为 `kernel.softmax` 并保留 `axis`。

使用示例:
- from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
- module = LowerNnToKernelPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_to_kernel.md
- test: test/pass/test_lowering_nn_to_kernel.py
- 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
"""

from __future__ import annotations

from collections.abc import Iterable

from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    IntAttr,
    IntegerAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    UnrealizedConversionCastOp,
    i32,
    i64,
)
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.irdl import IRDLOperation, irdl_op_definition, operand_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCopyOp, DmaFillOp, DmaTransposeOp
from kernel_gen.dialect.kernel import (
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceMinOp,
    KernelReduceOp,
    KernelSelectOp,
    KernelSoftmaxOp,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolFloorDivOp,
    SymbolGetDimOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
)
from ..pass_manager import Pass


@irdl_op_definition
class _DmaCastOutOp(IRDLOperation):
    """dma.cast（out 参数风格）。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 通过 out + source 形式表达 cast，匹配 lowering expectation 的输出格式。
    - 仅用于 nn_to_kernel lowering 内部构造与校验。

    使用示例:
    - _DmaCastOutOp(out, source)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "dma.cast"

    out = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)

    def __init__(self, out: SSAValue | Operation, source: SSAValue | Operation) -> None:
        super().__init__(operands=[out, source])

    def verify_(self) -> None:
        out_type = self.out.type
        source_type = self.source.type
        if not isinstance(out_type, NnMemoryType):
            raise VerifyException("dma.cast output must be nn.memory")
        if not isinstance(source_type, NnMemoryType):
            raise VerifyException("dma.cast source must be nn.memory")
        out_type.verify()
        source_type.verify()
        if source_type.shape != out_type.shape:
            raise VerifyException("dma.cast shape mismatch")
        if source_type.stride != out_type.stride:
            raise VerifyException("dma.cast stride mismatch")
        if source_type.space.space.data != out_type.space.space.data:
            raise VerifyException("dma.cast space mismatch")


class LowerNnToKernelError(ValueError):
    """nn -> kernel lowering 过程的显式错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于在 lowering 阶段中断执行并返回明确错误信息。

    使用示例:
    - raise LowerNnToKernelError("Unsupported nn op")

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """


_SUPPORTED_BINARY_KINDS = {
    "nn.add": "add",
    "nn.sub": "sub",
    "nn.mul": "mul",
    "nn.div": "div",
    "nn.truediv": "div",
    "nn.eq": "eq",
    "nn.ne": "ne",
    "nn.lt": "lt",
    "nn.le": "le",
    "nn.gt": "gt",
    "nn.ge": "ge",
}

_RESULT_TYPED_ALLOC_OPS = {"nn.matmul", "nn.img2col1d", "nn.img2col2d"}
_REDUCE_KIND_MAP = {
    "nn.reduce_sum": "sum",
    "nn.reduce_min": "min",
    "nn.reduce_max": "max",
}



def _ensure_space_attr(op: Operation) -> NnMemorySpaceAttr:
    """获取并校验 nn op 的 space attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确认 op.attributes["space"] 为 NnMemorySpaceAttr。

    使用示例:
    - space = _ensure_space_attr(op)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    space = op.attributes.get("space")
    if not isinstance(space, NnMemorySpaceAttr):
        raise LowerNnToKernelError("nn op must provide nn.space attribute")
    return space


def _ensure_single_result(op: Operation) -> NnMemoryType:
    """校验 nn op 仅有单个结果且类型为 nn.memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 要求结果数量为 1。
    - 要求结果类型为 NnMemoryType。

    使用示例:
    - result_type = _ensure_single_result(op)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if len(op.results) != 1:
        raise LowerNnToKernelError("nn op must have exactly one result")
    result_type = op.results[0].type
    if not isinstance(result_type, NnMemoryType):
        raise LowerNnToKernelError("nn op result must be nn.memory")
    return result_type


def _ensure_operand_count(op: Operation, expected: int) -> None:
    """校验 nn op 的 operand 数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - operand 数量不匹配时直接抛错。

    使用示例:
    - _ensure_operand_count(op, 2)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if len(op.operands) != expected:
        raise LowerNnToKernelError(
            f"nn op {op.name} expects {expected} operands, got {len(op.operands)}"
        )


def _parse_transpose_perm_attr(attr: object, rank: int) -> ArrayAttr:
    """解析 nn.transpose 的 perm attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 perm 为 ArrayAttr。
    - 校验 perm 为 0..rank-1 的排列。

    使用示例:
    - perm_attr = _parse_transpose_perm_attr(op.attributes["perm"], rank=2)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if not isinstance(attr, ArrayAttr):
        raise LowerNnToKernelError("nn.transpose perm must be ArrayAttr")
    perm_values: list[int] = []
    for entry in attr.data:
        if isinstance(entry, IntAttr):
            perm_values.append(entry.data)
            continue
        if isinstance(entry, IntegerAttr) and isinstance(entry.value, IntAttr):
            perm_values.append(entry.value.data)
            continue
        raise LowerNnToKernelError("nn.transpose perm must be a permutation of 0..rank-1")
    if len(perm_values) != rank or sorted(perm_values) != list(range(rank)):
        raise LowerNnToKernelError("nn.transpose perm must be a permutation of 0..rank-1")
    return attr


def _parse_softmax_axis_attr(attr: object) -> IntegerAttr:
    """解析 nn.softmax 的 axis attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 接收 IntegerAttr 或 IntAttr，并规整为 i64 IntegerAttr。
    - 统一校验 axis 的 i64 类型约束。

    使用示例:
    - axis_attr = _parse_softmax_axis_attr(op.attributes.get("axis"))

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if isinstance(attr, IntegerAttr):
        axis_attr = attr
    elif isinstance(attr, IntAttr):
        axis_attr = IntegerAttr(attr.data, IntegerType(64))
    else:
        raise LowerNnToKernelError("nn.softmax axis must be i64 IntegerAttr")

    if not isinstance(axis_attr.type, IntegerType):
        raise LowerNnToKernelError("nn.softmax axis must be i64 IntegerAttr")
    width_attr = axis_attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 64:
        raise LowerNnToKernelError("nn.softmax axis must be i64 IntegerAttr")
    return axis_attr


def _parse_reduce_axis_attr(attr: object, op_name: str) -> IntegerAttr:
    """解析 nn.reduce_* 的 axes attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 axes 为 ArrayAttr 且仅包含单轴。
    - 统一输出 i64 IntegerAttr。

    使用示例:
    - axis_attr = _parse_reduce_axis_attr(op.attributes["axes"], "nn.reduce_min")

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if not isinstance(attr, ArrayAttr):
        raise LowerNnToKernelError(f"{op_name} axes must be ArrayAttr")
    if len(attr.data) != 1:
        raise LowerNnToKernelError(f"{op_name} axes must contain exactly one axis")
    entry = attr.data[0]
    if isinstance(entry, IntAttr):
        axis_attr = IntegerAttr(entry.data, IntegerType(64))
    elif isinstance(entry, IntegerAttr):
        axis_attr = entry
    else:
        raise LowerNnToKernelError(f"{op_name} axes must be i64 IntegerAttr")
    if not isinstance(axis_attr.type, IntegerType):
        raise LowerNnToKernelError(f"{op_name} axes must be i64 IntegerAttr")
    width_attr = axis_attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 64:
        raise LowerNnToKernelError(f"{op_name} axes must be i64 IntegerAttr")
    return axis_attr


def _parse_reduce_keepdim_attr(attr: object, op_name: str) -> IntegerAttr:
    """解析 nn.reduce_* 的 keepdim attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 keepdim 为 i1 IntegerAttr。

    使用示例:
    - keepdim_attr = _parse_reduce_keepdim_attr(op.attributes["keepdim"], "nn.reduce_min")

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if isinstance(attr, IntAttr):
        attr = IntegerAttr(attr.data, IntegerType(1))
    if not isinstance(attr, IntegerAttr):
        raise LowerNnToKernelError(f"{op_name} keepdim must be i1 IntegerAttr")
    if not isinstance(attr.type, IntegerType):
        raise LowerNnToKernelError(f"{op_name} keepdim must be i1 IntegerAttr")
    width_attr = attr.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 1:
        raise LowerNnToKernelError(f"{op_name} keepdim must be i1 IntegerAttr")
    raw_value = attr.value.data
    if raw_value in (0, 1):
        return IntegerAttr(raw_value, IntegerType(1))
    if raw_value == -1:
        return IntegerAttr(1, IntegerType(1))
    raise LowerNnToKernelError(f"{op_name} keepdim must be bool")


def _build_alloc_dynamic_shape(
    source: SSAValue,
    result_type: NnMemoryType,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 dma.alloc 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 通过 symbol.get_dim 读取结果 shape 对应的符号值。
    - 逐维生成 !symbol.int operands，确保长度与 rank 一致。

    使用示例:
    - ops, operands = _build_alloc_dynamic_shape(op.operands[0], result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if isinstance(dim, StringAttr) and dim.data == "?":
            raise LowerNnToKernelError("nn op result shape must not contain '?'")
        op = SymbolGetDimOp(source, IntAttr(axis))
        ops.append(op)
        operands.append(op.result)
    return ops, operands


def _const_symbol_value(expr: str, literal: int) -> tuple[list[Operation], SSAValue]:
    """构造 !symbol.int<"expr"> SSA value。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 先创建 i32 常量，再通过 UnrealizedConversionCastOp 转为 symbol.int。
    - expr 用于约束 symbol.int 的公开表达式。

    使用示例:
    - ops, value = _const_symbol_value("N", 0)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    const = arith.ConstantOp(IntegerAttr(literal, i32))
    cast = UnrealizedConversionCastOp(
        operands=[const.result], result_types=[SymbolValueType.from_expr(expr)]
    )
    return [const, cast], cast.results[0]


def _static_int_from_operand(operand: SSAValue) -> int | None:
    """尝试从 operand 中解析静态整数值。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 arith.constant / builtin.unrealized_conversion_cast 形式的静态整数。
    - 无法解析时返回 None，交由上层决定是否报错。

    使用示例:
    - value = _static_int_from_operand(op.operands[0])

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    owner = operand.owner
    if owner is None:
        return None
    owner_name = getattr(owner, "name", None)
    if owner_name == "arith.constant":
        value_attr = owner.attributes.get("value")
        if value_attr is None and hasattr(owner, "value"):
            value_attr = owner.value
        if isinstance(value_attr, IntegerAttr):
            return int(value_attr.value.data)
        if isinstance(value_attr, IntAttr):
            return int(value_attr.data)
        return None
    if owner_name == "builtin.unrealized_conversion_cast":
        if owner.operands:
            return _static_int_from_operand(owner.operands[0])
    return None


def _symbol_expr_text(value: SSAValue) -> str:
    """提取 symbol.int 表达式文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 `!symbol.int<"...">` 类型的 SSAValue。
    - 返回其表达式字符串，供构造 symbol 算术表达式。

    使用示例:
    - expr = _symbol_expr_text(symbol_value)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if not isinstance(value.type, SymbolValueType):
        raise LowerNnToKernelError("symbol expr must be !symbol.int")
    return value.type.expr.expr.data


def _wrap_symbol_expr(expr: str) -> str:
    """在必要时为表达式补括号。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当表达式包含空格且未被括号包裹时补上括号。
    - 保持已包裹表达式不变，避免重复括号。

    使用示例:
    - wrapped = _wrap_symbol_expr("W + PL")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/pass/nn_lowering/img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    trimmed = expr.strip()
    if trimmed.startswith("(") and trimmed.endswith(")"):
        return trimmed
    if " " in trimmed:
        return f"({trimmed})"
    return trimmed


def _symbol_binary_expr(lhs_expr: str, rhs_expr: str, operator: str) -> str:
    """构造二元 symbol 表达式字符串。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - `+/-` 使用空格分隔。
    - `*` 不加空格，必要时为 rhs 加括号。
    - `//` 使用空格分隔，并在 lhs 需要时加括号。

    使用示例:
    - expr = _symbol_binary_expr("W", "PL", "+")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if operator in {"+", "-"}:
        return f"{lhs_expr} {operator} {rhs_expr}"
    if operator == "*":
        return f"{lhs_expr}*{_wrap_symbol_expr(rhs_expr)}"
    if operator == "//":
        return f"{_wrap_symbol_expr(lhs_expr)} // {rhs_expr}"
    raise LowerNnToKernelError(f"unsupported symbol operator {operator}")


def _symbol_const_value(value: int) -> tuple[list[Operation], SSAValue]:
    """构造 symbol.const 常量 SSA。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 `symbol.const` 生成 `!symbol.int<"...">` 常量。
    - 返回可插入的 op 列表与结果 SSA value。

    使用示例:
    - ops, one = _symbol_const_value(1)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    op = SymbolConstOp(value)
    return [op], op.result


def _symbol_binary_op(
    op_cls: type[Operation],
    lhs: SSAValue,
    rhs: SSAValue,
    operator: str,
) -> tuple[list[Operation], SSAValue]:
    """构造二元 symbol 算术 op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 根据 lhs/rhs 的表达式生成目标 result 类型。
    - 返回可插入的 op 列表与结果 SSA。

    使用示例:
    - ops, value = _symbol_binary_op(SymbolAddOp, lhs, rhs, "+")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/pass/nn_lowering/img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    lhs_expr = _symbol_expr_text(lhs)
    rhs_expr = _symbol_expr_text(rhs)
    result_expr = _symbol_binary_expr(lhs_expr, rhs_expr, operator)
    op = op_cls(lhs, rhs, SymbolValueType.from_expr(result_expr))
    return [op], op.result


def _normalize_img2col_operand(
    op_name: str,
    param_name: str,
    operand: SSAValue,
) -> tuple[list[Operation], SSAValue, list[Operation]]:
    """将 img2col 参数 operand 归一为 symbol.int。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若 operand 已是 !symbol.int，则直接返回。
    - 若 operand 为静态整数常量，则插入 conversion cast 转为 !symbol.int<"value">。
    - 其他情况直接抛错，避免在 lowering 中引入不明确的符号表达式。

    使用示例:
    - ops, kw, drop_ops = _normalize_img2col_operand("nn.img2col1d", "kw", kw_value)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if isinstance(operand.type, SymbolValueType):
        owner = operand.owner
        if isinstance(owner, SymbolConstOp):
            new_ops, new_value = _symbol_const_value(owner.value.data)
            return new_ops, new_value, [owner]
        if owner is not None and getattr(owner, "name", None) == "symbol.const":
            value_attr = owner.attributes.get("value")
            if isinstance(value_attr, IntAttr):
                new_ops, new_value = _symbol_const_value(int(value_attr.data))
                return new_ops, new_value, [owner]
            if isinstance(value_attr, IntegerAttr):
                new_ops, new_value = _symbol_const_value(int(value_attr.value.data))
                return new_ops, new_value, [owner]
        return [], operand, []
    if isinstance(operand.type, IntegerType):
        static_value = _static_int_from_operand(operand)
        if static_value is None:
            raise LowerNnToKernelError(
                f"{op_name} {param_name} must be symbol.int or constant int"
            )
        cast = UnrealizedConversionCastOp(
            operands=[operand],
            result_types=[SymbolValueType.from_expr(str(static_value))],
        )
        return [cast], cast.results[0], []
    raise LowerNnToKernelError(f"{op_name} {param_name} must be symbol.int or constant int")


def _normalize_img2col_operands(
    op: Operation,
) -> tuple[list[Operation], list[SSAValue], list[Operation]]:
    """规范化 img2col 参数 operand 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一将 img2col 参数转换为 !symbol.int。
    - 返回可插入的 op 列表与标准化后的 operand 列表。

    使用示例:
    - ops, operands, drop_ops = _normalize_img2col_operands(op)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/nn_lowering/img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if op.name == "nn.img2col1d":
        param_names = ["kw", "sw", "dw", "pl", "pr"]
        _ensure_operand_count(op, 6)
    elif op.name == "nn.img2col2d":
        param_names = ["kh", "kw", "sh", "sw", "dh", "dw", "ph", "pw", "pl", "pr"]
        _ensure_operand_count(op, 11)
    else:
        raise LowerNnToKernelError(f"{op.name} is not an img2col op")

    input_value = SSAValue.get(op.operands[0])
    extra_ops: list[Operation] = []
    normalized_params: list[SSAValue] = []
    drop_ops: list[Operation] = []
    for param_name, operand in zip(param_names, op.operands[1:]):
        new_ops, value, stale_ops = _normalize_img2col_operand(
            op.name,
            param_name,
            SSAValue.get(operand),
        )
        extra_ops.extend(new_ops)
        normalized_params.append(value)
        drop_ops.extend(stale_ops)
    return extra_ops, [input_value, *normalized_params], drop_ops


def _img2col_operand_to_attr(
    op_name: str,
    param_name: str,
    operand: SSAValue,
    *,
    numeric_attr: str,
) -> Attribute:
    """将 img2col 参数 operand 转为 attr 形式。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 !symbol.int 转为 StringAttr 或数值 attr（用于输出 stride/dilation/pad）。
    - 支持静态整数，动态符号统一转为 StringAttr。
    - numeric_attr 控制静态数值的 attr 类型：`int` 或 `i64`。

    使用示例:
    - attr = _img2col_operand_to_attr("nn.img2col1d", "sw", sw_value, numeric_attr="int")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if isinstance(operand.type, SymbolValueType):
        expr = _symbol_expr_text(operand)
        if expr.lstrip("-").isdigit():
            literal = int(expr)
            if numeric_attr == "int":
                return IntAttr(literal)
            if numeric_attr == "i64":
                return IntegerAttr(literal, i64)
            raise LowerNnToKernelError(f"{op_name} {param_name} numeric attr kind not supported")
        return StringAttr(expr)
    if isinstance(operand.type, IntegerType):
        static_value = _static_int_from_operand(operand)
        if static_value is None:
            raise LowerNnToKernelError(f"{op_name} {param_name} must be constant int")
        if numeric_attr == "int":
            return IntAttr(static_value)
        if numeric_attr == "i64":
            return IntegerAttr(static_value, i64)
        raise LowerNnToKernelError(f"{op_name} {param_name} numeric attr kind not supported")
    raise LowerNnToKernelError(f"{op_name} {param_name} must be symbol.int or constant int")


def _build_img2col_attr_array(
    op_name: str,
    param_name: str,
    operands: list[SSAValue],
    *,
    numeric_attr: str,
) -> ArrayAttr:
    """将 img2col 参数列表转换为 ArrayAttr。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一将 stride/dilation/pad operand 列表转为 attribute 数组。
    - 静态数值按 numeric_attr 输出，动态符号输出为 StringAttr。

    使用示例:
    - stride_attr = _build_img2col_attr_array("nn.img2col1d", "stride", [sw], numeric_attr="int")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    attrs = [
        _img2col_operand_to_attr(op_name, param_name, operand, numeric_attr=numeric_attr)
        for operand in operands
    ]
    return ArrayAttr(attrs)


def _build_matmul_dynamic_shape(
    lhs: SSAValue,
    rhs: SSAValue,
    result_type: NnMemoryType,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 nn.matmul 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 动态维度通过 symbol.get_dim 从 lhs/rhs 提取。
    - 仅返回结果 shape 中的符号维度列表，顺序与结果 shape 一致。

    使用示例:
    - ops, dims = _build_matmul_dynamic_shape(lhs, rhs, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if isinstance(dim, IntAttr):
            continue
        if not isinstance(dim, StringAttr):
            raise LowerNnToKernelError("nn.matmul result shape entry must be IntAttr or StringAttr")
        if axis == 0:
            get_dim = SymbolGetDimOp(lhs, IntAttr(0))
        elif axis == 1:
            get_dim = SymbolGetDimOp(rhs, IntAttr(1))
        else:
            raise LowerNnToKernelError("nn.matmul result rank must be 2")
        ops.append(get_dim)
        operands.append(get_dim.result)
    return ops, operands


def _build_img2col1d_dynamic_shape(
    input_value: SSAValue,
    kw: SSAValue,
    sw: SSAValue,
    dw: SSAValue,
    pl: SSAValue,
    pr: SSAValue,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 nn.img2col1d 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 通过 symbol.get_dim 读取 B/C/W。
    - 按合同计算输出宽度表达式并生成对应 symbol op。
    - 返回 [B, C, KW, W_out] 形式的 dynamic_shape。

    使用示例:
    - ops, operands = _build_img2col1d_dynamic_shape(inp, kw, sw, dw, pl, pr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops: list[Operation] = []
    one_ops, one = _symbol_const_value(1)
    ops.extend(one_ops)

    get_b = SymbolGetDimOp(input_value, IntAttr(0))
    ops.append(get_b)
    get_c = SymbolGetDimOp(input_value, IntAttr(1))
    ops.append(get_c)
    get_w = SymbolGetDimOp(input_value, IntAttr(2))
    ops.append(get_w)

    kw_minus_ops, kw_minus_one = _symbol_binary_op(SymbolSubOp, kw, one, "-")
    ops.extend(kw_minus_ops)
    dw_mul_ops, dw_mul = _symbol_binary_op(SymbolMulOp, dw, kw_minus_one, "*")
    ops.extend(dw_mul_ops)

    w_plus_pl_ops, w_plus_pl = _symbol_binary_op(SymbolAddOp, get_w.result, pl, "+")
    ops.extend(w_plus_pl_ops)
    w_plus_pr_ops, w_plus_pr = _symbol_binary_op(SymbolAddOp, w_plus_pl, pr, "+")
    ops.extend(w_plus_pr_ops)
    w_minus_dw_ops, w_minus_dw = _symbol_binary_op(SymbolSubOp, w_plus_pr, dw_mul, "-")
    ops.extend(w_minus_dw_ops)
    w_minus_one_ops, w_minus_one = _symbol_binary_op(SymbolSubOp, w_minus_dw, one, "-")
    ops.extend(w_minus_one_ops)
    w_div_ops, w_div = _symbol_binary_op(SymbolFloorDivOp, w_minus_one, sw, "//")
    ops.extend(w_div_ops)
    w_out_ops, w_out = _symbol_binary_op(SymbolAddOp, w_div, one, "+")
    ops.extend(w_out_ops)

    return ops, [get_b.result, get_c.result, kw, w_out]


def _build_img2col2d_dynamic_shape(
    input_value: SSAValue,
    kh: SSAValue,
    kw: SSAValue,
    sh: SSAValue,
    sw: SSAValue,
    dh: SSAValue,
    dw: SSAValue,
    ph: SSAValue,
    pw: SSAValue,
    pl: SSAValue,
    pr: SSAValue,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 nn.img2col2d 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 通过 symbol.get_dim 读取 B/C/H/W。
    - 生成 OH/OW 相关 symbol 算术表达式。
    - 返回 [B, C, KH, KW, OH, OW] 形式的 dynamic_shape。

    使用示例:
    - ops, operands = _build_img2col2d_dynamic_shape(inp, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops: list[Operation] = []
    one_ops, one = _symbol_const_value(1)
    ops.extend(one_ops)

    get_b = SymbolGetDimOp(input_value, IntAttr(0))
    ops.append(get_b)
    get_c = SymbolGetDimOp(input_value, IntAttr(1))
    ops.append(get_c)
    get_h = SymbolGetDimOp(input_value, IntAttr(2))
    ops.append(get_h)
    get_w = SymbolGetDimOp(input_value, IntAttr(3))
    ops.append(get_w)

    kh_minus_ops, kh_minus_one = _symbol_binary_op(SymbolSubOp, kh, one, "-")
    ops.extend(kh_minus_ops)
    kw_minus_ops, kw_minus_one = _symbol_binary_op(SymbolSubOp, kw, one, "-")
    ops.extend(kw_minus_ops)
    dh_mul_ops, dh_mul = _symbol_binary_op(SymbolMulOp, dh, kh_minus_one, "*")
    ops.extend(dh_mul_ops)
    dw_mul_ops, dw_mul = _symbol_binary_op(SymbolMulOp, dw, kw_minus_one, "*")
    ops.extend(dw_mul_ops)

    h_plus_ph_ops, h_plus_ph = _symbol_binary_op(SymbolAddOp, get_h.result, ph, "+")
    ops.extend(h_plus_ph_ops)
    h_plus_pw_ops, h_plus_pw = _symbol_binary_op(SymbolAddOp, h_plus_ph, pw, "+")
    ops.extend(h_plus_pw_ops)
    h_minus_dh_ops, h_minus_dh = _symbol_binary_op(SymbolSubOp, h_plus_pw, dh_mul, "-")
    ops.extend(h_minus_dh_ops)
    h_minus_one_ops, h_minus_one = _symbol_binary_op(SymbolSubOp, h_minus_dh, one, "-")
    ops.extend(h_minus_one_ops)
    h_div_ops, h_div = _symbol_binary_op(SymbolFloorDivOp, h_minus_one, sh, "//")
    ops.extend(h_div_ops)
    h_out_ops, h_out = _symbol_binary_op(SymbolAddOp, h_div, one, "+")
    ops.extend(h_out_ops)

    w_plus_pl_ops, w_plus_pl = _symbol_binary_op(SymbolAddOp, get_w.result, pl, "+")
    ops.extend(w_plus_pl_ops)
    w_plus_pr_ops, w_plus_pr = _symbol_binary_op(SymbolAddOp, w_plus_pl, pr, "+")
    ops.extend(w_plus_pr_ops)
    w_minus_dw_ops, w_minus_dw = _symbol_binary_op(SymbolSubOp, w_plus_pr, dw_mul, "-")
    ops.extend(w_minus_dw_ops)
    w_minus_one_ops, w_minus_one = _symbol_binary_op(SymbolSubOp, w_minus_dw, one, "-")
    ops.extend(w_minus_one_ops)
    w_div_ops, w_div = _symbol_binary_op(SymbolFloorDivOp, w_minus_one, sw, "//")
    ops.extend(w_div_ops)
    w_out_ops, w_out = _symbol_binary_op(SymbolAddOp, w_div, one, "+")
    ops.extend(w_out_ops)

    return ops, [get_b.result, get_c.result, kh, kw, h_out, w_out]


def _build_alloc_dynamic_shape_from_result(
    result_type: NnMemoryType,
    *,
    include_static: bool = True,
) -> tuple[list[Operation], list[SSAValue]]:
    """基于结果类型构造 dma.alloc 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - include_static=True 时，静态整数维度使用对应数值的 symbol.int。
    - include_static=False 时仅输出符号维度。
    - 符号维度使用同名 symbol.int。
    - 匿名动态维度不允许。

    使用示例:
    - ops, operands = _build_alloc_dynamic_shape_from_result(result_type)
    - ops, operands = _build_alloc_dynamic_shape_from_result(result_type, include_static=False)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for dim in result_type.shape.data:
        if isinstance(dim, IntAttr):
            if not include_static:
                continue
            new_ops, value = _const_symbol_value(str(dim.data), dim.data)
            ops.extend(new_ops)
            operands.append(value)
            continue
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                raise LowerNnToKernelError("nn op result shape must not contain '?'")
            new_ops, value = _const_symbol_value(dim.data, 0)
            ops.extend(new_ops)
            operands.append(value)
            continue
        raise LowerNnToKernelError("nn op result shape entry must be IntAttr or StringAttr")
    return ops, operands


def _build_reduce_alloc_dynamic_shape(
    source: SSAValue,
    result_type: NnMemoryType,
    axis_attr: IntegerAttr,
    keepdim_attr: IntegerAttr,
    op_name: str,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 reduce 输出 dma.alloc 的 dynamic_shape operands。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅为符号维度生成 symbol.get_dim。
    - static 维度不生成 dynamic_shape operand。
    - keepdim=false 时按 axis 跳过被规约维度。

    使用示例:
    - ops, operands = _build_reduce_alloc_dynamic_shape(inp, out_type, axis, keepdim, "nn.reduce_sum")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/reduce_sum.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise LowerNnToKernelError(f"{op_name} operand must be nn.memory")

    axis_value = axis_attr.value.data
    keepdim_flag = keepdim_attr.value.data != 0
    rank = len(source_type.shape.data)
    if axis_value < 0 or axis_value >= rank:
        raise LowerNnToKernelError(f"{op_name} axis must be within input rank")
    expected_rank = rank if keepdim_flag else rank - 1
    if len(result_type.shape.data) != expected_rank:
        raise LowerNnToKernelError(f"{op_name} result rank mismatch with keepdim")

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    for out_axis, out_dim in enumerate(result_type.shape.data):
        if isinstance(out_dim, StringAttr):
            if out_dim.data == "?":
                raise LowerNnToKernelError("nn op result shape must not contain '?'")
            in_axis = out_axis if keepdim_flag else out_axis + (1 if out_axis >= axis_value else 0)
            get_dim = SymbolGetDimOp(source, IntAttr(in_axis))
            ops.append(get_dim)
            operands.append(get_dim.result)
            continue
        if isinstance(out_dim, IntAttr):
            continue
        raise LowerNnToKernelError("nn op result shape entry must be IntAttr or StringAttr")
    return ops, operands


def _build_broadcast_alloc_dynamic_shape(
    source: SSAValue,
    result_type: NnMemoryType,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 nn.broadcast 结果 dma.alloc 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按尾维对齐规则，将 result 的每一维映射回 source 对应维度。
    - 对于可从 source 直接读取的维度（逐维相等），使用 symbol.get_dim 获取实际维度。
    - 对于由 singleton 扩张得到的静态整数维度，使用常量 symbol.int。
    - 对于 singleton 扩张为符号维度，仅允许复用 source shape 中已有的符号维度。
    - 禁止生成无法从 source 获得的符号维，避免引入不一致的 shape 语义。

    使用示例:
    - ops, operands = _build_broadcast_alloc_dynamic_shape(op.operands[0], result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise LowerNnToKernelError("nn.broadcast operand must be nn.memory")

    source_rank = len(source_type.shape.data)
    result_rank = len(result_type.shape.data)
    if result_rank < source_rank:
        raise LowerNnToKernelError("nn.broadcast result rank must be >= operand rank")
    prefix_rank = result_rank - source_rank

    ops: list[Operation] = []
    operands: list[SSAValue] = []
    axis_values: dict[int, SSAValue] = {}
    symbol_source_axes: dict[str, int] = {}
    for axis, source_dim in enumerate(source_type.shape.data):
        if isinstance(source_dim, StringAttr) and source_dim.data != "?":
            symbol_source_axes.setdefault(source_dim.data, axis)
    for result_axis, result_dim in enumerate(result_type.shape.data):
        if isinstance(result_dim, StringAttr) and result_dim.data == "?":
            raise LowerNnToKernelError("nn op result shape must not contain '?'")

        source_axis = result_axis - prefix_rank
        if source_axis < 0:
            if isinstance(result_dim, IntAttr):
                new_ops, value = _const_symbol_value(str(result_dim.data), result_dim.data)
                ops.extend(new_ops)
                operands.append(value)
                continue
            if isinstance(result_dim, StringAttr):
                symbol_axis = symbol_source_axes.get(result_dim.data)
                if symbol_axis is None:
                    raise LowerNnToKernelError(
                        "LowerNnToKernelBroadcastSymbolDimNotFromSource: "
                        f"nn.broadcast cannot expand implicit singleton dim to symbol dim '{result_dim.data}'"
                    )
                dim_value = axis_values.get(symbol_axis)
                if dim_value is None:
                    get_dim = SymbolGetDimOp(source, IntAttr(symbol_axis))
                    ops.append(get_dim)
                    dim_value = get_dim.result
                    axis_values[symbol_axis] = dim_value
                operands.append(dim_value)
                continue
            raise LowerNnToKernelError("nn op result shape entry must be IntAttr or StringAttr")

        source_dim = source_type.shape.data[source_axis]

        if isinstance(source_dim, IntAttr) and isinstance(result_dim, IntAttr):
            if source_dim.data == result_dim.data:
                dim_value = axis_values.get(source_axis)
                if dim_value is None:
                    get_dim = SymbolGetDimOp(source, IntAttr(source_axis))
                    ops.append(get_dim)
                    dim_value = get_dim.result
                    axis_values[source_axis] = dim_value
                operands.append(dim_value)
                continue
            if source_dim.data == 1:
                new_ops, value = _const_symbol_value(str(result_dim.data), result_dim.data)
                ops.extend(new_ops)
                operands.append(value)
                continue
            raise LowerNnToKernelError("nn.broadcast result shape is not compatible with operand shape")

        if isinstance(source_dim, StringAttr) and isinstance(result_dim, StringAttr):
            if source_dim.data == "?":
                raise LowerNnToKernelError("nn.broadcast operand shape must not contain '?'")
            if source_dim.data == result_dim.data:
                dim_value = axis_values.get(source_axis)
                if dim_value is None:
                    get_dim = SymbolGetDimOp(source, IntAttr(source_axis))
                    ops.append(get_dim)
                    dim_value = get_dim.result
                    axis_values[source_axis] = dim_value
                operands.append(dim_value)
                continue
            raise LowerNnToKernelError("nn.broadcast result shape is not compatible with operand shape")

        if isinstance(source_dim, IntAttr) and source_dim.data == 1 and isinstance(result_dim, StringAttr):
            symbol_axis = symbol_source_axes.get(result_dim.data)
            if symbol_axis is None:
                raise LowerNnToKernelError(
                    "LowerNnToKernelBroadcastSymbolDimNotFromSource: "
                    f"nn.broadcast cannot expand singleton dim to symbol dim '{result_dim.data}'"
                )
            dim_value = axis_values.get(symbol_axis)
            if dim_value is None:
                get_dim = SymbolGetDimOp(source, IntAttr(symbol_axis))
                ops.append(get_dim)
                dim_value = get_dim.result
                axis_values[symbol_axis] = dim_value
            operands.append(dim_value)
            continue

        raise LowerNnToKernelError("nn.broadcast result shape is not compatible with operand shape")

    return ops, operands


def _build_transpose_alloc_dynamic_shape(
    source: SSAValue,
    result_type: NnMemoryType,
    perm: ArrayAttr,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 nn.transpose 结果 dma.alloc 的 dynamic_shape operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按 perm 顺序从 source 读取维度，保证动态维来自 symbol.get_dim。
    - 仅接受 source/result rank 一致的 transpose。
    - 拒绝结果 shape 中的匿名维度 `?`。

    使用示例:
    - ops, operands = _build_transpose_alloc_dynamic_shape(source, result_type, perm_attr)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise LowerNnToKernelError("nn.transpose operand must be nn.memory")

    source_rank = len(source_type.shape.data)
    result_rank = len(result_type.shape.data)
    if result_rank != source_rank:
        raise LowerNnToKernelError("nn.transpose result rank must match operand rank")

    perm_values: list[int] = []
    for entry in perm.data:
        if isinstance(entry, IntAttr):
            perm_values.append(entry.data)
            continue
        if isinstance(entry, IntegerAttr) and isinstance(entry.value, IntAttr):
            perm_values.append(entry.value.data)
            continue
        raise LowerNnToKernelError("nn.transpose perm must be a permutation of 0..rank-1")

    ops: list[Operation] = []
    axis_values: dict[int, SSAValue] = {}
    for source_axis in range(source_rank):
        get_dim = SymbolGetDimOp(source, IntAttr(source_axis))
        ops.append(get_dim)
        axis_values[source_axis] = get_dim.result

    operands: list[SSAValue] = []
    for result_axis, source_axis in enumerate(perm_values):
        result_dim = result_type.shape.data[result_axis]
        if isinstance(result_dim, StringAttr) and result_dim.data == "?":
            raise LowerNnToKernelError("nn op result shape must not contain '?'")
        operands.append(axis_values[source_axis])
    return ops, operands


def _ensure_contiguous_result_stride(result_type: NnMemoryType) -> None:
    """校验结果 stride 在静态形状下满足连续布局。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在 shape/stride 均为静态整数时进行连续性校验。
    - 若 stride 不满足行主序连续布局，抛出明确错误。

    使用示例:
    - _ensure_contiguous_result_stride(result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    shape_dims: list[int] = []
    for dim in result_type.shape.data:
        if not isinstance(dim, IntAttr):
            return
        shape_dims.append(dim.data)

    stride_dims: list[int] = []
    for dim in result_type.stride.data:
        if not isinstance(dim, IntAttr):
            return
        stride_dims.append(dim.data)

    expected: list[int] = []
    running = 1
    for dim in reversed(shape_dims):
        expected.append(running)
        running *= dim
    expected.reverse()

    if stride_dims != expected:
        raise LowerNnToKernelError("dma.alloc requires contiguous result stride")


def _is_static_shape(result_type: NnMemoryType) -> bool:
    """判断结果 shape 是否全为静态整数维度。"""

    return all(isinstance(dim, IntAttr) for dim in result_type.shape.data)


def _select_shape_source(op: Operation) -> SSAValue:
    """选择用于生成 dynamic_shape 的 memory operand。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 优先返回第一个 `nn.memory` operand。
    - 为 mixed add 这类包含标量 operand 的路径提供统一 shape 来源。

    使用示例:
    - shape_source = _select_shape_source(op)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if op.name == "nn.select" and len(op.operands) >= 2:
        return SSAValue.get(op.operands[1])

    for operand in op.operands:
        operand_value = SSAValue.get(operand)
        if isinstance(operand_value.type, NnMemoryType):
            return operand_value
    raise LowerNnToKernelError("nn op must provide at least one nn.memory operand")


def _maybe_materialize_mixed_add_rhs(
    op: Operation,
    result_type: NnMemoryType,
    dynamic_shape: list[SSAValue],
) -> tuple[list[Operation], SSAValue]:
    """按需把 mixed `nn.add` 的 rhs 标量物化为 temporary memory。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅处理 `nn.add(memory[i32], i32|!symbol.int)`。
    - 通过 `dma.alloc + dma.fill` 生成可被 `kernel.binary_elewise(kind=add)` 消费的 rhs memory。

    使用示例:
    - extra_ops, rhs_value = _maybe_materialize_mixed_add_rhs(op, result_type, dynamic_shape)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if op.name != "nn.add":
        if len(op.operands) < 2:
            return [], SSAValue.get(op.operands[0])
        return [], SSAValue.get(op.operands[1])

    _ensure_operand_count(op, 2)
    lhs_value = SSAValue.get(op.operands[0])
    rhs_value = SSAValue.get(op.operands[1])
    lhs_type = lhs_value.type
    rhs_type = rhs_value.type

    if not isinstance(lhs_type, NnMemoryType):
        return [], rhs_value
    if isinstance(rhs_type, NnMemoryType):
        return [], rhs_value
    if rhs_type != i32 and not isinstance(rhs_type, SymbolValueType):
        return [], rhs_value
    if lhs_type.element_type != i32 or result_type.element_type != i32:
        raise LowerNnToKernelError("mixed nn.add lowering currently requires i32 memory/result")

    rhs_alloc = DmaAllocOp(dynamic_shape, result_type)
    rhs_fill = DmaFillOp(rhs_alloc.result, rhs_value)
    return [rhs_alloc, rhs_fill], rhs_alloc.result


def _build_kernel_op(
    op: Operation,
    out_value: SSAValue,
    space: NnMemorySpaceAttr,
    *,
    lhs_value: SSAValue | None = None,
    rhs_value: SSAValue | None = None,
    img2col_operands: list[SSAValue] | None = None,
) -> Operation:
    """构造 kernel dialect op。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 根据 nn op 名称映射 kernel op。
    - 处理二元/选择/类型转换/单 operand 结构化 op。
    - img2col 支持显式传入已归一的 symbol.int operands。

    使用示例:
    - kernel_op = _build_kernel_op(op, alloc.results[0], space)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if op.name in _SUPPORTED_BINARY_KINDS:
        _ensure_operand_count(op, 2)
        kind = _SUPPORTED_BINARY_KINDS[op.name]
        lowered_lhs = lhs_value if lhs_value is not None else SSAValue.get(op.operands[0])
        lowered_rhs = rhs_value if rhs_value is not None else SSAValue.get(op.operands[1])
        return KernelBinaryElewiseOp(
            lowered_lhs,
            lowered_rhs,
            out_value,
            kind=kind,
            space=space,
        )

    if op.name == "nn.matmul":
        _ensure_operand_count(op, 2)
        return KernelMatmulOp(op.operands[0], op.operands[1], out_value, space)

    if op.name == "nn.select":
        _ensure_operand_count(op, 3)
        return KernelSelectOp(op.operands[0], op.operands[1], op.operands[2], out_value, space)

    if op.name == "nn.cast":
        _ensure_operand_count(op, 1)
        return _DmaCastOutOp(out_value, op.operands[0])

    if op.name == "nn.exp":
        _ensure_operand_count(op, 1)
        return KernelExpOp(op.operands[0], out_value, space)

    if op.name == "nn.softmax":
        _ensure_operand_count(op, 1)
        axis_attr = _parse_softmax_axis_attr(op.attributes.get("axis"))
        return KernelSoftmaxOp(op.operands[0], out_value, axis_attr, space)

    if op.name == "nn.img2col1d":
        _ensure_operand_count(op, 6)
        operands = (
            img2col_operands
            if img2col_operands is not None
            else [SSAValue.get(operand) for operand in op.operands]
        )
        return KernelImg2col1dOp(
            operands[0],
            out_value,
            operands[1],
            operands[2],
            operands[3],
            operands[4],
            operands[5],
            space=space,
        )

    if op.name == "nn.img2col2d":
        _ensure_operand_count(op, 11)
        operands = (
            img2col_operands
            if img2col_operands is not None
            else [SSAValue.get(operand) for operand in op.operands]
        )
        return KernelImg2col2dOp(
            operands[0],
            out_value,
            operands[1],
            operands[2],
            operands[3],
            operands[4],
            operands[5],
            operands[6],
            operands[7],
            operands[8],
            operands[9],
            operands[10],
            space=space,
        )

    if op.name in _REDUCE_KIND_MAP:
        _ensure_operand_count(op, 1)
        axis_attr = _parse_reduce_axis_attr(op.attributes.get("axes"), op.name)
        keepdim_attr = _parse_reduce_keepdim_attr(op.attributes.get("keepdim"), op.name)
        return KernelReduceOp(
            op.operands[0],
            out_value,
            kind=_REDUCE_KIND_MAP[op.name],
            axis=axis_attr,
            keepdim=keepdim_attr,
            space=space,
        )

    raise LowerNnToKernelError(f"Unsupported nn op: {op.name}")


def _lower_nn_op(op: Operation, block: Block) -> None:
    """将单个 nn op lower 为 kernel op。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 为结果插入 dma.alloc。
    - 用 kernel op 替换 nn op，并替换所有使用者。
    - nn.broadcast 在 source/结果空间不一致时先插入 dma.alloc + dma.copy。
    - nn.transpose lower 为 dma.transpose。

    使用示例:
    - _lower_nn_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    if op.name == "nn.transpose":
        _ensure_operand_count(op, 1)
        result_type = _ensure_single_result(op)
        _ensure_space_attr(op)
        source = SSAValue.get(op.operands[0])
        source_type = source.type
        if not isinstance(source_type, NnMemoryType):
            raise LowerNnToKernelError("nn.transpose operand must be nn.memory")
        perm_attr = _parse_transpose_perm_attr(op.attributes.get("perm"), len(source_type.shape.data))
        if len(result_type.shape.data) != len(source_type.shape.data):
            raise LowerNnToKernelError("nn.transpose result rank must match operand rank")
        if _is_static_shape(result_type):
            shape_ops = []
            dynamic_shape = []
        else:
            shape_ops, dynamic_shape = _build_transpose_alloc_dynamic_shape(source, result_type, perm_attr)
        alloc = DmaAllocOp(dynamic_shape, result_type)
        transpose = DmaTransposeOp(alloc.result, source, perm_attr)

        try:
            alloc.verify()
            transpose.verify()
        except VerifyException as exc:
            raise LowerNnToKernelError(str(exc)) from exc

        block.insert_ops_before([*shape_ops, alloc, transpose], op)
        op.results[0].replace_by(alloc.result)
        block.erase_op(op)
        return

    if op.name in ("nn.broadcast", "nn.broadcast_to"):
        _ensure_operand_count(op, 1)
        result_type = _ensure_single_result(op)
        _ensure_space_attr(op)
        source = SSAValue.get(op.operands[0])
        source_type = source.type
        if not isinstance(source_type, NnMemoryType):
            raise LowerNnToKernelError("nn.broadcast operand must be nn.memory")

        if _is_static_shape(result_type):
            shape_ops = []
            dynamic_shape = []
        else:
            shape_ops, dynamic_shape = _build_broadcast_alloc_dynamic_shape(source, result_type)
        alloc = DmaAllocOp(dynamic_shape, result_type)
        broadcast_source = source
        extra_ops: list[Operation] = []
        extra_alloc: DmaAllocOp | None = None
        extra_copy: DmaCopyOp | None = None
        if source_type.space.space.data != result_type.space.space.data:
            temp_type = NnMemoryType(
                source_type.shape,
                source_type.stride,
                source_type.element_type,
                result_type.space,
            )
            if _is_static_shape(temp_type):
                temp_shape_ops = []
                temp_dynamic_shape = []
            else:
                temp_shape_ops, temp_dynamic_shape = _build_alloc_dynamic_shape(source, temp_type)
            extra_alloc = DmaAllocOp(temp_dynamic_shape, temp_type)
            extra_copy = DmaCopyOp(source, extra_alloc.result)
            extra_ops.extend(temp_shape_ops)
            extra_ops.extend([extra_alloc, extra_copy])
            broadcast_source = extra_alloc.result

        broadcast = DmaBroadcastOp(alloc.result, broadcast_source)

        try:
            alloc.verify()
            if extra_alloc is not None and extra_copy is not None:
                extra_alloc.verify()
                extra_copy.verify()
            broadcast.verify()
        except VerifyException as exc:
            raise LowerNnToKernelError(str(exc)) from exc

        ops_to_insert = [*shape_ops, *extra_ops, alloc, broadcast]
        block.insert_ops_before(ops_to_insert, op)
        op.results[0].replace_by(alloc.result)
        block.erase_op(op)
        return

    result_type = _ensure_single_result(op)
    space = _ensure_space_attr(op)

    img2col_ops: list[Operation] = []
    img2col_operands: list[SSAValue] | None = None
    img2col_drop_ops: list[Operation] = []
    if op.name in {"nn.img2col1d", "nn.img2col2d"}:
        img2col_ops, img2col_operands, img2col_drop_ops = _normalize_img2col_operands(op)

    _ensure_contiguous_result_stride(result_type)
    if _is_static_shape(result_type):
        shape_ops: list[Operation] = []
        dynamic_shape: list[SSAValue] = []
    elif op.name in _REDUCE_KIND_MAP:
        _ensure_operand_count(op, 1)
        axis_attr = _parse_reduce_axis_attr(op.attributes.get("axes"), op.name)
        keepdim_attr = _parse_reduce_keepdim_attr(op.attributes.get("keepdim"), op.name)
        shape_ops, dynamic_shape = _build_reduce_alloc_dynamic_shape(
            SSAValue.get(op.operands[0]),
            result_type,
            axis_attr,
            keepdim_attr,
            op.name,
        )
    elif op.name == "nn.matmul":
        lhs_value = SSAValue.get(op.operands[0])
        rhs_value = SSAValue.get(op.operands[1])
        shape_ops, dynamic_shape = _build_matmul_dynamic_shape(lhs_value, rhs_value, result_type)
    elif op.name == "nn.img2col1d":
        if img2col_operands is None:
            raise LowerNnToKernelError("nn.img2col1d normalized operands missing")
        shape_ops, dynamic_shape = _build_img2col1d_dynamic_shape(
            img2col_operands[0],
            img2col_operands[1],
            img2col_operands[2],
            img2col_operands[3],
            img2col_operands[4],
            img2col_operands[5],
        )
    elif op.name == "nn.img2col2d":
        if img2col_operands is None:
            raise LowerNnToKernelError("nn.img2col2d normalized operands missing")
        shape_ops, dynamic_shape = _build_img2col2d_dynamic_shape(
            img2col_operands[0],
            img2col_operands[1],
            img2col_operands[2],
            img2col_operands[3],
            img2col_operands[4],
            img2col_operands[5],
            img2col_operands[6],
            img2col_operands[7],
            img2col_operands[8],
            img2col_operands[9],
            img2col_operands[10],
        )
    elif op.name in _RESULT_TYPED_ALLOC_OPS:
        shape_ops, dynamic_shape = _build_alloc_dynamic_shape_from_result(result_type)
    else:
        shape_source = _select_shape_source(op)
        shape_ops, dynamic_shape = _build_alloc_dynamic_shape(shape_source, result_type)
    alloc = DmaAllocOp(dynamic_shape, result_type)
    rhs_ops, lowered_rhs = _maybe_materialize_mixed_add_rhs(op, result_type, dynamic_shape)
    kernel_op = _build_kernel_op(
        op,
        alloc.result,
        space,
        rhs_value=lowered_rhs,
        img2col_operands=img2col_operands,
    )
    if op.name == "nn.img2col1d":
        if img2col_operands is None:
            raise LowerNnToKernelError("nn.img2col1d normalized operands missing")
        kernel_op.attributes["stride"] = _build_img2col_attr_array(
            op.name,
            "stride",
            [img2col_operands[2]],
            numeric_attr="int",
        )
        kernel_op.attributes["dilation"] = _build_img2col_attr_array(
            op.name,
            "dilation",
            [img2col_operands[3]],
            numeric_attr="int",
        )
        kernel_op.attributes["pad"] = _build_img2col_attr_array(
            op.name,
            "pad",
            [img2col_operands[4], img2col_operands[5]],
            numeric_attr="int",
        )
    if op.name == "nn.img2col2d":
        if img2col_operands is None:
            raise LowerNnToKernelError("nn.img2col2d normalized operands missing")
        kernel_op.attributes["stride"] = _build_img2col_attr_array(
            op.name,
            "stride",
            [img2col_operands[3], img2col_operands[4]],
            numeric_attr="i64",
        )
        kernel_op.attributes["dilation"] = _build_img2col_attr_array(
            op.name,
            "dilation",
            [img2col_operands[5], img2col_operands[6]],
            numeric_attr="i64",
        )
        kernel_op.attributes["pad"] = _build_img2col_attr_array(
            op.name,
            "pad",
            [img2col_operands[7], img2col_operands[8], img2col_operands[9], img2col_operands[10]],
            numeric_attr="i64",
        )

    try:
        alloc.verify()
        for rhs_op in rhs_ops:
            rhs_op.verify()
        for extra_op in img2col_ops:
            extra_op.verify()
        kernel_op.verify()
    except VerifyException as exc:
        raise LowerNnToKernelError(str(exc)) from exc

    if img2col_ops:
        block.insert_ops_before([*img2col_ops, *shape_ops, alloc, *rhs_ops, kernel_op], op)
    else:
        block.insert_ops_before([*shape_ops, alloc, *rhs_ops, kernel_op], op)
    op.results[0].replace_by(alloc.result)
    block.erase_op(op)
    for stale_op in img2col_drop_ops:
        if getattr(stale_op, "name", None) != "symbol.const":
            continue
        if not stale_op.results:
            continue
        if stale_op.results[0].uses.get_length() == 0:
            block.erase_op(stale_op)


def _lower_block(block: Block) -> None:
    """对单个 block 执行 nn -> kernel lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按顺序 lower block 内出现的 nn op。

    使用示例:
    - _lower_block(block)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    ops = list(block.ops)
    for op in ops:
        for region in op.regions:
            _lower_region(region)
        if op.name.startswith("nn."):
            _lower_nn_op(op, block)


def _lower_region(region: Region) -> None:
    """对 region 内的所有 block 执行 lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 遍历 region 的每个 block 并执行 lowering。

    使用示例:
    - _lower_region(region)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    for block in region.blocks:
        _lower_block(block)


def _lower_module(module: Operation) -> None:
    """在 module 中执行 nn -> kernel lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅对 func.func 进行 lowering。

    使用示例:
    - _lower_module(module)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    for op in module.ops:
        if isinstance(op, func.FuncOp):
            _lower_region(op.body)


def _iter_ops(module: Operation) -> Iterable[Operation]:
    """遍历 module 内全部 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 递归遍历 module 内所有 op。

    使用示例:
    - for op in _iter_ops(module):
          ...

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    stack: list[Operation] = list(module.ops)
    while stack:
        op = stack.pop()
        yield op
        for region in op.regions:
            for block in region.blocks:
                stack.extend(reversed(list(block.ops)))


def _ensure_no_nn_ops(module: Operation) -> None:
    """确保 module 内不残留 nn op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 遍历 module，若发现 nn op 则抛错。

    使用示例:
    - _ensure_no_nn_ops(module)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    for op in _iter_ops(module):
        if op.name.startswith("nn."):
            raise LowerNnToKernelError(f"nn op remains after lowering: {op.name}")


def _clear_op_result_name_hints(module: Operation) -> None:
    """清理 op 结果的 name_hint，避免残留 SSA 名称影响 expectation 匹配。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅清理 op 结果的 `name_hint`，不影响 block arguments。
    - 统一让 Printer 使用自动编号输出，匹配 expectation 的编号形式。

    使用示例:
    - _clear_op_result_name_hints(module)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    for op in _iter_ops(module):
        for result in op.results:
            result.name_hint = None


class LowerNnToKernelPass(Pass):
    """nn -> kernel lowering pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 执行 nn dialect 到 kernel dialect 的 lowering。

    使用示例:
    - module = LowerNnToKernelPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "lower-nn-to-kernel"

    def run(self: "LowerNnToKernelPass", module: Operation) -> Operation:
        """执行 pass。

        创建者: 金铲铲大作战
        最后一次更改: 小李飞刀

        功能说明:
        - 将 module 内 nn op lower 为 kernel op。

        使用示例:
        - LowerNnToKernelPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_to_kernel.md
        - test: test/pass/test_lowering_nn_to_kernel.py
        - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
        """

        if not isinstance(module, ModuleOp):
            raise LowerNnToKernelError("module must be builtin.module")
        try:
            iter(module.ops)
        except TypeError as exc:
            raise LowerNnToKernelError("module ops must be iterable") from exc

        _lower_module(module)
        _ensure_no_nn_ops(module)
        _clear_op_result_name_hints(module)
        return module


__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
