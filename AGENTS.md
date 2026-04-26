# AGENTS.md

## 约定

- 未经特别授权，不得修改 `.skills` 目录中的任何文件。
- 未经用户明确授权，任何角色不得修改、移动、重命名或新建仓库中的 `expectation` 文件；`expectation` 只允许读取、执行、引用与记录，不得写入正常任务改动范围。
- `build` 可在当前文件内新增为实现当前 `spec` 明确定义 `API` 服务的辅助函数，但不得新增未在 `spec` 明确定义的公开接口，也不得以直接调用、包装转发、别名导入、反射或其他方式使用当前文件之外的非公开 `API` 函数、方法或隐藏 helper。
- `build` 修改功能实现文件时，必须同步在对应文件的文件级说明中补齐或更新 `API 列表`；`API 列表` 必须紧跟在 `功能说明` 后，只做快速索引，列出该文件承载的公开 `API` 与参数签名。若文件承载 `class`，必须列出类公开 `API`。
- `spec`、`review` 与架构互评 / 终验时，必须检查实现是否混入非 `API` 函数、是否跨文件使用非公开 `API`，以及测试是否直接调用非 `API` 接口。
- `review` 与复审不得以“只是内部 helper”“测试方便”“当前能跑”为由放行任何当前文件之外的非公开 `API` 使用。
- 架构师或管理员创建、分发任务时，`任务目标` 必须是执行人可直接落地的动作语句，例如“添加 `xxx` 接口”“为 `xxx` 函数增加 `yyy` 功能”“跑通 `python3 -m expectation.xxx` / `pytest ...`”；不得使用“整理一下”“看下问题”“继续推进”“按当前口径收口”这类无法直接执行的泛目标。
- 计划书与任务边界默认按“模块范围 + 禁止修改面 + 合同真源”约束，不按实现侧逐文件白名单约束；只要改动仍位于计划指定模块内、且符合 `spec`、审查与仓库规范，执行人可修改相关实现、测试与必要辅助文件。
- 只做计划书时，架构师在形成可下发版本前，必须至少与 `3` 个对象讨论并留下记录；对象可以是另一位架构师、实现执行人、审查人、相关模块维护者或用户本人，但不得少于 `3` 个。
- 计划书阶段凡是存在争议、冲突、口径不一致或不确定事项，一律由用户确认；在收到用户确认前，不得擅自补假设、拍板方案或把主观推断写成既定结论。
- 所有功能实现文件与新增/修改函数都必须遵守 [`agents/standard/实现文件规范.md`](agents/standard/实现文件规范.md)：文件级说明必须包含 `创建者 / 最后一次更改 / 功能说明 / API 列表 / 使用示例 / 关联文件`，其中 `API 列表` 必须紧跟在 `功能说明` 后；函数注释必须至少包含 `创建者 / 最后一次更改 / 功能说明 / 使用示例`。
- 常规任务日志、阻塞记录与待确认记录默认写入对应 `worktree`；主仓根目录不作为常规日志落点，只保留共享状态文件与无独立 `worktree` 的例外结论。
- 文件链接示例：
  - `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-list.md`](spec/codex-multi-agents/scripts/codex-multi-agents-list.md)
  - `test`：[`test/codex-multi-agents/test_codex-multi-agents-list.py`](test/codex-multi-agents/test_codex-multi-agents-list.py)
  - `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)

## 目录结构

- `<待填写>`

## 项目说明

- 项目目标：`<待填写>`
- 生效范围：`<待填写>`

## 测试文件约定

- [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)

## Diff 反推测试与终验

- 除 `merge` 外，`spec`、`build`、`review`、替补和终验修复执行人推进前必须完成自检，并在任务记录写清 `自检` 结果；缺失时审查、管理员或合并角色应退回补齐。
- 自检必须按角色写重点：`spec` 查接口、边界、异常、兼容性和文字歧义；`build` 查遗漏、冗余、注释准确性、复用、函数粒度、输入/输出校验、并发、资源、性能和兼容性；`review` 查特殊情况、完整性、维护性、扩展性、测试有效性和所有可改进点；计划书查示例、API 设计、任务边界、风险和方案取舍。
- `build`、重构执行、审查与复审不能只运行任务树或计划书列出的命令；必须按实际 diff 反推测试，并在任务日志写清 `Diff 反推自测` / `Diff 反推审查`。
- `Diff 反推测试` 只包含 `pytest`、测试脚本或可作为测试运行的本地脚本；`expectation` 是合同验收资产，不计入 diff 反推测试，也不能替代改动文件对应测试。
- 架构师做计划书终验、复验或终验修复复核时，必须在最新同步现场运行与本轮改动有关的 `expectation` 合同验收；未运行或失败时不得给出通过结论。只有用户明确要求全量 `expectation` 时，才按全量执行；环境依赖例外也必须由用户明确确认。

## 任务记录约定

- [`agents/standard/任务记录约定.md`](agents/standard/任务记录约定.md)

## [immutable]

- 带有 `[immutable]` 或 `[immutable-file]` 标记的内容，默认视为高敏感内容。
- 不得修改带有 `[immutable]` 或 `[immutable-file]` 标记的内容。
- 带有 `[immutable-file]` 标记的文件整体不可修改。
- 若文件位于 `expectation/` 下，即使没有显式标记 `[immutable-file]`，也默认按“不可修改、不可移动、不可重命名、不可新建”的规则处理，除非用户明确授权放开。

## 编码约定

- 目录约定：`<待填写>`
- 风格约定：`<待填写>`
- 测试约定：`<待填写>`

### spec 文件规范

- [`agents/standard/spec文件规范.md`](agents/standard/spec文件规范.md)

### 实现文件规范

- [`agents/standard/实现文件规范.md`](agents/standard/实现文件规范.md)

### 审查规范

- [`agents/standard/审查规范.md`](agents/standard/审查规范.md)

## 合并规范

- [`agents/standard/合并规范.md`](agents/standard/合并规范.md)
