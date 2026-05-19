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
from xdsl.parser import Parser

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.context import build_default_context
from kernel_gen.core.config import reset_config, set_dump_dir, set_target
from kernel_gen.core.error import KernelCodeError
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
ArchParallelizePass = importlib.import_module("kernel_gen.passes.arch_parallelize").ArchParallelizePass
DecompassPass = importlib.import_module("kernel_gen.passes.decompass").DecompassPass
LowerDmaMemoryHierarchyPass = importlib.import_module("kernel_gen.passes.dma_memory_hierarchy").LowerDmaMemoryHierarchyPass
MemoryPlanPass = importlib.import_module("kernel_gen.passes.memory_plan").MemoryPlanPass
MultiBufferPass = importlib.import_module("kernel_gen.passes.multi_buffer").MultiBufferPass
MemoryPoolPass = importlib.import_module("kernel_gen.passes.memory_pool").MemoryPoolPass
NnLoweringPass = importlib.import_module("kernel_gen.passes.lowering").NnLoweringPass
OutlineDeviceKernelPass = importlib.import_module("kernel_gen.passes.outline_device_kernel").OutlineDeviceKernelPass
SymbolBufferHoistPass = importlib.import_module("kernel_gen.passes.symbol_buffer_hoist").SymbolBufferHoistPass
SymbolLoopHoistPass = importlib.import_module("kernel_gen.passes.symbol_loop_hoist").SymbolLoopHoistPass
TileAnalysisPass = importlib.import_module("kernel_gen.passes.tile.analysis").TileAnalysisPass
TemplateNameInferPass = importlib.import_module("kernel_gen.passes.template_name_infer").TemplateNameInferPass

_PIPELINE_PASS_ORDER: list[str] = []


def _record_inline(self, ctx: Context, target: ModuleOp) -> None:
    """记录 inline pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `InlinePass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(InlinePass, "apply", _record_inline)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("inline")


def _record_cse(self, ctx: Context, target: ModuleOp) -> None:
    """记录 CSE pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `CommonSubexpressionElimination.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(CommonSubexpressionElimination, "apply", _record_cse)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("cse")


def _record_decompose(self, ctx: Context, target: ModuleOp) -> None:
    """记录 decompass pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `DecompassPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(DecompassPass, "apply", _record_decompose)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("decompass")


def _record_lower(self, ctx: Context, target: ModuleOp) -> None:
    """记录 lower-nn pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `NnLoweringPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(NnLoweringPass, "apply", _record_lower)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("lower-nn")


def _record_symbol_loop_hoist(self, ctx: Context, target: ModuleOp) -> None:
    """记录 symbol-loop-hoist pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `SymbolLoopHoistPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(SymbolLoopHoistPass, "apply", _record_symbol_loop_hoist)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("symbol-loop-hoist")


def _record_symbol_buffer_hoist(self, ctx: Context, target: ModuleOp) -> None:
    """记录 symbol-buffer-hoist pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `SymbolBufferHoistPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(SymbolBufferHoistPass, "apply", _record_symbol_buffer_hoist)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("symbol-buffer-hoist")


def _record_tile_analysis(self, ctx: Context, target: ModuleOp) -> None:
    """记录 tile-analysis pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `TileAnalysisPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(TileAnalysisPass, "apply", _record_tile_analysis)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("tile-analysis")


def _record_lower_dma_memory_hierarchy(self, ctx: Context, target: ModuleOp) -> None:
    """记录 lower-dma-memory-hierarchy pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `LowerDmaMemoryHierarchyPass` 的固定参数。

    使用示例:
    - monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "apply", _record_lower_dma_memory_hierarchy)
    """

    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append(f"lower-dma-memory-hierarchy:{self.fold}:{self.apply_op}")


def _record_memory_plan(self, ctx: Context, target: ModuleOp) -> None:
    """记录 memory-plan pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `MemoryPlanPass` 的 `insert_free` 与 `fold` 固定参数。

    使用示例:
    - monkeypatch.setattr(MemoryPlanPass, "apply", _record_memory_plan)
    """

    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append(f"memory-plan:{self.insert_free}:{self.fold}")


def _record_arch_parallelize(self, ctx: Context, target: ModuleOp) -> None:
    """记录 arch-parallelize pass 执行。

    功能说明:
    - 为 pipeline 顺序测试记录默认 npu-demo-lowering 直接接入的公开 `ArchParallelizePass` 参数。

    使用示例:
    - monkeypatch.setattr(ArchParallelizePass, "apply", _record_arch_parallelize)
    """

    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append(f"arch-parallelize:{self.target}:{self.parallel_level}")


def _record_memory_pool(self, ctx: Context, target: ModuleOp) -> None:
    """记录 memory-pool pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `MemoryPoolPass` 的 `rewrite` 与 `alignment` 固定参数。

    使用示例:
    - monkeypatch.setattr(MemoryPoolPass, "apply", _record_memory_pool)
    """

    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append(f"memory-pool:{self.rewrite}:{self.alignment}")


def _record_multi_buffer(self, ctx: Context, target: ModuleOp) -> None:
    """记录 multi-buffer pass 执行。

    功能说明:
    - 为 pipeline 顺序测试记录 `MultiBufferPass` 的固定 stage 数。

    使用示例:
    - monkeypatch.setattr(MultiBufferPass, "apply", _record_multi_buffer)
    """

    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append(f"multi-buffer:{self.memory_stage}:{self.fold}")


def _record_attach(self, ctx: Context, target: ModuleOp) -> None:
    """记录 attach-arch-information pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `AttachArchInformationPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(AttachArchInformationPass, "apply", _record_attach)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("attach-arch-information")


def _record_outline(self, ctx: Context, target: ModuleOp) -> None:
    """记录 outline-device-kernel pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `OutlineDeviceKernelPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(OutlineDeviceKernelPass, "apply", _record_outline)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("outline-device-kernel")


def _record_template_name(self, ctx: Context, target: ModuleOp) -> None:
    """记录 template-name-infer pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `TemplateNameInferPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(TemplateNameInferPass, "apply", _record_template_name)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("template-name-infer")


def _noop_pass_apply(self, ctx: Context, target: ModuleOp) -> None:
    """跳过非目标 pass，隔离验证默认 pipeline 的 arch 安全阶段。

    功能说明:
    - 为 pipeline 行为测试保留公开 `Pass.apply(...)` 调用形态，同时避免无关 pass 改写测试输入。

    使用示例:
    - monkeypatch.setattr(InlinePass, "apply", _noop_pass_apply)
    """

    _ = self
    _ = ctx
    _ = target


def _dump_stage_text_by_marker(dump_dir: Path, marker: str, *, occurrence: int = 1) -> str:
    """按 dump 文件首行 marker 读取指定 stage 文本。

    功能说明:
    - 通过公开 dump 文件内容定位 pass stage，避免把 pipeline 验收绑定到不稳定序号。
    - `occurrence` 用于区分同名 pass 的第几次出现，例如第二段 `symbol-buffer-hoist`。

    使用示例:
    - text = _dump_stage_text_by_marker(tmp_path, "symbol-buffer-hoist", occurrence=2)
    """

    if occurrence < 1:
        raise AssertionError(f"dump stage occurrence must be positive; got {occurrence}")
    seen = 0
    available_markers: list[str] = []
    for path in sorted(dump_dir.glob("*.mlir")):
        text = path.read_text(encoding="utf-8")
        stage_marker = text.splitlines()[0] if text.splitlines() else ""
        available_markers.append(stage_marker)
        if stage_marker != marker:
            continue
        seen += 1
        if seen == occurrence:
            return text
    raise AssertionError(
        f"dump stage marker {marker!r} occurrence {occurrence} not found; available={available_markers!r}"
    )


def matmul_kernel(lhs: Memory, rhs: Memory, out: Memory, TILE_M: SymbolDim, TILE_N: SymbolDim) -> None:
    """构造 npu_demo lowering 集成测试用 matmul kernel。


    功能说明:
    - 通过公开 DSL `loop/slice/matmul/deslice` 构造含符号 tile 的 matmul kernel。
    - 用于验证 npu-demo-lowering 的 memory-plan、buffer-hoist、memory-pool 与 gen_kernel 链路。

    使用示例:
    - module = mlir_gen(matmul_kernel, lhs, rhs, out, tile_m, tile_n)
    """

    M = lhs.shape.get_shape()[0]
    K = lhs.shape.get_shape()[1]
    N = rhs.shape.get_shape()[1]

    for m0 in loop(0, M, TILE_M):
        for n0 in loop(0, N, TILE_N):
            lhs_tile = slice(lhs, [m0, 0], [TILE_M, K], [1, 1], MemorySpace.TSM)
            rhs_tile = slice(rhs, [0, n0], [K, TILE_N], [1, 1], MemorySpace.TSM)
            partial = matmul(lhs_tile, rhs_tile)
            deslice(out, partial, [m0, n0], [TILE_M, TILE_N], [1, 1])


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
# 功能说明: 验证 npu-demo-lowering 的固定顺序包含 memory-plan insert-free、两次 symbol-buffer-hoist 与 memory-pool 后二次 symbol-loop-hoist。
# 测试目的: 锁定 dsl_run 新正向管线的最小公开顺序。
# 使用示例: pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k test_npu_demo_lowering_pipeline_pass_order
# 对应功能实现文件路径: kernel_gen/passes/pipeline/npu_demo_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/npu_demo_lowering.md
# 对应测试文件路径: test/passes/pipeline/test_npu_demo_lowering.py
@pytest.mark.nn_lowering
def test_npu_demo_lowering_pipeline_pass_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _PIPELINE_PASS_ORDER.clear()
    monkeypatch.setattr(InlinePass, "apply", _record_inline)
    monkeypatch.setattr(CommonSubexpressionElimination, "apply", _record_cse)
    monkeypatch.setattr(DecompassPass, "apply", _record_decompose)
    monkeypatch.setattr(NnLoweringPass, "apply", _record_lower)
    monkeypatch.setattr(SymbolLoopHoistPass, "apply", _record_symbol_loop_hoist)
    monkeypatch.setattr(MemoryPlanPass, "apply", _record_memory_plan)
    monkeypatch.setattr(ArchParallelizePass, "apply", _record_arch_parallelize)
    monkeypatch.setattr(TileAnalysisPass, "apply", _record_tile_analysis)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "apply", _record_lower_dma_memory_hierarchy)
    monkeypatch.setattr(MultiBufferPass, "apply", _record_multi_buffer)
    monkeypatch.setattr(SymbolBufferHoistPass, "apply", _record_symbol_buffer_hoist)
    monkeypatch.setattr(MemoryPoolPass, "apply", _record_memory_pool)
    monkeypatch.setattr(AttachArchInformationPass, "apply", _record_attach)
    monkeypatch.setattr(OutlineDeviceKernelPass, "apply", _record_outline)
    monkeypatch.setattr(TemplateNameInferPass, "apply", _record_template_name)

    pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    sentinel = ModuleOp([])
    assert pm.run(sentinel) is sentinel
    assert _PIPELINE_PASS_ORDER == [
        "inline",
        "cse",
        "decompass",
        "lower-nn",
        "symbol-loop-hoist",
        "cse",
        "memory-plan:True:False",
        "arch-parallelize:npu_demo:block",
        "symbol-buffer-hoist",
        "tile-analysis",
        'lower-dma-memory-hierarchy:True:matmul{["", "tlm1", "tlm2"]}',
        "multi-buffer:3:True",
        "memory-pool:True:0",
        "symbol-loop-hoist",
        "symbol-buffer-hoist",
        "attach-arch-information",
        "outline-device-kernel",
        "template-name-infer",
    ]


def test_npu_demo_lowering_pipeline_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match=r"^npu-demo-lowering only accepts target option; got only-kernel$"):
        build_npu_demo_lowering_pipeline({"only-kernel": "true"})


def test_npu_demo_lowering_pipeline_arch_parallelize_propagates_unsupported_structure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证默认 pipeline 直接使用公开 arch-parallelize 失败合同。

    功能说明:
    - 通过公开 pipeline builder 运行含多个顶层 `symbol.for` 的 module。
    - 其它 pass 用公开 `apply(...)` 调用形态替换为空操作，只隔离观察默认 pipeline 中的公开 arch 阶段。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k propagates_unsupported_structure
    """

    module_text = """builtin.module {
  func.func @unsupported_loops() {
    %0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %1 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    %2 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    symbol.for %i = %0 to %1 step %2 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<1>>} {
    }
    symbol.for %j = %0 to %1 step %2 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<1>>} {
    }
    func.return
  }
}
"""
    module = Parser(build_default_context(), module_text).parse_module()
    monkeypatch.setattr(InlinePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(CommonSubexpressionElimination, "apply", _noop_pass_apply)
    monkeypatch.setattr(DecompassPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(NnLoweringPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolLoopHoistPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPlanPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TileAnalysisPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MultiBufferPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolBufferHoistPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPoolPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(AttachArchInformationPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(OutlineDeviceKernelPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TemplateNameInferPass, "apply", _noop_pass_apply)

    pipeline = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    with pytest.raises(KernelCodeError, match=r"multiple top-level symbol\.for loops are not supported"):
        pipeline.run(module)


def test_npu_demo_lowering_pipeline_arch_parallelize_wraps_no_loop_body_with_block0_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证默认 pipeline 的公开 arch-parallelize 对无 `symbol.for` 直线函数生成 block0 guard。

    功能说明:
    - 通过公开 pipeline builder 运行只含直线 `func.return` 的 module。
    - 其它 pass 用公开 `apply(...)` 调用形态替换为空操作，确保只观察公开 arch 阶段。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k wraps_no_loop_body_with_block0_guard
    """

    _PIPELINE_PASS_ORDER.clear()
    module_text = """builtin.module {
  func.func private @callee()
  func.func @linear_kernel() {
    func.call @callee() : () -> ()
    func.return
  }
}
"""
    module = Parser(build_default_context(), module_text).parse_module()
    monkeypatch.setattr(InlinePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(CommonSubexpressionElimination, "apply", _noop_pass_apply)
    monkeypatch.setattr(DecompassPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(NnLoweringPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolLoopHoistPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPlanPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TileAnalysisPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MultiBufferPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolBufferHoistPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPoolPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(AttachArchInformationPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(OutlineDeviceKernelPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TemplateNameInferPass, "apply", _noop_pass_apply)

    pipeline = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    assert pipeline.run(module) is module

    lowered_text = str(module)
    assert "func.func @linear_kernel" in lowered_text
    assert "arch.get_block_id" in lowered_text
    assert "scf.if" in lowered_text
    assert "func.call @callee" in lowered_text


def test_npu_demo_lowering_pipeline_memory_plan_dump_shows_lifecycle_and_pool(tmp_path: Path) -> None:
    """验证 npu-demo-lowering 真实中间态包含 memory-plan 生命周期与 memory-pool 改写。


    功能说明:
    - 通过公开 `set_dump_dir(...)` 与公开 pipeline builder 观察 pass dump。
    - 按 pass marker 查找 `memory-plan`、两段 `symbol-buffer-hoist` 与 `memory-pool`，
      不依赖 dump 文件序号。
    - 断言第二段 `symbol-buffer-hoist` 把 memory-pool 后 loop-invariant alias op 推到内层 loop 前。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k memory_plan_dump
    """

    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    tile_m = SymbolDim("TILE_M")
    tile_n = SymbolDim("TILE_N")
    module = mlir_gen(matmul_kernel, lhs, rhs, out, tile_m, tile_n)
    pipeline = build_npu_demo_lowering_pipeline()

    set_dump_dir(tmp_path)
    try:
        pipeline.run(module)
    finally:
        reset_config()

    memory_plan_text = _dump_stage_text_by_marker(tmp_path, "memory-plan")
    arch_parallelize_text = _dump_stage_text_by_marker(tmp_path, "arch-parallelize")
    first_buffer_hoist_text = _dump_stage_text_by_marker(tmp_path, "symbol-buffer-hoist")
    memory_pool_text = _dump_stage_text_by_marker(tmp_path, "memory-pool")
    second_buffer_hoist_text = _dump_stage_text_by_marker(tmp_path, "symbol-buffer-hoist", occurrence=2)
    assert memory_plan_text.startswith("memory-plan\n")
    assert "dma.free" in memory_plan_text
    assert arch_parallelize_text.startswith("arch-parallelize\n")
    assert "arch.get_block_id" in arch_parallelize_text
    assert "symbol.const 2" in arch_parallelize_text
    assert first_buffer_hoist_text.startswith("symbol-buffer-hoist\n")
    assert "symbol.for" in first_buffer_hoist_text
    assert memory_pool_text.startswith("memory-pool\n")
    assert "arch.get_dynamic_memory" in memory_pool_text
    assert "dma.view" in memory_pool_text
    assert "dma.reshape" in memory_pool_text
    assert "dma.alloc" not in memory_pool_text
    assert "dma.free" not in memory_pool_text
    assert second_buffer_hoist_text.startswith("symbol-buffer-hoist\n")
    assert "arch.get_dynamic_memory" in second_buffer_hoist_text
    assert "dma.alloc" not in second_buffer_hoist_text
    assert "dma.free" not in second_buffer_hoist_text
    first_view_index = second_buffer_hoist_text.index('"dma.view"')
    first_reshape_index = second_buffer_hoist_text.index('"dma.reshape"', first_view_index)
    outer_for_index = second_buffer_hoist_text.index("symbol.for", first_reshape_index)
    inner_for_index = second_buffer_hoist_text.index("symbol.for", outer_for_index + len("symbol.for"))
    assert first_view_index < first_reshape_index < outer_for_index < inner_for_index


def test_npu_demo_lowering_pipeline_multi_buffer_static_dump_uses_ring_and_pool(tmp_path: Path) -> None:
    """验证静态 tile matmul dump 经过 multi-buffer 后生成 DMA ring。

    功能说明:
    - 使用公开 `set_dump_dir(...)` 与公开 pipeline builder 观察 `multi-buffer` 与 `memory-pool` stage。
    - 静态 tile 让 `LowerDmaMemoryHierarchyPass` 产生可计算 byte size 的 staging buffer。
    - 断言 memory-pool 后 ring backing 已由 dynamic memory/view/reshape 承接，且不残留 alloc/free。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k multi_buffer_static_dump
    """

    lhs = Memory([8, 8], NumericType.Float32)
    rhs = Memory([8, 8], NumericType.Float32)
    out = Memory([8, 8], NumericType.Float32)
    module = mlir_gen(matmul_kernel, lhs, rhs, out, SymbolDim(4), SymbolDim(4))
    pipeline = build_npu_demo_lowering_pipeline()

    set_dump_dir(tmp_path)
    try:
        pipeline.run(module)
    finally:
        reset_config()

    multi_buffer_text = _dump_stage_text_by_marker(tmp_path, "multi-buffer")
    memory_pool_text = _dump_stage_text_by_marker(tmp_path, "memory-pool")
    assert multi_buffer_text.startswith("multi-buffer\n")
    assert "dma.make_ring" in multi_buffer_text
    assert "dma.current_ring" in multi_buffer_text
    assert "dma.advance_ring" in multi_buffer_text
    assert memory_pool_text.startswith("memory-pool\n")
    assert "arch.get_dynamic_memory" in memory_pool_text
    assert "dma.view" in memory_pool_text
    assert "dma.reshape" in memory_pool_text
    assert "dma.make_ring" in memory_pool_text
    assert "dma.current_ring" in memory_pool_text
    assert "dma.advance_ring" in memory_pool_text
    assert "dma.alloc" not in memory_pool_text
    assert "dma.free" not in memory_pool_text
    assert "dma.make_ring" in str(module)
    assert "dma.alloc" not in str(module)
    assert "dma.free" not in str(module)


def test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain() -> None:
    """验证公开 npu_demo lowering -> gen_kernel 链路保留 tile 符号参数。"""
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    tile_m = SymbolDim("TILE_M")
    tile_n = SymbolDim("TILE_N")

    module = mlir_gen(matmul_kernel, lhs, rhs, out, tile_m, tile_n)
    pipeline = build_npu_demo_lowering_pipeline()
    pipeline.run(module)
    module_text = str(module)
    set_target("npu_demo")
    try:
        source = gen_kernel(module, EmitCContext())
    finally:
        reset_config()

    assert "template = T1" in module_text
    assert "template = T2" in module_text
    assert "template = T3" in module_text
    assert "arch.get_dynamic_memory" in module_text
    assert "dma.view" in module_text
    assert "dma.reshape" in module_text
    assert "dma.alloc" not in module_text
    assert "allalloc" not in module_text
    assert "void matmul_kernel(" in source
    assert "S_INT _cost_DMA1_matmul_kernel_device(" not in source
    assert "S_INT _cost_MAC_matmul_kernel_device(" not in source
    assert "template <typename" in source
    assert ", long long arg3, long long arg4" in source
    assert "static void matmul_kernel_device(" in source
    assert "npu_demo::KernelContext& ctx" not in source
    assert ", S_INT arg3, S_INT arg4" in source
    assert "npu_demo::launch<c_0, c_1, c_2, c_3>(matmul_kernel_device<" in source
    assert "arg0, arg1, arg2, arg3, arg4);" in source
    assert "get_dynamic_memory" in source
    assert ".view<" in source or ".template view<" in source
