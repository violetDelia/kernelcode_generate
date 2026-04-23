"""tile-analysis logic module.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 承接 `tile-analysis` 的真实 analysis-only 实现与 `ModulePass` 落点。
- 对外仍通过 registry 名称 `tile-analysis` 构造，但 pass 类与 logic 都定义在 `kernel_gen.tile.analysis`。
- 旧 `kernel_gen.passes.lowering.tile_analysis` submodule path 已退场，canonical public path 固定为 `kernel_gen.tile.analysis`。

使用示例:
- from kernel_gen.tile.analysis import TileAnalysisPass, apply_tile_analysis
- TileAnalysisPass().apply(Context(), module)
- apply_tile_analysis(module)

关联文件:
- spec: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
- test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
- 功能实现: [kernel_gen/tile/analysis.py](kernel_gen/tile/analysis.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

from . import common as tile_common


def apply_tile_analysis(module: ModuleOp) -> None:
    """执行 tile-analysis 的 analysis-only 主链。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只接受 `builtin.module`。
    - 对单函数 IR 写入 `tile.analysis` 与 `tile.tile_exprs`。
    - 不生成 `symbol.for`、`dma.view` 或其他改写结构。

    使用示例:
    - apply_tile_analysis(module)

    关联文件:
    - spec: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
    - 功能实现: [kernel_gen/tile/analysis.py](kernel_gen/tile/analysis.py)
    """

    if not isinstance(module, ModuleOp):
        tile_common._raise_tile_error("TilePassRequiresLoweredKernelIR", "module must be builtin.module")
    for op in module.ops:
        if not isinstance(op, tile_common.func.FuncOp):
            continue
        block = tile_common._get_single_block(op)
        tile_common._validate_input_contract(op, block)
        tile_common._annotate_tile_analysis(block)


class TileAnalysisPass(ModulePass):
    """`tile-analysis` 的公开 `ModulePass`。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 保持稳定公开名 `tile-analysis`。
    - 调用当前模块中的 `apply_tile_analysis(...)` 主逻辑。

    使用示例:
    - TileAnalysisPass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
    - test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
    - 功能实现: [kernel_gen/tile/analysis.py](kernel_gen/tile/analysis.py)
    """

    name = "tile-analysis"

    def apply(self: "TileAnalysisPass", ctx: Context, module: ModuleOp) -> None:
        del ctx
        apply_tile_analysis(module)


__all__ = ["TileAnalysisPass", "apply_tile_analysis"]
