"""tile helper and implementation package.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 tile family 在 S7 后的 canonical helper / logic path。
- 公开 `kernel_gen.passes.tile.analysis`、`kernel_gen.passes.tile.elewise`、`kernel_gen.passes.tile.reduce`。
- 共享错误固定落在 `kernel_gen.passes.common`。
- tile family 的 pass 类与主逻辑都定义在这里，旧 lowering 子模块只保留兼容包装。

使用示例:
- from kernel_gen.passes.tile.analysis import get_tile_analysis_pass_patterns
- from kernel_gen.passes.tile.elewise import get_tile_elewise_pass_patterns

关联文件:
- spec: [spec/pass/tile/README.md](spec/pass/tile/README.md)
- test: [test/pass/tile/test_package.py](test/pass/tile/test_package.py)
- test: [test/pass/tile/test_analysis.py](test/pass/tile/test_analysis.py)
- test: [test/pass/tile/test_elewise.py](test/pass/tile/test_elewise.py)
- test: [test/pass/tile/test_reduce.py](test/pass/tile/test_reduce.py)
- 功能实现: [kernel_gen/passes/tile/__init__.py](kernel_gen/passes/tile/__init__.py)
"""

from . import analysis, elewise, reduce

__all__ = ["analysis", "elewise", "reduce"]
