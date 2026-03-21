# 20260321-operation-scf-spec

## T-20260321-6fb6c202

- 时间：2026-03-21 20:42:42 +0800
- 角色：`李白`
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-operation-scf-spec`
- 任务描述：重构 `spec/operation/scf.md` 并补齐可执行测试设计。
- 变更文件：
  - `spec/operation/scf.md`
- 核心变更：
  - 补齐 `loop` 的测试目标与用例映射，覆盖整数循环、符号维度、`step==0` 与非法类型报错、半开区间语义。
  - 更新测试文件路径与执行命令，明确后续实现链路可直接接入。
  - 补充返回对象需暴露 `start/end/step` 的约束以支持 DSL 与测试校验。
- 测试：
  - 未执行（按任务要求仅改 spec）。
