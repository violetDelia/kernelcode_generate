"""tile-elewise pass tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `kernel_gen.tile.elewise.TileElewisePass` 的 ModulePass 合同。
- 锁定 `tile-elewise` 会在 `tile-analysis` 的基础上继续写出 `symbol.for` / `dma.view` 改写结构。
- 锁定 rewritten op 继续保留 `tile.analysis + tile.tile_exprs`。

使用示例:
- pytest -q test/pass/test_lowering_tile_elewise.py

关联文件:
- 功能实现: [kernel_gen/tile/elewise.py](kernel_gen/tile/elewise.py)
- Spec 文档: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
- 测试文件: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.dialects.builtin import FunctionType
from xdsl.ir import Block, Region
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

tile_analysis_helpers = importlib.import_module("test.pass.test_lowering_tile_analysis")
tile_analysis_module = importlib.import_module("kernel_gen.tile.analysis")
tile_elewise_module = importlib.import_module("kernel_gen.tile.elewise")
registry_module = importlib.import_module("kernel_gen.passes.registry")

TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TileElewisePass = tile_elewise_module.TileElewisePass
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def _collect_ops(root: object) -> list[object]:
    """递归收集 operation 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 便于断言 tile-elewise 会把 op 改写成显式 loop / view / kernel 结构。

    使用示例:
    - ops = _collect_ops(module)

    关联文件:
    - 功能实现: [kernel_gen/tile/elewise.py](kernel_gen/tile/elewise.py)
    - Spec 文档: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
    - 测试文件: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
    """

    collected: list[object] = []

    def _visit(op: object) -> None:
        collected.append(op)
        if hasattr(op, "regions"):
            for region in op.regions:
                for block in region.blocks:
                    for inner in block.ops:
                        _visit(inner)

    _visit(root)
    return collected


def _apply_tile_elewise_pipeline(module: ModuleOp) -> ModuleOp:
    """先执行 tile-analysis，再执行 tile-elewise。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 tile-elewise 专门测试提供最小组合入口。
    - 返回就地改写后的 module，供后续断言。

    使用示例:
    - module = _apply_tile_elewise_pipeline(module)

    关联文件:
    - 功能实现: [kernel_gen/tile/elewise.py](kernel_gen/tile/elewise.py)
    - Spec 文档: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
    - 测试文件: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
    """

    ctx = Context()
    TileAnalysisPass().apply(ctx, module)
    TileElewisePass().apply(ctx, module)
    return module


def _build_multi_plan_module() -> ModuleOp:
    """构造包含两个 tile 计划的测试模块。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于回归 `tile-elewise` 只处理最后一个 plan 的缩进 bug。
    - 让同一函数里同时存在两个 `kernel.binary_elewise`，便于断言两个 plan 都被改写。

    使用示例:
    - module = _build_multi_plan_module()

    关联文件:
    - 功能实现: [kernel_gen/tile/elewise.py](kernel_gen/tile/elewise.py)
    - Spec 文档: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
    - 测试文件: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
    """

    mem_type = tile_analysis_helpers._make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type, mem_type, mem_type])
    space = tile_analysis_helpers.NnMemorySpaceAttr.from_name("global")
    block.add_ops(
        [
            tile_analysis_helpers.KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind="add", space=space),
            tile_analysis_helpers.KernelBinaryElewiseOp(block.args[3], block.args[1], block.args[0], kind="mul", space=space),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        "tile_elewise_multi_plan",
        FunctionType.from_lists([mem_type, mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _expected_elementwise_exprs() -> ArrayAttr:
    return ArrayAttr(
        [
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
        ]
    )


def _expected_broadcast_exprs() -> ArrayAttr:
    return ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("TILE_D0")]),
            ArrayAttr([StringAttr(""), StringAttr("TILE_D0")]),
        ]
    )


def _expected_matmul_exprs() -> ArrayAttr:
    return ArrayAttr(
        [
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
        ]
    )


# TC-TILE-ELEWISE-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 TileElewisePass 作为 ModulePass 可直接执行，并对 elementwise 输出显式分块结构。
# 使用示例: pytest -q test/pass/test_lowering_tile_elewise.py -k test_tile_elewise_pass_rewrites_elementwise_and_preserves_contract
# 对应功能实现文件路径: kernel_gen/tile/elewise.py
# 对应 spec 文件路径: spec/pass/lowering/tile_elewise.md
# 对应测试文件路径: test/pass/test_lowering_tile_elewise.py
def test_tile_elewise_pass_rewrites_elementwise_and_preserves_contract() -> None:
    module = _apply_tile_elewise_pipeline(tile_analysis_helpers._build_module())

    ops = _collect_ops(module)
    kernel_ops = [op for op in ops if getattr(op, "name", None) == "kernel.binary_elewise"]
    loop_ops = [op for op in ops if getattr(op, "name", None) == "symbol.for"]
    view_ops = [op for op in ops if getattr(op, "name", None) == "dma.view"]
    bridge_ops = [op for op in ops if getattr(op, "name", None) in {"tile.step_value", "kernel_split.tile_value"}]

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )

    assert len(kernel_ops) == 1
    assert len(loop_ops) == 2
    assert len(view_ops) == 3
    assert bridge_ops == []
    assert kernel_ops[0].attributes["tile.analysis"] == expected_roles
    assert kernel_ops[0].attributes["tile.tile_exprs"] == _expected_elementwise_exprs()


# TC-TILE-ELEWISE-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 TileElewisePass 对 broadcast 也会保留 tile.analysis 与 tile.tile_exprs。
# 使用示例: pytest -q test/pass/test_lowering_tile_elewise.py -k test_tile_elewise_pass_rewrites_broadcast_and_preserves_contract
# 对应功能实现文件路径: kernel_gen/tile/elewise.py
# 对应 spec 文件路径: spec/pass/lowering/tile_elewise.md
# 对应测试文件路径: test/pass/test_lowering_tile_elewise.py
def test_tile_elewise_pass_rewrites_broadcast_and_preserves_contract() -> None:
    module = _apply_tile_elewise_pipeline(tile_analysis_helpers._build_broadcast_module())

    ops = _collect_ops(module)
    broadcast_ops = [op for op in ops if getattr(op, "name", None) == "dma.broadcast"]
    loop_ops = [op for op in ops if getattr(op, "name", None) == "symbol.for"]
    view_ops = [op for op in ops if getattr(op, "name", None) == "dma.view"]
    bridge_ops = [op for op in ops if getattr(op, "name", None) in {"tile.step_value", "kernel_split.tile_value"}]

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("expand"), StringAttr("elewise")]),
        ]
    )

    assert len(broadcast_ops) == 1
    assert len(loop_ops) == 1
    assert len(view_ops) == 2
    assert bridge_ops == []
    assert broadcast_ops[0].attributes["tile.analysis"] == expected_roles
    assert broadcast_ops[0].attributes["tile.tile_exprs"] == _expected_broadcast_exprs()


# TC-TILE-ELEWISE-003A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 TileElewisePass 会遍历并改写同一函数中的多个 plan，而不是只处理最后一个。
# 使用示例: pytest -q test/pass/test_lowering_tile_elewise.py -k test_tile_elewise_pass_rewrites_multiple_plans_and_preserves_contract
# 对应功能实现文件路径: kernel_gen/tile/elewise.py
# 对应 spec 文件路径: spec/pass/lowering/tile_elewise.md
# 对应测试文件路径: test/pass/test_lowering_tile_elewise.py
def test_tile_elewise_pass_rewrites_multiple_plans_and_preserves_contract() -> None:
    module = _apply_tile_elewise_pipeline(_build_multi_plan_module())

    ops = _collect_ops(module)
    kernel_ops = [op for op in ops if getattr(op, "name", None) == "kernel.binary_elewise"]
    loop_ops = [op for op in ops if getattr(op, "name", None) == "symbol.for"]
    view_ops = [op for op in ops if getattr(op, "name", None) == "dma.view"]
    bridge_ops = [op for op in ops if getattr(op, "name", None) in {"tile.step_value", "kernel_split.tile_value"}]

    assert len(kernel_ops) == 2
    assert len(loop_ops) == 4
    assert len(view_ops) == 6
    assert bridge_ops == []
    for kernel_op in kernel_ops:
        assert "tile.analysis" in kernel_op.attributes
        assert "tile.tile_exprs" in kernel_op.attributes


# TC-TILE-ELEWISE-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 TileElewisePass 对 matmul 的 rewritten kernel.matmul 也会保留 tile.analysis 与 tile.tile_exprs。
# 使用示例: pytest -q test/pass/test_lowering_tile_elewise.py -k test_tile_elewise_pass_rewrites_matmul_and_preserves_contract
# 对应功能实现文件路径: kernel_gen/tile/elewise.py
# 对应 spec 文件路径: spec/pass/lowering/tile_elewise.md
# 对应测试文件路径: test/pass/test_lowering_tile_elewise.py
def test_tile_elewise_pass_rewrites_matmul_and_preserves_contract() -> None:
    module = _apply_tile_elewise_pipeline(tile_analysis_helpers._build_matmul_module())

    ops = _collect_ops(module)
    matmul_ops = [op for op in ops if getattr(op, "name", None) == "kernel.matmul"]
    loop_ops = [op for op in ops if getattr(op, "name", None) == "symbol.for"]
    view_ops = [op for op in ops if getattr(op, "name", None) == "dma.view"]
    bridge_ops = [op for op in ops if getattr(op, "name", None) in {"tile.step_value", "kernel_split.tile_value"}]

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("reduce")]),
            ArrayAttr([StringAttr("reduce"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )

    assert len(matmul_ops) == 1
    assert len(loop_ops) == 2
    assert len(view_ops) == 3
    assert bridge_ops == []
    assert matmul_ops[0].attributes["tile.analysis"] == expected_roles
    assert matmul_ops[0].attributes["tile.tile_exprs"] == _expected_matmul_exprs()


# TC-TILE-ELEWISE-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 tile-elewise 目录入口对应的 registry 名称可直接构造 ModulePass。
# 使用示例: pytest -q test/pass/test_lowering_tile_elewise.py -k test_tile_elewise_registered_pass_is_module_pass
# 对应功能实现文件路径: kernel_gen/tile/elewise.py
# 对应 spec 文件路径: spec/pass/lowering/tile_elewise.md
# 对应测试文件路径: test/pass/test_lowering_tile_elewise.py
def test_tile_elewise_registered_pass_is_module_pass() -> None:
    load_builtin_passes()
    pass_obj = build_registered_pass("tile-elewise")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "tile-elewise"
    assert type(pass_obj).__name__ == "TileElewisePass"
    assert pass_obj.__class__.__module__ == "kernel_gen.tile.elewise"
