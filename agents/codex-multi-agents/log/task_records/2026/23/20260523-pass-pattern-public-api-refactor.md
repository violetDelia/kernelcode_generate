# T-20260524-c906a59e / pass-pattern-public-api-refactor

## 2026-05-24 小李飞刀 execute 开工记录

- 任务 ID：`T-20260524-c906a59e`
- 任务类型：`execute`
- worktree：`/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/23/20260523-pass-pattern-public-api-refactor.md`
- 合同真源：主仓只读计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md`
- worktree 内计划资产：缺失；沿用共享计划资产模式，只读引用主仓计划，不复制、不同步、不修改计划书。
- 基线：`HEAD=origin/main=merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`ahead/behind=0/0`。
- 任务目标：按计划一次完成全部小任务卡，公开 `kernel_gen/passes/**` 下所有 `RewritePattern` pattern 到各自 canonical module path，补齐 getter、`__all__`、文件级 API 列表、spec API、每个 pattern 的 MLIR before/after 文档与实现注释，并跑通 pytest、只读 expectation、静态门禁与敏感目录空 diff。
- 禁止修改面：不得修改、复制、新建、移动或删除 `expectation/`、`.skills/`、`agents/standard/**`。

## 执行前阅读

- 已读 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`。
- 已读 `AGENTS.md`。
- 已读主仓 `TODO.md`：`T-20260524-c906a59e` 为进行中 execute，指派 `小李飞刀`。
- 已读主仓计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md`。
- 已核对当前任务记录原先不存在，本文件按管理员指定路径创建。

## 2026-05-24 01:17 小李飞刀 execute 阶段记录

时间：2026-05-24 01:17 +0800

经办人：小李飞刀

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

任务目标：按主仓只读计划完成计划级 execute 候选 diff，并在只读 expectation 失败时按流程暂停转管理员 / 架构师确认。

改动：

- 实现公开 API：
  - 将 `hoist_dma_alias_ops.py`、`outline_device_kernel.py`、`symbol_buffer_hoist.py`、`nn_lowering.py` 及 nn lowering child module 中原私有 `RewritePattern` class 去掉前导下划线，保持语义名最小变化。
  - 补齐 `get_hoist_dma_alias_ops_pass_patterns(...)`、`get_outline_device_kernel_pass_patterns(...)`，保留既有 getter / family 名。
  - 同步各实现文件文件级 `API 列表`、class / getter docstring 与 `__all__`。
  - `kernel_gen/passes/__init__.py` 与 `kernel_gen/passes/lowering/nn_lowering/__init__.py` 仅补文档说明，不全量重导出 child pattern，未删除既有稳定 re-export。
- spec / registry：
  - 更新 `spec/pass/registry.md` 的 pattern canonical module path 原则。
  - 更新目标 pass / nn lowering / tile / decompass / buffer out-param spec API 列表和旧口径文字。
  - 为计划覆盖的每个公开 pattern 补 `Pattern MLIR before / after 合同`；rewrite / no-op 写 before + after 两个 `mlir` block，reject 写 before `mlir` 与公开错误文本。
  - 显式覆盖 `TunerParamHoistPattern`。
- 测试：
  - 新增 `test/passes/test_pattern_public_api_docs.py`，机械锁定 52 个公开 `RewritePattern` canonical module path、`__all__`、getter 顺序 / fresh instance、旧私有名不可访问、spec MLIR before/after / reject 文档窗口。
  - 更新 `test/passes/test_outline_device_kernel.py` 的旧隐藏 pattern 断言为公开 pattern / getter 断言，并保留旧私有名负例。
- 禁止修改面：候选 diff 未修改 `expectation/`、`.skills/`、`agents/standard/**`。

验证：

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`：exit 0，`2 passed, 1 warning`；锁定公开 pattern import、getter、`__all__`、旧私有名负例与 spec MLIR 文档门禁。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...`（计划列出的 15 个 pass 实现文件）：exit 0。
- `! rg -n 'class _[A-Za-z0-9_]*Pattern\\(RewritePattern\\)|def _get_.*patterns\\(|pattern.*不公开|私有 pattern|不提供公开 pattern getter|只保留 .*_patterns\\(' kernel_gen/passes spec/pass`：exit 0，旧口径静态门禁无命中。
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard && git diff --cached --name-only -- expectation .skills agents/standard && git status --short --untracked-files=all -- expectation .skills agents/standard && git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：exit 0，输出为空；敏感目录候选 diff / staged / untracked / ignored 均为空。
- 计划最低 pytest + 新增文档门禁：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py test/passes/test_hoist_dma_alias_ops.py test/passes/test_outline_device_kernel.py test/passes/test_symbol_buffer_hoist.py test/passes/test_symbol_loop_hoist.py test/passes/test_buffer_results_to_out_params.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py test/passes/lowering/nn_lowering/test_public_name.py test/passes/lowering/nn_lowering/test_nn_lowering.py test/passes/lowering/nn_lowering/test_asset_cases.py test/passes/test_registry.py`
  - 第一次运行：exit 1，`280 passed, 2 failed`；失败为 `test_outline_device_kernel.py` 仍按旧口径要求 pattern / getter 隐藏。
  - 修复测试旧口径后复跑：exit 0，`282 passed, 1 warning`。
- Diff 反推自测：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`：exit 0，`126 passed, 1 warning`；覆盖 nn lowering child pattern 改名、公开 `__all__`、family getter 与旧私有名负例。
- 只读 expectation：
  - 执行方式：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor:/home/lfr/kernelcode_generate python3 -m <module>`，其中 `kernel_gen.*` 由任务 worktree 导入，`expectation.*` 由主仓导入。
  - 通过入口：`expectation.pass.outline_device_kernel`、`expectation.pass.symbol_buffer_hoist`、`expectation.pass.symbol_loop_hoist`、`expectation.pass.decompass`、`expectation.pass.buffer_results_to_out_params`、`expectation.pass.lowing.nn_lowering` 均运行到对应入口完成，未报失败。
  - 失败入口 1：`expectation.pass.hoist_dma_alias_ops` exit 1；失败摘要：`pass-hoist_dma_alias_ops-slice` 中 2 个 case 失败，动态 weight slice 仍为高维 `dma.slice`，未命中期望的低维 slice / `symbol.mul` check。
  - 失败入口 2：`expectation.pass.tile` exit 1；失败摘要：`pass.tile.analysis` 下 matmul reduce / reduce exprs 多 case 因 `kernel.matmul` 的 `tile.tile_exprs` 文本与 check-next 期望不一致失败。
  - 基线复现：用主仓 main 代码原样复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops` 与 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`，两者同样 exit 1，失败类型与摘要一致；因此当前判断不是本轮候选 diff 引入的行为回归，而是当前主仓 expectation 与基线实现 / 合同已有不一致。

Diff 反推自测：

- 改动文件覆盖面：pass 实现公开 API / `__all__`、spec API 与 MLIR 文档、registry 公开路径文档、outline 测试旧口径、公开 API/docs 新测试。
- 反推测试：
  - 新增 `test_pattern_public_api_docs.py` 验证所有目标 pattern 的公开路径、旧私有名负例、getter 顺序和文档门禁。
  - 更新并复跑 `test_outline_device_kernel.py`，验证旧“pattern 隐藏”断言已收口为公开 pattern / getter。
  - 补跑完整 `test/passes/lowering/nn_lowering`，覆盖 nn lowering child pattern 改名和 family getter。
  - 复跑计划最低集合，覆盖受影响 pass 行为、registry 与 package import 边界。
- 未能完成项：计划列为必跑的只读 expectation 全量未通过；失败已确认在主仓 main 同样复现，需管理员 / 架构师确认是否作为当前任务阻断、是否调整 expectation scope 或另行修复既有合同。

自检：

- 接口：本轮新增 / 公开 API 均来自用户确认和计划书，未新增计划外公开接口；getter 保留既有 family 名，缺失处补 `get_<pass>_patterns(...)`。
- 边界 / 异常：reject pattern 文档写明公开错误文本；旧私有名负例已由新增测试覆盖；未修改 pass name、registry option、pipeline 顺序或 IR 语义。
- 兼容：`kernel_gen/passes/__init__.py` 与 `nn_lowering/__init__.py` 未全量 re-export pattern，未删除既有稳定 re-export。
- 实现遗漏 / 冗余：52 个 `RewritePattern` class 已纳入公开矩阵；`TunerParamHoistPattern` 已覆盖；未把非 pattern helper 公开或跨文件调用私有 helper。
- 注释准确性：实现文件 API 列表、class / getter docstring 与 spec API 同步；spec 为 pattern 写 before/after / reject 合同。
- 测试有效性：新增测试会在 pattern 未导出、旧私有名仍存在、getter 顺序错误或 spec 缺 MLIR 文档时失败；最低 pytest 与 nn lowering 全目录通过。
- 资源 / 并发 / 性能：本轮仅公开 API、文档和测试矩阵，不引入长生命周期资源、并发或性能路径变化。
- 敏感目录：`expectation/`、`.skills/`、`agents/standard/**` 候选 diff 为空。

结论：

- 代码 / spec / pytest / 静态门禁已形成可审候选。
- 因计划必跑只读 expectation 中 `hoist_dma_alias_ops` 与 `tile` 在任务 worktree 和主仓 main 均失败，且任务明确要求 expectation 冲突时暂停回报，当前不执行 `-next review`。
- 已准备向管理员 `神秘人` 与架构师回报：需确认是否将这两个既有 expectation 失败从本轮阻断中豁免 / 调整 expectation scope，或先分发单独修复既有合同后再继续本任务。

## 2026-05-24 大闸蟹架构口径补充 / 当前阻断

- 用户反馈：本计划要求在“实现的 pattern”中给出 IR before / after 示例，当前候选实现未体现。
- 复核结论：反馈成立。当前候选 diff 主要把 spec 侧补了 `mlir` before / after，但多个实现侧 `RewritePattern` class docstring 只写自然语言概述，没有按计划写清触发前 IR 与改写后 IR 示例。
- 合同依据：主仓计划 `ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md` 明确要求“每个 pattern 的实现注释必须同步写清 pattern 做了什么、触发前 IR 形态和改写后 IR 形态、no-op / reject 条件；注释可以使用精简 MLIR 片段，但必须能和 spec 中的 before / after case 对上”。
- 抽查证据：
  - `kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py` 中 `LowerNnAddPattern`、`LowerNnSubPattern`、`LowerNnMulPattern` 等 class docstring 只有“lowering 为 kernel.binary_elewise”描述，没有 before / after IR 示例。
  - `kernel_gen/passes/outline_device_kernel.py::OutlineDeviceKernelFuncPattern` 只有“带 launch attr 的 func.func @k 变为 host wrapper @k 与 device func @k_device”描述，没有对应 before / after IR 片段。
  - `kernel_gen/passes/hoist_dma_alias_ops.py`、`kernel_gen/passes/symbol_buffer_hoist.py`、`kernel_gen/passes/lowering/nn_lowering/{select_cast_lowering,dma_structured_lowering,matmul_img2col_lowering,reduce_softmax_lowering,nn_lowering}.py` 同类 pattern docstring 也缺少显式 before / after。
- 最小返工动作：
  1. 为本轮公开 / 改名 / 纳入公开 API 的每个 `RewritePattern` class，在实现 class docstring 的 `功能说明` 中补精简 IR before / after 示例；可以用最小 MLIR 片段，不要求完整可 parse，但必须能与对应 spec 的 before / after case 对上。
  2. 同一 family 可共享模板，但每个 pattern class docstring 必须能看出自己的 op kind 或 reject/no-op 语义，例如 `LowerNnAddPattern` 写 `nn.add -> dma.alloc + kernel.binary_elewise(kind="add")`，`LowerNnEqPattern` 写 compare 路径与 kind。
  3. reject pattern 写 before IR + 公开错误文本，不伪造 after rewrite；no-op pattern 写 before + unchanged after。
  4. 补或调整静态门禁，至少能防止只在 spec 中补 before / after 而实现 class docstring 缺失的假绿。
  5. 任务记录补 `Diff 反推自测`，说明实现注释门禁与相关 pytest / 静态扫描结果。
- 验收方式：review / 架构复核必须抽查实现 class docstring 与 spec before / after 是否一一对得上；实现侧缺少 before / after 示例时不得通过。

## 2026-05-24 01:29 小李飞刀 execute 返工记录

时间：2026-05-24 01:29 +0800

经办人：小李飞刀

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

任务目标：按用户 / 架构补充口径，补齐实现侧 `RewritePattern` class docstring 的 IR before / after 或 reject 合同，并补防假绿门禁。

改动：

- 实现注释返工：
  - 为本轮纳入公开矩阵的 52 个 `RewritePattern` class docstring 补 `IR before:` / `IR after:` fenced `mlir` 示例。
  - rewrite pattern 示例与对应 spec before / after case 对齐；同一 family 使用统一模板，但每个 class 都体现自身 op kind，例如 `nn.add -> kernel.binary_elewise(kind="add")`、`nn.eq -> kind="eq"`、`nn.truediv -> kind="div"`。
  - reject pattern `RejectUnsupportedNnOpPattern` 与 `RejectNnSoftmaxPattern` 补 before `mlir` 和公开错误文本，不伪造 after IR。
  - 含 no-op 边界的 pattern 在 docstring 中写明 `no-op unchanged after`，例如 alias hoist、symbol hoist、tile analysis / elewise / reduce、outline-device-kernel。
- 门禁返工：
  - 扩展 `test/passes/test_pattern_public_api_docs.py`，新增 `test_pass_pattern_implementation_docstrings_have_ir_contracts`。
  - 新门禁用 `inspect.getdoc(...)` 逐个检查公开 pattern class：非 reject 必须有 `IR before:`、`IR after:`、至少两个 fenced `mlir` block 与 class 对应 op/kind token；reject 必须有 `IR before:`、至少一个 fenced `mlir` block、公开错误文本与对应 op/error token。

验证：

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`：
  - 返工前新增门禁失败，定位到实现侧 docstring 缺失。
  - 补齐后复跑 exit 0，`3 passed, 1 warning`；锁定 spec 文档与实现 docstring 双门禁。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/passes/outline_device_kernel.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/passes/symbol_loop_hoist.py kernel_gen/passes/buffer_results_to_out_params.py kernel_gen/passes/decompass.py kernel_gen/passes/tile/analysis.py kernel_gen/passes/tile/elewise.py kernel_gen/passes/tile/reduce.py kernel_gen/passes/lowering/nn_lowering/nn_lowering.py kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`：exit 0。
- `! rg -n 'class _[A-Za-z0-9_]*Pattern\\(RewritePattern\\)|def _get_.*patterns\\(|pattern.*不公开|私有 pattern|不提供公开 pattern getter|只保留 .*_patterns\\(' kernel_gen/passes spec/pass`：exit 0。
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard && git diff --cached --name-only -- expectation .skills agents/standard && git status --short --untracked-files=all -- expectation .skills agents/standard && git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：exit 0，输出为空。
- 计划最低 pytest + 新门禁：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py test/passes/test_hoist_dma_alias_ops.py test/passes/test_outline_device_kernel.py test/passes/test_symbol_buffer_hoist.py test/passes/test_symbol_loop_hoist.py test/passes/test_buffer_results_to_out_params.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py test/passes/lowering/nn_lowering/test_public_name.py test/passes/lowering/nn_lowering/test_nn_lowering.py test/passes/lowering/nn_lowering/test_asset_cases.py test/passes/test_registry.py`：exit 0，`283 passed, 1 warning`。
- Diff 反推自测：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`：exit 0，`126 passed, 1 warning`。

Diff 反推自测：

- 实际新增 / 修改：实现 pattern class docstring、公开 API/docs 测试门禁。
- 反推依据：若任一公开 pattern class 只在 spec 补 before / after、实现 docstring 缺失，新增门禁会失败；若 class docstring 未体现自身 op kind 或 reject 公开错误文本，新增门禁会失败。
- 未重跑只读 expectation：本次返工仅改 docstring 与测试门禁，不改运行时行为；上一轮只读 expectation 的 `hoist_dma_alias_ops` 与 `tile` 失败已在主仓 main 原样复现，仍需管理员 / 架构师确认处理口径。

自检：

- 接口：未新增计划外公开 API；仅补实现注释和测试门禁。
- 边界：reject / no-op / rewrite 三类文档形态已分别覆盖；`RejectUnsupportedNnOpPattern` 使用实际公开错误文本 `unknown op: ...`，`RejectNnSoftmaxPattern` 使用 `nn.softmax must be decomposed before lower-nn`。
- 兼容：未修改 pass name、registry option、pipeline 顺序或 IR 语义。
- 注释准确性：实现 docstring 中的 before / after 与 spec case 同类对齐，family 内每个 pattern 都体现自身 op kind。
- 测试有效性：新增门禁能防止“只补 spec、不补实现 docstring”的假绿。
- 敏感目录：`expectation/`、`.skills/`、`agents/standard/**` 仍为空 diff。

结论：

- 用户 / 架构指出的实现 docstring IR before / after 缺失已返工收口。
- 当前仍不送 review，原因保持为上一轮记录的只读 expectation 既有失败阻断：`expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 在任务 worktree 和主仓 main 均失败，需管理员 / 架构师确认是否豁免 / 调整 scope / 另行修复。

## 2026-05-24 大闸蟹 expectation 既有失败隔离裁定

- 复核背景：小李飞刀回报实现侧 pattern docstring before / after 已收口，但计划只读 expectation 中 `expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 在任务 worktree 和主仓 main 均失败，请求确认豁免 / 调整 scope / 另修复。
- 独立复跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`：exit 1。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`：exit 1。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`：exit 1。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`：exit 1。
- 失败同源：
  - `hoist_dma_alias_ops` 均失败于 `pass-hoist_dma_alias_ops-slice`，动态 weight slice 未降维、`symbol.mul` check 未命中，任务 worktree 与主仓 main 失败摘要一致。
  - `tile` 均失败于 `pass.tile.analysis` 下 matmul reduce / reduce exprs 的 `tile.tile_exprs` 文本 check，任务 worktree 与主仓 main 失败类别一致；符号名 / memory space 存在随机化差异，不影响同源判断。
- 候选 diff 触及面复核：
  - `kernel_gen/passes/hoist_dma_alias_ops.py` 本轮改动为 pattern class 去私有前缀、补公开 getter、`__all__` 与 docstring IR before / after；未改 `_rewrite_view_deslice_grouping(...)`、reshape/fill 改写算法或 slice 动态降维算法。
  - `kernel_gen/passes/tile/{analysis,elewise,reduce}.py` 本轮改动为实现 docstring IR before / after；未改 tile analysis / elewise / reduce 的运行时算法。
- 架构裁定：
  - 不把这两条 latest-main 既有 expectation 失败扩展为当前 `pass-pattern-public-api-refactor` 的 execute 修复项；当前计划目标是 pattern 公开 API、getter、`__all__`、spec / docstring before-after 与测试门禁，不应顺手修复 `hoist_dma_alias_ops` 动态 slice 或 `tile` matmul reduce 合同。
  - 不修改、不同步、不豁免 `expectation/` 本体；`expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 不能记录为通过项，只能记录为 latest-main 既有失败隔离。
  - 可以进入 review，但 review 必须复核本节隔离结论：候选未引入运行时行为改动、同源失败在主仓 main 可复现、其它计划 pytest / py_compile / 静态门禁 / 敏感目录空 diff 均通过。
  - 若 review 发现候选实际改动了失败相关算法、失败数量 / 类别较 main 扩大，或敏感目录出现 diff，则必须退回 execute；否则这两条 expectation 失败不阻断本轮进入 review。
- 后续建议：`hoist_dma_alias_ops` 动态 slice 合同与 `tile` matmul reduce expectation 可另行建独立行为 / 合同修复计划；不并入本轮公开 API refactor。

## 2026-05-24 01:33 小李飞刀 execute 最终收口记录

时间：2026-05-24 01:33 +0800

经办人：小李飞刀

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

任务目标：根据大闸蟹架构裁定解除 expectation 既有失败阻断，补齐最终 execute 记录并送 review。

改动：

- 本轮 execute 候选最终保持以下交付：
  - 公开 `kernel_gen/passes/**` 下全部目标 `RewritePattern` 到各自 canonical module path。
  - 补齐 getter、`__all__`、文件级 `API 列表`、spec API、registry 公开路径说明。
  - 为 spec 和实现 class docstring 双侧补 pattern IR before / after 或 reject 公开错误文本。
  - 新增公开 API / spec MLIR / 实现 docstring 机械门禁。
  - 更新旧测试口径，确保 `OutlineDeviceKernelFuncPattern` 和 getter 作为公开 API，而旧私有名不可访问。
- 只读 expectation 处理：
  - `expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 不记为通过项。
  - 按大闸蟹裁定，这两项记录为 latest-main 既有失败隔离：任务 worktree 与主仓 main 均 exit 1，且本轮未修改相关运行时算法，不并入本轮 execute 修复项。
  - 不修改、不同步、不复制 `expectation/`。

验证：

- 已完成并记录的通过项：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`：exit 0，`3 passed, 1 warning`。
  - 计划最低 pytest + 新门禁：exit 0，`283 passed, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`：exit 0，`126 passed, 1 warning`。
  - 计划列出的 15 个 pass 实现文件 `py_compile`：exit 0。
  - 旧口径静态门禁 `rg`：exit 0。
  - `git diff --check`：exit 0。
  - `expectation/.skills/agents/standard` diff / staged / untracked / ignored 核对：exit 0，输出为空。
- 只读 expectation 隔离项：
  - `expectation.pass.hoist_dma_alias_ops`：任务 worktree与主仓 main 均 exit 1，同源失败于 dynamic slice 相关 expectation。
  - `expectation.pass.tile`：任务 worktree与主仓 main 均 exit 1，同源失败于 tile analysis matmul reduce / reduce exprs 文本 check。
  - 按架构裁定，review 必须复核同源失败、候选未扩大失败面，不能把这两条写成通过。

Diff 反推自测：

- 公开 API / getter / `__all__` / 旧私有名负例：由 `test_pattern_public_api_docs.py` 覆盖。
- spec 与实现文档合同：由 `test_pattern_public_api_docs.py` 同时检查 spec 文档窗口与实现 class docstring。
- nn lowering child pattern 改名和 family getter：由完整 `test/passes/lowering/nn_lowering` 覆盖。
- 受影响 pass 行为与 registry：由计划最低 pytest 集覆盖。

自检：

- 接口：公开 API 变更均有用户确认与计划授权；未新增计划外公开接口。
- 边界：reject / no-op / rewrite 文档形态均有测试门禁；旧私有名负例覆盖。
- 兼容：未修改 pass name、registry option、pipeline 顺序或 IR 语义。
- 实现：未跨文件调用非公开 helper；未公开非 pattern helper。
- 测试：新增门禁能防止 spec-only 假绿与实现 docstring 缺失假绿。
- 敏感目录：`expectation/`、`.skills/`、`agents/standard/**` 候选 diff 为空。

结论：

- execute 阶段已收口，可进入 review。
- 下一阶段 review 重点：复核公开 API / `__all__` / getter / spec / 实现 docstring 是否一致；复核 latest-main 既有 expectation 失败隔离是否成立；复核候选未扩大 `hoist_dma_alias_ops` 与 `tile` 失败面；复核其它 pytest、py_compile、静态门禁、敏感目录空 diff与任务记录完整性。

## 2026-05-24 01:34 管理员恢复 execute 同步

- 管理员 `神秘人` 已同步：`T-20260524-c906a59e` 按大闸蟹裁定解除暂停并恢复 execute。
- expectation 口径再次确认：`expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 在候选 worktree 和主仓 main 均失败，失败同源，判定为 latest-main 既有失败隔离；本轮不扩展为行为合同修复，不改 `expectation/`。
- 下一步：按正常流程进入 review；review 必须复核该隔离结论，且这两条不能作为通过项记录。

---

## 2026-05-24 01:46 +0800 不要啊教练 review 记录

时间：2026-05-24 01:46 +0800
经办人：不要啊教练
任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`
任务目标：审查公开 `RewritePattern` API、getter、`__all__`、文件级 `API 列表`、spec API、实现 class docstring IR before/after、MLIR 文档门禁、公开导入矩阵、Diff 反推自测、静态门禁、敏感目录空 diff，并复核 `expectation.pass.hoist_dma_alias_ops` / `expectation.pass.tile` latest-main 既有失败隔离。

### 审查范围

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor`。
- 计划书：主仓只读 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md`；worktree 内计划资产缺失，符合执行记录写明的共享计划资产模式。
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/23/20260523-pass-pattern-public-api-refactor.md`。
- 被审 diff：`kernel_gen/passes/**` 公开 pattern / getter / docstring、`spec/pass/**` API 与 MLIR 合同、`test/passes/test_outline_device_kernel.py`、新增 `test/passes/test_pattern_public_api_docs.py`、本任务记录。

### 最新同步现场

- 命令：`git fetch origin --prune && git status --short --branch --untracked-files=all && git rev-parse HEAD origin/main $(git merge-base HEAD origin/main)`。
- 结果：exit=0；`HEAD=origin/main=merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`。
- 当前候选范围：34 个 tracked 文件修改，2 个 untracked 文件：本任务记录与 `test/passes/test_pattern_public_api_docs.py`。

### Findings

- 阻断 1：公开 pattern 的 spec API 与文件级 `API 列表` 没有列齐公开方法签名。
  - 证据：
    - 计划书要求：`ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md:118-123` 写明每个 rewrite / no-op / reject pattern 的公开 spec 必须包含 pattern 名称、构造签名、`match_and_rewrite(...)` 签名。
    - 标准要求：`agents/standard/实现文件规范.md:11` 写明 class 场景必须逐条列类公开方法签名。
    - 抽查 1：`spec/pass/lowering/nn_lowering/element_binary_lowering.md:9-22` 只列 `class LowerNn*Pattern()` 与 `element_binary_patterns()`，`API详细说明` 也只覆盖 getter，未列 11 个 `LowerNn*Pattern.match_and_rewrite(...)`。
    - 抽查 2：`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py:14-26` 文件级 `API 列表` 同样只列 class 与 getter，未列公开 pattern 方法。
    - 抽查 3：`spec/pass/symbol_loop_hoist.md:9-25` 与 `kernel_gen/passes/symbol_loop_hoist.py:11-24` 只列 11 个公开 pattern class 与 getter，未列 `match_and_rewrite(...)`。
    - 机械复核命令：用 `test/passes/test_pattern_public_api_docs.py` 中的 pattern 清单反查 spec / 实现文件是否包含 `<Pattern>.match_and_rewrite(`。
    - 结果：spec 缺 34 个 pattern 方法签名，分布于 `spec/pass/symbol_loop_hoist.md`、`spec/pass/lowering/nn_lowering/{element_binary_lowering,select_cast_lowering,dma_structured_lowering,matmul_img2col_lowering,reduce_softmax_lowering}.md`；实现文件级 API 列表缺 44 个 pattern 方法签名，分布于 `symbol_loop_hoist.py`、`buffer_results_to_out_params.py`、`decompass.py`、`tile/{analysis,elewise,reduce}.py` 与 nn lowering child modules。
  - 影响：公开 API 合同不完整；调用方、测试和后续 review 无法从 spec / 文件级 `API 列表` 判断 pattern class 的公开方法边界，未满足本计划的 “spec API / 文件级 API 列表” 完成态。
  - 最小返工动作：按 pattern 清单补齐对应 spec `API 列表` / `API详细说明` 和实现文件级 `API 列表` 中的 `match_and_rewrite(...)` 签名；已有 spec 已列签名的文件保持一致，不需要扩大公开面到非 pattern helper。
  - 验收方式：新增或扩展静态门禁，按公开 pattern 矩阵检查每个 spec 和实现文件级说明均包含对应 `class ...` 与 `<Pattern>.match_and_rewrite(...)`；review 复跑该门禁应不再报告缺口。

- 阻断 2：新增 MLIR / docstring 门禁存在假绿，未覆盖上述 API 签名缺口，也不能证明每个 pattern 的 spec 合同完整。
  - 证据：
    - `test/passes/test_pattern_public_api_docs.py:316-326` 对 spec 的检查只要求 pattern 名称附近存在 `before` / `after` 与两个 fenced `mlir` block，或 reject 附近存在 `before` / `公开错误文本`；它不检查 `match_and_rewrite(...)` 签名，也不检查文件级 `API 列表`。
    - 实际运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`：exit=0，`3 passed, 1 warning`，但上面的机械复核仍发现 spec 缺 34 个方法签名、实现文件级 API 列表缺 44 个方法签名。
    - 示例：`spec/pass/lowering/nn_lowering/element_binary_lowering.md:94-130` 采用 family mapping + 两个示例 block，门禁会让 `LowerNnSubPattern` 等 pattern 通过窗口检查，但没有对应 `LowerNnSubPattern.match_and_rewrite(...)` API 条目。
  - 影响：当前 `Diff 反推自测` 对 “spec API / 文件级 API 列表” 的断言有效性不足，无法防止本轮已经出现的合同缺口再次进入 review。
  - 最小返工动作：扩展 `test_pattern_public_api_docs.py` 或等价本地测试脚本，至少检查：
    - 每个公开 pattern 在 spec 中有 class 构造签名和 `match_and_rewrite(...)` 签名；
    - 每个公开 pattern 在实现文件级 `API 列表` 中有 class 与公开方法签名；
    - 每个 pattern 的 spec MLIR 合同能定位到该 pattern 对应的 op/kind 或 reject 错误文本，避免只靠同一 family 的其它示例让窗口检查通过。
  - 验收方式：先在当前缺口上看到新增门禁失败，再补齐文档后复跑通过；任务记录写清失败样例和通过结果。

### 执行记录核对

- 已读取管理员创建记录、execute 开工记录、execute 阶段记录、用户 / 架构关于实现 docstring IR before/after 的返工口径、大闸蟹 expectation 既有失败隔离裁定、execute 最终收口记录。
- 执行记录包含执行前阅读、计划内小任务、Diff 反推自测、合同验收、敏感目录空 diff、自检和 latest-main 既有失败隔离说明。
- 记录中 `expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 已明确“不记为通过项”，符合管理员特别要求。

### Diff 反推审查与验证

- 候选范围：
  - 命令：`git -c core.quotepath=false diff --stat HEAD && git -c core.quotepath=false diff --name-status HEAD && git ls-files --others --exclude-standard`
  - 结果：exit=0；tracked diff 为 34 个文件、`1763 insertions(+), 158 deletions(-)`；untracked 为本任务记录与 `test/passes/test_pattern_public_api_docs.py`。
- 公开 pattern / 旧私有名静态扫描：
  - 命令：`rg -n 'class _[A-Za-z0-9_]*Pattern\\(RewritePattern\\)|def _get_.*patterns\\(|pattern.*不公开|私有 pattern|不提供公开 pattern getter|只保留 .*_patterns\\(' kernel_gen/passes spec/pass || true`
  - 结果：exit=0，输出为空；未发现旧私有 pattern class、旧私有 getter 或旧“不公开 pattern”口径残留。
- 新增文档门禁：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`
  - 结果：exit=0，`3 passed, 1 warning`；但该门禁未覆盖 Findings 中的 API 签名缺口，不能作为通过依据。
- 计划最低 pytest + 新门禁：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py test/passes/test_hoist_dma_alias_ops.py test/passes/test_outline_device_kernel.py test/passes/test_symbol_buffer_hoist.py test/passes/test_symbol_loop_hoist.py test/passes/test_buffer_results_to_out_params.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py test/passes/lowering/nn_lowering/test_public_name.py test/passes/lowering/nn_lowering/test_nn_lowering.py test/passes/lowering/nn_lowering/test_asset_cases.py test/passes/test_registry.py`
  - 结果：exit=0，`283 passed, 1 warning`。
- Diff 反推补跑：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`
  - 结果：exit=0，`126 passed, 1 warning`。
- py_compile：
  - 命令：计划列出的 15 个 pass 实现文件 `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...`
  - 结果：exit=0。
- 文本与敏感目录：
  - 命令：`git diff --check && git diff --cached --check`
  - 结果：exit=0。
  - 命令：`git diff --name-only -- expectation .skills agents/standard && git diff --cached --name-only -- expectation .skills agents/standard && git status --short --untracked-files=all -- expectation .skills agents/standard && git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：exit=0，输出为空。
  - 扩展禁止面命令：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan && git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan && git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`
  - 结果：exit=0，输出为空。
- expectation latest-main 既有失败隔离复核：
  - 候选：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`：exit=1；失败于 `pass-hoist_dma_alias_ops-slice`，`symbol.mul` check 未命中。
  - 主仓 main：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`：exit=1；同样失败于 `pass-hoist_dma_alias_ops-slice`，`symbol.mul` check 未命中。
  - 候选：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`：exit=1；失败于 `pass.tile.analysis` 下 matmul reduce / reduce exprs 的 `CHECK-NEXT` 文本不匹配。
  - 主仓 main：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`：exit=1；同样失败于 `pass.tile.analysis` 下 matmul reduce / reduce exprs 的 `CHECK-NEXT` 文本不匹配。
  - 结论：两条 expectation 只能记录为 latest-main 既有失败隔离；不作为通过项。本轮阻断来自文档 / API 合同缺口，不来自这两条 expectation。

### 自检

- 已基于最新 `origin/main=6369c235736e89499d6c1fc2b7b8bc19f2b564fe` 审查。
- 已读取实际 diff、计划书、执行记录和架构裁定，不只依赖执行人摘要。
- 已核对公开 `RewritePattern` class 去私有前缀、getter、`__all__`、旧私有名静态扫描和候选范围。
- 已核对敏感目录与禁止修改面为空 diff。
- 已复核 `expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 在候选和主仓 main 均失败且失败同源，候选未扩大为不同失败类别；两条不记为通过项。
- 因存在两个可执行返工项，结论不得写通过，也不得进入架构复核 / 终验。

### 结论

结论：不通过。

最小返工项：
1. 补齐公开 pattern 的 spec API 与实现文件级 `API 列表` 中缺失的 `match_and_rewrite(...)` 公开方法签名。
2. 扩展文档 / API 门禁，使其能机械发现上述缺口，并锁住每个 pattern 的 spec API 与 pattern-specific MLIR / reject 合同。

本任务应回到 `execute` 收口；收口后 review 复审再判断是否可进入架构复核 / 终验。

---

## 2026-05-24 01:57 +0800 小李飞刀 execute 返工收口记录

时间：2026-05-24 01:57 +0800

经办人：小李飞刀

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

任务目标：修复 review 阻断项：补齐公开 `RewritePattern` 在 spec API 与实现文件级 `API 列表` 中的 `match_and_rewrite(...)` 方法签名，并扩展门禁机械检查 spec API、实现 API 列表和 pattern-specific MLIR / reject 合同。

改动：

- 扩展 `test/passes/test_pattern_public_api_docs.py`：
  - 从实现源码 AST 提取每个公开 pattern 的真实 `match_and_rewrite(op: ..., rewriter: PatternRewriter) -> None` 签名。
  - 检查对应 spec 的 `## API 列表` 必须包含 pattern class 和公开方法签名。
  - 检查对应实现文件级 docstring 的 `API 列表` 必须包含 pattern class 和公开方法签名。
  - 检查 spec 的 pattern 文档窗口包含该 pattern 自身 op/kind token 或 reject 公开错误文本，避免 family 示例假绿。
- 补齐 spec API 与实现文件级 API 列表：
  - `symbol_loop_hoist` 的 11 个公开 hoist pattern。
  - `element_binary_lowering` 的 11 个公开 lower pattern。
  - `select_cast_lowering`、`dma_structured_lowering`、`matmul_img2col_lowering`、`reduce_softmax_lowering` 的公开 pattern。
  - `buffer_results_to_out_params`、`decompass`、`tile/{analysis,elewise,reduce}` 实现文件级 API 列表中缺失的 pattern 方法签名。
- 同步 `spec/pass/lowering/nn_lowering/spec.md` 中 `RejectUnsupportedNnOpPattern` 的 reject 公开错误文本 token 为 `unknown op: nn.unknown`，与实现 docstring 和运行时错误前缀一致。
- 本轮只改文档合同与测试门禁；未修改 pass name、registry option、pipeline 顺序、运行时算法或 `expectation/`。

先失败证明：

- 在只扩展门禁、尚未补文档前运行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`
  - 结果：exit 1，`2 failed, 2 passed, 1 warning`。
  - 失败样例 1：`spec/pass/symbol_loop_hoist.md` 缺 `SymbolConstHoistPattern.match_and_rewrite(op: SymbolConstOp, rewriter: PatternRewriter) -> None`。
  - 失败样例 2：`spec/pass/lowering/nn_lowering/spec.md` 的 `RejectUnsupportedNnOpPattern` 文档窗口缺 `unknown op` pattern-specific reject token。
- 该失败证明新增门禁能发现 review 指出的 spec API / 实现 API 列表缺口，并能锁住 reject 公开错误文本合同。

验证：

- 新增门禁：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`
  - 结果：exit 0，`4 passed, 1 warning`。
- 机械反查：
  - 使用 `test_pattern_public_api_docs.py` 的公开 pattern 清单与 AST 签名提取逻辑反查全部 spec API、实现文件级 API 列表和 spec token。
  - 结果：exit 0，`all pattern API list and spec token checks satisfied`。
- 计划最低 pytest + 新门禁：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py test/passes/test_hoist_dma_alias_ops.py test/passes/test_outline_device_kernel.py test/passes/test_symbol_buffer_hoist.py test/passes/test_symbol_loop_hoist.py test/passes/test_buffer_results_to_out_params.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py test/passes/lowering/nn_lowering/test_public_name.py test/passes/lowering/nn_lowering/test_nn_lowering.py test/passes/lowering/nn_lowering/test_asset_cases.py test/passes/test_registry.py`
  - 结果：exit 0，`284 passed, 1 warning`。
- Diff 反推补跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`
  - 结果：exit 0，`126 passed, 1 warning`。
- py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/passes/outline_device_kernel.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/passes/symbol_loop_hoist.py kernel_gen/passes/buffer_results_to_out_params.py kernel_gen/passes/decompass.py kernel_gen/passes/tile/analysis.py kernel_gen/passes/tile/elewise.py kernel_gen/passes/tile/reduce.py kernel_gen/passes/lowering/nn_lowering/nn_lowering.py kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`
  - 结果：exit 0。
- 静态旧口径扫描：
  - `rg -n 'class _[A-Za-z0-9_]*Pattern\(RewritePattern\)|def _get_.*patterns\(|pattern.*不公开|私有 pattern|不提供公开 pattern getter|只保留 .*_patterns\(' kernel_gen/passes spec/pass || true`
  - 结果：exit 0，输出为空。
- 文本与禁止面：
  - `git diff --check && git diff --cached --check`：exit 0。
  - `git diff --name-only -- expectation .skills agents/standard && git diff --cached --name-only -- expectation .skills agents/standard && git status --short --untracked-files=all -- expectation .skills agents/standard && git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：exit 0，输出为空。
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan && git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan && git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：exit 0，输出为空。
- 只读 expectation：
  - 本轮未把 `expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 记录为通过项。
  - 依据前序大闸蟹裁定与 review 复核，这两项仍只作为 latest-main 既有失败隔离：候选 worktree 与主仓 main 均 exit 1，失败同源；本轮返工未修改相关运行时算法，不改 `expectation/`。

Diff 反推自测：

- 实际新增 / 修改面：公开 pattern 文档门禁、spec API 列表、实现文件级 API 列表、reject 文档 token。
- 反推测试：
  - `test_pattern_public_api_docs.py` 覆盖公开 import / `__all__` / getter 顺序、spec MLIR / reject token、spec API 列表、实现文件级 API 列表、实现 class docstring IR 合同。
  - 计划最低 pytest 集覆盖受影响 pass 的行为回归、registry、公开导入和旧私有名负例。
  - `test/passes/lowering/nn_lowering` 补跑覆盖 nn lowering child pattern 改名、公开 family getter 和资产用例。
- 反推有效性：新增门禁在补齐前已真实失败，补齐后通过，能防止 `match_and_rewrite(...)` 方法签名缺失和 reject token 假绿再次进入 review。

自检：

- 接口：补齐的是计划 / review 已要求的公开 pattern 方法签名文档；未新增计划外公开对象、别名或顶层 re-export。
- 边界：rewrite、no-op、reject 三类合同继续由 spec / 实现 docstring 和门禁覆盖；`RejectUnsupportedNnOpPattern` reject 文本与实现 `unknown op: ...` 一致。
- 异常：未更改错误类型或运行时异常语义；`expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 仍按既有失败隔离处理。
- 兼容：未修改 pass name、registry option、pipeline 顺序或 IR 语义。
- 实现遗漏 / 冗余：用 AST 从源码反推出方法签名，减少手写门禁与实现漂移；未扩大检查到非 pattern helper。
- 注释准确性：文件级 API 列表和 spec API 列表均列出 class 与公开 `match_and_rewrite(...)` 方法签名。
- 复用 / 函数粒度：新增测试 helper 只服务本测试文件；未引入跨文件非公开 helper 调用。
- 输入输出 / 资源 / 并发 / 性能：本轮不改运行时输入输出、资源管理、并发或性能路径。
- 测试有效性：新增门禁先红后绿，并与计划最低 pytest、nn_lowering 目录补跑、py_compile、静态扫描、敏感目录检查形成闭环。

结论：

- review 两项阻断已按最小返工项收口。
- `expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 继续只作为 latest-main 既有失败隔离，不作为通过项。
- execute 可重新进入 review；review 重点复核新增门禁有效性、API 列表签名完整性、pattern-specific spec token、敏感目录空 diff和 expectation 隔离口径。

---

## 2026-05-24 02:07 +0800 不要啊教练 review 复审记录

时间：2026-05-24 02:07 +0800

经办人：不要啊教练

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

任务目标：复审 execute 返工是否闭合前次 review 阻断项：公开 `RewritePattern` 在 spec API 与实现文件级 `API 列表` 中补齐 `match_and_rewrite(...)` 签名，新增/扩展门禁能机械发现 spec API、实现 API 列表和 pattern-specific MLIR / reject token 缺口，并复核敏感目录空 diff 与 `expectation.pass.hoist_dma_alias_ops` / `expectation.pass.tile` latest-main 既有失败隔离。

复审结论：通过。

Findings：

- 未发现新的阻断项。
- 前次 review 两项阻断已闭合：
  - spec API 与实现文件级 `API 列表` 已包含公开 pattern class 与对应 `match_and_rewrite(op: ..., rewriter: PatternRewriter) -> None` 签名。
  - `test/passes/test_pattern_public_api_docs.py` 已扩展为 `4` 项门禁，覆盖公开 import / `__all__` / getter、spec MLIR / reject token、spec API 列表、实现文件级 API 列表与实现 class docstring IR 合同。

复审范围：

- 基线同步：`git fetch origin --prune` 后，候选 worktree `HEAD = origin/main = merge-base = 6369c235736e89499d6c1fc2b7b8bc19f2b564fe`；主仓 `/home/lfr/kernelcode_generate` 也在同一 `origin/main`。
- 计划书：候选 worktree 内无计划书副本，按任务记录沿用主仓只读 `ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md`。
- 候选 diff 覆盖 pass 实现公开 API / `__all__`、spec API 与文档、registry 公开路径文档、outline 测试旧口径调整，以及未跟踪新增 `test/passes/test_pattern_public_api_docs.py`；该未跟踪新增测试已纳入复审与单独 whitespace / AST 检查。
- 未修改 `expectation/`、`.skills/`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`ARCHITECTURE`。

Diff 反推审查：

- 独立机械反查：
  - 使用新增测试文件中的 `_PATTERN_MODULE_CASES` 与 AST 签名提取逻辑，逐项检查 spec API 与实现文件级 API 列表。
  - 结果：`missing_count=0`。
- 新增测试文件未跟踪，`git diff --check` 不会覆盖；已单独执行：
  - `git diff --no-index --check /dev/null test/passes/test_pattern_public_api_docs.py`：无 whitespace 问题。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... ast.parse(...) ... PY`：`ast_parse=ok`。
- AST 边界补查：
  - 变更实现文件无新增嵌套函数。
  - 未发现 `hasattr(ctx, ...)`、`getattr(ctx, ...)`、`callable(getattr(ctx, ...))` 或 `emit_barrier` 运行时能力探测分支。
  - 变更中存在的 `getattr` 用于 SSA/operation owner、parent block 或属性读取，不是 `ctx` 能力兼容分支；未作为阻断项。

复跑验证：

- 新增门禁：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`
  - 结果：exit 0，`4 passed, 1 warning`。
- 计划相关 pytest 扩展集：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py test/passes/test_registry.py test/passes/test_buffer_results_to_out_params.py test/passes/lowering/nn_lowering test/passes/test_outline_device_kernel.py test/passes/test_symbol_loop_hoist.py test/passes/test_hoist_dma_alias_ops.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py`
  - 结果：exit 0，`302 passed, 1 warning`。
- `nn_lowering` 目录补跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`
  - 结果：exit 0，`126 passed, 1 warning`。
- `symbol_buffer_hoist` 补跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py`
  - 结果：exit 0，`39 passed, 1 warning`。
- py_compile / 静态旧口径 / diff check：
  - `python3 -m compileall -q kernel_gen/passes test/passes spec/pass`：exit 0。
  - `rg -n 'class _[A-Za-z0-9_]*Pattern\(RewritePattern\)|def _get_.*patterns\(|pattern.*不公开|私有 pattern|不提供公开 pattern getter|只保留 .*_patterns\(' kernel_gen/passes spec/pass`：exit 1，输出为空，符合预期。
  - `git diff --check && git diff --cached --check`：exit 0。
- 敏感目录 / 禁止面：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan && git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan && git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`
  - 结果：exit 0，输出为空。

只读 expectation 隔离复核：

- 候选正确导入核对：以候选 worktree 为 `cwd` 且 `PYTHONPATH=.:/home/lfr/kernelcode_generate` 时，`kernel_gen.passes.hoist_dma_alias_ops` 与 `kernel_gen.passes.tile.analysis` 均从候选 worktree 导入；`expectation.pass.*` 从主仓只读 expectation 资产导入。
- `expectation.pass.hoist_dma_alias_ops`：
  - 候选：`PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`，workdir 为候选 worktree，exit 1。
  - 主仓：`PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=. python3 -m expectation.pass.hoist_dma_alias_ops`，workdir 为主仓，exit 1。
  - 两边同源失败于 `pass-hoist_dma_alias_ops-slice`：`symbol.mul` check 未命中，以及动态 conv2d weight slice 仍为高维 `dma.slice`，`low_rank_found=False, high_rank_found=True`。
- `expectation.pass.tile`：
  - 候选：`PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`，workdir 为候选 worktree，exit 1。
  - 主仓：前序复核在同一 `6369c235736e89499d6c1fc2b7b8bc19f2b564fe` 主仓基线复现 exit 1。
  - 两边同源失败于 `pass.tile.analysis` 下 matmul reduce / reduce exprs 的 `CHECK-NEXT` 文本不匹配。
- 上述两条仅记录为 latest-main 既有失败隔离，不作为通过项；本轮未修改 `expectation/`。

自检：

- 特殊情况：已按管理员特别要求把两条 expectation 失败单列为 latest-main 既有失败隔离，未混入通过项。
- 完整性：前次 review 阻断项、公开 API 文档一致性、门禁有效性、只读 expectation、敏感目录空 diff 均完成复核。
- 维护性：新增门禁从 AST 提取真实签名，能降低手写 API 列表漂移；pattern-specific token 检查能防止 family 示例假绿。
- 扩展性：公开 pattern 清单集中在测试矩阵，后续新增 pattern 时会被 import / `__all__` / getter / spec / 实现 docstring 门禁牵引。
- 测试有效性：新增门禁和相关 pytest 已复跑；未用 expectation 替代 Diff 反推测试。

结论：

- `T-20260524-c906a59e` review 复审通过。
- 这是计划级任务，review 通过后不直接进入 merge；应回报管理员接入架构复核 / 终验流程。

---

## 2026-05-24 02:10 +0800 不要啊教练 review 状态流转补记

时间：2026-05-24 02:10 +0800

经办人：不要啊教练

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

任务目标：按管理员补充要求复查 `TODO.md`，将已完成的计划级 review 复审通过结论用标准 `-next` 续接给管理员进入架构复核 / 终验。

改动：

- 复查主仓 `TODO.md`：任务仍为 `review / 进行中 / 指派 不要啊教练`，说明上轮复审通过记录与管理员回报已完成，但状态尚未用 `-next` 续接。
- 沿用 `2026-05-24 02:07 +0800` 复审结论：review 复审通过，无新增阻断项。

验证：

- 已读取主仓 `TODO.md`、`agents/codex-multi-agents/agents-lists.md` 与本任务记录尾部。
- 候选 worktree 基线仍为 `HEAD = origin/main = merge-base = 6369c235736e89499d6c1fc2b7b8bc19f2b564fe`。
- 本补记不重新审查业务 diff，不修改实现、spec、测试或 `expectation/`。

自检：

- 计划级 execute 落地后的 review 通过不得直接续接 merge；本次仅准备续接 `other` 给管理员处理架构复核 / 终验。
- 未手工修改 `TODO.md` 或人员状态文件；状态推进将使用标准脚本。

结论：

- 准备用 `codex-multi-agents-task.sh -next -type other -to 神秘人` 续接当前任务，并回报管理员。

---

## 2026-05-24 02:10 +0800 不要啊教练 review 状态推进结果

时间：2026-05-24 02:10 +0800

经办人：不要啊教练

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

任务目标：记录标准脚本状态推进结果，并回报管理员继续处理计划级架构复核 / 终验。

改动：

- 执行 `codex-multi-agents-task.sh -file TODO.md -next -task_id T-20260524-c906a59e -from 不要啊教练 -type other -to 神秘人 ...`。
- 脚本返回 `ERROR(3): task not found in running list: T-20260524-c906a59e`，但复查 `TODO.md` 后确认任务已从 `正在执行的任务` 移出，进入 `任务列表`：
  - 类型：`other`
  - 描述：`T-20260524-c906a59e / pass-pattern-public-api-refactor review 复审通过，请管理员接计划级架构复核 / 终验`
  - 当前指派：空
- 复查 `agents/codex-multi-agents/agents-lists.md`：`不要啊教练` 已恢复 `free`。

验证：

- `codex-multi-agents-task.sh -file TODO.md -status -doing`：当前 running 列表不再包含 `T-20260524-c906a59e`。
- `rg -n "T-20260524-c906a59e|不要啊教练|神秘人|大闸蟹" TODO.md agents/codex-multi-agents/agents-lists.md`：确认任务在 `任务列表`，`不要啊教练` 为 `free`，管理员 `神秘人` 当前 `busy`。

自检：

- 未直接续接 merge，符合计划级 review 通过后的流程要求。
- 当前任务已离开 review 阶段，但尚未被管理员/架构师领取；需用 talk 回报管理员处理下一步分发。

结论：

- review 职责已完成；状态已续接为待管理员处理的 `other` 任务，下一步回报管理员接架构复核 / 终验。

---

## 2026-05-24 02:27 +0800 大闸蟹第一轮架构复核 / 终验记录

时间：2026-05-24 02:27 +0800

结论人：大闸蟹

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

执行目录：`/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor`

计划书：主仓只读 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md`

记录文件：`agents/codex-multi-agents/log/task_records/2026/23/20260523-pass-pattern-public-api-refactor.md`

### latest 同步现场

- 已执行：`git fetch origin`
- 基线：
  - `HEAD=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`
  - `origin/main=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`
  - `merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`
  - `ahead/behind=0/0`
- `git diff --name-only HEAD..origin/main`：空。
- `git diff --cached --name-only`：空。
- 候选 diff：34 个 tracked 文件修改，2 个 untracked 文件：本任务记录与 `test/passes/test_pattern_public_api_docs.py`。

### 计划正文复核

- 公开 API 用户确认来源已在计划书记录：用户确认 scope 仅 `kernel_gen/passes/**`、所属模块 `__all__` 公开、不全量顶层 re-export、私有 pattern 去下划线、实现注释与 spec 都写 MLIR before/after、getter 保留既有名且只补缺失 getter。
- 候选实现符合方案 B：新增公开 pattern 保持 canonical module path，`kernel_gen/passes/__init__.py` 与 `kernel_gen/passes/lowering/nn_lowering/__init__.py` 只补“不全量重导出”说明，未全量重导出 child pattern，未删除既有稳定 re-export。
- 本轮未修改 pass name、registry option、pipeline 顺序或 expectation 合同资产。
- `RewritePattern` AST 复核：`kernel_gen/passes/**` 下公开 `RewritePattern` class 共 52 个，`private_count=0`。

### 复跑验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`：exit 0，`4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py test/passes/test_registry.py test/passes/test_buffer_results_to_out_params.py test/passes/lowering/nn_lowering test/passes/test_outline_device_kernel.py test/passes/test_symbol_loop_hoist.py test/passes/test_hoist_dma_alias_ops.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py`：exit 0，`302 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`：exit 0，`126 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py`：exit 0，`39 passed, 1 warning`。
- `python3 -m compileall -q kernel_gen/passes test/passes spec/pass`：exit 0。
- 旧口径扫描 `rg -n 'class _[A-Za-z0-9_]*Pattern\(RewritePattern\)|def _get_.*patterns\(|pattern.*不公开|私有 pattern|不提供公开 pattern getter|只保留 .*_patterns\(' kernel_gen/passes spec/pass`：exit 1，输出为空，符合预期。
- `git diff --check && git diff --cached --check`：exit 0。
- 未跟踪新增测试补查：
  - `git diff --no-index --check /dev/null test/passes/test_pattern_public_api_docs.py`：无 whitespace 输出。
  - `ast.parse(test/passes/test_pattern_public_api_docs.py)`：`ast_parse=ok`。
- 公开 pattern API 机械反查：复用 `test_pattern_public_api_docs.py` 的 pattern 清单与 AST 签名提取逻辑，反查 spec API、实现文件级 API 列表、`match_and_rewrite(...)` 签名，结果 `missing_count=0`。
- AST 边界补查：
  - 目标实现文件 `nested_function_count=0`。
  - `rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr\(ctx|emit_barrier' kernel_gen/passes test/passes/test_pattern_public_api_docs.py`：exit 1，输出为空。

### 只读 expectation 口径

- 通过项：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.decompass`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering`：exit 0。
- 隔离项：
  - 候选 `expectation.pass.hoist_dma_alias_ops`：exit 1；失败于 `pass-hoist_dma_alias_ops-slice`，`symbol.mul` check 未命中，动态 conv2d weight slice 仍为高维 slice。
  - 主仓 main `expectation.pass.hoist_dma_alias_ops`：exit 1；同源失败于 `pass-hoist_dma_alias_ops-slice`。
  - 候选 `expectation.pass.tile`：exit 1；失败于 `pass.tile.analysis` 下 matmul reduce / reduce exprs 的 `CHECK-NEXT` 文本不匹配。
  - 主仓 main `expectation.pass.tile`：exit 1；同源失败于 `pass.tile.analysis` matmul reduce / reduce exprs。
- 导入来源核对：候选运行时 `kernel_gen.passes.hoist_dma_alias_ops` 与 `kernel_gen.passes.tile.analysis` 从任务 worktree 导入；`expectation.pass.*.__main__` 从主仓 `/home/lfr/kernelcode_generate/expectation` 导入。
- 结论：`expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 只记录为 latest-main 既有失败隔离，不作为通过项；本轮未修改 `expectation/`。

### 敏感目录与禁止面

- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
- `git status --short --untracked-files=all -- kernel/dump`：空；本轮复跑 expectation 未在任务 worktree 留下候选 dump diff。

### Diff 反推终验

- `spec/pass/**` 与实现文件级 `API 列表` 已通过门禁锁定公开 pattern class 与 `match_and_rewrite(...)` 方法签名，前次 review 的 API 列表缺口已闭合。
- 实现侧 52 个公开 pattern class docstring 已通过门禁锁定 `IR before:` / `IR after:` 或 reject 公开错误文本，能防止只补 spec 不补实现注释的假绿。
- `test/passes/test_pattern_public_api_docs.py` 覆盖公开 import、`__all__`、getter 顺序 / fresh instance、旧私有名负例、spec MLIR/reject token、spec API 列表、实现文件级 API 列表与实现 docstring IR 合同。
- `test/passes/test_outline_device_kernel.py` 已从旧“隐藏 pattern helper”口径调整为公开 pattern / getter 断言，并保留旧私有名负例。
- 抽查 diff 显示运行时改动集中在 pattern class 去私有前缀、getter 公开、`__all__` 与 docstring；未发现本轮混入 `hoist_dma_alias_ops` 动态 slice 或 `tile` matmul reduce 运行时算法修复。

### 自检

- 已读取计划书、任务记录、review 与复审记录、候选 diff，不只依据管理员摘要。
- 已基于 latest 同步现场复核候选 diff，`HEAD` 与 `origin/main` 对齐。
- 已核对公开 API 变更均有计划和用户确认来源；无新增待用户确认项。
- 已核对实现未跨文件调用非公开 helper，测试未依赖旧私有 pattern 名。
- 已核对 `expectation/` 与敏感 / 禁止目录为空 diff，且未把 latest-main 既有 expectation 失败写成通过项。

### 结论

- 结论：`通过`
- 最小阻断项：无。
- 需用户确认项：无。
- 流转建议：第一轮计划级架构复核 / 终验通过；可进入第二轮架构终验。当前不进入 merge。

---

## 2026-05-24 02:35 +0800 守护最好的爱莉希雅第二轮架构复核 / 终验记录

时间：2026-05-24 02:35 +0800

结论人：守护最好的爱莉希雅

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

执行目录：`/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor`

计划书：主仓只读 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md`

记录文件：`agents/codex-multi-agents/log/task_records/2026/23/20260523-pass-pattern-public-api-refactor.md`

### latest 同步现场

- 已执行：`git fetch origin --prune`
- 任务 worktree 基线：
  - `HEAD=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`
  - `origin/main=bb874adfad94ea95697e08acc2bc12be5d34a52f`
  - `merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`
  - `ahead/behind=0/1`
- latest 主线相比任务基线的路径交集：
  - `kernel_gen/passes/tile/analysis.py`
  - `spec/pass/tile/analysis.md`
- 处理方式：未直接修改任务 worktree；创建临时 latest 集成 worktree `/tmp/ppapi-latest-validation/worktree`，以 `origin/main=bb874adfad94ea95697e08acc2bc12be5d34a52f` 为基线，用 `git apply --3way` 套用候选 tracked diff，并复制候选未跟踪测试 `test/passes/test_pattern_public_api_docs.py`。所有 tracked diff 均 clean apply，两个交集文件无文本冲突。
- 同源失败隔离基线：创建临时 clean latest worktree `/tmp/ppapi-latest-baseline`，`HEAD=bb874adfad94ea95697e08acc2bc12be5d34a52f`。

### 计划正文复核

- 公开 API 用户确认来源已在计划书记录：scope 仅 `kernel_gen/passes/**`，所属模块 `__all__` 公开，不全量顶层 re-export，私有 pattern 去下划线，spec 与实现注释写 MLIR before / after，getter 保留既有名且缺失才补。
- 候选 diff 符合方案 B：公开 pattern 维持 canonical module path，未全量重导出到 `kernel_gen.passes` 顶层，未删除既有稳定 re-export。
- 本轮未修改 pass name、registry option、pipeline 顺序或 expectation 合同资产。

### latest 集成态复跑验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`：exit 0，`4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py test/passes/test_registry.py test/passes/test_buffer_results_to_out_params.py test/passes/lowering/nn_lowering test/passes/test_outline_device_kernel.py test/passes/test_symbol_loop_hoist.py test/passes/test_hoist_dma_alias_ops.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py`：exit 0，`302 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`：exit 0，`126 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py`：exit 0，`39 passed, 1 warning`。
- `python3 -m compileall -q kernel_gen/passes test/passes spec/pass`：exit 0。
- 旧口径扫描 `rg -n 'class _[A-Za-z0-9_]*Pattern\(RewritePattern\)|def _get_.*patterns\(|pattern.*不公开|私有 pattern|不提供公开 pattern getter|只保留 .*_patterns\(' kernel_gen/passes spec/pass`：exit 1，输出为空，符合预期。
- `git diff --check && git diff --cached --check`：exit 0。
- 未跟踪新增测试补查：`git diff --no-index --check /dev/null test/passes/test_pattern_public_api_docs.py` 无 whitespace 输出；no-index 因新增文件存在返回 `1`，按无 whitespace 问题处理。
- `ast.parse(test/passes/test_pattern_public_api_docs.py)`：`ast_parse=ok`。
- `RewritePattern` AST 复核：`RewritePattern count=52 private_count=0`。
- 公开 pattern API 机械反查：复用 `test_pattern_public_api_docs.py` 清单与真实模块 / spec / class 方法反查，`missing_count=0`。
- ctx 能力探测扫描 `rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr\(ctx|emit_barrier' kernel_gen/passes test/passes/test_pattern_public_api_docs.py`：exit 1，输出为空。

### 只读 expectation 口径

- 导入来源核对：
  - `expectation.pass.*.__main__` 均来自 `/home/lfr/kernelcode_generate/expectation/...` 主仓只读资产。
  - `kernel_gen.passes.hoist_dma_alias_ops` 与 `kernel_gen.passes.tile.analysis` 在集成态来自 `/tmp/ppapi-latest-validation/worktree/kernel_gen/...`。
  - clean latest baseline 中同两个 `kernel_gen` 模块来自 `/tmp/ppapi-latest-baseline/kernel_gen/...`。
- 集成态通过项：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_loop_hoist`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.decompass`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=.:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering`：exit 0。
- 集成态隔离项：
  - `expectation.pass.hoist_dma_alias_ops`：exit 1；失败于 `pass-hoist_dma_alias_ops-slice`，`symbol.mul` check 未命中，动态 conv2d weight slice 仍为高维 slice。
  - `expectation.pass.tile`：exit 1；失败于 `pass.tile.analysis` 下 matmul reduce / reduce exprs 的 `CHECK-NEXT` 文本不匹配。
- clean latest baseline 同源复现：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=/tmp/ppapi-latest-baseline:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`：exit 1，同源失败于 `pass-hoist_dma_alias_ops-slice`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1 PYTHONPATH=/tmp/ppapi-latest-baseline:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`：exit 1，同源失败于 `pass.tile.analysis` matmul reduce / reduce exprs。
- 结论：`expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 仍是 latest-main 既有失败隔离，不作为通过项；本轮未修改 `expectation/`。

### 敏感目录与禁止面

- latest 集成态：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
  - `git status --short --untracked-files=all -- kernel/dump`：空。
- 任务 worktree：
  - `git status --short --untracked-files=all -- kernel/dump`：空；`kernel/dump` 中存在前序 expectation 运行留下的 ignored dump，不属于候选 diff。
  - `expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`、`ARCHITECTURE` 未进入候选 diff。
- 临时集成 worktree 与 baseline worktree 中 expectation 生成的 ignored dump 已清理；临时 worktree 后续可移除。

### Diff 反推终验

- latest 主线推进后存在两个交集文件，但候选 patch 在 `origin/main=bb874adfad94ea95697e08acc2bc12be5d34a52f` 上 clean apply，集成态 pytest / 静态 / expectation 口径均完成复核。
- `test/passes/test_pattern_public_api_docs.py` 仍能机械锁定公开 import、`__all__`、getter 顺序 / fresh instance、旧私有名负例、spec MLIR/reject token、spec API 列表、实现文件级 API 列表与实现 docstring IR 合同。
- 52 个 `RewritePattern` 子类均为公开 class，未发现 `_...Pattern` / `_get_...patterns` 旧口径。
- 未发现跨文件非公开 helper 公开化、ctx 能力探测、pass 行为改写、registry / pipeline / expectation 合同变更。

### 自检

- 已读取计划书、任务记录、review 复审、第一轮架构终验与 latest 主线状态，不只依据管理员摘要。
- 已基于 latest 同步现场复核路径交集，并在临时 latest 集成态而不是旧基线上复跑关键门禁。
- 已核对公开 API 变更均在用户确认范围内，无新增待用户确认项。
- 已核对 expectation 失败项未作为通过依据，且在 clean latest baseline 同源复现。
- 当前无可执行的本任务返工项。

### 结论

- 结论：`通过`
- 最小阻断项：无。
- 需用户确认项：无。
- 流转建议：第二轮计划级架构复核 / 终验通过，可进入 `merge`；本轮不直接执行 merge。

---

## 2026-05-24 02:44 +0800 李白 merge 记录

时间：2026-05-24 02:44 +0800

经办人：李白

任务：`T-20260524-c906a59e / pass-pattern-public-api-refactor`

任务目标：按合并规范合入已通过 review 复审与双架构终验的 pass pattern 公开 API 重构候选，确保代码 / spec / test 与任务记录同批提交并推送 `origin/main`。

合入来源：

- 来源 worktree：`/home/lfr/kernelcode_generate/wt-20260524-pass-pattern-public-api-refactor`。
- 来源分支：`task/pass-pattern-public-api-refactor`。
- 合并前同步：任务 worktree 原 `HEAD=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`origin/main=bb874adfad94ea95697e08acc2bc12be5d34a52f`，`merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`ahead/behind=0/1`。
- 同步动作：先用 `git stash push -u -m T-20260524-c906a59e-pre-latest-sync` 保存候选 diff 与未跟踪任务记录 / 新增测试，再 `git merge --ff-only origin/main` 快进到 latest main，最后 `git stash pop` 恢复候选。
- 冲突处理：`kernel_gen/passes/tile/analysis.py` 与 `spec/pass/tile/analysis.md` 自动合并，无冲突标记；`rg -n '<<<<<<<|=======|>>>>>>>' kernel_gen/passes spec/pass test/passes agents/codex-multi-agents/log/task_records/2026/23/20260523-pass-pattern-public-api-refactor.md` 无命中。
- 同步后基线：`HEAD=origin/main=merge-base=bb874adfad94ea95697e08acc2bc12be5d34a52f`，`ahead/behind=0/0`。

实际合入文件：

- 实现：`kernel_gen/passes/__init__.py`、`kernel_gen/passes/buffer_results_to_out_params.py`、`kernel_gen/passes/decompass.py`、`kernel_gen/passes/hoist_dma_alias_ops.py`、`kernel_gen/passes/outline_device_kernel.py`、`kernel_gen/passes/symbol_buffer_hoist.py`、`kernel_gen/passes/symbol_loop_hoist.py`、`kernel_gen/passes/tile/analysis.py`、`kernel_gen/passes/tile/elewise.py`、`kernel_gen/passes/tile/reduce.py`、`kernel_gen/passes/lowering/nn_lowering/__init__.py`、`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`。
- spec：`spec/pass/buffer_results_to_out_params.md`、`spec/pass/decompass.md`、`spec/pass/hoist_dma_alias_ops.md`、`spec/pass/outline_device_kernel.md`、`spec/pass/registry.md`、`spec/pass/symbol_buffer_hoist.md`、`spec/pass/symbol_loop_hoist.md`、`spec/pass/tile/analysis.md`、`spec/pass/tile/elewise.md`、`spec/pass/tile/reduce.md`、`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`、`spec/pass/lowering/nn_lowering/element_binary_lowering.md`、`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`、`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`、`spec/pass/lowering/nn_lowering/select_cast_lowering.md`、`spec/pass/lowering/nn_lowering/spec.md`。
- test：`test/passes/test_outline_device_kernel.py`、`test/passes/test_pattern_public_api_docs.py`。
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/23/20260523-pass-pattern-public-api-refactor.md`。

验证：

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pattern_public_api_docs.py`：exit 0，`4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py test/passes/test_registry.py test/passes/test_buffer_results_to_out_params.py test/passes/lowering/nn_lowering test/passes/test_outline_device_kernel.py test/passes/test_symbol_loop_hoist.py test/passes/test_hoist_dma_alias_ops.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py`：exit 0，`302 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering`：exit 0，`126 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py`：exit 0，`39 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes test/passes spec/pass`：exit 0。
- 旧口径扫描 `rg -n 'class _[A-Za-z0-9_]*Pattern\(RewritePattern\)|def _get_.*patterns\(|pattern.*不公开|私有 pattern|不提供公开 pattern getter|只保留 .*_patterns\(' kernel_gen/passes spec/pass`：无命中。
- AST pattern 扫描：`RewritePattern count=52 private_count=0`。
- API 机械反查：复用 `test/passes/test_pattern_public_api_docs.py` 的公开 pattern 清单、AST 签名提取和 spec / 实现 API 列表反查，exit 0，`missing_count=0`。
- `git diff --check && git diff --cached --check`：exit 0。
- 只读 expectation 通过项：
  - `expectation.pass.outline_device_kernel`：exit 0。
  - `expectation.pass.symbol_buffer_hoist`：exit 0。
  - `expectation.pass.symbol_loop_hoist`：exit 0。
  - `expectation.pass.decompass`：exit 0。
  - `expectation.pass.buffer_results_to_out_params`：exit 0。
  - `expectation.pass.lowing.nn_lowering`：exit 0。
- 只读 expectation 隔离项，不作为通过项：
  - 候选 `expectation.pass.hoist_dma_alias_ops`：exit 1；失败于 `pass-hoist_dma_alias_ops-slice`，`symbol.mul` check 未命中，动态 conv2d weight slice 仍为高维 slice，`low_rank_found=False, high_rank_found=True`。
  - latest main `expectation.pass.hoist_dma_alias_ops`：exit 1；同源失败于 `pass-hoist_dma_alias_ops-slice`。
  - 候选 `expectation.pass.tile`：exit 1；失败于 `pass.tile.analysis` 下 matmul reduce / reduce exprs 的 `CHECK-NEXT` 文本不匹配。
  - latest main `expectation.pass.tile`：exit 1；同源失败于 `pass.tile.analysis` matmul reduce / reduce exprs。

敏感目录与禁止面核对：

- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE plan`：空。
- 本轮未修改、未新建、未移动、未删除 `expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`、`ARCHITECTURE` 或 `plan`。

剩余风险：

- `expectation.pass.hoist_dma_alias_ops` 与 `expectation.pass.tile` 仍为 latest-main 既有失败隔离，已按双架构终验口径复核，不写为本轮通过依据，也不扩展为本轮修复项。
- expectation 运行留下的 `kernel/dump` 为 ignored 输出，不属于候选 diff。
- 当前未清理任务 worktree / 分支；原因是本轮仅授权 merge，且管理员此前要求 worktree / 分支清理范围确认后再处理。merge 完成回报中继续明确该状态。

结论：

- 候选 diff、任务记录、review 复审与双架构终验记录闭环；merge gate 已复跑通过或按 latest-main 既有失败隔离。
- 可将上述代码 / spec / test 与本任务记录同批提交并推送 `origin/main`，随后执行 `-done`。
