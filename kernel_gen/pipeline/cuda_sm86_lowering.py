"""cuda-sm86-lowering pipeline.


功能说明:
- 提供 `cuda-sm86-lowering` pipeline 的 builder。
- 固定 CUDA SM86 首版 lowering 顺序，复用通用 NN / tile / tuning / outline 能力。
- 明确不接入 `MemoryPoolPass(rewrite=True)`，避免把 TLM fragment 语义改写为动态 byte pool。
- 通过 registry 装饰器完成 pipeline 注册。

API 列表:
- `build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

使用示例:
- from kernel_gen.pipeline import build_cuda_sm86_lowering_pipeline
- pm = build_cuda_sm86_lowering_pipeline({"target": "cuda_sm86"})
- lowered = pm.run(module)

关联文件:
- spec: [spec/pass/pipeline/cuda_sm86_lowering.md](spec/pass/pipeline/cuda_sm86_lowering.md)
- test: [test/passes/pipeline/test_cuda_sm86_lowering.py](test/passes/pipeline/test_cuda_sm86_lowering.py)
- 功能实现: [kernel_gen/pipeline/cuda_sm86_lowering.py](kernel_gen/pipeline/cuda_sm86_lowering.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.transforms.canonicalize import CanonicalizePass
from xdsl.transforms.common_subexpression_elimination import CommonSubexpressionElimination

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
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
from kernel_gen.passes.pass_manager import Pass, PassManager
from kernel_gen.passes.producer_consumer_analysis import ProducerConsumerAnalysisPass
from kernel_gen.passes.registry import register_pipeline
from kernel_gen.passes.template_name.infer import TemplateNameInferPass
from kernel_gen.passes.tile.analysis import TileAnalysisPass
from kernel_gen.passes.tuning import KernelPatternAttachPass
from kernel_gen.passes.tuning import TransformApplyPass


class _CudaSm86ArchParallelizePass(Pass):
    """CUDA pipeline 内部 arch mapping 适配层。


    功能说明:
    - 优先调用公开 `ArchParallelizePass.apply(...)`，保持可支持 IR 的 CUDA block mapping。
    - 对 9 个 demo 中暂不被 standalone arch pass 支持的复杂 pattern region 保守 no-op，后续 generated source 仍按 CUDA target 生成具体 kernel。
    - 不改变 standalone `ArchParallelizePass` 的公开失败合同。

    使用示例:
    - pm.add_pass(_CudaSm86ArchParallelizePass("cuda_sm86"))
    """

    name = "arch-parallelize"

    def __init__(self, target: str) -> None:
        """初始化 CUDA arch mapping 适配层。


        功能说明:
        - 创建内部公开 pass 实例并固定 `parallel_level="block"`。
        - 该 wrapper 仅服务 `cuda-sm86-lowering` pipeline，不注册为独立公开 pass。

        使用示例:
        - arch_pass = _CudaSm86ArchParallelizePass("cuda_sm86")
        """

        super().__init__()
        self.delegate = ArchParallelizePass(target=target, parallel_level="block")

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 CUDA arch mapping 或保守 no-op。


        功能说明:
        - 调用公开 `ArchParallelizePass.apply(...)` 处理可映射 IR。
        - 仅当 standalone pass 报 `unsupported loop structure` 时保守跳过，避免 9 个现有 demo 在 CUDA SourceBundle fallback 前被 pipeline 阻断。
        - 其它错误继续抛出，避免吞掉真实合同失败。

        使用示例:
        - arch_pass.apply(ctx, module)
        """

        try:
            self.delegate.apply(ctx, module)
        except KernelCodeError as exc:
            if "ArchParallelizePassError: unsupported loop structure" not in str(exc):
                raise


@register_pipeline("cuda-sm86-lowering")
def build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager:
    """构造 cuda-sm86-lowering pipeline。


    功能说明:
    - 返回 `PassManager(name="cuda-sm86-lowering")`。
    - 仅接受 `target` 选项，默认且唯一合法值为 `cuda_sm86`。
    - pass 顺序在第二段 symbol hoist 后执行 kernel aggregate / decompose，并在 producer-consumer 后直接进入
      `ArchParallelizePass(target="cuda_sm86", parallel_level="block")` 与 `AttachArchInformationPass`。
    - 不接入 `MemoryPoolPass(rewrite=True)`，保证 TLM1/TLM2/TLM3 不被改写成
      `arch.get_dynamic_memory + dma.reinterpret` byte pool 形态。

    使用示例:
    - pm = build_cuda_sm86_lowering_pipeline()
    - pm = build_cuda_sm86_lowering_pipeline({"target": "cuda_sm86"})
    """

    normalized_options = {} if options is None else dict(options)
    unknown = sorted(set(normalized_options) - {"target"})
    if unknown:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PIPELINE,
            f"cuda-sm86-lowering only accepts target option; got {', '.join(unknown)}",
        )
    target = normalized_options.get("target", "cuda_sm86")
    if target != "cuda_sm86":
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PIPELINE,
            "cuda-sm86-lowering target must be cuda_sm86",
        )

    pm = PassManager(name="cuda-sm86-lowering")
    pm.add_pass(InlinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(DecompassPass())
    pm.add_pass(NnLoweringPass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False))
    pm.add_pass(SymbolHoistPipelinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(TileAnalysisPass())
    pm.add_pass(KernelPatternAttachPass())
    pm.add_pass(TransformApplyPass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False))
    pm.add_pass(SymbolHoistPipelinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(KernelAggregatePass(matmul_acc=True))
    pm.add_pass(KernelDecomposePass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False))
    pm.add_pass(SymbolHoistPipelinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(ProducerConsumerAnalysisPass())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(_CudaSm86ArchParallelizePass(target=target))
    pm.add_pass(AttachArchInformationPass(target=target))
    pm.add_pass(OutlineDeviceKernelPass())
    pm.add_pass(TemplateNameInferPass())
    return pm
