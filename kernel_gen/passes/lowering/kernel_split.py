"""kernel_split 兼容入口。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 保留 `KernelSplitPass` 与 `KernelSplitError` 的兼容入口。
- 实现完全委托 TilePass，公开 name 使用 `"tile"`。

使用示例:
- from kernel_gen.passes.lowering.kernel_split import KernelSplitPass
- module = KernelSplitPass().run(module)

关联文件:
- spec: [spec/pass/lowering/kernel_split.md](spec/pass/lowering/kernel_split.md)
- test: [test/pass/test_lowering_kernel_split.py](test/pass/test_lowering_kernel_split.py)
- 功能实现: [kernel_gen/passes/lowering/kernel_split.py](kernel_gen/passes/lowering/kernel_split.py)
"""

from __future__ import annotations

from xdsl.dialects.builtin import ModuleOp

<<<<<<< HEAD
from kernel_gen.passes.lowering.tile import (
    TilePass,
    TilePassError,
    _TileStepValueOp,
    _TileSymbolLiteralOp,
)


class KernelSplitError(TilePassError):
    """kernel_split 兼容错误类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保持旧入口 `KernelSplitError` 的异常类型与短语形式一致。

    使用示例:
    - raise KernelSplitError("TilePassUnsupportedOp: reduce kernel op is not supported")

    关联文件:
    - spec: [spec/pass/lowering/kernel_split.md](spec/pass/lowering/kernel_split.md)
    - test: [test/pass/test_lowering_kernel_split.py](test/pass/test_lowering_kernel_split.py)
    - 功能实现: [kernel_gen/passes/lowering/kernel_split.py](kernel_gen/passes/lowering/kernel_split.py)
    """


class KernelSplitPass(TilePass):
    """kernel_split 兼容 pass。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 兼容旧入口，但行为与 TilePass 完全一致。
    - 公开 name 固定为 `"tile"`。

    使用示例:
    - module = KernelSplitPass().run(module)

    关联文件:
    - spec: [spec/pass/lowering/kernel_split.md](spec/pass/lowering/kernel_split.md)
    - test: [test/pass/test_lowering_kernel_split.py](test/pass/test_lowering_kernel_split.py)
    - 功能实现: [kernel_gen/passes/lowering/kernel_split.py](kernel_gen/passes/lowering/kernel_split.py)
    """

    name = "tile"

    def run(self: "KernelSplitPass", module: ModuleOp) -> ModuleOp:
        """执行 kernel_split 兼容 pass。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 直接调用 TilePass 的实现逻辑。

        使用示例:
        - lowered = KernelSplitPass().run(module)

        关联文件:
        - spec: [spec/pass/lowering/kernel_split.md](spec/pass/lowering/kernel_split.md)
        - test: [test/pass/test_lowering_kernel_split.py](test/pass/test_lowering_kernel_split.py)
        - 功能实现: [kernel_gen/passes/lowering/kernel_split.py](kernel_gen/passes/lowering/kernel_split.py)
        """

        return super().run(module)


_KernelSplitTileValueOp = _TileStepValueOp
_KernelSplitSymbolLiteralOp = _TileSymbolLiteralOp


__all__ = [
    "KernelSplitPass",
    "KernelSplitError",
    "_KernelSplitTileValueOp",
    "_KernelSplitSymbolLiteralOp",
]
