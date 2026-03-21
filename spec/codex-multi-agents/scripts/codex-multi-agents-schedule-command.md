# 功能简介

`codex-multi-agents-schedule-command.sh` 用于按固定时间间隔周期性执行 shell 命令。脚本默认执行 `mand`，也支持通过参数指定其他命令、执行次数、运行 shell 和日志文件。

## 文档信息

- 创建者：`Codex`
- 最后一次更改：`Codex`
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-schedule-command.md)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-schedule-command.py`](../../../test/codex-multi-agents/test_codex-multi-agents-schedule-command.py)

## 依赖

- Shell 解释器：[`/bin/bash`](/bin/bash)
- 功能实现文件：[`skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-schedule-command.sh)
- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-schedule-command.py`](../../../test/codex-multi-agents/test_codex-multi-agents-schedule-command.py)

## 目标

- 提供一个无需额外系统服务即可使用的“固定间隔调度”脚本。
- 默认场景下定时执行 `mand`。
- 允许调用方显式控制执行次数，方便集成到自动化测试和 CI 流程。

## 限制与边界

- `-interval` 必须是非负整数，单位为秒。
- `-count` 必须是非负整数；`0` 表示无限循环执行。
- 脚本只负责本进程内循环调度，不负责写入 `crontab`、创建 `systemd` 服务或守护化运行。
- 若被调度命令返回非零退出码，脚本立即停止并返回错误。
- 日志文件仅做追加写入，不负责日志轮转。

## 公开接口

### CLI: `codex-multi-agents-schedule-command.sh`

#### 功能说明

按固定时间间隔执行指定命令；默认命令为 `mand`。

#### 参数说明

- `-interval`(`int`): 执行间隔秒数，必填，允许为 `0`。
- `-count`(`int`): 执行次数，选填，默认 `0`，表示无限循环。
- `-command`(`string`): 需要执行的命令字符串，选填，默认 `mand`。
- `-log-file`(`string`): 追加写入日志的文件路径，选填。
- `-shell`(`string`): 执行命令时使用的 shell 路径，选填，默认取当前 `SHELL`，若为空则回退到 `/bin/bash`。

#### 使用示例

```bash
codex-multi-agents-schedule-command.sh -interval 60 -count 1
codex-multi-agents-schedule-command.sh -interval 5 -count 3 -command 'mand --mode batch'
codex-multi-agents-schedule-command.sh -interval 10 -count 2 -command 'echo hello' -log-file ./schedule.log
```

#### 注意事项

- 若需要测试脚本行为，建议传入 `-count`，避免进入无限循环。
- `-command` 由 shell 执行，命令中的引号和转义需由调用方自行保证正确。
- 当 `-log-file` 指向的父目录不存在时，脚本会尝试自动创建。

#### 返回与限制

- 返回类型：进程退出码。
- 返回语义：
  - `0`：全部调度轮次执行成功。
  - `1`：参数错误。
  - `2`：shell 不存在、不可执行，或日志文件不可创建。
  - `3`：被调度命令执行失败。
  - `5`：预留给未分类内部错误。
- 限制条件：脚本不会吞掉被调度命令的非零退出状态。

## 测试

- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-schedule-command.py`](../../../test/codex-multi-agents/test_codex-multi-agents-schedule-command.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-schedule-command.py`
- 测试目标：
  - 验证默认命令 `mand` 可以被定时执行。
  - 验证自定义命令、执行次数和日志写入行为。
  - 验证命令失败时停止调度并返回 `RC=3`。
  - 验证参数校验和 shell 环境校验行为。
- 功能与用例清单：
  - `TC-001`：自定义命令按指定次数执行成功。
  - `TC-002`：默认命令 `mand` 可从 `PATH` 中解析并执行。
  - `TC-003`：命令失败时返回 `RC=3` 且停止后续执行。
  - `TC-004`：缺少 `-interval` 时返回 `RC=1`。
  - `TC-005`：shell 不存在时返回 `RC=2`。
