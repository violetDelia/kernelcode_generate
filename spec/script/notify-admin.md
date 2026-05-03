# notify-admin.md

## 功能简介

- 定义 `script/notify-admin.sh` 的行为约束。
- 用于按固定间隔向管理员发送会话消息，并在同轮按名单顺序提醒符合条件的 `busy` 执行人。
- 支持按名单配置一次性初始化管理员角色，并支持通过环境变量固定初始化分支，便于复现测试。
- 定时频率、发送身份、名单路径和提醒文案均在脚本顶部配置区维护。

## API 列表

- `script/notify-admin.sh(args: Literal["", "-init", "-h", "--help"] = "", *, NOTIFY_ADMIN_RANDOM_ROLL: Literal["0", "1", "2"] | None = None) -> int`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
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

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 不负责维护消息模板历史版本；提醒内容以脚本顶部配置区的 `ADMIN_MESSAGE` 与 `BUSY_MESSAGE` 为准。
- 不负责动态热加载运行中的脚本；修改配置后需重新启动脚本。
- `-init` 只负责触发管理员初始化，不进入定时循环。
- `busy` 提醒只读取 `AGENTS_LIST_FILE` 指向的 Markdown 表格；筛选依据为 `姓名`、`状态`，并在存在 `介绍`、`职责` 列时应用跳过规则。
## API详细说明

### `script/notify-admin.sh(args: Literal["", "-init", "-h", "--help"] = "", *, NOTIFY_ADMIN_RANDOM_ROLL: Literal["0", "1", "2"] | None = None) -> int`

- api：`script/notify-admin.sh(args: Literal["", "-init", "-h", "--help"] = "", *, NOTIFY_ADMIN_RANDOM_ROLL: Literal["0", "1", "2"] | None = None) -> int`
- 参数：
  - `-init`：可选 CLI 参数；按 `AGENTS_LIST_FILE` 中 `TO_NAME` 对应的人员配置初始化管理员；传入后只执行初始化，不进入循环。
  - `-h | --help`：可选 CLI 参数；输出帮助信息。
  - `NOTIFY_ADMIN_RANDOM_ROLL`：可选环境变量；类型为字符串枚举 `"0" | "1" | "2"`；`"0"` 命中初始化分支，`"1"` 与 `"2"` 跳过初始化分支；未设置时使用 `RANDOM % 3`。
- 返回值：默认模式正常运行时持续循环；`-init` 模式执行一次初始化后退出；配置非法、依赖脚本不可执行、名单文件缺失或 `sleep` 失败时输出稳定 `ERROR(...)` 短语并退出。
- 使用示例：

  ```bash
  ./script/notify-admin.sh
  NOTIFY_ADMIN_RANDOM_ROLL=0 ./script/notify-admin.sh
  ./script/notify-admin.sh -init
  ./script/notify-admin.sh --help
  ```
- 功能说明：按固定间隔向管理员发送提醒，并按名单顺序提醒符合条件的 `busy` 执行人；`-init` 模式复用人员名单脚本初始化管理员。
- 注意事项：默认 `INTERVAL_SECONDS=3600`；默认发送身份与路径为 `FROM_NAME="榕"`、`TO_NAME="神秘人"`、`AGENTS_LIST_FILE="agents/codex-multi-agents/agents-lists.md"`；循环模式发送顺序固定为管理员提醒在前、`busy` 提醒在后；`busy` 提醒只发送给 `AGENTS_LIST_FILE` 中 `状态=busy` 且未命中管理员/架构师/`TO_NAME` 跳过条件的条目；`NOTIFY_ADMIN_RANDOM_ROLL` 非 `"0" | "1" | "2"` 时必须报错 `ERROR(3): NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2`；`sleep` 失败时必须报错 `ERROR(5): sleep failed`；下游 `tmux` 调用返回非零时不生成独立 `ERROR(...)` 短语，也不中断本轮剩余 `busy` 提醒。

## 测试

- 测试文件：`test/script/test_notify_admin.py`
- 执行命令：`pytest -q test/script/test_notify_admin.py`

### 测试目标

- 验证 `spec/script/notify-admin.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SCRIPT-NOTIFY-ADMIN-001 | 边界/异常 | 默认循环配置使用 `3600` 秒间隔；同轮先向管理员发送 `ADMIN_MESSAGE`，再向符合条件的 `busy` 执行人发送 `BUSY_MESSAGE`；`sleep` 失败时报 `ERROR(5): sleep failed`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-NA-001 / test_notify_admin_loop_uses_default_interval_and_message`。 | “默认循环配置使用 `3600` 秒间隔；同轮先向管理员发送 `ADMIN_MESSAGE`，再向符合条件的 `busy` 执行人发送 `BUSY_MESSAGE`；`sleep` 失败时报 `ERROR(5): sleep failed`。”场景按公开错误语义失败或被拒绝。 | `TC-NA-001 / test_notify_admin_loop_uses_default_interval_and_message` |
| TC-SCRIPT-NOTIFY-ADMIN-002 | 公开入口 | 命中初始化分支时，会先调用 `codex-multi-agents-list.sh -init`，再开始会话发送。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-NA-002 / test_notify_admin_loop_may_trigger_admin_init`。 | 公开入口在“命中初始化分支时，会先调用 `codex-multi-agents-list.sh -init`，再开始会话发送。”场景下可导入、构造、注册或按名称发现。 | `TC-NA-002 / test_notify_admin_loop_may_trigger_admin_init` |
| TC-SCRIPT-NOTIFY-ADMIN-003 | 公开入口 | 未命中初始化分支时，不会调用管理员初始化脚本，但仍保持“先管理员、后 `busy`”的顺序。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-NA-003 / test_notify_admin_loop_skips_admin_init_when_roll_misses`。 | 公开入口在“未命中初始化分支时，不会调用管理员初始化脚本，但仍保持“先管理员、后 `busy`”的顺序。”场景下可导入、构造、注册或按名称发现。 | `TC-NA-003 / test_notify_admin_loop_skips_admin_init_when_roll_misses` |
| TC-SCRIPT-NOTIFY-ADMIN-004 | 公开入口 | `-init` 模式会调用 `codex-multi-agents-list.sh -file <AGENTS_LIST_FILE> -init -name <TO_NAME>`。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-NA-004 / test_notify_admin_init_mode_calls_list_script`。 | 公开入口在“`-init` 模式会调用 `codex-multi-agents-list.sh -file <AGENTS_LIST_FILE> -init -name <TO_NAME>`。”场景下可导入、构造、注册或按名称发现。 | `TC-NA-004 / test_notify_admin_init_mode_calls_list_script` |
| TC-SCRIPT-NOTIFY-ADMIN-005 | 边界/异常 | `NOTIFY_ADMIN_RANDOM_ROLL=3` 会报 `ERROR(3): NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-NA-005 / test_notify_admin_rejects_invalid_random_roll`。 | “`NOTIFY_ADMIN_RANDOM_ROLL=3` 会报 `ERROR(3): NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2`。”场景按公开错误语义失败或被拒绝。 | `TC-NA-005 / test_notify_admin_rejects_invalid_random_roll` |
| TC-SCRIPT-NOTIFY-ADMIN-006 | 边界/异常 | `NOTIFY_ADMIN_RANDOM_ROLL` 为非数字时会报同一稳定短语。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-NA-006 / test_notify_admin_rejects_non_numeric_random_roll`。 | “`NOTIFY_ADMIN_RANDOM_ROLL` 为非数字时会报同一稳定短语。”场景按公开错误语义失败或被拒绝。 | `TC-NA-006 / test_notify_admin_rejects_non_numeric_random_roll` |
| TC-SCRIPT-NOTIFY-ADMIN-007 | 公开入口 | 脚本通过 `bash -n` 语法检查。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-NA-007 / test_notify_admin_shell_syntax_is_valid`。 | 公开入口在“脚本通过 `bash -n` 语法检查。”场景下可导入、构造、注册或按名称发现。 | `TC-NA-007 / test_notify_admin_shell_syntax_is_valid` |
