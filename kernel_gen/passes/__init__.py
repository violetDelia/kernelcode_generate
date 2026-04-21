"""pass package.

创建者: 李白
最后一次更改: 小李飞刀

功能说明:
- 暴露 Pass 管理相关实现。
- 暴露 `buffer-results-to-out-params` 的公开入口。
- 暴露 `decompass` 专题 pass 的根路径入口。
- 暴露 `outline-device-kernel` 的公开入口。
- 暴露 `symbol-loop-hoist` 专题 pass 的根路径入口。
- 暴露 `tile-analysis` 的公开入口。
- 暴露 `tile-elewise` 的公开入口。
- 暴露 `tile-reduce` 的公开入口。

使用示例:
- import importlib
- pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
- Pass, PassManager = pass_module.Pass, pass_module.PassManager
- from kernel_gen.passes import BufferResultsToOutParamsPass, DecompassPass
- buffer_pass = BufferResultsToOutParamsPass()
- decompass_pass = DecompassPass()
- from kernel_gen.passes import OutlineDeviceKernelPass
- outline_pass = OutlineDeviceKernelPass()
- from kernel_gen.passes import TileAnalysisPass
- tile_analysis_pass = TileAnalysisPass()
- from kernel_gen.passes import TileElewisePass, TileReducePass
- tile_elewise_pass = TileElewisePass()
- tile_reduce_pass = TileReducePass()
- from kernel_gen.passes import SymbolLoopHoistPass
- hoist_pass = SymbolLoopHoistPass()

关联文件:
- spec:
  - spec/pass/pass_manager.md
  - spec/pass/lowering/buffer_results_to_out_params.md
  - spec/pass/decompass.md
  - spec/pass/outline_device_kernel.md
  - spec/pass/symbol_loop_hoist.md
- test:
  - test/pass/test_pass_manager.py
  - test/pass/test_buffer_results_to_out_params.py
  - test/pass/decompass/test_softmax.py
  - test/pass/outline_device_kernel/test_outline_device_kernel.py
- test/pass/test_lowering_tile_analysis.py
- test/pass/test_lowering_tile_elewise.py
- test/pass/test_lowering_tile_reduce.py
- test/pass/test_symbol_loop_hoist.py
- 功能实现:
  - kernel_gen/passes/pass_manager.py
  - kernel_gen/passes/buffer_results_to_out_params.py
  - kernel_gen/passes/decompass.py
  - kernel_gen/passes/outline_device_kernel.py
- kernel_gen/passes/lowering/tile_analysis.py
- kernel_gen/passes/lowering/tile_elewise.py
- kernel_gen/passes/lowering/tile_reduce.py
- kernel_gen/passes/symbol_loop_hoist.py
"""

from .buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)
from .decompass import DecompassError, DecompassPass, register_decompass_rewrite
from .outline_device_kernel import OutlineDeviceKernelError, OutlineDeviceKernelPass
from .lowering.tile_analysis import TileAnalysisPass
from .lowering.tile_elewise import TileElewisePass
from .lowering.tile_reduce import TileReducePass
from .pass_manager import Pass, PassManager
from .symbol_loop_hoist import SymbolLoopHoistError, SymbolLoopHoistPass

__all__ = [
    "Pass",
    "PassManager",
    "BufferResultsToOutParamsPass",
    "BufferResultsToOutParamsError",
    "DecompassPass",
    "DecompassError",
    "register_decompass_rewrite",
    "OutlineDeviceKernelPass",
    "OutlineDeviceKernelError",
    "TileAnalysisPass",
    "TileElewisePass",
    "TileReducePass",
    "SymbolLoopHoistPass",
    "SymbolLoopHoistError",
]
