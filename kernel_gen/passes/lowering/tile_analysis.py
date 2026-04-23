"""tile-analysis pass.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 提供 `tile-analysis` 的公开 `ModulePass` 入口。
- 只写 `tile.analysis` 与 `tile.tile_exprs`，不生成 tile 改写结构。
- 与 `tile-analysis` 的 analysis-only 公开合同保持一致。

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.lowering.tile_analysis import TileAnalysisPass
- TileAnalysisPass().apply(Context(), ModuleOp([]))

关联文件:
- spec: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
- test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
- 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
- 功能实现: [kernel_gen/tile/analysis.py](kernel_gen/tile/analysis.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

from kernel_gen.tile import analysis as tile_analysis_impl


class TileAnalysisPass(ModulePass):
    """`tile-analysis` 公开入口。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 保持稳定公开名 `tile-analysis`。
    - 只执行 analysis 标注，不生成 loop/view/helper。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - TileAnalysisPass().apply(Context(), ModuleOp([]))

    关联文件:
    - spec: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
    """

    name = "tile-analysis"

    def apply(self: "TileAnalysisPass", ctx: Context, module: ModuleOp) -> None:
        """执行 `tile-analysis` ModulePass。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 只接受 `builtin.module`。
        - 对单函数 IR 写入 `tile.analysis` 与 `tile.tile_exprs`。
        - 不生成 tile 改写结构，不引入 `symbol.for` / `dma.view`。

        使用示例:
        - TileAnalysisPass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
        - test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
        - 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
        - 功能实现: [kernel_gen/tile/analysis.py](kernel_gen/tile/analysis.py)
        """

        del ctx
        tile_analysis_impl.apply_tile_analysis(module)


__all__ = ["TileAnalysisPass"]
