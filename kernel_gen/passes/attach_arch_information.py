"""attach-arch-information compatibility module.


功能说明:
- 保留旧公开 import path `kernel_gen.passes.attach_arch_information`。
- 真实实现已迁移到 `kernel_gen.passes.arch.attach_arch_information`。
- 本文件只 re-export 公开 class，不承载 pass 业务逻辑。

API 列表:
- `class AttachArchInformationPass(target: str = "npu_demo", fold: bool = True)`
- `AttachArchInformationPass.from_options(options: dict[str, str]) -> AttachArchInformationPass`
- `AttachArchInformationPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
- pass_obj = AttachArchInformationPass(target="npu_demo")

关联文件:
- spec: spec/pass/arch/attach_arch_information.md
- test: test/passes/arch/test_attach_arch_information.py
- 功能实现: kernel_gen/passes/arch/attach_arch_information.py
"""

from kernel_gen.passes.arch.attach_arch_information import AttachArchInformationPass

__all__ = ["AttachArchInformationPass"]
