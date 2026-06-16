# cuda_sm89_include_npu_demo_structure_matmul.md

## 文档信息

- 状态：Draft 6 已按用户口径修正 `expectation/` 边界并补齐小任务示例 / 预期，守护复验已通过，用户已最终确认下发；当前可通知管理员创建唯一计划级 execute。
- 用户原始诉求：`新计划，将 sm86改为sm89.然后让include 的结构跟 npudomo 一致！ 跑通matmul。`
- 用户流程要求：`按照计划书流程，先讨论，我决策。如有必要完善添加expatation，经过我确认再下发。`
- 目标 `spec`：
  - 已确认：将当前 `spec/include/cuda_sm86/cuda_sm86.md` 正式迁移为 `spec/include/cuda_sm89/cuda_sm89.md`。
  - 已确认：将当前 `spec/dsl/gen_kernel/emit/cuda_sm86.md` 正式迁移为 `spec/dsl/gen_kernel/emit/cuda_sm89.md`。
  - 已确认：将当前 `spec/pass/pipeline/cuda_sm86_lowering.md` 正式迁移为 `spec/pass/pipeline/cuda_sm89_lowering.md`。
  - 已确认：补齐 / 更新 `spec/pass/registry.md` 的内置 pipeline 注册口径，使其显式包含 `cuda-sm89-lowering`；这是既有 pass registry 公开 API 的内置 pipeline 合同补齐，不新增 registry API。
  - 已确认：更新 `spec/pass/tuning/dma_memory_hierarchy.md` 的 CUDA C5 文案，从 CUDA SM86 C5 调用侧迁移为 CUDA SM89 C5 调用侧；这是既有 `lower-dma-memory-hierarchy` pass 文案 / 调用侧说明迁移，不新增 pass option。
  - 已确认：更新 `spec/execute_engine/execute_engine_target.md` 的内置 target 合同。
  - 已确认：更新 `spec/target/registry.md` 的目录 target 真源合同；这是公开 API 合同迁移。
  - 已确认：更新 `spec/dsl/gen_kernel/emit.md` 的通用 emit target 合同；这是公开 API 合同迁移。
  - 已确认：更新 `spec/execute_engine/strategy.md`、`spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md` 中的内置 target / strategy / target 文案；其中 target 集合与失败语义属于公开合同迁移，文件路径说明属于文案迁移。
  - 已确认：更新 `spec/script/pytest_config.md` 中 `cuda` mark 对 SM89 runtime 的说明；这是测试配置文案迁移，不新增 CLI 参数或 pytest mark。
- 目标 `API`：
  - 已确认：`target="cuda_sm89"`、`namespace cuda_sm89`、`include/cuda_sm89/cuda_sm89.cuh`、`cuda-sm89-lowering`、`build_cuda_sm89_lowering_pipeline(...)` 成为新的公开入口。
  - 已确认：既有 pass registry 公开 API `load_builtin_passes()`、`list_registered_pipelines()`、`build_registered_pipeline(...)` 必须暴露 / 构造 `cuda-sm89-lowering`，旧 `cuda-sm86-lowering` 不再作为 active 成功 registry 入口。
  - 已确认：旧 `cuda_sm86` target / namespace / include / pipeline / builder 不再作为成功入口；active spec / implementation / test 不保留旧成功路径。
- 目标 `test`：
  - 已确认：新增 / 重命名 CUDA SM89 相关测试文件，至少覆盖 execute_engine strategy、target registry、pipeline、emit SourceBundle、include structure、matmul runtime。
  - 已确认：同步更新通用合同测试：`test/execute_engine/test_contract.py`、`test/execute_engine/test_compile_strategy.py`、`test/execute_engine/test_builtin_strategy.py`、`test/target/test_registry.py`、`test/dsl/gen_kernel/emit/test_package.py`、`test/script/test_pytest_config.py` 或仓库现有等价 pytest config 测试。
  - 已确认：同步更新 pass registry 测试 `test/passes/test_registry.py`，覆盖 `load_builtin_passes()` 后 `cuda-sm89-lowering` 可见、可构造，旧 `cuda-sm86-lowering` 不再作为 active 成功 registry 入口。
  - 已确认：同步运行 / 更新 `test/passes/tuning/test_dma_memory_hierarchy.py` 的 C5 all-TLM1 覆盖，证明 `lower-dma-memory-hierarchy` 公开规则仍支持 SM89 C5 所需 `matmul{["tlm1", "tlm1", "tlm1"]}`。
  - 已确认：同步迁移 API-aligned SourceBundle 测试为 `test/dsl/gen_kernel/emit/test_cuda_sm89_api_aligned_codegen.py`，覆盖 hash entry、slot ABI、wrapper calls、dynamic symbol/control-flow 与 compile-only 生成形态。
  - 已确认：同步迁移 repo conformance 私有 API 边界测试 `test/repo_conformance/test_private_api_boundaries.py` 中 CUDA source builder / exact method set 的 SM89 口径。
- 目标 `验收资产`：
  - pytest / 脚本验收：见本文 `验收设计`。
  - 当前必过 `expectation` 合同验收：无。`expectation/` 检查与必要裁定属于架构师侧职责，当前架构侧只读扫描未发现 CUDA SM86 / SM89 专属 expectation 源码命中，不纳入计划内 execute 小任务。
- 目标 `功能实现`：
  - `include/cuda_sm89/`。
  - `kernel_gen/dsl/gen_kernel/emit/cuda_sm89/`。
  - `kernel_gen/execute_engine/builtin_strategy/cuda_sm89.py`。
  - `kernel_gen/pipeline/cuda_sm89_lowering.py`。
  - `kernel_gen/passes/registry.py`。
  - `kernel_gen/target/targets/cuda_sm89.txt`。

## 计划级任务

- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`。
- 当前 Draft 6 已按用户口径将 `expectation/` 检查与必要裁定移出计划内 execute 小任务，并补齐各小任务示例 / 预期；守护复验已通过，用户已最终确认下发，可生成 execute 任务。
- 计划归档目标：`agents/codex-multi-agents/log/task_records/done_plan/2026/25/cuda_sm89_include_npu_demo_structure_matmul.md`。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `cuda-sm89-include-npu-demo-structure-matmul` | `execute` | 待管理员创建 | `agents/codex-multi-agents/log/task_records/2026/25/20260615-cuda-sm89-include-npu-demo-structure-matmul.md` |

## 迭代审阅记录

### Draft 0：主线事实核对与讨论项

- 审阅对象：大闸蟹主线自查；尚未发起 subagent strict review。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、当前仓库 CUDA / include / npu_demo / matmul 相关文件。
- 严格通过口径：本 Draft 0 不求通过；只列出必须由用户确认的公开 API、include 结构、runtime 范围和 expectation 授权。
- 当前状态：等待用户决策。

### Draft 1：用户决策收口与 expectation 只读扫描

- 审阅对象：大闸蟹主线修订；尚未发起 subagent strict review。
- 输入标准包：Draft 0 全文、用户确认消息、`agents/standard/expectation任务规则.md`、`expectation/` 只读扫描结果。
- 用户确认：
  - C1=A：完整切到 `cuda_sm89`，包括 target。
  - C2=B：include 按功能分层对齐 `npu_demo`，不制造未实现的 cost / Trance 公开 API。
  - C3=A：runtime 必过范围只锁 matmul。
  - C4=条件授权：检查 `expectation/`，如存在 SM86 口径且属于本计划合同面，则允许按最小范围修改；当前扫描无 CUDA SM86 / SM89 专属 expectation 源码命中。
- expectation 只读扫描：
  - `rg -uuu -n -i "cuda[_-]?sm86|cuda[_-]?sm_86|sm86|sm_86|compute_86|arch=sm_86|cuda-sm86" expectation --glob '!**/__pycache__/**' --glob '!*.pyc'`：无输出。
  - `rg -uuu -n -i "cuda[_-]?sm89|cuda[_-]?sm_89|sm89|sm_89|compute_89|arch=sm_89|cuda-sm89" expectation --glob '!**/__pycache__/**' --glob '!*.pyc'`：无输出。
  - `find expectation -path '*/__pycache__' -prune -o -type f -print | sort | wc -l`：`519`。
- 严格通过口径：已无用户待确认项；仍需至少两轮 subagent strict review 和守护最终检验。
- 当时状态：待发起 subagent strict review；已进入 Round 1 并在 Draft 2 主线处理。

### Round 1：Codex subagent strict review（不通过，Draft 2 修订中）

- 人选确认来源：2026-06-15 管理员 `神秘人` 回执；本轮只使用两个独立 Codex subagent 会话，不使用 agents-list 常驻 tmux 角色会话。
- Round 1-A：Codex subagent A。
  - 分工：流程 / API / 范围审阅。
  - 重点：用户 C1-C4 决策来源、`cuda_sm86 -> cuda_sm89` 包 / target / 公开 API 影响面、include `Core / Memory / Dma / Kernel / Arch` 分层边界、任务卡可执行性、禁止混入其它 staged independent 计划与 expectation 权限。
- Round 1-B：Codex subagent B。
  - 分工：技术 / 验收 / 回归审阅。
  - 重点：matmul-only runtime 完成态、`npu_demo` include 结构与现有 spec / API 列表一致性、SM89 runtime 与文本门禁设计、Diff 反推 pytest 覆盖、SM86 残留扫描和 C4 条件授权 expectation 检查边界。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、计划全文与 staged 证据、用户 C1-C4 确认、全量 cached diff 中 unrelated 计划排除说明、禁止修改面、expectation 条件授权口径和必过验收命令。
- 严格通过口径：仍有阻断项、最小需改项、待确认项、可执行的 API / expectation / 验收 / 任务卡改进项则不通过；不得以“后续 execute 自行判断”放行计划边界不清。
- Round 1-A 回执：结论不通过。
  - 阻断项：公开 API 设计未闭合 include exact signatures；S2 未写死 `cuda_sm89.cuh` exact include 集合和顺序；验收设计缺 include structure pytest 命令且静态门禁未覆盖新增 include 测试路径。
  - 主线处理：Draft 2 补齐 `cuda_sm89` include API exact signatures、aggregate include 精确顺序、不聚合 Trance / cost 的依赖边界、`test/include/cuda_sm89/test_public_namespace.py` include structure 命令和静态门禁覆盖。
  - 状态：需修订，已纳入 Draft 2 最小修订。
- Round 1-B 回执：结论不通过。
  - 阻断项：目标 spec 范围漏掉 `spec/target/registry.md`、`spec/dsl/gen_kernel/emit.md`、`spec/execute_engine/strategy.md`、`spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md`、`spec/script/pytest_config.md`；公开 API 列表仍是压缩写法；最低 pytest 漏掉通用合同测试和 include 拆分测试。
  - 主线处理：Draft 2 将上述 spec 纳入目标范围和 S1-S3，标明公开合同迁移 / 文案迁移；补齐 exact API；补入 `test/execute_engine/test_contract.py`、`test/execute_engine/test_compile_strategy.py`、`test/execute_engine/test_builtin_strategy.py`、`test/target/test_registry.py`、`test/dsl/gen_kernel/emit/test_package.py`、`test/script/test_pytest_config.py` 与 include structure 测试命令。
  - 状态：需修订，已纳入 Draft 2 最小修订。
- 当时状态：Round 1 不通过项已在 Draft 2 主线处理；Round 2 已完成且不通过，Draft 3 已处理最小阻断项；待 Round 3 strict review，不得请求守护最终检验。

### Draft 2：Round 1 主线处理

- 修订对象：Round 1-A / Round 1-B 最小需改项。
- 主线修订：
  - 目标 spec 范围补入 `spec/target/registry.md`、`spec/dsl/gen_kernel/emit.md`、`spec/execute_engine/strategy.md`、`spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md`、`spec/script/pytest_config.md`，并区分公开合同迁移与文案迁移。
  - 公开 API 设计补齐 `cuda_sm89` include API exact signatures，按现有 `cuda_sm86` 签名纯迁移，不改变模板参数顺序、返回值、默认值或 `__device__` / `__host__` 限定；任一签名变化必须回用户确认。
  - C2 / S2 补齐 `cuda_sm89.cuh` exact include 顺序，明确不聚合 Trance / cost 及对应 `include/api` 头。
  - 验收设计补入 `test/include/cuda_sm89/test_public_namespace.py`、通用 execute_engine / target / emit package / pytest config 测试，扩展 SM86 / SM89 静态文本门禁范围。
  - runtime 验收补充 `-k matmul` 必须真实执行通过；环境缺失 skip 只能记录阻塞，不能记作 runtime 通过。
- 当时状态：待发起 Round 2 strict review；Round 2 已完成且不通过，见下文 Draft 3 主线处理。

### Round 2：Codex subagent strict review（不通过，Draft 3 修订中）

- 人选与会话来源：基于 Draft 2 staged 候选继续使用两个独立 Codex subagent 会话，不使用 agents-list 常驻 tmux 角色会话。
- Round 2-A：Codex subagent A（会话 nickname：Anscombe）。
  - 分工：流程 / API / 范围审阅。
  - 重点：Round 1 阻断是否被 Draft 2 正确修复、用户 C1-C4 决策来源是否仍闭合、公开 API / 稳定错误语义是否完整、expectation 条件授权是否未扩大。
- Round 2-B：Codex subagent B（会话 nickname：Kuhn）。
  - 分工：技术 / 验收 / 回归审阅。
  - 重点：SM89 SourceBundle / include / runtime matmul 验收是否覆盖实际迁移面、SM86 残留扫描是否覆盖 active 测试、diff 反推 pytest 是否足以证明旧成功路径退场。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、Draft 2 全文与 staged 证据、Round 1 问题和 Draft 2 收口摘要、用户 C1-C4 确认、全量 cached diff 中 unrelated 计划排除说明、禁止修改面、expectation 条件授权口径和必过验收命令。
- 严格通过口径：仍有阻断项、最小需改项、待确认项、可执行的 API / expectation / 验收 / 任务卡改进项则不通过；不得以“execute 自行补测试”放行计划验收缺口。
- Round 2-A 回执：结论不通过。
  - 阻断项 1：active `test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py` 锁定 SourceBundle hash entry、slot ABI、wrapper calls、dynamic symbol/control-flow 和 dynamic conv2d compile-only；Draft 2 未要求迁移 / 新增等价 `test_cuda_sm89_api_aligned_codegen.py`。
  - 阻断项 2：`spec/pass/pipeline/cuda_sm86_lowering.md` 与 `test/passes/pipeline/test_cuda_sm86_lowering.py` 锁定 public builder 失败文本 `target must be cuda_sm86` 和 `only accepts target option`；Draft 2 未写明 `build_cuda_sm89_lowering_pipeline(...)` 的 SM89 错误语义迁移。
  - 主线处理：Draft 3 补入 `test/dsl/gen_kernel/emit/test_cuda_sm89_api_aligned_codegen.py` 到目标 test、S3 和验收命令；补入 pipeline builder 稳定错误语义 `target must be cuda_sm89` 与 `only accepts target option`，并要求 `test/passes/pipeline/test_cuda_sm89_lowering.py` 锁定。
  - 状态：需修订，已纳入 Draft 3 最小修订。
- Round 2-B 回执：结论不通过。
  - 阻断项 1：Draft 2 未显式覆盖 `test/dsl/gen_kernel/emit/test_cuda_sm89_api_aligned_codegen.py` 或等价目标测试，无法证明 active API-aligned SourceBundle 迁移完整。
  - 阻断项 2：Draft 2 未把 `test/repo_conformance/test_private_api_boundaries.py` 纳入验收；该文件当前包含 CUDA SM86 source builder package-local / exact public method set 静态门禁，是本计划迁移后防止私有 API 越界与旧包残留的重要测试。
  - 主线处理：Draft 3 将 `test/repo_conformance/test_private_api_boundaries.py -k "cuda_sm89 or source_builder"` 纳入验收和 S3 任务；静态文本门禁范围扩到 `test` 根，明确 active conformance 测试也必须迁移到 SM89。
  - 状态：需修订，已纳入 Draft 3 最小修订。
- 当时状态：Round 2 不通过项已在 Draft 3 主线处理；待 Round 3 strict review，不得请求守护最终检验。

### Draft 3：Round 2 主线处理

- 修订对象：Round 2-A / Round 2-B 最小需改项。
- 主线修订：
  - 将 `test/dsl/gen_kernel/emit/test_cuda_sm89_api_aligned_codegen.py` 列为目标 test、S3 验收和必过 pytest，要求迁移当前 `test_cuda_sm86_api_aligned_codegen.py` 覆盖的 SourceBundle hash entry、slot ABI、wrapper calls、dynamic symbol/control-flow、dynamic conv2d compile-only 等 API-aligned 生成形态；该项不扩大 C3 runtime 必过范围，conv2d / flash_attention 仍不是 runtime 必过项。
  - 将 `test/repo_conformance/test_private_api_boundaries.py` 列为目标 test 与必过 pytest，要求 CUDA source builder package-local、root `__all__`、public method exact set 与 `spec/dsl/gen_kernel/emit/cuda_sm89.md` 同步，旧 `cuda_sm86` conformance 成功路径退场。
  - 补齐 `build_cuda_sm89_lowering_pipeline(...)` 稳定错误语义：非法 target 必须抛 `KernelCodeError` 且文本包含 `target must be cuda_sm89`；未知 option 必须抛 `KernelCodeError` 且文本包含 `only accepts target option`。
  - 静态文本门禁范围扩到 `spec include kernel_gen test`，防止 active repo conformance / generic tests 漏迁旧 SM86 成功路径。
- 当时状态：待发起 Round 3 strict review；Round 3 已完成，Round 3-A 不通过、Round 3-B 通过，见下文 Draft 4 主线处理。

### Round 3：Codex subagent strict review（A 不通过，B 通过，Draft 4 修订中）

- 人选与会话来源：基于 Draft 3 staged 候选继续使用两个独立 Codex subagent 会话，不使用 agents-list 常驻 tmux 角色会话。
- Round 3-A：Codex subagent A（会话 nickname：Avicenna）。
  - 分工：流程 / API / 范围审阅。
  - 重点：用户 C1-C4 决策来源、公开 API 迁移面、include 分层边界、任务卡可执行性、禁止混入其它 staged independent 计划与 expectation 权限。
  - 回执：结论不通过。
  - 阻断项 1：Draft 3 只把 `cuda-sm89-lowering` 作为 pipeline 公开入口列入，但未显式闭合 pass registry 公开面；既有 `load_builtin_passes()`、`list_registered_pipelines()`、`build_registered_pipeline(...)` 属于公开 API，当前内置 pipeline 注册真源在 `kernel_gen/passes/registry.py`。
  - 阻断项 2：计划书结构缺少明确归档目标和 `计划书入档验收 / 复验 / 修复复核记录` 占位；不满足计划书标准对 done_plan 归档目标的要求。
  - 主线处理：Draft 4 补入 `spec/pass/registry.md`、`kernel_gen/passes/registry.py`、`test/passes/test_registry.py` 到目标范围、S1、验收命令和公开 API 说明；补入计划归档目标与入档验收占位。
  - 状态：需修订，已纳入 Draft 4 最小修订。
- Round 3-B：Codex subagent B（会话 nickname：Meitner）。
  - 分工：技术 / 验收 / 回归审阅。
  - 回执：结论通过；阻断项、最小需改项、待确认项均无。
  - 通过摘要：API-aligned 测试、repo conformance 命令、SM86 静态扫描、matmul-only runtime 口径和 C4 expectation 边界均已闭合。
  - 状态：通过；若 Draft 4 仅修改 Round 3-A 指出的流程 / registry / 归档项，后续需基于 Draft 4 再做 strict review 确认未引入新问题。
- 当时状态：Round 3-A 不通过项已在 Draft 4 主线处理；待 Round 4 strict review，不得请求守护最终检验。

### Draft 4：Round 3-A 主线处理

- 修订对象：Round 3-A 最小需改项。
- 主线修订：
  - 将 pass registry 公开面纳入本计划：`spec/pass/registry.md` 补齐 / 更新 `cuda-sm89-lowering` 内置 pipeline 公开合同，`kernel_gen/passes/registry.py` 与 `test/passes/test_registry.py` 必须从 `cuda-sm86-lowering` 内置 pipeline 注册口径迁移到 `cuda-sm89-lowering`。
  - 明确既有 pass registry API 不新增、不改签名；只迁移内置 pipeline 名称与可构造目标，`load_builtin_passes()` 后 `list_registered_pipelines()` 必须包含 `cuda-sm89-lowering`，`build_registered_pipeline("cuda-sm89-lowering", {"target": "cuda_sm89"})` 必须返回 `PassManager(name="cuda-sm89-lowering")`。
  - 明确旧 `cuda-sm86-lowering` 不再作为 active 成功 registry 入口；若存在命中，只能作为历史 / 迁移记录 / 明确负向测试。
  - 补入计划归档目标和 `计划书入档验收 / 复验 / 修复复核记录` 占位，保持 `execute -> review -> archive_acceptance -> merge/归档` 流程可追踪。
- 当时状态：待发起 Round 4 strict review；Round 4 已完成且不通过，见下文 Draft 5 主线处理。

### Round 4：Codex subagent strict review（不通过，Draft 5 修订中）

- 人选与会话来源：基于 Draft 4 staged 候选继续使用两个独立 Codex subagent 会话，不使用 agents-list 常驻 tmux 角色会话。
- Round 4-A：Codex subagent A（会话 nickname：Huygens）。
  - 分工：流程 / API / 范围审阅。
  - 回执：结论不通过；无新增阻断项，有 1 个最小需改项。
  - 最小需改项：Draft 4 对 `spec/pass/registry.md` 当前基线表述不准确；当前 `spec/pass/registry.md` 无 `cuda-sm86-lowering` 命中，只写 `default-lowering` 与 `npu-demo-lowering`。计划应改为“补齐 / 更新 registry spec 的内置 pipeline 公开合同，使其显式包含 `cuda-sm89-lowering`，并声明旧 `cuda-sm86-lowering` 不作为 active 成功入口”；`kernel_gen/passes/registry.py` 与 `test/passes/test_registry.py` 仍按当前实际 SM86 注册入口迁移。
  - 主线处理：Draft 5 修正 `spec/pass/registry.md` 事实表述，避免把不存在的 SM86 spec 文案写成当前基线。
  - 状态：需修订，已纳入 Draft 5 最小修订。
- Round 4-B：Codex subagent B（会话 nickname：Pascal）。
  - 分工：技术 / 验收 / 回归审阅。
  - 回执：结论不通过。
  - 阻断项 1：`spec/pass/tuning/dma_memory_hierarchy.md` 仍有 `CUDA SM86 C5` 口径，但 Draft 4 未点名该文件，静态门禁会命中而计划范围未授权。
  - 阻断项 2：静态 SM86 扫描模式未覆盖 `CudaSm86` / `sm86`，可能漏掉 active 旧命名残留。
  - 主线处理：Draft 5 将 `spec/pass/tuning/dma_memory_hierarchy.md` 纳入目标 spec / 当前基线 / S1 范围和验收；静态门禁改为 `rg -n -i`，同时覆盖 `cuda_sm86`、`cuda-sm86`、`CudaSm86`、`sm86`、`sm_86`、`compute_86`、`arch=sm_86` 等形态，SM89 正向扫描同步扩展。
  - 状态：需修订，已纳入 Draft 5 最小修订。
- 当时状态：Round 4-A / Round 4-B 不通过项已在 Draft 5 主线处理；待 Round 5 strict review，不得请求守护最终检验。

### Draft 5：Round 4 主线处理

- 修订对象：Round 4-A / Round 4-B 最小需改项。
- 主线修订：
  - 修正 pass registry spec 基线：`spec/pass/registry.md` 当前没有 `cuda-sm86-lowering` 文案，计划只要求补齐 / 更新其内置 pipeline 公开合同，使 `cuda-sm89-lowering` 成为显式内置 pipeline；实现与测试仍从当前实际 `kernel_gen/passes/registry.py` / `test/passes/test_registry.py` 的 SM86 注册入口迁移。
  - 将 `spec/pass/tuning/dma_memory_hierarchy.md` 纳入本计划，迁移其 CUDA C5 调用侧文案为 SM89；规则语法、`apply_op` 参数、`matmul{["tlm1", "tlm1", "tlm1"]}` 行为和 pass API 不变。
  - 将静态文本门禁改为大小写不敏感的完整模式，避免漏掉 `CudaSm86` / `sm86` / `CudaSm89` / `sm89` 命名。
- 当时状态：待发起 Round 5 strict review；Round 5 已完成且通过，见下文收敛结论。

### Round 5：Codex subagent strict review（通过）

- 人选与会话来源：基于 Draft 5 staged 候选继续使用两个独立 Codex subagent 会话，不使用 agents-list 常驻 tmux 角色会话。
- Round 5-A：Codex subagent A（会话 nickname：Popper）。
  - 分工：流程 / API / 范围审阅。
  - 回执：结论通过；阻断项、最小需改项、待确认项均无。
  - 通过摘要：`spec/pass/registry.md` 事实表述已修正为补齐 / 更新 `cuda-sm89-lowering` 公开合同；pass registry API 不新增、不改签名；归档目标、入档验收占位、C1-C4、expectation 条件授权、unrelated diff 排除与下发门禁完整。
  - 状态：通过。
- Round 5-B：Codex subagent B（会话 nickname：Herschel）。
  - 分工：技术 / 验收 / 回归审阅。
  - 回执：结论通过；阻断项、最小需改项、待确认项均无。
  - 通过摘要：`spec/pass/tuning/dma_memory_hierarchy.md` 已纳入目标 spec / 当前基线 / S1 / 验收，CUDA C5 文案迁移为 SM89，`LowerDmaMemoryHierarchyPass` API、规则语法和 `matmul{["tlm1", "tlm1", "tlm1"]}` 行为不变；静态门禁已改为 `rg -n -i` 完整模式；API-aligned SourceBundle、repo conformance、pass registry pytest、matmul runtime 和 C4 expectation 边界保持闭合。
  - 状态：通过。
- 当前状态：Round 5-A / Round 5-B 均通过；Draft 5 已进入并通过守护最终检验，Draft 6 按用户口径修正 `expectation/` 边界并补齐小任务示例 / 预期后已通过守护复验；用户已最终确认下发，可通知管理员创建 execute。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：Round 1-A Codex subagent A、Round 1-B Codex subagent B 均不通过且已在 Draft 2 主线处理；Round 2-A Codex subagent A、Round 2-B Codex subagent B 均不通过且已在 Draft 3 主线处理；Round 3-A Codex subagent A 不通过且已在 Draft 4 主线处理；Round 3-B Codex subagent B 通过；Round 4-A Codex subagent A、Round 4-B Codex subagent B 均不通过且已在 Draft 5 主线处理；Round 5-A Codex subagent A、Round 5-B Codex subagent B 均通过。
- 收敛结论：Round 5 收敛到无阻断、无最小需改项、无待确认项；Draft 6 按用户口径把 `expectation/` 检查与必要裁定从计划内任务改回架构师侧职责，并补齐每个小任务的示例代码和预期结果。
- 遗留项：无新的方案待确认项；Draft 6 守护复验已通过，用户已最终确认下发，可通知管理员创建 execute。

### Draft 6：用户修正 `expectation/` 边界并补齐示例 / 预期

- 用户修正来源：2026-06-15 用户指出“对 `expectation/` 采用条件授权：先检查是否存在 SM86 口径；当前源码扫描无命中。若后续 strict review 证明存在本计划相关 SM86 expectation，允许按最小范围修改并记录 manifest / hash / scope diff；若不存在，则不新增无必要 expectation。”不属于计划内容，是架构师需要做的事情。
- 用户补充来源：2026-06-15 用户指出“另外为什么每个小计划没有示例代码和预期？”。
- 主线处理：
  - 从计划目标中移除 `expectation/` 条件授权目标句。
  - 取消计划内 `S5. expectation 检查与必要最小修改` 小任务卡。
  - 将 `expectation/` 当前结论收口为架构师侧只读扫描结果：当前无 CUDA SM86 / SM89 专属 expectation 源码命中，当前计划无必过 expectation 合同验收。
  - execute / review / archive_acceptance / merge / 管理员仍不得修改、新建、移动、删除或重命名 `expectation/`；若后续任何角色发现疑似本计划相关 expectation 缺口，必须暂停并回架构裁定，不作为本计划 execute 自行处理事项。
  - 在 S1-S4 每个小任务卡补齐“示例 / 预期”，给出执行人应能写出或观测到的最小代码形态、命令形态和成功判据；这些示例不新增公开 API，不替代验收命令。
- 当前状态：守护复验已通过；用户已最终确认下发，可通知管理员创建 execute。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅`
- Draft 5 当前状态：通过；Draft 5 守护最终检验已完成。
- Draft 6 当前状态：通过；Draft 6 守护复验已完成，用户已最终确认下发。
- Draft 5 守护回执结论：通过。
- Draft 6 守护复验回执结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无新的方案待确认项；仍必须遵守用户“我确认后下发”口径。
- 关键证据：
  - Draft 5 守护输入候选 staged blob=`8de6ec8c6acc91cf77a29a90d566c2cfce1c81b6`，staged sha256=`325943080d0b5bc151e245f053e197b901b09c1b3190d9c234876fa378671558`。
  - Draft 6 守护复验输入候选 staged blob=`4c4992a7a598ff7b667a992e326b846d43d2460d`，staged sha256=`011c412dcabe6f5e5336fe224b04c0b9c862992e5c5b8cab8c85baa248cc9f34`。
  - 本计划正式候选限定为 `ARCHITECTURE/plan/cuda_sm89_include_npu_demo_structure_matmul.md`，本计划 cached name-status=`A ARCHITECTURE/plan/cuda_sm89_include_npu_demo_structure_matmul.md`；`git diff --cached --check -- ARCHITECTURE/plan/cuda_sm89_include_npu_demo_structure_matmul.md` 与 `git diff --check -- ARCHITECTURE/plan/cuda_sm89_include_npu_demo_structure_matmul.md` 均无输出。
  - 全量 cached diff 中 `ARCHITECTURE/plan/memory_plan_multi_min_auto_pad_if_hoist.md` 为 unrelated staged independent file；当前 unstaged 删除现场不属于本计划候选，均不纳入本计划 execute / review / 守护 / merge 证据。
  - 敏感范围 `expectation`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md` 的 cached / unstaged diff 均为空；当前无本计划硬性 expectation gate。
  - Draft 6 已按用户口径将 `expectation/` 检查与必要裁定移出计划目标和计划内 execute 小任务；当前只保留架构师侧只读扫描结论、禁止修改面和“发现疑似缺口则暂停回架构裁定”的边界。
  - 当前计划内小任务标题仅 S1-S4；原 S5 仅作为 Draft 6 修订记录中“取消原 S5”的历史说明出现，不构成当前 execute 事项。
  - S1-S4 均已补齐“示例 / 预期”；示例不新增公开 API，也未替代验收命令。
  - C1 / C2 / C3 / C4 用户确认链、公开 API 迁移口径、include `Core / Memory / Dma / Kernel / Arch` 分层、matmul-only runtime gate、验收命令、禁止修改面和 Diff 反推 pytest / script 与 expectation 合同验收分离口径均通过 Draft 6 守护复验核对。
- 当前允许事项：允许通知管理员创建唯一计划级 execute `cuda-sm89-include-npu-demo-structure-matmul`；管理员不得创建第二个并行 execute。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：提莫炖蘑菇。
- 结论：通过。
- 验证基线：`task/cuda-sm89-include-npu-demo-structure-matmul`，`HEAD=79eabf072d1e11eb5a2743c4cfbf4b0be4317413`，`origin/main=118b1df1ebab9c982be53044beee5efc8ca75424`，`merge-base(HEAD, origin/main)=79eabf072d1e11eb5a2743c4cfbf4b0be4317413`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260615-cuda-sm89-include-npu-demo-structure-matmul`。
- 同步结果：已执行 `git fetch origin`；`HEAD..origin/main` 仅包含 unrelated 主线清理提交，且与本任务 staged 路径无交集。本次验收只以专属 worktree 候选为准，不从主仓 staged / unstaged / ignored local 现场取证。
- 合同验收摘要：当前计划无必过 expectation；`expectation/` 检查与必要裁定属于架构师侧职责，不作为计划内 execute 输出。archive_acceptance 复查确认 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md` staged / unstaged / untracked 均无本任务 diff。
- 最小阻断项或通过摘要：无阻断项。review 已通过；`review -> archive_acceptance` 标准流转补记已核对存在。S1-S4 SM89 target / spec / registry / pipeline / execute_engine 迁移、Core / Memory / Dma / Kernel / Arch include 实质分层、CUDA emit / SourceBundle 迁移、matmul runtime 必过口径和 review 阶段 full runtime gate 均有任务记录证据。archive_acceptance 复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/cuda_sm89/test_public_namespace.py` 通过，旧 SM86 active 文本门禁无输出，`git diff --check` 与 `git diff --cached --check` 通过；当前候选可进入 `merge/归档`。
- 计划归档目标：`agents/codex-multi-agents/log/task_records/done_plan/2026/25/cuda_sm89_include_npu_demo_structure_matmul.md`。

## 计划目标

- 把当前 CUDA target 从 SM86 口径收口到 SM89 口径；用户已确认包括 target 在内完整切换为 `cuda_sm89`。
- 让 CUDA include 结构按 `npu_demo` 的分层思路拆开：aggregate header 只聚合 api 层和 backend 层，backend 头文件按 `Core / Memory / Dma / Kernel / Arch` 等职责分层，避免继续把全部实现塞在一个 `Arch.h`。
- 跑通 matmul：至少 3 个现有 matmul demo case 经过 `DSL -> CUDA lowering -> emit SourceBundle -> nvcc -arch=sm_89 -> ExecutionEngine runtime` 后输出与 NumPy baseline 一致。
- 不把 conv2d / flash_attention 运行时修复纳入本计划必过 runtime 范围。

## 当前基线

- 当前公开 target 名是 `cuda_sm86`：
  - `kernel_gen/target/targets/cuda_sm86.txt`
  - `target="cuda_sm86"`
  - `cuda-sm86-lowering`
  - `build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
  - `ExecutionEngine(target="cuda_sm86")`
  - `emit_c_impl(..., target="cuda_sm86")`
- 当前 CUDA include 公开入口是 `include/cuda_sm86/cuda_sm86.cuh`，公开 namespace 是 `cuda_sm86`。
- 当前 CUDA compile strategy 默认 `nvcc -arch=sm_86`；但现有 runtime gate 已要求本机 `SM89 CUDA device`，当前机器核对到：
  - `nvcc`：`/home/lfr/.local/bin/nvcc`
  - GPU：`NVIDIA GeForce RTX 4060 Laptop GPU, 8.9`
- 当前 CUDA include 结构与 `npu_demo` 不一致：
  - `npu_demo` aggregate：`include/npu_demo/npu_demo.h`
  - `npu_demo` backend 分层：`Core.h / Trance.h / Memory.h / Dma.h / Kernel.h / Arch.h / cost/*.h`
  - `cuda_sm86` aggregate：`include/cuda_sm86/cuda_sm86.cuh`
  - `cuda_sm86` backend：只有一个 `include/cuda_sm86/Arch.h`，其中混入 Vector / Memory / DMA / Kernel / Arch / runtime detail / CUDA helper / matmul 等多类职责。
- 当前 CUDA emit package 是 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/`，已有 per-op 文件，但 SourceBundle builder 和 generated source 仍大量写死 `cuda_sm86` 命名、artifact、header path 和 symbol prefix。
- 当前 CUDA runtime 测试入口 `test/cuda/test_cuda_sm86_kernel_demos_runtime.py` 覆盖 3 个 matmul、3 个 conv2d、3 个 flash_attention demo；本计划建议最小必过 runtime 先收窄为 matmul 3 case，避免把目标扩大成整个 CUDA backend 重测。
- 当前 active 公共 spec 仍有 `cuda_sm86` 口径，必须纳入本计划：
  - `spec/pass/registry.md`：当前内置 pipeline 公开合同只显式写 `default-lowering` 与 `npu-demo-lowering`；需补齐 / 更新为显式包含 `cuda-sm89-lowering`，并声明旧 `cuda-sm86-lowering` 不作为 active 成功入口，属于既有 pass registry 公开 API 的内置 pipeline 合同补齐。
  - `spec/pass/tuning/dma_memory_hierarchy.md`：当前 `CUDA SM86 C5` 调用侧文案需迁移为 `CUDA SM89 C5`；规则语法和 `LowerDmaMemoryHierarchyPass` API 不变。
  - `spec/target/registry.md`：`cuda_sm86.txt` 目录 target 是公开合同；需迁移为 `cuda_sm89.txt`，属于公开 API 合同迁移。
  - `spec/dsl/gen_kernel/emit.md`：`target="cuda_sm86"` 的 ModuleOp SourceBundle 通用合同；需迁移为 `target="cuda_sm89"`，属于公开 API 合同迁移。
  - `spec/execute_engine/strategy.md`：内置 strategy 注册、stream 失败语义、CUDA SourceBundle nvcc 编译合同；需迁移为 `cuda_sm89`，属于公开 API / 稳定错误语义迁移。
  - `spec/execute_engine/execute_engine.md`：内置 target 集合含 `cuda_sm86`；需迁移为 `cuda_sm89`，属于公开 API 合同迁移。
  - `spec/execute_engine/execute_engine_api.md`：功能实现路径含 `builtin_strategy/cuda_sm86.py`；需迁移为 `cuda_sm89.py`，属于文档路径迁移。
  - `spec/script/pytest_config.md`：`cuda` mark 文案写 CUDA SM86；需改为 SM89 runtime 文案，属于测试配置说明迁移，不新增 pytest mark。
- 当前 active 通用测试仍绑定 `cuda_sm86`，必须纳入本计划：
  - `test/passes/test_registry.py`
  - `test/execute_engine/test_contract.py`
  - `test/execute_engine/test_compile_strategy.py`
  - `test/execute_engine/test_builtin_strategy.py`
  - `test/target/test_registry.py`
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py`
  - `test/repo_conformance/test_private_api_boundaries.py`
  - `test/script/test_pytest_config.py`
- 当前 `expectation/` 下未发现 CUDA SM86 / SM89 专属合同资产；已用不受 ignore 限制的 `rg -uuu` 只读扫描复核，源码无 `cuda_sm86` / `sm_86` / `SM86` / `cuda-sm86` 和 `cuda_sm89` / `sm_89` 命中。`expectation/` 被 `.gitignore` 忽略，属于合同资产敏感范围。
- 当前主仓存在无关 dirty / staged 状态，本计划不得混用：
  - `D ARCHITECTURE/plan/cuda_sm86_emit_package_structure_refactor_green_plan.md`
  - `A ARCHITECTURE/plan/memory_plan_multi_min_auto_pad_if_hoist.md`
  - `D ARCHITECTURE/plan/symbol_hoist_pipeline_pass_green_plan.md`
  - `D kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`

## 方案比较与选型

### C1：SM86 -> SM89 公开入口策略

- 用户决策：选项 A，完整公开重命名为 `cuda_sm89`，旧 `cuda_sm86` 不再作为成功入口；确认来源为 2026-06-15 用户回复“是的，包括target”。

- 选项 A：完整公开重命名为 `cuda_sm89`，旧 `cuda_sm86` 不再作为成功入口。
  - 改动：target 文件、target registry、pipeline builder / registry 名、emit package、include path、namespace、execute_engine strategy、测试和 spec 全部切到 SM89。
  - 优点：完全符合“将 sm86 改为 sm89”；不会留下两个 CUDA target 口径。
  - 风险：公开 API 破坏性最大；所有依赖 `cuda_sm86` 的测试、文档和代码必须同步迁移；旧用户调用会失败。
  - 推荐：若目标是正式切换项目 CUDA target，推荐 A。
- 选项 B：新增 `cuda_sm89`，保留 `cuda_sm86` 作为临时兼容别名。
  - 改动：新增 SM89 正式入口，同时旧入口代理到同一实现或保留 wrapper。
  - 优点：迁移风险小，旧测试 / 使用方不立即断。
  - 风险：同时存在两个 target，容易继续混淆 SM86/SM89；include 结构也要维护双份或 alias。
  - 推荐：仅当你要求兼容旧入口时选 B。
- 选项 C：只把 `-arch=sm_86` 改为 `-arch=sm_89`，不改 `cuda_sm86` target / namespace / include。
  - 优点：最小实现。
  - 风险：不符合“将 sm86 改为 sm89”和 include 结构统一诉求；历史计划已经走过类似“runtime SM89 但 API 名仍 SM86”的口径。
  - 推荐：不推荐。

### C2：CUDA include 结构对齐 `npu_demo` 的范围

- 用户决策：选项 B，功能分层对齐，不制造未实现家族；确认来源为 2026-06-15 用户回复“是的”。

- 选项 A：结构全量对齐。
  - 目标形态：
    - `include/cuda_sm89/cuda_sm89.cuh`
    - `include/cuda_sm89/Core.h`
    - `include/cuda_sm89/Memory.h`
    - `include/cuda_sm89/Dma.h`
    - `include/cuda_sm89/Kernel.h`
    - `include/cuda_sm89/Arch.h`
    - `include/cuda_sm89/Trance.h`
    - `include/cuda_sm89/cost/Core.h`
    - `include/cuda_sm89/cost/Dma.h`
    - `include/cuda_sm89/cost/Kernel.h`
  - 优点：目录结构最接近 `npu_demo`。
  - 风险：CUDA 当前没有 cost / Trance runtime 合同，若为了一致性补空壳，会增加伪 API 和测试负担。
  - 推荐：不推荐一次性做 full family，除非用户明确要求 cost / Trance 也同步成 CUDA 公共表面。
- 选项 B：功能分层对齐，不制造未实现家族。
  - 目标形态：
    - `include/cuda_sm89/cuda_sm89.cuh`
    - `include/cuda_sm89/Core.h`
    - `include/cuda_sm89/Memory.h`
    - `include/cuda_sm89/Dma.h`
    - `include/cuda_sm89/Kernel.h`
    - `include/cuda_sm89/Arch.h`
  - aggregate 聚合顺序对齐 `npu_demo` 的原则：先 `include/api/*`，再 `include/cuda_sm89/*`。
  - 不新增 CUDA cost / Trance 公开 API；后续有需求再单独计划。
  - 优点：解决当前 monolithic `Arch.h` 问题，避免伪接口。
  - 风险：目录数量不与 `npu_demo` 完全一致。
  - 推荐：推荐 B。
- 已确认落地结构：
  - `include/cuda_sm89/cuda_sm89.cuh` exact include 顺序固定为：
    1. `#include "include/api/Core.h"`
    2. `#include "include/api/Memory.h"`
    3. `#include "include/api/Dma.h"`
    4. `#include "include/api/Kernel.h"`
    5. `#include "include/api/Arch.h"`
    6. `#include "include/cuda_sm89/Core.h"`
    7. `#include "include/cuda_sm89/Memory.h"`
    8. `#include "include/cuda_sm89/Dma.h"`
    9. `#include "include/cuda_sm89/Kernel.h"`
    10. `#include "include/cuda_sm89/Arch.h"`
  - 不聚合 `include/api/Trance.h`、`include/api/cost/*.h`、`include/cuda_sm89/Trance.h` 或 `include/cuda_sm89/cost/*.h`；本计划不新增 CUDA Trance / cost public surface。
  - 可编译依赖由上述顺序保证：`Core` 承接 `Status / S_INT / Vector`，`Memory` 承接 `MemorySpace / Memory / stride / view`，`Dma` 承接 alloc / slice / ring，`Kernel` 承接 matmul / img2col2d / elementwise / reduce，`Arch` 承接 `ArgSlot / KernelContext / launch / block/thread/barrier` 和 CUDA runtime glue。
- 选项 C：只调整 aggregate include 顺序，不拆 `Arch.h`。
  - 优点：最小改动。
  - 风险：不能解决结构不一致；`Arch.h` 仍是巨型混合实现。
  - 推荐：不推荐。

### C3：matmul runtime 验收范围

- 用户决策：选项 A，只把 3 个 matmul demo 作为必须 runtime 通过项；确认来源为 2026-06-15 用户回复“是的”。

- 选项 A：只把 3 个 matmul demo 作为必须 runtime 通过项。
  - 命令形态：`pytest -q test/cuda/test_cuda_sm89_kernel_demos_runtime.py -m cuda -k matmul -rs`
  - 优点：正中用户“跑通 matmul”；降低 conv2d / flash_attention 扩大风险。
  - 风险：不能证明其它 CUDA demo 在重命名和 include 拆分后仍 runtime 通过。
  - 推荐：推荐 A。
- 选项 B：保留现有 9 demo runtime 全量通过作为必须项。
  - 命令形态：`pytest -q test/cuda/test_cuda_sm89_kernel_demos_runtime.py -m cuda -rs`
  - 优点：覆盖最完整。
  - 风险：计划范围明显扩大；conv2d / flash_attention 的问题会阻断本计划。
  - 推荐：仅当用户要求“CUDA demo 全量不退化”时选 B。

### C4：expectation 架构侧检查与条件修改授权

- 用户决策：条件授权。用户要求“需要修改 expatation，如果有必要。因为有些是以86来写的，检查一下”。
- 当前检查结论：
  - `expectation/` 源码中未发现 CUDA SM86 / SM89 专属合同资产或 SM86 文本命中。
  - 当前不新增无必要 expectation，也不把 `expectation/` 写入本计划 execute 修改面或小任务卡。
- 允许修改条件：
  - 仅当架构师后续核对发现本计划相关的 `expectation/` 源码确实以 SM86 / `cuda_sm86` / `sm_86` 写死，且该资产应随本计划迁移时，才允许按最小范围修改。
  - 修改前必须由架构师补 manifest / hash / check-ignore / ls-files / scope diff / 合同目标 / 验收命令。
  - execute / review / archive_acceptance / merge / 管理员不得自行修改 expectation；如发现疑似本体缺口，必须暂停并回架构裁定。
- 可选新增条件：
  - 若后续架构核对认为缺少 CUDA SM89 matmul 长期合同资产会影响验收可信度，可建议新增 `expectation/execute_engine/cuda_sm89/matmul.py`；但新增前仍需用户再次明确确认路径和合同目标。

## 公开 API 设计

- 用户确认来源：
  - 已确认流程：用户要求先讨论、由用户决策，必要时添加 expectation 也需用户确认后再下发。
  - 已确认公开 API：C1=A，完整切换到 `cuda_sm89`，包括 target；旧 `cuda_sm86` 不再成功。
  - 已确认 include 结构：C2=B，按功能分层对齐，不新增未实现 cost / Trance。
  - 已确认 runtime 范围：C3=A，只锁 matmul runtime 必过。
  - 已确认 expectation 权限：C4=架构师侧条件授权检查和必要最小修改；当前扫描无命中，不进入计划内 execute 小任务。
- 新增 / 替换公开 API：
  - `target="cuda_sm89"`
  - `cuda-sm89-lowering`
  - `build_cuda_sm89_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
  - 既有 `load_builtin_passes() -> None` 加载 `cuda-sm89-lowering` 内置 pipeline；不新增、不改签名。
  - 既有 `list_registered_pipelines() -> list[str]` 返回值包含 `cuda-sm89-lowering`；旧 `cuda-sm86-lowering` 不作为 active 成功入口。
  - 既有 `build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager` 可构造 `cuda-sm89-lowering`，并透传 options 到 `build_cuda_sm89_lowering_pipeline(...)`。
  - `extern "C" int kg_execute_entry(cuda_sm89::ArgSlot* slots, unsigned long long count)`
  - `namespace cuda_sm89`
  - `struct cuda_sm89::ArgSlot`
  - `cuda_sm89::ArgSlot` 字段：`kind`、`data`、`shape`、`stride`、`rank`、`dtype_code`、`int_value`、`float_value`
  - `class cuda_sm89::KernelContext`
  - `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status cuda_sm89::launch(Context& ctx, Args&&... args)`
  - `__device__ S_INT cuda_sm89::block_id()`
  - `__device__ S_INT cuda_sm89::thread_id()`
  - `__device__ S_INT cuda_sm89::thread_num()`
  - `__device__ void cuda_sm89::barrier()`
  - `template <MemorySpace Space, typename T, typename Context> __device__ Memory<Space, T> cuda_sm89::alloc(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm)`
  - `template <MemorySpace Space, typename SlotT, typename BackingT> class cuda_sm89::DmaRing`
  - `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ cuda_sm89::DmaRing<Space, SlotT, BackingT>::DmaRing(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, const Vector& shape, const Vector& stride, MemoryFormat format)`
  - `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm89::DmaRing<Space, SlotT, BackingT>::current() const`
  - `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm89::DmaRing<Space, SlotT, BackingT>::advance()`
  - `template <typename SlotT, MemorySpace Space, typename BackingT> __device__ cuda_sm89::DmaRing<Space, SlotT, BackingT> cuda_sm89::make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
  - `template <MemorySpace Space, typename T, typename Context> __device__ Status cuda_sm89::fill(Context& ctx, Memory<Space, T>& target, const T& value)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm89::slice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm89::deslice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::load(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::store(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::transpose(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::broadcast(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
  - `template <MemorySpace Space, typename T> __host__ __device__ Memory<Space, T> cuda_sm89::view(const Memory<Space, T>& source, long long offset, long long size, long long stride)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::add(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::sub(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::mul(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::truediv(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::exp(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::reduce_sum(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::reduce_max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
  - `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context> __device__ Status cuda_sm89::matmul(Context& ctx, Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs, bool acc = false)`
  - `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> __device__ Status cuda_sm89::img2col2d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`
- 签名迁移边界：
  - 上述 include API 是从当前 `cuda_sm86` 公开签名做 namespace / target / path 迁移，不改变模板参数顺序、返回值、默认值、`__device__` / `__host__` 限定或 `kg_execute_entry(cuda_sm89::ArgSlot* slots, unsigned long long count)` C ABI 形态。
  - 执行若发现必须改变任一公开签名、默认值、返回值或稳定错误文本，必须暂停并转用户确认；不得在 execute 中自行改 API。
- 旧 API 处理：
  - 删除 / 不再注册 `cuda_sm86` 成功入口；active spec / implementation / test 不保留旧成功路径。
- 稳定错误语义：
  - `target_header_mismatch` 的 detail 需从 `cuda_sm86` 更新为 `cuda_sm89`。
  - `stream_not_supported` 文本需从 `cuda_sm86 does not support non-None stream` 更新为 `cuda_sm89 does not support non-None stream`。
  - unsupported emit 文本需从 `unsupported cuda_sm86 final IR op: ...` 更新为 `unsupported cuda_sm89 final IR op: ...`。
  - `build_cuda_sm89_lowering_pipeline({"target": "<非 cuda_sm89>"})` 必须抛 `KernelCodeError`，错误文本包含 `target must be cuda_sm89`。
  - `build_cuda_sm89_lowering_pipeline({"<未知 option>": "..."})` 必须抛 `KernelCodeError`，错误文本包含 `only accepts target option`。

## 完成态定义

- Draft 3 已按用户确认、Round 1 修订和 Round 2 修订写清唯一方案，不再保留冲突口径。
- `cuda_sm89` 是唯一 CUDA target 口径；`nvcc` 默认命令使用 `-arch=sm_89`，不做设备能力探测或自动切换。
- CUDA generated source 使用 `#include "include/cuda_sm89/cuda_sm89.cuh"`、`cuda_sm89::` namespace 和 `kg_cuda_sm89_*` generated symbol prefix。
- CUDA include backend 按用户确认的结构拆分，并更新文件级说明 / API 列表；`cuda_sm89.cuh` 必须按 C2 exact include 顺序聚合，不包含 Trance / cost 头。
- 3 个 matmul demo runtime case 在 SM89 机器上真实执行通过，输出对齐 NumPy baseline。
- 旧 `sm_86` / `cuda_sm86` 残留只允许出现在历史计划、done_plan、迁移说明或明确负向测试中；active spec / implementation / test 不得保留旧成功路径。

## 验收设计

- 环境核对：
  - `which nvcc`
  - `nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader`
- 静态文本门禁：
  - `rg -n -i "cuda[_-]?sm86|cuda[_-]?sm_86|sm86|sm_86|compute_86|arch=sm_86|cuda-sm86" spec include kernel_gen test --glob '!**/done_plan/**'`
  - 预期：active 成功路径无旧口径；命中只能出现在历史计划 / done_plan / 本计划迁移记录 / 明确负向测试中；不得漏掉 `CudaSm86`、`sm86` 这类大小写或下划线变体。
  - `rg -n -i "cuda[_-]?sm89|cuda[_-]?sm_89|sm89|sm_89|compute_89|arch=sm_89|cuda-sm89" spec include kernel_gen test`
  - 预期：命中正式 SM89 target、include、pipeline、compile flag、runtime gate、`CudaSm89` / `sm89` 命名和测试。
- pytest / 脚本：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/cuda_sm89/test_public_namespace.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/target/test_cuda_sm89_registry.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/target/test_registry.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_cuda_sm89_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tuning/test_dma_memory_hierarchy.py -k "all_tlm1 or matmul"`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_cuda_sm89_strategy.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_builtin_strategy.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm89_emit.py test/dsl/gen_kernel/emit/test_cuda_sm89_memory_hierarchy.py test/dsl/gen_kernel/emit/test_cuda_sm89_launch_mapping.py test/dsl/gen_kernel/emit/test_cuda_sm89_fail_fast.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm89_api_aligned_codegen.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py -k "cuda_sm89 or source_builder"`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_pytest_config.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/cuda/test_cuda_sm89_kernel_demos_runtime.py -m cuda -k matmul -rs`
- Runtime 环境口径：
  - `test/cuda/test_cuda_sm89_kernel_demos_runtime.py -m cuda -k matmul -rs` 的完成态必须是真实执行通过；`nvcc` 缺失、无 CUDA device 或无 SM89 device 时只能记录环境阻塞 / skip 原因，不得计为 runtime 通过。
- 当前必过 expectation 合同验收：
  - 当前无必过 expectation；架构师侧只读扫描未发现 CUDA SM86 / SM89 专属 expectation。
  - `expectation/` 检查与必要裁定不作为计划内 execute 小任务；若后续发现疑似本计划相关 SM86 expectation，必须暂停回架构侧裁定。
- Diff 反推要求：
  - execute / review / archive_acceptance 必须按实际 diff 补测试；`expectation` 若新增，只能单列为合同验收，不替代 diff 反推 pytest。

## 计划内小任务

### S1. 收口 SM89 公开 target / spec / registry 口径

- 为什么做：当前 `cuda_sm86` 是公开 target，用户要求改为 SM89，必须先收口公开 API 与 spec。
- 做什么：按用户确认的 C1=A 更新 pass registry、target registry、pipeline spec、emit spec、execute_engine target / strategy / API spec 和测试命名。
- 不做什么：不在本卡拆 include 实现，不跑 runtime。
- 怎么验收：pass registry / target / pipeline / execute_engine spec 与测试均只表达用户确认的 SM89 口径；`load_builtin_passes()` 后 `cuda-sm89-lowering` 可见且可构造；`build_cuda_sm89_lowering_pipeline(...)` 锁定 `target must be cuda_sm89` 与 `only accepts target option` 错误文本；旧 SM86 命中受控。
- 卡住问谁：公开 API 新冲突问用户；流程状态问管理员；架构边界问大闸蟹。
- 上下文摘要：历史计划曾保留 `cuda_sm86` target 但 runtime gate 用 SM89；当前用户要求改 target 口径，属于公开 API 变更。
- 小任务目标：把 SM89 pass registry / target / pipeline / execute_engine public contract 写成唯一可执行口径，并让测试能机械验证。
- 非目标：不承诺旧 `cuda_sm86` 兼容，不保留旧成功入口。
- 模块范围：`spec/pass/registry.md`、`spec/pass/tuning/dma_memory_hierarchy.md`、`spec/target/registry.md`、`spec/pass/pipeline/cuda_sm89_lowering.md`、`spec/pass/pipeline/cuda_sm86_lowering.md` 的迁移处理、`spec/execute_engine/execute_engine_target.md`、`spec/execute_engine/strategy.md`、`spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md`、`spec/script/pytest_config.md`、`kernel_gen/passes/registry.py`、`kernel_gen/target/targets/`、`kernel_gen/pipeline/`、`kernel_gen/execute_engine/`、对应 `test/`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、无关计划、无关 dump。
- 合同真源：用户确认 > spec > pytest > 当前实现。
- 最小功能闭环：`load_builtin_passes()` 后 `list_registered_pipelines()` 可发现 `cuda-sm89-lowering`，`build_registered_pipeline("cuda-sm89-lowering", {"target": "cuda_sm89"})` 返回 `PassManager(name="cuda-sm89-lowering")`；`build_cuda_sm89_lowering_pipeline(...)` 和 `ExecutionEngine(target="cuda_sm89")` 可被测试发现并拒绝非 SM89 target；非法 target / 未知 option 的稳定错误文本由 pytest 锁定。
- 示例 / 预期：
  ```python
  from kernel_gen.passes.registry import (
      build_registered_pipeline,
      list_registered_pipelines,
      load_builtin_passes,
  )
  from kernel_gen.pipeline.cuda_sm89_lowering import build_cuda_sm89_lowering_pipeline

  load_builtin_passes()
  assert "cuda-sm89-lowering" in list_registered_pipelines()
  pm = build_registered_pipeline("cuda-sm89-lowering", {"target": "cuda_sm89"})
  assert pm.name == "cuda-sm89-lowering"
  assert build_cuda_sm89_lowering_pipeline({"target": "cuda_sm89"}).name == "cuda-sm89-lowering"
  ```
  预期：`cuda-sm89-lowering` 是 active 成功入口；`cuda-sm86-lowering` 不再作为 active 成功入口；非法 target 报错包含 `target must be cuda_sm89`，未知 option 报错包含 `only accepts target option`。
- 执行步骤：
  1. 按 C1=A 新增 / 替换 `cuda_sm89` target registry 文件和 pipeline builder，并移除 active `cuda_sm86` 成功入口。
  2. 更新 execute_engine 内置 target/include/compiler strategy 的公开合同与错误文本。
  3. 更新 `spec/pass/registry.md`、`kernel_gen/passes/registry.py` 与 `test/passes/test_registry.py`，使 `load_builtin_passes()` 注册 `cuda-sm89-lowering`，并移除 active `cuda-sm86-lowering` 成功 registry 入口。
  4. 更新 `spec/pass/tuning/dma_memory_hierarchy.md` 中 CUDA C5 调用侧文案为 SM89；不改变 `LowerDmaMemoryHierarchyPass` API、规则语法或 `matmul{["tlm1", "tlm1", "tlm1"]}` 行为。
  5. 更新 `spec/target/registry.md`、`spec/execute_engine/strategy.md`、`spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md` 与 `spec/script/pytest_config.md` 中 active CUDA target 口径。
  6. 更新 `spec/pass/pipeline/cuda_sm89_lowering.md` 与 `test/passes/pipeline/test_cuda_sm89_lowering.py`，锁定 pipeline 名称、pass 顺序、`target must be cuda_sm89` 和 `only accepts target option`。
  7. 更新对应 pass registry / dma memory hierarchy / target registry / pipeline / strategy / pytest config pytest。
- 验收必过项目：见 `验收设计` 中 pass registry / target / pipeline / execute_engine / pytest config 命令。
- 记录要求：任务记录写清旧入口处理方式、公开 API 变更证据和旧 SM86 文本门禁结果。

### S2. 按确认结构拆分 CUDA include

- 为什么做：当前 `include/cuda_sm86/Arch.h` 是巨型混合实现，和 `npu_demo` 分层结构不一致。
- 做什么：按 C2=B 将 CUDA include 拆为 `Core / Memory / Dma / Kernel / Arch` 等职责，并由 `cuda_sm89.cuh` aggregate 按 exact include 顺序聚合。
- 不做什么：不新增未确认的 CUDA cost / Trance 公开 API；不引入 cuBLAS 或第三方 kernel fallback。
- 怎么验收：`test/include/cuda_sm89/test_public_namespace.py` / 文本门禁确认 aggregate exact include 顺序、只聚合 C2 指定 api/backend 头、不聚合 Trance / cost；backend detail 不进入公开 API。
- 卡住问谁：若执行发现必须新增 CUDA cost / Trance 公开 API，暂停问用户；实现边界问大闸蟹。
- 上下文摘要：npu_demo aggregate 聚合 `include/api/*` 和 `include/npu_demo/*`；CUDA 当前只有 `api/Arch.h` 与 backend `Arch.h`。
- 小任务目标：生成源码只依赖 `include/cuda_sm89/cuda_sm89.cuh`，而 backend 实现按职责分层，matmul 所需 wrapper 可编译。
- 非目标：不重写 CUDA 数学算法；不调整 DSL 用户层 matmul 写法。
- 模块范围：`include/cuda_sm89/`、`spec/include/cuda_sm89/`、include / emit / execute_engine 相关测试。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、无关 target。
- 合同真源：用户确认 > `spec/include/cuda_sm89/cuda_sm89.md` > include pytest > 当前实现。
- 最小功能闭环：手写或 generated SourceBundle 包含 `#include "include/cuda_sm89/cuda_sm89.cuh"` 时可以通过 fake nvcc / compile-only 测试；`cuda_sm89.cuh` exact include 顺序与 C2 一致。
- 示例 / 预期：
  ```cpp
  #include "include/api/Core.h"
  #include "include/api/Memory.h"
  #include "include/api/Dma.h"
  #include "include/api/Kernel.h"
  #include "include/api/Arch.h"
  #include "include/cuda_sm89/Core.h"
  #include "include/cuda_sm89/Memory.h"
  #include "include/cuda_sm89/Dma.h"
  #include "include/cuda_sm89/Kernel.h"
  #include "include/cuda_sm89/Arch.h"
  ```
  预期：`include/cuda_sm89/cuda_sm89.cuh` 按上述 exact 顺序聚合；不包含 `Trance.h`、`cost/*.h` 或 `include/cuda_sm86/*`；新增 / 修改 header 的文件级说明和 API 列表与公开签名一致。
- 执行步骤：
  1. 从 monolithic CUDA `Arch.h` 中按职责迁移 Core / Memory / DMA / Kernel / Arch 内容。
  2. 为每个新增 / 修改 header 补齐文件级说明、API 列表、使用示例和关联文件。
  3. 按 C2 exact include 顺序更新 aggregate include，确保不包含 Trance / cost。
  4. 更新 `test/include/cuda_sm89/test_public_namespace.py` 或等价 include structure / API-list 测试。
- 验收必过项目：`test/include/cuda_sm89/test_public_namespace.py`、execute_engine fake nvcc strategy pytest、emit SourceBundle pytest。
- 记录要求：任务记录写清每个 header 的职责、未新增 cost / Trance 的依据，以及是否存在旧 monolithic 残留。

### S3. 更新 CUDA emit / SourceBundle 到 SM89

- 为什么做：generated source 当前写死 `cuda_sm86` include、namespace、symbol prefix、error 文本和 artifact header path。
- 做什么：将 CUDA emit package、constants、runtime source、SourceBundle builder 和 per-op wrapper call 输出迁移到 SM89 口径。
- 不做什么：不改变 final IR traversal 算法，不引入 name-only fallback，不修改 matmul DSL API。
- 怎么验收：emit tests 证明 generated source 使用 `cuda_sm89::`、`kg_cuda_sm89_*`、`include/cuda_sm89/generated_entry.cuh`、`-arch=sm_89`，API-aligned SourceBundle 测试覆盖 hash entry / slot ABI / wrapper calls / dynamic symbol-control-flow，repo conformance 测试覆盖 source builder 私有 API 边界，且旧 SM86 成功路径清零。
- 卡住问谁：旧 generated symbol 是否兼容问用户；SourceBundle 结构问大闸蟹。
- 上下文摘要：当前 `source_bundle.py` 中大量 `kg_cuda_sm86_*` / `cuda_sm86::` 是 active 生成路径。
- 小任务目标：SM89 SourceBundle 可被 execute_engine 写盘、编译，并保持 per-op final IR dataflow 语义。
- 非目标：不修复 conv2d / flash_attention runtime 数值问题。
- 模块范围：`spec/dsl/gen_kernel/emit.md`、`spec/dsl/gen_kernel/emit/cuda_sm89.md`、`kernel_gen/dsl/gen_kernel/emit/cuda_sm89/`、`kernel_gen/dsl/gen_kernel/emit/register` 自动加载相关路径、emit tests。
- 禁止修改面：`expectation/`、无关 emit backend、无关 npu_demo backend。
- 合同真源：spec > pytest > 当前实现。
- 最小功能闭环：matmul final IR 生成的 SourceBundle 包含 SM89 include、namespace、symbol prefix 和 Tensor Core marker；API-aligned SourceBundle 生成测试和 repo conformance 边界测试均迁移到 SM89 口径。
- 示例 / 预期：
  ```cpp
  #include "include/cuda_sm89/cuda_sm89.cuh"

  extern "C" int kg_execute_entry(cuda_sm89::ArgSlot* slots, unsigned long long count) {
    cuda_sm89::KernelContext ctx(slots, count);
    return kg_cuda_sm89_entry(ctx);
  }
  ```
  预期：generated SourceBundle 使用 `cuda_sm89::` namespace、`kg_cuda_sm89_*` symbol prefix、`include/cuda_sm89/generated_entry.cuh` artifact 和 `-arch=sm_89` 编译参数；active generated source 中不得残留 `cuda_sm86::`、`kg_cuda_sm86_*` 或 `include/cuda_sm86/` 成功路径。
- 执行步骤：
  1. 按 C1=A 迁移 / 新增 emit package 注册入口，删除 active `cuda_sm86` 成功注册路径。
  2. 更新 constants、runtime source 和 SourceBundle artifact key。
  3. 更新 per-op wrapper call 和 fail-fast 文本。
  4. 更新 `spec/dsl/gen_kernel/emit.md` 的通用 target 合同。
  5. 迁移 / 新增 `test/dsl/gen_kernel/emit/test_cuda_sm89_api_aligned_codegen.py`，保留当前 SM86 API-aligned 测试覆盖的 hash entry、slot ABI、wrapper calls、dynamic symbol/control-flow 和 compile-only 生成形态。
  6. 迁移 `test/repo_conformance/test_private_api_boundaries.py` 中 CUDA source builder package-local / exact public method set 的 SM89 口径。
  7. 更新 emit / launch / memory hierarchy / fail-fast / package pytest。
- 验收必过项目：见 `验收设计` 的 emit pytest 组合、`test/dsl/gen_kernel/emit/test_cuda_sm89_api_aligned_codegen.py`、`test/dsl/gen_kernel/emit/test_package.py` 与 `test/repo_conformance/test_private_api_boundaries.py -k "cuda_sm89 or source_builder"`。
- 记录要求：任务记录写清旧 `cuda_sm86` 字符串清理结果和保留原因。

### S4. 跑通 SM89 matmul runtime

- 为什么做：用户明确要求跑通 matmul，且当前机器具备 SM89 环境。
- 做什么：用 `target="cuda_sm89"` 运行 3 个现有 matmul demo case 的 CUDA runtime 测试，输出与 NumPy baseline 一致。
- 不做什么：不把 conv2d / flash_attention runtime 作为本卡必过项。
- 怎么验收：`pytest -q test/cuda/test_cuda_sm89_kernel_demos_runtime.py -m cuda -k matmul -rs` 通过；记录 `nvcc` 路径和 GPU compute capability。
- 卡住问谁：CUDA 环境缺失问管理员；matmul 语义 / API 变更问用户；实现边界问大闸蟹。
- 上下文摘要：当前 runtime test 已有 matmul 3 case 形态，可迁移到 SM89 目标。
- 小任务目标：真实 `nvcc -arch=sm_89` 编译 `.so` 并通过 `kg_execute_entry` 执行 matmul。
- 非目标：不新增矩阵 shape 全量 fuzz；不改 matmul operation helper 参数。
- 模块范围：`test/cuda/`、CUDA emit / include / execute_engine 相关实现。
- 禁止修改面：`expectation/` 不进入 execute 修改面；若发现疑似本计划相关 SM86 expectation，必须暂停回架构裁定。
- 合同真源：pytest runtime > spec > current implementation。
- 最小功能闭环：static / dynamic tile 的 3 个 matmul case，absent bias 与 present bias 都通过。
- 示例 / 预期：
  ```bash
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
    test/cuda/test_cuda_sm89_kernel_demos_runtime.py -m cuda -k matmul -rs
  ```
  预期：在 `nvidia-smi` 显示 compute capability 8.9 且 `nvcc` 可用时，3 个 matmul demo 真实编译并运行通过，日志能看到 SM89 target / include / `-arch=sm_89`，输出与 NumPy baseline 对齐；环境缺失只能记录阻塞或 skip 原因，不能记作 runtime 通过。
- 执行步骤：
  1. 迁移 runtime test 到 SM89 target / pipeline / include。
  2. 运行环境 preflight，缺环境时记录阻塞，不记作通过。
  3. 跑 matmul runtime 并记录输出摘要。
- 验收必过项目：matmul runtime 命令。
- 记录要求：任务记录写清 `which nvcc`、`nvidia-smi`、pytest 结果、失败时 stderr 摘要和是否涉及环境阻塞。

## 计划自检与返工口径

- 自检：
  - 当前 Draft 5 已记录公开 API 变更用户确认来源。
  - 当前 Draft 5 已记录 include 结构范围用户确认来源。
  - 当前 Draft 5 已记录 runtime matmul 范围用户确认来源。
  - 当前 Draft 6 已按用户修正记录 `expectation/` 检查与必要裁定属于架构师侧职责，不纳入计划内 execute 小任务。
  - 当前 Draft 6 已按用户补充为 S1-S4 每个小任务卡增加示例代码和预期结果。
  - 当前 Draft 5 已处理 Round 1-A / Round 1-B / Round 2-A / Round 2-B / Round 3-A / Round 4-A / Round 4-B 问题，且 Round 5-A / Round 5-B 均通过；Draft 6 守护复验已通过，用户已最终确认下发。
- 返工口径：
  - 若公开 API、expectation 边界、include 结构或 runtime 验收仍有歧义，必须回到计划修订。
  - 若后续修订导致 subagent strict review、守护最终检验或用户确认任一门禁失效，必须重新收敛；当前用户已最终确认下发，可通知管理员创建 execute。

## 待确认项

- 无。C1 / C2 / C3 / C4 已按 2026-06-15 用户回复收口。

## 用户确认与协同约束

- 用户确认来源：
  - 2026-06-15 用户要求新计划：将 SM86 改为 SM89、include 结构跟 npu_demo 一致、跑通 matmul。
  - 2026-06-15 用户要求流程：先讨论、用户决策；如有必要完善添加 expectation，经过用户确认再下发。
- 用户已确认事项：
  - 允许进入计划讨论流程。
  - C1=A：完整切到 `cuda_sm89`，包括 target。
  - C2=B：include 按 `Core / Memory / Dma / Kernel / Arch` 功能分层对齐 `npu_demo`，不新增未实现 cost / Trance。
  - C3=A：runtime 必过范围只锁 matmul。
  - C4=架构师侧条件授权：由架构师检查 `expectation/`，如有本计划相关 SM86 口径则最小修改；当前只读扫描无命中，不纳入计划内 execute 小任务。
- 待用户确认项：无。
- 迭代审阅记录：Round 1 strict review 已完成且不通过并在 Draft 2 主线修订；Round 2 strict review 已完成且不通过并在 Draft 3 主线修订；Round 3 strict review 已完成，Round 3-A 不通过并在 Draft 4 主线修订，Round 3-B 通过；Round 4 strict review 已完成且不通过并在 Draft 5 主线修订；Round 5-A / Round 5-B 均通过，subagent 收敛结论为无阻断、无最小需改项、无待确认项。
- 守护最终检验：Draft 5 已通过；Draft 6 按用户口径修正 `expectation/` 边界并补齐小任务示例 / 预期后，守护复验已通过。
- 下发门禁：用户已最终确认下发，允许通知管理员创建唯一计划级 execute `cuda-sm89-include-npu-demo-structure-matmul`。
