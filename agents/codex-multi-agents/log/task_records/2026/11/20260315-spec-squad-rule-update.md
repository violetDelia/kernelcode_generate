# spec-squad-rule-update-20260315 记录

## 2026-03-15-rule-update

- 时间：2026-03-15 19:52:55 +0800
- 角色：规格小队
- 任务描述：同步规格小队 prompt 新增规则，并立即开始执行。
- worktree：`N/A`
- 规则内容：
  - 删除任何 worktree 前，必须先检查该 worktree 是否仍有其他正在进行的任务。
  - 若存在其他正在进行的任务，则禁止删除该 worktree，并立即向管理员说明原因。
- 执行说明：
  - 后续凡涉及 worktree 删除，均先核对该 worktree 是否被其他进行中任务占用。
  - 若发现进行中任务，将停止删除动作并优先向管理员回报阻塞原因。
@规格小队向@神秘人发起会话: 已同步规则更新：后续如涉及删除 worktree，将先检查该 worktree 是否仍有其他正在进行的任务；若有，则禁止删除并立即说明原因，worktree=N/A，记录：agents/codex-multi-agents/log/task_records/2026/11/20260315-spec-squad-rule-update.md。
