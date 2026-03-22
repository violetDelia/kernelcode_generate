# codex-multi-agents-dashboard

## 功能简介

定义 `skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh` 的只读看板行为，覆盖参数校验、agents/任务表解析、摘要区、角色状态区、任务区、最近对话区以及帮助输出。

## 文档信息

- 创建者：`我不是牛马`
- 最后一次更改：`我不是牛马`
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-dashboard.md)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-dashboard.py`](../../../test/codex-multi-agents/test_codex-multi-agents-dashboard.py)

## 依赖

- [`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)：输出 agents 状态表。
- [`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh)：输出 doing/task-list 任务表。
- `agents` 列表 markdown 与 `TODO.md` 任务表：作为 dashboard 的只读数据源。

## 目标

- 为管理员提供单次或定时刷新的终端 dashboard。
- 在不修改数据源的前提下，聚合 agents、doing 任务、任务列表和最近对话。
- 明确错误返回码与展示边界，保证脚本在缺参、缺文件和坏数据下可诊断。

## 限制与边界

- 脚本只读，不写入 agents、TODO 或日志文件。
- `-once` 与 `-refresh` 互斥；`-refresh` 必须是正整数。
- 最近对话区仅在提供 `-log-file` 且未使用 `-no-talk` 时输出。
- 当前功能实现为 shell 脚本；当前环境无法使用 `pytest-cov` 直接统计其覆盖率，`95%` 覆盖率达标线按规则豁免。
- 覆盖充分性以显式用例清单作为当前基线。

## 公开接口

### `codex-multi-agents-dashboard.sh`

功能说明：

- 聚合 agents 名单、任务列表与最近对话日志并输出终端状态总览。

参数说明：

- `-agents-file <path>`：agents 列表文件，必填。
- `-todo-file <path>`：TODO 任务文件，必填。
- `-log-file <path>`：最近对话日志文件，可选。
- `-once`：输出一次后退出。
- `-refresh <seconds>`：按秒循环刷新输出。
- `-no-talk`：隐藏最近对话区。
- `-no-summary`：隐藏摘要区。
- `-h` / `--help`：输出帮助信息并返回成功。

使用示例：

```bash
bash skills/codex-multi-agents/scripts/codex-multi-agents-dashboard.sh \
  -agents-file agents/codex-multi-agents/agents-lists.md \
  -todo-file TODO.md \
  -once
```

注意事项：

- `-agents-file` 与 `-todo-file` 缺失时返回参数错误码 `1`。
- agents/todo 文件路径不存在时返回文件错误码 `2`。
- 上游脚本输出表头缺失或列不完整时返回数据错误码 `3`。
- 未知参数返回参数错误码 `1`。

返回与限制：

- 返回类型：shell 退出码。
- 返回语义：`0` 成功，`1` 参数错误，`2` 文件错误，`3` 数据错误，`5` 内部错误。
- 限制条件：`-refresh` 模式为无限循环，测试仅覆盖 `-once` 与帮助输出等可终止路径。

## 测试

- 测试文件：`test/codex-multi-agents/test_codex-multi-agents-dashboard.py`
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-dashboard.py`
- 覆盖率命令：`N/A`（shell 实现，按规则豁免 `95%` 覆盖率达标线）
- 当前覆盖率信息：当前覆盖率 `N/A`；当前环境下 shell 脚本由子进程执行，`pytest-cov` 会报告 `no-data-collected`，因此以 `TC-001..013` 的显式用例覆盖作为当前覆盖率基线。
- 测试目标：
  - TC-001：单次输出包含摘要、角色状态、任务区和最近对话区。
  - TC-002：缺少 `-agents-file` 返回参数错误。
  - TC-003：缺少 `-todo-file` 返回参数错误。
  - TC-004：`-once` 与 `-refresh` 同时提供时报错。
  - TC-005：`-refresh` 非正整数时报错。
  - TC-006：agents 文件不存在返回文件错误。
  - TC-007：todo 文件不存在返回文件错误。
  - TC-008：`-no-talk` 隐藏最近对话区。
  - TC-009：`-no-summary` 隐藏摘要区。
  - TC-010：日志文件缺失时最近对话区显示空状态。
  - TC-011：角色与 doing 任务正确关联。
  - TC-012：表格列宽对齐且超长字段截断。
  - TC-013：`--help` 输出帮助并返回成功。
- 功能与用例清单：
  - TC-001 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_once`
  - TC-002 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_missing_agents`
  - TC-003 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_missing_todo`
  - TC-004 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_once_refresh_conflict`
  - TC-005 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_invalid_refresh`
  - TC-006 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_missing_agents_file`
  - TC-007 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_missing_todo_file`
  - TC-008 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_no_talk`
  - TC-009 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_no_summary`
  - TC-010 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_missing_log_file`
  - TC-011 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_task_mapping`
  - TC-012 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_alignment_and_truncate`
  - TC-013 -> `test/codex-multi-agents/test_codex-multi-agents-dashboard.py::test_dashboard_help`
