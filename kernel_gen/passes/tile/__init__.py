"""tile helper and implementation package.


功能说明:
- 提供 tile family 在 S7 后的 canonical helper / logic path。
- 公开 `kernel_gen.passes.tile.analysis`、`kernel_gen.passes.tile.elewise`、`kernel_gen.passes.tile.reduce`。
- 共享错误固定落在 `kernel_gen.passes.common`。
- tile family 的 pass 类与主逻辑都定义在这里，旧 lowering 子模块只保留兼容包装。

API 列表:
- `analysis: module`
- `elewise: module`
- `reduce: module`

使用示例:
- from kernel_gen.passes.tile.analysis import get_tile_analysis_pass_patterns
- from kernel_gen.passes.tile.elewise import get_tile_elewise_pass_patterns

关联文件:
- spec: [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
- spec: [spec/pass/tile/elewise.md](spec/pass/tile/elewise.md)
- spec: [spec/pass/tile/reduce.md](spec/pass/tile/reduce.md)
- test: [test/passes/tile/test_package.py](test/passes/tile/test_package.py)
- test: [test/passes/tile/test_analysis.py](test/passes/tile/test_analysis.py)
- test: [test/passes/tile/test_elewise.py](test/passes/tile/test_elewise.py)
- test: [test/passes/tile/test_reduce.py](test/passes/tile/test_reduce.py)
- 功能实现: [kernel_gen/passes/tile/__init__.py](kernel_gen/passes/tile/__init__.py)
"""

from . import analysis, elewise, reduce

__all__ = ["analysis", "elewise", "reduce"]
