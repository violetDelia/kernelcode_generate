"""nn structured family tests.


功能说明:
- 覆盖 `kernel_gen.operation.nn` 的 family 级测试布局。

使用示例:
- pytest -q test/operation/nn/test_structured.py

关联文件:
- 功能实现: kernel_gen/operation/nn/__init__.py
- Spec 文档: spec/operation/nn.md
- 测试文件: test/operation/nn/test_structured.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import kernel_gen.operation as operation_api
import kernel_gen.operation.nn as operation_nn

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation.nn import (
    add,
    broadcast,
    broadcast_to,
    conv,
    eq,
    exp,
    fc,
    floordiv,
    ge,
    gt,
    hard_sigmoid,
    img2col1d,
    img2col2d,
    leaky_relu,
    le,
    lt,
    matmul,
    mul,
    ne,
    relu,
    reduce_max,
    reduce_min,
    reduce_sum,
    sigmoid,
    softmax,
    sub,
    tanh,
    transpose,
    truediv,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolList, SymbolShape
from kernel_gen.symbol_variable.type import Farmat, NumericType


# OP-FC-001
# 测试目的: 验证 fc 在无 bias 场景下保留批维并输出默认布局。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_fc_without_bias
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_fc_without_bias() -> None:
    value = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    weight = Memory([5, 4], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    result = fc(value, weight)
    assert result.shape.get_values() == [2, 3, 5]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.GM
    assert result.format is Farmat.Norm
    assert result.get_stride() == [15, 5, 1]


# OP-FC-002
# 测试目的: 验证 fc 支持可选 bias 且与输出特征维对齐。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_fc_with_optional_bias
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_fc_with_optional_bias() -> None:
    value = Memory(["B", "K"], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory(["N", "K"], NumericType.Float32, space=MemorySpace.GM)
    bias = Memory(["N"], NumericType.Float32, space=MemorySpace.GM)
    result = fc(value, weight, bias=bias)
    assert result.shape.get_values() == ["B", "N"]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.GM


# OP-FC-003
# 测试目的: 验证 fc 对非法类型输入报 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_fc_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_fc_type_error() -> None:
    value = Memory([2, 3], NumericType.Float32)
    weight = Memory([4, 3], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = fc("bad", weight)
    with pytest.raises(KernelCodeError):
        _ = fc(value, "bad")
    with pytest.raises(KernelCodeError):
        _ = fc(value, weight, bias=1.0)


# OP-FC-004
# 测试目的: 验证 fc 的 value/weight rank 约束报错。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_fc_rank_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_fc_rank_error() -> None:
    value = Memory([4], NumericType.Float32)
    weight = Memory([5, 4], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = fc(value, weight)
    value_ok = Memory([2, 4], NumericType.Float32)
    weight_bad = Memory([2, 4, 6], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = fc(value_ok, weight_bad)


# OP-FC-005
# 测试目的: 验证 fc 输入特征维不一致报错。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_fc_feature_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_fc_feature_mismatch() -> None:
    value = Memory([2, 3, 4], NumericType.Float32)
    weight = Memory([5, 6], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = fc(value, weight)


# OP-FC-006
# 测试目的: 验证 fc bias 维度不对齐报错。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_fc_bias_shape_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_fc_bias_shape_error() -> None:
    value = Memory([2, 3, 4], NumericType.Float32)
    weight = Memory([5, 4], NumericType.Float32)
    bias_rank = Memory([1, 5], NumericType.Float32)
    bias_mismatch = Memory([4], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = fc(value, weight, bias=bias_rank)
    with pytest.raises(KernelCodeError):
        _ = fc(value, weight, bias=bias_mismatch)


# OP-FC-007
# 测试目的: 验证 fc space 不一致报错。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_fc_space_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_fc_space_mismatch() -> None:
    value = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([4, 3], NumericType.Float32, space=MemorySpace.SM)
    with pytest.raises(KernelCodeError):
        _ = fc(value, weight)
    bias = Memory([4], NumericType.Float32, space=MemorySpace.SM)
    weight_ok = Memory([4, 3], NumericType.Float32, space=MemorySpace.GM)
    with pytest.raises(KernelCodeError):
        _ = fc(value, weight_ok, bias=bias)


# OP-FC-008
# 测试目的: 验证 fc 输出可继续参与 nn 算术链路。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_fc_chain_compatibility
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_fc_chain_compatibility() -> None:
    value = Memory([2, 3], NumericType.Float32)
    weight = Memory([4, 3], NumericType.Float32)
    result = fc(value, weight)
    combined = add(result, Memory([2, 4], NumericType.Float32))
    assert combined.shape.get_values() == [2, 4]
    assert combined.dtype is NumericType.Float32


# OP-MM-001
# 测试目的: 验证 matmul 基础二维矩阵乘输出 shape/dtype/space。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_matmul_success
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_matmul_success() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32, format=Farmat.CLast)
    rhs = Memory(["K", "N"], NumericType.Float32, stride=["N", 1], format=Farmat.CLast)
    result = matmul(lhs, rhs)
    assert isinstance(result, Memory)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32
    assert result.space is lhs.space
    assert result.format is Farmat.Norm
    assert result.get_stride() == ["N", 1]


# OP-MM-002
# 测试目的: 验证 matmul 显式 memoryspace 仅覆盖结果 space。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_matmul_space_override
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_matmul_space_override() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    rhs = Memory(["K", "N"], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    result = matmul(lhs, rhs, memoryspace=MemorySpace.SM)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.SM
    assert result.format is Farmat.Norm


# OP-MM-003
# 测试目的: 验证 matmul contracting dim 不一致报错。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_matmul_contracting_dim_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_matmul_contracting_dim_mismatch() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["Q", "N"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = matmul(lhs, rhs)


# OP-MM-004
# 测试目的: 验证 matmul 非二维输入报错。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_matmul_rank_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_matmul_rank_error() -> None:
    lhs = Memory(["B", "M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = matmul(lhs, rhs)


# OP-MM-005
# 测试目的: 验证 matmul 标量输入非法。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_matmul_scalar_operand_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_matmul_scalar_operand_error() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = matmul(lhs, 1)


# OP-MM-006
# 测试目的: 验证 matmul dtype 按固定优先级决议。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_matmul_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_matmul_dtype_mismatch() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Int32)
    result = matmul(lhs, rhs)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32


# OP-MM-007
# 测试目的: 验证 matmul space 不一致报错。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_matmul_space_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_matmul_space_mismatch() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32, space=MemorySpace.GM)
    rhs = Memory(["K", "N"], NumericType.Float32, space=MemorySpace.SM)
    with pytest.raises(KernelCodeError):
        _ = matmul(lhs, rhs)


# OP-IMG2COL-001
# 测试目的: 验证 img2col1d 输出形状与参数校验规则。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_img2col1d_contract
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_img2col1d_contract() -> None:
    value = Memory([1, 16, 32], NumericType.Float32, space=MemorySpace.GM)
    result = img2col1d(value, kw=3, sw=1, dw=1, pl=1, pr=1)
    expected = Memory([1, 16, 3, 32], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
    assert result.shape.get_values() == expected.shape.get_values()
    assert result.dtype is expected.dtype
    assert result.space is expected.space
    assert result.format is expected.format
    assert result.get_stride() == expected.get_stride()

    clast_value = Memory([1, 32, 16], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    clast_result = img2col1d(clast_value, kw=3, sw=1, dw=1, pl=1, pr=1)
    clast_expected = Memory([1, 32, 3, 16], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
    assert clast_result.shape.get_values() == clast_expected.shape.get_values()
    assert clast_result.dtype is clast_expected.dtype
    assert clast_result.space is clast_expected.space
    assert clast_result.format is clast_expected.format
    assert clast_result.get_stride() == clast_expected.get_stride()

    with pytest.raises(KernelCodeError):
        _ = img2col1d("bad", kw=3, sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col1d(Memory([1, 16, 32, 1], NumericType.Float32), kw=3, sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col1d(value, kw="3", sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col1d(value, kw=0, sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col1d(value, kw=3, sw=1, dw=1, pl=-1, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col1d(value, kw=True, sw=1, dw=1, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col1d(value, kw=64, sw=1, dw=1, pl=0, pr=0)


# OP-IMG2COL-002
# 测试目的: 验证 img2col2d 输出形状与参数校验规则。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_img2col2d_contract
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_img2col2d_contract() -> None:
    value = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)
    result = img2col2d(value, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)
    expected = Memory([1, 3, 3, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
    assert result.shape.get_values() == expected.shape.get_values()
    assert result.dtype is expected.dtype
    assert result.space is expected.space
    assert result.format is expected.format
    assert result.get_stride() == expected.get_stride()

    clast_value = Memory([1, 5, 5, 3], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    clast_result = img2col2d(clast_value, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)
    clast_expected = Memory([1, 5, 5, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
    assert clast_result.shape.get_values() == clast_expected.shape.get_values()
    assert clast_result.dtype is clast_expected.dtype
    assert clast_result.space is clast_expected.space
    assert clast_result.format is clast_expected.format
    assert clast_result.get_stride() == clast_expected.get_stride()

    with pytest.raises(KernelCodeError):
        _ = img2col2d("bad", kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col2d(Memory([1, 3, 5], NumericType.Float32), kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col2d(value, kh="3", kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col2d(value, kh=0, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col2d(value, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=-1, pw=0, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col2d(value, kh=True, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = img2col2d(value, kh=7, kw=7, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)


# 功能说明: 验证 operation 层公开导出仅要求 `img2col1d/img2col2d` 两个 family 入口可达，且 `kernel_gen.operation` 顶层不顺手暴露这些 structured helper。
# 测试目的: 锁定 `spec/operation/nn.md` 已定义的 `img2col1d/img2col2d` package-root 入口与顶层不外泄边界，不把未定义的模块元数据或子模块属性当公开合同。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_img2col_public_exports
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py, kernel_gen/operation/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_img2col_public_exports() -> None:
    assert operation_nn.img2col1d is img2col1d
    assert operation_nn.img2col2d is img2col2d
    assert not hasattr(operation_api, "img2col1d")
    assert not hasattr(operation_api, "img2col2d")
    assert not hasattr(operation_api, "img2col")


# OP-SM-001
# 测试目的: 验证 softmax 默认 axis=-1 且结果保持输入元信息。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_softmax_default_axis
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_softmax_default_axis() -> None:
    value = Memory([2, 3], NumericType.Float32, space=MemorySpace.LM, stride=SymbolShape([3, 1]))
    result = softmax(value)
    assert result.shape.get_values() == [2, 3]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.LM
    assert result.format is Farmat.Norm
    assert result.get_stride() == [3, 1]


# OP-SM-002
# 测试目的: 验证 softmax 负轴归一化路径。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_softmax_negative_axis
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_softmax_negative_axis() -> None:
    value = Memory(["B", "C", "H"], NumericType.Float16)
    result = softmax(value, axis=-2)
    assert result.shape.get_values() == ["B", "C", "H"]
    assert result.dtype is NumericType.Float16


# OP-SM-003
# 测试目的: 验证 softmax axis 非整数或为 bool 时抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_softmax_axis_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_softmax_axis_type_error() -> None:
    value = Memory([2, 3], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = softmax(value, axis=True)
    with pytest.raises(KernelCodeError):
        _ = softmax(value, axis=1.5)


# OP-SM-004
# 测试目的: 验证 softmax axis 越界抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_softmax_axis_out_of_range
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_softmax_axis_out_of_range() -> None:
    value = Memory([2, 3], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = softmax(value, axis=2)
    with pytest.raises(KernelCodeError):
        _ = softmax(value, axis=-3)


# OP-SM-005
# 测试目的: 验证 softmax 非浮点 dtype 抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_softmax_dtype_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_softmax_dtype_error() -> None:
    value = Memory([2, 3], NumericType.Int32)
    with pytest.raises(KernelCodeError):
        _ = softmax(value)


# OP-SM-006
# 测试目的: 验证 softmax 数值稳定性语义约束存在。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_softmax_numerical_stability_contract
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_softmax_numerical_stability_contract() -> None:
    doc = softmax.__doc__ or ""
    assert "exp(x - max(x)) / sum(exp(x - max(x)))" in doc
# OP-CONV-001
# 测试目的: 验证 conv 基础路径、输出形状与参数校验规则（含 bias 对齐）。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_conv_basic
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_conv_basic() -> None:
    value = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM)
    result = conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)
    assert result.shape.get_values() == [1, 8, 5, 5]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.GM
    assert result.format is Farmat.Norm
    assert result.get_stride() == [200, 25, 5, 1]

    bias = Memory([8], NumericType.Float32, space=MemorySpace.GM)
    _ = conv(value, weight, bias=bias, sh=2, sw=2, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

    with pytest.raises(KernelCodeError):
        _ = conv("bad", weight)
    with pytest.raises(KernelCodeError):
        _ = conv(value, "bad")
    with pytest.raises(KernelCodeError):
        _ = conv(Memory([1, 3, 5], NumericType.Float32), weight)
    with pytest.raises(KernelCodeError):
        _ = conv(value, Memory([8, 3, 3], NumericType.Float32))
    with pytest.raises(KernelCodeError):
        _ = conv(Memory([1, 4, 5, 5], NumericType.Float32), weight)
    with pytest.raises(KernelCodeError):
        _ = conv(Memory([1, 3, 5, 5], NumericType.Int32), weight)
    with pytest.raises(KernelCodeError):
        _ = conv(Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.SM), weight)

    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, bias="bad")
    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, bias=Memory([1, 8], NumericType.Float32))
    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, bias=Memory([4], NumericType.Float32))
    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, bias=Memory([8], NumericType.Int32))
    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, bias=Memory([8], NumericType.Float32, space=MemorySpace.SM))

    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, sh=0, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, sh=1, sw=1, dh=0, dw=1, ph=0, pw=0, pl=0, pr=0)
    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=-1, pw=0, pl=0, pr=0)
    with pytest.raises(KernelCodeError):
        _ = conv(value, weight, sh=True, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
    with pytest.raises(KernelCodeError):
        _ = conv(
            value,
            Memory([8, 3, 7, 7], NumericType.Float32, space=MemorySpace.GM),
            sh=1,
            sw=1,
            dh=1,
            dw=1,
            ph=0,
            pw=0,
            pl=0,
            pr=0,
        )
# OP-TP-001
# 测试目的: 验证 transpose 正例可按 perm 重排 shape，并生成连续 stride。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_transpose_success
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_transpose_success() -> None:
    value = Memory([2, 3, 4], NumericType.Float16, space=MemorySpace.LM, stride=[12, 4, 1], format=Farmat.CLast)
    result = transpose(value, perm=[2, 0, 1])
    assert result.shape.get_values() == [4, 2, 3]
    assert result.get_stride() == [6, 3, 1]
    assert result.dtype is NumericType.Float16
    assert result.space is MemorySpace.LM
    assert result.format is Farmat.CLast


# OP-TP-002
# 测试目的: 验证 transpose perm 长度不匹配或非排列时抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_transpose_invalid_perm_values
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_transpose_invalid_perm_values() -> None:
    value = Memory([2, 3], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = transpose(value, perm=[0, 1, 2])
    with pytest.raises(KernelCodeError):
        _ = transpose(value, perm=[0, 0])


# OP-TP-003
# 测试目的: 验证 transpose perm 元素类型非法时抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_transpose_invalid_perm_type
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_transpose_invalid_perm_type() -> None:
    value = Memory([2, 3], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = transpose(value, perm=[0, "1"])
    with pytest.raises(KernelCodeError):
        _ = transpose(value, perm=[0, True])


# OP-TP-004
# 测试目的: 验证 transpose 仍可通过 `kernel_gen.operation.nn` package-root 公开获取，且不会顺手上提到 `kernel_gen.operation` 顶层。
# 使用示例: pytest -q test/operation/nn/test_structured.py -k test_nn_transpose_exported_at_package_root
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_structured.py
def test_nn_transpose_exported_at_package_root() -> None:
    assert operation_nn.transpose is transpose
    assert not hasattr(operation_api, "transpose")
