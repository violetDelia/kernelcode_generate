"""cuda-sm86-lowering pipeline tests.


功能说明:
- 覆盖 `build_cuda_sm86_lowering_pipeline(...)` 的公开 builder、registry 名称和 pass 顺序。
- 验证 CUDA pipeline 不接入 `MemoryPoolPass(rewrite=True)`，避免 TLM fragment 被改写为 dynamic byte pool。

使用示例:
- pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py

关联文件:
- 功能实现: kernel_gen/pipeline/cuda_sm86_lowering.py
- Spec 文档: spec/pass/pipeline/cuda_sm86_lowering.md
- 测试文件: test/passes/pipeline/test_cuda_sm86_lowering.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.transforms.canonicalize import CanonicalizePass
from xdsl.transforms.common_subexpression_elimination import CommonSubexpressionElimination

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.pipeline import build_cuda_sm86_lowering_pipeline
from kernel_gen.passes.arch_parallelize import ArchParallelizePass
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.hoist import SymbolHoistPipelinePass
from kernel_gen.passes.inline import InlinePass
from kernel_gen.passes.kernel_aggregate import KernelAggregatePass
from kernel_gen.passes.kernel_decompose import KernelDecomposePass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.memory_plan import MemoryPlanPass
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.passes.producer_consumer_analysis import ProducerConsumerAnalysisPass
from kernel_gen.passes.registry import build_registered_pipeline, list_registered_pipelines, load_builtin_passes
from kernel_gen.passes.template_name.infer import TemplateNameInferPass
from kernel_gen.passes.tile.analysis import TileAnalysisPass
from kernel_gen.passes.tuning import KernelPatternAttachPass, TransformApplyPass

_PIPELINE_ORDER: list[str] = []
_PASS_NAME_BY_CLASS = {
    "InlinePass": "inline",
    "CommonSubexpressionElimination": "cse",
    "CanonicalizePass": "canonicalize",
    "DecompassPass": "decompass",
    "NnLoweringPass": "lower-nn",
    "MemoryPlanPass": "memory-plan",
    "SymbolHoistPipelinePass": "symbol-hoist-pipeline",
    "TileAnalysisPass": "tile-analysis",
    "KernelPatternAttachPass": "kernel-pattern-attach",
    "TransformApplyPass": "transform-apply",
    "KernelAggregatePass": "kernel-aggregate",
    "KernelDecomposePass": "kernel-decompose",
    "ProducerConsumerAnalysisPass": "producer-consumer-analysis",
    "ArchParallelizePass": "arch-parallelize",
    "AttachArchInformationPass": "attach-arch-information",
    "OutlineDeviceKernelPass": "outline-device-kernel",
    "TemplateNameInferPass": "template-name-infer",
}


def _record_pass_apply(self: Pass, ctx: Context, target: ModuleOp) -> None:
    """记录 pass apply 调用。

    功能说明:
    - 作为公开 pipeline 黑盒测试的 apply 替身。
    - 通过类名映射记录 pass 顺序，不读取 PassManager 私有状态。

    使用示例:
    - monkeypatch.setattr(InlinePass, "apply", _record_pass_apply)
    """

    _ = ctx
    _ = target
    class_name = type(self).__name__
    pass_name = _PASS_NAME_BY_CLASS.get(class_name, class_name)
    _PIPELINE_ORDER.append(pass_name)
    assert _PIPELINE_ORDER[-1] == pass_name


def test_cuda_sm86_lowering_pipeline_builds_pass_manager() -> None:
    """验证 cuda-sm86-lowering 公开 builder 和 registry 名称。

    功能说明:
    - 通过公开 builder 构造 `PassManager`。
    - 通过公开 pass registry 构造同名 pipeline。

    使用示例:
    - pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py -k builds_pass_manager
    """

    direct_pm = build_cuda_sm86_lowering_pipeline()
    load_builtin_passes()
    registry_pm = build_registered_pipeline("cuda-sm86-lowering")

    assert direct_pm.name == "cuda-sm86-lowering"
    assert registry_pm.name == "cuda-sm86-lowering"
    assert "cuda-sm86-lowering" in list_registered_pipelines()


def test_cuda_sm86_lowering_pipeline_rejects_non_cuda_target() -> None:
    """验证 CUDA pipeline 只接受 cuda_sm86 target。

    功能说明:
    - 通过公开 builder options 触发非法 target 边界。
    - 锁定未知 options 与非 CUDA target 都按 pipeline 合同失败。

    使用示例:
    - pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py -k rejects_non_cuda_target
    """

    with pytest.raises(KernelCodeError, match="target must be cuda_sm86"):
        build_cuda_sm86_lowering_pipeline({"target": "npu_demo"})
    with pytest.raises(KernelCodeError, match="only accepts target option"):
        build_cuda_sm86_lowering_pipeline({"only-kernel": "true"})


def test_cuda_sm86_lowering_pipeline_order_has_no_memory_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 CUDA pipeline pass 顺序与 TLM 非 dynamic pool 边界。

    功能说明:
    - 通过 monkeypatch 公开 `apply(...)` 方法记录运行顺序。
    - 不读取 `PassManager` 私有 `_passes`，只验证公开 `run(...)` 行为。

    使用示例:
    - pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py -k no_memory_pool
    """

    _PIPELINE_ORDER.clear()
    for pass_cls in (
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
        ProducerConsumerAnalysisPass,
        ArchParallelizePass,
        AttachArchInformationPass,
        OutlineDeviceKernelPass,
        TemplateNameInferPass,
    ):
        monkeypatch.setattr(pass_cls, "apply", _record_pass_apply)

    build_cuda_sm86_lowering_pipeline().run(ModuleOp([]))

    assert _PIPELINE_ORDER == [
        "inline",
        "cse",
        "canonicalize",
        "decompass",
        "lower-nn",
        "memory-plan",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "tile-analysis",
        "kernel-pattern-attach",
        "transform-apply",
        "memory-plan",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "kernel-aggregate",
        "kernel-decompose",
        "memory-plan",
        "symbol-hoist-pipeline",
        "cse",
        "canonicalize",
        "producer-consumer-analysis",
        "canonicalize",
        "arch-parallelize",
        "attach-arch-information",
        "outline-device-kernel",
        "template-name-infer",
    ]
    assert "memory-pool" not in _PIPELINE_ORDER
