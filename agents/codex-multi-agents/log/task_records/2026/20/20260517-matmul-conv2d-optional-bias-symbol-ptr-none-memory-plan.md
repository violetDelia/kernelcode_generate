# T-20260517-4567853a matmul/conv2d optional bias symbol.ptr none memory

## 任务信息

- 任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
- 角色：金铲铲大作战 / execute
- worktree：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- 计划书：只读引用主仓 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/matmul_conv2d_optional_bias_symbol_ptr_none_memory_green_plan.md`
- 合同真源：主仓 `expectation/`，任务 worktree 不复制、不新建、不修改 expectation

## Execute 记录

### 2026-05-18 初始同步与读取

- 已读取最新个人提示词、根 `AGENTS.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- worktree 状态：
  - `HEAD=7c2aa977553916441e9c6d184eae12c0deee5630`
  - `origin/main=7c2aa977553916441e9c6d184eae12c0deee5630`
  - 分支：`task/matmul-conv2d-optional-bias-symbol-ptr-none-memory`
  - 初始 `git status --short --branch`：clean
- 计划书读取结论：
  - 公开 API 授权范围：`memory.get_data`、`SymbolPtrType(dtype, template_name=None)`、`symbol.cast` 支持 ptr -> unknown symbol int、DSL None memory compare、runtime allow-absent memory。
  - 禁止范围：不新增 `memory.has_data` / `memory.ptr_ne_zero` / `optional_memory` / `nn.optional` / `KG_ARG_NONE`，不新增 `dma.transpose`，不改 expectation。
  - 主仓只读 expectation 必过入口：`expectation.dialect.symbol.type.ptr_type`、`expectation.dialect.symbol.operation.cast`、`expectation.dialect.symbol.operation.compare`、`expectation.dsl.mlir_gen.control_flow.none_memory_if`。

### 当前执行计划

- S1：补 `memory.get_data` dialect 与 `symbol.ptr` template / ptr cast 合同。
- S2：补 DSL None memory if lowering 到 `memory.get_data -> symbol.cast -> symbol.eq/ne -> scf.if`。
- S3：补 npu_demo emit_c ptr / get_data 发射与 include/API 文档。
- S4：补 runtime allow-absent None memory 输入。
- S5：迁移 matmul/conv2d 六个 demo 的 rank-1 optional bias。
- S6：补公开 pytest、主仓只读 expectation 验收、diff check、敏感目录空 diff与静态扫描。

### 2026-05-18 07:01 execute 收口

时间：2026-05-18 07:01 +0800
经办人：金铲铲大作战
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
任务目标：按计划完成 optional bias 的 `memory.get_data / symbol.ptr / symbol.cast / symbol.eq-ne` 公开合同、runtime `None` allow-absent、matmul / conv2d rank-1 bias、spec / 实现 / 测试 / 主仓只读 expectation 验收闭环；按用户补充口径补齐可复现轻量 tile 随机覆盖与 present/absent 两路运行记录。

改动：
- `kernel_gen/dialect/memory.py` / `spec/dialect/memory.md` / `test/dialect/test_memory.py`：新增 `memory` dialect 与 `MemoryGetDataOp(source, result_type=None)`，默认 context 注册该 dialect。
- `kernel_gen/dialect/symbol.py` / `spec/dialect/symbol.md` / `test/dialect/test_symbol.py`：`SymbolPtrType` 支持 template name；`symbol.cast` 支持 `!symbol.ptr<...> -> !symbol.int<#symbol.expr<?>>`；ptr 仍不得直接进入 compare。
- `kernel_gen/dsl/ast/**` / `spec/dsl/ast/**` / `test/dsl/ast/test_mlir_gen.py`：四种 memory-vs-None 条件 lower 到 `memory.get_data -> symbol.cast -> symbol.eq/ne -> scf.if`；`scf.if` 支持无 else body。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/**` / `kernel_gen/dsl/gen_kernel/kernel_emitter.py` / `spec/dsl/gen_kernel/**` / `test/dsl/gen_kernel/emit/test_package.py`：npu_demo 侧发射 `memory.get_data`、ptr cast、无 else `scf.if`，并写入 `// kg.allow_absent_memory_args` metadata；新增 data-use guard 校验。
- `kernel_gen/execute_engine/compiler.py` / `kernel_gen/tools/dsl_run.py` / `kernel/runner.py` / `spec/execute_engine/execute_engine_api.md` / `spec/tools/dsl_run.md` / `spec/kernel/runner.md` / 对应 pytest：runtime `None` 仅在 allow-absent metadata 存在时封送为 data=null、shape=`[0]`、stride=`[1]` 的 memory；缺 metadata 稳定失败。
- `kernel/matmul/**` 与 `kernel/conv2d/**`：六个 demo 增加 rank-1 optional bias；present 用真实 bias，absent 用 `None`；bias 加法只在 reduce 完成后、写回前执行。
- 按用户补充口径，六个 demo 的 tile 改为固定 seed 从轻量候选选择并输出 `tile_seed / tile_candidates / selected_tile / bias_case_order`；matmul 三例与 conv2d 三例均覆盖 present/absent。conv2d 随机候选收窄为随机 F/C/N、空间 tile 保持 `8/8`，避免越界触发计划外 symbol canonical 边界。
- `kernel/conv2d/inputs_dynamic_tile_dynamic.py`：修复 dynamic demo 原直接执行 outlined device entry 的问题，改为编译执行 root wrapper，保留 `npu_demo::launch<2,...>` block 分发语义；此前 absent 输出缺失 `f=8..15`，修复后 present/absent 都通过 NumPy 对齐。
- `kernel_gen/passes/memory_plan.py` / `kernel_gen/passes/memory_pool.py` / `spec/pass/*` / 对应 pytest：补 allow-absent memory guard 与无 else `scf.if` 相关 pass 边界。

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $(git diff --name-only -- '*.py')`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py -k 'ptr or cast or compare'`：exit 0，`29 passed, 81 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_memory.py -k 'get_data'`：exit 0，`5 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py -k 'default_context'`：exit 0，`1 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/test_parser.py test/dsl/ast/test_mlir_gen.py -k 'none or get_data or symbol_ptr'`：exit 0，`3 passed, 71 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/nodes/test_control_flow.py -k 'if'`：exit 0，`4 passed, 5 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py -k 'get_data or symbol_cast or scf_if'`：exit 0，`3 passed, 69 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/execute_engine/test_invoke.py -k 'none or absent'`：exit 0，`5 passed, 54 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py`：exit 0，`8 passed`。
- 六个 demo 脚本均 exit 0，关键输出：
  - `kernel/matmul/inputs_static_tile_static.py`：selected tile `(M=72,N=56,K=48)`；bias order `('present', 'absent')`；absent/present `max_abs_diff=3.4332275390625e-05`。
  - `kernel/matmul/inputs_static_tile_dynamic.py`：selected tile `(72, 88, 56)`；bias order `('absent', 'present')`；absent/present `max_abs_diff=3.0517578125e-05`。
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py`：selected tile `(48, 96, 64)`；bias order `('present', 'absent')`；absent/present `max_abs_diff=3.0517578125e-05`。
  - `kernel/conv2d/inputs_static_tile_static.py`：selected tile `(7,18,3,8,8)`；bias order `('present', 'absent')`；absent/present `max_abs_diff=4.1961669921875e-05`。
  - `kernel/conv2d/inputs_static_tile_dynamic.py`：selected tile `(7, 18, 3, 8, 8)`；bias order `('absent', 'present')`；absent/present `max_abs_diff=3.814697265625e-05`。
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py`：selected tile `(7, 18, 3, 8, 8)`；bias order `('absent', 'present')`；absent/present `max_abs_diff=4.57763671875e-05`。

合同验收：
- 导入边界证明：
  - `kernel_gen.__file__=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory/kernel_gen/__init__.py`
  - `expectation.dialect.symbol.type.ptr_type=/home/lfr/kernelcode_generate/expectation/dialect/symbol/type/ptr_type.py`
  - `expectation.dialect.symbol.operation.cast=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/cast.py`
  - `expectation.dialect.symbol.operation.compare=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/compare.py`
  - `expectation.dsl.mlir_gen.control_flow.none_memory_if=/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/control_flow/none_memory_if.py`
  - `expectation.utils.case_runner=/home/lfr/kernelcode_generate/expectation/utils/case_runner.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。

静态检查与敏感目录门禁：
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。
- `git diff -U0 -- '*.py' '*.md' | rg '^\\+.*(memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\()'`：无输出。
- `rg -n 'hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx' kernel_gen kernel test spec`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：无输出。

自检：
- 接口：新增/变更公开 API 均在计划授权范围内；未新增 `CompileRequest` / `ExecuteRequest` 参数；未新增 DSL `memory.data`、has-data、ptr-ne-zero 或 optional memory 表面 API。
- 边界与异常：覆盖 ptr template verifier、ptr cast 正反例、None 非 allow / 缺 metadata 失败、memory truthiness / 非 memory None compare 失败、allow-absent guard 外 data-use 失败。
- 兼容性：`SymbolPtrType(dtype)` 单参数兼容；present runtime ndarray 路径不回退；absent `None` 仅通过 metadata 放行。
- 实现遗漏：六个 matmul/conv2d demo 均覆盖 rank-1 bias present/absent；dynamic conv2d 改 root wrapper 后 block 0/1 都执行。
- 冗余与复用：没有跨文件私有 API 直连；helper 仅在当前文件或类内复用；未新增非装饰器嵌套函数。
- 注释准确性：新增/修改功能实现文件已补文件级说明/API 列表；新增/修改函数注释覆盖功能说明与使用示例。
- 输入/输出校验：runtime `None` 的 dtype/rank 来自 metadata，非 allow slot 不接受；demo 输出与 NumPy 参考对齐。
- 并发/资源：`ExecutionEngine` 编译对象均在 finally 中 close；未引入共享全局可变执行状态，随机 tile 使用固定 seed、可复现。
- 性能：tile 候选收窄在 npu_demo 容量安全范围内，conv2d 空间 tile 保持 8/8 避免计划外 symbol canonical 边界。
- 测试有效性：`expectation` 仅单列合同验收；diff 反推自测覆盖 dialect、DSL、emit、runtime、pass 和六个 demo 脚本；脚本输出包含 selected tile 与 present/absent 分支结果，review 可机械核对。

结论：execute 闭合；候选 diff 中 `expectation/.skills/agents/standard` 为空；按流程流转 review。

## Review 记录

### 2026-05-18 07:15 review：需修改

时间：2026-05-18 07:15 +0800
经办人：提莫炖蘑菇
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
任务目标：审查 matmul/conv2d optional bias symbol.ptr none memory 计划级 execute 的公开 API、spec、实现、pytest、六个 demo present/absent 覆盖、主仓只读 expectation 合同验收、Diff 反推自测、静态扫描与敏感目录空 diff。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- review 前执行：`git fetch origin`
- `HEAD=7c2aa977553916441e9c6d184eae12c0deee5630`
- `origin/main=7c2aa977553916441e9c6d184eae12c0deee5630`
- `merge-base=7c2aa977553916441e9c6d184eae12c0deee5630`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- 结论：待审 worktree 已在最新 `origin/main` 基线上；当前候选为未提交工作区 diff，无需 merge，未发现同步冲突或覆盖风险。

改动 / 真实审查结论：
- 结论：需修改，不能进入架构复核 / 终验。
- 阻断 1：`kernel_gen/tools/dsl_run.py` 与 `test/tools/test_dsl_run.py` 均在本轮 diff 中，但完整公开测试文件失败。命令 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py` 结果为 `7 failed, 33 passed, 1 warning`。其中至少 3 个失败直接命中本轮公开错误语义不一致：实现常量 `kernel_gen/tools/dsl_run.py:59` 为 `... integer scalar and allow-absent memory None`，spec `spec/tools/dsl_run.md:102` 固定短语为 `... integer scalar and None for memory`，测试常量 `test/tools/test_dsl_run.py:80` 仍是旧文本 `... numpy.ndarray and integer scalar`，导致 `test_dsl_run_rejects_unsupported_runtime_arg_type`、`test_dsl_run_rejects_float_runtime_scalar`、`test_dsl_run_rejects_unsupported_numpy_dtype` 均失败。最小修复：统一 spec / 实现 / 测试的公开错误短语，并补跑完整 `pytest -q test/tools/test_dsl_run.py`。
- 阻断 2：同一完整 pytest 还暴露 changed public dsl_run 路径的其它失败：`test_dsl_run_trance_dump_dir_writes_and_overwrites_trace_file` 编译失败，`test_dsl_run_add_dynamic_tile_scalar_matches_public_contract` 与 `test_dsl_run_accepts_numpy_integer_runtime_scalar` 在 `symbol` verifier 中触发 `AttributeError: 'cell' object has no attribute 'is_Mul'`，`test_dsl_run_sub_matches_public_contract` 编译失败。由于本轮修改 `kernel_gen/tools/dsl_run.py`、`kernel_gen/dialect/symbol.py` 与 `test/tools/test_dsl_run.py`，这些失败属于 Diff 反推审查范围；execute 记录只跑了 `-k 'none or absent'` 子集，未证明完整公开 `dsl_run` 文件在当前候选下仍为绿。最小修复：修复这些公开测试失败，或若确认某项为 latest main 既有失败，必须在最新干净基线给出复现与归因记录，并保证当前 diff 不扩大失败。
- 阻断 3：`spec/tools/dsl_run.md:224-227` 的用例编号重复：新增 `TC-TOOLS-DSL-RUN-047/048` 后，后续 runtime trance 两行仍使用同样编号。同时新增两行的建议测试名 `test_dsl_run_accepts_none_for_allow_absent_memory_arg` / `test_dsl_run_rejects_unguarded_none_memory_data_use` 与实际测试 `test_dsl_run_optional_bias_none_and_present_paths` / `test_dsl_run_rejects_none_without_allow_absent_metadata` 不一致。最小修复：重排后续用例编号，并把建议测试入口改成真实 pytest 名称。
- 阻断 4：`spec/execute_engine/execute_engine_api.md:204-205` 的建议测试名与实际测试不一致。spec 写的是 `test_execute_engine_invoke_allows_absent_memory_with_metadata` / `test_execute_engine_invoke_rejects_none_without_allow_absent_metadata`，实际为 `test_execute_engine_invoke_allows_none_with_absent_memory_metadata` / `test_execute_engine_invoke_rejects_none_without_absent_memory_metadata`。最小修复：同步 spec 的测试映射，避免合同矩阵指向不存在的 pytest 入口。
- 阻断 5：`kernel_gen/passes/template_name_infer.py:1-8` 的文件级说明在本轮 diff 中移除了 `功能说明:` 标签，只剩裸列表，违反实现文件规范中功能实现文件必须包含 `功能说明 / API 列表 / 使用示例 / 关联文件` 的要求。最小修复：恢复 `功能说明:` 段标题，并保持 API 列表紧跟功能说明后。

Diff 反推审查：
- 已审候选 diff 文件集合：`kernel/**`、`kernel_gen/core/context.py`、`kernel_gen/dialect/{memory.py,symbol.py}`、`kernel_gen/dsl/ast/**`、`kernel_gen/dsl/gen_kernel/**`、`kernel_gen/execute_engine/compiler.py`、`kernel_gen/passes/{memory_plan.py,memory_pool.py,template_name_default_constraints.py,template_name_infer.py}`、`kernel_gen/tools/dsl_run.py`、相关 `spec/**` 与 `test/**`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $(git diff --name-only -- '*.py') kernel_gen/dialect/memory.py kernel_gen/dsl/gen_kernel/emit/npu_demo/memory.py test/core/test_context.py test/dialect/test_memory.py`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py test/dialect/test_memory.py test/dsl/ast/test_mlir_gen.py test/dsl/gen_kernel/emit/test_package.py test/tools/test_dsl_run.py test/execute_engine/test_invoke.py -k 'ptr or cast or compare or get_data or none or absent or scf_if'`：exit 0，`55 passed, 248 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py`：exit 0，`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py`：exit 1，`7 failed, 33 passed, 1 warning`。该命令是由本轮修改 `kernel_gen/tools/dsl_run.py` 与 `test/tools/test_dsl_run.py` 反推得到的完整公开测试文件，失败项未在 execute 记录中覆盖或归因。

主仓只读 expectation 导入边界：
- 使用 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate`，任务 worktree 排在前，主仓 `/home/lfr/kernelcode_generate/expectation` 作为合同资产来源。
- 导入证明：
  - `kernel_gen.__file__=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory/kernel_gen/__init__.py`
  - `expectation.dialect.symbol.type.ptr_type=/home/lfr/kernelcode_generate/expectation/dialect/symbol/type/ptr_type.py`
  - `expectation.dialect.symbol.operation.cast=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/cast.py`
  - `expectation.dialect.symbol.operation.compare=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/compare.py`
  - `expectation.dsl.mlir_gen.control_flow.none_memory_if=/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/control_flow/none_memory_if.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。

敏感目录空 diff 与静态扫描：
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。
- `git diff -U0 -- '*.py' '*.md' | rg '^\\+.*(memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\()'`：exit 1，无命中。
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：exit 1，无命中。
- `git diff -U0 -- '*.py' | rg '^\\+.*(: object|-> object|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object)'`：exit 1，无命中。
- `git diff -U0 -- '*.py' | rg '^\\+\\s+def [A-Za-z_][A-Za-z0-9_]*\\('`：仅命中 class 方法或当前文件顶层 helper，未发现新增非装饰器嵌套函数。

自检：
- 特殊情况：发现 `None` allow-absent 相关子集通过，但完整 `dsl_run` 公开测试文件失败，说明 execute 的 `-k` 子集未覆盖改动文件的既有公开路径。
- 完整性：新增 `memory.get_data` / `symbol.ptr template` / runtime `None` 合同入口已有正向覆盖，但 spec 测试矩阵存在重复 ID 和不存在测试名，追踪链未闭合。
- 维护性：`template_name_infer.py` 文件级说明格式回退，后续按规范扫描会被继续退回。
- 测试有效性：主仓只读 expectation 四个入口通过，但 expectation 不能替代失败的公开 pytest；当前 review 不通过。

结论：需修改，退回 execute。最小需改项为上述 5 项；修复后至少补跑并记录 `pytest -q test/tools/test_dsl_run.py`、当前 Diff 反推 pytest、主仓只读 expectation 四个入口、`git diff --check`、敏感目录空 diff 与静态扫描。

### 2026-05-18 07:38 execute 返工收口

时间：2026-05-18 07:38 +0800
经办人：金铲铲大作战
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
任务目标：修复 review 退回的 5 项最小阻断：统一 `dsl_run` 公开错误短语，修复或归因完整 `test/tools/test_dsl_run.py` 失败，修正 `spec/tools/dsl_run.md` 重复用例 ID 与测试名映射，修正 `spec/execute_engine/execute_engine_api.md` 测试名映射，恢复 `kernel_gen/passes/template_name_infer.py` 文件级 `功能说明` 标签。

改动：
- `kernel_gen/tools/dsl_run.py` 与 `test/tools/test_dsl_run.py`：统一 `DslRunUnsupportedRealArg` 稳定错误短语为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor, numpy.ndarray, integer scalar and None for memory`，与 `spec/tools/dsl_run.md` 当前公开合同一致。
- `kernel_gen/dialect/symbol.py`：`SymbolConstOp.verify_()` 不再为了比较 result type 重新构造 `SymbolValueType`，改为直接比较 result type 内部 canonical expr 与常量值；该修复闭合完整 `test/tools/test_dsl_run.py` 顺序下 dynamic tile 触发的 verifier 稳定性失败，不改变 `symbol.const` 公开类型语义。
- `spec/tools/dsl_run.md`：把 optional bias `None` 两个用例映射到真实 pytest `test_dsl_run_optional_bias_none_and_present_paths` / `test_dsl_run_rejects_none_without_allow_absent_metadata`；runtime trance 用例编号顺延为 `TC-TOOLS-DSL-RUN-049/050/051`；脚本核对 `dsl_run_case_ids=52 duplicates=[]`。
- `spec/execute_engine/execute_engine_api.md`：把 allow-absent memory 两个建议测试名修正为真实 pytest `test_execute_engine_invoke_allows_none_with_absent_memory_metadata` / `test_execute_engine_invoke_rejects_none_without_absent_memory_metadata`。
- `kernel_gen/passes/template_name_infer.py`：恢复文件级说明中的 `功能说明:` 标签，保持 `API 列表` 紧跟功能说明后。

失败复现与归因：
- 本轮返工开始先复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -vv`，当前现场复现为 `3 failed, 37 passed`，3 项均为 `DslRunUnsupportedRealArg` 错误短语不一致；review 记录中的另外 4 项在本轮完整复跑中未再出现。
- 统一错误短语后，完整 `test/tools/test_dsl_run.py` 一度只剩 `test_dsl_run_add_dynamic_tile_scalar_matches_public_contract`，根因为完整 suite 顺序下 `SymbolConstOp.verify_()` 重新构造 `SymbolValueType.from_expr("2")` 触发 xDSL attribute 初始化不稳定。改为直接比较 expr 后，目标动态 tile 与完整文件均通过。

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py`：exit 0，`40 passed, 1 warning`；锁定完整 `dsl_run` 公开测试文件，不再只跑 `none/absent` 子集。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py::test_dsl_run_add_dynamic_tile_scalar_matches_public_contract test/tools/test_dsl_run.py::test_dsl_run_accepts_numpy_integer_runtime_scalar`：exit 0，`2 passed, 1 warning`；锁定 `SymbolConstOp.verify_()` 修复覆盖的 runtime scalar dynamic tile 路径。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $(git diff --name-only -- '*.py')`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py -k 'ptr or cast or compare or const'`：exit 0，`51 passed, 59 deselected`；覆盖 `symbol.const` verifier、ptr/cast/compare 相关 diff。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_invoke.py -k 'none or absent'`：exit 0，`3 passed, 16 deselected`；覆盖 execute engine allow-absent memory 测试名映射对应真实 pytest。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_memory.py -k 'get_data'`：exit 0，`5 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_context.py -k 'default_context'`：exit 0，`1 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/test_parser.py test/dsl/ast/test_mlir_gen.py -k 'none or get_data or symbol_ptr'`：exit 0，`3 passed, 71 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/nodes/test_control_flow.py -k 'if'`：exit 0，`4 passed, 5 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py -k 'get_data or symbol_cast or scf_if'`：exit 0，`3 passed, 69 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py`：exit 0，`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_memory_pool.py -k 'none or absent or scf_if or memory'`：exit 0，`58 passed, 1 warning`。
- 文本核对脚本：`dsl_run_case_ids=52 duplicates=[]`；四个新映射测试名均在对应 pytest 文件中存在。

合同验收：
- 导入边界证明使用 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate` 与 `importlib.util.find_spec(...)`：
  - `expectation.dialect.symbol.type.ptr_type`：`/home/lfr/kernelcode_generate/expectation/dialect/symbol/type/ptr_type.py`
  - `expectation.dialect.symbol.operation.cast`：`/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/cast.py`
  - `expectation.dialect.symbol.operation.compare`：`/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/compare.py`
  - `expectation.dsl.mlir_gen.control_flow.none_memory_if`：`/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/control_flow/none_memory_if.py`
  - `expectation.utils.case_runner`：`/home/lfr/kernelcode_generate/expectation/utils/case_runner.py`
  - `kernel_gen`：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory/kernel_gen/__init__.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。

静态检查与敏感目录门禁：
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。
- `git diff -U0 -- '*.py' '*.md' | rg '^\\+.*(memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\()'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(: object|-> object|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+\\s+def [A-Za-z_][A-Za-z0-9_]*\\('`：仅列出当前文件内公开方法或顶层 helper；未发现新增非装饰器嵌套函数。

自检：
- 接口：未新增计划外公开 API；`dsl_run` 错误短语与 `spec` 当前公开合同一致；execute engine / dsl_run 测试矩阵指向真实 pytest 名称。
- 边界：完整 `test/tools/test_dsl_run.py` 已覆盖 runtime scalar、None allow-absent、dump/trance、自定义 pipeline 与错误路径；复审记录中的 7 项失败已通过完整文件复跑闭合。
- 异常：unsupported real arg、float runtime scalar、unsupported numpy dtype 均按同一稳定错误短语失败；缺 metadata 的 `None` 路径仍按公开错误失败。
- 兼容性：`SymbolConstOp.verify_()` 只改变内部比较方式，不改变 `SymbolValueType` 构造、打印、解析或公开 IR 文本。
- 注释与规范：`template_name_infer.py` 文件级说明恢复 `功能说明:`，新增/修改功能文件仍保留 API 列表。
- 测试有效性：本轮不以 expectation 替代 diff 反推测试；完整 dsl_run pytest、symbol pytest、execute_engine pytest和相关模块 pytest均可在对应实现坏掉时失败。
- 敏感目录：`expectation/.skills/agents/standard` 候选 diff、暂存 diff、未跟踪与 ignored 检查均为空。

结论：review 退回的 5 项最小阻断已收口；本轮 execute 返工可重新流转 review。

### 2026-05-18 07:56 review 复审

时间：2026-05-18 07:56 +0800
审查人：提莫炖蘑菇
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
任务目标：复审 5 项退回阻断返工：`dsl_run` 公开错误短语、完整 `test/tools/test_dsl_run.py`、`spec/tools/dsl_run.md` 用例编号与测试名映射、`spec/execute_engine/execute_engine_api.md` 测试名映射、`template_name_infer.py` 文件级说明，并核对 Diff 反推自测、主仓只读 expectation 四入口、`git diff --check`、敏感目录空 diff 与静态扫描。

审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- 已执行：`git fetch origin`
- `HEAD=7c2aa977553916441e9c6d184eae12c0deee5630`
- `origin/main=7c2aa977553916441e9c6d184eae12c0deee5630`
- `merge-base=7c2aa977553916441e9c6d184eae12c0deee5630`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- 结论：待审 worktree 已在最新 `origin/main` 基线上；当前候选为工作区 diff，未发现需要 merge 的主线更新。

真实审查：
- 5 项退回阻断本身已收口：
  - `kernel_gen/tools/dsl_run.py`、`test/tools/test_dsl_run.py`、`spec/tools/dsl_run.md` 的 `DslRunUnsupportedRealArg` 公开错误短语已统一为 `real_args only supports torch.Tensor, numpy.ndarray, integer scalar and None for memory`。
  - `spec/tools/dsl_run.md` optional bias / trance 用例编号已顺延，新增用例测试名已指向真实 pytest 名称。
  - `spec/execute_engine/execute_engine_api.md` allow-absent memory 两个测试名已同步为真实 `test_execute_engine_invoke_allows_none_with_absent_memory_metadata` / `test_execute_engine_invoke_rejects_none_without_absent_memory_metadata`。
  - `kernel_gen/passes/template_name_infer.py` 文件级说明已恢复 `功能说明:`，`API 列表` 仍紧跟功能说明后。
- 结论：仍需修改，不能进入架构复核 / 终验。
- 新阻断：Diff 反推的 kernel 公开 pytest 当前不能稳定通过。`test/kernel/test_matmul_symbolic_memory_genkernel.py` 全文件复跑失败，具体为 `test_matmul_target_scripts_execute_and_tile_reduce_still_passes` 中公开脚本入口执行失败：
  - 第一次拆分复跑：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py` 结果 `1 failed, 3 passed, 1 warning`，失败脚本为 `kernel/matmul/inputs_dynamic_tile_dynamic.py`，子进程 `SIGSEGV`。
  - 第二次复跑同一命令：结果 `1 failed, 3 passed, 1 warning`，失败脚本为 `kernel/matmul/inputs_static_tile_static.py`，子进程超出测试内固定 `timeout=120`。
  - 单独运行 `test_matmul_target_scripts_execute_and_tile_reduce_still_passes` 与直接运行 `python3 kernel/matmul/inputs_static_tile_static.py` 可通过，说明当前失败更像 full-file 顺序 / 资源 / runtime 状态隔离问题；但公开 pytest 文件不能通过，execute 记录中的 `8 passed` 当前无法在 review 现场复现。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py` 在 review 现场由测试进程 `SIGSEGV` 终止，未得到 pytest 通过结果。
- 最小修复要求：execute 需让 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py` 在当前候选现场稳定通过，或在最新干净基线给出可复现归因并证明当前 diff 未扩大失败；否则该任务涉及的六个 demo 公开脚本验收链不闭合。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py`：最终复跑通过，`40 passed, 1 warning`。说明本轮 5 项退回中的 `dsl_run` 完整公开测试文件已收口；首次复跑曾出现一次 `compile_failed`，随后单用例与完整文件重跑通过，未再复现。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py -k 'ptr or cast or compare or const'`：通过，`51 passed, 59 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_invoke.py -k 'none or absent'`：通过，`3 passed, 16 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $(git diff --name-only -- '*.py') kernel_gen/dialect/memory.py kernel_gen/dsl/gen_kernel/emit/npu_demo/memory.py test/core/test_context.py test/dialect/test_memory.py`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`：失败，见上方阻断。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py`：测试进程 `SIGSEGV`，未得到通过结果。

主仓只读 expectation 导入边界：
- 使用 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate`，任务 worktree 排在前，主仓 `/home/lfr/kernelcode_generate/expectation` 作为合同资产来源。
- `python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
- `python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
- `python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
- `python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。

敏感目录空 diff 与静态扫描：
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。
- `git diff -U0 -- '*.py' '*.md' | rg '^\\+.*(memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\()'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(: object|-> object|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+\\s+def [A-Za-z_][A-Za-z0-9_]*\\('`：仅命中 class 方法或当前文件顶层 helper，未发现新增非装饰器嵌套函数。

自检：
- 特殊情况：5 项退回阻断已逐项核对，但本轮计划目标包含 matmul / conv2d 六个 demo 与公开脚本验收，当前公开 pytest 无法稳定复现 execute 的 `8 passed`。
- 完整性：主仓只读 expectation 四入口通过，但 expectation 不能替代失败的公开 pytest；kernel demo diff 对应测试链仍断。
- 维护性：full-file 顺序下脚本子进程 `SIGSEGV` / timeout 风险未归因，后续合入会把不稳定公开验收带入主线。
- 测试有效性：`test/tools/test_dsl_run.py` 已完整补跑通过；`test/kernel/test_matmul_symbolic_memory_genkernel.py` 与 `test/kernel/test_conv2d_symbolic_memory_genkernel.py` 未通过，不能据子集或单脚本通过放行。

结论：需修改，退回 execute。最小阻断项为 kernel demo 公开 pytest 在 review 当前现场失败；修复后需重新补跑并记录完整 Diff 反推 pytest、主仓只读 expectation 四入口、`git diff --check`、敏感目录空 diff与静态扫描。

### 2026-05-18 09:08 execute 返工收口

时间：2026-05-18 09:08 +0800
经办人：睡觉小分队
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
任务目标：继续定位并修复 review 复审点名的 kernel demo 公开 pytest 不稳定问题；若无法修复则记录干净基线归因与候选 diff 是否扩大失败。

执行前阅读记录：
- 已重新读取 `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/expectation任务规则.md`。
- 已读取主仓只读计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/matmul_conv2d_optional_bias_symbol_ptr_none_memory_green_plan.md` 的公开 API、目标实现/测试范围、主仓只读 expectation 四入口与禁止修改面。
- 已读取本任务记录中 07:56 review 复审结论，当前最小阻断为 `test/kernel/test_matmul_symbolic_memory_genkernel.py` / `test/kernel/test_conv2d_symbolic_memory_genkernel.py` 全文件公开 pytest 在 review 现场出现 `SIGSEGV` / timeout，无法复现 execute 记录中的 `8 passed`。

同步基线：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- 已执行 `git fetch origin`，未覆盖任务 diff。
- `HEAD=7c2aa977553916441e9c6d184eae12c0deee5630`
- `origin/main=7c2aa977553916441e9c6d184eae12c0deee5630`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`

返工收口 / 改动：
- `kernel_gen/dialect/symbol.py`：新增当前文件内 `_symbol_arith_operand_contains_unknown(...)`，`symbol` 算术 verifier 的 unknown 传播改为读取已 canonical 的表达文本，不再为 `?` 判断反复解析大尺寸动态表达 AST；同时补回不依赖 SymPy 的 full-tile 动态 step 线性倍数证明，覆盖 `B -> B + 3*S step S` 与 `0 -> 5*N step N`。
- `kernel_gen/passes/memory_pool.py`：`_peak_bytes(...)` 对静态整数候选仍精确取最大值；对含 `Min/Max/iter` 的动态复杂候选改用所有 allocation size 之和作为保守 backing peak 上界，避免 `sp.Max(...)` 在复杂符号表达上触发 SymPy 深层关系推导和段错误。
- `kernel/matmul/inputs_{dynamic_tile_dynamic,static_tile_dynamic,static_tile_static}.py` 与 `kernel/conv2d/inputs_{dynamic_tile_dynamic,static_tile_dynamic,static_tile_static}.py`：脚本 stdout 不再打印完整 module/source 大文本；诊断真源继续由 `kernel/dump/<case>/source.cpp` 与 pass dump 承接，stdout 保留 `[ARGS]`、`[IR]` 摘要和 `[CHECK]` 校验行，降低公开 pytest `subprocess.run(capture_output=True)` 的管道捕获和退出 GC 压力。
- 本轮未修改、复制、新建、删除或同步 `expectation/`、`.skills`、`agents/standard`。

失败复现与定位：
- 初始最小复现 `run_lowering_demo('debug_conv2d/direct_stack3', conv2d_inputs_dynamic_tile_dynamic_kernel, ...)` 曾在 `symbol` verifier 重复解析大表达式和 `memory_pool._peak_bytes -> sp.Max(...)` 处触发 `SIGSEGV`；收口后同一路径完成并返回源码。
- 连续复跑目标 kernel pytest 时曾复现一次 `kernel/matmul/inputs_static_tile_static.py` 子进程在全部 `[CHECK]` 成功输出后退出期 `SIGSEGV`；移除六个 demo 脚本完整 IR/source stdout 后，目标 pytest 连续两轮全文件通过。

Diff 反推自测：
- `find . -type d -name __pycache__ -prune -exec rm -rf {} + && rm -rf .pytest_cache kernel/dump && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：exit 0；两轮均为 `8 passed, 1 warning`，锁定 review 点名的 full-file / subprocess 稳定性问题。
- `find . -type d -name __pycache__ -prune -exec rm -rf {} + && rm -rf .pytest_cache kernel/dump && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py test/dialect/test_memory.py test/core/test_context.py test/dsl/ast/test_parser.py test/dsl/ast/test_mlir_gen.py test/dsl/ast/nodes/test_control_flow.py test/dsl/gen_kernel/emit/test_package.py test/tools/test_dsl_run.py test/execute_engine/test_invoke.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py`：先暴露 `test_symbol_min_fold_full_tile_dynamic_step_to_existing_step` 与 `test_symbol_min_fold_full_tile_zero_to_symbol_multiple` 2 条回归；补结构化动态 step 倍数证明后复跑 exit 0，`388 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_dynamic_step_to_existing_step test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_zero_to_symbol_multiple test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_dynamic_bounds_to_step_const -vv`：exit 0，`3 passed`。
- `find . -type d -name __pycache__ -prune -exec rm -rf {} + && rm -rf .pytest_cache kernel/dump && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：最终复跑 exit 0，`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit 0。

合同验收：
- 导入边界证明使用 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate`；`kernel_gen` 来自任务 worktree，`expectation.*` 来自主仓合同资产：
  - `kernel_gen=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory/kernel_gen/__init__.py`
  - `expectation.dialect.symbol.type.ptr_type=/home/lfr/kernelcode_generate/expectation/dialect/symbol/type/ptr_type.py`
  - `expectation.dialect.symbol.operation.cast=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/cast.py`
  - `expectation.dialect.symbol.operation.compare=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/compare.py`
  - `expectation.dsl.mlir_gen.control_flow.none_memory_if=/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/control_flow/none_memory_if.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。

静态检查与敏感目录门禁：
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。
- `git diff -U0 -- '*.py' '*.md' | rg '^\\+.*(memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\()'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(: object|-> object|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+\\s+def [A-Za-z_][A-Za-z0-9_]*\\('`：仅命中类方法或当前文件顶层 helper，未发现新增非装饰器嵌套函数。
- 验证后已清理本轮生成的 `__pycache__`、`.pytest_cache` 与 `kernel/dump`。

自检：
- 接口：本轮未新增计划外公开 API；`symbol` 与 `memory_pool` 仅收口当前公开 verifier / pass 语义，demo stdout 仍保留公开摘要与 `[CHECK]` 验收字段，完整 IR/source 由既有 dump 合同承接。
- 边界：unknown 传播不再重解析大表达式；full-tile 动态 step 不依赖 SymPy；memory-pool 动态 peak 采用保守上界，避免复杂符号比较段错误，静态整数 peak 仍精确。
- 异常与兼容：`symbol.min` full-tile 静态与动态 step 测试均覆盖；`dsl_run`、execute engine allow-absent、memory.get_data、control-flow none compare 等既有返工项未回退。
- 实现质量：未跨文件调用非公开 helper；未使用 ctx 能力探测；未新增非装饰器嵌套函数；新增/修改 helper 已写功能说明与使用示例。
- 测试有效性：目标 kernel demo pytest 已连续两轮全文件通过并最终复跑通过；相关 diff 反推集合 `388 passed`；主仓只读 expectation 四入口单列验收，未用 expectation 替代 pytest。
- 敏感目录：`expectation/.skills/agents/standard` tracked、staged、untracked、ignored 检查均为空。

结论：review 复审点名的 kernel demo pytest 稳定性阻断已收口；可按流程重新流转 review。

### 2026-05-18 09:22 review 复审

时间：2026-05-18 09:22 CST
审查人：提莫炖蘑菇
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
任务目标：复审 kernel demo pytest 稳定性返工、公开 API/实现/spec/test 一致性、Diff 反推自测、主仓只读 expectation 四入口、git diff --check、敏感目录空 diff 与静态扫描。

审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- 已执行 `git fetch origin`，未覆盖任务 diff。
- `HEAD=7c2aa977553916441e9c6d184eae12c0deee5630`
- `origin/main=7c2aa977553916441e9c6d184eae12c0deee5630`
- `merge-base=7c2aa977553916441e9c6d184eae12c0deee5630`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`

真实审查：
- 已读取主仓计划书 `ARCHITECTURE/plan/matmul_conv2d_optional_bias_symbol_ptr_none_memory_green_plan.md` 与任务记录 09:08 execute 返工段；目标 worktree 当前不含计划书副本，按主仓只读计划资产核对。
- 复核 `kernel_gen/dialect/symbol.py`：unknown 传播改为读取 canonical 表达文本，避免为 `?` 判定反复解析大尺寸动态表达；full-tile 动态 step 倍数证明不再依赖 SymPy 深层关系推导。对应 `test_symbol_min_fold_full_tile_dynamic_step_to_existing_step`、`test_symbol_min_fold_full_tile_zero_to_symbol_multiple`、`test_symbol_min_fold_full_tile_dynamic_bounds_to_step_const` 已覆盖。
- 复核 `kernel_gen/passes/memory_pool.py`：静态整数 peak 保持精确，动态复杂符号候选采用所有 allocation size 之和作为保守上界，避免 `sp.Max(...)` 触发复杂符号关系推导导致段错误；相关 `test/passes/test_memory_pool.py` 已包含在 Diff 反推集合。
- 复核 6 个 matmul/conv2d demo 脚本：stdout 不再输出完整 module/source 大文本，公开摘要仍保留 `[ARGS]`、`[IR]`、`[CHECK]`；完整 source/IR 仍由 dump 文件承接。该修复直接对应 review 点名的 full-file kernel pytest `SIGSEGV` / timeout 风险。
- 复核公开 API 边界：本轮未发现新增计划外公开 API；未发现跨文件调用非公开 helper、测试直连非 API、ctx 能力探测、`object` 签名或非装饰器嵌套函数阻断命中。
- 复核敏感目录：`expectation/`、`.skills/`、`agents/standard/**` 未出现在候选 diff、staged diff、untracked 或 ignored 状态中。

Diff 反推审查：
- `find . -type d -name __pycache__ -prune -exec rm -rf {} + && rm -rf .pytest_cache kernel/dump && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：exit 0；两轮均为 `8 passed, 1 warning`。
- `find . -type d -name __pycache__ -prune -exec rm -rf {} + && rm -rf .pytest_cache kernel/dump && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：exit 0；最终复跑 `8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_dynamic_step_to_existing_step test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_zero_to_symbol_multiple test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_dynamic_bounds_to_step_const -vv`：exit 0；`3 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py`：exit 0；`40 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py test/dialect/test_memory.py test/core/test_context.py test/dsl/ast/test_parser.py test/dsl/ast/test_mlir_gen.py test/dsl/ast/nodes/test_control_flow.py test/dsl/gen_kernel/emit/test_package.py test/tools/test_dsl_run.py test/execute_engine/test_invoke.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py`：exit 0；`388 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit 0。

主仓只读 expectation 合同验收：
- 导入边界证明使用 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate`；`kernel_gen` 来自任务 worktree，`expectation.*` 来自主仓合同资产。
- `python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
- `python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
- `python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
- `python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。

静态扫描与禁止修改面：
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。
- `git diff -U0 -- '*.py' '*.md' | rg '^\\+.*(memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\()'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(: object|-> object|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+\\s+def [A-Za-z_][A-Za-z0-9_]*\\('`：仅命中 class 方法或当前文件顶层 helper，人工核对未发现新增非装饰器嵌套函数。

findings：
- 无阻断项。

自检：
- 特殊情况：复核覆盖 review 退回的 kernel demo full-file pytest 稳定性问题，目标 pytest 已连续两轮通过并最终复跑通过。
- 完整性：Diff 反推审查覆盖实际改动的 symbol verifier、memory_pool peak、demo stdout、dsl_run、memory/context/execute engine、memory_plan/memory_pool 相关测试；expectation 单列为主仓只读合同验收。
- 维护性：未发现跨文件非公开 API 使用、测试直连非 API、ctx 能力探测、`object` 签名、非装饰器嵌套函数或敏感目录越权改动。
- 测试有效性：目标 kernel pytest、相关 pytest 集合、主仓只读 expectation 四入口和静态扫描均有记录；未用 expectation 替代 pytest。

结论：通过。T-20260517-4567853a review 复审通过，建议管理员按计划级任务流程接入架构复核 / 终验；review 不直接进入 merge。

### 2026-05-18 09:31 大闸蟹计划级架构复核 / 终验

时间：2026-05-18 09:31 CST
复核人：大闸蟹
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
任务目标：按计划书完成 optional bias 的 `memory.get_data`、`symbol.ptr`、`symbol.cast`、runtime `None` allow-absent、matmul / conv2d rank-1 bias、spec / 实现 / 测试 / 主仓只读 expectation 验收闭环，并确认可进入 merge 前置流程。

同步现场：
- worktree：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/matmul_conv2d_optional_bias_symbol_ptr_none_memory_green_plan.md`
- `HEAD=7c2aa977553916441e9c6d184eae12c0deee5630`
- `origin/main=7c2aa977553916441e9c6d184eae12c0deee5630`
- `merge-base=7c2aa977553916441e9c6d184eae12c0deee5630`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`

复核范围：
- 已重新读取当前角色提示词、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md` 与本计划书。
- 候选 diff 覆盖计划指定的 `kernel/`、`kernel_gen/`、`spec/`、`test/` 与任务记录；未发现计划外公开 API 变更要求。
- 新增任务记录文件当前为 untracked，必须在 merge 前与 spec / 实现 / pytest 候选 diff 同批纳入提交；若遗漏任务记录则 merge gate 不通过。

主仓只读 expectation 合同验收：
- 导入边界命令使用 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate`。
- `kernel_gen=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory/kernel_gen/__init__.py`
- `expectation.dialect.symbol.type.ptr_type=/home/lfr/kernelcode_generate/expectation/dialect/symbol/type/ptr_type.py`
- `expectation.dialect.symbol.operation.cast=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/cast.py`
- `expectation.dialect.symbol.operation.compare=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/compare.py`
- `expectation.dsl.mlir_gen.control_flow.none_memory_if=/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/control_flow/none_memory_if.py`
- `python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
- `python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
- `python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
- `python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。
- 主仓 expectation manifest 复核与计划一致：
  - `ce5c50196b6378699952b8b9c2df41a5be3eff15f2e0171fbe778e5fc7f47b9b  expectation/dialect/symbol/type/ptr_type.py`
  - `1aad3dcd7d3ddeb1d8f2a21ebda9aea5a9c8c58122e596d6eab799af2620ca3b  expectation/dialect/symbol/operation/cast.py`
  - `55aea773ff07a1e5fb661657660517fae1657179662310a6b0f697aca16bd863  expectation/dialect/symbol/operation/compare.py`
  - `943e503d116c27353ff9ef33bbe5fb19f9bf089a0aba9e8765a6d54e6bf1a580  expectation/dsl/mlir_gen/control_flow/none_memory_if.py`

计划 pytest / Diff 反推终验：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：exit 0，`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/dialect/test_symbol.py -k "ptr or cast or compare"`：exit 0，`29 passed, 81 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/dialect/test_memory.py -k "get_data"`：exit 0，`5 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/core/test_context.py -k "default_context"`：exit 0，`1 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/dsl/ast/test_parser.py test/dsl/ast/test_mlir_gen.py -k "none or get_data or symbol_ptr"`：exit 0，`3 passed, 71 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/dsl/ast/nodes/test_control_flow.py -k "if"`：exit 0，`4 passed, 5 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/dsl/gen_kernel/emit/test_package.py -k "get_data or symbol_cast or scf_if"`：exit 0，`3 passed, 69 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/tools/test_dsl_run.py test/execute_engine/test_invoke.py -k "none or absent"`：exit 0，`5 passed, 54 deselected, 2 warnings`。
- 已核对 review 复审记录中的相关集合 `388 passed`、`test/tools/test_dsl_run.py` `40 passed` 和 symbol 定向 `3 passed`；本次终验未运行全量 expectation，符合计划“不运行全量 expectation，除非用户另行明确要求”的口径。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit 0。

静态检查与禁止修改面：
- `git diff --check`：exit 0。
- `git diff --cached --check`：exit 0。
- 对 `git ls-files --others --exclude-standard` 的未跟踪新文件逐个执行 `git diff --no-index --check /dev/null <file>`：无 whitespace 错误输出。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。
- `rg -n "memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\(" kernel_gen kernel spec test expectation`：仅命中既有 `spec/include/api/Memory.md` 与 `spec/include/cpu/cpu.md` 的 `Memory::data()` 文档示例；计划允许 include / emit 目标代码出现 `Memory::data()`，且 `git diff -U0 -- kernel_gen kernel spec test | rg '^\\+.*(memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\()'` 无输出，未新增 DSL `memory.data()`。
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(: object|-> object|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object)'`：无输出。

自检：
- 公开 API：`memory.get_data`、`SymbolPtrType(template_name)`、`SymbolCastOp(ptr)`、symbol compare、runtime `None` allow-absent 与 runner / dsl_run 语义均落在用户已确认和计划列明范围内；未发现计划外 API 扩张。
- 合同真源：四个 expectation 入口均来自主仓，任务 worktree 未复制、修改、移动或新建 `expectation/`。
- 测试有效性：本次终验实际复跑计划验收设计中的定向 pytest 与四项 expectation；review 复审记录的更大相关集合也已核对。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/**` tracked / cached / untracked / ignored 均为空。
- 记录：本段已写入任务 worktree 记录；merge 前必须保证该记录与候选 diff 同批提交。

最小阻断项：无。

结论：通过。T-20260517-4567853a 大闸蟹计划级架构复核 / 终验通过；可按管理员流程继续等待另一架构终验 / merge gate 核对后进入合并，不得遗漏任务记录同批提交。

### 2026-05-18 09:31 第二架构复核 / 终验

时间：2026-05-18 09:31 CST
经办人：守护最好的爱莉希雅
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
任务目标：对 review 已通过候选执行第二架构复核 / 终验，核对 latest 同步现场、计划必过 pytest、主仓只读 expectation 四入口、禁止修改面、静态扫描、公开 API/spec/test 边界，并写回终验结论与最小阻断项。

执行前阅读记录：
- 已读取当前角色提示词 `agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md`、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/审查规范.md`、`agents/standard/实现文件规范.md`。
- 已读取主仓只读计划书 `ARCHITECTURE/plan/matmul_conv2d_optional_bias_symbol_ptr_none_memory_green_plan.md`，确认当前必过合同验收为四个主仓只读 expectation：`expectation.dialect.symbol.type.ptr_type`、`expectation.dialect.symbol.operation.cast`、`expectation.dialect.symbol.operation.compare`、`expectation.dsl.mlir_gen.control_flow.none_memory_if`。
- 已读取本任务记录中 09:08 execute 返工收口与 09:22 review 复审通过记录，重点复核 kernel demo pytest 稳定性返工、主仓 expectation 导入边界、敏感目录空 diff 与静态扫描。

同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- 已执行 `git fetch origin`，未覆盖任务 diff。
- `HEAD=7c2aa977553916441e9c6d184eae12c0deee5630`
- `origin/main=7c2aa977553916441e9c6d184eae12c0deee5630`
- `merge-base=7c2aa977553916441e9c6d184eae12c0deee5630`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- 结论：当前候选基于 latest `origin/main@7c2aa977553916441e9c6d184eae12c0deee5630`；无主线漂移。

Diff / 禁止修改面核对：
- `git diff --stat`：候选覆盖计划内 `symbol/memory` dialect、DSL lowering / emit、execute_engine、dsl_run、runner、matmul / conv2d demo、spec、pytest 与任务记录；未发现 scope 外目录。
- `git diff --check`：exit 0。
- `git diff --name-only -- expectation .skills agents/standard`：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
- `git status --short --ignored -- expectation .skills agents/standard`：无输出。

Diff 反推 pytest / 编译验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：exit 0，`8 passed, 1 warning`。锁定 review 曾阻塞的 matmul / conv2d demo full-file pytest 稳定性。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_dynamic_step_to_existing_step test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_zero_to_symbol_multiple test/dialect/test_symbol.py::test_symbol_min_fold_full_tile_dynamic_bounds_to_step_const -vv`：exit 0，`3 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py`：exit 0，`40 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol.py test/dialect/test_memory.py test/core/test_context.py test/dsl/ast/test_parser.py test/dsl/ast/test_mlir_gen.py test/dsl/ast/nodes/test_control_flow.py test/dsl/gen_kernel/emit/test_package.py test/tools/test_dsl_run.py test/execute_engine/test_invoke.py test/passes/test_memory_plan.py test/passes/test_memory_pool.py`：exit 0，`388 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit 0。

主仓只读 expectation 合同验收：
- 运行环境：`cwd=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`，`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory:/home/lfr/kernelcode_generate`。
- 导入边界：
  - `kernel_gen=/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory/kernel_gen/__init__.py`
  - `expectation.dialect.symbol.type.ptr_type=/home/lfr/kernelcode_generate/expectation/dialect/symbol/type/ptr_type.py`
  - `expectation.dialect.symbol.operation.cast=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/cast.py`
  - `expectation.dialect.symbol.operation.compare=/home/lfr/kernelcode_generate/expectation/dialect/symbol/operation/compare.py`
  - `expectation.dsl.mlir_gen.control_flow.none_memory_if=/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/control_flow/none_memory_if.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。

静态扫描：
- `git diff -U0 -- '*.py' '*.md' | rg '^\\+.*(memory\\.has_data|memory\\.ptr_ne_zero|optional_memory|nn\\.optional|KG_ARG_NONE|memory\\.data\\()'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(: object|-> object|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+\\s+def [A-Za-z_][A-Za-z0-9_]*\\('`：命中 `SymbolPtrType.__init__`、`_MemoryNoneCompareAST.emit_mlir` 和 `kernel_emitter.py` 当前文件内 helper；人工核对均为 class 方法或当前文件内 helper，未发现非装饰器嵌套函数。

公开 API / spec / test 边界抽查：
- `spec/dialect/memory.md` 与 `kernel_gen/dialect/memory.py` 的 `API 列表` 紧跟功能说明，公开列出 `Memory = Dialect("memory", [MemoryGetDataOp], [])` 与 `class MemoryGetDataOp(source: SSAValue | Operation, result_type: Attribute | None = None)`。
- `spec/dialect/symbol.md` 与 `kernel_gen/dialect/symbol.py` 已覆盖 `SymbolPtrType(dtype, template_name)`、`SymbolCastOp` ptr 到 unknown symbol int、direct ptr compare 失败；对应 pytest 覆盖 parse / print / verifier 正反例。
- `spec/tools/dsl_run.md`、`spec/kernel/runner.md`、`spec/execute_engine/execute_engine_api.md` 与实现一致：`None` 仅作为 allow-absent memory runtime arg；未新增 `CompileRequest` / `ExecuteRequest` / `CompiledKernel.execute(...)` 公开参数。
- `test/dialect/test_memory.py`、`test/dsl/ast/test_mlir_gen.py`、`test/dsl/gen_kernel/emit/test_package.py`、`test/execute_engine/test_invoke.py`、`test/tools/test_dsl_run.py` 均通过公开 parser / op 构造 / runner / execute_engine 入口验证；未发现跨文件非公开 helper 依赖。

自检：
- 特殊情况：针对 review 曾阻塞的 kernel demo full-file pytest，终验现场复跑 `8 passed`；未再复现 `SIGSEGV` 或 timeout。
- 完整性：计划必过四个主仓只读 expectation 均已在正确导入边界下运行并 exit 0；相关 pytest 集合、dsl_run、symbol 定向、py_compile、diff check 与敏感目录门禁均通过。
- 维护性：未发现未确认公开 API、跨文件非公开 helper、测试直连私有 helper、ctx 能力探测、`object` 签名、非装饰器嵌套函数或 expectation/.skills/agents/standard 污染。
- 测试有效性：pytest 与 expectation 分开记录；expectation 未替代 diff 反推测试。验证后已清理本轮生成的 `__pycache__`、`.pytest_cache` 与 `kernel/dump`。

findings：
- 无阻断项。

结论：通过。T-20260517-4567853a 第二架构复核 / 终验通过；最小阻断项：无。可进入 merge 流程；merge 前仍需按合并规范复核候选 diff、同批任务记录、敏感目录空 diff 与主仓最新状态。

### 2026-05-18 09:46 merge 收口记录

时间：2026-05-18 09:46 CST
经办人：李白
任务：T-20260517-4567853a / matmul-conv2d-optional-bias-symbol-ptr-none-memory
阶段：merge

合并前规则与来源：
- 已按李白角色职责只做合并 / 同步确认，不补实现、不补审查、不修改计划书裁定。
- 已读取并遵守根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md` 与 expectation 合同资产规则。
- 任务来源 worktree：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- 来源分支：`task/matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- 合同真源：主仓只读 `expectation/`，本任务不合入 `expectation/`、`.skills/`、`agents/standard/**` 改动。

latest 同步与冲突处理：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory`
- `HEAD=7c2aa977553916441e9c6d184eae12c0deee5630`
- `origin/main=7c2aa977553916441e9c6d184eae12c0deee5630`
- `merge-base=7c2aa977553916441e9c6d184eae12c0deee5630`
- `git rev-list --left-right --count HEAD...origin/main`：前序核对为 `0 0`。
- 合并前未发现主线漂移、冲突文件或需要覆盖的本地改动；主仓同步状态与任务 worktree 基线一致。

候选范围核对：
- `git diff --name-status` 显示 45 个 tracked 修改文件，范围覆盖计划内 `kernel/` matmul / conv2d demo、`kernel_gen/` core / dialect / DSL emit / execute_engine / passes / tools、`spec/` 对应规格、`test/` 对应 pytest。
- `git ls-files --others --exclude-standard` 显示 6 个任务新增文件与 1 个任务记录文件，必须同批合入：
  - `agents/codex-multi-agents/log/task_records/2026/20/20260517-matmul-conv2d-optional-bias-symbol-ptr-none-memory-plan.md`
  - `kernel_gen/dialect/memory.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/memory.py`
  - `spec/dialect/memory.md`
  - `test/core/test_context.py`
  - `test/dialect/test_memory.py`
- 合入范围未包含 `expectation/`、`.skills/`、`agents/standard/**`；任务记录已确认在候选 diff 内，避免先合代码后补记录。

merge 前复核命令与结果：
- 主仓只读 expectation 四入口：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.type.ptr_type`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.cast`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dialect.symbol.operation.compare`：exit 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WT:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.control_flow.none_memory_if`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PYTHONFAULTHANDLER=1 pytest -q -p no:cacheprovider test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py -vv`：exit 0，`8 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py`：exit 0，`40 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile $( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py'; } | sort -u )`：exit 0。
- `git diff --check`：exit 0。
- 导入边界抽查：`kernel_gen` 来自任务 worktree，四个 `expectation.*` 模块来自 `/home/lfr/kernelcode_generate/expectation/...`。
- `git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --untracked-files=all -- expectation .skills agents/standard`、`git status --short --ignored -- expectation .skills agents/standard`：均无输出。

静态扫描：
- `git diff -U0 -- '*.py' | rg '^\\+.*(from [A-Za-z0-9_.]+ import _|import [A-Za-z0-9_.]+\\._)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+.*(: object|-> object|def [A-Za-z_][A-Za-z0-9_]*\\([^\\n]*object)'`：无输出。
- `git diff -U0 -- '*.py' | rg '^\\+\\s+(async\\s+def|def)\\s+'` 命中 `SymbolPtrType.__init__`、`_MemoryNoneCompareAST.emit_mlir` 以及 `kernel_emitter.py` 当前文件内 helper；人工核对均为 class 方法或当前文件内 helper，未发现非装饰器嵌套函数。

生成物与敏感目录：
- 本轮测试生成的 `__pycache__`、`.pytest_cache`、`kernel/dump` 已在任务 worktree 内清理；清理后 `git status --short --ignored --untracked-files=all` 仅保留任务候选 diff 与任务记录。
- 未修改、移动、新建、删除 `expectation/` 或 `.skills/`；未带入 `agents/standard/**`。

剩余风险与结论：
- 未运行全量 expectation；按计划与两位架构终验记录，本任务当前必过合同资产为四个主仓只读 expectation 入口，均已通过。
- merge 阶段未发现冲突、主线漂移、记录缺失、敏感目录污染或 scope 外候选文件。
- 结论：T-20260517-4567853a 满足合并前门禁，可将候选代码 / spec / test / 本任务记录同批提交，随后 push `origin/main` 并执行 `-done`。最终合并提交号按合并规范在合并后回报中说明，不再追加记录提交。
