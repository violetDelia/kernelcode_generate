"""nn reduce operations.

功能说明:
- 承载 nn dialect package 拆分后的 nn reduce operations 实现。

API 列表:
- `class NnReduceSumOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnReduceMinOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnReduceMaxOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`

使用示例:
- from kernel_gen.dialect.nn import NnReduceSumOp

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_operation_reduce.py
- 功能实现: kernel_gen/dialect/nn/operation/reduce.py
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.dialect.nn.attr.space_attr import NnMemorySpaceAttr
from kernel_gen.dialect.nn.common import (
    build_contiguous_stride,
    dims_equal,
    normalize_axes_attr,
    normalize_bool_attr,
    raise_verify_error,
)
from kernel_gen.dialect.nn.type.memory_type import NnMemoryType
from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, result_def

def _symbol_expr_attr_from_expr(expr: str) -> Attribute:
    """构造公开 SymbolExprAttr。

    功能说明:
    - 延迟导入 `SymbolExprAttr`，避免 nn/symbol 模块初始化互相依赖。

    使用示例:
    - _symbol_expr_attr_from_expr("N")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    from kernel_gen.dialect.symbol import SymbolExprAttr

    return SymbolExprAttr.from_expr(expr)

def _is_symbol_expr_attr(attr: Attribute) -> bool:
    """判断属性是否是公开 SymbolExprAttr。

    功能说明:
    - 通过延迟导入的公开 class 判断 memory shape/stride 条目。

    使用示例:
    - _is_symbol_expr_attr(SymbolExprAttr.from_expr("N"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    from kernel_gen.dialect.symbol import SymbolExprAttr

    return isinstance(attr, SymbolExprAttr)

def _dim_expr_text(dim: Attribute) -> str:
    """读取 SymbolExprAttr 的规范表达式文本。

    功能说明:
    - 统一 shape/stride 的比较、静态求值和 stride 推导入口。

    使用示例:
    - _dim_expr_text(SymbolExprAttr.from_expr("N + 1"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if not _is_symbol_expr_attr(dim):
        raise_verify_error("dimension entries must be SymbolExprAttr")
    dim.verify()
    return dim.expr.data

def _static_int_from_expr_text(expr: str) -> int | None:
    """尝试从规范表达式文本提取静态整数。

    功能说明:
    - 仅识别十进制整数字面量，动态表达式返回 None。

    使用示例:
    - _static_int_from_expr_text("4")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    signless = expr[1:] if expr.startswith("-") else expr
    if signless.isdecimal():
        return int(expr)
    return None

def _static_int_from_dim(dim: Attribute) -> int | None:
    """尝试从 SymbolExprAttr 维度提取静态整数。

    功能说明:
    - 对 `#symbol.expr<4>` 返回 4；动态维度返回 None。

    使用示例:
    - _static_int_from_dim(SymbolExprAttr.from_expr("4"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    return _static_int_from_expr_text(_dim_expr_text(dim))

def _collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None:
    """提取维度中的整数值列表。


    功能说明:
    - 仅当所有维度均为静态整数 SymbolExprAttr 时返回整数列表。
    - 任何动态 SymbolExprAttr 维度返回 None，表示无法进行数值合同校验。

    使用示例:
    - _collect_int_dims([SymbolExprAttr.from_expr("1"), SymbolExprAttr.from_expr("2")])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    values: list[int] = []
    for dim in dims:
        value = _static_int_from_dim(dim)
        if value is None:
            return None
        values.append(value)
    return values

def _verify_reduce_axes(axes: ArrayAttr, rank: int) -> list[int]:
    """校验归约 axes 并返回整数列表。


    功能说明:
    - 校验 axes 非空、元素唯一且在合法范围内。
    - 仅接受 i64 IntegerAttr 轴值。

    使用示例:
    - axes = _verify_reduce_axes(ArrayAttr([IntegerAttr(1, IntegerType(64))]), rank=3)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if len(axes.data) == 0:
        raise_verify_error("axes-must-be-non-empty-unique-and-in-range")

    values: list[int] = []
    for entry in axes.data:
        if not isinstance(entry, IntegerAttr):
            raise_verify_error("axes-must-be-non-empty-unique-and-in-range")
        width_attr = entry.type.width
        width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
        if width_value != 64:
            raise_verify_error("axes-must-be-non-empty-unique-and-in-range")
        axis_value = entry.value.data
        if axis_value < 0 or axis_value >= rank:
            raise_verify_error("axes-must-be-non-empty-unique-and-in-range")
        values.append(axis_value)

    if len(set(values)) != len(values):
        raise_verify_error("axes-must-be-non-empty-unique-and-in-range")

    return values

def _verify_keepdim_attr(keepdim: IntegerAttr) -> bool:
    """校验 keepdim 的 i1 布尔属性并返回布尔值。


    功能说明:
    - 仅接受 i1 IntegerAttr，且值必须为 0/1/-1（i1 真值可能以 -1 表示）。

    使用示例:
    - keep = _verify_keepdim_attr(IntegerAttr(1, IntegerType(1)))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if not isinstance(keepdim, IntegerAttr):
        raise_verify_error("keepdim-must-be-i1-bool-attr")
    width_attr = keepdim.type.width
    width_value = width_attr.data if isinstance(width_attr, IntAttr) else width_attr
    if width_value != 1:
        raise_verify_error("keepdim-must-be-i1-bool-attr")
    value = keepdim.value.data
    if value not in (0, 1, -1):
        raise_verify_error("keepdim-must-be-i1-bool-attr")
    return value != 0

def _build_reduce_result_shape(
    input_dims: Sequence[Attribute],
    axes: set[int],
    keepdim: bool,
) -> list[Attribute]:
    """构造归约结果的 shape 属性列表。


    功能说明:
    - keepdim=true 时将归约轴替换为 1。
    - keepdim=false 时移除归约轴；若结果 rank 为 0 则规范为 [1]。

    使用示例:
    - _build_reduce_result_shape([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("3")], {0}, keepdim=False)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if keepdim:
        one = _symbol_expr_attr_from_expr("1")
        return [one if index in axes else dim for index, dim in enumerate(input_dims)]

    result_dims = [dim for index, dim in enumerate(input_dims) if index not in axes]
    if not result_dims:
        return [_symbol_expr_attr_from_expr("1")]
    return result_dims

def _verify_reduce_result_shape(result_type: NnMemoryType, expected_shape: Sequence[Attribute]) -> None:
    """校验归约结果 shape 合同。


    功能说明:
    - 比较结果 shape 与期望 shape 的长度与逐维一致性。

    使用示例:
    - _verify_reduce_result_shape(result_type, expected_shape)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if len(result_type.shape.data) != len(expected_shape):
        raise_verify_error("result-shape-must-match-reduce-contract")

    for expected_dim, actual_dim in zip(expected_shape, result_type.shape.data, strict=True):
        if not dims_equal(expected_dim, actual_dim):
            raise_verify_error("result-shape-must-match-reduce-contract")

def _verify_reduce_result_stride(result_type: NnMemoryType, expected_shape: Sequence[Attribute]) -> None:
    """校验归约结果 stride 必须为连续布局。


    功能说明:
    - 仅在结果 shape 静态可判定时校验 stride 等于连续布局。

    使用示例:
    - _verify_reduce_result_stride(result_type, expected_shape)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    expected_dims = _collect_int_dims(expected_shape)
    if expected_dims is None:
        return

    result_strides = _collect_int_dims(result_type.stride.data)
    if result_strides is None:
        raise_verify_error("result-stride-must-be-contiguous-for-result-shape")

    expected_stride = build_contiguous_stride(expected_dims)
    if result_strides != expected_stride:
        raise_verify_error("result-stride-must-be-contiguous-for-result-shape")

def _verify_non_empty_reduction_extent(input_dims: Sequence[Attribute], axes: Sequence[int]) -> None:
    """校验静态归约轴的维度不为空。


    功能说明:
    - 对静态维度为 0 的归约轴直接报错。

    使用示例:
    - _verify_non_empty_reduction_extent([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("0")], [1])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    for axis in axes:
        dim = input_dims[axis]
        if _static_int_from_dim(dim) == 0:
            raise_verify_error("empty-reduction-extent-must-be-rejected-when-static")

def _verify_reduce_op(op: "NnReduceSumOp | NnReduceMinOp | NnReduceMaxOp", *, require_non_empty: bool) -> None:
    """统一校验 nn.reduce_* 的结构化合同。


    功能说明:
    - 校验 input/result 类型、axes/keepdim、shape/stride 与空间一致性。
    - 按需检查静态空归约域错误路径。

    使用示例:
    - _verify_reduce_op(op, require_non_empty=True)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    input_type = op.input.type
    result_type = op.result.type
    if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
        raise_verify_error("operand-must-be-nn-memory")
    input_type.verify()
    result_type.verify()

    axes = _verify_reduce_axes(op.axes, len(input_type.shape.data))
    keepdim = _verify_keepdim_attr(op.keepdim)

    if require_non_empty:
        _verify_non_empty_reduction_extent(input_type.shape.data, axes)

    if result_type.element_type != input_type.element_type:
        raise_verify_error("result-element-type-must-match-input")

    op.space.verify()
    if input_type.space.space.data != result_type.space.space.data:
        raise_verify_error("result-space-must-match-input-and-attr")
    if input_type.space.space.data != op.space.space.data:
        raise_verify_error("result-space-must-match-input-and-attr")

    expected_shape = _build_reduce_result_shape(input_type.shape.data, set(axes), keepdim)
    _verify_reduce_result_shape(result_type, expected_shape)
    _verify_reduce_result_stride(result_type, expected_shape)

@irdl_op_definition
class NnReduceSumOp(IRDLOperation):
    """nn.reduce_sum。


    功能说明:
    - 定义 nn.reduce_sum 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
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


        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        axes_attr = normalize_axes_attr(axes)
        keepdim_attr = normalize_bool_attr(keepdim, "keepdim")
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


        功能说明:
        - 调用统一的归约合同校验逻辑。

        使用示例:
        - NnReduceSumOp(inp, result_type, axes=[1], keepdim=True, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        _verify_reduce_op(self, require_non_empty=False)

@irdl_op_definition
class NnReduceMinOp(IRDLOperation):
    """nn.reduce_min。


    功能说明:
    - 定义 nn.reduce_min 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
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


        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        axes_attr = normalize_axes_attr(axes)
        keepdim_attr = normalize_bool_attr(keepdim, "keepdim")
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


        功能说明:
        - 调用归约合同校验逻辑，并拒绝静态空归约域。

        使用示例:
        - NnReduceMinOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        _verify_reduce_op(self, require_non_empty=True)

@irdl_op_definition
class NnReduceMaxOp(IRDLOperation):
    """nn.reduce_max。


    功能说明:
    - 定义 nn.reduce_max 方言 op 与 verifier 约束。

    使用示例:
    - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
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


        功能说明:
        - 绑定输入、结果类型、axes/keepdim 与 space 属性。

        使用示例:
        - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        axes_attr = normalize_axes_attr(axes)
        keepdim_attr = normalize_bool_attr(keepdim, "keepdim")
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


        功能说明:
        - 调用归约合同校验逻辑，并拒绝静态空归约域。

        使用示例:
        - NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        _verify_reduce_op(self, require_non_empty=True)

__all__ = ["NnReduceSumOp", "NnReduceMinOp", "NnReduceMaxOp"]
