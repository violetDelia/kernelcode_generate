"""analysis passes package.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 暴露分析类 pass 的公开入口。

使用示例:
- from kernel_gen.passes.analysis.func_cost import AnalyzeFuncCostPass

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
