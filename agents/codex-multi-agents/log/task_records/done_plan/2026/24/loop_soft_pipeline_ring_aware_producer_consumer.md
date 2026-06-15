# loop_soft_pipeline_ring_aware_producer_consumer 计划书

## 文档信息

- 状态：已完成计划级 `execute -> review -> archive_acceptance` 入档验收，当前待 `merge/归档`；R1 / R2 / R3 / G1 / G2 为下发前历史记录，落地证据见任务 `T-20260613-bac54fd8` 记录。
- 用户需求来源：2026-06-13 用户确认按 ring current / advance 语义做 ping-pong，并要求“pass 叫作 loop soft pipeline”，同时扩展 `producer-consumer-analysis`，按计划书流程先讨论、用户决策、再补 `expectation` 推进。
- 下发前正式候选范围只包含本计划文本和引用的 `ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md` 说明文档；计划级 execute 落地范围为本计划明确的 `spec`、实现、测试与任务记录，不修改 `expectation/` 本体。
- 跟踪状态：本文件已按 G2 正式候选迁移要求通过 `git add -f` 纳入 index；`ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md` 作为同一架构参考文档纳入候选。
- 参考说明：[`ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md`](../reference/matmul_pingpong_producer_consumer_ir.md)

### 用户决策记录

- Q1 已确认：新增 `LoopSoftPipelinePass`，registry 名称 `loop-soft-pipeline`，module path 使用 `kernel_gen.passes.schedule.loop_soft_pipeline`。
- Q2 已确认：第一版暂不新增共享 `ring_cursor_analysis` 公开 API；两个 pass 各自独立实现 ring cursor / alias / MemoryEffect 分析逻辑，后续如需抽公共能力再另行确认公开 API。
- Q3 已确认：新增 `loop_first_productor/consumer` 与 `loop_carried_productor/consumer`。
- Q4 已确认：`N == 1` 且 K 维正数时退化为 `prologue copy -> epilogue matmul`，使用普通 `productor` / `consumer`，不新增 `prologue_epilogue_*` attr。
- Q5 已确认：`expectation/pass/pipeline/npu_demo_lowering.py` 不纳入本轮 expectation 修改范围；pipeline 顺序变化用 `spec`、pytest 和 dump 验收。
- Q6 已确认：首版只锁 matmul dynamic/dynamic A/B 输入链，其它形态 no-op 或保持现状，不新增稳定错误作为 unsupported 行为。
- 零 tile 边界：若 `N == 0` 或无法证明至少存在一个 K tile，且当前 IR 无法构造保持语义的 guard，`loop-soft-pipeline` 必须 no-op / 保持现状；不得生成无条件 prologue。

### 目标 `spec`

- 已新增：`spec/pass/loop_soft_pipeline.md`
- 已更新：`spec/pass/producer_consumer_analysis.md`
- 已更新：`spec/pass/pipeline/npu_demo_lowering.md`
- 已更新：`spec/pass/registry.md`

### 目标公开 API

本计划涉及公开 API / 公开行为变化。Q1 / Q2 / Q3 / Q4 / Q5 / Q6 已按用户决策记录收口；落地实现不得超出以下公开 API / 公开行为边界。

- 新 pass：
  - class：`LoopSoftPipelinePass(fold: bool = True)`
  - 方法：`LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass`
  - 方法：`LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`
  - registry pass name：`loop-soft-pipeline`
  - canonical module path：`kernel_gen.passes.schedule.loop_soft_pipeline`
  - 不新增 package re-export；`kernel_gen.passes.schedule.LoopSoftPipelinePass` 与 `kernel_gen.passes.LoopSoftPipelinePass` 不在本轮目标 API 内，如需新增必须另行取得用户确认。
  - 不新增 pass 专属稳定错误文本；第一版不接受 pass 专属 option，未知 option 走现有 registry 通用错误路径。若实现必须新增 `LoopSoftPipelinePassError` 或其它稳定错误语义，必须暂停并回到用户确认。
- `producer-consumer-analysis` 公开 attr 合同扩展：
  - 新增 `loop_first_productor` / `loop_first_consumer`
  - 新增 `loop_carried_productor` / `loop_carried_consumer`
  - 继续保留既有 `productor` / `consumer`、`loop_body_*`、`after_loop_*`、`if_branch_*`、`after_if_*`
- `npu-demo-lowering` pipeline 公开顺序变化：
  - 从 `multi-buffer -> producer-consumer-analysis -> memory-pool`
  - 改为 `multi-buffer -> loop-soft-pipeline -> producer-consumer-analysis -> memory-pool`
- 共享抽象能力：
  - 第一版不新增共享公开 `ring_cursor_analysis` API。
  - `LoopSoftPipelinePass` 与 `ProducerConsumerAnalysisPass` 各自在当前文件内实现所需 ring cursor / alias / MemoryEffect 逻辑。
  - 两个 pass 只能共享公开概念和 spec 口径，不得跨文件调用非公开 helper。
  - 后续如果需要抽取公共能力，必须另行提交公开 API 待确认项。

### 目标测试与验收资产

- 已新增：`test/passes/schedule/test_loop_soft_pipeline.py`
- 已更新：`test/passes/test_producer_consumer_analysis.py`
- 已更新：`test/passes/test_registry.py`
- 已更新：`test/passes/pipeline/test_npu_demo_lowering.py`
- 只读合同验收资产（按 Q5 用户确认，仅限架构授权范围；不是计划级 `execute` 的普通改动）：
  - `expectation/pass/loop_soft_pipeline/**`
  - `expectation/pass/producer_consumer_analysis/**`
- 不纳入本轮 expectation 修改范围：
  - `expectation/pass/pipeline/npu_demo_lowering.py`

## 计划级任务

- 当前状态：任务 `T-20260613-bac54fd8` 已完成 `execute -> review -> archive_acceptance` 入档验收，待 `merge/归档`。
- 正式计划只允许一个计划级 `execute` 大任务。
- 固定流转：`execute -> review -> archive_acceptance -> merge/归档`。
- 若 `review` 或 `archive_acceptance` 不通过，回到同一个 `execute`，不得另设 `refactor` 阶段。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `loop-soft-pipeline-ring-aware-producer-consumer` | `execute` | `/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer` | `agents/codex-multi-agents/log/task_records/2026/24/20260613-loop-soft-pipeline-ring-aware-producer-consumer.md` |

## 当前基线

- `npu-demo-lowering` 当前公开 pipeline 顺序中，`multi-buffer` 后直接进入 `producer-consumer-analysis`，再进入 `memory-pool`。
- 当前 dump 顺序在 matmul dynamic/dynamic 中表现为：
  - `24-multi-buffer.mlir`
  - `25-producer-consumer-analysis.mlir`
  - `26-memory-pool.mlir`
  - `27-cse.mlir`
  - `28-canonicalize.mlir`
- 当前 `24-multi-buffer.mlir` 已有 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
- 当前 `25-producer-consumer-analysis.mlir` 的 A/B 输入关系仍是同一轮：

```text
A_G2S[k] -> A_S2L[k] -> M[k]
B_G2S[k] -> B_S2L[k] -> M[k]
```

- 当前 `ProducerConsumerAnalysisPass` 只基于 SSA alias/use 和静态控制流分类建边；`spec/pass/producer_consumer_analysis.md` 明确写着 `symbol.for` 第一阶段不承诺 loop-carried、zero-trip 或跨迭代 runtime 精确语义。
- 当前 `ProducerConsumerAnalysisPass` 的公开 attr 不包含 `loop_first_*` 或 `loop_carried_*`。
- 当前 `producer-consumer-analysis` 不建模 ring cursor；它不知道两次不同的 `dma.current_ring(%ring)` 在“没有中间 advance”时可能指向同一 runtime slot，也不知道 `advance` 后的后续 `current_ring` 指向 next slot。
- 已有讨论结论：
  - `advance_ring` 只改变后续 `current_ring` 的 cursor，不表达读写。
  - producer/consumer 边来自“同一个 slot 上先 WRITE 后 READ”。
  - 分析必须先做 cursor trace，再做 MemoryEffect trace。
- 现有相关计划：
  - `ARCHITECTURE/plan/multi_buffer_analysis_apply_split.md` 正在处理 `multi-buffer` split / staged expectation 边界。
  - 本计划正式 execute 开始前必须确认该计划已合并，或确认它与本计划不会并行改同一公开 pipeline / registry / multi-buffer 文件。

## 计划目标

- 新增 `loop-soft-pipeline` pass，在 `multi-buffer` 之后、`producer-consumer-analysis` 之前运行。
- `loop-soft-pipeline` 不依赖旧 `productor` / `consumer` attr，不强依赖 `producer-consumer-analysis` 的结果。
- pass 基于 `dma.current_ring` / `dma.advance_ring`、MemoryEffect、view alias 和局部控制流识别可 soft pipeline 的 ring staging 模式。
- 第一版目标是 matmul dynamic/dynamic 的 A/B 输入链：

```text
lhs/rhs -> tsm_a/tsm_b -> tlm_a/tlm_b -> kernel.matmul
```

- 变换目标是把 K loop 从“本轮搬、本轮算”改成：

```text
prologue:
  preload k0

steady loop:
  compute current
  advance tlm
  preload next
  advance tsm
  do not advance tlm after preload

epilogue:
  compute last preloaded
  advance tlm
```

- 扩展 `producer-consumer-analysis`，让它能在 soft-pipeline 后 IR 上重新分析出：

```text
prologue A_S2L[0] -> steady first M[0]
body A_S2L[t+1]   -> next body M[t+1]
last body A_S2L   -> epilogue M[last]
```

以及 B 链的同构关系。

- `acc`、bias、out 不参与 A/B 输入 ping-pong。它们仍按现有 fill / matmul / bias / output 生产消费链分析。
- 完成后 pipeline dump 顺序预期变为：

```text
24 multi-buffer
25 loop-soft-pipeline
26 producer-consumer-analysis
27 memory-pool
28 cse
29 canonicalize
...
```

## 非目标

- 不做 async token、`arch.sign`、`arch.wait`、barrier 或真实异步 overlap。
- 不修改 `multi-buffer` 的 ring 化目标；本计划消费 `multi-buffer` 的输出。
- 不依赖 `producer-consumer-analysis` 的旧 event attr 作为 soft-pipeline 输入。
- 不在第一版处理任意 control-flow、nested region、多 producer、多 reader、多 ring group 的全通用调度。
- 不把 `acc` / output tile 当作 K 维 ping-pong ring slot。
- 不新增 pipeline option。
- 不修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 除 Q5 明确授权的架构侧预置范围外，不修改 `expectation/`；`execute`、`review`、`merge` 和管理员只允许读取、执行、引用与记录。

## 方案比较与选型

### 方案 A：先 `producer-consumer-analysis`，再 `loop-soft-pipeline`

- 内容：沿用 `24 -> 25` 的同轮 `copy -> matmul` event，soft pipeline pass 尝试继承旧 event。
- 优点：可以复用当前 `[8] [9] [10] [11]` 作为原始证据。
- 缺点：
  - ping-pong 后 event 分类会改变：同轮边变成 prologue / loop-carried / epilogue 边。
  - 旧 event id 无法原样复制；同一个旧 `[10]` 会拆成多条 runtime 边。
  - pass 会强依赖 `producer-consumer-analysis`，不符合用户要求。
- 结论：不推荐。

### 方案 B：先 `loop-soft-pipeline`，再 `producer-consumer-analysis`

- 内容：`loop-soft-pipeline` 基于 ring cursor / MemoryEffect 自己识别可调度段，生成 prologue / steady / epilogue；随后 `producer-consumer-analysis` 对最终 IR 重新标注。
- 优点：
  - soft pipeline pass 通用，不绑定现有 event attr。
  - producer-consumer 结果反映最终 IR，不需要继承旧编号。
  - 后续可以继续扩展 ring-aware 分析和其它调度模式。
- 缺点：
  - `producer-consumer-analysis` 必须新增 ring-aware cursor trace。
  - 需要新增公开 attr 分类表达 loop-carried 边。
- 结论：推荐。

### 方案 C：`loop-soft-pipeline` 输出显式调度 metadata，producer-consumer 只消费 metadata

- 内容：soft pipeline pass 输出显式 schedule attr，producer-consumer 不再从 ring cursor 反推跨迭代关系。
- 优点：分析简单，event 边可直接来自 schedule metadata。
- 缺点：
  - 新增一套公开 IR metadata 合同，后续维护成本高。
  - 容易把调度 pass 和分析 pass 绑定过紧。
- 结论：不作为第一版主线；可作为后续优化或 fallback。

## 推荐公开 API 设计

### `LoopSoftPipelinePass`

已确认新增公开 pass：

```python
class LoopSoftPipelinePass(fold: bool = True)
LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass
LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None
```

- registry pass name：`loop-soft-pipeline`
- 第一版不接受 pass 专属 option。
- `fold` 继续由 registry 通用 option 处理。
- 不新增 `LoopSoftPipelinePassError` 或 pass 专属稳定错误文本；未知 option 走现有 registry 通用路径。若现有 registry 不能表达该行为，执行必须暂停并回到用户确认。

已确认 package path：

```text
kernel_gen/passes/schedule/loop_soft_pipeline.py
```

确认原因：这是调度类 pass，不应放入 `memory/`，避免与 `multi-buffer` 的 storage ring 化职责混淆。后续若新增 `loop-unroll`、`loop-tile-schedule`、`async-pipeline`，可以归入同一 `schedule` 包。

### `producer-consumer-analysis` attr 扩展

已确认新增 attr：

| attr | 含义 |
| --- | --- |
| `loop_first_productor` | loop 前 producer 供 steady loop 第一轮 consumer 使用 |
| `loop_first_consumer` | steady loop 第一轮 consumer 消费 loop 前 producer |
| `loop_carried_productor` | steady loop 第 `t` 轮 producer 供第 `t + 1` 轮 consumer 使用 |
| `loop_carried_consumer` | steady loop 第 `t + 1` 轮 consumer 消费上一轮 producer |

继续使用既有：

| attr | 用法 |
| --- | --- |
| `productor` / `consumer` | 同 block 普通顺序边 |
| `after_loop_productor` / `after_loop_consumer` | loop body 最后一轮 producer 供 loop 后 consumer |
| `loop_body_productor` / `loop_body_consumer` | loop 前 producer 供 loop body 静态 consumer，保留当前语义 |

注意：`loop_first_*` 和 `loop_carried_*` 是公开 attr 变更，用户已确认采用；必须同步 `spec`、pytest，并由架构在 Q5 授权范围内预置 `expectation`。计划级 `execute` 不得修改 `expectation/` 本体。

### ring cursor 分析抽象

第一版不新增共享公开支持模块。两个 pass 各自独立实现当前文件内的 ring cursor / alias / MemoryEffect 逻辑，避免新增一组过早固定的公开 API。

两个实现必须保持同一概念模型：

- 读取 `dma.current_ring` / `dma.advance_ring` 顺序。
- 为 `dma.current_ring` 结果及其 `dma.reinterpret/view/reshape/subview` alias 建立 slot identity。
- 收集 MemoryEffect：
  - `READ(slot)`
  - `WRITE(slot)`
  - `ALLOC(slot)`
  - `FREE(slot)`
- 不分配 producer-consumer event id。
- 不做 IR rewrite。
- 不跨文件调用非公开 helper。

后续若两个 pass 的内部实现出现稳定重复逻辑，再单独讨论是否新增 `kernel_gen.passes.analysis.ring_cursor_analysis` 公开 API。

## 核心 IR 结果

### `loop-soft-pipeline` 输出形态

第一版在 matmul dynamic/dynamic A/B 输入链上输出：

```mlir
// prologue
"dma.deslice"(%tsm_a0, %global_a0, ...)
"dma.deslice"(%tsm_b0, %global_b0, ...)
"dma.copy"(%tlm_a0, %tsm_a0)
"dma.copy"(%tlm_b0, %tsm_b0)
"dma.advance_ring"(%tsm_a_ring)
"dma.advance_ring"(%tsm_b_ring)
// no advance tlm

symbol.for %k = %k0 to %steady_end step %tile_k {
  %tlm_a_cur = "dma.current_ring"(%tlm_a_ring)
  %tlm_b_cur = "dma.current_ring"(%tlm_b_ring)
  "kernel.matmul"(%acc, %tlm_a_cur, %tlm_b_cur, %acc_flag)

  "dma.advance_ring"(%tlm_a_ring)
  "dma.advance_ring"(%tlm_b_ring)

  "dma.deslice"(%tsm_a_next, %global_a_next, ...)
  "dma.deslice"(%tsm_b_next, %global_b_next, ...)
  "dma.copy"(%tlm_a_next, %tsm_a_next)
  "dma.copy"(%tlm_b_next, %tsm_b_next)
  "dma.advance_ring"(%tsm_a_ring)
  "dma.advance_ring"(%tsm_b_ring)
  // no advance tlm
}

// epilogue
"kernel.matmul"(%acc, %tlm_a_last, %tlm_b_last, %acc_flag_last)
"dma.advance_ring"(%tlm_a_ring)
"dma.advance_ring"(%tlm_b_ring)
```

### `producer-consumer-analysis` 输出形态

ring-aware 分析后应能标出：

```mlir
"dma.copy"(%tlm_a0, %tsm_a0)
  {consumer = [100], loop_first_productor = [102]}

"dma.copy"(%tlm_b0, %tsm_b0)
  {consumer = [101], loop_first_productor = [103]}

symbol.for %k = %k0 to %steady_end step %tile_k {
  "kernel.matmul"(%acc, %tlm_a_cur, %tlm_b_cur, %acc_flag)
    {loop_first_consumer = [102, 103],
     loop_carried_consumer = [106, 107],
     after_loop_productor = [200]}

  "dma.copy"(%tlm_a_next, %tsm_a_next)
    {consumer = [104], loop_carried_productor = [106], after_loop_productor = [108]}

  "dma.copy"(%tlm_b_next, %tsm_b_next)
    {consumer = [105], loop_carried_productor = [107], after_loop_productor = [109]}
}

"kernel.matmul"(%acc, %tlm_a_last, %tlm_b_last, %acc_flag_last)
  {after_loop_consumer = [108, 109], after_loop_productor = [201]}
```

其中：

```text
[102] prologue A_S2L[0] -> steady first M[0]
[103] prologue B_S2L[0] -> steady first M[0]
[106] body A_S2L[t+1]   -> next body M[t+1]
[107] body B_S2L[t+1]   -> next body M[t+1]
[108] last body A_S2L   -> epilogue M[last]
[109] last body B_S2L   -> epilogue M[last]
```

## 实现设计

### 抽象层次

推荐实现分四层，便于后续扩展：

1. `MemoryAccess` 层
   - 只负责从公开 `MemoryEffect` 读取 READ / WRITE / ALLOC / FREE。
   - 继续遵守不调用跨文件非公开 effect helper 的规则。
2. `Alias` 层
   - 统一处理 `dma.reinterpret` / `dma.view` / `dma.reshape` / `dma.subview`。
   - `dma.deslice` 不产生 alias result，只按 effect 建 READ / WRITE。
3. `RingCursor` 层
   - 对每个 `%ring` 建 cursor trace。
   - `current_ring(%ring)` 读取当前 slot。
   - `advance_ring(%ring)` 更新后续 current slot。
   - `advance_ring` 本身不产生 READ / WRITE。
4. `SchedulePattern` 层
   - `loop-soft-pipeline` 在这一层识别：

```text
READ current tlm
advance tlm
WRITE next tlm
no advance tlm until loop tail
```

   - `producer-consumer-analysis` 在这一层把 `WRITE(slot) -> READ(slot)` 转成 event attr。

### `loop-soft-pipeline` rewrite 约束

候选 loop 必须满足：

- 目标 loop 是 `symbol.for`。
- A/B TSM/TLM ring current、global load、TSM->TLM copy、matmul、advance 的相对顺序可证明。
- TLM slot 在同一轮 `matmul` 读完后才 advance。
- TSM slot 在 TSM->TLM copy 后 advance。
- A/B 两条输入链必须成对识别；单边缺失 no-op。
- 若 `N == 0`、无法证明存在第一个 tile，或无法用现有 IR 生成保护 prologue 的 guard，必须 no-op / 保持现状。
- `N == 1` 退化为 prologue copy 与 epilogue matmul，后续 `producer-consumer-analysis` 使用普通 `productor` / `consumer` 建边。
- `acc` 在 K loop 内跨轮累加，不能纳入 A/B ping-pong ring。
- bias / out 在 K loop 后，不能被移动进 steady body。
- 原 event attrs 若存在，rewrite 后必须清理，交给后续 `producer-consumer-analysis` 重新标注。

### `producer-consumer-analysis` ring-aware 约束

分析过程：

```text
1. 清理旧 event attrs，包括新增 loop_first_* / loop_carried_*。
2. 建 alias root。
3. 建 ring cursor trace。
4. 收集 READ / WRITE access facts。
5. 对每个 slot 维护 last_writer。
6. READ(slot) 时连到最近 WRITE(slot)。
7. 根据 producer/consumer 所在控制流位置分类为普通、loop_first、loop_carried、after_loop 等。
8. 写回 event attr。
```

分类规则：

| producer 位置 | consumer 位置 | attr |
| --- | --- | --- |
| prologue | steady loop 第一轮 | `loop_first_*` |
| steady 第 `t` 轮 | steady 第 `t` 轮 | `productor` / `consumer` |
| steady 第 `t` 轮 | steady 第 `t + 1` 轮 | `loop_carried_*` |
| steady 最后一轮 | epilogue | `after_loop_*` |
| prologue | epilogue 且 steady 为空 | 普通 `productor` / `consumer` |

## 架构侧 `expectation` 预置计划

Q5 已确认允许新增 / 修改 `expectation/pass/loop_soft_pipeline/**` 与 `expectation/pass/producer_consumer_analysis/**`。该步骤只能由用户或架构师在授权范围内执行，不能放入计划级 `execute` 正常任务；执行、审查、合并和管理员只能读取、运行、引用与记录。

架构预置前后必须记录：

- 用户确认来源：2026-06-13 Q5。
- 合同目标：锁定 `loop-soft-pipeline` 输出 IR 与 soft-pipeline 后 ring-aware producer-consumer 分析结果。
- 授权 scope：`expectation/pass/loop_soft_pipeline/**`、`expectation/pass/producer_consumer_analysis/**`。
- 禁止 scope：`expectation/pass/pipeline/npu_demo_lowering.py` 和其它 `expectation/` 路径。
- 开始 / 结束 manifest 或 hash。
- `git status --short --ignored`、tracked / staged / untracked / ignored 检查。
- scope 外空 diff。
- 合同验收命令与预期输出。

本轮不修改 `expectation/pass/pipeline/npu_demo_lowering.py`；pipeline 顺序变化只通过 `spec`、pytest 和 dump 验收。

### 新增 `expectation/pass/loop_soft_pipeline/**`

建议 leaf：

- `matmul_dynamic_ring_pipeline.py`
  - 输入：最小化的 `multi-buffer` 后 matmul dynamic/dynamic IR。
  - 预期：输出 prologue / steady / epilogue，dump 阶段文件名或测试 marker 出现 `loop-soft-pipeline`；该 marker 不是新增 IR attr。
  - 检查：prologue copy 后无 TLM advance；body matmul 后 TLM advance；body copy next 后无 TLM advance；epilogue matmul 后 TLM advance。
- `clears_old_events.py`
  - 输入：带旧 `productor/consumer` attr 的 ring IR。
  - 预期：rewrite 后旧 event attr 被清理，不原样继承。
- `unsupported_noop.py`
  - 输入：A/B 单边缺失、已有不匹配 advance、acc ring 等不安全形态。
  - 预期：no-op / 保持现状，不新增稳定错误。

### 更新 `expectation/pass/producer_consumer_analysis/**`

建议新增 leaf：

- `ring_loop_first.py`
  - 锁 `prologue A_S2L[0] -> steady first M[0]`。
- `ring_loop_carried.py`
  - 锁 `body A_S2L[t+1] -> next body M[t+1]`。
- `ring_after_loop.py`
  - 锁 `last body A_S2L -> epilogue M[last]`。
- `ring_cursor_current_advance.py`
  - 锁 `advance` 只改变 cursor，不代表 read/write。
  - 检查 `current` 在 advance 前后得到不同 slot identity。

## 完成态定义

- `spec/pass/loop_soft_pipeline.md` 定义新 pass 公开 API、registry 名称、行为、非目标、option 处理和 no-op 语义；不新增 pass 专属稳定错误文本。
- `spec/pass/producer_consumer_analysis.md` 定义 ring-aware 分析与新 event attr。
- `spec/pass/pipeline/npu_demo_lowering.md` 固定新顺序。
- `kernel_gen/passes/schedule/loop_soft_pipeline.py` 实现 `LoopSoftPipelinePass`，并通过 registry 构造。
- `kernel_gen/passes/producer_consumer_analysis.py` 支持 ring-aware cursor trace 和新增 attr 清理 / 写回。
- `kernel_gen/pipeline/npu_demo_lowering.py` 顺序变为 `MultiBufferPass -> LoopSoftPipelinePass -> ProducerConsumerAnalysisPass -> MemoryPoolPass`。
- `kernel/matmul/inputs_dynamic_tile_dynamic.py` 生成 dump 时，预期出现：

```text
24-multi-buffer.mlir
25-loop-soft-pipeline.mlir
26-producer-consumer-analysis.mlir
27-memory-pool.mlir
```

- `25-loop-soft-pipeline.mlir` 中 A/B 输入链被拆成 prologue / steady / epilogue。
- `26-producer-consumer-analysis.mlir` 中 TLM A/B 边包含 `loop_first_*`、`loop_carried_*`、`after_loop_*`。
- `acc`、bias、out 的既有生产消费关系不被破坏。
- 未授权或不安全 ring 形态保持 no-op，不生成错误 ping-pong。

## 验收设计

### pytest

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/passes/schedule/test_loop_soft_pipeline.py \
  test/passes/test_producer_consumer_analysis.py \
  test/passes/test_registry.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/passes/pipeline/test_npu_demo_lowering.py
```

### kernel demo / dump

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py
```

执行后核对：

- `kernel/dump/matmul/inputs_dynamic_tile_dynamic/25-loop-soft-pipeline.mlir`
- `kernel/dump/matmul/inputs_dynamic_tile_dynamic/26-producer-consumer-analysis.mlir`

### expectation 合同验收（架构预置后）

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.loop_soft_pipeline
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.producer_consumer_analysis
```

### repo conformance / KCE gate

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/repo_conformance/test_private_api_boundaries.py \
  test/tools/test_kernel_code_error_static_gate.py
```

## 架构前置项与计划内小任务卡

### E0 架构侧 expectation 预置（非 execute）

- 为什么做：先把用户确认的合同资产锁住，避免执行人实现后反推预期。
- 做什么：只在 Q5 授权 scope 内新增 / 更新 `loop_soft_pipeline` 与 `producer_consumer_analysis` expectation leaf。
- 不做什么：不修改 pipeline expectation，不修改 `spec`、实现、测试，不创建 execute 任务。
- 怎么验收：记录授权来源、manifest / hash、scope 外空 diff；在旧实现上 expectation 预期失败，失败点必须落在缺少 pass、缺少 attr 或缺少 ring-aware 分析。
- 合同验收：`python3 -m expectation.pass.loop_soft_pipeline` 与 `python3 -m expectation.pass.producer_consumer_analysis` 在旧实现上作为 red contract 记录失败；实现完成后必须通过。
- 卡住问谁：expectation scope、预期 IR 或合同目标争议问用户；权限和流程问管理员。

模块范围：

- 允许：`expectation/pass/loop_soft_pipeline/**`、`expectation/pass/producer_consumer_analysis/**`。
- 禁止：`expectation/pass/pipeline/npu_demo_lowering.py`、其它 `expectation/` 路径、`.skills/`、`agents/standard/`、计划外实现文件。
- 合同真源：用户 Q1-Q6 决策 > 本计划 > 参考 IR 文档 > 当前实现。
- 最小闭环：新增 leaf 能在旧实现上失败，并能精确说明目标 IR / attr。
- 记录要求：用户确认来源、授权 scope、manifest / hash、scope 外空 diff、运行入口、expected / actual。

执行步骤：

1. 记录授权前 manifest / hash 与 `git status --short --ignored`。
2. 新增 `expectation/pass/loop_soft_pipeline/**` red contract。
3. 新增 `expectation/pass/producer_consumer_analysis/**` ring-aware red contract。
4. 运行两个 expectation 入口并记录旧实现失败。
5. 记录 scope 外空 diff。

### S0 用户决策与 expectation 授权

- 为什么做：本计划涉及公开 API、公开 attr、pipeline 顺序和 `expectation` 合同资产。
- 做什么：记录 Q1-Q6 用户确认项，作为 strict review 和 execute 输入。
- 不做什么：不写实现、不写 expectation、不下发 execute。
- 怎么验收：Q1-Q6 均有用户确认来源；本草稿被标记为 ignored/untracked，正式候选迁移方式已写清。
- 合同验收：不适用，本卡只记录决策。
- 卡住问谁：公开 API、attr、expectation scope 卡住时问用户。

模块范围：计划书文本与任务记录引用。

禁止修改面：`expectation/`、`spec/`、实现、测试、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

合同真源：用户当前会话确认 > `AGENTS.md` > `agents/standard/计划书标准.md` > 本计划草稿。

最小闭环：Q1-Q6、ignored 草稿风险、下一步 strict review 状态均可追溯。

记录要求：写入 `迭代审阅记录` 与后续任务记录的“用户确认来源”。

执行步骤：

1. 记录 Q1-Q6 的用户确认来源。
2. 基于确认项修订计划草稿。

### S1 `spec` 与公开 API 收口

- 为什么做：execute 必须先有公开合同，不能实现后反推。
- 做什么：新增 / 更新 pass、analysis、pipeline、registry spec。
- 不做什么：不修改 expectation。
- 怎么验收：spec 文件 API 列表、option/no-op 语义、pipeline 顺序一致；不得包含 package re-export 或 `LoopSoftPipelinePassError`。
- 合同验收：不直接运行 expectation；只确保架构预置的 expectation 可作为后续合同验收入口。
- 卡住问谁：公开 API 或错误语义不确定时问用户。

模块范围：`spec/pass/loop_soft_pipeline.md`、`spec/pass/producer_consumer_analysis.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/registry.md`。

禁止修改面：`expectation/`、实现、测试、计划书、标准文档、`.skills/`。

合同真源：用户 Q1-Q6 > 本计划 > 现有 pass/registry spec。

最小闭环：公开 API、公开 attr、pipeline 顺序、unsupported no-op、`N == 0` / `N == 1` 边界全部写入 spec。

记录要求：任务记录写清公开 API 变更、未新增 package re-export、未新增稳定错误文本。

执行步骤：

1. 新增 `spec/pass/loop_soft_pipeline.md`。
2. 更新 `spec/pass/producer_consumer_analysis.md`。
3. 更新 `spec/pass/pipeline/npu_demo_lowering.md`。
4. 更新 `spec/pass/registry.md`。

### S2 实现 `LoopSoftPipelinePass`

- 为什么做：生成 prologue / steady / epilogue 的最终 IR。
- 做什么：实现 pass、registry、candidate matcher、rewrite 和旧 event attr 清理。
- 不做什么：不依赖 producer-consumer 旧结果，不处理 async/wait。
- 怎么验收：新增 pytest 通过；架构预置的 `expectation.pass.loop_soft_pipeline` 在实现完成后通过。
- 合同验收：`python3 -m expectation.pass.loop_soft_pipeline` 单列记录，不计入 diff 反推测试。
- 卡住问谁：rewrite 边界或动态 loop 边界问架构师 / 用户。

模块范围：`kernel_gen/passes/schedule/loop_soft_pipeline.py`、pass registry 必要接入文件、对应文件级 API 列表。

禁止修改面：`expectation/`、`spec/`、pipeline expectation、package re-export、`.skills/`、标准文档、无关 pass。

合同真源：`spec/pass/loop_soft_pipeline.md` > 架构预置 expectation > pytest > 当前实现。

最小闭环：dynamic/dynamic A/B 链 rewrite 可用；不安全形态 no-op；`N == 0` 不生成无保护 prologue；`N == 1` 可退化；旧 event attr 不继承。

记录要求：写清 diff 反推 pytest、no-op case、清理旧 attr 核对、未跨文件调用非公开 helper。

执行步骤：

1. 实现 pass class、from_options、apply。
2. 实现 ring cursor / candidate matcher。
3. 实现 matmul A/B 输入链 soft pipeline rewrite。
4. 处理 `N == 0`、`N == 1` 或不能证明 steady range 时的 no-op / fallback 策略。
5. 清理旧 event attrs。
6. 注册 pass 并补文件级 API 列表。

### S3 扩展 `ProducerConsumerAnalysisPass`

- 为什么做：最终 IR 必须重新分析出 loop-first / loop-carried / epilogue 消费关系。
- 做什么：接入 ring-aware cursor trace 与新 attr。
- 不做什么：不生成同步 op，不把 advance 当作读写。
- 怎么验收：producer-consumer pytest 通过；架构预置的 `expectation.pass.producer_consumer_analysis` 在实现完成后通过。
- 合同验收：`python3 -m expectation.pass.producer_consumer_analysis` 单列记录，不计入 diff 反推测试。
- 卡住问谁：新 attr 分类有歧义时问用户。

模块范围：`kernel_gen/passes/producer_consumer_analysis.py`、对应 spec 和测试引用。

禁止修改面：`expectation/`、loop soft pipeline 实现外的无关 pass、`.skills/`、标准文档。

合同真源：`spec/pass/producer_consumer_analysis.md` > 架构预置 expectation > pytest > 当前实现。

最小闭环：在 soft-pipeline 后 IR 上为 TLM A/B 建出 `loop_first_*`、`loop_carried_*`、`after_loop_*`；`advance_ring` 只影响 cursor，不作为读写；既有普通、if、loop_body、after_loop 行为不回归。

记录要求：写清 event attr 清理、新 attr 写回、ring current / advance 样例、旧测试回归结果。

执行步骤：

1. 扩展 event attr 清理列表。
2. 建 ring cursor facts。
3. 基于 slot identity 连 `WRITE -> READ`。
4. 增加 `loop_first` / `loop_carried` 分类。
5. 保持既有普通、if、loop_body、after_loop 行为不回归。

### S4 pipeline 集成

- 为什么做：默认 lowering 必须在 producer-consumer 之前看到 soft-pipeline 后 IR。
- 做什么：把新 pass 插入 `npu-demo-lowering`。
- 不做什么：不新增 pipeline option。
- 怎么验收：pipeline pass order pytest 与 matmul dynamic/dynamic dump 通过；不得要求 `expectation/pass/pipeline/npu_demo_lowering.py` 通过。
- 合同验收：本卡无 pipeline expectation 合同验收；pipeline 顺序只用 spec、pytest、dump 验收。
- 卡住问谁：pipeline 顺序与其它计划冲突时问架构师 / 管理员。

模块范围：`kernel_gen/pipeline/npu_demo_lowering.py`、pipeline spec、pipeline pytest。

禁止修改面：`expectation/pass/pipeline/npu_demo_lowering.py`、其它 `expectation/` 路径、pipeline option、无关 lowering。

合同真源：`spec/pass/pipeline/npu_demo_lowering.md` > pipeline pytest > dump 文件。

最小闭环：默认顺序为 `MultiBufferPass -> LoopSoftPipelinePass -> ProducerConsumerAnalysisPass -> MemoryPoolPass`；dump 阶段名变为 `25-loop-soft-pipeline.mlir`、`26-producer-consumer-analysis.mlir`。

记录要求：任务记录写清未修改 pipeline expectation、dump 文件核对点和相关冲突依赖。

执行步骤：

1. 更新 `kernel_gen/pipeline/npu_demo_lowering.py`。
2. 更新 pipeline spec。
3. 更新 pipeline pytest marker index。
4. 运行 matmul dynamic/dynamic demo，核对 dump。

### S5 总体验收与记录

- 为什么做：防止只过局部测试但破坏 pipeline 或 repo gate。
- 做什么：运行计划列出的 pytest、expectation、demo、repo conformance / KCE。
- 不做什么：不把 expectation 当 diff 反推测试混写。
- 怎么验收：所有命令通过，任务记录写清 diff 反推测试与合同验收。
- 合同验收：只运行本计划列出的 `expectation.pass.loop_soft_pipeline` 与 `expectation.pass.producer_consumer_analysis`；不运行 pipeline expectation。
- 卡住问谁：环境问题问管理员；合同争议问用户 / 架构师。

模块范围：任务涉及的 spec、实现、测试、dump、任务记录。

禁止修改面：`expectation/` 本体、计划书、标准文档、`.skills/`、无关主线文件。

合同真源：计划正文验收命令 > spec > pytest > 当前实现。

最小闭环：pytest、demo dump、两个当前必过 expectation、repo conformance / KCE 均有结果；失败时给出 actual / expected / verdict。

记录要求：按 `Diff 反推测试` 单列 pytest / script；按 `合同验收` 单列 expectation；记录 `git status --short` 与禁止修改面检查。

## 已确认与待确认项

当前无新增待用户确认项。Draft 0 中超出确认范围的 package re-export、`LoopSoftPipelinePassError` 和 unsupported 稳定错误均已移出本轮目标；如后续实现认为必须新增，必须暂停并回到用户确认。

### Q1 pass 公开 API（已确认）

- 选项 A：`LoopSoftPipelinePass`，registry `loop-soft-pipeline`，module `kernel_gen.passes.schedule.loop_soft_pipeline`。
- 选项 B：`LoopSoftPipelinePass`，registry `loop-soft-pipeline`，module `kernel_gen.passes.loop_soft_pipeline`。
- 用户决策：采用 A。
- 非本轮目标：不新增 `kernel_gen.passes.schedule.LoopSoftPipelinePass` 或 `kernel_gen.passes.LoopSoftPipelinePass` package re-export。

### Q2 是否新增共享 ring cursor analysis 公开 API（已确认）

- 选项 A：新增 `kernel_gen.passes.analysis.ring_cursor_analysis` 公开支持 API。
- 选项 B：不新增共享 API，在两个 pass 文件内分别实现 ring cursor 逻辑。
- 用户决策：采用 B。第一版两个 pass 独立实现；后续如需抽公共能力再单独确认公开 API。

### Q3 新 event attr 名称（已确认）

- 选项 A：使用 `loop_first_productor/consumer` 与 `loop_carried_productor/consumer`。
- 选项 B：只复用现有 `loop_body_*` / `after_loop_*`，不新增 attr。
- 用户决策：采用 A。

### Q4 `N == 1` 分类（已确认）

这里的 `N` 是 K 维 tile 数量：

```text
N = ceil_div(K, TILE_K)
```

`N == 1` 表示整个 K 维正好有一个 tile，例如 `0 < K <= TILE_K`。这种情况下没有“上一轮 preload 供下一轮 matmul”的 steady loop-carried 边，soft pipeline 退化为：

```text
prologue:
  preload k0

steady loop:
  空

epilogue:
  compute k0
```

因此消费边是：

```text
prologue copy(k0) -> epilogue matmul(k0)
```

- 选项 A：`prologue copy -> epilogue matmul` 用普通 `productor/consumer`。
- 选项 B：新增 `prologue_epilogue_productor/consumer`。
- 用户决策：采用 A。原因是第一版减少公开 attr 面；slot 证明不受影响。

### Q4b `N == 0` / zero-trip 边界（Draft 1 收口）

`N == 0` 表示 K 维没有任何 tile，不能无条件生成 prologue copy。第一版保守处理：

- 能证明 `N > 0` 或能用现有 IR 构造保持语义的 guard 时，才允许 rewrite。
- 不能证明时 no-op / 保持现状。
- 不新增稳定错误，不新增 `zero_trip_*` attr。

### Q5 expectation 授权范围（已确认）

- 选项 A：授权新增 / 修改 `expectation/pass/loop_soft_pipeline/**`、`expectation/pass/producer_consumer_analysis/**`。
- 选项 B：先只写 pytest，不动 expectation。
- 明确不纳入本轮修改：`expectation/pass/pipeline/npu_demo_lowering.py`。
- 用户决策：采用 A，但排除 pipeline expectation。

### Q6 首版场景范围（已确认）

- 选项 A：首版只锁 matmul dynamic/dynamic A/B 输入链，其他形态 no-op 或保持现状。
- 选项 B：首版同时覆盖 matmul static/static、static/dynamic、dynamic/dynamic。
- 用户决策：采用 A。

## 迭代审阅记录

### R1 Draft 0 strict review

- 标准包：根 `AGENTS.md`、当前架构师会话口径、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/角色权限矩阵.md`、`agents/standard/审查规范.md`、Draft 0 全文、Q1-Q6 用户确认项、禁止修改面、必过 pytest / expectation / dump 命令。
- 严格通过口径：无阻断项、无最小需改项、无待用户确认项；公开 API 与稳定错误语义全部有用户确认；`expectation` 权限合法；小任务卡具备模块范围、禁止修改面、合同真源、最小闭环、验收与记录要求；验收命令把 diff 反推测试和合同验收分开。
- 审阅任务：
  - Galileo：结论不通过。阻断项为 pipeline expectation 与 Q5 冲突、小任务卡缺标准字段、unsupported 稳定错误与 Q6 冲突；最小需改为补迭代审阅记录、明确 marker 不是 IR attr、移除未确认措辞；待确认为 package re-export、`LoopSoftPipelinePassError`、zero-trip 处理。
  - Noether：结论不通过。阻断项为 pipeline expectation 与 Q5 冲突、execute 小任务包含 expectation 本体修改、package re-export 与稳定错误文本超出确认、计划文件 ignored/untracked 风险未写明；最小需改为补迭代审阅记录、小任务卡标准字段、unsupported no-op 收口。
- Draft 1 主线处理：
  - 删除 pipeline expectation 修改与验收要求。
  - 将 `expectation` 本体改动移到 E0 架构侧预置，明确非 execute。
  - 移除 package re-export、`LoopSoftPipelinePassError` 和 unsupported 稳定错误。
  - 明确 `loop-soft-pipeline` marker 只是 dump 文件名或测试 marker，不是 IR attr。
  - 增加 ignored/untracked 草稿风险和正式候选迁移方式。
  - 补齐 E0 / S0-S5 的模块范围、禁止修改面、合同真源、最小闭环、验收和记录要求。
  - 增加 `N == 0` / zero-trip no-op 边界。
- 状态：R1 不通过，Draft 1 已修订；必须发起 R2 strict review，R2 无阻断、无最小需改项、无待确认项后才可进入守护最终检验。

### R2 Draft 1 strict review

- 标准包：沿用 R1 标准包，审阅对象改为 Draft 1 全文与 R1 主线处理结果。
- 严格通过口径：R1 阻断项必须完全收口；无新增阻断项、无最小需改项、无待用户确认项；尤其检查 `expectation` 权限、pipeline expectation 排除、未确认公开 API / 稳定错误文本、zero-trip 与 `N == 1` 边界、小任务卡完整性。
- 审阅任务：
  - Noether：结论通过；无阻断、无最小需改、无待确认。残余风险为仍需记录 R2 收敛并跑守护最终检验，且计划文件仍是 ignored/untracked 草稿但已写明迁移路径。
  - Galileo：结论不通过；无阻断、无待确认；1 个最小需改项为 `N == 1` 示例写成 `K <= TILE_K`，包含 `K == 0`，与 zero-trip no-op 规则冲突。
- Draft 2 主线处理：
  - 将 `N == 1` 的示例修为 `0 < K <= TILE_K`。
  - 将 Q4 摘要改为 `N == 1` 且 K 维正数。
- 状态：R2 未收敛，Draft 2 已修订；必须发起 R3 strict review，R3 无阻断、无最小需改项、无待确认项后才可进入守护最终检验。

### R3 Draft 2 strict review

- 标准包：沿用 R2 标准包，审阅对象改为 Draft 2 全文与 R2 最小需改项处理结果。
- 严格通过口径：R2 `N == 1` / zero-trip 冲突必须收口；无新增阻断项、无最小需改项、无待用户确认项。
- 审阅任务：
  - Galileo：结论通过；无阻断、无最小需改、无待确认。确认 Q4 摘要已写明 K 维正数，详细示例为 `0 < K <= TILE_K`。
  - Noether：结论通过；无阻断、无最小需改、无待确认。确认 pipeline expectation 排除、expectation ownership、unsupported no-op 行为和 guard-final gating 仍保持。
- 残余风险：
  - 守护最终检验尚未执行。
  - 计划文件路径仍受 `.gitignore` 影响，正式候选必须记录强制跟踪或迁移证据。
  - `multi_buffer_analysis_apply_split` 相关计划协调仍是 execute 前风险，不是用户待确认项。
- 状态：R3 已收敛；可以进入守护最终检验。

### 守护最终检验

- 状态：G1 不通过；G2 正式候选迁移已执行。后续管理员已创建唯一计划级 execute 任务 `T-20260613-bac54fd8`，任务链已完成 `execute -> review -> archive_acceptance`，当前待 `merge/归档`。
- 前置条件：已满足，R3 strict review 已收敛到无阻断、无最小需改项、无待确认项。
- 检验范围：标准包、公开 API、`expectation` 权限、禁止修改面、验收命令、小任务卡、ignored/untracked 草稿风险和正式候选迁移记录。
- 通过后动作：管理员才允许创建唯一计划级 `execute`；未通过则回到计划修订与下一轮 strict review。

#### G1 结果

- 守护人：`守护最好的爱莉希雅`。
- 结论：不通过。
- 阻断项：正式候选门禁未满足；本计划文件仍是 ignored/untracked 草稿，`git ls-files --stage` 无输出，`git diff --cached --name-status` 无输出。
- 内容核对：无新增内容返工项；Q1-Q6、公开 API、`expectation` 权限、pipeline expectation 排除、unsupported / zero-trip no-op、S1-S5 验收拆分和 R3 收敛记录均通过核对。
- 最小需改项：完成正式候选跟踪或迁移记录后重新请求守护最终检验。

#### G2 正式候选迁移

- 动作：按 G1 要求执行 `git add -f ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md`，并将计划引用的 `ARCHITECTURE/reference/matmul_pingpong_producer_consumer_ir.md` 作为同一架构文档候选纳入 index。
- 候选范围：仅本计划文本与引用参考说明文档；不包含 `expectation/`、`spec/`、实现、测试、pipeline expectation、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 或 `agents-lists.md`。
- 证据要求：重新请求守护时必须携带 `git ls-files --stage`、`git diff --cached --name-status`、`git status --short --ignored --untracked-files=all`、blob / sha256、`git diff --cached --check` 与敏感范围空 diff。
- 当前状态：正式候选已进入任务链并完成入档验收；后续执行后验收结论见下方“计划书入档验收”。

## 计划书入档验收（2026-06-13）

- 结论人：`提莫炖蘑菇`。
- 结论：通过；当前可按计划级链路续接 `merge/归档`，但 `archive_acceptance` 本身不执行 merge、提交、推送或清理。
- 验证基线：执行目录 `/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer`；已执行 `git fetch origin main --prune`；`HEAD=d679cdcbda147d18effa4121cf460df4d05e33f8`，`origin/main=d679cdcbda147d18effa4121cf460df4d05e33f8`，`merge-base=d679cdcbda147d18effa4121cf460df4d05e33f8`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 计划回写：本节已将计划状态、目标 `spec`、目标测试、任务 worktree 与下发后状态更新为已落地 / 已验收；未修改 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md` 或 `agents-lists.md`。
- Q4 / Q4b 收口：复审确认 single-tile 正 trip 退化为 `prologue copy -> epilogue matmul`，producer-consumer 只使用普通 `productor` / `consumer`，不产生 `loop_first` / `loop_carried` / `after_loop`；动态无法证明至少一个 tile 时保持 no-op / guard 口径，不生成无条件 prologue。
- Diff 反推测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py test/passes/test_producer_consumer_analysis.py test/passes/test_registry.py` 通过，`84 passed, 1 warning`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` 通过，`11 passed, 1 warning`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py` 通过，`7 passed`。
- 动态脚本验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py` 退出码 0，stdout 包含 `multi_tile=True tail=True`，并输出 `absent_bias max_abs_diff=2.86102294921875e-05`、`present_bias max_abs_diff=2.86102294921875e-05`。
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.loop_soft_pipeline` 退出码 0；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260613-loop-soft-pipeline-ring-aware-producer-consumer:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis` 退出码 0，并输出 10 条 after_if / after_loop / if_branch / loop_body / memory_effect_alias 正例。
- local-only / 只读资产：`expectation/pass/loop_soft_pipeline`、`expectation/pass/producer_consumer_analysis`、`expectation/pass/pipeline/npu_demo_lowering.py` 未进入 staged / unstaged diff；`kernel/dump/matmul/inputs_dynamic_tile_dynamic/**` 仅为 ignored local-only dump。
- 敏感范围：`git diff --check && git diff --cached --check` 通过；`git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` 与对应 cached diff 均无输出。
- latest main 交叉风险：当前 `HEAD`、`origin/main` 与 `merge-base` 一致，无 ahead / behind；计划候选未与最新 main 分叉。
- 可归档性：任务记录已包含 execute、返工 execute、review 复审通过、review -> archive_acceptance 标准流转记录；本次入档验收通过后按标准脚本续接 `merge`，由 merge 角色在合并前复核 staged/cached 范围、验证摘要、敏感范围和记录同批合入。

## 用户确认与协同约束

- 本计划已完成 R1 / R2 / R3 strict review、G1 / G2 正式候选迁移、计划级 execute、review 与 archive_acceptance 入档验收。
- 下一步为 `merge/归档`，不得由 archive_acceptance 角色直接执行 merge、提交、推送或清理。
- 若 merge 前发现 latest main 分叉、敏感范围污染、expectation 本体 diff 或任务记录缺口，必须暂停并按同一任务链回到对应责任阶段收口。
- 任何公开 API、稳定错误语义、pipeline 顺序或 `expectation` 授权范围变化，都必须回到用户确认。
