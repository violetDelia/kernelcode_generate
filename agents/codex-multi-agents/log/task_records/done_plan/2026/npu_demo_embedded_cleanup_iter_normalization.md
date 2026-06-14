# npu demo embedded cleanup and symbol minmax fold 计划书 Draft 2-R3

## 文档信息

- 状态：Draft 2-R3；用户已重新决策，旧 Draft 1-R1 / G2 守护通过记录只作为历史证据，不再授权恢复 execute 或 merge。Draft 2-R1 G4 守护复验已通过，但 Draft 2-R3 按 2026-06-14 用户新口径实质修改公开选项和 expectation 合同：`fold` 不再承担 symbol-hoist 后 cleanup 开关，新增 `cse` / `canonicalize` 公开选项控制内嵌 cleanup；`symbol.min` full-tile fold 增补动态 symbolic count 场景。Draft 2-R2 的任务身份修正仍有效，但其守护请求作废；Draft 2-R3 已重新完成 subagent strict review 收敛，当前等待 `守护最好的爱莉希雅` 本人守护最终检验。
- 用户需求来源：
  - 2026-06-13 用户确认 `symbol-loop-hoist` 窄边界：候选 op 本身在 `scf.if` then/else branch 内时不外提；if 前 condition guard 链仍可按 loop-invariant 规则外提。
  - 2026-06-13 用户要求 `15-symbol-hoist-pipeline` 默认运行完后执行 `cse` 与 `canonicalize`，避免 dump 中继续出现三组独立 symbol-hoist 后 cleanup。
  - 2026-06-13 用户要求 `npu_demo_embedded_cleanup_iter_normalization` 与 hoist 改动一起推进，因为 hoist pipeline 和 npu-demo pipeline 都会改变。
  - 2026-06-13 用户决策：`1 A`；`LoopSoftPipelinePass 不做`；将可化简内容下沉为 `symbol.min/max` 自身 fold；添加相应 `expectation`。
  - 2026-06-14 用户确认任务身份修正：`T-20260613-56f5a699` 不是 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md` 这个计划书，要求继续推进本计划；因此本计划必须独立成为正式计划书字段，不再借旧窄计划任务字段进入 archive_acceptance / merge。
  - 2026-06-14 用户新确认：`npu-demo` dump 中不再为 symbol-hoist 后 cleanup 生成独立 `cse` / `canonicalize` 文件；`symbol-hoist-pipeline` dump 本身就是 cleanup 后 IR。该 cleanup 不由 `fold` 控制，新增 `cse` 选项控制是否运行 CSE pass，新增 `canonicalize` 选项控制末尾是否运行 canonicalize pass；补齐 `symbol.min` full-tile fold 与 `symbol.max` 静态 fold expectation，`symbol.min` 必须覆盖 `min(S1, N*S1 - iter<0,N*S1,S1>) -> S1` 这类动态 symbolic count full-tile 场景。
- 当前文件位置：`ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`。
- 旧窄计划参考文件：`ARCHITECTURE/plan/symbol_loop_hoist_if_branch_no_hoist.md`。该文件仅作为历史窄 scope 和 branch no-hoist 合同来源，不作为本计划正式任务的 `计划书` 字段；管理员不得把旧窄任务链的 review / archive_acceptance / merge 当作本计划已正式下发的证据。
- 跟踪状态要求：`ARCHITECTURE/plan/` 当前被 ignore；本 Draft 2-R3 成为正式候选前必须 `git add -f ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`，并记录 `git ls-files --stage`、`git diff --cached --name-status`、`git status --short --ignored --untracked-files=all`、`sha256sum` 与 `git diff --cached --check`。
- Draft 2-R3 候选状态记录：
  - 本轮正式候选只包含 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`。
  - 当前全量 cached diff 可能另有 unrelated staged file：`ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md` 与 `ARCHITECTURE/plan/symbol_loop_hoist_if_branch_no_hoist.md`。这两份文件不属于本轮正式候选，不得纳入本计划 execute / review / 守护 / merge 证据，不得与本计划候选混用。
  - unrelated staged file 属于独立现场，可能由其它流程持续更新；本计划只要求守护按路径级隔离确认它未混入本计划证据，不要求核验它们的 blob / sha256 在守护过程中保持稳定。复核请求可附其当前 `ls-files` / `sha256sum` 作为现场参考，但不得把该参考值作为本计划候选自洽的稳定门禁。
  - 当前工作区存在 unrelated unstaged deletion：`kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`；该删除不属于本计划候选，不得 stage、不得进入本计划 merge / 守护证据。
  - `expectation/dialect/symbol/operation/fold/min.py`、`expectation/dialect/symbol/operation/fold/max.py` 与既有 fold / hoist expectation 均为用户授权范围内的 ignored local-only 合同资产，不进入 cached diff。
  - 本计划正文不内嵌本计划候选文件自身 sha256 固定值，避免自引用导致记录立即失效；每次请求 strict review / 守护最终检验时必须在请求现场附最新 `git ls-files --stage`、`git diff --cached --name-status`、`git status --short --ignored --untracked-files=all`、`sha256sum`、`git diff --cached --check`、敏感范围 diff 和 expectation manifest hash。
  - Draft 2-R1 G1 守护后历史核对结果：当时全量 `git diff --cached --name-status` 为三条 staged `A`，其中仅两条计划属于 Draft 2-R1 正式候选，`multi_buffer_apply_fixed_reserved_before_auto.md` 为 unrelated staged 现场；该记录只作为历史证据，不适用于 Draft 2-R3 当前候选边界。Draft 2-R3 当前正式候选只有 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`。

## 目标范围

- 目标 `spec`：
  - `spec/pass/registry.md`
  - `spec/pass/symbol_loop_hoist.md`
  - `spec/pass/symbol_hoist_pipeline.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/pipeline/cuda_sm86_lowering.md`
  - `spec/dialect/symbol.md`
  - `spec/pass/pass_manager.md` 只读核对；默认不修改。
- 非目标 `spec`：
  - `spec/pass/loop_soft_pipeline.md` 本轮只读核对，不写入新 normalization 合同。
- 目标实现：
  - `kernel_gen/passes/hoist/symbol_loop_hoist.py`
  - `kernel_gen/passes/hoist/symbol_hoist_pipeline.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
  - `kernel_gen/pipeline/cuda_sm86_lowering.py`
  - `kernel_gen/dialect/symbol/operation/arith.py`
- 非目标实现：
  - `kernel_gen/passes/schedule/loop_soft_pipeline.py` 本轮不新增、不修改 pass-local normalization。
- 目标测试：
  - `test/passes/test_symbol_loop_hoist.py`
  - `test/passes/test_symbol_hoist_pipeline.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/pipeline/test_cuda_sm86_lowering.py`
  - `test/passes/test_registry.py`
  - `test/dialect/symbol/test_symbol.py`
  - `test/repo_conformance/test_private_api_boundaries.py`
  - `test/tools/test_kernel_code_error_static_gate.py`
- `expectation/` 授权：
  - 用户已明确授权本轮添加 `symbol.min/max` fold 相关 expectation。
  - 架构侧可在以下 local-only 范围新增 / 更新 / 物化 expectation：`expectation/dialect/symbol/operation/fold/min.py`、`expectation/dialect/symbol/operation/fold/max.py`、`expectation/dialect/symbol/operation/fold/__main__.py`。
  - 旧 hoist local-only expectation 继续作为只读合同验收资产：`expectation/pass/symbol_loop_hoist/__main__.py`、`expectation/pass/symbol_loop_hoist/if_branch_no_hoist.py`、`expectation/pass/symbol_loop_hoist/memory_presence_guard.py`。
  - execute / review / archive_acceptance / merge / 管理员只能读取、运行、引用和记录这些 expectation；不得修改、新建、移动、删除、重命名或把 `expectation/` 纳入正常任务 diff。

## 公开 API 口径

- 本 Draft 2-R3 新增公开构造参数和 registry option：`cse: bool = True`、`canonicalize: bool = True`。用户确认来源：2026-06-14 用户明确要求“不是 fold，加一个 cse 选项，开启就使用 cse pass，以及 canonicalize 选项，打开最后会运行 canonicalize pass”。
- 不删除、不重命名公开 pass、registry 名称或 class 名称。
- 保持 `class SymbolLoopHoistPass(fold: bool = True)`、`SymbolLoopHoistPass.apply(ctx: Context, module: ModuleOp) -> None`、公开 `*HoistPattern` class、公开 `match_and_rewrite(...)` 方法和 `get_symbol_loop_hoist_patterns() -> list[RewritePattern]` 签名不变。
- 修改 `SymbolHoistPipelinePass` 公开签名为 `class SymbolHoistPipelinePass(fold: bool = True, cse: bool = True, canonicalize: bool = True)`。
- 新增 `SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass` 公开构造入口，用于承载 registry 透传的 pass 专属 `cse` / `canonicalize` option；直接调用 `from_options({"fold": "false"})` 必须失败，通用 `fold` 仍只由 registry 外层解析。
- `symbol-hoist-pipeline` registry 必须接受 `cse=<bool>` 与 `canonicalize=<bool>`，并继续接受通用 `fold=<bool>`；非法 bool 文本必须使用现有 pass registry bool option 错误风格收口，未知 option 必须通过 `from_options(...)` 失败并保留为 `PassRegistryError: pass 'symbol-hoist-pipeline' option error: <原因>`。
- 保持 `class LoopSoftPipelinePass(fold: bool = True)`、`LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass`、`LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None` 签名与行为不变。
- 保持 `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 签名、registry 名称与 options 不变。
- 保持 `SymbolMinOp` / `SymbolMaxOp` 构造签名不变；本轮只补充 / 收紧已有 `fold` 公开行为和 expectation 合同。
- 本计划改变的公开可观察行为：
  - 三段 `symbol-hoist-pipeline` 后不再有独立顶层 `cse -> canonicalize` dump；默认 `symbol-hoist-pipeline{cse=true, canonicalize=true}` 输出即 cleanup 后 IR。
  - npu-demo 顶层 `cse` / `canonicalize` marker 数量从 5 组降为 2 组。
  - `cuda-sm86-lowering` 不继承 npu-demo 的 dump 收敛目标；为控制影响面，本计划要求 CUDA pipeline 显式构造 `SymbolHoistPipelinePass(cse=False, canonicalize=False)` 并保留既有外置 `cse -> canonicalize`，只同步更新 CUDA spec / pytest 对新 pass marker option 的断言。
  - `fold` 只控制 pattern walker / pass manager 的通用 folding，不控制内嵌 CSE / canonicalize cleanup。
  - `symbol.min/max` 的可证明 fold 由 op 自身公开 fold 承载。

## 用户决策记录

- D1：`scf.if` branch 内 candidate 不外提；if 前 condition guard 链仍可外提。
- D2：本计划必须包含 hoist 改动一起推进，不能只做 npu-demo pipeline 清理；但正式任务的 `计划书` 字段必须是本计划 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`，不得继续挂旧窄计划字段。
- D3：三段 `symbol-hoist-pipeline` 默认内嵌 `CommonSubexpressionElimination -> CanonicalizePass` cleanup，npu-demo 顶层删除三段后置独立 cleanup。用户选择 1A。
- D4：`LoopSoftPipelinePass` 本轮不做 pass-local normalization，不新增 normalize marker，不新增 loop-soft 内部优化。
- D5：`symbol-hoist-pipeline` cleanup 不由 `fold` 控制；新增 `cse` 与 `canonicalize` bool 选项，默认均为 `True`。
- D6：将本轮化简目标落到 `SymbolMinOp` / `SymbolMaxOp` 的 fold 合同，而不是 loop-soft pass。
- D7：用户明确授权添加相应 expectation；范围限定为本计划列出的 symbol fold expectation 与旧 hoist local-only expectation 物化。
- D8：保留 `memory-pool -> cse -> canonicalize` 顶层 cleanup，不扩大到 `MemoryPoolPass` 行为变更。
- D9：架构边界口径：非 npu-demo 消费者按保守兼容处理；`cuda-sm86-lowering` 保留既有外置 cleanup，不把 npu-demo dump 收敛目标扩展到 CUDA pipeline。该项来自用户对 npu-demo dump 收敛目标的限定和最小影响面原则；若后续要让 CUDA 也继承内嵌 cleanup，必须另行回用户确认。

## 任务身份修正与旧链路口径

- 旧任务链 `T-20260613-56f5a699 / symbol-loop-hoist-if-branch-no-hoist` 的 `计划书` 字段为 `ARCHITECTURE/plan/symbol_loop_hoist_if_branch_no_hoist.md`，不是本计划书。
- 该旧任务链曾按 Draft 2-R1 G4 作为承接现场执行到 review；用户已指出该任务身份不能代表本计划正式下发。
- 架构已通知管理员 hold / 暂停旧任务链 review；旧链路不得继续进入 archive_acceptance / merge，不得作为本计划归档链路。
- 本计划仍包含旧 hoist branch no-hoist 合同和相关 spec / pytest 工作；这些是本计划范围内的执行内容，不意味着正式计划书字段可以继续使用旧窄计划。
- Draft 2-R3 守护最终检验通过后，管理员应以 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md` 为计划书字段创建唯一计划级 execute：`npu-demo-embedded-cleanup-symbol-minmax-fold`。
- 管理员不得同时保留旧链路继续 review / archive_acceptance / merge；若需迁移旧 worktree 中已有实现现场，必须在新 execute 任务记录中作为参考现场记录，由 execute 重新按本计划完成自检、diff 反推测试、expectation 只读验收和流转。

## 计划级任务

- 计划级任务目标：以本计划书为正式计划字段，完成 `symbol-loop-hoist` 的 `scf.if` branch 内候选 op 不外提合同、`symbol-hoist-pipeline` 新增 `cse` / `canonicalize` 选项与 `from_options(...)` registry 构造并默认内嵌 `CSE -> canonicalize` cleanup、`npu-demo-lowering` 顶层 pass 顺序 / dump marker 更新、`cuda-sm86-lowering` 显式保留外置 cleanup 兼容边界、`symbol.min/max` fold 合同与 local-only expectation 验收；本轮不修改 `LoopSoftPipelinePass`。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance/计划书入档验收 -> merge/归档`。
- 当前下发前置：
  - Draft 2-R3 已按用户新口径完成主线修订，并完成 Round 5-A / Round 5-B 两轮 subagent strict review 收敛，均无阻断、无最小需改项、无待确认项。
  - 下发前必须取得 `守护最好的爱莉希雅` 本人守护最终检验通过。
  - 管理员确认旧链路 `T-20260613-56f5a699` 已 hold / 暂停，未进入 archive_acceptance / merge。
  - 创建 execute 后，必须先保持未分发或暂停；完成本计划 `Pre-Execute local-only expectation 物化门禁` 后才允许分发 / 恢复 execute。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `npu-demo-embedded-cleanup-symbol-minmax-fold` | `execute` | 由管理员创建，建议 `/home/lfr/kernelcode_generate/wt-20260614-npu-demo-embedded-cleanup-symbol-minmax-fold` | `agents/codex-multi-agents/log/task_records/2026/24/20260614-npu-demo-embedded-cleanup-symbol-minmax-fold.md` |

## Pre-Execute local-only expectation 物化门禁

- 本计划取得 Draft 2-R3 守护最终检验通过并创建唯一 execute 后，管理员不得直接分发 execute；必须先确认目标 worktree，并保持任务暂停或未分发状态。
- 管理员通知架构师目标 worktree 路径后，架构师必须在该目标 worktree 中按 manifest 复核或物化以下 ignored local-only expectation：
  - `expectation/pass/symbol_loop_hoist/__main__.py`
  - `expectation/pass/symbol_loop_hoist/if_branch_no_hoist.py`
  - `expectation/pass/symbol_loop_hoist/memory_presence_guard.py`
  - `expectation/dialect/symbol/operation/fold/__main__.py`
  - `expectation/dialect/symbol/operation/fold/min.py`
  - `expectation/dialect/symbol/operation/fold/max.py`
- manifest：
  - `expectation/pass/symbol_loop_hoist/__main__.py` sha256=`53ac10281ff02d674dc4641f125951108b523627d13a5edf361fb65473139098`
  - `expectation/pass/symbol_loop_hoist/if_branch_no_hoist.py` sha256=`9cc2efbd127c697924628d2687fba303f3b5ad2c6c78eaca78ec74c1f43dd01a`
  - `expectation/pass/symbol_loop_hoist/memory_presence_guard.py` sha256=`d5ee57e861c72f9fe36d107e253739f56d1f6b453e0a041e8fe07058f7821790`
  - `expectation/dialect/symbol/operation/fold/__main__.py` sha256=`46563687d6dd1c739989e6063f4dff4364b1f55464a807af5b0c45de6460b395`
  - `expectation/dialect/symbol/operation/fold/min.py` sha256=`519af471c73fa881bee923636fe3a1e53cf05cd6c59db1bad75fbaf66d111ce9`
  - `expectation/dialect/symbol/operation/fold/max.py` sha256=`734e5df337a106082380e6add626bc93d65c420b3278d7f1ea9e861670f781ec`
- 物化 / 复核记录必须写入目标任务记录，并至少包含：

```bash
sha256sum \
  expectation/pass/symbol_loop_hoist/__main__.py \
  expectation/pass/symbol_loop_hoist/if_branch_no_hoist.py \
  expectation/pass/symbol_loop_hoist/memory_presence_guard.py \
  expectation/dialect/symbol/operation/fold/__main__.py \
  expectation/dialect/symbol/operation/fold/min.py \
  expectation/dialect/symbol/operation/fold/max.py

git status --short --ignored --untracked-files=all -- \
  expectation/pass/symbol_loop_hoist/__main__.py \
  expectation/pass/symbol_loop_hoist/if_branch_no_hoist.py \
  expectation/pass/symbol_loop_hoist/memory_presence_guard.py \
  expectation/dialect/symbol/operation/fold/__main__.py \
  expectation/dialect/symbol/operation/fold/min.py \
  expectation/dialect/symbol/operation/fold/max.py

git check-ignore -v \
  expectation/pass/symbol_loop_hoist/__main__.py \
  expectation/pass/symbol_loop_hoist/if_branch_no_hoist.py \
  expectation/pass/symbol_loop_hoist/memory_presence_guard.py \
  expectation/dialect/symbol/operation/fold/__main__.py \
  expectation/dialect/symbol/operation/fold/min.py \
  expectation/dialect/symbol/operation/fold/max.py

git ls-files --stage -- \
  expectation/pass/symbol_loop_hoist/__main__.py \
  expectation/pass/symbol_loop_hoist/if_branch_no_hoist.py \
  expectation/pass/symbol_loop_hoist/memory_presence_guard.py \
  expectation/dialect/symbol/operation/fold/__main__.py \
  expectation/dialect/symbol/operation/fold/min.py \
  expectation/dialect/symbol/operation/fold/max.py

git diff --cached --name-status -- expectation
git diff --name-status -- expectation
```

- 物化通过口径：
  - 六项 sha256 与 manifest 完全一致。
  - 六项均为 ignored local-only，`git check-ignore` 命中 `expectation` ignore 规则，`git ls-files --stage` 无输出。
  - `git diff --cached --name-status -- expectation` 与 `git diff --name-status -- expectation` 无输出。
  - 不要求新增 symbol fold expectation 在 execute 前通过；它是本计划 execute 的目标合同。旧 hoist expectation 若当前 main 已通过，可以只读运行并记录；若新增 fold expectation 因未实现 Draft 2-R3 新合同而失败，只记录 actual，不得由管理员或 execute 修改 expectation。
- 完成以上物化记录前，管理员不得分发或恢复 execute。
- execute / review / archive_acceptance 阶段的最终合同验收必须运行五条 expectation 命令并全部通过。

## 当前基线

- `symbol-hoist-pipeline` 当前只执行 alias-to-reinterpret 与 `symbol-loop-hoist -> symbol-buffer-hoist -> hoist-dma-alias-ops`，cleanup 依赖 npu-demo 顶层后置 `cse -> canonicalize`，且公开构造参数当前只有 `fold`。
- `npu-demo-lowering` 当前三次 `SymbolHoistPipelinePass()` 后都追加独立 `CommonSubexpressionElimination -> CanonicalizePass`。
- `cuda-sm86-lowering` 当前也三次默认构造 `SymbolHoistPipelinePass()` 并在每段后追加外置 `CommonSubexpressionElimination -> CanonicalizePass`；新增 `cse=True` / `canonicalize=True` 默认若不显式处理，会让 CUDA 同时执行内嵌 cleanup 与外置 cleanup。本计划选择在 CUDA pipeline 显式传 `cse=False, canonicalize=False` 保持旧外置 cleanup 行为。
- 当前 npu-demo 顶层顺序包含五次独立 `cse` 与五次独立 `canonicalize`：inline 后一组、三段 symbol-hoist 后各一组、memory-pool 后一组。
- `SymbolMinOp` 已有 full-tile tail fold 逻辑和 expectation，但当前只覆盖静态整数倍或静态 count * 动态 step，未锁定 `N*S1` 这类 symbolic count * dynamic step full-tile 证明；`SymbolMaxOp` 当前公开 fold 仅覆盖静态整数 operand，不定义动态 max 化简。
- 当前只读运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.symbol.operation.fold.min` 失败于新增 case `dialect-symbol-operation-fold-min-full_tile_symbolic_count_dynamic_step-1`，失败摘要为 `symbol.min result type must match canonical symbol expression`；该失败正是本计划 execute 要修复的合同缺口，不是 expectation 本体阻断。
- `LoopSoftPipelinePass` 当前在可证明 ring-backed preload loop 上生成 prologue / steady / epilogue；本计划不改变它的结构改写、no-op 边界或 ring current / advance 语义。

## 计划目标

- 继承并保留旧 hoist 计划目标：`symbol-loop-hoist` / `symbol-hoist-pipeline` 不得把 `scf.if` then/else branch 内候选 op 外提到 branch 外；if 前 condition guard 链仍可外提。
- 把三段 `symbol-hoist-pipeline` 后的 `cse -> canonicalize` 从 npu-demo 顶层 pipeline 移入 `SymbolHoistPipelinePass` 内部。
- npu-demo dump 中不再为 symbol-hoist 后 cleanup 生成独立 `cse` / `canonicalize` 文件；默认 `symbol-hoist-pipeline{cse=true, canonicalize=true}` dump 本身就是 cleanup 后 IR。
- 新增 `symbol-hoist-pipeline` 公开 `cse` 与 `canonicalize` 选项：`cse=true` 时运行 CSE pass，`canonicalize=true` 时在最后运行 canonicalize pass；两者互相独立，`fold` 不控制 cleanup。
- `cuda-sm86-lowering` 继续保留三段 symbol-hoist 后的独立外置 cleanup；其 `symbol-hoist-pipeline` marker 需显式显示 `cse=false canonicalize=false` 或等价稳定 option 表达，避免默认行为变化悄悄影响 CUDA dump。
- 保留初始 `inline -> cse -> canonicalize` 与 `memory-pool -> cse -> canonicalize` 两组顶层 cleanup。
- 不新增 `symbol-normalize`、`loop-soft-normalize` 或其它公开 pass，不改变 registry 名称。
- 不修改 `LoopSoftPipelinePass`；`26-loop-soft-pipeline` 之后若出现可由 op fold 化简的 `symbol.min/max`，由 `symbol.min/max` 自身 fold 承接。
- 补齐 symbol fold expectation，锁定 `symbol.min` full-tile fold、`symbol.min` symbolic count dynamic step full-tile fold、`symbol.max` 静态 fold 与动态保守不 fold边界。

## 方案比较与选型

### 方案 A：`symbol-hoist-pipeline` 通过 `cse` / `canonicalize` 选项内嵌 cleanup，symbol 化简下沉到 op fold

- 内容：
  - `SymbolHoistPipelinePass.apply(...)` 在 clone 上完成既有 rewrite 后，根据 `cse` / `canonicalize` 选项运行内部 cleanup。
  - 默认 `cse=True`、`canonicalize=True`，所以默认继续内部执行 `CommonSubexpressionElimination -> CanonicalizePass`。
  - npu-demo pipeline 删除三段 symbol-hoist 后的顶层 `cse -> canonicalize`。
  - `LoopSoftPipelinePass` 不做新增 normalization。
  - `symbol.min/max` 可证明化简由 op 自身 `fold` 承载，`fold` 不控制 cleanup。
- 优点：
  - 满足用户点名的 pipeline / dump 目标。
  - 不新增公开 pass marker，也不把 loop-soft pass 变复杂。
  - `cse` / `canonicalize` 显式选项让 dump 行为和 pass-local cleanup 可单独控制。
  - 化简语义靠 dialect op 自身维护，可被其它 pass / pipeline 复用。
  - expectation 可以直接锁 dialect fold 合同。
- 风险：
  - 顶层 pipeline marker 数量变化，spec 和 dump 测试必须同步。
  - `symbol.min/max` fold 规则必须保守，不能把动态 tail 或未知约束误折叠。
- 结论：采用。用户已选择 1A，并在 2026-06-14 明确 cleanup 不由 `fold` 控制，改用 `cse` / `canonicalize` 选项。

### 方案 B：`LoopSoftPipelinePass` 内部 normalization

- 内容：在 `LoopSoftPipelinePass` 改写后做 pass-local iter / symbol normalization。
- 结论：不采用。用户最新决策明确 `LoopSoftPipelinePass 不做`。

### 方案 C：新增公开 normalize pass

- 内容：新增 `symbol-normalize` 或 `loop-soft-normalize` pass。
- 结论：不采用。本轮不新增公开 API / registry / dump marker。

## 推荐公开行为设计

### `SymbolHoistPipelinePass`

- 签名变更：

```python
class SymbolHoistPipelinePass(fold: bool = True, cse: bool = True, canonicalize: bool = True)
SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass
SymbolHoistPipelinePass.apply(ctx: Context, module: ModuleOp) -> None
```

- 行为变更：
  - 既有两段 rewrite 成功后，在同一个 clone 上按选项运行内部 cleanup。
  - `cse=True` 时运行 `CommonSubexpressionElimination`；`cse=False` 时跳过 CSE。
  - `canonicalize=True` 时在末尾运行 `CanonicalizePass`；`canonicalize=False` 时跳过 canonicalize。
  - 两个选项都为 `True` 时，内部 cleanup 顺序固定为 `CommonSubexpressionElimination -> CanonicalizePass`。
  - 内部 cleanup 失败或 verifier 失败时，仍按当前 `SymbolHoistPipelineVerifierError: ...` 合同失败，原 module 不被部分替换。
  - `fold=False` 只关闭 pattern walker / pass manager 的通用 folding，不关闭 CSE / canonicalize cleanup。
  - npu-demo pipeline 使用默认 `SymbolHoistPipelinePass()`，因此三段默认输出为 cleanup 后 IR。
  - CUDA pipeline 使用 `SymbolHoistPipelinePass(cse=False, canonicalize=False)`，因此仍依赖外置 `cse -> canonicalize`，不改变 CUDA cleanup 位置。
  - registry 构造 `symbol-hoist-pipeline={cse=false}`、`symbol-hoist-pipeline={canonicalize=false}` 与 `symbol-hoist-pipeline={fold=false,cse=false,canonicalize=false}` 必须可用，并在 dump marker / pipeline spec 中稳定打印对应 option。

### `LoopSoftPipelinePass`

- 签名和行为不变：

```python
class LoopSoftPipelinePass(fold: bool = True)
LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass
LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None
```

- 本轮明确不做：
  - 不新增 pass-local iter / symbol normalization。
  - 不新增 `loop-soft-normalize` marker。
  - 不新增 loop-soft 专用 fold / cleanup 开关。
  - 不改变 unsupported、zero-trip、dynamic unknown trip 的 no-op 口径。
  - 不改变 ring current / advance 调度顺序。

### `symbol.min/max` fold

- `symbol.min` 必做 / 保留：
  - 静态整数 operand fold 为 `symbol.const min(lhs, rhs)`。
  - result type 为 `!symbol.int<#symbol.expr<?>>` 且 operand 静态时仍物化确定 `symbol.const`。
  - full-tile tail 模式 `min(step, end - iter<start,end,step>)` 在 `(end-start)` 可证明为 `step` 正整数倍时 fold 为 `step`。
  - 静态 step 物化为 `symbol.const step`；动态 step 直接复用原 step SSA value。
  - 动态 symbolic count full-tile 模式也必须 fold：`min(S1, N*S1 - iter<0,N*S1,S1>)` fold 为原 `S1` SSA value；等价的 `B -> B + N*S1 step S1` 也按同一规则处理。
  - 无法证明 full-tile、含 unknown `?` 或普通动态 symbol 时不得 fold 为常量。
- `symbol.max` 必做：
  - 静态整数 operand fold 为 `symbol.const max(lhs, rhs)`。
  - result type 为 `!symbol.int<#symbol.expr<?>>` 且 operand 静态时仍物化确定 `symbol.const`。
  - 动态 symbol、unknown `?`、`symbol.iter` operand 或 result type 与最大值不匹配时不得 fold 为常量。
- 本轮不做：
  - 不新增 `symbol.max` 动态 full-tile 或范围证明规则。
  - 不做跨 block / region 的 value numbering。
  - 不移动任何有 MemoryEffect 的 op。

### `npu-demo-lowering`

- 顶层 pipeline 删除三段 symbol-hoist 后独立 cleanup：

```text
memory-plan -> symbol-hoist-pipeline -> tile-analysis
...
memory-plan -> symbol-hoist-pipeline -> kernel-aggregate
...
memory-plan -> symbol-hoist-pipeline -> multi-buffer-analysis
```

- 顶层 pipeline 保留：

```text
inline -> cse -> canonicalize
memory-pool -> cse -> canonicalize
```

- 预期顶层 pass marker 计数：
  - `symbol-hoist-pipeline` 仍为 3。
  - 顶层 `cse` 从 5 降到 2。
  - 顶层 `canonicalize` 从 5 降到 2。
  - `loop-soft-pipeline` 仍为 1。

## 完成态定义

- `symbol-hoist-pipeline` 作为单独 pass 运行时，默认输出已包含 CSE / canonicalize 的可观察结果。
- npu-demo dump 中三段 symbol-hoist 后不再出现独立 `cse` / `canonicalize` 阶段。
- `producer-consumer-analysis` 仍紧跟 `loop-soft-pipeline`，且位于 `memory-pool` 前；本计划不改变它和 loop-soft 的相对顺序。
- `symbol.min/max` fold expectation 通过；`symbol.max` 不发生未经证明的动态 fold。
- `LoopSoftPipelinePass` 的实现、spec、公开签名与 pass-local 行为保持不变。
- static/static、static/dynamic、dynamic/dynamic matmul pipeline 仍满足原有 alloc/free 外提、dead fill、multi-buffer、loop-soft-pipeline、producer-consumer-analysis 与 memory-pool 合同，只更新观察 dump 的 marker 位置与 cleanup 所在阶段。

## 计划内小任务

### S0：保留并复验 `scf.if` branch no-hoist 合同

- 为什么做：当前暂停任务的原始 hoist 目标仍必须合入新 scope，不能因为 cleanup / pipeline 改动丢失。
- 做什么：更新或保留 `symbol-loop-hoist` 与 `symbol-hoist-pipeline` spec / pytest 中的 `scf.if` branch 内 candidate 不外提合同，并复验旧 local-only expectation。
- 不做什么：不禁止 if 前 condition guard 链外提；不新增公开 API。
- 怎么验收：`test_symbol_loop_hoist.py` / `test_symbol_hoist_pipeline.py` 通过，旧 hoist expectation 通过且 expectation 无 diff。
- 卡住问谁：branch 边界或旧 hoist expectation 授权争议问用户 / 架构师；任务状态或 worktree 复用问题问管理员。

详细执行步骤：
1. 核对 `spec/pass/symbol_loop_hoist.md` 写清 branch 内 candidate 不外提、if 前 condition guard 可外提。
2. 核对 `spec/pass/symbol_hoist_pipeline.md` 写清组合 pass 继承该边界。
3. 保留或补齐 pytest，断言 branch 内候选 op 留在 `scf.if` body 内。
4. 运行旧 hoist local-only expectation，只读验收，不把 expectation 纳入 staged diff。

### S1：更新 spec，明确 registry option、cleanup 选项、pipeline marker 变化和 symbol fold 归属

- 为什么做：当前 spec 明确要求 symbol-hoist 后外置 cleanup，且旧稿把 loop-soft normalization 写成目标，均与用户最新决策冲突。
- 做什么：更新 `registry.md`、`symbol_hoist_pipeline.md`、`npu_demo_lowering.md`、`cuda_sm86_lowering.md`、`symbol.md`，写清 `cse` / `canonicalize` 选项、registry 构造、cleanup 归属、marker 数量、CUDA 保守兼容边界、`symbol.min/max` fold 合同；只读核对 `loop_soft_pipeline.md` 不新增 normalization 合同。
- 不做什么：不新增公开 pass；不修改 `LoopSoftPipelinePass` spec；不让 `fold` 继续承担 cleanup 开关。
- 怎么验收：相关 pytest 通过，文本核对不再出现“三段 symbol-hoist 后必须紧跟 cse -> canonicalize”的旧合同，也不出现本轮新增 loop-soft normalization 合同。
- 卡住问谁：公开行为是否算 API 变更、`fold=false` 边界或 spec 合同冲突问用户 / 架构师。

详细执行步骤：
1. 在 `registry.md` 把 `symbol-hoist-pipeline` 从“只接受通用 `fold`”改为接受 pass 专属 `cse` / `canonicalize`，并写清未知 option / 非 bool 文本错误语义。
2. 删除或改写 `symbol_hoist_pipeline.md` 中“保持 `cse` / `canonicalize` 为 pipeline 外置阶段”的旧目标。
3. 在 `symbol_hoist_pipeline.md` 写明 `cse` / `canonicalize` 公开 option、默认值、`from_options(...)`、内部 cleanup 顺序、失败回滚和 `fold` 边界。
4. 在 `npu_demo_lowering.md` 更新公开顺序，顶层 `cse` / `canonicalize` 计数从 5 改为 2。
5. 在 `cuda_sm86_lowering.md` 写清 CUDA pipeline 保留外置 cleanup，并显式使用 `SymbolHoistPipelinePass(cse=False, canonicalize=False)` 避免默认内嵌 cleanup 扩散。
6. 在 `symbol.md` 核对 / 补齐 `symbol.min/max` fold 规则，特别是 `symbol.min` symbolic count dynamic step full-tile 正例与 `symbol.max` 动态保守边界。
7. 明确 `loop_soft_pipeline.md` 本轮不改，不新增 normalization 责任。

### S2：实现 `SymbolHoistPipelinePass` 内部 cleanup 公开选项

- 为什么做：减少 npu-demo 顶层 cleanup dump，并让该 pass 的单独输出即为收敛后 IR。
- 做什么：在 clone rewrite 后、verify / replace 前按 `cse` / `canonicalize` 选项运行内部 `CommonSubexpressionElimination` 与 `CanonicalizePass`。
- 不做什么：不调用旧根模块 pass；不新增未在 spec / `API 列表` 定义的 public helper；不修改 pass name；不让 `fold=False` 关闭 cleanup。
- 怎么验收：`test_symbol_hoist_pipeline.py` 证明默认单 pass cleanup 生效，`fold=False` 仍执行 cleanup，`cse=False` 跳过 CSE，`canonicalize=False` 跳过末尾 canonicalize，registry 对 `cse` / `canonicalize` bool option 可构造且非法 bool 文本稳定失败。
- 卡住问谁：xDSL CSE / canonicalize 在 pass 内运行出现 verifier、context 或 rollback 边界问题时问架构师。

详细执行步骤：
1. 在 `kernel_gen/passes/hoist/symbol_hoist_pipeline.py` 导入 xDSL `CommonSubexpressionElimination` 与 `CanonicalizePass`。
2. 为 `SymbolHoistPipelinePass` 增加 `cse: bool = True` 与 `canonicalize: bool = True` dataclass 字段，并更新文件级 `API 列表`。
3. 增加 `SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass`，只解析 `cse` / `canonicalize`，拒绝未知 option 和直接传入 `fold`。
4. 在 clone 上完成两段 pattern rewrite 后按 `self.cse` / `self.canonicalize` 运行内部 cleanup。
5. 将 cleanup 纳入现有 try / except / verify 边界。
6. 更新文件级说明和 `API 列表` 旁的行为说明，明确 `fold` 不控制 cleanup。
7. 增加 pytest，覆盖默认 cleanup、failure rollback、`fold=False`、registry `fold=false`、registry `cse=false`、registry `canonicalize=false`、非法 bool option、未知 option 和直接 `from_options({"fold": "false"})` 失败。

### S3：实现 / 补齐 `symbol.min/max` fold 合同与 expectation

- 为什么做：用户要求化简下沉到 `symbol.min/max` fold，并新增相应 expectation，而不是在 loop-soft pass 内做。
- 做什么：核对 / 补齐 `kernel_gen/dialect/symbol/operation/arith.py` 中 `SymbolMinOp` / `SymbolMaxOp` fold；补 `test_symbol.py`，只读运行并记录架构已物化的 local-only expectation。
- 不做什么：不新增共享公开 helper；不新增复杂动态范围证明；不把 `symbol.max` 动态场景误折叠。
- 怎么验收：`test/dialect/symbol/test_symbol.py` 相关用例通过，`expectation.dialect.symbol.operation.fold.min`、`max` 与聚合入口通过。
- 卡住问谁：任何超出现有 `symbol.min/max` fold 合同的动态证明、expectation 授权争议或公开错误语义变化问用户 / 架构师。

详细执行步骤：
1. 确认 `SymbolMinOp` 保留 full-tile tail fold：可证 full-tile 时 fold 到 step，静态 step 物化常量，动态 step 复用原 SSA。
2. 补齐 `SymbolMinOp` 对 symbolic count dynamic step 的 full-tile 证明：`0 -> N*S1 step S1` 与 `B -> B + N*S1 step S1` 必须 fold 为原 `S1` SSA value；不能依赖 SSA 名称，只能基于公开 symbol expr 结构证明。
3. 确认 `SymbolMaxOp` 静态整数 fold 生效，并在动态、unknown、iter、result type mismatch 场景保守返回 `None`。
4. 如发现 `SymbolMinOp` / `SymbolMaxOp` 规则缺口，只在 `arith.py` 当前文件内补实现；不得跨文件调用非公开 helper。
5. 更新 `test_symbol.py`，覆盖本计划列出的 fold 和拒绝 fold 场景。
6. 本轮已由架构侧新增 / 更新 local-only `expectation/dialect/symbol/operation/fold/min.py` 与 `max.py`；execute 只能读取、运行和记录，不能改 expectation。

### S4：更新 npu-demo pipeline 顺序与 dump 测试

- 为什么做：顶层 pass 顺序与 dump marker 数量是公开合同，必须同步测试。
- 做什么：从 `kernel_gen/pipeline/npu_demo_lowering.py` 删除三段 symbol-hoist 后的顶层 `CommonSubexpressionElimination -> CanonicalizePass`，更新 pipeline spec 与 tests。
- 不做什么：不删除初始 cleanup 和 memory-pool 后 cleanup；不改 `target` option；不修改 `LoopSoftPipelinePass`。
- 怎么验收：`test_npu_demo_lowering.py` 通过，真实 dump marker 计数为顶层 `cse == 2`、`canonicalize == 2`、`symbol-hoist-pipeline == 3`、`loop-soft-pipeline == 1`。
- 卡住问谁：旧测试依赖具体 dump 编号、fill / alloc-free / memory-pool 合同迁移位置不清楚时问架构师。

详细执行步骤：
1. 更新 builder pass 顺序。
2. 更新 pass order monkeypatch 期望列表。
3. 更新真实 dump 测试，优先按 marker 相对顺序断言，避免继续固定旧编号。
4. 把原先读取 post-decompose canonicalize 的断言迁移到第三段 `symbol-hoist-pipeline` 或内嵌 cleanup 后等价阶段；dump 文件名 / marker 不得再要求 symbol-hoist 后独立 `cse` / `canonicalize`。
5. 核对 static/static、static/dynamic、dynamic/dynamic 三类 dump 是否仍满足 fill / alloc/free / ring / memory-pool 合同。
6. 明确更新或新增以下验收矩阵，不能只检查 marker 计数：

| 验收面 | 断言位置 | 预期 |
| --- | --- | --- |
| fill 删除 | 第三段 `symbol-hoist-pipeline` 默认 cleanup 后，或由该阶段替代旧 post-decompose canonicalize 的等价 dump | static/static 与 static/dynamic 不残留可证明 dead fill；dynamic/dynamic 只允许保留既有非必删 acc fill |
| alloc/free hoist | 第三段 `symbol-hoist-pipeline` 默认 cleanup 后的 pattern 函数 | `dma.alloc` / `dma.free` 位于 pattern 函数首层，loop 内不残留 lifecycle op |
| logical matmul alias | 第三段 `symbol-hoist-pipeline` 默认 cleanup 后 | `kernel.matmul` 继续消费 logical `dma.reinterpret` alias |
| producer-consumer 位置 | dump marker 相对顺序 | `loop-soft-pipeline -> producer-consumer-analysis -> memory-pool`，producer-consumer 位于 loop-soft 后且 memory-pool 前 |
| memory-pool 前 IR 形态 | `producer-consumer-analysis` dump | 保留 typed `dma.alloc` / `dma.ring` / `!nn.memory` 形态，不出现 `arch.get_dynamic_memory` |
| memory-pool 后 IR 形态 | `memory-pool` 与 memory-pool 后 `cse -> canonicalize` dump | 出现 `arch.get_dynamic_memory + dma.reinterpret`，不残留 typed `dma.alloc/free` |
| cleanup marker 数量 | dump markers | 顶层 `cse == 2`、`canonicalize == 2`、`symbol-hoist-pipeline == 3`、`loop-soft-pipeline == 1` |

### S4b：收口 CUDA pipeline 兼容影响面

- 为什么做：`SymbolHoistPipelinePass()` 默认行为变更会影响所有默认构造方；CUDA pipeline 当前也三次默认构造该 pass，必须明确是继承新默认还是保守兼容。
- 做什么：`cuda-sm86-lowering` 显式使用 `SymbolHoistPipelinePass(cse=False, canonicalize=False)`，保持既有三段外置 `cse -> canonicalize`；同步更新 CUDA spec / pytest 的 pass marker 与顺序断言。
- 不做什么：不把 npu-demo dump 收敛目标扩展到 CUDA；不删除 CUDA 外置 cleanup；不新增 CUDA pipeline option。
- 怎么验收：`test/passes/pipeline/test_cuda_sm86_lowering.py` 通过，CUDA pass order 仍包含三段外置 `cse -> canonicalize`，且 dump marker 稳定反映 `symbol-hoist-pipeline` 的 `cse=false canonicalize=false` 显式边界。
- 卡住问谁：若 CUDA 维护者要求继承新默认或删除外置 cleanup，先回用户 / 架构师确认；流程状态问管理员。

详细执行步骤：
1. 将 `kernel_gen/pipeline/cuda_sm86_lowering.py` 中三处默认 `SymbolHoistPipelinePass()` 改为显式 `SymbolHoistPipelinePass(cse=False, canonicalize=False)`。
2. 更新 `spec/pass/pipeline/cuda_sm86_lowering.md` 的公开顺序说明，保留外置 cleanup，并说明显式关闭内嵌 cleanup 是为了避免默认行为扩散。
3. 更新 `test_cuda_sm86_lowering.py`，保持顺序列表不变，补断言 raw marker 中三处 `symbol-hoist-pipeline` 均带 `cse=false` / `canonicalize=false` 或等价稳定打印。
4. 核对 CUDA pipeline 仍不包含 `memory-pool`，C5 all-TLM1 transform rule 不变。

### S5：边界、质量与敏感面自检

- 为什么做：本计划涉及公开 pipeline 行为、dump marker 数量变化和 local-only expectation，必须严格防止混入 unrelated 改动。
- 做什么：执行 diff 反推测试、repo conformance、KCE gate、合同验收和敏感范围 diff 检查。
- 不做什么：不把 `expectation/` 失败当成 diff 反推测试；execute 不修改 expectation。
- 怎么验收：所有命令通过或记录明确环境阻塞；`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md` 无 diff；`expectation/` 只保持已授权 local-only 物化状态，不进入 cached / unstaged diff。
- 卡住问谁：latest main 或 unrelated 工作区状态导致门禁失败时，先记录 actual / expected / diff，再问管理员 / 架构师；合同验收语义争议问用户 / 架构师。

详细执行步骤：
1. 运行 diff 反推 pytest：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/passes/test_symbol_loop_hoist.py \
  test/passes/test_symbol_hoist_pipeline.py \
  test/passes/pipeline/test_npu_demo_lowering.py \
  test/passes/pipeline/test_cuda_sm86_lowering.py \
  test/passes/test_registry.py \
  test/dialect/symbol/test_symbol.py
```

2. 运行仓库边界门禁：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/repo_conformance/test_private_api_boundaries.py \
  test/tools/test_kernel_code_error_static_gate.py
```

3. 运行合同验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist.if_branch_no_hoist
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist.memory_presence_guard
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.symbol.operation.fold.min
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.symbol.operation.fold.max
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.symbol.operation.fold
```

4. 检查敏感范围：

```bash
git diff -- .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md
git diff --cached -- .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md
git diff --cached --name-status -- expectation
git diff --name-status -- expectation
git status --short --ignored --untracked-files=all -- expectation
```

## 验收设计

- diff 反推测试：
  - 必须覆盖修改过的 `spec`、实现、pipeline tests、pass tests 和 dialect tests。
  - 必须覆盖 `fold=false` registry 构造仍可用，且 `symbol-hoist-pipeline={fold=false}` 仍按 `cse` / `canonicalize` 默认值执行内嵌 cleanup。
  - 必须覆盖直接构造 `SymbolHoistPipelinePass(fold=False)` 仍执行默认内嵌 cleanup。
  - 必须覆盖 `symbol-hoist-pipeline={cse=false}` 跳过 CSE、`symbol-hoist-pipeline={canonicalize=false}` 跳过末尾 canonicalize、两个选项均 false 时只运行 hoist rewrite。
  - 必须覆盖 `SymbolHoistPipelinePass.from_options(...)` 对 `cse` / `canonicalize` 的 bool 解析、未知 option 失败、直接传 `fold` 失败，以及 registry 外层 `fold=false` 和 pass 专属 option 混用。
  - 必须覆盖 `cuda-sm86-lowering` 显式 `cse=false` / `canonicalize=false` 后仍保留旧外置 cleanup 顺序和 dump marker。
  - 必须覆盖 `symbol.min` full-tile fold、`symbol.min` symbolic count dynamic step full-tile fold、`symbol.max` 静态 fold，以及动态 / unknown / iter / result mismatch 的保守拒绝 fold。
  - 本轮不得要求 `LoopSoftPipelinePass(fold=False)` normalization 行为测试，因为本轮不改 `LoopSoftPipelinePass`。
- dump 验收：
  - 运行 npu-demo matmul dump，确认 symbol-hoist 后不再有独立 cleanup marker。
  - 确认 `producer-consumer-analysis` 仍位于 `loop-soft-pipeline` 后、`memory-pool` 前。
  - 确认 marker 计数符合 S4 矩阵。
- 合同验收：
  - 旧 hoist local-only expectation 必过。
  - `symbol.operation.fold.min`、`symbol.operation.fold.max` 与聚合入口必过。
  - expectation 保持 ignored local-only，不进入 staged diff。

## 待确认项

### 已确认协同项：并入 hoist 改动一起推进

- 结论：本计划不能按完全独立后续任务推进，应与 hoist 改动合并成同一条计划级 execute 口径。

### Q1 已收口：三段 `symbol-hoist-pipeline` 都内嵌 cleanup

- 结论：采用选项 A，三段都内嵌 cleanup，删除三段后置顶层 `cse -> canonicalize`。

### Q2 已收口：`LoopSoftPipelinePass` 本轮不做 normalization

- 结论：不修改 `LoopSoftPipelinePass`，不新增 loop-soft pass-local normalization。
- 用户确认来源：用户最新回复“`LoopSoftPipelinePass 不做`”。

### Q3 已收口：`fold` 不控制 cleanup，新增 `cse` / `canonicalize`

- 结论：`fold` 只控制通用 folding；`symbol-hoist-pipeline` 新增 `cse` / `canonicalize` bool 选项控制内嵌 cleanup，默认均为 `True`；化简归属为 `symbol.min/max` op 自身 fold。

### Q4 已收口：本轮添加对应 expectation

- 结论：用户已授权添加 `symbol.min/max` fold 对应 expectation；execute 等非架构角色仍不得修改 expectation。

### Q5 已收口：保留 memory-pool 后顶层 cleanup

- 结论：保留。

### 当前待确认项

- 无。

## 迭代审阅记录

- 当前状态：Draft 2-R3 是公开 API 与 expectation 合同的实质修订；Draft 2-R1 / Draft 2-R2 的 subagent 与守护结论只作为历史输入，不再放行当前版本。Draft 2-R3 已完成 Round 5-A / Round 5-B strict review 收敛。
- 下一步：基于 Draft 2-R3 最新正文和 Round 5 收敛结论，请求 `守护最好的爱莉希雅` 本人执行守护最终检验。
- 每轮 strict review 标准包至少包含：
  - 根 `AGENTS.md`
  - 榕角色 prompt
  - `agents/standard/计划书标准.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/expectation任务规则.md`
  - 本 Draft 2-R3 全文
  - 旧 Draft 1-R1/G2 历史只读摘要
  - 当前用户确认来源与 Q1-Q5 结论
  - 禁止修改面
  - 必过验收命令
  - 严格通过口径

### Draft 2 Round 1-A：Fermat strict review

- 审阅对象：`Fermat / 019ec1a8-f6b9-7912-ba72-87237838f936`。
- 审阅输入：Draft 2 两份计划、根 `AGENTS.md`、榕 prompt、计划书标准、审查规范、实现文件规范、spec 文件规范、expectation 任务规则、用户最新决策、禁止修改面和必过验收命令。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 证据摘要：
  - staged candidate 仅两份计划；unrelated unstaged deletion `kernel/dump/.../24-multi-buffer-analysis-if-path-expected.mlir` 不属于本候选。
  - 六个 expectation manifest hash 与计划一致，均为 ignored local-only，`git ls-files --stage` 无输出，expectation cached / unstaged diff 均为空。
  - `git diff --cached --check`、`git diff --check` 均通过。
  - 两条 `symbol_loop_hoist` expectation、`fold.min`、`fold.max`、`fold` 聚合入口均通过。
- 主线处理：无需修改。
- 状态：通过；结果纳入 Draft 2-R1 审阅记录。

### Draft 2 Round 1-B：Copernicus strict review

- 审阅对象：`Copernicus / 019ec1a9-69d6-7720-a9e1-61f80aae80d9`。
- 审阅输入：Draft 2 两份计划、根 `AGENTS.md`、榕 prompt、计划书标准、审查规范、实现文件规范、spec 文件规范、expectation 任务规则、用户最新决策、禁止修改面和必过验收命令。
- 结论：不通过。
- 阻断项：无方向性阻断。
- 最小需改项：
  1. S0-S5 小任务卡缺少 `卡住问谁`。
  2. S3 短口径“补 `test_symbol.py` 与 local-only expectation”容易让 execute 误以为可修改 expectation。
  3. 当前 unrelated unstaged deletion 未在 Draft 2 候选状态中写清排除口径，守护最终检验证据不够自包含。
- 待确认项：无。
- 主线处理：
  1. Draft 2-R1 为 S0-S5 全部补齐 `卡住问谁`。
  2. Draft 2-R1 将 S3 改为“补 `test_symbol.py`，只读运行并记录架构已物化的 local-only expectation”，并保留 execute 不得修改 expectation 的边界。
  3. Draft 2-R1 新增候选状态记录：cached candidate 仅两份计划，unrelated dump expected 删除不得 stage / merge，expectation 仍为 ignored local-only，并要求守护请求现场重算候选 evidence。
- 状态：已主线修订，需 Draft 2-R1 复审。

### Draft 2-R1 Round 2-A：Fermat strict review

- 审阅对象：`Fermat / 019ec1a8-f6b9-7912-ba72-87237838f936`。
- 审阅输入：最新 staged Draft 2-R1 两份计划、Round 1 问题与主线修订摘要、根 `AGENTS.md`、榕 prompt、计划书标准、审查规范、实现文件规范、spec 文件规范、expectation 任务规则、用户最新决策、禁止修改面和必过验收命令。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 证据摘要：
  - staged candidate 仍仅两份计划；unrelated dump expected 删除只在 unstaged diff，未进入 cached diff。
  - 敏感范围 `.skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md expectation` cached / unstaged diff 为空。
  - 六个 expectation 均为 ignored local-only，`git ls-files --stage -- expectation/...` 无输出，hash 与 manifest 一致。
  - 五个 expectation 入口均通过。
- 内容核对摘要（历史 Draft 2-R1 口径，不适用于 Draft 2-R3 新增 `cse` / `canonicalize` option 后的下发判断）：
  - Copernicus Round 1 三项最小需改已收口：S0-S5 均有 `卡住问谁`；S3 已改为补 `test_symbol.py` 并只读运行 / 记录架构已物化 expectation；候选状态写清 cached 仅两份计划、unrelated deletion 排除、expectation ignored local-only。
  - 用户最新决策保持一致：1A、`LoopSoftPipelinePass` 不做、默认 `fold=true`、化简下沉到 `symbol.min/max` fold、添加对应 expectation。
- 状态：通过。

### Draft 2-R1 Round 2-B：Copernicus strict review

- 审阅对象：`Copernicus / 019ec1a9-69d6-7720-a9e1-61f80aae80d9`。
- 审阅输入：最新 staged Draft 2-R1 两份计划、Round 1 问题与主线修订摘要、根 `AGENTS.md`、榕 prompt、计划书标准、审查规范、实现文件规范、spec 文件规范、expectation 任务规则、用户最新决策、禁止修改面和必过验收命令。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 证据摘要：
  - `git diff --cached --name-status` 仅两份计划 `A`；`git diff --name-status` 仅 unrelated unstaged 删除 `kernel/dump/.../24-multi-buffer-analysis-if-path-expected.mlir`。
  - `git diff --cached --check` / `git diff --check` 通过。
  - 敏感范围 `.skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md expectation` cached / unstaged diff 均为空。
  - 六项 expectation 均为 ignored local-only，`git ls-files --stage -- expectation/...` 无输出，hash 与计划 manifest 一致。
  - 两条 `symbol_loop_hoist` expectation、`fold.min`、`fold.max`、`fold` 聚合入口均通过。
- 内容核对摘要：
  - S0-S5 均补齐 `卡住问谁`，并按用户 / 架构师 / 管理员区分卡点。
  - S3 已改为“补 `test_symbol.py`，只读运行并记录架构已物化的 local-only expectation”，不再暗示 execute 可修改 expectation。
  - 候选状态已写清 cached 仅两份计划、unrelated dump expected 删除不得 stage / merge、expectation ignored local-only，并要求守护请求现场重算证据。
  - 用户最新决策保持一致。
- 状态：通过。

### Draft 2-R1 subagent 收敛结论（历史）

- 已完成 Draft 2 / Draft 2-R1 strict review：
  - Draft 2 Round 1-A `Fermat / 019ec1a8-f6b9-7912-ba72-87237838f936`：通过；无阻断、无最小需改项、无待确认项。
  - Draft 2 Round 1-B `Copernicus / 019ec1a9-69d6-7720-a9e1-61f80aae80d9`：不通过；无方向性阻断，3 项最小需改已在 Draft 2-R1 主线修订。
  - Draft 2-R1 Round 2-A `Fermat / 019ec1a8-f6b9-7912-ba72-87237838f936`：通过；无阻断、无最小需改项、无待确认项。
  - Draft 2-R1 Round 2-B `Copernicus / 019ec1a9-69d6-7720-a9e1-61f80aae80d9`：通过；无阻断、无最小需改项、无待确认项。
- 收敛结论：所有已发起且计划要求的 subagent strict review 均已无阻断、无最小需改项、无待确认项；可请求 `守护最好的爱莉希雅` 执行守护最终检验。
- Draft 2-R3 修订说明：该收敛结论只适用于 Draft 2-R1；Draft 2-R3 新增公开 `cse` / `canonicalize` option 与 `symbol.min` symbolic count expectation，因此必须重新 strict review，不能沿用该结论下发。

### Draft 2-R3 Round 3-A：Newton strict review

- 审阅对象：`Newton / 019ec425-a8c4-7d81-bb0b-b67ebd975f7d`。
- 审阅输入：Draft 2-R3 staged 计划、根 `AGENTS.md`、榕 prompt、计划书标准、审查规范、实现文件规范、spec 文件规范、expectation 任务规则、用户 2026-06-14 最新口径、禁止修改面和必过验收命令。
- 结论：不通过。
- 阻断项：无方向性阻断。
- 最小需改项：
  1. 计划新增 `symbol-hoist-pipeline` 的 registry option，但未把 `spec/pass/registry.md` 纳入目标 spec / S1 / 验收，也未记录 `SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass` 或等价公开构造路径。
  2. `SymbolHoistPipelinePass()` 默认行为变更会影响 `cuda-sm86-lowering` 三处默认构造；计划只覆盖 npu-demo，未说明 CUDA 是继承新默认还是显式保留旧外置 cleanup。
  3. 下发前置把 Draft 2-R3 写成“已完成两轮 subagent strict review 和守护通过”，但当前仍处于 Round 3 审阅中，状态自相矛盾。
- 待确认项：无新增用户决策项；以上可按既有用户口径和仓库公开 API 规则修订。
- 证据摘要：
  - `git diff --cached --check -- ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md` 与 `git diff --check -- ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md` 通过。
  - 敏感范围 cached / unstaged diff 为空。
  - 六项 expectation hash 与 manifest 一致且均为 ignored local-only。
  - 审阅过程中 staged blob 从早前候选漂移到 `9e590cbf3af16856450382ab5bff0a7314e04ef8`；后续必须重新冻结候选证据。
- 主线处理：
  1. 已把 `spec/pass/registry.md` 纳入目标 spec，并在公开 API / S1 / S2 / 验收中补 `from_options(...)`、registry option、未知 option / 非 bool 错误语义和 `test_registry.py` 覆盖。
  2. 已把 `spec/pass/pipeline/cuda_sm86_lowering.md`、`kernel_gen/pipeline/cuda_sm86_lowering.py`、`test/passes/pipeline/test_cuda_sm86_lowering.py` 纳入目标范围；计划要求 CUDA 显式 `cse=False, canonicalize=False`，保留旧外置 cleanup。
  3. 已将下发前置改为“当前尚未完成重新 strict review 收敛，不能通知管理员下发；下发前必须完成两轮 subagent strict review 与守护本人终检”。
- 状态：已主线修订；需重新 stage 并基于最新冻结候选发起下一轮 strict review。

### Draft 2-R3 Round 3-B：Turing strict review

- 审阅对象：`Turing / 019ec426-1b0d-76e0-ae0b-81c71fef0ee7`。
- 审阅输入：Draft 2-R3 staged 计划、根 `AGENTS.md`、榕 prompt、计划书标准、审查规范、实现文件规范、spec 文件规范、expectation 任务规则、用户 2026-06-14 最新口径、禁止修改面和必过验收命令。
- 结论：不通过。
- 阻断项：
  1. 审阅对象在 review 过程中从 staged blob `14c71583cbf483f5499d994cdcc3ecd0e30f71c1` 变化为 `9e590cbf3af16856450382ab5bff0a7314e04ef8`，不能对原固定候选给出通过结论。
- 最小需改项：
  1. Draft 2-R3 候选状态记录中仍保留 Draft 2-R1 G1 历史句“其中仅两条计划属于本轮正式候选”，会误导当前候选边界。需改为 Draft 2-R1 当时口径，并重申 Draft 2-R3 当前正式候选只有本计划一份。
- 待确认项：
  - 需确认后续 strict review 使用重新冻结后的最新 staged blob / sha256。
- 证据摘要：
  - 公开 API 口径自洽：`cse` / `canonicalize` 有 2026-06-14 用户确认来源，S1 / S2 / S5 覆盖 spec、registry option、非法 bool、`fold=false` 不控制 cleanup 的测试要求。
  - Pre-Execute expectation 门禁基本正确：只要求 manifest、ignored local-only、无 diff，不要求新增 min expectation 在 execute 前通过；最终五条 expectation 仍列为必过。
  - 当前只读 expectation 结果符合正文记录：hoist 两条与 `fold.max` 通过，`fold.min` 和聚合入口失败于 symbolic count dynamic step case，该失败是 execute 合同缺口。
- 主线处理：
  - 已将 Draft 2-R1 G1 历史句改为“当时 / Draft 2-R1 正式候选”，并重申 Draft 2-R3 当前正式候选只有本计划一份。
  - Round 3-B 不作为通过依据；需在 Round 3-A / 3-B 最小需改项全部修订后重新冻结候选并发起下一轮 strict review。

### Draft 2-R3 Round 4-A / 4-B：stale review attempts

- 审阅对象：`Euclid / 019ec43c-6ad6-7361-a30f-31d373d97753` 与 `Curie / 019ec445-20f9-7870-a870-60f8cc6711bb`。
- 触发背景：在 Round 3-B 主线修订后曾尝试发起下一轮 strict review，但随后 Round 3-A 返回新的最小需改项，导致该轮候选失效。
- 结果：两名 subagent 均因 `503 Service Unavailable` 失败，且审阅对象已被 Round 3-A 修订要求 invalidated。
- 主线处理：
  - 不把该轮计入 Draft 2-R3 strict review 收敛。
  - 不因 subagent 服务错误降级或绕过审阅流程。
  - 待本轮计划修订完成、候选重新 staged 冻结后，重新发起两轮有效 subagent strict review。

### Draft 2-R3 Round 5-A：Newton strict review

- 审阅对象：`Newton / 019ec425-a8c4-7d81-bb0b-b67ebd975f7d`。
- 审阅输入：固定 staged 候选 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`，blob `7d5746126e7f3fec16e3b57d17c0e236053f4f3b`，sha256 `9b0c96d92ea116b1bf7b62a55fa7b6a9053b00eff8bf335784398ed82960dab3`；标准包、Round 3-A / 3-B 问题与主线处理、用户 2026-06-14 最新口径、禁止修改面和必过验收命令。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 证据摘要：
  - Round 3-A 三项已收口：`registry.md` / `from_options` / `test_registry.py` 纳入，CUDA 显式 `cse=False, canonicalize=False` 保留外置 cleanup，下发前置改为 strict review / 守护通过前不得下发。
  - Round 3-B 已收口：历史 Draft 2-R1 候选边界不再误导 Draft 2-R3 当前候选，本轮正式候选仅本计划。
  - `cse` / `canonicalize` 有用户确认来源；`from_options` 作为现有 registry pass-specific option 机制承载路径，授权链自洽。
  - 六项 expectation 均为 ignored local-only，`git ls-files --stage` 无输出，hash 与 manifest 一致；`fold.min` 当前失败被计划定位为 execute 合同缺口。
  - S0-S5 / S4b 可执行，验收覆盖 diff 反推 pytest、repo conformance / KCE gate、合同 expectation 与敏感范围检查。
- 主线处理：无需修改技术方案、公开 API、任务卡或 expectation 口径；仅将 Round 5-A 结论写入本节。

### Draft 2-R3 Round 5-B：Turing strict review

- 审阅对象：`Turing / 019ec426-1b0d-76e0-ae0b-81c71fef0ee7`。
- 审阅输入：固定 staged 候选 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`，blob `7d5746126e7f3fec16e3b57d17c0e236053f4f3b`，sha256 `9b0c96d92ea116b1bf7b62a55fa7b6a9053b00eff8bf335784398ed82960dab3`；标准包、Round 3-A / 3-B 问题与主线处理、用户 2026-06-14 最新口径、禁止修改面和必过验收命令。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 证据摘要：
  - registry / `from_options` / `test_registry.py` 已进入目标范围、公开 API 和 S1 / S2 / S5 验收。
  - `from_options` 授权链合理：用户确认新增 `cse` / `canonicalize` registry option，现有 registry 规则要求非 `fold` option 由 pass `from_options(options)` 承载。
  - CUDA 影响面已收口为保守兼容：显式 `cse=False, canonicalize=False`，保留外置 cleanup。
  - 下发前置已改为 strict review 收敛和守护最终检验通过前不得下发。
  - expectation 口径自洽：授权范围、Pre-Execute 物化门禁、execute 前不要求新增 `fold.min` 通过、最终五条合同验收必过均已写清。
  - S0-S5 / S4b 可执行，diff 反推测试、合同验收和敏感范围检查分开。
- 主线处理：无需修改技术方案、公开 API、任务卡或 expectation 口径；仅将 Round 5-B 结论写入本节。

### Draft 2-R3 subagent 收敛结论

- 已发起审阅任务：
  - Round 3-A `Newton`：不通过；3 项最小需改已在主线修订。
  - Round 3-B `Turing`：不通过；候选漂移与历史表述问题已在主线修订。
  - Round 4-A / 4-B `Euclid` / `Curie`：stale review attempts，均因 503 失败且候选已失效；不计入收敛，不作为降级依据。
  - Round 5-A `Newton`：通过；无阻断、无最小需改项、无待确认项。
  - Round 5-B `Turing`：通过；无阻断、无最小需改项、无待确认项。
- 收敛结论：Draft 2-R3 当前全部有效 strict review 均已收敛为无阻断、无最小需改项、无待确认项；当前待用户决策项为无。
- 后续门禁：必须由 `守护最好的爱莉希雅` 本人执行守护最终检验并回执通过后，才允许通知管理员创建唯一计划级 execute。

### Draft 2-R3 守护最终检验

- 结论人：`守护最好的爱莉希雅`。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 守护核对候选：
  - 正式候选仅 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`。
  - staged blob：`cb28905437dc565c0bd107f481b0486048d39069`。
  - staged sha256：`32a0a5277d4f8d74c3cdffb512674fc0681aa8876b2d78b09c30bddf1b75b120`。
- 通过摘要：
  - 标准包、公开 API 与授权链、expectation 权限、禁止修改面、Round 5 收敛记录、unrelated staged 路径隔离、验收命令和 S0-S5 / S4b 任务卡均核对通过。
  - `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md` 与 `ARCHITECTURE/plan/symbol_loop_hoist_if_branch_no_hoist.md` 仅为 unrelated staged independent files，不纳入本计划证据。
  - unrelated unstaged deletion `kernel/dump/.../24-multi-buffer-analysis-if-path-expected.mlir` 未 staged，不属于本计划候选。
  - 六项 expectation hash 与 manifest 一致，均为 ignored local-only；execute / review / archive_acceptance / merge / 管理员只能读取、运行、引用和记录，不得修改、新建、移动、删除或重命名 expectation。
  - 当前 `fold.min` 与 fold 聚合入口失败于新增 symbolic-count dynamic-step case，该失败已定位为 Draft 2-R3 execute 要修复的合同缺口；Pre-Execute 只校验 local-only 物化 / 隔离，最终 execute / review / archive_acceptance 必须五条 expectation 全部通过。
- 允许事项：
  - 允许榕通知管理员创建唯一计划级 execute `npu-demo-embedded-cleanup-symbol-minmax-fold`。
  - 计划书字段必须是 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`。
  - 不得沿旧 `T-20260613-56f5a699` 作为本计划链路，不得创建第二个并行 npu_demo execute。
  - 创建后必须先保持未分发或暂停；待架构师在目标 worktree 按 Draft 2-R3 Pre-Execute local-only expectation 物化门禁完成 manifest / hash、status、check-ignore、ls-files 空输出、scope diff 和记录后，管理员才可分发或恢复 execute。

### Draft 2-R1 守护最终检验（历史）

- 历史状态：G1 / G2 / G3 不通过项已按守护允许口径修订候选状态说明，G4 复验通过；该通过只适用于 Draft 2-R1 当时的“承接旧链路”口径。
- G1 回执摘要：
  - 结论：不通过。
  - 阻断项：全量 cached diff 除两份正式候选计划外，还包含 unrelated staged `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`；而 Draft 2-R1 请求与正文声明 cached candidate / cached diff 仅两份计划，证据不自洽。
  - 最小需改项：将该 unrelated staged 文件移出 index，或在计划正文与复验请求中明确该 staged 文件为独立现场且不得混用，并重新提供全量 cached diff、两条候选路径 ls-files / staged sha256、diff check、敏感范围和 expectation manifest / 运行证据。
  - 待确认项：无。
- G1 主线处理：
  - 本轮不移动、不 unstage unrelated staged `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`，避免改动他人或其它计划的 staged 现场。
  - Draft 2-R1 候选状态记录已明确：本轮正式候选仅两份计划；`multi_buffer_apply_fixed_reserved_before_auto.md` 是 unrelated staged file，不属于本计划 execute / review / 守护 / merge 证据，不得混用。
  - G2 复验请求必须附全量 cached diff、unrelated staged file blob / sha256、两份正式候选 blob / sha256、diff check、敏感范围空 diff和 expectation manifest / 运行证据。
- G2 回执摘要：
  - 结论：不通过。
  - 阻断项：G1 的候选隔离口径已按允许方式写入正文，但计划正文和 G2 请求中记录的 unrelated staged file 固定 blob / sha256 与最新现场不一致，候选现场证据仍不自洽。
  - 最小需改项：不需要移动或 unstage 该 unrelated staged 文件；移除计划正文里对 unrelated 文件的固定 blob / sha，只保留路径级独立现场说明并要求请求现场实时附证据；随后重新提供全量 cached diff、三条 staged 路径当前 ls-files / sha256、两份正式候选路径证据、diff check、敏感范围空 diff 和 expectation manifest / 运行证据。
  - 待确认项：无。
- G2 主线处理：
  - Draft 2-R1 已移除 unrelated staged file 的固定 blob / sha256，只保留路径级独立现场说明和“复验请求现场实时附证据”的要求。
- G3 回执摘要：
  - 结论：不通过。
  - 阻断项：G2 修复已完成，但 G3 复验请求仍附带 unrelated staged file 的实时 blob / sha256；该 unrelated 文件在守护复验过程中被其它流程更新，导致请求证据、守护首次读取和守护最终读取互不一致。
  - 最小需改项：不需要移动或 unstage unrelated staged 文件；先让 unrelated staged 文件稳定，或在请求中明确其由其它流程持续更新、守护只按路径级隔离且不核其 blob / sha256 稳定性；随后重新提供最新全量 cached diff、三条 staged 路径当前 ls-files / sha256、两份正式候选路径证据、diff check、敏感范围空 diff 和 expectation manifest / 运行证据。
  - 待确认项：无。
- G3 主线处理：
  - 本轮继续不移动、不 unstage unrelated staged `ARCHITECTURE/plan/multi_buffer_apply_fixed_reserved_before_auto.md`。
  - Draft 2-R1 候选状态已改为路径级隔离口径：该 unrelated staged file 只需证明未纳入本计划候选、不得混入 execute / review / 守护 / merge 证据；其 blob / sha256 可作为复验请求现场参考，但不作为本计划稳定门禁。
  - G4 复验请求必须显式请求守护只对本轮两份正式候选核验 blob / sha256 稳定性；对 unrelated staged file 仅核验路径级隔离，不因其它流程在守护期间更新该文件而阻断本计划。
- G4 回执摘要：
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 允许事项：允许通知管理员进入同一暂停任务链 `T-20260613-56f5a699` 的恢复 / 退回 execute 前置流程；该允许事项仅适用于 Draft 2-R1 当时的“承接旧链路”口径。

### Draft 2-R2 任务身份修正

- 触发原因：
  - 2026-06-14 用户指出 `T-20260613-56f5a699` 的 `计划书` 字段仍为 `ARCHITECTURE/plan/symbol_loop_hoist_if_branch_no_hoist.md`，不是 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md`。
  - 用户确认继续推进本计划，但不能把旧窄计划任务链等同于本计划已经正式下发。
- 主线处理：
  - Draft 2-R2 将正式下发口径改为：以 `ARCHITECTURE/plan/npu_demo_embedded_cleanup_iter_normalization.md` 自身作为计划书字段创建唯一计划级 execute。
  - 旧任务链 `T-20260613-56f5a699` 必须 hold / 暂停，不得继续 review / archive_acceptance / merge，不得作为本计划归档链路。
  - 技术方案、公开 API 口径、`LoopSoftPipelinePass` 不做、默认 `fold=true`、`symbol.min/max` fold 合同、expectation 授权、S0-S5 小任务卡均保持 Draft 2-R1 G4 通过版本不变。
  - 本修正只改变任务身份、worktree / 记录路径建议和下发门禁，不改变实现方案。
- Draft 2-R3 作废口径：
  - Draft 2-R2 的“待守护复核后可按本计划字段创建 execute”口径已被 Draft 2-R3 supersede。
  - 旧链路 hold / 暂停要求继续有效；但不得再依据 Draft 2-R2 请求管理员创建 execute。
  - Draft 2-R2 记录中的“默认 `fold=true`”仅为历史技术口径；Draft 2-R3 当前口径是 `fold` 不控制 cleanup，`cse` / `canonicalize` 控制 cleanup。
- Draft 2-R2 守护复核回执：
  - 结论：不通过。
  - 阻断项：守护复核时现场 `expectation/dialect/symbol/operation/fold/min.py` sha256 已变为 `519af471c73fa881bee923636fe3a1e53cf05cd6c59db1bad75fbaf66d111ce9`，与 Draft 2-R2 manifest 旧值 `74a8e7b7be444e2ae92887585678bf44464230efa7007e1f670923728fa0a07d` 不一致；且 `expectation.dialect.symbol.operation.fold.min` 与聚合入口失败。
  - 失败摘要：新增 case `dialect-symbol-operation-fold-min-full_tile_symbolic_count_dynamic_step-1` 报 `KernelCodeError: symbol.min result type must match canonical symbol expression`；旧 hoist 两条 expectation 与 `fold.max` 通过。
  - 守护最小需改项：按 Draft 2-R2 manifest 重新物化 / 复核 expectation，或更新计划 manifest 与合同口径并说明授权来源，然后重新提供 hash、ignored/local-only/ls-files 空输出、敏感范围空 diff 和五条当前必过 expectation 通过证据。
  - Draft 2-R3 主线处理：不再尝试修复 Draft 2-R2 后下发；该失败已由 Draft 2-R3 收口为新用户授权合同，manifest 更新为新 hash，Pre-Execute 门禁改为只验证 local-only 物化与 diff 隔离，不要求新增 fold expectation 在 execute 前通过；新增 fold expectation 失败被明确记录为 execute 目标合同缺口。
  - 允许事项：当前不允许通知管理员创建 `npu-demo-embedded-cleanup-symbol-minmax-fold` execute；也不得沿旧 `T-20260613-56f5a699` 链路继续作为本计划归档链路。

## 用户确认与协同约束

- 当前 Draft 2-R3 已取得用户公开 API 与 expectation 授权确认：新增 `cse` / `canonicalize` option，`fold` 不控制 cleanup，新增 `symbol.min` symbolic count dynamic step full-tile expectation。
- 用户已确认本计划应包含 hoist 改动一起推进；Q1-Q5 已按 Draft 2-R3 口径收口为无待确认项。
- Draft 2-R3 已重新完成两轮 subagent strict review 收敛；下一步请求 `守护最好的爱莉希雅` 本人守护最终检验。
- 守护最终检验通过后，只通知管理员按本计划书字段创建唯一计划级 execute；不得继续沿用旧窄任务链作为本计划下发链路，不得创建第二个并行 npu_demo execute。
- execute / review / archive_acceptance / merge / 管理员不得修改本计划书正文，除非按流程回到架构修订。
