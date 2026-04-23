"""tile lowering canonical helper tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 直接覆盖 `kernel_gen.tile.common` 的 plan / rewrite / analysis 清理 helper。
- 锁定 tile pass 的非法输入、no-op、symbol/view 与 analysis 角色边界。
- 这些测试只依赖本地 pytest，不依赖 expectation 旧合同路径。

使用示例:
- pytest -q test/pass/test_lowering_tile_private_helpers.py

关联文件:
- 功能实现: [kernel_gen/tile/common.py](kernel_gen/tile/common.py)
- Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- 测试文件: [test/pass/test_lowering_tile_private_helpers.py](test/pass/test_lowering_tile_private_helpers.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, UnregisteredOp, i1, i32
from xdsl.ir import Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

tile_analysis_helpers = importlib.import_module("test.pass.test_lowering_tile_analysis")
tile_analysis_module = importlib.import_module("kernel_gen.tile.analysis")
tile_module = importlib.import_module("kernel_gen.tile.common")

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaFillOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType, NnReluOp
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolForOp, SymbolGetDimOp, SymbolIterType, SymbolValueType
from kernel_gen.dialect.tuner import TunerParamOp

TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TilePassError = tile_module.TilePassError


def _make_memory_type(
    shape_dims: list[object],
    element_type: object = i32,
    *,
    space: str = "global",
) -> NnMemoryType:
    """构造 tile private helper 测试用 nn.memory 类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持测试中按需构造 `i32` / `i1` / 符号维度混合的 memory 类型。
    - 通过显式 stride 维持与现有 helper 测试一致的最小布局表达。

    使用示例:
    - mem_type = _make_memory_type([StringAttr("M"), IntAttr(1)])

    关联文件:
    - 功能实现: [kernel_gen/tile/common.py](kernel_gen/tile/common.py)
    - Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - 测试文件: [test/pass/test_lowering_tile_private_helpers.py](test/pass/test_lowering_tile_private_helpers.py)
    """

    shape = ArrayAttr(shape_dims)
    stride = ArrayAttr([StringAttr(f"S{axis}") for axis in range(len(shape_dims))])
    return NnMemoryType(shape, stride, element_type, NnMemorySpaceAttr.from_name(space))


def _make_func_op(
    name: str,
    arg_types: list[object],
    result_types: list[object],
    body_ops: list[Operation],
) -> func.FuncOp:
    """构造最小 func.func 测试载体。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于直接驱动 tile pass 的输入合同、plan 与 rewrite helper。
    - 保持函数体只包含测试用最小 op 序列，避免引入额外 IR 噪声。

    使用示例:
    - func_op = _make_func_op("tile_helper", [mem_type], [], [func.ReturnOp()])

    关联文件:
    - 功能实现: [kernel_gen/tile/common.py](kernel_gen/tile/common.py)
    - Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - 测试文件: [test/pass/test_lowering_tile_private_helpers.py](test/pass/test_lowering_tile_private_helpers.py)
    """

    block = Block(arg_types=arg_types)
    block.add_ops(body_ops)
    return func.FuncOp(name, FunctionType.from_lists(arg_types, result_types), Region(block))


def _run_tile_analysis(module: ModuleOp) -> ModuleOp:
    """对测试模块执行 tile-analysis pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 tile helper 测试提供显式 analysis 标注。
    - 不引入 tile-elewise / tile-reduce 的后续改写，保持输入最小化。

    使用示例:
    - module = _run_tile_analysis(module)

    关联文件:
    - 功能实现: [kernel_gen/tile/analysis.py](kernel_gen/tile/analysis.py)
    - Spec 文档: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - 测试文件: [test/pass/test_lowering_tile_private_helpers.py](test/pass/test_lowering_tile_private_helpers.py)
    """

    TileAnalysisPass().apply(Context(), module)
    return module


# TC-TILE-PRIVATE-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper 里的输入合同、kernel 分类与 compare 兼容路径会按当前真实语义返回或失败。
# 使用示例: pytest -q test/pass/test_lowering_tile_private_helpers.py -k test_tile_private_helpers_cover_contract_and_classification_surface
# 对应功能实现文件路径: kernel_gen/tile/common.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile_private_helpers.py
def test_tile_private_helpers_cover_contract_and_classification_surface() -> None:
    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    bool_type = _make_memory_type([StringAttr("M")], i1)
    bool_block = Block(arg_types=[bool_type])
    block = Block(arg_types=[mem_type, mem_type, bool_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    kernel_op = KernelBinaryElewiseOp(block.args[3], block.args[0], block.args[1], kind="add", space=space)
    matmul_op = KernelMatmulOp(block.args[3], block.args[0], block.args[1], space)
    broadcast_op = DmaBroadcastOp(block.args[0], block.args[1])
    tuner_op = TunerParamOp(SymbolValueType.from_expr("TILE_M"))
    dim_op = SymbolGetDimOp(block.args[0], 0)
    call_op = func.CallOp("callee", [], [])
    return_op = func.ReturnOp()
    custom_op = UnregisteredOp.with_name("custom.op").create(operands=[], result_types=[])
    old_compare = KernelBinaryElewiseOp(block.args[3], block.args[0], block.args[2], kind="eq", space=space)
    old_compare.attributes["tile.analysis"] = tile_module._tile_analysis_attr([["elewise"], ["elewise"], ["elewise"]])
    old_compare.attributes["tile.tile_exprs"] = ArrayAttr([ArrayAttr([StringAttr("expr")])])
    bool_compare = KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind="eq", space=space)
    bool_compare.attributes["tile.analysis"] = tile_module._tile_analysis_attr([["elewise"], ["elewise"], ["elewise"]])
    bool_compare.attributes["tile.tile_exprs"] = ArrayAttr([ArrayAttr([StringAttr("expr")])])

    nn_relu = NnReluOp(block.args[0], mem_type, space)

    block.add_ops([kernel_op, matmul_op, broadcast_op, tuner_op, dim_op, call_op, return_op, custom_op, old_compare, bool_compare])

    assert tile_module._collect_kernel_ops(block) == [kernel_op, matmul_op, old_compare, bool_compare]
    assert tile_module._is_allowed_input_contract_op(kernel_op)
    assert tile_module._is_allowed_input_contract_op(matmul_op)
    assert tile_module._is_allowed_input_contract_op(broadcast_op)
    assert tile_module._is_allowed_input_contract_op(return_op)
    assert tile_module._is_allowed_input_contract_op(tuner_op)
    assert tile_module._is_allowed_input_contract_op(dim_op)
    assert not tile_module._is_allowed_input_contract_op(custom_op)

    assert tile_module._tile_op_kind(broadcast_op) == "broadcast"
    assert tile_module._tile_op_kind(matmul_op) == "matmul"
    assert tile_module._tile_op_kind(kernel_op) == "elementwise"
    assert tile_module._is_bool_memory(bool_block.args[0])
    assert not tile_module._is_bool_memory(block.args[0])
    with pytest.raises(TilePassError, match="reduce kernel op is not supported"):
        tile_module._tile_op_kind(SimpleNamespace(name="kernel.reduce_sum"))
    with pytest.raises(TilePassError, match="unsupported tile op custom.op"):
        tile_module._tile_op_kind(SimpleNamespace(name="custom.op"))

    assert tile_module._symbol_expr_from_value(SymbolConstOp(7).result) == "7"
    with pytest.raises(TilePassError, match="symbol value type must be !symbol.int"):
        tile_module._symbol_expr_from_value(block.args[0])

    tile_module._normalize_binary_elewise_compare_compat(block)
    remaining_compare_ops = [op for op in block.ops if getattr(op, "name", None) == "kernel.binary_elewise" and getattr(op.kind, "data", None) == "eq"]
    assert len(remaining_compare_ops) == 2
    assert remaining_compare_ops[0].operands[0] == block.args[2]
    assert remaining_compare_ops[0].operands[1] == block.args[3]
    assert remaining_compare_ops[0].operands[2] == block.args[0]
    assert remaining_compare_ops[0].attributes["tile.analysis"] == tile_module._tile_analysis_attr([["elewise"], ["elewise"], ["elewise"]])
    assert remaining_compare_ops[0].attributes["tile.tile_exprs"] == ArrayAttr([ArrayAttr([StringAttr("expr")])])
    assert remaining_compare_ops[1].operands[0] == block.args[2]
    assert remaining_compare_ops[1].operands[1] == block.args[0]
    assert remaining_compare_ops[1].operands[2] == block.args[1]


# TC-TILE-PRIVATE-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper 的输入合同与中间值物化校验会对 memory-return、func.call、nn 残留和 carry memory 进行 fail-fast。
# 使用示例: pytest -q test/pass/test_lowering_tile_private_helpers.py -k test_tile_private_helpers_validate_input_contract_and_materialization
# 对应功能实现文件路径: kernel_gen/tile/common.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile_private_helpers.py
def test_tile_private_helpers_validate_input_contract_rejects_memory_return() -> None:
    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    func_op = _make_func_op("tile_returns_memory", [mem_type], [mem_type], [func.ReturnOp()])

    with pytest.raises(TilePassError, match="still returns nn.memory results"):
        tile_module._validate_input_contract(func_op, func_op.body.block)


def test_tile_private_helpers_validate_input_contract_rejects_nn_relu() -> None:
    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    func_op = _make_func_op("tile_contains_nn", [mem_type], [], [])
    block = func_op.body.block
    block.add_ops([NnReluOp(block.args[0], mem_type, NnMemorySpaceAttr.from_name("global")), func.ReturnOp()])

    with pytest.raises(TilePassError, match="still contains nn.relu"):
        tile_module._validate_input_contract(func_op, block)


def test_tile_private_helpers_validate_input_contract_rejects_func_call() -> None:
    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    func_op = _make_func_op("tile_contains_call", [mem_type], [], [func.CallOp("callee", [], []), func.ReturnOp()])

    with pytest.raises(TilePassError, match="must not contain func.call in tile body"):
        tile_module._validate_input_contract(func_op, func_op.body.block)


def test_tile_private_helpers_validate_input_contract_rejects_unregistered_op() -> None:
    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    func_op = _make_func_op("tile_contains_unsupported", [mem_type], [], [UnregisteredOp.with_name("other.op").create(operands=[], result_types=[]), func.ReturnOp()])

    with pytest.raises(TilePassError, match="contains unsupported op builtin.unregistered"):
        tile_module._validate_input_contract(func_op, func_op.body.block)


def test_tile_private_helpers_validate_input_contract_accepts_bridge_ops() -> None:
    """验证 tile helper 的输入合同会放行当前允许子集。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只要 block 由已 lower 的 kernel / dma / return / bridge op 组成，就不应触发合同错误。
    - 该测试顺带锁住 `_is_allowed_input_contract_op` 对 bridge op 的放行分支。

    使用示例:
    - pytest -q test/pass/test_lowering_tile_private_helpers.py -k test_tile_private_helpers_validate_input_contract_accepts_bridge_ops

    关联文件:
    - 功能实现: [kernel_gen/tile/common.py](kernel_gen/tile/common.py)
    - Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - 测试文件: [test/pass/test_lowering_tile_private_helpers.py](test/pass/test_lowering_tile_private_helpers.py)
    """

    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    kernel_op = KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind="add", space=space)
    broadcast_op = DmaBroadcastOp(block.args[0], block.args[1])
    tuner_op = TunerParamOp(SymbolValueType.from_expr("TILE_M"))
    dim_op = SymbolGetDimOp(block.args[0], 0)
    func_op = _make_func_op("tile_bridge", [mem_type, mem_type, mem_type], [], [])
    block = func_op.body.block
    kernel_op = KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind="add", space=space)
    broadcast_op = DmaBroadcastOp(block.args[0], block.args[1])
    tuner_op = TunerParamOp(SymbolValueType.from_expr("TILE_M"))
    dim_op = SymbolGetDimOp(block.args[0], 0)
    block.add_ops([kernel_op, broadcast_op, tuner_op, dim_op, func.ReturnOp()])

    tile_module._validate_input_contract(func_op, block)


def test_tile_private_helpers_validate_intermediate_materialization_contract() -> None:
    """验证 tile helper 的 carry memory 合同与失败分支。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 跨 stage 中间值若未由 `dma.alloc` 物化，必须 fail-fast。
    - 已物化但未继续消费的 carry memory 也必须报 dead-carry 错误。

    使用示例:
    - pytest -q test/pass/test_lowering_tile_private_helpers.py -k test_tile_private_helpers_validate_intermediate_materialization_contract

    关联文件:
    - 功能实现: [kernel_gen/tile/common.py](kernel_gen/tile/common.py)
    - Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - 测试文件: [test/pass/test_lowering_tile_private_helpers.py](test/pass/test_lowering_tile_private_helpers.py)
    """

    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    space = NnMemorySpaceAttr.from_name("global")

    success_func = _make_func_op("tile_carry_success", [mem_type, mem_type], [], [])
    success_block = success_func.body.block
    success_alloc = DmaAllocOp([], mem_type)
    success_kernel = KernelBinaryElewiseOp(success_alloc.result, success_block.args[0], success_block.args[0], kind="add", space=space)
    success_consumer = KernelBinaryElewiseOp(success_block.args[1], success_alloc.result, success_block.args[0], kind="add", space=space)
    success_block.add_ops([success_alloc, success_kernel, success_consumer, func.ReturnOp()])
    tile_module._validate_intermediate_materialization(success_func, success_block)

    no_alloc_func = _make_func_op("tile_carry_missing_alloc", [mem_type, mem_type], [], [])
    no_alloc_block = no_alloc_func.body.block
    no_alloc_writer = KernelBinaryElewiseOp(no_alloc_block.args[0], no_alloc_block.args[1], no_alloc_block.args[1], kind="add", space=space)
    no_alloc_consumer = KernelBinaryElewiseOp(no_alloc_block.args[1], no_alloc_block.args[0], no_alloc_block.args[1], kind="add", space=space)
    no_alloc_block.add_ops([no_alloc_writer, no_alloc_consumer, func.ReturnOp()])
    with pytest.raises(TilePassError, match="without dma.alloc carry memory"):
        tile_module._validate_intermediate_materialization(no_alloc_func, no_alloc_block)

    dead_alloc_func = _make_func_op("tile_carry_dead", [mem_type], [], [])
    dead_alloc_block = dead_alloc_func.body.block
    dead_alloc = DmaAllocOp([], mem_type)
    dead_kernel = KernelBinaryElewiseOp(dead_alloc.result, dead_alloc_block.args[0], dead_alloc_block.args[0], kind="add", space=space)
    dead_alloc_block.add_ops([dead_alloc, dead_kernel, func.ReturnOp()])
    with pytest.raises(TilePassError, match="TilePassDeadCarryMemory"):
        tile_module._validate_intermediate_materialization(dead_alloc_func, dead_alloc_block)


# TC-TILE-PRIVATE-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper 的 loop/view 构造、stride 推导、symbol 维度判断与 memory 角色矩阵边界。
# 使用示例: pytest -q test/pass/test_lowering_tile_private_helpers.py -k test_tile_private_helpers_cover_loop_view_and_role_helpers
# 对应功能实现文件路径: kernel_gen/tile/common.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile_private_helpers.py
def test_tile_private_helpers_cover_loop_view_and_role_helpers() -> None:
    mem_type = _make_memory_type([StringAttr("M"), IntAttr(1)])
    scalar_type = _make_memory_type([StringAttr("S")], i1)
    zero = SymbolConstOp(0).result
    one = SymbolConstOp(1).result
    two = SymbolConstOp(2).result
    three = SymbolConstOp(3).result

    assert tile_module._build_loop_nest([]) == (None, None, [])
    outer_loop, inner_block, loop_vars = tile_module._build_loop_nest([(zero, three, one), (one, three, one)])
    assert isinstance(outer_loop, SymbolForOp)
    assert inner_block is not None
    assert len(loop_vars) == 2
    assert isinstance(next(iter(outer_loop.body.block.ops)), SymbolForOp)
    assert tile_module._build_iter_type(zero, three, one) == SymbolIterType.from_bounds("0", "3", "1")

    assert tile_module._build_stride_values([], one) == []
    assert tile_module._build_stride_values([two], one) == [one]
    assert tile_module._build_stride_values([two, three], one) == [three, one]

    view_type = tile_module._build_view_type_from_exprs(mem_type, ["TILE_D0", "1"])
    assert list(view_type.shape.data) == [StringAttr("TILE_D0"), IntAttr(1)]
    assert list(view_type.stride.data) == [IntAttr(1), IntAttr(1)]
    source_block = Block(arg_types=[mem_type])
    view = tile_module._build_view(source_block.args[0], offsets=[zero, one], shape_values=[two, three], const_one=one)
    assert isinstance(view, DmaViewOp)
    assert list(view.result.type.shape.data) == [IntAttr(2), IntAttr(3)]
    assert list(view.result.type.stride.data) == [IntAttr(3), IntAttr(1)]
    with pytest.raises(TilePassError, match="dma.view source must be nn.memory"):
        tile_module._build_view(zero, offsets=[], shape_values=[], const_one=one)

    elem_block = Block(arg_types=[mem_type, mem_type, mem_type])
    elem_op = KernelBinaryElewiseOp(elem_block.args[2], elem_block.args[0], elem_block.args[1], kind="add", space=NnMemorySpaceAttr.from_name("global"))
    assert tile_module._build_elementwise_tile_roles(elem_op) == [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]
    assert tile_module._build_elementwise_tile_roles(SimpleNamespace(name="kernel.binary_elewise", operands=[zero, one])) == []
    with pytest.raises(TilePassError, match="matmul requires 3 operands"):
        tile_module._build_matmul_tile_roles(SimpleNamespace(name="kernel.matmul", operands=[zero, one]))
    matmul_block = Block(arg_types=[mem_type, mem_type, mem_type])
    matmul_op = KernelMatmulOp(matmul_block.args[2], matmul_block.args[0], matmul_block.args[1], NnMemorySpaceAttr.from_name("global"))
    assert tile_module._build_matmul_tile_roles(matmul_op) == [
        ["elewise", "reduce"],
        ["reduce", "elewise"],
        ["elewise", "elewise"],
    ]

    assert tile_module._is_unit_dim(IntAttr(1))
    assert tile_module._is_unit_dim(StringAttr("1"))
    assert not tile_module._is_unit_dim(IntAttr(2))
    assert tile_module._dim_equals(StringAttr("M"), StringAttr("M"))
    assert tile_module._dim_equals(IntAttr(1), IntAttr(1))
    assert not tile_module._dim_equals(StringAttr("M"), IntAttr(1))

    broadcast_target = _make_memory_type([StringAttr("M"), StringAttr("N")])
    broadcast_source = _make_memory_type([IntAttr(1), StringAttr("N")])
    broadcast_block = Block(arg_types=[broadcast_target, broadcast_source])
    broadcast_op = DmaBroadcastOp(broadcast_block.args[0], broadcast_block.args[1])
    assert tile_module._build_broadcast_tile_roles(broadcast_op) == [
        ["elewise", "elewise"],
        ["expand", "elewise"],
    ]
    assert tile_module._build_broadcast_tile_roles(SimpleNamespace(name="dma.broadcast", operands=[zero, one])) == []
    broadcast_scalar_block = Block(arg_types=[broadcast_target])
    assert tile_module._build_broadcast_tile_roles(DmaBroadcastOp(broadcast_scalar_block.args[0], zero)) == [
        ["elewise", "elewise"],
        ["expand", "expand"],
    ]

    analysis_attr = tile_module._tile_analysis_attr([["elewise", "expand"], ["expand", "elewise"]])
    assert analysis_attr == ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("expand")]),
            ArrayAttr([StringAttr("expand"), StringAttr("elewise")]),
        ]
    )
    elem_op = KernelBinaryElewiseOp(elem_block.args[2], elem_block.args[0], elem_block.args[1], kind="add", space=NnMemorySpaceAttr.from_name("global"))
    tile_module._set_tile_analysis(elem_op, [["elewise", "elewise"]])
    assert "tile.analysis" in elem_op.attributes
    assert "tile.tile_exprs" in elem_op.attributes
    analysis_before = elem_op.attributes["tile.analysis"]
    tile_module._set_tile_analysis(elem_op, [])
    assert elem_op.attributes["tile.analysis"] == analysis_before

    clear_block = Block(arg_types=[mem_type])
    clear_kernel = KernelBinaryElewiseOp(clear_block.args[0], clear_block.args[0], clear_block.args[0], kind="add", space=NnMemorySpaceAttr.from_name("global"))
    clear_kernel.attributes["tile.analysis"] = analysis_attr
    clear_kernel.attributes["tile.tile_exprs"] = analysis_attr
    clear_block.add_ops([clear_kernel, func.ReturnOp()])
    tile_module._clear_tile_analysis(clear_block)
    assert "tile.analysis" not in clear_kernel.attributes
    assert "tile.tile_exprs" in clear_kernel.attributes

    ordered_memory_values = tile_module._collect_kernel_memory_operands(
        [
            SimpleNamespace(name="kernel.binary_elewise", operands=[elem_block.args[0], elem_block.args[1], zero]),
            SimpleNamespace(name="kernel.matmul", operands=[elem_block.args[1], elem_block.args[0], elem_block.args[0]]),
            SimpleNamespace(name="kernel.binary_elewise", operands=[zero, one, zero]),
        ]
    )
    assert ordered_memory_values == [elem_block.args[0], elem_block.args[1]]

    tile_module._validate_tile_name_uniqueness(["TILE_M0", "TILE_N0"])
    with pytest.raises(TilePassError, match="tile names must be unique per function"):
        tile_module._validate_tile_name_uniqueness(["TILE_M0", "TILE_M0"])


# TC-TILE-PRIVATE-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper 的 plan 选择会按 elementwise / broadcast / matmul 不同形态分配 tile 名称与 reduce 名称。
# 使用示例: pytest -q test/pass/test_lowering_tile_private_helpers.py -k test_tile_private_helpers_cover_plan_selection
# 对应功能实现文件路径: kernel_gen/tile/common.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile_private_helpers.py
def test_tile_private_helpers_cover_plan_selection() -> None:
    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    func_op = _make_func_op("tile_plan_module", [mem_type, mem_type, mem_type], [], [])
    block = func_op.body.block
    space = NnMemorySpaceAttr.from_name("global")
    kernel_op = KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind="add", space=space)
    block.add_ops([kernel_op, func.ReturnOp()])
    _run_tile_analysis(ModuleOp([func_op]))

    plans, tile_names = tile_module._plan_tile_ops(func_op, block, tile_reduce=False)
    assert len(plans) == 1
    assert plans[0].kind == "elementwise"
    assert plans[0].reference_operand_index == 0
    assert tile_names == ["TILE_D0", "TILE_D1"]

    multi_func_op = _make_func_op("tile_multi_plan", [mem_type, mem_type, mem_type, mem_type], [], [])
    multi_block = multi_func_op.body.block
    multi_block.add_ops(
        [
            KernelBinaryElewiseOp(multi_block.args[2], multi_block.args[0], multi_block.args[1], kind="add", space=space),
            KernelBinaryElewiseOp(multi_block.args[3], multi_block.args[1], multi_block.args[0], kind="mul", space=space),
            func.ReturnOp(),
        ]
    )
    _run_tile_analysis(ModuleOp([multi_func_op]))
    multi_plans, multi_names = tile_module._plan_tile_ops(multi_func_op, multi_block, tile_reduce=False)
    assert [plan.reference_operand_index for plan in multi_plans] == [2, 2]
    assert multi_names == ["TILE_E0", "TILE_E1", "TILE_E2", "TILE_E3"]

    broadcast_module = _run_tile_analysis(tile_analysis_helpers._build_broadcast_module())
    broadcast_func = next(iter(broadcast_module.ops))
    broadcast_block = broadcast_func.body.block
    broadcast_plans, broadcast_names = tile_module._plan_tile_ops(broadcast_func, broadcast_block, tile_reduce=False)
    assert broadcast_plans[0].kind == "broadcast"
    assert broadcast_plans[0].loop_axes == [1]
    assert broadcast_names == ["TILE_D0"]

    matmul_module = _run_tile_analysis(tile_analysis_helpers._build_matmul_module())
    matmul_func = next(iter(matmul_module.ops))
    matmul_block = matmul_func.body.block
    matmul_plans, matmul_names = tile_module._plan_tile_ops(matmul_func, matmul_block, tile_reduce=True)
    assert matmul_plans[0].kind == "matmul"
    assert matmul_plans[0].reduce_tile_name == "TILE_R0"
    assert matmul_names == ["TILE_D0", "TILE_D1", "TILE_R0"]

    matmul_no_reduce_plans, matmul_no_reduce_names = tile_module._plan_tile_ops(matmul_func, matmul_block, tile_reduce=False)
    assert matmul_no_reduce_plans[0].reduce_tile_name is None
    assert matmul_no_reduce_names == ["TILE_D0", "TILE_D1"]

    with pytest.raises(TilePassError, match="tile names must be unique per function"):
        tile_module._validate_tile_name_uniqueness(["TILE_X0", "TILE_X0"])


# TC-TILE-PRIVATE-005A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper 的前置校验、命名解析与分类分支能覆盖非法输入与边界输入。
# 使用示例: pytest -q test/pass/test_lowering_tile_private_helpers.py -k test_tile_private_helpers_cover_validation_edges
# 对应功能实现文件路径: kernel_gen/tile/common.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile_private_helpers.py
def test_tile_private_helpers_cover_validation_edges() -> None:
    zero = SymbolConstOp(0).result
    one = SymbolConstOp(1).result
    two = SymbolConstOp(2).result
    three = SymbolConstOp(3).result

    with pytest.raises(TilePassError, match="must contain exactly one block"):
        tile_module._get_single_block(
            SimpleNamespace(
                sym_name=SimpleNamespace(data="tile_multi_block"),
                body=SimpleNamespace(blocks=[object(), object()]),
            )
        )

    assert tile_module._row_major_stride_exprs([]) == []
    assert tile_module._row_major_stride_exprs(["TILE_D0"]) == ["1"]
    assert tile_module._row_major_stride_exprs(["TILE_D0", "TILE_D1", "TILE_D2"]) == ["TILE_D1", "TILE_D2", "1"]

    assert tile_module._tile_param_hint("TILE_B0") == "b0"
    assert tile_module._tile_param_hint("TILE_M12") == "m12"
    assert tile_module._tile_param_hint("TILE_B") is None
    assert tile_module._tile_param_hint("TILE_X1") is None
    assert tile_module._tile_param_hint("TILE_Bx") is None
    assert tile_module._tile_param_hint("plain") is None

    with pytest.raises(TilePassError, match="unsupported tile op custom.op"):
        tile_module._collect_tile_ops(
            SimpleNamespace(
                ops=[SimpleNamespace(name="custom.op", attributes={"tile.analysis": ArrayAttr([])})],
            )
        )

    with pytest.raises(TilePassError, match="reduce kernel op is not supported"):
        tile_module._tile_op_kind(SimpleNamespace(name="kernel.reduce_sum"))
    with pytest.raises(TilePassError, match="unsupported tile op custom.op"):
        tile_module._tile_op_kind(SimpleNamespace(name="custom.op"))

    with pytest.raises(TilePassError, match="tile.analysis must be an array"):
        tile_module._parse_tile_analysis_roles(SimpleNamespace(attributes={}))
    with pytest.raises(TilePassError, match="tile.analysis must be a 2d array"):
        tile_module._parse_tile_analysis_roles(SimpleNamespace(attributes={"tile.analysis": ArrayAttr([StringAttr("bad")])}))
    with pytest.raises(TilePassError, match="tile.analysis entries must be string"):
        tile_module._parse_tile_analysis_roles(SimpleNamespace(attributes={"tile.analysis": ArrayAttr([ArrayAttr([IntAttr(1)])])}))

    assert tile_module._classify_kernel_ops([]) is None
    with pytest.raises(TilePassError, match="reduce kernel op is not supported"):
        tile_module._classify_kernel_ops([SimpleNamespace(name="kernel.reduce_sum")])
    with pytest.raises(TilePassError, match="matmul must not mix with other kernel ops"):
        tile_module._classify_kernel_ops([SimpleNamespace(name="kernel.matmul"), SimpleNamespace(name="kernel.binary_elewise")])
    with pytest.raises(TilePassError, match="unsupported kernel op custom.op"):
        tile_module._classify_kernel_ops([SimpleNamespace(name="custom.op")])
    assert tile_module._classify_kernel_ops([SimpleNamespace(name="kernel.binary_elewise")]) == "elementwise"

    with pytest.raises(TilePassError, match="matmul requires 3 operands"):
        tile_module._build_matmul_tile_roles(SimpleNamespace(name="kernel.matmul", operands=[zero, one]))
    with pytest.raises(TilePassError, match="matmul operands must be nn.memory"):
        tile_module._build_matmul_tile_roles(SimpleNamespace(name="kernel.matmul", operands=[zero, one, two]))
    rank1_mem = _make_memory_type([StringAttr("M")])
    rank1_block = Block(arg_types=[rank1_mem, rank1_mem, rank1_mem])
    rank1_matmul = KernelMatmulOp(rank1_block.args[2], rank1_block.args[0], rank1_block.args[1], NnMemorySpaceAttr.from_name("global"))
    with pytest.raises(TilePassError, match="matmul operands must be rank-2"):
        tile_module._build_matmul_tile_roles(rank1_matmul)

    broadcast_target = _make_memory_type([StringAttr("M"), StringAttr("N")])
    broadcast_source = _make_memory_type([IntAttr(1), StringAttr("N")])
    broadcast_block = Block(arg_types=[broadcast_target, broadcast_source])
    broadcast_op = DmaBroadcastOp(broadcast_block.args[0], broadcast_block.args[1])
    assert tile_module._build_broadcast_tile_roles(broadcast_op) == [
        ["elewise", "elewise"],
        ["expand", "elewise"],
    ]
    assert tile_module._build_broadcast_tile_roles(SimpleNamespace(operands=[zero, one])) == []
    broadcast_scalar_block = Block(arg_types=[broadcast_target])
    assert tile_module._build_broadcast_tile_roles(DmaBroadcastOp(broadcast_scalar_block.args[0], zero)) == [
        ["elewise", "elewise"],
        ["expand", "expand"],
    ]
    widened_source_block = Block(arg_types=[broadcast_target, _make_memory_type([StringAttr("X"), StringAttr("N")])])
    widened_broadcast = DmaBroadcastOp(widened_source_block.args[0], widened_source_block.args[1])
    assert tile_module._build_broadcast_tile_roles(widened_broadcast) == [
        ["elewise", "elewise"],
        ["expand", "elewise"],
    ]
    source_rank_block = Block(arg_types=[broadcast_target, _make_memory_type([StringAttr("A"), StringAttr("B"), StringAttr("C")])])
    with pytest.raises(TilePassError, match="broadcast source rank must be <= target rank"):
        tile_module._build_broadcast_tile_roles(DmaBroadcastOp(source_rank_block.args[0], source_rank_block.args[1]))


# TC-TILE-PRIVATE-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper rewrite 能覆盖 elementwise / broadcast / matmul 的主链与边界分支。
# 使用示例: pytest -q test/pass/test_lowering_tile_private_helpers.py -k test_tile_private_helpers_cover_rewrite_helpers
# 对应功能实现文件路径: kernel_gen/tile/common.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile_private_helpers.py
def test_tile_private_helpers_cover_rewrite_helpers() -> None:
    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    broadcast_source_type = _make_memory_type([IntAttr(1), StringAttr("N")])
    space = NnMemorySpaceAttr.from_name("global")
    zero = SymbolConstOp(0).result
    one = SymbolConstOp(1).result
    two = SymbolConstOp(2).result
    three = SymbolConstOp(3).result

    # elementwise
    elem_func = _make_func_op("tile_rewrite_elementwise", [mem_type, mem_type, mem_type], [], [])
    elem_block = elem_func.body.block
    elem_op = KernelBinaryElewiseOp(elem_block.args[2], elem_block.args[0], elem_block.args[1], kind="add", space=space)
    elem_block.add_ops([elem_op, func.ReturnOp()])
    _run_tile_analysis(ModuleOp([elem_func]))
    elem_plans, _ = tile_module._plan_tile_ops(elem_func, elem_block, tile_reduce=False)
    elem_helper_ops = tile_module._rewrite_elementwise_plan(elem_plans[0], tile_values={"TILE_D0": two, "TILE_D1": three})
    assert any(isinstance(op, SymbolForOp) for op in elem_helper_ops)
    assert any(isinstance(op, DmaViewOp) for op in next(iter(elem_helper_ops[-1].body.block.ops)).body.block.ops)
    assert "tile.analysis" not in elem_op.attributes

    invalid_elem_plan = tile_module._TileOpPlan(op=UnregisteredOp.with_name("kernel.binary_elewise").create(operands=[], result_types=[]), kind="elementwise", loop_axes=[], tile_names=[])
    with pytest.raises(TilePassError, match="elementwise requires memory operands"):
        tile_module._rewrite_elementwise_plan(invalid_elem_plan, tile_values={})

    fallback_elem_plan = tile_module._TileOpPlan(
        op=elem_op,
        kind="elementwise",
        loop_axes=[0, 1],
        tile_names=["TILE_D0", "TILE_D1"],
        reference_operand_index=999,
    )
    fallback_elem_func = _make_func_op("tile_rewrite_elementwise_fallback", [mem_type, mem_type, mem_type], [], [])
    fallback_block = fallback_elem_func.body.block
    fallback_op = KernelBinaryElewiseOp(fallback_block.args[2], fallback_block.args[0], fallback_block.args[1], kind="add", space=space)
    fallback_block.add_ops([fallback_op, func.ReturnOp()])
    fallback_elem_plan = tile_module._TileOpPlan(
        op=fallback_op,
        kind="elementwise",
        loop_axes=[0, 1],
        tile_names=["TILE_D0", "TILE_D1"],
        reference_operand_index=999,
    )
    _run_tile_analysis(ModuleOp([fallback_elem_func]))
    fallback_ops = tile_module._rewrite_elementwise_plan(fallback_elem_plan, tile_values={"TILE_D0": two, "TILE_D1": three})
    assert any(isinstance(op, SymbolForOp) for op in fallback_ops)

    # broadcast no-op for scalar source and success for memory source
    broadcast_noop_func = _make_func_op("tile_rewrite_broadcast_noop", [mem_type], [], [])
    broadcast_noop_block = broadcast_noop_func.body.block
    broadcast_noop = DmaBroadcastOp(broadcast_noop_block.args[0], zero)
    broadcast_noop_block.add_ops([broadcast_noop, func.ReturnOp()])
    _run_tile_analysis(ModuleOp([broadcast_noop_func]))
    broadcast_noop_plans, _ = tile_module._plan_tile_ops(broadcast_noop_func, broadcast_noop_block, tile_reduce=False)
    assert broadcast_noop_plans[0].loop_axes == []
    broadcast_noop_helper_ops = tile_module._rewrite_broadcast_plan(broadcast_noop_plans[0], tile_values={})
    assert any(getattr(op, "name", None) == "dma.broadcast" for op in broadcast_noop_helper_ops)
    assert not any(isinstance(op, SymbolForOp) for op in broadcast_noop_helper_ops)

    broadcast_func = _make_func_op("tile_rewrite_broadcast", [mem_type, broadcast_source_type], [], [])
    broadcast_block = broadcast_func.body.block
    broadcast_op = DmaBroadcastOp(broadcast_block.args[0], broadcast_block.args[1])
    broadcast_block.add_ops([broadcast_op, func.ReturnOp()])
    _run_tile_analysis(ModuleOp([broadcast_func]))
    broadcast_plans, _ = tile_module._plan_tile_ops(broadcast_func, broadcast_block, tile_reduce=False)
    broadcast_helper_ops = tile_module._rewrite_broadcast_plan(broadcast_plans[0], tile_values={"TILE_D0": two})
    assert any(isinstance(op, SymbolForOp) for op in broadcast_helper_ops)
    assert any(isinstance(op, DmaViewOp) for op in broadcast_helper_ops[-1].body.block.ops)

    bad_broadcast_plan = tile_module._TileOpPlan(
        op=UnregisteredOp.with_name("dma.broadcast").create(operands=[zero, one], result_types=[]),
        kind="broadcast",
        loop_axes=[0],
        tile_names=["TILE_D0"],
        roles=[["elewise"], ["elewise"]],
    )
    with pytest.raises(TilePassError, match="broadcast target must be nn.memory"):
        tile_module._rewrite_broadcast_plan(bad_broadcast_plan, tile_values={"TILE_D0": two})

    bad_rank_block = Block(arg_types=[mem_type, mem_type])
    bad_rank_broadcast_plan = tile_module._TileOpPlan(
        op=DmaBroadcastOp(bad_rank_block.args[0], bad_rank_block.args[1]),
        kind="broadcast",
        loop_axes=[0],
        tile_names=["TILE_D0"],
        roles=[["elewise"], ["elewise", "elewise"]],
    )
    with pytest.raises(TilePassError, match="broadcast roles must match rank"):
        tile_module._rewrite_broadcast_plan(bad_rank_broadcast_plan, tile_values={"TILE_D0": two})

    source_rank_block = Block(arg_types=[mem_type, _make_memory_type([StringAttr("A"), StringAttr("B"), StringAttr("C")])])
    source_rank_mismatch_plan = tile_module._TileOpPlan(
        op=DmaBroadcastOp(source_rank_block.args[0], source_rank_block.args[1]),
        kind="broadcast",
        loop_axes=[0],
        tile_names=["TILE_D0"],
        roles=[["elewise", "elewise"], ["elewise", "elewise"]],
    )
    with pytest.raises(TilePassError, match="broadcast source rank must be <= target rank"):
        tile_module._rewrite_broadcast_plan(source_rank_mismatch_plan, tile_values={"TILE_D0": two})

    # rewrite 前置非法输入与 no-op 边界
    invalid_elem_func = _make_func_op("tile_rewrite_elementwise_invalid", [], [], [])
    invalid_elem_block = invalid_elem_func.body.block
    invalid_elem_op = KernelBinaryElewiseOp(zero, one, two, kind="add", space=space)
    invalid_elem_op.attributes["tile.analysis"] = ArrayAttr([ArrayAttr([StringAttr("elewise")])])
    invalid_elem_block.add_ops([invalid_elem_op, func.ReturnOp()])
    with pytest.raises(TilePassError, match="elementwise requires memory operands"):
        tile_module._plan_tile_ops(invalid_elem_func, invalid_elem_block, tile_reduce=False)

    invalid_broadcast_func = _make_func_op("tile_rewrite_broadcast_invalid", [mem_type, mem_type], [], [])
    invalid_broadcast_block = invalid_broadcast_func.body.block
    invalid_broadcast_op = DmaBroadcastOp(invalid_broadcast_block.args[0], invalid_broadcast_block.args[1])
    invalid_broadcast_op.attributes["tile.analysis"] = ArrayAttr([])
    invalid_broadcast_block.add_ops([invalid_broadcast_op, func.ReturnOp()])
    with pytest.raises(TilePassError, match="broadcast requires tile.analysis roles"):
        tile_module._plan_tile_ops(invalid_broadcast_func, invalid_broadcast_block, tile_reduce=False)

    with pytest.raises(TilePassError, match="tile.analysis must be an array"):
        tile_module._rewrite_broadcast_plan(
            tile_module._TileOpPlan(
                op=SimpleNamespace(operands=[zero, one], attributes={}),
                kind="broadcast",
                loop_axes=[0],
                tile_names=["TILE_D0"],
                roles=None,
            ),
            tile_values={"TILE_D0": two},
        )
    with pytest.raises(TilePassError, match="broadcast requires two operands"):
        tile_module._rewrite_broadcast_plan(
            tile_module._TileOpPlan(
                op=invalid_broadcast_op,
                kind="broadcast",
                loop_axes=[0],
                tile_names=["TILE_D0"],
                roles=[["elewise"]],
            ),
            tile_values={"TILE_D0": two},
        )

    with pytest.raises(TilePassError, match="matmul operands must be nn.memory"):
        tile_module._rewrite_matmul_plan(
            tile_module._TileOpPlan(
                op=SimpleNamespace(operands=[zero, one, two], attributes={}),
                kind="matmul",
                loop_axes=[0, 1],
                tile_names=["TILE_D0", "TILE_D1"],
                reduce_tile_name=None,
            ),
            tile_values={"TILE_D0": two, "TILE_D1": three},
            tile_reduce=False,
        )

    # matmul rewrite: reduce on i32 uses DmaFillOp, non-i32 falls back to unregistered dma.fill, tile_reduce off skips reduce chain.
    matmul_func = _make_func_op("tile_rewrite_matmul", [mem_type, mem_type, mem_type], [], [])
    matmul_block = matmul_func.body.block
    matmul_op = KernelMatmulOp(matmul_block.args[2], matmul_block.args[0], matmul_block.args[1], space)
    matmul_block.add_ops([matmul_op, func.ReturnOp()])
    _run_tile_analysis(ModuleOp([matmul_func]))
    matmul_plan, _ = tile_module._plan_tile_ops(matmul_func, matmul_block, tile_reduce=True)
    matmul_helper_ops = tile_module._rewrite_matmul_plan(matmul_plan[0], tile_values={"TILE_D0": two, "TILE_D1": three, "TILE_R0": one}, tile_reduce=True)
    assert any(isinstance(op, DmaFillOp) for op in next(iter(matmul_helper_ops[-1].body.block.ops)).body.block.ops)
    assert any(isinstance(op, SymbolForOp) for op in matmul_helper_ops)

    matmul_no_reduce_func = _make_func_op("tile_rewrite_matmul_no_reduce", [mem_type, mem_type, mem_type], [], [])
    matmul_no_reduce_block = matmul_no_reduce_func.body.block
    matmul_no_reduce_op = KernelMatmulOp(matmul_no_reduce_block.args[2], matmul_no_reduce_block.args[0], matmul_no_reduce_block.args[1], space)
    matmul_no_reduce_block.add_ops([matmul_no_reduce_op, func.ReturnOp()])
    _run_tile_analysis(ModuleOp([matmul_no_reduce_func]))
    matmul_no_reduce_plan, _ = tile_module._plan_tile_ops(matmul_no_reduce_func, matmul_no_reduce_block, tile_reduce=False)
    no_reduce_helper_ops = tile_module._rewrite_matmul_plan(matmul_no_reduce_plan[0], tile_values={"TILE_D0": two, "TILE_D1": three}, tile_reduce=False)
    assert any(isinstance(op, SymbolForOp) for op in no_reduce_helper_ops)

    non_i32_mem_type = _make_memory_type([StringAttr("M"), StringAttr("N")], i1)
    non_i32_func = _make_func_op("tile_rewrite_matmul_non_i32", [non_i32_mem_type, non_i32_mem_type, non_i32_mem_type], [], [])
    non_i32_block = non_i32_func.body.block
    non_i32_op = KernelMatmulOp(non_i32_block.args[2], non_i32_block.args[0], non_i32_block.args[1], space)
    non_i32_op.attributes.pop("space")
    non_i32_block.add_ops([non_i32_op, func.ReturnOp()])
    _run_tile_analysis(ModuleOp([non_i32_func]))
    non_i32_plan, _ = tile_module._plan_tile_ops(non_i32_func, non_i32_block, tile_reduce=True)
    non_i32_helper_ops = tile_module._rewrite_matmul_plan(non_i32_plan[0], tile_values={"TILE_D0": two, "TILE_D1": three, "TILE_R0": one}, tile_reduce=True)
    assert any(
        getattr(op.attributes.get("op_name__"), "data", None) == "dma.fill" and not isinstance(op, DmaFillOp)
        for op in next(iter(non_i32_helper_ops[-1].body.block.ops)).body.block.ops
    )
