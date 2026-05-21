"""Template-name constraint registry public compatibility entry.


功能说明:
- 保留 `kernel_gen.passes.template_name_constraints` 公开导入路径。
- 真实实现位于 `kernel_gen.passes.template_name.constraints`。

API 列表:
- `class TemplateValueRef(kind: Literal["operand", "result"], index: int)`
- `class SameSpec(lhs: TemplateValueRef, rhs: TemplateValueRef)`
- `class VerifyOnlySpec(item: TemplateValueRef)`
- `TemplateConstraintSpec = SameSpec | VerifyOnlySpec`
- `TemplateConstraintBuilder = Callable[[Operation], tuple[TemplateNameConstraint, ...]]`
- `register_template_constraints(op_name: str, constraints: tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder) -> None`
- `get_template_constraints(op_name: str) -> tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder`
- `build_template_constraints(op: Operation) -> tuple[TemplateNameConstraint, ...]`

使用示例:
- from kernel_gen.passes.template_name_constraints import build_template_constraints
- constraints = build_template_constraints(op)

关联文件:
- spec: spec/pass/template_name_constraints.md
- test: test/passes/test_template_name_constraints.py
- 功能实现: kernel_gen/passes/template_name/constraints.py
- 兼容入口: kernel_gen/passes/template_name_constraints.py
"""

from kernel_gen.passes.template_name.constraints import (
    SameSpec,
    TemplateConstraintBuilder,
    TemplateConstraintSpec,
    TemplateValueRef,
    VerifyOnlySpec,
    build_template_constraints,
    get_template_constraints,
    register_template_constraints,
)

__all__ = [
    "TemplateValueRef",
    "SameSpec",
    "VerifyOnlySpec",
    "TemplateConstraintSpec",
    "TemplateConstraintBuilder",
    "register_template_constraints",
    "get_template_constraints",
    "build_template_constraints",
]
