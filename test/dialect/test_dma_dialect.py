"""dma dialect tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 dma dialect 的 op verifier 与类型复用约束。

使用示例:
- pytest -q test/dialect/test_dma_dialect.py

关联文件:
- 功能实现: kernel_gen/dialect/dma.py
- Spec 文档: spec/dialect/dma.md
- 测试文件: test/dialect/test_dma_dialect.py
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, Builtin, IntAttr, StringAttr, i1, i32
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.ir import Attribute, Operation
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import (
    Dma,
    DmaAllocOp,
    DmaCastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaLoadOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import Nn, NnMemorySpaceAttr, NnMemoryType


def _build_context() -> Context:
    """构造加载 builtin/test/nn/dma 的解析上下文。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 parser/printer/verify 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Dma)
    return ctx


def _print_ir(value: object) -> str:
    """打印 attribute 或 operation/module 为文本。"""

    stream = StringIO()
    printer = Printer(stream=stream)
    if isinstance(value, Attribute):
        printer.print_attribute(value)
    elif isinstance(value, Operation):
        printer.print_op(value)
    else:
        printer.print(value)
    return stream.getvalue()


def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造 space attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 简化测试中的空间构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _make_memory_type(
    shape: ArrayAttr | None = None,
    stride: ArrayAttr | None = None,
    space: str = "global",
) -> NnMemoryType:
    """构造 nn.memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 提供默认可通过 verifier 的 memory type。

    使用示例:
    - _make_memory_type()

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if shape is None:
        shape = ArrayAttr([IntAttr(2), IntAttr(4)])
    if stride is None:
        stride = ArrayAttr([IntAttr(4), IntAttr(1)])
    return NnMemoryType(shape, stride, i32, _make_space(space))


def _make_index_list(values: list[int | str]) -> ArrayAttr:
    """构造索引列表 attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - int 映射为 IntAttr，str 映射为 StringAttr。

    使用示例:
    - _make_index_list([0, 0])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    attrs = []
    for value in values:
        if isinstance(value, int):
            attrs.append(IntAttr(value))
        else:
            attrs.append(StringAttr(value))
    return ArrayAttr(attrs)


# TC-DMA-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma op 仅接受 nn.memory 作为 memory 类型。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_requires_nn_memory_type
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_requires_nn_memory_type() -> None:
    source = _TestOp(result_types=[i32]).results[0]
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    op = DmaCopyOp(source, target)
    with pytest.raises(VerifyException, match="nn.memory"):
        op.verify()


# TC-DMA-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.copy 在合法输入下可通过 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_copy_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_copy_verify_success() -> None:
    memory_type = _make_memory_type()
    source = _TestOp(result_types=[memory_type]).results[0]
    target = _TestOp(result_types=[memory_type]).results[0]
    op = DmaCopyOp(source, target)
    op.verify()


# TC-DMA-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.copy 的 shape mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_copy_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_copy_shape_mismatch() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    target_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(8)]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    op = DmaCopyOp(source, target)
    with pytest.raises(VerifyException, match="shape mismatch"):
        op.verify()


# TC-DMA-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.load 的 result.space 必须与 op.space 一致，且结果 shape 必须匹配 sizes。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_load_result_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_load_result_space_mismatch() -> None:
    source_type = _make_memory_type(space="global")
    result_type = _make_memory_type(space="global")
    source = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_index_list([0, 0])
    sizes = _make_index_list([2, 4])
    strides = _make_index_list([1, 1])
    op = DmaLoadOp(source, offsets, sizes, strides, result_type, _make_space("shared"))
    with pytest.raises(VerifyException, match="space attribute must match result space"):
        op.verify()

    result_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(3)]), space="global")
    op = DmaLoadOp(source, offsets, sizes, strides, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape must match sizes"):
        op.verify()


# TC-DMA-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.slice 索引长度与 rank 不一致、结果 shape 不匹配时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_slice_rank_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_slice_rank_mismatch() -> None:
    source_type = _make_memory_type()
    result_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_index_list([0])
    sizes = _make_index_list([2])
    strides = _make_index_list([1])
    op = DmaSliceOp(source, offsets, sizes, strides, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="length must match rank"):
        op.verify()

    offsets = _make_index_list([0, 0])
    sizes = _make_index_list([2, 4])
    strides = _make_index_list([1, 1])
    result_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(3)]))
    op = DmaSliceOp(source, offsets, sizes, strides, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape must match sizes"):
        op.verify()


# TC-DMA-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.slice 在非 1 stride 下明确报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_slice_non_unit_stride_rejected
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_slice_non_unit_stride_rejected() -> None:
    source_type = _make_memory_type()
    result_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_index_list([0, 0])
    sizes = _make_index_list([2, 4])
    strides = _make_index_list([1, 2])
    op = DmaSliceOp(source, offsets, sizes, strides, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="IntAttr\\(1\\)"):
        op.verify()


# TC-DMA-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.store 的 source.shape 与 sizes 不一致会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_store_size_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_store_size_mismatch() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    target_type = _make_memory_type(shape=ArrayAttr([IntAttr(8), IntAttr(4)]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_index_list([0, 0])
    sizes = _make_index_list([2, 2])
    strides = _make_index_list([1, 1])
    op = DmaStoreOp(source, target, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="source shape must match sizes"):
        op.verify()


# TC-DMA-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.deslice 在合法输入下通过 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_deslice_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_deslice_verify_success() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    target_type = _make_memory_type(shape=ArrayAttr([IntAttr(8), IntAttr(4)]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_index_list([0, 0])
    sizes = _make_index_list([2, 4])
    strides = _make_index_list([1, 1])
    op = DmaDesliceOp(source, target, offsets, sizes, strides, target_type)
    op.verify()


# TC-DMA-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma op 透传 nn.memory 的类型 verifier 错误。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_nn_memory_type_verifier_passthrough
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_nn_memory_type_verifier_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    memory_type = _make_memory_type()
    source = _TestOp(result_types=[memory_type]).results[0]
    target = _TestOp(result_types=[memory_type]).results[0]
    op = DmaCopyOp(source, target)

    def _raise_verify(_: NnMemoryType) -> None:
        raise VerifyException("nn memory shape and stride rank must match")

    monkeypatch.setattr(NnMemoryType, "verify", _raise_verify)
    with pytest.raises(VerifyException, match="nn memory shape and stride rank must match"):
        op.verify()


# TC-DMA-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 offsets/sizes 使用 StringAttr 时可通过 verifier，stride 仍需为 1。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_index_string_attr_valid
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_index_string_attr_valid() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([StringAttr("M"), StringAttr("N")]))
    result_type = _make_memory_type(shape=ArrayAttr([StringAttr("M"), StringAttr("N")]), space="shared")
    source = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_index_list(["m0", "n0"])
    sizes = _make_index_list(["M", "N"])
    strides = _make_index_list([1, 1])
    op = DmaLoadOp(source, offsets, sizes, strides, result_type, _make_space("shared"))
    op.verify()


# TC-DMA-010
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-22 00:00:00 +0800
# 功能说明: 验证动态 offsets/sizes 支持 store/deslice，且 strides 仍必须为 IntAttr(1)。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_store_and_deslice_allow_dynamic_offsets_sizes
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_store_and_deslice_allow_dynamic_offsets_sizes() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("TM"), StringAttr("?")]),
        stride=ArrayAttr([StringAttr("TN"), IntAttr(1)]),
        space="shared",
    )
    target_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("M"), StringAttr("N")]),
        stride=ArrayAttr([StringAttr("N"), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_index_list(["m0", "?"])
    sizes = _make_index_list(["TM", "?"])
    strides = _make_index_list([1, 1])

    DmaStoreOp(source, target, offsets, sizes, strides).verify()
    DmaDesliceOp(source, target, offsets, sizes, strides, target_type).verify()


# TC-DMA-010
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-22 00:00:00 +0800
# 功能说明: 验证动态 offsets/sizes 下，strides 不接受 StringAttr。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_dynamic_offsets_sizes_reject_string_stride
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_dynamic_offsets_sizes_reject_string_stride() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("M"), StringAttr("N")]),
        stride=ArrayAttr([StringAttr("N"), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("TM"), StringAttr("?")]),
        stride=ArrayAttr([StringAttr("TN"), IntAttr(1)]),
        space="shared",
    )
    source = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_index_list(["m0", "?"])
    sizes = _make_index_list(["TM", "?"])
    strides = _make_index_list([1, "?"])
    op = DmaLoadOp(source, offsets, sizes, strides, result_type, _make_space("shared"))
    with pytest.raises(VerifyException, match="IntAttr\\(1\\)"):
        op.verify()


# TC-DMA-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 18:26:48 +0800
# 最近一次运行成功时间: 2026-03-21 18:26:48 +0800
# 功能说明: 验证 dma.cast 在 shape/stride/space 一致时允许 element_type 不同。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_cast_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_cast_verify_success() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    op = DmaCastOp(source, result_type)
    op.verify()


# TC-DMA-012
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 18:26:48 +0800
# 最近一次运行成功时间: 2026-03-21 18:26:48 +0800
# 功能说明: 验证 dma.cast 在 shape/stride/space 不一致时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_cast_layout_or_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_cast_layout_or_space_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]

    result_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(5)]))
    op = DmaCastOp(source, result_type)
    with pytest.raises(VerifyException, match="dma.cast shape mismatch"):
        op.verify()

    result_type = _make_memory_type(stride=ArrayAttr([IntAttr(5), IntAttr(1)]))
    op = DmaCastOp(source, result_type)
    with pytest.raises(VerifyException, match="dma.cast stride mismatch"):
        op.verify()

    result_type = _make_memory_type(space="shared")
    op = DmaCastOp(source, result_type)
    with pytest.raises(VerifyException, match="dma.cast space mismatch"):
        op.verify()


# TC-DMA-013
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:58:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:58:00 +0800
# 功能说明: 验证 dma.alloc 合法路径，并覆盖 alloc/view/reshape 的 parse/print round-trip。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_alloc_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_alloc_verify_success() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "dma.alloc"() : () -> !nn.memory<[2, 4], [4, 1], i32, #nn.space<global>>
  %1 = "dma.view"(%0) : (!nn.memory<[2, 4], [4, 1], i32, #nn.space<global>>) -> !nn.memory<[4, 2], [2, 1], i32, #nn.space<global>>
  %2 = "dma.reshape"(%0) : (!nn.memory<[2, 4], [4, 1], i32, #nn.space<global>>) -> !nn.memory<[4, 2], [2, 1], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()


# TC-DMA-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:58:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:58:00 +0800
# 功能说明: 验证 dma.view 在 element_type 或 space 不一致时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_view_type_or_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_view_type_or_space_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]

    result_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    op = DmaViewOp(source, result_type)
    with pytest.raises(VerifyException, match="element_type mismatch"):
        op.verify()

    result_type = _make_memory_type(space="shared")
    op = DmaViewOp(source, result_type)
    with pytest.raises(VerifyException, match="space mismatch"):
        op.verify()


# TC-DMA-015
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:58:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:58:00 +0800
# 功能说明: 验证 dma.view 在可判定元素总数不一致时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_view_numel_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_view_numel_mismatch() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(5), IntAttr(1)]),
    )
    op = DmaViewOp(source, result_type)
    with pytest.raises(VerifyException, match="numel mismatch"):
        op.verify()


# TC-DMA-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:58:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:58:00 +0800
# 功能说明: 验证 dma.reshape 在非连续布局时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_reshape_requires_contiguous
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_reshape_requires_contiguous() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(5), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(4), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, result_type)
    with pytest.raises(VerifyException, match="contiguous source"):
        op.verify()


# TC-DMA-017
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-21 23:40:00 +0800
# 最近一次运行成功时间: 2026-03-21 23:40:00 +0800
# 功能说明: 验证 dma.reshape 支持符号维度并遵循连续 stride 规则。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_reshape_allows_symbolic_shape
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_reshape_allows_symbolic_shape() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("N"), IntAttr(8)]),
        stride=ArrayAttr([IntAttr(8), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(4), StringAttr("M")]),
        stride=ArrayAttr([StringAttr("M"), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, result_type)
    op.verify()


# TC-DMA-018
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-21 23:40:00 +0800
# 最近一次运行成功时间: 2026-03-21 23:40:00 +0800
# 功能说明: 验证 dma.reshape 在符号维度下 stride 非连续时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_reshape_symbolic_stride_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_reshape_symbolic_stride_mismatch() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("N"), IntAttr(8)]),
        stride=ArrayAttr([IntAttr(9), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, result_type)
    with pytest.raises(VerifyException, match="contiguous result stride"):
        op.verify()


# TC-DMA-013
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-22 00:00:00 +0800
# 功能说明: 验证 dma dynamic shape/index 的 parse/print round-trip 覆盖 alloc/view/load/store/slice/deslice/reshape/cast。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_dynamic_shape_parse_print_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_dynamic_shape_parse_print_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "dma.alloc"() : () -> !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>
  %1 = "dma.view"(%0) : (!nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> !nn.memory<[?, N], [VIEW_STRIDE, 1], i32, #nn.space<global>>
  %2 = "dma.load"(%0) {offsets = ["m0", "?"], sizes = ["TM", "?"], strides = [#builtin.int<1>, #builtin.int<1>], space = #nn.space<shared>} : (!nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> !nn.memory<[TM, ?], [TN, 1], i32, #nn.space<shared>>
  "dma.store"(%2, %0) {offsets = ["m0", "?"], sizes = ["TM", "?"], strides = [#builtin.int<1>, #builtin.int<1>]} : (!nn.memory<[TM, ?], [TN, 1], i32, #nn.space<shared>>, !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> ()
  %3 = "dma.slice"(%0) {offsets = ["m0", "?"], sizes = ["TM", "?"], strides = [#builtin.int<1>, #builtin.int<1>], space = #nn.space<local>} : (!nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> !nn.memory<[TM, ?], [TN, 1], i32, #nn.space<local>>
  %4 = "dma.deslice"(%3, %0) {offsets = ["m0", "?"], sizes = ["TM", "?"], strides = [#builtin.int<1>, #builtin.int<1>]} : (!nn.memory<[TM, ?], [TN, 1], i32, #nn.space<local>>, !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>
  %5 = "dma.reshape"(%0) : (!nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> !nn.memory<[4, ?], [RESHAPE_STRIDE, 1], i32, #nn.space<global>>
  %6 = "dma.cast"(%0) : (!nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> !nn.memory<[M, N], [N, 1], i1, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()
