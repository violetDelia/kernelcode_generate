# Tuner Select Pattern Enum Default Selector Plan Draft 8

## 文档信息

- 状态：Draft 8；已完成 subagent strict review 收敛、守护最终检验、既有唯一 execute 恢复、execute、review 与 2026-06-13 入档验收，当前可进入 `merge/归档`。用户在 Draft 6 execute 暂停后明确修正核心口径：生成代码中需要一个 `enum class` 表示 pattern，`tuner.select` 先只是一个 selector function，跟旧占位行为一致返回默认 `pattern0`；本计划不在当前阶段生成 runtime `CostContext` 评估、`candidate_cost`、`best_cost` 或 `data_movement / compute` cost 选择逻辑。Draft 6 的 runtime cost-driven selector 合同、相关 strict review 与守护通过证据均作废，不得用于恢复 execute。Round 8-A / 8-B、Round 9-A / 9-B、Round 10-A、Round 11-A / 11-B、Round 12-A 与 Round 13-B strict review 均不通过；Round 10-B / 12-B / 13-A / 14-A / 14-B 通过。Draft 8 已按主线处理 exact naming 不一致、expectation 证明力、负例矩阵、任务目标措辞、小任务卡最小功能闭环、错误语义用户确认来源、selector 返回变量绑定、互斥分支链、selector 参数精确来源、默认值合同、pipeline handoff 节点、enum 精确数量、完整 enum member 列表和二路 launch 数量问题；任务记录已补齐守护通过、expectation 重物化、execute、review 与入档验收证据。
- 现有唯一计划级任务：`T-20260613-ad9fdae1 / tuner-select-runtime-cost-choice`。该任务已按 Draft 8 恢复并完成 execute、review 与入档验收；后续只允许按标准链路进入 `merge/归档`，不创建第二个 execute。
- 用户确认来源：
  - 用户确认 pattern 不一定只有两个，可能有很多候选；本计划继续要求 N 路 pattern 列表和 N 路 dispatcher 不写死二路。
  - 用户确认 `tuner.select` 需要 `args=()` 与 `tuner_args`，因为不是所有参数都需要参与选择相关 state；本计划继续保留 dialect 层 `args / tuner_args` 公开合同。
  - 用户在 C8 错误判定讨论中确认采用必要检查版口径，并指出检查不要过严；本计划只锁必要失败类别与稳定关键词，不锁完整错误文本。
  - 用户新确认：“代码中会有一个枚举类表示对应的 pattern”；“select 就是一个 func，返回默认 pattern0”。本 Draft 8 以此替换 Draft 6 的 runtime CostContext 选择方案。
  - 用户指出 tuner 计划需要补齐 expectation；本 Draft 8 继续使用 5 个 local-only expectation leaf，但将 `dsl/gen_kernel/tuner_emit.py` 和 `outline_device_kernel/tuner_launch.py` 合同改为 enum + default selector，不再锁 runtime cost selector。
- 目标 `spec`：
  - [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
  - [`spec/pass/tuning/kernel_pattern_attach.md`](../../spec/pass/tuning/kernel_pattern_attach.md)
  - [`spec/pass/tuning/outline_device_kernel.md`](../../spec/pass/tuning/outline_device_kernel.md)
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../spec/dsl/gen_kernel/gen_kernel.md)
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
- 目标公开 `API` / 公开输出合同：
  - 确认变更：`class TunerSelectOp(patterns: Sequence[str | SymbolRefAttr], result_type: Attribute = SymbolValueType.from_expr("pattern_id"), *, args: Sequence[SSAValue | Operation] = (), tuner_args: Sequence[SSAValue | Operation] = ())`
  - 保持不变：`class TunerLaunchOp(callee: str | SymbolRefAttr, args: Sequence[SSAValue | Operation] = ())`
  - 确认 IR 合同：`tuner.select` 的 canonical printer 只打印非空 operand 组；两组都空时保留旧式短语法；只有 `args` 非空时只打印 `args(...) : args(...) -> result`；只有 `tuner_args` 非空时只打印 `tuner_args(...) : tuner_args(...) -> result`；两组都非空时同时打印两组。
  - 确认 npu_demo source 合同：entry dispatcher module 路径生成 entry 级 pattern enum 和 selector function。selector function 返回 enum 类型，首版函数体固定 `return <EntryPatternEnum>::pattern0;`。host dispatcher 使用 selector 返回值做 N 路真实 `KernelContext` branch。
- 目标 `test`：
  - [`test/dialect/tuner/test_tuner.py`](../../test/dialect/tuner/test_tuner.py)
  - [`test/passes/tuning/test_kernel_pattern_attach.py`](../../test/passes/tuning/test_kernel_pattern_attach.py)
  - [`test/passes/tuning/test_outline_device_kernel.py`](../../test/passes/tuning/test_outline_device_kernel.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../test/dsl/gen_kernel/test_gen_kernel.py)
  - [`test/passes/pipeline/test_npu_demo_lowering.py`](../../test/passes/pipeline/test_npu_demo_lowering.py)
- 目标 `验收资产`：
  - 授权 scope：仅限 tuner enum/default selector 直接相关的 local-only expectation leaf：`expectation/dialect/tuner/operation/select.py`、`expectation/dsl/gen_kernel/tuner_emit.py`、`expectation/pass/kernel_pattern_attach/basic.py`、`expectation/pass/outline_device_kernel/tuner_launch.py`、`expectation/pass/pipeline/npu_demo_lowering.py`；目录聚合入口不作为当前必过合同入口，不得为本计划改写 discovery 范围。
  - 合同目标：锁定 `TunerSelectOp` 新公开 API、四种 canonical syntax 且空组不打印、`kernel-pattern-attach` 默认 `args` 透传且空 `tuner_args` 不打印、`tuner.launch -> arch.launch` outline、npu_demo pattern enum、selector function 默认返回 `pattern0`、N 路 dispatcher 和单真实 `KernelContext` launch。
  - 必过入口：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dialect/tuner/operation/select.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/kernel_pattern_attach/basic.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/outline_device_kernel/tuner_launch.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/gen_kernel/tuner_emit.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/pipeline/npu_demo_lowering.py`
  - 权限边界：`expectation/` 是 ignored local-only 合同资产，不进入 staged diff、merge candidate 或远程提交；执行、审查、合并、管理员和替补角色只能读取、运行、引用和记录，不能修改、新建、移动、删除或重命名 `expectation/` 本体。scope 内 expectation 本体由架构师按本计划授权在恢复 execute 前物化到目标 worktree 并记录 manifest/hash。
- 目标 `功能实现`：
  - [`kernel_gen/dialect/tuner/operation/select.py`](../../kernel_gen/dialect/tuner/operation/select.py)
  - [`kernel_gen/passes/tuning/kernel_pattern_attach.py`](../../kernel_gen/passes/tuning/kernel_pattern_attach.py)
  - [`kernel_gen/passes/tuning/outline_device_kernel.py`](../../kernel_gen/passes/tuning/outline_device_kernel.py)
  - [`kernel_gen/dsl/gen_kernel/kernel_emitter.py`](../../kernel_gen/dsl/gen_kernel/kernel_emitter.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/select.py`](../../kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/select.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/control_flow.py`](../../kernel_gen/dsl/gen_kernel/emit/npu_demo/control_flow.py)

## 计划级任务

- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`。
- 当前处理：既有 execute 已按 Draft 8 恢复并完成，review 与入档验收通过；下一步按标准脚本进入 `merge/归档`，不创建第二个 execute。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `tuner-select-runtime-cost-choice` | `execute` | `/home/lfr/kernelcode_generate/wt-20260613-tuner-select-runtime-cost-choice` | `agents/codex-multi-agents/log/task_records/2026/24/20260613-tuner-select-runtime-cost-choice.md` |

任务目标：按 Draft 8 完成 `tuner.select` N 路 enum/default selector 能力：扩展 `TunerSelectOp` 的 `args / tuner_args` IR 合同；生成 entry 级 pattern enum 与 selector function，selector 默认返回 `pattern0`；host dispatcher 按 enum 值只 launch 一个真实 `KernelContext` pattern；同步更新公开 spec、实现和 pytest；只运行、引用并记录 local-only expectation 合同验收、验收记录与边界门禁，不修改 expectation 本体。

## 迭代审阅记录

### 历史记录摘要
- Draft 0-6 围绕 runtime cost-driven selector 完成多轮 subagent strict review 和 Draft 6 守护最终检验，但用户随后明确改口径为 enum + selector function 默认 `pattern0`。因此 Draft 6 的 runtime CostContext 方案、S4 cost selector 任务卡、C3/C6/C7 cost 相关确认、Round 7 通过结论和守护通过结论均不再作为当前可恢复 execute 的依据。
- Draft 8 是新的正式候选文本；必须重新执行至少两路 subagent strict review，所有阻断、最小需改项和待确认项收口后，再请求 `守护最好的爱莉希雅` 本人守护最终检验。

### 收敛轮次 8-A：Cicero strict review
- 审阅对象：`Cicero / 019ebf27-f887-7122-8c0d-4afadf3c9be8`。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、Draft 7 全文、用户最新确认、暂停的唯一 execute、禁止修改面和必过验收命令。
- 严格通过口径：仍有任何影响 enum/default selector 公开输出合同、`args/tuner_args` IR 合同、N 路 dispatcher、expectation 权限、任务卡可落地性、暂停 execute 恢复边界或用户确认完整性的可执行改进项，则不通过。
- 结论：不通过。
- 发现问题：
  - 计划把 enum/function 命名写成“推荐”，但 expectation 锁死 `MatmulEntryPattern` / `select_matmul_entry_pattern`，公开输出合同不一致。
  - 无 `tuner_args` case 没有断言 selector function 无业务参数，也没有禁止把 `args` 自动传给 selector。
  - N=3 dispatcher expectation 没有直接锁 enum comparison branch 结构，可能放过无条件串行 launch。
  - `tuner_args` selector case 的 forbidden snippets 少了 `data_movement_cost` / `compute_cost`。
- 主线处理：
  - Draft 8 明确 exact enum/function name 不作为当前稳定输出合同，expectation 改为 regex 抽取 enum 与 selector 名后验证结构。
  - Draft 8 强化 `tuner_emit.py`：空 `tuner_args` selector 必须无业务参数，禁止传 `arg0`；N=3 断言每个 pattern enum comparison branch 与三次真实 launch；`tuner_args` case 补齐全部 cost forbidden snippets。
- 状态：Round 8-A 未通过，Draft 8 已按主线修订；需重新 strict review。

### 收敛轮次 8-B：Meitner strict review
- 审阅对象：`Meitner / 019ebf27-f98d-7811-90e2-dc485caada4f`。
- 输入标准包：同 8-A。
- 严格通过口径：同 8-A。
- 结论：不通过。
- 发现问题：
  - exact enum/function name 与 exact error text 缺用户确认或 expectation 应放松为语义匹配。
  - S5 声明端到端 enum/default selector path，但 pipeline expectation 只锁 pass 顺序，证明力不足。
  - `args/tuner_args` verifier 反例矩阵缺 `args` 同数量错类型和 `tuner_args` 数量不匹配。
  - 任务目标写“同步更新 local-only expectation 合同验收”，容易和 execute 不得修改 expectation 边界冲突。
  - S1-S5 缺显式 `最小功能闭环`。
- 主线处理：
  - Draft 8 把 exact enum/function name 移出稳定输出合同；错误文本改为只锁稳定关键词，不锁完整句子，并记录用户已确认必要检查版错误语义。
  - Draft 8 将 S5 合同表述收窄为 pass-order handoff，端到端 source path 由 S4 pytest 和 `tuner_emit` leaf 承接。
  - Draft 8 补齐 `args` 同数量错类型、`tuner_args` 数量不匹配两条 expectation 负例。
  - Draft 8 将任务目标改为“运行并记录 local-only expectation 合同验收”，并给 S1-S5 补 `最小功能闭环`。
- 状态：Round 8-B 未通过，Draft 8 已按主线修订；需重新 strict review。

### 收敛轮次 9-A：Cicero strict review
- 审阅对象：`Cicero / 019ebf27-f887-7122-8c0d-4afadf3c9be8`。
- 输入标准包：基于 Draft 8 staged blob `a6e42552520dcffd09168e87615cff0c652521bc`、Round 8-A / 8-B 阻断与主线处理、用户确认项、禁止修改面、5 个 local-only expectation manifest 和必过验收命令。
- 严格通过口径：仍有任何影响 enum/default selector 公开输出合同、args/tuner_args IR 合同、N 路 dispatcher、expectation 权限、任务卡可落地性、暂停 execute 恢复边界、公开 API、验收资产或用户确认完整性的可执行改进项，则不通过。
- 结论：不通过。
- 发现问题：
  - `expectation/dsl/gen_kernel/tuner_emit.py` 只用 `selector_name()` 文本断言 selector 调用，可能被 selector function 定义本身满足，无法证明 dispatcher 实际调用 selector。
  - N=3 branch 断言只检查 callee 存在，没有把 pattern0 / pattern1 enum 条件与对应 launch 绑定，也没有证明 pattern2 在最终真实 launch 分支中。
- 主线处理：
  - `tuner_emit.py` 新增轻量 C++ brace 结构解析，抽取 `matmul_entry` dispatcher body 后检查 selector call。
  - `tuner_emit.py` 新增 enum 条件分支 body 断言与 final branch 断言，绑定 pattern0 / pattern1 / pattern2 对应 launch，并保留 exactly three launch 检查。
- 状态：Round 9-A 未通过，已按主线修订；需基于最新文本重新 strict review。

### 收敛轮次 9-B：Meitner strict review
- 审阅对象：`Meitner / 019ebf27-f98d-7811-90e2-dc485caada4f`。
- 输入标准包：同 9-A。
- 严格通过口径：同 9-A。
- 结论：不通过。
- 发现问题：
  - `tuner_emit.py` selector call 与 branch body 证明力不足，同 9-A。
  - 计划正文写了必要检查版稳定错误语义已由用户确认，但“用户确认来源”段未显式记录 C8 来源；公开错误语义属于公开 API，需补来源或列待确认。
- 主线处理：
  - `tuner_emit.py` 证明力按 9-A 主线修订。
  - `文档信息 / 用户确认来源` 与 `用户确认与协同约束` 补写 C8：用户确认采用必要检查版错误语义，只锁必要失败类别和稳定关键词，不锁完整错误文本。
- 状态：Round 9-B 未通过，已按主线修订；需基于最新文本重新 strict review。

### 收敛轮次 10-A：Cicero strict review
- 审阅对象：`Cicero / 019ebf27-f887-7122-8c0d-4afadf3c9be8`。
- 输入标准包：基于 Draft 8 最新 staged 文本、Round 9-A / 9-B 阻断与主线处理、用户确认项、禁止修改面、5 个 local-only expectation manifest 和必过验收命令。
- 严格通过口径：仍有任何影响 enum/default selector 公开输出合同、args/tuner_args IR 合同、N 路 dispatcher、expectation 权限、任务卡可落地性、暂停 execute 恢复边界、公开 API、验收资产或用户确认完整性的可执行改进项，则不通过。
- 结论：不通过。
- 发现问题：
  - `tuner_emit.py` 虽已检查 dispatcher body 中存在 selector call 与 enum branch，但没有绑定 selector 返回变量和后续 enum comparison；unused selector call 加常量 enum comparison 仍可能通过。
  - branch-local `npu_demo::KernelContext` 未与对应 launch 绑定到同一分支体内，只靠全局计数证明力不足。
  - S5 pipeline handoff 文本漏写 `attach-arch-information`，与 `expectation/pass/pipeline/npu_demo_lowering.py` 锁定顺序不一致。
- 主线处理：
  - `tuner_emit.py` 新增 selector binding 解析，要求 dispatcher 出现 `<Enum> <pattern_var> = <selector>(...)`，并要求 pattern0 / pattern1 条件使用同一 `<pattern_var>` 与 enum enumerator 比较；pattern2 若为显式分支同样绑定变量，若为 final else 则由前序同变量条件链推出。
  - `tuner_emit.py` 的 branch helper 要求对应分支体内同时出现 `npu_demo::KernelContext` 与对应 launch callee。
  - S5 的 `做什么` 与 `最小功能闭环` 均补齐 `attach-arch-information` 节点。
- 状态：Round 10-A 未通过，已按主线修订；需基于最新文本重新 strict review。

### 收敛轮次 10-B：Meitner strict review
- 审阅对象：`Meitner / 019ebf27-f98d-7811-90e2-dc485caada4f`。
- 输入标准包：同 10-A。
- 严格通过口径：同 10-A。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 是否需要用户确认：不需要。
- 是否可请求守护最终检验：可在 Round 10-A / 10-B 结果写回并收口“待发起 / 未收敛”状态后请求；但因 Round 10-A 不通过，本轮未满足守护前置。
- 状态：Round 10-B 通过，但本轮整体未收敛；需基于 10-A 修订后的最新文本重新 strict review。

### 收敛轮次 11-A：Cicero strict review
- 审阅对象：`Cicero / 019ebf27-f887-7122-8c0d-4afadf3c9be8`。
- 输入标准包：基于 Draft 8 最新 staged 文本、Round 10-A / 10-B 阻断与主线处理、用户确认项、禁止修改面、5 个 local-only expectation manifest 和必过验收命令。
- 严格通过口径：仍有任何影响 enum/default selector 公开输出合同、args/tuner_args IR 合同、N 路 dispatcher、expectation 权限、任务卡可落地性、暂停 execute 恢复边界、公开 API、验收资产或用户确认完整性的可执行改进项，则不通过。
- 结论：不通过。
- 发现问题：
  - N 路 dispatcher 仍未证明“只 launch 被选中的一个真实 branch”；独立 `if pattern0 {launch0}; if pattern1 {launch1} else {launch2}` 仍可能通过。
- 主线处理：
  - `tuner_emit.py` 删除旧独立分支 helper，新增互斥链解析：pattern0 条件分支必须紧跟 `else`，其 else 承接 pattern1，pattern1 的 else / 显式末路承接 pattern2。
  - 互斥链 helper 继续要求 selector 返回变量参与每个 enum comparison，且每个分支体内同时包含 `npu_demo::KernelContext` 与对应 launch callee。
- 状态：Round 11-A 未通过，已按主线修订；需基于最新文本重新 strict review。

### 收敛轮次 11-B：Meitner strict review
- 审阅对象：`Meitner / 019ebf27-f98d-7811-90e2-dc485caada4f`。
- 输入标准包：同 11-A。
- 严格通过口径：同 11-A。
- 结论：不通过。
- 发现问题：
  - final branch 检查未证明 `else` 属于同一条 `pattern_var` 条件链。
  - selector 参数只做包含式检查，未拒绝额外非 `tuner_args` 参数。
  - `expectation/dialect/tuner/operation/select.py` 未断言 `args` / `tuner_args` 默认值为 `()`。
- 主线处理：
  - final branch 已纳入 11-A 的互斥链结构解析。
  - `tuner_emit.py` 新增 selector function 参数名解析，空 `tuner_args` 必须为 `[]`，`tuner_args(%tile)` 必须精确为 `["tile"]`。
  - `select.py` signature positive case 补 `parameters["args"].default == ()` 与 `parameters["tuner_args"].default == ()`。
- 状态：Round 11-B 未通过，已按主线修订；需基于最新文本重新 strict review。

### 收敛轮次 12-A：Cicero strict review
- 审阅对象：`Cicero / 019ebf27-f887-7122-8c0d-4afadf3c9be8`。
- 输入标准包：基于 Draft 8 最新 staged 文本、Round 11-A / 11-B 阻断与主线处理、用户确认项、禁止修改面、5 个 local-only expectation manifest 和必过验收命令。
- 严格通过口径：仍有任何影响 enum/default selector 公开输出合同、args/tuner_args IR 合同、N 路 dispatcher、expectation 权限、任务卡可落地性、暂停 execute 恢复边界、公开 API、验收资产或用户确认完整性的可执行改进项，则不通过。
- 结论：不通过。
- 发现问题：
  - `tuner_args` source case 虽验证二路互斥链，但没有断言 exactly 2 real launch，可能放过额外无条件 launch。
  - `_extract_pattern_enum(... expected_patterns=N)` 只检查 `pattern0..pattern{N-1}` 存在，没有拒绝额外 enumerator，可能放过源码 enum 与输入 patterns 数量不一致。
- 主线处理：
  - `tuner_emit.py` 的 `tuner_args` case 补 `source.count("npu_demo::launch<") == 2` 与 `KernelContext >= 2`。
  - `_extract_pattern_enum` 解析所有 `pattern\d+ = \d+` enumerator，并要求精确等于 `[(0,0), ..., (N-1,N-1)]`。
- 状态：Round 12-A 未通过，已按主线修订；需基于最新文本重新 strict review。

### 收敛轮次 12-B：Meitner strict review
- 审阅对象：`Meitner / 019ebf27-f98d-7811-90e2-dc485caada4f`。
- 输入标准包：同 12-A。
- 严格通过口径：同 12-A。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 是否需要用户确认：不需要。
- 是否可请求守护最终检验：Round 12-B 本身不阻断；但因 Round 12-A 不通过，本轮未满足守护前置。
- 状态：Round 12-B 通过，但本轮整体未收敛；需基于 12-A 修订后的最新文本重新 strict review。

### 收敛轮次 13-A：Cicero strict review
- 审阅对象：`Cicero / 019ebf27-f887-7122-8c0d-4afadf3c9be8`。
- 输入标准包：基于 Draft 8 最新 staged 文本、Round 12-A / 12-B 阻断与主线处理、用户确认项、禁止修改面、5 个 local-only expectation manifest 和必过验收命令。
- 严格通过口径：仍有任何影响 enum/default selector 公开输出合同、args/tuner_args IR 合同、N 路 dispatcher、expectation 权限、任务卡可落地性、暂停 execute 恢复边界、公开 API、验收资产或用户确认完整性的可执行改进项，则不通过。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 是否需要用户确认：不需要。
- 是否可请求守护最终检验：Round 13-A 本身不阻断；但需 Round 13-B 也通过并写回收敛结论后才可请求。
- 状态：Round 13-A 通过，但本轮整体未收敛；需基于 13-B 修订后的最新文本重新 strict review。

### 收敛轮次 13-B：Meitner strict review
- 审阅对象：`Meitner / 019ebf27-f98d-7811-90e2-dc485caada4f`。
- 输入标准包：同 13-A。
- 严格通过口径：同 13-A。
- 结论：不通过。
- 发现问题：
  - `_extract_pattern_enum` 只提取 `pattern\d+ = \d+` 子集并比较期望，无法拒绝 `extra = 99` 这类额外 enum member。
- 主线处理：
  - `_extract_pattern_enum` 改为按逗号解析 enum body 的完整 enumerator 列表；每个 member 必须完整匹配 `patternN = N`，完整列表必须严格等于 `0..N-1`，任何额外或异常 member 都失败。
- 状态：Round 13-B 未通过，已按主线修订；需基于最新文本重新 strict review。

### 收敛轮次 14-A：Cicero strict review
- 审阅对象：`Cicero / 019ebf27-f887-7122-8c0d-4afadf3c9be8`。
- 输入标准包：基于 Draft 8 最新 staged 文本、Round 13-A / 13-B 阻断与主线处理、用户确认项、禁止修改面、5 个 local-only expectation manifest 和必过验收命令。
- 严格通过口径：仍有任何影响 enum/default selector 公开输出合同、args/tuner_args IR 合同、N 路 dispatcher、expectation 权限、任务卡可落地性、暂停 execute 恢复边界、公开 API、验收资产或用户确认完整性的可执行改进项，则不通过。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 是否需要用户确认：不需要。
- 是否可请求守护最终检验：Round 14-A 本身不阻断；需 Round 14-B 也通过并写回收敛结论后请求守护最终检验。
- 状态：Round 14-A 通过。

### 收敛轮次 14-B：Meitner strict review
- 审阅对象：`Meitner / 019ebf27-f98d-7811-90e2-dc485caada4f`。
- 输入标准包：同 14-A。
- 严格通过口径：同 14-A。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 是否需要用户确认：不需要。
- 是否可请求守护最终检验：Round 14-B 本身不阻断；需计划负责人写回 14-A / 14-B 结论并更新 subagent 收敛结论后请求守护最终检验。
- 状态：Round 14-B 通过。

### subagent 收敛结论
- 已发起或计划要求的审阅任务：Round 8-A Cicero、8-B Meitner、9-A Cicero、9-B Meitner、10-A Cicero、10-B Meitner、11-A Cicero、11-B Meitner、12-A Cicero、12-B Meitner、13-A Cicero、13-B Meitner、14-A Cicero、14-B Meitner。
- 当前结论：已收敛；Round 14-A Cicero 与 Round 14-B Meitner 均通过，均无阻断、无最小需改项、无待用户确认项。
- 遗留项：无；可进入 `守护最好的爱莉希雅` 本人守护最终检验。

### 守护最终检验
- 检验对象：`守护最好的爱莉希雅` 本人。
- 当前结论：已通过；任务记录 `2026-06-13 14:03 +0800` 已摘录 Draft 8 守护最终检验回执，结论=通过、阻断项=无、最小需改项=无、是否需要用户确认=不需要。
- 阻断项：无；Round 14-A / 14-B subagent strict review 已收敛，均无阻断、无最小需改项、无待用户确认项。
- 允许事项：完成目标 worktree 的 5 个 local-only expectation leaf 物化记录后，恢复既有唯一暂停 execute `T-20260613-ad9fdae1 / tuner-select-runtime-cost-choice`；不得创建第二个 execute。

## 计划书入档验收 / 复验 / 修复复核记录

- 当前状态：2026-06-13 15:28 +0800 入档验收通过；下一步按标准脚本续接 `merge`，不提前提交、推送或归档。
- 结论人：`不要啊教练`。
- 验证基线：执行目录 `/home/lfr/kernelcode_generate/wt-20260613-tuner-select-runtime-cost-choice`；当前分支 `task/tuner-select-runtime-cost-choice`；`HEAD=d679cdcbda147d18effa4121cf460df4d05e33f8`；`origin/main=a5f6e7a4593396f739787810f5d5be0b2d82dcb8`；`merge-base=d679cdcbda147d18effa4121cf460df4d05e33f8`；`HEAD...origin/main=0 1`。
- 同步结果：`git fetch --prune origin main` 通过；`origin/main` 领先 1 个 loop-soft-pipeline 相关提交，重叠触及 `spec/pass/pipeline/npu_demo_lowering.md` 与 `test/passes/pipeline/test_npu_demo_lowering.py`。临时 `origin/main` worktree 上 `git apply --check --3way <当前 staged patch>` 通过；latest-main+patch 上 `pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k test_npu_demo_lowering_pipeline_pass_order` 为 `1 passed, 10 deselected, 1 warning`；拷贝当前 local-only expectation 后运行 `python3 expectation/pass/pipeline/npu_demo_lowering.py` 通过。
- 合同验收摘要：5 个计划列明 leaf expectation 均已在本 worktree 运行通过：`expectation/dialect/tuner/operation/select.py`、`expectation/pass/kernel_pattern_attach/basic.py`、`expectation/pass/outline_device_kernel/tuner_launch.py`、`expectation/dsl/gen_kernel/tuner_emit.py`、`expectation/pass/pipeline/npu_demo_lowering.py`。
- Diff 反推与静态门禁：`py_compile` 通过；`test/dialect/tuner/test_tuner.py` 为 `14 passed`；`test/passes/tuning/test_kernel_pattern_attach.py test/passes/tuning/test_outline_device_kernel.py` 为 `20 passed, 1 warning`；`test/dsl/gen_kernel/test_gen_kernel.py` 为 `101 passed, 2 warnings`；`test/passes/pipeline/test_npu_demo_lowering.py` 为 `11 passed, 1 warning`；`test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py` 为 `19 passed, 1 warning`；`test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py` 为 `7 passed`。
- 敏感范围与 expectation 边界：`git diff --check`、`git diff --cached --check` 均通过；`expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` staged / unstaged diff 均为空；5 个 Draft 8 expectation leaf 均为 `!!` ignored local-only，`git ls-files --stage -- <5 leaf>` 无输出，未进入 index。
- 最小阻断项或通过摘要：无阻断项、无最小需改项；review 通过记录和 review -> archive_acceptance 流转补记均已核对；入档验收通过，可进入 `merge/归档` 阶段。

## 计划目标

- 把 `tuner.select` 的 IR 合同扩展为支持 N 个 `patterns`、runtime `args` 和选择相关 `tuner_args`。
- 在 npu_demo entry dispatcher module 路径中，生成一个 entry 级 `enum class` 表示 pattern id。
- 生成一个 selector function，返回该 enum 类型；首版 body 固定返回 `pattern0`，与旧“默认选择 pattern0”行为保持一致。
- Host dispatcher 使用 selector function 返回值做 N 路分支，只 launch 被选中的真实 `KernelContext` pattern。
- 保持 `tuner.launch` 裸 op 不允许直接进入源码生成；真实 launch 仍通过 `outline-device-kernel` 后的 `arch.launch` 承接。
- 保证 `kernel-pattern-attach` 当前公开 producer 可以继续只生成 2 个 pattern，但下游 IR/source 不把候选数写死为 2。

## 非目标

- 不在本计划生成 runtime `CostContext` 全量评估、`candidate_cost`、`best_cost`、`data_movement_cost`、`compute_cost` 或 cost 最优选择逻辑。
- 不在本计划实现真实 benchmark、profile、cache、剪枝、调优参数枚举、search space、online tuning 或外部数据库。
- 不在本计划修改 `dsl_run(...)`、`dsl_cost_run(...)` 的公开入口签名。
- 不修改 `TunerLaunchOp` 的公开签名。
- 不跨文件调用非公开 `_xxx` helper；测试不得直连非公开 helper。
- 不把 `expectation/` 纳入 staged diff、merge candidate 或远程提交。

## 当前基线

- `TunerSelectOp` 当前公开构造为 `TunerSelectOp(patterns, result_type=...)`，无 operands。
- `tuner.select` 当前文本形态为 `tuner.select {patterns = [@p0, @p1]} : !symbol.int<#symbol.expr<pattern_id>>`。
- npu_demo `tuner.select` 当前发射 `S_INT <name> = 0;`，表示默认 pattern0。
- `KernelPatternAttachPass` 当前固定生成两个 pattern 函数，dispatcher 是 `tuner.select + symbol.const 0 + symbol.eq + scf.if + tuner.launch`。
- `OutlineDeviceKernelPass` 当前把 `tuner.launch(@pattern)` 改写为 `arch.launch @pattern_device`。
- 当前 Draft 6 local-only `expectation/dsl/gen_kernel/tuner_emit.py` 仍锁 runtime cost selector，已经与用户最新口径冲突；必须重写为 enum/default selector 合同后才能恢复 execute。
- 既有 execute worktree 中存在小李飞刀未暂存实现改动；架构师不得覆盖执行人实现改动。Draft 8 重物化只允许同步计划和 local-only expectation，并记录 hash。

## 方案比较与选型

### 方案 A：继续 Draft 6 runtime CostContext selector
- 结论：废止。
- 原因：用户明确要求当前 `select` 是一个 function，默认返回 `pattern0`；runtime cost 选择超出当前期望。

### 方案 B：保留旧 `S_INT pattern_id = 0;`
- 结论：不作为最终目标。
- 原因：它不能表达“代码中有 enum class 表示对应 pattern”，也不利于 N 路 dispatcher 的可读性。

### 方案 C：生成 pattern enum + selector function，selector 默认返回 pattern0
- 结论：采用。
- 原因：满足用户最新口径；保留未来把 selector function body 替换成真实调优策略的扩展点；当前不引入 cost runtime 风险。

## 公开 API 设计

- 用户确认来源：用户确认 `TunerSelectOp` 采用 `patterns, result_type=..., *, args=(), tuner_args=()`；用户最新确认代码中应有 enum class 表示 pattern，`select` 是一个 function，默认返回 `pattern0`。

### `class TunerSelectOp(...)`

```python
class TunerSelectOp(
    patterns: Sequence[str | SymbolRefAttr],
    result_type: Attribute = SymbolValueType.from_expr("pattern_id"),
    *,
    args: Sequence[SSAValue | Operation] = (),
    tuner_args: Sequence[SSAValue | Operation] = (),
)
```

- `patterns`：非空 flat pattern symbol 列表，长度为 N，N >= 1。重复 symbol 不作为稳定失败；列表位置仍代表不同候选 id。
- `args`：透传给 pattern launch 的 runtime operands；顺序必须与 pattern launch args 匹配。
- `tuner_args`：传给 selector function 的选择相关 runtime state；不等于 `args`，也不自动包含所有 runtime operands。
- `result_type`：固定为 `!symbol.int<#symbol.expr<pattern_id>>`。
- 稳定错误语义：空 `patterns`、非 flat symbol、非 `pattern_id` result type、`args` type list 不匹配、`tuner_args` type list 不匹配均失败。不新增 `patterns` 唯一性硬检查。错误文本只锁稳定关键词，不锁完整句子；用户此前已确认必要检查版错误语义，当前不新增 exact error text 合同。

### npu_demo generated source 合同

- 对 entry 名 `matmul_entry`，生成一个 entry 级 enum class；enum class exact name 不作为当前公开稳定输出合同。
- enum enumerator 必须按 `patterns` 列表顺序生成：`pattern0 = 0`、`pattern1 = 1`、...、`pattern{N-1} = N-1`。
- 生成一个 selector function；selector function exact name 不作为当前公开稳定输出合同。
- selector function 返回 enum 类型，参数只来自 `tuner_args`；若 `tuner_args` 为空，函数无业务参数。
- 首版 selector function body 固定返回该 enum 的 `pattern0`：

```cpp
return <EntryPatternEnum>::pattern0;
```

- `tuner.select args(...)` 的 `args` 不传给 selector function，除非同一个 value 也显式出现在 `tuner_args(...)` 中。
- Host dispatcher 内 `tuner.select` result 绑定为 enum 值，后续 `symbol.eq %pattern, const_i` 必须发射为 enum 比较，例如 `pattern == <EntryPatternEnum>::pattern1`，不能依赖裸 int 与 enum class 隐式比较。

## IR 与源码示例

### Final IR 示例

```mlir
builtin.module {
  func.func @matmul_entry(%arg0 : !nn.memory<...>) attributes {entry_point} {
    %pattern = tuner.select args(%arg0)
      {patterns = [@matmul_entry_pattern0, @matmul_entry_pattern1, @matmul_entry_pattern2]}
      : args(!nn.memory<...>) -> !symbol.int<#symbol.expr<pattern_id>>
    %zero = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %is0 = "symbol.eq"(%pattern, %zero)
      : (!symbol.int<#symbol.expr<pattern_id>>, !symbol.int<#symbol.expr<0>>) -> i1
    scf.if %is0 {
      arch.launch<...>(@matmul_entry_pattern0_device, %arg0) : (!nn.memory<...>) -> ()
    } else {
      ...
    }
    func.return
  }
}
```

### Source 示例

以下名称只作说明，exact enum / selector function name 不作为当前公开稳定输出合同；实现和验收锁结构语义。

```cpp
enum class <EntryPatternEnum> : S_INT {
    pattern0 = 0,
    pattern1 = 1,
    pattern2 = 2,
};

<EntryPatternEnum> <selector_function>() {
    return <EntryPatternEnum>::pattern0;
}

void matmul_entry(Memory& arg0) {
    <EntryPatternEnum> pattern = <selector_function>();
    if (pattern == <EntryPatternEnum>::pattern0) {
        npu_demo::KernelContext ctx;
        npu_demo::launch<..., matmul_entry_pattern0_device>(ctx, arg0);
    } else if (pattern == <EntryPatternEnum>::pattern1) {
        npu_demo::KernelContext ctx;
        npu_demo::launch<..., matmul_entry_pattern1_device>(ctx, arg0);
    } else {
        npu_demo::KernelContext ctx;
        npu_demo::launch<..., matmul_entry_pattern2_device>(ctx, arg0);
    }
}
```

## 完成态定义

- `TunerSelectOp` 支持 N 个 `patterns`、runtime `args` 与选择相关 `tuner_args`，parse / print / verifier 与 spec 一致。
- `kernel-pattern-attach` 当前公开 producer 仍可只生成 2 路 dispatcher；下游 `tuner.select`、outline 与 codegen 支持公开 IR 中 N=1 / N=3。
- `outline-device-kernel` 继续正确把 `tuner.launch` 改写为 `arch.launch @pattern_device`；本计划不要求为了 selector 保留 cost metadata。
- npu_demo entry dispatcher source 包含 pattern enum 和 selector function，selector 默认返回 enum `pattern0`。
- Source 不包含 `npu_demo::CostContext`、`candidate_cost`、`best_cost`、`data_movement_cost` 或 `compute_cost`。
- N 路 dispatcher generated source 只 launch 一个真实 `KernelContext` branch。
- local-only expectation 覆盖 tuner dialect、kernel-pattern-attach、outline-device-kernel、gen_kernel tuner emit 和 npu_demo lowering pipeline。
- 无 scope 外 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 越权改动。

## 验收设计

- Diff 反推 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/tuner/test_tuner.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tuning/test_kernel_pattern_attach.py test/passes/tuning/test_outline_device_kernel.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
- 当前必过 `expectation` 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dialect/tuner/operation/select.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/kernel_pattern_attach/basic.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/outline_device_kernel/tuner_launch.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/gen_kernel/tuner_emit.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/pipeline/npu_demo_lowering.py`
- expectation scope 核对：
  - 允许的 local-only expectation scope 仅限上述 5 个 leaf。
  - 目录聚合入口不作为当前必过合同验收。
  - 必须记录 scope 开始 / 结束 manifest 或 hash、目标 worktree 物化记录、scope 外空 diff、tracked / staged / untracked / ignored 文件检查。
  - `expectation/` 仍不得进入 staged diff、merge candidate 或远程提交。
- 文本门禁：
  - `git diff --cached --check` 与 `git diff --check` 必须无输出。
  - `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` 必须无输出。
  - touched Python 实现不得跨文件导入非公开 `_xxx` helper。

## 计划内小任务

### S1. 更新 tuner.select 公开 spec 与 dialect op
- 为什么做：当前 `tuner.select` 无 operands，不能表达 pattern launch args 与 selector state。
- 做什么：为 `TunerSelectOp` 增加 `args` 与 `tuner_args`，同步 parse / print / verifier / spec / tests。
- 不做什么：不新增 search-space API，不修改 `TunerLaunchOp`，不生成 cost selector。
- 怎么验收：运行 `test/dialect/tuner/test_tuner.py`；合同验收单列运行 `expectation/dialect/tuner/operation/select.py`。
- 卡住问谁：公开 API 签名、旧语法兼容和错误文本问用户；实现边界问架构师。
- 上下文摘要：selector function 未来可能根据 `tuner_args` 做策略，但当前只默认返回 pattern0；`args` 仍用于真实 pattern launch。
- 小任务目标：添加兼容旧第二位置 `result_type` 的 `TunerSelectOp(patterns, result_type=..., *, args=..., tuner_args=...)`，并让 IR 文本合同稳定。
- 模块范围：`spec/dialect/tuner.md`、`kernel_gen/dialect/tuner/operation/select.py`、`test/dialect/tuner/test_tuner.py`。
- 禁止修改面：`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`；`expectation/` 本体不得由 execute 修改。
- 合同真源：用户确认 > local-only `expectation/dialect/tuner/operation/select.py` > `spec/dialect/tuner.md` > pytest > 当前实现。
- 非目标：不新增 search-space API，不修改 `TunerLaunchOp`，不生成 cost selector，不扩大公开工具入口。
- 最小功能闭环：公开 constructor、parse、print、verify 均支持四种 `args/tuner_args` 组合；错误边界覆盖数量不匹配和同数量错类型两类 type list 失败。
- 执行步骤：
  1. 更新 `spec/dialect/tuner.md` 的 API 列表、语法、错误语义和测试矩阵。
  2. 修改 `TunerSelectOp` constructor、operand defs、parse / print / verify，确保 `args` 与 `tuner_args` 是两组可区分 operands，并记录 segment 大小。
  3. 校验两组文本 type list 分别与 operand 数量和逐项实际 type 完全一致。
  4. 补充 dialect pytest 覆盖四种 canonical 组合、旧语法兼容、N patterns 和错误边界。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dialect/tuner/operation/select.py`
- 记录要求：记录旧语法兼容、四种 canonical 语法组合、错误文本、expectation hash 和合同验收结果。

### S2. 维持 dispatcher N 路可表达
- 为什么做：用户明确 pattern 可能很多，不能把 dispatcher 或 source 写死成二选一。
- 做什么：让公开 IR 和下游 outline/codegen 支持 N 路；`kernel-pattern-attach` 当前公开 producer 可仍只生成 2 个 pattern。
- 不做什么：不在本卡扩大 `kernel-pattern-attach` 候选生成数量。
- 怎么验收：运行 `test/passes/tuning/test_kernel_pattern_attach.py`；合同验收单列运行 `expectation/pass/kernel_pattern_attach/basic.py`。
- 卡住问谁：是否扩展候选 producer 问用户；IR 形状问架构师。
- 模块范围：`spec/pass/tuning/kernel_pattern_attach.md`、`kernel_gen/passes/tuning/kernel_pattern_attach.py`、`test/passes/tuning/test_kernel_pattern_attach.py`。
- 禁止修改面：同 S1。
- 合同真源：用户确认 > local-only `expectation/pass/kernel_pattern_attach/basic.py` > pass spec > pytest > 当前实现。
- 非目标：不扩大 `kernel-pattern-attach` 当前候选生成数量，不引入真实 tuner search space。
- 最小功能闭环：公开 pass 继续生成当前 2 路 dispatcher，`tuner.select` 和每个 `tuner.launch` 都透传 entry runtime `args`，且默认不打印空 `tuner_args()`。
- 执行步骤：
  1. 保持 `kernel-pattern-attach` 公开 producer 当前只生成 2 个 pattern。
  2. 保证 `args` 透传给 `TunerSelectOp` 和每个 `TunerLaunchOp`。
  3. 默认构造空 `tuner_args=()`，但 printed IR 不输出空 `tuner_args()`。
  4. 下游 N=1 / N=3 通过公开手写 IR 的 outline / codegen 测试覆盖，不测试私有 builder。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/kernel_pattern_attach/basic.py`
- 记录要求：记录 N=2 producer 输出、默认 `tuner_args=()` 不打印空组的 expectation 合同结果。

### S3. 保持 tuner.launch outline 到 arch.launch
- 为什么做：源码生成不直接接受裸 `tuner.launch`，真实 launch 仍必须经 outline 后的 `arch.launch`。
- 做什么：确保 `outline-device-kernel` 继续把 `tuner.launch(@pattern, args...)` 改写为 `arch.launch @pattern_device`。
- 不做什么：不为了 selector function 引入或强制保留 cost metadata。
- 怎么验收：运行 `test/passes/tuning/test_outline_device_kernel.py`；合同验收单列运行 `expectation/pass/outline_device_kernel/tuner_launch.py`。
- 卡住问谁：outline 语义问架构师。
- 模块范围：`spec/pass/tuning/outline_device_kernel.md`、`kernel_gen/passes/tuning/outline_device_kernel.py`、`test/passes/tuning/test_outline_device_kernel.py`。
- 禁止修改面：同 S1。
- 合同真源：用户确认 > local-only `expectation/pass/outline_device_kernel/tuner_launch.py` > outline spec > pytest > 当前实现。
- 非目标：不为 selector function 引入 cost metadata，不允许裸 `tuner.launch` 直接进入源码生成。
- 最小功能闭环：给定 host dispatcher 中的 `tuner.launch(@pattern, args...)`，outline 后 host 中无 `tuner.launch` 残留，并出现等价 `arch.launch @pattern_device`。
- 执行步骤：
  1. 更新 spec，说明 enum selector 不依赖 device cost metadata。
  2. 保持 `tuner.launch` 到 `arch.launch` 的公开输出。
  3. 补齐 pytest 覆盖 tuner dispatcher outline 后无 `tuner.launch` 残留。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/outline_device_kernel/tuner_launch.py`
- 记录要求：记录 outline 输出 IR 和 expectation 合同结果。

### S4. 实现 npu_demo enum/default selector 发射
- 为什么做：用户希望源码中有 pattern enum，`select` 是函数，当前阶段默认返回 `pattern0`。
- 做什么：在 entry dispatcher module 路径生成 pattern enum、selector function 和 enum-based N 路 branch。
- 不做什么：不生成 `CostContext` cost evaluation，不计算 best cost，不改变 `dsl_cost_run`。
- 怎么验收：运行 `test/dsl/gen_kernel/test_gen_kernel.py`；合同验收单列运行 `expectation/dsl/gen_kernel/tuner_emit.py`。
- 卡住问谁：generated source 命名、enum 输出合同问用户；实现边界问架构师。
- 模块范围：`spec/dsl/gen_kernel/gen_kernel.md`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/select.py`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/control_flow.py`、`test/dsl/gen_kernel/test_gen_kernel.py`。
- 禁止修改面：同 S1。
- 合同真源：用户确认 > local-only `expectation/dsl/gen_kernel/tuner_emit.py` > gen_kernel spec > pytest > 当前实现。
- 非目标：不生成 runtime `CostContext` 评估、不计算 best cost、不修改 `dsl_cost_run` 或 cost runner 公开入口。
- 最小功能闭环：N=3 dispatcher source 中存在 enum class、返回 enum 的 selector function、默认返回 `pattern0`、pattern0 / pattern1 enum 条件分支、pattern2 最终真实 launch 分支和三路真实 `KernelContext` launch；无任何 runtime cost selector 源码。
- 执行步骤：
  1. 更新 gen_kernel spec，写清 enum class、selector function、默认返回 pattern0 和 N 路 branch 语义。
  2. 在 module entry dispatcher 发射路径中收集 `tuner.select.patterns`，生成 entry 级 enum class。
  3. 生成 selector function，返回 enum 类型；参数来自 `tuner_args`，body 固定返回 `pattern0`。
  4. 让 `tuner.select` result 在源码中绑定为 enum 值。
  5. 让 `symbol.eq(pattern_id, const_i)` 在 pattern selector 场景发射为 enum 比较。
  6. 保持 `arch.launch` 真实 branch 使用 `KernelContext`，只运行被选中的 branch。
  7. 删除或更新 Draft 6 cost selector 断言；新增 N=3 enum/default selector 测试。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/dsl/gen_kernel/tuner_emit.py`
- 必要断言：源码包含 `enum class`、`pattern0 = 0`、`pattern1 = 1`、`pattern2 = 2`、返回该 enum 的 selector function、`return <Enum>::pattern0;`、pattern0 / pattern1 的 enum 条件分支、pattern2 的真实 launch 分支、`npu_demo::KernelContext`；源码不包含 `npu_demo::CostContext`、`candidate_cost`、`best_cost`、`data_movement_cost`、`compute_cost`。
- 记录要求：记录源码片段、enum 命名、selector 参数来源、默认返回 pattern0、N 路 branch 和 expectation 合同结果。

### S5. Pipeline 与端到端回归
- 为什么做：单独 op / pass 正确不代表默认 npu-demo-lowering 链路可运行。
- 做什么：跑通 `kernel-pattern-attach -> transform-apply -> attach-arch-information -> outline-device-kernel -> template-name-infer -> gen_kernel` 的 enum/default selector path。
- 不做什么：不要求全量 `expectation` 通过；不纳入 cuda_sm86 runtime selector。
- 怎么验收：运行 pipeline pytest、private API boundary、KCE gate；端到端 enum/default selector 源码由 `test/dsl/gen_kernel/test_gen_kernel.py` 与 `expectation/dsl/gen_kernel/tuner_emit.py` 覆盖；本卡合同验收单列运行 `expectation/pass/pipeline/npu_demo_lowering.py`，该 leaf 只锁 pass-order handoff。
- 卡住问谁：latest main 无关 gate 失败问架构师裁定；流程问管理员。
- 模块范围：pipeline spec / tests、必要工具测试。
- 禁止修改面：同 S1。
- 合同真源：用户确认 > local-only `expectation/pass/pipeline/npu_demo_lowering.py` > pipeline spec > pytest > 当前实现。
- 非目标：不要求全量 `expectation` 通过，不把目录聚合入口列为必过，不纳入 cuda_sm86 runtime selector。
- 最小功能闭环：公开 pipeline 顺序保持 `kernel-pattern-attach -> transform-apply -> attach-arch-information -> outline-device-kernel -> template-name-infer` handoff；端到端 source path 由 S4 的 codegen pytest 和 `tuner_emit` leaf 验收。
- 执行步骤：
  1. 更新 `spec/pass/pipeline/npu_demo_lowering.md` 中 selector 行为描述。
  2. 补充 pipeline 测试，覆盖默认 lowering 能进入 enum/default selector path。
  3. 运行计划列出的 pytest 和 diff 反推测试。
  4. 记录敏感目录空 diff、private API boundary 和 KCE gate 结果。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/pipeline/npu_demo_lowering.py`
- 记录要求：记录每条命令结果、未运行原因、无关失败证据、expectation 合同结果和 staged diff 范围。

## 前置依赖与并行风险

- Draft 8 已重新完成 strict review 与守护最终检验，并按记录恢复既有唯一 execute `T-20260613-ad9fdae1`。
- 架构师重物化只覆盖 local-only expectation 与计划文件，未覆盖执行人实现改动。
- latest-main 重叠风险已在 review 与入档验收中复核：当前 staged patch 可干净应用到 `origin/main`，重叠 pipeline pytest 与 pipeline expectation leaf 在 latest-main+patch 上通过。

## 计划自检与返工口径

- 自检：Draft 8 已记录公开 API 用户确认来源、非目标、禁止修改面、合同真源、local-only expectation 权限、必过命令、唯一 execute 恢复边界和 S1-S5 最小功能闭环。
- 自检：当前计划文件必须保持 tracked/index diff；`expectation/` 只能作为 ignored local-only 合同资产，由架构师物化并记录 manifest/hash，不得进入 staged diff、merge candidate 或远程提交。
- 返工口径：只要 subagent、守护最终检验、执行、review 或计划书入档验收仍能指出影响公开 API、输出合同、expectation 证明力、任务卡可执行性、可读性、可维护性或验收可信度的可执行项，就回到计划修订或原 execute 返工，不得恢复/推进。
- 恢复口径：已执行；Draft 8 strict review 收敛、用户待决策项为无、`守护最好的爱莉希雅` 本人守护最终检验通过、5 个 local-only expectation 已物化到 execute worktree 并记录 manifest/hash 后，管理员已恢复既有暂停任务 `T-20260613-ad9fdae1`。

## 待确认项

- 当前无待确认项。用户已明确：selector function 默认返回 `pattern0`，不采用 Draft 6 runtime CostContext 选择。

## 用户确认与协同约束

- 用户确认来源：
  - `tuner.select` 需要 `args=()` 与 `tuner_args`。
  - pattern 可能很多，不能按二路写死。
  - C8 错误判定采用必要检查版，只锁必要失败类别与稳定关键词，不锁完整错误文本。
  - 源码中需要 enum class 表示 pattern。
  - `select` 是一个 function，当前默认返回 `pattern0`。
- 恢复状态：Draft 8 已完成 subagent strict review 收敛、守护最终检验、expectation 重物化、既有唯一 execute 恢复、execute、review 与入档验收。
- 恢复口径：只允许恢复既有暂停 execute `T-20260613-ad9fdae1 / tuner-select-runtime-cost-choice`，不得创建第二个 execute；该口径已执行，后续只进入 `merge/归档`。
- 计划自检：当前 Draft 8 已去除 Draft 6 runtime cost selector 目标，重写公开输出合同、小任务卡和 expectation 目标；strict review、守护最终检验和入档验收均已通过，无剩余待确认项。
