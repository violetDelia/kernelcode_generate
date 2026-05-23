"""DMA alias operation definitions.

功能说明:
- 定义 `dma.view`、`dma.subview`、`dma.reshape` 与 `dma.reinterpret`。

API 列表:
- `class DmaSubviewOp(source: SSAValue | Operation, offset: SSAValue | Operation, size: SSAValue | Operation, stride: SSAValue | Operation, result_type: NnMemoryType)`
- `class DmaViewOp(source: SSAValue | Operation, offsets: Sequence[SSAValue], shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaReshapeOp(source: SSAValue | Operation, shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaReinterpretOp(source: SSAValue | Operation, offset: SSAValue | Operation, shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`

使用示例:
- `DmaViewOp(source, offsets, shape, stride, result_type)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/alias.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import ArrayAttr, IntAttr
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.irdl import (
    AttrSizedOperandSegments,
    IRDLOperation,
    attr_def,
    irdl_op_definition,
    operand_def,
    result_def,
    traits_def,
    var_operand_def,
)
from xdsl.traits import NoMemoryEffect
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from ..canonicalization import DmaReshapeCanonicalizationTrait, DmaViewCanonicalizationTrait
from ..common import (
    element_byte_size,
    is_contiguous,
    is_i8_byte_pool,
    linear_max_index,
    maybe_numel,
    operand_int_value,
    verify_default_contiguous_stride,
    verify_memory_type,
    verify_operands_match_layout,
    verify_rank_match,
    verify_static_view_bounds,
    verify_symbol_index_operands,
    verify_symbol_int_operands,
    verify_view_result_stride,
)


def _linear_extent_index(shape: Sequence[SSAValue], stride: Sequence[SSAValue]) -> int | None:
    """计算 shape/stride 的静态最大线性相对索引。

    功能说明:
    - `dma.reinterpret` 的 offset 是独立 operand，本 helper 只计算从 result 起点到最后一个元素的线性距离。
    - 任一 shape/stride 无法静态恢复时返回 None，让 verifier 跳过静态 bounds 判断。

    使用示例:
    - extent = _linear_extent_index(op.shape, op.stride)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    total = 0
    for size_value, stride_value in zip(shape, stride, strict=True):
        size_int = operand_int_value(size_value)
        stride_int = operand_int_value(stride_value)
        if size_int is None or stride_int is None:
            return None
        total += (size_int - 1) * stride_int
    return total


@irdl_op_definition
class DmaViewOp(IRDLOperation):
    """dma.view。"""

    name = "dma.view"
    traits = traits_def(NoMemoryEffect(), DmaViewCanonicalizationTrait())

    source = operand_def(NnMemoryType)
    offsets = var_operand_def(Attribute)
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


        功能说明:
        - 设置 source、动态 offsets/shape/stride operand 与结果类型。
        - offsets 允许 `!symbol.int` 与 `!symbol.iter`。

        使用示例:
        - DmaViewOp(source, offsets, shape, stride, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance(result_type, NnMemoryType):
            raise TypeError("result_type must be nn.memory")

        super().__init__(operands=[source, offsets, shape, stride], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.view。


        功能说明:
        - `space` 必须一致；`element_type` 必须一致（i8 byte pool 允许不同 element_type）。
        - 非 byte pool 场景下 source/result rank 必须一致；byte pool 允许 rank 不一致。
        - `offsets` 允许 `!symbol.int` 与 `!symbol.iter`，`shape`/`stride` 仍需 `!symbol.int`。
        - `offsets`/`shape`/`stride` 长度与结果 rank 一致。
        - 非 byte pool 场景下，结果 stride 必须等于 source physical stride 与 view logical stride 的逐维乘积。
        - 当边界可静态判定时，必须满足 `offset + (size - 1) * stride < dim`。
        - 非 byte pool 场景下可判定 numel 不一致必须报错；byte pool 需满足 typed 子区间字节边界可达。

        使用示例:
        - DmaViewOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type = verify_memory_type(self.source.type, "source")
        result_type = verify_memory_type(self.result.type, "result")
        offsets = verify_symbol_index_operands(self.offsets, "offsets", min_value=0)
        shape = verify_symbol_int_operands(self.shape, "shape", min_value=1)
        stride = verify_symbol_int_operands(self.stride, "stride", min_value=1)
        rank = len(result_type.shape.data)
        if len(source_type.shape.data) != rank and not is_i8_byte_pool(source_type):
            raise VerifyException("dma.view source/result rank mismatch")
        verify_rank_match(offsets, rank, "offsets")
        verify_rank_match(shape, rank, "shape")
        verify_rank_match(stride, rank, "stride")
        verify_operands_match_layout(shape, result_type.shape, "shape must match result shape")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.view space mismatch")

        source_numel = maybe_numel(source_type.shape)
        result_numel = maybe_numel(result_type.shape)
        if is_i8_byte_pool(source_type):
            verify_operands_match_layout(stride, result_type.stride, "stride must match result stride")
            result_elem_size = element_byte_size(result_type.element_type)
            if result_elem_size is None:
                raise VerifyException("dma.view element_type unsupported for byte pool")
            max_index = linear_max_index(offsets, shape, stride)
            if max_index is not None and source_numel is not None:
                byte_end = (max_index + 1) * result_elem_size
                if byte_end > source_numel:
                    raise VerifyException("dma.view byte bounds mismatch")
        else:
            verify_view_result_stride(source_type.stride, stride, result_type.stride)
            if source_type.element_type != result_type.element_type:
                raise VerifyException("dma.view element_type mismatch")
            if source_numel is not None and result_numel is not None and source_numel != result_numel:
                raise VerifyException("dma.view numel mismatch")
            verify_static_view_bounds(source_type.shape, source_type.stride, offsets, shape, stride)


@irdl_op_definition
class DmaSubviewOp(IRDLOperation):
    """dma.subview。"""

    name = "dma.subview"
    traits = traits_def(NoMemoryEffect())

    source = var_operand_def(NnMemoryType)
    offset = var_operand_def(SymbolValueType)
    size = var_operand_def(SymbolValueType)
    stride = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = (AttrSizedOperandSegments(as_property=True),)

    def __init__(
        self,
        source: SSAValue | Operation,
        offset: SSAValue | Operation,
        size: SSAValue | Operation,
        stride: SSAValue | Operation,
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.subview。


        功能说明:
        - 设置一维 i8 backing memory、元素单位 offset/size/stride 与一维 typed result。
        - `offset/size/stride` 均为单个 `!symbol.int<#symbol.expr<expr>>` operand。

        使用示例:
        - DmaSubviewOp(pool, offset, size, stride, flat_result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance(result_type, NnMemoryType):
            raise TypeError("result_type must be nn.memory")

        super().__init__(
            operands=[[source], [offset], [size], [stride]],
            result_types=[result_type],
        )

    def verify_(self) -> None:
        """校验 dma.subview。


        功能说明:
        - source 必须是一维 i8 backing memory。
        - result 必须是一维 contiguous typed memory，且 space 与 source 一致。
        - offset/size/stride 都必须是单个 `!symbol.int<#symbol.expr<expr>>`；size 必须匹配 result flat shape。

        使用示例:
        - DmaSubviewOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if len(self.source) != 1 or len(self.offset) != 1 or len(self.size) != 1 or len(self.stride) != 1:
            raise VerifyException("dma.subview requires one source, offset, size and stride")

        source_type = verify_memory_type(self.source[0].type, "source")
        result_type = verify_memory_type(self.result.type, "result")
        offset = verify_symbol_int_operands(self.offset, "offset", min_value=0)[0]
        size = verify_symbol_int_operands(self.size, "size", min_value=1)[0]
        stride = verify_symbol_int_operands(self.stride, "stride", min_value=1)[0]

        if not is_i8_byte_pool(source_type):
            raise VerifyException("dma.subview source must be one-dimensional i8 memory")
        if len(result_type.shape.data) != 1:
            raise VerifyException("dma.subview result must be one-dimensional")
        if len(result_type.stride.data) != 1:
            raise VerifyException("dma.subview result stride rank must be one")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.subview space mismatch")

        verify_default_contiguous_stride(result_type, "dma.subview result must be contiguous")
        verify_operands_match_layout([size], result_type.shape, "dma.subview size must match result shape")

        source_numel = maybe_numel(source_type.shape)
        result_numel = maybe_numel(result_type.shape)
        result_elem_size = element_byte_size(result_type.element_type)
        if result_elem_size is None:
            raise VerifyException("dma.subview result element_type unsupported")
        offset_int = operand_int_value(offset)
        size_int = operand_int_value(size)
        stride_int = operand_int_value(stride)
        if (
            source_numel is not None
            and result_numel is not None
            and offset_int is not None
            and size_int is not None
            and stride_int is not None
        ):
            byte_end = (offset_int + (size_int - 1) * stride_int + 1) * result_elem_size
            if byte_end > source_numel:
                raise VerifyException("dma.subview byte bounds mismatch")


@irdl_op_definition
class DmaReshapeOp(IRDLOperation):
    """dma.reshape。"""

    name = "dma.reshape"
    traits = traits_def(NoMemoryEffect(), DmaReshapeCanonicalizationTrait())

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


        功能说明:
        - 设置 source、动态 shape operand 与结果类型。

        使用示例:
        - DmaReshapeOp(source, shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(operands=[source, shape], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.reshape。


        功能说明:
        - element_type/space 必须一致。
        - source 必须连续，result.stride 必须为连续行主序。
        - 可判定 numel 不一致必须报错。

        使用示例:
        - DmaReshapeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type = verify_memory_type(self.source.type, "source")
        result_type = verify_memory_type(self.result.type, "result")
        shape = verify_symbol_int_operands(self.shape, "shape", min_value=1)
        verify_rank_match(shape, len(result_type.shape.data), "shape")
        verify_operands_match_layout(shape, result_type.shape, "shape must match result shape")
        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.reshape element_type mismatch")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.reshape space mismatch")

        source_numel = maybe_numel(source_type.shape)
        result_numel = maybe_numel(result_type.shape)
        if source_numel is not None and result_numel is not None and source_numel != result_numel:
            raise VerifyException("dma.reshape numel mismatch")

        if not is_contiguous(source_type):
            raise VerifyException("dma.reshape requires contiguous source")

        verify_default_contiguous_stride(result_type, "dma.reshape requires contiguous result stride")


@irdl_op_definition
class DmaReinterpretOp(IRDLOperation):
    """dma.reinterpret。"""

    name = "dma.reinterpret"
    traits = traits_def(NoMemoryEffect())

    source = operand_def(NnMemoryType)
    offset = operand_def(Attribute)
    shape = var_operand_def(SymbolValueType)
    stride = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        source: SSAValue | Operation,
        offset: SSAValue | Operation,
        shape: Sequence[SSAValue],
        stride: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.reinterpret。


        功能说明:
        - 设置 source、线性 offset、result shape/stride operand 与结果类型。
        - source 是一维 i8 byte pool 时，offset 单位为 byte；其它 source 使用 source element 单位。

        使用示例:
        - DmaReinterpretOp(source, offset, shape, stride, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        if not isinstance(result_type, NnMemoryType):
            raise TypeError("result_type must be nn.memory")

        super().__init__(operands=[source, offset, shape, stride], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.reinterpret。


        功能说明:
        - source/result 均为 `!nn.memory` 且 memory space 必须一致。
        - 非 byte pool source 要求 source/result element_type 一致；byte pool source 允许 result 使用 typed element。
        - offset 必须是 `!symbol.int` 或 `!symbol.iter`；shape/stride 必须是 `!symbol.int`。
        - shape/stride operand 必须与 result type 的 shape/stride exact 匹配。
        - 静态可判定时按 offset 单位执行 bounds 检查。

        使用示例:
        - DmaReinterpretOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        source_type = verify_memory_type(self.source.type, "source")
        result_type = verify_memory_type(self.result.type, "result")
        offset = verify_symbol_index_operands([self.offset], "offset", min_value=0)[0]
        shape = verify_symbol_int_operands(self.shape, "shape", min_value=1)
        stride = verify_symbol_int_operands(self.stride, "stride", min_value=1)
        rank = len(result_type.shape.data)
        verify_rank_match(shape, rank, "shape")
        verify_rank_match(stride, rank, "stride")
        verify_operands_match_layout(shape, result_type.shape, "dma.reinterpret shape must match result shape")
        verify_operands_match_layout(stride, result_type.stride, "dma.reinterpret stride must match result stride")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.reinterpret space mismatch")

        source_numel = maybe_numel(source_type.shape)
        extent = _linear_extent_index(shape, stride)
        offset_int = operand_int_value(offset)
        if is_i8_byte_pool(source_type):
            result_elem_size = element_byte_size(result_type.element_type)
            if result_elem_size is None:
                raise VerifyException("dma.reinterpret result element_type unsupported for byte pool")
            if source_numel is not None and offset_int is not None and extent is not None:
                byte_end = offset_int + (extent + 1) * result_elem_size
                if byte_end > source_numel:
                    raise VerifyException("dma.reinterpret byte bounds mismatch")
            return

        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.reinterpret element_type mismatch")
        if source_numel is not None and offset_int is not None and extent is not None:
            if offset_int + extent >= source_numel:
                raise VerifyException("dma.reinterpret bounds mismatch")


__all__ = [
    "DmaViewOp",
    "DmaSubviewOp",
    "DmaReshapeOp",
    "DmaReinterpretOp",
]
