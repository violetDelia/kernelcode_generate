# producer_consumer_analysis pass

## 功能简介

- `ProducerConsumerAnalysisPass` 是独立公开 `ModulePass`，registry 名称固定为 `producer-consumer-analysis`。
- pass 基于 xDSL 公开 `MemoryEffect` 读取 memory `ALLOC/WRITE/READ/FREE` 语义，并用当前 pass 内置 alias / ring cursor / init-only ring alias 规则标注普通、控制流分类或 ring-aware event 简单整数列表属性。
- pass 只做 IR 分析标注，不生成 `arch.wait`、`arch.sign`、runtime event、double buffer overlap、ring buffer 或 core 分配逻辑。

## API 列表

- `class ProducerConsumerAnalysisPass(fold: bool = True)`
- `ProducerConsumerAnalysisPass.from_options(options: dict[str, str]) -> ProducerConsumerAnalysisPass`
- `ProducerConsumerAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
- registry pass name：`producer-consumer-analysis`

## 文档信息

- `spec`：`spec/pass/producer_consumer_analysis.md`
- `功能实现`：`kernel_gen/passes/producer_consumer_analysis.py`
- `test`：`test/passes/test_producer_consumer_analysis.py`
- `expectation`：主仓本地 ignored / untracked 只读合同来源 `expectation/pass/producer_consumer_analysis/**`

## 依赖

- `xdsl.traits.get_effects(op)`：读取公开 `MemoryEffect`。
- `spec/dialect/dma.md`：定义 `dma.alloc/free/copy/load/store/slice/deslice/view/reshape/subview/reinterpret` 等 op 的公开 effect 与 alias 语义。
- `spec/dialect/kernel.md`：定义 kernel op 对 out/input memory 的公开 read/write effect。
- `spec/pass/registry.md`：承载 registry 名称和 `fold` 通用 option。
- `spec/pass/loop_soft_pipeline.md`：定义 ring-backed soft-pipeline 改写输出结构。
- `spec/pass/pipeline/npu_demo_lowering.md`：承载默认 pipeline 接入位置。

## 目标

- 为后续同步 / pipeline 编排提供稳定的生产消费 event 标注资产。
- 将 `productor` / `consumer` 标注从专题脚本迁移为当前仓库通用 pass。
- 让同一个 producer value 到 downstream meaningful consumers 的关系可以通过 IR attr 直接检查。
- 让 `loop-soft-pipeline` 生成的多 tile ring-backed current/advance steady 结构可以用 `loop_first` / `loop_carried` / `after_loop` attr 直接表达跨迭代生产消费关系。
- 让 `dma.alloc` 与 `dma.make_ring` 的初始化同步只连接第一组真实 READ / WRITE first-touch，不污染后续普通 data event。

## 额外补充

### 模块级补充

- 当前文件只公开 `ProducerConsumerAnalysisPass` 与 registry pass name，不公开 alias table、event allocator、event list attr 或内部 helper。
- 当前实现允许在 `kernel_gen/passes/producer_consumer_analysis.py` 当前文件内定义私有 event list attr，用于打印裸 `[0]` / `[0, 1]` 文本；该 attr 不得作为公开 dialect attribute 注册。
- 不做包根 `kernel_gen.passes.ProducerConsumerAnalysisPass` re-export；如需包根公开入口，必须另行用户确认。
- pass rerun 前必须校验并清理旧 `productor` / `consumer`、控制流分类 attr 与 ring-aware 分类 attr；合法旧形态包括本 pass 私有 attr 和 parser 读回的整数 `ArrayAttr`，非法或负数 event id 必须失败。
- `FREE` 第一阶段不参与标注。
- 没有 downstream meaningful consumer 的 producer 不写 `productor`。
- 找不到 producer 的 consumer 不写 `consumer`，也不创建虚拟 producer。
- `ALLOC` init candidate 与 `dma.make_ring` init candidate 使用 first-touch 语义：只选同一 init root 按 op 顺序的第一组真实 READ 或 WRITE touch 写 `consumer`；若第一组是 `scf.if` then/else 互斥分支的同序 touch，复用既有 `if_branch_*` 共享 event 规则。
- 普通 `WRITE` candidate 保持 dataflow 语义，只连接 downstream meaningful `READ` consumer，不把后续 WRITE 当作 consumer。

### Event Attr 合同

- 主 attr：
  - `productor = [id...]`：当前 op 生产 memory 后，为每条 downstream meaningful consumer edge 分配的 event id 列表。
  - `consumer = [id...]`：当前 op 读取已生产 memory 时消费的 event id 列表。
- 控制流分类 attr：
  - `if_branch_productor` / `if_branch_consumer`
  - `after_if_productor` / `after_if_consumer`
  - `loop_body_productor` / `loop_body_consumer`
  - `after_loop_productor` / `after_loop_consumer`
- ring-aware 分类 attr：
  - `loop_first_productor` / `loop_first_consumer`：loop 前 preload 写入 ring current slot，并被 steady loop 第一次 matmul 读取。
  - `loop_carried_productor` / `loop_carried_consumer`：loop body 中 `dma.advance_ring` 后的 preload 写入下一 ring current slot，并被后续迭代读取。
- 同一 producer -> consumer edge 只能写一种 event 对：普通 edge 写 `productor` / `consumer`，控制流或 ring-aware edge 写对应分类 attr，且不得同时叠写主 `productor` / `consumer`。
- event id 在每个 `func.func` 内从 `0` 开始，按 pass 遍历顺序递增。
- 文本必须为简单整数列表，例如 `productor = [0]`、`consumer = [0, 1]`。
- 不得输出 `#builtin.int<...>`、`[0 : i64]` 或 `array<i64: ...>` 作为本 pass 公开 event attr 文本。

### Effect 与 Alias

| effect / op | 合同 |
| --- | --- |
| `ALLOC(value)` | `value` 是 init producer value 候选；只有存在第一组真实 READ 或 WRITE first-touch 时才写 `productor`，后续 touch 不再消费该 init event。 |
| `WRITE(value)` | `value` 是 producer value 候选；每条 downstream meaningful `READ` edge 分配 event。 |
| `READ(value)` | 只有被某个 producer value 的 downstream traversal 命中时才写 `consumer`。 |
| `FREE(value)` | 第一阶段不标注。 |
| `dma.make_ring(memory, num, offset) -> ring` | 当 ring slot 后续存在第一条真实 READ 或 WRITE touch 时，`dma.make_ring` 是 ring init producer；backing `dma.alloc` 在该 ring 路径不写 event attr。 |
| `dma.view(source) -> result` | `result` alias `source`；不生产、不消费。 |
| `dma.reshape(source) -> result` | `result` alias `source`；不生产、不消费。 |
| `dma.subview(source) -> result` | `result` alias `source`；不生产、不消费。 |
| `dma.reinterpret(source) -> result` | `result` alias `source`；不生产、不消费。 |
| `dma.deslice(target, source, ...)` | 通过 effect 消费 `source`、生产 `target`；op 本身不产生 result。 |
| `dma.current_ring(ring) -> result` | `result` 是 ring cursor slot root；在 init-only alias 表中归属 `dma.make_ring`，op 本身不写 producer/consumer attr。 |
| `dma.advance_ring(ring)` | cursor advance boundary；其 result 在 init-only alias 表中归属 `dma.make_ring`，op 本身不写 producer/consumer attr。 |

### ALLOC 与 make_ring init first-touch 合同

- `dma.alloc` 直接被使用时，alloc op 只为同一 alias root 的第一组真实 READ 或 WRITE touch 分配 init event；普通顺序路径第一组只有一个 op，`scf.if` then/else 互斥分支同序 first-touch 可以共享同一个 `if_branch` event。
- 如果第一条 touch 是 WRITE，例如 `dma.slice(target=%alloc, source=...)`，该 WRITE op 同时写 `consumer=[alloc_init_event]` 与后续普通 data `productor=[data_event]`。
- 后续读取同一 root 的 op 只消费普通 WRITE data event，不再消费 alloc init event。
- `dma.view`、`dma.reshape`、`dma.subview`、`dma.reinterpret`、`dma.current_ring`、`dma.advance_ring` 等 alias-only / cursor-only op 不算真实 first touch，且自身不写 init event attr。
- `dma.alloc -> dma.make_ring` 场景中，backing `dma.alloc` 不写 `productor` / `consumer`；`dma.make_ring` 写 init `productor`，通过 init-only alias 表连接 ring slot 的第一条真实 READ 或 WRITE touch。
- `dma.current_ring` / `dma.advance_ring` result 及其 `dma.reinterpret` alias 链只在 init-only 表中回到 `dma.make_ring` root；普通 alias_roots 与 ring-aware current/advance dataflow 不因此改变。
- init first-touch 只复用现有 `productor` / `consumer`、`if_branch_*`、`after_if_*`、`loop_body_*`、`after_loop_*` 等 event attr，不新增公开 attr。

### Ring-aware current/advance 合同

- ring-aware 分析只补充 `symbol.for` 直接 body 周围可证明的 ring cursor 关系。
- `dma.current_ring` result 及其 `dma.reinterpret` alias 链归属同一个 ring root。
- 对同一 ring：
  - loop 前最后一个 `WRITE` 与 loop body 首个 `dma.advance_ring` 前的首个 `READ` 形成 `loop_first_productor` / `loop_first_consumer`。
  - loop body 首个 `dma.advance_ring` 后的首个 `WRITE` 与该 advance 前的首个 `READ` 形成 `loop_carried_productor` / `loop_carried_consumer`。
  - loop body 首个 `dma.advance_ring` 后的首个 `WRITE` 与 loop 后首个 `READ` 形成 `after_loop_productor` / `after_loop_consumer`。
- `loop-soft-pipeline` 的 static single-tile 退化结果没有 steady `symbol.for`，仅有 prologue preload 与 epilogue matmul；该形态使用普通 `productor` / `consumer`，不得生成 `loop_first` / `loop_carried` / `after_loop` attr。
- `dma.advance_ring` 只提供 cursor boundary，不参与 `MemoryEffect` 生产消费标注，输出不得在该 op 上携带 `productor` / `consumer` 或分类 attr。
- ring-aware event id 继续使用同一 `func.func` 内的全局递增 event id 序列，不单独重置。

## API详细说明

### `class ProducerConsumerAnalysisPass(fold: bool = True)`

- api：`class ProducerConsumerAnalysisPass(fold: bool = True)`
- 参数：
  - `fold`：通用 pass 后 folding 开关；类型 `bool`；默认值 `True`。
- 返回值：`ProducerConsumerAnalysisPass` 实例。
- 功能说明：构造生产消费分析 pass。
- 使用示例：

```python
from kernel_gen.passes.producer_consumer_analysis import ProducerConsumerAnalysisPass

pass_obj = ProducerConsumerAnalysisPass(fold=False)
```

- 注意事项：
  - 不接受 attr name、alias table 或 control-flow 策略构造参数。
  - 当前文件之外不得调用本 pass 的内部 alias helper 或 event allocator helper。

### `ProducerConsumerAnalysisPass.from_options(options: dict[str, str]) -> ProducerConsumerAnalysisPass`

- api：`ProducerConsumerAnalysisPass.from_options(options: dict[str, str]) -> ProducerConsumerAnalysisPass`
- 参数：
  - `options`：pass 专属 options；类型 `dict[str, str]`；第一阶段只接受空字典。
- 返回值：`ProducerConsumerAnalysisPass` 实例。
- 功能说明：为 registry 构造入口提供 pass 专属 option 解析。
- 使用示例：

```python
pass_obj = ProducerConsumerAnalysisPass.from_options({})
```

- 注意事项：
  - `fold` 是 registry 通用 option，由 `build_registered_pass(...)` 先拆分并写入 pass 实例。
  - 未知 option 必须以 `KernelCodeError` 失败，错误文本包含 `ProducerConsumerAnalysisPassError: unknown option`。

### `ProducerConsumerAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`ProducerConsumerAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL context；类型 `Context`。
  - `module`：待分析 module；类型 `ModuleOp`。
- 返回值：`None`；原地写回 IR attrs。
- 功能说明：遍历 `builtin.module` 中每个非声明 `func.func`，为受控 memory dataflow 写入 event attrs。
- 使用示例：

```python
ProducerConsumerAnalysisPass().apply(ctx, module)
```

- 注意事项：
  - 必须使用公开 `MemoryEffect` 读取 read/write，不得调用 dma/kernel 跨文件私有 effect helper。
  - 同一路径 fanout 中，同一个 produced memory version 有多个 static user 时，每个 user 分配独立 event。
  - 同一个 consumer op 对同一个 producer group 重复读取只消费一个 event。
- `dma.alloc` init root 与 `dma.make_ring` init root 只连接第一组真实 READ / WRITE first-touch；后续 touch 不重复消费 init event。
  - `dma.alloc -> dma.make_ring` 时，backing alloc 不写 event attr，init producer attr 写在 `dma.make_ring` 上。
  - 普通 `WRITE` candidate 仍只连接 downstream READ consumer；不得把后续 WRITE 当作普通 data consumer。
  - `scf.if` 中 if 前 producer 被 then / else 互斥分支消费时共享同一个 event。
  - `scf.if` 同一分支内部的 producer 到多个 downstream consumer 仍按同一路径 fanout 处理，每个 consumer 分配独立 event。
  - `scf.if` 前 producer 进入同一分支内多个 downstream consumer 时也按同一路径 fanout 处理；只允许 then / else 互斥分支的同序 consumer 共享 event。
  - 写入 `if_branch_*`、`after_if_*`、`loop_body_*`、`loop_first_*`、`loop_carried_*` 或 `after_loop_*` 的 edge 不得同时写主 `productor` / `consumer`。
  - 同一 `scf.if` branch 或同一 `symbol.for` body block 内的普通顺序 edge 仍写主 `productor` / `consumer`，不得误写 `if_branch_*` 或 `loop_body_*`。
  - then / else 都生产同一个 memory value 且 if 后 consumer 使用该 value 时，两个 branch producer 分别获得 event，if 后 consumer 记录两个 event。
  - 普通 `symbol.for` 第一阶段支持 loop 前 producer 到 body consumer、body 内 producer 到 body consumer、body producer 到 loop 后 static consumer 的静态分类；ring-backed current/advance 结构额外支持本文件 `Ring-aware current/advance 合同` 定义的 loop-first、loop-carried 与 after-loop 分类。
  - zero-trip runtime 精确语义不由本 pass 承诺；上游 `loop-soft-pipeline` 对静态 zero-trip 保持 no-op。

## 测试

- 测试文件：`test/passes/test_producer_consumer_analysis.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_producer_consumer_analysis.py`

### 测试目标

- 验证 `MemoryEffect` 正向链路。
- 验证 alias 规则与 `dma.deslice` 读写/alias 组合。
- 验证 fanout、alloc result、alloc first-touch、重复 read 去重。
- 验证 `dma.make_ring` init producer、ring slot first-touch 和 init-only alias 不污染普通 ring data edge。
- 验证 `scf.if` 与 `symbol.for` 控制流分类 attr。
- 验证 ring-backed soft-pipeline 的 `loop_first` / `loop_carried` / `after_loop` 分类 attr。
- 验证 single-tile prologue/epilogue 退化形态只写普通 `productor` / `consumer`。
- 验证 registry 名称、`fold` 通用 option 和未知 option 失败。
- 验证 attr 文本为简单整数列表。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PRODUCER-CONSUMER-001 | MemoryEffect | `dma.copy -> dma.copy` | 准备合法 `!nn.memory` IR。 | 运行 pass。 | producer 写 `productor=[0]`，consumer 写 `consumer=[0]`。 | `test_producer_consumer_analysis_basic_memory_effect_chain` |
| TC-PRODUCER-CONSUMER-002 | alias | `copy -> view/reinterpret -> matmul -> deslice -> copy` | 准备 `dma.view`、`dma.reinterpret` 与 `dma.deslice` 链。 | 运行 pass。 | view/reinterpret 不标注，deslice 同时 consumer/productor，后续 target 读取消费 deslice 生产事件。 | `test_producer_consumer_analysis_alias_and_deslice_chain` |
| TC-PRODUCER-CONSUMER-003 | fanout | 同一 producer 有两个 user | 准备同一路径 fanout IR。 | 运行 pass。 | producer 标多个 event，consumer 分别消费。 | `test_producer_consumer_analysis_fanout_alloc_and_duplicate_read` |
| TC-PRODUCER-CONSUMER-004 | control-flow | `scf.if` incoming 与 after-if edge | 准备 then/else 与 if 后 consumer IR。 | 运行 pass。 | 控制流 edge 只写 `if_branch_*` / `after_if_*` 分类 attr，不叠写主 attr。 | `test_producer_consumer_analysis_if_branch_and_after_if_edges` |
| TC-PRODUCER-CONSUMER-005 | control-flow | `scf.if` 同分支内部 fanout | 准备分支内 producer 后接两个 downstream consumer 的 IR。 | 运行 pass。 | 同分支内部普通顺序 edge 写主 attr，producer 标两个 event，两个 consumer 分别消费不同 event，不写 `if_branch_*`。 | `test_producer_consumer_analysis_if_branch_internal_fanout_uses_distinct_events` |
| TC-PRODUCER-CONSUMER-006 | control-flow | if 前 producer 进入同一 `scf.if` 分支 fanout | 准备 if 前 producer 被同一 then 分支两个 downstream consumer 读取的 IR。 | 运行 pass。 | producer 标两个 `if_branch` event，两个同分支 consumer 分别消费不同 event，不叠写主 attr。 | `test_producer_consumer_analysis_if_incoming_same_branch_fanout_uses_distinct_events` |
| TC-PRODUCER-CONSUMER-007 | control-flow | `symbol.for` loop body / after-loop edge | 准备 loop 前、loop body、loop 后 consumer IR。 | 运行 pass。 | 跨入/跨出 loop 的 edge 只写 `loop_body_*` / `after_loop_*`，同一 loop body block 内普通顺序 edge 只写主 attr。 | `test_producer_consumer_analysis_symbol_for_body_and_after_loop_edges` |
| TC-PRODUCER-CONSUMER-008 | 异常 | 非法旧 event attr / 未知 option | 准备负数 attr 或未知 option。 | 运行 pass / from_options。 | `KernelCodeError` 失败。 | `test_producer_consumer_analysis_rejects_invalid_event_attr_and_unknown_option` |
| TC-PRODUCER-CONSUMER-009 | registry | 公开 pass name | 调用 `load_builtin_passes()`。 | `build_registered_pass("producer-consumer-analysis", {"fold": "false"})`。 | 返回 `ProducerConsumerAnalysisPass(fold=False)`。 | `test_producer_consumer_analysis_registry_entry_and_fold_option` |
| TC-PRODUCER-CONSUMER-010 | ring-aware | soft-pipeline current/advance | 准备 loop 前 preload、loop body matmul/advance/preload next、loop 后 epilogue matmul IR。 | 运行 pass。 | prologue copy 标 `loop_first_productor`，loop matmul 标 `loop_first_consumer` 与 `loop_carried_consumer`，body copy 标 `loop_carried_productor` 与 `after_loop_productor`，advance op 不带 event attr。 | `test_producer_consumer_analysis_ring_soft_pipeline_events` |
| TC-PRODUCER-CONSUMER-011 | ring-aware fallback | single-tile prologue/epilogue | 准备无 steady loop 的 prologue copy 与 epilogue matmul IR。 | 运行 pass。 | prologue copy 与 epilogue matmul 使用主 `productor` / `consumer`，不写 `loop_first`、`loop_carried` 或 `after_loop`。 | `test_producer_consumer_analysis_single_tile_prologue_epilogue_uses_main_attrs` |
| TC-PRODUCER-CONSUMER-012 | alloc init | alloc 后首个 WRITE touch | 准备 `dma.alloc -> dma.slice WRITE -> dma.copy READ` IR。 | 运行 pass。 | alloc 写 init `productor`，slice 写 init `consumer` 与普通 data `productor`，copy 只消费 data event。 | `test_producer_consumer_analysis_alloc_first_touch_write_uses_init_event_once` |
| TC-PRODUCER-CONSUMER-013 | alloc init | alloc 后首个 READ touch | 准备 `dma.alloc -> dma.copy READ -> dma.copy READ` IR。 | 运行 pass。 | 只有第一条 copy 消费 alloc init event，第二条 copy 不重复消费 init event。 | `test_producer_consumer_analysis_alloc_first_touch_read_uses_init_event_once` |
| TC-PRODUCER-CONSUMER-014 | alloc init | alias-only op before first touch | 准备 alloc 后接 view/reinterpret，再接真实 WRITE。 | 运行 pass。 | alias-only op 不带 event attr，first WRITE 消费 alloc init event。 | `test_producer_consumer_analysis_alloc_first_touch_ignores_alias_only_ops` |
| TC-PRODUCER-CONSUMER-015 | alloc init | 普通 WRITE 不扩成 WRITE consumer | 准备 alloc first WRITE 后接第二个 WRITE 与 reader。 | 运行 pass。 | 第二个 WRITE 不消费第一个 WRITE 的 data event，reader 消费两个普通 WRITE data events。 | `test_producer_consumer_analysis_alloc_first_touch_write_candidate_still_has_read_only_consumers` |
| TC-PRODUCER-CONSUMER-016 | alloc init + control-flow | alloc first-touch then/else 共享 init event | 准备 `dma.alloc` 后接 `scf.if`，then/else 各有第一条真实 WRITE touch，if 后读取 alloc root。 | 运行 pass。 | alloc 写 `if_branch_productor=[0]`，两个分支 touch 均写 `if_branch_consumer=[0]`，if 后 reader 只消费两个分支 WRITE 的 `after_if` data events。 | `test_producer_consumer_analysis_alloc_first_touch_if_branch_shares_init_event` |
| TC-PRODUCER-CONSUMER-017 | ring init | make_ring 承接 init producer | 准备 `alloc -> make_ring -> current_ring -> reinterpret -> slice WRITE -> matmul READ` IR。 | 运行 pass。 | backing alloc 无 event attr，make_ring 写 init `productor`，slice 消费 init 并生产 data，matmul 只消费 data。 | `test_producer_consumer_analysis_ring_backing_init_alias_first_slot_write_uses_init_event_once` |
| TC-PRODUCER-CONSUMER-018 | ring init | init-only alias 与普通 ring data 隔离 | 准备 ring slot first WRITE 后接 reader。 | 运行 pass。 | reader 不消费 make_ring init event，普通 data edge 仍用主 `productor` / `consumer`。 | `test_producer_consumer_analysis_ring_backing_init_alias_does_not_pollute_ring_data_events` |
| TC-PRODUCER-CONSUMER-019 | ring init | cursor / reinterpret 无 event attr | 准备 advance/current/reinterpret 后 first WRITE。 | 运行 pass。 | advance/current/reinterpret 不写 event attr，first WRITE 消费 make_ring init event。 | `test_producer_consumer_analysis_ring_backing_init_alias_current_advance_reinterpret_have_no_event_attrs` |

## 合同验收

- 主仓本地 ignored / untracked 只读合同来源：`expectation/pass/producer_consumer_analysis/**`。
- execute / review / archive_acceptance / merge / 管理员不得修改、复制、新建、移动、删除、重命名或同步 expectation 文件。
- 当前相关 leaf 至少包括 `alloc_first_touch` 与 `ring_backing_init_alias`；完整 family 还覆盖 `memory_effect_alias`、`if_branch`、`after_if`、`loop_body`、`after_loop`、`ring_loop_first`、`ring_loop_carried`、`ring_after_loop`、`ring_cursor_current_advance`。
- 记录必须写清 expectation import 来源、关键 leaf 名称、manifest / hash、`git check-ignore` 与 `git ls-files --stage` 证据。
- 验收命令：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate \
python3 -m expectation.pass.producer_consumer_analysis
```

- 记录必须写清 `expectation.*` 来自主仓、`kernel_gen.*` 来自任务 worktree。
