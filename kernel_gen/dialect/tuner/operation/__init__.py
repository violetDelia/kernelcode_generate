"""tuner operation package.

功能说明:
- 聚合 tuner package 内公开 op。

API 列表:
- `class TunerParamOp(result_type: Attribute)`
- `class TunerCostOp(...)`
- `class TunerSelectOp(patterns: Sequence[str | SymbolRefAttr], result_type: Attribute = SymbolValueType.from_expr("pattern_id"), *, args: Sequence[SSAValue | Operation] = (), tuner_args: Sequence[SSAValue | Operation] = ())`
- `class TunerLaunchOp(...)`

使用示例:
- `from kernel_gen.dialect.tuner.operation import ...`

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/tuner/
- 功能实现: kernel_gen/dialect/tuner/operation/__init__.py
"""

from __future__ import annotations

from .cost import TunerCostOp
from .launch import TunerLaunchOp
from .param import TunerParamOp
from .select import TunerSelectOp

__all__ = ["TunerCostOp", "TunerLaunchOp", "TunerParamOp", "TunerSelectOp"]
