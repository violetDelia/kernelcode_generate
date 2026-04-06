时间：2026-04-06 11:46:18 +0800
经办人：李白
任务：T-20260406-00758808（prompt-only｜除李白外禁用 git，例外仅 worktree add + diff）
任务目标：
- 按用户新规，将 git 禁用规则写入所有角色提示词 `agents/codex-multi-agents/agents/*/*.prompt.md`，并统一放入 `## 禁用` 小节。
- 规则口径：除 `李白` 外，禁止执行任何 `git` 命令；例外仅允许执行 `git worktree add`（仅添加工作树）与 `git diff`（仅查看差异；非必要不要轻易使用）。其余 git 如需使用：先向管理员申请授权，再由 `李白` 代操作。
- `李白.prompt.md` 需额外写明：`李白` 是唯一允许执行全部 git 的角色；其他角色如需执行上述两项以外的 git 操作，必须先向管理员申请授权，再由 `李白` 统一代执行。
改动：
- 在 11 个角色提示词文件中新增 `## 禁用` 小节，并移除原先散落在“访问与约束/绝对约束”中的 git 禁令条款，避免重复与口径漂移。
- 按用户要求：不再添加 `## 元数据` / `最后一次更改：...` 这类元数据块。
- 范围核对：
  - `git status --porcelain=v1`：仅 11 个 `agents/codex-multi-agents/agents/*/*.prompt.md` + 本记录文件发生变更。
  - `git diff --name-only` 与 `git diff --name-only --cached`：应仅包含上述允许文件。
结论：
- 已按新规完成提示词口径同步，变更范围受控（prompt-only + record）。
