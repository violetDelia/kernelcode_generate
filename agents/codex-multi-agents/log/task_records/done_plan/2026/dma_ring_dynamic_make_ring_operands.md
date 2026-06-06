# DMA Ring Type for MultiBufferPass 计划书 Draft 4

## 文档信息

- 计划用途：规划 `dma.ring` 公开类型与 `dma.make_ring` operands 的合同调整，使 ring 参数以 `dma.make_ring` operands 作为唯一真源，服务现有与后续 `MultiBufferPass`。
- 当前状态：既有唯一计划级 `execute` `T-20260605-0b33f547` 已由管理员恢复为进行中。用户于 2026-06-05 指出本计划流程存在三项未收口；随后已裁决 expectation 内容可接受、pass expectation 结构符合一般结构、当前按 ring 在 loop 外的支持范围收口、`num` 与 `target` 计算口径已确认，并要求 `memory-stage` 固定 num 与 `target` 优先计算拆成独立 expectation 文件；之后补充动态 shape 参数一般由 kernel 参数传入，可增加 `alloc(S1, S2)` 动态例子。当前 Draft 4 后已发生 target 优先、expectation 拆分、动态 case 与 no-`+1` 对齐口径的新修订，且 no-`+1` 修订后的 Feynman / Gibbs 两路 subagent strict review 已完成并通过，`守护最好的爱莉希雅` no-`+1` 修订后守护最终检验已通过，用户已明确同意推进本计划。2026-06-06 execute 阶段发现 `expectation.pass.multi_buffer.matmul_ring_target` dynamic same-space 的 `CHECK` 文本与现有 `ircheck` 对 `SymbolExprAttr` 的归一匹配口径不一致；用户明确要求不要修正 `ircheck`，由架构师修改 expectation，且该补丁已完成两路 strict review 与守护最终检验。随后发现 `expectation.dialect.dma.operation.make_ring` 负例仍可能随机生成 `offset == shape_bytes` 并把合法边界当作失败合同，该补丁已完成两路 strict review 与守护最终检验。execute 恢复公开 `KernelCodeError(ErrorKind.VERIFY, ErrorModule.DIALECT, ...)` 后，`expectation.utils.case_runner.assert_parse_operation_verifier_fails` 只捕获 `VerifyException`，导致 `make_ring/current_ring/advance_ring` negative leaf 失败；本轮架构裁定保持公开 verifier 错误类型为 `KernelCodeError`，仅让 expectation helper 把 verify/dialect 的 KCE 视为 verifier failure，其它 KCE 继续冒泡。该 helper 补丁已完成本地验证、Feynman / Gibbs 两路 round11-R2 strict review 与 `守护最好的爱莉希雅` 本人守护最终检验；结论通过，无阻断、无最小需改、无设计待确认。当前允许通知执行人继续既有 `T-20260605-0b33f547` 基于新 helper 做验收闭环；不得创建第二个 execute，不得扩大公开 API、错误类型、稳定错误文本或 execute 范围。
- 用户确认来源：
  - 2026-06-04 用户确认：按“`DmaRingType` 只保留 slot memory type，动态 `num/offset/shape_bytes` 作为 `make_ring` operands”的口径出计划书。
  - 2026-06-04 用户确认：该调整目的为 `multi buffer pass`。
  - 2026-06-04 用户对“另外”回复“不知”，本计划不再保留未完成“另外”事项；reduce / matmul K 维累加是否适用 multi-buffer 仅作为后续专题讨论，不进入本计划执行目标。
  - 2026-06-04 用户确认“可以，你先添加”，授权架构侧新增 `expectation/pass/multi_buffer/**` pass 级 expectation，用于锁定 `MultiBufferPass` 黑盒输出中的新 DMA ring 合同。
  - 2026-06-05 用户确认“测试的 alloc loop 的外面”，本计划新增的 `expectation.pass.multi_buffer.matmul_ring_memory_stage` 与 `expectation.pass.multi_buffer.matmul_ring_target` 输入 IR 必须把 lhs/rhs staging `dma.alloc` 与对应 `dma.free` 放在 `symbol.for` 外，loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费。
  - 2026-06-05 用户流程纠偏：新增 / 修改 expectation 的具体内容仍需用户确认；讨论冲突 / 争议必须由用户裁决；下发 execute 前必须取得用户明确同意。
  - 2026-06-05 用户裁决：四个 DMA ring leaf expectation 内容可以；新增 pass expectation 的 loop 外 alloc / loop 内 copy+matmul / loop 外 ring 结构符合一般结构；当前不支持其它 ring 位置，按“ring 在 loop 外”支持范围收口；`num` 需要由 pass 参数 / 分析结果计算，不得回到 ring type，也不得作为无来源固定常量；`shape_bytes` 根据每个 ring slot 的 target memory 大小计算，不是根据最终 matmul output memory 计算。
  - 2026-06-05 用户裁决：固定 ring 数沿用现有 `memory-stage` option；新增 / 使用 `target=<target-name>` option 时 `target` 优先，`target-name` 是 target registry 中的目标名，不是 memory space 名；仓库当前已有示例为 `npu_demo`、`cpu`；`memory-stage` 固定 num 与 `target` 优先计算必须拆成独立 expectation 文件。
  - 2026-06-05 用户补充：动态 shape 参数一般由 kernel 参数传入；本轮可在 target leaf 中增加动态例子，例如 `dma.alloc(%s1, %s2)` / `alloc(S1, S2)`。
  - 2026-06-05 用户裁决：`offset` 不需要 `+1`；加 `+1` 会在 memory slot 之间制造 1 字节空隙并导致后续地址对齐风险。本轮 `MultiBufferPass` ring 化输出必须使用 `offset = shape_bytes`，backing bytes 使用 `num * shape_bytes`。
  - 2026-06-05 用户明确回复“好的，可以推进这个计划了”，同意恢复 / 继续唯一计划级 `execute`：`dma-ring-dynamic-make-ring-operands`。
  - 2026-06-06 用户 / 执行链路确认：不要修正 `ircheck`；`expectation.pass.multi_buffer.matmul_ring_target` dynamic same-space 的匹配问题由架构师修订 expectation 合同资产。
  - 2026-06-06 架构按用户 no-`+1` 裁决收口：`expectation.dialect.dma.operation.make_ring` 不得再把 `offset == shape_bytes` 作为负例；正例必须覆盖该合法边界，负例只覆盖 `offset < shape_bytes`。
  - 2026-06-06 架构裁定：公开 verifier 失败继续遵循仓库统一 `KernelCodeError(ErrorKind.VERIFY, ErrorModule.DIALECT, ...)` 语义，不回退 `VerifyException`；`expectation.utils.case_runner.assert_parse_operation_verifier_fails` 应把该 KCE 视为 verifier failure，但不得吞掉其它 kind/module 的 KCE。
- 目标 `spec`：
  - `spec/dialect/dma.md`
  - `spec/pass/multi_buffer.md`
  - `spec/operation/dma.md`（若 operation facade 暴露 ring helper，则同步；若未暴露，只记录不适用）
  - `spec/dsl/ast/nodes/dma.md` / `spec/dsl/ast/plugin/dma.md`（若 DSL 暴露 ring helper，则同步；若未暴露，只记录不适用）
  - `spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`（默认只作为当前 pipeline 不接入 multi-buffer 的合同来源；若 execute 实际修改该文件，必须补跑 pipeline pytest）
- 目标 `API`：
  - `class DmaRingType(memory_type: NnMemoryType)`
  - `class DmaMakeRingOp(memory: SSAValue | Operation, num: SSAValue | Operation, offset: SSAValue | Operation, shape_bytes: SSAValue | Operation, result_type: DmaRingType)`
  - `class DmaCurrentRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
  - `class DmaAdvanceRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
  - `class MultiBufferPass(memory_stage: int = 3, fold: bool = True, target: str | None = None)`
  - `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- 目标 `test`：
  - `test/dialect/dma/test_operation_ring.py`
  - `test/dialect/dma/test_package.py`
  - `test/passes/test_multi_buffer.py`
  - `test/passes/test_template_name_constraints.py`
  - `test/passes/test_registry.py`
  - `test/dsl/gen_kernel/emit/test_package.py`（仅 `dma_ring` 相关 emit 用例）
  - `test/passes/pipeline/test_npu_demo_lowering.py`（仅当 execute 修改 npu-demo-lowering pipeline spec / implementation / registry pipeline 口径时补跑）
  - `test/operation/test_dma.py`（若 operation facade 暴露 ring helper）
  - `test/dsl/ast/nodes/test_dma.py` / `test/dsl/ast/plugin/test_dma.py`（若 DSL 暴露 ring helper）
- 目标功能实现：
  - `kernel_gen/dialect/dma/type/ring_type.py`
  - `kernel_gen/dialect/dma/type/__init__.py`
  - `kernel_gen/dialect/dma/operation/ring.py`
  - `kernel_gen/dialect/dma/operation/__init__.py`
  - `kernel_gen/dialect/dma/__init__.py`
  - `kernel_gen/passes/multi_buffer.py`
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`
- 当前验收资产：
  - Diff 反推 pytest 最低集合见“验收设计”。
  - 架构侧已按 A 路径先行更新 `expectation/dialect/dma/type/ring_type.py`、`expectation/dialect/dma/operation/make_ring.py`、`expectation/dialect/dma/operation/current_ring.py`、`expectation/dialect/dma/operation/advance_ring.py` 到新 `!dma.ring<!nn.memory<...>>` 合同，并把旧 `!dma.ring<#symbol.expr<offset>, ...>` 作为应拒绝形态；其中 `make_ring.py` 静态正例必须覆盖 `offset == shape_bytes` 合法边界，负例只覆盖 `offset < shape_bytes`。
  - 用户授权新增 / 完善 `expectation/pass/multi_buffer/**`，当前拆成两个 pass leaf：
    - `expectation.pass.multi_buffer.matmul_ring_memory_stage` 锁定 `memory-stage=2` 固定 ring num：`dma.make_ring.num` 必须为 `2`，`offset = shape_bytes`，backing bytes 为 `num * shape_bytes`。
    - `expectation.pass.multi_buffer.matmul_ring_target` 锁定 `target=npu_demo` 优先：即使同时给出 `memory-stage=2`，也必须按 target space 分组计算 `num`；matmul lhs/rhs 在同一 target space 时，`num = target_space_bytes // (lhs_shape_bytes + rhs_shape_bytes)`；lhs/rhs 在不同 target space 时，各自按本 space 的 target memory size 与本 space 内 slot `shape_bytes` 合计计算；动态 shape case 中 `S1/S2/S3` 由 kernel 参数传入，输入 staging 使用 `dma.alloc(%s1, %s2)` 与 `dma.alloc(%s2, %s3)`，同一 target space 下 `num = 524288 // (4*S1*S2 + 4*S2*S3)`。
  - `matmul_ring_memory_stage` 使用小范围随机静态 `M/K/N`、dtype、loop end 与 lhs/rhs slot space；`matmul_ring_target` 同时覆盖随机静态 same-space、随机静态 different-space 和固定动态 same-space case。输入 IR 的 lhs/rhs staging `dma.alloc` 与对应 `dma.free` 必须在 `symbol.for` 外，loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费；pass 输出中的两组 loop 外 backing `dma.alloc` 必须位于 `symbol.for` 前；每组 ring 的 `shape_bytes` 根据该组 target / slot memory 大小计算，静态 lhs 为 `M * K * dtype_bytes`、rhs 为 `K * N * dtype_bytes`，动态 lhs 为 `4*S1*S2`、rhs 为 `4*S2*S3`，不是根据最终 matmul output memory 计算；`offset = shape_bytes`，不得为了满足旧 `< offset` 约束额外 `+1`；`memory-stage` leaf 的每组 backing bytes 为 `num * shape_bytes`；`target` leaf 中同一 target space 下的两组 ring 使用同一个共享 `num`，每组 backing bytes 仍为该组 `num * shape_bytes`；两组 `dma.make_ring` result type 必须是 `!dma.ring<!nn.memory<...>>`，旧 `!dma.ring<#symbol.expr<offset>, ...>` 不得出现在 pass 输出；动态 case 不得用 `symbol.get_dim` 替代 kernel 参数来源。
  - 用户已确认六个 leaf expectation 内容可作为本轮合同候选：`expectation.dialect.dma.type.ring_type`、`expectation.dialect.dma.operation.make_ring`、`expectation.dialect.dma.operation.current_ring`、`expectation.dialect.dma.operation.advance_ring`、`expectation.pass.multi_buffer.matmul_ring_memory_stage`、`expectation.pass.multi_buffer.matmul_ring_target`；不把递归聚合入口 `expectation.dialect.dma` 或 `expectation.pass` 作为本轮候选门禁，避免混入无关合同资产。
  - `expectation/utils/case_runner.py` 属于本轮合同运行 helper 资产；`assert_parse_operation_verifier_fails(...)` 必须接受 `VerifyException` 或 `KernelCodeError(ErrorKind.VERIFY, ErrorModule.DIALECT, ...)`，并继续让其它 `KernelCodeError` 冒泡，避免误吞非 verifier 失败。
  - 候选 red contract 基线：当前实现仍按旧 offset-in-type parser / verifier 与 `MultiBufferPass` ring 构造工作，六个 leaf expectation 预期失败，失败面应落在新 `!dma.ring<!nn.memory<...>>` 不被接受、旧 `!dma.ring<#symbol.expr<offset>, ...>` 仍被接受、pass 输出仍打印旧 offset-in-type ring、`MultiBufferPass` 尚未把 loop 外 staging alloc 输入改写为 loop 外 backing ring，或 `MultiBufferPass` 尚未支持 `target=<target-name>` option；用户已确认 expectation 内容与 no-`+1` 对齐口径，no-`+1` 修订后的两路 strict review 已通过，`守护最好的爱莉希雅` 本人守护最终检验已通过，且用户已明确同意推进 execute；恢复 execute 后，execute / review / archive_acceptance 必须把六个 leaf 作为必过合同验收。
  - 当前授权 expectation 文件 sha256 基线：
    - `expectation/dialect/dma/type/ring_type.py`：`2a0b91a850a33899cfb97bf311d62c6155fd6fadfc4457debee715a73b6b3ffe`
    - `expectation/dialect/dma/operation/make_ring.py`：`86eec197f044e3b9f8f75c6042d02772827071cc02aef25eedd6ffe354fb3c43`
    - `expectation/dialect/dma/operation/current_ring.py`：`3213e762c13fec8606b181000b36819bb61281859599da41a137c077ba9c6292`
    - `expectation/dialect/dma/operation/advance_ring.py`：`ed4a9e8b9599877d3a33215f8068edd02da0ae66f6394a7376f6a6dcf2024a17`
    - `expectation/pass/multi_buffer/__main__.py`：`d64e1bb5c6392b395c5d8a6ab521049eb34703a50e37ac49dec906d17280cafb`
    - `expectation/pass/multi_buffer/matmul_ring_memory_stage.py`：`9b1db54b4ee4b548e0fdf5e679df4a86088f961159ed18aa4084ab03f7a45ecd`
    - `expectation/pass/multi_buffer/matmul_ring_target.py`：`e03967f390087182cc65d0c1d6577029c10b884d5f1176a9ac16c838c9f3096f`
    - `expectation/utils/case_runner.py`：`990b5c0d74efb3b96585065fe8cbf8ac85e10efe11e411c2acbbd4df455b382b`
  - execute 阶段只允许读取和运行 `expectation/`，不得修改。

## 计划级任务

- 计划级任务目标：把 `DmaRingType` 收窄为只承载 slot `NnMemoryType`，将 ring stage 数、stage byte offset 与 slot byte size 全部作为 `dma.make_ring` operands 表达，并让 spec、实现、parser/printer、verifier、npu_demo emit 与公开 pytest 闭环。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance/计划书入档验收 -> merge/归档`。
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`；不得另建独立 `refactor` 阶段绕过计划级任务。
- 下发前置：既有 `T-20260605-0b33f547` 已恢复为进行中；不得创建第二个计划级 `execute`。2026-06-06 架构侧已按用户要求修订 `matmul_ring_target` dynamic CHECK 并完成必要复核；`make_ring` 合法边界补丁也已完成两路 strict review 与守护。当前 `case_runner` KCE verifier failure 适配补丁已完成本轮 Feynman / Gibbs round11-R2 strict review 与 `守护最好的爱莉希雅` 本人守护回执，允许通知执行人继续既有任务。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `dma-ring-dynamic-make-ring-operands` | `execute` | 管理员下发的当前仓库独立 worktree | `agents/codex-multi-agents/log/task_records/2026/23/20260604-dma-ring-dynamic-make-ring-operands.md` |

## 迭代审阅记录

### 收敛轮次 1：subagent strict review 返回不通过

- 审阅对象：Draft 1 全文。
- 输入标准包：根 `AGENTS.md`、当前计划阶段约束、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、计划全文、已确认用户口径、待确认项、禁止修改面和验收命令。
- 严格通过口径：公开 API 用户确认来源完整；`DmaRingType` 不再携带 offset；`make_ring` operands 能表达动态 `num/offset/shape_bytes`；现有 `MultiBufferPass` 调用点和测试纳入计划；测试不直连跨文件非公开 helper；没有未授权 `expectation/` 改动；reduce/K 维累加未被误纳入本轮目标。
- 审阅任务：
  - `019e8edd-0396-7151-86ac-8b7af5a225f6`：不通过。
  - `019e8edc-d4e7-77b0-8dc8-89ae5c2fe360`：不通过。
- 发现问题：
  - `expectation/dialect/dma/**` 旧 ring 合同处理方式未确认，计划不可下发。
  - Draft 1 同时写“expectation A/B 待确认”和“本计划不新增或修改 expectation，只用 pytest / 文本扫描验收”，正文冲突。
  - 稳定错误文本从 `count` 改为 `num` 属于公开错误语义，需要用户确认来源或保留为待确认项。
  - 每张小任务卡缺少单列合同验收。
  - `test_multi_buffer_rewrites_matmul_lhs_rhs_pair` 未明确要求断言 `num/offset/shape_bytes` operand 值、backing bytes 与 `DmaRingType(slot_type)`。
  - 缺少旧 `!dma.ring<#symbol.expr<...>, ...>` / `DmaRingType(offset, slot_type)` 负向测试要求。
  - npu_demo emit 对 `make_ring.offset` operand 的消费口径不清。
  - `spec/pass/multi_buffer.md` 对 npu-demo-lowering 调用点的旧说法与当前 `spec/pass/pipeline/npu_demo_lowering.md`、pipeline 测试不一致。
- 主线处理：
  - Draft 2 删除 expectation 冲突表述，改为 A/B 待确认。
  - Draft 2 将 `count -> num` 稳定错误文本列为待用户确认项；未确认前不下发。
  - Draft 2 明确 npu_demo serial emit 本轮继续固定 `{0} /*offset*/`，只要求不再读取 `ring_type.offset`，不新增 runtime ring cursor。
  - Draft 2 明确本轮不把 `MultiBufferPass` 接入 npu-demo-lowering pipeline，只修正 `spec/pass/multi_buffer.md` 中与当前 pipeline 合同冲突的依赖说明。
- 状态：未收敛；待用户 / 架构确认后重新发起 strict review。

### 收敛轮次 2：expectation A 路径架构侧收口

- 触发原因：管理员指出 Draft 1 / Draft 2 不可下发，核心阻断是四个 `expectation/dialect/dma/**` ring 合同仍为旧 offset-in-type 形态，且 strict review / 守护最终检验未完成。
- 架构裁定：采用计划推荐 A，不采用 B；本轮由架构侧先行维护四个 expectation 合同文件，把旧 expectation 从当前正向合同改为历史被拒绝形态。
- 授权范围：
  - `expectation/dialect/dma/type/ring_type.py`
  - `expectation/dialect/dma/operation/make_ring.py`
  - `expectation/dialect/dma/operation/current_ring.py`
  - `expectation/dialect/dma/operation/advance_ring.py`
- 主线处理：
  - `ring_type.py` 正例改为 `!dma.ring<!nn.memory<...>>`，并增加旧 `!dma.ring<#symbol.expr<offset>, ...>` 负例。
  - `make_ring.py` 正反例 result type 改为 `!dma.ring<slot_memory>`，`num/offset/shape_bytes` 继续作为 `dma.make_ring` operands。
  - `current_ring.py` / `advance_ring.py` 的 ring operand type 改为只携带 slot memory type。
  - `count -> num` 稳定错误文本改名不进入本轮；本计划保持既有 `count` 错误文本兼容，不再把该事项作为当前待确认项。
- 状态：A 路径已收口；需要基于 Draft 3 与最新 expectation 重新发起 subagent strict review。

### 收敛轮次 3：Draft 3 subagent strict review 返工

- 审阅对象：`ARCHITECTURE/plan/dma_ring_dynamic_make_ring_operands.md` Draft 3，以及 A 路径授权更新的四个 ring expectation。
- 输入标准包：
  - 根规范：`AGENTS.md`。
  - 当前角色 prompt 摘要：架构计划阶段；正式计划路径为 `ARCHITECTURE/plan/dma_ring_dynamic_make_ring_operands.md`；计划阶段只允许修改本计划与 A 路径授权的四个 expectation；execute 不得修改 `expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`。
  - 相关标准：`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/任务记录约定.md`、`agents/standard/审查规范.md`。
  - 待审文本：Draft 3 全文与四个 expectation 文件。
  - 上一轮问题：A/B expectation 合同处理方式未确认；`count -> num` 稳定错误文本口径未确认；Draft 2 尚未重新 strict review。
  - 本轮收口摘要：采用 A；四个 ring expectation 已改为新 `!dma.ring<!nn.memory<...>>` 合同；`count -> num` 稳定错误文本改名不进入本轮；正式路径统一为 `ARCHITECTURE/plan/dma_ring_dynamic_make_ring_operands.md`。
  - 待用户确认项：无；错误文本改名已排除出本轮。
  - 禁止修改面：除本轮架构侧授权的四个 expectation 和本计划外，不得修改其它 `expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`、`kernel_gen/**`、`spec/**`、`test/**`。
  - 必过验收命令：本计划“验收设计”列出的 pytest、四个 ring leaf expectation、文本扫描和敏感目录门禁。
- 严格通过口径：
  - A 路径 expectation 合同边界必须机械可审查，不得把无关 `expectation.dialect.dma` 全量失败混入本计划。
  - `count` 错误文本保留必须清楚，不得误要求未确认的公开错误文本改名。
  - 公开 API 列表与签名残留扫描必须覆盖 package root。
  - npu_demo DMA emit spec、实现和测试边界必须一致。
  - 敏感目录门禁必须覆盖未跟踪文件。
- Findings：
  - `Goodall`：最小需改项；敏感目录门禁只用 `git diff -- .skills expectation ...`，无法发现未跟踪文件，不能闭环 execute 禁止范围。
  - `Parfit`：最小需改项；`python3 -m expectation.dialect.dma` 作为当前必过合同验收过宽，会混入无关 DMA family expectation；package root / API 列表和公开签名残留扫描未锁住 `DmaMakeRingOp(... count ...)`；目标 spec 包含 npu_demo DMA emit spec，但 S1-S3 未明确同步该 spec。
- 主线处理：
  - 将当前必过 expectation 合同收窄为四个 ring leaf 入口：`expectation.dialect.dma.type.ring_type`、`expectation.dialect.dma.operation.make_ring`、`expectation.dialect.dma.operation.current_ring`、`expectation.dialect.dma.operation.advance_ring`；不把递归聚合入口 `expectation.dialect.dma` 作为当前必过门禁。
  - 在 S2 明确同步 `kernel_gen/dialect/dma/type/__init__.py`、`kernel_gen/dialect/dma/operation/__init__.py`、`kernel_gen/dialect/dma/__init__.py` 的文件级 API 列表和导出说明。
  - 新增公开签名残留扫描，锁定 `DmaMakeRingOp(... count ...)` 与 `DmaRingType(offset ...)` 不得作为公开签名残留；稳定错误文本中的 `count` 单独保留为允许项。
  - 在 S3 增加同步 `spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`，写明 current / advance 继续固定 `{0} /*offset*/`、不消费 `make_ring.offset`、不新增 runtime helper，并补文本验收。
  - 将敏感目录门禁升级为 `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md`，并要求对 ignored expectation 资产记录执行前后文件清单与 sha256 快照。
- 返工复核：
  - `Goodall`：通过；敏感目录门禁返工已收口。
  - `Parfit`：通过；四个 ring leaf expectation 门禁、公开签名残留扫描和 npu_demo DMA emit spec 同步要求已收口。
- 状态：第 3 轮已收敛；守护最终检验已通过。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：两路 Draft 1 strict review 已返回不通过；Draft 3 strict review 已发现最小需改项并完成主线返工；`Goodall` / `Parfit` 返工复核均通过；Draft 4 pass 级 expectation 后的 `Noether-R2` / `Hopper-R2` 曾通过；2026-06-05 用户流程纠偏与 target / dynamic 新修订后，`McClintock` / `Epicurus` 两路 strict review 曾重新完成并通过；no-`+1` 对齐修订后，`Feynman` / `Gibbs` 两路 strict review 已重新完成并通过；2026-06-06 target dynamic CHECK 架构补丁已由 `Hubble` / `Socrates` 审阅通过；2026-06-06 `make_ring` 合法边界补丁已由 `Feynman` / `Gibbs` 审阅通过并完成守护；2026-06-06 `case_runner` KCE verifier failure 适配补丁已完成 `Feynman` / `Gibbs` round11-R2 strict review。
- 最新收敛结论：no-`+1` 修订后 `Feynman` / `Gibbs` 均结论通过，且 `守护最好的爱莉希雅` no-`+1` 修订后守护最终检验已通过；该结论已支持管理员恢复既有 `T-20260605-0b33f547`。2026-06-06 target dynamic CHECK 架构补丁属于 execute 期新修订，`Hubble` / `Socrates` 两路 strict review 已通过，且 `守护最好的爱莉希雅` 本人守护最终检验已通过。`make_ring` 合法边界补丁已由 `Feynman` / `Gibbs` 两路 strict review 通过，并已完成守护最终检验。当前最新补丁为轮次 11 `case_runner` KCE verifier failure 适配，`Feynman` / `Gibbs` round11-R2 均结论通过，`守护最好的爱莉希雅` 本人守护最终检验通过，无阻断、无最小需改项、无待用户确认项。
- 当前遗留项：无设计争议遗留项；no-`+1` 用户裁决与用户 execute 明确同意均已回写。2026-06-06 `case_runner` KCE verifier failure 适配补丁已通过守护最终检验，允许通知执行人继续既有 `T-20260605-0b33f547`；不得创建第二个 execute。

### Draft 3 守护最终检验历史记录

- 检验执行：`守护最好的爱莉希雅`。
- 检验对象：`ARCHITECTURE/plan/dma_ring_dynamic_make_ring_operands.md` Draft 3。
- 正式回执：`agents/codex-multi-agents/log/talk.log:10964`；补催回执：`agents/codex-multi-agents/log/talk.log:10965`。
- 检验范围：正式计划路径、A 路径四个 ring leaf expectation 门禁、`count -> num` 稳定错误文本排除口径、公开 API / package API 列表同步、公开签名残留扫描、npu_demo DMA emit spec、敏感目录门禁、ignored expectation sha256 快照、Goodall / Parfit 返工复核结论。
- 必过门禁：subagent 收敛结论证明无阻断、无最小需改项、无待确认项；用户确认事项已落入计划正文且无剩余待决策项。
- Draft 3 历史结论：通过；无阻断；无最小需改；无待确认；当时允许通知管理员创建唯一计划级 `execute`：`dma-ring-dynamic-make-ring-operands`。
- 关键证据：
  - 守护只读核对对象为正式路径 Draft 3，未创建任务、未修改文件。
  - 临时路径残留扫描 `rg -P (?<!ARCHITECTURE/)plan/dma_ring_dynamic_make_ring_operands.md` 对正式计划文件无输出。
  - 计划正文已写明 A 路径、当前必过 expectation 仅四个 ring leaf，不把 `python3 -m expectation.dialect.dma` 递归聚合入口作为本轮门禁。
  - `count -> num` 稳定错误文本改名排除出本轮，继续保留 `count` 错误文本兼容。
  - Goodall / Parfit 返工复核均通过，subagent 收敛结论写明无阻断、无最小需改项、无待确认项。
  - 四个 ring leaf red contract 下发前均 `exit=1`，失败面集中在旧实现仍要求 `dma.ring` offset 或旧 offset-in-type 仍被接受，符合计划红灯基线；未运行全量 `python3 -m expectation.dialect.dma`。
  - 四个授权 expectation sha256 与计划记录一致，`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md` 无输出。
- 最小阻断项：无。
- 当前状态：以上仅为 Draft 3 历史守护结论；Draft 4 新增 pass 级 expectation 后曾重新执行守护最终检验，后续用户流程纠偏与 target / dynamic 新修订已使 Draft 3 / Draft 4 守护通过均不再作为当前下发依据；当前最新 subagent 状态见第 7 轮记录。

### 收敛轮次 4：用户授权新增 pass 级 expectation

- 触发原因：用户追问是否应补充 pass-level expectation，并确认“可以，你先添加”；随后确认“测试的 alloc loop 的外面”，要求新增 pass expectation 的输入 staging alloc 置于 loop 外。
- 授权范围：
  - 新增 `expectation/pass/multi_buffer/__main__.py`。
  - 新增 `expectation/pass/multi_buffer/matmul_ring.py`。
  - 更新本计划，把新增 pass leaf 纳入当前必过 expectation 合同验收。
- 主线处理：
  - `expectation.pass.multi_buffer.matmul_ring` 通过 `ircheck` 运行 `--pass "multi-buffer={memory-stage=3,fold=false}"`，锁定 matmul lhs/rhs loop-external staging alloc pair 改写后的两组 `dma.make_ring/current_ring/advance_ring`。
  - 该 leaf 小范围随机选择静态 `M/K/N`、dtype、loop end 与 lhs/rhs slot space；输入 IR 将 lhs/rhs staging `dma.alloc` 与对应 `dma.free` 放在 `symbol.for` 外，loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费。
  - 该 leaf 当时按旧公式检查 `num` 由 pass `memory_stage` 参数 / 分析结果计算，本 case 为 `memory_stage=3`，所以 `num` operand 值为 `3`；`shape_bytes` 根据对应 target / slot memory 大小计算，lhs 为 `M * K * dtype_bytes`，rhs 为 `K * N * dtype_bytes`；后续用户已裁决 no-`+1`，当前合同改为 `offset = shape_bytes`、`backing = num * shape_bytes`，并断言两组输出 backing `dma.alloc` 位于 `symbol.for` 前。
  - 该 leaf 要求 `dma.make_ring` result type 为 `!dma.ring<!nn.memory<...>>`，并拒绝旧 `!dma.ring<#symbol.expr<offset>, ...>` pass 输出。
- 本轮新增验证：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile expectation/pass/multi_buffer/__main__.py expectation/pass/multi_buffer/matmul_ring.py`：通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring`：当前实现下 `exit=1`，失败类型为 `IrcheckMatchError: CHECK-NEXT not found on next line`，失败 CHECK 点为未找到 `%[[LHS_BACKING]] = "dma.alloc"... -> <lhs backing i8 memory>` 下一行，说明 pass 输出未出现预期 loop 外 backing `dma.alloc` / `dma.make_ring` 新 ring 合同，符合 red contract 基线。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer`：当前实现下 `exit=1`，聚合到同一个 `matmul_ring` leaf，失败类型同为 `IrcheckMatchError: CHECK-NEXT not found on next line`。
- 状态：Draft 4 已新增 pass 级合同资产；Draft 3 strict review 与守护最终检验结论曾失效为当前下发依据，后续已基于 Draft 4 重新组织 subagent strict review 和守护最终检验复验并通过。

### 收敛轮次 5：Draft 4 strict review 返工

- 触发原因：Draft 4 两路 subagent strict review 均提出最小需改项。
- Noether 最小需改项：
  - S1/S3/S4 尚未明确要求 `spec/pass/multi_buffer.md`、`kernel_gen/passes/multi_buffer.py` 与 `test/passes/test_multi_buffer.py` 同步 loop 外 staging alloc/free 合同，可能让 `expectation` 替代 diff 反推 pytest。
- Hopper 最小需改项：
  - 新增 `matmul_ring.py` 存在多个小私有 helper 与私有互调。
  - 新增 expectation 依赖 `expectation.utils.case_runner` / `expectation.utils.random`，公开 API 列表证据不足。
  - red contract 摘要不够精确。
- 主线处理：
  - 更新 S1：要求 `spec/pass/multi_buffer.md` 明确 lhs/rhs staging `dma.alloc/free` 在 `symbol.for` 外、loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费的公开合同。
  - 更新 S3：要求 `kernel_gen/passes/multi_buffer.py` 接受 loop 外 staging alloc/free 输入，并要求 `test/passes/test_multi_buffer.py::test_multi_buffer_rewrites_matmul_lhs_rhs_pair` 公开 pytest 覆盖 loop 外 staging alloc/free 输入、loop 外 backing `dma.alloc/make_ring` 输出、loop 内 `current/advance`、原 staging alloc/free 移除。
  - 更新 S4：明确该公开 pytest 属于 diff 反推测试，不得被 `expectation.pass.multi_buffer.matmul_ring` 替代。
  - 重写 `expectation/pass/multi_buffer/matmul_ring.py`，仅保留公开 `main() -> None`，不再定义私有 helper，不再导入 `expectation.utils.case_runner` 或 `expectation.utils.random`；只使用标准库 `random` 与 `kernel_gen.tools.ircheck.run_ircheck_text` 公开 API。
  - 重写 `expectation/pass/multi_buffer/__main__.py`，只通过 `importlib.import_module("expectation.pass.multi_buffer.matmul_ring")` 调用 leaf 文件 API 列表中的 `main()`。
  - 精确记录 red contract：`expectation.pass.multi_buffer.matmul_ring` 当前 `exit=1`，失败类型为 `IrcheckMatchError: CHECK-NEXT not found on next line`，失败 CHECK 点为未找到 `%[[LHS_BACKING]] = "dma.alloc"... -> <lhs backing i8 memory>` 下一行。
- 本轮验证：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile expectation/pass/multi_buffer/__main__.py expectation/pass/multi_buffer/matmul_ring.py`：通过；`__pycache__` 已清理。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring`：当前实现下 `exit=1`，失败类型与 red contract 一致。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer`：当前实现下 `exit=1`，聚合到同一个 leaf，失败类型与 red contract 一致。
  - `sha256sum expectation/pass/multi_buffer/__main__.py expectation/pass/multi_buffer/matmul_ring.py`：分别为 `9e898d4dc98641157b4406a9fe39b085ae27a808b9e791ce28348330fcee8a5c`、`1151d25a03ddc519847e42b6f46b681f32e0b8546eb64ba966f33a5712ea2ffa`，与“当前验收资产”一致。
- Draft 4 subagent 返工复核：
  - `Noether-R2`：通过；上一轮 S1/S3/S4 pytest / spec / implementation 边界问题已收口。
  - `Hopper-R2`：通过；上一轮 expectation 私有 helper、跨文件非公开 API 与 red contract 摘要问题已收口。
- 历史五个 leaf red contract 守护前快检（后续已被用户裁决后的六个 leaf 拆分口径取代）：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.type.ring_type`：当前实现下 `exit=1`；失败面为新 `!dma.ring<!nn.memory<...>>` 仍被旧 parser 以 `Expected ',' after dma.ring offset` 拒绝，且旧 offset-in-type 仍未被拒绝。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.make_ring`：当前实现下 `exit=1`；失败面为 make_ring result 新 ring type 仍被旧 parser 以 `Expected ',' after dma.ring offset` 拒绝。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.current_ring`：当前实现下 `exit=1`；失败面为 current_ring 输入新 ring type 仍被旧 parser 以 `Expected ',' after dma.ring offset` 拒绝。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.advance_ring`：当前实现下 `exit=1`；失败面为 advance_ring 输入新 ring type 仍被旧 parser 以 `Expected ',' after dma.ring offset` 拒绝。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring`：当前实现下 `exit=1`；失败类型为 `IrcheckMatchError: CHECK-NEXT not found on next line`，失败 CHECK 点为未找到 `%[[LHS_BACKING]] = "dma.alloc"... -> <lhs backing i8 memory>` 下一行。
- 状态：Draft 4 两路 subagent strict review 曾通过；`守护最好的爱莉希雅` 守护最终检验复验曾通过。2026-06-05 用户指出流程未收口后，该通过结论降级为历史审阅输入；当时存在用户待确认项，不允许通知管理员继续 / 创建唯一计划级 `execute`。该状态曾被后续用户裁决、target / dynamic 新修订、第 7 轮 strict review 通过结论和 no-`+1` 修订前当前文本守护最终检验通过结论取代；当前又被 no-`+1` 对齐修订取代，需重新审阅与守护。

### Draft 4 守护最终检验复验记录

- 检验执行：`守护最好的爱莉希雅`。
- 复验对象：`ARCHITECTURE/plan/dma_ring_dynamic_make_ring_operands.md` Draft 4。
- 复验回执：`agents/codex-multi-agents/log/talk.log:10996`。
- 验证基线：`HEAD=76e19a81`；执行目录 `/home/lfr/kernelcode_generate`；只读复验，未创建任务，未修改文件，未运行全量 `expectation.dialect.dma` 或 `expectation.pass`。
- 历史复验结论：通过；无阻断；无最小需改；无待确认；当时允许通知管理员创建唯一计划级 `execute`：`dma-ring-dynamic-make-ring-operands`。
- 当前效力：2026-06-05 用户指出流程未收口后，本复验结论不再作为当前下发依据；用户随后已确认 expectation 内容并裁决主要冲突 / 争议，且本轮 target 优先、expectation 拆分、dynamic case 与 no-`+1` 对齐口径均发生在该复验之后。第 7 轮两路 subagent strict review 和 no-`+1` 修订前当前文本守护最终检验也已被 no-`+1` 新修订取代；当前必须重新审阅与守护。
- 当时态核对：
  - 计划级任务下发前置当时已修订为 Draft 4 两路 subagent strict review 已完成，守护最终检验复验已通过后允许创建唯一计划级 `execute`。
  - `Noether-R2` 与 `Hopper-R2` 均通过。
  - 正文当时写明无阻断、无最小需改项、无待确认项；该状态已被 2026-06-05 用户流程纠偏取代。
  - 用户确认测试输入 alloc 在 loop 外。
  - `expectation.pass.multi_buffer.matmul_ring` 不替代 diff 反推 pytest。
- 历史五个 leaf red contract 复验摘要（后续已被用户裁决后的六个 leaf 拆分口径取代）：
  - `expectation.dialect.dma.type.ring_type`：当前实现下 `exit=1`；新 ring type 被旧 parser 拒绝，旧 offset-in-type 仍被接受，符合 red contract。
  - `expectation.dialect.dma.operation.make_ring`：当前实现下 `exit=1`；`make_ring` result 新 ring type 被旧 parser 拒绝，符合 red contract。
  - `expectation.dialect.dma.operation.current_ring`：当前实现下 `exit=1`；`current_ring` 输入新 ring type 被旧 parser 拒绝，符合 red contract。
  - `expectation.dialect.dma.operation.advance_ring`：当前实现下 `exit=1`；`advance_ring` 输入新 ring type 被旧 parser 拒绝，符合 red contract。
  - `expectation.pass.multi_buffer.matmul_ring`：当前实现下 `exit=1`；`IrcheckMatchError: CHECK-NEXT not found on next line`，失败点为未找到 `%[[LHS_BACKING]] = "dma.alloc"... -> <lhs backing i8 memory>` 下一行，符合 red contract。
- 历史 sha256 复验摘要：当时六个授权 expectation 与计划记录一致，`ring_type=2a0b91a850a33899cfb97bf311d62c6155fd6fadfc4457debee715a73b6b3ffe`，`make_ring=00fe13afb8d14f123edf7a0182f68d2c49a6e6908700cd96a329e4b920106379`，`current_ring=3213e762c13fec8606b181000b36819bb61281859599da41a137c077ba9c6292`，`advance_ring=ed4a9e8b9599877d3a33215f8068edd02da0ae66f6394a7376f6a6dcf2024a17`，`multi_buffer.__main__=9e898d4dc98641157b4406a9fe39b085ae27a808b9e791ce28348330fcee8a5c`，`matmul_ring=1151d25a03ddc519847e42b6f46b681f32e0b8546eb64ba966f33a5712ea2ffa`；该单 leaf 口径已被后续 `matmul_ring_memory_stage` / `matmul_ring_target` 拆分取代。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md` 无输出。

### 收敛轮次 6：用户流程纠偏与 target 优先 expectation 拆分

- 触发原因：用户指出 Draft 4 流程存在 expectation 内容未确认、冲突未交用户裁决、下发 execute 前未取得用户明确同意三项问题；管理员已暂停 `T-20260605-0b33f547` 与依赖旧计划态的 `T-20260605-360c7137`。
- 用户裁决：
  - 四个 DMA ring leaf expectation 内容可以。
  - pass expectation 的 loop 外 alloc / loop 内 copy+matmul / loop 外 ring 结构符合一般结构；当前仅按 ring 在 loop 外范围收口。
  - `num` 必须由 pass 参数 / 分析结果计算；固定 ring 数沿用现有 `memory-stage` option。
  - `target=<target-name>` 优先于 `memory-stage`；`target-name` 是 target registry 中的目标名，不是 memory space 名；仓库当前已有 `npu_demo` 与 `cpu` 等目标名。
  - `shape_bytes` 按每个 ring slot 的 target memory 大小计算，不按最终 matmul output memory 计算。
  - `memory-stage` 固定 num 与 `target` 优先计算必须拆成独立 expectation 文件。
- 主线处理：
  - 将原单 leaf pass 合同拆成 `expectation.pass.multi_buffer.matmul_ring_memory_stage` 与 `expectation.pass.multi_buffer.matmul_ring_target`。
  - `matmul_ring_memory_stage` 使用 `--pass "multi-buffer={memory-stage=2,fold=false}"`，锁定 `dma.make_ring.num = 2`、`offset = shape_bytes` 与 backing bytes `num * shape_bytes`。
  - `matmul_ring_target` 使用 `--pass "multi-buffer={memory-stage=2,target=npu_demo,fold=false}"`，锁定 `target=npu_demo` 优先；同一 leaf 内覆盖 same-space、different-space 与 dynamic same-space 三个 case：same-space 中 `num = target_space_bytes // (lhs_shape_bytes + rhs_shape_bytes)` 且两组 ring 使用同一个 `num`；different-space 中 lhs/rhs 各自使用所属 target space 的 capacity 与本 space 内 slot `shape_bytes` 合计计算 `num`；dynamic same-space 中 `S1/S2/S3` 来自 kernel 参数，输入 staging 为 `dma.alloc(%s1, %s2)` 与 `dma.alloc(%s2, %s3)`，`shape_bytes` 为 `4*S1*S2` 与 `4*S2*S3`，共享 `num = 524288 floordiv (4*S1*S2 + 4*S2*S3)`；静态 case 均断言不等于 fallback `memory-stage=2`，动态 case 断言不使用 `symbol.get_dim` 伪造 shape 来源。
  - `expectation/pass/multi_buffer/__main__.py` 聚合运行两个 pass leaf；旧 `expectation.pass.multi_buffer.matmul_ring` 不再作为当前合同入口。
- 当前 red contract 快检摘要：
  - `expectation.dialect.dma.type.ring_type`：当前实现下 `exit=1`；新 ring type 被旧 parser 以 `Expected ',' after dma.ring offset` 拒绝，旧 offset-in-type 仍被接受。
  - `expectation.dialect.dma.operation.make_ring`：当前实现下 `exit=1`；`make_ring` result 新 ring type 被旧 parser 拒绝。
  - `expectation.dialect.dma.operation.current_ring`：当前实现下 `exit=1`；`current_ring` 输入新 ring type 被旧 parser 拒绝。
  - `expectation.dialect.dma.operation.advance_ring`：当前实现下 `exit=1`；`advance_ring` 输入新 ring type 被旧 parser 拒绝。
  - `expectation.pass.multi_buffer.matmul_ring_memory_stage`：当前实现下 `exit=1`；`IrcheckMatchError: CHECK-NEXT not found on next line`，失败点为未找到 loop 外 `%[[LHS_BACKING]] = "dma.alloc"...`。
  - `expectation.pass.multi_buffer.matmul_ring_target`：当前实现下 `exit=1`；`IrcheckRunError` 包装 pass 执行失败，根因为当前 `MultiBufferPass` 尚未支持 `target` option（`MultiBufferOptionError: unknown option: target`），尚未进入新增 dynamic same-space CHECK。
- 当时 sha256 基线：`ring_type=2a0b91a850a33899cfb97bf311d62c6155fd6fadfc4457debee715a73b6b3ffe`，`make_ring=00fe13afb8d14f123edf7a0182f68d2c49a6e6908700cd96a329e4b920106379`，`current_ring=3213e762c13fec8606b181000b36819bb61281859599da41a137c077ba9c6292`，`advance_ring=ed4a9e8b9599877d3a33215f8068edd02da0ae66f6394a7376f6a6dcf2024a17`，`multi_buffer.__main__=d64e1bb5c6392b395c5d8a6ab521049eb34703a50e37ac49dec906d17280cafb`，`matmul_ring_memory_stage=9c19a9197f7197322b473ba8fa3e6dd95889667ca4b4ed5b578afbb559e5db31`，`matmul_ring_target=8f153c6551686729f6ddae331604f74e9a2f7926796704bf37cc8ef7c93e9773`；该 sha 已被后续 no-`+1` 对齐修订取代。
- 当时状态：计划与 expectation 内容当时已按用户裁决重收口；随后完成第 7 轮两路 subagent strict review，且 no-`+1` 修订前当前文本守护最终检验通过。该轮结论已被用户 no-`+1` 对齐裁决与本轮新修订取代；当时下发条件未满足，需重新 strict review、守护最终检验，并在守护通过后取得用户对恢复 / 继续唯一计划级 `execute` 的明确同意。当前最新状态见文档信息、计划级任务下发前置和 no-`+1` 修订后记录。

### 收敛轮次 7：target / dynamic 修订后 strict review 通过

- 触发原因：用户确认“推进计划”，要求在 target 优先、expectation 拆分与 dynamic same-space 新修订后继续计划流程。
- 审阅对象：`ARCHITECTURE/plan/dma_ring_dynamic_make_ring_operands.md` 当前文本，以及 `expectation/pass/multi_buffer/__main__.py`、`expectation/pass/multi_buffer/matmul_ring_memory_stage.py`、`expectation/pass/multi_buffer/matmul_ring_target.py` 当前文本。
- 输入标准包：
  - 根规范：`AGENTS.md`。
  - 当前角色 prompt 摘要：计划阶段；当前只读审阅，不得修改文件、不得创建任务、不得恢复 execute、不得写 expectation；两个任务 `T-20260605-0b33f547` 与 `T-20260605-360c7137` 继续暂停。
  - 相关标准：`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/任务记录约定.md`、`agents/standard/审查规范.md`。
  - 待审文本：计划全文与三个 pass expectation 文件。
  - 上一轮问题：用户指出 expectation 内容确认、冲突裁决和下发同意未收口；随后 target 优先、expectation 拆分与 dynamic same-space case 已按用户裁决回写。
  - 本轮收口摘要：`target=<target-name>` 是 target registry 名且优先于 `memory-stage`；same-space / different-space / dynamic same-space 均纳入 target leaf；dynamic shape 来自 kernel 参数 `%s1/%s2/%s3` 与 `dma.alloc(%s1, %s2)` / `dma.alloc(%s2, %s3)`，不得用 `symbol.get_dim` 替代；计划仍要求守护最终检验通过后再取得用户 execute 明确同意。
  - 待用户确认项：无设计待确认项；恢复 / 继续 execute 同意是后续流程门禁。
  - 禁止修改面：不得修改 `expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md` 或任何实现 / spec / test 文件。
  - 必过验收命令：计划“验收设计”列出的 pytest、六个 leaf expectation、文本扫描和敏感目录门禁；本轮 subagent 审阅可只读核对，不替代守护最终检验。
- 严格通过口径：
  - 当前态必须明确暂停执行；不得误写允许创建或恢复 `execute`。
  - 历史 Draft 3 / Draft 4 守护通过记录必须降级为历史输入，不得作为当前放行依据。
  - 动态 target 口径必须贯穿当前验收资产、MultiBufferPass option、完成态、S1/S3/S4、待确认 / 已收口决策。
  - expectation leaf 不得引入私有 helper 或跨文件非公开 API；pytest 与 expectation 合同验收必须区分。
  - 只有无阻断、无最小需改项、无设计待确认项，才允许进入守护最终检验。
- 审阅任务：
  - `McClintock` / `019e9824-d4e8-7192-b24b-65b60453b693`：通过；无阻断；无最小需改项；无设计待确认项；允许进入守护最终检验。
  - `Epicurus` / `019e9825-2de5-7063-9306-74f33ffb647c`：通过；无阻断；无最小需改项；无设计待确认项；允许进入守护最终检验。
- 关键证据：
  - `McClintock` 核对公开 API、验收资产、S1/S3/S4、target expectation 动态 case 与 `__main__.py` 聚合均一致；确认 `matmul_ring_target.py` 只保留公开 `main()`，dynamic case 使用 `%s1/%s2/%s3` 与 `symbol.mul/add/floordiv`，并禁止 `symbol.get_dim`。
  - `Epicurus` 核对当前状态、下发前置、待确认项与用户协同约束一致；确认 Draft 3 / Draft 4 守护通过均已降级为历史输入；“无设计待确认项”和“守护后仍需用户 execute 同意”不冲突，后者是流程门禁。
  - 本地主线只读核对：`sha256sum` 显示 `multi_buffer.__main__=d64e1bb5c6392b395c5d8a6ab521049eb34703a50e37ac49dec906d17280cafb`，`matmul_ring_memory_stage=9c19a9197f7197322b473ba8fa3e6dd95889667ca4b4ed5b578afbb559e5db31`，`matmul_ring_target=8f153c6551686729f6ddae331604f74e9a2f7926796704bf37cc8ef7c93e9773`。
  - 本地主线只读核对：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md` 无输出；主仓与两个 worktree 的 plan / target `cmp` 均为 0。
- 主线处理：无需修订设计内容；仅将本轮 strict review 结果回写计划当前态与收敛结论。
- 当时状态：第 7 轮已收敛；无阻断、无最小需改项、无设计待确认项；允许进入守护最终检验。后续 no-`+1` 修订前守护已通过，但该状态已被用户 no-`+1` 对齐裁决与本轮新修订取代；当前最新状态见 no-`+1` 修订后记录。

### no-`+1` 修订前当前文本守护最终检验记录

- 检验执行：`守护最好的爱莉希雅`。
- 检验对象：`ARCHITECTURE/plan/dma_ring_dynamic_make_ring_operands.md` 当前文本（本记录回写前计划 sha256=`eb3f54d59d77929d9140e8c4280ba15a3e508febeb90311a1e75c1f4a69d6432`）。
- 检验回执：`agents/codex-multi-agents/log/talk.log` 中 `守护最好的爱莉希雅` 向 `大闸蟹` 的 “DMA ring 当前文本守护最终检验回执”。
- 验证基线：`HEAD=76e19a81`；执行目录 `/home/lfr/kernelcode_generate`；只读检验，未创建任务，未修改文件。
- 结论：通过；无阻断；无最小需改；无设计待确认。
- 通过含义：当时仅允许进入下一步向用户确认是否恢复 / 继续唯一计划级 `execute`：`dma-ring-dynamic-make-ring-operands`；在用户明确同意前仍不得恢复 `T-20260605-0b33f547`，不得创建 / 恢复 execute。本记录后用户裁决 no-`+1` 对齐口径并触发计划与 expectation 新修订，因此本守护结论不再作为当前下发依据，当前必须重新 strict review 与守护最终检验。
- 当前态核对：
  - 用户确认项已回写 target 优先、`memory-stage` / `target` 分文件、dynamic same-space kernel 参数来源。
  - `McClintock` / `Epicurus` 两路 strict review 已重新完成并通过，计划记录写明无阻断、无最小需改项、无设计待确认项。
  - 待确认项仅剩守护通过后向用户确认是否恢复 / 继续 execute 的流程门禁，不是设计待确认。
- red contract 快检：
  - 未运行全量 `expectation.dialect.dma` 或 `expectation.pass`；按当前计划 leaf 运行六个入口。
  - 四个 DMA ring leaf 均 `exit=1`，失败面为新 `!dma.ring<!nn.memory<...>>` 被旧 parser 以 `Expected comma after dma.ring offset` 拒绝，且 `ring_type` 负例显示旧 offset-in-type 仍被接受。
  - `expectation.pass.multi_buffer.matmul_ring_memory_stage` `exit=1`，`IrcheckMatchError CHECK-NEXT not found on next line`，仍缺 loop 外 `LHS_BACKING dma.alloc`。
  - `expectation.pass.multi_buffer.matmul_ring_target` `exit=1`，`PassRegistryError -> MultiBufferOptionError unknown option: target`，尚未进入 dynamic CHECK。
  - 以上符合当前旧实现红灯基线。
- sha256 摘要：`multi_buffer.__main__=d64e1bb5c6392b395c5d8a6ab521049eb34703a50e37ac49dec906d17280cafb`，`matmul_ring_memory_stage=9c19a9197f7197322b473ba8fa3e6dd95889667ca4b4ed5b578afbb559e5db31`，`matmul_ring_target=8f153c6551686729f6ddae331604f74e9a2f7926796704bf37cc8ef7c93e9773`，均与守护请求一致。
- 同步与门禁：主仓与 `/home/lfr/wt-20260604-dma-ring-dynamic-make-ring-operands` 的计划和三个 pass expectation 文件 `cmp=0`；`prompt-plan-archive-flow` 已被管理员裁定与 DMA ring 无关，DMA 计划不再作为该任务 staged diff 的一部分；敏感目录门禁 `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md` 无输出；`expectation/pass/multi_buffer` 下无 `__pycache__`。

### 收敛轮次 8：no-`+1` 对齐修订

- 触发原因：用户指出 `offset` 不需要 `+1`；若 `+1` 会在 memory slot 之间制造 1 字节空隙，导致后续地址对齐风险。
- 用户裁决：
  - `MultiBufferPass` ring 化输出必须使用 `offset = shape_bytes`。
  - backing memory bytes 使用 `num * shape_bytes`。
  - `dma.make_ring` 静态 verifier 的非重叠约束从旧 `shape_bytes < offset` 收口为 `shape_bytes <= offset`；稳定错误文本中 `count -> num` 改名仍不进入本轮。
- 主线处理：
  - `expectation.pass.multi_buffer.matmul_ring_memory_stage` 静态公式改为 lhs/rhs `offset = shape_bytes`，backing bytes 改为 `MEMORY_STAGE * shape_bytes`。
  - `expectation.pass.multi_buffer.matmul_ring_target` 静态 same-space / different-space 公式改为每组 `offset = shape_bytes`、`backing = num * shape_bytes`。
  - dynamic same-space case 删除 `symbol.add %[[*_BYTES]], %[[C1]]` 的 offset 计算，`dma.make_ring` 直接复用 `%[[*_BYTES]]` 作为 offset 与 shape_bytes，backing bytes 由 `symbol.mul %[[NUM]], %[[*_BYTES]]` 计算。
  - 计划目标、验收资产、S1/S3/S4、待确认项与用户确认来源均同步 no-`+1` 口径；上一轮 strict review 和守护通过记录降级为历史输入。
- 本轮验证：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile expectation/pass/multi_buffer/__main__.py expectation/pass/multi_buffer/matmul_ring_memory_stage.py expectation/pass/multi_buffer/matmul_ring_target.py`：通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_memory_stage`：当前实现下 `exit=1`，失败为 `IrcheckMatchError CHECK-NEXT not found on next line`，仍缺 loop 外 `%[[LHS_BACKING]] = "dma.alloc"...`，符合 red contract。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_target`：当前实现下 `exit=1`，失败为 `IrcheckRunError` 包装 pass 执行失败，根因为 `MultiBufferOptionError: unknown option: target`，尚未进入 dynamic CHECK，符合 red contract。
  - `sha256sum`：本记录回写前计划 sha 为 `591f364b2cfcaaf9250355ba16e87c68741045b4b0b6fb42d2a27f43c36ffb11`；`multi_buffer.__main__=d64e1bb5c6392b395c5d8a6ab521049eb34703a50e37ac49dec906d17280cafb`，`matmul_ring_memory_stage=9b1db54b4ee4b548e0fdf5e679df4a86088f961159ed18aa4084ab03f7a45ecd`，`matmul_ring_target=7b0afee378158d969925951dc7eb82a0af5491af4bd5c1e2572928d4bb96184f`。
- 本轮 strict review：
  - `Feynman` / `019e9848-7e41-7da1-8d60-f3be334191e6`：通过；无阻断、无最小需改项、无设计待确认项；允许进入守护最终检验。
  - `Gibbs` / `019e9848-ed7c-7a92-97d2-22dd946f4515`：通过；无阻断、无最小需改项、无设计待确认项；允许进入守护最终检验。
- strict review 关键证据：
  - no-`+1` 口径已贯穿计划、验收资产、S1/S3/S4、用户确认来源和 pass expectation；未发现 `offset = shape_bytes + 1` 或 dynamic `symbol.add bytes, 1` 正向残留。
  - verifier 口径自洽：`shape_bytes <= offset`、`backing_bytes >= num * offset`，而 `MultiBufferPass` 生成 `offset = shape_bytes`，所以 backing `num * shape_bytes` 满足容量下界；`num * offset` 只保留在通用 backing capacity / 稳定错误语义处，不是 `MultiBufferPass` backing 输出公式。
  - 计划状态明确暂停 execute，历史 strict review / 守护通过结论均降级，`prompt-plan-archive-flow` 已解耦，不构成本计划等待项。
  - pass expectation 仅公开 `main()`，文件说明 / API 列表合规，未引入私有 helper 或跨文件非公开 API；pytest 与 expectation 角色区分清楚。
  - 主仓与 `/home/lfr/wt-20260604-dma-ring-dynamic-make-ring-operands` 对应四文件 `cmp=0`；敏感目录门禁无输出，`expectation/pass/multi_buffer` 下无 `__pycache__`。
- no-`+1` 修订后守护最终检验：
  - 检验执行：`守护最好的爱莉希雅`。
  - 检验回执：`agents/codex-multi-agents/log/talk.log` 中 “DMA ring no-+1 修订后守护最终检验回执”。
  - 验证基线：`HEAD=76e19a81`；执行目录 `/home/lfr/kernelcode_generate`；只读检验，未创建 / 恢复任务，未修改文件，未运行全量 `expectation.dialect.dma` 或 `expectation.pass`。
  - 结论：通过；无阻断；无最小需改；无设计待确认。
  - 通过含义：仅允许进入下一步向用户确认是否恢复 / 继续唯一计划级 `execute`：`dma-ring-dynamic-make-ring-operands`；在用户明确同意前仍不得恢复 `T-20260605-0b33f547`，不得创建 / 恢复新的 execute。
  - sha 核对：`plan=1640aad0959c3e8f6ceef3f8f159b93adf31fa42a4ad0b6196c689dea2821938`，`multi_buffer.__main__=d64e1bb5c6392b395c5d8a6ab521049eb34703a50e37ac49dec906d17280cafb`，`matmul_ring_memory_stage=9b1db54b4ee4b548e0fdf5e679df4a86088f961159ed18aa4084ab03f7a45ecd`，`matmul_ring_target=7b0afee378158d969925951dc7eb82a0af5491af4bd5c1e2572928d4bb96184f`，均与守护请求一致。
  - 当前态核对：用户 no-`+1` 裁决已回写，`MultiBufferPass` ring 化输出要求 `offset = shape_bytes`、`backing_bytes = num * shape_bytes`；`dma.make_ring` 静态 verifier 已收口为 `shape_bytes <= offset`；`count -> num` 稳定错误文本改名仍排除出本轮；`Feynman` / `Gibbs` 两路 strict review 已通过，正文写明无阻断、无最小需改、无设计待确认。
  - 六个 leaf red contract 快检：四个 DMA ring leaf 均 `exit=1`，失败面为旧 parser 拒绝新 `!dma.ring<!nn.memory<...>>` 且旧 offset-in-type 仍被接受；`expectation.pass.multi_buffer.matmul_ring_memory_stage` `exit=1`，`IrcheckMatchError CHECK-NEXT not found on next line`，仍缺 loop 外 `LHS_BACKING dma.alloc`；`expectation.pass.multi_buffer.matmul_ring_target` `exit=1`，`PassRegistryError -> MultiBufferOptionError unknown option: target`，尚未进入 dynamic CHECK；以上符合当前旧实现红灯基线。
  - 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md` 无输出；`expectation/pass/multi_buffer` 无 `__pycache__`。
- 状态：no-`+1` 修订当时已完成本地自检、两路 strict review 与 `守护最好的爱莉希雅` 本人守护最终检验；用户也已明确同意推进本计划，因此管理员已恢复既有唯一计划级 execute `T-20260605-0b33f547`。该状态已被 2026-06-06 target dynamic CHECK 架构补丁状态覆盖；当前最新状态见“收敛轮次 9”，不得创建第二个 execute。

### 收敛轮次 9：execute 期 target dynamic CHECK 架构补丁

- 触发原因：`T-20260605-0b33f547` 恢复执行后，执行人在 `/home/lfr/wt-20260604-dma-ring-dynamic-make-ring-operands` 运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_target`，失败于 dynamic same-space case 的 `CHECK-NEXT`，现有实现输出已具备 `num * shape_bytes` 运算链，但 `CHECK` 中复杂 `#symbol.expr` 文本与当前 `ircheck` 对 `SymbolExprAttr` 的归一匹配口径不一致。
- 用户 / 执行链路裁定：不要修正 `kernel_gen/tools/ircheck.py`；由架构师修订 `expectation/pass/multi_buffer/matmul_ring_target.py` 合同资产。
- 主线处理：
  - `matmul_ring_target.py` dynamic same-space 中复杂 `#symbol.expr` 结果类型改为捕获并复用 `NUM_EXPR`、`LHS_BACKING_EXPR`、`RHS_BACKING_EXPR`，避免把当前 `ircheck` 的二次归一细节写死为语义真源。
  - `CHECK` 仍逐行锁定 `symbol.floordiv %[[TARGET_BYTES]], %[[TOTAL_BYTES]]`，以及 `symbol.mul %[[NUM]], %[[LHS_BYTES]]` / `symbol.mul %[[NUM]], %[[RHS_BYTES]]`；`dma.alloc`、`dma.make_ring`、`offset = shape_bytes`、`shape_bytes`、新 `!dma.ring<!nn.memory<...>>`、禁止 `symbol.get_dim` 和禁止旧 offset-in-type ring 的合同不变。
  - 未修改 `kernel_gen/tools/ircheck.py`，执行人恢复该文件无 diff 的口径保持不变。
- 本轮验证：
  - 主仓 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile expectation/pass/multi_buffer/matmul_ring_target.py`：通过。
  - DMA worktree `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_target`：通过。
  - DMA worktree `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer`：通过。
  - 主仓与 DMA worktree `expectation/pass/multi_buffer/matmul_ring_target.py` `cmp=0`。
  - DMA worktree `git status --short --untracked-files=all -- kernel_gen/tools/ircheck.py expectation/pass/multi_buffer/matmul_ring_target.py` 无输出。
  - 当前 pass expectation sha：`multi_buffer.__main__=d64e1bb5c6392b395c5d8a6ab521049eb34703a50e37ac49dec906d17280cafb`，`matmul_ring_memory_stage=9b1db54b4ee4b548e0fdf5e679df4a86088f961159ed18aa4084ab03f7a45ecd`，`matmul_ring_target=e03967f390087182cc65d0c1d6577029c10b884d5f1176a9ac16c838c9f3096f`。
- 本轮 strict review：
  - `Hubble` / `019e98d3-b1aa-7290-a60c-809c5f0bd670`：通过；无阻断、无最小需改项、无设计待确认项；确认 dynamic 表达式捕获复用仅适配 `ircheck` 对 `#symbol.expr` 的现有归一打印口径，未放松数据流合同。
  - `Socrates` / `019e98d3-f9b4-7d01-9a87-81cb424b152b`：首轮不通过，最小需改项为全局 / 末尾当前态仍残留 no-`+1` 放行表述；主线已将其改为历史事实并明确轮次 9 当前门禁。复审通过；无阻断、无最小需改项、无设计待确认项。
- strict review 关键证据：
  - `Hubble` 确认 dynamic same-space 仍锁住 `%s1/%s2/%s3` 参数来源、`S1*S2` / `S2*S3`、`lhs_bytes + rhs_bytes`、`target_bytes floordiv total_bytes`、`num * shape_bytes`，并保留 `dma.make_ring(..., bytes, bytes)`、禁止 `symbol.get_dim` 与旧 `!dma.ring<#symbol.expr`。
  - `Socrates` 复审确认计划 sha `232d667a6a4653c1afe32695c7627aa926080a058bf7db2dbd37522ab9a6fb8a` 与 pass expectation sha 匹配，旧 no-`+1` 放行表述已改为历史事实，当前状态以轮次 9 为准，敏感目录门禁无输出。
- 守护最终检验：
  - 检验执行：`守护最好的爱莉希雅` 本人。
  - 检验回执：`agents/codex-multi-agents/log/talk.log` 中 “DMA ring 2026-06-06 execute 期 target dynamic CHECK 架构补丁守护最终检验回执”。
  - 验证基线：主仓 `HEAD=76e19a81`；主仓执行目录 `/home/lfr/kernelcode_generate`；DMA worktree `/home/lfr/wt-20260604-dma-ring-dynamic-make-ring-operands`。
  - 结论：通过；阻断项无；最小需改项无；无设计待确认项。
  - sha 核对：守护检验对象 `plan=039c4ad0dd1cd7d801f0ac1b8a0a67b413d901251c584bae64b3c8663becfb40`，`multi_buffer.__main__=d64e1bb5c6392b395c5d8a6ab521049eb34703a50e37ac49dec906d17280cafb`，`matmul_ring_memory_stage=9b1db54b4ee4b548e0fdf5e679df4a86088f961159ed18aa4084ab03f7a45ecd`，`matmul_ring_target=e03967f390087182cc65d0c1d6577029c10b884d5f1176a9ac16c838c9f3096f`，均与请求一致；主仓与 DMA worktree 四文件 `cmp=0`。
  - 验证摘要：主仓 `py_compile expectation/pass/multi_buffer/matmul_ring_target.py` 通过；DMA worktree `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_target` 通过；DMA worktree `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer` 通过；未运行全量 `expectation.dialect.dma` 或 `expectation.pass`。
  - 通过含义：允许通知执行人继续既有 `T-20260605-0b33f547 / dma-ring-dynamic-make-ring-operands`，基于新 expectation 做验收闭环；不得创建第二个 execute。
- 状态：两路 strict review 与 `守护最好的爱莉希雅` 本人守护最终检验均已完成并通过；无阻断、无最小需改项、无设计待确认项。当时允许通知执行人继续既有 `T-20260605-0b33f547` 基于新 expectation 做验收闭环；不得创建第二个 execute。该状态已被 2026-06-06 `make_ring` 合法边界架构补丁状态覆盖；当前最新状态见“收敛轮次 10”。

### 收敛轮次 10：make_ring `offset == shape_bytes` 合法边界补丁

- 触发原因：execute / review 链路发现 `expectation.dialect.dma.operation.make_ring` 的 `parse-negative-1` 使用 `get_random_int(0, ...)` 生成减量，可能随机得到 `offset == shape_bytes`；同时 case 说明仍写“shape_bytes 不小于 offset 应被拒绝”，与用户已裁决的 no-`+1` / `shape_bytes <= offset` 合法口径冲突。
- 用户 / 架构口径：
  - 用户 no-`+1` 裁决已明确 `offset = shape_bytes` 是 `MultiBufferPass` 本轮应生成的合法边界。
  - `dma.make_ring` 静态 verifier 口径保持 `shape_bytes <= offset`；因此 expectation 负例只能覆盖 `offset < shape_bytes`。
  - 本轮不改变公开 API、稳定错误文本或错误类型；错误类型是否从当前 `KernelCodeError` 改为 `VerifyException` 不得由 execute 擅自实现，若要改变仍需用户另行确认。
- 主线处理：
  - `expectation/dialect/dma/operation/make_ring.py` 的静态正例说明改为覆盖 `offset == shape_bytes` 合法边界。
  - `_static_slot_case(...)` 默认生成 `offset = shape_bytes` 与 `backing_bytes = num * shape_bytes`。
  - `parse-negative-1` 改为使用 `get_random_int(1, ...)`，保证只生成 `offset < shape_bytes`。
  - 负例说明改为“offset 小于 shape_bytes”，不再把等号边界写成失败合同。
- 本轮验证：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile expectation/dialect/dma/operation/make_ring.py`：通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.make_ring`：当前主仓旧实现下 `exit=1`；四个 case 均失败在旧 parser 仍要求 `dma.ring` offset，报 `Expected ',' after dma.ring offset`，符合当前旧实现 red contract 基线；输出中 `parse-positive-1` 已显示 `offset == shape_bytes`。
  - `sha256sum expectation/dialect/dma/operation/make_ring.py`：`86eec197f044e3b9f8f75c6042d02772827071cc02aef25eedd6ffe354fb3c43`。
- 本轮 strict review：
  - `Feynman` / `019e9848-7e41-7da1-8d60-f3be334191e6`：通过；无阻断、无最小需改项、无待用户确认项；可进入守护最终检验。
  - `Gibbs` / `019e9848-ed7c-7a92-97d2-22dd946f4515`：通过；无阻断、无最小需改项、无待确认项。
- strict review 关键证据：
  - 两路均确认最新 sha：`plan=b4ef7c31825bf726e6ccac7220e8e1947afa64bceba81280c5edcf2c22968f86`，`make_ring.py=86eec197f044e3b9f8f75c6042d02772827071cc02aef25eedd6ffe354fb3c43`。
  - 两路均确认 `make_ring.py` 静态正例由 `_static_slot_case()` 默认 `offset_extra=0` 覆盖 `offset == shape_bytes`，`parse-negative-1` 使用 `get_random_int(1, ...)` 只生成 `offset < shape_bytes`。
  - 两路均确认计划当前态、下发前置、当前遗留项和待确认项已写明轮次 10 仍待守护，通过前不得通知执行人继续、不得创建第二个 execute。
  - 两路均确认本轮不改变公开 API、稳定错误文本或错误类型；如需把 `KernelCodeError` 改为 `VerifyException`，仍需另行用户确认。
- 守护最终检验：
  - 检验执行：`守护最好的爱莉希雅` 本人。
  - 验证基线：`plan=3da3916510d7113641c193241702641eb5afba6e99fa0931edd7b90d863f5396`，`make_ring.py=86eec197f044e3b9f8f75c6042d02772827071cc02aef25eedd6ffe354fb3c43`。
  - 结论：通过；阻断项无；最小需改项无；待确认项无。
  - 关键证据：`_static_slot_case()` 默认 `offset_extra=0`，机械生成 `offset = shape_bytes`；`parse-negative-1` 使用 `get_random_int(1, ...)` 只生成 `offset < shape_bytes`；`py_compile` 通过；当前旧实现下 `expectation.dialect.dma.operation.make_ring` `exit=1` 且失败面仍为旧 parser `Expected ',' after dma.ring offset`，符合 red contract。
  - 通过含义：仅解除本轮 `make_ring` 合法边界补丁守护门禁；不得创建第二个 execute，不得扩大公开 API、错误类型、稳定错误文本、pass expectation 或 execute 范围。
- 状态：本轮架构补丁已完成本地验证、两路 strict review 与守护最终检验；该状态已被 2026-06-06 `case_runner` KCE verifier failure 适配补丁覆盖，当前最新状态见“收敛轮次 11”。

### 收敛轮次 11：case_runner 适配 KernelCodeError verifier failure

- 触发原因：execute 恢复 `kernel_gen/dialect/dma/operation/ring.py` 使用公开统一错误 `kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, ...)` 后，`make_ring/current_ring/advance_ring` negative leaf 失败；根因是 `expectation/utils/case_runner.py::assert_parse_operation_verifier_fails(...)` 只捕获 xDSL `VerifyException`，未把公开 KCE verifier 失败视为 verifier failure。
- 架构裁定：
  - 公开 verifier 错误类型继续保持 `KernelCodeError(ErrorKind.VERIFY, ErrorModule.DIALECT, ...)`，不回退 `VerifyException`。
  - `expectation` helper 只在 `KernelCodeError.kind() == "verify"` 且 `KernelCodeError.module() == "dialect"` 时把 KCE 视为 verifier failure。
  - 其它 kind/module 的 `KernelCodeError` 必须继续冒泡，不得被该 helper 当作 verifier failure 吞掉。
- 主线处理：
  - `expectation/utils/case_runner.py` 导入公开 `ErrorKind`、`ErrorModule`、`KernelCodeError`。
  - `assert_parse_operation_verifier_fails(...)` 文档改为接受 `VerifyException` 或 `KernelCodeError(ErrorKind.VERIFY, ErrorModule.DIALECT, ...)`。
  - 新增 `except KernelCodeError as exc` 分支，精确校验 kind/module；匹配失败则原样抛出，匹配成功后沿用 `match` 正则校验。
- 本轮验证：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/wt-20260604-dma-ring-dynamic-make-ring-operands:/home/lfr/kernelcode_generate python3 -m py_compile /home/lfr/kernelcode_generate/expectation/utils/case_runner.py`：通过。
  - 在 `/home/lfr/wt-20260604-dma-ring-dynamic-make-ring-operands` 以 `PYTHONPATH=/home/lfr/wt-20260604-dma-ring-dynamic-make-ring-operands:/home/lfr/kernelcode_generate` 运行六个 leaf 均通过：
    - `python3 -m expectation.dialect.dma.type.ring_type`
    - `python3 -m expectation.dialect.dma.operation.make_ring`
    - `python3 -m expectation.dialect.dma.operation.current_ring`
    - `python3 -m expectation.dialect.dma.operation.advance_ring`
    - `python3 -m expectation.pass.multi_buffer.matmul_ring_memory_stage`
    - `python3 -m expectation.pass.multi_buffer.matmul_ring_target`
  - `sha256sum expectation/utils/case_runner.py`：`990b5c0d74efb3b96585065fe8cbf8ac85e10efe11e411c2acbbd4df455b382b`。
- 本轮 strict review：
  - 首轮 strict review：`Gibbs` 通过；`Feynman` 不通过，阻断项为“禁止修改面与合同真源”和“计划自检”仍只列七个授权资产，未把 `expectation/utils/case_runner.py` 纳入本轮架构授权资产。
  - 主线返工：更新“禁止修改面与合同真源”，明确当前计划阶段允许修改本计划与八个架构授权 expectation / helper 资产；更新计划自检为八资产口径。
  - round11-R2 strict review：`Feynman` / `019e9848-7e41-7da1-8d60-f3be334191e6` 通过；`Gibbs` / `019e9848-ed7c-7a92-97d2-22dd946f4515` 通过；两路均确认无阻断、无最小需改项、无待用户确认项，允许进入守护最终检验。
  - R2 计划 sha256：`07af6429a68accb835bce5929d32e530670de8d2af6f96d98eefb0aa1e06b7ee`；`case_runner.py` sha256 仍为 `990b5c0d74efb3b96585065fe8cbf8ac85e10efe11e411c2acbbd4df455b382b`。
- 守护最终检验：
  - 检验执行：`守护最好的爱莉希雅` 本人。
  - 检验回执：`agents/codex-multi-agents/log/talk.log:11162`，“DMA ring 2026-06-06 case_runner KCE verifier failure 适配补丁守护最终检验回执”。
  - 结论：通过；阻断项无；最小需改项无；待确认项无设计待确认项。
  - sha 核对：`plan=2a45493314ac250d2ee7cf01989dc2a851040d30a5413a896102299e31dbeece`，`case_runner=990b5c0d74efb3b96585065fe8cbf8ac85e10efe11e411c2acbbd4df455b382b`，八个授权 expectation / helper 资产均与请求一致。
  - 通过含义：允许通知执行人继续既有 `T-20260605-0b33f547 / dma-ring-dynamic-make-ring-operands`，基于新 helper 做验收闭环；不得创建第二个 execute，不得扩大公开 API、错误类型、稳定错误文本或 execute 范围。
- 状态：本轮架构补丁已完成本地验证、两路 round11-R2 strict review 与守护最终检验；允许通知执行人继续既有 `T-20260605-0b33f547`。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：待 execute / review / archive_acceptance 链路完成后填写。
- 结论：待执行。
- 验证基线：管理员下发 worktree 最新同步现场。
- 执行目录：管理员下发的当前仓库独立 worktree。
- 同步结果：待记录 `fetch / HEAD / origin/main / merge-base / ahead-behind`。
- 合同验收摘要：待记录 pytest、文本扫描和禁止修改面门禁。
- 最小阻断项或通过摘要：待入档验收填写。

## 计划目标

- `DmaRingType` 公开构造与 assembly 从 `!dma.ring<#symbol.expr<offset>, !nn.memory<...>>` 改为只包含 slot memory type 的 `!dma.ring<!nn.memory<...>>`。
- `dma.make_ring` 的 `num/offset/shape_bytes` 使用 operands 表达，允许动态 `!symbol.int<#symbol.expr<expr>>`，不再要求 ring type 中重复保存 offset。
- `dma.current_ring` 与 `dma.advance_ring` 继续从 ring type 的 slot memory type 推导默认 result type。
- `dma.make_ring` verifier 继续检查 backing memory 是一维 `i8` memory、slot space 与 backing space 一致、静态可判定时 `num > 0`、`offset > 0`、`shape_bytes > 0`、`shape_bytes <= offset`、`backing_bytes >= num * offset`；`MultiBufferPass` 本轮生成的 ring 必须使用 `offset = shape_bytes`，不得额外 `+1` 制造 slot 间字节空隙。
- 动态 `num/offset/shape_bytes` 只做类型校验与可证明静态约束校验；不可静态求值时不得伪造稳定错误，也不得回退到 type 参数。
- 更新 spec、文件级 API 列表、parser/printer、公开测试、现有 `MultiBufferPass` ring 构造点和 npu_demo emit，使旧 offset-in-type 合同不再作为公开正向路径。
- 本计划只提供 `MultiBufferPass` 需要的 ring 参数表达基础；不新增 `MultiBufferPass`，但按用户确认补充 `target=<target-name>` option 并保持既有 `memory-stage` option；不把 `MultiBufferPass` 接入当前 `npu-demo-lowering` pipeline，也不讨论 reduce 类累加或 matmul K 维累加的 ring 化策略。

## 当前基线

- `spec/dialect/dma.md` 当前公开 API 为 `class DmaRingType(offset: SymbolExprAttr, memory_type: NnMemoryType)`。
- `kernel_gen/dialect/dma/type/ring_type.py` 当前文件级 API 列表、构造参数、parser/printer 和 verifier 均要求 `offset` 参数。
- 当前 ring assembly 是 `!dma.ring<#symbol.expr<256>, !nn.memory<...>>`。
- `kernel_gen/dialect/dma/operation/ring.py` 当前 `DmaMakeRingOp` operands 为 `memory/count/offset/shape_bytes`，result 为 `DmaRingType`；verifier 要求 `ring_type.offset == offset operand`。
- `test/dialect/dma/test_operation_ring.py` 当前正向测试构造 `DmaRingType(_expr_attr(256), slot_type)`，并断言旧 assembly。
- 当前仓库已存在 `kernel_gen/passes/multi_buffer.py`、`spec/pass/multi_buffer.md` 和 `test/passes/test_multi_buffer.py`；`MultiBufferPass` 当前通过 `DmaRingType(SymbolExprAttr.from_expr(str(candidate.offset_bytes)), slot_type)` 构造 ring。
- `test/passes/test_template_name_constraints.py` 当前也构造旧 `DmaRingType(SymbolExprAttr.from_expr("16"), slot_type)` 验证 ring op template-name 约束。
- `expectation/dialect/dma/type/ring_type.py`、`expectation/dialect/dma/operation/make_ring.py`、`expectation/dialect/dma/operation/current_ring.py`、`expectation/dialect/dma/operation/advance_ring.py` 已由架构侧先行更新为新 `!dma.ring<!nn.memory<...>>` 正向合同；旧 `!dma.ring<#symbol.expr<offset>, ...>` 已改为应拒绝形态。
- `expectation/pass/multi_buffer/__main__.py`、`expectation/pass/multi_buffer/matmul_ring_memory_stage.py` 与 `expectation/pass/multi_buffer/matmul_ring_target.py` 已由用户授权新增 / 完善为 pass 级合同资产；用户已确认测试输入 alloc 在 loop 外，且 `memory-stage` 固定 num 与 `target` 优先计算必须拆成独立 expectation 文件；当前实现下两个 pass leaf 预期失败，失败点应集中在 `MultiBufferPass` 未将 loop 外 staging alloc 输入改写为新 ring 合同、输出仍使用旧 offset-in-type ring，或尚未支持 `target=<target-name>` option。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 当前通过 `DmaMakeRingOp` owner 和 ring slot type 发射 serial slot view，并固定输出 `{0} /*offset*/`；本计划要求它不再读取 `ring_type.offset`，也不新增真实 runtime ring cursor。
- `spec/pass/multi_buffer.md` 当前写有 `npu-demo-lowering` 固定调用 `MultiBufferPass(memory_stage=3)`；但 `spec/pass/pipeline/npu_demo_lowering.md` 与 `test/passes/pipeline/test_npu_demo_lowering.py` 已明确当前 pipeline 不接入 `multi-buffer`。本计划需修正 `spec/pass/multi_buffer.md` 的过期说法，不改变 pipeline 实现。
- 当前缺口：
  - `offset` 同时存在于 type 参数和 `make_ring` operand，重复真源会阻碍动态 offset。
  - `MultiBufferPass` 要把 loop 外 staging alloc/free 与 loop 内 copy/matmul 消费模式改写为 loop 外 backing storage + loop 内 current/advance ring；它需要 stage 数、offset 和 shape bytes 能作为 SSA operands 参与后续动态或符号化计算，而不是固化在 type 参数中。
- 旧 spec 把 `count/offset/shape_bytes` 写成静态正整数，与动态 operands 口径冲突。
- 旧 parser/printer 与测试会继续接受/输出 offset-in-type，无法锁定新合同。
- 现有 `DmaMakeRingOp` 第二个 operand 命名为 `count`，计划目标为 `num`；参数名变更已由用户确认的 `num/offset/shape_bytes` operands 口径覆盖，但稳定错误文本从 `count` 改为 `num` 未获用户确认，本轮不改旧 `count` 错误文本。

## 禁止修改面与合同真源

- 当前计划阶段允许修改：本计划文件；本轮架构侧 A 路径授权的四个 expectation 文件：`expectation/dialect/dma/type/ring_type.py`、`expectation/dialect/dma/operation/make_ring.py`、`expectation/dialect/dma/operation/current_ring.py`、`expectation/dialect/dma/operation/advance_ring.py`；用户授权新增 / 完善的 `expectation/pass/multi_buffer/__main__.py`、`expectation/pass/multi_buffer/matmul_ring_memory_stage.py` 与 `expectation/pass/multi_buffer/matmul_ring_target.py`；本轮架构裁定授权适配的合同运行 helper：`expectation/utils/case_runner.py`。
- 当前计划阶段禁止修改：除上述八个架构授权 expectation / helper 资产外的其它 `expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`、`kernel_gen/**`、`spec/**`、`test/**`。
- execute 允许范围：当前仓库独立 worktree 内与 DMA ring type/op、`MultiBufferPass` ring 构造点、template-name ring 约束测试、npu_demo ring emit、相关 spec 与公开 pytest 直接相关的文件。
- execute 禁止范围：
  - 未经明确授权新增、删除、重命名或修改任何 `expectation/` 资产。
  - 修改 `.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`。
  - 修改任何带 `[immutable]` / `[immutable-file]` 标记的内容。
  - 新增除本计划列明的 DMA ring API 变更之外的公开 API、工具参数或稳定错误语义。
  - 为兼容旧 `DmaRingType(offset, memory_type)` 增加公开别名、包装转发或隐式双格式解析，除非用户另行确认兼容策略。
  - 跨文件调用非公开 helper，或让测试直接调用跨文件非公开 helper。
- 合同真源优先级：用户确认事项 > 本计划公开 API 设计 > `spec/dialect/dma.md` > 公开 pytest > 当前实现。

## 方案比较与选型

- 不采用方案：继续保留 `DmaRingType(offset, memory_type)`，同时允许 `make_ring.offset` 动态。
  - 原因：type 参数与 operand 会形成重复真源；动态 offset 无法稳定写入 `SymbolExprAttr` 类型参数，也会让 verifier 继续要求二者相等。
- 不采用方案：把 `num/offset/shape_bytes` 都放进 ring type。
  - 原因：这会把运行期或符号值错误地提升为 type 参数，违背用户确认的 operands 口径，也不利于后续 lowering 保持动态值。
- 不采用方案：把本计划扩大成重写或新增 `MultiBufferPass`。
  - 原因：当前仓库已存在 `MultiBufferPass`、spec 和测试；本计划目标是修正 DMA ring API 的参数真源，使 multi-buffer 的 ring 构造建立在正确公开合同上。
- 不采用方案：在本计划内讨论或实现 reduce 类累加 / matmul K 维累加 ring 化。
  - 原因：`plan/multibuffer pass` 已把该事项标为“还需要讨论”；这涉及累加依赖、跨 iteration 可见性和结果正确性，不能混入本轮 DMA ring API 清理。
- 不采用方案：保留旧 assembly 双格式兼容。
  - 原因：用户确认的是 `DmaRingType` 只保留 slot memory type；保留旧 offset-in-type 构造或旧 assembly 会继续暴露重复真源，违背本轮收口目标。
- 采用方案：`DmaRingType(memory_type)` 只描述 slot type，`DmaMakeRingOp(memory, num, offset, shape_bytes, result_type)` 作为 ring 参数唯一真源。
- 最小公开接口：调整 `DmaRingType` 构造签名、`!dma.ring<...>` assembly、`DmaMakeRingOp` 参数命名和 verifier 合同；`current_ring` / `advance_ring` 保持现有公开入口；按用户确认补充 `MultiBufferPass(..., target: str | None = None)` 与 `multi-buffer={target=<target-name>}` option。

## 公开 API 设计

- 用户确认来源：2026-06-04 用户确认按“`DmaRingType` 只保留 slot memory type，动态 `num/offset/shape_bytes` 作为 `make_ring` operands”出计划书。
- API 列表：
  - `class DmaRingType(memory_type: NnMemoryType)`
  - `DmaRingType.parse_parameters(parser: AttrParser) -> Sequence[Attribute]`
  - `DmaRingType.print_parameters(printer: Printer) -> None`
  - `DmaRingType.verify() -> None`
  - `class DmaMakeRingOp(memory: SSAValue | Operation, num: SSAValue | Operation, offset: SSAValue | Operation, shape_bytes: SSAValue | Operation, result_type: DmaRingType)`
  - `DmaMakeRingOp.verify_() -> None`
  - `class DmaCurrentRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
  - `DmaCurrentRingOp.verify_() -> None`
  - `class DmaAdvanceRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
  - `DmaAdvanceRingOp.verify_() -> None`
  - `class MultiBufferPass(memory_stage: int = 3, fold: bool = True, target: str | None = None)`
  - `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- Assembly 设计：
  - 新格式：`!dma.ring<!nn.memory<[...], [...], dtype, #nn.space<...>>>`
  - 不把 `offset`、`num` 或 `shape_bytes` 打印进 `!dma.ring` type。
- 稳定错误语义：
  - 本轮不改变现有 `count` 错误文本；`count` 在错误文本中仅作为历史稳定错误语义保留，不作为 `DmaMakeRingOp` 新公开参数名来源。
  - `dma.ring memory type must be nn.memory`
  - `dma.make_ring memory must be one-dimensional i8 memory`
  - `count must be !symbol.int`
  - `offset must be !symbol.int`
  - `shape_bytes must be !symbol.int`
  - `count must be > 0`
  - `offset must be > 0`
  - `shape_bytes must be > 0`
  - `shape_bytes must be <= offset`
  - `dma.make_ring backing memory bytes must be >= count * offset`
  - `dma.make_ring result ring slot space must match backing memory space`
  - `dma.current_ring result must match ring slot memory type`
  - `dma.advance_ring result must match ring slot memory type`
- 兼容性口径：不保留旧 `DmaRingType(offset, memory_type)` 构造或旧 `!dma.ring<#symbol.expr<offset>, ...>` 正向 parse；旧形态不作为公开正向路径。
- `MultiBufferPass` option 口径：
  - `memory-stage` 保持既有语义：固定 ring num 来源。
  - `target=<target-name>` 中的 `target-name` 是 target registry 的目标名，不是 `tlm1/tlm2/tlm3` 这类 memory space 名；仓库当前内置目标名包括 `npu_demo`、`cpu`。
  - `target` 优先于 `memory-stage`：当 target registry 中目标的对应 slot space memory size 为正时，按每个 target space 分组，把该组本轮所有 ring slot 的 `shape_bytes` 合计为 `total_stage_shape_bytes`，`num = target_space_bytes // total_stage_shape_bytes`；例如同一 target space 下 matmul lhs/rhs 两个 slot 的动态形状为 `S1*S2` 与 `S2*S3`、dtype 为 `f32` 时，动态 shape operands 由 kernel 参数传入，`shape_bytes` 为 `4*S1*S2` 与 `4*S2*S3`，`num = all // (4*S1*S2 + 4*S2*S3)`；`memory-stage` 仅作为没有 target 优先计算时的固定 fallback。
  - 本轮只收口用户确认的 “ring 在 loop 外” 输入结构；未知 target、零容量 target 或其它 ring 位置若需要稳定错误文本 / no-op 语义，必须在实现前回到用户确认，不得由 execute 自行扩展公开错误语义。

## 完成态定义

- `DmaRingType(slot_type)` 可以构造、verify、parse、print；`DmaRingType(offset, slot_type)` 不再是公开正向用法。
- `!dma.ring<!nn.memory<...>>` parse/print 通过，旧 offset-in-type assembly 不作为正向用例保留。
- `DmaMakeRingOp(memory, num, offset, shape_bytes, ring_type)` 使用 operands 作为 `num/offset/shape_bytes` 唯一真源。
- `DmaMakeRingOp` 原公开字段 / 参数 `count` 统一改名为 `num`；本轮稳定错误文本继续沿用现有 `count` 语义，不把 `count -> num` 文本改名纳入当前执行目标。
- `DmaMakeRingOp.verify_()` 对动态 operands 做类型校验，对静态可判定 operands 做正数、`shape_bytes <= offset` 和 backing capacity 校验。
- `DmaCurrentRingOp` / `DmaAdvanceRingOp` 默认 result type 继续使用 `ring_type.memory_type`，显式错误 result type 继续被 verifier 拒绝。
- `dma.advance_ring` 继续作为有副作用 op 保留，不因 result 未使用被 DCE 删除。
- npu_demo ring emit 不再依赖 `ring_type.offset`；本轮 serial 后端继续固定发射 `{0} /*offset*/` 的 current / advance typed view，不消费 `make_ring.offset` 生成真实 cursor，不新增 runtime helper。
- `MultiBufferPass` 中所有 ring 构造点改用 `DmaRingType(slot_type)`，仍通过 `DmaMakeRingOp` operands 传入由 pass 参数 / target registry / 分析结果计算出的 stage 数、offset 和 shape bytes；既有 `memory-stage` option 继续表示固定 ring num，新增 `target=<target-name>` option 以 target registry 的对应 slot space memory size 和该 space 下本轮所有 ring slot `shape_bytes` 合计计算 `num`，且 `target` 优先于 `memory-stage`。
- `test_multi_buffer_rewrites_matmul_lhs_rhs_pair` 必须构造 lhs/rhs staging `dma.alloc/free` 在 `symbol.for` 外、loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费的公开 pytest 输入，并显式断言两组 ring 的 `num/offset/shape_bytes` operand 值、backing bytes 和 `DmaRingType(slot_type)`：`memory_stage` 固定 num 用例中 `num` 由 `memory_stage` 计算，本 case 为 `3`；`shape_bytes` 分别根据 lhs/rhs target / slot memory 大小计算，lhs slot bytes `24`、offset `24`、backing bytes `num * shape_bytes = 72`；rhs slot bytes `48`、offset `48`、backing bytes `num * shape_bytes = 144`。
- `test/passes/test_multi_buffer.py` 必须新增或更新独立 target 优先 pytest，显式传入 `MultiBufferPass(memory_stage=2, fold=False, target="npu_demo")` 或等价 registry option；该用例必须证明 target 名是 registry 目标名、`target` 优先于 `memory-stage`，并按 `npu_demo` target 中同一 slot space memory size 与该 space 下本轮所有 ring slot `shape_bytes` 合计计算共享 `num`，不得把 `target` 误解为 `tlm1/tlm2/tlm3` memory space；还必须覆盖动态 shape operands 来自 kernel 参数的 `dma.alloc(%s1, %s2)` / `dma.alloc(%s2, %s3)` 场景，断言实现用公开 `symbol.mul/add/floordiv` 计算动态 `shape_bytes/total_stage_shape_bytes/num/backing_bytes`，并断言 `offset = shape_bytes`、不得用 `symbol.get_dim` 替代参数来源。
- `test/passes/test_template_name_constraints.py` 等 ring op 调用点同步新 ring type 构造。
- spec、实现文件文件级 API 列表和测试同步新签名；测试不跨文件调用非公开 helper。
- expectation 合同处理完成态：A 路径已采用；架构侧已先行更新 `expectation/dialect/dma/**` ring 合同到新 assembly，且用户授权新增 / 完善 `expectation.pass.multi_buffer.matmul_ring_memory_stage` 与 `expectation.pass.multi_buffer.matmul_ring_target` pass 级合同；execute / review / archive_acceptance 必须将六个 leaf expectation 列为当前必过合同验收。

## 验收设计

- Diff 反推 pytest 最低集合：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/dialect/dma/test_operation_ring.py \
  test/dialect/dma/test_package.py \
  test/passes/test_multi_buffer.py \
  test/passes/test_template_name_constraints.py \
  test/passes/test_registry.py
```

- 若 execute 修改 operation facade 或 DSL DMA helper，还必须补跑：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/operation/test_dma.py \
  test/dsl/ast/nodes/test_dma.py \
  test/dsl/ast/plugin/test_dma.py
```

- 若 execute 修改 npu_demo emit ring，还必须新增 / 更新 `dma_ring` 相关 emit 用例，并补跑：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/dsl/gen_kernel/emit/test_package.py -k "dma_ring"
```

- 若 execute 修改 `npu-demo-lowering` pipeline spec / implementation / registry pipeline 口径，还必须补跑：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/passes/pipeline/test_npu_demo_lowering.py \
  test/passes/test_registry.py
```

- 本计划默认不修改 `npu-demo-lowering` pipeline implementation；只允许修正 `spec/pass/multi_buffer.md` 中与当前 pipeline 合同冲突的旧说明。
- 当前必过 `expectation` 合同验收：仅六个 leaf 入口（四个 DMA ring dialect leaf + 两个 `MultiBufferPass` pass leaf：`memory-stage` 固定 num 与 `target` 优先计算）。
- 架构侧已先行更新 `expectation/dialect/dma/**` ring 合同到新 assembly，并将旧 offset-in-type 作为应拒绝形态；用户授权新增 / 拆分 `MultiBufferPass` pass 级合同，execute / review / archive_acceptance 必须运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.type.ring_type
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.make_ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.current_ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.advance_ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_memory_stage
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_target
```

  本计划不把递归聚合入口 `python3 -m expectation.dialect.dma`、`python3 -m expectation.pass` 或其它 pass family 作为当前必过门禁；若 archive_acceptance 另行要求全量 DMA family / pass package expectation，必须先记录与本轮无关的既有失败隔离口径或转用户确认。
- 文本 / 静态验收：

```bash
rg -n "DmaRingType\\(|!dma\\.ring|dma\\.make_ring|make_ring" \
  spec/dialect/dma.md \
  kernel_gen/dialect/dma/type/ring_type.py \
  kernel_gen/dialect/dma/operation/ring.py \
  kernel_gen/passes/multi_buffer.py \
  kernel_gen/dialect/dma/__init__.py \
  test/dialect/dma/test_operation_ring.py
```

```bash
rg -n "DmaRingType\\([^\\n)]*,[^\\n)]*\\)|!dma\\.ring<#symbol\\.expr|result ring offset must match offset operand|ring_type\\.offset" \
  spec kernel_gen test
```

  第二条扫描不得出现本计划目标范围内的旧正向合同残留；若出现旧错误测试或历史说明，必须明确解释不是正向 API。

```bash
rg -n "DmaMakeRingOp\\([^\\n)]*count|DmaRingType\\(offset|class DmaRingType\\(offset|class DmaMakeRingOp\\([^\\n)]*count" \
  spec kernel_gen test
```

  第三条扫描不得出现公开签名残留；稳定错误文本中的 `count must ...` / `>= count * offset` 是本轮明确保留项，不纳入该扫描。

```bash
rg -n "hasattr\\(ctx|getattr\\(ctx|callable\\(getattr" \
  kernel_gen/dialect/dma/type/ring_type.py \
  kernel_gen/dialect/dma/operation/ring.py \
  kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py
```

  输出必须为空。

- 敏感目录门禁：

```bash
git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md
```

  输出必须为空。
- ignored expectation 资产只读快照：execute / review / archive_acceptance 必须记录执行前后 `expectation/` 文件清单与 sha256 快照，并证明除“当前验收资产”记录的八个授权 expectation 文件基线（六个 leaf + `expectation/pass/multi_buffer/__main__.py` 聚合入口 + `expectation/utils/case_runner.py` helper）外无新增、删除、重命名或内容变化；若发现 expectation 快照变化，当前链路不得通过，必须转用户 / 架构确认。
- Diff 反推要求：执行、review 与 archive_acceptance 必须按实际 diff 补测试；`expectation` 若被用户后续授权，也必须单列为合同验收，不能替代 pytest。

## 计划内小任务

### S1. 固定 DMA ring 公开 API 与 multi-buffer 依赖合同

- 为什么做：当前 `DmaRingType` 把 offset 写入 type 参数，与用户确认的 “type 只保留 slot memory type” 冲突，也让 `MultiBufferPass` 的 stage/offset/shape_bytes 无法只通过 operands 表达。
- 做什么：更新 `spec/dialect/dma.md`、`spec/pass/multi_buffer.md` 依赖说明、相关 API 列表和测试矩阵，把 `DmaRingType(memory_type)`、`!dma.ring<!nn.memory<...>>` 与 `MultiBufferPass` 使用 make_ring operands 的关系写成新公开合同；明确本轮 `MultiBufferPass` 正向匹配输入为 lhs/rhs staging `dma.alloc/free` 在 `symbol.for` 外、loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费；按用户确认补充 `target=<target-name>` option，写清 target registry 名称优先于 `memory-stage` 固定 num；并修正 `spec/pass/multi_buffer.md` 中与当前 npu-demo-lowering pipeline 合同冲突的旧说明。
- 不做什么：不修改实现，不由 execute 擅自修改 `expectation/`，不保留旧 assembly 正向兼容，不把 `MultiBufferPass` 接入当前 `npu-demo-lowering` pipeline。
- 怎么验收：文本扫描命中新 API 和 multi-buffer 依赖说明，旧 offset-in-type 正向合同扫描无残留；计划内 pytest 在实现卡完成后通过。
- 卡住问谁：公开 API 拼写、是否保留旧兼容问用户；multi-buffer/reduce 边界问架构师；流程状态问管理员。
- 上下文摘要：spec 是 execute 的公开合同真源，必须先写清构造签名、assembly、错误语义和非目标。
- 小任务目标：更新 DMA ring spec 合同，使执行人可按新 API 实现并通过文本核对。
- 非目标：不把 `num/offset/shape_bytes` 放回 ring type；不扩展 runtime ring helper；不实现 reduce/K 维累加 ring 化。
- 模块范围：DMA dialect spec、multi-buffer spec 依赖说明与相关公开测试矩阵。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`、无关 spec。
- 合同真源：用户确认 > 本计划 > `spec/dialect/dma.md` > pytest > 当前实现。
- 最小功能闭环：spec 明确 `DmaRingType(memory_type)` 与 `DmaMakeRingOp(..., num, offset, shape_bytes, result_type)`，并明确 `MultiBufferPass` 从 loop 外 staging alloc/free + loop 内 copy/matmul 消费改写为 loop 外 backing ring + loop 内 current/advance；`memory-stage` 固定 ring num，`target=<target-name>` 使用 target registry 中目标名（如 `npu_demo`、`cpu`）并优先按对应 slot space memory size 计算 `num`；动态 shape operands 来自 kernel 参数时，按 `dma.alloc(%s1, %s2)` 这类输入参数生成 symbol arithmetic，不从 memory type 再发 `symbol.get_dim`。
- 执行步骤：
  1. 更新 `spec/dialect/dma.md` 功能简介、API 列表、通用约束、API 详细说明和测试矩阵。
  2. 更新 `spec/pass/multi_buffer.md`，说明 ring 参数来自 `dma.make_ring` operands，不依赖 `DmaRingType` offset 参数；同步 `MultiBufferPass(memory_stage: int = 3, fold: bool = True, target: str | None = None)` 与 `from_options(options)` 的公开 API 列表。
  3. 在 `spec/pass/multi_buffer.md` 明确本轮正向匹配输入：lhs/rhs staging `dma.alloc` 与对应 `dma.free` 位于 `symbol.for` 外，loop body 内只保留 `dma.copy` 与 `kernel.matmul` 对 staging buffer 的消费；改写后原 staging alloc/free 被移除，loop 外生成 backing `dma.alloc` / `dma.make_ring`，loop 内插入 `dma.current_ring` / `dma.advance_ring`。
  4. 在 `spec/pass/multi_buffer.md` 明确 `memory-stage` 仍是固定 ring num 来源；`target=<target-name>` 中的值是 target registry 目标名，不是 memory space 名；当 `target` 可解析且目标对应 slot space memory size 为正时，按 target space 分组，用该 space 下本轮所有 ring slot 的 `shape_bytes` 合计计算 `num = target_space_bytes // total_stage_shape_bytes`，且 `target` 优先于 `memory-stage`；动态 shape operands 来自 kernel 参数时，使用这些参数计算 `shape_bytes/num/backing_bytes`，并令 `offset = shape_bytes`，不得伪造 `symbol.get_dim`。
  5. 修正 `spec/pass/multi_buffer.md` 中 “`npu-demo-lowering` 固定调用 `MultiBufferPass(memory_stage=3)`” 的过期说法，改为与 `spec/pass/pipeline/npu_demo_lowering.md` 一致：当前 pipeline 不接入 `multi-buffer`，multi-buffer 仍为独立 pass / registry 能力。
  6. 核对 `spec/operation/dma.md`、DSL spec 是否公开 ring helper；若有，按同一口径同步；若无，记录不适用。
  7. 按已确认的 expectation 处理方式记录 `expectation/dialect/dma/**`：授权更新时由架构侧先行维护；未授权时只作为历史只读来源，不由 execute 修改。
  8. 用文本扫描确认旧 offset-in-type 正向合同不再残留。
- 合同验收：
  - `rg -n "DmaRingType\\(memory_type|!dma\\.ring<!nn\\.memory|num.*offset.*shape_bytes" spec/dialect/dma.md`
  - `rg -n "make_ring.*operand|dma\\.current_ring|dma\\.advance_ring" spec/pass/multi_buffer.md`
  - `rg -n "loop 外.*dma\\.alloc|symbol\\.for.*copy.*matmul|current_ring.*advance_ring" spec/pass/multi_buffer.md`
  - `rg -n "target=<target-name>|target registry|memory-stage.*固定|target.*优先|total_stage_shape_bytes|S1\\*S2.*S2\\*S3|kernel 参数|symbol\\.floordiv" spec/pass/multi_buffer.md`
  - `rg -n "不接入.*multi-buffer|独立 pass|registry" spec/pass/multi_buffer.md`
  - `rg -n "!dma\\.ring<#symbol\\.expr|DmaRingType\\(offset" spec/dialect/dma.md spec/pass/multi_buffer.md` 无正向合同残留。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py`
- 记录要求：写清公开 API 变更用户确认来源、multi-buffer 动机、旧兼容不保留的计划依据。

### S2. 实现 DmaRingType 单参数 type 与 make_ring 动态 operands

- 为什么做：实现仍要求 `DmaRingType(offset, memory_type)`，parser/printer/verifier 也绑定旧 offset 参数。
- 做什么：修改 `kernel_gen/dialect/dma/type/ring_type.py` 和 `kernel_gen/dialect/dma/operation/ring.py`，移除 type offset 参数，把 `num/offset/shape_bytes` operands 作为唯一 ring 参数真源。
- 不做什么：不新增跨文件公开 helper，不保留未确认旧格式兼容，不改 `current_ring` / `advance_ring` 的公开语义。
- 怎么验收：`test/dialect/dma/test_operation_ring.py` 覆盖新构造、新 assembly、动态 operands、静态边界错误和 side effect 保留。
- 卡住问谁：IRDL 参数重排问架构师；发现必须新增计划外公开 API 或改变计划外稳定错误文本时问用户。
- 上下文摘要：type 参数减少是公开 API 和 parser/printer 变更，必须同步文件级 API 列表和函数注释。
- 小任务目标：实现 `DmaRingType(memory_type)` 和 `DmaMakeRingOp(..., num, offset, shape_bytes, result_type)`，并让 dialect ring pytest 通过。
- 非目标：不实现真实 runtime ring cursor；不改变 npu_demo serial no-op advance 口径。
- 模块范围：`kernel_gen/dialect/dma/type/`、`kernel_gen/dialect/dma/operation/ring.py`、DMA dialect package root。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`、无关 dialect/pass/emit 文件。
- 合同真源：用户确认 > 本计划 > `spec/dialect/dma.md` > `test/dialect/dma/test_operation_ring.py` > 当前实现。
- 最小功能闭环：新 ring type parse/print/verify 成功，make_ring verifier 不再比较 `ring_type.offset`，静态可判定边界仍失败。
- 执行步骤：
  1. 更新 `ring_type.py` 文件级 API 列表、构造参数、parser/printer 和 verifier，移除 offset 校验 helper 或将其改为当前文件内必要逻辑。
  2. 更新 `operation/ring.py` 文件级 API 列表和 `DmaMakeRingOp` 参数名；将公开参数和正向调用点命名收口为 `num`，保持 operand 顺序为 `memory, num, offset, shape_bytes, result_type`；稳定错误文本继续沿用既有 `count` 文本。
  3. 更新 make_ring verifier：`num/offset/shape_bytes` 只来自 operands；动态表达式只做类型验证，静态可判定时做数值约束。
  4. 更新 `current_ring` / `advance_ring` 默认 result type 读取逻辑，使其只依赖 `ring_type.memory_type`。
  5. 更新 `kernel_gen/dialect/dma/type/__init__.py`、`kernel_gen/dialect/dma/operation/__init__.py`、`kernel_gen/dialect/dma/__init__.py` 的文件级 API 列表和导出说明，确保公开签名不再出现 `DmaRingType(offset, ...)` 或 `DmaMakeRingOp(..., count, ...)`。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_operation_ring.py test/dialect/dma/test_package.py`
  - `test/dialect/dma/test_operation_ring.py` 必须新增或更新负向用例，断言旧 `!dma.ring<#symbol.expr<...>, ...>` 不再作为正向 parse 路径，旧 `DmaRingType(offset, slot_type)` 不再作为公开正向构造路径。
  - `test/dialect/dma/test_operation_ring.py` 必须覆盖动态 `num/offset/shape_bytes` operands 不被 type 参数阻断。
  - `rg -n "ring_type\\.offset|result ring offset must match offset operand|!dma\\.ring<#symbol\\.expr" kernel_gen/dialect/dma test/dialect/dma` 无新正向残留。
  - `rg -n "DmaMakeRingOp\\([^\\n)]*count|DmaRingType\\(offset|class DmaRingType\\(offset|class DmaMakeRingOp\\([^\\n)]*count" spec/dialect/dma.md kernel_gen/dialect/dma test/dialect/dma/test_operation_ring.py` 无公开签名残留；稳定错误文本中的 `count` 允许保留。
- 记录要求：写清 API 列表同步、旧 helper 删除或保留依据、动态 operand 校验边界、Diff 反推自测和敏感目录门禁。

### S3. 更新公开测试、MultiBufferPass、npu_demo ring emit 与必要调用点

- 为什么做：公开测试、现有 `MultiBufferPass` 和 npu_demo ring emit 仍可能构造旧 `DmaRingType(offset, slot_type)` 或读取 `ring_type.offset`。
- 做什么：更新公开 pytest、`kernel_gen/passes/multi_buffer.py`、npu_demo emit ring 逻辑和直接调用点，使所有正向路径使用新 ring type 与 make_ring operands，并让 `MultiBufferPass` 覆盖用户确认的 loop 外 staging alloc/free 输入合同、`memory-stage` 固定 num 路径和 `target=<target-name>` 优先计算路径。
- 不做什么：不新增 runtime ring object，不改变 `advance_ring` side effect 语义，不扩展到无关 DMA op。
- 怎么验收：dialect ring pytest、multi-buffer pytest、registry pytest、template-name constraints pytest、emit 相关最小 pytest 和文本扫描通过。
- 卡住问谁：npu_demo emit 是否需要真实 ring cursor或 multi-buffer 边界问架构师；公开后端 runtime API 变化问用户。
- 上下文摘要：即使 dialect 通过，emit 和调用点仍可能保留旧 API，必须用文本扫描和 diff 反推测试锁住。
- 小任务目标：清理旧 `DmaRingType(offset, ...)` 调用点和 `ring_type.offset` 依赖，使公开测试与 `MultiBufferPass` 覆盖新 ring 合同和 loop 外 staging alloc/free 输入合同。
- 非目标：不修改 CUDA 或其它 target 的 ring runtime，除非实际 diff 证明它们直接依赖旧公开 API；不新增除用户确认的 `target=<target-name>` 之外的 registry option；不自行定义未知 target、零容量 target 或其它 ring 位置的稳定错误 / no-op 边界。
- 模块范围：DMA ring tests、`test/passes/test_multi_buffer.py`、`test/passes/test_template_name_constraints.py`、`kernel_gen/passes/multi_buffer.py`、npu_demo DMA ring emit、必要的 operation/DSL 调用点。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`、无关 target emit。
- 合同真源：用户确认 > 本计划 > spec > pytest > emit 当前实现。
- 最小功能闭环：所有正向测试和 `MultiBufferPass` 使用 `DmaRingType(slot_type)`；`MultiBufferPass` 公开 pytest 覆盖 lhs/rhs staging alloc/free 在 loop 外、loop 内只 copy/matmul 的输入合同；stage 数、offset 和 shape bytes 仍由 `DmaMakeRingOp` operands 传入；`memory-stage` 路径固定 num，`target=npu_demo` 路径按 target registry 中同一 slot space memory size 与该 space 下本轮所有 ring slot `shape_bytes` 合计计算共享 num 且优先于 `memory-stage`；npu_demo serial emit 固定发射 `{0} /*offset*/`，但不得读取 `ring_type.offset` 或新增未确认 runtime helper；side effect test 继续通过。
- 执行步骤：
  1. 更新 `test/dialect/dma/test_operation_ring.py` 的构造、parse/print 和 verifier edge case。
  2. 增加动态 `num/offset/shape_bytes` operand case，证明动态表达式不被 type 参数阻断。
  3. 更新 `kernel_gen/passes/multi_buffer.py`，将 ring type 构造改为 `DmaRingType(slot_type)`，并保持由 pass 参数 / target registry / 分析结果计算 `num`、`offset`、`shape_bytes` operands 的生成逻辑。
  4. 更新 `kernel_gen/passes/multi_buffer.py` 的匹配逻辑，使其接受 lhs/rhs staging `dma.alloc/free` 在 `symbol.for` 外、loop body 内只消费 staging buffer的正向输入；改写后必须删除原 staging alloc/free，loop 外生成 backing `dma.alloc` / `dma.make_ring`，loop 内插入 `dma.current_ring` / `dma.advance_ring` 并替换 `dma.copy` target 与 `kernel.matmul` lhs/rhs operand。
  5. 更新 `kernel_gen/passes/multi_buffer.py` 的 option 解析，保留 `memory-stage`，新增 `target` 字段；`target` 值必须按 target registry 目标名解析（如 `npu_demo`、`cpu`），不得按 memory space 名解析；当 target 对应 slot space memory size 为正时，按 target space 分组，用该 space 下本轮所有 ring slot 的 `shape_bytes` 合计计算 `num = target_space_bytes // total_stage_shape_bytes`，并优先于 `memory-stage`。
  6. 更新 `test/passes/test_multi_buffer.py` 中 `test_multi_buffer_rewrites_matmul_lhs_rhs_pair`，公开构造 lhs/rhs staging `dma.alloc/free` 位于 `symbol.for` 外、loop body 内只含 `dma.copy` 与 `kernel.matmul` 消费的输入，并显式断言两组 `DmaMakeRingOp.num/offset/shape_bytes` operand 值、backing byte pool shape 和 `DmaRingType(slot_type)`；按当前 memory-stage 测试类型，`num` 由 `memory_stage` 计算，本 case 为 `3`，`shape_bytes` 根据 lhs/rhs target / slot memory 大小计算，lhs 应为 `num=3, offset=24, shape_bytes=24, backing=72`，rhs 应为 `num=3, offset=48, shape_bytes=48, backing=144`。
  7. 在 `test/passes/test_multi_buffer.py` 新增 target 优先公开 pytest，显式传入 `target="npu_demo"` 且同时给出 `memory_stage=2`；覆盖 same-space、different-space 与 dynamic same-space：same-space 断言 `num = target_space_bytes // (lhs_shape_bytes + rhs_shape_bytes)` 且两组 ring 共享该 `num`，different-space 断言 lhs/rhs 各自按所属 target space 的 capacity 与本 space 内 slot `shape_bytes` 合计计算 `num`，dynamic same-space 构造 kernel 参数 `%s1/%s2/%s3` 与 `dma.alloc(%s1, %s2)` / `dma.alloc(%s2, %s3)` 输入，断言通过 `symbol.mul/add/floordiv` 计算 `4*S1*S2`、`4*S2*S3`、`num = target_space_bytes floordiv (4*S1*S2 + 4*S2*S3)` 与动态 backing bytes；再断言 `offset = shape_bytes`、每组 backing bytes 为对应 `num * shape_bytes`，静态 case 的 `num` 不等于 fallback `memory_stage=2`，动态 case 不出现 `symbol.get_dim`。
  8. `test/passes/test_multi_buffer.py` 必须断言 loop 外 backing `dma.alloc/make_ring` 生成在 `symbol.for` 前、loop 内 `dma.current_ring` / `dma.advance_ring` 成对出现、原 staging alloc/free 不再残留；该 pytest 是本轮 diff 反推测试，不得用 `expectation.pass.multi_buffer.matmul_ring_memory_stage` 或 `expectation.pass.multi_buffer.matmul_ring_target` 替代。
  9. 更新 `test/passes/test_template_name_constraints.py` 中的旧 ring type 构造。
  10. 更新 `spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`，补齐 `make_ring` / `current_ring` / `advance_ring` emit 合同：current / advance 继续固定 `{0} /*offset*/`，不消费 `make_ring.offset` 生成真实 cursor，不新增 runtime helper。
  11. 更新 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py`，移除 `ring_type.offset` 依赖，保持 serial fixed-offset view 输出。
  12. 在 `test/dsl/gen_kernel/emit/test_package.py` 新增 / 更新 `dma_ring` 相关用例，断言 current / advance 输出仍为 `{0} /*offset*/` serial view，且 invalid source / invalid result type 公开错误语义保持稳定。
  13. 用 `rg` 查找并修复其它正向调用点。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_operation_ring.py test/dialect/dma/test_package.py test/passes/test_multi_buffer.py test/passes/test_template_name_constraints.py test/passes/test_registry.py`
  - `test/passes/test_multi_buffer.py` 必须包含公开 pytest，覆盖 lhs/rhs staging `dma.alloc/free` 在 `symbol.for` 外、loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费、改写后 loop 外 backing `dma.alloc/make_ring` 与 loop 内 `current/advance` 成对出现、原 staging alloc/free 被移除；该 pytest 不得被 expectation 替代。
  - `test/passes/test_multi_buffer.py` 必须包含 target 优先公开 pytest，覆盖 `target="npu_demo"` 优先于 `memory_stage=2`，并按同一 target space memory size 与该 space 下本轮所有 ring slot `shape_bytes` 合计计算共享 num；动态子用例必须使用 kernel 参数驱动 `dma.alloc(%s1, %s2)` / `dma.alloc(%s2, %s3)`，并断言 symbol arithmetic 链与无 `symbol.get_dim` 残留。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py -k "dma_ring"`
  - `test/passes/test_multi_buffer.py::test_multi_buffer_rewrites_matmul_lhs_rhs_pair` 必须覆盖 loop 外 staging alloc/free 输入与 loop 外 backing ring 输出，且该覆盖属于 diff 反推 pytest。
  - `rg -n "DmaRingType\\([^\\n)]*,[^\\n)]*\\)|!dma\\.ring<#symbol\\.expr|ring_type\\.offset" spec kernel_gen test` 无未解释正向残留。
  - `rg -n "make_ring|current_ring|advance_ring|\\{0\\} /\\*offset\\*/|runtime helper|runtime cursor" spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py test/dsl/gen_kernel/emit/test_package.py` 命中新 ring emit 合同和 serial fixed-offset 口径，不得要求新增 runtime helper / cursor。
- 记录要求：写清更新的调用点、未触及 target 的依据、Diff 反推测试、减法检查和敏感目录门禁。

### S4. 总体验收、记录与可合并候选检查

- 为什么做：本计划涉及公开 API、spec、实现和测试同步，必须在进入 review 前完成一致性和敏感面门禁。
- 做什么：执行最低 pytest、实际 diff 反推测试、文本扫描、敏感目录门禁，并补齐任务记录。
- 不做什么：不以 expectation 替代 pytest；不在未授权情况下修改合同资产；不把未作为当前门禁的旧 expectation 写成通过。
- 怎么验收：验收设计全部通过，任务记录包含执行前阅读、最小功能闭环、Diff 反推自测、减法检查、自检和禁止修改面。
- 卡住问谁：流程 / 状态问管理员；验收口径问架构师；需要扩大公开 API 或 expectation 授权问用户。
- 上下文摘要：execute 结束前必须证明当前 diff 没有旧 API 残留、没有敏感文件越权、没有跨文件非公开 helper 使用。
- 小任务目标：完成 DMA ring 动态 operands 改动的测试与记录闭环，提交 review。
- 非目标：不做 merge，不归档计划。
- 模块范围：本计划改动范围和任务记录。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`，以及任何未授权 immutable 文件。
- 合同真源：用户确认 > 本计划 > spec > pytest > 当前实现。
- 最小功能闭环：计划列出的 pytest 和文本门禁通过，记录齐全，可交给 review。
- 执行步骤：
  1. 运行验收设计的最低 pytest。
  2. 按实际 diff 补跑 operation/DSL/emit 相关 pytest。
  3. 运行旧 API 残留扫描、ctx 能力探测扫描和敏感目录门禁。
  4. 补齐任务记录并回报管理员进入 review。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_operation_ring.py test/dialect/dma/test_package.py test/passes/test_multi_buffer.py test/passes/test_template_name_constraints.py test/passes/test_registry.py`
  - `test/passes/test_multi_buffer.py` 必须包含公开 pytest，覆盖 lhs/rhs staging `dma.alloc/free` 在 `symbol.for` 外、loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费、改写后 loop 外 backing `dma.alloc/make_ring` 与 loop 内 `current/advance` 成对出现、原 staging alloc/free 被移除；该 pytest 属于 diff 反推测试，不得被 `expectation.pass.multi_buffer.matmul_ring_memory_stage` 或 `expectation.pass.multi_buffer.matmul_ring_target` 替代。
  - `test/passes/test_multi_buffer.py` 必须包含 target 优先公开 pytest，覆盖 `target="npu_demo"` 按同一 target space memory size 与该 space 下本轮所有 ring slot `shape_bytes` 合计计算共享 num，且优先于 `memory_stage=2`；动态子用例必须覆盖 kernel 参数 `%s1/%s2/%s3` 输入和 `symbol.mul/add/floordiv` 生成。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py -k "dma_ring"`
  - 若实际 diff 修改 `npu-demo-lowering` pipeline spec / implementation / registry pipeline 口径，补跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py`。
  - 运行六个 leaf expectation：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.type.ring_type`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.make_ring`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.current_ring`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.advance_ring`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_memory_stage`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer.matmul_ring_target`
  - 实际 diff 反推 pytest。
  - 文本 / 静态验收全部满足。
  - `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md` 输出为空。
  - ignored `expectation/` 文件清单前后一致，八个授权 expectation 文件（六个 leaf + `expectation/pass/multi_buffer/__main__.py` 聚合入口 + `expectation/utils/case_runner.py` helper）sha256 必须匹配“当前验收资产”记录的基线；若不一致，需转用户 / 架构确认。
- 记录要求：写清执行前阅读、最小功能闭环、Diff 反推自测、减法检查、自检、禁止修改面、公开 API 用户确认来源和剩余风险。

## 计划自检与返工口径

- 自检：
  - 已把公开 API 变更写成 `DmaRingType(memory_type)` 与 `DmaMakeRingOp(..., num, offset, shape_bytes, result_type)`。
  - 已记录用户确认来源和 multi-buffer 动机。
  - 已把 `expectation/` 列为 execute 禁止修改面；本轮架构侧只维护八个授权 expectation / helper 资产：四个 DMA ring expectation 文件、`expectation/pass/multi_buffer/__main__.py`、两个 pass leaf 文件与 `expectation/utils/case_runner.py`。
  - 已采用 A 路径并更新 `expectation/dialect/dma/**` ring 合同；已按用户裁决将 pass 级合同拆成 `expectation.pass.multi_buffer.matmul_ring_memory_stage` 与 `expectation.pass.multi_buffer.matmul_ring_target`；已按用户补充在 target leaf 增加 kernel 参数传入的动态 shape case；用户已确认六个 leaf expectation 内容可接受。
  - 已将 `count -> num` 稳定错误文本改名排除出本轮执行目标，保留既有 `count` 错误文本兼容。
  - 已区分 pytest / 文本扫描 / expectation 合同验收。
  - 已组织两路 subagent strict review，Draft 1 结论均为不通过；Draft 3 曾完成 strict review 与守护最终检验；Draft 4 新增 pass 级 expectation 后，Noether-R2 / Hopper-R2 返工复核均已通过，守护最终检验复验已通过；用户于 2026-06-05 指出 expectation 内容确认、争议裁决和下发同意未收口后，本轮 target 优先 / expectation 拆分 / 动态 shape case 曾重新完成 `McClintock` / `Epicurus` 两路 strict review 并通过，no-`+1` 修订前当前文本守护最终检验曾通过；no-`+1` 新修订后已重新完成 `Feynman` / `Gibbs` 两路 strict review 并通过，`守护最好的爱莉希雅` 本人守护最终检验已通过；用户已明确同意恢复 / 继续唯一计划级 execute。2026-06-06 target dynamic CHECK 架构补丁已完成 `Hubble` / `Socrates` 两路 strict review 与 `守护最好的爱莉希雅` 本人守护最终检验，均通过。2026-06-06 `make_ring` 合法边界补丁已完成本地验证、`Feynman` / `Gibbs` 两路 strict review 与守护最终检验。当前 `case_runner` KCE verifier failure 适配补丁已完成本地验证、`Feynman` / `Gibbs` round11-R2 strict review 与守护最终检验。
- 返工口径：只要仍有能提升质量、可读性、可维护性、测试有效性、API 清晰度或验收可信度的可执行项，就回到计划修订或 execute 返工；不得以“当前能跑”为理由放行旧 offset-in-type 残留。

## 待确认项

- 设计决策：当前无剩余设计待确认项；`target=<target-name>`、`target` 优先、`memory-stage` 固定 num、`shape_bytes`、no-`+1` 对齐、`offset == shape_bytes` 合法边界、loop 外 ring 范围和动态 shape 参数来自 kernel 参数的口径均已按用户裁决回写。
- 下发同意与流程门禁：
  - no-`+1` 修订后的 `Feynman` / `Gibbs` 两路 subagent strict review 已完成并通过；`守护最好的爱莉希雅` 本人 no-`+1` 修订后守护最终检验已通过，回执可追溯到 `agents/codex-multi-agents/log/talk.log` 的“DMA ring no-+1 修订后守护最终检验回执”。用户已于 2026-06-05 明确回复“好的，可以推进这个计划了”，因此管理员已恢复既有唯一计划级 `execute`：`T-20260605-0b33f547`。
  - 2026-06-06 target dynamic CHECK 架构补丁不创建第二个计划级 `execute`，也不重新耦合 prompt-plan 任务。
  - 当前流程门禁：2026-06-06 `case_runner` KCE verifier failure 适配补丁已完成两路 round11-R2 strict review 与 `守护最好的爱莉希雅` 本人守护最终检验；允许通知执行人继续既有 `T-20260605-0b33f547`，不得创建第二个 execute。
- 后续非本轮事项：若后续希望把稳定错误文本从 `count must ...` / `>= count * offset` 改成 `num must ...` / `>= num * offset`，必须另行取得用户确认并重新修订计划；本轮不实现、不验收该错误文本改名。

## 已收口决策

- 不保留旧 `DmaRingType(offset, memory_type)` 构造或旧 `!dma.ring<#symbol.expr<offset>, !nn.memory<...>>` 正向 parse。
- `DmaMakeRingOp` 第二个公开参数命名统一为 `num`，表示 ring stage 数；operand 顺序保持 `memory, num, offset, shape_bytes, result_type`。
- 稳定错误文本本轮不改名，继续保留既有 `count` 文本兼容；`count -> num` 错误文本改名不在当前计划范围。
- `expectation/dialect/dma/**` 合同处理方式采用 A；四个 ring expectation 已由架构侧先行更新；`expectation.dialect.dma.operation.make_ring` 已补齐 `offset == shape_bytes` 合法边界正例，负例只覆盖 `offset < shape_bytes`；`expectation/utils/case_runner.py` 已按公开 KCE verifier 语义适配 `assert_parse_operation_verifier_fails(...)`；用户授权新增 pass 级 expectation，并于 2026-06-05 裁决 expectation 内容可接受；当前 pass 合同已拆成 `expectation.pass.multi_buffer.matmul_ring_memory_stage` 与 `expectation.pass.multi_buffer.matmul_ring_target`；execute 不得修改 expectation，恢复 execute 后六个 leaf expectation 作为当前合同验收。
- 动态 shape case 纳入 `expectation.pass.multi_buffer.matmul_ring_target`；动态维度由 kernel 参数 `%s1/%s2/%s3` 传入，输入 staging 形态为 `dma.alloc(%s1, %s2)` / `dma.alloc(%s2, %s3)`，不以 `symbol.get_dim` 作为本 case 的 shape 来源。
- npu_demo serial ring emit 本轮继续发射固定 `{0} /*offset*/` 的 current / advance view，只移除 `ring_type.offset` 依赖，不消费 `make_ring.offset` 生成真实 cursor，不新增 runtime ring helper。
- 当前 `npu-demo-lowering` pipeline 不接入 `MultiBufferPass`；本计划只修正 `spec/pass/multi_buffer.md` 的过期表述，不修改 pipeline 实现或新增 pipeline option。
- reduce 类累加或 matmul K 维度是否适用 multi-buffer 不纳入本计划，后续单独讨论。

## 用户确认与协同约束

- 用户确认来源：2026-06-04 用户确认“出一个计划书”，并确认 `DmaRingType` 只保留 slot memory type、动态 `num/offset/shape_bytes` 作为 `make_ring` operands 的公开 API 变更方向；随后确认目的为 `multi buffer pass`。
- 用户已确认事项：
  - `DmaRingType` 不再承载 offset。
  - `num/offset/shape_bytes` 作为 `dma.make_ring` operands。
  - 计划目标服务 `MultiBufferPass`；reduce/K 维累加先不纳入本轮。
  - 新增 `expectation/pass/multi_buffer/**` pass 级合同资产。
  - `expectation.pass.multi_buffer.matmul_ring_memory_stage` 与 `expectation.pass.multi_buffer.matmul_ring_target` 的测试输入 lhs/rhs staging `dma.alloc/free` 必须在 `symbol.for` 外，loop body 内只保留 `dma.copy` 与 `kernel.matmul` 消费。
  - 四个 DMA ring leaf expectation 内容可以。
  - 新增 pass expectation 的 loop 外 alloc / loop 内 copy+matmul / loop 外 ring 结构符合一般结构。
  - 当前仅按 ring 在 loop 外的支持范围收口，不扩到当前不支持的其它 ring 位置。
  - `num` 必须由 pass 参数 / 分析结果计算。
  - `shape_bytes` 根据每个 ring slot 的 target memory 大小计算，不根据最终 matmul output memory 计算。
  - 固定 ring num 沿用 `memory-stage`；`target=<target-name>` 中 `target-name` 是 target registry 目标名（如仓库当前 `npu_demo`、`cpu`），且 `target` 优先于 `memory-stage`。
  - `memory-stage` 固定 num 与 `target` 优先计算必须拆成独立 expectation 文件。
  - 动态 shape 参数一般由 kernel 参数传入；本轮 target leaf 可增加 `alloc(S1, S2)` 形态的动态例子，并按这些参数计算动态 `shape_bytes/num/offset/backing_bytes`。
  - `offset` 不需要 `+1`；本轮 `MultiBufferPass` ring 化输出必须使用 `offset = shape_bytes` 与 `backing_bytes = num * shape_bytes`，避免 slot 间 1 字节空隙和地址对齐风险；`expectation.dialect.dma.operation.make_ring` 必须把 `offset == shape_bytes` 作为合法边界。
- 待用户确认项：当前无剩余设计待确认项，也无剩余下发同意待确认项；用户已明确同意恢复 / 继续唯一计划级 `execute`，管理员已恢复既有 `T-20260605-0b33f547`。2026-06-06 target dynamic CHECK 架构补丁、`make_ring` 合法边界补丁与 `case_runner` KCE verifier failure 适配补丁均已完成 strict review 与守护最终检验；当前允许通知执行人继续。
- 迭代审阅记录：Draft 1 两路 subagent strict review 均不通过；Draft 3 已采用 A 路径并收口错误文本范围，Goodall / Parfit strict review 返工复核均通过；Draft 4 新增 pass 级 expectation 后，Noether / Hopper 均提出最小需改项，主线返工后 Noether-R2 / Hopper-R2 均通过。2026-06-05 用户指出 expectation 内容确认、争议裁决和下发同意未收口后，以上结论均仅作为历史审阅输入；用户已裁决 expectation 内容与主要冲突口径，本轮 target 优先、expectation 拆分与动态 shape case 属于 Draft 4 守护复验后的新修订，曾由 `McClintock` / `Epicurus` 两路 strict review 重新审阅并通过；no-`+1` 对齐修订发生在该轮审阅之后，已由 `Feynman` / `Gibbs` 两路 strict review 重新审阅并通过；2026-06-06 target dynamic CHECK 架构补丁已由 `Hubble` / `Socrates` 两路审阅并通过；`make_ring` 合法边界补丁已由 `Feynman` / `Gibbs` 两路审阅并通过；当前 `case_runner` KCE verifier failure 适配补丁已由 `Feynman` / `Gibbs` round11-R2 审阅并通过。
- 守护最终检验：Draft 3 历史守护由 `守护最好的爱莉希雅` 本人执行并通过，正式回执见 `agents/codex-multi-agents/log/talk.log:10964`，补催回执见 `agents/codex-multi-agents/log/talk.log:10965`；Draft 4 守护最终检验初验由 `守护最好的爱莉希雅` 本人执行且结论不通过，回执见 `agents/codex-multi-agents/log/talk.log:10989`，最小需改项为计划级任务下发前置当前态冲突；主线修订后 Draft 4 守护最终检验复验由 `守护最好的爱莉希雅` 本人执行并通过，回执见 `agents/codex-multi-agents/log/talk.log:10996`。2026-06-05 用户指出流程未收口后，守护复验通过不再作为当前下发依据；本轮 target 优先、expectation 拆分与 dynamic shape case 完成并通过两路 strict review 后，no-`+1` 修订前当前文本守护最终检验曾由 `守护最好的爱莉希雅` 本人重新执行并通过；当前 no-`+1` 对齐修订发生在该守护之后，已重新完成两路 strict review，并由 `守护最好的爱莉希雅` 本人完成 no-`+1` 修订后守护最终检验，守护回执为“DMA ring no-+1 修订后守护最终检验回执”，结论通过、无阻断、无最小需改、无设计待确认。2026-06-06 target dynamic CHECK 架构补丁、`make_ring` 合法边界补丁与 `case_runner` KCE verifier failure 适配补丁均已由 `守护最好的爱莉希雅` 本人完成守护最终检验；`case_runner` 回执见 `agents/codex-multi-agents/log/talk.log:11162`。
- 暂停 / 恢复回执：大闸蟹于 `agents/codex-multi-agents/log/talk.log:11020` 通知管理员暂停，于 `agents/codex-multi-agents/log/talk.log:11021` 通知执行人暂停；管理员于 `agents/codex-multi-agents/log/talk.log:11023` 确认已暂停 `T-20260605-0b33f547`，执行人停止实现 / 审查 / 归档；用户明确同意推进后，管理员已恢复既有 `T-20260605-0b33f547` 为进行中。当前 `case_runner` KCE verifier failure 适配补丁已完成守护最终检验，允许通知执行人继续。
- 关联任务状态：用户已明确裁定 `prompt-plan-archive-flow` 与 DMA ring 无关；管理员已删除错误耦合的暂停任务 `T-20260605-360c7137`，另行创建 prompt-only execute `T-20260605-899ccd84`。该任务不再作为本 DMA ring 计划下发前置或等待项。
