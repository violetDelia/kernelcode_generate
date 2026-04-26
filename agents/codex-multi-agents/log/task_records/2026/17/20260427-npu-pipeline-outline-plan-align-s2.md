# 20260427-npu-pipeline-outline-plan-align-s2

- 任务号：`T-20260427-edf6681e`
- 创建者：`守护最好的爱莉希雅`
- 最后修改人：`小李飞刀`
- 关联计划书：[npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)
- 相关归档资产：[npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)
- 记录文件：[20260427-npu-pipeline-outline-plan-align-s2.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md)
- 任务类型：`spec`
- worktree：`/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2`

## 任务目标

- 目标：`对齐计划资产与 latest main 现场，收口 done_plan / 任务记录承接位置，并让计划正文、TODO.md 与直接关联归档记录和最新主线一致。`
- 不做什么：`不改任何 expectation；不改实现、pytest、spec 正文合同、其他专题计划或无关归档资产。`

## 相关链接

- spec：
  - [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)
- test：
  - `无新增测试；本任务只做计划资产与记录对齐`
- 功能实现：
  - `latest main 现场无 TODO.md；当前续接以 surviving done_plan 与本任务记录为准`
  - [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)

## 当前阻点

- `origin/main@9a0a52a0730581787bcf4c767167253c4c5b936e` 的干净现场中，不再包含 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`、`TODO.md` 与 `expectation` 包。
- 该现场仍保留的直接计划承接资产只有 `agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md`。
- 因此本轮需要收的不是产品问题，而是活动计划路径缺失后的归档承接说明、任务续接记录和链接层级。

## 边界

- 允许修改：
  - 当前 worktree 的 surviving `done_plan` 归档文件
  - 当前任务记录，以及与该承接位置直接相关的文字说明
- 不允许修改：
  - `expectation/**`
  - `kernel_gen/**`
  - `test/**`
  - 与本计划无直接关系的其他计划资产 / 归档资产

## 自检

- 结论：`通过`
- 说明：`本轮只处理计划归档承接、任务清单 / 任务创建记录 / 归档对齐记录，以及相对链接层级；未扩到实现、测试、spec 合同正文或 expectation。`

## Diff 反推自测

- 已在下方执行记录中补充本轮 diff 对应的本地校验命令和结果。

---

时间：2026-04-27 00:12 +0800
经办人：睡觉小分队
任务：T-20260427-edf6681e
任务目标：把 `npu_pipeline_outline_device_kernel_contract` 主题的计划资产对齐到 latest main 仍存在的承接位置，只处理 surviving `done_plan` 与直接关联记录。
执行前阅读记录：已读 `/home/lfr/kernelcode_generate/TODO.md` 当前任务行、`/home/lfr/kernelcode_generate/AGENTS.md`、`agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`、前序任务记录 `/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260426-npu-pipeline-outline-s1.md`、以及当前 worktree 中 surviving 归档文件 `/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md`。另已核对 latest main 干净现场事实：当前 worktree `HEAD` 即 `origin/main@9a0a52a0730581787bcf4c767167253c4c5b936e`，其中活动计划路径、`TODO.md` 与 `expectation` 包均缺失，只剩旧专题名 `done_plan` 归档文件。
最小功能闭环：保持当前 worktree 中活动计划路径、`TODO.md` 与 `expectation` 包继续缺失；在 surviving `done_plan` 归档文件中补上稳定承接说明、`2026-04-27` 复验结论、`R1` 任务行、`任务创建记录` 与 `归档对齐记录`；同时把该归档文件内原根目录层级的 Markdown 相对链接统一改到 `done_plan` 层级可达，不新建第二份并列归档文件。
改动：
- 更新 [`npu_demo_lowering_outline_device_kernel_green_plan.md`](../../done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)，在标题下新增稳定承接说明，写清自 `origin/main@9a0a52a0730581787bcf4c767167253c4c5b936e` 起活动计划路径、`TODO.md` 与 `expectation` 包已不再随主线出现，当前主题只由这份 surviving `done_plan` 承接。
- 更新同一归档文件的 `最后一次更改` 与 `最近一次更新时间`，并在 `任务清单` 追加 `R1：计划资产与 latest main 现场对齐 / 归档记录收口`。
- 将共享计划里的 `2026-04-27` 复验结论和 `T-20260427-edf6681e` 唯一修复任务信息补入 surviving `done_plan`，再新增 `任务创建记录` 与 `归档对齐记录`，把 `S1-S4` 历史任务链和当前 `R1` 的后续续接依据统一收到归档文件。
- 将归档文件中原来按 `ARCHITECTURE/plan` 层级编写的 Markdown 相对链接统一重写到 `done_plan/2026/17` 层级；同时把 latest main 干净现场中已不存在的 `expectation/pass/outline_device_kernel` 文件入口改成普通代码路径，避免 surviving 归档继续保留失效的可点击链接。
- 重写当前任务记录，补齐本轮 `目标 / 边界 / 自检 / Diff 反推自测 / 执行记录`；未改实现、测试、`expectation` 或任何其他专题资产。
验证：
- `test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md && echo NO_PLAN` -> `NO_PLAN`
- `test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/TODO.md && echo NO_TODO` -> `NO_TODO`
- `test ! -e /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/expectation && echo NO_EXPECTATION` -> `NO_EXPECTATION`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 ls-tree -r --name-only 9a0a52a0730581787bcf4c767167253c4c5b936e | rg '^ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan\\.md$|^TODO\\.md$|^expectation($|/)|^agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan\\.md$'` -> 仅命中 `agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md`
- `python3` Markdown 链接校验脚本：surviving `done_plan` 共解析 `95` 条相对链接，结果 `missing_count=0`
- `python3` 文本断言脚本：确认归档文件已包含稳定承接说明、`2026-04-27` 复验段、`R1` 任务行、`任务创建记录` 与 `归档对齐记录`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 diff --check` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 status --short` -> 仅命中 surviving `done_plan` 归档文件与当前任务记录
Diff 反推自测：
- 本轮实际 diff 只涉及 surviving 归档文件 [`npu_demo_lowering_outline_device_kernel_green_plan.md`](../../done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md) 与当前任务记录；按 diff 反推执行了活动计划路径缺失检查、`TODO.md` 缺失检查、`expectation` 包缺失检查、`ls-tree` 基线核对、Markdown 相对链接校验脚本、文本断言脚本、`git diff --check` 与 `git status --short`。结果通过。
- 本轮未运行 `pytest` 或测试脚本，原因：改动仅限计划归档文字、任务清单与任务记录，不涉及实现、测试文件或本地可执行脚本逻辑。
合同验收（如适用）：
- 未执行。原因：本轮只处理计划资产与记录承接位置，不涉及产品合同入口或 `expectation` 运行结果；`expectation` 继续单列，不计入 `Diff 反推自测`。
自检：已按任务要求重新核对当前任务行、共享计划、前序记录、latest main 干净现场事实和同类归档样例；本轮只处理当前 worktree 的 surviving `done_plan` 与任务记录，没有改实现、测试、`expectation` 或任何其他专题资产；归档文件已写清“为什么仍使用旧专题名文件承接新主题”，同时把 `R1`、`2026-04-27` 复验结论和后续续接依据一并补齐；相对链接也已收到“根目录资产和当前任务记录保留可点击链接，latest main 已缺失的 expectation 入口改成普通代码路径”的一致口径。
结论：当前 `spec` 已完成；`npu_pipeline_outline_device_kernel_contract` 主题在 latest main 干净现场中的现行承接位置已经收到 surviving `done_plan` 与当前任务记录，不需要在该现场重新补回活动计划路径、`TODO.md` 或 `expectation` 包。下一步可进入 `review`，重点复核 `done_plan` 的 `95` 条相对链接、`2026-04-27` 复验承接是否完整，以及本轮 diff 是否只限计划资产 / 归档 / 记录范围。

时间：2026-04-27 00:22:55 +0800
经办人：提莫炖蘑菇
任务：T-20260427-edf6681e / review
任务目标：复核 latest main 现场下的 done_plan 承接、当前任务记录与链接层级是否已经对齐，不再继续指向缺失的活动计划路径、`TODO.md` 或 `expectation` 文件入口。
执行前阅读记录：
- 已读根仓 `TODO.md` 当前任务行、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、`ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md` 的通用口径约束，以及当前任务记录与 surviving done_plan 归档文件。
- 已复核 [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md) 和 [20260427-npu-pipeline-outline-plan-align-s2.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md) 的当前现场。
真实审查：
- surviving done_plan [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md) 的相对链接当前已经可达；文件内也没有继续把 `expectation` 文件入口写成 Markdown 链接。
- latest main 现场缺失事实也和 build 记录一致：当前 worktree 中不存在 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`、`TODO.md` 与 `expectation` 包。
- 但当前任务记录 [20260427-npu-pipeline-outline-plan-align-s2.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md) 仍有 3 处直接链接继续指向活动计划路径或 `TODO.md`：
  - 第 6 行 `关联计划书`
  - 第 20 行 `spec`
  - 第 24 行 `功能实现` 下的 `TODO.md`
- 本轮任务目标要求“done_plan 承接、任务记录与链接层级已对齐，不再误指向缺失的活动计划路径、TODO.md 或 expectation 文件入口”。当前任务记录这 3 处还没收住，因此不能通过。
Diff 反推审查：
- `test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md && echo NO_PLAN; test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/TODO.md && echo NO_TODO; test ! -e /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/expectation && echo NO_EXPECTATION` -> `NO_PLAN / NO_TODO / NO_EXPECTATION`
- `python3` 链接校验脚本：surviving done_plan 与当前任务记录的 Markdown 链接在当前仓库根目录下都可解析；但这不改变当前任务记录仍继续把活动计划路径和 `TODO.md` 当直接承接入口的事实。
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 diff --check` -> 通过
合同验收（如适用）：
- 未执行。原因：本轮只复核计划归档与任务记录承接位置，不涉及产品合同运行。
自检：
- 当前 diff 只涉及计划归档资产；没有实现、测试或 `expectation` 写入。
- 当前剩余问题集中在任务记录链接口径，没有扩散到 surviving done_plan 的相对链接可达性。
可改进点：
- 将当前任务记录中的 `关联计划书` 与 `spec` 改成 surviving done_plan 承接资产，或改成纯文本说明，不再继续把缺失的活动计划路径当作当前现场入口。
- 将当前任务记录 `功能实现` 下的 `TODO.md` 链接改为纯文本缺失说明，或改成 surviving done_plan / 当前记录的续接入口，不再把缺失的 `TODO.md` 当作可点击承接资产。
结论：
- 需修改。
- surviving done_plan 本身已基本对齐，但当前任务记录仍继续直接链接活动计划路径和 `TODO.md`，与本轮“latest main 现场只由 done_plan 承接”的目标不一致。

时间：2026-04-27 00:26:58 +0800
经办人：提莫炖蘑菇
任务：T-20260427-edf6681e / review
任务目标：复核当前任务记录是否已经不再直接链接活动计划路径与 `TODO.md`，并把承接入口统一到 surviving done_plan。
执行前阅读记录：
- 已读根仓 `TODO.md` 当前任务行、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录与 surviving done_plan 归档文件。
- 已复核 [20260427-npu-pipeline-outline-plan-align-s2.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md) 和 [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md) 的当前现场。
真实审查：
- 当前任务记录顶部第 6 / 20 / 24 行已经不再直接链接缺失的活动计划路径与 `TODO.md`，承接入口已改成 surviving done_plan 或纯文本说明。
- surviving done_plan 的相对链接仍然可达，latest main 现场缺失活动计划路径、`TODO.md` 与 `expectation` 包的事实也没有回退。
- 但当前任务记录第 89 行仍保留了一个直接指向活动计划目录的 Markdown 链接：`ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md`。
- 本轮任务目标要求“当前任务记录已不再直接链接活动计划路径与 TODO.md，承接入口已统一到 surviving done_plan”。虽然这个链接不是本专题原活动计划文件，但它仍是直接活动计划路径链接，和本轮收口目标不一致。
Diff 反推审查：
- `rg -n '\\[[^]]+\\]\\([^)]*(ARCHITECTURE/plan|TODO\\.md|expectation/)' /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md` -> 当前仅命中任务记录第 89 行这 1 处 `ARCHITECTURE/plan/...` 直链
- `python3` 当前任务记录 Markdown 链接校验 -> `MISSING 0`
- `test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md && echo NO_PLAN; test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/TODO.md && echo NO_TODO; test ! -e /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/expectation && echo NO_EXPECTATION` -> `NO_PLAN / NO_TODO / NO_EXPECTATION`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 diff --check` -> 通过
合同验收（如适用）：
- 未执行。原因：本轮只复核计划归档与任务记录承接位置，不涉及产品合同运行。
自检：
- 当前剩余问题已经缩到任务记录里的 1 处活动计划路径直链。
- 未改实现、测试与 `expectation`。
可改进点：
- 将当前任务记录第 89 行的活动计划目录直链改成纯文本说明，或改成 surviving done_plan / 当前任务记录入口，避免再次把承接线索拉回活动计划目录。
结论：
- 需修改。
- 当前任务记录的主要承接入口已经改到 surviving done_plan，但第 89 行仍残留 1 处活动计划目录直链，尚未完全收口。

时间：2026-04-27 00:30:53 +0800
经办人：提莫炖蘑菇
任务：T-20260427-edf6681e / review
任务目标：复核当前任务记录中的活动计划目录与 `TODO.md` Markdown 直链是否已经全部清零，并确认承接入口只保留 surviving done_plan。
执行前阅读记录：
- 已读 TODO.md 当前任务行、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录与 surviving done_plan 归档文件。
- 已复核 [20260427-npu-pipeline-outline-plan-align-s2.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md) 与 [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md) 的当前现场。
真实审查：
- 当前任务记录顶部 `关联计划书 / spec / 功能实现` 承接入口已经全部改到 surviving done_plan 或纯文本说明，不再直接链接缺失的活动计划路径与 `TODO.md`。
- 上一轮 review 指出的第 89 行活动计划目录直链已经改成纯文本，不再命中 Markdown 直链扫描。
- surviving done_plan 继续作为当前唯一承接入口；latest main 现场缺失活动计划路径、`TODO.md` 与 `expectation` 包的事实也没有回退。
- 当前 diff 范围内没有新增指向 `expectation` 文件入口的 Markdown 直链。
Diff 反推审查：
- `rg -n '\\[[^]]+\\]\\([^)]*(ARCHITECTURE/plan|TODO\\.md|expectation/)' /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md` -> 无命中
- `python3` Markdown 链接校验脚本 -> `20260427-npu-pipeline-outline-plan-align-s2.md: missing=0`，`npu_demo_lowering_outline_device_kernel_green_plan.md: missing=0`
- `test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md && echo NO_PLAN; test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/TODO.md && echo NO_TODO; test ! -e /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/expectation && echo NO_EXPECTATION` -> `NO_PLAN / NO_TODO / NO_EXPECTATION`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 diff --check` -> 通过
合同验收（如适用）：
- 未执行。原因：本轮只复核计划归档与任务记录承接位置，不涉及产品合同运行。
自检：
- 当前 diff 仍只涉及计划归档资产与任务记录，没有实现、测试或 `expectation` 写入。
- 当前任务记录中的活动计划目录与 `TODO.md` Markdown 直链已经清零，承接入口已经统一到 surviving done_plan。
结论：
- 通过。
- 当前任务记录与 surviving done_plan 的承接入口已经一致，latest main 现场下不再误指向缺失的活动计划路径、`TODO.md` 或 `expectation` 文件入口。

时间：2026-04-27 11:28:00 +0800
经办人：小李飞刀
任务：T-20260427-edf6681e / build 返修
任务目标：将当前任务记录中剩余的活动计划路径与 `TODO.md` 直链收口到 surviving `done_plan` 承接或纯文本缺失说明，避免当前现场继续把缺失入口当作可点击资产。
执行前阅读记录：
- 已读根仓 `TODO.md` 当前任务行、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录中的 build / review 条目，以及 surviving 归档文件 [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)。
- 已复核当前任务记录中所有 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md` 与 `TODO.md` 的 Markdown 直链残留，确认只剩顶部 `关联计划书`、`相关链接/spec`、`相关链接/功能实现` 和 review 条目中的 `TODO.md` 可点击入口。
最小功能闭环：
- 当前任务记录不再把缺失的活动计划路径或 `TODO.md` 作为可点击承接入口。
- surviving `done_plan` 继续作为当前主题唯一可点击承接资产；`TODO.md` 只保留为缺失事实说明。
- 本轮只收任务记录文字和链接口径，不改 `done_plan` 主体、不改实现、不改测试。
改动：
- 更新当前任务记录顶部 `关联计划书`，改为指向 surviving 归档文件 [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)。
- 更新 `相关链接/spec`，改为同一份 surviving `done_plan` 承接资产。
- 更新 `相关链接/功能实现`，将原来的 `TODO.md` 可点击入口改成纯文本缺失说明：`latest main 现场无 TODO.md；当前续接以 surviving done_plan 与本任务记录为准`。
- 更新 review 条目中的 `执行前阅读记录`，将原来的 `TODO.md` 可点击入口改为纯文本 `TODO.md`，避免记录正文继续保留缺失入口直链。
- 同步本记录文件头 `最后修改人` 为 `小李飞刀`。
验证：
- `python3` 文本计数脚本：当前任务记录中“活动计划直链”计数 `0`，“TODO 直链”计数 `0`
- `python3` Markdown 链接校验脚本：当前任务记录相对 / 绝对 Markdown 链接解析结果 `missing_count=0`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 diff --check` -> 通过
Diff 反推自测：
- 本轮实际 diff 只涉及当前任务记录 [20260427-npu-pipeline-outline-plan-align-s2.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md)；按 diff 反推执行了活动计划路径 / `TODO.md` 直链计数脚本、Markdown 链接校验脚本与 `git diff --check`，结果通过。
- 本轮未运行 `pytest` 或测试脚本，原因：改动仅限任务记录文字和链接口径，不涉及实现、测试文件或脚本逻辑。
合同验收（如适用）：
- 未执行。原因：本轮只收任务记录承接入口，不涉及产品合同运行；`expectation` 继续只读且不计入 diff 反推测试。
自检：
- 本轮未改 `expectation`、未改实现、未改测试，也未扩到其他专题归档资产。
- surviving `done_plan` 继续作为当前主题唯一承接资产；当前任务记录已不再把缺失的活动计划路径和 `TODO.md` 当作当前现场入口。
- 变更范围仅限当前任务记录，符合 review 退回项“当前任务记录仍直接链接活动计划路径和 TODO.md”的最小返修范围。
结论：
- 当前 build 已完成，可续接 `review`。
- 本轮返修点已收住：当前任务记录中的活动计划路径与 `TODO.md` 直链已全部移除，承接入口已统一到 surviving `done_plan` 与当前记录。

时间：2026-04-27 11:40:00 +0800
经办人：小李飞刀
任务：T-20260427-edf6681e / build 返修
任务目标：清理当前任务记录第 89 行残留的活动计划目录 Markdown 直链，并同步去掉同轮 review 条目里残留的 `TODO.md` 可点击入口。
执行前阅读记录：
- 已读根仓 `TODO.md` 当前任务行、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录最近一轮 review 条目，以及 surviving `done_plan` 承接资产 [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)。
- 已复核当前任务记录中全部 `ARCHITECTURE/plan/*.md` 和 `TODO.md` 的 Markdown 直链残留，确认 review 指出的第 89 行活动计划目录链接，以及同轮 review 条目中的 `TODO.md` 可点击入口仍未清除。
最小功能闭环：
- 当前任务记录不再包含任何指向 `ARCHITECTURE/plan/*.md` 或 `TODO.md` 的 Markdown 直链。
- surviving `done_plan` 继续作为当前主题唯一可点击承接资产。
- 本轮只收任务记录文字口径，不改 `done_plan` 主体、实现、测试或 `expectation`。
改动：
- 将 review 条目第 89 行中的活动计划目录链接从 Markdown 链接改为纯文本：`ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md`。
- 将同轮 review 条目中的 `TODO.md` 可点击入口改为纯文本 `TODO.md`。
验证：
- `python3` 文本计数脚本：`activity_plan_markdown_links=0`，`todo_markdown_links=0`
- `python3` Markdown 链接校验脚本：`missing_count=0`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 diff --check` -> 通过
Diff 反推自测：
- 本轮实际 diff 只涉及当前任务记录 [20260427-npu-pipeline-outline-plan-align-s2.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md)；按 diff 反推执行了活动计划目录 / `TODO.md` Markdown 直链计数脚本、Markdown 链接校验脚本与 `git diff --check`，结果通过。
- 本轮未运行 `pytest` 或测试脚本，原因：改动仅限任务记录文字，不涉及实现、测试文件或脚本逻辑。
合同验收（如适用）：
- 未执行。原因：本轮只收任务记录承接入口，`expectation` 继续只读且不计入 diff 反推测试。
自检：
- 本轮未改 `expectation`、未改实现、未改测试，也未扩到其他归档资产。
- 当前任务记录中所有活动计划目录与 `TODO.md` 的 Markdown 入口现已清零，和本轮“只由 surviving done_plan 承接”的目标一致。
结论：
- 当前 build 已完成，可续接 `review`。
- review 指出的最后 1 处活动计划目录直链已清除；当前任务记录已完全收口到 surviving `done_plan` 承接。

时间：2026-04-27 12:18:00 +0800
经办人：李白
任务：T-20260427-edf6681e / merge
任务目标：将 surviving `done_plan` 承接正文与当前任务记录的 residual diff 重放到 latest `origin/main`，确保活动计划目录与 `TODO.md` Markdown 直链保持清零，当前主题只保留 surviving `done_plan` 作为承接入口。
执行前阅读记录：
- 已读根仓 TODO 当前任务行、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、共享计划 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md` 的 `R1` 阶段 / 完成态 / 验收设计、前序记录 [20260426-npu-pipeline-outline-s1.md](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260426-npu-pipeline-outline-s1.md)、当前任务记录中的 build / review 结论，以及 surviving 归档文件 [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md)。
- 已核对 merge 基线：工作树原始 `HEAD` 为 `9a0a52a0730581787bcf4c767167253c4c5b936e`，latest `origin/main` 为 `95620a9d3fc9d597e9807ad8821dd6a8f492cf77`。
- 已核对 review 结论已通过；重放后复查发现当前任务记录第 148 行仍残留 1 处 `TODO.md` 直链，因此在 merge 前补做最小收口。
最小功能闭环：
- 只收 surviving `done_plan` 归档正文和当前任务记录。
- 当前任务记录中不再保留任何指向活动计划目录、`TODO.md` 或 `expectation` 的 Markdown 直链。
- 当前专题的承接入口只保留 surviving `done_plan` 与当前任务记录，不回带活动计划路径。
- 不修改任何实现、测试或 `expectation` 资产。
真实收口过程：
- 在工作树执行 `git fetch origin`，确认 latest `origin/main` 前进到 `95620a9d3fc9d597e9807ad8821dd6a8f492cf77`。
- 通过 `stash -> detach 到 origin/main -> stash pop` 将 worktree 残差重放到 latest 主线，无文本冲突。
- 重放后发现当前任务记录仍残留 1 处 `TODO.md` 直链，于是将该处改成纯文本 `TODO.md`，保持和本轮 review 目标一致。
- 本轮 merge 的 tracked diff 只包括 surviving 归档文件 [npu_demo_lowering_outline_device_kernel_green_plan.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md) 与当前任务记录 [20260427-npu-pipeline-outline-plan-align-s2.md](/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md)。
验证：
- `rg -n '\\[[^]]+\\]\\([^)]*(ARCHITECTURE/plan|TODO\\.md|expectation/)' /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md` -> 无命中
- `test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md && echo NO_PLAN; test ! -f /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/TODO.md && echo NO_TODO; test ! -e /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/expectation && echo NO_EXPECTATION` -> `NO_PLAN / NO_TODO / NO_EXPECTATION`
- `python3` Markdown 链接校验脚本 -> `20260427-npu-pipeline-outline-plan-align-s2.md: missing=0`，`npu_demo_lowering_outline_device_kernel_green_plan.md: missing=0`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2 diff --check` -> 通过
Diff 反推自测：
- 本轮实际 diff 只涉及 surviving `done_plan` 与当前任务记录；按 diff 反推执行了活动计划目录 / `TODO.md` / `expectation` Markdown 直链扫描、缺失路径探测、Markdown 链接校验脚本与 `git diff --check`，结果通过。
- 本轮未运行 `pytest` 或测试脚本，原因：当前 diff 不涉及实现文件、测试文件或本地可执行脚本逻辑。
合同验收（如适用）：
- 未执行。原因：本轮只收归档正文与任务记录承接口径；`expectation` 未改动，继续只读且不计入 diff 反推测试。
自检：
- 未改实现、未改测试、未改 `expectation`。
- 当前主题在 latest main 现场下继续只由 surviving `done_plan` 和当前任务记录承接，没有重新引入活动计划目录或 `TODO.md` 作为可点击入口。
- merge 只收最小文本残差，没有扩大到其他专题或共享资产。
结论：
- 可以提交、推送并执行 `-done`。
- 本轮 merge 收口后，当前任务记录中的活动计划目录与 `TODO.md` Markdown 直链保持清零，承接入口只保留 surviving `done_plan`。
