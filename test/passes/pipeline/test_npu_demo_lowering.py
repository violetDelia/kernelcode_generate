"""npu demo lowering pipeline tests.


功能说明:
- 覆盖 kernel_gen/pipeline/npu_demo_lowering.py 的公开 builder 与顺序。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.pipeline.npu_demo_lowering --cov-branch --cov-report=term-missing test/passes/pipeline/test_npu_demo_lowering.py`

使用示例:
- pytest -q test/passes/pipeline/test_npu_demo_lowering.py

关联文件:
- 功能实现: kernel_gen/pipeline/npu_demo_lowering.py
- Spec 文档: spec/pass/pipeline/npu_demo_lowering.md
- 测试文件: test/passes/pipeline/test_npu_demo_lowering.py
"""

from __future__ import annotations

import importlib
import re
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

pipeline_module = importlib.import_module("kernel_gen.pipeline")
build_npu_demo_lowering_pipeline = pipeline_module.build_npu_demo_lowering_pipeline

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
PassManager = pass_manager_module.PassManager
InlinePass = importlib.import_module("kernel_gen.passes.inline").InlinePass
CommonSubexpressionElimination = importlib.import_module(
    "xdsl.transforms.common_subexpression_elimination"
).CommonSubexpressionElimination
CanonicalizePass = importlib.import_module("xdsl.transforms.canonicalize").CanonicalizePass
AttachArchInformationPass = importlib.import_module("kernel_gen.passes.attach_arch_information").AttachArchInformationPass
ArchParallelizePass = importlib.import_module("kernel_gen.passes.arch_parallelize").ArchParallelizePass
DecompassPass = importlib.import_module("kernel_gen.passes.decompass").DecompassPass
KernelAggregatePass = importlib.import_module("kernel_gen.passes.kernel_aggregate").KernelAggregatePass
KernelDecomposePass = importlib.import_module("kernel_gen.passes.kernel_decompose").KernelDecomposePass
KernelPatternAttachPass = importlib.import_module("kernel_gen.passes.kernel_pattern_attach").KernelPatternAttachPass
MemoryPlanPass = importlib.import_module("kernel_gen.passes.memory_plan").MemoryPlanPass
MemoryPoolPass = importlib.import_module("kernel_gen.passes.memory_pool").MemoryPoolPass
SymbolHoistPipelinePass = importlib.import_module("kernel_gen.passes.hoist").SymbolHoistPipelinePass
NnLoweringPass = importlib.import_module("kernel_gen.passes.lowering").NnLoweringPass
OutlineDeviceKernelPass = importlib.import_module("kernel_gen.passes.outline_device_kernel").OutlineDeviceKernelPass
ProducerConsumerAnalysisPass = importlib.import_module(
    "kernel_gen.passes.producer_consumer_analysis"
).ProducerConsumerAnalysisPass
SymbolBufferHoistPass = importlib.import_module("kernel_gen.passes.hoist.symbol_buffer_hoist").SymbolBufferHoistPass
TileAnalysisPass = importlib.import_module("kernel_gen.passes.tile.analysis").TileAnalysisPass
TemplateNameInferPass = importlib.import_module("kernel_gen.passes").TemplateNameInferPass
TransformApplyPass = importlib.import_module("kernel_gen.passes.transform_apply").TransformApplyPass

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


def _record_canonicalize(self, ctx: Context, target: ModuleOp) -> None:
    """记录 canonicalize pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 xDSL `CanonicalizePass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(CanonicalizePass, "apply", _record_canonicalize)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("canonicalize")


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


def _record_symbol_hoist_pipeline(self, ctx: Context, target: ModuleOp) -> None:
    """记录 symbol-hoist-pipeline pass 执行。

    功能说明:
    - 为 pipeline 顺序测试记录 `SymbolHoistPipelinePass.apply(...)` 被调用。
    - 验证公开 pipeline 不再直接串接三个旧 hoist pass。

    使用示例:
    - monkeypatch.setattr(SymbolHoistPipelinePass, "apply", _record_symbol_hoist_pipeline)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("symbol-hoist-pipeline")


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


def _record_kernel_pattern_attach(self, ctx: Context, target: ModuleOp) -> None:
    """记录 kernel-pattern-attach pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `KernelPatternAttachPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(KernelPatternAttachPass, "apply", _record_kernel_pattern_attach)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("kernel-pattern-attach")


def _record_transform_apply(self, ctx: Context, target: ModuleOp) -> None:
    """记录 transform-apply pass 执行。

    功能说明:
    - 为 pipeline 顺序测试记录 `TransformApplyPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(TransformApplyPass, "apply", _record_transform_apply)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("transform-apply")


def _record_kernel_aggregate(self, ctx: Context, target: ModuleOp) -> None:
    """记录 kernel-aggregate pass 执行。

    功能说明:
    - 为 pipeline 顺序测试记录 `KernelAggregatePass` 的 `matmul_acc` 固定参数。

    使用示例:
    - monkeypatch.setattr(KernelAggregatePass, "apply", _record_kernel_aggregate)
    """

    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append(f"kernel-aggregate:{self.matmul_acc}")


def _record_kernel_decompose(self, ctx: Context, target: ModuleOp) -> None:
    """记录 kernel-decompose pass 执行。

    功能说明:
    - 为 pipeline 顺序测试记录 `KernelDecomposePass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(KernelDecomposePass, "apply", _record_kernel_decompose)
    """

    _ = ctx
    _ = target
    pass_name = self.name
    if pass_name != "kernel-decompose":
        raise AssertionError(f"unexpected kernel decompose pass name: {pass_name}")
    _PIPELINE_PASS_ORDER.append(pass_name)


def _record_memory_plan(self, ctx: Context, target: ModuleOp) -> None:
    """记录 memory-plan pass 执行。


    功能说明:
    - 为 pipeline 顺序测试记录 `MemoryPlanPass` 的 `insert_free`、`reuse` 与 `fold` 固定参数。

    使用示例:
    - monkeypatch.setattr(MemoryPlanPass, "apply", _record_memory_plan)
    """

    _ = ctx
    _ = target
    insert_free = self.insert_free
    reuse = self.reuse
    fold = self.fold
    _PIPELINE_PASS_ORDER.append(f"memory-plan:{insert_free}:{reuse}:{fold}")


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


def _record_producer_consumer_analysis(self, ctx: Context, target: ModuleOp) -> None:
    """记录 producer-consumer-analysis pass 执行。

    功能说明:
    - 为 pipeline 顺序测试记录 `ProducerConsumerAnalysisPass.apply(...)` 被调用。

    使用示例:
    - monkeypatch.setattr(ProducerConsumerAnalysisPass, "apply", _record_producer_consumer_analysis)
    """

    _ = self
    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append("producer-consumer-analysis")


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


def _dump_stage_markers(dump_dir: Path) -> list[str]:
    """收集 dump 目录中所有阶段 marker。


    功能说明:
    - 将 `set_dump_dir(...)` 产生的 `*.mlir` 文件首行 marker 按文件名顺序收集为列表。
    - 用于断言相对顺序与目标序号，避免把验收绑定到内部 helper。

    使用示例:
    - markers = _dump_stage_markers(tmp_path)
    """

    return [path.read_text(encoding="utf-8").splitlines()[0] for path in sorted(dump_dir.glob("*.mlir"))]


def _dump_stage_index(dump_dir: Path, marker: str, *, occurrence: int = 1) -> int:
    """定位指定 marker 的第 `occurrence` 次出现对应的 dump 文件索引。


    功能说明:
    - 将 marker 绑定到实际 dump 文件顺序，便于断言目标阶段序号与相对位置。

    使用示例:
    - idx = _dump_stage_index(tmp_path, "arch-parallelize")
    """

    if occurrence < 1:
        raise AssertionError(f"dump stage occurrence must be positive; got {occurrence}")
    seen = 0
    for index, path in enumerate(sorted(dump_dir.glob("*.mlir")), start=1):
        text = path.read_text(encoding="utf-8")
        stage_marker = text.splitlines()[0] if text.splitlines() else ""
        if stage_marker != marker:
            continue
        seen += 1
        if seen == occurrence:
            return index
    raise AssertionError(f"dump stage marker {marker!r} occurrence {occurrence} not found")


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
# 对应功能实现文件路径: kernel_gen/pipeline/npu_demo_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/npu_demo_lowering.md
# 对应测试文件路径: test/passes/pipeline/test_npu_demo_lowering.py
def test_npu_demo_lowering_pipeline_builds_pass_manager() -> None:
    pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    assert isinstance(pm, PassManager)
    assert pm.name == "npu-demo-lowering"


# TC-PIPELINE-101
# 功能说明: 验证 npu-demo-lowering 的固定顺序包含三次 memory-plan、四次 CSE、五次 canonicalize、pre-pool producer-consumer-analysis 和 late attach。
# 测试目的: 锁定 dsl_run 新正向管线的最小公开顺序。
# 使用示例: pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k test_npu_demo_lowering_pipeline_pass_order
# 对应功能实现文件路径: kernel_gen/pipeline/npu_demo_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/npu_demo_lowering.md
# 对应测试文件路径: test/passes/pipeline/test_npu_demo_lowering.py
@pytest.mark.nn_lowering
def test_npu_demo_lowering_pipeline_pass_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _PIPELINE_PASS_ORDER.clear()
    monkeypatch.setattr(InlinePass, "apply", _record_inline)
    monkeypatch.setattr(CommonSubexpressionElimination, "apply", _record_cse)
    monkeypatch.setattr(CanonicalizePass, "apply", _record_canonicalize)
    monkeypatch.setattr(DecompassPass, "apply", _record_decompose)
    monkeypatch.setattr(NnLoweringPass, "apply", _record_lower)
    monkeypatch.setattr(SymbolHoistPipelinePass, "apply", _record_symbol_hoist_pipeline)
    monkeypatch.setattr(MemoryPlanPass, "apply", _record_memory_plan)
    monkeypatch.setattr(ArchParallelizePass, "apply", _record_arch_parallelize)
    monkeypatch.setattr(TileAnalysisPass, "apply", _record_tile_analysis)
    monkeypatch.setattr(KernelPatternAttachPass, "apply", _record_kernel_pattern_attach)
    monkeypatch.setattr(TransformApplyPass, "apply", _record_transform_apply)
    monkeypatch.setattr(KernelAggregatePass, "apply", _record_kernel_aggregate)
    monkeypatch.setattr(KernelDecomposePass, "apply", _record_kernel_decompose)
    monkeypatch.setattr(SymbolBufferHoistPass, "apply", _record_symbol_buffer_hoist)
    monkeypatch.setattr(MemoryPoolPass, "apply", _record_memory_pool)
    monkeypatch.setattr(ProducerConsumerAnalysisPass, "apply", _record_producer_consumer_analysis)
    monkeypatch.setattr(AttachArchInformationPass, "apply", _record_attach)
    monkeypatch.setattr(OutlineDeviceKernelPass, "apply", _record_outline)
    monkeypatch.setattr(TemplateNameInferPass, "apply", _record_template_name)

    pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    sentinel = ModuleOp([])
    assert pm.run(sentinel) is sentinel
    assert _PIPELINE_PASS_ORDER == [
        "inline",
        "cse",
        "canonicalize",
        "decompass",
        "lower-nn",
        "memory-plan:True:True:False",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "tile-analysis",
        "kernel-pattern-attach",
        "transform-apply",
        "memory-plan:True:True:False",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "kernel-aggregate:True",
        "kernel-decompose",
        "memory-plan:True:True:False",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "producer-consumer-analysis",
        "memory-pool:True:1024",
        "canonicalize",
        "arch-parallelize:npu_demo:block",
        "attach-arch-information",
        "outline-device-kernel",
        "template-name-infer",
    ]


def test_npu_demo_lowering_pipeline_rejects_unknown_option() -> None:
    with pytest.raises(KernelCodeError, match=r"^npu-demo-lowering only accepts target option; got only-kernel$"):
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
    monkeypatch.setattr(CanonicalizePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(DecompassPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(NnLoweringPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolHoistPipelinePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPlanPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TileAnalysisPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(KernelPatternAttachPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TransformApplyPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolBufferHoistPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPoolPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(ProducerConsumerAnalysisPass, "apply", _noop_pass_apply)
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
    monkeypatch.setattr(CanonicalizePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(DecompassPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(NnLoweringPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolHoistPipelinePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPlanPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TileAnalysisPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(KernelPatternAttachPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TransformApplyPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolBufferHoistPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPoolPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(ProducerConsumerAnalysisPass, "apply", _noop_pass_apply)
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


def test_npu_demo_lowering_pipeline_arch_parallelize_skips_entry_point_dispatcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证默认 pipeline 的 arch-parallelize 阶段跳过 `entry_point` host。

    功能说明:
    - 通过公开 pipeline builder 运行 host dispatcher + pattern 函数组合 IR。
    - 其它 pass 用公开 `apply(...)` 调用形态替换为空操作，隔离观察 arch 阶段的 host no-op 与 pattern rewrite。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k skips_entry_point_dispatcher
    """

    module_text = """builtin.module {
  func.func @entry_dispatch() attributes {entry_point} {
    %0 = tuner.select {patterns = [@entry_dispatch_pattern0]} : !symbol.int<#symbol.expr<pattern_id>>
    tuner.launch(@entry_dispatch_pattern0) : () -> ()
    func.return
  }
  func.func @entry_dispatch_pattern0() attributes {kernel.pattern_id = #builtin.int<0>} {
    %0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %1 = symbol.const 64 : !symbol.int<#symbol.expr<64>>
    %2 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    symbol.for %3 = %0 to %1 step %2 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<64>, step = #symbol.expr<4>>} {
      %4 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    }
    func.return
  }
}
"""
    module = Parser(build_default_context(), module_text).parse_module()
    monkeypatch.setattr(InlinePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(CommonSubexpressionElimination, "apply", _noop_pass_apply)
    monkeypatch.setattr(CanonicalizePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(DecompassPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(NnLoweringPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolHoistPipelinePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPlanPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TileAnalysisPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(KernelPatternAttachPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TransformApplyPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(SymbolBufferHoistPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(MemoryPoolPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(ProducerConsumerAnalysisPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(AttachArchInformationPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(OutlineDeviceKernelPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TemplateNameInferPass, "apply", _noop_pass_apply)

    pipeline = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    assert pipeline.run(module) is module

    lowered_text = str(module)
    host = lowered_text.split("func.func @entry_dispatch()", 1)[1].split(
        "func.func @entry_dispatch_pattern0()",
        1,
    )[0]
    pattern = lowered_text.split("func.func @entry_dispatch_pattern0()", 1)[1]
    assert "attributes {entry_point}" in host
    assert "tuner.launch(@entry_dispatch_pattern0" in host
    assert "arch.get_block_id" not in host
    assert "symbol.ne" not in host
    assert "scf.if" not in host
    assert "arch.get_block_id" in pattern


def test_npu_demo_lowering_pipeline_dynamic_acc_kernel_decompose_dump_shows_lifecycle_and_pool(
    tmp_path: Path,
) -> None:
    """验证 npu-demo-lowering 真实中间态包含 memory-plan 生命周期与 memory-pool 改写。


    功能说明:
    - 通过公开 `set_dump_dir(...)` 与公开 pipeline builder 观察 pass dump。
    - 按 pass marker 查找三段 `memory-plan`、三段 `symbol-hoist-pipeline` 与 `memory-pool`，
      不依赖 dump 文件序号。
    - 断言 `kernel-aggregate` 与 `kernel-decompose` 位于第二段 hoist cleanup 后、
      第三段 memory-plan 前，且 producer stage
      仍保留 typed `dma.alloc` 形态。
    - 断言 `arch-parallelize` 位于 memory-pool 后的 `canonicalize` 之后，且 memory-pool 后没有第 5 个 CSE。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k dynamic_acc_kernel_decompose_dump
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
    second_memory_plan_text = _dump_stage_text_by_marker(tmp_path, "memory-plan", occurrence=2)
    third_memory_plan_text = _dump_stage_text_by_marker(tmp_path, "memory-plan", occurrence=3)
    first_symbol_hoist_text = _dump_stage_text_by_marker(tmp_path, "symbol-hoist-pipeline")
    second_symbol_hoist_text = _dump_stage_text_by_marker(tmp_path, "symbol-hoist-pipeline", occurrence=2)
    third_symbol_hoist_text = _dump_stage_text_by_marker(tmp_path, "symbol-hoist-pipeline", occurrence=3)
    kernel_aggregate_text = _dump_stage_text_by_marker(tmp_path, "kernel-aggregate")
    decompose_text = _dump_stage_text_by_marker(tmp_path, "kernel-decompose")
    producer_consumer_text = _dump_stage_text_by_marker(tmp_path, "producer-consumer-analysis")
    memory_pool_text = _dump_stage_text_by_marker(tmp_path, "memory-pool")
    post_pool_canonicalize_text = _dump_stage_text_by_marker(tmp_path, "canonicalize", occurrence=5)
    arch_parallelize_text = _dump_stage_text_by_marker(tmp_path, "arch-parallelize")
    attach_text = _dump_stage_text_by_marker(tmp_path, "attach-arch-information")
    outline_text = _dump_stage_text_by_marker(tmp_path, "outline-device-kernel")
    markers = _dump_stage_markers(tmp_path)
    assert memory_plan_text.startswith("memory-plan\n")
    assert "dma.free" in memory_plan_text
    assert first_symbol_hoist_text.startswith("symbol-hoist-pipeline\n")
    assert "symbol.for" in first_symbol_hoist_text
    assert second_memory_plan_text.startswith("memory-plan\n")
    assert "dma.free" in second_memory_plan_text
    assert second_symbol_hoist_text.startswith("symbol-hoist-pipeline\n")
    assert kernel_aggregate_text.startswith("kernel-aggregate\n")
    assert decompose_text.startswith("kernel-decompose\n")
    assert '"kernel.matmul_fusion"' not in decompose_text
    assert "acc = true" not in decompose_text
    assert "acc = false" not in decompose_text
    assert '"kernel.matmul"' in decompose_text
    assert third_memory_plan_text.startswith("memory-plan\n")
    assert third_symbol_hoist_text.startswith("symbol-hoist-pipeline\n")
    assert producer_consumer_text.startswith("producer-consumer-analysis\n")
    assert "dma.alloc" in producer_consumer_text
    assert "!nn.memory" in producer_consumer_text
    assert "arch.get_dynamic_memory" not in producer_consumer_text
    assert memory_pool_text.startswith("memory-pool\n")
    assert "arch.get_dynamic_memory" in memory_pool_text
    assert "dma.reinterpret" in memory_pool_text
    assert "dma.alloc" not in memory_pool_text
    assert "dma.free" not in memory_pool_text
    assert post_pool_canonicalize_text.startswith("canonicalize\n")
    assert arch_parallelize_text.startswith("arch-parallelize\n")
    assert "arch.get_block_id" in arch_parallelize_text
    assert "symbol.const 2" in arch_parallelize_text
    assert attach_text.startswith("attach-arch-information\n")
    assert "arch.get_dynamic_memory" in attach_text
    assert "!nn.memory<[#C2097152]" in attach_text
    assert outline_text.startswith("outline-device-kernel\n")
    assert _dump_stage_index(tmp_path, "cse", occurrence=1) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=1)
    assert _dump_stage_index(tmp_path, "cse", occurrence=2) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=2)
    assert _dump_stage_index(tmp_path, "cse", occurrence=3) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=3)
    assert _dump_stage_index(tmp_path, "cse", occurrence=4) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=4)
    assert markers.count("cse") == 4
    assert _dump_stage_index(tmp_path, "memory-plan", occurrence=1) == 7
    assert _dump_stage_index(tmp_path, "symbol-hoist-pipeline", occurrence=1) == 8
    assert _dump_stage_index(tmp_path, "symbol-hoist-pipeline", occurrence=1) + 1 == _dump_stage_index(
        tmp_path, "cse", occurrence=2
    )
    assert _dump_stage_index(tmp_path, "cse", occurrence=2) + 1 == _dump_stage_index(
        tmp_path, "canonicalize", occurrence=2
    )
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=2) == 10
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=2) + 1 == _dump_stage_index(
        tmp_path, "tile-analysis"
    )
    assert _dump_stage_index(tmp_path, "tile-analysis") == 11
    assert _dump_stage_index(tmp_path, "kernel-pattern-attach") == 12
    assert _dump_stage_index(tmp_path, "transform-apply") == 13
    assert _dump_stage_index(tmp_path, "memory-plan", occurrence=2) == 14
    assert _dump_stage_index(tmp_path, "symbol-hoist-pipeline", occurrence=2) == 15
    assert _dump_stage_index(tmp_path, "cse", occurrence=3) == 16
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=3) == 17
    assert _dump_stage_index(tmp_path, "kernel-aggregate") == 18
    assert _dump_stage_index(tmp_path, "kernel-decompose") == 19
    assert _dump_stage_index(tmp_path, "memory-plan", occurrence=3) == 20
    assert _dump_stage_index(tmp_path, "symbol-hoist-pipeline", occurrence=3) == 21
    assert _dump_stage_index(tmp_path, "cse", occurrence=4) == 22
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=4) == 23
    assert _dump_stage_index(tmp_path, "producer-consumer-analysis") == 24
    assert _dump_stage_index(tmp_path, "memory-pool") == 25
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=5) == 26
    assert _dump_stage_index(tmp_path, "arch-parallelize") == 27
    assert _dump_stage_index(tmp_path, "attach-arch-information") == 28
    assert _dump_stage_index(tmp_path, "outline-device-kernel") == 29
    assert _dump_stage_index(tmp_path, "template-name-infer") == 30
    assert markers.count("attach-arch-information") == 1
    assert markers.count("symbol-hoist-pipeline") == 3
    assert "dma-alias-to-reinterpret" not in markers
    assert "symbol-loop-hoist" not in markers
    assert "hoist-dma-alias-ops" not in markers
    assert "lower-dma-memory-hierarchy" not in markers
    assert "multi-buffer" not in markers
    assert markers[6:11] == [
        "memory-plan",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "tile-analysis",
    ]
    assert markers[11:17] == [
        "kernel-pattern-attach",
        "transform-apply",
        "memory-plan",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
    ]
    assert markers[17:28] == [
        "kernel-aggregate",
        "kernel-decompose",
        "memory-plan",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "producer-consumer-analysis",
        "memory-pool",
        "canonicalize",
        "arch-parallelize",
        "attach-arch-information",
    ]


def test_npu_demo_lowering_pipeline_static_dump_uses_pool_without_multi_buffer(tmp_path: Path) -> None:
    """验证静态 tile matmul dump 不接入 multi-buffer 且直接进入 memory-pool。

    功能说明:
    - 使用公开 `set_dump_dir(...)` 与公开 pipeline builder 观察 `transform-apply` 与 `memory-pool` stage。
    - 静态 tile 让 pattern 内 `TransformApplyPass` 执行 lower-dma-memory-hierarchy 并产生可计算 byte size 的 staging buffer。
    - 断言当前 npu-demo-lowering 不接入 `multi-buffer`，DMA staging 直接交给 memory-pool。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k static_dump_uses_pool_without_multi_buffer
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

    transform_apply_text = _dump_stage_text_by_marker(tmp_path, "transform-apply")
    kernel_aggregate_text = _dump_stage_text_by_marker(tmp_path, "kernel-aggregate")
    decompose_text = _dump_stage_text_by_marker(tmp_path, "kernel-decompose")
    producer_consumer_text = _dump_stage_text_by_marker(tmp_path, "producer-consumer-analysis")
    memory_pool_text = _dump_stage_text_by_marker(tmp_path, "memory-pool")
    arch_parallelize_text = _dump_stage_text_by_marker(tmp_path, "arch-parallelize")
    attach_text = _dump_stage_text_by_marker(tmp_path, "attach-arch-information")
    markers = _dump_stage_markers(tmp_path)
    assert transform_apply_text.startswith("transform-apply\n")
    assert "dma.make_ring" not in transform_apply_text
    assert "dma.current_ring" not in transform_apply_text
    assert "dma.advance_ring" not in transform_apply_text
    assert kernel_aggregate_text.startswith("kernel-aggregate\n")
    assert decompose_text.startswith("kernel-decompose\n")
    assert '"kernel.matmul_fusion"' not in decompose_text
    assert "acc = true" not in decompose_text
    assert "acc = false" not in decompose_text
    assert '"kernel.matmul"' in decompose_text
    assert producer_consumer_text.startswith("producer-consumer-analysis\n")
    assert "dma.alloc" in producer_consumer_text
    assert "arch.get_dynamic_memory" not in producer_consumer_text
    assert memory_pool_text.startswith("memory-pool\n")
    assert "arch.get_dynamic_memory" in memory_pool_text
    assert "dma.reinterpret" in memory_pool_text
    assert "dma.make_ring" not in memory_pool_text
    assert "dma.current_ring" not in memory_pool_text
    assert "dma.advance_ring" not in memory_pool_text
    assert "dma.alloc" not in memory_pool_text
    assert "dma.free" not in memory_pool_text
    assert "multi-buffer" not in markers
    assert "lower-dma-memory-hierarchy" not in markers
    assert _dump_stage_index(tmp_path, "transform-apply") + 1 == _dump_stage_index(
        tmp_path, "memory-plan", occurrence=2
    )
    assert _dump_stage_index(tmp_path, "memory-plan", occurrence=2) + 1 == _dump_stage_index(
        tmp_path, "symbol-hoist-pipeline", occurrence=2
    )
    assert _dump_stage_index(tmp_path, "symbol-hoist-pipeline", occurrence=2) + 1 == _dump_stage_index(
        tmp_path, "cse", occurrence=3
    )
    assert _dump_stage_index(tmp_path, "cse", occurrence=3) + 1 == _dump_stage_index(
        tmp_path, "canonicalize", occurrence=3
    )
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=3) + 1 == _dump_stage_index(
        tmp_path, "kernel-aggregate"
    )
    assert _dump_stage_index(tmp_path, "kernel-aggregate") + 1 == _dump_stage_index(
        tmp_path, "kernel-decompose"
    )
    assert _dump_stage_index(tmp_path, "kernel-decompose") + 1 == _dump_stage_index(
        tmp_path, "memory-plan", occurrence=3
    )
    assert _dump_stage_index(tmp_path, "memory-plan", occurrence=3) + 1 == _dump_stage_index(
        tmp_path, "symbol-hoist-pipeline", occurrence=3
    )
    assert _dump_stage_index(tmp_path, "symbol-hoist-pipeline", occurrence=3) + 1 == _dump_stage_index(
        tmp_path, "cse", occurrence=4
    )
    assert _dump_stage_index(tmp_path, "cse", occurrence=4) + 1 == _dump_stage_index(
        tmp_path, "canonicalize", occurrence=4
    )
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=4) + 1 == _dump_stage_index(
        tmp_path, "producer-consumer-analysis"
    )
    assert _dump_stage_index(tmp_path, "producer-consumer-analysis") + 1 == _dump_stage_index(
        tmp_path, "memory-pool"
    )
    assert markers.count("cse") == 4
    assert markers.count("symbol-hoist-pipeline") == 3
    assert "hoist-dma-alias-ops" not in markers
    assert _dump_stage_index(tmp_path, "memory-pool") + 1 == _dump_stage_index(
        tmp_path, "canonicalize", occurrence=5
    )
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=5) + 1 == _dump_stage_index(
        tmp_path, "arch-parallelize"
    )
    assert _dump_stage_index(tmp_path, "arch-parallelize") + 1 == _dump_stage_index(
        tmp_path, "attach-arch-information"
    )
    assert arch_parallelize_text.startswith("arch-parallelize\n")
    assert "arch.get_block_id" in arch_parallelize_text
    assert attach_text.startswith("attach-arch-information\n")
    assert "launch_block = #builtin.int<2>" in attach_text
    assert "arch.get_dynamic_memory" in attach_text
    assert "!nn.memory<[#C2097152]" in attach_text
    assert "dma.make_ring" not in str(module)
    assert "dma.alloc" not in str(module)
    assert "dma.free" not in str(module)


# TC-PIPELINE-115
# 功能说明: 验证 npu-demo-lowering dump 中 symbol-hoist-pipeline 阶段按组合 pattern 合同收口。
# 测试目的: 通过公开 dump marker 断言 P2 writer retarget、P1 alias descriptor 顺序和 symbol 外提事实。
# 使用示例: pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k symbol_hoist_pipeline_pattern
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_hoist_pipeline.py
# 对应 spec 文件路径: spec/pass/symbol_hoist_pipeline.md
# 对应测试文件路径: test/passes/pipeline/test_npu_demo_lowering.py
def test_npu_demo_lowering_pipeline_symbol_hoist_pipeline_pattern_dump(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证真实 pipeline dump 中 symbol-hoist-pipeline 的 pattern 事实。

    功能说明:
    - 通过公开 `set_dump_dir(...)` 与 `build_npu_demo_lowering_pipeline(...)` 生成真实 dump。
    - 不绑定固定 dump 编号，只按首行 marker 定位 `symbol-hoist-pipeline` stage。
    - 断言旧 `symbol-loop-hoist` 与 `hoist-dma-alias-ops` 的可观察结果在组合 pass stage 中出现。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k symbol_hoist_pipeline_pattern
    """

    matmul_demo = importlib.import_module("kernel.matmul.inputs_static_tile_static")
    out = Memory([166, 172], NumericType.Float32)
    lhs = Memory([166, 217], NumericType.Float32)
    rhs = Memory([217, 172], NumericType.Float32)
    bias = Memory([172], NumericType.Float32)
    module = mlir_gen(matmul_demo.matmul_inputs_static_tile_static_kernel, out, lhs, rhs, bias)
    pipeline = build_npu_demo_lowering_pipeline()
    monkeypatch.setattr(ArchParallelizePass, "apply", _noop_pass_apply)
    monkeypatch.setattr(ProducerConsumerAnalysisPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(AttachArchInformationPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(OutlineDeviceKernelPass, "apply", _noop_pass_apply)
    monkeypatch.setattr(TemplateNameInferPass, "apply", _noop_pass_apply)

    set_dump_dir(tmp_path)
    try:
        pipeline.run(module)
    finally:
        reset_config()

    first_hoist_text = _dump_stage_text_by_marker(tmp_path, "symbol-hoist-pipeline")
    final_hoist_text = _dump_stage_text_by_marker(tmp_path, "symbol-hoist-pipeline", occurrence=3)
    markers = _dump_stage_markers(tmp_path)
    p1_alias_before_consumer = re.search(
        r'(?P<alias>%\d+) = "dma\.reinterpret"\([^\n]+\)\s+<\{[^\n]*\}> : [^\n]+\n'
        r'\s+%\d+ = "dma\.deslice"\(%\d+, (?P=alias),',
        final_hoist_text,
    )
    broadcast_flat_source = re.search(
        r'(?P<flat>%\d+) = "dma\.alloc"\(\) <\{[^}]+\}> : \(\) -> '
        r'!nn\.memory<\[#C56\], \[#C1\], f32, #nn\.space<tsm>>'
        r'[\s\S]+?"dma\.fill"\((?P=flat), %\d+\)'
        r'[\s\S]+?"dma\.broadcast"\(%\d+, (?P=flat)\)',
        final_hoist_text,
    )
    guard_index = final_hoist_text.index("memory.get_data")
    cast_index = final_hoist_text.index("symbol.cast")
    cond_index = final_hoist_text.index("symbol.ne")
    first_loop_index = final_hoist_text.index("symbol.for")

    assert first_hoist_text.startswith("symbol-hoist-pipeline\n")
    assert final_hoist_text.startswith("symbol-hoist-pipeline\n")
    assert markers.count("symbol-hoist-pipeline") == 3
    assert "symbol-loop-hoist" not in markers
    assert "hoist-dma-alias-ops" not in markers
    assert guard_index < cast_index < cond_index < first_loop_index
    assert final_hoist_text.index("arith.constant") < first_loop_index
    assert p1_alias_before_consumer is not None
    assert broadcast_flat_source is not None
    assert "source_low" not in final_hoist_text
    assert "target_low" not in final_hoist_text
    assert "DmaViewDesliceGroupingPattern" not in final_hoist_text


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
    assert "dma.reinterpret" in module_text
    assert "dma.alloc" not in module_text
    assert "allalloc" not in module_text
    assert "void matmul_kernel(" in source
    assert "S_INT _cost_DMA1_matmul_kernel_device(" not in source
    assert "S_INT _cost_MAC_matmul_kernel_device(" not in source
    assert "template <typename" in source
    assert ", S_INT arg3, S_INT arg4" in source
    assert "void matmul_kernel_pattern0_device(" in source
    assert "void matmul_kernel_pattern1_device(" in source
    assert "npu_demo::KernelContext& ctx" not in source
    assert ", S_INT arg3, S_INT arg4" in source
    assert "npu_demo::launch<" in source
    assert "(matmul_kernel_pattern0_device<" in source
    assert "(matmul_kernel_pattern1_device<" in source
    assert "arg0, arg1, arg2, arg3, arg4);" in source
    assert "get_dynamic_memory" in source
    assert "reinterpret_cast" in source
