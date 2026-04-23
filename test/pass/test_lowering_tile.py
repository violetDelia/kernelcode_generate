"""tile helper module tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 锁定 `kernel_gen.passes.lowering.tile` 已退回为 helper module，不再公开旧 `TilePass`。
- 覆盖 helper module 对外只保留错误类型与共享 helper 的收口口径。

使用示例:
- pytest -q test/pass/test_lowering_tile.py

关联文件:
- 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
- Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- 测试文件: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.dialects.builtin import IntAttr, IntegerAttr, i1, i32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp
from kernel_gen.symbol_variable.type import NumericType

tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
SPACE_GLOBAL = NnMemorySpaceAttr.from_name("global")


# TC-TILE-HELPER-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper module 不再公开旧 TilePass / TileAnalysisPass / bridge op。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_helper_module_drops_legacy_public_contract
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_helper_module_drops_legacy_public_contract() -> None:
    assert tile_module.__all__ == ["TilePassError", "_raise_tile_error"]
    assert not hasattr(tile_module, "TilePass")
    assert not hasattr(tile_module, "TileAnalysisPass")
    assert not hasattr(tile_module, "_TileStepValueOp")
    assert not hasattr(tile_module, "_TileSymbolLiteralOp")
    assert not hasattr(tile_module, "_read_kernel_split_tile_spec")
    assert not hasattr(tile_module, "_build_elementwise_loop_specs")
    assert not hasattr(tile_module, "_build_matmul_loop_specs")


# TC-TILE-HELPER-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile helper module 仍保留 analysis 共享 helper，供新 ModulePass 复用。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_helper_module_keeps_shared_analysis_helpers
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_helper_module_keeps_shared_analysis_helpers() -> None:
    roles = [["elewise", "elewise"], ["expand", "elewise"]]
    attr = tile_module._tile_analysis_attr(roles)

    expected = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("expand"), StringAttr("elewise")]),
        ]
    )

    assert attr == expected
    assert tile_module._tile_param_hint("TILE_M0") == "m0"
    assert tile_module._tile_param_hint("TILE_D0") is None


# TC-TILE-HELPER-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 覆盖 tile helper 的输入合同校验与中间物化规则。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_helper_module_validates_input_contract_and_materialization
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_helper_module_validates_input_contract_and_materialization() -> None:
    mem_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        i32,
        SPACE_GLOBAL,
    )
    bool_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        i1,
        SPACE_GLOBAL,
    )
    bool_numeric_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        NumericType.Bool,
        SPACE_GLOBAL,
    )

    assert tile_module._is_bool_memory(DmaAllocOp([], bool_type).result)
    assert tile_module._is_bool_memory(DmaAllocOp([], bool_numeric_type).result)
    assert tile_module._is_allowed_input_contract_op(DmaAllocOp([], mem_type))
    assert tile_module._is_allowed_input_contract_op(func.ReturnOp())

    func_op = SimpleNamespace(
        sym_name=StringAttr("tile_kernel"),
        function_type=SimpleNamespace(outputs=SimpleNamespace(data=())),
    )
    allowed_block = Block()
    allowed_block.add_op(DmaAllocOp([], mem_type))
    allowed_block.add_op(func.ReturnOp())
    tile_module._validate_input_contract(func_op, allowed_block)

    with pytest.raises(tile_module.TilePassError, match="still returns nn.memory results"):
        tile_module._validate_input_contract(
            SimpleNamespace(
                sym_name=StringAttr("tile_kernel"),
                function_type=SimpleNamespace(outputs=SimpleNamespace(data=(mem_type,))),
            ),
            allowed_block,
        )

    nn_block = Block()
    nn_block.add_op(func.ReturnOp())
    nn_block.add_op(
        NnAddOp(
            DmaAllocOp([], mem_type).result,
            DmaAllocOp([], mem_type).result,
            mem_type,
            SPACE_GLOBAL,
        )
    )
    with pytest.raises(tile_module.TilePassError, match="still contains nn.add"):
        tile_module._validate_input_contract(func_op, nn_block)

    call_block = Block()
    call_block.add_op(func.CallOp("callee", [], []))
    with pytest.raises(tile_module.TilePassError, match="must not contain func.call"):
        tile_module._validate_input_contract(func_op, call_block)

    unsupported_block = Block()
    unsupported_block.add_op(arith.ConstantOp(IntegerAttr(1, 32)))
    with pytest.raises(tile_module.TilePassError, match="contains unsupported op arith.constant"):
        tile_module._validate_input_contract(func_op, unsupported_block)

    carry_func = SimpleNamespace(
        sym_name=StringAttr("carry_kernel"),
        function_type=SimpleNamespace(outputs=SimpleNamespace(data=())),
    )
    carry_block = Block()
    carry_source = func.CallOp("carry", [], [mem_type])
    carry_block.add_op(carry_source)
    lhs_alloc = DmaAllocOp([], mem_type)
    rhs_alloc = DmaAllocOp([], mem_type)
    carry_block.add_op(lhs_alloc)
    carry_block.add_op(rhs_alloc)
    first_kernel = KernelBinaryElewiseOp(
        carry_source.results[0],
        lhs_alloc.result,
        rhs_alloc.result,
        kind="add",
        space=SPACE_GLOBAL,
    )
    carry_block.add_op(first_kernel)
    consumer_alloc = DmaAllocOp([], mem_type)
    carry_block.add_op(consumer_alloc)
    second_kernel = KernelBinaryElewiseOp(
        consumer_alloc.result,
        carry_source.results[0],
        rhs_alloc.result,
        kind="add",
        space=SPACE_GLOBAL,
    )
    carry_block.add_op(second_kernel)
    with pytest.raises(tile_module.TilePassError, match="without dma.alloc carry memory"):
        tile_module._validate_intermediate_materialization(carry_func, carry_block)

    dead_block = Block()
    dead_alloc = DmaAllocOp([], mem_type)
    dead_lhs = DmaAllocOp([], mem_type)
    dead_rhs = DmaAllocOp([], mem_type)
    dead_block.add_op(dead_alloc)
    dead_block.add_op(dead_lhs)
    dead_block.add_op(dead_rhs)
    dead_block.add_op(
        KernelBinaryElewiseOp(
            dead_alloc.result,
            dead_lhs.result,
            dead_rhs.result,
            kind="add",
            space=SPACE_GLOBAL,
        )
    )
    with pytest.raises(tile_module.TilePassError, match="without later consumption"):
        tile_module._validate_intermediate_materialization(carry_func, dead_block)


# TC-TILE-HELPER-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 覆盖 compare 兼容重排与符号表达辅助 helper。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_helper_module_normalizes_compare_and_symbol_helpers
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_helper_module_normalizes_compare_and_symbol_helpers() -> None:
    out_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        i32,
        SPACE_GLOBAL,
    )
    lhs_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        i32,
        SPACE_GLOBAL,
    )
    rhs_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        i1,
        SPACE_GLOBAL,
    )
    block = Block()
    compare_op = KernelBinaryElewiseOp(
        DmaAllocOp([], out_type).result,
        DmaAllocOp([], lhs_type).result,
        DmaAllocOp([], rhs_type).result,
        kind="eq",
        space=SPACE_GLOBAL,
    )
    compare_op.attributes["tile.analysis"] = StringAttr("analysis")
    compare_op.attributes["tile.tile_exprs"] = StringAttr("tile")
    block.add_op(compare_op)

    tile_module._normalize_binary_elewise_compare_compat(block)
    normalized = list(block.ops)[0]
    assert isinstance(normalized, KernelBinaryElewiseOp)
    assert normalized.out.type == rhs_type
    assert normalized.attributes["tile.analysis"] == StringAttr("analysis")
    assert normalized.attributes["tile.tile_exprs"] == StringAttr("tile")

    assert tile_module._symbol_expr_from_value(SymbolConstOp(7).result) == "7"
    with pytest.raises(tile_module.TilePassError, match="symbol value type must be !symbol.int"):
        tile_module._symbol_expr_from_value(DmaAllocOp([], out_type).result)

    assert tile_module._expr_to_dim_attr("8") == IntAttr(8)
    assert tile_module._expr_to_dim_attr("-3") == IntAttr(-3)
    assert tile_module._expr_to_dim_attr("TILE_D0") == StringAttr("TILE_D0")
    assert tile_module._row_major_stride_exprs([]) == []
    assert tile_module._row_major_stride_exprs(["M"]) == ["1"]
    assert tile_module._row_major_stride_exprs(["M", "N"]) == ["N", "1"]

    built_symbol = tile_module._build_symbol_const(7)
    assert built_symbol.name == "builtin.unregistered"
    assert built_symbol.attributes["op_name__"] == StringAttr("symbol.const")
    assert built_symbol.results[0].type.get_value() == 7
