# multi_buffer_analysis_apply_split

## 文档信息

- 状态：Draft 3-R2，Round 3-A / Round 3-B `subagent` strict review 均通过；`守护最好的爱莉希雅` 本人守护最终检验通过，当前无阻断项、无最小需改项、无待用户确认项；允许管理员按恢复门禁恢复既有暂停任务 `T-20260610-c415f4aa`，不得创建第二个 `execute`。
- 目标 `spec`：
  - [`spec/pass/memory/multi_buffer.md`](../../spec/pass/memory/multi_buffer.md)
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
- 目标 `API`：以下公开 class / pass name / 签名保持用户确认口径，不新增、不删除、不重命名。
  - `class MultiBufferAnalysisPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
  - `MultiBufferAnalysisPass.from_options(options: dict[str, str]) -> MultiBufferAnalysisPass`
  - `MultiBufferAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
  - `class MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`
  - `MultiBufferApplyPass.from_options(options: dict[str, str]) -> MultiBufferApplyPass`
  - `MultiBufferApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
  - `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`
  - `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
  - `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`
  - registry pass name：`multi-buffer-analysis`、`multi-buffer-apply`、兼容保留 `multi-buffer`
- 目标 `test`：
  - [`test/passes/memory/test_multi_buffer.py`](../../test/passes/memory/test_multi_buffer.py)
  - [`test/passes/test_registry.py`](../../test/passes/test_registry.py)
  - [`test/passes/pipeline/test_npu_demo_lowering.py`](../../test/passes/pipeline/test_npu_demo_lowering.py)
- 目标 `验收资产`：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
- 本地 `expectation` 诊断参考（非必过，不纳入远程候选）：
  - `expectation/pass/multi_buffer/**`
  - 只读运行用于对照 paused worktree 的 split 行为，不进入计划级 execute 必过项，不作为 merge 候选，不要求 `git add -f`。
- 目标 `功能实现`：
  - [`kernel_gen/passes/memory/multi_buffer.py`](../../kernel_gen/passes/memory/multi_buffer.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/pipeline/npu_demo_lowering.py`](../../kernel_gen/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/passes/memory/__init__.py`](../../kernel_gen/passes/memory/__init__.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/multi_buffer.py`](../../kernel_gen/passes/multi_buffer.py)

## 计划级任务

- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`。
- 本计划只允许一个计划级 `execute` 大任务；S1-S4 是计划内小任务卡，不创建独立 `TODO` 状态。
- 旧任务 `T-20260610-c415f4aa` 已暂停，恢复时仍应沿用同一任务链，不再新建第二个 `execute`。
- 恢复前置：恢复 `T-20260610-c415f4aa` 前，必须先完成下方“恢复门禁”；execute 开工后只核对门禁证据，不负责剥离或清理 `expectation/` staged 候选。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `multi-buffer-analysis-apply-split` | `execute` | `wt-20260610-multi-buffer-analysis-apply-split` | `agents/codex-multi-agents/log/task_records/2026/24/20260610-multi-buffer-analysis-apply-split.md` |

### 恢复门禁

- 责任角色：管理员或架构侧在恢复 `execute` 前完成；计划级 execute 不执行此门禁清理动作。
- 目标：paused worktree 只能保留实现 / spec / test / 任务记录等计划级候选，不得把 `expectation/pass/multi_buffer/**` 放在 staged / merge candidate 中。
- 操作现场：`/home/lfr/kernelcode_generate/wt-20260610-multi-buffer-analysis-apply-split`。
- 最小动作：
  1. 将正式通过 strict review 和守护最终检验的 Draft 3 计划文本同步到 worktree 的 `ARCHITECTURE/plan/multi_buffer_analysis_apply_split.md`。
  2. 从 index 剥离 expectation 候选，保留本地文件时也只能作为 ignored / untracked local-only 参考：

```bash
git restore --staged -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py
```

  3. 记录并满足以下核对：

```bash
git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py
```

预期无输出。

```bash
git status --short --ignored --untracked-files=all -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py
```

预期不得出现第一列为 `A` / `M` / `D` 的 staged 状态；允许 `!!` 或 `??` 表示本地-only 文件。

- execute 开工核对：若上述 cached diff 非空，execute 必须暂停并回管理员，不得自行修改、移动、删除或提交 `expectation/`。

## 迭代审阅记录

### 历史收口摘要

- 旧 Draft 2-R8 已把 `analysis/apply/facade` 的公开 API、registry 名称、pipeline 顺序和大部分测试边界收口到可执行形态。
- 旧 Draft 2-R8 里的 `expectation/pass/multi_buffer/**` 被放进了计划阶段候选；用户随后明确改口：`expectation` 只允许本地-only 诊断，不应出现在计划级远程候选或 execute 必过项里。
- 因此本次 Draft 3 不是重做 split 方案，而是把合同边界重新收回到“代码 / spec / pytest 为主，local-only expectation 仅作参考”。

### 当前收敛状态

- Round 1-A：`Sagan`，agent_id=`019ebc3d-29d7-7f10-bf49-061f74d804d3`，结论=不通过。
  - 标准包：`AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/expectation任务规则.md`、本计划全文、上一轮 review / pause 记录、用户最新 local-only expectation 口径、禁止修改面、必过验收命令。
  - 严格通过口径：仍有可执行改进项则不通过。
  - 发现问题：恢复前置未写成可执行门禁；S1-S4 小任务卡缺 `执行步骤`、`验收与记录要求`。
  - 主线处理：已补“恢复门禁”，明确恢复前由管理员或架构侧剥离 staged expectation，execute 只核对；已补 S1-S4 执行步骤与记录要求。
  - 状态：不通过，已按问题修订为 Draft 3-R1，待 Round 2 复审。
- Round 1-B：`Russell`，agent_id=`019ebc3d-b60a-7781-bfdb-68c837aac243`，结论=不通过。
  - 标准包：同 Round 1-A，另重点审 API 确认来源、local-only expectation 是否变相验收、恢复前置和任务卡结构。
  - 严格通过口径：仍有可执行改进项则不通过。
  - 发现问题：公开 API / 稳定错误语义用户确认来源写得不完整；local-only expectation 命令仍放在“验收设计”下造成变相验收歧义；恢复前置缺 owner 和证据；S1-S4 缺执行步骤与记录要求；archive_acceptance 段缺归档目标和核对项。
  - 主线处理：已补 API 用户确认来源逐项；已把 local-only expectation 移到独立“可选本地诊断参考（非验收）”；已补恢复门禁 owner / 命令 / 证据；已补任务卡步骤与记录要求；已补入档验收核对项。
  - 状态：不通过，已按问题修订为 Draft 3-R1，待 Round 2 复审。
- Round 2-A：`Sagan`，agent_id=`019ebc3d-29d7-7f10-bf49-061f74d804d3`，结论=不通过。
  - 审阅对象：Draft 3-R1。
  - 发现问题：恢复门禁、S1-S4 可执行性、Draft 2-R8 / expectation staged 混用风险已基本闭合；但稳定错误语义漏列 `memory_stage must be integer` 与 `memory-stage must be positive`。
  - 主线处理：已在 Draft 3-R2 的公开 API 稳定错误语义和用户确认来源中补齐两条错误文本。
  - 状态：不通过，已修订，待 Round 3 复审。
- Round 2-B：`Russell`，agent_id=`019ebc3d-b60a-7781-bfdb-68c837aac243`，结论=通过。
  - 审阅对象：Draft 3-R1。
  - 通过摘要：恢复门禁、local-only expectation 非验收、必过验收设计、archive_acceptance / 归档目标、S1-S4 执行步骤和 API / 用户确认来源均已基本闭合。
  - 状态：通过；由于 Round 2-A 仍有最小需改项，整体尚未收敛，需基于 Draft 3-R2 继续复审。
- Round 3-A：`Sagan`，agent_id=`019ebc3d-29d7-7f10-bf49-061f74d804d3`，结论=通过。
  - 审阅对象：Draft 3-R2。
  - 通过摘要：Round 2-A 漏列的两条错误语义已补入公开 API 与用户确认来源；恢复门禁、S1-S4 可执行性、local-only expectation 非验收和 staged 范围均无阻断。
  - 阻断项：无。
  - 最小需改项：无。
  - 待用户确认项：无。
- Round 3-B：`Russell`，agent_id=`019ebc3d-b60a-7781-bfdb-68c837aac243`，结论=通过。
  - 审阅对象：Draft 3-R2。
  - 通过摘要：Round 2-B 通过项保持通过；新增错误语义未引入 API / 用户确认 / 验收歧义；恢复门禁、archive_acceptance、S1-S4 与 local-only expectation 边界均可执行。
  - 阻断项：无。
  - 最小需改项：无。
  - 待用户确认项：无。
- subagent 收敛结论：已发起的 strict review 任务 `Sagan` / `Russell` 已基于最新 Draft 3-R2 收敛到无阻断项、无最小需改项、无待用户确认项；可进入 `守护最好的爱莉希雅` 本人守护最终检验。
- 守护最终检验：`守护最好的爱莉希雅` 本人已于 talk.log 回执 Draft 3-R2 结论=通过；阻断项=无；最小需改项=无；待确认项=无。
  - 关键证据：`git ls-files --stage -- ARCHITECTURE/plan/multi_buffer_analysis_apply_split.md` 为 `100644 8c4511fd379f2443b124fe252532a22df2efd572 0`；`git diff --cached --name-status -- ARCHITECTURE/plan/multi_buffer_analysis_apply_split.md expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py` 仅有 `A ARCHITECTURE/plan/multi_buffer_analysis_apply_split.md`；`expectation/pass/multi_buffer/**` 与 `expectation/pass/pipeline/npu_demo_lowering.py` 为 ignored local-only。
  - 恢复结论：允许管理员按计划正文恢复门禁恢复既有暂停任务 `T-20260610-c415f4aa`，继续沿用原计划级 `execute` / 金铲铲大作战链路；不得创建第二个 `execute`。恢复时仍须在执行 worktree 同步通过终验的 Draft 3 计划、剥离 staged expectation candidate，并由 execute 开工核对门禁证据。
- 当前状态：守护最终检验已通过；等待管理员按恢复门禁恢复 `T-20260610-c415f4aa` execute。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：提莫炖蘑菇。
- 结论：通过（merge 门禁返工后复验）。
- 验证基线：`/home/lfr/kernelcode_generate/wt-20260610-multi-buffer-analysis-apply-split`；`HEAD=427308a109643290a2b321d3d2fe82d8e2f06972`，`origin/main=427308a109643290a2b321d3d2fe82d8e2f06972`，`merge-base=427308a109643290a2b321d3d2fe82d8e2f06972`，ahead/behind=`0 0`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260610-multi-buffer-analysis-apply-split`。
- 合同验收摘要：本计划没有当前必过 `expectation` 合同验收；入档验收只运行正文列出的 pytest / 脚本 / private-KCE 门禁，并核对 `expectation/pass/multi_buffer/**` 未进入 staged / merge candidate。
- 入档核对项：latest main 基线、执行目录、计划正文必过命令、arch_parallelize tight-colon CHECK 返工、Diff 反推审查、private/KCE 门禁、`git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py` 空输出、敏感禁止修改面空 diff。
- 结果摘要：merge 门禁返工 review 阶段已通过；入档验收阶段核对当前记录、latest main 同步现场、arch_parallelize tight-colon CHECK、计划必过 pytest / 脚本、private/KCE、arch/gen_kernel Diff 反推、敏感范围和 `expectation` local-only 边界均通过；`git diff --check && git diff --cached --check` 通过，`expectation/pass/multi_buffer/**` 仅为 ignored local-only。
- 归档目标：入档验收通过后进入 `merge/归档`，由合并角色把计划书归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/multi_buffer_analysis_apply_split.md`；架构师不替 merge 角色归档。
- 最小阻断项或通过摘要：无阻断项、无最小需改项。

## 计划目标

- 继续完成 `multi-buffer` split 方案的残余收口，重点修复 loop-local / direct-use staging 的 `dma.current_ring` 插入边界。
- 保持 `MultiBufferAnalysisPass -> MultiBufferApplyPass -> MultiBufferPass` 的公开 API 与 registry 口径不变。
- 让 use block 已有前缀 op 时，`dma.current_ring` 仍插到第一条既有 op 前；`dma.advance_ring` 保持在 use block 末尾或 terminator 前。
- 本地-only `expectation/pass/multi_buffer/**` 仅用于诊断 paused worktree 的行为，不作为计划级必过项，不作为远程候选。

## 当前基线

- root snapshot：2026-06-12 在 `/home/lfr/kernelcode_generate` 执行 `git fetch origin main --prune` 后，`HEAD=28f277aaf4f20317cc9fde1cc1673a2bdc010b5a`，`origin/main=a82065dc065cfc14b6a45e5dcdfa11692fb43672`，`merge-base=28f277aaf4f20317cc9fde1cc1673a2bdc010b5a`；远端相对本地新增差异当前只涉及 `kernel_gen/passes/arch/arch_parallelize.py`。
- root snapshot 当前仍保留旧 `MultiBufferPass` 形态；正式计划候选只 staged `ARCHITECTURE/plan/multi_buffer_analysis_apply_split.md`，`expectation/pass/multi_buffer/**` 是 ignored local-only。
- paused execution worktree：`/home/lfr/kernelcode_generate/wt-20260610-multi-buffer-analysis-apply-split` 已有 split 方案的大部分实现、spec 和测试改动，但该 worktree 内计划文件仍可能是 Draft 2-R8，且历史 staged expectation 候选必须按“恢复门禁”先剥离。
- paused execution worktree 最新复审留下的唯一实现阻断是：loop-local / direct-use 分支在 use block 已有无关前缀 op 时，`dma.current_ring` 仍可能落在前缀之后，而不是第一条既有 op 前。
- paused execution worktree 现有 `test/passes/memory/test_multi_buffer.py` 已覆盖 matmul pair、existing-current no-op 和若干 direct use 场景，但还缺少“已有前缀 op / terminator”这类边界断言。
- 恢复 execute 前必须在执行 worktree 重新同步 latest main、套用通过终验的 Draft 3 计划、清空 staged expectation candidate，并按最终 diff 反推测试。

## 方案比较与选型

- 不采用方案：把 `expectation/pass/multi_buffer/**` 继续写进计划级必过合同或 staged 远程候选。
- 采用方案：`expectation/pass/multi_buffer/**` 只保留本地诊断参考；计划级验收只依赖 pytest、脚本和 diff 反推测试。
- 取舍理由：用户已明确本地-only 口径；execute / review / archive_acceptance 只需验证公开实现、spec 与测试闭环，避免把合同资产混入远程链路。
- 风险：如果 local-only expectation 与实现再度冲突，只记录证据，不自动升级为计划级修改 `expectation`。

## 公开 API 设计

本轮不新增公开 API，只继续执行用户已确认的 split 口径。

API 列表：

- `class MultiBufferAnalysisPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
  - `memory_stage`：正整数；`target is None` 时 same-loop staging 仍以固定 stage 口径运行。
  - `target`：`None` 或非空字符串；非空时优先走 target capacity 口径。
- `MultiBufferAnalysisPass.from_options(options: dict[str, str]) -> MultiBufferAnalysisPass`
  - 允许 `memory-stage` 与 `target`。
  - `fold` 与未知 option 仍报稳定错误。
- `MultiBufferAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
  - 只写三项临时属性，不物化 ring。
- `class MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`
  - `alignment`：非负整数；默认 `1024`；`0` 关闭对齐。
- `MultiBufferApplyPass.from_options(options: dict[str, str]) -> MultiBufferApplyPass`
  - 允许 `target` 与 `alignment`。
- `MultiBufferApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
  - 读取 analysis 属性，消费并删除临时属性，物化 ring。
- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`
  - 兼容 facade，内部顺序执行 analysis 再 apply。
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`
- registry pass name：
  - `multi-buffer-analysis`
  - `multi-buffer-apply`
  - `multi-buffer`
- package re-export：
  - `kernel_gen.passes.memory.MultiBufferAnalysisPass`
  - `kernel_gen.passes.memory.MultiBufferApplyPass`
  - `kernel_gen.passes.memory.MultiBufferPass`
  - `kernel_gen.passes.MultiBufferAnalysisPass`
  - `kernel_gen.passes.MultiBufferApplyPass`
  - `kernel_gen.passes.MultiBufferPass`
- 稳定错误语义：
  - `MultiBufferOptionError: memory_stage must be positive`
  - `MultiBufferOptionError: memory_stage must be integer`
  - `MultiBufferOptionError: target must be non-empty`
  - `MultiBufferOptionError: unknown option: <name>`
  - `MultiBufferOptionError: memory-stage must be integer`
  - `MultiBufferOptionError: memory-stage must be positive`
  - `MultiBufferOptionError: alignment must be non-negative integer`
  - registry 包装为 `PassRegistryError: pass '<pass-name>' option error: <原因>`

## 完成态定义

- `spec/pass/memory/multi_buffer.md`、`spec/pass/registry.md`、`spec/pass/pipeline/npu_demo_lowering.md` 仍保持 split 口径，且不再把 local-only expectation 写成计划级必过合同。
- `kernel_gen/passes/memory/multi_buffer.py` 在 direct-use 路径上满足：use block 已有前缀 op 时，`dma.current_ring` 必须落在第一条既有 op 之前。
- `kernel_gen/passes/memory/multi_buffer.py` 对满足条件的 existing-current 候选保持 no-op，不重复 ring 化。
- `test/passes/memory/test_multi_buffer.py` 能在 prefix / suffix / terminator 场景下锁定 current / advance 的绝对位置。
- `test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py` 复验通过。
- 本地-only `expectation/pass/multi_buffer/**` 可继续作为诊断参考，但不进入 archive_acceptance 的必过范围。

## 非目标与禁止修改面

- 不修改、新建、移动、删除或提交 `expectation/` 本体；`expectation/pass/multi_buffer/**` 只保留本地 ignored 诊断参考。
- 不修改 `expectation/pass/pipeline/npu_demo_lowering.py`，不把 pipeline expectation 列为当前必过项。
- 不修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md`。
- 不新增 pipeline option，不改变 `build_npu_demo_lowering_pipeline` 公开签名。
- 不新增 plan 外公开 API、脚本参数、include API 或稳定错误文本。
- 不处理任意 alias escape、多层 alias chain、已有 ring 再 ring 化、`arch.sign` / `arch.wait` / async barrier。
- 不把 local-only expectation 当作 diff 反推测试，不用它替代 pytest 或脚本验收。

## 合同真源

优先级：

1. 用户确认来源。
2. 本计划 Draft 3 口径。
3. `spec/pass/memory/multi_buffer.md`、`spec/pass/registry.md`、`spec/pass/pipeline/npu_demo_lowering.md`。
4. `test/passes/memory/test_multi_buffer.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`。
5. 当前实现。

说明：

- `expectation/pass/multi_buffer/**` 不是当前必过合同真源，只能作为本地-only 诊断参考。
- 若 local-only expectation 与 spec / pytest 冲突，记录 actual / expected / spec / verdict 后转架构，不由 execute 修改 expectation。

## 验收设计

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py
```

## 可选本地诊断参考（非验收）

- execute 不要求运行以下命令；archive_acceptance 不把这些命令作为通过前置。
- 如执行人或审查人自愿运行，只能记录 `actual / expected / spec / verdict` 作为诊断；失败不阻断本计划，不触发 execute 修改 `expectation/`。
- local-only expectation 不计入 Diff 反推测试，不替代 pytest / 脚本 / private-KCE 门禁。

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260610-multi-buffer-analysis-apply-split PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.multi_buffer
```

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260610-multi-buffer-analysis-apply-split PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.multi_buffer.apply
```

## 计划内小任务

### S1. 收口 direct-use current 插入边界

- 为什么做：review 已确认 loop-local / direct-use 分支在 use block 有前缀 op 时，`dma.current_ring` 还可能落在前缀之后。
- 做什么：修正 `kernel_gen/passes/memory/multi_buffer.py` 的 current 插入锚点选择，让 direct-use 与 loop-local staging 的 current 都优先插到 use block 第一条既有 op 前；如果支配关系不允许，则候选 no-op 或回架构 / 用户确认。
- 不做什么：不改公开 API，不引入新 pass，不把 `expectation` 变成远程候选。
- 怎么验收：补齐 prefix / suffix / terminator 边界测试，确认 current 绝对位置与 advance 绝对位置都满足计划口径。
- 卡住问谁：支配关系或口径冲突问架构师；需要改公开 API 问用户；任务状态问管理员。
- 模块范围：`kernel_gen/passes/memory/multi_buffer.py`
- 禁止修改面：`expectation/` 本体、`.skills/`、`agents/standard/`、`AGENTS.md`、计划正文之外的任务状态文件。
- 合同真源：`spec/pass/memory/multi_buffer.md > pytest > 当前实现`
- 最小功能闭环：use block 前缀 op 存在时，current 仍在前缀前；advance 仍在尾部 / terminator 前。
- 执行步骤：
  1. 在恢复门禁已通过的 worktree 阅读 `spec/pass/memory/multi_buffer.md` 的 current / advance 插入点合同和上一轮 review 记录。
  2. 定位 `kernel_gen/passes/memory/multi_buffer.py` 中 loop-local / direct-use staging 的 current 插入路径，找出当前使用 `insertion_anchor` 或 alloc 附近锚点导致 current 落在既有前缀 op 后面的分支。
  3. 将 direct-use current 插入锚点收口为 use block 第一条既有 op 前；advance 插入锚点保持 use block 末尾或 terminator 前。
  4. 若某类候选的 setup / dynamic shape operand 不能在第一条既有 op 前支配 current，则该候选 no-op，并记录原因；不得静默退回“first use 前”口径。
  5. 同步更新本文件内被修改函数的功能说明 / 使用示例注释和文件级 `API 列表`，不得新增跨文件非公开 helper 调用。
- 验收与记录要求：
  - 记录 direct-use current 插入点修改前后的 IR 顺序证据，至少包含 prefix、current、slice/use、suffix、advance 的相对位置。
  - 记录是否触发 no-op 分支；若触发，写清 spec 依据和测试覆盖。
  - 本卡验收由 S2/S3 的 pytest 和 private/KCE 门禁闭合，不单独用 expectation 判定。

### S2. 补 direct-use / existing-current 回归测试

- 为什么做：当前 tests 只证明 matmul pair 和 existing-current no-op 没有回退，还没锁住“use block 已有前缀 op”这个具体缺口。
- 做什么：在 `test/passes/memory/test_multi_buffer.py` 新增/调整边界测试，覆盖 prefix op、suffix op、terminator、existing-current no-op 与 direct-use loop-local 场景。
- 不做什么：不直连非公开 helper，不新增 expectation 测试，不改 pipeline 口径。
- 怎么验收：`pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py` 通过，且新测试能在 boundary 口径回退时失败。
- 卡住问谁：需要断言内部 helper 时问架构师；需要改公开 API 时问用户。
- 模块范围：`test/passes/memory/test_multi_buffer.py`
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`。
- 合同真源：`spec/pass/memory/multi_buffer.md > pytest > 当前实现`
- 最小功能闭环：prefix / suffix / terminator 边界都能稳定验证 current / advance 位置。
- 执行步骤：
  1. 在 `test/passes/memory/test_multi_buffer.py` 用公开 `MultiBufferPass` / `MultiBufferAnalysisPass` / `MultiBufferApplyPass` 入口构造 direct-use loop-local case，不直接调用实现文件私有 helper。
  2. 构造 use block 已有前缀 op 的 case，断言 `dma.current_ring` 的 index 小于该前缀 op index，且 consumer 使用 current slot。
  3. 构造 use 后已有 suffix op 或 terminator 的 case，断言 `dma.advance_ring` 位于 suffix 后或 terminator 前。
  4. 保留 / 补强 existing-current no-op case，断言已有 `dma.current_ring` 时不重复 `dma.make_ring/current_ring/advance_ring`，不删除原 alloc/free，不清理 analysis attrs。
  5. 让新增测试在 current 回退到前缀后、advance 回退到 suffix 前或 existing-current 被重复 ring 化时失败。
- 验收与记录要求：
  - 运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`，记录 exit code 和通过数。
  - 记录新增 / 修改测试名和每个测试覆盖的边界。
  - 记录测试未直连当前文件外非公开 API；若必须新增测试 helper，只能放在同一测试文件内且符合函数注释规范。

### S3. 复跑 pytest / pipeline / 动态脚本

- 为什么做：direct-use 修复必须用公开测试和脚本验证，不靠 local-only expectation 代替。
- 做什么：复跑 memory/registry pytest、pipeline pytest、dynamic matmul 脚本、private/KCE 门禁和 diff 反推检查。
- 不做什么：不把 local-only expectation 计入 diff 反推测试，不把它当作必过合同。
- 怎么验收：上述命令退出码 0，且 diff 反推审查能说明 current/advance 的绝对位置已收口。
- 卡住问谁：脚本失败涉及非本计划范围时问架构师；任务链状态问管理员。
- 模块范围：`test/passes/**`、`kernel/matmul/**`
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`
- 合同真源：`spec > pytest > 当前实现`
- 最小功能闭环：公开测试与脚本都能证明 direct-use 边界已收口。
- 执行步骤：
  1. 运行 memory / registry pytest，验证 pass family 和 registry option 未回退。
  2. 运行 pipeline pytest，验证 npu-demo-lowering 仍按 split 顺序和 memory-pool 后续顺序通过。
  3. 运行 dynamic matmul 脚本，验证 dump 生成链路未被 direct-use 修复破坏。
  4. 运行 private API boundary 与 KCE static gate，验证没有跨文件非公开 API 和稳定错误文本问题。
  5. 运行 `git diff --check` 与 `git diff --cached --check`；按最终 diff 额外补充必要 pytest / 脚本。
- 验收与记录要求：
  - 必过命令：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
  - `expectation/pass/multi_buffer/**` 不作为本卡必过；若运行可选本地诊断，必须单列“可选诊断”，失败不阻断。
  - 任务记录必须写 `Diff 反推自测`，说明每个改动文件由哪些 pytest / 脚本覆盖。

### S4. 记录闭环并准备复审

- 为什么做：计划级 execute 必须把实现、测试、验收和记录闭合到可复审状态。
- 做什么：补齐任务记录中的执行前阅读、Diff 反推自测、验收结果、expectation staged 空核对和自检结论；若运行 local-only expectation 诊断，再单列诊断记录。
- 不做什么：不推进 archive_acceptance，不替管理员改状态，不修改 expectation 本体。
- 怎么验收：任务记录能直接说明当前结论、失败边界和下一步。
- 卡住问谁：任务状态和流转问管理员。
- 模块范围：当前计划对应 task record。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`。
- 合同真源：根 `AGENTS.md`、`agents/standard/任务记录约定.md`、本计划。
- 最小功能闭环：记录足以支撑 review / archive_acceptance 复核。
- 执行步骤：
  1. 在任务记录 `agents/codex-multi-agents/log/task_records/2026/24/20260610-multi-buffer-analysis-apply-split.md` 追加执行前阅读、恢复门禁核对、禁止修改面和当前基线。
  2. 记录 S1/S2 的实现与测试改动、S3 的必过命令结果、Diff 反推自测、减法检查和自检。
  3. 记录 `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py` 为空，证明 expectation 未进入 staged / merge candidate。
  4. 若运行 local-only expectation 诊断，只记录 `actual / expected / spec / verdict`，并明确它不是必过验收。
  5. 完成后按标准脚本流转到 `review`，不得进入 `archive_acceptance` 或 `merge`。
- 验收与记录要求：
  - 任务记录必须包含 `Diff 反推自测`、必过命令结果、private/KCE 门禁结果、敏感范围核对和自检。
  - 任务记录必须说明 execute 未修改、移动、删除、提交 `expectation/`。
  - 流转记录必须包含完整 `-next -type review -auto` 命令、输出、TODO/agents-list/talk 复查和自检。

## 计划自检与返工口径

- 自检：本计划已把用户最新 local-only expectation 口径从计划级必过和远程候选中移除，只保留为诊断参考。
- 自检：公开 API 沿用 2026-06-10 已确认的 split 口径，本轮不再新增 API。
- 自检：剩余实现阻断收敛到 direct-use current 插入边界和对应 pytest 有效性。
- 自检：验收命令分清 pytest / 脚本 / private-KCE 与 local-only expectation 诊断，未把 expectation 写成 diff 反推测试。
- 当前未完成项：等待管理员按恢复门禁恢复既有暂停任务 `T-20260610-c415f4aa`。
- 返工口径：只要 strict review、守护最终检验、review 或 archive_acceptance 仍能指出影响公开行为、测试有效性、维护性或验收可信度的可执行项，就不得通过。

## 待确认项

- 无。

## 用户确认来源

- 2026-06-10 用户确认拆分为 analysis/apply 两个 pass。
- 2026-06-10 用户确认公开 class 与参数归属：`MultiBufferAnalysisPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`、`MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`、`MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`。
- 2026-06-10 用户确认 registry pass name：`multi-buffer-analysis`、`multi-buffer-apply`、兼容保留 `multi-buffer`；并确认 package re-export 到 `kernel_gen.passes.memory` 与 `kernel_gen.passes`。
- 2026-06-10 用户确认公开 `from_options(...)`、默认值和稳定错误语义按计划口径收口：`memory_stage must be positive`、`memory_stage must be integer`、`target must be non-empty`、`unknown option: <name>`、`memory-stage must be integer`、`memory-stage must be positive`、`alignment must be non-negative integer`，registry 用 `PassRegistryError` 包装。
- 2026-06-10 用户确认 analysis 只保留使用点、更新点、num 三项临时属性。
- 2026-06-10 用户确认 apply 根据 num 更新 alloc，并在对应使用点最前面插入 current、最后面插入 advance。
- 2026-06-10 用户确认 `alignment` 选项名和默认值 `1024`。
- 2026-06-12 用户明确要求：`expectation/pass/multi_buffer` 只做本地-only 参考，不进入计划级远程候选，不作为 execute 必过项。
