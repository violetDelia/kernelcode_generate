"""nn reduction family tests.


功能说明:
- 覆盖 `kernel_gen.operation.nn` 的 family 级测试布局。

使用示例:
- pytest -q test/operation/nn/test_reduction.py

关联文件:
- 功能实现: kernel_gen/operation/nn/__init__.py
- Spec 文档: spec/operation/nn.md
- 测试文件: test/operation/nn/test_reduction.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation.nn import (
    reduce_max,
    reduce_min,
    reduce_sum,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import Farmat, NumericType


# OP-RD-001
# 测试目的: 验证 reduce_sum 的 axis=None/int/Sequence[int] 路径与输出 shape 推导。
# 使用示例: pytest -q test/operation/nn/test_reduction.py -k test_nn_reduce_sum_shape_contract
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_reduction.py
def test_nn_reduce_sum_shape_contract() -> None:
    value = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.LM, stride=[12, 4, 1], format=Farmat.CLast)
    all_sum = reduce_sum(value)
    dim1_sum = reduce_sum(value, axis=1, keepdim=True)
    seq_sum = reduce_sum(value, axis=[-1, 0], keepdim=False)

    assert all_sum.shape.get_values() == [1]
    assert all_sum.dtype is NumericType.Float32
    assert all_sum.space is MemorySpace.LM
    assert all_sum.format is Farmat.Norm
    assert all_sum.get_stride() == [1]

    assert dim1_sum.shape.get_values() == [2, 1, 4]
    assert dim1_sum.dtype is NumericType.Float32
    assert dim1_sum.space is MemorySpace.LM
    assert dim1_sum.format is Farmat.Norm
    assert dim1_sum.get_stride() == [4, 4, 1]

    assert seq_sum.shape.get_values() == [3]
    assert seq_sum.dtype is NumericType.Float32
    assert seq_sum.space is MemorySpace.LM
    assert seq_sum.format is Farmat.Norm
    assert seq_sum.get_stride() == [1]


# OP-RD-002
# 测试目的: 验证 reduce_sum 的 axis/keepdim 边界与异常路径。
# 使用示例: pytest -q test/operation/nn/test_reduction.py -k test_nn_reduce_sum_axis_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_reduction.py
def test_nn_reduce_sum_axis_error() -> None:
    value = Memory([2, 3, 4], NumericType.Float32)

    with pytest.raises(KernelCodeError):
        _ = reduce_sum(value, axis=True)
    with pytest.raises(KernelCodeError):
        _ = reduce_sum(value, axis=1.5)
    with pytest.raises(KernelCodeError):
        _ = reduce_sum(value, axis=[0, "1"])
    with pytest.raises(KernelCodeError):
        _ = reduce_sum(value, axis=3)
    with pytest.raises(KernelCodeError):
        _ = reduce_sum(value, axis=[0, -3])
    with pytest.raises(KernelCodeError):
        _ = reduce_sum(value, axis=[])
    with pytest.raises(KernelCodeError):
        _ = reduce_sum(value, keepdim=1)


# OP-RD-003
# 测试目的: 验证 reduce_min/reduce_max 的 keepdim 规则与输出元信息口径。
# 使用示例: pytest -q test/operation/nn/test_reduction.py -k test_nn_reduce_min_max_keepdim_contract
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_reduction.py
def test_nn_reduce_min_max_keepdim_contract() -> None:
    value = Memory([2, 3, 4], NumericType.Float16, space=MemorySpace.SM, stride=[12, 4, 1], format=Farmat.CLast)
    min_keepdim = reduce_min(value, axis=[2], keepdim=True)
    max_reduce = reduce_max(value, axis=0, keepdim=False)

    assert min_keepdim.shape.get_values() == [2, 3, 1]
    assert min_keepdim.dtype is NumericType.Float16
    assert min_keepdim.space is MemorySpace.SM
    assert min_keepdim.format is Farmat.Norm
    assert min_keepdim.get_stride() == [3, 1, 1]

    assert max_reduce.shape.get_values() == [3, 4]
    assert max_reduce.dtype is NumericType.Float16
    assert max_reduce.space is MemorySpace.SM
    assert max_reduce.format is Farmat.Norm
    assert max_reduce.get_stride() == [4, 1]


# OP-RD-004
# 测试目的: 验证 reduce_min/reduce_max 在静态空归约域时报错。
# 使用示例: pytest -q test/operation/nn/test_reduction.py -k test_nn_reduce_min_max_empty_extent_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_reduction.py
def test_nn_reduce_min_max_empty_extent_error() -> None:
    empty_axis = Memory([0, 4], NumericType.Float32)

    with pytest.raises(KernelCodeError):
        _ = reduce_min(empty_axis, axis=0)
    with pytest.raises(KernelCodeError):
        _ = reduce_max(empty_axis, axis=None)
