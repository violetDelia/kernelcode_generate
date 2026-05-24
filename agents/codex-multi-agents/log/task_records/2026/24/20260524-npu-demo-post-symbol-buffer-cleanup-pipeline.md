时间：2026-05-24 21:06 +0800
经办人：神秘人
任务：npu-demo-post-symbol-buffer-cleanup-pipeline / 管理员创建
任务目标：按 ARCHITECTURE/plan/npu_demo_post_symbol_buffer_cleanup_pipeline_green_plan.md 创建唯一计划级 execute，调整 npu-demo-lowering 第一段 SymbolBufferHoistPass 后的 cleanup 三联 pass，并完成 spec、实现、测试、主仓只读 expectation 合同验收与敏感目录门禁。
改动：已创建任务 worktree /home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline，基线为 origin/main@6bd6e5d9782f92261741a8d46abddd6fd3371617；本记录用于任务链后续 execute/review/archive_acceptance/merge 追加。
验证：已只读核对计划状态为“下发前架构通过 / 用户已确认下发 / 可通知管理员创建唯一计划级 execute”；worktree 当前 git status --short 无输出，HEAD 与 origin/main 短哈希均为 6bd6e5d9。管理员不执行 pytest/expectation。
自检：任务目标为可执行动作，计划书和用户下发口径均明确；禁止修改面为 expectation/.skills/agents/standard，expectation.pass.pipeline.npu_demo_lowering 只作为主仓只读合同真源；计划级任务后续必须 execute -> review -> archive_acceptance -> merge。
结论：可通过任务脚本创建并分发唯一计划级 execute。

时间：2026-05-24 22:45 +0800
经办人：小李飞刀
任务：T-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline / execute
执行前阅读：
- 已读取个人提示词、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读取主仓只读计划书 `ARCHITECTURE/plan/npu_demo_post_symbol_buffer_cleanup_pipeline_green_plan.md`，确认用户已确认下发，execute 候选 diff 中 `expectation/.skills/agents/standard` 必须为空。
- 已核对 worktree：`/home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline`，HEAD=`6bd6e5d9782f92261741a8d46abddd6fd3371617`，初始仅本任务记录为 untracked。
最小功能闭环：
- `kernel_gen/pipeline/npu_demo_lowering.py`：在第一段 `SymbolBufferHoistPass()` 后新增 `SymbolLoopHoistPass() -> HoistDmaAliasOpsPass() -> CanonicalizePass()`，未新增 option、registry 名称或公开 API。
- `spec/pass/pipeline/npu_demo_lowering.md`：公开顺序从 28 阶段更新为 31 阶段，写清第一段 post-buffer cleanup 不插入 CSE，`tile-analysis` 后移到 cleanup 后。
- `test/passes/pipeline/test_npu_demo_lowering.py`：更新 exact order、dump index、pass marker 相邻关系和 occurrence，锁定 `symbol-buffer-hoist(1) -> symbol-loop-hoist(2) -> hoist-dma-alias-ops(2) -> canonicalize(3) -> tile-analysis`；后续 transform 段 occurrence 同步后移。
改动文件：
- `kernel_gen/pipeline/npu_demo_lowering.py`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `agents/codex-multi-agents/log/task_records/2026/24/20260524-npu-demo-post-symbol-buffer-cleanup-pipeline.md`
Diff 反推自测：
- `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py`：exit=0。
- `python3 -m compileall -q kernel_gen/pipeline/npu_demo_lowering.py`：exit=0。
- `pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`10 passed, 1 warning`。
合同验收资产：
- 主仓只读 expectation sha256：`8251fc981115eb145571fe56e2c076859fa1d9a94084b5ff6f8370f6e2ea2529  /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
- import proof：`/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`，`spec.origin=/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
静态扫描与禁止修改面：
- `git diff --check`：exit=0。
- `git status --short -- expectation .skills agents/standard`：无输出。
- `rg -n "pm\\.add_pass\\((LowerDmaMemoryHierarchyPass|MultiBufferPass)|from kernel_gen\\.passes.*multi_buffer|from kernel_gen\\.passes.*dma_memory_hierarchy" kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py spec/pass/pipeline/npu_demo_lowering.md`：exit=1，无命中，确认未把 standalone `lower-dma-memory-hierarchy` 或 `multi-buffer` 接入顶层 pipeline。
- `rg -n "lower-dma-memory-hierarchy|multi-buffer" ...` 仅命中 spec/test 中对 transform 间接执行和负向断言的说明，不是新增顶层 pass。
自检：
- 接口：未新增、删除、重命名公开 API；builder 签名和 registry 名称保持不变。
- 边界：新增三联 cleanup 位于第一段 `SymbolBufferHoistPass` 后，未改变 transform 后 cleanup、memory-pool、arch、attach、outline、template-name 相对后段语义。
- 异常：options 校验路径未改，未知 option 公开错误语义不变。
- 兼容性：`expectation.pass.pipeline.npu_demo_lowering` 已在 worktree-first PYTHONPATH 下通过，主仓 expectation 未写入候选 diff。
- 实现遗漏：已同步实现、spec、pytest 和任务记录；未改计划外 pass。
- 冗余：未新增 helper、wrapper 或重复函数层；仅增加三个 pass 实例化调用和对应文档/测试。
- 注释准确性：文件级说明和函数说明的 pipeline 顺序已同步新顺序。
- 复用与函数粒度：复用现有 pass，不新增私有 helper，不跨文件调用非公开 API。
- 输入/输出校验：builder target/unknown option 校验保持原实现。
- 并发/资源/性能：仅调整 pass 顺序和数量，无共享状态或资源生命周期新增。
- 测试有效性：Diff 反推 pytest 同时覆盖 exact pass order、真实 dump marker、主链路 gen_kernel 和负向 marker。
减法检查：
- 未新增公开 API、registry option、pass name、helper 文件或兼容 shim。
- 未把 CSE 插入第一段 post-buffer cleanup，保持用户确认的三联 `symbol-loop-hoist -> hoist-dma-alias-ops -> canonicalize`。
- 未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
结论：
- execute 范围已闭合，候选 diff 清单明确，Diff 反推自测与主仓只读 expectation 均通过，可流转 review。

时间：2026-05-24 23:03 +0800
经办人：提莫炖蘑菇
任务：T-20260524-ebee86b8 / npu-demo-post-symbol-buffer-cleanup-pipeline / review
任务目标：审查第一段 SymbolBufferHoistPass 后新增 SymbolLoopHoistPass -> HoistDmaAliasOpsPass -> CanonicalizePass 的 spec、实现、pytest、Diff 反推自测、主仓只读 expectation 与敏感目录门禁。
最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline`。
- 审查前执行 `git fetch origin --prune`：`HEAD=6bd6e5d9782f92261741a8d46abddd6fd3371617`、`origin/main=95d9a8b20a8cb9765e5cfd51b7f0ba79fe373aca`、`merge-base=6bd6e5d9782f92261741a8d46abddd6fd3371617`、ahead/behind=`0/5`。
- 先用 latest `origin/main@95d9a8b20a8cb9765e5cfd51b7f0ba79fe373aca` 构造临时候选 `/tmp/kcg-review-npu-demo-post-symbol-buffer-49BKLb` 并应用本任务三文件 diff，patch sha256=`db7be0a5c2a13be5ea66c798c20223adadf1a7d5a00f81387c5620b98cad58fe`，确认 latest 主线兼容。
- 精确核对本任务三文件与 `HEAD..origin/main` 无重叠后，原任务 worktree 执行 `git merge --ff-only origin/main` 成功；对齐后 `HEAD=origin/main=merge-base=95d9a8b20a8cb9765e5cfd51b7f0ba79fe373aca`，ahead/behind=`0/0`，任务 diff 保留为三文件与本任务记录。
审查范围：
- 计划书：主仓只读 `ARCHITECTURE/plan/npu_demo_post_symbol_buffer_cleanup_pipeline_green_plan.md`。
- 被审 diff：`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`、本任务记录。
- 合同真源：主仓只读 `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`，sha256=`8251fc981115eb145571fe56e2c076859fa1d9a94084b5ff6f8370f6e2ea2529`。
审查结论：
- `kernel_gen/pipeline/npu_demo_lowering.py` 仅在第一段 `SymbolBufferHoistPass()` 后新增 `SymbolLoopHoistPass()`、`HoistDmaAliasOpsPass()`、`CanonicalizePass()` 三个既有公开 pass；未新增 builder 参数、registry 名称、pipeline option 或公开错误文本。
- `spec/pass/pipeline/npu_demo_lowering.md` 已同步 31 项公开顺序，明确第一段 post-buffer cleanup 不插入 CSE，顶层仍不接入 standalone `lower-dma-memory-hierarchy` 或 `multi-buffer`。
- `test/passes/pipeline/test_npu_demo_lowering.py` 已同步 exact order、dump marker、occurrence 和相邻关系断言，覆盖 `symbol-buffer-hoist -> symbol-loop-hoist -> hoist-dma-alias-ops -> canonicalize -> tile-analysis`，并保留 transform 后 cleanup 与 memory-pool 后段断言。
Diff 反推审查：
- `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py && python3 -m compileall -q kernel_gen/pipeline test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- import proof：`expectation.pass.pipeline.npu_demo_lowering -> /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`；`kernel_gen.pipeline.npu_demo_lowering -> /home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline/kernel_gen/pipeline/npu_demo_lowering.py`。
- `git diff --check && git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：无输出；`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：无输出；`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：无输出。
- `rg -n "lower-dma-memory-hierarchy|multi-buffer" kernel_gen/pipeline/npu_demo_lowering.py spec/pass/pipeline/npu_demo_lowering.md test/passes/pipeline/test_npu_demo_lowering.py`：命中均为 spec/test 中 transform 间接执行说明或顶层不接入断言，未命中新增顶层 `pm.add_pass(...)`。
减法审查：
- 本轮替代的是旧的 `MemoryPlanPass -> SymbolBufferHoistPass -> TileAnalysisPass` 直接相邻顺序；已由 `MemoryPlanPass -> SymbolBufferHoistPass -> SymbolLoopHoistPass -> HoistDmaAliasOpsPass -> CanonicalizePass -> TileAnalysisPass` 替代。
- 未删除旧 pass 能力；保留依据充分：三个新增阶段均为既有公开 pass，第二段 transform 后 cleanup、memory-pool、arch、attach、outline、template-name 相对后段语义保持不变。
- 未新增或改动 `private callable`；AST 核对 `kernel_gen/pipeline/npu_demo_lowering.py` 无 private callable、无嵌套函数；`test/passes/pipeline/test_npu_demo_lowering.py` 存量 private helper 未新增，且未发现 private callable 调用 private callable。
- 未新增跨文件非公开 API 调用、ctx 能力探测、`object` 签名或非装饰器嵌套函数。
执行记录核对：
- execute 已记录执行前阅读、最小功能闭环、Diff 反推自测、主仓只读 expectation import proof、静态扫描与禁止修改面。
- review 已在 latest `origin/main` 同步现场复跑对应 pytest、合同验收和静态门禁。
自检：
- 已读取个人提示词、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`、计划书正文、任务记录与实际 diff。
- 已核对公开 API 用户确认来源：本计划只改变公开 pipeline 顺序，计划记录用户 2026-05-24 已确认；未新增函数 / class / registry / option / 错误文本。
- 已核对测试有效性：order pytest 通过 monkeypatch 公开 `apply(...)` 入口锁定完整顺序；dump gate 按 marker 和 occurrence 证明新增 cleanup 的实际阶段位置，不只依赖固定编号。
- 已核对 `expectation/`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md` 无候选 diff。
findings：无阻断项。
结论：通过。该任务为计划级 execute 落地后的 review，通过后应进入 `archive_acceptance / 计划书入档验收`，不得直接进入 merge。

时间：2026-05-24 23:06 +0800
经办人：提莫炖蘑菇
任务：T-20260524-ebee86b8 / npu-demo-post-symbol-buffer-cleanup-pipeline / archive_acceptance
任务目标：核对计划级任务 review 通过后的最新同步现场、review 结论、Diff 反推审查、主仓只读 expectation 合同验收、敏感目录空 diff、任务记录完整性和可入档证据。
最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline`。
- `git fetch origin --prune` 后 `HEAD=origin/main=merge-base=95d9a8b20a8cb9765e5cfd51b7f0ba79fe373aca`，ahead/behind=`0/0`。
- 当前候选 diff：`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`、`agents/codex-multi-agents/log/task_records/2026/24/20260524-npu-demo-post-symbol-buffer-cleanup-pipeline.md`。
入档验收核对：
- review 记录已写入本文件，结论为通过，包含 latest 主线同步、临时候选 latest 验证、实际 diff、Diff 反推审查、主仓只读 expectation import proof、敏感目录空 diff、减法审查和自检。
- execute 与 review 均记录未新增公开 API / registry / option / 错误文本，只改变用户已确认的公开 pipeline 顺序。
- 任务记录作为 untracked 候选文件存在：`git ls-files --others --exclude-standard -- agents/codex-multi-agents/log/task_records/2026/24/20260524-npu-demo-post-symbol-buffer-cleanup-pipeline.md` 输出本记录路径；合并阶段必须与代码/spec/test 同批纳入。
计划必过验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- import proof：`expectation.pass.pipeline.npu_demo_lowering -> /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`；`kernel_gen.pipeline.npu_demo_lowering -> /home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline/kernel_gen/pipeline/npu_demo_lowering.py`。
补充验证：
- `pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`10 passed, 1 warning`。
- `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py && python3 -m compileall -q kernel_gen/pipeline test/passes/pipeline/test_npu_demo_lowering.py && git diff --check && git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：无输出；`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：无输出；`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：无输出。
自检：
- 已核对计划书状态、用户确认来源、execute 记录、review 记录、必过 expectation、Diff 反推测试与敏感目录门禁。
- 未修改 `expectation/`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 未发现需退回 execute 的缺口。
结论：archive_acceptance / 计划书入档验收通过。可进入 merge；merge 阶段必须只合入上述候选 diff，并保证任务记录与代码/spec/test 同批合入。

时间：2026-05-24 23:17 +0800
经办人：李白
任务：T-20260524-ebee86b8 / npu-demo-post-symbol-buffer-cleanup-pipeline / merge
执行前阅读：
- 已重新读取个人提示词、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`。
- 已核对本任务为计划级 merge，前序 `review` 与 `archive_acceptance / 计划书入档验收` 均已通过；本阶段只负责同步确认、候选范围复核、同批合入、推送与 `-done`。
最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline`。
- `HEAD=origin/main=merge-base=95d9a8b20a8cb9765e5cfd51b7f0ba79fe373aca`，分支 `task/npu-demo-post-symbol-buffer-cleanup-pipeline`。
- 主仓 `/home/lfr/kernelcode_generate` 初始 `HEAD=origin/main=95d9a8b20a8cb9765e5cfd51b7f0ba79fe373aca` 且 clean。
候选范围复核：
- `git diff --name-status` 仅包含：
  - `M kernel_gen/pipeline/npu_demo_lowering.py`
  - `M spec/pass/pipeline/npu_demo_lowering.md`
  - `M test/passes/pipeline/test_npu_demo_lowering.py`
- `git ls-files --others --exclude-standard` 仅包含：`agents/codex-multi-agents/log/task_records/2026/24/20260524-npu-demo-post-symbol-buffer-cleanup-pipeline.md`。
- 候选 diff 与任务目标一致；任务记录已作为 untracked 候选记录纳入本次同批合并范围。
真实 merge 门禁：
- `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py && python3 -m compileall -q kernel_gen/pipeline test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- 主仓只读 expectation hash：`8251fc981115eb145571fe56e2c076859fa1d9a94084b5ff6f8370f6e2ea2529  /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
- import proof：`expectation.pass.pipeline.npu_demo_lowering -> /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`；`kernel_gen.pipeline.npu_demo_lowering -> /home/lfr/kernelcode_generate/wt-20260524-npu-demo-post-symbol-buffer-cleanup-pipeline/kernel_gen/pipeline/npu_demo_lowering.py`。
- `git diff --check && git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`：无输出；`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`：无输出。
静态边界复核：
- AST 扫描 `kernel_gen/pipeline/npu_demo_lowering.py` 与 `test/passes/pipeline/test_npu_demo_lowering.py`：未发现新增非装饰器嵌套函数。
- `rg` 扫描未发现 `ctx` 能力探测、`object` 签名、`pm.add_pass(LowerDmaMemoryHierarchyPass|MultiBufferPass)`；`lower-dma-memory-hierarchy` / `multi-buffer` 命中仅为 spec/test 说明与负向断言，未作为顶层 pipeline pass 接入。
合并口径：
- 本次只合入 `kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py` 与本任务记录。
- 不纳入 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`ARCHITECTURE/plan` 或其它 worktree/cache 改动。
结论：
- review 与 archive_acceptance 结论齐全；latest main 同步无冲突；真实门禁通过；候选范围明确，可提交、推送并执行 `-done`。
