"""tile helper compatibility wrapper.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 兼容保留 `kernel_gen.passes.lowering.tile` 的旧 helper 导入入口。
- tile family 的真实 helper / logic 已迁到 `kernel_gen.tile.common`。
- 当前模块只重导出稳定错误类型与错误构造 helper。

使用示例:
- from kernel_gen.passes.lowering.tile import TilePassError, _raise_tile_error
- raise TilePassError("TilePassUnsupportedOp: unsupported tile op")

关联文件:
- spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
- 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
- 功能实现: [kernel_gen/tile/common.py](kernel_gen/tile/common.py)
"""

from __future__ import annotations

from kernel_gen.tile.common import TilePassError, _raise_tile_error

__all__ = ["TilePassError", "_raise_tile_error"]
