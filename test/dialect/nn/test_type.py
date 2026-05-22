"""test type.

功能说明:
- 验证 nn dialect package 拆分后对应 family 的公开行为不变。

使用示例:
- pytest -q test/dialect/nn/test_type.py

关联文件:
- 功能实现: kernel_gen/dialect/nn/
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/nn/test_type.py
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


def test_memory_type_round_trip() -> None:
    ctx = _build_context()
    for text in [
        "!nn.memory<[#symbol.expr<M>, #symbol.expr<?>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>, #symbol.expr<?>], i32, #nn.space<global>>",
        "!nn.memory<[], [], i32, #nn.space<global>>",
        "!nn.memory<[#symbol.expr<?>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tlm1>>",
        "!nn.memory<[#symbol.expr<?>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tlm2>>",
        "!nn.memory<[#symbol.expr<?>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tlm3>>",
    ]:
        memory_type = Parser(ctx, text).parse_attribute()
        assert isinstance(memory_type, NnMemoryType)
        memory_type.verify()
        assert _print_ir(memory_type) == text

def test_memory_type_template_name_round_trip_and_field() -> None:
    """验证 `NnMemoryType.template_name` 文本与公开字段合同。"""

    ctx = _build_context()
    text = "!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>, template = T1>"
    memory_type = Parser(ctx, text).parse_attribute()
    assert isinstance(memory_type, NnMemoryType)
    memory_type.verify()
    assert _print_ir(memory_type) == text
    assert memory_type.template_name.data == "T1"

    cleared = copy_memory_type(memory_type)
    assert cleared.template_name.data == ""
    assert _print_ir(cleared) == "!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>>"

    restored = copy_memory_type_with_template_name(cleared, StringAttr("T2"))
    assert restored.template_name.data == "T2"
    assert _print_ir(restored).endswith(", template = T2>")

@pytest.mark.parametrize("template_name", ["1T", "T 1", "<T1>", ""])
def test_memory_type_rejects_invalid_template_name(template_name: str) -> None:
    """验证 template_name 非法文本按 verifier 合同失败。"""

    if template_name == "":
        memory_type = NnMemoryType(
            ArrayAttr([_expr_attr("M")]),
            ArrayAttr([_expr_attr(1)]),
            i32,
            _make_space("global"),
            template_name=template_name,
        )
        memory_type.verify()
        assert memory_type.template_name.data == ""
        return
    with pytest.raises(VerifyException, match="template_name must be an identifier"):
        NnMemoryType(
            ArrayAttr([_expr_attr("M")]),
            ArrayAttr([_expr_attr(1)]),
            i32,
            _make_space("global"),
            template_name=template_name,
        )

def test_memory_type_rank_mismatch_rejected() -> None:
    with pytest.raises(VerifyException, match="rank must match"):
        NnMemoryType(
            ArrayAttr([_expr_attr(4), _expr_attr(8)]),
            ArrayAttr([_expr_attr(1)]),
            i32,
            _make_space("global"),
        )

def test_memory_type_parse_requires_all_fields() -> None:
    ctx = _build_context()
    with pytest.raises(ParseError):
        Parser(ctx, "!nn.memory<[#symbol.expr<1>], i32, #nn.space<global>>").parse_attribute()

def test_memory_type_parse_rejects_non_space_attr() -> None:
    ctx = _build_context()
    with pytest.raises(ParseError, match="nn memory type space"):
        Parser(ctx, "!nn.memory<[#symbol.expr<1>], [#symbol.expr<1>], i32, i32>").parse_attribute()

@pytest.mark.parametrize(
    ("shape", "stride", "message"),
    [
        ([_expr_attr("-1")], [_expr_attr(1)], "non-negative"),
        ([IntAttr(1)], [_expr_attr(1)], "SymbolExprAttr"),
    ],
)
def test_memory_type_rejects_invalid_dim_entry(
    shape: list[Attribute],
    stride: list[Attribute],
    message: str,
) -> None:
    with pytest.raises(VerifyException, match=message):
        NnMemoryType(
            ArrayAttr(shape),
            ArrayAttr(stride),
            i32,
            _make_space("global"),
        )

def test_memory_type_accepts_stride_question_dim_pair() -> None:
    memory_type = NnMemoryType(
        ArrayAttr([_expr_attr("?")]),
        ArrayAttr([_expr_attr("?")]),
        i32,
        _make_space("global"),
    )
    memory_type.verify()

def test_memory_dim_parser_and_mixed_add_public_parser_contracts() -> None:
    ctx = _build_context()
    rng = random.Random(20260505)
    round_trip_types = [
        '!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], "elem, type", #nn.space<global>>',
        "!nn.memory<[#symbol.expr<N + 1>], [#symbol.expr<1>], tensor<2xf32>, #nn.space<global>>",
        "!nn.memory<[#symbol.expr<M floordiv 2>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], i32, #nn.space<global>>",
    ]
    for text in rng.sample(round_trip_types, k=len(round_trip_types)):
        parsed_type = Parser(ctx, text).parse_attribute()
        assert isinstance(parsed_type, NnMemoryType)
        parsed_type.verify()
        assert _print_ir(parsed_type) == text

    for malformed_text in [
        "!nn.memory",
        "!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>",
        "!nn.memory<#symbol.expr<M>, [#symbol.expr<1>], i32, #nn.space<global>>",
        "!nn.memory<[#symbol.expr<M>), [#symbol.expr<1>], i32, #nn.space<global>>",
        "!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>, >",
        "!nn.memory<[#symbol.expr<M +>], [#symbol.expr<1>], i32, #nn.space<global>>",
    ]:
        with pytest.raises(ParseError):
            Parser(ctx, malformed_text).parse_attribute()

    with pytest.raises(VerifyException, match="SymbolExprAttr"):
        _print_ir(NnMemoryType(ArrayAttr([Float32Type()]), ArrayAttr([_expr_attr(1)]), i32, _make_space("global")))

    parsed = Parser(
        ctx,
        "!nn.memory<[#symbol.expr<M + 1>, #symbol.expr<(K + 2)>, #symbol.expr<tail>], [#symbol.expr<tail>, #symbol.expr<1>, #symbol.expr<?>], i32, #nn.space<global>>",
    ).parse_attribute()
    assert isinstance(parsed, NnMemoryType)
    assert _print_ir(parsed) == "!nn.memory<[#symbol.expr<M + 1>, #symbol.expr<K + 2>, #symbol.expr<tail>], [#symbol.expr<tail>, #symbol.expr<1>, #symbol.expr<?>], i32, #nn.space<global>>"

    complex_expr = "(-DW * (KW - 1) + PL + PR + W - 1) * SW + 1"
    parsed_complex = Parser(
        ctx,
        f"!nn.memory<[#symbol.expr<B>, #symbol.expr<C>, #symbol.expr<{complex_expr}>], [#symbol.expr<C * {complex_expr}>, #symbol.expr<{complex_expr}>, #symbol.expr<1>], i32, #nn.space<global>>",
    ).parse_attribute()
    assert isinstance(parsed_complex, NnMemoryType)
    assert _print_ir(parsed_complex) == "!nn.memory<[#symbol.expr<B>, #symbol.expr<C>, #symbol.expr<(-DW*(KW - 1) + PL + PR + W - 1)*SW + 1>], [#symbol.expr<(-DW*(KW - 1) + PL + PR + W - 1)*C*SW + 1>, #symbol.expr<(-DW*(KW - 1) + PL + PR + W - 1)*SW + 1>, #symbol.expr<1>], i32, #nn.space<global>>"
    floordiv_text = "!nn.memory<[#symbol.expr<M floordiv 2>, #symbol.expr<(N + 1) floordiv T>], [#symbol.expr<(N + 1) floordiv T>, #symbol.expr<1>], i32, #nn.space<global>>"
    parsed_floordiv = Parser(ctx, floordiv_text).parse_attribute()
    assert isinstance(parsed_floordiv, NnMemoryType)
    assert _print_ir(parsed_floordiv) == floordiv_text
    with pytest.raises(ParseError):
        Parser(ctx, "!nn.memory<[#symbol.expr<M//2>], [#symbol.expr<1>], i32, #nn.space<global>>").parse_attribute()

    memory_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
        element_type=Float32Type(),
    )
    lhs = _TestOp(result_types=[memory_type]).results[0]
    scalar = _TestOp(result_types=[SymbolValueType.from_expr("N")]).results[0]

    wrong_space_result = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="attribute space must match memory operand space"):
        NnAddOp(lhs, scalar, wrong_space_result, _make_space("shared")).verify()

    wrong_stride = _make_simple_memory_type(
        [2, 3],
        [1, 1],
        space="global",
        element_type=Float32Type(),
    )
    with pytest.raises(VerifyException, match="result stride must match memory operand"):
        NnAddOp(lhs, scalar, wrong_stride, _make_space("global")).verify()

    wrong_dtype = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
        element_type=Float16Type(),
    )
    with pytest.raises(VerifyException, match="result element_type must match promoted element_type"):
        NnAddOp(lhs, scalar, wrong_dtype, _make_space("global")).verify()
