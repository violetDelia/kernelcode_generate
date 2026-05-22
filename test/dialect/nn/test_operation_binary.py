"""test operation binary.

功能说明:
- 验证 nn dialect package 拆分后对应 family 的公开行为不变。

使用示例:
- pytest -q test/dialect/nn/test_operation_binary.py

关联文件:
- 功能实现: kernel_gen/dialect/nn/
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/nn/test_operation_binary.py
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


def test_add_op_verify_success() -> None:
    memory_type = _make_memory_type()
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[memory_type]).results[0]
    op = NnAddOp(lhs, rhs, memory_type, _make_space("global"))
    op.verify()

def test_div_op_verify_success() -> None:
    space = _make_space("global")
    lhs_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    rhs_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    NnDivOp(lhs, rhs, result_type, space).verify_()

def test_div_op_rejects_shape_mismatch() -> None:
    space = _make_space("global")
    lhs_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    rhs_type = _make_matrix_type([4, 7], [7, 1], element_type=i32)
    result_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnDivOp(lhs, rhs, result_type, space)
    with pytest.raises(VerifyException, match="nn op shape must match across operands and result"):
        op.verify_()

def test_add_op_accepts_memory_const_rhs() -> None:
    memory_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
    )
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[i32]).results[0]
    op = NnAddOp(lhs, rhs, memory_type, _make_space("global"))
    op.verify()

def test_add_op_accepts_memory_symbol_rhs() -> None:
    memory_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
    )
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[SymbolValueType.from_expr("K")]).results[0]
    op = NnAddOp(lhs, rhs, memory_type, _make_space("global"))
    op.verify()

def test_add_op_rejects_operand_space_mismatch() -> None:
    lhs_type = _make_memory_type("global")
    rhs_type = _make_memory_type("shared")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnAddOp(lhs, rhs, lhs_type, _make_space("global"))
    with pytest.raises(VerifyException, match="same space"):
        op.verify()

def test_add_op_rejects_attr_space_mismatch() -> None:
    memory_type = _make_memory_type("local")
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[memory_type]).results[0]
    op = NnAddOp(lhs, rhs, memory_type, _make_space("global"))
    with pytest.raises(VerifyException, match="attribute space"):
        op.verify()

def test_compare_op_requires_i1_result() -> None:
    operand_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("global", i32)
    lhs = _TestOp(result_types=[operand_type]).results[0]
    rhs = _TestOp(result_types=[operand_type]).results[0]
    op = NnEqOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="must be i1"):
        op.verify()

def test_module_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[#symbol.expr<M>, #symbol.expr<?>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>, #symbol.expr<?>], i32, #nn.space<global>>
  %1 = "test.op"() : () -> !nn.memory<[#symbol.expr<M>, #symbol.expr<?>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>, #symbol.expr<?>], i32, #nn.space<global>>
  %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[#symbol.expr<M>, #symbol.expr<?>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>, #symbol.expr<?>], i32, #nn.space<global>>, !nn.memory<[#symbol.expr<M>, #symbol.expr<?>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>, #symbol.expr<?>], i32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<M>, #symbol.expr<?>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>, #symbol.expr<?>], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()

def test_space_mismatch_from_text_rejected() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>>
  %1 = "test.op"() : () -> !nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<shared>>
  %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>>, !nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<shared>>) -> !nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    with pytest.raises(VerifyException, match="same space"):
        module.verify()

def test_attr_space_mismatch_from_text_rejected() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<local>>
  %1 = "test.op"() : () -> !nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<local>>
  %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<local>>, !nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<local>>) -> !nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<local>>
}
"""
    module = Parser(ctx, text).parse_module()
    with pytest.raises(VerifyException, match="attribute space"):
        module.verify()

@pytest.mark.parametrize("op_cls", [NnSubOp, NnMulOp, NnTrueDivOp])
def test_arithmetic_ops_verify_success(op_cls: type[Operation]) -> None:
    memory_type = _make_memory_type()
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[memory_type]).results[0]
    op = op_cls(lhs, rhs, memory_type, _make_space("global"))
    op.verify()

@pytest.mark.parametrize("op_cls", [NnNeOp, NnLtOp, NnLeOp, NnGtOp, NnGeOp])
def test_compare_ops_verify_success(op_cls: type[Operation]) -> None:
    operand_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("global", IntegerType(1))
    lhs = _TestOp(result_types=[operand_type]).results[0]
    rhs = _TestOp(result_types=[operand_type]).results[0]
    op = op_cls(lhs, rhs, result_type, _make_space("global"))
    op.verify()

def test_add_op_rejects_pure_scalar_operands() -> None:
    result_type = _make_simple_memory_type([2, 3], [3, 1], space="global")
    lhs = _TestOp(result_types=[i32]).results[0]
    rhs = _TestOp(result_types=[Float32Type()]).results[0]
    op = NnAddOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="at least one nn.memory operand"):
        op.verify()

def test_add_op_rejects_mixed_result_shape_mismatch() -> None:
    memory_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        [2, 2],
        [2, 1],
        space="global",
    )
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[i32]).results[0]
    op = NnAddOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="result shape must match memory operand"):
        op.verify()

@pytest.mark.parametrize(
    ("lhs_type", "rhs_type", "result_type", "message"),
    [
        (
            _make_simple_memory_type(["M"], [1], space="global"),
            _make_simple_memory_type(["M"], [1], space="global"),
            _make_simple_memory_type(["M"], [1], space="shared"),
            "result space",
        ),
        (
            _make_simple_memory_type(["M"], [2], space="global"),
            _make_simple_memory_type(["M"], [1], space="global"),
            _make_simple_memory_type(["M"], [2], space="global"),
            "stride must match",
        ),
        (
            _make_simple_memory_type(["M"], [1], space="global", element_type=i32),
            _make_simple_memory_type(["M"], [1], space="global", element_type=IntegerType(16)),
            _make_simple_memory_type(["M"], [1], space="global", element_type=i32),
            "operand element_type",
        ),
        (
            _make_simple_memory_type(["M"], [1], space="global", element_type=i32),
            _make_simple_memory_type(["M"], [1], space="global", element_type=i32),
            _make_simple_memory_type(["M"], [1], space="global", element_type=IntegerType(16)),
            "arithmetic result element_type",
        ),
    ],
)
def test_add_op_rejects_type_mismatch(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    result_type: NnMemoryType,
    message: str,
) -> None:
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnAddOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match=message):
        op.verify()

def test_add_op_rejects_implicit_broadcast_shape_mismatch() -> None:
    lhs_type = _make_simple_memory_type([1, "N"], [1, 1])
    rhs_type = _make_simple_memory_type(["M", "N"], [1, 1])
    result_type = _make_simple_memory_type(["M", "N"], [1, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnAddOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape"):
        op.verify()

def test_compare_op_rejects_implicit_broadcast_shape_mismatch() -> None:
    lhs_type = _make_simple_memory_type([1, "N"], [1, 1])
    rhs_type = _make_simple_memory_type(["M", "N"], [1, 1])
    result_type = _make_simple_memory_type(["M", "N"], [1, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnEqOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape"):
        op.verify()

def test_explicit_broadcast_then_add_verify_success() -> None:
    input_type = _make_simple_memory_type([1, "N"], [1, 1])
    target_type = _make_simple_memory_type(["M", "N"], [1, 1])
    other_type = _make_simple_memory_type(["M", "N"], [1, 1])
    inp = _TestOp(result_types=[input_type]).results[0]
    other = _TestOp(result_types=[other_type]).results[0]
    broadcast_op = NnBroadcastOp(inp, target_type, _make_space("global"))
    broadcast_op.verify()
    add_op = NnAddOp(broadcast_op.result, other, target_type, _make_space("global"))
    add_op.verify()

def test_nn_public_validation_branches() -> None:
    good_input = _make_simple_memory_type([2], [1], space="global", element_type=Float32Type())
    bad_input = _make_simple_memory_type([2], [1], space="global", element_type=i32)
    good_result = _make_simple_memory_type([2], [1], space="global", element_type=Float32Type())
    good_input_value = _TestOp(result_types=[good_input]).results[0]
    with pytest.raises(VerifyException, match="operand-element-type-must-be-float"):
        NnExpOp(_TestOp(result_types=[bad_input]).results[0], good_result, _make_space("global")).verify()
    with pytest.raises(VerifyException, match="result-shape-stride-must-match-input"):
        NnExpOp(
            good_input_value,
            _make_simple_memory_type([2], [2], space="global"),
            _make_space("global"),
        ).verify()
    with pytest.raises(VerifyException, match="alpha must be int or float scalar"):
        NnLeakyReluOp(
            good_input_value,
            _TestOp(result_types=[_make_memory_type()]).results[0],
            good_result,
            _make_space("global"),
        ).verify()

    img2col_input = _make_simple_memory_type(
        [1, 2, 8],
        [16, 8, 1],
        space="global",
        element_type=Float32Type(),
    )
    img2col_result = _make_simple_memory_type(
        [1, 2, 3, 8],
        [48, 24, 8, 1],
        space="global",
        element_type=Float32Type(),
    )
    img2col_input_value = _TestOp(result_types=[img2col_input]).results[0]
    with pytest.raises(VerifyException, match="kw-sw-dw-must-be-int-or-symbol"):
        NnImg2col1dOp(
            img2col_input_value,
            img2col_result,
            kw=_TestOp(result_types=[Float32Type()]).results[0],
            sw=arith.ConstantOp(IntegerAttr(1, i32)).result,
            dw=arith.ConstantOp(IntegerAttr(1, i32)).result,
            pl=arith.ConstantOp(IntegerAttr(0, i32)).result,
            pr=arith.ConstantOp(IntegerAttr(0, i32)).result,
            space=_make_space("global"),
        ).verify()
    with pytest.raises(VerifyException, match="kw-sw-dw-must-be-positive"):
        NnImg2col1dOp(
            img2col_input_value,
            img2col_result,
            kw=arith.ConstantOp(IntegerAttr(0, i32)).result,
            sw=arith.ConstantOp(IntegerAttr(1, i32)).result,
            dw=arith.ConstantOp(IntegerAttr(1, i32)).result,
            pl=arith.ConstantOp(IntegerAttr(0, i32)).result,
            pr=arith.ConstantOp(IntegerAttr(0, i32)).result,
            space=_make_space("global"),
        ).verify()

def test_mixed_scalar_binary_family_public_contracts() -> None:
    rng = random.Random(20260505)
    op_classes = rng.sample([NnSubOp, NnMulOp, NnTrueDivOp, NnFloorDivOp], k=4)
    memory_i32 = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
        element_type=i32,
    )
    result_f16 = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        space="global",
        element_type=Float16Type(),
    )
    memory_value = _TestOp(result_types=[memory_i32]).results[0]
    scalar_f16 = _TestOp(result_types=[Float16Type()]).results[0]

    for op_cls in op_classes:
        op_cls(memory_value, scalar_f16, result_f16, _make_space("global")).verify()
        op_cls(scalar_f16, memory_value, result_f16, _make_space("global")).verify()

        with pytest.raises(VerifyException, match="requires at least one nn.memory operand"):
            op_cls(
                _TestOp(result_types=[i32]).results[0],
                _TestOp(result_types=[Float32Type()]).results[0],
                result_f16,
                _make_space("global"),
            ).verify()

        with pytest.raises(VerifyException, match="attribute space must match memory operand space"):
            op_cls(memory_value, scalar_f16, result_f16, _make_space("shared")).verify()

        wrong_space_result = _make_simple_memory_type(
            [2, 3],
            [3, 1],
            space="shared",
            element_type=Float16Type(),
        )
        with pytest.raises(VerifyException, match="result space must match memory operand"):
            op_cls(memory_value, scalar_f16, wrong_space_result, _make_space("global")).verify()

        wrong_shape = _make_simple_memory_type(
            [2, 4],
            [4, 1],
            space="global",
            element_type=Float16Type(),
        )
        with pytest.raises(VerifyException, match="result shape must match memory operand"):
            op_cls(memory_value, scalar_f16, wrong_shape, _make_space("global")).verify()

        wrong_stride = _make_simple_memory_type(
            [2, 3],
            [1, 1],
            space="global",
            element_type=Float16Type(),
        )
        with pytest.raises(VerifyException, match="result stride must match memory operand"):
            op_cls(memory_value, scalar_f16, wrong_stride, _make_space("global")).verify()

        with pytest.raises(VerifyException, match="scalar element_type must be i32/f16/f32 or symbol.int"):
            op_cls(
                memory_value,
                _TestOp(result_types=[IntegerType(16)]).results[0],
                result_f16,
                _make_space("global"),
            ).verify()

        wrong_dtype = _make_simple_memory_type(
            [2, 3],
            [3, 1],
            space="global",
            element_type=i32,
        )
        with pytest.raises(VerifyException, match="result element_type must match promoted element_type"):
            op_cls(memory_value, scalar_f16, wrong_dtype, _make_space("global")).verify()
