"""test operation reduce.

功能说明:
- 验证 nn dialect package 拆分后对应 family 的公开行为不变。

使用示例:
- pytest -q test/dialect/nn/test_operation_reduce.py

关联文件:
- 功能实现: kernel_gen/dialect/nn/
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/nn/test_operation_reduce.py
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
from kernel_gen.core.error import KernelCodeError
from xdsl.utils.exceptions import ParseError

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


def test_reduce_sum_op_shape_contract() -> None:
    input_type = _make_simple_memory_type(
        [2, 3, 4],
        [12, 4, 1],
        space="global",
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    cases = [
        (
            [1],
            True,
            _make_simple_memory_type(
                [2, 1, 4],
                [4, 4, 1],
                space="global",
            ),
        ),
        (
            [1],
            False,
            _make_simple_memory_type(
                [2, 4],
                [4, 1],
                space="global",
            ),
        ),
    ]
    for axes, keepdim, result_type in cases:
        op = NnReduceSumOp(inp, result_type, axes=axes, keepdim=keepdim, space=_make_space("global"))
        op.verify()

def test_reduce_sum_op_rejects_invalid_axes() -> None:
    input_type = _make_simple_memory_type(
        [2, 3, 4],
        [12, 4, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        [2, 3, 4],
        [12, 4, 1],
        space="global",
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    cases = [
        ArrayAttr([]),
        ArrayAttr([IntegerAttr(0, IntegerType(64)), IntegerAttr(0, IntegerType(64))]),
        ArrayAttr([IntegerAttr(3, IntegerType(64))]),
        ArrayAttr([IntegerAttr(1, IntegerType(32))]),
        ArrayAttr([IntAttr(1)]),
    ]
    for axes_attr in cases:
        op = NnReduceSumOp(inp, result_type, axes=[0], keepdim=True, space=_make_space("global"))
        op.attributes["axes"] = axes_attr
        with pytest.raises(KernelCodeError, match="axes-must-be-non-empty-unique-and-in-range"):
            op.verify()

def test_reduce_min_op_contract_and_empty_extent_rejection() -> None:
    input_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        [1, 3],
        [3, 1],
        space="global",
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnReduceMinOp(inp, result_type, axes=[0], keepdim=True, space=_make_space("global"))
    op.verify()

    empty_input_type = _make_simple_memory_type(
        [0, 3],
        [3, 1],
        space="global",
    )
    empty_result_type = _make_simple_memory_type(
        [1, 3],
        [3, 1],
        space="global",
    )
    empty_inp = _TestOp(result_types=[empty_input_type]).results[0]
    empty_op = NnReduceMinOp(empty_inp, empty_result_type, axes=[0], keepdim=True, space=_make_space("global"))
    with pytest.raises(KernelCodeError, match="empty-reduction-extent-must-be-rejected-when-static"):
        empty_op.verify()

def test_reduce_max_op_contract_and_empty_extent_rejection() -> None:
    input_type = _make_simple_memory_type(
        [2, 3, 4],
        [12, 4, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        [2, 4],
        [4, 1],
        space="global",
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnReduceMaxOp(inp, result_type, axes=[1], keepdim=False, space=_make_space("global"))
    op.verify()

    empty_input_type = _make_simple_memory_type(
        [2, 0, 4],
        [0, 0, 1],
        space="global",
    )
    empty_result_type = _make_simple_memory_type(
        [2, 4],
        [4, 1],
        space="global",
    )
    empty_inp = _TestOp(result_types=[empty_input_type]).results[0]
    empty_op = NnReduceMaxOp(empty_inp, empty_result_type, axes=[1], keepdim=False, space=_make_space("global"))
    with pytest.raises(KernelCodeError, match="empty-reduction-extent-must-be-rejected-when-static"):
        empty_op.verify()

def test_reduce_ops_reject_type_or_space_mismatch() -> None:
    input_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
        element_type=i32,
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    cases = [
        (
            _make_simple_memory_type(
                [2],
                [1],
                space="global",
                element_type=Float32Type(),
            ),
            "global",
            "result-element-type-must-match-input",
        ),
        (
            _make_simple_memory_type(
                [2],
                [1],
                space="shared",
                element_type=i32,
            ),
            "global",
            "result-space-must-match-input-and-attr",
        ),
        (
            _make_simple_memory_type(
                [2],
                [1],
                space="global",
                element_type=i32,
            ),
            "shared",
            "result-space-must-match-input-and-attr",
        ),
    ]
    for result_type, space, message in cases:
        op = NnReduceSumOp(inp, result_type, axes=[1], keepdim=False, space=_make_space(space))
        with pytest.raises(KernelCodeError, match=message):
            op.verify()

def test_exp_reduce_module_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>
  %1 = "nn.exp"(%0) {space = #nn.space<global>} : (!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>
  %2 = "nn.reduce_sum"(%1) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : (!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<1>], [#symbol.expr<1>, #symbol.expr<1>], f32, #nn.space<global>>
  %3 = "nn.reduce_max"(%1) {axes = [0 : i64], keepdim = false, space = #nn.space<global>} : (!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<4>], [#symbol.expr<1>], f32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()

def test_reduce_ops_reject_non_i1_keepdim_attr() -> None:
    input_type = _make_simple_memory_type(
        [2, 3, 4],
        [12, 4, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        [2, 4],
        [4, 1],
        space="global",
    )
    op_types = (NnReduceSumOp, NnReduceMinOp, NnReduceMaxOp)
    for op_type in op_types:
        inp = _TestOp(result_types=[input_type]).results[0]
        op = op_type(inp, result_type, axes=[1], keepdim=False, space=_make_space("global"))
        op.attributes["keepdim"] = IntegerAttr(1, IntegerType(32))
        with pytest.raises(KernelCodeError, match="keepdim-must-be-i1-bool-attr"):
            op.verify()

def test_reduce_ops_reject_non_contiguous_result_stride() -> None:
    input_type = _make_simple_memory_type(
        [2, 3, 4],
        [12, 4, 1],
        space="global",
    )
    bad_result_type = _make_simple_memory_type(
        [2, 4],
        [5, 1],
        space="global",
    )
    op_types = (NnReduceSumOp, NnReduceMinOp, NnReduceMaxOp)
    for op_type in op_types:
        inp = _TestOp(result_types=[input_type]).results[0]
        op = op_type(inp, bad_result_type, axes=[1], keepdim=False, space=_make_space("global"))
        with pytest.raises(KernelCodeError, match="result-stride-must-be-contiguous-for-result-shape"):
            op.verify()

def test_unary_float_family_and_reduce_helper_edges() -> None:
    input_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        element_type=Float32Type(),
    )
    result_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        element_type=Float32Type(),
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    alpha = arith.ConstantOp(IntegerAttr(1, i32)).result
    beta = arith.ConstantOp(IntegerAttr(2, i32)).result

    NnReluOp(inp, result_type, _make_space("global")).verify()
    NnSigmoidOp(inp, result_type, _make_space("global")).verify()
    NnTanhOp(inp, result_type, _make_space("global")).verify()
    NnExpOp(inp, result_type, _make_space("global")).verify()
    NnLeakyReluOp(inp, alpha, result_type, _make_space("global")).verify()
    NnHardSigmoidOp(inp, alpha, beta, result_type, _make_space("global")).verify()

    symbol_value = _TestOp(result_types=[SymbolValueType.from_expr("K")]).results[0]
    with pytest.raises(KernelCodeError, match="alpha must be int or float scalar"):
        NnLeakyReluOp(inp, symbol_value, result_type, _make_space("global")).verify()
    with pytest.raises(KernelCodeError, match="beta must be int or float scalar"):
        NnHardSigmoidOp(inp, alpha, symbol_value, result_type, _make_space("global")).verify()

    reduce_input_type = _make_simple_memory_type(
        [2, 3, 4],
        [12, 4, 1],
        element_type=Float32Type(),
    )
    reduce_input = _TestOp(result_types=[reduce_input_type]).results[0]
    reduce_result = _make_simple_memory_type(
        [2, 4],
        [4, 1],
        element_type=Float32Type(),
    )
    NnReduceSumOp(reduce_input, reduce_result, axes=[1], keepdim=False, space=_make_space("global")).verify()
    with pytest.raises(KernelCodeError, match="axes-must-be-non-empty-unique-and-in-range"):
        NnReduceSumOp(
            reduce_input,
            reduce_result,
            axes=ArrayAttr([IntegerAttr(1, IntegerType(32))]),
            keepdim=False,
            space=_make_space("global"),
        ).verify()
    with pytest.raises(KernelCodeError, match="axes-must-be-non-empty-unique-and-in-range"):
        NnReduceSumOp(
            reduce_input,
            reduce_result,
            axes=[1, 1],
            keepdim=False,
            space=_make_space("global"),
        ).verify()
    with pytest.raises(KernelCodeError, match="keepdim-must-be-i1-bool-attr"):
        NnReduceSumOp(
            reduce_input,
            reduce_result,
            axes=[1],
            keepdim=IntegerAttr(1, IntegerType(2)),
            space=_make_space("global"),
        ).verify()
    with pytest.raises(TypeError, match="keepdim must be bool/int or i1 attr"):
        NnReduceSumOp(
            reduce_input,
            reduce_result,
            axes=[1],
            keepdim=StringAttr("bad"),
            space=_make_space("global"),
        )
