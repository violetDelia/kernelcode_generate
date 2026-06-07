"""npu-demo-lowering pipeline expectation.

功能说明:
- 验证 `npu-demo-lowering` 公开 pipeline builder 返回稳定命名的 `PassManager`。
- 锁定 `MultiBufferPass(memory_stage=2, target="npu_demo")` 位于第三段
  `symbol-hoist-pipeline -> cse -> canonicalize` 之后、`producer-consumer-analysis` 之前。
- 锁定 `memory-pool:True:1024 -> cse -> canonicalize` 的相邻顺序。
- 本 leaf 只覆盖本计划授权的 npu_demo pipeline 合同；不定义目录级 `expectation.pass.pipeline` 聚合入口。

API 列表:
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering`

关联文件:
- spec: [`spec/pass/pipeline/npu_demo_lowering.md`](../../../spec/pass/pipeline/npu_demo_lowering.md)
- test: [`test/passes/pipeline/test_npu_demo_lowering.py`](../../../test/passes/pipeline/test_npu_demo_lowering.py)
- 功能实现: [`kernel_gen/pipeline/npu_demo_lowering.py`](../../../kernel_gen/pipeline/npu_demo_lowering.py)
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pipeline_module = importlib.import_module("kernel_gen.pipeline")
build_npu_demo_lowering_pipeline = pipeline_module.build_npu_demo_lowering_pipeline

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
PassManager = pass_manager_module.PassManager
InlinePass = importlib.import_module("kernel_gen.passes.inline").InlinePass
CommonSubexpressionElimination = importlib.import_module(
    "xdsl.transforms.common_subexpression_elimination"
).CommonSubexpressionElimination
CanonicalizePass = importlib.import_module("xdsl.transforms.canonicalize").CanonicalizePass
DecompassPass = importlib.import_module("kernel_gen.passes.decompass").DecompassPass
NnLoweringPass = importlib.import_module("kernel_gen.passes.lowering").NnLoweringPass
MemoryPlanPass = importlib.import_module("kernel_gen.passes.memory_plan").MemoryPlanPass
SymbolHoistPipelinePass = importlib.import_module("kernel_gen.passes.hoist").SymbolHoistPipelinePass
TileAnalysisPass = importlib.import_module("kernel_gen.passes.tile.analysis").TileAnalysisPass
KernelPatternAttachPass = importlib.import_module("kernel_gen.passes.tuning.kernel_pattern_attach").KernelPatternAttachPass
TransformApplyPass = importlib.import_module("kernel_gen.passes.tuning.transform_apply").TransformApplyPass
KernelAggregatePass = importlib.import_module("kernel_gen.passes.kernel_aggregate").KernelAggregatePass
KernelDecomposePass = importlib.import_module("kernel_gen.passes.kernel_decompose").KernelDecomposePass
MultiBufferPass = importlib.import_module("kernel_gen.passes.multi_buffer").MultiBufferPass
ProducerConsumerAnalysisPass = importlib.import_module(
    "kernel_gen.passes.producer_consumer_analysis"
).ProducerConsumerAnalysisPass
MemoryPoolPass = importlib.import_module("kernel_gen.passes.memory_pool").MemoryPoolPass
ArchParallelizePass = importlib.import_module("kernel_gen.passes.arch_parallelize").ArchParallelizePass
AttachArchInformationPass = importlib.import_module("kernel_gen.passes.attach_arch_information").AttachArchInformationPass
OutlineDeviceKernelPass = importlib.import_module("kernel_gen.passes.outline_device_kernel").OutlineDeviceKernelPass
TemplateNameInferPass = importlib.import_module("kernel_gen.passes").TemplateNameInferPass

PIPELINE_PASS_ORDER: list[str] = []


def _record_pipeline_pass(self, ctx: Context, target: ModuleOp) -> None:
    """记录 npu-demo-lowering pipeline 中单个公开 pass 的执行。

    功能说明:
    - 使用各 pass 公开 `apply(...)` 入口的调用形态，只记录顺序与关键构造参数。
    - 避免读取 `PassManager` 私有 pass 列表，同时隔离无关 pass 对空 module 的实际重写。

    使用示例:
    - `MultiBufferPass.apply = _record_pipeline_pass`
    """

    _ = ctx
    _ = target
    if isinstance(self, InlinePass):
        PIPELINE_PASS_ORDER.append("inline")
    elif isinstance(self, CommonSubexpressionElimination):
        PIPELINE_PASS_ORDER.append("cse")
    elif isinstance(self, CanonicalizePass):
        PIPELINE_PASS_ORDER.append("canonicalize")
    elif isinstance(self, DecompassPass):
        PIPELINE_PASS_ORDER.append("decompass")
    elif isinstance(self, NnLoweringPass):
        PIPELINE_PASS_ORDER.append("lower-nn")
    elif isinstance(self, MemoryPlanPass):
        PIPELINE_PASS_ORDER.append(f"memory-plan:{self.insert_free}:{self.reuse}:{self.fold}:{self.auto_pad}")
    elif isinstance(self, SymbolHoistPipelinePass):
        PIPELINE_PASS_ORDER.append("symbol-hoist-pipeline")
    elif isinstance(self, TileAnalysisPass):
        PIPELINE_PASS_ORDER.append("tile-analysis")
    elif isinstance(self, KernelPatternAttachPass):
        PIPELINE_PASS_ORDER.append("kernel-pattern-attach")
    elif isinstance(self, TransformApplyPass):
        PIPELINE_PASS_ORDER.append("transform-apply")
    elif isinstance(self, KernelAggregatePass):
        PIPELINE_PASS_ORDER.append(f"kernel-aggregate:{self.matmul_acc}")
    elif isinstance(self, KernelDecomposePass):
        PIPELINE_PASS_ORDER.append(self.name)
    elif isinstance(self, MultiBufferPass):
        PIPELINE_PASS_ORDER.append(f"multi-buffer:{self.memory_stage}:{self.target}")
        assert self.memory_stage == 2
        assert self.target == "npu_demo"
    elif isinstance(self, ProducerConsumerAnalysisPass):
        PIPELINE_PASS_ORDER.append("producer-consumer-analysis")
    elif isinstance(self, MemoryPoolPass):
        PIPELINE_PASS_ORDER.append(f"memory-pool:{self.rewrite}:{self.alignment}")
    elif isinstance(self, ArchParallelizePass):
        PIPELINE_PASS_ORDER.append(f"arch-parallelize:{self.target}:{self.parallel_level}")
    elif isinstance(self, AttachArchInformationPass):
        PIPELINE_PASS_ORDER.append("attach-arch-information")
    elif isinstance(self, OutlineDeviceKernelPass):
        PIPELINE_PASS_ORDER.append("outline-device-kernel")
    elif isinstance(self, TemplateNameInferPass):
        PIPELINE_PASS_ORDER.append("template-name-infer")
    else:
        raise AssertionError(f"unexpected pass type: {type(self).__name__}")


def main() -> None:
    """运行 npu-demo-lowering pipeline expectation。

    功能说明:
- 构造公开 `npu-demo-lowering` pipeline，并通过 `PassManager.run(...)` 记录 pass 顺序。
- 验证 multi-buffer 阶段使用 `memory_stage=2` 和 `target=npu_demo`，且紧邻 producer-consumer-analysis 之前。
- 验证 memory-pool 阶段后接一轮 CSE，再进入 canonicalize。

    使用示例:
    - `main()`
    """

    patched_classes = (
        InlinePass,
        CommonSubexpressionElimination,
        CanonicalizePass,
        DecompassPass,
        NnLoweringPass,
        MemoryPlanPass,
        SymbolHoistPipelinePass,
        TileAnalysisPass,
        KernelPatternAttachPass,
        TransformApplyPass,
        KernelAggregatePass,
        KernelDecomposePass,
        MultiBufferPass,
        ProducerConsumerAnalysisPass,
        MemoryPoolPass,
        ArchParallelizePass,
        AttachArchInformationPass,
        OutlineDeviceKernelPass,
        TemplateNameInferPass,
    )
    original_apply = {pass_cls: pass_cls.apply for pass_cls in patched_classes}
    try:
        for pass_cls in patched_classes:
            pass_cls.apply = _record_pipeline_pass
        PIPELINE_PASS_ORDER.clear()
        pass_manager = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
        sentinel_module = ModuleOp([])
        assert isinstance(pass_manager, PassManager)
        assert pass_manager.name == "npu-demo-lowering"
        assert pass_manager.run(sentinel_module) is sentinel_module
    finally:
        for pass_cls, apply_func in original_apply.items():
            pass_cls.apply = apply_func

    expected_order = [
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
    assert PIPELINE_PASS_ORDER == expected_order, (
        "unexpected npu-demo-lowering order:\n"
        f"actual={PIPELINE_PASS_ORDER!r}\n"
        f"expected={expected_order!r}"
    )
    multi_buffer_index = PIPELINE_PASS_ORDER.index("multi-buffer:2:npu_demo")
    assert PIPELINE_PASS_ORDER[multi_buffer_index - 3 : multi_buffer_index] == [
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
    ]
    assert PIPELINE_PASS_ORDER[multi_buffer_index + 1] == "producer-consumer-analysis"
    memory_pool_index = PIPELINE_PASS_ORDER.index("memory-pool:True:1024")
    assert PIPELINE_PASS_ORDER[memory_pool_index + 1 : memory_pool_index + 3] == [
        "cse",
        "canonicalize",
    ]
    print("[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.")


if __name__ == "__main__":
    main()
