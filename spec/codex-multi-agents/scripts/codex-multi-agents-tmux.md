# codex-multi-agents-tmux.md

用于对 `codex-multi-agents` 的 tmux 会话进行连接与消息发送。

## [immutable]文件位置

- 脚本文件：[`skills/codex-multi-agents/scripts/codex-multi-agents-tmux`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh)

## 参数约定

- `-attach`：连接 tmux 会话（会话不存在则创建）。
- `-talk`：向目标会话发送一条消息并写入日志。
- `-s`：tmux 会话名（用于 `-attach`）。
- `-from`：消息发送方标识。
- `-to`：消息接收方标识，同时作为 tmux 目标会话名。
- `-message`：消息正文。
- `-log`：对话日志文件路径。

## 并发约束

- `-talk` 追加日志时必须使用 `flock` 文件锁，避免并发写入冲突。
- `-attach` 不涉及文件写入，不做文件锁控制。

## 功能

### 连接会话

命令：

```bash
codex-multi-agents-tmux.sh -attach -s "worker-a"
```

功能说明：

- 若会话存在，执行 `tmux attach -t <session>` 连接会话。
- 若会话不存在，执行 `tmux new -s <session>` 创建并进入新会话。

注意事项：

- `-s` 为必填参数。
- 运行环境必须可用 `tmux` 命令。

### 发送对话

命令：

```bash
codex-multi-agents-tmux.sh -talk -from "scheduler" -to "worker-a" -session-id  <to_id> -message "请处理任务 T1" -log "./agents/codex-multi-agents/log/talk.log"
```

功能说明：

- 发送文本格式固定为：`@<from>向@<to>发起会话: <message>`。
- 使用命令 `tmux send-keys -t <to_id> "<formatted_message>" C-m` 向目标会话发送消息。
- 同步向 `-log` 文件追加一行同内容消息。

注意事项：

- `-from`、`-to`、`-message`、`-log` 均为必填参数。
- 目标会话不存在时返回数据错误。
- 写日志时使用 `flock` 加锁，锁超时/冲突返回锁错误。

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
- 含义：文件或环境错误（日志目录不可写、`tmux` 不可用）。
- 输出：在标准错误（stderr）中打印路径或环境错误原因。

- 返回码：`3`
- 含义：数据错误（目标会话不存在等）。
- 输出：在标准错误（stderr）中打印具体数据校验失败原因。

- 返回码：`4`
- 含义：并发或锁错误（日志文件加锁失败、锁超时、锁冲突）。
- 输出：在标准错误（stderr）中打印锁状态与处理建议。

- 返回码：`5`
- 含义：未分类内部错误（脚本执行异常）。
- 输出：在标准错误（stderr）中打印错误摘要。

## 测试

- 测试文件位置：[`test/codex-multi-agents/test_codex-multi-agents-tmux.py`](../../../test/codex-multi-agents/test_codex-multi-agents-tmux.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-tmux.py`

### 测试目标

- 验证 `-attach` 在会话存在/不存在两种分支下行为正确。
- 验证 `-talk` 的消息格式、tmux 发送与日志追加行为。
- 验证返回码约定：`0/1/2/3/4/5`。
- 验证并发锁冲突下的错误返回。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TC-001 | `-attach` | 会话已存在 | tmux 中存在 `worker-a` | `-attach -s worker-a` | 返回码 `0`；调用 `tmux attach -t worker-a` |
| TC-002 | `-attach` | 会话不存在 | tmux 中不存在 `worker-b` | `-attach -s worker-b` | 返回码 `0`；调用 `tmux new -s worker-b` |
| TC-003 | `-talk` | 正常发送并记日志 | 目标会话存在且日志可写 | `-talk -from A -to B -message M -log L` | 返回码 `0`；发送格式正确；日志新增一行 |
| TC-004 | `-talk` | 目标会话不存在 | tmux 中不存在目标会话 | `-talk -from A -to missing -message M -log L` | 返回码 `3`；报错会话不存在 |
| TC-005 | 参数校验 | 缺少必填参数 | 无 | `-talk -from A -to B -log L` | 返回码 `1`；报错缺少 `-message` |
| TC-006 | 环境校验 | tmux 不可用 | `PATH` 中无 tmux | `-attach -s worker-a` | 返回码 `2`；报错 `tmux not found` |
| TC-007 | 并发锁 | 日志锁冲突 | 另一个进程持有 `<log>.lock` | `-talk -from A -to B -message M -log L` | 返回码 `4`；报错无法加锁 |

### 用例与自动化映射

- TC-001 -> `test_attach_existing_session`
- TC-002 -> `test_attach_create_session_when_missing`
- TC-003 -> `test_talk_send_and_append_log_success`
- TC-004 -> `test_talk_target_session_not_found_returns_rc3`
- TC-005 -> `test_talk_missing_message_returns_rc1`
- TC-006 -> `test_tmux_not_found_returns_rc2`
- TC-007 -> `test_talk_lock_conflict_returns_rc4`
