# multi_buffer_apply_fixed_reserved_before_auto

## 文档信息
- 目标 `spec`：[`spec/pass/memory/multi_buffer.md`](../../spec/pass/memory/multi_buffer.md)
- 目标 `API`：
  - `class MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`
  - `MultiBufferApplyPass.from_options(options: dict[str, str]) -> MultiBufferApplyPass`
  - `MultiBufferApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
  - `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`
  - `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`
- 目标 `test`：
  - [`test/passes/memory/test_multi_buffer.py`](../../test/passes/memory/test_multi_buffer.py)
  - [`test/passes/pipeline/test_npu_demo_lowering.py`](../../test/passes/pipeline/test_npu_demo_lowering.py)
- 目标 `验收资产`：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/pipeline/test_npu_demo_lowering.py`
- 目标 `功能实现`：[`kernel_gen/passes/memory/multi_buffer.py`](../../kernel_gen/passes/memory/multi_buffer.py)

## 计划级任务
- 计划任务名：`multi-buffer-apply-fixed-reserved-before-auto`
- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`。
- 当前状态：Draft 3，已按用户要求补充“执行规则：fixed-reserved before auto”，已完成 Draft 3 Round 5 subagent strict review 收敛，并已取得 `守护最好的爱莉希雅` 本人守护最终检验通过回执；等待用户最终确认下发。
- 下发限制：当前不得通知管理员创建 execute；必须等用户最终确认下发后，才允许请求管理员创建唯一计划级 execute。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `multi-buffer-apply-fixed-reserved-before-auto` | `execute` | 由管理员创建 | `agents/codex-multi-agents/log/task_records/2026/24/20260614-multi-buffer-apply-fixed-reserved-before-auto.md` |

## 迭代审阅记录

### 用户决策记录
- 决策时间：2026-06-14。
- 用户问题：`25-multi-buffer-apply.mlir` 中 mixed fixed/auto 变换需要按 alloc 上的编辑决定，3 个 memory 是 fixed `2`，随后 auto 才基于剩余容量推导。
- 架构决策包：
  - C1=A：只收口 `expectation/pass/multi_buffer/apply` 相关 expectation，不扩大到 analysis/facade 全量迁移。
  - C2=A：新增静态数字口径 leaf，复刻 3 个 fixed `num="2"` 后 auto 应为 `79` 的场景。
  - C3=A：计划目标写成“补合同 + 必要时修实现”；不预设必须改实现。
- 用户确认：用户回复“是的”，确认采用 C1=A / C2=A / C3=A。

### Pre-Review local-only expectation 物化记录
- 授权来源：用户确认上述 C1/C2/C3 后，授权架构师先更新 expectation。
- 授权 scope：仅 `expectation/pass/multi_buffer/apply/` 下 apply leaf 与聚合入口；不修改 `analysis/`、`facade/`，不进入 staged diff，不作为远程提交候选。
- 物化目标：
  - 将 apply 旧字段 `multi_buffer.update_point/use_point` 迁到当前公开合同 `multi_buffer.update_points/use_points`。
  - 新增 `expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`，锁定同一 TSM scope 内 3 个 fixed `num="2"` 先占容量，2 个 auto candidate 共享 `auto_num=79`。
- manifest：
  - `expectation/pass/multi_buffer/apply/__main__.py` sha256=`b3fe8c14b1f71ab4aa40fa40f05db8e518e02ac2e392c1bcb06ba66bd0fca32d`
  - `expectation/pass/multi_buffer/apply/fixed_memory_stage.py` sha256=`27a67b744563b6b12755319081f0239ea0f56289e3cf79a73a43b409a2e5abc6`
  - `expectation/pass/multi_buffer/apply/dynamic_target_auto.py` sha256=`9611bbf9939305c434479a2fbf4066b9ce5c768b2a627893d260e809bb39c42b`
  - `expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py` sha256=`5b125ff0d6b706b4e8414c01acd5f47be97565fcabed0e39edcaca18af38b0af`
  - `expectation/pass/multi_buffer/apply/direct_use_boundary.py` sha256=`a6f314d3042eeb2393d07ceab76c49bf17eae31b7ec29b9cdaeed7077ecc2ec4`
  - `expectation/pass/multi_buffer/apply/existing_current_noop.py` sha256=`d157ccc835028da2aa7bd68f846965558c6d4a292bb9e452f4a447cc0dcdd66d`
- local-only 证据：
  - `git check-ignore -v` 对上述 6 个文件均命中 `.gitignore:21:expectation`。
  - `git ls-files --stage -- expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 无输出。
  - `git diff --name-status -- expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 无输出。
  - `git diff --cached --name-status -- expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 无输出。
  - `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 显示 apply manifest、analysis/facade 既有 local-only 文件和 apply `__pycache__` 均为 `!!` ignored local-only。
  - 分类口径：上述 6 个 apply `.py` 文件是本计划当前合同 manifest；`expectation/pass/multi_buffer/apply/__pycache__/*` 是 py_compile / 运行生成的 ignored cache，非合同资产，不进入 manifest；`expectation/pass/multi_buffer/analysis/**` 与 `expectation/pass/multi_buffer/facade/**` 是既有 ignored local-only 资产，非本计划授权 scope，execute/review/archive_acceptance/merge 不得修改、运行为必过或纳入提交。
- 已运行合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/pass/multi_buffer/apply/__main__.py expectation/pass/multi_buffer/apply/fixed_memory_stage.py expectation/pass/multi_buffer/apply/dynamic_target_auto.py expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py expectation/pass/multi_buffer/apply/direct_use_boundary.py expectation/pass/multi_buffer/apply/existing_current_noop.py` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k "target or if_path"` 通过：5 passed, 20 deselected。

### 收敛轮次 1：subagent strict review
- 审阅对象：
  - Round 1-A：Faraday / agent_id=`019ec1c4-2d26-7940-9158-7f45c442c414`
  - Round 1-B：Gauss / agent_id=`019ec1c4-7ed9-75a3-a3c2-c3c101cbdf91`
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、staged 计划全文、用户 C1/C2/C3 确认、local-only expectation manifest、禁止修改面和必过验收命令。
- 严格通过口径：仍有可执行改进项则不通过；不得放行 expectation 权限不清、API 变化未确认、任务卡不可执行、验收不闭合或 mixed fixed/auto 行为未被锁定。
- 发现问题：
  - Round 1-A 结论=不通过。阻断项：缺少必备 `计划书入档验收 / 复验 / 修复复核记录` 章节；S4 expectation 与敏感范围核对缺 staged / ignored / untracked 检查；“无待确认项”与“仍需用户下发确认”表述混杂。
  - Round 1-B 结论=不通过。阻断项：`archive_acceptance` 不可判定；expectation 权限证据不闭合，尤其缺 `git diff --cached --name-status` 与 `git status --short --ignored --untracked-files=all`；当前 ignored `analysis/facade` 与 `apply/__pycache__` 状态缺分类。
- 主线处理：
  - 采纳 Round 1-A/B 阻断项，Draft 1 增补 archive_acceptance 占位章节。
  - 采纳 staged / ignored / untracked 检查要求，S4 增补 `git diff --cached --name-status` 与 `git status --short --ignored --untracked-files=all`。
  - 采纳 ignored 状态分类要求，明确 apply manifest 是当前合同，`__pycache__` 是非合同 cache，analysis/facade 是既有 local-only 非目标资产。
  - 收口待确认表述：当前无方案待用户确认项；管理员下发不是当前方案待确认项，须等 subagent 收敛和守护终验通过后再按流程请求。
- 状态：不通过，已按最小需改项修订为 Draft 1，需进入 Round 2 strict review。

### 收敛轮次 2：subagent strict review
- 审阅对象：待发起。
- 输入标准包：基于 Draft 1 最新 staged 计划全文、Round 1-A/B 问题与本轮收口摘要、根 `AGENTS.md`、当前角色 prompt、相关 `agents/standard/**`、用户 C1/C2/C3 确认、expectation manifest、禁止修改面和必过验收命令。
- 严格通过口径：确认 Round 1 阻断项已闭合；仍有可执行改进项则不通过；不得放行 archive_acceptance 不可判定、expectation 权限不清或用户场景未锁定。
- 发现问题：
  - Round 2-A / Faraday 结论=不通过。Round 1 阻断已基本闭合，但 S1/S2/S3 小任务卡未在各自验收字段单列当前必过 expectation 合同验收；标准要求每张小任务卡的验收字段中单列当前必过 expectation。
  - Round 2-B / Gauss 结论=通过，无阻断、无最小需改项、无新增待用户确认项。确认 archive_acceptance、expectation 权限、用户场景、公开 API 与只读权限均清楚。
- 主线处理：
  - 采纳 Round 2-A 阻断项，Draft 2 在 S1/S2/S3 的 `验收必过项目` 中单列当前必过 expectation 合同验收，并注明 expectation 是合同验收，不计入 diff 反推测试。
  - 保留 Round 2-B 通过证据；本轮因 Round 2-A 未通过，整体不能进入守护最终检验。
- 状态：不通过，已按最小需改项修订为 Draft 2，需进入 Round 3 strict review。

### 收敛轮次 3：subagent strict review
- 审阅对象：
  - Round 3-A：Faraday / agent_id=`019ec1c4-2d26-7940-9158-7f45c442c414`
  - Round 3-B：Gauss / agent_id=`019ec1c4-7ed9-75a3-a3c2-c3c101cbdf91`
- 输入标准包：基于 Draft 2 最新 staged 计划全文、Round 1/2 问题与本轮收口摘要、根 `AGENTS.md`、当前角色 prompt、相关 `agents/standard/**`、用户 C1/C2/C3 确认、expectation manifest、禁止修改面和必过验收命令。
- 严格通过口径：确认 S1/S2/S3/S4 均单列当前必过 expectation 合同验收；仍有可执行改进项则不通过；不得放行 archive_acceptance 不可判定、expectation 权限不清或用户场景未锁定。
- 发现问题：
  - Round 3-A 结论=通过，无阻断、无最小需改项、无待用户确认项。确认 S1/S2/S3 已在 `验收必过项目` 单列当前必过 expectation，且 expectation 不计入 diff 反推测试、不授权修改 expectation。
  - Round 3-B 结论=通过，无阻断、无最小需改项、无待用户确认项。确认 archive_acceptance、cached/status 检查、分类口径、公开 API 不变、用户场景和只读权限均清楚。
- 主线处理：
  - 采纳 Round 3 通过结论，Draft 2 已满足计划书标准和 expectation 规则的闭合要求。
  - 准备请求 `守护最好的爱莉希雅` 做守护最终检验；在守护通过前仍不通知管理员下发。
- 状态：已收口，可进入守护最终检验。

### 收敛轮次 4：Draft 3 执行规则补写 strict review
- 触发原因：用户指出执行人不一定知道 fixed-reserved before auto 的详细规则，要求把规则写清楚。
- Draft 3 变更摘要：新增 `执行规则：fixed-reserved before auto` 章节，展开 fixed/auto 分类、scope 隔离、slot/alignment 字节公式、fixed reserved、auto group、`79` vs `81` 静态推导、实现顺序和测试正反断言。
- 审阅对象：
  - Round 4-A：Faraday / agent_id=`019ec1c4-2d26-7940-9158-7f45c442c414`
  - Round 4-B：Gauss / agent_id=`019ec1c4-7ed9-75a3-a3c2-c3c101cbdf91`
- 输入标准包：基于 Draft 3 最新 staged 计划全文、Draft 3 新增规则 diff、根 `AGENTS.md`、当前角色 prompt、相关 `agents/standard/**`、用户 C1/C2/C3 确认、local-only expectation manifest、禁止修改面和必过验收命令。
- 严格通过口径：确认新增规则足够指导 execute，且未扩大方案、公开 API、expectation 授权、manifest、S1-S4 任务卡或验收命令；仍有可执行改进项则不通过。
- 发现问题：
  - Round 4-A / Faraday 结论=不通过。规则内容本身清楚，未发现 fixed/auto 分类、scope、byte math、`group_unit`、same-scope no-op、`alignment=0`、动态场景或 `79 vs 81` 推导错误，也未看到它改变公开 API、expectation manifest、S1-S4 或验收命令；阻断项是流程记录仍写 Draft 2、守护证据绑定旧 blob/sha、下发门禁容易让 Draft 3 在未重新收敛/守护时被误认为只差用户确认。
  - Round 4-B / Gauss 结论=通过。确认新增规则覆盖 fixed/auto 分类、三元 scope、fixed reserved、`group_unit=sum(aligned_slot_bytes(auto group))`、no-op、`alignment=0`、动态不引入 `symbol.get_dim`、以及 `79` vs `81` 推导；未改变公开 API、expectation manifest、S1-S4 任务卡或验收命令。
- 主线处理：
  - 采纳 Round 4-A 最小需改项，Draft 3 当前状态改为“尚未完成 subagent 收敛与守护最终检验”。
  - 将 Draft 2 守护通过记录保留为历史证据，不再作为 Draft 3 当前可下发依据。
  - 下发门禁改为必须等待 Draft 3 subagent 收敛、当前 Draft 3 守护通过和用户最终确认。
- 状态：不通过，已按最小需改项修订；需进入下一轮 strict review。

### 收敛轮次 5：Draft 3 流程记录收口 strict review
- 审阅对象：
  - Round 5-A：Faraday / agent_id=`019ec1c4-2d26-7940-9158-7f45c442c414`
  - Round 5-B：Gauss / agent_id=`019ec1c4-7ed9-75a3-a3c2-c3c101cbdf91`
- 输入标准包：基于 Draft 3 最新 staged 计划全文、Round 4-A/B 问题与本轮收口摘要、根 `AGENTS.md`、当前角色 prompt、相关 `agents/standard/**`、用户 C1/C2/C3 确认、expectation manifest、禁止修改面和必过验收命令。
- 严格通过口径：确认 Round 4-A 流程记录阻断已闭合，新增执行规则仍清楚且未改变方案边界；仍有可执行改进项则不通过。
- 发现问题：
  - Round 5-A / Faraday 结论=通过，无阻断、无最小需改项、无新增方案待用户确认项。确认 Round 4-A 流程阻断已闭合；当前状态已为 Draft 3 且尚未完成收敛/守护，Draft 2 守护仅保留为历史，下发门禁已改为 Draft 3 收敛、守护通过、用户最终确认。
  - Round 5-B / Gauss 结论=通过，无阻断、无最小需改项、无新增方案待用户确认项。确认新增执行规则对 fixed/auto 分类、scope、byte math、fixed reserved、auto group、`79` vs `81` 推导、`alignment=0`、动态场景不引入 `symbol.get_dim` 的约束清楚，未扩大范围或改变公开 API、expectation 授权、manifest、S1-S4 或验收命令。
- 主线处理：
  - 采纳 Round 5-A/B 通过结论，Draft 3 已满足进入守护最终检验条件。
- 状态：已收口，可进入 Draft 3 守护最终检验。

### subagent 收敛结论
- 已发起或计划要求的审阅任务：
  - Round 1-A：Faraday / 不通过
  - Round 1-B：Gauss / 不通过
  - Round 2-A：Faraday / 不通过
  - Round 2-B：Gauss / 通过
  - Round 3-A：Faraday / 通过
  - Round 3-B：Gauss / 通过
  - Round 4-A：Faraday / 不通过
  - Round 4-B：Gauss / 通过
  - Round 5-A：Faraday / 通过
  - Round 5-B：Gauss / 通过
- 当前收敛结论：Draft 3 无阻断、无最小需改项、无新增方案待用户确认项；可进入守护最终检验。
- 遗留项：无新增方案待用户确认项；Draft 3 守护最终检验已通过，尚需用户最终确认下发流程。

### 守护最终检验
- 检验对象：`守护最好的爱莉希雅`
- 检验范围：标准包、公开 API、expectation 权限、禁止修改面、验收命令和 S1-S4 小任务卡。
- Draft 3 当前结论：通过。
- Draft 3 回执来源：用户转发的 `守护最好的爱莉希雅` 本人回执，回执对象为 `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md Draft 3`。
- Draft 3 阻断项：无。
- Draft 3 最小需改项：无。
- Draft 3 是否需要用户确认：不需要新的方案口径确认；C1=A / C2=A / C3=A 已收口。但按用户“我确认后下发”口径，仍需用户最终确认下发后才可通知管理员。
- Draft 3 关键证据摘要：
  - staged blob：`100644 ceeb06fc35290833252b2693a619d085ed42c6a6 0`
  - staged sha256：`fee9b77ce658c9c444485c177f5af604c3c60654b956c53e5076f069d4401e48`
  - 本计划自身 cached name-status：`A ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`
  - `git diff --cached --check -- ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md` 无输出。
  - 当前全量 cached diff 另有 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md` 与 `ARCHITECTURE/plan/symbol_loop_hoist_if_branch_no_hoist.md` 两份独立 staged 计划；它们不属于本计划候选，不纳入本计划 execute / review / 守护 / merge 证据，不混用。
  - Draft 3 新增 `执行规则：fixed-reserved before auto` 覆盖 fixed/auto 分类、同 insertion scope / target loop / memory space 隔离、slot/alignment 字节公式、fixed reserved、same_scope_reserved no-op、auto group、`79` vs `81` 推导、实现顺序和测试正反断言；该规则未改变公开 API、expectation 授权、manifest、S1-S4 任务卡或验收命令。
  - Round 4-A Faraday 流程记录阻断已闭合；Round 5-A Faraday 与 Round 5-B Gauss 均通过，均无阻断、无最小需改项、无新增方案待确认项。
  - apply 6 个 local-only expectation hash 与 manifest 一致，均为 ignored local-only；`git check-ignore` 命中 `.gitignore:21:expectation`；`git ls-files --stage -- expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 无输出。
  - `expectation/pass/multi_buffer/analysis` 与 `facade` 仍按计划归类为非目标既有 ignored local-only，apply `__pycache__` 为非合同 cache。
  - 敏感范围 `expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` 的 cached / unstaged diff 均为空。
  - 守护只读运行并通过 `python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`、`python3 -m expectation.pass.multi_buffer.apply` 和 `py_compile` 6 个 apply leaf。
- Draft 3 允许事项：允许在用户最终确认下发后通知管理员创建唯一计划级 execute `multi-buffer-apply-fixed-reserved-before-auto`；管理员不得创建第二个 execute。创建后必须先保持未分发或暂停状态，待架构师在目标 worktree 按计划 manifest 完成 local-only expectation 物化、hash/status/check-ignore/ls-files/scope diff/合同验收记录后，管理员才可分发或恢复 execute。
- Draft 2 历史结论：通过。
- Draft 2 回执来源：`agents/codex-multi-agents/log/talk.log:13380`，`守护最好的爱莉希雅` 本人回执。
- Draft 2 阻断项：无。
- Draft 2 最小需改项：无。
- Draft 2 是否需要用户确认：不需要新的方案口径确认；C1=A / C2=A / C3=A 均已收口。按用户要求，仍需用户最终确认后才下发。
- Draft 2 关键证据摘要：
  - staged blob：`100644 b6106b45fd8a801a6394ba3ce8e4eb4746142a62 0`
  - staged sha256：`a28542df3f139a6b848b62825efdcdd1e08afb4cf59dc668e0d02594a8d313b3`
  - 本计划自身 cached name-status：`A ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`
  - 当前 index 另有 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md` 与 `ARCHITECTURE/plan/symbol_loop_hoist_if_branch_no_hoist.md` 两份独立 staged 计划；守护已确认它们不属于本计划候选、不纳入本计划证据、不混用。
  - apply 6 个 local-only expectation manifest hash 与计划一致，均为 ignored local-only；`git ls-files --stage -- expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade` 无输出；expectation 相关 cached/unstaged diff 为空。
  - 守护只读运行并通过 `py_compile` 6 个 apply leaf、`python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto` 和 `python3 -m expectation.pass.multi_buffer.apply`。
- Draft 2 允许事项：历史有效；当前以下发限制和 Draft 3 允许事项为准。当前不得通知管理员创建 execute，直到用户最终确认下发。

## 计划书入档验收 / 复验 / 修复复核记录
- 当前状态：已完成 `archive_acceptance`，结论通过；等待 `merge/归档` 按合并规范同批合入计划书、任务记录、spec 与测试。
- 结论人：提莫炖蘑菇。
- 结论：通过；无最小阻断项、无新增待用户确认项。
- 验证基线：目标 worktree `/home/lfr/kernelcode_generate/wt-20260614-multi-buffer-apply-fixed-reserved-before-auto`，分支 `task/multi-buffer-apply-fixed-reserved-before-auto`；`HEAD = 031a1462c2095df98636b4605d38bd09b5f49c97`，`origin/main = 031a1462c2095df98636b4605d38bd09b5f49c97`，`merge-base = 031a1462c2095df98636b4605d38bd09b5f49c97`，ahead/behind = `0 0`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260614-multi-buffer-apply-fixed-reserved-before-auto`。
- 同步结果：`git fetch origin main --prune && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main` 通过；未发现冲突或覆盖风险。
- 合入候选：`ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`、`agents/codex-multi-agents/log/task_records/2026/24/20260614-multi-buffer-apply-fixed-reserved-before-auto.md`、`spec/pass/memory/multi_buffer.md`、`test/passes/memory/test_multi_buffer.py`。
- 合同验收摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`：exit=0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`：exit=0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k test_multi_buffer_apply_fixed_reserved_before_auto_static_num`：exit=0，`1 passed, 25 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`37 passed, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：exit=0，`8 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile test/passes/memory/test_multi_buffer.py kernel_gen/passes/memory/multi_buffer.py`：exit=0。
  - `git diff --check && git diff --cached --check`：exit=0。
- expectation 权限核对摘要：
  - `expectation/pass/multi_buffer/_path.py` sha256=`767b46f69b62b522e3ba1cdd2983f430ec6d08cd51cd74e25b6f54d86e5367f7`；该文件仅为 local-only 导入支撑。
  - `expectation/pass/multi_buffer/apply/__main__.py` sha256=`b3fe8c14b1f71ab4aa40fa40f05db8e518e02ac2e392c1bcb06ba66bd0fca32d`
  - `expectation/pass/multi_buffer/apply/fixed_memory_stage.py` sha256=`27a67b744563b6b12755319081f0239ea0f56289e3cf79a73a43b409a2e5abc6`
  - `expectation/pass/multi_buffer/apply/dynamic_target_auto.py` sha256=`9611bbf9939305c434479a2fbf4066b9ce5c768b2a627893d260e809bb39c42b`
  - `expectation/pass/multi_buffer/apply/fixed_reserved_before_auto.py` sha256=`5b125ff0d6b706b4e8414c01acd5f47be97565fcabed0e39edcaca18af38b0af`
  - `expectation/pass/multi_buffer/apply/direct_use_boundary.py` sha256=`a6f314d3042eeb2393d07ceab76c49bf17eae31b7ec29b9cdaeed7077ecc2ec4`
  - `expectation/pass/multi_buffer/apply/existing_current_noop.py` sha256=`d157ccc835028da2aa7bd68f846965558c6d4a292bb9e452f4a447cc0dcdd66d`
  - `git check-ignore -v` 对上述 7 个文件均命中 `.gitignore:21:expectation`。
  - `git ls-files --stage -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/_path.py expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`：仅出现上述 local-only `.py` 文件与 `apply/__pycache__/*` 为 `!!` ignored；`__pycache__` 为非合同 cache。
  - `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md kernel/dump` 与 cached 版本均无输出。
- 通过摘要：spec 已补 mixed fixed/auto fixed-reserved-before-auto 合同和 `TC-MULTI-BUFFER-014A`；tracked pytest 使用公开 `MultiBufferApplyPass(target="npu_demo")` 锁定 3 个 fixed `num=2` 先占 `67584` bytes 后 auto group 为 `79`，并反向断言不出现 `81` 或 `multi_buffer.`；现有实现已在 old pair 与 loop staging group 路径先汇总 fixed reserved / same-scope reserved，再扣除 reserved 计算 auto group，无需实现修改；公开 API、registry option、公开错误语义均未改；任务记录已包含 execute、execute -> review、review、review -> archive_acceptance 与本次 archive_acceptance 证据。

## 计划目标
- 锁定 `multi-buffer-apply` mixed fixed/auto 合同：同一 target loop / insertion scope / memory space 内，fixed `multi_buffer.num` 候选必须先计入 reserved bytes，auto group 再按剩余容量计算。
- 对用户发现的场景形成可执行验收：3 个 fixed `num="2"` 的 TSM memory 先占容量，后续 auto group 在 `npu_demo` 下得到 `auto_num=79`，而不是未扣 fixed 时的 `81`。
- 让 execute 只读运行 local-only expectation；若实现已经满足，只补 tracked pytest/spec 证据；若实现不满足，则在 `multi-buffer-apply` 范围内最小修复。

## 执行规则：fixed-reserved before auto
- 候选分类只看当前公开三项临时属性，不靠变量名、文本顺序或 dump 编号猜测：
  - `multi_buffer.num = "<positive-int>"` 是 fixed candidate，例如 `"2"`。
  - `multi_buffer.num = "auto"` 是 auto candidate。
  - 缺少 `multi_buffer.update_points`、`multi_buffer.use_points` 或 `multi_buffer.num` 的 alloc 不是本规则候选；执行人不得为通过测试临时发明新属性。
- 作用域按三元组隔离：同一 insertion scope / target loop / memory space 才共享 reserved 与 capacity。
  - 同 memory space 内的 fixed candidate 必须先扣 reserved，再计算同 scope auto group。
  - 不同 memory space 的 fixed 不得扣到当前 space。
  - 不同 insertion scope 或不同 target loop 的 fixed 不得扣到当前 auto group。
  - 同一 scope 内能证明会与 ring backing 共存的非候选同 space `dma.alloc`，仍按现有 spec 计入 `same_scope_reserved_bytes`；无法证明 footprint 时 auto group 保持 no-op，不得冒险生成可能越界的 backing。
- 字节公式必须按当前 `alignment` 计算：
  - `slot_bytes = shape_element_count * element_byte_width`；动态场景保持当前 symbol expr 公式，不引入 `symbol.get_dim`。
  - `aligned_slot_bytes = align_unit(slot_bytes, alignment)`；默认 `alignment=1024`，`alignment=0` 时按现有合同使用 raw slot bytes。
  - fixed candidate 贡献 `fixed_num * aligned_slot_bytes` 到同 scope / same space 的 `fixed_reserved_bytes`。
  - fixed ring 输出使用 `num=fixed_num`、`offset=aligned_slot_bytes`、`backing_bytes=fixed_num * aligned_slot_bytes`。
- auto group 计算必须在 fixed reserved 汇总完成后进行：
  - `available = target_capacity[space] - fixed_reserved_bytes[space] - same_scope_reserved_bytes[space]`。
  - `group_unit = sum(aligned_slot_bytes(candidate) for candidate in auto group)`。
  - `auto_num = available floordiv group_unit`。
  - target 缺失、capacity 非正、available 非正、group_unit 非正或 auto_num 非正时，auto group no-op。
  - auto group 内每个 candidate 使用同一个 `auto_num`；每个 ring 的 `offset=aligned_slot_bytes(candidate)`，`backing_bytes=auto_num * aligned_slot_bytes(candidate)`。
- 用户场景的静态数字必须能从上述规则直接推出：
  - `npu_demo` TSM capacity = `2097152` bytes。
  - fixed A：`4096 * f32 = 16384` bytes，`num=2`，reserved=`32768`。
  - fixed B：`256 * f32 = 1024` bytes，`num=2`，reserved=`2048`。
  - fixed C：`4096 * f32 = 16384` bytes，`num=2`，reserved=`32768`。
  - `fixed_reserved_bytes = 32768 + 2048 + 32768 = 67584`。
  - auto LHS：`3584 * f32 = 14336` bytes；auto RHS：`2816 * f32 = 11264` bytes。
  - `group_unit = 14336 + 11264 = 25600`。
  - `available = 2097152 - 67584 = 2029568`。
  - `auto_num = 2029568 floordiv 25600 = 79`；未扣 fixed 时 `2097152 floordiv 25600 = 81`，这是本计划必须防住的错误结果。
- 实现顺序要求：
  - 不得在扫描到 auto candidate 时直接用完整 target capacity 生成 `auto_num`。
  - 必须先完成同 scope / same space fixed reserved 汇总，再物化 auto group 的 `num`、`offset`、`backing`。
  - 若现有实现已经满足，execute 只补 spec/pytest 与记录；若不满足，只在 `multi-buffer-apply` 范围内最小修复。
- 测试/验收必须同时锁正反两面：
  - 正向必须看到 fixed `num=2` 对应 ring 和 auto `num=79` 对应 ring。
  - 反向必须断言没有 `81`，并且输出不残留 `multi_buffer.` 临时属性。
  - local-only expectation 只读运行；execute/review/merge/管理员不得修改、移动、重命名、新建或删除 expectation。

## 当前基线
- 当前公开合同：
  - `spec/pass/memory/multi_buffer.md` 已声明 fixed candidate 的 `fixed_backing_bytes` 计入同 memory space 的 `fixed_reserved_bytes`。
  - auto candidate 公式已声明 `available = target_capacity[space] - fixed_reserved_bytes[space] - same_scope_reserved_bytes[space]`。
- 当前公开 API：
  - `MultiBufferAnalysisPass`、`MultiBufferApplyPass`、`MultiBufferPass` 构造签名、`from_options`、`apply` 不变。
  - registry pass name、options、公开错误语义不变。
- 当前实现入口：
  - `kernel_gen/passes/memory/multi_buffer.py`
  - `multi-buffer-apply` 的 loop staging group 路径和旧 matmul pair 路径均存在 fixed reserved 相关逻辑，但缺少用户场景的显式合同锁定。
- 当前测试与验收资产：
  - `test/passes/memory/test_multi_buffer.py` 已覆盖 target auto、different space、dynamic same-space 和 if path。
  - 原本 local-only `expectation/pass/multi_buffer/apply` 多处使用旧 `multi_buffer.update_point/use_point` 字段，已由架构师在 local-only scope 内重物化为当前字段。
- 当前缺口：
  - 缺少 tracked pytest 明确断言“3 fixed=2 后 auto=79，而非 81”的用户场景。
  - 缺少计划级 execute 对目标 worktree local-only expectation 的物化和只读运行记录。

## 方案比较与选型
- 不采用方案 1：把本问题塞进当前 `symbol-loop-hoist-if-branch-no-hoist` 任务。
  - 原因：该任务边界是 symbol loop hoist 中 scf.if branch 内候选不外提；本问题属于 memory multi-buffer apply 容量合同，模块与验收不同。
- 不采用方案 2：全量迁移 `expectation/pass/multi_buffer` analysis/apply/facade。
  - 原因：用户当前问题只指向 apply fixed/auto 混合合同；全量迁移会扩大任务范围并牵出旧本地资产维护问题。
- 采用方案：窄计划，目标集中在 `multi-buffer-apply` mixed fixed/auto。
  - local-only expectation 只收口 apply leaf。
  - tracked 改动只允许覆盖 `spec/pass/memory/multi_buffer.md`、`kernel_gen/passes/memory/multi_buffer.py`、`test/passes/memory/test_multi_buffer.py`、必要的 pipeline dump 测试。

## 公开 API 设计
- 用户确认来源：2026-06-14 用户确认 C1=A / C2=A / C3=A。
- 公开 API 结论：不新增、不删除、不重命名、不改签名、不改默认值、不改公开错误文本、不新增 registry option、不改 target capacity。
- 保持不变：
  - `class MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`
  - `MultiBufferApplyPass.from_options(options: dict[str, str]) -> MultiBufferApplyPass`
  - `MultiBufferApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
  - `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`
  - `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

## 完成态定义
- `multi-buffer-apply` 对同一 memory space 中 fixed 与 auto 混合候选的容量计算稳定为：先扣 fixed reserved，再算 auto group。
- 新增或更新 pytest 直接断言用户场景：3 个 fixed=2 的 TSM candidate 先占容量，后续 auto group 在 `npu_demo` 下得到 `79`。
- 目标 worktree 中 local-only `expectation/pass/multi_buffer/apply` manifest 与本计划记录一致；execute/review/merge 只读取、运行、引用和记录，不修改 expectation。
- `spec/pass/memory/multi_buffer.md` 的测试矩阵或合同说明补齐本场景，且不改变公开 API。
- 计划记录中写清 diff 反推测试、合同验收、scope 外空 diff 和是否需要实现修复。

## 验收设计
- 当前必过 expectation 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`
- pytest / 脚本：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
- 文本核对：
  - 新 pytest 或 dump 核对必须能区分 `79` 与未扣 fixed reserved 时的 `81`。
  - 输出不得残留 `multi_buffer.` 临时属性，fixed `2` 与 auto `79` 对应的 `dma.make_ring` 都必须存在。
- Diff 反推要求：执行与审查按实际 diff 补充测试；`expectation` 单列为合同验收，不计入 diff 反推测试。

## 计划内小任务

### S1. 补齐 mixed fixed/auto 合同描述
- 为什么做：当前 spec 虽有公式，但测试矩阵没有单列用户发现的 3 fixed 后 auto 场景。
- 做什么：在 `spec/pass/memory/multi_buffer.md` 中补充 mixed fixed/auto target same-space 场景和验收矩阵说明。
- 不做什么：不新增 API、不改 option、不改 target capacity、不修改 expectation 本体。
- 怎么验收：`git diff --check -- spec/pass/memory/multi_buffer.md` 通过；spec 文本明确 fixed reserved 先扣，再计算 auto。
- 卡住问谁：公开 API 或容量公式想改时问用户；计划范围和验收口径问架构师。
- 上下文摘要：用户观察到 dump 中前三个 memory 应为 fixed `2`，后续 auto 应基于剩余容量推导。
- 小任务目标：补充 spec/test matrix，使 mixed fixed/auto 行为成为可审查合同。
- 非目标：不改 `MultiBufferApplyPass` 签名和 registry option。
- 模块范围：`spec/pass/memory/multi_buffer.md`
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：用户确认 > `spec/pass/memory/multi_buffer.md` > pytest > local-only expectation > 当前实现。
- 最小功能闭环：spec 中出现 mixed fixed/auto 场景，说明 `auto_num=79` 对应扣 fixed 后结果。
- 执行步骤：
  1. 在测试矩阵增加 mixed fixed/auto 场景。
  2. 在 Apply 合同或示例中明确 fixed reserved 与 auto group 的同 scope 同 space 关系。
  3. 运行 `git diff --check -- spec/pass/memory/multi_buffer.md`。
- 验收必过项目：
  - 文本核对和 `git diff --check -- spec/pass/memory/multi_buffer.md`。
  - 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`。
  - 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`。
  - 说明：上述 expectation 是当前必过合同验收，不计入 diff 反推测试；S4 汇总运行并记录，S1 不授权修改 expectation。
- 记录要求：任务记录写清 spec 变更摘要和未改变公开 API。

### S2. 补 tracked pytest 锁定 3 fixed 后 auto=79
- 为什么做：local-only expectation 不能替代 diff 反推测试，必须有 tracked pytest 锁定行为。
- 做什么：在 `test/passes/memory/test_multi_buffer.py` 添加或更新测试，构造同一 TSM scope 中 3 个 fixed `num="2"` 与 2 个 auto candidate，断言 auto `num=79` 且不是 `81`。
- 不做什么：不直接读取 local-only expectation；不把 dump 文件作为提交产物；不绕过公开 pass API。
- 怎么验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k fixed_reserved` 通过；全文件 pytest 通过。
- 卡住问谁：若只能通过新增测试 helper 或调整公开边界解决，先问架构师；若涉及公开 API，问用户。
- 上下文摘要：用户问题来自真实 dump，但 tracked pytest 应最小化重现容量数学，不依赖临时 dump 产物。
- 小任务目标：新增可稳定运行的 pytest，能失败地区分未扣 fixed reserved 的错误实现。
- 非目标：不新增测试对非公开跨文件 helper 的调用；不提交 `kernel/dump/**`。
- 模块范围：`test/passes/memory/test_multi_buffer.py`
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：用户确认 > spec > pytest > local-only expectation > 当前实现。
- 最小功能闭环：测试构造公开 `MultiBufferApplyPass(target="npu_demo")` 输入并断言 fixed `2` 与 auto `79` 的 `dma.make_ring`。
- 执行步骤：
  1. 复用当前测试文件内公开构造方式，避免跨文件非公开 API。
  2. 构造 slot byte 等价于 `16384 / 1024 / 16384 / 14336 / 11264` 的静态 TSM case。
  3. 给 apply-only 输入补 `analysis.loop_id` 和三项当前 `multi_buffer.update_points/use_points/num` 属性。
  4. 运行定向 pytest 和全文件 pytest。
- 验收必过项目：
  - 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`。
  - 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k fixed_reserved`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py`
  - 说明：expectation 是当前必过合同验收，不计入 diff 反推测试；S2 不授权修改 expectation。
- 记录要求：任务记录写清为什么 `79` 是扣除 fixed reserved 后结果，为什么 `81` 是错误对照。

### S3. 必要时修复 multi-buffer apply mixed fixed/auto
- 为什么做：若 S2 或 expectation 在目标 worktree 失败，说明实现没有完整落实 fixed reserved before auto。
- 做什么：在 `kernel_gen/passes/memory/multi_buffer.py` 内最小修复 fixed reserved 汇总与 auto group 可用容量计算。
- 不做什么：不改公开 API、不新增 pass option、不改 target registry、不调整 pipeline 顺序、不重构无关 matcher。
- 怎么验收：S2 pytest、全文件 pytest、pipeline pytest 和当前必过 expectation 均通过。
- 卡住问谁：若需改变候选边界、容量公式或错误语义，问用户；若流程或任务状态问题，问管理员。
- 上下文摘要：计划不预设实现一定有 bug；执行人必须以验收失败为依据决定是否改实现。
- 小任务目标：确保同一 insertion scope / target loop / memory space 内 fixed reserved 汇总后再计算 auto。
- 非目标：不处理不同任务中的 symbol hoist、tuner selector、cost context 或 dump writer。
- 模块范围：`kernel_gen/passes/memory/multi_buffer.py` 及必要同模块测试。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：用户确认 > spec > pytest > local-only expectation > 当前实现。
- 最小功能闭环：fixed candidate 的 `fixed_num * aligned_slot_bytes` 必须进入同 space reserved；auto group 使用剩余容量计算一个共享 `auto_num`。
- 执行步骤：
  1. 先运行 S2 定向测试和 fixed_reserved expectation，确认是否需要实现修复。
  2. 若失败，定位是旧 matmul pair 路径还是 loop staging group 路径。
  3. 最小修复 reserved 汇总，不引入跨文件 private API 使用。
  4. 更新文件级说明或函数注释，确保实现文件规范仍满足。
  5. 运行计划验收与 diff 反推测试。
- 验收必过项目：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py`
  - 说明：expectation 是当前必过合同验收，不计入 diff 反推测试；S3 只能修实现/spec/test，不能修改 expectation。
- 记录要求：若未改实现，记录证据说明实现已满足；若改实现，记录 root cause、最小 diff 和回归测试。

### S4. 集成验收、权限核对与记录闭环
- 为什么做：本计划同时涉及 tracked spec/test/implementation 和 local-only expectation，必须把两类验收分开记录。
- 做什么：完成 diff 反推测试、当前必过 expectation 合同验收、禁止修改面和 local-only manifest 核对。
- 不做什么：不把 expectation 加入 staged diff；不创建第二个 execute；不替管理员归档。
- 怎么验收：计划列出的 pytest、expectation、diff check、敏感范围空 diff 全部通过并写入任务记录。
- 卡住问谁：expectation 缺失或 hash 不一致时暂停问架构师；状态流转问管理员。
- 上下文摘要：execute/review/merge 只能读取、运行、引用和记录 expectation。
- 小任务目标：让管理员和 review 能直接判断是否可进入下一阶段。
- 非目标：不处理全量 expectation；不修 analysis/facade 旧 local-only expectation。
- 模块范围：任务记录、计划涉及的 spec/test/implementation。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：计划正文列出的当前必过 expectation 与 pytest。
- 最小功能闭环：所有计划验收命令通过，scope 外空 diff 证据完整。
- 执行步骤：
  1. 运行当前必过 expectation leaf 与 apply 聚合入口。
  2. 运行 memory/pipeline pytest 与 private/KCE gate。
  3. 运行 `git diff --check`、`git diff --cached --check`。
  4. 核对 `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` 为空。
  5. 核对 `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` 为空。
  6. 核对 `git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer/apply expectation/pass/multi_buffer/analysis expectation/pass/multi_buffer/facade`；允许的 current contract 仅为 manifest 6 个 apply `.py` 文件，`apply/__pycache__/*` 只能记录为非合同 cache，`analysis/**` 与 `facade/**` 只能记录为非目标既有 ignored local-only 资产。
  7. 记录 local-only expectation hash、check-ignore、ls-files 空输出、staged/unstaged/scope status 分类和合同验收结果。
- 验收必过项目：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply.fixed_reserved_before_auto`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.apply`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/pipeline/test_npu_demo_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
- 记录要求：任务记录分开写 `Diff 反推自测` 与 `合同验收`；不得用 expectation 替代 pytest。若 expectation 缺失、hash 不一致、或失败且疑似合同本体问题，execute/review 只能记录 `actual / expected / spec / verdict` 并暂停转架构裁定，不得修改 expectation 或直接口头豁免。

## 计划自检与返工口径
- 自检：
  - 公开 API：不变。
  - expectation 权限：只由用户授权下的架构师在 local-only scope 物化；execute/review/merge 不得修改。
  - 验收资产：pytest 与 expectation 分开。
  - 任务边界：只覆盖 multi-buffer apply mixed fixed/auto，不包含 symbol hoist、tuner 或全量 expectation 迁移。
  - 可维护性：tracked pytest 锁行为，local-only expectation 锁合同，spec 补充矩阵。
- 返工口径：只要仍有能提升测试有效性、边界完整性、可读性或验收可信度的可执行项，就回到计划修订或 execute 返工。

## 待确认项
- 当前无方案待用户确认项。
- 已确认：
  - C1=A：只收口 apply expectation。
  - C2=A：使用静态 3 fixed=2 后 auto=79 场景。
  - C3=A：补合同 + 必要时修实现。
- 下发门禁：Draft 3 subagent 收敛已完成，Draft 3 守护最终检验已通过；按用户“我确认后下发”口径，当前仍不得通知管理员创建 execute，必须等用户最终确认下发后，架构师才可按流程通知管理员创建唯一计划级 execute。创建后仍必须先保持未分发或暂停状态，待架构师在目标 worktree 完成 local-only expectation 物化门禁后，管理员才可分发或恢复 execute。

## 用户确认与协同约束
- 用户确认来源：2026-06-14 用户回复“是的”确认 C1=A / C2=A / C3=A。
- 用户已确认事项：expectation 更新范围、静态 leaf 数字口径、执行计划范围。
- 待用户确认项：当前无方案待确认。
- expectation 协同约束：
  - 目标 worktree 创建后，管理员必须先保持未分发或暂停状态，待架构师按本 manifest 物化 local-only expectation 并记录 hash/status/check-ignore/ls-files/scope diff/合同验收后，才可恢复或分发 execute。
  - execute、review、archive_acceptance、merge、管理员和替补只能读取、运行、引用与记录 expectation，不得修改、新建、移动、删除或重命名 expectation 本体。
- 迭代审阅记录：已完成 Round 1/2/3；Draft 3 Round 4 发现流程记录阻断；Draft 3 Round 5 已通过并收敛。
- 守护最终检验：Draft 2 已通过且仅作历史依据；Draft 3 已由 `守护最好的爱莉希雅` 本人守护最终检验通过。未取得用户最终确认下发前不得通知管理员创建 execute。
