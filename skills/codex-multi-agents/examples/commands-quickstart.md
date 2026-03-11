# codex-multi-agents 命令速查

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

### 初始化人员（通过名单向 tmux 会话发送初始化消息）
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -init -name 小明
```

注意：
- `姓名` 字段不可通过 `-replace` 修改。
- 写操作（`-add/-replace/-delete`）会加 `flock` 文件锁。

## 2. tmux 会话管理（codex-multi-agents-tmux.sh）

脚本路径：`./scripts/codex-multi-agents-tmux.sh`

### 连接会话（不存在则创建）
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -attach -s worker-a
```

### 发送对话并写日志
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -talk -from scheduler -to worker-a -session-id worker-a \
  -message "请处理任务 T1" \
  -log agents/codex-multi-agents/log/talk.log
```

### 按名单初始化角色环境
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -init-env -file agents/codex-multi-agents/agents-lists.md -name 小明
```

## 3. 任务调度（codex-multi-agents-task.sh）

脚本路径：`./scripts/codex-multi-agents-task.sh`

### TODO.md 表头要求（含创建时间）
```markdown
## 正在执行的任务
| 任务 ID | 描述 | 指派 | 创建时间 | 状态 | 用户指导 |
| --- | --- | --- | --- | --- | --- |

## 任务列表
| 任务 ID | 描述 | 指派 | 创建时间 |
| --- | --- | --- | --- |
```

### 新建任务（自动生成任务 ID 与创建时间）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -new -info "实现任务调度器告警" -to worker-b
```

### 分发任务（任务列表 -> 正在执行）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -dispatch -task_id T-20260308-xxxxxxx1 -to worker-a
```

### 暂停任务（正在执行状态 -> 暂停）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -pause -task_id T-20260308-xxxxxxx1
```

### 完成任务（正在执行移除并写入 DONE.md）
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -done -task_id T-20260308-xxxxxxx1 \
  -log ./agents/codex-multi-agents/log/task-T-20260308-xxxxxxx1.log
```

注意：
- `-dispatch` 必须带 `-task_id -to`。
- `-done` 必须带 `-task_id -log`，并自动写同级 `DONE.md`。
- `-new` 必须带 `-info`，`-to` 可选。
- 写操作统一使用 `flock` 文件锁。

## 4. 返回码

- `0`：成功
- `1`：参数错误
- `2`：文件或环境错误
- `3`：数据错误
- `4`：并发或锁错误
- `5`：未分类内部错误
