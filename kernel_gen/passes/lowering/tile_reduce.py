"""tile-reduce pass.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 提供 `tile-reduce` 的公开 `ModulePass` 入口。
- 消费已有 `tile.analysis` / `tile.tile_exprs` 输入合同，只对 `kernel.matmul` 补齐 reduce 轴循环。
- 不生成 `tile.step_value` / `kernel_split.tile_value` 这类旧桥接 op。

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.lowering.tile_reduce import TileReducePass
- TileReducePass().apply(Context(), ModuleOp([]))

关联文件:
- spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
- 功能实现: [kernel_gen/tile/reduce.py](kernel_gen/tile/reduce.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

from kernel_gen.tile import reduce as tile_reduce_impl


class TileReducePass(ModulePass):
    """`tile-reduce` 公开入口。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 保持稳定公开名 `tile-reduce`。
    - 只消费已有 `tile.analysis` / `tile.tile_exprs` 合同并生成 matmul 的 reduce 轴循环。
    - 生成的 `tuner.param` 结果类型为 `!symbol.int<"...">`，便于下游 codegen 直接绑定 tile 因子。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - TileReducePass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    name = "tile-reduce"

    def apply(self: "TileReducePass", ctx: Context, module: ModuleOp) -> None:
        """执行 `tile-reduce` ModulePass。

        创建者: 金铲铲大作战
        最后一次更改: 朽木露琪亚

        功能说明:
        - 只接受 `builtin.module`。
        - 只对 `kernel.matmul` 计划补齐 reduce 轴循环和 `dma.fill` 累加结构。
        - 保留 rewritten op 的 `tile.analysis` 与 `tile.tile_exprs`。
        - 不生成 `tile.step_value` / `kernel_split.tile_value` 旧桥接 op。

        使用示例:
        - TileReducePass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
        - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
        - 功能实现: [kernel_gen/tile/reduce.py](kernel_gen/tile/reduce.py)
        """

        del ctx
        tile_reduce_impl.apply_tile_reduce(module)


__all__ = ["TileReducePass"]
