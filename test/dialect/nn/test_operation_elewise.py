"""test operation elewise.

功能说明:
- 验证 nn dialect package 拆分后对应 family 的公开行为不变。

使用示例:
- pytest -q test/dialect/nn/test_operation_elewise.py

关联文件:
- 功能实现: kernel_gen/dialect/nn/
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/nn/test_operation_elewise.py
"""


from __future__ import annotations

from collections.abc import Sequence
from io import StringIO
import random
import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith
from xdsl.context import Context
from xdsl.dialects.builtin import (
    ArrayAttr,
    Builtin,
    Float16Type,
    Float32Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    i1,
    i32,
)
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.ir import Attribute, Operation
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import ParseError, VerifyException

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect import (
    Nn,
    NnAddOp,
    NnBroadcastOp,
    NnEqOp,
    NnGeOp,
    NnGtOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
    NnLeOp,
    NnLtOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnSubOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.nn import (
    copy_memory_type,
    copy_memory_type_with_template_name,
    NnCastOp,
    NnDivOp,
    NnExpOp,
    NnFloorDivOp,
    NnHardSigmoidOp,
    NnLeakyReluOp,
    NnReluOp,
    NnSigmoidOp,
    NnTanhOp,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
    NnSelectOp,
    NnSoftmaxOp,
    NnTransposeOp,
)
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolValueType
from kernel_gen.dialect.symbol import Symbol


def _build_context() -> Context:
    """构造加载 builtin/test/nn 的解析上下文。


    功能说明:
    - 为 parser/printer/verify 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Symbol)
    return ctx

def _print_ir(value: Attribute | Operation) -> str:
    """打印 attribute 或 operation/module 为文本。"""

    stream = StringIO()
    printer = Printer(stream=stream)
    if isinstance(value, Attribute):
        printer.print_attribute(value)
    elif isinstance(value, Operation):
        printer.print_op(value)
    else:
        printer.print(value)
    return stream.getvalue()

def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造 space attribute。"""

    return NnMemorySpaceAttr(StringAttr(name))

def _expr_attr(value: int | str) -> SymbolExprAttr:
    """构造公开 SymbolExprAttr。

    功能说明:
    - 为 nn dialect 测试统一生成结构化 memory shape/stride 表达。

    使用示例:
    - _expr_attr("N")
    """

    return SymbolExprAttr.from_expr(str(value))

def _symbol_dims(values: Sequence[int | str | SymbolExprAttr]) -> list[Attribute]:
    """构造 memory shape/stride 结构化维度。

    功能说明:
    - 使用公开 SymbolExprAttr 表达 memory layout，避免旧 IntAttr/StringAttr layout 入口。

    使用示例:
    - _symbol_dims([2, "N"])
    """

    return [value if isinstance(value, SymbolExprAttr) else _expr_attr(value) for value in values]

def _make_memory_type(space: str = "global", element_type: IntegerType = i32) -> NnMemoryType:
    """构造合法的 nn memory type。"""

    return NnMemoryType(
        ArrayAttr([_expr_attr("M"), _expr_attr("?"), _expr_attr(4)]),
        ArrayAttr([_expr_attr(4), _expr_attr(1), _expr_attr("?")]),
        element_type,
        _make_space(space),
    )

def _make_simple_memory_type(
    shape: list[int | str | SymbolExprAttr],
    stride: list[int | str | SymbolExprAttr],
    space: str = "global",
    element_type: IntegerType = i32,
) -> NnMemoryType:
    """构造指定 shape/stride 的 nn memory type。


    功能说明:
    - 便于构造 broadcast 与隐式广播拒绝测试所需类型。

    使用示例:
    - _make_simple_memory_type([1, "N"], [1, 1])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """
    return NnMemoryType(
        ArrayAttr(_symbol_dims(shape)),
        ArrayAttr(_symbol_dims(stride)),
        element_type,
        _make_space(space),
    )

def _make_matrix_type(
    shape: Sequence[int | str | SymbolExprAttr],
    stride: Sequence[int | str | SymbolExprAttr],
    space: str = "global",
    element_type: IntegerType = i32,
) -> NnMemoryType:
    """构造 rank=2 的 nn memory type。


    功能说明:
    - 便于构造 matmul 用的 rank=2 memory type。

    使用示例:
    - _make_matrix_type(["M", "N"], [8, 1])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    return NnMemoryType(
        ArrayAttr(_symbol_dims(shape)),
        ArrayAttr(_symbol_dims(stride)),
        element_type,
        _make_space(space),
    )


def test_select_op_verify_success() -> None:
    space = _make_space("global")
    cond_type = _make_matrix_type([4, 8], [8, 1], element_type=i1)
    data_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    cond = _TestOp(result_types=[cond_type]).results[0]
    lhs = _TestOp(result_types=[data_type]).results[0]
    rhs = _TestOp(result_types=[data_type]).results[0]
    NnSelectOp(cond, lhs, rhs, result_type, space).verify_()

def test_select_op_rejects_cond_element_type() -> None:
    space = _make_space("global")
    cond_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    data_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    cond = _TestOp(result_types=[cond_type]).results[0]
    lhs = _TestOp(result_types=[data_type]).results[0]
    rhs = _TestOp(result_types=[data_type]).results[0]
    op = NnSelectOp(cond, lhs, rhs, result_type, space)
    with pytest.raises(VerifyException, match="nn.select cond element_type must be i1"):
        op.verify_()

def test_cast_op_verify_success() -> None:
    space = _make_space("global")
    input_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 8], [8, 1], element_type=IntegerType(16))
    input_value = _TestOp(result_types=[input_type]).results[0]
    NnCastOp(input_value, result_type, space).verify_()

def test_cast_op_rejects_shape_mismatch() -> None:
    space = _make_space("global")
    input_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 7], [7, 1], element_type=IntegerType(16))
    input_value = _TestOp(result_types=[input_type]).results[0]
    op = NnCastOp(input_value, result_type, space)
    with pytest.raises(VerifyException, match="nn.cast shape must match input"):
        op.verify_()

def test_broadcast_op_verify_success() -> None:
    input_type = _make_simple_memory_type([1, "N"], [1, 1])
    result_type = _make_simple_memory_type(["M", "N"], [1, 1])
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space("global"))
    op.verify()

    int_input = _make_simple_memory_type([2], [1], space="global")
    int_result = _make_simple_memory_type([2], [1], space="global")
    int_value = _TestOp(result_types=[int_input]).results[0]
    int_op = NnBroadcastOp(int_value, int_result, _make_space("global"))
    int_op.verify()

def test_broadcast_op_space_mismatch() -> None:
    input_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("shared", i32)
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="result-space-must-match-input-and-attr"):
        op.verify()

def test_broadcast_op_element_type_mismatch() -> None:
    input_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("global", IntegerType(1))
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="result-element-type-must-match-input"):
        op.verify()

@pytest.mark.parametrize(
    ("input_type", "result_type", "space", "message"),
    [
        (
            _make_simple_memory_type([1], [1], space="global"),
            _make_simple_memory_type([1], [1], space="global"),
            "shared",
            "result-space-must-match-input-and-attr",
        ),
        (
            _make_simple_memory_type([1, "N"], [1, 1], space="global"),
            _make_simple_memory_type(["N"], [1], space="global"),
            "global",
            "result-rank-must-be-greater-or-equal-to-input",
        ),
        (
            _make_simple_memory_type([2, "N"], [1, 1], space="global"),
            _make_simple_memory_type(["M", "N"], [1, 1], space="global"),
            "global",
            "result-shape-must-match-broadcast-contract",
        ),
    ],
)
def test_broadcast_op_rejects_invalid_inputs(
    input_type: NnMemoryType,
    result_type: NnMemoryType,
    space: str,
    message: str,
) -> None:
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space(space))
    with pytest.raises(VerifyException, match=message):
        op.verify()

def test_broadcast_module_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<1>, #symbol.expr<1>], i32, #nn.space<global>>
  %1 = "nn.broadcast"(%0) {space = #nn.space<global>} : (!nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<1>, #symbol.expr<1>], i32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<M>, #symbol.expr<N>], [#symbol.expr<1>, #symbol.expr<1>], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()

def test_transpose_op_verify_success() -> None:
    input_type = _make_simple_memory_type(
        ["M", "N", 4],
        [8, 4, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        ["N", "M", 4],
        ["M*4", 4, 1],
        space="global",
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnTransposeOp(inp, result_type, perm=[1, 0, 2], space=_make_space("global"))
    op.verify()

@pytest.mark.parametrize(
    ("perm", "message"),
    [
        ([0], "perm must match input rank"),
        ([0, 0], "permutation"),
        ([0, 2], "permutation"),
    ],
)
def test_transpose_op_rejects_invalid_perm(perm: Sequence[int], message: str) -> None:
    input_type = _make_simple_memory_type(["M", "N"], [2, 1])
    result_type = _make_simple_memory_type(["N", "M"], [1, 2])
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnTransposeOp(inp, result_type, perm=perm, space=_make_space("global"))
    with pytest.raises(VerifyException, match=message):
        op.verify()

@pytest.mark.parametrize(
    ("result_type", "space", "message"),
    [
        (
            _make_simple_memory_type(["M", "N"], [1, 2]),
            "global",
            "result shape",
        ),
        (
            _make_simple_memory_type(["N", "M"], [2, 1]),
            "global",
            "result stride",
        ),
        (
            _make_simple_memory_type(
                ["N", "M"],
                [1, 2],
                element_type=IntegerType(16),
            ),
            "global",
            "element_type",
        ),
        (
            _make_simple_memory_type(["N", "M"], [1, 2], space="shared"),
            "global",
            "input/result must use the same space",
        ),
        (
            _make_simple_memory_type(["N", "M"], [1, 2]),
            "shared",
            "attribute space",
        ),
    ],
)
def test_transpose_op_result_mismatch(
    result_type: NnMemoryType,
    space: str,
    message: str,
) -> None:
    input_type = _make_simple_memory_type(["M", "N"], [2, 1])
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnTransposeOp(inp, result_type, perm=[1, 0], space=_make_space(space))
    with pytest.raises(VerifyException, match=message):
        op.verify()

def test_transpose_module_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<4>], [#symbol.expr<8>, #symbol.expr<4>, #symbol.expr<1>], i32, #nn.space<global>>
  %1 = "nn.transpose"(%0) {perm = [1 : i64, 0 : i64, 2 : i64], space = #nn.space<global>} : (!nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<4>], [#symbol.expr<8>, #symbol.expr<4>, #symbol.expr<1>], i32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<N>, #symbol.expr<M>, #symbol.expr<4>], [#symbol.expr<4*M>, #symbol.expr<4>, #symbol.expr<1>], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()

def test_transpose_dynamic_stride_public_contract() -> None:
    input_type = _make_simple_memory_type(
        ["?", 2],
        [2, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        [2, "?"],
        ["?", 1],
        space="global",
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    NnTransposeOp(inp, result_type, perm=[1, 0], space=_make_space("global")).verify()
