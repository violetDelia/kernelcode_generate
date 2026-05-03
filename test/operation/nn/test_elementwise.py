"""nn elementwise family tests.


功能说明:
- 覆盖 `kernel_gen.operation.nn` 的 family 级测试布局。

使用示例:
- pytest -q test/operation/nn/test_elementwise.py

关联文件:
- 功能实现: kernel_gen/operation/nn/__init__.py
- Spec 文档: spec/operation/nn.md
- 测试文件: test/operation/nn/test_elementwise.py
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


# OP-001
# 测试目的: 验证 add API 可独立调用并保持形状。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_add_memory
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_add_memory() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    assert isinstance(result, Memory)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Float32


# OP-005
# 测试目的: 验证 Memory 与标量加法支持左右两侧。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_add_scalar
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_add_scalar() -> None:
    mem = Memory([2, 2], NumericType.Int32)
    left = add(mem, 1)
    right = add(1, mem)
    assert left.shape.get_values() == [2, 2]
    assert left.dtype is NumericType.Int32
    assert right.shape.get_values() == [2, 2]
    assert right.dtype is NumericType.Int32


# OP-006
# 测试目的: 验证链式表达式逐步检查形状与类型。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_chain_expression
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_chain_expression() -> None:
    lhs = Memory(["M", "N"], NumericType.Float32)
    rhs = Memory(["M", "N"], NumericType.Float32)
    result = add(add(lhs, 3), rhs)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32


# OP-003
# 测试目的: 验证 shape 不一致抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_shape_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_shape_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = add(lhs, rhs)


# OP-004
# 测试目的: 验证 rank 不一致抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_rank_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_rank_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = add(lhs, rhs)


# OP-014
# 测试目的: 验证 nn.add 的 dtype 按固定优先级决议。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py

def test_nn_dtype_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Int32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = add(lhs, rhs)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Float32
    scalar_result = add(Memory(["A"], NumericType.Int8), 1)
    assert scalar_result.dtype is NumericType.Int32


# OP-008
# 测试目的: 验证不支持的 dtype 触发 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_dtype_invalid_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_dtype_invalid_error() -> None:
    lhs = Memory(["A", "B"], NumericType.Bool)
    rhs = Memory(["A", "B"], NumericType.Int32)
    with pytest.raises(KernelCodeError):
        _ = add(lhs, rhs)


# OP-005A
# 测试目的: 验证 bool 标量可被接受。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_add_bool_scalar
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_add_bool_scalar() -> None:
    lhs = Memory(["A", "B"], NumericType.Int32)
    result = add(lhs, True)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Int32


# OP-007
# 测试目的: 验证标量类型不合法抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_scalar_type_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_scalar_type_error() -> None:
    mem = Memory([1], NumericType.Int32)
    with pytest.raises(KernelCodeError):
        _ = add(mem, "3")


# OP-009
# 测试目的: 验证比较 API 返回 predicate dtype。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_compare_predicate
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_compare_predicate() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    eq_result = eq(lhs, rhs)
    lt_result = lt(lhs, 0)
    gt_result = gt(0, lhs)
    with pytest.raises(KernelCodeError):
        _ = eq(Memory(["A", "B"], NumericType.Float32), Memory(["A", "B"], NumericType.Int32))
    assert eq_result.shape.get_values() == ["A", "B"]
    assert eq_result.dtype is NumericType.Bool
    assert lt_result.dtype is NumericType.Bool
    assert gt_result.dtype is NumericType.Bool


# OP-010
# 测试目的: 验证比较时 shape 顺序不同抛 KernelCodeError。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_compare_shape_order
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_compare_shape_order() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["B", "A"], NumericType.Float32)
    with pytest.raises(KernelCodeError):
        _ = eq(lhs, rhs)


# OP-002A
# 测试目的: 验证其他算术 API 保持形状。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_other_arithmetic
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_other_arithmetic() -> None:
    lhs = Memory([2, 2], NumericType.Int32)
    rhs = Memory([2, 2], NumericType.Int32)
    assert sub(lhs, rhs).shape.get_values() == [2, 2]
    assert mul(lhs, 2).shape.get_values() == [2, 2]
    assert truediv(lhs, 1).shape.get_values() == [2, 2]


# OP-002B
# 测试目的: 验证 sub 的 dtype 规则与标量反向调用。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_sub_reverse_and_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_sub_reverse_and_dtype_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Int32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    result = sub(lhs, rhs)
    assert result.shape.get_values() == ["A", "B"]
    assert result.dtype is NumericType.Float32
    reverse = sub(1, lhs)
    assert reverse.shape.get_values() == ["A", "B"]


# OP-002
# 测试目的: 验证 sub 在 format/stride 不一致时回落默认布局。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_sub_format_fallback
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_sub_format_fallback() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.CLast)
    rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 2], format=Farmat.Norm)
    result = sub(lhs, rhs)
    assert result.get_format() is Farmat.Norm
    assert result.get_stride()[1] == 1


# OP-017
# 测试目的: 验证 floordiv 复用算术规则、支持标量并覆盖错误路径。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_floordiv_rules
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_floordiv_rules() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32)
    rhs = Memory([1, "N"], NumericType.Float32, format=Farmat.CLast)
    result = floordiv(lhs, rhs)
    assert result.shape.get_values() == ["M", "N"]
    assert result.dtype is NumericType.Float32
    assert result.format is Farmat.Norm
    assert result.get_stride()[1] == 1
    scalar_result = floordiv(lhs, 2)
    assert scalar_result.shape.get_values() == ["M", "N"]
    assert scalar_result.dtype is NumericType.Int32
    reverse_result = floordiv(2, lhs)
    assert reverse_result.shape.get_values() == ["M", "N"]
    assert reverse_result.dtype is NumericType.Int32
    with pytest.raises(KernelCodeError):
        _ = floordiv(lhs, Memory(["K"], NumericType.Int32))


# OP-011
# 测试目的: 验证逐元素算术包装在纯标量输入下复用 Python/SymbolDim 算术语义，并保持非法标量类型报错。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_scalar_only_error
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_scalar_only_error() -> None:
    symbol = SymbolDim("N")

    assert add(1, 2) == 3
    assert sub(5, 2) == 3
    assert truediv(6, 3) == 2.0
    assert floordiv(7, 3) == 2
    assert add(1, symbol).get_value() == "N + 1"
    assert sub(5, symbol).get_value() == "5 - N"
    assert mul(2, symbol).get_value() == "2*N"
    assert floordiv(7, symbol).get_value() == "7 // N"

    with pytest.raises(KernelCodeError):
        _ = add("lhs", "rhs")


# OP-012
# 测试目的: 验证比较操作对称 API 可用。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_compare_alias
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_compare_alias() -> None:
    lhs = Memory([1], NumericType.Int32)
    rhs = Memory([1], NumericType.Int32)
    assert ne(lhs, rhs).dtype is NumericType.Bool
    assert le(lhs, rhs).dtype is NumericType.Bool
    assert ge(lhs, rhs).dtype is NumericType.Bool


# OP-013
# 测试目的: 验证 nn 链路在迁移后不依赖已移除的 convert_from_* 入口。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_operation_does_not_require_convert_from_list
# 对应功能实现文件路径: kernel_gen/symbol_variable/memory.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_operation_does_not_require_convert_from_list() -> None:
    assert not hasattr(SymbolList, "convert_from_list")
    assert not hasattr(SymbolShape, "convert_from_list")

    lhs = Memory(["N", 32], NumericType.Float32, stride=["C", 1])
    rhs = Memory(["N", 32], NumericType.Float32, stride=["C", 1])

    result = add(lhs, rhs)

    assert result.shape.get_values() == ["N", 32]
    assert result.stride is not None
    assert result.stride.get_values() == ["C", 1]


# OP-015
# 测试目的: 验证 format 不一致时回落默认布局。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_add_format_fallback
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py

def test_nn_add_format_fallback() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.CLast)
    rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.Norm)
    result = add(lhs, rhs)
    assert result.get_format() is Farmat.Norm
    assert result.get_stride()[1] == 1


# OP-016A
# 测试目的: 验证 stride 不一致时回落默认布局。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_add_stride_fallback
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py

def test_nn_add_stride_fallback() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1])
    rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 2])
    result = add(lhs, rhs)
    assert result.get_format() is Farmat.Norm
    assert result.get_stride()[1] == 1


# OP-016
# 测试目的: 验证 stride 序列化维度的符号与常量路径。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_add_stride_dim_serialization
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_add_stride_dim_serialization() -> None:
    lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.CLast)
    rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.CLast)
    result = add(lhs, rhs)
    assert result.get_stride() == ["N", 1]


# OP-018
# 测试目的: 验证公开 add / leaky_relu 对非法标量与激活参数直接失败。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_helper_validation_branches
# 对应功能实现文件路径: kernel_gen/operation/nn/common.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_helper_validation_branches() -> None:
    with pytest.raises(KernelCodeError, match="Unsupported scalar type for nn operation"):
        _ = add(Memory([2, 2], NumericType.Int32), object())

    with pytest.raises(KernelCodeError, match="must be int or float"):
        _ = leaky_relu(Memory([2, 2], NumericType.Float32), alpha=True)

    with pytest.raises(KernelCodeError, match="must be int or float"):
        _ = leaky_relu(Memory([2, 2], NumericType.Float32), alpha=SymbolDim("N"))

    with pytest.raises(KernelCodeError, match="must be finite"):
        _ = leaky_relu(Memory([2, 2], NumericType.Float32), alpha=float("inf"))


# OP-ACT-001
# 测试目的: 验证 relu/sigmoid/tanh/hard_sigmoid 输出继承输入描述。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_activation_basic
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_activation_basic() -> None:
    value = Memory([2, 3], NumericType.Float32, space=MemorySpace.SM, stride=[3, 1], format=Farmat.CLast)
    for func in (relu, sigmoid, tanh):
        result = func(value)
        assert result.shape.get_values() == value.shape.get_values()
        assert result.dtype is value.dtype
        assert result.space is value.space
        assert result.format is value.format
        assert result.get_stride() == value.get_stride()

    hard_result = hard_sigmoid(value, alpha=0.2, beta=0.5)
    assert hard_result.shape.get_values() == value.shape.get_values()
    assert hard_result.dtype is value.dtype
    assert hard_result.space is value.space
    assert hard_result.format is value.format
    assert hard_result.get_stride() == value.get_stride()


# OP-ACT-002
# 测试目的: 验证 leaky_relu alpha 参数接受有限数值并继承输入描述。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_activation_leaky_relu_alpha
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_activation_leaky_relu_alpha() -> None:
    value = Memory([4, 1], NumericType.Float16, space=MemorySpace.GM, stride=[1, 1], format=Farmat.Norm)
    for alpha in (0.01, 0, -0.5, 2):
        result = leaky_relu(value, alpha=alpha)
        assert result.shape.get_values() == value.shape.get_values()
        assert result.dtype is value.dtype
        assert result.space is value.space
        assert result.format is value.format
        assert result.get_stride() == value.get_stride()


# OP-ACT-003
# 测试目的: 验证激活函数对非法输入、dtype 与参数报错。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_activation_invalid_input
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_activation_invalid_input() -> None:
    value = Memory([2, 2], NumericType.Float32)

    with pytest.raises(KernelCodeError):
        _ = relu("bad")

    with pytest.raises(KernelCodeError):
        _ = sigmoid(Memory([2, 2], NumericType.Int32))

    with pytest.raises(KernelCodeError):
        _ = tanh(Memory([2, 2], NumericType.Bool))

    with pytest.raises(KernelCodeError):
        _ = leaky_relu(value, alpha=True)

    with pytest.raises(KernelCodeError):
        _ = leaky_relu(value, alpha=SymbolDim("N"))

    with pytest.raises(KernelCodeError):
        _ = leaky_relu(value, alpha=float("nan"))

    with pytest.raises(KernelCodeError):
        _ = leaky_relu(value, alpha=float("inf"))

    with pytest.raises(KernelCodeError):
        _ = hard_sigmoid(value, alpha=True, beta=0.5)

    with pytest.raises(KernelCodeError):
        _ = hard_sigmoid(value, alpha=0.2, beta=SymbolDim("B"))

    with pytest.raises(KernelCodeError):
        _ = hard_sigmoid(value, alpha=0.2, beta=float("-inf"))


# OP-EXP-001
# 测试目的: 验证 exp 仅接受浮点 Memory 且输出继承输入元信息。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_exp_basic
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_exp_basic() -> None:
    value = Memory([2, 3], NumericType.Float32, space=MemorySpace.SM, stride=[3, 1], format=Farmat.CLast)
    result = exp(value)
    assert result.shape.get_values() == [2, 3]
    assert result.dtype is NumericType.Float32
    assert result.space is MemorySpace.SM
    assert result.format is Farmat.CLast
    assert result.get_stride() == [3, 1]


# OP-EXP-002
# 测试目的: 验证 exp 对非 Memory 或非浮点 dtype 输入报错。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_exp_invalid_input
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
# 对应测试文件路径: test/operation/nn/test_elementwise.py
def test_nn_exp_invalid_input() -> None:
    with pytest.raises(KernelCodeError):
        _ = exp("bad")
    with pytest.raises(KernelCodeError):
        _ = exp(Memory([2, 3], NumericType.Int32))


# OP-RD-001
# 测试目的: 验证 reduce_sum 的 axis=None/int/Sequence[int] 路径与输出 shape 推导。
# 使用示例: pytest -q test/operation/nn/test_elementwise.py -k test_nn_reduce_sum_shape_contract
# 对应功能实现文件路径: kernel_gen/operation/nn/__init__.py
# 对应 spec 文件路径: spec/operation/nn.md
