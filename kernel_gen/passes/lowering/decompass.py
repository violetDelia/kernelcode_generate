"""decompass pass 公开入口。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 `decompass` pass 的稳定导入路径。
- 对外公开 `DecompassPass`、`DecompassError` 与 `register_decompass_rewrite`。

使用示例:
- from kernel_gen.passes.lowering.decompass import DecompassPass
- module = DecompassPass().run(module)

关联文件:
- spec: spec/pass/lowering/decompass.md
- test: test/pass/test_decompose_nn_softmax.py
- 功能实现: kernel_gen/passes/lowering/decompose_nn_softmax.py
"""

from .decompose_nn_softmax import (
    DecompassError,
    DecompassPass,
    register_decompass_rewrite,
)

__all__ = ["DecompassPass", "DecompassError", "register_decompass_rewrite"]
