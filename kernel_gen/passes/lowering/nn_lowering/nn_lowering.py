"""nn_lowering pass 实现。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 `NnLoweringPass` 的公开入口与错误规范。
- 兼容当前 `LowerNnToKernelPass` 的实际 lowering 行为。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- module = NnLoweringPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/public_name.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
"""

from __future__ import annotations

from xdsl.ir import Operation

from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelError, LowerNnToKernelPass
from kernel_gen.passes.pass_manager import Pass
from .nn_lowering_utility import NnLoweringError, ensure_module_op


class NnLoweringPass(Pass):
    """nn_lowering pass。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 提供新的公开 pass 名称与调用入口。
    - 当前阶段复用 `LowerNnToKernelPass` 的 lowering 行为。

    使用示例:
    - module = NnLoweringPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
    """

    name = "lower-nn"

    def run(self: "NnLoweringPass", module: Operation) -> Operation:
        """执行 nn_lowering pass。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 校验 module 入口。
        - 调用 LowerNnToKernelPass 完成实际 lowering。

        使用示例:
        - NnLoweringPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_lowering.md
        - test: test/pass/nn_lowering/public_name.py
        - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
        """

        module_op = ensure_module_op(module)
        try:
            return LowerNnToKernelPass().run(module_op)
        except LowerNnToKernelError as exc:
            raise NnLoweringError(str(exc)) from exc


__all__ = ["NnLoweringPass", "NnLoweringError"]
