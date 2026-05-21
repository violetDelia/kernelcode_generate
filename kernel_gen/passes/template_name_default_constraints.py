"""Default template-name constraints public compatibility entry.


功能说明:
- 保留 `kernel_gen.passes.template_name_default_constraints` 公开导入路径。
- 真实实现位于 `kernel_gen.passes.template_name.default_constraints`。

API 列表:
- `register_default_template_constraints() -> None`

使用示例:
- from kernel_gen.passes.template_name_default_constraints import register_default_template_constraints
- register_default_template_constraints()

关联文件:
- spec: spec/pass/template_name_default_constraints.md
- test: test/passes/test_template_name_constraints.py
- 功能实现: kernel_gen/passes/template_name/default_constraints.py
- 兼容入口: kernel_gen/passes/template_name_default_constraints.py
"""

from kernel_gen.passes.template_name.default_constraints import register_default_template_constraints

__all__ = ["register_default_template_constraints"]
