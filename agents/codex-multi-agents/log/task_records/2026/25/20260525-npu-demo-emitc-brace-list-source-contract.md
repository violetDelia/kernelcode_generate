时间：2026-05-26 06:38 CST
经办人：神秘人
阶段：管理员下发前核对
任务：T-20260526-7b3fafe7 / npu-demo-emitc-brace-list-source-contract
执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`

任务目标：
- 按计划书 `ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md` 完成 npu_demo generated source layout brace-list 合同闭环。
- 新增/同步 Memory / DMA / cost initializer-list public overload 的 spec、include 与测试。
- 统一 npu_demo DMA / cost emitter 输出 brace-list，移除 generated source 中 `Vector` 与 `long long` layout buffer 泄漏。
- 覆盖 `dma.reshape` rank > 4、`dma.reinterpret`、`dma.ring`、slice / deslice / view / copy / store / load / transpose、`tuner.cost`。
- 跑通计划列 pytest、主仓只读 `expectation.dsl.gen_kernel.brace_list_source`、`git diff --check` 与敏感目录门禁。

latest main 重核：
- 前置 `T-20260525-f1e949c7 / kernel-binary-elewise-min-max-flash-attention` 已 merge/push/-done，提交 `f93fc1a81e1ea6859f16f81dee611049c7955ce6` 已同步到 `origin/main`。
- 主仓 `HEAD=origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，普通工作区 clean。
- 已创建任务 worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`。
- 已创建任务分支：`task/npu-demo-emitc-brace-list-source-contract`，基线为 `origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`。
- 计划中目标 include/spec/test/emitter 路径需由 execute 基于 latest main 现状核对；前置任务刚修改 `include/npu_demo/npu_demo.h`、`include/npu_demo/cost/Kernel.h`、`spec/include/npu_demo/npu_demo.md`、`spec/dsl/gen_kernel/emit.md` 与相关 include/public namespace 测试，execute 不得按旧计划草案覆盖已合入 min/max 合同。

合同真源与禁止修改面：
- `expectation` 真源为主仓 `expectation/dsl/gen_kernel/brace_list_source.py`，计划记录 sha256=`ab5ff21ecd18b4e2b73fd2696b20216aa7b2ee5abfee4518cf67c59d7b4f784b`，当前计划基线为实现前红灯。
- execute 只能只读运行 `expectation`，不得修改、复制、新建、同步、删除或清理 `expectation/`。
- 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 必须为空。
- 本计划不得新增未确认 public API；所有 public API 必须严格限于计划书已确认的 initializer-list overload 与 generated-source brace-list 合同。

验收提醒：
- 必须按实际 diff 反推 pytest，不能只运行计划列名命令。
- 必须记录 `expectation.dsl.gen_kernel.brace_list_source` 的正确导入边界：任务 worktree 代码在前，主仓 expectation 合同资产为真源。
- 必须记录 generated npu_demo source 负向扫描：布局参数位置不得暴露 `Vector(...)` / `Vector{...}`，不得生成 `long long *_shape[]` / `long long *_stride[]` 等 layout buffer。
- 必须跑通计划列 pytest、`py_compile` 或 compileall、`git diff --check`、敏感目录三条门禁。
- 任务记录必须与代码 / spec / test 同批进入 merge，不能代码先合记录后补。

自检：
- 管理员仅创建 worktree、记录 latest main 重核和准备分发任务；未修改实现、spec、测试、include、kernel demo、expectation、.skills 或 agents/standard。
- 当前任务记录为新建记录，后续 execute / review / archive_acceptance / merge 需沿用该记录。

结论：前置依赖已完成，可正式分发唯一计划级 execute。

---

时间：2026-05-26 07:15 CST
经办人：睡觉小分队
任务：T-20260526-7b3fafe7 / npu-demo-emitc-brace-list-source-contract
阶段：execute
执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`

任务目标：
- 按 `ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md` 完成 npu_demo generated source layout brace-list 合同闭环。
- 新增 / 同步 `Memory`、`DMA`、`cost` initializer-list public overload 的 spec/include/test。
- 统一 npu_demo DMA/cost emitter 输出 brace-list layout，移除 generated source 中 `Vector` 与 `long long` layout buffer 泄漏。
- 跑通计划列 pytest、主仓只读 `expectation.dsl.gen_kernel.brace_list_source`、`git diff --check` 与敏感目录门禁。

执行前阅读记录：
- 已重新读取 `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
- 已读取主仓只读计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md`，核对 S1-S4 与全局完成态 / 验收设计。
- 已读取任务记录当前文件与 `/home/lfr/kernelcode_generate/TODO.md`，确认当前责任仍为 `execute / 睡觉小分队 / 进行中`。
- 最新同步基线：`git fetch origin` 后 `HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，`origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，`ahead/behind=0/0`。
- 合同真源：`/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`，sha256 按计划记录为 `ab5ff21ecd18b4e2b73fd2696b20216aa7b2ee5abfee4518cf67c59d7b4f784b`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

计划内小任务卡核对：
- S1 include/spec：补齐 `include/api/Memory.h`、`include/npu_demo/Memory.h` 的 initializer-list constructor / `view` / `reshape`；补齐 `include/api/Dma.h`、`include/npu_demo/Dma.h` 的 initializer-list `slice/deslice/transpose/store/load`；补齐 `include/api/cost/Dma.h`、`include/npu_demo/cost/Dma.h` 的 initializer-list `cost::slice/deslice`。
- S2 emitter：`dma.reshape`、`dma.reinterpret`、`dma.ring`、`dma.slice/deslice/view/copy/store/load`、`tuner.cost` 的 npu_demo source layout 参数统一为 `{...} /*name*/` brace-list。
- S3 generated source 减法：移除 generated npu_demo source 的 `Vector(...)` / `Vector{...}` layout 发射与 `long long *_shape[]` / `*_stride[]` / `reshape_shape_` / `ring_shape_` 局部 layout buffer。
- S4 验收：计划列 pytest、Diff 反推 pytest、主仓只读 `expectation.dsl.gen_kernel.brace_list_source`、py_compile、`git diff --check`、敏感目录空 diff。

改动摘要：
- include public API：
  - `include/api/Memory.h` / `include/npu_demo/Memory.h` 新增 initializer-list `Memory` constructor、`Memory::view(...)`、`Memory::reshape(...)` overload，并同步文件级 API 列表与函数说明。
  - `include/api/Dma.h` / `include/npu_demo/Dma.h` 新增 initializer-list `slice/deslice/transpose/store/load` overload；手写 `Vector` 兼容路径保留。
  - `include/api/cost/Dma.h` / `include/npu_demo/cost/Dma.h` 新增 initializer-list `cost::slice/deslice` overload；`include/npu_demo/cost/Dma.h` 使用当前文件内 `cost::detail::kMaxCostDmaRank`，不跨文件调用 `Memory.h` 的 private detail。
  - `include/npu_demo/npu_demo.h` 聚合 API 列表同步公开 initializer-list DMA/cost 入口，并保留前置 min/max 合同与 `npu_demo::DMA` 公开符号。
- emitter/source：
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/{slice,deslice,view,copy,store,reshape,reinterpret,ring}.py` 改为发射 brace-list layout，不再生成 Vector layout 或局部 shape/stride buffer。
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py` 对 DMA `slice/deslice/store` cost layout 发射 brace-list；`dma.store` 仍映射到公开 `cost::deslice`。
  - `kernel_gen/dsl/gen_kernel/kernel_emitter.py` 不再把 npu_demo `.view<...>({...})` 归一化回 `Vector{...}`；body-level npu_demo memory pipeline 使用成员式 brace-list `view/slice/deslice`；同时修复 `buffer-results-to-out-params` 后 npu_demo `dma.cast` out-param result 名绑定，避免生成未声明 `v0`。
- spec/test：
  - 同步 `spec/include/api/{Memory,Dma}.md`、`spec/include/api/cost/Dma.md`、`spec/include/npu_demo/npu_demo.md`、`spec/dsl/gen_kernel/**`、`spec/tools/dsl_{run,cost_run}.md` 的 brace-list generated-source 合同。
  - 补充 include public namespace 与 API 编译测试、npu_demo generated source brace-list 断言、`dsl_cost_run` rank2 store brace-list 断言。
  - 更新 `test/dsl/gen_kernel/test_gen_kernel.py` 旧标量/Vector 输出断言为新 brace-list 合同。
  - 更新 `test/tools/test_emitc_case_runner.py` 的 `kernel.exp` 断言，保持与输入 IR 操作数顺序一致。

最小功能闭环：
- public include 层：initializer-list overload 可编译、可运行，非法 layout 返回公开失败状态或稳定 `runtime_error` 文本。
- generated source 层：layout 参数均以 `{...} /*offset|size|stride|shape*/` 输出；完整 brace-list expectation 覆盖 DMA layout 与 cost layout 两类正例。
- 兼容边界：手写 `Vector` overload 保留；本轮未新增 Python helper public API；未修改 expectation；未覆盖旧计划口径覆盖已合入 min/max 合同。
- 失败边界：layout rank mismatch、空 layout、非正 size/stride、越界、非法 reshape 仍通过 include helper 或 emit error 稳定失败。

Diff 反推自测：
- 改动 include Memory/DMA/cost 公开 overload，反推运行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_cost.py test/include/api/test_public_namespace.py test/include/npu_demo/test_public_namespace.py`
  - 结果：exit=0，`22 passed`。
- 改动 gen_kernel emitter 与 generated source 合同，反推运行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit=0，`170 passed, 2 warnings`。
- 改动工具链相关输出与 `emitc_case_runner` 门禁，反推运行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_ircheck_runner.py test/tools/test_emitc_case_runner.py`
  - 结果：exit=0，`110 passed, 2 warnings`。
- Python 语法自测：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/tools/emitc_case_runner.py`
  - 结果：exit=0。

合同验收：
- 命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 -m expectation.dsl.gen_kernel.brace_list_source`
- cwd：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`
- 导入边界 proof：
  - `expectation_file=/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
  - `kernel_gen_file=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract/kernel_gen/dsl/gen_kernel/__init__.py`
- 结果：exit=0；通过 `dsl-gen_kernel-brace_list-dma_layout-1` 与 `dsl-gen_kernel-brace_list-cost_layout-1` 两条只读合同。

静态扫描与门禁：
- `git diff --check`：exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
- 生成源码负向扫描：
  - `rg -n "Vector\\(|Vector\\{|long long [A-Za-z0-9_]*(shape|stride)|reshape_shape_|ring_shape_|_shape\\[|_stride\\[" kernel_gen/dsl/gen_kernel/emit/npu_demo kernel_gen/dsl/gen_kernel/kernel_emitter.py`
  - 结果：仅命中解释性注释 `不再把 ... Vector{...}` 与 `generated source 不生成 long long *_shape[] / *_stride[]`，未命中实际发射代码。
- 私有 / ctx 边界扫描：
  - `rg -n "hasattr\\(|getattr\\([^\\n]*ctx|callable\\(getattr|::detail::|detail::kMaxMemoryHelperRank" kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/tools/emitc_case_runner.py include/npu_demo/cost/Dma.h`
  - 结果：exit=1，无命中；未新增 ctx 能力探测，未跨文件依赖 `Memory.h` private detail。
- 注释路径核对：
  - `rg -n "test/include/api/(dma|memory|cost)\\.py" include/api/Dma.h include/api/Memory.h include/api/cost/Dma.h include/npu_demo/Dma.h include/npu_demo/Memory.h include/npu_demo/cost/Dma.h`
  - 结果：无命中；原生 `rg` no-match 返回 1，本轮触达 include 文件中的关联测试路径已同步为真实 pytest 文件名。

减法检查：
- 新增 / 改动 private callable：
  - 未新增 Python module-level private callable。
  - 改动既有 `kernel_gen/dsl/gen_kernel/kernel_emitter.py::_normalize_npu_demo_stmt`：删除 `.view<...>` 到 `Vector{...}` 的旧归一化分支，保留 npu_demo namespace 补全逻辑。
  - 改动既有 `kernel_gen/dsl/gen_kernel/kernel_emitter.py::_emit_npu_demo_body_level_kernel_body`：替换旧自由函数 `view(..., scalar layout)` / `slice(..., scalar layout)` / `deslice(..., scalar layout)` 为成员式 brace-list source。
  - 改动既有 `kernel_gen/dsl/gen_kernel/kernel_emitter.py::_bind_rewritten_out_result`：允许 npu_demo `DmaCastOp` result 绑定 out-param，修复 plan gate 中 `emitc_case_runner` 生成未声明 `v0` 的问题；不放宽 npu_demo `dma.view` / `dma.reshape` 局部 tile 视图。
  - 改动既有 npu_demo dma/cost emit 注册函数，删除旧 scalar special-case、`Vector(...)` / `Vector{...}` layout 和局部 shape/stride buffer 发射逻辑；未新增跨文件非公开 helper 调用。
- 新增 C++ public overload：
  - `Memory`、`DMA`、`cost` initializer-list overload 均为计划确认 public API，已进入 include 文件级 API 列表和 spec API 列表。
  - `include/npu_demo/cost/Dma.h::cost::detail::kMaxCostDmaRank` 为当前文件内实现常量，不是 callable，不构成 public API。
- 被替代旧逻辑与处理：
  - `generated source` 的 `Vector` layout 发射、`long long *_shape[]` / `*_stride[]` layout buffer、`rank 1..4 Vector supports` 生成端限制已删除或替换为 brace-list output。
  - 手写 include `Vector` overload 作为兼容 public API 保留，不属于 generated source 泄漏。
  - `tuner.cost(op_name="dma.store")` 未新增 `cost::store`，继续复用 `cost::deslice`，符合计划边界。

自检：
- 接口：新增 initializer-list overload 均在 include 文件级 API 列表、spec API 列表和 public namespace 测试中落位；未新增未确认 Python public helper。
- 边界：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 未修改；主仓 expectation 仅只读运行。
- 异常 / 失败：initializer-list 空 rank、长度不一致、非正 size/stride、越界与非法 reshape 均通过 include helper 或 emit error 收口。
- 兼容：手写 Vector overload 保留；已合入 min/max 合同未回退。
- 实现遗漏：plan 点名 `reshape/reinterpret/ring/slice/deslice/view/copy/store/load/tuner.cost` 均已覆盖；`dma.store` cost 仍为 `cost::deslice`。
- 冗余 / 复用：generated source 侧旧 Vector/layout buffer 路径已删除；include runtime 侧复用现有 Vector overload 或直接 copy/convert 执行，不引入跨文件 private API。
- 函数粒度 / 注释：新增 C++ overload 均有功能说明、使用示例和关联文件；本轮触达 include 注释测试路径已修正为真实文件。
- 资源 / 性能：initializer-list overload 使用固定上限栈 buffer，rank 上限 8，避免动态分配；generated source 不再生成临时 layout buffer。
- 测试有效性：pytest 同时断言正向编译运行和负向无 `Vector` / no buffer；只读 expectation 锁定完整 generated source 与 cost source。

结论：
- execute 已完成；当前无阻塞。
- 下一步按流程通过 `-next` 续接 review，审查重点建议覆盖 public API 列表精确性、generated source 负向扫描、主仓只读 expectation 导入边界和敏感目录空 diff。

---

时间：2026-05-26 12:02 CST
经办人：不要啊教练
任务：T-20260526-7b3fafe7 / npu-demo-emitc-brace-list-source-contract
阶段：review
执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`

审查前同步：
- 已重新读取个人提示词、根 `AGENTS.md`、`agents/standard/审查规范.md` 与 `agents/standard/任务记录约定.md`。
- 已执行 `git fetch origin`；`HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，`origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，`merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，ahead/behind=`0/0`。
- 待审 worktree 内缺少 `ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md`；本轮按管理员记录与 execute 记录，只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md`，sha256=`9d05ef7328e5fd214bffb2fa7a775ebc36cca69203df24eb20cffd80bdf74603`。未复制或修改计划书。
- 主仓只读 expectation 合同资产 `/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`，sha256=`ab5ff21ecd18b4e2b73fd2696b20216aa7b2ee5abfee4518cf67c59d7b4f784b`。

审查结论：不通过，退回 execute。

最小需改项：
1. `include/api/Dma.h:4` 文件级功能说明仍写“公共层提供 `alloc / fill / slice / deslice / transpose / broadcast` 六类 DMA helper 声明”，但本轮 API 列表与 spec 已新增 `store/load` initializer-list 公开入口。需同步改成包含 `store/load` 的当前 public DMA helper 范围，避免文件说明与 API 列表自相矛盾。
2. `include/npu_demo/Dma.h:3` 文件级功能说明仍写“`alloc/fill/slice/deslice/transpose/broadcast` 轻量实现”，漏掉本轮新增的 `store/load` initializer-list public overload。需同步到当前实现承载范围。
3. `spec/include/api/Dma.md:291` 测试矩阵 `TC-INCLUDE-API-DMA-005` 仍只描述 `alloc/fill/slice/deslice/transpose/broadcast` 公开入口，经 `include/npu_demo/npu_demo.h` 的公开 namespace 测试本轮已加入 `store/load`。需把该矩阵行同步到含 `store/load` 的当前公开入口集合，或拆出对应行，保证 spec/test 对齐。
4. `include/npu_demo/Memory.h:46` 与 `include/npu_demo/cost/Dma.h:22` 文件级 `关联文件` 仍指向不存在或旧路径的 `test/include/npu_demo/kernel_context.py`、`test/include/npu_demo/cost.py`。这两个文件本轮已修改功能实现并新增/修改公开 API 承接能力，文件级说明需改为真实测试入口，例如本轮实际覆盖的 `test/include/api/test_memory.py` 与 `test/include/api/test_cost.py`，否则不满足实现文件说明准确性要求。

真实审查：
- include/API：`Memory`、`DMA`、`cost::DMA` initializer-list overload 已进入 API 列表并有对应函数说明/使用示例；手写 `Vector` 兼容路径未被删除。阻断点集中在 changed 文件的顶部功能说明、关联文件与 spec 测试矩阵未完全同步。
- emitter：`dma.copy/slice/deslice/view/reshape/reinterpret/ring/store` 与 `tuner.cost` 的 layout 发射已从 `Vector` 或局部 layout buffer 改为 brace-list；`kernel_emitter.py` 删除 `.view<...>` brace-list 回写 `Vector{...}` 的旧归一化分支。
- 公开 API/非公开 API 边界：未发现本轮 Python 侧新增跨文件调用非公开 helper；未发现 ctx 能力探测、`object` 签名或非装饰器嵌套函数新增问题。C++ `detail` 命中均在当前 include 文件内部或既有实现命名空间内，未发现 generated source 依赖 `detail`。
- 减法审查：候选 diff 未恢复旧根 shim、未新增 `cost::store` 公开 API；generated source 侧 `Vector` layout 与 `long long *_shape[]` / `*_stride[]` layout buffer 已从发射路径删除。阻断项为说明/spec 同步缺口，不是运行结果失败。

Diff 反推审查与验收复跑：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/tools/emitc_case_runner.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_cost.py test/include/api/test_public_namespace.py test/include/npu_demo/test_public_namespace.py`：exit=0，`22 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`170 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_ircheck_runner.py test/tools/test_emitc_case_runner.py`：exit=0，`110 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 -m expectation.dsl.gen_kernel.brace_list_source`：exit=0；输出包含两条合同 case。
- expectation 导入证明：`expectation_file=/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`；`kernel_gen_file=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract/kernel_gen/__init__.py`。
- generated source 负向扫描：`rg -n "Vector\(|Vector\{|long long [A-Za-z0-9_]*(shape|stride)|reshape_shape_|ring_shape_|_shape\[|_stride\[" kernel_gen/dsl/gen_kernel/emit/npu_demo kernel_gen/dsl/gen_kernel/kernel_emitter.py` 仅命中说明性注释，未命中实际发射代码。
- 私有/ctx/object 扫描：`rg -n "hasattr\(|getattr\([^\n]*ctx|callable\(getattr|from kernel_gen\.[^\n]* import _|import kernel_gen\.[^\n]*\._|def [A-Za-z_][A-Za-z0-9_]*\([^\n]*object|\bobject\b" ...`：无命中。
- `git diff --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均为空。

自检：
- 本轮只写任务记录，不修改代码、spec、测试、计划、expectation、.skills、agents/standard、AGENTS、TODO 或 DONE。
- review 阻断项均为当前 diff 触达文件内可直接修复的说明/spec 同步问题；不要求改 expectation。
- 计划级 review 未通过，应按流程退回 execute，修复后重新 review；不得进入 archive_acceptance 或 merge。

---

时间：2026-05-26 22:50 CST
经办人：小李飞刀
任务：T-20260526-7b3fafe7 / npu-demo-emitc-brace-list-source-contract
阶段：execute 返工
执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`

任务目标：
- 修复 review 退回的 4 个最小项：
  1. `include/api/Dma.h` 文件级功能说明补入 `store/load` 当前公开 DMA helper 范围。
  2. `include/npu_demo/Dma.h` 文件级功能说明补入 `store/load` 当前 npu_demo DMA 实现范围。
  3. `spec/include/api/Dma.md` 的 `TC-INCLUDE-API-DMA-005` 测试矩阵同步为 `alloc/fill/slice/deslice/transpose/store/load/broadcast`。
  4. `include/npu_demo/Memory.h` 与 `include/npu_demo/cost/Dma.h` 的旧测试路径同步为真实 pytest 入口。

执行前阅读记录：
- 已重新读取个人提示词 `/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读取当前任务记录、本轮 review 退回记录、主仓只读计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md` 与 `/home/lfr/kernelcode_generate/TODO.md`；确认当前任务为 `execute / 小李飞刀 / 进行中`。
- latest main 核对：`git fetch origin main` 后 `HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`、`origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`、`merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`、ahead/behind=`0/0`。
- 合同真源：主仓 `/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`；本轮只读运行，不修改 expectation。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

返工收口：
- `include/api/Dma.h`：文件级功能说明从旧 `alloc / fill / slice / deslice / transpose / broadcast` 更新为 `alloc / fill / slice / deslice / transpose / store / load / broadcast`，与本轮 API 列表和 spec 对齐。
- `include/npu_demo/Dma.h`：文件级功能说明从旧 `alloc/fill/slice/deslice/transpose/broadcast` 更新为 `alloc/fill/slice/deslice/transpose/store/load/broadcast`。
- `spec/include/api/Dma.md`：`TC-INCLUDE-API-DMA-005` 的场景与预期同步为含 `store/load` 的公开入口集合。
- `include/npu_demo/Memory.h`：将残留旧 `test/include/npu_demo/kernel_context.py` 关联路径统一替换为 `test/include/api/test_memory.py`。
- `include/npu_demo/cost/Dma.h`：将残留旧 `test/include/npu_demo/cost.py` 关联路径统一替换为 `test/include/api/test_cost.py`。

最小功能闭环：
- 本轮只修说明/spec 同步，不改变 C++/Python 行为、不新增公开 API、不改 expectation。
- review 4 个最小项均已直接闭合；同类旧测试路径残留已用窄扫清空。

Diff 反推自测：
- include public API 与文件说明同步后，复跑公开 include 测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_cost.py test/include/api/test_public_namespace.py test/include/npu_demo/test_public_namespace.py`
  - 结果：exit=0，`22 passed`。
- generated source / emitter diff 保持不回退，复跑相关 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit=0，`170 passed, 2 warnings`。
- tools / runner 相关 diff 保持不回退，复跑相关 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_ircheck_runner.py test/tools/test_emitc_case_runner.py`
  - 结果：exit=0，`110 passed, 2 warnings`。
- Python 语法检查：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/tools/emitc_case_runner.py`
  - 结果：exit=0。

合同验收：
- 命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 -m expectation.dsl.gen_kernel.brace_list_source`
- cwd：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`
- 结果：exit=0；输出两条合同 case：
  - `dsl-gen_kernel-brace_list-dma_layout-1`
  - `dsl-gen_kernel-brace_list-cost_layout-1`
- 导入边界 proof：
  - `expectation_file=/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
  - `kernel_gen_file=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract/kernel_gen/__init__.py`

静态扫描与门禁：
- review 残留项扫描：
  - `rg -n "alloc / fill / slice / deslice / transpose / broadcast|alloc/fill/slice/deslice/transpose/broadcast|test/include/npu_demo/kernel_context.py|test/include/npu_demo/cost.py|test/include/api/(dma|memory|cost)\\.py" include/api/Dma.h include/api/Memory.h include/api/cost/Dma.h include/npu_demo/Dma.h include/npu_demo/Memory.h include/npu_demo/cost/Dma.h spec/include/api/Dma.md`
  - 结果：exit=0，无输出；旧功能说明集合、旧测试路径和小写旧测试文件名均未残留。
- generated source 负向扫描：
  - `rg -n "Vector\\(|Vector\\{|long long [A-Za-z0-9_]*(shape|stride)|reshape_shape_|ring_shape_|_shape\\[|_stride\\[" kernel_gen/dsl/gen_kernel/emit/npu_demo kernel_gen/dsl/gen_kernel/kernel_emitter.py || true`
  - 结果：仅命中说明性注释 `不再把 ... Vector{...}` 与 `generated source 不生成 long long *_shape[] / *_stride[]`，未命中实际发射代码。
- 私有 / ctx / object 边界扫描：
  - `rg -n "hasattr\\(|getattr\\([^\\n]*ctx|callable\\(getattr|from kernel_gen\\.[^\\n]* import _|import kernel_gen\\.[^\\n]*\\._|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object|\\bobject\\b" kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/tools/emitc_case_runner.py include/npu_demo/cost/Dma.h`
  - 结果：exit=1，无命中。
- `git diff --check`：exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。

减法检查：
- 本轮未新增或修改 Python / C++ private callable。
- 本轮只删除旧文案残留：旧 DMA helper 范围文本、旧 `TC-INCLUDE-API-DMA-005` 场景文本、旧不存在测试路径。
- 未保留 review 指出的旧说明口径；窄扫已证明同类旧路径无残留。

自检：
- 接口：无新增/删除/重命名公开 API；仅把文件说明与 spec 测试矩阵同步到既有本轮 API 列表。
- 边界：未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 异常 / 兼容：本轮无行为改动；既有 include/emitter pytest 和只读 expectation 均通过。
- 实现遗漏：review 4 个最小项已全部闭合；同类旧路径残留已额外清理。
- 注释准确性：触达 include 文件的文件级功能说明和关联测试路径已与真实测试入口一致。
- 资源 / 并发 / 性能：无运行时逻辑变更。
- 测试有效性：Diff 反推 pytest 覆盖 include 公开 API、generated source、工具链；expectation 单列为合同验收。

结论：
- execute 返工已完成，当前无阻塞。
- 下一步按流程通过 `-next` 续接 review。

## review 记录 - 2026-05-26 23:32 CST - 提莫炖蘑菇

结论：最小需改项，不通过，退回 execute。

发现：
- 阻断：`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py:67` 本轮改动触达的 private callable `_num_elements_expr(shape_values: tuple[str, ...]) -> str` 有效代码只有 3 行；`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py:100` 改动后的 private callable `_emit_ring_slot_view(...)` 仍在同一实现中调用 `_ring_owner(...)`、`_memory_element_cpp_type(...)`、`_symbol_expr_text(...)`、`_num_elements_expr(...)` 等 private callable。按 `agents/standard/审查规范.md` 的私有函数审查规则，新建或改动 private callable 小于 5 行有效代码不得放行，private callable 调用其它 private callable 也不得放行。
  - 影响：即使本轮公开 API、pytest 与 expectation 均通过，当前实现仍违反最新 private helper 减法边界；review 不能以“只是内部 helper / 当前能跑”为由放行。
  - 最小返工动作：删除或内联 `_num_elements_expr(...)`，并收口 `_emit_ring_slot_view(...)` 的 private-to-private 调用链；优先把仅服务单一调用点的小逻辑内联到 `_emit_ring_slot_view(...)`，或合并为一个满足规范且不再调用其它 private callable 的当前文件 helper。
  - 验收方式：复跑 `git diff -U0 -- '*.py' | rg '^\\+def _|^\\+class _|^\\+\\s+def _|^\\+\\s+class _|_num_elements_expr\\(' || true` 确认无不合格新增 / 改动 private callable；复跑本任务 Diff 反推 pytest、只读 expectation、`git diff --check` 与敏感目录门禁。

审查范围：
- worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`
- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-emitc-brace-list-source-contract.md`
- 任务类型：计划级 `review`，通过时应进入 `archive_acceptance`，不得直接 merge。

同步基线：
- `git fetch origin --prune`：已执行。
- `HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- 分支：`task/npu-demo-emitc-brace-list-source-contract`
- 同步结果：当前 worktree 已在 latest `origin/main` 基线上；无 merge/rebase 操作，未覆盖任务 diff。

执行记录核对：
- 已读取当前任务记录、12:02 review 退回项、22:50 小李飞刀 execute 返工记录、主仓计划书与主仓 `TODO.md`。
- 当前 worktree 根目录无 `TODO.md`，已读取主仓 `/home/lfr/kernelcode_generate/TODO.md`；其中 `T-20260526-7b3fafe7` 当前为 `review / 提莫炖蘑菇 / 进行中`，与本轮指派一致。
- 22:50 execute 记录中的 4 个退回项均有对应 diff：
  - `include/api/Dma.h` 文件级功能说明已补 `store/load`。
  - `include/npu_demo/Dma.h` 文件级功能说明已补 `store/load`。
  - `spec/include/api/Dma.md` 的 `TC-INCLUDE-API-DMA-005` 已同步为 `alloc/fill/slice/deslice/transpose/store/load/broadcast`。
  - `include/npu_demo/Memory.h` 与 `include/npu_demo/cost/Dma.h` 的旧测试路径已替换为真实 pytest 入口。
- 定向残留扫描 `rg -n "alloc / fill / slice / deslice / transpose / broadcast|alloc/fill/slice/deslice/transpose/broadcast|test/include/npu_demo/kernel_context.py|test/include/npu_demo/cost.py|test/include/api/(dma|memory|cost)\\.py" include/api/Dma.h include/api/Memory.h include/api/cost/Dma.h include/npu_demo/Dma.h include/npu_demo/Memory.h include/npu_demo/cost/Dma.h spec/include/api/Dma.md || true`：exit=0，无输出。

Diff 反推审查：
- include / public API 文件说明和公开入口改动：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_cost.py test/include/api/test_public_namespace.py test/include/npu_demo/test_public_namespace.py`
  - 结果：exit=0，`22 passed`。
- generated source / npu_demo emit 改动：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit=0，`170 passed, 2 warnings`。
- tools / runner 改动：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_ircheck_runner.py test/tools/test_emitc_case_runner.py`
  - 结果：exit=0，`110 passed, 2 warnings`。
- Python 语法检查：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/dsl/gen_kernel/kernel_emitter.py`
  - 结果：exit=0。

合同验收：
- 只读合同真源：主仓 `/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
- 导入边界 proof：
  - `expectation_file=/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
  - `expectation_sha256=ab5ff21ecd18b4e2b73fd2696b20216aa7b2ee5abfee4518cf67c59d7b4f784b`
  - `kernel_gen_file=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract/kernel_gen/__init__.py`
- 命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 -m expectation.dsl.gen_kernel.brace_list_source`
  - cwd：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`
  - 结果：exit=0，输出两条合同 case：`dsl-gen_kernel-brace_list-dma_layout-1`、`dsl-gen_kernel-brace_list-cost_layout-1`。

静态扫描与敏感目录门禁：
- `git diff --check`：exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
- ctx/object/importlib 扫描：
  - `git diff -U0 -- '*.py' | rg '^\\+.*(hasattr\\(|getattr\\(|callable\\(getattr|\\bobject\\b|importlib|__import__|def .*object|: object|, object)' || true`
  - 结果：exit=0，无输出。
- private callable 扫描：
  - `git diff -U0 -- '*.py' | rg '^\\+def _|^\\+class _|^\\+\\s+def _|^\\+\\s+class _|_num_elements_expr\\(' || true`
  - 结果：命中 `_num_elements_expr` 签名变更与 `_emit_ring_slot_view` 内调用，构成本轮阻断。

减法审查：
- 4 个退回项对应的旧说明口径、旧测试路径和小写旧测试文件名已删除，窄扫无残留。
- 本轮仍触达 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 的 private callable `_num_elements_expr(...)`，其有效代码小于 5 行，并被 `_emit_ring_slot_view(...)` 调用；执行记录中“本轮未新增或修改 Python / C++ private callable”的判断与实际 diff 不一致。
- 因 private callable 减法边界未收口，本轮不能进入 `archive_acceptance`。

自检：
- 已读取实际 diff，不只依赖 execute 摘要。
- 已核对 latest main 基线、计划书、任务记录、只读 expectation 真源与禁止修改面。
- 已核对 4 个退回项闭合、公开 API/spec 说明一致性和相关 pytest。
- 已完成 Diff 反推审查、合同验收、敏感目录门禁和 private callable 审查。
- 由于存在可执行最小返工项，本轮结论必须为不通过并退回 execute。

## execute 返工记录 - 2026-05-26 23:45 CST - 小李飞刀

时间：2026-05-26 23:45 CST

经办人：小李飞刀

任务：`T-20260526-7b3fafe7 / npu-demo-emitc-brace-list-source-contract`

任务目标：
- 修复 review 阻断项：收口 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` private callable 边界，删除或内联 `_num_elements_expr(...)`，避免 private callable 小于 5 行有效代码及 private callable 调用 private callable。
- 复跑 Diff 反推 pytest、主仓只读 `expectation.dsl.gen_kernel.brace_list_source`、`git diff --check` 与敏感目录门禁。

执行前阅读记录：
- 已读取根 `AGENTS.md`、`agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读取计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md`。
- 已读取当前任务记录尾部 review 退回项与主仓 `/home/lfr/kernelcode_generate/TODO.md`；TODO 当前行为 `T-20260526-7b3fafe7 / execute / 小李飞刀 / 进行中`。
- 已确认 worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`。

同步基线：
- 命令：`git fetch origin main --prune`
- `HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- 结果：当前 worktree 已在 latest `origin/main` 基线上；未执行 merge/rebase，未覆盖任务 diff。

改动：
- 修改 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`。
- 删除单用途 private helper 链路：`_memory_element_cpp_type(...)`、`_symbol_expr_text(...)`、`_num_elements_expr(...)`、`_ring_owner(...)`、`_emit_ring_slot_view(...)`。
- 将 `dma.current_ring` 与 `dma.advance_ring` 的 ring owner 校验、`NnMemoryType` 校验、element type 选择、shape 表达式校验、flat typed view 和 reshape 发射直接内联到对应 decorated emit 实现中。
- 未新增公开 API，未修改 spec/API 列表或公开错误文本；本轮只收口 review 指出的 private callable 边界。

新增 / 重复 / 范围扩大判断：
- 新增问题：本轮 review 新增阻断项为 private callable 减法边界，前一轮 execute 未识别 `ring.py` 中 `_num_elements_expr(...)` 和 `_emit_ring_slot_view(...)` 的私有链式调用风险。
- 重复问题：无同一阻断项第三次重复；本轮已直接删除相关单用途 helper 链路。
- 范围扩大：无。仅修改 review 点名文件 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 与本记录。

最小功能闭环：
- `dma.current_ring` / `dma.advance_ring` 仍发射 backing memory 的 brace-list typed view；rank > 1 继续先生成 flat view 再 `.reshape({shape} /*shape*/)`。
- `?` shape 仍按原公开 emit 错误文本 `ring slot shape must be static or symbolic` 失败。
- 非 `dma.make_ring` 来源仍按原公开 emit 错误文本 `ring source must be dma.make_ring` 失败。

Diff 反推自测：
- Python 语法：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`
  - 结果：exit=0。
- npu_demo gen_kernel / emit 相关 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit=0，`170 passed, 2 warnings`。
  - 断言点：锁定 npu_demo generated source brace-list 发射、gen_kernel 源码生成和相关 package 行为不回退。
- include 公开 API pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_cost.py test/include/api/test_public_namespace.py test/include/npu_demo/test_public_namespace.py`
  - 结果：exit=0，`22 passed`。
  - 断言点：锁定本计划 include brace-list overload、公开 namespace 和 API 说明对应的可编译行为。
- 工具链 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_ircheck_runner.py test/tools/test_emitc_case_runner.py`
  - 结果：exit=0，`110 passed, 2 warnings`。
  - 断言点：锁定 dsl_run / dsl_cost_run / ircheck / emitc runner 经当前 generated source 入口不回退。
- 相关文件 py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/dsl/gen_kernel/kernel_emitter.py`
  - 结果：exit=0。

合同验收：
- 主仓只读合同资产：`/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
- sha256：`ab5ff21ecd18b4e2b73fd2696b20216aa7b2ee5abfee4518cf67c59d7b4f784b`
- 导入边界 proof：
  - 命令：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 - <<'PY' ...`
  - `expectation_file=/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
  - `kernel_gen_file=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract/kernel_gen/__init__.py`
- 命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 -m expectation.dsl.gen_kernel.brace_list_source`
  - cwd：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`
  - 结果：exit=0，输出 `dsl-gen_kernel-brace_list-dma_layout-1`、`dsl-gen_kernel-brace_list-cost_layout-1`。

减法检查：
- 删除的 private callable：
  - `_memory_element_cpp_type(memory_type, ctx) -> str`
  - `_symbol_expr_text(attr, ctx, op_name: str) -> str`
  - `_num_elements_expr(shape_values) -> str`
  - `_ring_owner(value, ctx, op_name: str) -> DmaMakeRingOp`
  - `_emit_ring_slot_view(op, ctx) -> str`
- 删除依据：均只服务本文件 ring slot 发射；其中 `_num_elements_expr(...)` 有效代码小于 5 行，且 `_emit_ring_slot_view(...)` 调用了多个 private callable，违反 private callable 边界。
- 保留依据：本轮未新增当前文件 helper；为避免 private callable 调用 private callable，`current_ring` 与 `advance_ring` 的 emit 实现各自直接承接发射逻辑。
- review 指定扫描：
  - `git diff -U0 -- '*.py' | rg '^\\+def _|^\\+class _|^\\+\\s+def _|^\\+\\s+class _|_num_elements_expr\\(' || true`
  - 结果：命中删除行 `-def _num_elements_expr...`、旧示例删除行和大段删除导致 diff 展示的既有 decorated emit 函数签名；无 `+.*_num_elements_expr(` 新增行。
- 新增 `_num_elements_expr` 精确扫描：
  - `git diff -U0 -- '*.py' | rg '^\\+.*_num_elements_expr\\(' || true`
  - 结果：exit=0，输出为空。
- 当前文件残留扫描：
  - `rg -n "_memory_element_cpp_type|_symbol_expr_text|_num_elements_expr|_ring_owner|_emit_ring_slot_view" kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py || true`
  - 结果：exit=0，输出为空。
- AST private-to-private 扫描：
  - 脚本：解析 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`，收集 private `FunctionDef` 并扫描 `Call` 是否调用同文件 private callable。
  - 结果：`private_funcs=_emit_npu_demo_dma_advance_ring,_emit_npu_demo_dma_current_ring,_emit_npu_demo_dma_make_ring`，`private_to_private=none`。

静态扫描与敏感目录门禁：
- ctx / object / 跨文件私有导入扫描：
  - `rg -n "hasattr\\(|getattr\\([^\\n]*ctx|callable\\(getattr|from kernel_gen\\.[^\\n]* import _|import kernel_gen\\.[^\\n]*\\._|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object|\\bobject\\b" kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/tools/emitc_case_runner.py include/npu_demo/cost/Dma.h || true`
  - 结果：exit=0，输出为空。
- `git diff --check`：exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，输出为空。

自检：
- 接口：无新增、删除、重命名公开 API；未修改 spec/API 列表。
- 边界：未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 异常：保留 ring source、ring slot type、unknown shape 的公开 emit 错误语义。
- 兼容：`dma.current_ring` / `dma.advance_ring` generated source 形态保持 brace-list；pytest 与 expectation 均通过。
- 冗余：已删除 review 点名的小 helper 与 private-to-private 链路；未保留旧 `_vector_ctor_expr` / `_shape_vector_expr` / `_num_elements_expr` 旧 Vector 路径。
- 注释准确性：未新增公开 API；现有文件级说明仍与当前文件无公开 API、通过 registry 调度的事实一致。
- 函数粒度：本轮为满足 private callable 规则接受两个 decorated emit 实现中少量重复逻辑，避免新增不合规 helper。
- 资源 / 并发 / 性能：无运行时资源生命周期或并发语义变更；仅改变源码发射实现结构。
- 测试有效性：Diff 反推 pytest 覆盖 generated source、include 公开 API 和工具链；expectation 单列为合同验收。

结论：
- review 阻断项已收口；当前无阻塞。
- 下一步按流程 `-next` 续接 `review`。

## review 复审记录 - 2026-05-26 23:13 CST - 提莫炖蘑菇

结论：通过，按计划级流程流转 `archive_acceptance`，不直接 merge。

验证基线：
- `git fetch origin --prune`
- `HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`

发现：
- 无新增阻断项。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 的 private helper 链路已收口：`_memory_element_cpp_type`、`_symbol_expr_text`、`_num_elements_expr`、`_ring_owner`、`_emit_ring_slot_view` 均已删除，当前 AST 扫描 `private_to_private=none`。
- 4 个最小返工项均已闭合：
  1. `include/api/Dma.h` 文件级功能说明补入 `store/load`。
  2. `include/npu_demo/Dma.h` 文件级功能说明补入 `store/load`。
  3. `spec/include/api/Dma.md` 的 `TC-INCLUDE-API-DMA-005` 已同步为包含 `store/load` 的测试矩阵。
  4. `include/npu_demo/Memory.h` 与 `include/npu_demo/cost/Dma.h` 旧测试路径已替换为真实 pytest 入口。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` -> `exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py` -> `170 passed, 2 warnings`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_cost.py test/include/api/test_public_namespace.py test/include/npu_demo/test_public_namespace.py` -> `22 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_ircheck_runner.py test/tools/test_emitc_case_runner.py` -> `110 passed, 2 warnings`

合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 -m expectation.dsl.gen_kernel.brace_list_source` -> `exit=0`，输出 `dsl-gen_kernel-brace_list-dma_layout-1` 与 `dsl-gen_kernel-brace_list-cost_layout-1`
- 导入边界 proof：
  - `expectation_file=/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
  - `expectation_sha256=ab5ff21ecd18b4e2b73fd2696b20216aa7b2ee5abfee4518cf67c59d7b4f784b`
  - `kernel_gen_file=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract/kernel_gen/__init__.py`

静态扫描与敏感目录门禁：
- `git diff --check` -> `exit=0`
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` -> 空
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` -> 空
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` -> 空
- private callable AST 扫描：`private_funcs=_emit_npu_demo_dma_advance_ring,_emit_npu_demo_dma_current_ring,_emit_npu_demo_dma_make_ring`，`private_to_private=none`
- `git diff -U0 -- '*.py' | rg '^\\+.*(hasattr\\(|getattr\\(|callable\\(getattr|\\bobject\\b|importlib|__import__|def .*object|: object|, object)' || true` -> 空
- 4 项残留扫描 `rg -n "alloc / fill / slice / deslice / transpose / broadcast|alloc/fill/slice/deslice/transpose/broadcast|test/include/npu_demo/kernel_context.py|test/include/npu_demo/cost.py|test/include/api/(dma|memory|cost)\\.py" include/api/Dma.h include/api/Memory.h include/api/cost/Dma.h include/npu_demo/Dma.h include/npu_demo/Memory.h include/npu_demo/cost/Dma.h spec/include/api/Dma.md || true` -> 空

减法审查：
- 删除了 ring.py 中仅服务于单文件发射的旧 helper 链路，避免 `private callable` 调用 `private callable`。
- 新的 `dma.current_ring` / `dma.advance_ring` 实现保持同一公开 emit 行为，未新增公开 API、未改 expectation。
- 本轮不保留任何被旧 helper 替代的旧路径。

自检：
- 已逐行核对实际 diff，未仅依赖执行摘要。
- 已确认最新主线现场对齐，无覆盖风险。
- 已核对公开 API、文件级说明、spec/test 同步、Diff 反推自测、只读 expectation 与敏感目录门禁。
- 已核对私有函数审查：本轮 private callable 无小于 5 行有效代码的新合规问题，且无 private-to-private 调用残留。

结论：
- `review` 通过，可续接 `archive_acceptance`。

---

时间：2026-05-26 23:58 CST
经办人：不要啊教练
任务：T-20260526-7b3fafe7 / npu-demo-emitc-brace-list-source-contract
阶段：archive_acceptance / 计划书入档验收
执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`

任务目标：
- 核对计划级 npu_demo EmitC brace-list source contract 的 review 通过结论、候选 diff 范围、任务记录完整性、Diff 反推审查、主仓只读 `expectation.dsl.gen_kernel.brace_list_source`、`git diff --check`、敏感目录空 diff 与可入档证据。
- 通过后按计划级流程续接 merge，不直接合并。

最新同步现场：
- 已执行 `git fetch origin --prune`。
- 分支：`task/npu-demo-emitc-brace-list-source-contract`
- `HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- ahead/behind=`0/0`
- 结果：worktree 已在 latest `origin/main` 基线上；未执行 merge/rebase，未覆盖任务 diff。

计划书与合同真源：
- 待审 worktree 内无 `ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md` 副本；本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_brace_list_source_contract_green_plan.md`。
- 主仓共享计划 sha256=`9d05ef7328e5fd214bffb2fa7a775ebc36cca69203df24eb20cffd80bdf74603`。
- 主仓只读 expectation：`/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`，sha256=`ab5ff21ecd18b4e2b73fd2696b20216aa7b2ee5abfee4518cf67c59d7b4f784b`。
- 本轮未复制、修改或同步计划书与 expectation。

候选 diff 范围核对：
- 候选 diff 覆盖 include public API 与 npu_demo 实现：`include/api/Dma.h`、`include/api/Memory.h`、`include/api/cost/Dma.h`、`include/npu_demo/Dma.h`、`include/npu_demo/Memory.h`、`include/npu_demo/cost/Dma.h`、`include/npu_demo/npu_demo.h`。
- 候选 diff 覆盖 npu_demo emitter 与 kernel emitter：`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/{copy,deslice,reinterpret,reshape,ring,slice,store,view}.py`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`。
- 候选 diff 覆盖对应 spec 与测试：`spec/dsl/gen_kernel/**`、`spec/include/api/**`、`spec/include/npu_demo/npu_demo.md`、`spec/tools/dsl_{run,cost_run}.md`、`test/dsl/gen_kernel/**`、`test/include/**`、`test/tools/**`。
- 候选 diff 包含本任务记录：`agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-emitc-brace-list-source-contract.md`，当前为 untracked，merge 前必须与代码/spec/test 同批纳入。
- `git diff --diff-filter=D --name-status`：无删除文件。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 与 cached/status 门禁均为空；未纳入禁止修改面。
- 范围结论：候选 diff 与主仓共享计划的 include/spec/emitter/test/记录范围一致；共享计划本身无 worktree diff，不作为本次候选改动提交。

任务记录完整性核对：
- 已核对管理员下发记录、execute 记录、12:02 review 退回记录、23:32 review 退回记录、23:45 execute 返工记录与 review 复审通过记录。
- 记录链显示两轮 review 退回项均有对应 execute 返工与复审通过结论。
- 注意：尾部 `review 复审记录 - 2026-05-26 23:13 CST - 提莫炖蘑菇` 标题时间早于前一条 `execute 返工记录 - 2026-05-26 23:45 CST`，但该 review 记录位于 execute 记录之后，正文明确核对了 23:45 execute 返工内容；本 archive_acceptance 记录将其判定为标题时间笔误并补充审计说明，不作为退回 execute 的功能阻断。merge 前必须同批纳入本 archive_acceptance 记录，以保留该澄清。
- review 通过结论：已存在 `结论：通过，按计划级流程流转 archive_acceptance，不直接 merge`，且复审记录包含 Diff 反推审查、合同验收、静态扫描和敏感目录门禁。

Diff 反推审查 / 验收复跑：
- Python 语法：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/tools/emitc_case_runner.py`
  - 结果：exit=0。
- include public API pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_cost.py test/include/api/test_public_namespace.py test/include/npu_demo/test_public_namespace.py`
  - 结果：exit=0，`22 passed`。
- gen_kernel / emitter pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit=0，`170 passed, 2 warnings`。
- tools pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_ircheck_runner.py test/tools/test_emitc_case_runner.py`
  - 结果：exit=0，`110 passed, 2 warnings`。
- 主仓只读合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 -m expectation.dsl.gen_kernel.brace_list_source`
  - cwd：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`
  - 结果：exit=0，输出 `dsl-gen_kernel-brace_list-dma_layout-1` 与 `dsl-gen_kernel-brace_list-cost_layout-1`。
- 导入边界 proof：
  - `expectation_file=/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
  - `kernel_gen_file=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract/kernel_gen/__init__.py`

静态扫描与门禁：
- `git diff --check`：exit=0。
- generated source 负向扫描：`rg -n "Vector\(|Vector\{|long long [A-Za-z0-9_]*(shape|stride)|reshape_shape_|ring_shape_|_shape\[|_stride\[" kernel_gen/dsl/gen_kernel/emit/npu_demo kernel_gen/dsl/gen_kernel/kernel_emitter.py` 仅命中说明性注释，未命中实际发射代码。
- 旧说明/旧测试路径残留扫描：`rg -n "alloc / fill / slice / deslice / transpose / broadcast|alloc/fill/slice/deslice/transpose/broadcast|test/include/npu_demo/kernel_context.py|test/include/npu_demo/cost.py|test/include/api/(dma|memory|cost)\.py" include/api/Dma.h include/api/Memory.h include/api/cost/Dma.h include/npu_demo/Dma.h include/npu_demo/Memory.h include/npu_demo/cost/Dma.h spec/include/api/Dma.md || true`：输出为空。
- private helper 残留扫描：`rg -n "_memory_element_cpp_type|_symbol_expr_text|_num_elements_expr|_ring_owner|_emit_ring_slot_view" kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py || true`：输出为空。
- AST private-to-private 扫描：`private_funcs=_emit_npu_demo_dma_advance_ring,_emit_npu_demo_dma_current_ring,_emit_npu_demo_dma_make_ring`，`private_to_private=none`。
- ctx/object/跨文件私有导入扫描：`rg -n "hasattr\(|getattr\([^\n]*ctx|callable\(getattr|from kernel_gen\.[^\n]* import _|import kernel_gen\.[^\n]*\._|def [A-Za-z_][A-Za-z0-9_]*\([^\n]*object|\bobject\b" ...`：输出为空。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。

减法审查：
- 旧 generated source `Vector(...)` / `Vector{...}` layout 发射、`long long *_shape[]` / `*_stride[]` layout buffer、`reshape_shape_` / `ring_shape_` buffer 路径已从发射实现中删除或替换为 brace-list public overload。
- ring.py 返工已删除单用途 private helper 链路，避免小 private callable 与 private-to-private 调用。
- 手写 include `Vector` overload 保留，符合计划边界；本轮未新增 `cost::store`，`dma.store` cost 仍映射到 `cost::deslice`。

自检：
- 已按 archive_acceptance 口径核对 latest main、TODO 状态、共享计划、候选 diff、review 通过记录、任务记录、验收命令和敏感目录门禁。
- 已确认候选 diff 不含 expectation、.skills、agents/standard、AGENTS、TODO、DONE。
- 已确认任务记录需与代码/spec/test 同批纳入 merge；当前记录为 untracked，merge 前必须显式 add。
- 未发现需要退回 execute 的功能、spec、测试、公开 API 或禁止修改面问题。

结论：通过 archive_acceptance，可按计划级流程续接 merge。

merge 前交接要求：
- 必须同批纳入代码、spec、test 与 `agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-emitc-brace-list-source-contract.md`。
- 不得纳入 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- merge 角色需复核任务记录当前 untracked 状态，提交前执行 `git diff --check`、敏感目录空 diff 与必要 smoke。

---

时间：2026-05-26 23:25 CST
经办人：李白
任务：T-20260526-7b3fafe7 / npu-demo-emitc-brace-list-source-contract
阶段：merge
执行目录：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`

任务目标：
- 按 archive_acceptance 通过口径合入 npu_demo EmitC brace-list source contract 候选 diff。
- 确保代码、spec、test 与任务记录 `agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-emitc-brace-list-source-contract.md` 同批纳入。
- 排除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

合并前同步：
- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`。
- `git fetch --prune origin`：完成。
- `HEAD=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- `merge-base=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- ahead/behind=`0/0`
- 主仓 `/home/lfr/kernelcode_generate` 同步核对：`HEAD=origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`，工作区 clean。
- 结果：任务 worktree 已在 latest main 基线上，无主线前进、无冲突、无覆盖他人改动。

实际合入来源：
- 源 worktree：`/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract`
- 源分支：`task/npu-demo-emitc-brace-list-source-contract`
- 源基线：`origin/main=f93fc1a81e1ea6859f16f81dee611049c7955ce6`
- 合入方式：在任务分支提交候选 diff 与本记录后，推送 `HEAD:main`；随后同步主仓本地 `main`。

实际候选范围：
- include public API 与 npu_demo 实现：
  - `include/api/Dma.h`
  - `include/api/Memory.h`
  - `include/api/cost/Dma.h`
  - `include/npu_demo/Dma.h`
  - `include/npu_demo/Memory.h`
  - `include/npu_demo/cost/Dma.h`
  - `include/npu_demo/npu_demo.h`
- npu_demo emitter 与 kernel emitter：
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py`
  - `kernel_gen/dsl/gen_kernel/kernel_emitter.py`
- spec：
  - `spec/dsl/gen_kernel/emit.md`
  - `spec/dsl/gen_kernel/emit/npu_demo.md`
  - `spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`
  - `spec/dsl/gen_kernel/gen_kernel.md`
  - `spec/include/api/Dma.md`
  - `spec/include/api/Memory.md`
  - `spec/include/api/cost/Dma.md`
  - `spec/include/npu_demo/npu_demo.md`
  - `spec/tools/dsl_cost_run.md`
  - `spec/tools/dsl_run.md`
- test：
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/include/api/test_cost.py`
  - `test/include/api/test_dma.py`
  - `test/include/api/test_memory.py`
  - `test/include/npu_demo/test_public_namespace.py`
  - `test/tools/test_dsl_cost_run.py`
  - `test/tools/test_emitc_case_runner.py`
- 任务记录：
  - `agents/codex-multi-agents/log/task_records/2026/25/20260525-npu-demo-emitc-brace-list-source-contract.md`

任务记录核对：
- 已核对管理员下发记录、execute 记录、两轮 review 退回记录、execute 返工记录、review 复审通过记录与 archive_acceptance 通过记录。
- 任务记录当前在 worktree 为 untracked，提交前将显式 `git add` 并与代码/spec/test 同批提交。
- archive_acceptance 已对 review 复审标题时间笔误作审计说明；该说明随本记录同批合入。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/copy.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/deslice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reshape.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/slice.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/tools/emitc_case_runner.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_cost.py test/include/api/test_public_namespace.py test/include/npu_demo/test_public_namespace.py`：exit=0，`22 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`170 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_ircheck_runner.py test/tools/test_emitc_case_runner.py`：exit=0，`110 passed, 2 warnings`。
- 主仓只读合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract:/home/lfr/kernelcode_generate python3 -m expectation.dsl.gen_kernel.brace_list_source`：exit=0，输出 `dsl-gen_kernel-brace_list-dma_layout-1` 与 `dsl-gen_kernel-brace_list-cost_layout-1`。
- 导入边界 proof：
  - `expectation_file=/home/lfr/kernelcode_generate/expectation/dsl/gen_kernel/brace_list_source.py`
  - `kernel_gen_file=/home/lfr/kernelcode_generate/wt-20260525-npu-demo-emitc-brace-list-source-contract/kernel_gen/__init__.py`
- `git diff --check`：exit=0。
- `rg -n "Vector\(|Vector\{|long long [A-Za-z0-9_]*(shape|stride)|reshape_shape_|ring_shape_|_shape\[|_stride\[" kernel_gen/dsl/gen_kernel/emit/npu_demo kernel_gen/dsl/gen_kernel/kernel_emitter.py || true`：仅命中说明性注释，未命中实际发射代码。
- `rg -n "_memory_element_cpp_type|_symbol_expr_text|_num_elements_expr|_ring_owner|_emit_ring_slot_view" kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py || true`：输出为空。
- AST private-to-private 扫描：`private_funcs=_emit_npu_demo_dma_advance_ring,_emit_npu_demo_dma_current_ring,_emit_npu_demo_dma_make_ring`，`private_to_private=none`。
- `rg -n "hasattr\(|getattr\([^\n]*ctx|callable\(getattr|from kernel_gen\.[^\n]* import _|import kernel_gen\.[^\n]*\._|def [A-Za-z_][A-Za-z0-9_]*\([^\n]*object|\bobject\b" kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py kernel_gen/tools/emitc_case_runner.py include/npu_demo/cost/Dma.h || true`：输出为空。

敏感目录核对：
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：输出为空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：输出为空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：输出为空。
- 本次 merge 不纳入 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

冲突处理：
- 未发生 merge/rebase 冲突；latest main 未前进。
- 未覆盖主仓或其它任务本地改动。

剩余风险：
- 计划书位于主仓共享路径，任务 worktree 内无计划书副本；本次按 archive_acceptance 记录只读引用主仓共享计划，不提交计划书。
- `expectation.dsl.gen_kernel.brace_list_source` 仅作为当前计划必过合同验收单列，不作为 Diff 反推测试替代；本次未修改 expectation。

结论：
- merge 前核对通过，可提交并推送。
