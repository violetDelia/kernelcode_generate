"""lowering pass package.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 提供 nn -> kernel lowering pass 的公开入口。
- 提供 `LowerNnToKernelPass` 兼容入口。
- 提供 buffer-results-to-out-params 的 lowering 兼容入口。
- 提供 lower-dma-memory-hierarchy pass 的公开入口。
- 提供 decompass pass 的公开入口。
- 提供 outline-device-kernel pass 的公开入口。
- 提供 tile pass 与 kernel_split 兼容入口。

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
- from kernel_gen.passes.lowering.outline_device_kernel import OutlineDeviceKernelPass
- pass_obj = OutlineDeviceKernelPass()
- from kernel_gen.passes.lowering.tile import TilePass
- pass_obj = TilePass()

关联文件:
- spec:
  - [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
  - [spec/pass/lowering/buffer_results_to_out_params.md](spec/pass/lowering/buffer_results_to_out_params.md)
  - [spec/pass/lowering/dma_memory_hierarchy.md](spec/pass/lowering/dma_memory_hierarchy.md)
  - [spec/pass/decompass.md](spec/pass/decompass.md)
  - [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
  - [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
  - [spec/pass/lowering/kernel_split.md](spec/pass/lowering/kernel_split.md)
- test:
  - [test/pass/nn_lowering/public_name.py](test/pass/nn_lowering/public_name.py)
  - [test/pass/nn_lowering/test_lowering_nn_lowering.py](test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [test/pass/test_buffer_results_to_out_params.py](test/pass/test_buffer_results_to_out_params.py)
  - [test/pass/test_dma_memory_hierarchy.py](test/pass/test_dma_memory_hierarchy.py)
  - [test/pass/decompass/test_softmax.py](test/pass/decompass/test_softmax.py)
  - [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
  - [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
  - [test/pass/test_lowering_kernel_split.py](test/pass/test_lowering_kernel_split.py)
- 功能实现:
  - [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [kernel_gen/passes/lowering/nn_to_kernel.py](kernel_gen/passes/lowering/nn_to_kernel.py)
  - [kernel_gen/passes/buffer_results_to_out_params.py](kernel_gen/passes/buffer_results_to_out_params.py)
  - [kernel_gen/passes/lowering/buffer_results_to_out_params.py](kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - [kernel_gen/passes/lowering/dma_memory_hierarchy.py](kernel_gen/passes/lowering/dma_memory_hierarchy.py)
  - [kernel_gen/passes/decompass.py](kernel_gen/passes/decompass.py)
  - [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
  - [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
  - [kernel_gen/passes/lowering/kernel_split.py](kernel_gen/passes/lowering/kernel_split.py)
"""

from .nn_lowering import NnLoweringError, NnLoweringPass
from .nn_to_kernel import LowerNnToKernelPass
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
from .outline_device_kernel import OutlineDeviceKernelError, OutlineDeviceKernelPass
from .tile import TilePass, TilePassError

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
    "KernelSplitPass",
    "KernelSplitError",
]
