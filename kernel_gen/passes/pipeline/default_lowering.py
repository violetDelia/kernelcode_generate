"""default lowering pipeline.


功能说明:
- 提供 `default-lowering` pipeline 的 builder。
- 固定默认 lowering pass 顺序，避免重复拼装。
- 通过 registry 装饰器完成 pipeline 注册。
- 默认 pipeline 显式启用 `lower-dma-memory-hierarchy` 的 legacy hierarchy 兼容路径，
  保持公开黑盒输出包含 `dma.slice / dma.deslice` 链。

API 列表:
- `build_default_lowering_pipeline() -> PassManager`

使用示例:
- from kernel_gen.passes.pipeline import build_default_lowering_pipeline
- pm = build_default_lowering_pipeline()
- lowered = pm.run(module)

关联文件:
- spec: [spec/pass/pipeline/default_lowering.md](spec/pass/pipeline/default_lowering.md)
- test: [test/passes/pipeline/test_default_lowering.py](test/passes/pipeline/test_default_lowering.py)
- 功能实现: [kernel_gen/passes/pipeline/default_lowering.py](kernel_gen/passes/pipeline/default_lowering.py)
"""

from __future__ import annotations

from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import register_pipeline


@register_pipeline("default-lowering")
def build_default_lowering_pipeline() -> PassManager:
    """构造 default-lowering pipeline。


    功能说明:
    - 返回 `PassManager(name="default-lowering")`。
    - 固定 pass 顺序为 `DecompassPass -> NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。
    - `LowerDmaMemoryHierarchyPass(fold=False)` 是 default-lowering 的公开黑盒合同，
      用于生成 legacy `dma.slice / dma.deslice` staging 链。

    使用示例:
    - pm = build_default_lowering_pipeline()
    - lowered = pm.run(module)

    关联文件:
    - spec: [spec/pass/pipeline/default_lowering.md](spec/pass/pipeline/default_lowering.md)
    - test: [test/passes/pipeline/test_default_lowering.py](test/passes/pipeline/test_default_lowering.py)
    - 功能实现: [kernel_gen/passes/pipeline/default_lowering.py](kernel_gen/passes/pipeline/default_lowering.py)
    """

    pm = PassManager(name="default-lowering")
    pm.extend(
        [
            DecompassPass(),
            NnLoweringPass(),
            BufferResultsToOutParamsPass(),
            LowerDmaMemoryHierarchyPass(fold=False),
        ]
    )
    return pm
