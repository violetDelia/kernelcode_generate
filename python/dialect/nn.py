"""NN dialect definitions.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 定义 nn dialect 的 memory type、space attribute 与逐元素二元 op。

使用示例:
- from python.dialect.nn import Nn, NnAddOp, NnMemorySpaceAttr, NnMemoryType

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/test_nn_dialect.py
- 功能实现: python/dialect/nn.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerType, StringAttr, i1
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

_VALID_SPACES = {"global", "shared", "local"}


def _parse_dim_list(parser: AttrParser) -> ArrayAttr[Attribute]:
    """解析 shape 或 stride 维度列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持非负整数、`?` 与符号标识符。

    使用示例:
    - _parse_dim_list(parser)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: python/dialect/nn.py
    """

    dims: list[Attribute] = []
    parser.parse_punctuation("[", "Expected dimension list.")
    if parser.parse_optional_punctuation("]") is not None:
        return ArrayAttr(dims)

    while True:
        if parser.parse_optional_punctuation("?") is not None:
            dims.append(StringAttr("?"))
        else:
            integer = parser.parse_optional_integer(allow_boolean=False, allow_negative=False)
            if integer is not None:
                dims.append(IntAttr(integer))
            else:
                dims.append(StringAttr(parser.parse_identifier("Expected dimension symbol.")))

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
    - 功能实现: python/dialect/nn.py
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
            raise VerifyException("Dimension list only supports IntAttr or StringAttr")
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
    - 功能实现: python/dialect/nn.py
    """

    if isinstance(dim, IntAttr):
        if dim.data < 0:
            raise VerifyException(f"{field_name} dimensions must be non-negative")
        return

    if isinstance(dim, StringAttr) and dim.data:
        return

    raise VerifyException(f"{field_name} dimensions must be IntAttr or StringAttr")


@irdl_attr_definition
class NnMemorySpaceAttr(ParametrizedAttribute):
    """NN memory space attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 显式建模 `global`、`shared`、`local` 三种 memory space。

    使用示例:
    - NnMemorySpaceAttr(StringAttr(\"global\"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: python/dialect/nn.py
    """

    name = "nn.space"

    space: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析 space attribute 参数。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 解析 `#nn.space<...>` 中的 space 标识符。

        使用示例:
        - NnMemorySpaceAttr.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """

        parser.parse_punctuation("<", "Expected '<' for nn space attribute.")
        space = StringAttr(parser.parse_identifier("Expected nn memory space identifier."))
        parser.parse_punctuation(">", "Expected '>' for nn space attribute.")
        return (space,)

    def print_parameters(self, printer: Printer) -> None:
        """打印 space attribute 参数。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 以 `#nn.space<...>` 形式输出 space 标识。

        使用示例:
        - space_attr.print_parameters(printer)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """

        printer.print_string("<")
        printer.print_string(self.space.data)
        printer.print_string(">")

    def verify(self) -> None:
        """校验 space attribute。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 仅允许 `global/shared/local` 三种值。

        使用示例:
        - NnMemorySpaceAttr.from_name("global").verify()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """

        if self.space.data not in _VALID_SPACES:
            raise VerifyException("nn space must be one of global/shared/local")

    @classmethod
    def from_name(cls, space: str) -> "NnMemorySpaceAttr":
        """从字符串构造 space attribute。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 简化 `global/shared/local` 的构造。

        使用示例:
        - NnMemorySpaceAttr.from_name(\"global\")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
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
    - 功能实现: python/dialect/nn.py
    """

    name = "nn.memory"

    shape: ArrayAttr[Attribute] = param_def(ArrayAttr[Attribute])
    stride: ArrayAttr[Attribute] = param_def(ArrayAttr[Attribute])
    element_type: Attribute = param_def(Attribute)
    space: NnMemorySpaceAttr = param_def(NnMemorySpaceAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析 memory type 参数。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 解析 `!nn.memory<shape, stride, element_type, space>` 文本。

        使用示例:
        - NnMemoryType.parse_parameters(parser)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """

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
            raise VerifyException("nn memory type space must be #nn.space<...>")
        return (shape, stride, element_type, space)

    def print_parameters(self, printer: Printer) -> None:
        """打印 memory type 参数。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 按 `!nn.memory<...>` 格式输出四字段信息。

        使用示例:
        - memory_type.print_parameters(printer)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """

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
        """校验 memory type。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 校验 shape/stride rank、维度合法性与 space 取值。

        使用示例:
        - NnMemoryType(...).verify()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """

        self.space.verify()
        if not isinstance(self.element_type, TypeAttribute):
            raise VerifyException("nn memory element_type must be a type attribute")
        if len(self.shape.data) != len(self.stride.data):
            raise VerifyException("nn memory shape and stride rank must match")

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
                raise VerifyException("stride '?' requires corresponding shape dimension to be symbol or integer")


def _verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 memory type。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确认类型为 `nn.memory` 并触发类型校验。

    使用示例:
    - _verify_memory_type(op.lhs.type, "lhs")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: python/dialect/nn.py
    """

    if not isinstance(value, NnMemoryType):
        raise VerifyException(f"{field_name} must be nn.memory")
    value.verify()
    return value


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
    - 功能实现: python/dialect/nn.py
    """

    lhs_type = _verify_memory_type(op.lhs.type, "lhs")
    rhs_type = _verify_memory_type(op.rhs.type, "rhs")
    result_type = _verify_memory_type(op.result.type, "result")

    op.space.verify()
    if lhs_type.space.space.data != rhs_type.space.space.data:
        raise VerifyException("nn op operands must use the same space")
    if lhs_type.space.space.data != op.space.space.data:
        raise VerifyException("nn op attribute space must match operand space")
    if result_type.space.space.data != op.space.space.data:
        raise VerifyException("nn op attribute space must match result space")

    if lhs_type.shape != rhs_type.shape or lhs_type.shape != result_type.shape:
        raise VerifyException("nn op shape must match across operands and result")
    if lhs_type.stride != rhs_type.stride or lhs_type.stride != result_type.stride:
        raise VerifyException("nn op stride must match across operands and result")
    if lhs_type.element_type != rhs_type.element_type:
        raise VerifyException("nn op operand element_type must match")

    if compare_result:
        if result_type.element_type != i1:
            raise VerifyException("nn compare result element_type must be i1")
    elif result_type.element_type != lhs_type.element_type:
        raise VerifyException("nn arithmetic result element_type must match operand element_type")


class _BaseNnBinaryOp(IRDLOperation):
    """NN 二元 op 基类。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一定义 lhs/rhs/result 与 space attribute。

    使用示例:
    - class NnAddOp(_BaseNnBinaryOp): ...

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: python/dialect/nn.py
    """

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
        """初始化二元 op。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 operand、result 与 space attribute。

        使用示例:
        - NnAddOp(lhs, rhs, result_type, space)

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """

        super().__init__(
            operands=[lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class NnAddOp(_BaseNnBinaryOp):
    """nn.add。"""

    name = "nn.add"

    def verify_(self) -> None:
        """校验 nn.add。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑。

        使用示例:
        - NnAddOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=False)


@irdl_op_definition
class NnSubOp(_BaseNnBinaryOp):
    """nn.sub。"""

    name = "nn.sub"

    def verify_(self) -> None:
        """校验 nn.sub。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑。

        使用示例:
        - NnSubOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=False)


@irdl_op_definition
class NnMulOp(_BaseNnBinaryOp):
    """nn.mul。"""

    name = "nn.mul"

    def verify_(self) -> None:
        """校验 nn.mul。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑。

        使用示例:
        - NnMulOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=False)


@irdl_op_definition
class NnTrueDivOp(_BaseNnBinaryOp):
    """nn.truediv。"""

    name = "nn.truediv"

    def verify_(self) -> None:
        """校验 nn.truediv。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑。

        使用示例:
        - NnTrueDivOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=False)


@irdl_op_definition
class NnEqOp(_BaseNnBinaryOp):
    """nn.eq。"""

    name = "nn.eq"

    def verify_(self) -> None:
        """校验 nn.eq。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑（compare）。

        使用示例:
        - NnEqOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnNeOp(_BaseNnBinaryOp):
    """nn.ne。"""

    name = "nn.ne"

    def verify_(self) -> None:
        """校验 nn.ne。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑（compare）。

        使用示例:
        - NnNeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnLtOp(_BaseNnBinaryOp):
    """nn.lt。"""

    name = "nn.lt"

    def verify_(self) -> None:
        """校验 nn.lt。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑（compare）。

        使用示例:
        - NnLtOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnLeOp(_BaseNnBinaryOp):
    """nn.le。"""

    name = "nn.le"

    def verify_(self) -> None:
        """校验 nn.le。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑（compare）。

        使用示例:
        - NnLeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnGtOp(_BaseNnBinaryOp):
    """nn.gt。"""

    name = "nn.gt"

    def verify_(self) -> None:
        """校验 nn.gt。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑（compare）。

        使用示例:
        - NnGtOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=True)


@irdl_op_definition
class NnGeOp(_BaseNnBinaryOp):
    """nn.ge。"""

    name = "nn.ge"

    def verify_(self) -> None:
        """校验 nn.ge。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复用 nn 二元 op 校验逻辑（compare）。

        使用示例:
        - NnGeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/test_nn_dialect.py
        - 功能实现: python/dialect/nn.py
        """
        _verify_binary_memory_op(self, compare_result=True)


Nn = Dialect(
    "nn",
    [
        NnAddOp,
        NnSubOp,
        NnMulOp,
        NnTrueDivOp,
        NnEqOp,
        NnNeOp,
        NnLtOp,
        NnLeOp,
        NnGtOp,
        NnGeOp,
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
    "NnTrueDivOp",
    "NnEqOp",
    "NnNeOp",
    "NnLtOp",
    "NnLeOp",
    "NnGtOp",
    "NnGeOp",
    "NnMemorySpaceAttr",
    "NnMemoryType",
]
