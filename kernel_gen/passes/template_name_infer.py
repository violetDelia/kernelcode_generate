"""Template-name inference pass public compatibility entry.


功能说明:
- 保留 `kernel_gen.passes.template_name_infer` 公开导入路径。
- 真实实现位于 `kernel_gen.passes.template_name.infer`。

API 列表:
- `class TemplateNameInferPass(fold: bool = True)`
- `TemplateNameInferPass.from_options(options: dict[str, str]) -> TemplateNameInferPass`
- `TemplateNameInferPass.apply(self, ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.template_name_infer import TemplateNameInferPass
- TemplateNameInferPass().apply(Context(), module)

关联文件:
- spec: spec/pass/template_name_infer.md
- test: test/passes/test_template_name_infer.py
- 功能实现: kernel_gen/passes/template_name/infer.py
- 兼容入口: kernel_gen/passes/template_name_infer.py
"""

from kernel_gen.passes.template_name.infer import TemplateNameInferPass

__all__ = ["TemplateNameInferPass"]
