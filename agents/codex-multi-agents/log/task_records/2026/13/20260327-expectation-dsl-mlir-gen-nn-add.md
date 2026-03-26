时间: 2026-03-27 02:07:48 +0800
任务: T-20260327-2e2a020b
任务目标: 在 /home/lfr/kernelcode_generate/wt-20260327-expectation-dsl-mlir-gen-nn-add 执行 spec 阶段：仅同步 expectation/dsl/mlir_gen/dialect/nn/add.py 到主目录版本，并补齐 spec/dsl/{ast,emit_mlir,mlir_gen}.md 中 nn.add 的入口约束、错误路径与测试映射；禁止同任务做实现/测试。
改动: 已将 worktree 下 expectation/dsl/mlir_gen/dialect/nn/add.py 覆盖为主目录同路径版本并校验一致；更新 spec/dsl/ast.md、spec/dsl/emit_mlir.md、spec/dsl/mlir_gen.md，补充 nn.add 双入口约束（nn.add 与 BinaryExprAST(op="add") 等价）、broadcast mismatch 诊断口径 Implicit broadcast dimension mismatch、dtype 对齐需经 dma.cast 的阶段职责，以及 AST-012A、EMIT-026A/B/C、MGEN-032A/B/C 测试映射（其中 EMIT-026C、MGEN-032C 标注为实现阶段补充）。
结论: 任务范围内仅涉及 expectation 同步与 spec 文档更新，未修改实现与测试代码，未执行测试命令；可进入实现阶段，按 EMIT-026C 与 MGEN-032C 完成 nn.add dtype promotion lowering 与用例闭环。
