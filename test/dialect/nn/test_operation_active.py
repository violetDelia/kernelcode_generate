"""test operation active.

功能说明:
- 验证 nn dialect package 拆分后对应 family 的公开行为不变。

使用示例:
- pytest -q test/dialect/nn/test_operation_active.py

关联文件:
- 功能实现: kernel_gen/dialect/nn/
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/nn/test_operation_active.py
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
