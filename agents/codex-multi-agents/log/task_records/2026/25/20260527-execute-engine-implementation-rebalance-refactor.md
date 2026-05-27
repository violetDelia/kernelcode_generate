# 20260527-execute-engine-implementation-rebalance-refactor

## 管理员创建记录 - 2026-05-27 - 神秘人

- 任务类型：计划级 `execute`
- 计划书：`ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md`
- worktree：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`
- 分支：`task/execute-engine-implementation-rebalance-refactor`
- 创建基线：`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`
- 任务目标：按计划书完成 `kernel_gen/execute_engine` 实现均衡重构，在不改变 `execute_engine` 包根公开 API、`compiler` / `strategy` 公开导入路径、failure phrase、compile/execute 行为和 strategy registry 语义的前提下，将 `compiler.py` 收成公开 facade，将 strategy registry 保持在 `strategy.py`，将 `cpu` / `npu_demo` 内置后端实现和启动代码迁入 `builtin_strategy.py`，新增 `runtime_args.py` 承接运行时参数封装和 entry 调用；同步 spec、实现文件 API 列表、pytest、AST/token 静态扫描和任务记录。
- 禁止修改面：候选 diff 中 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 必须为空。
- 合同口径：本计划无必过 `expectation`；不得把 expectation 作为通过依据。
- 流程要求：完成 execute 后进入 review；计划级 review 通过后进入 archive_acceptance，不得直接 merge；任务记录必须与代码/spec/test 同批合入。

## execute 记录 - 2026-05-27 13:04 +0800 - 小李飞刀

- 任务：`T-20260527-fd30965d` / `execute-engine-implementation-rebalance-refactor`
- 任务目标：按计划把 `kernel_gen/execute_engine` 拆为 `compiler.py` facade、`strategy.py` registry、`builtin_strategy.py` 内置后端实现、`runtime_args.py` 运行期 ABI，并保持包根公开 API、旧公开导入路径、failure phrase、compile/execute 行为和 strategy registry 语义不变。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`
- 同步现场：`HEAD=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，无合并冲突。
- 执行前阅读记录：已读取根 `AGENTS.md`、`agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、计划书 `ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md`、本任务记录、`TODO.md` 当前任务行，以及 `test/execute_engine/**` / `test/repo_conformance/test_private_api_boundaries.py` 的边界规则。
- 计划内小任务卡核对：本轮一次完成 `compiler.py` facade 收口、`strategy.py` registry 真源保留、`builtin_strategy.py` 内置后端实现承接、`runtime_args.py` 运行时参数/ABI 承接、`target_support.py` 不恢复、spec/test/static gate 同步。

### 改动

- `kernel_gen/execute_engine/compiler.py`
  - 保留 `CompileRequest`、`ExecuteRequest`、`ExecuteResult`、`CompiledKernel`、`ExecutionEngine` 与 `CompileStrategy/register/get` 旧公开导入路径。
  - `CompiledKernel.execute(...)` 改为调用 `runtime_args.invoke_compiled_kernel(...)`，只负责公开 execute request 校验、entry point 校验和 `ExecuteResult` / failure phrase 映射。
  - `_BuiltinCompileStrategy.compile(...)` 仅把 `builtin_strategy.build_builtin_compile_artifacts(...)` 的编译产物装配为 `CompiledKernel`。
  - 删除 target include、entry shim、compile unit、真实编译命令、runtime arg slot / ctypes loader 细节。
- `kernel_gen/execute_engine/builtin_strategy.py`
  - 承接内置 `cpu` / `npu_demo` 编译实现：target include、entry shim、template dispatch、allow-absent metadata、compile unit、g++ 命令、trance 宏、临时产物 cleanup。
  - 保留文件级 API：`BuiltinCompileArtifacts`、`build_builtin_compile_artifacts(...)`、`install_builtin_compile_strategies(...)`。
  - 内部实现 helper 收敛到当前文件内部 `_BuiltinStrategySupport`，不进入 `__all__`，不运行期导入 `compiler.py`，不构造 `CompiledKernel`。
- `kernel_gen/execute_engine/runtime_args.py`
  - 新增文件，承接 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel(...)`。
  - 内部 `_RuntimeArgSupport` 处理 dtype/shape/stride 规范化、torch/numpy 轻量识别、allow-absent `None`、C ABI slot、`ctypes.CDLL` 与 entry symbol 调用。
- `kernel_gen/execute_engine/strategy.py`
  - 保持 `CompileStrategy`、`register_compile_strategy(...)`、`get_compile_strategy(...)` 公开 API 不变。
  - registry 错误构造和 target 校验收敛到当前文件内部 `_StrategyRegistrySupport`，不承接内置后端实现。
- `spec/execute_engine/*.md`
  - 同步四文件职责：`compiler.py` 只做 facade，`builtin_strategy.py` 承接内置编译后端，`runtime_args.py` 承接运行期 ABI，`target_support.py` 不恢复。
- `test/execute_engine/test_contract.py`
  - 补 runtime_args 文件存在、内部文件级 API exact set、旧公开路径导入、包根 `__all__` 不扩大、`target_support.py` 退场、builtin/runtime/compiler/static boundary、fresh subprocess import permutation 和 private callable gate。

### 最小功能闭环

- 编译路径闭环：`ExecutionEngine.compile(...)` -> `strategy.get_compile_strategy(...)` -> `_BuiltinCompileStrategy.compile(...)` -> `build_builtin_compile_artifacts(...)` -> `CompiledKernel(...)`。
- 执行路径闭环：`CompiledKernel.execute(...)` -> `invoke_compiled_kernel(...)` -> runtime arg slot -> `.so` / placeholder entry -> `ExecuteResult`。
- registry 闭环：`register_compile_strategy(...)` / `get_compile_strategy(...)` 仍由 `strategy.py` 真源承接，包根与 `compiler.py` 旧公开导入路径保持。
- target support 退场闭环：`kernel_gen/execute_engine/target_support.py` 不存在；`BuiltinTargetSupportArtifacts` / `build_builtin_target_support_artifacts` 不恢复。

### Diff 反推自测

- 改动文件：`kernel_gen/execute_engine/compiler.py`、`builtin_strategy.py`、`strategy.py`、新增 `runtime_args.py`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/execute_engine/strategy.py kernel_gen/execute_engine/builtin_strategy.py kernel_gen/execute_engine/runtime_args.py`，退出码 0。锁定四个实现文件语法与导入级类型注解可解析。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen/execute_engine`，退出码 0。锁定 execute_engine package 编译通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine`，退出码 0，`67 passed, 1 warning`。锁定公开 compile/execute 行为、failure phrase、registry 语义、target include/entry shim/template/allow-absent/runtime ABI 以及 contract gate。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile_strategy.py test/execute_engine/test_invoke.py`，退出码 0，`24 passed, 1 warning`。锁定 registry 与 runtime invoke diff 重点路径。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/repo_conformance/test_private_api_boundaries.py`，退出码 0，`18 passed`。锁定公开 API exact set、旧路径/新内部路径、private callable 和跨文件私有 API 边界。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine test/repo_conformance/test_private_api_boundaries.py`，退出码 0，`70 passed, 1 warning`。作为最终 diff 反推组合自测。
- 改动文件：`test/execute_engine/test_contract.py`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine`，退出码 0，收集 `67` 个测试。锁定测试目录可收集且未引入 skip/collect 结构问题。
  - fresh subprocess import permutation 脚本，退出码 0，`fresh subprocess import permutations ok: 120`。锁定 `kernel_gen.execute_engine`、`compiler`、`strategy`、`builtin_strategy`、`runtime_args` 任意导入顺序无循环。
- 改动文件：`spec/execute_engine/*.md`。
  - 由 `test/execute_engine/test_contract.py` 的文件存在、API exact set、旧路径导入和职责边界断言覆盖；spec 文案与实现分层一致。
- 静态边界：
  - `target_support absent` 脚本，退出码 0。锁定旧文件未恢复。
  - `diff scoped ctx/nested scan ok: 4 execute_engine files`，退出码 0。锁定本轮实现文件无 `ctx/context` 能力探测、无嵌套函数。
  - `execute_engine responsibility AST/token gate ok`，退出码 0。锁定 `builtin_strategy.py` 不运行期导入 `compiler.py`、不构造 `CompiledKernel`，`strategy.py` 不运行期依赖 `compiler.py`，`target_support.py` 不存在。
  - `git diff --check`，退出码 0。锁定 diff 无空白错误。

### 合同验收

- 本计划明确无必过 `expectation`，本轮不以 `expectation` 作为通过依据，未运行 expectation。

### 敏感目录与禁止修改面

- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。
- 候选 diff 未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

### 减法检查

- 新增 / 改动 `private callable` 清单：AST 扫描结果为 `compiler.py=[]`、`strategy.py=[]`、`builtin_strategy.py=[]`、`runtime_args.py=[]`；本轮没有新增或改动 module-level `_helper` / class `_method`。
- 当前文件内部实现容器：
  - `_BuiltinStrategySupport`、`_RuntimeArgSupport`、`_StrategyRegistrySupport`、`_ExecutionEngineSupport` 只在当前文件内部承载复杂实现逻辑；方法名非下划线，不进入 `__all__`，不作为跨文件 API。
  - 使用该结构是为了同时满足“不得新增公开 API”和“当前 diff 模块级 helper 不得伪公开”的边界，避免把大量实现 helper 写入文件级 API 列表。
- 被替代旧逻辑：
  - `compiler.py` 中 target include、entry shim、compile unit、真实编译、template dispatch 和 allow-absent metadata 逻辑已迁入 `builtin_strategy.py`。
  - `compiler.py` 中 runtime 参数封送、slot 构造、ctypes loader 和 entry 调用逻辑已迁入 `runtime_args.py`。
  - `target_support.py` 未恢复，`BuiltinTargetSupportArtifacts` / `build_builtin_target_support_artifacts` 未新增。
- 删除 / 未删除验证：
  - `target_support absent` 脚本通过。
  - `test/repo_conformance/test_private_api_boundaries.py` 通过，确认本轮没有跨文件私有 API、浅 private callable 或模块级伪公开 helper。
- 保留旧逻辑依据：
  - `compiler.py` 保留 `_BuiltinCompileStrategy` 装配 `CompiledKernel`，符合计划要求：`builtin_strategy.py` 不构造 `CompiledKernel`，facade 负责公开对象装配。
  - `strategy.py` 保留 registry 真源和 target registry 校验，符合公开 registry 语义不变要求。

### 自检

- 接口：包根 `kernel_gen.execute_engine.__all__`、`compiler.py.__all__`、`strategy.py.__all__` 未扩大；`builtin_strategy.py` / `runtime_args.py` 不进入包根公开 API。
- 边界：当前文件之外只使用公开 API；`builtin_strategy.py` 不运行期导入 `compiler.py`；测试不直连跨文件非公开 helper。
- 异常：failure phrase 由现有 `target_header_mismatch`、`source_empty_or_invalid`、`compile_failed`、`template_instance_required`、`symbol_resolve_failed`、`runtime_throw_or_abort` 等公开短语承接；未新增错误短语。
- 兼容性：`ExecutionEngine.compile(...)`、`CompiledKernel.execute(...)`、`CompileStrategy/register/get` 的签名和行为由 `test/execute_engine` 覆盖。
- 实现遗漏：target include/entry shim/template/runtime ABI/allow-absent/cleanup/import order 均有 pytest 或静态 gate 覆盖。
- 冗余与复用：未保留 `target_support.py`；没有为拆文件新增额外 wrapper 层；复杂内部逻辑按当前文件内部支持类收敛。
- 注释准确性：新增/修改实现文件均保留文件级说明、API 列表、使用示例和关联文件；新增/修改函数/方法包含功能说明和示例。
- 函数粒度：公开文件级 API 保持小集合；内部支持类方法承载非平凡逻辑，避免浅 private callable。
- 输入/输出校验：runtime args、compile request、target/header、entry point、stream/capture 禁用、allow-absent `None` 等路径均由 pytest 覆盖。
- 资源：`CompiledKernel.close()` 仍负责 cleanup；`builtin_strategy` 仅返回 cleanup callback，失败时释放临时目录。
- 并发/导入：120 种 fresh subprocess import permutation 通过，未发现导入循环。
- 性能：重构不改变编译/执行算法复杂度；仅移动职责。
- 测试有效性：Diff 反推测试覆盖公开行为、导入矩阵、静态边界、敏感目录和 conformance；若 facade、registry 或 runtime ABI 破坏，对应 pytest 会失败。

### 结论

- `execute` 已完成，当前候选 diff 可进入 `review`。

## review 记录 - 2026-05-27 13:14 +0800 - 提莫炖蘑菇

- 任务：`T-20260527-fd30965d` / `execute-engine-implementation-rebalance-refactor`
- 任务目标：审查 `execute_engine` implementation rebalance refactor 的公开 API 保持、`compiler/strategy/builtin_strategy/runtime_args` 分层、`spec/test` 同步、Diff 反推自测、静态边界扫描、敏感目录空 diff 与任务记录完整性。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`
- 最新同步现场：已执行 `git fetch origin`；`HEAD=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`merge-base=1778f4f717b84dc46a6a889059fc8d6fdcef895b`；未发现需要合并的新主线提交或覆盖风险。
- 计划书核对：目标 worktree 内 `ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md` 因 `ARCHITECTURE/plan/` ignore 不存在；本轮按主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md` 只读核对。
- 被审 diff：`kernel_gen/execute_engine/{compiler.py,strategy.py,builtin_strategy.py,runtime_args.py}`、`spec/execute_engine/{execute_engine.md,execute_engine_api.md,execute_engine_target.md,strategy.md}`、`test/execute_engine/test_contract.py`、本任务记录。

### Findings

1. `kernel_gen/execute_engine/runtime_args.py:40` / `kernel_gen/execute_engine/runtime_args.py:50` / `kernel_gen/execute_engine/runtime_args.py:68` / `kernel_gen/execute_engine/runtime_args.py:95` / `kernel_gen/execute_engine/runtime_args.py:116` / `kernel_gen/execute_engine/builtin_strategy.py:45` / `kernel_gen/execute_engine/builtin_strategy.py:120`
   - 问题：新增内部模块把多组内部类型、常量和 helper 结构以非下划线名称暴露在模块顶层，例如 `StringValue`、`MemoryRuntimeInput`、`LoadedEntrySymbol`、`ArgSlot`、`CArgSlot`、`ParamSpec`、`TARGET_HEADER_MISMATCH`、`COMPILE_FAILED` 等；这些名称既不在对应文件级 `API 列表` / `__all__` exact set 中，也没有用户确认作为新增公开 API。
   - 影响：本计划明确不新增公开 API，且 `builtin_strategy.py` / `runtime_args.py` 只允许极窄文件级 API；当前写法会让外部调用方通过 `from kernel_gen.execute_engine.runtime_args import ArgSlot` 或 `from kernel_gen.execute_engine.builtin_strategy import ParamSpec` 直接依赖未定义接口，测试又只检查 `__all__`，无法阻止事实公开面扩大。
   - 最小返工动作：将非 API 的内部类型、Protocol、常量、pattern 和中间结构改成单下划线内部名，或取得用户确认后补入 `spec` 与文件级 API 列表；同时补 `test/execute_engine/test_contract.py` 的 AST / import gate，机械断言 `builtin_strategy.py`、`runtime_args.py` 中本模块定义的非下划线导出只允许出现在 exact `__all__` / 文件级 API 列表内。
   - 验收方式：复跑 `pytest -q test/execute_engine/test_contract.py test/repo_conformance/test_private_api_boundaries.py`，并用脚本验证两个模块除标准导入名外没有未授权非下划线本模块定义对象。

2. `kernel_gen/execute_engine/compiler.py:51` / `kernel_gen/execute_engine/compiler.py:347` / `kernel_gen/execute_engine/compiler.py:434`
   - 问题：`compiler.py` 作为旧公开导入路径，顶层以非下划线名称导入并暴露 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies`；其中多项不属于 `compiler.py` 文件级 API 列表，也不属于 `compiler.__all__`。
   - 影响：调用方可以从旧公开路径 `kernel_gen.execute_engine.compiler` 直接导入 runtime / builtin 内部文件级 API，等价于新增未确认的兼容入口；这绕过了计划中“`compiler.py` 收成 facade，内置后端和 runtime 细节不进入旧公开路径”的边界。
   - 最小返工动作：对 `compiler.py` 中仅供内部调用的跨文件 API 使用下划线别名导入，例如 `_invoke_compiled_kernel`、`_build_builtin_compile_artifacts`、`_install_builtin_compile_strategies`，并同步调用点；若确需保留非下划线导入，则必须补用户确认、`spec/API 列表` 和公开测试。
   - 验收方式：补 `test_execute_engine_compiler_facade_static_boundary` 或新增合同测试，断言 `kernel_gen.execute_engine.compiler` 的非下划线公开面只包含 `compiler.__all__` 允许的对象；复跑 `pytest -q test/execute_engine/test_contract.py`。

### 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/execute_engine/strategy.py kernel_gen/execute_engine/builtin_strategy.py kernel_gen/execute_engine/runtime_args.py` -> 退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen/execute_engine` -> 退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine` -> 退出码 0，`67 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile_strategy.py test/execute_engine/test_invoke.py` -> 退出码 0，`24 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/repo_conformance/test_private_api_boundaries.py` -> 退出码 0，`18 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine` -> 退出码 0，收集 `67` 个测试。
- `git diff --check` -> 退出码 0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` -> 均为空输出。
- 额外静态核对：`test ! -e kernel_gen/execute_engine/target_support.py` -> 通过；`importlib.util.find_spec("kernel_gen.execute_engine.target_support") is None` -> 通过；本轮 execute_engine 文件无非装饰器嵌套 `def`，无 `hasattr(ctx` / `getattr(ctx` / `callable(getattr(ctx` 命中。

### Diff 反推审查

- 已按实际 diff 反推复跑 `test/execute_engine`、`test_compile_strategy.py`、`test_invoke.py`、`test_contract.py`、`test_private_api_boundaries.py`、`py_compile`、`compileall`、`git diff --check` 和敏感目录门禁。
- `expectation`：本计划无必过 `expectation`；本轮未把 `expectation` 作为通过依据。

### 减法审查

- 执行记录已写清旧逻辑迁移：`compiler.py` 中 target include / entry shim / compile unit / runtime ABI 分别迁入 `builtin_strategy.py` 与 `runtime_args.py`，`target_support.py` 不恢复。
- 审查确认旧 `target_support.py` 文件不存在，旧模块 `find_spec` 为 `None`。
- 阻断项：减法后的内部结构仍以非下划线顶层名暴露在 `runtime_args.py`、`builtin_strategy.py` 和 `compiler.py` 旧公开路径，公开边界未完全收口。

### 自检

- 已读取角色提示词、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、计划书、任务记录和实际 diff。
- 已核对公开 API 用户确认、跨文件公开 API 边界、测试是否只走公开入口、执行人自检 / Diff 反推自测、敏感目录禁止面和任务记录完整性。
- 已发现两个可执行公开边界返工项；按审查规范，只要仍有可执行返工项，结论不得为通过。

### 结论

- 结论：`最小需改项`。
- 下一步：回 `execute` 收口上述公开边界与测试 gate 后再进入 review；当前不得进入 `archive_acceptance` 或 `merge`。

## execute 返工记录 - 2026-05-27 13:29 +0800 - 小李飞刀

- 任务：`T-20260527-fd30965d` / `execute-engine-implementation-rebalance-refactor`
- 任务目标：修复 review 指出的公开边界最小需改项，收口 `runtime_args.py` / `builtin_strategy.py` 的未授权非下划线内部对象暴露，以及 `compiler.py` 旧公开路径泄漏 runtime/builtin 文件级 API。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`
- 同步现场：`HEAD=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`merge-base=1778f4f717b84dc46a6a889059fc8d6fdcef895b`；本次返工未发现需要合并的新主线提交。
- 执行前阅读记录：已读取本轮 review 记录、主仓只读计划 `ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md`、根 `AGENTS.md`、个人提示词、`agents/standard/任务记录约定.md`、相关 `spec/execute_engine/*.md`、`test/execute_engine/test_contract.py` 与当前 diff。

### 返工收口

- 针对 Finding 1：
  - `kernel_gen/execute_engine/runtime_args.py`：将非文件级 API 的内部协议、类型别名、slot 结构和 failure phrase 常量收为下划线内部名：`_StringValue`、`_MemoryRuntimeInput`、`_RuntimeInputValue`、`_LoadedEntrySymbol`、`_ArgSlot`、`_CArgSlot`、`_RUNTIME_THROW_OR_ABORT`、`_SYMBOL_RESOLVE_FAILED`、`_RUNTIME_KNOWN_ERROR_PHRASES`。
  - `kernel_gen/execute_engine/builtin_strategy.py`：将非文件级 API 的内部常量、pattern 和形参结构收为下划线内部名：`_TARGET_HEADER_MISMATCH`、`_SOURCE_EMPTY_OR_INVALID`、`_COMPILE_FAILED`、`_TEMPLATE_INSTANCE_REQUIRED`、`_SYMBOL_RESOLVE_FAILED`、`_RUNTIME_THROW_OR_ABORT`、`_BUILTIN_KNOWN_ERROR_PHRASES`、`_COMPILER_ICE_MARKERS`、`_INT_TYPE_PATTERN`、`_FLOAT_TYPE_PATTERN`、`_KERNEL_CONTEXT_TYPE_PATTERN`、`_MEMORY_TYPE_PATTERN`、`_TEMPLATE_PARAM_PATTERN`、`_TEMPLATE_DTYPE_OPTIONS`、`_CONCRETE_MEMORY_DTYPE_PATTERN`、`_TEMPLATE_INSTANCE_SEED_PATTERN`、`_ALLOW_ABSENT_MEMORY_ARGS_PATTERN`、`_REPO_ROOT`、`_ParamSpec`。
  - `test/execute_engine/test_contract.py`：新增 AST gate，机械断言 `builtin_strategy.py` 本模块定义的非下划线对象只允许 `BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies`；`runtime_args.py` 本模块定义的非下划线对象只允许 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`。
- 针对 Finding 2：
  - `kernel_gen/execute_engine/compiler.py`：跨文件调用改为下划线别名导入 `_AllowAbsentMemoryArg`、`_invoke_compiled_kernel`、`_build_builtin_compile_artifacts`、`_install_builtin_compile_strategies`，旧公开路径不再暴露 runtime/builtin 文件级 API。
  - `test/execute_engine/test_contract.py`：补 `compiler.py` facade 静态 gate，断言 `compiler` 模块上不存在 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`、`BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies`。
- 新增 / 重复 / 范围扩大判断：
  - 本轮仅处理 review 两个公开边界 finding，无新增范围。
  - 未新增公开 API，未修改 `expectation/.skills/agents/standard/AGENTS/TODO/DONE`。
  - 未修改计划书要求以外的模块。

### 最小功能闭环

- `compiler.py` 继续作为公开 facade，保留 `CompileRequest`、`ExecuteRequest`、`ExecuteResult`、`CompiledKernel`、`ExecutionEngine` 与 strategy registry 旧公开导入路径。
- `builtin_strategy.py` 继续提供极窄文件级 API：`BuiltinCompileArtifacts`、`build_builtin_compile_artifacts(...)`、`install_builtin_compile_strategies(...)`。
- `runtime_args.py` 继续提供极窄文件级 API：`AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel(...)`。
- 公开失败短语、compile / execute 行为、strategy registry 语义不变。

### Diff 反推自测

- 改动文件：`kernel_gen/execute_engine/compiler.py`、`kernel_gen/execute_engine/builtin_strategy.py`、`kernel_gen/execute_engine/runtime_args.py`、`test/execute_engine/test_contract.py`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/execute_engine/strategy.py kernel_gen/execute_engine/builtin_strategy.py kernel_gen/execute_engine/runtime_args.py test/execute_engine/test_contract.py`，退出码 0。锁定返工后语法与 import 注解可编译。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py`，退出码 0，`15 passed`。锁定 compiler facade 不泄漏 runtime/builtin 文件级 API、builtin/runtime 本模块定义公开面 exact set、安装边界、导入顺序、旧 target_support 退场和 private callable gate。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine test/repo_conformance/test_private_api_boundaries.py`，退出码 0，`70 passed, 1 warning`。锁定 execute_engine 公开行为、runtime ABI、compile strategy、私有 API 边界与 conformance。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen/execute_engine`，退出码 0。锁定 execute_engine 包可整体编译。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine`，退出码 0，收集 `67` 个测试。锁定测试目录可收集，未引入 collect 结构异常。
- 静态核验：
  - `grep -R "from kernel_gen.execute_engine.compiler import .*AllowAbsentMemoryArg\|from kernel_gen.execute_engine.compiler import .*RuntimeInput\|from kernel_gen.execute_engine.compiler import .*invoke_compiled_kernel\|from kernel_gen.execute_engine.compiler import .*BuiltinCompileArtifacts\|from kernel_gen.execute_engine.compiler import .*build_builtin_compile_artifacts\|from kernel_gen.execute_engine.compiler import .*install_builtin_compile_strategies" -n test kernel_gen spec | grep -v __pycache__ || true`，退出码 0，输出为空。锁定旧公开路径未被测试、实现或 spec 继续作为内部文件 API 入口使用。
  - AST 脚本核验 `builtin_strategy.py` 与 `runtime_args.py` 本模块定义的非下划线对象集合，退出码 0，输出分别为 `['BuiltinCompileArtifacts', 'build_builtin_compile_artifacts', 'install_builtin_compile_strategies']` 与 `['AllowAbsentMemoryArg', 'RuntimeInput', 'invoke_compiled_kernel']`。
  - Python import proof：`kernel_gen.execute_engine.compiler` 上 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`、`BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies` 均为 `False`。
- 空白与敏感目录：
  - `git diff --check`，退出码 0。
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。
  - `git status --short -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。

### 合同验收

- 本计划无必过 `expectation`，本轮未运行 expectation，也未把 expectation 作为通过依据。

### 减法检查

- 本轮返工没有新增公开 API。
- 内部对象减法：
  - `runtime_args.py` 仅保留 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel` 三个文件级 API；其余本模块定义对象统一下划线化。
  - `builtin_strategy.py` 仅保留 `BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies` 三个文件级 API；其余本模块定义对象统一下划线化。
  - `compiler.py` 旧公开路径不再非下划线暴露 runtime/builtin 文件级 API。
- `private callable`：本轮没有新增 module-level `_helper`；`test_execute_engine_private_callable_gate` 仍覆盖 execute_engine 四个文件的小 private callable 与 private-to-private 调用链。
- 保留旧逻辑依据：`compiler.py` 仍通过下划线别名调用 runtime/builtin 文件级 API，是当前 facade 装配 `CompiledKernel` 和 strategy 安装的必要内部调用，不作为公开入口。

### 自检

- 接口：包根 `kernel_gen.execute_engine.__all__` 未扩大；`compiler.py` 旧公开路径仅保留既有公开 facade 与 strategy registry API；runtime/builtin 文件级 API 不进入包根。
- 边界：未新增跨文件非公开 API；跨文件调用均指向文件级 API 并在 `compiler.py` 内以下划线别名隐藏。
- 异常：failure phrase 未新增、未改名；现有 compile/execute 错误语义由测试覆盖。
- 兼容性：公开 `ExecutionEngine.compile(...)`、`CompiledKernel.execute(...)`、`CompileStrategy/register/get` 行为由 `test/execute_engine` 覆盖。
- 实现遗漏：review 两个 finding 均有代码修复与静态测试；未发现剩余未授权非下划线本模块定义对象。
- 冗余：没有为返工新增 wrapper/转发层；仅改名和测试 gate 加固。
- 注释准确性：返工未新增新公开 API；现有文件级 API 列表仍与 `__all__` exact set 一致。
- 复用与函数粒度：保持当前文件内部支持类结构，不新增浅 private callable。
- 输入/输出校验：runtime args、allow-absent、compile request、target/header、entry point 相关路径继续由 `test/execute_engine` 覆盖。
- 资源：cleanup 与 runtime loader 路径未改语义。
- 并发/导入：`test_execute_engine_strategy_import_order_matrix` 通过，锁定 fresh subprocess import order 无循环。
- 性能：返工只调整名称和公开面，不改变编译/执行算法。
- 测试有效性：新增 AST gate 会在 runtime/builtin 新增未授权非下划线本模块定义对象或 compiler 旧路径泄漏时失败。

### 结论

- `execute` 返工已完成。
- 当前候选 diff 可回流 `review`。

## review 复审记录 - 2026-05-27 13:38 +0800 - 提莫炖蘑菇

- 任务：`T-20260527-fd30965d` / `execute-engine-implementation-rebalance-refactor`
- 任务目标：复审公开边界返工，重点核对 `runtime_args.py` / `builtin_strategy.py` 内部对象下划线收口、`compiler.py` 旧公开路径不泄漏 runtime / builtin internal API、`test_contract` 静态 gate、Diff 反推自测与敏感目录门禁。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`
- 最新同步现场：已执行 `git fetch origin`；`HEAD=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`merge-base=1778f4f717b84dc46a6a889059fc8d6fdcef895b`；未发现需要合并的新主线提交或覆盖风险。
- 计划书核对：目标 worktree 内 `ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md` 因 `ARCHITECTURE/plan/` ignore 不存在；本轮继续按主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md` 只读核对。
- 被审 diff：`kernel_gen/execute_engine/{compiler.py,strategy.py,builtin_strategy.py,runtime_args.py}`、`spec/execute_engine/{execute_engine.md,execute_engine_api.md,execute_engine_target.md,strategy.md}`、`test/execute_engine/test_contract.py`、本任务记录。

### Findings

1. `kernel_gen/execute_engine/compiler.py:148` / `kernel_gen/execute_engine/compiler.py:197` / `kernel_gen/execute_engine/compiler.py:259`
   - 问题：返工后 `compiler.py` 为避免旧公开路径泄漏，移除了 `RuntimeInput` / `AllowAbsentMemoryArg` 的非下划线运行期绑定，但公开 dataclass / method 注解仍直接使用 `RuntimeInput` 和 `AllowAbsentMemoryArg`。由于 `from __future__ import annotations`，普通 import 与现有 pytest 不失败；但公开反射入口 `typing.get_type_hints(...)` 无法解析这些注解。
   - 复现：
     - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... get_type_hints(ExecuteRequest / CompiledKernel / CompiledKernel.execute) ... PY`
     - 结果：
       - `ExecuteRequest: ERROR NameError: name 'RuntimeInput' is not defined`
       - `CompiledKernel: ERROR NameError: name 'AllowAbsentMemoryArg' is not defined`
       - `CompiledKernel.execute: ERROR NameError: name 'RuntimeInput' is not defined`
   - 影响：计划和 `spec/execute_engine/execute_engine_api.md` 明确这些签名是公开合同；当前实现虽然不再泄漏 runtime internal API，但同时破坏了公开注解的运行时可解析性，依赖 `typing.get_type_hints`、dataclass schema、文档生成或运行期校验的公开调用方会失败。现有 `test_contract` 只断言“不泄漏名称”，没有覆盖“不泄漏但公开注解仍可解析”的边界。
   - 最小返工动作：在不把 `RuntimeInput` / `AllowAbsentMemoryArg` 重新暴露为 `compiler.py` 旧公开路径非下划线 API 的前提下，修复 `ExecuteRequest.args`、`CompiledKernel.allow_absent_memory_args`、`CompiledKernel.execute(args=...)` 的公开注解解析；同时补 `test/execute_engine/test_contract.py` 静态 / 运行时 gate，断言 `typing.get_type_hints(ExecuteRequest)`、`typing.get_type_hints(CompiledKernel)`、`typing.get_type_hints(CompiledKernel.execute)` 可成功解析，并继续断言 `compiler.py` 不泄漏未确认 runtime / builtin 文件级 API。
   - 验收方式：复跑 `pytest -q test/execute_engine/test_contract.py`、`pytest -q test/execute_engine`，并保留上述 `get_type_hints` 反证脚本或等价 pytest。

### 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/execute_engine/runtime_args.py kernel_gen/execute_engine/builtin_strategy.py kernel_gen/execute_engine/strategy.py test/execute_engine/test_contract.py` -> 退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py` -> 退出码 0，`15 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py::test_execute_engine_strategy_import_order_matrix -vv` -> 退出码 0，`1 passed`。
- fresh subprocess import-order 手工脚本覆盖 `kernel_gen.execute_engine.strategy`、`builtin_strategy`、`runtime_args`、`compiler`、包根全部排列 -> 退出码 0，`all permutations ok`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine` -> 退出码 0，`67 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/repo_conformance/test_private_api_boundaries.py` -> 退出码 0，`18 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine` -> 退出码 0，收集 `67` 个测试。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen/execute_engine test/execute_engine` -> 退出码 0。
- `git diff --check` -> 退出码 0。
- `git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` -> 均为空输出。

### Diff 反推审查

- 已按实际 diff 反推复跑 `test/execute_engine/test_contract.py`、全量 `test/execute_engine`、`test/repo_conformance/test_private_api_boundaries.py`、`py_compile`、`compileall`、`collect-only`、`git diff --check` 和敏感目录门禁。
- 额外反推了公开注解反射边界：`typing.get_type_hints(...)` 对 `compiler.py` 公开 dataclass / method 失败，现有 pytest 未覆盖该边界。
- `expectation`：本计划无必过 `expectation`；本轮未把 `expectation` 作为通过依据。

### 减法审查

- 已核对返工减法：
  - `runtime_args.py` 本模块定义的非下划线对象已收口到 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`。
  - `builtin_strategy.py` 本模块定义的非下划线对象已收口到 `BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies`。
  - `compiler.py` 旧公开路径不再直接暴露 runtime / builtin 文件级 API。
- 阻断项：减法过度后未给公开注解提供可解析绑定，导致公开签名反射失败；需要在“不泄漏旧公开路径内部 API”和“公开注解可解析”之间补机械 gate。
- 本轮未发现敏感目录 diff；未发现 `expectation/.skills/agents/standard` 改动。

### 自检

- 已读取角色提示词、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、计划书、任务记录和实际 diff。
- 已核对执行人返工记录、最小功能闭环、自检、Diff 反推自测、敏感目录门禁和公开 API 边界。
- 已发现一个可执行公开边界返工项；按审查规范，只要仍有可执行返工项，结论不得为通过。

### 结论

- 结论：`最小需改项`。
- 下一步：回 `execute` 修复公开注解运行时可解析性，并补 `test_contract` gate 后再进入 review；当前不得进入 `archive_acceptance` 或 `merge`。

## execute 第三轮返工记录 - 2026-05-27 13:50 +0800 - 金铲铲大作战

- 任务：`T-20260527-fd30965d` / `execute-engine-implementation-rebalance-refactor`
- 任务目标：按守护最好的爱莉希雅与大闸蟹第三轮裁定，用最小项修复 `compiler.py` 公开注解 `typing.get_type_hints(...)` 可解析性，同时不恢复旧公开路径的 runtime / builtin internal API 绑定。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`
- 执行前阅读记录：已重新读取根 `AGENTS.md`、个人提示词、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/审查规范.md`、本任务记录末尾 review finding 与第三轮裁定消息。
- 禁止修改面：本轮未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`；未扩大包根 `__all__`；未恢复 `compiler.py` 非下划线 `RuntimeInput`、`AllowAbsentMemoryArg`、`invoke_compiled_kernel`、`BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies` 绑定。

### 返工收口

- `kernel_gen/execute_engine/compiler.py`
  - 新增 `import kernel_gen.execute_engine.runtime_args as _runtime_args` 私有模块别名。
  - 将 `ExecuteRequest.args`、`CompiledKernel.allow_absent_memory_args`、`CompiledKernel.execute(args=...)` 的公开注解改为 `_runtime_args.RuntimeInput` / `_runtime_args.AllowAbsentMemoryArg` 路径，使默认 `typing.get_type_hints(...)` 可在 `compiler.py` 模块全局中解析。
  - `CompiledKernel` 装配 allow-absent metadata 时改用 `_runtime_args.AllowAbsentMemoryArg(...)`；仍通过 `_invoke_compiled_kernel` 下划线别名调用 runtime ABI。
- `kernel_gen/execute_engine/runtime_args.py`
  - 将 `RuntimeInput` / `_RuntimeInputValue` 从字符串 forward alias 改为当前文件内可运行期解析的真实 `TypeAlias`，避免 `get_type_hints` 经 `_runtime_args.RuntimeInput` 递归到无法在 `compiler.py` 全局解析的 `_MemoryRuntimeInput` 字符串。
  - 公开文件级 API 名称未变化：仍为 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`。
- `test/execute_engine/test_contract.py`
  - 新增 `get_type_hints` gate：`ExecuteRequest`、`CompiledKernel`、`CompiledKernel.execute` 三项公开注解必须成功解析。
  - 同一测试继续断言 `compiler_module` 不具有 `RuntimeInput`、`AllowAbsentMemoryArg`、`invoke_compiled_kernel`、`BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies` 等非下划线 internal API。
- 未使用 `__getattr__`、monkeypatch、自定义 `get_type_hints(globalns=...)`、`importlib` 或 `getattr` 反射绕过边界。

### 最小功能闭环

- 公开 facade 仍只暴露计划确认的 `CompileRequest`、`ExecuteRequest`、`ExecuteResult`、`CompiledKernel`、`ExecutionEngine` 与 strategy registry。
- `compiler.py` 旧公开路径仍不导出 runtime / builtin 文件级 API。
- 默认 `typing.get_type_hints(ExecuteRequest)`、`typing.get_type_hints(CompiledKernel)`、`typing.get_type_hints(CompiledKernel.execute)` 已可解析，覆盖 review 复现失败。

### Diff 反推自测

- 改动文件：`kernel_gen/execute_engine/compiler.py`、`kernel_gen/execute_engine/runtime_args.py`、`test/execute_engine/test_contract.py`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... get_type_hints(ExecuteRequest / CompiledKernel / CompiledKernel.execute) ... PY`，退出码 0；输出显示三项 hints keys 均成功返回，且 `compiler.py` 上六个禁止 internal API 均为 `False`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/execute_engine/runtime_args.py kernel_gen/execute_engine/builtin_strategy.py kernel_gen/execute_engine/strategy.py test/execute_engine/test_contract.py`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py`，退出码 0，`16 passed`。
  - 备注：首次全文件复跑曾在 `test_execute_engine_strategy_import_order_matrix` 的一个 subprocess 排列出现一次 `returncode=-11`；随后对同一 import 顺序手工复现 `5/5` 次退出码 0，单项 import-order pytest 退出码 0，最终全量 `test_contract.py` 退出码 0。当前未形成稳定阻断。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine`，退出码 0，`68 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/repo_conformance/test_private_api_boundaries.py`，退出码 0，`19 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine`，退出码 0，收集 `68` 个测试。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`，退出码 0。
- 静态扫描：
  - `rg -n "__getattr__|monkeypatch|get_type_hints\\([^\\n]*globalns|custom get_type_hints" kernel_gen/execute_engine/compiler.py kernel_gen/execute_engine/runtime_args.py test/execute_engine/test_contract.py || true`，退出码 0，输出为空。
  - `rg -n "importlib|getattr\\(" kernel_gen/execute_engine/compiler.py || true`，退出码 0，输出为空。
- 空白与敏感目录：
  - `git diff --check`，退出码 0。
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。
  - `git status --short -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，退出码 0，输出为空。

### 合同验收

- 本计划无必过 `expectation`，本轮未运行 expectation，也未把 expectation 作为通过依据。

### 减法检查

- 本轮未新增公开 API，未恢复任何被裁定禁止的旧公开路径 internal API。
- 新增 / 改动 `private callable`：无。
- 被替代旧逻辑：用 `_runtime_args` 私有模块别名替代原先无法解析的裸 `RuntimeInput` / `AllowAbsentMemoryArg` 注解；用真实 `RuntimeInput` TypeAlias 替代字符串 forward alias，删除公开注解反射对隐藏字符串名的依赖。
- 保留旧逻辑依据：`_invoke_compiled_kernel`、`_build_builtin_compile_artifacts`、`_install_builtin_compile_strategies` 仍以下划线别名保留，是 `compiler.py` facade 装配 strategy 与执行 ABI 的必要内部调用；测试已锁定这些对象不以非下划线名称暴露。

### 自检

- 接口：未扩大 `kernel_gen.execute_engine.__all__`；`compiler.py` 旧公开路径未新增非下划线 runtime/builtin internal API。
- 边界：未跨文件调用非公开 helper；`compiler.py` 只使用 `runtime_args.py` 文件级 API，并通过下划线 / 模块别名隐藏旧公开路径。
- 异常：未修改 failure phrase 或公开错误语义。
- 兼容性：公开 compile / execute / strategy 行为由全量 `test/execute_engine` 覆盖；公开反射行为由新增 `get_type_hints` gate 覆盖。
- 实现遗漏：第三轮 finding 已有实现和测试双重覆盖；未发现必须让非下划线 internal API 从 `compiler.py` 可 import 的情况。
- 冗余：未新增 wrapper、`__getattr__`、monkeypatch 或反射兼容层。
- 注释准确性：文件级 API 名称未变化；注解解析修复不改变公开 API 列表。
- 复用 / 函数粒度：未新增 private callable，未引入嵌套函数。
- 输入输出 / 资源 / 并发 / 性能：本轮只调整类型注解解析与别名承接，不改变运行时参数封送、编译、加载、cleanup 或执行路径。
- 测试有效性：新增 gate 会在 `get_type_hints` 重新失败或 `compiler.py` 旧路径重新泄漏 internal API 时失败。

### 结论

- `execute` 第三轮返工已完成。
- 当前候选 diff 可回流 `review`。

## review 复审记录 - 2026-05-27 21:12 +0800 - 不要啊教练

时间：2026-05-27 21:12 +0800
经办人：不要啊教练
任务：T-20260527-fd30965d / execute-engine-implementation-rebalance-refactor
任务目标：复审第三轮最小返工，核对 `compiler.py` 公开注解 `get_type_hints` 三项可解析、`compiler.py` 不恢复非下划线 runtime / builtin internal API、包根 `__all__` 不扩大、`test_contract` gate、全量 `test/execute_engine`、compileall、`git diff --check` 与敏感目录空 diff。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`
- 已执行：`GIT_TERMINAL_PROMPT=0 git fetch origin --prune`，退出码 0。
- 基线：`HEAD=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`merge-base=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`ahead/behind=0/0`。
- 对齐结论：当前待审 worktree 已对齐 latest `origin/main`，未发现需要合并的新主线提交、冲突或覆盖任务 diff 的风险。
- 计划书核对：任务 worktree 内计划书因 ignore 缺失，本轮继续只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md` 作为合同真源。

### 被审范围

- 候选改动：`kernel_gen/execute_engine/builtin_strategy.py`、`kernel_gen/execute_engine/compiler.py`、`kernel_gen/execute_engine/strategy.py`、新增 `kernel_gen/execute_engine/runtime_args.py`、`spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md`、`spec/execute_engine/execute_engine_target.md`、`spec/execute_engine/strategy.md`、`test/execute_engine/test_contract.py`、本任务记录。
- 禁止修改面核对：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 均无 tracked / cached / ignored 敏感改动。
- 合同验收：计划明确本任务无必过 `expectation`，本轮未运行 expectation，也未把 expectation 作为 diff 反推测试。

### Findings

- 未发现阻断项。

### 重点核对

- `compiler.py` 使用私有模块别名 `_runtime_args.RuntimeInput` / `_runtime_args.AllowAbsentMemoryArg` 修复公开注解反射；`typing.get_type_hints(ExecuteRequest)`、`typing.get_type_hints(CompiledKernel)`、`typing.get_type_hints(CompiledKernel.execute)` 均可解析。
- `compiler.py` 不具有 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`、`BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies` 非下划线绑定，旧公开路径未恢复 runtime / builtin internal API。
- 包根 `kernel_gen.execute_engine.__all__` 与 `compiler.__all__` exact set 仍为 `CompileStrategy`、`CompiledKernel`、`CompileRequest`、`ExecuteRequest`、`ExecuteResult`、`ExecutionEngine`、`get_compile_strategy`、`register_compile_strategy`；未扩大公开 API。
- `builtin_strategy.py` 本模块定义的非下划线对象只剩 `BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies`；`runtime_args.py` 本模块定义的非下划线对象只剩 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`。
- `test/execute_engine/test_contract.py` 已补 `get_type_hints` gate 和 forbidden internal API gate；若公开注解再次不可解析或 `compiler.py` 重新暴露上述 internal API 会失败。
- 静态扫描命中分类：`runtime_args.py` 中 `hasattr/getattr` 命中用于 runtime memory 参数的 shape/dtype/stride/data_ptr 轻量识别和 `ctypes` entry symbol 解析，符合计划中 runtime args ABI 封送职责；未命中 `ctx` / context 能力探测。`test_contract.py` 的 `importlib/getattr/hasattr` 命中属于公开面与 AST gate 测试代码。

### 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... get_type_hints / forbidden hasattr / exact __all__ / internal module defined-name audit ... PY`，退出码 0；输出显示三项 hints keys 成功返回，compiler 六个 forbidden internal API 均为 `False`，builtin/runtime 未授权非下划线本模块定义对象为空。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py`，退出码 0，`16 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine`，退出码 0，`68 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/repo_conformance/test_private_api_boundaries.py`，退出码 0，`19 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine`，退出码 0，收集 `68` 个测试。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/execute_engine/compiler.py kernel_gen/execute_engine/runtime_args.py kernel_gen/execute_engine/builtin_strategy.py kernel_gen/execute_engine/strategy.py test/execute_engine/test_contract.py`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`，退出码 0。
- 静态 callable 边界脚本：非装饰器嵌套函数、`object` 签名、短小 private callable、private callable 直接调用 private callable 均为空，退出码 0。
- `rg -n "hasattr\(|getattr\(|callable\(getattr|__getattr__|monkeypatch|get_type_hints\([^\n]*globalns|custom get_type_hints|: object\b|-> object\b|importlib" ...`：仅命中上述 runtime 参数识别、动态库 entry 解析与测试 gate，人工分类为允许命中。
- `git diff --check`，退出码 0。
- 手工空白检查覆盖新增 untracked `runtime_args.py` 与本轮 tracked 候选文件，未发现 trailing whitespace 或缺失 final newline。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，输出为空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，输出为空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，输出为空。

### Diff 反推审查

- 实现 diff 反推：`compiler.py` 注解修复、runtime/builtin 分层、registry 分层由 `test_contract.py`、全量 `test/execute_engine`、`py_compile`、`compileall` 与静态公开面脚本覆盖。
- 测试 diff 反推：`test_contract.py` 新增 gate 已直接复跑，并与 `test/repo_conformance/test_private_api_boundaries.py` 组合验证私有 API 边界不回退。
- spec diff 反推：`spec/execute_engine/*.md` 的分层说明与 `test_contract.py` 文件存在、API exact set、旧路径导入、target_support 退场和 internal module API exact set 对齐。
- expectation 单列：本计划无必过 expectation，本轮不运行、不修改、不作为通过依据。

### 减法审查

- 旧逻辑迁移：`compiler.py` 原 target include、entry shim、compile unit、编译路径和 runtime ABI 细节已迁入 `builtin_strategy.py` 与 `runtime_args.py`；`target_support.py` 未恢复。
- 第三轮减法：没有为修复注解反射恢复 `compiler.py` 旧公开路径的非下划线 `RuntimeInput` / `AllowAbsentMemoryArg` / runtime / builtin API 绑定，而是用 `_runtime_args` 私有模块别名保持反射可解析。
- 私有 callable：本轮未新增短小 private callable；静态脚本与 `test_execute_engine_private_callable_gate` 均未发现 private callable 小于 5 行有效代码或 private callable 直接调用 private callable。
- 保留依据：`_invoke_compiled_kernel`、`_build_builtin_compile_artifacts`、`_install_builtin_compile_strategies` 作为 `compiler.py` facade 的内部装配调用保留，均以下划线别名隐藏，不进入旧公开路径非下划线 API。

### 自检

- 已重新读取角色提示词、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、主仓共享计划、任务记录和实际 diff。
- 已核对执行人第三轮返工记录、执行前阅读、自检、Diff 反推自测、禁止修改面、公开 API / 文件级 API 列表、跨文件非公开 API、测试有效性和敏感目录门禁。
- 未发现仍需 execute 收口的公开边界、测试缺口、注释 / spec 明显不一致、未授权 expectation 改动或可维护性阻断项。

### 结论

- 结论：通过。
- 下一步：这是计划级任务，review 通过后应流转 `archive_acceptance / 计划书入档验收`，不得直接进入 merge。

## archive_acceptance / 计划书入档验收 - 2026-05-27 21:17 +0800 - 提莫炖蘑菇

时间：2026-05-27 21:17 +0800
经办人：提莫炖蘑菇
任务：T-20260527-fd30965d / execute-engine-implementation-rebalance-refactor
任务目标：核对计划级 execute-engine implementation rebalance 记录、review 通过结论、Diff 反推审查、test_contract gate、全量 test/execute_engine、compileall、git diff check、敏感目录空 diff 与可入档性。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`
- 已执行：`git fetch origin`，退出码 0。
- 基线：`HEAD=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`merge-base=1778f4f717b84dc46a6a889059fc8d6fdcef895b`。
- 对齐结论：当前待入档 worktree 已对齐 latest `origin/main`，未发现需要合并的新主线提交、冲突或覆盖任务 diff 的风险。
- 计划书核对：目标 worktree 内计划书因 ignore 缺失；本轮按主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/execute_engine_implementation_rebalance_refactor_green_plan.md` 只读核对。

### 候选范围与记录完整性

- 候选代码 / spec / test diff：
  - `kernel_gen/execute_engine/builtin_strategy.py`
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/execute_engine/strategy.py`
  - `kernel_gen/execute_engine/runtime_args.py`
  - `spec/execute_engine/execute_engine.md`
  - `spec/execute_engine/execute_engine_api.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/execute_engine/strategy.md`
  - `test/execute_engine/test_contract.py`
- 候选同批记录：`agents/codex-multi-agents/log/task_records/2026/25/20260527-execute-engine-implementation-rebalance-refactor.md` 为 untracked 候选文件，必须与代码 / spec / test 同批合入。
- review 通过记录：已核对 `2026-05-27 21:12 +0800 - 不要啊教练` 的 review 复审结论为 `通过`，且记录包含 latest 同步现场、Findings、Diff 反推审查、减法审查、验证和计划级下一阶段说明。
- 返工闭环：已核对提莫炖蘑菇两轮 `最小需改项` 与小李飞刀 / 金铲铲大作战 execute 返工记录，第三轮已收口 `typing.get_type_hints(...)` 公开注解可解析性，且未恢复 `compiler.py` 旧公开路径 runtime / builtin internal API 泄漏。

### Findings

- 未发现入档阻断项。

### 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py`，退出码 0，`16 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine`，退出码 0，`68 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/repo_conformance/test_private_api_boundaries.py`，退出码 0，`19 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine`，退出码 0，收集 `68` 个测试。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... get_type_hints / compiler forbidden internal API / package __all__ ... PY`，退出码 0；输出确认：
  - `ExecuteRequest` / `CompiledKernel` / `CompiledKernel.execute` 三项公开注解均可解析。
  - `compiler.py` 上 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel`、`BuiltinCompileArtifacts`、`build_builtin_compile_artifacts`、`install_builtin_compile_strategies` 均为 `False`。
  - 包根 `__all__` 仍为计划确认的 8 个公开 API。
- `git diff --check`，退出码 0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，输出为空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，输出为空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，输出为空。
- 合同验收：计划明确本任务无必过 `expectation`；本轮未运行 expectation，也未把 expectation 作为通过依据。

### Diff 反推审查 / 入档复核

- `compiler.py` facade、`strategy.py` registry、`builtin_strategy.py` 内置后端、`runtime_args.py` runtime ABI 分层由 `test_contract.py`、全量 `test/execute_engine`、`test_private_api_boundaries.py`、`compileall` 与 `get_type_hints` proof 覆盖。
- `spec/execute_engine/*.md` 与 `test_contract.py` 的 API exact set、旧路径导入、`target_support.py` 退场、internal module API exact set 和公开注解解析 gate 已对齐。
- 任务记录包含 execute、review、返工、复审与本次 archive_acceptance 记录；满足“任务记录与代码/spec/test 同批合入”门禁。

### 减法审查

- 旧逻辑迁移：`compiler.py` 原 target include、entry shim、compile unit、内置后端实现和 runtime ABI 细节已分拆到 `builtin_strategy.py` / `runtime_args.py`；`target_support.py` 未恢复。
- 公开边界：`kernel_gen.execute_engine.__all__` 未扩大；`compiler.py` 旧公开路径不再暴露 runtime / builtin 文件级 API。
- 私有 callable：review 记录与本轮复核均未发现新增短小 private callable、private callable 调用 private callable 或测试直连 private callable 阻断。
- 保留依据：`compiler.py` 中 `_runtime_args`、`_invoke_compiled_kernel`、`_build_builtin_compile_artifacts`、`_install_builtin_compile_strategies` 作为 facade 内部装配调用保留，均不进入旧公开路径非下划线 API。

### 自检

- 已重新读取个人提示词、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、主仓共享计划、任务记录和候选 diff。
- 已核对 latest 主线现场、review 通过记录、Diff 反推审查、减法审查、test_contract gate、全量 `test/execute_engine`、compileall、git diff check、敏感目录空 diff、无必过 expectation 口径和同批记录要求。
- 未发现剩余可执行返工项或入档阻断项。

### 结论

- 结论：`archive_acceptance 通过`。
- 下一步：可流转 `merge`。merge 必须同批合入本任务记录与候选代码 / spec / test；不得遗漏 `kernel_gen/execute_engine/runtime_args.py` 或任务记录。

---

## merge 记录 - 2026-05-27 21:22 CST - 李白

时间：2026-05-27 21:22 +0800
经办人：李白
任务：T-20260527-fd30965d / execute-engine-implementation-rebalance-refactor
任务目标：合入已通过 archive_acceptance 的 execute-engine implementation rebalance 候选代码、spec、test 与同批任务记录；确保 `runtime_args.py` 和本任务记录同批纳入，继续排除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

### 合并前同步

- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`。
- `git fetch --prune origin`：exit 0。
- `HEAD=1778f4f717b84dc46a6a889059fc8d6fdcef895b`。
- `origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`。
- `merge-base=1778f4f717b84dc46a6a889059fc8d6fdcef895b`。
- ahead/behind=`0/0`。
- 主仓 `/home/lfr/kernelcode_generate` 核对：`HEAD=origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`。
- 结果：latest main 未前进，无冲突、无覆盖任务 diff 风险。

### 实际合入来源

- 源 worktree：`/home/lfr/kernelcode_generate/wt-20260527-execute-engine-implementation-rebalance-refactor`。
- 源分支：`task/execute-engine-implementation-rebalance-refactor`。
- 源基线：`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`。
- 合入方式：在任务分支提交候选 diff 与本记录后，推送 `HEAD:main`；随后同步主仓本地 `main`。

### 实际候选范围

- 代码：
  - `kernel_gen/execute_engine/builtin_strategy.py`
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/execute_engine/strategy.py`
  - `kernel_gen/execute_engine/runtime_args.py`
- spec：
  - `spec/execute_engine/execute_engine.md`
  - `spec/execute_engine/execute_engine_api.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/execute_engine/strategy.md`
- test：
  - `test/execute_engine/test_contract.py`
- 任务记录：
  - `agents/codex-multi-agents/log/task_records/2026/25/20260527-execute-engine-implementation-rebalance-refactor.md`

### 任务记录核对

- 已核对管理员创建记录、execute 记录、review 不通过记录、execute 返工记录、review 复审不通过记录、第三轮 execute 返工记录、review 通过记录与 archive_acceptance 通过记录。
- 任务记录当前在 worktree 为 untracked 候选文件；提交前将显式 `git add` 并与代码/spec/test 同批纳入。
- 计划书因 ignore 不在任务 worktree 中；本次按记录与 archive_acceptance 口径只读引用主仓共享计划，不复制计划书。

### 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py`：exit 0，`16 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine`：exit 0，`68 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/repo_conformance/test_private_api_boundaries.py`：exit 0，`19 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine`：exit 0，收集 `68` 个测试。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... get_type_hints / forbidden compiler internal API / package __all__ ... PY`：exit 0；三项公开注解可解析，`compiler.py` 上六个 runtime / builtin internal API 均为 `False`，包根 `__all__` 仍为计划确认 8 项。
- `test ! -e kernel_gen/execute_engine/target_support.py`：exit 0。
- `git diff --check`：exit 0。
- 静态扫描 `rg -n "__getattr__|monkeypatch|get_type_hints\([^\n]*globalns|custom get_type_hints|: object\b|-> object\b|importlib" ...`：仅命中 `test_contract.py` 中公开面与 AST gate 的 `importlib` 测试代码；未命中实现侧 `compiler.py` / `runtime_args.py` / `builtin_strategy.py` / `strategy.py` 的禁止模式。

### 合同验收

- 本计划无必过 `expectation`。
- 本轮未运行 expectation，未修改、复制、新建、移动或删除 `expectation/`，也未把 expectation 作为通过依据。

### 敏感目录与禁止修改面

- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：输出为空。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：输出为空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：输出为空。
- 本次 merge 不纳入 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

### 冲突处理

- 未执行 merge/rebase/reset/checkout；latest main 未前进，未发生冲突。
- 未覆盖主仓或其它任务本地改动。

### 剩余风险

- 主仓当前存在其它任务的未跟踪记录/目录，本次 merge 不触碰。
- 本计划无必过 expectation；验证依据为 diff 反推 pytest、compileall、collect-only、静态 gate 和 archive_acceptance 记录。

### 结论

- merge 前核对通过；可提交并推送。
