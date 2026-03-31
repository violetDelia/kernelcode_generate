"""DMA dialect definitions.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 定义 dma dialect 的 alloc/copy/load/store/slice/deslice/view/reshape/cast op 与 verifier 规则。
- 复用 nn dialect 的 NnMemoryType 与 NnMemorySpaceAttr。

使用示例:
- from kernel_gen.dialect.dma import Dma, DmaCopyOp

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/test_dma_dialect.py
- 功能实现: kernel_gen/dialect/dma.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import (
    AttrSizedOperandSegments,
    IRDLOperation,
    attr_def,
    irdl_op_definition,
    operand_def,
    result_def,
    var_operand_def,
)
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType


def _verify_memory_type(value: Attribute, field_name: str) -> NnMemoryType:
    """校验并返回 nn.memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 确认类型为 nn.memory 并触发类型校验。

    使用示例:
    - _verify_memory_type(op.source.type, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not isinstance(value, NnMemoryType):
        raise VerifyException(f"{field_name} must be nn.memory")
    value.verify()
    return value


def _verify_memory_operand(value: SSAValue, field_name: str) -> NnMemoryType:
    """校验 SSA operand 为 nn.memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一处理 SSA operand 的 nn.memory 类型校验与内部验证。

    使用示例:
    - _verify_memory_operand(op.source, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    return _verify_memory_type(value.type, field_name)


def _operand_int_value(value: SSAValue) -> int | None:
    """尝试从 `!symbol.int<"expr">` SSA operand 恢复静态整型值。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅识别字面量整数表达式，例如 `!symbol.int<"4">`。
    - 其他符号表达式统一视为运行期值。

    使用示例:
    - _operand_int_value(op.sizes[0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not isinstance(value.type, SymbolValueType):
        return None
    expr = value.type.expr.expr.data.strip()
    try:
        return int(expr)
    except ValueError:
        return None


def _verify_symbol_int_operands(
    values: Sequence[SSAValue], field_name: str, *, min_value: int
) -> Sequence[SSAValue]:
    """校验 `!symbol.int<"expr">` operand 列表。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 确保所有 operand 类型为 `!symbol.int<"expr">`。
    - 若 operand 可静态恢复为整型常量，则施加最小值约束。

    使用示例:
    - _verify_symbol_int_operands(op.sizes, "sizes", min_value=1)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value in values:
        if not isinstance(value.type, SymbolValueType):
            raise VerifyException(f"{field_name} entries must be !symbol.int")
        value.type.verify()
        static_value = _operand_int_value(value)
        if static_value is not None and static_value < min_value:
            raise VerifyException(f"{field_name} entries must be >= {min_value}")
    return values


def _verify_rank_match(values: Sequence[SSAValue], rank: int, field_name: str) -> None:
    """校验标量 operand 列表长度与 rank 一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于验证切片大小与 shape 的对应关系。

    使用示例:
    - _verify_rank_match(offsets, rank, "offsets")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if len(values) != rank:
        raise VerifyException(f"{field_name} length must match rank")


def _verify_operands_match_layout(
    values: Sequence[SSAValue],
    layout: ArrayAttr[Attribute],
    mismatch_message: str,
) -> None:
    """校验 operand 列表与类型中可静态判定的布局一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若布局维度为 `IntAttr`，对应 operand 必须是相同值的 `!symbol.int<"n">`。
    - 若布局维度为符号属性，则只要求存在 `!symbol.int<"expr">` SSA operand。

    使用示例:
    - _verify_operands_match_layout(op.sizes, result_type.shape, "shape must match sizes")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value, expected in zip(values, layout.data, strict=True):
        if isinstance(expected, IntAttr):
            static_value = _operand_int_value(value)
            if static_value != expected.data:
                raise VerifyException(mismatch_message)


def _verify_unit_stride_operands(strides: Sequence[SSAValue]) -> None:
    """校验 stride operand 是否全为常量 1。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 当前阶段仅支持单位步长语义。
    - 每个 operand 都必须是值为 `1` 的 `!symbol.int<"1">`。

    使用示例:
    - _verify_unit_stride_operands(op.strides)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for value in strides:
        if _operand_int_value(value) != 1:
            raise VerifyException("dma stride must be 1 in current implementation")


def _maybe_numel(shape: ArrayAttr[Attribute]) -> int | None:
    """尝试计算 shape 的元素总数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在全部维度为 IntAttr 时返回乘积。

    使用示例:
    - _maybe_numel(ArrayAttr([IntAttr(2), IntAttr(4)]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    numel = 1
    for dim in shape.data:
        if not isinstance(dim, IntAttr):
            return None
        numel *= dim.data
    return numel


def _verify_static_view_bounds(
    source_shape: ArrayAttr[Attribute],
    offsets: Sequence[SSAValue],
    shape: Sequence[SSAValue],
    stride: Sequence[SSAValue],
) -> None:
    """校验 dma.view 可静态判定的边界约束。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 当 `source.shape` 与 `offsets/shape/stride` 都可静态恢复时，执行
      `offset + (size - 1) * stride < dim` 检查。

    使用示例:
    - _verify_static_view_bounds(source_type.shape, op.offsets, op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for index, source_dim in enumerate(source_shape.data):
        if not isinstance(source_dim, IntAttr):
            continue
        offset_value = _operand_int_value(offsets[index])
        size_value = _operand_int_value(shape[index])
        stride_value = _operand_int_value(stride[index])
        if offset_value is None or size_value is None or stride_value is None:
            continue
        last_index = offset_value + (size_value - 1) * stride_value
        if last_index >= source_dim.data:
            raise VerifyException("dma.view bounds mismatch")


def _default_contiguous_stride(shape: ArrayAttr[Attribute]) -> list[Attribute]:
    """按默认连续布局生成行主序 stride。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 静态维度返回 `IntAttr` 乘积。
    - 符号维度返回无空格 `*` 连接的乘法表达式。
    - `?` 维度会把更高维 stride 退化为 `?`。

    使用示例:
    - _default_contiguous_stride(ArrayAttr([IntAttr(2), IntAttr(4)]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    stride: list[Attribute] = []
    running: int | str | None = 1
    for dim in reversed(shape.data):
        if running is None:
            stride.append(StringAttr("?"))
        elif isinstance(running, int):
            stride.append(IntAttr(running))
        else:
            stride.append(StringAttr(running))
        if running is None:
            continue
        if isinstance(dim, IntAttr):
            if dim.data == 1:
                continue
            if isinstance(running, int):
                running *= dim.data
            else:
                running = f"{dim.data}*{running}"
            continue
        if isinstance(dim, StringAttr):
            if dim.data == "?":
                running = None
            elif running == 1:
                running = dim.data
            else:
                running = f"{dim.data}*{running}"
            continue
        if running is not None:
            running = None
    stride.reverse()
    return stride


def _is_contiguous(memory_type: NnMemoryType) -> bool:
    """检查 memory type 是否连续行主序。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在 stride 为 IntAttr 且匹配连续行主序时返回 True。

    使用示例:
    - _is_contiguous(memory_type)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    expected = _default_contiguous_stride(memory_type.shape)
    if len(expected) != len(memory_type.stride.data):
        return False
    for expected_dim, stride_dim in zip(expected, memory_type.stride.data, strict=True):
        if isinstance(expected_dim, IntAttr):
            if not isinstance(stride_dim, IntAttr) or stride_dim.data != expected_dim.data:
                return False
            continue
        if isinstance(expected_dim, StringAttr):
            if not isinstance(stride_dim, StringAttr) or stride_dim.data != expected_dim.data:
                return False
            continue
        return False
    return True


def _verify_default_contiguous_stride(memory_type: NnMemoryType, message: str) -> None:
    """校验 memory type 的 stride 是否匹配默认连续布局。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 根据 `shape` 生成默认连续布局。
    - 要求 `stride` 与默认布局完全一致。

    使用示例:
    - _verify_default_contiguous_stride(result_type, "dma.alloc requires contiguous result stride")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not _is_contiguous(memory_type):
        raise VerifyException(message)


@irdl_op_definition
class DmaAllocOp(IRDLOperation):
    """dma.alloc。"""

    name = "dma.alloc"

    dynamic_shape = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        dynamic_shape: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.alloc。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置动态 shape operand 与结果类型。

        使用示例:
        - DmaAllocOp(dynamic_shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[dynamic_shape], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.alloc。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 结果类型必须为 nn.memory。

        使用示例:
        - DmaAllocOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        result_type = _verify_memory_type(self.result.type, "result")
        dynamic_shape = _verify_symbol_int_operands(self.dynamic_shape, "dynamic_shape", min_value=1)
        _verify_rank_match(dynamic_shape, len(result_type.shape.data), "dynamic_shape")
        _verify_operands_match_layout(dynamic_shape, result_type.shape, "dynamic_shape must match result shape")
        _verify_default_contiguous_stride(result_type, "dma.alloc requires contiguous result stride")


@irdl_op_definition
class DmaFreeOp(IRDLOperation):
    """dma.free。"""

    name = "dma.free"

    source = operand_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation) -> None:
        """初始化 dma.free。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置待释放的 source operand。

        使用示例:
        - DmaFreeOp(source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source])

    def verify_(self) -> None:
        """校验 dma.free。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - source 必须为 nn.memory。

        使用示例:
        - DmaFreeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        _verify_memory_operand(self.source, "source")


@irdl_op_definition
class DmaCopyOp(IRDLOperation):
    """dma.copy。"""

    name = "dma.copy"

    source = operand_def(NnMemoryType)
    target = operand_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation, target: SSAValue | Operation) -> None:
        """初始化 dma.copy。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置 source 与 target operand。

        使用示例:
        - DmaCopyOp(source, target)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source, target])

    def verify_(self) -> None:
        """校验 dma.copy。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - source/target 的 shape/stride/element_type 必须一致。

        使用示例:
        - DmaCopyOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        target_type = _verify_memory_type(self.target.type, "target")
        if source_type.shape != target_type.shape:
            raise VerifyException("dma.copy source/target shape mismatch")
        if source_type.stride != target_type.stride:
            raise VerifyException("dma.copy source/target stride mismatch")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.copy source/target element_type mismatch")


@irdl_op_definition
class DmaLoadOp(IRDLOperation):
    """dma.load。"""

    name = "dma.load"

    source = operand_def(NnMemoryType)
    offsets = var_operand_def(SymbolValueType)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 dma.load。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置 source、索引属性、结果类型与 space attribute。

        使用示例:
        - DmaLoadOp(source, offsets, sizes, strides, result_type, space)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(
            operands=[source, offsets, sizes, strides],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 dma.load。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - result.shape == sizes 且 element_type/space 一致。

        使用示例:
        - DmaLoadOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        offsets = _verify_symbol_int_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, result_type.shape, "shape must match sizes")
        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.load element_type mismatch")
        self.space.verify()
        if result_type.space.space.data != self.space.space.data:
            raise VerifyException("dma.load space attribute must match result space")


@irdl_op_definition
class DmaStoreOp(IRDLOperation):
    """dma.store。"""

    name = "dma.store"

    source = operand_def(NnMemoryType)
    target = operand_def(NnMemoryType)
    offsets = var_operand_def(SymbolValueType)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        target: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.store。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置 source/target 与索引属性。

        使用示例:
        - DmaStoreOp(source, target, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source, target, offsets, sizes, strides])

    def verify_(self) -> None:
        """校验 dma.store。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。

        使用示例:
        - DmaStoreOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        target_type = _verify_memory_type(self.target.type, "target")
        offsets = _verify_symbol_int_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(target_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, source_type.shape, "source shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.store element_type mismatch")


@irdl_op_definition
class DmaSliceOp(IRDLOperation):
    """dma.slice。"""

    name = "dma.slice"

    target = operand_def(NnMemoryType)
    source = operand_def(NnMemoryType)
    offsets = var_operand_def(SymbolValueType)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        target: SSAValue | Operation,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
    ) -> None:
        """初始化 dma.slice。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 target/source 与索引属性。

        使用示例:
        - DmaSliceOp(target, source, offsets, sizes, strides)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[target, source, offsets, sizes, strides])

    def verify_(self) -> None:
        """校验 dma.slice。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - target.shape == sizes 且 target/source element_type 一致。
        - 当前阶段 stride 必须为 1。

        使用示例:
        - DmaSliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        target_type = _verify_memory_type(self.target.type, "target")
        source_type = _verify_memory_type(self.source.type, "source")
        offsets = _verify_symbol_int_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        if len(target_type.shape.data) != rank:
            raise VerifyException("dma.slice target rank must match source rank")
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, target_type.shape, "shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.slice element_type mismatch")


@irdl_op_definition
class DmaDesliceOp(IRDLOperation):
    """dma.deslice。"""

    name = "dma.deslice"

    source = operand_def(NnMemoryType)
    target = operand_def(NnMemoryType)
    offsets = var_operand_def(SymbolValueType)
    sizes = var_operand_def(SymbolValueType)
    strides = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        target: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        sizes: Sequence[SSAValue],
        strides: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.deslice。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置 source/target、索引属性与结果类型。

        使用示例:
        - DmaDesliceOp(source, target, offsets, sizes, strides, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(
            operands=[source, target, offsets, sizes, strides],
            result_types=[result_type],
        )

    def verify_(self) -> None:
        """校验 dma.deslice。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - source.shape 必须与 sizes 对齐。
        - offsets/sizes/strides 长度与 target rank 一致。
        - result type 必须与 target type 一致。

        使用示例:
        - DmaDesliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        target_type = _verify_memory_type(self.target.type, "target")
        result_type = _verify_memory_type(self.result.type, "result")
        offsets = _verify_symbol_int_operands(self.offsets, "offsets", min_value=0)
        sizes = _verify_symbol_int_operands(self.sizes, "sizes", min_value=1)
        strides = _verify_symbol_int_operands(self.strides, "strides", min_value=1)
        rank = len(target_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride_operands(strides)
        _verify_operands_match_layout(sizes, source_type.shape, "source shape must match sizes")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.deslice element_type mismatch")
        if result_type != target_type:
            raise VerifyException("dma.deslice result must match target type")


@irdl_op_definition
class DmaViewOp(IRDLOperation):
    """dma.view。"""

    name = "dma.view"

    source = operand_def(NnMemoryType)
    offsets = var_operand_def(SymbolValueType)
    shape = var_operand_def(SymbolValueType)
    stride = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        offsets: Sequence[SSAValue],
        shape: Sequence[SSAValue],
        stride: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.view。

        创建者: 金铲铲大作战
        最后一次更改: OpenAI

        功能说明:
        - 设置 source、动态 offsets/shape/stride operand 与结果类型。

        使用示例:
        - DmaViewOp(source, offsets, shape, stride, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        if not isinstance(result_type, NnMemoryType):
            raise TypeError("result_type must be nn.memory")

        super().__init__(operands=[source, offsets, shape, stride], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.view。

        创建者: 金铲铲大作战
        最后一次更改: OpenAI

        功能说明:
        - element_type/space 必须一致。
        - `offsets`/`shape`/`stride` 必须是 `!symbol.int<"expr">` 且长度与 rank 一致。
        - 当边界可静态判定时，必须满足 `offset + (size - 1) * stride < dim`。
        - 可判定 numel 不一致必须报错。

        使用示例:
        - DmaViewOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        offsets = _verify_symbol_int_operands(self.offsets, "offsets", min_value=0)
        shape = _verify_symbol_int_operands(self.shape, "shape", min_value=1)
        stride = _verify_symbol_int_operands(self.stride, "stride", min_value=1)
        rank = len(result_type.shape.data)
        if len(source_type.shape.data) != rank:
            raise VerifyException("dma.view source/result rank mismatch")
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(shape, rank, "shape")
        _verify_rank_match(stride, rank, "stride")
        _verify_operands_match_layout(shape, result_type.shape, "shape must match result shape")
        _verify_operands_match_layout(stride, result_type.stride, "stride must match result stride")
        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.view element_type mismatch")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.view space mismatch")

        source_numel = _maybe_numel(source_type.shape)
        result_numel = _maybe_numel(result_type.shape)
        if source_numel is not None and result_numel is not None and source_numel != result_numel:
            raise VerifyException("dma.view numel mismatch")
        _verify_static_view_bounds(source_type.shape, offsets, shape, stride)


@irdl_op_definition
class DmaReshapeOp(IRDLOperation):
    """dma.reshape。"""

    name = "dma.reshape"

    source = operand_def(NnMemoryType)
    shape = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        shape: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.reshape。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source、动态 shape operand 与结果类型。

        使用示例:
        - DmaReshapeOp(source, shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source, shape], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.reshape。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - element_type/space 必须一致。
        - source 必须连续，result.stride 必须为连续行主序。
        - 可判定 numel 不一致必须报错。

        使用示例:
        - DmaReshapeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        shape = _verify_symbol_int_operands(self.shape, "shape", min_value=1)
        _verify_rank_match(shape, len(result_type.shape.data), "shape")
        _verify_operands_match_layout(shape, result_type.shape, "shape must match result shape")
        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.reshape element_type mismatch")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.reshape space mismatch")

        source_numel = _maybe_numel(source_type.shape)
        result_numel = _maybe_numel(result_type.shape)
        if source_numel is not None and result_numel is not None and source_numel != result_numel:
            raise VerifyException("dma.reshape numel mismatch")

        if not _is_contiguous(source_type):
            raise VerifyException("dma.reshape requires contiguous source")

        _verify_default_contiguous_stride(result_type, "dma.reshape requires contiguous result stride")


@irdl_op_definition
class DmaCastOp(IRDLOperation):
    """dma.cast。"""

    name = "dma.cast"

    source = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation, result_type: NnMemoryType) -> None:
        """初始化 dma.cast。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source 与结果类型。

        使用示例:
        - DmaCastOp(source, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.cast。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - shape/stride/space 必须一致，仅 element_type 可变化。

        使用示例:
        - DmaCastOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        if source_type.shape != result_type.shape:
            raise VerifyException("dma.cast shape mismatch")
        if source_type.stride != result_type.stride:
            raise VerifyException("dma.cast stride mismatch")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.cast space mismatch")


class Dma(Dialect):
    """DMA dialect 入口。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 注册 dma dialect 的 op 定义。

    使用示例:
    - ctx.load_dialect(Dma)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    name = "dma"
    operations = [
        DmaAllocOp,
        DmaFreeOp,
        DmaCopyOp,
        DmaLoadOp,
        DmaStoreOp,
        DmaSliceOp,
        DmaDesliceOp,
        DmaViewOp,
        DmaReshapeOp,
        DmaCastOp,
    ]
    attributes = []


__all__ = [
    "Dma",
    "DmaAllocOp",
    "DmaFreeOp",
    "DmaCopyOp",
    "DmaLoadOp",
    "DmaStoreOp",
    "DmaSliceOp",
    "DmaDesliceOp",
    "DmaViewOp",
    "DmaReshapeOp",
    "DmaCastOp",
]
