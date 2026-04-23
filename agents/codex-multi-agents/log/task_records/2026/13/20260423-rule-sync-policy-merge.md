# T-20260423-fc671dee / 规则同步 merge

## 任务信息
- 任务状态: `merge`
- worktree: [`wt-20260423-rule-sync-policy-merge`](/home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge)
- 计划书: [`ARCHITECTURE/plan/python_quality_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/python_quality_refactor_green_plan.md)

## 执行前阅读记录
- 已读 [`TODO.md`](../../../../../../../TODO.md) 中 `T-20260423-fc671dee` 任务行，确认本轮工作树与任务目标。
- 已读本次规则同步相关文件：
  - [`agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`](../../../../../../agents/不要啊教练/不要啊教练.prompt.md)
  - [`agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md`](../../../../../../agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md)
  - [`agents/codex-multi-agents/agents/大闸蟹/大闸蟹.prompt.md`](../../../../../../agents/大闸蟹/大闸蟹.prompt.md)
  - [`agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md`](../../../../../../agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md)
  - [`agents/codex-multi-agents/agents/jcc你莫辜负/jcc你莫辜负.prompt.md`](../../../../../../agents/jcc你莫辜负/jcc你莫辜负.prompt.md)
  - [`agents/standard/审查规范.md`](../../../../../../agents/standard/审查规范.md)
  - [`agents/standard/计划书标准.md`](../../../../../../agents/standard/计划书标准.md)
- 已核对当前 worktree 内前序记录与任务列表，确认这次是规则同步文档收口，没有混入其他阶段内容。

## 真实自检
- 逐条核对新增规则，确认审查与终验口径已经从“只要还有改进项就不给通过”进一步收紧为“只要还能明确指出一线可改进点，就必须写成 `需修改`”。
- 核对 `agents/standard/审查规范.md` 与 `agents/standard/计划书标准.md` 的新增句子，确认它们与各角色 prompt 的同步表述一致，没有引入新的角色边界或实现范围。
- 核对本次改动仅限规则文本与标准文档，不包含实现、测试或合同资产文件。
- 核对输出描述、任务边界和验收语义，确认本次同步只是在原有审查从严口径上做一致化，不改变已有任务分工。

## Diff 反推自测
- `grep -n "审查口径从严" /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge/agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge/agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge/agents/codex-multi-agents/agents/大闸蟹/大闸蟹.prompt.md /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge/agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge/agents/codex-multi-agents/agents/jcc你莫辜负/jcc你莫辜负.prompt.md`
- `grep -n "严格改进门槛" /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge/agents/standard/审查规范.md /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge/agents/standard/计划书标准.md`
- `grep -n "终验、复验或终验修复复核一律从严" /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge/agents/standard/计划书标准.md`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-rule-sync-policy-merge diff --check`
- 结果：
  - 上述新增规则均已命中，说明相关 prompt 与标准文档已同步写入。
  - 计划书标准新增句子也已命中，说明终验 / 复验口径与审查口径保持一致。
  - `git diff --check` 无格式问题。

## 结论
- 规则同步内容已写入本轮 worktree，当前仅剩提交并合并到主线。

## merge
- 时间：2026-04-23 22:18 +0800
- 经办人：李白
- 任务：T-20260423-fc671dee
- 任务目标：把本次规则同步更新并入主线，保证 review 与终验从严口径在相关 prompt 与标准文档里一致生效。

### 本次收口范围
- [`agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`](../../../../../../agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md)
- [`agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md`](../../../../../../agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md)
- [`agents/codex-multi-agents/agents/大闸蟹/大闸蟹.prompt.md`](../../../../../../agents/codex-multi-agents/agents/大闸蟹/大闸蟹.prompt.md)
- [`agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md`](../../../../../../agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md)
- [`agents/codex-multi-agents/agents/jcc你莫辜负/jcc你莫辜负.prompt.md`](../../../../../../agents/codex-multi-agents/agents/jcc你莫辜负/jcc你莫辜负.prompt.md)
- [`agents/standard/审查规范.md`](../../../../../../agents/standard/审查规范.md)
- [`agents/standard/计划书标准.md`](../../../../../../agents/standard/计划书标准.md)

### 结果
- 以上规则同步已收口到当前 worktree，后续合并后会一并推送主线。
- 本轮未引入实现、测试或 `expectation` 改动，`expectation` 仍只作为合同验收资产单列。

### 结论
- 通过
