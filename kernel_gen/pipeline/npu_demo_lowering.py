"""npu-demo-lowering pipeline.


功能说明:
- 提供 `npu-demo-lowering` pipeline 的 builder。
- 固定 `dsl_run` 的 npu_demo 正向链路为
  `InlinePass -> CommonSubexpressionElimination -> CanonicalizePass -> DecompassPass -> NnLoweringPass -> MemoryPlanPass -> SymbolHoistPipelinePass -> CommonSubexpressionElimination -> CanonicalizePass -> TileAnalysisPass -> KernelPatternAttachPass -> TransformApplyPass -> MemoryPlanPass -> SymbolHoistPipelinePass -> CommonSubexpressionElimination -> CanonicalizePass -> KernelAggregatePass -> KernelDecomposePass -> MemoryPlanPass -> SymbolHoistPipelinePass -> CommonSubexpressionElimination -> CanonicalizePass -> MultiBufferPass -> ProducerConsumerAnalysisPass -> MemoryPoolPass -> CanonicalizePass -> ArchParallelizePass -> AttachArchInformationPass -> OutlineDeviceKernelPass -> TemplateNameInferPass`。
- 默认三段 `MemoryPlanPass(auto_pad=True)` 补齐 insert-free 生命周期并启用 padded backing / logical alias 改写，`MemoryPoolPass` 执行 dynamic backing 改写，template-name infer 在 outline 后写回 wrapper/body memory type 的 template name。
- `MultiBufferPass(memory_stage=2, target=target)` 在 memory-pool 前运行，target 非空时按 npu_demo target capacity 自动计算 ring num。
- 通过 registry 装饰器完成 pipeline 注册。

API 列表:
- `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

使用示例:
- from kernel_gen.pipeline import build_npu_demo_lowering_pipeline
- pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
- lowered = pm.run(module)

关联文件:
- spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
- test: [test/passes/pipeline/test_npu_demo_lowering.py](test/passes/pipeline/test_npu_demo_lowering.py)
- 功能实现: [kernel_gen/pipeline/npu_demo_lowering.py](kernel_gen/pipeline/npu_demo_lowering.py)
"""

from __future__ import annotations

from xdsl.transforms.canonicalize import CanonicalizePass
from xdsl.transforms.common_subexpression_elimination import CommonSubexpressionElimination

from kernel_gen.passes.arch.arch_parallelize import ArchParallelizePass
from kernel_gen.passes.arch.attach_arch_information import AttachArchInformationPass
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.hoist import SymbolHoistPipelinePass
from kernel_gen.passes.inline import InlinePass
from kernel_gen.passes.kernel.kernel_aggregate import KernelAggregatePass
from kernel_gen.passes.kernel.kernel_decompose import KernelDecomposePass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.memory.memory_plan import MemoryPlanPass
from kernel_gen.passes.memory.memory_pool import MemoryPoolPass
from kernel_gen.passes.memory.multi_buffer import MultiBufferPass
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import register_pipeline
from kernel_gen.passes.tuning.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.passes.producer_consumer_analysis import ProducerConsumerAnalysisPass
from kernel_gen.passes.template_name.infer import TemplateNameInferPass
from kernel_gen.passes.tile.analysis import TileAnalysisPass
from kernel_gen.passes.tuning import KernelPatternAttachPass
from kernel_gen.passes.tuning import TransformApplyPass


@register_pipeline("npu-demo-lowering")
def build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager:
    """构造 npu-demo-lowering pipeline。


    功能说明:
    - 返回 `PassManager(name="npu-demo-lowering")`。
    - 固定 pass 顺序为
      `InlinePass -> CommonSubexpressionElimination -> CanonicalizePass -> DecompassPass -> NnLoweringPass -> MemoryPlanPass -> SymbolHoistPipelinePass -> CommonSubexpressionElimination -> CanonicalizePass -> TileAnalysisPass -> KernelPatternAttachPass -> TransformApplyPass -> MemoryPlanPass -> SymbolHoistPipelinePass -> CommonSubexpressionElimination -> CanonicalizePass -> KernelAggregatePass -> KernelDecomposePass -> MemoryPlanPass -> SymbolHoistPipelinePass -> CommonSubexpressionElimination -> CanonicalizePass -> MultiBufferPass -> ProducerConsumerAnalysisPass -> MemoryPoolPass -> CanonicalizePass -> ArchParallelizePass -> AttachArchInformationPass -> OutlineDeviceKernelPass -> TemplateNameInferPass`。
    - `CommonSubexpressionElimination` 后均紧跟 xDSL `CanonicalizePass`，仅在本 pipeline 内清理 IR，
      不把 canonicalize 注册为仓库公开 pass。
    - `MemoryPlanPass` 固定以 `insert_free=True, reuse=True, fold=False, auto_pad=True` 运行三次；
      padded backing / logical alias、生命周期与可证明复用先补齐，再由 `SymbolHoistPipelinePass` 统一清理 symbol 与 alias。
    - `TileAnalysisPass` 紧跟第一段 post-buffer cleanup 后，只补充 tile 分析属性，不生成 tile 循环。
    - 三处 `SymbolHoistPipelinePass` 均以 alias 归一优先、再固定点运行
      `symbol-loop-hoist -> symbol-buffer-hoist -> hoist-dma-alias-ops` 的 combined pattern 清理 symbol 与 alias；
      `cse -> canonicalize` 作为 pipeline 独立阶段紧跟其后。
    - `KernelPatternAttachPass` 在 `TileAnalysisPass` 后生成 host dispatcher 与两个 pattern 函数。
    - `TransformApplyPass` 只消费 pattern 函数上的 `kernel.transform_pipeline`，在 pattern 内执行 lower-dma-memory-hierarchy 与 canonicalize。
    - `SymbolHoistPipelinePass` 在没有 `symbol.for` 与 alias op 的模块上应保持 no-op，因此可直接用于
      dsl_run 的最小 npu_demo 正向合同。
    - `KernelAggregatePass(matmul_acc=True) -> KernelDecomposePass()` 位于第二段
      symbol hoist cleanup 后、第三段 `MemoryPlanPass` 前，保证 producer/consumer 只分析已分解后的动态 acc matmul IR。
    - `MultiBufferPass(memory_stage=2, target=target)` 位于第三段 cleanup 后、`ProducerConsumerAnalysisPass` 前；
      `target` 非空时按 target registry 容量自动计算 ring num。
    - `ProducerConsumerAnalysisPass` 位于 multi-buffer 后、`MemoryPoolPass` 前，只写
      普通或控制流分类分析 attr，不生成同步 op，并保留 typed `dma.alloc` / `dma.ring` 形态供分析读取。
    - `MemoryPoolPass` 固定以 `rewrite=True, alignment=1024` 运行，将片上 `dma.alloc` 改写为
      `arch.get_dynamic_memory + dma.reinterpret`。
    - memory-pool 后只运行 `CanonicalizePass`，随后执行
      `ArchParallelizePass(target=target, parallel_level="block")`，不得再插入额外 CSE。
    - late `AttachArchInformationPass(target=target)` 位于 arch-parallelize 后、outline 前，用于特化
      `MemoryPoolPass(rewrite=True)` 生成的 `arch.get_dynamic_memory`。
    - `TemplateNameInferPass` 位于 pipeline 最后，为 host wrapper 与 device body 的 `nn.memory`
      签名写入 template name。
    - 仅允许 `target` 选项；当前默认 target 为 `npu_demo`，`only-kernel` 等历史选项必须显式失败。

    使用示例:
    - pm = build_npu_demo_lowering_pipeline()
    - pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    - lowered = pm.run(module)

    关联文件:
    - spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
    - test: [test/passes/pipeline/test_npu_demo_lowering.py](test/passes/pipeline/test_npu_demo_lowering.py)
    - 功能实现: [kernel_gen/pipeline/npu_demo_lowering.py](kernel_gen/pipeline/npu_demo_lowering.py)
    """

    normalized_options = {} if options is None else dict(options)
    unknown = sorted(set(normalized_options) - {"target"})
    if unknown:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PIPELINE,
            f"npu-demo-lowering only accepts target option; got {', '.join(unknown)}",
        )
    target = normalized_options.get("target", "npu_demo")
    if not isinstance(target, str) or not target.strip():
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PIPELINE,
            "npu-demo-lowering target must be non-empty string",
        )

    pm = PassManager(name="npu-demo-lowering")
    pm.add_pass(InlinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(DecompassPass())
    pm.add_pass(NnLoweringPass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True))
    pm.add_pass(SymbolHoistPipelinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(TileAnalysisPass())
    pm.add_pass(KernelPatternAttachPass())
    pm.add_pass(TransformApplyPass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True))
    pm.add_pass(SymbolHoistPipelinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(KernelAggregatePass(matmul_acc=True))
    pm.add_pass(KernelDecomposePass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True))
    pm.add_pass(SymbolHoistPipelinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(MultiBufferPass(memory_stage=2, target=target))
    pm.add_pass(ProducerConsumerAnalysisPass())
    pm.add_pass(MemoryPoolPass(rewrite=True, alignment=1024))
    pm.add_pass(CanonicalizePass())
    pm.add_pass(ArchParallelizePass(target=target, parallel_level="block"))
    pm.add_pass(AttachArchInformationPass(target=target))
    pm.add_pass(OutlineDeviceKernelPass())
    pm.add_pass(TemplateNameInferPass())
    return pm
