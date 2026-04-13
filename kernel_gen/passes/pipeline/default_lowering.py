"""default lowering pipeline.

创建者: 朽木露琪亚
最后一次更改: 小李飞刀

功能说明:
- 提供 `default-lowering` pipeline 的 builder。
- 固定默认 lowering pass 顺序，避免重复拼装。
- 通过 registry 装饰器完成 pipeline 注册。

使用示例:
- from kernel_gen.passes.pipeline import build_default_lowering_pipeline
- pm = build_default_lowering_pipeline()
- lowered = pm.run(module)

关联文件:
- spec: [spec/pass/pipeline/default_lowering.md](spec/pass/pipeline/default_lowering.md)
- test: [test/pass/test_pipeline_default_lowering.py](test/pass/test_pipeline_default_lowering.py)
- 功能实现: [kernel_gen/passes/pipeline/default_lowering.py](kernel_gen/passes/pipeline/default_lowering.py)
"""

from __future__ import annotations

from kernel_gen.passes.lowering import (
    BufferResultsToOutParamsPass,
    LowerDmaMemoryHierarchyPass,
    NnLoweringPass,
)
from kernel_gen.passes.lowering.decompass import DecompassPass
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import register_pipeline


@register_pipeline("default-lowering")
def build_default_lowering_pipeline() -> PassManager:
    """构造 default-lowering pipeline。

    创建者: 朽木露琪亚
    最后一次更改: 小李飞刀

    功能说明:
    - 返回 `PassManager(name="default-lowering")`。
    - 固定 pass 顺序为 `DecompassPass -> NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。

    使用示例:
    - pm = build_default_lowering_pipeline()
    - lowered = pm.run(module)

    关联文件:
    - spec: [spec/pass/pipeline/default_lowering.md](spec/pass/pipeline/default_lowering.md)
    - test: [test/pass/test_pipeline_default_lowering.py](test/pass/test_pipeline_default_lowering.py)
    - 功能实现: [kernel_gen/passes/pipeline/default_lowering.py](kernel_gen/passes/pipeline/default_lowering.py)
    """

    pm = PassManager(name="default-lowering")
    pm.add_pass(DecompassPass())
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    return pm
