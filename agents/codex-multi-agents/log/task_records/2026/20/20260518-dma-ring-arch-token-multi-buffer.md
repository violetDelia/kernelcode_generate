# T-20260518-e79bde42 dma ring / arch token / multi buffer

时间：2026-05-18 18:11
经办人：大闸蟹
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：裁定当前 execute 任务的流程阻断，明确记录缺失时的继续方式。
改动：核对 worktree `/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`，确认实现/spec/test diff 已存在，但任务记录文件此前缺失；按仓库规则，记录缺失不得进入 review。
验证：`test -f /home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/agents/codex-multi-agents/log/task_records/2026/20/20260518-dma-ring-arch-token-multi-buffer.md && echo exists || echo missing` -> `missing`；`git -C /home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer status --short --branch --untracked-files=all` -> 仅见实现/spec/test 候选 diff，记录文件未存在。
自检：当前不能 review；记录缺失属于流程阻断，不是实现阻断。执行链应先补最小记录，再继续 review / 终验。
结论：阻塞。最小动作是由现执行人先补齐该任务记录的最小可审字段后再继续；若补齐后仍不及时推进，再由管理员暂停该 execute 并决定是否换执行承接。

时间：2026-05-18 19:30
经办人：大闸蟹
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：对暂停后的接续方式作架构裁定。
改动：管理员确认任务已按 18:11 裁定暂停；现场仍为 execute / 金铲铲大作战已产生实现、spec、test dirty diff，但本记录只有大闸蟹流程阻塞段，没有执行人的最小执行记录；暂停前未改代码、未跑技术验收。
验证：读取本记录尾部，确认仅存在 18:11 大闸蟹流程阻塞段；未读取或评价当前 dirty diff 的技术正确性，本次只裁定流程接续方式。
自检：继续要求原执行人补记录已经在 18:11 给过明确口径，但仍未形成可审执行记录；若继续等待，会让 review 阶段缺少执行前阅读、最小功能闭环、Diff 反推自测、自检和验收证据。现有 dirty diff 不能直接进入 review，也不能由 review 代补执行记录。
结论：选择 B。请管理员换 execute 承接；接手者必须先只读梳理现有 dirty diff 并写 takeover 记录，然后才能决定保留、修正或重做实现。takeover 记录至少包含：最新同步现场、当前 dirty diff 文件清单、哪些改动继承为未验证候选、计划书 S1-S6 覆盖矩阵、未运行技术验收说明、下一步 Diff 反推自测与主仓只读 expectation / full expectation 门禁计划、`expectation/.skills/agents/standard` 空 diff核对。接手者不得把金铲铲未记录的工作写成已验证结论；补齐 takeover 记录前不得恢复 review。

### 2026-05-18 20:46 execute takeover

时间：2026-05-18 20:46 +0800
经办人：睡觉小分队
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：按管理员换执行承接要求，只读梳理当前 dirty diff，补齐 takeover 记录，再决定保留、修正或重做实现；本轮不进入 review，不修改 expectation。

执行前阅读记录：
- 已重新读取当前角色提示词、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读取共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_ring_arch_token_multi_buffer_green_plan.md`，并确认当前可见正文只包含 S1-S4 小任务卡；用户/管理员口头分发里出现的 S5-S6 不在该计划正文内，后续必须按计划正文实际范围记录，不得虚写覆盖。
- 已读取前序任务记录中大闸蟹 18:11 / 19:30 的流程阻塞与接续裁定，以及本任务链当前只读 takeover 要求。
- 已核对 TODO，任务行仍为 `T-20260518-e79bde42`，状态尚未流转离开当前 execute 链。

同步基线：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`
- 已执行 `git fetch origin --prune`
- `HEAD=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`
- `origin/main=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- `git merge-base HEAD origin/main=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`

当前 dirty diff 文件清单：
- tracked modified：
  - `kernel_gen/dialect/arch.py`
  - `kernel_gen/dialect/dma.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/__init__.py`
  - `kernel_gen/passes/__init__.py`
  - `kernel_gen/passes/dma_memory_hierarchy.py`
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/template_name_default_constraints.py`
  - `spec/dialect/arch.md`
  - `spec/dialect/dma.md`
  - `spec/pass/lowering/dma_memory_hierarchy/spec.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/pass/template_name_default_constraints.md`
  - `test/dialect/test_arch.py`
  - `test/dialect/test_dma.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_dma_memory_hierarchy.py`
  - `test/passes/test_registry.py`
  - `test/passes/test_template_name_constraints.py`
- untracked：
  - `agents/codex-multi-agents/log/task_records/2026/20/20260518-dma-ring-arch-token-multi-buffer.md`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`
  - `kernel_gen/passes/multi_buffer.py`
  - `spec/pass/multi_buffer.md`
  - `test/passes/test_multi_buffer.py`

继承为未验证候选的范围：
- `kernel_gen/dialect/arch.py`、`kernel_gen/dialect/dma.py`、`kernel_gen/passes/multi_buffer.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`kernel_gen/passes/registry.py`、`kernel_gen/passes/__init__.py`、`kernel_gen/passes/dma_memory_hierarchy.py` 以及对应 `spec` / `test` 全部作为未验证候选。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/__init__.py` 与新增 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 作为未验证候选。
- `spec/pass/template_name_default_constraints.md`、`spec/pass/lowering/dma_memory_hierarchy/spec.md`、`test/dialect/test_arch.py`、`test/dialect/test_dma.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/passes/test_dma_memory_hierarchy.py`、`test/passes/test_registry.py`、`test/passes/test_template_name_constraints.py` 均属未验证候选。

计划书 S1-S6 覆盖矩阵：
- S1：已见对应候选，`dma` / `arch` dialect ring/token 原语落点存在于 `kernel_gen/dialect/*`、`spec/dialect/*`、`test/dialect/*`。
- S2：已见对应候选，`multi-buffer` pass 落点存在于 `kernel_gen/passes/multi_buffer.py`、`spec/pass/multi_buffer.md`、`test/passes/test_multi_buffer.py`、registry 及 `__init__`。
- S3：已见对应候选，`npu-demo-lowering` pipeline 接入点落在 `kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md` 与相关 pipeline test。
- S4：已见对应候选，`spec/pass/registry.md`、`spec/pass/template_name_default_constraints.md`、`test/passes/test_registry.py`、`test/passes/test_template_name_constraints.py`、任务记录文件均在范围内。
- S5：当前共享计划正文未包含 S5 小任务卡，未能做覆盖判断；若后续需要 S5，请先由管理员补计划正文或另行确认。
- S6：当前共享计划正文未包含 S6 小任务卡，未能做覆盖判断；若后续需要 S6，请先由管理员补计划正文或另行确认。

未运行技术验收说明：
- 本轮仅完成只读 takeover，不改实现、不改测试、不改 expectation，也未运行技术验收命令。
- 原因：先按管理员要求补齐 takeover 记录，再决定保留、修正或重做实现，避免在未记录承接范围时直接进入 review。
- 风险：当前 dirty diff 仍未被技术验证，`multi-buffer` / `dma ring` / `arch token` 的语义正确性仍需后续 Diff 反推 pytest 与合同验收闭环证明。

下一步 Diff 反推自测与门禁计划：
- 先按实际 diff 反推 pytest 覆盖 `kernel_gen/dialect/arch.py`、`kernel_gen/dialect/dma.py`、`kernel_gen/passes/multi_buffer.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py` 和对应 `spec/test`。
- 合同验收只读运行主仓 `expectation.dialect.dma`、`expectation.dialect.arch` 与本计划正文要求的全量 expectation；`expectation` 仅作为合同资产，不纳入普通 diff。
- 任务 worktree 必须继续证明 `PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate` 时 `expectation.*` 来自主仓、`kernel_gen.*` 来自任务 worktree。
- 在候选 diff 中核对 `expectation/.skills/agents/standard` 仍为空；若出现任何 expectation 相关差异，必须立即停止并回报用户/架构师，不得自行清理或同步。

expectation/.skills/agents/standard 空 diff 核对：
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。

最小功能闭环（当前只读结论）：
- 目标闭环应是 `dma ring` + `arch token` 公开发明 + `multi-buffer` pass + `npu-demo-lowering` 接入 + kernel dump/e2e + 主仓只读 expectation 验收。
- 当前仅可确认改动面覆盖该闭环的实现/spec/test 入口，但尚未完成验证，不得写成已通过。

自检：
- 已核对任务记录、计划正文、基线、dirty diff、敏感目录空 diff 与后续门禁路径。
- 已发现计划正文与分发消息存在 S1-S6 / 实际 S1-S4 的口径差异，已显式记录，不按旧口径补假设。
- 当前未做技术验证，因此不能把任何实现正确性、测试通过性或合同验收结果写成既成结论。

结论：takeover 已完成，当前仍为未验证 execute 候选；下一步应先按实际 diff 做测试归因，再决定保留、修正或重做实现。

### 2026-05-18 21:44 execute 续跑与门禁定位

时间：2026-05-18 21:44 +0800
经办人：睡觉小分队
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：继续按实际 diff 做 Diff 反推自测，区分本任务候选问题与 clean main 既有 expectation 门禁红点，并决定是否可继续推进 review。

执行前阅读记录：
- 已复核本记录 takeover 段、计划正文 S1-S4、TODO 当前任务行与前序裁定。
- 已确认本轮未修改 expectation/.skills/agents/standard，候选 diff 仍为前述文件清单。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py` -> `158 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -vv` -> `4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv` -> `4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv` -> `8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation` -> 1200s 超时，日志推进到 `dsl-mlir_gen-dialect-symbol-get_stride-3`，未得到完成结论。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass` -> exit 1，clean main baseline 已存在 3 个失败家族：
  - `pass.attach_arch_information`：`launch_attrs` / `dynamic_memory_capacity` 断言找不到 `launch_block/launch_thread/launch_subthread/shared_memory_size` 的 expected `CHECK-NEXT`。
  - `pass.symbol_buffer_hoist`：`kernel_lifecycle`、`reshape_multi_loop`、`subview_multi_loop`、`view_multi_loop` 断言未命中。
  - `pass.symbol_loop_hoist`：`symbol_minmax` 断言未命中。

Diff 反推自测：
- 当前实现相关 pytest（`test/dialect/test_dma.py`、`test/dialect/test_arch.py`、`test/passes/test_multi_buffer.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/kernel/test_*_symbolic_memory_genkernel.py`）已通过，说明本轮新增 ring/token/multi-buffer 接入没有破坏这些公开入口。
- `python3 -m expectation.pass` 在 clean main baseline 已红，且失败家族集中在 `attach_arch_information`、`symbol_buffer_hoist`、`symbol_loop_hoist`，不在本轮新增 `dma ring / arch token / multi-buffer` 的直接覆盖面内。
- 当前只能得出“本任务候选未扩大上述 failure 家族”的保守结论；全量 expectation 门禁仍未闭合，需架构/用户裁定是否把这些既有红点视为本任务外阻断或另建专项。

自检：
- 接口：本轮未新增未确认公开 API；`MultiBufferPass` 与 `dma/arch` 新原语的公开列表已对应 spec/test。
- 边界：候选 diff 仍只包含 `kernel_gen/*`、`spec/*`、`test/*` 和任务记录，不含 `expectation/.skills/agents/standard`。
- 测试有效性：kernel demo 公开 pytest 与本任务相关 unit pytest 均可在实现坏掉时失败；但全量 expectation 门禁当前由 clean main 既有红点阻断。
- 兼容性：未使用 ctx 能力探测、未新增非装饰器嵌套函数、未跨文件调用非公开 helper。

结论：当前可以确认本任务候选未破坏 kernel demo / dialect / pass / registry 的直接公开 pytest，但 full expectation 在 clean main 上已存在外部红点；是否继续以该门禁强制阻断本计划，需要架构侧或用户裁定。

### 2026-05-18 21:52 execute 阻塞回报

时间：2026-05-18 21:52 +0800
经办人：睡觉小分队
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：把当前验证结果收口成可执行结论，明确是否能按计划进入 review。

改动：
- 本轮未新增代码改动；仅补充验证与阻塞判断。
- 已确认本任务候选的公开 pytest（`test/dialect/test_dma.py`、`test/dialect/test_arch.py`、`test/passes/test_multi_buffer.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`、`test/kernel/test_conv2d_symbolic_memory_genkernel.py`）均通过。
- 已确认 clean main 的 `python3 -m expectation.pass` 仍失败，失败家族集中在 `pass.attach_arch_information`、`pass.symbol_buffer_hoist`、`pass.symbol_loop_hoist`，与本轮新增 `dma ring / arch token / multi-buffer` 候选无直接重叠，但与计划正文要求的 full expectation 硬门禁冲突。

验证：
- `git diff --check` -> exit 0。
- `git diff --name-only -- expectation .skills agents/standard` / `git diff --cached --name-only -- expectation .skills agents/standard` / `git status --short --untracked-files=all -- expectation .skills agents/standard` / `git status --short --ignored -- expectation .skills agents/standard` -> 均为空。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py` -> `158 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -vv` -> `4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv` -> `4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv` -> `8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass` -> exit 1；clean main baseline 已红。

Diff 反推自测：
- 当前候选 diff 不扩大 `attach_arch_information`、`symbol_buffer_hoist`、`symbol_loop_hoist` 的 clean main 失败家族。
- 但由于计划正文要求 full expectation 必跑且必须通过，现阶段无法进入 review / 终验 / merge。

阻塞：
- `python3 -m expectation` 在 1200s 内仍未跑完，日志推进到 `dsl-mlir_gen-dialect-symbol-get_stride-3`；同时 clean main `python3 -m expectation.pass` 已明确失败。
- 这说明当前 full expectation 门禁无法仅凭本轮 execute 候选通过；需要架构师或用户裁定：这些既有 expectation 红点是否作为本计划外部背景、是否允许先按 kernel demo / dialect / pass 公开 pytest 进入 review，或是否需要另建专项先收口 `attach_arch_information`、`symbol_buffer_hoist`、`symbol_loop_hoist`。

自检：
- 接口：未新增未确认公开 API；`dma/arch/multi-buffer` 的 spec、实现与测试边界保持一致。
- 边界：候选 diff 和敏感目录检查继续为空，未接触 `expectation/.skills/agents/standard`。
- 风险：若不先裁定 full expectation 既有红点归属，贸然 `-next review` 会让审查目标与计划硬门禁不一致。

结论：当前 execute 继续阻塞，不应流转 review。请管理员/架构师先裁定 full expectation 既有红点的归属与是否另建专项；裁定前本任务仅保留为未验证候选。

### 2026-05-18 22:14 大闸蟹架构裁定：full expectation 基线红点

时间：2026-05-18 22:14 +0800
经办人：大闸蟹
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：裁定 clean main 既有 full expectation 红点是否作为本任务 review 前硬阻断。

裁定：
- `python3 -m expectation` / `python3 -m expectation.pass` 当前不能写成通过；该事实必须继续保留在记录里。
- 在以下条件同时满足时，clean main 已存在且未被本候选扩大的 `attach_arch_information`、`symbol_buffer_hoist`、`symbol_loop_hoist` 红点不再作为本任务进入 review 的硬阻断：
  1. 本任务直接门禁已通过并记录：相关 pytest、kernel demo pytest、`expectation.dialect.dma`、`expectation.dialect.arch`、`py_compile`、`git diff --check`。
  2. 敏感目录检查为空：`expectation/`、`.skills`、`agents/standard` tracked / cached / untracked / ignored 均无候选 diff。
  3. 记录中保留 clean main 基线证据：失败来自 `PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass`，且失败家族为 `pass.attach_arch_information`、`pass.symbol_buffer_hoist`、`pass.symbol_loop_hoist`。
  4. 候选 diff 未修改上述失败家族的 expectation 本体，且未改对应 pass / pipeline 的相关实现导致失败家族扩大；review 必须复核这一点。
  5. 后续 review 不得写“full expectation 通过”，只能写“full expectation 存在 clean main 外部红点，本候选未扩大，按架构裁定不阻断本轮 review”。

影响：
- 本任务可按直接门禁进入 review；review 需要重点复核本裁定的 5 个条件，尤其是失败家族与候选 diff 的无关性。
- 若 review 或后续复验发现新增失败、失败家族扩大、候选触碰 `attach_arch_information` / `symbol_buffer_hoist` / `symbol_loop_hoist` 相关实现并与红点可能相关，或者 `expectation.dialect.dma` / `expectation.dialect.arch` 回退失败，则本裁定立即失效，任务退回 execute。
- `python3 -m expectation` 1200s 未完成只能记录为 full expectation 未闭合，不能当作通过依据。
- 建议管理员另建或挂起专项收口 clean main 的 `expectation.pass` 红点；该专项不作为本任务 review 前置，但在终验 / merge 记录中仍需明确 full expectation 外部红点口径，不能隐去。

验证：
- 已读取计划正文中 S3 / S4 对 full expectation 的硬门禁要求。
- 已读取本记录中睡觉小分队 21:44 / 21:52 的执行结果：本任务相关 pytest 与 `expectation.dialect.dma`、`expectation.dialect.arch` 通过，clean main `expectation.pass` 已存在三类失败家族。
- 本次未复跑技术命令；本裁定基于执行记录中的已记录现场，review 仍需按最新现场复核。

自检：
- 该裁定没有放宽本任务直接合同：`dma` / `arch` / `multi-buffer` / `npu-demo-lowering` 相关 pytest 与单项 expectation 仍必须通过。
- 该裁定没有允许把 full expectation 写成通过，也没有授权任何角色修改 `expectation/`。
- 该裁定仅处理 review 前是否可继续；终验 / merge 若遇到新的 full expectation 失败或失败范围变化，必须重新请求架构裁定。

结论：允许本任务在记录外部红点并满足上述条件后进入 review；full expectation 既有红点不作为本任务 review 前硬阻断，但必须作为外部红点在 review、终验和 merge 记录中持续显式保留。

### 2026-05-18 22:20 execute 收口并准备流转 review

时间：2026-05-18 22:20 +0800
经办人：睡觉小分队
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：按大闸蟹 22:14 架构裁定，在直接门禁通过、敏感目录空 diff、clean main full expectation 外部红点已记录且候选未扩大失败家族的前提下，完成 execute 收口并流转 review。

改动：
- 本段不新增实现改动，仅补最终 execute 收口记录。
- 现有候选仍为 dma ring type/op、arch token/sign/wait type/op、`MultiBufferPass(memory_stage=3)`、`npu-demo-lowering` 接入、相关 spec / pytest / 任务记录。
- `full expectation` 不写成通过；保持记录为 clean main 外部红点：`attach_arch_information` / `symbol_buffer_hoist` / `symbol_loop_hoist`。

最终验证摘要：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py`：`158 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation`：1200s 未完成，不能写为通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass`：clean main exit 1，失败家族为 `pass.attach_arch_information`、`pass.symbol_buffer_hoist`、`pass.symbol_loop_hoist`；按大闸蟹 22:14 裁定不作为本任务 review 前硬阻断，但 review 必须复核未扩大失败家族。
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。

import proof：
- `expectation.__main__=/home/lfr/kernelcode_generate/expectation/__main__.py`
- `expectation.dialect.dma.operation.make_ring=/home/lfr/kernelcode_generate/expectation/dialect/dma/operation/make_ring.py`
- `expectation.dialect.dma.operation.current_ring=/home/lfr/kernelcode_generate/expectation/dialect/dma/operation/current_ring.py`
- `expectation.dialect.dma.operation.advance_ring=/home/lfr/kernelcode_generate/expectation/dialect/dma/operation/advance_ring.py`
- `expectation.dialect.dma.type.ring_type=/home/lfr/kernelcode_generate/expectation/dialect/dma/type/ring_type.py`
- `expectation.dialect.arch.operation.token=/home/lfr/kernelcode_generate/expectation/dialect/arch/operation/token.py`
- `expectation.dialect.arch.operation.sign=/home/lfr/kernelcode_generate/expectation/dialect/arch/operation/sign.py`
- `expectation.dialect.arch.operation.wait=/home/lfr/kernelcode_generate/expectation/dialect/arch/operation/wait.py`
- `expectation.dialect.arch.type.token_type=/home/lfr/kernelcode_generate/expectation/dialect/arch/type/token_type.py`
- `kernel_gen.dialect.dma=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/kernel_gen/dialect/dma.py`
- `kernel_gen.dialect.arch=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/kernel_gen/dialect/arch.py`
- `kernel_gen.passes.multi_buffer=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/kernel_gen/passes/multi_buffer.py`
- `kernel_gen.passes.pipeline.npu_demo_lowering=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/kernel_gen/passes/pipeline/npu_demo_lowering.py`

Diff 反推自测：
- 实现侧：`kernel_gen/dialect/dma.py`、`kernel_gen/dialect/arch.py` 由 `test/dialect/test_dma.py` / `test/dialect/test_arch.py` 与主仓只读 `expectation.dialect.dma` / `expectation.dialect.arch` 覆盖。
- pass / registry / pipeline 侧：`kernel_gen/passes/multi_buffer.py`、`kernel_gen/passes/registry.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py` 由 `test/passes/test_multi_buffer.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py` 覆盖。
- kernel demo 侧：`test/kernel/test_matmul_symbolic_memory_genkernel.py` 与 `test/kernel/test_conv2d_symbolic_memory_genkernel.py` 合跑通过，覆盖真实 dump/e2e 入口。
- spec 侧：对应 pytest 和 `git diff --check` 覆盖文档链接/公开合同同步；review 需继续核对 API 列表与实现签名一致。

自检：
- 接口：未新增未确认公开 API；本轮公开 API 均来自计划正文，包括 `DmaRingType`、`DmaMakeRingOp`、`DmaCurrentRingOp`、`DmaAdvanceRingOp`、`ArchTokenType`、`ArchTokenOp`、`ArchSignOp`、`ArchWaitOp`、`MultiBufferPass`。
- 边界：计划正文实际只有 S1-S4，小任务卡覆盖已按实际正文记录；不虚写 S5/S6。
- 异常与兼容：`memory-stage`、registry common fold、ring/token verifier、CSE 副作用、pipeline 相邻顺序和 kernel dump 均有对应测试入口。
- 禁止修改面：未修改、复制、新建或同步 `expectation/`；`.skills` 与 `agents/standard` 为空 diff。
- 测试有效性：直接门禁足以在本任务核心实现坏掉时失败；full expectation 未通过的外部红点按大闸蟹裁定进入 review 复核条件。

结论：execute 收口完成。按大闸蟹 22:14 架构裁定，本任务可流转 review；review 必须复核直接门禁、敏感目录空 diff、主仓只读 `expectation.dialect.dma/arch` 未回退、clean main full expectation 外部红点未扩大，以及候选未触碰相关失败家族。

### 2026-05-18 22:29 execute 流转前复核

时间：2026-05-18 22:29 +0800
经办人：睡觉小分队
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：按管理员要求在流转 review 前再次确认直接门禁仍通过、敏感目录空 diff、候选未扩大 clean main 既有 full expectation 红点，并显式保留 full expectation 外部红点。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )` -> exit 0。
- `git diff --check` -> exit 0。
- `git diff --name-only -- expectation .skills agents/standard` -> 无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard` -> 无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard` -> 无输出。
- `git status --short --ignored -- expectation .skills agents/standard` -> 无输出。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py` -> `158 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv` -> `8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma && ... python3 -m expectation.dialect.arch` -> exit 0。

full expectation 外部红点保留：
- `python3 -m expectation` 不写通过；此前本 worktree 运行 1200s 未完成。
- clean main `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass` 已记录为 exit 1，失败家族为 `pass.attach_arch_information`、`pass.symbol_buffer_hoist`、`pass.symbol_loop_hoist`。
- 本候选没有修改 `expectation/`，也未新增上述失败家族；按大闸蟹 22:14 架构裁定，该既有红点不作为本轮进入 review 的硬阻断，review 必须复核此条件。

自检：
- 直接门禁仍通过。
- 敏感目录空 diff 仍成立。
- 计划正文实际只有 S1-S4，记录中不虚写 S5/S6 覆盖。
- full expectation 仍明确保留为外部红点，未被写成通过。

结论：满足大闸蟹裁定的 review 前置条件；准备执行 `-next review`。

### 2026-05-18 23:45 review 复审：最小需改项

时间：2026-05-18 23:45 +0800
经办人：不要啊教练
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：复审 dma ring type/op、arch token/sign/wait type/op、`MultiBufferPass(memory_stage=3)`、`npu-demo-lowering` 接入、spec/API/实现/pytest 一致性、Diff 反推自测、kernel dump/e2e、主仓只读 `expectation.dialect.dma/arch`、敏感目录空 diff，并按大闸蟹 22:14 裁定复核 clean main full expectation 外部红点未被候选扩大。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`。
- `git fetch origin --prune`：完成。
- `HEAD=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `origin/main=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `merge-base=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `ahead/behind=0/0`，未发生同步冲突，未覆盖任务 diff。

改动：
- 本段仅写入 review 记录；未修改实现、spec、测试、计划书、`expectation/`、`.skills` 或 `agents/standard`。

真实审查结论：最小需改项，不通过，需退回 execute。

发现 1：`MultiBufferPass` 公开 option / 稳定错误语义在 spec、实现与测试之间不一致。
- 证据：`spec/pass/multi_buffer.md:78-83` 写 direct API 错误为 `MultiBufferOptionError: memory_stage must be >= 2`，但同一 spec `spec/pass/multi_buffer.md:48` 又写 `memory_stage` 必须为正整数；实现 `kernel_gen/passes/multi_buffer.py:90-91`、`kernel_gen/passes/multi_buffer.py:576-579` 只拒绝 `<=0` 并报 `memory-stage/memory_stage must be positive`；测试 `test/passes/test_multi_buffer.py:207-210` 与 `test/passes/test_registry.py:884-895` 也锁定 `must be positive`。
- 影响：`memory_stage=1` 的公开合同不清楚，且公开错误文本属于稳定 API 语义；review 不能在 spec/实现/测试相互冲突时放行。
- 最小需改：二选一收口。若合同是 `>=2`，实现与 pytest 必须拒绝 `memory_stage=1` / `memory-stage=1` 并断言稳定错误文本；若合同是正整数，spec 错误语义必须同步为 `must be positive` 并补 `memory_stage=1` 正例或明确允许用例。涉及公开错误语义变化时按 AGENTS.md 记录用户确认来源。
- 复验建议：复跑 `pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py`，并保留 `git diff --check`。

发现 2：`test/passes/test_multi_buffer.py` 未覆盖计划要求的完整 no-op / stale-use 矩阵。
- 证据：计划 S2 执行步骤 5 要求 lhs/rhs 任一缺失、missing free、multiple free、free 早于最后使用、已有 ring、非 matmul、非直系 body、nested/sibling region、view/reshape alias 逃逸、partial/accumulator buffer 或不属于 lhs/rhs staging pair 的 alloc 一律整对 no-op；计划 S2 执行步骤 11 要求测试包含 partial/accumulator no-op、已有 ring no-op、非 matmul no-op、只存在 lhs 或 rhs 的 partial pair no-op、current/use/advance 顺序和 no stale slot use 断言。当前 `test/passes/test_multi_buffer.py` 只有 `TC-MULTI-BUFFER-001..006`，覆盖 options、registry、lhs/rhs 正例、missing free、free before matmul、alias escape；当前 `spec/pass/multi_buffer.md:109-118` 的测试矩阵也只列这 6 类。
- 影响：本 pass 是保守改写，漏掉计划要求的负例会让 alias/control-flow/partial staging 等边界靠实现细节而非公开测试锁住；后续 pipeline 接入可能把非目标结构半改写。
- 最小需改：补齐计划要求的负例和断言，至少包括 partial/accumulator no-op、已有 ring no-op、非 matmul no-op、lhs-only/rhs-only partial pair no-op、nested/sibling or non-direct region no-op、multiple free no-op，以及 no stale slot use 的直接断言；若决定缩小测试矩阵，必须先取得架构/用户裁定并同步计划与 spec。
- 复验建议：复跑 `pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py`。

Diff 反推审查：
- `kernel_gen/dialect/dma.py`、`kernel_gen/dialect/arch.py`：新增 ring/token/sign/wait type/op，已由 `test/dialect/test_dma.py`、`test/dialect/test_arch.py` 与主仓只读 `expectation.dialect.dma/arch` 覆盖；本轮未发现未在 spec 列出的新增公开 API。
- `kernel_gen/passes/multi_buffer.py`、`kernel_gen/passes/registry.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`：已由 pass/registry/pipeline pytest 覆盖，但发现公开 option 错误语义不一致与 multi-buffer 负例矩阵缺口。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`：文件声明无跨文件公开 API；内部调用父级公开 `emit_c_value(value: SSAValue, ctx: EmitCContext) -> str`，该 API 在 `kernel_gen/dsl/gen_kernel/emit/__init__.py` 文件级 API 列表中列明。
- 候选没有修改 `expectation/`，也没有修改 `attach_arch_information`、`symbol_buffer_hoist`、`symbol_loop_hoist` 相关 expectation 本体；未发现候选把 clean main 外部红点家族扩大为新家族。

复跑验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py`：`158 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch`：exit 0。
- `git diff --check`：exit 0。

敏感目录与禁止修改面：
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。

静态扫描：
- 扫描本轮 changed/untracked Python 文件中的 `hasattr(`、`getattr(`、`callable(getattr`、`object` 签名、`_type` 写入、`from .* import _`：未发现本任务新增 ctx 能力探测、`object` 公开签名、`result._type` / `arg._type` 私有字段写入或跨文件导入私有 helper 的阻断项。
- 命中项主要为已有公开 availability 断言、registry 对 pass class 的属性读取、SSA/type verifier 局部变量，不构成本轮新增阻断。

full expectation 外部红点保留：
- 本 review 复跑 `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.pass`：exit 1。
- 失败家族仍为 `pass.attach_arch_information`、`pass.symbol_buffer_hoist`、`pass.symbol_loop_hoist`，与大闸蟹 22:14 裁定列出的 clean main 外部红点一致。
- 本记录不写 `python3 -m expectation` 或 `python3 -m expectation.pass` 通过；只记录“full expectation 存在 clean main 外部红点，本候选未扩大，按架构裁定不作为本轮 review 前置阻断”。

自检：
- 已先读取个人提示词、AGENTS.md 与 agents/standard 规则，并按 review 职责只审查不改实现。
- 已按最新规则先 fetch 并确认待审 worktree 与 `origin/main` 同步，无冲突和覆盖风险。
- 已按实际 diff 反推审查，不用 expectation 替代 pytest。
- 已检查公开 API/spec/test 边界、跨文件非公开 API、测试直连非 API、ctx 能力探测、object 签名、非装饰器嵌套函数和敏感目录空 diff。
- 直接门禁和主仓只读 `expectation.dialect.dma/arch` 虽通过，但两项可执行阻断仍成立，因此不能给通过。

结论：不通过，最小需改项如上。请退回 execute 收口 `multi-buffer` 公开 option 错误语义一致性与计划要求 no-op/stale-use 测试矩阵；修复后重新 review。full expectation 仍按大闸蟹 22:14 裁定保留 clean main 外部红点口径，不得写为通过。

### 2026-05-19 01:28 execute 返工收口

时间：2026-05-19 01:28 +0800
经办人：咯咯咯
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：修复 review 退回的最小需改项：统一 `MultiBufferPass` `memory-stage` 公开 option 与稳定错误语义，补齐计划要求的 no-op 和 no-stale-slot-use pytest 矩阵，并按大闸蟹 22:14 裁定保留 full expectation 外部红点。

执行前阅读记录：
- 已重新读取 `agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`、根 `AGENTS.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/expectation任务规则.md`。
- 已读取计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_ring_arch_token_multi_buffer_green_plan.md` 的 S1-S4、公开 API 设计、`memory-stage=<positive-int>` option、S2 no-op / stale-use 测试矩阵与 S4 验收要求。
- 已读取本记录中 takeover、22:14 大闸蟹 full expectation 外部红点裁定、22:20/22:29 execute 收口记录与 23:45 review 最小需改项。
- 已读取主仓 `/home/lfr/kernelcode_generate/TODO.md` 当前任务行，确认本任务仍为 `execute / 咯咯咯 / 进行中`；worktree 内无独立 `TODO.md`。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`。
- `git fetch origin main`：完成。
- `HEAD=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `origin/main=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `merge-base=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- 未发生同步冲突，未覆盖候选 diff。

返工收口：
- 针对发现 1：采用计划正文与 registry spec 已写明的 `memory-stage=<positive-int>` 合同，不新增公开 API、不改 option 名。`spec/pass/multi_buffer.md` 将 direct API 错误语义统一为 `MultiBufferOptionError: memory_stage must be positive`，并明确 `from_options({"memory-stage": "1"})` 是允许正例；实现侧原本已按 `positive` 失败语义处理，未改成 `>=2`。
- 针对发现 1：`test/passes/test_multi_buffer.py` 增加 `MultiBufferPass(memory_stage=1)` 与 `from_options({"memory-stage": "1"})` 正例；`test/passes/test_registry.py` 增加 registry `memory-stage=1` 正例。
- 针对发现 2：`test/passes/test_multi_buffer.py` 扩展到 13 个公开 pass API 用例，覆盖 multiple free no-op、已有 ring no-op、lhs-only/rhs-only partial pair no-op、非 `symbol.for` 直接 body no-op、非 matmul no-op、accumulator/output alloc 不被 ring 化、current/use/advance 顺序和 no stale slot use。
- 针对发现 2：`spec/pass/multi_buffer.md` 同步测试矩阵，明确 partial/accumulator buffer 不属于 lhs/rhs pair 时保持原生命周期，不被 ring 化；合法 lhs/rhs pair 仍可在真实 pipeline 内 ring 化。
- 修复过程中曾临时加过过窄的 nested loop / extra alloc 整体 no-op 约束，导致 `test_npu_demo_lowering_pipeline_multi_buffer_static_dump_uses_ring_and_pool` 失败；已撤回该过窄实现，保留真实 pipeline 的 `dma.make_ring/current_ring/advance_ring` 目标形态。

最小功能闭环：
- `MultiBufferPass` 公开 option 仍为 `memory-stage=<positive-int>`，默认 stage=3；`memory_stage=1` / `memory-stage=1` 明确可用，`0`、负数、非整数和未知 option 仍稳定失败。
- no-op 矩阵现在覆盖计划要求的核心保守边界；测试只通过公开 `MultiBufferPass.apply(...)`、公开 registry 入口和公开 dialect op 构造 IR，不直连跨文件非公开 helper。
- no stale slot use 断言直接检查同 ring 的 `dma.advance_ring` 之后不再消费推进前 `dma.current_ring` result。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/multi_buffer.py test/passes/test_multi_buffer.py test/passes/test_registry.py && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py` -> `13 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/multi_buffer.py test/passes/test_multi_buffer.py test/passes/test_registry.py && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py` -> `70 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py` -> `165 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv` -> `8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma && ... python3 -m expectation.dialect.arch` -> exit 0。
- `git diff --check` -> exit 0。
- `git diff --name-only -- expectation .skills agents/standard` / `git diff --cached --name-only -- expectation .skills agents/standard` / `git status --short --untracked-files=all -- expectation .skills agents/standard` / `git status --short --ignored -- expectation .skills agents/standard` -> 均无输出。
- 静态扫描 changed/untracked Python 文件中的 `hasattr(`、`getattr(`、`callable(getattr`、`object` 签名、`from .* import _`、`._type`：未发现本轮新增 ctx 能力探测、跨文件私有 helper 导入或公开 `object` 签名阻断；命中项为既有 registry/测试属性读取、测试内 `object()` 哨兵和公开 availability 断言，不属于本轮新增阻断。

import proof：
- `expectation.dialect.dma.operation.make_ring=/home/lfr/kernelcode_generate/expectation/dialect/dma/operation/make_ring.py`
- `expectation.dialect.dma.operation.current_ring=/home/lfr/kernelcode_generate/expectation/dialect/dma/operation/current_ring.py`
- `expectation.dialect.dma.operation.advance_ring=/home/lfr/kernelcode_generate/expectation/dialect/dma/operation/advance_ring.py`
- `expectation.dialect.arch.operation.token=/home/lfr/kernelcode_generate/expectation/dialect/arch/operation/token.py`
- `expectation.dialect.arch.operation.sign=/home/lfr/kernelcode_generate/expectation/dialect/arch/operation/sign.py`
- `expectation.dialect.arch.operation.wait=/home/lfr/kernelcode_generate/expectation/dialect/arch/operation/wait.py`
- `kernel_gen.dialect.dma=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/kernel_gen/dialect/dma.py`
- `kernel_gen.dialect.arch=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/kernel_gen/dialect/arch.py`
- `kernel_gen.passes.multi_buffer=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/kernel_gen/passes/multi_buffer.py`
- `kernel_gen.passes.pipeline.npu_demo_lowering=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer/kernel_gen/passes/pipeline/npu_demo_lowering.py`

Diff 反推自测：
- `spec/pass/multi_buffer.md` 的 option/error/matrix 改动由 `test/passes/test_multi_buffer.py`、`test/passes/test_registry.py` 和 `git diff --check` 覆盖；断言锁定 `memory-stage=1` 正例、`0/负数/非整数/unknown/fold` 失败边界与文档矩阵。
- `test/passes/test_multi_buffer.py` 的 no-op/stale-use 扩展由本文件 13 个用例覆盖；新增断言能在 extra free、existing ring、partial pair、non-direct body、non-matmul、accumulator 和 stale current slot 行为错误时失败。
- `test/passes/test_registry.py` 的 registry 正例由 `test_build_registered_multi_buffer_options` 覆盖。
- 因返工过程中核对了 pipeline 真实 ring 化，补跑 `test/passes/pipeline/test_npu_demo_lowering.py`，确认 `multi-buffer` dump 仍含 `dma.make_ring/current_ring/advance_ring` 且 memory-pool 后无 `dma.alloc/free` 回退。
- 候选仍包含前序 dma/arch/pipeline/kernel 直接改动，因此同步复跑 dialect、pass、pipeline、kernel demo pytest 与主仓只读 `expectation.dialect.dma/arch`。

full expectation 外部红点保留：
- 本记录不写 `python3 -m expectation` 或 `python3 -m expectation.pass` 通过。
- 复跑 clean main：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass > /tmp/T-20260518-e79bde42-expectation-pass-clean-main.log 2>&1` -> exit 1。
- 失败摘要仍包含 `pass.symbol_loop_hoist.symbol_minmax` 的 `CHECK-NEXT not found`，并继续出现前序已记录的 `pass.symbol_buffer_hoist` 家族输出；按大闸蟹 22:14 裁定，full expectation clean main 外部红点不得写成通过，且不作为本轮 review 前硬阻断。
- 本轮未修改 `expectation/` 本体，也未把 `expectation` 纳入普通任务 diff。

自检：
- 接口：未新增、删除、重命名或改签公开 API；`memory-stage` 仍是计划确认的公开 option，稳定错误语义已在 spec / 实现 / pytest 间一致。
- 边界：未修改 `expectation/.skills/agents/standard`；任务记录落点为当前 worktree 指定记录文件。
- 异常：`memory_stage` 直接构造与 `memory-stage` registry option 的正例和错误路径均有 pytest；`fold` 仍只由 registry 通用 option 处理。
- 兼容：没有新增 ctx 能力探测、非装饰器嵌套函数、公开 `object` 签名或跨文件非公开 API 调用。
- 实现遗漏：no-op 矩阵已补齐 review 指出的 multiple free、已有 ring、非 matmul、partial pair、非直系 body、accumulator 与 stale slot use；真实 pipeline ring 化也已复跑防回退。
- 冗余与复用：测试 helper 只服务本文件公开 pass 行为构造，未抽跨文件 helper；重复断言集中到本文件本地 helper。
- 注释准确性：spec 的 accumulator 口径改为“不被 ring 化，合法 lhs/rhs pair 仍可改写”，避免与真实 pipeline output alloc 冲突。
- 函数粒度与可维护性：实现最终未引入额外复杂分支；测试扩展保持按场景分组。
- 输入输出校验：memory-stage 正整数边界、registry 包装错误、ring rewrite 输出形态和 no-op 输入均有覆盖。
- 资源/并发/性能：本轮未引入资源持有或并发状态；新增测试为小型 IR，未扩大长耗时路径。
- 测试有效性：新增断言均会在对应错误实现下失败；expectation 单列为合同验收，不计入 Diff 反推自测。

结论：execute 返工已完成，满足 review 退回的两项最小需改项；直接 pytest、主仓只读 `expectation.dialect.dma/arch`、`git diff --check`、敏感目录空 diff和静态扫描已通过。full expectation 仍按大闸蟹 22:14 裁定保留为 clean main 外部红点，不写通过。下一步按流程流转 review。

### 2026-05-19 review 复审

审查基线：
- 已按最新同步规则先 `git fetch origin` 并确认 worktree `/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer` 与 `origin/main=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0` 对齐，`merge-base` 相同，无覆盖任务 diff 风险。
- 仍保持只读审查，不修改实现、spec、test、expectation/.skills 或 agents/standard。

复审范围：
- 任务 `T-20260518-e79bde42` 的 `MultiBufferPass` memory-stage 返工。
- 重点核对：公开 option/错误语义、no-op/no-stale-slot-use pytest 矩阵、Diff 反推自测、主仓只读 `expectation.dialect.dma/arch`、敏感目录空 diff、静态扫描、full expectation 外部红点保留口径。

已核验证据：
- `spec/pass/multi_buffer.md:41, 48-52, 56-76, 112-125`：公开 option 约束、ring 改写模式、输出形态与测试矩阵已收口到当前版本。
- `test/passes/test_multi_buffer.py:367-584`：已覆盖 `memory-stage=1` 正例、registry `fold=false` 透传、missing free、free-before-matmul、alias escape、多 free、existing ring、partial pair、non-direct body、non-matmul、accumulator/no-stale-slot-use 等场景。
- `test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`：registry 及 pipeline 顺序、`dma.make_ring/current_ring/advance_ring` 目标形态已复跑。
- `python3 -m py_compile`、`pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py`、`pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py`、`PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`、`git diff --check`、`python3 -m expectation.dialect.dma`、`python3 -m expectation.dialect.arch` 均通过。
- `python3 -m expectation.pass` 仍为 exit 1，失败仍落在 clean main 外部红点家族，未扩大到本候选 diff；本轮不把它写成通过。
- `git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --untracked-files=all -- expectation .skills agents/standard`、`git status --short --ignored -- expectation .skills agents/standard` 均无输出。

Diff 反推审查：
- `kernel_gen/passes/multi_buffer.py`、`kernel_gen/passes/registry.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py` 与对应测试的直接 diff 已被上述 pytest / 直读 expectation / diff check 覆盖。
- `test/passes/test_multi_buffer.py` 的 no-op 矩阵已比前一轮更完整，但仍缺少对 `spec/pass/multi_buffer.md:41` 明确列出的 `sibling region use` / `nested region` 负例的独立测试钉死；当前仅有 `non-direct body`、`alias escape`、`partial pair` 等覆盖，不能直接证明 sibling/nested 边界已被测试锁定。

Findings：
1. `spec/pass/multi_buffer.md:41, 198, 204` 明确把 `sibling region use`、`nested/sibling region` 列为不外提/no-op 边界，但 `test/passes/test_multi_buffer.py:524-539` 只有 `non-direct body` 场景，没有独立构造 sibling/nested region 用例。
   - 影响：实现若错误地在 sibling/nested region 上 ring 化 staging pair，仍可能通过当前矩阵，留下假绿。
   - 最小返工动作：补一条公开 pytest，使用现有公开 dialect API 构造 `symbol.for` 内 candidate alloc 在 sibling/nested region 被额外 use 的 IR，断言 `MultiBufferPass` 保持 no-op；或若确认为不需要，先回写 spec/计划收口该边界并取得架构/用户确认。
   - 验收方式：新增用例在错误实现下会失败，且 `pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py` 保持通过。

自检：
- 已确认未越权修改 `expectation/`、`.skills`、`agents/standard`。
- 已按实际 diff 反推审查，不以 expectation 通过替代 pytest。
- 已检查公开 API、跨文件非公开 API、测试直连非 API helper、ctx 能力探测、object 签名、非装饰器嵌套函数和敏感目录空 diff。

结论：
- 不通过。
- 原因：`MultiBufferPass` 的 no-op 矩阵仍缺少 `sibling region use` / `nested region` 的独立 pytest 负例，和计划书/Spec 明列边界未完全对齐。
- 下一步：退回 `execute` 补齐该负例后重新 review；full expectation 仍按大闸蟹 22:14 裁定保留 clean main 外部红点，不作为通过依据。

### 2026-05-19 21:29 execute 返工补 sibling/nested region pytest

时间：2026-05-19 21:29 +0800
经办人：金铲铲大作战
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
任务目标：补齐 review 指出的 `MultiBufferPass` sibling / nested region use no-op 公开 pytest，并同步 spec / 记录后再次流转 review。

执行前阅读记录：
- 重新读取当前角色最新 prompt、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 复核本任务链前序 takeover / execute / review 记录，确认本轮只处理 review 指出的最小阻断项，不越权改 `expectation/`、`.skills` 或 `agents/standard`。
- 再次核对当前 worktree 与最新主线同步现场：`HEAD=origin/main=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`，`git rev-list --left-right --count HEAD...origin/main = 0 0`，`git merge-base HEAD origin/main = 8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。

改动：
- `test/passes/test_multi_buffer.py` 新增 `test_multi_buffer_keeps_nested_region_use_noop`，覆盖 outer `symbol.for` 直接 body 中含 nested `symbol.for` region 的额外 alloc use 时，`MultiBufferPass` 必须保持整对 no-op。
- `test/passes/test_multi_buffer.py` 新增 `test_multi_buffer_keeps_sibling_region_use_noop`，覆盖 outer `symbol.for` 直接 body 中含 `scf.if` sibling branch region 的额外 alloc use 时，`MultiBufferPass` 必须保持整对 no-op。
- `spec/pass/multi_buffer.md` 的测试矩阵新增 TC-MULTI-BUFFER-013 / 014，明确 nested region use 和 sibling branch region use 的 no-op 预期。
- 未修改 `expectation/`、`.skills` 或 `agents/standard`；未新增公开 API。

最小功能闭环：
- 直接 body 内合法 lhs/rhs pairing 仍可 ring 化。
- 若 alloc result 再被 nested `symbol.for` 或 `scf.if` sibling branch 使用，pass 必须保持 no-op，不得误判为可 ring 化 pair。
- 该边界现在由公开 pytest 机械锁定，能够在实现退化时失败。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py -k 'nested_region_use or sibling_region_use'` -> `2 passed, 13 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py` -> `72 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch` -> exit 0。
- `git diff --check` -> exit 0。
- `git diff --name-only -- expectation .skills agents/standard` / `git diff --cached --name-only -- expectation .skills agents/standard` / `git status --short --untracked-files=all -- expectation .skills agents/standard` / `git status --short --ignored -- expectation .skills agents/standard` -> 均为空。
- 导入边界证明：`expectation.dialect.dma.operation.make_ring/current_ring/advance_ring`、`expectation.dialect.dma.type.ring_type`、`expectation.dialect.arch.operation.token/sign/wait`、`expectation.dialect.arch.type.token_type` 均来自 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.dialect.dma`、`kernel_gen.dialect.arch`、`kernel_gen.passes.multi_buffer` 均来自任务 worktree。
- 静态扫描：`rg -n 'hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx|from [^\\n]+ import _|\\._[A-Za-z]' kernel_gen/passes/multi_buffer.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py test/passes/test_multi_buffer.py` -> 无输出。
- 本轮未复跑 full expectation；沿用前序记录里 clean main 的 expectation.pass 基线红点归因，不把它写成本轮通过。

Diff 反推自测：
- `test/passes/test_multi_buffer.py` 新增 nested / sibling no-op 用例，由 `pytest -q test/passes/test_multi_buffer.py -k 'nested_region_use or sibling_region_use'` 精确覆盖。
- `spec/pass/multi_buffer.md` 测试矩阵新增 TC-013 / TC-014，由完整 `pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py` 覆盖，确认矩阵扩展不回退 registry / pipeline 行为。
- `expectation.dialect.dma` / `expectation.dialect.arch` 作为合同验收资产单列，不计入 Diff 反推自测。

自检：
- 接口：未新增未确认公开 API；仅补测试用例与 spec 测试矩阵。
- 边界：nested / sibling region use 现在由公开 pytest 显式覆盖；对 alias escape、partial pair、non-direct body、non-matmul 的既有边界未回退。
- 测试有效性：新增断言在 pass 误把跨 region use 当可 ring 化时会失败，不是空跑测试。
- 兼容性：未使用 ctx 能力探测，未跨文件调用非公开 helper，未修改 `expectation/`、`.skills`、`agents/standard`。
- 冗余/复用：新增 helper 均在测试文件内，只服务公开 pass 行为构造；没有新增跨文件 helper。

结论：review 最小阻断项已补齐，直接 pytest、主仓只读 `expectation.dialect.dma/arch`、`git diff --check`、敏感目录空 diff和静态扫描均通过。当前候选可重新流转 review；full expectation 仍沿用前序记录里的 clean main 外部红点说明，不写通过。

### 2026-05-19 21:47 review 复审通过

审查角色：不要啊教练
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer
审查目录：`/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`
计划真源：worktree 内未包含 `ARCHITECTURE/plan/dma_ring_arch_token_multi_buffer_green_plan.md`；本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_ring_arch_token_multi_buffer_green_plan.md`，与前序 takeover / 架构裁定记录一致。

前置同步：
- 已执行 `git fetch origin --prune`。
- `HEAD=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `origin/main=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `merge-base=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `git rev-list --left-right --count HEAD...origin/main` -> `0 0`。
- 更新结果：待审 worktree 已与最新 `origin/main` 对齐；未发生冲突，未覆盖任务 diff，未发现需要 reset/checkout 的风险。

复审重点：
- 复核上一轮 review 退回项：`MultiBufferPass` 对 nested `symbol.for` region use 和 sibling `scf.if` branch region use 必须保持 no-op。
- 核对公开 API、实现、spec、pytest、Diff 反推自测、主仓只读 `expectation.dialect.dma` / `expectation.dialect.arch`、`git diff --check`、敏感目录空 diff、静态扫描与任务记录。
- 继续保留大闸蟹 2026-05-18 22:14 裁定：full expectation / `expectation.pass` 的 clean main 外部红点不得写成通过，但在直接门禁通过且失败未扩大时不作为本轮 review 前置阻断。

真实审查：
- `spec/pass/multi_buffer.md` 已新增 TC-MULTI-BUFFER-013 / 014，覆盖 nested region use no-op 与 sibling branch region use no-op；非目标边界仍明确为不处理跨 region control flow、alias escape、已有 ring、多 free、partial pair 与非 matmul。
- `test/passes/test_multi_buffer.py` 已新增 `test_multi_buffer_keeps_nested_region_use_noop` 与 `test_multi_buffer_keeps_sibling_region_use_noop`，均只通过公开 `MultiBufferPass.apply(...)` 和公开 dialect op 构造 IR，不直连 `kernel_gen/passes/multi_buffer.py` 的私有 helper。
- `kernel_gen/passes/multi_buffer.py` 的 `_collect_candidate_uses(...)` 仍要求所有 use 的 operation block 必须是 owner loop direct body；nested/sibling region use 会直接返回 no-op，和新增 pytest、spec 矩阵一致。
- `kernel_gen/passes/multi_buffer.py` 的文件级 API 列表列出 `MultiBufferPass(memory_stage: int = 3, fold: bool = True)`、`from_options(...)`、`apply(...)`；class 和公开方法注释包含功能说明与使用示例。
- `kernel_gen/dialect/dma.py`、`kernel_gen/dialect/arch.py` 的 ring/token 公开 API 列表与对应 spec/test 保持一致；未发现本轮新增未在 spec 明确定义的公开接口。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 声明无公开 API，调用边界通过 emit registry；未发现跨文件调用非公开 helper。
- 静态扫描：新增 diff 行未命中 `ctx` 能力探测、跨文件私有导入、`object` 签名、`._type` 私有字段写入或非装饰器嵌套函数。宽泛扫描命中的 `getattr/hasattr/object` 位于既有 registry 公开反射、测试本地 helper 或 xDSL owner/block 读取，不构成本轮新增违规。
- 敏感目录：`expectation/`、`.skills`、`agents/standard` 的 tracked、cached、untracked、ignored 检查均为空；本轮未复制、修改、新建、移动或删除 expectation 合同资产。

Diff 反推审查：
- `test/passes/test_multi_buffer.py` 新增 nested/sibling no-op 用例，由 `pytest -q test/passes/test_multi_buffer.py -k 'nested_region_use or sibling_region_use'` 精确覆盖，且能在错误 ring 化跨 region use 时失败。
- `spec/pass/multi_buffer.md` 的 TC-013 / TC-014 已由完整 `test/passes/test_multi_buffer.py` 与 `test/passes/test_registry.py` / `test/passes/pipeline/test_npu_demo_lowering.py` 联合覆盖，确认补测不回退 registry 与 pipeline 行为。
- 候选仍包含 `dma` / `arch` dialect、`npu_demo` emit、`dma_memory_hierarchy`、registry、template constraints 与 kernel demo 相关改动，因此同步复跑 dialect、pass、pipeline、kernel demo pytest 与主仓只读 dialect expectation。
- `expectation.dialect.dma` 与 `expectation.dialect.arch` 只作为合同验收资产单列，不计入 Diff 反推测试；未用 expectation 替代 pytest。

复跑验收：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py -k 'nested_region_use or sibling_region_use'` -> `2 passed, 13 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py` -> `72 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py` -> `167 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv` -> `8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma` -> exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch` -> exit 0。
- import proof：`expectation.dialect.dma.*` 与 `expectation.dialect.arch.*` 来自 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.dialect.dma`、`kernel_gen.dialect.arch`、`kernel_gen.passes.multi_buffer`、`kernel_gen.passes.pipeline.npu_demo_lowering` 来自任务 worktree。
- `git diff --check` -> exit 0。
- `git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --untracked-files=all -- expectation .skills agents/standard`、`git status --short --ignored -- expectation .skills agents/standard` -> 均无输出。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass` -> exit 1；失败仍为 clean main 外部红点家族，未作为本轮通过依据。

可改进点：
- 无新的 review 阻断项。
- 建议后续架构复核/终验继续显式保留 full expectation 外部红点裁定，不得把 full expectation 写成通过；若失败家族扩大或触及本候选直接范围，需重新回 execute 或请求架构裁定。

自检：
- 特殊情况：已覆盖 nested region use、sibling branch region use、alias escape、多 free、partial pair、non-direct body、existing ring 与 stale current slot use。
- 完整性：公开 API、spec、实现、pytest、registry、pipeline、emit、主仓只读 expectation 与敏感目录门禁均已核对。
- 维护性：新增测试只走公开 API，未把当前文件外私有 helper 固化为测试合同。
- 扩展性：`multi-buffer` v1 明确 no-op 边界，后续若扩展跨 region/alias，需要先改 spec/API 与测试矩阵。
- 测试有效性：Diff 反推 pytest 能覆盖本轮返工点，expectation 单列为合同验收资产。

结论：通过。
下一步：本任务为计划级任务，review 通过后应回管理员进入架构复核/终验，不直接 merge；merge 前仍需按计划记录同批合并、终验与外部 full expectation 裁定。

### 2026-05-19 21:59 第二架构计划级复核 / 终验

时间：2026-05-19 21:59 CST
经办人：守护最好的爱莉希雅
任务：T-20260518-e79bde42；计划级架构复核 / 终验；计划书 `ARCHITECTURE/plan/dma_ring_arch_token_multi_buffer_green_plan.md`
任务目标：在 review 复审通过后，按计划终验规则核对 latest main 同步现场、主仓只读 `expectation.dialect.dma` / `expectation.dialect.arch` 合同验收、Diff 反推 pytest、kernel demo pytest、导入边界、敏感目录空 diff、full expectation 外部红点口径和最小阻断项。

验证基线与执行目录：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`。
- 已执行 `git fetch origin main`：成功。
- `HEAD=origin/main=merge-base=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- `git status --short --branch`：当前任务 diff 为 dma/arch dialect、multi-buffer pass、pipeline/spec/test/kernel emit 和本任务记录；未见无关敏感目录改动。

合同验收摘要：
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma`：exit=0，覆盖 ring type、`dma.make_ring`、`dma.current_ring`、`dma.advance_ring` 以及既有 dma parse/verifier 合同。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch`：exit=0，覆盖 token type、`arch.token`、`arch.sign`、`arch.wait` 以及既有 arch parse/verifier 合同。
- 导入边界复核：`expectation.dialect.dma.operation.make_ring/current_ring/advance_ring`、`expectation.dialect.dma.type.ring_type`、`expectation.dialect.arch.operation.token/sign/wait`、`expectation.dialect.arch.type.token_type` 均来自主仓 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.dialect.dma`、`kernel_gen.dialect.arch`、`kernel_gen.passes.multi_buffer`、`kernel_gen.passes.pipeline.npu_demo_lowering` 均来自任务 worktree。
- full expectation / `expectation.pass`：本轮未写成通过；继续沿用 2026-05-18 22:14 架构裁定和 review 复审记录，clean main 外部红点不作为本轮通过依据，也不作为当前直接阻断。若后续失败家族扩大到本候选直接范围，必须回 execute 或重新请求架构裁定。

Diff 反推验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py -k 'nested_region_use or sibling_region_use'`：`2 passed, 13 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py`：`167 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：`8 passed, 1 warning`。
- `git diff --check`：exit=0。

敏感目录与静态扫描：
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。
- `rg -n "hasattr\\(|getattr\\([^\\n]*ctx|callable\\(getattr|from kernel_gen\\.passes\\..* import _|pass_module\\._|: object|-> object" ...`：仅命中 `test/passes/test_registry.py` 中 `assert not hasattr(lowering_module, "BufferResultsToOutParamsPass")` 的历史 re-export 负例；该命中不是 `ctx` 能力探测，不是本轮新增公开 API 兼容分支，不构成阻断。未发现跨文件私有 pass helper import 或 `pass_module._` 直连。

自检：
- 终验已在 latest main 同步现场运行当前计划直接相关合同验收；`expectation.dialect.dma/arch` 单列为合同资产，未替代 Diff 反推 pytest。
- review 退回的 nested/sibling region use no-op 边界已有公开 pytest 精确覆盖，并在本轮复跑通过。
- 敏感目录 tracked/cached/untracked/ignored 均为空；任务 worktree 未复制、修改、新建、移动或删除 `expectation/`。
- 公开 API、registry option、spec/test/实现和导入边界均沿计划与用户确认口径；未发现新的可执行返工项。

结论：通过；最小阻断项：无。T-20260518-e79bde42 可进入后续架构双验/merge 流转；merge 前仍需合并角色按合并规范核对任务记录同批合入、候选 diff、敏感目录空 diff、full expectation 外部红点裁定和 latest main 状态。

### 2026-05-19 21:57 大闸蟹计划级架构复核 / 终验

时间：2026-05-19 21:57 CST
经办人：大闸蟹
任务：T-20260518-e79bde42 / dma-ring-arch-token-multi-buffer；计划级架构复核 / 终验
任务目标：按 `ARCHITECTURE/plan/dma_ring_arch_token_multi_buffer_green_plan.md` 和 2026-05-18 22:14 full expectation 外部红点裁定，复核 latest 同步现场、直接合同验收、Diff 反推测试、kernel demo、敏感目录、静态扫描、任务记录同批合并证据和最小阻断项。

终验前阅读记录：
- 已重新读取 `agents/codex-multi-agents/agents/大闸蟹/大闸蟹.prompt.md`、根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/expectation任务规则.md`、`agents/standard/任务记录约定.md`。
- 已读取主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_ring_arch_token_multi_buffer_green_plan.md` 的文档信息、公开 API、S1-S4、完成态和验收设计。
- 已读取本任务记录中 2026-05-18 22:14 大闸蟹裁定、execute / review / 复审记录；确认 full expectation / `expectation.pass` 不能写成通过，clean main 外部红点必须在终验和 merge 记录中显式保留。

验证基线与执行目录：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`。
- 已执行 `git fetch origin --prune`。
- `HEAD=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`，`origin/main=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`，`merge-base=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- `git status --short --branch`：候选 diff 位于计划范围；任务记录文件为当前 worktree 候选新增记录，merge 时必须与代码 / spec / test 同批合入。

合同验收：
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma`：exit=0；覆盖 `dma.make_ring/current_ring/advance_ring` 与 `!dma.ring` 合同。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch`：exit=0；覆盖 `arch.token/sign/wait` 与 `!arch.token` 合同。
- import proof：`expectation.dialect.dma.operation.make_ring/current_ring/advance_ring`、`expectation.dialect.dma.type.ring_type`、`expectation.dialect.arch.operation.token/sign/wait`、`expectation.dialect.arch.type.token_type` 均来自 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.dialect.dma`、`kernel_gen.dialect.arch`、`kernel_gen.passes.multi_buffer`、`kernel_gen.passes.pipeline.npu_demo_lowering` 均来自任务 worktree。
- full expectation 外部红点保留：本轮复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass`，exit=1；失败家族仍为 `pass.attach_arch_information`、`pass.symbol_buffer_hoist`、`pass.symbol_loop_hoist`，与 2026-05-18 22:14 裁定一致。本记录不写 `python3 -m expectation` 或 `python3 -m expectation.pass` 通过；`python3 -m expectation` 未重新长跑，因 `expectation.pass` 已复现既有外部红点且前序记录证明 full expectation 1200s 未闭合。

Diff 反推与计划 hard gate：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py -k 'nested_region_use or sibling_region_use'`：`2 passed, 13 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py`：`72 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py`：`167 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：`8 passed, 1 warning`。

静态与敏感目录核对：
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard` 与 `git status --short --ignored -- expectation .skills agents/standard`：空。
- `rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr\(ctx|from [^\n]+ import _|\._type|: object|-> object|def .+\(.*object' <本轮 changed/untracked Python 文件>`：exit=1，无命中；未发现本轮新增 ctx 能力探测、跨文件私有 helper import、私有 `_type` 写入或公开 `object` 签名。
- `rg -n "最终 review|终验|Diff 反推|合同验收|同批合并" agents/codex-multi-agents/log/task_records/2026/20/20260518-dma-ring-arch-token-multi-buffer.md`：命中前序 review、Diff 反推、合同验收与同批合并记录要求；本段补齐大闸蟹侧终验结论。

自检：
- 公开 API：`DmaRingType`、`DmaMakeRingOp`、`DmaCurrentRingOp`、`DmaAdvanceRingOp`、`ArchTokenType`、`ArchTokenOp`、`ArchSignOp`、`ArchWaitOp`、`MultiBufferPass(memory_stage=3, fold=True)`、`from_options`、registry `multi-buffer` 与 `memory-stage` option 均来自用户已确认计划；未发现未确认公开 API 或稳定错误语义变更。
- 合同资产：任务 worktree 未修改、复制或物化 `expectation/`；直接合同 `expectation.dialect.dma/arch` 使用主仓 expectation + 任务 worktree `kernel_gen` 通过。
- full expectation：按 2026-05-18 22:14 裁定显式保留 clean main 外部红点，不作为本轮直接门禁通过依据，也不写成通过；本轮复跑 `expectation.pass` 未发现失败家族扩大。
- 测试有效性：nested/sibling region no-op 返工点、multi-buffer/registry/pipeline、dma/arch dialect、template/dma hierarchy 相关测试、kernel demo 均已复跑；expectation 单列为合同验收，不替代 pytest。
- 禁止修改面：`expectation/.skills/agents/standard` tracked、cached、untracked、ignored 检查均为空。
- 记录：任务记录为候选新增文件，已含 takeover、execute、review、复审、full expectation 外部红点裁定和本次终验；merge 阶段必须确认记录与代码/spec/test 同批合入。

结论：大闸蟹侧计划级架构复核 / 终验通过；最小阻断项：无。双架构通过前不得 merge；进入 merge 前仍需合并角色按合并规范核对 latest main、敏感目录空 diff、任务记录同批合入和 full expectation 外部红点保留口径。

### 2026-05-19 22:01 守护最好的爱莉希雅第二架构终验顺序补记

时间：2026-05-19 22:01 CST
经办人：守护最好的爱莉希雅
任务：T-20260518-e79bde42；第二架构计划级复核 / 终验顺序补记
任务目标：将第二架构终验结论追加到文件尾部，避免上文 2026-05-19 21:59 完整终验段落位于大闸蟹终验段之前导致管理员误判缺结论。

验证基线与执行目录：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`。
- `HEAD=origin/main=merge-base=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`，`HEAD...origin/main=0 0`。

合同验收摘要：
- 主仓只读 `expectation.dialect.dma`：exit=0。
- 主仓只读 `expectation.dialect.arch`：exit=0。
- 导入边界：`expectation.dialect.dma/arch` 来自主仓 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.dialect.dma`、`kernel_gen.dialect.arch`、`kernel_gen.passes.multi_buffer`、`kernel_gen.passes.pipeline.npu_demo_lowering` 来自任务 worktree。
- full expectation / `expectation.pass` 仍按 2026-05-18 22:14 裁定保留 clean main 外部红点，不写成通过，也不作为本轮直接阻断。

验证摘要：
- `py_compile` 本轮 changed/untracked Python 文件：exit=0。
- nested/sibling region use 定向 pytest：`2 passed, 13 deselected, 1 warning`。
- dialect/pass/pipeline/template/dma hierarchy pytest 集合：`167 passed, 1 warning`。
- matmul/conv2d kernel demo pytest：`8 passed, 1 warning`。
- `git diff --check`：exit=0。
- `expectation/.skills/agents/standard` tracked、cached、untracked、ignored 检查均为空。
- 静态扫描仅命中 `test/passes/test_registry.py` 的历史 re-export 负例 `assert not hasattr(...)`，非 `ctx` 能力探测，非本轮阻断；未发现跨文件私有 pass helper import 或 `pass_module._` 直连。

自检：
- 上文 21:59 段已写完整命令和证据；本段只作为文件尾顺序补记。
- review 返工点已由公开 pytest 覆盖；主仓只读合同验收和敏感目录门禁均通过；未发现新的可执行返工项。

结论：通过；最小阻断项：无。T-20260518-e79bde42 已具备第二架构计划级终验通过结论，可进入后续双架构/merge 流转；merge 前仍需合并角色按合并规范核对任务记录同批合入、候选 diff、敏感目录空 diff、full expectation 外部红点裁定和 latest main 状态。

### 2026-05-19 22:31 李白 merge 收口记录

时间：2026-05-19 22:31 CST
经办人：李白
任务：T-20260518-e79bde42；merge 收口
任务目标：按合并规范将已通过双架构终验的 `dma-ring-arch-token-multi-buffer` 候选同步到 latest `origin/main`，核对冲突/重叠、任务记录同批、直接合同验收、敏感目录空 diff、full expectation 外部红点口径，并完成 merge / push / `-done`。

合并前规则与来源：
- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- 李白只做合并与同步确认；不补实现、不补审查、不改计划书、不修改 `expectation/`。
- 任务来源 worktree：`/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer`。
- 来源分支：`task/dma-ring-arch-token-multi-buffer`。
- 计划书只读核对使用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_ring_arch_token_multi_buffer_green_plan.md`。

latest main 同步与冲突处理：
- `git fetch --prune origin`：成功。
- 同步前基线：`HEAD=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`；`origin/main=95b2cfc1ef904bd03fe9ded3a9c9861c54c8b96e`；`merge-base=8cded6bd3240b5e9a9a07e2f3f1510ed1d22abe0`；`HEAD...origin/main=0 1`。
- 先将本任务候选代码 / spec / test / 任务记录固化为分支提交 `aedb256b`，随后执行 `git merge --no-ff --no-edit origin/main` 对齐 latest main。
- 同步冲突：
  - `kernel_gen/dialect/dma.py`
  - `spec/dialect/dma.md`
- 冲突原因：本任务在同一文件中新增 `dma.ring` / `dma.make_ring` / `dma.current_ring` / `dma.advance_ring`，而 latest main `95b2cfc1` 已合入 `MemoryEffect` 公开读写语义与相关 spec/test。
- 处理方式：仅做机械并集合并，保留本任务 ring type/op/API/spec/test，同时保留 latest main 的 `MemoryEffect` trait helper、`NoMemoryEffect` / read-write 语义和 spec 文本；未新增计划外公开 API，未改 `expectation/`。
- `rg -n "<<<<<<<|=======|>>>>>>>" kernel_gen/dialect/dma.py spec/dialect/dma.md`：无输出。

候选范围核对：
- 本任务候选文件：
  - `agents/codex-multi-agents/log/task_records/2026/20/20260518-dma-ring-arch-token-multi-buffer.md`
  - `kernel_gen/dialect/arch.py`
  - `kernel_gen/dialect/dma.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/__init__.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`
  - `kernel_gen/passes/__init__.py`
  - `kernel_gen/passes/dma_memory_hierarchy.py`
  - `kernel_gen/passes/multi_buffer.py`
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/template_name_default_constraints.py`
  - `spec/dialect/arch.md`
  - `spec/dialect/dma.md`
  - `spec/pass/lowering/dma_memory_hierarchy/spec.md`
  - `spec/pass/multi_buffer.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/pass/template_name_default_constraints.md`
  - `test/dialect/test_arch.py`
  - `test/dialect/test_dma.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_dma_memory_hierarchy.py`
  - `test/passes/test_multi_buffer.py`
  - `test/passes/test_registry.py`
  - `test/passes/test_template_name_constraints.py`
- latest main 同步带入 `95b2cfc1` 已合并存活记录与 symbol-buffer-hoist 相关文件；这些来自 `origin/main`，不是本任务新候选范围。最终 main commit 将包含完整 ancestry，任务记录与本任务代码/spec/test 均在同一合并链路中。
- 本任务不带入 `expectation/`、`.skills/`、`agents/standard/**`、`TODO.md` 或 `DONE.md`。

同步后合同验收与共享 gate：
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.dma`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260518-dma-ring-arch-token-multi-buffer:/home/lfr/kernelcode_generate python3 -m expectation.dialect.arch`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git diff --cached --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py -k 'nested_region_use or sibling_region_use'`：`2 passed, 13 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_arch.py test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_template_name_constraints.py`：`169 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：`8 passed, 1 warning`。
- `git diff --check`：exit 0。
- `git diff --cached --check`：exit 0。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。

生成物与禁止修改面：
- 本轮复核生成的 `.pytest_cache`、`kernel/dump` 与 `__pycache__` 已在任务 worktree 内清理。
- 未修改、复制、移动、新建或删除 `expectation/`；`.skills/` 与 `agents/standard/**` 保持空 diff。
- 主仓 `/home/lfr/kernelcode_generate` 当前仍有与本任务无关的本地文档改动 `ARCHITECTURE/project_architecture.md` 与 `docs/**`；本次 merge 不 staging、不覆盖这些路径。

full expectation / `expectation.pass` 口径：
- 本次 merge 不运行也不写 `python3 -m expectation` / `python3 -m expectation.pass` 通过。
- 继续保留 2026-05-18 22:14 架构裁定：full expectation / `expectation.pass` 的 clean main 外部红点不作为本轮直接阻断，也不作为本任务通过依据；若后续失败家族扩大到本候选直接范围，必须回 execute 或请求架构裁定。

结论：
- T-20260518-e79bde42 在 latest `origin/main@95b2cfc1` 同步后已完成冲突机械合并、直接合同验收、共享 pytest gate、diff check 与敏感目录核对。
- 最小阻断项：无。
- 可提交 merge commit，fast-forward 合入主仓 `main`，push 后执行 `-done` 并清理完成 worktree / branch。最终提交号按合并规范在合并后回报，不再追加记录提交。
