"""dma facade smoke tests.


功能说明:
- 保留 `test_operation_dma.py` 作为 dma helper 的兼容冒烟入口。
- 具体 alloc/lifecycle 与 transfer/view 用例已拆分到独立 family 文件。
- 当前文件额外覆盖 `fill` 的最小公开合同。

使用示例:
- pytest -q test/operation/test_dma.py

关联文件:
- 功能实现: kernel_gen/operation/dma.py
- Spec 文档: spec/operation/dma.md
- 测试文件: test/operation/test_dma.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation.dma import alloc, broadcast, copy, fill, view
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


# TC-OP-DMA-FACADE-001
# 测试目的: 验证 dma smoke 入口仍可直接调用 alloc/copy。
# 使用示例: pytest -q test/operation/test_dma.py -k test_dma_facade_alloc_copy_smoke
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_dma.py
def test_dma_facade_alloc_copy_smoke() -> None:
    source = alloc([2, 2], NumericType.Float32)
    copied = copy(source, MemorySpace.SM)
    assert source.get_shape() == [2, 2]
    assert copied.space is MemorySpace.SM


# TC-OP-DMA-FACADE-002
# 测试目的: 验证 dma smoke 入口仍可直接调用 view。
# 使用示例: pytest -q test/operation/test_dma.py -k test_dma_facade_view_smoke
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_dma.py
def test_dma_facade_view_smoke() -> None:
    result = view(Memory([4, 4], NumericType.Float32), offset=[0, 0], size=[2, 2], stride=[1, 1])
    assert result.get_shape() == [2, 2]


# TC-OP-DMA-FACADE-003
# 测试目的: 验证 `kernel_gen.operation.dma.fill` 作为公开 helper 返回 None，且不替换目标对象。
# 使用示例: pytest -q test/operation/test_dma.py -k test_dma_facade_fill_returns_none
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_dma.py
def test_dma_facade_fill_returns_none() -> None:
    target = alloc([2, 2], NumericType.Float32)
    assert fill(target, 0) is None
    assert target.get_shape() == [2, 2]


# TC-OP-DMA-FACADE-004
# 测试目的: 验证 `fill` 对非法字符串字面量在公开 helper 层直接拒绝。
# 使用示例: pytest -q test/operation/test_dma.py -k test_dma_facade_fill_rejects_invalid_string_literal
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_dma.py
def test_dma_facade_fill_rejects_invalid_string_literal() -> None:
    target = alloc([2, 2], NumericType.Float32)
    try:
        fill(target, "nan")
    except KernelCodeError as exc:
        assert 'fill string literal must be "inf" or "-inf"' in str(exc)
    else:
        raise AssertionError("expected KernelCodeError for invalid fill string literal")


# TC-OP-DMA-FACADE-005
# 测试目的: 验证 `fill` 拒绝 bool 与非有限 float，保留有限 float 与规范 inf 字符串。
# 使用示例: pytest -q test/operation/test_dma.py -k test_dma_facade_fill_rejects_bool_and_nonfinite_float
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_dma.py
def test_dma_facade_fill_rejects_bool_and_nonfinite_float() -> None:
    target = alloc([2, 2], NumericType.Float32)
    assert fill(target, 1.5) is None
    assert fill(target, "inf") is None
    assert fill(target, "-inf") is None

    for value, expected in ((True, "fill value must"), (float("inf"), "finite float"), (float("nan"), "finite float")):
        try:
            fill(target, value)
        except KernelCodeError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"expected KernelCodeError for {value!r}")


# TC-OP-DMA-FACADE-006
# 测试目的: 验证 `dma.broadcast(target, source)` 作为 target-first 公开 helper 返回 None。
# 使用示例: pytest -q test/operation/test_dma.py -k test_dma_facade_broadcast_returns_none
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_dma.py
def test_dma_facade_broadcast_returns_none() -> None:
    target = Memory([4, 8], NumericType.Float32, space=MemorySpace.SM)
    source = Memory([1, 8], NumericType.Float32, space=MemorySpace.SM)

    assert broadcast(target, source) is None


# TC-OP-DMA-FACADE-007
# 测试目的: 验证 `dma.broadcast` 拒绝 rank、dtype、space 与静态 shape 不兼容。
# 使用示例: pytest -q test/operation/test_dma.py -k test_dma_facade_broadcast_rejects_invalid_contract
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_dma.py
def test_dma_facade_broadcast_rejects_invalid_contract() -> None:
    target = Memory([4, 8], NumericType.Float32, space=MemorySpace.SM)

    for source, expected in (
        (Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.SM), "rank"),
        (Memory([1, 8], NumericType.Int32, space=MemorySpace.SM), "dtype"),
        (Memory([1, 8], NumericType.Float32, space=MemorySpace.GM), "space"),
        (Memory([2, 7], NumericType.Float32, space=MemorySpace.SM), "shape"),
    ):
        try:
            broadcast(target, source)
        except KernelCodeError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"expected KernelCodeError for {expected}")
