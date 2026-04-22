"""npu-demo-lowering pipeline.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 提供 `npu-demo-lowering` pipeline 的 builder。
- 固定 `dsl_run` 的 npu_demo 正向链路为
  `InlinePass -> DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass -> AttachArchInformationPass -> OutlineDeviceKernelPass`。
- 通过 registry 装饰器完成 pipeline 注册。

使用示例:
- from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline
- pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
- lowered = pm.run(module)

关联文件:
- spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
- test: [test/pass/test_pipeline_npu_demo_lowering.py](test/pass/test_pipeline_npu_demo_lowering.py)
- 功能实现: [kernel_gen/passes/pipeline/npu_demo_lowering.py](kernel_gen/passes/pipeline/npu_demo_lowering.py)
"""

from __future__ import annotations

from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.inline import InlinePass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import register_pipeline
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass


@register_pipeline("npu-demo-lowering")
def build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager:
    """构造 npu-demo-lowering pipeline。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 返回 `PassManager(name="npu-demo-lowering")`。
    - 固定 pass 顺序为
      `InlinePass -> DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass -> AttachArchInformationPass -> OutlineDeviceKernelPass`。
    - `SymbolLoopHoistPass` 在没有 `symbol.for` 的模块上应保持 no-op，因此可直接用于
      dsl_run 的最小 npu_demo 正向合同。
    - 仅允许 `target` 选项；当前默认 target 为 `npu_demo`，`only-kernel` 等历史选项必须显式失败。

    使用示例:
    - pm = build_npu_demo_lowering_pipeline()
    - pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    - lowered = pm.run(module)

    关联文件:
    - spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
    - test: [test/pass/test_pipeline_npu_demo_lowering.py](test/pass/test_pipeline_npu_demo_lowering.py)
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
    pm.add_pass(DecompassPass())
    pm.add_pass(NnLoweringPass())
    pm.add_pass(SymbolLoopHoistPass())
    pm.add_pass(AttachArchInformationPass(target=target))
    pm.add_pass(OutlineDeviceKernelPass())
    return pm
