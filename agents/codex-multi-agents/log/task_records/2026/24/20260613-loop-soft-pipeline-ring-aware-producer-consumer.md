时间：2026-06-13 13:29 +0800
经办人：金铲铲大作战
任务：T-20260613-bac54fd8 / loop-soft-pipeline-ring-aware-producer-consumer
任务目标：实现 `LoopSoftPipelinePass`（registry=`loop-soft-pipeline`，module=`kernel_gen.passes.schedule.loop_soft_pipeline`），扩展 `ProducerConsumerAnalysisPass` 的 ring-aware current/advance 分析和 `loop_first` / `loop_carried` / `after_loop` 标注，更新 spec / pytest / pipeline 顺序，并完成计划列出的 pytest、dump 与两个 expectation 合同验收；execute 完成后按计划级链路续接 review。

## 执行前阅读记录

- 已读根目录 `AGENTS.md`、角色提示词 `agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/expectation任务规则.md`。
- 已读计划书 `ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md` 与参考 `ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md`。
- 已读相关实现 / spec / 测试：`kernel_gen/passes/producer_consumer_analysis.py`、`kernel_gen/passes/registry.py`、`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/producer_consumer_analysis.md`、`spec/pass/registry.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/test_producer_consumer_analysis.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`。
- 已按只读合同资产口径运行并引用 `expectation.pass.loop_soft_pipeline` 与 `expectation.pass.producer_consumer_analysis`；未修改、新建、移动、删除或重命名 `expectation/`。
- `TODO.md` 复查显示本任务为 `execute / 金铲铲大作战 / 进行中`；任务记录文件执行前不存在，本条为本任务 execute 正式补建记录。
- 执行前 index 中仅本任务已 staged 计划 / 参考证据：`ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md`、`ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md`；未混入其它既有 staged 计划。

## 计划内小任务卡核对

- `LoopSoftPipelinePass` 已落在 canonical module `kernel_gen.passes.schedule.loop_soft_pipeline`，registry name 为 `loop-soft-pipeline`。
- 仅新增计划明确的公开 API：`class LoopSoftPipelinePass(fold: bool = True)`、`LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass`、`LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`。
- 未新增 package re-export，未新增 `LoopSoftPipelinePassError`，未新增共享公开 `ring_cursor_analysis` API。
- `ProducerConsumerAnalysisPass` 已扩展 ring-aware current/advance 事件分析，支持 `loop_first_productor` / `loop_first_consumer`、`loop_carried_productor` / `loop_carried_consumer` 与 `after_loop_*` 标注。
- pipeline 顺序已更新为 `MultiBufferAnalysisPass -> MultiBufferApplyPass -> LoopSoftPipelinePass -> ProducerConsumerAnalysisPass -> MemoryPoolPass`，仅通过 spec / pytest / dump 验收，不运行被排除的 pipeline expectation。
- unsupported 与静态 zero-trip 保持 no-op / 现状；动态正 trip soft pipeline 重写按最后一个合法迭代起点处理 tail。

## 最小功能闭环

- 新增 `kernel_gen/passes/schedule/loop_soft_pipeline.py`：识别 direct `SymbolForOp` 中 ring current / advance 包围的 ping-pong producer-consumer 结构，把 ring preload 拆成 prologue、steady next-preload 与 epilogue；清理 stale producer-consumer event attrs。
- `LoopSoftPipelinePass` 使用已注册 `symbol.const` / `symbol.sub` / `symbol.floordiv` / `symbol.mul` / `symbol.add` 表达动态边界，避免生成未注册自定义 op。
- tail 边界使用最后合法迭代起点：`start + ((end - start - 1) floordiv step) * step`；静态非正 trip / unsupported 保持原 IR。
- preload 闭包包含 `MemoryEffectKind.WRITE` 写入 copy source 的 side-effect producer（例如 `dma.deslice`），避免只按 SSA 依赖漏克隆源数据写入。
- `ProducerConsumerAnalysisPass` 使用 ring root 与 MemoryEffect READ/WRITE 关系识别 loop-first、loop-carried 与 after-loop consumer；不把 `DmaAdvanceRingOp` 本身标为 event。
- 更新 registry、pipeline、spec 和 pytest，测试只通过公开 API 与 parser / registry / pipeline 入口验证，不调用跨文件非公开 helper。

## 改动摘要

- 新增：`kernel_gen/passes/schedule/loop_soft_pipeline.py`、`spec/pass/loop_soft_pipeline.md`、`test/passes/schedule/test_loop_soft_pipeline.py`。
- 修改：`kernel_gen/passes/producer_consumer_analysis.py`、`kernel_gen/passes/registry.py`、`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/producer_consumer_analysis.md`、`spec/pass/registry.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/test_producer_consumer_analysis.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`。
- 纳入候选证据：`ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md`、`ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md`。

## 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py test/passes/test_producer_consumer_analysis.py test/passes/test_registry.py`
  - 结果：退出码 0，`81 passed, 1 warning`。
  - 锁定：loop-soft-pipeline public API / no-op 边界 / preload source writer 克隆 / stale event 清理 / producer-consumer ring event / registry 构建和无 package re-export。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - 结果：退出码 0，`11 passed, 1 warning`。
  - 锁定：npu_demo lowering pipeline 中 `loop-soft-pipeline` 位于 `multi-buffer-apply` 之后、`producer-consumer-analysis` 与 `memory-pool` 之前，并检查 dump stage marker 顺序。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
  - 结果：退出码 0，`7 passed`。
  - 锁定：新增 / 改动 private callable 不跨文件使用、不调用其它 private callable，错误类型不绕过静态门禁。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - 结果：退出码 0。
  - 摘要：运行动态 symbolic / random / tail 场景，输出包含 `shape=(M=179,K=177,N=254)`、`selected_tile=(72, 88, 56)`、`tail=True`；`absent_bias max_abs_diff=2.47955322265625e-05`，`present_bias max_abs_diff=2.6702880859375e-05`。
  - 锁定：dump 级 pipeline 顺序、动态 tail soft pipeline 边界、side-effect preload writer 克隆后的 runtime 正确性。
- `git diff --check`
  - 结果：退出码 0，无输出。
- `git diff --cached --check`
  - 结果：退出码 0，无输出。

## 合同验收

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.loop_soft_pipeline`
  - 结果：退出码 0，无 stdout。
  - 说明：从主仓读取 expectation 合同资产，优先使用本 worktree 的 `kernel_gen` 实现；未修改 expectation。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - 结果：退出码 0。
  - stdout 摘要：`after_if`、`after_loop`、`if_branch`、`loop_body`、`memory_effect_alias` 等 10 条正例全部通过。
  - 说明：从主仓读取 expectation 合同资产，优先使用本 worktree 的 `kernel_gen` 实现；未修改 expectation。
- `expectation/pass/pipeline/npu_demo_lowering.py`：按任务边界排除，未运行、不引用为本轮必过项、未进入候选。

## Diff 反推自测

- `kernel_gen/passes/schedule/loop_soft_pipeline.py`、`spec/pass/loop_soft_pipeline.md`、`test/passes/schedule/test_loop_soft_pipeline.py`：由 `test/passes/schedule/test_loop_soft_pipeline.py` 和 `expectation.pass.loop_soft_pipeline` 覆盖 public API、重写结构、no-op、stale attr 清理、source writer 克隆和未知 option。
- `kernel_gen/passes/producer_consumer_analysis.py`、`spec/pass/producer_consumer_analysis.md`、`test/passes/test_producer_consumer_analysis.py`：由 `test/passes/test_producer_consumer_analysis.py` 和 `expectation.pass.producer_consumer_analysis` 覆盖 ring-aware event 与既有 producer-consumer 合同。
- `kernel_gen/passes/registry.py`、`spec/pass/registry.md`、`test/passes/test_registry.py`：由 `test/passes/test_registry.py` 覆盖 built-in registry name、`fold=False` option 和无 package re-export。
- `kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`：由 pipeline pytest 与 `kernel/matmul/inputs_dynamic_tile_dynamic.py` dump/runtime 验收覆盖顺序和 tail 场景。
- private API / error gate：由 `test/repo_conformance/test_private_api_boundaries.py` 与 `test/tools/test_kernel_code_error_static_gate.py` 覆盖。

## 减法检查

- 新增 / 改动 private callable：
  - `kernel_gen/passes/schedule/loop_soft_pipeline.py`：`_LoopSoftPipelineCandidate`、`_LoopSoftPipelineRewrite`；其中 `_LoopSoftPipelineRewrite` 的复用逻辑保留为类内公开命名静态方法，避免 changed private callable 调用 private callable，同时保持候选识别 / 克隆 / 边界构造集中管理。
  - `kernel_gen/passes/producer_consumer_analysis.py`：`_RingEventSpec`、`_RingAwareAnalysis`；用于 ring root、MemoryEffect 访问和 loop event 关系聚合，无法内联到 `apply` 而不显著降低可读性。
  - 测试侧：`_run_loop_soft_pipeline`、`_ring_preload_ir`、`_record_loop_soft_pipeline` 均满足有效行数约束，且只服务本文件测试。
- 已替代旧逻辑：
  - 初版未注册 `loop-soft-pipeline.symbol.*` 边界 op 已替换为已注册 `symbol.*` op；旧路径未保留。
  - 初版仅 SSA 依赖收集 preload 已补强为包含 `MemoryEffectKind.WRITE` source writer；旧漏收集路径未保留。
  - 初版 epilogue `end - step` 已替换为最后合法迭代起点公式，覆盖动态 tail；旧公式未保留。
  - `ProducerConsumerAnalysisPass` 初版 private `_apply_to_func` 已内联回公开 `apply`，避免 changed private callable 调用 private helper。
- 保留旧逻辑依据：既有 static user、if branch、loop body、after loop 和 MemoryEffect alias 分析仍是当前 producer-consumer 合同的一部分，已由原 pytest 与 expectation 继续覆盖。
- 删除 / 未删除验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py` 通过；`rg -n 'LoopSoftPipelinePass' kernel_gen/passes/__init__.py kernel_gen/passes/schedule 2>/dev/null || true` 仅显示 canonical module 内引用，无 package re-export。

## 敏感范围核对

- `git diff -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'`
  - 结果：仅显示 `!! kernel/dump/`；`expectation/pass/loop_soft_pipeline`、`expectation/pass/producer_consumer_analysis`、`expectation/pass/pipeline/npu_demo_lowering.py` 无 staged / unstaged diff。
- `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md` 未修改。

## 自检

- 接口：仅新增计划 / spec 明确的 `LoopSoftPipelinePass` canonical public API；无 package re-export、无新 public error、无共享 public ring cursor API。
- 边界：unsupported / static zero-trip no-op，动态正 trip 处理 tail；unknown option 走 `KernelCodeError(CONTRACT, PASS, ...)`。
- 兼容：pipeline 顺序通过 pytest / dump 验证，producer-consumer 既有合同继续通过。
- 实现：新增文件具备文件级 `功能说明 / API 列表 / 使用示例 / 关联文件`，改动功能文件同步更新文件级说明和函数注释；未使用跨文件非公开 helper。
- 冗余 / 复用 / 粒度：重写、边界构造、ring event 分析保持在当前文件内服务公开 API；旧失败路径已删除。
- 输入 / 输出校验：registry option、fold option、IR unsupported/no-op、event attr 清理均有测试。
- 并发 / 资源 / 性能：本 pass 为单 module IR rewrite，无共享全局状态；动态边界 op 数量与 loop 重写规模线性相关。
- 测试有效性：pytest、dump、expectation 和静态门禁均能覆盖本轮 diff；expectation 仅作合同验收，不替代 Diff 反推测试。

## 结论

execute 实现、spec、pytest、dump、合同验收、Diff 反推自测、减法检查和敏感范围核对已完成；下一步按计划级链路使用 `-next -type review -auto` 续接 review。

时间：2026-06-13 13:32 +0800
经办人：金铲铲大作战
任务：T-20260613-bac54fd8 / 暂存后复查
任务目标：在 execute 候选暂存后复核 staged 范围、diff check 和敏感范围。
改动：已暂存本任务计划 / 参考、实现、spec、测试与任务记录；未暂存 `expectation/`、`.skills/`、共享状态文件或 `kernel/dump/`。
验证：
- `git diff --cached --name-only`
  - 结果：仅包含本任务候选：计划、参考、任务记录、`kernel_gen/passes/schedule/loop_soft_pipeline.py`、producer-consumer / registry / pipeline 实现、对应 spec 与 pytest。
- `git diff --check`
  - 结果：退出码 0，无输出。
- `git diff --cached --check`
  - 结果：退出码 0，无输出。
- `git diff --cached -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'`
  - 结果：仅显示 `!! kernel/dump/`。
自检：暂存范围与任务边界一致；计划 / 参考为本任务证据，未混入其它计划；`expectation` 仍为只读合同资产且未进入 staged / unstaged diff。
结论：候选暂存复查通过，可以执行 `-next -type review -auto`。

时间：2026-06-13 13:34 +0800
经办人：金铲铲大作战
任务：T-20260613-bac54fd8 / execute -> review 标准流转补记
任务目标：记录本次 execute 完成后的 `-next -type review -auto` 流转、脚本输出、状态复查、talk 复查、diff check、敏感范围和自检。
改动：仅追加任务记录；实现 / spec / 测试候选未再改动；未进入 `archive_acceptance` 或 `merge`。
验证：
- 实际流转命令：
```bash
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file "/home/lfr/kernelcode_generate/TODO.md" \
  -next \
  -task_id "T-20260613-bac54fd8" \
  -from "金铲铲大作战" \
  -type "review" \
  -message "review；任务目标：审查 loop-soft-pipeline 与 ring-aware producer-consumer 的公开 API、实现、spec、pytest、dump、expectation 合同验收、Diff 反推自测、减法检查和敏感范围；任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md。计划级链路为 execute -> review -> archive_acceptance -> merge/归档。" \
  -agents-list "/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md" \
  -auto
```
- 完整脚本输出：
```text
OK: next T-20260613-bac54fd8
OK: replace 金铲铲大作战 状态
OK: auto-dispatch T-20260613-bac54fd8 -> 不要啊教练
OK: replace 不要啊教练 状态
OK: talk 金铲铲大作战 -> 不要啊教练 (不要啊教练)
OK: talk 金铲铲大作战 -> 神秘人 (神秘人)
```
- `TODO.md` 复查：
  - `T-20260613-bac54fd8` 已为 `review / 不要啊教练 / 进行中`。
- `agents/codex-multi-agents/agents-lists.md` 复查：
  - `金铲铲大作战` 为 `free`。
  - `不要啊教练` 为 `busy`。
- `agents/codex-multi-agents/log/talk.log` 复查：
  - 包含 `@金铲铲大作战向@不要啊教练发起会话` 的 review 交接消息，写明 worktree、计划书、记录文件和计划级链路。
  - 包含 `@金铲铲大作战向@神秘人发起会话: 任务 T-20260613-bac54fd8 已完成当前阶段，已回到任务列表；新任务类型=review，已经指派给-> 不要啊教练。`
- `git diff --check`
  - 结果：退出码 0，无输出。
- `git diff --cached --check`
  - 结果：退出码 0，无输出。
- `git diff --cached -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'`
  - 结果：仅显示 `!! kernel/dump/`。
自检：本条仅补齐标准流转记录并暂存，不修改实现 / spec / 测试 / 计划验收结论；未改任务状态文件，任务状态由 `-next` 标准脚本完成；未进入 `archive_acceptance` 或 `merge`；`expectation/pass/loop_soft_pipeline`、`expectation/pass/producer_consumer_analysis`、`expectation/pass/pipeline/npu_demo_lowering.py` 均未进入 staged / unstaged diff。
结论：execute -> review 标准流转完成，当前接手人为 `不要啊教练`，等待 review 结论。

时间：2026-06-13 13:36 +0800
经办人：金铲铲大作战
任务：T-20260613-bac54fd8 / execute -> review 补记后暂存复查
任务目标：按管理员要求确认 13:32 之后标准流转补记已在任务记录尾部补齐并暂存，且未重新执行 `-next`、未改任务状态、未进入 `archive_acceptance` 或 `merge`。
改动：仅补任务记录尾部；未改实现 / spec / test / 计划验收结论。
验证：
- `TODO.md`：`T-20260613-bac54fd8` 为 `review / 不要啊教练 / 进行中`。
- `agents/codex-multi-agents/agents-lists.md`：`不要啊教练` 为 `busy`，`金铲铲大作战` 为 `free`。
- `agents/codex-multi-agents/log/talk.log`：包含交接给 `不要啊教练` 的 review 消息与回报 `神秘人` 的管理员消息；也包含管理员要求本次只补记录、不要重新执行 `-next` 的指令。
- `git diff --check`
  - 结果：退出码 0，无输出。
- `git diff --cached --check`
  - 结果：退出码 0，无输出。
- `git diff -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git diff --cached -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'`
  - 结果：仅显示 `!! kernel/dump/`；三个 expectation 路径均未进入 staged / unstaged diff。
自检：仅补记录并暂存；未重新执行 `-next`；未改 TODO / agents-list；未改实现、spec、测试或计划验收结论；未进入 `archive_acceptance` 或 `merge`。
结论：标准流转补记和补记后复查已完成，等待管理员核对通过后由 `不要啊教练` 继续 review。

时间：2026-06-13 13:43 +0800
经办人：不要啊教练
任务：T-20260613-bac54fd8 / review：loop-soft-pipeline-ring-aware-producer-consumer
任务目标：审查 loop-soft-pipeline 与 ring-aware producer-consumer 的公开 API、实现、spec、pytest、dump、expectation 合同验收、Diff 反推自测、减法检查和敏感范围；计划级 review 通过后才可续接 archive_acceptance，不得直接 merge。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer`。
- 已执行 `git fetch origin main --prune`，输出：`From github.com:violetDelia/kernelcode_generate` / `* branch main -> FETCH_HEAD`。
- `HEAD=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `origin/main=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `merge-base HEAD origin/main=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `git rev-list --left-right --count HEAD...origin/main` -> `0 0`，未发现 latest main 交叉覆盖风险。
- 当前 TODO 为 `review / 不要啊教练 / 进行中`；agents-list 显示 `不要啊教练=busy`、`金铲铲大作战=free`。
- 已确认 2026-06-13 13:34 / 13:36 的 execute -> review 标准流转补记在任务记录尾部，且管理员已核对通过。

发现：
- 阻断 1：[`kernel_gen/passes/schedule/loop_soft_pipeline.py`](kernel_gen/passes/schedule/loop_soft_pipeline.py) 第 633-672 行对所有正 trip 候选都生成 steady `symbol.for`，[`kernel_gen/passes/producer_consumer_analysis.py`](kernel_gen/passes/producer_consumer_analysis.py) 第 287-349 行只要看到该 syntactic loop 就写 `loop_first_*` / `loop_carried_*` / `after_loop_*`。这违反计划书 Q4：`N == 1` 且 K 维正数时必须退化为 `prologue copy -> epilogue matmul`，使用普通 `productor` / `consumer`，不能产生 loop-carried 边。复现方式：把测试 helper `_ring_preload_ir()` 中静态 K loop 从 `0..8 step 4` 改成 `0..4 step 4` 后运行 `LoopSoftPipelinePass` 再运行 `ProducerConsumerAnalysisPass`；实际输出含静态 zero-trip steady loop `symbol.for ... end = 0`，prologue copy 被标 `loop_first_productor`，dead steady loop 内 copy 被标 `loop_carried_productor` / `after_loop_productor`，epilogue matmul 被标多个 `after_loop_consumer`。影响：单 tile 场景的公开 producer-consumer attr 语义错误，且现有 pytest / expectation 未覆盖该已确认用户决策边界。最小返工动作：为 `LoopSoftPipelinePass` 增加可证明 single-trip 分支，只生成 prologue preload 与 epilogue matmul，不生成 steady `symbol.for` 或 loop-carried preload；同步 `spec/pass/loop_soft_pipeline.md` 与 `spec/pass/producer_consumer_analysis.md`，补 `test_loop_soft_pipeline_*single_tile*` 和 producer-consumer 单 tile 断言，验收时确认输出只含普通 `productor` / `consumer`，不含 `loop_first` / `loop_carried` / `after_loop`。
- 阻断 2：[`kernel_gen/passes/schedule/loop_soft_pipeline.py`](kernel_gen/passes/schedule/loop_soft_pipeline.py) 第 310-329 行在无法静态证明 trip count 时直接返回 True，第 638-670 行随后无条件在 loop 前插入 prologue preload；[`spec/pass/loop_soft_pipeline.md`](spec/pass/loop_soft_pipeline.md) 第 80-84 行也把“动态边界无法静态证明为 zero-trip 时允许按结构合同尝试改写”写成公开合同。这与计划书 Q4b 冲突：`N == 0` 或无法证明至少存在一个 K tile，且当前 IR 无法构造保持语义的 guard 时，必须 no-op / 保持现状，不得生成无条件 prologue。影响：动态 K 维运行时为 0 tile 时，候选可能执行原 loop 不会执行的 prologue copy 与 epilogue matmul，改变语义；同时 spec 把未获用户确认的宽松动态行为固化成公开合同。最小返工动作：按计划收口动态边界，要么构造并测试保持语义的 guard，要么在无法证明 `N > 0` 时 no-op；同步修正 `spec/pass/loop_soft_pipeline.md`，补动态 zero/unknown-trip 回归测试和 dump/expectation 证据。

已核对通过项：
- `LoopSoftPipelinePass` canonical module 为 `kernel_gen.passes.schedule.loop_soft_pipeline`，未新增 package re-export；registry name 为 `loop-soft-pipeline`。
- 未新增共享公开 `ring_cursor_analysis` API，未新增 `LoopSoftPipelinePassError`。
- pipeline 顺序已接入 `MultiBufferAnalysisPass -> MultiBufferApplyPass -> LoopSoftPipelinePass -> ProducerConsumerAnalysisPass -> MemoryPoolPass`。
- `expectation/pass/pipeline/npu_demo_lowering.py` 未纳入本轮 expectation 修改或验收。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py test/passes/test_producer_consumer_analysis.py test/passes/test_registry.py` -> `81 passed, 1 warning`，退出码 0；但未覆盖 `N == 1` 正数退化和动态无法证明 `N > 0` 的 guard/no-op。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `11 passed, 1 warning`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py` -> `7 passed`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py` -> 退出码 0；输出含 `tail=True` 与 `absent_bias/present_bias max_abs_diff=3.4332275390625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.loop_soft_pipeline` -> 退出码 0，无 stdout。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis` -> 退出码 0；stdout 显示 after_if、after_loop、if_branch、loop_body、memory_effect_alias 等 10 条正例通过。
- 定向复现脚本：用 `test.passes.schedule.test_loop_soft_pipeline._ring_preload_ir()` 构造输入并把静态 loop 改为 `0..4 step 4`，依次运行 `LoopSoftPipelinePass(fold=False)` 与 `ProducerConsumerAnalysisPass(fold=False)` -> 退出码 0；实际输出含 `symbol.for ... end = #symbol.expr<0>`、`loop_first_productor`、`loop_carried_productor`、`after_loop_productor` 和 `after_loop_consumer`，证明阻断 1。
- `git diff --check` -> 无输出，退出码 0。
- `git diff --cached --check` -> 无输出，退出码 0。

Diff 反推审查：
- `kernel_gen/passes/schedule/loop_soft_pipeline.py` 与 `test/passes/schedule/test_loop_soft_pipeline.py`：现有测试覆盖一般 `0..8 step 4`、unsupported、static zero-trip、stale attr 和 source writer 克隆，但漏掉计划明确的 `0 < K <= TILE_K` 单 tile退化，以及动态无法证明 `N > 0` 的 guard/no-op。
- `kernel_gen/passes/producer_consumer_analysis.py` 与 `test/passes/test_producer_consumer_analysis.py`：现有 ring-aware 测试覆盖多 tile syntactic soft-pipeline，但未覆盖 single-trip 后只能普通 `productor/consumer` 的分类。
- `spec/pass/loop_soft_pipeline.md`：当前 no-op 边界与计划 Q4b 冲突，属于 spec 同步问题。
- `kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`：顺序与 dump marker 门禁复跑通过。
- `expectation` 单列为合同验收，不计入 Diff 反推测试。

减法审查：
- execute 记录写明删除了初版未注册 `loop-soft-pipeline.symbol.*`、旧 SSA-only preload 收集、旧 `end - step` 公式和 `_apply_to_func` private helper；当前 diff 中未见这些旧路径保留。
- 新增 private / 当前文件内部 helper 已由 private/KCE 门禁复跑通过；本轮阻断不是 private callable 边界，而是计划已确认的 single-trip / dynamic zero-trip 语义未收口。
- `rg -n 'LoopSoftPipelinePass' kernel_gen/passes/__init__.py kernel_gen/passes/schedule 2>/dev/null || true` 的执行人记录显示仅 canonical module 内引用，无 package re-export。

expectation 与敏感范围：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` -> 无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` -> 无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'` -> 仅显示 `!! kernel/dump/`；三个 expectation 路径未进入 staged / unstaged diff。

自检：
- 已读取根 `AGENTS.md`、`不要啊教练.prompt.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、计划书、execute 主体记录和 execute -> review 补记。
- 已先同步 latest main 并确认无分叉、无覆盖风险。
- 已读取实际 diff，核对公开 API、canonical path、registry、pipeline 顺序、spec、pytest、expectation 边界、private/KCE 和敏感范围。
- 当前存在 2 个可执行阻断项，结论不能通过；按计划级链路退回同一任务 execute 返工，不进入 archive_acceptance 或 merge。

结论：
- review 不通过。
- 下一步使用标准脚本 `-next -type execute -auto` 退回 execute，要求最小返工上述 2 项并补对应测试、spec、Diff 反推自测、合同验收和敏感范围记录。

时间：2026-06-13 13:46 +0800
经办人：不要啊教练
任务：T-20260613-bac54fd8 / review -> execute 标准流转记录
任务目标：按 review 不通过结论，把同一计划级任务退回 execute 返工；不进入 archive_acceptance 或 merge。

流转命令：

```bash
CODEX_MULTI_AGENTS_CONFIG=/home/lfr/kernelcode_generate/agents/codex-multi-agents/config/config.txt \
CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-bac54fd8 \
  -from "不要啊教练" \
  -type execute \
  -message "execute；任务目标：修复 T-20260613-bac54fd8 review 指出的 loop-soft-pipeline 最小阻断项：1）按用户 Q4 处理 N==1 且 K 维正数的 single-tile 退化，输出 prologue copy -> epilogue matmul，并让 producer-consumer 使用普通 productor/consumer，不产生 loop_first/loop_carried/after_loop；2）按 Q4b 处理无法证明 N>0 的动态边界，构造保持语义的 guard 或 no-op，不得无条件 prologue。同步 spec、pytest、dump/expectation 验收、Diff 反推自测、减法检查和敏感范围记录。任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md。计划级链路为 execute -> review -> archive_acceptance -> merge/归档。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260613-bac54fd8
OK: replace 不要啊教练 状态
OK: auto-dispatch T-20260613-bac54fd8 -> 睡觉小分队
OK: replace 睡觉小分队 状态
OK: talk 不要啊教练 -> 睡觉小分队 (睡觉小分队)
OK: talk 不要啊教练 -> 神秘人 (神秘人)
```

流转后复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing` 显示 `T-20260613-bac54fd8` 为 `execute / 睡觉小分队 / 进行中`。
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status` 显示 `睡觉小分队=busy`、`不要啊教练=free`。
- `tail -n 30 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log` 可见 `不要啊教练 -> 睡觉小分队` 的 execute 返工交接消息，以及 `不要啊教练 -> 神秘人` 的阶段完成回报。

Diff 与敏感范围复查：
- `git diff --check` -> 无输出，退出码 0。
- `git diff --cached --check` -> 无输出，退出码 0。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` -> 无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` -> 无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'` -> 仅显示 `!! kernel/dump/`；三个 expectation 路径未进入 staged / unstaged diff。

自检：
- 本段只记录 review -> execute 标准流转并暂存，不修改实现、spec、test、计划书、`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md` 或 `agents-list`。
- 已按不通过结论退回同一计划级任务 execute，没有进入 archive_acceptance 或 merge。
- 当前下一责任人为 `睡觉小分队`，`不要啊教练` 已 free。

时间：2026-06-13 14:03 +0800
经办人：睡觉小分队
任务：T-20260613-bac54fd8 / execute 返工收口
任务目标：修复 review 指出的 loop-soft-pipeline 两个最小阻断项：`N == 1` 且 K 维正数时退化为 prologue preload -> epilogue matmul，并保证 producer-consumer 使用普通 `productor` / `consumer`；无法静态证明 `N > 0` 的动态边界保持 no-op，不生成无条件 prologue。

执行前阅读记录：
- 已读取根 `AGENTS.md`、`agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
- 已复查 `TODO.md`：`T-20260613-bac54fd8` 为 `execute / 睡觉小分队 / 进行中`。
- 已复查 `agents/codex-multi-agents/agents-lists.md`：`睡觉小分队=busy`，`不要啊教练=free`。
- 已读取计划书 `ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md` 中 Q4 / Q4b、S2 / S3 约束：`0 < K <= TILE_K` single-tile 退化；不能证明正 trip 且未构造 guard 时 no-op。
- 已读取 review 不通过记录与 13:46 `review -> execute` 标准流转补记；管理员已核对通过并解除只读限制。
- 已读取并核对本轮相关实现 / spec / test：`kernel_gen/passes/schedule/loop_soft_pipeline.py`、`spec/pass/loop_soft_pipeline.md`、`spec/pass/producer_consumer_analysis.md`、`test/passes/schedule/test_loop_soft_pipeline.py`、`test/passes/test_producer_consumer_analysis.py`。

返工收口：
- 阻断 1（single-tile）：`LoopSoftPipelinePass` 将旧 `non_zero_trip` 改为静态 `trip_count` 判断；`trip_count == 1` 时只克隆 prologue preload 与 epilogue matmul，直接删除原 loop，不构造 boundary op、steady `symbol.for`、`dma.advance_ring` 或 preload next。新增 pytest `test_loop_soft_pipeline_single_tile_degenerates_to_prologue_epilogue` 锁定 `0..4 step 4` 输出 2 条 copy、1 条 matmul、0 个 `symbol.for`、无 `symbol.sub/add/advance_ring`。
- 阻断 1（producer-consumer）：新增 `_single_tile_prologue_epilogue_ir` 测试输入与 `test_producer_consumer_analysis_single_tile_prologue_epilogue_uses_main_attrs`，验证无 steady loop 的 prologue / epilogue 形态只写主 `productor=[0]`、`productor=[1]`、`consumer=[0, 1]`，不产生 `loop_first` / `loop_carried` / `after_loop`。
- 阻断 2（dynamic unknown）：`find_candidate` 仅接受 start / end / step 都可静态证明且 trip count > 0 的 loop；动态未知边界返回 no-op。新增 `test_loop_soft_pipeline_dynamic_unknown_trip_keeps_original_shape`，验证符号 `%k_end` 仍保留原 `symbol.for`，不插入 `symbol.sub/add` 或无条件 prologue。
- 同步 spec：`spec/pass/loop_soft_pipeline.md` 写明 static single-tile 退化、动态未知 trip no-op、不构造 guard；`spec/pass/producer_consumer_analysis.md` 写明 ring-aware `loop_*` 只适用于多 tile steady loop，single-tile prologue / epilogue 使用普通主 attr。

改动：
- 修改 `kernel_gen/passes/schedule/loop_soft_pipeline.py`：增加 `_LoopSoftPipelineCandidate.trip_count`；替换旧动态默认放行的 `non_zero_trip`；新增 single-tile rewrite 分支；更新文件级说明和相关函数注释。
- 修改 `test/passes/schedule/test_loop_soft_pipeline.py`：扩展 `_ring_preload_ir(single_trip=True, dynamic_end=True)`；新增 single-tile 与 dynamic unknown no-op 测试。
- 修改 `test/passes/test_producer_consumer_analysis.py`：新增 single-tile prologue / epilogue 形态测试。
- 修改 `spec/pass/loop_soft_pipeline.md` 与 `spec/pass/producer_consumer_analysis.md`：同步 Q4 / Q4b 公开行为与测试清单。
- 未修改 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md` 或 `agents-list`。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py`
  - 结果：退出码 0，`7 passed, 1 warning`。
  - 锁定：多 tile rewrite、single-tile 退化、动态 unknown no-op、unsupported / zero-trip no-op、旧 event 清理、source writer clone 和 unknown option。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_producer_consumer_analysis.py -k 'single_tile or ring_soft_pipeline_events'`
  - 结果：退出码 0，`2 passed, 10 deselected, 1 warning`。
  - 锁定：多 tile ring-aware `loop_*` 仍可用；single-tile prologue / epilogue 只用主 `productor` / `consumer`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py test/passes/test_producer_consumer_analysis.py test/passes/test_registry.py`
  - 结果：退出码 0，`84 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - 结果：退出码 0，`11 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
  - 首次结果：退出码 1，`testcurrent_diff_module_helpers_use_private_prefix_or_public_api` 失败；原因是新增测试 helper 曾命名为 `single_tile_prologue_epilogue_ir`。
  - 处理：改回仓库约定的 `_single_tile_prologue_epilogue_ir`，不新增公开 helper。
  - 复跑结果：退出码 0，`7 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - 结果：退出码 0；stdout 含 `multi_tile=True tail=True`，`absent_bias max_abs_diff=3.814697265625e-05`，`present_bias max_abs_diff=3.814697265625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.loop_soft_pipeline`
  - 结果：退出码 0，无 stdout。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - 结果：退出码 0；stdout 显示 after_if、after_loop、if_branch、loop_body、memory_effect_alias 等 10 条正例通过。
- `git diff --check`
  - 结果：退出码 0，无输出。
- `git diff --cached --check`
  - 结果：退出码 0，无输出。

Diff 反推自测：
- `kernel_gen/passes/schedule/loop_soft_pipeline.py` 与 `test/passes/schedule/test_loop_soft_pipeline.py`：反推运行 `test/passes/schedule/test_loop_soft_pipeline.py`，新增断言会在 single-tile 仍生成 steady loop、动态 unknown 仍无条件 prologue、旧 event 泄漏或 no-op 误改时失败。
- `test/passes/test_producer_consumer_analysis.py` 与 `spec/pass/producer_consumer_analysis.md`：反推运行 producer-consumer 全量与 `single_tile/ring_soft_pipeline_events` 定向用例，覆盖多 tile ring-aware 与 single-tile 主 attr 分流。
- `spec/pass/loop_soft_pipeline.md`：反推运行 loop-soft-pipeline 全量 pytest 与两个 expectation 合同验收，确认 spec 新行为有对应测试锁定且合同资产仍可通过。
- pipeline 相关既有 staged diff 未在本轮改动，但 dynamic unknown no-op 可能影响默认 lowering；反推运行 `test/passes/pipeline/test_npu_demo_lowering.py` 与 `kernel/matmul/inputs_dynamic_tile_dynamic.py`，均通过。
- `expectation` 单列为合同验收，不计入 Diff 反推测试；本轮未修改 expectation。

减法检查：
- 改动 / 新增 private callable 清单：
  - `_LoopSoftPipelineRewrite.static_trip_count(...)`：替代旧 `non_zero_trip(...)`；有效逻辑超过 5 行，用于集中表达 Q4b 静态证明口径；旧动态未知默认 True 逻辑已删除。
  - `_ring_preload_ir(...)`：已有测试 helper 扩展 `single_trip` / `dynamic_end` 分支；无跨文件非公开 API 调用，服务公开 `LoopSoftPipelinePass.apply(...)` 测试。
  - `_single_tile_prologue_epilogue_ir(...)`：新增测试 IR 构造 helper；模板内容超过 5 行，未调用其它 private callable，服务公开 `ProducerConsumerAnalysisPass.apply(...)` 测试。
- 被替代旧逻辑：删除 `non_zero_trip` 对动态边界默认放行的路径；删除 single-tile 复用多 tile boundary/steady loop 的行为。
- 保留旧逻辑依据：多 tile `build_steady_boundary`、preload / matmul clone、旧 event attr 清理和 ring-aware producer-consumer 逻辑仍是计划 S2 / S3 正路径，相关 pytest 与 expectation 已通过。
- 删除 / 未删除验证：
  - `rg -n "non_zero_trip|hasattr\\(|getattr\\(|callable\\(getattr|LoopSoftPipelinePassError" kernel_gen/passes/schedule/loop_soft_pipeline.py test/passes/schedule/test_loop_soft_pipeline.py test/passes/test_producer_consumer_analysis.py spec/pass/loop_soft_pipeline.md spec/pass/producer_consumer_analysis.md || true`
  - 结果：仅 `spec/pass/loop_soft_pipeline.md` 声明“不公开 LoopSoftPipelinePassError”；无旧 `non_zero_trip`、无新增 ctx 能力探测、无稳定错误实现。
  - `git diff --name-status` 仅显示本轮 5 个返工文件。

敏感范围：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'`
  - 结果：仅 `!! kernel/dump/`；三个 expectation 路径均未进入 staged / unstaged diff。

自检：
- 接口：未新增、删除、重命名或修改公开 API；`LoopSoftPipelinePass` canonical path、registry name 与 producer-consumer public attr 面保持不变。
- 边界：static zero-trip / non-positive step / dynamic unknown trip no-op；static single-tile 退化；multi-tile rewrite 保持原正路径。
- 异常：unknown option 与 private/KCE 门禁复跑通过；未新增稳定错误文本。
- 兼容：pipeline pytest、dynamic matmul dump 和两个 expectation 均通过；single-tile 不再产生 dead steady loop 或 loop-carried attr。
- 实现遗漏 / 冗余：旧动态默认放行和 single-tile steady loop 误生成已删除；未引入 guard 半实现或新 attr。
- 注释 / spec：功能文件说明、候选和 rewrite 注释、两个 spec 行为与测试清单已同步。
- 复用 / 函数粒度：trip count 判定集中在当前文件内部，不跨文件使用非公开 helper；新增测试 helper 仅构造 IR。
- 输入输出校验：start/end/step 非静态时保守 no-op，静态 trip count 精确区分 0 / 1 / 多 tile。
- 资源 / 并发 / 性能：pass 仍为单 module 局部 rewrite，无共享全局状态；新增 trip count 静态判断为常量时间。
- 测试有效性：新增断言会在 review 复现的 dead steady loop、loop_* attr 泄漏、动态无条件 prologue 任一问题回归时失败。

结论：
- 两个 review 阻断项已按 Q4 / Q4b 收口，spec、实现、pytest、dump、expectation、Diff 反推自测、减法检查、自检和敏感范围核对已完成。
- 下一步暂存本轮改动与任务记录后，按计划级链路执行 `-next -type review -auto`；不进入 `archive_acceptance` 或 `merge`。

时间：2026-06-13 14:06 +0800
经办人：睡觉小分队
任务：T-20260613-bac54fd8 / execute -> review 标准流转记录
任务目标：记录本次 execute 返工完成后的 `-next -type review -auto` 流转、脚本输出、状态复查、talk 复查、diff check、敏感范围和自检；不进入 `archive_acceptance` 或 `merge`。

流转命令：

```bash
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-bac54fd8 \
  -from "睡觉小分队" \
  -type review \
  -message "review；任务目标：复审 T-20260613-bac54fd8 execute 返工候选，重点核对 Q4 single-tile prologue copy -> epilogue matmul 且 producer-consumer 只用普通 productor/consumer、不产生 loop_first/loop_carried/after_loop；Q4b 动态无法证明 N>0 时 no-op/guard 不生成无条件 prologue；同步 spec、pytest、dump/expectation 验收、Diff 反推自测、减法检查、敏感范围和任务记录。任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md。计划级链路为 execute -> review -> archive_acceptance -> merge/归档，review 通过后不得直接 merge。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260613-bac54fd8
OK: replace 睡觉小分队 状态
OK: auto-dispatch T-20260613-bac54fd8 -> 提莫炖蘑菇
OK: replace 提莫炖蘑菇 状态
OK: talk 睡觉小分队 -> 提莫炖蘑菇 (提莫炖蘑菇)
OK: talk 睡觉小分队 -> 神秘人 (神秘人)
```

流转后复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing`
  - 结果：`T-20260613-bac54fd8` 为 `review / 提莫炖蘑菇 / 进行中`；任务目标为复审本次 Q4 / Q4b execute 返工候选；计划级链路仍为 `execute -> review -> archive_acceptance -> merge/归档`。
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status`
  - 结果：`提莫炖蘑菇=busy`，`睡觉小分队=free`。
- `tail -n 40 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`
  - 结果：可见 `@睡觉小分队向@提莫炖蘑菇发起会话` 的 review 交接消息，包含 worktree、计划书、记录文件、复审目标和计划级链路；可见 `@睡觉小分队向@神秘人发起会话` 的阶段完成回报，写明新任务类型为 review 并指派给提莫炖蘑菇。
- `git diff --check && git diff --cached --check`
  - 结果：退出码 0，无输出。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md && git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'`
  - 结果：仅 `!! kernel/dump/`；三个 expectation 路径均未进入 staged / unstaged diff。

自检：
- 本段记录实际 `execute -> review` 标准流转；任务状态由标准脚本完成，未手工修改 `TODO.md` 或 `agents-lists.md`。
- 已补完整命令、完整脚本输出、TODO/agents-list/talk 复查、diff check、敏感范围、expectation 路径复查和自检。
- 候选改动与任务记录已暂存；未修改 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md` 或 `agents-list`。
- 未进入 `archive_acceptance`、`merge`、提交、推送或归档。

结论：execute -> review 标准流转完成，当前接手人为 `提莫炖蘑菇`，等待 review 结论。

时间：2026-06-13 14:09 +0800
经办人：睡觉小分队
任务：T-20260613-bac54fd8 / execute -> review 流转补记后复查
任务目标：按管理员最新要求复查 14:03 之后本次 `execute -> review` 标准流转补记已在任务记录尾部补齐并暂存；不重新执行 `-next`，不改任务状态，不进入 `archive_acceptance` 或 `merge`。
改动：仅追加本条任务记录复查说明；前一条 14:06 段已包含实际 `-next -type review -auto` 完整命令、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围和自检；未修改实现 / spec / test / 计划验收结论。
验证：
- `tail -n 180 agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md`
  - 结果：尾部可见 14:06 `execute -> review 标准流转记录`，包含完整命令、完整输出、TODO 复查、agents-list 复查、talk 复查、`git diff --check && git diff --cached --check`、敏感范围、expectation 路径复查和自检。
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing | rg 'T-20260613-bac54fd8|任务 ID|---'`
  - 结果：`T-20260613-bac54fd8` 为 `review / 提莫炖蘑菇 / 进行中`。
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status | rg '睡觉小分队|提莫炖蘑菇|姓名|---'`
  - 结果：`提莫炖蘑菇=busy`，`睡觉小分队=free`。
- `tail -n 30 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`
  - 结果：包含 `睡觉小分队 -> 提莫炖蘑菇` 的 review 交接消息、`睡觉小分队 -> 神秘人` 的阶段完成回报，以及管理员本次要求只补记录的消息。
- `git diff --check && git diff --cached --check`
  - 结果：退出码 0，无输出。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md && git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,200p'`
  - 结果：仅 `!! kernel/dump/`；三个 expectation 路径均未进入 staged / unstaged diff。
自检：仅补任务记录并暂存；未重新执行 `-next`；未手工改 `TODO.md` / `agents-lists.md`；未改实现、spec、测试或计划验收结论；未进入 `archive_acceptance`、`merge`、提交、推送或归档；`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md`、`agents-list` 均为空 diff。
结论：本次 execute -> review 标准流转补记和补记后复查已完成并暂存；当前任务仍为 `review / 提莫炖蘑菇 / 进行中`。

时间：2026-06-13 14:19 +0800
经办人：提莫炖蘑菇
任务：T-20260613-bac54fd8 / review 复审
任务目标：复审 execute 返工候选，核对 Q4 single-tile 退化、Q4b 动态未知 no-op / guard 边界、spec / pytest / dump / expectation / Diff 反推自测 / 减法检查 / private-KCE / 敏感范围和任务记录；计划级 review 通过后只流转 `archive_acceptance`，不直接进入 merge。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer`。
- 已执行 `git fetch origin main --prune`。
- `HEAD=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `origin/main=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `merge-base=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `git rev-list --left-right --count HEAD...origin/main` -> `0 0`；当前 review 基于 latest main，无分叉、无覆盖风险。

被审 diff：
- 新增 / 修改计划与参考：`ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md`、`ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md`。
- 新增 / 修改实现：`kernel_gen/passes/schedule/loop_soft_pipeline.py`、`kernel_gen/passes/producer_consumer_analysis.py`、`kernel_gen/passes/registry.py`、`kernel_gen/pipeline/npu_demo_lowering.py`。
- 新增 / 修改 spec：`spec/pass/loop_soft_pipeline.md`、`spec/pass/producer_consumer_analysis.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/registry.md`。
- 新增 / 修改测试：`test/passes/schedule/test_loop_soft_pipeline.py`、`test/passes/test_producer_consumer_analysis.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`。
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md`。

执行记录核对：
- 已读取睡觉小分队 14:03 execute 返工记录：包含执行前阅读、返工收口、验证、Diff 反推自测、减法检查、敏感范围、自检和结论。
- 已核对 14:06 `execute -> review` 标准流转记录与 14:09 补记后复查；管理员已确认本次补记通过，解除只读限制。
- `TODO.md` 当前显示 `T-20260613-bac54fd8` 为 `review / 提莫炖蘑菇 / 进行中`；`agents-lists.md` 显示 `提莫炖蘑菇=busy`、`睡觉小分队=free`。

发现：
- 无阻断项。

重点审查：
- Q4 single-tile：`LoopSoftPipelinePass` 使用静态 `trip_count` 分流；`trip_count == 1` 时只克隆 prologue preload 与 epilogue matmul，删除原 loop，不构造 steady `symbol.for`、boundary `symbol.sub/add/floordiv/mul` 或 `dma.advance_ring`。`test_loop_soft_pipeline_single_tile_degenerates_to_prologue_epilogue` 锁定 `0..4 step 4` 输出 2 条 `dma.copy`、1 条 `kernel.matmul`、0 个 `symbol.for`，且无 `dma.advance_ring` / `symbol.sub` / `symbol.add`。
- Q4 producer-consumer：`test_producer_consumer_analysis_single_tile_prologue_epilogue_uses_main_attrs` 验证无 steady loop 的 prologue / epilogue 形态只写普通 `productor=[0]`、`productor=[1]`、`consumer=[0, 1]`，不出现 `loop_first`、`loop_carried` 或 `after_loop`。
- Q4b 动态未知：`static_trip_count(...)` 在 start/end/step 任一不可静态证明时返回 `None`，`find_candidate(...)` no-op；`test_loop_soft_pipeline_dynamic_unknown_trip_keeps_original_shape` 锁定符号 `%k_end` 保留原 `symbol.for`，不插入 `symbol.sub` / `symbol.add` 或无条件 prologue。
- spec 同步：`spec/pass/loop_soft_pipeline.md` 已写明 static single-tile 退化、dynamic unknown trip no-op、不新增 `LoopSoftPipelinePassError`；`spec/pass/producer_consumer_analysis.md` 已写明 single-tile 使用普通 attr，多 tile ring-aware 使用 `loop_first` / `loop_carried` / `after_loop`；pipeline / registry spec 已同步 pass 顺序与 registry 名称。
- 公开 API / re-export：canonical import path 为 `kernel_gen.passes.schedule.loop_soft_pipeline.LoopSoftPipelinePass`；`kernel_gen.passes.LoopSoftPipelinePass` 与 `kernel_gen.passes.schedule.LoopSoftPipelinePass` 未新增 package re-export，`test_registry_surviving_public_paths_match_consumer_matrix` 有反向断言。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py test/passes/test_producer_consumer_analysis.py test/passes/test_registry.py`
  - 结果：退出码 0，`84 passed, 1 warning`。
  - 锁定：Q4 single-tile 退化、Q4b dynamic unknown no-op、producer-consumer single-tile 主 attr、多 tile ring-aware attr、registry 名称与 package re-export 边界。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - 结果：退出码 0，`11 passed, 1 warning`。
  - 锁定：`multi-buffer-apply -> loop-soft-pipeline -> producer-consumer-analysis -> memory-pool` 顺序与 dump marker。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
  - 结果：退出码 0，`7 passed`。
  - 锁定：private API / private callable shape 门禁与 KernelCodeError 静态门禁。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - 结果：退出码 0；stdout 包含 `multi_tile=True tail=True`，`absent_bias max_abs_diff=3.4332275390625e-05`，`present_bias max_abs_diff=3.4332275390625e-05`。
- dump 复查：`kernel/dump/matmul/inputs_dynamic_tile_dynamic` 中可见 `26-loop-soft-pipeline.mlir: loop-soft-pipeline{fold=true}` 与 `producer-consumer-analysis{fold=true}` marker；dump 目录为 ignored local-only，不进入候选 diff。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.loop_soft_pipeline`
  - 结果：退出码 0，无 stdout。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - 结果：退出码 0；stdout 显示 after_if、after_loop、if_branch、loop_body、memory_effect_alias 等 10 条正例通过。
- `git diff --check && git diff --cached --check`
  - 结果：退出码 0，无输出。

Diff 反推审查：
- `kernel_gen/passes/schedule/loop_soft_pipeline.py` / `test/passes/schedule/test_loop_soft_pipeline.py`：由 loop-soft-pipeline 全量 pytest 覆盖；新增断言会在 single-tile 仍生成 steady loop、动态未知仍生成无条件 prologue、旧 event 泄漏或 source writer 未克隆时失败。
- `kernel_gen/passes/producer_consumer_analysis.py` / `test/passes/test_producer_consumer_analysis.py`：由 producer-consumer 全量 pytest 覆盖；新增断言会在 single-tile 误写 `loop_first` / `loop_carried` / `after_loop` 或 ring-aware 多 tile event 缺失时失败。
- `kernel_gen/passes/registry.py` / `test/passes/test_registry.py`：由 registry pytest 覆盖；锁定 `loop-soft-pipeline` registry 名称、canonical path 可导入、package root 不新增 re-export。
- `kernel_gen/pipeline/npu_demo_lowering.py` / `test/passes/pipeline/test_npu_demo_lowering.py`：由 pipeline pytest 与 dynamic matmul 脚本覆盖；锁定 pass 顺序、dump marker、memory-pool 前 producer-consumer 位置与 dynamic/tail 正向链路。
- `spec/pass/*.md`：对应 pass / registry / pipeline pytest 和 expectation 合同验收均已复跑；`expectation/pass/pipeline/npu_demo_lowering.py` 按 Q5 不纳入本轮 expectation 修改或必过验收。

减法审查：
- 旧 `non_zero_trip` 动态默认放行路径已被静态 `trip_count` 判定替代；无法静态证明正 trip 时 no-op，未保留旧动态无条件 prologue 入口。
- single-tile 不再复用多 tile boundary / steady loop / advance / preload-next 逻辑；退化为 prologue preload 与 epilogue matmul。
- `ProducerConsumerAnalysisPass._apply_to_func(...)` 私有方法已内联到公开 `apply(...)`，避免新增私有方法调用链。
- `rg` 抽查未见新增 `hasattr/getattr/callable(getattr(...))` 上下文能力探测；`LoopSoftPipelinePassError` 只在 plan/spec 历史与非目标文本中出现，未实现为稳定错误。
- private / KCE 门禁已复跑通过；本轮新增 / 改动 Python 文件未命中当前 diff private callable 五行与私有调用链阻断。

敏感范围：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` -> 无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` -> 无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,220p'`
  - 结果：仅 `!! kernel/dump/...` ignored dump 文件；三个 expectation 路径未进入 staged / unstaged diff。

自检：
- 已按最新主线现场复审，确认无分叉和覆盖风险。
- 已读取实际 staged diff、任务记录、计划 Q4 / Q4b、相关 spec、实现和测试，不只依赖 execute 摘要。
- 已核对公开 API / re-export 边界、private/KCE、无 expectation 修改、无 `.skills` / `agents/standard` / 根状态敏感文件改动。
- 已完成 Diff 反推审查、减法审查和测试有效性核对；未发现剩余可执行返工项。

结论：
- review 通过。
- 按计划级链路，下一步使用标准脚本 `-next -type archive_acceptance -auto` 续接 `archive_acceptance / 计划书入档验收`；不得直接进入 merge。

时间：2026-06-13 14:21 +0800
经办人：提莫炖蘑菇
任务：T-20260613-bac54fd8 / review -> archive_acceptance 标准流转记录
任务目标：记录本次 review 通过后按计划级链路续接 `archive_acceptance` 的标准脚本命令、输出、状态复查、talk 复查、diff check、敏感范围和自检；不进入 merge。

流转命令：

```bash
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-bac54fd8 \
  -from "提莫炖蘑菇" \
  -type archive_acceptance \
  -message "archive_acceptance；任务目标：核对 T-20260613-bac54fd8 计划级 loop-soft-pipeline ring-aware producer-consumer 任务的计划书入档验收与可归档性；重点复核 latest main 同步现场、计划书回写、Q4 single-tile 与 Q4b 动态未知 no-op/guard 收口、spec/pytest/dump/expectation 验收、Diff 反推审查、减法审查、private/KCE、敏感范围空 diff、expectation 只读合同资产和任务记录完整性。任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md。计划级链路为 execute -> review -> archive_acceptance -> merge/归档；archive_acceptance 完成前不得进入 merge。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260613-bac54fd8
OK: replace 提莫炖蘑菇 状态
OK: auto-dispatch T-20260613-bac54fd8 -> 提莫炖蘑菇
OK: replace 提莫炖蘑菇 状态
OK: talk 提莫炖蘑菇 -> 神秘人 (神秘人)
```

流转后复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing | rg 'T-20260613-bac54fd8|任务 ID|---'`
  - 结果：`T-20260613-bac54fd8` 为 `archive_acceptance / 提莫炖蘑菇 / 进行中`。
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status | rg '提莫炖蘑菇|睡觉小分队|姓名|---'`
  - 结果：`提莫炖蘑菇=busy`，`睡觉小分队=free`。
- `tail -n 40 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`
  - 结果：包含 `提莫炖蘑菇 -> 神秘人` 的阶段完成回报，说明任务已进入计划书入档验收并仍指派给当前执行者。
- `git diff --check && git diff --cached --check`
  - 结果：退出码 0，无输出。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md && git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,220p'`
  - 结果：仅 `!! kernel/dump/...` ignored dump 文件；三个 expectation 路径均未进入 staged / unstaged diff。

自检：
- 本段只补齐 review -> archive_acceptance 标准流转记录并暂存；任务状态由标准脚本完成，未手工修改 `TODO.md` 或 `agents-lists.md`。
- 未修改实现、spec、测试、计划验收结论、`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`DONE.md` 或 `agents-list`。
- 已按计划级链路进入 `archive_acceptance`，未进入 merge、提交、推送或归档。

结论：review -> archive_acceptance 标准流转完成；当前任务为 `archive_acceptance / 提莫炖蘑菇 / 进行中`。

时间：2026-06-13 14:32 +0800
经办人：提莫炖蘑菇
任务：T-20260613-bac54fd8 / archive_acceptance 计划书入档验收
任务目标：核对计划级 loop-soft-pipeline ring-aware producer-consumer 任务的计划书入档验收与可归档性；复核 latest main 同步现场、计划书回写、Q4 single-tile 与 Q4b 动态未知 no-op / guard 收口、spec / pytest / dump / expectation 验收、Diff 反推审查、减法审查、private-KCE、敏感范围空 diff、expectation 只读合同资产和任务记录完整性。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer`。
- 已执行 `git fetch origin main --prune`。
- `HEAD=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `origin/main=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `merge-base=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `git rev-list --left-right --count HEAD...origin/main` -> `0 0`；当前候选与 latest main 无分叉。

计划书回写：
- 已按入档验收要求回写 `ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md`。
- 回写内容：计划标题 / 状态改为已完成 `execute -> review -> archive_acceptance`、目标 `spec` 与测试资产改为已新增 / 已更新、计划级任务 worktree 改为实际路径、G2 后续状态改为已进入任务链并完成入档验收、追加“计划书入档验收（2026-06-13）”结论。
- 回写未修改 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md` 或 `agents-lists.md`。

发现：
- 无阻断项。

重点验收：
- Q4 single-tile：review 复审确认 `N == 1` 且 K 维正数时退化为 `prologue copy -> epilogue matmul`，producer-consumer 只使用普通 `productor` / `consumer`，不产生 `loop_first`、`loop_carried` 或 `after_loop`。
- Q4b 动态未知：review 复审确认无法静态证明至少一个 tile 时保持 no-op / guard 口径，不生成无条件 prologue。
- spec / 实现 / 测试：`spec/pass/loop_soft_pipeline.md`、`spec/pass/producer_consumer_analysis.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/registry.md` 与对应实现 / pytest 已在 review 复审中核对；本轮 archive_acceptance 未修改实现、spec 或测试。
- latest main 交叉风险：当前 `HEAD`、`origin/main` 与 `merge-base` 一致，ahead / behind 为 `0 0`，无覆盖风险。
- 任务记录：已核对 execute、返工 execute、execute -> review 补记、review 复审通过和 review -> archive_acceptance 标准流转记录；管理员已确认 review -> archive_acceptance 流转记录通过。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py test/passes/test_producer_consumer_analysis.py test/passes/test_registry.py`
  - 结果：退出码 0，`84 passed, 1 warning`。
  - 锁定：loop-soft-pipeline public API、Q4 single-tile、Q4b dynamic unknown no-op、producer-consumer ring event、registry name 与无 package re-export。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - 结果：退出码 0，`11 passed, 1 warning`。
  - 锁定：npu_demo lowering pipeline 顺序与 dump marker。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
  - 结果：退出码 0，`7 passed`。
  - 锁定：private API 边界与 KernelCodeError 静态门禁。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - 结果：退出码 0；stdout 包含 `multi_tile=True tail=True`、`absent_bias max_abs_diff=2.86102294921875e-05`、`present_bias max_abs_diff=2.86102294921875e-05`。
  - dump 复查：`kernel/dump/matmul/inputs_dynamic_tile_dynamic` 中可见 `26-loop-soft-pipeline.mlir` 与 producer-consumer / memory-pool 后续 marker；dump 为 ignored local-only。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.loop_soft_pipeline`
  - 结果：退出码 0，无 stdout。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - 结果：退出码 0；stdout 显示 after_if、after_loop、if_branch、loop_body、memory_effect_alias 等 10 条正例通过。
- `git diff --check && git diff --cached --check`
  - 结果：退出码 0，无输出。

Diff 反推审查：
- `kernel_gen/passes/schedule/loop_soft_pipeline.py` / `test/passes/schedule/test_loop_soft_pipeline.py`：由 loop-soft-pipeline / producer-consumer / registry pytest 组合覆盖；review 已核对 single-tile、dynamic unknown、stale attr 清理和 no package re-export 断言。
- `kernel_gen/passes/producer_consumer_analysis.py` / `test/passes/test_producer_consumer_analysis.py`：由 producer-consumer pytest 与 expectation 合同验收覆盖 ring-aware event 和既有控制流分类。
- `kernel_gen/passes/registry.py` / `test/passes/test_registry.py`：由 registry pytest 覆盖 built-in registry name、canonical path 和 re-export 边界。
- `kernel_gen/pipeline/npu_demo_lowering.py` / `test/passes/pipeline/test_npu_demo_lowering.py`：由 pipeline pytest 与 dynamic matmul 脚本覆盖 pipeline 顺序、dump marker 和 runtime 结果。
- 计划书 / 任务记录：本轮只回写计划入档结论和任务记录，已由 `git diff --check`、敏感范围空 diff、TODO / agents-list / talk 复查后续流转要求覆盖。
- `expectation` 单列为合同验收资产，不计入 Diff 反推测试；本轮未修改 `expectation/`。

减法审查：
- 本轮 archive_acceptance 无实现 / spec / test 代码改动；减法审查以 review 复审结论为准。
- review 已确认旧动态默认放行和 single-tile steady loop 误生成路径被删除，无法静态证明正 trip 时 no-op，single-tile 不再复用多 tile boundary / steady loop / advance / preload-next 逻辑。
- review 已确认 `ProducerConsumerAnalysisPass._apply_to_func(...)` 私有方法已内联到公开 `apply(...)`，未保留不合格 private callable 调 private callable 链。
- 本轮计划书回写只删除过期“不可下发 / 等待守护复验”当前状态措辞，替换为实际任务链完成态；未新增实现 helper 或新 API。

敏感范围：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,220p'`
  - 结果：仅 `!! kernel/dump/matmul/inputs_dynamic_tile_dynamic/...` ignored dump 文件；三个 expectation 路径均未进入 staged / unstaged diff。

自检：
- 已按 archive_acceptance 职责核对 latest main 现场、计划书回写、当前必过 pytest / 动态脚本 / expectation 合同验收、Diff 反推审查、减法审查、private-KCE、敏感范围、expectation 只读资产和任务记录完整性。
- 本轮只修改计划书入档验收正文与任务记录；未修改实现、spec、测试、`expectation/`、`.skills/`、`agents/standard/` 或共享任务状态文件。
- 未执行 merge、提交、推送、归档或清理；下一步只通过标准脚本续接 `merge`。

结论：
- archive_acceptance 通过。
- 下一步按计划级链路使用标准脚本 `-next -type merge -auto` 续接 `merge/归档`，由 merge 角色完成合并前复核、提交、推送和归档。

时间：2026-06-13 14:34 +0800
经办人：提莫炖蘑菇
任务：T-20260613-bac54fd8 / archive_acceptance -> merge 标准流转记录
任务目标：记录本次 archive_acceptance 通过后按计划级链路续接 `merge/归档` 的标准脚本命令、输出、状态复查、talk 复查、diff check、敏感范围和自检；不执行 merge、提交、推送、归档或清理。

流转命令：

```bash
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-bac54fd8 \
  -from "提莫炖蘑菇" \
  -type merge \
  -message "merge；任务目标：合入 T-20260613-bac54fd8 已通过 review 与 archive_acceptance 的 loop-soft-pipeline ring-aware producer-consumer 改动、计划书回写和任务记录；重点核对 staged/cached 范围、pytest/expectation 记录、敏感范围空 diff、expectation 只读资产未进入 diff，并按合并规范执行提交/推送/归档。任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260613-bac54fd8
OK: replace 提莫炖蘑菇 状态
OK: auto-dispatch T-20260613-bac54fd8 -> 李白
OK: replace 李白 状态
OK: talk 提莫炖蘑菇 -> 李白 (李白)
OK: talk 提莫炖蘑菇 -> 神秘人 (神秘人)
```

流转后复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing | rg 'T-20260613-bac54fd8|任务 ID|类型|指派|状态|---'`
  - 结果：`T-20260613-bac54fd8` 为 `merge / 李白 / 进行中`。
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status | rg '提莫炖蘑菇|李白|睡觉小分队|神秘人|姓名|---'`
  - 结果：`李白=busy`，`提莫炖蘑菇=free`，`睡觉小分队=free`，`神秘人=free`。
- `tail -n 60 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`
  - 结果：包含 `提莫炖蘑菇 -> 李白` 的 merge 交接消息，写明 worktree、计划书、记录文件和 merge 目标；包含 `提莫炖蘑菇 -> 神秘人` 的阶段完成回报，写明新任务类型为 merge 且指派给李白。
- `git diff --check && git diff --cached --check`
  - 结果：退出码 0，无输出。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md && git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`
  - 结果：退出码 0，无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump | sed -n '1,220p'`
  - 结果：仅 `!! kernel/dump/matmul/inputs_dynamic_tile_dynamic/...` ignored dump 文件；三个 expectation 路径均未进入 staged / unstaged diff。

自检：
- 本段仅记录实际 `archive_acceptance -> merge` 标准流转；任务状态由标准脚本完成，未手工修改 `TODO.md` 或 `agents-lists.md`。
- 已补完整命令、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围、expectation 路径复查和自检。
- 本轮只补计划书入档验收、任务记录和标准流转记录；未修改实现、spec、测试、`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`DONE.md` 或 `agents-list`。
- 未执行 merge、提交、推送、归档或清理。

结论：archive_acceptance -> merge 标准流转完成；当前任务为 `merge / 李白 / 进行中`，提莫炖蘑菇已释放。

时间：2026-06-13 14:42 +0800
经办人：李白
任务：T-20260613-bac54fd8 / merge 合并记录
任务目标：按合并规范在最新 `origin/main` 上合入已通过 review 与 archive_acceptance 的 loop-soft-pipeline ring-aware producer-consumer 候选，确保计划书入档验收回写、任务记录、参考文档、实现、spec、测试与计划归档同批进入一个合并提交。

同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer`。
- `git fetch origin main --prune` -> 退出码 0。
- `HEAD=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `origin/main=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `merge-base HEAD origin/main=d679cdcbda147d18effa4121cf460df4d05e33f8`。
- `git rev-list --left-right --count HEAD...origin/main` -> `0 0`。
- 未发生冲突；latest main 与本候选无额外交叉覆盖风险。

流程与记录完整性：
- 已确认任务当前为 `merge / 李白 / 进行中`。
- 已确认任务记录包含 execute、返工 execute、execute -> review 补记、review 复审通过、review -> archive_acceptance、archive_acceptance 通过记录，以及 2026-06-13 14:34 的 `archive_acceptance -> merge` 标准流转补记。
- `archive_acceptance` 结论为通过，且计划书已回写入档验收结论；本合并记录与任务记录同批合入。

实际合入范围：
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md`。
- 参考文档：`ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md`。
- 计划归档：原计划路径 `ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md` 已在 merge 阶段移出，归档目标为 `agents/codex-multi-agents/log/task_records/done_plan/2026/loop_soft_pipeline_ring_aware_producer_consumer.md`；`git ls-files --stage` 显示归档目标 blob 为 `100644 de825bf4dbf3e6dc0bdd0a6daa0237bd2cc484cf 0`。
- 实现：`kernel_gen/passes/producer_consumer_analysis.py`、`kernel_gen/passes/registry.py`、`kernel_gen/passes/schedule/loop_soft_pipeline.py`、`kernel_gen/pipeline/npu_demo_lowering.py`。
- spec：`spec/pass/loop_soft_pipeline.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/producer_consumer_analysis.md`、`spec/pass/registry.md`。
- 测试：`test/passes/pipeline/test_npu_demo_lowering.py`、`test/passes/schedule/test_loop_soft_pipeline.py`、`test/passes/test_producer_consumer_analysis.py`、`test/passes/test_registry.py`。
- 不合入 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md` 或其它未授权文件。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py test/passes/test_producer_consumer_analysis.py test/passes/test_registry.py` -> `84 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `11 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py` -> `7 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py` -> 退出码 0，输出包含 `multi_tile=True tail=True`、`absent_bias max_abs_diff=3.814697265625e-05`、`present_bias max_abs_diff=3.814697265625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.loop_soft_pipeline` -> 退出码 0，无 stdout。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis` -> 退出码 0，stdout 显示 after_if、after_loop、if_branch、loop_body、memory_effect_alias 等 10 条正例通过。
- `git diff --check` -> 无输出，退出码 0。
- `git diff --cached --check` -> 无输出，退出码 0。

敏感范围与 expectation：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` -> 无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` -> 无输出。
- `git diff --name-status -- expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py` -> 无输出。
- `git diff --cached --name-status -- expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py` -> 无输出。
- `git status --short --ignored --untracked-files=all -- expectation/pass/loop_soft_pipeline expectation/pass/producer_consumer_analysis expectation/pass/pipeline/npu_demo_lowering.py kernel/dump .pytest_cache` 仅显示 ignored local-only dump / `.pytest_cache` 副产物；三个 expectation 路径未进入 staged / unstaged diff。
- 本轮 merge 不修改、新增、移动、删除或重命名 `expectation/` 合同资产。

Diff 反推与减法核对：
- `loop_soft_pipeline`、`producer_consumer_analysis` 与 registry diff 已由 `test_loop_soft_pipeline.py`、`test_producer_consumer_analysis.py`、`test_registry.py` 和 expectation 合同验收覆盖，锁定 Q4 single-tile、Q4b dynamic unknown no-op、ring-aware event、registry name 与 package re-export 边界。
- pipeline diff 已由 `test/passes/pipeline` pytest 与 dynamic matmul 脚本覆盖，锁定 `loop-soft-pipeline` pass 顺序、dump marker 和 runtime 结果。
- private/KCE 已由 private API boundaries 与 KCE static gate 组合门禁覆盖。
- `expectation` 单列为合同验收资产，不计入 Diff 反推测试，也不进入合并 diff。
- 已复核 review / archive_acceptance 的减法记录：旧动态默认放行和 single-tile steady loop 误生成路径已删除；`ProducerConsumerAnalysisPass._apply_to_func(...)` 私有方法已内联到公开 `apply(...)`；未新增公开 API、package re-export、`LoopSoftPipelinePassError` 或共享 ring cursor API。

结论：
- 合并前核对通过，可提交并推送。
- 计划书归档、参考文档、任务记录、实现、spec 与测试将在同一提交中合入；合并后再执行 `-done` 与 `-done-plan`，并按完成清理规则核对 worktree / branch。
