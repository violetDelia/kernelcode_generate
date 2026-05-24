时间：2026-05-24 20:42
经办人：守护最好的爱莉希雅
任务：arch-parallelize presence guard prefix support / 小任务草案
任务目标：新建一个非计划级 execute 小任务，支持 `kernel/matmul/inputs_dynamic_tile_dynamic.py` 在 `ArchParallelizePass` 前存在 `arith.constant` 与 `memory.get_data -> symbol.cast -> symbol.ne` presence guard setup 的 IR 形态，确保 demo 可以继续跑到源码生成。

改动：
- 用户确认来源：用户在分析 `kernel/matmul/inputs_dynamic_tile_dynamic.py` 未生成源码后，明确要求“新建一个任务支持这个情况。只是小任务，不是计划”。
- 问题定位：
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py` 当前 lowering dump 停在 `kernel/dump/matmul/inputs_dynamic_tile_dynamic/24-canonicalize.mlir`，没有生成 `source.cpp`。
  - 复现失败点为 `ArchParallelizePassError: unsupported loop structure`。
  - `24-canonicalize.mlir` 的 pattern 函数在第一个顶层 `symbol.for` 前含有：
    - `arith.constant`，用于 loop body 内 `dma.fill` 标量；
    - `memory.get_data -> symbol.cast -> symbol.ne`，用于 optional bias / None presence guard；
    - 当前 `ArchParallelizePass` 的 loop prefix 白名单只接受 `symbol.*` setup 与 `arch.get_dynamic_memory` / `dma.view` / `dma.reshape` / `dma.reinterpret`，因此把该合法 setup 前缀判为 unsupported。
- 建议新建小任务：
  - 任务类型：`execute`
  - 任务目标：扩展 `ArchParallelizePass` 支持 `symbol.for` 前的 side-effect-free setup 前缀：`arith.constant`、`memory.get_data`、`symbol.cast`、`symbol.ne`，要求这些 op 的 operands 仍必须来自函数参数或更早已放行 setup result；同步 `spec/pass/arch_parallelize.md` 与公开 pytest，并跑通 `kernel/matmul/inputs_dynamic_tile_dynamic.py` 生成源码。
  - 非目标：不改 `npu-demo-lowering` pipeline 顺序；不新增 pass、registry option 或公开工具参数；不放宽多顶层 loop、loop-carried、multi-block func body、loop 后 setup、未知副作用 op；不修改 `expectation/`。
  - 建议记录文件：`agents/codex-multi-agents/log/task_records/2026/24/20260524-arch-parallelize-presence-prefix.md`，任务 worktree 创建后沿用同一路径写入 worktree。
- 执行人落地边界：
  - `spec/pass/arch_parallelize.md`：补 loop-prefix setup 合同，说明 `arith.constant` 与 presence guard 链只作为 loop 前无副作用/只读 setup，不改变 block 分片语义。
  - `kernel_gen/passes/arch_parallelize/arch_parallelize.py`：扩展 `_is_allowed_loop_prefix_setup_op(...)` 对应 op 类型；保持 `_setup_operands_are_allowed(...)` 的支配/顺序约束。
  - `test/passes/test_arch_parallelize.py`：新增公开入口 pytest，构造动态 memory 参数、bias presence guard 和顶层 `symbol.for`，断言 pass 不再报 `unsupported loop structure` 且外层 loop 被 block-strided rewrite。
  - 视 diff 反推补 `test/passes/pipeline/test_npu_demo_lowering.py` 或 kernel demo gate，但不得直接调用跨文件非公开 helper。

验证：
- 已读当前角色提示词、`AGENTS.md` 用户粘贴版、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：此前复现失败为 `ArchParallelizePassError: unsupported loop structure`，失败发生于 `build_npu_demo_lowering_pipeline().run(module)`，尚未进入 `gen_kernel`。
- `rg -n "class .*GetData|memory.get_data|SymbolCast|symbol.ne|arith.constant" kernel_gen/dialect test spec -S`：确认 `MemoryGetDataOp`、`SymbolCastOp`、`SymbolNeOp` 均为现有公开 dialect API；`arith.constant` 已在现有 pass/test 中作为公开 IR op 使用。
- `find kernel/dump/matmul/inputs_dynamic_tile_dynamic -maxdepth 1 -type f -name 'source.cpp' -print`：当前无输出，符合“未生成源码”的现场。

自检：
- 本轮未修改实现、spec、test、TODO 或 `.skills`。
- 本轮仅形成小任务草案和管理员分发口径；公开行为变化已有用户确认来源，且范围限定为 `ArchParallelizePass` 支持该 presence guard setup 前缀。
- `expectation/` 不纳入本小任务改动范围；如执行发现必须修改 expectation，应暂停回架构裁定。
- 任务目标是可直接执行动作，不使用“整理/看下/继续推进”等泛目标。

结论：可请管理员创建非计划级 execute 小任务；建议任务目标使用上文“扩展 `ArchParallelizePass` 支持 ... 并跑通 `kernel/matmul/inputs_dynamic_tile_dynamic.py` 生成源码”的具体口径。

时间：2026-05-24 21:08
经办人：睡觉小分队
任务：T-20260524-36083d1c / arch-parallelize presence-prefix execute
任务目标：扩展 `ArchParallelizePass` 支持 `symbol.for` 前 side-effect-free setup 前缀 `arith.constant`、`memory.get_data`、`symbol.cast`、`symbol.ne`，同步 spec/pytest，并跑通 `kernel/matmul/inputs_dynamic_tile_dynamic.py` 生成 `source.cpp`。

执行前阅读记录：
- 已读个人提示词、`AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读本记录草案、主仓 `TODO.md` 中 T-20260524-36083d1c 任务行、`spec/pass/arch_parallelize.md`、`kernel_gen/passes/arch_parallelize/arch_parallelize.py`、`test/passes/test_arch_parallelize.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`。
- 当前执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-presence-prefix`；分支：`task/arch-parallelize-presence-prefix`；HEAD：`6bd6e5d9782f92261741a8d46abddd6fd3371617`。

改动：
- `kernel_gen/passes/arch_parallelize/arch_parallelize.py`：将 presence guard 所需 `arith.ConstantOp`、`MemoryGetDataOp`、`SymbolCastOp`、`SymbolNeOp` 纳入 loop 前 setup prefix 白名单；继续复用既有 `_setup_operands_are_allowed(...)`，确保 operand 只来自函数参数或更早已放行 setup result；验证阶段改用 `verify_generated_ops(...)` 包装为 `KernelCodeError`，不直接依赖 `VerifyException`。
- `spec/pass/arch_parallelize.md`：补齐 presence-prefix 合同、依赖真源、operand 支配/顺序边界和 TC-PASS-ARCH-PARALLELIZE-020。
- `test/passes/test_arch_parallelize.py`：新增公开入口 pytest，覆盖 `arith.constant` + `memory.get_data -> symbol.cast -> symbol.ne` 出现在唯一顶层 `symbol.for` 前且不触发 `unsupported loop structure`。
- `kernel/matmul/inputs_dynamic_tile_dynamic.py`：将 demo IR gate 从旧 `dma.view` 更新为当前 pipeline 实际产物 `dma.reinterpret`，保持 source.cpp gate 与 dynamic memory 断言。
- `kernel/matmul/inputs_static_tile_dynamic.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`：同步公开 demo/pytest 中旧 `dma.view` 断言到当前 `dma.reinterpret` / `slice(...)` 生成形态，避免相关公开 pytest 继续锁过期 IR/source 文本。
- 未修改 `expectation/`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`；未改 npu-demo-lowering pipeline；未新增 pass/registry option/工具参数；未放宽多顶层 loop、loop-carried、multi-block、未知副作用 op 边界。

最小功能闭环：
- 实现入口：`ArchParallelizePass` 仍只接受唯一顶层 `symbol.for` 或无 loop 的 block0 guard 场景；新增仅限 loop 前无副作用 / 只读 presence guard setup 前缀。
- 失败边界：loop 后 setup、未知副作用 op、多顶层 loop、loop-carried、multi-block func body 不变；非法结构仍走 `ArchParallelizePassError: unsupported loop structure`。
- kernel gate：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py` exit=0，并确认 `kernel/dump/matmul/inputs_dynamic_tile_dynamic/source.cpp` 存在。

验证：
- 复现旧问题：修改前 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py` 失败于 `KernelCodeError: ArchParallelizePassError: unsupported loop structure`。
- `python3 -m compileall -q kernel_gen/passes/arch_parallelize test/passes/test_arch_parallelize.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/matmul/inputs_static_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/test_pattern_public_api_docs.py`：exit=0，`84 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/kernel/test_matmul_symbolic_memory_genkernel.py`：exit=0，`4 passed, 1 warning`。
- `rm -rf kernel/dump/matmul/inputs_dynamic_tile_dynamic && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py && test -f kernel/dump/matmul/inputs_dynamic_tile_dynamic/source.cpp && ls -l kernel/dump/matmul/inputs_dynamic_tile_dynamic/source.cpp`：exit=0，生成 `source.cpp`，大小 `15958` bytes；stdout 含 `[IR] dynamic memory evidence` 与 absent/present bias `[CHECK]`。
- `git diff --check && git diff --check --cached`：exit=0。
- 敏感目录空 diff：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均无输出。
- 静态边界核对：`rg "from xdsl\\.utils\\.exceptions import VerifyException|raise VerifyException|except VerifyException|hasattr\\(|getattr\\([^\\n]*ctx" kernel_gen/passes/arch_parallelize/arch_parallelize.py -n || true` 无输出；AST 扫描 `kernel_gen/passes/arch_parallelize/arch_parallelize.py` 无嵌套函数。
- `test/repo_conformance/test_private_api_boundaries.py`：本 worktree 不存在，未作为本任务门禁运行。
- 合同验收：本小任务未列 `expectation` 必过资产；未运行 expectation，且候选 diff 中 `expectation/` 为空。

Diff 反推自测：
- 改动 `kernel_gen/passes/arch_parallelize/arch_parallelize.py`、`spec/pass/arch_parallelize.md`、`test/passes/test_arch_parallelize.py`：反推 `compileall` 与 `test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/test_pattern_public_api_docs.py`，覆盖 pass 行为、registry/API 文档一致性和新增 presence-prefix 正例。
- 改动 `kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`：反推 `test/kernel/test_matmul_symbolic_memory_genkernel.py` 与指定 dynamic script gate，覆盖三条 matmul demo 的公开脚本入口、IR/source 断言和 source.cpp 生成。
- `git diff --check` 与敏感目录空 diff 覆盖格式与禁止修改面；expectation 单列为合同资产，未计入 Diff 反推测试。

减法检查：
- 新增 private callable：无。
- 改动 private callable：`_is_allowed_loop_prefix_setup_op(...)` 仅扩展白名单判定，未新增小于 5 行 helper，未引入 private callable 套 private callable。
- 被替代旧逻辑：移除本文件对 `VerifyException` 的直接 import/catch，改用项目公开 `verify_generated_ops(...)` + `KernelCodeError` 口径；`rg` 已确认 arch_parallelize 文件内无 `VerifyException` 直接使用。
- 保留旧逻辑依据：`_setup_operands_are_allowed(...)` 的顺序/支配约束保留，确保新增 presence-prefix 不放宽 loop body、loop 后或未知副作用来源。

自检：
- 接口：未新增公开 API、pass 名称、registry option 或工具参数；spec/API 列表与实现入口一致。
- 边界：只放行任务点名的四类 presence-prefix op，且 operand 来源受既有 allowed-values 顺序约束；多顶层 loop、loop-carried、multi-block、未知副作用、loop 后 setup 边界未放宽。
- 异常：pass verify 失败统一经 `KernelCodeError` 暴露，未继续直接使用 `VerifyException`。
- 兼容性：旧 symbol setup、memory-pool setup、旧 `dma.view`/`dma.reshape` alias 前缀仍在原白名单内；新增逻辑不改变无 loop block0 guard 与已有 block op 跳过行为。
- 实现遗漏：已覆盖 implementation/spec/pytest/kernel demo gate；未发现需要 expectation 或 pipeline 变更。
- 冗余与复用：复用现有 setup operand 检查和 pass rewrite 结构，无新增重复 helper。
- 注释准确性：新增测试注释、spec 合同和实现 helper 注释均明确 presence guard setup 前缀与限制。
- 输入/输出校验：pytest 锁定新增 prefix 出现在 `arch.get_block_id` 前，demo 锁定 source.cpp 生成和 dynamic memory 证据。
- 资源/并发/性能：仅扩展 IR 结构识别，不增加运行时循环或外部资源；kernel demo 实跑通过。
- 测试有效性：Diff 反推测试覆盖 pass 单元、公开 kernel demo pytest、指定脚本 source gate、格式和敏感目录门禁。

结论：execute 已闭环，可流转 review。

时间：2026-05-24 21:21 +0800
经办人：不要啊教练
任务：T-20260524-36083d1c / arch-parallelize presence-prefix review
任务目标：审查 `ArchParallelizePass` presence-prefix 支持、spec/pytest、`inputs_dynamic_tile_dynamic.py` source.cpp gate、Diff 反推自测、敏感目录空 diff 与任务记录。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-presence-prefix`。
- 审查前读取：个人提示词、`AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、本任务记录与主仓 `TODO.md` 任务行。
- `git fetch origin` 后：原 HEAD `6bd6e5d9782f92261741a8d46abddd6fd3371617`，`origin/main=264798461c3830ab6abcfa026ef7be199b25d2f3`，`merge-base=6bd6e5d9782f92261741a8d46abddd6fd3371617`，ahead/behind=`0 1`。
- `origin/main` 新增/修改文件为 `symbol_buffer_hoist` 相关记录/spec/test/实现，与本任务候选文件无交集；已执行 `git merge --ff-only origin/main` 安全对齐。
- 对齐后 HEAD、`origin/main`、`merge-base` 均为 `264798461c3830ab6abcfa026ef7be199b25d2f3`，ahead/behind=`0 0`；任务 diff 未被覆盖。

审查范围：
- 候选 diff：`kernel_gen/passes/arch_parallelize/arch_parallelize.py`、`spec/pass/arch_parallelize.md`、`test/passes/test_arch_parallelize.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`、本任务记录。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 本小任务记录未列 expectation 必过资产；expectation 仅按敏感目录空 diff 核对。

真实审查：
- `arch_parallelize.py` 仅把 `arith.ConstantOp`、`MemoryGetDataOp`、`SymbolCastOp`、`SymbolNeOp` 加入 loop 前 setup prefix 白名单，并继续复用 `_setup_operands_are_allowed(...)` 的函数参数 / 更早 setup result 支配约束；未放宽 loop 后 setup、多顶层 loop、loop-carried、multi-block 或未知副作用 op。
- `ArchParallelizePass.apply(...)` 改为通过公开 `verify_generated_ops([module])` 包装 verifier 失败，未继续跨文件直连 `VerifyException`。
- `spec/pass/arch_parallelize.md` 已同步 presence guard setup 前缀、operand 来源约束、依赖真源与 TC-PASS-ARCH-PARALLELIZE-020。
- `test_arch_parallelize_allows_presence_guard_setup_before_single_loop` 通过公开 `run_ircheck_text(...)` 锁定 `arith.constant -> memory.get_data -> symbol.cast -> symbol.ne` 位于 `arch.get_block_id` 前，覆盖本轮 unblock 场景。
- `inputs_dynamic_tile_dynamic.py` 的 gate 已从旧 `dma.view` 调整为当前 pipeline 实际 `dma.reinterpret`，并由脚本实跑确认生成 `source.cpp`。
- `inputs_static_tile_dynamic.py` 与 `test_matmul_symbolic_memory_genkernel.py` 的 `dma.reinterpret` / `slice(...)` 同步属于相关公开 demo/pytest 文本收口；未改变 kernel 计算逻辑。

Diff 反推审查：
- 反推 `compileall` 覆盖改动实现、spec 对应测试与两个 matmul demo 文件语法。
- 反推 `test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/test_pattern_public_api_docs.py` 覆盖 pass 行为、registry 与公开 API 文档矩阵。
- 反推 `test/kernel/test_matmul_symbolic_memory_genkernel.py` 覆盖三条 matmul demo 的公开脚本入口、IR/source 文本断言和 accumulator 顺序。
- 反推 `kernel/matmul/inputs_dynamic_tile_dynamic.py` 脚本 gate 覆盖本任务点名的 source.cpp 生成现场。
- `expectation` 未作为 Diff 反推测试使用；本任务无当前必过 expectation 入口。

验证：
- `python3 -m compileall -q kernel_gen/passes/arch_parallelize test/passes/test_arch_parallelize.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/matmul/inputs_static_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/test_pattern_public_api_docs.py`：exit=0，`84 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/kernel/test_matmul_symbolic_memory_genkernel.py`：exit=0，`4 passed, 1 warning`。
- `rm -rf kernel/dump/matmul/inputs_dynamic_tile_dynamic && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py && test -f kernel/dump/matmul/inputs_dynamic_tile_dynamic/source.cpp && ls -l kernel/dump/matmul/inputs_dynamic_tile_dynamic/source.cpp`：exit=0，生成 `source.cpp`，大小 `15708` bytes，stdout 含 absent/present bias `[CHECK]`。
- `git diff --check`：exit=0。
- `git diff --check --cached`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均无输出。
- 静态扫描：`rg "from xdsl\.utils\.exceptions import VerifyException|raise VerifyException|except VerifyException|hasattr\(|getattr\([^\n]*ctx|callable\(getattr|_type\b|object\b" ...` 未命中本轮阻断项；`test_arch_parallelize.py` 存量 `hasattr(passes_module, ...)` 是公开 package shape 断言，不是 ctx 能力探测。
- AST 嵌套函数扫描：无命中。

减法审查：
- 本轮替代旧逻辑：`ArchParallelizePass` 不再从实现文件直接 import/catch `VerifyException`，改用项目公开 `verify_generated_ops(...)`；`rg` 已确认候选实现文件无 `VerifyException` 直接使用。
- 本轮改动 private callable：`_is_allowed_loop_prefix_setup_op(...)` 有效代码行数满足不少于 5 行，且未调用其它 private callable。
- 本轮未新增 private callable；候选测试未直连实现文件私有 helper，新增 pass 行为测试走公开 `run_ircheck_text(...)`。
- 保留旧逻辑依据：`_setup_operands_are_allowed(...)`、loop shape 分类、loop 后 setup 失败、多顶层 loop/loop-carried 失败边界均保留，保证新增 presence-prefix 只解锁点名前缀。

findings：
- 无阻断发现。

自检：
- 已读取实际 diff 和任务记录，未只依赖执行摘要。
- 已核对公开 API/spec/test 边界：未新增 pass、registry option、工具参数或 expectation 合同入口；spec/API 列表未引入未确认公开 API。
- 已核对跨文件非公开 API：新增实现依赖均为公开方言 op 类型或公开 pass helper；测试只走公开 pass / runner / demo 入口。
- 已核对测试有效性：新增 pytest 断言 presence guard 前缀必须保留在 `arch.get_block_id` 前，脚本 gate 确认本任务目标 `source.cpp` 生成恢复。
- 已核对敏感目录：`expectation/`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md` 无 diff。
- 残余风险：本任务未运行 full test/full expectation；按任务目标和执行记录，本小任务必需门禁已覆盖。

结论：通过。该任务为用户确认的非计划级小任务，可按普通任务流转 merge；merge 范围应仅包含上述候选 diff 与本任务记录，不得纳入 ignored dump、`expectation/`、`.skills`、`agents/standard` 或状态文件。

时间：2026-05-24 21:28 +0800
经办人：李白
任务：T-20260524-36083d1c / arch-parallelize presence-prefix merge
任务目标：合入已审查通过的 arch-parallelize presence-prefix 支持、spec/test/demo gate 与同批任务记录。

merge 前同步与范围核对：
- 已重新读取个人提示词、`AGENTS.md`、`agents/standard/合并规范.md` 与 `agents/standard/任务记录约定.md`，按 merge 专职职责只做合并与同步确认，不修改实现口径。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-presence-prefix`。
- `git fetch --prune origin` 后，任务 worktree 原 HEAD 为 `264798461c3830ab6abcfa026ef7be199b25d2f3`，`origin/main=dd3d4e9bd8331b67cfbe857b4331c1b398c9d61f`，behind 1。
- 对比 `264798461c3830ab6abcfa026ef7be199b25d2f3..origin/main` 只包含前序 tile-analysis 记录/spec/test/实现，与本任务候选文件无交集；已执行 `git merge --ff-only origin/main` 安全同步。
- 同步后 `HEAD=origin/main=merge-base=dd3d4e9bd8331b67cfbe857b4331c1b398c9d61f`，ahead/behind=`0/0`，候选 diff 保持为本任务范围。
- 合并候选文件：`kernel_gen/passes/arch_parallelize/arch_parallelize.py`、`spec/pass/arch_parallelize.md`、`test/passes/test_arch_parallelize.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py` 与本任务记录。
- 禁止修改面核对：`expectation/`、`.skills/`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`ARCHITECTURE/plan` 无候选 diff；ignored `kernel/dump/**` 和 `__pycache__` 只来自门禁运行，不纳入提交。

Diff 反推自测与合并门禁：
- `python3 -m compileall -q kernel_gen/passes/arch_parallelize test/passes/test_arch_parallelize.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/matmul/inputs_static_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/test_pattern_public_api_docs.py`：exit=0，`84 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/kernel/test_matmul_symbolic_memory_genkernel.py`：exit=0，`4 passed, 1 warning`。
- `rm -rf kernel/dump/matmul/inputs_dynamic_tile_dynamic && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py && test -f kernel/dump/matmul/inputs_dynamic_tile_dynamic/source.cpp && ls -l kernel/dump/matmul/inputs_dynamic_tile_dynamic/source.cpp`：exit=0，生成 `kernel/dump/matmul/inputs_dynamic_tile_dynamic/source.cpp`，大小 `15708` bytes；stdout 含 absent/present bias `[CHECK]`。
- `git diff --check && git diff --cached --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan` 均无输出。
- 静态扫描：AST 嵌套函数扫描对本轮改动 Python 文件无输出；`rg "hasattr\\(ctx|hasattr\\([^\\n]*ctx|getattr\\(ctx|getattr\\([^\\n]*ctx|callable\\(getattr|from xdsl\\.utils\\.exceptions import VerifyException|raise VerifyException|except VerifyException" ...` 无输出。
- `expectation`：本小任务未列必过合同验收资产，未运行 expectation；候选 diff 中 `expectation/` 为空，符合只读合同资产规则。

真实收口结论：
- Review 记录已明确通过，且本轮 latest main 同步后无冲突、无重叠、无敏感目录 diff。
- 任务记录已补入 merge 前真实同步、Diff 反推自测、门禁与禁止修改面核对结果，并将与候选代码/spec/test 同批提交。
- 最小阻断项：无。
