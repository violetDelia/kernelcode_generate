"""tile-analysis pass.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 提供 `tile-analysis` 的公开 `ModulePass` 入口。
- 只写 `tile.analysis` 与 `tile.tile_exprs`，不生成 tile 改写结构。
- 与 expectation/pass/tile/analysis 的 analysis-only 黑盒口径一致。

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.lowering.tile_analysis import TileAnalysisPass
- TileAnalysisPass().apply(Context(), ModuleOp([]))

关联文件:
- spec: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
- test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
- 功能实现: [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

from . import tile as tile_module


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
        """

        del ctx
        if not isinstance(module, ModuleOp):
            tile_module._raise_tile_error("TilePassRequiresLoweredKernelIR", "module must be builtin.module")
        for op in module.ops:
            if not isinstance(op, tile_module.func.FuncOp):
                continue
            block = tile_module._get_single_block(op)
            tile_module._validate_input_contract(op, block)
            tile_module._annotate_tile_analysis(block)


__all__ = ["TileAnalysisPass"]
