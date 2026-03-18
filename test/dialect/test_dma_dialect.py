"""dma dialect tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 dma dialect 的 op verifier 与类型复用约束。

使用示例:
- pytest -q test/dialect/test_dma_dialect.py

关联文件:
- 功能实现: python/dialect/dma.py
- Spec 文档: spec/dialect/dma.md
- 测试文件: test/dialect/test_dma_dialect.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, Builtin, IntAttr, StringAttr, i32
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.dialect.dma import (
    Dma,
    DmaCopyOp,
    DmaDesliceOp,
    DmaLoadOp,
    DmaSliceOp,
    DmaStoreOp,
)
from python.dialect.nn import Nn, NnMemorySpaceAttr, NnMemoryType


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
    - 功能实现: python/dialect/dma.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Dma)
    return ctx


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
    - 功能实现: python/dialect/dma.py
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
    - 功能实现: python/dialect/dma.py
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
    - 功能实现: python/dialect/dma.py
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
# 对应功能实现文件路径: python/dialect/dma.py
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
# 对应功能实现文件路径: python/dialect/dma.py
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
# 对应功能实现文件路径: python/dialect/dma.py
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
# 功能说明: 验证 dma.load 的 result.space 必须与 op.space 一致。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_load_result_space_mismatch
# 对应功能实现文件路径: python/dialect/dma.py
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


# TC-DMA-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.slice 索引长度与 rank 不一致时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_slice_rank_mismatch
# 对应功能实现文件路径: python/dialect/dma.py
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


# TC-DMA-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.slice 在非 1 stride 下明确报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_slice_non_unit_stride_rejected
# 对应功能实现文件路径: python/dialect/dma.py
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
    with pytest.raises(VerifyException, match="stride must be 1"):
        op.verify()


# TC-DMA-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.store 的 source.shape 与 sizes 不一致会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_store_size_mismatch
# 对应功能实现文件路径: python/dialect/dma.py
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
# 对应功能实现文件路径: python/dialect/dma.py
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
# 对应功能实现文件路径: python/dialect/dma.py
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
# 对应功能实现文件路径: python/dialect/dma.py
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
