"""Template-name pass internal implementation package.


功能说明:
- 聚合 template-name graph、constraint registry、default constraints 与 infer pass 的真实实现模块。
- 本 package root 只作为内部目录边界，不 re-export 公开对象；公开导入路径仍是旧根兼容模块。

API 列表:
- 无公开 API；`__all__ = []`

使用示例:
- # 内部消费者按具体实现模块导入，例如本目录下的 infer.py。
- # 外部 caller 使用 kernel_gen.passes.TemplateNameInferPass 包根 re-export，
- # 或直接导入 kernel_gen.passes.template_name.infer。

关联文件:
- spec: spec/pass/template_name_graph.md
- spec: spec/pass/template_name_constraints.md
- spec: spec/pass/template_name_default_constraints.md
- spec: spec/pass/template_name_infer.md
- test: test/passes/test_registry.py
- 功能实现: kernel_gen/passes/template_name/graph.py
- 功能实现: kernel_gen/passes/template_name/constraints.py
- 功能实现: kernel_gen/passes/template_name/default_constraints.py
- 功能实现: kernel_gen/passes/template_name/infer.py
"""

__all__: list[str] = []
