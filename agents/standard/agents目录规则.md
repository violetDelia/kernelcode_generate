# agents 目录规则

## 文件说明
- 功能说明：统一约束 `agents/` 目录下通用文件、任务记录文件与 `memory.md` 的使用边界，减少各角色提示词中的重复描述。
- 使用示例：各角色提示词可直接引用本文件，例如：`通用规则以 [agents目录规则](../../../standard/agents目录规则.md) 为准。`
- 使用示例：当任务进入合并阶段时，按本文件核对记录文件是否随业务改动一并进入合并提交。

## 通用规则

- 每个角色私有的 `memory.md` 只记录关键规则、长期约束、重大决策、异常阻塞与重要上下文，不记录日常执行结果；新增记录时最新内容写在最前面。
- `agents/` 目录内除 `task_records` 外的文件仅在主分支更新，例如 `talk.log`、`agents-lists.md`；`agents/codex-multi-agents/log/task_records/` 下的任务日志在对应 `worktree` 更新。若记录路径不存在，可按规则创建。
- 同一任务链（`spec/实现/审查/复审/合并`）只使用同一个记录文件，该记录文件在对应 `worktree` 更新。
- 所有任务记录均以 [`agents/standard/任务记录约定.md`](/home/lfr/kernelcode_generate/agents/standard/任务记录约定.md) 为准。
- 合并任务必须带上 `agents/codex-multi-agents/log/task_records/...` 下的对应日志；合并提交只包含业务文件与任务日志。
- 合并任务执行 `-done` 后，当前链路记录文件立即封板，禁止继续追加更新；如需 `origin/main` 同步确认或其他后续跟踪，必须新建独立任务并使用独立记录文件。
