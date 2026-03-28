"""analysis passes package.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 暴露 analysis 类 pass 的入口与公共类型。

使用示例:
- from kernel_gen.passes.analysis import AnalyzeFuncCostPass
- pass_obj = AnalyzeFuncCostPass()

关联文件:
- spec: spec/pass/analysis/func_cost.md
- test: test/pass/test_analysis_func_cost.py
- 功能实现: kernel_gen/passes/analysis/func_cost.py
"""

from .func_cost import AnalyzeFuncCostPass, FuncCostAnalysisError, FuncCostSummary, OpCost

__all__ = [
    "AnalyzeFuncCostPass",
    "FuncCostAnalysisError",
    "FuncCostSummary",
    "OpCost",
]
