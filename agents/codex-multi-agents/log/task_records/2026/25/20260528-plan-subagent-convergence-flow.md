# 20260528-plan-subagent-convergence-flow

## 任务信息

- 任务：`plan-subagent-convergence-flow`
- 类型：`execute`
- worktree：`/home/lfr/kernelcode_generate/wt-20260528-plan-subagent-convergence-flow`
- 发起人：`大闸蟹`
- 用户确认来源：2026-05-28 用户消息“新计划书，修改计划书的流程，它不是 round 2论。而是一直讨论知道所有subganet 任务没有问题为止”，随后确认“round 轮数的更改，推进 execute 任务”。
- 计划书：`None`，本任务为流程标准文档窄范围修改。

## 任务目标

更新计划书流程标准，把“固定至少两轮 / Round 2 后可收口”的 active rule 改为“Codex subagent 严格审阅持续迭代，直到所有已发起或计划要求的 subagent 审阅任务都无阻断、无最小需改项、无待确认项，且记录完整后，才允许进入守护最终检验”。

## 模块范围

- `AGENTS.md`
- `agents/standard/计划书标准.md`
- `agents/standard/计划书模板.md`
- `agents/standard/计划书完成样板.md`
- `agents/standard/协作执行通用规则.md`
- `agents/standard/审查规范.md`
- `agents/standard/异常处理规范.md`
- `agents/standard/协作沟通原则.md`
- `agents/standard/测试文件约定.md`
- `agents/standard/规则索引.md`
- 如执行人发现同一 active rule 在其它 `agents/standard/*.md` 中残留，允许同步修改。

## 禁止修改面

- 不得修改、移动、新增或删除 `expectation/`。
- 不得修改 `.skills/`。
- 不得修改业务实现、测试、kernel demo 或生成物。
- 不得修改 `TODO.md` / `DONE.md`，任务状态只由标准脚本处理。

## 必须保持的流程边界

- `subagent` 严格审阅仍是计划书下发前硬门禁。
- `subagent` 不可用时仍不得降级或绕过。
- 用户待决策项仍必须先收口。
- `守护最好的爱莉希雅` 的守护最终检验仍是管理员下发计划前硬门禁。
- 普通计划意见仍不得替代守护最终检验。

## 建议验收

- 旧固定轮次口径负向扫描：
  - 不得在 active rule 中出现 `至少两轮`、`第二轮必须`、`两轮 subagent`、`Round 1 / Round 2`、`Round 2：subagent strict review` 等固定轮次下发条件。
  - 若样例或历史记录保留轮次编号，必须明确它只是示例，不是 active rule。
- 新收敛流程正向扫描：
  - 必须命中 `subagent 严格审阅收敛` 或等价表述。
  - 必须命中“所有已发起或计划要求的 subagent 审阅任务均无阻断、无最小需改项、无待确认项”或等价表述。
  - 模板必须包含 `收敛结论` 字段。
- `git diff --check`
- `git diff --name-only -- expectation .skills` 必须空。

## 进展记录

- 2026-05-28 大闸蟹：创建独立 worktree 与任务记录，待分发 execute。

## execute 记录

时间：2026-05-28 15:20
经办人：小李飞刀
任务：T-20260528-cfb6d8fa / plan-subagent-convergence-flow
任务目标：将计划书流程标准从固定两轮 / Round 2 下发条件，改为 `subagent` 严格审阅持续收敛，直到所有已发起或计划要求的 `subagent` 审阅任务均无阻断、无最小需改项、无待确认项后才进入守护最终检验。

### 执行前阅读记录

- 已读个人提示词：`agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`。
- 已读根规则：`AGENTS.md`。
- 已读标准：`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读任务记录：本文件当前管理员创建段。
- 计划书：无独立计划书，本任务为流程标准文档窄范围修改。
- 禁止修改面：`expectation/`、`.skills/`、业务实现、`test/kernel`、未授权共享状态文件；其中本任务明确授权修改根 `AGENTS.md` 与 `agents/standard/**`。

### 计划内小任务卡核对

- 旧固定轮次 active rule 清理：已将 `至少两轮` / `Round 2` 下发条件改为持续收敛。
- 新收敛流程落文：已写入 `AGENTS.md` 与相关 `agents/standard/**`。
- 模板收敛结论：`agents/standard/计划书模板.md` 与 `agents/standard/计划书完成样板.md` 已新增 `subagent 收敛结论`。
- 禁止修改面：未触碰 `expectation/`、`.skills/`、业务实现和 `test/kernel`。

### 改动摘要

- `AGENTS.md`：计划书下发前规则改为 `subagent` 严格审阅持续收敛；新增收敛结论与守护最终检验前置关系。
- `agents/standard/计划书标准.md`：取消固定轮次要求，明确所有已发起或计划要求的 `subagent` 审阅任务必须收敛到无阻断、无最小需改项、无待确认项。
- `agents/standard/计划书模板.md`：将迭代记录从固定 Round 1 / Round 2 改为收敛轮次 1 / N，并新增 `subagent 收敛结论`。
- `agents/standard/计划书完成样板.md`：同步样板中的收敛轮次、收敛结论和守护最终检验门禁。
- `agents/standard/协作执行通用规则.md`、`协作沟通原则.md`、`审查规范.md`、`异常处理规范.md`、`测试文件约定.md`、`规则索引.md`：同步 active rule、审查/异常/测试核对口径。

### 最小功能闭环

- 文档真源已覆盖根规则、计划书标准、模板、完成样板、审查/异常/沟通/测试/索引入口。
- 旧固定轮次下发条件已从 active rule 中移除。
- 新流程明确：持续审阅 -> 记录收敛结论 -> 用户待确认项收口 -> 守护最终检验 -> 管理员下发唯一计划级 execute。

### Diff 反推自测

- 实际改动文件：`AGENTS.md` 与 `agents/standard/**` 流程标准文档。
- 反推测试类型：文本残留扫描、正向语义扫描、模板字段扫描、格式检查、敏感目录空 diff。
- 旧固定轮次 active rule 负向扫描：
  - 命令：`rg -n '至少两轮|第二轮必须|两轮 subagent|两轮 \`subagent\`|Round 1 / Round 2|Round 2：subagent strict review|基于 Round 1' AGENTS.md agents/standard`
  - 结果：exit=1，无命中；`rg` exit=1 表示未找到匹配，符合预期。
- 旧轮次宽扫分类：
  - 命令：`rg -n '两轮|Round|第二轮|第 1 轮|第 2 轮' AGENTS.md agents/standard`
  - 结果：仅命中 `第二轮及以后返工` 这类审查返工轮次描述，非计划书 `subagent` 固定下发规则，允许保留。
- 新收敛流程正向扫描：
  - 命令：`rg -n '严格审阅持续收敛|收敛结论|无阻断、无最小需改项、无待确认项|所有已发起或计划要求|守护最终检验' AGENTS.md agents/standard/计划书标准.md agents/standard/计划书模板.md agents/standard/计划书完成样板.md agents/standard/协作执行通用规则.md agents/standard/协作沟通原则.md agents/standard/审查规范.md agents/standard/异常处理规范.md agents/standard/测试文件约定.md agents/standard/规则索引.md`
  - 结果：exit=0，命中 `AGENTS.md`、计划书标准、模板、完成样板、协作、审查、异常、测试和规则索引。
- 模板收敛结论扫描：
  - 命令：`rg -n 'subagent 收敛结论|收敛结论' agents/standard/计划书模板.md agents/standard/计划书完成样板.md`
  - 结果：exit=0，模板和完成样板均命中。
- 格式检查：
  - 命令：`git diff --check`
  - 结果：exit=0。
- 敏感目录空 diff：
  - 命令：`git diff --name-only -- expectation .skills && git diff --cached --name-only -- expectation .skills && git status --short --untracked-files=all -- expectation .skills`
  - 结果：exit=0，无输出。
- 业务实现 / kernel 禁止面：
  - 命令：`git diff --name-only -- kernel_gen kernel test/kernel`
  - 结果：exit=0，无输出。
- 未运行 pytest：本轮只修改流程标准文档，无 Python 实现、spec 行为或测试代码 diff；按 `agents/standard/测试文件约定.md`，本类任务以文本残留扫描、正向扫描、格式检查和敏感目录空 diff 为有效 diff 反推自测。

### 减法检查

- 新增 / 改动 private callable：无。
- 被替代旧逻辑：固定 `至少两轮` / `Round 2` 下发条件。
- 处理结果：替换为 `subagent` 严格审阅持续收敛和 `subagent 收敛结论` 门禁；未保留旧固定轮次 active rule。
- 保留旧描述：仅保留非计划书下发规则的“第二轮及以后返工”等审查记录语境。

### 自检

- 公开 API：未修改业务公开 API、脚本参数、工具入口或稳定错误语义。
- 边界：改动限定在授权的 `AGENTS.md` 与 `agents/standard/**`。
- 禁止修改面：`expectation/`、`.skills/`、业务实现、`test/kernel` 均为空 diff。
- 冗余与一致性：同步更新标准、模板、完成样板、审查、异常、沟通、测试和索引，避免固定轮次口径残留。
- 测试有效性：负向扫描锁定旧固定轮次 active rule 不再存在；正向扫描锁定新收敛流程和模板收敛结论存在。

### 结论

- execute 已完成，候选 diff 可进入 review。

### 流转记录

- 命令：`CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -next -task_id T-20260528-cfb6d8fa -from 小李飞刀 -type review ... -auto`
- 结果：exit=0。
- 输出摘要：
  - `OK: next T-20260528-cfb6d8fa`
  - `OK: auto-dispatch T-20260528-cfb6d8fa -> 不要啊教练`
  - `OK: talk 小李飞刀 -> 不要啊教练`
  - `OK: talk 小李飞刀 -> 神秘人`
- 结论：已按计划级流程从 execute 续接 review，并回报管理员。

## review 记录

时间：2026-05-28 22:52
经办人：不要啊教练
任务：T-20260528-cfb6d8fa / plan-subagent-convergence-flow
阶段：review
结论：通过，可按普通窄任务流程进入 merge；不得额外纳入 `expectation/`、`.skills/`、业务实现、`test/kernel`、`TODO.md` 或 `DONE.md`。

### 执行前阅读记录

- 已读个人提示词：`agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`。
- 已读根规则：`AGENTS.md`。
- 已读标准：`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/计划书标准.md`、`agents/standard/测试文件约定.md`。
- 已读任务记录：本文件 execute 记录与流转记录。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-plan-subagent-convergence-flow`。
- 同步命令：`git fetch origin --prune`。
- 当前分支：`wt-20260528-plan-subagent-convergence-flow`。
- `HEAD`：`45e800c198446c1be86779f95191bb2dd572d29a`。
- `origin/main`：`45e800c198446c1be86779f95191bb2dd572d29a`。
- `merge-base`：`45e800c198446c1be86779f95191bb2dd572d29a`。
- ahead / behind：`0 / 0`。
- 结果：待审 worktree 已在最新主线基线；无同步冲突、无覆盖风险。

### 审查范围

候选 diff：
- `AGENTS.md`
- `agents/standard/协作执行通用规则.md`
- `agents/standard/协作沟通原则.md`
- `agents/standard/审查规范.md`
- `agents/standard/异常处理规范.md`
- `agents/standard/测试文件约定.md`
- `agents/standard/规则索引.md`
- `agents/standard/计划书完成样板.md`
- `agents/standard/计划书标准.md`
- `agents/standard/计划书模板.md`
- 本任务记录：`agents/codex-multi-agents/log/task_records/2026/25/20260528-plan-subagent-convergence-flow.md`

禁止面核对：`expectation/`、`.skills/`、业务实现、`test/kernel`、`TODO.md`、`DONE.md` 不在候选 diff。

### 真实审查

- 固定两轮 / Round 2 下发条件：已从 active rule 删除。`AGENTS.md`、`计划书标准.md`、`协作执行通用规则.md`、`协作沟通原则.md` 不再要求“至少两轮”或“第二轮必须”作为计划下发门禁。
- 新流程：已落为 `subagent` 严格审阅持续收敛，要求所有已发起或计划要求的 `subagent` 审阅任务无阻断、无最小需改项、无待确认项后，才能进入守护最终检验。
- 模板与完成样板：`计划书模板.md` 使用 `收敛轮次 1` / `收敛轮次 N（按需重复）`，并新增 `subagent 收敛结论`；`计划书完成样板.md` 以两轮示例展示收敛过程，但下发判断落在 `subagent 收敛结论`，未把第二轮写成 active rule。
- 审查 / 异常 / 测试 / 索引入口：`审查规范.md`、`异常处理规范.md`、`测试文件约定.md`、`规则索引.md` 已同步新口径，审查时需核对收敛记录、标准包、收敛结论、用户待决策项和守护最终检验。
- 公开 API / 私有 API 边界：本轮只改流程标准文档，未新增业务公开 API、脚本参数、工具入口或稳定错误语义；未引入跨文件非公开 API、ctx 能力探测、object 签名或非装饰器嵌套函数。

### Diff 反推审查

- 实际 diff 类型：流程标准文档改动，无 Python 业务实现、spec 行为、测试代码或 kernel demo diff。
- 旧固定轮次 active rule 负向扫描：
  - 命令：`rg -n '至少两轮|第二轮必须|两轮 subagent|两轮 \`subagent\`|Round 1 / Round 2|Round 2：subagent strict review|基于 Round 1' AGENTS.md agents/standard || true`
  - 结果：无命中。
- 旧轮次宽扫分类：
  - 命令：`rg -n '两轮|Round|第二轮|第 1 轮|第 2 轮' AGENTS.md agents/standard || true`
  - 结果：仅命中“第二轮及以后返工”这类任务返工记录语境，不属于计划书下发 active rule。
- 新流程正向扫描：
  - 命令：`rg -n '严格审阅持续收敛|收敛结论|无阻断、无最小需改项、无待确认项|所有已发起或计划要求|守护最终检验' AGENTS.md agents/standard`
  - 结果：命中 `AGENTS.md`、计划书标准、计划书模板、计划书完成样板、协作执行、协作沟通、审查、异常、测试和规则索引。
- 模板收敛字段核对：
  - 命令：自写 Python 扫描 `AGENTS.md`、`计划书标准.md`、`计划书模板.md`、`计划书完成样板.md`、`审查规范.md`、`测试文件约定.md` 的关键字段。
  - 结果：`positive scan ok`。
- 旧 active 固定轮次精确扫描：
  - 命令：自写 Python 扫描 `至少两轮 Codex`、`第二轮必须`、`Round 1 / Round 2`、`基于第一轮修订后的计划文本` 等旧口径。
  - 结果：`old active fixed-round scan ok`。
- 格式检查：
  - 命令：`git diff --check`
  - 结果：通过，输出 `diff-check ok`。
- 敏感目录空 diff：
  - 命令：`git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills`、`git status --short --untracked-files=all -- expectation .skills`
  - 结果：无输出。
- 业务实现 / test/kernel 禁止面：
  - 命令：`git diff --name-only -- kernel_gen kernel test/kernel test spec expectation .skills`
  - 结果：无输出。
- 状态文件禁止面：
  - 命令：`git diff --name-only -- TODO.md DONE.md`、`git diff --cached --name-only -- TODO.md DONE.md`、`git status --short --untracked-files=all -- TODO.md DONE.md`
  - 结果：无输出。
- 私有 API / ctx / object / 嵌套函数静态面：
  - 命令：`git diff -U0 -- AGENTS.md agents/standard | rg -n 'hasattr\(|getattr\(|callable\(|object\)|object,|def .*\(|class ' || true`
  - 结果：无命中。

### 减法审查

- 被删除旧口径：固定 `至少两轮` / `Round 2` 作为计划下发条件。
- 替代新口径：持续收敛，直到所有已发起或计划要求的 `subagent` 审阅任务均无阻断、无最小需改项、无待确认项；再由守护最终检验把关。
- 未恢复项：未恢复 `Round 2` 下发条件；未绕过 `subagent` 不可用不得降级规则；未弱化用户待决策项收口和守护最终检验。

### 自检

- 特殊情况：完成样板中的 `收敛轮次 2` 是示例轮次，且同段已用 `subagent 收敛结论` 作判断；不构成固定两轮 active rule。
- 完整性：根规则、计划书标准、模板、完成样板、审查、异常、沟通、测试和索引均已同步。
- 维护性：新规则把判断点从轮次编号转为状态收敛，后续审查可机械核对“无阻断、无最小需改项、无待确认项”。
- 测试有效性：本轮文档 diff 用负向扫描、正向扫描、格式检查和禁止面扫描覆盖；无 Python/pytest 对应改动。

### 结论与流转建议

- 结论：review 通过。
- 流转：本任务是普通窄范围流程标准文档任务，按管理员最新口径通过后进入 `merge`，不进入 `archive_acceptance`。
- merge 前必须同批纳入上述候选标准文档和本任务记录；不得额外纳入 `expectation/`、`.skills/`、业务实现、`test/kernel`、`TODO.md`、`DONE.md` 或其它并行改动。

## merge 记录

时间：2026-05-28 22:59 CST
经办人：李白
任务：T-20260528-cfb6d8fa / plan-subagent-convergence-flow
任务目标：合入 review 已通过的计划书 subagent 收敛流程标准文档候选 diff 与同批任务记录，排除 `expectation/.skills/TODO.md/DONE.md`、业务实现、`test/kernel` 和其它并行改动。

### 合并前同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-plan-subagent-convergence-flow`。
- `git fetch --prune origin`：exit=0。
- `HEAD=45e800c198446c1be86779f95191bb2dd572d29a`。
- `origin/main=45e800c198446c1be86779f95191bb2dd572d29a`。
- `merge-base=45e800c198446c1be86779f95191bb2dd572d29a`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：任务 worktree 已对齐 latest `origin/main`，无冲突或覆盖风险。

### 实际合入范围

- `AGENTS.md`
- `agents/standard/协作执行通用规则.md`
- `agents/standard/协作沟通原则.md`
- `agents/standard/审查规范.md`
- `agents/standard/异常处理规范.md`
- `agents/standard/测试文件约定.md`
- `agents/standard/规则索引.md`
- `agents/standard/计划书完成样板.md`
- `agents/standard/计划书标准.md`
- `agents/standard/计划书模板.md`
- `agents/codex-multi-agents/log/task_records/2026/25/20260528-plan-subagent-convergence-flow.md`

### 合并前复核

- 旧固定轮次负向扫描：`rg -n '至少两轮|第二轮必须|两轮 subagent|两轮 \`subagent\`|Round 1 / Round 2|Round 2：subagent strict review|基于 Round 1' AGENTS.md agents/standard || true` 无输出；未发现固定两轮 / Round 2 作为 active 下发条件残留。
- 新收敛流程正向扫描：`rg -n '严格审阅持续收敛|收敛结论|无阻断、无最小需改项、无待确认项|所有已发起或计划要求|守护最终检验' AGENTS.md agents/standard` 命中根规则、计划书标准、计划书模板、完成样板、协作执行、协作沟通、审查、异常、测试和规则索引。
- 敏感目录与禁止面：`git diff --name-only -- expectation .skills TODO.md DONE.md kernel_gen kernel test/kernel test spec` 无输出；`git status --short --untracked-files=all -- expectation .skills TODO.md DONE.md kernel_gen kernel test/kernel test spec` 无输出。
- 任务记录：本 merge 记录已写入当前任务记录，准备与 `AGENTS.md` 和 `agents/standard/**` 同批提交。

### 验证

- `git diff --check`：exit=0，无输出。
- `git diff --name-only -- expectation .skills TODO.md DONE.md kernel_gen kernel test/kernel test spec`：exit=0，无输出。
- `git status --short --untracked-files=all -- expectation .skills TODO.md DONE.md kernel_gen kernel test/kernel test spec`：exit=0，无输出。
- 未运行 pytest：本任务只修改流程标准文档，不涉及 Python 实现、业务 `spec` 行为、业务测试或 kernel demo；已按记录与审查口径使用文本负向 / 正向扫描、格式检查和禁止面扫描覆盖本次 diff。

### 冲突与剩余风险

- 冲突处理：无需冲突处理。
- 剩余风险：主仓存在 T-20260528-8b55edd9 相关 kernel demo/test 并行改动；本次合并在任务 worktree 内只提交指定标准文档与任务记录，不纳入该并行改动。

### 结论

- 合并前核对通过，可将上述候选文件与任务记录同批提交并 push 到 `origin/main`；提交后执行 `-done` 并清理已完成 worktree / branch。
