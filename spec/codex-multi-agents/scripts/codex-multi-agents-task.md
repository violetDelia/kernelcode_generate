# codex-multi-agents-task

## 功能简介

定义 [`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh) 的任务流转合同。当前实现拆分为三部分：入口脚本负责参数解析、锁与流程编排；核心模块负责 `TODO.md`、`DONE.md`、`agents-lists.md` 的读写与状态流转；通知脚本负责 `list -init` 与 `tmux -talk` 的消息副作用。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-task.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-task.md)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- `功能实现`：
  - [`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh)
  - [`skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py)
  - [`skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh)

## 依赖

- 任务脚本：[`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh)
- 核心状态模块：[`skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py)
- 通知模块：[`skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task-notify.sh)
- 角色列表脚本：[`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)
- 会话消息脚本：[`skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh)
- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- 角色列表文件：[`agents/codex-multi-agents/agents-lists.md`](../../../agents/codex-multi-agents/agents-lists.md)
- 配置文件：[`agents/codex-multi-agents/config/config.txt`](../../../agents/codex-multi-agents/config/config.txt)
- 数据文件：`TODO.md` 与同级 `DONE.md`
- 系统能力：`flock`

## 术语

- `任务类型`：任务阶段标签，只接受 `spec/build/review/merge/other/refactor`。
- `正在执行的任务`：已被指派、当前仍在推进的任务。
- `任务列表`：尚未分发，或已经通过 `-next` 退回等待下一阶段处理的任务。
- `计划书`：用于聚合任务数量与完成状态的文档路径。
- `完成待检查`：计划统计中的计划状态，表示该计划无剩余待完成任务，但尚未执行 `-done-plan`。

## 目标

- 提供统一的 `-dispatch/-done/-pause/-continue/-reassign/-next/-new/-delete/-done-plan/-status` 命令入口。
- 维护 `TODO.md`、`DONE.md`、`agents-lists.md` 之间一致的任务状态和角色状态。
- 在 `-new/-done/-delete/-done-plan` 时维护 `## 计划书` 统计。
- 在 `-dispatch` 成功后发送固定格式的任务消息；在 `-next` 成功后固定向管理员发送阶段摘要；在 `-next -auto` 成功时额外发送自动续接消息。
- 在参数错误、文件错误、数据错误、锁冲突与内部错误时返回稳定返回码。

## 实现分层

- `codex-multi-agents-task.sh`：入口层；负责参数解析、参数合法性校验、文件加锁、调用核心模块、在成功后触发通知模块。
- `codex-multi-agents-task-core.py`：核心数据层；负责解析与写回 `TODO.md`、`DONE.md`、`agents-lists.md`，并实现 `dispatch/done/pause/continue/reassign/next/new/delete/done-plan/status-*` 的状态流转。
- `codex-multi-agents-task-notify.sh`：通知副作用层；负责 `codex-multi-agents-list.sh -init`、`codex-multi-agents-tmux.sh -talk`、默认任务消息模板与管理员摘要。
- 三层边界固定：
  - 入口层不直接修改 Markdown 表格内容；
  - 核心数据层不直接发送消息；
  - 通知副作用层不决定任务流转规则。

## 限制与边界

- `TODO.md` 必须至少包含：
  - `## 正在执行的任务`
  - `## 任务列表`
  - `## 需要用户确认的事项`
- `## 计划书` 可缺失；写操作时脚本会自动补齐该段落及表头。
- `正在执行的任务` 表头固定为：
  - `| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |`
- `任务列表` 表头固定为：
  - `| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |`
- `计划书` 表头固定为：
  - `| 计划书 | 总任务数 | 已完成任务 | 待完成任务 | 完成状态 |`
- `DONE.md` 表头固定为：
  - `| 任务 ID | 描述 | 指派 | 完成状态 | 完成时间 | 日志文件 | 备注 |`
- `任务 ID` 在 `正在执行的任务` 与 `任务列表` 中必须全局唯一。
- `-dispatch/-done/-pause/-continue/-reassign/-next` 必须提供 `-agents-list`。
- `-next` 必须显式提供 `-from`；后续 `tmux -talk` 通知统一使用该发起人。
- `-next/-new` 必须提供 `-type`。
- `-new` 必须提供 `-worktree/-depends/-plan`，且 `-worktree` 不能为空字符串或 `None`。
- `-new` 的 `-plan` 允许为 `None`；若不是 `None`，则必须以 `.md` 结尾。
- `-new` 写入的 `worktree` 在 `正在执行的任务` 与 `任务列表` 中必须唯一。
- `-dispatch` 默认读取任务记录中的 `任务类型`；若显式提供 `-type`，则必须与任务记录一致。
- `-dispatch` 仅在全部依赖任务已经从 `正在执行的任务` 与 `任务列表` 中消失时才允许继续。
- `-dispatch` 仅在目标角色存在、当前空闲且总并发人数未超过 `CODEX_MULTI_AGENTS_MAX_PARALLEL` 时才允许继续。
- `-next` 仅负责：
  - 将运行中任务移回 `任务列表`
  - 用 `-message` 更新 `描述`
  - 用 `-type` 更新下一阶段 `任务类型`
- `-next` 将任务退回 `任务列表` 时，`指派` 必须清空。
- `-next` 成功后固定向管理员发送摘要：`任务 <task_id> 已完成当前阶段，已回到任务列表；新任务类型=<type>，请管理员推进。`；发送者使用 `-from`。
- `-next -auto` 仅对 `merge/review/build/spec` 四类任务执行自动续接；`other/refactor` 仍保留在 `任务列表`。
- `-next -auto` 只尝试自动续接当前刚通过 `-next` 退回 `任务列表` 的同一任务，不扫描其他任务。
- `-next -auto` 的候选人集合规则：
  - `agents-lists.md` 中状态为 `free` 且职责匹配的角色
  - `职责` 包含 `不承担管理员分发的任务` 的角色不计入候选
  - 若当前执行者满足上述条件，则作为候选之一参与选择
- `-next -auto` 在候选人集合中随机选择接手人。
- 若设置 `CODEX_MULTI_AGENTS_AUTO_RANDOM_SEED`，自动续接使用该值的 `sha256` 结果作为随机种子；在候选集合与 `agents-lists.md` 顺序不变时可复现选择结果。
- `-next -auto` 若自动接续到其他角色，会先执行一次 `list -init`，再向接手人发送任务消息，并向管理员发送摘要。
- `-next -auto` 若自动接续到当前执行者本人，不向本人发消息，只向管理员发送摘要。
- `-next -auto` 若当前任务类型不支持自动续接、没有合适角色、或当前并发人数已达上限，则当前任务保留在 `任务列表`，并向管理员发送摘要。
- `-next -auto` 自动接续成功时，接续任务沿用当前任务原 `任务 ID`，不生成新任务 ID。
- `-next -auto` 向管理员发送的成功摘要固定为：`任务 <current_task_id> 已完成当前阶段，已回到任务列表；新任务类型=<type>，已经指派给-> <当前执行者|角色名>。`；发送者使用 `-from`。
- `-auto` 只能与 `-next` 组合使用。
- `-delete` 只能删除 `任务列表` 中的任务，或 `正在执行的任务` 中 `状态=暂停` 的任务；不能删除 `状态=进行中` 的任务。
- `-done-plan` 只能处理 `完成状态=完成待检查` 且 `待完成任务=0` 的计划书记录。
- `-done-plan` 的 `-plan` 不允许为 `None`，且必须以 `.md` 结尾。
- 权限限制：
  - `-new` 仅管理员或架构师可执行。
  - `-dispatch/-done/-done-plan` 仅管理员可执行。
- 锁顺序固定：
  - `-dispatch/-pause/-continue/-reassign/-next`：先锁 `TODO.md`，再锁 `agents-lists.md`
  - `-done`：先锁 `TODO.md`，再锁 `DONE.md`，最后锁 `agents-lists.md`
- 返回码固定：
  - `0`：成功
  - `1`：参数错误
  - `2`：文件错误
  - `3`：数据错误
  - `4`：锁冲突或并发错误
  - `5`：内部错误

## 公开接口

### `-status`

功能说明：

- 只读输出 `正在执行的任务`、`任务列表` 或 `计划书` 表格。

参数说明：

- `-status(开关)`：启用状态查询。
- `-doing(开关)`：输出运行中任务表。
- `-task-list(开关)`：输出任务列表表。
- `-plan-list(开关)`：输出计划统计表。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -status \
  -plan-list
```

注意事项：

- `-doing/-task-list/-plan-list` 必须且只能三选一。
- `-status` 不修改任何文件。

返回与限制：

- 成功返回 `0`；参数组合不合法返回 `1`；表结构非法返回 `2`。

### `-dispatch`

功能说明：

- 将任务从 `任务列表` 移入 `正在执行的任务`，同步角色状态为 `busy`，并在成功后发送一条任务消息。

参数说明：

- `-dispatch(开关)`：启用分发。
- `-task_id(字符串)`：待分发任务 ID。
- `-to(字符串)`：目标角色姓名；必须存在于 `agents-lists.md`。
- `-agents-list(路径)`：角色列表文件。
- `-type(枚举，可选)`：任务类型；未提供时直接使用任务记录中的 `任务类型`，提供时必须与任务记录一致。
- `-message(字符串，可选)`：补充说明；提供后追加在默认任务消息末尾。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -dispatch \
  -task_id "EX-3" \
  -to "worker-a" \
  -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- 分发前会尽力执行一次 `codex-multi-agents-list.sh -init -file <agents-list> -name <to>`。
- 若任务记录与命令行都没有可用的 `任务类型`，则分发失败。
- 默认任务消息固定包含：任务 ID、描述、当前任务中实际存在的 `worktree`、计划书路径、记录文件、任务记录要求、问题咨询指引。
- 提供 `-message` 时，仅作为默认任务消息后的补充说明。

返回与限制：

- 成功返回 `0`；任务不存在、目标角色不存在、角色忙碌、依赖未清空、任务类型不一致或并发人数超限时返回 `3`。

### `-done`

功能说明：

- 将运行中任务移出 `TODO.md`，追加到 `DONE.md`，并按需更新角色状态与计划统计。

参数说明：

- `-done(开关)`：启用完成操作。
- `-task_id(字符串)`：目标任务 ID。
- `-log(路径)`：写入 `DONE.md` 的日志文件路径。
- `-agents-list(路径)`：角色列表文件。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -done \
  -task_id "EX-1" \
  -log "./agents/codex-multi-agents/log/ex1.md" \
  -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- `-log` 只写入记录，不检查目标文件是否存在。
- 若任务绑定计划书，则会同步更新计划表的已完成数与待完成数。

返回与限制：

- 成功返回 `0`；任务不存在返回 `3`。

### `-pause`

功能说明：

- 将运行中任务状态从 `进行中` 改为 `暂停`，并在该角色无其他运行中任务时释放为 `free`。

参数说明：

- `-pause(开关)`：启用暂停操作。
- `-task_id(字符串)`：目标任务 ID。
- `-agents-list(路径)`：角色列表文件。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -pause \
  -task_id "EX-2" \
  -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- `-pause` 不移动任务位置，只修改运行表内的 `状态`。

返回与限制：

- 成功返回 `0`；任务不存在返回 `3`。

### `-continue`

功能说明：

- 将已暂停任务恢复为 `进行中`，并将对应角色状态设为 `busy`。

参数说明：

- `-continue(开关)`：启用继续操作。
- `-task_id(字符串)`：目标任务 ID。
- `-agents-list(路径)`：角色列表文件。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -continue \
  -task_id "EX-2" \
  -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- 仅 `状态=暂停` 的运行中任务允许继续。

返回与限制：

- 成功返回 `0`；任务不存在或状态不合法返回 `3`。

### `-reassign`

功能说明：

- 在 `正在执行的任务` 中替换指派对象，并重算旧角色与新角色的状态。

参数说明：

- `-reassign(开关)`：启用改派操作。
- `-task_id(字符串)`：目标任务 ID。
- `-to(字符串)`：新的目标角色。
- `-agents-list(路径)`：角色列表文件。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -reassign \
  -task_id "EX-2" \
  -to "worker-c" \
  -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- `-reassign` 仅适用于运行中任务；不能改派 `任务列表` 中的任务。

返回与限制：

- 成功返回 `0`；任务不存在或目标角色不存在返回 `3`。

### `-next`

功能说明：

- 将当前运行中任务退回 `任务列表`，改写下一阶段的描述与任务类型；带 `-auto` 时，仅尝试自动续接当前这同一条任务。

参数说明：

- `-next(开关)`：启用续接操作。
- `-task_id(字符串)`：目标任务 ID。
- `-from(字符串)`：发起 `-next` 的当前执行者姓名；用于 `-next` 与 `-next -auto` 的后续会话消息发送者。
- `-type(枚举)`：下一阶段任务类型。
- `-message(字符串)`：新的任务描述。
- `-agents-list(路径)`：角色列表文件。
- `-auto(开关，可选)`：启用自动续接。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -next \
  -task_id "EX-2" \
  -from "worker-b" \
  -type "review" \
  -message "下一阶段：补齐边界测试" \
  -agents-list "./agents/codex-multi-agents/agents-lists.md"

codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -next \
  -task_id "EX-2" \
  -from "worker-b" \
  -type "review" \
  -message "下一阶段：补齐边界测试" \
  -agents-list "./agents/codex-multi-agents/agents-lists.md" \
  -auto
```

注意事项：

- `-next` 不修改依赖任务、计划书、记录文件与创建时间。
- `-next` 将任务退回 `任务列表` 时，会清空该任务的 `指派`。
- `-next` 与 `-next -auto` 的所有会话消息都使用命令行显式传入的 `-from` 作为发送者，不再依赖环境变量解析。
- `-next` 成功后，若原指派角色没有其他运行中任务，则其状态更新为 `free`。
- `-next` 无论是否带 `-auto`，都会向管理员发送一条摘要消息。
- `-next -auto` 只会自动接续 `merge/review/build/spec`；`other/refactor` 仍保留在 `任务列表`。
- `-next -auto` 自动接续成功时，会把当前这条刚退回 `任务列表` 的同一任务移回 `正在执行的任务`，并把接手角色状态改为 `busy`。
- `-next -auto` 自动接续成功时，沿用当前任务原 `任务 ID`，不改写为新 ID。
- `-next -auto` 发给接手执行人的任务消息固定包含：任务 ID、描述，以及当前任务中实际存在的 `worktree`、计划书路径、记录文件、任务记录要求、问题咨询指引。
- `-next -auto` 无论是否成功自动接续，都会向管理员发送一条摘要消息。

返回与限制：

- 成功返回 `0`；任务不存在返回 `3`。

### `-delete`

功能说明：

- 删除待分发任务，或删除已暂停的运行中任务。

参数说明：

- `-delete(开关)`：启用删除操作。
- `-task_id(字符串)`：目标任务 ID。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -delete \
  -task_id "EX-3"
```

注意事项：

- 删除不会写入 `DONE.md`。

返回与限制：

- 成功返回 `0`；任务不存在或任务仍在运行中返回 `3`。

### `-new`

功能说明：

- 在 `任务列表` 追加一条新任务，并在需要时同步更新计划统计。

参数说明：

- `-new(开关)`：启用新建操作。
- `-info(字符串)`：任务描述。
- `-type(枚举)`：任务类型。
- `-worktree(路径)`：工作树路径。
- `-depends(字符串或None)`：依赖任务列表。
- `-plan(路径或None)`：计划书路径。
- `-to(字符串，可选)`：默认指派对象。
- `-from(字符串，可选)`：发起人；未提供时由环境或配置解析。
- `-log(路径，可选)`：记录文件。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -new \
  -info "补充单元测试" \
  -type "build" \
  -worktree "repo-x" \
  -depends "EX-2 EX-3" \
  -plan "ARCHITECTURE/plan/x.md" \
  -to "worker-b"
```

注意事项：

- 任务 ID 由脚本按 `T-YYYYMMDD-<8位hash>` 生成。
- `-depends` 非 `None` 时，所有依赖任务 ID 都必须已存在于任务表。
- `-plan None` 表示该任务不绑定计划书；其余值必须以 `.md` 结尾。

返回与限制：

- 成功返回 `0`；缺少必填参数返回 `1`；`worktree` 重复或依赖不存在返回 `3`。

### `-done-plan`

功能说明：

- 删除 `完成待检查` 的计划统计行，表示该计划已从任务层完全收口。

参数说明：

- `-done-plan(开关)`：启用计划归档操作。
- `-plan(路径)`：目标计划书路径。

使用示例：

```bash
codex-multi-agents-task.sh \
  -file "./skills/codex-multi-agents/examples/TODO.md" \
  -done-plan \
  -plan "ARCHITECTURE/plan/x.md"
```

注意事项：

- 目标计划若仍有任务残留在 `正在执行的任务` 或 `任务列表`，则不能执行 `-done-plan`。
- `-plan` 必须是 `.md` 文件路径，不能使用 `None`。

返回与限制：

- 成功返回 `0`；计划状态不满足条件时返回 `3`。

## 测试

- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`
- 测试目标：
  - 验证各主操作的参数校验、状态迁移、计划统计与角色状态同步。
  - 验证分发前初始化、分发后消息发送、默认模板拼接与消息失败语义。
  - 验证 `-next` 清空指派并向管理员发送摘要；验证 `-next -auto` 仅续接同一任务、保留原任务 ID、按接手人场景发送摘要与会话消息。
  - 验证文件不存在、表结构非法、依赖未清空、角色忙碌、并行人数超限与锁冲突路径。
  - 验证权限限制：管理员专属操作与管理员/架构师专属操作。
- 功能与用例清单：
  - `TC-001` `test_dispatch_task_success`：分发成功，任务移入运行表，角色变为 `busy`
  - `TC-002` `test_dispatch_missing_task_returns_rc3`：分发不存在任务，返回 `3`
  - `TC-003` `test_done_task_moves_to_done_file_success`：完成成功，任务移出 TODO，追加到 DONE
  - `TC-004` `test_done_missing_task_returns_rc3`：完成不存在任务，返回 `3`
  - `TC-005` `test_pause_task_success`：暂停成功，运行中任务状态改为 `暂停`
  - `TC-006` `test_pause_missing_task_returns_rc3`：暂停不存在任务，返回 `3`
  - `TC-007` `test_new_task_with_assignee_success`：新建任务并带默认指派，任务列表新增一行
  - `TC-008` `test_new_task_without_assignee_success`：新建任务且不带默认指派，指派为空
  - `TC-009` `test_argument_error_returns_rc1`：缺少必填参数，返回 `1`
  - `TC-010` `test_file_not_found_returns_rc2`：`TODO.md` 不存在，返回 `2`
  - `TC-011` `test_invalid_todo_structure_returns_rc2`：表结构非法，返回 `2`
  - `TC-012` `test_lock_conflict_returns_rc4`：文件锁冲突，返回 `4`
  - `TC-013` `test_status_doing_outputs_running_table`：查询运行中任务，输出运行表
  - `TC-014` `test_status_task_list_outputs_list_table`：查询任务列表，输出任务列表表
  - `TC-015` `test_status_requires_exactly_one_mode`：`-status` 模式参数不合法，返回 `1`
  - `TC-016` `test_status_invalid_table_returns_rc2`：`-status` 遇到坏表头，返回 `2`
  - `TC-017` `test_dispatch_with_message_sends_talk_success`：显式消息发送成功
  - `TC-018` `test_dispatch_with_message_failure_keeps_dispatch_result`：显式消息发送失败但分发结果保留
  - `TC-019` `test_dispatch_runs_init_before_dispatch`：分发前初始化
  - `TC-020` `test_dispatch_without_message_talk_failure_is_warning`：默认模板发送失败，仅输出告警
  - `TC-021` `test_dispatch_without_message_template_includes_worktree_and_plan`：默认模板包含 `worktree` 与 `计划书`
  - `TC-022` `test_continue_task_success`：继续暂停任务，状态恢复为 `进行中`
  - `TC-023` `test_continue_missing_task_returns_rc3`：继续不存在任务，返回 `3`
  - `TC-024` `test_continue_requires_paused_status`：继续非暂停任务，返回 `3`
  - `TC-025` `test_continue_requires_agents_list`：继续任务缺少角色列表，返回 `1`
  - `TC-026` `test_reassign_task_success`：改派成功，任务指派更新，角色状态重算
  - `TC-027` `test_reassign_missing_task_returns_rc3`：改派不存在任务，返回 `3`
  - `TC-028` `test_reassign_requires_agents_list`：改派缺少角色列表，返回 `1`
  - `TC-029` `test_delete_task_list_success`：删除任务列表任务
  - `TC-030` `test_delete_missing_task_returns_rc3`：删除不存在任务，返回 `3`
  - `TC-031` `test_delete_running_task_returns_rc3`：删除运行中任务，返回 `3`
  - `TC-032` `test_delete_paused_running_task_success`：删除已暂停运行中任务
  - `TC-033` `test_next_task_moves_running_to_task_list_success`：续接成功，任务回到列表，描述与类型更新
  - `TC-034` `test_next_requires_message`：续接缺少描述，返回 `1`
  - `TC-035` `test_next_requires_type`：续接缺少任务类型，返回 `1`
  - `TC-036` `test_new_restricted_for_non_privileged_operator`：普通执行人调用 `-new`，返回 `3`
  - `TC-037` `test_done_restricted_for_non_privileged_operator`：非管理员调用 `-done`，返回 `3`
  - `TC-038` `test_new_requires_worktree`：新建缺少 `-worktree`，返回 `1`
  - `TC-039` `test_dispatch_blocked_by_unresolved_dependency`：分发时依赖未清空，返回 `3`
  - `TC-040` `test_dispatch_rejects_busy_agent`：目标角色为 `busy`，返回 `3`
  - `TC-041` `test_next_requires_agents_list`：续接缺少角色列表，返回 `1`
  - `TC-041A` `test_next_requires_from`：续接缺少发起人，返回 `1`
  - `TC-042` `test_new_requires_depends_and_plan`：新建缺少 `-depends/-plan`，返回 `1`
  - `TC-043` `test_status_plan_list_outputs_plan_table`：查询计划统计表
  - `TC-044` `test_new_requires_existing_dependencies`：新建任务依赖不存在，返回 `3`
  - `TC-045` `test_new_updates_plan_progress_table`：新建任务更新计划统计
  - `TC-046` `test_done_last_plan_task_marks_plan_waiting_review`：完成最后一个计划任务，计划状态改为 `完成待检查`
  - `TC-047` `test_done_plan_removes_review_ready_plan`：归档完成待检查计划
  - `TC-048` `test_done_plan_requires_review_ready_status`：归档非 `完成待检查` 计划，返回 `3`
  - `TC-049` `test_done_plan_restricted_for_non_privileged_operator`：非管理员调用 `-done-plan`，返回 `3`
  - `TC-050` `test_dispatch_rejects_when_parallel_limit_reached`：并发人数达到上限，返回 `3`
  - `TC-051` `test_dispatch_restricted_for_non_admin_operator`：非管理员调用 `-dispatch`，返回 `3`
  - `TC-052` `test_next_auto_reassigns_same_task_to_operator`：自动续接给当前执行者，任务 ID 不变
  - `TC-053` `test_next_auto_reassigns_same_task_to_other_agent`：自动续接给其他匹配角色，并发送任务消息
  - `TC-054` `test_next_auto_failure_notifies_admin`：自动续接失败，任务保留在列表并通知管理员推进
  - `TC-055` `test_auto_only_supports_next`：`-auto` 与其他命令组合，返回 `1`
  - `TC-056` `test_next_auto_random_assignment_with_seed`：设置随机种子时自动续接结果可复现
  - `TC-057` `test_next_auto_random_assignment_seed_changes`：不同随机种子会触发不同接手人
