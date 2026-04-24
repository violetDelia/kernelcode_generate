# launch_kernel_cost_func_multi_kind_green_plan.md

> 说明：该文件为 `launch_kernel_cost_func_multi_kind` 的归档承载快照。当前 latest 远端基线 `origin/main@995d5fa30c44de27ec5544706e3d15be1f75d348` 仍通过 `agents/codex-multi-agents/log/task_records/done_plan/2026/17/launch_kernel_cost_func_multi_kind_green_plan.md` 承载本计划；并且自 `origin/main@791b9d0ed6a74276f2cf2e08fadd55156e874469` 起的后续主线现场，均不再包含 `ARCHITECTURE/plan/launch_kernel_cost_func_multi_kind_green_plan.md` 与 `TODO.md`。因此后续计划状态、结论和续接依据统一收口到本归档文件与对应任务记录，不再回写缺失的计划正文或 `TODO.md`。

## 文档信息

- 创建者：`Codex`
- 最后一次更改：`咯咯咯`
- 目标 `spec`：
  - [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../../spec/pass/tuning/launch_kernel_cost_func.md)
  - [`spec/dialect/tuner.md`](../../../../../../../spec/dialect/tuner.md)
  - [`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)
- 目标 `API`：
  - `launch-kernel-cost-func={cost_kind=<kind0>|<kind1>|...}`
  - `LaunchKernelCostFuncPass(cost_kind="<kind0>|<kind1>|...")`
  - `build_registered_pass("launch-kernel-cost-func", {"cost_kind": "<kind0>|<kind1>|..."})`
  - `tuner.cost(...){cost_kind = "<kind>", op_name = "..."}`
- 目标 `test`：
  - [`test/pass/test_launch_kernel_cost_func.py`](../../../../../../../test/pass/test_launch_kernel_cost_func.py)
  - [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)
  - [`test/dialect/test_tuner_dialect.py`](../../../../../../../test/dialect/test_tuner_dialect.py)
- 目标 `验收资产`：
  - [`expectation/pass/tuning/launch_kernel_cost_func`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func)
  - [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory)
  - [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)
- 目标 `功能实现`：
  - [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
  - [`kernel_gen/dialect/tuner.py`](../../../../../../../kernel_gen/dialect/tuner.py)
  - [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1：launch-kernel-cost-func 多 cost_kind 红转绿收口` | `T-20260422-f94ed233`（[`main_npu_demo_pipeline_fold_cse_green_plan.md`](main_npu_demo_pipeline_fold_cse_green_plan.md) 的 `S2` 任务） | `wt-20260422-launch-kernel-cost-multi-kind-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-launch-kernel-cost-multi-kind-s1.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹、守护最好的爱莉希雅`
- 结论摘要：`复评通过。单阶段 S1 可接受，范围集中在 launch-kernel-cost-func pass、tuner verifier、registry 与 expectation/spec/pytest 同步，不需要拆纯 spec。multi_kind / invalid_kind 合同真源顺序清楚，四字段 arch.launch 不并入本计划的边界清楚。前置依赖已直接写明 T-20260422-f94ed233；basic_all.py 与 invalid_kind.py 已按 [immutable-file] 只读运行处理，若 immutable 合同与本计划冲突则停止并向用户确认。守护最好的爱莉希雅互评通过：S1 单阶段覆盖 spec、实现、pytest、expectation 同链，依赖 T-20260422-f94ed233 已在任务清单、验收设计与任务新建建议中写清；kind/device_func 旧合同回退已在 API、完成态和测试中排除，阶段正文自包含，可直接交给 spec。`

## 终验 / 复验 / 修复复核记录

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`主目录 /home/lfr/kernelcode_generate 已先执行 git fetch --prune；当前 HEAD 与 origin/main 同步到 737badc1fa7212a7645f59f5982f9c05398698f6。`
- 执行目录：`/home/lfr/kernelcode_generate`
- 相关 expectation 摘要：`本轮只执行与本计划相关的 expectation 合同验收：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；目录入口中的 basic_all / multi_kind / shared_callee_once / invalid_kind 均通过。`
- 最小阻断项或通过摘要：`尽管本轮相关 expectation 已通过，但当前仍有同范围可继续收口点，因此不能给通过。最小阻断项是：本计划涉及的 spec / pass / verifier 仍把 cost_kind 固定为 compute / memory / kind2 / kind3 四个值，例如 spec/pass/tuning/launch_kernel_cost_func.md、spec/dialect/tuner.md、kernel_gen/passes/tuning/launch_kernel_cost_func.py、kernel_gen/dialect/tuner.py 仍显式枚举四值；而用户后续已把这一域的公开方向改为“pass 可接受任意 kind 字符串与任意数量”。在这组固定四 kind 合同退场前，本计划不能作为最终完成态给通过。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按当前终验阻断项补建唯一修复任务 T-20260424-147a9135，worktree=/home/lfr/kernelcode_generate/wt-20260424-launch-kernel-cost-multi-kind-repair-s2，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-launch-kernel-cost-multi-kind-repair-s2.md。最小修复目标只收 4 个文件中的固定四值合同：spec/pass/tuning/launch_kernel_cost_func.md、spec/dialect/tuner.md、kernel_gen/passes/tuning/launch_kernel_cost_func.py、kernel_gen/dialect/tuner.py 中仍把 cost_kind 固定为 compute/memory/kind2/kind3 的表述与实现，需要继续统一到 pass 可接受任意 kind 字符串与任意数量的公开方向。`
- 另一位架构师补充重点：`后续修复不应继续围绕固定四值补小改，而应直接把 spec / pass / verifier 收到 open-kind 方向。`

### 2026-04-24 守护最好的爱莉希雅 终验复核

- 结论：`不通过`
- 验证基线：`主目录 /home/lfr/kernelcode_generate 已执行 git fetch --prune；当前 HEAD 与 origin/main 同步到 5e6eec17e7e4ee28df881afad0c4485e105be9a1。`
- 执行目录：`/home/lfr/kernelcode_generate`
- 相关 expectation 摘要：`本轮只执行与本计划相关的 expectation 合同验收：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func。basic_all / multi_kind / shared_callee_once 已通过，但目录入口在 invalid_kind 处失败，整体 exit 1；失败短语为 CASE-1 断言 “failing ircheck run must report ok=False”。`
- 最小阻断项或通过摘要：`当前实现与主 spec 已转到 open-kind 方向，spec/pass/tuning/launch_kernel_cost_func.md、spec/dialect/tuner.md、kernel_gen/passes/tuning/launch_kernel_cost_func.py、kernel_gen/dialect/tuner.py 均接受任意非空 kind 名与任意数量；但只读 expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py 仍锁定旧合同，要求非法 kind 必须报出“compute / memory / kind2 / kind3”固定四值错误短语。由于本轮相关 expectation 本身未通过，且合同资产仍与当前公开方向不一致，本计划仍不能给通过。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按当前最新阻断项补建唯一修复任务 T-20260424-3b148a23，worktree=/home/lfr/kernelcode_generate/wt-20260424-launch-kernel-cost-multi-kind-repair-s3，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-launch-kernel-cost-multi-kind-repair-s3.md。上一轮 T-20260424-147a9135 已完成实现/spec 的 open-kind 收口，当前剩余阻断仅在 expectation；本任务不得修改 immutable expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py，只处理其修复/拆链边界：将该文件保留为旧四值历史合同或 companion 资产，按当前 open-kind 公开方向调整目录级 expectation 入口与相关非 immutable 合同资产，使本计划相关 expectation 恢复通过。`

### 2026-04-24 守护最好的爱莉希雅 阻塞链补充

- 结论：`当前不能继续让 T-20260424-3b148a23 空转`
- 执行目录：`阻塞判断基于 /home/lfr/kernelcode_generate/wt-20260424-launch-kernel-cost-multi-kind-repair-s3 与共享 TODO / 计划正文。`
- 验证基线：`管理员固定的当前现场仍是 origin/main@8e73d6af6fb6；该现场下 3b148a23 的 blocker 已由执行人与架构侧多轮复核确认。`
- 相关 expectation 摘要：`当前目录级 expectation 继续在 multi_kind.py 先报 LaunchKernelCostFuncError: cost_kind must be one of compute, memory；失败点已超出 immutable invalid_kind.py 的拆链边界，说明 expectation-only 任务前提未成立。`
- 最小阻断项或通过摘要：`当前最小阻断项不是 3b148a23 自身的 runner 写法，而是其前置条件缺失：管理员指定基线下的 7 个 product/spec/pytest 文件仍未恢复 open-kind，因此 expectation-only 拆链不能形成真实闭环。为避免 3b148a23 持续空转，已补建唯一可执行前置 build 切片 T-20260424-6195abc3，专门把 kernel_gen/passes/tuning/launch_kernel_cost_func.py、kernel_gen/dialect/tuner.py、spec/pass/tuning/launch_kernel_cost_func.md、spec/dialect/tuner.md、test/pass/test_launch_kernel_cost_func.py、test/pass/test_pass_registry.py、test/dialect/test_tuner_dialect.py 重新收回 open-kind；在该前置切片完成前，3b148a23 继续保持阻塞，不执行 expectation-only 下一步。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`前置 build 切片任务号为 T-20260424-6195abc3，worktree=/home/lfr/kernelcode_generate/wt-20260424-launch-kernel-cost-multi-kind-pre-s4，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-launch-kernel-cost-multi-kind-pre-s4.md。该任务只处理上述 7 个 product/spec/pytest 文件及其直接关联内容；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测。`

### 2026-04-25 守护最好的爱莉希雅 复验（03c64eb）

- 结论：`不通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地删改与未跟踪文件，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck。`
- 验证基线：`origin/main@03c64ebe6ea37f94c997ecff2f4923ed36d6c90e；主目录 fast-forward 受本地改动阻挡，未覆盖现有现场。`
- 相关 expectation 摘要：`本轮只执行当前正文保留的相关 expectation 合同验收：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；当前目录入口只接线 compute/memory runner。2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory，exit 0。`
- 最小阻断项或通过摘要：`当前仍有可继续收口点，因此不能给通过。最小阻断项是：计划正文本身仍大面积保留旧四值合同，和最新主线现场已不一致。正文顶部“目标 API”仍写 launch-kernel-cost-func={cost_kind=compute|memory|kind2|kind3}、LaunchKernelCostFuncPass(cost_kind=\"compute|memory|kind2|kind3\")、build_registered_pass(\"launch-kernel-cost-func\", {\"cost_kind\": \"compute|memory|kind2|kind3\"})；“目标验收资产”仍点名 multi_kind.py 与 invalid_kind.py；完成态、验收设计、S1 阶段目标也仍以四值和四个 cost function 为完成口径。但最新主线现场的产品 spec 已转到 open-kind，当前 tracked expectation 目录入口也只保留 compute/memory 资产：expectation/pass/tuning/launch_kernel_cost_func/__main__.py 只接线 expectation.pass.tuning.launch_kernel_cost_func_compute_memory.__main__，而 tracked 文件集合里已没有 multi_kind.py、invalid_kind.py。也就是说，这份计划正文的公开 API、验收资产与完成态描述还没有和当前真实实现 / spec / pytest / expectation 收到同一口径。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按本轮复验结果补建唯一修复任务 T-20260425-85e85979，worktree=/home/lfr/kernelcode_generate/wt-20260425-launch-kernel-cost-multi-kind-repair-s5，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260425-launch-kernel-cost-multi-kind-repair-s5.md。任务只处理计划正文中的旧四值公开 API、旧验收资产与旧完成态描述，和当前 open-kind 产品 spec、tracked expectation 目录入口、真实实现/spec/pytest/expectation 的对齐；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测。`

### 2026-04-25 守护最好的爱莉希雅 复验（7546a4d）

- 结论：`不通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地删改与未跟踪文件，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck-2。`
- 验证基线：`origin/main@7546a4d2cb66f5a93d8ae85372b823ace24d6e7c；主目录 fast-forward 受本地改动阻挡，未覆盖现有现场。`
- 相关 expectation 摘要：`本轮只执行当前正文保留的相关 expectation 合同验收：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck-2 python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；目录入口继续只接线 compute/memory runner。2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck-2 python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory，exit 0。`
- 最小阻断项或通过摘要：`当前仍有可继续收口点，因此不能给通过。最小阻断项没有变化：计划正文本身仍保留旧四值公开 API、旧验收资产与四个 cost function 完成口径，未与当前现场对齐。最新主线现场中，expectation/pass/tuning/launch_kernel_cost_func/__main__.py 已明确只承接 compute/memory 目录入口，tracked 文件集合中没有 multi_kind.py、invalid_kind.py；spec/pass/tuning/launch_kernel_cost_func.md 也已经写明当前公开方向为 open-kind、旧两值与旧四值示例只作兼容样例保留。但这份计划正文顶部“目标 API”仍写 compute|memory|kind2|kind3，`目标验收资产` 仍点名 multi_kind.py 与 invalid_kind.py，完成态、验收设计、S1 阶段目标仍以四值和四个 cost function 为目标。也就是说，正文的公开 API、验收资产与完成态描述还没有和当前真实实现 / spec / pytest / expectation 对齐。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按本轮复验结果补建当前唯一修复任务 T-20260425-4af4fb77，worktree=/home/lfr/kernelcode_generate/wt-20260425-launch-kernel-cost-multi-kind-repair-s6，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260425-launch-kernel-cost-multi-kind-repair-s6.md。任务只处理计划正文中的旧四值公开 API、旧验收资产与四个 cost function 完成口径，和当前 open-kind 产品 spec、tracked expectation 目录入口、真实实现/spec/pytest/expectation 的对齐，以及直接关联的实现/spec/test 收口；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测。`

### 2026-04-25 守护最好的爱莉希雅 复验（791b9d0）

- 结论：`不通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地删改与未跟踪文件，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck-3。`
- 验证基线：`origin/main@791b9d0ed6a74276f2cf2e08fadd55156e874469；主目录 fast-forward 受本地改动阻挡，未覆盖现有现场。`
- 相关 expectation 摘要：`本轮只执行当前正文保留的相关 expectation 合同验收：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck-3 python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；目录入口继续只接线 compute/memory runner。2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-launch-kernel-cost-multi-kind-recheck-3 python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory，exit 0。`
- 最小阻断项或通过摘要：`当前仍有可继续收口点，因此不能给通过。最新同步现场本身已经不再携带这份计划资产：origin/main@791b9d0 的干净 worktree 中只有 ARCHITECTURE/project_architecture.md 与 ARCHITECTURE/reference/reference_project_rvv_xdsl_research.md，既没有 ARCHITECTURE/plan/launch_kernel_cost_func_multi_kind_green_plan.md，也没有 TODO.md。也就是说，这份计划正文虽然在当前本地现场仍可见，但它并未随最新同步现场一起存在；在计划资产重新与最新主线现场对齐前，不能把这份计划当作已完成的有效归档对象。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按本轮复验结果补建当前唯一修复任务 T-20260425-393f25ad，worktree=/home/lfr/kernelcode_generate/wt-20260425-launch-kernel-cost-multi-kind-repair-s7，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260425-launch-kernel-cost-multi-kind-repair-s7.md。任务只处理计划资产与最新主线现场的对齐，以及直接关联的归档/记录收口；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测。`

## 输入摘要

- 目标：把本计划正文中仍残留的旧四值合同、旧目录级 expectation 资产和固定“四个 cost function”完成口径，统一收到当前 open-kind 产品合同与当前 tracked `compute / memory` 目录入口。
- 不做什么：本轮只修正文案，不修改实现、pytest 或仓库中的 `expectation`；不重开 `multi_kind.py` / `invalid_kind.py` 历史合同链；不重新定义 kind 名称上界。
- 当前痛点：当前 `spec/pass/tuning/launch_kernel_cost_func.md`、`spec/dialect/tuner.md`、实现和 pytest 已经是 open-kind，但本计划正文仍把 `cost_kind` 写成固定四值，并继续把 `multi_kind.py` / `invalid_kind.py` 当作当前目录验收资产。
- 完成后用户最想看到的例子：`LaunchKernelCostFuncPass(cost_kind="compute|memory|latency")` 可以为同一个 `_device_kernel` 按顺序生成 3 个 sibling cost function；同时当前 tracked 目录入口 `python3 -m expectation.pass.tuning.launch_kernel_cost_func` 只承接 `compute / memory` runner。

## 计划目标

- 把共享计划正文收到当前公开方向：`cost_kind` 是任意非空、`|` 分隔且去重后的 kind 列表，不再把 `compute / memory / kind2 / kind3` 当作上界。
- 把目录级 expectation 验收口径收到当前 tracked 资产：`expectation.pass.tuning.launch_kernel_cost_func` 只接线 `launch_kernel_cost_func_compute_memory`，不再把 `multi_kind.py` / `invalid_kind.py` 写成当前目录入口必过项。
- 把“完成态”收到真实产品行为：cost function 数量等于请求的 unique `cost_kind` 数量，不再固定为 4 个。
- 保持原 wrapper、原 device func、原 `arch.launch` 不变；`dma.view/dma.reshape` helper 保留但不生成 `tuner.cost`；其他现有成本节点不因合法 kind 改变而裁剪。
- 明确产品公开合同与目录级合同验收的分层：前者由 open-kind `spec/pytest/实现` 共同定义，后者由当前 tracked `compute / memory` runner 负责。

## 当前基线

- 当前公开合同：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../../spec/pass/tuning/launch_kernel_cost_func.md) 与 [`spec/dialect/tuner.md`](../../../../../../../spec/dialect/tuner.md) 已写明 open-kind；`cost_kind` 接受任意非空 kind 名，列表形态接受任意非空、`|` 分隔且去重后的片段序列。
- 当前公开 API：`LaunchKernelCostFuncPass(cost_kind="compute|memory|latency")` 与 registry option `{"cost_kind": "compute|memory|latency"}` 已是受支持示例；单值 `compute` / `memory` 行为继续兼容。
- 当前实现入口：[`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py) 通过 `_normalize_cost_kinds(...)` 解析 open-kind 列表，错误短语为 `LaunchKernelCostFuncError: cost_kind must be a non-empty '|' separated list of unique kind names`；[`kernel_gen/dialect/tuner.py`](../../../../../../../kernel_gen/dialect/tuner.py) verifier 接受任意非空 `StringAttr` kind。
- 当前测试覆盖：[`test/pass/test_launch_kernel_cost_func.py`](../../../../../../../test/pass/test_launch_kernel_cost_func.py)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)、[`test/dialect/test_tuner_dialect.py`](../../../../../../../test/dialect/test_tuner_dialect.py) 已覆盖 `compute|memory|latency` 等 open-kind 场景。
- 当前 tracked expectation 资产：[`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py) 只接线 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)；后者当前只运行 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)。
- 当前唯一缺口：共享计划正文仍残留旧四值 API、`multi_kind.py` / `invalid_kind.py` 验收资产和“四个 cost function”完成口径，和上述真实现场不一致。

## 合同真源顺序

- 产品公开 API / IR 的真源顺序：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../../spec/pass/tuning/launch_kernel_cost_func.md) + [`spec/dialect/tuner.md`](../../../../../../../spec/dialect/tuner.md) > [`test/pass/test_launch_kernel_cost_func.py`](../../../../../../../test/pass/test_launch_kernel_cost_func.py) + [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py) + [`test/dialect/test_tuner_dialect.py`](../../../../../../../test/dialect/test_tuner_dialect.py) > 当前实现。
- 当前目录级合同验收入口的真源顺序：[`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py) > [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py) + [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)。
- 本计划正文必须同时与以上两层真源一致：既不回退 open-kind 产品合同，也不把当前未 tracked 的 `multi_kind.py` / `invalid_kind.py` 写成目录级必过资产。
- 四字段 `arch.launch` 的合同真源不归本计划所有；本计划只消费该前置结果，外部真源按 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](main_npu_demo_pipeline_fold_cse_green_plan.md) 执行。

## 方案比较与选型

- 不采用方案：为了迁就旧计划正文，把产品合同重新收回固定四值，或重新引入 `kind2/kind3` 作为公开上界。
- 不采用原因：当前 `spec/pytest/实现` 已经统一到 open-kind；若正文继续保留固定四值，会再次与真实现场分叉。
- 采用方案：计划正文明确区分“产品公开合同”和“目录级合同验收”。前者继续使用 open-kind，后者只承接当前 tracked `compute / memory` runner。
- 最小公开接口：`cost_kind="<kind0>|<kind1>|..."`；不新增 `cost_kinds` option，不新增 `kind` attr，不恢复旧 `device_func` attr。

- 不采用方案：把目录级 `compute / memory` runner 解释成产品只支持两 kind。
- 不采用原因：这会把当前 tracked expectation 覆盖范围误当成产品输入域上界，和 `spec/pytest/实现` 已支持的 open-kind 不一致。
- 采用方案：目录级 expectation 只描述“当前 tracked 合同验收资产”，而函数生成数量仍由请求的 unique `cost_kind` 数量决定。
- 最小维护收益：不需要回改实现或测试，也不给下游造成“当前必须补回 multi_kind.py / invalid_kind.py”的误导。

## 公开 API 设计

### Pass CLI / ircheck

- 公开入口：`--pass "launch-kernel-cost-func={cost_kind=compute|memory|latency}"`
- 参数顺序：`cost_kind` 内部按 `|` 左到右保序。
- 参数类型：非空字符串；每个片段必须是非空 kind 名，且整个列表去重。
- 返回值：输入 module 原地新增 cost functions；pass run 返回 module。

```text
// COMPILE_ARGS: --pass "launch-kernel-cost-func={cost_kind=compute|memory|latency}"
```

### Python Pass API

- 公开入口：`LaunchKernelCostFuncPass(cost_kind="compute|memory|latency")`
- 参数顺序：构造参数只有 `cost_kind`。
- 参数类型：`str`。
- 返回值：`ModuleOp`。
- 兼容要求：`LaunchKernelCostFuncPass(cost_kind="memory").cost_kind == "memory"` 继续成立；多值时可增加只读 `cost_kinds == ("compute", "memory", "latency")` 一类展开结果。

```python
module = LaunchKernelCostFuncPass(cost_kind="compute|memory|latency").run(module)
```

### Registry API

- 公开入口：`build_registered_pass("launch-kernel-cost-func", {"cost_kind": "compute|memory|latency"})`
- 参数顺序：pass 名称，options dict。
- 参数类型：`dict[str, str]`。
- 返回值：`LaunchKernelCostFuncPass`。

```python
load_builtin_passes()
pass_obj = build_registered_pass(
    "launch-kernel-cost-func",
    {"cost_kind": "compute|memory|latency"},
)
```

### IR 输出

```mlir
func.func @_cost_compute__device_kernel(...) -> !symbol.int<"..."> {
  %cost = tuner.cost(...) {cost_kind = "compute", op_name = "kernel.add"} : (...) -> !symbol.int<"...">
  ...
}
func.func @_cost_memory__device_kernel(...) -> !symbol.int<"..."> { ... }
func.func @_cost_latency__device_kernel(...) -> !symbol.int<"..."> { ... }
```

## 完成态定义

- 共享计划正文不再把 `compute / memory / kind2 / kind3` 写成公开上界，也不再把 `multi_kind.py` / `invalid_kind.py` 写成当前目录级验收资产。
- [`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py) 的目录入口稳定承接 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)，后者当前只运行 [`basic_all.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)。
- `LaunchKernelCostFuncPass(cost_kind="compute|memory|latency")` 这一类 open-kind 输入会为每个 unique device callee 按顺序插入与 unique `cost_kind` 数量一致的 cost function；共享 callee 在每个 kind 下仍只生成一份。
- 非法 `cost_kind` 的稳定错误短语为 `LaunchKernelCostFuncError: cost_kind must be a non-empty '|' separated list of unique kind names`。
- `tuner.cost` verifier 接受任意非空 kind 字符串，继续拒绝旧 `kind` 和 `device_func` attrs。
- 单值 `compute` / `memory` 旧行为保持不变；空段、重复段、重名 cost function、metadata attr 冲突、unsupported op 等失败路径保持显式失败。

## 验收设计

- 验收资产：[`expectation/pass/tuning/launch_kernel_cost_func/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func/__main__.py)
- 输入样例：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func`
- 锁定输出：目录入口只接线当前 tracked `compute / memory` runner，不导入 `multi_kind.py` / `invalid_kind.py` 等历史子资产。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func`

- 验收资产：[`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py)、[`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)
- 输入样例：单 wrapper 指向单 device callee，device body 含 `dma.copy`、`kernel.add`。
- 锁定输出：当前 tracked 目录级合同只锁定 `compute / memory` 两 kind 成功路径；`basic_all.py` 可通过目录 runner 独立运行。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`

- 验收资产：[`test/pass/test_launch_kernel_cost_func.py`](../../../../../../../test/pass/test_launch_kernel_cost_func.py)
- 输入样例：构造单 wrapper、共享 callee、`compute|memory|latency`、冲突 attr、unsupported op、重名 cost function。
- 锁定输出：单 kind 旧行为、open-kind 多函数生成、错误路径和去重行为。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_launch_kernel_cost_func.py`

- 验收资产：[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)、[`test/dialect/test_tuner_dialect.py`](../../../../../../../test/dialect/test_tuner_dialect.py)
- 输入样例：registry 多 kind option；`TunerCostOp(cost_kind=StringAttr("latency"))`。
- 锁定输出：registry 透传；tuner verifier 接受任意非空 kind 并继续拒绝旧 attrs。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py -k launch_kernel_cost_func`
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_tuner_dialect.py -k tuner_cost`

- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func`
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`
- 建任务依赖：创建本计划 `S1` 任务时，`dependencies` 必须填写 `T-20260422-f94ed233`；该任务是 [`main_npu_demo_pipeline_fold_cse_green_plan.md`](main_npu_demo_pipeline_fold_cse_green_plan.md) 的 `S2`。这不是执行人手工等待，也不是在本计划内修 `arch`。
- 外部依赖检查：若上述 expectation 在 pass 前报四字段 `arch.launch` parse 失败，执行人不得在本计划任务内修改 `arch`，应记录为依赖任务未满足或集成现场未同步，并等待依赖任务完成后重跑。
- Diff 反推验证：执行与审查阶段必须按实际改动文件补跑对应 pytest 或可执行脚本；计划命令只是最低集合；`expectation` 合同验收单列，不算 diff 反推测试。
- 终验 expectation：架构师终验 / 复验 / 终验修复复核时必须在最新同步现场运行与本轮改动有关的 expectation 合同验收；只有用户明确要求时才运行全量 expectation。

## 阶段拆分

### S1：launch-kernel-cost-func 多 cost_kind 红转绿收口

#### 上下文摘要

- 用户原始诉求是让 `launch-kernel-cost-func` 支持多 `cost_kind`；当前产品现场已经收口到 open-kind，目录级 tracked expectation 则只保留 `compute / memory` runner。
- 本阶段是单阶段闭环任务，首任务以 spec 起步；spec、实现、pytest、expectation 曾在同一 spec/review/merge 链内收口，当前计划正文必须与这组真实结果保持一致。
- 本阶段在建任务时依赖 `T-20260422-f94ed233`（[`main_npu_demo_pipeline_fold_cse_green_plan.md`](main_npu_demo_pipeline_fold_cse_green_plan.md) 的 `S2` 任务）；依赖完成后四字段 `arch.launch` 应已经可用，否则相关 expectation 无法进入 pass。

#### 阶段目标

- 让共享计划正文与当前 open-kind 产品合同、tracked `compute / memory` 目录入口和真实 `spec/pytest/实现` 对齐，并保持现有单 kind 行为不回退。

#### 非目标

- 不实现真实成本 evaluator。
- 不把任意新 kind 映射为实际 compute/memory 权重。
- 不修改 `analysis/func_cost`、tile pass、default pipeline 或 npu-demo lowering。
- 不在本任务内修复四字段 `arch.launch` parser；该项属于外部计划。
- 不把 `multi_kind.py` / `invalid_kind.py` 重新纳入当前 tracked expectation 目录入口。

#### 目标 spec / API

- `spec/pass/tuning/launch_kernel_cost_func.md`
- `spec/dialect/tuner.md`
- `公开 API：LaunchKernelCostFuncPass(cost_kind="compute|memory|latency")`
- `公开 API：build_registered_pass("launch-kernel-cost-func", {"cost_kind": "compute|memory|latency"})`
- `公开 IR：tuner.cost(...){cost_kind = "<kind>", op_name = "..."}`

#### 禁止修改面 / 合同真源

- `禁止修改面：.skills`
- `禁止修改面：与本计划无关的 pass / codegen / pipeline 不得顺手改`
- `禁止修改面：已有 [immutable-file] 不得修改；若执行人发现历史 immutable expectation 与当前 tracked 合同入口不一致，必须停止并向用户确认，不得顺手回改`
- `合同真源：产品公开合同按 spec/pass/tuning/launch_kernel_cost_func.md + spec/dialect/tuner.md > pytest > 当前实现；目录级合同验收按 expectation/pass/tuning/launch_kernel_cost_func/__main__.py > expectation/pass/tuning/launch_kernel_cost_func_compute_memory/**`

#### 最小功能闭环

- 计划正文明确 open-kind 与当前 tracked expectation 目录入口的分层关系，不再引用旧四值或旧 `multi_kind.py` / `invalid_kind.py` 资产。
- spec 明确 `cost_kind` 是任意非空、`|` 分隔且去重后的 kind 列表。
- pass option 解析为有序 kind tuple；拒绝空值、空段和重复段。
- pass 对每个 unique device callee、每个 kind 生成一份 cost function；插入顺序与 `cost_kind` 列表一致，函数数量不设固定上界。
- tuner dialect verifier 接受任意非空 kind；继续拒绝旧 `kind/device_func` attrs。
- tracked expectation 目录入口仅覆盖当前 `compute / memory` runner；pytest 继续覆盖 open-kind pass、本体 registry 透传和 tuner verifier。

#### 执行步骤

1. 读取本计划全局完成态、验收设计、当前 `expectation/pass/tuning/launch_kernel_cost_func/__main__.py`、`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`、`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py` 与相关 spec/test/实现；若需要引用历史 immutable expectation，只能作为背景只读核对，不得把它们重新写成当前目录入口。
2. 先确认四字段 `arch.launch` 当前是否可 parse；若不可用，记录外部依赖阻塞，不在本任务内改 arch。
3. 明确当前 tracked expectation 目录入口只接线 `launch_kernel_cost_func_compute_memory`，不把未 tracked 的 `multi_kind.py` / `invalid_kind.py` 写进当前目录级合同。
4. 更新 spec、pytest、实现与计划正文的公开口径，保证 open-kind 产品合同一致。
5. 按验收设计运行当前 tracked expectation 与相关 pytest；再按实际 diff 反推补跑相关测试。

#### 预期示例代码

```python
module = LaunchKernelCostFuncPass(
    cost_kind="compute|memory|latency",
).run(module)
```

#### 预期输出

```text
func.func @_cost_compute__device_kernel
func.func @_cost_memory__device_kernel
func.func @_cost_latency__device_kernel
cost_kind = "compute"
cost_kind = "memory"
cost_kind = "latency"
```

#### 目标验收资产

- `expectation/pass/tuning/launch_kernel_cost_func/__main__.py`：锁定当前 tracked 目录入口只承接 `compute / memory` runner。
- `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`：锁定当前 tracked `compute / memory` 目录 runner。
- `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`：锁定当前 tracked 两 kind 成功路径。
- `test/pass/test_launch_kernel_cost_func.py`：锁定多 kind 生成、去重、错误路径。
- `test/pass/test_pass_registry.py`：锁定 registry option 透传。
- `test/dialect/test_tuner_dialect.py`：锁定 tuner.cost 合法 kind 与旧 attr 拒绝。

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_launch_kernel_cost_func.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py -k launch_kernel_cost_func`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_tuner_dialect.py -k tuner_cost`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S1、全局完成态/验收设计、相关 spec/test/实现、外部 arch.launch 依赖状态`
- `最小功能闭环：写清多 kind option、cost function 生成、tuner verifier、expectation 和 pytest 的对应关系`
- `自检：除 merge 外，执行人完成前确认通用项，并补充本角色重点；禁止只写“已自检/无问题”，必须写实际检查结论`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：收口 launch-kernel-cost-func open-kind 产品合同与 tracked compute/memory expectation 目录入口，使共享计划正文、spec、实现、pytest 与当前目录级验收资产一致`
- `依赖任务：T-20260422-f94ed233`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-launch-kernel-cost-multi-kind-s1.md`

## 待确认项

- `无。用户已确认四字段 arch.launch 不并入本计划；建本计划 S1 任务时依赖项挂到 main_npu_demo_pipeline_fold_cse_green_plan 的 S2 任务 T-20260422-f94ed233。当前 tracked 目录入口只承接 launch_kernel_cost_func/__main__.py 与 launch_kernel_cost_func_compute_memory/**；若后续要重新引入历史 immutable expectation，必须拆到单独合同资产任务。`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：用户确认“四字段 arch.launch 不并入；这是建任务时的依赖项，依赖 main_npu_demo_pipeline_fold_cse_green_plan 的 S2 任务 T-20260422-f94ed233”`
- `未确认前处理要求：不适用；创建本计划 S1 任务时必须填写 T-20260422-f94ed233`
- `协同约束：当前未收到用户要求本计划必须询问 3 人；按计划书流程，至少完成架构师互评后再建任务`
- `询问记录 1：已询问大闸蟹；复评结论为通过，依赖 ID 与 immutable 处理口径已满足推进前置`
- `询问记录 2：已询问守护最好的爱莉希雅；互评结论为通过，S1 任务范围、依赖边界、旧合同排除和 spec 入口均已满足推进前置`
- `询问记录 3：已询问睡觉小分队，当前未收到冲突意见`

## 任务创建记录

- `S1=T-20260423-9c23217c，任务类型 spec，worktree=wt-20260422-launch-kernel-cost-multi-kind-s1，依赖 T-20260422-f94ed233`
- `归档前最后一次共享计划快照状态：TODO.md 计划状态曾为 1/0/1 进行中；当前 latest 远端基线 origin/main@995d5fa30c44de27ec5544706e3d15be1f75d348 仍由 done_plan 承载本计划，且自 791b9d0 起的后续主线现场均已无 TODO.md，后续状态以 done_plan 与任务记录为准`

## 计划书自检

- 已按 [`agents/standard/计划书标准.md`](../../../../../../../agents/standard/计划书标准.md) 核对结构：文档信息、任务清单、评审摘要、输入摘要、目标、基线、方案、API、完成态、验收、阶段、待确认、协同约束齐全。
- 本轮正文修复只调整计划书；未修改实现、spec、pytest 或 expectation。
- 阶段拆分为单阶段，避免为小范围改动拆纯 spec / build / review 壳层；实际任务仍按 spec -> review -> merge 链路推进。
- 已写清产品公开合同与目录级 expectation 入口的双层真源顺序，且 expectation 不替代 diff 反推测试。
- 已写清外部四字段 `arch.launch` 依赖，避免执行人误把 cost pass 任务扩大到 arch ABI。

## 参考资料

- [`agents/standard/计划书标准.md`](../../../../../../../agents/standard/计划书标准.md)：计划结构、互评、终验、diff 反推要求。
- [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory/basic_all.py)：当前 tracked compute/memory 成功路径与 helper 保留规则。
- [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](main_npu_demo_pipeline_fold_cse_green_plan.md)：四字段 `arch.launch` / shared memory size ABI 的外部前置计划。

## 归档对齐记录

时间：2026-04-25 02:02 +0800
经办人：咯咯咯
任务：T-20260425-393f25ad
任务目标：把 `launch_kernel_cost_func_multi_kind` 的计划资产对齐到 latest main 仍存在的承载位置，仅处理计划文件、归档与记录资产。
改动：将共享计划快照复制到 `agents/codex-multi-agents/log/task_records/done_plan/2026/17/launch_kernel_cost_func_multi_kind_green_plan.md`；新增 latest main 已无 `ARCHITECTURE/plan/launch_kernel_cost_func_multi_kind_green_plan.md` 与 `TODO.md` 的说明；将原 `TODO.md 计划状态` 改成归档前快照说明，避免继续引用最新主线中已不存在的状态文件。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260425-launch-kernel-cost-multi-kind-repair-s9 rev-parse HEAD origin/main` -> `995d5fa30c44de27ec5544706e3d15be1f75d348`；`git -C /home/lfr/kernelcode_generate/wt-20260425-launch-kernel-cost-multi-kind-repair-s9 ls-tree -r --name-only 791b9d0ed6a74276f2cf2e08fadd55156e874469 | rg '^ARCHITECTURE/plan/launch_kernel_cost_func_multi_kind_green_plan\\.md$|^TODO\\.md$|^agents/codex-multi-agents/log/task_records/done_plan/2026/17/launch_kernel_cost_func_multi_kind_green_plan\\.md$'` 无输出；`git -C /home/lfr/kernelcode_generate/wt-20260425-launch-kernel-cost-multi-kind-repair-s9 ls-tree -r --name-only 995d5fa30c44de27ec5544706e3d15be1f75d348 | rg '^ARCHITECTURE/plan/launch_kernel_cost_func_multi_kind_green_plan\\.md$|^TODO\\.md$|^agents/codex-multi-agents/log/task_records/done_plan/2026/17/launch_kernel_cost_func_multi_kind_green_plan\\.md$'` 仅命中当前 done_plan 承载文件，未命中 `ARCHITECTURE/plan/...` 与 `TODO.md`。`
结论：该计划的后续承载点已改为 `done_plan` 归档文件；若后续还需引用计划正文，应以本文件与任务记录为准。
