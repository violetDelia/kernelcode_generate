"""tile-reduce pass tests.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `kernel_gen.passes.lowering.tile_reduce.TileReducePass` 的 ModulePass 合同。
- 锁定 `tile-reduce` 会在 `tile-analysis` 的基础上继续写出 `symbol.for` / `dma.view` / `dma.fill` 的 reduce 结构。
- 锁定 rewritten `kernel.matmul` 继续保留 `tile.analysis + tile.tile_exprs`。

使用示例:
- pytest -q test/pass/test_lowering_tile_reduce.py

关联文件:
- 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
- Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- 测试文件: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

tile_analysis_helpers = importlib.import_module("test.pass.test_lowering_tile_analysis")
tile_analysis_module = importlib.import_module("kernel_gen.passes.lowering.tile_analysis")
tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
tile_reduce_module = importlib.import_module("kernel_gen.passes.lowering.tile_reduce")
registry_module = importlib.import_module("kernel_gen.passes.registry")

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp

TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TilePassError = tile_module.TilePassError
TileReducePass = tile_reduce_module.TileReducePass
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def _apply_tile_reduce_pipeline(module):
    """先执行 tile-analysis，再执行 tile-reduce。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 tile-reduce 专门测试提供最小组合入口。
    - 返回就地改写后的 module，供后续断言。

    使用示例:
    - module = _apply_tile_reduce_pipeline(module)

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    - Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - 测试文件: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    """

    ctx = Context()
    TileAnalysisPass().apply(ctx, module)
    TileReducePass().apply(ctx, module)
    return module


def _expected_matmul_exprs() -> ArrayAttr:
    """返回 tile-reduce matmul 的期望 tile 表达矩阵。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一复用 `TILE_D0/TILE_D1` 的三 operand 矩阵。

    使用示例:
    - expected = _expected_matmul_exprs()

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    - Spec 文档: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - 测试文件: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    """

    return ArrayAttr(
        [
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
        ]
    )


def _build_fc_chain_module():
    """构造 broadcast -> matmul -> binary 组合链路模块。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成最小 fc 风格 lowered IR，用于验证 tile-reduce 只为 matmul reduce 计划建参。
    - `matmul` 的输出使用 `dma.alloc` 中间 buffer，满足跨阶段 carry memory 合同。

    使用示例:
    - module = _build_fc_chain_module()

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    - Spec 文档: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - 测试文件: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    """

    out_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    x_type = tile_analysis_helpers._make_memory_type(["M", "K"])
    weight_type = tile_analysis_helpers._make_memory_type(["K", "N"])
    bias_type = tile_analysis_helpers._make_memory_type(["N"])
    block = tile_analysis_helpers.Block(arg_types=[out_type, x_type, weight_type, bias_type])
    space = tile_analysis_helpers.NnMemorySpaceAttr.from_name("global")
    bias_alloc = DmaAllocOp([], out_type)
    matmul_alloc = DmaAllocOp([], out_type)
    block.add_ops(
        [
            bias_alloc,
            matmul_alloc,
            DmaBroadcastOp(bias_alloc.result, block.args[3]),
            KernelMatmulOp(matmul_alloc.result, block.args[1], block.args[2], space),
            KernelBinaryElewiseOp(block.args[0], matmul_alloc.result, bias_alloc.result, kind="add", space=space),
            tile_analysis_helpers.func.ReturnOp(),
        ]
    )
    func_op = tile_analysis_helpers.func.FuncOp(
        "tile_reduce_fc_chain",
        tile_analysis_helpers.FunctionType.from_lists([out_type, x_type, weight_type, bias_type], []),
        tile_analysis_helpers.Region(block),
    )
    return tile_analysis_helpers.ModuleOp([func_op])


def _tuner_param_names(module) -> list[str]:
    """提取 module 中 `tuner.param` 的名称。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 遍历 IR 并读取 `tuner.param` 结果类型中的 `symbol.int` 名称。
    - 保持遍历顺序，便于断言 pass 产出的参数顺序。

    使用示例:
    - names = _tuner_param_names(module)

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    - Spec 文档: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - 测试文件: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    """

    names: list[str] = []
    for op in tile_analysis_helpers._collect_ops(module):
        if getattr(op, "name", None) != "tuner.param":
            continue
        value = op.result.type.get_value()
        names.append(str(value))
    return names


# TC-TILE-REDUCE-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 TileReducePass 作为 ModulePass 可直接执行，并对 matmul 输出显式 reduce 结构。
# 使用示例: pytest -q test/pass/test_lowering_tile_reduce.py -k test_tile_reduce_pass_rewrites_matmul_and_preserves_contract
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile_reduce.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile_reduce.py
def test_tile_reduce_pass_rewrites_matmul_and_preserves_contract() -> None:
    module = _apply_tile_reduce_pipeline(tile_analysis_helpers._build_matmul_module())

    ops = tile_analysis_helpers._collect_ops(module)
    matmul_ops = [op for op in ops if getattr(op, "name", None) == "kernel.matmul"]
    loop_ops = [op for op in ops if getattr(op, "name", None) == "symbol.for"]
    view_ops = [op for op in ops if getattr(op, "name", None) == "dma.view"]
    fill_ops = [op for op in ops if getattr(op, "name", None) == "dma.fill"]
    alloc_ops = [op for op in ops if getattr(op, "name", None) == "dma.alloc"]
    bridge_ops = [
        op
        for op in ops
        if getattr(op, "name", None) in {"tile.step_value", "kernel_split.tile_value", "tile.symbol_literal"}
    ]

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("reduce")]),
            ArrayAttr([StringAttr("reduce"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )

    assert len(matmul_ops) == 1
    assert len(loop_ops) == 3
    assert len(view_ops) == 3
    assert len(fill_ops) == 1
    assert len(alloc_ops) == 1
    assert bridge_ops == []
    assert matmul_ops[0].attributes["tile.analysis"] == expected_roles
    assert matmul_ops[0].attributes["tile.tile_exprs"] == _expected_matmul_exprs()


# TC-TILE-REDUCE-001A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 TileReducePass 对缺少 tile.analysis 的 kernel.matmul 显式失败。
# 使用示例: pytest -q test/pass/test_lowering_tile_reduce.py -k test_tile_reduce_rejects_matmul_without_analysis_attrs
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile_reduce.py
# 对应 spec 文件路径: spec/pass/lowering/tile_reduce.md
# 对应测试文件路径: test/pass/test_lowering_tile_reduce.py
def test_tile_reduce_rejects_matmul_without_analysis_attrs() -> None:
    module = tile_analysis_helpers._build_matmul_module()

    with pytest.raises(TilePassError, match="TilePassUnsupportedOp: .*requires tile.analysis and tile.tile_exprs"):
        TileReducePass().apply(Context(), module)


# TC-TILE-REDUCE-001B
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 TileReducePass 在组合链路中只为 matmul reduce 计划建参。
# 使用示例: pytest -q test/pass/test_lowering_tile_reduce.py -k test_tile_reduce_fc_chain_omits_unconsumed_tuner_params
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile_reduce.py
# 对应 spec 文件路径: spec/pass/lowering/tile_reduce.md
# 对应测试文件路径: test/pass/test_lowering_tile_reduce.py
def test_tile_reduce_fc_chain_omits_unconsumed_tuner_params() -> None:
    module = _apply_tile_reduce_pipeline(_build_fc_chain_module())

    assert _tuner_param_names(module) == ["TILE_M0", "TILE_M1", "TILE_R0"]
    assert "TILE_B0" not in str(module)
    assert "TILE_E0" not in str(module)
    assert "TILE_E1" not in str(module)


# TC-TILE-REDUCE-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 tile-reduce 目录入口对应的 registry 名称可直接构造 ModulePass。
# 使用示例: pytest -q test/pass/test_lowering_tile_reduce.py -k test_tile_reduce_registered_pass_is_module_pass
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile_reduce.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile_reduce.py
def test_tile_reduce_registered_pass_is_module_pass() -> None:
    load_builtin_passes()
    pass_obj = build_registered_pass("tile-reduce")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "tile-reduce"
    assert type(pass_obj).__name__ == "TileReducePass"
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.lowering.tile_reduce"
