"""decompass compatibility export.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 为仍使用 `kernel_gen.passes.decompass` 导入路径的调用方保留兼容入口。
- 真实实现继续收口在 `kernel_gen.passes.lowering.decompass`。

使用示例:
- from kernel_gen.passes.decompass import DecompassPass
- module = DecompassPass().run(module)

关联文件:
- spec: [spec/pass/lowering/decompass.md](spec/pass/lowering/decompass.md)
- test: [test/pass/test_decompose_nn_softmax.py](test/pass/test_decompose_nn_softmax.py)
- 功能实现: [kernel_gen/passes/decompass.py](kernel_gen/passes/decompass.py)
"""

from .lowering.decompass import DecompassError, DecompassPass, register_decompass_rewrite

__all__ = ["DecompassPass", "DecompassError", "register_decompass_rewrite"]
