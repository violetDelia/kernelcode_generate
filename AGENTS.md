# AGENTS.md

## 约定

- 未经特别授权，不得修改 `.skills` 目录中的任何文件。
- 所有函数与文件都需补充完整的功能说明和使用示例，并提供对应的 `创建者`、`最后修改人`、`spec`、`test`、`功能实现` 文件链接。
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
- 架构师做计划书终验、复验或终验修复复核时，必须在最新同步现场运行全量 `expectation` 合同验收；未运行或失败时不得给出通过结论，除非用户明确确认环境依赖例外。

## 任务记录约定

- [`agents/standard/任务记录约定.md`](agents/standard/任务记录约定.md)

## [immutable]

- 带有 `[immutable]` 或 `[immutable-file]` 标记的内容，默认视为高敏感内容。
- 不得修改带有 `[immutable]` 或 `[immutable-file]` 标记的内容。
- 带有 `[immutable-file]` 标记的文件整体不可修改。

## 编码约定

- 目录约定：`<待填写>`
- 风格约定：`<待填写>`
- 测试约定：`<待填写>`

### spec 文件规范

- [`agents/standard/spec文件规范.md`](agents/standard/spec文件规范.md)

### 审查规范

- [`agents/standard/审查规范.md`](agents/standard/审查规范.md)

## 合并规范

- [`agents/standard/合并规范.md`](agents/standard/合并规范.md)
