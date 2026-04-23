"""tile helper and implementation package.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 tile family 在 S4 阶段的 canonical helper / implementation path。
- 公开 `kernel_gen.tile.common`、`kernel_gen.tile.analysis`、`kernel_gen.tile.elewise`、`kernel_gen.tile.reduce`。
- 当前阶段只做 helper/path 收口，不在这里执行最终 logic rewrite。

使用示例:
- from kernel_gen.tile import common as tile_common
- from kernel_gen.tile.analysis import apply_tile_analysis

关联文件:
- spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
- test: [test/pass/test_lowering_tile_private_helpers.py](test/pass/test_lowering_tile_private_helpers.py)
- 功能实现: [kernel_gen/tile/__init__.py](kernel_gen/tile/__init__.py)
"""

from . import analysis, common, elewise, reduce

__all__ = ["common", "analysis", "elewise", "reduce"]
