"""arch pass package.


功能说明:
- 提供 architecture mapping family 下 pass 的 canonical package root。
- 当前公开 `arch-parallelize` 与 `attach-arch-information`。

API 列表:
- `class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
- `class AttachArchInformationPass(target: str = "npu_demo", fold: bool = True)`

使用示例:
- from kernel_gen.passes.arch import ArchParallelizePass, AttachArchInformationPass
- arch_pass = ArchParallelizePass(target="npu_demo", parallel_level="block")
- attach_pass = AttachArchInformationPass(target="npu_demo")

关联文件:
- spec: spec/pass/arch/arch_parallelize.md
- spec: spec/pass/arch/attach_arch_information.md
- test: test/passes/arch/test_arch_parallelize.py
- test: test/passes/arch/test_attach_arch_information.py
- 功能实现: kernel_gen/passes/arch/__init__.py
"""

from .arch_parallelize import ArchParallelizePass
from .attach_arch_information import AttachArchInformationPass

__all__ = ["ArchParallelizePass", "AttachArchInformationPass"]
