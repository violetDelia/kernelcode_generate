# symbol_hoist_pipeline_pass_green_plan

## 文档信息

- 目标 `spec`：
  - [`spec/pass/symbol_hoist_pipeline.md`](../../spec/pass/symbol_hoist_pipeline.md)
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
  - 如执行选择移动旧 pass 文件，还需同步 [`spec/pass/dma_alias_to_reinterpret.md`](../../spec/pass/dma_alias_to_reinterpret.md)、[`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)、[`spec/pass/hoist_dma_alias_ops.md`](../../spec/pass/hoist_dma_alias_ops.md)
- 目标 `API`：
  - 用户已确认：`class SymbolHoistPipelinePass(fold: bool = True)`
  - 用户已确认：`SymbolHoistPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`
  - 用户已确认：registry pass name `symbol-hoist-pipeline`
  - 用户已确认：不新增 pass 专属 option；只接受 registry 通用 `fold`。
  - 用户已确认：旧 pass 移到 `kernel_gen/passes/hoist/`。
  - 用户最新覆盖确认：`symbol_buffer_hoist` 也必须迁入 `kernel_gen/passes/hoist/`；旧 import 根模块不提供桥接。
- 目标 `test`：
  - [`test/passes/test_symbol_hoist_pipeline.py`](../../test/passes/test_symbol_hoist_pipeline.py)
  - [`test/passes/pipeline/test_npu_demo_lowering.py`](../../test/passes/pipeline/test_npu_demo_lowering.py)
  - 旧 pass 迁移相关既有测试：`test/passes/test_dma_alias_to_reinterpret.py`、`test/passes/test_symbol_loop_hoist.py`、`test/passes/test_hoist_dma_alias_ops.py`、`test/passes/test_registry.py`
- 目标 `验收资产`：
  - pytest / kernel demo 为主；用户已确认本计划不新增、不修改、不要求运行 `expectation`。
  - 若已有 `expectation` 与新 pass name 冲突，记录为非本轮门禁 / 后续专项，不由 execute 修改 expectation。
- 目标 `功能实现`：
  - [`kernel_gen/passes/hoist/`](../../kernel_gen/passes/hoist/)
  - [`kernel_gen/pipeline/npu_demo_lowering.py`](../../kernel_gen/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)

## 计划级任务

- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`。
- 当前状态：`用户决策已收口 / T-20260524-ebee86b8 已满足 / 可由管理员创建排队 execute / 执行开始前依赖 T-20260524-6dacd489 merge/DONE`
- 最新覆盖口径：`2026-05-25` 用户确认 `kernel_gen/passes/hoist/` 缺 `symbol_buffer_hoist`，本计划需把 `SymbolBufferHoistPass` 也迁入 `kernel_gen/passes/hoist/`；同时旧 import 根模块不提供桥接。本文历史讨论中的旧根模块桥接草案仅作背景，不再作为当前执行合同。
- 新版流程约束：
  - 计划草案阶段不进 `TODO`。
  - 计划负责人必须先完成 Codex 内置 `subagent` 讨论摘要；这里的 `subagent` 不是大闸蟹、提莫炖蘑菇、小李飞刀等角色。
  - 用户最新确认：除终审 / 计划书入档验收阶段外，计划草案阶段不需要再询问其它人；只问 Codex 内置 `subagent` 即可。
  - 涉及范围取舍、公开 API、`expectation` 授权、冲突或不确定项，必须整理选项 / 影响 / 推荐项交用户确认。
  - 用户确认可下发后，由管理员创建唯一计划级 `execute`。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `symbol-hoist-pipeline-pass` | `execute` | 待管理员创建 | `agents/codex-multi-agents/log/task_records/2026/24/20260524-symbol-hoist-pipeline-pass.md` |

### 依赖关系

| 依赖任务 | 依赖原因 | 依赖满足条件 | 依赖满足后的动作 |
| --- | --- | --- | --- |
| `T-20260524-ebee86b8 / npu-demo-post-symbol-buffer-cleanup-pipeline` | 该任务修改同一公开 `npu-demo-lowering` pipeline；本计划也会替换 hoist 相关 stage，若基于旧 main 下发会造成 pass 顺序、dump marker、pipeline pytest 与 expectation 非门禁口径冲突。 | 已满足：`T-20260524-ebee86b8` 已 `merge/DONE`，主仓 `HEAD=origin/main=7dbe05d3874a6f8f4705e948a318fda167898515` 包含其最终 pipeline/spec/test/任务记录，且 `TODO.md` 不再显示该任务进行中。 | 已完成 latest-main 重核；公开 API / expectation 口径无新增争议，可进入管理员创建排队 execute。 |
| `T-20260524-6dacd489 / producer-consumer-analysis-before-memory-pool` | 该小任务当前正在修改同一 `kernel_gen/pipeline/npu_demo_lowering.py`、pipeline spec/test 和 dump marker 断言；本计划会继续替换 hoist stage，若同时执行会冲突。 | `T-20260524-6dacd489` 已 `merge/DONE`，主仓 `origin/main` 包含其最终 pipeline/spec/test/任务记录，且 `TODO.md` 不再显示该任务进行中。 | 管理员可先创建 / 排队本计划唯一 `execute`，但执行人必须在该依赖满足后再开始实现，并基于 latest `origin/main` 重核 pass-name 顺序、dump marker 和验收命令。 |

## 评审摘要

- 评审结论：`可下发排队`
- 讨论来源：Codex 内置 `subagent`；`大闸蟹`回执作为非阻塞参考，不再作为下发前置。
- 结论摘要：用户希望把当前 `npu-demo-lowering` 中 alias 归一、symbol 外提和 dma alias 外提这组 hoist 能力收敛为一个 `symbol-hoist-pipeline` pass，并把相关 pass 移到 `kernel_gen/passes/hoist/`。
- 当前状态：`用户决策已收口 / T-20260524-ebee86b8 已满足 / 可创建排队 execute / 执行开始前依赖 T-20260524-6dacd489`

## 多人讨论记录

- 用户：`2026-05-24 会话`
  - 问题：是否增加 `symbol hoist pipeline pass`，并把 `07-dma-alias-to-reinterpret`、`08-symbol-loop-hoist`、`09-hoist-dma-alias-ops` 的能力整合。
  - 用户观点：
    - 该 pass 不是简单外层顺序调用，而是“运行这几个 pass 的所有 pattern”。
    - 同时将这几个 pass 移到 `passes/hoist/`。
    - 后续按新版计划书流程推进。
  - 证据：当前 `kernel_gen/pipeline/npu_demo_lowering.py` 与 `spec/pass/pipeline/npu_demo_lowering.md` 公开顺序仍直接列 `DmaAliasToReinterpretPass -> SymbolLoopHoistPass -> HoistDmaAliasOpsPass` 两段组合。
  - 当时分歧：
    - 用户提到“四个 pass”，当前点名 dump 中唯一业务 pass 为三个，`cse/canonicalize` 是否纳入新 pass 当时仍需确认；已在最终决策中收口为外置。
    - “前面 2 公开 pass”语义当时需按 subagent 讨论结论整理；已在最终决策中收口为新增 `SymbolHoistPipelinePass`。当时旧 pass 根模块桥接草案已被 `2026-05-25` 最新确认覆盖。
  - 采纳结论：本计划先按讨论稿推进，待用户决策后收口。
- 用户：`2026-05-24 最终决策`
  - C1：确认新增公开 pass `SymbolHoistPipelinePass(fold: bool = True)`。
  - C2：确认 registry pass name 为 `symbol-hoist-pipeline`。
  - C3：确认不新增 pass 专属 option，只使用 registry 通用 `fold`；未知非 `fold` option 按公开 registry 错误失败。
  - C4：确认 `cse` / `canonicalize` 外置，不纳入新 pass。
  - C5：确认不是按旧 pass family 分段执行；新 pass 内把相关 pattern 放到一起运行，因为这些 pattern 会相互影响，需要在一个 pass 中收敛。
  - C6：确认整合原因是 pattern 相互影响，不是为了简单减少 dump stage。
  - C7：当时确认旧 pass 移到 `kernel_gen/passes/hoist/`，旧 import 根模块第一版桥接草案不新增包根 re-export；该草案已被 `2026-05-25` 最新确认覆盖为旧四个根模块稳定失败。
  - C8：确认新 pass 使用这些旧 pass 的 pattern；执行语义为先把可归一的 alias 变成 `dma.reinterpret`，再运行 hoist 相关 pattern，仍属于一个 pass 内的 combined-pattern 收敛，不是依次调用旧 pass 的 `apply`。
  - C9：确认本计划不新增、不修改、不同步 `expectation`。
  - 采纳结论：公开 API 与 expectation 口径已闭合；当前唯一硬前置是等待同改 pipeline 的 `T-20260524-ebee86b8` 合入后重核 latest main。
- Codex 内置 subagent：`2026-05-24 只读讨论`
  - 结论：`不通过`
  - 问题：
    1. `SymbolHoistPipelinePass(fold=True)`、registry name `symbol-hoist-pipeline`、是否暴露 `from_options`、未知 option 错误文本、第二段是否也跑 alias-to-reinterpret family 都是公开 API / 公开行为变更，当前仍未取得用户最终确认。
    2. 旧 import 路径不能笼统写“保留 / 删除”；当前 `kernel_gen.passes.__init__` 只 re-export `SymbolLoopHoistPass`，而 `DmaAliasToReinterpretPass` / `HoistDmaAliasOpsPass` 主要是旧根模块公开，且 `expectation/pass/pipeline/npu_demo_lowering.py` 也直接 import 旧根模块。
    3. 单 walker 混跑所有 pattern 不稳；三个 pass 现有执行边界不同，包括 clone + verify + rollback、greedy 稳定态和带 module/state 的 pattern。
    4. `cse/canonicalize` 不应合入新 pass；当前 `CanonicalizePass` 只是 pipeline 内部阶段，不进入仓库 registry。
    5. `expectation/pass/pipeline/npu_demo_lowering.py` 锁旧 pass order 与旧 import，若本计划改公开 pipeline stage，会成为已知合同冲突。
  - 采纳结论：
    - 增加公开 API 确认矩阵，明确 class / registry / fold / 专属 option / 错误语义 / 第二段完整运行新 pass。
    - 当时记录第一版保留三个旧根模块桥接文件，`kernel_gen.passes` 包根只保留既有 re-export，不新增 `DmaAliasToReinterpretPass` / `HoistDmaAliasOpsPass` 包根导出；该历史建议已被 `2026-05-25` 最新确认覆盖。
    - subagent 推荐第一版采用一个公开 pass 内多阶段 walker；用户最终改为 combined-pattern 收敛：一个 pass 内共同运行相关 pattern，但必须先完成可归一 alias -> `dma.reinterpret` 的优先归一，再让 hoist 相关 pattern 收敛。
    - `cse/canonicalize` 外置。
    - 用户最终确认本计划不新增、不修改、不同步 `expectation`；既有 pipeline expectation 若仍锁旧顺序，记录为非本轮门禁 / 后续专项，不由 execute 修改。
  - 遗留项：已满足新版流程的 subagent 讨论要求；用户决策已收口。
- 大闸蟹回执：已发起且已收到；按用户最新流程调整为非阻塞参考，见下。
- 提莫炖蘑菇 / 小李飞刀：此前已发起催办；按用户最新流程不作为下发前置，已收到回执仅作为参考，见下。
- 大闸蟹：`2026-05-24 只读互评`
  - 结论：`最小需改项`
  - 问题：
    1. `SymbolHoistPipelinePass` exact API、registry name、旧路径桥接 / 删除、`4 个 pass` 是否包含 CSE / Canonicalize、第二段是否也运行 `dma-alias-to-reinterpret` 都仍是公开 API / pipeline 行为待确认项。
    2. 旧 import 路径需要区分旧模块 shim 与 `kernel_gen.passes` 包根 re-export；现有包根已有 `SymbolLoopHoistPass` re-export，不能混同处理。
    3. 单 walker 合并所有 pattern 与当前三 pass 语义不等价风险高，涉及 rewrite+verify+rollback、folding、module 状态与递归策略。
    4. 当前存在同改 `npu-demo-lowering` pipeline 的进行中任务 `T-20260524-ebee86b8`，本计划必须以该任务 merge/DONE 后 latest main 为下发硬前置。
    5. 当前仓内已有 `expectation/pass/pipeline/npu_demo_lowering.py` 锁 pipeline order，需要明确 expectation 同步授权或非本轮门禁归属。
  - 采纳结论：
    - 增加公开 API 用户确认矩阵。
    - 当时推荐第一版采用一个 pass 内按 family 多阶段 walker；用户最终决策改为 combined-pattern 收敛。
    - 下发前置增加 `T-20260524-ebee86b8 merge/DONE + latest origin/main 重核`。
    - expectation 口径加入用户决策矩阵，最终收口为不改 expectation。
  - 遗留项：按用户最新流程，该回执不再作为继续推进的前置；其建议已并入决策矩阵。
- 小李飞刀：`2026-05-24 只读互评`
  - 结论：`最小需改项`
  - 问题：
    1. 公开 API 确认不足：class / registry / fold、旧 import 桥接 / 包根 re-export 是否保留会影响 spec/test/迁移范围；该历史分歧已被 `2026-05-25` 最新确认覆盖为旧四个根模块稳定失败。
    2. “四个 pass”范围仍有歧义：CSE / Canonicalize 是否纳入会改变公开语义、dump stage 和验收口径。
    3. pattern 执行策略未机械化：单 walker 与按 family 多阶段 walker 语义可能不同。
    4. pipeline expectation 口径不够闭合：execute/review 可能把主仓旧 expectation 当阻断或误改合同资产。
    5. 迁移静态门禁需补精确矩阵：`passes/hoist` 内部 helper、旧根模块当时的桥接方案、registry/pipeline 导入需 import matrix、`__all__` exact、旧路径成功/失败矩阵、dump marker 与 9 demo gate；其中旧根模块桥接方案已被 `2026-05-25` 最新确认覆盖。
  - 采纳结论：所有建议并入用户确认矩阵与 S1/S2/S3 验收门禁；其中 pattern 执行策略以用户最终决策为准。
  - 遗留项：非前置参考；不阻塞继续提交用户决策。
- 提莫炖蘑菇：`2026-05-24 只读互评`
  - 结论：`不通过`
  - 问题：
    1. 公开 API 确认仍未闭合：exact 签名、registry、from_options / unknown option、fold 传递、第二段是否跑 alias-to-reinterpret。
    2. 旧 import 桥接与包根 re-export 缺 exact import 成功 / 失败矩阵；该历史分歧已被 `2026-05-25` 最新确认覆盖为旧四个根模块稳定失败。
    3. 按 family 多阶段 walker 的 exact 顺序、轮次、fixed-point、verify / rollback 与旧三 pass 等价证据未硬化。
    4. CSE / Canonicalize 外置仍需用户确认后写成硬门禁，并静态防止内置进新 pass。
    5. `expectation/pass/pipeline/npu_demo_lowering.py` 与同改 pipeline 前置 `T-20260524-ebee86b8` 未闭合。
  - 采纳结论：与 Codex subagent / 大闸蟹一致，全部纳入用户确认矩阵和下发前置；其中 pattern 执行策略和 expectation 口径以用户最终决策为准。
  - 遗留项：非前置参考；不阻塞继续提交用户决策。

## 计划目标

- 新增 `symbol-hoist-pipeline` pass，把当前 hoist 相关 pattern 能力作为一个 pipeline-level hoist pass 统一运行。
- 将现有 hoist 相关 pass 实现迁移到 `kernel_gen/passes/hoist/` 包内，减少 `kernel_gen/passes/` 根目录扁平堆叠。
- 将 `npu-demo-lowering` 的两段：
  - `DmaAliasToReinterpretPass -> SymbolLoopHoistPass -> HoistDmaAliasOpsPass`
  - `SymbolLoopHoistPass -> HoistDmaAliasOpsPass`
  收敛为 `SymbolHoistPipelinePass -> cse -> canonicalize`，降低 pass order 与 dump stage 噪声。
- 保持 `cse -> canonicalize` 作为新 pass 之后的独立 pipeline stage；用户已确认二者不纳入新 pass。

## 当前基线

- 当前公开合同：
  - `spec/pass/dma_alias_to_reinterpret.md` 定义公开 pass `DmaAliasToReinterpretPass(fold: bool = True)`，registry name `dma-alias-to-reinterpret`。
  - `spec/pass/symbol_loop_hoist.md` 定义公开 pass `SymbolLoopHoistPass(fold: bool = True)`，registry name `symbol-loop-hoist`。
  - `spec/pass/hoist_dma_alias_ops.md` 定义公开 pass `HoistDmaAliasOpsPass(fold: bool = True)`，registry name `hoist-dma-alias-ops`。
  - `spec/pass/pipeline/npu_demo_lowering.md` 公开固定 pipeline 顺序，当前直接列出上述 pass。
- 当前实现入口：
  - `kernel_gen/passes/dma_alias_to_reinterpret.py`
  - `kernel_gen/passes/symbol_loop_hoist.py`
  - `kernel_gen/passes/hoist_dma_alias_ops.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
  - `kernel_gen/passes/registry.py`
- 当前测试入口：
  - `test/passes/test_dma_alias_to_reinterpret.py`
  - `test/passes/test_symbol_loop_hoist.py`
  - `test/passes/test_hoist_dma_alias_ops.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_registry.py`
- 当前 dump 事实：
  - `kernel/dump/matmul/inputs_dynamic_tile_dynamic/07-dma-alias-to-reinterpret.mlir`
  - `kernel/dump/matmul/inputs_dynamic_tile_dynamic/08-symbol-loop-hoist.mlir`
  - `kernel/dump/matmul/inputs_dynamic_tile_dynamic/09-hoist-dma-alias-ops.mlir`
  - 第二段当前为 `17-symbol-loop-hoist.mlir`、`18-hoist-dma-alias-ops.mlir`，之后 `19-cse.mlir`、`20-canonicalize.mlir`。
- 当前缺口：
  - hoist 相关 pass 分散在根目录和 pipeline 顺序中，组合关系由调用方手工维护。
  - 如果直接把多个 pass 简单顺序调用进一个 wrapper，可能保留旧 pattern walker 的阶段边界；用户已明确要求“所有 pattern 一起执行”的 combined-pattern pass。
- 迁移到 `passes/hoist/` 涉及公开 import 路径；`2026-05-25` 用户最新确认覆盖旧根模块桥接草案，当前完成态为旧四个根模块稳定失败。
- 下发前置：
  - `T-20260524-ebee86b8` 已满足：主仓 `HEAD=origin/main=7dbe05d3874a6f8f4705e948a318fda167898515`，当前基线、pipeline 顺序、dump marker 与验收命令已按 latest main 重核。
  - 管理员可创建 / 排队本计划唯一 `execute`。
  - 执行开始前必须等待同改 `npu-demo-lowering` pipeline 的 `T-20260524-6dacd489` merge/DONE；依赖满足后执行人基于最新 `origin/main` 再做一次 pass-name 顺序和验收命令重核。

## 方案比较与选型

### 方案 A：新 pass 简单顺序调用旧 pass

- 内容：`SymbolHoistPipelinePass.apply(...)` 内依次调用 `DmaAliasToReinterpretPass().apply(...)`、`SymbolLoopHoistPass().apply(...)`、`HoistDmaAliasOpsPass().apply(...)`。
- 优点：实现风险最低，复用旧 pass 公开行为。
- 缺点：不符合用户“运行所有 pattern”的倾向；旧阶段边界仍存在，只是换了外层名字。
- 当前结论：不作为推荐方案，仅作为 fallback。

### 方案 B：新 pass 聚合 hoist pattern，作为一个 combined-pattern pass 运行

- 内容：把 alias-to-reinterpret、symbol-loop-hoist、hoist-dma-alias-ops 的 pattern getter / pattern family 移到 `passes/hoist/`，由 `SymbolHoistPipelinePass` 统一承载。
- 用户确认口径：
  - 新 pass 不得简单依次调用旧三个 pass 的 `apply`。
  - 新 pass 不按旧 pass family 拆成多个对外或内部阶段；它应在一个 pass 内共同运行这些 pattern。
  - 由于 hoist 相关 pattern 会相互影响，执行策略必须允许它们在同一个 pass 内收敛。
  - 仍需在 pattern 优先级 / 驱动器中保证可归一 alias 先变成 `dma.reinterpret`，再让 hoist 相关 pattern 基于归一形态继续收敛。
- 优点：符合用户“运行所有 pattern、相互影响所以放到一个 pass”的要求；pipeline 对外只看到一个 hoist stage。
- 风险：
  - pattern 优先级必须机械固定，避免 hoist pattern 在 alias 未归一时误判。
  - 如果旧 pass 原本各自拥有 rollback / verifier 边界，合并后必须有 whole-pass 级验证失败回滚，不能留下半改 IR。
  - 需要严禁跨文件调用非公开 helper，必须把可复用 pattern getter 写入 spec 与 API 列表或收敛在同包公开 API。
- 当前结论：用户已确认采用本方案；execute 必须围绕 combined-pattern 收敛补等价正例、相互影响正例和 no-op / rollback 反例。

### 方案 C：同时把 `cse/canonicalize` 合入 `symbol-hoist-pipeline`

- 内容：新 pass 内部执行 hoist patterns 后再执行 CSE / Canonicalize。
- 优点：dump stage 更少。
- 缺点：`CanonicalizePass` 是 xDSL pass，当前 spec 明确它不进入仓库 registry；合入会扩大公开语义和测试边界。
- 当前结论：不推荐；除非用户明确确认。

## 公开 API 设计

- 用户确认来源：
  - 已确认：用户要求新增 `symbol hoist pipeline pass`，并把相关 pass 放到 `passes/hoist/`。
  - 已确认：exact class name、registry name、CSE / Canonicalize 外置、不新增 expectation。
  - 最新覆盖确认：`2026-05-25` 用户确认旧 import 根模块不提供桥接，旧四个根模块稳定失败，新真源为 `kernel_gen.passes.hoist.*`。
- 公开 API：
  - `class SymbolHoistPipelinePass(fold: bool = True)`
  - `SymbolHoistPipelinePass.name: str = "symbol-hoist-pipeline"`
  - `SymbolHoistPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`
  - registry：`build_registered_pass("symbol-hoist-pipeline", {"fold": "false"})`
- package 结构：
  - `kernel_gen/passes/hoist/__init__.py`
  - `kernel_gen/passes/hoist/symbol_hoist_pipeline.py`
  - `kernel_gen/passes/hoist/dma_alias_to_reinterpret.py`
  - `kernel_gen/passes/hoist/symbol_loop_hoist.py`
  - `kernel_gen/passes/hoist/dma_alias_ops.py`
- 公开 import 口径：
  - 新实现真源放到 `kernel_gen.passes.hoist.*`。
  - 旧四个根模块稳定失败：
    - `kernel_gen.passes.dma_alias_to_reinterpret`
    - `kernel_gen.passes.symbol_loop_hoist`
    - `kernel_gen.passes.hoist_dma_alias_ops`
    - `kernel_gen.passes.symbol_buffer_hoist`
  - `kernel_gen.passes` 包根不新增 `DmaAliasToReinterpretPass` / `HoistDmaAliasOpsPass` re-export；旧根模块删除与旧路径失败由 registry/import pytest 锁定。
- registry / option / 错误语义：
  - `SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass` 仅支持 registry 通用 `fold`，不新增 pass 专属 option。
  - `fold` 语义传给 combined-pattern 驱动器内所有支持 fold 的 hoist pattern。
  - 未知非 `fold` option 稳定失败为 `PassRegistryError: pass 'symbol-hoist-pipeline' does not accept options`。

## 完成态定义

- `kernel_gen/passes/hoist/` 成为 hoist pass 真源目录。
- `SymbolHoistPipelinePass` 公开 API、registry、spec、测试均闭合。
- `npu-demo-lowering` 两段 hoist 组合改为 `SymbolHoistPipelinePass -> cse -> canonicalize`。
- 旧四个根模块不提供桥接；旧路径必须稳定失败，新真源统一为 `kernel_gen.passes.hoist.*`。
- 真实 dump 不再出现旧三段连续 stage，而出现 `symbol-hoist-pipeline` stage；`cse/canonicalize` 独立保留。
- 9 个 npu_demo kernel demo 仍全部通过，至少包含 matmul dynamic tile dynamic。
- 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/` 为空。

## 验收设计

- pytest / 脚本：
  - `pytest -q test/passes/test_symbol_hoist_pipeline.py`
  - `pytest -q test/passes/test_dma_alias_to_reinterpret.py test/passes/test_symbol_loop_hoist.py test/passes/test_hoist_dma_alias_ops.py`
  - `pytest -q test/passes/test_registry.py -k "symbol_hoist_pipeline or dma_alias_to_reinterpret or symbol_loop_hoist or hoist_dma_alias_ops"`
  - `pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
  - 9 个 npu_demo kernel demo，至少当前 hard gate：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
- 当前必过 expectation 合同验收：无。
  - 用户已确认本计划不新增、不修改、不同步 `expectation`。
  - 当前仓内若存在 `expectation/pass/pipeline/npu_demo_lowering.py` 锁旧 pipeline order，本计划记录为非本轮门禁 / 后续专项，不得由 execute 修改，也不得在本轮 review / archive_acceptance 中作为阻断。
  - execute / review / archive_acceptance 只核对候选 diff 中 `expectation/` 为空，并记录未运行或非门禁归属。
- 静态门禁：
  - 旧四个根模块必须稳定失败；不得保留旧根导入桥接或 re-export 实现。
  - 不新增 `hasattr/getattr(ctx, ...)` 能力探测。
  - 不新增非装饰器嵌套函数。
  - 测试不得跨文件直连非公开 helper。
  - `expectation/.skills/agents/standard` tracked / cached / untracked / ignored 均不得有候选 diff。

## 计划内小任务

### S1. 收口公开 API 与 hoist 目录结构

- 为什么做：新 pass 与目录迁移都涉及公开 API 和 import 路径，必须先把合同写清。
- 做什么：同步 `spec/pass/symbol_hoist_pipeline.md`、旧 pass spec 与文件级 API 列表，明确 `passes/hoist/` 目录结构、旧四个根模块稳定失败和新真源路径。
- 不做什么：不新增 package root re-export；不保留旧根导入桥接。
- 怎么验收：`pytest -q test/passes/test_registry.py -k "symbol_hoist_pipeline or builtin_passes"`；静态扫描旧路径失败策略与 spec 一致。
- 卡住问谁：公开 API 兼容 / 删除问用户；流程问管理员；实现边界问架构师。
- 上下文摘要：当前三个 pass 是已公开 API，目录迁移不是纯内部重构。
- 小任务目标：让 spec/API/import/registry 口径机械一致。
- 非目标：不改 `expectation/`。
- 模块范围：`spec/pass/**`、`kernel_gen/passes/hoist/**`、`kernel_gen/passes/registry.py`、相关 tests。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`。
- 合同真源：用户确认 > spec > pytest > 当前实现。
- 最小功能闭环：`build_registered_pass("symbol-hoist-pipeline")` 可构造新 pass；旧 pass 公开入口按最终确认保持或失败。
- 执行步骤：
  1. 新增 `spec/pass/symbol_hoist_pipeline.md`，列 API 和非目标。
  2. 更新旧 pass spec 的迁移说明和 import 口径。
  3. 更新 registry builtin 加载和测试。
- 验收必过项目：pytest 与静态门禁；expectation 暂不列必过。
- 记录要求：写清用户确认来源、旧路径策略和 registry 结果。

### S2. 实现 `SymbolHoistPipelinePass` 聚合 pattern family

- 为什么做：用户希望一个 pass 运行 hoist 相关 pattern，而不是 pipeline 手工串多段 pass。
- 做什么：在 `kernel_gen/passes/hoist/` 实现 `SymbolHoistPipelinePass`，聚合 alias-to-reinterpret、symbol-loop-hoist、dma alias hoist pattern，不调用旧 pass 的 `apply`，而是在一个 pass 内让相关 pattern 共同收敛；驱动器必须保证可归一 alias 优先变成 `dma.reinterpret`，随后 hoist 相关 pattern 基于归一形态继续收敛。
- 不做什么：不把 CSE / Canonicalize 放入新 pass；不为了测试直连旧文件私有 helper。
- 怎么验收：`pytest -q test/passes/test_symbol_hoist_pipeline.py` 覆盖同一 IR 中同时需要 alias-to-reinterpret、symbol-loop-hoist、hoist-dma-alias-ops 的正例和 no-op 反例。
- 卡住问谁：pattern 顺序影响语义问用户 / 架构师；公开 API 问用户。
- 上下文摘要：当前 pass 之间存在依赖顺序，但用户确认这些 pattern 会相互影响，需要放到一个 pass 中共同运行；实现必须用公开 pattern / API 承载这种 combined-pattern 行为。
- 小任务目标：一个公开 pass 能完成旧组合的核心 rewrite。
- 非目标：不删除旧 pass 语义测试。
- 模块范围：`kernel_gen/passes/hoist/**`、`test/passes/test_symbol_hoist_pipeline.py`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`。
- 合同真源：spec > pytest > 真实 dump。
- 最小功能闭环：公开 IR 经 `--pass symbol-hoist-pipeline` 后表现等价于旧组合的目标结果。
- 执行步骤：
  1. 迁移或暴露 hoist pattern family 的公开 getter / class。
  2. 实现新 pass 的 apply。
  3. 添加 registry 和 fold option 测试。
- 验收必过项目：`pytest -q test/passes/test_symbol_hoist_pipeline.py test/passes/test_registry.py -k "symbol_hoist_pipeline or hoist"`.
- 记录要求：写清 combined-pattern 驱动器策略、alias -> `dma.reinterpret` 优先归一规则、whole-pass verifier / rollback 边界和旧组合等价证据。

### S3. 更新 `npu-demo-lowering` 顺序与 dump gate

- 为什么做：用户目标是减少 pipeline 中连续 hoist stage，把它们收束为 `symbol-hoist-pipeline`。
- 做什么：更新 `kernel_gen/pipeline/npu_demo_lowering.py` 和 `spec/pass/pipeline/npu_demo_lowering.md` 的 pass 顺序，把两段旧 hoist pass 组合替换为 `SymbolHoistPipelinePass -> cse -> canonicalize`。
- 不做什么：不改 `MemoryPlanPass`、`SymbolBufferHoistPass`、`MemoryPoolPass`、`ArchParallelizePass` 的相对后段语义；不新增 pipeline option。
- 怎么验收：`pytest -q test/passes/pipeline/test_npu_demo_lowering.py` 断言两处 `symbol-hoist-pipeline -> cse -> canonicalize`，不再绑定旧 dump 编号。
- 卡住问谁：pipeline 公开顺序争议问用户；实现失败归属问架构师。
- 上下文摘要：pipeline 顺序是公开行为，必须和 spec/test 同批改。
- 小任务目标：公开 builder 输出新顺序，真实 dump marker 与 spec 一致。
- 非目标：不接入 multi-buffer，不移动 memory-pool 后段。
- 模块范围：`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`。
- 合同真源：用户确认的新 pipeline 顺序 > spec pipeline 顺序 > pytest dump marker > 当前 dump。
- 最小功能闭环：`inputs_dynamic_tile_dynamic` dump 里旧 07/08/09 连续 stage 被新 single stage 替代，后续 CSE/Canonicalize 存在。
- 执行步骤：
  1. 替换 builder 中两段旧 pass 组合。
  2. 更新 pipeline 文件级说明和 spec 公开顺序。
  3. 更新 pipeline pass order / dump marker tests。
- 验收必过项目：pipeline pytest、9 个 demo。
- 记录要求：记录旧 marker -> 新 marker 映射和 demo exit code。

### S4. 回归旧 pass 与 9 个 kernel demo

- 为什么做：新聚合 pass 和目录迁移可能破坏旧独立 pass、registry 或 kernel demo。
- 做什么：复跑旧 pass 测试、registry、pipeline 和 9 个 demo；按 diff 反推补测试。
- 不做什么：不以 expectation 替代 diff 反推测试；不修改 expectation。
- 怎么验收：列出的 pytest / demo / py_compile / git diff check / 敏感目录门禁全部通过。
- 卡住问谁：expectation 冲突问架构师；公开 API 冲突问用户；流程问管理员。
- 上下文摘要：该计划风险主要是公开 API 迁移和 pipeline stage 改名。
- 小任务目标：证明旧独立能力、新聚合能力和真实 demo 都可运行。
- 非目标：不修复计划外 kernel 数值问题；若出现计划外红点先记录归属。
- 模块范围：`kernel_gen/passes/**`、`kernel_gen/pipeline/**`、`spec/pass/**`、`test/passes/**`、`kernel/*` demo gate。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`。
- 合同真源：pytest / demo > current dump；expectation 不作为本计划必过。
- 最小功能闭环：所有指定测试通过，任务记录含 diff 反推自测。
- 执行步骤：
  1. 运行 py_compile。
  2. 运行 pass / pipeline pytest。
  3. 运行 9 个 demo。
  4. 运行敏感目录门禁。
- 验收必过项目：本计划验收设计命令。
- 记录要求：逐项写命令、exit code、失败归属和剩余风险。

## 计划自检与返工口径

- 当前计划已完成 Codex 内置 `subagent` 讨论；无需再等待其它角色互评回执。
- 用户已确认公开 API 新增、旧路径不提供桥接、`4 个 pass` 精确范围、CSE/Canonicalize 外置、combined-pattern 执行策略和不改 `expectation`。
- 当前下发状态：`T-20260524-ebee86b8` 已满足，本计划可由管理员创建 / 排队唯一计划级 `execute`；执行开始前必须等待同改 `npu-demo-lowering` 的 `T-20260524-6dacd489` merge/DONE，避免两个任务并行改同一 pipeline。
- 若后续非前置参考回执指出 API、目录迁移、pattern 顺序、pipeline 验收或旧 pass 兼容存在实际阻断，可作为计划修订依据；但不再作为本轮继续提交用户决策的前置。

## 用户已确认项

### C0. 公开 API 确认矩阵

| 项目 | 用户确认合同 | 影响 |
| --- | --- | --- |
| 新公开 class | `class SymbolHoistPipelinePass(fold: bool = True)` | 新增公开 pass API，用户已确认。 |
| pass name | `SymbolHoistPipelinePass.name = "symbol-hoist-pipeline"` | 新 registry 名称和 dump marker。 |
| registry name | `build_registered_pass("symbol-hoist-pipeline")` | 新公开工具 / ircheck pass 名。 |
| options | 不新增 pass 专属 option；只接受 registry 通用 `fold` | 避免扩大公开参数面。 |
| unknown option 错误 | `PassRegistryError: pass 'symbol-hoist-pipeline' does not accept options` | 稳定错误语义，需 spec/pytest 锁定。 |
| `fold` 传递 | 同一 `fold` 值传给 combined-pattern 驱动器内所有支持 fold 的 pattern | 保持旧 pass 可控行为一致。 |
| second stage | 第二段也运行完整 `symbol-hoist-pipeline`，其中 alias-to-reinterpret pattern 在无旧 alias op 时 no-op | pipeline 更简单，属于用户确认过的公开行为变化。 |
| 包根 re-export | 不新增 `DmaAliasToReinterpretPass` / `HoistDmaAliasOpsPass` 到 `kernel_gen.passes` 包根；既有 `SymbolLoopHoistPass` 包根 re-export 保持 | 防止扩大包根公开面。 |
| 旧根模块 | `2026-05-25` 最新确认覆盖第一版桥接草案；旧四个根模块稳定失败，新真源为 `kernel_gen.passes.hoist.*` | 与当前候选实现、spec 和 pytest 负例一致。 |
| CSE / Canonicalize | 外置，pipeline 顺序为 `symbol-hoist-pipeline -> cse -> canonicalize` | 不扩大新 pass 公开语义。 |
| pattern 执行策略 | 一个 pass 内共同运行相关 pattern；可归一 alias 优先变成 `dma.reinterpret`，随后 hoist pattern 继续收敛；不得依次调用旧 pass `apply` | 满足用户“pattern 会相互影响，所以放到一个 pass”的原因。 |
| expectation | 本计划不新增、不修改、不同步 `expectation`；execute 候选 diff 保持 `expectation/` 空 | 旧 pipeline expectation 若冲突，记录为非本轮门禁 / 后续专项。 |

### C1. 旧公开 import 路径如何处理

- 问题：旧 pass 移到 `kernel_gen/passes/hoist/` 后，旧 import 路径是否保留。
- 用户确认：`2026-05-25` 最新确认覆盖第一版桥接草案；旧路径不保留 re-export，旧四个根模块稳定失败，新真源在 `kernel_gen.passes.hoist.*`。
- 完成态：旧 `kernel_gen.passes.dma_alias_to_reinterpret`、`kernel_gen.passes.symbol_loop_hoist`、`kernel_gen.passes.hoist_dma_alias_ops`、`kernel_gen.passes.symbol_buffer_hoist` 均稳定失败；不新增 `DmaAliasToReinterpretPass` / `HoistDmaAliasOpsPass` 到 `kernel_gen.passes` 包根。
- 影响：删除旧路径已纳入本计划完成态，必须由 import 负例与 registry 测试锁定。

### C2. “4 个 pass”的精确范围

- 问题：用户提到“四个 pass”，当前点名唯一业务 pass 为三个；`cse/canonicalize` 是否算进新 pass。
- 用户确认：新 pass 只聚合 `dma-alias-to-reinterpret`、`symbol-loop-hoist`、`hoist-dma-alias-ops` 的业务 pattern；`cse/canonicalize` 仍在外面。
- 完成态：pipeline 中 `symbol-hoist-pipeline` 后仍显式保留 `cse -> canonicalize`。
- 影响：把 `cse` 或 `canonicalize` 放入新 pass 不纳入本计划。

### C2B. 第二段是否也运行 `dma-alias-to-reinterpret`

- 问题：当前第二段只有 `symbol-loop-hoist -> hoist-dma-alias-ops`；新 `symbol-hoist-pipeline` 若固定包含 `dma-alias-to-reinterpret`，第二段会新增一次 alias 归一 family。
- 用户确认：第二段也运行完整 `symbol-hoist-pipeline`；其中 alias-to-reinterpret pattern 在没有旧 alias op 时 no-op。
- 完成态：不定义第二个 pass，不新增“跳过 alias-to-reinterpret”的 option。
- 影响：需要 pytest/dump 证明第二段新增 alias 归一能力无回归。

### C3. `symbol-hoist-pipeline` 的 pattern 执行策略

- 问题：新 pass 是一次 GreedyRewritePatternApplier 跑所有 pattern，还是按旧 pass family 分段多轮跑。
- 用户确认：不是按旧 pass family 分段；所有相关 pattern 在一个 pass 内共同运行，因为这些 pattern 会相互影响。
- 完成态：实现不得简单调用旧 pass `apply`，也不得把旧三 pass 阶段边界原样搬进新 pass；实现需要固定 pattern 优先级 / 驱动策略，使可归一 alias 先成为 `dma.reinterpret`，随后 hoist 相关 pattern 在同一 pass 中继续收敛。
- 影响：这是本计划核心公开行为，必须用组合正例、相互影响正例、no-op 反例和 rollback 反例锁定。

### C4. 用户“前面 2 公开 pass”的解释

- 问题：该短句需要转成 exact API 合同。
- 用户确认：新增 `SymbolHoistPipelinePass` 为公开 pass；`2026-05-25` 最新确认旧单 pass 根模块路径不提供桥接。
- 影响：registry、spec、测试和旧路径失败矩阵按该合同实现。

### C5. `expectation/pass/pipeline/npu_demo_lowering.py` 是否纳入本计划

- 问题：该 expectation 当前锁旧 pipeline order，本计划会改公开 pipeline stage。
- 用户确认：不新增、不修改、不同步 expectation。
- 完成态：本计划不运行 `expectation/pass/pipeline/npu_demo_lowering.py` 作为必过门禁；若其仍锁旧顺序，记录为非本轮门禁 / 后续专项。
- 影响：execute / review / archive_acceptance 只检查候选 diff 中 `expectation/` 为空，不得自行复制或修改 expectation。

## 用户确认与协同约束

- 用户确认来源：
  - `2026-05-24` 用户要求新增 `symbol hoist pipeline pass`，整合 hoist 相关功能，并把相关 pass 放到 `passes/hoist/`。
  - `2026-05-24` 用户要求按新版计划书流程行动。
  - `2026-05-24` 用户确认 `SymbolHoistPipelinePass(fold=True)`、registry name `symbol-hoist-pipeline`、只接受 `fold`、CSE / Canonicalize 外置、新 pass 使用旧 pattern 且先归一为 `dma.reinterpret` 后运行 hoist pattern、本轮不改 expectation。
  - `2026-05-25` 用户最新确认覆盖旧路径桥接草案：`symbol_buffer_hoist` 也迁入 `kernel_gen/passes/hoist/`，旧四个根模块不提供桥接并稳定失败，新真源为 `kernel_gen.passes.hoist.*`。
- 用户确认来源：用户确认“计划草案阶段只问 Codex 内置 subagent 即可；除终审外不需要询问其他人”。
- Codex 内置 subagent：已完成讨论，结论见“多人讨论记录”。
- 其它角色回执：不作为下发前置；已收到的大闸蟹、小李飞刀、提莫炖蘑菇回执作为参考记录。
- 下发前置：`T-20260524-ebee86b8` 已显式满足；本计划可通知管理员创建 / 排队唯一计划级 execute。由于 `T-20260524-6dacd489` 当前仍在 TODO 执行中且同改 pipeline，该 execute 必须依赖 `T-20260524-6dacd489` merge/DONE 后再开始。
