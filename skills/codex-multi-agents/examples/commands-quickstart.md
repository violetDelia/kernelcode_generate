# codex-multi-agents 命令速查

以下内容为使用示例与参数速记，便于快速上手。更完整的行为细节以脚本与规范文档为准。

## 1. 名单管理（codex-multi-agents-list.sh）

脚本路径：`./scripts/codex-multi-agents-list.sh`

### 查看名单
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -status
```

### 查询字段
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -find -name 小明 -key 归档文件
```

### 新增人员
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -add -name 小王 -type codex
```

### 修改字段
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -replace -name 小明 -key 状态 -value busy
```

### 删除人员
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -delete -name 小王
```

### 初始化人员
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -init -name 小明
```

参数速记：
- `-file` 名单文件路径
- `-name` 人员姓名
- `-type` 启动类型（示例：`codex`）
- `-key` 字段名
- `-value` 字段值
- `状态` 建议仅使用 `free` / `busy`

## 2. tmux 会话管理（codex-multi-agents-tmux.sh）

脚本路径：`./scripts/codex-multi-agents-tmux.sh`

### 发送对话并写日志
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -talk -from scheduler -to worker-a \
  -agents-list agents/codex-multi-agents/agents-lists.md \
  -message "请处理任务 T1" \
  -log agents/codex-multi-agents/log/talk.log
```

说明：
- `-talk` 不再接受手工传入 `-session-id`。
- 目标 tmux 会话会按 `agents-lists.md` 中目标角色的 `会话` 字段自动解析。

### 按名单初始化角色环境
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -init-env -file agents/codex-multi-agents/agents-lists.md -name 小明
```

参数速记：
- `-from/-to/-agents-list/-message/-log` 对话参数（仅 `-talk`）
- `-file/-name` 名单参数（仅 `-init-env/-wake`）

## 3. 任务调度（codex-multi-agents-task.sh）

脚本路径：`./scripts/codex-multi-agents-task.sh`

### TODO 结构示例
```markdown
## 正在执行的任务
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 任务列表
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 依赖任务 | 计划书 | 指派 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 计划书
| 计划书 | 总任务数 | 已完成任务 | 待完成任务 | 完成状态 |
| --- | --- | --- | --- | --- |

## 需要用户确认的事项（可选）
| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |
| --- | --- | --- | --- | --- | --- |
```

### 新建任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -new -info "实现任务调度器告警" \
  -worktree repo-x \
  -depends "T-20260408-aaaa1111,T-20260408-bbbb2222" \
  -plan "ARCHITECTURE/plan/example_green_plan.md" \
  -to worker-b -from 大闸蟹 \
  -log ./agents/codex-multi-agents/log/task-record.md
```

说明：
- `-new` 必填：`-info/-worktree/-depends/-plan`。
- `-worktree/-depends/-plan` 支持传 `None`（表示写空值）。
- 权限：仅架构师与管理员可执行 `-new`。

### 分发任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -dispatch -task_id T-20260308-xxxxxxx1 -to worker-a \
  -agents-list ./agents/codex-multi-agents/agents-lists.md
```

说明：
- 每次 `-dispatch` 前，脚本都会先执行一次 `codex-multi-agents-list.sh -init`。
- 若未提供 `-message`，会自动发送默认模板消息。
- 若目标角色为 `busy`，分发会被阻断。
- 若任务存在未完成依赖（依赖任务仍在 TODO），分发会被阻断。
- 并行上限默认 `8`，可通过 `CODEX_MULTI_AGENTS_MAX_PARALLEL` 覆盖。
- 权限：仅管理员可执行 `-dispatch`。

### 暂停任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md -agents-list ./agents/codex-multi-agents/agents-lists.md \
  -pause -task_id T-20260308-xxxxxxx1
```

### 完成任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -done -task_id T-20260308-xxxxxxx1 \
  -log ./agents/codex-multi-agents/log/task-T-20260308-xxxxxxx1.log \
  -agents-list ./agents/codex-multi-agents/agents-lists.md
```

### 续接任务（-next）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -next -task_id T-20260308-xxxxxxx1 \
  -message "审查：复核权限校验与并行上限分发阻断" \
  -agents-list ./agents/codex-multi-agents/agents-lists.md
```

说明：
- `-next` 会把任务从“正在执行的任务”移回“任务列表”。
- 只替换“描述”，其余字段（worktree/依赖/计划书/指派/记录文件）保持不变。

### 计划书归档（-done-plan）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -done-plan -plan "ARCHITECTURE/plan/example_green_plan.md"
```

说明：
- 仅当该计划在 `## 计划书` 中为“完成待检查”且待完成任务为 0 时可执行。
- 权限：仅管理员可执行 `-done-plan`。

### 查看状态
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md -status -doing
```

```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md -status -task-list
```

```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md -status -plan-list
```

参数速记：
- `-file` TODO 文件路径
- `-new/-dispatch/-pause/-continue/-reassign/-next/-done/-delete/-done-plan` 操作类型
- `-task_id` 任务 ID
- `-info` 任务描述
- `-agents-list` 角色名单路径（`-dispatch/-done/-pause/-continue/-reassign/-next` 必填）
- `-to/-from/-worktree/-depends/-plan/-log` 任务字段
- `-status -doing/-task-list/-plan-list` 状态查询

## 4. 权限速记
- 架构师/管理员：可 `-new`。
- 管理员：可 `-dispatch/-done/-done-plan`。
- 其他执行者：完成后仅使用 `-next` 推进后续任务（李白除外）。
- 李白：不使用 `-next`，合并后回报管理员，由管理员执行 `-done`。

## 5. 任务流转速记
- 实现任务默认包含测试验证。
- 审查不通过则回到实现任务（含测试）再次迭代，直到审查通过。
