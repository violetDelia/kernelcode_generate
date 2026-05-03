"""npu demo lowering pipeline tests.


功能说明:
- 覆盖 kernel_gen/passes/pipeline/npu_demo_lowering.py 的公开 builder 与顺序。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.pipeline.npu_demo_lowering --cov-branch --cov-report=term-missing test/passes/pipeline/test_npu_demo_lowering.py`

使用示例:
- pytest -q test/passes/pipeline/test_npu_demo_lowering.py

关联文件:
- 功能实现: kernel_gen/passes/pipeline/npu_demo_lowering.py
- Spec 文档: spec/pass/pipeline/npu_demo_lowering.md
- 测试文件: test/passes/pipeline/test_npu_demo_lowering.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.config import reset_config, set_target
from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.operation.dma import deslice, slice
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

pipeline_module = importlib.import_module("kernel_gen.passes.pipeline")
build_npu_demo_lowering_pipeline = pipeline_module.build_npu_demo_lowering_pipeline

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
PassManager = pass_manager_module.PassManager
InlinePass = importlib.import_module("kernel_gen.passes.inline").InlinePass
CommonSubexpressionElimination = importlib.import_module(
    "xdsl.transforms.common_subexpression_elimination"
).CommonSubexpressionElimination
AttachArchInformationPass = importlib.import_module("kernel_gen.passes.attach_arch_information").AttachArchInformationPass
DecompassPass = importlib.import_module("kernel_gen.passes.decompass").DecompassPass
NnLoweringPass = importlib.import_module("kernel_gen.passes.lowering").NnLoweringPass
OutlineDeviceKernelPass = importlib.import_module("kernel_gen.passes.outline_device_kernel").OutlineDeviceKernelPass
SymbolBufferHoistPass = importlib.import_module("kernel_gen.passes.symbol_buffer_hoist").SymbolBufferHoistPass
SymbolLoopHoistPass = importlib.import_module("kernel_gen.passes.symbol_loop_hoist").SymbolLoopHoistPass
TileAnalysisPass = importlib.import_module("kernel_gen.passes.tile.analysis").TileAnalysisPass
LaunchKernelCostFuncPass = importlib.import_module(
    "kernel_gen.passes.tuning.launch_kernel_cost_func"
).LaunchKernelCostFuncPass


# TC-PIPELINE-100
# 功能说明: 验证 npu-demo-lowering builder 返回 PassManager 且名称固定。
# 测试目的: 锁定 npu-demo-lowering pipeline 的公开名称与类型。
# 使用示例: pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k test_npu_demo_lowering_pipeline_builds_pass_manager
# 对应功能实现文件路径: kernel_gen/passes/pipeline/npu_demo_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/npu_demo_lowering.md
# 对应测试文件路径: test/passes/pipeline/test_npu_demo_lowering.py
def test_npu_demo_lowering_pipeline_builds_pass_manager() -> None:
    pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    assert isinstance(pm, PassManager)
    assert pm.name == "npu-demo-lowering"


# TC-PIPELINE-101
# 功能说明: 验证 npu-demo-lowering 的固定顺序为 inline -> cse -> decompass -> lower-nn -> symbol-loop-hoist -> cse -> tile-analysis -> symbol-buffer-hoist -> attach-arch-information -> outline-device-kernel -> launch-kernel-cost-func。
# 测试目的: 锁定 dsl_run 新正向管线的最小公开顺序。
# 使用示例: pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k test_npu_demo_lowering_pipeline_pass_order
# 对应功能实现文件路径: kernel_gen/passes/pipeline/npu_demo_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/npu_demo_lowering.md
# 对应测试文件路径: test/passes/pipeline/test_npu_demo_lowering.py
@pytest.mark.nn_lowering
def test_npu_demo_lowering_pipeline_pass_order(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []

    def _record_inline(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("inline")

    def _record_cse(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("cse")

    def _record_decompose(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("decompass")

    def _record_lower(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("lower-nn")

    def _record_hoist(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("symbol-loop-hoist")

    def _record_buffer_hoist(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("symbol-buffer-hoist")

    def _record_tile_analysis(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("tile-analysis")

    def _record_attach(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("attach-arch-information")

    def _record_outline(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("outline-device-kernel")

    def _record_cost(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        _ = target
        order.append("launch-kernel-cost-func")

    monkeypatch.setattr(InlinePass, "apply", _record_inline)
    monkeypatch.setattr(CommonSubexpressionElimination, "apply", _record_cse)
    monkeypatch.setattr(DecompassPass, "apply", _record_decompose)
    monkeypatch.setattr(NnLoweringPass, "apply", _record_lower)
    monkeypatch.setattr(SymbolLoopHoistPass, "apply", _record_hoist)
    monkeypatch.setattr(TileAnalysisPass, "apply", _record_tile_analysis)
    monkeypatch.setattr(SymbolBufferHoistPass, "apply", _record_buffer_hoist)
    monkeypatch.setattr(AttachArchInformationPass, "apply", _record_attach)
    monkeypatch.setattr(OutlineDeviceKernelPass, "apply", _record_outline)
    monkeypatch.setattr(LaunchKernelCostFuncPass, "apply", _record_cost)

    pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    sentinel = ModuleOp([])
    assert pm.run(sentinel) is sentinel
    assert order == [
        "inline",
        "cse",
        "decompass",
        "lower-nn",
        "symbol-loop-hoist",
        "cse",
        "tile-analysis",
        "symbol-buffer-hoist",
        "attach-arch-information",
        "outline-device-kernel",
        "launch-kernel-cost-func",
    ]


def test_npu_demo_lowering_pipeline_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match=r"^npu-demo-lowering only accepts target option; got only-kernel$"):
        build_npu_demo_lowering_pipeline({"only-kernel": "true"})


def test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain() -> None:
    """验证公开 npu_demo lowering -> gen_kernel 链路保留 tile 符号参数。"""
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    tile_m = SymbolDim("TILE_M")
    tile_n = SymbolDim("TILE_N")

    def matmul_kernel(lhs: Memory, rhs: Memory, out: Memory, TILE_M: SymbolDim, TILE_N: SymbolDim):
        M = lhs.shape.get_shape()[0]
        K = lhs.shape.get_shape()[1]
        N = rhs.shape.get_shape()[1]

        for m0 in loop(0, M, TILE_M):
            for n0 in loop(0, N, TILE_N):
                lhs_tile = slice(lhs, [m0, 0], [TILE_M, K], [1, 1], MemorySpace.TSM)
                rhs_tile = slice(rhs, [0, n0], [K, TILE_N], [1, 1], MemorySpace.TSM)
                partial = matmul(lhs_tile, rhs_tile)
                deslice(out, partial, [m0, n0], [TILE_M, TILE_N], [1, 1])

    module = mlir_gen(matmul_kernel, lhs, rhs, out, tile_m, tile_n)
    pipeline = build_npu_demo_lowering_pipeline()
    pipeline.run(module)
    set_target("npu_demo")
    try:
        source = gen_kernel(module, EmitCContext())
    finally:
        reset_config()

    assert "void matmul_kernel(" in source
    assert "S_INT _cost_DMA_matmul_kernel_device(" in source
    assert "S_INT _cost_MAC_matmul_kernel_device(" in source
    assert ", long long arg3, long long arg4" in source
    assert "static void matmul_kernel_device(" in source
    assert "npu_demo::KernelContext& ctx" not in source
    assert ", S_INT arg3, S_INT arg4" in source
    assert "npu_demo::launch<c_0, c_1, c_2, c_3>(matmul_kernel_device, arg0, arg1, arg2, arg3, arg4);" in source
    assert "Memory<TSM, float>" in source
