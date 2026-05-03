# codex-multi-agents 命令速查

## 文档信息

- `spec`：
  - [`spec/codex-multi-agents/scripts/codex-multi-agents-list.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-list.md)
  - [`spec/codex-multi-agents/scripts/codex-multi-agents-task.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-task.md)
- `test`：
  - [`test/codex-multi-agents/test_codex-multi-agents-list.py`](../../../test/codex-multi-agents/test_codex-multi-agents-list.py)
  - [`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- `功能实现`：
  - [`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](../scripts/codex-multi-agents-list.sh)
  - [`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../scripts/codex-multi-agents-task.sh)
  - [`skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh`](../scripts/codex-multi-agents-tmux.sh)

## 文件说明

以下内容为 `codex-multi-agents` 常用命令的速查与示例，便于快速上手。更完整的行为细节以脚本与规范文档为准。

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

### 发送对话
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -talk -from scheduler -to worker-a \
  -agents-list agents/codex-multi-agents/agents-lists.md \
  -message "请处理任务 T1"
```

说明：
- `-talk` 不再接受手工传入 `-session-id`。
- 目标 tmux 会话会按 `agents-lists.md` 中目标角色的 `会话` 字段自动解析。
- 对话日志固定写入 `$(dirname <agents-list>)/log/talk.log`。
- 若只是单次咨询，不要新建任务，直接使用 `-talk`。

### 单次咨询示例
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -talk -from worker-a -to 守护最好的爱莉希雅 \
  -agents-list agents/codex-multi-agents/agents-lists.md \
  -message "这不是任务。请确认 add 接口参数顺序是否固定为 lhs,rhs,out。"
```

说明：
- 适用于流程澄清、架构问题、实现细节确认、审查意见同步。
- 该类消息不修改 `TODO.md`，也不占用任务流转。

### 按名单初始化角色环境
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -init-env -file agents/codex-multi-agents/agents-lists.md -name 小明
```

参数速记：
- `-from/-to/-agents-list/-message` 对话参数（仅 `-talk`）
- `-file/-name` 名单参数（仅 `-init-env/-wake`）

## 3. 任务调度（codex-multi-agents-task.sh）

脚本路径：`./scripts/codex-multi-agents-task.sh`

### TODO 结构示例
```markdown
## 正在执行的任务
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 任务列表
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

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
  -type build \
  -worktree repo-x \
  -depends "T-20260408-aaaa1111,T-20260408-bbbb2222" \
  -plan "ARCHITECTURE/plan/example_green_plan.md" \
  -to worker-b -from 大闸蟹 \
  -log ./agents/codex-multi-agents/log/task-record.md
```

说明：
- `-new` 必填：`-info/-type/-worktree/-depends/-plan`。
- `-type` 只接受 `spec/build/review/merge/other/refactor`。
- `-worktree/-depends/-plan` 支持传 `None`，但 `-worktree` 不能为 `None` 或空字符串。
- 权限：仅架构师与管理员可执行 `-new`。

### 新建计划修复任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -new -info "default-lowering-S6-实现；计划书：《ARCHITECTURE/plan/pass_pipeline_registration_refactor_green_plan.md》；任务目标：修复：收口 default-lowering 构建路径与 pass 名兼容；任务链记录：20260413-default-lowering-s6.md" \
  -type build \
  -worktree wt-20260413-default-lowering-s6 \
  -depends None \
  -plan ARCHITECTURE/plan/pass_pipeline_registration_refactor_green_plan.md \
  -from 守护最好的爱莉希雅 \
  -log agents/codex-multi-agents/log/task_records/2026/15/20260413-default-lowering-s6.md
```

说明：
- 计划书终验若不通过，不直接归档；由给出最终“不通过”结论的架构师创建修复任务。
- 修复任务继续挂在原计划书下，`任务目标` 第一短句直接写 `修复：<最小阻断项>`。
- 另一位架构师只补充阻断项和修复范围，不再重复建同一任务。
- 若误建了同一修复任务，只保留一条继续推进，另一条按重复任务处理。

### 分发任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -dispatch -task_id T-20260308-xxxxxxx1 -to worker-a \
  -agents-list ./agents/codex-multi-agents/agents-lists.md
```

说明：
- 每次 `-dispatch` 前，脚本都会先执行一次 `codex-multi-agents-list.sh -init`。
- `-dispatch` 不要求显式传 `-type`，默认读取任务记录中的 `任务类型`；若显式传入，则必须与任务记录一致。
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
  -from worker-a \
  -type review \
  -message "审查：复核权限校验与并行上限分发阻断" \
  -agents-list ./agents/codex-multi-agents/agents-lists.md
```

说明：
- `-next` 会把任务从“正在执行的任务”移回“任务列表”。
- `-next` 必须显式提供下一阶段 `-type`，避免阶段类型误判。
- 只替换“描述”和“任务类型”；worktree/依赖/计划书/记录文件保持不变；退回任务列表时 `指派` 会清空。

### 手动续接并指派（-next -to）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -next -task_id T-20260308-xxxxxxx1 \
  -from worker-a \
  -to worker-b \
  -type review \
  -message "审查：复核权限校验与并行上限分发阻断" \
  -agents-list ./agents/codex-multi-agents/agents-lists.md
```

说明：
- `-next -to <worker>` 会把同一任务直接续接到指定角色，不在任务列表保留待分发副本。
- 脚本会同步更新 `agents-lists.md`：原接手人按剩余运行中任务数重算 `free/busy`，新接手人置为 `busy`。
- `-next -to` 与 `-next -auto` 互斥。

### 自动续接任务（-next -auto）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -next -task_id T-20260308-xxxxxxx1 \
  -from worker-a \
  -type review \
  -message "审查：复核权限校验与并行上限分发阻断" \
  -agents-list ./agents/codex-multi-agents/agents-lists.md \
  -auto
```

说明：
- `-auto` 只能和 `-next` 一起使用。
- `-next -auto` 会先把当前任务退回 `任务列表`，清空 `指派`，再只尝试自动续接这同一条任务。
- 自动接续顺序固定为：当前执行者本人；若不匹配，再按 `agents-lists.md` 顺序选择其他空闲且职责匹配的角色。
- 若当前任务类型不支持自动续接、没有合适角色或并发已满，则当前任务保留在 `任务列表`。
- 自动接续成功后，会向接手人发送任务消息，并向管理员发送摘要；若接给当前执行者本人，则只向管理员发送摘要。
- 若任务有独立 `worktree`，执行人完成当前阶段前，必须先把常规任务日志写入该 `worktree` 下的对应记录文件；只有无独立 `worktree` 的计划互评、专题 `spec` 互评、终验或归档结论，才按规则写入计划书、专题 `spec` 正文或 `done_plan` 记录文件。

实际通知效果：
- 接给其他角色时，执行人会收到一条固定格式消息，内容至少包含：`任务 ID`、`描述`、`worktree`、`计划书`、`记录文件`、任务记录要求、问题咨询指引；其中“任务记录要求”固定要求：若任务有独立 `worktree`，常规任务日志必须写入该 `worktree` 下的对应记录文件。若本次 `-next` 是为了 `merge`，消息会额外提示“完成后直接回报管理员，由管理员执行 -done”。
- 接给其他角色时，管理员会收到固定摘要：`任务 <task_id> 已完成当前阶段，已回到任务列表；新任务类型=<type>，已经指派给-> <角色名>。`
- 若自动接续落到当前执行者本人，则不会再给本人发消息，只会给管理员发送摘要，避免重复提醒。
- 若自动接续失败，管理员会收到固定摘要：`任务 <task_id> 已完成当前阶段，已回到任务列表；新任务类型=<type>，请管理员推进。`
- 若本次 `-next` 自带 `-message`，该内容会写回任务描述；真正发给执行人的通知仍然会保留固定前缀：`请处理任务 <task_id>（<描述>）...`，`-message` 不会替代这些基础字段。

### 计划书归档（-done-plan）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -done-plan -plan "ARCHITECTURE/plan/example_green_plan.md"
```

说明：
- 仅当该计划在 `## 计划书` 中为“完成待检查”且待完成任务为 0 时可执行。
- 权限：仅管理员可执行 `-done-plan`。
- 若双架构师结论仍为“不通过”，应先等待修复任务完成并重新验收，不执行 `-done-plan`。

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
- `-type` 任务阶段类型（`-next/-new` 必填，`-dispatch` 可选）
- `-agents-list` 角色名单路径（`-dispatch/-done/-pause/-continue/-reassign/-next` 必填）
- `-to/-from/-worktree/-depends/-plan/-log` 任务字段
- `-auto` 自动续接开关，仅用于 `-next`
- `-status -doing/-task-list/-plan-list` 状态查询

## 4. 权限速记
- 架构师/管理员：可 `-new`。
- 管理员：可 `-dispatch/-done/-done-plan`。
- 其他执行者：完成后仅使用 `-next` 推进后续任务（李白除外）。
- 李白：不使用 `-next`，合并后回报管理员，由管理员执行 `-done`。

## 5. 任务流转速记
- 实现任务默认包含测试验证。
- 审查不通过则回到实现任务（含测试）再次迭代，直到审查通过。
- 计划书终验不通过则由架构师补建修复任务，管理员只推进唯一保留的修复任务。
