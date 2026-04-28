# agents 目录规则

## 文件说明
- 功能说明：统一约束 `agents/` 目录下通用文件、任务记录文件与 `memory.md` 的使用边界，减少各角色提示词中的重复描述。
- 使用示例：各角色提示词可直接引用本文件，例如：`通用规则以 [agents目录规则](../../../standard/agents目录规则.md) 为准。`
- 使用示例：当任务进入合并阶段时，按本文件核对记录文件是否随业务改动一并进入合并提交。
- 入口索引：首次进入 `agents/standard` 时，先看 [`规则索引.md`](规则索引.md)；若术语含义不清，再看 [`术语统一页.md`](术语统一页.md)。

## 通用规则

- 每个角色私有的 `memory.md` 只记录关键规则、长期约束、重大决策、异常阻塞与重要上下文，不记录日常执行结果；新增记录时最新内容写在最前面。
- `agents/` 目录内除 `task_records` 外的文件仅在主分支更新，例如 `talk.log`、`agents-lists.md`；`agents/codex-multi-agents/log/task_records/` 下的常规任务日志、阻塞记录与待确认记录必须在对应 `worktree` 更新，主仓根目录不作为常规日志落点。若记录路径不存在，可按规则创建。
- 禁止在主仓根目录更新常规任务日志；只有无独立任务 `worktree` 的计划互评、专题 `spec` 互评、终验或归档结论，才按规则写入计划书、专题 `spec` 正文或 `done_plan` 记录文件。
- 同一计划级任务链（`execute/review/复审/合并`）只使用同一个记录文件，该记录文件必须在对应 `worktree` 更新；计划书内部 `S1/S2/...` 只是计划内小任务卡，不单独创建任务日志。
- 所有任务记录均以 [`任务记录约定.md`](任务记录约定.md) 为准。
- 合并任务必须带上 `agents/codex-multi-agents/log/task_records/...` 下的对应日志；合并提交只包含业务文件与任务日志。
- 合并任务执行 `-done` 后，当前链路记录文件立即封板，禁止继续追加更新；如需 `origin/main` 同步确认或其他后续跟踪，必须新建独立任务并使用独立记录文件。

## 目录树示例

```text
主仓：
  <repo-root>/
    TODO.md
    DONE.md
    agents/codex-multi-agents/agents-lists.md
    agents/codex-multi-agents/log/talk.log
    agents/standard/任务记录约定.md

任务 worktree：
  wt-<task-name>/
    src/...
    test/...
    agents/codex-multi-agents/log/task_records/<year>/<week>/<record>.md
```

## 主仓更新 / worktree 更新

| 场景 | 应更新位置 | 典型文件 |
| --- | --- | --- |
| 主仓更新 | 共享状态文件、角色列表、标准文档主线版本 | `agents/codex-multi-agents/agents-lists.md`、`agents/codex-multi-agents/log/talk.log`、`agents/standard/*.md` |
| `worktree` 更新 | 当前任务直接相关的实现、测试、任务日志 | `src/...`、`test/...`、`agents/codex-multi-agents/log/task_records/...` |
| 禁止混写 | 常规任务日志不得回写主仓；主仓共享状态文件也不应只改在任务 `worktree` | `TODO.md`、`DONE.md`、常规 `task_records` |

## 快速判断

- 若文件会被所有角色共享读取，优先判断是否属于主仓更新。
- 若文件只服务当前任务链路复核与续接，优先判断是否属于 `worktree` 更新。
- 若任务已进入 `merge`，先确认任务日志位于对应 `worktree`，再确认需要带入的共享文档是否本轮明确在任务范围内。
