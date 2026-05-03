"""tile helper compatibility wrapper.


功能说明:
- 兼容保留 `kernel_gen.passes.lowering.tile` 的旧 helper 导入入口。
- tile family 的真实逻辑已迁到 `kernel_gen.passes.tile.analysis`、`kernel_gen.passes.tile.elewise`、`kernel_gen.passes.tile.reduce`。
- 当前模块只重导出稳定错误构造 helper。

API 列表:
- `_raise_tile_error(kind: str, message: str) -> NoReturn`

使用示例:
- from kernel_gen.passes.lowering.tile import _raise_tile_error
- _raise_tile_error("TilePassUnsupportedOp", "unsupported tile op")

关联文件:
- spec: [spec/pass/tile/README.md](spec/pass/tile/README.md)
- test: [test/passes/tile/test_package.py](test/passes/tile/test_package.py)
- 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
- 功能实现: [kernel_gen/passes/common.py](kernel_gen/passes/common.py)
"""

from __future__ import annotations

from kernel_gen.passes.common import raise_pass_contract_error

_raise_tile_error = raise_pass_contract_error

__all__ = ["_raise_tile_error"]
