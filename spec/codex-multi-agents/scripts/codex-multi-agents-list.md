# codex-multi-agents-list.md

用于对 `codex-multi-agents` 的 agents 名单进行读取和维护。

## [immutable]文件位置

- 脚本文件：[`skills/codex-multi-agents/scripts/codex-multi-agents-list`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)
- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-list.py`](../../../test/codex-multi-agents/test_codex-multi-agents-list.py)

## [immutable]参考

- 名单参考文件：[`agents-lists.md`](../../examples/scripts/codex-multi-agents-list/agents-lists.md)

## 参数约定

- `-file`：名单文件路径。
- `-status`：读取并展示名单信息（按列宽对齐输出）。
- `-replace`：修改指定人员的字段值。
- `-add`：新增人员。
- `-delete`：删除人员。
- `-name`：人员姓名（用于定位目标行）。
- `-key`：待修改字段名。
- `-value`：待写入字段值。

## 字段约束

- `姓名` 为不可修改字段，不允许通过 `-replace` 修改。
- `姓名` 在名单文件中必须唯一。
- 字段名必须与名单表头一致。

## 并发约束

- 写操作（`-replace`、`-add`、`-delete`）使用 `flock` 文件锁，避免并发写入冲突。
- 读操作（`-status`）不加锁，仅进行只读解析和展示。

## 功能

### 读取 agents 名单

命令：

```bash
codex-multi-agents-list.sh -file "agents-list.md" -status
```

功能说明：

- 读取 `-file` 指定的名单文件。
- 在终端输出名单中的 agent 信息及状态信息。
- 读取阶段会统计各列最大显示宽度，输出时按宽度对齐，保证表格整齐。

注意事项：

- `-file` 路径必须存在且可读。
- 名单文件需符合参考结构，否则解析结果可能不完整。
- 建议使用 UTF-8 编码保存名单文件。

### 修改字段

命令：

```bash
codex-multi-agents-list.sh -replace -name "xiaoming" -key "归档文件" -value "aaa"
```

功能说明：

- 根据人员 `name` 修改指定字段 `key` 的值。

注意事项：

- 关键字 `姓名` 不可修改。
- 修改时使用 `flock` 加锁，避免并发写入导致数据冲突。

### 查询
```bash
codex-multi-agents-list.sh -find -name "xiaoming" -key "归档文件" 
```

功能说明：

- 根据人员 `name` 查找指定字段 `key` 的值。

注意事项：

- 修改时使用 `flock` 加锁，避免并发写入导致数据冲突。

### 添加人员

命令：

```bash
codex-multi-agents-list.sh -add -name "liming" -type "codex"
```

注意事项：

- 不允许添加同名人员。
- 写入前使用 `flock` 加锁，避免并发冲突。
- 添加人员时，随机生成一个不重复的"会话"、"agent session"、"worktree"值。值不能含有中文字符。
- 选项type对应的值为"启动设置",值为codex、claude等。
- 如果type 为codex `bash ./codex-multi-agents-tmux.sh -attach -s -attach -s <会话> | codex | tmux -send-keys -t <会话> "/rename <name> | tmux -send-keys -t <会话> ENTER"`,其他type 尚未支持。

### 删除人员

命令：

```bash
codex-multi-agents-list.sh -delete -name "xiaoming"
```

注意事项：

- 删除前使用 `flock` 加锁，避免并发冲突。

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
- 含义：数据错误（目标人员不存在、人员重名、字段名非法）。
- 输出：在标准错误（stderr）中打印具体数据校验失败原因。

- 返回码：`4`
- 含义：并发或锁错误（文件加锁失败、锁超时、锁冲突）。
- 输出：在标准错误（stderr）中打印锁状态与处理建议。

- 返回码：`5`
- 含义：未分类内部错误（脚本执行异常）。
- 输出：在标准错误（stderr）中打印错误摘要。

## 测试

- 测试文件位置：[`test/codex-multi-agents/test_codex-multi-agents-list.py`](../../../test/codex-multi-agents/test_codex-multi-agents-list.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py`

### 测试目标

- 验证 `agents` 名单脚本的 4 个核心功能：读取、添加、修改、删除。
- 验证返回码约定：`0/1/2/3/4/5` 的行为是否符合文档定义。
- 验证字段约束：`姓名` 不可改、`姓名` 唯一、字段名合法。
- 验证并发行为：文件锁冲突时是否正确失败。

### 测试范围

- 命令行参数解析与参数组合校验。
- Markdown 表格结构解析与数据完整性校验。
- 文件读写与原子更新。
- 并发锁（`flock`）处理。

### 用例设计说明

- 每个用例包含：前置条件、操作命令、预期返回码、预期输出/文件变更。
- 单测使用临时文件，避免污染真实名单文件。
- 用例命名采用 `test_<功能>_<场景>`，便于定位失败原因。
- 测试函数注释需包含：`TC-编号`、`Last Run`、`Last Success`、功能文件路径、`spec` 文件路径。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 后置检查 |
|---|---|---|---|---|---|---|
| TC-001 | `-status` | 正常读取名单 | 合法名单文件存在 | `-file <path> -status` | 返回码 `0`；输出包含表头与人员数据 | 文件内容不发生变更 |
| TC-002 | `-add` | 新增人员成功 | 名单中不存在目标姓名 | `-file <path> -add -name 王五` | 返回码 `0`；文件新增 `王五` 行 | 新增后可被 `-status` 读到 |
| TC-003 | `-add` | 新增同名人员 | 名单中已存在 `小明` | `-file <path> -add -name 小明` | 返回码 `3`；报错 `agent already exists` | 文件内容不变 |
| TC-004 | `-replace` | 修改字段成功 | 名单中存在 `小明` 且字段 `状态` 存在 | `-file <path> -replace -name 小明 -key 状态 -value ready` | 返回码 `0`；`小明` 的 `状态` 被更新 | 再次读取确认值已更新 |
| TC-005 | `-replace` | 修改不可变字段 `姓名` | 名单中存在目标人员 | `-file <path> -replace -name 小明 -key 姓名 -value 新名字` | 返回码 `3`；报错 `immutable` | 文件内容不变 |
| TC-006 | `-replace` | 修改非法字段 | 名单中不存在该字段名 | `-file <path> -replace -name 小明 -key 不存在字段 -value x` | 返回码 `3`；报错 `invalid field name` | 文件内容不变 |
| TC-007 | `-delete` | 删除人员成功 | 名单中存在 `李白` | `-file <path> -delete -name 李白` | 返回码 `0`；文件中不再包含 `李白` | 再次读取确认 `李白` 不存在 |
| TC-008 | `-delete` | 删除不存在人员 | 名单中不存在目标姓名 | `-file <path> -delete -name 不存在` | 返回码 `3`；报错 `agent not found` | 文件内容不变 |
| TC-009 | 参数校验 | 缺少必填参数 | 合法名单文件存在 | `-file <path> -replace -name 小明 -key 状态` | 返回码 `1`；报错缺少 `-value` | 文件内容不变 |
| TC-010 | 文件校验 | 文件不存在 | 指定路径不存在 | `-file <missing> -status` | 返回码 `2`；报错 `file not found` | 不产生新文件 |
| TC-011 | 表结构校验 | 表头缺少 `姓名` 列 | 文件为非法表头 | `-file <path> -status` | 返回码 `2`；报错缺少 `姓名` 列 | 文件内容不变 |
| TC-012 | 数据校验 | 名单内 `姓名` 重复 | 文件中存在重复姓名 | `-file <path> -status` | 返回码 `3`；报错 `duplicate 姓名` | 文件内容不变 |
| TC-013 | 并发锁 | 锁冲突 | 另一个进程已持有 `<file>.lock` | `-file <path> -add -name 并发测试` | 返回码 `4`；报错 `cannot acquire lock` | 文件内容不变 |

### 通过准则

- 所有用例执行完成，且返回码与预期一致。
- 文件内容变更类用例（新增/修改/删除）均验证到实际文件状态。
- 错误路径用例在 `stderr` 输出可识别错误信息。

### 用例与自动化映射

- TC-001 -> `test_status_outputs_table_and_returns_0`
- TC-002 -> `test_add_agent_success`
- TC-003 -> `test_add_duplicate_agent_returns_rc3`
- TC-004 -> `test_replace_field_success`
- TC-005 -> `test_replace_name_field_is_immutable`
- TC-006 -> `test_replace_unknown_field_returns_rc3`
- TC-007 -> `test_delete_agent_success`
- TC-008 -> `test_delete_missing_agent_returns_rc3`
- TC-009 -> `test_argument_error_returns_rc1`
- TC-010 -> `test_file_not_found_returns_rc2`
- TC-011 -> `test_invalid_table_missing_name_column_returns_rc2`
- TC-012 -> `test_duplicate_name_in_file_returns_rc3`
- TC-013 -> `test_lock_conflict_returns_rc4`
