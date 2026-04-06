# notify-admin.md

## 功能简介

- 定义 `script/notify-admin.sh` 的行为约束。
- 用于按固定间隔向管理员发送会话消息。
- 支持按名单配置一次性初始化管理员角色。
- 定时频率、管理员信息、日志路径和消息内容均在脚本顶部配置区维护。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/script/notify-admin.md`](../../spec/script/notify-admin.md)
- `功能实现`：[`script/notify-admin.sh`](../../script/notify-admin.sh)
- `test`：[`test/script/test_notify_admin.py`](../../test/script/test_notify_admin.py)

## 依赖

- 会话发送脚本：[`skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh`](../../skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh)
- 人员名单脚本：[`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](../../skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)

## 目标

- 提供一个长期运行的循环脚本。
- 每轮按当前配置向管理员发送一次会话消息。
- 提供一次性管理员初始化入口，复用人员名单脚本的 `-init` 能力。
- 允许直接编辑脚本顶部配置区来修改发送内容和定时间隔。

## 限制与边界

- 不负责创建管理员会话；目标会话必须已存在。
- 不负责动态热加载运行中的脚本；修改配置后需重新启动脚本。
- 不负责消息模板管理；消息内容直接由脚本顶部配置区提供。
- `-init` 只负责触发管理员初始化，不进入定时循环。

## 公开接口

### `notify-admin.sh`

功能说明：

- 默认启动一个无限循环，按配置区的 `INTERVAL_SECONDS` 周期执行一次管理员会话发送。
- 循环模式下每轮按 `1/3` 概率先调用一次管理员初始化脚本，再继续发送会话消息。
- 当传入 `-init` 时，按 `TO_NAME` 和 `AGENTS_LIST_FILE` 调用人员名单脚本初始化管理员，并立即退出。

参数说明：

- 无必选业务参数。
- `-init`：按 `AGENTS_LIST_FILE` 中 `TO_NAME` 对应的人员配置初始化管理员。
- `-h|--help`：输出帮助信息。

使用示例：

```bash
./script/notify-admin.sh
./script/notify-admin.sh -init
```

注意事项：

- 发送会调用 `codex-multi-agents-tmux.sh -talk`。
- 初始化会调用 `codex-multi-agents-list.sh -file <agents-lists.md> -init -name "$TO_NAME"`。
- 测试时可通过 `NOTIFY_ADMIN_RANDOM_ROLL=0|1|2` 固定循环模式是否命中 `1/3` 初始化分支。
- 默认 `INTERVAL_SECONDS=3600`。
- 默认 `MESSAGE` 为两句：`询问正在运行任务的人，要求回报并继续。`、`逐个更新任务书，推动任务有序完成。`
- `INTERVAL_SECONDS` 必须大于 `0`。
- 循环通知模式下，`FROM_NAME`、`TO_NAME`、`LOG_FILE`、`MESSAGE` 均不能为空。
- 初始化模式下，`TO_NAME` 与 `AGENTS_LIST_FILE` 均不能为空。

返回与限制：

- 默认模式下正常运行时持续循环，不主动退出。
- `-init` 模式下初始化成功后立即退出。
- 配置非法、依赖脚本不可执行或下游调用失败时，脚本直接报错退出。

## 测试

- 测试文件：[`test/script/test_notify_admin.py`](../../test/script/test_notify_admin.py)
- 执行命令：`pytest -q test/script/test_notify_admin.py`
- 测试目标：
  - 校验脚本语法正确。
  - 校验默认 `INTERVAL_SECONDS=3600` 与默认 `MESSAGE` 两句内容。
  - 校验循环模式命中 `1/3` 分支时会先执行管理员初始化，未命中时不会初始化。
  - 校验 `NOTIFY_ADMIN_RANDOM_ROLL` 非法时会 fail-fast 并给出稳定错误短语。
  - 校验 `-init` 时会调用人员名单脚本完成管理员初始化。
- 功能与用例清单：
  - NA-001：合法配置下脚本可通过语法检查。
  - NA-002：默认循环配置使用 `3600` 秒间隔并透传两句默认通知消息。
  - NA-003：循环模式命中 `1/3` 分支时会先执行一次管理员初始化，未命中则不会初始化。
  - NA-004：`-init` 使用 `codex-multi-agents-list.sh -file <AGENTS_LIST_FILE> -init -name <TO_NAME>`。
