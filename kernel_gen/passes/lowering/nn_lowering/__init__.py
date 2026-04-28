"""nn_lowering pass 公共入口。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 对外暴露 `NnLoweringPass` 与公开 pattern 集合入口。

API 列表:
- `class NnLoweringPass()`
- `nn_lowering_patterns() -> list[RewritePattern]`

使用示例:
- from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
- from kernel_gen.passes.lowering.nn_lowering import nn_lowering_patterns
- from xdsl.context import Context
- NnLoweringPass().apply(Context(), module)
- patterns = nn_lowering_patterns()

关联文件:
- spec: spec/pass/lowering/nn_lowering/spec.md
- test: test/pass/nn_lowering/public_name.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/__init__.py
"""

from .nn_lowering import NnLoweringPass, nn_lowering_patterns

__all__ = ["NnLoweringPass", "nn_lowering_patterns"]
