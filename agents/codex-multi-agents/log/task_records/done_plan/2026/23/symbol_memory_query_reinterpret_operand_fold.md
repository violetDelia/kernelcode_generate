# symbol_memory_query_reinterpret_operand_fold

## 文档信息

- 计划用途：为 `symbol.get_dim` / `symbol.get_stride` 增加直接读取 `dma.reinterpret` result shape / stride operands 的 folding 规则，使 memory-pool 后已有的 reinterpret alias 不再继续保留冗余 symbol query。
- 用户确认来源：2026-06-07 用户确认“`symbol.get_dim/get_stride` 这个可以添加”；同一消息确认“不需要” memory-pool 后加 CSE、同步 pipeline spec/test、源码发射层 `+ 0` 清理，并要求“做一个计划书”“按照计划书的流程”；随后补充“动态应该也可以”，确认 direct `dma.reinterpret` 的动态 shape / stride SSA operands 也应 fold 到原 operand，而不是只处理静态常量。
- 目标 `spec`：
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- 目标 `API`：
  - 不新增、删除、重命名或修改公开 API 签名。
  - 既有公开 API 保持：
    - `class SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`
    - `class SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`
    - `class DmaReinterpretOp(source: SSAValue | Operation, offset: SSAValue | Operation, shape: Sequence[SSAValue], stride: Sequence[SSAValue], result_type: NnMemoryType)`
- 目标 `test`：
  - [`test/dialect/symbol/test_symbol.py`](../../test/dialect/symbol/test_symbol.py)
  - 如 execute 实际改动触达 DMA reinterpret public surface，补跑 [`test/dialect/dma/test_reinterpret.py`](../../test/dialect/dma/test_reinterpret.py)
- 目标 `验收资产`：
  - pytest 为主。
  - 当前不新增、不修改、不要求运行 `expectation/`；`expectation/dialect/symbol/operation/get_dim.py`、`expectation/dialect/symbol/operation/get_stride.py`、`expectation/dialect/symbol/operation/fold/` 仅作为历史 / 本地只读合同来源说明，不作为本计划当前必过门禁。
- 目标 `功能实现`：
  - [`kernel_gen/dialect/symbol/operation/memory_query.py`](../../kernel_gen/dialect/symbol/operation/memory_query.py)
  - 只在需要公开导入依赖时读取 [`kernel_gen/dialect/dma/operation/alias.py`](../../kernel_gen/dialect/dma/operation/alias.py)

## 计划级任务

- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`。
- 计划级任务目标：为 `SymbolGetDimOp` / `SymbolGetStrideOp` 添加 `dma.reinterpret` operand folding 规则，同步 symbol dialect spec 与 pytest，验收 canonical folding 可把 query 替换为对应 shape / stride SSA operand。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `symbol-memory-query-reinterpret-operand-fold` | `execute` | 待管理员创建 | `agents/codex-multi-agents/log/task_records/2026/24/20260607-symbol-memory-query-reinterpret-operand-fold.md` |

## 迭代审阅记录

### 收敛轮次 1：subagent strict review

- 审阅对象：
  - `Franklin / 019e9e2d-521b-7e42-9793-4ddec55fe40b`
  - `Nietzsche / 019e9e2d-5252-75b0-b014-9a712a24d93f`
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/任务记录约定.md`、本计划全文、用户确认项、禁止修改面、必过验收命令、`spec/dialect/symbol.md`、`kernel_gen/dialect/symbol/operation/memory_query.py`、`kernel_gen/dialect/dma/operation/alias.py`、`test/dialect/symbol/test_symbol.py` 和严格通过口径。
- 严格通过口径：不新增公开 API；不修改 `expectation/`；不把 memory-pool 后 CSE、pipeline spec/test 或源码发射 `+ 0` 清理纳入本计划；动态 operand 口径清楚；任务目标可直接 execute；小任务卡、验收、禁止修改面和合同真源闭合；仍有可执行最小改进项则不通过。
- 发现问题：
  - `Franklin`：不通过。S1/S2/S3 禁止修改面缺少 `ARCHITECTURE/plan/**` / 本计划书；direct `dma.reinterpret` 的静态 operand fold 优先级存在歧义；验收 `rg` 命令扫描范围过宽且无法形成清晰门禁；S3 未明确要求通过 `Folder.try_fold` 证明 canonical folder 接受 SSAValue fold 且不新建 op。
  - `Nietzsche`：不通过。计划未明确 `memory_query.py` 不能顶层导入 DMA，若顶层导入 `DmaReinterpretOp` 会因 `dma.operation.alias` 反向导入 `kernel_gen.dialect.symbol` 导致循环导入风险；类型不匹配拒绝测试未说明要用未调用 `DmaReinterpretOp.verify()` 的畸形 IR，否则 DMA verifier 会先强制 shape / stride operand 与 result type 匹配。
- 主线处理：
  - 采纳 `Franklin`：S1/S2/S3 禁止修改面补 `ARCHITECTURE/plan/**` / 本计划书；明确 direct `DmaReinterpretOp` 命中时优先返回 selected shape / stride SSAValue，包括静态、具名动态和 `?`，非 direct reinterpret fallback 才保留静态 `IntAttr` fold；删除过宽 `rg` 门禁，改为 `git diff --name-only` 目标文件清单核对；S3 增加 `Folder(_build_context()).try_fold(...)` 正例，要求 `values == [selected_operand]` 且 `new_ops == []`。
  - 采纳 `Nietzsche`：S2 明确禁止顶层导入 DMA 或 alias 子模块，要求在 `fold()` 或当前文件内顶层 helper 内使用公开 root API 的局部 import `from kernel_gen.dialect.dma import DmaReinterpretOp`；S3 明确类型不匹配拒绝例使用公开构造但不调用 `reinterpret.verify()` 的畸形 IR，只测 memory query fold 保守返回 `None`，不得修改 DMA verifier。
- 状态：需修订；修订后发起第二轮 strict review。

### 收敛轮次 2：subagent strict review

- 审阅对象：
  - `Franklin / 019e9e2d-521b-7e42-9793-4ddec55fe40b`
  - `Nietzsche / 019e9e2d-5252-75b0-b014-9a712a24d93f`
- 输入标准包：基于第 1 轮修订后的最新计划全文、上一轮问题和本轮收口摘要、根 `AGENTS.md`、当前角色 prompt、相关 `agents/standard/**`、用户确认项、待确认项、禁止修改面、必过验收命令和严格通过口径。
- 严格通过口径：确认第 1 轮全部最小需改项已闭合；无新增阻断、无最小需改项、无待确认项。
- 发现问题：
  - `Franklin`：通过。确认 S1/S2/S3 禁止修改面已补 `ARCHITECTURE/plan/**` / 本计划书；direct `DmaReinterpretOp` 静态 operand 优先 SSAValue 口径已闭合；过宽 `rg` 验收已改为 `git diff --name-only HEAD` 目标文件清单白名单；S3 已补 `Folder(_build_context()).try_fold(...)` 正例断言 `values == [selected_operand]` 且 `new_ops == []`。无新增最小需改项。
  - `Nietzsche`：通过。确认禁止 `memory_query.py` 顶层导入 DMA、只能在函数体内局部导入公开 root API 的约束已闭合；类型不匹配拒绝例使用未调用 `DmaReinterpretOp.verify()` 的畸形 IR 已写清；动态 operand、静态 operand 优先级、`Folder.try_fold`、`expectation` / pipeline / emit 禁止面均无新增问题。无最小需改项。
- 主线处理：无需继续修订；两路复审均通过且无待用户确认项。
- 状态：已收口。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：
  - `Franklin / 019e9e2d-521b-7e42-9793-4ddec55fe40b`：第 1 轮不通过，第 2 轮通过。
  - `Nietzsche / 019e9e2d-5252-75b0-b014-9a712a24d93f`：第 1 轮不通过，第 2 轮通过。
- 收敛结论：两路 subagent strict review 已基于最新修订文本收敛到无阻断、无最小需改项、无待确认项；可进入守护最终检验。
- 遗留项：无。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅`
- 检验范围：本计划全文、subagent 收敛结论、公开 API / expectation 权限 / 禁止修改面 / 验收命令 / 小任务卡。
- 必过门禁：subagent 收敛结论已证明无阻断、无最小需改项、无待确认项；用户待决策项已确认；无越权边界。
- 初检回执：`agents/codex-multi-agents/log/talk.log:11285`；结论不通过，唯一阻断为正式计划未进入 tracked / index diff，内容核对暂未发现额外阻断。
- 主线处理：执行 `git add -f ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md`，并记录 `git ls-files --stage`、`git diff --name-status --cached` 与 `git status --short --ignored --untracked-files=all` 证据，确认该计划不再只显示 ignored `!!`。
- 复验回执：`agents/codex-multi-agents/log/talk.log:11305`；结论通过，阻断项无，最小需改项无，待确认项无。
- 关键证据：正式计划已进入 index，`git ls-files --stage -- ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md` 输出 `100644 093fb6bbb429abe25ccb5201da23e521ef2f60be 0 ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md`；`git diff --name-status --cached -- ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md` 输出 `A ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md`；`git diff --cached --check -- ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md` 通过；守护复核公开 API、expectation 只读、动态 operand fold、循环导入约束、畸形 IR 测试口径、pipeline / CSE / emit 非目标、S1-S3 小任务卡和待确认项均已闭合。
- 结论：通过；允许管理员后续创建唯一计划级 `execute`，守护未直接下发、未创建任务、未通知管理员。
- 最小阻断项：无。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：不要啊教练。
- 结论：通过；允许进入计划级链路下一阶段 `merge`，不得跳过合并阶段直接归档或移动 `done_plan`。
- 验证基线：`HEAD=origin/main=merge-base=aec10c294cff71f1a2b4f05841f25db02808ff2b`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260607-symbol-memory-query-reinterpret-operand-fold`。
- 同步结果：2026-06-07 12:15 +0800 执行 `git fetch --prune origin` 成功；当前任务状态为 `archive_acceptance / 不要啊教练 / 进行中`，无过期基线、冲突或覆盖风险。
- 合同验收摘要：当前计划正文无必过 `expectation`；`expectation/dialect/symbol/operation/get_dim.py`、`expectation/dialect/symbol/operation/get_stride.py` 与 `expectation/dialect/symbol/operation/fold/` 仅为历史 / 本地只读合同来源说明，本阶段不运行、不作为阻断。
- pytest / 门禁摘要：`pytest -q test/dialect/symbol/test_symbol.py -k "get_dim or get_stride or memory_query"` 14 passed；`pytest -q test/dialect/symbol/test_symbol.py` 117 passed；`pytest -q test/dialect/dma/test_reinterpret.py` 3 passed；`pytest -q test/repo_conformance/test_private_api_boundaries.py -x` 4 passed；`git diff HEAD --check`、`git diff --cached --check` 均通过。
- 敏感目录与可归档性：`git diff --name-only HEAD -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md` 无输出；功能 diff 仅为 `kernel_gen/dialect/symbol/operation/memory_query.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py`；计划正文已完成本入档验收记录回写，无阻断项、无最小需改项。

## 计划目标

- 增加 `symbol.get_dim(dma.reinterpret(...), axis=i)` 到 `dma.reinterpret.shape[i]` 的 folding。
- 增加 `symbol.get_stride(dma.reinterpret(...), axis=i)` 到 `dma.reinterpret.stride[i]` 的 folding。
- 保持非 direct reinterpret source 上现有静态整数 shape / stride 条目折为 `IntAttr` 的行为不变；direct `DmaReinterpretOp` 命中时优先复用 selected shape / stride SSAValue，即使该 operand 的 type 是静态整数表达。
- direct `dma.reinterpret` source 下，具名动态符号与匿名动态 `?` 的 shape / stride operands 也 fold 到原 SSAValue；动态非 reinterpret source、非法 axis、result type 不匹配等场景保守不折叠。
- 不调整 npu-demo-lowering pass 顺序，不在 memory-pool 后新增 CSE，不做源码发射层 `+ 0` 清理，不做 `dma.reinterpret` chain composition。

## 当前基线

- 当前公开合同：
  - `spec/dialect/symbol.md` 定义 `SymbolGetDimOp(memory, index)` 与 `SymbolGetStrideOp(memory, index)`。
  - 现有 spec 写明 query 到静态整数条目时支持常量折叠；符号表达、匿名动态值不得折叠为常量，但尚未定义 direct `dma.reinterpret` operand 的 SSAValue fold。
  - `spec/dialect/dma.md` 定义 `dma.reinterpret` 的 result shape / stride operands 必须与 result memory type exact match。
- 当前公开 API：
  - `SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`
  - `SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`
  - `DmaReinterpretOp(source, offset, shape, stride, result_type)`
- 当前实现入口：
  - `kernel_gen/dialect/symbol/operation/memory_query.py` 中 `_BaseSymbolMemoryQueryOp.fold()` 当前只返回静态整数 `IntAttr`。
  - `kernel_gen/dialect/dma/operation/alias.py` 中 `DmaReinterpretOp` 公开暴露 `shape` 与 `stride` var operands，并由 verifier 保证它们匹配 result type。
- 当前测试与验收资产：
  - `test/dialect/symbol/test_symbol.py` 已覆盖静态 dim / stride fold、动态 symbol 不 fold、无效 axis / 非 memory / `?` 拒绝。
  - `test/dialect/dma/test_reinterpret.py` 已覆盖 `dma.reinterpret` 公开 verifier 边界。
  - `expectation/dialect/symbol/operation/get_dim.py`、`get_stride.py`、`fold/` 当前只读，不作为本计划必改资产。
- 当前 dump 事实：
  - `/home/lfr/kernelcode_generate/kernel/dump/matmul/**/25-memory-pool.mlir` 后出现 `dma.reinterpret` result 被 `symbol.get_dim/get_stride` 读取的形态。
  - `/home/lfr/kernelcode_generate/kernel/dump/matmul/**/26-canonicalize.mlir` 目前未消掉这类 query，因为 query fold 不会返回 reinterpret 的 shape / stride SSA operand。
- 当前缺口：
  - 对 `dma.reinterpret` result 的动态 shape / stride 查询已经有更精确的 SSA 真源，但 canonicalize 无法复用，导致后续 IR 保留冗余 query 和由 query 派生的 symbol 算术。

## 方案比较与选型

- 不采用方案：在 memory-pool 后新增 CSE，并同步 pipeline spec / test。
- 原因：用户明确确认“不需要”；CSE 也不能从 `symbol.get_dim(dma.reinterpret)` 推导到 shape operand，只能合并等价现有 op。
- 不采用方案：在源码发射层清理 `+ 0`。
- 原因：用户明确确认“不需要”；该问题属于 emit 文本化质量，不是本计划的 IR folding 根因。
- 不采用方案：本计划同时做 `dma.reinterpret` chain composition。
- 原因：chain composition 涉及 offset 单位换算、typed source 与 byte pool 边界、bounds verifier 和 CSE 交互，风险与验收面更大；用户当前只确认 `symbol.get_dim/get_stride` 可添加。
- 采用方案：在 `symbol.get_dim/get_stride` 的公开 folding 入口中识别 direct defining op 为 `DmaReinterpretOp`，当 axis 合法且 result type 与被选 operand type exact match 时，返回对应 `shape[axis]` 或 `stride[axis]` SSAValue；该规则优先于静态 `IntAttr` fold，覆盖静态、具名动态符号和匿名动态 `?` operand，不要求 operand 可求为常量。
- 最小公开接口：保持既有 class 构造签名不变，仅新增公开 folding 行为。

## 公开 API 设计

- 用户确认来源：2026-06-07 用户确认“`symbol.get_dim/get_stride` 这个可以添加”。
- 功能简介：在不修改公开 API 签名的前提下，扩展 `SymbolGetDimOp` / `SymbolGetStrideOp` 的 folding 行为，使其可从 `dma.reinterpret` 的公开 operands 中读取动态 shape / stride 真源。
- API 列表：
  - `class SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`
  - `class SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`
- 公开行为：
  - `symbol.get_dim(%reinterpret_result) {axis = i}` 若 `%reinterpret_result` 由 direct `DmaReinterpretOp` 定义，且 `i` 在 `shape` operand 范围内，且 `query.result.type == reinterpret.shape[i].type`，fold 返回 `reinterpret.shape[i]`。
  - `symbol.get_stride(%reinterpret_result) {axis = i}` 若 `%reinterpret_result` 由 direct `DmaReinterpretOp` 定义，且 `i` 在 `stride` operand 范围内，且 `query.result.type == reinterpret.stride[i].type`，fold 返回 `reinterpret.stride[i]`。
  - 上述 SSAValue fold 覆盖静态与动态 operand，包括 `!symbol.int<#symbol.expr<2>>`、`!symbol.int<#symbol.expr<N>>`、`!symbol.int<#symbol.expr<M + 1>>` 和 `!symbol.int<#symbol.expr<?>>`；这些值不是折成 `IntAttr`，而是复用已有 SSAValue。
  - 非 direct reinterpret source 的静态整数 memory type 条目仍可 fold 为 `IntAttr`，由既有 materialization 生成 `symbol.const`。
  - 无 direct defining `DmaReinterpretOp`、axis 非静态整数、axis 越界、operand type 不匹配、source 非 `nn.memory` 或 result type 不匹配时保守返回 `None`；非 reinterpret source 上的动态 symbol / `?` 仍不凭 memory type 折成 SSAValue。
- 稳定错误语义：不新增 verifier 错误，不修改现有错误文本；本规则只影响合法 IR 的 fold 结果。

## 完成态定义

- `spec/dialect/symbol.md` 明确 `symbol.get_dim/get_stride` 对 direct `dma.reinterpret` result 的 shape / stride operand folding 规则与拒绝边界。
- `kernel_gen/dialect/symbol/operation/memory_query.py` 的文件级说明、相关函数注释和 fold 行为与 spec 一致。
- `test/dialect/symbol/test_symbol.py` 覆盖：
  - `get_dim` 从 `DmaReinterpretOp.shape[axis]` fold 到已有 SSAValue，包含静态、具名动态符号和匿名动态 `?` operand。
  - `get_stride` 从 `DmaReinterpretOp.stride[axis]` fold 到已有 SSAValue，包含静态、具名动态符号和匿名动态 `?` operand。
  - result type 与被选 operand type 不匹配时不 fold。
  - 现有静态 `IntAttr` folding 和 public rejection matrix 不退化。
- 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`ARCHITECTURE/plan/**` 无改动。
- 不出现 pipeline 顺序、dump marker 或源码 emit 相关改动。

## 验收设计

- pytest / 脚本：
  - `pytest -q test/dialect/symbol/test_symbol.py -k "get_dim or get_stride or memory_query"`
  - `pytest -q test/dialect/symbol/test_symbol.py`
  - 若 execute 实际触达 DMA reinterpret 文件或公开导入边界，补跑：`pytest -q test/dialect/dma/test_reinterpret.py`
- 当前必过 expectation 合同验收：不适用；用户已确认本计划不需要同步 expectation，且计划不修改 `expectation/`。
- 历史 / 本地只读 expectation 来源说明：
  - `expectation/dialect/symbol/operation/get_dim.py`
  - `expectation/dialect/symbol/operation/get_stride.py`
  - `expectation/dialect/symbol/operation/fold/`
  - 这些路径只读参考，不计入当前必跑门禁。
- 文本核对：
  - `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md ARCHITECTURE/plan`
  - `git diff --name-only HEAD -- kernel_gen spec test expectation .skills agents/standard AGENTS.md ARCHITECTURE/plan | sort`
  - 上述 diff 文件清单预期只包含 `kernel_gen/dialect/symbol/operation/memory_query.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py`，以及按实际 DMA 触达可选的 `test/dialect/dma/test_reinterpret.py`；不得出现 `kernel_gen/pipeline/**`、`spec/pass/**`、`test/passes/**`、`expectation/**`、`.skills/**`、`agents/standard/**`、`AGENTS.md` 或 `ARCHITECTURE/plan/**`。
- 锁定结果：
  - `Folder.try_fold` 对 direct reinterpret query 返回已有 `shape` / `stride` SSAValue，不生成新 op；静态 operand、动态 symbol 和 `?` operand 都按 SSAValue 复用。
  - 非 direct reinterpret source 和类型不匹配场景保持不 fold。
- Diff 反推要求：执行与审查按实际 diff 补测试；`expectation` 单列为合同验收且本计划当前不跑。

## 计划内小任务

### S1. 同步 symbol dialect spec 的 memory query folding 合同

- 为什么做：当前 spec 只写静态整数条目 fold，没有定义 query 从 `dma.reinterpret` operands 复用动态 shape / stride SSA 的公开行为。
- 做什么：更新 `spec/dialect/symbol.md`，补充 direct `dma.reinterpret` result 的 `shape[i]` / `stride[i]` operand folding 规则、动态 operand 复用语义、类型匹配条件和拒绝边界。
- 不做什么：不修改 `spec/pass/pipeline/npu_demo_lowering.md`，不新增 memory-pool 后 CSE，不定义 `dma.reinterpret` chain composition。
- 怎么验收：文本核对 spec 只新增 symbol memory query folding 规则；`git diff -- spec/dialect/symbol.md` 不含 pipeline、emit 或 expectation 口径。
- 卡住问谁：公开 API 行为边界或需求取舍问用户；spec 与实现冲突问架构师；流程状态问管理员。
- 上下文摘要：memory-pool 后 query 的真源已存在于 `DmaReinterpretOp.shape/stride` operands，spec 需要给 execute 一个明确合同。
- 小任务目标：把 `symbol.get_dim/get_stride` direct reinterpret operand folding 写入 symbol dialect spec，并通过文本核对确认未扩大范围。
- 非目标：不写 pipeline 顺序，不写 CSE 插入，不写源码 emit `+ 0` 清理，不写 reinterpret chain 合成。
- 模块范围：`spec/dialect/symbol.md`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`ARCHITECTURE/plan/**` / 本计划书、pipeline spec、emit spec、immutable 文件。
- 合同真源：用户确认 > 本计划 > `spec/dialect/symbol.md` > pytest > 当前实现；历史 expectation 只读参考。
- 最小功能闭环：spec 对合法 direct reinterpret query 与拒绝边界给出可测试规则。
- 执行步骤：
  1. 在 `symbol.get_dim/get_stride` 相关注意事项处补充 direct `DmaReinterpretOp` fold 规则。
  2. 写清必须检查静态 axis、operand 范围和 result type exact match。
  3. 写清动态具名符号与 `?` operand 可以复用原 SSAValue，但非 direct reinterpret、类型不匹配、非法 axis 继续保守不 fold。
- 验收必过项目：`git diff -- spec/dialect/symbol.md` 文本核对；pytest 由 S3 覆盖。
- 记录要求：任务记录写清 spec 新增行为、非目标和未修改 expectation 的证据。

### S2. 实现 memory query 对 DmaReinterpretOp operands 的 fold

- 为什么做：当前 `_BaseSymbolMemoryQueryOp.fold()` 只把静态整数 memory type 条目返回为 `IntAttr`，无法对动态 reinterpret shape / stride operand 进行 SSAValue folding。
- 做什么：在 `kernel_gen/dialect/symbol/operation/memory_query.py` 中实现 direct defining op 识别，`SymbolGetDimOp` 返回 `DmaReinterpretOp.shape[axis]`，`SymbolGetStrideOp` 返回 `DmaReinterpretOp.stride[axis]`，并保留现有静态常量 fold。
- 不做什么：不新增 pass，不修改 `DmaReinterpretOp` verifier，不跨文件调用非公开 helper，不使用运行时能力探测，不写嵌套函数。
- 怎么验收：pytest 覆盖静态、具名动态符号和 `?` operand 均 fold 返回已有 SSAValue；`rg` 核对未出现 `hasattr/getattr/callable(getattr(...))` 兼容探测；文本核对无顶层 DMA import；文件级说明和函数注释与实现同步。
- 卡住问谁：若 xDSL folding API 对返回 SSAValue 存在限制，问架构师裁定用 folder pattern 还是 fold；若需要新增公开 API，先问用户。
- 上下文摘要：`HasFolderInterface.fold()` 当前签名允许 `Sequence[SSAValue | Attribute] | None`，项目内已有 `symbol.min` fold 到已有 SSAValue 的测试。
- 小任务目标：让合法 direct reinterpret query fold 为已有 SSAValue，包括动态具名符号和 `?` operand，并保持原有 `IntAttr` fold 与拒绝矩阵不退化。
- 非目标：不实现 chain composition，不做 dominance 跨区域重写专项，不改 DMA dialect API，不顶层导入 DMA dialect。
- 模块范围：`kernel_gen/dialect/symbol/operation/memory_query.py` 及必要公开 import。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`ARCHITECTURE/plan/**` / 本计划书、`kernel_gen/pipeline/**`、源码 emit 层、immutable 文件。
- 合同真源：用户确认 > 本计划 > `spec/dialect/symbol.md` > pytest > 当前实现。
- 最小功能闭环：合法 query 的 `fold()` 返回 `(selected_operand,)`，不要求 selected operand 可求常量；不合法时返回 `None`。
- 执行步骤：
  1. 禁止在 `memory_query.py` 顶层导入 DMA；若需要 `DmaReinterpretOp` 类型，只能在 `fold()` 或当前文件内顶层 helper 的函数体内使用公开 root API 局部导入 `from kernel_gen.dialect.dma import DmaReinterpretOp`，不得导入 `kernel_gen.dialect.dma.operation.alias`。
  2. 通过公开 `DmaReinterpretOp` 类型识别 query source 的 owner op。
  3. direct `DmaReinterpretOp` 命中时优先处理，在 axis 合法、selected operand 存在且 `self.result.type == selected_operand.type` 时返回 selected operand；该路径优先于静态 `IntAttr` fold。
  4. 非 direct reinterpret source 保留现有静态 integer `IntAttr` folding 路径，避免改变普通 memory query 常量物化行为。
  5. 更新文件级说明或相关函数注释，说明新增 fold 行为。
- 验收必过项目：S3 pytest；`rg -n "hasattr\\(|getattr\\(|callable\\(" kernel_gen/dialect/symbol/operation/memory_query.py` 无能力探测新增；`rg -n "^from kernel_gen\\.dialect\\.dma|^import kernel_gen\\.dialect\\.dma|kernel_gen\\.dialect\\.dma\\.operation\\.alias" kernel_gen/dialect/symbol/operation/memory_query.py` 无输出；`git diff --check` 通过。
- 记录要求：任务记录写清是否新增 import、是否新增 helper、旧逻辑保留原因和 Diff 反推自测。

### S3. 补充 focused pytest 与敏感目录门禁

- 为什么做：新行为必须通过公开 pytest 锁定，不能用 dump 现象或 expectation 替代 diff 反推测试。
- 做什么：在 `test/dialect/symbol/test_symbol.py` 增加 direct `DmaReinterpretOp` source 的 `get_dim/get_stride` fold 正例，覆盖静态、具名动态符号和匿名动态 `?` operands，并增加类型不匹配拒绝例，补跑相关 pytest。
- 不做什么：不新增 expectation，不改 pipeline test，不重生成 matmul dump 作为当前门禁。
- 怎么验收：运行 symbol pytest targeted 与全量文件；若 touching DMA 文件则补跑 reinterpret pytest；敏感目录 `git status` 无输出。
- 卡住问谁：测试需要新增 fixture 但触及非公开 helper 时问架构师；需要 expectation 授权时问用户。
- 上下文摘要：现有 `test_symbol.py` 已有 `_make_memory_type/_make_memory_value` 和 Folder 断言风格，可直接扩展。
- 小任务目标：用公开构造和 Folder / fold 断言锁住新增行为和拒绝边界。
- 非目标：不覆盖 pipeline order，不断言全量 dump 变化，不修改 contract assets。
- 模块范围：`test/dialect/symbol/test_symbol.py`；按实际 diff 可补 `test/dialect/dma/test_reinterpret.py`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`ARCHITECTURE/plan/**` / 本计划书、pipeline tests、dump 资产、immutable 文件。
- 合同真源：pytest 为 diff 反推测试真源；历史 expectation 只读参考，不作为本轮门禁。
- 最小功能闭环：测试能证明 folding 选中了 reinterpret 的原始 shape / stride SSAValue，动态具名符号和 `?` 均可复用，且类型不匹配不 fold。
- 执行步骤：
  1. 构造 `DmaReinterpretOp` 输入 memory、offset、shape operands、stride operands 和 result memory type。
  2. 对 `SymbolGetDimOp(reinterpret.result, axis)` 与 `SymbolGetStrideOp(reinterpret.result, axis)` 断言 fold 返回对应 operand，至少覆盖静态 operand、具名动态符号和 `?` operand。
  3. 增加至少一个 `Folder(_build_context()).try_fold(query)` 正例，断言 `values == [selected_operand]` 且 `new_ops == []`，证明公开 Folder / canonical folding 接受 SSAValue fold。
  4. 类型不匹配拒绝例使用公开构造但不调用 `DmaReinterpretOp.verify()` 的畸形 IR：让 result memory type 条目与 selected shape / stride operand type 不一致，再直接测试 `SymbolGetDimOp(...).fold()` / `SymbolGetStrideOp(...).fold()` 返回 `None`；不得修改或绕过 DMA verifier 合同。
  5. 跑 targeted pytest、全量 `test_symbol.py`，按实际 diff 补跑 DMA reinterpret pytest。
  6. 执行敏感目录门禁、diff 文件清单核对和 `git diff --check`。
- 验收必过项目：
  - `pytest -q test/dialect/symbol/test_symbol.py -k "get_dim or get_stride or memory_query"`
  - `pytest -q test/dialect/symbol/test_symbol.py`
  - 按实际 diff 补跑 `pytest -q test/dialect/dma/test_reinterpret.py`
  - `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md ARCHITECTURE/plan`
  - `git diff --name-only HEAD -- kernel_gen spec test expectation .skills agents/standard AGENTS.md ARCHITECTURE/plan | sort`，预期仅出现本计划允许的目标文件清单。
- 记录要求：任务记录写清 Diff 反推自测、未运行项原因、sensitive status 输出和测试锁定行为。

## 计划自检与返工口径

- 自检：
  - 公开 API：不新增或修改签名；只新增用户确认过的 folding 行为。
  - 迭代审阅记录：strict review 与守护最终检验完成前不得下发 execute。
  - 小任务短口径：S1/S2/S3 均有为什么做、做什么、不做什么、怎么验收、卡住问谁。
  - 验收资产：pytest 与 history expectation 分开；当前无必过 expectation。
  - 禁止修改面：明确禁止 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`ARCHITECTURE/plan/**` / 本计划书、pipeline 与 emit 层。
  - 可读性和可维护性：优先在现有 `_BaseSymbolMemoryQueryOp.fold()` 内小范围扩展，避免新增 pass 或跨模块 private helper。
- 返工口径：只要 subagent、守护、review 或 archive_acceptance 发现仍有可提升质量、可读性、可维护性、测试有效性或验收可信度的可执行项，就回到计划修订或 execute 返工。

## 待确认项

- 无。用户已确认添加 `symbol.get_dim/get_stride` 优化，并明确排除 memory-pool 后 CSE、pipeline spec/test 同步和源码发射层 `+ 0` 清理。

## 用户确认与协同约束

- 用户确认来源：2026-06-07 当前会话。
- 用户已确认事项：
  - 可以添加 `symbol.get_dim/get_stride` 优化。
  - direct `dma.reinterpret` source 的动态 shape / stride operands 也应 fold 到原 SSAValue。
  - 不需要 memory-pool 后加 CSE。
  - 不需要同步 pipeline spec/test。
  - 不需要源码发射层 `+ 0` 清理。
  - 需要做计划书，并按计划书流程推进。
- 待用户确认项：无。
- 迭代审阅记录：见本文件“迭代审阅记录”，strict review 收敛后回写。
- 守护最终检验：已通过，回执见 `agents/codex-multi-agents/log/talk.log:11305`；允许管理员按唯一计划级 execute 下发。
