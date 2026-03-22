# 20260322-task-script-one-step-dispatch-plan

## 任务背景

为多 agent 任务流转收敛为单脚本执行，减少“修改 `TODO.md`、修改 `agents-lists.md`、再发 tmux 消息”分步执行时的漏操作。

## 方案结论

- 不新增编排脚本，直接扩展 `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`
- 设计定位：保留 `task.sh` 作为统一入口，内部串起任务表更新、角色状态同步与可选消息发送
- 统一入口：
  - `-new`
  - `-dispatch`
  - `-done`
  - `-pause`
- 新增参数：`-agents-list <path>`
- 新增参数：`-message <text>`（仅 `-dispatch`）

## 编排规则

- `-new`：沿用 `task.sh -new`
- `-dispatch`：
  - 内部先完成 `TODO.md` 与 `agents-lists.md` 更新
  - 若提供 `-message`，再读取 `agents-lists.md` 的 `会话` 字段并调用 `codex-multi-agents-tmux.sh -talk`
- `-done`：
  - 内部完成 `TODO.md` -> `DONE.md` 归档
  - 若该指派在操作后已无其他 `进行中` 任务，则自动将角色状态置为 `free`
- `-pause`：
  - 内部将任务状态更新为 `暂停`
  - 若该指派在操作后已无其他 `进行中` 任务，则自动将角色状态置为 `free`

## 状态约定

- `agents-lists.md` 当前角色状态仅使用：`busy` / `free`
- `-done` / `-pause` 不引入 `paused` 等新状态
- 是否释放角色，只看该角色是否还存在其他 `状态=进行中` 的任务

## 边界

- `-dispatch -message` 之外，不负责任务会话对话或 `/compact` 等行为
- 仍由 `task.sh` 内部统一写 Markdown，不再额外增加编排层
- 若 agent 不存在，`-dispatch` 与 `-new -to` 在修改 `TODO.md` 前失败
- 若 `-dispatch -message` 的消息发送失败，已提交的分发结果不回滚，只返回错误并提示补发消息

## 落地文件

- `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`
- `spec/codex-multi-agents/scripts/codex-multi-agents-task.md`
- `test/codex-multi-agents/test_codex-multi-agents-task.py`

## 测试结果

- 命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`
- 结果：`17 passed`；`task.sh` 已实现 `-agents-list` 必填、角色状态同步，以及 `-dispatch -message` 自动发消息
