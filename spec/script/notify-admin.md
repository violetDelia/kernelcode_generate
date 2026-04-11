# notify-admin.md

## 功能简介

- 定义 `script/notify-admin.sh` 的行为约束。
- 用于按固定间隔向管理员发送会话消息，并在同轮按名单顺序提醒符合条件的 `busy` 执行人。
- 支持按名单配置一次性初始化管理员角色，并支持通过环境变量固定初始化分支，便于复现测试。
- 定时频率、发送身份、名单路径和提醒文案均在脚本顶部配置区维护。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/script/notify-admin.md`](../../spec/script/notify-admin.md)
- `功能实现`：[`script/notify-admin.sh`](../../script/notify-admin.sh)
- `test`：[`test/script/test_notify_admin.py`](../../test/script/test_notify_admin.py)

## 依赖

- 会话发送脚本：[`skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh`](../../skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh)
- 人员名单脚本：[`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](../../skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)
- 默认人员名单：[`agents/codex-multi-agents/agents-lists.md`](../../agents/codex-multi-agents/agents-lists.md)

## 术语

- `管理员提醒`：每轮固定先发给 `TO_NAME` 的提醒文案，默认内容为 `请推进“正在执行的任务”并分发“任务列表”中可分发任务。`
- `busy 提醒`：管理员提醒之后，发给 `agents-lists.md` 中符合条件的 `busy` 执行人的提醒文案，默认内容为 `继续当前任务，完成后使用 -next 并回报管理员。`
- `初始化分支`：循环模式下按 `NOTIFY_ADMIN_RANDOM_ROLL` 或 `RANDOM % 3` 决定是否先调用一次 `codex-multi-agents-list.sh -init` 的分支。

## 目标

- 提供一个长期运行的循环脚本。
- 每轮先向管理员发送一次会话消息，再按名单顺序向符合条件的 `busy` 执行人逐一发送提醒。
- 提供一次性管理员初始化入口，复用人员名单脚本的 `-init` 能力。
- 允许直接编辑脚本顶部配置区来修改发送内容、筛选名单和定时间隔。

## 限制与边界

- 不负责维护消息模板历史版本；提醒内容以脚本顶部配置区的 `ADMIN_MESSAGE` 与 `BUSY_MESSAGE` 为准。
- 不负责动态热加载运行中的脚本；修改配置后需重新启动脚本。
- `-init` 只负责触发管理员初始化，不进入定时循环。
- `busy` 提醒只读取 `AGENTS_LIST_FILE` 指向的 Markdown 表格；筛选依据为 `姓名`、`状态`，并在存在 `介绍`、`职责` 列时应用跳过规则。

## 公开接口

### `notify-admin.sh`

功能说明：

- 默认启动一个无限循环，每轮依次执行：校验配置、判断是否命中初始化分支、发送管理员提醒、发送 `busy` 提醒、休眠 `INTERVAL_SECONDS` 秒。
- 循环模式下命中初始化分支时，会先调用一次管理员初始化脚本，再继续同轮提醒发送。
- 当传入 `-init` 时，按 `TO_NAME` 和 `AGENTS_LIST_FILE` 调用人员名单脚本初始化管理员，并立即结束本次执行。

参数说明：

- 无必选业务参数。
- `-init`：按 `AGENTS_LIST_FILE` 中 `TO_NAME` 对应的人员配置初始化管理员。
- `-h|--help`：输出帮助信息。
- `NOTIFY_ADMIN_RANDOM_ROLL(环境变量)`：可选值为 `0`、`1`、`2`；为 `0` 时命中初始化分支，为 `1` 或 `2` 时跳过初始化分支；未设置时使用 `RANDOM % 3`。

使用示例：

```bash
./script/notify-admin.sh
NOTIFY_ADMIN_RANDOM_ROLL=0 ./script/notify-admin.sh
./script/notify-admin.sh -init
```

注意事项：

- 默认 `INTERVAL_SECONDS=1800`。
- 默认发送身份与路径为：`FROM_NAME="榕"`、`TO_NAME="神秘人"`、`AGENTS_LIST_FILE="agents/codex-multi-agents/agents-lists.md"`。
- 默认提醒文案分为两段：`ADMIN_MESSAGE="请推进“正在执行的任务”并分发“任务列表”中可分发任务。"`，`BUSY_MESSAGE="继续当前任务，完成后使用 -next 并回报管理员。"`。
- 初始化会调用 `codex-multi-agents-list.sh -file <AGENTS_LIST_FILE> -init -name "$TO_NAME"`。
- 循环模式发送会调用 `codex-multi-agents-tmux.sh -talk`，且发送顺序固定为：管理员提醒在前，`busy` 提醒在后；对话日志由 tmux 脚本自动写入 `$(dirname <AGENTS_LIST_FILE>)/log/talk.log`。
- `busy` 提醒目标按 `AGENTS_LIST_FILE` 中表格出现顺序遍历，只向 `状态=busy` 的条目发送，并跳过以下条目：`姓名` 为空、`姓名` 等于 `TO_NAME`、`介绍` 包含 `管理员` 或 `架构师`、`职责` 包含 `管理员` 或 `架构`。
- 若 `AGENTS_LIST_FILE` 中不存在同时包含 `姓名` 与 `状态` 的 Markdown 表格，或本轮不存在符合条件的 `busy` 条目，则本轮只发送管理员提醒。
- 下游 `tmux` 调用返回非零时，当前脚本不会生成独立的 `ERROR(...)` 短语，也不会因该返回码中断本轮剩余 `busy` 提醒；只要后续 `sleep` 成功，循环仍会继续进入下一轮。
- `sleep` 调用失败时，脚本输出稳定短语 `ERROR(5): sleep failed` 并退出。
- `INTERVAL_SECONDS` 必须大于 `0`。
- 循环通知模式下，`FROM_NAME`、`TO_NAME`、`ADMIN_MESSAGE`、`BUSY_MESSAGE` 均不能为空。
- 初始化模式下，`TO_NAME` 与 `AGENTS_LIST_FILE` 均不能为空。
- `NOTIFY_ADMIN_RANDOM_ROLL` 仅允许 `0`、`1`、`2`；其他值必须报错 `ERROR(3): NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2`。

返回与限制：

- 默认模式下正常运行时持续循环，不主动退出。
- `-init` 模式下只执行一次管理员初始化调用，不进入循环。
- 配置非法、依赖脚本不可执行、名单文件缺失或 `sleep` 失败时，脚本会输出稳定 `ERROR(...)` 短语并退出。
- 下游 `tmux` 调用的非零返回码当前不会被包装成独立错误短语；相关行为以本节“注意事项”描述为准。

## 测试

- 测试文件：[`test/script/test_notify_admin.py`](../../test/script/test_notify_admin.py)
- 执行命令：`pytest -q test/script/test_notify_admin.py`
- 测试目标：
  - 校验脚本语法正确。
  - 校验循环模式默认使用 `1800` 秒间隔，并固定遵循“先管理员、后 `busy`”的发送顺序。
  - 校验命中初始化分支时先执行管理员初始化，未命中时不会初始化。
  - 校验 `busy` 提醒会跳过管理员、架构师和 `TO_NAME` 自身。
  - 校验 `-init` 时会调用人员名单脚本完成管理员初始化。
  - 校验 `NOTIFY_ADMIN_RANDOM_ROLL` 非法时会立即报错并给出稳定错误短语。
  - 当前测试清单不覆盖下游 `tmux` 非零返回；该语义由 `script/notify-admin.sh` 与本 `spec` 共同约束。
- 功能与用例清单：
  - `TC-NA-001 / test_notify_admin_loop_uses_default_interval_and_message`：默认循环配置使用 `1800` 秒间隔；同轮先向管理员发送 `ADMIN_MESSAGE`，再向符合条件的 `busy` 执行人发送 `BUSY_MESSAGE`；`sleep` 失败时报 `ERROR(5): sleep failed`。
  - `TC-NA-002 / test_notify_admin_loop_may_trigger_admin_init`：命中初始化分支时，会先调用 `codex-multi-agents-list.sh -init`，再开始会话发送。
  - `TC-NA-003 / test_notify_admin_loop_skips_admin_init_when_roll_misses`：未命中初始化分支时，不会调用管理员初始化脚本，但仍保持“先管理员、后 `busy`”的顺序。
  - `TC-NA-004 / test_notify_admin_init_mode_calls_list_script`：`-init` 模式会调用 `codex-multi-agents-list.sh -file <AGENTS_LIST_FILE> -init -name <TO_NAME>`。
  - `TC-NA-005 / test_notify_admin_rejects_invalid_random_roll`：`NOTIFY_ADMIN_RANDOM_ROLL=3` 会报 `ERROR(3): NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2`。
  - `TC-NA-006 / test_notify_admin_rejects_non_numeric_random_roll`：`NOTIFY_ADMIN_RANDOM_ROLL` 为非数字时会报同一稳定短语。
  - `TC-NA-007 / test_notify_admin_shell_syntax_is_valid`：脚本通过 `bash -n` 语法检查。
