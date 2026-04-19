"""nn_to_kernel compatibility pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 `LowerNnToKernelPass` 兼容入口，内部复用 `NnLoweringPass` 的实现。
- 保持 pass 名称为 `lower-nn-to-kernel`，以兼容既有 pipeline 与测试。
- 提供 `LowerNnToKernelError` 兼容错误类型，确保旧导入口可用。
- 不再回写旧 `kernel.add`，公开结果统一保持为 `kernel.binary_elewise(kind=...)`。

使用示例:
- from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
- module = LowerNnToKernelPass().run(module)
- from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelError

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/test_pass_manager.py
- 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import ModuleOp

from kernel_gen.passes.lowering.nn_lowering import NnLoweringError, NnLoweringPass
from kernel_gen.passes.pass_manager import Pass


class LowerNnToKernelError(NnLoweringError):
    """`lower-nn-to-kernel` 兼容错误类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保留旧错误类型名，便于旧 import 路径与测试稳定。
    - 语义与 `NnLoweringError` 保持一致。

    使用示例:
    - raise LowerNnToKernelError("lower-nn-to-kernel failed")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/test_pass_manager.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """


class LowerNnToKernelPass(Pass):
    """`lower-nn-to-kernel` 兼容入口。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对外提供旧名字 `LowerNnToKernelPass`。
    - 内部复用 `NnLoweringPass` 的实现与错误路径。
    - 仅保留 pass 名称兼容，不回写旧 kernel 公开 op 名。

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
        - 保持 lowering 结果为当前公开 `kernel.binary_elewise(kind=...)`。

        使用示例:
        - lowered = LowerNnToKernelPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_lowering.md
        - test: test/pass/test_pass_manager.py
        - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
        """

        try:
            return NnLoweringPass().run(module)
        except NnLoweringError as exc:
            raise LowerNnToKernelError(str(exc)) from exc


__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
