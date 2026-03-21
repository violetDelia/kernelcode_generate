"""DMA dialect definitions.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 定义 dma dialect 的 copy/load/store/slice/deslice op 与 verifier 规则。
- 复用 nn dialect 的 NnMemoryType 与 NnMemorySpaceAttr。

使用示例:
- from kernel_gen.dialect.dma import Dma, DmaCopyOp

关联文件:
- spec: spec/dialect/dma.md
- test: test/dialect/test_dma_dialect.py
- 功能实现: kernel_gen/dialect/dma.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, result_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType


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


def _verify_index_list(value: Attribute, field_name: str, *, min_value: int) -> ArrayAttr[Attribute]:
    """校验索引列表 attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 允许 IntAttr 或非空 StringAttr。
    - 对 IntAttr 施加最小值约束。

    使用示例:
    - _verify_index_list(op.sizes, "sizes", min_value=1)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not isinstance(value, ArrayAttr):
        raise VerifyException(f"{field_name} must be an array")
    for entry in value.data:
        if isinstance(entry, IntAttr):
            if entry.data < min_value:
                raise VerifyException(f"{field_name} entries must be >= {min_value}")
        elif isinstance(entry, StringAttr) and entry.data:
            continue
        else:
            raise VerifyException(f"{field_name} entries must be IntAttr or StringAttr")
    return value


def _verify_rank_match(list_attr: ArrayAttr[Attribute], rank: int, field_name: str) -> None:
    """校验索引列表长度与 rank 一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 长度不匹配时抛出 verifier 错误。

    使用示例:
    - _verify_rank_match(offsets, rank, "offsets")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if len(list_attr.data) != rank:
        raise VerifyException(f"{field_name} length must match rank")


def _verify_sizes_match_shape(sizes: ArrayAttr[Attribute], shape: ArrayAttr[Attribute], field_name: str) -> None:
    """校验 sizes 与 shape 一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于验证切片大小与 shape 的对应关系。

    使用示例:
    - _verify_sizes_match_shape(sizes, source.shape, "source")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if sizes != shape:
        raise VerifyException(f"{field_name} shape must match sizes")


def _verify_unit_stride(strides: ArrayAttr[Attribute]) -> None:
    """校验 stride 是否为全 1。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当前阶段仅支持 stride 为 1 的切片语义。

    使用示例:
    - _verify_unit_stride(strides)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    for entry in strides.data:
        if not isinstance(entry, IntAttr) or entry.data != 1:
            raise VerifyException("dma stride must be 1 in current implementation")


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
    result = result_def(NnMemoryType)

    offsets = attr_def(ArrayAttr)
    sizes = attr_def(ArrayAttr)
    strides = attr_def(ArrayAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        source: SSAValue | Operation,
        offsets: ArrayAttr[Attribute],
        sizes: ArrayAttr[Attribute],
        strides: ArrayAttr[Attribute],
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
            operands=[source],
            result_types=[result_type],
            attributes={
                "offsets": offsets,
                "sizes": sizes,
                "strides": strides,
                "space": space,
            },
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
        offsets = _verify_index_list(self.offsets, "offsets", min_value=0)
        sizes = _verify_index_list(self.sizes, "sizes", min_value=1)
        strides = _verify_index_list(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride(strides)
        _verify_sizes_match_shape(sizes, result_type.shape, "result")
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

    offsets = attr_def(ArrayAttr)
    sizes = attr_def(ArrayAttr)
    strides = attr_def(ArrayAttr)

    def __init__(
        self,
        source: SSAValue | Operation,
        target: SSAValue | Operation,
        offsets: ArrayAttr[Attribute],
        sizes: ArrayAttr[Attribute],
        strides: ArrayAttr[Attribute],
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

        super().__init__(
            operands=[source, target],
            attributes={
                "offsets": offsets,
                "sizes": sizes,
                "strides": strides,
            },
        )

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
        offsets = _verify_index_list(self.offsets, "offsets", min_value=0)
        sizes = _verify_index_list(self.sizes, "sizes", min_value=1)
        strides = _verify_index_list(self.strides, "strides", min_value=1)
        rank = len(target_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride(strides)
        _verify_sizes_match_shape(sizes, source_type.shape, "source")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.store element_type mismatch")


@irdl_op_definition
class DmaSliceOp(IRDLOperation):
    """dma.slice。"""

    name = "dma.slice"

    source = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)

    offsets = attr_def(ArrayAttr)
    sizes = attr_def(ArrayAttr)
    strides = attr_def(ArrayAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        source: SSAValue | Operation,
        offsets: ArrayAttr[Attribute],
        sizes: ArrayAttr[Attribute],
        strides: ArrayAttr[Attribute],
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 dma.slice。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 设置 source、索引属性、结果类型与 space。

        使用示例:
        - DmaSliceOp(source, offsets, sizes, strides, result_type, space)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(
            operands=[source],
            result_types=[result_type],
            attributes={
                "offsets": offsets,
                "sizes": sizes,
                "strides": strides,
                "space": space,
            },
        )

    def verify_(self) -> None:
        """校验 dma.slice。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - offsets/sizes/strides 长度与 source rank 一致。
        - result.shape == sizes 且 element_type/space 一致。
        - 当前阶段 stride 必须为 1。

        使用示例:
        - DmaSliceOp(...).verify_()

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        source_type = _verify_memory_type(self.source.type, "source")
        result_type = _verify_memory_type(self.result.type, "result")
        offsets = _verify_index_list(self.offsets, "offsets", min_value=0)
        sizes = _verify_index_list(self.sizes, "sizes", min_value=1)
        strides = _verify_index_list(self.strides, "strides", min_value=1)
        rank = len(source_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride(strides)
        _verify_sizes_match_shape(sizes, result_type.shape, "result")
        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.slice element_type mismatch")
        self.space.verify()
        if result_type.space.space.data != self.space.space.data:
            raise VerifyException("dma.slice space attribute must match result space")


@irdl_op_definition
class DmaDesliceOp(IRDLOperation):
    """dma.deslice。"""

    name = "dma.deslice"

    source = operand_def(NnMemoryType)
    target = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)

    offsets = attr_def(ArrayAttr)
    sizes = attr_def(ArrayAttr)
    strides = attr_def(ArrayAttr)

    def __init__(
        self,
        source: SSAValue | Operation,
        target: SSAValue | Operation,
        offsets: ArrayAttr[Attribute],
        sizes: ArrayAttr[Attribute],
        strides: ArrayAttr[Attribute],
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
            operands=[source, target],
            result_types=[result_type],
            attributes={
                "offsets": offsets,
                "sizes": sizes,
                "strides": strides,
            },
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
        offsets = _verify_index_list(self.offsets, "offsets", min_value=0)
        sizes = _verify_index_list(self.sizes, "sizes", min_value=1)
        strides = _verify_index_list(self.strides, "strides", min_value=1)
        rank = len(target_type.shape.data)
        _verify_rank_match(offsets, rank, "offsets")
        _verify_rank_match(sizes, rank, "sizes")
        _verify_rank_match(strides, rank, "strides")
        _verify_unit_stride(strides)
        _verify_sizes_match_shape(sizes, source_type.shape, "source")
        if source_type.element_type != target_type.element_type:
            raise VerifyException("dma.deslice element_type mismatch")
        if result_type != target_type:
            raise VerifyException("dma.deslice result must match target type")


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
    operations = [DmaCopyOp, DmaLoadOp, DmaStoreOp, DmaSliceOp, DmaDesliceOp]
    attributes = []


__all__ = [
    "Dma",
    "DmaCopyOp",
    "DmaLoadOp",
    "DmaStoreOp",
    "DmaSliceOp",
    "DmaDesliceOp",
]
