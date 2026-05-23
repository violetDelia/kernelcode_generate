# T-20260523-fef10685 symbol-buffer-hoist dominance lifecycle

时间：2026-05-23 09:34 CST
经办人：金铲铲大作战
任务：T-20260523-fef10685 / execute / symbol-buffer-hoist-dominance-lifecycle
任务目标：按 `ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md` 扩展 `symbol-buffer-hoist` 的 `dma.alloc/free` dominance/lifecycle proof，实现 alias / MemoryEffect / full-write-on-all-paths / free liveness 分析，使 matmul scratch buffer 与 acc buffer 在证明安全时可逐层外提；同步 spec、实现、pytest、kernel dump 验收，跑通主仓只读 `expectation.pass.symbol_buffer_hoist`，并保持 `expectation/.skills/agents/standard` 候选 diff 为空。

执行前阅读记录：
- 已重新读取个人提示词：`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`，确认当前职责为计划级 `execute`，不得审查/合并/修改 `expectation/`。
- 已重新读取根 `AGENTS.md`，确认公开 API、跨文件非公开 API、ctx 能力探测、嵌套函数、expectation 和敏感目录规则。
- 已读取 `agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读取主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md`；任务 worktree 内无本计划副本，按管理员口径只读引用主仓计划。
- 任务记录文件在本轮开始时不存在，已在 worktree 内新建。

同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle`
- 分支：`task/symbol-buffer-hoist-dominance-lifecycle`
- `HEAD=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`
- `origin/main=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`
- `merge-base=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`
- 执行前候选 diff 仅在任务 worktree 内推进；未回主仓做任务改动。

计划内小任务卡核对：
- S1 spec：已把 nested `symbol.for` data use 从“一律最近层 no-op”收口为 dominance/lifecycle 条件，并补 fixed-point、acc fill dominance、zero-trip、partial alias write、unknown call/effect 反例测试索引。
- S2 实现：已在 `kernel_gen/passes/symbol_buffer_hoist.py` 当前文件内补 alias/event/full-write/free-liveness helper；未新增公开 API，未导出 helper。
- S3 pattern：已移除 nested `SymbolForOp` data use 直接 hard reject，改由 plan/proof 驱动；pattern 仍每次只移动一层，由 fixed-point 多轮收敛。
- S4 pytest/kernel dump：已补静态/动态 fixed-point、acc fill 支配 nested read、branch write 缺 merge path、zero-trip nested write、partial subview write、unknown call/effect no-op 等公开 pytest；已跑 matmul demo dump gate。
- S5 expectation：只读运行主仓 `expectation.pass.symbol_buffer_hoist`，未复制/新建/修改 expectation。
- S6 记录：本记录写清 diff、pytest、合同验收、导入边界、敏感目录和静态扫描。

改动：
- `kernel_gen/passes/symbol_buffer_hoist.py`
  - 文件级说明更新 nested lifecycle proof 行为，API 列表保持 `DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()`、`SymbolBufferHoistPass` 不变。
  - 新增当前文件内 `_MemoryEvent` 与 alias/data event/full-write/free liveness helper，基于公开 `MemoryEffect` 和公开 dialect type 判定 READ/WRITE、full reset、partial write 与 escape。
  - `_build_hoist_use_plan` 改为收集 direct body 与 descendant region 事件，允许 nested read 被同 block 或 ancestor block 的完整 write/reset 支配后逐层外提；保留 unknown effect、first read before write、多 free、nested/free-before-use、partial alias write 等 no-op。
  - 保留 alias op 单层外提与 fixed-point 行为，不新增 pass option、registry name、公开 getter 或错误类型。
- `test/passes/test_symbol_buffer_hoist.py`
  - 新增公开 pytest：静态/动态 nested alloc/free fixed-point，acc fill dominance，branch write 不支配 merge read，nested write 可能不执行，partial subview write 后 root read，unknown call/effect escape。
  - 测试只通过公开 `SymbolBufferHoistPass` / registry / public dialect op 构造行为验证，不跨文件导入实现下划线 helper。
  - 将 acc 用例名称对齐计划映射：`test_symbol_buffer_hoist_acc_buffer_hoists_when_fill_dominates_reads`。
- `spec/pass/symbol_buffer_hoist.md`
  - 同步 nested lifecycle proof、fixed-point 正例、acc fill dominance 正例、zero-trip/partial write/unknown call 反例。
  - 补 TC-PASS-SYMBOL-BUFFER-HOIST-020~025，测试名与当前公开 pytest 对齐。
- `kernel/runner.py`
  - 将 `build_npu_demo_lowering_pipeline` 导入从旧 `kernel_gen.passes.pipeline` 改为当前公开 canonical `kernel_gen.pipeline`。
  - 归因：计划要求的 matmul demo dump gate 在当前主线下经 `kernel/runner.py` 触发，旧路径已不存在；该改动只使用现行公开 pipeline 入口，不新增公开 API。

当前 diff：
- `git diff --stat`：`kernel/runner.py` 2 行、`kernel_gen/passes/symbol_buffer_hoist.py` 453 行级变更、`spec/pass/symbol_buffer_hoist.md` 12 行级变更、`test/passes/test_symbol_buffer_hoist.py` 369 行级变更；合计 4 文件，767 insertions / 69 deletions。
- `git diff --name-only`：
  - `kernel/runner.py`
  - `kernel_gen/passes/symbol_buffer_hoist.py`
  - `spec/pass/symbol_buffer_hoist.md`
  - `test/passes/test_symbol_buffer_hoist.py`

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -ra`
  - 结果：exit=0，`37 passed, 1 warning`
  - 覆盖点：pass 公开入口、fixed-point nested alloc/free、acc buffer fill dominance、alias/effect/no-op 边界、registry 无关测试不混入。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -k 'fixed_point_nested_loop_static or fixed_point_nested_loop_dynamic or fill_dominates_reads or branch_write_misses or nested_loop_write_may_not_run or partial_write_precedes_full_read or unknown_call_uses_buffer' -ra`
  - 结果：exit=0，`7 passed, 30 deselected, 1 warning`
  - 覆盖点：本轮新增 dominance/lifecycle 正反例逐项命中。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`
  - 结果：exit=0，`38 passed, 55 deselected, 1 warning`
  - 覆盖点：公开 pass class、pattern getter 与 registry pass name 未回退。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_kernel.py -ra`
  - 结果：exit=0，`96 passed, 1 warning`
  - 覆盖点：本轮只读依赖的 DMA / kernel `MemoryEffect` 与 dialect 行为未被破坏。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -ra`
  - 结果：exit=0，`4 passed, 1 warning`
  - 覆盖点：matmul symbolic genkernel 与 runner 公开 pipeline 导入边界闭合。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`
  - 结果：exit=0。

合同验收：
- 主仓 expectation hash：
  - `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/__main__.py`：`5d164540771f95606ded2d48128ec373cacc5cf841f47a4d625751d5719d2960`
  - `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`：`641e242747d761e4285bba74710e8997a8116901c9a2d3adb92a23f8de838064`
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：exit=0。
  - 覆盖点：主仓只读 `alloc_free.py` 新合同 static/dynamic fixed-point、zero-trip、partial-write、kernel lifecycle 等 family case 全部通过。
- 导入边界证明：
  - `expectation.pass.symbol_buffer_hoist`：`path=['/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist']`
  - `expectation.pass.symbol_buffer_hoist.alloc_free`：`file=/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`
  - `kernel_gen.passes.symbol_buffer_hoist`：`file=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle/kernel_gen/passes/symbol_buffer_hoist.py`
  - `kernel_gen.pipeline`：`file=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle/kernel_gen/pipeline/__init__.py`

kernel dump / demo 验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - 结果：exit=0
  - 输出摘要：`absent_bias max_abs_diff=3.4332275390625e-05`，`present_bias max_abs_diff=3.4332275390625e-05`
  - 说明：当前仓库没有独立 `kernel/matmul/inputs_static_tile_static_present_bias.py` 文件；现有 `inputs_static_tile_static.py` 在同一脚本内随机顺序覆盖 absent/present bias，并生成 `kernel/dump/matmul/inputs_static_tile_static_present_bias/...` dump。未新建 wrapper，避免扩大公开 demo 入口。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`
  - 结果：exit=0
  - 输出摘要：`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0
  - 输出摘要：`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`
- 结构核对：
  - `kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/12-symbol-buffer-hoist.mlir` 与 `20-symbol-buffer-hoist.mlir` 中可见 `%12/%13/%14/%15/%16` 类 TSM scratch/acc alloc 位于 tile loop 外层，matching `dma.free` 位于外层之后；`dma.fill`、`kernel.matmul`、`kernel.binary_elewise` 保持在计算 loop 内。
  - 后续 `20-symbol-buffer-hoist.mlir` 中 lower-dma-memory-hierarchy 生成的 TLM alloc/free 属于后续 pass 结果，不作为本轮 symbol-buffer-hoist 退回证据。

静态边界扫描：
- `rg -n 'hasattr\(|getattr\(|callable\(getattr' kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`
  - 结果：无输出。
- `rg -n 'def .*\(.*object|object\)' kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`
  - 结果：无输出。
- `rg -n 'from .* import _|import .*\._' kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`
  - 结果：无输出。
- `rg -n '^\s{4,}def ' kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`
  - 结果：仅命中 class methods：`match_and_rewrite` x4 与 `SymbolBufferHoistPass.apply`，不是函数体内嵌套 helper。
- `rg -n 'SymbolBufferHoistError|symbol-buffer-hoist.*option|build_registered_pass\("symbol-buffer-hoist",.*[^)]' kernel_gen spec test`
  - 结果：仅命中 `spec/pass/symbol_buffer_hoist.md` 中“当前专题不新增 SymbolBufferHoistError”的说明；未新增 option 或错误类型。

敏感目录门禁：
- `git diff --name-only -- expectation .skills agents/standard`
  - 结果：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`
  - 结果：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`
  - 结果：无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：无输出。

格式门禁：
- `git diff --check`
  - 结果：exit=0。

自检：
- 接口：未新增公开 API；`SymbolBufferHoistPass(fold=True)`、pattern class、getter、registry name 均保持不变。`kernel/runner.py` 只改为现行公开 `kernel_gen.pipeline` 导入。
- 边界：覆盖 static/dynamic fixed-point 正例、acc fill dominance 正例、branch write merge read 反例、zero-trip nested write 反例、partial alias write 反例、unknown call/effect 反例、free-before-use/multiple-free/nested-free 既有反例。
- 异常：unknown effect / unknown call 保持 no-op；verifier 失败仍统一包装为 `KernelCodeError(module="pass")` 与 `SymbolBufferHoistVerifierError` 前缀。
- 兼容性：legacy `dma.slice` target、`dma.deslice` source、metadata query、alias op one-layer hoist 与 registry 行为均有既有 pytest 保持。
- 实现遗漏：计划中要求的 alias / MemoryEffect / full-write-on-all-paths / free liveness proof 已落到当前文件内 helper；未处理完整 CFG LICM，按计划保持保守。
- 冗余/复用/函数粒度：复杂判定拆为当前文件内 helper，未跨文件调用非公开 helper；helper 有功能说明和使用示例。
- 输入/输出校验：shape dominance、alias operand dominance、free 唯一性与位置、partial write/full write 覆盖关系均有测试。
- 资源/并发/性能：pass 仍按 greedy fixed-point walker 运行，每次只移动一层；未引入全局状态、缓存或线程资源。
- 测试有效性：新增测试断言 alloc/free 实际位置、use 仍绑定外提后 buffer、no-op 反例保留 alloc/free 原位，错误实现会导致断言失败。

结论：
- execute 已完成。代码/spec/test/记录在同一 worktree 内闭合；主仓只读 `expectation.pass.symbol_buffer_hoist` exit=0；相关 pytest、matmul demo、py_compile、git diff check、导入边界和敏感目录门禁均通过。
- 无需修改 `expectation/.skills/agents/standard`；候选 diff 中这些目录为空。
- 下一步：按流程续接 review，重点审查 dominance/lifecycle proof 的安全性、公开 API 边界、kernel/runner.py canonical import 的必要性与 dump gate 记录。

时间：2026-05-23 09:46 CST
经办人：提莫炖蘑菇
任务：T-20260523-fef10685 / review / symbol-buffer-hoist-dominance-lifecycle
任务目标：审查 symbol-buffer-hoist dominance/lifecycle proof 的 spec、实现、公开 pytest、kernel dump gate、主仓只读 expectation.pass.symbol_buffer_hoist、导入边界、敏感目录门禁与任务记录。

审查前置同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle`
- 已执行：`git fetch origin`
- `HEAD=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`
- `origin/main=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`
- `merge-base=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`
- 当前状态：待审 worktree 与最新 `origin/main` 同基线；候选 diff 为 `kernel/runner.py`、`kernel_gen/passes/symbol_buffer_hoist.py`、`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py`，本任务记录为未跟踪记录文件；未执行 merge/reset/checkout，未覆盖任务 diff。

执行记录核对：
- 已读计划：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md`。
- 已读任务记录：本文件 2026-05-23 09:34 execute 段。
- execute 记录包含执行前阅读、计划内小任务卡核对、最小功能闭环、Diff 反推自测、主仓只读 expectation 导入边界、kernel dump gate、静态扫描、敏感目录门禁和自检。
- expectation 口径核对：本轮 review 只读运行主仓 `expectation/pass/symbol_buffer_hoist/**`；未复制、未新建、未修改 expectation。

Diff 反推审查：
- 被审 diff：
  - `kernel/runner.py`
  - `kernel_gen/passes/symbol_buffer_hoist.py`
  - `spec/pass/symbol_buffer_hoist.md`
  - `test/passes/test_symbol_buffer_hoist.py`
- 重点核对：
  - `symbol-buffer-hoist` 公开 API 未新增；`SymbolBufferHoistPass` / `DmaAllocInSymbolForHoistPattern` / `get_symbol_buffer_hoist_patterns()` 仍为公开入口。
  - `kernel/runner.py` 改为使用 canonical `kernel_gen.pipeline.build_npu_demo_lowering_pipeline`，与当前 `spec/pass/registry.md` 中旧 `kernel_gen.passes.pipeline` 稳定失败边界一致。
  - pytest 未跨文件直连 `kernel_gen/passes/symbol_buffer_hoist.py` 下划线 helper；新增 helper 均留在当前实现文件内。
  - 未发现 ctx 能力探测、`object` 签名、跨文件私有导入或非装饰器嵌套函数新增。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -ra`
  - 结果：exit=0，`37 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`
  - 结果：exit=0，`38 passed, 55 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py && git diff --check`
  - 结果：exit=0
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：exit=0
  - 说明：合同验收单列，不计入 Diff 反推测试；导入边界为主仓 expectation + 任务 worktree `kernel_gen`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_kernel.py -ra`
  - 结果：exit=0，`96 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -ra`
  - 结果：exit=0，`4 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -k 'fixed_point_nested_loop_static or fixed_point_nested_loop_dynamic or fill_dominates_reads or branch_write_misses or nested_loop_write_may_not_run or partial_write_precedes_full_read or unknown_call_uses_buffer' -ra`
  - 结果：exit=0，`7 passed, 30 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - 结果：exit=0，`absent_bias max_abs_diff=3.4332275390625e-05`，`present_bias max_abs_diff=3.4332275390625e-05`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`
  - 结果：exit=0，`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0，`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`：无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。
- 静态扫描：
  - `rg -n 'hasattr\(|getattr\(|callable\(getattr|\bobject\b|from .* import _|import .*\._' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py`：无输出。
  - `rg -n '^\s{4,}def ' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py`：仅命中 pattern/pass class method，不是函数体内嵌套 helper。
  - `rg -n 'SymbolBufferHoistError|symbol-buffer-hoist.*option|build_registered_pass\("symbol-buffer-hoist",.*[^)]' kernel_gen spec test`：仅命中 `spec/pass/symbol_buffer_hoist.md` 中“不新增 SymbolBufferHoistError”的说明。

发现：
- 阻断：`kernel_gen/passes/symbol_buffer_hoist.py:771` 把 `dma.deslice` 的 `source` operand 从公开 DMA `MemoryEffect` 的 `READ` 改写成内部 `_MemoryEvent(effects={WRITE}, full_write=False)`，绕开了本轮 nested lifecycle proof 的“每个 READ 前必须由 full write/reset 支配”要求。公开 `spec/dialect/dma.md` 明确 `dma.copy/load/store/slice/deslice/transpose/cast` 对 target 为 `WRITE`、source 为 `READ`；本计划核心事件表也把 `dma.deslice(target, source, ...)` 归为 target `WRITE`、source `READ`。当前特殊处理导致 nested `symbol.for` 中只有 `dma.deslice(source=alloc)`、没有任何 reset/write 的 output scratch 也会被 fixed-point 外提到外层。审查用最小复现脚本已验证：构造 `alloc -> nested symbol.for { dma.deslice(target, alloc) } -> free` 后运行 `SymbolBufferHoistPass()`，结果 `top_has_alloc_free=True True`、`outer_has_alloc_free=False False`，即 alloc/free 被提到外层。影响：这会把真实 READ 伪装成 WRITE，扩大 legacy output scratch 合同，可能把未初始化或上一迭代残留 scratch 变成跨迭代共享状态；同时实现注释中“`dma.slice target` 与 `dma.deslice source` 仍作为旧兼容边界存在，但也通过公开 effect 参与证明”与代码行为不一致。最小返工动作：二选一收口，推荐保持公开 effect-first 口径：`dma.deslice source` 按 READ 事件进入 lifecycle proof，只有在此前存在支配它的 full reset/write 时才允许 nested 外提；若必须保留 legacy direct output scratch 例外，则必须在 spec 中把它写成精确例外，仅限同 owner body 直接 `dma.deslice source + matching free`，不得作为 nested proof 的 WRITE 事件，并补正反 pytest（direct legacy 仍可外提；nested deslice source 无 reset/write 必须 no-op；nested deslice source 前有 `dma.fill` 或等价 full write 时才允许外提）。验收方式：新增/更新公开 pytest 覆盖上述三种形态，复跑 `pytest -q test/passes/test_symbol_buffer_hoist.py -ra`、本轮 targeted `-k`、`python3 -m expectation.pass.symbol_buffer_hoist`，并保持敏感目录门禁为空。

自检：
- 已逐项读取实际 diff，而不是只看执行摘要。
- 已按当前 diff 复跑公开 pytest、py_compile、git diff check、kernel demo gate、主仓只读 expectation 和敏感目录门禁。
- 已核对公开 API、expectation 权限、跨文件非公开 API、测试入口和静态扫描。
- 当前存在可执行的行为边界返工项，按角色提示词不得写通过。

结论：最小需改项
- 本轮 review 不通过，需回 `execute` 收口 `dma.deslice source` READ / legacy output scratch 例外边界与对应公开 pytest 后再复审。

时间：2026-05-23 09:55 +0800
经办人：咯咯咯
任务：T-20260523-fef10685 / execute 返工 / symbol-buffer-hoist-dominance-lifecycle
任务目标：修复 review 指出的 `dma.deslice source` READ / legacy output scratch 例外边界，补齐 spec 与公开 pytest，确认 nested deslice source 无 reset/write 不再绕过 lifecycle proof，复跑 Diff 反推 pytest、主仓只读 expectation、kernel demo gate、git diff check 和敏感目录空 diff。

执行前阅读记录：
- 已重新读取个人提示词、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/测试文件约定.md`、`agents/standard/expectation任务规则.md`。
- 已读取主仓 `TODO.md` 当前任务行，确认本任务为 `咯咯咯 / execute / 进行中`。
- 已读取主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md`；任务 worktree 内无计划书副本，继续只读引用主仓计划。
- 已读取本记录 09:46 review 结论，确认阻断项为 `dma.deslice source` 被当作 WRITE 绕过 nested lifecycle READ proof。
- 同步现场：执行目录 `/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle`；已执行 `git fetch origin --prune`；`HEAD=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`，`origin/main=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`，`merge-base=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`，ahead/behind=`0/0`；无需合并，无冲突。

返工收口：
- `kernel_gen/passes/symbol_buffer_hoist.py`
  - 新增当前文件内私有 `_is_direct_legacy_output_scratch_use(...)`。
  - `_memory_event_from_use(...)` 新增 `loop_block` 入参，只在 `dma.deslice source` 直接位于 owner `symbol.for` body 时保留 legacy output scratch 例外。
  - descendant region 内的 `dma.deslice source` 不再被改写成 WRITE，而是按公开 DMA `MemoryEffect` 的 READ 进入 lifecycle proof；若此前没有 full reset/write，外提 no-op。
- `test/passes/test_symbol_buffer_hoist.py`
  - 新增 `_build_nested_deslice_source_module(with_reset: bool)`。
  - 新增 `test_symbol_buffer_hoist_keeps_nested_deslice_source_without_reset`，锁定 nested `dma.deslice(source=alloc)` 无 reset/write 时 alloc/free 保持 owner loop 内。
  - 新增 `test_symbol_buffer_hoist_hoists_nested_deslice_source_after_reset`，锁定 owner block `dma.fill` 支配 nested `dma.deslice source` READ 时 alloc/free 可外提。
  - 既有 `test_symbol_buffer_hoist_hoists_output_scratch_alloc_and_matching_free` 继续覆盖 direct legacy output scratch 可外提。
- `spec/pass/symbol_buffer_hoist.md`
  - 写清 legacy output scratch 例外只限同 owner body 直接 `dma.deslice source`。
  - 写清 nested region 内 `dma.deslice source` 必须按 READ 参与 lifecycle proof，无此前 full reset/write 时 no-op。
  - 测试矩阵新增 nested deslice source 无 reset/write 反例与 reset 支配正例。
- 未新增或改签公开 API；未修改、复制、移动、新建或删除 `expectation/`、`.skills/`、`agents/standard/**`。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_nested_deslice_source_without_reset test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_nested_deslice_source_after_reset -ra`：exit=0，`2 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -ra`：exit=0，`39 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -k 'fixed_point_nested_loop_static or fixed_point_nested_loop_dynamic or fill_dominates_reads or nested_deslice_source or branch_write_misses or nested_loop_write_may_not_run or partial_write_precedes_full_read or unknown_call_uses_buffer' -ra`：exit=0，`9 passed, 30 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`：exit=0，`40 passed, 55 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_kernel.py -ra`：exit=0，`96 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -ra`：exit=0，`4 passed, 1 warning`。
- 主仓只读合同验收：
  - 命令：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：exit=0。
- 导入边界：
  - `expectation.pass.symbol_buffer_hoist` path=`/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist`
  - `expectation.pass.symbol_buffer_hoist.alloc_free` file=`/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`
  - `kernel_gen.passes.symbol_buffer_hoist` file=`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle/kernel_gen/passes/symbol_buffer_hoist.py`
  - `kernel_gen.pipeline` file=`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle/kernel_gen/pipeline/__init__.py`
- 主仓 expectation hash：
  - `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/__main__.py`：`5d164540771f95606ded2d48128ec373cacc5cf841f47a4d625751d5719d2960`
  - `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`：`641e242747d761e4285bba74710e8997a8116901c9a2d3adb92a23f8de838064`
- kernel demo gate：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，`absent_bias max_abs_diff=3.4332275390625e-05`，`present_bias max_abs_diff=3.4332275390625e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit=0，`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit=0，`absent_bias max_abs_diff=3.0517578125e-05`，`present_bias max_abs_diff=3.0517578125e-05`。
- `git diff --check`：exit=0。
- untracked 任务记录 diff check：exit=0，`untracked diff check ok`。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`：无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。
- 静态边界扫描：
  - `rg -n 'hasattr\(|getattr\(|callable\(getattr|\bobject\b|from .* import _|import .*\._' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py`：无输出。
  - `rg -n '^\s{4,}def ' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py`：仅命中 pattern/pass class method，不是函数体内嵌套 helper。

Diff 反推自测：
- `kernel_gen/passes/symbol_buffer_hoist.py`：
  - 反推测试：新增 deslice nodeid、全文件 `test_symbol_buffer_hoist.py`、targeted `-k`、registry gate、主仓只读 expectation、matmul demo gate。
  - 锁定行为：direct owner body `dma.deslice source` legacy 仍可外提；nested `dma.deslice source` 无 reset/write no-op；nested `dma.deslice source` 前有 owner-block full reset/write 时允许外提。
- `test/passes/test_symbol_buffer_hoist.py`：
  - 反推测试：新增 2 个 nodeid 与全文件 39 个用例。
  - 锁定行为：旧实现会错误外提无 reset/write 的 nested deslice source；新断言要求 alloc/free 留在 owner loop。
- `spec/pass/symbol_buffer_hoist.md`：
  - 反推核对：legacy direct output scratch 例外、nested READ proof 正反例与测试矩阵一致；API 列表未变化。
- `kernel/runner.py` 既有 diff：
  - 反推测试：`test/kernel/test_matmul_symbolic_memory_genkernel.py` 与 3 个 matmul demo gate。
- `expectation` 单列为合同验收资产，不计入 Diff 反推测试；本轮只读运行，候选 diff 为空。

自检：
- 接口：未新增、删除、重命名或改签公开 API；新增 helper 只在当前文件内使用。
- 边界：已覆盖 direct legacy output scratch、nested deslice source 无 reset/write、nested deslice source 有 reset、acc fill、zero-trip、partial write、unknown call、branch write 与 fixed-point 正例。
- 异常：未改变公开错误类型或稳定错误文本；verifier 包装仍保持 `SymbolBufferHoistVerifierError:`。
- 兼容性：direct owner body `dma.deslice source + matching free` 既有输出 scratch合同继续通过；主仓只读 expectation 全部通过。
- 实现遗漏：review 指出的 READ / legacy 例外边界已收口；不再把 nested deslice source 伪装成 WRITE。
- 冗余与复用：新增 helper 只封装 legacy 判定，避免把 owner body 与 nested region 逻辑散落在事件转换处。
- 注释准确性：实现注释与 spec 均写清 nested deslice source 按 READ proof。
- 函数粒度：未新增嵌套函数；新增测试 helper 只服务当前测试文件。
- 输入/输出校验：仍以公开 MemoryEffect、full_write、dominance 和 free 顺序证明为准。
- 资源/并发/性能：无全局状态、缓存、文件 IO 或并发资源；pattern fixed-point 行为不变。
- 测试有效性：新增反例能在 review 复现的旧实现下失败，新增正例锁定 reset 支配时不回退。
- 敏感目录：`expectation/`、`.skills/`、`agents/standard/**` 候选 diff 为空。

结论：
- execute 返工已闭合，可流转 review。
- 下一步：执行 `-next -auto` 续接 review，并回报管理员。

时间：2026-05-23 10:01 CST
经办人：不要啊教练
任务：T-20260523-fef10685 / review 复审 / symbol-buffer-hoist-dominance-lifecycle
任务目标：复审 `dma.deslice source` READ 与 legacy direct output scratch 边界返工，核对 spec、公开 pytest、Diff 反推自测、主仓只读 expectation、kernel demo gate、git diff check 与敏感目录空 diff。

审查前置同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle`。
- 已执行：`git fetch origin --prune`。
- `HEAD=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `origin/main=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `merge-base=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 当前待审 worktree 与最新 `origin/main` 同基线；未执行 merge/reset/checkout，未覆盖任务 diff；候选 diff 为 `kernel/runner.py`、`kernel_gen/passes/symbol_buffer_hoist.py`、`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py` 与任务记录。
- 本 worktree 缺计划书副本，本轮继续只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md` 作为合同真源。

执行记录核对：
- 已读主仓计划、09:34 execute 记录、09:46 review 记录和 09:55 execute 返工记录。
- 09:46 review 阻断项为 `dma.deslice source` 被当作 WRITE 绕过 nested lifecycle READ proof。
- 09:55 execute 返工记录已写清返工动作、Diff 反推自测、主仓只读 expectation、kernel demo gate、静态扫描、敏感目录门禁和自检。

真实审查：
- 重复问题收口：`kernel_gen/passes/symbol_buffer_hoist.py:753` 至 `kernel_gen/passes/symbol_buffer_hoist.py:802` 已将 legacy output scratch 例外限制为同 owner `symbol.for` 直接 body 内的 `dma.deslice source`；descendant region 内 `dma.deslice source` 重新按公开 `MemoryEffect` READ 进入 proof。
- 重复问题收口：`test/passes/test_symbol_buffer_hoist.py:1208` 至 `test/passes/test_symbol_buffer_hoist.py:1252` 构造 nested deslice source 正反例，`test/passes/test_symbol_buffer_hoist.py:2048` 至 `test/passes/test_symbol_buffer_hoist.py:2087` 锁定无 reset/write no-op 与有 owner block reset 可外提；旧实现会在无 reset/write 反例上错误外提。
- 重复问题收口：`spec/pass/symbol_buffer_hoist.md:150` 至 `spec/pass/symbol_buffer_hoist.md:178` 已同步 direct legacy 例外、nested READ proof 和无 reset/write 反例；测试矩阵 `TC-PASS-SYMBOL-BUFFER-HOIST-022/023` 已补齐。
- 新增问题（阻断）：`kernel_gen/passes/symbol_buffer_hoist.py:22` 至 `kernel_gen/passes/symbol_buffer_hoist.py:27` 的文件级 `API 列表` 未列出 `SymbolBufferHoistPass.name: str`，但专题 spec 顶部 API 列表在 `spec/pass/symbol_buffer_hoist.md:12` 至 `spec/pass/symbol_buffer_hoist.md:17` 明确包含 `SymbolBufferHoistPass.name: str`，实现类也在 `kernel_gen/passes/symbol_buffer_hoist.py:1333` 暴露 `name = "symbol-buffer-hoist"`。根据根 `AGENTS.md` 与实现文件规范，execute 修改功能实现文件时必须同步维护文件级 API 列表，class 场景需列类公开 API；当前实现文件 API 列表与 spec/实现不一致，不能通过。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_nested_deslice_source_without_reset test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_nested_deslice_source_after_reset -ra`：exit=0，`2 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -ra`：exit=0，`39 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`：exit=0，`40 passed, 55 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_kernel.py -ra`：exit=0，`96 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -ra`：exit=0，`4 passed, 1 warning`。
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`：exit=0；合同验收单列，不计入 Diff 反推测试。
- 导入边界 proof：`expectation.pass.symbol_buffer_hoist` path=`/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist`；`expectation.pass.symbol_buffer_hoist.__main__` sha256=`5d164540771f95606ded2d48128ec373cacc5cf841f47a4d625751d5719d2960`；`expectation.pass.symbol_buffer_hoist.alloc_free` sha256=`641e242747d761e4285bba74710e8997a8116901c9a2d3adb92a23f8de838064`；`kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，包含 `absent_bias max_abs_diff=3.4332275390625e-05` 与 `present_bias max_abs_diff=3.4332275390625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit=0，包含 `absent_bias max_abs_diff=3.0517578125e-05` 与 `present_bias max_abs_diff=3.0517578125e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit=0，包含 `absent_bias max_abs_diff=3.0517578125e-05` 与 `present_bias max_abs_diff=3.0517578125e-05`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`：exit=0。
- `git diff --check`：exit=0；`git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --untracked-files=all -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：均无输出。
- 静态扫描：`rg -n 'hasattr\(|getattr\(|callable\(getattr|\bobject\b|from .* import _|import .*\._' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py` 无输出；`rg -n '^\s{4,}def '` 仅命中 class methods，不是函数体内嵌套 helper；`rg -n 'skip\(|xfail|collect_ignore|pytest_ignore_collect' test/passes/test_symbol_buffer_hoist.py` 无输出。

最小需改项：
1. 问题：`kernel_gen/passes/symbol_buffer_hoist.py` 文件级 `API 列表` 缺 `SymbolBufferHoistPass.name: str`。
   影响：实现文件 API 索引与 spec/实际公开类 API 不一致，违反实现文件规范；后续审查无法把公开 API 真源快速对齐。
   最小返工动作：在 `kernel_gen/passes/symbol_buffer_hoist.py` 文件级 `API 列表` 中补 `SymbolBufferHoistPass.name: str`，不改代码行为。
   验收方式：复跑 `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py`、`git diff --check`、敏感目录空 diff；必要时复跑 `pytest -q test/passes/test_symbol_buffer_hoist.py -k public_patterns_are_reachable -ra`。

自检：
- 已逐项读取实际 diff、计划、执行记录和前序 review 记录。
- 已复跑返工 nodeid、全量相关 pytest、主仓只读 expectation、matmul demo gate、py_compile、diff check、静态扫描和敏感目录门禁。
- 已确认前轮 `dma.deslice source` READ / legacy direct output scratch 行为阻断闭合。
- 当前仍存在一个可执行实现文件规范返工项；按角色提示词与审查规范不得写通过。

结论：最小需改项，不通过，回 execute。

时间：2026-05-23 10:05 CST
经办人：睡觉小分队
任务：T-20260523-fef10685 / execute 返工 / symbol-buffer-hoist-dominance-lifecycle
任务目标：修复 review 最小需改项，在 `kernel_gen/passes/symbol_buffer_hoist.py` 文件级 API 列表补齐 `SymbolBufferHoistPass.name: str`，与 `spec/pass/symbol_buffer_hoist.md` 和实现类公开属性保持一致；不改代码行为。

执行前阅读：
- 已读取最新个人提示词、根 `AGENTS.md` 与 `agents/standard` 规则，继续按 execute 职责执行。
- 已读取本任务记录中 10:01 复审结论，确认唯一阻断为实现文件文件级 API 列表缺少 `SymbolBufferHoistPass.name: str`。
- 已核对 `spec/pass/symbol_buffer_hoist.md` 顶部 API 列表已包含 `SymbolBufferHoistPass.name: str`，实现类公开属性为 `name = "symbol-buffer-hoist"`。

变更：
- `kernel_gen/passes/symbol_buffer_hoist.py`：仅在文件级 `API 列表` 中新增 `SymbolBufferHoistPass.name: str`。
- 未修改任何代码行为、测试逻辑或合同资产。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_public_patterns_are_reachable -ra`：exit=0，`1 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`：exit=0，`40 passed, 55 deselected, 1 warning`。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。

Diff 反推自测：
- 本轮只改 `kernel_gen/passes/symbol_buffer_hoist.py` 文件级 API 索引，不改实现行为。
- 反推测试为 `py_compile`、公开 pattern 入口 pytest、registry/公开 pass 构造相关 pytest 与 `git diff --check`。
- `expectation` 只作为合同资产目录做未授权 diff 检查，不计入 Diff 反推测试；本轮未修改、复制、新建、删除或同步 `expectation/`。

自检：
- 接口：未新增、删除、重命名或修改公开 API；仅补齐已存在公开属性在实现文件 API 列表中的索引。
- 边界：spec、实现类公开属性与文件级 API 列表已对齐。
- 行为：未修改 pass 行为、测试行为、pipeline 行为或错误语义。
- 非公开 API：本轮未新增跨文件调用、包装转发、别名导入或反射访问。
- 规范：未引入 ctx 能力探测、`object` 签名或非装饰器嵌套函数。
- 敏感目录：`expectation/`、`.skills/`、`agents/standard/**` 候选 diff 为空。

结论：
- execute 返工已闭合，可流转 review。

时间：2026-05-23 10:08 CST
经办人：不要啊教练
任务：T-20260523-fef10685 / review 复审 / symbol-buffer-hoist-dominance-lifecycle
任务目标：复审 `symbol-buffer-hoist` 文件级 API 列表补齐 `SymbolBufferHoistPass.name: str`、验证记录、Diff 反推自测与敏感目录空 diff。

审查前置同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle`。
- 已执行：`git fetch origin --prune`。
- `HEAD=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `origin/main=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `merge-base=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 当前待审 worktree 与最新 `origin/main` 同基线；未执行 merge/reset/checkout，未覆盖任务 diff。
- 本轮为最小返工复审；任务 worktree 仍缺计划书副本，继续只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md` 作为合同真源。

执行记录核对：
- 已读 10:05 execute 返工记录，确认本轮唯一改动为 `kernel_gen/passes/symbol_buffer_hoist.py` 文件级 `API 列表` 补 `SymbolBufferHoistPass.name: str`，不改代码行为、测试逻辑或合同资产。
- 已核对 execute 记录包含 Diff 反推自测、敏感目录门禁和自检。

真实审查：
- `kernel_gen/passes/symbol_buffer_hoist.py:22` 至 `kernel_gen/passes/symbol_buffer_hoist.py:28` 的文件级 `API 列表` 已包含 `SymbolBufferHoistPass.name: str`。
- `spec/pass/symbol_buffer_hoist.md:12` 至 `spec/pass/symbol_buffer_hoist.md:17` 的 spec API 列表也包含 `SymbolBufferHoistPass.name: str`。
- `kernel_gen/passes/symbol_buffer_hoist.py:1334` 实现类公开属性仍为 `name = "symbol-buffer-hoist"`；文件级 API 列表、spec 与实现已对齐。
- 本轮没有新增公开 API、没有改签、没有跨文件非公开 API 调用、没有测试直连新增非 API helper，也没有修改 `expectation/`、`.skills` 或 `agents/standard`。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_public_patterns_are_reachable -ra`：exit=0，`1 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`：exit=0，`40 passed, 55 deselected, 1 warning`。
- `git diff --check`：exit=0；`git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。

自检：
- 已逐项核对实际 diff、spec API 列表、实现类属性和 execute 返工记录。
- 已按最小 API 索引改动反推复跑 py_compile、公开入口 pytest、registry/公开 pass 构造相关 pytest、diff check 与敏感目录门禁。
- 本轮未复跑主仓只读 `expectation.pass.symbol_buffer_hoist` 与 kernel demo gate，原因是本轮只改文件级 API 索引、不改行为；上一轮复审已对行为返工复跑并通过，当前最小验证足以覆盖本轮 diff。
- 未发现剩余可执行返工项。

结论：通过。
- 前轮 `dma.deslice source` READ / legacy direct output scratch 行为返工已在 10:01 复审确认闭合。
- 本轮文件级 API 列表返工已闭合，验证通过。
- 计划级任务 review 通过；请管理员接架构复核 / 终验，不由 review 直接续接 merge。

---

时间：2026-05-23 10:12 CST
经办人：大闸蟹
任务：T-20260523-fef10685 / 架构复核终验 / symbol-buffer-hoist-dominance-lifecycle
任务目标：按计划级终验复核最新同步现场、主仓只读 expectation 真源、公开 API/spec/test 边界、Diff 反推测试、kernel demo gate 与敏感目录空 diff，并给出 merge 前架构结论。

同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle`。
- 计划书真源：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md`。
- `HEAD=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- 主仓 `origin/main=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- 候选 diff：`kernel/runner.py`、`kernel_gen/passes/symbol_buffer_hoist.py`、`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py` 与本任务记录。
- 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/**` tracked / cached / untracked / ignored 门禁为空。

合同真源与导入边界：
- `expectation.pass.symbol_buffer_hoist.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/__main__.py`，sha256=`5d164540771f95606ded2d48128ec373cacc5cf841f47a4d625751d5719d2960`。
- `expectation.pass.symbol_buffer_hoist.alloc_free` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`，sha256=`641e242747d761e4285bba74710e8997a8116901c9a2d3adb92a23f8de838064`。
- `kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle/kernel_gen/passes/symbol_buffer_hoist.py`。

终验验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -ra`：exit=0，`39 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_kernel.py -ra`：exit=0，`96 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -ra`：exit=0，`4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`：exit=0，`40 passed, 55 deselected, 1 warning`。
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`：exit=0。
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，含 `matmul/inputs_static_tile_static_absent_bias max_abs_diff=3.4332275390625e-05` 与 `matmul/inputs_static_tile_static_present_bias max_abs_diff=3.4332275390625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`：exit=0。
- `git diff --check`：exit=0；`git diff --cached --check`：exit=0。
- 静态边界扫描：`rg -n 'hasattr\(|getattr\(|callable\(getattr|\bobject\b|from .* import _|import .*\._' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py` 无输出。
- 嵌套函数 / skip 假绿扫描：`rg -n '^\s{4,}def |skip\(|xfail|collect_ignore|pytest_ignore_collect' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py` 仅命中 `symbol_buffer_hoist.py` 内 class methods，不是函数体内嵌套 helper；无 skip/xfail/collect 命中。

复核结论：
- `dma.deslice source` READ proof 与 legacy direct output scratch 边界已由 review 复审确认闭合，终验未发现回退。
- `SymbolBufferHoistPass.name: str` 已补入 `kernel_gen/passes/symbol_buffer_hoist.py` 文件级 API 列表，与 spec 和实现公开属性一致。
- spec / 实现 / pytest / kernel demo / 主仓只读 expectation 均按计划通过；未发现公开 API 未确认变更或跨文件非公开 API 使用。
- 最小阻断项：无。

结论：通过，可进入 merge 前下一架构/管理员流程；双架构通过前仍不得 merge。

---

时间：2026-05-23 10:13 CST
经办人：守护最好的爱莉希雅
任务：T-20260523-fef10685 / 第二架构终验 / symbol-buffer-hoist-dominance-lifecycle
任务目标：按计划级终验复核 latest 同步现场、主仓只读 expectation 真源、dominance/lifecycle 行为边界、公开 API/spec/test 同步、Diff 反推测试、kernel demo gate、静态边界扫描与敏感目录空 diff，并给出 merge 前第二架构结论。

同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle`。
- 计划书真源：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md`。
- `HEAD=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `origin/main=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `merge-base=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 候选 diff：`kernel/runner.py`、`kernel_gen/passes/symbol_buffer_hoist.py`、`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py` 与本任务记录；无 cached diff。

合同真源与导入边界：
- `expectation.pass.symbol_buffer_hoist.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/__main__.py`，sha256=`5d164540771f95606ded2d48128ec373cacc5cf841f47a4d625751d5719d2960`，与计划 manifest 一致。
- `expectation.pass.symbol_buffer_hoist.alloc_free` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`，sha256=`641e242747d761e4285bba74710e8997a8116901c9a2d3adb92a23f8de838064`，与计划 manifest 一致。
- `kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle/kernel_gen/passes/symbol_buffer_hoist.py`，确认 `PYTHONPATH` 导入边界为 worktree 代码优先、主仓 expectation 只读。

终验验证：
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`：exit=0。
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -ra`：exit=0，`39 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_kernel.py -ra`：exit=0，`96 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -ra`：exit=0，`4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`：exit=0，`1 passed, 55 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，输出包含 `matmul/inputs_static_tile_static_absent_bias max_abs_diff=3.4332275390625e-05` 与 `matmul/inputs_static_tile_static_present_bias max_abs_diff=3.4332275390625e-05`。当前仓库不存在独立 `kernel/matmul/inputs_static_tile_static_present_bias.py`，present-bias 由该脚本同次覆盖，未把缺失路径写成通过。
- `git diff --check`：exit=0；`git diff --cached --check`：exit=0。

敏感目录与静态边界：
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `rg -n 'hasattr\(|getattr\(|callable\(getattr' kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py`：无输出。
- `rg -n 'from .* import _|\._[A-Za-z]' test/passes/test_symbol_buffer_hoist.py`：无输出。
- `rg -n 'SymbolBufferHoistError|symbol-buffer-hoist.*option|build_registered_pass\("symbol-buffer-hoist",.*[^)]' kernel_gen spec test`：仅命中 `spec/pass/symbol_buffer_hoist.md` 中“本计划不新增 `SymbolBufferHoistError`”说明，非阻断。
- `rg -n '\bobject\b' kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`：无输出。
- `rg -n '^\s{4,}def ' kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`：仅命中类方法 `match_and_rewrite` / `apply`，未发现函数体内嵌套 helper。

结构复核：
- `kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/12-symbol-buffer-hoist.mlir` 与 `20-symbol-buffer-hoist.mlir` 中，`%12/%13/%14/%15/%16` 类 scratch alloc 位于外层 `symbol.for` 前，matching `dma.free` 位于外层 loop 后；`dma.fill`、`kernel.matmul`、`kernel.binary_elewise` 仍保留在计算 loop 内，符合计划的 lifecycle / reset 边界。

自检：
- 已按最新同步现场复核 review 返工点：`dma.deslice source` 按 READ 参与 proof，legacy direct output scratch 边界已收紧；`SymbolBufferHoistPass.name: str` 已补入文件级 API 列表并与 spec / 实现一致。
- 未发现公开 API 未确认变更、跨文件非公开 API 使用、测试直连非公开 helper、能力探测、`object` 签名或函数内嵌套 helper。
- 主仓只读 expectation 与任务 worktree 代码导入边界清楚；候选 diff 中 `expectation/`、`.skills`、`agents/standard/**` 为空。

结论：通过。
- 最小阻断项：无。
- 可进入 merge 前管理员流程；merge 前仍需确认任务记录与代码/spec/test 同批纳入，且候选 diff 继续保持 `expectation/`、`.skills`、`agents/standard/**` 为空。

时间：2026-05-23 10:11 CST
经办人：不要啊教练
任务：T-20260523-fef10685 / review 状态续接
任务目标：按用户要求在 review 通过后使用 `-next` 续接下一阶段，并回报管理员。
改动：本任务 review 已于 10:08 CST 记录为通过；因该任务为计划级任务，本次续接到 `架构复核 / 终验`，不由 review 直接续接 merge。
验证：已查看主仓 `TODO.md`，确认该任务仍显示 `review / 不要啊教练 / 进行中`，需要状态续接。
自检：未修改实现、spec、测试、expectation、`.skills` 或 `agents/standard`；仅追加任务记录并准备使用标准任务脚本续接状态。
结论：执行 `-next` 续接架构复核 / 终验，并回报管理员。

---

时间：2026-05-23 11:16 CST
经办人：李白
任务：T-20260523-fef10685 / symbol-buffer-hoist-dominance-lifecycle / merge
任务目标：按 merge 职责合入已通过 review 复审与双架构终验的 symbol-buffer-hoist dominance/lifecycle 候选 diff，核对 latest main、候选范围、任务记录同批、主仓只读 `expectation.pass.symbol_buffer_hoist`、kernel demo gate、`git diff --check` 和敏感目录空 diff。

合并前同步与来源：
- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle`。
- 计划真源：只读引用主仓 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_dominance_lifecycle_green_plan.md`。
- 已执行 `git fetch --prune origin`；同步结果：`HEAD=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`，`origin/main=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`，`merge-base=2a89eecfeecc2ebc65d7ea0359a626aaeec5233f`，ahead / behind 为 `0 / 0`。
- 同步未产生冲突，未执行会覆盖候选 diff 的 `reset` / `checkout` / 强制合并。

实际合入范围：
- `kernel/runner.py`。
- `kernel_gen/passes/symbol_buffer_hoist.py`。
- `spec/pass/symbol_buffer_hoist.md`。
- `test/passes/test_symbol_buffer_hoist.py`。
- 同批任务记录：`agents/codex-multi-agents/log/task_records/2026/22/20260523-symbol-buffer-hoist-dominance-lifecycle.md`。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py kernel/runner.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -ra`：exit=0，`39 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_dma.py test/dialect/test_kernel.py -ra`：exit=0，`96 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py -ra`：exit=0，`4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py -k 'symbol_buffer_hoist or symbol-buffer-hoist' -ra`：exit=0，`1 passed, 55 deselected, 1 warning`。
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`：exit=0；`expectation.pass.symbol_buffer_hoist` 使用主仓只读合同资产，`kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree。
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-symbol-buffer-hoist-dominance-lifecycle:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/alloc_free.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，输出包含 `matmul/inputs_static_tile_static_absent_bias max_abs_diff=3.4332275390625e-05` 与 `matmul/inputs_static_tile_static_present_bias max_abs_diff=3.4332275390625e-05`。
- `kernel/matmul/inputs_static_tile_static_present_bias.py`：当前仓库不存在该独立脚本；present-bias 由 `kernel/matmul/inputs_static_tile_static.py` 同次覆盖，未把缺失路径写成通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit=0，输出包含 `matmul/inputs_static_tile_dynamic/absent_bias max_abs_diff=3.0517578125e-05` 与 `matmul/inputs_static_tile_dynamic/present_bias max_abs_diff=3.0517578125e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit=0，输出包含 `matmul/inputs_dynamic_tile_dynamic/absent_bias max_abs_diff=3.0517578125e-05` 与 `matmul/inputs_dynamic_tile_dynamic/present_bias max_abs_diff=3.0517578125e-05`。
- `git diff --check`：exit=0；`git diff --cached --check`：exit=0。
- 静态扫描：`rg -n 'hasattr\(|getattr\(|callable\(getattr|\bobject\b|from .* import _|import .*\._' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py` 无输出。
- 嵌套函数 / skip 假绿扫描：`rg -n '^\s{4,}def |skip\(|xfail|collect_ignore|pytest_ignore_collect' kernel/runner.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py` 仅命中 `kernel_gen/passes/symbol_buffer_hoist.py` 内 class methods，未发现函数体内嵌套 helper，未命中 skip / xfail / collect ignore。

敏感目录核对：
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。
- 本轮不修改、新建、移动、删除 `expectation/`；只读运行主仓 `expectation.pass.symbol_buffer_hoist` 与 `alloc_free.py`。
- `.skills/`、`agents/standard/` 无普通 diff、无 staged diff、无 untracked / ignored 变更进入候选范围。
- `TODO.md` / `DONE.md` 未手工修改；状态只在 push 后通过任务脚本推进。

冲突处理：
- 无冲突；latest main 与任务 worktree 同基线，候选 diff 未被覆盖。

剩余风险：
- 当前计划明确由主仓 expectation 作为只读合同真源；merge 不合入任何 expectation 改动。
- full expectation 未作为本轮 gate；本轮只运行计划列明的 `expectation.pass.symbol_buffer_hoist` 与 `alloc_free.py`。

结论：merge gate 通过，任务记录已在合并提交前补齐；可将候选实现 / spec / test 与本任务记录同批提交、推送并执行 `-done`。
