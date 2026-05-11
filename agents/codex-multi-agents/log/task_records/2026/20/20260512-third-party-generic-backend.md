时间：2026-05-12 01:31 +0800
经办人：小李飞刀
任务：T-20260512-32961719 / third_party_generic_backend_green_plan
任务目标：按计划书一次完成 S1-S6 的 spec、实现、测试与验收闭环；添加 third_party generic backend 扩展机制，支持 backend auto-load、ModuleOp `emit_c_impl` handler、SourceProduct/SourceBundle、compile strategy registry，并跑通 dummy backend 与授权 expectation 验收。
执行前阅读记录：
- 已读取个人提示词 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`。
- 已读取仓库根 `AGENTS.md`，确认 execute 角色、公开 API、expectation、`.skills`、跨文件非公开 API、ctx 能力探测、`object` 签名和嵌套函数限制。
- 已读取 `agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读取 `TODO.md`，确认 `T-20260512-32961719` 为 execute / 小李飞刀 / 进行中。
- 已读取计划书 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`，确认 S1-S6、禁止修改面、公开 API 保持项、SourceProduct/SourceBundle 内部 helper 不公开、`xpu_sdnn4` 不作为验收口。
- 指定 worktree `/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend` 初始不存在；已从主仓 `HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72` 新建 worktree 分支 `task/third-party-generic-backend`，并确认 `HEAD...origin/main` 为 `0 0`。
- worktree 当前无任务 diff。
expectation manifest/hash baseline：
- 计划固定命令要求写入 `/tmp/third_party_generic_backend_expectation_baseline.sha256`。
- 当前 latest-main worktree 不包含 `expectation/` 目录；首次直接执行固定 `find expectation ...` 会产生 `find: expectation: No such file or directory`，不能作为有效 manifest。
- 已按现场修正为空 manifest：`/tmp/third_party_generic_backend_expectation_baseline.sha256`，`wc -l` 为 `0`，文件 sha256 为 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。
- 后续若新增 `expectation/dsl/gen_kernel/third_party_backend/**`，属于本任务授权范围；其它 expectation 路径仍不得新增、修改、移动或删除。
禁止修改面：
- 除授权 `expectation/dsl/gen_kernel/third_party_backend/**` 外，`expectation/**` 默认只读。
- `.skills/**` 禁止修改。
- 禁止修改 `include/**`、`kernel_gen/dsl/ast/**`、`kernel_gen/passes/**`、`kernel_gen/dialect/**`、`kernel_gen/operation/**`、`kernel/**`、外部第三方路径。
下一步：
- 按 S1-S6 扫描 `kernel_gen/dsl/gen_kernel/**`、`kernel_gen/execute_engine/**`、`kernel_gen/target/**`、对应 spec/test，先摸清现有 registry、emit、gen_kernel、ExecutionEngine.compile 与 target 实现，再分步落地。

时间：2026-05-12 02:27 +0800
经办人：小李飞刀
任务：T-20260512-32961719 / third_party_generic_backend_green_plan
任务目标：按计划书一次完成 S1-S6 的 spec、实现、测试与验收闭环；添加 third_party generic backend 扩展机制，支持 backend auto-load、ModuleOp `emit_c_impl` handler、SourceProduct/SourceBundle、compile strategy registry，并跑通 dummy backend 与授权 expectation 验收。
改动：
- `kernel_gen/dsl/gen_kernel/emit/register.py`：补齐 target backend auto-load、ModuleOp `emit_c_impl` handler、SourceProduct/SourceBundle 归一化、重复注册需 `override=True`、SourceProduct 非法路径/内容/返回值错误边界；保留 `dispatch_op_for_target(op, ctx, target)` 兼容入口，且只按指定 target 查询，不回退 CPU。
- `kernel_gen/dsl/gen_kernel/emit/__init__.py`：让 `emit_c(ModuleOp, ctx)` 走 registry handler；补 CPU / npu_demo ModuleOp handler；移除未知 target CPU fallback；未注册 target 保持旧公开失败面。
- `kernel_gen/dsl/gen_kernel/gen_kernel.py`：保留 `gen_kernel(obj, ctx) -> str` 签名；ModuleOp 走 `emit_c` registry；SourceBundle dump 时写 `source.cpp` 并展开 bundle artifact；SourceBundle parse/write helper 仅为当前文件内私有实现，不公开。
- `kernel_gen/dsl/gen_kernel/kernel_emitter.py`：收窄公开 API 列表，`KernelEmitter.emit()` 仍为公开入口，ModuleOp 仅保留 npu_demo 内部发射形态，不新增 `emit_c_module_impl`。
- `kernel_gen/execute_engine/compiler.py`、`kernel_gen/execute_engine/__init__.py`：新增计划确认的公开 compile strategy registry：`CompileStrategy.compile(request) -> CompiledKernel`、`register_compile_strategy(target, strategy, *, override=False) -> None`、`get_compile_strategy(target) -> CompileStrategy`；`ExecutionEngine.compile(...)` 签名不变并委托 strategy；compile-only target 的 `CompiledKernel.execute()` 稳定失败为 `execution_unsupported`。
- `kernel_gen/dsl/gen_kernel/emit/dummy_generic/__init__.py`：新增 dummy generic backend，按注册机制提供 ModuleOp SourceProduct 与 compile-only strategy；不作为通用公开 API 暴露。
- `spec/dsl/gen_kernel/backend_loader.md`、`spec/dsl/gen_kernel/source_product.md`、`spec/dsl/gen_kernel/source_bundle.md`、`spec/execute_engine/strategy.md`：新增专题 spec；同步更新 emit / gen_kernel / kernel_emitter / execute_engine / target registry 相关 spec，使公开 API、错误边界和测试章节与实现一致。
- `test/dsl/gen_kernel/test_backend_loader.py`、`test/dsl/gen_kernel/test_module_emitter.py`、`test/dsl/gen_kernel/test_source_bundle.py`、`test/execute_engine/test_compile_strategy.py`：补公开 pytest 覆盖 backend auto-load、missing backend、missing handler、duplicate override、SourceProduct/SourceBundle、dump artifact、安全路径、compile strategy registry 与 compile-only `execution_unsupported`。
- `test/execute_engine/test_contract.py`：同步 execute_engine 公开导出和稳定失败短语。
- 授权 expectation 仅新增 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`；因 worktree `.gitignore` 忽略 `expectation/`，两文件已用 `git add -f` 纳入任务 diff。未新增、修改、移动或删除其它 expectation 文件。
最小功能闭环：
- S1 backend auto-load：注册 target 且存在 `kernel_gen.dsl.gen_kernel.emit.<target>` 时按需导入；缺 backend 与 backend 内部导入失败分别给出 `backend_not_found` / `backend_import_failed`；未注册 target 不自动导入、不 CPU fallback。
- S2 ModuleOp handler：第三方 backend 可通过 `emit_c_impl(ModuleOp, target=...)` 返回 `str` 或 `Mapping[str, str]`；非法返回、非法 artifact path、bundle marker 冲突均公开失败。
- S3 SourceBundle：bundle 聚合文本使用 `// __KG_BUNDLE_FILE__:<path>` 标记；`dump_dir` 下输出 `source.cpp` 与安全 artifact 文件；内部 encode/decode/write helper 不公开。
- S4 compile strategy：strategy registry 只通过公开 API 注册/查询；重复注册必须显式 `override=True`；未知 target 不回退 CPU；dummy backend 编译只产物，不执行 kernel。
- S5 dummy backend 与授权 expectation：dummy backend 覆盖单文件 source、bundle source、compile-only execute 失败合同。
- S6 验收边界：`xpu_sdnn4` 不纳入实现或验收；未新增 `emit_c_module_impl`；`gen_kernel`、`emit_c`、`ExecutionEngine.compile` 公开签名保持不变。
Diff 反推自测：
- `PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，`264 tests collected`，退出码 0。
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，`264 passed, 2 warnings`，退出码 0。
- `coverage erase && PYTHONPATH=. coverage run --branch --source=kernel_gen.dsl.gen_kernel,kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/dsl/gen_kernel test/execute_engine test/target && coverage json -o /tmp/third_party_generic_backend_coverage.json && coverage report --include='kernel_gen/dsl/gen_kernel/*,kernel_gen/execute_engine/*,kernel_gen/target/*'` -> 通过，`264 passed, 2 warnings`；coverage JSON 已写 `/tmp/third_party_generic_backend_coverage.json`；当前专题覆盖报告 TOTAL `91%`，退出码 0。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend` -> 通过，退出码 0。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend` -> 通过，退出码 0。
- expectation 授权范围核对脚本 -> 通过，仅命中 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`。
禁止修改面与静态扫描：
- `git diff --check && git diff --cached --check && git diff --quiet -- .skills && test -z "$(git status --short --untracked-files=all -- .skills)"` -> 通过，退出码 0；`.skills` 空 diff。
- `rg -n 'xpu_sdnn4|dummy_generic' kernel_gen/dsl/gen_kernel/emit/__init__.py kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/gen_kernel.py kernel_gen/execute_engine/compiler.py || true` -> 无输出，确认主链未引入 `xpu_sdnn4` 或 dummy target 特判。
- `rg -n 'sdnn\.gen|from sdnn|import sdnn' kernel_gen test || true` -> 无输出。
- `rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr' kernel_gen/dsl/gen_kernel kernel_gen/execute_engine test/dsl/gen_kernel test/execute_engine || true` -> 无输出，未新增 ctx 能力探测。
- target-name 静态扫描仍命中既有 `kernel_gen/execute_engine/compiler.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py` 中 CPU / npu_demo 内置分支和 `emit_context.py` 文档示例；本轮新增入口已避免在主链用 dummy target 特判。
- 测试私有字段扫描仅命中既有 `test/execute_engine/test_invoke.py` 假对象 `_stride/_contiguous/_data_ptr` 与 `test/dsl/gen_kernel/test_gen_kernel.py` 中 `_legacy` 字符串，不属于本轮新增跨文件非公开 API 直连。
自检：
- 接口：未新增 `emit_c_module_impl`；`emit_c(obj, ctx)`、`gen_kernel(obj, ctx)`、`dsl_gen_kernel(...)`、`ExecutionEngine.compile(...)` 签名保持不变；新增 compile strategy API 与计划书确认项一致；SourceProduct/SourceBundle parse/write helper 未公开。
- 边界与异常：覆盖未注册 target 不 fallback、missing backend、backend import failure、missing ModuleOp handler、重复注册、非法 SourceProduct 类型、非法 bundle 路径、bundle marker 冲突、compile-only execute 失败。
- 兼容性：单 op `gen_kernel` 仍委托 `emit_c_op`；CPU/npu_demo 既有 gen_kernel / execute_engine / target pytest 全部通过；未知 target 保持公开失败而不是静默 fallback。
- 实现遗漏：计划书 S1-S6 对应 spec、实现、测试、授权 expectation 均已落地；`xpu_sdnn4` 明确不纳入。
- 冗余与复用：backend loader 与 SourceBundle 校验集中在 `emit/register.py` 与 `gen_kernel.py` 当前文件内 helper；dummy backend 仅用于验收，不污染主链。
- 函数粒度：新增 helper 均为顶层 helper；未新增非装饰器嵌套函数。
- 输入输出与资源：SourceBundle dump 校验相对路径、拒绝绝对路径/上跳/目录/symlink escape；compile strategy dummy 产物落在 dump_dir 或临时目录。
- 并发与性能：registry 仍为进程内注册表，重复注册需 override，未引入后台线程或共享文件锁；dummy strategy 只写本地 artifact。
- 测试有效性：Diff 反推 pytest 覆盖改动主链与新公开边界；expectation 仅单列合同验收，不替代 pytest。
结论：execute 已完成，当前可按流程流转 review。

时间：2026-05-12 02:30 +0800
经办人：不要啊教练
任务：T-20260512-32961719 / third_party_generic_backend_green_plan review 前置核对
任务目标：按最新审查前置同步规则，在不覆盖任务 diff、不丢失他人改动前提下同步最新 origin/main，并确认计划书、任务记录、合同资产与禁止修改面后再进入 review。
改动：未修改业务文件、spec、测试、计划书、expectation 或 .skills；仅追加本任务记录。
验证：
- 执行目录：/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend。
- `git fetch origin --prune` -> 通过，退出码 0。
- 更新基线：HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72；origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72；merge-base=82dd3b696e01142f1a90e2cc4675398322c71b72。
- 更新结果：当前待审 worktree 已与最新 origin/main 对齐，无需 merge；未覆盖任务 diff。
- 计划资产核对：`ARCHITECTURE/plan/third_party_generic_backend_green_plan.md` 在目标 worktree 内缺失；主仓 /home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md 存在，但尚未获得管理员/架构师授权用主仓共享计划替代目标 worktree 计划资产继续 review。
- diff scope 预核对：当前 diff 含 staged expectation 新增 `expectation/dsl/gen_kernel/third_party_backend/__main__.py`、`expectation/dsl/gen_kernel/third_party_backend/basic.py`；execute 记录声称属于授权范围，但因目标 worktree 缺计划资产，本轮尚不能在 review 结论中确认授权来源闭合。
- 未继续运行 pytest / coverage / expectation：原因是审查前置资产缺失，按规则需先暂停并回报管理员，不应在缺计划资产场景下继续形成审查结论。
自检：已按 review 前置要求完成 fetch 与安全同步核对；未修改禁止面；已发现目标 worktree 缺计划资产这一前置阻塞，并按规则暂停，不使用主仓计划替代目标 worktree 合同真源自行放行；后续需管理员或架构师明确裁定后再继续真实审查与 Diff 反推审查。
结论：阻塞，待管理员裁定是否授权本轮只读引用主仓共享计划继续 review，或退回 execute 补齐目标 worktree 的计划资产；当前不进入通过/最小需改项审查结论。

时间：2026-05-12 02:32 +0800
经办人：守护最好的爱莉希雅
任务：T-20260512-32961719 / third_party_generic_backend_green_plan 架构裁定
裁定事项：目标 worktree 缺 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`，是否允许 review 只读引用主仓共享计划作为合同真源继续审查。
裁定结论：
- 授权 review 只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md` 作为本轮合同真源继续审查。
- 不要求回 execute 复制、补建或修改目标 worktree 内的计划资产；不得把主仓共享计划复制进 worktree 作为任务 diff。
- 目标 worktree 缺计划资产必须在 review 记录中明示，合同真源路径必须写成主仓共享计划绝对路径。
expectation 授权核对：
- 当前 staged 新增 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 在主仓共享计划授权范围 `expectation/dsl/gen_kernel/third_party_backend/**` 内。
- 当前 staged 新增 `expectation/dsl/gen_kernel/third_party_backend/basic.py` 在主仓共享计划授权范围 `expectation/dsl/gen_kernel/third_party_backend/**` 内。
- 上述判断只确认路径 scope 合法；review 仍必须按计划正文复核 expectation manifest/hash baseline、`git diff` / `git status` scope、内容是否符合合同、`.skills` 空 diff、公开 API/spec/test 边界和静态扫描。
后续 review 要求：
- 基于 latest 同步后的目标 worktree `/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend` 执行 review。
- 使用主仓共享计划作为只读合同真源，不修改主仓计划、不修改 worktree 计划资产。
- 若 review 发现授权 scope 外 expectation 变更、`.skills` 变更、跨文件非公开 API、测试直连非 API、ctx 能力探测、`object` 签名、非装饰器嵌套函数或其它可执行缺口，应按正常流程退回 execute。

时间：2026-05-12 02:32 +0800
经办人：大闸蟹
任务：T-20260512-32961719 / third_party_generic_backend_green_plan review 前置裁定
裁定：
- 授权 review 本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md` 作为合同真源继续审查；不要求退回 execute 补齐目标 worktree 内的 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`。
- 裁定理由：目标 worktree 已同步到 `origin/main@82dd3b696e01142f1a90e2cc4675398322c71b72`，任务 diff 未覆盖主线；主仓共享计划存在且是本计划已通过互评、可下发的合同真源。缺少 worktree 内计划资产属于承载缺口，不改变当前任务的合同内容。
- expectation 授权核对口径：主仓共享计划明确写明本计划仅授权新增或修改 `expectation/dsl/gen_kernel/third_party_backend/**`，其它 `expectation/**` 必须保持 diff 为空。当前 staged expectation 新增 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py` 均在授权范围内；review 仍需复核没有其它 tracked / untracked expectation 变更。
- review 要求：记录中必须写明“待审 worktree 缺计划资产，本轮只读引用主仓共享计划作为合同真源”；继续按计划正文核对授权 expectation、`.skills` 空 diff、禁止修改面、公开 API/spec/test 边界、Diff 反推审查与固定验收命令。
结论：可继续 review，不回 execute。

时间：2026-05-12 02:40 +0800
经办人：不要啊教练
任务：T-20260512-32961719 / third_party_generic_backend_green_plan review
任务目标：基于最新 origin/main 同步后的 worktree，按主仓共享计划只读合同真源审查 third_party generic backend 扩展机制、dummy backend、spec/pytest、授权 expectation 范围、公开 API/spec/test 边界、Diff 反推审查与固定验收命令。
改动：未修改业务文件、spec、测试、计划书、expectation 或 .skills；仅追加本任务记录。
审查基线与合同真源：
- 执行目录：/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend。
- 最新同步基线：HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72；origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72；merge-base=82dd3b696e01142f1a90e2cc4675398322c71b72；`git fetch origin --prune` 已通过，无需 merge，未覆盖任务 diff。
- 待审 worktree 缺 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`；本轮按守护最好的爱莉希雅与大闸蟹写回记录的裁定，只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md` 作为合同真源继续 review；未复制、未新建、未修改 worktree 计划资产。
- expectation 授权依据：主仓共享计划仅授权 `expectation/dsl/gen_kernel/third_party_backend/**`；当前 staged expectation 只有 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`，未发现其它 tracked/untracked expectation 变更。
真实审查：
- 已读取实际 diff 与新增未跟踪文件，覆盖 `kernel_gen/dsl/gen_kernel/**`、`kernel_gen/execute_engine/**`、`spec/dsl/gen_kernel/**`、`spec/execute_engine/**`、`spec/target/registry.md`、`test/dsl/gen_kernel/**`、`test/execute_engine/**`、授权 expectation 新增文件与任务记录。
- 已核对禁止修改面：`.skills` 空 diff；除授权 `expectation/dsl/gen_kernel/third_party_backend/**` 外无其它 expectation 变更；未见 `include/**`、`kernel_gen/dsl/ast/**`、`kernel_gen/passes/**`、`kernel_gen/dialect/**`、`kernel_gen/operation/**`、`kernel/**`、外部第三方路径变更。
- 已核对静态边界：本轮扫描未发现 `hasattr(ctx...)`、`getattr(ctx...)`、`callable(getattr(...))` ctx 能力探测；未发现新增 `object` 签名；未发现 `xpu_sdnn4`、`sdnn.gen`、`from sdnn`、`import sdnn` 命中；AST 扫描仅命中 `emit_c_impl` 等装饰器工厂内部 `decorator` 闭包，属于装饰器实现所需闭包场景。
发现：
- 阻断：`kernel_gen/dsl/gen_kernel/emit/register.py:475` 让 `_dispatch_op_with_registry(...)` 在显式 target registry 未命中时继续查询 `_OP_REGISTRY` 默认注册表；但 `spec/dsl/gen_kernel/emit/register.md:45` 与 `spec/dsl/gen_kernel/emit/register.md:207` 明确要求 `dispatch_op_for_target(...)` 只查询指定 target，不得回退默认注册表或 CPU 注册表。公开反证：在独立 Python 进程中通过公开 `emit_c_impl(ModuleOp, override=True)` 注册默认 ModuleOp handler 后，`dispatch_op_for_target(module, ctx, "review_generic")` 返回 `default-leaked`。影响：显式 target 隔离被破坏，第三方 target 查询可能误用默认 handler。最小修复：为 `dispatch_op_for_target(...)` 使用只查 target-scoped registry 的分发路径，并新增公开 pytest 锁死默认注册表不能泄漏到显式 target。
- 阻断：`spec/execute_engine/strategy.md:105` 与 `spec/execute_engine/strategy.md:106` 写明使用 `request` 时 `source`、`function` 必须为 `None`，但 `kernel_gen/execute_engine/compiler.py:2098` 到 `kernel_gen/execute_engine/compiler.py:2103` 在 `request is not None` 时直接忽略调用方传入的 `source` 与 `function`，没有公开失败。公开反证：`ExecutionEngine(target="review_strategy").compile(source="conflicting-source", function="conflicting-func", request=CompileRequest(...))` 会继续把 request 交给 strategy 并返回 `request-func`。影响：公开 API 的冲突参数语义与 spec 不一致，调用方错误参数会被静默吞掉。最小修复：按 spec 显式拒绝 `request` 与 `source/function` 混用并补 pytest；若需要保持忽略行为，必须先同步 spec 并取得用户确认。
- 阻断：新建 spec 结构与 API 口径未收口。`spec/dsl/gen_kernel/backend_loader.md:21`、`spec/dsl/gen_kernel/source_product.md:15`、`spec/dsl/gen_kernel/source_bundle.md:14`、`spec/execute_engine/strategy.md:18` 均在 `API 列表` 后直接进入 `依赖`，缺少标准要求的 `文档信息` 章节；`spec/dsl/gen_kernel/emit/register.md:15` 与 `kernel_gen/dsl/gen_kernel/emit/register.py:14` 把 `emit_c_include_impl` 写成 `emit_c_include_impl(target: str, override: bool = False)`，但真实实现 `kernel_gen/dsl/gen_kernel/emit/register.py:416` 是 keyword-only `emit_c_include_impl(*, target: str, override: bool = False)`；`spec/dsl/gen_kernel/source_bundle.md:70` 期望 marker 内容失败为 `source_bundle_malformed`，而实现 `kernel_gen/dsl/gen_kernel/emit/register.py:309` 到 `kernel_gen/dsl/gen_kernel/emit/register.py:310` 与测试 `test/dsl/gen_kernel/test_source_bundle.py:148` 锁定的是 `source_product_invalid`。影响：spec/API 快速索引、详细语义和测试期望不一致，后续执行人或第三方 backend 无法按 spec 机械实现。最小修复：补齐新 spec 的 `文档信息`，把 keyword-only `*` 写进所有 API 列表和详细说明，并统一 SourceBundle marker 内容非法时的稳定失败短语到 spec/实现/测试同一口径。
Diff 反推审查：
- 被审 diff 文件：`kernel_gen/dsl/gen_kernel/emit/__init__.py`、`kernel_gen/dsl/gen_kernel/emit/register.py`、`kernel_gen/dsl/gen_kernel/gen_kernel.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`kernel_gen/execute_engine/__init__.py`、`kernel_gen/execute_engine/compiler.py`、`kernel_gen/dsl/gen_kernel/emit/dummy_generic/__init__.py`、新增/修改 spec、`test/dsl/gen_kernel/test_backend_loader.py`、`test/dsl/gen_kernel/test_module_emitter.py`、`test/dsl/gen_kernel/test_source_bundle.py`、`test/execute_engine/test_compile_strategy.py`、`test/execute_engine/test_contract.py`、授权 expectation 新增文件。
- 反推测试命令覆盖：backend auto-load、ModuleOp handler、SourceProduct/SourceBundle、compile strategy、execute_engine/target 回归与授权 expectation 入口均已复跑；但测试未覆盖上述 `dispatch_op_for_target(...)` 默认注册表泄漏与 `ExecutionEngine.compile(request=...)` 参数冲突，且 spec 结构/API 口径问题不能由现有 pytest 发现。
验证：
- `PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，264 tests collected，退出码 0。
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，264 passed, 2 warnings，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend` -> 通过，退出码 0。该 expectation 仅作为授权合同验收单列，不计入 Diff 反推测试。
- `coverage erase` -> 通过，退出码 0。
- `PYTHONPATH=. coverage run --branch --source=kernel_gen.dsl.gen_kernel,kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，264 passed, 2 warnings，退出码 0。
- `coverage json -o /tmp/third_party_generic_backend_coverage.json` -> 通过，退出码 0；`coverage report --include='kernel_gen/dsl/gen_kernel/*,kernel_gen/execute_engine/*,kernel_gen/target/*'` -> TOTAL 91%，退出码 0。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend` -> 通过，退出码 0。
- `git diff --check` -> 通过，退出码 0。
- `git diff --cached --check` -> 通过，退出码 0。
- `git diff --quiet -- .skills` -> 通过，退出码 0；`git status --short --untracked-files=all -- .skills` -> 空。
- `/tmp/third_party_generic_backend_expectation_baseline.sha256` 存在；expectation scope 脚本 -> 通过，仅授权路径有新增。
- 静态扫描：ctx 能力探测、object 签名、`xpu_sdnn4`、`sdnn.gen` 均无命中；非装饰器嵌套函数扫描未发现违规，仅装饰器工厂闭包命中。
自检：已按实际 diff 做真实审查和 Diff 反推审查；测试与合同验收通过，但仍存在 3 个明确可执行阻断，且均影响公开 API/spec 或 target 隔离边界，不能以“当前测试能跑”放行。未修改 expectation、.skills、业务代码或计划书；后续应回 execute 修复并补对应 pytest/记录。
结论：最小需改项，退回 execute 修复上述阻断项后再 review；计划级任务不得进入架构复核/终验。

时间：2026-05-12 02:49 +0800
经办人：小李飞刀
任务：T-20260512-32961719 / third_party_generic_backend_green_plan execute 返修
任务目标：修复 review 指出的最小阻断项：`dispatch_op_for_target(...)` 不得查询默认注册表并补公开 pytest；`ExecutionEngine.compile(request=...)` 按 spec 拒绝 `source/function` 混用；补齐新 spec 文档信息；修正 `emit_c_include_impl` keyword-only 签名索引；统一 SourceBundle marker 内容非法失败短语。
执行前阅读记录：
- 已重新读取个人提示词 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、仓库根 `AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读取本任务记录中的 review 阻断项和双架构关于主仓共享计划只读合同真源的裁定；本轮不复制、不修改 worktree 内缺失的计划资产。
改动：
- `kernel_gen/dsl/gen_kernel/emit/register.py`：为 `_dispatch_op_with_registry(...)` 增加 `include_default` 控制；普通 `dispatch_op(...)` 保留默认 registry fallback，显式 `dispatch_op_for_target(...)` 使用 `include_default=False`，只查指定 target registry；文件级 API 列表把 `emit_c_include_impl` 改为 keyword-only 签名。
- `test/dsl/gen_kernel/test_backend_loader.py`：新增 `_DefaultOnlyOp` 与 `test_dispatch_op_for_target_does_not_read_default_registry`，通过公开 `emit_c_impl(...)` 注册默认 handler 后验证 `dispatch_op_for_target(...)` 不泄漏默认 registry。
- `kernel_gen/execute_engine/compiler.py`：`ExecutionEngine.compile(request=...)` 在 `source` 或 `function` 非 `None` 时显式抛出 `source_empty_or_invalid: request cannot be combined with source or function`，不再静默忽略冲突参数。
- `test/execute_engine/test_compile_strategy.py`：新增 `test_compile_request_rejects_source_or_function_mix`，覆盖 `request+source` 与 `request+function` 两类公开冲突。
- `kernel_gen/dsl/gen_kernel/emit/register.py`、`test/dsl/gen_kernel/test_source_bundle.py`、`spec/dsl/gen_kernel/source_bundle.md`、`spec/dsl/gen_kernel/source_product.md`：统一 artifact content 含完整 SourceBundle marker 行时的稳定失败短语为 `source_bundle_malformed`；非字符串 SourceProduct 仍为 `source_product_invalid`；symlink escape 仍为 `source_bundle_path_escape`。
- `spec/dsl/gen_kernel/backend_loader.md`、`spec/dsl/gen_kernel/source_bundle.md`、`spec/dsl/gen_kernel/source_product.md`、`spec/execute_engine/strategy.md`、`spec/dsl/gen_kernel/emit/register.md`：补齐 `文档信息`，同步 keyword-only 签名索引和测试用例名称；`spec/execute_engine/execute_engine.md` 同步 `request` 与 `source/function` 不得混用的公开注意事项。
最小功能闭环：
- review 反证 1 已闭合：显式 target 查询不再读取默认 op registry；新增 pytest 会在默认 handler 泄漏时失败。
- review 反证 2 已闭合：`ExecutionEngine.compile(request=...)` 不再吞掉冲突 `source/function`，新增 pytest 锁定 `source_empty_or_invalid`。
- review 反证 3 已闭合：新增 spec 均有 `文档信息`；`emit_c_include_impl` 的 `*` 已同步到文件级 API 列表与 spec；SourceBundle marker 内容非法短语在实现、spec、pytest 中一致。
Diff 反推自测：
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_backend_loader.py test/dsl/gen_kernel/test_source_bundle.py test/execute_engine/test_compile_strategy.py` -> 通过，`16 passed, 1 warning`，退出码 0。
- `PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，`266 tests collected`，退出码 0。
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，`266 passed, 2 warnings`，退出码 0。
- `coverage erase && PYTHONPATH=. coverage run --branch --source=kernel_gen.dsl.gen_kernel,kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/dsl/gen_kernel test/execute_engine test/target && coverage json -o /tmp/third_party_generic_backend_coverage.json && coverage report --include='kernel_gen/dsl/gen_kernel/*,kernel_gen/execute_engine/*,kernel_gen/target/*'` -> 通过，`266 passed, 2 warnings`；coverage JSON 写入 `/tmp/third_party_generic_backend_coverage.json`；专题 coverage TOTAL `91%`，退出码 0。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend` -> 通过，退出码 0。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend` -> 通过，退出码 0。
- expectation 授权范围核对脚本 -> 通过，仅命中 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`；本轮未新增其它 expectation 改动。
禁止修改面与静态扫描：
- `git diff --check && git diff --cached --check && git diff --quiet -- .skills && test -z "$(git status --short --untracked-files=all -- .skills)"` -> 通过，退出码 0；`.skills` 空 diff。
- `rg -n 'emit_c_include_impl\(target:|emit_c_include_impl\(\*, target' kernel_gen spec test` -> 仅命中 keyword-only `emit_c_include_impl(*, target: str, override: bool = False)` 形式。
- `rg -n 'request cannot be combined|request.*source|source.*request' kernel_gen/execute_engine spec/execute_engine test/execute_engine` -> 命中实现、spec 与新增 pytest，未发现相反口径。
- `rg -n 'source_product_invalid|source_bundle_malformed|source_bundle_path_escape' spec/dsl/gen_kernel/source_bundle.md spec/dsl/gen_kernel/source_product.md test/dsl/gen_kernel/test_source_bundle.py kernel_gen/dsl/gen_kernel/emit/register.py kernel_gen/dsl/gen_kernel/gen_kernel.py` -> marker 内容非法为 `source_bundle_malformed`，非字符串产品为 `source_product_invalid`，symlink escape 为 `source_bundle_path_escape`。
- `rg -n '^## 文档信息' spec/dsl/gen_kernel/backend_loader.md spec/dsl/gen_kernel/source_bundle.md spec/dsl/gen_kernel/source_product.md spec/execute_engine/strategy.md spec/dsl/gen_kernel/emit/register.md` -> 五个相关 spec 均命中。
- `rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr' kernel_gen/dsl/gen_kernel kernel_gen/execute_engine test/dsl/gen_kernel test/execute_engine || true` -> 无输出。
- `rg -n 'xpu_sdnn4|dummy_generic' kernel_gen/dsl/gen_kernel/emit/__init__.py kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/gen_kernel.py kernel_gen/execute_engine/compiler.py || true` -> 无输出；dummy backend 仍只在独立 backend 模块、spec/test/expectation 中出现。
- `rg -n 'sdnn\.gen|from sdnn|import sdnn' kernel_gen test || true` -> 无输出。
自检：
- 接口：未新增未确认公开 API；`dispatch_op_for_target(...)`、`ExecutionEngine.compile(...)`、`emit_c_include_impl(...)` 的公开签名与 spec 对齐；`ExecutionEngine.compile(...)` 的混参失败语义已写入 spec。
- 边界与异常：新增测试分别锁定默认 registry 泄漏、`request+source`/`request+function` 混用、SourceBundle marker 行错误短语；测试在实现回退时会失败。
- 兼容性：普通 `dispatch_op(...)` 仍允许默认 registry fallback；只收窄显式 `dispatch_op_for_target(...)`；既有 gen_kernel/execute_engine/target pytest 全量相关集合通过。
- 实现遗漏：review 三项阻断均已落地；未修改 `.skills`；除既有授权路径外无 expectation 改动。
- 冗余与复用：新增分发控制参数只服务当前文件内 helper；未引入跨文件非公开 helper 调用；无非装饰器嵌套函数。
- 输入输出、资源、并发、性能：本轮变更不引入新资源生命周期；SourceBundle 路径/内容错误仍在 encode/dump 边界显式失败；compile request 冲突在 strategy 调度前失败，避免无效 strategy 调用。
- 测试有效性：Diff 反推测试覆盖改动实现与 spec 口径，授权 expectation 仅作为合同验收单列。
结论：execute 返修已完成，可再次流转 review。

时间：2026-05-12 03:06 +0800
经办人：提莫炖蘑菇
任务：T-20260512-32961719 / third_party_generic_backend_green_plan review 复审
任务目标：复审 execute 返修后的 third-party generic backend diff，重点核对 `dispatch_op_for_target(...)` 默认 registry 泄漏、`ExecutionEngine.compile(request=...)` 混参拒绝、新 spec 文档信息、`emit_c_include_impl` keyword-only 签名索引、SourceBundle marker 错误短语、公开 API/spec/test 一致性、Diff 反推审查、授权 expectation、禁止修改面与静态扫描。
审查基线与合同真源：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend`。
- review 前同步：`git fetch origin --prune` -> 通过；`HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72`，`origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72`，`merge-base=82dd3b696e01142f1a90e2cc4675398322c71b72`；无需 merge，未覆盖任务 diff。
- 待审 worktree 仍缺 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`；本轮沿用守护最好的爱莉希雅与大闸蟹记录裁定，只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md` 作为合同真源；未复制、未新建、未修改 worktree 计划资产。
真实审查：
- 已读取实际 diff 与新增未跟踪文件，覆盖 `kernel_gen/dsl/gen_kernel/**`、`kernel_gen/execute_engine/**`、`kernel_gen/target/**`、相关 spec、相关 pytest、授权 expectation 与任务记录。
- 已复核返修项：`dispatch_op_for_target(...)` 已使用 `include_default=False` 且新增公开 pytest 覆盖默认 registry 不泄漏；`ExecutionEngine.compile(request=...)` 已拒绝 `source/function` 混用并新增公开 pytest；新增 spec 已补 `文档信息`；`emit_c_include_impl` keyword-only 签名已在 register spec 与实现文件 API 列表同步；SourceBundle marker 内容非法已统一为 `source_bundle_malformed`。
发现：
- 阻断：`spec/dsl/gen_kernel/emit/register.md:315` 到 `spec/dsl/gen_kernel/emit/register.md:321` 的功能与用例清单仍引用 7 个不存在的 pytest 名称：`test_backend_auto_loads_registered_module_backend`、`test_unregistered_target_does_not_fallback_to_cpu`、`test_missing_backend_module_reports_backend_not_found`、`test_backend_internal_import_error_reports_backend_import_failed`、`test_missing_module_handler_reports_backend_handler_not_found`、`test_duplicate_backend_registration_requires_override`、`test_module_handler_returns_source_bundle_mapping`。当前真实测试名分别在 `test/dsl/gen_kernel/test_backend_loader.py` 与 `test/dsl/gen_kernel/test_module_emitter.py` 中为 `test_backend_loader_imports_registered_dummy_backend`、`test_backend_loader_rejects_unregistered_target_without_cpu_fallback`、`test_backend_loader_distinguishes_missing_module`、`test_backend_loader_distinguishes_backend_import_failure`、`test_backend_loader_distinguishes_missing_module_handler`、`test_emit_registry_duplicate_requires_explicit_override`、`test_module_handler_returns_mapping_as_source_bundle`。影响：spec/test 映射不可机械追踪，review/终验按 spec 反推 pytest 时会落到不存在入口。最小修复：把该表 `建议测试` 列改为当前真实 pytest 名称，或同步重命名测试并保持 collect-only 通过。
- 阻断：`kernel_gen/execute_engine/compiler.py:17` 与 `kernel_gen/execute_engine/__init__.py:16` 的文件级 API 列表写成 `class CompileStrategy()`，但真实实现是 `kernel_gen/execute_engine/compiler.py:1837` 的 `class CompileStrategy(Protocol)`，且 `spec/execute_engine/strategy.md:11`、`spec/execute_engine/execute_engine.md:25`、`spec/execute_engine/execute_engine_api.md:16` 均把公开 API 写为 `class CompileStrategy(Protocol)`。影响：本轮新增公开 compile strategy API 的文件级快速索引与 spec/实现不一致，不满足功能实现文件 API 列表同步要求。最小修复：把 `compiler.py` 与 `execute_engine/__init__.py` 文件级 API 列表中的 `class CompileStrategy()` 统一为 `class CompileStrategy(Protocol)`。
Diff 反推审查：
- 被审 diff 文件：`kernel_gen/dsl/gen_kernel/emit/__init__.py`、`kernel_gen/dsl/gen_kernel/emit/register.py`、`kernel_gen/dsl/gen_kernel/gen_kernel.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`kernel_gen/execute_engine/__init__.py`、`kernel_gen/execute_engine/compiler.py`、`kernel_gen/dsl/gen_kernel/emit/dummy_generic/__init__.py`、新增/修改 spec、`test/dsl/gen_kernel/test_backend_loader.py`、`test/dsl/gen_kernel/test_module_emitter.py`、`test/dsl/gen_kernel/test_source_bundle.py`、`test/execute_engine/test_compile_strategy.py`、`test/execute_engine/test_contract.py`、授权 expectation 新增文件。
- 返修相关反推测试已复跑并通过；但上述两个 spec/API 索引问题属于文档与公开边界一致性缺口，当前 pytest 通过不能替代。
验证：
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_backend_loader.py test/dsl/gen_kernel/test_source_bundle.py test/execute_engine/test_compile_strategy.py` -> 通过，`16 passed, 1 warning`，退出码 0。
- `PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，`266 tests collected`，退出码 0。
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target` -> 通过，`266 passed, 2 warnings`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend` -> 通过，退出码 0；该 expectation 仅作为授权合同验收单列，不计入 Diff 反推测试。
- `coverage erase && PYTHONPATH=. coverage run --branch --source=kernel_gen.dsl.gen_kernel,kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/dsl/gen_kernel test/execute_engine test/target && coverage json -o /tmp/third_party_generic_backend_coverage.json && coverage report --include='kernel_gen/dsl/gen_kernel/*,kernel_gen/execute_engine/*,kernel_gen/target/*'` -> 通过，`266 passed, 2 warnings`；coverage JSON 写入 `/tmp/third_party_generic_backend_coverage.json`；专题 coverage TOTAL `91%`，退出码 0。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend` -> 通过，退出码 0。
- `git diff --check`、`git diff --cached --check`、`git diff --quiet -- .skills`、`git status --short --untracked-files=all -- .skills` -> 通过，`.skills` 空 diff。
- expectation manifest/hash scope gate -> 通过，仅授权路径 `expectation/dsl/gen_kernel/third_party_backend/**` 有新增；未发现 scope 外 expectation tracked/untracked/ignored 变更。
- 静态扫描：`hasattr(ctx...)` / `getattr(ctx...)` / `callable(getattr(...))` 无命中；主链文件无 `xpu_sdnn4` / `dummy_generic` target 特判；`sdnn.gen` / `from sdnn` / `import sdnn` 无命中；changed-file 静态扫描未发现本轮新增 skip/xfail/collect_ignore/coverage 配置变更；非装饰器嵌套函数扫描仅命中类方法与装饰器工厂闭包。
自检：已按实际 diff 做真实审查和 Diff 反推审查；未修改业务代码、spec、测试、计划书、expectation 或 `.skills`，仅追加任务记录；返修测试与授权合同验收均通过，但仍有 2 个明确可执行的公开 spec/API 索引一致性问题，不能给通过。
结论：最小需改项，退回 execute 修复上述两项后再 review；计划级任务不得进入架构复核/终验。

时间：2026-05-12 03:10 +0800
经办人：睡觉小分队
任务：T-20260512-32961719 / third_party_generic_backend_green_plan execute 复审返修
任务目标：修复 review 复审指出的最小需改项：同步 `spec/dsl/gen_kernel/emit/register.md` 功能与用例清单中的 pytest 名称到当前真实测试入口；将 `kernel_gen/execute_engine/{compiler.py,__init__.py}` 文件级 API 列表中的 `CompileStrategy` 统一为 `class CompileStrategy(Protocol)`，并复跑对应 pytest、授权 expectation、静态扫描与 Diff 反推自测。
执行前阅读记录：
- 已读取个人提示词 `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、仓库根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md` 与当前 `TODO.md` 任务行。
- 已读取主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`，沿用前序架构裁定：目标 worktree 缺计划资产，本轮只读引用主仓共享计划作为合同真源，不复制、不新建、不修改 worktree 计划资产。
- 已读取本任务记录中的 review 复审结论，确认本轮只修两个点名阻断项，不扩大实现范围，不修改 `.skills`，expectation 仅限已授权 `expectation/dsl/gen_kernel/third_party_backend/**`。
同步基线：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend`。
- `HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72`。
- `origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
改动：
- `spec/dsl/gen_kernel/emit/register.md`：将功能与用例清单 `建议测试` 列从不存在的旧 pytest 名称同步为当前真实入口：
  - `test_backend_loader_imports_registered_dummy_backend`
  - `test_backend_loader_rejects_unregistered_target_without_cpu_fallback`
  - `test_backend_loader_distinguishes_missing_module`
  - `test_backend_loader_distinguishes_backend_import_failure`
  - `test_backend_loader_distinguishes_missing_module_handler`
  - `test_emit_registry_duplicate_requires_explicit_override`
  - `test_module_handler_returns_mapping_as_source_bundle`
- `kernel_gen/execute_engine/compiler.py`：文件级 API 列表中的 `class CompileStrategy()` 改为 `class CompileStrategy(Protocol)`。
- `kernel_gen/execute_engine/__init__.py`：文件级 API 列表中的 `class CompileStrategy()` 改为 `class CompileStrategy(Protocol)`。
- 未修改 `expectation/`、`.skills`、计划书或其它实现逻辑。
最小功能闭环：
- spec/test 映射现在可从 `spec/dsl/gen_kernel/emit/register.md` 机械追踪到真实 pytest 名称。
- execute_engine 包入口与 compiler 实现文件的快速 API 索引现在与真实 `class CompileStrategy(Protocol)`、`spec/execute_engine/strategy.md`、`spec/execute_engine/execute_engine.md` 和 `spec/execute_engine/execute_engine_api.md` 一致。
Diff 反推自测：
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_backend_loader.py test/dsl/gen_kernel/test_module_emitter.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py`：通过，`23 passed, 1 warning`，退出码 0。
- `PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 tests collected`，退出码 0。
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 passed, 2 warnings`，退出码 0。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend`：通过，退出码 0。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend`：通过，退出码 0。
- expectation 授权范围核对脚本：通过，仅包含 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`；无 scope 外 expectation 变更。
禁止修改面与静态扫描：
- `git diff --check && git diff --cached --check`：通过，退出码 0。
- `git diff --name-only -- expectation .skills`：无输出。
- `git diff --cached --name-only -- expectation .skills`：仅输出授权路径 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`。
- `git status --short --untracked-files=all -- .skills`：无输出。
- `rg` 旧 pytest 名称与 `class CompileStrategy()`：无命中。
- changed-python diff 扫描 `hasattr(ctx...)` / `getattr(ctx...)` / `callable(getattr(...))` / `object` 签名 / `xpu_sdnn4` / `sdnn.gen`：无命中。
- changed-python diff 的 `def` 扫描仅命中类方法或 `Protocol` 方法，不是函数体内非装饰器嵌套函数。
- changed-python diff 的私有 API 扫描仅命中当前类内 `_emit_module` / `_module_funcs` 和对象自身 `_cleanup()` 调用，不属于跨文件非公开 API 使用。
自检：
- 接口：未新增、删除、重命名或修改公开 API；仅修正文档/API 快速索引，使其与现有公开 `CompileStrategy(Protocol)` 和真实 pytest 名称一致。
- 边界与异常：本轮不改变运行时错误语义；前序 `dispatch_op_for_target`、compile request 混参和 SourceBundle 错误短语返修测试保持通过。
- 兼容性：不改变 `emit_c` / `gen_kernel` / `ExecutionEngine.compile` 签名，不扩大 `xpu_sdnn4` 或外部 third-party 验收范围。
- 实现遗漏 / 冗余 / 复用 / 函数粒度：本轮无实现逻辑变更；未引入 helper、嵌套函数或跨文件私有调用。
- 输入输出、资源、并发、性能：本轮为 spec/API 列表文本修复，无资源或并发行为变化。
- 测试有效性：targeted pytest 覆盖被修 spec/test 映射和 execute_engine API 索引相关模块；相关集合 pytest、py_compile 与授权 expectation 均通过。
结论：execute 复审返修完成，可再次流转 review。

时间：2026-05-12 03:11 +0800
经办人：睡觉小分队
任务：T-20260512-32961719 / third_party_generic_backend_green_plan
流程推进：
- 已执行 `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -next -task_id T-20260512-32961719 -from 睡觉小分队 -type review ... -auto`。
- 脚本返回：`OK: next T-20260512-32961719`、`OK: auto-dispatch T-20260512-32961719 -> 提莫炖蘑菇`、`OK: talk 睡觉小分队 -> 提莫炖蘑菇`、`OK: talk 睡觉小分队 -> 神秘人`。
结论：已流转 review 并通过脚本回报管理员。

时间：2026-05-12 03:16 +0800
经办人：提莫炖蘑菇
任务：T-20260512-32961719 / third_party_generic_backend_green_plan review 复审
任务目标：复审最小返修：核对 `spec/dsl/gen_kernel/emit/register.md` 功能与用例清单 pytest 名称已同步真实测试入口，`kernel_gen/execute_engine/{compiler.py,__init__.py}` 文件级 API 列表已统一为 `class CompileStrategy(Protocol)`，并复核对应 pytest、Diff 反推自测、授权 expectation、静态扫描与禁止修改面。
审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend`。
- 已执行 `git fetch origin`。
- `HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72`。
- `origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72`。
- `merge-base HEAD origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72`。
- 结果：待审 worktree 已在最新 `origin/main` 基线上，无需 merge/rebase；未覆盖任务 diff，未丢失本地改动。
计划与合同真源：
- 目标 worktree 未携带 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`，沿用前序架构裁定，只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`。
- 计划明确 coverage report 是记录项，不设置本计划新增阈值；本轮不以专题 coverage TOTAL `91%` 作为阻断。
- `expectation/` 授权范围仅限 `expectation/dsl/gen_kernel/third_party_backend/**`；其它 `expectation/**` 与 `.skills` 必须保持空 diff。
真实审查：
- `spec/dsl/gen_kernel/emit/register.md` 的功能与用例清单已改为当前真实 pytest 名称：`test_backend_loader_imports_registered_dummy_backend`、`test_backend_loader_rejects_unregistered_target_without_cpu_fallback`、`test_backend_loader_distinguishes_missing_module`、`test_backend_loader_distinguishes_backend_import_failure`、`test_backend_loader_distinguishes_missing_module_handler`、`test_emit_registry_duplicate_requires_explicit_override`、`test_module_handler_returns_mapping_as_source_bundle`。
- 已用脚本反查 `spec/dsl/gen_kernel/emit/register.md` 中 backtick pytest 名称均可在 `test/**/*.py` 中找到；结论为 `register spec pytest mapping ok`。
- `kernel_gen/execute_engine/compiler.py` 与 `kernel_gen/execute_engine/__init__.py` 文件级 API 列表均已统一为 `class CompileStrategy(Protocol)`，与 `kernel_gen/execute_engine/compiler.py` 真实类定义及 `spec/execute_engine/{strategy.md,execute_engine.md,execute_engine_api.md}` 一致。
- `rg` 检查旧 pytest 名称与 `class CompileStrategy()` 均无命中。
- 授权 expectation 仅包含 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`；`.skills` 无 tracked/untracked diff。
Diff 反推审查：
- 返修点直接涉及 `spec/dsl/gen_kernel/emit/register.md`、`kernel_gen/execute_engine/compiler.py`、`kernel_gen/execute_engine/__init__.py`。
- 反推 pytest 覆盖 backend loader、ModuleOp handler、CompileStrategy 与 execute_engine contract：`test/dsl/gen_kernel/test_backend_loader.py`、`test/dsl/gen_kernel/test_module_emitter.py`、`test/execute_engine/test_compile_strategy.py`、`test/execute_engine/test_contract.py`。
- 扩展反推集合覆盖计划涉及的 `test/dsl/gen_kernel`、`test/execute_engine`、`test/target`，同时执行 collect-only、py_compile、diff check、授权 expectation、manifest/hash scope gate 与静态扫描。
验证：
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_backend_loader.py test/dsl/gen_kernel/test_module_emitter.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py`：通过，`23 passed, 1 warning`，退出码 0。
- `PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 tests collected`，退出码 0。
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 passed, 2 warnings`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend`：通过，退出码 0；该 expectation 仅作为授权合同验收单列，不计入 Diff 反推测试。
- `coverage erase && PYTHONPATH=. coverage run --branch --source=kernel_gen.dsl.gen_kernel,kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/dsl/gen_kernel test/execute_engine test/target && coverage json -o /tmp/third_party_generic_backend_coverage.json && coverage report --include='kernel_gen/dsl/gen_kernel/*,kernel_gen/execute_engine/*,kernel_gen/target/*'`：通过，`266 passed, 2 warnings`；coverage JSON 写入 `/tmp/third_party_generic_backend_coverage.json`；专题 coverage TOTAL `91%`，退出码 0。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend`：通过，退出码 0。
- `git diff --check && git diff --cached --check`：通过，退出码 0。
- `git diff --quiet -- .skills` 与 `git status --short --untracked-files=all -- .skills`：通过，`.skills` 空 diff。
- expectation manifest/hash scope gate：通过，仅授权目录 `expectation/dsl/gen_kernel/third_party_backend/**` 存在变更；scope 外 tracked/untracked/ignored expectation 均为空。
静态扫描：
- `hasattr(ctx, ...)`、`getattr(ctx, ...)`、`callable(getattr(...))` 能力探测：无命中。
- `object` 签名：无命中。
- `xpu_sdnn4`、`sdnn.gen`、`from sdnn`、`import sdnn`：无命中。
- `collect_ignore`、`pytest_ignore_collect`、`skip(`、`xfail`、coverage 配置变更：未发现本轮新增隐藏测试或降阈值改动。
- 非装饰器嵌套函数扫描：仅命中类方法与装饰器工厂闭包，不存在新增非法函数体内嵌套 `def`。
可改进点：
- 未发现当前最小返修范围内仍需退回 execute 的可执行问题。
自检：
- 已按实际 diff 做真实审查与 Diff 反推审查；未修改业务代码、spec、测试、计划书、expectation 或 `.skills`，仅追加任务记录。
- 返修点与公开 API/spec/test 索引一致；授权 expectation、pytest、collect-only、py_compile、diff check、静态扫描与禁止修改面均已核对。
结论：通过。该任务为计划级任务，review 通过后应由管理员接入架构复核 / 终验流程，不进入 merge。

时间：2026-05-12 03:21 +0800
经办人：大闸蟹
任务：T-20260512-32961719 / third_party_generic_backend_green_plan 架构复核 / 终验
复核目标：按计划级任务终验要求，在最新同步现场复核主仓共享计划 only、授权 expectation 范围、`.skills` 空 diff、Diff 反推审查、静态扫描，以及 review 点名的 `spec/dsl/gen_kernel/emit/register.md` pytest 名称一致性和 `kernel_gen/execute_engine/{compiler.py,__init__.py}` API 列表一致性。
同步与合同真源：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend`。
- 已执行 `git fetch origin --prune`。
- 验证基线：`HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72`，`origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72`，`merge-base=82dd3b696e01142f1a90e2cc4675398322c71b72`，`HEAD...origin/main=0 0`；无需 merge，未覆盖任务 diff。
- 待验 worktree 仍缺 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`；沿用前序架构裁定，只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md` 作为合同真源；本轮未复制、未新建、未修改 worktree 计划资产。
重点复核：
- `spec/dsl/gen_kernel/emit/register.md` 中列出的 pytest 名称均可在 `test/**/*.py` 中反查到真实测试函数；`register spec pytest mapping ok`。
- `kernel_gen/execute_engine/compiler.py` 与 `kernel_gen/execute_engine/__init__.py` 文件级 API 列表均为 `class CompileStrategy(Protocol)`，并与 `spec/execute_engine/strategy.md`、`spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md` 和真实类定义一致；未发现旧 `class CompileStrategy()` 命中。
- 授权 expectation 范围仅为 `expectation/dsl/gen_kernel/third_party_backend/**`；当前 tracked/staged expectation 仅包含 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`。manifest/hash gate 也只发现该授权前缀内文件和本次运行生成的 ignored `__pycache__`，无 scope 外 expectation 变更。
- `.skills` tracked diff、staged diff 与 untracked 文件均为空。
验收命令摘要：
- `PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 tests collected`。
- `PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend`：通过，退出码 0。
- `coverage erase && PYTHONPATH=. coverage run --branch --source=kernel_gen.dsl.gen_kernel,kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/dsl/gen_kernel test/execute_engine test/target && coverage json -o /tmp/third_party_generic_backend_coverage.json && coverage report --include='kernel_gen/dsl/gen_kernel/*,kernel_gen/execute_engine/*,kernel_gen/target/*'`：通过，`266 passed, 2 warnings`，专题 coverage `TOTAL 91%`，与计划记录项一致。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend`：通过。
- `git diff --check`、`git diff --cached --check`：通过。
- expectation scope gate：通过，仅授权路径有新增；`.skills` 空 diff gate：通过。
静态与边界扫描：
- `hasattr(ctx, ...)`、`getattr(ctx, ...)`、`callable(getattr(...))` 能力探测扫描无命中。
- `xpu_sdnn4`、`sdnn.gen`、`from sdnn`、`import sdnn` 在本计划主链扫描无命中。
- changed Python AST 扫描未发现非法非装饰器嵌套函数；命中范围内未发现新增 `object` 公开签名或跨文件非公开 API 使用。
- `collect_ignore`、`pytest_ignore_collect`、`skip(`、`xfail`、coverage 配置变更未发现本轮新增隐藏测试或降阈值行为。
Diff 反推复核：
- review 已按实际 diff 覆盖 backend loader、ModuleOp handler、SourceProduct/SourceBundle、compile strategy、execute_engine/target 回归与授权 expectation；本轮终验复跑了对应公开 pytest、collect-only、coverage、py_compile、diff check、expectation 与静态扫描。
- 前两轮 review 指出的 target registry fallback、compile request 混参、spec 文档信息、SourceBundle 错误短语、pytest 名称映射与 `CompileStrategy(Protocol)` API 列表问题均已在当前现场闭合。
最小阻断项：无。
结论：通过，可进入后续 merge/归档流程；merge 前仍需按合并规范确认最终 diff 和禁止修改面。

时间：2026-05-12 03:23 +0800
经办人：守护最好的爱莉希雅
任务：T-20260512-32961719 / third_party_generic_backend_green_plan 第二架构复核 / 终验
复核目标：按计划级任务终验要求，在最新同步现场复核主仓共享计划 only、公开 pytest、授权 expectation、expectation scope、`.skills` 空 diff、Diff 反推审查、静态扫描，以及 review 点名的 `spec/dsl/gen_kernel/emit/register.md` pytest 名称一致性和 `kernel_gen/execute_engine/{compiler.py,__init__.py}` API 列表一致性。
同步与合同真源：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend`。
- 已执行 `git fetch --prune origin`。
- 验证基线：`HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72`，`origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72`。
- 待验 worktree 已在最新 `origin/main` 基线上，无需 merge/rebase；未覆盖任务 diff。
- 待验 worktree 缺 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`；按前序架构裁定只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md` 作为合同真源；本轮未复制、未新建、未修改计划资产。
重点复核：
- `spec/dsl/gen_kernel/emit/register.md` 中列出的 pytest 名称已与真实测试函数一致：`test_backend_loader_imports_registered_dummy_backend`、`test_backend_loader_rejects_unregistered_target_without_cpu_fallback`、`test_backend_loader_distinguishes_missing_module`、`test_backend_loader_distinguishes_backend_import_failure`、`test_backend_loader_distinguishes_missing_module_handler`、`test_emit_registry_duplicate_requires_explicit_override`、`test_module_handler_returns_mapping_as_source_bundle` 均可在 `test/dsl/gen_kernel/**` 中反查。
- 旧 pytest 名称扫描无命中。
- `kernel_gen/execute_engine/compiler.py` 与 `kernel_gen/execute_engine/__init__.py` 文件级 API 列表均为 `class CompileStrategy(Protocol)`；`spec/execute_engine/**` 与真实类定义一致，旧 `class CompileStrategy()` 扫描无命中。
- 授权 expectation 范围仅为 `expectation/dsl/gen_kernel/third_party_backend/**`；当前 tracked/staged expectation 仅包含 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`。
- expectation manifest/hash scope gate 通过，scope 外无 tracked/staged/untracked 变更；本轮运行产生的 ignored `__pycache__` 不作为合同变更。
- `.skills` tracked diff、staged diff 与 untracked 文件均为空。
验收命令摘要：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_backend_loader.py test/dsl/gen_kernel/test_module_emitter.py test/dsl/gen_kernel/test_source_bundle.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py`：通过，`27 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 tests collected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend`：通过，退出码 0。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend`：通过，退出码 0。
- `git diff --check` 与 `git diff --cached --check`：通过。
- `coverage erase && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen.dsl.gen_kernel,kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/dsl/gen_kernel test/execute_engine test/target && coverage json -o /tmp/third_party_generic_backend_arch2_coverage.json && coverage report --include='kernel_gen/dsl/gen_kernel/*,kernel_gen/execute_engine/*,kernel_gen/target/*'`：通过，`266 passed, 2 warnings`，专题 coverage `TOTAL 91%`；该 coverage 为计划记录项，不是新增阈值门禁。
静态与边界扫描：
- `hasattr(ctx, ...)`、`getattr(ctx, ...)`、`callable(getattr(...))` 能力探测扫描无命中。
- `xpu_sdnn4`、`sdnn.gen`、`from sdnn`、`import sdnn` 扫描无命中。
- changed Python AST 扫描未发现非法非装饰器嵌套函数；仅允许装饰器工厂闭包。
- diff 扫描未发现新增 `object` 公开签名、隐藏测试、`skip` / `xfail`、coverage 配置规避或越权使用第三方 backend 公开面。
Diff 反推复核：
- 本轮复跑覆盖 backend loader、ModuleOp handler、SourceProduct/SourceBundle、compile strategy、execute_engine contract、target registry、授权 expectation、compileall、diff check、expectation scope gate、`.skills` gate 与静态扫描。
- review 已闭合的 target registry fallback、compile request 混参、spec 文档信息、SourceBundle 错误短语、pytest 名称映射与 `CompileStrategy(Protocol)` API 列表问题，在当前同步现场未复现阻断。
自检：
- 本轮只追加任务记录；未修改实现、spec、测试、计划书、expectation 或 `.skills`。
- 已按实际 diff 做计划级终验和 Diff 反推复核。
最小阻断项：无。
结论：通过。T-20260512-32961719 已具备进入后续 merge/归档流程的架构终验条件；merge 前仍需按合并规范确认最终 diff、禁止修改面与授权 expectation scope。

时间：2026-05-12 03:28 +0800
经办人：李白
任务：T-20260512-32961719 / third_party_generic_backend_green_plan
任务目标：merge 前收口复核并准备合入 third-party generic backend 计划任务；确认 latest 同步、任务记录、主仓共享计划只读口径、授权 expectation scope、`.skills` 空 diff、公开 pytest、coverage、compileall、静态扫描和禁止修改面。

merge 前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260512-third-party-generic-backend`。
- 已执行 `git fetch --prune origin`。
- worktree 分支：`task/third-party-generic-backend`。
- `HEAD=82dd3b696e01142f1a90e2cc4675398322c71b72`。
- `origin/main=82dd3b696e01142f1a90e2cc4675398322c71b72`。
- `git rev-list --left-right --count HEAD...origin/main` 输出 `0 0`，无需 merge/rebase；未覆盖任务 diff。
- 主仓根目录 `/home/lfr/kernelcode_generate` 存在与本任务无关的未提交改动：`.gitignore`、`kernel_gen/dialect/symbol.py`、`kernel_gen/dsl/ast/nodes/symbol.py`；本次合并不触碰、不暂存、不覆盖这些改动，后续通过任务 worktree 提交并快进推送远端 `main`。

合同真源与记录核对：
- 已读取本任务记录中 execute、review、两轮返修、复审和双架构终验记录；最终 review 通过，两位架构终验均通过，最小阻断项无。
- 待合并 worktree 缺 `ARCHITECTURE/plan/third_party_generic_backend_green_plan.md`；按守护最好的爱莉希雅与大闸蟹前序裁定，本轮只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/third_party_generic_backend_green_plan.md` 作为合同真源；本次未复制、未新建、未修改计划资产。
- 已核对计划授权 expectation scope 仅为 `expectation/dsl/gen_kernel/third_party_backend/**`；`.skills/**` 禁止修改。
- 当前待合入 diff 覆盖 `kernel_gen/dsl/gen_kernel/**`、`kernel_gen/execute_engine/**`、相关 `spec/dsl/gen_kernel/**`、`spec/execute_engine/**`、`spec/target/registry.md`、`test/dsl/gen_kernel/**`、`test/execute_engine/**`、授权 expectation 新增文件和本任务记录。

授权 expectation 与禁止修改面：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.third_party_backend`：退出码 0。
- `git diff --name-only -- .skills`、`git diff --cached --name-only -- .skills`、`git status --short --untracked-files=all -- .skills`：均无输出。
- `git diff --name-only -- expectation`：无输出。
- `git diff --cached --name-only -- expectation`：仅输出 `expectation/dsl/gen_kernel/third_party_backend/__main__.py` 与 `expectation/dsl/gen_kernel/third_party_backend/basic.py`。
- `git status --short --untracked-files=all -- expectation`：仅显示上述两个授权新增文件。
- expectation scope gate：通过；无授权 scope 外 tracked、staged 或 untracked expectation 变更。`__pycache__` 仅位于授权目录内且为 ignored 运行产物，不作为合同变更。

merge 前 gate：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 tests collected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel test/execute_engine test/target`：通过，`266 passed, 2 warnings`。
- `coverage erase && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. coverage run --branch --source=kernel_gen.dsl.gen_kernel,kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/dsl/gen_kernel test/execute_engine test/target && coverage json -o /tmp/third_party_generic_backend_merge_coverage.json && coverage report --include='kernel_gen/dsl/gen_kernel/*,kernel_gen/execute_engine/*,kernel_gen/target/*'`：通过，`266 passed, 2 warnings`，coverage TOTAL `91%`。
- `PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_pycache PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/dsl/gen_kernel kernel_gen/execute_engine kernel_gen/target test/dsl/gen_kernel test/execute_engine test/target expectation/dsl/gen_kernel/third_party_backend`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_backend_loader.py test/dsl/gen_kernel/test_module_emitter.py test/dsl/gen_kernel/test_source_bundle.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py`：通过，`27 passed, 1 warning`。
- `git diff --check` 与 `git diff --cached --check`：均通过。

静态扫描：
- target 分支扫描命中既有 CPU / npu_demo 主链和 `emit_context.py` 文档示例；未命中 `dummy_generic` 主链特判。
- `rg -n 'xpu_sdnn4|dummy_generic' kernel_gen/dsl/gen_kernel/emit/__init__.py kernel_gen/dsl/gen_kernel/kernel_emitter.py kernel_gen/dsl/gen_kernel/gen_kernel.py kernel_gen/execute_engine/compiler.py`：无输出。
- `rg -n 'sdnn\.gen|from sdnn|import sdnn' kernel_gen test`：无输出。
- 隐藏测试 / coverage 配置扫描未发现本轮新增 `collect_ignore`、`pytest_ignore_collect`、`skip`、`xfail` 或 coverage 配置改动；命中为仓库既有测试或文档，不属本轮改动。
- `rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr' kernel_gen/dsl/gen_kernel kernel_gen/execute_engine test/dsl/gen_kernel test/execute_engine`：无输出。
- 私有 API 测试扫描命中既有 `_legacy` 字符串和 `test/execute_engine/test_invoke.py` 假对象字段；非本轮新增跨文件非公开 API 直连。
- AST 扫描当前 diff / staged / untracked Python 文件：无 `object` 注解；嵌套函数命中仅为 `emit/register.py` 中装饰器工厂闭包 `decorator`，符合规则例外。

merge 结论：
- 合并前 gate 通过；任务记录、授权来源、终验结论、diff scope 与禁止修改面已核对。
- 可暂存本任务允许文件和记录文件，生成任务分支提交并推送到 `origin/main`。
