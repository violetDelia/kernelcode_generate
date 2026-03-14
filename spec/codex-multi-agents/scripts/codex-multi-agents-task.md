# codex-multi-agents-task.md

用于对 `TODO.md` 任务进行调度管理（分发、完成、暂停、新建）。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-task.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-task.md)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh)

## 背景

- 用于多线程任务调度。
- 通过统一维护 `TODO.md` 与 `DONE.md`，实现任务生命周期流转。

## 文件与表结构约定

### TODO 文件

- `-file` 指向 `TODO.md`。
- 必须包含以下两个任务段落（标题名需一致）：
  - `## 正在执行的任务`
  - `## 任务列表`
- 可选包含用户确认段落（标题名需一致）：`## 需要用户确认的事项`

`正在执行的任务` 表头要求：

| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

`任务列表` 表头要求：

| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- |

`需要用户确认的事项` 表头要求：

| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |
| --- | --- | --- | --- | --- | --- |

说明：
- 允许 `TODO.md` 内存在其他段落（例如“需要用户确认的事项”），脚本不得破坏无关段落。
- `任务 ID` 在 `正在执行的任务` 和 `任务列表` 两张表的并集内必须唯一。
- `创建时间` 推荐格式：`YYYY-MM-DD HH:MM:SS ±HHMM`。

### DONE 文件

- 路径固定为与 `TODO.md` 同级目录下的 `DONE.md`。
- 若 `DONE.md` 不存在，脚本需自动创建。
- `DONE.md` 记录已完成任务，默认表头如下：

| 任务 ID | 描述 | 指派 | 完成状态 | 完成时间 | 日志文件 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |

说明：
- `完成状态` 固定写入 `已完成`。
- `完成时间` 为执行完成操作时的本地时间，格式要求：`YYYY-MM-DD HH:MM:SS ±HHMM`。

## 参数约定

- `-file`：`TODO.md` 文件路径。
- `-dispatch`：分发任务（从任务列表移入正在执行）。
- `-done`：完成任务（从正在执行移除并写入 `DONE.md`）。
- `-pause`：暂停任务（正在执行中目标任务状态改为 `暂停`）。
- `-new`：新建任务（写入任务列表）。
- `-status`：查看任务列表或正在执行任务。
- `-task_id`：目标任务 ID（用于 `-dispatch/-done/-pause`）。
- `-to`：指派对象（worker 名称）。
- `-from`：发起人（仅 `-new` 使用，可选）。
- `-info`：任务描述（用于 `-new`）。
- `-worktree`：任务对应的工作树（仅 `-new` 使用，可选）。
- `-log`：任务日志文件路径（用于 `-done`）。
- `-log` 在 `-new` 场景下写入 `记录文件` 列（可选）。
- `-doing`：`-status` 下查看正在执行任务。
- `-task-list`：`-status` 下查看任务列表。

## 并发约束

- 所有会写文件的操作（`-dispatch/-done/-pause/-new`）必须使用 `flock`。
- 锁对象为目标文件本体，不创建额外 `.lock` 文件。
- `-done` 涉及 `TODO.md` 与 `DONE.md` 双文件写入时：
  - 必须保证两个文件修改原子可追踪（至少同一次命令内完成）。
  - 锁顺序固定：先锁 `TODO.md`，再锁 `DONE.md`，避免死锁。
- `-status` 为只读操作，不加锁。

## 功能

### 查看状态

命令：

```bash
codex-multi-agents-task.sh "./skills/codex-multi-agents/examples/TODO.md" -file -status -doing
codex-multi-agents-task.sh "./skills/codex-multi-agents/examples/TODO.md" -file -status -task-list
```

功能说明：

- `-doing`：输出 `正在执行的任务` 表头与数据行。
- `-task-list`：输出 `任务列表` 表头与数据行。
- 仅读取 `TODO.md`，不修改文件内容。

### 分发任务

命令：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -dispatch -task_id "EX-3" -to "worker-a"
```

功能说明：

- 从 `任务列表` 按 `任务 ID` 找到目标任务。
- 将该任务从 `任务列表` 删除，并追加到 `正在执行的任务`。
- 若 `worktree` 字段为空，保持空值（不自动写入 `.`）。
- 迁移后字段写入规则：
  - `任务 ID`：沿用原值。
  - `发起人`：沿用原值。
  - `创建时间`：沿用原值。
  - `worktree`：沿用原值（允许为空）。
  - `描述`：沿用原值。
  - `指派`：写入 `-to`。
  - `状态`：写入 `进行中`。
  - `用户指导`：默认空值（保留空列）。
  - `记录文件`：沿用原值。

注意事项：

- `-dispatch` 必须携带 `-task_id`、`-to`。
- 若任务不在 `任务列表` 中，返回 `RC=3`。
- 若同 ID 已存在于 `正在执行的任务`，返回 `RC=3`。

### 完成任务

命令：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -done -task_id "EX-1" -log "./agents/codex-multi-agents/log/task-EX-1.log"
```

功能说明：

- 从 `正在执行的任务` 按 `任务 ID` 找到目标任务。
- 从 `正在执行的任务` 中移除该任务。
- 在同级 `DONE.md` 追加一条完成记录，至少包含：
  - `任务 ID`
  - `描述`
  - `指派`
  - `完成状态`（固定 `已完成`）
  - `完成时间`
  - `日志文件`（写入 `-log`）
- 若 `DONE.md` 不存在，自动创建并写入表头。

注意事项：

- `-done` 必须携带 `-task_id`、`-log`。
- 若任务不在 `正在执行的任务` 中，返回 `RC=3`。
- `-log` 仅作为记录字段写入，不强制校验日志文件是否存在。

### 暂停任务

命令：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -pause -task_id "EX-2"
```

功能说明：

- 在 `正在执行的任务` 中定位目标 `任务 ID`。
- 将目标任务 `状态` 更新为 `暂停`。
- 其余字段保持不变。

注意事项：

- `-pause` 必须携带 `-task_id`。
- 若任务不在 `正在执行的任务` 中，返回 `RC=3`。

### 新建任务

命令：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -new -info "实现任务调度器告警" -to "worker-b" -from "李白" -worktree "repo-x" -log "./log/record-1.log"
```

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -new -info "补充单元测试"
```

`-to/-from/-worktree/-log` 为可选参数，其中 `-log` 对应 `记录文件`。
功能说明：
- 按“日期-hash”规则生成新任务 ID。
- 任务 ID 推荐格式：`T-YYYYMMDD-<8位hash>`。
- 将新任务追加到 `任务列表`。
- 字段写入规则：
  - `任务 ID`：自动生成。
  - `发起人`：写入 `-from`；未提供则写空值。
  - `描述`：写入 `-info`。
  - `指派`：若传入 `-to` 则写入其值，否则写空值。
  - `创建时间`：写入创建当下本地时间。
  - `worktree`：写入 `-worktree`；未提供则写空值。
  - `记录文件`：写入 `-log`；未提供则写空值。

注意事项：

- `-new` 必须携带 `-info`。
- 生成 ID 若发生冲突，需自动重试直到唯一。

## 参数组合约束

- 一次命令只能执行一个主操作：`-dispatch/-done/-pause/-new` 四选一。
- `-dispatch` 仅接受：`-file -task_id -to`。
- `-done` 仅接受：`-file -task_id -log`。
- `-pause` 仅接受：`-file -task_id`。
- `-new` 仅接受：`-file -info [-to] [-from] [-worktree] [-log]`。
- `-status` 仅接受：`-file -status -doing` 或 `-file -status -task-list`。
- 出现未知参数或参数组合非法，返回 `RC=1`。

## 返回与错误

### 成功返回说明

- 返回码：`0`
- 含义：命令执行成功，目标操作已完成。
- 输出：在标准输出（stdout）打印结果信息。

### 失败返回说明

- 返回码：`1`
- 含义：参数错误（参数缺失、参数组合非法、未知参数）。
- 输出：在标准错误（stderr）中打印参数错误原因。

- 返回码：`2`
- 含义：文件错误（`-file` 不存在、不可读、格式不合法）。
- 输出：在标准错误（stderr）中打印文件路径和失败原因。

- 返回码：`3`
- 含义：数据错误（任务不存在、任务 ID 冲突、表头字段非法）。
- 输出：在标准错误（stderr）中打印具体数据校验失败原因。

- 返回码：`4`
- 含义：并发或锁错误（文件加锁失败、锁超时、锁冲突）。
- 输出：在标准错误（stderr）中打印锁状态与处理建议。

- 返回码：`5`
- 含义：未分类内部错误（脚本执行异常）。
- 输出：在标准错误（stderr）中打印错误摘要。

## 测试

- 测试文件位置：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`

### 测试目标

- 验证任务四个核心操作：分发、完成、暂停、新建。
- 验证跨文件流转：`TODO.md -> DONE.md`。
- 验证返回码约定：`0/1/2/3/4/5`。
- 验证并发写入锁冲突返回 `RC=4`。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TC-001 | `-dispatch` | 分发成功 | 任务位于任务列表 | `-file F -dispatch -task_id EX-3 -to worker-a` | 返回码 `0`；任务移入正在执行；状态=`进行中`；`创建时间`保持不变 |
| TC-002 | `-dispatch` | 任务不存在 | 任务列表不存在该 ID | `-file F -dispatch -task_id BAD -to worker-a` | 返回码 `3`；报错 task not found |
| TC-003 | `-done` | 完成成功 | 任务位于正在执行 | `-file F -done -task_id EX-1 -log L` | 返回码 `0`；TODO 移除任务；DONE 追加记录 |
| TC-004 | `-done` | 任务不存在 | 正在执行不存在该 ID | `-file F -done -task_id BAD -log L` | 返回码 `3`；报错 task not found |
| TC-005 | `-pause` | 暂停成功 | 任务位于正在执行 | `-file F -pause -task_id EX-2` | 返回码 `0`；状态变为 `暂停` |
| TC-006 | `-pause` | 任务不存在 | 正在执行不存在该 ID | `-file F -pause -task_id BAD` | 返回码 `3`；报错 task not found |
| TC-007 | `-new` | 新建成功（带指派） | TODO 结构合法 | `-file F -new -info "desc" -to worker-b` | 返回码 `0`；任务列表新增记录且指派=worker-b，`创建时间`写入成功 |
| TC-008 | `-new` | 新建成功（不带指派） | TODO 结构合法 | `-file F -new -info "desc"` | 返回码 `0`；任务列表新增记录且指派为空，`创建时间`写入成功 |
| TC-009 | 参数校验 | 缺少必填参数 | TODO 存在 | `-file F -done -task_id EX-1` | 返回码 `1`；报错缺少 `-log` |
| TC-010 | 文件校验 | TODO 文件不存在 | 路径不存在 | `-file missing -new -info "desc"` | 返回码 `2`；报错 file not found |
| TC-011 | 表结构校验 | 缺少任务段落或表头 | TODO 非法 | `-file F -new -info "desc"` | 返回码 `2`；报错 invalid table format |
| TC-012 | 并发锁 | 锁冲突 | 另一个进程持有 TODO 锁 | `-file F -dispatch -task_id EX-3 -to worker-a` | 返回码 `4`；报错 cannot acquire lock |
| TC-013 | `-status` | 输出正在执行任务 | TODO 结构合法 | `-file F -status -doing` | 返回码 `0`；输出包含运行中任务表 |
| TC-014 | `-status` | 输出任务列表 | TODO 结构合法 | `-file F -status -task-list` | 返回码 `0`；输出包含任务列表表 |
| TC-015 | `-status` | 参数组合错误 | TODO 结构合法 | `-file F -status` 或 `-file F -status -doing -task-list` | 返回码 `1`；报错 requires exactly one of -doing/-task-list |

### 用例与自动化映射

- TC-001 -> `test_dispatch_task_success`
- TC-002 -> `test_dispatch_missing_task_returns_rc3`
- TC-003 -> `test_done_task_moves_to_done_file_success`
- TC-004 -> `test_done_missing_task_returns_rc3`
- TC-005 -> `test_pause_task_success`
- TC-006 -> `test_pause_missing_task_returns_rc3`
- TC-007 -> `test_new_task_with_assignee_success`
- TC-008 -> `test_new_task_without_assignee_success`
- TC-009 -> `test_argument_error_returns_rc1`
- TC-010 -> `test_file_not_found_returns_rc2`
- TC-011 -> `test_invalid_todo_structure_returns_rc2`
- TC-012 -> `test_lock_conflict_returns_rc4`
- TC-013 -> `test_status_doing_outputs_running_table`
- TC-014 -> `test_status_task_list_outputs_list_table`
- TC-015 -> `test_status_requires_exactly_one_mode`
