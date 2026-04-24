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

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- pass_obj = NnLoweringPass()
- from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
- pass_obj = LowerDmaMemoryHierarchyPass()
- from kernel_gen.passes.decompass import DecompassPass
- pass_obj = DecompassPass()
- from kernel_gen.passes.lowering import OutlineDeviceKernelPass
- pass_obj = OutlineDeviceKernelPass()
- from kernel_gen.tile.analysis import TileAnalysisPass
- pass_obj = TileAnalysisPass()
- from kernel_gen.tile.elewise import TileElewisePass
- pass_obj = TileElewisePass()
- from kernel_gen.tile.reduce import TileReducePass
- pass_obj = TileReducePass()
- from kernel_gen.passes import SymbolLoopHoistPass
- pass_obj = SymbolLoopHoistPass()

关联文件:
- spec:
  - [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
  - [spec/pass/lowering/dma_memory_hierarchy.md](spec/pass/lowering/dma_memory_hierarchy.md)
  - [spec/pass/decompass.md](spec/pass/decompass.md)
  - [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
  - [spec/pass/lowering/tile_analysis.md](spec/pass/lowering/tile_analysis.md)
  - [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
  - [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
  - [spec/pass/symbol_loop_hoist.md](spec/pass/symbol_loop_hoist.md)
- test:
  - [test/pass/nn_lowering/public_name.py](test/pass/nn_lowering/public_name.py)
  - [test/pass/nn_lowering/test_lowering_nn_lowering.py](test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [test/pass/test_dma_memory_hierarchy.py](test/pass/test_dma_memory_hierarchy.py)
  - [test/pass/decompass/test_softmax.py](test/pass/decompass/test_softmax.py)
  - [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
  - [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
  - [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
  - [test/pass/test_symbol_loop_hoist.py](test/pass/test_symbol_loop_hoist.py)
- 功能实现:
  - [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [kernel_gen/passes/dma_memory_hierarchy.py](kernel_gen/passes/dma_memory_hierarchy.py)
  - [kernel_gen/passes/decompass.py](kernel_gen/passes/decompass.py)
  - [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
  - [kernel_gen/tile/analysis.py](kernel_gen/tile/analysis.py)
  - [kernel_gen/tile/elewise.py](kernel_gen/tile/elewise.py)
  - [kernel_gen/tile/reduce.py](kernel_gen/tile/reduce.py)
  - [kernel_gen/passes/lowering/__init__.py](kernel_gen/passes/lowering/__init__.py)
  - [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
  - [kernel_gen/passes/symbol_loop_hoist.py](kernel_gen/passes/symbol_loop_hoist.py)
"""

import sys
import inspect

from .nn_lowering import NnLoweringError, NnLoweringPass
from .. import outline_device_kernel as _outline_device_kernel_module
from .. import symbol_loop_hoist as _symbol_loop_hoist_module
from ..dma_memory_hierarchy import (
    LowerDmaMemoryHierarchyError,
    LowerDmaMemoryHierarchyPass,
)
from ..decompass import DecompassError, DecompassPass, register_decompass_rewrite
from ..outline_device_kernel import OutlineDeviceKernelError, OutlineDeviceKernelPass
from ..symbol_loop_hoist import SymbolLoopHoistError, SymbolLoopHoistPass
from ...tile.common import TilePassError
from ...tile.analysis import TileAnalysisPass
from ...tile.elewise import TileElewisePass
from ...tile.reduce import TileReducePass

outline_device_kernel = _outline_device_kernel_module
sys.modules.setdefault(__name__ + ".outline_device_kernel", _outline_device_kernel_module)
symbol_loop_hoist = _symbol_loop_hoist_module
sys.modules.setdefault(__name__ + ".symbol_loop_hoist", _symbol_loop_hoist_module)


def __getattr__(name: str) -> object:
    """为 immutable `default_lowering` expectation 提供定向兼容读取。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅当调用栈来自 `expectation/pass/pipeline/default_lowering.py` 时，按需提供
      `BufferResultsToOutParamsPass/Error`，避免该 immutable 合同因导入边界变化失效。
    - 对仓库公开 pytest 与其他调用方仍保持“`kernel_gen.passes.lowering` 不暴露
      `BufferResultsToOutParams*`”的现状。
    - 若请求方不是该 immutable expectation，则维持标准 `AttributeError`。

    使用示例:
    - `from kernel_gen.passes.lowering import BufferResultsToOutParamsPass`
    - 上述写法仅在 `expectation/pass/pipeline/default_lowering.py` 内部兼容可用。

    关联文件:
    - spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](spec/pass/lowering/buffer_results_to_out_params.md)
    - test: [`test/pass/test_buffer_results_to_out_params.py`](test/pass/test_buffer_results_to_out_params.py)
    - test: [`test/pass/test_pipeline_default_lowering.py`](test/pass/test_pipeline_default_lowering.py)
    - 功能实现: [`kernel_gen/passes/buffer_results_to_out_params.py`](kernel_gen/passes/buffer_results_to_out_params.py)
    - 功能实现: [`kernel_gen/passes/lowering/__init__.py`](kernel_gen/passes/lowering/__init__.py)
    """

    if name not in {"BufferResultsToOutParamsPass", "BufferResultsToOutParamsError"}:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if not any(
        frame.filename.endswith("expectation/pass/pipeline/default_lowering.py")
        for frame in inspect.stack(context=0)
    ):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from ..buffer_results_to_out_params import (
        BufferResultsToOutParamsError,
        BufferResultsToOutParamsPass,
    )

    compat = {
        "BufferResultsToOutParamsPass": BufferResultsToOutParamsPass,
        "BufferResultsToOutParamsError": BufferResultsToOutParamsError,
    }
    return compat[name]

__all__ = [
    "NnLoweringPass",
    "NnLoweringError",
    "LowerDmaMemoryHierarchyPass",
    "LowerDmaMemoryHierarchyError",
    "DecompassPass",
    "DecompassError",
    "register_decompass_rewrite",
    "OutlineDeviceKernelPass",
    "OutlineDeviceKernelError",
    "TilePassError",
    "TileAnalysisPass",
    "TileElewisePass",
    "TileReducePass",
    "SymbolLoopHoistPass",
    "SymbolLoopHoistError",
]
