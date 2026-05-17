# T-20260517-26908324 npu-demo memory-plan pipeline execute

## 任务信息

- 任务 ID：`T-20260517-26908324`
- 角色：`金铲铲大作战 / execute`
- worktree：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`
- 分支：`task/npu-demo-memory-plan-pipeline`
- 起点基线：`HEAD=origin/main=merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
- 合同真源：主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md`
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/**`

## 读取与同步

- 已读取最新个人 prompt、`AGENTS.md` 与 `agents/standard` 规则。
- 已按任务要求在 worktree 内确认 `origin/main` 基线；任务开始时 worktree clean。
- 当前 worktree 不携带 `expectation/pass/...` 合同资产；本计划未列必过 expectation 命令，候选 diff 中 `expectation/.skills/agents/standard` 保持为空。

## 实际改动

- `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - 将 `MemoryPlanPass(insert_free=True, fold=False)` 固定接入 `npu-demo-lowering`。
  - 顺序调整为 `inline -> cse -> decompass -> lower-nn -> symbol-loop-hoist -> cse -> memory-plan -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> memory-pool -> symbol-loop-hoist -> symbol-buffer-hoist -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- `kernel_gen/passes/symbol_buffer_hoist.py`
  - 支持同一 owner `symbol.for` 直接 body 内 `dma.alloc + data use + unique dma.free` 安全成对外提。
  - 保持负例 no-op：free 早于 data use、多 free、nested free、非 owner body free、未知 direct use / alias escape。
  - 移除本轮新增 `getattr` 父节点读取，改为直接使用 xDSL 对象公开方法，避免静态扫描误判。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - 针对 `dma.free` 释放 `dma.alloc` 结果的场景，生成 `delete[] value.data();`，使用既有公开 `Memory::data()`，不新增 `npu_demo::free` include 公开 API。
  - 非 alloc memory 值保持既有 `free<Space, T>(...)` 文本路径，不扩大 include API。
- `test/passes/pipeline/test_npu_demo_lowering.py`
  - 订单测试覆盖 `memory-plan:True:False`、两次 `symbol-loop-hoist`、两次 `symbol-buffer-hoist`。
  - 新增真实 dump 阶段测试：`08-memory-plan` 含 `dma.free`、`09-symbol-buffer-hoist` 执行、`12-memory-pool` 不残留 `dma.alloc/dma.free` 并生成 dynamic backing memory。
- `test/passes/test_symbol_buffer_hoist.py`
  - 新增 input staging / output scratch alloc+free 成对外提正例。
  - 新增 free-before-use、多 free、nested free、未知 direct use no-op 负例。
- `test/dsl/gen_kernel/emit/test_package.py`
  - 补 `dma.free` 释放 `dma.alloc` result 的 EmitC 回归，防止生成未公开 include helper 或模板 dtype 不匹配源码。
- `spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/memory_plan.md`、`spec/pass/symbol_buffer_hoist.md`、`spec/pass/symbol_loop_hoist.md`、`spec/pass/pass_manager.md`、`spec/pass/registry.md`
  - 同步 npu-demo-lowering 顺序、memory-plan 接入、symbol-buffer-hoist alloc/free 成对外提边界、PassManager 不做业务顺序校验、registry 描述。

## Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py`
  - 结果：`14 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - 结果：`5 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py -k 'dma_misc_helper_contracts or dma_free_alloc_result'`
  - 结果：`2 passed, 67 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected`

## 计划验收自检

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`169 passed`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`
- `git diff --check`
  - 结果：`exit=0`
- 敏感目录 diff：
  - `git diff --name-only -- expectation .skills agents/standard`：无输出
  - `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出
- 静态扫描：
  - `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py`：`exit=1`，无输出
  - `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`：`exit=1`，无输出
  - 计划文本扫描仍命中既有 tile family 文档/测试说明：`spec/pass/tile/*`、`kernel_gen/passes/tile/__init__.py`、`kernel_gen/passes/lowering/tile.py`、`test/passes/tile/test_package.py`；未命中本轮旧顺序编号和 `SymbolLoopHoistRequiresSymbolFor` 残留。

## 特殊记录

- 一次把 pass 相关 pytest 与 `test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'` 串联在同一 shell 中执行时进程收到 `Signal(11)`；拆分为两条命令后同一覆盖集合均稳定通过：
  - pass/emit 相关：`169 passed`
  - dsl_run 相关：`11 passed`
- `dsl_run` 回归曾暴露 `dma.free` 生成 `free<GM, T1>(Memory<GM, int32_t>)` / 缺少公开 helper 的编译失败；最终没有新增 include public API，改为 alloc result 释放发射 `delete[] value.data();`。

## 自检

- 接口：未新增 pipeline option，`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 保持不变。
- 边界：`symbol-buffer-hoist` 仅放宽计划确认的 alloc/free 成对外提；复杂 alias、nested free、多 free、free-before-use 均保持 no-op。
- 异常：非 module 与 verifier 失败边界不回退。
- 兼容性：`default-lowering` 未修改；registry 仍只透传 options，不解析 pipeline 专属顺序。
- 测试有效性：新增测试均走公开 pass、pipeline builder、emit_c_op 或 dsl_run 入口，不跨文件直连非公开 helper。
- 禁止修改面：`expectation/.skills/agents/standard` 无 diff。

## 结论

- execute 已完成计划内 spec、实现、pytest 与验收闭环。
- 当前无新增阻断，可按流程流转 review。

---

时间：2026-05-17 05:05
经办人：提莫炖蘑菇 / review
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：复审 `npu-demo-lowering` 接入 `MemoryPlanPass(insert_free=True, fold=False)`、memory/symbol/tile pipeline 重排、`symbol-buffer-hoist` 对 `dma.alloc + dma.free` 安全成对外提、spec/test/记录与禁止修改面。

## review 同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`
- 已重新读取个人提示词、`AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`、`agents/standard/协作执行通用规则.md` 与 `agents/standard/实现文件规范.md`。
- 同步命令：`git fetch origin --prune`
- 基线核对：
  - `git rev-parse HEAD` -> `ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-parse origin/main` -> `ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git merge-base HEAD origin/main` -> `ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- 结论：待审 worktree 已在最新 `origin/main` 基线上，未发现需要覆盖任务 diff 的同步动作或冲突风险。

## 被审 diff

- `kernel_gen/passes/pipeline/npu_demo_lowering.py`
- `kernel_gen/passes/symbol_buffer_hoist.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
- `spec/pass/memory_plan.md`
- `spec/pass/pass_manager.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `spec/pass/registry.md`
- `spec/pass/symbol_buffer_hoist.md`
- `spec/pass/symbol_loop_hoist.md`
- `test/dsl/gen_kernel/emit/test_package.py`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/passes/test_symbol_buffer_hoist.py`
- 统计：`12 files changed, 929 insertions(+), 148 deletions(-)`。

## 真实审查

发现：无阻断项。

- `npu-demo-lowering` 顺序与计划正文一致：`Inline -> CSE -> Decompass -> NnLowering -> SymbolLoopHoist -> CSE -> MemoryPlan(insert_free=True, fold=False) -> SymbolBufferHoist -> TileAnalysis -> LowerDmaMemoryHierarchy(fold=True, apply_op='matmul{["", "tlm1", "tlm2"]}') -> MemoryPool(rewrite=True, alignment=0) -> SymbolLoopHoist -> SymbolBufferHoist -> AttachArchInformation -> OutlineDeviceKernel -> TemplateNameInfer`。
- `default-lowering` 未改；`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 公开签名未改；未新增 pipeline option。
- `symbol-buffer-hoist` 仅放宽计划确认的同一 owner `symbol.for` 直接 body 内 `dma.alloc + data use + 唯一 dma.free` 成对外提；free-before-use、多 free、nested free、跨 loop/未知 direct use 仍保持 no-op。
- `dma.free` npu_demo 发射对 `DmaAllocOp` 结果使用 `delete[] value.data()`，未新增未确认 include helper；非 alloc memory 保持既有 `free<Space, T>(...)` 路径。
- spec、实现文件说明/API 列表和测试入口已同步当前公开行为；未发现新增未确认公开 API。
- 测试通过公开 pass、pipeline builder、emit registry/`emit_c_op` 与脚本入口观察行为，未发现跨文件直连非公开 helper。
- 执行记录包含执行前阅读、实际改动、Diff 反推自测、计划验收、自检与禁止修改面核对。

## Diff 反推审查

- Pipeline builder 与 pass 顺序改动：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py`
  - 结果：`5 passed`
  - 断言覆盖：pass 顺序、`memory-plan:True:False`、两次 `symbol-loop-hoist` / `symbol-buffer-hoist`、真实 dump 中 `memory-plan -> symbol-buffer-hoist -> memory-pool` 闭环。
- `symbol-buffer-hoist` alloc/free 成对外提改动：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py`
  - 结果：`14 passed`
  - 断言覆盖：input staging / output scratch 正例，free-before-use、多 free、nested free、unknown direct use、loop-carried shape 等 no-op 负例。
- npu_demo `dma.free` EmitC 发射改动：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dsl/gen_kernel/emit/test_package.py -k 'dma_misc_helper_contracts or dma_free_alloc_result'`
  - 结果：`2 passed, 67 deselected`
  - 断言覆盖：`DmaAllocOp` result 的 `dma.free` 生成 `delete[] value.data()`，不依赖未确认 include helper。
- npu_demo / pipeline / tiled dsl_run 回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected`
- 计划相关组合回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`169 passed`
- 与当前计划前置链路相关的公开 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/operation/test_dma.py test/dialect/test_dma.py test/dsl/ast/nodes/test_dma.py test/dsl/ast/test_mlir_gen.py test/dialect/test_symbol.py test/dialect/test_arch.py test/passes/test_attach_arch_information.py test/target/test_registry.py test/include/api/test_arch.py test/include/npu_demo/test_kernel_context.py test/kernel/test_runner.py test/dsl/ast/test_parser.py test/dsl/ast/test_package.py test/dsl/ast/test_dsl_ast.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`
  - 结果：`397 passed, 2 warnings`
- py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`

## 合同验收与敏感目录

- 当前计划未授权修改 `expectation/`；本轮只用主仓只读 expectation 做合同核验，且不把 expectation 计入 Diff 反推测试。
- 主仓只读合同核验：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/fill.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/fold/min.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/pass/attach_arch_information/launch_attrs.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/pass/attach_arch_information/dynamic_memory_capacity.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.attach_arch_information` -> `exit=0`
- 敏感目录核对：
  - `git diff --name-only -- expectation .skills agents/standard` -> 无输出
  - `git status --short --untracked-files=all -- expectation .skills agents/standard` -> 无输出
  - `git status --short --ignored -- expectation/pass/attach_arch_information .skills agents/standard` -> 无输出
- 格式核对：`git diff --check` -> `exit=0`

## 静态扫描

- `rg -n 'import torch|from torch|torch\.' kernel/runner.py kernel/matmul kernel/conv2d kernel/flash_attention test/kernel spec/kernel` -> 无输出。
- `rg -n 'run_torch_demo|KernelTorchDemoResult' kernel kernel_gen spec test` -> 仅命中公开删除说明或负例测试，不阻断。
- `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec` -> 无输出。
- `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel` -> 无输出。
- `git diff -U0 -- kernel kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'` 人工分类：
  - `test/kernel/test_runner.py` 中 `hasattr` 为旧公开名删除负例，不是 ctx 能力探测。
  - 既有 `getattr(value.__class__, "__module__", "")` 为模块名分类逻辑，不是 ctx 能力探测。
  - 其余 `_specialize/_apply`、同文件 helper 或历史说明命中不构成跨文件非公开 API 调用。

## 自检

- 已逐项读取计划正文、执行记录、实际 diff、实现/spec/test 变更和只读合同验收记录。
- 已按实际 diff 反推并复跑 pipeline、symbol-buffer-hoist、npu_demo `dma.free`、dsl_run 与相关公开 pytest。
- 已核对公开 API、跨文件非公开 API、测试直连非 API、ctx 能力探测、`object` 签名、非装饰器嵌套函数、敏感目录与任务记录完整性。
- 未发现可读性、可维护性、测试有效性或边界完整性上的可执行返工项。

## 结论

- 结论：通过。
- 通过依据：当前 diff 与计划完成态一致，Diff 反推审查和合同核验通过，`expectation/.skills/agents/standard` 无候选 diff，未发现公开 API/非公开 API/测试边界阻断。
- 下一步：该任务属于计划级任务，review 通过后应由管理员流转架构复核 / 终验；review 不直接进入 merge。

---

时间：2026-05-17 05:20
经办人：守护最好的爱莉希雅 / 架构复核终验
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：按计划级完成态复核 `npu-demo-lowering` 接入 `MemoryPlanPass(insert_free=True, fold=False)`、pipeline 顺序、`symbol-buffer-hoist` alloc/free 成对外提、主仓只读 expectation、Diff 反推测试和禁止修改面。

## 终验同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`
- 已重新读取 worktree 内 `AGENTS.md`、当前角色提示词、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md` 与 `agents/standard/spec文件规范.md`。
- 同步命令：`git fetch --prune origin`
- 基线核对：
  - `git rev-parse HEAD` -> `ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-parse origin/main` -> `ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git merge-base HEAD origin/main` -> `ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- 候选 diff：12 个计划范围文件 + 本任务记录，`expectation/`、`.skills/`、`agents/standard/**` 无 tracked、staged、untracked 或 ignored diff。

## 发现

- 最小需改项：计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md:185`、`:190`、`:193`、`:199` 明确要求 `symbol-buffer-hoist` 覆盖 “free 不在同一 owner loop body / 外层 / sibling loop” no-op 负例，并点名 `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body`；当前候选测试只覆盖 free 早于 data use、多 free、nested free、未知 direct use，见 `test/passes/test_symbol_buffer_hoist.py:689`、`:706`、`:723`、`:742`，缺少该计划点名负例。实现代码在 `kernel_gen/passes/symbol_buffer_hoist.py:263` 到 `:266` 对 parent block mismatch 会保守 no-op，行为方向看起来正确，但缺少公开 pytest 锁定 `spec/pass/symbol_buffer_hoist.md:157` 的 `non owner body` 合同。影响：计划完成态和测试矩阵不闭合，后续若改坏外层 / sibling loop free 的 no-op 边界，现有测试不会失败。最小返工动作：新增公开构造用例和 `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body`，覆盖 alloc/data use 在 owner loop body、matching `dma.free` 位于 owner loop 外层或 sibling block 时 alloc/free 均保持原位；同步 `spec/pass/symbol_buffer_hoist.md` 测试表或当前 TC-008 命令清单包含该测试名。验收方式：`pytest -q test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'` 通过，且全量计划 pytest 保持通过。

## 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py` -> `169 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'` -> `11 passed, 27 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py` -> `exit=0`
- `git diff --check` 与 `git diff --cached --check` -> `exit=0`
- 主仓只读 expectation，`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate`：
  - `python3 /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/fill.py` -> `exit=0`
  - `python3 /home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/fold/min.py` -> `exit=0`
  - `python3 /home/lfr/kernelcode_generate/expectation/pass/attach_arch_information/launch_attrs.py` -> `exit=0`
  - `python3 /home/lfr/kernelcode_generate/expectation/pass/attach_arch_information/dynamic_memory_capacity.py` -> `exit=0`
  - `python3 -m expectation.pass.attach_arch_information` -> `exit=0`
- 导入边界探针：`kernel_gen.passes.pipeline.npu_demo_lowering` 与 `kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree；`expectation.pass.attach_arch_information` 为主仓 namespace package 入口，具体脚本按主仓绝对路径运行。
- 前置链路公开 pytest：首次 `timeout=120s` 超时无退出码；用 `timeout=360s` 复跑同一命令后 `397 passed, 2 warnings`。
- 静态扫描：
  - `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes` -> 仅命中 tile family canonical path 文档 / 测试说明和 registry 条目，未命中旧顺序或 `SymbolLoopHoistRequiresSymbolFor`。
  - `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py` -> 无输出。
  - `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec` -> 无输出。
  - `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel` -> 无输出。
  - `git diff -U0 -- kernel kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'` -> 命中均为本轮删除旧 `getattr(...)` / `object()` 负例，不构成新增阻断。
- 禁止修改面：
  - `git diff --name-only -- expectation .skills agents/standard` -> 无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard` -> 无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 无输出。

## 自检

- 已按最新同步现场核对计划正文、执行记录、review 记录、实际 diff、实现/spec/test 变更和主仓只读 expectation。
- 已按计划与实际 diff 复跑 pipeline、symbol-buffer-hoist、memory-plan、registry、pass-manager、emit、dsl_run、前置链路公开 pytest、py_compile、静态扫描和禁止修改面。
- 已核对公开 API 边界：未新增 pipeline option，`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 保持不变，`default-lowering` 未改；`SymbolBufferHoistPass(fold: bool = True)` 已在现有公开基类能力范围内写入 spec。
- 已核对测试入口未直连跨文件私有 helper；本轮新增测试 helper 均在同一测试文件内服务公开 pass / pipeline 入口。
- 残余风险：除上方点名缺失的 `free_not_in_owner_loop_body` 公开负例外，未发现其它可执行返工项。

## 结论

- 结论：最小需改项，不通过终验；通过前不得 merge。
- 下一步：回 `execute` 补齐 `free_not_in_owner_loop_body` 公开 pytest 与 spec 测试表命令清单，再由 review 复审后重新请求双架构终验。

---

时间：2026-05-17 05:17
经办人：大闸蟹
任务：T-20260517-26908324 / npu-demo memory-plan pipeline / 计划级架构复核与终验
任务目标：按计划书 `ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md` 对 review 通过后的候选 diff 做计划级终验，复跑计划必过 pytest、真实 pipeline/dsl_run、只读 expectation 核验、静态边界和敏感目录门禁，并写回终验结论。

## 终验同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`。
- 终验前重新读取：根 `AGENTS.md`、个人提示词 `agents/codex-multi-agents/agents/大闸蟹/大闸蟹.prompt.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- 只读计划真源：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md`。
- `git fetch origin --prune` 后核对：
  - `HEAD=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `origin/main=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-list --left-right --count HEAD...origin/main` 为 `0 0`
- 当前候选 diff：12 个业务/spec/test 文件，统计 `929 insertions(+), 148 deletions(-)`；本任务记录文件当前仍为 untracked，见 merge gate。

## 终验核对

- `npu-demo-lowering` 实现顺序与计划一致：`inline -> cse -> decompass -> lower-nn -> symbol-loop-hoist -> cse -> memory-plan(insert_free=True, fold=False) -> symbol-buffer-hoist -> tile-analysis -> lower-dma-memory-hierarchy -> memory-pool -> symbol-loop-hoist -> symbol-buffer-hoist -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- `default-lowering` 未改；`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 签名未改；未新增 pipeline option。
- `symbol-buffer-hoist` 改动限定在计划范围：同一 owner `symbol.for` 直接 body 内 `dma.alloc + data use + 唯一合法 dma.free` 成对外提；free-before-use、多 free、nested free、未知 direct use / alias escape 保持 no-op。
- `npu_demo dma.free` 对 `DmaAllocOp` 结果发射 `delete[] value.data()`，未新增未确认 include helper；非 alloc memory 仍走既有 `free<Space, T>(...)` 文本路径。
- `SymbolBufferHoistPass(fold: bool = True)` 是基类 `Pass` 已有构造能力，本轮 spec/API 列表对齐实际公开签名；实测 `SymbolBufferHoistPass(fold=False).fold is False`。

## Diff 反推终验

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`169 passed, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or memory_plan_dump'`
  - 结果：`2 passed, 3 deselected, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py -k 'matching_free or free_precedes or multiple_free or free_is_nested or unknown_direct_use'`
  - 结果：`6 passed, 8 deselected, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_registry.py -k 'memory_plan or npu_demo_lowering or builtin'`
  - 结果：`7 passed, 40 deselected, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_pass_manager.py -k 'business_order or surviving_import_matrix or pass_manager'`
  - 结果：`15 passed, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py -k pass_order`
  - 结果：`1 passed, 4 deselected, 1 warning`，exit=0。
- 前置链路公开 pytest 组合：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/operation/test_dma.py test/dialect/test_dma.py test/dsl/ast/nodes/test_dma.py test/dsl/ast/test_mlir_gen.py test/dialect/test_symbol.py test/dialect/test_arch.py test/passes/test_attach_arch_information.py test/target/test_registry.py test/include/api/test_arch.py test/include/npu_demo/test_kernel_context.py test/kernel/test_runner.py test/dsl/ast/test_parser.py test/dsl/ast/test_package.py test/dsl/ast/test_dsl_ast.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`
  - 结果：`397 passed, 2 warnings`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：exit=0。

## 合同验收

- 当前计划未授权修改 `expectation/`，本轮只做主仓只读 expectation 核验，且不计入 Diff 反推测试。
- 导入边界：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate`；`expectation.*` 来自主仓，`kernel_gen.*` 来自任务 worktree。
- 主仓只读核验：
  - `python3 /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/fill.py` -> exit=0。
  - `python3 /home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/fold/min.py` -> exit=0。
  - `python3 /home/lfr/kernelcode_generate/expectation/pass/attach_arch_information/launch_attrs.py` -> exit=0。
  - `python3 /home/lfr/kernelcode_generate/expectation/pass/attach_arch_information/dynamic_memory_capacity.py` -> exit=0。
  - `python3 -m expectation.pass.attach_arch_information` -> exit=0。
  - `python3 -m expectation.pass.memory_plan` -> exit=0。
- import 证明：
  - `expectation.dsl.mlir_gen.dialect.dma.fill` -> `/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/fill.py`
  - `expectation.dialect.symbol.operation.fold.min` -> `/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/fold/min.py`
  - `expectation.pass.attach_arch_information.launch_attrs` -> `/home/lfr/kernelcode_generate/expectation/pass/attach_arch_information/launch_attrs.py`
  - `expectation.pass.attach_arch_information.dynamic_memory_capacity` -> `/home/lfr/kernelcode_generate/expectation/pass/attach_arch_information/dynamic_memory_capacity.py`
  - `kernel_gen.passes.pipeline.npu_demo_lowering` -> `/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline/kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `kernel_gen.passes.symbol_buffer_hoist` -> `/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline/kernel_gen/passes/symbol_buffer_hoist.py`
  - `kernel_gen.dsl.gen_kernel.emit.npu_demo.dma.free` -> `/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline/kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`

## 静态与敏感目录

- `git diff --check && git diff --cached --check` -> exit=0。
- `git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --untracked-files=all -- expectation .skills agents/standard`、`git status --short --ignored -- expectation .skills agents/standard` -> 均无输出，exit=0。
- `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes`
  - 命中仅为 tile family 自身文档 / 测试说明、`kernel_gen/passes/tile/__init__.py` canonical helper 说明、`kernel_gen/passes/lowering/tile.py` 历史 wrapper 说明、`spec/pass/registry.md` / `spec/pass/pass_manager.md` 的当前合法描述；未命中 `SymbolLoopHoistRequiresSymbolFor` 或旧 dump 序号残留。
- `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py` -> 无输出，exit=1。
- `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec` -> 无输出，exit=1。
- `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel` -> 无输出，exit=1。
- diff 级扫描 `git diff -U0 -- kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'` 仅命中删除行：删除旧 `getattr(...)` 父节点读取和删除 `object()` 测试输入，非阻断。

## 记录与 merge gate

- `git ls-files --others --exclude-standard` 当前仅显示本任务记录：`agents/codex-multi-agents/log/task_records/2026/20/20260517-npu-demo-memory-plan-pipeline.md`。
- 该任务记录当前在 worktree 中仍为 untracked；终验通过不代替 merge 阶段同批合并核对。
- merge 前必须把本任务记录与代码/spec/test 候选 diff 同批纳入提交；若记录仍未纳入候选 / staged diff，merge 应阻断。
- merge 前仍需复核 `expectation/.skills/agents/standard` 空 diff、最新 `origin/main` 同步现场和候选 diff。

## 自检

- 已按计划正文和实际 diff 反推测试，未只依赖 review 摘要。
- 已核对公开 API：pipeline builder 签名、pipeline option 未新增；`SymbolBufferHoistPass(fold=False)` 为基类已有公开构造能力，本轮只对齐 spec/API 列表。
- 已核对实现未跨文件调用非公开 helper；测试使用公开 pass、pipeline、emit 和 dsl_run 入口，未直连业务私有 helper。
- 已区分普通 pytest 与主仓只读 expectation 合同验收；未修改、复制、新建或删除 `expectation/`。
- 已核对敏感目录空 diff；本轮架构终验只追加任务记录，未修改业务实现、spec、测试、计划或合同资产。

## 结论

- 通过。T-20260517-26908324 当前计划级架构复核 / 终验无阻断项，可通知管理员进入后续 merge 前准备。
- 进入 merge 前必须纳入当前未跟踪任务记录，并按合并规范重新核对最新主线、候选 diff、敏感目录空 diff和同批记录证据。

---

时间：2026-05-17 05:24
经办人：守护最好的爱莉希雅 / 架构复核终验结论重申
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：在记录尾部明确守护侧当前有效终验结论，避免与大闸蟹 05:17 通过结论混读。

## 当前有效结论

- 结论：最小需改项，不通过守护侧终验；通过前不得 merge。
- 与大闸蟹意见差异：大闸蟹 05:17 记录给出通过；守护侧 05:20 终验记录指出计划点名的 `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 未落入候选测试矩阵。双架构终验未同时通过，按流程不能进入 merge。
- 最小返工动作：回 `execute` 新增公开 pytest `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body`，覆盖 alloc/data use 在 owner `symbol.for` body、matching `dma.free` 位于 owner loop 外层或 sibling block 时 alloc/free 均保持原位；同步 `spec/pass/symbol_buffer_hoist.md` 测试表或 TC-008 命令清单包含该测试名。
- 验收方式：`pytest -q test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'` 通过，且计划 pytest、主仓只读 expectation、静态扫描和敏感目录空 diff 仍通过后重新发起 review / 双架构终验。

---

时间：2026-05-17 08:23:38 CST
经办人：金铲铲大作战 / execute 返工
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：按守护侧终验最小需改项，补齐 `symbol-buffer-hoist` 的 `free_not_in_owner_loop_body` no-op 公开 pytest 与 `spec/pass/symbol_buffer_hoist.md` TC-008 测试索引，保持计划 pytest、主仓只读 expectation、静态扫描和敏感目录空 diff 不回退。

## 返工改动

- `test/passes/test_symbol_buffer_hoist.py`
  - 新增 `_build_slice_with_free_not_in_owner_loop_body_module()`，构造 alloc 与 `dma.slice` data use 位于 owner `symbol.for` 直接 body、matching `dma.free` 位于同一 owner loop 内 sibling nested block 的公开 IR 负例。
  - 新增 `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body`，断言 pass 后顶层无 alloc/free、owner loop 内 alloc 与 data use 保持原位、nested block 内 free 仍释放同一 alloc result。
  - 将原未知 direct use 用例编号顺延为 `TC-SYMBOL-BUFFER-HOIST-004G`，避免测试编号重复。
- `spec/pass/symbol_buffer_hoist.md`
  - 更新 TC-PASS-SYMBOL-BUFFER-HOIST-008，把 `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 纳入 no-op 边界与建议命令。

## Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`
  - 覆盖：守护侧点名返工测试、nested free、多 free、free 早于 data use、未知 direct use no-op 边界。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`
  - 覆盖：计划 pass / pipeline / registry / pass manager / emit 相关 pytest，包含新增 `symbol-buffer-hoist` 负例。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`
  - 覆盖：npu-demo lowering / pipeline / tiled 公开脚本链路。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`

## 合同验收

- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`
  - 输出覆盖：`passes-memory_plan-invalid-dynamic-lifetime`、`passes-memory_plan-invalid-call-boundary`、`passes-memory_plan-lifecycle-static-1`、`passes-memory_plan-lifecycle-static-2`、`passes-memory_plan-lifecycle-dynamic`、`passes-memory_plan-lifecycle-call-boundary`。
- 本轮未修改、复制、新建、移动或删除 `expectation/`，expectation 仅作为主仓合同真源读取与运行。

## 静态扫描与禁止修改面

- `git diff --check` -> `exit=0`
- `git diff --name-only -- expectation .skills agents/standard` -> 无输出
- `git status --short --untracked-files=all -- expectation .skills agents/standard` -> 无输出
- `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes`
  - 结果：仅命中 tile family canonical path 文档 / 测试说明和 registry 条目；未命中旧 `npu-demo-lowering` 顺序、旧 dump 序号或 `SymbolLoopHoistRequiresSymbolFor`。
- `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - 结果：无输出
- `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec`
  - 结果：无输出
- `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel`
  - 结果：无输出
- `git diff -U0 -- kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'`
  - 结果：仅命中本轮候选 diff 中删除的旧 `getattr(...)` 与删除的 `object()` 负例输入，不构成新增阻断。

## 当前候选 diff

- 业务/spec/test 候选 diff：
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `kernel_gen/passes/symbol_buffer_hoist.py`
  - `spec/pass/memory_plan.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/pass/symbol_buffer_hoist.md`
  - `spec/pass/symbol_loop_hoist.md`
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_symbol_buffer_hoist.py`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/20/20260517-npu-demo-memory-plan-pipeline.md`
- 当前统计：`12 files changed, 993 insertions(+), 148 deletions(-)`，任务记录仍为 untracked 候选文件，需随业务/spec/test 同批纳入后续 review / merge。

## 自检

- 已重新核对守护侧 05:24 最小需改项、计划正文 S3 / S5、实际 diff和当前 worktree 状态。
- 已补齐计划点名的 `free_not_in_owner_loop_body` 公开 pytest，且测试只通过公开 `SymbolBufferHoistPass` 入口观察行为；新增 helper 仅在当前测试文件内服务公开 API 用例。
- 未改公开 API、未新增 pipeline option、未改 `default-lowering`，未触碰 `expectation/`、`.skills/`、`agents/standard/**`。
- 已按实际 diff 反推运行目标 pytest、计划 pytest、dsl_run 相关 pytest、py_compile、主仓只读 expectation、静态扫描和禁止修改面核对。
- 未发现新的可执行返工项。

## 结论

- 结论：execute 返工完成，可回流 review。
- 回流依据：守护侧点名测试缺口已补齐，TC-008 已同步，目标 pytest、计划 pytest、主仓只读 expectation、静态扫描和敏感目录空 diff 均通过。

---

时间：2026-05-17 08:37:07 CST
经办人：金铲铲大作战 / execute 复审返工
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：按提莫炖蘑菇 review 复审最小需改项，修正 `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 的 IR 形态，避免与既有 `free_is_nested` 等价，真正覆盖 owner loop 内 sibling region block 边界；同步 `spec/pass/symbol_buffer_hoist.md` TC-008 并复跑点名 pytest、计划 pytest、主仓只读 expectation、静态扫描和敏感目录空 diff。

## 复审阻断

- 问题：上一轮新增 `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 把 matching `dma.free` 放在 nested `symbol.for` body 内，与既有 `test_symbol_buffer_hoist_keeps_alloc_when_free_is_nested` 的 IR 形态等价。
- 影响：虽然目标 pytest、计划 pytest、主仓只读 `expectation.pass.memory_plan`、`git diff --check` 和敏感目录空 diff 均通过，但测试有效性不足，未能独立锁定守护侧要求的 “free 不在 owner loop 直接 body / sibling block” 边界。
- 最小返工动作：将该测试改为使用 `scf.if` sibling region block：alloc 与 `dma.slice` data use 位于 owner `symbol.for` 直接 body，matching `dma.free` 位于同一 owner loop 内的 `scf.if` true-region block。

## 改动

- `test/passes/test_symbol_buffer_hoist.py`
  - 为测试文件增加公开 xDSL `scf` dialect import，并使用公开 `SymbolEqOp` 构造 `scf.if` 条件。
  - `_build_slice_with_free_not_in_owner_loop_body_module()` 由 nested `symbol.for` free 改为 `scf.IfOp(condition.result, [], Region(free_block), None)`，其中 `free_block` 包含 `DmaFreeOp(alloc.result)` 与 `scf.YieldOp()`。
  - `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 改为查找 `scf.IfOp` true-region，断言 `dma.slice` 仍引用 owner loop body 内 alloc、`dma.free` 仍位于 sibling region block 并释放同一 alloc result，顶层和 owner loop 直接 body 不出现被错误外提的 free。
- `spec/pass/symbol_buffer_hoist.md`
  - TC-PASS-SYMBOL-BUFFER-HOIST-008 场景更新为 “free 位于 owner loop 内 `scf.if` sibling region block”，避免继续写成与 nested free 等价的泛化描述。

## Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`
  - 覆盖：`scf.if` sibling region block free、nested `symbol.for` free、多 free、free 早于 data use、未知 direct use no-op 边界。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`
  - 覆盖：计划 pass / pipeline / registry / pass manager / emit 相关 pytest。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`
  - 覆盖：npu-demo lowering / pipeline / tiled 公开脚本链路。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`

## 合同验收

- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`
  - 输出覆盖：`passes-memory_plan-invalid-dynamic-lifetime`、`passes-memory_plan-invalid-call-boundary`、`passes-memory_plan-lifecycle-static-1`、`passes-memory_plan-lifecycle-static-2`、`passes-memory_plan-lifecycle-dynamic`、`passes-memory_plan-lifecycle-call-boundary`。
- 本轮未修改、复制、新建、移动或删除 `expectation/`，expectation 仅作为主仓合同真源读取与运行。

## 静态扫描与禁止修改面

- `git diff --check` -> `exit=0`
- `git diff --name-only -- expectation .skills agents/standard` -> 无输出
- `git status --short --untracked-files=all -- expectation .skills agents/standard` -> 无输出
- `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes`
  - 结果：仅命中 tile family canonical path 文档 / 测试说明和 registry 条目；未命中旧 `npu-demo-lowering` 顺序、旧 dump 序号或 `SymbolLoopHoistRequiresSymbolFor`。
- `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - 结果：无输出
- `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec`
  - 结果：无输出
- `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel`
  - 结果：无输出
- `git diff -U0 -- kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'`
  - 结果：仅命中本轮候选 diff 中删除的旧 `getattr(...)` 与删除的 `object()` 负例输入，不构成新增阻断。

## 当前候选 diff

- 业务/spec/test 候选 diff：
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `kernel_gen/passes/symbol_buffer_hoist.py`
  - `spec/pass/memory_plan.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/pass/symbol_buffer_hoist.md`
  - `spec/pass/symbol_loop_hoist.md`
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_symbol_buffer_hoist.py`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/20/20260517-npu-demo-memory-plan-pipeline.md`
- 当前统计：`12 files changed, 1007 insertions(+), 150 deletions(-)`，任务记录仍为 untracked 候选文件，需随业务/spec/test 同批纳入后续 review / merge。

## 自检

- 已重新核对提莫复审最小需改项、计划正文 S3 / S5、实际 diff 和当前 worktree 状态。
- 已确认 `SymbolForOp.verify_()` 只支持 single-block region，不能用多 block owner loop 构造 sibling block；本轮改用合法 `scf.if` sibling region block 覆盖 parent-block mismatch，避免与 nested `symbol.for` free 等价。
- 新增测试只通过公开 `SymbolBufferHoistPass` 入口观察行为；新增 helper 仅在当前测试文件内服务公开 API 用例。
- 未改公开 API、未新增 pipeline option、未改 `default-lowering`，未触碰 `expectation/`、`.skills/`、`agents/standard/**`。
- 已按实际 diff 反推运行目标 pytest、计划 pytest、dsl_run 相关 pytest、py_compile、主仓只读 expectation、静态扫描和禁止修改面核对。
- 未发现新的可执行返工项。

## 结论

- 结论：execute 复审返工完成，可回流 review。
- 回流依据：新增测试已从 nested `symbol.for` 改为 `scf.if` sibling region block，TC-008 已同步，目标 pytest、计划 pytest、主仓只读 expectation、静态扫描和敏感目录空 diff 均通过。

---

时间：2026-05-17 08:30
经办人：提莫炖蘑菇 / review 复审
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：复审 execute 针对守护侧终验最小需改项的返工：`test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 与 `spec/pass/symbol_buffer_hoist.md` TC-008 是否真正覆盖 free 不在 owner loop 直接 body 的 no-op 边界。

## 复审同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`
- 已重新读取个人提示词、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`。
- 同步命令：`git fetch origin --prune`
- 基线核对：
  - `HEAD=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `origin/main=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- 结论：待审 worktree 已对齐最新主线；当前无同步冲突或覆盖任务 diff 的风险。

## Findings

- 最小需改项：[`test/passes/test_symbol_buffer_hoist.py`](/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline/test/passes/test_symbol_buffer_hoist.py):378 新增 `_build_slice_with_free_not_in_owner_loop_body_module()` 与已有 `_build_slice_with_nested_free_module()` 形态等价，二者都把 `dma.free` 放在 owner loop body 内的 nested `SymbolForOp` block 中；[`test/passes/test_symbol_buffer_hoist.py`](/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline/test/passes/test_symbol_buffer_hoist.py):786 的新增测试因此只重复覆盖 nested free，不覆盖守护侧退回记录要求的“matching `dma.free` 位于 owner loop 外层或 sibling block”边界。影响：TC-008 虽然列入 [`spec/pass/symbol_buffer_hoist.md`](/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline/spec/pass/symbol_buffer_hoist.md):281，但测试矩阵仍缺一个与 nested free 不同的非 owner-body free 场景，错误实现仍可能被重复测试假绿覆盖。最小返工动作：将 `free_not_in_owner_loop_body` 夹具改成与 `free_is_nested` 不同的合法公开 IR 形态，明确覆盖 free 不在 owner `symbol.for` 直接 body 的外层 / sibling block 边界；若该 IR 在当前 verifier 下不可合法构造，则需把不可构造原因写入记录并请架构师裁定 TC-008 是否改为仅保留 nested free。验收方式：`pytest -q test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested'` 必须能证明两个用例的 IR 结构不同，并继续通过计划 pytest、静态扫描和敏感目录空 diff。

## Diff 反推审查

- 目标返工 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`
  - 复审判断：命令通过，但新增 `free_not_in_owner_loop_body` 与既有 `free_is_nested` 形态重复，测试有效性不足，不能作为守护侧点名缺口已闭合的证据。
- 计划 pass / pipeline / registry / pass manager / emit 组合：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`
- 主仓只读合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`
- 格式与敏感目录：
  - `git diff --check` -> `exit=0`
  - `git diff --name-only -- expectation .skills agents/standard` -> 无输出
  - `git status --short --untracked-files=all -- expectation .skills agents/standard` -> 无输出
- 静态扫描：
  - `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes` -> 仅命中 tile family / registry / pass_manager 当前合法说明。
  - `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py` -> 无输出。
  - `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec` -> 无输出。
  - `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel` -> 无输出。
  - `git diff -U0 -- kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'` -> 仅命中删除旧 `getattr(...)` 和删除旧 `object()` 测试输入，不构成新增阻断。

## 自检

- 已按最新主线现场复审，不基于过期 review 结论放行。
- 已读取实际 residual diff、守护侧退回记录、execute 返工记录和新增测试/spec。
- 已复跑目标 pytest、计划组合 pytest、主仓只读 expectation、格式检查、敏感目录检查和静态扫描。
- 当前阻断不是命令失败，而是新增测试与既有 nested free 用例重复，未证明 TC-008 的非 owner-body free 边界。

## 结论

- 结论：最小需改项，不通过。
- 下一步：回 `execute` 收口 `free_not_in_owner_loop_body` 的测试有效性，或在无法构造合法 IR 时请架构师裁定并更新 TC-008 / 任务记录口径；通过前不得进入架构终验或 merge。

---

时间：2026-05-17 08:37:07 CST
经办人：金铲铲大作战 / execute 复审返工
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：按提莫炖蘑菇 08:30 review 复审最小需改项，修正 `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 的 IR 形态，避免与既有 `free_is_nested` 等价，真正覆盖 owner loop 内 sibling region block 边界；同步 `spec/pass/symbol_buffer_hoist.md` TC-008 并复跑点名 pytest、计划 pytest、主仓只读 expectation、静态扫描和敏感目录空 diff。

## 改动

- `test/passes/test_symbol_buffer_hoist.py`
  - 为测试文件增加公开 xDSL `scf` dialect import，并使用公开 `SymbolEqOp` 构造 `scf.if` 条件。
  - `_build_slice_with_free_not_in_owner_loop_body_module()` 由 nested `symbol.for` free 改为 `scf.IfOp(condition.result, [], Region(free_block), None)`，其中 `free_block` 包含 `DmaFreeOp(alloc.result)` 与 `scf.YieldOp()`。
  - `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 改为查找 `scf.IfOp` true-region，断言 `dma.slice` 仍引用 owner loop body 内 alloc、`dma.free` 仍位于 sibling region block 并释放同一 alloc result，顶层和 owner loop 直接 body 不出现被错误外提的 free。
- `spec/pass/symbol_buffer_hoist.md`
  - TC-PASS-SYMBOL-BUFFER-HOIST-008 场景更新为 “free 位于 owner loop 内 `scf.if` sibling region block”，避免继续写成与 nested free 等价的泛化描述。

## Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`
  - 覆盖：`scf.if` sibling region block free、nested `symbol.for` free、多 free、free 早于 data use、未知 direct use no-op 边界。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`

## 合同验收

- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`
  - 输出覆盖：`passes-memory_plan-invalid-dynamic-lifetime`、`passes-memory_plan-invalid-call-boundary`、`passes-memory_plan-lifecycle-static-1`、`passes-memory_plan-lifecycle-static-2`、`passes-memory_plan-lifecycle-dynamic`、`passes-memory_plan-lifecycle-call-boundary`。
- 本轮未修改、复制、新建、移动或删除 `expectation/`，expectation 仅作为主仓合同真源读取与运行。

## 静态扫描与禁止修改面

- `git diff --check` -> `exit=0`
- `git diff --name-only -- expectation .skills agents/standard` -> 无输出
- `git status --short --untracked-files=all -- expectation .skills agents/standard` -> 无输出
- `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes`
  - 结果：仅命中 tile family canonical path 文档 / 测试说明和 registry 条目；未命中旧 `npu-demo-lowering` 顺序、旧 dump 序号或 `SymbolLoopHoistRequiresSymbolFor`。
- `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - 结果：无输出
- `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec`
  - 结果：无输出
- `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel`
  - 结果：无输出
- `git diff -U0 -- kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'`
  - 结果：仅命中本轮候选 diff 中删除的旧 `getattr(...)` 与删除的 `object()` 负例输入，不构成新增阻断。

## 自检

- 已重新核对提莫复审最小需改项、计划正文 S3 / S5、实际 diff 和当前 worktree 状态。
- 已确认 `SymbolForOp.verify_()` 只支持 single-block region，不能用多 block owner loop 构造 sibling block；本轮改用合法 `scf.if` sibling region block 覆盖 parent-block mismatch，避免与 nested `symbol.for` free 等价。
- 新增测试只通过公开 `SymbolBufferHoistPass` 入口观察行为；新增 helper 仅在当前测试文件内服务公开 API 用例。
- 未改公开 API、未新增 pipeline option、未改 `default-lowering`，未触碰 `expectation/`、`.skills/`、`agents/standard/**`。
- 已按实际 diff 反推运行目标 pytest、计划 pytest、dsl_run 相关 pytest、py_compile、主仓只读 expectation、静态扫描和禁止修改面核对。
- 未发现新的可执行返工项。

## 结论

- 结论：execute 复审返工完成，可回流 review。
- 回流依据：新增测试已从 nested `symbol.for` 改为 `scf.if` sibling region block，TC-008 已同步，目标 pytest、计划 pytest、主仓只读 expectation、静态扫描和敏感目录空 diff 均通过。

---

时间：2026-05-17 09:03 CST
经办人：不要啊教练 / review 复审
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：复审 execute 对 `free_not_in_owner_loop_body` 测试有效性返工：确认用例已从 nested `symbol.for` 改为 `scf.if` sibling region block，`spec/pass/symbol_buffer_hoist.md` TC-008 已同步，并核对点名 pytest、计划 pytest、dsl_run、主仓只读 `expectation.pass.memory_plan`、格式检查、静态扫描和禁止修改面。

## review 前置同步

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`。
- 已重新读取根 `AGENTS.md`、个人提示词、`agents/standard/审查规范.md` 与 `agents/standard/任务记录约定.md`。
- 同步命令：`git fetch origin main`。
- 基线核对：
  - `HEAD=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `origin/main=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- 覆盖风险核对：`origin/main` 相对 `HEAD` 无新增文件差异；任务 diff 与 untracked 任务记录无主线重叠，未执行会覆盖任务 diff 的同步动作。
- 计划真源：待审 worktree 内缺 `ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md`，本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md`；未复制、修改或新建计划资产。

## Findings

无阻断项。

- `test/passes/test_symbol_buffer_hoist.py` 中 `_build_slice_with_free_not_in_owner_loop_body_module()` 现使用 `scf.IfOp(condition.result, [], Region(free_block), None)`，matching `dma.free` 位于 owner `symbol.for` 直接 body 内的 `scf.if` true-region block；既有 `free_is_nested` 仍使用 nested `SymbolForOp`，两者 IR 形态已区分。
- `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 通过公开 `SymbolBufferHoistPass` 入口执行，断言顶层无 alloc/free、owner loop 直接 body 内仍有 alloc 和 data use、`dma.free` 仍在 `scf.if` true-region 并释放同一 alloc result，能锁住 parent-block mismatch 的 no-op 边界。
- `spec/pass/symbol_buffer_hoist.md` TC-008 已将场景同步为 free 位于 owner loop 内 `scf.if` sibling region block，并保留 free-before-use、多 free、nested free、未知 direct use 的同组 no-op 验收。
- 本轮未新增公开 pipeline option，未修改 `default-lowering`；`SymbolBufferHoistPass(fold: bool = True)` 只是对基类已有公开构造参数的 spec/API 对齐，不是新增实现入口。
- 测试没有跨文件直连 `symbol_buffer_hoist.py` 的非公开 helper；新增 helper 均位于同一测试文件内服务公开 pass 行为断言。
- 未发现跨文件非公开 API、ctx 能力探测、非装饰器嵌套函数、`object` 签名或未授权 `expectation/.skills/agents/standard` diff。

## Diff 反推审查

- 返工点名 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`。
  - 核对点：覆盖 `scf.if` sibling region block free、nested `symbol.for` free、多 free、free 早于 data use、未知 direct use no-op 边界。
- 计划 pass / pipeline / registry / pass manager / emit 组合：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`。
- dsl_run 相关回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`。
- py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`。

## 合同验收与门禁

- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`。
  - 输出覆盖：`passes-memory_plan-invalid-dynamic-lifetime`、`passes-memory_plan-invalid-call-boundary`、`passes-memory_plan-lifecycle-static-1`、`passes-memory_plan-lifecycle-static-2`、`passes-memory_plan-lifecycle-dynamic`、`passes-memory_plan-lifecycle-call-boundary`。
- 格式检查：`git diff --check && git diff --cached --check` -> `exit=0`。
- 禁止修改面：
  - `git diff --name-only -- expectation .skills agents/standard` -> 无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard` -> 无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard` -> 无输出。
- 旧口径扫描：`rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes` 仅命中 tile family 当前合法说明与 registry/pass_manager 现行描述，未命中旧 `npu-demo-lowering` 顺序、旧 dump 序号或 `SymbolLoopHoistRequiresSymbolFor`。
- 静态扫描：
  - `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec` -> 无输出。
  - `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel` -> 无输出。
  - `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py` -> 无输出。

## 自检

- 已按最新主线现场复审，不沿用过期通过或不通过结论。
- 已读取计划正文、前序 review/终验记录、execute 返工记录和实际 residual diff。
- 已核对 `free_not_in_owner_loop_body` 与 `free_is_nested` 的 IR 形态差异，并确认测试会在错误外提该 `scf.if` region free 时失败。
- 已区分 diff 反推 pytest 与主仓只读 expectation 合同验收；未修改、复制、新建、移动或删除 `expectation/`。
- 当前仍需 merge 阶段把本任务记录与业务/spec/test diff 同批纳入候选提交；review 结论不替代 merge gate。

## 结论

- 结论：通过。
- 通过依据：守护侧与提莫点名的测试有效性缺口已收口，TC-008 已同步，Diff 反推审查、主仓只读 expectation、格式检查、静态扫描和敏感目录门禁均通过，未发现剩余可执行返工项。
- 下一步：该任务为计划级任务，review 通过后应回报管理员接双架构复核 / 终验；review 不直接续接 merge。

---

时间：2026-05-17 08:54 CST
经办人：守护最好的爱莉希雅 / 架构复核与终验
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：按最新 review 复审通过现场，复跑计划必过 pytest、主仓只读 `expectation.pass.memory_plan`、导入边界、静态扫描与禁止修改面，并给出计划级架构终验结论。

## 终验前置同步

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`。
- 已重新读取根 `AGENTS.md`、当前角色提示词、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md` 与 `agents/standard/expectation任务规则.md`。
- 当前名单核对：`agents/codex-multi-agents/agents-lists.md` 中守护最好的爱莉希雅为当前 session `019e2ebd-d924-74c2-bc05-76fcf3ceb9a4`。
- 基线核对：
  - `HEAD=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `origin/main=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- 计划真源：只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md`，未复制、修改或新建计划资产。

## 终验 Findings

无阻断项。

- `free_not_in_owner_loop_body` 已使用 `scf.IfOp` sibling region block 构造 matching `dma.free`，与 `free_is_nested` 的 nested `SymbolForOp` 场景区分明确。
- `SymbolBufferHoistPass` 生命周期配套保持公开入口测试：安全 `alloc + free` 成对外提；free 早于 data use、多 free、nested free、`scf.if` region free、未知 direct use 均 no-op。
- `npu-demo-lowering` 顺序与计划目标一致：第二个 CSE 后插入 `MemoryPlanPass(insert_free=True, fold=False)`，第一次 `SymbolBufferHoistPass` 位于 memory-plan 后，memory-pool 后追加第二次 `SymbolLoopHoistPass` 与 `SymbolBufferHoistPass`。
- `SymbolBufferHoistPass(fold: bool = True)` 是对基类 `Pass` 既有公开构造参数的 spec/API 列表对齐，未新增实现入口、pipeline option 或 registry option。
- 未发现跨文件调用非公开 helper、测试直连实现私有 helper、ctx 能力探测、非装饰器嵌套函数或未确认公开 API 扩展。

## 终验命令

- 点名回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`
- 计划组合 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`
- dsl_run 相关回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`
- py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`
- 格式检查：
  - `git diff --check && git diff --cached --check`
  - 结果：`exit=0`

## 主仓 expectation 与导入边界

- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`
  - 输出覆盖：`passes-memory_plan-invalid-dynamic-lifetime`、`passes-memory_plan-invalid-call-boundary`、`passes-memory_plan-lifecycle-static-1`、`passes-memory_plan-lifecycle-static-2`、`passes-memory_plan-lifecycle-dynamic`、`passes-memory_plan-lifecycle-call-boundary`
- 导入边界探针：
  - `kernel_gen.passes.symbol_buffer_hoist -> /home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline/kernel_gen/passes/symbol_buffer_hoist.py`
  - `kernel_gen.passes.pipeline.npu_demo_lowering -> /home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline/kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `expectation.pass.memory_plan.__main__ -> /home/lfr/kernelcode_generate/expectation/pass/memory_plan/__main__.py`

## 静态扫描与敏感目录

- 旧口径扫描：
  - `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes`
  - 结果：仅命中 tile family canonical path 文档 / 测试说明和 registry 条目；未命中旧 `npu-demo-lowering` 顺序、旧 dump 序号或 `SymbolLoopHoistRequiresSymbolFor`。
- touched 文件静态扫描：
  - `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - 结果：无输出
- ctx 能力探测扫描：
  - `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec`
  - 结果：无输出
- 嵌套函数扫描：
  - `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel`
  - 结果：无输出
- diff 级扫描：
  - `git diff -U0 -- kernel kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'`
  - 结果：仅命中本轮删除的旧 `getattr(...)` 和删除的 `object()` 负例输入。
- 禁止修改面：
  - `git diff --name-only -- expectation .skills agents/standard` -> 无输出
  - `git diff --cached --name-only -- expectation .skills agents/standard` -> 无输出
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 无输出

## 候选 diff 核对

- 业务/spec/test 候选 diff：
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `kernel_gen/passes/symbol_buffer_hoist.py`
  - `spec/pass/memory_plan.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/pass/symbol_buffer_hoist.md`
  - `spec/pass/symbol_loop_hoist.md`
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_symbol_buffer_hoist.py`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/20/20260517-npu-demo-memory-plan-pipeline.md` 当前为 worktree 未跟踪文件；merge 前必须与上述业务/spec/test diff 同批纳入候选提交，不得代码先合后补记录。
- 当前 `git diff --cached --name-only` 为空；终验未执行 stage 操作，merge 角色需在合并门禁中重新核对 staged/candidate diff 包含任务记录。

## 终验结论

- 结论：通过，可进入 merge 前准备。
- 通过依据：计划必过 pytest、Diff 反推测试、主仓只读 `expectation.pass.memory_plan`、导入边界、静态扫描、格式检查与敏感目录空 diff 均已通过；最新 `free_not_in_owner_loop_body` 修复覆盖有效，未发现剩余计划级阻断项。
- merge 前保留门禁：重新确认 latest `origin/main`，纳入任务记录同批提交，复核 `expectation/`、`.skills/`、`agents/standard/**` 空 diff。

---

时间：2026-05-17 08:56 CST
经办人：大闸蟹 / 架构复核与终验
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：按管理员最新 review 复审通过现场，重新执行计划级架构复核 / 终验，核对 `free_not_in_owner_loop_body` 返工、计划必过 pytest、主仓只读 `expectation.pass.memory_plan`、导入边界、静态边界、禁止修改面与同批合并门禁。

## 终验同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`。
- 终验前重新读取：根 `AGENTS.md`、个人提示词 `agents/codex-multi-agents/agents/大闸蟹/大闸蟹.prompt.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- 计划真源：只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md`；未复制、修改或新建计划资产。
- `git fetch origin --prune` 后核对：
  - `HEAD=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `origin/main=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- 候选 diff：12 个业务 / spec / test 文件处于 modified；本任务记录当前为 untracked。终验未执行 stage 或 merge。

## Findings

无阻断项。

- `test/passes/test_symbol_buffer_hoist.py` 已新增 `_build_slice_with_free_not_in_owner_loop_body_module()`，matching `dma.free` 位于 owner `symbol.for` 内的 `scf.if` sibling region block；`free_is_nested` 仍覆盖 nested `SymbolForOp`，两个边界不再混淆。
- `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 通过公开 `SymbolBufferHoistPass` 入口断言 alloc / data use 留在 owner loop body，`dma.free` 留在 `scf.if` true-region，锁住非 owner body no-op 合同。
- `spec/pass/symbol_buffer_hoist.md` 已同步 TC-008，明确 free-before-use、多 free、nested free、`scf.if` sibling region free、未知 direct use 均保持 no-op。
- `npu-demo-lowering` 顺序与计划目标一致，`MemoryPlanPass(insert_free=True, fold=False)` 位于第二个 CSE 后，第一次 `SymbolBufferHoistPass` 位于 memory-plan 后，`MemoryPoolPass` 后追加第二次 `SymbolLoopHoistPass` 与 `SymbolBufferHoistPass`。
- 未发现新增未确认公开 API、pipeline option、registry option、跨文件非公开 API 调用、测试直连实现私有 helper、ctx 能力探测或非装饰器嵌套函数。

## 验证

- 基线同步：
  - `git fetch origin --prune && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main` -> `HEAD=origin/main=merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`，`0 0`。
- 点名返工 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`。
- 计划组合 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`。
- dsl_run 回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`。
- 真实 pipeline / registry / pass manager 切片：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py` -> `5 passed, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or memory_plan_dump'` -> `2 passed, 3 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_registry.py -k 'memory_plan or npu_demo_lowering or builtin'` -> `7 passed, 40 deselected, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_pass_manager.py -k 'business_order or surviving_import_matrix or pass_manager'` -> `15 passed, 1 warning`。
- 广域前置公开链路：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/operation/test_dma.py test/dialect/test_dma.py test/dsl/ast/nodes/test_dma.py test/dsl/ast/test_mlir_gen.py test/dialect/test_symbol.py test/dialect/test_arch.py test/passes/test_attach_arch_information.py test/target/test_registry.py test/include/api/test_arch.py test/include/npu_demo/test_kernel_context.py test/kernel/test_runner.py test/dsl/ast/test_parser.py test/dsl/ast/test_package.py test/dsl/ast/test_dsl_ast.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`
  - 结果：`397 passed, 2 warnings`。
- py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`。
- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`，输出覆盖 `passes-memory_plan-invalid-dynamic-lifetime`、`passes-memory_plan-invalid-call-boundary`、`passes-memory_plan-lifecycle-static-1`、`passes-memory_plan-lifecycle-static-2`、`passes-memory_plan-lifecycle-dynamic`、`passes-memory_plan-lifecycle-call-boundary`。
- 导入边界：
  - `expectation.pass.memory_plan.__main__`、`lifecycle`、`invalid` 均来自 `/home/lfr/kernelcode_generate/expectation/pass/memory_plan/`。
  - `kernel_gen.passes.pipeline.npu_demo_lowering`、`kernel_gen.passes.symbol_buffer_hoist`、`kernel_gen.dsl.gen_kernel.emit.npu_demo.dma.free` 均来自任务 worktree。
  - 导入边界探针第一次使用 `import expectation.pass...` 语法失败，因为 `pass` 是 Python 关键字；已改用 `importlib.import_module(...)` 复跑成功。
- 格式与禁止修改面：
  - `git diff --check && git diff --cached --check` -> `exit=0`。
  - `git diff --name-only -- expectation .skills agents/standard` -> 无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard` -> 无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 无输出。
- 静态扫描：
  - `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes` -> 仅命中 tile family canonical path 文档 / 测试说明和 registry/pass_manager 现行条目；未命中旧 `npu-demo-lowering` 顺序、旧 dump 序号或 `SymbolLoopHoistRequiresSymbolFor`。
  - `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py` -> 无输出。
  - `rg -n 'hasattr\([^\n]*ctx|getattr\([^\n]*ctx|callable\(getattr\([^\n]*ctx' kernel_gen kernel test spec` -> 无输出。
  - `rg -n --multiline 'def [A-Za-z0-9_]+\([^)]*\):\n[[:space:]]+def ' kernel_gen test kernel` -> 无输出。
  - `git diff -U0 -- kernel kernel_gen spec test include | rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]|def .+\(.*object'` -> 仅命中本轮删除的旧 `getattr(...)` 与删除的 `object()` 负例输入。

## 自检

- 已按最新同步现场复核，不沿用上一轮通过 / 不通过结论。
- 已核对计划正文、最新 review 复审记录、实际 diff、实现 / spec / test 变更和主仓只读 expectation。
- 已确认 `free_not_in_owner_loop_body` 测试会在错误外提 `scf.if` region free 时失败，且与 nested `symbol.for` 场景分离。
- 已区分 diff 反推 pytest 与 expectation 合同验收；本轮未修改、复制、新建、移动或删除 `expectation/`。
- 当前保留 merge 前门禁：本任务记录仍为 untracked，merge 角色必须将记录与业务 / spec / test diff 同批纳入候选 / staged diff；若记录未纳入，应阻塞 merge。

## 结论

- 结论：通过，可进入 merge 前准备。
- 通过依据：最新 review 点名返工已闭环，计划组合 pytest、dsl_run、广域公开链路、主仓只读 `expectation.pass.memory_plan`、导入边界、py_compile、格式检查、静态扫描与敏感目录空 diff 均通过，未发现剩余可执行阻断项。
- 未执行：未 stage、未 merge。

---

时间：2026-05-17 09:23 CST
经办人：守护最好的爱莉希雅 / 架构复核与终验复核
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：按管理员最新要求，对本轮返工后的候选重新给出守护侧明确终验结论；复核 `free_not_in_owner_loop_body`、点名 pytest、计划组合、dsl_run、主仓只读 `expectation.pass.memory_plan`、py_compile、diff check、敏感目录空 diff 与静态扫描。

## 同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`。
- 已重新读取：根 `AGENTS.md`、当前角色提示词、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- 计划真源：只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_memory_plan_pipeline_green_plan.md`；未复制、修改或新建计划资产。
- `git fetch origin --prune` 后核对：
  - `HEAD=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `origin/main=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- 候选状态：12 个业务 / spec / test 文件 modified，本任务记录 untracked；本轮终验未 stage、未 merge。

## Findings

无阻断项。

- `test/passes/test_symbol_buffer_hoist.py` 中 `_build_slice_with_free_not_in_owner_loop_body_module()` 使用 `scf.IfOp(condition.result, [], Region(free_block), None)`，matching `dma.free` 位于 owner `symbol.for` 内的 sibling region block；`free_is_nested` 仍使用 nested `SymbolForOp`，两个边界已分离。
- `test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body` 通过公开 `SymbolBufferHoistPass` 执行，断言 alloc/data use 留在 owner loop body，`dma.free` 留在 `scf.if` true-region。
- `spec/pass/symbol_buffer_hoist.md` TC-008 已明确 `scf.if` sibling region free、多 free、free-before-use、nested free、unknown direct use 均保持 no-op。
- `npu-demo-lowering` 实现中 `MemoryPlanPass(insert_free=True, fold=False)` 位于第二个 CSE 后，第一次 `SymbolBufferHoistPass` 位于 memory-plan 后，memory-pool 后有第二次 `SymbolLoopHoistPass` 与 `SymbolBufferHoistPass`，与计划目标一致。
- 未发现新增 pipeline option、registry option、未确认公开 API、跨文件非公开 API 调用、测试直连实现私有 helper、ctx 能力探测或非装饰器嵌套函数。

## 验证

- 点名返工 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`
- 计划组合 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`
- dsl_run 回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`
- py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`
- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`，输出覆盖 `passes-memory_plan-invalid-dynamic-lifetime`、`passes-memory_plan-invalid-call-boundary`、`passes-memory_plan-lifecycle-static-1`、`passes-memory_plan-lifecycle-static-2`、`passes-memory_plan-lifecycle-dynamic`、`passes-memory_plan-lifecycle-call-boundary`。
- 导入边界：
  - `kernel_gen.passes.symbol_buffer_hoist` -> 任务 worktree。
  - `kernel_gen.passes.pipeline.npu_demo_lowering` -> 任务 worktree。
  - `kernel_gen.dsl.gen_kernel.emit.npu_demo.dma.free` -> 任务 worktree。
  - `expectation.pass.memory_plan.__main__` -> `/home/lfr/kernelcode_generate/expectation/pass/memory_plan/__main__.py`。
- 格式检查：
  - `git diff --check && git diff --cached --check` -> `exit=0`
- 敏感目录：
  - `git diff --name-only -- expectation .skills agents/standard` -> 无输出
  - `git diff --cached --name-only -- expectation .skills agents/standard` -> 无输出
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 无输出
- 静态扫描：
  - 旧口径扫描仅命中 tile family canonical path 文档 / 测试说明和 registry 条目；未命中旧 `npu-demo-lowering` 顺序、旧 dump 序号或 `SymbolLoopHoistRequiresSymbolFor`。
  - touched 文件 `hasattr/getattr/callable/object/from _/._` 扫描无输出。
  - ctx 能力探测扫描无输出。
  - 非装饰器嵌套函数扫描无输出。
  - diff 级扫描仅命中本轮删除的旧 `getattr(...)` 和删除的 `object()` 负例输入。

## 自检

- 已基于当前同步现场复核，不以既有通过记录替代本轮结论。
- 已检查实际候选 diff、计划完成态、最新 review 记录与大闸蟹终验记录。
- 已确认 `free_not_in_owner_loop_body` 的 `scf.if` sibling region block 测试有效，并区别于 nested `symbol.for`。
- 已区分 diff 反推 pytest 与主仓只读 expectation 合同验收；本轮未修改、复制、新建、移动或删除 `expectation/`。
- merge 前仍需将当前 untracked 任务记录与业务 / spec / test diff 同批纳入候选 / staged diff；若未纳入，应阻塞 merge。

## 结论

- 结论：通过，可进入 merge 前准备。
- 通过依据：本轮点名返工、计划组合、dsl_run、主仓只读 `expectation.pass.memory_plan`、导入边界、py_compile、diff check、敏感目录空 diff 与静态扫描均通过，未发现剩余可执行阻断项。
- 未执行：未 stage、未 merge。

---

时间：2026-05-17 10:02 CST
经办人：李白 / merge
任务：T-20260517-26908324 / npu-demo memory-plan pipeline
任务目标：按 merge 角色合入双架构计划级终验通过的 npu-demo memory-plan pipeline 候选 diff，确保任务记录与业务 / spec / test 同批提交、推送并执行 `-done`。

## merge 同步现场

- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md` 与 `agents/standard/expectation任务规则.md`。
- 合并来源 worktree：`/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline`，分支 `task/npu-demo-memory-plan-pipeline`。
- `git fetch --prune origin` 后核对：
  - 主仓 `/home/lfr/kernelcode_generate`：`HEAD=origin/main=merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`。
  - 任务 worktree：`HEAD=origin/main=merge-base=ac0f46ab6b0e15d9335dfa1e91c18cced44ff1d9`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 主仓存在无关未跟踪文件 `ARCHITECTURE/reference/conv2d_xpu_ir_flow_compare.md` 与本任务 worktree 目录；本次合并未读取为候选 diff、未纳入提交。

## 候选范围

- 业务 / spec / test 候选 diff 共 12 个 modified 文件：
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `kernel_gen/passes/symbol_buffer_hoist.py`
  - `spec/pass/memory_plan.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/pass/symbol_buffer_hoist.md`
  - `spec/pass/symbol_loop_hoist.md`
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_symbol_buffer_hoist.py`
- 同批记录文件：`agents/codex-multi-agents/log/task_records/2026/20/20260517-npu-demo-memory-plan-pipeline.md`。该文件在 merge 前仍为 worktree untracked，本次已补 merge 记录，后续必须与上述 12 个文件同批 `git add` / commit。
- 不纳入范围：`expectation/`、`.skills/`、`agents/standard/**`、`TODO.md`、`DONE.md`、`ARCHITECTURE/plan/**` 均未出现在任务 diff/status 中。

## merge 前验证

- 点名返工 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py -k 'free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or unknown_direct_use'`
  - 结果：`5 passed, 10 deselected, 1 warning`。
- 计划组合 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_plan.py test/passes/test_registry.py test/passes/test_pass_manager.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`170 passed, 1 warning`。
- dsl_run 回归：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/tools/test_dsl_run.py -k 'npu_demo or pipeline or tiled'`
  - 结果：`11 passed, 27 deselected, 1 warning`。
- py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：`exit=0`。
- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-npu-demo-memory-plan-pipeline:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：`exit=0`，输出覆盖 `passes-memory_plan-invalid-dynamic-lifetime`、`passes-memory_plan-invalid-call-boundary`、`passes-memory_plan-lifecycle-static-1`、`passes-memory_plan-lifecycle-static-2`、`passes-memory_plan-lifecycle-dynamic`、`passes-memory_plan-lifecycle-call-boundary`。
- 导入边界：
  - `expectation.pass.memory_plan.__main__`、`lifecycle`、`invalid` 均来自 `/home/lfr/kernelcode_generate/expectation/pass/memory_plan/`。
  - `kernel_gen.passes.pipeline.npu_demo_lowering`、`kernel_gen.passes.symbol_buffer_hoist`、`kernel_gen.dsl.gen_kernel.emit.npu_demo.dma.free` 均来自任务 worktree。
- 格式与禁止修改面：
  - `git diff --check && git diff --cached --check`：`exit=0`。
  - `git diff --name-only -- expectation .skills agents/standard TODO.md DONE.md ARCHITECTURE/plan`：无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard TODO.md DONE.md ARCHITECTURE/plan`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard TODO.md DONE.md ARCHITECTURE/plan`：无输出。
- 旧口径扫描：
  - `rg -n 'not enter|不进入.*npu-demo-lowering|SymbolLoopHoistRequiresSymbolFor|tile[-_ ]family|lower-dma-memory-hierarchy.*symbol-loop-hoist|symbol-loop-hoist.*lower-dma-memory-hierarchy|08-tile-analysis|09-lower-dma-memory-hierarchy|10-symbol-buffer-hoist|11-memory-pool' spec/pass kernel_gen/passes test/passes`
  - 结果：仅命中 tile family canonical path 文档 / 测试说明和 registry 条目；未命中旧 `npu-demo-lowering` 顺序、旧 dump 序号或 `SymbolLoopHoistRequiresSymbolFor`。
- touched 文件静态扫描：
  - `rg -n 'hasattr\(|getattr\(|callable\(|\bobject\b|from [^\n]+ import _|\._[A-Za-z]' kernel_gen/passes/pipeline/npu_demo_lowering.py kernel_gen/passes/symbol_buffer_hoist.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_symbol_buffer_hoist.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
  - 结果：无输出。
- ctx 能力探测扫描与非装饰器嵌套函数扫描均无输出。
- diff 级禁用写法扫描 `git diff -U0 -- kernel kernel_gen spec test include | rg -n ...` 仅命中本轮删除的旧 `getattr(...)` 和删除的 `object()` 负例输入，不构成新增违规。

## 结论

- merge 前核对通过。
- 当前无冲突、无未授权敏感目录改动、无缺失记录；下一步将 12 个业务 / spec / test 文件与本任务记录同批暂存、提交、push `origin/main`，随后执行 `-done` 并回报管理员。
