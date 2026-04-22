"""npu-demo-lowering pipeline.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 提供 `npu-demo-lowering` pipeline 的 builder。
- 固定 `dsl_run` 的 npu_demo 正向链路为 `DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass`。
- 通过 registry 装饰器完成 pipeline 注册。

使用示例:
- from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline
- pm = build_npu_demo_lowering_pipeline()
- lowered = pm.run(module)

关联文件:
- spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
- test: [test/pass/test_pipeline_npu_demo_lowering.py](test/pass/test_pipeline_npu_demo_lowering.py)
- 功能实现: [kernel_gen/passes/pipeline/npu_demo_lowering.py](kernel_gen/passes/pipeline/npu_demo_lowering.py)
"""

from __future__ import annotations

from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.pass_manager import PassManager, _build_pass_manager_from_passes
from kernel_gen.passes.registry import register_pipeline
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass


@register_pipeline("npu-demo-lowering")
def build_npu_demo_lowering_pipeline() -> PassManager:
    """构造 npu-demo-lowering pipeline。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 返回 `PassManager(name="npu-demo-lowering")`。
    - 固定 pass 顺序为 `DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass`。
    - `SymbolLoopHoistPass` 在没有 `symbol.for` 的模块上应保持 no-op，因此可直接用于
      dsl_run 的最小 npu_demo 正向合同。

    使用示例:
    - pm = build_npu_demo_lowering_pipeline()
    - lowered = pm.run(module)

    关联文件:
    - spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
    - test: [test/pass/test_pipeline_npu_demo_lowering.py](test/pass/test_pipeline_npu_demo_lowering.py)
    - 功能实现: [kernel_gen/passes/pipeline/npu_demo_lowering.py](kernel_gen/passes/pipeline/npu_demo_lowering.py)
    """

    return _build_pass_manager_from_passes(
        "npu-demo-lowering",
        [DecompassPass(), NnLoweringPass(), SymbolLoopHoistPass()],
    )
