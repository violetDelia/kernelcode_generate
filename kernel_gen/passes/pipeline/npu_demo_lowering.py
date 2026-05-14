"""npu-demo-lowering pipeline.


功能说明:
- 提供 `npu-demo-lowering` pipeline 的 builder。
- 固定 `dsl_run` 的 npu_demo 正向链路为
  `InlinePass -> CommonSubexpressionElimination -> DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass -> CommonSubexpressionElimination -> TileAnalysisPass -> LowerDmaMemoryHierarchyPass -> SymbolBufferHoistPass -> MemoryPoolPass -> AttachArchInformationPass -> OutlineDeviceKernelPass -> TemplateNameInferPass`。
- 默认 `MemoryPoolPass` 仅执行 summary 模式，template-name infer 在 outline 后写回 wrapper/body memory type 的 template name。
- 通过 registry 装饰器完成 pipeline 注册。

API 列表:
- `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

使用示例:
- from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline
- pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
- lowered = pm.run(module)

关联文件:
- spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
- test: [test/passes/pipeline/test_npu_demo_lowering.py](test/passes/pipeline/test_npu_demo_lowering.py)
- 功能实现: [kernel_gen/passes/pipeline/npu_demo_lowering.py](kernel_gen/passes/pipeline/npu_demo_lowering.py)
"""

from __future__ import annotations

from xdsl.transforms.common_subexpression_elimination import CommonSubexpressionElimination

from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
from kernel_gen.passes.inline import InlinePass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.memory_pool import MemoryPoolPass
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import register_pipeline
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.passes.symbol_buffer_hoist import SymbolBufferHoistPass
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass
from kernel_gen.passes.template_name_infer import TemplateNameInferPass
from kernel_gen.passes.tile.analysis import TileAnalysisPass


@register_pipeline("npu-demo-lowering")
def build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager:
    """构造 npu-demo-lowering pipeline。


    功能说明:
    - 返回 `PassManager(name="npu-demo-lowering")`。
    - 固定 pass 顺序为
      `InlinePass -> CommonSubexpressionElimination -> DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass -> CommonSubexpressionElimination -> TileAnalysisPass -> LowerDmaMemoryHierarchyPass -> SymbolBufferHoistPass -> MemoryPoolPass -> AttachArchInformationPass -> OutlineDeviceKernelPass -> TemplateNameInferPass`。
    - `CommonSubexpressionElimination` 紧跟 `InlinePass`，用于消除 inline 展平后产生的重复纯常量与等价表达式。
    - 第二个 `CommonSubexpressionElimination` 紧跟 `SymbolLoopHoistPass`，用于消除 loop 外提后产生的重复纯常量与等价表达式。
    - `TileAnalysisPass` 紧跟 `SymbolLoopHoistPass` 后置 CSE，只补充 tile 分析属性，不生成 tile 循环。
    - `LowerDmaMemoryHierarchyPass` 固定以 `fold=True` 和 `apply_op='matmul{["", "tlm1", "tlm2"]}'` 插入 matmul lhs/rhs staging。
    - `SymbolLoopHoistPass` 在没有 `symbol.for` 的模块上应保持 no-op，因此可直接用于
      dsl_run 的最小 npu_demo 正向合同。
    - `SymbolBufferHoistPass` 位于 `TileAnalysisPass` 之后，用于把 loop 内安全 `dma.alloc`
      外提到 loop 之前。
    - `MemoryPoolPass` 固定以 `rewrite=False, alignment=1024` 运行，只记录 summary，不默认改写片上 `dma.alloc`。
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
    - 功能实现: [kernel_gen/passes/pipeline/npu_demo_lowering.py](kernel_gen/passes/pipeline/npu_demo_lowering.py)
    """

    normalized_options = {} if options is None else dict(options)
    unknown = sorted(set(normalized_options) - {"target"})
    if unknown:
        raise ValueError(f"npu-demo-lowering only accepts target option; got {', '.join(unknown)}")
    target = normalized_options.get("target", "npu_demo")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("npu-demo-lowering target must be non-empty string")

    pm = PassManager(name="npu-demo-lowering")
    pm.add_pass(InlinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(DecompassPass())
    pm.add_pass(NnLoweringPass())
    pm.add_pass(SymbolLoopHoistPass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(TileAnalysisPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass(fold=True, apply_op='matmul{["", "tlm1", "tlm2"]}'))
    pm.add_pass(SymbolBufferHoistPass())
    pm.add_pass(MemoryPoolPass(rewrite=False, alignment=1024))
    pm.add_pass(AttachArchInformationPass(target=target))
    pm.add_pass(OutlineDeviceKernelPass())
    pm.add_pass(TemplateNameInferPass())
    return pm
