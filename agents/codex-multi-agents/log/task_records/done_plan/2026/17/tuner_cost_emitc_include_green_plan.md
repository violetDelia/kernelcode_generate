# tuner_cost_emitc_include_green_plan.md

> 说明：该文件为 `tuner_cost_emitc_include` 的归档承载快照。自 `origin/main@361405ec41f494f3cfdb24f27a9aa1378ef108d5` 起的后续主线现场，均不再包含 `ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan.md` 与 `TODO.md`；因此本计划持续由 `agents/codex-multi-agents/log/task_records/done_plan/2026/17/tuner_cost_emitc_include_green_plan.md` 承载。后续计划状态、结论和续接依据统一收口到本归档文件与对应任务记录，不再逐次跟随单个 latest commit 改写顶部说明；若需核对某一轮复验基线，以对应复验段和修复任务记录为准。

## 文档信息

- 创建者：`Codex`
- 最后一次更改：`睡觉小分队`
- 目标 `spec`：
  - [`spec/dialect/tuner.md`](../../../../../../../spec/dialect/tuner.md)
  - [`spec/dsl/emit_c.md`](../../../../../../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel.md)
  - [`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../../spec/pass/tuning/launch_kernel_cost_func.md)
  - [`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)
  - [`spec/include/api/Dma.md`](../../../../../../../spec/include/api/Dma.md)
  - [`spec/include/api/Kernel.md`](../../../../../../../spec/include/api/Kernel.md)
  - `spec/include/api/cost/Core.md`（新增）
  - `spec/include/api/cost/Dma.md`（新增）
  - `spec/include/api/cost/Kernel.md`（新增）
  - [`spec/include/npu_demo/npu_demo.md`](../../../../../../../spec/include/npu_demo/npu_demo.md)
- 目标 `API`：
  - `tuner.cost(...){cost_kind = "...", op_name = "kernel.add"} -> !symbol.int<"...">`
  - `cost_kind` 固定为 `compute` 与 `memory` 两类，其中 `memory` 表示访存开销。
  - `include/api/cost/...`：按 `include/api` 文件结构镜像定义 cost 公共接口。
  - `include/npu_demo/cost/...`：按 npu_demo target 承接 cost 实现，当前所有 kind 默认返回 `0`。
  - `emit_c(target="npu_demo")`：把 `tuner.cost` 发射成 `S_INT <name> = cost::<api_name><...>(...);`，结果可被后续 `symbol.add` 消费。
- 目标 `test`：
  - [`test/dialect/test_tuner_dialect.py`](../../../../../../../test/dialect/test_tuner_dialect.py)
  - [`test/dsl/test_emit_c.py`](../../../../../../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../../../../../../test/dsl/test_gen_kernel.py)
  - [`test/pass/test_launch_kernel_cost_func.py`](../../../../../../../test/pass/test_launch_kernel_cost_func.py)
  - [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)
  - `test/include/api/test_cost.py`（新增）
  - `test/include/npu_demo/test_cost.py`（新增）
- 目标 `验收资产`：
  - `expectation/dsl/emit_c/npu_demo/cost/`（新增目录）
  - `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/`（新增目录）
  - [`expectation/pass/tuning/launch_kernel_cost_func`](../../../../../../../expectation/pass/tuning/launch_kernel_cost_func)（仅历史证据，不作为本计划当前生效真源）
  - [`expectation/dsl/emit_c/npu_demo/__main__.py`](../../../../../../../expectation/dsl/emit_c/npu_demo/__main__.py)
- 目标 `功能实现`：
  - [`include/api/Core.h`](../../../../../../../include/api/Core.h)
  - [`include/api/Dma.h`](../../../../../../../include/api/Dma.h)
  - [`include/api/Kernel.h`](../../../../../../../include/api/Kernel.h)
  - `include/api/cost/`（新增目录）
  - [`include/npu_demo/Dma.h`](../../../../../../../include/npu_demo/Dma.h)
  - `include/npu_demo/cost/`（新增目录）
  - [`include/npu_demo/npu_demo.h`](../../../../../../../include/npu_demo/npu_demo.h)
  - [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
  - [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/dialect/tuner.py`](../../../../../../../kernel_gen/dialect/tuner.py)
  - [`kernel_gen/dsl/emit_c.py`](../../../../../../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel/emit_c`](../../../../../../../kernel_gen/dsl/gen_kernel/emit_c)

## 任务清单

> 用户已确认 4 项公开 API 决策；当前主线已包含 `T-20260423-9c23217c` 落下的旧四 kind 基线。本计划不再要求改写该已完成任务，而是直接以当前仓库状态为起点，在 `S1-S3` 中把公开合同收口到 `compute/memory` 两 kind，并补齐 include / emit_c / gen_kernel 缺口。

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1：Cost kind 固定合同、Cost include API 与 npu_demo 默认实现收口` `T-20260423-e6493d39` | `无` | `wt-20260423-tuner-cost-include-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-tuner-cost-include-s1.md` |
| `S2：emit_c tuner.cost 节点级源码发射收口` `T-20260423-084b8955` | `S1` | `wt-20260423-tuner-cost-emitc-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-tuner-cost-emitc-s2.md` |
| `S3：gen_kernel cost function 端到端源码与编译链路收口` `T-20260423-88264a9c` | `S1`，`S2` | `wt-20260423-tuner-cost-gen-kernel-s3` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-tuner-cost-gen-kernel-s3.md` |

### 历史任务承接规则

- `T-20260423-9c23217c` 视为当前主线基线，不再作为本计划 `S1` 的创建前置任务。
- `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py` 与 `expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py` 当前带 `[immutable-file]`，本计划不得修改。
- 旧四 kind 目录资产仅作为历史合同证据保留，不作为本计划当前生效真源；`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 仍是本计划的 canonical 两 kind pass 合同路径，但其目录文件与 `.gitignore` 放行若需真实入库，必须拆到单独的合同资产处理，不与当前 `T-20260423-e6493d39` 的产品 diff 混在同一条 build/review 链；immutable 文件本体仍不得改动。
- 若执行阶段发现历史四 kind 基线与本计划两 kind 合同冲突，默认在本计划任务内直接修正文档、实现和可改验收资产；不再回头要求改写已完成任务记录。

## 评审摘要

- 评审结论：`守护最好的爱莉希雅：通过；大闸蟹：通过；睡觉小分队：历史版本通过；提莫炖蘑菇：历史版本通过`
- 评审人：`守护最好的爱莉希雅；大闸蟹；睡觉小分队；提莫炖蘑菇`
- 结论摘要：`最新版本已经吸收了前两轮主要阻断：新增 `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 作为当前生效的两 kind pass expectation 真源，旧四 kind 目录只保留为历史证据；同时把 `launch-kernel-cost-func` / registry / `tuner.cost` verifier 及对应 spec/pytest 的两 kind 收口显式挂到 `S1`。此前残留的旧前置句也已改成“旧任务仅作历史基线，不再构成 `S1` 前置”，正文执行口径现已统一；`守护最好的爱莉希雅` 与 `大闸蟹` 最新复评均已通过，当前版本可以按计划流程建任务。`

## 终验 / 复验 / 修复复核记录

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`主目录 /home/lfr/kernelcode_generate 已执行 git fetch --prune；当前 HEAD 与 origin/main 同步到 d91a78cf0376046fd0f6c2d4649031f4d62c33da。`
- 执行目录：`/home/lfr/kernelcode_generate`
- 相关 expectation 摘要：`本轮只运行与本计划相关的 expectation 合同验收与入口核对。1) `expectation/dsl/emit_c/npu_demo/cost/` 当前不存在；2) `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 当前不存在；3) `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo` 当前 exit 0，但目录入口只聚合 header/kernel/dma/symbol，未纳入本计划声明的 cost 合同；4) 作为历史参考，`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func` 当前 exit 1，失败于 `multi_kind.py`，错误为 `LaunchKernelCostFuncError: cost_kind must be one of compute, memory`。`
- 最小阻断项或通过摘要：`当前仍有明确可继续收口点，因此不能给通过。最小阻断项有两条：第一，计划正文声明的当前生效 expectation 真源 `expectation/dsl/emit_c/npu_demo/cost/` 与 `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 在最新主线并不存在，导致计划自己的合同验收路径无法按正文执行；第二，现有 `expectation/dsl/emit_c/npu_demo/__main__.py` 只聚合 header/kernel/dma/symbol，未把 cost expectation 纳入目录入口，与本计划“`python3 -m expectation.dsl.emit_c.npu_demo` 应覆盖 cost 合同”的完成态不一致。只要这两处未收口，这份计划仍不能通过。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按当前终验阻断项补建唯一修复任务 T-20260424-14596a18，worktree=/home/lfr/kernelcode_generate/wt-20260424-tuner-cost-emitc-include-repair-s4，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-tuner-cost-emitc-include-repair-s4.md。任务只收当前缺失的 expectation 资产与目录入口：创建 expectation/dsl/emit_c/npu_demo/cost/、创建 expectation/pass/tuning/launch_kernel_cost_func_compute_memory/，并把 expectation/dsl/emit_c/npu_demo/__main__.py 接到 cost 合同；不得修改 [immutable-file] expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py。`

### 2026-04-25 守护最好的爱莉希雅 复验（0d3eb0c）

- 结论：`不通过`
- 验证基线：`origin/main@0d3eb0ce01f47d25adedc85ec2fc75842c0005e5；主目录 /home/lfr/kernelcode_generate 已先执行 git fetch --prune，但因本地删改与未跟踪文件未直接作为复验现场。`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260425-tuner-cost-emitc-include-recheck`
- 相关 expectation 摘要：`本轮只运行正文当前保留的相关 expectation。1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-tuner-cost-emitc-include-recheck python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory -> exit 0。2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-tuner-cost-emitc-include-recheck python3 -m expectation.dsl.emit_c.npu_demo -> exit 1；失败栈显示 expectation/dsl/emit_c/npu_demo/__main__.py 仍导入 .header / .kernel.__main__ / .dma.__main__ / .symbol.__main__，而最新干净现场的 expectation/dsl/emit_c/npu_demo/ 下仅有 __main__.py 与 cost/。`
- 最小阻断项或通过摘要：`当前仍有明确可继续收口点，因此不能给通过。唯一阻断项是：计划正文当前保留的目录入口 expectation.dsl.emit_c.npu_demo 在最新同步现场不可执行。cost 目录本身已经存在，但 expectation/dsl/emit_c/npu_demo/__main__.py 的聚合入口仍沿用旧的 header/kernel/dma/symbol 导入口径，和最新 tracked 目录结构不一致，导致本计划正文声明的合同入口无法在最新现场直接运行。`

### 2026-04-25 守护最好的爱莉希雅 补建修复任务（0d3eb0c 复验后）

- 背景：`当前唯一阻断项不是 pass expectation，而是 expectation.dsl.emit_c.npu_demo 目录入口仍按旧的 header/kernel/dma/symbol 结构聚合，和最新真实文件集合（仅 __main__.py 与 cost/）不一致。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按当前阻断项补建当前唯一修复任务 T-20260425-179e2ee1，worktree=/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5，记录文件=/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/agents/codex-multi-agents/log/task_records/2026/17/20260425-tuner-cost-emitc-include-repair-s5.md。任务边界只收 expectation/dsl/emit_c/npu_demo 目录入口与当前真实文件集合的对齐，以及直接关联的实现/spec/test 收口；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测。`

### 2026-04-25 守护最好的爱莉希雅 任务边界确认（T-20260425-179e2ee1）

- 当前状态：`T-20260425-179e2ee1 已完成并进入 DONE，不再继续在同一任务号下追加修改。`
- 边界确认：`该任务处于执行期时，允许直接修改 expectation/dsl/emit_c/npu_demo/__main__.py、expectation/dsl/emit_c/npu_demo/cost/__main__.py，以及与目录入口修正直接相关的 helper 或 companion 文件；不得触碰任何 [immutable-file]。`
- 当前口径：`若后续再出现同类 expectation 入口问题，应新建任务承接；不要在已完成的 T-20260425-179e2ee1 下继续推进。`

### 2026-04-25 守护最好的爱莉希雅 继续推进复验（361405ec）

- 结论：`不通过`
- 验证基线：`origin/main@361405ec41f494f3cfdb24f27a9aa1378ef108d5；主目录 /home/lfr/kernelcode_generate 已先执行 git fetch --prune，但因本地删改与未跟踪文件未直接作为复验现场。`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260425-tuner-cost-emitc-include-recheck-2`
- 相关 expectation 摘要：`本轮继续只运行正文当前保留的相关 expectation。1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-tuner-cost-emitc-include-recheck-2 python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory -> exit 0。2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-tuner-cost-emitc-include-recheck-2 python3 -m expectation.dsl.emit_c.npu_demo -> exit 0；目录入口当前已只聚合 cost 合同并可直接运行。`
- 最小阻断项或通过摘要：`产品侧与正文当前保留的合同入口已经收口，但最新同步现场本身没有 ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan.md，也没有 TODO.md。当前仍可继续收口的点只剩计划资产与最新主线现场的对齐；在这一步完成前，不能把这份计划当作已完成的有效归档对象。`

### 2026-04-25 守护最好的爱莉希雅 补建修复任务（361405ec 继续推进复验后）

- 背景：`当前唯一阻点不在实现、spec、pytest 或正文保留的 expectation，而在计划资产本身尚未与最新主线现场对齐。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按当前阻点补建当前唯一修复任务 T-20260425-5fd7d2a1，worktree=/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s6，记录文件=/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s6/agents/codex-multi-agents/log/task_records/2026/17/20260425-tuner-cost-emitc-include-repair-s6.md。任务边界只收计划资产与最新主线现场的对齐，以及直接关联的归档或记录收口；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测。`

## 任务创建记录

- `S1=T-20260423-e6493d39，任务类型 spec，worktree=wt-20260423-tuner-cost-include-s1，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-tuner-cost-include-s1.md`
- `S2=T-20260423-084b8955，任务类型 spec，依赖 T-20260423-e6493d39，worktree=wt-20260423-tuner-cost-emitc-s2，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-tuner-cost-emitc-s2.md`
- `S3=T-20260423-88264a9c，任务类型 spec，依赖 T-20260423-e6493d39,T-20260423-084b8955，worktree=wt-20260423-tuner-cost-gen-kernel-s3，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-tuner-cost-gen-kernel-s3.md`
- `归档前最后一次共享计划快照状态：TODO.md 计划状态曾为 3/0/3 进行中；自 361405ec 起的后续主线现场均已无 TODO.md，本计划持续由 done_plan 承载，后续状态以 done_plan 与任务记录为准；若需核对某一轮复验基线，以对应复验段和修复任务记录为准`

## 归档对齐记录

时间：2026-04-25 10:18 +0800
经办人：睡觉小分队
任务：T-20260425-5fd7d2a1
任务目标：把 `tuner_cost_emitc_include` 的计划资产对齐到 latest main 仍存在的承载位置，仅处理计划文件、归档与记录资产。
改动：将共享计划快照复制到 `agents/codex-multi-agents/log/task_records/done_plan/2026/17/tuner_cost_emitc_include_green_plan.md`；新增 latest main 已无 `ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan.md` 与 `TODO.md` 的说明；将原 `TODO.md 计划状态` 改成归档前快照说明，避免继续引用最新主线中已不存在的状态文件。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s6 ls-tree -r --name-only 361405ec41f494f3cfdb24f27a9aa1378ef108d5 | rg '^ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan\\.md$|^TODO\\.md$|^agents/codex-multi-agents/log/task_records/done_plan/2026/17/tuner_cost_emitc_include_green_plan\\.md$'` 无输出；具体复验基线对照已写入当前任务记录 [`20260425-tuner-cost-emitc-include-repair-s6.md`](../../../2026/17/20260425-tuner-cost-emitc-include-repair-s6.md)，当前归档对齐记录只保留稳定承载结论。`
结论：该计划的后续承载点已改为 `done_plan` 归档文件；后续现行说明不再逐次跟随单个 latest commit 改写，若还需引用计划正文或核对某一轮复验基线，应以本文件、对应复验段和任务记录为准。

## 输入摘要

- 目标：`launch-kernel-cost-func` 生成的 sibling cost function 在最终 emitc 后不再只保留 IR `tuner.cost`，而是能生成可编译的 C++ cost helper 调用。
- 不做什么：本计划不实现真实成本模型、不做成本表查找、不改变原 kernel helper 的计算语义；当前所有 npu_demo cost helper 默认返回 `0`。
- 当前痛点：`tuner.cost` 已能表达 `cost_kind/op_name` 和原 op operands，但 include 下没有 cost API，emit_c 也没有 `tuner.cost` 节点级发射；生成到 C++ 时成本函数无法落到可编译 helper。
- 完成后用户最想看到的例子：`kernel.add` 正常生成 `add<...>(out, lhs, rhs);`，对应的 `tuner.cost(... op_name="kernel.add")` 生成 `S_INT cost0 = cost::add<... Kind>(out, lhs, rhs);`，并参与后续 `symbol.add` 总成本累计。

## 计划目标

- 把 `launch-kernel-cost-func`、`tuner.cost` verifier 与 pass registry 的公开合法 kind 从旧四 kind 收口为 `compute/memory` 两类，并用新的两 kind expectation 入口锁定。
- 新增 `include/api/cost` 公共 cost API，目录结构与 `include/api` 对齐，本轮覆盖当前 `Kernel` 与 `Dma` 公共 helper 集合。
- 新增 `include/npu_demo/cost` 后端实现，当前所有 npu_demo kind 默认返回 `0`，保证生成代码可编译、可链接、可执行。
- 固定 `cost_kind` 合法集合为 `compute/memory`，其中 `memory` 表示访存开销；不由 target 配置指定。
- 让 `emit_c(target="npu_demo")` 支持 `tuner.cost`，按 `op_name` 映射到对应 cost helper，按原 op operands 顺序生成 out-first C++ 调用。
- 保持 `tuner.cost` 的 IR 语义不变：仍返回 `!symbol.int`，仍使用 `cost_kind/op_name` metadata，仍不恢复旧 `kind/device_func` attr。
- 用 `expectation/dsl/emit_c/npu_demo/cost` 锁定单 op cost 源码文本，用 pytest 锁定 include 可编译和 emit_c 节点级行为。

## 当前基线

- 当前公开合同：[`spec/dialect/tuner.md`](../../../../../../../spec/dialect/tuner.md) 把 `tuner.cost` 定义为成本函数内的局部成本节点，固定返回 `!symbol.int`，但明确“不负责运行期求值、调度策略、搜索空间算法或真实 cost table”。
- 当前 pass / registry / verifier 合同：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../../../../../spec/pass/tuning/launch_kernel_cost_func.md)、[`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)、[`spec/dialect/tuner.md`](../../../../../../../spec/dialect/tuner.md) 以及对应实现/pytest 仍停在旧四 kind 基线；前置计划 [`launch_kernel_cost_func_multi_kind_green_plan.md`](launch_kernel_cost_func_multi_kind_green_plan.md) 已把主线实现收口到固定 `compute/memory/kind2/kind3`。
- 当前 include API：[`include/api/Kernel.h`](../../../../../../../include/api/Kernel.h) 只有计算 helper 声明，模板顺序为先 space 后 type；[`include/npu_demo/Kernel.h`](../../../../../../../include/npu_demo/Kernel.h) 承接实现；目前不存在 `include/api/cost` 或 `include/npu_demo/cost`。
- 当前 emit_c 实现：[`kernel_gen/dsl/emit_c.py`](../../../../../../../kernel_gen/dsl/emit_c.py) 已支持 `kernel.binary_elewise`、`kernel.matmul` 等 npu_demo helper 调用；`kernel_gen/dsl/gen_kernel/emit_c/kernel.py` 仍通过旧实现桥接 kernel op；当前没有 `TunerCostOp` 的注册或旧实现分支。
- 当前 expectation：旧目录 `expectation/pass/tuning/launch_kernel_cost_func/` 里仍是四 kind 历史资产，其中 `basic_all.py` 与 `invalid_kind.py` 为 `[immutable-file]`；当前仓库还没有专门承接 `compute/memory` 两 kind 的可改 pass expectation 入口。`expectation/dsl/emit_c/npu_demo/kernel/binary_add.py` 已锁定普通计算 helper 文本，但没有对应 cost helper 文本。
- 当前缺口：即使 pass 成功生成了旧四 kind 版本的 cost function 基线，后续 emitc 仍无法把 `tuner.cost` 降成 C++；include 也没有每个 API 对应 kind 的 cost helper；同时当前缺少新的两 kind pass expectation 真源，导致公开合同从旧四 kind 收窄到 `compute/memory` 仍未被黑盒资产锁定。

## 合同真源顺序

- `expectation/dsl/emit_c/npu_demo/cost > spec/dsl/emit_c.md + spec/include/api/cost/*.md + spec/include/npu_demo/npu_demo.md > test/dsl/test_emit_c.py + test/dsl/test_gen_kernel.py + test/include/api/test_cost.py + test/include/npu_demo/test_cost.py > 当前实现`
- `expectation/pass/tuning/launch_kernel_cost_func_compute_memory > spec/pass/tuning/launch_kernel_cost_func.md + spec/pass/registry.md + spec/dialect/tuner.md > test/pass/test_launch_kernel_cost_func.py + test/pass/test_pass_registry.py + test/dialect/test_tuner_dialect.py > 当前实现`
- `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`、`multi_kind.py`、`shared_callee_once.py`、`invalid_kind.py` 仅作为旧四 kind 历史证据，不作为本计划当前生效真源。
- 上述顺序只定义计划层 canonical 口径；当前任务链的 build/review diff 仍按角色边界执行。若 `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 或 `.gitignore` 放行需要真实入库，必须拆到单独的合同资产处理，不与当前产品 diff 混在同一条 build/review 链。
- 若 emit_c cost expectation 与 pass expectation 冲突，优先确认 `tuner.cost` IR 是否符合 pass 真源；不允许在 emit_c 侧引入只服务源码输出的私有 IR attr。

## 方案比较与选型

- 不采用方案：在 emit_c 中把 `tuner.cost` 直接折叠成常量 `0`。
- 不采用原因：这会绕过用户要求的 include cost API，后续无法替换为真实 target cost 实现，也看不到“不同 kind 的 cost 函数”源码合同。
- 采用方案：`tuner.cost` 发射为显式 cost helper 调用，npu_demo 默认实现返回 `0`。
- 维护收益：IR、emit_c、include API 三层一一对应；以后只改 target cost helper 实现即可引入真实成本。

- 不采用方案：继续把 cost helper 放在 `include/npu_demo/Kernel.h` 旁边混写。
- 不采用原因：用户明确要求 `include/api/cost/...`，且 cost API 与计算 API 返回类型、语义、目标实现都不同；混写会让公开接口难以审查。
- 采用方案：新增 `include/api/cost` 和 `include/npu_demo/cost` 两棵树，文件结构镜像现有 `include/api`，例如 `cost/Kernel.h` 覆盖 kernel helper 的成本接口。
- 维护收益：每个公开 API 都能找到对应 cost API，执行人和审查人可以按文件结构机械检查覆盖率。

- 不采用方案：只支持 `kernel.add` 的 cost emit。
- 不采用原因：用户要求“每个 api 接口实现对应 kind 的 cost 函数”，并已确认本轮 `dma/kernel` 都支持；只做 add 会立即形成缺口。
- 采用方案：S1 覆盖 `include/api/Kernel.h` 与 `include/api/Dma.h` 已公开 helper 集合；S2 按 `op_name` 映射到这些 helper；暂不把未公开的旧 `Nn` helper 纳入。
- 维护收益：覆盖边界与 `spec/include/api/Kernel.md`、`spec/include/api/Dma.md` 一致，不重新引入已删除的 `Nn.h` 公共层。

## 公开 API 设计

> 用户已确认本节 4 项 API 决策：`cost_kind` 固定为 `compute/memory` 两类；C++ helper 使用 `cost::add` 这类扁平函数名；模板参数与原 API 保持一致并追加 kind；本轮 Kernel/Dma 都支持。

### 已确认：Cost kind 固定为 compute/memory

- 公开位置：`include/api/cost/Core.h`
- 合法 IR 字符串：`compute`、`memory`。
- C++ 公共 kind 定义：`namespace npu_demo::cost { enum class CostKind { Compute, Memory }; }`
- 返回类型：所有 cost helper 返回 `S_INT`。
- 默认实现：npu_demo 当前 `Compute/Memory` 均返回 `0`。
- verifier 规则：`tuner.cost.cost_kind` 仍是字符串 attr；合法集合固定为 `compute|memory`。缺少 `cost_kind`、空值、重复值、或传入 `kind1/kind2/kind3/all` 等非公开值时必须稳定失败。
- 历史基线说明：`T-20260423-9c23217c` 仅作为旧四 kind 历史基线记录保留；本计划不再以其为 `S1` 前置，当前公开合同直接由 `S1-S3` 收口到 `compute/memory`。

### 已确认：Kernel/Dma cost helper 命名

- 公开位置：`include/api/cost/Kernel.h`
- 公开位置：`include/api/cost/Dma.h`
- 命名空间：`namespace npu_demo::cost`
- 函数形态示例：

```cpp
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT add(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
```

- emit_c 输出示例：

```cpp
S_INT cost0 = cost::add<GM, float, float, cost::CostKind::Compute>(
    out /*out*/, lhs /*lhs*/, rhs /*rhs*/);
```

- 规则：不使用 `cost::kernel::add` 或 `cost<OpTag, ...>`；`op_name="kernel.add"` 映射到 `cost::add`，`op_name="dma.copy"` 映射到 `cost::copy`。若 Kernel 与 Dma 未来出现同名且同签名 helper，必须在 spec 中先显式处理冲突，不允许靠 C++ 重载碰运气。

### 已确认：模板参数顺序与原 API 保持一致

- 规则：每个 cost helper 的模板参数先逐字保持对应 `include/api` helper 的模板参数顺序，再在末尾追加 `CostKind Kind`。
- 单 space kernel helper：若原 API 是 `<Space, InType, OutType>`，cost API 为 `<Space, InType, OutType, Kind>`。
- matmul helper：若原 API 是 `<LhsSpace, RhsSpace, OutSpace, LhsType, RhsType, OutType>`，cost API 为 `<LhsSpace, RhsSpace, OutSpace, LhsType, RhsType, OutType, Kind>`。
- Dma helper：逐个按 `include/api/Dma.h` 的模板参数顺序复制，再追加 `Kind`；不得为了 cost 单独重排 `src/dst space` 或 dtype 参数。

### `tuner.cost` 到 C++ 的发射规则

- 输入 IR：

```mlir
%cost = tuner.cost(%out, %lhs, %rhs) {
  space = #nn.space<global>,
  cost_kind = "compute",
  op_name = "kernel.add"
} : (!nn.memory<[4], [1], f32, #nn.space<global>>,
     !nn.memory<[4], [1], f32, #nn.space<global>>,
     !nn.memory<[4], [1], f32, #nn.space<global>>) -> !symbol.int<"LOCAL">
```

- 输出：

```cpp
S_INT cost0 = cost::add<GM, float, float, cost::CostKind::Compute>(
    out /*out*/, lhs /*lhs*/, rhs /*rhs*/);
```

- 绑定规则：`emit_c_op(TunerCostOp)` 必须给 result 分配 `S_INT` 局部变量名；后续 `symbol.add` 通过 `emit_c_value(%cost)` 引用该变量。
- 参数规则：C++ 参数顺序与原 `tuner.cost` operand 顺序一致；`launch-kernel-cost-func` 当前对 `kernel.add` 透传为 `out, lhs, rhs`，因此生成 out-first。
- 失败规则：未知 `op_name`、缺少必须 attr、operand 类型与 helper 模板不匹配、`cost_kind` 不是 `compute|memory` 时必须显式失败，不得静默生成 `0`。

## 用户确认结论

1. `cost_kind` 合法集合固定为 `compute/memory`，其中 `memory` 表示访存，不再采用 `kind1/kind2/kind3` 或 target 配置真源。
2. C++ cost helper 使用 `cost::add`、`cost::copy` 这类 `namespace npu_demo::cost` 下的扁平函数名。
3. Cost helper 模板参数与对应 `include/api` helper 完全一致，并在末尾追加 kind 参数。
4. `include/api/cost` 与 `include/npu_demo/cost` 本轮同时覆盖 `Kernel` 与 `Dma`。

## 完成态定义

- `include/api/cost` 存在，并按 `include/api` 结构覆盖 `Core.h`、`Kernel.h`、`Dma.h`。
- `include/npu_demo/cost` 存在，并为 npu_demo 的 `compute/memory` 两个 cost kind 提供默认返回 `0` 的实现。
- `include/npu_demo/npu_demo.h` 聚合 cost API 与 npu_demo cost 实现；生成源码只需 `#include "include/npu_demo/npu_demo.h"` 与 `using namespace npu_demo;` 即可编译 cost helper。
- `emit_c(target="npu_demo")` 能把 `tuner.cost` 发射为 `S_INT` 局部变量定义，并能被 `symbol.add`、`symbol.for` 成本累计链消费。
- `kernel.add`、`kernel.sub`、`kernel.mul`、`kernel.truediv`、比较、`exp/select/reduce/matmul/img2col` 的 cost helper 覆盖率与 `include/api/Kernel.h` 保持一致。
- `dma.copy` 等 pass 会生成 `tuner.cost` 的 Dma op 也必须有 emit_c cost helper，不允许 cost function 只在 kernel op 上可编译。

## 验收设计

- 验收资产：`expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py`
- 输入样例：包含普通 `kernel.binary_elewise(kind="add")` 与同 operands 的 `tuner.cost(... op_name="kernel.add")`。
- 锁定输出：普通 op 生成 `add<...>(...)`；cost op 生成 `S_INT <val> = cost::add<...>(...)`；`symbol.add` 使用该 cost 变量。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py`

- 验收资产：`expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py`
- 输入样例：`tuner.cost(%out, %lhs, %rhs) {op_name = "kernel.matmul", cost_kind = "..."}`
- 锁定输出：模板顺序覆盖多 space、多 dtype 与 Kind；参数保持 `out/lhs/rhs`。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py`

- 验收资产：`expectation/dsl/emit_c/npu_demo/cost/dma_copy.py`
- 输入样例：`tuner.cost(%dst, %source) {op_name = "dma.copy", cost_kind = "..."}`
- 锁定输出：Dma cost helper 可编译，参数注释保持 `dst/source`。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/emit_c/npu_demo/cost/dma_copy.py`

- pytest：`test/include/api/test_cost.py`
- 验收目标：头文件可被独立 include；`cost::CostKind::{Compute, Memory}`、Kernel/Dma cost helper 声明、模板实例化与返回 `S_INT` 可编译。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_cost.py`

- pytest：`test/include/npu_demo/test_cost.py`
- 验收目标：npu_demo 默认 cost helper 实现返回 `0`，`include/npu_demo/npu_demo.h` 聚合后可直接使用。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/npu_demo/test_cost.py`

- pytest：`test/dsl/test_emit_c.py`、`test/dsl/test_gen_kernel.py`
- 验收目标：`TunerCostOp` 节点级发射、函数级 cost sibling source、未知 `op_name/cost_kind` 失败路径。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_emit_c.py -k "tuner_cost or npu_demo"`
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py -k "tuner_cost or cost_function or npu_demo"`

- 验收资产：`expectation/pass/tuning/launch_kernel_cost_func_compute_memory/__main__.py`
- 输入样例：`launch-kernel-cost-func` 仅生成 `compute/memory` 两类 sibling cost function；旧四 kind 目录不再参与本计划当前生效合同。
- 锁定输出：只出现 `_cost_compute_*` 与 `_cost_memory_*`；非法 `kind2/kind3` 由 pass/verifier/registry 稳定失败；目录 runner 只执行新的两 kind 资产。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`

- pytest：`test/pass/test_launch_kernel_cost_func.py`、`test/pass/test_pass_registry.py`、`test/dialect/test_tuner_dialect.py`
- 验收目标：`launch-kernel-cost-func`、registry 与 `tuner.cost` verifier 的合法集合已收口到 `compute/memory`；旧四 kind 不再是当前公开合同。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_launch_kernel_cost_func.py -k "launch_kernel_cost_func"`
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py -k "launch_kernel_cost_func"`
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_tuner_dialect.py -k "tuner_cost"`

- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo`
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`
- Diff 反推验证：执行与审查阶段必须按实际 diff 补跑对应 pytest 或可执行脚本；`expectation` 是合同验收资产，不替代 diff 反推测试。

## 阶段拆分

### S1：Cost kind 固定合同、Cost include API 与 npu_demo 默认实现收口

#### 上下文摘要

- 用户要求 `include/api/cost/...` 与 `include/api` 文件结构一致，且 npu_demo 每个 API 接口实现对应 kind 的 cost 函数，当前默认全部为 `0`。
- 用户已确认 `cost_kind` 合法集合固定为 `compute/memory`，其中 `memory` 表示访存。
- 当前主线已包含 `T-20260423-9c23217c` 落下的旧四 kind 基线；本阶段直接在当前代码上把公开合同收口到两 kind，不再回头改写已完成任务记录。
- 旧目录里的 `basic_all.py` 与 `invalid_kind.py` 带 `[immutable-file]`，本阶段不得修改；两 kind 合同需用新增可改资产或可改目录入口收口。
- 本阶段不只写 spec；必须同时收口 `launch-kernel-cost-func` / `tuner.cost` / registry 的两 kind 公开合同、公共声明、npu_demo 默认实现、聚合头与 include 编译测试。

#### 阶段目标

- 建立固定 `compute/memory` cost kind 合同与 cost include 层，明确新的两 kind pass expectation 真源，并保证后续 emit_c 生成的 cost helper 有可编译落点。

#### 非目标

- 不实现真实 cost evaluator。
- 不重写 `launch-kernel-cost-func` 的 sibling cost function 拓扑、callee 去重或 `symbol.add` 累计结构；本阶段只收口合法 `cost_kind` 集合、相关 verifier / registry / spec / pytest 与两 kind expectation 真源。
- 不新增未进入 `include/api` 公开层的旧 `Nn` helper。

#### 禁止修改面 / 合同真源

- `禁止修改面：.skills`
- `禁止修改面：已有 [immutable-file] 不得修改`
- `计划层 canonical：expectation/pass/tuning/launch_kernel_cost_func_compute_memory > spec/pass/tuning/launch_kernel_cost_func.md + spec/pass/registry.md + spec/dialect/tuner.md + spec/include/api/cost/* > test/pass/test_launch_kernel_cost_func.py + test/pass/test_pass_registry.py + test/dialect/test_tuner_dialect.py + test/include/api/test_cost.py + test/include/npu_demo/test_cost.py > pass/verifier/include 实现`
- `当前 T-20260423-e6493d39 的 build/review diff 边界：只纳入 spec / kernel_gen / include / pytest 相关改动；不混入 .gitignore 与 expectation/pass/tuning/launch_kernel_cost_func_compute_memory/** 文件改动。`

#### 最小功能闭环

- 明确 `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 是本计划的 canonical 两 kind pass 合同路径；当前 S1 build/review 只需要把 spec / include / pytest / pass 口径收到该路径，不在本任务 diff 中直接纳入该目录文件或 `.gitignore` 放行。
- 收口 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`kernel_gen/passes/registry.py` 与 `kernel_gen/dialect/tuner.py` 的公开合法集合到 `compute/memory`。
- 更新 `spec/pass/tuning/launch_kernel_cost_func.md`、`spec/pass/registry.md`、`spec/dialect/tuner.md` 与对应 pytest，使之不再把 `kind2/kind3` 作为当前公开合同。
- 新增 cost spec，明确 `cost::CostKind::{Compute, Memory}`、返回 `S_INT`、模板顺序、参数顺序。
- 新增 `include/api/cost/Core.h`、`include/api/cost/Kernel.h`、`include/api/cost/Dma.h`。
- 新增 `include/npu_demo/cost/Core.h`、`include/npu_demo/cost/Kernel.h`、`include/npu_demo/cost/Dma.h`，所有 helper 默认 `return 0;`。
- 更新 `include/npu_demo/npu_demo.h` 聚合 cost 头。
- 新增 include pytest，覆盖至少 Kernel 的 `add/sub/mul/matmul` 和 Dma 的 `copy/slice/deslice` 模板实例化。

#### 验收必过项目

- `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 仍是目录级合同验收入口；若当前任务链尚未单独纳入该目录文件，不得用 worktree 本地副本或 `.gitignore` 临时放开的文件证明当前 diff 已通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_launch_kernel_cost_func.py -k "launch_kernel_cost_func"`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py -k "launch_kernel_cost_func"`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_tuner_dialect.py -k "tuner_cost"`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_cost.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/npu_demo/test_cost.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/npu_demo/test_public_namespace.py`

#### Diff 反推要求

- 若改动 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`kernel_gen/passes/registry.py` 或 `kernel_gen/dialect/tuner.py`，必须补跑 pass/registry/dialect 对应 pytest 与新的两 kind pass expectation。
- 若改动 `include/api/Core.h` 或 `include/npu_demo/Core.h`，必须补跑 core 相关 include pytest。
- 若改动 `include/npu_demo/npu_demo.h`，必须补跑 public namespace 与至少一个实际 C++ 编译测试。

#### 记录要求

- 任务记录写入对应 worktree 记录文件。
- 记录 `自检` 与 `Diff 反推自测`，明确固定 `compute/memory` kind、模板顺序、Kernel/Dma 覆盖率、默认返回 `0` 是否与本计划一致。
- 若当前 build/review diff 不纳入 `.gitignore` 与 `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/**`，记录里必须明确“已拆出当前 diff，只保留 canonical 路径说明”，不得把未入索引的本地目录当成通过依据。

### S2：emit_c tuner.cost 节点级源码发射收口

#### 上下文摘要

- `launch-kernel-cost-func` 已将原 op 克隆为 `tuner.cost` 节点；本阶段让 `target=npu_demo` 下该节点能发射为 C++ cost helper 调用。
- 本阶段依赖 S1 的固定 cost kind 合同、C++ helper 名称和模板顺序。

#### 阶段目标

- 让单个 `tuner.cost` 在 `emit_c(target="npu_demo")` 下生成 `S_INT` 局部变量，并能被后续 symbol 表达式引用。

#### 非目标

- 不改变普通 `kernel.*` 或 `dma.*` 的计算 helper 输出。
- 不在 emit_c 中计算真实成本。
- 不吞掉未知 op，未知 `op_name` 必须显式失败。

#### 禁止修改面 / 合同真源

- `禁止修改面：已有 [immutable-file] expectation 不得修改；需要新增 cost expectation 时新建文件`
- `合同真源：expectation/dsl/emit_c/npu_demo/cost > spec/dsl/emit_c.md > test/dsl/test_emit_c.py > emit_c 实现`

#### 最小功能闭环

- `kernel_gen.dsl.gen_kernel.emit_c` 注册或旧实现分支支持 `TunerCostOp`。
- 按 `op_name` 映射到 cost helper；至少覆盖 `kernel.add`、`kernel.matmul`、`dma.copy`，并按完成态扩展到 Kernel/Dma 全集合。
- 生成结果变量名并绑定到 `TunerCostOp.result`，后续 `symbol.add` 可引用。
- 新增 cost expectation，包含 case 列表和“检验什么”的注释。
- pytest 覆盖未知 `op_name`、未知 `cost_kind`、缺失 memory 类型等失败路径。

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/emit_c/npu_demo/cost/dma_copy.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_emit_c.py -k "tuner_cost or npu_demo"`

#### Diff 反推要求

- 若改动 package-style emit_c 注册表，必须补跑 `test_emit_c_package_registers_common_op_and_value_types` 或对应新增注册测试。
- 若改动旧 `kernel_gen/dsl/emit_c.py`，必须补跑相关 npu_demo kernel/dma emit_c pytest 和新增 cost expectation。

#### 记录要求

- 任务记录写入对应 worktree 记录文件。
- 记录 `自检` 与 `Diff 反推自测`，明确 `tuner.cost` result 是否可被 `symbol.add` 正确引用。

### S3：gen_kernel cost function 端到端源码与编译链路收口

#### 上下文摘要

- S2 只保证单节点可发射；本阶段验证 `launch-kernel-cost-func` 生成的 sibling cost function 在完整 `gen_kernel(target="npu_demo")` 中输出可编译源码。

#### 阶段目标

- 让包含 `kernel()` 与多个 `_cost_<kind>_kernel()` 的 module 生成 host/kernel/cost 源码，且 include 聚合、using namespace、S_INT 返回、symbol.add 累计都能闭环。

#### 非目标

- 不把 cost function 自动接入运行时调度或搜索器。
- 不改变原 kernel launch 行为。
- 不实现真实 non-zero cost。

#### 禁止修改面 / 合同真源

- `合同真源：expectation/pass/tuning/launch_kernel_cost_func_compute_memory + expectation/dsl/emit_c/npu_demo/cost > spec/dsl/gen_kernel.md + spec/pass/tuning/launch_kernel_cost_func.md > test/dsl/test_gen_kernel.py + test/pass/test_launch_kernel_cost_func.py > gen_kernel / emit_c / pass 实现`
- `禁止修改面：已有 [immutable-file] 不得修改`

#### 最小功能闭环

- 完整 module 中普通 kernel function 与 cost function 都能由 `gen_kernel` 输出。
- `cost_kind` 列表为 `compute/memory` 并生成多个 cost functions 时，每个函数体都调用对应 C++ Kind 的 cost helper。
- `func.return %total : !symbol.int` 发射为 `return total;`。
- npu_demo 头文件聚合后可编译至少一个包含 cost function 的源文件。

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py -k "tuner_cost or cost_function or npu_demo"`

#### Diff 反推要求

- 若改动 gen_kernel 函数级源码组装，必须补跑 `test/dsl/test_gen_kernel.py` 中 npu_demo launch、header、return 和 module source 相关测试。
- 若改动 include 聚合或 C++ 编译脚本，必须补跑 include/npu_demo 编译测试。

#### 记录要求

- 任务记录写入对应 worktree 记录文件。
- 记录 `自检` 与 `Diff 反推自测`，明确完整源码是否同时包含普通 kernel 和 cost functions。

## 协同约束与询问记录

- 用户要求“多和别人讨论，我来决策”；用户已确认 4 项 API 决策，本计划需在复评通过后再建任务。
- 已询问对象 4 个，覆盖：
  - `睡觉小分队`：spec/API 合同与 `cost_kind` 名称边界；固定 compute/memory 版本复评通过。
  - `大闸蟹`：任务拆分、前置依赖与 include/emit_c/gen_kernel 链路边界；固定 compute/memory 版本复评结论为通过，S1 对改写后 T-20260423-9c23217c 的完成依赖，以及旧任务 immutable expectation 的处理口径已收口。
  - `守护最好的爱莉希雅`：计划书标准、禁止修改面与可执行性；固定 compute/memory 版本复评通过。
  - `提莫炖蘑菇`：审查风险、旧路径残留和黑盒 expectation 覆盖；固定 compute/memory 版本复评通过。
- 询问记录：
  - `守护最好的爱莉希雅：用户确认前版本通过；用户确认后版本待重新复评。`
  - `守护最好的爱莉希雅：用户确认后版本最小需改项。API 与阶段边界已按用户决策收口，但 T-20260423-9c23217c 的旧固定 kind 任务仍在 TODO 中；建任务前需明确该任务是暂停、删除还是改写，不能保留三选一。`
- `守护最好的爱莉希雅：榕同步最新用户决策，target 配置版本复评请求作废；改为固定 cost_kind，当前只有 compute 与 memory/访存。本计划需重写后重新复评。`
- `守护最好的爱莉希雅：最终固定 compute/memory 版本复评通过。任务粒度和依赖关系清楚；原版本把 T-20260423-9c23217c 写成 S1 前置。`
- `大闸蟹：通过。S1/S2/S3 拆分合理，Kernel/Dma、cost::add/cost::copy、模板末尾追加 CostKind 的边界清楚；原版本把 T-20260423-9c23217c 写成改写后前置。`
- `大闸蟹：补充复评。若现场 T-20260423-9c23217c 已完成并离开 TODO，则“先改写该任务再开 S1”已构成必须写回正文的执行阻断；若任务系统不能改写已完成任务，正文只能停在向用户确认，不能自行替换成新任务。`
- `用户确认：cost_kind 固定为 compute/memory，其中 memory 表示访存；不由 target 指定；helper 使用 cost::add 这类扁平 cost namespace；模板参数与 api 保持一致；Dma/Kernel 都支持。计划已按该决策重写，需重新复评。`
- `用户最新决策：不补前置任务，计划书直接与当前主线状态对齐；T-20260423-9c23217c 只作为历史四 kind 基线，不再作为 S1 创建前置。`
- `榕根据用户最新决策收口：正文已改为“以当前主线为基线继续推进”，删除失效的“改写已完成任务”前置；下一步是按新正文重提复评，而不是补建默认替代任务。`
- `守护最好的爱莉希雅：不通过。目录级合同真源与 S3 合同验收仍直接指向 expectation/pass/tuning/launch_kernel_cost_func 全目录，而该目录里的只读旧四 kind 资产未与新的两 kind 入口分流；同时 S1 的非目标与计划目标/当前基线对 launch-kernel-cost-func pass、tuner verifier 及其 spec/pytest 的收口要求相互冲突。`
- `大闸蟹：最小需改项。两 kind 版本必须由明确的新 pass expectation 资产承接，旧四 kind 目录只能保留为只读历史证据；同时要把 pass / verifier / registry / spec / pytest 的两 kind 收口显式挂到某一阶段，不得悬空。`
- `榕根据最新两份复评收口：新增 `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 作为本计划当前生效的两 kind pass expectation 真源；S1 明确承接 launch-kernel-cost-func / registry / tuner verifier 与对应 spec/pytest 的两 kind 收口。`
- `大闸蟹：最新最小需改项。正文主体已收住新两 kind pass expectation 真源和 S1 对 pass / registry / tuner verifier 的承接，但公开 API 设计里仍残留“`T-20260423-9c23217c` 不能按原描述继续推进”的旧句；该句会与后文“旧任务仅作历史基线、S1 直接以当前主线推进”冲突。`
- `守护最好的爱莉希雅：最新最小需改项。上轮两条阻断已收口，但正文“已确认：Cost kind 固定为 compute/memory”里仍保留旧句“`T-20260423-9c23217c` 已与本决策冲突，不能按原描述继续推进”，需删改该句，把 `S1` 直接以当前主线推进的口径统一后再建任务。`
- `榕根据大闸蟹与守护最好的爱莉希雅的最新最小需改项收口：已把该句改写为历史基线说明，明确 `T-20260423-9c23217c` 仅作旧四 kind 历史基线保留，不再构成 `S1` 前置；随后已按新正文重新复评。`
- `守护最好的爱莉希雅：最新复评通过。两 kind pass expectation 真源、`S1` 对 pass / registry / verifier / spec / pytest 的承接，以及旧四 kind 任务仅作历史基线的口径现已统一；按当前正文可直接进入任务创建。`
- `大闸蟹：最新复评通过。当前版本已把 `expectation/pass/tuning/launch_kernel_cost_func_compute_memory` 明确成两 kind 当前真源，旧四 kind 目录只保留历史证据；`S1` 已显式承接 pass / registry / tuner verifier 与对应 spec/pytest 的两 kind 收口；`T-20260423-9c23217c` 已统一为历史基线说明，不再构成 `S1` 前置。`

## 任务新建建议

- 本计划已按用户最新决策改成“以当前主线状态为起点继续推进”；`T-20260423-9c23217c` 不再作为 `S1` 创建前置。
- 创建 `S1` 前无需回头改写已完成任务；执行阶段直接在当前仓库状态上把公开合同从旧四 kind 收口到 `compute/memory` 两 kind。
- `basic_all.py` 与 `invalid_kind.py` 仍为 `[immutable-file]`；执行人不得修改；当前生效的两 kind pass expectation 必须落到新增目录 `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/`，不得继续复用旧四 kind 目录 runner 作为本计划验收入口。
- `守护最好的爱莉希雅` 与 `大闸蟹` 最新复评均已通过；可按 `S1/S2/S3` 创建任务。
- 首任务 `S1` 按当前任务系统新口径以 `spec` 类型创建，但阶段内容必须包含 spec、include 实现、pytest 和 review 同链，不允许退化为纯 spec 文档任务。

## 自检

- `spec/API` 自检：计划已按用户确认把 `cost_kind` 固定为 `compute/memory` 两类，helper 改为 `cost::add` 扁平命名，模板顺序与 API 一致，Kernel/Dma 同步覆盖。
- `任务边界` 自检：S1 先提供固定 cost kind 合同与 C++ helper 落点，S2 再做节点级 emit，S3 再做函数级源码与编译链路；依赖顺序符合当前实现缺口。
- `风险` 自检：最大风险已改为“当前主线仍带旧四 kind 历史基线，而本计划要把公开合同收口到 compute/memory 两 kind”；为避免重新依赖已完成任务记录，正文已改成直接在 `S1-S3` 中消化这一差异，并新增专门的两 kind pass expectation 真源目录。其次是旧任务里 `basic_all.py` 与 `invalid_kind.py` 为 `[immutable-file]`，已要求通过新增可改资产或可改目录入口收口；再次是 `cost::add` 扁平命名未来可能遇到 Dma/Kernel 同名同签名冲突，已要求先在 spec 中显式处理。
- `示例` 自检：计划示例使用 `S_INT` 局部变量承接 `tuner.cost`，避免丢失 `!symbol.int` result；同时保留 out-first 参数顺序。

## 大闸蟹最新复评（2026-04-23）

- 结论：`最小需改项`
- 最小阻断项：
  - `公开 API 设计 / 已确认：Cost kind 固定为 compute/memory` 小节此前残留旧句“`T-20260423-9c23217c` 当前锁定 `compute/memory/kind2/kind3` 固定集合，已与本决策冲突，不能按原描述继续推进”。这和正文其他位置已写死的“该任务只作历史基线、S1 直接以当前主线推进”相互冲突；执行人会不清楚是直接建 `S1`，还是还要回头处理旧任务。`
- 处理结果：`已于当前版本改写为历史基线说明：“`T-20260423-9c23217c` 仅作为旧四 kind 历史基线记录保留；本计划不再以其为 `S1` 前置，当前公开合同直接由 `S1-S3` 收口到 `compute/memory`。” 当前等待按新正文复评。`

## 守护最好的爱莉希雅最新复评（2026-04-23）

- 结论：`通过`
- 结论摘要：
  - `两 kind pass expectation 真源、`S1` 对 `launch-kernel-cost-func` / registry / `tuner.cost` verifier 与对应 spec/pytest 的承接，以及 `T-20260423-9c23217c` 仅作历史基线不再构成 `S1` 前置的口径都已统一；当前版本可按计划流程建任务。`

## 大闸蟹最终复评（2026-04-23）

- 结论：`通过`
- 结论摘要：
  - `expectation/pass/tuning/launch_kernel_cost_func_compute_memory/` 已明确为当前生效的两 kind pass expectation 真源，旧四 kind 目录只保留历史证据口径。
  - `S1` 已显式承接 `launch-kernel-cost-func` / registry / `tuner.cost` verifier 及对应 spec/pytest 的两 kind收口，没有再把关键合同留给后续阶段补齐。
  - 公开 API 设计里关于 `T-20260423-9c23217c` 的旧句已统一改成“历史基线说明，不再构成 `S1` 前置”，正文执行口径现已一致，可按当前版本创建任务。
