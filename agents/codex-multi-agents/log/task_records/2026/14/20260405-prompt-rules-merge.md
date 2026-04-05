时间：2026-04-05 22:17:00 +0800
经办人：李白
任务：T-20260405-b5443a5c（合并收口）
任务目标：合并提示词与标准规则变更；不触碰 .agents/.skills，且不含 ARCHITECTURE/plan。

范围核对：
- `git diff --name-only` 覆盖：
  - `agents/codex-multi-agents/agents/*/*.prompt.md`
  - `agents/standard/任务记录约定.md`
- `git ls-files --others --exclude-standard` 新增：
  - `agents/standard/agents目录规则.md`
  - `agents/standard/expectation任务规则.md`
  - `agents/standard/任务新建模板.md`

测试：
- 无（规则/提示词变更）。

结论：范围符合，可合并收口。
