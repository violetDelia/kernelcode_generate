# notify-admin.md

## 功能简介

- 定义 `script/notify-admin.sh` 的行为约束。
- 用于按固定间隔向管理员发送会话消息。
- 支持按名单配置一次性初始化管理员角色。
- 定时频率、管理员信息、日志路径和消息内容均在脚本顶部配置区维护。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/script/notify-admin.md`](../../spec/script/notify-admin.md)
- `功能实现`：[`script/notify-admin.sh`](../../script/notify-admin.sh)
- `test`：`<待补充>`

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
- 初始化会调用 `codex-multi-agents-list.sh -init -name "$TO_NAME"`。
- `INTERVAL_SECONDS` 必须大于 `0`。
- 循环通知模式下，`FROM_NAME`、`TO_NAME`、`LOG_FILE`、`MESSAGE` 均不能为空。
- 初始化模式下，`TO_NAME` 与 `AGENTS_LIST_FILE` 均不能为空。

返回与限制：

- 默认模式下正常运行时持续循环，不主动退出。
- `-init` 模式下初始化成功后立即退出。
- 配置非法、依赖脚本不可执行或下游调用失败时，脚本直接报错退出。

## 测试

- 测试文件：`<待补充>`
- 执行命令：`bash -n script/notify-admin.sh`
- 测试目标：
  - 校验脚本语法正确。
  - 校验顶部配置区的必要字段检查逻辑。
  - 校验发送时会调用管理员会话脚本。
  - 校验 `-init` 时会调用人员名单脚本完成管理员初始化。
- 功能与用例清单：
  - NA-001：合法配置下脚本可通过语法检查。
  - NA-002：缺少必要配置时脚本报错退出。
  - NA-003：发送逻辑使用 `codex-multi-agents-tmux.sh -talk`。
  - NA-004：`-init` 使用 `codex-multi-agents-list.sh -init -name <TO_NAME>`。
