"""nn_lowering private helper regression tests.

创建者: jcc你莫辜负
最后修改人: jcc你莫辜负

功能说明:
- 按实际 diff 直接覆盖 nn_lowering package 的 private helper 合同与边界路径。
- 这些 pytest 只用于 diff 反推自测，不依赖 expectation 资产。

使用示例:
- pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/spec.md
- 测试文件: test/pass/nn_lowering/test_lowering_nn_lowering.py
- 测试文件: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    FunctionType,
    IntAttr,
    IntegerAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    i1,
    i32,
    i64,
)
from xdsl.ir import Block, Region
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

nn_tests = importlib.import_module("test.pass.nn_lowering.test_lowering_nn_lowering")

core_module = importlib.import_module("kernel_gen.passes.lowering.nn_lowering.nn_lowering")
utility_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.nn_lowering_utility"
)
dma_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.dma_structured_lowering"
)
element_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.element_binary_lowering"
)
reduce_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.reduce_softmax_lowering"
)
select_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.select_cast_lowering"
)
matmul_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.matmul_img2col_lowering"
)

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCastOp, DmaFillOp, DmaTransposeOp
from kernel_gen.dialect.kernel import (
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceOp,
    KernelSelectOp,
)
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnCastOp,
    NnEqOp,
    NnExpOp,
    NnGeOp,
    NnGtOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
    NnLeOp,
    NnLtOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnNeOp,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
    NnSelectOp,
    NnSoftmaxOp,
    NnTransposeOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolFloorDivOp,
    SymbolGetDimOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
)
from kernel_gen.passes.lowering.nn_lowering import NnLoweringError

SPACE_GLOBAL = nn_tests.SPACE_GLOBAL
nn_memory_type = nn_tests.nn_memory_type
add_block_arg = nn_tests.add_block_arg


def _op_summary(block: Block) -> list[str]:
    return [op.name for op in block.ops]


@irdl_op_definition
class UnsupportedNnOp(IRDLOperation):
    """测试专用的 nn.unknown 伪 op。"""

    name = "nn.unknown"
    result = result_def(i32)

    def __init__(self) -> None:
        super().__init__(result_types=[i32])


# NN-PH-001
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 nn_lowering_utility 的公开校验入口、错误模型与基础边界。
# 使用示例: pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k test_nn_lowering_utility_helpers
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
def test_nn_lowering_utility_helpers() -> None:
    module = ModuleOp([])
    assert utility_module.ensure_module_op(module) is module
    with pytest.raises(NnLoweringError, match="module must be builtin.module"):
        utility_module.ensure_module_op(object())

    result_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL)
    fake_result = SimpleNamespace(type=result_type)
    fake_op = SimpleNamespace(
        attributes={"space": SPACE_GLOBAL},
        results=[fake_result],
        operands=[object(), object()],
        name="nn.fake",
    )
    assert utility_module.ensure_space_attr(fake_op) is SPACE_GLOBAL
    assert utility_module.ensure_single_result(fake_op) is result_type
    utility_module.ensure_operand_count(fake_op, 2)
    utility_module.ensure_expected_op_name(fake_op, "nn.fake")

    with pytest.raises(NnLoweringError, match="nn op must provide nn.space attribute"):
        utility_module.ensure_space_attr(SimpleNamespace(attributes={}, results=[fake_result], operands=[], name="nn.fake"))
    with pytest.raises(NnLoweringError, match="nn op must have exactly one result"):
        utility_module.ensure_single_result(SimpleNamespace(results=[], operands=[], name="nn.fake"))
    with pytest.raises(NnLoweringError, match="expects 3 operands"):
        utility_module.ensure_operand_count(SimpleNamespace(name="nn.fake", operands=[1, 2]), 3)
    with pytest.raises(NnLoweringError, match="unknown op: nn.other"):
        utility_module.ensure_expected_op_name(SimpleNamespace(name="nn.other"), "nn.fake")


# NN-PH-002
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 core helper 的 shape / stride / symbol / reduce / matmul / materialize 合同。
# 使用示例: pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k test_nn_lowering_core_helpers
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
def test_nn_lowering_core_helpers() -> None:
    core_module._ensure_space_attr(SimpleNamespace(attributes={"space": SPACE_GLOBAL}))
    with pytest.raises(NnLoweringError, match="nn op must define #nn.space attribute"):
        core_module._ensure_space_attr(SimpleNamespace(attributes={}))

    result_type = nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL)
    fake_result = SimpleNamespace(type=result_type)
    fake_op = SimpleNamespace(results=[fake_result], operands=[object(), object()], name="nn.fake")
    assert core_module._ensure_single_result(fake_op) is result_type
    with pytest.raises(NnLoweringError, match="nn op must produce exactly one result"):
        core_module._ensure_single_result(SimpleNamespace(results=[], operands=[], name="nn.fake"))

    core_module._ensure_operand_count(fake_op, 2)
    with pytest.raises(NnLoweringError, match="must have 3 operands"):
        core_module._ensure_operand_count(SimpleNamespace(name="nn.fake", operands=[1, 2]), 3)

    int_attr_op = SimpleNamespace(attributes={"axis": IntegerAttr.from_int_and_width(7, 64)}, name="nn.fake")
    assert core_module._ensure_int_attr(int_attr_op, "axis") == 7
    int_attr_op.attributes["axis"] = IntAttr(3)
    assert core_module._ensure_int_attr(int_attr_op, "axis") == 3
    with pytest.raises(NnLoweringError, match="axis must be integer"):
        core_module._ensure_int_attr(SimpleNamespace(attributes={}, name="nn.fake"), "axis")

    operand_type = nn_memory_type(
        (IntAttr(2), StringAttr("N")),
        (IntAttr(2), StringAttr("S")),
        i32,
        SPACE_GLOBAL,
    )
    result_type = nn_memory_type(
        (IntAttr(2), StringAttr("N")),
        (IntAttr(2), StringAttr("S")),
        i32,
        SPACE_GLOBAL,
    )
    op = SimpleNamespace(name="nn.unary")
    assert core_module._ensure_unary_result_matches_operand(op, operand_type, result_type) == [2, "N"]
    with pytest.raises(NnLoweringError, match="result shape must match operand"):
        core_module._ensure_unary_result_matches_operand(
            op,
            operand_type,
            nn_memory_type((IntAttr(3), StringAttr("N")), (IntAttr(2), StringAttr("S")), i32, SPACE_GLOBAL),
        )
    with pytest.raises(NnLoweringError, match="result stride must match operand"):
        core_module._ensure_unary_result_matches_operand(
            op,
            operand_type,
            nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), StringAttr("T")), i32, SPACE_GLOBAL),
        )
    with pytest.raises(NnLoweringError, match="result element type must match operand"):
        core_module._ensure_unary_result_matches_operand(
            op,
            operand_type,
            nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), StringAttr("S")), i1, SPACE_GLOBAL),
        )
    with pytest.raises(NnLoweringError, match="result space must match operand"):
        core_module._ensure_unary_result_matches_operand(
            op,
            operand_type,
            nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), StringAttr("S")), i32, NnMemorySpaceAttr(StringAttr("shared"))),
        )

    block = Block(arg_types=[operand_type])
    operand = block.args[0]
    unary_op = NnExpOp(operand, result_type, SPACE_GLOBAL)
    block.add_op(unary_op)
    dynamic_shape = core_module._collect_unary_dynamic_shape(block, unary_op, operand, [2, "N"], [2, "N"])
    assert len(dynamic_shape) == 1
    assert isinstance(list(block.ops)[0], SymbolGetDimOp)
    with pytest.raises(NnLoweringError, match="operand shape must match result shape"):
        core_module._collect_unary_dynamic_shape(block, unary_op, operand, [2, 2], [2, "M"])

    symbol_operand = add_block_arg(Block(), SymbolValueType.from_expr("K"))
    assert core_module._ensure_symbol_int(op, symbol_operand) is symbol_operand
    with pytest.raises(NnLoweringError, match="parameters must be symbol.int"):
        core_module._ensure_symbol_int(op, add_block_arg(Block(), i32))

    int_symbol = add_block_arg(Block(), i32)
    assert core_module._ensure_symbol_or_int(op, symbol_operand) is symbol_operand
    assert core_module._ensure_symbol_or_int(op, int_symbol) is int_symbol
    with pytest.raises(NnLoweringError, match="broadcast scalar must be int or symbol"):
        core_module._ensure_symbol_or_int(op, add_block_arg(Block(), nn_memory_type((IntAttr(1),), (IntAttr(1),), i32, SPACE_GLOBAL)))

    assert core_module._normalize_shape_dims([IntAttr(2), IntegerAttr.from_int_and_width(3, 64), StringAttr("N")]) == [2, 3, "N"]
    with pytest.raises(NnLoweringError, match="matmul shape must be IntAttr or StringAttr"):
        core_module._normalize_shape_dims([ArrayAttr([])])

    assert core_module._ensure_reduce_axis("nn.reduce_min", ArrayAttr([IntegerAttr.from_int_and_width(1, 64)])) == 1
    with pytest.raises(NnLoweringError, match="axes must be ArrayAttr"):
        core_module._ensure_reduce_axis("nn.reduce_min", StringAttr("bad"))
    with pytest.raises(NnLoweringError, match="reduce axes must be non-empty"):
        core_module._ensure_reduce_axis("nn.reduce_min", ArrayAttr([]))
    with pytest.raises(NnLoweringError, match="reduce axes must contain exactly one element"):
        core_module._ensure_reduce_axis(
            "nn.reduce_min",
            ArrayAttr([IntegerAttr.from_int_and_width(0, 64), IntegerAttr.from_int_and_width(1, 64)]),
        )
    with pytest.raises(NnLoweringError, match="reduce axis must be integer"):
        core_module._ensure_reduce_axis("nn.reduce_min", ArrayAttr([StringAttr("A")]))

    assert core_module._ensure_reduce_keepdim("nn.reduce_min", IntAttr(1)) is True
    assert core_module._ensure_reduce_keepdim("nn.reduce_min", IntegerAttr.from_int_and_width(0, 64)) is False
    with pytest.raises(NnLoweringError, match="keepdim must be integer"):
        core_module._ensure_reduce_keepdim("nn.reduce_min", StringAttr("bad"))
    with pytest.raises(NnLoweringError, match="keepdim must be 0 or 1"):
        core_module._ensure_reduce_keepdim("nn.reduce_min", IntAttr(2))

    img2col_operand_block = Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(2), IntAttr(2)), (IntAttr(4), IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)])
    img2col_operand = img2col_operand_block.args[0]
    img2col_param_block = Block(
        arg_types=[
            SymbolValueType.from_expr("KW"),
            SymbolValueType.from_expr("SW"),
            SymbolValueType.from_expr("DW"),
            SymbolValueType.from_expr("PL"),
            SymbolValueType.from_expr("PR"),
        ]
    )
    img2col_op = SimpleNamespace(name="nn.img2col1d", operands=[img2col_operand, *img2col_param_block.args])
    resolved_operand, resolved_params = core_module._ensure_img2col_params(img2col_op, 6, 5)
    assert resolved_operand is img2col_operand
    assert all(value.owner is img2col_param_block for value in resolved_params)
    with pytest.raises(NnLoweringError, match="must have 6 operands"):
        core_module._ensure_img2col_params(SimpleNamespace(name="nn.img2col1d", operands=[img2col_operand, *img2col_param_block.args[:-1]]), 6, 5)

    reduce_block = Block(arg_types=[nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)])
    reduce_operand = reduce_block.args[0]
    reduce_op = NnReduceMinOp(
        reduce_operand,
        nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL),
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(1, 64),
        SPACE_GLOBAL,
    )
    reduce_block.add_op(reduce_op)
    assert core_module._collect_reduce_dynamic_shape(
        reduce_block,
        reduce_op,
        reduce_operand,
        [2, "N"],
        [2, "N"],
        1,
        True,
    ) == [list(reduce_block.ops)[0].results[0]]
    with pytest.raises(NnLoweringError, match="reduce axis must be integer"):
        core_module._collect_reduce_dynamic_shape(
            reduce_block,
            reduce_op,
            reduce_operand,
            [2, 3],
            [2, "M"],
            1,
            True,
        )

    lhs_type = nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), i32, SPACE_GLOBAL)
    rhs_type = nn_memory_type((IntAttr(3), IntAttr(4)), (IntAttr(4), IntAttr(1)), i32, SPACE_GLOBAL)
    out_type = nn_memory_type((IntAttr(2), IntAttr(4)), (IntAttr(4), IntAttr(1)), i32, SPACE_GLOBAL)
    core_module._ensure_matmul_shape(lhs_type, rhs_type, out_type)
    with pytest.raises(NnLoweringError, match="requires rank-2 memory types"):
        core_module._ensure_matmul_shape(
            nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL),
            rhs_type,
            out_type,
        )
    with pytest.raises(NnLoweringError, match="contracting dimensions must match"):
        core_module._ensure_matmul_shape(
            lhs_type,
            nn_memory_type((IntAttr(5), IntAttr(4)), (IntAttr(4), IntAttr(1)), i32, SPACE_GLOBAL),
            out_type,
        )
    with pytest.raises(NnLoweringError, match="output shape must match operands"):
        core_module._ensure_matmul_shape(
            lhs_type,
            rhs_type,
            nn_memory_type((IntAttr(2), IntAttr(5)), (IntAttr(5), IntAttr(1)), i32, SPACE_GLOBAL),
        )

    core_module._ensure_matmul_stride(out_type)
    core_module._ensure_matmul_stride(
        nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(4), IntAttr(1)), i32, SPACE_GLOBAL)
    )
    with pytest.raises(NnLoweringError, match="stride must be contiguous"):
        core_module._ensure_matmul_stride(nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL))
    with pytest.raises(NnLoweringError, match="stride must be contiguous"):
        core_module._ensure_matmul_stride(
            nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(5), IntAttr(1)), i32, SPACE_GLOBAL)
        )

    materialize_block = Block()
    materialize_value = add_block_arg(materialize_block, i32)
    filled = core_module._materialize_fill(materialize_block, materialize_value, out_type, SPACE_GLOBAL)
    assert filled.type == out_type
    materialize_ops = list(materialize_block.ops)
    assert isinstance(materialize_ops[0], DmaAllocOp)
    assert isinstance(materialize_ops[1], DmaFillOp)

    mixed_block = Block(arg_types=[nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL), i32])
    lhs = mixed_block.args[0]
    rhs = mixed_block.args[1]
    mixed_op = SimpleNamespace(attributes={"space": SPACE_GLOBAL}, name="nn.add")
    new_lhs, new_rhs = core_module._materialize_fill_for_mixed(mixed_block, mixed_op, lhs, rhs, out_type)
    assert isinstance(new_rhs.type, NnMemoryType)
    assert new_lhs is lhs
    assert isinstance(list(mixed_block.ops)[-1], DmaFillOp)


# NN-PH-003
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 dma_structured lowering helper、surviving pattern 导出和关键错误边界。
# 使用示例: pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k test_dma_structured_lowering_helpers
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
def test_dma_structured_lowering_helpers() -> None:
    block = Block(arg_types=[SymbolValueType.from_expr("M")])
    block_symbol = block.args[0]
    assert dma_module._find_block_symbol_dim(block, "M") is block_symbol
    assert dma_module._find_block_symbol_dim(block, "N") is None

    assert dma_module._ensure_symbol_or_int(SimpleNamespace(), block_symbol) is block_symbol
    assert dma_module._ensure_symbol_or_int(SimpleNamespace(), add_block_arg(Block(), i32)) is not None
    with pytest.raises(NnLoweringError, match="broadcast scalar must be int or symbol"):
        dma_module._ensure_symbol_or_int(SimpleNamespace(), add_block_arg(Block(), nn_memory_type((IntAttr(1),), (IntAttr(1),), i32, SPACE_GLOBAL)))

    operand_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    helper_block = Block(arg_types=[operand_type])
    anchor_op = NnBroadcastOp(helper_block.args[0], result_type, SPACE_GLOBAL)
    helper_block.add_op(anchor_op)
    source_dim = dma_module._get_symbol_dim_from_source(
        helper_block,
        anchor_op,
        1,
        [2, "M"],
        helper_block.args[0],
        [2, "M"],
    )
    assert isinstance(source_dim, object)
    assert len([op for op in helper_block.ops if isinstance(op, SymbolGetDimOp)]) == 1
    with pytest.raises(NnLoweringError, match="result dim is not symbolic"):
        dma_module._get_symbol_dim_from_source(helper_block, anchor_op, 1, [2, 2], helper_block.args[0], [2, "M"])

    result_shape, operand_shape = dma_module._ensure_broadcast_shape(anchor_op, result_type, operand_type)
    assert result_shape == [2, "M"]
    assert operand_shape == [2, "M"]
    with pytest.raises(NnLoweringError, match="result rank must be >= operand rank"):
        dma_module._ensure_broadcast_shape(
            anchor_op,
            nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL),
            operand_type,
        )
    with pytest.raises(NnLoweringError, match="operand shape must not contain '\\?'"):
        dma_module._ensure_broadcast_shape(
            anchor_op,
            nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL),
            nn_memory_type((IntAttr(2), StringAttr("?")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL),
        )

    dma_module._ensure_broadcast_compat([2, "M"], [2, "M"])
    dma_module._ensure_broadcast_compat([1, "N"], [1, "N"])
    with pytest.raises(NnLoweringError, match="invalid broadcast target shape"):
        dma_module._ensure_broadcast_compat([2, 4], [3, 4])
    with pytest.raises(NnLoweringError, match="symbol mismatch"):
        dma_module._ensure_broadcast_compat([2, "M"], [2, "N"])

    assert dma_module.__all__ == ["dma_structured_patterns"]
    assert [type(pattern).__name__ for pattern in dma_module.dma_structured_patterns()] == [
        "_LowerNnBroadcastPattern",
        "_LowerNnTransposePattern",
    ]

    broadcast_block = Block(arg_types=[operand_type])
    broadcast_op = NnBroadcastOp(broadcast_block.args[0], result_type, SPACE_GLOBAL)
    broadcast_block.add_op(broadcast_op)
    dma_module._lower_broadcast(broadcast_block, broadcast_op)
    assert any(isinstance(op, DmaBroadcastOp) for op in broadcast_block.ops)

    transpose_operand = nn_memory_type((IntAttr(2), IntAttr(4)), (IntAttr(4), IntAttr(1)), i32, SPACE_GLOBAL)
    transpose_result = nn_memory_type((IntAttr(4), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    transpose_block = Block(arg_types=[transpose_operand])
    transpose_op = NnTransposeOp(
        transpose_block.args[0],
        transpose_result,
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64), IntegerAttr.from_int_and_width(0, 64)]),
        SPACE_GLOBAL,
    )
    transpose_block.add_op(transpose_op)
    dma_module._lower_transpose(transpose_block, transpose_op)
    assert any(isinstance(op, DmaTransposeOp) for op in transpose_block.ops)


# NN-PH-004
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 element binary lowering helper、mixed 物化路径与 surviving pattern 导出。
# 使用示例: pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k test_element_binary_lowering_helpers
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
def test_element_binary_lowering_helpers() -> None:
    helper_block = Block(arg_types=[nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)])
    source = helper_block.args[0]
    result_type = nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    anchor = NnAddOp(source, source, result_type, SPACE_GLOBAL)
    helper_block.add_op(anchor)

    memory_operand = element_module._select_memory_operand(anchor)
    assert memory_operand is source
    with pytest.raises(NnLoweringError, match="requires at least one nn.memory operand"):
        element_module._select_memory_operand(SimpleNamespace(operands=[], name="nn.fake"))

    ops, dynamic_shape = element_module._build_alloc_dynamic_shape_from_source(source, result_type)
    assert len(ops) == 2
    assert len(dynamic_shape) == 2
    assert all(isinstance(op, SymbolGetDimOp) for op in ops)
    static_ops, static_dynamic = element_module._build_alloc_dynamic_shape_from_source(
        source,
        nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL),
    )
    assert static_ops == []
    assert static_dynamic == []
    with pytest.raises(NnLoweringError, match="operand/result rank mismatch"):
        element_module._build_alloc_dynamic_shape_from_source(
            source,
            nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL),
        )
    with pytest.raises(NnLoweringError, match="must not contain '\\?'"):
        element_module._build_alloc_dynamic_shape_from_source(
            source,
            nn_memory_type((IntAttr(2), StringAttr("?")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL),
        )

    scalar_block = Block(arg_types=[i32])
    scalar = scalar_block.args[0]
    fill_ops, filled = element_module._materialize_element_binary_scalar_operand(scalar, source.type, dynamic_shape)
    assert len(fill_ops) == 2
    assert isinstance(fill_ops[0], DmaAllocOp)
    assert isinstance(fill_ops[1], DmaFillOp)
    assert isinstance(filled.type, NnMemoryType)
    compare_ops, compared = element_module._materialize_compare_scalar_operand(scalar, source.type, dynamic_shape)
    assert len(compare_ops) == 2
    assert isinstance(compare_ops[1], DmaBroadcastOp)
    assert isinstance(compared.type, NnMemoryType)
    with pytest.raises(NnLoweringError, match="scalar type mismatch"):
        element_module._materialize_element_binary_scalar_operand(
            add_block_arg(Block(), Float32Type()),
            source.type,
            dynamic_shape,
        )
    with pytest.raises(NnLoweringError, match="scalar type mismatch"):
        element_module._materialize_compare_scalar_operand(
            add_block_arg(Block(), Float32Type()),
            source.type,
            dynamic_shape,
        )

    symbol_const = SymbolConstOp(3)
    normalize_block = Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)])
    normalize_anchor = NnAddOp(normalize_block.args[0], normalize_block.args[0], result_type, SPACE_GLOBAL)
    normalize_block.add_op(symbol_const)
    normalize_block.add_op(normalize_anchor)
    element_module._normalize_symbol_ops(normalize_block, normalize_anchor)
    assert any(isinstance(op, SymbolConstOp) for op in normalize_block.ops)

    binary_block = Block(arg_types=[source.type, source.type])
    binary_op = NnAddOp(binary_block.args[0], binary_block.args[1], result_type, SPACE_GLOBAL)
    binary_block.add_op(binary_op)
    element_module._lower_element_binary_op(binary_op, binary_block, kind="add", is_compare=False)
    assert any(isinstance(op, KernelBinaryElewiseOp) for op in binary_block.ops)
    assert any(isinstance(op, DmaAllocOp) for op in binary_block.ops)

    mixed_block = Block(arg_types=[source.type, i32])
    mixed_op = NnAddOp(mixed_block.args[0], mixed_block.args[1], result_type, SPACE_GLOBAL)
    mixed_block.add_op(mixed_op)
    element_module._lower_element_binary_op(mixed_op, mixed_block, kind="add", is_compare=False)
    assert any(isinstance(op, DmaFillOp) for op in mixed_block.ops)

    compare_block = Block(arg_types=[i32, source.type])
    compare_op = NnEqOp(compare_block.args[0], compare_block.args[1], nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL), SPACE_GLOBAL)
    compare_block.add_op(compare_op)
    element_module._lower_element_binary_op(compare_op, compare_block, kind="eq", is_compare=True)
    assert any(isinstance(op, DmaBroadcastOp) for op in compare_block.ops)

    with pytest.raises(NnLoweringError, match="at least one nn.memory operand"):
        bad_block = Block(arg_types=[i32, i32])
        bad_op = NnAddOp(bad_block.args[0], bad_block.args[1], result_type, SPACE_GLOBAL)
        bad_block.add_op(bad_op)
        element_module._lower_element_binary_op(bad_op, bad_block, kind="add", is_compare=False)
    assert element_module.__all__ == ["element_binary_patterns"]
    assert [type(pattern).__name__ for pattern in element_module.element_binary_patterns()] == [
        "_LowerNnAddPattern",
        "_LowerNnSubPattern",
        "_LowerNnMulPattern",
        "_LowerNnDivPattern",
        "_LowerNnTrueDivPattern",
        "_LowerNnEqPattern",
        "_LowerNnNePattern",
        "_LowerNnLtPattern",
        "_LowerNnLePattern",
        "_LowerNnGtPattern",
        "_LowerNnGePattern",
    ]


# NN-PH-005
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 reduce/softmax、select/cast、matmul/img2col 的 helper 与 surviving pattern 导出。
# 使用示例: pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k test_reduce_select_cast_matmul_helpers
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
def test_reduce_select_cast_matmul_helpers() -> None:
    reduce_block = Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)])
    reduce_operand = reduce_block.args[0]
    reduce_result = nn_memory_type((IntAttr(2), IntAttr(1)), (IntAttr(1), IntAttr(1)), i32, SPACE_GLOBAL)
    reduce_op = NnReduceMinOp(
        reduce_operand,
        reduce_result,
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntegerAttr.from_int_and_width(1, 64),
        SPACE_GLOBAL,
    )
    reduce_block.add_op(reduce_op)
    assert reduce_module._ensure_int_attr(reduce_op, "keepdim") == 1
    assert reduce_module._ensure_reduce_axis(reduce_op.name, ArrayAttr([IntegerAttr.from_int_and_width(1, 64)])) == 1
    assert reduce_module._ensure_reduce_keepdim(reduce_op.name, IntegerAttr.from_int_and_width(1, 64)) is True
    dynamic_shape = reduce_module._build_alloc_dynamic_shape_from_operand(
        reduce_block,
        reduce_op,
        reduce_operand,
        reduce_result,
        [1, 1],
    )
    assert dynamic_shape == []
    reduce_module._lower_reduce(reduce_block, reduce_op, kind="min")
    assert any(isinstance(op, KernelReduceOp) for op in reduce_block.ops)

    with pytest.raises(NnLoweringError, match="must be integer"):
        reduce_module._ensure_int_attr(SimpleNamespace(attributes={}, name="nn.reduce_min"), "keepdim")
    with pytest.raises(NnLoweringError, match="must be ArrayAttr"):
        reduce_module._ensure_reduce_axis("nn.reduce_min", StringAttr("bad"))
    with pytest.raises(NnLoweringError, match="must be 0 or 1"):
        reduce_module._ensure_reduce_keepdim("nn.reduce_min", IntAttr(2))
    with pytest.raises(NnLoweringError, match="operand must be nn.memory"):
        reduce_module._build_alloc_dynamic_shape_from_operand(
            reduce_block,
            reduce_op,
            add_block_arg(Block(), i32),
            reduce_result,
            [1, 1],
        )

    exp_block = Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)])
    exp_operand = exp_block.args[0]
    exp_result = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)
    exp_op = NnExpOp(exp_operand, exp_result, SPACE_GLOBAL)
    exp_block.add_op(exp_op)
    reduce_module._lower_exp(exp_block, exp_op)
    assert any(isinstance(op, KernelExpOp) for op in exp_block.ops)
    assert reduce_module.__all__ == ["reduce_softmax_patterns"]
    assert [type(pattern).__name__ for pattern in reduce_module.reduce_softmax_patterns()] == [
        "_LowerNnReduceSumPattern",
        "_LowerNnReduceMinPattern",
        "_LowerNnReduceMaxPattern",
        "_RejectNnSoftmaxPattern",
    ]

    select_block = Block(
        arg_types=[
            nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL),
            nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL),
            nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL),
        ]
    )
    cond = select_block.args[0]
    lhs = select_block.args[1]
    rhs = select_block.args[2]
    select_result = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)
    select_op = NnSelectOp(cond, lhs, rhs, select_result, SPACE_GLOBAL)
    select_block.add_op(select_op)
    select_module._lower_select_op(select_op, select_block)
    assert any(isinstance(op, KernelSelectOp) for op in select_block.ops)

    cast_block = Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)])
    cast_op = NnCastOp(cast_block.args[0], nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL), SPACE_GLOBAL)
    cast_block.add_op(cast_op)
    select_module._lower_cast_op(cast_op, cast_block)
    assert any(isinstance(op, DmaCastOp) for op in cast_block.ops)
    with pytest.raises(NnLoweringError, match="element_type must be integer or float and not i1"):
        invalid_cast_block = Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)])
        invalid_cast_op = NnCastOp(
            invalid_cast_block.args[0],
            nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL),
            SPACE_GLOBAL,
        )
        invalid_cast_block.add_op(invalid_cast_op)
        select_module._lower_cast_op(invalid_cast_op, invalid_cast_block)

    exp_select_block = Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)])
    exp_select_op = NnExpOp(exp_select_block.args[0], exp_select_block.args[0].type, SPACE_GLOBAL)
    exp_select_block.add_op(exp_select_op)
    select_module._lower_exp_op(exp_select_op, exp_select_block)
    assert any(isinstance(op, KernelExpOp) for op in exp_select_block.ops)
    assert select_module.__all__ == ["select_cast_patterns"]
    assert [type(pattern).__name__ for pattern in select_module.select_cast_patterns()] == [
        "_LowerSelectPattern",
        "_LowerCastPattern",
        "_LowerExpPattern",
    ]

    matmul_block = Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), Float32Type(), SPACE_GLOBAL), nn_memory_type((IntAttr(3), IntAttr(4)), (IntAttr(4), IntAttr(1)), Float32Type(), SPACE_GLOBAL)])
    matmul_op = NnMatmulOp(matmul_block.args[0], matmul_block.args[1], nn_memory_type((IntAttr(2), IntAttr(4)), (IntAttr(4), IntAttr(1)), Float32Type(), SPACE_GLOBAL), SPACE_GLOBAL)
    matmul_block.add_op(matmul_op)
    matmul_module._lower_matmul(matmul_block, matmul_op)
    assert any(isinstance(op, KernelMatmulOp) for op in matmul_block.ops)

    img1_block = Block(arg_types=[
        nn_memory_type((IntAttr(2), IntAttr(2), IntAttr(2)), (IntAttr(4), IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL),
        SymbolValueType.from_expr("KW"),
        SymbolValueType.from_expr("SW"),
        SymbolValueType.from_expr("DW"),
        SymbolValueType.from_expr("PL"),
        SymbolValueType.from_expr("PR"),
    ])
    img1_op = NnImg2col1dOp(
        img1_block.args[0],
        nn_memory_type((IntAttr(2), IntAttr(2), IntAttr(2)), (IntAttr(4), IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL),
        img1_block.args[1],
        img1_block.args[2],
        img1_block.args[3],
        img1_block.args[4],
        img1_block.args[5],
        SPACE_GLOBAL,
    )
    img1_block.add_op(img1_op)
    matmul_module._lower_img2col1d(img1_block, img1_op)
    assert any(isinstance(op, KernelImg2col1dOp) for op in img1_block.ops)

    img2_block = Block(arg_types=[
        nn_memory_type((IntAttr(2), IntAttr(2), IntAttr(2), IntAttr(2)), (IntAttr(8), IntAttr(4), IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL),
        SymbolValueType.from_expr("KH"),
        SymbolValueType.from_expr("KW"),
        SymbolValueType.from_expr("SH"),
        SymbolValueType.from_expr("SW"),
        SymbolValueType.from_expr("DH"),
        SymbolValueType.from_expr("DW"),
        SymbolValueType.from_expr("PH"),
        SymbolValueType.from_expr("PW"),
        SymbolValueType.from_expr("PL"),
        SymbolValueType.from_expr("PR"),
    ])
    img2_op = NnImg2col2dOp(
        img2_block.args[0],
        nn_memory_type((IntAttr(2), IntAttr(2), IntAttr(2), IntAttr(2)), (IntAttr(8), IntAttr(4), IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL),
        img2_block.args[1],
        img2_block.args[2],
        img2_block.args[3],
        img2_block.args[4],
        img2_block.args[5],
        img2_block.args[6],
        img2_block.args[7],
        img2_block.args[8],
        img2_block.args[9],
        img2_block.args[10],
        SPACE_GLOBAL,
    )
    img2_block.add_op(img2_op)
    matmul_module._lower_img2col2d(img2_block, img2_op)
    assert any(isinstance(op, KernelImg2col2dOp) for op in img2_block.ops)
    assert matmul_module.__all__ == ["matmul_img2col_patterns"]
    assert [type(pattern).__name__ for pattern in matmul_module.matmul_img2col_patterns()] == [
        "_LowerNnMatmulPattern",
        "_LowerNnImg2col1dPattern",
        "_LowerNnImg2col2dPattern",
    ]


# NN-PH-006
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 补齐 nn_lowering core helper 的 mixed/shape/error 分支与 reject pattern。
# 使用示例: pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k core_additional
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
def test_nn_lowering_core_additional_branches() -> None:
    memory_type = nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), i32, SPACE_GLOBAL)
    other_memory_type = nn_memory_type((IntAttr(2), IntAttr(4)), (IntAttr(4), IntAttr(1)), i32, SPACE_GLOBAL)
    symbolic_lhs_type = nn_memory_type((StringAttr("M"), IntAttr(3)), (IntAttr(3), IntAttr(1)), i32, SPACE_GLOBAL)
    symbolic_rhs_type = nn_memory_type((IntAttr(3), StringAttr("N")), (StringAttr("N"), IntAttr(1)), i32, SPACE_GLOBAL)
    symbolic_out_type = nn_memory_type((StringAttr("M"), StringAttr("N")), (StringAttr("N"), IntAttr(1)), i32, SPACE_GLOBAL)

    mixed_block = Block(arg_types=[i32, memory_type])
    mixed_lhs = mixed_block.args[0]
    mixed_rhs = mixed_block.args[1]
    mixed_op = NnAddOp(mixed_lhs, mixed_rhs, memory_type, SPACE_GLOBAL)
    new_lhs, new_rhs = core_module._materialize_fill_for_mixed(mixed_block, mixed_op, mixed_lhs, mixed_rhs, memory_type)
    assert isinstance(new_lhs.type, NnMemoryType)
    assert new_rhs is mixed_rhs
    assert any(isinstance(op, DmaFillOp) for op in mixed_block.ops)

    both_block = Block(arg_types=[memory_type, memory_type])
    both_op = NnAddOp(both_block.args[0], both_block.args[1], memory_type, SPACE_GLOBAL)
    both_block.add_op(both_op)
    core_module._lower_binary(both_block, both_op)
    assert any(isinstance(op, KernelBinaryElewiseOp) for op in both_block.ops)

    rhs_block = Block(arg_types=[i32, memory_type])
    rhs_op = NnAddOp(rhs_block.args[0], rhs_block.args[1], memory_type, SPACE_GLOBAL)
    rhs_block.add_op(rhs_op)
    core_module._lower_binary(rhs_block, rhs_op)
    assert any(isinstance(op, DmaFillOp) for op in rhs_block.ops)

    with pytest.raises(NnLoweringError, match="at least one nn.memory operand"):
        no_memory_block = Block(arg_types=[i32, i32])
        no_memory_op = NnAddOp(no_memory_block.args[0], no_memory_block.args[1], memory_type, SPACE_GLOBAL)
        no_memory_block.add_op(no_memory_op)
        core_module._lower_binary(no_memory_block, no_memory_op)
    with pytest.raises(NnLoweringError, match="same shape"):
        mismatch_block = Block(arg_types=[memory_type, other_memory_type])
        mismatch_op = NnAddOp(mismatch_block.args[0], mismatch_block.args[1], memory_type, SPACE_GLOBAL)
        mismatch_block.add_op(mismatch_op)
        core_module._lower_binary(mismatch_block, mismatch_op)

    reduce_bad_operand_block = Block(arg_types=[i32, i32])
    reduce_bad_operand = reduce_bad_operand_block.args[0]
    reduce_bad_operand_extra = reduce_bad_operand_block.args[1]
    reduce_op = SimpleNamespace(
        name="nn.reduce_min",
        operands=[reduce_bad_operand, reduce_bad_operand_extra],
        results=[SimpleNamespace(type=memory_type)],
        attributes={"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "keepdim": IntAttr(0), "space": SPACE_GLOBAL},
    )
    with pytest.raises(NnLoweringError, match="nn.reduce operand must be nn.memory"):
        core_module._lower_reduce(reduce_bad_operand_block, reduce_op, kind="min")

    reduce_operand_only_block = Block(arg_types=[memory_type])
    reduce_operand_only = reduce_operand_only_block.args[0]
    missing_axes_op = SimpleNamespace(
        name="nn.reduce_min",
        operands=[reduce_operand_only],
        results=[SimpleNamespace(type=memory_type)],
        attributes={"keepdim": IntAttr(0), "space": SPACE_GLOBAL},
    )
    with pytest.raises(NnLoweringError, match="axes must be ArrayAttr"):
        core_module._lower_reduce(reduce_operand_only_block, missing_axes_op, kind="min")
    missing_keepdim_op = SimpleNamespace(
        name="nn.reduce_min",
        operands=[reduce_operand_only],
        results=[SimpleNamespace(type=memory_type)],
        attributes={"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "space": SPACE_GLOBAL},
    )
    with pytest.raises(NnLoweringError, match="keepdim must be bool"):
        core_module._lower_reduce(reduce_operand_only_block, missing_keepdim_op, kind="min")
    bad_rank_op = SimpleNamespace(
        name="nn.reduce_min",
        operands=[reduce_operand_only],
        results=[SimpleNamespace(type=nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), i32, SPACE_GLOBAL))],
        attributes={"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "keepdim": IntAttr(0), "space": SPACE_GLOBAL},
    )
    with pytest.raises(NnLoweringError, match="reduce shape rank must match"):
        core_module._lower_reduce(reduce_operand_only_block, bad_rank_op, kind="min")

    matmul_block = Block(
        arg_types=[
            symbolic_lhs_type,
            symbolic_rhs_type,
        ]
    )
    matmul_op = NnMatmulOp(matmul_block.args[0], matmul_block.args[1], symbolic_out_type, SPACE_GLOBAL)
    matmul_block.add_op(matmul_op)
    core_module._lower_matmul(matmul_block, matmul_op)
    assert any(isinstance(op, SymbolGetDimOp) for op in matmul_block.ops)
    assert any(isinstance(op, KernelMatmulOp) for op in matmul_block.ops)

    with pytest.raises(NnLoweringError, match="nn.matmul operands must be nn.memory"):
        bad_matmul_op = NnMatmulOp(add_block_arg(Block(), i32), add_block_arg(Block(), i32), symbolic_out_type, SPACE_GLOBAL)
        core_module._lower_matmul(Block(), bad_matmul_op)
    with pytest.raises(NnLoweringError, match="matmul output shape must match operands"):
        mismatch_matmul_op = NnMatmulOp(
            add_block_arg(Block(), symbolic_lhs_type),
            add_block_arg(Block(), symbolic_rhs_type),
            nn_memory_type((StringAttr("X"), StringAttr("N")), (StringAttr("N"), IntAttr(1)), i32, SPACE_GLOBAL),
            SPACE_GLOBAL,
        )
        core_module._lower_matmul(Block(), mismatch_matmul_op)

    pattern = core_module._RejectUnsupportedNnOpPattern()
    rewriter = SimpleNamespace(has_done_action=False)
    assert pattern.match_and_rewrite(SimpleNamespace(name="foo"), rewriter) is None
    with pytest.raises(NnLoweringError, match="unknown op: nn.unknown"):
        pattern.match_and_rewrite(UnsupportedNnOp(), rewriter)


# NN-PH-007
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 补齐 dma_structured lowering helper、broadcast/transpose 误差与 pattern 分支。
# 使用示例: pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k dma_structured_additional
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
def test_dma_structured_lowering_additional_branches() -> None:
    operand_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    source_operand = Block(arg_types=[operand_type]).args[0]

    assert dma_module._ensure_symbol_or_int(SimpleNamespace(), SymbolConstOp(3)) is not None
    assert dma_module._ensure_symbol_or_int(SimpleNamespace(), add_block_arg(Block(), i32)) is not None
    with pytest.raises(NnLoweringError, match="broadcast scalar must be int or symbol"):
        dma_module._ensure_symbol_or_int(SimpleNamespace(), add_block_arg(Block(), nn_memory_type((IntAttr(1),), (IntAttr(1),), i32, SPACE_GLOBAL)))

    axis_block = Block(arg_types=[operand_type])
    axis_op = NnBroadcastOp(axis_block.args[0], result_type, SPACE_GLOBAL)
    axis_block.add_op(axis_op)
    axis_source = dma_module._get_symbol_dim_from_source(axis_block, axis_op, 1, [2, "M"], axis_block.args[0], [2, "M"])
    assert axis_source is not None
    axis_out_block = Block(arg_types=[SymbolValueType.from_expr("M"), nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL)])
    axis_out_op = SimpleNamespace(name="nn.broadcast")
    assert dma_module._get_symbol_dim_from_source(axis_out_block, axis_out_op, 0, ["M", 2], axis_out_block.args[1], [2]) is axis_out_block.args[0]
    with pytest.raises(NnLoweringError, match="axis out of range"):
        dma_module._get_symbol_dim_from_source(Block(arg_types=[nn_memory_type((IntAttr(2),), (IntAttr(1),), i32, SPACE_GLOBAL)]), axis_out_op, 0, ["M", 2], source_operand, [2])
    with pytest.raises(NnLoweringError, match="source dim is not symbolic"):
        dma_module._get_symbol_dim_from_source(axis_block, axis_op, 1, [2, "M"], Block(arg_types=[nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(3), IntAttr(1)), i32, SPACE_GLOBAL)]).args[0], [2, 3])
    with pytest.raises(NnLoweringError, match="symbol mismatch"):
        dma_module._get_symbol_dim_from_source(
            axis_block,
            axis_op,
            1,
            [2, "M"],
            Block(arg_types=[nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)]).args[0],
            [2, "N"],
        )


# NN-PH-008
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 补齐 select/cast/exp 与 reduce/softmax lowering helper 的错误短路与 pattern 分支。
# 使用示例: pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k select_reduce_additional
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/test_nn_lowering_private_helpers.py
def test_select_reduce_softmax_additional_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    source_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)
    result_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)

    with pytest.raises(NnLoweringError, match="dynamic_shape source must be nn.memory"):
        select_module._build_alloc_dynamic_shape_from_source(add_block_arg(Block(), i32), result_type)
    static_source = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)
    static_result_type = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)
    assert select_module._build_alloc_dynamic_shape_from_source(Block(arg_types=[static_source]).args[0], static_result_type)[0] == []
    with pytest.raises(NnLoweringError, match="rank mismatch"):
        select_module._build_alloc_dynamic_shape_from_source(Block(arg_types=[source_type]).args[0], nn_memory_type((IntAttr(2),), (IntAttr(1),), Float32Type(), SPACE_GLOBAL))
    with pytest.raises(NnLoweringError, match="must not contain '\\?'"):
        select_module._build_alloc_dynamic_shape_from_source(Block(arg_types=[source_type]).args[0], nn_memory_type((IntAttr(2), StringAttr("?")), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL))

    cond_type = nn_memory_type((IntAttr(2), StringAttr("M")), (IntAttr(2), IntAttr(1)), i1, SPACE_GLOBAL)
    select_block = Block(arg_types=[cond_type, source_type, source_type])
    select_op = NnSelectOp(select_block.args[0], select_block.args[1], select_block.args[2], result_type, SPACE_GLOBAL)
    select_block.add_op(select_op)
    select_module._lower_select_op(select_op, select_block)
    assert any(isinstance(op, KernelSelectOp) for op in select_block.ops)

    with pytest.raises(NnLoweringError, match="cond must be nn.memory"):
        select_module._lower_select_op(
            NnSelectOp(add_block_arg(Block(), i32), add_block_arg(Block(), source_type), add_block_arg(Block(), source_type), result_type, SPACE_GLOBAL),
            Block(),
        )
    with pytest.raises(NnLoweringError, match="lhs must be nn.memory"):
        select_module._lower_select_op(
            NnSelectOp(add_block_arg(Block(), source_type), add_block_arg(Block(), i32), add_block_arg(Block(), source_type), result_type, SPACE_GLOBAL),
            Block(),
        )
    with pytest.raises(NnLoweringError, match="rhs must be nn.memory"):
        select_module._lower_select_op(
            NnSelectOp(add_block_arg(Block(), source_type), add_block_arg(Block(), source_type), add_block_arg(Block(), i32), result_type, SPACE_GLOBAL),
            Block(),
        )

    monkeypatch.setattr(KernelSelectOp, "verify", lambda self: (_ for _ in ()).throw(VerifyException("boom")))
    with pytest.raises(NnLoweringError, match="boom"):
        select_block_error = Block(arg_types=[cond_type, source_type, source_type])
        select_error_op = NnSelectOp(select_block_error.args[0], select_block_error.args[1], select_block_error.args[2], result_type, SPACE_GLOBAL)
        select_block_error.add_op(select_error_op)
        select_module._lower_select_op(select_error_op, select_block_error)

    cast_source = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
    cast_result = nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)
    with pytest.raises(NnLoweringError, match="dynamic_shape source must be nn.memory"):
        select_module._build_alloc_dynamic_shape_from_source(add_block_arg(Block(), i32), cast_result)
    assert select_module._build_alloc_dynamic_shape_from_source(Block(arg_types=[cast_source]).args[0], cast_result)[0] == []
    with pytest.raises(NnLoweringError, match="result shape must not contain '\\?'"):
        select_module._build_alloc_dynamic_shape_from_source(Block(arg_types=[cast_source]).args[0], nn_memory_type((IntAttr(2), StringAttr("?")), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL))

    cast_block = Block(arg_types=[cast_source])
    cast_op = NnCastOp(cast_block.args[0], cast_result, SPACE_GLOBAL)
    cast_block.add_op(cast_op)
    select_module._lower_cast_op(cast_op, cast_block)
    assert any(isinstance(op, DmaCastOp) for op in cast_block.ops)

    cast_optional = SimpleNamespace(
        name="nn.cast",
        operands=[add_block_arg(Block(), i32), SymbolConstOp(3)],
        results=[SimpleNamespace(type=cast_result)],
        attributes={"space": SPACE_GLOBAL},
    )
    with pytest.raises(NnLoweringError, match="input must be nn.memory"):
        select_module._lower_cast_op(cast_optional, Block())
    cast_invalid_optional = SimpleNamespace(
        name="nn.cast",
        operands=[add_block_arg(Block(), i32), add_block_arg(Block(), cast_source)],
        results=[SimpleNamespace(type=cast_result)],
        attributes={"space": SPACE_GLOBAL},
    )
    with pytest.raises(NnLoweringError, match="optional operand must be int or symbol"):
        select_module._lower_cast_op(cast_invalid_optional, Block())

    monkeypatch.setattr(DmaCastOp, "verify_", lambda self: (_ for _ in ()).throw(VerifyException("boom")))
    with pytest.raises(NnLoweringError, match="boom"):
        cast_verify_block = Block(arg_types=[cast_source])
        cast_verify_op = NnCastOp(cast_verify_block.args[0], cast_result, SPACE_GLOBAL)
        cast_verify_block.add_op(cast_verify_op)
        select_module._lower_cast_op(cast_verify_op, cast_verify_block)

    exp_block = Block(arg_types=[source_type])
    exp_op = NnExpOp(exp_block.args[0], result_type, SPACE_GLOBAL)
    exp_block.add_op(exp_op)
    select_module._lower_exp_op(exp_op, exp_block)
    assert any(isinstance(op, KernelExpOp) for op in exp_block.ops)
    with pytest.raises(NnLoweringError, match="operand must be nn.memory"):
        select_module._lower_exp_op(NnExpOp(add_block_arg(Block(), i32), result_type, SPACE_GLOBAL), Block())
    with pytest.raises(NnLoweringError, match="result shape must match operand"):
        select_module._lower_exp_op(
            NnExpOp(exp_block.args[0], nn_memory_type((IntAttr(2), IntAttr(3)), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL), SPACE_GLOBAL),
            Block(),
        )
    monkeypatch.setattr(DmaAllocOp, "verify", lambda self: (_ for _ in ()).throw(VerifyException("boom")))
    with pytest.raises(NnLoweringError, match="boom"):
        exp_verify_block = Block(arg_types=[source_type])
        exp_verify_op = NnExpOp(exp_verify_block.args[0], result_type, SPACE_GLOBAL)
        exp_verify_block.add_op(exp_verify_op)
        select_module._lower_exp_op(exp_verify_op, exp_verify_block)

    select_pattern = select_module._LowerSelectPattern()
    cast_pattern = select_module._LowerCastPattern()
    exp_pattern = select_module._LowerExpPattern()
    with pytest.raises(NnLoweringError, match="nn op must be inside a block"):
        select_pattern.match_and_rewrite(NnSelectOp(add_block_arg(Block(), source_type), add_block_arg(Block(), source_type), add_block_arg(Block(), source_type), result_type, SPACE_GLOBAL), SimpleNamespace(has_done_action=False))
    with pytest.raises(NnLoweringError, match="nn op must be inside a block"):
        cast_pattern.match_and_rewrite(NnCastOp(add_block_arg(Block(), cast_source), cast_result, SPACE_GLOBAL), SimpleNamespace(has_done_action=False))
    with pytest.raises(NnLoweringError, match="nn op must be inside a block"):
        exp_pattern.match_and_rewrite(NnExpOp(add_block_arg(Block(), source_type), result_type, SPACE_GLOBAL), SimpleNamespace(has_done_action=False))

    reduce_source = nn_memory_type((IntAttr(2), StringAttr("N")), (IntAttr(2), IntAttr(1)), Float32Type(), SPACE_GLOBAL)
    reduce_result = nn_memory_type((IntAttr(2),), (IntAttr(1),), Float32Type(), SPACE_GLOBAL)
    static_reduce_operand = Block(arg_types=[reduce_source]).args[0]
    reduce_operand_only = Block(arg_types=[reduce_source]).args[0]
    assert reduce_module._build_alloc_dynamic_shape_from_operand(Block(), SimpleNamespace(name="nn.reduce_min"), static_reduce_operand, reduce_result, [0]) == []
    with pytest.raises(NnLoweringError, match="operand must be nn.memory"):
        reduce_module._build_alloc_dynamic_shape_from_operand(Block(), SimpleNamespace(name="nn.reduce_min"), add_block_arg(Block(), i32), reduce_result, [0])

    reduce_block = Block(arg_types=[i32, reduce_source])
    reduce_op = NnReduceMinOp(reduce_block.args[0], reduce_result, [1], 0, SPACE_GLOBAL)
    reduce_block.add_op(reduce_op)
    with pytest.raises(NnLoweringError, match="operand must be nn.memory"):
        reduce_module._lower_reduce(reduce_block, reduce_op, kind="min")
    missing_axes_op = SimpleNamespace(
        name="nn.reduce_min",
        operands=[reduce_operand_only],
        results=[SimpleNamespace(type=reduce_result)],
        attributes={"keepdim": IntAttr(0), "space": SPACE_GLOBAL},
    )
    with pytest.raises(NnLoweringError, match="axes must be ArrayAttr"):
        reduce_module._lower_reduce(Block(arg_types=[reduce_source]), missing_axes_op, kind="min")
    missing_keepdim_op = SimpleNamespace(
        name="nn.reduce_min",
        operands=[reduce_operand_only],
        results=[SimpleNamespace(type=reduce_result)],
        attributes={"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "space": SPACE_GLOBAL},
    )
    with pytest.raises(NnLoweringError, match="keepdim must be bool"):
        reduce_module._lower_reduce(Block(arg_types=[reduce_source]), missing_keepdim_op, kind="min")
    rank_mismatch_block = Block(arg_types=[reduce_source])
    rank_mismatch_result = nn_memory_type(
        (IntAttr(2), IntAttr(2)),
        (IntAttr(2), IntAttr(1)),
        Float32Type(),
        SPACE_GLOBAL,
    )
    rank_mismatch_op = NnReduceMinOp(
        rank_mismatch_block.args[0],
        rank_mismatch_result,
        ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]),
        IntAttr(0),
        SPACE_GLOBAL,
    )
    rank_mismatch_block.add_op(rank_mismatch_op)
    with pytest.raises(NnLoweringError, match="reduce shape rank must match"):
        reduce_module._lower_reduce(rank_mismatch_block, rank_mismatch_op, kind="min")

    reduce_pattern = reduce_module._LowerNnReduceSumPattern()
    reduce_min_pattern = reduce_module._LowerNnReduceMinPattern()
    reduce_max_pattern = reduce_module._LowerNnReduceMaxPattern()
    softmax_pattern = reduce_module._RejectNnSoftmaxPattern()
    with pytest.raises(NnLoweringError, match="nn op must be inside a block"):
        reduce_pattern.match_and_rewrite(NnReduceSumOp(add_block_arg(Block(), reduce_source), reduce_result, ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), IntAttr(0), SPACE_GLOBAL), SimpleNamespace(has_done_action=False))
    with pytest.raises(NnLoweringError, match="nn op must be inside a block"):
        reduce_min_pattern.match_and_rewrite(NnReduceMinOp(add_block_arg(Block(), reduce_source), reduce_result, ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), IntAttr(0), SPACE_GLOBAL), SimpleNamespace(has_done_action=False))
    with pytest.raises(NnLoweringError, match="nn op must be inside a block"):
        reduce_max_pattern.match_and_rewrite(NnReduceMaxOp(add_block_arg(Block(), reduce_source), reduce_result, ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), IntAttr(0), SPACE_GLOBAL), SimpleNamespace(has_done_action=False))
    with pytest.raises(NnLoweringError, match="nn.softmax must be decomposed before lower-nn"):
        softmax_pattern.match_and_rewrite(NnSoftmaxOp(add_block_arg(Block(), reduce_source), reduce_result, IntAttr(0), SPACE_GLOBAL), SimpleNamespace(has_done_action=False))
    with pytest.raises(NnLoweringError, match="result must be nn.memory"):
        dma_module._ensure_broadcast_shape(SimpleNamespace(name="nn.broadcast"), object(), source_type)
    with pytest.raises(NnLoweringError, match="operand must be nn.memory"):
        dma_module._ensure_broadcast_shape(SimpleNamespace(name="nn.broadcast"), result_type, object())
    with pytest.raises(NnLoweringError, match="result dim not in source"):
        dma_module._ensure_broadcast_compat([1, "M"], [1, 2])
    with pytest.raises(NnLoweringError, match="result dim not in source"):
        dma_module._ensure_broadcast_compat([2, "M"], [2, 2])

    source_operand = Block(arg_types=[source_type]).args[0]
    with pytest.raises(NnLoweringError, match="must have 1 operands"):
        dma_module._lower_broadcast(SimpleNamespace(), SimpleNamespace(name="nn.broadcast", operands=[], results=[SimpleNamespace(type=result_type)], attributes={"space": SPACE_GLOBAL}))
    with pytest.raises(NnLoweringError, match="operand must be nn.memory"):
        bad_broadcast = NnBroadcastOp(add_block_arg(Block(), i32), result_type, SPACE_GLOBAL)
        dma_module._lower_broadcast(Block(), bad_broadcast)
    with pytest.raises(NnLoweringError, match="perm must be ArrayAttr"):
        bad_transpose = SimpleNamespace(
            name="nn.transpose",
            operands=[add_block_arg(Block(), source_type)],
            results=[SimpleNamespace(type=result_type)],
            attributes={"perm": [0, 1], "space": SPACE_GLOBAL},
        )
        dma_module._lower_transpose(Block(), bad_transpose)
    with pytest.raises(NnLoweringError, match="perm rank mismatch"):
        bad_transpose_block = Block(arg_types=[source_type])
        bad_transpose = NnTransposeOp(
            bad_transpose_block.args[0],
            result_type,
            ArrayAttr([IntegerAttr.from_int_and_width(0, 64)]),
            SPACE_GLOBAL,
        )
        bad_transpose_block.add_op(bad_transpose)
        dma_module._lower_transpose(bad_transpose_block, bad_transpose)
    with pytest.raises(NnLoweringError, match="operand shape must not contain '\\?'"):
        bad_operand = nn_memory_type((IntAttr(2), StringAttr("?")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
        bad_transpose_block = Block(arg_types=[bad_operand])
        bad_transpose = NnTransposeOp(
            bad_transpose_block.args[0],
            result_type,
            ArrayAttr([IntegerAttr.from_int_and_width(0, 64), IntegerAttr.from_int_and_width(1, 64)]),
            SPACE_GLOBAL,
        )
        bad_transpose_block.add_op(bad_transpose)
        dma_module._lower_transpose(bad_transpose_block, bad_transpose)
    with pytest.raises(NnLoweringError, match="result dim not in source"):
        result_not_in_source = nn_memory_type((StringAttr("X"), StringAttr("M")), (IntAttr(2), IntAttr(1)), i32, SPACE_GLOBAL)
        bad_transpose_block = Block(arg_types=[source_type])
        bad_transpose = NnTransposeOp(
            bad_transpose_block.args[0],
            result_not_in_source,
            ArrayAttr([IntegerAttr.from_int_and_width(0, 64), IntegerAttr.from_int_and_width(1, 64)]),
            SPACE_GLOBAL,
        )
        bad_transpose_block.add_op(bad_transpose)
        dma_module._lower_transpose(bad_transpose_block, bad_transpose)

    broadcast_pattern = dma_module._LowerNnBroadcastPattern()
    transpose_pattern = dma_module._LowerNnTransposePattern()
    with pytest.raises(NnLoweringError, match="nn op must be inside a block"):
        broadcast_pattern.match_and_rewrite(NnBroadcastOp(source_operand, result_type, SPACE_GLOBAL), SimpleNamespace(has_done_action=False))
    with pytest.raises(NnLoweringError, match="nn op must be inside a block"):
        transpose_pattern.match_and_rewrite(
            NnTransposeOp(
                source_operand,
                result_type,
                ArrayAttr([IntegerAttr.from_int_and_width(0, 64), IntegerAttr.from_int_and_width(1, 64)]),
                SPACE_GLOBAL,
            ),
            SimpleNamespace(has_done_action=False),
        )
