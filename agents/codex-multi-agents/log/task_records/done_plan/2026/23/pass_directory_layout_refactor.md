# pass directory layout refactor 计划书 Draft 5

## 文档信息

- 计划用途：把 `kernel_gen/passes` 中仍散落在根目录或非目标 family 的 pass，按用户给出的目录草图收口到 `arch / kernel / memory / tuning` 四类目录；同步 `spec/pass` 与 `test/passes` 的目录结构；顺带对迁移触达的 pass 实现做小范围规范化重构。
- 当前状态：Draft 5 为 `T-20260607-3318f2e2 / pass-directory-layout-refactor` execute 期 latest-main 删除事实裁定修订。Draft 1 已经两路 subagent strict review，结论均为不通过；Draft 2 已按审阅意见收窄公开 API 口径、修正真实签名、补齐迁移矩阵和 expectation 策略；Draft 3 已从用户指定草案 `plan/1.md` 迁移为正式计划文件 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`；Draft 3-R1 两路 subagent strict review 均通过并通过守护最终检验；Draft 4 仅调整当前必过 expectation 验收口径；Draft 5 按 `origin/main=81d753329a66ed338b846785622407f4a3e0554d` 已删除 `LaunchKernelCostFuncPass` 的事实，移除 / 降级 `launch_kernel_cost_func` 相关实现、spec、test 和 API 目标引用，不恢复已删除公开面。
- 用户确认来源：2026-06-07 用户要求：“出一个计划书，`/home/lfr/kernelcode_generate/plan/1.md`。按照她重构文件目录，同时 spec 和 test 也需要。另外可以看一下 pass 的实现，稍微重构让代码更规范一点。”
- 计划文件位置：`ARCHITECTURE/plan/pass_directory_layout_refactor.md`。`plan/1.md` 是用户指定的临时草案来源；正式下发、审阅和守护均以本文件为准。
- 目标 `spec`：
  - `spec/pass/registry.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/arch/arch_parallelize.md`
  - `spec/pass/arch/attach_arch_information.md`
  - `spec/pass/kernel/kernel_aggregate.md`
  - `spec/pass/kernel/kernel_decompose.md`
  - `spec/pass/memory/memory_plan.md`
  - `spec/pass/memory/memory_pool.md`
  - `spec/pass/memory/multi_buffer.md`
  - `spec/pass/tuning/dma_memory_hierarchy.md`
  - `spec/pass/tuning/kernel_pattern_attach.md`
  - `spec/pass/tuning/transform_apply.md`
  - `spec/pass/tuning/outline_device_kernel.md`
- 目标 `API`：
  - 不修改任何 pass class 构造签名、`Pass.name`、registry pass name、pipeline name、pass option、返回值或稳定错误文本。
  - 新增 canonical module import path：
    - `kernel_gen.passes.arch.arch_parallelize`
    - `kernel_gen.passes.arch.attach_arch_information`
    - `kernel_gen.passes.kernel.kernel_aggregate`
    - `kernel_gen.passes.kernel.kernel_decompose`
    - `kernel_gen.passes.memory.memory_plan`
    - `kernel_gen.passes.memory.memory_pool`
    - `kernel_gen.passes.memory.multi_buffer`
    - `kernel_gen.passes.tuning.outline_device_kernel`
  - 明确不恢复已退场旧路径：
    - `kernel_gen.passes.dma_memory_hierarchy`
    - `kernel_gen.passes.kernel_pattern_attach`
    - `kernel_gen.passes.transform_apply`
  - 保留既有 public import path 作为兼容 shim，不在本计划删除：
    - `kernel_gen.passes.arch_parallelize`
    - `kernel_gen.passes.arch_parallelize.arch_parallelize`
    - `kernel_gen.passes.attach_arch_information`
    - `kernel_gen.passes.kernel_aggregate`
    - `kernel_gen.passes.kernel_decompose`
    - `kernel_gen.passes.memory_plan`
    - `kernel_gen.passes.memory_pool`
    - `kernel_gen.passes.multi_buffer`
    - `kernel_gen.passes.outline_device_kernel`
  - `from kernel_gen.passes import ...` package root re-export 保持当前公开行为。
- 目标 `test`：
  - `test/passes/test_registry.py`
  - `test/passes/test_pass_manager.py`
  - `test/passes/test_pattern_public_api_docs.py`
  - `test/passes/arch/test_arch_parallelize.py`
  - `test/passes/arch/test_attach_arch_information.py`
  - `test/passes/kernel/test_kernel_aggregate.py`
  - `test/passes/kernel/test_kernel_decompose.py`
  - `test/passes/memory/test_memory_plan.py`
  - `test/passes/memory/test_memory_pool.py`
  - `test/passes/memory/test_multi_buffer.py`
  - `test/passes/tuning/test_dma_memory_hierarchy.py`
  - `test/passes/tuning/test_kernel_pattern_attach.py`
  - `test/passes/tuning/test_transform_apply.py`
  - `test/passes/tuning/test_outline_device_kernel.py`
  - pipeline 回归：`test/passes/pipeline/test_default_lowering.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/passes/pipeline/test_cuda_sm86_lowering.py`
- 当前只读 `expectation` 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.arch_parallelize`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.attach_arch_information`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_aggregate`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_decompose`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_pool`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy.basic`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_pattern_attach`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.transform_apply`
- 当前不列为必过的历史 / 共享 expectation 基线冲突：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.default_lowering` 当前在 latest main 失败，原因为 `expectation/pass/pipeline/default_lowering.py` 导入已退场旧路径 `kernel_gen.passes.dma_memory_hierarchy`，而 `spec/pass/registry.md` 当前明确该路径应稳定失败。本计划不修改 `expectation/`，也不恢复该已退场旧路径；除非用户或架构师另行确认，否则该入口只作为当前基线冲突记录，不作为本计划必过资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering` 当前共享 expectation 期望 `npu-demo-lowering` 在 pipeline 中接入 `multi-buffer:memory_stage=2:target=npu_demo`；本计划只做 pass 目录 / spec / test 重构，明确不改变 `npu-demo-lowering` 阶段顺序、不接入 `multi-buffer`、不新增 pipeline option，因此该入口作为共享 expectation 合同漂移记录，不作为本计划必过资产。pipeline pytest 仍为本计划必过回归。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy` 当前在 latest main 失败，原因为其聚合入口会运行 `matmul_apply`，而 `matmul_apply` 的 `matmul-out-copy`、`matmul-all-operands-copy`、`matmul-tlm-family-copy` 三个 case 当前失败；对应公开 pytest `test/passes/test_dma_memory_hierarchy.py` 当前通过。本计划只做目录重构，不修改 `expectation/` 或 `lower-dma-memory-hierarchy` 行为，因此该聚合入口只作为当前基线冲突记录，不作为必过资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy.matmul_apply` 当前同上失败；本计划只把 `expectation.pass.dma_memory_hierarchy.basic` 列为当前必过合同验收。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer` 当前共享 expectation 的 `matmul_ring_memory_stage` 仍匹配三操作数 `dma.make_ring(memory,num,offset)`；本计划不修改 `dma.make_ring` / `DmaMakeRingOp` 公开合同，不回退也不前推 API，相关 API 调整归属其它专题计划，因此该入口作为共享 expectation 合同漂移记录，不作为本计划必过资产。
- 目标 `功能实现`：
  - `kernel_gen/passes/__init__.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/arch/__init__.py`
  - `kernel_gen/passes/arch/arch_parallelize.py`
  - `kernel_gen/passes/arch/attach_arch_information.py`
  - `kernel_gen/passes/kernel/__init__.py`
  - `kernel_gen/passes/kernel/kernel_aggregate.py`
  - `kernel_gen/passes/kernel/kernel_decompose.py`
  - `kernel_gen/passes/memory/__init__.py`
  - `kernel_gen/passes/memory/memory_plan.py`
  - `kernel_gen/passes/memory/memory_pool.py`
  - `kernel_gen/passes/memory/multi_buffer.py`
  - `kernel_gen/passes/tuning/dma_memory_hierarchy.py`（实现已在目标 family，仅更新关联路径）
  - `kernel_gen/passes/tuning/kernel_pattern_attach.py`（实现已在目标 family，仅更新关联路径）
  - `kernel_gen/passes/tuning/transform_apply.py`（实现已在目标 family，仅更新关联路径）
  - `kernel_gen/passes/tuning/outline_device_kernel.py`
  - 兼容 shim：
    - `kernel_gen/passes/arch_parallelize/__init__.py`
    - `kernel_gen/passes/arch_parallelize/arch_parallelize.py`
    - `kernel_gen/passes/{attach_arch_information,kernel_aggregate,kernel_decompose,memory_plan,memory_pool,multi_buffer,outline_device_kernel}.py`
- `expectation/` 授权：本计划默认不新增、不修改 `expectation/`；只读取和运行当前已有合同资产。若 execute 发现 expectation 本体必须修改，必须暂停并回用户 / 架构师确认。

## 计划级任务

- 计划级任务目标：按 `plan/1.md` 用户目录草图把 pass 实现、spec 和 pytest 收口到 `arch / kernel / memory / tuning` family 目录；保留旧公开 import path 兼容 shim；同步 registry、pipeline、文档、pytest 与只读 expectation 验收；对迁移触达的 pass 做小范围规范化重构，使实现文件说明、API 列表、private helper 与跨文件调用符合仓库规范。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance / 计划书入档验收 -> merge/归档`。
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`；不得另建独立 `refactor` 阶段绕过计划级任务。
- 当前下发前置：Draft 3-R1 subagent strict review 已收敛；`守护最好的爱莉希雅` 守护最终检验已通过；正式计划迁移到 `ARCHITECTURE/plan/` 并进入 index。Draft 4 execute 期 expectation 验收口径修订已完成两路 strict review 与守护复验；Draft 5 latest-main 删除事实修订需完成两路 strict review 与守护复验后，管理员才可恢复已暂停的唯一计划级 `execute`；本计划回写不直接创建任务。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `pass-directory-layout-refactor` | `execute` | 管理员下发的新独立 worktree | `agents/codex-multi-agents/log/task_records/2026/<week>/YYYYMMDD-pass-directory-layout-refactor.md` |

## 迭代审阅记录

### 收敛轮次 1：subagent strict review

- 审阅对象：Draft 1 全文。
- 输入标准包：
  - 根 `AGENTS.md`
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/任务记录约定.md`
  - Draft 1 全文
  - 用户确认来源
  - 禁止修改面
  - 必过 pytest / expectation / 文本门禁命令
- 严格通过口径：无未确认公开 API 变更；目录迁移矩阵完整；spec/test 目录镜像可执行；旧 import shim 兼容策略明确；实现规范化范围可控且不会演变成语义重写；验收命令覆盖 registry、pipeline、compat import、canonical import、expectation 只读合同；仍有可执行的可读性、可维护性、测试有效性或边界完整性返工项则不得通过。
- 审阅任务：
  - `Dalton / 019e9dba-5a8d-7c51-90b6-a6ece4d4dd61`：不通过。
  - `Huygens / 019e9dba-8677-7263-b141-fe49f7daedd6`：不通过。
- 发现问题：
  1. Draft 1 把“按草图重构目录”直接写成新增 canonical import path 与 `__module__` 迁移确认，公开 API 确认来源不够明确。
  2. Draft 1 将 `producer_consumer_analysis` 放入 `memory` family，超出用户草图列出的 memory pass 范围。
  3. Draft 1 的公开 API 列表存在错误签名 / 默认值，且未列 class 公开 `apply(...)` 方法。
  4. `arch_parallelize` 旧路径当前是 package root 和内部子模块，Draft 1 把它写成普通 root `.py` shim，不可直接执行。
  5. Draft 1 expectation 合同验收不完整，并误把当前基线失败的 `expectation.pass.pipeline.default_lowering` 列为必过。
  6. Draft 1 的 AST shim 检查仍是占位命令；S1-S4 的验收命令不够具体；敏感目录门禁漏列 `plan/` / `ARCHITECTURE/plan/`。
- 主线处理：
  - 采纳 1：Draft 2 明确新增 canonical import path 是用户目录重构需求的一部分，但旧 direct path 删除和已退场旧 tuning path 恢复均不在本计划；`__module__` 指向新 canonical path 写为完成态并保留旧 path object identity compat。
  - 采纳 2：Draft 2 移除 `producer_consumer_analysis` 迁移范围；该 pass 仍保持 root-level，除 registry / pipeline import 不受本计划触达。
  - 采纳 3：Draft 2 用当前实现 introspection 结果修正 API 列表，补齐 `apply(...)`。
  - 采纳 4：Draft 2 单列 `kernel_gen/passes/arch_parallelize/__init__.py` 与 `kernel_gen/passes/arch_parallelize/arch_parallelize.py` 兼容策略。
  - 采纳 5：Draft 2 补齐相关 expectation 入口；`default_lowering` expectation 记录为 latest main 既有冲突，不列必过。
  - 采纳 6：Draft 2 补真实可执行静态门禁，并在敏感目录门禁中加入 `plan/1.md` 和正式计划路径。
- 状态：已按 Draft 1-R1 修订为 Draft 2，需发起下一轮 strict review。

### 收敛轮次 2：Draft 3 subagent strict review

- 审阅对象：`ARCHITECTURE/plan/pass_directory_layout_refactor.md` Draft 3 全文。
- 输入标准包：
  - 根 `AGENTS.md`
  - 当前 Codex 计划负责人上下文与用户确认来源
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/任务记录约定.md`
  - `agents/standard/审查规范.md`
  - Draft 1 审阅问题与 Draft 2 主线处理摘要
  - Draft 3 正式计划全文
  - 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、本正式计划文件
  - 必过 pytest / expectation / 文本门禁命令
- 严格通过口径：无未确认公开 API 变更；新增 canonical import path 与旧 compat shim 口径可执行；迁移矩阵与当前真实代码目录一致；spec/test 目录镜像和验收命令自洽；`expectation/` 只读策略明确；小任务卡均单列合同验收；仍有可执行的可读性、可维护性、测试有效性或边界完整性返工项则不得通过。
- 本地基线核对：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py test/passes/test_pattern_public_api_docs.py`：84 passed, 1 warning。
  - 当前真实 class / method 签名已用 `inspect.signature` 核对，`MultiBufferPass(memory_stage: int = 3, fold: bool = True, target: str | None = None)` 与 latest main 一致。
  - 当前必过只读 expectation 已抽样 / 分批核对：`npu_demo_lowering`、`arch_parallelize`、`attach_arch_information`、`kernel_aggregate`、`kernel_decompose`、`memory_plan`、`memory_pool`、`multi_buffer`、`outline_device_kernel`、`dma_memory_hierarchy.basic`、`kernel_pattern_attach`、`transform_apply` 均通过。
  - 当前非必过基线冲突已核对：`expectation.pass.pipeline.default_lowering` 失败于已退场旧路径 `kernel_gen.passes.dma_memory_hierarchy`；`expectation.pass.dma_memory_hierarchy` / `expectation.pass.dma_memory_hierarchy.matmul_apply` 失败于 `matmul-out-copy`、`matmul-all-operands-copy`、`matmul-tlm-family-copy` 三个 existing case。
  - `git diff --check -- ARCHITECTURE/plan/pass_directory_layout_refactor.md`：通过。
  - `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md ARCHITECTURE/plan/pass_directory_layout_refactor.md`：无输出。
  - 本地基线回写前计划 sha256：`639621d781d1698f600be9be28cd2cf9622632213453515dcb5da1d28d6ff366`；计划文件自身 sha 不作为稳定合同基线。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：通过。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过。
- 发现问题：无阻断、无最小需改项、无待用户确认项。
- 主线处理：
  - Draft 3-R1 在审阅期间补强 S1-S3 的逐卡 `expectation` 合同验收文本；不改变公开 API、迁移范围或 `expectation` 授权。
  - Kierkegaard 核对公开 API、迁移矩阵与 `expectation` 基线，确认新增 canonical import path 与旧 compat shim 分工自洽，已退场旧路径未被误恢复，当前必过 / 非必过 expectation 口径自洽。
  - Ptolemy 核对流程门禁、小任务卡与验收口径，确认 S1-S5 五行短口径和详细字段一致，`expectation` 与 diff 反推 pytest 分开，当前态未出现“待审 / 待守护 / 可下发”冲突。
- 状态：两路 strict review 均已收敛；允许进入守护最终检验。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：最终状态通过；无阻断、无最小需改项、无待确认项；允许进入守护最终检验。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：最终状态通过；无阻断、无最小需改项、无待确认项；允许进入守护最终检验。
- 收敛结论：Draft 3-R1 已满足 subagent strict review 收敛口径并通过 `守护最好的爱莉希雅` 守护最终检验；Draft 4 execute 期验收口径修订已完成 Kierkegaard 与 Ptolemy 两路 strict review 和守护复验；Draft 5-R1 latest-main 删除事实修订已完成 Kierkegaard 与 Ptolemy 两路 strict review，均无阻断、无最小需改项、无待用户确认项。
- 遗留项：Draft 5-R1 正等待守护复验。未来 `execute` / `review` / `archive_acceptance` 仍需按实际 diff 反推 pytest、只读 expectation 合同验收和任务记录。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅`。
- 当前状态：已完成。
- 必过门禁：所有已发起或计划要求的 subagent strict review 均无阻断、无最小需改项、无待确认项；用户待决策项为无；本计划不越权修改 `expectation/`；正式下发前计划位置符合 `ARCHITECTURE/plan/` 规则。
- 结论：通过；阻断项=无；最小需改项=无；待确认项=无。
- 回执来源：`agents/codex-multi-agents/log/talk.log:11261`，2026-06-07，`守护最好的爱莉希雅` 向 `大闸蟹` 发起会话。
- 守护检验对象摘要：
  - 检验对象计划 sha256：`fc651728dbf8bda551d61515494324bcf38882acda57044e6e6e4258f1cb07f2`。
  - 正式计划已进入 index，`git ls-files --stage -- ARCHITECTURE/plan/pass_directory_layout_refactor.md` 为 `100644 6b29abd0a095b9636de9bdb37f432828f5b9b9fe 0 ARCHITECTURE/plan/pass_directory_layout_refactor.md`。
  - `git diff --cached --name-status -- ARCHITECTURE/plan/pass_directory_layout_refactor.md` 为 `A ARCHITECTURE/plan/pass_directory_layout_refactor.md`。
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d` 与 `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1` 两路 subagent strict review 均通过，且无阻断、无最小需改项、无待确认项。
  - 用户确认来源已记录为 2026-06-07 按 `plan/1.md` 草图重构 pass 目录并同步 spec/test、顺带小范围规范化 pass 实现。
  - 公开 API 口径为新增 canonical import path、保留旧 public import path compat shim、不恢复已退场 tuning 旧路径。
  - Draft 3 守护检验时 `expectation/` 只读；当时必过 12 个 expectation 入口均通过；`pipeline.default_lowering`、`dma_memory_hierarchy` 聚合与 `matmul_apply` 明确为非必过基线冲突。Draft 4 当前执行期口径见下节。
  - 敏感范围 `.skills`、`expectation`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 无 tracked / staged diff。
  - S1-S5 小任务卡可执行，且 diff 反推 pytest 与合同验收分列。
- 守护结论：允许通知管理员创建唯一计划级 `execute`；`守护最好的爱莉希雅` 不直接下发、不创建任务、不通知管理员。

### execute 期验收口径修订：Draft 4

- 触发来源：`T-20260607-3318f2e2 / pass-directory-layout-refactor` execute 阶段报告计划原列 12 个只读 expectation 中有 2 个与当前共享 expectation 合同漂移冲突；管理员暂停任务并要求计划负责人修订正式计划。
- 架构裁定：选择 A，具体为修订本计划验收口径，不由本任务修改 `expectation/`。本计划仍不改变 `npu-demo-lowering` pipeline、不接入 `multi-buffer`、不新增 pipeline option、不回退或前推 `dma.make_ring` / `DmaMakeRingOp` 公开合同。
- 用户 / 守护同步：2026-06-07 用户确认 `npu-demo-lowering pipeline` 不作为本计划必过 expectation；`守护最好的爱莉希雅` 已撤回“可直接继续 execute”表述，并确认最终以“先修订正式计划、两路 strict review 与守护复验通过后再恢复 execute”为准。
- 主线处理：
  - `expectation.pass.pipeline.npu_demo_lowering` 从当前必过只读 expectation 移入共享 expectation 基线冲突记录；该入口当前要求 `multi-buffer:memory_stage=2:target=npu_demo`，属于其它专题范围，不作为本目录重构计划阻断。
  - `expectation.pass.multi_buffer` 从当前必过只读 expectation 移入共享 expectation 基线冲突记录；其 `matmul_ring_memory_stage` 当前仍匹配三操作数 `dma.make_ring(memory,num,offset)`，不作为本目录重构计划阻断。
  - 当前必过只读 expectation 由 12 项收为 10 项；pipeline pytest 仍包含 `test/passes/pipeline/test_npu_demo_lowering.py`，用于回归当前 `npu-demo-lowering` 行为未被目录迁移破坏。
- review 必查项：复核两项 expectation 失败确实分别来自 `multi-buffer` pipeline 阶段要求与三操作数 `make_ring` 旧合同，且不是目录迁移 diff、import shim 或 registry 破坏；复核剩余 10 项 expectation 与 pytest / 文本门禁通过。
- 待用户确认项：无。若后续要改 pipeline 行为、`dma.make_ring` / `DmaMakeRingOp` API 或 `expectation/` 本体，则必须另行取得用户确认。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：通过；阻断项无、最小需改项无、待确认项无。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过；阻断项无、最小需改项无、待确认项无。
- 审阅证据摘要：
  - 两路均核对 Draft 4 当前必过 expectation 已收为 10 项，未包含 `expectation.pass.pipeline.npu_demo_lowering` 或 `expectation.pass.multi_buffer`。
  - 两路均确认上述两项已移入非必过 / 共享 expectation 基线冲突记录，且正文明确不改 pipeline、不接入 `multi-buffer`、不调整 `dma.make_ring` / `DmaMakeRingOp` 合同。
  - 两路均确认 pipeline pytest 回归仍保留，且本轮无新增公开 API、无新增 expectation 授权、无待用户确认项。
- 当前状态：Draft 4 strict review 与守护复验均已通过；管理员已按 Draft 4 口径恢复过 `T-20260607-3318f2e2` execute。后续恢复前置以 Draft 5 当前状态为准。

### execute 期 latest-main 删除事实修订：Draft 5

- 触发来源：`T-20260607-3318f2e2 / pass-directory-layout-refactor` execute 阶段快进并重放到 `origin/main=81d753329a66ed338b846785622407f4a3e0554d` 后报告：latest main 已删除 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`spec/pass/tuning/launch_kernel_cost_func.md`、`test/passes/tuning/test_launch_kernel_cost_func.py`，而 Draft 4 正文仍把这些文件与 `LaunchKernelCostFuncPass` API 列入目标范围。
- 架构裁定：选择 A，按 latest main 删除事实修订本计划；本目录重构计划不恢复 `LaunchKernelCostFuncPass`，不恢复其实现、spec、test 或公开 API 文档，不把它列入迁移 / 验收范围。
- 主线处理：
  - 从目标 `spec`、目标 `test`、目标 `功能实现` 中移除 `launch_kernel_cost_func` 三个已删除文件。
  - 从实现 / spec / test 迁移矩阵中移除 `launch_kernel_cost_func` 的“已在目标目录，只核对引用”行。
  - 从公开 API 快速索引中移除 `LaunchKernelCostFuncPass(...)`、`from_options(...)`、`apply(...)` 条目。
  - 在当前基线中记录 `origin/main=81d753329a66ed338b846785622407f4a3e0554d` 已删除该 pass；若未来需要恢复该已删除公开面，必须另行取得用户确认并新建对应计划。
- review 必查项：复核 execute 未恢复 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`spec/pass/tuning/launch_kernel_cost_func.md`、`test/passes/tuning/test_launch_kernel_cost_func.py`；复核 `kernel_gen/passes/tuning/__init__.py` 保持 latest main 删除 `LaunchKernelCostFuncPass` 的事实，不新增该 class re-export；复核 registry / docs / pytest 未重新要求该 pass。
- 待用户确认项：无。本修订是收缩本计划范围以尊重 latest main 已删除事实；若要恢复该 pass 或其公开 API，必须另行取得用户确认。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：Draft 5 初审通过；Draft 5-R1 记录当前态修订后复核通过；阻断项无、最小需改项无、待确认项无。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：Draft 5 初审不通过，唯一阻断为末尾当前态仍写“可通知创建 execute”；Draft 5-R1 已按最小需改项修正并复核通过；阻断项无、最小需改项无、待确认项无。
- 审阅证据摘要：
  - 两路均核对 `launch_kernel_cost_func` / `LaunchKernelCostFuncPass` 未出现在目标 spec/test/功能实现、迁移矩阵、公开 API 索引或验收命令中；仅保留在 Draft 5 修订记录、latest-main 删除事实、review 必查项和 S3 非目标说明中。
  - 两路均确认正文记录 `origin/main=81d753329a66ed338b846785622407f4a3e0554d` 已删除三个文件，本计划不恢复实现/spec/test/API，未来恢复需另行用户确认。
  - 两路均确认 Draft 4 expectation 口径、pipeline 禁止面、`dma.make_ring` / `DmaMakeRingOp` 禁止面保持不变；本轮为范围收缩，无新增用户确认项。
  - Ptolemy 复核确认 `:111`、`:246`、`:752` 当前态已统一为 Draft 5 strict review + 守护复验通过后才可恢复暂停 execute，不再存在“待审 / 待守护 / 可下发”冲突。
- 当前状态：Draft 5-R1 strict review 已收敛；正等待守护复验。守护复验通过前管理员不得恢复 `T-20260607-3318f2e2` execute。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：待计划级 `execute` 完成后由计划书入档验收角色填写。
- 结论：待填写。
- 验证基线：待填写。
- 执行目录：待填写。
- 同步结果：待填写。
- 合同验收摘要：待填写。
- 最小阻断项或通过摘要：待填写。

## 计划目标

- 把 pass 文件目录从“部分 root-level、部分 family 子包”的混合状态，收口为可预测的 `arch / kernel / memory / tuning` 分类。
- 让 `spec/pass` 与 `test/passes` 目录跟随同一分类，降低新 pass 查找、审查和维护成本。
- 保留 registry pass name、pipeline 顺序、class 构造签名、package root re-export 和旧 direct import path，不把目录重构变成行为 breaking change。
- 让 `registry.load_builtin_passes()`、pipeline builder、测试和工具层全部使用新的 canonical import path。
- 旧 direct import path 只作为薄兼容 shim：不得承载业务逻辑、不得新增隐藏 helper、不得复制实现。
- 对迁移触达的 pass 做有限实现规范化：
  - 更新文件级 `功能说明 / API 列表 / 使用示例 / 关联文件`。
  - 删除过期路径描述、重复 import、未使用代码和明显浅 wrapper。
  - 新建 / 改动 private callable 必须不少于 5 行有效代码，且不得调用其它 private callable。
  - 不改变 IR 改写语义、错误文本、Pass option、registry 行为或 pipeline 阶段顺序。

## 当前基线

- `plan/1.md` 当前只有用户目录草图：
  - `passes/arch/{arch_parallelize, attach arch information}`
  - `passes/kernel/{kernel_aggregate, kernel decompose}`
  - `passes/memory/{memory pool, memory plan, multi buffer}`
  - `passes/tuning` 新加并包含 `outline device kernel`
- 当前实现目录：
  - 已有 family 子包：`kernel_gen/passes/hoist`、`kernel_gen/passes/tile`、`kernel_gen/passes/template_name`、`kernel_gen/passes/tuning`、`kernel_gen/passes/lowering/nn_lowering`。
  - 仍在 root-level 的 pass：`attach_arch_information.py`、`buffer_results_to_out_params.py`、`decompass.py`、`inline.py`、`kernel_aggregate.py`、`kernel_decompose.py`、`memory_plan.py`、`memory_pool.py`、`multi_buffer.py`、`outline_device_kernel.py`、`producer_consumer_analysis.py`。
  - `arch_parallelize` 目前是 `kernel_gen/passes/arch_parallelize/arch_parallelize.py`，不在用户草图的 `arch` family。
  - `producer_consumer_analysis.py` 不在用户草图列出的 memory pass 范围内，Draft 2 不迁移该文件。
- 当前 spec 目录：
  - 多数 root-level pass 的 spec 位于 `spec/pass/<name>.md`。
  - `memory_pool` 当前 spec 位于 `spec/pass/lowering/memory_pool.md`，与实现 `kernel_gen/passes/memory_pool.py` 分类不一致。
  - `dma_memory_hierarchy` 当前 spec 位于 `spec/pass/lowering/dma_memory_hierarchy/spec.md`，但实现已在 `kernel_gen/passes/tuning/dma_memory_hierarchy.py`。
- 当前 test 目录：
  - 多数 pass pytest 位于 `test/passes/test_<name>.py`。
  - `tile` 和 `lowering/nn_lowering` 已有子目录测试。
- latest-main 删除事实：
  - `origin/main=81d753329a66ed338b846785622407f4a3e0554d` 已删除 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`spec/pass/tuning/launch_kernel_cost_func.md` 与 `test/passes/tuning/test_launch_kernel_cost_func.py`。
  - 本目录重构计划不恢复 `LaunchKernelCostFuncPass`、不恢复其 spec/test/API 文档、不把它列入迁移或验收范围；若未来要求恢复该已删除公开面，必须另行取得用户确认并新建对应计划。
- 当前公开路径与消费者：
  - `spec/pass/registry.md` 将 `kernel_gen.passes.memory_plan`、`kernel_gen.passes.memory_pool`、`kernel_gen.passes.multi_buffer`、`kernel_gen.passes.outline_device_kernel`、`kernel_gen.passes.kernel_aggregate`、`kernel_gen.passes.kernel_decompose` 等列为 canonical public path。
  - `kernel_gen/pipeline/default_lowering.py`、`kernel_gen/pipeline/npu_demo_lowering.py`、`kernel_gen/pipeline/cuda_sm86_lowering.py` 直接导入多个 root-level pass；本计划只更新迁移范围内的 import，`producer_consumer_analysis` 保持旧路径。
  - `expectation/pass/pipeline/npu_demo_lowering.py`、`expectation/pass/memory_pool/invalid.py`、`expectation/pass/outline_device_kernel/invalid_attr.py` 等只读合同资产仍导入旧 direct path，本计划通过 compat shim 保持可用。
  - `expectation/pass/pipeline/default_lowering.py` 当前导入已退场旧路径 `kernel_gen.passes.dma_memory_hierarchy`，latest main 运行失败；`spec/pass/registry.md` 当前把该旧路径列为稳定失败旧路径。本计划不恢复该旧路径，不把该 expectation 作为当前必过资产。
  - `expectation/pass/pipeline/npu_demo_lowering.py` 当前共享 expectation 已漂移为期望 `npu-demo-lowering` 接入 `multi-buffer:memory_stage=2:target=npu_demo`；本计划不改 pipeline 行为，因此该入口不作为本计划必过 expectation。
  - `expectation/pass/dma_memory_hierarchy/__main__.py` 当前聚合入口会运行失败的 `matmul_apply` leaf；latest main 下 `expectation.pass.dma_memory_hierarchy.basic` 通过，`expectation.pass.dma_memory_hierarchy.matmul_apply` 失败。本计划不修改 `lower-dma-memory-hierarchy` 行为或 expectation，本轮只把 `basic` leaf 作为当前必过资产。
  - `expectation/pass/multi_buffer` 当前共享 expectation 中的 `matmul_ring_memory_stage` 仍匹配三操作数 `dma.make_ring(memory,num,offset)`；本计划不改变 `dma.make_ring` / `DmaMakeRingOp` 公开合同，因此 `expectation.pass.multi_buffer` 不作为本计划必过 expectation。
  - `test/passes/test_registry.py` 明确断言若干 pass 的 `__class__.__module__` 为旧路径；执行时必须同步改为新 canonical path，同时另补旧 path shim import 测试。
- 当前实现规模：
  - `kernel_gen/passes/memory_pool.py` 约 2567 行，属于本计划最大风险文件；本计划只允许目录迁移、文件说明 / import / helper 规范化和可证明等价的小重构，不允许重写算法。
  - `kernel_gen/passes/memory_plan.py` 约 929 行，存在 auto-pad / lifecycle 逻辑；本计划不改变语义。
  - 其它迁移触达 pass 文件约 384-718 行，适合做路径、文档和小范围 helper 规范化。

## 迁移矩阵

### 实现文件 source -> dest

| 当前路径 | 目标 canonical 路径 | 旧路径处理 |
| --- | --- | --- |
| `kernel_gen/passes/arch_parallelize/arch_parallelize.py` | `kernel_gen/passes/arch/arch_parallelize.py` | 旧子模块改为 re-export shim |
| `kernel_gen/passes/arch_parallelize/__init__.py` | `kernel_gen/passes/arch/__init__.py` 中 re-export `ArchParallelizePass` | 旧 package root 改为 re-export shim |
| `kernel_gen/passes/attach_arch_information.py` | `kernel_gen/passes/arch/attach_arch_information.py` | 旧 module 改为 re-export shim |
| `kernel_gen/passes/kernel_aggregate.py` | `kernel_gen/passes/kernel/kernel_aggregate.py` | 旧 module 改为 re-export shim |
| `kernel_gen/passes/kernel_decompose.py` | `kernel_gen/passes/kernel/kernel_decompose.py` | 旧 module 改为 re-export shim |
| `kernel_gen/passes/memory_plan.py` | `kernel_gen/passes/memory/memory_plan.py` | 旧 module 改为 re-export shim |
| `kernel_gen/passes/memory_pool.py` | `kernel_gen/passes/memory/memory_pool.py` | 旧 module 改为 re-export shim |
| `kernel_gen/passes/multi_buffer.py` | `kernel_gen/passes/memory/multi_buffer.py` | 旧 module 改为 re-export shim |
| `kernel_gen/passes/outline_device_kernel.py` | `kernel_gen/passes/tuning/outline_device_kernel.py` | 旧 module 改为 re-export shim |
| `kernel_gen/passes/tuning/dma_memory_hierarchy.py` | 不移动 | 只更新 spec/test 路径引用 |
| `kernel_gen/passes/tuning/kernel_pattern_attach.py` | 不移动 | 只更新 spec/test 路径引用 |
| `kernel_gen/passes/tuning/transform_apply.py` | 不移动 | 只更新 spec/test 路径引用 |

### spec 文件 source -> dest

| 当前路径 | 目标路径 | 处理 |
| --- | --- | --- |
| `spec/pass/arch_parallelize.md` | `spec/pass/arch/arch_parallelize.md` | 移动为 canonical spec |
| `spec/pass/attach_arch_information.md` | `spec/pass/arch/attach_arch_information.md` | 移动为 canonical spec |
| `spec/pass/kernel_aggregate.md` | `spec/pass/kernel/kernel_aggregate.md` | 移动为 canonical spec |
| `spec/pass/kernel_decompose.md` | `spec/pass/kernel/kernel_decompose.md` | 移动为 canonical spec |
| `spec/pass/memory_plan.md` | `spec/pass/memory/memory_plan.md` | 移动为 canonical spec |
| `spec/pass/lowering/memory_pool.md` | `spec/pass/memory/memory_pool.md` | 移动为 canonical spec |
| `spec/pass/multi_buffer.md` | `spec/pass/memory/multi_buffer.md` | 移动为 canonical spec |
| `spec/pass/outline_device_kernel.md` | `spec/pass/tuning/outline_device_kernel.md` | 移动为 canonical spec |
| `spec/pass/lowering/dma_memory_hierarchy/spec.md` | `spec/pass/tuning/dma_memory_hierarchy.md` | 移动为 canonical spec |
| `spec/pass/kernel_pattern_attach.md` | `spec/pass/tuning/kernel_pattern_attach.md` | 移动为 canonical spec |
| `spec/pass/transform_apply.md` | `spec/pass/tuning/transform_apply.md` | 移动为 canonical spec |

### test 文件 source -> dest

| 当前路径 | 目标路径 | 处理 |
| --- | --- | --- |
| `test/passes/test_arch_parallelize.py` | `test/passes/arch/test_arch_parallelize.py` | 移动 |
| `test/passes/test_attach_arch_information.py` | `test/passes/arch/test_attach_arch_information.py` | 移动 |
| `test/passes/test_kernel_aggregate.py` | `test/passes/kernel/test_kernel_aggregate.py` | 移动 |
| `test/passes/test_kernel_decompose.py` | `test/passes/kernel/test_kernel_decompose.py` | 移动 |
| `test/passes/test_memory_plan.py` | `test/passes/memory/test_memory_plan.py` | 移动 |
| `test/passes/test_memory_pool.py` | `test/passes/memory/test_memory_pool.py` | 移动 |
| `test/passes/test_multi_buffer.py` | `test/passes/memory/test_multi_buffer.py` | 移动 |
| `test/passes/test_outline_device_kernel.py` | `test/passes/tuning/test_outline_device_kernel.py` | 移动 |
| `test/passes/test_dma_memory_hierarchy.py` | `test/passes/tuning/test_dma_memory_hierarchy.py` | 移动 |
| `test/passes/test_kernel_pattern_attach.py` | `test/passes/tuning/test_kernel_pattern_attach.py` | 移动 |
| `test/passes/test_transform_apply.py` | `test/passes/tuning/test_transform_apply.py` | 移动 |

## 方案比较与选型

### 方案 A：只移动实现文件，不动 spec/test

- 内容：仅把 `kernel_gen/passes/*.py` 移动到新子目录，保留 spec/test 原位置。
- 缺点：用户明确要求 spec 和 test 也需要；审查时仍无法从目录结构定位同一 pass 的合同和测试。
- 结论：不采用。

### 方案 B：移动实现、spec、test，并删除旧 public import path

- 内容：所有旧 direct import path 直接删除，调用方必须改用新 canonical path。
- 缺点：旧 direct import path 已写入 `spec/pass/registry.md`、多个 pass spec、pytest、pipeline 和只读 expectation；直接删除属于 breaking public API 变更，会扩大迁移面，并导致 expectation 未授权改动或失败。
- 结论：不采用。

### 方案 C：移动实现、spec、test，新增新 canonical path，保留旧 direct import shim

- 内容：按 `arch / kernel / memory / tuning` 创建新 canonical implementation/spec/test 路径；更新 registry、pipeline、内部测试优先使用新路径；旧 direct import path 保留为兼容 shim，只转发公开 API，不承载业务逻辑。
- 优点：满足用户目录重构目标，spec/test 同步；不破坏现有 expectation 与外部调用；可用测试同时锁定新 canonical path 和旧 compat path。
- 风险：兼容 shim 可能长期滞留，造成双路径维护。
- 风险处理：shim 文件必须只包含公开 re-export 和文件级说明；spec 明确旧 path 是兼容入口，不再作为新代码推荐路径；后续若要删除旧 path，必须另开计划并取得用户确认。
- 结论：采用。

## 公开 API 设计

### 功能简介

- 本计划调整 pass 模块的公开 import path 组织方式，不调整 pass 的 IR 语义、构造参数、registry 名称、pipeline 名称或错误语义。

### API 列表

- `class AttachArchInformationPass(target: str = "npu_demo", fold: bool = True)`
- `AttachArchInformationPass.from_options(options: dict[str, str]) -> AttachArchInformationPass`
- `AttachArchInformationPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
- `ArchParallelizePass.from_options(options: dict[str, str]) -> ArchParallelizePass`
- `ArchParallelizePass.apply(ctx: Context, module: ModuleOp) -> None`
- `class KernelAggregatePass(matmul_acc: bool = False, fold: bool = True)`
- `KernelAggregatePass.from_options(options: dict[str, str]) -> KernelAggregatePass`
- `KernelAggregatePass.apply(ctx: Context, module: ModuleOp) -> None`
- `class KernelDecomposePass(fold: bool = True)`
- `KernelDecomposePass.from_options(options: dict[str, str]) -> KernelDecomposePass`
- `KernelDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`
- `class MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False, auto_pad: bool = False)`
- `MemoryPlanPass.from_options(options: dict[str, str]) -> MemoryPlanPass`
- `MemoryPlanPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class MemoryPoolPass(rewrite: bool = False, fold: bool = True, alignment: int = 1024)`
- `MemoryPoolPass.from_options(options: dict[str, str]) -> MemoryPoolPass`
- `MemoryPoolPass.apply(ctx: Context, module: ModuleOp) -> None`
- `MemoryPoolPass.get_summary(func_name: str) -> MemoryPoolSummary`
- `MemoryPoolPass.all_summaries() -> dict[str, MemoryPoolSummary]`
- `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`
- `MemoryPoolSummary.to_text() -> str`
- `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`
- `class MultiBufferPass(memory_stage: int = 3, fold: bool = True, target: str | None = None)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class OutlineDeviceKernelPass(fold: bool = True)`
- `OutlineDeviceKernelPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class KernelPatternAttachPass(fold: bool = True)`
- `KernelPatternAttachPass.from_options(options: dict[str, str]) -> KernelPatternAttachPass`
- `KernelPatternAttachPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class TransformApplyPass(fold: bool = True)`
- `TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass`
- `TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class LowerDmaMemoryHierarchyPass(fold: bool = True, apply_op: str | None = None)`
- `LowerDmaMemoryHierarchyPass.from_options(options: dict[str, str]) -> LowerDmaMemoryHierarchyPass`
- `LowerDmaMemoryHierarchyPass.apply(ctx: Context, module: ModuleOp) -> None`

### Canonical import path 迁移矩阵

| pass | 旧 direct path | 新 canonical path | 兼容策略 |
| --- | --- | --- | --- |
| `arch-parallelize` | `kernel_gen.passes.arch_parallelize` | `kernel_gen.passes.arch.arch_parallelize` | 旧 package root `__init__.py` 保留 re-export shim；不把 class `__module__` 改回旧 path |
| `arch-parallelize` 内部旧子模块 | `kernel_gen.passes.arch_parallelize.arch_parallelize` | `kernel_gen.passes.arch.arch_parallelize` | 旧子模块保留 re-export shim；不承载业务逻辑 |
| `attach-arch-information` | `kernel_gen.passes.attach_arch_information` | `kernel_gen.passes.arch.attach_arch_information` | 旧 module 保留 re-export shim |
| `kernel-aggregate` | `kernel_gen.passes.kernel_aggregate` | `kernel_gen.passes.kernel.kernel_aggregate` | 旧 module 保留 re-export shim |
| `kernel-decompose` | `kernel_gen.passes.kernel_decompose` | `kernel_gen.passes.kernel.kernel_decompose` | 旧 module 保留 re-export shim |
| `memory-plan` | `kernel_gen.passes.memory_plan` | `kernel_gen.passes.memory.memory_plan` | 旧 module 保留 re-export shim |
| `memory-pool` | `kernel_gen.passes.memory_pool` | `kernel_gen.passes.memory.memory_pool` | 旧 module 保留 re-export shim |
| `multi-buffer` | `kernel_gen.passes.multi_buffer` | `kernel_gen.passes.memory.multi_buffer` | 旧 module 保留 re-export shim |
| `outline-device-kernel` | `kernel_gen.passes.outline_device_kernel` | `kernel_gen.passes.tuning.outline_device_kernel` | 旧 module 保留 re-export shim |

### 非目标模块

- 本计划不迁移 `kernel_gen/passes/inline.py`、`kernel_gen/passes/decompass.py`、`kernel_gen/passes/buffer_results_to_out_params.py`、`kernel_gen/passes/pass_manager.py`、`kernel_gen/passes/registry.py`、`kernel_gen/passes/common.py`、`kernel_gen/passes/producer_consumer_analysis.py`。
- 本计划不重构 `kernel_gen/passes/hoist`、`kernel_gen/passes/tile`、`kernel_gen/passes/template_name`、`kernel_gen/passes/lowering/nn_lowering` 的目录结构；如内部 import 受影响，可做最小路径更新。
- 本计划不删除任何旧 direct import path；旧路径删除必须另开计划。

## 完成态定义

- `kernel_gen/passes` 下新增并使用以下 family：
  - `kernel_gen/passes/arch`
  - `kernel_gen/passes/kernel`
  - `kernel_gen/passes/memory`
  - `kernel_gen/passes/tuning` 中补齐 `outline_device_kernel.py`
- 迁移范围内的新 canonical module path 可直接 import，对应 class 的 `__module__` 指向新 canonical path。
- 旧 direct import path 仍可 import 相同公开 class / getter；旧 shim 不包含 pass 业务逻辑。
- `registry.load_builtin_passes()` 内部导入使用新 canonical path；`build_registered_pass(...)` 返回实例的 `__class__.__module__` 为新 canonical path。
- pipeline builder 内部导入使用新 canonical path；pipeline pass order、pass options 和默认值不变。
- `spec/pass` 按 `arch / kernel / memory / tuning` 同步目录；旧 spec 路径要么移动为新路径，要么保留最小跳转说明，但不能出现两个互相冲突的合同真源。
- `test/passes` 按 `arch / kernel / memory / tuning` 同步目录；每个迁移 pass 至少有 canonical import 测试和 compat import 测试。
- 迁移触达实现文件的文件级说明均包含 `功能说明 / API 列表 / 使用示例 / 关联文件`，且 `API 列表` 紧跟 `功能说明`。
- 新建 / 改动 private callable 满足：
  - 不少于 5 行有效代码。
  - 不调用其它 private callable。
  - 只在当前文件内部使用。
  - 任务记录中写清为什么不能内联、替代了什么旧逻辑、旧逻辑是否删除。
- `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 在候选 diff 中无改动。

## 验收设计

### Diff 反推 pytest

- 目录结构 / import / registry：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py test/passes/test_pattern_public_api_docs.py`
- family 目录测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/arch test/passes/kernel test/passes/memory test/passes/tuning`
- pipeline 回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/pipeline/test_cuda_sm86_lowering.py`
- 全量 pass 回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes`

### 只读 expectation 合同验收

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.arch_parallelize`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.attach_arch_information`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_aggregate`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_decompose`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_pool`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy.basic`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_pattern_attach`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.transform_apply`

### 当前非必过 expectation 基线冲突

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.default_lowering` 当前失败于 `ModuleNotFoundError: No module named 'kernel_gen.passes.dma_memory_hierarchy'`。
- 该旧路径在 `spec/pass/registry.md` 当前列为已退场且应稳定失败的路径。本计划不恢复该旧路径，也不修改 `expectation/`，因此该 expectation 不作为当前必过合同验收；若用户或架构师要求恢复它，必须先更新本计划公开 API 和 expectation 授权。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering` 当前共享 expectation 期望 `npu-demo-lowering` 在 pipeline 中接入 `multi-buffer:memory_stage=2:target=npu_demo`；本计划不改变 `npu-demo-lowering` pipeline、不接入 `multi-buffer`、不新增 pipeline option，因此该入口不作为本计划必过 expectation。`test/passes/pipeline/test_npu_demo_lowering.py` 仍作为本计划必过 pytest 回归。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy` 当前失败于 `expectation.pass.dma_memory_hierarchy.matmul_apply` 的 `matmul-out-copy`、`matmul-all-operands-copy`、`matmul-tlm-family-copy` 三个 case；本计划不修改该 pass 语义或 expectation，本轮只把 `expectation.pass.dma_memory_hierarchy.basic` 列为当前必过合同验收。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy.matmul_apply` 同上作为当前非必过 expectation 基线冲突记录。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer` 当前共享 expectation 的 `matmul_ring_memory_stage` 仍匹配三操作数 `dma.make_ring(memory,num,offset)`；本计划不修改 `dma.make_ring` / `DmaMakeRingOp` 公开合同，不回退也不前推 API，因此该入口不作为本计划必过 expectation。

### 文本 / 静态门禁

- 新 canonical path 必须在 registry / pipeline / spec / tests 中生效：
  - `rg -n "kernel_gen\\.passes\\.(arch_parallelize|attach_arch_information|kernel_aggregate|kernel_decompose|memory_plan|memory_pool|multi_buffer|outline_device_kernel)" kernel_gen/pipeline kernel_gen/passes/registry.py test/passes spec/pass`
  - 预期：只允许旧 compat shim、兼容测试、兼容说明和只读 expectation 相关说明；registry / pipeline 主路径不得继续使用旧 direct import。
- 已退场 tuning 旧路径不得恢复：
  - `python3 - <<'PY'
import importlib.util
for name in ("kernel_gen.passes.dma_memory_hierarchy", "kernel_gen.passes.kernel_pattern_attach", "kernel_gen.passes.transform_apply"):
    if importlib.util.find_spec(name) is not None:
        raise SystemExit(f"unexpected restored old path: {name}")
PY`
- 旧 shim 不得承载业务逻辑：
  - `python3 - <<'PY'
from pathlib import Path
import ast
allowed = (
    Path("kernel_gen/passes/attach_arch_information.py"),
    Path("kernel_gen/passes/kernel_aggregate.py"),
    Path("kernel_gen/passes/kernel_decompose.py"),
    Path("kernel_gen/passes/memory_plan.py"),
    Path("kernel_gen/passes/memory_pool.py"),
    Path("kernel_gen/passes/multi_buffer.py"),
    Path("kernel_gen/passes/outline_device_kernel.py"),
    Path("kernel_gen/passes/arch_parallelize/__init__.py"),
    Path("kernel_gen/passes/arch_parallelize/arch_parallelize.py"),
)
for path in allowed:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)):
            continue
        raise SystemExit(f"{path} contains business node {type(node).__name__}")
PY`
- private callable 约束：
  - `rg -n "^def _|^class _|^    def _" kernel_gen/passes/arch kernel_gen/passes/kernel kernel_gen/passes/memory kernel_gen/passes/tuning`
  - 执行人需在任务记录中列出新增 / 改动 private callable、有效行数、调用次数和是否调用其它 private callable。
- 敏感目录门禁：
  - `git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md ARCHITECTURE/plan/pass_directory_layout_refactor.md`
  - `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md ARCHITECTURE/plan/pass_directory_layout_refactor.md`
- 格式门禁：
  - `git diff --check`

## 计划内小任务

### S1. 建立 pass family 目录与兼容路径矩阵

- 为什么做：当前 pass 实现一部分在 root-level，一部分在 family 子包，新增 pass 时难以判断应放在哪里。
- 做什么：创建 `arch / kernel / memory` family，补齐 `tuning/outline_device_kernel.py`，把计划范围内实现移动到新 canonical path，并在旧路径保留兼容 shim。
- 不做什么：不删除旧 direct import path，不改 pass class 签名、registry name、pipeline 阶段顺序或 IR 语义。
- 怎么验收：运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py`；运行新旧 import smoke；运行旧 shim AST 门禁；确认 registry / pipeline 主路径不再导入迁移范围内旧 direct path。
- 卡住问谁：公开路径兼容策略冲突问用户；目录归属争议问架构师；任务状态 / worktree 问管理员。

详细字段：
- 上下文摘要：用户给出的草图覆盖 `arch / kernel / memory / tuning`，当前实现中对应 pass 多数仍在 root-level 或非目标 package。
- 小任务目标：完成实现目录 rehome 和旧路径 shim，使新旧 import path 均可用且业务逻辑只存在于新 canonical module。
- 非目标：不迁移 `hoist`、`tile`、`template_name`、`inline`、`decompass`、`buffer_results_to_out_params`、`pass_manager`、`registry`、`producer_consumer_analysis`。
- 模块范围：`kernel_gen/passes/**`、`kernel_gen/pipeline/**` 中相关 import。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划正式版本正文。
- 合同真源：用户目录草图 > 本计划公开路径矩阵 > `spec/pass/registry.md` > pytest import / registry 断言 > 当前实现。
- 最小功能闭环：`importlib.import_module(new_path)` 和 `importlib.import_module(old_path)` 均返回公开 class；`build_registered_pass(name)` 返回新 canonical class。
- 执行步骤：
  1. 新增 `kernel_gen/passes/arch/__init__.py`、`kernel_gen/passes/kernel/__init__.py`、`kernel_gen/passes/memory/__init__.py`。
  2. 移动实现文件到新 canonical path。
  3. 旧 direct path 改为 re-export shim，保留文件级说明与 `__all__`。
  4. 更新 `kernel_gen/passes/__init__.py` package root re-export 来源。
  5. 更新 `kernel_gen/passes/registry.py` 和 pipeline builder import。
  6. 运行 import smoke 与 registry pytest。
- Diff 反推测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY'
import importlib
pairs = {
    "kernel_gen.passes.arch.arch_parallelize": "ArchParallelizePass",
    "kernel_gen.passes.arch.attach_arch_information": "AttachArchInformationPass",
    "kernel_gen.passes.kernel.kernel_aggregate": "KernelAggregatePass",
    "kernel_gen.passes.kernel.kernel_decompose": "KernelDecomposePass",
    "kernel_gen.passes.memory.memory_plan": "MemoryPlanPass",
    "kernel_gen.passes.memory.memory_pool": "MemoryPoolPass",
    "kernel_gen.passes.memory.multi_buffer": "MultiBufferPass",
    "kernel_gen.passes.tuning.outline_device_kernel": "OutlineDeviceKernelPass",
}
for module_name, class_name in pairs.items():
    cls = getattr(importlib.import_module(module_name), class_name)
    assert cls.__module__ == module_name, (class_name, cls.__module__)
compat = {
    "kernel_gen.passes.arch_parallelize": "ArchParallelizePass",
    "kernel_gen.passes.arch_parallelize.arch_parallelize": "ArchParallelizePass",
    "kernel_gen.passes.attach_arch_information": "AttachArchInformationPass",
    "kernel_gen.passes.kernel_aggregate": "KernelAggregatePass",
    "kernel_gen.passes.kernel_decompose": "KernelDecomposePass",
    "kernel_gen.passes.memory_plan": "MemoryPlanPass",
    "kernel_gen.passes.memory_pool": "MemoryPoolPass",
    "kernel_gen.passes.multi_buffer": "MultiBufferPass",
    "kernel_gen.passes.outline_device_kernel": "OutlineDeviceKernelPass",
}
for module_name, class_name in compat.items():
    getattr(importlib.import_module(module_name), class_name)
PY`
- 合同验收：本卡不修改 `expectation/`；完成实现目录和 compat shim 后，至少运行下列只读 expectation 证明旧 direct import consumer 仍可用：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.arch_parallelize`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.attach_arch_information`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_aggregate`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_decompose`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_pool`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy.basic`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_pattern_attach`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.transform_apply`
- 验收与记录要求：任务记录写清移动矩阵、旧 shim 文件清单、新 canonical path import 结果、旧 path compat 结果。

### S2. 同步 spec 目录和公开路径合同

- 为什么做：当前 spec 把旧 direct path 写成 canonical path，执行目录迁移后若不改 spec，会形成旧合同和新实现冲突。
- 做什么：按 `arch / kernel / memory / tuning` 移动或重建对应 spec，更新 `API 列表`、文档信息、依赖、测试清单和 registry 的路径矩阵。
- 不做什么：不改变 pass class 构造签名、option、错误文本或 IR 行为。
- 怎么验收：运行旧路径文本扫描，确认迁移范围内旧 direct path 只出现在 compat 说明；抽查每个新 spec 的 `功能简介 / API 列表 / 文档信息` 顺序；运行 `rg -n "spec/pass/(arch_parallelize|kernel_aggregate|kernel_decompose|memory_plan|multi_buffer|outline_device_kernel)\\.md|spec/pass/lowering/(memory_pool|dma_memory_hierarchy)" spec/pass` 确认旧 spec 路径不再作为合同真源。
- 卡住问谁：公开 API 路径是否应删除旧 compat 问用户；spec 和实现归属冲突问架构师。

详细字段：
- 上下文摘要：`spec/pass/registry.md` 当前列出大量旧 direct path；`memory_pool` 和 `dma_memory_hierarchy` spec 路径与实现分类已不一致。
- 小任务目标：让 spec 目录和内容成为新目录结构的合同真源。
- 非目标：不把任务过程、历史迁移过程写入最终 spec；不把私有 helper 写进 spec 依赖。
- 模块范围：`spec/pass/**`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划正式版本正文。
- 合同真源：本计划公开路径矩阵 > `agents/standard/spec文件规范.md` > 当前 pass spec。
- 最小功能闭环：每个迁移 pass 有且只有一个新 canonical spec 真源；旧 spec 路径若保留，只能是跳转说明，不承载独立合同。
- 执行步骤：
  1. 建立 `spec/pass/arch`、`spec/pass/kernel`、`spec/pass/memory`、`spec/pass/tuning` 缺失目录。
  2. 移动或重写迁移范围内 spec 到新目录。
  3. 更新 `功能简介` 后紧跟的 `API 列表`。
  4. 更新 `文档信息` 中的实现文件和测试文件路径。
  5. 更新 `spec/pass/registry.md` 的 canonical path 矩阵和内置 pass 列表。
  6. 扫描旧 direct path 文本，保留项必须标注为 compat path。
- Diff 反推测试 / 文本核对：
  - `rg -n "kernel_gen\\.passes\\.(arch_parallelize|attach_arch_information|kernel_aggregate|kernel_decompose|memory_plan|memory_pool|multi_buffer|outline_device_kernel)" spec/pass`
  - 预期：旧 direct path 只允许出现在 compat path 说明；new canonical path 必须出现在对应 spec 的文档信息或依赖中。
  - `rg -n "spec/pass/(arch_parallelize|attach_arch_information|kernel_aggregate|kernel_decompose|memory_plan|multi_buffer|outline_device_kernel)\\.md|spec/pass/lowering/(memory_pool|dma_memory_hierarchy)" spec/pass`
  - 预期：无旧 spec 真源路径残留；如保留跳转说明，必须不承载 `API详细说明`。
- 合同验收：本卡不修改 `expectation/`，也不把 expectation 当作 spec diff 反推测试；完成 spec 目录同步后，计划级当前必过只读 expectation 仍按 `验收设计` 列表运行；`pipeline.default_lowering`、`pipeline.npu_demo_lowering`、`dma_memory_hierarchy` 聚合 / `matmul_apply`、`multi_buffer` 仍只作为非必过 / 共享 expectation 基线冲突记录。
- 验收与记录要求：任务记录列出 spec move 矩阵、旧 path 文本扫描结果和保留理由。

### S3. 同步 pytest 目录并补 canonical / compat import 测试

- 为什么做：用户要求 test 也跟随目录重构；同时目录迁移必须由测试证明新 path 可用且旧 path 未破坏 expectation / 外部 caller。
- 做什么：把迁移范围内 pytest 移入 `test/passes/arch`、`test/passes/kernel`、`test/passes/memory`、`test/passes/tuning`，更新测试注释、pytest 命令和 public API import 断言。
- 不做什么：不把测试改成直连跨文件私有 helper；不扩大 expectation。
- 怎么验收：运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/arch test/passes/kernel test/passes/memory test/passes/tuning test/passes/test_registry.py test/passes/test_pattern_public_api_docs.py`；运行 pipeline pytest；运行全量 `test/passes`。
- 卡住问谁：测试是否需要覆盖未确认旧 path 删除时问用户；测试矩阵过大影响 CI 时问架构师。

详细字段：
- 上下文摘要：当前多数 pass 测试位于 `test/passes/test_<name>.py`，只有 `tile`、`lowering/nn_lowering` 已部分分目录；`launch_kernel_cost_func` 相关测试已在 latest main 删除，不纳入本计划。
- 小任务目标：让测试目录与 pass family 对齐，并锁定 canonical path / compat path 行为。
- 非目标：不重写测试夹具，不改变测试对公开 IR 行为的断言。
- 模块范围：`test/passes/**`、必要时 `test/tools/**` 与 `test/dsl/**` 中旧 import 更新。
- 禁止修改面：`expectation/`、`.skills`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划正式版本正文。
- 合同真源：本计划公开路径矩阵 > `agents/standard/测试文件约定.md` > 当前 pytest。
- 最小功能闭环：每个迁移 pass 的测试从新 canonical path 导入 class；每个旧 direct path 至少有一条 compat import smoke。
- 执行步骤：
  1. 建立测试 family 目录。
  2. 移动迁移范围内 pytest 文件，更新 `pytest` 节点路径。
  3. 更新测试文件 docstring、TC 注释中的 spec / 实现路径。
  4. 在 registry 或 dedicated import 测试中增加新 canonical path `__module__` 断言。
  5. 在 compat import 测试中断言旧 direct path 导出的对象等于新 canonical 对象。
  6. 更新 pipeline / tool / DSL 测试中的内部导入为新 canonical path；只读 expectation 不改。
- Diff 反推测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/arch test/passes/kernel test/passes/memory test/passes/tuning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pattern_public_api_docs.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/pipeline/test_cuda_sm86_lowering.py`
- 合同验收：本卡不修改 `expectation/`；完成 pytest 目录同步和 import 断言后，计划级当前必过只读 expectation 仍按 `验收设计` 列表运行，用于证明测试路径迁移没有破坏旧 direct import consumer；非必过 / 共享 expectation 基线冲突仍不得升级为本卡阻断。
- 验收与记录要求：任务记录写清测试移动矩阵、import smoke 覆盖范围、pytest 通过结果。

### S4. 对迁移触达 pass 做小范围实现规范化

- 为什么做：目录迁移会触达文件级说明、import、helper 和路径注释；顺手规范化能降低后续审查和维护成本。
- 做什么：只做等价、局部、可测试的实现规范化；重点更新文件级说明和 API 列表，清理过期路径说明、重复 import、明显浅 wrapper、违反 private callable 规则的局部结构。
- 不做什么：不重写 `memory_pool` / `memory_plan` 核心算法，不改变 IR 输出、错误文本、Pass option 或资源生命周期。
- 怎么验收：运行迁移范围对应 pytest、pipeline pytest、只读 expectation；运行 private callable 扫描；任务记录写清每个新增 / 改动 private callable 的有效行数、调用次数和是否调用其它 private callable。
- 卡住问谁：任何语义改动、公开 API 调整或 expectation 失败归因不明时问用户 / 架构师。

详细字段：
- 上下文摘要：迁移范围内最大文件为 `memory_pool.py`，其次为 `memory_plan.py`；本计划的实现重构必须“轻量”，不能变成算法专题。
- 小任务目标：让迁移后的实现文件满足 `实现文件规范.md`，且保持行为等价。
- 非目标：不修改 `kernel_gen/passes/hoist/symbol_buffer_hoist.py`、`kernel_gen/passes/tile/**`、`kernel_gen/passes/template_name/**` 的内部结构。
- 模块范围：S1 迁移触达的新 canonical implementation 文件与旧 shim。
- 禁止修改面：`expectation/`、`.skills`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划正式版本正文。
- 合同真源：当前 pass spec > pytest > expectation > 当前实现。
- 最小功能闭环：迁移后 pass 行为在公开 pytest / 当前必过 expectation 中保持不变；实现文件说明与实际 API 一致。
- 执行步骤：
  1. 对每个迁移实现文件更新文件级 `功能说明 / API 列表 / 使用示例 / 关联文件`。
  2. 删除过期旧路径说明，把旧路径说明移到 shim 文件。
  3. 检查新增 / 改动 private callable；小于 5 行有效代码必须内联，private callable 调 private callable 必须内联或合并。
  4. 清理未使用 import、重复常量、无意义 wrapper；每项必须能由 diff 解释。
  5. 不碰 pass 核心算法，除非当前测试失败且 spec 明确要求修复。
  6. 运行对应 pass pytest、pipeline pytest、当前必过 expectation。
- Diff 反推测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/arch test/passes/kernel test/passes/memory test/passes/tuning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/pipeline/test_cuda_sm86_lowering.py`
  - `rg -n "^def _|^class _|^    def _" kernel_gen/passes/arch kernel_gen/passes/kernel kernel_gen/passes/memory kernel_gen/passes/tuning`
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.arch_parallelize`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.attach_arch_information`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_aggregate`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_decompose`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_pool`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy.basic`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_pattern_attach`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.transform_apply`
- 验收与记录要求：任务记录必须包含 `减法检查`，列出 private callable、旧逻辑删除 / 保留依据、扫描命令和测试结果。

### S5. 总体验收、同步检查与任务记录

- 为什么做：目录重构跨实现、spec、test、registry、pipeline 和兼容路径，必须用总体验收证明没有遗漏。
- 做什么：运行计划验收命令、diff 反推测试、只读 expectation、文本门禁、敏感目录门禁，并补齐任务记录。
- 不做什么：不把 expectation 当作 diff 反推测试；不跳过失败项；不自行归档或合并。
- 怎么验收：所有命令通过；任务记录完整；候选 diff 不含禁止修改面。
- 卡住问谁：流程状态问管理员；合同验收失败且疑似 expectation 本体问题问架构师 / 用户。

详细字段：
- 上下文摘要：本计划触达公开 import path 和大量测试路径，review 会重点检查漏改和兼容策略。
- 小任务目标：形成可 review 的候选 diff 和完整任务记录。
- 非目标：不创建 review / archive / merge 之外的额外阶段。
- 模块范围：本计划所有触达文件、任务记录文件。
- 禁止修改面：`expectation/`、`.skills`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划正式版本正文。
- 合同真源：本计划完成态 > spec > pytest > expectation > 当前实现。
- 最小功能闭环：新目录结构、spec/test 目录、registry/pipeline、新旧 import path、当前必过只读 expectation 全部闭环。
- 执行步骤：
  1. 运行 `pytest` 与 expectation 命令。
  2. 运行文本门禁、sensitive diff/status、`git diff --check`。
  3. 用 `git diff --name-status` 反推确认所有 move / rename / shim 均在计划范围内。
  4. 任务记录写清执行前阅读、计划内小任务卡核对、最小功能闭环、Diff 反推自测、合同验收、减法检查、自检和结论。
  5. 完成后续接 `review`，不得直接进入 archive 或 merge。
- 合同验收：运行本计划 `验收设计` 中全部当前必过只读 expectation；`当前非必过 expectation 基线冲突` 中列出的入口只复核失败归因并记录，不作为本计划阻断。
- 验收与记录要求：记录每条命令退出码、通过数量或失败摘要；未运行项必须写明原因和风险。

## 待确认项

- 无当前阻断待确认项。
- 已按用户 2026-06-07 指令把新增 canonical import path 与 spec/test 目录重构纳入计划；旧 direct import path 本计划保留 compat shim，不做删除。

## 用户确认与协同约束

- 用户确认来源：2026-06-07 用户要求按 `plan/1.md` 草图重构 pass 文件目录，并同步 spec/test，顺带小范围规范化 pass 实现。
- 公开 API 口径：用户确认覆盖“新增新目录 canonical import path”；旧 direct import path 删除未获确认，本计划不删除。
- `expectation/`：默认只读，不新增、不修改。
- 当前恢复前置：Draft 3-R1 守护最终检验已通过，Draft 4 execute 期验收口径修订已完成 strict review 与守护复验；Draft 5 latest-main 删除事实修订必须完成两路 strict review 与守护复验后，管理员才可恢复已暂停的唯一计划级 `execute`。本计划回写不直接创建任务。
