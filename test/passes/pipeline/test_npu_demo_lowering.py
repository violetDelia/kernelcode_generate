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
AttachArchInformationPass = importlib.import_module("kernel_gen.passes.arch.attach_arch_information").AttachArchInformationPass
ArchParallelizePass = importlib.import_module("kernel_gen.passes.arch.arch_parallelize").ArchParallelizePass
DecompassPass = importlib.import_module("kernel_gen.passes.decompass").DecompassPass
KernelAggregatePass = importlib.import_module("kernel_gen.passes.kernel.kernel_aggregate").KernelAggregatePass
KernelDecomposePass = importlib.import_module("kernel_gen.passes.kernel.kernel_decompose").KernelDecomposePass
KernelPatternAttachPass = importlib.import_module("kernel_gen.passes.tuning.kernel_pattern_attach").KernelPatternAttachPass
MemoryPlanPass = importlib.import_module("kernel_gen.passes.memory.memory_plan").MemoryPlanPass
MemoryPoolPass = importlib.import_module("kernel_gen.passes.memory.memory_pool").MemoryPoolPass
MultiBufferPass = importlib.import_module("kernel_gen.passes.memory.multi_buffer").MultiBufferPass
SymbolHoistPipelinePass = importlib.import_module("kernel_gen.passes.hoist").SymbolHoistPipelinePass
NnLoweringPass = importlib.import_module("kernel_gen.passes.lowering").NnLoweringPass
OutlineDeviceKernelPass = importlib.import_module("kernel_gen.passes.tuning.outline_device_kernel").OutlineDeviceKernelPass
ProducerConsumerAnalysisPass = importlib.import_module(
    "kernel_gen.passes.producer_consumer_analysis"
).ProducerConsumerAnalysisPass
SymbolBufferHoistPass = importlib.import_module("kernel_gen.passes.hoist.symbol_buffer_hoist").SymbolBufferHoistPass
TileAnalysisPass = importlib.import_module("kernel_gen.passes.tile.analysis").TileAnalysisPass
TemplateNameInferPass = importlib.import_module("kernel_gen.passes").TemplateNameInferPass
TransformApplyPass = importlib.import_module("kernel_gen.passes.tuning.transform_apply").TransformApplyPass

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
    - 为 pipeline 顺序测试记录 `MemoryPlanPass` 的 `insert_free`、`reuse`、`fold` 与 `auto_pad` 固定参数。

    使用示例:
    - monkeypatch.setattr(MemoryPlanPass, "apply", _record_memory_plan)
    """

    _ = ctx
    _ = target
    insert_free = self.insert_free
    reuse = self.reuse
    fold = self.fold
    auto_pad = self.auto_pad
    _PIPELINE_PASS_ORDER.append(f"memory-plan:{insert_free}:{reuse}:{fold}:{auto_pad}")


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


def _record_multi_buffer(self, ctx: Context, target: ModuleOp) -> None:
    """记录 multi-buffer pass 执行。

    功能说明:
    - 为 pipeline 顺序测试记录 `MultiBufferPass.apply(...)` 被调用。
    - 锁定 pipeline 传入的 `memory_stage=2` 与 `target=npu_demo`。

    使用示例:
    - monkeypatch.setattr(MultiBufferPass, "apply", _record_multi_buffer)
    """

    _ = ctx
    _ = target
    _PIPELINE_PASS_ORDER.append(f"multi-buffer:{self.memory_stage}:{self.target}")
    assert self.memory_stage == 2
    assert self.target == "npu_demo"


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
        if stage_marker.split("{", 1)[0] != marker:
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

    markers: list[str] = []
    for path in sorted(dump_dir.glob("*.mlir")):
        raw_marker = path.read_text(encoding="utf-8").splitlines()[0]
        markers.append(raw_marker.split("{", 1)[0])
    return markers


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
        if stage_marker.split("{", 1)[0] != marker:
            continue
        seen += 1
        if seen == occurrence:
            return index
    raise AssertionError(f"dump stage marker {marker!r} occurrence {occurrence} not found")


def _pattern_function_text(stage_text: str, function_name: str) -> str:
    """截取 dump 中指定 pattern/device 函数文本。

    功能说明:
    - 只按公开 dump 文本中的 `func.func @name` 边界截取。
    - 用于 pipeline 级测试观察 alloc/free 与 consumer 的相对位置。

    使用示例:
    - text = _pattern_function_text(stage_text, "matmul_kernel_pattern0")
    """

    start = stage_text.index(f"func.func @{function_name}")
    next_func = stage_text.find("\n  func.func @", start + 1)
    if next_func == -1:
        return stage_text[start:]
    return stage_text[start:next_func]


def _assert_alloc_free_at_pattern_function_scope(function_text: str) -> None:
    """断言 `dma.alloc/free` 均位于 pattern 函数首层。

    功能说明:
    - 通过 xDSL dump 的稳定缩进判断 alloc/free 不在 `symbol.for` 或 `scf.if` region 内。
    - 首层缩进允许 alloc 在首个 supported loop 前、free 在 loop 后。
    - 同时要求当前 pattern 函数实际保留 typed lifecycle op，避免空检查误通过。

    使用示例:
    - _assert_alloc_free_at_pattern_function_scope(pattern_text)
    """

    saw_alloc = False
    saw_free = False
    for line in function_text.splitlines():
        if '"dma.alloc"' not in line and '"dma.free"' not in line:
            continue
        if not line.startswith("    ") or line.startswith("      "):
            raise AssertionError(f"dma lifecycle op must be at pattern function scope: {line}")
        saw_alloc = saw_alloc or '"dma.alloc"' in line
        saw_free = saw_free or '"dma.free"' in line
    if not saw_alloc or not saw_free:
        raise AssertionError("expected pattern function scope dma.alloc and dma.free")


def _assert_kernel_matmul_consumes_logical_reinterpret(function_text: str) -> None:
    """断言 `kernel.matmul` out operand 来自 logical `dma.reinterpret` alias。

    功能说明:
    - 收集当前函数内 `dma.reinterpret` result。
    - 验证每个 `kernel.matmul` 的第一个 memory operand 使用 logical alias，而不是 padded backing alloc。

    使用示例:
    - _assert_kernel_matmul_consumes_logical_reinterpret(pattern_text)
    """

    reinterpret_results = set(re.findall(r'^\s*(%\w+) = "dma\.reinterpret"', function_text, flags=re.MULTILINE))
    matmul_operands = re.findall(r'"kernel\.matmul"\(([^)]*)\)', function_text)
    if not matmul_operands:
        raise AssertionError("expected at least one kernel.matmul op")
    for operands in matmul_operands:
        out_operand = operands.split(",", 1)[0].strip()
        if out_operand not in reinterpret_results:
            raise AssertionError(f"kernel.matmul out must use logical reinterpret alias; got {out_operand}")


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
# 功能说明: 验证 npu-demo-lowering 的固定顺序包含三次 memory-plan、五次 CSE、五次 canonicalize、pre-pool multi-buffer / producer-consumer-analysis 和 late attach。
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
    monkeypatch.setattr(MultiBufferPass, "apply", _record_multi_buffer)
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
        "memory-plan:True:True:False:True",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "tile-analysis",
        "kernel-pattern-attach",
        "transform-apply",
        "memory-plan:True:True:False:True",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "kernel-aggregate:True",
        "kernel-decompose",
        "memory-plan:True:True:False:True",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "multi-buffer:2:npu_demo",
        "producer-consumer-analysis",
        "memory-pool:True:1024",
        "cse",
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
    - 断言 `arch-parallelize` 位于 memory-pool 后的 `cse -> canonicalize` 之后。

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
    post_pool_cse_text = _dump_stage_text_by_marker(tmp_path, "cse", occurrence=5)
    post_pool_canonicalize_text = _dump_stage_text_by_marker(tmp_path, "canonicalize", occurrence=5)
    arch_parallelize_text = _dump_stage_text_by_marker(tmp_path, "arch-parallelize")
    attach_text = _dump_stage_text_by_marker(tmp_path, "attach-arch-information")
    outline_text = _dump_stage_text_by_marker(tmp_path, "outline-device-kernel")
    markers = _dump_stage_markers(tmp_path)
    assert memory_plan_text.splitlines()[0] == "memory-plan{insert_free=true fold=false reuse=true auto_pad=true}"
    assert "dma.free" in memory_plan_text
    assert first_symbol_hoist_text.splitlines()[0] == "symbol-hoist-pipeline{fold=true}"
    assert "symbol.for" in first_symbol_hoist_text
    assert second_memory_plan_text.splitlines()[0] == "memory-plan{insert_free=true fold=false reuse=true auto_pad=true}"
    assert "dma.free" in second_memory_plan_text
    assert second_symbol_hoist_text.splitlines()[0] == "symbol-hoist-pipeline{fold=true}"
    assert kernel_aggregate_text.splitlines()[0] == "kernel-aggregate{matmul_acc=true fold=true}"
    assert decompose_text.splitlines()[0] == "kernel-decompose{fold=true}"
    assert '"kernel.matmul_fusion"' not in decompose_text
    assert "acc = true" not in decompose_text
    assert "acc = false" not in decompose_text
    assert '"kernel.matmul"' in decompose_text
    assert third_memory_plan_text.splitlines()[0] == "memory-plan{insert_free=true fold=false reuse=true auto_pad=true}"
    assert third_symbol_hoist_text.splitlines()[0] == "symbol-hoist-pipeline{fold=true}"
    assert producer_consumer_text.splitlines()[0] == "producer-consumer-analysis{fold=true}"
    assert "dma.alloc" in producer_consumer_text
    assert "!nn.memory" in producer_consumer_text
    assert "arch.get_dynamic_memory" not in producer_consumer_text
    assert memory_pool_text.splitlines()[0] == "memory-pool{rewrite=true fold=true alignment=1024}"
    assert "arch.get_dynamic_memory" in memory_pool_text
    assert "dma.reinterpret" in memory_pool_text
    assert "dma.alloc" not in memory_pool_text
    assert "dma.free" not in memory_pool_text
    assert post_pool_cse_text.startswith("cse\n")
    assert post_pool_canonicalize_text.startswith("canonicalize\n")
    assert arch_parallelize_text.splitlines()[0] == 'arch-parallelize{target="npu_demo" parallel_level="block"}'
    assert "arch.get_block_id" in arch_parallelize_text
    assert "symbol.const 2" in arch_parallelize_text
    assert attach_text.splitlines()[0] == 'attach-arch-information{target="npu_demo" fold=true}'
    assert "arch.get_dynamic_memory" in attach_text
    assert "!nn.memory<[#C2097152]" in attach_text
    assert outline_text.splitlines()[0] == "outline-device-kernel{fold=true}"
    assert _dump_stage_index(tmp_path, "cse", occurrence=1) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=1)
    assert _dump_stage_index(tmp_path, "cse", occurrence=2) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=2)
    assert _dump_stage_index(tmp_path, "cse", occurrence=3) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=3)
    assert _dump_stage_index(tmp_path, "cse", occurrence=4) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=4)
    assert _dump_stage_index(tmp_path, "cse", occurrence=5) + 1 == _dump_stage_index(tmp_path, "canonicalize", occurrence=5)
    assert markers.count("cse") == 5
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
    assert _dump_stage_index(tmp_path, "multi-buffer") == 24
    assert _dump_stage_index(tmp_path, "producer-consumer-analysis") == 25
    assert _dump_stage_index(tmp_path, "memory-pool") == 26
    assert _dump_stage_index(tmp_path, "cse", occurrence=5) == 27
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=5) == 28
    assert _dump_stage_index(tmp_path, "arch-parallelize") == 29
    assert _dump_stage_index(tmp_path, "attach-arch-information") == 30
    assert _dump_stage_index(tmp_path, "outline-device-kernel") == 31
    assert _dump_stage_index(tmp_path, "template-name-infer") == 32
    assert markers.count("attach-arch-information") == 1
    assert markers.count("symbol-hoist-pipeline") == 3
    assert "dma-alias-to-reinterpret" not in markers
    assert "symbol-loop-hoist" not in markers
    assert "hoist-dma-alias-ops" not in markers
    assert "lower-dma-memory-hierarchy" not in markers
    assert markers.count("multi-buffer") == 1
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
    assert markers[17:30] == [
        "kernel-aggregate",
        "kernel-decompose",
        "memory-plan",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "multi-buffer",
        "producer-consumer-analysis",
        "memory-pool",
        "cse",
        "canonicalize",
        "arch-parallelize",
        "attach-arch-information",
    ]


def test_npu_demo_lowering_pipeline_static_dump_runs_multi_buffer_before_pool(tmp_path: Path) -> None:
    """验证静态 tile matmul dump 运行 multi-buffer 后再进入 memory-pool。

    功能说明:
    - 使用公开 `set_dump_dir(...)` 与公开 pipeline builder 观察 `transform-apply` 与 `memory-pool` stage。
    - 静态 tile 让 pattern 内 `TransformApplyPass` 执行 lower-dma-memory-hierarchy 并产生可计算 byte size 的 staging buffer。
    - 断言当前 npu-demo-lowering 在第三段 cleanup 后接入 `multi-buffer`；该 demo 不满足 direct staging pair 时允许 no-op。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k static_dump_runs_multi_buffer_before_pool
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
    multi_buffer_text = _dump_stage_text_by_marker(tmp_path, "multi-buffer")
    producer_consumer_text = _dump_stage_text_by_marker(tmp_path, "producer-consumer-analysis")
    memory_pool_text = _dump_stage_text_by_marker(tmp_path, "memory-pool")
    arch_parallelize_text = _dump_stage_text_by_marker(tmp_path, "arch-parallelize")
    attach_text = _dump_stage_text_by_marker(tmp_path, "attach-arch-information")
    markers = _dump_stage_markers(tmp_path)
    assert transform_apply_text.splitlines()[0] == "transform-apply{fold=true}"
    assert "dma.make_ring" not in transform_apply_text
    assert "dma.current_ring" not in transform_apply_text
    assert "dma.advance_ring" not in transform_apply_text
    assert kernel_aggregate_text.splitlines()[0] == "kernel-aggregate{matmul_acc=true fold=true}"
    assert decompose_text.splitlines()[0] == "kernel-decompose{fold=true}"
    assert '"kernel.matmul_fusion"' not in decompose_text
    assert "acc = true" not in decompose_text
    assert "acc = false" not in decompose_text
    assert '"kernel.matmul"' in decompose_text
    assert multi_buffer_text.splitlines()[0] == 'multi-buffer{memory_stage=2 fold=true target="npu_demo"}'
    assert "dma.alloc" in multi_buffer_text
    assert producer_consumer_text.splitlines()[0] == "producer-consumer-analysis{fold=true}"
    assert "dma.alloc" in producer_consumer_text
    assert "arch.get_dynamic_memory" not in producer_consumer_text
    assert memory_pool_text.splitlines()[0] == "memory-pool{rewrite=true fold=true alignment=1024}"
    assert "arch.get_dynamic_memory" in memory_pool_text
    assert "dma.reinterpret" in memory_pool_text
    assert "dma.make_ring" not in memory_pool_text
    assert "dma.current_ring" not in memory_pool_text
    assert "dma.advance_ring" not in memory_pool_text
    assert "dma.alloc" not in memory_pool_text
    assert "dma.free" not in memory_pool_text
    assert markers.count("multi-buffer") == 1
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
        tmp_path, "multi-buffer"
    )
    assert _dump_stage_index(tmp_path, "multi-buffer") + 1 == _dump_stage_index(
        tmp_path, "producer-consumer-analysis"
    )
    assert _dump_stage_index(tmp_path, "producer-consumer-analysis") + 1 == _dump_stage_index(
        tmp_path, "memory-pool"
    )
    assert markers.count("cse") == 5
    assert markers.count("symbol-hoist-pipeline") == 3
    assert "hoist-dma-alias-ops" not in markers
    assert _dump_stage_index(tmp_path, "memory-pool") + 1 == _dump_stage_index(
        tmp_path, "cse", occurrence=5
    )
    assert _dump_stage_index(tmp_path, "cse", occurrence=5) + 1 == _dump_stage_index(
        tmp_path, "canonicalize", occurrence=5
    )
    assert _dump_stage_index(tmp_path, "canonicalize", occurrence=5) + 1 == _dump_stage_index(
        tmp_path, "arch-parallelize"
    )
    assert _dump_stage_index(tmp_path, "arch-parallelize") + 1 == _dump_stage_index(
        tmp_path, "attach-arch-information"
    )
    assert arch_parallelize_text.splitlines()[0] == 'arch-parallelize{target="npu_demo" parallel_level="block"}'
    assert "arch.get_block_id" in arch_parallelize_text
    assert attach_text.splitlines()[0] == 'attach-arch-information{target="npu_demo" fold=true}'
    assert "launch_block = #builtin.int<2>" in attach_text
    assert "arch.get_dynamic_memory" in attach_text
    assert "!nn.memory<[#C2097152]" in attach_text
    assert "dma.make_ring" not in str(module)
    assert "dma.current_ring" not in str(module)
    assert "dma.advance_ring" not in str(module)
    assert "dma.alloc" not in str(module)
    assert "dma.free" not in str(module)


# TC-PASS-PIPELINE-NPU-DEMO-LOWERING-008
# 功能说明: 验证 static/static、static/dynamic、dynamic/dynamic matmul demo 的 alloc/free 在 final hoist 后位于 pattern 函数首层，并锁定 fill 完成态。
# 测试目的: 通过公开 demo kernel 与 dump marker 锁定 `memory-plan(auto_pad=true) -> symbol-hoist-pipeline -> cse -> canonicalize` 的 lifecycle 外提与 dead-fill 合同。
# 使用示例: pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k matmul_demo_allocs_hoist
# 对应功能实现文件路径: kernel_gen/pipeline/npu_demo_lowering.py
# 对应功能实现文件路径: kernel_gen/passes/hoist/symbol_buffer_hoist.py
# 对应 spec 文件路径: spec/pass/pipeline/npu_demo_lowering.md
# 对应 spec 文件路径: spec/pass/symbol_buffer_hoist.md
# 对应测试文件路径: test/passes/pipeline/test_npu_demo_lowering.py
def test_npu_demo_lowering_pipeline_matmul_demo_allocs_hoist_for_static_and_dynamic_tiles(tmp_path: Path) -> None:
    """验证三类 matmul demo 在 pipeline pre-pool typed IR 中完成 alloc/free 最外提。

    功能说明:
    - 使用公开 matmul demo kernel 与公开 `set_dump_dir(...)` 生成真实 pipeline dump。
    - 覆盖 static/static、static/dynamic、dynamic/dynamic 三类计划场景。
    - 断言第三段 `symbol-hoist-pipeline` 后 pattern 函数中 `dma.alloc/free` 均位于首层。
    - 断言后续 canonicalize 中 static/static 与 static/dynamic 不残留 dead fill，
      dynamic/dynamic 只允许保留 DU2-A 下非必删的 acc fill。
    - 断言三类 demo 中 `kernel.matmul` 继续消费 logical `dma.reinterpret` alias。

    使用示例:
    - pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k matmul_demo_allocs_hoist
    """

    static_static = importlib.import_module("kernel.matmul.inputs_static_tile_static")
    static_dynamic = importlib.import_module("kernel.matmul.inputs_static_tile_dynamic")
    dynamic_dynamic = importlib.import_module("kernel.matmul.inputs_dynamic_tile_dynamic")
    cases = (
        (
            "static_static",
            static_static.matmul_inputs_static_tile_static_kernel,
            (
                Memory([166, 172], NumericType.Float32),
                Memory([166, 217], NumericType.Float32),
                Memory([217, 172], NumericType.Float32),
                Memory([172], NumericType.Float32),
            ),
            "matmul_inputs_static_tile_static_kernel_pattern0",
            True,
            0,
        ),
        (
            "static_dynamic",
            static_dynamic.matmul_inputs_static_tile_dynamic_kernel,
            (
                Memory([197, 184], NumericType.Float32),
                Memory([197, 178], NumericType.Float32),
                Memory([178, 184], NumericType.Float32),
                Memory([184], NumericType.Float32),
                SymbolDim("TILE_H"),
                SymbolDim("TILE_W"),
                SymbolDim("TILE_K"),
            ),
            "matmul_inputs_static_tile_dynamic_kernel_pattern0",
            True,
            0,
        ),
        (
            "dynamic_dynamic",
            dynamic_dynamic.matmul_inputs_dynamic_tile_dynamic_kernel,
            (
                Memory(["H", "W"], NumericType.Float32),
                Memory(["H", "K"], NumericType.Float32),
                Memory(["K", "W"], NumericType.Float32),
                Memory(["W"], NumericType.Float32),
                SymbolDim("TILE_H"),
                SymbolDim("TILE_W"),
                SymbolDim("TILE_K"),
            ),
            "matmul_inputs_dynamic_tile_dynamic_kernel_pattern0",
            True,
            1,
        ),
    )

    for case_name, kernel_func, args, pattern_name, requires_logical_matmul, expected_fill_count in cases:
        case_dump_dir = tmp_path / case_name
        case_dump_dir.mkdir()
        module = mlir_gen(kernel_func, *args)
        pipeline = build_npu_demo_lowering_pipeline()

        set_dump_dir(case_dump_dir)
        try:
            pipeline.run(module)
        finally:
            reset_config()

        final_hoist_text = _dump_stage_text_by_marker(case_dump_dir, "symbol-hoist-pipeline", occurrence=3)
        post_decompose_canonicalize_text = _dump_stage_text_by_marker(case_dump_dir, "canonicalize", occurrence=4)
        memory_pool_text = _dump_stage_text_by_marker(case_dump_dir, "memory-pool")
        pattern_text = _pattern_function_text(final_hoist_text, pattern_name)
        canonical_pattern_text = _pattern_function_text(post_decompose_canonicalize_text, pattern_name)
        _assert_alloc_free_at_pattern_function_scope(pattern_text)
        assert '"kernel.matmul"' in pattern_text
        assert canonical_pattern_text.count('"dma.fill"') == expected_fill_count
        if expected_fill_count == 1:
            fill_targets = re.findall(r'"dma\.fill"\((%\w+),', canonical_pattern_text)
            matmul_outs = re.findall(r'"kernel\.matmul"\((%\w+),', canonical_pattern_text)
            assert fill_targets == matmul_outs[:1]
        assert '"dma.alloc"' not in memory_pool_text
        assert '"dma.free"' not in memory_pool_text
        if requires_logical_matmul:
            _assert_kernel_matmul_consumes_logical_reinterpret(canonical_pattern_text)


# TC-PIPELINE-115
# 功能说明: 验证 npu-demo-lowering dump 中 symbol-hoist-pipeline 阶段按组合 pattern 合同收口。
# 测试目的: 通过公开 dump marker 断言 alias descriptor 顺序、symbol 外提和 acc fill 删除事实。
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
    - 断言 kernel-decompose 后的后续 canonicalize 不再保留 acc 初始化 fill。

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
    post_decompose_canonicalize_text = _dump_stage_text_by_marker(tmp_path, "canonicalize", occurrence=4)
    final_pattern_text = _pattern_function_text(
        final_hoist_text,
        "matmul_inputs_static_tile_static_kernel_pattern0",
    )
    markers = _dump_stage_markers(tmp_path)
    reinterpret_results = set(re.findall(r'^\s*(%\w+) = "dma\.reinterpret"', final_pattern_text, flags=re.MULTILINE))
    output_deslice = re.search(r'"dma\.deslice"\(%0, (?P<source>%\w+),', final_pattern_text)
    broadcast = re.search(r'"dma\.broadcast"\(%\w+, (?P<source>%\w+)\)', final_pattern_text)
    guard_index = final_hoist_text.index("memory.get_data")
    cast_index = final_hoist_text.index("symbol.cast")
    cond_index = final_hoist_text.index("symbol.ne")
    first_loop_index = final_hoist_text.index("symbol.for")
    first_stage_loop_index = first_hoist_text.index("symbol.for")

    assert first_hoist_text.splitlines()[0] == "symbol-hoist-pipeline{fold=true}"
    assert final_hoist_text.splitlines()[0] == "symbol-hoist-pipeline{fold=true}"
    assert markers.count("symbol-hoist-pipeline") == 3
    assert "symbol-loop-hoist" not in markers
    assert "hoist-dma-alias-ops" not in markers
    assert guard_index < cast_index < cond_index < first_loop_index
    assert first_hoist_text.index("arith.constant") < first_stage_loop_index
    assert '"dma.fill"' in first_hoist_text
    assert '"dma.fill"' not in post_decompose_canonicalize_text
    assert output_deslice is not None
    assert output_deslice.group("source") in reinterpret_results
    assert broadcast is not None
    assert broadcast.group("source") in reinterpret_results
    _assert_alloc_free_at_pattern_function_scope(final_pattern_text)
    _assert_kernel_matmul_consumes_logical_reinterpret(final_pattern_text)
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

    assert 'template_name = "T1"' in module_text
    assert 'template_name = "T2"' in module_text
    assert 'template_name = "T3"' in module_text
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
    assert "npu_demo::KernelContext& ctx" in source
    assert "template <typename Context>" not in source
    assert "<npu_demo::KernelContext>" not in source
    assert ", S_INT arg3, S_INT arg4" in source
    assert "npu_demo::launch<" in source
    assert "npu_demo::launch<2, 1, 1, 0, matmul_kernel_pattern0_device<" in source
    assert "npu_demo::launch<2, 1, 1, 0, matmul_kernel_pattern1_device<" in source
    assert "(ctx, arg0, arg1, arg2, arg3, arg4);" in source
    assert "get_dynamic_memory" in source
    assert "reinterpret_cast" in source
