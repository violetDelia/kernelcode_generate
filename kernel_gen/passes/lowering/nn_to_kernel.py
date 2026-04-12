"""nn_to_kernel compatibility pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 `LowerNnToKernelPass` 兼容入口，内部复用 `NnLoweringPass` 的实现。
- 保持 pass 名称为 `lower-nn-to-kernel`，以兼容既有 pipeline 与测试。

使用示例:
- from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
- module = LowerNnToKernelPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/test_pass_manager.py
- 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import ModuleOp

from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.passes.pass_manager import Pass


class LowerNnToKernelPass(Pass):
    """`lower-nn-to-kernel` 兼容入口。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对外提供旧名字 `LowerNnToKernelPass`。
    - 内部复用 `NnLoweringPass` 的实现与错误路径。

    使用示例:
    - module = LowerNnToKernelPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/test_pass_manager.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    name = "lower-nn-to-kernel"

    def run(self: "LowerNnToKernelPass", module: ModuleOp) -> ModuleOp:
        """执行 lowering 入口并返回改写后的 module。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 委派给 `NnLoweringPass` 完成实际 lowering。

        使用示例:
        - lowered = LowerNnToKernelPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_lowering.md
        - test: test/pass/test_pass_manager.py
        - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
        """

        return NnLoweringPass().run(module)


__all__ = ["LowerNnToKernelPass"]
