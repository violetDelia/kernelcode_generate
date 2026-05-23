"""npu-demo-lowering pipeline.


功能说明:
- 提供 `npu-demo-lowering` pipeline 的 builder。
- 固定 `dsl_run` 的 npu_demo 正向链路为
  `InlinePass -> CommonSubexpressionElimination -> CanonicalizePass -> DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass -> HoistDmaAliasOpsPass -> CommonSubexpressionElimination -> CanonicalizePass -> MemoryPlanPass -> SymbolBufferHoistPass -> TileAnalysisPass -> KernelPatternAttachPass -> TransformApplyPass -> SymbolLoopHoistPass -> HoistDmaAliasOpsPass -> CommonSubexpressionElimination -> CanonicalizePass -> MemoryPlanPass -> SymbolBufferHoistPass -> MemoryPoolPass -> CanonicalizePass -> ArchParallelizePass -> ProducerConsumerAnalysisPass -> AttachArchInformationPass -> OutlineDeviceKernelPass -> TemplateNameInferPass`。
- 默认 `MemoryPlanPass` 补齐 insert-free 生命周期，`MemoryPoolPass` 执行 dynamic backing 改写，template-name infer 在 outline 后写回 wrapper/body memory type 的 template name。
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

from kernel_gen.passes.arch_parallelize import ArchParallelizePass
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.hoist_dma_alias_ops import HoistDmaAliasOpsPass
from kernel_gen.passes.inline import InlinePass
from kernel_gen.passes.kernel_pattern_attach import KernelPatternAttachPass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.memory_plan import MemoryPlanPass
from kernel_gen.passes.memory_pool import MemoryPoolPass
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import register_pipeline
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.passes.producer_consumer_analysis import ProducerConsumerAnalysisPass
from kernel_gen.passes.symbol_buffer_hoist import SymbolBufferHoistPass
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass
from kernel_gen.passes.template_name.infer import TemplateNameInferPass
from kernel_gen.passes.tile.analysis import TileAnalysisPass
from kernel_gen.passes.transform_apply import TransformApplyPass


@register_pipeline("npu-demo-lowering")
def build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager:
    """构造 npu-demo-lowering pipeline。


    功能说明:
    - 返回 `PassManager(name="npu-demo-lowering")`。
    - 固定 pass 顺序为
      `InlinePass -> CommonSubexpressionElimination -> CanonicalizePass -> DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass -> HoistDmaAliasOpsPass -> CommonSubexpressionElimination -> CanonicalizePass -> MemoryPlanPass -> SymbolBufferHoistPass -> TileAnalysisPass -> KernelPatternAttachPass -> TransformApplyPass -> SymbolLoopHoistPass -> HoistDmaAliasOpsPass -> CommonSubexpressionElimination -> CanonicalizePass -> MemoryPlanPass -> SymbolBufferHoistPass -> MemoryPoolPass -> CanonicalizePass -> ArchParallelizePass -> ProducerConsumerAnalysisPass -> AttachArchInformationPass -> OutlineDeviceKernelPass -> TemplateNameInferPass`。
    - `CommonSubexpressionElimination` 后均紧跟 xDSL `CanonicalizePass`，仅在本 pipeline 内清理 IR，
      不把 canonicalize 注册为仓库公开 pass。
    - `MemoryPlanPass` 固定以 `insert_free=True, fold=False` 运行两次，并位于对应
      `SymbolBufferHoistPass` 前补齐 `dma.free` 生命周期。
    - 第一段 `SymbolBufferHoistPass` 位于第一段 `MemoryPlanPass` 后、`TileAnalysisPass` 前，用于把
      loop 内安全 `dma.alloc + dma.free` 成对外提到 owner `symbol.for` 两侧。
    - `TileAnalysisPass` 紧跟 `SymbolLoopHoistPass` 后置 CSE，只补充 tile 分析属性，不生成 tile 循环。
    - 两处 `SymbolLoopHoistPass` 后均紧跟 `HoistDmaAliasOpsPass`，用于把紧邻 `dma.fill`
      后的 `dma.reshape` 上移并改写 fill target。
    - `KernelPatternAttachPass` 在 `TileAnalysisPass` 后生成 host dispatcher 与两个 pattern 函数。
    - `TransformApplyPass` 只消费 pattern 函数上的 `kernel.transform_pipeline`，在 pattern 内执行 lower-dma-memory-hierarchy 与 canonicalize。
    - `SymbolLoopHoistPass` 在没有 `symbol.for` 的模块上应保持 no-op，因此可直接用于
      dsl_run 的最小 npu_demo 正向合同。
    - `MemoryPoolPass` 固定以 `rewrite=True, alignment=0` 运行，将片上 `dma.alloc` 改写为
      `arch.get_dynamic_memory + dma.view + dma.reshape`。
    - memory-pool 后只运行 `CanonicalizePass`，随后执行
      `ArchParallelizePass(target=target, parallel_level="block")`，不得再插入额外 CSE。
    - `ProducerConsumerAnalysisPass` 位于 `AttachArchInformationPass(target=target)` 之前，只写
      普通或控制流分类分析 attr，不生成同步 op。
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
    pm.add_pass(SymbolLoopHoistPass())
    pm.add_pass(HoistDmaAliasOpsPass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(MemoryPlanPass(insert_free=True, fold=False))
    pm.add_pass(SymbolBufferHoistPass())
    pm.add_pass(TileAnalysisPass())
    pm.add_pass(KernelPatternAttachPass())
    pm.add_pass(TransformApplyPass())
    pm.add_pass(SymbolLoopHoistPass())
    pm.add_pass(HoistDmaAliasOpsPass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(MemoryPlanPass(insert_free=True, fold=False))
    pm.add_pass(SymbolBufferHoistPass())
    pm.add_pass(MemoryPoolPass(rewrite=True, alignment=0))
    pm.add_pass(CanonicalizePass())
    pm.add_pass(ArchParallelizePass(target=target, parallel_level="block"))
    pm.add_pass(ProducerConsumerAnalysisPass())
    pm.add_pass(AttachArchInformationPass(target=target))
    pm.add_pass(OutlineDeviceKernelPass())
    pm.add_pass(TemplateNameInferPass())
    return pm
