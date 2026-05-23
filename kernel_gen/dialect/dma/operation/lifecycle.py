"""DMA lifecycle operation definitions.

功能说明:
- 定义 `dma.alloc`、`dma.fill` 与 `dma.free`。

API 列表:
- `class DmaAllocOp(dynamic_shape: Sequence[SSAValue], result_type: NnMemoryType)`
- `class DmaFillOp(target: SSAValue | Operation, value: SSAValue | Operation)`
- `class DmaFreeOp(source: SSAValue | Operation)`

使用示例:
- `DmaAllocOp(dynamic_shape, result_type)`

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/dma/
- 功能实现: kernel_gen/dialect/dma/operation/lifecycle.py
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

from ..canonicalization import DmaFillCanonicalizationTrait
from ..common import (
    verify_dynamic_shape_matches_result,
    verify_fill_target_element_type,
    verify_fill_value_matches_target,
    verify_fill_value_operand,
    verify_memory_operand,
    verify_memory_type,
    verify_symbol_int_operands,
)
from ..effect import DmaAllocMemoryEffect, DmaFreeMemoryEffect, DmaTargetWriteEffect

@irdl_op_definition
class DmaAllocOp(IRDLOperation):
    """dma.alloc。"""

    name = "dma.alloc"
    traits = traits_def(DmaAllocMemoryEffect())

    dynamic_shape = var_operand_def(SymbolValueType)
    result = result_def(NnMemoryType)

    irdl_options = [AttrSizedOperandSegments(as_property=True)]

    def __init__(
        self,
        dynamic_shape: Sequence[SSAValue],
        result_type: NnMemoryType,
    ) -> None:
        """初始化 dma.alloc。


        功能说明:
        - 设置动态 shape operand 与结果类型。

        使用示例:
        - DmaAllocOp(dynamic_shape, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(operands=[dynamic_shape], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.alloc。


        功能说明:
        - 结果类型必须为 nn.memory。
        - dynamic_shape 支持空列表（全静态 shape）、全量 rank 列表或仅符号维度列表。
        - stride 按结果类型显式指定，不再额外限制布局。

        使用示例:
        - DmaAllocOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        result_type = verify_memory_type(self.result.type, "result")
        dynamic_shape = verify_symbol_int_operands(self.dynamic_shape, "dynamic_shape", min_value=0)
        verify_dynamic_shape_matches_result(dynamic_shape, result_type.shape, "dynamic_shape")


@irdl_op_definition
class DmaFillOp(IRDLOperation):
    """dma.fill。"""

    name = "dma.fill"
    traits = traits_def(DmaTargetWriteEffect(), DmaFillCanonicalizationTrait())

    target = operand_def(NnMemoryType)
    value = operand_def(Attribute)

    def __init__(self, target: SSAValue | Operation, value: SSAValue | Operation) -> None:
        """初始化 dma.fill。


        功能说明:
        - 设置被写入的 `target` memory 与标量 `value` operand。

        使用示例:
        - DmaFillOp(target, value)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(operands=[target, value])

    def verify_(self) -> None:
        """校验 dma.fill。


        功能说明:
        - `target` 必须为非 bool 数值 `!nn.memory<...>`。
        - `value` 允许 builtin 整数、builtin 浮点或 `!symbol.int<#symbol.expr<expr>>`。

        使用示例:
        - DmaFillOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        target_type = verify_memory_operand(self.target, "target")
        verify_fill_target_element_type(target_type.element_type)
        value = verify_fill_value_operand(self.value, "value")
        verify_fill_value_matches_target(value.type, target_type.element_type)


@irdl_op_definition
class DmaFreeOp(IRDLOperation):
    """dma.free。"""

    name = "dma.free"
    traits = traits_def(DmaFreeMemoryEffect())

    source = operand_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation) -> None:
        """初始化 dma.free。


        功能说明:
        - 设置待释放的 source operand。

        使用示例:
        - DmaFreeOp(source)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        super().__init__(operands=[source])

    def verify_(self) -> None:
        """校验 dma.free。


        功能说明:
        - source 必须为 nn.memory。

        使用示例:
        - DmaFreeOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/dma/
        - 功能实现: kernel_gen/dialect/dma/
        """

        verify_memory_operand(self.source, "source")



__all__ = [
    "DmaAllocOp",
    "DmaFillOp",
    "DmaFreeOp",
]
