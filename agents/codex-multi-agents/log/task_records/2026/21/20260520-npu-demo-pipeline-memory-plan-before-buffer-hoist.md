# T-20260520-b5abd965 / npu_demo_pipeline_memory_plan_before_buffer_hoist

## 2026-05-20 execute 执行前记录

时间：2026-05-20 13:40 CST
经办人：金铲铲大作战
任务：T-20260520-b5abd965 / npu_demo_pipeline_memory_plan_before_buffer_hoist
任务目标：按计划调整公开 `npu-demo-lowering` pipeline 顺序，两段 `MemoryPlanPass(insert_free=True, fold=False)` 前移到对应 `SymbolBufferHoistPass` 前，只删除 memory-pool 后那一次 `CommonSubexpressionElimination`，保留前三段 CSE 与 memory-pool 后 `CanonicalizePass`，同步 spec、pipeline builder、pipeline pytest、dump marker 断言与记录。
执行前阅读记录：已重新读取个人 prompt、根 `AGENTS.md`、`agents/standard/协作执行通用规则.md`、`实现文件规范.md`、`测试文件约定.md`、`任务记录约定.md`、`expectation任务规则.md`；已读取主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_pipeline_memory_plan_before_buffer_hoist_green_plan.md`，因任务 worktree 缺本地计划资产，本轮只读引用主仓共享计划；已核对 TODO 中任务状态为 `execute / 金铲铲大作战 / 进行中`。
改动：执行前尚未修改代码；确认禁止修改面为 `expectation/`、`.skills/`、`agents/standard/**`，本计划不以 expectation 作为必过资产。
验证：
- `git fetch origin --prune && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git status --short --untracked-files=all` -> `HEAD=origin/main=merge-base=578a9f6f3d122ed27fb1475ac9134d83db5a8062`，执行前无本地 diff。
- `git diff --name-only -- expectation .skills agents/standard && git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 无输出，敏感目录执行前空 diff。
自检：任务目标可执行；公开 API 签名、pipeline option、registry 名称均不变；只调整计划确认的公开 pipeline 顺序与对应 spec/test；如修改中发现需新增公开 API 或 expectation 合同变更，将暂停回报管理员/架构师。
结论：执行前现场可继续，进入实现/spec/test 修改。

## 2026-05-20 execute 完成记录

时间：2026-05-20 14:52 CST
经办人：金铲铲大作战
任务：T-20260520-b5abd965 / npu_demo_pipeline_memory_plan_before_buffer_hoist
任务目标：按计划完成公开 `npu-demo-lowering` pipeline 顺序调整，并同步 spec、pipeline builder、pipeline pytest、dump marker 断言。
改动：
- `kernel_gen/passes/pipeline/npu_demo_lowering.py`：将两段 `MemoryPlanPass(insert_free=True, fold=False)` 前移到各自 `SymbolBufferHoistPass` 之前；删除 memory-pool 后那一次 `CommonSubexpressionElimination`；保留前三段 CSE 与 memory-pool 后 `CanonicalizePass`；同步文件级说明与 API 列表中的公开顺序描述。
- `spec/pass/pipeline/npu_demo_lowering.md`：同步公开顺序、术语、目标、注意事项与测试矩阵，明确 memory-pool 后不再接入 CSE，顺序变为 `memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- `test/passes/pipeline/test_npu_demo_lowering.py`：更新 pass order 断言、dump marker 顺序断言、memory-pool 后负 CSE 断言与静态 dump 校验；点名测试仍只验证公开 API 与公开命令入口。
- 新增任务记录文件并补齐执行前阅读、验证、自检和结论。
验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -ra` -> `8 passed, 1 warning, exit=0`
- 9 个 kernel demo 逐个通过，均 `exit=0`：
  - `kernel/matmul/inputs_static_tile_static.py` -> `[CHECK] matmul/inputs_static_tile_static_absent_bias max_abs_diff=3.4332275390625e-05`，`[CHECK] matmul/inputs_static_tile_static_present_bias max_abs_diff=3.4332275390625e-05`
  - `kernel/matmul/inputs_static_tile_dynamic.py` -> `[IR] static memory evidence: 197x178x184 memory and TILE_H/TILE_W/TILE_K tile present`，`[CHECK] matmul/inputs_static_tile_dynamic/absent_bias max_abs_diff=3.0517578125e-05`，`[CHECK] matmul/inputs_static_tile_dynamic/present_bias max_abs_diff=3.0517578125e-05`
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py` -> `[IR] dynamic memory evidence: H/K/W memory and TILE_H/TILE_W/TILE_K tile present; static and anonymous shapes absent`，`[CHECK] matmul/inputs_dynamic_tile_dynamic/absent_bias max_abs_diff=3.0517578125e-05`，`[CHECK] matmul/inputs_dynamic_tile_dynamic/present_bias max_abs_diff=3.0517578125e-05`
  - `kernel/conv2d/inputs_static_tile_static.py` -> `[IR] static memory evidence: output/input/weight concrete shapes present; dynamic symbol shapes absent`，`[CHECK] conv2d/inputs_static_tile_static_absent_bias max_abs_diff=4.1961669921875e-05`，`[CHECK] conv2d/inputs_static_tile_static_present_bias max_abs_diff=4.1961669921875e-05`
  - `kernel/conv2d/inputs_static_tile_dynamic.py` -> `[IR] static memory evidence: output/input/weight concrete shapes present; dynamic symbol shapes absent`，`[CHECK] conv2d/inputs_static_tile_dynamic_absent_bias max_abs_diff=3.814697265625e-05`，`[CHECK] conv2d/inputs_static_tile_dynamic_present_bias max_abs_diff=3.814697265625e-05`
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py` -> `[IR] dynamic memory evidence: output/input/weight semantic symbolic memory present; memory-pool arch.get_dynamic_memory + dma.view present; dma.alloc/allalloc absent`，`[CHECK] conv2d/inputs_dynamic_tile_dynamic/absent_bias max_abs_diff=4.57763671875e-05`，`[CHECK] conv2d/inputs_dynamic_tile_dynamic/present_bias max_abs_diff=4.57763671875e-05`
  - `kernel/flash_attention/inputs_static_tile_static.py` -> `[CHECK] flash_attention/inputs_static_tile_static max_abs_diff=1.837313175201416e-05`
  - `kernel/flash_attention/inputs_static_tile_dynamic.py` -> `[CHECK] flash_attention/inputs_static_tile_dynamic max_abs_diff=1.1898577213287354e-05`
  - `kernel/flash_attention/inputs_dynamic_tile_dynamic.py` -> `[CHECK] flash_attention/inputs_dynamic_tile_dynamic max_abs_diff=9.715557098388672e-06`
- `kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel` marker 顺序复核：共 25 段，`cse` 仅 3 次，`memory-pool` 后直接为 `canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- `git diff --check` -> `exit=0`
- `git diff --name-only -- expectation .skills agents/standard && git diff --cached --name-only -- expectation .skills agents/standard && git status --short --untracked-files=all -- expectation .skills agents/standard && git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 全部空输出。
Diff 反推自测：本轮实际改动仅涉及 `kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`；用 `py_compile` 锁定实现语法，用 pipeline pytest 锁定公开顺序 / dump 断言 / 失败边界，用 9 个 kernel demo 锁定公开 npu-demo 正向链路与真实样例行为，用 dump marker 核对锁定 stage 顺序与 memory-pool 后无 CSE。
自检：已确认未修改 `expectation/`、`.skills/`、`agents/standard/**`；未新增公开 API、未改 `build_npu_demo_lowering_pipeline(...)` 签名、未新增 pipeline option、未接入 `MultiBufferPass`；测试只验证公开 builder、公开 pipeline 与公开 kernel demo 入口；`memory-pool` 后去掉 CSE 后，所有过渡断言仍能锁定公开顺序，不再依赖旧编号合同。
结论：已闭合，可进入 `review`。

## 2026-05-20 13:52 review 记录

时间：2026-05-20 13:52 +0800
经办人：不要啊教练
任务：T-20260520-b5abd965 / npu_demo_pipeline_memory_plan_before_buffer_hoist
任务目标：审查 `npu-demo-lowering` pipeline 顺序调整：两段 `MemoryPlanPass(insert_free=True, fold=False)` 前移到对应 `SymbolBufferHoistPass` 前、只删除 memory-pool 后 CSE、保留前三段 CSE 与 memory-pool 后 `CanonicalizePass`，核对 spec / 实现 / pytest / dump marker / 9 个 kernel demo / `git diff --check` / 敏感目录空 diff 与任务记录。

### 审查前置同步

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-pipeline-memory-plan-before-buffer-hoist`。
- 已执行：`git fetch origin --prune`。
- 同步基线：`HEAD=578a9f6f3d122ed27fb1475ac9134d83db5a8062`，`origin/main=578a9f6f3d122ed27fb1475ac9134d83db5a8062`，`merge-base=578a9f6f3d122ed27fb1475ac9134d83db5a8062`，`ahead/behind=0/0`。
- 当前无主线合并冲突或覆盖风险；工作树候选 diff 为 `kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py` 与任务记录。

### 被审 diff

- `kernel_gen/passes/pipeline/npu_demo_lowering.py`：两段 `MemoryPlanPass(insert_free=True, fold=False)` 已前移到对应 `SymbolBufferHoistPass` 前；memory-pool 后 `CommonSubexpressionElimination` 已删除，仍保留 memory-pool 后 `CanonicalizePass`；前三段 CSE 保留。
- `spec/pass/pipeline/npu_demo_lowering.md`：公开顺序、术语、注意事项和测试矩阵同步到 `memory-plan -> symbol-buffer-hoist` 与 `memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- `test/passes/pipeline/test_npu_demo_lowering.py`：pass order、dump marker、`markers.count("cse") == 3`、post-pool `canonicalize` 与静态 dump 断言已同步。
- `agents/codex-multi-agents/log/task_records/2026/21/20260520-npu-demo-pipeline-memory-plan-before-buffer-hoist.md`：执行前记录、完成记录、验证与自检已补齐。

### findings

- 无阻断项。
- 未发现可执行返工项；当前 diff 与计划目标一致，测试覆盖了本轮实际顺序调整和真实 demo 链路。

### Diff 反推审查

- 实现 / spec 核对：`rg -n "CommonSubexpressionElimination|MemoryPlanPass|SymbolBufferHoistPass|MemoryPoolPass|CanonicalizePass|ProducerConsumerAnalysisPass|build_npu_demo_lowering_pipeline|memory-pool" kernel_gen/passes/pipeline/npu_demo_lowering.py spec/pass/pipeline/npu_demo_lowering.md test/passes/pipeline/test_npu_demo_lowering.py` 已核对目标顺序、三段 CSE、四段 canonicalize、两段 `memory-plan -> symbol-buffer-hoist`、post-pool 无 CSE。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -ra`：exit=0，`8 passed, 1 warning`。
- 9 个 kernel demo 复跑均 exit=0：
  - `kernel/matmul/inputs_static_tile_static.py`：`[CHECK] matmul/inputs_static_tile_static_absent_bias max_abs_diff=3.4332275390625e-05`，`present_bias max_abs_diff=3.4332275390625e-05`。
  - `kernel/matmul/inputs_static_tile_dynamic.py`：`[IR] static memory evidence...`，absent/present `max_abs_diff=3.0517578125e-05`。
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py`：`[IR] dynamic memory evidence...`，absent/present `max_abs_diff=3.0517578125e-05`。
  - `kernel/conv2d/inputs_static_tile_static.py`：absent/present `max_abs_diff=4.1961669921875e-05`。
  - `kernel/conv2d/inputs_static_tile_dynamic.py`：absent/present `max_abs_diff=3.814697265625e-05`。
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py`：`[IR] dynamic memory evidence... memory-pool arch.get_dynamic_memory + dma.view present; dma.alloc/allalloc absent`，absent/present `max_abs_diff=4.57763671875e-05`。
  - `kernel/flash_attention/inputs_static_tile_static.py`：`max_abs_diff=1.837313175201416e-05`。
  - `kernel/flash_attention/inputs_static_tile_dynamic.py`：`max_abs_diff=1.1898577213287354e-05`。
  - `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：`max_abs_diff=9.715557098388672e-06`。
- dump marker 复核：`kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel` 中 `.mlir` marker 共 25 段，序列为 `first-ir -> inline -> cse -> canonicalize -> decompass -> lower-nn -> symbol-loop-hoist -> cse -> canonicalize -> memory-plan -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> symbol-loop-hoist -> cse -> canonicalize -> memory-plan -> symbol-buffer-hoist -> memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`；`cse_count=3`，`canonicalize_count=4`，memory-pool 后 tail 为 `memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。

### 静态扫描与敏感目录

- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。
- `git diff -U0 -- kernel_gen spec test | rg -n '^\+.*(hasattr\(|getattr\(|callable\(getattr|from kernel_gen\.[A-Za-z0-9_.]+ import _|import kernel_gen\.[A-Za-z0-9_.]+\._|object\b|def [A-Za-z_][A-Za-z0-9_]*\(.*\):)' || true`：无新增命中。
- 运行 demo 后出现的 `.pytest_cache` 与 `kernel/dump/**` 为 ignored 运行产物，不在敏感目录内，不纳入候选 diff。

### 执行记录核对

- 执行记录包含执行前阅读、改动清单、Diff 反推自测、9 个 demo 验收、dump marker 复核、敏感目录空 diff、自检与结论。
- 本计划不以 `expectation` 作为必过资产；候选 diff 中 `expectation/` 为空。

### 自检

- 已基于最新 `origin/main` 对齐现场审查实际 diff。
- 已逐项核对实现、spec、pytest 与计划目标；未只采信执行摘要。
- 已检查公开 API：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 签名未变，未新增 pipeline option、registry 名称或公开 API。
- 已检查测试有效性：pipeline order 测试锁定 3 段 CSE、4 段 canonicalize、两段 `memory-plan -> symbol-buffer-hoist`，dump 测试锁定 post-pool 无 CSE 与真实 stage marker。
- 已检查跨文件非公开 API、ctx 能力探测、`object` 签名、非装饰器嵌套函数和敏感目录。
- 未发现剩余可执行返工项。

### 结论

- 结论：通过。
- 下一步：计划级任务请管理员接架构复核 / 终验；review 不直接 merge。

## 2026-05-20 13:59 第二架构计划级终验记录

时间：2026-05-20 13:59 CST
经办人：守护最好的爱莉希雅
任务：T-20260520-b5abd965 / npu-demo-pipeline-memory-plan-before-buffer-hoist
任务目标：按 `ARCHITECTURE/plan/npu_demo_pipeline_memory_plan_before_buffer_hoist_green_plan.md` 对 review 通过后的候选执行第二架构计划级复核 / 终验，核对最新同步现场、pipeline 顺序、dump marker、9 个 kernel demo、敏感目录空 diff、静态扫描和最小阻断项。

### 验证基线与执行目录

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-pipeline-memory-plan-before-buffer-hoist`。
- 已执行：`git fetch origin`。
- 基线核对：
  - `HEAD=578a9f6f3d122ed27fb1475ac9134d83db5a8062`
  - `origin/main=578a9f6f3d122ed27fb1475ac9134d83db5a8062`
  - `merge-base=578a9f6f3d122ed27fb1475ac9134d83db5a8062`
  - `ahead/behind=0/0`
- 当前工作树候选 diff：`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py` 与本任务记录；未发现主线覆盖风险。

### 计划目标核对

- `kernel_gen/passes/pipeline/npu_demo_lowering.py` 的 `pm.add_pass(...)` 顺序与计划唯一 pass-name 真源一致：
  - 第一段为 `... cse -> canonicalize -> memory-plan -> symbol-buffer-hoist -> tile-analysis`。
  - 第二段为 `lower-dma-memory-hierarchy -> symbol-loop-hoist -> cse -> canonicalize -> memory-plan -> symbol-buffer-hoist -> memory-pool`。
  - memory-pool 后为 `canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- `spec/pass/pipeline/npu_demo_lowering.md` 同步写清公开顺序、非目标、CSE/Canonicalize 关系和测试矩阵；未新增 pipeline option、registry pass name 或公开 API 签名。
- `test/passes/pipeline/test_npu_demo_lowering.py` 同步断言三段 CSE、四段 canonicalize、两段 `memory-plan -> symbol-buffer-hoist`、memory-pool 后无 CSE，以及 arch 早于 attach、attach 早于 outline。

### Diff 反推测试

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -ra`：exit=0，`8 passed, 1 warning`。

### Kernel demo 硬门禁

9 个 demo 均从任务 worktree 运行，全部 exit=0：

- `kernel/matmul/inputs_static_tile_static.py`：absent / present bias `max_abs_diff=3.4332275390625e-05`。
- `kernel/matmul/inputs_static_tile_dynamic.py`：静态 memory/tile evidence 存在，absent / present bias `max_abs_diff=3.0517578125e-05`。
- `kernel/matmul/inputs_dynamic_tile_dynamic.py`：动态 H/K/W 与 TILE_H/TILE_W/TILE_K evidence 存在，absent / present bias `max_abs_diff=3.0517578125e-05`。
- `kernel/conv2d/inputs_static_tile_static.py`：absent / present bias `max_abs_diff=4.1961669921875e-05`。
- `kernel/conv2d/inputs_static_tile_dynamic.py`：absent / present bias `max_abs_diff=3.814697265625e-05`。
- `kernel/conv2d/inputs_dynamic_tile_dynamic.py`：动态 memory-pool evidence 存在，absent / present bias `max_abs_diff=4.57763671875e-05`。
- `kernel/flash_attention/inputs_static_tile_static.py`：`max_abs_diff=1.837313175201416e-05`。
- `kernel/flash_attention/inputs_static_tile_dynamic.py`：`max_abs_diff=1.1898577213287354e-05`。
- `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：`max_abs_diff=9.715557098388672e-06`。

### Dump marker 终验

- 核对目录：`kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel`。
- marker 总数：25。
- `cse_count=3`，`canonicalize_count=4`。
- 完整 marker 序列：
  `first-ir -> inline -> cse -> canonicalize -> decompass -> lower-nn -> symbol-loop-hoist -> cse -> canonicalize -> memory-plan -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> symbol-loop-hoist -> cse -> canonicalize -> memory-plan -> symbol-buffer-hoist -> memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- post-pool tail：
  `memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- 判定：目标顺序、两段 `memory-plan -> symbol-buffer-hoist`、只删除 memory-pool 后那一次 CSE、保留 memory-pool 后 canonicalize 均已被机械验证。

### 禁止修改面与静态扫描

- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。
- 静态扫描：`git diff -U0 -- kernel_gen spec test | rg -n '^\\+.*(hasattr\\(|getattr\\(|callable\\(getattr|from kernel_gen\\.[A-Za-z0-9_.]+ import _|import kernel_gen\\.[A-Za-z0-9_.]+\\._|\\bobject\\b|def [A-Za-z_][A-Za-z0-9_]*\\(.*\\):)' || true` 无新增命中。
- 运行产生的 `.pytest_cache/`、`kernel/dump/`、`__pycache__/` 均为 ignored 产物，不属于候选 diff；敏感目录为空。

### expectation 口径

- 本计划正文明确“不新增、不同步、不要求运行任何 expectation”，当前终验未把 expectation 作为通过依据。
- 候选 diff 中 `expectation/` 为空，符合计划禁止修改面。

### 自检

- 已重新读取个人提示词、根 `AGENTS.md` 与 `agents/standard/任务记录约定.md`、`审查规范.md`。
- 已基于最新 `origin/main` 对齐现场复核实际 diff，不只采信 review 摘要。
- 已复核公开 API 边界：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 签名不变，pipeline option、registry、错误文本不变。
- 已复核测试有效性：pipeline pytest 与真实 dump marker 同时锁定目标顺序；9 个 kernel demo 覆盖公开 npu_demo 正向链路。
- 未发现跨文件非公开 API、ctx 能力探测、`object` 签名、非装饰器嵌套函数或敏感目录污染。

### 结论

- 结论：第二架构计划级终验通过。
- 最小阻断项：无。
- 流转建议：可进入 merge；merge 前必须确保本任务记录与代码 / spec / test 同批纳入候选 diff。

## 2026-05-20 23:35 CST 李白 merge 收口记录

时间：2026-05-20 23:35 CST
经办人：李白
任务：T-20260520-b5abd965 / merge
任务目标：合入 `npu_demo_pipeline_memory_plan_before_buffer_hoist` 已通过双架构终验的候选 diff，并确保任务记录与代码 / spec / test 同批进入主线。

### 合并前同步与范围核对

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-pipeline-memory-plan-before-buffer-hoist`。
- 分支：`task/npu-demo-pipeline-memory-plan-before-buffer-hoist`。
- 已执行：`git fetch --prune origin`。
- 同步基线：`HEAD=origin/main=578a9f6f3d122ed27fb1475ac9134d83db5a8062`，`ahead/behind=0/0`。
- 主仓 `/home/lfr/kernelcode_generate` 合并前状态 clean，无需要覆盖的本地改动。
- 候选文件核对为 4 个，任务记录与业务 / spec / test 同批纳入：
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `agents/codex-multi-agents/log/task_records/2026/21/20260520-npu-demo-pipeline-memory-plan-before-buffer-hoist.md`
- 本计划不把 `expectation` 列为必过合同资产，merge 记录不将 `expectation` 写作通过依据。

### merge 复核验证

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -ra`：exit=0，`8 passed, 1 warning`。
- 9 个 kernel demo 复核：
  - `kernel/matmul/inputs_static_tile_static.py`：exit=0，absent / present `max_abs_diff=3.4332275390625e-05`。
  - `kernel/matmul/inputs_static_tile_dynamic.py`：exit=0，absent / present `max_abs_diff=3.0517578125e-05`。
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit=0，absent / present `max_abs_diff=3.0517578125e-05`。
  - `kernel/conv2d/inputs_static_tile_static.py`：首轮循环运行出现一次 `Segmentation fault (core dumped)`；未改代码，单项重跑 exit=0，absent / present `max_abs_diff=4.1961669921875e-05`。
  - `kernel/conv2d/inputs_static_tile_dynamic.py`：exit=0，absent / present `max_abs_diff=3.814697265625e-05`。
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py`：exit=0，absent / present `max_abs_diff=4.57763671875e-05`。
  - `kernel/flash_attention/inputs_static_tile_static.py`：exit=0，`max_abs_diff=1.837313175201416e-05`。
  - `kernel/flash_attention/inputs_static_tile_dynamic.py`：exit=0，`max_abs_diff=1.1898577213287354e-05`。
  - `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：exit=0，`max_abs_diff=9.715557098388672e-06`。
- dump marker 复核：`kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel` 共 25 段；`cse_count=3`；`canonicalize_count=4`；post-pool tail 为 `memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。
- 静态扫描新增行：`hasattr/getattr/callable(getattr)`、跨文件私有 import、`object` 签名、非装饰器嵌套函数均无命中。

### 冲突与风险

- 冲突处理：未发生冲突。
- 敏感目录：`expectation/`、`.skills/`、`agents/standard/**` 无 tracked / staged / untracked / ignored 候选改动。
- 剩余风险：`kernel/conv2d/inputs_static_tile_static.py` 在首轮 demo 循环中出现一次进程级 segfault，随后单项重跑通过；本轮未修改代码，按真实过程记录，后续若复现需单列运行稳定性专项。

### 结论

- 结论：merge 前核对通过，可合入主线。
- 最小阻断项：无。

## 2026-05-20 13:59 +0800 大闸蟹架构终验记录

时间：2026-05-20 13:59 +0800
经办人：大闸蟹
任务：T-20260520-b5abd965 / npu_demo_pipeline_memory_plan_before_buffer_hoist
任务目标：按计划终验 `npu-demo-lowering` pipeline 顺序调整：两段 `MemoryPlanPass(insert_free=True, fold=False)` 前移到对应 `SymbolBufferHoistPass` 前；只删除 memory-pool 后那一次 `CommonSubexpressionElimination`；保留前三段 CSE 与 memory-pool 后 `CanonicalizePass`；核对 spec / 实现 / pytest / dump marker / 9 个 kernel demo / 敏感目录空 diff。

### 验证基线与执行目录

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-pipeline-memory-plan-before-buffer-hoist`。
- 已执行 `git fetch origin --prune`。
- `HEAD=578a9f6f3d122ed27fb1475ac9134d83db5a8062`
- `origin/main=578a9f6f3d122ed27fb1475ac9134d83db5a8062`
- `merge-base=578a9f6f3d122ed27fb1475ac9134d83db5a8062`
- `ahead/behind=0/0`
- 候选 diff 限定在 `kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py` 与本任务记录；未发现主线覆盖风险。

### 终验复核

- 公开 API：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 签名、pipeline name、pipeline option、registry 名称和公开错误语义均未改变；本轮只改变用户已确认的公开 pipeline 固定顺序。
- pipeline 顺序：实现、spec 与 pytest 均锁定两段 `memory-plan -> symbol-buffer-hoist`；memory-pool 后仅 `canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`；前三段 CSE 保留，memory-pool 后 CSE 已删除。
- expectation：本计划明确不新增、不修改、不要求运行任何 expectation；本次终验不把 expectation 作为通过依据。

### 验证

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -ra`：exit=0，`8 passed, 1 warning`。
- 9 个 kernel demo 均 exit=0：
  - `kernel/matmul/inputs_static_tile_static.py`：absent / present `max_abs_diff=3.4332275390625e-05`。
  - `kernel/matmul/inputs_static_tile_dynamic.py`：absent / present `max_abs_diff=3.0517578125e-05`。
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py`：absent / present `max_abs_diff=3.0517578125e-05`。
  - `kernel/conv2d/inputs_static_tile_static.py`：absent / present `max_abs_diff=4.1961669921875e-05`。
  - `kernel/conv2d/inputs_static_tile_dynamic.py`：absent / present `max_abs_diff=3.814697265625e-05`。
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py`：absent / present `max_abs_diff=4.57763671875e-05`。
  - `kernel/flash_attention/inputs_static_tile_static.py`：`max_abs_diff=1.837313175201416e-05`。
  - `kernel/flash_attention/inputs_static_tile_dynamic.py`：`max_abs_diff=1.1898577213287354e-05`。
  - `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：`max_abs_diff=9.715557098388672e-06`。
- dump marker 复核：`kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel` 共 25 段；`cse_count=3`；memory-pool 后 tail 为 `memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- `git diff --check`：exit=0；本任务记录 untracked 文件 diff check 无 whitespace 输出。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。
- 静态扫描 `hasattr/getattr/callable(getattr)`、跨文件私有 import、`object` 签名和非装饰器嵌套函数新增行：无命中。
- 运行 demo 后出现的 `.pytest_cache` 与 `kernel/dump/**` 均为 ignored 运行产物；`git status --short --untracked-files=all` 未显示新的 tracked / untracked 候选文件。

### 自检

- 计划完成态：spec、pipeline builder、pipeline pytest、dump marker 断言和 9 个 kernel demo 均已按计划闭合。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/**` 候选 diff 为空。
- 测试有效性：pipeline order 测试锁定三段 CSE、四段 canonicalize、两段 `memory-plan -> symbol-buffer-hoist`；真实 dump 锁定 memory-pool 后无 CSE 与 arch / attach 相对顺序；9 个 demo 覆盖 matmul、conv2d、flash_attention 正向链路。
- 未发现公开 API 越界、跨文件非公开 API 调用、测试直连非公开 helper、ctx 能力探测或未归档静态扫描命中。

### 结论

- 结论：架构终验通过。
- 最小阻断项：无。
- 流转建议：大闸蟹侧计划级终验已完成；merge 前仍需确保本任务记录与代码 / spec / test 同批纳入候选 diff。

## 2026-05-20 13:59 守护最好的爱莉希雅第二架构终验最终索引

- 详细终验记录见本文件上方 `2026-05-20 13:59 第二架构计划级终验记录`。
- 终验基线：`HEAD=origin/main=merge-base=578a9f6f3d122ed27fb1475ac9134d83db5a8062`，`ahead/behind=0/0`。
- 关键验证：`py_compile` exit=0；pipeline pytest `8 passed, 1 warning`；9 个 kernel demo 全部 exit=0；dump marker 共 25 段，`cse_count=3`，post-pool tail 为 `memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`；`git diff --check` 通过；`expectation/`、`.skills/`、`agents/standard` tracked / cached / untracked / ignored 均为空。
- expectation 口径：本计划不把 expectation 列为必过资产，本次未作为通过依据。
- 结论：第二架构计划级终验通过。
- 最小阻断项：无。
- 流转建议：可进入 merge；merge 前必须确保本任务记录与代码 / spec / test 同批纳入候选 diff。
