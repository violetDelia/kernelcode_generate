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


def _verify_stride_list(value: Attribute, field_name: str) -> ArrayAttr[Attribute]:
    """校验 stride 列表 attribute。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 仅允许 `IntAttr(1)`，不接受 `StringAttr` 或其他 attribute。
    - 与 spec 中 `strides` 仅支持 `IntAttr(1)` 的约束保持一致。

    使用示例:
    - _verify_stride_list(op.strides, "strides")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if not isinstance(value, ArrayAttr):
        raise VerifyException(f"{field_name} must be an array")
    for entry in value.data:
        if not isinstance(entry, IntAttr) or entry.data != 1:
            raise VerifyException(f"{field_name} entries must be IntAttr(1)")
    return value


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


def _contiguous_stride(shape: ArrayAttr[Attribute]) -> list[Attribute]:
    """生成行主序连续 stride。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当维度为符号时，以 `?` 标记无法确定的 stride。
    - 若后续维度全为 IntAttr，则返回确定的 IntAttr stride。

    使用示例:
    - _contiguous_stride(ArrayAttr([IntAttr(2), IntAttr(4)]))

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    stride: list[Attribute] = []
    running: int | None = 1
    for dim in reversed(shape.data):
        if running is None:
            stride.append(StringAttr("?"))
        else:
            stride.append(IntAttr(running))
        if isinstance(dim, IntAttr) and running is not None:
            running *= dim.data
        else:
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

    expected = _contiguous_stride(memory_type.shape)
    if len(expected) != len(memory_type.stride.data):
        return False
    for expected_dim, stride_dim in zip(expected, memory_type.stride.data, strict=True):
        if isinstance(expected_dim, IntAttr):
            if not isinstance(stride_dim, IntAttr) or stride_dim.data != expected_dim.data:
                return False
            continue
        if isinstance(expected_dim, StringAttr):
            if isinstance(stride_dim, IntAttr):
                continue
            if isinstance(stride_dim, StringAttr) and stride_dim.data:
                continue
            return False
        return False
    return True


@irdl_op_definition
class DmaAllocOp(IRDLOperation):
    """dma.alloc。"""

    name = "dma.alloc"

    result = result_def(NnMemoryType)

    def __init__(self, result_type: NnMemoryType) -> None:
        """初始化 dma.alloc。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置结果类型。

        使用示例:
        - DmaAllocOp(result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(result_types=[result_type])

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

        _verify_memory_type(self.result.type, "result")


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
        strides = _verify_stride_list(self.strides, "strides")
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
        strides = _verify_stride_list(self.strides, "strides")
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
        strides = _verify_stride_list(self.strides, "strides")
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
        strides = _verify_stride_list(self.strides, "strides")
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


@irdl_op_definition
class DmaViewOp(IRDLOperation):
    """dma.view。"""

    name = "dma.view"

    source = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation, result_type: NnMemoryType) -> None:
        """初始化 dma.view。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source 与结果类型。

        使用示例:
        - DmaViewOp(source, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source], result_types=[result_type])

    def verify_(self) -> None:
        """校验 dma.view。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - element_type/space 必须一致。
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
        if source_type.element_type != result_type.element_type:
            raise VerifyException("dma.view element_type mismatch")
        if source_type.space.space.data != result_type.space.space.data:
            raise VerifyException("dma.view space mismatch")

        source_numel = _maybe_numel(source_type.shape)
        result_numel = _maybe_numel(result_type.shape)
        if source_numel is not None and result_numel is not None and source_numel != result_numel:
            raise VerifyException("dma.view numel mismatch")


@irdl_op_definition
class DmaReshapeOp(IRDLOperation):
    """dma.reshape。"""

    name = "dma.reshape"

    source = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)

    def __init__(self, source: SSAValue | Operation, result_type: NnMemoryType) -> None:
        """初始化 dma.reshape。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 设置 source 与结果类型。

        使用示例:
        - DmaReshapeOp(source, result_type)

        关联文件:
        - spec: spec/dialect/dma.md
        - test: test/dialect/test_dma_dialect.py
        - 功能实现: kernel_gen/dialect/dma.py
        """

        super().__init__(operands=[source], result_types=[result_type])

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

        expected = _contiguous_stride(result_type.shape)
        for expected_dim, stride_dim in zip(expected, result_type.stride.data, strict=True):
            if isinstance(expected_dim, IntAttr):
                if not isinstance(stride_dim, IntAttr) or stride_dim.data != expected_dim.data:
                    raise VerifyException("dma.reshape requires contiguous result stride")
                continue
            if isinstance(expected_dim, StringAttr):
                if isinstance(stride_dim, IntAttr):
                    continue
                if isinstance(stride_dim, StringAttr) and stride_dim.data:
                    continue
                raise VerifyException("dma.reshape requires contiguous result stride")
            raise VerifyException("dma.reshape requires contiguous result stride")


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
    "DmaCopyOp",
    "DmaLoadOp",
    "DmaStoreOp",
    "DmaSliceOp",
    "DmaDesliceOp",
    "DmaViewOp",
    "DmaReshapeOp",
    "DmaCastOp",
]
