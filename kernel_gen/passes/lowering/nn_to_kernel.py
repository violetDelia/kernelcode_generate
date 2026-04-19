"""nn_to_kernel compatibility pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 `LowerNnToKernelPass` 兼容入口，内部复用 `NnLoweringPass` 的实现。
- 保持 pass 名称为 `lower-nn-to-kernel`，以兼容既有 pipeline 与测试。
- 提供 `LowerNnToKernelError` 兼容错误类型，确保旧导入口可用。
- 兼容旧 kernel.add 结果：将 `kernel.binary_elewise(kind="add")` 改写为 `kernel.add`。

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
from xdsl.ir import Block

from kernel_gen.dialect.kernel import KernelAddOp, KernelBinaryElewiseOp
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
    - 兼容 kernel.add 输出，保持旧 expectation 口径可用。

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
        - 兼容旧 kernel.add 语义：将 `kernel.binary_elewise(kind="add")` 改写为 `kernel.add`。

        使用示例:
        - lowered = LowerNnToKernelPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/nn_lowering.md
        - test: test/pass/test_pass_manager.py
        - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
        """

        try:
            lowered = NnLoweringPass().run(module)
        except NnLoweringError as exc:
            raise LowerNnToKernelError(str(exc)) from exc
        for op in list(lowered.walk()):
            if not isinstance(op, KernelBinaryElewiseOp):
                continue
            if op.kind.data != "add":
                continue
            block = op.parent
            if not isinstance(block, Block):
                raise LowerNnToKernelError("lower-nn-to-kernel expects kernel op in block")
            block.insert_op_before(KernelAddOp(op.out, op.lhs, op.rhs, op.space), op)
            block.erase_op(op)
        return lowered


__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
