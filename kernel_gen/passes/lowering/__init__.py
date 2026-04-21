"""lowering pass compatibility package.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 提供 nn -> kernel lowering pass 的公开入口。
- 提供 `LowerNnToKernelPass` 兼容入口。
- 提供 buffer-results-to-out-params 的 lowering 兼容入口。
- 提供 lower-dma-memory-hierarchy pass 的公开入口。
- 提供 decompass pass 的公开入口。
- 提供 outline-device-kernel 的 lowering 兼容入口。
- 提供 tile-analysis / tile-elewise / tile-reduce ModulePass、tile pass 与 kernel_split 兼容入口。
- 提供 symbol-loop-hoist 的兼容入口。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- pass_obj = NnLoweringPass()
- from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
- pass_obj = LowerNnToKernelPass()
- from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
- pass_obj = BufferResultsToOutParamsPass()
- from kernel_gen.passes.lowering.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
- pass_obj = LowerDmaMemoryHierarchyPass()
- from kernel_gen.passes.decompass import DecompassPass
- pass_obj = DecompassPass()
- from kernel_gen.passes.lowering import OutlineDeviceKernelPass
- pass_obj = OutlineDeviceKernelPass()
- from kernel_gen.passes.lowering.tile_analysis import TileAnalysisPass
- pass_obj = TileAnalysisPass()
- from kernel_gen.passes.lowering.tile_elewise import TileElewisePass
- pass_obj = TileElewisePass()
- from kernel_gen.passes.lowering.tile_reduce import TileReducePass
- pass_obj = TileReducePass()
- from kernel_gen.passes.lowering.tile import TilePass
- pass_obj = TilePass()
- from kernel_gen.passes import SymbolLoopHoistPass
- pass_obj = SymbolLoopHoistPass()

关联文件:
- spec:
  - [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
  - [spec/pass/lowering/buffer_results_to_out_params.md](spec/pass/lowering/buffer_results_to_out_params.md)
  - [spec/pass/lowering/dma_memory_hierarchy.md](spec/pass/lowering/dma_memory_hierarchy.md)
  - [spec/pass/decompass.md](spec/pass/decompass.md)
  - [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
  - [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
  - [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
  - [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
  - [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
  - [spec/pass/lowering/kernel_split.md](spec/pass/lowering/kernel_split.md)
  - [spec/pass/symbol_loop_hoist.md](spec/pass/symbol_loop_hoist.md)
- test:
  - [test/pass/nn_lowering/public_name.py](test/pass/nn_lowering/public_name.py)
  - [test/pass/nn_lowering/test_lowering_nn_lowering.py](test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [test/pass/test_buffer_results_to_out_params.py](test/pass/test_buffer_results_to_out_params.py)
  - [test/pass/test_dma_memory_hierarchy.py](test/pass/test_dma_memory_hierarchy.py)
  - [test/pass/decompass/test_softmax.py](test/pass/decompass/test_softmax.py)
  - [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
  - [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
  - [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
  - [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
  - [test/pass/test_lowering_kernel_split.py](test/pass/test_lowering_kernel_split.py)
  - [test/pass/test_symbol_loop_hoist.py](test/pass/test_symbol_loop_hoist.py)
- 功能实现:
  - [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [kernel_gen/passes/lowering/nn_to_kernel.py](kernel_gen/passes/lowering/nn_to_kernel.py)
  - [kernel_gen/passes/buffer_results_to_out_params.py](kernel_gen/passes/buffer_results_to_out_params.py)
  - [kernel_gen/passes/lowering/buffer_results_to_out_params.py](kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - [kernel_gen/passes/lowering/dma_memory_hierarchy.py](kernel_gen/passes/lowering/dma_memory_hierarchy.py)
  - [kernel_gen/passes/decompass.py](kernel_gen/passes/decompass.py)
  - [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
  - [kernel_gen/passes/lowering/tile_analysis.py](kernel_gen/passes/lowering/tile_analysis.py)
  - [kernel_gen/passes/lowering/tile_elewise.py](kernel_gen/passes/lowering/tile_elewise.py)
  - [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
  - [kernel_gen/passes/lowering/__init__.py](kernel_gen/passes/lowering/__init__.py)
  - [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
  - [kernel_gen/passes/lowering/kernel_split.py](kernel_gen/passes/lowering/kernel_split.py)
  - [kernel_gen/passes/symbol_loop_hoist.py](kernel_gen/passes/symbol_loop_hoist.py)
"""

import sys

from .nn_lowering import NnLoweringError, NnLoweringPass
from .nn_to_kernel import LowerNnToKernelPass
from .. import outline_device_kernel as _outline_device_kernel_module
from .. import symbol_loop_hoist as _symbol_loop_hoist_module
from ..buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)
from .dma_memory_hierarchy import (
    LowerDmaMemoryHierarchyError,
    LowerDmaMemoryHierarchyPass,
)
from ..decompass import DecompassError, DecompassPass, register_decompass_rewrite
from .kernel_split import KernelSplitError, KernelSplitPass
from ..outline_device_kernel import OutlineDeviceKernelError, OutlineDeviceKernelPass
from ..symbol_loop_hoist import SymbolLoopHoistError, SymbolLoopHoistPass
from .tile import TilePass, TilePassError
from .tile_analysis import TileAnalysisPass
from .tile_elewise import TileElewisePass

outline_device_kernel = _outline_device_kernel_module
sys.modules.setdefault(__name__ + ".outline_device_kernel", _outline_device_kernel_module)
symbol_loop_hoist = _symbol_loop_hoist_module
sys.modules.setdefault(__name__ + ".symbol_loop_hoist", _symbol_loop_hoist_module)

__all__ = [
    "NnLoweringPass",
    "NnLoweringError",
    "BufferResultsToOutParamsPass",
    "BufferResultsToOutParamsError",
    "LowerDmaMemoryHierarchyPass",
    "LowerDmaMemoryHierarchyError",
    "DecompassPass",
    "DecompassError",
    "register_decompass_rewrite",
    "OutlineDeviceKernelPass",
    "OutlineDeviceKernelError",
    "TilePass",
    "TilePassError",
    "TileAnalysisPass",
    "TileElewisePass",
    "TileReducePass",
    "TileReduceError",
    "KernelSplitPass",
    "KernelSplitError",
    "SymbolLoopHoistPass",
    "SymbolLoopHoistError",
]


def __getattr__(name: str):
    if name in {"TileReducePass", "TileReduceError"}:
        from .tile_reduce import TileReduceError, TileReducePass

        globals()["TileReducePass"] = TileReducePass
        globals()["TileReduceError"] = TileReduceError
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
