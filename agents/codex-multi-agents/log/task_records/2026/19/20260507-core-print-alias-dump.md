时间：2026-05-07 22:40
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / core_print_alias_dump_green_plan execute
任务目标：新增 `kernel_gen.core.print.print_operation_with_aliases(operation: Operation | ModuleOp) -> str`，接入 `PassManager` / `dsl_run` / `ircheck` dump alias IR，跑通 core print 合同、全量 pytest、全量 expectation 与 kernel_gen coverage 95/80。

执行前阅读记录：
- 已阅读个人提示词、仓库根目录 `AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/任务记录约定.md`。
- 已阅读计划书 `ARCHITECTURE/plan/core_print_alias_dump_green_plan.md`，确认当前 worktree 不携带 `expectation/` 目录，主仓 expectation 只能只读引用。
- 已阅读前序记录与当前 worktree 现状，确认本轮仅在 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` 内提交实现/spec/test/记录改动，不改 `.skills`，不改未授权 `expectation/`。
- 已执行 `git fetch origin`，确认 `HEAD=origin/main=merge-base=673349f53bc3f29e804ff47c2784c57b12aa9d54`，当前 worktree 无需合并最新主线。

改动：
- 新增 `kernel_gen/core/print.py`，提供唯一公开入口 `print_operation_with_aliases(operation: Operation | ModuleOp) -> str`，实现 core alias printer。
- 新增 `spec/core/print.md`，补齐功能简介、API 列表、API 详细说明、测试章节与 alias 规则。
- 新增 `test/core/test_print.py`，覆盖公开导入、alias 输出、round-trip parse、非法输入与 raw attribute 打印不污染。
- 更新 `kernel_gen/passes/pass_manager.py`、`kernel_gen/tools/dsl_run.py`、`kernel_gen/tools/ircheck.py` 的 dump 入口，默认使用 alias IR。
- 同步修正若干 `spec/`、`kernel_gen/`、`test/` 中与 alias dump、NnMemoryType、SymbolExprAttr、tile / memory_pool / launch-kernel-cost-func 相关的实现与测试。
- 本轮未修改 `expectation/` 目录中的任何文件；仅在 `/tmp` 创建只读 expectation 快照作为运行环境，worktree 内无 expectation diff。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_print.py test/passes/test_pass_manager.py test/tools/test_dsl_run.py test/tools/test_ircheck_cli.py -ra` -> `66 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test` -> `1971 tests collected in 3.12s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test -ra --maxfail=1` -> `1971 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate python3 -m expectation.core.print` -> 8 个 core print 合同 case 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONPYCACHEPREFIX=/tmp/kernelcode_pycache_core_print python3 -m compileall -q kernel_gen kernel test` -> 通过。
- `git diff --check` -> 通过。
- `git diff --name-only -- expectation .skills ARCHITECTURE/plan` -> 无输出，确认未改 expectation、`.skills` 与计划书。
- `rg -n 'str\((module|target|result|output)\)|Printer\(.*\)\.print_op|print_op\(' kernel_gen/passes/pass_manager.py kernel_gen/tools/dsl_run.py kernel_gen/tools/ircheck.py kernel_gen/core/print.py` -> 命中均为预期实现内或单独诊断渲染入口。
- `rg -n 'xdsl\..*_(print|parser)|_resume_from|_print|_parse|Operation\.__str__|monkeypatch|hasattr\(ctx|getattr\(ctx|object\)' kernel_gen/core kernel_gen/passes/pass_manager.py kernel_gen/tools/dsl_run.py kernel_gen/tools/ircheck.py test/core test/passes/test_pass_manager.py test/tools/test_dsl_run.py test/tools/test_ircheck_cli.py` -> 未发现越权跨文件非公开 API、ctx 能力探测、object 签名或非装饰器嵌套函数新增。
- `PYTHONDONTWRITEBYTECODE=1 coverage run --branch --source=kernel_gen -m pytest -q test && ...` -> 全量 coverage run 在执行到 `test/kernel/test_conv2d_symbolic_memory_genkernel.py::test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes` 时发生 Python segfault，栈在 `xdsl.pattern_rewriter` / `__hash__`；单条复现 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py::test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes -ra` 通过，说明全量 coverage 故障与顺序/环境相关，当前未闭合硬门禁。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/tmp/core_print_alias_expectation_site2 python3 -m expectation` -> 失败，详见 `合同验收`。

Diff 反推自测：
- `pytest -q test/core/test_print.py`：验证新增公开入口、alias 规则、非法输入与 raw attribute 打印不污染。
- `pytest -q test/passes/test_pass_manager.py test/tools/test_dsl_run.py test/tools/test_ircheck_cli.py`：验证 dump IR 默认 alias 化且入口行为未回退。
- `pytest --collect-only -q test` 与 `pytest -q test -ra --maxfail=1`：验证全量测试收集与执行顺序在本轮 diff 下可运行。
- `py_compile` 与 `git diff --check`：验证代码与文本格式无明显语法/空白问题。

合同验收：
- `python3 -m expectation.core.print`：通过。
- `python3 -m expectation`：未通过，当前只读 expectation 合同与本轮实现存在多处不一致，且不能通过修改其它 expectation 解决。
- 主要失败归因：
  - `expectation.operation.arch.*` 仍直连 `kernel_gen.target.registry._get_current_target/_set_current_target` 私有入口，而本轮实现已收口到公开 `get_current_target/set_current_target`。
  - `expectation.pass.tuning.launch_kernel_cost_func.*` 仍要求旧 `compute/memory/latency` 口径，与当前 `spec/pass/tuning/launch_kernel_cost_func.md` 的七值 kind 合同不一致。
  - `expectation.pass.lowing.nn_lowering.*`、`expectation.pass.tile.*`、`expectation.pass.memory_pool.*`、`expectation.tools.dsl_run.invalid_contract` 等 case 还保留旧文本或旧失败语义，与当前实现/公开边界不一致。

禁止修改面：
- `expectation/` 目录本轮未写入任何工作树 diff；只读合同资产仅作运行验证。
- `.skills/` 无任何改动。
- 计划书文件未在 worktree 内修改。
- 未新增除 `kernel_gen.core.print.print_operation_with_aliases(operation: Operation | ModuleOp) -> str` 之外的公开 API。
- 未引入 `object` 签名、ctx 能力探测、跨文件非公开 helper 调用或非装饰器嵌套函数。

自检：
- 接口：新增公开入口签名与 `spec/core/print.md` 一致，dump 入口仍保持公开路径而非新增并行 API。
- 边界：未越权修改 expectation；未改 `.skills`；未改未授权公开 API。
- 异常：非法输入 `TypeError` 与现有稳定错误文本保持一致；full expectation 失败已单列归因，不被误判为实现通过。
- 兼容：普通 `str(op)` 与 raw attribute 打印未被 alias printer 污染。
- 冗余：core alias printer 的私有 helper 仅在当前文件内使用，无跨文件 helper 外泄。
- 注释：新增/修改函数已补 `功能说明` 与 `使用示例`。
- 复用：dump 接入统一走 `print_operation_with_aliases(...)`，未在多处重复拼装 alias IR。
- 粒度：alias printer、dump 入口、测试入口拆分清晰。
- 输入/输出：alias IR 可 parse round-trip；非法参数失败语义稳定。
- 资源/并发/性能：无新增全局 alias 状态；全量 expectation/coverage 的崩溃与本轮代码相关性待架构/合同进一步裁定。
- 测试有效性：pytest 反向断言在实现破坏时会失败；expectation 失败已保留原始 stderr/trace 证据。

结论：需修改 / 阻塞。当前可执行闭环已覆盖 core print、dump 接入与全量 pytest，但全量 expectation 与 full coverage 仍未闭合；其中 expectation 存在与当前公开合同不一致的历史资产冲突，coverage 全量运行存在 segfault 复现，需要架构裁定或后续专项收口。

---

时间：2026-05-07 04:30 CST
经办人：守护最好的爱莉希雅
类型：架构裁定 / 最小继续路径

裁定结论：
- 当前不得进入 `review`，任务保持 `execute` 阻塞 / 继续收口态。
- `python3 -m expectation` 与 `kernel_gen` coverage `95/80` 仍是本计划硬门禁；在计划未被用户更新前，不得带这些 blocker 进入 review。

全量 expectation 裁定：
- 全量 `expectation` 仍是本计划必过合同验收资产。
- 不允许通过恢复 `target_registry._get_current_target/_set_current_target` 私有入口、重新引入旧 `compute/memory/latency` cost kind 兼容，或新增未确认公开 API 来让旧 expectation 通过。
- 对仍可由当前公开 spec / 实现修复的失败，继续在本任务 `execute` 内修实现、必要 `spec` 和 pytest。
- 对已经确认与当前公开合同冲突的只读 expectation 资产，普通 execute/review/merge 不得修改；最小继续路径是先取得用户或架构师极窄授权处理合同资产，再回到本任务复跑全量 expectation。
- 当前已知需要极窄授权确认的范围：
  - `expectation/operation/arch/**`：旧 case 直连 `kernel_gen.target.registry._get_current_target/_set_current_target`，应改为当前公开 `get_current_target/set_current_target` 口径；不得在实现中恢复下划线入口。
  - `expectation/pass/tuning/launch_kernel_cost_func/**`：旧 `compute/memory/latency` 文本与当前七值 cost kind spec 冲突；若当前七值合同为真源，应极窄更新这些 expectation 到当前公开合同；不得把实现回退到旧三值合同。
  - 其它 25 个失败中若存在同类“旧 expectation 文本 / 旧失败语义 vs 当前公开合同”冲突，按同一规则列清文件与 case 后等待授权；非冲突类继续由 execute 修实现。

coverage 裁定：
- full coverage `95/80` 仍是本计划 execute 阻断项，当前不能因“单条复现通过”而视为通过。
- execute 可先在本任务内继续排查全量顺序 segfault；若要改用 coverage parallel/shard + combine 作为等价验收，必须同时满足：
  - 覆盖全量 `test`，不 skip/xfail，不缩小 `--source=kernel_gen`，不扩大 omit，不降低 `95/80`；
  - 生成同一个 coverage JSON 并通过 `script/check_python_coverage.py --include-module kernel_gen --line-min 95 --branch-min 80`；
  - 在任务记录写清 shard 命令、collect 数量、每个 shard 结果、combine 结果和 line/branch 数值；
  - 由架构 / 用户确认该 sharded coverage 验收可替代原全量顺序命令。
- 若 sharded coverage 仍 segfault，或只能通过跳测 / omit / 降阈值规避，则必须回用户确认是否拆独立 coverage 顺序 / 环境专项；在确认前本任务继续阻塞。

流转裁定：
- 当前不允许 `-next review`。
- 最小继续顺序：
  1. execute 继续归因并修复所有非 expectation 合同冲突类失败。
  2. 管理员 / 架构侧向用户确认或补建极窄 expectation 合同资产处理口径；普通 execute 不直接改未授权 expectation。
  3. execute 在最新同步现场复跑 `python3 -m expectation`。
  4. execute 完成 full coverage `95/80`，或在架构 / 用户确认后用等价 sharded coverage + combine 通过。
  5. `python3 -m expectation`、full pytest、coverage `95/80`、`git diff --check`、禁止修改面和静态扫描全部通过后，才允许进入 review。

## 架构裁定 - 2026-05-07 04:29 +0800 - 大闸蟹

结论：不允许带当前 blocker 进入 review，任务继续停留在 execute / 阻塞态；不得由普通 execute、review 或 merge 修改 `expectation/`。

1. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation` 仍是本计划必过合同硬门禁。执行人可继续修复由 `kernel_gen/spec/test` 实现缺口导致的失败，但不得为了通过旧合同而恢复跨文件私有 API、回退当前公开 spec，或新增未确认公开 API。
2. 当前已归因为旧合同资产冲突的失败，例如 `expectation.operation.arch.*` 直连 `target_registry._get_current_target/_set_current_target` 私有入口、`expectation.pass.tuning.launch_kernel_cost_func.*` 仍锁旧 `compute/memory/latency` 口径，与本计划普通 execute 可修改范围冲突。该类失败不授权 execute 直接改 expectation；需要先列出精确失败矩阵，并由用户或架构师对具体 expectation 路径给极窄授权，或另拆合同资产同步计划。当前不作 blanket 授权。
3. coverage 95/80 仍是本计划硬门禁。全量顺序 coverage segfault 不是可带入 review 的残留风险；执行人应记录最小复现、失败顺序、最后通过的单测与栈摘要，并优先判断是否为本轮实现引入的状态污染 / 递归 hash / alias printer 状态泄漏。若最终证明只能作为外部环境或顺序专项处理，需回用户确认拆分或调整验收归属；确认前不得降级为通过。
4. 最小继续路径：小李飞刀继续保持 execute 阻塞，不 `-next review`；补充 `full expectation` 失败矩阵与 `coverage segfault` 最小复现记录。神秘人据此回用户确认是否授权处理 `expectation/core/print.py` 以外的具体合同资产，或拆出 expectation 合同同步 / coverage 顺序专项。未取得确认前，本任务不得进入 review/终验/merge。

---

时间：2026-05-07 04:50 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / execute 阻塞证据补充
任务目标：按神秘人与守护最好的爱莉希雅 / 大闸蟹最新裁定，补齐 full expectation 失败矩阵与 coverage 顺序问题证据；保持任务在 execute，不进入 review，不改 `expectation/`。

执行前阅读记录：
- 已重新读取个人提示词、`AGENTS.md`、`agents/standard/任务记录约定.md` 与 `agents/standard/实现文件规范.md`。
- 已确认最新硬口径：`python3 -m expectation` 与 coverage `95/80` 仍是本计划硬门禁；未全部通过前不得 `-next review`。
- 已确认普通 execute/review/merge 不得修改 `expectation/`，不得恢复 `target_registry._get_current_target/_set_current_target` 私有入口，不得回退旧 `compute/memory/latency` cost kind，不得新增未确认公开 API。
- 已执行 `git fetch origin`，当前 `HEAD=origin/main=merge-base=673349f53bc3f29e804ff47c2784c57b12aa9d54`，worktree 与最新主线同步且任务 diff 未被覆盖。

改动：
- 仅追加本任务记录。
- 未修改 `kernel_gen/`、`spec/`、`test/` 或 `expectation/`。
- `expectation/` 在目标 worktree 内仍不存在；本轮只使用 `/tmp/core_print_alias_expectation_site2` 的只读同步现场运行主仓 expectation 合同。

full expectation 执行证据：
- 执行目录：`/tmp/core_print_alias_expectation_site2`
- 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/tmp/core_print_alias_expectation_site2 python3 -m expectation`
- 结果：退出码 `1`，失败 `25` 个 module。
- 详细日志：`/tmp/core_print_full_expectation_20260507.log`

full expectation 失败矩阵：

| # | expectation 路径 | 失败命令 | 失败摘要 | 现行 spec / 公开 API | 可由 kernel_gen/spec/test 修复 | 是否需要 expectation 极窄授权 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `expectation.operation.arch.get_block_id` | `python3 -m expectation.operation.arch.get_block_id` | 3 cases 直连 `target_registry._get_current_target`，当前属性不存在。 | `spec/target/registry.md` 公开 `get_current_target()/set_current_target(...)`；`spec/operation/arch.md` 约束 arch helper 只走公开 target registry。 | 否；按裁定不得恢复下划线私有入口。 | 是；若当前公开 API 为真源，需要极窄更新该 expectation。 |
| 2 | `expectation.operation.arch.get_block_num` | `python3 -m expectation.operation.arch.get_block_num` | 3 cases 直连 `target_registry._get_current_target`。 | 同上。 | 否。 | 是。 |
| 3 | `expectation.operation.arch.get_dynamic_memory` | `python3 -m expectation.operation.arch.get_dynamic_memory` | 1 case 直连 `_get_current_target`，2 cases 直连 `_set_current_target`。 | 同上。 | 否。 | 是。 |
| 4 | `expectation.operation.arch.get_subthread_id` | `python3 -m expectation.operation.arch.get_subthread_id` | 3 cases 直连 `_get_current_target`。 | 同上。 | 否。 | 是。 |
| 5 | `expectation.operation.arch.get_subthread_num` | `python3 -m expectation.operation.arch.get_subthread_num` | 3 cases 直连 `_get_current_target`。 | 同上。 | 否。 | 是。 |
| 6 | `expectation.operation.arch.get_thread_id` | `python3 -m expectation.operation.arch.get_thread_id` | 3 cases 直连 `_get_current_target`。 | 同上。 | 否。 | 是。 |
| 7 | `expectation.operation.arch.get_thread_num` | `python3 -m expectation.operation.arch.get_thread_num` | 3 cases 直连 `_get_current_target`。 | 同上。 | 否。 | 是。 |
| 8 | `expectation.operation.arch.launch_kernel` | `python3 -m expectation.operation.arch.launch_kernel` | 2 cases 直连 `_set_current_target`。 | 同上；`spec/operation/arch.md` 固定 `launch_kernel[...]` 公开语义。 | 否。 | 是。 |
| 9 | `expectation.pass.lowing.nn_lowering.element_binary.add` | `python3 -m expectation.pass.lowing.nn_lowering.element_binary.add` | dynamic case 的 `symbol.add ... -> !symbol.int<#symbol.expr<1 + G>>` CHECK-NEXT 未命中。 | `spec/pass/lowering/nn_lowering/spec.md` 与 `element_binary_lowering.md`：动态 result shape 需按 rank 生成 `symbol.get_dim`，mixed scalar 路径走 `dma.fill`。 | 待继续对照 actual IR；若 actual 违反现行 spec，则修 kernel_gen/spec/test；若 actual 符合现行 spec，则需 expectation 授权。 | 待判定。 |
| 10 | `expectation.pass.lowing.nn_lowering.element_binary.div` | `python3 -m expectation.pass.lowing.nn_lowering.element_binary.div` | dynamic case 的 `symbol.add ... <1 + SZQ>` CHECK-NEXT 未命中。 | 同上。 | 待继续对照 actual IR。 | 待判定。 |
| 11 | `expectation.pass.lowing.nn_lowering.element_binary.mul` | `python3 -m expectation.pass.lowing.nn_lowering.element_binary.mul` | dynamic case 的 `symbol.add ... <1 + O>` CHECK-NEXT 未命中。 | 同上。 | 待继续对照 actual IR。 | 待判定。 |
| 12 | `expectation.pass.lowing.nn_lowering.element_binary.sub` | `python3 -m expectation.pass.lowing.nn_lowering.element_binary.sub` | dynamic case 的 `symbol.add ... <1 + FOIKRM>` CHECK-NEXT 未命中。 | 同上。 | 待继续对照 actual IR。 | 待判定。 |
| 13 | `expectation.pass.lowing.nn_lowering.element_binary.truediv` | `python3 -m expectation.pass.lowing.nn_lowering.element_binary.truediv` | dynamic case 的 `symbol.add ... <1 + QWSZI>` CHECK-NEXT 未命中。 | 同上。 | 待继续对照 actual IR。 | 待判定。 |
| 14 | `expectation.pass.lowing.nn_lowering.img2col.img2col1d` | `python3 -m expectation.pass.lowing.nn_lowering.img2col.img2col1d` | dynamic case 期望 `floordiv` 形态的函数签名 / stride 文本，CHECK-NEXT 未命中。 | `spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md` 现行文本要求动态输出 extent 沿用 `SymbolDim` 字符串口径，`(expr // stride) + 1` 以 `//` 保留，不回退 `floor/floordiv`。 | 否；若当前 spec 为真源，不应回退实现到旧 `floordiv` 文本。 | 是；需极窄同步该 expectation 到当前 `//` 文本口径。 |
| 15 | `expectation.pass.lowing.nn_lowering.img2col.img2col2d` | `python3 -m expectation.pass.lowing.nn_lowering.img2col.img2col2d` | dynamic case 期望 `floordiv` 形态的函数签名 / stride 文本，CHECK-NEXT 未命中。 | 同上。 | 否。 | 是。 |
| 16 | `expectation.pass.lowing.nn_lowering.transpose` | `python3 -m expectation.pass.lowing.nn_lowering.transpose` | dynamic case 期望 `symbol.get_dim` 的固定位置，CHECK-NEXT 未命中。 | `spec/pass/lowering/nn_lowering/spec.md` 与 `dma_structured_lowering.md`：`nn.transpose` lower 为 `dma.transpose`，动态符号维处理需符合当前 lowering 规则。 | 待继续对照 actual IR；可能是实现顺序缺口，也可能是旧文本顺序冲突。 | 待判定。 |
| 17 | `expectation.pass.memory_pool.dynamic` | `python3 -m expectation.pass.memory_pool.dynamic` | `mixed_scope_alloc` 期望某条 `symbol.add` offset base，CHECK-NEXT 未命中。 | `spec/pass/lowering/memory_pool.md`：同一 `func + memory space` 内 alloc 按词法出现顺序线性切分，rewrite 为 `arch.get_dynamic_memory + dma.subview + dma.reshape`。 | 是；该项优先按 memory_pool 实现 / pytest 对照继续排查，不先视为 expectation 冲突。 | 暂不需要，除非确认 actual 已符合 spec。 |
| 18 | `expectation.pass.pipeline.default_lowering` | `python3 -m expectation.pass.pipeline.default_lowering` | case 2 `AssertionError`，日志未给出额外消息。 | `spec/pass/pipeline/default_lowering.md`：顺序固定为 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy`，黑盒结果含 out-param ABI 与 `kernel.binary_elewise(kind="add")`。 | 是；需先按 case 2 actual 输出比对 pipeline 当前实现 / spec。 | 暂不需要，除非确认旧 expectation 文本冲突。 |
| 19 | `expectation.pass.tile.analysis.broadcast` | `python3 -m expectation.pass.tile.analysis.broadcast` | `tiled-dynamic` 期望函数签名 / `tile.tile_exprs` 前置文本，CHECK-NEXT 未命中。 | `spec/pass/tile/analysis.md`：`tile-analysis` 只补 `tile.analysis` 与 `tile.tile_exprs`，外层 `symbol.for` 内已切 shape 需要写回 tile exprs，broadcast expand 维保持空。 | 待继续对照 actual IR。 | 待判定。 |
| 20 | `expectation.pass.tile.elewise.element_compare` | `python3 -m expectation.pass.tile.elewise.element_compare` | 4 cases 期望 `dma.view` operand 排列 / stride 文本，CHECK-NEXT 未命中。 | `spec/pass/tile/elewise.md`：`tile-elewise` 消费 `tile.analysis` / `tile.tile_exprs` 并生成 `symbol.for + dma.view`。 | 是；优先按 tile-elewise 当前实现 / spec 排查，不先 blanket 授权 expectation。 | 暂不需要，除非确认旧 expectation 文本冲突。 |
| 21 | `expectation.pass.tuning.launch_kernel_cost_func.basic_all` | `python3 -m expectation.pass.tuning.launch_kernel_cost_func.basic_all` | `compute` / `memory` 旧 kind 被当前实现拒绝，报 `cost_kind must be '|' separated names from [DMA1,DMA2,DMA3,DMA4,MAC,VECTOR1,VECTOR2]`。 | `spec/pass/tuning/launch_kernel_cost_func.md`：`cost_kind` 只接受七值集合，旧 `compute/memory/DMA` 必须显式失败。 | 否；按裁定不得回退旧 kind。 | 是；需极窄更新该 expectation。 |
| 22 | `expectation.pass.tuning.launch_kernel_cost_func.multi_kind` | `python3 -m expectation.pass.tuning.launch_kernel_cost_func.multi_kind` | 旧 `compute|memory|latency` 多 kind 被当前七值合同拒绝。 | 同上。 | 否。 | 是。 |
| 23 | `expectation.pass.tuning.launch_kernel_cost_func.shared_callee_once` | `python3 -m expectation.pass.tuning.launch_kernel_cost_func.shared_callee_once` | 旧 cost kind 被当前七值合同拒绝。 | 同上。 | 否。 | 是。 |
| 24 | `expectation.tools.dsl_cost_run.invalid_contract` | `python3 -m expectation.tools.dsl_cost_run.invalid_contract` | cases 1/2 仍期望旧错误 `['DMA', 'MAC']`；case 3 pipeline 仍含旧 `cse` pass 并使用旧 `DMA` kind，报 `PassRegistryError: unknown pass 'cse'`。 | `spec/tools/dsl_cost_run.md` 与 `spec/tools/dsl_run.md`：`dsl_cost_run` 只接受 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2`；缺 sibling 失败固定为 `DslCostRunMissingCostFunction`；不回退普通 kernel。 | 否；不应为旧 expectation 恢复旧 kind 或旧 pass 名。 | 是；需极窄更新该 expectation 到当前七值 / 当前 pipeline 口径。 |
| 25 | `expectation.tools.dsl_run.invalid_contract` | `python3 -m expectation.tools.dsl_run.invalid_contract` | case 6 仍期望 real_args 只支持 `torch.Tensor/numpy.ndarray` 且 helper 可隐式可见；当前 spec 支持 `int/float` runtime scalar 且不隐式注入 helper，实际报 `Unsupported call expression`。 | `spec/tools/dsl_run.md`：`real_args` 元素允许 `torch.Tensor | numpy.ndarray | int | float`；DSL 函数体名称必须来自显式 import / 闭包 / 全局绑定，`dsl_run` 不补写 `func.__globals__`。 | 否；不应回退到旧 real_args 合同或隐式 helper 注入。 | 是；需极窄更新该 expectation。 |

coverage 顺序 / segfault 证据：
- 旧失败命令：`PYTHONDONTWRITEBYTECODE=1 coverage erase && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test && ...`
- 旧失败结果：退出码 `139`，约 `54%` 进度，正在执行 `test/kernel/test_conv2d_symbolic_memory_genkernel.py::test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes`。
- 旧栈摘要：`xdsl/irdl/operations.py::__hash__` -> `xdsl/pattern_rewriter.py::_populate_worklist/rewrite_region/rewrite_module` -> `kernel_gen/passes/pass_manager.py::_fold_module/run` -> `kernel/runner.py::run_lowering_demo` -> `test/kernel/test_conv2d_symbolic_memory_genkernel.py:148`。
- `IRDLOperation.__hash__` 当前源码为 `return id(self)`，未发现 Python 层递归 hash 实现。
- 静态扫描 `print_operation_with_aliases|dump_dir|set_dump_dir|restore_config` 显示 alias printer 只在 dump 入口使用；目标 conv2d 单测不设置 dump_dir；`test/core/test_print.py` 后接目标单测未复现崩溃，当前无证据指向 alias printer 全局状态泄漏。

coverage 最小复现 / 排查命令：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test > /tmp/core_print_collect.txt` -> 目标 conv2d case 位于收集顺序 `1099-1101`，文件顺序第 `54` 个。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py::test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes -ra` -> 通过，`1 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -ra` -> 通过，`3 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test/core/test_print.py test/kernel/test_conv2d_symbolic_memory_genkernel.py::test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes -ra` -> 通过，`7 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test/include/npu_demo/test_runtime_launch.py test/kernel/test_conv2d_symbolic_memory_genkernel.py::test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes -ra` -> 通过，`2 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test/dsl/gen_kernel/test_gen_kernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py::test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes -ra` -> 通过，`92 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q $(collect order files 1..54) -ra` -> 通过，`1101 passed`。
- 复跑完整 coverage gate：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage erase && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 coverage run --branch --source=kernel_gen -m pytest -q test -ra && PYTHONDONTWRITEBYTECODE=1 coverage json -o /tmp/core_print_alias_dump_cov_rerun.json && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 script/check_python_coverage.py --coverage-json /tmp/core_print_alias_dump_cov_rerun.json --include-module kernel_gen --line-min 95 --branch-min 80`
- 复跑完整 coverage gate 结果：pytest 阶段通过，`1971 passed, 1 warning in 335.19s`；未复现 segfault；coverage check 退出码 `1`，失败为 `line coverage 94.17% < 95.00%`，branch 为 `86.35% >= 80.00%`。
- 当前最低覆盖缺口摘要：`kernel_gen/passes/memory_pool.py` missing `125` lines，`kernel_gen/dialect/symbol.py` missing `62` lines，`kernel_gen/dsl/ast/nodes/dma.py` missing `56` lines，`kernel_gen/tools/ircheck.py` missing `48` lines，`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py` missing `44` lines，`kernel_gen/execute_engine/compiler.py` missing `42` lines。

Diff 反推自测：
- 本次记录追加没有产品代码 diff；反推测试重点为阻塞复现命令。
- `pytest --collect-only -q test`：用于确认当前 full test 收集顺序与目标 conv2d case 位置。
- coverage 单条 / 单文件 / 组合 / 前缀 / 全量命令：用于确认旧 segfault 当前是否可复现，以及硬门禁当前真实失败类型。
- full expectation 命令：用于确认全量合同当前失败矩阵，而非只凭局部失败判断。

自检：
- 接口：本次未新增、删除、重命名或修改公开 API。
- 边界：未修改 `expectation/`、`.skills/`、计划书或主仓协调资产。
- 异常：full expectation 失败逐项列出路径、命令、失败摘要与当前判断；未把旧合同冲突作为 blanket 授权处理。
- 兼容：未恢复私有 target registry helper，未回退旧 cost kind，未新增未确认公开 API。
- 实现遗漏：仍存在 full expectation 25 项失败，其中 operation/arch、launch-kernel-cost-func、dsl_cost_run、dsl_run 已明确属于旧合同冲突；nn_lowering、memory_pool、pipeline、tile 相关项仍需继续 actual IR 对照后收口。
- 资源/并发/性能：旧 coverage segfault 当前不可复现；全量 coverage 仍因行覆盖率 `94.17 < 95` 阻塞。
- 测试有效性：本次只补阻塞证据；未用 expectation 替代 diff 反推测试；未跳测、xfail、omit 或降阈值。

结论：阻塞 / 继续 execute。当前不得 `-next review`；只有 full expectation、full pytest、coverage 95/80、`git diff --check`、禁止修改面和静态扫描全部通过后，才允许流转 review。

## 用户补充验收重点 - 2026-05-07 - 大闸蟹记录

用户指出：由于 symbol expr / memory expr 定义已变，类似 `if isinstance(dim, IntAttr)` / `if isinstance(dim, StringAttr)` 来解析 `NnMemoryType.shape/stride` 的旧代码不应继续存在。后续 review / 架构复核 / 终验必须重点检查：

1. `NnMemoryType.shape` / `NnMemoryType.stride` 条目必须按 `SymbolExprAttr` 处理；不得继续把 memory layout 条目当旧 `IntAttr` / `StringAttr` 解析、动态判断或构造。
2. 合法例外仅限非 memory layout 语义，例如 axis / perm / kind / op_name / memory space / tile.analysis metadata 等明确仍由 `IntAttr` / `StringAttr` 承载的公开属性；不得用这些例外掩盖 shape/stride 旧分支。
3. 重点扫描范围：`kernel_gen/passes/memory_pool.py`、`kernel_gen/passes/dma_memory_hierarchy.py`、`kernel_gen/passes/decompass.py`、`kernel_gen/passes/lowering/nn_lowering/**`、`kernel_gen/passes/tile/**`、`kernel_gen/core/contracts.py` 中与 `shape.data` / `stride.data` 直接相关的旧判断、旧错误文本和 `NnMemoryType(ArrayAttr([IntAttr/StringAttr...]))` 构造。
4. review/终验若发现仍有 memory shape/stride 旧分支残留，不能判通过；应回到 execute 继续按 `SymbolExprAttr` 收口，除非有 spec 明确列出的公开例外。

---

时间：2026-05-07 18:40 +0800
任务：T-20260507-bfc9a0e0 / execute 继续收口
目标：按用户与架构补充要求，清理 `kernel_gen/**` 中 `NnMemoryType.shape/stride` 旧 `IntAttr/StringAttr` layout 分支，记录扫描命令、清理范围、合法例外与剩余阻塞。

---

时间：2026-05-07 11:21 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / execute 继续收口
目标：继续只处理实现 / spec / test 侧可独立收口项；不写 `expectation/`；不引用任一 expectation sync worktree 作为通过依据；不进入 review。

最新同步口径：
- 神秘人再次冻结 expectation sync 引用：`alias-sync` 与 `contract-sync` 当前仍有互相冲突口径。
- 在两位架构师形成同一最终落点前，本 execute 不使用 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync` 或 `/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync` 作为通过依据。
- 普通 execute 仍不得写、移动、新建或删除 `expectation/`；本轮 `git diff --name-only -- expectation .skills` 无输出。
- 当前不执行 `-next review`。

实现侧修复：
- 修复 `default-lowering` 与当前 `spec/pass/pipeline/default_lowering.md` 不一致的问题。
- `kernel_gen/passes/pipeline/default_lowering.py` 中 `build_default_lowering_pipeline()` 改为显式使用 `LowerDmaMemoryHierarchyPass(fold=False)`。
- 原因：当前 `LowerDmaMemoryHierarchyPass()` 默认 `fold=True` 且无 `apply_op` 时是 no-op，不能产出 default-lowering spec 要求的 legacy `dma.slice / dma.deslice` staging 链。
- 同步更新该实现文件文件级说明和函数注释，写清 default-lowering 的公开黑盒合同是保留 `dma.slice / dma.deslice` 链。
- `test/passes/pipeline/test_default_lowering.py` 新增公开黑盒回归 `test_default_lowering_pipeline_add_uses_legacy_dma_hierarchy`，只通过公开 `PassManager` / pipeline builder / target registry / dialect op 可达性验证：
  - memory-return `nn.add` 经过 default-lowering 后变成前置 out-param ABI；
  - `func` 输出为空；
  - IR 中存在 `dma.slice` 与 `dma.deslice`；
  - `kernel.binary_elewise(kind="add", space=local)` 命中。

actual IR / spec / verdict 矩阵补充：

| 项 | actual / expected 差异 | 当前 spec 对照 | verdict |
| --- | --- | --- | --- |
| `nn_lowering.element_binary.add/div/mul/sub/truediv` | actual 使用 `#symbol.expr<X + 1>` 等 canonical 文本，旧 expectation 要求 `#symbol.expr<1 + X>`。 | 当前 `SymbolExprAttr` / nn_lowering spec 不要求保留旧操作数文本顺序，只要求动态 result shape 用当前 symbol expr 表达。 | actual 符合当前 spec；普通 execute 不回退到旧文本顺序。 |
| `nn_lowering.transpose` | actual 对输出 `[N, M]` 先取输出轴 0 对应的 source axis 1，再取 source axis 0；旧 expectation 锁旧 `symbol.get_dim` 行顺序。 | 当前 spec 要求 `nn.transpose` lower 为 `dma.transpose`，动态维按结果维度构造，不要求旧 source-axis 顺序。 | actual 符合当前 spec；普通 execute 不改 expectation。 |
| `memory_pool.dynamic` | actual 已是 `arch.get_dynamic_memory + dma.subview + dma.reshape`，表达式为 `N*M` 等 canonical 顺序；旧 expectation 锁 `M*N` 等文本顺序。 | 当前 memory_pool spec 要求按词法顺序线性切分和结构化 `SymbolExprAttr`，不要求旧 commutative 文本顺序。 | actual 符合当前 spec；仅记录旧合同差异。 |
| `pipeline.default_lowering` | 修复前 actual 未出现 `dma.slice / dma.deslice`，违反 spec；修复后 probe 得到 `slice_count=4`、`deslice_count=2`、`kernel_space=local`。 | 当前 default-lowering spec 明确要求 `lower-dma-memory-hierarchy` legacy staging 链。 | 已修实现并补 pytest。 |
| `tile.analysis.broadcast.tiled_dynamic` | 只读诊断中 `run_ircheck_text` 返回 `ok=True`。 | 当前 tile-analysis spec 要求保留 `tile.analysis + tile.tile_exprs`。 | 当前诊断样例符合 spec。 |
| `tile.elewise.element_compare` | actual 包含 `symbol.for`、3 个 `dma.view`、`tile.analysis`、`tile.tile_exprs`，旧 expectation 锁旧短文本行。 | 当前 tile-elewise spec 约束语义与公开 attrs，不要求旧 `dma.view` 简写文本。 | actual 符合当前 spec；普通 execute 不改 expectation。 |
| `tile.reduce.fc` | isolated static / dynamic / mixed 只读诊断均 `ok=True`；此前 full suite `-11` 属顺序 / 子进程稳定性风险。 | 当前 tile-reduce spec 仍以目录级 pass 行为为准。 | 暂无实现侧语义缺口，继续记录 full-suite 风险。 |

NnMemoryType layout 旧分支扫描：
- 命令：`rg -n 'NnMemoryType\\(ArrayAttr\\(\\[(IntAttr|StringAttr)|isinstance\\([^\\n]+,\\s*(IntAttr|StringAttr)\\)|\\.shape\\.data|\\.stride\\.data|shape\\.data|stride\\.data' kernel_gen || true`
- 命令：`rg -n 'IntAttr|StringAttr' kernel_gen/passes/memory_pool.py kernel_gen/passes/dma_memory_hierarchy.py kernel_gen/passes/decompass.py kernel_gen/passes/lowering/nn_lowering kernel_gen/passes/tile kernel_gen/core/contracts.py || true`
- 结果：未发现 `memory_pool.py` 中继续按 `IntAttr` / `StringAttr` 解析 `NnMemoryType.shape/stride` 的旧分支；重点 pass 中剩余 `IntAttr` / `StringAttr` 命中属于合法例外或非 memory layout 属性：
  - `SymbolGetDimOp(..., IntAttr(axis))`：axis 属性。
  - `transpose perm`、`reduce axis/keepdim`：公开整数 metadata。
  - `tile.analysis` / `tile.tile_exprs`：公开 tile metadata 文本。
  - `op_name`、`kind`、`space`、target width：非 `NnMemoryType.shape/stride` layout。
  - `matmul_img2col_lowering._build_symbol_attr(...)`：`symbol.floordiv` / symbol arithmetic op 所需 attr，不构造 `NnMemoryType(ArrayAttr([IntAttr/StringAttr...]))`。
- 仍需注意：`shape.data` / `stride.data` 的遍历本身是当前 `NnMemoryType` 结构化 API 的正常读取，判定重点是条目是否继续兼容旧 `IntAttr/StringAttr`。本轮扫描未发现重点 pass 中该类旧 layout 分支残留。

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py -ra` -> `3 passed, 1 warning in 0.30s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/pipeline/default_lowering.py test/passes/pipeline/test_default_lowering.py && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/test_dma_memory_hierarchy.py test/passes/test_pass_manager.py -k 'default_lowering or dma_memory_hierarchy or lower_dma_memory_hierarchy' -ra` -> `18 passed, 14 deselected, 1 warning in 0.31s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/pipeline/default_lowering.py test/passes/pipeline/test_default_lowering.py && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test` -> `1989 tests collected in 1.69s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage erase && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 coverage run --branch --source=kernel_gen -m pytest -q test -ra && PYTHONDONTWRITEBYTECODE=1 coverage json -o /tmp/core_print_alias_dump_cov.json && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 script/check_python_coverage.py --coverage-json /tmp/core_print_alias_dump_cov.json --include-module kernel_gen --line-min 95 --branch-min 80` -> `1989 passed, 1 warning in 334.46s`；coverage gate 通过，`line=95.00%`，`branch=87.93%`。
- `git diff --check` -> 通过。
- `git diff --name-only -- expectation .skills` -> 无输出。

合同验收：
- 本轮未把任一 expectation sync worktree 作为通过依据。
- 本轮未写 `expectation/`。
- 因最新口径再次冻结 sync 引用，full expectation 仍保持未闭合阻塞；待两位架构师统一唯一 sync 落点后，才能按统一路径复跑 `python3 -m expectation` 并记录为合同验收结果。

自检：
- 接口：未新增、删除、重命名或修改公开 API；`default-lowering` 行为与现行 spec 对齐。
- 边界：只改原 execute worktree 内实现 / test / 记录；未碰主仓协调资产，未碰 `.skills` 与 `expectation/`。
- 异常：保留 expectation sync 冻结为阻塞，不用未统一链路制造通过。
- 兼容：target registry 使用公开 API；测试未直连下划线 helper。
- 实现遗漏：`pipeline.default_lowering` 已由实际 IR 与 pytest 覆盖；其它矩阵项暂未发现当前 spec 违例。
- 冗余：没有新增并行 pipeline 或重复 hierarchy rewrite；只调整已有 pipeline pass 参数。
- 注释准确性：实现文件文件级说明和函数注释已同步 `fold=False` 的公开行为。
- 复用 / 函数粒度：新增 pytest helper 仅服务当前测试文件，不外泄为产品 API。
- 输入 / 输出校验：新增黑盒测试锁定 out-param ABI、slice/deslice、kernel op kind/space。
- 测试有效性：pytest 失败会直接暴露 `fold=True` no-op 回退；expectation 未被用作 Diff 反推测试。

结论：继续 execute / 阻塞。实现侧 `pipeline.default_lowering` 缺口已修复，full pytest 与 coverage gate 当前通过；由于 expectation sync 唯一落点再次冻结，full expectation 不能作为通过证据，当前不得 `-next review`。

---

时间：2026-05-07 11:28 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / execute 合同验收阻塞复核

最新同步口径：
- 大闸蟹与神秘人最新消息再次声明唯一有效 expectation 同步 worktree 为 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`，branch=`arch/core-print-alias-expectation-sync`。
- 固定验证命令应为：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync python3 -m expectation`。
- 普通 execute 仍只处理原 execute worktree 的实现 / spec / test 和 actual IR / spec 对照，不写 `expectation/`。

同步 worktree 现场核对：
- 命令：`git status --short && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD`
- 目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- 结果：branch=`arch/core-print-alias-expectation-sync`，HEAD=`673349f53bc3f29e804ff47c2784c57b12aa9d54`，仅有未跟踪记录文件 `agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-expectation-sync.md`。
- 命令：`find . -maxdepth 4 -path './expectation*' -print`
- 结果：无输出。
- 命令：`git ls-tree --name-only HEAD expectation || true` 与 `git ls-tree --name-only HEAD | rg '^expectation$' || true`
- 结果：无输出，确认该 sync worktree 当前 HEAD 不携带 `expectation/` 目录。

full expectation 合同验收：
- 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync python3 -m expectation`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`
- 日志：`/tmp/core_print_alias_full_expectation_alias_sync_20260507_1121.log`
- 结果：失败，stderr 为 `/usr/bin/python3: No module named expectation`。
- 判定：当前唯一有效 sync worktree 不携带 `expectation/` 包，固定 full expectation 验证命令不可执行。这不是原 execute worktree 的实现 / spec / test 缺口；需要管理员 / 架构师提供含 `expectation/` 合同资产的同步现场，或修正固定验证路径。

禁止修改面：
- 本轮未写 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`。
- 本轮未写原 execute worktree 的 `expectation/` 或 `.skills`；`git diff --name-only -- expectation .skills` 无输出。
- 本轮未使用重复非活动链路 `/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync` 作为通过依据。

结论：继续 execute / 阻塞，不 `-next review`。实现侧已修复当前可独立闭合的 `default-lowering` 缺口并通过 full pytest / coverage gate；full expectation 当前因唯一 sync worktree 缺 `expectation/` 包无法执行，需回报管理员 / 架构师处理同步现场。

---

时间：2026-05-07 11:31 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / expectation sync 口径冻结覆盖

最新覆盖口径：
- 神秘人最新同步：expectation sync 仍未有统一最终落点，已回用户裁定。
- 裁定前不得使用 `alias-sync` 或 `contract-sync` 任一 worktree 作为通过依据。
- 裁定前不得写 `expectation/`，不得 `-next review`。
- 本 execute 只能继续处理不依赖 sync worktree 的实现 / spec / test 侧事项并记录。

当前执行状态：
- 前一段对 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync` 的核对与固定命令尝试仅作为现场诊断保留，不再作为通过依据。
- 当前不引用 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`。
- 当前不引用 `/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`。
- 原 execute worktree 未写 `expectation/` 或 `.skills`；`git diff --name-only -- expectation .skills` 无输出。

结论：
- 继续 execute / 阻塞。
- 不 `-next review`。
- 等待用户 / 架构师给出唯一合同同步落点或新的验收路径后，再复跑 full expectation。

---

时间：2026-05-07 11:34 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / alias-sync 唯一路径复验

最新同步口径：
- 神秘人同步：大闸蟹与守护最好的爱莉希雅已统一，唯一有效落点为 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`，branch=`arch/core-print-alias-expectation-sync`。
- 固定 full expectation 验证命令：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync python3 -m expectation`。
- 重复非活动链路 `/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync` 不作为通过依据、不继续写 expectation、不分发、不合并、不引用。
- 普通 execute 仍不得写 `expectation/`。

alias-sync 现场核对：
- 命令：`git status --short --untracked-files=all && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && find . -maxdepth 2 -type d -name expectation -print`
- 目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- 结果：branch=`arch/core-print-alias-expectation-sync`，HEAD=`673349f53bc3f29e804ff47c2784c57b12aa9d54`，仅有未跟踪记录文件 `agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-expectation-sync.md`，未发现 `expectation/` 目录。

full expectation 固定命令结果：
- 命令：`set -o pipefail; PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync python3 -m expectation 2>&1 | tee /tmp/core_print_alias_full_expectation_alias_sync_20260507_1132_pipefail.log`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`
- 结果：失败，退出码 `1`。
- stderr：`/usr/bin/python3: No module named expectation`。
- 判定：alias-sync 唯一同步 worktree 当前不携带 `expectation/` 包，固定 full expectation 命令无法导入合同入口。这不是原 execute worktree 的实现 / spec / test 缺口；需要管理员 / 架构师修正同步现场或提供含 `expectation/` 的验证路径。

禁止修改面：
- 未写 `alias-sync` worktree 中任何文件。
- 未写 `contract-sync` worktree，且未引用其作为通过依据。
- 原 execute worktree `git diff --name-only -- expectation .skills` 无输出。

结论：
- 继续 execute / 阻塞。
- 不 `-next review`。
- 当前 full pytest / coverage gate 已有通过证据；full expectation 因唯一 sync worktree 缺 `expectation/` 包无法执行，需要回报管理员处理同步现场。

---

时间：2026-05-07 11:35 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / expectation sync 再次冻结

最新口径覆盖：
- 神秘人最新回报：`T-20260507-bfc9a0e0` expectation sync 冻结，再次恢复为“等待用户裁定唯一 expectation sync 落点”的状态。
- 在两位架构师形成同一最终落点前，不使用 `alias-sync` 或 `contract-sync` 任一 worktree 作为通过依据。
- 不写 `expectation/`，不 `-next review`，只能继续处理不依赖 sync 的实现 / spec / test 侧事项并记录。

当前状态：
- 这条冻结口径覆盖前面所有同步复验/命令尝试记录。
- 原 execute worktree 仍保持实现侧既有修复与记录；`git diff --name-only -- expectation .skills` 仍无输出。
- 当前不再把任何 sync worktree 作为合同验收依据。

结论：
- 继续 execute / 阻塞。
- 不 `-next review`。
- 等待用户或架构师统一唯一 expectation sync 落点后，再恢复 full expectation 验收。

执行边界：
- 未修改 `expectation/`；`git diff --name-only -- expectation .skills` 无输出。
- 未修改 `.skills/`。
- 未恢复旧私有 API，未新增未确认公开 API。
- 未进入 `review`，当前仍保持 execute 阻塞。

清理范围：
- `kernel_gen/passes/memory_pool.py`：memory layout 维度求值路径只接受 `SymbolExprAttr`；旧 `_sympy_expr_from_text` / `IntAttr` / `StringAttr` layout 兼容路径已清理。
- `kernel_gen/passes/decompass.py`：`_symbol_expr_text` 只承接 `SymbolExprAttr`，不再把裸 `IntAttr` / `StringAttr` 当 memory shape/stride。
- `kernel_gen/passes/dma_memory_hierarchy.py`：动态 shape / full-window 相关路径只读 `SymbolExprAttr` layout；保留 `SymbolGetDimOp(..., IntAttr(axis))` 作为合法 axis 属性。
- `kernel_gen/passes/tile/analysis.py`：tile analysis 读取 memory shape 时只接受 `SymbolExprAttr`；tile metadata 的 `StringAttr` 保持为合法例外。
- `kernel_gen/passes/lowering/nn_lowering/**`：element/select/cast/dma structured/reduce/matmul img2col 相关 memory layout helper 已收口为 `SymbolExprAttr`；axis、keepdim、op attribute、img2col 参数属性继续按公开属性语义处理。
- `kernel_gen/dialect/symbol.py`：`symbol.get_dim/get_stride` 的 memory entry 只从 `SymbolExprAttr` 推导；裸 `IntAttr/StringAttr` 不再作为 memory layout 输入。
- `kernel_gen/core/contracts.py`：`collect_int_dims` / `dims_equal` 只按 `SymbolExprAttr` layout 判断；`IntAttr` 仅保留给 `IntegerType.width` 等非 memory layout 属性。
- `kernel_gen/dialect/kernel.py`、`kernel_gen/dialect/__init__.py`、相关 `spec` 与公开 pytest：同步当前 `ArrayAttr[SymbolExprAttr]` layout 真源，不再用旧 layout helper 构造通过样例。

扫描命令与结果：
- `rg -n "NnMemoryType\(ArrayAttr\(\[.*(IntAttr|StringAttr)|shape=ArrayAttr\(\[.*(IntAttr|StringAttr)|stride=ArrayAttr\(\[.*(IntAttr|StringAttr)|_dim_array\(\[.*(IntAttr|StringAttr)|_make_(simple_memory_type|matrix_type|memory_type)\([^\n]*(IntAttr|StringAttr)|_normalize_dims|_normalize_memory_dims" kernel_gen test spec -g '*.py' -g '*.md'`
  - 结果：仅剩 `test/passes/test_memory_pool.py:503` 的 `element_type=StringAttr("bad")`，这是 unsupported dtype 负例，不是 memory shape/stride layout。
- `rg -n "isinstance\([^\n]*(IntAttr|StringAttr)|\b(IntAttr|StringAttr)\b" kernel_gen/passes/memory_pool.py kernel_gen/passes/dma_memory_hierarchy.py kernel_gen/passes/decompass.py kernel_gen/passes/tile kernel_gen/passes/lowering/nn_lowering kernel_gen/core/contracts.py kernel_gen/dialect/symbol.py -g '*.py'`
  - 结果：剩余命中均为合法例外或说明文本：`IntegerType.width`、`symbol.const` value、`symbol.get_dim/get_stride` axis / fold result、`tile.analysis` / `tile.tile_exprs` metadata、op kind / keepdim / img2col 参数属性、`SymbolExprAttr(expr: StringAttr)` 自身存储。

合法例外：
- `axis` / `perm` / `kind` / `op_name` / `space` 等非 memory layout 属性。
- `tile.analysis` / `tile.tile_exprs` metadata。
- `symbol.const` 的 `IntAttr` value、`symbol.get_dim/get_stride` 的 `IntAttr(axis)` 与静态 fold 返回 `IntAttr`。
- `SymbolExprAttr(expr: StringAttr)` 的内部表达式存储；该 `StringAttr` 是当前结构化 layout 属性的一部分，不是旧裸 `StringAttr` layout。
- `IntegerType.width` 等 builtin type 元数据。

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen test` -> 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_contracts.py test/dialect/test_dma.py test/dialect/test_kernel.py test/dialect/test_nn.py test/dialect/test_symbol.py -ra --maxfail=1` -> `270 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_pool.py test/passes/test_dma_memory_hierarchy.py test/passes/decompass/test_softmax.py test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py test/passes/lowering/nn_lowering -ra --maxfail=1` -> `197 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test -ra --maxfail=1` -> `1971 passed, 1 warning in 329.76s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage erase && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 coverage run --branch --source=kernel_gen -m pytest -q test -ra && PYTHONDONTWRITEBYTECODE=1 coverage json -o /tmp/core_print_alias_dump_cov_layout_cleanup.json && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 script/check_python_coverage.py --coverage-json /tmp/core_print_alias_dump_cov_layout_cleanup.json --include-module kernel_gen --line-min 95 --branch-min 80` -> pytest 阶段 `1971 passed, 1 warning in 341.95s`，coverage gate 失败：`line coverage 94.51% < 95.00%`。
- `git diff --check` -> 通过。
- `git diff --name-only -- expectation .skills` -> 无输出。

合同验收资产：
- 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/tmp/core_print_alias_expectation_site2 python3 -m expectation`
- 结果：退出码 `1`，当前全量 expectation 失败 `24` 个 module。
- 当前失败模块：
  - `expectation.operation.arch.get_block_id`
  - `expectation.operation.arch.get_block_num`
  - `expectation.operation.arch.get_dynamic_memory`
  - `expectation.operation.arch.get_subthread_id`
  - `expectation.operation.arch.get_subthread_num`
  - `expectation.operation.arch.get_thread_id`
  - `expectation.operation.arch.get_thread_num`
  - `expectation.operation.arch.launch_kernel`
  - `expectation.pass.lowing.nn_lowering.element_binary.add`
  - `expectation.pass.lowing.nn_lowering.element_binary.div`
  - `expectation.pass.lowing.nn_lowering.element_binary.mul`
  - `expectation.pass.lowing.nn_lowering.element_binary.sub`
  - `expectation.pass.lowing.nn_lowering.element_binary.truediv`
  - `expectation.pass.lowing.nn_lowering.img2col.img2col1d`
  - `expectation.pass.lowing.nn_lowering.img2col.img2col2d`
  - `expectation.pass.lowing.nn_lowering.transpose`
  - `expectation.pass.memory_pool.dynamic`
  - `expectation.pass.pipeline.default_lowering`
  - `expectation.pass.tile.elewise.element_compare`
  - `expectation.pass.tuning.launch_kernel_cost_func.basic_all`
  - `expectation.pass.tuning.launch_kernel_cost_func.multi_kind`
  - `expectation.pass.tuning.launch_kernel_cost_func.shared_callee_once`
  - `expectation.tools.dsl_cost_run.invalid_contract`
  - `expectation.tools.dsl_run.invalid_contract`

自检：
- 接口：未新增公开 API；memory layout 真源按 `ArrayAttr[SymbolExprAttr]` 保持。
- 边界：测试不再通过旧 helper 构造通过态 `NnMemoryType(ArrayAttr([IntAttr/StringAttr...]))`；旧 layout 负例改由 dialect verifier 承担。
- 异常：`memory_pool` unsupported dtype 负例仍保留 `StringAttr("bad")`，与 memory layout 无关。
- 兼容：保留 axis / metadata / op attr 的 `IntAttr/StringAttr` 合法语义，未扩大到 memory shape/stride。
- 冗余：去掉旧 `_normalize_dims` / `_normalize_memory_dims` 测试 helper，避免测试继续暗示旧 layout 兼容。
- 测试有效性：公开 pytest 全量通过，coverage gate 与 full expectation 仍真实失败并单列，不用 expectation 替代 diff 反推测试。

结论：仍为 execute 阻塞。`NnMemoryType.shape/stride` 旧 `IntAttr/StringAttr` layout 分支已按当前扫描清理；剩余阻断为 full expectation 24 项失败与 coverage line `94.51% < 95.00%`，未满足计划硬门禁，不能进入 review。

---

时间：2026-05-07 10:50 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / core_print_alias_dump execute 继续收口
任务目标：继续补齐硬门禁证据，清理过时测试实现代码，补足 coverage 95/80，并确认 full expectation 与 full pytest 当前状态。

执行前阅读记录：
- 已再次查看主仓 `TODO.md`，当前仍为 `T-20260507-bfc9a0e0` execute 进行中，记录文件为本 worktree 内 `agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-dump.md`。
- 已复读个人提示词、`AGENTS.md` 与 `agents/standard/任务记录约定.md`；本轮继续遵守不改 `expectation/`、不改 `.skills/`、不新增未确认公开 API、测试只走公开 API、`expectation` 单列为合同验收资产。
- 当前计划硬门禁仍为 full expectation、full pytest、coverage 95/80、py_compile、`git diff --check`、禁止修改面与静态扫描全部通过后才允许 `-next review`。

改动：
- `test/dialect/test_symbol.py`
  - 在公开 `SymbolExprAttr` canonical 矩阵中补 `-? -> ?` 与 `--N -> N`，覆盖当前 symbol expr 结构化语义，不恢复旧 `IntAttr/StringAttr` memory layout。
- `test/tools/test_ircheck_runner.py`
  - 新增公开 runner 测试 `test_run_ircheck_text_regex_literal_edge_matrix`，覆盖 `{.*}` 行内 regex、空 `{{}}` regex 与未 token 化 `[[` 变量片段的公开解析边界。
  - 新增 `test_run_ircheck_text_rejects_trailing_empty_case`，覆盖多 case 尾部空 case 的公开错误。
  - 新增 `test_run_ircheck_text_rejects_option_edge_matrix`，覆盖 compile args 空 pass 名、空 option 块、空 key/value、重复 key 与缺少 value 的公开拒绝边界。
- 未修改产品语义；本轮仅补测试锁定现有公开行为与 coverage 缺口。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py -ra --maxfail=1`
  - 结果：通过，`99 passed in 0.50s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_runner.py -ra --maxfail=1`
  - 结果：通过，`52 passed, 1 warning in 0.41s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage erase && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 coverage run --branch --source=kernel_gen -m pytest -q test -ra && PYTHONDONTWRITEBYTECODE=1 coverage json -o /tmp/core_print_alias_dump_cov_after_ircheck_edges.json && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 script/check_python_coverage.py --coverage-json /tmp/core_print_alias_dump_cov_after_ircheck_edges.json --include-module kernel_gen --line-min 95 --branch-min 80`
  - 结果：通过，pytest 阶段 `1988 passed, 1 warning in 333.98s`；coverage gate：`line=95.00% >= 95.00%`，`branch=87.93% >= 80.00%`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile $(find kernel_gen test -name '*.py' -not -path './.git/*')`
  - 结果：通过，退出码 `0`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test`
  - 结果：通过，`1988 tests collected in 1.54s`。
- `git diff --check && git diff --name-only -- expectation .skills`
  - 结果：通过；`expectation` / `.skills` 无 diff。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test -ra`
  - 结果：本次非 coverage 全量命令在 `900s` 超时，输出推进到约 `90%`；未给出失败用例。由于同一轮 coverage full pytest 已完整跑完 `1988 passed`，此项记录为非 coverage 全量命令超时风险，未作为通过项替代合同验收。
- 超时后按 collect 顺序补跑 90% 后段：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/target test/test_main_npu_demo_pipeline.py -ra --maxfail=1` -> 通过，`41 passed, 2 warnings in 3.40s`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py -ra --maxfail=1` -> 通过，`10 passed, 1 warning in 4.71s`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -ra --maxfail=1` -> 通过，`36 passed, 2 warnings in 6.50s`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_emitc_case_runner.py test/tools/test_ircheck_cli.py test/tools/test_ircheck_matcher.py test/tools/test_ircheck_parser.py test/tools/test_ircheck_runner.py test/tools/test_mlir_gen_compare.py test/tools/test_package.py -ra --maxfail=1` -> 通过，`119 passed, 1 warning in 0.74s`。

静态扫描：
- `rg -n "NnMemoryType\(.*(IntAttr|StringAttr)|ArrayAttr\(\[(IntAttr|StringAttr)" kernel_gen`
  - 结果：剩余命中均为合法例外：
    - `kernel_gen/dialect/dma.py` / `kernel_gen/dialect/nn.py` 的 transpose `perm` 构造与示例，属于非 memory layout 的 axis/perm 属性。
    - `kernel_gen/passes/tile/analysis.py`、`kernel_gen/passes/tile/elewise.py`、`kernel_gen/passes/tile/reduce.py` 的 tile metadata / roles / tile_exprs，属于非 memory layout metadata。
- `rg -n "shape\.data|stride\.data" kernel_gen/passes/memory_pool.py kernel_gen/passes/dma_memory_hierarchy.py kernel_gen/passes/decompass.py kernel_gen/passes/tile/analysis.py kernel_gen/passes/lowering/nn_lowering kernel_gen/dsl/ast/nodes/dma.py kernel_gen/dsl/ast/nodes/nn.py kernel_gen/dialect/nn.py kernel_gen/dialect/symbol.py`
  - 结果：`shape.data` / `stride.data` 使用面已按 `SymbolExprAttr` helper、rank/stride 比较或当前公开 verifier 处理；未发现继续把 memory layout 条目当旧裸 `IntAttr` / `StringAttr` 解析或构造的实现分支。
- `rg -n "NnMemoryType\(ArrayAttr\(\[.*(IntAttr|StringAttr)|shape=ArrayAttr\(\[.*(IntAttr|StringAttr)|stride=ArrayAttr\(\[.*(IntAttr|StringAttr)|_dim_array\(\[.*(IntAttr|StringAttr)|_make_(simple_memory_type|matrix_type|memory_type)\([^\n]*(IntAttr|StringAttr)|_normalize_dims|_normalize_memory_dims" kernel_gen test spec -g '*.py' -g '*.md'`
  - 结果：旧测试 helper / 旧 layout 构造已清理；剩余合法例外仍为非 layout 属性或负例 dtype。

合同验收：
- 工作区本身没有 `expectation/` 目录；按前序同步现场使用只读资产 `/tmp/core_print_alias_expectation_site2/expectation` 运行。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation`
  - 结果：失败，退出码 `1`，原因：本 worktree 不携带 expectation 包，`No module named expectation`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/tmp/core_print_alias_expectation_site2 python3 -m expectation`
  - 结果：失败，退出码 `1`，full expectation 当前失败 `26` 个 module：
    - `expectation.operation.arch.get_block_id`
    - `expectation.operation.arch.get_block_num`
    - `expectation.operation.arch.get_dynamic_memory`
    - `expectation.operation.arch.get_subthread_id`
    - `expectation.operation.arch.get_subthread_num`
    - `expectation.operation.arch.get_thread_id`
    - `expectation.operation.arch.get_thread_num`
    - `expectation.operation.arch.launch_kernel`
    - `expectation.pass.lowing.nn_lowering.element_binary.add`
    - `expectation.pass.lowing.nn_lowering.element_binary.div`
    - `expectation.pass.lowing.nn_lowering.element_binary.mul`
    - `expectation.pass.lowing.nn_lowering.element_binary.sub`
    - `expectation.pass.lowing.nn_lowering.element_binary.truediv`
    - `expectation.pass.lowing.nn_lowering.img2col.img2col1d`
    - `expectation.pass.lowing.nn_lowering.img2col.img2col2d`
    - `expectation.pass.lowing.nn_lowering.transpose`
    - `expectation.pass.memory_pool.dynamic`
    - `expectation.pass.pipeline.default_lowering`
    - `expectation.pass.tile.analysis.broadcast`
    - `expectation.pass.tile.elewise.element_compare`
    - `expectation.pass.tile.reduce.fc`
    - `expectation.pass.tuning.launch_kernel_cost_func.basic_all`
    - `expectation.pass.tuning.launch_kernel_cost_func.multi_kind`
    - `expectation.pass.tuning.launch_kernel_cost_func.shared_callee_once`
    - `expectation.tools.dsl_cost_run.invalid_contract`
    - `expectation.tools.dsl_run.invalid_contract`
- 单独复现：
  - `PYTHONFAULTHANDLER=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/tmp/core_print_alias_expectation_site2 python3 -m expectation.pass.tile.reduce.fc` -> 通过，退出码 `0`；full suite 中 `status -11` 暂按全量顺序/子进程风险记录，不能作为单测复现失败。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/tmp/core_print_alias_expectation_site2 python3 -m expectation.pass.tile.analysis.broadcast` -> 失败，文本匹配 `CHECK-NEXT not found`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/tmp/core_print_alias_expectation_site2 python3 -m expectation.pass.memory_pool.dynamic` -> 失败，文本匹配 `CHECK-NEXT not found`。
- 当前判断：
  - `operation.arch.*` 仍依赖旧私有 target registry 调用口径，不能通过恢复 `_get_current_target/_set_current_target` 私有入口修复。
  - `launch_kernel_cost_func.*` / `dsl_cost_run.invalid_contract` 仍包含旧 cost kind 或旧 pipeline 口径，不能通过回退当前公开七类 cost kind 或恢复旧 pipeline 修复。
  - `dsl_run.invalid_contract` 仍含旧入参合同冲突，不能通过回退当前公开 `dsl_run` 合同修复。
  - `nn_lowering` / `memory_pool` / `tile` / `pipeline` 失败主要表现为旧文本与当前 `SymbolExprAttr` canonical 输出、alias dump 或 pass 输出顺序不一致；需要按具体路径由架构/用户裁定是否极窄授权同步 expectation 合同，或另立实现专项，不得在本轮普通 execute 中修改 expectation 或回退当前公开 spec。

Diff 反推自测：
- 实际 diff 涉及 `test/dialect/test_symbol.py` 与 `test/tools/test_ircheck_runner.py` 的公开行为补测，因此反推测试选择：
  - `pytest -q test/dialect/test_symbol.py`
  - `pytest -q test/tools/test_ircheck_runner.py`
  - full coverage gate `coverage run --branch --source=kernel_gen -m pytest -q test`
  - `pytest --collect-only -q test`
  - py_compile、`git diff --check`、禁止修改面扫描。
- `expectation` 仅作为合同验收单列；未用 expectation 替代 diff 反推测试。

自检：
- 接口：本轮未新增、删除、重命名或修改公开 API；只补公开测试。
- 边界：未修改 `expectation/` 与 `.skills/`；未写主仓任务记录；未进入 review。
- 异常：full expectation 失败已列路径、命令、失败类型和当前判断；`tile.reduce.fc` full suite `-11` 已单独复现为通过，记录为顺序/子进程风险。
- 兼容：未恢复旧私有 target registry helper、旧 cost kind、旧 `NnMemoryType` bare `IntAttr/StringAttr` layout 或旧 `dsl_run` 合同。
- 实现遗漏：当前仍存在 full expectation 26 项失败；其中可否由 kernel_gen/spec/test 修复不能 blanket 推断，需按路径裁定，避免用旧合同回退当前公开 spec。
- 冗余：清理过时测试构造后，`NnMemoryType.shape/stride` 静态扫描未发现旧 layout 构造残留；合法例外已区分。
- 注释准确性：本轮只改测试，新增 case 注释写明每个 case 覆盖的公开行为。
- 复用/函数粒度：未新增跨文件 helper；测试沿用公开 `run_ircheck_text`、`SymbolExprAttr`。
- 输入输出校验：ircheck regex / compile args 异常路径已通过公开 runner 测试锁定。
- 资源/并发/性能：coverage full pytest 可在约 334s 完成；非 coverage full pytest 本次 900s 超时，后段目标/工具文件拆跑均通过，仍作为风险记录。
- 测试有效性：新增测试能在 regex/compile args 解析边界或 symbol canonical 规则回退时失败。

结论：阻塞 / 继续 execute。coverage 95/80 已达成，py_compile、collect-only、diff check、禁止修改面与相关公开 pytest 均通过；但 full expectation 仍失败 26 项，且普通 execute 不得修改 expectation 或回退当前公开合同，因此当前仍不能 `-next review`。需要管理员/架构师按失败矩阵裁定是否对具体 expectation 路径做极窄授权、拆合同资产同步任务，或调整 full expectation 门禁归属。

---

时间：2026-05-07 10:56 +0800
经办人：守护最好的爱莉希雅
类型：架构裁定 / full expectation 失败矩阵下一步

裁定结论：
- 当前仍不得进入 `review`；任务保持 `execute` 阻塞态。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation` 仍是本计划硬门禁；在用户未更新计划完成态前，不允许调整 full expectation 门禁归属，也不允许带已知失败进入 review。
- coverage `95/80` 已按记录解除阻塞；后续 review / 终验仍需复跑或核对同等命令结果，但当前最小阻断项集中在 full expectation。

必须继续由 `kernel_gen/spec/test` 收口的失败：
- `expectation.pass.lowing.nn_lowering.element_binary.{add,div,mul,sub,truediv}`：必须先记录每个 case 的 actual IR、expected 片段、对应 spec 条款和 verdict。若 actual IR 违反当前 `SymbolExprAttr` / nn lowering 合同，继续修实现；只有 actual IR 已符合 spec 且 expectation 仍锁旧文本时，才可转入极窄 expectation 授权。
- `expectation.pass.lowing.nn_lowering.transpose`：同上，先比对 actual IR 的 `symbol.get_dim` 顺序、rank 和 lower 结果；不得直接归为旧 expectation。
- `expectation.pass.memory_pool.dynamic`：优先按 memory pool 当前 spec 对照 `arch.get_dynamic_memory + dma.subview + dma.reshape`、offset 顺序、space / func 唯一 backing 与 dynamic shape 行为。若 actual 不符合 spec，继续修实现。
- `expectation.pass.pipeline.default_lowering`：先对照 default lowering pipeline 当前公开顺序和输出 ABI；若 pipeline 输出或 pass 串接不符合 spec，继续修实现。
- `expectation.pass.tile.analysis.broadcast`：先对照 tile-analysis 对 `tile.analysis` / `tile.tile_exprs` 的补全行为；若 actual 缺失 tile expr、broadcast 维处理或别名输出不符合 spec，继续修实现。
- `expectation.pass.tile.elewise.element_compare`：先对照 `symbol.for + dma.view` 的 operand、offset、size、stride 和 result layout；若 actual 违反 tile-elewise spec，继续修实现。
- `expectation.pass.tile.reduce.fc`：单独复现通过、full suite 中出现 `-11`，当前不能归为 expectation 文本冲突；execute 需要记录是否为 full expectation 顺序 / 子进程 / 全局状态问题，并给出稳定复现或确认后续修复。若是实现引入的全局状态污染，继续修实现。

需要用户或架构师极窄授权处理合同资产，且不得由普通 execute/review/merge 直接修改的失败：
- `expectation.operation.arch.*`：旧 case 直连 `kernel_gen.target.registry._get_current_target/_set_current_target` 私有入口，违反当前公开 API 边界。不得恢复下划线私有入口；若当前 `get_current_target/set_current_target` 是真源，需要极窄同步 `expectation/operation/arch/**`。
- `expectation.pass.tuning.launch_kernel_cost_func.{basic_all,multi_kind,shared_callee_once}`：旧 `compute/memory/latency` kind 与当前七值 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 公开合同冲突。不得回退实现到旧三值；需要极窄同步对应 expectation。
- `expectation.tools.dsl_cost_run.invalid_contract`：旧 `DMA/MAC`、旧 `cse` pipeline 和旧失败文本与当前 `dsl_cost_run` 七值 kind / pipeline 合同冲突。不得恢复旧 pass 名或旧 kind；需要极窄同步该 expectation。
- `expectation.tools.dsl_run.invalid_contract`：旧 real_args / helper 注入口径与当前 `dsl_run` 支持 runtime scalar 且不隐式注入 helper 的公开合同冲突。不得回退当前公开合同；需要极窄同步该 expectation。
- `expectation.pass.lowing.nn_lowering.img2col.{img2col1d,img2col2d}`：若当前 spec 确认以 `//` / `SymbolExprAttr` canonical floordiv 文本为真源，则旧 `floordiv` 文本属于合同资产旧口径；不得为 expectation 回退实现。该项可列入极窄同步，但同步前需在记录中附 actual IR 与 spec 引用。

禁止事项：
- 不得恢复任何跨文件私有 API 入口来满足 expectation。
- 不得回退公开 cost kind、`dsl_run` 入参合同、SymbolExprAttr canonical 文本或 NnMemoryType shape/stride 结构化实现来满足旧文本。
- 不得把其它 `expectation/**` 的修改混入本计划普通 execute diff；如需处理，必须有用户或架构师对具体路径、case 和目标文本的极窄授权记录。

最小继续路径：
1. 任务继续停在 `execute`，不 `-next review`。
2. execute 先补一张“actual IR / expected / spec / verdict”矩阵，覆盖所有待判定的 `nn_lowering`、`memory_pool`、`pipeline`、`tile` 与 `tile.reduce.fc` full suite 顺序风险。
3. 对 verdict 为“actual 违反 spec”的项，继续修 `kernel_gen/spec/test`，不得动 expectation。
4. 对 verdict 为“actual 符合 spec，expectation 锁旧文本/旧入口”的项，由管理员汇总为极窄 expectation 合同同步请求；该请求只能覆盖列明路径和 case，不得 blanket 授权。
5. 完成实现修复与已授权合同资产同步后，复跑 `python3 -m expectation`、full pytest / coverage 95/80、py_compile、`git diff --check`、`expectation/.skills` diff 和静态边界扫描；全部通过后才允许进入 review。

合同同步落点补充：
- 已确认极窄 `expectation` 合同同步不得在当前 execute worktree 中由普通 execute 写入。
- 架构侧已建立独立 worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`。
- 独立记录文件：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-expectation-contract-sync.md`。
- 该 worktree 只承载已裁定路径的合同同步，不授权扩散到其它 `expectation/**`，也不改变本任务 full expectation 硬门禁。

## 架构裁定 - 2026-05-07 10:55 +0800 - 大闸蟹

结论：不调整 full expectation 门禁；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation` 仍是本计划硬门槛。当前不得 `-next review`，必须继续 execute，直到 full expectation、full pytest/等价全量 pytest 证据、coverage 95/80、禁止修改面和静态扫描全部闭合。

### 允许按极窄合同同步处理的 expectation 路径

以下路径已足够归因为旧合同资产与当前公开 spec 冲突，不应通过恢复私有 API、回退旧 cost kind、回退旧 `dsl_run` 合同或恢复旧 pipeline 名称修实现。授权范围仅限让这些 expectation 与当前公开 spec / API / 稳定错误语义对齐；不得顺手改其它 expectation、runner 或断言框架：

1. `expectation/operation/arch/get_block_id.py`
2. `expectation/operation/arch/get_block_num.py`
3. `expectation/operation/arch/get_dynamic_memory.py`
4. `expectation/operation/arch/get_subthread_id.py`
5. `expectation/operation/arch/get_subthread_num.py`
6. `expectation/operation/arch/get_thread_id.py`
7. `expectation/operation/arch/get_thread_num.py`
8. `expectation/operation/arch/launch_kernel.py`
9. `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`
10. `expectation/pass/tuning/launch_kernel_cost_func/multi_kind.py`
11. `expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`
12. `expectation/tools/dsl_cost_run/invalid_contract.py`
13. `expectation/tools/dsl_run/invalid_contract.py`
14. `expectation/pass/lowing/nn_lowering/img2col/img2col1d.py`
15. `expectation/pass/lowing/nn_lowering/img2col/img2col2d.py`

边界说明：
- `operation.arch.*` 只能改为使用公开 target registry / target API；不得恢复 `_get_current_target` / `_set_current_target` 这类私有入口。
- `launch_kernel_cost_func.*` 与 `dsl_cost_run.invalid_contract` 只能对齐当前七值 kind：`DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2`，不得兼容旧 `compute/memory/latency`、旧 `DMA/MAC` 入口值或旧 `cse` pass 名。
- `dsl_run.invalid_contract` 只能对齐当前 `real_args` 支持 `torch.Tensor | numpy.ndarray | int | float` 与显式 import/闭包/全局绑定规则；不得恢复隐式 helper 注入。
- `img2col1d/2d` 只能对齐当前 `SymbolExprAttr` canonical 文本与 `//` 口径；不得回退实现到旧 `floordiv` 文本。

### 必须继续按实现/spec/test 收口的路径

以下路径尚未证明是 expectation 合同冲突，不能授权改 expectation。execute 必须先输出 actual IR / actual stderr，与当前 spec 逐条比对；若 actual 违反 spec，修 `kernel_gen/spec/test`；若 actual 已符合 spec，再回架构/用户请求极窄 expectation 授权。

1. `expectation/pass/lowing/nn_lowering/element_binary/add.py`
2. `expectation/pass/lowing/nn_lowering/element_binary/div.py`
3. `expectation/pass/lowing/nn_lowering/element_binary/mul.py`
4. `expectation/pass/lowing/nn_lowering/element_binary/sub.py`
5. `expectation/pass/lowing/nn_lowering/element_binary/truediv.py`
6. `expectation/pass/lowing/nn_lowering/transpose.py`
7. `expectation/pass/memory_pool/dynamic.py`
8. `expectation/pass/pipeline/default_lowering.py`
9. `expectation/pass/tile/analysis/broadcast.py`
10. `expectation/pass/tile/elewise/element_compare.py`

`expectation/pass/tile/reduce/fc.py` 单独复现已通过，但 full suite 中曾出现 `status -11`；该项暂按 full expectation 顺序 / 子进程稳定性问题继续记录和复跑，不授权改 expectation。

### 继续路径

1. 小李飞刀继续保持 execute，不 `-next review`。
2. 先按“必须继续实现侧收口”的 10 个路径产出 actual IR / spec 对照记录并修实现侧真实缺口。
3. 对上方 15 个“允许极窄合同同步”的 expectation 路径，若执行人具备用户/架构授权上下文，可在当前任务内只改这些文件；若当前 worktree 不携带 expectation 资产或脚本流程不允许普通 execute 写入 expectation，则由神秘人协调建立单独 expectation 合同同步 worktree，但不得调整 full expectation 门禁归属。
4. 任何新增 expectation 路径、公开 API 变化、降低/拆除 full expectation gate、降低 coverage 95/80 或跳测/xfail/omit，都必须重新回用户确认。

## 架构侧 expectation 同步落点 - 2026-05-07 11:05 +0800 - 大闸蟹

已创建独立架构同步 worktree：

- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- 记录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-expectation-sync.md`
- 基线：`origin/main@673349f53bc3f29e804ff47c2784c57b12aa9d54`

裁定：

1. 该 worktree 是架构侧极窄 `expectation` 合同同步落点，不是普通 execute/review/merge/admin 改动面。
2. 普通 execute 不得在 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` 写 `expectation/`；小李飞刀继续只处理实现/spec/test 与尚未裁定的 actual IR / spec 对照项。
3. 合同同步验证使用组合路径：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync python3 -m expectation`。
4. 同步范围仍仅限上一节列出的 15 个授权 expectation 路径；不得扩散到其它 `expectation/**`，不得降低 full expectation 门禁。

## expectation 同步落点统一 - 2026-05-07 11:12 +0800 - 大闸蟹

因现场同时存在两个 expectation 同步 worktree，已统一唯一有效落点：

- 唯一有效 worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`
- branch：`task/core-print-expectation-contract-sync`
- 记录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-expectation-contract-sync.md`

大闸蟹此前建立的 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync` 判定为重复落点，不得作为通过依据，不得继续写 `expectation`，不分发、不合并、不引用。

固定 full expectation 组合验证命令改为：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync \
python3 -m expectation
```

授权范围以唯一有效 worktree 的记录为准：operation/arch 8 个、launch_kernel_cost_func 3 个、`tools.dsl_cost_run.invalid_contract`、`tools.dsl_run.invalid_contract` 可直接同步；`img2col1d/2d` 仅在 actual 已被 execute 记录证明符合当前 `//` / `SymbolExprAttr` canonical spec 后同步；其它 expectation 仍禁止修改。

## expectation 合同同步最终口径 - 2026-05-07 11:18 +0800

双架构最终统一为以下唯一有效落点：

- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`
- branch：`task/core-print-expectation-contract-sync`
- 记录文件：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-expectation-contract-sync.md`

重复 / 无效落点：
- `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- branch：`arch/core-print-alias-expectation-sync`
- 该 worktree 不得作为通过依据，不得继续写 `expectation`，不分发、不合并、不引用。

固定 full expectation 验证入口：
```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync \
python3 -m expectation
```

授权范围以唯一有效 worktree 的记录为准：`operation.arch.*`、`launch_kernel_cost_func.*`、`tools.dsl_cost_run.invalid_contract`、`tools.dsl_run.invalid_contract` 可直接同步；`img2col1d.py` / `img2col2d.py` 仅在原 execute 记录证明 actual 已符合当前 `//` / `SymbolExprAttr` canonical spec 后同步；其它 `expectation/**` 仍禁止修改。

## 最终唯一落点确认 - 2026-05-07 11:11 +0800 - 大闸蟹

本段覆盖本记录中所有较早的 expectation 同步落点段落。

T-20260507-bfc9a0e0 唯一有效 expectation 合同同步落点为：

- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- branch：`arch/core-print-alias-expectation-sync`
- 记录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-expectation-sync.md`

重复 / 误建非活动链路：

- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`
- branch：`task/core-print-expectation-contract-sync`
- 状态：不得作为通过依据，不得继续写 `expectation`，不分发、不合并、不引用。

固定验证入口：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync \
python3 -m expectation
```

授权范围保持此前裁定：operation/arch 8 个、launch_kernel_cost_func 3 个、`expectation/tools/dsl_cost_run/invalid_contract.py`、`expectation/tools/dsl_run/invalid_contract.py` 可直接同步；`expectation/pass/lowing/nn_lowering/img2col/img2col1d.py` 和 `expectation/pass/lowing/nn_lowering/img2col/img2col2d.py` 仅在 execute 记录证明 actual 已符合当前 `//` / `SymbolExprAttr` canonical spec 后同步。其它 `expectation/**` 禁止修改。

## expectation 同步落点冻结最终口径 - 2026-05-07 11:16 +0800 - 守护最好的爱莉希雅

本段覆盖此前所有互相冲突的同步落点段落与口头回复。

唯一有效 expectation 合同同步落点：
- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- branch：`arch/core-print-alias-expectation-sync`
- 记录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-expectation-sync.md`

重复 / 非活动链路：
- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`
- branch：`task/core-print-expectation-contract-sync`
- 状态：不得作为通过依据，不得继续写 `expectation`，不分发、不合并、不引用。

固定验证入口：
```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync \
python3 -m expectation
```

授权范围保持此前裁定：`operation.arch.*`、`launch_kernel_cost_func.*`、`expectation/tools/dsl_cost_run/invalid_contract.py`、`expectation/tools/dsl_run/invalid_contract.py` 可直接同步；`img2col1d.py` 和 `img2col2d.py` 仅在 execute 记录证明 actual 已符合当前 `//` / `SymbolExprAttr` canonical spec 后同步。其它 `expectation/**` 禁止修改。

---

时间：2026-05-07 12:46 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / TODO 再次复查

触发来源：
- 榕要求再次查看 `TODO.md` 并继续任务。
- 神秘人随后确认：`T-20260507-bfc9a0e0` 仍由小李飞刀 `execute / 进行中`，任务列表无新任务。

复查结果：
- `TODO.md` 当前仍只有 `T-20260507-bfc9a0e0` 处于 `execute / 进行中`。
- 当前没有新的可执行任务条目。
- 当前没有解除 expectation sync 冻结的裁定。

当前执行口径：
- 继续保持 expectation sync 冻结。
- 不引用 `alias-sync` 或 `contract-sync` 任一 worktree 作为通过依据。
- 不写 `expectation/`。
- 不执行 `-next review`。
- 等榕裁定唯一有效 full expectation 验证路径后，再按裁定复跑并记录。

禁止修改面复核：
- 命令：`git diff --name-only -- expectation .skills`
- 结果：无输出。

结论：
- 当前任务继续 execute / 阻塞。
- 本次无新增产品代码 diff；不运行 full expectation，不流转 review。

---

时间：2026-05-07 11:30 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / TODO 复查与阻塞状态确认

触发来源：
- 榕要求再次查看 `TODO.md`，继续当前任务，完成后 `-next` 并回报管理员；如发现阻塞 / 疑问，使用脚本回报管理 / 架构师。

复查结果：
- 已重新读取个人提示词 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`。
- 已重新读取主仓 `TODO.md`。
- `TODO.md` 当前仍只有 `T-20260507-bfc9a0e0` 处于 `execute / 进行中`，worktree 为 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`，记录文件为 `agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-dump.md`。
- 当前任务描述仍要求跑通 full expectation、pytest、coverage 95/80，并记录禁止修改面与 Diff 反推自测。

当前状态判定：
- 根据神秘人最新同步，`T-20260507-bfc9a0e0` 继续保持 execute 阻塞，expectation sync 冻结。
- 裁定前不得引用 `alias-sync` 或 `contract-sync` 任一 worktree 作为通过依据。
- 裁定前不得写 `expectation/`，不得 `-next review`。
- 当前只能保留并继续维护实现 / spec / test 侧证据。

已完成的实现 / spec / test 侧证据摘要：
- `default-lowering` 与当前 spec 不一致的实现缺口已修复：`build_default_lowering_pipeline()` 显式使用 `LowerDmaMemoryHierarchyPass(fold=False)`，恢复公开黑盒 `dma.slice / dma.deslice` staging 链。
- 已补 `test/passes/pipeline/test_default_lowering.py::test_default_lowering_pipeline_add_uses_legacy_dma_hierarchy`，只走公开 API 验证 out-param ABI、`dma.slice`、`dma.deslice` 与 `kernel.binary_elewise(kind="add", space=local)`。
- 已记录 element_binary、transpose、memory_pool.dynamic、tile.analysis.broadcast、tile.elewise.element_compare、tile.reduce.fc 的 actual IR / expected / spec / verdict 矩阵。
- 已记录 `NnMemoryType.shape/stride` 旧 `IntAttr/StringAttr` layout 分支扫描范围、合法例外与剩余结果。

验证基线：
- `pytest -q test/passes/pipeline/test_default_lowering.py -ra` -> `3 passed, 1 warning`。
- `py_compile kernel_gen/passes/pipeline/default_lowering.py test/passes/pipeline/test_default_lowering.py` + 相关 pipeline / dma hierarchy / pass manager pytest -> `18 passed, 14 deselected, 1 warning`。
- `pytest --collect-only -q test` -> `1989 tests collected`。
- full coverage gate -> `1989 passed, 1 warning`，coverage `line=95.00%`，`branch=87.93%`。
- `git diff --check` -> 通过。
- `git diff --name-only -- expectation .skills` -> 无输出。

Diff 反推自测：
- 本次 TODO 复查没有新增产品代码 diff；反推测试沿用上方最近一次实现侧修复对应 pytest / py_compile / collect-only / coverage / diff-check 基线。
- 未运行 full expectation，因为最新流程明确要求等待榕裁定唯一有效 full expectation 验证路径，且不得引用任一 sync worktree 作为通过依据。

自检：
- 接口：未新增、删除、重命名或修改公开 API。
- 边界：未写 `expectation/`，未写 `.skills/`，未引用任一 sync worktree 作为通过依据。
- 异常：当前阻塞原因是 full expectation 验证路径未裁定，非新增实现缺口。
- 测试有效性：实现侧已保留可复现 pytest / coverage / diff-check 证据；expectation 未被计入 Diff 反推测试。

结论：
- 继续 execute / 阻塞。
- 不执行 `-next review`。
- 已按要求准备向管理员 / 榕回报：当前等待榕裁定唯一有效 full expectation 验证路径；收到裁定后再复跑并记录。

## expectation 同步落点最终不可再覆盖口径 - 2026-05-07 11:24 +0800 - 守护最好的爱莉希雅

本段覆盖此前所有互相冲突的同步落点段落与口头回复；后续不再切换。

接受大闸蟹最新口径：`T-20260507-bfc9a0e0` 唯一有效 expectation 合同同步落点固定为：

- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`
- branch：`task/core-print-expectation-contract-sync`
- 记录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-expectation-contract-sync.md`

重复 / 非活动链路：
- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- branch：`arch/core-print-alias-expectation-sync`
- 状态：不得作为通过依据，不得继续写 `expectation`，不分发、不合并、不引用。

固定验证入口：
```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync \
python3 -m expectation
```

授权范围以 contract-sync 记录为准：`operation.arch.*`、`launch_kernel_cost_func.*`、`expectation/tools/dsl_cost_run/invalid_contract.py`、`expectation/tools/dsl_run.invalid_contract.py` 可直接同步；`img2col1d.py` 和 `img2col2d.py` 仅在 execute 记录证明 actual 已符合当前 `//` / `SymbolExprAttr` canonical spec 后同步。其它 `expectation/**` 禁止修改。

## 最终覆盖裁定 - 2026-05-07 - 大闸蟹

本段覆盖本记录中所有较早、相互冲突的 expectation 同步落点段落。为与守护最好的爱莉希雅最新最终口径保持一致，T-20260507-bfc9a0e0 唯一有效 expectation 合同同步落点最终固定为：

- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`
- branch：`task/core-print-expectation-contract-sync`
- 记录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-expectation-contract-sync.md`

重复 / 误建非活动链路：

- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- branch：`arch/core-print-alias-expectation-sync`
- 状态：不得作为通过依据，不得继续写 `expectation`，不分发、不合并、不引用。

固定验证入口：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync \
python3 -m expectation
```

授权范围保持此前裁定：operation/arch 8 个、launch_kernel_cost_func 3 个、`expectation/tools/dsl_cost_run/invalid_contract.py`、`expectation/tools/dsl_run/invalid_contract.py` 可直接同步；`expectation/pass/lowing/nn_lowering/img2col/img2col1d.py` 和 `expectation/pass/lowing/nn_lowering/img2col/img2col2d.py` 仅在 execute 记录证明 actual 已符合当前 `//` / `SymbolExprAttr` canonical spec 后同步。其它 `expectation/**` 禁止修改。

## 双架构最终一致口径 - 2026-05-07 11:20 +0800 - 大闸蟹

本段覆盖本记录此前所有互相冲突的同步落点段落。大闸蟹接受守护最好的爱莉希雅撤回 contract-sync 后的最终口径。

唯一有效 expectation 合同同步落点：
- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- branch：`arch/core-print-alias-expectation-sync`
- 记录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-expectation-sync.md`

重复 / 非活动链路：
- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`
- branch：`task/core-print-expectation-contract-sync`
- 状态：不得作为通过依据，不得继续写 `expectation`，不分发、不合并、不引用。

固定验证入口：
```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync \
python3 -m expectation
```

授权范围保持此前裁定：`operation.arch.*`、`launch_kernel_cost_func.*`、`expectation/tools/dsl_cost_run/invalid_contract.py`、`expectation/tools/dsl_run/invalid_contract.py` 可直接同步；`img2col1d.py` 和 `img2col2d.py` 仅在 execute 记录证明 actual 已符合当前 `//` / `SymbolExprAttr` canonical spec 后同步。其它 `expectation/**` 禁止修改。

## 双架构最终冻结口径 - 2026-05-07 11:30 +0800 - 大闸蟹

本段覆盖本记录此前所有互相冲突的同步落点段落。大闸蟹接受守护最好的爱莉希雅最新确认的最终口径，后续不再切换。

唯一有效 expectation 合同同步落点：
- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`
- branch：`task/core-print-expectation-contract-sync`
- 记录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync/agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-expectation-contract-sync.md`

重复 / 非活动链路：
- worktree：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`
- branch：`arch/core-print-alias-expectation-sync`
- 状态：不得作为通过依据，不得继续写 `expectation`，不分发、不合并、不引用。

固定验证入口：
```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync \
python3 -m expectation
```

授权范围保持此前裁定：`operation.arch.*`、`launch_kernel_cost_func.*`、`expectation/tools/dsl_cost_run/invalid_contract.py`、`expectation/tools/dsl_run/invalid_contract.py` 可直接同步；`img2col1d.py` 和 `img2col2d.py` 仅在 execute 记录证明 actual 已符合当前 `//` / `SymbolExprAttr` canonical spec 后同步。其它 `expectation/**` 禁止修改。

---

时间：2026-05-07 13:48 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / TODO 再次复查与阻塞回报

触发来源：
- 榕再次要求查看 `TODO.md`，继续任务，完成后 `-next` 并回报管理员；若有阻塞 / 疑问，继续用脚本回报管理 / 架构师并要求回复。

复查结果：
- `TODO.md` 当前仍只有 `T-20260507-bfc9a0e0` 处于 `execute / 进行中`。
- 任务列表为空，无新任务。
- 任务仍要求跑通 full expectation、full pytest、kernel_gen coverage 95/80，并记录禁止修改面与 Diff 反推自测。
- 当前神秘人最后同步口径仍是 expectation sync 冻结：不引用 `alias-sync` 或 `contract-sync` 任一 worktree作为通过依据，不写 `expectation/`，不 `-next review`，等待榕裁定唯一有效 full expectation 验证路径。

本次执行：
- 未修改产品代码。
- 未运行 full expectation，因为当前明确等待榕裁定唯一验证路径。
- 未执行 `-next review`，避免把未完成的 hard gate 带入审查。

禁止修改面：
- 命令：`git diff --name-only -- expectation .skills`
- 结果：无输出。

自检：
- 接口：本次未新增、删除、重命名或修改公开 API。
- 边界：未写 `expectation/`，未写 `.skills/`，未引用任一 sync worktree 作为通过依据。
- 测试有效性：本次无新产品 diff；沿用前序记录中的实现侧 pytest / coverage / diff-check 证据。
- 阻塞：full expectation 验证路径未由榕裁定，当前无法完成计划硬门禁。

结论：
- 继续 execute / 阻塞。
- 不 `-next review`。
- 已准备再次用脚本回报神秘人，并请求等待 / 推进榕裁定唯一 full expectation 验证路径。

---

时间：2026-05-07 14:51 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / TODO 再次复查与阻塞重复回报

触发来源：
- 榕再次要求查看 `TODO.md`，继续任务，完成后 `-next` 并回报管理员；如有阻塞 / 疑问，重复用脚本询问直到回复。

复查结果：
- `TODO.md` 当前仍只有 `T-20260507-bfc9a0e0` 处于 `execute / 进行中`。
- 任务列表为空，无新任务。
- 任务仍要求 full expectation / full pytest / coverage 95/80 全部闭合后才能流转。
- 最新有效执行口径仍是 expectation sync 冻结：不引用 `alias-sync` 或 `contract-sync` 任一 worktree 作为通过依据，不写 `expectation/`，不 `-next review`，等待榕裁定唯一有效 full expectation 验证路径。

本次执行：
- 未修改产品代码。
- 未运行 full expectation，因为当前没有唯一有效验证路径裁定。
- 未执行 `-next review`，因为 full expectation hard gate 未闭合且已有明确冻结口径。

禁止修改面：
- 命令：`git diff --name-only -- expectation .skills`
- 结果：无输出。

阻塞项：
- 唯一 full expectation 验证路径未由榕裁定。
- `alias-sync` / `contract-sync` 均不得作为通过依据。
- 普通 execute 不能写 `expectation/` 自行修复合同资产。

自检：
- 接口：本次无公开 API 改动。
- 边界：未写 `expectation/`，未写 `.skills/`，未引用任一 sync worktree。
- 测试有效性：本次无新产品 diff；实现侧测试证据沿用前序记录的 pytest / coverage / diff-check 基线。

结论：
- 继续 execute / 阻塞。
- 不 `-next review`。
- 按榕要求继续用脚本回报管理员，并直接询问榕裁定唯一 full expectation 验证路径。

---

时间：2026-05-07 15:55 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / TODO 再次复查与阻塞确认

触发来源：
- 榕再次要求查看 `TODO.md`，继续任务，完成后 `-next` 并回报管理员；如有阻塞 / 疑问，重复用脚本询问直到回复。
- 神秘人同步确认：任务列表为空，小李飞刀当前仍是 `T-20260507-bfc9a0e0` 的 execute 执行人。

复查结果：
- `TODO.md` 当前仍只有 `T-20260507-bfc9a0e0` 处于 `execute / 进行中`。
- 任务列表为空，无新任务可分发。
- 当前无榕关于唯一 full expectation 验证路径的裁定。

当前冻结口径：
- 不引用 `alias-sync` 或 `contract-sync` 任一 worktree 作为通过依据。
- 不写 `expectation/`。
- 不执行 `-next review`。
- 等榕裁定唯一 full expectation 验证路径后再恢复复跑并记录。

禁止修改面：
- 命令：`git diff --name-only -- expectation .skills`
- 结果：无输出。

本次执行：
- 未修改产品代码。
- 未运行 full expectation。
- 未流转 review。

结论：
- 继续 execute / 阻塞。
- 已继续按要求用脚本回报管理员，并再次催榕裁定唯一 full expectation 验证路径。

---

时间：2026-05-07 16:57 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / TODO 再次复查与阻塞重复催办

触发来源：
- 榕再次要求查看 `TODO.md`，继续任务，完成后 `-next` 并回报管理员；如有阻塞 / 疑问，重复用脚本询问直到回复。

复查结果：
- `TODO.md` 当前仍只有 `T-20260507-bfc9a0e0` 处于 `execute / 进行中`。
- 任务列表为空，无新任务。
- 需要用户确认事项为空。
- 当前仍无榕关于唯一 full expectation 验证路径的裁定。

当前冻结口径：
- 不引用 `alias-sync` 或 `contract-sync` 任一 worktree 作为通过依据。
- 不写 `expectation/`。
- 不执行 `-next review`。
- 等榕裁定唯一 full expectation 验证路径后再恢复复跑并记录。

禁止修改面：
- 命令：`git diff --name-only -- expectation .skills`
- 结果：无输出。

本次执行：
- 未修改产品代码。
- 未运行 full expectation。
- 未流转 review。

结论：
- 继续 execute / 阻塞。
- 继续按要求用脚本回报管理员，并再次直接催榕裁定唯一 full expectation 验证路径。

---

时间：2026-05-07 18:28 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / 最新阻塞状态补记

最新口径：
- 神秘人已明确：新的 full expectation 固定命令依赖 `expectation/utils/suite_runner.py` 极窄变更；按 `AGENTS.md` expectation 权限，execute 不直接修改 `expectation`。
- runner 变更已转大闸蟹和守护按用户授权处理；execute 当前等待架构侧确认 runner 已按授权落位。
- `alias-sync` 是唯一有效合同同步落点；`contract-sync` 作废。

本次复核：
- 命令：`git diff -- expectation/utils/suite_runner.py`
- 执行目录：`/home/lfr/kernelcode_generate`
- 结果：无输出；当前无 execute 保留的 `suite_runner.py` diff。

待复跑命令：
```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

自检与 Diff 反推自测：
- 本次无产品代码 diff，无新增 pytest / 脚本测试。
- 未写 `expectation/`，未写 `.skills/`。
- full expectation 属于合同验收资产；在架构确认 runner 落位前不复跑、不作为通过依据。

结论：
- 继续 execute / 阻塞。
- 不 `-next review`。
- 等架构侧确认 `suite_runner` 落位后，再按固定命令复跑 full expectation 并补记结果。

---

时间：2026-05-07 18:53 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / 最新 execute 阻塞补记
任务目标：补齐 runner 落位后的 full expectation 复跑结果、Diff 反推自测与剩余 actual/spec 矩阵，并保持任务不进入 review。

改动：
- 已在本记录 `2026-05-07 18:49 +0800` 段落写入完整 actual / expected / spec / verdict 矩阵。
- 本轮唯一新增修改为 `spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`：将 img2col 动态 extent 从旧 `SymbolDim` / `//` 文本口径收成 `SymbolExprAttr` + `symbol.floordiv` 当前公开口径。
- 未修改 `expectation/**` 或 `.skills/**`。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering/test_img2col1d.py test/passes/lowering/nn_lowering/test_img2col2d.py test/dialect/test_symbol.py -ra` -> 通过，`106 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/core/contracts.py kernel_gen/passes/tile/elewise.py kernel_gen/dialect/kernel.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py` -> 通过。
- `git diff --check` -> 通过，无输出。
- `git diff --name-only -- expectation .skills` -> 无输出。
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation` -> 失败，退出码 `1`，日志 `/tmp/core_print_alias_full_expectation_after_img2col_spec_20260507.log`，剩余 `24 cases`。

Diff 反推自测：
- 本轮 spec diff 反推运行 img2col lowering pytest 与 symbol dialect pytest，覆盖 `SymbolExprAttr` / `symbol.floordiv` 口径。
- 前序同轮已记录 tile / memory_pool / nn_lowering / kernel 相关公开 pytest：`143 passed, 1 warning`。
- `expectation` 只作为合同验收资产单列，不计入 Diff 反推测试。

自检：
- 接口：未新增、删除、重命名或修改公开 API。
- 边界：未写 `expectation/`、未写 `.skills/`、未恢复旧私有 target registry、旧 cost kind、旧 dsl_run helper 注入或旧 `IntAttr/StringAttr` memory layout 兼容。
- 实现缺口：本轮对照后未发现剩余 actual 违反当前 spec 的实现侧可修项；剩余失败按 18:49 矩阵分类为旧合同冲突或需 expectation 文本同步。
- 测试有效性：公开 pytest 能锁定本轮 spec 修正；full expectation 仍失败，不能进入 review。

结论：
- 继续 `execute / 阻塞`。
- 不执行 `-next review`。
- 等架构 / 用户对剩余旧合同资产给出极窄同步或其它裁定；execute 不写 expectation。

---

时间：2026-05-07 18:49 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / runner 落位后剩余矩阵继续收口
任务目标：按最新 execute 口径继续处理 full expectation 剩余矩阵；不写 `expectation/`；实现侧 actual 违反当前 spec 时修 `kernel_gen/spec/test`，actual 符合当前 spec 时记录为只读合同同步项。

执行前阅读记录：
- 已重新读取个人提示词、根目录 `AGENTS.md` 和 `agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
- 已读取本任务记录最新裁定：`expectation/utils/suite_runner.py` 已由架构侧按榕授权极窄修正；execute 不写 `expectation/`；full expectation 仍是 hard gate；当前不得 `-next review`。
- 已复核禁止修改面：`git diff --name-only -- expectation .skills` 无输出。

改动：
- 修改 `spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`，将 `img2col1d/img2col2d` 动态输出 extent 从旧 `SymbolDim` / 原始 `//` 文本口径收成当前 `SymbolExprAttr` 结构化表达与 `symbol.floordiv` 公开文本口径。
- 未修改 `kernel_gen/**` 产品实现。
- 未修改、移动、新建或删除任何 `expectation/**` 或 `.skills/**` 文件。

实现侧 actual / expected / spec / verdict 矩阵：

| 分组 | actual 摘要 | expectation expected 摘要 | 当前 spec / pytest 依据 | verdict |
| --- | --- | --- | --- | --- |
| `operation.arch.*` 8 项 | expectation 仍直连旧 `target_registry._get_current_target/_set_current_target` 私有入口。 | 旧私有 target registry 合同。 | 既有架构裁定：不得恢复私有 target registry，不得新增未确认公开 target API。 | 旧合同冲突，等待架构极窄同步；execute 不修实现。 |
| `launch_kernel_cost_func.*` 3 项 | 当前公开 `cost_kind` 只接受 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2`。 | 旧 `compute/memory/latency` cost kind。 | 当前 tuning spec/test 已锁定新 cost kind；不得回退旧公开错误语义。 | 旧合同冲突，等待架构极窄同步。 |
| `tools.dsl_cost_run.invalid_contract` | 当前按公开 `dsl_cost_run` / launch-kernel cost kind 合同拒绝旧参数组合。 | 旧 `DMA/MAC/cse` invalid_contract 文本与行为。 | 既有裁定：不得恢复旧 cost kind 或旧 cse pass 口径。 | 旧合同冲突，等待架构极窄同步。 |
| `tools.dsl_run.invalid_contract` case 6 | actual 为 `Unsupported call expression`，其它 invalid contract case 按当前公开错误通过。 | 旧 real_args/helper 注入口径。 | 既有裁定：不得恢复旧 dsl_run helper 注入或旧私有路径。 | 旧合同冲突，等待架构极窄同步。 |
| `nn_lowering.element_binary.{add,div,mul,sub,truediv}` | actual 生成 `symbol.add %const1, %rhs`，result type canonical 为 `S + 1` / `QJB + 1` 等。 | 期望 result type 文本为 `1 + S` / `1 + QJB` 等旧顺序。 | `spec/dialect/symbol.md` 以 `SymbolExprAttr` canonical 文本为准；相关 pytest `test_element_binary_*` 和 `test_symbol.py` 通过。 | actual 符合当前 canonical spec；需 expectation 文本同步，execute 不回退文本顺序。 |
| `nn_lowering.img2col1d/2d` | actual 使用 `symbol.floordiv` 与 `SymbolExprAttr` canonical 乘法顺序，例如 stride 文本把 output extent 因子前置。 | 期望旧乘法因子顺序和旧函数签名文本顺序。 | 本轮已修 `spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`；`spec/dialect/symbol.md` 拒绝裸 `/` / `//`，要求 `floordiv`；img2col pytest 通过。 | actual 符合当前 spec；需 expectation 文本同步。 |
| `nn_lowering.transpose` | actual 按输出 shape 顺序先取 source axis 1，再取 axis 0，并生成 `dma.alloc(%axis1, %axis0)`。 | 期望先取 source axis 0，再取 axis 1。 | `spec/pass/lowering/nn_lowering/spec.md` 要求 dynamic shape operand 按结果 rank 顺序传入；`test_lower_transpose_dynamic` 通过。 | actual 符合结果 shape 顺序；需 expectation 文本同步。 |
| `memory_pool.dynamic` | actual 对符号乘法和 offset 采用 canonical 文本，例如 `OLL*PGZY`、`2*(J + OLL*PGZY)`；subview/reshape 保持词法线性切分。 | 期望 `PGZY*OLL`、`(PGZY*OLL+J)*2` 等旧文本顺序。 | `spec/pass/lowering/memory_pool.md` 要求同一 `func + space` 词法顺序线性切分，并只接受 `SymbolExprAttr` layout；memory_pool pytest 通过。 | actual 符合当前 spec；需 expectation 文本同步。 |
| `tile.analysis.broadcast` | actual 广播 source stride canonical 为 `[AMK, AMK, AMK, 1]`，`tile.analysis` 与 `tile.tile_exprs` 按 expand / elewise 角色写回。 | 期望旧文本 `[1*1*AMK, 1*AMK, AMK, 1]`。 | `spec/pass/tile/analysis.md` 要求 expand 维不写 tile expr，非 expand 维写当前 tile shape；不要求保留冗余乘法文本；tile analysis pytest 通过。 | actual 符合当前 spec；需 expectation 文本同步。 |
| `tile.elewise.element_compare` | actual 按当前 `kernel.binary_elewise(out, lhs, rhs)` 公开顺序生成 view 和 op，compare 输出为 `i1` out。 | 期望旧输入/断言按 raw operand 位置匹配，仍对 `ARG2` out 位置作旧文本断言。 | `spec/dialect/kernel.md` 与 `spec/pass/tile/elewise.md` 均声明 `out/lhs/rhs` 公开顺序；`test_tile_elewise_binary_pattern_public_compare_and_boundary_matrix` 通过。 | actual 符合当前 public operand order；需 expectation 文本同步。 |

NnMemoryType layout 旧 `IntAttr/StringAttr` 扫描：
- 命令：`rg -n "NnMemoryType\\(ArrayAttr\\(\\[(IntAttr|StringAttr)|shape\\.data|stride\\.data|isinstance\\([^\\n]*(IntAttr|StringAttr)" kernel_gen -g '*.py'`
- 命令：`rg -n "isinstance\\((dim|shape_dim|stride_dim|value|entry|attr),\\s*(IntAttr|StringAttr)\\)|NnMemoryType\\(ArrayAttr\\(\\[(IntAttr|StringAttr)|shape\\.data.*IntAttr|stride\\.data.*IntAttr|shape\\.data.*StringAttr|stride\\.data.*StringAttr" kernel_gen -g '*.py'`
- 结果：未发现 `NnMemoryType(ArrayAttr([IntAttr...]))` 或 `NnMemoryType(ArrayAttr([StringAttr...]))` 旧 layout 构造。
- 合法例外：`axis/perm/kind/op_name/cost_kind/metadata` 等非 memory layout attribute；已通过 `NnMemoryType` verifier 的 `shape.data/stride.data` 读取；`SymbolExprAttr` 校验后的 layout 访问。
- 剩余风险：全仓仍有大量合法 `shape.data/stride.data` 读取，review / 终验仍需重点检查是否有新引入的 layout 旧分支；本轮未发现需要恢复旧 `IntAttr/StringAttr` memory layout 兼容的实现路径。

Diff 反推自测：
- 改动文件：`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`、前序已有任务 diff 中的 `spec/dialect/kernel.md`。
- 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering/test_img2col1d.py test/passes/lowering/nn_lowering/test_img2col2d.py test/dialect/test_symbol.py -ra`
- 结果：通过，`106 passed, 1 warning`。
- 命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/core/contracts.py kernel_gen/passes/tile/elewise.py kernel_gen/dialect/kernel.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`
- 结果：通过，退出码 `0`。
- 命令：`git diff --check`
- 结果：通过，无输出。
- 命令：`git diff --name-only -- expectation .skills`
- 结果：无输出。
- 前序同轮已保留的公开 pytest 证据：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_kernel.py test/passes/tile/test_elewise.py test/passes/tile/test_analysis.py test/passes/test_memory_pool.py test/passes/lowering/nn_lowering/test_element_binary_add.py test/passes/lowering/nn_lowering/test_element_binary_div.py test/passes/lowering/nn_lowering/test_element_binary_mul.py test/passes/lowering/nn_lowering/test_element_binary_sub.py test/passes/lowering/nn_lowering/test_element_binary_truediv.py test/passes/lowering/nn_lowering/test_img2col1d.py test/passes/lowering/nn_lowering/test_img2col2d.py test/passes/lowering/nn_lowering/test_nn_lowering.py -ra` -> `143 passed, 1 warning`。

合同验收：
- 固定命令：`PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation`
- 结果：失败，退出码 `1`。
- 日志：`/tmp/core_print_alias_full_expectation_after_img2col_spec_20260507.log`。
- 失败数：`24 cases`。
- 剩余失败：`operation.arch.*` 8 项、`nn_lowering.element_binary.*` 5 项、`nn_lowering.img2col1d/2d`、`nn_lowering.transpose`、`memory_pool.dynamic`、`tile.analysis.broadcast`、`tile.elewise.element_compare`、`launch_kernel_cost_func.*` 3 项、`tools.dsl_cost_run.invalid_contract`、`tools.dsl_run.invalid_contract`。
- 判定：full expectation hard gate 仍未通过；普通 execute 不得修改 expectation case，因此不能 `-next review`。

自检：
- 接口：本轮未新增、删除、重命名或修改公开 API。
- 边界：未写 `expectation/`、未写 `.skills/`、未引用作废 `contract-sync` 作为通过依据。
- 异常：剩余失败已按 actual / expected / spec / verdict 分类；实现侧可修项目前只发现并修正 img2col spec 中旧 `//` 口径残留。
- 兼容：没有恢复旧私有 target registry、旧 cost kind、旧 dsl_run helper 注入、旧 `IntAttr/StringAttr` memory layout 兼容。
- 实现遗漏：当前剩余 implementation-side actual 均与当前 spec / pytest 一致；hard gate 仍依赖 expectation 合同同步或架构裁定。
- 冗余：未新增 helper 或兼容 shim。
- 注释准确性：本轮只改 spec 文字，不改函数注释。
- 复用与函数粒度：未改实现函数。
- 输入输出校验：未改公开校验路径；已扫描 NnMemoryType layout 旧分支。
- 资源 / 并发 / 性能：未改运行时代码，无新增风险。
- 测试有效性：img2col/symbol pytest 能锁定 `SymbolExprAttr`/`symbol.floordiv` 口径；tile/memory_pool/nn_lowering 相关 pytest 前序已通过。

结论：
- 继续 `execute / 阻塞`。
- 不执行 `-next review`。
- 下一步需要架构按矩阵对 `expectation` 合同资产进行极窄同步，或给出新的用户裁定；execute 仍只保留实现/spec/test 证据，不写 expectation。

## full expectation runner 裁定与复跑 - 2026-05-07 18:14 +0800 - 大闸蟹

已按授权对 `expectation/utils/suite_runner.py` 做极窄修正，支持：
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`
- 子进程 `cwd` 使用该 worktree。
- 子进程 `PYTHONPATH` 顺序为 `worktree -> 调用方已有路径 -> repo_root`，其中 `repo_root=/home/lfr/kernelcode_generate` 仅排后面用于提供 `expectation/` 合同资产。
- 未设置 `EXPECTATION_WORKTREE_ROOT` 时保持原行为。

复跑命令：
```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

复跑结果：
- `python3 -m expectation.core.print` 在 `cwd=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` 下通过，确认 child 进程已优先导入 worktree `kernel_gen.core.print`。
- `python3 -m expectation` 仍失败，但失败已从“主仓抢先导入”收敛为真实实现/合同差异，共 24 项，主要为：
  - `expectation.operation.arch.*`
  - `expectation.pass.lowing.nn_lowering.element_binary.*`
  - `expectation.pass.lowing.nn_lowering.img2col.*`
  - `expectation.pass.lowing.nn_lowering.transpose`
  - `expectation.pass.memory_pool.dynamic`
  - `expectation.pass.tile.analysis.broadcast`
  - `expectation.pass.tile.elewise.element_compare`
  - `expectation.pass.tuning.launch_kernel_cost_func.*`
  - `expectation.tools.dsl_cost_run.invalid_contract`
  - `expectation.tools.dsl_run.invalid_contract`

结论：
- full expectation runner / 验证现场路径修正方式：已裁定并落实为 `EXPECTATION_WORKTREE_ROOT`。
- 当前任务仍阻塞于真实实现/合同差异，不是 runner 路径问题。
- 保持 `execute`，不进入 review；若后续需要缩小 24 项中的合同修复范围，再按用户/架构授权单独裁定。

---

时间：2026-05-07 18:25 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / suite_runner 权限边界复核

触发来源：
- 神秘人同步最新口径：榕已给出新的 full expectation 固定命令，但该命令依赖 `expectation/utils/suite_runner.py` 极窄变更。
- 按 `AGENTS.md` expectation 权限，execute 不直接修改 `expectation`；runner 已转大闸蟹和守护按用户授权处理。
- 当前要求：继续保持 execute 阻塞，不 `-next review`；待架构侧确认 `suite_runner` 已按授权落位后，再使用新命令复跑。

固定待复跑命令：
```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

本次复核：
- 命令：`git diff -- expectation/utils/suite_runner.py`
- 执行目录：`/home/lfr/kernelcode_generate`
- 结果：无输出；当前无 execute 保留的 `suite_runner.py` diff。
- 说明：即使主仓现场文件内容已出现 `EXPECTATION_WORKTREE_ROOT` 相关能力，本 execute 仍不把它作为通过依据；需等待架构侧明确确认 runner 已按授权落位。

禁止修改面：
- 本次未修改 `expectation/`。
- 本次未修改 `.skills/`。
- 本次未引用 `contract-sync`；`alias-sync` 仍按最新口径作为唯一有效合同同步落点，但 full expectation 需等 runner 确认后复跑。

Diff 反推自测：
- 本次无产品代码 diff，无新增 pytest / 脚本测试。
- full expectation 属于合同验收资产，不计入 Diff 反推测试；当前因 runner 落位确认未完成，不复跑。

自检：
- 接口：本次未新增、删除、重命名或修改公开 API。
- 边界：遵守 expectation 只读 / execute 不写 runner 的最新权限口径。
- 测试有效性：当前不能凭未确认 runner 状态进入 review；等待架构侧确认后必须复跑 fixed full expectation，并将结果补回本记录。

结论：
- 继续 execute / 阻塞。
- 不 `-next review`。
- 等大闸蟹 / 守护确认 `expectation/utils/suite_runner.py` 授权变更已落位后，再按固定命令复跑 full expectation。

---

时间：2026-05-07 18:15 +0800
经办人：守护最好的爱莉希雅
类型：架构裁定 / full expectation runner 验证现场修正

触发来源：
- 神秘人同步：按榕裁定固定命令复跑 full expectation 仍失败，execute 记录 57 个失败。
- 关键根因：顶层 `PYTHONPATH` 能让直接 `expectation.core.print` 导入任务 worktree 的 `kernel_gen`，但 full suite 的 `expectation/utils/suite_runner.py` 在每个 case 子进程中把 `repo_root=/home/lfr/kernelcode_generate` 前置到 `PYTHONPATH`，且 `subprocess.run(..., cwd=repo_root)` 让子进程 `sys.path[0]` 也是主仓根目录，导致子进程优先导入主仓 `kernel_gen`。

裁定结论：
- 当前 57 个 full expectation 失败不能作为业务实现失败或合同文本失败的最终判据；full suite 子进程没有稳定验证 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` 的实现。
- 任务继续 `execute` 阻塞，不得进入 `review`。
- 不得把 `alias-sync` / `contract-sync` 任一 worktree 当作通过依据来绕过 runner 问题。
- `/home/lfr/kernelcode_generate` 仍只作为 `expectation/` 合同资产来源，不是新的 sync 落点。

唯一允许的验证现场修正方向：
- 极窄修正实际被加载的 runner：`/home/lfr/kernelcode_generate/expectation/utils/suite_runner.py`。
- 修正目标只限子进程验证现场：
  - `_subprocess_env(...)` 必须保留调用方已有 `PYTHONPATH` 顺序，不得把 `repo_root` 前置到已有 worktree 路径之前。
  - 若 `repo_root` 不在已有 `PYTHONPATH` 中，只能追加到末尾，用于装载 `expectation/` 合同资产。
  - `_run_case_module(...)` 的 `cwd` 不得固定为 `repo_root`；应使用 active code root。active code root 定义为当前 `PYTHONPATH` 中第一个包含 `kernel_gen/` 的目录；在榕裁定命令下应解析为 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`。
  - 若没有 active code root，才回退 `repo_root`。
- 修正后，子进程中 `sys.path[0]` 与 `PYTHONPATH` 优先级必须保证任务 worktree 的 `kernel_gen` 早于主仓 `kernel_gen`。

授权边界：
- 这是 expectation runner / 验证 harness 的极窄修正，不是 expectation case 合同同步。
- 授权范围仅限 `expectation/utils/suite_runner.py`；不得修改任何 `expectation/**` case 文件、断言文本、runner 以外工具、`.skills/**` 或公开 API。
- 普通 execute 只有在管理员明确转达本裁定后，才可按此极窄范围修 runner；review/merge/admin 仍不得自行扩大 expectation 修改面。

固定验收方式：
```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

修正后必须先补充路径诊断：
- full suite 子进程内 `kernel_gen.__file__` 必须指向 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump/kernel_gen/__init__.py`。
- `expectation.core.print` 在 full suite 子进程和直接单项运行中都必须命中同一份 worktree `kernel_gen.core.print`。

后续判定规则：
- runner 路径修正前的 57 个失败矩阵仅作为路径污染证据，不作为实现缺口清单。
- runner 路径修正并复跑 fixed command 后，仍失败的 case 才进入原先的 actual IR / expected / spec / verdict 分类。
- 若修正 runner 后 full expectation 通过，才允许继续检查 full pytest、coverage 95/80、diff check、禁止修改面与静态扫描，全部通过后才可 `-next review`。

---

时间：2026-05-07 18:15 +0800
经办人：守护最好的爱莉希雅
类型：架构授权执行 / suite_runner 极窄修正与复跑结果

授权来源：
- 神秘人同步榕裁定：允许极窄调整 full expectation runner / 验证现场路径。
- 授权范围只限 `expectation/utils/suite_runner.py`。
- 不得修改其它 `expectation/**` 文件，不得修改合同 case。

实际处理：
- 已按授权修正 `/home/lfr/kernelcode_generate/expectation/utils/suite_runner.py` 的 full suite 子进程现场。
- 新增 `EXPECTATION_WORKTREE_ROOT` 行为：
  - 未设置时保持原行为。
  - 设置后子进程 `cwd` 使用 `EXPECTATION_WORKTREE_ROOT`。
  - 子进程 `PYTHONPATH` 第一位固定为 `EXPECTATION_WORKTREE_ROOT`。
  - `/home/lfr/kernelcode_generate` 只排在后面，用于提供 `expectation/` 合同资产。
- 未修改其它 `expectation/**` case 文件。
- 未修改 `.skills/**`。
- `alias-sync` 仍为唯一有效 sync 落点；`contract-sync` 作废；`/home/lfr/kernelcode_generate` 仅用于装载 `expectation/` 合同资产。

验证命令：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/utils/suite_runner.py` -> 通过。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation > /tmp/core_print_alias_full_expectation_runner_fix_20260507.log 2>&1` -> 失败，退出码 `1`。

runner 修正效果：
- 复跑后 full suite 失败从路径污染状态下的 `57 cases` 降为 `24 cases`。
- `expectation.core.print` 不再失败，说明子进程已能导入任务 worktree 的 `kernel_gen.core.print`。
- 之前由主仓 `kernel_gen` 抢先导入导致的大量旧 layout / missing API 失败已消失。

当前 full expectation 剩余失败：
- `expectation.operation.arch.get_block_id`
- `expectation.operation.arch.get_block_num`
- `expectation.operation.arch.get_dynamic_memory`
- `expectation.operation.arch.get_subthread_id`
- `expectation.operation.arch.get_subthread_num`
- `expectation.operation.arch.get_thread_id`
- `expectation.operation.arch.get_thread_num`
- `expectation.operation.arch.launch_kernel`
- `expectation.pass.lowing.nn_lowering.element_binary.add`
- `expectation.pass.lowing.nn_lowering.element_binary.div`
- `expectation.pass.lowing.nn_lowering.element_binary.mul`
- `expectation.pass.lowing.nn_lowering.element_binary.sub`
- `expectation.pass.lowing.nn_lowering.element_binary.truediv`
- `expectation.pass.lowing.nn_lowering.img2col.img2col1d`
- `expectation.pass.lowing.nn_lowering.img2col.img2col2d`
- `expectation.pass.lowing.nn_lowering.transpose`
- `expectation.pass.memory_pool.dynamic`
- `expectation.pass.tile.analysis.broadcast`
- `expectation.pass.tile.elewise.element_compare`
- `expectation.pass.tuning.launch_kernel_cost_func.basic_all`
- `expectation.pass.tuning.launch_kernel_cost_func.multi_kind`
- `expectation.pass.tuning.launch_kernel_cost_func.shared_callee_once`
- `expectation.tools.dsl_cost_run.invalid_contract`
- `expectation.tools.dsl_run.invalid_contract`

裁定：
- runner / 验证现场路径问题已按授权闭合。
- 当前 24 个失败不再归因于 suite runner 主仓优先导入问题，可以回到此前 actual IR / expected / spec / verdict 矩阵继续收口。
- `operation.arch.*`、`launch_kernel_cost_func.*`、`tools.dsl_cost_run.invalid_contract`、`tools.dsl_run.invalid_contract` 仍属于已裁定的旧合同资产冲突，不得通过恢复私有 API、旧 cost kind 或旧 dsl_run 合同修实现。
- `nn_lowering.element_binary.*`、`transpose`、`memory_pool.dynamic`、`tile.analysis.broadcast`、`tile.elewise.element_compare` 仍需 execute 继续补 actual IR / expected / spec / verdict 矩阵；actual 违反 spec 的继续修实现，actual 符合 spec 的再请求极窄 expectation 同步。
- `img2col1d/2d` 仍按条件同步边界处理：需先有 actual 符合当前 `//` / `SymbolExprAttr` canonical spec 的记录。

结论：
- full expectation hard gate 仍未通过。
- 任务继续 `execute` 阻塞，不得进入 `review`。

---

时间：2026-05-07 18:08 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / 榕裁定路径 full expectation 复跑

触发来源：
- 神秘人同步榕裁定：full expectation 固定验证路径解除冻结。
- 固定命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation`。
- 固定口径：`alias-sync` 是唯一有效 sync 落点；`contract-sync` 作废；`/home/lfr/kernelcode_generate` 只用于显式装载 `expectation/` 合同资产，不是新的 sync 落点；不得由 execute / 管理员补建或复制 `expectation`。

执行命令与结果：
- 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation > /tmp/core_print_alias_full_expectation_20260507_final2.log 2>&1`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`
- 结果：失败，退出码 `1`。
- 总结：`expectation expectation suite failed (57 cases)`。
- 完整日志：`/tmp/core_print_alias_full_expectation_20260507_final2.log`。

路径诊断：
- 直接导入诊断命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 - <<'PY' ...`
- 直接导入结果：`kernel_gen.__file__` 指向 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump/kernel_gen/__init__.py`，且 `from kernel_gen.core.print import print_operation_with_aliases` 成功。
- 直接合同命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation.core.print`
- 直接合同结果：通过，8 个 core.print case 全部完成。
- full suite 失败原因之一：`/home/lfr/kernelcode_generate/expectation/utils/suite_runner.py` 的 `_subprocess_env(repo_root)` 会在每个 case 子进程中把 `repo_root=/home/lfr/kernelcode_generate` 前置到 `PYTHONPATH`，因此子进程优先导入主仓 `kernel_gen`，不是本任务 worktree 的 `kernel_gen`。这导致 full suite 中 `expectation.core.print` 子进程报 `ModuleNotFoundError: No module named 'kernel_gen.core.print'`，而直接运行 `expectation.core.print` 可通过。
- 判定：当前固定 full expectation 命令没有稳定验证本任务 worktree 的实现；该问题落在 `expectation` runner / 验证现场路径组合上。普通 execute 不能修改 `expectation/`，也不能补建 / 复制 expectation。

失败矩阵：

| 分组 | 失败模块 | 失败摘要 | 初步判定 |
| --- | --- | --- | --- |
| core.print | `expectation.core.print` | full suite 子进程报 `ModuleNotFoundError: No module named 'kernel_gen.core.print'`；同一 PYTHONPATH 下直接 `python3 -m expectation.core.print` 通过。 | full suite 子进程 PYTHONPATH 被 `expectation/utils/suite_runner.py` 改写为主仓优先，未验证到 worktree 实现。 |
| execute_engine npu_demo | `expectation.execute_engine.npu_demo.cost.elewise`、`expectation.execute_engine.npu_demo.default.add`、`expectation.execute_engine.npu_demo.default.matmul`、`expectation.execute_engine.npu_demo.default.mul`、`expectation.execute_engine.npu_demo.default.sub` | `nn element binary result shape must be int or symbol`、`matmul shape must be IntAttr or StringAttr` 等旧 layout 错误。 | 子进程主仓优先后命中旧实现 / 旧合同组合；需路径修正后再判定是否仍是实现缺口。 |
| operation.arch | `expectation.operation.arch.get_block_id`、`get_block_num`、`get_dynamic_memory`、`get_subthread_id`、`get_subthread_num`、`get_thread_id`、`get_thread_num`、`launch_kernel` | 仍直连 `kernel_gen.target.registry._get_current_target/_set_current_target` 私有入口。 | 旧 expectation 合同冲突；不得恢复私有 API。 |
| decompass | `expectation.pass.decompass.softmax` | `shape dimensions must be SymbolExprAttr`。 | 需要在路径修正后复核；当前 full suite 子进程未可靠验证 worktree。 |
| dma_memory_hierarchy | `expectation.pass.dma_memory_hierarchy.matmul_apply` | `dynamic_shape result shape entries must be IntAttr or StringAttr`。 | 旧 layout 合同 / 子进程主仓优先问题，需路径修正后复核。 |
| nn_lowering | `expectation.pass.lowing.nn_lowering.broadcast`、`cast`、`element_binary.add`、`element_binary.div`、`element_binary.mul`、`element_binary.sub`、`element_binary.truediv`、`element_compare`、`exp`、`img2col.img2col1d`、`img2col.img2col2d`、`matmul`、`reduce.reduce_max`、`reduce.reduce_min`、`reduce.reduce_sum`、`select`、`transpose` | 旧 `IntAttr/StringAttr` layout、旧文本 order 或旧 `floordiv` 合同。 | 此前 actual/spec 矩阵已区分多项为旧文本冲突；但本次 full suite 子进程不可靠，需路径修正后复核。 |
| memory_pool | `expectation.pass.memory_pool.alignment`、`basic`、`dynamic`、`invalid`、`spaces` | `MemoryPoolUnsupportedShape: #symbol.expr<...>` 等。 | 与当前 SymbolExprAttr layout 相关；需路径修正后用 worktree 实现复核。 |
| pipeline | `expectation.pass.pipeline.default_lowering` | `nn element binary result shape must be int or symbol`。 | 已在 worktree 修复 default-lowering 并补 pytest；本次 full suite 子进程未可靠验证 worktree。 |
| tile.analysis | `expectation.pass.tile.analysis.broadcast`、`element_binary`、`element_compare`、`fc`、`matmul` | `CHECK-NEXT not found` 或 `shape dimensions must be SymbolExprAttr`。 | 旧文本 / layout 组合；需路径修正后复核。 |
| tile.elewise | `expectation.pass.tile.elewise.broadcast`、`element_binary`、`element_compare`、`fc`、`matmul` | `CHECK-NEXT not found` 或 layout verifier 失败。 | 旧文本 / layout 组合；需路径修正后复核。 |
| tile.reduce | `expectation.pass.tile.reduce.fc`、`matmul` | `shape dimensions must be SymbolExprAttr` 等。 | 需路径修正后复核；此前 isolated fc 诊断为 `ok=True`。 |
| launch_kernel_cost_func | `expectation.pass.tuning.launch_kernel_cost_func.basic_all`、`multi_kind`、`shared_callee_once` | 旧 `compute/memory/latency` cost kind 被当前七值合同拒绝。 | 旧 expectation 合同冲突；不得回退 cost kind。 |
| tools | `expectation.tools.dsl_cost_run.invalid_contract`、`expectation.tools.dsl_run.add`、`expectation.tools.dsl_run.invalid_contract` | 旧 cost kind / 旧 `cse` pass / `nn element binary result shape must be int or symbol` / old invalid real_args 断言。 | 部分为旧合同冲突；`dsl_run.add` 需路径修正后复核。 |

补齐已有验证记录：
- full pytest：前序已记录 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test -ra` / coverage full run 中 pytest 阶段通过，`1989 passed, 1 warning`。
- coverage：前序已记录 full coverage gate 通过，`line=95.00%`、`branch=87.93%`。
- 禁止修改面：本次复查 `git diff --name-only -- expectation .skills` 无输出。
- `git diff --check`：本次复查通过，无输出。
- core.print 单项合同：本次直接 `python3 -m expectation.core.print` 通过。

Diff 反推自测：
- 本次无新增产品代码 diff；继续沿用前序实现侧 pytest / coverage / diff-check 证据。
- full expectation 是合同验收资产，不计入 Diff 反推测试；本次作为 hard gate 单列，结果失败。

自检：
- 接口：本次未新增、删除、重命名或修改公开 API。
- 边界：未写 `expectation/`，未写 `.skills/`，未引用 `contract-sync` 作为通过依据。
- 异常：full expectation 失败已列矩阵；同时记录固定命令对子进程 PYTHONPATH 的路径问题。
- 测试有效性：直接 core.print 合同可命中 worktree 并通过；full suite 当前不能稳定证明 worktree 实现，因为子进程主仓优先。

结论：
- full expectation hard gate 未通过，继续 execute / 阻塞。
- 不 `-next review`。
- 需要管理员 / 架构 / 榕裁定：修正 full expectation runner / 验证现场，使 case 子进程优先导入 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` 的 `kernel_gen`；或授权相应 expectation runner 侧极窄修正。普通 execute 不写 `expectation/`，不能自行修复该路径问题。

---

时间：2026-05-07 18:00 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / TODO 再次复查与阻塞重复催办

触发来源：
- 榕再次要求查看 `TODO.md`，继续任务，完成后 `-next` 并回报管理员；如有阻塞 / 疑问，重复用脚本询问直到回复。

复查结果：
- `TODO.md` 当前仍只有 `T-20260507-bfc9a0e0` 处于 `execute / 进行中`。
- 任务列表为空，无新任务。
- 需要用户确认事项为空。
- 当前仍无唯一 full expectation 验证路径裁定。

当前冻结口径：
- 不引用 `alias-sync` 或 `contract-sync` 任一 worktree 作为通过依据。
- 不写 `expectation/`。
- 不执行 `-next review`。
- 等榕裁定唯一 full expectation 验证路径后再恢复复跑并记录。

禁止修改面：
- 命令：`git diff --name-only -- expectation .skills`
- 结果：无输出。

本次执行：
- 未修改产品代码。
- 未运行 full expectation。
- 未流转 review。

结论：
- 继续 execute / 阻塞。
- 继续按要求用脚本回报管理员，并再次直接催榕裁定唯一 full expectation 验证路径。

---

时间：2026-05-07 18:31 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / 最新阻塞状态补记

最新口径：
- 神秘人已明确：新的 full expectation 固定命令依赖 `expectation/utils/suite_runner.py` 极窄变更；按 `AGENTS.md` expectation 权限，execute 不直接修改 `expectation`。
- runner 变更已转大闸蟹和守护按用户授权处理；execute 当前等待架构侧确认 runner 已按授权落位。
- `alias-sync` 是唯一有效合同同步落点；`contract-sync` 作废。

本次复核：
- 命令：`git diff -- expectation/utils/suite_runner.py`
- 执行目录：`/home/lfr/kernelcode_generate`
- 结果：无输出；当前无 execute 保留的 `suite_runner.py` diff。

待复跑命令：
```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

自检与 Diff 反推自测：
- 本次无产品代码 diff，无新增 pytest / 脚本测试。
- 未写 `expectation/`，未写 `.skills/`。
- full expectation 属于合同验收资产；在架构确认 runner 落位前不复跑、不作为通过依据。

结论：
- 继续 execute / 阻塞。
- 不 `-next review`。
- 等架构侧确认 `suite_runner` 落位后，再按固定命令复跑 full expectation 并补记结果。

---

时间：2026-05-07 18:56 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / 文件末尾最新状态补记
任务目标：确保最新 execute 状态按记录文件末尾追加，避免只依赖中段补记。

改动：
- 本轮实际修改：`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`，把 img2col 动态 extent 的旧 `//` 文本要求改为当前 `SymbolExprAttr` + `symbol.floordiv` 公开口径。
- 详细 actual / expected / spec / verdict 矩阵已写在本记录 `2026-05-07 18:49 +0800` 段落；该矩阵显示剩余实现侧 actual 未发现违反当前 spec 的可修项，剩余失败需要 expectation 合同极窄同步或架构裁定。
- 未修改 `expectation/**` 或 `.skills/**`。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering/test_img2col1d.py test/passes/lowering/nn_lowering/test_img2col2d.py test/dialect/test_symbol.py -ra` -> `106 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/core/contracts.py kernel_gen/passes/tile/elewise.py kernel_gen/dialect/kernel.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py` -> 通过。
- `git diff --check` -> 通过。
- `git diff --name-only -- expectation .skills` -> 无输出。
- 合同验收固定命令 `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation` -> 失败，退出码 `1`，剩余 `24 cases`，日志 `/tmp/core_print_alias_full_expectation_after_img2col_spec_20260507.log`。

自检：
- 未新增或变更公开 API。
- 未恢复旧私有 target registry、旧 cost kind、旧 dsl_run helper 注入或旧 `IntAttr/StringAttr` memory layout 兼容。
- `expectation` 只作为合同验收资产单列，不计入 Diff 反推自测。

结论：
- 继续 `execute / 阻塞`。
- 不执行 `-next review`。
- 等架构 / 用户对剩余旧合同资产给出极窄同步或其它裁定；普通 execute 不写 expectation。

---

时间：2026-05-07 18:58 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / 24 个 expectation 极窄同步等待中
任务目标：保持 execute 阻塞，等待架构侧在 `wt-20260507-core-print-alias-expectation-sync` 完成 24 个 expectation 文件的极窄同步后，再按固定命令复跑 full expectation。

改动：
- 已收到最新裁定：大闸蟹已给出 24 个 expectation 文件的极窄同步范围。
- 普通 execute 仍不得写 `expectation/`；当前任务继续只保留实现/spec/test 侧证据，不进入 review。
- 后续 full expectation 复跑固定命令保持不变：
  `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation`

验证：
- 当前未复跑 full expectation；等待架构侧同步落位后再执行。
- 既有验证仍有效：img2col/symbol pytest `106 passed, 1 warning`；py_compile、`git diff --check`、`git diff --name-only -- expectation .skills` 通过。

自检：
- 未修改 `expectation/`、`.skills/` 或公开 API。
- 当前仍需等待 expectation 合同资产同步完成后，才能判断 24 个剩余失败是否全部收口。

结论：
- 继续 `execute / 阻塞`。
- 不执行 `-next review`。
- 等架构侧同步完成后，按固定命令复跑 full expectation，再决定是否进入后续 full pytest / coverage / diff check / 静态扫描流转。

## expectation 极窄同步授权裁定 - 2026-05-07 19:05 +0800 - 大闸蟹

裁定依据：
- 已读取本记录 `2026-05-07 18:49 +0800` 的 actual / expected / spec / verdict 矩阵。
- 已读取 `2026-05-07 18:56 +0800` 最新状态补记：runner 落位后固定 full expectation 仍失败 24 cases，日志为 `/tmp/core_print_alias_full_expectation_after_img2col_spec_20260507.log`。
- 执行人已验证 img2col + symbol 相关 pytest `106 passed`、py_compile、`git diff --check` 与禁止修改面通过。
- 当前剩余矩阵未发现需要恢复旧私有 target registry、旧 cost kind、旧 dsl_run helper 注入、旧 `IntAttr/StringAttr` memory layout 或旧文本顺序的实现侧缺口。

授权结论：
- 允许对下列 `expectation` 合同资产做一次极窄同步，且只能在已裁定的唯一有效 sync 落点 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync` 内处理。
- 普通 execute / review / merge / admin 仍不得自行修改 `expectation`；该授权只允许架构师或被用户 / 架构师明确指派的 expectation 合同同步执行处理。
- 不授权修改任何未列名的 `expectation/**`、`.skills/**`、计划资产或公开 API。

授权文件范围：
- `expectation/operation/arch/get_block_id.py`
- `expectation/operation/arch/get_block_num.py`
- `expectation/operation/arch/get_dynamic_memory.py`
- `expectation/operation/arch/get_subthread_id.py`
- `expectation/operation/arch/get_subthread_num.py`
- `expectation/operation/arch/get_thread_id.py`
- `expectation/operation/arch/get_thread_num.py`
- `expectation/operation/arch/launch_kernel.py`
- `expectation/pass/lowing/nn_lowering/element_binary/add.py`
- `expectation/pass/lowing/nn_lowering/element_binary/div.py`
- `expectation/pass/lowing/nn_lowering/element_binary/mul.py`
- `expectation/pass/lowing/nn_lowering/element_binary/sub.py`
- `expectation/pass/lowing/nn_lowering/element_binary/truediv.py`
- `expectation/pass/lowing/nn_lowering/img2col/img2col1d.py`
- `expectation/pass/lowing/nn_lowering/img2col/img2col2d.py`
- `expectation/pass/lowing/nn_lowering/transpose.py`
- `expectation/pass/memory_pool/dynamic.py`
- `expectation/pass/tile/analysis/broadcast.py`
- `expectation/pass/tile/elewise/element_compare.py`
- `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`
- `expectation/pass/tuning/launch_kernel_cost_func/multi_kind.py`
- `expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`
- `expectation/tools/dsl_cost_run/invalid_contract.py`
- `expectation/tools/dsl_run/invalid_contract.py`

同步目标：
- `operation.arch.*`：从旧私有 `target_registry._get_current_target/_set_current_target` 合同同步到当前公开 target registry / arch operation 合同；不得恢复下划线私有入口。
- `launch_kernel_cost_func.*` 与 `tools.dsl_cost_run.invalid_contract`：同步到当前七值 cost kind `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2`、当前 pipeline/pass 名称和当前公开错误语义；不得恢复 `compute/memory/latency`、旧 `DMA/MAC` 入口或旧 `cse` pass。
- `tools.dsl_run.invalid_contract`：同步 case 6 到当前公开 dsl_run real_args / AST 失败语义；不得恢复旧 helper 注入或私有路径。
- `nn_lowering.element_binary.*`：同步到当前 `SymbolExprAttr` canonical 文本顺序，例如 `X + 1`，不得回退实现到旧 `1 + X` 文本。
- `nn_lowering.img2col1d/2d`：同步到当前 `SymbolExprAttr` + `symbol.floordiv` 文本和 canonical 因子顺序。
- `nn_lowering.transpose`：同步到按结果 rank 顺序构造 dynamic shape operand 的当前 IR。
- `memory_pool.dynamic`：同步 commutative / offset canonical 文本顺序，保留 `arch.get_dynamic_memory + dma.subview + dma.reshape` 语义。
- `tile.analysis.broadcast`：同步到当前 stride canonical 文本、expand 维空 tile expr 和 elewise 维 tile expr 合同。
- `tile.elewise.element_compare`：同步到当前公开 `kernel.binary_elewise(out, lhs, rhs)` operand 顺序、`i1` output 和当前 `dma.view` / `tile.*` attrs。

固定验收命令：
```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

同步后必须补充验证：
- 上述固定 full expectation 必须通过。
- `git diff --name-only -- expectation` 在 sync worktree 中只能出现本裁定列名的 24 个文件；不得出现其它 `expectation/**` 文件。
- 原 execute worktree 仍需保留 `expectation/**` diff empty。
- 继续复核 full pytest、coverage 95/80、py_compile、`git diff --check`、禁止修改面和静态扫描；全部通过后才允许流转 review。

当前任务结论：
- 在上述 expectation 合同同步完成并通过固定 full expectation 前，T-20260507-bfc9a0e0 继续 `execute / 阻塞`，不得进入 review。

## expectation 极窄同步授权复核 - 2026-05-07 19:18 +0800 - 守护最好的爱莉希雅

复核输入：
- 小李飞刀最新补记确认：runner 落位后固定 full expectation 仍失败 24 cases，日志 `/tmp/core_print_alias_full_expectation_after_img2col_spec_20260507.log`。
- Diff 反推自测：img2col + symbol pytest `106 passed`；py_compile、`git diff --check`、禁止修改面通过。
- 本轮只修改 `spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`，未写 `expectation/**` 或 `.skills/**`。
- actual / expected / spec / verdict 矩阵显示剩余 24 项均为旧合同文本或旧公开口径冲突；未发现需要恢复旧私有 target registry、旧 cost kind、旧 dsl_run helper 注入、旧 `IntAttr/StringAttr` memory layout 或旧表达式文本顺序的实现侧缺口。

裁定：
- 同意大闸蟹上一段 24 个文件的极窄 expectation 同步范围。
- 唯一有效 sync 落点仍固定为 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`；不得使用 `/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync` 作为通过依据。
- 授权只覆盖上一段列名的 24 个 `expectation` 文件；不得扩展到其它 `expectation/**`、`.skills/**`、计划资产或实现文件。
- 普通 execute / review / merge / admin 仍不得自行修改 `expectation`；只能由架构师或被用户 / 架构师明确指派的合同同步执行处理。

同步要求：
- `operation.arch.*` 必须改到当前公开 target / arch 合同，不得恢复 `_get_current_target/_set_current_target` 私有入口。
- cost 与 `dsl_cost_run` 必须改到当前七值 kind `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 和当前公开错误语义，不得恢复 `compute/memory/latency`、旧 `DMA/MAC` 或旧 `cse` 口径。
- `dsl_run.invalid_contract` 只同步当前公开 real_args / AST 失败语义，不得恢复 helper 注入或私有路径。
- `nn_lowering`、`memory_pool`、`tile` 相关 case 只同步 expected 文本到当前 `SymbolExprAttr` canonical、`symbol.floordiv`、当前 operand 顺序和当前公开 pass 合同，不得为了旧文本回退实现。

固定验收命令：
```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

通过条件：
- 固定 full expectation 必须通过。
- sync worktree 中 `git diff --name-only -- expectation` 只能出现授权 24 个文件。
- execute worktree 中 `expectation/**` diff 必须保持为空。
- full pytest、coverage 95/80、py_compile、`git diff --check`、禁止修改面和静态扫描仍需保持通过。

结论：
- 当前可以进入极窄 expectation 合同同步。
- 同步完成并通过固定 full expectation 前，T-20260507-bfc9a0e0 仍为 `execute / 阻塞`，不得进入 review。

---

时间：2026-05-07 19:05 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / TODO 复查后继续等待 alias-sync 落位

触发来源：
- 榕要求再次查看 `TODO.md` 并继续当前任务。
- 神秘人已核对 `TODO.md`：当前仍由小李飞刀负责 `execute / 进行中`，任务列表为空；继续等待架构侧完成 `alias-sync` 内 24 个 `expectation` 文件极窄同步。

当前状态：
- 不写 `expectation/`。
- 不引用未落位的 sync worktree 作为通过依据。
- 不执行 `-next review`。
- 等守护 / 架构侧回报 24 个文件已在 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync` 落位后，再按固定命令复跑 full expectation。

自检：
- 本次未修改产品代码、spec、test 或 `expectation/`。
- 本次无新增 Diff 反推自测；当前阻塞点是合同资产同步未完成，不是实现侧新增 diff。

结论：
- 继续 `execute / 阻塞`。
- 同步完成前不流转 review。

---

时间：2026-05-07 20:24 +0800
经办人：小李飞刀
任务：T-20260507-bfc9a0e0 / execute 收口与硬门禁复跑

本轮执行内容：
- 按 alias-sync 唯一路径和固定命令复跑 full expectation。
- 补齐/确认 full pytest、coverage 95/80、py_compile、`git diff --check`、禁止修改面和静态扫描。
- 修复本轮残留的 `object` 签名违规，收口到更具体的联合类型。

代码/文档改动：
- `kernel_gen/dsl/ast/nodes/basic.py`
  - 将 `FunctionAST.input_from_runtime_arg(..., value: object, ...)` 收口为具体联合类型。
  - 补齐该函数文件级 API 列表与函数说明，去除残留人员元信息。
- `spec/dsl/ast/nodes/basic.md`
  - 将对应 API 列表与参数类型同步为具体联合类型。
- `test/dsl/ast/nodes/test_basic.py`
  - 增加签名断言，确保不再出现 `object` 形参。

验证结果：
- fixed full expectation：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation`
  - 结果：退出码 0。
  - 日志：`/tmp/core_print_alias_full_expectation_execute_after_object_20260507.log`
- `pytest --collect-only -q test`
  - 结果：`1989 tests collected in 2.02s`。
  - 日志：`/tmp/core_print_alias_collect_execute_after_object_20260507.log`
- `pytest -q test -ra`
  - 结果：`1989 passed, 1 warning in 318.64s`。
  - 日志：`/tmp/core_print_alias_full_pytest_execute_after_object_20260507.log`
- coverage：
  - 结果：`kernel_gen` line `95.00%`，branch `87.93%`。
  - 报告：`/tmp/core_print_alias_dump_cov_execute_after_object_20260507.json`
  - 日志：`/tmp/core_print_alias_full_coverage_pytest_execute_after_object_20260507.log`
- `pytest -q test/dsl/ast/nodes/test_basic.py -ra`
  - 结果：`16 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/ast/nodes/basic.py test/dsl/ast/nodes/test_basic.py`
  - 结果：通过。
- `git diff --check`
  - 结果：通过。
- `git diff --name-only -- expectation .skills`
  - 结果：无输出。
- 静态扫描：
  - `rg -n "(^|[,( ])[^\n]*:\s*object\b|->\s*object\b" kernel_gen test script -g '*.py'`
    - 结果：无输出。
  - `rg -n "hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx" kernel_gen test spec -g '*.py' -g '*.md'`
    - 结果：无输出。
  - `rg -n "NnMemoryType\(.*(IntAttr|StringAttr)|ArrayAttr\(\[(IntAttr|StringAttr)" kernel_gen || true`
    - 结果：仅剩非 memory layout 的合法例外（如 perm / tile metadata），未见旧 layout 兼容读取。

Diff 反推自测：
- `test/core/test_print.py`、`test/passes/test_pass_manager.py`、`test/tools/test_dsl_run.py`、`test/tools/test_ircheck_runner.py`、`test/tools/test_mlir_gen_compare.py` 覆盖本轮 core print alias dump、pass manager、dsl_run、ircheck、compare 相关改动。
- `test/dsl/ast/nodes/test_basic.py` 覆盖 `FunctionAST.input_from_runtime_arg` 签名与 runtime arg 入口收口。
- `pytest -q test -ra` 与 `pytest --collect-only -q test` 作为全量回归与收集验证，不计入 expectation 反推测试。

自检结论：
- 未修改 `expectation/` 与 `.skills/`。
- 未新增未确认公开 API。
- 未使用跨文件非公开 API、ctx 能力探测、`object` 签名或非装饰器嵌套函数。
- 当前 execute 侧硬门禁已补齐，具备进入 `-next -auto -type review` 条件。

---

时间：2026-05-07 20:39 +0800
经办人：不要啊教练
任务：T-20260507-bfc9a0e0 / review
结论：最小需改项

审查前置同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`。
- 已执行 `git fetch origin main`。
- 同步基线：`HEAD=673349f53bc3f29e804ff47c2784c57b12aa9d54`，`origin/main=673349f53bc3f29e804ff47c2784c57b12aa9d54`，`merge-base=673349f53bc3f29e804ff47c2784c57b12aa9d54`，ahead/behind=`0/0`。
- 更新结果：待审 worktree 已与 latest `origin/main` 对齐，无需 merge/rebase；未覆盖任务 diff。
- 计划资产：待审 worktree 内缺 `ARCHITECTURE/plan/core_print_alias_dump_green_plan.md`；本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/core_print_alias_dump_green_plan.md` 作为合同真源，未复制/新建/修改计划资产。

真实审查：
- 已读取个人提示词、`AGENTS.md`、`agents/standard/审查规范.md`、主仓共享计划与任务记录。
- 已审查实际 diff 中 `kernel_gen/core/print.py`、dump 接入点、`FunctionAST.input_from_runtime_arg` object 签名清理、`SymbolExprAttr` memory layout 收口、禁止修改面与静态扫描结果。
- `kernel_gen/passes/pass_manager.py`、`kernel_gen/tools/dsl_run.py`、`kernel_gen/tools/ircheck.py` 的 dump 路径已接入公开 `print_operation_with_aliases(...)`；`ircheck` 的 CHECK 匹配文本与 `-irdump` 诊断文本保持分离。
- `expectation/` 与 `.skills/` 在待审 worktree 无 diff / staged diff / untracked diff。

发现：
- 阻断：`spec/core/contracts.md:16`、`spec/core/contracts.md:17`、`spec/core/contracts.md:18` 顶部 API 简表仍保留旧签名：`build_contiguous_stride(shape: Sequence[Attribute]) -> ArrayAttr[Attribute]`、`dims_equal(lhs: Sequence[Attribute], rhs: Sequence[Attribute]) -> bool`、`public_dim_values(dims: Sequence[Attribute]) -> list[int | str]`。同文件详细 API 段与实现已改为 `build_contiguous_stride(shape: Sequence[int]) -> list[int]`、`dims_equal(lhs: Attribute, rhs: Attribute) -> bool`、`public_dim_values(shape: SymbolShape) -> list[int | str]`，导致公开 spec 顶部 API 列表和实现/详细说明互相矛盾。按当前规则，API 列表必须紧跟功能简介且列公开 API 与参数签名，修改实现文件时必须同步维护文件级/API 列表；该不一致不得放行。

最小修复要求：
- 更新 `spec/core/contracts.md` 顶部 API 简表三行，使其与 `kernel_gen/core/contracts.py` 文件级 API 列表及同 spec 的详细 API 段一致。
- 修复后补跑至少 `pytest -q test/core/test_contracts.py test/dsl/ast/nodes/test_basic.py -ra`、`pytest --collect-only -q test`、`git diff --check`、禁止修改面与静态扫描；若 execute 认为无需重跑 full pytest/coverage/full expectation，需在记录中写明基于本轮仅文档签名修复的取舍。

Diff 反推审查：
- `kernel_gen/core/print.py` / `spec/core/print.md` / `test/core/test_print.py`：检查 alias 规则、公开入口、非法输入、round-trip 与 raw attr/type 不污染；定位性 pytest 通过。
- `kernel_gen/passes/pass_manager.py`、`kernel_gen/tools/dsl_run.py`、`kernel_gen/tools/ircheck.py` 与对应 spec/test：检查 dump IR alias 接入与 `ircheck` 匹配文本不被诊断格式污染；定位性 pytest 通过。
- `kernel_gen/dsl/ast/nodes/basic.py` / `spec/dsl/ast/nodes/basic.md` / `test/dsl/ast/nodes/test_basic.py`：检查 `object` 签名收口与测试签名断言；定位性 pytest 通过。
- `SymbolExprAttr` layout 收口相关 diff：抽样检查 `core.contracts`、`dialect`、`dsl/ast/nodes/nn.py`、pass lowering 与测试 helper；静态扫描未见新增 `object` 签名、ctx 能力探测、跨文件私有 helper 导入或非装饰器嵌套函数。
- 审查发现的阻断来自 `spec/core/contracts.md` 顶部 API 简表，不属于 expectation 合同问题。

验证：
- `git fetch origin main` -> 通过；HEAD 与 `origin/main` 均为 `673349f53bc3f29e804ff47c2784c57b12aa9d54`，ahead/behind=`0/0`。
- `python3 -m pytest -q test/core/test_print.py test/passes/test_pass_manager.py test/tools/test_dsl_run.py test/tools/test_ircheck_cli.py -ra` -> `66 passed, 1 warning`。
- `python3 -m pytest -q test/core/test_contracts.py test/dsl/ast/nodes/test_basic.py -ra` -> `21 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test` -> `1989 tests collected in 2.41s`，日志 `/tmp/core_print_alias_review_collect_20260507.log`。
- 固定 full expectation：`PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation` -> 退出码 `0`，日志 `/tmp/core_print_alias_review_full_expectation_20260507.log`。
- 固定 `expectation.core.print`：同上固定 `PYTHONPATH` 运行 `python3 -m expectation.core.print` -> 退出码 `0`，日志 `/tmp/core_print_alias_review_expectation_core_print_fixed_20260507.log`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/core/print.py kernel_gen/core/contracts.py kernel_gen/passes/pass_manager.py kernel_gen/tools/dsl_run.py kernel_gen/tools/ircheck.py kernel_gen/dsl/ast/nodes/basic.py` -> 通过。
- `git diff --check`、`git diff --cached --check` -> 通过。
- `git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills`、`git ls-files --others --exclude-standard -- expectation .skills` -> 均无输出。
- `rg -n "(^|[,( ])[^
]*:\s*object\b|->\s*object\b" kernel_gen test script -g '*.py'` -> 无输出。
- `rg -n "hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)" kernel_gen test spec -g '*.py' -g '*.md'` -> 无输出。
- AST 扫描 modified `kernel_gen/` 与 `kernel/` Python 文件非装饰器嵌套函数 -> 无输出。
- `git diff -- '*.py' | rg '^\+.*from .* import _|^\+.*import .*\._|^\+.*\._[A-Za-z]'` -> 无输出。
- `git diff -U0 -- test | rg '^\+.*(pytest\.skip|skip\(|xfail|no cover|pragma: no cover|deselect|filterwarnings|--cov-fail-under|collect_ignore|pytest_ignore_collect)'` -> 无输出。
- 同类旧 API 签名扫描确认当前直接阻断集中在 `spec/core/contracts.md:16-18`。

未执行项与残余风险：
- 本轮 review 未重复执行 `pytest -q test` 和 coverage 95/80，因为已发现公开 API 简表阻断，结论不会通过；execute 记录中已有 `pytest -q test 1989 passed` 与 coverage `95.00/87.93` 证据。修复后应按修复范围补充记录。

结论：
- `最小需改项`，退回 `execute` 修复 `spec/core/contracts.md` 顶部 API 简表与实现/详细 API 不一致问题。
- 不进入架构复核 / 终验，不 merge。

记录修正：上段验证列表中的 object 签名扫描命令因 Markdown 转义显示换行，实际执行命令为 `rg -n "(^|[,( ])[^^]*:\s*object\b|->\s*object\b" kernel_gen test script -g '*.py'` 的等价扫描；实际结果仍为无输出，审查结论不变。

记录再次修正：上一条记录修正中的 `[^^]*` 为文字笔误，准确 object 签名扫描命令为：
```bash
rg -n '(^|[,(  ])[^\n]*:\s*object\b|->\s*object\b' kernel_gen test script -g '*.py'
```
实际执行结果仍为无输出，审查结论不变。

---

时间：2026-05-07 21:02 +0800
经办人：咯咯咯
任务：T-20260507-bfc9a0e0 / execute 返修
任务目标：修复 review 阻断，统一 `spec/core/contracts.md` 顶部 API 简表中 `build_contiguous_stride`、`dims_equal`、`public_dim_values` 三条签名，并补跑 review 要求的最小 pytest、collect、diff check 与静态扫描。

执行前阅读记录：
- 已重新读取个人提示词 `agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`、仓库根目录 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/协作执行通用规则.md`。
- 已读取主仓 `TODO.md` 中 `T-20260507-bfc9a0e0` 当前任务行，状态为 `execute / 咯咯咯 / 进行中`。
- 已读取本记录末尾 review 结论，确认本轮唯一阻断为 `spec/core/contracts.md` 顶部 API 简表三条签名与实现 / 详细 API 不一致。
- 已核对 `kernel_gen/core/contracts.py` 文件级 API 列表与 `spec/core/contracts.md` 详细 API 段，确认目标签名分别为 `build_contiguous_stride(shape: Sequence[int]) -> list[int]`、`dims_equal(lhs: Attribute, rhs: Attribute) -> bool`、`public_dim_values(shape: SymbolShape) -> list[int | str]`。

前置同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`
- 已执行 `git fetch origin main`。
- `HEAD=673349f53bc3f29e804ff47c2784c57b12aa9d54`
- `origin/main=673349f53bc3f29e804ff47c2784c57b12aa9d54`
- `merge-base=673349f53bc3f29e804ff47c2784c57b12aa9d54`
- `ahead/behind=0/0`
- 更新结果：worktree 已对齐 latest `origin/main`，未 merge/rebase，未覆盖任务 diff。

改动：
- `spec/core/contracts.md`：仅修改顶部 API 简表三行，使其与 `kernel_gen/core/contracts.py` 文件级 API 列表及同 spec 详细 API 段一致：
  - `build_contiguous_stride(shape: Sequence[int]) -> list[int]`
  - `dims_equal(lhs: Attribute, rhs: Attribute) -> bool`
  - `public_dim_values(shape: SymbolShape) -> list[int | str]`
- 未修改 `kernel_gen/`、`test/`、`expectation/`、`.skills/` 或计划书。

最小功能闭环：
- 本轮交付是 spec 公开 API 简表一致性修复，不新增、不删除、不改签公开 API，只把顶部索引修回已经由实现文件和详细 API 定义的签名。
- 失败边界：若三条 API 简表再次回退到旧 `Sequence[Attribute]` / `ArrayAttr[Attribute]` / `dims` 参数名，`rg` 对照与 review 复核会再次发现不一致。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_contracts.py test/dsl/ast/nodes/test_basic.py -ra`：退出码 0，`21 passed, 1 warning in 0.72s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test > /tmp/core_print_alias_execute_contracts_spec_collect_20260507.log && tail -n 5 /tmp/core_print_alias_execute_contracts_spec_collect_20260507.log`：退出码 0，`1989 tests collected in 2.85s`。
- `git diff --check && git diff --cached --check`：退出码 0。
- `git diff --name-only -- expectation .skills && git diff --cached --name-only -- expectation .skills && git ls-files --others --exclude-standard -- expectation .skills`：退出码 0，无输出。
- `rg -n '(^|[,(  ])[^\n]*:\s*object\b|->\s*object\b' kernel_gen test script -g '*.py'`：无输出。
- `rg -n 'hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)' kernel_gen test spec -g '*.py' -g '*.md'`：无输出。
- `git diff -- '*.py' | rg '^\+.*from .* import _|^\+.*import .*\\._|^\+.*\\._[A-Za-z]'`：无输出。
- modified `kernel_gen/` 与 `kernel/` Python 文件 AST 非装饰器嵌套函数扫描：无输出。
- `git diff -U0 -- test | rg '^\+.*(pytest\.skip|skip\(|xfail|no cover|pragma: no cover|deselect|filterwarnings|--cov-fail-under|collect_ignore|pytest_ignore_collect)'`：无输出。
- `rg -n 'build_contiguous_stride\(|dims_equal\(|public_dim_values\(' spec/core/contracts.md kernel_gen/core/contracts.py`：确认顶部 API 简表、详细 API 与实现文件签名一致。

未重跑项：
- 未重跑 `pytest -q test -ra`、coverage 95/80 和固定 full expectation；原因是本轮只修改 `spec/core/contracts.md` 顶部三行 API 简表，未改产品代码、测试代码或合同验收资产。前序 execute 已记录 full pytest、coverage 与 fixed full expectation 通过；本轮按 review 明确要求补跑最小定位 pytest、collect、diff check、禁止修改面与静态扫描。

Diff 反推自测：
- `spec/core/contracts.md`：反推 `pytest -q test/core/test_contracts.py test/dsl/ast/nodes/test_basic.py -ra`、全量 collect、`git diff --check`、API 签名 `rg` 对照和静态扫描。
- `expectation` 未作为 Diff 反推测试；本轮未改 `expectation/`，仅确认 diff / untracked 均为空。

自检：
- 接口：未新增、删除、重命名或修改公开 API；只修正 spec 顶部 API 简表与既有实现 / 详细 API 一致。
- 边界：未修改 `expectation/`、`.skills/`、计划书或任务范围外文件。
- 异常：本轮为文档签名一致性修复，无新增运行时异常路径。
- 兼容：保持前序已通过的 core contracts / dsl basic 行为，不改实现。
- 实现遗漏：review 指出的三条签名不一致已全部修复。
- 冗余与注释：未新增冗余代码或注释；spec 顶部索引仅保留快速签名。
- 复用与函数粒度：不涉及实现函数新增或拆分。
- 输入/输出校验：由 `test/core/test_contracts.py` 继续覆盖公开 contracts 行为。
- 资源/并发/性能：文档修复不涉及资源、并发或性能路径。
- 测试有效性：定位 pytest 与 API 签名对照能覆盖本轮阻断；collect 确认全量测试仍可收集。

结论：review 阻断已修复，具备重新流转 review 条件。

---

时间：2026-05-07 21:04 +0800
经办人：咯咯咯
任务：T-20260507-bfc9a0e0 / execute 返修流转
任务目标：完成 `spec/core/contracts.md` 顶部 API 简表返修后续接 review。
改动：已在主仓根目录执行 `codex-multi-agents-task.sh -next -type review -auto`，任务从 `execute / 咯咯咯` 流转到 `review / 提莫炖蘑菇`。
验证：脚本输出 `OK: next T-20260507-bfc9a0e0`、`OK: auto-dispatch T-20260507-bfc9a0e0 -> 提莫炖蘑菇`、`OK: talk 咯咯咯 -> 提莫炖蘑菇`、`OK: talk 咯咯咯 -> 神秘人`，退出码 0。
TODO 状态：`T-20260507-bfc9a0e0` 当前为 `review / 提莫炖蘑菇 / 进行中`。
自检：流转前已写入 execute 返修记录、验证结果、Diff 反推自测与自检；未修改 `expectation/` 或 `.skills/`。
结论：已进入 review，等待复审。

---

时间：2026-05-07 21:08 +0800
经办人：提莫炖蘑菇
任务：T-20260507-bfc9a0e0 / review 复审
任务目标：复审 `spec/core/contracts.md` 顶部 API 简表返修，确认 `build_contiguous_stride`、`dims_equal`、`public_dim_values` 三条签名已与实现和详细 API 一致，并核对最小 pytest、collect、diff check、禁止修改面与静态扫描记录。

审查前置同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`。
- 已执行 `git fetch origin`。
- 同步基线：`HEAD=673349f53bc3f29e804ff47c2784c57b12aa9d54`，`origin/main=673349f53bc3f29e804ff47c2784c57b12aa9d54`，`merge-base=673349f53bc3f29e804ff47c2784c57b12aa9d54`。
- 更新结果：待审 worktree 已与 latest `origin/main` 对齐，无需 merge/rebase，未覆盖任务 diff。
- 计划资产：待审 worktree 内缺 `ARCHITECTURE/plan/core_print_alias_dump_green_plan.md`；本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/core_print_alias_dump_green_plan.md` 作为合同真源，未复制、新建或修改计划资产。

真实审查：
- 已读取个人提示词、`AGENTS.md`、`agents/standard/审查规范.md`、主仓共享计划、前序 review 记录与 execute 返修记录。
- 已审查 `spec/core/contracts.md`、`kernel_gen/core/contracts.py`、`test/core/test_contracts.py` 的实际 diff。
- `spec/core/contracts.md` 顶部 API 简表当前为：
  - `build_contiguous_stride(shape: Sequence[int]) -> list[int]`
  - `dims_equal(lhs: Attribute, rhs: Attribute) -> bool`
  - `public_dim_values(shape: SymbolShape) -> list[int | str]`
- 上述三条已与 `kernel_gen/core/contracts.py` 文件级 API 列表、函数签名和 `spec/core/contracts.md` 详细 API 段一致。
- `test/core/test_contracts.py` 已同步使用 `SymbolExprAttr` 覆盖 `collect_int_dims` / `dims_equal` / memory type shape-stride 口径，并保留 `IntAttr` 非 memory layout / 负例断言。

发现：
- 无阻断发现。
- 无剩余可执行改进项。

Diff 反推审查：
- 被审 diff：`spec/core/contracts.md`、`kernel_gen/core/contracts.py`、`test/core/test_contracts.py`。
- 反推验证覆盖：
  - `test/core/test_contracts.py` 覆盖 core contracts 公开行为和三条签名相关 helper 行为。
  - `test/dsl/ast/nodes/test_basic.py` 复核前序 `object` 签名收口未回退。
  - `pytest --collect-only -q test` 复核全量测试仍可收集。
  - `git diff --check` 复核文本/空白无问题。
  - `rg` 签名对照复核顶部 API 简表、详细 API 与实现文件一致。
- `expectation` 单列为合同资产；本轮未把 expectation 作为 diff 反推测试，也未修改 expectation。

验证：
- `git fetch origin` -> 通过；`HEAD=origin/main=merge-base=673349f53bc3f29e804ff47c2784c57b12aa9d54`。
- `python3 -m pytest -q test/core/test_contracts.py test/dsl/ast/nodes/test_basic.py -ra` -> `21 passed, 1 warning`。
- `python3 -m pytest --collect-only -q test >/tmp/core_print_alias_review_collect_20260507_again.log && tail -n 3 /tmp/core_print_alias_review_collect_20260507_again.log && git diff --check` -> `1989 tests collected in 2.58s`，`git diff --check` 通过。
- `git diff --name-only -- expectation .skills` -> 无输出。
- `rg -n '(^|[,( ])[^\n]*:\s*object\b|->\s*object\b|hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)' kernel_gen/core/contracts.py spec/core/contracts.md test/core/test_contracts.py -g '*.py' -g '*.md'` -> 无输出。
- `git diff --stat -- spec/core/contracts.md kernel_gen/core/contracts.py test/core/test_contracts.py` -> `3 files changed, 58 insertions(+), 40 deletions(-)`。

禁止修改面：
- `git diff --name-only -- expectation .skills` 无输出。
- 本轮未修改 `expectation/`、`.skills/`、计划书或任务范围外合同资产。
- 未发现新增 `object` 签名、ctx 能力探测、跨文件非公开 API 或非装饰器嵌套函数。

未执行项与残余风险：
- 未重跑 `pytest -q test`、coverage 95/80 和固定 full expectation；原因是本轮复审针对 `spec/core/contracts.md` 顶部 API 简表返修，execute 前序已记录 full pytest、coverage 与 fixed full expectation 通过，本轮最小复核按实际 diff 覆盖。
- 残余风险：无。

自检：
- 已核对任务目标、计划书、记录文件、合同真源和执行人记录。
- 已核对公开 API 简表与实现 / 详细 API 一致。
- 已核对最小 pytest、collect、diff check、禁止修改面和静态扫描。
- 无可执行改进项，结论可写通过。

结论：通过。该任务为计划级任务，review 通过后应进入架构复核 / 终验，不直接进入 merge。

---

时间：2026-05-07 21:30 +0800
经办人：守护最好的爱莉希雅
任务：T-20260507-bfc9a0e0 / 架构复核 / 终验
结论：通过

同步基线：
- `HEAD=origin/main=673349f53bc3f29e804ff47c2784c57b12aa9d54`
- `merge-base=673349f53bc3f29e804ff47c2784c57b12aa9d54`
- `ahead/behind=0/0`
- 更新结果：已安全对齐 latest `origin/main`，未覆盖任务 diff。

计划资产口径：
- 待验 worktree `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` 缺计划资产。
- 本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/core_print_alias_dump_green_plan.md` 作为合同真源。

验证目录：
- `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`

必过 expectation 合同验收：
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation.core.print`：通过。
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation`：通过，退出码 `0`。
- full expectation 日志：`/tmp/core_print_alias_full_expectation_final_20260507_194323.log`。

pytest / coverage / diff check：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test`：`1989 tests collected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test -ra`：`1989 passed, 1 warning`，日志 `/tmp/core_print_alias_terminal_pytest_20260507_211652.log`。
- `PYTHONDONTWRITEBYTECODE=1 coverage run --branch --source=kernel_gen -m pytest -q test` + `script/check_python_coverage.py --include-module kernel_gen --line-min 95 --branch-min 80`：通过，日志 `/tmp/core_print_alias_terminal_coverage_20260507_212348.log`。
- coverage 结果：`kernel_gen` line `95.00%`，branch `87.93%`。
- `git diff --check` / `git diff --cached --check`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/kernelcode_pycache_terminal python3 -m compileall kernel_gen/core kernel_gen/passes/pass_manager.py kernel_gen/tools/dsl_run.py kernel_gen/tools/ircheck.py`：通过。

禁止修改面与静态扫描：
- `git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills`、`git ls-files --others --exclude-standard -- expectation .skills`：均无输出。
- `rg -n '(^|[,( ])[^\n]*:\s*object\b|->\s*object\b' kernel_gen test script -g '*.py'`：无输出。
- `rg -n 'hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)' kernel_gen test spec -g '*.py' -g '*.md'`：无输出。
- `git diff -- '*.py' | rg '^\+.*from .* import _|^\+.*import .*\\._|^\+.*\\._[A-Za-z]'`：无输出。
- `git diff -U0 -- test | rg '^\+.*(pytest\.skip|skip\(|xfail|no cover|pragma: no cover|deselect|filterwarnings|--cov-fail-under|collect_ignore|pytest_ignore_collect)'`：无输出。

结论摘要：
- `core_print_alias_dump_green_plan` 的计划级架构复核 / 终验通过。
- 当前无最小阻断项。
- 可进入 merge/归档流转。

---

时间：2026-05-07 21:32 +0800
经办人：大闸蟹
任务：T-20260507-bfc9a0e0 / 第二架构复核 / 终验
结论：通过

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump`
- 已执行 `git fetch --prune origin`。
- 验证基线：`HEAD=origin/main=merge-base=673349f53bc3f29e804ff47c2784c57b12aa9d54`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 更新结果：待验 worktree 已与 latest `origin/main` 对齐；未 merge/rebase；任务 diff 保留，无同步冲突。

计划资产口径：
- 待验 worktree 内缺 `ARCHITECTURE/plan/core_print_alias_dump_green_plan.md`。
- 本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/core_print_alias_dump_green_plan.md` 作为合同真源；未复制、新建或修改计划资产。

必过 expectation 合同验收：
- 固定 full expectation 命令：
```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```
- 结果：退出码 `0`；日志 `/tmp/core_print_alias_dump_arch_full_expectation_20260507_211242.log`。
- 固定 `expectation.core.print`：同一 `EXPECTATION_WORKTREE_ROOT` 与 `PYTHONPATH` 运行 `python3 -m expectation.core.print`，退出码 `0`，8 个 core print 合同 case 通过。

pytest / coverage / compile / diff check：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test`：`1989 tests collected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_print.py test/passes/test_pass_manager.py test/tools/test_dsl_run.py test/tools/test_ircheck_cli.py`：`66 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test`：`1989 passed, 1 warning`；日志 `/tmp/core_print_alias_dump_arch_pytest_20260507_211700.log`。
- `PYTHONDONTWRITEBYTECODE=1 coverage erase && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test`：`1989 passed, 1 warning`；日志 `/tmp/core_print_alias_dump_arch_coverage_20260507_212321.log`。
- `coverage json -o /tmp/core_print_alias_dump_arch_cov.json` + `script/check_python_coverage.py --include-module kernel_gen --line-min 95 --branch-min 80`：通过，`line=95.00%`，`branch=87.93%`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/kernelcode_pycache python3 -m compileall kernel_gen/core kernel_gen/passes/pass_manager.py kernel_gen/tools/dsl_run.py kernel_gen/tools/ircheck.py`：通过。
- `git diff --check`：通过。

禁止修改面：
- `git diff --name-only -- expectation .skills ARCHITECTURE/plan`：无输出。
- `git diff --cached --name-only -- expectation .skills ARCHITECTURE/plan`：无输出。
- `git -C /home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync status --short -- expectation`：无输出。
- 本轮复核未修改 `expectation/`、`.skills` 或计划书；`expectation` 仅按固定 full expectation 命令作为只读合同资产参与验收。

静态边界扫描：
- dump 默认 alias 入口扫描确认 `PassManager` / `dsl_run` / `ircheck -irdump` 已走 `print_operation_with_aliases(...)`；`Printer.print_op` 命中仅位于 `kernel_gen/core/print.py` alias printer 内部实现或 `ircheck` raw render helper，未发现阻断性绕过。
- 私有 API / ctx 能力探测 / object 签名扫描未发现新增违规：无 `hasattr(ctx|context)` / `getattr(ctx|context)` / `callable(getattr(...))`，无 `object` 参数或返回签名，未发现跨文件导入下划线 helper 的新增 diff。
- 非装饰器嵌套函数扫描未发现新增违规。
- pytest/coverage 配置 diff 扫描未发现降阈值、扩大 omit、隐藏测试、skip/xfail 或过滤门禁规避。
- `NnMemoryType.shape/stride` 旧 `IntAttr/StringAttr` layout 分支重点扫描未发现阻断残留；剩余 `IntAttr/StringAttr` 命中属于 axis / perm / kind / tile metadata / op attribute 等非 memory layout 公开属性或测试负例。

复核结论：
- `core_print_alias_dump_green_plan` 当前计划级第二架构复核 / 终验通过。
- 最小阻断项：无。
- 可进入 `merge/归档` 流转；merge 阶段仍需按管理员流程保持 `expectation` 合同资产权限边界，不得把作废 sync worktree 作为通过依据。

---

时间：2026-05-07 21:56 +0800
经办人：李白
任务：T-20260507-bfc9a0e0 / core_print_alias_dump merge
任务目标：在最新主线基础上安全合并本任务已通过复核 / 终验的业务改动，补齐合并记录并完成 `-done`。
改动：复核目标 worktree `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` 与 `origin/main` 基线一致（`HEAD=origin/main=673349f53bc3f29e804ff47c2784c57b12aa9d54`），确认任务 diff、记录文件与禁止修改面边界一致；本轮未触碰 `expectation/`、`.skills`、`ARCHITECTURE/plan` 或主仓状态文件。合同验收仅复用唯一有效只读 sync 落点 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync`，未使用重复非活动链路 `/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync` 作为通过依据。
验证：
 - `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump:/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync:/home/lfr/kernelcode_generate python3 -m expectation` -> `rc=0`，日志 `/tmp/core_print_alias_merge_full_expectation_20260507_213858.log`
 - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test` -> `1989 tests collected`
 - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_print.py test/passes/test_pass_manager.py test/tools/test_dsl_run.py test/tools/test_ircheck_cli.py -ra` -> `66 passed, 1 warning`
 - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test -ra` -> `1989 passed, 1 warning`，日志 `/tmp/core_print_alias_merge_full_pytest_20260507_214252.log`
 - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen -m pytest -q test -ra` + `script/check_python_coverage.py --include-module kernel_gen --line-min 95 --branch-min 80` -> 通过，`line=95.00%`、`branch=87.93%`
 - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile $(git diff --name-only -- '*.py')` -> 通过
 - `git diff --check` / `git diff --cached --check` -> 通过
 - `git diff --name-only -- expectation .skills ARCHITECTURE/plan agents/standard TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills ARCHITECTURE/plan agents/standard TODO.md DONE.md`、`git status --porcelain -- expectation .skills ARCHITECTURE/plan agents/standard TODO.md DONE.md` -> 均无输出
 - 静态扫描：`object` 签名、`ctx` 能力探测、跨文件下划线 helper 导入、嵌套函数、skip/xfail 与 coverage 配置弱化扫描均未发现新增违规
结论：通过，允许进入 merge/push/-done。

---

时间：2026-05-07 21:58 +0800
经办人：李白
任务：T-20260507-bfc9a0e0 / core_print_alias_dump merge 完成
任务目标：记录本轮实际合并、推送与状态推进结果。
改动：已在主仓 `/home/lfr/kernelcode_generate` 通过 `git merge --ff-only task/core-print-alias-dump` 快进合入任务分支，并执行 `git push origin main`。业务合并提交为 `6f19c67193ae7e1c02e47c2e7b0209e0340475a0`；合入范围为本任务已通过终验的 `kernel/`、`kernel_gen/`、`spec/`、`test/` 改动及本任务记录文件。
验证：
 - `git merge --ff-only task/core-print-alias-dump` -> 通过
 - `git push origin main` -> 通过，`origin/main=6f19c67193ae7e1c02e47c2e7b0209e0340475a0`
 - 主仓禁止修改面：未合入 `expectation/`、`.skills`、`ARCHITECTURE/plan`、`agents/standard`、`TODO.md` 或 `DONE.md` 手工改动
 - 同步资产处理：`/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync` 仅作为终验 / merge 前只读合同验收路径；`/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync` 未引用、未合并、未清理
结论：业务合并与 push 已完成，等待执行 `-done`。

---

时间：2026-05-07 22:01 +0800
经办人：李白
任务：T-20260507-bfc9a0e0 / core_print_alias_dump merge 状态收尾
任务目标：记录 `-done`、管理员回报和任务 worktree / branch 清理结果。
改动：通过任务脚本执行 `-done`，并在主仓清理已完成任务 worktree `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` 与本地分支 `task/core-print-alias-dump`；保留 `/home/lfr/kernelcode_generate/wt-20260507-core-print-alias-expectation-sync` 与 `/home/lfr/kernelcode_generate/wt-20260507-core-print-expectation-contract-sync`，未清理、未合并、未引用其作为新的通过依据。
验证：
 - `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -done -task_id T-20260507-bfc9a0e0 -log agents/codex-multi-agents/log/task_records/2026/19/20260507-core-print-alias-dump.md -agents-list agents/codex-multi-agents/agents-lists.md` -> `OK: done T-20260507-bfc9a0e0`、`OK: replace 李白 状态`
 - `rg -n "T-20260507-bfc9a0e0" TODO.md DONE.md` -> 仅 `DONE.md` 存在已完成记录
 - `git worktree remove /home/lfr/kernelcode_generate/wt-20260507-core-print-alias-dump` + `git branch -D task/core-print-alias-dump` -> 通过
 - `git rev-parse HEAD` / `git rev-parse origin/main` -> `6d63d3e52309541ebfd7e90aa1dcb686350eae06`，本地与远端一致
 - `bash skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -talk -from 李白 -to 神秘人 ...` -> `OK: talk 李白 -> 神秘人 (神秘人)`
结论：T-20260507-bfc9a0e0 已完成 merge/push/-done 与任务 worktree/branch 清理；等待管理员后续归档 / done-plan 流转。
