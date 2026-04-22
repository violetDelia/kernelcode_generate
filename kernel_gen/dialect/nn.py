"""NN dialect definitions.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 定义 nn dialect 的 memory type、space attribute 与逐元素/广播 op。
- 约定 `nn.truediv` 为唯一公开除法 op，`nn.div` alias 已移除。
- `nn.select` 不在 nn dialect 中提供，相关 lowering 由 pass 层按 op 名称处理。

使用示例:
- from kernel_gen.dialect.nn import Nn, NnAddOp, NnBroadcastOp, NnMemorySpaceAttr, NnMemoryType

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/test_nn_dialect.py
- 功能实现: kernel_gen/dialect/nn.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.common.contracts import (
    _build_contiguous_stride as _common_build_contiguous_stride,
    _collect_int_dims as _common_collect_int_dims,
    _dims_equal as _common_dims_equal,
    _verify_i64_attr as _common_verify_i64_attr,
    _verify_i64_attr_group as _common_verify_i64_attr_group,
    _verify_i64_attr_value as _common_verify_i64_attr_value,
    _verify_memory_type as _common_verify_memory_type,
)
from kernel_gen.common.errors import _ERROR_TEMPLATE
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    i1,
    i32,
)
from xdsl.ir import Attribute, Dialect, Operation, ParametrizedAttribute, SSAValue, TypeAttribute
from xdsl.irdl import (
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    operand_def,
    param_def,
    result_def,
)
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

_VALID_SPACES = {"global", "shared", "local", "tsm", "tlm1", "tlm2", "tlm3"}
_ERROR_ACTION = "请按接口约束传参"
_ERROR_ACTUAL = "不满足期望"
_ERROR_SCENE = "dialect.nn verifier"


def _raise_verify_error(expected: str, *, actual: str = _ERROR_ACTUAL) -> None:
    """统一抛出 nn dialect verifier 错误。"""

    raise VerifyException(
        _ERROR_TEMPLATE.format(
            scene=_ERROR_SCENE,
            expected=expected,
            actual=actual,
            action=_ERROR_ACTION,
        )
    )


def _parse_dim_list(parser: AttrParser) -> ArrayAttr[Attribute]:
    """解析 shape 或 stride 维度列表。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持非负整数、`?` 与符号标识符。
    - 允许表达式维度（例如 `W + PL` / `(W + PL) // SW`），并按原文本保留。

    使用示例:
    - _parse_dim_list(parser)

    关联文件:
    - spec: [spec/dialect/nn.md](spec/dialect/nn.md)
    - test: [test/dialect/test_nn_dialect.py](test/dialect/test_nn_dialect.py)
    - 功能实现: [kernel_gen/dialect/nn.py](kernel_gen/dialect/nn.py)
    """

    dims: list[Attribute] = []
    parser.parse_punctuation("[", "Expected dimension list.")
    if parser.parse_optional_punctuation("]") is not None:
        return ArrayAttr(dims)

    while True:
        if parser.parse_optional_punctuation("?") is not None:
            dims.append(StringAttr("?"))
        else:
            start_pos = parser.pos
            input_text = parser.lexer.input.content
            integer = parser.parse_optional_integer(allow_boolean=False, allow_negative=False)
            parsed_simple_integer = False
            if integer is not None:
                lookahead = parser.pos
                while lookahead < len(input_text) and input_text[lookahead].isspace():
                    lookahead += 1
                if lookahead >= len(input_text) or input_text[lookahead] in {",", "]"}:
                    dims.append(IntAttr(integer))
                    parsed_simple_integer = True
                else:
                    parser._resume_from(start_pos)
            if not parsed_simple_integer:
                parsed_simple_ident = False
                ident = parser.parse_optional_identifier()
                if ident is not None:
                    lookahead = parser.pos
                    while lookahead < len(input_text) and input_text[lookahead].isspace():
                        lookahead += 1
                    if lookahead >= len(input_text) or input_text[lookahead] in {",", "]"}:
                        dims.append(StringAttr(ident))
                        parsed_simple_ident = True
                    else:
                        parser._resume_from(start_pos)
                if not parsed_simple_ident:
                    depth = 0
                    end_pos = None
                    pos = start_pos
                    while pos < len(input_text):
                        ch = input_text[pos]
                        if ch == "(":
                            depth += 1
                        elif ch == ")" and depth > 0:
                            depth -= 1
                        elif depth == 0 and ch in {",", "]"}:
                            end_pos = pos
                            break
                        pos += 1
                    if end_pos is None:
                        parser.raise_error("Expected dimension list terminator.")
                    expr = input_text[start_pos:end_pos].strip()
                    if not expr:
                        parser.raise_error("Expected dimension symbol.")
                    parser._resume_from(end_pos)
                    dims.append(StringAttr(expr))

        if parser.parse_optional_punctuation(",") is None:
            break

    parser.parse_punctuation("]", "Expected dimension list terminator.")
    return ArrayAttr(dims)


def _print_dim_list(printer: Printer, dims: ArrayAttr[Attribute]) -> None:
    """打印 shape 或 stride 维度列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按 `[d0, d1, ...]` 文本格式输出维度。

    使用示例:
    - _print_dim_list(printer, dims)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    printer.print_string("[")
    for index, dim in enumerate(dims.data):
        if index:
            printer.print_string(", ")
        if isinstance(dim, IntAttr):
            printer.print_string(str(dim.data))
        elif isinstance(dim, StringAttr):
            printer.print_string(dim.data)
        else:
            _raise_verify_error("Dimension list only supports IntAttr or StringAttr")
    printer.print_string("]")


def _verify_dim_entry(dim: Attribute, field_name: str) -> None:
    """校验单个维度条目合法性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受 IntAttr 与非空 StringAttr。

    使用示例:
    - _verify_dim_entry(StringAttr(\"N\"), \"shape\")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if isinstance(dim, IntAttr):
        if dim.data < 0:
            _raise_verify_error(f"{field_name} dimensions must be non-negative")
        return

    if isinstance(dim, StringAttr) and dim.data:
        return

    _raise_verify_error(f"{field_name} dimensions must be IntAttr or StringAttr")


@irdl_attr_definition
class NnMemorySpaceAttr(ParametrizedAttribute):
    """NN memory space attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 显式建模 `global`、`shared`、`local`、`tsm`、`tlm1`、`tlm2`、`tlm3` 七种 memory space。

    使用示例:
    - NnMemorySpaceAttr(StringAttr(\"global\"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.space"

    space: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析 space attribute 参数。"""

        parser.parse_punctuation("<", "Expected '<' for nn space attribute.")
        space = StringAttr(parser.parse_identifier("Expected nn memory space identifier."))
        parser.parse_punctuation(">", "Expected '>' for nn space attribute.")
        return (space,)

    def print_parameters(self, printer: Printer) -> None:
        """打印 space attribute 参数。"""

        printer.print_string("<")
        printer.print_string(self.space.data)
        printer.print_string(">")

    def verify(self) -> None:
        """校验 space attribute。"""

        if self.space.data not in _VALID_SPACES:
            _raise_verify_error("nn space must be one of global/shared/local/tsm/tlm1/tlm2/tlm3")

    @classmethod
    def from_name(cls, space: str) -> "NnMemorySpaceAttr":
        """从字符串构造 space attribute。

        创建者: 小李飞刀
        最后一次更改: jcc你莫辜负

        功能说明:
        - 简化 `global/shared/local/tsm/tlm1/tlm2/tlm3` 的构造。

        使用示例:
        - NnMemorySpaceAttr.from_name(\"global\")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        return cls(StringAttr(space))


@irdl_attr_definition
class NnMemoryType(ParametrizedAttribute, TypeAttribute):
    """NN memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 建模 `shape`、`stride`、`element_type` 与 `space` 四类信息。

    使用示例:
    - NnMemoryType(ArrayAttr([IntAttr(4)]), ArrayAttr([IntAttr(1)]), IntegerType(32), NnMemorySpaceAttr.from_name(\"global\"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.memory"

    shape: ArrayAttr[Attribute] = param_def(ArrayAttr[Attribute])
    stride: ArrayAttr[Attribute] = param_def(ArrayAttr[Attribute])
    element_type: Attribute = param_def(Attribute)
    space: NnMemorySpaceAttr = param_def(NnMemorySpaceAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析 memory type 参数。"""

        parser.parse_punctuation("<", "Expected '<' for nn memory type.")
        shape = _parse_dim_list(parser)
        parser.parse_punctuation(",", "Expected ',' after shape.")
        stride = _parse_dim_list(parser)
        parser.parse_punctuation(",", "Expected ',' after stride.")
        element_type = parser.parse_attribute()
        parser.parse_punctuation(",", "Expected ',' after element type.")
        space = parser.parse_attribute()
        parser.parse_punctuation(">", "Expected '>' for nn memory type.")
        if not isinstance(space, NnMemorySpaceAttr):
            _raise_verify_error("nn memory type space must be #nn.space<...>")
        return (shape, stride, element_type, space)

    def print_parameters(self, printer: Printer) -> None:
        """打印 memory type 参数。"""

        printer.print_string("<")
        _print_dim_list(printer, self.shape)
        printer.print_string(", ")
        _print_dim_list(printer, self.stride)
        printer.print_string(", ")
        printer.print_attribute(self.element_type)
        printer.print_string(", ")
        printer.print_attribute(self.space)
        printer.print_string(">")

    def verify(self) -> None:
        """校验 memory type。"""

        self.space.verify()
        if len(self.shape.data) != len(self.stride.data):
            _raise_verify_error("nn memory shape and stride rank must match")

        for dim in self.shape.data:
            _verify_dim_entry(dim, "shape")
        for dim in self.stride.data:
            _verify_dim_entry(dim, "stride")

        for shape_dim, stride_dim in zip(self.shape.data, self.stride.data, strict=True):
            if (
                isinstance(stride_dim, StringAttr)
                and stride_dim.data == "?"
                and isinstance(shape_dim, StringAttr)
                and shape_dim.data == "?"
            ):
                _raise_verify_error("stride '?' requires corresponding shape dimension to be symbol or integer")


def _verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 memory type。"""

    return _common_verify_memory_type(value, field_name, scene=_ERROR_SCENE)


def _verify_binary_memory_op(op: "_BaseNnBinaryOp", compare_result: bool) -> None:
    """统一校验 nn 二元 op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 检查 operand/result 类型、shape/stride、element_type 与 space 一致性。

    使用示例:
    - _verify_binary_memory_op(op, compare_result=False)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    lhs_type = _verify_memory_type(op.lhs.type, "lhs")
    rhs_type = _verify_memory_type(op.rhs.type, "rhs")
    result_type = _verify_memory_type(op.result.type, "result")

    op.space.verify()
    if lhs_type.space.space.data != rhs_type.space.space.data:
        _raise_verify_error("nn op operands must use the same space")
    if lhs_type.space.space.data != op.space.space.data:
        _raise_verify_error("nn op attribute space must match operand space")
    if result_type.space.space.data != op.space.space.data:
        _raise_verify_error("nn op attribute space must match result space")

    if lhs_type.shape != rhs_type.shape or lhs_type.shape != result_type.shape:
        _raise_verify_error("nn op shape must match across operands and result")
    if lhs_type.stride != rhs_type.stride or lhs_type.stride != result_type.stride:
        _raise_verify_error("nn op stride must match across operands and result")
    if lhs_type.element_type != rhs_type.element_type:
        _raise_verify_error("nn op operand element_type must match")

    if compare_result:
        if result_type.element_type != i1:
            _raise_verify_error("nn compare result element_type must be i1")
    elif result_type.element_type != lhs_type.element_type:
        _raise_verify_error("nn arithmetic result element_type must match operand element_type")


_ADD_DTYPE_ORDER = {"i32": 0, "f16": 1, "f32": 2}
_ADD_DTYPE_ATTR = {"i32": i32, "f16": Float16Type(), "f32": Float32Type()}


def _is_symbol_int_type(attr: Attribute) -> bool:
    """判断 attribute 是否为 symbol.int。

    创建者: 金铲铲大作战
    最后一次更改: 大闸蟹

    功能说明:
    - 仅通过 `name` 字段判断是否为 `symbol.int` 类型，避免 nn/symbol 循环依赖。

    使用示例:
    - _is_symbol_int_type(SymbolValueType.from_expr("K"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return getattr(attr, "name", None) == "symbol.int"


def _is_int_or_symbol_type(attr: Attribute) -> bool:
    """判断类型是否为整数或 symbol.int。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 允许任意位宽的 IntegerType。
    - 允许 symbol.int，复用 `_is_symbol_int_type` 规避循环依赖。

    使用示例:
    - _is_int_or_symbol_type(i32)
    - _is_int_or_symbol_type(SymbolValueType.from_expr("K"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return _is_symbol_int_type(attr) or isinstance(attr, IntegerType)


def _static_int_from_operand(operand: SSAValue) -> int | None:
    """尝试从 operand 提取静态整数值。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 支持 `arith.constant`/`symbol.const` 以及单层 `builtin.unrealized_conversion_cast`。
    - 无法解析时返回 None，交由上层决定是否跳过数值合同校验。

    使用示例:
    - value = _static_int_from_operand(op.kw)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    owner = operand.owner
    if owner is None:
        return None
    owner_name = getattr(owner, "name", None)
    if owner_name == "arith.constant":
        value_attr = owner.attributes.get("value")
        if value_attr is None:
            value_attr = getattr(owner, "value", None)
        if isinstance(value_attr, IntegerAttr):
            return int(value_attr.value.data)
        if isinstance(value_attr, IntAttr):
            return int(value_attr.data)
        return None
    if owner_name == "symbol.const":
        value_attr = owner.attributes.get("value")
        if isinstance(value_attr, IntAttr):
            return int(value_attr.data)
        return None
    if owner_name == "builtin.unrealized_conversion_cast":
        if owner.operands:
            return _static_int_from_operand(owner.operands[0])
    return None


def _verify_img2col_param_operands(
    operands: Sequence[SSAValue],
    *,
    allow_zero: bool,
    type_error_phrase: str,
    value_error_phrase: str,
) -> list[int | None]:
    """校验 img2col 参数 operand 类型并提取静态值。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 要求每个 operand 为 IntegerType 或 symbol.int。
    - 若可解析出静态整数值，则校验正数/非负数约束。
    - 解析失败则返回 None，供上层决定是否跳过形状合同校验。

    使用示例:
    - kw, sw = _verify_img2col_param_operands([op.kw, op.sw], allow_zero=False, type_error_phrase="kw-sw-must-be-int-or-symbol", value_error_phrase="kw-sw-must-be-positive")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    values: list[int | None] = []
    for operand in operands:
        if not _is_int_or_symbol_type(operand.type):
            _raise_verify_error(type_error_phrase)
        static_value = _static_int_from_operand(operand)
        if static_value is not None:
            if allow_zero:
                if static_value < 0:
                    _raise_verify_error(value_error_phrase)
            elif static_value <= 0:
                _raise_verify_error(value_error_phrase)
        values.append(static_value)
    return values


def _resolve_add_dtype_key(attr: Attribute) -> str | None:
    """解析 nn.add 标量/element_type 的 promotion key。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 i32/f16/f32 三种类型；
    - `!symbol.int` 视作 i32 参与 promotion。

    使用示例:
    - _resolve_add_dtype_key(i32)
    - _resolve_add_dtype_key(SymbolValueType.from_expr("K"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if _is_symbol_int_type(attr):
        return "i32"
    if isinstance(attr, IntegerType) and attr.width.data == 32:
        return "i32"
    if isinstance(attr, Float16Type):
        return "f16"
    if isinstance(attr, Float32Type):
        return "f32"
    return None


def _is_float_element_type(attr: Attribute) -> bool:
    """判断 element_type 是否为浮点类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 允许 f16/bf16/f32/f64 四类浮点类型。

    使用示例:
    - _is_float_element_type(Float32Type())

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return isinstance(attr, (Float16Type, BFloat16Type, Float32Type, Float64Type))


def _promote_add_dtype(lhs_type: Attribute, rhs_type: Attribute) -> Attribute | None:
    """计算 nn.add 的 dtype promotion 结果类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按 i32 < f16 < f32 顺序进行 promotion。

    使用示例:
    - _promote_add_dtype(i32, Float16Type())

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    lhs_key = _resolve_add_dtype_key(lhs_type)
    rhs_key = _resolve_add_dtype_key(rhs_type)
    if lhs_key is None or rhs_key is None:
        return None
    promoted_key = lhs_key if _ADD_DTYPE_ORDER[lhs_key] >= _ADD_DTYPE_ORDER[rhs_key] else rhs_key
    return _ADD_DTYPE_ATTR[promoted_key]


def _verify_add_op(op: "NnAddOp") -> None:
    """校验 nn.add，支持 memory + scalar/symbol。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 允许 `nn.memory + scalar`、`scalar + nn.memory`、`nn.memory + !symbol.int`；
    - 至少一侧必须为 `nn.memory`，结果的 shape/stride/space 继承 memory operand；
    - scalar dtype promotion 固定为 i32 < f16 < f32。

    使用示例:
    - _verify_add_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    lhs_value = SSAValue.get(op.lhs)
    rhs_value = SSAValue.get(op.rhs)
    lhs_type = lhs_value.type
    rhs_type = rhs_value.type
    result_type = _verify_memory_type(op.result.type, "result")

    lhs_is_memory = isinstance(lhs_type, NnMemoryType)
    rhs_is_memory = isinstance(rhs_type, NnMemoryType)
    if not lhs_is_memory and not rhs_is_memory:
        _raise_verify_error("nn.add requires at least one nn.memory operand")

    op.space.verify()
    if lhs_is_memory and rhs_is_memory:
        _verify_binary_memory_op(op, compare_result=False)
        return

    memory_type = _verify_memory_type(lhs_type if lhs_is_memory else rhs_type, "memory operand")
    if memory_type.space.space.data != op.space.space.data:
        _raise_verify_error("nn.add attribute space must match memory operand space")
    if result_type.space.space.data != memory_type.space.space.data:
        _raise_verify_error("nn.add result space must match memory operand")

    if result_type.shape != memory_type.shape:
        _raise_verify_error("nn.add result shape must match memory operand")
    if result_type.stride != memory_type.stride:
        _raise_verify_error("nn.add result stride must match memory operand")

    scalar_type = rhs_type if lhs_is_memory else lhs_type
    promoted_type = _promote_add_dtype(memory_type.element_type, scalar_type)
    if promoted_type is None:
        _raise_verify_error("nn.add scalar element_type must be i32/f16/f32 or symbol.int")
    if result_type.element_type != promoted_type:
        _raise_verify_error("nn.add result element_type must match promoted element_type")


def _verify_mixed_scalar_binary_op(op: "_BaseNnBinaryOp", op_name: str) -> None:
    """校验支持 mixed memory+scalar/symbol 的 nn 二元算术 op。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 允许 `nn.memory + scalar`、`scalar + nn.memory`、`nn.memory + !symbol.int`。
    - 结果的 shape/stride/space 继承 memory operand，dtype 按统一 promotion 规则决议。

    使用示例:
    - _verify_mixed_scalar_binary_op(op, "nn.sub")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    lhs_value = SSAValue.get(op.lhs)
    rhs_value = SSAValue.get(op.rhs)
    lhs_type = lhs_value.type
    rhs_type = rhs_value.type
    result_type = _verify_memory_type(op.result.type, "result")

    lhs_is_memory = isinstance(lhs_type, NnMemoryType)
    rhs_is_memory = isinstance(rhs_type, NnMemoryType)
    if not lhs_is_memory and not rhs_is_memory:
        _raise_verify_error(f"{op_name} requires at least one nn.memory operand")

    op.space.verify()
    if lhs_is_memory and rhs_is_memory:
        _verify_binary_memory_op(op, compare_result=False)
        return

    memory_type = _verify_memory_type(lhs_type if lhs_is_memory else rhs_type, "memory operand")
    if memory_type.space.space.data != op.space.space.data:
        _raise_verify_error(f"{op_name} attribute space must match memory operand space")
    if result_type.space.space.data != memory_type.space.space.data:
        _raise_verify_error(f"{op_name} result space must match memory operand")

    if result_type.shape != memory_type.shape:
        _raise_verify_error(f"{op_name} result shape must match memory operand")
    if result_type.stride != memory_type.stride:
        _raise_verify_error(f"{op_name} result stride must match memory operand")

    scalar_type = rhs_type if lhs_is_memory else lhs_type
    promoted_type = _promote_add_dtype(memory_type.element_type, scalar_type)
    if promoted_type is None:
        _raise_verify_error(f"{op_name} scalar element_type must be i32/f16/f32 or symbol.int")
    if result_type.element_type != promoted_type:
        _raise_verify_error(f"{op_name} result element_type must match promoted element_type")


def _dims_equal(lhs: Attribute, rhs: Attribute) -> bool:
    """判断两个维度是否语义一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在同类型且内容相等时认为一致。

    使用示例:
    - _dims_equal(IntAttr(1), IntAttr(1))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """
    return _common_dims_equal(lhs, rhs)


def _verify_broadcast_compat(input_type: NnMemoryType, result_type: NnMemoryType) -> None:
    """校验 nn.broadcast 的 shape 兼容性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按尾维对齐规则检查输入与输出 shape。
    - 仅允许 input 维为 1 时向任意目标维扩张。

    使用示例:
    - _verify_broadcast_compat(input_type, result_type)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """
    input_dims = input_type.shape.data
    result_dims = result_type.shape.data
    if len(result_dims) < len(input_dims):
        _raise_verify_error("result-rank-must-be-greater-or-equal-to-input")

    for input_dim, result_dim in zip(reversed(input_dims), reversed(result_dims), strict=False):
        if _dims_equal(input_dim, result_dim):
            continue
        if isinstance(input_dim, IntAttr) and input_dim.data == 1:
            continue
        _raise_verify_error("result-shape-must-match-broadcast-contract")


def _verify_transpose_perm(perm: ArrayAttr, rank: int) -> list[int]:
    """校验 nn.transpose 的 perm 合法性并返回序列。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 校验 perm 长度与 rank 一致。
    - 校验 perm 为 0..rank-1 的排列。

    使用示例:
    - _verify_transpose_perm(ArrayAttr([IntAttr(1), IntAttr(0)]), rank=2)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """
    if len(perm.data) != rank:
        _raise_verify_error("nn.transpose perm must match input rank")
    perm_values: list[int] = []
    for entry in perm.data:
        if isinstance(entry, IntAttr):
            perm_values.append(entry.data)
            continue
        if isinstance(entry, IntegerAttr) and isinstance(entry.value, IntAttr):
            perm_values.append(entry.value.data)
            continue
        _raise_verify_error("nn.transpose perm must be a permutation of 0..rank-1")
    if sorted(perm_values) != list(range(rank)):
        _raise_verify_error("nn.transpose perm must be a permutation of 0..rank-1")
    return perm_values


def _verify_transpose_layout(
    input_type: NnMemoryType,
    result_type: NnMemoryType,
    perm_values: Sequence[int],
) -> None:
    """校验 nn.transpose 的 shape/stride 是否按 perm 重排。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 按 perm 重排 input shape/stride，并与 result 对齐校验。

    使用示例:
    - _verify_transpose_layout(input_type, result_type, [1, 0])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """
    expected_shape = [input_type.shape.data[index] for index in perm_values]
    for expected_dim, actual_dim in zip(expected_shape, result_type.shape.data, strict=True):
        if not _dims_equal(expected_dim, actual_dim):
            _raise_verify_error("nn.transpose result shape must match permuted input")

    expected_stride = [input_type.stride.data[index] for index in perm_values]
    for expected_dim, actual_dim in zip(expected_stride, result_type.stride.data, strict=True):
        if not _dims_equal(expected_dim, actual_dim):
            _raise_verify_error("nn.transpose result stride must match permuted input")


def _normalize_i64_attr(value: int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr:
    """将数值规范化为 i64 IntegerAttr。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持传入 int/IntAttr/IntegerAttr，统一为 i64 IntegerAttr。
    - 用于 nn.img2col1d/nn.img2col2d 属性构造入口。

    使用示例:
    - _normalize_i64_attr(3, "kw")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if isinstance(value, IntegerAttr):
        return value
    if isinstance(value, IntAttr):
        value = value.data
    return IntegerAttr(value, IntegerType(64))


def _verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool) -> int:
    """校验 i64 属性值并返回整数。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验属性类型为 i64。
    - 校验正数/非负数约束并返回值。

    使用示例:
    - _verify_i64_attr_value(attr, "kw", allow_zero=False)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return _common_verify_i64_attr_value(
        attr,
        field_name,
        allow_zero=allow_zero,
        scene=_ERROR_SCENE,
    )


def _verify_i64_attr_group(
    attrs: Sequence[IntegerAttr],
    *,
    allow_zero: bool,
    error_phrase: str,
) -> list[int]:
    """校验一组 i64 属性值并返回整数列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验属性类型为 i64，且满足正数/非负数约束。
    - 任一属性不满足约束时，统一抛出 error_phrase。

    使用示例:
    - _verify_i64_attr_group([kw, sw, dw], allow_zero=False, error_phrase="kw-sw-dw-must-be-positive")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return _common_verify_i64_attr_group(
        attrs,
        allow_zero=allow_zero,
        error_phrase=error_phrase,
        scene=_ERROR_SCENE,
    )


def _verify_i64_attr(attr: IntegerAttr, field_name: str) -> int:
    """校验 i64 属性并返回整数值。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验属性类型为 i64，但不限制符号正负。
    - 用于需要允许负值的 axis 等字段。

    使用示例:
    - axis_value = _verify_i64_attr(axis_attr, "axis")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return _common_verify_i64_attr(attr, field_name, scene=_ERROR_SCENE)


def _collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None:
    """提取维度中的整数值列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅当所有维度均为 IntAttr 时返回整数列表。
    - 任何非 IntAttr 维度返回 None，表示无法进行数值合同校验。

    使用示例:
    - _collect_int_dims([IntAttr(1), IntAttr(2)])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return _common_collect_int_dims(dims)


def _build_contiguous_stride(shape: Sequence[int]) -> list[int]:
    """按连续行主序构建 stride 列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 以最后一维 stride=1 计算前序 stride。

    使用示例:
    - _build_contiguous_stride([1, 4, 8])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return _common_build_contiguous_stride(shape)


def _normalize_axes_attr(axes: Sequence[int] | ArrayAttr) -> ArrayAttr:
    """将归约 axes 规范化为 i64 ArrayAttr。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持传入轴序列或 ArrayAttr。
    - 统一输出元素为 i64 IntegerAttr 的 ArrayAttr。

    使用示例:
    - _normalize_axes_attr([0, 2])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if isinstance(axes, ArrayAttr):
        return axes
    return ArrayAttr([IntegerAttr(int(axis), IntegerType(64)) for axis in axes])


def _normalize_bool_attr(value: bool | int | IntegerAttr | IntAttr, field_name: str) -> IntegerAttr:
    """将布尔语义规范化为 i1 IntegerAttr。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 bool/int/IntAttr/IntegerAttr 输入，统一为 i1 IntegerAttr。
    - 具体合法性由 verifier 进一步校验。

    使用示例:
    - _normalize_bool_attr(True, "keepdim")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if isinstance(value, IntegerAttr):
        return value
    if isinstance(value, IntAttr):
        value = value.data
    if isinstance(value, bool):
        value = 1 if value else 0
    return IntegerAttr(int(value), IntegerType(1))


def _verify_exp_op(op: "NnExpOp") -> None:
    """校验 nn.exp 的结构化合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 operand/result 必须是 nn.memory 且输入为浮点类型。
    - 校验 shape/stride/element_type/space 一致性。

    使用示例:
    - _verify_exp_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    input_type = op.input.type
    result_type = op.result.type
    if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
        _raise_verify_error("operand-must-be-nn-memory")
    input_type.verify()
    result_type.verify()

    if not _is_float_element_type(input_type.element_type):
        _raise_verify_error("operand-element-type-must-be-float")

    if input_type.shape != result_type.shape or input_type.stride != result_type.stride:
        _raise_verify_error("result-shape-stride-must-match-input")

    if input_type.element_type != result_type.element_type:
        _raise_verify_error("result-element-type-must-match-input")

    op.space.verify()
    if input_type.space.space.data != result_type.space.space.data:
        _raise_verify_error("result-space-must-match-input-and-attr")
    if input_type.space.space.data != op.space.space.data:
        _raise_verify_error("result-space-must-match-input-and-attr")


def _verify_unary_float_op(
    input_type: NnMemoryType,
    result_type: NnMemoryType,
    space: NnMemorySpaceAttr,
) -> None:
    """校验逐元素浮点 unary op 的公共合同。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一校验 `relu/sigmoid/tanh/exp` 这类浮点 unary op 的输入、输出与 memory space 约束。
    - 作为 `NnReluOp`、`NnSigmoidOp`、`NnTanhOp`、`NnExpOp` verifier 共享的底层 helper。

    使用示例:
    - _verify_unary_float_op(input_type, result_type, op.space)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    input_type.verify()
    result_type.verify()

    if not _is_float_element_type(input_type.element_type):
        _raise_verify_error("operand-element-type-must-be-float")

    if input_type.shape != result_type.shape or input_type.stride != result_type.stride:
        _raise_verify_error("result-shape-stride-must-match-input")

    if input_type.element_type != result_type.element_type:
        _raise_verify_error("result-element-type-must-match-input")

    space.verify()
    if input_type.space.space.data != result_type.space.space.data:
        _raise_verify_error("result-space-must-match-input-and-attr")
    if input_type.space.space.data != space.space.data:
        _raise_verify_error("result-space-must-match-input-and-attr")


def _verify_activation_scalar_operand(value: SSAValue, field_name: str) -> None:
    """校验激活函数额外标量参数类型。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 `leaky_relu` / `hard_sigmoid` 的附加标量参数只能是整数或浮点标量。
    - 明确拒绝 `nn.memory` 与 `symbol.int` 作为激活系数输入，避免 verifier 接受未公开的参数形态。

    使用示例:
    - _verify_activation_scalar_operand(op.alpha, "alpha")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    attr = value.type
    if isinstance(attr, NnMemoryType) or _is_symbol_int_type(attr):
        _raise_verify_error(f"{field_name} must be int or float scalar")
    if not isinstance(attr, (IntegerType, Float16Type, BFloat16Type, Float32Type, Float64Type)):
        _raise_verify_error(f"{field_name} must be int or float scalar")


def _verify_reduce_axes(axes: ArrayAttr, rank: int) -> list[int]:
    """校验归约 axes 并返回整数列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 axes 非空、元素唯一且在合法范围内。
    - 仅接受 i64 IntegerAttr 轴值。

    使用示例:
    - axes = _verify_reduce_axes(ArrayAttr([IntegerAttr(1, IntegerType(64))]), rank=3)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if len(axes.data) == 0:
        _raise_verify_error("axes-must-be-non-empty-unique-and-in-range")

    values: list[int] = []
    for entry in axes.data:
        if not isinstance(entry, IntegerAttr):
            _raise_verify_error("axes-must-be-non-empty-unique-and-in-range")
        width_attr = entry.type.width
        width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
        if width_value != 64:
            _raise_verify_error("axes-must-be-non-empty-unique-and-in-range")
        axis_value = entry.value.data
        if axis_value < 0 or axis_value >= rank:
            _raise_verify_error("axes-must-be-non-empty-unique-and-in-range")
        values.append(axis_value)

    if len(set(values)) != len(values):
        _raise_verify_error("axes-must-be-non-empty-unique-and-in-range")

    return values


def _verify_keepdim_attr(keepdim: IntegerAttr) -> bool:
    """校验 keepdim 的 i1 布尔属性并返回布尔值。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受 i1 IntegerAttr，且值必须为 0/1/-1（i1 真值可能以 -1 表示）。

    使用示例:
    - keep = _verify_keepdim_attr(IntegerAttr(1, IntegerType(1)))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if not isinstance(keepdim, IntegerAttr):
        _raise_verify_error("keepdim-must-be-i1-bool-attr")
    width_attr = keepdim.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 1:
        _raise_verify_error("keepdim-must-be-i1-bool-attr")
    value = keepdim.value.data
    if value not in (0, 1, -1):
        _raise_verify_error("keepdim-must-be-i1-bool-attr")
    return value != 0


def _build_reduce_result_shape(
    input_dims: Sequence[Attribute],
    axes: set[int],
    keepdim: bool,
) -> list[Attribute]:
    """构造归约结果的 shape 属性列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - keepdim=true 时将归约轴替换为 1。
    - keepdim=false 时移除归约轴；若结果 rank 为 0 则规范为 [1]。

    使用示例:
    - _build_reduce_result_shape([IntAttr(2), IntAttr(3)], {0}, keepdim=False)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if keepdim:
        return [IntAttr(1) if index in axes else dim for index, dim in enumerate(input_dims)]

    result_dims = [dim for index, dim in enumerate(input_dims) if index not in axes]
    if not result_dims:
        return [IntAttr(1)]
    return result_dims


def _verify_reduce_result_shape(result_type: NnMemoryType, expected_shape: Sequence[Attribute]) -> None:
    """校验归约结果 shape 合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 比较结果 shape 与期望 shape 的长度与逐维一致性。

    使用示例:
    - _verify_reduce_result_shape(result_type, expected_shape)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if len(result_type.shape.data) != len(expected_shape):
        _raise_verify_error("result-shape-must-match-reduce-contract")

    for expected_dim, actual_dim in zip(expected_shape, result_type.shape.data, strict=True):
        if not _dims_equal(expected_dim, actual_dim):
            _raise_verify_error("result-shape-must-match-reduce-contract")


def _verify_reduce_result_stride(result_type: NnMemoryType, expected_shape: Sequence[Attribute]) -> None:
    """校验归约结果 stride 必须为连续布局。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在结果 shape 静态可判定时校验 stride 等于连续布局。

    使用示例:
    - _verify_reduce_result_stride(result_type, expected_shape)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    expected_dims = _collect_int_dims(expected_shape)
    if expected_dims is None:
        return

    result_strides = _collect_int_dims(result_type.stride.data)
    if result_strides is None:
        _raise_verify_error("result-stride-must-be-contiguous-for-result-shape")

    expected_stride = _build_contiguous_stride(expected_dims)
    if result_strides != expected_stride:
        _raise_verify_error("result-stride-must-be-contiguous-for-result-shape")


def _verify_non_empty_reduction_extent(input_dims: Sequence[Attribute], axes: Sequence[int]) -> None:
    """校验静态归约轴的维度不为空。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对静态维度为 0 的归约轴直接报错。

    使用示例:
    - _verify_non_empty_reduction_extent([IntAttr(2), IntAttr(0)], [1])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    for axis in axes:
        dim = input_dims[axis]
        if isinstance(dim, IntAttr) and dim.data == 0:
            _raise_verify_error("empty-reduction-extent-must-be-rejected-when-static")


def _verify_reduce_op(op: "NnReduceSumOp | NnReduceMinOp | NnReduceMaxOp", *, require_non_empty: bool) -> None:
    """统一校验 nn.reduce_* 的结构化合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 input/result 类型、axes/keepdim、shape/stride 与空间一致性。
    - 按需检查静态空归约域错误路径。

    使用示例:
    - _verify_reduce_op(op, require_non_empty=True)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    input_type = op.input.type
    result_type = op.result.type
    if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
        _raise_verify_error("operand-must-be-nn-memory")
    input_type.verify()
    result_type.verify()

    axes = _verify_reduce_axes(op.axes, len(input_type.shape.data))
    keepdim = _verify_keepdim_attr(op.keepdim)

    if require_non_empty:
        _verify_non_empty_reduction_extent(input_type.shape.data, axes)

    if result_type.element_type != input_type.element_type:
        _raise_verify_error("result-element-type-must-match-input")

    op.space.verify()
    if input_type.space.space.data != result_type.space.space.data:
        _raise_verify_error("result-space-must-match-input-and-attr")
    if input_type.space.space.data != op.space.space.data:
        _raise_verify_error("result-space-must-match-input-and-attr")

    expected_shape = _build_reduce_result_shape(input_type.shape.data, set(axes), keepdim)
    _verify_reduce_result_shape(result_type, expected_shape)
    _verify_reduce_result_stride(result_type, expected_shape)


def _img2col_output_dim(
    input_dim: int,
    kernel: int,
    stride: int,
    dilation: int,
    pad_before: int,
    pad_after: int,
) -> int:
    """计算 img2col 输出维度。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 复用卷积输出维度公式并返回整数结果。

    使用示例:
    - _img2col_output_dim(8, 3, 1, 1, 1, 1)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    numerator = input_dim + pad_before + pad_after - dilation * (kernel - 1) - 1
    return numerator // stride + 1


class _BaseNnBinaryOp(IRDLOperation):
    """NN 二元 op 基类。"""

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化二元 op。"""

        super().__init__(
            operands=[lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class NnAddOp(_BaseNnBinaryOp):
    """nn.add。"""

    name = "nn.add"

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)

    def verify_(self) -> None:
        """校验 nn.add 的 memory/scalar 组合。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 memory+scalar/symbol 的 verifier 校验。

        使用示例:
        - NnAddOp(lhs, rhs, result_type, space).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        _verify_add_op(self)


@irdl_op_definition
class NnSubOp(_BaseNnBinaryOp):
    """nn.sub。"""

    name = "nn.sub"
    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)

    def verify_(self) -> None:
        _verify_mixed_scalar_binary_op(self, "nn.sub")


@irdl_op_definition
class NnMulOp(_BaseNnBinaryOp):
    """nn.mul。"""

    name = "nn.mul"
    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)

    def verify_(self) -> None:
        _verify_mixed_scalar_binary_op(self, "nn.mul")


@irdl_op_definition
class NnDivOp(_BaseNnBinaryOp):
    """nn.div。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.div 方言 op 与 verifier 约束。
    - 仅支持 memory + memory 形式，不支持隐式 broadcast。

    使用示例:
    - NnDivOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.div"

    def verify_(self) -> None:
        """校验 nn.div 的 verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用统一二元 memory verifier。

        使用示例:
        - NnDivOp(lhs, rhs, result_type, space).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        _verify_binary_memory_op(self, compare_result=False)


@irdl_op_definition
class NnTrueDivOp(_BaseNnBinaryOp):
    """nn.truediv。"""

    name = "nn.truediv"
    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)

    def verify_(self) -> None:
        _verify_mixed_scalar_binary_op(self, "nn.truediv")


@irdl_op_definition
class NnFloorDivOp(_BaseNnBinaryOp):
    """nn.floordiv。"""

    name = "nn.floordiv"

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)

    def verify_(self) -> None:
        _verify_mixed_scalar_binary_op(self, "nn.floordiv")


@irdl_op_definition
class NnEqOp(_BaseNnBinaryOp):
    """nn.eq。"""

    name = "nn.eq"

    def verify_(self) -> None:
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnNeOp(_BaseNnBinaryOp):
    """nn.ne。"""

    name = "nn.ne"

    def verify_(self) -> None:
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnLtOp(_BaseNnBinaryOp):
    """nn.lt。"""

    name = "nn.lt"

    def verify_(self) -> None:
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnLeOp(_BaseNnBinaryOp):
    """nn.le。"""

    name = "nn.le"

    def verify_(self) -> None:
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnGtOp(_BaseNnBinaryOp):
    """nn.gt。"""

    name = "nn.gt"

    def verify_(self) -> None:
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnGeOp(_BaseNnBinaryOp):
    """nn.ge。"""

    name = "nn.ge"

    def verify_(self) -> None:
        _verify_binary_memory_op(self, compare_result=True)


def _verify_select_op(op: "NnSelectOp") -> None:
    """校验 nn.select 的结构化合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 cond/lhs/rhs/result 均为 nn.memory。
    - cond element_type 必须为 i1。
    - lhs/rhs/result 的 shape/stride/space 必须一致。

    使用示例:
    - _verify_select_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    cond_type = _verify_memory_type(op.cond.type, "cond")
    lhs_type = _verify_memory_type(op.lhs.type, "lhs")
    rhs_type = _verify_memory_type(op.rhs.type, "rhs")
    result_type = _verify_memory_type(op.result.type, "result")

    if cond_type.element_type != i1:
        _raise_verify_error("nn.select cond element_type must be i1")

    op.space.verify()
    if lhs_type.space.space.data != rhs_type.space.space.data:
        _raise_verify_error("nn.select operands must use the same space")
    if lhs_type.space.space.data != op.space.space.data:
        _raise_verify_error("nn.select attribute space must match operand space")
    if result_type.space.space.data != op.space.space.data:
        _raise_verify_error("nn.select attribute space must match result space")

    if lhs_type.shape != rhs_type.shape or lhs_type.shape != result_type.shape:
        _raise_verify_error("nn.select shape must match across operands and result")
    if lhs_type.stride != rhs_type.stride or lhs_type.stride != result_type.stride:
        _raise_verify_error("nn.select stride must match across operands and result")
    if lhs_type.element_type != rhs_type.element_type:
        _raise_verify_error("nn.select operand element_type must match")
    if result_type.element_type != lhs_type.element_type:
        _raise_verify_error("nn.select result element_type must match operand element_type")


@irdl_op_definition
class NnSelectOp(IRDLOperation):
    """nn.select。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.select 方言 op 与 verifier 约束。

    使用示例:
    - NnSelectOp(cond, lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.select"

    cond = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        cond: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 nn.select op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定 cond/lhs/rhs、结果类型与 space。

        使用示例:
        - NnSelectOp(cond, lhs, rhs, result_type, space)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        super().__init__(
            operands=[cond, lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.select 的 verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 调用统一 select 校验逻辑。

        使用示例:
        - NnSelectOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        _verify_select_op(self)


def _verify_cast_op(op: "NnCastOp") -> None:
    """校验 nn.cast 的结构化合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 input/result 必须为 nn.memory。
    - shape/stride/space 必须一致，element_type 允许变化。

    使用示例:
    - _verify_cast_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    input_type = _verify_memory_type(op.input.type, "input")
    result_type = _verify_memory_type(op.result.type, "result")

    op.space.verify()
    if input_type.space.space.data != op.space.space.data:
        _raise_verify_error("nn.cast attribute space must match operand space")
    if result_type.space.space.data != op.space.space.data:
        _raise_verify_error("nn.cast attribute space must match result space")

    if input_type.shape != result_type.shape:
        _raise_verify_error("nn.cast shape must match input")
    if input_type.stride != result_type.stride:
        _raise_verify_error("nn.cast stride must match input")


@irdl_op_definition
class NnCastOp(IRDLOperation):
    """nn.cast。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.cast 方言 op 与 verifier 约束。

    使用示例:
    - NnCastOp(input_value, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.cast"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 nn.cast op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定输入、结果类型与 space。

        使用示例:
        - NnCastOp(input_value, result_type, space)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.cast 的 verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 调用统一 cast 校验逻辑。

        使用示例:
        - NnCastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        _verify_cast_op(self)


def _verify_matmul_shape(
    lhs_shape: Sequence[Attribute],
    rhs_shape: Sequence[Attribute],
    result_shape: Sequence[Attribute],
) -> None:
    """校验 matmul 的形状约束。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 matmul 的 rank=2 以及 contracting/result 维度约束。

    使用示例:
    - _verify_matmul_shape(lhs.shape.data, rhs.shape.data, result.shape.data)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(result_shape) != 2:
        _raise_verify_error("nn.matmul requires rank-2 memory types")

    if lhs_shape[1] != rhs_shape[0]:
        _raise_verify_error("nn.matmul contracting dimensions must match")

    if result_shape[0] != lhs_shape[0] or result_shape[1] != rhs_shape[1]:
        _raise_verify_error("nn.matmul result shape must match lhs/rhs")


def _verify_softmax_op(op: "NnSoftmaxOp") -> None:
    """校验 nn.softmax 的结构化合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验 operand/result 必须是 nn.memory，且 rank/axis 合法。
    - 校验 shape/stride/element_type/space 与 op 属性一致性。

    使用示例:
    - _verify_softmax_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    input_type = op.input.type
    result_type = op.result.type
    if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
        _raise_verify_error("operand-and-result-must-be-nn-memory")
    input_type.verify()
    result_type.verify()

    rank = len(input_type.shape.data)
    if rank <= 0:
        _raise_verify_error("input-rank-must-be-positive")
    axis_value = _verify_i64_attr(op.axis, "axis")
    if axis_value < -rank or axis_value >= rank:
        _raise_verify_error("axis-must-be-in-range")

    op.space.verify()
    if input_type.space.space.data != result_type.space.space.data:
        _raise_verify_error("result-space-must-match-input-and-attr")
    if input_type.space.space.data != op.space.space.data:
        _raise_verify_error("result-space-must-match-input-and-attr")

    if input_type.shape != result_type.shape:
        _raise_verify_error("result-shape-must-match-input")
    if input_type.stride != result_type.stride:
        _raise_verify_error("result-stride-must-match-input")

    if input_type.element_type != result_type.element_type or not _is_float_element_type(input_type.element_type):
        _raise_verify_error("result-element-type-must-match-input-and-be-float")


@irdl_op_definition
class NnSoftmaxOp(IRDLOperation):
    """nn.softmax。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.softmax 方言 op 与 verifier 约束。

    使用示例:
    - NnSoftmaxOp(inp, result_type, axis=-1, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.softmax"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    axis = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        axis: int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 softmax op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定输入、结果类型、axis 与 space 属性。
        - axis 会规整为 i64 IntegerAttr 以便 verifier 校验。

        使用示例:
        - NnSoftmaxOp(inp, result_type, axis=-1, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        axis_attr = _normalize_i64_attr(axis, "axis")
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"axis": axis_attr, "space": space},
        )

    def verify_(self) -> None:
        """校验 nn.softmax 的 verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 调用统一的 softmax 合同校验逻辑。

        使用示例:
        - NnSoftmaxOp(inp, result_type, axis=-1, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        _verify_softmax_op(self)


@irdl_op_definition
class NnBroadcastOp(IRDLOperation):
    """nn.broadcast。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表达 nn dialect 的显式 broadcast。
    - 按尾维对齐规则校验 shape 与 space/element_type 一致性。

    使用示例:
    - NnBroadcastOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.broadcast"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 broadcast op。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 绑定输入 operand、结果类型与 space 属性。

        使用示例:
        - NnBroadcastOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        input_type = self.input.type
        result_type = self.result.type
        if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
            _raise_verify_error("operand-must-be-nn-memory")
        input_type.verify()
        result_type.verify()

        self.space.verify()
        if input_type.space.space.data != result_type.space.space.data:
            _raise_verify_error("result-space-must-match-input-and-attr")
        if input_type.space.space.data != self.space.space.data:
            _raise_verify_error("result-space-must-match-input-and-attr")
        if input_type.element_type != result_type.element_type:
            _raise_verify_error("result-element-type-must-match-input")

        _verify_broadcast_compat(input_type, result_type)


@irdl_op_definition
class NnTransposeOp(IRDLOperation):
    """nn.transpose。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 定义 nn.transpose 方言 op 与 verifier 约束。

    使用示例:
    - NnTransposeOp(inp, result_type, perm=[1, 0], space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.transpose"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    perm = attr_def(ArrayAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        perm: Sequence[int] | ArrayAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 transpose op。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 绑定输入、结果类型、perm 与 space 属性。

        使用示例:
        - NnTransposeOp(inp, result_type, perm=[1, 0], space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        perm_attr = perm if isinstance(perm, ArrayAttr) else ArrayAttr([IntAttr(value) for value in perm])
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"perm": perm_attr, "space": space},
        )

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        result_type = _verify_memory_type(self.result.type, "result")

        self.space.verify()
        if input_type.space.space.data != result_type.space.space.data:
            _raise_verify_error("nn.transpose input/result must use the same space")
        if input_type.space.space.data != self.space.space.data:
            _raise_verify_error("nn.transpose attribute space must match type space")

        if input_type.element_type != result_type.element_type:
            _raise_verify_error("nn.transpose element_type must match")

        perm_values = _verify_transpose_perm(self.perm, len(input_type.shape.data))
        _verify_transpose_layout(input_type, result_type, perm_values)


@irdl_op_definition
class NnReluOp(IRDLOperation):
    """nn.relu。"""

    name = "nn.relu"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(self, input_value: SSAValue | Operation, result_type: NnMemoryType, space: NnMemorySpaceAttr) -> None:
        super().__init__(operands=[input_value], result_types=[result_type], attributes={"space": space})

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        result_type = _verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)


@irdl_op_definition
class NnSigmoidOp(IRDLOperation):
    """nn.sigmoid。"""

    name = "nn.sigmoid"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(self, input_value: SSAValue | Operation, result_type: NnMemoryType, space: NnMemorySpaceAttr) -> None:
        super().__init__(operands=[input_value], result_types=[result_type], attributes={"space": space})

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        result_type = _verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)


@irdl_op_definition
class NnTanhOp(IRDLOperation):
    """nn.tanh。"""

    name = "nn.tanh"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(self, input_value: SSAValue | Operation, result_type: NnMemoryType, space: NnMemorySpaceAttr) -> None:
        super().__init__(operands=[input_value], result_types=[result_type], attributes={"space": space})

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        result_type = _verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)


@irdl_op_definition
class NnLeakyReluOp(IRDLOperation):
    """nn.leaky_relu。"""

    name = "nn.leaky_relu"

    input = operand_def(NnMemoryType)
    alpha = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        alpha: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(operands=[input_value, alpha], result_types=[result_type], attributes={"space": space})

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        result_type = _verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)
        _verify_activation_scalar_operand(SSAValue.get(self.alpha), "alpha")


@irdl_op_definition
class NnHardSigmoidOp(IRDLOperation):
    """nn.hard_sigmoid。"""

    name = "nn.hard_sigmoid"

    input = operand_def(NnMemoryType)
    alpha = operand_def(Attribute)
    beta = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        alpha: SSAValue | Operation,
        beta: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[input_value, alpha, beta],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        input_type = _verify_memory_type(self.input.type, "input")
        result_type = _verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)
        _verify_activation_scalar_operand(SSAValue.get(self.alpha), "alpha")
        _verify_activation_scalar_operand(SSAValue.get(self.beta), "beta")


@irdl_op_definition
class NnExpOp(IRDLOperation):
    """nn.exp。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.exp 方言 op 与 verifier 约束。

    使用示例:
    - NnExpOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.exp"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 exp op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定输入、结果类型与 space 属性。

        使用示例:
        - NnExpOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.exp verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 调用统一的 nn.exp 合同校验逻辑。

        使用示例:
        - NnExpOp(inp, result_type, NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        _verify_exp_op(self)


@irdl_op_definition
class NnReduceSumOp(IRDLOperation):
    """nn.reduce_sum。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.reduce_sum 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.reduce_sum"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    axes = attr_def(ArrayAttr)
    keepdim = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        axes: Sequence[int] | ArrayAttr,
        keepdim: bool | int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 reduce_sum op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        axes_attr = _normalize_axes_attr(axes)
        keepdim_attr = _normalize_bool_attr(keepdim, "keepdim")
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={
                "axes": axes_attr,
                "keepdim": keepdim_attr,
                "space": space,
            },
        )

    def verify_(self) -> None:
        """校验 nn.reduce_sum verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 调用统一的归约合同校验逻辑。

        使用示例:
        - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        _verify_reduce_op(self, require_non_empty=False)


@irdl_op_definition
class NnReduceMinOp(IRDLOperation):
    """nn.reduce_min。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.reduce_min 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.reduce_min"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    axes = attr_def(ArrayAttr)
    keepdim = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        axes: Sequence[int] | ArrayAttr,
        keepdim: bool | int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 reduce_min op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        axes_attr = _normalize_axes_attr(axes)
        keepdim_attr = _normalize_bool_attr(keepdim, "keepdim")
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={
                "axes": axes_attr,
                "keepdim": keepdim_attr,
                "space": space,
            },
        )

    def verify_(self) -> None:
        """校验 nn.reduce_min verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 调用归约合同校验逻辑，并拒绝静态空归约域。

        使用示例:
        - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        _verify_reduce_op(self, require_non_empty=True)


@irdl_op_definition
class NnReduceMaxOp(IRDLOperation):
    """nn.reduce_max。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.reduce_max 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.reduce_max"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    axes = attr_def(ArrayAttr)
    keepdim = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        axes: Sequence[int] | ArrayAttr,
        keepdim: bool | int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 reduce_max op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        axes_attr = _normalize_axes_attr(axes)
        keepdim_attr = _normalize_bool_attr(keepdim, "keepdim")
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={
                "axes": axes_attr,
                "keepdim": keepdim_attr,
                "space": space,
            },
        )

    def verify_(self) -> None:
        """校验 nn.reduce_max verifier 合同。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 调用归约合同校验逻辑，并拒绝静态空归约域。

        使用示例:
        - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """
        _verify_reduce_op(self, require_non_empty=True)


@irdl_op_definition
class NnImg2col1dOp(IRDLOperation):
    """nn.img2col1d。

    创建者: jcc你莫辜负
    最后一次更改: 大闸蟹

    功能说明:
    - 定义一维 img2col 方言 op 与 verifier 约束。

    使用示例:
    - NnImg2col1dOp(inp, result_type, kw_value, sw_value, dw_value, pl_value, pr_value, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.img2col1d"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    kw = operand_def(Attribute)
    sw = operand_def(Attribute)
    dw = operand_def(Attribute)
    pl = operand_def(Attribute)
    pr = operand_def(Attribute)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        kw: SSAValue | Operation,
        sw: SSAValue | Operation,
        dw: SSAValue | Operation,
        pl: SSAValue | Operation,
        pr: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col1d op。

        创建者: jcc你莫辜负
        最后一次更改: 大闸蟹

        功能说明:
        - 绑定输入 operand、结果类型、窗口参数 operand 与 space 属性。

        使用示例:
        - NnImg2col1dOp(inp, result_type, kw_value, sw_value, dw_value, pl_value, pr_value, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        super().__init__(
            operands=[input_value, kw, sw, dw, pl, pr],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.img2col1d。

        创建者: jcc你莫辜负
        最后一次更改: 大闸蟹

        功能说明:
        - 校验 operand rank、窗口参数 operand 合法性、result rank/type/space 与合同约束。

        使用示例:
        - NnImg2col1dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        input_type = self.input.type
        result_type = self.result.type
        if not isinstance(input_type, NnMemoryType):
            _raise_verify_error("operand-must-be-rank-3-nn-memory")
        if not isinstance(result_type, NnMemoryType):
            _raise_verify_error("result-rank-must-be-4")
        input_type.verify()
        result_type.verify()

        if len(input_type.shape.data) != 3:
            _raise_verify_error("operand-must-be-rank-3-nn-memory")
        if len(result_type.shape.data) != 4:
            _raise_verify_error("result-rank-must-be-4")

        kw_value, sw_value, dw_value = _verify_img2col_param_operands(
            [self.kw, self.sw, self.dw],
            allow_zero=False,
            type_error_phrase="kw-sw-dw-must-be-int-or-symbol",
            value_error_phrase="kw-sw-dw-must-be-positive",
        )
        pl_value, pr_value = _verify_img2col_param_operands(
            [self.pl, self.pr],
            allow_zero=True,
            type_error_phrase="pl-pr-must-be-int-or-symbol",
            value_error_phrase="pl-pr-must-be-non-negative",
        )

        self.space.verify()
        if input_type.space.space.data != self.space.space.data:
            _raise_verify_error("result-space-matches-input")
        if result_type.space.space.data != input_type.space.space.data:
            _raise_verify_error("result-space-matches-input")
        if result_type.element_type != input_type.element_type:
            _raise_verify_error("result-element-type-matches-input")

        input_dims = _collect_int_dims(input_type.shape.data)
        result_dims = _collect_int_dims(result_type.shape.data)
        if input_dims is None or result_dims is None:
            return
        if any(value is None for value in (kw_value, sw_value, dw_value, pl_value, pr_value)):
            return

        n_dim, c_dim, w_dim = input_dims
        w_out = _img2col_output_dim(w_dim, kw_value, sw_value, dw_value, pl_value, pr_value)
        if w_out <= 0:
            _raise_verify_error("result-shape-stride-must-match-img2col1d-contract")

        expected_shape = [n_dim, c_dim, kw_value, w_out]
        if result_dims != expected_shape:
            _raise_verify_error("result-shape-stride-must-match-img2col1d-contract")

        result_strides = _collect_int_dims(result_type.stride.data)
        if result_strides is None:
            _raise_verify_error("result-shape-stride-must-match-img2col1d-contract")
        expected_stride = _build_contiguous_stride(expected_shape)
        if result_strides != expected_stride:
            _raise_verify_error("result-shape-stride-must-match-img2col1d-contract")


@irdl_op_definition
class NnImg2col2dOp(IRDLOperation):
    """nn.img2col2d。

    创建者: jcc你莫辜负
    最后一次更改: 大闸蟹

    功能说明:
    - 定义二维 img2col 方言 op 与 verifier 约束。

    使用示例:
    - NnImg2col2dOp(inp, result_type, kh_value, kw_value, sh_value, sw_value, dh_value, dw_value, ph_value, pw_value, pl_value, pr_value, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.img2col2d"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    kh = operand_def(Attribute)
    kw = operand_def(Attribute)
    sh = operand_def(Attribute)
    sw = operand_def(Attribute)
    dh = operand_def(Attribute)
    dw = operand_def(Attribute)
    ph = operand_def(Attribute)
    pw = operand_def(Attribute)
    pl = operand_def(Attribute)
    pr = operand_def(Attribute)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        kh: SSAValue | Operation,
        kw: SSAValue | Operation,
        sh: SSAValue | Operation,
        sw: SSAValue | Operation,
        dh: SSAValue | Operation,
        dw: SSAValue | Operation,
        ph: SSAValue | Operation,
        pw: SSAValue | Operation,
        pl: SSAValue | Operation,
        pr: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col2d op。

        创建者: jcc你莫辜负
        最后一次更改: 大闸蟹

        功能说明:
        - 绑定输入 operand、结果类型、窗口参数 operand 与 space 属性。

        使用示例:
        - NnImg2col2dOp(inp, result_type, kh_value, kw_value, sh_value, sw_value, dh_value, dw_value, ph_value, pw_value, pl_value, pr_value, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        super().__init__(
            operands=[input_value, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.img2col2d。

        创建者: jcc你莫辜负
        最后一次更改: 大闸蟹

        功能说明:
        - 校验 operand rank、窗口参数 operand 合法性、result rank/type/space 与合同约束。

        使用示例:
        - NnImg2col2dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        input_type = self.input.type
        result_type = self.result.type
        if not isinstance(input_type, NnMemoryType):
            _raise_verify_error("operand-must-be-rank-4-nn-memory")
        if not isinstance(result_type, NnMemoryType):
            _raise_verify_error("result-rank-must-be-6")
        input_type.verify()
        result_type.verify()

        if len(input_type.shape.data) != 4:
            _raise_verify_error("operand-must-be-rank-4-nn-memory")
        if len(result_type.shape.data) != 6:
            _raise_verify_error("result-rank-must-be-6")

        kh_value, kw_value, sh_value, sw_value, dh_value, dw_value = _verify_img2col_param_operands(
            [self.kh, self.kw, self.sh, self.sw, self.dh, self.dw],
            allow_zero=False,
            type_error_phrase="kh-kw-sh-sw-dh-dw-must-be-int-or-symbol",
            value_error_phrase="kh-kw-sh-sw-dh-dw-must-be-positive",
        )
        ph_value, pw_value, pl_value, pr_value = _verify_img2col_param_operands(
            [self.ph, self.pw, self.pl, self.pr],
            allow_zero=True,
            type_error_phrase="ph-pw-pl-pr-must-be-int-or-symbol",
            value_error_phrase="ph-pw-pl-pr-must-be-non-negative",
        )

        self.space.verify()
        if input_type.space.space.data != self.space.space.data:
            _raise_verify_error("result-space-matches-input")
        if result_type.space.space.data != input_type.space.space.data:
            _raise_verify_error("result-space-matches-input")
        if result_type.element_type != input_type.element_type:
            _raise_verify_error("result-element-type-matches-input")

        input_dims = _collect_int_dims(input_type.shape.data)
        result_dims = _collect_int_dims(result_type.shape.data)
        if input_dims is None or result_dims is None:
            return
        if any(
            value is None
            for value in (
                kh_value,
                kw_value,
                sh_value,
                sw_value,
                dh_value,
                dw_value,
                ph_value,
                pw_value,
                pl_value,
                pr_value,
            )
        ):
            return

        n_dim, c_dim, h_dim, w_dim = input_dims
        h_out = _img2col_output_dim(h_dim, kh_value, sh_value, dh_value, ph_value, pw_value)
        w_out = _img2col_output_dim(w_dim, kw_value, sw_value, dw_value, pl_value, pr_value)
        if h_out <= 0:
            _raise_verify_error("result-shape-stride-must-match-img2col2d-contract")
        if w_out <= 0:
            _raise_verify_error("result-shape-stride-must-match-img2col2d-contract")

        expected_shape = [n_dim, c_dim, kh_value, kw_value, h_out, w_out]
        if result_dims != expected_shape:
            _raise_verify_error("result-shape-stride-must-match-img2col2d-contract")

        result_strides = _collect_int_dims(result_type.stride.data)
        if result_strides is None:
            _raise_verify_error("result-shape-stride-must-match-img2col2d-contract")
        expected_stride = _build_contiguous_stride(expected_shape)
        if result_strides != expected_stride:
            _raise_verify_error("result-shape-stride-must-match-img2col2d-contract")


@irdl_op_definition
class NnMatmulOp(IRDLOperation):
    """nn.matmul。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 定义 nn.matmul 方言 op 与 verifier 约束。

    使用示例:
    - NnMatmulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    name = "nn.matmul"

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 matmul op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 构造 nn.matmul op 并绑定 operands/attributes。

        使用示例:
        - NnMatmulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: kernel_gen/dialect/nn.py
        """

        super().__init__(
            operands=[lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        lhs_type = _verify_memory_type(self.lhs.type, "lhs")
        rhs_type = _verify_memory_type(self.rhs.type, "rhs")
        result_type = _verify_memory_type(self.result.type, "result")

        self.space.verify()
        if lhs_type.space.space.data != rhs_type.space.space.data:
            _raise_verify_error("nn.matmul operands must use the same space")
        if lhs_type.space.space.data != self.space.space.data:
            _raise_verify_error("nn.matmul attribute space must match operand space")
        if result_type.space.space.data != self.space.space.data:
            _raise_verify_error("nn.matmul attribute space must match result space")

        _verify_matmul_shape(lhs_type.shape.data, rhs_type.shape.data, result_type.shape.data)

        if lhs_type.element_type != rhs_type.element_type or lhs_type.element_type != result_type.element_type:
            _raise_verify_error("nn.matmul operand/result element_type must match")


Nn = Dialect(
    "nn",
    [
        NnAddOp,
        NnSubOp,
        NnMulOp,
        NnDivOp,
        NnTrueDivOp,
        NnFloorDivOp,
        NnEqOp,
        NnNeOp,
        NnLtOp,
        NnLeOp,
        NnGtOp,
        NnGeOp,
        NnSelectOp,
        NnCastOp,
        NnBroadcastOp,
        NnTransposeOp,
        NnReluOp,
        NnSigmoidOp,
        NnTanhOp,
        NnLeakyReluOp,
        NnHardSigmoidOp,
        NnSoftmaxOp,
        NnExpOp,
        NnReduceSumOp,
        NnReduceMinOp,
        NnReduceMaxOp,
        NnImg2col1dOp,
        NnImg2col2dOp,
        NnMatmulOp,
    ],
    [
        NnMemorySpaceAttr,
        NnMemoryType,
    ],
)

__all__ = [
    "Nn",
    "NnAddOp",
    "NnSubOp",
    "NnMulOp",
    "NnDivOp",
    "NnTrueDivOp",
    "NnFloorDivOp",
    "NnEqOp",
    "NnNeOp",
    "NnLtOp",
    "NnLeOp",
    "NnGtOp",
    "NnGeOp",
    "NnSelectOp",
    "NnCastOp",
    "NnBroadcastOp",
    "NnTransposeOp",
    "NnReluOp",
    "NnSigmoidOp",
    "NnTanhOp",
    "NnLeakyReluOp",
    "NnHardSigmoidOp",
    "NnSoftmaxOp",
    "NnExpOp",
    "NnReduceSumOp",
    "NnReduceMinOp",
    "NnReduceMaxOp",
    "NnImg2col1dOp",
    "NnImg2col2dOp",
    "NnMatmulOp",
    "NnMemorySpaceAttr",
    "NnMemoryType",
]
