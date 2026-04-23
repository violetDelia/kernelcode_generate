"""tile-elewise pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 `tile-elewise` 的公开 `ModulePass` 入口。
- 消费已有 `tile.analysis` / `tile.tile_exprs` 输入合同，只切分 elewise 轴并保留最终合同属性。
- 不生成 `tile.step_value` / `kernel_split.tile_value` 这类旧桥接 op。

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.lowering.tile_elewise import TileElewisePass
- TileElewisePass().apply(Context(), ModuleOp([]))

关联文件:
- spec: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
- test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
- 功能实现: [kernel_gen/passes/lowering/tile_elewise.py](kernel_gen/passes/lowering/tile_elewise.py)
- 功能实现: [kernel_gen/tile/elewise.py](kernel_gen/tile/elewise.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

from kernel_gen.tile import elewise as tile_elewise_impl


class TileElewisePass(ModulePass):
    """`tile-elewise` 公开入口。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保持稳定公开名 `tile-elewise`。
    - 只消费已有 `tile.analysis` / `tile.tile_exprs` 合同并生成 tile loop / view 结构。
    - 生成的 `tuner.param` 结果类型为 `!symbol.int<"...">`，便于下游 codegen 直接绑定 tile 因子。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - TileElewisePass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
    - test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_elewise.py](kernel_gen/passes/lowering/tile_elewise.py)
    """

    name = "tile-elewise"

    def apply(self: "TileElewisePass", ctx: Context, module: ModuleOp) -> None:
        """执行 `tile-elewise` ModulePass。

        创建者: 小李飞刀
        最后更改: 小李飞刀

        功能说明:
        - 只接受 `builtin.module`。
        - 对单函数输入按 elementwise/broadcast/matmul 计划改写。
        - 保留 rewritten op 的 `tile.analysis` 与 `tile.tile_exprs`，其中 `tile.tile_exprs` 仅对真实切分轴写入 tile 名称。
        - 不生成 `tile.step_value` / `kernel_split.tile_value` 旧桥接 op。

        使用示例:
        - TileElewisePass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
        - test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
        - 功能实现: [kernel_gen/passes/lowering/tile_elewise.py](kernel_gen/passes/lowering/tile_elewise.py)
        - 功能实现: [kernel_gen/tile/elewise.py](kernel_gen/tile/elewise.py)
        """

        del ctx
        tile_elewise_impl.apply_tile_elewise(module)


__all__ = ["TileElewisePass"]
