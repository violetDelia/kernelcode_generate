时间: 2026-03-27 02:01:32 +0800
经手人: 咯咯咯
任务: T-20260327-dc7c8ce2
任务目标: 补齐 get_subthread_num DSL 入口约束/错误路径/测试映射（spec/dsl/{ast,emit_mlir,mlir_gen}.md）。
改动: 核对 spec/dsl/ast.md、spec/dsl/emit_mlir.md、spec/dsl/mlir_gen.md 已包含 get_subthread_num 的入口约束、lowering 约束与测试映射编号；本次未修改 spec 内容，仅补齐任务记录。
结论: spec 阶段无需额外改动，需进入实现/测试阶段补齐 DSL 解析与 lowering，并新增 test/dsl/test_ast_visitor.py 用例。
