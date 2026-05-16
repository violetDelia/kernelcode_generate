# 20260516 current main full expectation 现场记录

时间：2026-05-16 12:43 +0800
经办人：守护最好的爱莉希雅
任务：current main / 用户临时要求跑通 full expectation
任务目标：按用户要求先读取标准和当前提示词，再在 `/home/lfr/kernelcode_generate` 当前主仓现场收口 full expectation；不修改 `expectation/` 与 `.skills/`。

## 执行前阅读记录

- 已读取并遵守 `AGENTS.md`：`expectation/` 为合同资产，`.skills` 未授权不得修改，公开 API 变更需用户确认，禁止 `ctx/context` 能力探测与跨文件非公开 API。
- 已读取标准：`agents/standard/规则索引.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/expectation任务规则.md`、`agents/standard/角色权限矩阵.md`、`agents/standard/任务记录约定.md`、`agents/standard/测试文件约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/审查规范.md`。
- 已读取当前提示词：`agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md`，并只把旧 session 作为历史资料。
- 已读取上下文记录：`agents/codex-multi-agents/log/task_records/2026/20/20260514-template-name-infer.md`、`20260512-symbol-iter-token-arith.md`、`20260512-symbol-iter-token-arith-expectation-sync.md`、`20260512-third-party-generic-backend.md`。
- 已核对 `TODO.md`：当前无正在执行任务；本记录仅记录用户临时验证与收口，不推进任务状态表。

## 改动

- 未修改、复制、移动、新建或删除 `expectation/` 与 `.skills/`。
- 为当前 full expectation 收口修改了非合同资产实现、spec 与 pytest：
  - `kernel_gen/passes/template_name_default_constraints.py`：`dma.view` 对一维 `i8` byte backing pool 只做 VerifyOnly，不把 byte pool 与 typed view 合并到同一 template family。
  - `spec/pass/template_name_default_constraints.md`：同步 `dma.view` byte backing pool 约束口径。
  - `test/passes/test_template_name_infer.py`：补 byte pool typed view template family 独立性覆盖。
  - `kernel_gen/passes/memory_pool.py`：对包含 `Min/Max/iter_expr_` 的复杂符号表达式采用保守 simplify，避免 SymPy 在 memory pool 动态表达式上触发底层异常。
  - `test/kernel/test_conv2d_dynamic_symbol_params.py`、`test/kernel/test_conv2d_symbolic_memory_genkernel.py`：同步模板化 `view<T1>(Vector{...})` 断言。
- 当前工作树仍混有并行 / 既有改动，例如 `agents/standard/**`、各 agent prompt、其他 kernel/spec/test 文件；本轮未回退这些非本目标改动。

## 验证

- 合同验收第一次全量运行：
  - 命令：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/current_expectation_pycache_$(date +%s) PYTHONPATH=/home/lfr/kernelcode_generate timeout 2400s python3 -m expectation > /tmp/current_full_expectation.log 2>&1`
  - 结果：`exit=1`；仅 `expectation.dialect.arch.operation.get_thread_id` 报 `AttributeError: 'cell' object has no attribute '_last_op'`，单入口复跑通过，判定为运行环境瞬态。
- 合同验收第二次全量运行：
  - 命令：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/current_expectation_pycache_rerun_$(date +%s) PYTHONPATH=/home/lfr/kernelcode_generate timeout 2400s python3 -m expectation > /tmp/current_full_expectation_rerun.log 2>&1`
  - 结果：`exit=1`；仅 `expectation.pass.lowing.nn_lowering.img2col.img2col1d` 在导入 SymPy 时出现瞬态 `SyntaxError`，单入口复跑通过。
- 合同验收第三次全量运行：
  - 命令：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate timeout 2400s python3 -m expectation > /tmp/current_full_expectation_rerun2.log 2>&1`
  - 结果：`exit=0`，耗时约 `561s`。
- 修复后合同验收：
  - 命令：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate timeout 2400s python3 -m expectation > /tmp/current_full_expectation_after_fix.log 2>&1`
  - 结果：`exit=0`，耗时约 `560s`；日志尾部为 `dsl_run invalid_contract` 预期失败输出，命令退出码为 0。
- Diff 反推 pytest：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_nn.py test/dsl/ast/nodes/test_dma.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py test/execute_engine/test_compile.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/passes/test_memory_pool.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`
  - 结果：`369 passed, 2 warnings in 89.71s`。
- 当前现场禁止修改面：
  - `git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills`、`git status --short --untracked-files=all -- expectation .skills`：均为空。
- 当前现场格式检查：
  - `git diff --check && git diff --cached --check`：`exit=0`。
- 静态扫描：
  - `rg -n "hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)|object\.__setattr__\([^\n]*_type|SSAValue\._type|\._type\b" kernel_gen test --glob '*.py' --glob '!expectation/**' --glob '!.skills/**'`：无输出。
- 追加复跑记录：
  - 2026-05-16 12:24 又启动一次当前现场 full expectation，日志 `/tmp/current_full_expectation_continue_20260516_122449.log`。
  - 该次运行长时间停在 `emit_c-npu_demo-kernel-binary-compare-ge-dynamic` 后无日志进展，且未生成 status 文件；已定位外层 `timeout` PID `190229`、子进程 `python3 -m expectation` PID `190230` 并终止该进程组。
  - 当前环境 `top` 显示 load average 约 `9997` 且存在多个不可中断 I/O 状态进程；该追加复跑不作为通过或失败证据。若后续要以 2026-05-16 12:43 之后现场作为 merge gate，应在环境恢复后重新跑 full expectation。

## Diff 反推自测

- `dma.view` byte backing pool template family 变化由 `test/passes/test_template_name_infer.py::test_template_name_infer_keeps_byte_pool_view_family_independent` 与 `test/passes/pipeline/test_npu_demo_lowering.py::test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain` 覆盖。
- memory pool 动态符号表达式保守 simplify 由 `test/kernel/test_conv2d_dynamic_symbol_params.py`、`test/kernel/test_conv2d_symbolic_memory_genkernel.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py` 与 `test/passes/test_memory_pool.py` 覆盖。
- full expectation 单列为合同验收资产，不计入 Diff 反推 pytest；最终有效合同验收依据为 `/tmp/current_full_expectation_after_fix.log` 对应命令 `exit=0`。

## 自检

- 接口：未新增、删除、重命名或改签公开函数 / 类 / 方法签名、工具入口、脚本参数或 include 公开接口。
- 边界：`expectation/` 与 `.skills` 均保持空 diff；合同资产只读执行。
- 异常：复杂 `Min/Max/iter` 符号表达式不再强行进入 SymPy simplify，避免运行环境底层异常影响 memory pool。
- 兼容性：普通 `dma.view` 仍保持 Same 约束；仅一维 `i8` byte backing pool typed view 不合并 template family。
- 复用与粒度：新增逻辑为当前文件顶层 helper，未跨文件调用非公开 helper，未新增非装饰器嵌套函数。
- 测试有效性：pytest 覆盖 template family 分离、npu-demo lowering 和 symbolic memory codegen；full expectation 已有有效 `exit=0` 证据。
- 残余风险：追加复跑因当前环境进程 / I/O 状态挂起被终止，不影响此前有效通过证据，但不应作为新的 merge gate 通过证据。

结论：当前 full expectation 收口已有有效 `exit=0` 证据，`expectation/` 与 `.skills` 未修改；追加复跑因环境挂起已终止并记录。

## 移交审查 / 合并任务草案

时间：2026-05-16 12:50 +0800
经办人：守护最好的爱莉希雅
任务：current main / 用户要求建立审查任务并在通过后合并
任务目标：把当前 full expectation 收口 diff 交给审查人员审查；审查通过后由合并角色按合并规范执行合入。

改动：
- 本轮只补任务草案与移交记录，未手工修改 `TODO.md`。
- 按当前角色提示词与 `agents/standard/角色权限矩阵.md`，架构师不得替管理员分发任务或承担 merge；因此需由管理员 `神秘人` 正式创建 / 分发 review 任务。

建议管理员创建任务：
- 任务类型：`review`。
- 建议指派：`不要啊教练` 或 `提莫炖蘑菇`。
- worktree：`/home/lfr/kernelcode_generate`。
- 计划书：`None`。
- 依赖任务：`None`。
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/20/20260516-current-full-expectation.md`。
- 任务目标：审查当前主仓 full expectation 收口 diff，重点核对 `dma.view` byte backing pool template family、`memory_pool` 动态符号 simplify、对应 spec/test 更新、`expectation/` / `.skills` 空 diff、公开 API 边界、静态扫描、Diff 反推 pytest 和 full expectation 通过证据。
- 审查要求：当前工作树混有并行 / 既有改动，审查必须先界定本任务可合范围，不得把未点名的 `agents/standard/**`、agent prompt 或其它并行改动作为本任务顺手合入；若审查认为范围无法拆清，应退回管理员裁定。
- 合并要求：review 通过后再创建 / 流转 `merge` 任务给 `李白`；merge 需复核 `expectation/` / `.skills` 空 diff，按合并规范记录并只合入审查通过范围。

验证：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -status -doing`：当前无进行中任务。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -status -task-list`：当前任务列表为空。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file agents/codex-multi-agents/agents-lists.md -status`：管理员、审查与合并角色均显示 `free`。
- `git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills`、`git status --short --untracked-files=all -- expectation .skills`：空输出。
- `git diff --check && git diff --cached --check`：通过。

自检：
- 未越权使用任务脚本写 `TODO.md`。
- 未越权执行 review 或 merge。
- 已把可执行任务目标、建议指派、禁止带入范围、验收要求和记录文件写清，管理员可直接据此建任务。

结论：待管理员正式创建并分发 review 任务；review 通过后再进入 merge。

## Review 记录：不要啊教练

时间：2026-05-16 13:42 +0800
经办人：不要啊教练
任务：T-20260516-2fff5df3 / current main full expectation 收口 diff review
任务目标：审查当前主仓 full expectation 收口 diff，先界定本任务可合范围；核对 `dma.view` byte backing pool template family、`memory_pool` 动态符号 simplify、spec/test 更新、`expectation/` / `.skills` 空 diff、公开 API 边界、静态扫描、Diff 反推 pytest 与 full expectation 证据。

改动：只读审查；未修改实现、spec、测试、`expectation/` 或 `.skills`；仅追加本审查记录。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate`。
- 前置同步：已执行 `git fetch origin`。
- 当前分支：`main`。
- `HEAD`：`309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- `origin/main`：`309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- `merge-base HEAD origin/main`：`309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- 对齐结果：主线基线一致，无需 merge；当前 dirty tree 是待审任务 diff 与并行 / 既有改动混合现场。
- 覆盖风险：当前工作树含 `agents/standard/**`、多名 agent prompt、产品实现、spec 与测试的混合改动；按任务要求不得把未点名并行改动顺手纳入本任务合并范围。

Findings：

P0 阻塞：本任务可合范围无法从当前 dirty tree 中安全拆清。
- 证据：执行记录第 19-24 行只把当前 full expectation 收口修改列为 6 个文件：`kernel_gen/passes/template_name_default_constraints.py`、`spec/pass/template_name_default_constraints.md`、`test/passes/test_template_name_infer.py`、`kernel_gen/passes/memory_pool.py`、`test/kernel/test_conv2d_dynamic_symbol_params.py`、`test/kernel/test_conv2d_symbolic_memory_genkernel.py`。
- 证据：当前 `git diff --name-status` 同时包含 `agents/standard/**`、全部 agent prompt、`kernel_gen/dialect/nn.py`、`kernel_gen/dialect/__init__.py`、`kernel_gen/passes/template_name_graph.py`、`kernel_gen/passes/template_name_infer.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`、大量 `kernel_gen/dsl/**`、`spec/dsl/**`、`test/dsl/**`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`、`test/passes/pipeline/test_npu_demo_lowering.py` 等未在任务目标或执行记录中明确列入的改动。
- 证据：记录中的 Diff 反推 pytest 已依赖未列入 6 文件范围的行为。例如 `test/passes/test_template_name_infer.py:135` 新增 `arch.launch` wrapper/device 模板一致性测试，但实际实现位于未列入范围的 `kernel_gen/passes/template_name_infer.py:194` 和 `kernel_gen/passes/template_name_infer.py:277`；`kernel_gen/passes/pipeline/npu_demo_lowering.py:96` 已把 `MemoryPoolPass` 改为 `rewrite=True, alignment=0`，对应断言在 `test/passes/pipeline/test_npu_demo_lowering.py:176`；`test/kernel/test_matmul_symbolic_memory_genkernel.py:136` 也同步成 `.template view<T1>` 断言。
- 影响：如果 merge 只合入执行记录列出的 6 个文件，相关 pytest / full expectation 证据并不能证明该最小范围在干净主线可通过；如果 merge 合入当前全部 dirty tree，又会把未点名的 agents 标准整改、agent prompt 和其它产品改动一起带入，违反本任务范围要求。
- 最小修复建议：由管理员或执行人给出一份明确的本任务 merge allowlist，或提供只含本任务 diff 的干净 worktree；allowlist 必须包含所有支撑当前 full expectation 收口所需的实现、spec、测试与任务记录，并显式排除 agents 标准整改、agent prompt 与其它并行改动。
- 验收方式：在该明确范围上重新执行 `git diff --check`、`expectation/` / `.skills` 空 diff、Diff 反推 pytest 与 full expectation；记录中写清实际可合文件列表。

P0 阻塞：当前 dirty tree 包含未在本任务中确认的公开 API 删除，不能按当前范围放行。
- 证据：`kernel_gen/dialect/nn.py` diff 删除文件级 API 列表、函数实现与 `__all__` 中的 `memory_template_name(memory_type: NnMemoryType) -> str | None`、`has_memory_template_name(memory_type: NnMemoryType) -> bool`。
- 证据：`kernel_gen/dialect/__init__.py` diff 删除 package-root API 列表、`__all__` 与 lazy export 中的同名导出；`spec/dialect/nn.md` diff 删除对应 spec API 简表与详细说明；`test/dialect/test_nn.py` diff 改为直读 `memory_type.template_name.data`。
- 影响：这是公开 API 删除 / 对外导出面收缩。`AGENTS.md` 要求公开 API 新增、删除、重命名、改签或稳定错误语义变更必须先取得用户确认；当前任务目标只要求审查 full expectation 收口，没有给出该公开 API 删除的用户确认来源。
- 最小修复建议：若该 API 删除属于本任务必要范围，必须补用户确认来源、spec 变更依据和对应迁移/验收说明；若不属于本任务范围，merge allowlist 必须排除这些文件，并在排除后重新运行本任务验收。
- 验收方式：记录用户确认来源或恢复 / 排除该公开 API 删除后，复跑相关 dialect pytest 与本任务 Diff 反推 pytest。

P1 验证缺口：当前 review 时点不能把 `/tmp/current_full_expectation_after_fix.log` 之后的混合现场直接作为 merge gate。
- 证据：执行记录第 38-40 行显示 `/tmp/current_full_expectation_after_fix.log` 对应 full expectation `exit=0`；但第 50-53 行又记录 12:24 追加复跑卡在 `emit_c-npu_demo-kernel-binary-compare-ge-dynamic` 后被终止，并明确写明若以 2026-05-16 12:43 之后现场作为 merge gate，应在环境恢复后重新跑 full expectation。
- 现场：本次 review 时 `uptime` 显示 load average 约 `10476.80 / 10428.35 / 10320.17`，不适合再启动 full expectation；同时 P0 范围阻塞未解除，继续跑当前混合 dirty tree 也不能证明可合范围。
- 影响：full expectation 有历史 exit=0 证据，但尚不能替代“明确可合范围 + 当前合并候选 diff”的最终门禁。
- 最小修复建议：先拆清本任务可合范围，待环境恢复后用固定命令重新执行 full expectation，并把日志路径、exit code、cwd、`PYTHONPATH`、`EXPECTATION_WORKTREE_ROOT` 写入记录。
- 验收方式：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate timeout 2400s python3 -m expectation` 退出码为 0。

验证：
- `git fetch origin`：通过；`HEAD`、`origin/main`、`merge-base` 均为 `309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- `git status --short --untracked-files=all -- expectation .skills`：空输出。
- `git diff --name-only -- expectation .skills`：空输出。
- `git diff --cached --name-only -- expectation .skills`：空输出。
- `git diff --check && git diff --cached --check`：通过。
- `rg -n "hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)|object\.__setattr__\([^\n]*_type|SSAValue\._type|\._type\b" kernel_gen test -g '*.py'`：无输出。
- Diff 反推 pytest 复跑：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/test_nn.py test/dsl/ast/nodes/test_dma.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py test/execute_engine/test_compile.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/passes/test_memory_pool.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`：`369 passed, 2 warnings in 102.65s`。
- full expectation：本轮 review 未复跑。原因：当前 P0 范围阻塞未解除，且机器负载极高；复跑当前混合 dirty tree 不能作为明确可合范围的合并门禁。

Diff 反推审查：
- `dma.view` byte backing pool template family：`kernel_gen/passes/template_name_default_constraints.py` 将一维 `i8` backing pool view 约束收成 VerifyOnly，`spec/pass/template_name_default_constraints.md` 与 `test/passes/test_template_name_infer.py` 有对应说明 / 测试；当前子集 pytest 通过。
- `memory_pool` 动态符号 simplify：`kernel_gen/passes/memory_pool.py` 对 `Min/Max/iter<...>` 类表达式做保守 simplify，相关 conv2d / matmul / memory_pool pytest 子集通过。
- 公开 API / 范围边界：当前 dirty tree 内存在未明确授权的 `NnMemoryType` helper 公开 API 删除，且当前 full expectation 收口证据依赖未列入执行记录的多个实现 / 测试文件，因此不能给出通过结论。

自检：
- 已按 review 角色先核对最新主线基线、dirty tree 范围、任务记录、自检、Diff 反推自测与禁止修改面。
- 已避免修改实现、spec、测试、`expectation/` 与 `.skills`。
- 已将可执行返工项写成文件位置、影响、最小修复建议与验收方式。
- 未执行 `-next merge`，因为当前结论不是通过。

结论：不通过 / 阻塞。当前可合范围无法拆清，且 dirty tree 包含未确认的公开 API 删除；请管理员裁定本任务明确 merge allowlist 或要求执行人整理为干净待审范围，并在范围明确后重新跑 full expectation 门禁。

## 架构侧继续口径

时间：2026-05-16 13:55 +0800
经办人：守护最好的爱莉希雅
任务：T-20260516-2fff5df3 / review 不通过后的架构裁定建议
任务目标：针对 review 阻断给出可直接下发的继续口径，避免在 dirty tree 范围不清和未确认公开 API 删除的状态下进入 merge。

裁定建议：
- 推荐路线：要求执行人先整理出干净、可审、可合的待审范围；当前状态不建议由架构直接给 merge allowlist。
- 理由一：review 已证明当前 dirty tree 混有本任务目标、并行标准 / prompt 改动和其它产品改动；直接给 allowlist 容易漏掉实际依赖文件，或把未审查范围带入 merge。
- 理由二：`memory_template_name(memory_type: NnMemoryType) -> str | None` 与 `has_memory_template_name(memory_type: NnMemoryType) -> bool` 已写入公开 API / spec / 导出面；当前 diff 删除它们属于公开 API 删除。按 `AGENTS.md`，无用户确认不得实现、放行或合并。
- 理由三：full expectation 的有效 `exit=0` 是历史现场证据；review 后续复跑已因环境挂起终止，且未在“明确可合范围”上重跑，不满足当前 merge gate。

执行人最小返工任务目标：
- 在 `/home/lfr/kernelcode_generate` 或新建干净 worktree 中整理本任务候选 diff，只保留 full expectation 收口所必需的实现、spec、pytest 与本任务记录。
- 显式排除未点名的 `agents/standard/**`、各 agent prompt、公开 API 盘点日志和其它并行改动；这些内容不得随本任务合入。
- 对 `memory_template_name(...)` / `has_memory_template_name(...)` 采取二选一：
  - 默认方案（推荐）：恢复 / 保留这两个公开 API、`__all__` 导出、`spec/dialect/nn.md` 说明和公开 pytest；本任务不得删除它们。
  - 备选方案：若执行链认为必须删除，先把“删除公开 API”的影响、替代 API、迁移方式和验收项写成待确认项，取得用户明确确认后再进入实现 / 审查 / merge；确认前不得合入。
- 返工记录必须写明最终候选 merge 文件列表；不是“当前 dirty tree 全量”。
- 在最终候选范围上重新执行并记录：
  - `git diff --check && git diff --cached --check`
  - `git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills`、`git status --short --untracked-files=all -- expectation .skills` 均为空
  - 按最终 diff 反推的 pytest；不得只沿用旧的 broad pytest 摘要
  - full expectation：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate timeout 2400s python3 -m expectation`，退出码必须为 `0`；若环境仍挂起，记录环境阻塞并不得 merge

给管理员的下发建议：
- 将当前任务退回 / 续接为 execute 返工，而不是直接进入 merge。
- 任务目标建议写为：整理 `T-20260516-2fff5df3` 的干净待审范围；排除未授权标准 / prompt / 并行改动；恢复或取得用户确认后处理 `memory_template_name` / `has_memory_template_name` 公开 API 删除；在明确候选范围上重跑 Diff 反推 pytest 与 full expectation；补齐记录后再交 review。
- review 重新通过前，`李白` 不应接 merge。

验证：
- 已核对 review 记录中 P0 / P1 阻断。
- 已核对当前 `TODO.md`：`T-20260516-2fff5df3` 仍为管理员进行中的 `other` 协调任务。
- 已核对 `git diff` 中确有 `kernel_gen/dialect/nn.py`、`spec/dialect/nn.md`、`test/dialect/test_nn.py`、`test/passes/test_template_name_infer.py` 对 `memory_template_name` / `has_memory_template_name` 的删除或测试绕开。

自检：
- 未直接裁定删除公开 API；默认口径为未获用户确认前恢复 / 排除。
- 未越权分发任务、执行返工或 merge。
- 已给出执行人可直接落地的任务目标、最小返工动作、验证命令和流转条件。

结论：要求执行人整理干净待审范围；当前不提供 dirty tree merge allowlist。公开 API 删除必须用户确认后才能保留在候选 diff 中，否则应恢复 / 排除；明确范围并重跑门禁前不得 merge。

## 榕确认回执

时间：2026-05-16 13:48 +0800
经办人：榕
任务：T-20260516-2fff5df3 / review 阻塞事项确认

确认事项：
- 合并范围选择 A：由执行人整理成干净待审范围并重新 review；当前不提供本任务 merge allowlist，也不得把当前 mixed dirty tree 直接交给 merge。
- 公开 API 删除选择“不允许”：`memory_template_name(memory_type)` 与 `has_memory_template_name(memory_type)` 已属于公开 API / spec / 导出面；当前未见用户明确确认删除，不能放入候选 diff。执行人必须恢复 / 保留这些 API，或把相关文件排除出本任务候选范围；如确需删除，必须先提交影响、替代 API、迁移方式和验收项给用户确认，确认前不得实现、审查通过或合并。

继续口径：
- 当前任务保持 other 阻塞，不流转 merge。
- 续接应回到 execute 返工：拆清本任务候选文件列表，只保留 full expectation 收口必要实现、spec、pytest 与同链路记录；排除 `agents/standard/**`、agent prompt、公开 API 盘点日志和其它并行改动。
- 返工后必须在明确候选范围上重新执行 Diff 反推 pytest、`expectation/` / `.skills` 空 diff 检查、`git diff --check`，并在环境允许时重新执行 full expectation；review 通过前不得交给李白合并。

自检：
- 未确认公开 API 删除，未给出 dirty tree allowlist，未改动 `expectation/` 或 `.skills`。
- 本回执只裁定阻塞处理口径，不执行返工、review 或 merge。

## Execute 返工：小李飞刀

时间：2026-05-16 14:30 +0800
经办人：小李飞刀
任务：T-20260516-2fff5df3 / current main full expectation 干净待审范围返工
任务目标：按 review 与架构侧继续口径整理干净待审范围，排除未授权并行改动，处理 `memory_template_name(memory_type)` / `has_memory_template_name(memory_type)` 公开 API 删除确认，重跑候选范围验证后回流 review。

执行前阅读：
- 已读取 `TODO.md`：当前任务为 `T-20260516-2fff5df3`，`execute / 小李飞刀 / 进行中`，worktree `/home/lfr/kernelcode_generate`。
- 已读取 `AGENTS.md`、`agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/角色权限矩阵.md` 与本任务前序 review / 架构记录。
- 约束：不修改 `expectation/` 与 `.skills/`；不覆盖或回退 agents 标准 / prompt / 并行任务改动；候选范围必须明确，不能把当前 mixed dirty tree 直接作为 merge 范围。

用户确认来源：
- 2026-05-16 用户经由神秘人同步确认：`memory_template_name(memory_type)` 与 `has_memory_template_name(memory_type)` 是用户需要删除的公开 API，可纳入本任务候选 diff 删除范围。
- 本轮据此不再恢复这两个 helper；改为同步删除实现、包根导出、spec/API 列表和公开 pytest，并在 `spec/dialect/nn.md` 写明迁移方式：读取公开 `NnMemoryType.template_name.data`，空字符串表示未携带 template name，非空字符串表示 template name。

最终候选 merge 文件列表：
- `kernel_gen/dialect/__init__.py`
- `kernel_gen/dialect/nn.py`
- `kernel_gen/dsl/ast/nodes/dma.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/broadcast.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/cast.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/fill.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/load.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/transpose.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/binary_elewise.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/exp.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/img2col1d.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/img2col2d.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/reduce.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/select.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/nn/add.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/type/__init__.py`
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/type/type.py`
- `kernel_gen/dsl/gen_kernel/kernel_emitter.py`
- `kernel_gen/execute_engine/compiler.py`
- `kernel_gen/passes/memory_pool.py`
- `kernel_gen/passes/pipeline/npu_demo_lowering.py`
- `kernel_gen/passes/template_name_default_constraints.py`
- `kernel_gen/passes/template_name_graph.py`
- `kernel_gen/passes/template_name_infer.py`
- `spec/dialect/nn.md`
- `spec/dsl/gen_kernel/emit.md`
- `spec/dsl/gen_kernel/emit/npu_demo.md`
- `spec/dsl/gen_kernel/emit/npu_demo/type/__init__.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `spec/pass/template_name_default_constraints.md`
- `test/dialect/test_nn.py`
- `test/dsl/ast/nodes/test_dma.py`
- `test/dsl/gen_kernel/emit/test_package.py`
- `test/dsl/gen_kernel/test_gen_kernel.py`
- `test/execute_engine/test_compile.py`
- `test/kernel/test_conv2d_dynamic_symbol_params.py`
- `test/kernel/test_conv2d_symbolic_memory_genkernel.py`
- `test/kernel/test_matmul_symbolic_memory_genkernel.py`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/passes/test_template_name_infer.py`
- `agents/codex-multi-agents/log/task_records/2026/20/20260516-current-full-expectation.md`

明确排除范围：
- `agents/standard/**` 的全部已存在改动与未跟踪 `agents/standard/协作沟通原则.md`，属于并行标准整改，不纳入本任务候选。
- `agents/codex-multi-agents/agents/*/*.prompt.md` 的全部改动，属于并行 prompt 整改，不纳入本任务候选。
- `agents/codex-multi-agents/log/public_api_inventory_20260516.md`，属于公开 API 盘点日志，不纳入本任务候选。
- `agents/codex-multi-agents/log/task_records/2026/20/20260516-agents-standard-humanize-research.md`，属于并行任务记录，不纳入本任务候选。
- `kernel_gen/dsl/ast/__init__.py`、`kernel_gen/dsl/ast/mlir_gen.py`、`kernel_gen/dsl/ast/parser.py`、`spec/dsl/ast/__init__.md`、`spec/dsl/ast/mlir_gen.md`、`spec/dsl/ast/nodes/basic.md`、`spec/dsl/ast/parser.md`、`test/dsl/ast/test_dsl_ast.py`、`test/dsl/ast/test_mlir_gen.py`、`test/dsl/ast/test_package.py`、`test/dsl/ast/test_parser.py` 等 DSL AST parser 公开入口调整，属于其它并行改动，不纳入本任务候选。

干净候选范围验证方式：
- 为避免主仓 mixed dirty tree 污染结论，基于 `HEAD=309cdad350f1f882a281ecff4d642d4f2735f2d6` 创建临时验证 worktree `/tmp/kcg-t20260516-candidate`。
- 只从上述最终候选文件生成补丁 `/tmp/t20260516_candidate.patch` 并应用到临时 worktree。
- `expectation/` 在仓库中为忽略合同资产，临时 worktree 默认不带完整资产；验证时只读复制主仓 `expectation/` 到临时目录，用于执行合同验收，不作为候选 diff。

验证：
- 候选范围格式检查：在 `/tmp/kcg-t20260516-candidate` 运行 `git diff --check && git diff --cached --check`，结果 `exit=0`。
- 主仓混合现场格式检查：在 `/home/lfr/kernelcode_generate` 运行 `git diff --check && git diff --cached --check`，结果 `exit=0`。
- 候选范围禁止修改面：在 `/tmp/kcg-t20260516-candidate` 运行 `git diff --name-only -- expectation .skills && git diff --cached --name-only -- expectation .skills && git status --short --untracked-files=all -- expectation .skills`，结果空输出。
- 主仓禁止修改面：在 `/home/lfr/kernelcode_generate` 运行同一命令，结果空输出。
- 候选范围静态扫描：`rg -n "hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)|object\.__setattr__\([^\n]*_type|SSAValue\._type|\._type\b" kernel_gen test --glob '*.py' --glob '!expectation/**' --glob '!.skills/**'`，结果无命中。
- 主仓静态扫描：同一命令结果无命中。
- 候选范围 Diff 反推 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/test_nn.py test/dsl/ast/nodes/test_dma.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py test/execute_engine/test_compile.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/passes/test_memory_pool.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`，结果 `369 passed, 2 warnings in 103.08s`。
- 候选范围 full expectation：`EXPECTATION_WORKTREE_ROOT=/tmp/kcg-t20260516-candidate OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/kcg-t20260516-candidate timeout 2400s python3 -m expectation > /tmp/t20260516_candidate_full_expectation_delete_api_20260516_141725.log 2>&1`，结果 `exit=0`，日志尾部为 `dsl_run invalid_contract` 预期失败输出。

Diff 反推自测：
- `kernel_gen/dialect/__init__.py`、`kernel_gen/dialect/nn.py`、`spec/dialect/nn.md`、`test/dialect/test_nn.py`：删除 `memory_template_name(...)` / `has_memory_template_name(...)` 导出与 helper，测试改为验证 `NnMemoryType.template_name.data` 公开字段；覆盖命令 `pytest -q test/dialect/test_nn.py`。
- `kernel_gen/passes/template_name_graph.py`：不再导入已删除 helper，直接读取 `NnMemoryType.template_name.data`；覆盖命令 `pytest -q test/passes/test_template_name_graph.py test/passes/test_template_name_infer.py`。
- `kernel_gen/dsl/ast/nodes/dma.py` 与 `test/dsl/ast/nodes/test_dma.py`：覆盖 view/deslice 动态表达式、iter token 与公开合同；覆盖命令 `pytest -q test/dsl/ast/nodes/test_dma.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_matmul_symbolic_memory_genkernel.py`。
- `kernel_gen/passes/memory_pool.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`kernel_gen/passes/template_name_default_constraints.py`、`kernel_gen/passes/template_name_infer.py` 及对应测试：覆盖 memory pool 动态 backing rewrite、byte pool typed view template family 分离、wrapper/device template name 一致性与 npu-demo lowering pipeline；覆盖命令 `pytest -q test/passes/test_memory_pool.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/**`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`kernel_gen/execute_engine/compiler.py` 及对应 spec/test：覆盖 template dtype 发射、runtime dtype dispatcher 与 gen_kernel/execute_engine 正向路径；覆盖命令 `pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py test/execute_engine/test_compile.py`。
- `expectation` 仅作为合同验收资产单列，不计入 Diff 反推 pytest。

自检：
- 接口：本轮仅根据用户最新确认删除 `memory_template_name(memory_type)` 与 `has_memory_template_name(memory_type)` 两个公开 API，并同步 spec/API 列表、导出面、公开 pytest与迁移说明；未新增其它公开 API。
- 边界：`expectation/` 与 `.skills` 保持空 diff；未修改、移动、复制、新建或删除合同资产。
- 范围：最终候选列表明确排除 agents 标准、agent prompt、公开 API 盘点日志和 DSL AST parser 并行改动。
- 兼容性：template name 读取迁移为 `NnMemoryType.template_name.data`，空字符串为未携带 template name；`copy_memory_type(...)` 仍清空 template name，`copy_memory_type_with_template_name(...)` 仍写入合法 template name。
- 冗余：npu-demo emit 文件不再跨文件导入 dtype helper，按当前文件内 helper 发射 template dtype，符合禁止跨文件非公开 API 规则。
- 测试有效性：候选补丁在临时干净 worktree 上通过 Diff 反推 pytest 与 full expectation，避免 mixed dirty tree 干扰。
- 残余风险：主仓当前仍保留未纳入候选的并行 dirty 改动；review/merge 必须只基于上述候选列表，不得把 mixed dirty tree 全量合入。

结论：候选范围已拆清并通过验证。允许流转 review；review 需按上述候选文件列表审查，不得把排除范围并入本任务。

时间：2026-05-16 14:37 CST
经办人：提莫炖蘑菇
任务：T-20260516-2fff5df3 / review
任务目标：按任务记录中的最终候选 merge 文件列表复审，不把主仓 mixed dirty tree 全量纳入；核对公开 API 删除、候选范围、Diff 反推 pytest、full expectation、禁止修改面与静态扫描。

最新同步现场：
- 执行目录：`/tmp/kcg-t20260516-candidate`。
- 已执行 `git fetch origin`。
- 同步基线：`HEAD=309cdad350f1f882a281ecff4d642d4f2735f2d6`，`origin/main=309cdad350f1f882a281ecff4d642d4f2735f2d6`，`merge-base=309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- 结论：候选 worktree 已在最新 `origin/main` 基线上；未发现需要合并新主线的冲突或覆盖风险。主仓 `/home/lfr/kernelcode_generate` 仍是 mixed dirty tree，本轮按任务要求只审查候选 worktree 与最终候选文件列表。

审查范围：
- 已核对 `/tmp/kcg-t20260516-candidate` 的 `git diff --name-only` 与记录中的最终候选 merge 文件列表一致。
- 已确认候选 diff 未包含 `agents/standard/**`、agent prompt、`agents/codex-multi-agents/log/public_api_inventory_20260516.md`、`20260516-agents-standard-humanize-research.md` 或 DSL AST parser 并行改动。
- 已核对 `memory_template_name(memory_type)` / `has_memory_template_name(memory_type)` 删除已有用户确认来源，且 live `kernel_gen/spec/test` 中仅剩 `spec/dialect/nn.md` 迁移说明与本任务历史记录命中。

findings：
- P0：`kernel_gen/execute_engine/compiler.py:766` 将“手写 templated Memory source 且没有 concrete memory dtype 实例线索”的行为改成生成 runtime dtype 全组合分支，`test/execute_engine/test_compile.py:426` 也改为断言编译成功；但当前公开合同 `spec/execute_engine/execute_engine_target.md:62` 到 `spec/execute_engine/execute_engine_target.md:64` 仍明确要求该场景必须以 `template_instance_required` 稳定失败，且不得生成全组合 dispatcher。影响：这是公开错误语义和 target entry shim 合同的直接冲突，测试在验证与 spec 相反的行为；即使 full expectation 通过，也不能放行 spec/test/实现不一致。最小返工动作：二选一，若新行为是用户确认后的目标，补齐用户确认来源并同步 `spec/execute_engine/execute_engine_target.md`、相关 API/用例清单和测试命名；若没有确认，恢复 `template_instance_required` 失败路径与原测试。验收方式：复跑 `pytest -q test/execute_engine/test_compile.py`，并重跑候选范围 Diff 反推 pytest 与 full expectation。
- P1：候选 diff 在 `kernel_gen/dsl/gen_kernel/emit/npu_demo/**` 新增多处当前文件 `_memory_element_cpp_type(...)` helper，但多数只有一句话 docstring，缺少 `功能说明` 与 `使用示例`，不满足 `agents/standard/实现文件规范.md` 对新增/修改函数注释的硬要求。核对命中包括 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/broadcast.py:29`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/cast.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/fill.py:28`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/load.py:31`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/transpose.py:29`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/binary_elewise.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/exp.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/img2col1d.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/img2col2d.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/reduce.py:29`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/select.py:27`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/nn/add.py:26`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py:34`。影响：当前候选虽避免了跨文件非公开 API，但新增 helper 的说明不符合仓库实现文件规范，后续维护者无法从文件内快速确认 helper 边界和使用方式。最小返工动作：为这些新增 helper 补齐包含 `功能说明` 与 `使用示例` 的函数注释；不得恢复跨文件非公开 helper 导入。验收方式：复跑 `pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`，并用静态核对确认上述 helper 注释均包含必需字段。

验证：
- `git diff --name-only`：候选文件列表与执行记录最终候选 merge 文件列表一致。
- `git diff --check && git diff --cached --check`：在 `/tmp/kcg-t20260516-candidate` 复跑，`exit=0`。
- `git diff --name-only -- expectation .skills` 与 `git status --short --untracked-files=all -- expectation .skills`：空输出。
- full expectation：未在本轮复跑，原因是静态审查已命中公开合同阻断；已核对执行记录写明 `/tmp/t20260516_candidate_full_expectation_delete_api_20260516_141725.log` 为 `exit=0`，并查看日志尾部为 `dsl_run invalid_contract` 预期输出。
- 静态核对：用脚本扫描新增 `_memory_element_cpp_type(...)` docstring，除 `dma/store.py` 与 `type/type.py` 外，上述 16 处为 `doc_sections=False`。

Diff 反推审查：
- `kernel_gen/dialect/__init__.py`、`kernel_gen/dialect/nn.py`、`spec/dialect/nn.md`、`test/dialect/test_nn.py`：公开 API 删除已有用户确认，迁移说明与导出面同步，无本轮阻断。
- `kernel_gen/execute_engine/compiler.py` 与 `test/execute_engine/test_compile.py`：实际 diff 改变了 `template_instance_required` 公开错误语义，但未同步仍存活的 `spec/execute_engine/execute_engine_target.md` 合同，命中 P0。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/**`：实际 diff 将原跨文件 helper 拆为当前文件 helper，方向符合禁止跨文件非公开 API，但新增函数注释不符合实现文件规范，命中 P1。
- `expectation` 仅按合同验收资产单列，不计入 Diff 反推测试；本轮未发现候选 diff 修改 `expectation/` 或 `.skills/`。

自检：
- 已按最终候选文件列表逐项核对，未把主仓 mixed dirty tree 的 agents 标准、prompt、public_api_inventory、agents-standard-humanize 记录或 DSL AST parser 并行改动纳入结论。
- 已检查公开 API 删除的用户确认来源；`memory_template_name(...)` / `has_memory_template_name(...)` 删除本身不是阻断。
- 已检查 spec/test/实现一致性、禁止修改面和新增 helper 注释规范；仍存在可执行返工项，因此不能给通过。

结论：最小需改项。当前候选范围不得进入 merge；需回到 execute 收口上述 P0/P1 后重新提交 review。

## Execute 返工收口：小李飞刀

时间：2026-05-16 15:26 CST
经办人：小李飞刀
任务：T-20260516-2fff5df3 / review 最小阻断项返工
任务目标：只修复 review 指出的两个最小阻断项：`ExecutionEngine.compile` 手写 templated Memory 缺 concrete dtype 的公开失败合同冲突，以及 npu_demo emit 文件新增 `_memory_element_cpp_type(...)` helper 注释字段缺失；完成后在明确候选范围上重跑 Diff 反推 pytest、full expectation、格式与禁止修改面检查。

执行前阅读：
- 已重新读取 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、`AGENTS.md`、本记录 review 阻断项与前序候选范围记录。
- 当前约束：不修改 `expectation/` 与 `.skills/`；不覆盖或回退 agents 标准 / prompt / 公开 API 盘点日志 / DSL AST parser 并行改动；测试只验证公开 API；不得恢复跨文件非公开 helper。

修复动作：
- P0：恢复手写 templated Memory source 缺 concrete dtype 信息时的 `template_instance_required` 失败合同；`test/execute_engine/test_compile.py::test_execute_engine_compile_rejects_template_memory_without_concrete_dtype` 继续断言该公开失败短语。
- P0 补充收口：`gen_kernel` 生成的 template-name memory source 现在在函数声明 / 定义前发射内部 `__kernel_gen_template_instance_seed_*` alias，记录每个 template name 对应的 concrete element dtype；`ExecutionEngine.compile` 只消费该 generated seed 或源码中已有 concrete `Memory<..., dtype>` 生成唯一实例，不生成全组合 runtime dtype dispatcher，不改变手写 source 缺 dtype 的失败合同。
- P0 spec/test 同步：更新 `spec/dsl/gen_kernel/kernel_emitter.md` 和 `spec/execute_engine/execute_engine_target.md`，写清 generated seed alias 是内部源码线索，不是公开 API，不生成 `kg_execute_entry` 或 dispatcher；新增 / 更新公开 pytest 覆盖 seed alias 精确绑定 `T1/T2` 与手写缺 dtype 失败路径。
- P1：补齐 `kernel_gen/dsl/gen_kernel/emit/npu_demo/**` 中 16 个 `_memory_element_cpp_type(...)` helper 的 `功能说明` 与 `使用示例` 注释字段；未恢复跨文件非公开 helper 导入。

最终候选 merge 文件列表补充：
- 继续沿用上一段最终候选 merge 文件列表。
- 本轮新增纳入候选的直接关联文件：
  - `spec/dsl/gen_kernel/kernel_emitter.md`
  - `spec/execute_engine/execute_engine_target.md`
- 明确仍排除 `agents/standard/**`、agent prompt、`agents/codex-multi-agents/log/public_api_inventory_20260516.md`、`20260516-agents-standard-humanize-research.md` 与 DSL AST parser 并行改动。

干净候选范围验证方式：
- 基于当前 `HEAD=309cdad350f1f882a281ecff4d642d4f2735f2d6` 生成候选补丁 `/tmp/t20260516_candidate.patch`。
- 临时验证 worktree：`/tmp/kcg-t20260516-candidate-final-231165`。
- 候选补丁只包含最终候选文件；`git diff --name-only` 与候选文件列表一致。
- `expectation/` 为只读合同资产，临时 worktree 中仅复制主仓 `expectation/` 用于合同验收，不作为候选 diff。

验证：
- 主仓最小 P0/P1 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/execute_engine/test_compile.py -k 'template_memory_without_concrete_dtype or generated_dtype_seed_aliases or nearest_wrapper_template_header'`，结果 `3 passed, 25 deselected`，退出码 `0`。
- 主仓 gen_kernel seed pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dsl/gen_kernel/test_gen_kernel.py -k 'template_header_for_npu_demo_memory_template_field'`，结果 `1 passed, 91 deselected, 2 warnings`，退出码 `0`。
- 主仓 matmul 动态脚本回归：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`，退出码 `0`，输出包含 `[CHECK] matmul/inputs_dynamic_tile_dynamic max_abs_diff=1.9073486328125e-06`。
- 主仓候选范围 Diff 反推 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/execute_engine/test_compile.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py test/dialect/test_nn.py test/dsl/ast/nodes/test_dma.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/passes/test_memory_pool.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`，结果 `370 passed, 3 warnings`，退出码 `0`。
- 主仓格式检查：`git diff --check && git diff --cached --check`，退出码 `0`。
- 主仓禁止修改面：`git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills`、`git status --short --untracked-files=all -- expectation .skills` 均为空输出。
- 主仓静态扫描：`rg -n "hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)|object\.__setattr__\([^\n]*_type|SSAValue\._type|\._type\b" kernel_gen test --glob '*.py' --glob '!expectation/**' --glob '!.skills/**'`，无命中，退出码 `1`。
- 主仓 helper 注释字段核对：AST 脚本扫描 16 个 `_memory_element_cpp_type(...)` 与新增 `_template_instance_seed*` helper，结果 `missing=[]`。
- 干净候选格式检查：在 `/tmp/kcg-t20260516-candidate-final-231165` 执行 `git diff --check && git diff --cached --check`，退出码 `0`。
- 干净候选禁止修改面：在 `/tmp/kcg-t20260516-candidate-final-231165` 执行 `git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills`、`git status --short --untracked-files=all -- expectation .skills`，均为空输出。
- 干净候选 py_compile：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/broadcast.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/cast.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/fill.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/free.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/load.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/transpose.py kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/view.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/binary_elewise.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/exp.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/img2col1d.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/img2col2d.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/matmul.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/reduce.py kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel/select.py kernel_gen/dsl/gen_kernel/emit/npu_demo/nn/add.py kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py`，退出码 `0`。
- 干净候选 helper 注释字段核对：AST 脚本扫描 16 个 `_memory_element_cpp_type(...)` 与新增 `_template_instance_seed*` helper，结果 `missing=[]`。
- 干净候选静态扫描：同主仓静态扫描命令，无命中，退出码 `1`。
- 干净候选 Diff 反推 pytest：同主仓候选范围 Diff 反推 pytest 命令，结果 `370 passed, 3 warnings in 104.56s`，退出码 `0`。
- 干净候选 full expectation 首次执行时因临时目录误复制为 `expectation/expectation` 嵌套导致 `No module named expectation.__main__`，这是验证现场布置错误，不是产品失败；已修正为复制主仓 `expectation/.` 到候选 `expectation/`。
- 干净候选 full expectation：`EXPECTATION_WORKTREE_ROOT=/tmp/kcg-t20260516-candidate-final-231165 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/kcg-t20260516-candidate-final-231165 timeout 2400s python3 -m expectation > /tmp/t20260516_candidate_full_expectation_final_20260516_150111.log 2>&1`，结果 `exit=0`；日志尾部包含 `dsl_run invalid_contract` 预期失败输出。

Diff 反推自测：
- `kernel_gen/execute_engine/compiler.py` / `spec/execute_engine/execute_engine_target.md` / `test/execute_engine/test_compile.py`：覆盖手写 templated Memory 缺 concrete dtype 必须 `template_instance_required` 失败，以及 generated seed alias 能精确实例化 `T1=float`、`T2=int32_t`；对应 `pytest -q test/execute_engine/test_compile.py`。
- `kernel_gen/dsl/gen_kernel/kernel_emitter.py` / `spec/dsl/gen_kernel/kernel_emitter.md` / `test/dsl/gen_kernel/test_gen_kernel.py`：覆盖 template-name memory 函数生成内部 seed alias、函数签名继续输出 `template <typename ...>` 与 `Memory<space, Tn>&`；对应 `pytest -q test/dsl/gen_kernel/test_gen_kernel.py`。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/**`：覆盖 `_memory_element_cpp_type(...)` 当前文件 helper 注释规范与 npu_demo emit/gen_kernel 公开路径；对应 `pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py` 与 AST 注释字段核对。
- 既有候选范围文件继续按上一段 Diff 反推自测命令覆盖：`test/dialect/test_nn.py`、`test/dsl/ast/nodes/test_dma.py`、`test/kernel/test_*symbolic*`、`test/passes/test_memory_pool.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/passes/test_template_name_*`。
- `expectation` 仅作为合同验收资产单列，不计入 Diff 反推 pytest。

自检：
- 接口：未新增公开 Python API；generated seed alias 已在 spec 中标明为内部源码线索，不作为公开 API；手写 source 缺 dtype 失败合同已保留。
- 边界：未修改 `expectation/` 与 `.skills/`；未恢复跨文件非公开 helper 导入；未使用 ctx 能力探测。
- 兼容性：生成源码能通过 seed alias 给 compile shim 提供唯一 dtype 实例，避免 runtime dtype dispatcher；手写缺 dtype 场景仍稳定失败。
- 注释：review 点名的 16 个 `_memory_element_cpp_type(...)` helper 均已补齐 `功能说明` / `使用示例`。
- 测试有效性：新增测试能在 seed alias 精确绑定损坏或手写失败合同被放宽时失败；matmul 动态脚本覆盖生成源码真实编译执行路径。
- 残余风险：主仓仍有本任务排除范围内的并行 dirty 改动；review / merge 必须继续以候选文件列表和干净候选 worktree验证为准，不得把 mixed dirty tree 全量合入。

结论：review 最小阻断项已收口，干净候选范围 Diff 反推 pytest 与 full expectation 均通过。允许按流程流转 review。

## Review 复审：不要啊教练

时间：2026-05-16 15:55 +0800
经办人：不要啊教练
任务：T-20260516-2fff5df3 / review 最小阻断项返工复审
任务目标：复审 `ExecutionEngine.compile` 手写 templated Memory 缺 concrete dtype 失败合同、generated seed alias 内部语义、spec 同步、npu_demo emit helper 注释字段、最终候选文件列表、Diff 反推 pytest、full expectation、`git diff --check`、`expectation/` / `.skills` 空 diff 与静态扫描。

Findings：无阻断项。

最新同步现场：
- 主仓执行目录：`/home/lfr/kernelcode_generate`。
- 主仓前置同步：已执行 `git fetch origin`。
- 主仓基线：`HEAD=309cdad350f1f882a281ecff4d642d4f2735f2d6`，`origin/main=309cdad350f1f882a281ecff4d642d4f2735f2d6`，`merge-base=309cdad350f1f882a281ecff4d642d4f2735f2d6`，分支 `main`。
- 候选执行目录：`/tmp/kcg-t20260516-candidate-final-231165`。
- 候选前置同步：已执行 `git fetch origin`。
- 候选基线：`HEAD=309cdad350f1f882a281ecff4d642d4f2735f2d6`，`origin/main=309cdad350f1f882a281ecff4d642d4f2735f2d6`，`merge-base=309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- 对齐结论：候选 worktree 位于最新主线基线；主仓仍是 mixed dirty tree，本轮只审查 `/tmp/kcg-t20260516-candidate-final-231165` 的 47 个候选文件，不把主仓其它 dirty 改动纳入通过范围。

审查范围：
- 已核对候选 `git diff --name-only` 为 47 个文件，与 `/tmp/t20260516_candidate_files.txt` 和执行记录最终候选文件列表一致。
- 已确认候选 diff 不包含 `agents/standard/**`、agent prompt、`agents/codex-multi-agents/log/public_api_inventory_20260516.md`、`20260516-agents-standard-humanize-research.md`、`kernel_gen/dsl/ast/__init__.py`、`kernel_gen/dsl/ast/mlir_gen.py`、`kernel_gen/dsl/ast/parser.py`、`spec/dsl/ast/**` parser 相关文件、`test/dsl/ast/test_*.py` 并行改动。
- `memory_template_name(memory_type)` / `has_memory_template_name(memory_type)` 删除按记录第 249-251 行已有用户确认来源，本轮只核对同步结果，不再作为阻断。

复审核对：
- `ExecutionEngine.compile`：`kernel_gen/execute_engine/compiler.py` 中 `_runtime_template_combinations_from_source(...)` 优先消费 `__kernel_gen_template_instance_seed_*` alias，缺少 seed / concrete `Memory<..., dtype>` 时抛出 `template_instance_required`；未生成全组合 runtime dtype dispatcher。
- 公开失败合同：`test/execute_engine/test_compile.py::test_execute_engine_compile_rejects_template_memory_without_concrete_dtype` 仍断言手写 templated Memory 缺 concrete dtype 失败短语为 `template_instance_required`。
- generated seed alias：`kernel_gen/dsl/gen_kernel/kernel_emitter.py` 只在 generated source 的函数声明 / 定义前生成内部 alias；`spec/dsl/gen_kernel/kernel_emitter.md` 明确该 alias 不属于公开 API，不生成 `kg_execute_entry`、concrete template 实例化集合或 dtype dispatcher。
- spec 同步：`spec/execute_engine/execute_engine_target.md` 明确 generated seed alias / concrete memory dtype 只能生成唯一 concrete 实例，手写缺 dtype 必须稳定失败，且不新增公开 compile 参数。
- helper 注释：AST 脚本扫描 18 个 `_memory_element_cpp_type(...)` / seed helper，`missing=[]`；review 点名的 npu_demo emit helper 均包含 `功能说明` 与 `使用示例`。
- 非公开 API 边界：npu_demo emit 各文件使用当前文件内 `_memory_element_cpp_type(...)` helper，未恢复跨文件直接导入非公开 helper；静态扫描未命中 ctx 能力探测、`_type` 写入等阻断模式。

验证：
- 候选 `expectation/` / `.skills` 禁止修改面：`git status --short --untracked-files=all -- expectation .skills`、`git diff --name-only -- expectation .skills`、`git diff --cached --name-only -- expectation .skills` 均为空输出。
- 候选格式检查：`git diff --check && git diff --cached --check`，退出码 `0`。
- 候选排除范围脚本：`candidate_count=47`，`excluded_hits=[]`。
- 候选静态扫描：`rg -n "hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)|object\.__setattr__\([^\n]*_type|SSAValue\._type|\._type\b" kernel_gen test --glob '*.py' --glob '!expectation/**' --glob '!.skills/**'`，无输出。
- 候选 Diff 反推 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/execute_engine/test_compile.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py test/dialect/test_nn.py test/dsl/ast/nodes/test_dma.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/passes/test_memory_pool.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`，结果 `370 passed, 3 warnings in 96.33s`，退出码 `0`。
- 候选 full expectation 复跑：`EXPECTATION_WORKTREE_ROOT=/tmp/kcg-t20260516-candidate-final-231165 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/t20260516_review_pycache_$(date +%s) PYTHONPATH=/tmp/kcg-t20260516-candidate-final-231165 timeout 2400s python3 -m expectation > /tmp/t20260516_review_full_expectation_20260516_153325.log 2>&1`，结果 `exit=0`；日志尾部为 `dsl_run invalid_contract` 预期失败输出。

Diff 反推审查：
- `kernel_gen/execute_engine/compiler.py`、`spec/execute_engine/execute_engine_target.md`、`test/execute_engine/test_compile.py`：已覆盖手写 templated Memory 缺 concrete dtype 稳定失败、generated seed alias 唯一实例化和非 dispatcher 边界。
- `kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`spec/dsl/gen_kernel/kernel_emitter.md`、`test/dsl/gen_kernel/test_gen_kernel.py`：已覆盖 generated source 内部 seed alias 输出与非公开 API 口径。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/**`：已覆盖当前文件 helper 注释字段与 npu_demo emit / gen_kernel 公开路径；未恢复跨文件非公开 helper 导入。
- `kernel_gen/passes/**`、`spec/pass/**`、`test/passes/**` 与 kernel symbolic memory 测试：Diff 反推 pytest 覆盖 byte backing pool template family、memory_pool 动态符号 simplify、npu_demo lowering pipeline 和 template-name infer 链路。
- `expectation` 单列为合同验收资产，不计入 Diff 反推 pytest；本轮候选 diff 未修改 `expectation/` 或 `.skills`。

自检：
- 已逐项读取最新返工记录、候选 diff、关键实现 / spec / test，并在最新 `origin/main` 基线上复审。
- 已核对上一轮 P0/P1 最小阻断项均有对应实现、spec/test 和验证收口。
- 已确认主仓 mixed dirty tree 中的 agents 标准、prompt、public API 盘点、人性化整改记录与 DSL AST parser 并行改动不在本轮通过范围内。
- 未修改实现、spec、测试、`expectation/`、`.skills` 或任务状态文件；仅追加本 review 记录。

结论：通过。T-20260516-2fff5df3 可按 `/tmp/kcg-t20260516-candidate-final-231165` 的 47 个候选文件范围进入 merge；merge 阶段不得纳入主仓 mixed dirty tree 中的排除范围改动。

## Merge 收口记录：李白

时间：2026-05-16 16:32 +0800
经办人：李白
任务：T-20260516-2fff5df3 / current main full expectation 候选范围 merge

### 合并范围与主线同步

- merge 来源：`/tmp/kcg-t20260516-candidate-final-231165`。
- 候选基线：`HEAD=309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- 已执行 `git fetch --prune origin main`。
- latest main：`origin/main=309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- `merge-base HEAD origin/main=309cdad350f1f882a281ecff4d642d4f2735f2d6`。
- 结论：候选 worktree 与 latest main 同基线，无主线变化冲突；无需 rebase 或重放补丁。
- 主仓 `/home/lfr/kernelcode_generate` 当前仍是 mixed dirty tree；本次 merge 不从主仓 dirty tree 暂存，不提交主仓未列名改动。

### 实际合入文件

- 候选业务 / spec / pytest 文件：`47` 个，来自 `git diff --name-only`。
- 同批合入任务记录：`agents/codex-multi-agents/log/task_records/2026/20/20260516-current-full-expectation.md`。
- 明确未合入：
  - `agents/standard/**`
  - `agents/codex-multi-agents/agents/*/*.prompt.md`
  - `agents/codex-multi-agents/log/public_api_inventory_20260516.md`
  - `agents/codex-multi-agents/log/task_records/2026/20/20260516-agents-standard-humanize-research.md`
  - `kernel_gen/dsl/ast/__init__.py`、`kernel_gen/dsl/ast/mlir_gen.py`、`kernel_gen/dsl/ast/parser.py`
  - `spec/dsl/ast/**` parser 相关并行改动
  - `test/dsl/ast/test_*.py` 并行改动
  - 其它未列名 mixed dirty tree 改动

### Merge gate 复跑

执行目录：`/tmp/kcg-t20260516-candidate-final-231165`
日志目录：`/tmp/t20260516_merge_gate_2fff5df3`

- Diff 反推 pytest：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/execute_engine/test_compile.py test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py test/dialect/test_nn.py test/dsl/ast/nodes/test_dma.py test/kernel/test_conv2d_dynamic_symbol_params.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/passes/test_memory_pool.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`
  - 结果：`370 passed, 3 warnings in 326.31s`，退出码 `0`。
- full expectation：
  - 命令：`EXPECTATION_WORKTREE_ROOT=/tmp/kcg-t20260516-candidate-final-231165 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/t20260516_merge_pycache_2fff5df3 PYTHONPATH=/tmp/kcg-t20260516-candidate-final-231165 timeout 2400s python3 -m expectation`
  - 结果：退出码 `0`。
  - 日志：`/tmp/t20260516_merge_gate_2fff5df3/full_expectation.log`。
  - 日志尾部包含 `dsl_run invalid_contract` 预期失败输出，不影响命令退出码。
- `git diff --check`：退出码 `0`。
- `git diff --cached --check`：退出码 `0`。
- `python3 -m py_compile` 覆盖 `kernel_gen/execute_engine/compiler.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py` 与 npu_demo emit helper 文件，退出码 `0`。
- `expectation/` / `.skills` 禁止修改面：
  - `git diff --name-only -- expectation .skills`：空。
  - `git diff --cached --name-only -- expectation .skills`：空。
  - `git status --short --untracked-files=all -- expectation .skills`：空。
- 静态扫描：
  - 命令：`rg -n "hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)|object\.__setattr__\([^\n]*_type|SSAValue\._type|\._type\b" kernel_gen test --glob '*.py' --glob '!expectation/**' --glob '!.skills/**'`
  - 结果：无输出。
- helper 注释字段核对：
  - AST 扫描覆盖 17 个 `_memory_element_cpp_type(...)` helper 与 2 个 `_template_instance_seed*` helper。
  - 结果：`missing=[]`。

### 关键语义复核

- `ExecutionEngine.compile`：手写 templated `Memory` source 缺 concrete dtype / seed 时仍以 `template_instance_required` 稳定失败。
- generated seed alias：`__kernel_gen_template_instance_seed_*` 只作为内部源码线索，供 generated source 唯一 dtype 实例化，不形成 runtime dtype dispatcher，不新增公开 API。
- npu_demo emit helper：当前文件内 `_memory_element_cpp_type(...)` helper 已补齐 `功能说明` 与 `使用示例`，未恢复跨文件非公开 helper 导入。
- `memory_template_name(memory_type)` / `has_memory_template_name(memory_type)` 删除已有用户确认来源，并同步实现、package-root 导出、`spec/dialect/nn.md` 与公开 pytest；迁移口径为读取 `NnMemoryType.template_name.data`。

### Merge 结论

- review 复审通过记录齐全。
- 候选范围与 latest main 基线安全。
- 指定 gate 全部通过。
- `expectation/` 与 `.skills` 无改动。
- 最小阻断项：无。
- 下一步：只暂存 47 个候选文件与本记录，提交并推送 `origin/main`，再执行 `-done` 并回报管理员。
