"""nn dialect tests.


功能说明:
- 覆盖 nn dialect 的 attr/type/op verifier、parse/print 与 round-trip 行为。

使用示例:
- pytest -q test/dialect/test_nn.py

覆盖率:
- 覆盖率命令: pytest -q --cov=kernel_gen.dialect.nn --cov-report=term-missing test/dialect/test_nn.py
- 覆盖率结果: 99%（2026-03-22 13:09:11 +0800）

关联文件:
- 功能实现: kernel_gen/dialect/nn.py
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/test_nn.py
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

REPO_ROOT = Path(__file__).resolve().parents[2]
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
    has_memory_template_name,
    memory_template_name,
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
    - test: test/dialect/test_nn.py
    - 功能实现: kernel_gen/dialect/nn.py
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
    - test: test/dialect/test_nn.py
    - 功能实现: kernel_gen/dialect/nn.py
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
    - test: test/dialect/test_nn.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return NnMemoryType(
        ArrayAttr(_symbol_dims(shape)),
        ArrayAttr(_symbol_dims(stride)),
        element_type,
        _make_space(space),
    )


# TY-001
# 功能说明: 验证 memory type parse/print 可稳定 round-trip。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_memory_type_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


def test_memory_type_template_name_round_trip_and_helpers() -> None:
    """验证 `NnMemoryType.template_name` 文本与 helper 公开合同。"""

    ctx = _build_context()
    text = "!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>, template = T1>"
    memory_type = Parser(ctx, text).parse_attribute()
    assert isinstance(memory_type, NnMemoryType)
    memory_type.verify()
    assert _print_ir(memory_type) == text
    assert memory_template_name(memory_type) == "T1"
    assert has_memory_template_name(memory_type) is True

    cleared = copy_memory_type(memory_type)
    assert memory_template_name(cleared) is None
    assert _print_ir(cleared) == "!nn.memory<[#symbol.expr<M>], [#symbol.expr<1>], i32, #nn.space<global>>"

    restored = copy_memory_type_with_template_name(cleared, StringAttr("T2"))
    assert memory_template_name(restored) == "T2"
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
        assert memory_template_name(memory_type) is None
        return
    with pytest.raises(VerifyException, match="template_name must be an identifier"):
        NnMemoryType(
            ArrayAttr([_expr_attr("M")]),
            ArrayAttr([_expr_attr(1)]),
            i32,
            _make_space("global"),
            template_name=template_name,
        )


# TY-002
# 功能说明: 验证公开 `global/shared/local/tsm/tlm1/tlm2/tlm3` space text form 均可 parse/print round-trip。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_space_attr_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_space_attr_round_trip() -> None:
    ctx = _build_context()
    for text in [
        "#nn.space<global>",
        "#nn.space<shared>",
        "#nn.space<local>",
        "#nn.space<tsm>",
        "#nn.space<tlm1>",
        "#nn.space<tlm2>",
        "#nn.space<tlm3>",
    ]:
        space_attr = Parser(ctx, text).parse_attribute()
        assert isinstance(space_attr, NnMemorySpaceAttr)
        space_attr.verify()
        assert _print_ir(space_attr) == text

    from_name = NnMemorySpaceAttr.from_name("global")
    from_name.verify()
    assert _print_ir(from_name) == "#nn.space<global>"


# TY-002A
# 功能说明: 验证非法或已废弃的 space attribute 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_invalid_space_attr_rejected
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_invalid_space_attr_rejected() -> None:
    with pytest.raises(VerifyException, match="global/shared/local/tsm/tlm1/tlm2/tlm3"):
        _make_space("register").verify()

    with pytest.raises(VerifyException, match="global/shared/local/tsm/tlm1/tlm2/tlm3"):
        _make_space("tlm").verify()


# TY-003
# 功能说明: 验证 memory type 的 shape/stride rank mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_memory_type_rank_mismatch_rejected
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_memory_type_rank_mismatch_rejected() -> None:
    with pytest.raises(VerifyException, match="rank must match"):
        NnMemoryType(
            ArrayAttr([_expr_attr(4), _expr_attr(8)]),
            ArrayAttr([_expr_attr(1)]),
            i32,
            _make_space("global"),
        )


# TY-004
# 功能说明: 验证 nn.add 在 operand/result/space 一致时可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_add_op_verify_success() -> None:
    memory_type = _make_memory_type()
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[memory_type]).results[0]
    op = NnAddOp(lhs, rhs, memory_type, _make_space("global"))
    op.verify()


# NN-DIA-043
# 功能说明: 验证 nn.div 合法路径可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_div_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_div_op_verify_success() -> None:
    space = _make_space("global")
    lhs_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    rhs_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    NnDivOp(lhs, rhs, result_type, space).verify_()


# NN-DIA-046
# 功能说明: 验证 nn.div 在形状不一致时触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_div_op_rejects_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-ADD-A1-001
# 功能说明: 验证 nn.add 支持 memory + const scalar。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_accepts_memory_const_rhs
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-044
# 功能说明: 验证 nn.select 合法路径可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_select_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_select_op_verify_success() -> None:
    space = _make_space("global")
    cond_type = _make_matrix_type([4, 8], [8, 1], element_type=i1)
    data_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    cond = _TestOp(result_types=[cond_type]).results[0]
    lhs = _TestOp(result_types=[data_type]).results[0]
    rhs = _TestOp(result_types=[data_type]).results[0]
    NnSelectOp(cond, lhs, rhs, result_type, space).verify_()


# NN-DIA-047
# 功能说明: 验证 nn.select 在 cond 非 i1 时触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_select_op_rejects_cond_element_type
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-045
# 功能说明: 验证 nn.cast 合法路径可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_cast_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_cast_op_verify_success() -> None:
    space = _make_space("global")
    input_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 8], [8, 1], element_type=IntegerType(16))
    input_value = _TestOp(result_types=[input_type]).results[0]
    NnCastOp(input_value, result_type, space).verify_()


# NN-DIA-048
# 功能说明: 验证 nn.cast 在 shape 不一致时触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_cast_op_rejects_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_cast_op_rejects_shape_mismatch() -> None:
    space = _make_space("global")
    input_type = _make_matrix_type([4, 8], [8, 1], element_type=i32)
    result_type = _make_matrix_type([4, 7], [7, 1], element_type=IntegerType(16))
    input_value = _TestOp(result_types=[input_type]).results[0]
    op = NnCastOp(input_value, result_type, space)
    with pytest.raises(VerifyException, match="nn.cast shape must match input"):
        op.verify_()


# NN-ADD-A1-002
# 功能说明: 验证 nn.add 支持 memory + symbol.int。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_accepts_memory_symbol_rhs
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TY-005
# 功能说明: 验证 nn.add operand space mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_rejects_operand_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_add_op_rejects_operand_space_mismatch() -> None:
    lhs_type = _make_memory_type("global")
    rhs_type = _make_memory_type("shared")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnAddOp(lhs, rhs, lhs_type, _make_space("global"))
    with pytest.raises(VerifyException, match="same space"):
        op.verify()


# TY-006
# 功能说明: 验证 op attribute space 与 type space 不一致时会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_rejects_attr_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_add_op_rejects_attr_space_mismatch() -> None:
    memory_type = _make_memory_type("local")
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[memory_type]).results[0]
    op = NnAddOp(lhs, rhs, memory_type, _make_space("global"))
    with pytest.raises(VerifyException, match="attribute space"):
        op.verify()


# TY-007
# 功能说明: 验证比较 op 结果 element_type 必须固定为 i1。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_compare_op_requires_i1_result
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_compare_op_requires_i1_result() -> None:
    operand_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("global", i32)
    lhs = _TestOp(result_types=[operand_type]).results[0]
    rhs = _TestOp(result_types=[operand_type]).results[0]
    op = NnEqOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="must be i1"):
        op.verify()


# TY-008
# 功能说明: 验证模块 parse/print 可在 nn op 上保持 round-trip。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_module_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TY-009
# 功能说明: 验证 parse 后的 nn.add 在 space mismatch 场景下会被 verifier 捕获。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_space_mismatch_from_text_rejected
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TY-010
# 功能说明: 验证文本 assembly 中 op attribute space 与 type space 不一致时会在 verify 阶段失败。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_attr_space_mismatch_from_text_rejected
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TY-011
# 功能说明: 验证缺失字段的 nn.memory 文本会在 parse 阶段失败。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_memory_type_parse_requires_all_fields
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_memory_type_parse_requires_all_fields() -> None:
    ctx = _build_context()
    with pytest.raises(ParseError):
        Parser(ctx, "!nn.memory<[#symbol.expr<1>], i32, #nn.space<global>>").parse_attribute()


# TY-012
# 功能说明: 验证 memory type space 不是 nn.space 时 parse 会失败。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_memory_type_parse_rejects_non_space_attr
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_memory_type_parse_rejects_non_space_attr() -> None:
    ctx = _build_context()
    with pytest.raises(ParseError, match="nn memory type space"):
        Parser(ctx, "!nn.memory<[#symbol.expr<1>], [#symbol.expr<1>], i32, i32>").parse_attribute()


# TY-013
# 功能说明: 验证 memory type 非法维度条目会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_memory_type_rejects_invalid_dim_entry
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TY-014
# 功能说明: 验证 stride '?' 与 shape '?' 同位时作为匿名动态布局通过。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_memory_type_accepts_stride_question_dim_pair
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_memory_type_accepts_stride_question_dim_pair() -> None:
    memory_type = NnMemoryType(
        ArrayAttr([_expr_attr("?")]),
        ArrayAttr([_expr_attr("?")]),
        i32,
        _make_space("global"),
    )
    memory_type.verify()


# TY-015
# 功能说明: 验证逐元素算术 op(sub/mul/truediv) 合法输入可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_arithmetic_ops_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
@pytest.mark.parametrize("op_cls", [NnSubOp, NnMulOp, NnTrueDivOp])
def test_arithmetic_ops_verify_success(op_cls: type[Operation]) -> None:
    memory_type = _make_memory_type()
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[memory_type]).results[0]
    op = op_cls(lhs, rhs, memory_type, _make_space("global"))
    op.verify()


# TY-016
# 功能说明: 验证比较 op(ne/lt/le/gt/ge) 合法输入可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_compare_ops_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
@pytest.mark.parametrize("op_cls", [NnNeOp, NnLtOp, NnLeOp, NnGtOp, NnGeOp])
def test_compare_ops_verify_success(op_cls: type[Operation]) -> None:
    operand_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("global", IntegerType(1))
    lhs = _TestOp(result_types=[operand_type]).results[0]
    rhs = _TestOp(result_types=[operand_type]).results[0]
    op = op_cls(lhs, rhs, result_type, _make_space("global"))
    op.verify()


# TY-017
# 功能说明: 验证 nn.add 在纯 scalar operand 下会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_rejects_pure_scalar_operands
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_add_op_rejects_pure_scalar_operands() -> None:
    result_type = _make_simple_memory_type([2, 3], [3, 1], space="global")
    lhs = _TestOp(result_types=[i32]).results[0]
    rhs = _TestOp(result_types=[Float32Type()]).results[0]
    op = NnAddOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="at least one nn.memory operand"):
        op.verify()


# NN-ADD-A1-003
# 功能说明: 验证 nn.add 在 memory+scalar 场景 result shape 不一致会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_rejects_mixed_result_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TY-018
# 功能说明: 验证 nn.add 在 space/stride/element_type 不一致时会拒绝。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_rejects_type_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TC-NN-BC-001
# 功能说明: 验证 nn.broadcast 合法输入可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_broadcast_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TC-NN-BC-002
# 功能说明: 验证 nn.broadcast 在 space 不一致时报错。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_broadcast_op_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_broadcast_op_space_mismatch() -> None:
    input_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("shared", i32)
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="result-space-must-match-input-and-attr"):
        op.verify()


# TC-NN-BC-003
# 功能说明: 验证 nn.broadcast 在 element_type 不一致时报错。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_broadcast_op_element_type_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_broadcast_op_element_type_mismatch() -> None:
    input_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("global", IntegerType(1))
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="result-element-type-must-match-input"):
        op.verify()


# TC-NN-BC-005
# 功能说明: 验证 nn.broadcast 在 space/rank/shape 不满足时会拒绝。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_broadcast_op_rejects_invalid_inputs
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# TC-NN-BC-004
# 功能说明: 验证含 nn.broadcast 的模块可 round-trip。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_broadcast_module_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-036
# 功能说明: 验证 nn.transpose 在合法输入下通过 verifier。
# 测试目的: 保证 perm/shape/stride/space/element type 校验通过时可成功生成 op。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_transpose_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-037
# 功能说明: 验证 nn.transpose perm 非法时会触发 verifier。
# 测试目的: 保证 perm 长度/排列不合法时及时拒绝。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_transpose_op_rejects_invalid_perm
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-038
# 功能说明: 验证 nn.transpose 在 shape/stride/space/element type 不一致时拒绝。
# 测试目的: 确保 result 类型与空间约束严格匹配 perm 规则。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_transpose_op_result_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-039
# 功能说明: 验证含 nn.transpose 的模块可 round-trip。
# 测试目的: 确保 nn.transpose 的 parse/print 文本稳定。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_transpose_module_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-045
# 功能说明: 验证 nn.softmax 在合法输入下通过 verifier。
# 测试目的: 保证 rank/axis/shape/stride/space/element type 合法时可构造 op。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_softmax_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_softmax_op_verify_success() -> None:
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
    op = NnSoftmaxOp(inp, result_type, axis=-1, space=_make_space("global"))
    op.verify()


# NN-DIA-046
# 功能说明: 验证 nn.softmax axis 越界或 rank 非法时拒绝。
# 测试目的: 覆盖 rank<=0 与 axis 超界的 verifier 错误路径。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_softmax_op_rejects_invalid_axis_or_rank
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
@pytest.mark.parametrize(
    ("input_type", "axis", "message"),
    [
        (
            _make_simple_memory_type(
                [2, 3],
                [3, 1],
                element_type=Float32Type(),
            ),
            2,
            "axis-must-be-in-range",
        ),
        (
            _make_simple_memory_type(
                [],
                [],
                element_type=Float32Type(),
            ),
            0,
            "input-rank-must-be-positive",
        ),
    ],
)
def test_softmax_op_rejects_invalid_axis_or_rank(
    input_type: NnMemoryType,
    axis: int,
    message: str,
) -> None:
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnSoftmaxOp(inp, input_type, axis=axis, space=_make_space("global"))
    with pytest.raises(VerifyException, match=message):
        op.verify()


# NN-DIA-047
# 功能说明: 验证 nn.softmax result shape/stride/space/element type 不一致时拒绝。
# 测试目的: 覆盖 result 不匹配与空间不一致的 verifier 错误路径。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_softmax_op_rejects_result_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
@pytest.mark.parametrize(
    ("result_type", "space", "message"),
    [
        (
            _make_simple_memory_type(
                [2, 2],
                [2, 1],
                element_type=Float32Type(),
            ),
            "global",
            "result-shape-must-match-input",
        ),
        (
            _make_simple_memory_type(
                [2, 3],
                [1, 1],
                element_type=Float32Type(),
            ),
            "global",
            "result-stride-must-match-input",
        ),
        (
            _make_simple_memory_type(
                [2, 3],
                [3, 1],
                element_type=i32,
            ),
            "global",
            "result-element-type-must-match-input-and-be-float",
        ),
        (
            _make_simple_memory_type(
                [2, 3],
                [3, 1],
                element_type=Float32Type(),
                space="shared",
            ),
            "global",
            "result-space-must-match-input-and-attr",
        ),
        (
            _make_simple_memory_type(
                [2, 3],
                [3, 1],
                element_type=Float32Type(),
            ),
            "shared",
            "result-space-must-match-input-and-attr",
        ),
    ],
)
def test_softmax_op_rejects_result_mismatch(
    result_type: NnMemoryType,
    space: str,
    message: str,
) -> None:
    input_type = _make_simple_memory_type(
        [2, 3],
        [3, 1],
        element_type=Float32Type(),
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnSoftmaxOp(inp, result_type, axis=1, space=_make_space(space))
    with pytest.raises(VerifyException, match=message):
        op.verify()


# TC-NN-MM-001
# 功能说明: 验证 nn.matmul 在合法输入下通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_op_verify_success() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1])
    rhs_type = _make_matrix_type(["K", "N"], [8, 1])
    result_type = _make_matrix_type(["M", "N"], [8, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    op.verify()


# TC-NN-MM-002
# 功能说明: 验证 contracting 维度不匹配时 nn.matmul 抛错。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_op_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_op_shape_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1])
    rhs_type = _make_matrix_type(["Q", "N"], [8, 1])
    result_type = _make_matrix_type(["M", "N"], [8, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="contracting"):
        op.verify()


# TC-NN-MM-003
# 功能说明: 验证结果 shape 不匹配时 nn.matmul 抛错。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_op_result_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_op_result_shape_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1])
    rhs_type = _make_matrix_type(["K", "N"], [8, 1])
    result_type = _make_matrix_type(["M", "K"], [8, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="result shape"):
        op.verify()


# TC-NN-MM-004
# 功能说明: 验证含 nn.matmul 的模块 parse/print round-trip。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_module_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_module_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[#symbol.expr<M>, #symbol.expr<K>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>
  %1 = "test.op"() : () -> !nn.memory<[#symbol.expr<K>, #symbol.expr<N>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>
  %2 = "nn.matmul"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[#symbol.expr<M>, #symbol.expr<K>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>, !nn.memory<[#symbol.expr<K>, #symbol.expr<N>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<M>, #symbol.expr<N>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()


# TC-NN-MM-005
# 功能说明: 验证 matmul operand space mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_op_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_op_space_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1], space="global")
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], space="shared")
    result_type = _make_matrix_type(["M", "N"], [8, 1], space="global")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="same space"):
        op.verify()


# TC-NN-MM-006
# 功能说明: 验证 matmul attribute space mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_op_attr_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_op_attr_space_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1], space="local")
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], space="local")
    result_type = _make_matrix_type(["M", "N"], [8, 1], space="local")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="attribute space"):
        op.verify()


# TC-NN-MM-009
# 功能说明: 验证 matmul result space 不一致时会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_op_result_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_op_result_space_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1], space="global")
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], space="global")
    result_type = _make_matrix_type(["M", "N"], [8, 1], space="shared")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="result space"):
        op.verify()


# TC-NN-MM-007
# 功能说明: 验证 matmul rank!=2 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_op_rank_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_op_rank_mismatch() -> None:
    lhs_type = _make_memory_type("global")
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], space="global")
    result_type = _make_matrix_type(["M", "N"], [8, 1], space="global")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="rank-2"):
        op.verify()


# TC-NN-MM-008
# 功能说明: 验证 matmul element_type 不一致会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_matmul_op_element_type_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_matmul_op_element_type_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1], element_type=i32)
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], element_type=i32)
    result_type = _make_matrix_type(["M", "N"], [8, 1], element_type=IntegerType(16))
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="element_type"):
        op.verify()


# TC-NN-IB-001
# 功能说明: 验证 nn.add 拒绝隐式 broadcast 形状。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_add_op_rejects_implicit_broadcast_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_add_op_rejects_implicit_broadcast_shape_mismatch() -> None:
    lhs_type = _make_simple_memory_type([1, "N"], [1, 1])
    rhs_type = _make_simple_memory_type(["M", "N"], [1, 1])
    result_type = _make_simple_memory_type(["M", "N"], [1, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnAddOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape"):
        op.verify()


# TC-NN-IB-002
# 功能说明: 验证 nn.eq 拒绝隐式 broadcast 形状。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_compare_op_rejects_implicit_broadcast_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_compare_op_rejects_implicit_broadcast_shape_mismatch() -> None:
    lhs_type = _make_simple_memory_type([1, "N"], [1, 1])
    rhs_type = _make_simple_memory_type(["M", "N"], [1, 1])
    result_type = _make_simple_memory_type(["M", "N"], [1, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnEqOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape"):
        op.verify()


# TC-NN-IB-003
# 功能说明: 验证显式 broadcast 后再执行 nn.add 可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_explicit_broadcast_then_add_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-040
# 功能说明: 验证 nn.img2col1d 合同的正向与负向约束。
# 测试目的: 覆盖 operand/attrs/result/space 一致性以及形状/步幅合同校验。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_nn_dialect_img2col1d_contract_v1
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_nn_dialect_img2col1d_contract_v1() -> None:
    input_type = _make_simple_memory_type(
        [1, 2, 8],
        [16, 8, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        [1, 2, 3, 8],
        [48, 24, 8, 1],
        space="global",
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    kw = arith.ConstantOp(IntegerAttr(3, i32)).result
    sw = arith.ConstantOp(IntegerAttr(1, i32)).result
    dw = arith.ConstantOp(IntegerAttr(1, i32)).result
    pl = arith.ConstantOp(IntegerAttr(1, i32)).result
    pr = arith.ConstantOp(IntegerAttr(1, i32)).result
    op = NnImg2col1dOp(inp, result_type, kw=kw, sw=sw, dw=dw, pl=pl, pr=pr, space=_make_space("global"))
    op.verify()

    cases = [
        (
            _make_simple_memory_type([1, 2], [2, 1], space="global"),
            result_type,
            {"kw": 3, "sw": 1, "dw": 1, "pl": 1, "pr": 1},
            "global",
            "operand-must-be-rank-3-nn-memory",
        ),
        (
            input_type,
            result_type,
            {"kw": 0, "sw": 1, "dw": 1, "pl": 1, "pr": 1},
            "global",
            "kw-sw-dw-must-be-positive",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 2, 3],
                [6, 3, 1],
                space="global",
            ),
            {"kw": 3, "sw": 1, "dw": 1, "pl": 1, "pr": 1},
            "global",
            "result-rank-must-be-4",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 2, 3, 8],
                [48, 24, 8, 1],
                space="shared",
            ),
            {"kw": 3, "sw": 1, "dw": 1, "pl": 1, "pr": 1},
            "global",
            "result-space-matches-input",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 2, 4, 8],
                [64, 32, 8, 1],
                space="global",
            ),
            {"kw": 3, "sw": 1, "dw": 1, "pl": 1, "pr": 1},
            "global",
            "result-shape-stride-must-match-img2col1d-contract",
        ),
        (
            input_type,
            result_type,
            {"kw": 3, "sw": 1, "dw": 1, "pl": 1, "pr": 1},
            "shared",
            "result-space-matches-input",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 2, 3, 8],
                [48, 24, 8, 1],
                space="global",
                element_type=IntegerType(16),
            ),
            {"kw": 3, "sw": 1, "dw": 1, "pl": 1, "pr": 1},
            "global",
            "result-element-type-matches-input",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 2, 3, 8],
                [48, 24, 8, 2],
                space="global",
            ),
            {"kw": 3, "sw": 1, "dw": 1, "pl": 1, "pr": 1},
            "global",
            "result-shape-stride-must-match-img2col1d-contract",
        ),
        (
            _make_simple_memory_type(
                [1, 2, 2],
                [4, 2, 1],
                space="global",
            ),
            _make_simple_memory_type(
                [1, 2, 3, 1],
                [6, 3, 1, 1],
                space="global",
            ),
            {"kw": 3, "sw": 1, "dw": 1, "pl": 0, "pr": 0},
            "global",
            "result-shape-stride-must-match-img2col1d-contract",
        ),
    ]
    for case_input, case_result, attrs, space, message in cases:
        case_inp = _TestOp(result_types=[case_input]).results[0]
        kw = arith.ConstantOp(IntegerAttr(attrs["kw"], i32)).result
        sw = arith.ConstantOp(IntegerAttr(attrs["sw"], i32)).result
        dw = arith.ConstantOp(IntegerAttr(attrs["dw"], i32)).result
        pl = arith.ConstantOp(IntegerAttr(attrs["pl"], i32)).result
        pr = arith.ConstantOp(IntegerAttr(attrs["pr"], i32)).result
        case_op = NnImg2col1dOp(
            case_inp,
            case_result,
            kw=kw,
            sw=sw,
            dw=dw,
            pl=pl,
            pr=pr,
            space=_make_space(space),
        )
        with pytest.raises(VerifyException, match=message):
            case_op.verify()


# NN-DIA-041
# 功能说明: 验证 nn.img2col2d 合同的正向与负向约束。
# 测试目的: 覆盖 operand/attrs/result/space 一致性以及形状/步幅合同校验。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_nn_dialect_img2col2d_contract_v1
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_nn_dialect_img2col2d_contract_v1() -> None:
    input_type = _make_simple_memory_type(
        [1, 3, 5, 5],
        [75, 25, 5, 1],
        space="global",
    )
    result_type = _make_simple_memory_type(
        [1, 3, 3, 3, 5, 5],
        [675, 225, 75, 25, 5, 1],
        space="global",
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    kh = arith.ConstantOp(IntegerAttr(3, i32)).result
    kw = arith.ConstantOp(IntegerAttr(3, i32)).result
    sh = arith.ConstantOp(IntegerAttr(1, i32)).result
    sw = arith.ConstantOp(IntegerAttr(1, i32)).result
    dh = arith.ConstantOp(IntegerAttr(1, i32)).result
    dw = arith.ConstantOp(IntegerAttr(1, i32)).result
    ph = arith.ConstantOp(IntegerAttr(1, i32)).result
    pw = arith.ConstantOp(IntegerAttr(1, i32)).result
    pl = arith.ConstantOp(IntegerAttr(1, i32)).result
    pr = arith.ConstantOp(IntegerAttr(1, i32)).result
    op = NnImg2col2dOp(
        inp,
        result_type,
        kh=kh,
        kw=kw,
        sh=sh,
        sw=sw,
        dh=dh,
        dw=dw,
        ph=ph,
        pw=pw,
        pl=pl,
        pr=pr,
        space=_make_space("global"),
    )
    op.verify()

    cases = [
        (
            _make_simple_memory_type(
                [1, 3, 5],
                [15, 5, 1],
                space="global",
            ),
            result_type,
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 1, "pw": 1, "pl": 1, "pr": 1},
            "global",
            "operand-must-be-rank-4-nn-memory",
        ),
        (
            input_type,
            result_type,
            {"kh": 0, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 1, "pw": 1, "pl": 1, "pr": 1},
            "global",
            "kh-kw-sh-sw-dh-dw-must-be-positive",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 3, 3],
                [9, 3, 1],
                space="global",
            ),
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 1, "pw": 1, "pl": 1, "pr": 1},
            "global",
            "result-rank-must-be-6",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 3, 3, 3, 5, 5],
                [675, 225, 75, 25, 5, 1],
                space="shared",
            ),
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 1, "pw": 1, "pl": 1, "pr": 1},
            "global",
            "result-space-matches-input",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 3, 3, 4, 5, 5],
                [900, 300, 100, 25, 5, 1],
                space="global",
            ),
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 1, "pw": 1, "pl": 1, "pr": 1},
            "global",
            "result-shape-stride-must-match-img2col2d-contract",
        ),
        (
            input_type,
            result_type,
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 1, "pw": 1, "pl": 1, "pr": 1},
            "shared",
            "result-space-matches-input",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 3, 3, 3, 5, 5],
                [675, 225, 75, 25, 5, 1],
                space="global",
                element_type=IntegerType(16),
            ),
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 1, "pw": 1, "pl": 1, "pr": 1},
            "global",
            "result-element-type-matches-input",
        ),
        (
            input_type,
            _make_simple_memory_type(
                [1, 3, 3, 3, 5, 5],
                [675, 225, 75, 25, 5, 2],
                space="global",
            ),
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 1, "pw": 1, "pl": 1, "pr": 1},
            "global",
            "result-shape-stride-must-match-img2col2d-contract",
        ),
        (
            _make_simple_memory_type(
                [1, 3, 2, 5],
                [30, 10, 5, 1],
                space="global",
            ),
            _make_simple_memory_type(
                [1, 3, 3, 3, 1, 3],
                [81, 27, 9, 3, 3, 1],
                space="global",
            ),
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 0, "pw": 0, "pl": 0, "pr": 0},
            "global",
            "result-shape-stride-must-match-img2col2d-contract",
        ),
        (
            _make_simple_memory_type(
                [1, 3, 5, 2],
                [30, 10, 2, 1],
                space="global",
            ),
            _make_simple_memory_type(
                [1, 3, 3, 3, 5, 1],
                [135, 45, 15, 5, 1, 1],
                space="global",
            ),
            {"kh": 3, "kw": 3, "sh": 1, "sw": 1, "dh": 1, "dw": 1, "ph": 0, "pw": 0, "pl": 0, "pr": 0},
            "global",
            "result-shape-stride-must-match-img2col2d-contract",
        ),
    ]
    for case_input, case_result, attrs, space, message in cases:
        case_inp = _TestOp(result_types=[case_input]).results[0]
        kh = arith.ConstantOp(IntegerAttr(attrs["kh"], i32)).result
        kw = arith.ConstantOp(IntegerAttr(attrs["kw"], i32)).result
        sh = arith.ConstantOp(IntegerAttr(attrs["sh"], i32)).result
        sw = arith.ConstantOp(IntegerAttr(attrs["sw"], i32)).result
        dh = arith.ConstantOp(IntegerAttr(attrs["dh"], i32)).result
        dw = arith.ConstantOp(IntegerAttr(attrs["dw"], i32)).result
        ph = arith.ConstantOp(IntegerAttr(attrs["ph"], i32)).result
        pw = arith.ConstantOp(IntegerAttr(attrs["pw"], i32)).result
        pl = arith.ConstantOp(IntegerAttr(attrs["pl"], i32)).result
        pr = arith.ConstantOp(IntegerAttr(attrs["pr"], i32)).result
        case_op = NnImg2col2dOp(
            case_inp,
            case_result,
            kh=kh,
            kw=kw,
            sh=sh,
            sw=sw,
            dh=dh,
            dw=dw,
            ph=ph,
            pw=pw,
            pl=pl,
            pr=pr,
            space=_make_space(space),
        )
        with pytest.raises(VerifyException, match=message):
            case_op.verify()


# NN-DIA-045
# 功能说明: 验证 nn.exp 浮点输入与元信息保持的合法路径。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_exp_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_exp_op_verify_success() -> None:
    input_type = _make_simple_memory_type(
        [2, 4],
        [4, 1],
        space="global",
        element_type=Float32Type(),
    )
    result_type = _make_simple_memory_type(
        [2, 4],
        [4, 1],
        space="global",
        element_type=Float32Type(),
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnExpOp(inp, result_type, _make_space("global"))
    op.verify()


# NN-DIA-046
# 功能说明: 验证 nn.exp 对非浮点输入与 shape/stride/space 不一致的拒绝路径。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_exp_op_rejects_invalid_inputs
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_exp_op_rejects_invalid_inputs() -> None:
    float_input = _make_simple_memory_type(
        [2, 4],
        [4, 1],
        space="global",
        element_type=Float32Type(),
    )
    float_result = _make_simple_memory_type(
        [2, 4],
        [4, 1],
        space="global",
        element_type=Float32Type(),
    )
    cases = [
        (
            _make_simple_memory_type(
                [2, 4],
                [4, 1],
                space="global",
                element_type=i32,
            ),
            _make_simple_memory_type(
                [2, 4],
                [4, 1],
                space="global",
                element_type=i32,
            ),
            "global",
            "operand-element-type-must-be-float",
        ),
        (
            float_input,
            _make_simple_memory_type(
                [2, 5],
                [5, 1],
                space="global",
                element_type=Float32Type(),
            ),
            "global",
            "result-shape-stride-must-match-input",
        ),
        (
            float_input,
            _make_simple_memory_type(
                [2, 4],
                [5, 1],
                space="global",
                element_type=Float32Type(),
            ),
            "global",
            "result-shape-stride-must-match-input",
        ),
        (
            float_input,
            _make_simple_memory_type(
                [2, 4],
                [4, 1],
                space="global",
                element_type=Float16Type(),
            ),
            "global",
            "result-element-type-must-match-input",
        ),
        (
            float_input,
            _make_simple_memory_type(
                [2, 4],
                [4, 1],
                space="shared",
                element_type=Float32Type(),
            ),
            "global",
            "result-space-must-match-input-and-attr",
        ),
        (
            float_input,
            float_result,
            "shared",
            "result-space-must-match-input-and-attr",
        ),
    ]
    for input_type, result_type, space, message in cases:
        inp = _TestOp(result_types=[input_type]).results[0]
        op = NnExpOp(inp, result_type, _make_space(space))
        with pytest.raises(VerifyException, match=message):
            op.verify()


# NN-DIA-047
# 功能说明: 验证 nn.reduce_sum 的 axes/keepdim 与结果 shape 合同。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_reduce_sum_op_shape_contract
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-048
# 功能说明: 验证 nn.reduce_sum 对非法 axes 的拒绝路径。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_reduce_sum_op_rejects_invalid_axes
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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
        with pytest.raises(VerifyException, match="axes-must-be-non-empty-unique-and-in-range"):
            op.verify()


# NN-DIA-049
# 功能说明: 验证 nn.reduce_min 的 keepdim 合同与静态空归约域拒绝。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_reduce_min_op_contract_and_empty_extent_rejection
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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
    with pytest.raises(VerifyException, match="empty-reduction-extent-must-be-rejected-when-static"):
        empty_op.verify()


# NN-DIA-050
# 功能说明: 验证 nn.reduce_max 的 keepdim 合同与静态空归约域拒绝。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_reduce_max_op_contract_and_empty_extent_rejection
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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
    with pytest.raises(VerifyException, match="empty-reduction-extent-must-be-rejected-when-static"):
        empty_op.verify()


# NN-DIA-051
# 功能说明: 验证 nn.reduce_* 的 element_type/space 不一致拒绝路径。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_reduce_ops_reject_type_or_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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
        with pytest.raises(VerifyException, match=message):
            op.verify()


# NN-DIA-052
# 功能说明: 验证 nn.exp 与 nn.reduce_* 在模块文本中 round-trip。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_exp_reduce_module_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-053
# 功能说明: 验证 nn.reduce_* 对非 i1 keepdim attribute 的拒绝路径。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_reduce_ops_reject_non_i1_keepdim_attr
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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
        with pytest.raises(VerifyException, match="keepdim-must-be-i1-bool-attr"):
            op.verify()


# NN-DIA-054
# 功能说明: 验证 nn.reduce_* 对非连续结果 stride 的拒绝路径。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_reduce_ops_reject_non_contiguous_result_stride
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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
        with pytest.raises(VerifyException, match="result-stride-must-be-contiguous-for-result-shape"):
            op.verify()


# NN-DIA-055
# 测试目的: 验证公开 img2col / unary-float / activation verifier 边界。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_nn_public_validation_branches
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-S7-001
# 功能说明: 覆盖 unary float family、activation scalar verifier 与 reduce helper 的剩余边界。
# 测试目的: 锁定 relu/sigmoid/tanh/exp/leaky_relu/hard_sigmoid 的 verifier 主路径，以及 reduce 的公开异常边界不回退。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_unary_float_family_and_reduce_helper_edges
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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
    with pytest.raises(VerifyException, match="alpha must be int or float scalar"):
        NnLeakyReluOp(inp, symbol_value, result_type, _make_space("global")).verify()
    with pytest.raises(VerifyException, match="beta must be int or float scalar"):
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
    with pytest.raises(VerifyException, match="axes-must-be-non-empty-unique-and-in-range"):
        NnReduceSumOp(
            reduce_input,
            reduce_result,
            axes=ArrayAttr([IntegerAttr(1, IntegerType(32))]),
            keepdim=False,
            space=_make_space("global"),
        ).verify()
    with pytest.raises(VerifyException, match="axes-must-be-non-empty-unique-and-in-range"):
        NnReduceSumOp(
            reduce_input,
            reduce_result,
            axes=[1, 1],
            keepdim=False,
            space=_make_space("global"),
        ).verify()
    with pytest.raises(VerifyException, match="keepdim-must-be-i1-bool-attr"):
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


# NN-DIA-S7-002
# 功能说明: 覆盖 nn.memory 维度列表 parser 的当前公开文本范围，以及 mixed scalar add verifier 的剩余错误路径。
# 测试目的: 锁定 dim list 在标识符、整数、`?`、`+`、`-`、`*` 与括号范围内的 parse/print 行为，并补齐 mixed add 在 space/stride/element_type 方向的异常短语。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_memory_dim_parser_and_mixed_add_public_parser_contracts
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-S7-003
# 功能说明: 以公开 op 构造入口验证 mixed scalar 二元 family 的参数化 verifier 合同。
# 测试目的: 锁定 sub/mul/truediv/floordiv 的 memory+scalar、scalar+memory、space、shape、stride 与 dtype 边界。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_mixed_scalar_binary_family_public_contracts
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-S7-004
# 功能说明: 验证 transpose 在动态维度公开合同下使用连续 stride 规则。
# 测试目的: 锁定 result 低维为动态 `?` 时高维 stride 为 `?`、低维 stride 为 1 的合法布局。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_transpose_dynamic_stride_public_contract
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
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


# NN-DIA-S7-005
# 功能说明: 验证 select/cast/activation 的公开 verifier 错误矩阵。
# 测试目的: 锁定公开 op 构造入口对 space、shape、stride、dtype 和标量参数边界的错误语义。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_select_cast_activation_public_error_matrix
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_select_cast_activation_public_error_matrix() -> None:
    cond = _TestOp(
        result_types=[_make_simple_memory_type([2], [1], element_type=i1)]
    ).results[0]
    data_type = _make_simple_memory_type([2], [1], element_type=Float32Type())
    data = _TestOp(result_types=[data_type]).results[0]

    select_cases = [
        (
            data,
            _TestOp(
                result_types=[
                    _make_simple_memory_type([2], [1], space="shared", element_type=Float32Type())
                ]
            ).results[0],
            data_type,
            "global",
            "nn.select operands must use the same space",
        ),
        (
            data,
            data,
            data_type,
            "shared",
            "nn.select attribute space must match operand space",
        ),
        (
            data,
            data,
            _make_simple_memory_type([2], [1], space="shared", element_type=Float32Type()),
            "global",
            "nn.select attribute space must match result space",
        ),
        (
            data,
            _TestOp(
                result_types=[_make_simple_memory_type([3], [1], element_type=Float32Type())]
            ).results[0],
            data_type,
            "global",
            "nn.select shape must match across operands and result",
        ),
        (
            data,
            _TestOp(
                result_types=[_make_simple_memory_type([2], [2], element_type=Float32Type())]
            ).results[0],
            data_type,
            "global",
            "nn.select stride must match across operands and result",
        ),
        (
            data,
            _TestOp(result_types=[_make_simple_memory_type([2], [1], element_type=i32)]).results[0],
            data_type,
            "global",
            "nn.select operand element_type must match",
        ),
        (
            data,
            data,
            _make_simple_memory_type([2], [1], element_type=i32),
            "global",
            "nn.select result element_type must match operand element_type",
        ),
    ]
    for lhs, rhs, result_type, space, message in select_cases:
        with pytest.raises(VerifyException, match=message):
            NnSelectOp(cond, lhs, rhs, result_type, _make_space(space)).verify()

    with pytest.raises(VerifyException, match="nn.cast attribute space must match operand space"):
        NnCastOp(data, data_type, _make_space("shared")).verify()
    with pytest.raises(VerifyException, match="nn.cast attribute space must match result space"):
        NnCastOp(
            data,
            _make_simple_memory_type([2], [1], space="shared", element_type=Float16Type()),
            _make_space("global"),
        ).verify()
    with pytest.raises(VerifyException, match="nn.cast stride must match input"):
        NnCastOp(
            data,
            _make_simple_memory_type([2], [2], element_type=Float16Type()),
            _make_space("global"),
        ).verify()

    wrong_shape = _make_simple_memory_type([3], [1], element_type=Float32Type())
    with pytest.raises(VerifyException, match="result-shape-stride-must-match-input"):
        NnReluOp(data, wrong_shape, _make_space("global")).verify()
    wrong_dtype = _make_simple_memory_type([2], [1], element_type=Float16Type())
    with pytest.raises(VerifyException, match="result-element-type-must-match-input"):
        NnSigmoidOp(data, wrong_dtype, _make_space("global")).verify()
    wrong_space = _make_simple_memory_type([2], [1], space="shared", element_type=Float32Type())
    with pytest.raises(VerifyException, match="result-space-must-match-input-and-attr"):
        NnTanhOp(data, wrong_space, _make_space("global")).verify()
    with pytest.raises(VerifyException, match="result-space-must-match-input-and-attr"):
        NnReluOp(data, data_type, _make_space("shared")).verify()
    with pytest.raises(VerifyException, match="alpha must be int or float scalar"):
        NnLeakyReluOp(data, _TestOp(result_types=[StringAttr("bad")]).results[0], data_type, _make_space("global")).verify()


# NN-DIA-S7-006
# 功能说明: 验证 img2col 的公开 symbol/dynamic 参数与错误矩阵。
# 测试目的: 锁定 symbol.const、动态 shape、symbol 参数、非负 padding 和 result stride 边界。
# 使用示例: pytest -q test/dialect/test_nn.py -k test_img2col_public_symbol_dynamic_error_matrix
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn.py
def test_img2col_public_symbol_dynamic_error_matrix() -> None:
    input_1d = _make_simple_memory_type(
        [1, 2, 8],
        [16, 8, 1],
        element_type=Float32Type(),
    )
    result_1d = _make_simple_memory_type(
        [1, 2, 3, 8],
        [48, 24, 8, 1],
        element_type=Float32Type(),
    )
    input_1d_value = _TestOp(result_types=[input_1d]).results[0]
    three = SymbolConstOp(3).result
    one = SymbolConstOp(1).result
    zero = SymbolConstOp(0).result
    NnImg2col1dOp(input_1d_value, result_1d, three, one, one, one, one, _make_space("global")).verify()
    with pytest.raises(VerifyException, match="kw-sw-dw-must-be-positive"):
        NnImg2col1dOp(input_1d_value, result_1d, zero, one, one, one, one, _make_space("global")).verify()
    with pytest.raises(VerifyException, match="pl-pr-must-be-non-negative"):
        NnImg2col1dOp(
            input_1d_value,
            result_1d,
            three,
            one,
            one,
            arith.ConstantOp(IntegerAttr(-1, i32)).result,
            one,
            _make_space("global"),
        ).verify()

    dynamic_input_1d = _make_simple_memory_type(
        [1, 2, "W"],
        ["2*W", "W", 1],
        element_type=Float32Type(),
    )
    NnImg2col1dOp(
        _TestOp(result_types=[dynamic_input_1d]).results[0],
        result_1d,
        three,
        one,
        one,
        one,
        one,
        _make_space("global"),
    ).verify()
    symbol_param = _TestOp(result_types=[SymbolValueType.from_expr("KW")]).results[0]
    NnImg2col1dOp(
        input_1d_value,
        result_1d,
        symbol_param,
        one,
        one,
        one,
        one,
        _make_space("global"),
    ).verify()
    with pytest.raises(VerifyException, match="result-shape-stride-must-match-img2col1d-contract"):
        NnImg2col1dOp(
            input_1d_value,
            _make_simple_memory_type(
                [1, 2, 3, 8],
                ["S", 24, 8, 1],
                element_type=Float32Type(),
            ),
            three,
            one,
            one,
            one,
            one,
            _make_space("global"),
        ).verify()

    input_2d = _make_simple_memory_type(
        [1, 3, 5, 5],
        [75, 25, 5, 1],
        element_type=Float32Type(),
    )
    result_2d = _make_simple_memory_type(
        [1, 3, 3, 3, 5, 5],
        [675, 225, 75, 25, 5, 1],
        element_type=Float32Type(),
    )
    input_2d_value = _TestOp(result_types=[input_2d]).results[0]
    NnImg2col2dOp(input_2d_value, result_2d, three, three, one, one, one, one, one, one, one, one, _make_space("global")).verify()
    dynamic_input_2d = _make_simple_memory_type(
        [1, 3, "H", 5],
        ["15*H", "5*H", 5, 1],
        element_type=Float32Type(),
    )
    NnImg2col2dOp(
        _TestOp(result_types=[dynamic_input_2d]).results[0],
        result_2d,
        three,
        three,
        one,
        one,
        one,
        one,
        one,
        one,
        one,
        one,
        _make_space("global"),
    ).verify()
    NnImg2col2dOp(
        input_2d_value,
        result_2d,
        symbol_param,
        three,
        one,
        one,
        one,
        one,
        one,
        one,
        one,
        one,
        _make_space("global"),
    ).verify()
    with pytest.raises(VerifyException, match="ph-pw-pl-pr-must-be-non-negative"):
        NnImg2col2dOp(
            input_2d_value,
            result_2d,
            three,
            three,
            one,
            one,
            one,
            one,
            arith.ConstantOp(IntegerAttr(-1, i32)).result,
            one,
            one,
            one,
            _make_space("global"),
        ).verify()
    with pytest.raises(VerifyException, match="result-shape-stride-must-match-img2col2d-contract"):
        NnImg2col2dOp(
            input_2d_value,
            _make_simple_memory_type(
                [1, 3, 3, 3, 5, 5],
                ["S", 225, 75, 25, 5, 1],
                element_type=Float32Type(),
            ),
            three,
            three,
            one,
            one,
            one,
            one,
            one,
            one,
            one,
            one,
            _make_space("global"),
        ).verify()
