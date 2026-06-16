"""Pass pipelines.


功能说明:
- 提供 pipeline builder 的公开入口。

API 列表:
- `build_default_lowering_pipeline() -> PassManager`
- `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
- `build_cuda_sm89_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

使用示例:
- from kernel_gen.pipeline import (
-     build_cuda_sm89_lowering_pipeline,
-     build_default_lowering_pipeline,
-     build_npu_demo_lowering_pipeline,
- )
- pm = build_default_lowering_pipeline()
- pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
- pm = build_cuda_sm89_lowering_pipeline({"target": "cuda_sm89"})

关联文件:
- spec: [spec/pass/pipeline/default_lowering.md](spec/pass/pipeline/default_lowering.md)
- spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
- spec: [spec/pass/pipeline/cuda_sm89_lowering.md](spec/pass/pipeline/cuda_sm89_lowering.md)
- test: [test/passes/pipeline/test_default_lowering.py](test/passes/pipeline/test_default_lowering.py)
- test: [test/passes/pipeline/test_npu_demo_lowering.py](test/passes/pipeline/test_npu_demo_lowering.py)
- test: [test/passes/pipeline/test_cuda_sm89_lowering.py](test/passes/pipeline/test_cuda_sm89_lowering.py)
- 功能实现: [kernel_gen/pipeline/__init__.py](kernel_gen/pipeline/__init__.py)
"""

from __future__ import annotations

from .cuda_sm89_lowering import build_cuda_sm89_lowering_pipeline
from .default_lowering import build_default_lowering_pipeline
from .npu_demo_lowering import build_npu_demo_lowering_pipeline

__all__ = [
    "build_cuda_sm89_lowering_pipeline",
    "build_default_lowering_pipeline",
    "build_npu_demo_lowering_pipeline",
]
