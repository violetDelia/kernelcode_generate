"""core contracts tests.


功能说明:
- 覆盖 kernel_gen.core.contracts 中的公共 verifier、shape 与 dtype 辅助逻辑。

使用示例:
- pytest -q test/core/test_contracts.py

关联文件:
- 功能实现: kernel_gen/core/contracts.py
- Spec 文档: spec/core/contracts.md
- 测试文件: test/core/test_contracts.py
"""

from __future__ import annotations

import sympy as sp
import pytest
from xdsl.dialects.builtin import (
    ArrayAttr,
    Float32Type,
    FloatAttr,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    i32,
)
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.contracts import (
    build_contiguous_stride,
    collect_int_dims,
    default_stride,
    dims_equal,
    public_dim_values,
    shape_numel,
    verify_i64_attr,
    verify_i64_attr_group,
    verify_i64_attr_range,
    verify_i64_attr_value,
    verify_memory_type,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape


def _make_memory_type() -> NnMemoryType:
    """构造合法 nn.memory type 用于公共 helper 测试。"""

    return NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr(StringAttr("global")),
    )


def test_verify_memory_type_success_and_failure() -> None:
    memory_type = _make_memory_type()
    assert verify_memory_type(memory_type, "lhs", scene="common.contracts verifier") is memory_type

    with pytest.raises(VerifyException, match="lhs must be nn.memory"):
        verify_memory_type(StringAttr("bad"), "lhs", scene="common.contracts verifier")


def test_verify_i64_attr_family() -> None:
    axis = IntegerAttr(3, IntegerType(64))
    non_negative = IntegerAttr(0, IntegerType(64))
    positive = IntegerAttr(5, IntegerType(64))
    wider = IntegerAttr(1, IntegerType(32))

    assert verify_i64_attr(axis, "axis", scene="common.contracts verifier") == 3
    assert verify_i64_attr_range(axis, "axis", min_value=-2, max_value=5, scene="common.contracts verifier") == 3
    assert verify_i64_attr_value(non_negative, "keepdim", allow_zero=True, scene="common.contracts verifier") == 0
    assert verify_i64_attr_value(positive, "kw", allow_zero=False, scene="common.contracts verifier") == 5
    assert verify_i64_attr_group(
        [positive, IntegerAttr(2, IntegerType(64))],
        allow_zero=False,
        error_phrase="kw-sw must be positive",
        scene="common.contracts verifier",
    ) == [5, 2]

    with pytest.raises(VerifyException, match="axis must be i64"):
        verify_i64_attr(FloatAttr(1.5, Float32Type()), "axis", scene="common.contracts verifier")
    with pytest.raises(VerifyException, match="axis must be i64"):
        verify_i64_attr(IntegerAttr(1, IntegerType(32)), "axis", scene="common.contracts verifier")
    with pytest.raises(VerifyException, match="axis must be within \\[-2, 1\\]"):
        verify_i64_attr_range(axis, "axis", min_value=-2, max_value=1, scene="common.contracts verifier")
    with pytest.raises(VerifyException, match="keepdim must be positive"):
        verify_i64_attr_value(IntegerAttr(0, IntegerType(64)), "keepdim", allow_zero=False, scene="common.contracts verifier")
    with pytest.raises(VerifyException, match="keepdim must be non-negative"):
        verify_i64_attr_value(IntegerAttr(-1, IntegerType(64)), "keepdim", allow_zero=True, scene="common.contracts verifier")
    with pytest.raises(VerifyException, match="kw-sw must be positive"):
        verify_i64_attr_group(
            [FloatAttr(1.5, Float32Type())],  # type: ignore[list-item]
            allow_zero=False,
            error_phrase="kw-sw must be positive",
            scene="common.contracts verifier",
        )
    with pytest.raises(VerifyException, match="kw-sw must be positive"):
        verify_i64_attr_group(
            [IntegerAttr(-1, IntegerType(64))],
            allow_zero=True,
            error_phrase="kw-sw must be positive",
            scene="common.contracts verifier",
        )
    with pytest.raises(VerifyException, match="kw-sw must be positive"):
        verify_i64_attr_group(
            [positive, IntegerAttr(0, IntegerType(64))],
            allow_zero=False,
            error_phrase="kw-sw must be positive",
            scene="common.contracts verifier",
        )
    with pytest.raises(VerifyException, match="kw-sw must be positive"):
        verify_i64_attr_group(
            [wider, positive],
            allow_zero=False,
            error_phrase="kw-sw must be positive",
            scene="common.contracts verifier",
        )


def test_collect_dims_and_stride_helpers() -> None:
    assert collect_int_dims([IntAttr(1), IntAttr(2), IntAttr(3)]) == [1, 2, 3]
    assert collect_int_dims([IntAttr(1), StringAttr("N")]) is None
    assert build_contiguous_stride([2, 3, 4]) == [12, 4, 1]


def test_dims_equal() -> None:
    assert dims_equal(IntAttr(2), IntAttr(2))
    assert not dims_equal(IntAttr(2), IntAttr(3))
    assert dims_equal(StringAttr("N"), StringAttr("N"))
    assert not dims_equal(StringAttr("N"), StringAttr("M"))
    assert not dims_equal(IntAttr(2), StringAttr("2"))


def test_public_dim_values_default_stride_shape_numel() -> None:
    symbolic = SymbolShape(
        [
            SymbolDim(
                sp.Mul(
                    sp.Mul(
                        sp.symbols("A", integer=True, real=True),
                        sp.symbols("B", integer=True, real=True),
                        evaluate=False,
                    ),
                    sp.Pow(sp.symbols("B", integer=True, real=True), -1, evaluate=False),
                    evaluate=False,
                )
            ),
            4,
        ]
    )
    default_shape = SymbolShape([SymbolDim("M"), SymbolDim("K"), SymbolDim("N")])
    concrete_shape = SymbolShape([2, 3, 4])

    assert public_dim_values(symbolic) == ["A*B/B", 4]
    assert default_stride(default_shape).get_values() == ["K*N", "N", 1]
    assert shape_numel(concrete_shape).get_value() == 24
