"""kernel dialect tests.

创建者: 小李飞刀
最后一次更改: 大闸蟹

功能说明:
- 覆盖 kernel dialect 的 verifier 约束与 memory type 复用规则。

使用示例:
- pytest -q test/dialect/test_kernel_dialect.py

当前覆盖率信息: 100%（2026-03-22 13:05:49 +0800）
覆盖率命令: pytest -q --cov=kernel_gen.dialect.kernel --cov-report=term-missing test/dialect/test_kernel_dialect.py

关联文件:
- 功能实现: kernel_gen/dialect/kernel.py
- Spec 文档: spec/dialect/kernel.md
- 测试文件: test/dialect/test_kernel_dialect.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    i1,
    i32,
)
from xdsl.dialects.test import TestOp as _TestOp
from xdsl.ir import Attribute, SSAValue
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.kernel import (
    _verify_element_type_match,
    _verify_memory_type,
    _verify_same_layout,
    KernelAddOp,
    KernelCastOp,
    KernelDivOp,
    KernelEqOp,
    KernelExpOp,
    KernelGtOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelLtOp,
    KernelMatmulOp,
    KernelMulOp,
    KernelReduceMinOp,
    KernelSoftmaxOp,
    KernelSelectOp,
    KernelSubOp,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType


def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造 space attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 简化测试中的空间构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _make_memory_type(
    shape: ArrayAttr | None = None,
    stride: ArrayAttr | None = None,
    element_type: Attribute = i32,
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
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if shape is None:
        shape = ArrayAttr([IntAttr(2), IntAttr(4)])
    if stride is None:
        stride = ArrayAttr([IntAttr(4), IntAttr(1)])
    return NnMemoryType(shape, stride, element_type, _make_space(space))


def _make_value(memory_type: NnMemoryType):
    """构造携带 memory type 的 SSA value。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 TestOp 生成带类型的 SSAValue。

    使用示例:
    - _make_value(_make_memory_type())

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    return _TestOp(result_types=[memory_type]).results[0]


def _const_i32(value: int) -> SSAValue:
    """构造 i32 常量 SSA value。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 生成 `arith.constant` i32 常量，供 kernel img2col 参数 operand 使用。

    使用示例:
    - k = _const_i32(3)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel_dialect.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    return arith.ConstantOp(IntegerAttr(value, i32)).result


# TC-KRN-001
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证合法 space 可通过校验。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_space_attr_valid
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_space_attr_valid() -> None:
    space = _make_space("global")
    space.verify()


# TC-KRN-002
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证非法 space 被拒绝。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_space_attr_invalid
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_space_attr_invalid() -> None:
    with pytest.raises(VerifyException, match="nn space"):
        NnMemorySpaceAttr(StringAttr("invalid"))


# TC-KRN-003
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证 shape/stride rank 不一致被拒绝。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_memory_type_rank_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_memory_type_rank_mismatch() -> None:
    with pytest.raises(VerifyException, match="shape and stride rank"):
        _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]), stride=ArrayAttr([IntAttr(1)]))


# TC-KRN-004
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证 kernel.add 正常路径可通过。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_add_success
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_add_success() -> None:
    memory_type = _make_memory_type()
    lhs = _make_value(memory_type)
    rhs = _make_value(memory_type)
    out = _make_value(memory_type)
    op = KernelAddOp(lhs, rhs, out, _make_space("global"))
    op.verify()


# TC-KRN-005
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证 kernel.add shape 不一致报错。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_add_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_add_shape_mismatch() -> None:
    lhs_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    rhs_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(5)]))
    out_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    op = KernelAddOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="shape must match"):
        op.verify()

    lhs_type = _make_memory_type(stride=ArrayAttr([IntAttr(4), IntAttr(1)]))
    rhs_type = _make_memory_type(stride=ArrayAttr([IntAttr(5), IntAttr(1)]))
    out_type = _make_memory_type(stride=ArrayAttr([IntAttr(4), IntAttr(1)]))
    op = KernelAddOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="stride must match"):
        op.verify()

    lhs_type = _make_memory_type(space="global")
    rhs_type = _make_memory_type(space="local")
    out_type = _make_memory_type(space="global")
    op = KernelAddOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="same space"):
        op.verify()

    lhs_type = _make_memory_type(space="global")
    rhs_type = _make_memory_type(space="global")
    out_type = _make_memory_type(space="global")
    op = KernelAddOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("local"))
    with pytest.raises(VerifyException, match="attribute space"):
        op.verify()

    lhs_type = _make_memory_type(element_type=i32)
    rhs_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=Float32Type())
    op = KernelAddOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="kernel arithmetic element_type must match"):
        op.verify()

    invalid_lhs = _TestOp(result_types=[i32]).results[0]
    with pytest.raises(VerifyException, match="lhs must be nn.memory"):
        _verify_memory_type(invalid_lhs.type, "lhs")


# TC-KRN-006
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证 kernel.eq 输出类型为 i1。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_eq_output_type
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_eq_output_type() -> None:
    lhs_type = _make_memory_type(element_type=i32)
    rhs_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i1)
    op = KernelEqOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("global"))
    op.verify()


# TC-KRN-007
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证 kernel.eq 输出类型非法报错。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_eq_output_type_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_eq_output_type_error() -> None:
    lhs_type = _make_memory_type(element_type=i32)
    rhs_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i32)
    op = KernelEqOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="compare output element_type must be i1"):
        op.verify()

    lt_op = KernelLtOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="compare output element_type must be i1"):
        lt_op.verify()

    gt_op = KernelGtOp(_make_value(lhs_type), _make_value(rhs_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="compare output element_type must be i1"):
        gt_op.verify()


# TC-KRN-008
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证 kernel.select 条件类型非法报错。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_select_cond_type_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_select_cond_type_error() -> None:
    cond_type = _make_memory_type(element_type=i32)
    lhs_type = _make_memory_type(element_type=i32)
    rhs_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i32)
    op = KernelSelectOp(
        _make_value(cond_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        _make_value(out_type),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="cond element_type must be i1"):
        op.verify()

    cond_type = _make_memory_type(element_type=i1)
    op = KernelSelectOp(
        _make_value(cond_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        _make_value(out_type),
        _make_space("global"),
    )
    op.verify()


# TC-KRN-009
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证 kernel.cast 类型非法报错。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_cast_type_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_cast_type_error() -> None:
    input_type = _make_memory_type(element_type=i1)
    out_type = _make_memory_type(element_type=i32)
    op = KernelCastOp(_make_value(input_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="kernel.cast element_type"):
        op.verify()


# TC-KRN-010
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-22 13:05:49 +0800
# 最近一次运行成功时间: 2026-03-22 13:05:49 +0800
# 功能说明: 验证 kernel op 不产生 SSA result。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_ops_no_result
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_ops_no_result() -> None:
    memory_type = _make_memory_type()
    lhs = _make_value(memory_type)
    rhs = _make_value(memory_type)
    out = _make_value(memory_type)
    add_op = KernelAddOp(lhs, rhs, out, _make_space("global"))
    sub_op = KernelSubOp(lhs, rhs, out, _make_space("global"))
    mul_op = KernelMulOp(lhs, rhs, out, _make_space("global"))
    div_op = KernelDivOp(lhs, rhs, out, _make_space("global"))
    eq_op = KernelEqOp(lhs, rhs, _make_value(_make_memory_type(element_type=i1)), _make_space("global"))
    gt_op = KernelGtOp(lhs, rhs, _make_value(_make_memory_type(element_type=i1)), _make_space("global"))
    lt_op = KernelLtOp(lhs, rhs, _make_value(_make_memory_type(element_type=i1)), _make_space("global"))
    select_op = KernelSelectOp(
        _make_value(_make_memory_type(element_type=i1)),
        lhs,
        rhs,
        out,
        _make_space("global"),
    )
    cast_input = _make_value(_make_memory_type(element_type=Float32Type()))
    cast_output = _make_value(_make_memory_type(element_type=Float16Type()))
    cast_op = KernelCastOp(cast_input, cast_output, _make_space("global"))
    exp_input = _make_value(_make_memory_type(element_type=Float32Type()))
    exp_output = _make_value(_make_memory_type(element_type=Float32Type()))
    exp_op = KernelExpOp(exp_input, exp_output, _make_space("global"))
    softmax_input = _make_value(_make_memory_type(element_type=Float32Type()))
    softmax_output = _make_value(_make_memory_type(element_type=Float32Type()))
    softmax_op = KernelSoftmaxOp(softmax_input, softmax_output, axis=1, space=_make_space("global"))
    img2col_input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(75), IntAttr(25), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    img2col_output_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(243), IntAttr(81), IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    img2col_op = KernelImg2col2dOp(
        _make_value(img2col_input_type),
        _make_value(img2col_output_type),
        kh=_const_i32(3),
        kw=_const_i32(3),
        sh=_const_i32(1),
        sw=_const_i32(1),
        dh=_const_i32(1),
        dw=_const_i32(1),
        ph=_const_i32(0),
        pw=_const_i32(0),
        pl=_const_i32(0),
        pr=_const_i32(0),
        space=_make_space("global"),
    )
    img2col1d_input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(15), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    img2col1d_output_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    img2col1d_op = KernelImg2col1dOp(
        _make_value(img2col1d_input_type),
        _make_value(img2col1d_output_type),
        k=_const_i32(3),
        s=_const_i32(1),
        d=_const_i32(1),
        p_left=_const_i32(0),
        p_right=_const_i32(0),
        space=_make_space("global"),
    )
    for op in (
        add_op,
        sub_op,
        mul_op,
        div_op,
        eq_op,
        gt_op,
        lt_op,
        select_op,
        cast_op,
        exp_op,
        softmax_op,
        img2col1d_op,
        img2col_op,
    ):
        op.verify()
        assert len(op.results) == 0

    _verify_same_layout([], _make_space("global"))
    _verify_element_type_match([], "unused")


# TC-KRN-011
# 创建者: 小李飞刀
# 最后一次更改: 大闸蟹
# 最近一次运行测试时间: 2026-04-08 10:20:49 +0800
# 最近一次运行成功时间: 2026-04-08 10:20:49 +0800
# 功能说明: 验证 kernel.exp 正常路径可通过。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_exp_success
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_exp_success() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(element_type=Float32Type())
    op = KernelExpOp(_make_value(input_type), _make_value(out_type), _make_space("global"))
    op.verify()


# TC-KRN-013
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 10:51:30 +0800
# 最近一次运行成功时间: 2026-04-08 10:51:30 +0800
# 功能说明: 验证 kernel.exp 支持 bf16 element_type。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_exp_supports_bf16
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_exp_supports_bf16() -> None:
    input_type = _make_memory_type(element_type=BFloat16Type())
    out_type = _make_memory_type(element_type=BFloat16Type())
    op = KernelExpOp(_make_value(input_type), _make_value(out_type), _make_space("global"))
    op.verify()


# TC-KRN-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 10:20:49 +0800
# 最近一次运行成功时间: 2026-04-08 10:20:49 +0800
# 功能说明: 验证 kernel.exp 拒绝非浮点 element_type。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_exp_requires_float
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_exp_requires_float() -> None:
    input_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i32)
    op = KernelExpOp(_make_value(input_type), _make_value(out_type), _make_space("global"))
    with pytest.raises(VerifyException, match="kernel.exp element_type must be float"):
        op.verify()


# TC-KRN-014
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 13:13:24 +0800
# 最近一次运行成功时间: 2026-04-08 13:13:24 +0800
# 功能说明: 验证 kernel.matmul dtype mismatch 被拒绝。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_matmul_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_matmul_dtype_mismatch() -> None:
    lhs_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(3)]),
        element_type=Float32Type(),
    )
    rhs_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(4)]),
        element_type=Float16Type(),
    )
    out_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        element_type=Float32Type(),
    )
    op = KernelMatmulOp(
        _make_value(lhs_type),
        _make_value(rhs_type),
        _make_value(out_type),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.matmul element_type"):
        op.verify()


# TC-KRN-015
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 13:13:24 +0800
# 最近一次运行成功时间: 2026-04-08 13:13:24 +0800
# 功能说明: 验证 kernel.matmul 拒绝非二维 operand 与形状不匹配。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_matmul_rank_shape_contract
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_matmul_rank_shape_contract() -> None:
    lhs_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(3)]))
    rhs_rank3_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(3), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(12), IntAttr(4), IntAttr(1)]),
    )
    out_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    op = KernelMatmulOp(
        _make_value(lhs_type),
        _make_value(rhs_rank3_type),
        _make_value(out_type),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.matmul requires rank-2"):
        op.verify()

    rhs_mismatch_type = _make_memory_type(shape=ArrayAttr([IntAttr(5), IntAttr(4)]))
    op = KernelMatmulOp(
        _make_value(lhs_type),
        _make_value(rhs_mismatch_type),
        _make_value(out_type),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.matmul contracting dimensions"):
        op.verify()


# TC-KRN-017
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-09 00:00:00 +0800
# 功能说明: 验证 kernel.img2col1d/img2col2d 保持结构化输出与显式窗口属性。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_img2col_structured_contract
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_img2col_structured_contract() -> None:
    img2col1d_input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(15), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    img2col1d_output_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    KernelImg2col1dOp(
        _make_value(img2col1d_input_type),
        _make_value(img2col1d_output_type),
        k=_const_i32(3),
        s=_const_i32(1),
        d=_const_i32(1),
        p_left=_const_i32(0),
        p_right=_const_i32(0),
        space=_make_space("global"),
    ).verify()

    img2col2d_input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(75), IntAttr(25), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    img2col2d_output_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(243), IntAttr(81), IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    KernelImg2col2dOp(
        _make_value(img2col2d_input_type),
        _make_value(img2col2d_output_type),
        kh=_const_i32(3),
        kw=_const_i32(3),
        sh=_const_i32(1),
        sw=_const_i32(1),
        dh=_const_i32(1),
        dw=_const_i32(1),
        ph=_const_i32(0),
        pw=_const_i32(0),
        pl=_const_i32(0),
        pr=_const_i32(0),
        space=_make_space("global"),
    ).verify()


# TC-KRN-018
# 创建者: 小李飞刀
# 最后一次更改: 大闸蟹
# 最近一次运行测试时间: 2026-04-09 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-09 00:00:00 +0800
# 功能说明: 验证 kernel.img2col1d/img2col2d 拒绝非法输入 rank 或 layout。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_img2col_input_rank_layout_contract
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_img2col_input_rank_layout_contract() -> None:
    img2col1d_output_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    rank2_input = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d requires rank-3 input"):
        KernelImg2col1dOp(
            _make_value(rank2_input),
            _make_value(img2col1d_output_type),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    non_contiguous_1d_input = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(15), IntAttr(1), IntAttr(3)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d input layout must be contiguous"):
        KernelImg2col1dOp(
            _make_value(non_contiguous_1d_input),
            _make_value(img2col1d_output_type),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    img2col1d_input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(15), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    rank3_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d requires rank-4 result"):
        KernelImg2col1dOp(
            _make_value(img2col1d_input_type),
            _make_value(rank3_output),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    img2col2d_output_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(243), IntAttr(81), IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    rank3_2d_input = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(5), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(25), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d requires rank-4 input"):
        KernelImg2col2dOp(
            _make_value(rank3_2d_input),
            _make_value(img2col2d_output_type),
            kh=_const_i32(3),
            kw=_const_i32(3),
            sh=_const_i32(1),
            sw=_const_i32(1),
            dh=_const_i32(1),
            dw=_const_i32(1),
            ph=_const_i32(0),
            pw=_const_i32(0),
            pl=_const_i32(0),
            pr=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    non_contiguous_2d_input = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(75), IntAttr(1), IntAttr(15), IntAttr(3)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d input layout must be contiguous"):
        KernelImg2col2dOp(
            _make_value(non_contiguous_2d_input),
            _make_value(img2col2d_output_type),
            kh=_const_i32(3),
            kw=_const_i32(3),
            sh=_const_i32(1),
            sw=_const_i32(1),
            dh=_const_i32(1),
            dw=_const_i32(1),
            ph=_const_i32(0),
            pw=_const_i32(0),
            pl=_const_i32(0),
            pr=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    img2col2d_input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(75), IntAttr(25), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    rank5_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(81), IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d requires rank-6 result"):
        KernelImg2col2dOp(
            _make_value(img2col2d_input_type),
            _make_value(rank5_output),
            kh=_const_i32(3),
            kw=_const_i32(3),
            sh=_const_i32(1),
            sw=_const_i32(1),
            dh=_const_i32(1),
            dw=_const_i32(1),
            ph=_const_i32(0),
            pw=_const_i32(0),
            pl=_const_i32(0),
            pr=_const_i32(0),
            space=_make_space("global"),
        ).verify()


# TC-KRN-019
# 创建者: 小李飞刀
# 最后一次更改: 大闸蟹
# 最近一次运行测试时间: 2026-04-09 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-09 00:00:00 +0800
# 功能说明: 验证 kernel.img2col1d/img2col2d 拒绝结构化输出形状与推导关系不一致（含公式结果 < 1）。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_img2col_output_extent_contract
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_img2col_output_extent_contract() -> None:
    img2col1d_input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(15), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    bad_window_axis_1d_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(2), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(18), IntAttr(6), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d result shape/stride must match img2col1d contract"):
        KernelImg2col1dOp(
            _make_value(img2col1d_input_type),
            _make_value(bad_window_axis_1d_output),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    bad_extent_1d_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(18), IntAttr(6), IntAttr(2), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d result shape/stride must match img2col1d contract"):
        KernelImg2col1dOp(
            _make_value(img2col1d_input_type),
            _make_value(bad_extent_1d_output),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    bad_stride_1d_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(30), IntAttr(10), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d result shape/stride must match img2col1d contract"):
        KernelImg2col1dOp(
            _make_value(img2col1d_input_type),
            _make_value(bad_stride_1d_output),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    short_1d_input = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(1)]),
        stride=ArrayAttr([IntAttr(3), IntAttr(1), IntAttr(1)]),
        element_type=Float32Type(),
    )
    short_1d_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(1)]),
        stride=ArrayAttr([IntAttr(9), IntAttr(3), IntAttr(1), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d result shape/stride must match img2col1d contract"):
        KernelImg2col1dOp(
            _make_value(short_1d_input),
            _make_value(short_1d_output),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    img2col2d_input_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(75), IntAttr(25), IntAttr(5), IntAttr(1)]),
        element_type=Float32Type(),
    )
    bad_window_axis_2d_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(2), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(162), IntAttr(54), IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(img2col2d_input_type),
            _make_value(bad_window_axis_2d_output),
            kh=_const_i32(3),
            kw=_const_i32(3),
            sh=_const_i32(1),
            sw=_const_i32(1),
            dh=_const_i32(1),
            dw=_const_i32(1),
            ph=_const_i32(0),
            pw=_const_i32(0),
            pl=_const_i32(0),
            pr=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    bad_extent_2d_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(2), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(162), IntAttr(54), IntAttr(18), IntAttr(6), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(img2col2d_input_type),
            _make_value(bad_extent_2d_output),
            kh=_const_i32(3),
            kw=_const_i32(3),
            sh=_const_i32(1),
            sw=_const_i32(1),
            dh=_const_i32(1),
            dw=_const_i32(1),
            ph=_const_i32(0),
            pw=_const_i32(0),
            pl=_const_i32(0),
            pr=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    bad_stride_2d_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(200), IntAttr(80), IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(img2col2d_input_type),
            _make_value(bad_stride_2d_output),
            kh=_const_i32(3),
            kw=_const_i32(3),
            sh=_const_i32(1),
            sw=_const_i32(1),
            dh=_const_i32(1),
            dw=_const_i32(1),
            ph=_const_i32(0),
            pw=_const_i32(0),
            pl=_const_i32(0),
            pr=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    short_2d_input = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(1), IntAttr(1)]),
        stride=ArrayAttr([IntAttr(3), IntAttr(1), IntAttr(1), IntAttr(1)]),
        element_type=Float32Type(),
    )
    short_2d_output = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(1), IntAttr(1)]),
        stride=ArrayAttr([IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1), IntAttr(1), IntAttr(1)]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(short_2d_input),
            _make_value(short_2d_output),
            kh=_const_i32(3),
            kw=_const_i32(3),
            sh=_const_i32(1),
            sw=_const_i32(1),
            dh=_const_i32(1),
            dw=_const_i32(1),
            ph=_const_i32(0),
            pw=_const_i32(0),
            pl=_const_i32(0),
            pr=_const_i32(0),
            space=_make_space("global"),
        ).verify()


# TC-KRN-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 21:12:06 +0800
# 最近一次运行成功时间: 2026-04-08 21:12:06 +0800
# 功能说明: 验证 kernel.softmax 正常路径可通过。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_softmax_success
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_softmax_success() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(element_type=Float32Type())
    op = KernelSoftmaxOp(_make_value(input_type), _make_value(out_type), axis=1, space=_make_space("global"))
    op.verify()


# TC-KRN-020
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 21:12:06 +0800
# 最近一次运行成功时间: 2026-04-08 21:12:06 +0800
# 功能说明: 验证 kernel.softmax axis 越界会报错。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_softmax_axis_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_softmax_axis_error() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(element_type=Float32Type())
    op = KernelSoftmaxOp(_make_value(input_type), _make_value(out_type), axis=2, space=_make_space("global"))
    with pytest.raises(VerifyException, match="axis must be within"):
        op.verify()


# TC-KRN-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 21:12:06 +0800
# 最近一次运行成功时间: 2026-04-08 21:12:06 +0800
# 功能说明: 验证 kernel.softmax 拒绝非浮点 element_type。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_softmax_requires_float
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_softmax_requires_float() -> None:
    input_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i32)
    op = KernelSoftmaxOp(_make_value(input_type), _make_value(out_type), axis=1, space=_make_space("global"))
    with pytest.raises(VerifyException, match="kernel.softmax element_type must be float"):
        op.verify()


# TC-KRN-023
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-09 04:20:00 +0800
# 最近一次运行成功时间: 2026-04-09 04:20:00 +0800
# 功能说明: 验证 kernel.reduce_min 正常路径可通过。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_reduce_min_success
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_reduce_min_success() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(1)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(1)]),
        element_type=Float32Type(),
    )
    op = KernelReduceMinOp(
        _make_value(input_type),
        _make_value(out_type),
        axis=1,
        keepdim=True,
        space=_make_space("global"),
    )
    op.verify()


# TC-KRN-020
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-09 04:20:00 +0800
# 最近一次运行成功时间: 2026-04-09 04:20:00 +0800
# 功能说明: 验证 kernel.reduce_min axis 越界会报错。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_reduce_min_axis_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_reduce_min_axis_error() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(1)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(1)]),
        element_type=Float32Type(),
    )
    op = KernelReduceMinOp(
        _make_value(input_type),
        _make_value(out_type),
        axis=2,
        keepdim=True,
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="axis must be within"):
        op.verify()


# TC-KRN-022
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-09 05:50:19 +0800
# 最近一次运行成功时间: 2026-04-09 05:50:19 +0800
# 功能说明: 验证 kernel.reduce_min 拒绝 out.shape 不一致。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_reduce_min_out_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_reduce_min_out_shape_mismatch() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
        element_type=Float32Type(),
    )
    op = KernelReduceMinOp(
        _make_value(input_type),
        _make_value(out_type),
        axis=1,
        keepdim=True,
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.reduce_min out shape must match reduce contract"):
        op.verify()


# TC-KRN-021
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-09 05:31:18 +0800
# 最近一次运行成功时间: 2026-04-09 05:31:18 +0800
# 功能说明: 验证 kernel.reduce_min 拒绝 keepdim 非 i1。
# 使用示例: pytest -q test/dialect/test_kernel_dialect.py -k test_kernel_reduce_min_keepdim_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel_dialect.py
def test_kernel_reduce_min_keepdim_error() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(1)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(1)]),
        element_type=Float32Type(),
    )
    op = KernelReduceMinOp(
        _make_value(input_type),
        _make_value(out_type),
        axis=1,
        keepdim=IntegerAttr(2, IntegerType(8)),
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="keepdim must be i1"):
        op.verify()
