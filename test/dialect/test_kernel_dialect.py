"""kernel dialect tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 kernel dialect 的 verifier 约束与 memory type 复用规则。

使用示例:
- pytest -q test/dialect/test_kernel_dialect.py

关联文件:
- 功能实现: kernel_gen/dialect/kernel.py
- Spec 文档: spec/dialect/kernel.md
- 测试文件: test/dialect/test_kernel_dialect.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, i1, i32
from xdsl.dialects.test import TestOp as _TestOp
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.kernel import (
    KernelAddOp,
    KernelCastOp,
    KernelEqOp,
    KernelGtOp,
    KernelLtOp,
    KernelSelectOp,
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
    element_type=i32,
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


# TC-KRN-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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


# TC-KRN-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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


# TC-KRN-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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


# TC-KRN-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-21 21:56:08 +0800
# 最近一次运行成功时间: 2026-03-21 21:56:08 +0800
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
    cast_op = KernelCastOp(lhs, out, _make_space("global"))
    for op in (add_op, eq_op, gt_op, lt_op, select_op, cast_op):
        assert len(op.results) == 0
