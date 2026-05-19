# T-20260520-dabe6d4b / npu_demo_late_arch_context_cleanup

## 2026-05-20 管理员下发前置记录

- 任务 ID：`T-20260520-dabe6d4b`
- 经办人：神秘人
- 计划书：`ARCHITECTURE/plan/npu_demo_late_arch_context_cleanup_green_plan.md`
- 任务目标：按计划完成旧 `kernel_gen/context.py` 删除、`ArchParallelizePass.apply(...)` 支持 `symbol.for` 前 `ArchGetDynamicMemoryOp` / `DmaViewOp` / `DmaReshapeOp` setup 前缀、`npu-demo-lowering` pipeline 重排、`spec` / 实现 / `pytest` / 9 个 kernel demo / 静态扫描 / 敏感目录与任务记录同批验收闭环。
- latest main：`HEAD=origin/main=merge-base=8a73d06b37ab9417d5b41b397f70b752395c8787`，`ahead/behind=0/0`。
- worktree：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-late-arch-context-cleanup`
- branch：`task/npu-demo-late-arch-context-cleanup`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/21/20260520-npu-demo-late-arch-context-cleanup.md`
- 当前指派：`金铲铲大作战`

### 并行 / 依赖判断

- 当前 TODO 只有 `T-20260520-e0fbce33` 处于 review，且计划范围不重叠，可并行下发。
- 本计划不依赖当前 review 任务结束即可下发。
- 后合入者需基于 latest main 复跑 pipeline 顺序、9 个 kernel demo、相关 pytest 与敏感目录 gate。

### 禁止修改面与合同口径

- `expectation/`、`.skills/`、`agents/standard/**` 必须空 diff。
- execute / review / admin / merge 不得复制、新建、同步、修改或删除 `expectation/`。
- 任务记录必须与 spec / 实现 / pytest 同批进入 review、终验和 merge。

## 2026-05-20 管理员下发记录

- 已按计划创建唯一计划级 execute `T-20260520-dabe6d4b` 并分发给 `金铲铲大作战`。

## 2026-05-20 execute 记录

### 执行前阅读 / 基线确认

- 已重新阅读个人 prompt、根 `AGENTS.md`、相关 `agents/standard` 规则与本计划正文。
- 已确认 worktree 基线与 latest main 现场一致，候选 diff 仅包含本任务相关实现、spec 与 test 修改。
- 已确认 `expectation/`、`.skills/`、`agents/standard/**` 在本任务中保持只读，候选 diff 为空。

### 实现修改

- 删除旧兼容桥接文件 `kernel_gen/context.py`。
- `spec/core/context.md` 明确旧 `kernel_gen.context` 不再作为公开导入路径。
- `test/core/test_context.py` 新增：
  - `build_default_context()` 正向可用；
  - 旧 `kernel_gen.context` 通过独立 Python 进程导入失败。
- `kernel_gen/passes/arch_parallelize.py` 扩展顶层 loop 前缀校验：
  - 允许 `ArchGetDynamicMemoryOp`、`DmaViewOp`、`DmaReshapeOp` 作为 memory-pool 生成的公开 setup 前缀；
  - 仅允许这些 prefix 依赖函数参数、纯 symbol setup 或更早允许 setup；
  - 仍拒绝 loop 后同级 setup、多个顶层 loop、loop-carried、multi-block、非 void return 与副作用/未知顶层 op。
- `kernel_gen/passes/pipeline/npu_demo_lowering.py` 重排为计划固定顺序：
  - 每个 `CommonSubexpressionElimination` 后显式跟 `xdsl.transforms.canonicalize.CanonicalizePass`；
  - 保留两次 `MemoryPlanPass(insert_free=True, fold=False)`；
  - 删除早期 `AttachArchInformationPass`；
  - 将 `ArchParallelizePass` 移至 `memory-pool -> cse -> canonicalize` 后、`AttachArchInformationPass` 前；
  - 保持 `MultiBufferPass` 不接入本 pipeline。
- `spec/pass/arch_parallelize.md` 与 `spec/pass/pipeline/npu_demo_lowering.md` 同步公开顺序、验证边界与测试矩阵。
- `test/passes/test_arch_parallelize.py` 增加：
  - memory-pool 前缀正例；
  - memory-pool setup 位于 loop 后的负例。
- `test/passes/pipeline/test_npu_demo_lowering.py` 同步新顺序、两次 `memory-plan`、四次 `cse + canonicalize`、唯一 late attach、dump marker 与 25 阶段顺序断言。

### 自检

- 已确认本轮未引入 `expectation/`、`.skills/`、`agents/standard/**` 候选 diff。
- 已确认未新增公开 API、未新增 pipeline option、未把 `CanonicalizePass` 写入本仓 registry。
- 已确认 `ArchParallelizePass` 仅放宽到 memory-pool 生成的 `arch.get_dynamic_memory -> dma.view -> dma.reshape` 前缀，不放宽 loop 后同级 op、未知 op 或副作用 op。
- 已确认旧 `kernel_gen.context` 的测试改为独立 Python 进程验证，避免被测试包路径回接主仓旧文件误导。

### Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/arch_parallelize.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/core/test_context.py test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k npu_demo -ra` -> `exit=0`
- 9 个 kernel demo 通过：
  - `kernel/matmul/inputs_static_tile_static.py`
  - `kernel/matmul/inputs_static_tile_dynamic.py`
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - `kernel/conv2d/inputs_static_tile_static.py`
  - `kernel/conv2d/inputs_static_tile_dynamic.py`
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - `kernel/flash_attention/inputs_static_tile_static.py`
  - `kernel/flash_attention/inputs_static_tile_dynamic.py`
  - `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
- 9 个 demo 的 dump 校验结果：
  - `kernel/dump/matmul/inputs_dynamic_tile_dynamic`、`kernel/dump/matmul/inputs_static_tile_dynamic`、`kernel/dump/conv2d/inputs_dynamic_tile_dynamic` 含完整 25 个阶段 marker；
  - `kernel/dump/matmul/inputs_static_tile_static_absent_bias`、`kernel/dump/matmul/inputs_static_tile_static_present_bias`、`kernel/dump/conv2d/inputs_static_tile_static_absent_bias`、`kernel/dump/conv2d/inputs_static_tile_static_present_bias`、`kernel/dump/conv2d/inputs_static_tile_dynamic_absent_bias`、`kernel/dump/conv2d/inputs_static_tile_dynamic_present_bias`、`kernel/dump/flash_attention/*` 仅保留 `source.cpp`，无额外未预期 dump 文件。

### 静态扫描 / 敏感目录

- `git diff --check` -> `exit=0`
- `rg -n "kernel_gen\\.context\\b|from kernel_gen import context|import kernel_gen\\.context" kernel_gen test expectation --glob '!kernel_gen/context.py'` -> 无命中
- `rg -n "build_registered_pass\\(\\\"canonicalize\\\"|register.*canonicalize" kernel_gen spec test` -> 无命中
- `rg -n "pytest\\.mark\\.(skip|skipif|xfail)|collect_ignore|pytest_ignore_collect" test/core/test_context.py test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py` -> 无命中
- `git diff --name-only -- expectation .skills agents/standard` -> 空
- `git diff --cached --name-only -- expectation .skills agents/standard` -> 空
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 空

### 结论

- `kernel_gen/context.py` 已删除，旧桥接路径测试已收口为失败负例。
- `npu-demo-lowering` pipeline 已按计划固定顺序重排，并保留 `CanonicalizePass` 仅作为 pipeline 内部 xDSL pass。
- `ArchParallelizePass` 已扩展支持 memory-pool 生成的 loop-prefix setup 前缀，且未扩大到其它顶层副作用 op。
- 本轮目标 pytest、9 个 kernel demo、静态扫描与敏感目录门禁均已通过，可进入 `review`。

## 2026-05-20 review 记录

时间：2026-05-20 03:54 CST
经办人：提莫炖蘑菇
任务：T-20260520-dabe6d4b / npu_demo_late_arch_context_cleanup
任务目标：复审旧 `kernel_gen/context.py` 删除、`ArchParallelizePass` memory-pool setup 前缀公开合同、`npu-demo-lowering` pipeline 重排、spec / 实现 / pytest / 9 个 kernel demo / dump marker / 静态扫描 / 敏感目录空 diff 与任务记录
改动：已只读核对 worktree `/home/lfr/kernelcode_generate/wt-20260520-npu-demo-late-arch-context-cleanup` 与 `origin/main`，确认 `HEAD=origin/main=merge-base=8a73d06b37ab9417d5b41b397f70b752395c8787`，无冲突覆盖风险；被审 diff 包含 `kernel_gen/context.py` 删除、`kernel_gen/passes/arch_parallelize.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/core/context.md`、`spec/pass/arch_parallelize.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/core/test_context.py`、`test/passes/test_arch_parallelize.py`、`test/passes/pipeline/test_npu_demo_lowering.py`。发现 1 条最小需改项：`test/core/test_context.py:23` 新增了未使用的 `pytest` 导入，属于可直接收口的可维护性返工点。
验证：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/arch_parallelize.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/core/test_context.py test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py` -> `exit=0`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py` -> `2 passed, 2 warnings, exit=0`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py` -> `18 passed, 1 warning, exit=0`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `8 passed, 1 warning, exit=0`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k npu_demo -ra` -> `3 passed, 37 deselected, 2 warnings, exit=0`；9 个 kernel demo 全部通过；`git diff --check` -> `exit=0`；旧 `kernel_gen.context` 消费者扫描、`pytest.mark.skip/xfail` 扫描与 canonicalize registry 扫描均无命中；`git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` 均为空。
自检：已逐项读取实际 diff，而非仅看执行摘要；已核对公开 API 变更无新增、`expectation/`、`.skills/`、`agents/standard/**` 无候选改动；已确认旧 `kernel_gen.context` 删除只在 `spec/core/context.md` 保留非公开说明、测试负例通过独立 Python 进程锁定；已确认 `npu-demo-lowering` 新顺序、两次 `MemoryPlanPass` 与 xDSL `CanonicalizePass` 仅在 pipeline 内使用；已确认 9 个 kernel demo 与静态扫描门禁通过。当前仍有可执行返工项，不能写 `通过`。
结论：最小需改项
发现：
- 中 test/core/test_context.py:23 未使用的 `pytest` 导入，增加噪音且与新增测试无关。建议删除该导入后重跑 `py_compile`、`pytest -q test/core/test_context.py` 和 `git diff --check`，确认无回归。

## 2026-05-20 execute 返工记录

时间：2026-05-20 03:58 CST
经办人：金铲铲大作战
任务：T-20260520-dabe6d4b / npu_demo_late_arch_context_cleanup
任务目标：删除 `test/core/test_context.py` 中未使用的 `pytest` 导入，并复跑点名验证。
改动：按 review 最小需改项，仅从 `test/core/test_context.py` 删除未使用的 `pytest` 导入；未改动 `expectation/`、`.skills/`、`agents/standard/**`，未扩大公开 API 或 pipeline 行为。
验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile test/core/test_context.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py` -> `2 passed, 2 warnings, exit=0`
- `git diff --check` -> `exit=0`
- `git diff --name-only -- expectation .skills agents/standard && git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 无输出，敏感目录空 diff。
Diff 反推自测：本轮 diff 仅涉及 `test/core/test_context.py` 的导入清理；已用 `py_compile` 锁定语法、用 `pytest -q test/core/test_context.py` 锁定 context 公开行为与旧路径负例未回退、用 `git diff --check` 锁定格式。
自检：已确认返工范围只清理未使用导入；未新增测试直连非公开 API，未使用跨文件非公开 helper，未修改合同资产或标准目录；测试断言仍覆盖 `build_default_context()` 正向解析与旧 `kernel_gen.context` 负向导入边界。
结论：返工闭合，可回到 `review`。

## 2026-05-20 review 复审记录

时间：2026-05-20 04:08 CST
经办人：不要啊教练
任务：T-20260520-dabe6d4b / npu_demo_late_arch_context_cleanup
任务目标：复审返工项 `test/core/test_context.py` 删除未使用 `pytest` 导入，并核对点名验证、敏感目录空 diff 与任务记录。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-late-arch-context-cleanup`
- 已执行 `git fetch origin --prune`。
- `HEAD=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `origin/main=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `merge-base=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `ahead/behind=0/0`
- 同步结果：worktree 与最新 `origin/main` 对齐，未发现冲突或覆盖任务 diff 风险。

被审 diff：
- `kernel_gen/context.py` 删除
- `kernel_gen/passes/arch_parallelize.py`
- `kernel_gen/passes/pipeline/npu_demo_lowering.py`
- `spec/core/context.md`
- `spec/pass/arch_parallelize.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `test/core/test_context.py`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/passes/test_arch_parallelize.py`
- 本轮复审重点：`test/core/test_context.py` 未使用 `pytest` 导入返工。

真实审查：
- `test/core/test_context.py` 已删除 `pytest` 导入，`rg -n '^import pytest|pytest\.' test/core/test_context.py` 无命中。
- `test/core/test_context.py` 仍保留 `build_default_context()` 正向解析与旧 `kernel_gen.context` 独立进程负向导入测试，返工未削弱原测试边界。
- 旧路径消费者扫描 `rg -n "kernel_gen\.context\b|from kernel_gen import context|import kernel_gen\.context" kernel_gen test expectation --glob '!kernel_gen/context.py'` 无命中。
- `pytest.mark.skip/skipif/xfail` 与 collect ignore 扫描在 `test/core/test_context.py` 无命中。
- `expectation/`、`.skills`、`agents/standard` tracked / cached / untracked / ignored 均为空。

Diff 反推审查：
- 本轮返工实际只清理 `test/core/test_context.py` 的未使用导入，反推测试为 `py_compile` 与 `pytest -q test/core/test_context.py`。
- `pytest -q test/core/test_context.py` 会覆盖 context 正向公开入口和旧路径负向导入；若误删必要 import 或破坏旧路径负例会失败。
- `git diff --check` 覆盖格式与空白问题。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile test/core/test_context.py` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py` -> `2 passed, 2 warnings`，exit 0。
- `git diff --check` -> exit 0。
- `git diff --name-only -- expectation .skills agents/standard` -> 空。
- `git diff --cached --name-only -- expectation .skills agents/standard` -> 空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard` -> 空。
- `git status --short --ignored -- expectation .skills agents/standard` -> 空。

发现：
- 无新增阻断项。
- 上一轮 review 的未使用 `pytest` 导入问题已收口。

自检：
- 已先同步最新主线现场并记录基线。
- 已读取实际 diff、计划和前序记录，未只依赖执行摘要。
- 已确认返工未触碰 `expectation/`、`.skills`、`agents/standard`。
- 已确认本轮未新增公开 API、未跨文件调用非公开 helper、未使用 ctx 能力探测、未新增非装饰器嵌套函数。
- 已按实际 diff 反推审查，且 expectation 未被用作 diff 反推测试。

结论：通过。
下一步：本任务为计划级任务，review 通过后应由管理员接架构复核 / 终验，不直接 merge。

## 2026-05-20 架构终验记录

时间：2026-05-20 04:16 CST
经办人：大闸蟹
任务：T-20260520-dabe6d4b / npu_demo_late_arch_context_cleanup
任务目标：终验旧 `kernel_gen/context.py` 删除、`ArchParallelizePass` memory-pool setup 前缀公开合同、`npu-demo-lowering` pipeline 重排、`spec` / 实现 / `pytest` / 9 个 kernel demo / 静态扫描 / 敏感目录空 diff 与任务记录。

验证基线：
- `HEAD=origin/main=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `merge-base=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `ahead/behind=0/0`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-late-arch-context-cleanup`

合同验收摘要：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/arch_parallelize.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/core/test_context.py test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py` -> `2 passed, 2 warnings`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py` -> `18 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `8 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k npu_demo -ra` -> `3 passed, 37 deselected, 2 warnings`
- 9 个 kernel demo 全部通过
- `git diff --check` -> `exit=0`
- 旧 `kernel_gen.context` 消费者扫描、`pytest.mark.skip/skipif/xfail` 扫描、`canonicalize` registry 扫描均无命中
- `expectation/.skills/agents/standard` tracked / cached / untracked / ignored 均为空

终验结论：通过。
最小阻断项：无。
补充说明：本计划不使用 `expectation/` 作为合同资产，已按用户口径完成删除旧兼容桥接、pipeline 重排、公开 `ArchParallelizePass` 合同扩展与敏感目录门禁闭环。

## 2026-05-20 第二架构终验记录

时间：2026-05-20 04:19 CST
经办人：守护最好的爱莉希雅
任务：T-20260520-dabe6d4b / npu_demo_late_arch_context_cleanup
任务目标：对旧 `kernel_gen/context.py` 删除、`ArchParallelizePass` memory-pool setup 前缀公开合同、`npu-demo-lowering` pipeline 重排、`spec` / 实现 / `pytest` / 9 个 kernel demo / 静态扫描 / 敏感目录空 diff 与任务记录做第二架构终验。

验证基线：
- `HEAD=origin/main=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `merge-base=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `ahead/behind=0/0`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-late-arch-context-cleanup`

合同验收摘要：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/arch_parallelize.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/core/test_context.py test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py` -> `2 passed, 2 warnings`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py` -> `18 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `8 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k npu_demo -ra` -> `3 passed, 37 deselected, 2 warnings`
- 9 个 kernel demo 全部通过：
  - `kernel/matmul/inputs_static_tile_static.py`
  - `kernel/matmul/inputs_static_tile_dynamic.py`
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - `kernel/conv2d/inputs_static_tile_static.py`
  - `kernel/conv2d/inputs_static_tile_dynamic.py`
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - `kernel/flash_attention/inputs_static_tile_static.py`
  - `kernel/flash_attention/inputs_static_tile_dynamic.py`
  - `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
- `git diff --check` -> `exit=0`
- 旧 `kernel_gen.context` 消费者扫描无命中；`pytest.mark.skip/skipif/xfail` 扫描无命中；`build_registered_pass("canonicalize", ...)` / `register.*canonicalize` 扫描无命中
- `expectation/.skills/agents/standard` tracked / cached / untracked / ignored 均为空

自检：
- 已先核对最新同步现场、`fetch` / 对齐结果与候选 diff，无覆盖风险。
- 已逐项读取实际 diff、计划正文、前序执行 / review 记录，而不是只看执行摘要。
- 已核对公开 `API` 变更无新增、`expectation/`、`.skills/`、`agents/standard/**` 无候选改动。
- 已核对旧 `kernel_gen.context` 删除、`ArchParallelizePass` setup 前缀扩展、pipeline 顺序重排、`CanonicalizePass` 仅作 pipeline 内部 xDSL pass 的边界。
- 已按实际 diff 反推测试，且本轮没有把 `expectation` 当作 diff 反推测试。

结论：通过。
最小阻断项：无。
通过摘要：本计划已满足当前公开合同、计划顺序、合同验收与敏感目录门禁，可进入 merge / 归档流转。

---

时间：2026-05-20 04:17 CST
经办人：李白
阶段：merge 收口

合并前同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260520-npu-demo-late-arch-context-cleanup`
- 任务分支：`task/npu-demo-late-arch-context-cleanup`
- 已执行 `git fetch --prune origin`。
- `HEAD=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `origin/main=8a73d06b37ab9417d5b41b397f70b752395c8787`
- `ahead/behind=0/0`
- 主仓 `/home/lfr/kernelcode_generate` 当前为 clean，本次合并不存在覆盖主仓本地改动风险。

本次候选同批范围：
- `kernel_gen/context.py` 删除。
- `kernel_gen/passes/arch_parallelize.py`
- `kernel_gen/passes/pipeline/npu_demo_lowering.py`
- `spec/core/context.md`
- `spec/pass/arch_parallelize.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `test/core/test_context.py`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/passes/test_arch_parallelize.py`
- `agents/codex-multi-agents/log/task_records/2026/21/20260520-npu-demo-late-arch-context-cleanup.md`

merge 前真实复核：
- 候选 diff 与 review、返工复审、双架构终验记录一致；任务记录当前为未跟踪文件，已确认必须与代码 / spec / test 同批纳入提交，不得先合代码后补记录。
- 本计划不使用 `expectation/` 作为合同资产；merge 记录不把 expectation 写作通过依据。
- `expectation/`、`.skills/`、`agents/standard/` 无普通 diff、staged diff、未跟踪或 ignored 输出。
- 旧 `kernel_gen.context` 消费者扫描、`pytest.mark.skip/skipif/xfail` 扫描和 `canonicalize` registry 扫描均无命中。

merge 前复跑命令：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/arch_parallelize.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/core/test_context.py test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py`：exit `0`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py`：`2 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py`：`18 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k npu_demo -ra`：`3 passed, 37 deselected, 2 warnings`。
- 9 个 kernel demo 逐条复跑，全部 exit `0`：`kernel/matmul/inputs_static_tile_static.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/conv2d/inputs_static_tile_static.py`、`kernel/conv2d/inputs_static_tile_dynamic.py`、`kernel/conv2d/inputs_dynamic_tile_dynamic.py`、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`。
- `rg -n "kernel_gen\\.context\\b|from kernel_gen import context|import kernel_gen\\.context" kernel_gen test expectation --glob '!kernel_gen/context.py'`：无命中。
- `rg -n "pytest\\.mark\\.(skip|skipif|xfail)|collect_ignore" test/core/test_context.py test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py`：无命中。
- `rg -n 'build_registered_pass\\("canonicalize"|register.*canonicalize' kernel_gen spec test`：无命中。
- `git diff --check`：exit `0`。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。

Diff 反推自测 / 审查继承：
- `test/core/test_context.py` 锁定公开 `build_default_context()` 与旧 `kernel_gen.context` 负向导入边界。
- `test/passes/test_arch_parallelize.py` 锁定 memory-pool setup 前缀公开合同。
- `test/passes/pipeline/test_npu_demo_lowering.py`、`test/tools/test_dsl_run.py -k npu_demo` 与 9 个 kernel demo 锁定 npu-demo pipeline 重排后的真实主链路。
- 本轮 merge 前重新复跑上述直接相关 gate，未发现 latest main 下的失效。

merge 结论：
- 可合并。
- 记录文件已与业务 / spec / test 候选同批纳入提交范围。
- 最小阻断项：无。
