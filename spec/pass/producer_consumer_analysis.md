# producer_consumer_analysis pass

## 功能简介

- `ProducerConsumerAnalysisPass` 是独立公开 `ModulePass`，registry 名称固定为 `producer-consumer-analysis`。
- pass 基于 xDSL 公开 `MemoryEffect` 读取 memory `ALLOC/WRITE/READ/FREE` 语义，并用当前 pass 内置 alias 规则标注普通或控制流分类 event 简单整数列表属性。
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
- `expectation`：主仓只读合同资产 `expectation/pass/producer_consumer_analysis/**`

## 依赖

- `xdsl.traits.get_effects(op)`：读取公开 `MemoryEffect`。
- `spec/dialect/dma.md`：定义 `dma.alloc/free/copy/load/store/slice/deslice/view/reshape/subview` 等 op 的公开 effect 与 alias 语义。
- `spec/dialect/kernel.md`：定义 kernel op 对 out/input memory 的公开 read/write effect。
- `spec/pass/registry.md`：承载 registry 名称和 `fold` 通用 option。
- `spec/pass/pipeline/npu_demo_lowering.md`：承载默认 pipeline 接入位置。

## 目标

- 为后续同步 / pipeline 编排提供稳定的生产消费 event 标注资产。
- 将 `productor` / `consumer` 标注从专题脚本迁移为当前仓库通用 pass。
- 让同一个 producer value 到 downstream meaningful consumers 的关系可以通过 IR attr 直接检查。

## 额外补充

### 模块级补充

- 当前文件只公开 `ProducerConsumerAnalysisPass` 与 registry pass name，不公开 alias table、event allocator、event list attr 或内部 helper。
- 当前实现允许在 `kernel_gen/passes/producer_consumer_analysis.py` 当前文件内定义私有 event list attr，用于打印裸 `[0]` / `[0, 1]` 文本；该 attr 不得作为公开 dialect attribute 注册。
- 不做包根 `kernel_gen.passes.ProducerConsumerAnalysisPass` re-export；如需包根公开入口，必须另行用户确认。
- pass rerun 前必须校验并清理旧 `productor` / `consumer` 与控制流分类 attr；合法旧形态包括本 pass 私有 attr 和 parser 读回的整数 `ArrayAttr`，非法或负数 event id 必须失败。
- `FREE` 第一阶段不参与标注。
- 没有 downstream meaningful consumer 的 producer 不写 `productor`。
- 找不到 producer 的 consumer 不写 `consumer`，也不创建虚拟 producer。

### Event Attr 合同

- 主 attr：
  - `productor = [id...]`：当前 op 生产 memory 后，为每条 downstream meaningful consumer edge 分配的 event id 列表。
  - `consumer = [id...]`：当前 op 读取已生产 memory 时消费的 event id 列表。
- 控制流分类 attr：
  - `if_branch_productor` / `if_branch_consumer`
  - `after_if_productor` / `after_if_consumer`
  - `loop_body_productor` / `loop_body_consumer`
  - `after_loop_productor` / `after_loop_consumer`
- 同一 producer -> consumer edge 只能写一种 event 对：普通 edge 写 `productor` / `consumer`，控制流 edge 写对应分类 attr，且不得同时叠写主 `productor` / `consumer`。
- event id 在每个 `func.func` 内从 `0` 开始，按 pass 遍历顺序递增。
- 文本必须为简单整数列表，例如 `productor = [0]`、`consumer = [0, 1]`。
- 不得输出 `#builtin.int<...>`、`[0 : i64]` 或 `array<i64: ...>` 作为本 pass 公开 event attr 文本。

### Effect 与 Alias

| effect / op | 合同 |
| --- | --- |
| `ALLOC(value)` | `value` 是 producer value 候选；只有存在 downstream meaningful consumer 时才写 `productor`。 |
| `WRITE(value)` | `value` 是 producer value 候选；每条 downstream meaningful `READ` edge 分配 event。 |
| `READ(value)` | 只有被某个 producer value 的 downstream traversal 命中时才写 `consumer`。 |
| `FREE(value)` | 第一阶段不标注。 |
| `dma.view(source) -> result` | `result` alias `source`；不生产、不消费。 |
| `dma.reshape(source) -> result` | `result` alias `source`；不生产、不消费。 |
| `dma.subview(source) -> result` | `result` alias `source`；不生产、不消费。 |
| `dma.deslice(target, source, ...) -> result` | 通过 effect 消费 `source`、生产 `target`，且 `result` alias `target`。 |

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
  - `scf.if` 中 if 前 producer 被 then / else 互斥分支消费时共享同一个 event。
  - `scf.if` 同一分支内部的 producer 到多个 downstream consumer 仍按同一路径 fanout 处理，每个 consumer 分配独立 event。
  - `scf.if` 前 producer 进入同一分支内多个 downstream consumer 时也按同一路径 fanout 处理；只允许 then / else 互斥分支的同序 consumer 共享 event。
  - 写入 `if_branch_*`、`after_if_*`、`loop_body_*` 或 `after_loop_*` 的 edge 不得同时写主 `productor` / `consumer`。
  - 同一 `scf.if` branch 或同一 `symbol.for` body block 内的普通顺序 edge 仍写主 `productor` / `consumer`，不得误写 `if_branch_*` 或 `loop_body_*`。
  - then / else 都生产同一个 memory value 且 if 后 consumer 使用该 value 时，两个 branch producer 分别获得 event，if 后 consumer 记录两个 event。
  - `symbol.for` 第一阶段只支持 loop 前 producer 到 body consumer、body 内 producer 到 body consumer、body producer 到 loop 后 static consumer 的静态分类；不承诺 loop-carried、zero-trip 或跨迭代 runtime 精确语义。

## 测试

- 测试文件：`test/passes/test_producer_consumer_analysis.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_producer_consumer_analysis.py`

### 测试目标

- 验证 `MemoryEffect` 正向链路。
- 验证 alias 规则与 `dma.deslice` 读写/alias 组合。
- 验证 fanout、alloc result、重复 read 去重。
- 验证 `scf.if` 与 `symbol.for` 控制流分类 attr。
- 验证 registry 名称、`fold` 通用 option 和未知 option 失败。
- 验证 attr 文本为简单整数列表。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PRODUCER-CONSUMER-001 | MemoryEffect | `dma.copy -> dma.copy` | 准备合法 `!nn.memory` IR。 | 运行 pass。 | producer 写 `productor=[0]`，consumer 写 `consumer=[0]`。 | `test_producer_consumer_analysis_basic_memory_effect_chain` |
| TC-PRODUCER-CONSUMER-002 | alias | `copy -> view -> matmul -> deslice -> copy` | 准备 `dma.view` 与 `dma.deslice` 链。 | 运行 pass。 | view 不标注，deslice 同时 consumer/productor，result alias target。 | `test_producer_consumer_analysis_alias_and_deslice_chain` |
| TC-PRODUCER-CONSUMER-003 | fanout | 同一 producer 有两个 user | 准备同一路径 fanout IR。 | 运行 pass。 | producer 标多个 event，consumer 分别消费。 | `test_producer_consumer_analysis_fanout_alloc_and_duplicate_read` |
| TC-PRODUCER-CONSUMER-004 | control-flow | `scf.if` incoming 与 after-if edge | 准备 then/else 与 if 后 consumer IR。 | 运行 pass。 | 控制流 edge 只写 `if_branch_*` / `after_if_*` 分类 attr，不叠写主 attr。 | `test_producer_consumer_analysis_if_branch_and_after_if_edges` |
| TC-PRODUCER-CONSUMER-005 | control-flow | `scf.if` 同分支内部 fanout | 准备分支内 producer 后接两个 downstream consumer 的 IR。 | 运行 pass。 | 同分支内部普通顺序 edge 写主 attr，producer 标两个 event，两个 consumer 分别消费不同 event，不写 `if_branch_*`。 | `test_producer_consumer_analysis_if_branch_internal_fanout_uses_distinct_events` |
| TC-PRODUCER-CONSUMER-006 | control-flow | if 前 producer 进入同一 `scf.if` 分支 fanout | 准备 if 前 producer 被同一 then 分支两个 downstream consumer 读取的 IR。 | 运行 pass。 | producer 标两个 `if_branch` event，两个同分支 consumer 分别消费不同 event，不叠写主 attr。 | `test_producer_consumer_analysis_if_incoming_same_branch_fanout_uses_distinct_events` |
| TC-PRODUCER-CONSUMER-007 | control-flow | `symbol.for` loop body / after-loop edge | 准备 loop 前、loop body、loop 后 consumer IR。 | 运行 pass。 | 跨入/跨出 loop 的 edge 只写 `loop_body_*` / `after_loop_*`，同一 loop body block 内普通顺序 edge 只写主 attr。 | `test_producer_consumer_analysis_symbol_for_body_and_after_loop_edges` |
| TC-PRODUCER-CONSUMER-008 | 异常 | 非法旧 event attr / 未知 option | 准备负数 attr 或未知 option。 | 运行 pass / from_options。 | `KernelCodeError` 失败。 | `test_producer_consumer_analysis_rejects_invalid_event_attr_and_unknown_option` |
| TC-PRODUCER-CONSUMER-009 | registry | 公开 pass name | 调用 `load_builtin_passes()`。 | `build_registered_pass("producer-consumer-analysis", {"fold": "false"})`。 | 返回 `ProducerConsumerAnalysisPass(fold=False)`。 | `test_producer_consumer_analysis_registry_entry_and_fold_option` |

## 合同验收

- 主仓只读合同资产：`expectation/pass/producer_consumer_analysis/**`。
- execute / review / merge 不得修改、复制、新建、删除或同步 expectation 文件。
- 验收命令：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate \
python3 -m expectation.pass.producer_consumer_analysis
```

- 记录必须写清 `expectation.*` 来自主仓、`kernel_gen.*` 来自任务 worktree。
