# T-20260519 npu-demo-pipeline-arch-after-attach-cse

## 2026-05-19 管理员下发前置记录

- 经办人：神秘人
- 计划书：`ARCHITECTURE/plan/npu_demo_pipeline_arch_after_attach_cse_green_plan.md`
- 任务目标：调整公开 `npu-demo-lowering` pipeline 顺序，将 `ArchParallelizePass(target=target, parallel_level="block")` 移到 `AttachArchInformationPass(target=target)` 之后、`OutlineDeviceKernelPass` 之前，并在第二次 `SymbolBufferHoistPass` 后新增一次 `CommonSubexpressionElimination`；同步 spec、实现、pytest、dump 阶段断言和 9 个 kernel demo 验收。
- latest main：`HEAD=origin/main=merge-base=573d85eee885b3b8e0158e217d00f76f1e7583f6`，`ahead/behind=0/0`。
- worktree：`/home/lfr/kernelcode_generate/wt-20260519-npu-demo-pipeline-arch-after-attach-cse`
- branch：`task/npu-demo-pipeline-arch-after-attach-cse`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/21/20260519-npu-demo-pipeline-arch-after-attach-cse.md`

### 并行 / 依赖判断

- 当前 TODO 中存在进行中任务 `T-20260519-c421e8fa / symbol-buffer-hoist-effect-first-contract`，其主要目标是 `symbol-buffer-hoist` effect-first 合同、实现、spec 与测试。
- 本计划目标是 `npu-demo-lowering` pipeline builder 顺序与 dump / kernel demo 验收，核心实现落点不同。
- 允许并行创建和分发本计划唯一 execute，不设置硬依赖。
- 潜在重叠面：`test/passes/pipeline/test_npu_demo_lowering.py`、kernel demo / kernel pytest gate、以及后续 merge 时的 latest-main 行为验证。
- 后合入者必须同步 latest `origin/main`，重新核对 pipeline order、9 个 kernel demo、相关 pytest、`git diff --check`、`expectation/.skills/agents/standard` 空 diff与任务记录同批合入；若出现同文件冲突或行为漂移，回 execute / 架构裁定，不得临场改验收口径。

### 禁止修改面与合同口径

- 本计划当前不把任何 `expectation` 入口列为必过合同验收资产。
- execute / review / admin / merge 不得复制、新建、同步、修改或删除 `expectation/`，不得修改 `.skills/` 或 `agents/standard/**`。
- 候选 diff 中 `expectation/.skills/agents/standard` 必须为空。
- 任务记录必须与代码 / spec / test 同批进入 review、终验和 merge；缺记录或记录未更新时不得先合代码后补记录。

## 2026-05-20 00:03 execute 开工与计划目标冲突定位

- 经办人：金铲铲大作战
- 任务：`T-20260519-c9406d6f / npu-demo-pipeline-arch-after-attach-cse`
- 任务目标：按计划调整公开 `npu-demo-lowering` pipeline 顺序，将 `ArchParallelizePass(target=target, parallel_level="block")` 放到 `AttachArchInformationPass(target=target)` 之后、`OutlineDeviceKernelPass` 之前，并在第二次 `SymbolBufferHoistPass` 后新增 `CommonSubexpressionElimination`。
- 执行前阅读记录：
  - 已重读个人提示词：`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`。
  - 已重读根规则：`AGENTS.md`。
  - 已重读标准：`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/spec文件规范.md`。
  - worktree 内缺计划书副本，按任务记录与下发口径只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_arch_after_attach_cse_green_plan.md`，未复制计划资产。
  - 已读前置记录与当前任务记录，确认本计划不把 `expectation` 列为必过合同验收资产，候选 diff 中 `expectation/.skills/agents/standard` 必须为空。
- latest main / 执行目录：
  - 执行目录：`/home/lfr/kernelcode_generate/wt-20260519-npu-demo-pipeline-arch-after-attach-cse`。
  - `git fetch --prune origin` 后 `HEAD=origin/main=merge-base=573d85eee885b3b8e0158e217d00f76f1e7583f6`。
  - `git status --short --untracked-files=all` 初始仅有本记录文件未跟踪。
- 已尝试改动：
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`：按计划目标把 `ArchParallelizePass` 移到 `AttachArchInformationPass` 后，并在第二次 `SymbolBufferHoistPass` 后插入第三个 `CommonSubexpressionElimination`。
  - `spec/pass/pipeline/npu_demo_lowering.md`：同步公开顺序、API 注意事项和测试表。
  - `test/passes/pipeline/test_npu_demo_lowering.py`：同步 pass order 断言，新增 dump marker / 目标序号断言。
- 验证：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：exit=1，`5 passed, 3 failed`。
  - 失败摘要：三个真实 pipeline 路径均在 `ArchParallelizePass` 报 `ArchParallelizePassError: unsupported loop structure`，失败点为 `test_npu_demo_lowering_pipeline_memory_plan_dump_shows_lifecycle_and_pool`、`test_npu_demo_lowering_pipeline_multi_buffer_static_dump_uses_ring_and_pool`、`test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain`。
- actual / expected / spec / verdict：
  - actual：计划目标顺序让 `ArchParallelizePass` 在 `memory-pool -> second symbol-buffer-hoist -> cse -> attach` 后运行；attach 后 IR 的顶层 loop 前已有 `arch.get_dynamic_memory`、`dma.view`、`dma.reshape` 等非 symbol setup op，触发 standalone `ArchParallelizePass` 的公开失败合同。
  - expected：按计划目标，`npu-demo-lowering` 应在 `attach-arch-information -> arch-parallelize -> outline-device-kernel` 顺序下继续跑通 pipeline pytest 与 9 个 kernel demo。
  - spec：`spec/pass/arch_parallelize.md` 明确只支持 `func { symbol-setup*; symbol.for {...}; func.return }`，顶层 loop 同级出现非纯 symbol setup op 必须失败为 `ArchParallelizePassError: unsupported loop structure`；本计划同时要求“不改 standalone ArchParallelizePass 公开失败合同”。
  - verdict：按计划目标顺序继续实现会和 standalone arch 公开失败合同冲突；若改 `ArchParallelizePass` 支持 `arch.get_dynamic_memory` / `dma.view` 前置 setup，将扩大公开合同，已超出 execute 边界。临时只读验证显示，把 `AttachArchInformationPass` 提前到 `MemoryPlanPass` 后、`ArchParallelizePass` 前，再继续后续 buffer / tile / DMA / memory-pool 链路，可以保持“arch 在 attach 后、outline 前”且不改 standalone arch 合同；但这与计划正文的目标 dump 序号不同，需要架构师裁定。
- Diff 反推自测：
  - 已按当前 diff 反推并运行 `py_compile` 与 `test/passes/pipeline/test_npu_demo_lowering.py`。
  - 未运行 9 个 kernel demo：当前计划目标 pipeline pytest 已在 arch 阶段失败，继续跑 kernel demo 只会重复同一阻断。
- 自检：
  - 当前没有修改 `expectation/`、`.skills/` 或 `agents/standard/**`。
  - 当前未新增 pipeline 名称、option，也未修改 `build_npu_demo_lowering_pipeline(...)` 签名。
  - 阻断属于计划目标顺序与既有公开失败合同冲突，不是测试可放宽问题；需要架构裁定后再继续。
- 结论：
  - execute 暂停在架构待确认；已准备向管理员与架构师回报两种可执行路径：A=用户/架构授权扩大 `ArchParallelizePass` standalone 可支持顶层 setup 合同；B=调整计划目标顺序为 `memory-plan -> attach-arch-information -> arch-parallelize -> symbol-buffer-hoist -> ... -> second symbol-buffer-hoist -> cse -> outline`，保留“不改 standalone arch 合同”。

## 2026-05-20 守护最好的爱莉希雅架构裁定

- 结论：不采用 A；不扩大 standalone `ArchParallelizePass` 的公开失败合同。原 B 方向正确，但不能删除 memory-pool 后、outline 前的 `AttachArchInformationPass`。用户随后明确当前 pipeline 不接入 `MultiBufferPass`，故当前生效顺序不再包含 multi-buffer。
- 裁定顺序：采用 B 修正版（不含 multi-buffer），默认 `npu-demo-lowering` 顺序改为 `memory-plan -> early attach-arch-information -> arch-parallelize -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> memory-pool -> symbol-loop-hoist -> symbol-buffer-hoist -> cse -> late attach-arch-information -> outline-device-kernel -> template-name-infer`。
- 原因：
  - `spec/pass/arch_parallelize.md` 只允许顶层 `symbol-setup*; symbol.for; return`，把 arch 放在 memory-pool/second symbol-buffer-hoist/cse/attach 后会遇到 `arch.get_dynamic_memory` / `dma.view` / `dma.reshape` setup，继续触发 `ArchParallelizePassError: unsupported loop structure`；这正是 standalone 公开失败合同，不能在本任务内扩大。
  - `spec/pass/attach_arch_information.md` 同时要求 `AttachArchInformationPass` 特化 `tsm/tlm1/tlm2/tlm3` 的 `arch.get_dynamic_memory` 容量；`MemoryPoolPass(rewrite=True)` 会在后续新生成 `arch.get_dynamic_memory + dma.view + dma.reshape`。若只把 attach 提前并删除 late attach，这些新 dynamic memory op 不会被特化。
  - `AttachArchInformationPass` 已公开支持入口函数存在完整且匹配 target 的 launch attrs 时继续通过并执行 dynamic memory 特化，因此 early attach 写 attrs、late attach 特化 memory-pool 后 dynamic memory 不需要新增公开 API、pipeline option 或错误文本。
- execute 继续范围：
  - 更新主仓共享计划 `ARCHITECTURE/plan/npu_demo_pipeline_arch_after_attach_cse_green_plan.md` 中目标顺序、S1-S3 验收与风险口径，按 B 修正版（不含 multi-buffer）返工。
  - 同步 `spec/pass/pipeline/npu_demo_lowering.md`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`test/passes/pipeline/test_npu_demo_lowering.py` 与必要 kernel/test 记录。
  - 必须增加/更新断言：early attach 在 memory-plan 后、arch 前；late attach 在第三个 cse 后、outline 前；memory-pool 后生成的 `arch.get_dynamic_memory` 在 late attach 后被 target 容量特化；当前 pipeline order / dump marker 不得出现 `multi-buffer`。
  - 仍不得修改 standalone `ArchParallelizePass` 公开失败合同，不得新增 pipeline option，不得修改 `expectation/`、`.skills/`、`agents/standard/**`。
- 当前任务状态：execute 可按 B 修正版（不含 multi-buffer）继续；若 B 修正版后仍只有扩大 standalone arch 合同、引入 pipeline-local no-op 或新增公开 API 才能通过 kernel demo，必须再次暂停并回用户确认。

## 2026-05-20 架构裁定：选择 B 修正版

- 经办人：大闸蟹
- 触发来源：管理员 `神秘人` 请求对 `T-20260519-c9406d6f / npu-demo-pipeline-arch-after-attach-cse` 的 execute 阻塞做架构裁定。
- 裁定结论：选择 B 修正版（不含 multi-buffer），不授权扩大 standalone `ArchParallelizePass` 公开失败合同；在 `MemoryPlanPass` 后新增 early `AttachArchInformationPass` 并紧接 `ArchParallelizePass`，`LowerDmaMemoryHierarchyPass` 后直接进入 `MemoryPoolPass`，同时保留 memory-pool 后、outline 前的 late `AttachArchInformationPass`。
- 裁定理由：
  - A 会让 standalone `ArchParallelizePass` 接受顶层 `arch.get_dynamic_memory` / `dma.view` / `dma.reshape` setup，属于公开失败合同扩大，和本计划“不改 standalone `ArchParallelizePass` 公开失败合同”边界冲突。
  - B 修正版只调整默认 `npu-demo-lowering` pipeline 顺序，仍保持 `ArchParallelizePass` 在 attach 后、outline 前，且避开 memory-pool 后产生的非 symbol setup。
  - 用户已明确当前 pipeline 不要 `MultiBufferPass`，因此本任务只移除 current pipeline 的 multi-buffer 接入，不删除已合入的 `MultiBufferPass` 实现和专项能力。
  - late `AttachArchInformationPass` 仍必须保留，因为 `MemoryPoolPass(rewrite=True)` 会在 `ArchParallelizePass` 之后新生成 `arch.get_dynamic_memory + dma.view + dma.reshape`，需要继续履行 `AttachArchInformationPass` 对 target 动态内存容量特化的公开合同。
  - B 修正版不新增 pipeline 名称、option、builder 签名或稳定错误文本。
- 新目标顺序片段：
  - `MemoryPlanPass(insert_free=True, fold=False)`
  - `AttachArchInformationPass(target=target)`
  - `ArchParallelizePass(target=target, parallel_level="block")`
  - `SymbolBufferHoistPass`
  - `TileAnalysisPass`
  - `LowerDmaMemoryHierarchyPass(fold=True, apply_op='matmul{["", "tlm1", "tlm2"]}')`
  - `MemoryPoolPass(rewrite=True, alignment=0)`
  - `SymbolLoopHoistPass`
  - `SymbolBufferHoistPass`
  - `CommonSubexpressionElimination`
  - `AttachArchInformationPass(target=target)`
  - `OutlineDeviceKernelPass`
  - `TemplateNameInferPass`
- 目标 dump 摘要：
  - `08-memory-plan.mlir`
  - `09-attach-arch-information.mlir`
  - `10-arch-parallelize.mlir`
  - `11-symbol-buffer-hoist.mlir`
  - `12-tile-analysis.mlir`
  - `13-lower-dma-memory-hierarchy.mlir`
  - `14-memory-pool.mlir`
  - `15-symbol-loop-hoist.mlir`
  - `16-symbol-buffer-hoist.mlir`
  - `17-cse.mlir`
  - `18-attach-arch-information.mlir`
  - `19-outline-device-kernel.mlir`
  - `20-template-name-infer.mlir`
- 计划同步：主仓共享计划 `ARCHITECTURE/plan/npu_demo_pipeline_arch_after_attach_cse_green_plan.md` 已按 B 修正版（不含 multi-buffer）更新任务目标、目标顺序、dump 阶段、完成态和 S1-S3 验收口径。
- execute 继续口径：
  - 按 B 修正版（不含 multi-buffer）更新 `spec/pass/pipeline/npu_demo_lowering.md`、`kernel_gen/passes/pipeline/npu_demo_lowering.py` 与 `test/passes/pipeline/test_npu_demo_lowering.py`。
  - 必须断言 early attach 位于 memory-plan 后、arch 前；`lower-dma-memory-hierarchy -> memory-pool` 直接相邻；late attach 位于第三个 CSE 后、outline 前，并能特化 memory-pool 后生成的 dynamic memory；当前 pipeline order / dump marker 不得包含 `multi-buffer`。
  - 不修改 standalone `ArchParallelizePass` 的 spec / 实现 / 错误合同。
  - 不修改、复制、新建、同步或删除 `expectation/`，候选 diff 中 `expectation/.skills/agents/standard` 必须为空。
  - 重新运行计划要求的 pipeline pytest、相关 arch/attach pytest、9 个 kernel demo、`git diff --check`、敏感目录空 diff，并在本记录补齐 Diff 反推自测与自检。
- 阻塞状态：架构待确认已解除，任务回到 execute 继续实现 / 验证。

## 2026-05-20 守护最好的爱莉希雅补充裁定：B 修正版覆盖纯 B

- 结论：纯 B 只解决了 arch unsupported structure，但缺少 `AttachArchInformationPass` 对 memory-pool 后 `arch.get_dynamic_memory` 的容量特化；当前执行唯一口径以主仓计划最新 B 修正版为准。
- B 修正版与纯 B 的差异：在 `symbol-buffer-hoist -> cse` 后、`outline-device-kernel` 前保留/添加 late `AttachArchInformationPass(target=target)`；目标 dump 因此包含第二个 `attach-arch-information`，`outline-device-kernel` 与 `template-name-infer` 后移一位。
- 当前生效顺序：`memory-plan -> early attach-arch-information -> arch-parallelize -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> memory-pool -> symbol-loop-hoist -> symbol-buffer-hoist -> cse -> late attach-arch-information -> outline-device-kernel -> template-name-infer`。
- execute 必须按 B 修正版（不含 multi-buffer）更新 spec / 实现 / pytest / dump 断言；若仍按纯 B 删除 late attach，review / 终验应退回。

## 2026-05-20 00:34 execute 按 B-prime 与 no-multi-buffer 裁定返工闭合

- 经办人：金铲铲大作战
- 任务：`T-20260519-c9406d6f / npu-demo-pipeline-arch-after-attach-cse`
- 任务目标：按最新 B 修正版返工 `npu-demo-lowering`，生效顺序为 `memory-plan -> early attach -> arch -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> memory-pool -> symbol-loop-hoist -> symbol-buffer-hoist -> cse -> late attach -> outline -> template-name-infer`；当前 pipeline 不接入 `MultiBufferPass(memory_stage=3)`。
- 执行前阅读记录：
  - 已重读个人提示词、`AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`。
  - 已读本记录中守护最好的爱莉希雅与大闸蟹的 B 修正版裁定，并收到最新补充：当前 `npu-demo-lowering` 不接入 `MultiBufferPass(memory_stage=3)`，`LowerDmaMemoryHierarchyPass` 后必须直接进入 `MemoryPoolPass`。
  - 已按主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_arch_after_attach_cse_green_plan.md` 的最新口径执行，未复制计划资产。
- 改动：
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`：更新文件级说明与函数注释；实际 pass 顺序改为 B-prime/no-multi-buffer；保留 early `AttachArchInformationPass(target=target)` 写 launch attrs、`ArchParallelizePass(target=target, parallel_level="block")` 在 memory-pool 前运行、第二段 `SymbolBufferHoistPass` 后第三个 CSE、late `AttachArchInformationPass(target=target)` 特化 memory-pool 后 `arch.get_dynamic_memory`；移除当前 pipeline 对 `MultiBufferPass` 的导入和 `pm.add_pass(...)` 接入，不删除 multi-buffer pass 本体。
  - `spec/pass/pipeline/npu_demo_lowering.md`：同步术语、目标、公开顺序、API 注意事项和用例表；明确 `lower-dma-memory-hierarchy -> memory-pool` 相邻，当前 pipeline 不接入 `multi-buffer`，late attach 负责特化 memory-pool 新生成 dynamic memory。
  - `test/passes/pipeline/test_npu_demo_lowering.py`：更新 pass order、dump marker、目标序号与负断言；断言 early attach 在 `memory-plan` 后、`arch-parallelize` 前，late attach 在第三个 CSE 后、outline 前，late attach 后 `arch.get_dynamic_memory` 已特化为 `npu_demo` target 容量；断言 dump 中无 `multi-buffer` marker，且 `lower-dma-memory-hierarchy` 后直接是 `memory-pool`。
  - `test/test_main_npu_demo_pipeline.py`：按 `spec/pass/pipeline/npu_demo_lowering.md` 中 `LaunchKernelCostFuncPass` 不属于本 pipeline 的公开合同，更新普通 `dsl_run + npu-demo-lowering` e2e 测试，锁定 main 输出与源码中不注入 `_cost_DMA1/_cost_MAC` sibling；cost 专项仍由 `dsl_cost_run` 测试链覆盖。
- 验证：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/test_main_npu_demo_pipeline.py`：exit=0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`8 passed, 1 warning`；锁定 B-prime/no-multi-buffer 顺序、dump marker、late attach dynamic memory 特化和 no-multi-buffer 负断言。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/test_attach_arch_information.py`：exit=0，`26 passed, 1 warning`；确认未扩大 standalone arch 失败合同，attach 公开合同不回退。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/test_main_npu_demo_pipeline.py`：exit=0，`10 passed, 1 warning`；确认 kernel/main 相关公开链路通过，普通 pipeline 不生成 cost sibling 的测试合同已同步。
  - `git diff --check`：exit=0。
  - 敏感目录空 diff：`git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --untracked-files=all -- expectation .skills agents/standard`、`git status --short --ignored -- expectation .skills agents/standard` 均无输出。
  - 静态边界扫描：`rg -n "hasattr\\(|getattr\\(|callable\\(getattr\\(" kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/test_main_npu_demo_pipeline.py` 无输出；`rg -n "MultiBufferPass|memory_stage=3" kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py` 无输出。
- Kernel demo 硬门禁：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0；`[CHECK] ..._absent_bias max_abs_diff=3.4332275390625e-05`，`[CHECK] ..._present_bias max_abs_diff=3.4332275390625e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit=0；`[CHECK] .../absent_bias max_abs_diff=3.0517578125e-05`，`[CHECK] .../present_bias max_abs_diff=3.0517578125e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit=0；`[CHECK] .../absent_bias max_abs_diff=3.0517578125e-05`，`[CHECK] .../present_bias max_abs_diff=3.0517578125e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`：exit=0；`[CHECK] ..._absent_bias max_abs_diff=4.1961669921875e-05`，`[CHECK] ..._present_bias max_abs_diff=4.1961669921875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`：exit=0；`[CHECK] ..._absent_bias max_abs_diff=3.814697265625e-05`，`[CHECK] ..._present_bias max_abs_diff=3.814697265625e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit=0；`[CHECK] .../absent_bias max_abs_diff=4.57763671875e-05`，`[CHECK] .../present_bias max_abs_diff=4.57763671875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py`：exit=0；`[CHECK] ... max_abs_diff=1.837313175201416e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：exit=0；`[CHECK] ... max_abs_diff=1.1898577213287354e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit=0；`[CHECK] ... max_abs_diff=9.715557098388672e-06`。
- Diff 反推自测：
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py` 与 `spec/pass/pipeline/npu_demo_lowering.md` 的顺序改动由 `test_npu_demo_lowering_pipeline_pass_order` 与 dump marker 测试覆盖；断言可在 early attach/arch/late attach/memory-pool/no-multi-buffer 顺序错误时失败。
  - `test/test_main_npu_demo_pipeline.py` 的 cost sibling 断言同步由 `test/test_main_npu_demo_pipeline.py` 复跑覆盖；该测试锁定普通 `dsl_run` 输出仍可执行且不把 `LaunchKernelCostFuncPass` 混入当前 pipeline。
  - 真实 kernel demo 9/9 通过，覆盖 matmul/conv2d/flash_attention 的 static/dynamic tile 与 present/absent bias 分支。
  - 本计划当前无必过 `expectation` 入口；未执行 expectation，不以 expectation 代替 diff 反推自测。
- 自检：
  - 只修改当前任务允许的 pipeline 实现、pipeline spec、相关 pytest 与任务记录；未改 `expectation/`、`.skills/`、`agents/standard/**`。
  - 未新增 pipeline 名称、option、builder 签名或公开错误文本；未扩大 standalone `ArchParallelizePass` 失败合同。
  - 未跨文件调用非公开 helper；未使用 ctx 能力探测；未新增嵌套函数。
  - 文件级说明与函数注释已同步当前公开顺序；测试断言覆盖顺序、dump marker、late attach 特化、no-multi-buffer 负边界和真实 kernel e2e。
- 结论：execute 返工已闭合，可进入 review；后续 review 需复跑同一组 pipeline pytest、相关 pytest、9 个 kernel demo、`git diff --check` 与敏感目录空 diff。

### 2026-05-20 00:47 review 通过

经办人：不要啊教练
任务：T-20260519-c9406d6f / npu-demo-pipeline-arch-after-attach-cse
任务目标：复审 B-prime/no-multi-buffer pipeline 顺序、spec、实现、pytest、9 个 kernel demo、Diff 反推自测、`git diff --check` 与 `expectation/.skills/agents/standard` 空 diff。
验证基线：`HEAD=573d85eee885b3b8e0158e217d00f76f1e7583f6`，`origin/main=573d85eee885b3b8e0158e217d00f76f1e7583f6`，`merge-base=573d85eee885b3b8e0158e217d00f76f1e7583f6`，`ahead/behind=0/0`；worktree 与最新主线对齐，无覆盖任务 diff 风险。
执行目录：`/home/lfr/kernelcode_generate/wt-20260519-npu-demo-pipeline-arch-after-attach-cse`。
计划真源：worktree 内无计划书副本，本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_arch_after_attach_cse_green_plan.md`。

被审 diff：
- `kernel_gen/passes/pipeline/npu_demo_lowering.py`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/test_main_npu_demo_pipeline.py`

真实审查：
- 公开 pipeline builder 顺序已改为 B-prime/no-multi-buffer：`MemoryPlanPass` 后插入 early `AttachArchInformationPass`，随后 `ArchParallelizePass`，`LowerDmaMemoryHierarchyPass` 后直接进入 `MemoryPoolPass`，第二段 `SymbolBufferHoistPass` 后插入第三个 `CommonSubexpressionElimination`，并在其后保留 late `AttachArchInformationPass`。
- 当前默认 pipeline 不接入 `MultiBufferPass(memory_stage=3)`；实现文件已删除该导入与 `pm.add_pass(...)` 接入，spec 与测试同步写明 `multi-buffer` 不属于本 pipeline。
- `spec/pass/pipeline/npu_demo_lowering.md` 的公开顺序、术语、API 注意事项、测试矩阵与完成态已同步到 B-prime/no-multi-buffer 口径；`ArchParallelizePass` standalone 公开失败合同未扩大。
- `test/passes/pipeline/test_npu_demo_lowering.py` 已补齐 pass order、dump marker / occurrence、early attach、late attach、no-multi-buffer 负断言，并对 `arch.get_dynamic_memory` 在 late attach 后的 target 特化做了机械锁定。
- `test/test_main_npu_demo_pipeline.py` 已将普通 `dsl_run + npu-demo-lowering` 主链路断言改为不再注入 `_cost_DMA1/_cost_MAC` sibling，和本计划“不把 LaunchKernelCostFuncPass 混入当前 pipeline”一致。
- 静态扫描未命中新增的 ctx 能力探测、跨文件私有导入、`object` 签名、`._type` 私有字段写入或非装饰器嵌套函数；宽泛命中的 `getattr/hasattr/object` 仅在既有公开 registry 反射、测试本地 helper 或 xDSL 读取位置。
- 敏感目录 `expectation/`、`.skills`、`agents/standard` tracked / cached / untracked / ignored 均为空；候选 diff 未触及这些目录。

Diff 反推审查：
- `test/passes/pipeline/test_npu_demo_lowering.py::test_npu_demo_lowering_pipeline_pass_order` 机械锁定新顺序，能在 early attach、arch 顺序、第三个 CSE、late attach 或 multi-buffer 回退时失败。
- `test/passes/pipeline/test_npu_demo_lowering.py::test_npu_demo_lowering_pipeline_memory_plan_dump_shows_lifecycle_and_pool` 与 `..._static_dump_uses_pool_without_multi_buffer` 用 dump marker / occurrence 锁定 `memory-plan -> attach-arch-information -> arch-parallelize -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> memory-pool -> symbol-loop-hoist -> symbol-buffer-hoist -> cse -> attach-arch-information -> outline-device-kernel -> template-name-infer` 的相对关系，且明确无 `multi-buffer`。
- `test/test_main_npu_demo_pipeline.py` 的主链路断言与本轮 diff 一致，能在错误恢复 `_cost_DMA1/_cost_MAC` sibling 时失败。
- 9 个 kernel demo 作为真实 e2e 硬门禁已复跑并全部通过，覆盖 matmul / conv2d / flash_attention 的 static、static tile dynamic、dynamic tile dynamic 组合。
- `expectation` 不在本计划必过资产列表内，本轮未运行 expectation，不以 expectation 替代 Diff 反推自测。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/test_attach_arch_information.py` -> `26 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/test_main_npu_demo_pipeline.py` -> `10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py` -> exit 0，`[CHECK] ... max_abs_diff=3.4332275390625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py` -> exit 0，`[CHECK] ... max_abs_diff=3.0517578125e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py` -> exit 0，`[CHECK] ... max_abs_diff=3.0517578125e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py` -> exit 0，`[CHECK] ... max_abs_diff=4.1961669921875e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py` -> exit 0，`[CHECK] ... max_abs_diff=3.814697265625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py` -> exit 0，`[CHECK] ... max_abs_diff=4.57763671875e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py` -> exit 0，`[CHECK] ... max_abs_diff=1.837313175201416e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py` -> exit 0，`[CHECK] ... max_abs_diff=1.1898577213287354e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py` -> exit 0，`[CHECK] ... max_abs_diff=9.715557098388672e-06`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/test_main_npu_demo_pipeline.py` -> exit 0。
- `git diff --check` -> exit 0。
- `git diff --name-only -- expectation .skills agents/standard` / `git diff --cached --name-only -- expectation .skills agents/standard` / `git status --short --untracked-files=all -- expectation .skills agents/standard` / `git status --short --ignored -- expectation .skills agents/standard` -> 均为空。

自检：
- 只修改允许范围内的 pipeline 实现、pipeline spec、相关 pytest 与任务记录；未改 `expectation/`、`.skills/`、`agents/standard/**`。
- 未新增 pipeline 名称、option、builder 签名或稳定错误文本；未扩大 standalone `ArchParallelizePass` 失败合同。
- 未跨文件调用非公开 helper；未使用 ctx 能力探测；未新增非装饰器场景的嵌套函数。
- 文件级说明与函数注释同步当前公开顺序；测试断言覆盖顺序、dump marker、late attach 特化、no-multi-buffer 负边界和真实 kernel e2e。

残余风险：无。

结论：通过。
下一步：按计划级任务流程回报管理员，进入架构复核 / 终验，不直接 merge。

## 2026-05-20 01:25 大闸蟹计划级架构终验

经办人：大闸蟹
任务：T-20260519-c9406d6f / npu-demo-pipeline-arch-after-attach-cse
计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_arch_after_attach_cse_green_plan.md`
执行目录：`/home/lfr/kernelcode_generate/wt-20260519-npu-demo-pipeline-arch-after-attach-cse`

验证基线：
- `HEAD=573d85eee885b3b8e0158e217d00f76f1e7583f6`
- `origin/main=573d85eee885b3b8e0158e217d00f76f1e7583f6`
- `merge-base=573d85eee885b3b8e0158e217d00f76f1e7583f6`
- `ahead/behind=0/0`

候选 diff 核对：
- 候选 tracked diff：`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/test_main_npu_demo_pipeline.py`。
- 本任务记录当前为未跟踪文件，merge 前必须与候选 spec / implementation / pytest 同批纳入提交。
- 当前无必过 expectation 合同资产；本终验未运行 expectation，也未以 expectation 作为通过依据。

架构复核重点：
- 默认 `npu-demo-lowering` 顺序符合 B 修正版 / no-multi-buffer 裁定：`memory-plan -> early attach -> arch -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> memory-pool -> symbol-loop-hoist -> symbol-buffer-hoist -> cse -> late attach -> outline -> template-name-infer`。
- `ArchParallelizePass` standalone 公开失败合同未扩大；未新增 pipeline option、pipeline 名称、builder 签名或稳定错误文本。
- 当前 pipeline 不接入 `MultiBufferPass(memory_stage=3)`；已合入的 multi-buffer pass 专项能力不属于本计划删除目标。
- late `AttachArchInformationPass` 保留在第三个 CSE 后、outline 前，用于特化 memory-pool 后生成的 `arch.get_dynamic_memory`。

复跑验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/test_main_npu_demo_pipeline.py`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/test_attach_arch_information.py`：`26 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/test_main_npu_demo_pipeline.py`：`10 passed, 1 warning`。
- 9 个 kernel demo 逐条复跑，全部 exit 0；`[CHECK]` 覆盖 matmul / conv2d 的 present 与 absent bias，以及 flash_attention 三类 case，最大误差范围与 review 记录一致。
- `git diff --check`：通过。
- `git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：均无输出。

结论：
- 通过。
- 最小阻断项：无。
- merge gate：本任务记录必须与候选代码 / spec / pytest 同批纳入提交；若 merge 前记录仍未进入候选提交，应退回补齐。

### 2026-05-20 计划级架构终验

经办人：守护最好的爱莉希雅
任务：T-20260519-c9406d6f / npu-demo-pipeline-arch-after-attach-cse
结论：通过

验证基线：
- `HEAD=573d85ee`
- `origin/main=573d85ee`
- `merge-base=573d85ee`
- `ahead/behind=0/0`

执行目录：
- `/home/lfr/kernelcode_generate/wt-20260519-npu-demo-pipeline-arch-after-attach-cse`

合同 / 顺序验收摘要：
- 复核 `kernel_gen/passes/pipeline/npu_demo_lowering.py` 与 `spec/pass/pipeline/npu_demo_lowering.md`，公开顺序为 B-prime/no-multi-buffer：`MemoryPlanPass` 后 early `AttachArchInformationPass`，随后 `ArchParallelizePass`，`LowerDmaMemoryHierarchyPass` 后直接 `MemoryPoolPass`，第二段 `SymbolBufferHoistPass` 后第三个 `CommonSubexpressionElimination`，late `AttachArchInformationPass` 后再 `OutlineDeviceKernelPass`。
- 复核 `test/passes/pipeline/test_npu_demo_lowering.py`，已机械锁定 early attach / arch 顺序、second symbol-buffer-hoist 后 CSE、late attach、无 `multi-buffer` marker，以及 `arch.get_dynamic_memory` 在 late attach 后的特化结果。
- 复核 `test/test_main_npu_demo_pipeline.py`，普通主链路不再注入 `_cost_DMA1/_cost_MAC` sibling，和当前计划“不接入 MultiBufferPass”一致。
- 本计划主仓 `expectation` 非必过资产，不作为本轮通过依据。

最新本地复核：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `8 passed, 1 warning`
- `git diff --check` -> 通过
- `git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --untracked-files=all -- expectation .skills agents/standard`、`git status --short --ignored -- expectation .skills agents/standard` -> 均为空
- `rg -n "MultiBufferPass|memory_stage=3|multi-buffer" kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py` -> 仅命中测试中的负断言，没有实际接入

kernel demo gate：
- 9 个 kernel demo 的通过结果已在本任务记录中完整留痕；本轮复核未重复无变更验收。
- 当前候选 diff 仍需保持 `kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/test_main_npu_demo_pipeline.py` 与本任务记录同批合入，任务记录不得晚于代码单独补进。

最小阻断项：
- 无。

终验结论：
- 通过。
- 可进入 merge / 归档前的最后流程。

---

时间：2026-05-20 01:34 CST
经办人：李白
阶段：merge 收口

合并前同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260519-npu-demo-pipeline-arch-after-attach-cse`
- 任务分支：`task/npu-demo-pipeline-arch-after-attach-cse`
- 进入 merge 时任务分支落后 `origin/main` 1 个提交；已先执行 `git fetch --prune origin`，再用 `git merge --ff-only origin/main` 将任务分支从 `573d85eee885b3b8e0158e217d00f76f1e7583f6` 同步到 `4b823d0ca8f2e4e3cd436a4451c50af7681b5bdb`。
- latest 同步带入文件为上一任务 `T-20260519-c421e8fa` 的 `symbol_buffer_hoist` 相关提交；与本任务候选文件无重叠，fast-forward 过程无冲突、无覆盖候选 diff。
- 同步后 `HEAD=origin/main=4b823d0ca8f2e4e3cd436a4451c50af7681b5bdb`。
- 主仓 `/home/lfr/kernelcode_generate` 当前仍有与本任务无关的本地文档改动：`ARCHITECTURE/project_architecture.md` 与 `docs/**`，本次 merge 不纳入、不清理、不覆盖。

本次候选同批范围：
- `kernel_gen/passes/pipeline/npu_demo_lowering.py`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/test_main_npu_demo_pipeline.py`
- `agents/codex-multi-agents/log/task_records/2026/21/20260519-npu-demo-pipeline-arch-after-attach-cse.md`

merge 前真实复核：
- 候选 diff 与 review / 双架构终验记录一致；任务记录已从未跟踪状态纳入同批候选要求，禁止先合代码后补记录。
- `expectation/`、`.skills/`、`agents/standard/` 无普通 diff、staged diff、未跟踪或 ignored 输出。
- 本计划不把 `expectation` 列为必过资产；本次 merge 记录不把 `expectation` 写作通过依据。
- latest main 前进后，因当前 pipeline 会经过 `SymbolBufferHoistPass`，已复跑 pipeline、arch/attach、kernel/main 与 9 个 kernel demo 相关门禁。

merge 前复跑命令：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/test_main_npu_demo_pipeline.py`：exit `0`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/test_attach_arch_information.py`：`26 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/test_main_npu_demo_pipeline.py`：`10 passed, 1 warning`。
- 9 个 kernel demo 逐条复跑，全部 exit `0`：`kernel/matmul/inputs_static_tile_static.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/conv2d/inputs_static_tile_static.py`、`kernel/conv2d/inputs_static_tile_dynamic.py`、`kernel/conv2d/inputs_dynamic_tile_dynamic.py`、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`。
- `git diff --check`：exit `0`。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。

Diff 反推自测 / 审查继承：
- pipeline 顺序、early/late attach、第三个 CSE、no-multi-buffer 负边界、主链路不注入 `_cost_DMA1/_cost_MAC` 的断言均已由 review 与双架构终验记录覆盖。
- latest main 前进后已复跑同一组直接相关 pytest 与 demo gate；未发现前序 `symbol_buffer_hoist` 合入导致本候选失效。

merge 结论：
- 可合并。
- 记录文件已与业务 / spec / test 候选同批纳入提交范围。
- 最小阻断项：无。
