# 20260404-agent-prompt-constraints

- 时间：`2026-04-04 21:43:41 +0800`
- 经办人：`不要啊教练`
- 任务：`T-20260404-a337dd1b`
- 任务目标：
  - 复审全员 prompt 约束补强是否仅修改 `agents/codex-multi-agents/agents/*/*.prompt.md`，并确保新增“不得阅读无关文件/目录 + 不得做职责之外工作”的表述与角色职责一致。
- 改动：
  - 追加复审结论；未修改实现/测试。
- 结论：
  - `git diff` 仅包含 `agents/codex-multi-agents/agents/*/*.prompt.md`，未触碰 `.skills/.agents`、`skills/`、`TODO.md/DONE.md/AGENTS.md`。
  - 所有角色均新增“不得阅读与当前任务无关文件/目录（额外阅读需先 -talk 说明原因+文件清单并获确认）”与“不得做职责之外工作”的约束，且与各自职责边界一致。
  - 未引入额外流程负担，仅增强边界约束；本次无需测试。
  - 漏洞与风险：提示词文本变更不涉及代码路径与输入处理，未发现安全风险。
