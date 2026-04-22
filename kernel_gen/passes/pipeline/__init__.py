"""Pass pipelines.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 提供 pipeline builder 的公开入口。

使用示例:
- from kernel_gen.passes.pipeline import (
-     build_default_lowering_pipeline,
-     build_npu_demo_lowering_pipeline,
- )
- pm = build_default_lowering_pipeline()
- pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})

关联文件:
- spec: [spec/pass/pipeline/README.md](spec/pass/pipeline/README.md)
- spec: [spec/pass/pipeline/default_lowering.md](spec/pass/pipeline/default_lowering.md)
- spec: [spec/pass/pipeline/npu_demo_lowering.md](spec/pass/pipeline/npu_demo_lowering.md)
- test: [test/pass/test_pipeline_default_lowering.py](test/pass/test_pipeline_default_lowering.py)
- test: [test/pass/test_pipeline_npu_demo_lowering.py](test/pass/test_pipeline_npu_demo_lowering.py)
- 功能实现: [kernel_gen/passes/pipeline/__init__.py](kernel_gen/passes/pipeline/__init__.py)
"""

from __future__ import annotations

from .default_lowering import build_default_lowering_pipeline
from .npu_demo_lowering import build_npu_demo_lowering_pipeline

__all__ = ["build_default_lowering_pipeline", "build_npu_demo_lowering_pipeline"]
