"""tuner dialect package root.

功能说明:
- 暴露 tuner dialect 稳定 root API。

API 列表:
- `Tuner`
- `class TunerCostOp(operands: list[SSAValue | Operation], *, cost_kind: Attribute, op_name: Attribute, extra_attrs: dict[str, Attribute] | None = None, result_type: Attribute = SymbolValueType.from_expr("COST"))`
- `class TunerLaunchOp(callee: str | SymbolRefAttr, args: Sequence[SSAValue | Operation] = ())`
- `class TunerParamOp(result_type: Attribute)`
- `class TunerSelectOp(patterns: Sequence[str | SymbolRefAttr], result_type: Attribute = SymbolValueType.from_expr("pattern_id"))`

使用示例:
- `from kernel_gen.dialect.tuner import Tuner, TunerCostOp, TunerSelectOp`

关联文件:
- spec: spec/dialect/tuner.md
- test: test/dialect/tuner/
- 功能实现: kernel_gen/dialect/tuner/__init__.py
"""

from __future__ import annotations

from xdsl.ir import Dialect

from .operation import TunerCostOp, TunerLaunchOp, TunerParamOp, TunerSelectOp

Tuner = Dialect("tuner", [TunerParamOp, TunerCostOp, TunerSelectOp, TunerLaunchOp], [])

__all__ = [
    "Tuner",
    "TunerCostOp",
    "TunerLaunchOp",
    "TunerParamOp",
    "TunerSelectOp",
]
