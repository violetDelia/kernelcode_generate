"""tile-analysis implementation landing module.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 承接 `tile-analysis` 的真实 analysis-only 实现落点。
- 对公开 `ModulePass` 壳保持在 `kernel_gen.passes.lowering.tile_analysis` 的前提下，把校验与 analysis 标注主链收口到 `kernel_gen.tile.analysis`。
- S4 阶段只做 path 收口，不改 analysis 逻辑语义。

使用示例:
- from kernel_gen.tile.analysis import apply_tile_analysis
- apply_tile_analysis(module)

关联文件:
- spec: [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
- test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
- 功能实现: [kernel_gen/tile/analysis.py](kernel_gen/tile/analysis.py)
"""

from __future__ import annotations

from xdsl.dialects.builtin import ModuleOp

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


__all__ = ["apply_tile_analysis"]
