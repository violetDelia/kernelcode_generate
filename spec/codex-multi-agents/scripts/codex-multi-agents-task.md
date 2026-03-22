# codex-multi-agents-task.md

## 功能简介

定义 `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh` 的任务调度行为，覆盖任务分发、完成、暂停、新建与状态查询，并约束 `TODO.md`/`DONE.md` 的读写规则。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-task.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-task.md)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh)

## 依赖

- `TODO.md`：任务数据源。
- `DONE.md`：完成任务归档文件（与 `TODO.md` 同级目录）。
- `flock`：用于写操作锁定。

## 目标

- 提供统一的任务分发、完成、暂停、新建与状态查询命令。
- 维护 `TODO.md` 与 `DONE.md` 的一致性与可追踪性。
- 在缺参、缺文件、坏数据或锁冲突时给出明确返回码。

## 限制与边界

- 只读/写 `TODO.md` 与 `DONE.md`，不得修改其他段落内容。
- 一次命令只能执行一个主操作：`-dispatch/-done/-pause/-new` 四选一。
- `TODO.md` 必须包含段落：
  - `## 正在执行的任务`
  - `## 任务列表`
  - 可选 `## 需要用户确认的事项`
- `正在执行的任务` 表头：
  - `| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |`
- `任务列表` 表头：
  - `| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |`
- `需要用户确认的事项` 表头：
  - `| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |`
- `任务 ID` 在 `正在执行的任务` 与 `任务列表` 中必须唯一。
- `DONE.md` 位于 `TODO.md` 同级目录；若不存在需自动创建，默认表头：
  - `| 任务 ID | 描述 | 指派 | 完成状态 | 完成时间 | 日志文件 | 备注 |`
- `完成状态` 固定写入 `已完成`。
- `创建时间`/`完成时间` 推荐格式：`YYYY-MM-DD HH:MM:SS ±HHMM`。
- 并发约束：
  - `-dispatch/-done/-pause/-new` 必须使用 `flock` 锁定目标文件。
  - `-done` 同时写 `TODO.md` 与 `DONE.md` 时，锁顺序固定为先 `TODO.md` 后 `DONE.md`。
  - `-status` 只读，不加锁。
- 返回码约定：
  - `0` 成功。
  - `1` 参数错误。
  - `2` 文件错误。
  - `3` 数据错误（任务不存在、ID 冲突、表头非法）。
  - `4` 锁冲突或并发错误。
  - `5` 内部错误。

## 公开接口

### `codex-multi-agents-task.sh`

功能说明：

- 统一处理任务调度与查询命令。

参数说明：

- `-file <path>`：`TODO.md` 文件路径（必填）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -status -doing
```

注意事项：

- `-file` 必须存在且结构合法。

返回与限制：

- 返回码遵循“限制与边界”约定。

#### `-status`

功能说明：

- 输出任务状态表（正在执行或任务列表）。

参数说明：

- `-status`：查看任务状态。
- `-doing`：输出正在执行任务表。
- `-task-list`：输出任务列表表。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -status -doing
```

注意事项：

- `-doing` 与 `-task-list` 必须且只能二选一。

返回与限制：

- 成功返回 `0`，参数组合错误返回 `1`。

#### `-dispatch`

功能说明：

- 从任务列表分发任务至正在执行区。

参数说明：

- `-dispatch`：执行分发操作。
- `-task_id <id>`：目标任务 ID（必填）。
- `-to <name>`：指派对象（必填）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -dispatch -task_id "EX-3" -to "worker-a"
```

注意事项：

- 若任务不在任务列表中，返回 `3`。
- 若 `worktree` 为空，保持空值。
- 迁移后写入 `状态=进行中`，`用户指导` 保持空列。

返回与限制：

- 成功返回 `0`；任务不存在或冲突返回 `3`。

#### `-done`

功能说明：

- 完成任务并写入 `DONE.md`。

参数说明：

- `-done`：执行完成操作。
- `-task_id <id>`：目标任务 ID（必填）。
- `-log <path>`：日志文件路径（必填，写入记录）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -done -task_id "EX-1" -log "./log/record.md"
```

注意事项：

- 任务不存在返回 `3`。
- `-log` 仅写入记录字段，不校验文件存在性。

返回与限制：

- 成功返回 `0`；失败返回对应错误码。

#### `-pause`

功能说明：

- 暂停正在执行的任务。

参数说明：

- `-pause`：执行暂停操作。
- `-task_id <id>`：目标任务 ID（必填）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -pause -task_id "EX-2"
```

注意事项：

- 任务不存在返回 `3`。

返回与限制：

- 成功返回 `0`；失败返回对应错误码。

#### `-new`

功能说明：

- 新建任务并写入任务列表。

参数说明：

- `-new`：执行新建操作。
- `-info <desc>`：任务描述（必填）。
- `-to <name>`：指派对象（可选）。
- `-from <name>`：发起人（可选）。
- `-worktree <path>`：工作树（可选）。
- `-log <path>`：记录文件（可选，写入“记录文件”列）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -new -info "补充单元测试" -to "worker-b"
```

注意事项：

- 任务 ID 按“日期-hash”规则生成，推荐格式 `T-YYYYMMDD-<8位hash>`。

返回与限制：

- 成功返回 `0`；失败返回对应错误码。

## 测试

- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`
- 覆盖率命令：`pytest -q --cov=skills/codex-multi-agents/scripts/codex-multi-agents-task.sh --cov-branch --cov-report=term-missing test/codex-multi-agents/test_codex-multi-agents-task.py`
- 当前覆盖率信息：`N/A`（shell 脚本由子进程执行，`pytest-cov` 会报告 `no-data-collected`；按规则豁免 `95%` 覆盖率达标线，以 `TC-001..015` 用例覆盖为当前基线）

### 测试目标

- 验证任务分发、完成、暂停、新建与状态查询。
- 验证 `TODO.md` 与 `DONE.md` 的跨文件流转。
- 验证返回码约定 `0/1/2/3/4/5`。
- 验证并发锁冲突返回 `RC=4`。

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
