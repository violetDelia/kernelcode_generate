"""test operation structured.

功能说明:
- 验证 nn dialect package 拆分后对应 family 的公开行为不变。

使用示例:
- pytest -q test/dialect/nn/test_operation_structured.py

关联文件:
- 功能实现: kernel_gen/dialect/nn/
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/nn/test_operation_structured.py
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


def test_matmul_op_verify_success() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1])
    rhs_type = _make_matrix_type(["K", "N"], [8, 1])
    result_type = _make_matrix_type(["M", "N"], [8, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    op.verify()

def test_matmul_op_shape_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1])
    rhs_type = _make_matrix_type(["Q", "N"], [8, 1])
    result_type = _make_matrix_type(["M", "N"], [8, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(KernelCodeError, match="contracting"):
        op.verify()

def test_matmul_op_result_shape_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1])
    rhs_type = _make_matrix_type(["K", "N"], [8, 1])
    result_type = _make_matrix_type(["M", "K"], [8, 1])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(KernelCodeError, match="result shape"):
        op.verify()

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

def test_matmul_op_space_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1], space="global")
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], space="shared")
    result_type = _make_matrix_type(["M", "N"], [8, 1], space="global")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(KernelCodeError, match="same space"):
        op.verify()

def test_matmul_op_attr_space_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1], space="local")
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], space="local")
    result_type = _make_matrix_type(["M", "N"], [8, 1], space="local")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(KernelCodeError, match="attribute space"):
        op.verify()

def test_matmul_op_result_space_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1], space="global")
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], space="global")
    result_type = _make_matrix_type(["M", "N"], [8, 1], space="shared")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(KernelCodeError, match="result space"):
        op.verify()

def test_matmul_op_rank_mismatch() -> None:
    lhs_type = _make_memory_type("global")
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], space="global")
    result_type = _make_matrix_type(["M", "N"], [8, 1], space="global")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(KernelCodeError, match="rank-2"):
        op.verify()

def test_matmul_op_element_type_mismatch() -> None:
    lhs_type = _make_matrix_type(["M", "K"], [8, 1], element_type=i32)
    rhs_type = _make_matrix_type(["K", "N"], [8, 1], element_type=i32)
    result_type = _make_matrix_type(["M", "N"], [8, 1], element_type=IntegerType(16))
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(KernelCodeError, match="element_type"):
        op.verify()

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
        with pytest.raises(KernelCodeError, match=message):
            case_op.verify()

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
        with pytest.raises(KernelCodeError, match=message):
            case_op.verify()

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
    with pytest.raises(KernelCodeError, match="kw-sw-dw-must-be-positive"):
        NnImg2col1dOp(input_1d_value, result_1d, zero, one, one, one, one, _make_space("global")).verify()
    with pytest.raises(KernelCodeError, match="pl-pr-must-be-non-negative"):
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
    with pytest.raises(KernelCodeError, match="result-shape-stride-must-match-img2col1d-contract"):
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
    with pytest.raises(KernelCodeError, match="ph-pw-pl-pr-must-be-non-negative"):
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
    with pytest.raises(KernelCodeError, match="result-shape-stride-must-match-img2col2d-contract"):
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
