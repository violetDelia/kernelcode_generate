# DSL Cost Run Cost-Mode Kernel Summary Plan Draft 8

## 文档信息

- 计划用途：只规划 `dsl_cost_run(...)` 的 cost-mode 执行语义。目标是让 emit 按配置生成两种 host：`norm` mode 生成 `host + launch kernel`，`cost` mode 生成 `host call cost`；两者复用同一份 body/helper，只是 `ctx` 类型不同。`dsl_cost_run(...)` 编译并执行 cost host，从 summary string 捕获并解析指定 `cost_kind` 的 `int`。
- 当前状态：Draft 8 已执行落地；Noether / Hopper Round 6 strict review、守护最终检验、execute 三次返工、review 三次复审和 2026-06-12 archive_acceptance 均已通过；等待 merge / 归档阶段同批合入代码、spec、test、计划书和任务记录。
- 用户确认来源：
  - 用户确认当前不做跨后端 provider、真实时间统计或 calibration，只想使能 cost run。
  - 用户确认 emit 可以生成 kernel，也可以生成 host cost；它们是同一套 body/helper，区别是 `ctx` 是 cost context。
  - 用户确认 cost summary 可以作为参数或可返回结构体让 Python 捕获。
  - 用户确认可以添加 config cost mode，决定生成 `host + launch kernel` 还是生成 `host call cost`。
  - 用户确认 `set_codegen_mode/get_codegen_mode` 可以作为公开 config API，mode 值使用 `norm/cost`。
  - 用户确认不推荐 `Memory<GM, S_INT>& __kg_cost_output` 作为 cost 捕获主形态，倾向用字符串承载 summary；生成的 cost func 末尾把 cost 分析结果更新到字符串，Python 侧打印或解析该字符串。
  - 用户确认继续按本计划推荐项推进：summary string sink 采用 `std::string& __kg_cost_summary` + entry shim 内部输出缓冲 + `ExecuteResult.run_stdout`；允许 `capture_function_output=True` 在 npu_demo generated cost summary sink 场景从稳定失败变为限定成功，其他场景继续以 `function_output_capture_not_supported` 失败；新增 `npu_demo::CostSummary`、`npu_demo::CostContext`、`npu_demo::format_cost_summary`；summary string 采用单行 JSON；DMA summary 聚合采用 raw bytes 汇总后统一 `ceil(total / 64)`；`CostContext` helper 不写业务 output。
  - 用户确认按照当前新方案一次拿出所有 cost 分析，`dsl_cost_run(..., "DMA")` 已不需要；本计划删除 `"DMA"` 兼容入口，只支持 `"DMA1"` / `"DMA2"` / `"DMA3"` / `"DMA4"` / `"MAC"` / `"VECTOR1"` / `"VECTOR2"` exact kind。
  - 用户确认对于 npu demo 来讲，cost 只算第一个 block；本计划不把 `launch_block` 乘进总 cost，不把 block=2 当作 full-launch 聚合。
  - 用户确认 `CoreConfigSnapshot` 采用 B：新增尾字段 `codegen_mode: Literal["norm", "cost"] = "norm"`，`snapshot_config()` / `restore_config()` 保存和恢复该字段，同时兼容旧三字段构造。
- 目标 `spec`：
  - `spec/core/config.md`
  - `spec/dsl/gen_kernel/emit_context.md`
  - `spec/dsl/gen_kernel/gen_kernel.md`
  - `spec/execute_engine/execute_engine.md`
  - `spec/execute_engine/execute_engine_api.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/execute_engine/strategy.md`
  - `spec/tools/dsl_cost_run.md`
  - `spec/tools/dsl_run.md`
  - `spec/include/npu_demo/npu_demo.md`
  - `spec/include/api/Arch.md`
  - `spec/include/api/Kernel.md`
  - `spec/include/api/Dma.md`
  - `spec/include/api/cost/Core.md`
  - `spec/include/api/cost/Dma.md`
  - `spec/include/api/cost/Kernel.md`
- 目标 `API`：
  - 保持不变：`dsl_cost_run(func_obj, real_args, pipeline, cost_kind) -> int`
  - 已确认删除：`dsl_cost_run(..., "DMA")` 兼容 kind
  - 已确认新增：`set_codegen_mode(value: Literal["norm", "cost"]) -> None`
  - 已确认新增：`get_codegen_mode() -> Literal["norm", "cost"]`
  - 已确认变更：`CoreConfigSnapshot(target, dump_dir, trance_enabled, codegen_mode: Literal["norm", "cost"] = "norm")`
  - 已确认限定启用：`CompiledKernel.execute(..., capture_function_output=True) -> ExecuteResult` 在 npu_demo generated cost summary sink 场景返回 `run_stdout`
  - 已确认新增文件级 API：`kernel_gen.execute_engine.runtime_args.invoke_compiled_kernel_capture_output(...) -> tuple[int, str]`，不进入包根 `kernel_gen.execute_engine.__all__`
  - 已确认新增 include API：`npu_demo::CostContext` / `npu_demo::CostSummary` / `npu_demo::format_cost_summary`
- 目标 `test`：
  - `test/core/test_config.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/execute_engine/test_builtin_strategy.py`
  - `test/execute_engine/test_contract.py`
  - `test/execute_engine/test_invoke.py`
  - `test/tools/test_dsl_run.py`
  - `test/tools/test_dsl_cost_run.py`
  - `test/tools/test_package.py`
  - `test/include/api/test_arch.py`
  - `test/include/api/test_cost.py`
  - `test/include/npu_demo/test_cost.py`
  - `test/include/npu_demo/test_kernel_context.py`
  - `test/include/npu_demo/test_runtime_launch.py`
  - 待新增或更新：`test/include/npu_demo/test_cost_context.py`
- 目标 `验收资产`：
  - 当前无必过 `expectation`；本计划不修改 `expectation/`。
  - pytest 和文本门禁为 diff 反推测试。
- 目标 `功能实现`：
  - `kernel_gen/core/config.py`
  - `kernel_gen/dsl/gen_kernel/emit_context.py`
  - `kernel_gen/dsl/gen_kernel/gen_kernel.py`
  - npu_demo module / function source emitter
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/execute_engine/runtime_args.py`
  - `kernel_gen/execute_engine/builtin_strategy/common.py`
  - `kernel_gen/tools/dsl_run.py`
  - `include/npu_demo/Kernel.h`
  - `include/npu_demo/Dma.h`
  - `include/npu_demo/Arch.h`
  - `include/npu_demo/npu_demo.h`

## 计划级任务

- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`。
- 当前 Draft 8 不创建任务；下表仅为后续可下发草案。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `dsl-cost-run-cost-mode-kernel-summary` | `execute` | `/home/lfr/kernelcode_generate/wt-20260610-dsl-cost-run-cost-mode-kernel-summary` | `agents/codex-multi-agents/log/task_records/2026/24/20260610-dsl-cost-run-cost-mode-kernel-summary.md` |

## 迭代审阅记录

### 收敛轮次 1：Noether / Hopper strict review
- 审阅对象：管理员确认 Round 1 使用 Noether 与 Hopper 两路独立 Codex subagent strict review；Noether 重点看流程、公开 API、expectation 与用户确认闭环；Hopper 重点看 `dsl_cost_run` / cost mode / kernel summary 行为、测试与验收有效性；两者均按 strict 全量审阅。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、必要标准文档、本计划全文、Q1-Q8 用户确认来源、禁止修改面、公开 API / 稳定错误 / expectation 授权、必过 pytest 命令和当前 indexed 证据。
- 严格通过口径：用户确认来源不完整、公开 API 记录不闭合、任务目标不可执行、小任务卡不闭合、`_cost_*` sibling 旧路径残留、cost mode 没有由 emit 生成 host cost、summary string capture 不可验收、或任意可提升测试有效性的改进项则不通过。
- Noether 结论：不通过；阻断包括 `capture_function_output=True` 公开错误语义未闭合、DMA raw bytes 聚合单位不明确、`dsl_run` mode restore 口径冲突、稳定错误语义存在“或”式表述、`DMA` alias 兼容列表不闭合；最小需改项包括补 execute_engine contract/test、定义 DMA 计量单位和 unsupported 行为、明确 `dsl_run` snapshot restore、定义 cost host entry 命名和 CompileRequest.function 选择。
- Hopper 结论：不通过；阻断包括 summary capture 缺 exact C ABI 输出通道、DMA finalize 边界未定义、`EmitCContext` mode 查询未列公开 API、cost host entry 名未定；最小需改项包括统一 `DMA` alias、移除“返回 0 或 fail-fast”、补 include cost 与 `dsl_run` mode 测试。
- 主线处理：Draft 4 已修订为 exact capture companion ABI、`CostContext` DMA raw bytes finalize 语义、无新增 `EmitCContext` 公开方法、cost host entry 命名规则、用户确认删除 `DMA` alias、稳定错误文本和补全验收矩阵。
- 状态：Round 1 未通过，Draft 4 已按问题修订；待重新 staged 后发起 Round 2 Noether / Hopper 复审；不可下发。

### 收敛轮次 2：Noether / Hopper strict review
- 审阅对象：Noether 与 Hopper，按管理员确认复审 Draft 4 最新 indexed 对象全文 / 关键 diff；审阅时 indexed blob 为 `100644 c7d5b44565029e5c3271efe78be7011badc658ee 0 ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md`。
- 输入标准包：Round 1 标准包、Draft 4 全文 / diff、Round 1 问题与 Draft 4 主线处理摘要、Q1-Q8 用户确认来源、禁止修改面和必过 pytest 命令。
- 严格通过口径：仍有阻断、最小需改项、待确认项或可执行改进项则不通过。
- Noether 结论：不通过；阻断项为 `CostContext` fail-fast 与 C ABI 捕获链路没有闭合到稳定错误语义；最小需改项为 `EmitCContext` mode 查询表述仍有公开 API 边界歧义、S2 小任务卡把已确认 host cost 命名 / summary ABI 写成开放问题、capture overflow / missing companion / non-npu_demo 负向测试未闭合。
- Hopper 结论：不通过；阻断项无；最小需改项为 `EmitCContext` mode 口径冲突、`invoke_compiled_kernel_capture_output(...)` 作为文件级 API 的直接调用错误语义未收口、`CostSummary` / `CostContext` 非法输入行为不精确。
- 主线处理：Draft 5 已改为 emitter 直接使用公开 `get_codegen_mode()` 且 `EmitCContext` 不新增 mode API；CostContext unsupported helper / layout 统一抛出 `std::runtime_error("kg_cost_unsupported")`，entry shim / capture companion 必须 catch C++ 异常并返回非零 status；`invoke_compiled_kernel_capture_output(...)` 直接 API 明确正容量、缺 companion、nonzero status、溢出和解码失败语义；`CostSummary::value(...)` / `CostContext::add_cost(...)` 明确 invalid kind 和负值行为；S2/S3/S5/S6/S7 负向测试矩阵补齐。
- 状态：Round 2 未通过，Draft 5 已按最小项修订；待重新 staged 后发起下一轮 Noether / Hopper strict review；不可下发。

### 收敛轮次 3：Noether / Hopper strict review
- 审阅对象：Noether 与 Hopper，复审 Draft 5 最新 indexed 对象全文 / 关键 diff；审阅时 indexed blob 为 `100644 6da70b0ee800cf7f846ef1432e9fb42bf611f3ef 0 ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md`。
- 输入标准包：Round 1 / Round 2 标准包、Draft 5 全文 / diff、Round 2 问题与 Draft 5 主线处理摘要、Q1-Q8 用户确认来源、禁止修改面和必过 pytest 命令。
- 严格通过口径：仍有阻断、最小需改项、待确认项或可执行改进项则不通过。
- Noether 结论：不通过；Round 2 Noether 阻断已闭合；新增阻断为 `CoreConfigSnapshot` 公开类签名变更缺少显式用户确认闭环；最小需改项为 `format_cost_summary` 作为公开 include API 的生成路径和测试门禁仍可被“等价序列化”绕开。
- Hopper 结论：不通过；阻断为 cost-mode 对 `arch.launch` extent / active context 的语义未闭合，需用户确认是完整 launch、单次 body 还是 fail-fast。
- 主线处理：用户已确认 npu demo 只算第一个 block，Draft 6 已写入 first-block cost 语义，不做 full-launch 汇总；Draft 6 已收紧 cost host 和文本门禁，必须调用 `npu_demo::format_cost_summary(ctx.summary())`，不再允许“等价 summary string 序列化”绕过公开 formatter；用户已确认 `CoreConfigSnapshot` 采用尾字段默认值方案 B，Draft 6 已写入 Q10。
- 状态：Round 3 未通过，Draft 6 已修订 Round 3 问题并完成用户待确认项收口；待重新 staged 后发起下一轮 Noether / Hopper strict review；不可下发。

### 收敛轮次 4：Noether / Hopper strict review
- 审阅对象：Noether 与 Hopper，复审 Draft 6 最新 indexed 对象全文 / 关键 diff；审阅时 indexed blob 为 `100644 1c0c49070423ea6cd3ff57a41a3117d75aed98a8 0 ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md`。
- 输入标准包：Round 1 / Round 2 / Round 3 标准包、Draft 6 全文 / diff、Round 3 问题与 Draft 6 主线处理摘要、Q1-Q10 用户确认来源、禁止修改面和必过 pytest 命令。
- 严格通过口径：仍有阻断、最小需改项、待确认项或可执行改进项则不通过。
- Noether 结论：不通过；阻断项为 first-block cost 的 active runtime metadata 实现边界仍未闭合，计划允许复用 `npu_demo::detail` 但未把边界收进 `include/npu_demo/Arch.h` / Arch spec/test，存在 generated source 或其它 include 跨文件调用私有 detail 的风险。
- Hopper 结论：不通过；阻断项无；最小需改项为旧三字段 `CoreConfigSnapshot(...)` 兼容性缺少显式验收，以及 first-block runtime metadata 内部实现边界不够硬。
- 主线处理：Draft 7 已把 first-block active runtime 支持收口到 `include/npu_demo/Arch.h` 同文件内部 runner / runtime metadata，补入 `spec/include/api/Arch.md`、`test/include/npu_demo/test_kernel_context.py`、`test/include/npu_demo/test_runtime_launch.py`；明确 generated source、`include/npu_demo/Dma.h`、`include/npu_demo/Kernel.h` 和测试不得直接引用 `npu_demo::detail` / `ScopedActiveKernelContext`；S1 验收补旧三字段 `CoreConfigSnapshot(...)` 构造兼容测试。
- 状态：Round 4 未通过，Draft 7 已按问题修订；待重新 staged 后发起下一轮 Noether / Hopper strict review；不可下发。

### 收敛轮次 5：Noether / Hopper strict review
- 审阅对象：Noether 与 Hopper，复审 Draft 7 最新 indexed 对象全文 / 关键 diff；审阅时 indexed blob 为 `100644 660739b23cd4de7441f38fa814a227b363c1100a 0 ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md`。
- 输入标准包：Round 1 / Round 2 / Round 3 / Round 4 标准包、Draft 7 全文 / diff、Round 4 问题与 Draft 7 主线处理摘要、Q1-Q10 用户确认来源、禁止修改面和必过 pytest 命令。
- 严格通过口径：仍有阻断、最小需改项、待确认项或可执行改进项则不通过。
- Noether 结论：不通过；阻断项无；最小需改项为 `spec/include/api/Arch.md` 已进入目标 spec，但对应 `test/include/api/test_arch.py` 未进入目标 test、总体验收命令和 S4 验收命令。
- Hopper 结论：不通过；阻断项为 `Arch.h` 私有边界被写成过宽的全局 `npu_demo::detail` 禁令，会误伤 `Dma.h` / `Kernel.h` 现有同文件 detail helper；最小需改项同 Noether，要求补 `test/include/api/test_arch.py` 必过命令。
- 主线处理：Draft 8 已把禁止范围精确为 generated source 不得出现 `npu_demo::detail`，`Dma.h` / `Kernel.h` / 测试不得跨文件直接消费 `Arch.h` runtime 内部符号；明确允许 `Dma.h` / `Kernel.h` 使用本文件内 `npu_demo::detail` helper；目标 test、总体验收命令和 S4 验收命令已加入 `test/include/api/test_arch.py`。
- 状态：Round 5 未通过，Draft 8 已按问题修订；待重新 staged 后发起下一轮 Noether / Hopper strict review；不可下发。

### 收敛轮次 6：Noether / Hopper strict review
- 审阅对象：Noether 与 Hopper，复审 Draft 8 最新 indexed 对象全文 / 关键 diff。
- 输入标准包：Round 1 / Round 2 / Round 3 / Round 4 / Round 5 标准包、Draft 8 全文 / diff、Round 5 问题与 Draft 8 主线处理摘要、Q1-Q10 用户确认来源、禁止修改面和必过 pytest 命令。
- 严格通过口径：仍有阻断、最小需改项、待确认项或可执行改进项则不通过。
- Noether 结论：通过；阻断项无；最小需改项无；待确认项无。关键证据包括 indexed blob `100644 7b03377da88f22cdee3dc9ac04b2bc25b3aa4152 0`、`git diff --cached --check` 无输出、`test/include/api/test_arch.py` 已进入目标 test / 总体验收 / S4 验收、generated source 禁 `npu_demo::detail` 且 `Dma.h` / `Kernel.h` 只禁止跨文件消费 `Arch.h` runtime 内部符号、公开 API 与 Q1-Q10 均闭合、expectation 权限无问题。
- Hopper 结论：通过；阻断项无；最小需改项无；待确认项无。关键证据包括 indexed blob `100644 7b03377da88f22cdee3dc9ac04b2bc25b3aa4152 0`、Round 5 两项已闭合、`test/include/api/test_arch.py` 已进入目标 test / 总体验收 / S4 验收、`npu_demo::detail` 禁令已收窄为 generated source 禁用并允许 `Dma.h` / `Kernel.h` 同文件 detail、first-block 语义和 capture / formatter / CoreConfigSnapshot 行为均闭合。
- 主线处理：无需继续修订；Round 6 双路 strict review 已收敛。
- 状态：Round 6 通过；等待 `守护最好的爱莉希雅` 本人守护最终检验；不可下发。

### subagent 收敛结论
- 已发起或计划要求的审阅任务：Round 1 Noether / Hopper 已完成且均不通过；Round 2 Noether / Hopper 已完成且均不通过；Round 3 Noether / Hopper 已完成且均不通过；Round 4 Noether / Hopper 已完成且均不通过；Round 5 Noether / Hopper 已完成且均不通过；Round 6 Noether / Hopper 已完成且均通过。
- 收敛结论：已收敛；阻断项、最小需改项、待确认项均为无。
- 遗留项：无；等待 `守护最好的爱莉希雅` 本人守护最终检验。

### 守护最终检验
- 检验对象：`守护最好的爱莉希雅`
- 检验范围：标准包、公开 API、expectation 权限、禁止修改面、验收命令、小任务卡、`dsl_cost_run` 公开兼容性、emit cost mode 语义和 cost summary 捕获。
- 结论：2026-06-10 由 `守护最好的爱莉希雅` 本人在 clean guard worktree `/home/lfr/kernelcode_generate/wt-20260610-dsl-cost-run-cost-mode-kernel-summary-guard` 执行，结论通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 关键证据：写入本结论前，`git ls-files --stage -- ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md` 为 `100644 756226ddb4c472f522015a04701eb4c89a3a8040 0`；indexed sha256 为 `558bb5ed6f6b09ffae41d427b9fd36be47415f68111ff1e78d6008bd6eef0720`，indexed `wc -l` 为 `732`；`git diff --cached --name-status -- ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md` 为 `A`；`git status --short --ignored --untracked-files=all -- ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md` 为 `A  ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md`；`git diff --cached --check -- ARCHITECTURE/plan/dsl_cost_run_cost_mode_kernel_summary.md` 无输出；`git diff --cached --name-status -- expectation`、`git diff --name-status -- expectation` 与 `git status --short --untracked-files=no -- expectation` 均无输出；当前无必过 `expectation`。
- 是否允许管理员创建唯一计划级 `execute`：允许。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：`提莫炖蘑菇` / 2026-06-12 23:04 +0800。
- 结论：`archive_acceptance` 通过；可按计划级链路进入 `merge / 归档`，不得跳过合并记录与同批合入要求。
- 验证基线：执行目录 `/home/lfr/kernelcode_generate/wt-20260610-dsl-cost-run-cost-mode-kernel-summary`；`HEAD=20fef239299f34bbb919c31ecee4aba5fae7fdd6`，`origin/main=a82065dc065cfc14b6a45e5dcdfa11692fb43672`，`merge-base=20fef239299f34bbb919c31ecee4aba5fae7fdd6`；latest main 新增 `arch_parallelize.py` / `ircheck` 相关文件，与本候选 diff 无重叠。
- 合同验收摘要：当前无必过 `expectation`；本计划和候选 diff 均未修改 `expectation/`。入档验收已按计划正文复跑 pytest：`test/core/test_config.py` 7 passed，`test/dsl/gen_kernel/test_gen_kernel.py` 100 passed，execute_engine 组合 71 passed，tools 组合 67 passed，include / npu_demo 组合 32 passed；`99-cost-source.cpp` 文本门禁、`git diff --check`、`git diff --cached --check` 和敏感范围空 diff 均通过。
- 最小阻断项或通过摘要：无阻断项；任务记录包含 execute、三轮返工、review 复审通过、`review -> archive_acceptance` 流转补记与本次入档验收记录。merge 阶段必须同批纳入本计划书、代码 / spec / test 和任务记录，并继续排除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

## 计划目标

- 在 `kernel_gen.core.config` 中新增显式 codegen mode：`norm` / `cost`。
- gen_kernel / npu_demo emitter 通过已确认公开 `kernel_gen.core.config.get_codegen_mode()` 获取 mode；`EmitCContext` 不新增 mode 查询 API、公开属性或内部 mode 状态。
- `gen_kernel(..., EmitCContext())` 保持唯一源码生成入口，但按 mode 生成不同 host：
  - `norm` mode：生成普通 host，host 创建 `npu_demo::KernelContext`，再 `launch<..., body<..., npu_demo::KernelContext>>(ctx, args...)`。
  - `cost` mode：生成 host cost，host 创建 `npu_demo::CostContext`，按 npu demo first-block cost 语义调用 `body<..., npu_demo::CostContext>(ctx, args...)`，随后通过 `npu_demo::format_cost_summary(ctx.summary())` 序列化到 summary string。
- `dsl_run(...)` 生成/编译期间临时切到 `norm` mode，完成后 restore 调用前 config snapshot；若调用前全局 mode 是 `cost`，调用后仍恢复为 `cost`。
- `dsl_cost_run(...)` 生成/编译期间临时切到 `cost` mode，完成后 restore 调用前 config snapshot；执行 cost host 后捕获 generated cost host 写出的全量 summary string，再由 Python 解析并返回 `cost_kind` 对应 `int`。
- 保持 `dsl_cost_run(func_obj, real_args, pipeline, cost_kind) -> int` 的公开签名不变。
- 不再查找 `_cost_<kind>_*` sibling function，不再用 `tuner.cost` 或直接 `cost::` helper 作为 `dsl_cost_run` 主路径。
- 不做真实时间统计、benchmark、插值、拟合、跨后端 provider 或 per API trace。

## 当前基线

- `kernel_gen.core.config` 当前只公开 `target`、`dump_dir`、`trance_enabled`，没有 codegen mode。
- `EmitCContext()` 当前只从 `get_target()` 读取 target，不读取 mode。
- `gen_kernel(obj, ctx)` 当前按同一生成路径输出 source，不能由同一个入口选择 kernel host 或 cost host。
- `dsl_run(...)` 当前生成普通 source 并执行普通 kernel host。
- `dsl_cost_run(...)` 当前通过 `_select_source_and_cost_entry(...)` 拼出 `_cost_<kind>_<device body>`，要求 lowered module 存在对应 sibling，并仍接受 `"DMA"` 兼容 kind；本计划会删除该兼容 kind。
- 当前 `_append_cost_capture_wrapper(...)` 用 regex 找 `S_INT _cost_*` 函数，并追加 capture wrapper 把返回值写入 `Memory<GM, S_INT>`。
- 当前 `_rewrite_dma_cost_helpers_to_raw_bytes(...)` 只服务旧 sibling 源码，把 `cost::copy/slice/deslice/img2col*` 改写为 raw-bytes helper。
- 当前测试锁定“命名 npu-demo pipeline 缺 cost sibling 时失败”，这与本计划目标相反，需要改为 cost mode 正向成功。
- `include/api/Dma.h` 与 `include/api/Kernel.h` 当前已经是 context-first helper 声明形态，helper 模板末尾有 `Context`，函数首参为 `Context& ctx`。
- `include/npu_demo/Dma.h` 与 `include/npu_demo/Kernel.h` 当前 helper 对任意 `Context` 基本执行 kernel-mode 真实数据搬运 / 计算，许多实现直接 `(void)ctx`；尚未通过 `CostContext` 累计 summary。
- 当前没有 public `npu_demo::CostContext` / `CostSummary` exact API。

## 方案比较与选型

### 不采用 A：工具层在 generated source 后追加 cost capture wrapper 作为主方案
- 问题：用户已确认 emit 可以生成 kernel，也可以生成 host cost；如果工具层用字符串追加 wrapper，会绕过 emit 的结构化职责。
- 影响：容易继续依赖 C++ 文本解析，无法让生成侧测试直接锁定 cost host。

### 不采用 B：继续依赖 `_cost_<kind>_*` sibling
- 问题：旧 sibling 不是 cost mode 的 host/body/context 链路。
- 影响：与 context-first helper 和 cost context 方向分叉。

### 不采用 C：新增 `dsl_cost_trace` / provider / per API 明细
- 问题：用户已明确当前不做这件事，只想使能 cost run 并拿 summary。
- 影响：会扩大公开 API 和任务范围。

### 采用方案：config-driven emit mode + string summary sink
- `codegen_mode="norm"`：emit 生成普通 host + launch kernel。
- `codegen_mode="cost"`：emit 生成 host cost，host cost 使用 `CostContext` 调同一份 body / helper，并在函数末尾把 `ctx.summary()` 序列化成 summary string 交给 Python。
- 推荐第一阶段用 `std::string& __kg_cost_summary` 作为 generated cost host 的末尾参数；entry shim 在 C++ 侧创建本地 `std::string` 并传给 host cost，调用结束后通过执行引擎内部输出缓冲复制回 Python，最终落到现有 `ExecuteResult.run_stdout`。这里不是把 Python `str` 当作可写入参。
- `CostSummary` 保留完整字段，summary string 也保留完整字段；当前 `dsl_cost_run` 只从字符串解析一个 `cost_kind` scalar 并返回 `int`，后续如需公开完整 summary 可另立 API。

## 公开 API 设计

- 用户确认来源：用户已确认可以添加 config cost mode，决定生成 `host + launch kernel` 还是生成 `host call cost`；用户确认 `set_codegen_mode/get_codegen_mode` 可以，mode 值使用 `norm/cost`；用户确认本计划中 summary string sink、include API、JSON 格式、DMA 聚合、CostContext output 行为、`capture_function_output=True` 限定成功边界和删除 `"DMA"` kind 均采用当前方案。
- 公开 API 用户决策已收口；未完成 subagent strict review 和 `守护最好的爱莉希雅` 本人守护最终检验前不得下发 execute。

### 已确认新增：core config codegen mode

Exact API：

```python
set_codegen_mode(value: Literal["norm", "cost"]) -> None
get_codegen_mode() -> Literal["norm", "cost"]
```

推荐 `CoreConfigSnapshot` 变更：

```python
CoreConfigSnapshot(
    target: str | None,
    dump_dir: Path | None,
    trance_enabled: bool,
    codegen_mode: Literal["norm", "cost"] = "norm",
)
```

- 默认值：`"norm"`。
- `reset_config()`：恢复为 `"norm"`。
- `snapshot_config()` / `restore_config()`：必须保存和恢复 `codegen_mode`。
- 非法值错误：`codegen_mode must be 'norm' or 'cost'`。
- 约束：不新增任意 dict 配置，不给 `gen_kernel(...)` / `dsl_run(...)` / `dsl_cost_run(...)` 增加同义参数。
- 用户确认：采用 Q10 方案 B，`codegen_mode` 是尾字段且默认值为 `"norm"`；`snapshot_config()` / `restore_config()` 必须保存和恢复该字段。
- 兼容验收：`CoreConfigSnapshot(target, dump_dir, trance_enabled)` 旧三字段构造必须继续可用，并把 `codegen_mode` 置为 `"norm"`；`restore_config(old_snapshot)` 必须按 `"norm"` 恢复 mode。

### 保持不变：`dsl_cost_run`

- `dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`
- 公开行为：
  - 调用方签名不变。
  - 返回值仍是 `int`。
  - `cost_kind` 第一阶段只接受 `DMA1`、`DMA2`、`DMA3`、`DMA4`、`MAC`、`VECTOR1`、`VECTOR2` exact 列表。
  - `"DMA"` 不再是合法 `cost_kind`；非法值固定错误为 `DslCostRunInvalidCostKind: cost_kind must be one of ['DMA1', 'DMA2', 'DMA3', 'DMA4', 'MAC', 'VECTOR1', 'VECTOR2']`。
  - 第一阶段仍只支持 `target="npu_demo"`；跨 target cost mode 后续另立计划。
- 行为变化：
  - `dsl_cost_run` 内部 snapshot 当前 config，临时 `set_codegen_mode("cost")`，生成 cost source，编译后 restore 调用前 config。
  - 不再要求 lowered module 存在 `_cost_<kind>_*` sibling。
  - 不再以缺 sibling 作为命名 npu-demo pipeline 的正向失败。
  - cost host 的全量 summary string 由执行结果中的既有 `ExecuteResult.run_stdout` 字段承载；`dsl_cost_run` 内部按 `cost_kind` 解析后仍只返回 `int`。

### 启用既有执行结果字段：cost summary string capture

- 不新增 `CompiledKernel.execute(...)` 参数，不新增 `ExecuteResult` 字段，不新增包根公开入口。
- 允许 `dsl_cost_run(...)` 内部对 npu_demo generated cost host 调用使用既有 `capture_function_output=True` 语义；这是用户已确认的公开成功边界变更。
- `capture_function_output=True` 第一阶段只支持 npu_demo generated cost summary sink；CPU、CUDA SM86、第三方 target、普通 npu_demo function 或缺少 companion capture symbol 的 npu_demo function 继续以 `function_output_capture_not_supported` 失败。
- `runtime_args.py` 新增文件级 API，不进入包根导出：

```python
invoke_compiled_kernel_capture_output(
    soname_path: str,
    entry_point: str,
    args: tuple[RuntimeInput, ...],
    allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...],
    output_capacity: int = 4096,
) -> tuple[int, str]
```

- 直接调用 `invoke_compiled_kernel_capture_output(...)` 的稳定语义：
  - `output_capacity` 必须是正整数；非法值抛出 `KernelCodeError`，`failure_phrase == "runtime_throw_or_abort"`，detail 包含 `output_capacity must be positive`。
  - 直接 API 解析的 symbol 名固定为 `<entry_point>_capture`；缺少该 companion symbol 时抛出 `KernelCodeError`，`failure_phrase == "symbol_resolve_failed"`，detail 包含 `entry_point '<entry_point>_capture' is missing`。
  - companion 返回非 0 status 时，直接 API 返回 `(status_code, "")`，不尝试解析输出缓冲；`CompiledKernel.execute(..., capture_function_output=True)` 再把非 0 status 映射为 `runtime_throw_or_abort`。
  - companion 返回 0 但 `output_size >= output_capacity`、声明的 `output_size` 超出可读缓冲、或输出字节无法按 UTF-8 / ASCII 兼容文本解码时，直接 API 抛出 `KernelCodeError`，`failure_phrase == "runtime_throw_or_abort"`，detail 包含 `capture output is invalid`。
  - `CompiledKernel.execute(..., capture_function_output=True)` 只在缺 companion symbol 时把底层 `symbol_resolve_failed` 映射为 `function_output_capture_not_supported`；shared object 加载失败保留 `symbol_resolve_failed`；ABI 封送失败、输出解码失败和 companion nonzero status 映射为 `runtime_throw_or_abort`。
- companion C ABI 名称固定为 `<entry_point>_capture`；默认 entry 为 `kg_execute_entry` 时 companion 为 `kg_execute_entry_capture`。
- companion C ABI 签名固定为：

```cpp
extern "C" int kg_execute_entry_capture(
    const _ArgSlot* ordered_args,
    unsigned long long arg_count,
    char* output,
    unsigned long long output_capacity,
    unsigned long long* output_size);
```

- `output_capacity` 默认 4096 字节，summary string 必须以 UTF-8 / ASCII 兼容文本写入；`output_size` 为不含 NUL 结尾的字节数。
- companion 返回 `0` 表示成功；返回非 `0` 时由 `CompiledKernel.execute(...)` 映射为 `runtime_throw_or_abort`。
- companion symbol 缺失时，由 `CompiledKernel.execute(..., capture_function_output=True)` 映射为 `function_output_capture_not_supported`，不得泄漏 `symbol_resolve_failed`。
- summary 长度达到或超过 `output_capacity` 时 companion 返回非 `0`，最终映射为 `runtime_throw_or_abort`，`dsl_cost_run` 对外稳定转成 `DslCostRunExecutionFailed: cost summary capture failed`。
- normal entry shim 与 companion capture shim 都必须包裹 generated host 调用并捕获 `std::exception` 和未知 C++ 异常；捕获后返回非 0 status，不允许 C++ 异常跨 `extern "C"` ABI 导致进程 abort。
- 执行引擎内部 entry shim 负责：
  - 若被调用函数末尾参数是 `std::string& __kg_cost_summary`，则不把该参数计入用户 runtime args。
  - shim 本地构造 `std::string __kg_cost_summary`，传入 generated cost host。
  - generated cost host 返回后，将字符串内容复制到执行引擎内部输出缓冲。
  - Python 侧把该缓冲文本写入 `ExecuteResult.run_stdout`。
- summary string 为空、超过内部缓冲容量、或不符合解析格式时，`dsl_cost_run` 固定抛出 `DslCostRunExecutionFailed: cost summary capture failed`。

### 已确认新增：`npu_demo::CostSummary`

推荐 exact API：

```cpp
namespace npu_demo {

struct CostSummary {
    S_INT dma1 = 0;
    S_INT dma2 = 0;
    S_INT dma3 = 0;
    S_INT dma4 = 0;
    S_INT mac = 0;
    S_INT vector1 = 0;
    S_INT vector2 = 0;

    S_INT value(cost::CostKind kind) const;
};

}  // namespace npu_demo
```

- 功能说明：保存 cost mode host 一次执行中的 finalized 聚合结果。
- `value(cost::CostKind kind)` 语义：
  - `DMA1/DMA2/DMA3/DMA4` 返回对应 finalized DMA cost。
  - `MAC/VECTOR1/VECTOR2` 返回对应累加 cost。
  - `npu_demo::DMA` 在 C++ 中仍是 `CostKind::DMA1` 别名，因此 `value(npu_demo::DMA)` 与 `value(npu_demo::DMA1)` 一致；Python `dsl_cost_run(..., "DMA")` 已删除，不再暴露该别名。
  - `kind` 不是 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 时抛出 `std::invalid_argument("unsupported cost kind")`。
- 用户确认：接受本计划推荐 exact API。

### 已确认新增：`npu_demo::CostContext`

推荐 exact API：

```cpp
namespace npu_demo {

class CostContext {
public:
    CostContext() = default;

    void add_cost(cost::CostKind kind, S_INT value);
    const CostSummary& summary() const;
};

}  // namespace npu_demo
```

- 功能说明：cost-mode context；同一 generated body 用 `CostContext& ctx` 实例化时，DMA / Kernel helper 只累计 summary，不执行真实数据写回。
- `add_cost(kind, value)` 单位：
  - `kind in {DMA1, DMA2, DMA3, DMA4}` 时，`value` 必须是 raw bytes，不是 `ceil(bytes / 64)` 后的 cost。
  - `kind in {MAC, VECTOR1, VECTOR2}` 时，`value` 是已经按对应公式计算出的 cost 单位。
  - `kind` 不是 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 时抛出 `std::invalid_argument("unsupported cost kind")`。
  - `value < 0` 时抛出 `std::invalid_argument("cost value must be non-negative")`；不允许 clamp、忽略或累加负值。
- `summary()` 必须返回 finalized `CostSummary`：DMA 字段按 `ceil(total_raw_bytes / 64)` 生成，MAC / VECTOR 字段为直接累加值。
- `CostContext` 内部可维护 raw byte accumulator，但该 accumulator 不进入公开 API，不写入 `CostSummary` 字段。
- `CostContext` 路径不得调用 `npu_demo::cost::detail` 跨文件私有 helper；DMA raw bytes 计算必须在当前 helper 所在文件内使用当前公开 `Memory` / `Vector` 信息完成，或提升为同文件内部 helper。
- 用户确认：接受本计划推荐 exact API；`add_cost(...)` 保持 public method。

### 已确认新增：`npu_demo::format_cost_summary`

推荐 exact API：

```cpp
namespace npu_demo {

std::string format_cost_summary(const CostSummary& summary);

}  // namespace npu_demo
```

- 功能说明：把一次 cost mode host 的 `CostSummary` 序列化为稳定、单行、可解析 summary string。
- 固定格式：JSON object，key 固定为 `DMA1`、`DMA2`、`DMA3`、`DMA4`、`MAC`、`VECTOR1`、`VECTOR2`，value 为 finalized 整数 cost；不输出 `DMA` 聚合 key。
- 示例：`{"DMA1":0,"DMA2":0,"DMA3":0,"DMA4":0,"MAC":0,"VECTOR1":128,"VECTOR2":0}`。
- 用户确认：接受 JSON 作为第一阶段稳定格式。

## 生成形态

同一份 body：

```cpp
template <typename T, typename Context>
static void kernel_body(Context& ctx, Memory<GM, T>& out, Memory<GM, T>& lhs, Memory<GM, T>& rhs) {
    add<GM, T, T>(ctx, out, lhs, rhs);
}
```

`norm` mode 生成普通 host：

```cpp
template <typename T>
void kernel(Memory<GM, T>& out, Memory<GM, T>& lhs, Memory<GM, T>& rhs) {
    npu_demo::KernelContext ctx;
    npu_demo::launch<1, 1, 1, 0, kernel_body<T, npu_demo::KernelContext>>(ctx, out, lhs, rhs);
}
```

`cost` mode 生成 host cost：

```cpp
template <typename T>
void kernel_cost(Memory<GM, T>& out, Memory<GM, T>& lhs, Memory<GM, T>& rhs, std::string& __kg_cost_summary) {
    npu_demo::CostContext ctx;
    // For launch wrappers, cost mode executes the first block view only.
    kernel_body<T, npu_demo::CostContext>(ctx, out, lhs, rhs);
    __kg_cost_summary = npu_demo::format_cost_summary(ctx.summary());
}
```

要求：
- body/helper 是同一份；只因 `Context` 类型不同进入 norm mode 或 cost mode。
- cost mode source 必须包含 `#include <string>` 或经目标 include 间接稳定提供 `std::string`；推荐显式生成 `#include <string>`。
- cost host wrapper 名称固定为 `<norm_wrapper_name>_cost`；例如 norm wrapper 为 `kernel` 时 cost wrapper 为 `kernel_cost`。
- `dsl_cost_run` 从 lowered npu_demo wrapper `func.sym_name` 结构化推导 cost host entry：`cost_entry_name = f"{wrapper_name}_cost"`；不得通过 regex 搜索源码函数名，不得拼 `_cost_<kind>_*` sibling。
- `ExecutionEngine.compile(source=cost_source, function=cost_entry_name)` 使用该 cost host 名称；entry shim 生成普通 `kg_execute_entry` 与 companion `kg_execute_entry_capture`。
- cost host 不走 `_cost_*` sibling，不走 `tuner.cost`，不直接调用 `cost::` helper。
- npu demo cost host 第一阶段只计算第一个 block：对 `arch.launch` wrapper，执行 body 的 block 0 worker 视角，不遍历或累加其它 block，不把 `launch_block` 乘进 summary。
- first-block worker 的 active runtime metadata 必须来自原 `arch.launch`：`block_id=0`，`block_num=<launch block extent>`，`thread_id/thread_num/subthread` 按 npu demo 能力和 launch 参数配置；`thread_id()` / `thread_num()` / `block_id()` / `barrier(...)` / `get_dynamic_memory(...)` 在 cost mode 下不得读到默认空 runtime。
- first-block active runtime 支持必须在 `include/npu_demo/Arch.h` 同文件内部实现：可扩展该文件内的 launch runtime metadata / scoped active context 机制，或在该文件内新增 cost-only first-block runner；不新增 `CostContext` public launch metadata API。
- generated cost source 不得出现 `npu_demo::detail`。
- `include/npu_demo/Dma.h`、`include/npu_demo/Kernel.h` 和测试不得跨文件直接消费 `Arch.h` runtime 内部符号，包括 `ScopedActiveKernelContext`、`KernelContextRuntimeAccess`、`current_kernel_runtime`、`run_launch_worker`；允许 `Dma.h` / `Kernel.h` 使用各自文件内已有或新增的 `npu_demo::detail` helper。
- 如必须新增公开 first-block launch helper，必须重新列用户确认项。
- cost host 不应写业务 `out`；测试必须证明 output 参数保持原值。
- cost host 只在 body / helper 正常返回后写 `__kg_cost_summary`；`CostContext` helper 抛出 `std::invalid_argument` / `std::runtime_error` 或其它异常时，entry shim catch 后返回非 0 status，不能产出 partial summary。
- summary string 必须由 `npu_demo::format_cost_summary(ctx.summary())` 生成，稳定、单行、可解析，例如 `{"DMA1":0,"DMA2":0,"DMA3":0,"DMA4":0,"MAC":0,"VECTOR1":128,"VECTOR2":0}`。
- Python 侧解析 summary string 后按 `cost_kind` 返回 `int`；解析失败固定抛出 `DslCostRunExecutionFailed: cost summary capture failed`，不吞错、不默认 0。
- `99-cost-source.cpp` 仍作为 `dsl_cost_run` 的 dump 文件名，内容为 cost mode source。
- `TRANCE` 开启时仍只打印 stdout return value，不新增 `trance/summary.log` 或 block 文件。

## 完成态定义

- `dsl_run(...)` 生成/编译期间使用 `norm` mode，并在结束后恢复调用前 config snapshot；不受 `dsl_cost_run(...)` 影响，也不把调用前的 `cost` mode 强制改成 `norm`。
- `dsl_cost_run(add_kernel, real_args, "npu-demo-lowering", "VECTOR1")` 返回正向 `int`，不再因为缺 `_cost_VECTOR1_*` sibling 失败。
- `dsl_cost_run(..., "DMA")` 固定以 `DslCostRunInvalidCostKind: cost_kind must be one of ['DMA1', 'DMA2', 'DMA3', 'DMA4', 'MAC', 'VECTOR1', 'VECTOR2']` 失败。
- npu demo `arch.launch` cost mode 只算第一个 block，不按 `launch_block` 汇总所有 block；block=2 的测试必须证明 cost 没有被乘 2。
- cost mode source 中存在 `npu_demo::CostContext`、`kernel_body<..., npu_demo::CostContext>(ctx, ...)` 或 first-block cost runner 调用、以及 `npu_demo::format_cost_summary(ctx.summary())`。
- cost mode source 中不存在 `_cost_` sibling 主链路、`tuner.cost` 或直接 `cost::` helper 调用。
- cost mode 执行不会修改业务输出 memory；只写 summary string sink。
- invalid `cost_kind`、非 `npu_demo` target、cost context unsupported helper、summary string 为空 / 不可解析均按本计划定义的 exact 公开错误失败。
- npu_demo generated cost summary sink 的 `capture_function_output=True` 成功返回 `ExecuteResult.run_stdout`；CPU / CUDA SM86 / 第三方 target / 普通 npu_demo function / 缺 companion symbol 仍以 `function_output_capture_not_supported` 失败；capture overflow、输出解码失败或 companion 返回非 0 status 通过 `dsl_cost_run` 固定转为 `DslCostRunExecutionFailed: cost summary capture failed`。
- `dump_dir` 下仍写 `99-cost-source.cpp`，文件名和目录结构保持当前公开行为。

## 验收设计

- pytest / 脚本：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_config.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_invoke.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_package.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/api/test_cost.py test/include/npu_demo/test_cost.py test/include/npu_demo/test_cost_context.py test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py`
- 当前必过 expectation 合同验收：无；本计划不修改 `expectation/`。
- 文本门禁：
  - `99-cost-source.cpp` 不得出现 `_cost_VECTOR1_`、`_cost_DMA`、`tuner.cost`。
  - `99-cost-source.cpp` 必须出现 `std::string& __kg_cost_summary`、`npu_demo::CostContext`、`npu_demo::format_cost_summary(ctx.summary())`、以及 cost host 函数。
  - `99-cost-source.cpp` 必须出现 cost host entry `<wrapper>_cost`，不得出现 `_cost_<kind>_` sibling 命名。
  - block extent 为 2 的 npu demo cost source 不得出现 full-launch 汇总或 `* 2` 之类按 block 数乘 summary 的逻辑；必须能体现 first-block cost 语义。
  - `99-cost-source.cpp` 不得出现 `npu_demo::detail`、`ScopedActiveKernelContext`、`KernelContextRuntimeAccess`、`current_kernel_runtime`、`run_launch_worker` 或其它 `Arch.h` runtime 内部符号。
  - `kernel_gen/tools/dsl_run.py` 中旧 `_select_source_and_cost_entry` / `_append_cost_capture_wrapper` 若保留，必须不再作为 `dsl_cost_run` 主路径；推荐删除或改名为 cost-mode 语义。
- Diff 反推要求：执行与审查必须按实际 diff 补测试；`expectation` 若未来被授权加入，必须单列为合同验收。

## 计划内小任务

### S1. 新增 core config codegen mode
- 为什么做：用户确认通过 config cost mode 决定生成 kernel host 还是 host cost。
- 做什么：新增 `set_codegen_mode/get_codegen_mode`，扩展 snapshot/restore/reset，更新 spec/test。
- 不做什么：不新增任意 dict 配置，不给 `gen_kernel` 或 `dsl_run` 新增同义参数。
- 怎么验收：`pytest -q test/core/test_config.py` 覆盖默认 `norm`、设置 `cost`、非法值、snapshot/restore，以及旧三字段 `CoreConfigSnapshot(target, dump_dir, trance_enabled)` 构造兼容并恢复为 `norm`。
- 卡住问谁：mode 值新增或改名问用户。
- 上下文摘要：mode 必须是公开配置，不藏在工具私有状态里。
- 小任务目标：core config 能稳定控制 codegen mode。
- 非目标：不改 emit。
- 模块范围：`kernel_gen/core/config.py`、`spec/core/config.md`、`test/core/test_config.py`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：用户确认 > 本计划 > spec > pytest。
- 最小功能闭环：`set_codegen_mode("cost")` 后 `get_codegen_mode()` 返回 `"cost"`，restore 能回到原值；`reset_config()` 后返回 `"norm"`。
- 执行步骤：
  1. 扩展 config 状态和 `CoreConfigSnapshot`。
  2. 添加 setter/getter 和非法值检查。
  3. 更新 spec 与测试，显式覆盖旧三字段 `CoreConfigSnapshot(...)` 构造兼容。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_config.py`。
- 记录要求：记录公开 API 用户确认来源。

### S2. 让 gen_kernel 按 codegen mode 生成 host
- 为什么做：生成差异应在 emit 层完成，而不是工具层拼接 C++。
- 做什么：npu_demo module/function emitter 通过已确认公开 `get_codegen_mode()` 读取 mode，生成 kernel host 或 cost host。
- 不做什么：不新增 `gen_kernel(..., mode=...)` 参数，不复制第二套 emitter。
- 怎么验收：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py` 锁定同一 body 在两种 mode 下 host 不同，并覆盖 block=2 时 cost host 使用 first-block cost 语义。
- 卡住问谁：若固定 `<wrapper>_cost` 命名或 `std::string& __kg_cost_summary` + `<entry_point>_capture` ABI 与现有 wrapper 结构发生实现冲突，先问架构师；若必须改变公开 API 或 ABI，再列为用户待确认项。
- 上下文摘要：这是本计划的主结构。
- 小任务目标：公开 `gen_kernel(..., EmitCContext())` 能在 `set_codegen_mode("cost")` 后返回 host cost source。
- 非目标：不执行 source。
- 模块范围：`kernel_gen/dsl/gen_kernel/**`、`spec/dsl/gen_kernel/**`、`test/dsl/gen_kernel/**`。
- 禁止修改面：同 S1。
- 合同真源：本计划 > spec/dsl/gen_kernel > pytest。
- 最小功能闭环：一个 npu_demo add module 在 norm mode 生成 `KernelContext + launch`，在 cost mode 生成 `CostContext + first-block host cost call + summary string capture`。
- 执行步骤：
  1. 在 npu_demo host emitter 读取 `kernel_gen.core.config.get_codegen_mode()`；不新增 `EmitCContext` 公开 method 或属性。
  2. 调整 npu_demo host emitter 分支，`norm` 生成普通 host，`cost` 生成 `<wrapper>_cost` host，且对 `arch.launch` wrapper 只生成第一个 block 的 cost path。
  3. 保持 body/helper 生成共用。
  4. dump 行为按调用方控制，`gen_kernel` 不自行决定 `99-cost-source.cpp`。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py`。
- 记录要求：记录没有新增 `gen_kernel` 参数。

### S3. 增加 npu_demo CostContext / CostSummary
- 为什么做：cost host 需要一个可命名 ctx 和 summary。
- 做什么：新增 `npu_demo::CostSummary` / `npu_demo::CostContext`，并更新 include/spec/API 列表。
- 不做什么：不新增 Python trace API，不做真实计时。
- 怎么验收：`pytest -q test/include/npu_demo/test_cost_context.py` 覆盖 DMA raw bytes finalize、MAC/VECTOR 累加、kind value、初始值、invalid kind、negative value 和 `format_cost_summary(...)` 固定 JSON 输出。
- 卡住问谁：exact include API 问用户。
- 上下文摘要：这是 cost host 的 C++ 状态载体。
- 小任务目标：cost context 可累计并读取 summary。
- 非目标：不接 generated source。
- 模块范围：`include/npu_demo/**`、`spec/include/npu_demo/npu_demo.md`、相关测试。
- 禁止修改面：同 S1。
- 合同真源：用户确认 > spec/include > pytest。
- 最小功能闭环：手写 C++ test 构造 `CostContext`，对 DMA kind 调用 `add_cost(..., raw_bytes)` 后读取 finalized `summary().value(...)`，对 MAC/VECTOR kind 调用 `add_cost(..., cost)` 后读取累加值。
- 失败闭环：`summary().value(static_cast<CostKind>(...))` 与 `add_cost(static_cast<CostKind>(...), value)` 对 invalid kind 抛 `std::invalid_argument("unsupported cost kind")`；`add_cost(kind, -1)` 抛 `std::invalid_argument("cost value must be non-negative")`。
- 执行步骤：
  1. 在 include 层定义 exact API。
  2. 更新文件级 `API 列表` 和 spec。
  3. 补 include test，直接断言 `format_cost_summary(...)` 输出单行 JSON、固定 key、无 `DMA` 聚合 key。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/npu_demo/test_cost_context.py`。
- 记录要求：记录用户确认来源。

### S4. 让 npu_demo DMA / Kernel helper 支持 CostContext
- 为什么做：同一 body/helper 必须在 cost ctx 下累计 summary，而不是执行真实写回。
- 做什么：为 DMA / Kernel helper 增加明确的 `CostContext` 分派。
- 不做什么：不通过运行时能力探测选择行为，不让普通 `KernelContext` 路径改变语义。
- 怎么验收：include test 证明 `CostContext` 下 `add/slice/deslice/matmul/img2col` 累计对应 kind，DMA 多节点按 raw bytes 汇总后统一 `ceil(total/64)`，且不修改 output；arch context helper 在 first-block runtime metadata 下可读 `block_id=0` 和原 launch extent。
- 卡住问谁：某个 op 的 cost 公式不明确问用户 / 架构师。
- 上下文摘要：这是 cost mode 真正成立的关键。
- 小任务目标：覆盖 `dsl_cost_run` 现有测试涉及的 DMA / VECTOR / MAC 基础路径。
- 非目标：不覆盖未知 op，不返回真实时间。
- 模块范围：`include/npu_demo/Dma.h`、`include/npu_demo/Kernel.h`、`include/npu_demo/Arch.h`、`spec/include/api/Arch.md`、`spec/include/npu_demo/npu_demo.md`、相关 spec/test。
- 禁止修改面：同 S1。
- 合同真源：现有 `include/npu_demo/cost/*` 公式 > spec > pytest。
- 最小功能闭环：`CostContext` 调用 `add` 得到 `VECTOR1`，调用多次 `slice/deslice` 得到 finalized DMA kind，调用 `matmul` 得到 `MAC`。
- 执行步骤：
  1. 在当前 helper 所在文件内实现 CostContext raw bytes / cost 公式，避免跨文件调用 `npu_demo::cost::detail` 非公开 helper。
  2. 在 `include/npu_demo/Arch.h` 同文件内部实现 CostContext first-block active runtime 支持；generated source 不得出现 `npu_demo::detail`；`Dma.h`、`Kernel.h` 和测试不得跨文件直接消费 `Arch.h` runtime 内部符号。
  3. KernelContext 路径继续执行真实 helper。
  4. CostContext 支持路径只累计 summary 并按现有 helper 签名返回成功值。
  5. CostContext unsupported helper / unsupported layout 固定 fail-fast：抛出 `std::runtime_error("kg_cost_unsupported")`；entry shim / capture companion catch 后返回非 0 status，最终由 `dsl_cost_run` 映射为 `DslCostRunExecutionFailed: cost summary capture failed`。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/api/test_cost.py test/include/npu_demo/test_cost_context.py test/include/npu_demo/test_cost.py test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py`。
- 记录要求：记录每个 helper 的 cost kind 映射。

### S5. 让 execute_engine 捕获 cost summary string
- 为什么做：generated cost host 更新的是 C++ 字符串，Python 需要稳定拿到该字符串才能打印 / 解析。
- 做什么：在 entry shim / runtime args ABI 内部支持 `std::string& __kg_cost_summary` 末尾参数、companion capture symbol 和 `capture_function_output=True` 的 summary string capture。
- 不做什么：不新增 `CompiledKernel.execute(...)` 参数，不新增 `ExecuteResult` 字段，不让普通 `dsl_run(...)` 改行为。
- 怎么验收：execute_engine 测试能编译一个末尾 `std::string&` 的 npu_demo host，调用 `capture_function_output=True` 后 `ExecuteResult.run_stdout` 包含 JSON summary；missing companion、CPU、CUDA SM86、第三方 target 和普通 npu_demo function 仍以 `function_output_capture_not_supported` 失败；capture overflow / companion nonzero status 映射为 `runtime_throw_or_abort`。
- 卡住问谁：companion C ABI 无法在现有 ctypes 路径稳定调用时问架构师；不得自行改 `CompiledKernel.execute(...)` 签名。
- 上下文摘要：`std::string` 只存在于 C++ host / shim 内；跨 Python 边界用内部输出缓冲。
- 小任务目标：`CompiledKernel.execute(..., capture_function_output=True)` 在 npu_demo cost summary companion symbol 场景返回可解析 `run_stdout`，其他场景保留 `function_output_capture_not_supported`。
- 非目标：不把任意 C++ 函数返回值捕获泛化为新公开能力。
- 模块范围：`kernel_gen/execute_engine/compiler.py`、`kernel_gen/execute_engine/runtime_args.py`、`kernel_gen/execute_engine/builtin_strategy/common.py`、相关 spec/test。
- 禁止修改面：同 S1。
- 合同真源：用户确认 > 本计划 > `spec/execute_engine/execute_engine_api.md` > pytest。
- 最小功能闭环：entry shim 本地构造 `std::string`，调用 host cost 后通过 `<entry_point>_capture` companion ABI 把文本放入 `ExecuteResult.run_stdout`。
- 执行步骤：
  1. 扩展 npu_demo entry shim 参数解析，识别函数末尾 `std::string& __kg_cost_summary`。
  2. 该参数不计入用户 runtime args；normal entry 可本地构造并丢弃该 string，capture entry 必须复制该 string。
  3. 生成 companion symbol `<entry_point>_capture`，签名按本计划公开 API 设计固定。
  4. 新增 `invoke_compiled_kernel_capture_output(...)` 文件级 API，不修改 `invoke_compiled_kernel(...)` 现有签名和返回值。
  5. 直接 API 覆盖成功、`output_capacity <= 0`、缺 companion、companion nonzero status、overflow / invalid output decode。
  6. `CompiledKernel.execute(..., capture_function_output=True)` 在 target 非 npu_demo 或 companion symbol 缺失时保持 `function_output_capture_not_supported`。
  7. capture 成功时把缓冲文本写入 `ExecuteResult.run_stdout`；capture 非零 status 映射为 `runtime_throw_or_abort`。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_invoke.py`。
- 记录要求：记录未新增 execute_engine 包根 API，且普通 `dsl_run` 路径未变。

### S6. 将 `dsl_cost_run` 切到 cost mode source
- 为什么做：旧工具路径仍找 `_cost_*` sibling，没有使用 emit 生成的 host cost。
- 做什么：`dsl_cost_run` 临时 `set_codegen_mode("cost")`，调用 `gen_kernel` 得到 cost source，编译 cost host，执行并捕获 summary string，再解析返回 summary scalar。
- 不做什么：不改 `CompiledKernel.execute(...)` 签名或 `ExecuteResult` 返回结构，不新增 Python API。
- 怎么验收：`test/tools/test_dsl_cost_run.py` 正向 cost run 返回 int，输出 memory 不变，dump 中 `99-cost-source.cpp` 是 cost mode source，且内部 summary string 可打印 / 可解析；`cost_kind="DMA"` 按 exact invalid kind 错误失败；summary 为空 / 不可解析 / 缺 key、unsupported helper、capture overflow 或 execute nonzero 均映射为 `DslCostRunExecutionFailed: cost summary capture failed`。
- 卡住问谁：若 `<wrapper>_cost` entry 与 lowered wrapper 结构冲突，问架构师；不得回退文本 regex 猜测。
- 上下文摘要：这是工具入口的核心改造。
- 小任务目标：`dsl_cost_run` 不依赖 cost sibling，也不 fallback 普通 kernel。
- 非目标：不做跨 target。
- 模块范围：`kernel_gen/tools/dsl_run.py`、`kernel_gen/execute_engine/**` 中 S5 已定义的内部 string capture 支持、相关 tests。
- 禁止修改面：同 S1。
- 合同真源：`spec/tools/dsl_cost_run.md` > pytest > 当前实现。
- 最小功能闭环：npu-demo add kernel 的 VECTOR1 cost run 成功；block=2 用例返回 first-block cost，不返回 full-launch 两倍 cost。
- 执行步骤：
  1. 保持 real args / pipeline 绑定规则不变。
  2. 生成 source 前 snapshot config，临时 `set_codegen_mode("cost")`，完成后 restore。
  3. 调用 `gen_kernel(module, EmitCContext())` 生成 cost source，并按 lowered wrapper 名结构化推导 `cost_entry_name = f"{wrapper_name}_cost"`。
  4. 将 cost source 写入 `dump_dir/<kernel>/99-cost-source.cpp`，不破坏普通 `source.cpp`。
  5. 编译 cost host entry，调用 `compiled_kernel.execute(args=execute_args, capture_function_output=True)`。
  6. 从 `ExecuteResult.run_stdout` 读取 summary string，解析 `cost_kind` 对应数值。
  7. `execute_result.ok` 为假、execute 抛错、summary string 为空 / 不可解析 / 缺 key 时，固定转为 `DslCostRunExecutionFailed: cost summary capture failed`。
  8. 对 npu demo `arch.launch`，按用户确认只统计第一个 block；不得乘以 block extent。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_package.py`。
- 记录要求：记录删除 / 停用旧 sibling 主路径的证据。

### S7. 更新测试与文本门禁
- 为什么做：旧测试把缺 sibling 失败作为目标，必须改成 cost mode 正向闭环。
- 做什么：更新 `test/tools/test_dsl_cost_run.py`、dump / trance 相关测试和 generated source 文本门禁。
- 不做什么：不新增 expectation。
- 怎么验收：完整 pytest 命令通过，且有反例证明 `_cost_*` sibling 缺失不阻断命名 pipeline。
- 卡住问谁：测试与公开 spec 冲突问架构师。
- 上下文摘要：防止实现只绕过错误而没有真正走 emit cost mode。
- 小任务目标：测试能挡住“仍然找 sibling”“普通 kernel 写输出”“summary string 未捕获 / 不可解析”“mode 泄漏”“`DMA` alias 未删除”五类失败。
- 非目标：不测真实时间。
- 模块范围：`test/tools/**`、`test/include/**`、`test/dsl/gen_kernel/**`。
- 禁止修改面：同 S1。
- 合同真源：spec > pytest。
- 最小功能闭环：正向、负向、dump、trance、mode restore 均覆盖。
- 执行步骤：
  1. 把 missing sibling tests 改为 cost-mode success 或 custom unsupported 负向。
  2. 增加 output unchanged assertion。
  3. 增加 `99-cost-source.cpp` 文本门禁和 summary string 解析断言。
  4. 增加 `dsl_run` / `dsl_cost_run` 对调用前 config snapshot 的 restore 测试，包括调用前 mode 为 `cost` 的场景。
  5. 增加 `cost_kind="DMA"` invalid kind 测试，保留其他 invalid kind / non-npu target / real_args 校验测试。
  6. 增加 missing companion、capture overflow、CUDA SM86 / third-party target capture unsupported、CostContext invalid kind / negative value、unsupported helper fail-fast 测试。
  7. 增加 npu demo block=2 first-block cost 测试，证明 cost 不乘 block 数，同时 active runtime metadata 可用。
  8. 增加 generated cost source 文本门禁，禁止 `npu_demo::detail`、`ScopedActiveKernelContext`、`KernelContextRuntimeAccess`、`current_kernel_runtime`、`run_launch_worker` 出现在 `99-cost-source.cpp`。
- 验收必过项目：本计划 `验收设计` 中 pytest。
- 记录要求：记录 diff 反推测试。

## 非目标

- 不新增 `dsl_cost_trace`、`CostReport` 或每 API 明细公开入口。
- 不做任意后端 provider 抽象。
- 不做真实时间统计、CUDA event、benchmark、插值、拟合或 calibrated time。
- 不运行普通 kernel 来推 cost。
- 不修改 `expectation/`。
- 不改变 `dsl_run(...)` 公开行为。
- 不支持非 `npu_demo` target；跨 target cost mode 后续另立计划。

## 计划自检与返工口径

- 自检：
  - `dsl_cost_run` Python API 不变。
  - `set_codegen_mode/get_codegen_mode` 和 `norm/cost` mode 值已获用户确认。
  - `CostContext` / `CostSummary` / `format_cost_summary` include API 与 summary string sink exact ABI 已获用户确认。
  - `capture_function_output=True` 在 npu_demo generated cost summary sink 场景限定成功、其它场景保持 `function_output_capture_not_supported` 已获用户确认。
  - `dsl_cost_run(..., "DMA")` 删除已获用户确认，invalid kind 错误文本已固定。
  - npu demo cost 只算第一个 block 已获用户确认。
  - 生成差异由 emit mode 承接，不再由工具层拼接 wrapper 作为主方案。
  - 旧 `_cost_*` sibling 主路径已列为必须删除 / 停用。
  - cost mode 必须由 emit 生成 host cost，并捕获 summary string。
  - summary string 捕获 / 解析、output unchanged、mode restore 和 dump 文本门禁均有测试。
  - `CoreConfigSnapshot` 尾字段默认值方案 B 已获用户确认。
  - Round 1 / Round 2 / Round 3 / Round 4 / Round 5 subagent strict review 已完成且均不通过；Round 6 Noether / Hopper strict review 已完成且均通过；Draft 8 已完成 subagent 收敛，尚待守护最终检验。
- 返工口径：只要仍有 `_cost_*` 依赖、工具层字符串追加主路径、普通 kernel 写输出、mode 泄漏、summary string 不可验证、公开 API 记录不完整或测试不能挡住旧路径，就回到计划修订或 execute 返工。

## 用户决策项

### Q1. codegen mode exact API 名称
- 结论：已确认。
- 用户确认：`set_codegen_mode/get_codegen_mode` 可以，mode 值使用 `norm/cost`。
- 落地：写入 `spec/core/config.md`，默认值为 `"norm"`，非法值错误为 `codegen_mode must be 'norm' or 'cost'`。

### Q2. cost host summary string exact ABI
- 结论：已确认采用推荐项。
- 用户方向：不采用 `Memory<GM, S_INT>& __kg_cost_output` 作为主捕获方式；生成的 cost func 末尾更新字符串，Python 侧打印 / 解析。
- 推荐项：generated cost host 末尾参数为 `std::string& __kg_cost_summary`；entry shim 本地创建 `std::string` 并传入 host cost，调用结束后通过 `<entry_point>_capture` companion C ABI 输出缓冲复制回 Python，写入既有 `ExecuteResult.run_stdout`；Python 调用者不直接传可变 `str`。
- 备选 A：`char* buffer, size_t capacity, size_t* written`。
  - 影响：C ABI 更稳，但 generated signature 更重，且要处理容量不足。
- 备选 B：host cost 返回 `std::string` 或 `CostSummary`。
  - 影响：需要执行引擎捕获 C++ 返回值或新增 shim 行为，范围更大。

### Q3. 是否确认新增 `npu_demo::CostSummary`
- 结论：已确认采用推荐项。
- 推荐项：确认本计划中的 exact API。
- 影响：host cost 可稳定读取 summary。

### Q4. 是否确认新增 `npu_demo::CostContext`
- 结论：已确认采用推荐项。
- 推荐项：确认本计划中的 exact API：默认构造、`add_cost(...)`、`summary() const`。
- 影响：host cost 可实际调用 `body<..., npu_demo::CostContext>`。
- 备选：只公开 `summary()`，通过 `detail::CostContextAccess` 让 helper 记录 cost。影响是 public method 更少，但实现更复杂。

### Q5. 是否确认新增 `npu_demo::format_cost_summary`
- 结论：已确认采用推荐项。
- 推荐项：确认本计划中的 exact API：`std::string format_cost_summary(const CostSummary& summary)`，输出单行 JSON object。
- 影响：generated cost host 可以把 summary 稳定转成 Python 可打印 / 可解析文本。
- 备选：把格式化做成 `CostSummary::to_string() const`。
  - 影响：接口更少，但 `CostSummary` 从纯数据结构变成带序列化行为的类型。

### Q6. DMA summary 聚合语义
- 结论：已确认采用选项 A。
- 选项 A：保持当前 `dsl_cost_run` DMA 聚合语义：同一 cost run 内先聚合 raw bytes，再 `ceil(total / 64)`。
  - 推荐：选择 A，兼容旧工具合同。
- 选项 B：每个 DMA helper 节点各自 `ceil(bytes / 64)` 后再求和。
  - 影响：和旧 `dsl_cost_run` DMA wrapper 语义可能不一致。

### Q7. `CostContext` 下 helper 是否允许修改业务输出
- 结论：已确认采用推荐项。
- 推荐项：不允许；cost mode helper 只累计 summary，不写业务 output。
- 影响：测试可明确证明 cost run 不等同普通 kernel run。

### Q8. 是否保留 `dsl_cost_run(..., "DMA")`
- 结论：已确认删除。
- 用户确认：按照当前新方案，一次拿出所有 cost 分析，`dsl_cost_run(..., "DMA")` 已不需要。
- 落地：`VALID_DSL_COST_KINDS` 只保留 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2`；`"DMA"` 固定按 invalid kind 错误失败。

### Q9. npu demo cost 是否按完整 launch block 汇总
- 结论：已确认只算第一个 block。
- 用户确认：对于 npu demo 来讲，是只算第一个 block。
- 落地：cost mode 对 `arch.launch` wrapper 只执行 block 0 worker 视角，不遍历或累加其它 block，不把 `launch_block` 乘进 summary；block=2 测试必须证明 cost 没有翻倍。
- 影响：第一阶段结果是 npu demo first-block cost，不是 full-launch aggregate cost；后续若要按完整 launch 汇总需另立计划或重新确认。

### Q10. `CoreConfigSnapshot` exact 签名
- 结论：已确认采用方案 B。
- 用户确认：`CoreConfigSnapshot B`。
- 方案 B：`CoreConfigSnapshot(target, dump_dir, trance_enabled, codegen_mode: Literal["norm", "cost"] = "norm")`。
- 落地：新增尾字段 `codegen_mode` 且默认值为 `"norm"`；`snapshot_config()` / `restore_config()` 必须保存和恢复该字段；`reset_config()` 后 mode 为 `"norm"`。
- 影响：公开状态完整，同时旧三字段构造调用更容易兼容。

## 用户确认与协同约束

- 用户已确认事项：
  - 当前只做 `cost run`。
  - emit 可以生成 kernel host，也可以生成 host cost。
  - 两者是同一 body/helper，区别是 cost mode 的 `ctx` 是 cost context。
  - 可以通过 config cost mode 决定生成 `host + launch kernel` 还是 `host call cost`。
  - `set_codegen_mode/get_codegen_mode` 可以作为公开 config API，mode 值使用 `norm/cost`。
  - Python 需要捕获 cost summary string，并能打印或解析。
  - 不采用 `Memory<GM, S_INT>& __kg_cost_output` 作为主捕获方式；生成的 cost func 末尾更新字符串。
  - `dsl_cost_run(..., "DMA")` 已不需要，按当前新方案删除。
  - npu demo cost 只算第一个 block。
  - `CoreConfigSnapshot` 采用尾字段默认值方案 B。
  - 不做跨后端 provider、真实时间统计或 calibration。
- 待用户确认项：
  - 无；Q1-Q10 均已按用户确认收口。
- 协同约束：
  - Noether / Hopper Round 6 subagent strict review 已收敛，且 `守护最好的爱莉希雅` 本人守护最终检验已通过；可通知管理员创建唯一计划级 `execute`。
  - 若确认新增公开 API，计划正文必须记录用户确认来源，并补 strict review。
  - 不得修改 `expectation/`，除非用户后续明确授权。
