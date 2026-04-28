"""lowering pass compatibility package.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 nn -> kernel lowering pass 的公开入口。
- 提供 lower-dma-memory-hierarchy pass 的聚合导出。
- 提供 decompass pass 的公开入口。
- 提供 outline-device-kernel 的 lowering 兼容入口。
- 提供 tile-analysis / tile-elewise / tile-reduce ModulePass 入口。
- 提供 symbol-loop-hoist 的兼容入口。
- 当前文件只重导出 spec 已定义的公开 pass 类；不新增跨文件 private helper 入口。

API 列表:
- `class NnLoweringPass()`
- `class LowerDmaMemoryHierarchyPass()`
- `class DecompassPass()`
- `class OutlineDeviceKernelPass()`
- `class TileAnalysisPass()`
- `class TileElewisePass()`
- `class TileReducePass()`
- `class SymbolLoopHoistPass()`

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- pass_obj = NnLoweringPass()
- from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
- pass_obj = LowerDmaMemoryHierarchyPass()
- from kernel_gen.passes.decompass import DecompassPass
- pass_obj = DecompassPass()
- from kernel_gen.passes.lowering import OutlineDeviceKernelPass
- pass_obj = OutlineDeviceKernelPass()
- from kernel_gen.passes.tile.analysis import TileAnalysisPass
- pass_obj = TileAnalysisPass()
- from kernel_gen.passes.tile.elewise import TileElewisePass
- pass_obj = TileElewisePass()
- from kernel_gen.passes.tile.reduce import TileReducePass
- pass_obj = TileReducePass()
- from kernel_gen.passes import SymbolLoopHoistPass
- pass_obj = SymbolLoopHoistPass()

关联文件:
- spec:
  - [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
  - [spec/pass/lowering/dma_memory_hierarchy/spec.md](spec/pass/lowering/dma_memory_hierarchy/spec.md)
  - [spec/pass/decompass.md](spec/pass/decompass.md)
  - [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
  - [spec/pass/tile/analysis.md](spec/pass/tile/analysis.md)
  - [spec/pass/tile/elewise.md](spec/pass/tile/elewise.md)
  - [spec/pass/tile/reduce.md](spec/pass/tile/reduce.md)
  - [spec/pass/tile/README.md](spec/pass/tile/README.md)
  - [spec/pass/symbol_loop_hoist.md](spec/pass/symbol_loop_hoist.md)
- test:
  - [test/pass/nn_lowering/public_name.py](test/pass/nn_lowering/public_name.py)
  - [test/pass/nn_lowering/test_lowering_nn_lowering.py](test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [test/pass/test_dma_memory_hierarchy.py](test/pass/test_dma_memory_hierarchy.py)
  - [test/pass/decompass/test_softmax.py](test/pass/decompass/test_softmax.py)
  - [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [test/pass/tile/test_analysis.py](test/pass/tile/test_analysis.py)
  - [test/pass/tile/test_elewise.py](test/pass/tile/test_elewise.py)
  - [test/pass/tile/test_reduce.py](test/pass/tile/test_reduce.py)
  - [test/pass/test_symbol_loop_hoist.py](test/pass/test_symbol_loop_hoist.py)
- 功能实现:
  - [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [kernel_gen/passes/dma_memory_hierarchy.py](kernel_gen/passes/dma_memory_hierarchy.py)
  - [kernel_gen/passes/decompass.py](kernel_gen/passes/decompass.py)
  - [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
  - [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
  - [kernel_gen/passes/tile/elewise.py](kernel_gen/passes/tile/elewise.py)
  - [kernel_gen/passes/tile/reduce.py](kernel_gen/passes/tile/reduce.py)
  - [kernel_gen/passes/lowering/__init__.py](kernel_gen/passes/lowering/__init__.py)
  - [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
  - [kernel_gen/passes/symbol_loop_hoist.py](kernel_gen/passes/symbol_loop_hoist.py)
"""

import sys

from .nn_lowering import NnLoweringPass
from .. import outline_device_kernel as _outline_device_kernel_module
from .. import symbol_loop_hoist as _symbol_loop_hoist_module
from ..dma_memory_hierarchy import (
    LowerDmaMemoryHierarchyPass,
)
from ..decompass import DecompassPass
from ..outline_device_kernel import OutlineDeviceKernelPass
from ..symbol_loop_hoist import SymbolLoopHoistPass
from ..tile.analysis import TileAnalysisPass
from ..tile.elewise import TileElewisePass
from ..tile.reduce import TileReducePass

outline_device_kernel = _outline_device_kernel_module
sys.modules.setdefault(__name__ + ".outline_device_kernel", _outline_device_kernel_module)
symbol_loop_hoist = _symbol_loop_hoist_module
sys.modules.setdefault(__name__ + ".symbol_loop_hoist", _symbol_loop_hoist_module)

__all__ = [
    "NnLoweringPass",
    "LowerDmaMemoryHierarchyPass",
    "DecompassPass",
    "OutlineDeviceKernelPass",
    "TileAnalysisPass",
    "TileElewisePass",
    "TileReducePass",
    "SymbolLoopHoistPass",
]
