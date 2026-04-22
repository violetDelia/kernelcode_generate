"""common contracts tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen.common.contracts 中的公共 verifier、shape 与 dtype 辅助逻辑。

使用示例:
- pytest -q test/common/test_contracts.py

关联文件:
- 功能实现: kernel_gen/common/contracts.py
- Spec 文档: spec/common/contracts.md
- 测试文件: test/common/test_contracts.py
"""

from __future__ import annotations

import sympy as sp
import pytest
from xdsl.dialects.builtin import (
    ArrayAttr,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    i32,
)
from xdsl.utils.exceptions import VerifyException

from kernel_gen.common.contracts import (
    _build_contiguous_stride,
    _collect_int_dims,
    _default_stride,
    _dims_equal,
    _public_dim_values,
    _shape_numel,
    _verify_i64_attr,
    _verify_i64_attr_group,
    _verify_i64_attr_range,
    _verify_i64_attr_value,
    _verify_memory_type,
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
    assert _verify_memory_type(memory_type, "lhs", scene="common.contracts verifier") is memory_type

    with pytest.raises(VerifyException, match="lhs must be nn.memory"):
        _verify_memory_type(StringAttr("bad"), "lhs", scene="common.contracts verifier")


def test_verify_i64_attr_family() -> None:
    axis = IntegerAttr(3, IntegerType(64))
    non_negative = IntegerAttr(0, IntegerType(64))
    positive = IntegerAttr(5, IntegerType(64))
    wider = IntegerAttr(1, IntegerType(32))

    assert _verify_i64_attr(axis, "axis", scene="common.contracts verifier") == 3
    assert _verify_i64_attr_range(axis, "axis", min_value=-2, max_value=5, scene="common.contracts verifier") == 3
    assert _verify_i64_attr_value(non_negative, "keepdim", allow_zero=True, scene="common.contracts verifier") == 0
    assert _verify_i64_attr_value(positive, "kw", allow_zero=False, scene="common.contracts verifier") == 5
    assert _verify_i64_attr_group(
        [positive, IntegerAttr(2, IntegerType(64))],
        allow_zero=False,
        error_phrase="kw-sw must be positive",
        scene="common.contracts verifier",
    ) == [5, 2]

    with pytest.raises(VerifyException, match="axis must be i64"):
        _verify_i64_attr(IntegerAttr(1, IntegerType(32)), "axis", scene="common.contracts verifier")
    with pytest.raises(VerifyException, match="axis must be within \\[-2, 1\\]"):
        _verify_i64_attr_range(axis, "axis", min_value=-2, max_value=1, scene="common.contracts verifier")
    with pytest.raises(VerifyException, match="keepdim must be non-negative"):
        _verify_i64_attr_value(IntegerAttr(-1, IntegerType(64)), "keepdim", allow_zero=True, scene="common.contracts verifier")
    with pytest.raises(VerifyException, match="kw-sw must be positive"):
        _verify_i64_attr_group(
            [positive, IntegerAttr(0, IntegerType(64))],
            allow_zero=False,
            error_phrase="kw-sw must be positive",
            scene="common.contracts verifier",
        )
    with pytest.raises(VerifyException, match="kw-sw must be positive"):
        _verify_i64_attr_group(
            [wider, positive],
            allow_zero=False,
            error_phrase="kw-sw must be positive",
            scene="common.contracts verifier",
        )


def test_collect_dims_and_stride_helpers() -> None:
    assert _collect_int_dims([IntAttr(1), IntAttr(2), IntAttr(3)]) == [1, 2, 3]
    assert _collect_int_dims([IntAttr(1), StringAttr("N")]) is None
    assert _build_contiguous_stride([2, 3, 4]) == [12, 4, 1]


def test_dims_equal() -> None:
    assert _dims_equal(IntAttr(2), IntAttr(2))
    assert not _dims_equal(IntAttr(2), IntAttr(3))
    assert _dims_equal(StringAttr("N"), StringAttr("N"))
    assert not _dims_equal(StringAttr("N"), StringAttr("M"))
    assert not _dims_equal(IntAttr(2), StringAttr("2"))


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

    assert _public_dim_values(symbolic) == ["A*B/B", 4]
    assert _default_stride(default_shape).get_values() == ["K*N", "N", 1]
    assert _shape_numel(concrete_shape).get_value() == 24
