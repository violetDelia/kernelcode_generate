"""buffer-results-to-out-params lowering compatibility shim.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 为仍从 `kernel_gen.passes.lowering.buffer_results_to_out_params` 导入的调用方提供兼容转发。
- 实际实现位于 `kernel_gen.passes.buffer_results_to_out_params`。

使用示例:
- from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
- pass_obj = BufferResultsToOutParamsPass()

关联文件:
- spec: spec/pass/lowering/buffer_results_to_out_params.md
- test: test/pass/test_buffer_results_to_out_params.py
- 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
"""

from __future__ import annotations

from kernel_gen.passes.buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)

__all__ = ["BufferResultsToOutParamsPass", "BufferResultsToOutParamsError"]
