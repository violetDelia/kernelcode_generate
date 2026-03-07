---
name: codex-multi-agents
description: 在单仓库内构建多会话执行框架，用于按 TODO.md 分发任务、跟踪状态并记录角色日志。
---

# codex-multi-agents

## 快速跳转
- [适用场景](#适用场景)
- [强制约束](#强制约束)
- [角色交互](#角色交互)
- [目录](#目录)
- [流程](#流程)
- [输出与审计](#输出与审计)
- [参考](#参考)

## 适用场景
- 用户希望把任务拆分给多个角色并行或轮转执行。
- 需要严格隔离角色上下文。
- 需要完整的日志，能追踪每个角色“做过什么”。

## 强制约束


## 角色交互

## 目录
- 日志目录：`agents/codex-multi-agents/log`
- 临时目录：`agents/codex-multi-agents/tmp`
- 配置文件：`agents/codex-multi-agents/config/config.txt`
- 示例目录：`./example/`

## 流程
<a id="step-init"></a>
1. 初始化。
- 如果不存在配置文件，则新增配置文件，示例文件可以参考"./examples.config"。
- 询问用户管理员名称，得到许可后，写入配置文件的 `ROOT_NAME` 字段。
- 询问用户 `TODO.md` 位置并写入配置文件；若不存在，则新建 `./TODO.md`。
- 新建管理员 agents；如需新增角色，转到[新增角色](#step-add-role)步骤。


<a id="step-start"></a>
2. 启动。
- 读取配置文件和 `agents` 名单。
- 如果不存在配置文件，转到[初始化](#step-init)步骤。
- 启动

<a id="step-add-role"></a>
3. 新增角色。
- 确认用户新增角色的名称<name> 
- 确认用户新增角色的类型<type>  "codex"、"claude" 
- 使用 ./scripts/codex-multi-agents-list.sh -add -name <name> -type <type> 新增角色。
- 你的名字为<your_name>,新增角色<name> 的"会话"为<session_id>, 新增角色<name>的"提示词"为<提示词>，新增角色的"职责"为<role>，新增角色<name> 的"worktree"为<worktree>,新增角色<name> 的"归档文件"为<file>。
- 使用 ./scripts/codex-multi-agents-tmux.sh -from <your_name> -to <name> -session-id <session-id> -message "你的名字叫做<name>,你的职责是<role>,你的工作树为<worktree>"





## 参考
