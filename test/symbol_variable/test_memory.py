"""memory tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 Memory/MemorySpace/LocalSpaceMeta 构造、表示与转换行为。

使用示例:
- pytest -q test/symbol_variable/test_memory.py

关联文件:
- 功能实现: python/symbol_variable/memory.py
- Spec 文档: spec/symbol_variable/memory.md
- 测试文件: test/symbol_variable/test_memory.py
"""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.symbol_variable.memory import LocalSpaceMeta, Memory, MemorySpace
from python.symbol_variable.symbol_shape import SymbolShape
from python.symbol_variable.type import Farmat, NumericType


# ME-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证默认空间为 GM。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_default_space
# 对应功能实现文件路径: python/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_default_space() -> None:
    mem = Memory([1, 2], NumericType.Float32)
    assert mem.space is MemorySpace.GM


# ME-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证指定空间写入。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_custom_space
# 对应功能实现文件路径: python/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_custom_space() -> None:
    mem = Memory([1], NumericType.Int32, space=MemorySpace.LM)
    assert mem.space is MemorySpace.LM


# ME-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 __repr__ 包含空间名与张量字段表达。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_repr
# 对应功能实现文件路径: python/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_repr() -> None:
    mem = Memory([1, 2], NumericType.Float32)
    rep = repr(mem)
    assert rep.startswith("Memory(GM,")
    assert "Tensor(" in rep
    assert "shape=" in rep
    assert "dtype=" in rep


# ME-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 tensor-like 字段直入构造保持 shape/dtype/stride/format。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_construct_from_tensor_fields
# 对应功能实现文件路径: python/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_construct_from_tensor_fields() -> None:
    class DummyTensor:
        def __init__(self, shape, dtype, stride, format):
            self.shape = shape
            self.dtype = dtype
            self.stride = stride
            self.format = format

    tensor = DummyTensor(["N", 4], NumericType.Float32, stride=[4, 1], format=Farmat.Norm)
    mem = Memory(
        tensor.shape,
        tensor.dtype,
        stride=tensor.stride,
        format=tensor.format,
    )
    assert isinstance(mem, Memory)
    assert mem.space is MemorySpace.GM
    assert mem.shape.get_values() == ["N", 4]
    assert mem.dtype is tensor.dtype
    assert mem.stride.get_values() == [4, 1]
    assert mem.format is tensor.format


# ME-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 shape/stride 可直接接收 SymbolShape。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_shape_stride_accept_symbol_shape
# 对应功能实现文件路径: python/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_shape_stride_accept_symbol_shape() -> None:
    shape = SymbolShape([1, "N"])
    stride = SymbolShape([2, 1])
    mem = Memory(shape, NumericType.Float32, stride=stride)
    assert mem.shape is shape
    assert mem.stride is stride


# ME-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 format 语义映射（c last=NHWC，c not last=NCHW）。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_format_mapping
# 对应功能实现文件路径: python/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_format_mapping() -> None:
    assert Farmat.Norm.value == "NCHW"
    assert Farmat.CLast.value == "NHWC"
    assert Farmat.Norm is Farmat.NCHW
    assert Farmat.CLast is Farmat.NHWC
    assert Farmat.Norm.name == "NCHW"
    assert "Farmat.NCHW" in repr(Farmat.Norm)


# ME-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 01:43:13 +0800
# 最近一次运行成功时间: 2026-03-16 01:43:13 +0800
# 功能说明: 验证 LocalSpaceMeta 冻结与 MemorySpace 元信息字段。
# 使用示例: pytest -q test/symbol_variable/test_memory.py -k test_space_meta
# 对应功能实现文件路径: python/symbol_variable/memory.py
# 对应 spec 文件路径: spec/symbol_variable/memory.md
# 对应测试文件路径: test/symbol_variable/test_memory.py
def test_space_meta() -> None:
    meta = MemorySpace.GM.value
    assert isinstance(meta, LocalSpaceMeta)
    assert meta.name == "GM"
    assert meta.align == 1024
    with pytest.raises(FrozenInstanceError):
        meta.align = 256
