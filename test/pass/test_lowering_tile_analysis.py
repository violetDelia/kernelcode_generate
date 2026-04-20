"""tile-analysis pass tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `kernel_gen.passes.lowering.tile_analysis.TileAnalysisPass` 的 ModulePass 合同。
- 锁定 `tile-analysis` 只写 `tile.analysis` 与 `tile.tile_exprs`，不生成 tile 改写结构。
- 覆盖 `kernel.binary_elewise`、`dma.broadcast`、`kernel.matmul` 三类 op 的 analysis-only 结果。

使用示例:
- pytest -q test/pass/test_lowering_tile_analysis.py

关联文件:
- 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
- Spec 文档: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
- 测试文件: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, StringAttr, i32
from xdsl.ir import Block, Region
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

tile_analysis_module = importlib.import_module("kernel_gen.passes.lowering.tile_analysis")
TileAnalysisPass = tile_analysis_module.TileAnalysisPass

from kernel_gen.dialect.dma import DmaBroadcastOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType


def _make_memory_type(shape_names: list[str]) -> NnMemoryType:
    """构造测试用 nn.memory 类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 以字符串维度构造最小 `nn.memory` 类型，便于锁定 tile analysis 结果。

    使用示例:
    - mem_type = _make_memory_type(["M", "N"])

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
    - Spec 文档: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - 测试文件: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
    """

    shape = ArrayAttr([StringAttr(name) for name in shape_names])
    stride = ArrayAttr([StringAttr(f"S{axis}") for axis in range(len(shape_names))])
    space = NnMemorySpaceAttr.from_name("global")
    return NnMemoryType(shape, stride, i32, space)


def _build_module() -> ModuleOp:
    """构造最小 tile-analysis 测试模块。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成单函数 `kernel.binary_elewise` 模块，用于验证 analysis 标注合同。

    使用示例:
    - module = _build_module()

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
    - Spec 文档: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - 测试文件: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
    """

    mem_type = _make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops(
        [
            KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind="add", space=space),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        "tile_analysis_module",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _build_broadcast_module() -> ModuleOp:
    """构造最小 tile-analysis broadcast 测试模块。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成单函数 `dma.broadcast` 模块，用于验证 analysis 标注与 tile 表达式占位。

    使用示例:
    - module = _build_broadcast_module()

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
    - Spec 文档: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - 测试文件: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
    """

    target_type = _make_memory_type(["M", "N"])
    source_type = _make_memory_type(["N"])
    block = Block(arg_types=[target_type, source_type])
    block.add_ops([DmaBroadcastOp(block.args[0], block.args[1]), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_analysis_broadcast",
        FunctionType.from_lists([target_type, source_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _build_matmul_module() -> ModuleOp:
    """构造最小 tile-analysis matmul 测试模块。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成单函数 `kernel.matmul` 模块，用于验证 analysis 标注与 tile 表达式占位。

    使用示例:
    - module = _build_matmul_module()

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
    - Spec 文档: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - 测试文件: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
    """

    lhs_type = _make_memory_type(["M", "K"])
    rhs_type = _make_memory_type(["K", "N"])
    out_type = _make_memory_type(["M", "N"])
    block = Block(arg_types=[lhs_type, rhs_type, out_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([KernelMatmulOp(block.args[2], block.args[0], block.args[1], space), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_analysis_matmul",
        FunctionType.from_lists([lhs_type, rhs_type, out_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _collect_ops(root) -> list[object]:
    """递归收集 operation 列表。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 便于断言 `tile-analysis` 不会插入 `symbol.for` / `dma.view` 一类改写 op。

    使用示例:
    - ops = _collect_ops(module)

    关联文件:
    - 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
    - Spec 文档: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - 测试文件: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
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


# TC-TILE-ANALYSIS-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 TileAnalysisPass 作为 ModulePass 可直接执行，并只写 analysis 标注。
# 使用示例: pytest -q test/pass/test_lowering_tile_analysis.py -k test_tile_analysis_pass_apply_only_adds_analysis_attrs
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile_analysis.py
# 对应 spec 文件路径: spec/pass/lowering/tile_analysis.md
# 对应测试文件路径: test/pass/test_lowering_tile_analysis.py
def test_tile_analysis_pass_apply_only_adds_analysis_attrs() -> None:
    module = _build_module()
    pass_obj = TileAnalysisPass()

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "tile-analysis"

    pass_obj.apply(Context(), module)

    ops = _collect_ops(module)
    kernel_ops = [op for op in ops if getattr(op, "name", None) == "kernel.binary_elewise"]
    loop_ops = [op for op in ops if getattr(op, "name", None) == "symbol.for"]
    view_ops = [op for op in ops if getattr(op, "name", None) == "dma.view"]

    assert len(kernel_ops) == 1
    assert loop_ops == []
    assert view_ops == []
    assert "tile.analysis" in kernel_ops[0].attributes
    assert "tile.tile_exprs" in kernel_ops[0].attributes


# TC-TILE-ANALYSIS-002
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 TileAnalysisPass 对 dma.broadcast 也会写入 tile.analysis 与 tile.tile_exprs。
# 使用示例: pytest -q test/pass/test_lowering_tile_analysis.py -k test_tile_analysis_pass_marks_broadcast_attrs
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile_analysis.py
# 对应 spec 文件路径: spec/pass/lowering/tile_analysis.md
# 对应测试文件路径: test/pass/test_lowering_tile_analysis.py
def test_tile_analysis_pass_marks_broadcast_attrs() -> None:
    module = _build_broadcast_module()
    TileAnalysisPass().apply(Context(), module)

    ops = _collect_ops(module)
    broadcast_ops = [op for op in ops if getattr(op, "name", None) == "dma.broadcast"]
    loop_ops = [op for op in ops if getattr(op, "name", None) == "symbol.for"]
    view_ops = [op for op in ops if getattr(op, "name", None) == "dma.view"]

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("expand"), StringAttr("elewise")]),
        ]
    )
    expected_exprs = ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
        ]
    )

    assert len(broadcast_ops) == 1
    assert loop_ops == []
    assert view_ops == []
    assert broadcast_ops[0].attributes["tile.analysis"] == expected_roles
    assert broadcast_ops[0].attributes["tile.tile_exprs"] == expected_exprs


# TC-TILE-ANALYSIS-003
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 TileAnalysisPass 对 kernel.matmul 也会写入 tile.analysis 与 tile.tile_exprs。
# 使用示例: pytest -q test/pass/test_lowering_tile_analysis.py -k test_tile_analysis_pass_marks_matmul_attrs
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile_analysis.py
# 对应 spec 文件路径: spec/pass/lowering/tile_analysis.md
# 对应测试文件路径: test/pass/test_lowering_tile_analysis.py
def test_tile_analysis_pass_marks_matmul_attrs() -> None:
    module = _build_matmul_module()
    TileAnalysisPass().apply(Context(), module)

    ops = _collect_ops(module)
    matmul_ops = [op for op in ops if getattr(op, "name", None) == "kernel.matmul"]
    loop_ops = [op for op in ops if getattr(op, "name", None) == "symbol.for"]
    view_ops = [op for op in ops if getattr(op, "name", None) == "dma.view"]

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("reduce")]),
            ArrayAttr([StringAttr("reduce"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    expected_exprs = ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
        ]
    )

    assert len(matmul_ops) == 1
    assert loop_ops == []
    assert view_ops == []
    assert matmul_ops[0].attributes["tile.analysis"] == expected_roles
    assert matmul_ops[0].attributes["tile.tile_exprs"] == expected_exprs


# TC-TILE-ANALYSIS-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 tile-analysis 目录入口对应的 registry 名称可直接构造 ModulePass。
# 使用示例: pytest -q test/pass/test_lowering_tile_analysis.py -k test_tile_analysis_registered_pass_is_module_pass
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile_analysis.py
# 对应 spec 文件路径: spec/pass/lowering/tile_analysis.md
# 对应测试文件路径: test/pass/test_lowering_tile_analysis.py
def test_tile_analysis_registered_pass_is_module_pass() -> None:
    load_builtin_passes = importlib.import_module("kernel_gen.passes.registry").load_builtin_passes
    build_registered_pass = importlib.import_module("kernel_gen.passes.registry").build_registered_pass

    load_builtin_passes()
    pass_obj = build_registered_pass("tile-analysis")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "tile-analysis"
    assert type(pass_obj).__name__ == "TileAnalysisPass"
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.lowering.tile_analysis"
