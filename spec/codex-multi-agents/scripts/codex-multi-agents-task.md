# codex-multi-agents-task

## 功能简介

定义 [`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh) 的任务流转合同。当前实现拆分为三部分：入口脚本负责参数解析、锁与流程编排；核心模块负责 `TODO.md`、`DONE.md`、`agents-lists.md` 的读写与状态流转；通知脚本负责 `list -init` 与 `tmux -talk` 的消息副作用。

## API 列表

- `-status`
- `-dispatch`
- `-done`
- `-pause`
- `-continue`
- `-reassign`
- `-next`
- `-delete`
- `-new`
- `-done-plan`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`Codex`
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
- 在 `-dispatch` 成功后发送固定格式的任务消息；在 `-reassign` 成功后同时通知旧接手人与新接手人；在 `-next` 成功后固定向管理员发送阶段摘要；当 `-next` 触发自动续接时，额外发送自动续接消息。
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

- 命令级限制、文件结构要求、权限、锁顺序与状态一致性约束均写在对应 API 的 `注意事项` 与 `返回与限制` 中，本节不再重复展开。

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
- `TODO.md` 读取时必须至少包含 `## 正在执行的任务`、`## 任务列表`、`## 需要用户确认的事项` 三段。
- `## 计划书` 可缺失；`-plan-list` 只读取已存在的计划统计，不会补写缺失段落。
- 表头固定：
  - `正在执行的任务`：`| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |`
  - `任务列表`：`| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |`
  - `计划书`：`| 计划书 | 总任务数 | 已完成任务 | 待完成任务 | 完成状态 |`

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

- `-dispatch` 仅管理员可执行。
- `-agents-list` 必须显式提供，且必须与配置解析出的 canonical `AGENTS_FILE` 指向同一文件；不允许写入其他名单副本。
- 分发前会尽力执行一次 `codex-multi-agents-list.sh -init -file <agents-list> -name <to>`。
- 若任务记录与命令行都没有可用的 `任务类型`，则分发失败。
- `-dispatch` 默认读取任务记录中的 `任务类型`；若显式提供 `-type`，则必须与任务记录一致。
- 仅当全部依赖任务已经同时从 `正在执行的任务` 与 `任务列表` 中消失时，才允许分发。
- `任务 ID` 在 `正在执行的任务` 与 `任务列表` 中必须全局唯一；若运行表已存在同一角色多条 `状态=进行中` 的脏数据，`-dispatch` 必须直接失败。
- 目标角色除名单状态为 `free` 外，还必须在运行表中没有其他 `状态=进行中` 的任务；即使名单里是 stale `free`，也必须拒绝重复占用。
- `-dispatch` 仅在目标角色存在、当前空闲且总并发人数未超过 `CODEX_MULTI_AGENTS_MAX_PARALLEL` 时才允许继续。
- `-dispatch` 的目标角色必须满足对应任务类型职责约束；`build` 不能分发给 `审查/复审` 专职，`merge` 不能分发给候补或非合并专职。
- 角色职责约束固定为：
  - `spec`：只允许 `spec` 专职或 `全能替补`。
  - `build`：只允许 `实现/测试` 专职或 `全能替补`。
  - `review`：只允许 `审查/复审` 专职或 `全能替补`。
  - `refactor`：只允许 `实现/开发/测试/重构` 专职或 `全能替补`。
  - `merge`：只允许合并专职；职责必须包含 `合并`，且职责不包含 `全能替补` 或 `不含合并`。
  - `other`：不做额外职责限制。
- `agents-lists.md` 不是可被 `TODO.md` 全量回算覆盖的派生文件；`-dispatch` 只允许更新当前命令直接触及的角色状态，不得整表重置 `busy/free`。
- 对当前命令直接读写的角色，`agents-lists.md` 与运行表必须严格映照；若发现应为 `busy` 的角色是 `free`，或应为 `free` 的角色是 `busy`，脚本必须直接失败。
- 默认任务消息固定包含：任务 ID、描述、当前任务中实际存在的 `worktree`、计划书路径、记录文件、任务记录要求、问题咨询指引；其中“任务记录要求”必须明确：若任务有独立 `worktree`，常规任务日志必须写入该 `worktree` 下的对应记录文件。
- 提供 `-message` 时，仅作为默认任务消息后的补充说明。
- 锁顺序固定为：先锁 `TODO.md`，再锁 `agents-lists.md`。

返回与限制：

- 成功返回 `0`；任务不存在、目标角色不存在、角色忙碌、依赖未清空、任务类型不一致、目标角色职责不匹配或并发人数超限时返回 `3`。

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

- `-agents-list` 必须显式提供，且必须与配置解析出的 canonical `AGENTS_FILE` 指向同一文件；不允许写入其他名单副本。
- `-log` 只写入记录，不检查目标文件是否存在。
- `DONE.md` 表头固定为：`| 任务 ID | 描述 | 指派 | 完成状态 | 完成时间 | 日志文件 | 备注 |`
- 若任务绑定计划书，则会同步更新计划表的已完成数与待完成数。
- 若写操作需要维护计划统计而 `TODO.md` 中缺少 `## 计划书`，则会自动补齐该段落及表头。
- 若运行表已存在同一角色多条 `状态=进行中` 的脏数据，`-done` 必须直接失败。
- `-done` 只更新当前命令涉及的角色状态：若原指派角色已无其他进行中任务，则置为 `free`；未被当前命令触及的其他角色保持原样。
- `agents-lists.md` 不是可被 `TODO.md` 全量回算覆盖的派生文件；`-done` 不得整表重置 `busy/free`。
- 若当前接手角色在 `agents-lists.md` 中的状态与运行表不一致，`-done` 必须直接失败，不能静默修正。
- `-done` 默认由管理员执行；但 `merge` 任务在合并完成后必须由合并角色自行执行 `-done`。合并角色仅可处理“指派给自身且任务类型为 `merge` 的运行中任务”，不得对其他类型或他人任务执行。
- 锁顺序固定为：先锁 `TODO.md`，再锁 `DONE.md`，最后锁 `agents-lists.md`。

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

- `-agents-list` 必须显式提供，且必须与配置解析出的 canonical `AGENTS_FILE` 指向同一文件；不允许写入其他名单副本。
- 若运行表已存在同一角色多条 `状态=进行中` 的脏数据，`-pause` 必须直接失败。
- `-pause` 不移动任务位置，只修改运行表内的 `状态`。
- `-pause` 只更新当前任务指派角色的状态；若该角色已无其他进行中任务，则置为 `free`。
- `agents-lists.md` 不是可被 `TODO.md` 全量回算覆盖的派生文件；`-pause` 不得整表重置 `busy/free`。
- 若当前接手角色在 `agents-lists.md` 中的状态与运行表不一致，`-pause` 必须直接失败，不能静默修正。
- 锁顺序固定为：先锁 `TODO.md`，再锁 `agents-lists.md`。

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

- `-agents-list` 必须显式提供，且必须与配置解析出的 canonical `AGENTS_FILE` 指向同一文件；不允许写入其他名单副本。
- 若运行表已存在同一角色多条 `状态=进行中` 的脏数据，`-continue` 必须直接失败。
- 仅 `状态=暂停` 的运行中任务允许继续。
- `agents-lists.md` 不是可被 `TODO.md` 全量回算覆盖的派生文件；`-continue` 不得整表重置 `busy/free`。
- 若当前接手角色在 `agents-lists.md` 中的状态与运行表不一致，`-continue` 必须直接失败，不能静默修正。
- 恢复后的接手角色必须在运行表中没有其他 `状态=进行中` 的任务；若已存在其他运行中任务，则继续失败。
- 锁顺序固定为：先锁 `TODO.md`，再锁 `agents-lists.md`。

返回与限制：

- 成功返回 `0`；任务不存在或状态不合法返回 `3`。

### `-reassign`

功能说明：

- 在 `正在执行的任务` 中替换指派对象，并只更新旧角色与新角色的状态。
- 改派成功后同步通知被取消任务的旧角色与新的接手角色。

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

- `-agents-list` 必须显式提供，且必须与配置解析出的 canonical `AGENTS_FILE` 指向同一文件；不允许写入其他名单副本。
- 若运行表已存在同一角色多条 `状态=进行中` 的脏数据，`-reassign` 必须直接失败。
- `-reassign` 仅适用于运行中任务；不能改派 `任务列表` 中的任务。
- 目标角色必须在 `agents-lists.md` 中处于 `free` 状态。
- 目标角色除名单状态外，还必须在运行表中没有其他 `状态=进行中` 的任务；即使名单里是 stale `free`，也必须拒绝重复占用。
- `-reassign` 的目标角色必须满足对应任务类型职责约束；`build` 不能改派给 `审查/复审` 专职，`merge` 不能改派给候补或非合并专职。
- 角色职责约束与 `-dispatch` 相同。
- `-reassign` 只更新旧角色与新角色的状态：新角色置为 `busy`；旧角色若已无其他进行中任务则置为 `free`。
- `agents-lists.md` 不是可被 `TODO.md` 全量回算覆盖的派生文件；`-reassign` 不得整表重置 `busy/free`。
- 若旧角色或新角色在 `agents-lists.md` 中的状态与运行表不一致，`-reassign` 必须直接失败，不能静默修正。
- 旧角色收到“停止当前处理”的提示，新角色收到与 `-dispatch` 一致的默认任务消息模板。
- 锁顺序固定为：先锁 `TODO.md`，再锁 `agents-lists.md`。

返回与限制：

- 成功返回 `0`；任务不存在、目标角色不存在、目标角色忙碌或目标角色职责不匹配返回 `3`。

### `-next`

功能说明：

- 将当前运行中任务改写为下一阶段；默认退回 `任务列表`，随后尝试自动启动 `任务列表` 中首个 ready 任务；带 `-to` 时手动指派给指定角色；`-auto` 仅作为兼容开关保留。

参数说明：

- `-next(开关)`：启用续接操作。
- `-task_id(字符串)`：目标任务 ID。
- `-from(字符串)`：发起 `-next` 的当前执行者姓名；用于 `-next` 与 `-next -auto` 的后续会话消息发送者。
- `-to(字符串，可选)`：手动指定下一阶段接手人；与 `-auto` 互斥。
- `-type(枚举)`：下一阶段任务类型。
- `-message(字符串)`：新的任务描述。
- `-agents-list(路径)`：角色列表文件；普通 `-next`、`-next -to`、`-next -auto` 都必须显式提供。
- `-auto(开关，可选)`：兼容开关；与不带 `-auto` 的自动续接逻辑一致。

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
  -to "worker-c" \
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

- `-agents-list` 必须显式提供，且必须与配置解析出的 canonical `AGENTS_FILE` 指向同一文件；不允许写入其他名单副本。
- 若运行表已存在同一角色多条 `状态=进行中` 的脏数据，`-next` 必须直接失败。
- `-next` 不修改依赖任务、计划书、记录文件与创建时间。
- `-next` 必须显式提供 `-from`；所有 `tmux -talk` 会话消息统一使用该发起人。
- `-next` 将任务退回 `任务列表` 时，会清空该任务的 `指派`。
- 不带 `-to` 的 `-next` 会先把当前任务按新的 `描述` 与 `任务类型` 退回 `任务列表`，然后再尝试自动续接；普通 `-next` 只尝试启动首个 ready 任务，`-next -auto` 会继续启动所有 ready 任务，直到没有可启动任务或达到并发上限。
- `-next -to` 不退回等待管理员分发的任务列表，而是原任务 ID 直接续接到指定角色；`任务列表` 不保留该任务副本。
- `-next -to` 的目标角色必须存在、处于 `free` 状态，且在运行表中没有其他 `状态=进行中` 的任务；目标角色为当前执行者时，当前任务会先从运行表移除，再判断其是否仍有其他运行中任务。
- `-next -to` 的角色职责约束与 `-dispatch` 相同。
- `-next -to` 与 `-auto` 互斥；`-auto` 只能与 `-next` 组合使用。
- `-next` 与 `-next -auto` 的所有会话消息都使用命令行显式传入的 `-from` 作为发送者，不再依赖环境变量解析。
- `-next` 只更新当前命令涉及的角色状态：原指派角色若已无其他运行中任务则更新为 `free`；手动续接或自动续接接手任务的新角色更新为 `busy`；未被当前命令触及的其他角色保持原样。
- `agents-lists.md` 不是可被 `TODO.md` 全量回算覆盖的派生文件；`-next` 不得整表重置 `busy/free`。
- 若当前命令直接读写的角色在 `agents-lists.md` 中的状态与运行表不一致，`-next` 必须直接失败，不能静默修正。
- `-next` 无论是否带 `-auto`，都会向管理员发送一条摘要消息。
- 自动续接只会尝试启动 `spec/build/review/merge/refactor` 五类 ready 任务；`other` 不参与自动续接。
- 自动续接会扫描整个 `任务列表`，只考虑“依赖任务已经从 `正在执行的任务` 与 `任务列表` 中消失”的 ready 任务；按当前列表顺序选择，不会跳过前面的可启动任务去启动后面的任务。
- 自动续接成功时，会把被选中的 ready 任务移回 `正在执行的任务`，并把接手角色状态改为 `busy`。
- 若被自动续接的是当前这条刚退回 `任务列表` 的同一任务，则沿用当前任务原 `任务 ID`。
- `-next` 自动续接给其他角色时使用默认任务消息模板，与 `-dispatch` 保持一致。
- `-next` 发给接手执行人的任务消息固定包含：任务 ID、描述，以及当前任务中实际存在的 `worktree`、计划书路径、记录文件、任务记录要求、问题咨询指引；其中“任务记录要求”必须明确：若任务有独立 `worktree`，常规任务日志必须写入该 `worktree` 下的对应记录文件。
- 自动续接无论是否成功，都会向管理员发送一条摘要消息。
- 自动续接候选规则固定为：
  - 先按任务类型筛出专职池，再按需要启用候补池。
  - `spec` 专职：职责包含 `spec` 或 `spec 文档编写`，且职责不包含 `全能替补`。
  - `build` 专职：职责包含 `实现` 或 `测试`，且职责不包含 `全能替补`。
  - `review` 专职：职责包含 `审查` 或 `复审`，且职责不包含 `全能替补`。
  - `refactor` 专职：职责包含 `实现`、`开发`、`测试` 或 `重构`，且职责匹配后可在专职池中参与选择。
  - `merge` 专职：职责包含 `合并`，且职责不包含 `全能替补` 或 `不含合并`。
  - 候补：职责包含 `全能替补`。
  - 仅保留 `agents-lists.md` 中状态为 `free` 且职责匹配的角色；职责包含 `不承担管理员分发的任务` 的角色不计入候选。
  - 若当前执行者满足上述条件，则作为候选之一参与选择。
- 自动续接选择规则固定为：
  - `spec/build/review/refactor`：若存在可用专职，只在专职池内随机；专职池为空时才允许候补池参与随机。
  - `merge`：只在专职池内随机；若无可用专职则自动续接失败，任务保留在 `任务列表` 并通知管理员。
  - 随机范围仅限当前启用的候选池，不跨层级混合随机。
- 若设置 `CODEX_MULTI_AGENTS_AUTO_RANDOM_SEED`，自动续接使用该值的 `sha256` 结果作为随机种子；在候选集合与 `agents-lists.md` 顺序不变时可复现选择结果。
- `-next -auto` 若在同一轮自动启动多条任务，则只向每个接手人发送自己的任务消息；管理员摘要汇总本轮所有自动启动结果，不向普通接手人扩散无关任务信息。
- 自动续接若启动的是 `任务列表` 中其他 ready 任务，则管理员摘要固定为：`任务 <current_task_id> 已完成当前阶段，已回到任务列表；已自动开始任务 <auto_task_id> -> <当前执行者|角色名>。`
- 自动续接若启动到其他角色，会先执行一次 `list -init`，再向接手人发送任务消息，并向管理员发送摘要。
- 自动续接若启动到当前执行者本人，不向本人发消息，只向管理员发送摘要。
- 自动续接若当前没有可启动任务、没有合适角色、或当前并发人数已达上限，则当前 `-next` 处理后的任务保留在 `任务列表`，并向管理员发送摘要。
- 锁顺序固定为：先锁 `TODO.md`，再锁 `agents-lists.md`。

默认任务消息模板（自动续接给其他角色）：

- 当 `worktree`、`计划书`、`记录文件` 为空时，对应字段与分隔符不输出。
- 模板固定格式如下：

```
请处理任务 <task_id>（<desc>）。worktree=<worktree>；计划书=<plan_doc>；记录文件=<record_file>；若任务有独立 worktree，常规任务日志必须写入该 worktree 下的对应记录文件；只有无独立 worktree 的计划互评、专题 spec 互评、终验或归档结论，才按规则写入计划书、专题 spec 正文或 done_plan 记录文件。完成后按 <repo_root>/agents/standard/任务记录约定.md 记录并回报管理员；流程不清楚请询问管理员；实现/架构问题请询问架构师。
```

使用示例：

```
请处理任务 EX-2（下一阶段：补齐边界用例）。worktree=/tmp/wt-ex2；计划书=ARCHITECTURE/plan/demo.md；记录文件=./log/ex2.md；若任务有独立 worktree，常规任务日志必须写入该 worktree 下的对应记录文件；只有无独立 worktree 的计划互评、专题 spec 互评、终验或归档结论，才按规则写入计划书、专题 spec 正文或 done_plan 记录文件。完成后按 /home/lfr/kernelcode_generate/agents/standard/任务记录约定.md 记录并回报管理员；流程不清楚请询问管理员；实现/架构问题请询问架构师。
```

返回与限制：

- 成功返回 `0`；任务不存在、目标角色不存在、目标角色忙碌、目标角色职责不匹配或并发人数超限时返回 `3`。

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
- `-delete` 只能删除 `任务列表` 中的任务，或 `正在执行的任务` 中 `状态=暂停` 的任务；不能删除 `状态=进行中` 的任务。
- 若写操作需要维护计划统计而 `TODO.md` 中缺少 `## 计划书`，则会自动补齐该段落及表头。

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

- `-new` 仅管理员或架构师可执行。
- 任务 ID 由脚本按 `T-YYYYMMDD-<8位hash>` 生成。
- 写入前 `TODO.md` 必须至少包含 `## 正在执行的任务`、`## 任务列表`、`## 需要用户确认的事项` 三段；若缺少 `## 计划书`，写操作会自动补齐该段落及表头。
- `正在执行的任务` 与 `任务列表` 表头必须固定为：
  - `| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 状态 | 用户指导 | 记录文件 |`
  - `| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 任务类型 | 依赖任务 | 计划书 | 指派 | 记录文件 |`
- `-new` 必须提供 `-type/-worktree/-depends/-plan`；其中 `-worktree` 不能为空字符串或 `None`。
- `-depends` 非 `None` 时，所有依赖任务 ID 都必须已存在于任务表。
- `-plan None` 表示该任务不绑定计划书；其余值必须以 `.md` 结尾。
- 新写入的 `worktree` 在 `正在执行的任务` 与 `任务列表` 中必须唯一。
- 新生成的 `任务 ID` 在 `正在执行的任务` 与 `任务列表` 中必须全局唯一。

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

- `-done-plan` 仅管理员可执行。
- 目标计划若仍有任务残留在 `正在执行的任务` 或 `任务列表`，则不能执行 `-done-plan`。
- `-plan` 必须是 `.md` 文件路径，不能使用 `None`。
- `计划书` 表头固定为：`| 计划书 | 总任务数 | 已完成任务 | 待完成任务 | 完成状态 |`
- `-done-plan` 只能处理 `完成状态=完成待检查` 且 `待完成任务=0` 的计划书记录。
- 若双架构师对同一计划的最新终验结论仍为“不通过”，应先由架构师补建修复任务并完成重新验收，再执行 `-done-plan`。

返回与限制：

- 成功返回 `0`；计划状态不满足条件时返回 `3`。

## 测试

- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`
- 测试目标：
  - 验证各主操作的参数校验、状态迁移、计划统计与角色状态同步。
  - 验证分发前初始化、分发后消息发送、默认模板拼接与消息失败语义。
  - 验证 `-next` 清空指派并向管理员发送摘要；验证 `-next -to` 手动续接、角色状态同步与会话消息；验证普通 `-next` 只会扫描并拉起 `任务列表` 中首个 ready 任务，`-next -auto` 会继续拉起所有 ready 任务，并按接手人场景发送摘要与会话消息。
  - 验证文件不存在、表结构非法、依赖未清空、角色忙碌、并行人数超限与锁冲突路径。
  - 验证权限规则：管理员专属操作、管理员/架构师专属操作，以及合并角色执行 `-done` 的范围。
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
  - `TC-026` `test_reassign_task_success`：改派成功，任务指派更新，只更新旧/新接手人状态，并通知旧/新接手人
  - `TC-027` `test_reassign_missing_task_returns_rc3`：改派不存在任务，返回 `3`
  - `TC-028` `test_reassign_requires_agents_list`：改派缺少角色列表，返回 `1`
  - `TC-028A` `test_reassign_rejects_busy_agent`：改派目标角色忙碌，返回 `3`
  - `TC-028B` `test_reassign_rejects_merge_task_for_substitute`：`merge` 改派到候补角色被拒绝
  - `TC-028C` `test_reassign_rejects_merge_task_for_non_merge_specialist`：`merge` 改派到非合并专职被拒绝
  - `TC-028D` `test_reassign_rejects_build_task_for_review_specialist`：`build` 改派到 `review` 专职被拒绝
  - `TC-029` `test_delete_task_list_success`：删除任务列表任务
  - `TC-030` `test_delete_missing_task_returns_rc3`：删除不存在任务，返回 `3`
  - `TC-031` `test_delete_running_task_returns_rc3`：删除运行中任务，返回 `3`
  - `TC-032` `test_delete_paused_running_task_success`：删除已暂停运行中任务
  - `TC-033` `test_next_task_moves_running_to_task_list_success`：续接成功，任务回到列表，描述与类型更新
  - `TC-033A` `test_next_to_dispatches_same_task_and_updates_agent_status`：手动续接到指定角色，任务回到运行表并同步旧/新角色状态
  - `TC-030B` `test_next_to_rejects_build_task_for_review_specialist`：`-next -to` 不能把 `build` 手动续接给 `review` 专职
  - `TC-034` `test_next_requires_message`：续接缺少描述，返回 `1`
  - `TC-035` `test_next_requires_type`：续接缺少任务类型，返回 `1`
  - `TC-036` `test_new_restricted_for_non_privileged_operator`：普通执行人调用 `-new`，返回 `3`
  - `TC-037` `test_done_restricted_for_non_privileged_operator`：非管理员且不满足合并角色条件调用 `-done`，返回 `3`
  - `TC-037A` `test_done_allows_merge_operator`：合并角色完成自身 `merge` 任务，返回 `0`
  - `TC-038` `test_new_requires_worktree`：新建缺少 `-worktree`，返回 `1`
  - `TC-039` `test_dispatch_blocked_by_unresolved_dependency`：分发时依赖未清空，返回 `3`
  - `TC-040` `test_dispatch_rejects_busy_agent`：目标角色为 `busy`，返回 `3`
  - `TC-036A` `test_dispatch_rejects_merge_task_for_substitute`：`merge` 分发到候补角色被拒绝
  - `TC-036B` `test_dispatch_rejects_merge_task_for_non_merge_specialist`：`merge` 分发到非合并专职被拒绝
  - `TC-036C` `test_dispatch_rejects_build_task_for_review_specialist`：`build` 分发到 `review` 专职被拒绝
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
  - `TC-057A` `test_next_auto_starts_first_ready_task_from_task_list`：普通 `-next` 会自动启动任务列表中首个 ready 任务
  - `TC-058` `test_next_auto_spec_dedicated_first`：`spec` 专职可用时仅从专职池选择
  - `TC-059` `test_next_auto_build_dedicated_first`：`build` 专职可用时仅从专职池选择
  - `TC-060` `test_next_auto_build_falls_back_to_substitute`：`build` 专职不可用时回退到候补池
  - `TC-061` `test_next_auto_review_dedicated_first`：`review` 专职可用时仅从专职池选择
  - `TC-062` `test_next_auto_merge_rejects_fallback`：`merge` 无专职且仅候补可用时自动续接失败
  - `TC-062A` `test_next_auto_merge_rejects_non_merge_specialist`：`merge` 自动续接不会错误挑选非合并专职
