# pass_infrastructure_refactor_green_plan.md

## 文档信息

- 创建者：`Codex`
- 最后一次更改：`小李飞刀`
- 目标 `spec`：
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](../../spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
  - [`spec/pass/lowering/dma_memory_hierarchy/spec.md`](../../spec/pass/lowering/dma_memory_hierarchy/spec.md)
  - [`spec/pass/lowering/memory_pool.md`](../../spec/pass/lowering/memory_pool.md)
  - [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
  - [`spec/pass/lowering/tile_analysis.md`](../../spec/pass/lowering/tile_analysis.md)
  - [`spec/pass/lowering/tile_elewise.md`](../../spec/pass/lowering/tile_elewise.md)
  - [`spec/pass/lowering/tile_reduce.md`](../../spec/pass/lowering/tile_reduce.md)
  - [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
  - [`spec/analysis/analysis_engine.md`](../../spec/analysis/analysis_engine.md)
  - [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)
- 目标 `API`：
  - `build_registered_pass("lower-nn")`
  - `build_registered_pass("buffer-results-to-out-params")`
  - `build_registered_pass("lower-dma-memory-hierarchy")`
  - `build_registered_pass("memory-pool")`
  - `build_registered_pass("tile-analysis")`
  - `build_registered_pass("tile-elewise")`
  - `build_registered_pass("tile-reduce")`
  - `build_registered_pass("symbol-loop-hoist")`
  - `kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass`
  - `kernel_gen.passes.lowering.nn_lowering.NnLoweringPass`
  - `kernel_gen.passes.dma_memory_hierarchy.LowerDmaMemoryHierarchyPass`
  - `kernel_gen.passes.memory_pool.MemoryPoolPass`
- 目标 `test`：
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_buffer_results_to_out_params.py`](../../test/pass/test_buffer_results_to_out_params.py)
  - [`test/pass/test_dma_memory_hierarchy.py`](../../test/pass/test_dma_memory_hierarchy.py)
  - [`test/pass/test_memory_pool.py`](../../test/pass/test_memory_pool.py)
  - [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)
  - [`test/pass/test_lowering_tile_private_helpers.py`](../../test/pass/test_lowering_tile_private_helpers.py)
  - [`test/pass/test_lowering_tile_analysis.py`](../../test/pass/test_lowering_tile_analysis.py)
  - [`test/pass/test_lowering_tile_elewise.py`](../../test/pass/test_lowering_tile_elewise.py)
  - [`test/pass/test_lowering_tile_reduce.py`](../../test/pass/test_lowering_tile_reduce.py)
  - [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
  - [`test/pass/nn_lowering/public_name.py`](../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](../../test/pass/nn_lowering/test_nn_lowering_private_helpers.py)
  - [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
  - [`test/analysis/test_analysis_private_helpers.py`](../../test/analysis/test_analysis_private_helpers.py)
  - [`test/analysis/test_analysis_submodule_private_helpers.py`](../../test/analysis/test_analysis_submodule_private_helpers.py)
  - [`test/pass/test_analysis_func_cost.py`](../../test/pass/test_analysis_func_cost.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)
- 目标 `验收资产`：
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)
  - [`expectation/pass/tile`](../../expectation/pass/tile)
  - [`expectation/pass/buffer_results_to_out_params`](../../expectation/pass/buffer_results_to_out_params)
  - [`expectation/pass/symbol_loop_hoist`](../../expectation/pass/symbol_loop_hoist)
  - [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
- 目标 `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/buffer_results_to_out_params.py`](../../kernel_gen/passes/buffer_results_to_out_params.py)
  - [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](../../kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - [`kernel_gen/passes/lowering/nn_to_kernel.py`](../../kernel_gen/passes/lowering/nn_to_kernel.py)
  - [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering)
  - [`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](../../kernel_gen/passes/lowering/dma_memory_hierarchy.py)
  - [`kernel_gen/passes/lowering/memory_pool.py`](../../kernel_gen/passes/lowering/memory_pool.py)
  - [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
  - `kernel_gen/tile/`（新增目录）
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
  - [`kernel_gen/passes/analysis`](../../kernel_gen/passes/analysis)
  - [`kernel_gen/analysis`](../../kernel_gen/analysis)
  - [`ARCHITECTURE/project_architecture.md`](../../ARCHITECTURE/project_architecture.md)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1：canonical public path 与迁移矩阵冻结` | 无 | `wt-20260423-pass-infra-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md` |
| `S2：compat shim 退场` | `S1` | `wt-20260423-pass-infra-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md` |
| `S3：dma/memory_pool rehome` | `S1` | `wt-20260423-pass-infra-s3` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s3.md` |
| `S4：tile helper 与路径迁移` | `S1,S2,S3` | `wt-20260423-pass-infra-s4` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s4.md` |
| `S5：nn_lowering family rewrite` | `S1,S2` | `wt-20260423-pass-infra-s5` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s5.md` |
| `S6：symbol_loop_hoist rewrite` | `S1,S3,S4` | `wt-20260423-pass-infra-s6` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s6.md` |
| `S7：tile logic rewrite 与旧路径扫尾` | `S4,S5,S6` | `wt-20260423-pass-infra-s7` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s7.md` |
| `S8：analysis family 退场` | `S7` | `wt-20260423-pass-infra-s8` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md` |

## 评审摘要

- 评审结论：`通过（守护最好的爱莉希雅、大闸蟹复评）`
- 评审人：`大闸蟹`、`睡觉小分队`、`提莫炖蘑菇`、`小李飞刀`、`守护最好的爱莉希雅`
- 结论摘要：`大闸蟹先前要求先冻结 canonical public path，再分 analysis / compat / rehome / tile / nn_lowering / symbol_loop_hoist 多条链推进；睡觉小分队要求写死合同真源、旧公开名退场和 immutable expectation；提莫炖蘑菇要求把 importlib / registry / pass_manager / analysis 目录入口单列为执行前边界；小李飞刀要求 tile 两段串行、nn_lowering 与 symbol_loop_hoist 写清稳定语义；守护最好的爱莉希雅要求 analysis 不能前置到首段，且 immutable 禁止修改面必须写进正文。用户已确认 analysis family 继续留在本计划，作为 S8 尾段执行；以上阻断项已在当前版正文收口。`
- 守护最好的爱莉希雅本轮复评结论：`正文格式已回到计划书标准；S1-S8 的任务新建建议都明确写成首任务类型 spec、默认链路 spec -> build -> review -> merge；analysis 后置到 S8、nn_lowering / tile / symbol_loop_hoist 拆分和 immutable expectation 禁止修改面均已写清，当前无结构性阻断项。`
- 大闸蟹本轮复评结论：`最新正文已符合计划书标准与近期通过计划书结构；S1-S8 均明确写成首任务类型 spec、默认链路 spec -> build -> review -> merge；analysis 留在 S8 尾段、tile 分两段串行、immutable expectation 只读与 canonical public path 先固定的边界均已写实。`

## 终验 / 复验 / 修复复核记录

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`origin/main@40bbd3a8dab5a147a040edc273676feda6bf6b86`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260424-pass-infra-final`
- 合同验收摘要：`本轮先在主目录执行 git fetch --prune；因主目录存在本地删改与未跟踪 worktree，复验改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-pass-infra-final。按计划只复验相关 expectation：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-pass-infra-final python3 -m expectation.pass.buffer_results_to_out_params，exit 1，报 No module named expectation.pass.buffer_results_to_out_params；2）... python3 -m expectation.pass.tile，exit 1，报 No module named expectation.pass.tile；3）... python3 -m expectation.pass.symbol_loop_hoist，exit 1，报 No module named expectation.pass.symbol_loop_hoist；4）... python3 -m expectation.pass.lowing.nn_lowering，exit 1，报 No module named expectation.pass.lowing；5）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-pass-infra-final python3 expectation/pass/pipeline/default_lowering.py，exit 2，报文件不存在。`
- 最小阻断项或通过摘要：`当前最小阻断项是：计划正文点名的相关 expectation 资产在最新干净 worktree 里并未随主线同步存在。缺失项至少包括 expectation/pass/buffer_results_to_out_params、expectation/pass/tile、expectation/pass/symbol_loop_hoist、expectation/pass/lowing/nn_lowering 以及 expectation/pass/pipeline/default_lowering.py。只要这组计划点名的合同入口在最新同步现场仍不可执行，本轮复验就不能给通过。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按本轮复验结果补建唯一修复任务 T-20260424-3b36f2e2，worktree=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-pass-infra-final-repair-s9.md。任务只处理计划正文点名的相关 expectation 资产缺失或不可执行问题，以及它们直接关联的实现/spec/test 收口；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测，expectation 只单列为合同验收资产。`
- 另一位架构师补充重点：`后续继续推进时，先把计划正文点名的相关 expectation 资产与最新同步现场对齐，再做下一轮复验。`

### 2026-04-24 守护最好的爱莉希雅 复验（4983279）

- 结论：`通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地删改与未跟踪文件，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-pass-infra-recheck-2。`
- 验证基线：`origin/main@4983279c54631dcb42fceeca75b0233815621948；主目录 HEAD 与 origin/main 一致。`
- 合同验收摘要：`本轮只执行计划正文点名的相关 expectation：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-pass-infra-recheck-2 python3 -m expectation.pass.buffer_results_to_out_params，exit 0；2）... python3 -m expectation.pass.tile，exit 0；3）... python3 -m expectation.pass.symbol_loop_hoist，exit 0；4）... python3 -m expectation.pass.lowing.nn_lowering，exit 0；5）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-pass-infra-recheck-2 python3 expectation/pass/pipeline/default_lowering.py，exit 0。`
- 最小阻断项或通过摘要：`无。上一轮复验中“相关 expectation 资产缺失或不可执行”的阻断已经收口：buffer_results_to_out_params、tile、symbol_loop_hoist、lowing.nn_lowering 与 pipeline/default_lowering 入口在最新干净现场均可执行并通过；DONE.md 也已记录修复任务 T-20260424-3b36f2e2 完成。当前未再发现新的可直接执行改进点。`

### 2026-04-24 大闸蟹 复验（7ac5513）

- 结论：`不通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地改动，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-pass-infra-recheck-3。`
- 验证基线：`origin/main@7ac5513cec14ea146d48dbe9b21984c2ad1430e9。`
- 合同验收摘要：`本轮只执行计划正文点名的相关 expectation：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-pass-infra-recheck-3 python3 -m expectation.pass.buffer_results_to_out_params，exit 0；2）... python3 -m expectation.pass.tile，exit 0；3）... python3 -m expectation.pass.symbol_loop_hoist，exit 0；4）... python3 -m expectation.pass.lowing.nn_lowering，exit 0；5）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-pass-infra-recheck-3 python3 expectation/pass/pipeline/default_lowering.py，exit 0。`
- 最小阻断项或通过摘要：`当前仍有可直接收口点，因此不能给通过。最小阻断项是：计划正文第 200-208 行“old path failure boundary”与第 233-235 行“完成态定义”仍把 kernel_gen.passes.lowering.tile 归入必须失败或不再作为公开导入入口的旧路径；但最新主线实际保留该模块作为 compat helper module，kernel_gen/passes/lowering/tile.py 仍可导入，且 test/pass/test_lowering_tile.py 已明确锁定“该模块继续存在，但只保留 TilePassError 与 _raise_tile_error”。也就是说，计划正文对 tile 旧路径的完成态描述还未和当前真实实现 / spec / pytest 对齐。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按本轮复验结果补建唯一修复任务 T-20260424-285240b8，worktree=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s10，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-pass-infra-final-repair-s10.md。任务只处理计划正文中 kernel_gen.passes.lowering.tile 完成态描述与当前 compat helper reality 的对齐，以及直接关联的实现/spec/test 收口；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测。`

### 2026-04-25 守护最好的爱莉希雅 复验（791b9d0）

- 结论：`不通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地删改与未跟踪文件，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260425-pass-infra-recheck-4。`
- 验证基线：`origin/main@791b9d0ed6a74276f2cf2e08fadd55156e874469；主目录 fast-forward 受本地改动阻挡，未覆盖现有现场。`
- 合同验收摘要：`本轮只执行正文当前保留的相关 expectation：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-pass-infra-recheck-4 python3 -m expectation.pass.buffer_results_to_out_params，exit 0；2）... python3 -m expectation.pass.tile，exit 0；3）... python3 -m expectation.pass.symbol_loop_hoist，exit 0；4）... python3 -m expectation.pass.lowing.nn_lowering，exit 0；5）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260425-pass-infra-recheck-4 python3 expectation/pass/pipeline/default_lowering.py，exit 0。`
- 最小阻断项或通过摘要：`当前仍有可继续收口点，因此不能给通过。最新同步现场本身已经不再携带这份计划资产：origin/main@791b9d0 的干净 worktree 中只有 ARCHITECTURE/project_architecture.md 与 ARCHITECTURE/reference/reference_project_rvv_xdsl_research.md，既没有 ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md，也没有 TODO.md。也就是说，这份计划正文虽然在当前本地现场仍可见，但它并未随最新同步现场一起存在；在计划资产重新与最新主线现场对齐前，不能把这份计划当作已完成的有效归档对象。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按本轮复验结果补建当前唯一修复任务 T-20260425-086dd45d，worktree=/home/lfr/kernelcode_generate/wt-20260425-pass-infra-repair-s11，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260425-pass-infra-repair-s11.md。任务只处理计划资产与最新主线现场的对齐，以及直接关联的归档/记录收口；不得改动任何 [immutable-file]；执行记录要求真实自检与 Diff 反推自测。`

## 输入摘要

- 目标：重构 pass 基础设施，冻结 surviving public path，逐步清理 compat shim、rehome 历史 lowering 入口，并把 `nn_lowering / tile / symbol_loop_hoist` 收口到更稳定、可维护的实现形态。
- 不做什么：计划阶段不修改实现；不擅自改只读 `expectation`；不把 analysis 提前到前半段；不把多个重构族混成单阶段“大扫除”。
- 当前痛点：当前仓库是半迁移状态，旧路径、registry、spec、pytest、`importlib` 字符串导入和 `expectation` 合同仍交叉锁定；如果不先冻结 canonical public path，执行阶段很容易形成“实现迁了、公开合同还没迁”的半成品。
- 完成后用户最想看到的例子：执行人只看计划书就能知道 `lower-nn`、`tile-analysis`、`symbol-loop-hoist` 等 surviving 公开入口还保留什么、哪些旧路径该失败、每个阶段默认按 `spec -> build -> review -> merge` 链推进。

## 计划目标

- 冻结本专题 surviving public path、旧路径失败边界和消费者迁移矩阵，让执行人不再靠猜测迁目录。
- 收口 compat shim、rehome pass、tile helper/path、nn_lowering family、symbol_loop_hoist 的实现与公开合同。
- 保持 surviving public pass 名稳定，不把目录迁移顺手做成公开行为变更。
- 用只读 expectation、pytest 和 import failure 一起锁住重构后行为。
- 在本计划尾段完成 analysis family 退场，避免其继续悬挂为半迁移状态。

## 当前基线

- 当前公开合同：
  - [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md) 已写明 `lower-nn` 是唯一公开 pass 名，但 compat `nn_to_kernel` 入口仍存在。
  - [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md) 已把 `tile-analysis` / `tile-elewise` / `tile-reduce` 定义成对外合同，但真实逻辑仍依赖 [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)。
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md) 仍承载 tile family、dma hierarchy、symbol-loop-hoist 的顺序合同，并保留 `Pass.run -> apply` 兼容语义。
- 当前公开 API：
  - `build_registered_pass("lower-nn")`、`build_registered_pass("buffer-results-to-out-params")`、`build_registered_pass("lower-dma-memory-hierarchy")`、`build_registered_pass("memory-pool")`、`build_registered_pass("tile-analysis")`、`build_registered_pass("tile-elewise")`、`build_registered_pass("tile-reduce")`、`build_registered_pass("symbol-loop-hoist")` 当前都可构造。
  - `kernel_gen.passes.lowering.buffer_results_to_out_params`、`kernel_gen.passes.lowering.nn_to_kernel`、`kernel_gen.passes.lowering.dma_memory_hierarchy`、`kernel_gen.passes.lowering.memory_pool`、`kernel_gen.passes.lowering.tile*` 仍是活跃导入面。
- 当前实现入口：
  - `kernel_gen/analysis` 与 `kernel_gen/passes/analysis` 仍存在，[`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 仍注册 `AnalyzeFuncCostPass`。
  - `nn_lowering` 外层已有 `PatternRewriteWalker`，但 family 内部仍大量使用 `parent_block`、`insert_ops_before`、`rewriter.has_done_action` 和遗留 `lower_*_family()`。
  - `tile_analysis.py` / `tile_elewise.py` / `tile_reduce.py` 是 `ModulePass` 壳，核心逻辑仍压在 `lowering/tile.py`。
  - `symbol_loop_hoist.py` 仍是 `while progress + detach/insert_ops_before`。
- 当前测试与验收资产：
  - `test/pass/test_pass_registry.py`、`test/pass/test_pass_manager.py`、`test/dsl/test_gen_kernel.py`、`test/script/test_python_coverage_check.py` 大量锁旧模块路径和旧 include-module 字符串。
  - `expectation/pass/lowing/nn_lowering/**`、`expectation/pass/tile/**`、`expectation/pass/buffer_results_to_out_params/**`、`expectation/pass/pipeline/default_lowering.py` 含大量 `[immutable-file]`。
- 当前缺口或失败点：
  - 如果直接按草稿把 analysis 删除、compat 清理、rehome、tile/nn_lowering/symbol_loop_hoist 重写混在一轮推进，最容易留下“主文件已迁，registry/spec/test/importlib 仍锁旧路径”的半完成状态。

## 合同真源顺序

- `expectation/pass/lowing/nn_lowering + expectation/pass/tile + expectation/pass/buffer_results_to_out_params + expectation/pass/symbol_loop_hoist + expectation/pass/pipeline/default_lowering.py > spec/pass/lowering/*.md + spec/pass/registry.md + spec/pass/pass_manager.md + spec/pass/analysis/*.md + spec/analysis/*.md > pytest / 本地测试脚本 > 当前实现`
- 对本计划而言，`expectation` 只作为只读合同验收资产单列，不承担“为了让实现过绿而改 expectation”的职责；若实现与只读合同冲突，默认由执行阶段收口实现、spec 和 pytest，且不把 expectation 当作对应测试的替代品。

## 消费者迁移矩阵

| 消费者 | surviving public path | 旧路径失败边界 | 迁移说明 |
| --- | --- | --- | --- |
| registry / pass manager caller | `build_registered_pass(...)`、`build_registered_pipeline(...)` | 通过名字解析，不继续接受旧 import path 当作公开入口 | 由 `test/pass/test_pass_registry.py` 与 `test/pass/test_pass_manager.py` 锁定 |
| out-param / nn lowering caller | `kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass`、`kernel_gen.passes.lowering.nn_lowering.NnLoweringPass` | `kernel_gen.passes.lowering.buffer_results_to_out_params`、`kernel_gen.passes.lowering.nn_to_kernel` | S2 退场 compat shim，旧 lowering 入口稳定失败 |
| dma / memory_pool caller | `kernel_gen.passes.dma_memory_hierarchy.LowerDmaMemoryHierarchyPass`、`kernel_gen.passes.memory_pool.MemoryPoolPass` | `kernel_gen.passes.lowering.dma_memory_hierarchy`、`kernel_gen.passes.lowering.memory_pool` | S3 只保留上移后的公开导入点 |
| tile caller | `build_registered_pass("tile-analysis")`、`build_registered_pass("tile-elewise")`、`build_registered_pass("tile-reduce")` | `kernel_gen.passes.lowering.tile_analysis`、`kernel_gen.passes.lowering.tile_elewise`、`kernel_gen.passes.lowering.tile_reduce` | `kernel_gen.passes.lowering.tile` 仍保留为 compat helper module，但不再承担 pass caller / logic helper 入口；S4/S7 完成后其余旧 lowering 路径失败 |
| symbol loop hoist caller | `build_registered_pass("symbol-loop-hoist")`、`kernel_gen.passes.symbol_loop_hoist.SymbolLoopHoistPass` | 不再追加新的 compat 路径 | 仅重写实现形态，不改公开名 |
| analysis caller | `analysis(...)`、`AnalyzeFuncCostPass`（S8 结束前） | `kernel_gen.analysis`、`kernel_gen.passes.analysis`（S8 后） | analysis family 放在尾段处理，S8 后整体退场 |

## 方案比较与选型

- 不采用方案：按草稿把 analysis 删除、compat 清理、rehome、tile / nn_lowering / symbol_loop_hoist 行为重写、旧路径删除混成一轮。
- 不采用原因：当前库是半迁移状态，这样会让执行人同时碰删除、迁移、重写三类动作，无法机械判断缺口归因。
- 采用方案：先冻结 canonical public path 和消费者迁移矩阵，再按 `compat -> rehome -> tile helper/path -> nn_lowering -> symbol_loop_hoist -> tile logic -> analysis` 的顺序推进。
- 最小公开接口：
  - surviving public pass 名保持 `lower-nn`、`buffer-results-to-out-params`、`lower-dma-memory-hierarchy`、`memory-pool`、`tile-analysis`、`tile-elewise`、`tile-reduce`、`symbol-loop-hoist`
  - 旧模块路径在各自阶段完成后稳定失败，不再静默兼容

## 公开 API 设计

### surviving public path

- `BufferResultsToOutParamsPass`
  - 公开入口：`kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass`
- `NnLoweringPass`
  - 公开入口：`kernel_gen.passes.lowering.nn_lowering.NnLoweringPass`
- `LowerDmaMemoryHierarchyPass`
  - 公开入口：`kernel_gen.passes.dma_memory_hierarchy.LowerDmaMemoryHierarchyPass`
- `MemoryPoolPass`
  - 公开入口：`kernel_gen.passes.memory_pool.MemoryPoolPass`
- `TileAnalysisPass` / `TileElewisePass` / `TileReducePass`
  - 公开入口：registry 名称保持不变
  - 内部实现落点：迁到 `kernel_gen.tile.*`
- `SymbolLoopHoistPass`
  - 公开入口：`kernel_gen.passes.symbol_loop_hoist.SymbolLoopHoistPass`

### old path failure boundary

- 以下旧路径在对应阶段完成后必须稳定失败，不允许继续兼容：
  - `kernel_gen.passes.lowering.buffer_results_to_out_params`
  - `kernel_gen.passes.lowering.nn_to_kernel`
  - `kernel_gen.passes.lowering.dma_memory_hierarchy`
  - `kernel_gen.passes.lowering.memory_pool`
  - `kernel_gen.passes.lowering.tile_analysis`
  - `kernel_gen.passes.lowering.tile_elewise`
  - `kernel_gen.passes.lowering.tile_reduce`
  - `kernel_gen.analysis`
  - `kernel_gen.passes.analysis`
- `kernel_gen.passes.lowering.tile` 继续保留为 compat helper module，只允许稳定导出 `TilePassError` 与 `_raise_tile_error`，不再作为 pass caller / logic helper 入口。

### 调用示例

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pass

load_builtin_passes()
lower_nn = build_registered_pass("lower-nn")
tile_analysis = build_registered_pass("tile-analysis")
symbol_hoist = build_registered_pass("symbol-loop-hoist")
```

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
from kernel_gen.passes.memory_pool import MemoryPoolPass
```

## 完成态定义

- `spec/pass/registry.md`、`spec/pass/pass_manager.md`、相关 lowering spec 明确 surviving public path、旧路径失败边界、只读 expectation 与 `PassManager` 兼容桥边界。
- `kernel_gen.passes.lowering.buffer_results_to_out_params`、`kernel_gen.passes.lowering.nn_to_kernel`、`kernel_gen.passes.lowering.dma_memory_hierarchy`、`kernel_gen.passes.lowering.memory_pool`、`kernel_gen.passes.lowering.tile_{analysis,elewise,reduce}` 不再作为公开导入入口。
- `kernel_gen.passes.lowering.tile` 继续存在，但只作为 compat helper module；公开面只保留 `TilePassError` 与 `_raise_tile_error`，不再承载 tile family 的 pass / logic helper 默认入口。
- `kernel_gen/tile/` 存在，tile family 的共享 helper 与真实逻辑不再压在 `kernel_gen/passes/lowering/tile.py`。
- `nn_lowering` family 不再保留 `lower_*_family()` 死代码，pattern 主链不再依赖公开的 `parent_block + has_done_action`。
- `symbol_loop_hoist` 不再把 `while progress + detach` 作为主实现骨架。
- `kernel_gen/analysis` 与 `kernel_gen/passes/analysis` 在 `S8` 结束后退场，`AnalyzeFuncCostPass` 不再可导入、不可在 registry 中构造。
- 相关 pytest、expectation、import failure 验收全部通过。

## 验收设计

- 验收资产：[`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- 输入样例：registry 构造 surviving pass；PassManager 组合 tile family、symbol-loop-hoist、lower-dma-memory-hierarchy。
- 锁定输出：公开 pass 名不变；旧路径在对应阶段失败；顺序合同不回退。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py`

- 验收资产：[`test/pass/test_buffer_results_to_out_params.py`](../../test/pass/test_buffer_results_to_out_params.py)、[`test/pass/nn_lowering/public_name.py`](../../test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
- 输入样例：surviving 新入口与旧 compat 入口导入。
- 锁定输出：新入口工作；旧 compat 入口退场；`lower-nn` 公开名保持不变。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_buffer_results_to_out_params.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_lowering_nn_lowering.py`

- 验收资产：[`test/pass/test_dma_memory_hierarchy.py`](../../test/pass/test_dma_memory_hierarchy.py)、[`test/pass/test_memory_pool.py`](../../test/pass/test_memory_pool.py)
- 输入样例：rehome 后的新模块路径与 registry 构造。
- 锁定输出：新路径通过；旧 lowering 路径失败；公开 pass 名和行为不回退。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_dma_memory_hierarchy.py test/pass/test_memory_pool.py`

- 验收资产：[`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)、[`test/pass/test_lowering_tile_private_helpers.py`](../../test/pass/test_lowering_tile_private_helpers.py)、[`test/pass/test_lowering_tile_analysis.py`](../../test/pass/test_lowering_tile_analysis.py)、[`test/pass/test_lowering_tile_elewise.py`](../../test/pass/test_lowering_tile_elewise.py)、[`test/pass/test_lowering_tile_reduce.py`](../../test/pass/test_lowering_tile_reduce.py)
- 输入样例：tile helper、tile-analysis、tile-elewise、tile-reduce 主路径与边界输入。
- 锁定输出：helper/path 迁移完成；logic rewrite 后黑盒行为不回退。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_lowering_tile.py test/pass/test_lowering_tile_private_helpers.py test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py`

- 验收资产：[`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
- 输入样例：无 `symbol.for`、有 invariant `symbol.const`、有可外提 `symbol.binary`。
- 锁定输出：公开 pass 名不变；no-op 与外提行为保持正确；稳定态规则不歧义。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py`

- 验收资产：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)、[`test/pass/test_analysis_func_cost.py`](../../test/pass/test_analysis_func_cost.py)
- 输入样例：analysis family 旧入口导入、registry 构造、spec/test 残留。
- 锁定输出：`S8` 结束后旧入口稳定失败；analysis spec/test/doc 残留清零。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py`

- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.buffer_results_to_out_params`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.lowing.nn_lowering`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/pipeline/default_lowering.py`
- Diff 反推验证：执行与审查阶段必须按实际改动文件补跑对应 pytest 或本地测试脚本；计划命令只是最低集合；`expectation` 合同验收单列，不算 diff 反推测试。
- 终验 expectation：架构师终验 / 复验 / 终验修复复核时必须在最新同步现场运行与本轮改动有关的 expectation 合同验收；只有用户明确要求时才运行全量 expectation。

## 阶段拆分

### S1：canonical public path 与迁移矩阵冻结

#### 上下文摘要

- 当前最大的风险不是具体代码怎么改，而是执行人不知道哪些旧路径还要保、哪些路径该失败、哪些测试和字符串导入要同步改。

#### 阶段目标

- 冻结 surviving public path、旧路径失败边界和消费者迁移矩阵。

#### 非目标

- 不在本阶段删除实现文件。
- 不在本阶段做 pass 行为重写。

#### 目标 spec / API

- [`spec/pass/registry.md`](../../spec/pass/registry.md)
- [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- `公开 API：build_registered_pass(...)`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/**（只读合同资产）`
- `合同真源：spec/pass/registry.md + spec/pass/pass_manager.md > test/pass/test_pass_registry.py + test/pass/test_pass_manager.py > 当前实现`

#### 最小功能闭环

- surviving public path 写死。
- old path failure boundary 写死。
- `importlib.import_module(...)` 旧路径消费者清单固定。

#### 执行步骤

1. 读取当前计划、相关 spec、`test/pass/test_pass_registry.py`、`test/pass/test_pass_manager.py`、`kernel_gen/passes/{registry,pass_manager}.py`。
2. 更新 spec 与相关 pytest 基线，使执行人能机械判断“哪个模块继续活、哪个模块该失败”。
3. 按 diff 反推补跑 registry / pass_manager pytest，并记录旧路径消费者基线清单。

#### 预期示例代码

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
```

#### 预期输出

```text
surviving path fixed
old path failure boundary fixed
consumer migration matrix fixed
```

#### 目标验收资产

- [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
- [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S1、全局完成态/验收设计、相关 spec/test/实现、前序记录`
- `最小功能闭环：写清 surviving public path、old path failure boundary、consumer matrix`
- `自检：重点写接口、兼容、旧路径失败边界、示例和文字歧义是否已机械可判`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：冻结 pass infra surviving public path、旧路径失败边界与消费者迁移矩阵`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md`

### S2：compat shim 退场

#### 上下文摘要

- `buffer_results_to_out_params` 和 `nn_to_kernel` 已有新主入口，但旧 lowering compat shim 仍是活跃消费面。

#### 阶段目标

- 退场 `kernel_gen.passes.lowering.buffer_results_to_out_params` 与 `kernel_gen.passes.lowering.nn_to_kernel` 两个 compat 入口。

#### 非目标

- 不改 surviving pass 名 `buffer-results-to-out-params` 与 `lower-nn`。
- 不在本阶段做 `nn_lowering` family 行为重写。

#### 目标 spec / API

- [`spec/pass/lowering/buffer_results_to_out_params.md`](../../spec/pass/lowering/buffer_results_to_out_params.md)
- [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
- `公开 API：kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/pass/buffer_results_to_out_params/**`
- `合同真源：spec/pass/lowering/buffer_results_to_out_params.md + spec/pass/lowering/nn_lowering/spec.md > test/pass/test_buffer_results_to_out_params.py + test/pass/nn_lowering/public_name.py > 当前实现`

#### 最小功能闭环

- 新入口是唯一 surviving 公开实现入口。
- compat shim 旧路径稳定失败。
- pytest 中的 module path assert 与 `importlib` 字符串同步更新。

#### 执行步骤

1. 读取 S1 记录、相关 spec、相关 pytest、实现文件和 `kernel_gen/passes/{__init__.py,lowering/__init__.py}`。
2. 删除 compat shim 并改写 surviving 导入。
3. 按 diff 反推补跑 buffer-results-to-out-params / nn_lowering 相关 pytest。

#### 预期示例代码

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
```

#### 预期输出

```text
import kernel_gen.passes.lowering.buffer_results_to_out_params -> ModuleNotFoundError
import kernel_gen.passes.lowering.nn_to_kernel -> ModuleNotFoundError
```

#### 目标验收资产

- [`test/pass/test_buffer_results_to_out_params.py`](../../test/pass/test_buffer_results_to_out_params.py)
- [`test/pass/nn_lowering/public_name.py`](../../test/pass/nn_lowering/public_name.py)
- [`expectation/pass/buffer_results_to_out_params`](../../expectation/pass/buffer_results_to_out_params)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_buffer_results_to_out_params.py test/pass/nn_lowering/public_name.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.buffer_results_to_out_params`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S2、全局完成态/验收设计、S1 记录、相关 spec/test/实现`
- `最小功能闭环：写清 surviving 入口、compat 失败边界、pytest 与 expectation 的对应关系`
- `自检：重点写兼容性、失败短语、module path assert 与导入边界`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：退场 buffer_results_to_out_params / nn_to_kernel compat shim 并收口 surviving 导入`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md`

### S3：dma/memory_pool rehome

#### 上下文摘要

- `dma_memory_hierarchy.py` 与 `memory_pool.py` 仍位于 `kernel_gen/passes/lowering/`，但用户草稿明确要求迁到上级目录。

#### 阶段目标

- 完成 `dma_memory_hierarchy` 与 `memory_pool` 的实现、spec、test、字符串导入 rehome。

#### 非目标

- 不改 `lower-dma-memory-hierarchy` / `memory-pool` 的公开名字和公开行为。
- 不顺手改 default pipeline 顺序。

#### 目标 spec / API

- [`spec/pass/lowering/dma_memory_hierarchy/spec.md`](../../spec/pass/lowering/dma_memory_hierarchy/spec.md)
- [`spec/pass/lowering/memory_pool.md`](../../spec/pass/lowering/memory_pool.md)
- `公开 API：kernel_gen.passes.dma_memory_hierarchy.LowerDmaMemoryHierarchyPass`
- `公开 API：kernel_gen.passes.memory_pool.MemoryPoolPass`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/pass/pipeline/default_lowering.py`
- `合同真源：spec/pass/lowering/dma_memory_hierarchy/spec.md + spec/pass/lowering/memory_pool.md > test/pass/test_dma_memory_hierarchy.py + test/pass/test_memory_pool.py > 当前实现`

#### 最小功能闭环

- 新模块路径成为唯一 surviving 公开导入点。
- 旧 lowering 路径失败。
- registry 和字符串导入同步更新。

#### 执行步骤

1. 读取 S1 记录、相关 spec、pytest、registry、`kernel_gen/passes/{__init__.py,lowering/__init__.py}`。
2. rehome 实现并改写 spec/test/importlib 字符串。
3. 按 diff 反推补跑 rehome 相关 pytest。

#### 预期示例代码

```python
from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
from kernel_gen.passes.memory_pool import MemoryPoolPass
```

#### 预期输出

```text
import kernel_gen.passes.lowering.dma_memory_hierarchy -> ModuleNotFoundError
import kernel_gen.passes.lowering.memory_pool -> ModuleNotFoundError
```

#### 目标验收资产

- [`test/pass/test_dma_memory_hierarchy.py`](../../test/pass/test_dma_memory_hierarchy.py)
- [`test/pass/test_memory_pool.py`](../../test/pass/test_memory_pool.py)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_dma_memory_hierarchy.py test/pass/test_memory_pool.py`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S3、全局完成态/验收设计、S1 记录、相关 spec/test/实现`
- `最小功能闭环：写清 new path、old path failure、registry / importlib 更新点`
- `自检：重点写路径迁移、公开名保持、pipeline 不越界、错误模型不回退`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：完成 dma_memory_hierarchy 与 memory_pool 的 rehome 和旧路径退场`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s3.md`

### S4：tile helper 与路径迁移

#### 上下文摘要

- 当前 tile family 的核心逻辑仍压在 `lowering/tile.py`，三个 pass 只是壳；如果直接改 logic，会在新旧两处同时改。

#### 阶段目标

- 先迁 `tile.py` helper 和 tile family 实际落点到 `kernel_gen/tile/`，不在本阶段做最终逻辑重写。

#### 非目标

- 不要求在本阶段完成 tile-analysis / tile-elewise / tile-reduce 的完整 pattern 化逻辑。
- 不修改公开 pass 名。

#### 目标 spec / API

- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- [`spec/pass/lowering/tile_analysis.md`](../../spec/pass/lowering/tile_analysis.md)
- [`spec/pass/lowering/tile_elewise.md`](../../spec/pass/lowering/tile_elewise.md)
- [`spec/pass/lowering/tile_reduce.md`](../../spec/pass/lowering/tile_reduce.md)

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/pass/tile/**`
- `合同真源：spec/pass/lowering/tile*.md > test/pass/test_lowering_tile*.py + test/pass/test_pass_manager.py > 当前实现`

#### 最小功能闭环

- `kernel_gen/tile/` 建立。
- `tile` helper 与实际实现落点完成迁移。
- 旧路径消费者改链，不再让 `lowering/tile.py` 同时承担 helper 和最终逻辑。

#### 执行步骤

1. 读取 S1/S2/S3 记录、相关 spec、tile pytest、`test/dsl/test_gen_kernel.py` 和 `test/script/test_python_coverage_check.py`。
2. 迁 helper / path，保持黑盒行为不变。
3. 按 diff 反推补跑 tile 相关 pytest 和路径字符串相关测试。

#### 预期示例代码

```python
from kernel_gen.tile.common import ...
```

#### 预期输出

```text
tile helper moved out of kernel_gen.passes.lowering.tile
tile pass shell no longer depends on old mixed path layout
```

#### 目标验收资产

- [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)
- [`test/pass/test_lowering_tile_private_helpers.py`](../../test/pass/test_lowering_tile_private_helpers.py)
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- [`expectation/pass/tile`](../../expectation/pass/tile)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_lowering_tile.py test/pass/test_lowering_tile_private_helpers.py test/dsl/test_gen_kernel.py -k "tile or gen_kernel"`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S4、全局完成态/验收设计、S1-S3 记录、相关 spec/test/实现`
- `最小功能闭环：写清 helper/path 迁移完成点、旧路径消费者改链点和未进 logic rewrite 的边界`
- `自检：重点写路径依赖、helper 复用、module path assert、覆盖面和维护性`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：完成 tile helper 与实现路径迁移，不在本阶段做最终 logic rewrite`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s4.md`

### S5：nn_lowering family rewrite

#### 上下文摘要

- `nn_lowering` 当前是“外层新、内层旧”的半迁移状态；不先清理 family 死代码和手写路径，后续维护成本会持续扩大。

#### 阶段目标

- 把 `nn_lowering` family 收口为“辅助函数 + 单 op RewritePattern + 薄 pass.apply()”。

#### 非目标

- 不新增新 pass 名。
- 不修改 decompass / softmax 边界合同。

#### 目标 spec / API

- [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
- [`spec/pass/lowering/nn_lowering`](../../spec/pass/lowering/nn_lowering)
- `公开 API：build_registered_pass("lower-nn")`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/pass/lowing/nn_lowering/**`
- `合同真源：expectation/pass/lowing/nn_lowering > spec/pass/lowering/nn_lowering/spec.md > test/pass/nn_lowering/*.py > 当前实现`

#### 最小功能闭环

- `lower_*_family()` 死代码清理。
- family 文件不再依赖公开的 `parent_block + has_done_action` 主路径。
- `lower-nn` 公开 pass 名和黑盒 expectation 不回退。

#### 执行步骤

1. 读取 S1/S2 记录、nn_lowering spec、相关 pytest、只读 expectation。
2. 逐个 family 改成单 op pattern，并清理 compat / 死代码。
3. 按 diff 反推补跑 nn_lowering pytest 与 expectation。

#### 预期示例代码

```python
PatternRewriteWalker(
    GreedyRewritePatternApplier([...]),
    apply_recursively=True,
).rewrite_module(module)
```

#### 预期输出

```text
lower-nn keeps public name
family rewrite path no longer depends on parent_block/has_done_action
```

#### 目标验收资产

- [`test/pass/nn_lowering/public_name.py`](../../test/pass/nn_lowering/public_name.py)
- [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
- [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](../../test/pass/nn_lowering/test_nn_lowering_private_helpers.py)
- [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/nn_lowering/test_nn_lowering_private_helpers.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.lowing.nn_lowering`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S5、全局完成态/验收设计、S1-S2 记录、相关 spec/test/实现`
- `最小功能闭环：写清 family 死代码清理、单 op pattern 收口、黑盒 expectation 对齐情况`
- `自检：重点写 API 不回退、异常路径、pattern 复用、函数粒度和测试有效性`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：完成 nn_lowering family 的单 op RewritePattern 重构并清理遗留死代码`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s5.md`

### S6：symbol_loop_hoist rewrite

#### 上下文摘要

- `symbol_loop_hoist` 仍是 `while progress + detach` 主链；如果不单独写清稳定态规则，很容易改偏循环语义。

#### 阶段目标

- 将 `symbol_loop_hoist` 收口为 pattern 驱动实现，并明确达到稳定态的规则。

#### 非目标

- 不扩大到新的 control-flow interface 专题。
- 不修改公开 pass 名和顺序合同。

#### 目标 spec / API

- [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
- `公开 API：build_registered_pass("symbol-loop-hoist")`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/pass/symbol_loop_hoist/**`
- `合同真源：expectation/pass/symbol_loop_hoist > spec/pass/symbol_loop_hoist.md > test/pass/test_symbol_loop_hoist.py + test/pass/test_pass_manager.py > 当前实现`

#### 最小功能闭环

- `symbol-loop-hoist` 在缺 `symbol.for` 时保持 no-op。
- invariant `symbol.const` / `symbol.binary` 外提规则机械可判。
- 顺序合同不回退。

#### 执行步骤

1. 读取 S1/S3/S4 记录、相关 spec、pytest、只读 expectation。
2. 重构为 pattern 驱动实现，并补齐稳定态说明。
3. 按 diff 反推补跑 symbol_loop_hoist 相关 pytest 与 expectation。

#### 预期示例代码

```python
symbol_hoist = build_registered_pass("symbol-loop-hoist")
```

#### 预期输出

```text
symbol-loop-hoist keeps public name
no-op without symbol.for
hoist invariant symbol ops only
```

#### 目标验收资产

- [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
- [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- [`expectation/pass/symbol_loop_hoist`](../../expectation/pass/symbol_loop_hoist)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py test/pass/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist"`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S6、全局完成态/验收设计、S1/S3/S4 记录、相关 spec/test/实现`
- `最小功能闭环：写清稳定态规则、no-op 边界、顺序合同和未覆盖原因`
- `自检：重点写循环语义、外提条件、维护性、异常路径与测试有效性`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：完成 symbol_loop_hoist 的 pattern 驱动重构并写清稳定态规则`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s6.md`

### S7：tile logic rewrite 与旧路径扫尾

#### 上下文摘要

- S4 只迁 helper/path，不做最终逻辑重写；真正的 tile pattern 化和全库旧路径扫尾要单列，不然会把路径迁移和行为变更混在一起。

#### 阶段目标

- 完成 tile family 真实 logic rewrite，并清理全库旧路径、旧字符串导入和残留别名。

#### 非目标

- 不新增新 tile pass 名。
- 不扩大到 execute_engine 或其他 pipeline 专题。

#### 目标 spec / API

- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- [`spec/pass/lowering/tile_analysis.md`](../../spec/pass/lowering/tile_analysis.md)
- [`spec/pass/lowering/tile_elewise.md`](../../spec/pass/lowering/tile_elewise.md)
- [`spec/pass/lowering/tile_reduce.md`](../../spec/pass/lowering/tile_reduce.md)

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/pass/tile/**`
- `合同真源：expectation/pass/tile > spec/pass/lowering/tile*.md > test/pass/test_lowering_tile*.py + test/pass/test_pass_registry.py + test/pass/test_pass_manager.py + test/dsl/test_gen_kernel.py > 当前实现`

#### 最小功能闭环

- tile-analysis / tile-elewise / tile-reduce 完成 pattern 化逻辑实现。
- 全库旧路径字符串、module path assert、coverage include-module 收口。
- 只读 expectation 绿。

#### 执行步骤

1. 读取 S4/S5/S6 记录、相关 spec、pytest、只读 expectation。
2. 完成 tile family 逻辑重构，并同步清理全库旧路径消费者。
3. 按 diff 反推补跑 tile 相关 pytest、gen_kernel、coverage check 与 expectation。

#### 预期示例代码

```python
tile_analysis = build_registered_pass("tile-analysis")
tile_elewise = build_registered_pass("tile-elewise")
tile_reduce = build_registered_pass("tile-reduce")
```

#### 预期输出

```text
tile family logic moved off old lowering/tile.py path
old tile module paths fail after migration
```

#### 目标验收资产

- [`test/pass/test_lowering_tile_analysis.py`](../../test/pass/test_lowering_tile_analysis.py)
- [`test/pass/test_lowering_tile_elewise.py`](../../test/pass/test_lowering_tile_elewise.py)
- [`test/pass/test_lowering_tile_reduce.py`](../../test/pass/test_lowering_tile_reduce.py)
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- [`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)
- [`expectation/pass/tile`](../../expectation/pass/tile)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py test/dsl/test_gen_kernel.py test/script/test_python_coverage_check.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S7、全局完成态/验收设计、S4/S5/S6 记录、相关 spec/test/实现`
- `最小功能闭环：写清 tile logic rewrite、旧路径扫尾范围、pytest 与 expectation 对应关系`
- `自检：重点写 pattern 行为、旧路径残留、可维护性、测试完整性和所有可改进点`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：完成 tile family logic rewrite 并清理全库旧路径残留`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s7.md`

### S8：analysis family 退场

#### 上下文摘要

- 用户已确认 analysis family 继续留在本计划，作为尾段执行；这意味着前面阶段先完成 surviving 主链重构，最后再一次性退场 analysis。

#### 阶段目标

- 删除 `kernel_gen/analysis`、`kernel_gen/passes/analysis`、`AnalyzeFuncCostPass` 及其 spec/test/doc 消费面。

#### 非目标

- 不回头重写 tile / nn_lowering / symbol_loop_hoist。
- 不在本阶段新增新的 analysis 替代专题。

#### 目标 spec / API

- [`spec/analysis/analysis_engine.md`](../../spec/analysis/analysis_engine.md)
- [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)
- `公开 API：AnalyzeFuncCostPass 退场`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/**（本阶段不通过 expectation 改写收口 analysis 退场）`
- `合同真源：spec/analysis/*.md + spec/pass/analysis/func_cost.md + spec/pass/pass_manager.md > test/analysis/*.py + test/pass/test_analysis_func_cost.py > 当前实现`

#### 最小功能闭环

- `kernel_gen.analysis` 与 `kernel_gen.passes.analysis` 旧路径稳定失败。
- `AnalyzeFuncCostPass` 不再可导入、不可在 registry 中构造。
- analysis 相关 spec/test/doc 残留清零。

#### 执行步骤

1. 读取 S1-S7 记录、analysis 相关 spec/test/实现、registry/pass_manager 和 project_architecture 文档。
2. 删除 analysis family 并同步清理 spec/test/doc/registry 残留。
3. 按 diff 反推补跑 analysis 退场相关 pytest、registry/pass_manager 相关 pytest。

#### 预期示例代码

```python
import importlib

importlib.import_module("kernel_gen.analysis")
```

#### 预期输出

```text
ModuleNotFoundError
```

#### 目标验收资产

- [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
- [`test/analysis/test_analysis_private_helpers.py`](../../test/analysis/test_analysis_private_helpers.py)
- [`test/analysis/test_analysis_submodule_private_helpers.py`](../../test/analysis/test_analysis_submodule_private_helpers.py)
- [`test/pass/test_analysis_func_cost.py`](../../test/pass/test_analysis_func_cost.py)
- [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
- [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/analysis/test_analysis.py test/analysis/test_analysis_private_helpers.py test/analysis/test_analysis_submodule_private_helpers.py test/pass/test_analysis_func_cost.py test/pass/test_pass_registry.py test/pass/test_pass_manager.py`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S8、全局完成态/验收设计、S1-S7 记录、相关 spec/test/实现`
- `最小功能闭环：写清 analysis 退场范围、旧路径失败边界、registry / doc 清理完成点`
- `自检：重点写删旧范围是否完整、是否仍有活跃消费者、错误模型和文档残留是否清零`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：完成 analysis family 退场并清理 registry/spec/test/doc 全部残留`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md`

## 待确认项

- 当前无待确认项。

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：analysis family 继续留在本计划，作为 S8 尾段执行`
- `未确认前处理要求：不适用`
- `若用户要求至少询问 3 人：已满足，且本轮实际询问了 5 人`
- `询问记录 1：大闸蟹；结论：最小需改项，要求先冻结 canonical public path，再拆 analysis / compat / rehome / tile / nn_lowering / symbol_loop_hoist`
- `询问记录 2：睡觉小分队；结论：公开合同真源、旧公开名退场和 immutable expectation 必须写死`
- `询问记录 3：提莫炖蘑菇；结论：importlib / registry / pass_manager / analysis 目录入口必须单列为执行前边界`
- `询问记录 4：小李飞刀；结论：tile 两段串行，nn_lowering 与 symbol_loop_hoist 写清稳定语义`
- `询问记录 5：守护最好的爱莉希雅；结论：当前库不是从零重构，analysis 不能前置，immutable 禁止修改面必须写进正文`

## 任务创建记录

- `S1=T-20260423-73440e31，任务类型 spec，worktree=wt-20260423-pass-infra-s1，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md`
- `S2=T-20260423-e1e94e87，任务类型 spec，依赖 T-20260423-73440e31，worktree=wt-20260423-pass-infra-s2，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md`
- `S3=T-20260423-5b62c1a4，任务类型 spec，依赖 T-20260423-73440e31，worktree=wt-20260423-pass-infra-s3，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s3.md`
- `S4=T-20260423-8023eef9，任务类型 spec，依赖 T-20260423-73440e31,T-20260423-e1e94e87,T-20260423-5b62c1a4，worktree=wt-20260423-pass-infra-s4，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s4.md`
- `S5=T-20260423-432a6289，任务类型 spec，依赖 T-20260423-73440e31,T-20260423-e1e94e87，worktree=wt-20260423-pass-infra-s5，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s5.md`
- `S6=T-20260423-09ef159e，任务类型 spec，依赖 T-20260423-73440e31,T-20260423-5b62c1a4,T-20260423-8023eef9，worktree=wt-20260423-pass-infra-s6，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s6.md`
- `S7=T-20260423-3f989a1a，任务类型 spec，依赖 T-20260423-8023eef9,T-20260423-432a6289,T-20260423-09ef159e，worktree=wt-20260423-pass-infra-s7，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s7.md`
- `S8=T-20260423-acccf628，任务类型 spec，依赖 T-20260423-3f989a1a，worktree=wt-20260423-pass-infra-s8，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md`
- `任务已按阶段默认链路建成 spec 起步；后续续接仍按 spec -> build -> review -> merge 推进。`

## 计划书自检

- 通用自检：已读 [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md) 与模板；本轮只改计划书；未越权修改实现、测试或 expectation。
- 结构自检：标题、文档信息、任务清单、评审摘要、终验记录、输入摘要、目标、基线、合同真源顺序、方案、公开 API、完成态、验收设计、阶段拆分、待确认、用户确认、任务创建记录、计划书自检、参考资料齐全。
- 阶段自检：每个 `Sx` 都补齐了 `阶段目标 / 非目标 / 目标 spec / API / 禁止修改面 / 合同真源 / 最小功能闭环 / 执行步骤 / 预期示例代码 / 预期输出 / 目标验收资产 / 验收必过项目 / 记录要求 / 任务新建建议`。
- 链路自检：每个阶段的任务建议都明确写为“首任务类型 `spec`，默认沿 `spec -> build -> review -> merge` 链推进”，不再只写孤立阶段名。
- 边界自检：immutable expectation、old path failure boundary、`PassManager` 兼容桥、analysis 后置到 S8 的边界已经写清。

## 参考资料

- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)
- [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md)
- [`plan/a.md`](../../plan/a.md)

## 大闸蟹最新复评

- 复评人：`大闸蟹`
- 复评结论：`通过`
- 复评摘要：`最新正文已符合计划书标准与近期通过计划书的结构；S1-S8 均明确写成首任务类型 spec、默认链路 spec -> build -> review -> merge；analysis 留在 S8 尾段、tile 分两段串行、immutable expectation 只读与 canonical public path 先固定的边界均已写实，可继续按正文推进。`
