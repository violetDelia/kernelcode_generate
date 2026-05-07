"""kernel dialect tests.


功能说明:
- 覆盖 kernel dialect 的 verifier 约束与 memory type 复用规则。

使用示例:
- pytest -q test/dialect/test_kernel.py

当前覆盖率信息: 100%（2026-03-22 13:05:49 +0800）
覆盖率命令: pytest -q --cov=kernel_gen.dialect.kernel --cov-report=term-missing test/dialect/test_kernel.py

关联文件:
- 功能实现: kernel_gen/dialect/kernel.py
- Spec 文档: spec/dialect/kernel.md
- 测试文件: test/dialect/test_kernel.py
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
    UnrealizedConversionCastOp,
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
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceOp,
    KernelReduceMinOp,
    KernelSelectOp,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolValueType


def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造 space attribute。


    功能说明:
    - 简化测试中的空间构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _expr_attr(value: int | str) -> SymbolExprAttr:
    """构造公开 SymbolExprAttr。

    功能说明:
    - 为 kernel dialect 测试统一生成结构化 memory shape/stride 表达。

    使用示例:
    - _expr_attr("N")
    """

    return SymbolExprAttr.from_expr(str(value))


def _dim_array(values: list[int | str | SymbolExprAttr]) -> ArrayAttr[Attribute]:
    """构造 memory shape/stride 结构化维度。

    功能说明:
    - 使用公开 SymbolExprAttr 表达 memory layout，避免旧 IntAttr/StringAttr layout 入口。

    使用示例:
    - _dim_array([2, "N"])
    """

    return ArrayAttr([value if isinstance(value, SymbolExprAttr) else _expr_attr(value) for value in values])


def _make_memory_type(
    shape: ArrayAttr | None = None,
    stride: ArrayAttr | None = None,
    element_type: Attribute = i32,
    space: str = "global",
) -> NnMemoryType:
    """构造 nn.memory type。


    功能说明:
    - 提供默认可通过 verifier 的 memory type。

    使用示例:
    - _make_memory_type()

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    if shape is None:
        shape = _dim_array([2, 4])
    if stride is None:
        stride = _dim_array([4, 1])
    return NnMemoryType(shape, stride, element_type, _make_space(space))


def _make_value(memory_type: NnMemoryType):
    """构造携带 memory type 的 SSA value。


    功能说明:
    - 使用 TestOp 生成带类型的 SSAValue。

    使用示例:
    - _make_value(_make_memory_type())

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    return _TestOp(result_types=[memory_type]).results[0]


def _const_i32(value: int) -> SSAValue:
    """构造 i32 常量 SSA value。


    功能说明:
    - 生成 `arith.constant` i32 常量，供 kernel img2col 参数 operand 使用。

    使用示例:
    - k = _const_i32(3)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    return arith.ConstantOp(IntegerAttr(value, i32)).result


def _symbol_const_i32(value: int) -> SSAValue:
    """构造 symbol.const 常量 SSA value。


    功能说明:
    - 生成 `symbol.const` 结果，供 kernel img2col 参数 operand 校验使用。

    使用示例:
    - k = _symbol_const_i32(3)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    return SymbolConstOp(value).result


def _cast_i32_to_symbol(value: int) -> SSAValue:
    """构造公开 unrealized cast 后的 symbol.int SSA value。


    功能说明:
    - 通过 xDSL 公开 `builtin.unrealized_conversion_cast` 模拟 parser / lowering 常见的整数到 symbol.int 桥接。

    使用示例:
    - k = _cast_i32_to_symbol(3)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel.py
    """

    cast = UnrealizedConversionCastOp.get(
        [_const_i32(value)],
        [SymbolValueType.from_expr(str(value))],
    )
    return cast.results[0]


# TC-KRN-001
# 功能说明: 验证合法 space 可通过校验。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_space_attr_valid
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_space_attr_valid() -> None:
    space = _make_space("global")
    space.verify()


# TC-KRN-002
# 功能说明: 验证非法 space 被拒绝。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_space_attr_invalid
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_space_attr_invalid() -> None:
    with pytest.raises(VerifyException, match="nn space"):
        NnMemorySpaceAttr(StringAttr("invalid"))


# TC-KRN-003
# 功能说明: 验证 shape/stride rank 不一致被拒绝。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_memory_type_rank_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_memory_type_rank_mismatch() -> None:
    with pytest.raises(VerifyException, match="shape and stride rank"):
        _make_memory_type(shape=_dim_array([2, 4]), stride=_dim_array([1]))


# TC-KRN-004
# 功能说明: 验证 kernel.binary_elewise(kind="add") 正常路径可通过。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_binary_elewise_add_success
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_binary_elewise_add_success() -> None:
    memory_type = _make_memory_type()
    lhs = _make_value(memory_type)
    rhs = _make_value(memory_type)
    out = _make_value(memory_type)
    op = KernelBinaryElewiseOp(out, lhs, rhs, kind="add", space=_make_space("global"))
    op.verify()


# TC-KRN-005
# 功能说明: 验证 kernel.binary_elewise(kind="add") 的 layout 或 element_type 不一致时报错。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_binary_elewise_add_layout_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_binary_elewise_add_layout_mismatch() -> None:
    lhs_type = _make_memory_type(shape=_dim_array([2, 4]))
    rhs_type = _make_memory_type(shape=_dim_array([2, 5]))
    out_type = _make_memory_type(shape=_dim_array([2, 4]))
    op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="add",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="shape must match"):
        op.verify()

    lhs_type = _make_memory_type(stride=_dim_array([4, 1]))
    rhs_type = _make_memory_type(stride=_dim_array([5, 1]))
    out_type = _make_memory_type(stride=_dim_array([4, 1]))
    op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="add",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="stride must match"):
        op.verify()

    lhs_type = _make_memory_type(space="global")
    rhs_type = _make_memory_type(space="local")
    out_type = _make_memory_type(space="global")
    op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="add",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="same space"):
        op.verify()

    lhs_type = _make_memory_type(space="global")
    rhs_type = _make_memory_type(space="global")
    out_type = _make_memory_type(space="global")
    op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="add",
        space=_make_space("local"),
    )
    with pytest.raises(VerifyException, match="attribute space"):
        op.verify()

    lhs_type = _make_memory_type(element_type=i32)
    rhs_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=Float32Type())
    op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="add",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.binary_elewise element_type must match"):
        op.verify()

    invalid_lhs = _TestOp(result_types=[i32]).results[0]
    invalid_op = KernelBinaryElewiseOp(
        _make_value(out_type),
        invalid_lhs,
        _make_value(rhs_type),
        kind="add",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="base attribute nn.memory"):
        invalid_op.verify()


# TC-KRN-006
# 功能说明: 验证 kernel.binary_elewise(kind="eq") 的输出类型为 i1。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_binary_elewise_compare_output_type
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_binary_elewise_compare_output_type() -> None:
    lhs_type = _make_memory_type(element_type=i32)
    rhs_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i1)
    op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="eq",
        space=_make_space("global"),
    )
    op.verify()


# TC-KRN-007
# 功能说明: 验证 kernel.binary_elewise 比较类输出类型非法或 kind 非法时报错。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_binary_elewise_compare_output_type_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_binary_elewise_compare_output_type_error() -> None:
    lhs_type = _make_memory_type(element_type=i32)
    rhs_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i32)
    op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="eq",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="compare output element_type must be i1"):
        op.verify()

    lt_op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="lt",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="compare output element_type must be i1"):
        lt_op.verify()

    gt_op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        kind="gt",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="compare output element_type must be i1"):
        gt_op.verify()

    bool_rhs_op = KernelBinaryElewiseOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(_make_memory_type(element_type=i1)),
        kind="eq",
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="compare output element_type must be i1"):
        bool_rhs_op.verify()

    with pytest.raises(VerifyException, match="kind must be one of"):
        KernelBinaryElewiseOp(
            _make_value(_make_memory_type()),
            _make_value(_make_memory_type()),
            _make_value(_make_memory_type()),
            kind="pow",
            space=_make_space("global"),
        )


# TC-KRN-024
# 功能说明: 验证 kernel.binary_elewise 公开 kind 输入矩阵与非字符串拒绝边界。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_binary_elewise_public_kind_matrix
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_binary_elewise_public_kind_matrix() -> None:
    memory_type = _make_memory_type()
    bool_memory_type = _make_memory_type(element_type=i1)
    lhs = _make_value(memory_type)
    rhs = _make_value(memory_type)

    for kind in ("sub", "mul", "div", "truediv"):
        KernelBinaryElewiseOp(
            _make_value(memory_type),
            lhs,
            rhs,
            kind=StringAttr(kind),
            space=_make_space("global"),
        ).verify()

    for kind in ("ne", "le", "ge"):
        KernelBinaryElewiseOp(
            _make_value(bool_memory_type),
            lhs,
            rhs,
            kind=kind,
            space=_make_space("global"),
        ).verify()

    with pytest.raises(VerifyException, match="kernel.binary_elewise kind must be string"):
        KernelBinaryElewiseOp(
            _make_value(memory_type),
            lhs,
            rhs,
            kind=IntAttr(1),
            space=_make_space("global"),
        )


# TC-KRN-008
# 功能说明: 验证 kernel.select 条件类型非法报错。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_select_cond_type_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_select_cond_type_error() -> None:
    cond_type = _make_memory_type(element_type=i32)
    lhs_type = _make_memory_type(element_type=i32)
    rhs_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i32)
    op = KernelSelectOp(
        _make_value(out_type),
        _make_value(cond_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="cond element_type must be i1"):
        op.verify()

    cond_type = _make_memory_type(element_type=i1)
    op = KernelSelectOp(
        _make_value(out_type),
        _make_value(cond_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        _make_space("global"),
    )
    op.verify()


# TC-KRN-010
# 功能说明: 验证 kernel op 不产生 SSA result。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_ops_no_result
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_ops_no_result() -> None:
    memory_type = _make_memory_type()
    lhs = _make_value(memory_type)
    rhs = _make_value(memory_type)
    out = _make_value(memory_type)
    add_op = KernelBinaryElewiseOp(out, lhs, rhs, kind="add", space=_make_space("global"))
    eq_op = KernelBinaryElewiseOp(
        _make_value(_make_memory_type(element_type=i1)),
        lhs,
        rhs,
        kind="eq",
        space=_make_space("global"),
    )
    select_op = KernelSelectOp(
        out,
        _make_value(_make_memory_type(element_type=i1)),
        lhs,
        rhs,
        _make_space("global"),
    )
    exp_input = _make_value(_make_memory_type(element_type=Float32Type()))
    exp_output = _make_value(_make_memory_type(element_type=Float32Type()))
    exp_op = KernelExpOp(exp_output, exp_input, _make_space("global"))
    img2col_input_type = _make_memory_type(
        shape=_dim_array([1, 3, 5, 5]),
        stride=_dim_array([75, 25, 5, 1]),
        element_type=Float32Type(),
    )
    img2col_output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3, 3, 3]),
        stride=_dim_array([243, 81, 27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    img2col_op = KernelImg2col2dOp(
        _make_value(img2col_output_type),
        _make_value(img2col_input_type),
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
        shape=_dim_array([1, 3, 5]),
        stride=_dim_array([15, 5, 1]),
        element_type=Float32Type(),
    )
    img2col1d_output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3]),
        stride=_dim_array([27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    img2col1d_op = KernelImg2col1dOp(
        _make_value(img2col1d_output_type),
        _make_value(img2col1d_input_type),
        k=_const_i32(3),
        s=_const_i32(1),
        d=_const_i32(1),
        p_left=_const_i32(0),
        p_right=_const_i32(0),
        space=_make_space("global"),
    )
    for op in (
        add_op,
        eq_op,
        select_op,
        exp_op,
        img2col1d_op,
        img2col_op,
    ):
        op.verify()
        assert len(op.results) == 0


# TC-KRN-011
# 功能说明: 验证 kernel.exp 正常路径可通过。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_exp_success
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_exp_success() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(element_type=Float32Type())
    op = KernelExpOp(_make_value(out_type), _make_value(input_type), _make_space("global"))
    op.verify()


# TC-KRN-013
# 功能说明: 验证 kernel.exp 支持 bf16 element_type。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_exp_supports_bf16
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_exp_supports_bf16() -> None:
    input_type = _make_memory_type(element_type=BFloat16Type())
    out_type = _make_memory_type(element_type=BFloat16Type())
    op = KernelExpOp(_make_value(out_type), _make_value(input_type), _make_space("global"))
    op.verify()


# TC-KRN-012
# 功能说明: 验证 kernel.exp 拒绝非浮点 element_type。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_exp_requires_float
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_exp_requires_float() -> None:
    input_type = _make_memory_type(element_type=i32)
    out_type = _make_memory_type(element_type=i32)
    op = KernelExpOp(_make_value(out_type), _make_value(input_type), _make_space("global"))
    with pytest.raises(VerifyException, match="kernel.exp element_type must be float"):
        op.verify()


# TC-KRN-014
# 功能说明: 验证 kernel.matmul 允许 out/lhs/rhs 使用不同合法 memory space。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_matmul_allows_mixed_spaces
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_matmul_allows_mixed_spaces() -> None:
    lhs_type = _make_memory_type(
        shape=_dim_array([2, 3]),
        stride=_dim_array([3, 1]),
        space="tlm1",
    )
    rhs_type = _make_memory_type(
        shape=_dim_array([3, 4]),
        stride=_dim_array([4, 1]),
        space="tlm2",
    )
    out_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        stride=_dim_array([4, 1]),
        space="tsm",
    )
    op = KernelMatmulOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        _make_space("global"),
    )
    op.verify()


# TC-KRN-014
# 功能说明: 验证 kernel.matmul dtype mismatch 被拒绝。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_matmul_dtype_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_matmul_dtype_mismatch() -> None:
    lhs_type = _make_memory_type(
        shape=_dim_array([2, 3]),
        element_type=Float32Type(),
    )
    rhs_type = _make_memory_type(
        shape=_dim_array([3, 4]),
        element_type=Float16Type(),
    )
    out_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        element_type=Float32Type(),
    )
    op = KernelMatmulOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_type),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.matmul element_type"):
        op.verify()


# TC-KRN-015
# 功能说明: 验证 kernel.matmul 拒绝非二维 operand 与形状不匹配。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_matmul_rank_shape_contract
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_matmul_rank_shape_contract() -> None:
    lhs_type = _make_memory_type(shape=_dim_array([2, 3]))
    rhs_rank3_type = _make_memory_type(
        shape=_dim_array([2, 3, 4]),
        stride=_dim_array([12, 4, 1]),
    )
    out_type = _make_memory_type(shape=_dim_array([2, 4]))
    op = KernelMatmulOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_rank3_type),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.matmul requires rank-2"):
        op.verify()

    rhs_mismatch_type = _make_memory_type(shape=_dim_array([5, 4]))
    op = KernelMatmulOp(
        _make_value(out_type),
        _make_value(lhs_type),
        _make_value(rhs_mismatch_type),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.matmul contracting dimensions"):
        op.verify()

    out_shape_mismatch_type = _make_memory_type(shape=_dim_array([3, 4]))
    op = KernelMatmulOp(
        _make_value(out_shape_mismatch_type),
        _make_value(lhs_type),
        _make_value(_make_memory_type(shape=_dim_array([3, 4]))),
        _make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.matmul result shape"):
        op.verify()


# TC-KRN-025
# 功能说明: 验证 kernel.matmul mixed-space 公开矩阵与非法 space 拒绝边界。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_matmul_space_contract_matrix
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_matmul_space_contract_matrix() -> None:
    for out_space, lhs_space, rhs_space, attr_space in [
        ("global", "global", "local", "global"),
        ("local", "global", "global", "shared"),
        ("tsm", "tlm1", "tlm2", "global"),
    ]:
        lhs_type = _make_memory_type(
            shape=_dim_array([2, 3]),
            element_type=Float32Type(),
            space=lhs_space,
        )
        rhs_type = _make_memory_type(
            shape=_dim_array([3, 4]),
            element_type=Float32Type(),
            space=rhs_space,
        )
        out_type = _make_memory_type(
            shape=_dim_array([2, 4]),
            element_type=Float32Type(),
            space=out_space,
        )
        KernelMatmulOp(
            _make_value(out_type),
            _make_value(lhs_type),
            _make_value(rhs_type),
            _make_space(attr_space),
        ).verify()

    lhs_type = _make_memory_type(
        shape=_dim_array([2, 3]),
        element_type=Float32Type(),
        space="global",
    )
    rhs_type = _make_memory_type(
        shape=_dim_array([3, 4]),
        element_type=Float32Type(),
        space="global",
    )
    out_type = _make_memory_type(
        shape=_dim_array([2, 4]),
        element_type=Float32Type(),
        space="global",
    )
    with pytest.raises(VerifyException, match="nn space must be one of"):
        KernelMatmulOp(
            _make_value(out_type),
            _make_value(lhs_type),
            _make_value(rhs_type),
            _make_space("invalid"),
        ).verify()


# TC-KRN-017
# 功能说明: 验证 kernel.img2col1d/img2col2d 保持结构化输出与显式窗口属性。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_img2col_structured_contract
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_img2col_structured_contract() -> None:
    img2col1d_input_type = _make_memory_type(
        shape=_dim_array([1, 3, 5]),
        stride=_dim_array([15, 5, 1]),
        element_type=Float32Type(),
    )
    img2col1d_output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3]),
        stride=_dim_array([27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    KernelImg2col1dOp(
        _make_value(img2col1d_output_type),
        _make_value(img2col1d_input_type),
        k=_const_i32(3),
        s=_const_i32(1),
        d=_const_i32(1),
        p_left=_const_i32(0),
        p_right=_const_i32(0),
        space=_make_space("global"),
    ).verify()

    img2col2d_input_type = _make_memory_type(
        shape=_dim_array([1, 3, 5, 5]),
        stride=_dim_array([75, 25, 5, 1]),
        element_type=Float32Type(),
    )
    img2col2d_output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3, 3, 3]),
        stride=_dim_array([243, 81, 27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    KernelImg2col2dOp(
        _make_value(img2col2d_output_type),
        _make_value(img2col2d_input_type),
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
# 功能说明: 验证 kernel.img2col1d/img2col2d 拒绝非法输入 rank 或 layout。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_img2col_input_rank_layout_contract
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_img2col_input_rank_layout_contract() -> None:
    img2col1d_output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3]),
        stride=_dim_array([27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    rank2_input = _make_memory_type(
        shape=_dim_array([3, 5]),
        stride=_dim_array([5, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d requires rank-3 input"):
        KernelImg2col1dOp(
            _make_value(img2col1d_output_type),
            _make_value(rank2_input),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    non_contiguous_1d_input = _make_memory_type(
        shape=_dim_array([1, 3, 5]),
        stride=_dim_array([15, 1, 3]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d input layout must be contiguous"):
        KernelImg2col1dOp(
            _make_value(img2col1d_output_type),
            _make_value(non_contiguous_1d_input),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    img2col1d_input_type = _make_memory_type(
        shape=_dim_array([1, 3, 5]),
        stride=_dim_array([15, 5, 1]),
        element_type=Float32Type(),
    )
    rank3_output = _make_memory_type(
        shape=_dim_array([1, 3, 3]),
        stride=_dim_array([9, 3, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d requires rank-4 result"):
        KernelImg2col1dOp(
            _make_value(rank3_output),
            _make_value(img2col1d_input_type),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    img2col2d_output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3, 3, 3]),
        stride=_dim_array([243, 81, 27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    rank3_2d_input = _make_memory_type(
        shape=_dim_array([3, 5, 5]),
        stride=_dim_array([25, 5, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d requires rank-4 input"):
        KernelImg2col2dOp(
            _make_value(img2col2d_output_type),
            _make_value(rank3_2d_input),
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
        shape=_dim_array([1, 3, 5, 5]),
        stride=_dim_array([75, 1, 15, 3]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d input layout must be contiguous"):
        KernelImg2col2dOp(
            _make_value(img2col2d_output_type),
            _make_value(non_contiguous_2d_input),
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
        shape=_dim_array([1, 3, 5, 5]),
        stride=_dim_array([75, 25, 5, 1]),
        element_type=Float32Type(),
    )
    rank5_output = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3, 3]),
        stride=_dim_array([81, 27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d requires rank-6 result"):
        KernelImg2col2dOp(
            _make_value(rank5_output),
            _make_value(img2col2d_input_type),
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
# 功能说明: 验证 kernel.img2col1d/img2col2d 拒绝结构化输出形状与推导关系不一致（含公式结果 < 1）。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_img2col_output_extent_contract
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_img2col_output_extent_contract() -> None:
    img2col1d_input_type = _make_memory_type(
        shape=_dim_array([1, 3, 5]),
        stride=_dim_array([15, 5, 1]),
        element_type=Float32Type(),
    )
    bad_window_axis_1d_output = _make_memory_type(
        shape=_dim_array([1, 3, 2, 3]),
        stride=_dim_array([18, 6, 3, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d result shape/stride must match img2col1d contract"):
        KernelImg2col1dOp(
            _make_value(bad_window_axis_1d_output),
            _make_value(img2col1d_input_type),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    bad_extent_1d_output = _make_memory_type(
        shape=_dim_array([1, 3, 3, 2]),
        stride=_dim_array([18, 6, 2, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d result shape/stride must match img2col1d contract"):
        KernelImg2col1dOp(
            _make_value(bad_extent_1d_output),
            _make_value(img2col1d_input_type),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    bad_stride_1d_output = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3]),
        stride=_dim_array([30, 10, 3, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d result shape/stride must match img2col1d contract"):
        KernelImg2col1dOp(
            _make_value(bad_stride_1d_output),
            _make_value(img2col1d_input_type),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    short_1d_input = _make_memory_type(
        shape=_dim_array([1, 3, 1]),
        stride=_dim_array([3, 1, 1]),
        element_type=Float32Type(),
    )
    short_1d_output = _make_memory_type(
        shape=_dim_array([1, 3, 3, 1]),
        stride=_dim_array([9, 3, 1, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col1d result shape/stride must match img2col1d contract"):
        KernelImg2col1dOp(
            _make_value(short_1d_output),
            _make_value(short_1d_input),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    img2col2d_input_type = _make_memory_type(
        shape=_dim_array([1, 3, 5, 5]),
        stride=_dim_array([75, 25, 5, 1]),
        element_type=Float32Type(),
    )
    bad_window_axis_2d_output = _make_memory_type(
        shape=_dim_array([1, 3, 2, 3, 3, 3]),
        stride=_dim_array([162, 54, 27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(bad_window_axis_2d_output),
            _make_value(img2col2d_input_type),
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
        shape=_dim_array([1, 3, 3, 3, 2, 3]),
        stride=_dim_array([162, 54, 18, 6, 3, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(bad_extent_2d_output),
            _make_value(img2col2d_input_type),
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
        shape=_dim_array([1, 3, 3, 3, 3, 3]),
        stride=_dim_array([200, 80, 27, 9, 3, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(bad_stride_2d_output),
            _make_value(img2col2d_input_type),
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
        shape=_dim_array([1, 3, 1, 1]),
        stride=_dim_array([3, 1, 1, 1]),
        element_type=Float32Type(),
    )
    short_2d_output = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3, 1, 1]),
        stride=_dim_array([27, 9, 3, 1, 1, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(short_2d_output),
            _make_value(short_2d_input),
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


# TC-KRN-026
# 功能说明: 验证 kernel.img2col1d 参数 operand 的公开 symbol/cast/动态与非法值矩阵。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_img2col1d_public_param_operand_matrix
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_img2col1d_public_param_operand_matrix() -> None:
    input_type = _make_memory_type(
        shape=_dim_array([1, 3, 5]),
        stride=_dim_array([15, 5, 1]),
        element_type=Float32Type(),
    )
    output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3]),
        stride=_dim_array([27, 9, 3, 1]),
        element_type=Float32Type(),
    )

    KernelImg2col1dOp(
        _make_value(output_type),
        _make_value(input_type),
        k=_symbol_const_i32(3),
        s=_symbol_const_i32(1),
        d=_symbol_const_i32(1),
        p_left=_symbol_const_i32(0),
        p_right=_symbol_const_i32(0),
        space=_make_space("global"),
    ).verify()
    KernelImg2col1dOp(
        _make_value(output_type),
        _make_value(input_type),
        k=_cast_i32_to_symbol(3),
        s=_cast_i32_to_symbol(1),
        d=_cast_i32_to_symbol(1),
        p_left=_cast_i32_to_symbol(0),
        p_right=_cast_i32_to_symbol(0),
        space=_make_space("global"),
    ).verify()

    dynamic_param = _TestOp(result_types=[SymbolValueType.from_expr("K")]).results[0]
    KernelImg2col1dOp(
        _make_value(output_type),
        _make_value(input_type),
        k=dynamic_param,
        s=_const_i32(1),
        d=_const_i32(1),
        p_left=_const_i32(0),
        p_right=_const_i32(0),
        space=_make_space("global"),
    ).verify()

    dynamic_input_type = _make_memory_type(
        shape=_dim_array([1, 3, "W"]),
        stride=_dim_array(["3 * W", "W", 1]),
        element_type=Float32Type(),
    )
    KernelImg2col1dOp(
        _make_value(output_type),
        _make_value(dynamic_input_type),
        k=_const_i32(3),
        s=_const_i32(1),
        d=_const_i32(1),
        p_left=_const_i32(0),
        p_right=_const_i32(0),
        space=_make_space("global"),
    ).verify()

    bad_param = _TestOp(result_types=[Float32Type()]).results[0]
    with pytest.raises(VerifyException, match="kernel.img2col1d k/s/d must be integer or symbol"):
        KernelImg2col1dOp(
            _make_value(output_type),
            _make_value(input_type),
            k=bad_param,
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    with pytest.raises(VerifyException, match="kernel.img2col1d k/s/d must be positive"):
        KernelImg2col1dOp(
            _make_value(output_type),
            _make_value(input_type),
            k=_const_i32(0),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(0),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()

    with pytest.raises(VerifyException, match="kernel.img2col1d p_left/p_right must be non-negative"):
        KernelImg2col1dOp(
            _make_value(output_type),
            _make_value(input_type),
            k=_const_i32(3),
            s=_const_i32(1),
            d=_const_i32(1),
            p_left=_const_i32(-1),
            p_right=_const_i32(0),
            space=_make_space("global"),
        ).verify()


# TC-KRN-027
# 功能说明: 验证 kernel.img2col2d 的 space/dtype、动态参数和窗口轴公开矩阵。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_img2col2d_public_contract_matrix
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_img2col2d_public_contract_matrix() -> None:
    input_type = _make_memory_type(
        shape=_dim_array([1, 3, 5, 5]),
        stride=_dim_array([75, 25, 5, 1]),
        element_type=Float32Type(),
        space="global",
    )
    output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 3, 3, 3]),
        stride=_dim_array([243, 81, 27, 9, 3, 1]),
        element_type=Float32Type(),
        space="global",
    )

    with pytest.raises(VerifyException, match="kernel.img2col2d attribute space must match input space"):
        KernelImg2col2dOp(
            _make_value(output_type),
            _make_value(_make_memory_type(
                shape=_dim_array([1, 3, 5, 5]),
                stride=_dim_array([75, 25, 5, 1]),
                element_type=Float32Type(),
                space="local",
            )),
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

    with pytest.raises(VerifyException, match="kernel.img2col2d attribute space must match result space"):
        KernelImg2col2dOp(
            _make_value(_make_memory_type(
                shape=_dim_array([1, 3, 3, 3, 3, 3]),
                stride=_dim_array([243, 81, 27, 9, 3, 1]),
                element_type=Float32Type(),
                space="local",
            )),
            _make_value(input_type),
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

    with pytest.raises(VerifyException, match="kernel.img2col2d result element_type must match input"):
        KernelImg2col2dOp(
            _make_value(_make_memory_type(
                shape=_dim_array([1, 3, 3, 3, 3, 3]),
                stride=_dim_array([243, 81, 27, 9, 3, 1]),
                element_type=Float16Type(),
            )),
            _make_value(input_type),
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

    bad_kw_output_type = _make_memory_type(
        shape=_dim_array([1, 3, 3, 2, 3, 3]),
        stride=_dim_array([162, 54, 18, 9, 3, 1]),
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="kernel.img2col2d result shape/stride must match img2col2d contract"):
        KernelImg2col2dOp(
            _make_value(bad_kw_output_type),
            _make_value(input_type),
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

    dynamic_param = _TestOp(result_types=[SymbolValueType.from_expr("KH")]).results[0]
    KernelImg2col2dOp(
        _make_value(output_type),
        _make_value(input_type),
        kh=dynamic_param,
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

    dynamic_input_type = _make_memory_type(
        shape=_dim_array([1, 3, "H", "W"]),
        stride=_dim_array(["3 * H * W", "H * W", "W", 1]),
        element_type=Float32Type(),
    )
    KernelImg2col2dOp(
        _make_value(output_type),
        _make_value(dynamic_input_type),
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


# TC-KRN-023
# 功能说明: 验证 kernel.reduce_min 正常路径可通过。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_reduce_min_success
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_reduce_min_success() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(
        shape=_dim_array([2, 1]),
        stride=_dim_array([1, 1]),
        element_type=Float32Type(),
    )
    op = KernelReduceMinOp(
        _make_value(out_type),
        _make_value(input_type),
        axis=1,
        keepdim=True,
        space=_make_space("global"),
    )
    op.verify()


# TC-KRN-020
# 功能说明: 验证 kernel.reduce_min axis 越界会报错。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_reduce_min_axis_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_reduce_min_axis_error() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(
        shape=_dim_array([2, 1]),
        stride=_dim_array([1, 1]),
        element_type=Float32Type(),
    )
    op = KernelReduceMinOp(
        _make_value(out_type),
        _make_value(input_type),
        axis=2,
        keepdim=True,
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="axis must be within"):
        op.verify()


# TC-KRN-022
# 功能说明: 验证 kernel.reduce_min 拒绝 out.shape 不一致。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_reduce_min_out_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_reduce_min_out_shape_mismatch() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(
        shape=_dim_array([2, 2]),
        stride=_dim_array([2, 1]),
        element_type=Float32Type(),
    )
    op = KernelReduceMinOp(
        _make_value(out_type),
        _make_value(input_type),
        axis=1,
        keepdim=True,
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="kernel.reduce_min out shape must match reduce contract"):
        op.verify()


# TC-KRN-021
# 功能说明: 验证 kernel.reduce_min 拒绝 keepdim 非 i1。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_reduce_min_keepdim_error
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_reduce_min_keepdim_error() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    out_type = _make_memory_type(
        shape=_dim_array([2, 1]),
        stride=_dim_array([1, 1]),
        element_type=Float32Type(),
    )
    op = KernelReduceMinOp(
        _make_value(out_type),
        _make_value(input_type),
        axis=1,
        keepdim=IntegerAttr(2, IntegerType(8)),
        space=_make_space("global"),
    )
    with pytest.raises(VerifyException, match="keepdim must be i1"):
        op.verify()


# TC-KRN-028
# 功能说明: 验证 kernel.reduce 通用公开入口的 kind/axis/keepdim 与 shape 矩阵。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_reduce_public_kind_axis_keepdim_matrix
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_reduce_public_kind_axis_keepdim_matrix() -> None:
    input_type = _make_memory_type(
        shape=_dim_array([2, 3]),
        stride=_dim_array([3, 1]),
        element_type=Float32Type(),
    )
    keepdim_out_type = _make_memory_type(
        shape=_dim_array([2, 1]),
        stride=_dim_array([1, 1]),
        element_type=Float32Type(),
    )
    squeeze_out_type = _make_memory_type(
        shape=_dim_array([2]),
        stride=_dim_array([1]),
        element_type=Float32Type(),
    )

    KernelReduceOp(
        _make_value(keepdim_out_type),
        _make_value(input_type),
        kind=StringAttr("sum"),
        axis=IntegerAttr(1, IntegerType(64)),
        keepdim=IntAttr(1),
        space=_make_space("global"),
    ).verify()
    KernelReduceOp(
        _make_value(squeeze_out_type),
        _make_value(input_type),
        kind="max",
        axis=IntAttr(1),
        keepdim=0,
        space=_make_space("global"),
    ).verify()

    rank1_input_type = _make_memory_type(
        shape=_dim_array([3]),
        stride=_dim_array([1]),
        element_type=Float32Type(),
    )
    scalar_out_type = _make_memory_type(
        shape=_dim_array([1]),
        stride=_dim_array([1]),
        element_type=Float32Type(),
    )
    KernelReduceOp(
        _make_value(scalar_out_type),
        _make_value(rank1_input_type),
        kind="min",
        axis=0,
        keepdim=False,
        space=_make_space("global"),
    ).verify()

    with pytest.raises(VerifyException, match="kernel.reduce kind must be one of"):
        KernelReduceOp(
            _make_value(keepdim_out_type),
            _make_value(input_type),
            kind="prod",
            axis=1,
            keepdim=True,
            space=_make_space("global"),
        )

    with pytest.raises(VerifyException, match="kernel.reduce element_type must match"):
        KernelReduceOp(
            _make_value(_make_memory_type(
                shape=_dim_array([2, 1]),
                stride=_dim_array([1, 1]),
                element_type=Float16Type(),
            )),
            _make_value(input_type),
            kind="sum",
            axis=1,
            keepdim=True,
            space=_make_space("global"),
        ).verify()

    with pytest.raises(VerifyException, match="kernel.reduce out space must match input"):
        KernelReduceOp(
            _make_value(_make_memory_type(
                shape=_dim_array([2, 1]),
                stride=_dim_array([1, 1]),
                element_type=Float32Type(),
                space="local",
            )),
            _make_value(input_type),
            kind="sum",
            axis=1,
            keepdim=True,
            space=_make_space("global"),
        ).verify()

    with pytest.raises(VerifyException, match="kernel.reduce attribute space must match input"):
        KernelReduceOp(
            _make_value(keepdim_out_type),
            _make_value(input_type),
            kind="sum",
            axis=1,
            keepdim=True,
            space=_make_space("local"),
        ).verify()

    with pytest.raises(VerifyException, match="kernel.reduce out shape must match reduce contract"):
        KernelReduceOp(
            _make_value(_make_memory_type(
                shape=_dim_array([3]),
                stride=_dim_array([1]),
                element_type=Float32Type(),
            )),
            _make_value(input_type),
            kind="sum",
            axis=1,
            keepdim=False,
            space=_make_space("global"),
        ).verify()


# TC-KRN-029
# 功能说明: 验证 kernel.reduce_min 的 dtype 和 space 公开拒绝矩阵。
# 使用示例: pytest -q test/dialect/test_kernel.py -k test_kernel_reduce_min_dtype_space_matrix
# 对应功能实现文件路径: kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dialect/kernel.md
# 对应测试文件路径: test/dialect/test_kernel.py
def test_kernel_reduce_min_dtype_space_matrix() -> None:
    input_type = _make_memory_type(element_type=Float32Type())
    keepdim_out_type = _make_memory_type(
        shape=_dim_array([2, 1]),
        stride=_dim_array([1, 1]),
        element_type=Float32Type(),
    )

    with pytest.raises(VerifyException, match="kernel.reduce_min element_type must match"):
        KernelReduceMinOp(
            _make_value(_make_memory_type(
                shape=_dim_array([2, 1]),
                stride=_dim_array([1, 1]),
                element_type=Float16Type(),
            )),
            _make_value(input_type),
            axis=1,
            keepdim=True,
            space=_make_space("global"),
        ).verify()

    with pytest.raises(VerifyException, match="kernel.reduce_min out space must match input"):
        KernelReduceMinOp(
            _make_value(_make_memory_type(
                shape=_dim_array([2, 1]),
                stride=_dim_array([1, 1]),
                element_type=Float32Type(),
                space="local",
            )),
            _make_value(input_type),
            axis=1,
            keepdim=True,
            space=_make_space("global"),
        ).verify()

    with pytest.raises(VerifyException, match="kernel.reduce_min attribute space must match input"):
        KernelReduceMinOp(
            _make_value(keepdim_out_type),
            _make_value(input_type),
            axis=1,
            keepdim=True,
            space=_make_space("local"),
        ).verify()
