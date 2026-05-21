"""Template-name graph public compatibility entry.


功能说明:
- 保留 `kernel_gen.passes.template_name_graph` 公开导入路径。
- 真实实现位于 `kernel_gen.passes.template_name.graph`。

API 列表:
- `class TemplateNameValue(value: SSAValue, op: Operation, kind: Literal["operand", "result", "block_arg"], index: int)`
- `class Same(lhs: TemplateNameValue, rhs: TemplateNameValue)`
- `class VerifyOnly(item: TemplateNameValue)`
- `TemplateNameConstraint = Same | VerifyOnly`
- `class TemplateNameSolution(names: Mapping[SSAValue, str])`
- `TemplateNameSolution.name_of(self, value: SSAValue) -> str | None`
- `class TemplateNameGraph()`
- `TemplateNameGraph.add_value(self, item: TemplateNameValue) -> None`
- `TemplateNameGraph.add_constraint(self, constraint: TemplateNameConstraint) -> None`
- `TemplateNameGraph.add_constraints(self, constraints: Sequence[TemplateNameConstraint]) -> None`
- `TemplateNameGraph.add_signature_seed(self, item: TemplateNameValue) -> None`
- `TemplateNameGraph.solve(self) -> TemplateNameSolution`

使用示例:
- from kernel_gen.passes.template_name_graph import TemplateNameGraph
- graph = TemplateNameGraph()

关联文件:
- spec: spec/pass/template_name_graph.md
- test: test/passes/test_template_name_graph.py
- 功能实现: kernel_gen/passes/template_name/graph.py
- 兼容入口: kernel_gen/passes/template_name_graph.py
"""

from kernel_gen.passes.template_name.graph import (
    Same,
    TemplateNameConstraint,
    TemplateNameGraph,
    TemplateNameSolution,
    TemplateNameValue,
    VerifyOnly,
)

__all__ = [
    "TemplateNameValue",
    "Same",
    "VerifyOnly",
    "TemplateNameConstraint",
    "TemplateNameSolution",
    "TemplateNameGraph",
]
