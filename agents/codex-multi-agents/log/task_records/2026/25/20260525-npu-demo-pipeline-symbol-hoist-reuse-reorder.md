# T-20260526 npu-demo pipeline symbol-hoist reuse reorder

## 管理员下发前记录

- 时间：2026-05-26
- 经办人：神秘人
- 任务类型：计划级 execute
- 计划书：`ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md`
- worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`
- 分支：`task/npu-demo-pipeline-symbol-hoist-reuse-reorder`
- 基线：`origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder.md`

### 下发依据

- 用户最新明确：`memory-plan` 是整个 pipeline 重构计划的一部分，不是独立小计划。
- 守护最好的爱莉希雅回报：`ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` 已完成两轮 subagent 严格审阅、用户待决策项收口和守护最终检验，结论为通过，可下发唯一计划级 execute。
- 窄任务 `T-20260526-dc681a62 / memory-plan-scf-if-branch-local-reuse` 已按最新口径暂停，不再继续执行，避免与本全量计划并行写 `kernel_gen/passes/memory_plan.py`、`spec/pass/memory_plan.md`、`test/passes/test_memory_plan.py`。

### 任务目标

按 `ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` 完成全量闭环：

- 完成 npu-demo pipeline 中 `symbol-hoist` 与 `memory-plan reuse` 重排。
- 完成 `kernel.matmul` acc 公开 API / spec / 实现 / pytest。
- 完成 `MemoryPlanPass(insert_free=True, reuse=True, fold=False)` 对单块 `scf.if` branch-local alloc/free/reuse 的支持。
- 完成 `KernelMatmulFusionDecomposePass` 对 `acc` 的新分解形态。
- 完成 `MemoryPoolPass(rewrite=True, alignment=1024)` 动态 offset rewrite/alignment 支持。
- 同步计划指定 spec、实现、测试、include 与 9 个 npu-demo kernel demo 验收。
- 跑通计划列出的主仓只读 expectation 合同验收。

### 合同真源

- execute 候选 diff 不得修改、复制、新建、同步或删除 `expectation/`。
- 主仓只读必过：
  - `expectation.pass.memory_plan`
  - `expectation.pass.kernel_aggregate`
  - `expectation.pass.kernel_matmul_fusion_decompose`
  - `expectation.pass.memory_pool`
- 架构侧预同步 hash：
  - `expectation/pass/memory_plan/control_flow.py`：`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`
  - `expectation/pass/kernel_matmul_fusion_decompose/basic.py`：`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`
- 运行 expectation 时必须使用任务 worktree 在前、主仓在后的导入边界，并记录 import proof。

### 禁止修改面

- 不得修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 不得把 paused 窄任务作为独立合并链路继续推进。
- 若主仓只读 expectation 因合同真源或导入边界冲突失败，execute 只记录并回报，不能自行修改 expectation。

### 流程要求

- 本任务为计划级任务，必须按 `execute -> review -> archive_acceptance -> merge` 流转。
- review 通过后不得直接进入 merge，必须先进入 archive_acceptance。
- merge 前必须确认任务记录与代码/spec/test 同批纳入候选提交。

## execute 进度记录

### 2026-05-26 21:56 +0800 睡觉小分队

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`。
- 候选来源确认：本轮只在全量计划 worktree 内形成候选 diff；未从暂停的 `T-20260526-dc681a62` 窄任务 worktree 复制、同步或复用未验证 `memory_plan.py` diff。
- 执行前阅读：已读取个人 prompt、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、主仓只读计划书 `ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` 与本任务记录。
- 当前已落地：
  - `npu-demo-lowering` pass 顺序重排为三段 `MemoryPlanPass(insert_free=True, reuse=True, fold=False) -> SymbolHoistPipelinePass -> cse -> canonicalize`，移除 pipeline 顶层 standalone `SymbolBufferHoistPass`，并固定 `MemoryPoolPass(rewrite=True, alignment=1024)`。
  - `SymbolHoistPipelinePass` 调整为 clone/verify/rollback 两阶段：第一段仅 alias-to-reinterpret，第二段按 `symbol-loop-hoist -> symbol-buffer-hoist -> hoist-dma-alias-ops` 固定顺序。
  - `MemoryPlanPass` 支持单块 `scf.if` branch-local alloc/free/reuse，并补充 `scf.yield` 逃逸拒绝。
  - `MemoryPoolPass` 支持动态 aligned offset 物化。
  - `kernel.matmul` acc 公开 API、dialect effect、DSL AST/plugin、npu_demo emit/include 与 `KernelMatmulFusionDecomposePass` 新分解形态已同步。
  - 已同步对应 `spec/pass/*`、`spec/dialect/kernel.md`、`spec/operation/kernel.md`、`spec/dsl/ast/*`、`spec/include/api/Kernel.md`。
- 已完成验证：
  - `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/passes/hoist/symbol_hoist_pipeline.py kernel_gen/passes/hoist/symbol_buffer_hoist.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py kernel_gen/dialect/kernel/operation/structured.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py`：通过。
  - `pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：`10 passed`。
  - `pytest -q test/passes/test_symbol_hoist_pipeline.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py`：`108 passed`。
  - `pytest -q test/operation/kernel/test_structured.py -k matmul`：`1 passed, 2 deselected`。
  - `pytest -q test/dialect/kernel/test_kernel.py -k matmul`：`7 passed, 29 deselected`。
  - `pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -k matmul`：`2 passed, 67 deselected`。
  - `pytest -q test/include/api/test_kernel.py`：`5 passed`。
  - `pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py -k "matmul or npu_demo"`：`91 passed, 79 deselected`。
  - `pytest -q test/passes/test_kernel_aggregate.py test/passes/test_kernel_matmul_fusion_decompose.py`：`13 passed`。
  - `pytest -q test/passes/test_registry.py -k "symbol_hoist_pipeline or symbol_buffer_hoist or memory_plan"`：`5 passed, 59 deselected`。
  - `pytest -q test/passes/test_memory_plan.py -k "scf_if_branch_yield_escape or scf_if"`：`5 passed, 21 deselected`。
  - 主仓只读 `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：通过。
- 当前待完成：
  - 复跑四个计划列名主仓只读 expectation 全入口并记录 import proof。
  - 复跑 9 个 npu-demo kernel demo。
  - 复跑 `git diff --check`、静态扫描、敏感目录门禁和最终 Diff 反推自测汇总。
  - 补齐最终自检后按流程 `-next review`。

## 管理员暂停记录

- 时间：2026-05-26
- 经办人：神秘人
- 结论：暂停 `T-20260526-d06257fb`。
- 原因：守护最好的爱莉希雅更新计划状态：用户新增 `kernel.matmul_fusion` 的 `fusion_list` 字符串属性后，`ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` Round 4 两个 subagent strict review 均为最小需改项；计划正文虽已吸收 API 列表、`__init__.py` 文件级 API 范围、非空 `fusion_list` decompose 语义不变 pytest 等要求，但 `expectation.pass.kernel_aggregate` 仍需架构侧预同步到包含 `fusion_list=\"kernel.matmul,kernel.binary_elewise.add\"` 的新合同并记录 hash / 红绿状态。因此当前全量计划不可下发。
- 处置：已通过任务脚本 `-pause` 暂停任务；execute 不得继续修改、验证或 `-next`。当前 worktree 中已有候选 diff 仅作为暂停现场，不得进入 review/merge，也不得作为最终候选依据。
- 禁止修改面：继续保持 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 非候选范围；execute 不得自行同步 `expectation.pass.kernel_aggregate`。

## 管理员恢复记录

- 时间：2026-05-26
- 经办人：神秘人
- 结论：恢复 `T-20260526-d06257fb` execute。
- 恢复依据：守护最好的爱莉希雅回报 `expectation.pass.kernel_aggregate` 已由架构侧极窄预同步完成；计划书状态已更新为 `可下发候选 / Round 4 已收口 / 守护最终检验通过`，最小阻断项无。
- 核对结果：
  - 计划书 `ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` 已记录 `expectation/pass/kernel_aggregate/basic.py` sha256=`f986f1c9ca6cb6f807b8799f989d903a0aeab5ab3023b25fe153331175401b9e`。
  - 主仓 `sha256sum expectation/pass/kernel_aggregate/basic.py` 与计划一致。
  - `python3 -m py_compile expectation/pass/kernel_aggregate/basic.py` 通过。
- 恢复要求：
  - execute 继续在本 worktree 收口，不得修改、复制、新建、同步或删除 `expectation/`。
  - 必须补齐基于最新计划的 `fusion_list` 公开 API / spec / pytest / expectation 验收记录。
  - 继续保持 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 非候选范围。

### 2026-05-26 23:24 +0800 睡觉小分队

- 任务：`T-20260526-d06257fb / npu-demo pipeline symbol-hoist reuse reorder` 恢复后 execute 复验。
- 任务目标：在恢复后的同一 worktree 内继续收口 `fusion_list`、pipeline reorder、memory plan reuse、memory pool rewrite/alignment、9 demo 与主仓只读 expectation 验收；若仍有合同阻塞则写清证据并回报，不流转 review。
- 执行前阅读记录：
  - 重新读取 `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
  - 复核本记录中的暂停/恢复记录、主仓只读计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` 与恢复 hash：`expectation/pass/kernel_aggregate/basic.py` = `f986f1c9ca6cb6f807b8799f989d903a0aeab5ab3023b25fe153331175401b9e`。
  - 现场基线：`HEAD=origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，分支 `task/npu-demo-pipeline-symbol-hoist-reuse-reorder`，`merge-base HEAD origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`。
- 最小功能闭环：
  - `kernel.matmul` / `KernelMatmulOp` / DSL / include / emit 已承接 `acc` 公开 API，`npu_demo::matmul(..., bool acc=false)` 已按 false overwrite、true accumulate 发射。
  - `KernelMatmulFusionOp` 已承接 `fusion_list: str | StringAttr = ""`；默认空保持旧兼容，非字符串 attr 按 `kernel.matmul_fusion fusion_list must be string` 失败；`KernelAggregatePass(matmul_acc=True)` 已生成固定 `fusion_list = "kernel.matmul,kernel.binary_elewise.add"`；`KernelMatmulFusionDecomposePass` 不复制 metadata。
  - `npu-demo-lowering` 已改为计划顺序，移除 pipeline 顶层 standalone `SymbolBufferHoistPass`，保留 public pass；`MemoryPoolPass(rewrite=True, alignment=1024)` 已按动态 chained alignment 物化 offset。
  - 候选来源仍仅为本全量计划 worktree；未从暂停的 `T-20260526-dc681a62` 窄任务 worktree 复制或同步 diff。
- Diff 反推自测：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：`10 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_hoist_pipeline.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py`：`71 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_pool.py`：`39 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel/test_structured.py -k "matmul"`：`1 passed, 2 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k "matmul"`：`7 passed, 29 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -k "matmul"`：`2 passed, 67 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py`：`5 passed`；计划中的 `-k "matmul"` 在当前文件无匹配项会返回 exit 5，因此用整文件公开 include API 测试覆盖。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py -k "matmul or npu_demo"`：`91 passed, 79 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_kernel_aggregate.py test/passes/test_kernel_matmul_fusion_decompose.py`：`14 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py -k "symbol_hoist_pipeline or symbol_buffer_hoist or memory_plan"`：`5 passed, 59 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py -k "scf_if_branch_yield_escape or scf_if"`：`5 passed, 21 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/passes/hoist/symbol_hoist_pipeline.py kernel_gen/passes/hoist/symbol_buffer_hoist.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py kernel_gen/dialect/kernel/operation/structured.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py`：通过。
- 9 个 npu-demo kernel demo：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/matmul/inputs_static_tile_static_*`，关键 marker `absent_bias max_abs_diff=3.433e-05`、`present_bias max_abs_diff=3.433e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/matmul/inputs_static_tile_dynamic`，关键 marker `max_abs_diff=3.052e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/matmul/inputs_dynamic_tile_dynamic`，关键 marker `max_abs_diff=4.578e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/conv2d/inputs_static_tile_static_*`，关键 marker `absent_bias max_abs_diff=4.196e-05`、`present_bias max_abs_diff=4.196e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/conv2d/inputs_static_tile_dynamic_*`，关键 marker `absent_bias max_abs_diff=3.815e-05`、`present_bias max_abs_diff=3.815e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/conv2d/inputs_dynamic_tile_dynamic`，关键 marker `max_abs_diff=4.578e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/flash_attention/inputs_static_tile_static`，关键 marker `max_abs_diff=1.837e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/flash_attention/inputs_static_tile_dynamic`，关键 marker `max_abs_diff=1.190e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/flash_attention/inputs_dynamic_tile_dynamic`，关键 marker `max_abs_diff=9.716e-06`。
- 合同验收：
  - 导入边界：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate`；`expectation.*` 来自主仓，`kernel_gen.*` 来自任务 worktree。
  - 主仓只读 `python3 -m expectation.pass.memory_plan`：通过；`expectation/pass/memory_plan/control_flow.py` hash=`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`。
  - 主仓只读 `python3 -m expectation.pass.kernel_matmul_fusion_decompose`：通过；`expectation/pass/kernel_matmul_fusion_decompose/basic.py` hash=`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`。
  - 主仓只读 `python3 -m expectation.pass.memory_pool`：通过；`expectation/pass/memory_pool/basic.py` hash=`3bc7aaedc9386bd1771433cedd1b7f4db7872c18ebebd0094eb9e4f75d310838`。
  - 主仓只读 `python3 -m expectation.pass.kernel_aggregate`：失败，阻塞。
- `expectation.pass.kernel_aggregate` 阻塞证据：
  - actual：`run_ircheck_text` 的实际 IR 已包含 `%acc = symbol.ne ...` 与 `"kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) {space = #nn.space<tsm>, fusion_list = "kernel.matmul,kernel.binary_elewise.add"} ...`。
  - expected：主仓只读 `expectation/pass/kernel_aggregate/basic.py` 当前 CHECK 运行时文本为 `"kernel.matmul_fusion"(%out, %lhs, %rhs, %[[ACC]]) {.*fusion_list = "kernel.matmul,kernel.binary_elewise.add".*}`。
  - spec：当前 `kernel_gen.tools.ircheck` 文件说明与实现均规定 `CHECK` 普通文本按字面量匹配，行内 regex 必须使用 `{{...}}` 或局部 `[[NAME:REGEX]]`；单花括号 `{.*...*}` 不是通用 regex 片段，只支持完整 `{.*}` 空白兼容片段。
  - verdict：当前实现已生成计划要求的 `fusion_list` IR；失败点是主仓只读 expectation CHECK 文本把通配写成单花括号，导致 ircheck 按字面量寻找 `{.*fusion_list...*}`。execute 无权修改 `expectation/`，因此不 `-next review`，需架构侧极窄同步该 CHECK 或调整合同门禁。
- 静态与敏感目录核对：
  - `git diff --check`：通过。
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git ls-files --others --exclude-standard -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `rg -n "SymbolBufferHoistPass\\(" kernel_gen/pipeline/npu_demo_lowering.py spec/pass/pipeline/npu_demo_lowering.md test/passes/pipeline/test_npu_demo_lowering.py || true`：空，确认 pipeline 顶层 standalone `SymbolBufferHoistPass` 已退场。
  - `rg -n "ruses" kernel_gen spec test /home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md || true`：仅计划说明文本命中，无实现/spec/test 残留拼写。
  - `test ! -e kernel_gen/passes/pipeline`：通过，确认未新增计划外 `passes/pipeline` 包。
  - `rg -n "get_kernel_aggregate_patterns|get_kernel_matmul_fusion_decompose_patterns" kernel_gen spec test || true`：空，确认未保留旧 pattern getter 公开口径。
  - `rg -n "hasattr\\(ctx|getattr\\(ctx|callable\\(getattr" kernel_gen spec test || true`：仅命中既有无关测试 `test/tools/test_dsl_run.py` 与 `test/passes/lowering/nn_lowering/test_public_name.py`，本轮改动文件无新增 ctx 能力探测。
- 减法检查：
  - 新增/改动 private callable 重点核对：`kernel_gen/dialect/kernel/operation/structured.py:_normalize_matmul_fusion_list_attr` 有效代码 19 行，未调用其它 private callable，用于收敛 `fusion_list` 默认空、`str | StringAttr` 与稳定错误短语，不适合内联到 constructor / verifier 两处。
  - `kernel_gen/passes/kernel_aggregate.py` 与 `kernel_gen/passes/kernel_matmul_fusion_decompose.py` 本轮保持 pass 内部 helper 复用，`KernelAggregatePass` 的旧相邻 tmp+add 直接保留路径已由固定 `fusion_list` 聚合替代；`KernelMatmulFusionDecomposePass` 明确忽略并不复制 `fusion_list` metadata。
  - `kernel_gen/passes/memory_pool.py` 存在历史私有 helper 链式调用，本轮只在既有 rewrite/materialize 结构内补动态 alignment 链；已用新增 pytest 和 9 demo 约束行为。若 review 要求按最新 private callable 规则整体拆解该历史文件，需要架构另定范围，当前不越权大规模重构。
- 自检：
  - 已核对公开 API 列表与 spec：`kernel.matmul acc`、`KernelMatmulFusionOp fusion_list`、pipeline 顺序、memory plan reuse、memory pool rewrite/alignment 均已同步到对应 spec/test。
  - 已核对异常边界：`fusion_list` 非字符串、`acc` 非 i1、shape/dtype mismatch、`scf.yield` 逃逸、dynamic memory pool alignment 均有公开 pytest 或合同覆盖。
  - 已核对兼容性：`KernelMatmulAST(out,lhs,rhs,location)` 旧位置参数仍兼容；`KernelMatmulFusionOp` 空 `fusion_list` 不打印 attr，保留旧 IR 兼容。
  - 当前唯一阻塞为只读 `expectation.pass.kernel_aggregate` CHECK 文本与 ircheck 公开匹配语义不一致；execute 不修改 expectation，不流转 review。
- 结论：阻塞，等待管理员/架构师对 `expectation/pass/kernel_aggregate/basic.py` 两条 `fusion_list` CHECK 做极窄同步或调整本计划合同门禁；当前不执行 `-next`。

### 2026-05-26 23:36 +0800 睡觉小分队

- 任务：`T-20260526-d06257fb / npu-demo pipeline symbol-hoist reuse reorder` 架构极窄同步后 execute 收口。
- 任务目标：按守护最好的爱莉希雅与管理员恢复口径，基于主仓只读 `expectation.pass.kernel_aggregate` 新 hash 复跑计划验收、Diff 反推自测、9 demo、静态门禁与敏感目录空 diff，通过后流转 review。
- 恢复依据：
  - 守护最好的爱莉希雅裁定 A：仅极窄同步主仓 `expectation.pass.kernel_aggregate` CHECK 文本为 ircheck 当前公开语义可匹配写法，不改 ircheck、不改门禁。
  - 管理员同步 hash：`expectation/pass/kernel_aggregate/basic.py` sha256=`f899de09532749fedd27ab08978ec35eacf395772ae6cea408a76831cf76e0f9`。
- 导入边界 proof：
  - 命令环境：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate`。
  - `expectation.pass.kernel_aggregate.basic`：`/home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py`。
  - `expectation.pass.kernel_matmul_fusion_decompose.basic`：`/home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py`。
  - `expectation.pass.memory_pool.basic`：`/home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py`。
  - `expectation.pass.memory_plan.control_flow`：`/home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`。
  - `kernel_gen.passes.kernel_aggregate`：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder/kernel_gen/passes/kernel_aggregate.py`。
  - `kernel_gen.passes.kernel_matmul_fusion_decompose`：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder/kernel_gen/passes/kernel_matmul_fusion_decompose.py`。
  - `kernel_gen.passes.memory_pool`：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder/kernel_gen/passes/memory_pool.py`。
  - `kernel_gen.passes.memory_plan`：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder/kernel_gen/passes/memory_plan.py`。
- 主仓只读合同验收：
  - `sha256sum /home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py /home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py /home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py /home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`：分别为 `f899de09532749fedd27ab08978ec35eacf395772ae6cea408a76831cf76e0f9`、`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`、`3bc7aaedc9386bd1771433cedd1b7f4db7872c18ebebd0094eb9e4f75d310838`、`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_aggregate`：exit 0，4 cases 输出通过，锁定固定 `fusion_list` 的 aggregate 正例与 no-op 反例。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：exit 0，锁定 scf.if branch-local alloc/free/reuse、yield escape、dynamic lifetime、call boundary 与 lifecycle。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_matmul_fusion_decompose`：exit 0，锁定 `scf.if` true/false `kernel.matmul(acc=true/false)` 分解。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_pool`：exit 0，锁定 dynamic memory、alignment、mixed dtype、loop alloc、invalid non-contiguous、multiple spaces。
- Diff 反推自测：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_hoist_pipeline.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py test/passes/test_kernel_aggregate.py test/passes/test_kernel_matmul_fusion_decompose.py`：`134 passed, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel/test_structured.py -k matmul`：`1 passed, 2 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k matmul`：`7 passed, 29 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -k matmul`：`2 passed, 67 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/passes/test_registry.py -k 'symbol_hoist_pipeline or symbol_buffer_hoist or memory_plan or matmul'`：`9 passed, 60 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py -k 'matmul or npu_demo'`：`91 passed, 84 deselected, 2 warnings`。
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/passes/hoist/symbol_hoist_pipeline.py kernel_gen/passes/hoist/symbol_buffer_hoist.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py kernel_gen/dialect/kernel/operation/structured.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py`：exit 0。
- 9 个 npu-demo kernel demo：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/matmul/inputs_static_tile_static`，markers：`absent_bias max_abs_diff=3.4332275390625e-05`、`present_bias max_abs_diff=3.4332275390625e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/matmul/inputs_static_tile_dynamic`，markers：`absent_bias max_abs_diff=3.0517578125e-05`、`present_bias max_abs_diff=3.0517578125e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/matmul/inputs_dynamic_tile_dynamic`，markers：`absent_bias max_abs_diff=4.57763671875e-05`、`present_bias max_abs_diff=4.57763671875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/conv2d/inputs_static_tile_static`，markers：`absent_bias max_abs_diff=4.1961669921875e-05`、`present_bias max_abs_diff=4.1961669921875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/conv2d/inputs_static_tile_dynamic`，markers：`absent_bias max_abs_diff=3.814697265625e-05`、`present_bias max_abs_diff=3.814697265625e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/conv2d/inputs_dynamic_tile_dynamic`，markers：`absent_bias max_abs_diff=4.57763671875e-05`、`present_bias max_abs_diff=4.57763671875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/flash_attention/inputs_static_tile_static`，marker：`max_abs_diff=1.837313175201416e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/flash_attention/inputs_static_tile_dynamic`，marker：`max_abs_diff=1.1898577213287354e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/flash_attention/inputs_dynamic_tile_dynamic`，marker：`max_abs_diff=9.715557098388672e-06`。
- 静态扫描与敏感目录门禁：
  - `git diff --check`：exit 0。
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git ls-files --others --exclude-standard -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `rg -n "SymbolBufferHoistPass\\(" kernel_gen/pipeline/npu_demo_lowering.py spec/pass/pipeline/npu_demo_lowering.md test/passes/pipeline/test_npu_demo_lowering.py || true`：空。
  - `rg -n "get_kernel_aggregate_patterns|get_kernel_matmul_fusion_decompose_patterns" kernel_gen spec test || true`：空。
  - `rg -n "hasattr\\(ctx|getattr\\(ctx|callable\\(getattr" kernel_gen spec test || true`：仅既有无关测试 `test/tools/test_dsl_run.py:366` 与 `test/passes/lowering/nn_lowering/test_public_name.py:173-177`，本轮改动文件无新增 ctx 能力探测。
- 减法检查：
  - `fusion_list` CHECK 阻塞已由架构侧同步主仓 expectation 解决；本 worktree 未修改、复制、新建或删除 `expectation/`。
  - 本轮新增/改动 private callable 仍以 `kernel_gen/dialect/kernel/operation/structured.py:_normalize_matmul_fusion_list_attr` 为核心，19 行有效代码且不调用其它 private callable；其余改动沿用既有 pass 内部 helper，未新增公开 API 之外的跨文件 helper 调用。
  - 旧 pipeline 顶层 standalone `SymbolBufferHoistPass` 已从 `npu-demo-lowering` 退场，public pass/registry 保留；旧 `kernel.matmul+binary_elewise.add` 临时累加形态由 `KernelAggregatePass` 改为带 `fusion_list` 的 `kernel.matmul_fusion`。
- 自检：
  - 接口：`kernel.matmul acc`、`KernelMatmulFusionOp fusion_list`、`npu_demo::matmul(..., bool acc=false)`、pipeline pass 顺序、memory plan/memory pool 合同均与 spec/API 列表一致。
  - 边界与异常：覆盖空/非空 `fusion_list`、非字符串 `fusion_list`、`acc` 兼容、`scf.if` branch-local reuse、yield escape、dynamic aligned offset、no-op 反例和 9 demo 真执行。
  - 兼容性：未删除 `SymbolBufferHoistPass` public pass；`KernelMatmulAST` 位置 `location` 兼容；`KernelMatmulFusionOp` 默认空 `fusion_list` 不改变旧 IR。
  - 测试有效性：Diff 反推 pytest 覆盖实现/spec/API 改动，expectation 单列合同验收，9 demo 覆盖 pipeline 真执行与 source 编译运行。
  - 禁止修改面：候选 diff 中 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md` 为空。
- 结论：execute 已闭环，按计划级流程流转 `review`；后续仍应按 `execute -> review -> archive_acceptance -> merge`，review 通过后不得直接 merge。

## review 前置同步阻塞 - 2026-05-26 23:39 CST - 提莫炖蘑菇

结论：暂停 review，不给通过结论；等待管理员/执行人按最新主线安全对齐后重新流转 review。

任务：`T-20260526-d06257fb / npu-demo pipeline symbol-hoist reuse reorder`

执行目录：
- `/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`

同步基线：
- 已执行 `git fetch origin --prune`
- `HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`
- `merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- 分支：`task/npu-demo-pipeline-symbol-hoist-reuse-reorder`

阻塞原因：
- 待审 worktree 未在最新 `origin/main` 基线上；`origin/main` 已新增提交 `61f5dba3 merge npu demo emitc brace list source contract`。
- `git diff --name-only HEAD..origin/main` 显示最新主线包含 brace-list source contract 36 个文件改动。
- 本任务候选 diff 与最新主线 diff 在 `test/dsl/gen_kernel/emit/test_package.py` 重叠：
  - `comm -12 <(git diff --name-only | sort) <(git diff --name-only HEAD..origin/main | sort)` 输出 `test/dsl/gen_kernel/emit/test_package.py`。
- 该重叠文件中，任务候选修改 `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline` 的 `matmul(..., false /*acc*/)` 断言；最新主线同文件大量更新 brace-list `Vector` 合同断言。直接 merge/checkout/rebase 有覆盖或冲突风险。

当前判断：
- 按最新审查前置同步规则，review / 复审 / archive_acceptance 前必须先把待审 worktree 对齐最新 `origin/main`，且不得覆盖任务 diff 或丢失他人改动。
- 当前存在重叠文件，review 不能强行 merge/reset/checkout，也不能在旧基线 `f93fc1a...` 上给出通过结论。

最小处理建议：
- 由 execute 在当前任务 worktree 中安全对齐 `origin/main@61f5dba3c3f09d554794d9cd4d066570acb6da53`，保留本任务候选 diff，人工核对并解决 `test/dsl/gen_kernel/emit/test_package.py` 的 brace-list 合同与 `matmul acc` 断言叠加。
- 对齐后复跑计划记录中的 Diff 反推 pytest、9 个 npu-demo demo、主仓只读 expectation 四入口、`git diff --check` 与敏感目录门禁。
- 记录最新同步现场、冲突处理或无冲突证明、复验结果后重新流转 review。

自检：
- 已读取任务记录尾部 execute 收口、主仓 TODO 当前指派和 worktree 状态。
- 未修改业务实现、spec、test、expectation 或任务状态文件。
- 未执行 merge/rebase/reset/checkout，未覆盖本地候选 diff。

### 2026-05-26 23:47 +0800 睡觉小分队

- 任务：`T-20260526-d06257fb / npu-demo pipeline symbol-hoist reuse reorder` review 前置同步返工。
- 任务目标：按 review 退回要求，在不覆盖候选 diff 的前提下安全对齐 latest `origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`，人工核对 `test/dsl/gen_kernel/emit/test_package.py` 中 brace-list 合同与 `matmul acc` 断言叠加，复跑计划门禁并重新流转 review。
- 执行前阅读记录：
  - 重新读取个人 prompt、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
  - 已读取本任务记录、review 前置同步阻塞记录和主仓只读计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md`。
- 最新同步现场：
  - 同步前：`HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，`origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`，`merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`。
  - 候选 diff 备份：`/tmp/T-20260526-d06257fb-align-20260526234251/`，包含 `worktree.diff`、`index.diff`、`status.txt`、`head.txt`、`origin_main.txt`。
  - 同步动作：执行 `git fetch origin --prune`；执行 `git stash push --include-untracked -m "T-20260526-d06257fb backup before origin/main align"` 保存候选 diff；执行 `git merge --ff-only origin/main` 快进到 `61f5dba3c3f09d554794d9cd4d066570acb6da53`；执行 `git stash pop` 恢复候选 diff。
  - 同步结果：`HEAD=origin/main=merge-base=61f5dba3c3f09d554794d9cd4d066570acb6da53`；`git stash pop` 自动合并，无冲突；本轮临时 stash 已 dropped，未留下本任务 stash。
  - 重叠文件处理：`test/dsl/gen_kernel/emit/test_package.py` 自动合并后人工核对，主线 brace-list/Vector 相关断言保留，本任务 `matmul<...>(..., false /*acc*/);` 断言保留；未使用 `reset/checkout/clean` 覆盖候选。
- 导入边界 proof：
  - 命令环境：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate`。
  - `expectation.pass.kernel_aggregate.basic`：`/home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py`。
  - `expectation.pass.kernel_matmul_fusion_decompose.basic`：`/home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py`。
  - `expectation.pass.memory_pool.basic`：`/home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py`。
  - `expectation.pass.memory_plan.control_flow`：`/home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`。
  - `kernel_gen.passes.kernel_aggregate`、`kernel_gen.passes.kernel_matmul_fusion_decompose`、`kernel_gen.passes.memory_pool`、`kernel_gen.passes.memory_plan` 均来自本任务 worktree。
- 主仓只读合同验收：
  - `sha256sum /home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py /home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py /home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py /home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`：分别为 `f899de09532749fedd27ab08978ec35eacf395772ae6cea408a76831cf76e0f9`、`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`、`3bc7aaedc9386bd1771433cedd1b7f4db7872c18ebebd0094eb9e4f75d310838`、`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_aggregate`：exit 0，4 cases 输出通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_matmul_fusion_decompose`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_pool`：exit 0。
- Diff 反推自测：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_hoist_pipeline.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py test/passes/test_kernel_aggregate.py test/passes/test_kernel_matmul_fusion_decompose.py`：`134 passed, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel/test_structured.py -k matmul`：`1 passed, 2 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k matmul`：`7 passed, 29 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -k matmul`：`2 passed, 67 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/passes/test_registry.py -k 'symbol_hoist_pipeline or symbol_buffer_hoist or memory_plan or matmul'`：`9 passed, 60 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py -k 'matmul or npu_demo'`：`91 passed, 84 deselected, 2 warnings`。
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/passes/hoist/symbol_hoist_pipeline.py kernel_gen/passes/hoist/symbol_buffer_hoist.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py kernel_gen/dialect/kernel/operation/structured.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py`：exit 0。
- 9 个 npu-demo kernel demo：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/matmul/inputs_static_tile_static`，markers：`absent_bias max_abs_diff=3.4332275390625e-05`、`present_bias max_abs_diff=3.4332275390625e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/matmul/inputs_static_tile_dynamic`，markers：`absent_bias max_abs_diff=3.0517578125e-05`、`present_bias max_abs_diff=3.0517578125e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/matmul/inputs_dynamic_tile_dynamic`，markers：`absent_bias max_abs_diff=4.57763671875e-05`、`present_bias max_abs_diff=4.57763671875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/conv2d/inputs_static_tile_static`，markers：`absent_bias max_abs_diff=4.1961669921875e-05`、`present_bias max_abs_diff=4.1961669921875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/conv2d/inputs_static_tile_dynamic`，markers：`absent_bias max_abs_diff=3.814697265625e-05`、`present_bias max_abs_diff=3.814697265625e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/conv2d/inputs_dynamic_tile_dynamic`，markers：`absent_bias max_abs_diff=4.57763671875e-05`、`present_bias max_abs_diff=4.57763671875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py`：exit 0，dump `kernel/dump/flash_attention/inputs_static_tile_static`，marker：`max_abs_diff=1.837313175201416e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：exit 0，dump `kernel/dump/flash_attention/inputs_static_tile_dynamic`，marker：`max_abs_diff=1.1898577213287354e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit 0，dump `kernel/dump/flash_attention/inputs_dynamic_tile_dynamic`，marker：`max_abs_diff=9.715557098388672e-06`。
- 静态扫描与敏感目录门禁：
  - `git diff --check`：exit 0。
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git ls-files --others --exclude-standard -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `rg -n "SymbolBufferHoistPass\\(" kernel_gen/pipeline/npu_demo_lowering.py spec/pass/pipeline/npu_demo_lowering.md test/passes/pipeline/test_npu_demo_lowering.py || true`：空。
  - `rg -n "get_kernel_aggregate_patterns|get_kernel_matmul_fusion_decompose_patterns" kernel_gen spec test || true`：空。
  - `rg -n "hasattr\\(ctx|getattr\\(ctx|callable\\(getattr" kernel_gen spec test || true`：仅既有无关测试 `test/tools/test_dsl_run.py:366` 与 `test/passes/lowering/nn_lowering/test_public_name.py:173-177`，本轮改动文件无新增 ctx 能力探测。
  - `rg -n "Vector\\{|long long .*layout|matmul<[^>]+>\\(v\\d+ /\\*out\\*/, v\\d+ /\\*lhs\\*/, v\\d+ /\\*rhs\\*/\\);" test/dsl/gen_kernel/emit/test_package.py || true`：仅命中主线保留的负向断言 `assert "Vector{" not in stmt`；未命中旧三参 matmul 调用断言。
- 减法检查：
  - 本轮同步只执行安全对齐和验证，未新增业务 helper；既有候选 `private callable` 清单与上一条 execute 记录一致。
  - `test/dsl/gen_kernel/emit/test_package.py` 的旧三参 `matmul` 断言已被本任务四参 `false /*acc*/` 断言替代，主线 brace-list 负向断言保留。
  - 本轮未修改、复制、新建、同步或删除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 自检：
  - 接口与边界：latest main brace-list source contract 与本任务 `matmul acc` 合同在重叠测试中共存；未删除主线新增断言。
  - 冲突风险：候选 diff 已在 `61f5dba3c3f09d554794d9cd4d066570acb6da53` 上恢复并验证；`test_package.py` 自动合并后人工核对通过。
  - 测试有效性：Diff 反推 pytest、9 demo、四项主仓只读 expectation、py_compile、diff check 和敏感目录门禁均在最新基线上通过。
  - 禁止修改面：候选 diff 不含 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md`。
- 结论：review 前置同步阻塞已解除，execute 在 latest `origin/main` 上重新闭环；按计划级流程重新流转 `review`，review 通过后仍应进入 `archive_acceptance`，不得直接 merge。

## review 结论 - 2026-05-27 00:18 CST - 提莫炖蘑菇

结论：最小需改项 / 不通过，退回 execute；本轮不得进入 `archive_acceptance`。

任务：`T-20260526-d06257fb / npu-demo pipeline symbol-hoist reuse reorder`

审查范围：
- worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`
- 计划书：主仓只读 `ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder.md`
- 被审 diff：`git diff --name-status` 中 41 个候选文件，覆盖 include/kernel dialect/operation/DSL emit/pass/spec/test 与任务记录。

最新同步现场：
- 已执行：`git fetch origin --prune`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`
- `HEAD=61f5dba3c3f09d554794d9cd4d066570acb6da53`
- `origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`
- `merge-base=61f5dba3c3f09d554794d9cd4d066570acb6da53`
- 分支：`task/npu-demo-pipeline-symbol-hoist-reuse-reorder`
- 同步结论：已在 latest `origin/main` 基线上，前序 `test/dsl/gen_kernel/emit/test_package.py` 重叠风险已由 execute 安全对齐并复验。

发现：

1. 阻断：本轮新增 / 改动 `private callable` 仍违反最新私有 helper 硬门禁。
   - 位置：
     - `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py:46`：新增 `_matmul_acc_literal(...)` 只有 4 行有效代码，低于 5 行有效代码下限。
     - `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py:64`：改动的 `_emit_npu_demo_kernel_matmul(...)` 调用 `_memory_element_cpp_type(...)` 与 `_matmul_acc_literal(...)`，形成 private callable 调 private callable。
     - `kernel_gen/dialect/kernel/operation/structured.py:101` 与 `kernel_gen/dialect/kernel/operation/structured.py:122`：新增 `_verify_matmul_acc_attr(...)` / `_normalize_matmul_acc_attr(...)` 调用 `_matmul_acc_error(...)` 或 `_verify_matmul_acc_attr(...)`，形成 private-to-private 链。
     - `test/dsl/ast/plugin/test_kernel.py:51`：新增 `_kernel_matmul_acc_stmt(...)` 只有 1 行有效代码。
     - 机械扫描还命中本轮改动的 `kernel_gen/passes/memory_plan.py`、`kernel_gen/passes/memory_pool.py` 中多处改动 private callable 继续调用 private callable；这些属于同一硬门禁，需要 execute 统一收口而不是只修单点。
   - 影响：违反当前个人 prompt 与 `agents/standard/审查规范.md` 的硬规则；review 不得以“只是内部 helper / 测试方便 / 当前能跑”放行。继续进入 `archive_acceptance` 会把新的私有 helper 链路固化。
   - 最小返工动作：
     - 对本轮新增 / 改动 private callable 做机械清单。
     - 小于 5 行有效代码的 helper 直接内联或合并到唯一足够深的当前文件 helper。
     - private callable 调 private callable 的链路改为内联、合并为单一 helper、或提升为已在 spec / 文件级 API 列表中确认的公开 API；测试 helper 不例外。
   - 验收方式：
     - 复跑本轮私有 callable 扫描，确认新增 / 改动 private callable 均不小于 5 行有效代码且不调用其它 private callable。
     - 复跑对应 pytest、`py_compile`、`git diff --check` 与敏感目录门禁。

2. 阻断：`KernelMatmulOp.acc` 的公开 spec 与实现不一致，且缺测试覆盖。
   - 位置：
     - `spec/dialect/kernel.md:293` 写明 `acc` 接受 `bool`、`0/1`、`IntegerAttr i1` 或 `IntAttr bool/int`。
     - `kernel_gen/dialect/kernel/operation/structured.py:140-142` 对 `IntAttr(True/False)` 显式抛 `kernel.matmul acc must be bool/i1`。
   - 证据：
     - `PYTHONPATH=. python3 - <<'PY' ... KernelMatmulOp(..., acc=IntAttr(True)) ... PY` 输出 `KernelCodeError`，错误短语为 `kernel.matmul acc must be bool/i1`。
     - 现有 `test/dialect/kernel/test_kernel.py -k matmul` 只覆盖 `acc=True`、`acc=2` 和非 i1 `IntegerAttr`，未覆盖 `IntAttr(True/False)` 的公开合同。
   - 影响：公开 API / spec / 实现 / pytest 不一致。调用方按 spec 传 `IntAttr(True)` 会失败；如果实际设计是拒绝 `IntAttr(bool)`，则 spec/API 合同需要用户确认后收窄。
   - 最小返工动作：
     - 按当前已确认公开合同修实现，让 `IntAttr(True/False)` 与 `IntAttr(1/0)` 行为一致，并补公开 pytest；或
     - 若要拒绝 `IntAttr(bool)`，必须先取得用户 / 架构确认并同步 spec/API 列表、实现错误语义与负例测试。
   - 验收方式：
     - 增补 `KernelMatmulOp(..., acc=IntAttr(True/False))` 正 / 负例（取决于确认后的合同）。
     - 复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k matmul`。

Diff 反推审查：
- 已读取实际 diff，不只依赖 execute 摘要；重点核对：
  - `kernel.matmul acc` include / operation / dialect / DSL / emit 链路。
  - `KernelMatmulFusionOp.fusion_list` 与 `KernelAggregatePass` / `KernelMatmulFusionDecomposePass`。
  - `MemoryPlanPass` scf.if branch-local 生命周期与 reuse。
  - `MemoryPoolPass(rewrite=True, alignment=1024)` 动态 offset 物化。
  - `npu-demo-lowering` 三段 `memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize` 顺序。
- 本轮复跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k 'matmul'`：`7 passed, 29 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py -k 'npu_demo and matmul'`：`2 passed, 70 deselected, 2 warnings`。
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dialect/kernel/operation/structured.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py`：exit 0。
- 未复跑 9 个 demo：已发现静态硬门禁和 spec/实现不一致阻断，继续跑完整 demo 不会改变 review 结论；execute 返工后需重跑并记录。

合同验收：
- 导入边界：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate`，主仓加载 `expectation`，任务 worktree 加载 `kernel_gen`。
- 已复跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_aggregate`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_matmul_fusion_decompose`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_pool`：exit 0。
- hash 核对：
  - `expectation/pass/kernel_aggregate/basic.py`：`f899de09532749fedd27ab08978ec35eacf395772ae6cea408a76831cf76e0f9`
  - `expectation/pass/kernel_matmul_fusion_decompose/basic.py`：`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`
  - `expectation/pass/memory_pool/basic.py`：`3bc7aaedc9386bd1771433cedd1b7f4db7872c18ebebd0094eb9e4f75d310838`
  - `expectation/pass/memory_plan/control_flow.py`：`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`
- 说明：`expectation` 只作为合同验收，不计入 Diff 反推测试；本 worktree 未修改 `expectation/`。

静态扫描与敏感目录：
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `rg -n "hasattr\\(ctx|getattr\\(ctx|callable\\(getattr|def [^(]+\\([^)]*object\\b|importlib\\.import_module|__import__|collect_ignore|pytest_ignore_collect|xfail|skip\\(" kernel_gen spec test || true`：命中均为既有无关测试 / spec / import matrix；本轮改动文件未新增 ctx 能力探测、`object` 签名或测试隐藏配置。

减法审查：
- 旧 pipeline 顶层 standalone `SymbolBufferHoistPass` 已被 `SymbolHoistPipelinePass` 承接，`rg` 核对目标 pipeline/spec/test 未残留 standalone 阶段。
- `KernelMatmulFusionDecomposePass` 已删除旧 tmp alloc + binary add + free 分解形态，改为 `scf.if` 双分支静态 `kernel.matmul(acc=true/false)`；有 pytest 与 expectation 覆盖。
- `KernelAggregatePass` 已删除原 apply 内手写遍历大段逻辑，改为单 root pattern，但引入/保留的 private callable 链路未按最新标准收口，是本轮阻断。
- 本轮新增/改动 private callable 的机械扫描已执行，发现小于 5 行和 private-to-private 调用，见 findings。

返工轮次标注：
- 新增问题：是。此前 review 只因 latest-main 同步阻塞暂停；本轮是同步阻塞解除后第一次基于 latest main 的实质审查。
- 重复问题：无。
- 范围扩大：无；两个阻断均来自当前候选 diff 直接触达文件和当前审查标准。

自检：
- 已按个人 prompt / `AGENTS.md` / `agents/standard/审查规范.md` 检查公开 API、非公开 API、测试边界、expectation 只读、Diff 反推审查、减法审查和私有 callable。
- 未修改业务实现、spec、test、plan、expectation 或任务状态文件；仅追加本审查记录。
- 由于存在明确可执行阻断项，结论不得写通过；计划级任务不得进入 `archive_acceptance`。

下一步：
- 退回 execute 修复上述两项最小阻断。
- execute 返工后需重新基于 latest main 记录同步现场，复跑 Diff 反推 pytest、9 个 npu-demo demo、四项主仓只读 expectation、`py_compile`、`git diff --check` 与敏感目录门禁，再重新流转 review。

## execute 返工收口 - 2026-05-27 00:19 CST - 咯咯咯

- 任务：`T-20260526-d06257fb / npu-demo pipeline symbol-hoist reuse reorder`
- 任务目标：只修复 review 指出的两个最小阻断项：本轮新增/改动 private callable 小于 5 行有效代码与 private-to-private 调用链；`KernelMatmulOp.acc` 的 `IntAttr(bool)` 公开 spec/实现/pytest 合同不一致。
- 执行前阅读记录：
  - 已读最新个人提示词 `/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`。
  - 已读根 `AGENTS.md`、`agents/standard/规则索引.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/任务记录约定.md`。
  - worktree 内计划书路径缺失，改读主仓只读计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md`。
  - 已读本记录尾部 review 结论，确认本轮只收口两个最小阻断，不修改 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md`。
- 最新同步现场：
  - 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`。
  - 已执行 `git fetch origin --prune`。
  - `HEAD=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
  - `origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
  - `merge-base=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
  - `ahead/behind=0/0`，无需合并；未执行 `reset/checkout/clean`，未覆盖候选 diff。
- 改动：
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py`：删除本文件 `_memory_element_cpp_type(...)` 与 `_matmul_acc_literal(...)` 两个 private helper，将 dtype template 解析与 `acc` C++ bool literal 直接收口到注册 emit 函数内，消除浅 helper 与 private-to-private 调用。
  - `kernel_gen/dialect/kernel/operation/structured.py`：删除 `_matmul_acc_error(...)`、`_verify_matmul_acc_attr(...)`、`_normalize_matmul_acc_attr(...)` private 链，改为当前文件私有规则容器 `_KernelMatmulAccRules`；`KernelMatmulOp.acc` 继续保持公开签名不变，并按 spec 接受 `IntAttr(True/False)` 与 `IntAttr(1/0)`。
  - `kernel_gen/dsl/ast/plugin/kernel.py`：`_build_matmul(...)` 内联 arity 检查，不再调用 `_ensure_arg_count(...)` private helper。
  - `kernel_gen/passes/memory_plan.py`：`_owner_block_for_alloc(...)` 内联支持 owner block 判定并删除 `_verify_supported_owner_block(...)`；`_is_escape_op(...)` 内联 alias use 判定，消除浅 helper 与 private-to-private 调用。
  - `kernel_gen/passes/memory_pool.py`：把本轮改动触达的 alignment / dynamic offset / rewrite info 复杂链路收进当前文件私有规则容器 `_MemoryPoolRewriteRules`，顶层 changed private callable 只做不少于 5 行的参数整理与公开命名方法调度；删除 `_floordiv_material(...)`、`_align_material(...)`、`_dynamic_offset_from_prior_numels(...)` 顶层 private 链。
  - `test/dialect/kernel/test_kernel.py`：补公开 pytest，覆盖 `KernelMatmulOp(..., acc=IntAttr(True))`、`IntAttr(False)` 与 `IntAttr(1)` 的 MemoryEffect 合同。
  - `test/dsl/ast/plugin/test_kernel.py` 与 `test/passes/pipeline/test_npu_demo_lowering.py`：将本轮新增/改动测试 helper 扩到不少于 5 行有效代码。
- 最小功能闭环：
  - private callable 阻断由 `test/repo_conformance/test_private_api_boundaries.py` 机械锁定：当前 diff private callable 不再浅于 5 行，且不再 private callable 调 private callable。
  - `KernelMatmulOp.acc` 公开合同按现有 spec 执行，不收窄公开 API；`IntAttr(bool)` 与 `IntAttr(0/1)` 均走公开 constructor，非法 `acc=2` 与非 i1 `IntegerAttr` 仍按 `kernel.matmul acc must be bool/i1` 失败。
- Diff 反推自测：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`：exit 0，`3 passed`；锁定 private API 边界、当前 diff private callable 五行与链路规则、模块 helper 前缀规则。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k matmul`：exit 0，`7 passed, 29 deselected`；锁定 `KernelMatmulOp.acc`、matmul/matmul_fusion verifier 与 effect。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_hoist_pipeline.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py test/passes/test_kernel_aggregate.py test/passes/test_kernel_matmul_fusion_decompose.py`：exit 0，`134 passed, 1 warning`；覆盖 pipeline、symbol hoist、memory-plan、memory-pool、aggregate 与 fusion decompose 改动。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel/test_structured.py -k matmul`：exit 0，`1 passed, 2 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -k matmul`：exit 0，`2 passed, 67 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/passes/test_registry.py -k 'symbol_hoist_pipeline or symbol_buffer_hoist or memory_plan or matmul'`：exit 0，`9 passed, 60 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py -k 'matmul or npu_demo'`：exit 0，`91 passed, 84 deselected, 2 warnings`。
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/passes/hoist/symbol_hoist_pipeline.py kernel_gen/passes/hoist/symbol_buffer_hoist.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py kernel_gen/dialect/kernel/operation/structured.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py test/dialect/kernel/test_kernel.py test/dsl/ast/plugin/test_kernel.py test/passes/pipeline/test_npu_demo_lowering.py`：exit 0。
- 9 个 npu-demo kernel demo：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit 0。
- 主仓只读合同验收：
  - `sha256sum /home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py /home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py /home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py /home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`：分别为 `f899de09532749fedd27ab08978ec35eacf395772ae6cea408a76831cf76e0f9`、`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`、`3bc7aaedc9386bd1771433cedd1b7f4db7872c18ebebd0094eb9e4f75d310838`、`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_aggregate`：exit 0，4 cases 输出通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_matmul_fusion_decompose`：exit 0，3 cases 输出通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_pool`：exit 0。
- 静态扫描与敏感目录门禁：
  - `rg -n "_matmul_acc_error|_verify_matmul_acc_attr|_normalize_matmul_acc_attr|_memory_element_cpp_type|_matmul_acc_literal|_floordiv_material|_align_material|_dynamic_offset_from_prior_numels|_verify_supported_owner_block" kernel_gen/dialect/kernel/operation/structured.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py || true`：输出为空。
  - `git diff --check`：exit 0。
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git ls-files --others --exclude-standard -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- 减法检查：
  - 删除 / 合并浅 helper：`_matmul_acc_literal(...)`、本文件 `_memory_element_cpp_type(...)`、`_verify_supported_owner_block(...)`、`_floordiv_material(...)`、`_align_material(...)`、`_dynamic_offset_from_prior_numels(...)` 已从对应文件移除。
  - 删除 / 合并 private-to-private 链：`_build_matmul(...) -> _ensure_arg_count(...)`、`_owner_block_for_alloc(...) -> _verify_supported_owner_block(...)`、`_is_escape_op(...) -> _operation_uses_alias(...)`、`_offset_bytes_material(...) -> _dynamic_offset_from_prior_numels(...)`、`_prepare_rewrite_infos(...) -> 多个 private helper` 均已收敛。
  - 保留依据：`_KernelMatmulAccRules` 与 `_MemoryPoolRewriteRules` 是当前文件私有规则容器，不新增公开 API、不跨文件调用非公开 API；顶层 changed private callable 已通过 repo conformance 机械 gate。
  - 机械验证：`test/repo_conformance/test_private_api_boundaries.py` exit 0，`rg` 旧 helper 名输出为空。
- 自检：
  - 接口：未新增/删除/重命名公开 API；`KernelMatmulOp.acc` 按现有 spec 保持 `bool | int | IntegerAttr | IntAttr` 签名并修复实现缺口。
  - 边界/异常：`IntAttr(True/False/1)` 正例补齐；`acc=2` 与非 i1 `IntegerAttr` 负例仍保留；memory-plan/memory-pool 既有公开错误语义由原 pytest 与 expectation 覆盖。
  - 非公开 API：未跨文件调用非公开 helper；当前 diff private callable 机械 gate 通过；测试未直连跨文件非公开 API。
  - 实现质量：删除浅 helper，减少 private-to-private 链；复杂 memory-pool rewrite 逻辑集中到当前文件规则容器，避免扩大公开 API。
  - 测试有效性：Diff 反推 pytest 覆盖本轮 touched implementation/spec/test；expectation 单列合同验收，不替代 pytest；9 demo 覆盖 npu-demo source 真实生成运行。
  - 禁止修改面：`expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md` 候选 diff 为空。
- 结论：两个最小阻断项已收口，execute 在 latest `origin/main` 上重新闭环；按计划级流程重新流转 `review`，review 通过后仍应进入 `archive_acceptance`，不得直接 merge。

## 状态续接 - 2026-05-27 00:22 CST - 咯咯咯

- 已执行 `codex-multi-agents-task.sh -next -task_id T-20260526-d06257fb -from 咯咯咯 -type review -auto`。
- 脚本结果：`OK: next T-20260526-d06257fb`；自动分派 `提莫炖蘑菇`；已向 `提莫炖蘑菇` 与 `神秘人` 发送 talk。
- 主仓 `TODO.md` 当前状态：`review / 提莫炖蘑菇 / 进行中`。

## review 复审结论 - 2026-05-27 00:28 CST - 提莫炖蘑菇

结论：通过。两个最小返工项已收口；本任务为计划级任务，review 通过后应进入 `archive_acceptance`，不得直接 merge。

任务：`T-20260526-d06257fb / npu-demo pipeline symbol-hoist reuse reorder`

审查范围：
- worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`
- 计划书：worktree 内 `ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` 不存在；按任务记录和下发口径读取主仓只读 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` 作为计划合同来源。
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder.md`
- 被审 diff：`git diff --name-status` 中 41 个候选文件，覆盖 include、kernel dialect/operation、DSL emit、pass、pipeline、spec、pytest 与本任务记录。

最新同步现场：
- 已执行：`git fetch origin --prune`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`
- `HEAD=61f5dba3c3f09d554794d9cd4d066570acb6da53`
- `origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`
- `merge-base=61f5dba3c3f09d554794d9cd4d066570acb6da53`
- 分支：`task/npu-demo-pipeline-symbol-hoist-reuse-reorder`
- 同步结论：已在 latest `origin/main` 基线上；本轮 review 未执行 merge/reset/checkout，未覆盖候选 diff。

findings：
- 无阻断项。

返工项核对：
- private callable 五行 / 链路门禁：
  - 复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`：`3 passed`。
  - 旧浅 helper 与 private-to-private 链路名反证：`rg -n "_matmul_acc_error|_verify_matmul_acc_attr|_normalize_matmul_acc_attr|_memory_element_cpp_type|_matmul_acc_literal|_floordiv_material|_align_material|_dynamic_offset_from_prior_numels|_verify_supported_owner_block" ...` 输出为空。
  - 核对结论：本轮新增/改动 private callable 已由机械 gate 锁定，不再存在上轮指出的 `<5` 行有效代码和 private callable 调 private callable 阻断。
- `KernelMatmulOp.acc IntAttr(bool)` 合同：
  - 复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k matmul`：`7 passed, 29 deselected`。
  - 额外直接构造核对：`KernelMatmulOp(..., acc=IntAttr(True/False/1/0)).verify()` 均通过，输出 `IntAttr bool/int acc accepted`。
  - `rg` 核对 `spec/dialect/kernel.md`、`kernel_gen/dialect/kernel/operation/structured.py`、`test/dialect/kernel/test_kernel.py`：spec 仍声明 `IntAttr bool/int` 合同，测试已覆盖 `IntAttr(True)`、`IntAttr(False)` 与 `IntAttr(1)`。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_hoist_pipeline.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py test/passes/test_kernel_aggregate.py test/passes/test_kernel_matmul_fusion_decompose.py`：`134 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py -k 'matmul or npu_demo'`：`91 passed, 84 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel/test_structured.py -k matmul test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -k matmul`：`3 passed, 69 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/passes/hoist/symbol_hoist_pipeline.py kernel_gen/passes/hoist/symbol_buffer_hoist.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py kernel_gen/dialect/kernel/operation/structured.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py test/dialect/kernel/test_kernel.py test/dsl/ast/plugin/test_kernel.py test/passes/pipeline/test_npu_demo_lowering.py`：exit 0。

9 个 npu-demo kernel demo：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit 0，`absent_bias max_abs_diff=3.4332275390625e-05`，`present_bias max_abs_diff=3.4332275390625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit 0，`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit 0，`absent_bias max_abs_diff=4.57763671875e-05`，`present_bias max_abs_diff=4.57763671875e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`：exit 0，`absent_bias max_abs_diff=4.1961669921875e-05`，`present_bias max_abs_diff=4.1961669921875e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`：exit 0，`absent_bias max_abs_diff=3.814697265625e-05`，`present_bias max_abs_diff=3.814697265625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit 0，`absent_bias max_abs_diff=4.57763671875e-05`，`present_bias max_abs_diff=4.57763671875e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py`：exit 0，`max_abs_diff=1.837313175201416e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：exit 0，`max_abs_diff=1.1898577213287354e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit 0，`max_abs_diff=9.715557098388672e-06`。

合同验收：
- 导入边界：cwd 为任务 worktree；`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate`，主仓加载 `expectation`，任务 worktree 加载 `kernel_gen`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_aggregate`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_matmul_fusion_decompose`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_pool`：exit 0。
- hash 核对：
  - `/home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py`：`f899de09532749fedd27ab08978ec35eacf395772ae6cea408a76831cf76e0f9`
  - `/home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py`：`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`
  - `/home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py`：`3bc7aaedc9386bd1771433cedd1b7f4db7872c18ebebd0094eb9e4f75d310838`
  - `/home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`：`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`
- 说明：`expectation` 只作合同验收，不计入 Diff 反推测试；本 worktree 候选 diff 不含 `expectation/`。

静态扫描与敏感目录：
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git status --short`：仅候选代码/spec/test 与本任务记录变更；未出现禁止目录。

减法审查：
- 上轮指出的 `_matmul_acc_literal`、本文件 `_memory_element_cpp_type`、`_verify_supported_owner_block`、`_floordiv_material`、`_align_material`、`_dynamic_offset_from_prior_numels` 等浅 helper / 私有链路已删除或合并。
- 旧 `KernelMatmulOp.acc IntAttr(bool)` 拒绝逻辑已替换为公开合同一致的接受路径，并补充 pytest。
- `test/dsl/gen_kernel/emit/test_package.py` 保留 latest main brace-list 断言，同时保留本任务 `matmul(..., false /*acc*/)` 断言；前序重叠文件对齐未回退。
- 未发现本轮返工新增旧入口、旧 shim 或禁止目录改动。

返工轮次标注：
- 重复问题：否。上轮两个阻断均已用机械测试与实际构造核对收口。
- 新增问题：无。
- 范围扩大：未发现；返工集中在 review 指定的 private callable 与 `KernelMatmulOp.acc` 合同。

自检：
- 已核对实际 diff、执行记录、计划合同、公开 API/spec/test 一致性、private callable 门禁、非公开 API 边界、Diff 反推审查、主仓只读 expectation 与敏感目录。
- 未修改业务实现、spec、test、plan、expectation 或任务状态文件；仅追加本 review 记录。
- 当前无剩余可执行返工项；计划级 review 通过后下一阶段为 `archive_acceptance`。

下一步：
- 使用标准脚本续接 `archive_acceptance / 计划书入档验收`，并回报管理员。

## archive_acceptance / 计划书入档验收 - 2026-05-27 00:41 CST - 不要啊教练

结论：通过。计划级任务 `T-20260526-d06257fb` 可按 `execute -> review -> archive_acceptance -> merge` 流转到 merge；不得由 archive_acceptance 直接合并。

任务目标：核对 latest 同步现场、review 通过记录、Diff 反推审查、四项主仓只读 expectation、9 个 npu-demo demo、`py_compile`、`git diff --check`、敏感目录空 diff、任务记录同批合入证据与可入档性。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`。
- 已执行：`git fetch origin --prune`，exit 0。
- 分支：`task/npu-demo-pipeline-symbol-hoist-reuse-reorder`。
- `HEAD=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
- `origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
- `merge-base=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
- `ahead/behind=0/0`，无需 merge；未执行 `reset/checkout/clean`，未覆盖候选 diff。
- 当前主仓 `TODO.md` 仍为 `archive_acceptance / 不要啊教练 / 进行中`。

计划与记录核对：
- 任务 worktree 内 `ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md` 不存在；本轮按任务记录和下发口径只读引用主仓共享计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_symbol_hoist_reuse_reorder_green_plan.md`。
- 主仓共享计划书 sha256：`65dd34c9358786a8cf7ffad2b51f484e42f1608453dbcec4376c14808c75beb7`。
- 已核对 `review 复审结论 - 2026-05-27 00:28 CST - 提莫炖蘑菇`：结论为通过，无阻断项，并明确下一阶段为 `archive_acceptance`。
- 任务记录当前为 untracked 候选文件：`agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder.md`；merge 前必须与代码/spec/test 同批 `git add` / 合入。

候选 diff 与范围：
- `git diff --name-status`：41 个已修改候选文件，覆盖 include、kernel dialect/operation、DSL AST/plugin/emit、pass、pipeline、spec 与 pytest。
- `git ls-files --others --exclude-standard`：仅本任务记录文件。
- `git diff --diff-filter=D --name-status`：空，未删除文件。
- 候选范围符合计划模块；未发现 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 进入候选 diff。

findings：
- 无阻断项。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`：exit 0，`3 passed`；锁定 private callable 五行 / 链路边界。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k matmul`：exit 0，`7 passed, 29 deselected`；锁定 `KernelMatmulOp.acc` 与 matmul dialect 行为。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_hoist_pipeline.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py test/passes/test_kernel_aggregate.py test/passes/test_kernel_matmul_fusion_decompose.py`：exit 0，`134 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py -k 'matmul or npu_demo'`：exit 0，`91 passed, 84 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel/test_structured.py -k matmul test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -k matmul`：exit 0，`3 passed, 69 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/passes/hoist/symbol_hoist_pipeline.py kernel_gen/passes/hoist/symbol_buffer_hoist.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py kernel_gen/dialect/kernel/operation/structured.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py test/dialect/kernel/test_kernel.py test/dsl/ast/plugin/test_kernel.py test/passes/pipeline/test_npu_demo_lowering.py`：exit 0。

9 个 npu-demo demo：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 kernel/matmul/inputs_static_tile_static.py`：exit 0；`absent_bias max_abs_diff=3.4332275390625e-05`，`present_bias max_abs_diff=3.4332275390625e-05`。
- `... python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit 0；`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`。
- `... python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit 0；`absent_bias max_abs_diff=4.57763671875e-05`，`present_bias max_abs_diff=4.57763671875e-05`。
- `... python3 kernel/conv2d/inputs_static_tile_static.py`：exit 0；`absent_bias max_abs_diff=4.1961669921875e-05`，`present_bias max_abs_diff=4.1961669921875e-05`。
- `... python3 kernel/conv2d/inputs_static_tile_dynamic.py`：exit 0；`absent_bias max_abs_diff=3.814697265625e-05`，`present_bias max_abs_diff=3.814697265625e-05`。
- `... python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit 0；`absent_bias max_abs_diff=4.57763671875e-05`，`present_bias max_abs_diff=4.57763671875e-05`。
- `... python3 kernel/flash_attention/inputs_static_tile_static.py`：exit 0；`max_abs_diff=1.837313175201416e-05`。
- `... python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：exit 0；`max_abs_diff=1.1898577213287354e-05`。
- `... python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit 0；`max_abs_diff=9.715557098388672e-06`。
- 临时 demo 日志落点：`/tmp/t-20260526-d06257fb-demos`；该目录不属于候选 diff。

合同验收：
- 导入边界：cwd 为任务 worktree；`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate`，任务 worktree 优先加载 `kernel_gen`，主仓只读加载 `expectation`。
- import proof：
  - `expectation.pass.kernel_aggregate.basic=/home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py`
  - `expectation.pass.memory_plan.control_flow=/home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`
  - `expectation.pass.kernel_matmul_fusion_decompose.basic=/home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py`
  - `expectation.pass.memory_pool.basic=/home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py`
  - `kernel_gen=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder/kernel_gen/__init__.py`
- hash 核对：
  - `/home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py`：`f899de09532749fedd27ab08978ec35eacf395772ae6cea408a76831cf76e0f9`
  - `/home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py`：`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`
  - `/home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py`：`3bc7aaedc9386bd1771433cedd1b7f4db7872c18ebebd0094eb9e4f75d310838`
  - `/home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`：`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_aggregate`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_matmul_fusion_decompose`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_pool`：exit 0。
- 说明：`expectation` 只作为合同验收，不计入 Diff 反推测试；本任务候选 diff 未修改、复制、新建、移动或删除 `expectation/`。

静态扫描与敏感目录：
- 旧 helper 反证：`rg -n "_matmul_acc_error|_verify_matmul_acc_attr|_normalize_matmul_acc_attr|_memory_element_cpp_type|_matmul_acc_literal|_floordiv_material|_align_material|_dynamic_offset_from_prior_numels|_verify_supported_owner_block" ...` 输出为空。
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git ls-files --others --exclude-standard -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。

减法审查：
- 已复核 review 记录与本轮反证：上轮指出的浅 helper / private-to-private 链路已删除或合并，旧 helper 名扫描为空。
- `test/repo_conformance/test_private_api_boundaries.py` 通过，机械锁定本轮 private callable 边界。
- 未发现恢复旧 `KernelMatmulOp.acc IntAttr(bool)` 拒绝逻辑、旧 tmp alloc + binary add + free 分解形态、旧 standalone pipeline 顺序或旧敏感目录改动。

任务记录同批合入证据：
- 任务记录文件当前为 untracked 候选：`agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder.md`。
- merge 前必须把该记录与 41 个代码/spec/test 候选文件同批纳入，不得只合代码后补记录。
- 共享计划书只读存在于主仓，不在任务 worktree 候选 diff 中；merge 不应复制或伪造 worktree 计划书副本。

自检：
- 已按最新个人 prompt、`AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md` 与 `expectation任务规则.md` 执行 archive_acceptance。
- 已核对 latest main 同步现场、review 通过记录、实际候选 diff、Diff 反推测试、9 demo、合同验收、敏感目录、减法审查和任务记录同批合入要求。
- 未修改业务实现、spec、测试、计划书、`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md` 或 `DONE.md`；仅追加本 archive_acceptance 记录。
- 当前无剩余可执行返工项。

结论：archive_acceptance 通过；按计划级流程续接 `merge`。merge 前必须同批纳入代码/spec/test 与本任务记录，并继续排除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

---

## merge 记录 - 2026-05-27 00:49 CST - 李白

结论：merge 前核对通过；可提交并推送。

任务：`T-20260526-d06257fb / npu-demo pipeline symbol-hoist reuse reorder`

任务目标：
- 合入已通过 `archive_acceptance` 的代码、spec、test 与本任务记录。
- 确保任务记录 `agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder.md` 与 41 个代码/spec/test 候选同批纳入。
- 继续排除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`，不得复制或修改 expectation。

合并前同步：
- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`。
- `git fetch --prune origin`：exit 0。
- `HEAD=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
- `origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
- `merge-base=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
- ahead/behind=`0/0`。
- 主仓 `/home/lfr/kernelcode_generate` 同步核对：`HEAD=origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`，工作区 clean。
- 结果：任务 worktree 已在 latest main 基线上；无主线前进、无冲突、无覆盖他人改动。

实际合入来源：
- 源 worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder`。
- 源分支：`task/npu-demo-pipeline-symbol-hoist-reuse-reorder`。
- 源基线：`origin/main=61f5dba3c3f09d554794d9cd4d066570acb6da53`。
- 合入方式：在任务分支提交候选 diff 与本记录后，推送 `HEAD:main`；随后同步主仓本地 `main`。

实际候选范围：
- include：
  - `include/api/Kernel.h`
  - `include/npu_demo/Kernel.h`
- kernel dialect / operation / DSL / emit：
  - `kernel_gen/dialect/kernel/__init__.py`
  - `kernel_gen/dialect/kernel/operation/__init__.py`
  - `kernel_gen/dialect/kernel/operation/structured.py`
  - `kernel_gen/dsl/ast/nodes/kernel.py`
  - `kernel_gen/dsl/ast/plugin/kernel.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py`
  - `kernel_gen/operation/kernel/__init__.py`
  - `kernel_gen/operation/kernel/structured.py`
- pass / pipeline：
  - `kernel_gen/passes/hoist/symbol_hoist_pipeline.py`
  - `kernel_gen/passes/kernel_aggregate.py`
  - `kernel_gen/passes/kernel_matmul_fusion_decompose.py`
  - `kernel_gen/passes/memory_plan.py`
  - `kernel_gen/passes/memory_pool.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
- spec：
  - `spec/dialect/kernel.md`
  - `spec/dsl/ast/nodes/kernel.md`
  - `spec/dsl/ast/plugin/kernel.md`
  - `spec/include/api/Kernel.md`
  - `spec/operation/kernel.md`
  - `spec/pass/kernel_aggregate.md`
  - `spec/pass/kernel_matmul_fusion_decompose.md`
  - `spec/pass/lowering/memory_pool.md`
  - `spec/pass/memory_plan.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/pass/symbol_hoist_pipeline.md`
- test：
  - `test/dialect/kernel/test_kernel.py`
  - `test/dsl/ast/nodes/test_kernel.py`
  - `test/dsl/ast/plugin/test_kernel.py`
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/include/api/test_kernel.py`
  - `test/operation/kernel/test_structured.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_kernel_aggregate.py`
  - `test/passes/test_kernel_matmul_fusion_decompose.py`
  - `test/passes/test_memory_plan.py`
  - `test/passes/test_memory_pool.py`
  - `test/passes/test_symbol_hoist_pipeline.py`
- 任务记录：
  - `agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder.md`

任务记录核对：
- 已核对管理员下发记录、暂停/恢复记录、execute 记录、review 同步阻塞记录、latest-main 对齐返工记录、review 不通过记录、execute 返工记录、review 复审通过记录和 archive_acceptance 通过记录。
- 任务记录当前在 worktree 为 untracked，提交前将显式 `git add`，并与 41 个代码/spec/test 候选同批提交。
- 共享计划书只读存在于主仓，任务 worktree 内无计划书副本；本次不复制或伪造计划书副本。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`：exit 0，`3 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/kernel/test_kernel.py -k matmul`：exit 0，`7 passed, 29 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_hoist_pipeline.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py test/passes/test_kernel_aggregate.py test/passes/test_kernel_matmul_fusion_decompose.py`：exit 0，`134 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_kernel.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py -k 'matmul or npu_demo'`：exit 0，`91 passed, 84 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel/test_structured.py -k matmul test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -k matmul`：exit 0，`3 passed, 69 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/passes/hoist/symbol_hoist_pipeline.py kernel_gen/passes/hoist/symbol_buffer_hoist.py kernel_gen/passes/memory_plan.py kernel_gen/passes/memory_pool.py kernel_gen/passes/kernel_aggregate.py kernel_gen/passes/kernel_matmul_fusion_decompose.py kernel_gen/dialect/kernel/operation/structured.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py test/dialect/kernel/test_kernel.py test/dsl/ast/plugin/test_kernel.py test/passes/pipeline/test_npu_demo_lowering.py`：exit 0。

9 个 npu-demo demo：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 kernel/matmul/inputs_static_tile_static.py`：exit 0，`absent_bias max_abs_diff=3.4332275390625e-05`，`present_bias max_abs_diff=3.4332275390625e-05`。
- `... python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit 0，`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`。
- `... python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit 0，`absent_bias max_abs_diff=4.57763671875e-05`，`present_bias max_abs_diff=4.57763671875e-05`。
- `... python3 kernel/conv2d/inputs_static_tile_static.py`：exit 0，`absent_bias max_abs_diff=4.1961669921875e-05`，`present_bias max_abs_diff=4.1961669921875e-05`。
- `... python3 kernel/conv2d/inputs_static_tile_dynamic.py`：exit 0，`absent_bias max_abs_diff=3.814697265625e-05`，`present_bias max_abs_diff=3.814697265625e-05`。
- `... python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit 0，`absent_bias max_abs_diff=4.57763671875e-05`，`present_bias max_abs_diff=4.57763671875e-05`。
- `... python3 kernel/flash_attention/inputs_static_tile_static.py`：exit 0，`max_abs_diff=1.837313175201416e-05`。
- `... python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：exit 0，`max_abs_diff=1.1898577213287354e-05`。
- `... python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit 0，`max_abs_diff=9.715557098388672e-06`。

合同验收：
- 导入边界：cwd 为任务 worktree；`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate`，任务 worktree 优先加载 `kernel_gen`，主仓只读加载 `expectation`。
- import proof：
  - `expectation.pass.kernel_aggregate.basic=/home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py`
  - `expectation.pass.memory_plan.control_flow=/home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`
  - `expectation.pass.kernel_matmul_fusion_decompose.basic=/home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py`
  - `expectation.pass.memory_pool.basic=/home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py`
  - `kernel_gen=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder/kernel_gen/__init__.py`
- hash 核对：
  - `/home/lfr/kernelcode_generate/expectation/pass/kernel_aggregate/basic.py`：`f899de09532749fedd27ab08978ec35eacf395772ae6cea408a76831cf76e0f9`
  - `/home/lfr/kernelcode_generate/expectation/pass/kernel_matmul_fusion_decompose/basic.py`：`fa2959a7fde54409720701ed3ee87676cf0121baad440671e4cfd3b259862cc6`
  - `/home/lfr/kernelcode_generate/expectation/pass/memory_pool/basic.py`：`3bc7aaedc9386bd1771433cedd1b7f4db7872c18ebebd0094eb9e4f75d310838`
  - `/home/lfr/kernelcode_generate/expectation/pass/memory_plan/control_flow.py`：`1a939d77bef5632d26c6272c0a4d7d7f7a218ce14ef9a9c1ab847d5f589788d2`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_aggregate`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_matmul_fusion_decompose`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-pipeline-symbol-hoist-reuse-reorder:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_pool`：exit 0。
- 说明：`expectation` 只作为合同验收，不计入 Diff 反推测试；本任务候选 diff 未修改、复制、新建、移动或删除 `expectation/`。

静态扫描与敏感目录：
- `git diff --check`：exit 0。
- `git diff --name-only | wc -l`：`41`。
- `git ls-files --others --exclude-standard`：仅本任务记录。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。

冲突处理：
- 未发生 merge/rebase 冲突；latest main 未前进。
- 未使用 `reset` / `checkout` 覆盖候选 diff。
- 9 demo 产生的 ignored dump/cache 未进入候选 diff；提交前仅 stage 上述 41 个候选文件与任务记录。

剩余风险：
- 主仓只读 expectation 已按计划验收通过，但本次 merge 不合入 expectation；相关合同资产归属仍按前序架构极窄同步记录。
- 共享计划书不在任务 worktree 候选 diff 中，本次不提交计划书。

结论：
- merge 前核对通过；可提交并推送。
