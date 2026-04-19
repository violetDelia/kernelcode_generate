"""pass package.

创建者: 李白
最后一次更改: 李白

功能说明:
- 暴露 Pass 管理相关实现。
- 暴露 `buffer-results-to-out-params` 的公开入口。
- 暴露 `decompass` 专题 pass 的根路径入口。

使用示例:
- import importlib
- pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
- Pass, PassManager = pass_module.Pass, pass_module.PassManager
- from kernel_gen.passes import BufferResultsToOutParamsPass, DecompassPass
- buffer_pass = BufferResultsToOutParamsPass()
- decompass_pass = DecompassPass()

关联文件:
- spec:
  - spec/pass/pass_manager.md
  - spec/pass/lowering/buffer_results_to_out_params.md
  - spec/pass/decompass.md
- test:
  - test/pass/test_pass_manager.py
  - test/pass/test_buffer_results_to_out_params.py
  - test/pass/decompass/test_softmax.py
- 功能实现:
  - kernel_gen/passes/pass_manager.py
  - kernel_gen/passes/buffer_results_to_out_params.py
  - kernel_gen/passes/decompass.py
"""

from .buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)
from .decompass import DecompassError, DecompassPass, register_decompass_rewrite
from .pass_manager import Pass, PassManager

__all__ = [
    "Pass",
    "PassManager",
    "BufferResultsToOutParamsPass",
    "BufferResultsToOutParamsError",
    "DecompassPass",
    "DecompassError",
    "register_decompass_rewrite",
]
