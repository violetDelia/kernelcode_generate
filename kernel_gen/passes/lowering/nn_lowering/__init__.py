"""nn_lowering pass 公共入口。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 对外暴露 `NnLoweringPass` 与相关错误类型。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- module = NnLoweringPass().run(module)

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/public_name.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/__init__.py
"""

from .nn_lowering import NnLoweringError, NnLoweringPass

__all__ = ["NnLoweringPass", "NnLoweringError"]
