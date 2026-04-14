时间：2026-04-15 02:16 +0800
经办人：睡觉小分队
任务：T-20260415-b12af343
任务目标：统一流程口径，要求李白在合并完成后自行执行 `-done`，并同步相关角色提示词与流程说明。
改动：
- 更新 `agents/codex-multi-agents/agents/李白/李白.prompt.md`：将 merge 链路调整为“合并完成后先 `-done` 再 `-talk` 回报管理员”，并补充对应脚本示例。
- 更新 `agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md`：归档链路与自检口径改为“归档 merge 任务由李白执行 `-done` 后，管理员再执行 `-done-plan`”；脚本示例中将管理员 `-done` 示例改为非 merge 场景。
- 更新 `agents/standard/协作执行通用规则.md`：统一通用链路为“李白合并后执行 `-done`，再通知管理员推进”。
- 更新 `agents/standard/角色权限矩阵.md`：merge 角色允许命令补充 `-done`，并补充仅可完成“本人指派的 merge 任务”的约束。
- 更新 `agents/standard/任务记录约定.md`：合并任务结论模板改为“已执行 `-done` 后通知管理员继续推进”。
- 更新 `spec/codex-multi-agents/scripts/codex-multi-agents-task.md`：在 `-done` 权限与注意事项中补充流程要求：merge 任务合并完成后由合并角色自行执行 `-done`。
验证：
- `rg -n "请管理员执行 -done|由管理员执行 -done|合并后由管理员执行 -done" agents/standard agents/codex-multi-agents/agents spec/codex-multi-agents/scripts -g '*.md'`：无命中，未发现“管理员代执行 merge 任务 -done”的口径。
- `rg -n "merge.*-done|李白.*-done|合并完成后.*-done" agents/standard agents/codex-multi-agents/agents spec/codex-multi-agents/scripts -g '*.md'`：确认新链路口径在角色提示词、标准流程与脚本 spec 中一致。
结论：spec 与流程说明已同步完成；下一步建议进入 `review`，重点复核“merge 任务由李白执行 `-done`、管理员只做推进与 `-done-plan`”是否全链路一致。

时间：2026-04-15 02:33 +0800
经办人：提莫炖蘑菇
任务：T-20260415-b12af343
任务目标：复核“李白合并后自行执行 -done 并 -talk 回报管理员”与“管理员不代执行 merge 任务 -done”在提示词、标准流程与 task 脚本 spec 的一致性。
改动：
- 审查结论：通过。
- 已核对文件：
  - `agents/codex-multi-agents/agents/李白/李白.prompt.md`
  - `agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md`
  - `agents/standard/协作执行通用规则.md`
  - `spec/codex-multi-agents/scripts/codex-multi-agents-task.md`
  - `agents/standard/角色权限矩阵.md`（用于交叉核对权限口径）
- 一致性结果：
  - 李白提示词明确要求：合并成功后先 `-done`，再 `-talk` 回报管理员。
  - 管理员提示词明确要求：`merge` 任务由李白执行 `-done`，管理员不代执行；管理员负责后续推进与计划归档动作。
  - 协作通用规则明确链路：李白“写日志 -> 合并 -> `-done` -> `-talk`”。
  - task 脚本 spec 明确流程要求：`merge` 任务合并完成后由合并角色自行 `-done`，管理员不代执行该动作。
验证：
- `rg -n "T-20260415-b12af343" /home/lfr/kernelcode_generate/TODO.md` -> 命中“正在执行的任务”，指派为提莫炖蘑菇。
- `git diff --name-only`（worktree：`wt-20260415-libai-self-done-policy`）-> 本任务改动包含李白/神秘人提示词、通用规则、权限矩阵、任务记录约定与 task spec。
- `rg -n "合并.*-done|李白.*-done|管理员.*-done|done-plan|merge" agents/codex-multi-agents/agents/李白/李白.prompt.md agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md agents/standard/协作执行通用规则.md spec/codex-multi-agents/scripts/codex-multi-agents-task.md` -> 关键口径均有明确命中，未发现互相冲突表述。
结论：通过。当前口径一致：李白合并后自行执行 `-done` 并 `-talk` 回报管理员，管理员不代执行 merge 任务 `-done`；可按流程执行 `-next -auto` 续接到 merge。
