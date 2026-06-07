# multi_buffer.md

## 功能简介

- 定义 `multi-buffer` pass 的公开合同。
- 本 pass 将可证明的 loop staging / scratch `dma.alloc/free` 生命周期改写为 DMA ring。
- 兼容旧 matmul lhs/rhs direct pair，同时支持 direct alias 与 direct memory use 形态。
- `target=<target-name>` 非空时优先按 target registry memory capacity 计算 ring `num`；未提供 target 时使用固定 `memory_stage`。
- 本 pass 不插入 `arch.sign` / `arch.wait`，不做 core split，不处理任意 alias、跨 region control flow 或已有 ring 再 ring。

## API 列表

- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/memory/multi_buffer.md`](multi_buffer.md)
- `功能实现`：[`kernel_gen/passes/memory/multi_buffer.py`](../../../kernel_gen/passes/memory/multi_buffer.py)
- `test`：[`test/passes/memory/test_multi_buffer.py`](../../../test/passes/memory/test_multi_buffer.py)

## 依赖

- DMA ring type/op：[`spec/dialect/dma.md`](../../dialect/dma.md)
- Kernel matmul op：[`spec/dialect/kernel.md`](../../dialect/kernel.md)
- Symbol loop op：[`spec/dialect/symbol.md`](../../dialect/symbol.md)
- pass registry：[`spec/pass/registry.md`](../registry.md)
- npu-demo-lowering pipeline：[`spec/pass/pipeline/npu_demo_lowering.md`](../pipeline/npu_demo_lowering.md)

## 目标

- 为 matmul / conv2d lowering 中可证明的 loop staging / scratch buffer 引入 ring 表达。
- 将目标 loop 外或 loop-local staging `dma.alloc/free` 生命周期替换为 backing storage + `dma.current_ring` / `dma.advance_ring`。
- 支持 slot shape bytes 静态计算和 `dma.alloc(%s1, %s2)` 这类 kernel 参数传入的动态 shape bytes 计算。
- 当 `target` 非空时按 target memory capacity 与同 space 对齐感知 slot bytes 合计计算 ring `num`，并优先于 `memory_stage`。
- 为后续 core split 与 token/sign/wait 同步计划准备稳定 IR 形态。

## 非目标

- 不新增 pipeline option；`npu-demo-lowering` 固定按 `target` 自动口径调用 `MultiBufferPass(memory_stage=2, target=<pipeline target>)`。
- 不处理旧 matmul lhs/rhs direct pair 中 lhs 或 rhs 单边缺失的 partial ring。
- 不通过 `symbol.get_dim` 从 memory type 反推动静态 / 动态 shape；动态 shape 必须来自 `dma.alloc` 的公开 dynamic_shape operands。
- 不处理不在 `symbol.for` 直接 body 内的 use、sibling/nested region use、alias escape、已有 ring、旧 direct pair partial 或多 free 生命周期。
- 不处理多层 alias chain；只支持 alloc 的 direct alias，以及 direct alias result 的一层 consumer use。
- pass runtime 不依赖 `expectation/` 合同资产；计划授权范围内的 expectation 同步只用于合同验收。

## 行为

### option

- `memory_stage` 直接构造参数必须为正整数。
- `target` 直接构造参数为 `None` 或非空字符串。
- `from_options({})` 使用默认 `memory_stage=2`。
- `from_options({"memory-stage": "<int>"})` 使用指定 stage 数。
- `from_options({"target": "<target-name>"})` 使用 target registry 中的目标名；当 `target` 与 `memory-stage` 同时出现时 target 优先计算 ring `num`。
- `from_options(...)` 只接受 `memory-stage` 与 `target`；未知 option 或 `fold` 必须失败。
- registry 通用 `fold` option 由 [`spec/pass/registry.md`](../registry.md) 剥离并写回 pass 实例，不属于本 pass 专属 options。

### 改写模式

#### 旧 matmul lhs/rhs direct pair

- 输入 matmul 必须位于同一 `symbol.for` 直接 body 内。
- lhs/rhs 两个 matmul operand 都必须来自 `DmaAllocOp`。
- lhs/rhs staging `DmaAllocOp` 必须位于 owner `symbol.for` 的 parent block 中，并且在 `symbol.for` 之前。
- 对应 `DmaFreeOp` 必须位于同一 parent block 中，并且在 `symbol.for` 之后。
- 每个 alloc 的直接 use 集合必须且只能包含：
  - loop body 中唯一 `dma.copy` target use；
  - 当前 `kernel.matmul` 的对应 lhs/rhs operand use；
  - parent block 中唯一 `dma.free` source use。
- 生命周期顺序必须为 parent block 中 `alloc < symbol.for < free`，loop body 中 `copy < kernel.matmul`。
- lhs/rhs 任一候选不满足条件时，整对保持 no-op。

#### loop staging / scratch direct alias 与 direct use

- 每个 `dma.alloc` 独立分析，必须且只能匹配一个 `dma.free`。
- 支持 alloc 的 direct alias：
  - `dma.reinterpret(%alloc, ...)`
  - `dma.view(%alloc, ...)`
  - `dma.reshape(%alloc, ...)`
  - `dma.subview(%alloc, ...)`
- 支持 alloc 或 direct alias result 被以下 loop body op 的 memory operand 消费：
  - `dma.broadcast`
  - `dma.copy`
  - `dma.deslice`
  - `dma.fill`
  - `dma.load`
  - `dma.slice`
  - `dma.store`
  - `dma.transpose`
  - `kernel.binary_elewise`
  - `kernel.img2col1d`
  - `kernel.img2col2d`
  - `kernel.matmul`
- 候选必须至少包含 `dma.copy`、`dma.deslice`、`dma.slice`、`dma.transpose`、`kernel.img2col1d`、`kernel.img2col2d` 或 `kernel.matmul` 之一作为进展 use；只有 direct `dma.copy` 且无 alias 的候选保持 no-op。
- 旧 matmul lhs/rhs direct pair 的 `kernel.matmul` operand 1/2 仍由兼容路径处理；新 loop staging 路径不抢占该成对合同。
- 所有 access op 必须位于同一个最近 `symbol.for` 的直接 body 内，不得跨 nested region、sibling region 或 loop 外 escape。
- 若原 alloc/free 位于目标 loop body 内，生命周期必须满足 `alloc < first_use <= last_use < free`，ring setup 插在原 alloc 之前，`num` 固定为 1。
- 若原 alloc/free 位于目标 loop 的同一祖先 block，生命周期必须满足 `alloc < target_loop_anchor < free`；ring setup 插在目标 loop anchor 前。
- 祖先 block 候选若 access 中包含 `kernel.binary_elewise`，当前保持 no-op，避免把 reduce-carried / partial scratch 误判为每轮独立 staging。
- 目标 loop body 中已有 `dma.current_ring` 时，当前候选保持 no-op，避免已有 ring 再 ring 化。

### 输出形态

- 每个可 ring 化 buffer 在插入锚点之前插入：
  - 一维 `i8` backing `dma.alloc`；
  - ring `num` operand；
  - byte offset operand；
  - `dma.make_ring`。
- 静态 `memory-stage` 路径中 `num` 为 `memory_stage`；`offset` 为 slot type 的 padded byte span；backing bytes 为 `num * offset`，不得额外 `+1`。
- `target` 路径中按 target loop / insertion scope / memory space 分组；同一 space 共享 `num`，不同 space 各自使用本 space capacity。
- `target` 路径中计算 `num` 时，分母使用同组每个 slot byte size 按 memory-pool alignment 1024 向上对齐后的合计；若同 scope 内存在同 space 预留 alloc，先按同一 alignment 对预留量向上对齐后再扣减 capacity。
- 动态 same-space case 中，shape bytes 由 `dma.alloc` dynamic_shape operands 计算，例如 lhs `4*S1*S2`、rhs `4*S2*S3`，共享 num 使用 `524288 floordiv (align_up(4*S1*S2, 1024) + align_up(4*S2*S3, 1024))` 等价的 `symbol.add/floordiv/mul` 链；不得使用 `symbol.get_dim` 替代 kernel 参数来源。
- 如果 target 缺少对应 `*_memory_size`、capacity 非正、slot bytes 无法证明、动态 shape operand 在插入点不可见，或静态 `num <= 0`，当前组保持 no-op。
- 在第一个本轮 use 前插入 `dma.current_ring`，并用 current slot 替换 direct alias source 或 direct memory use operand。
- 当前 slot 最后一次 use 后插入 `dma.advance_ring`；其 result 表示推进后的 slot，本 pass v1 不消费该 result。
- 原 typed staging `dma.alloc` 与匹配 `dma.free` 删除；原 consumer op 保留。
- `dma.advance_ring` 具有副作用，即使 result 未使用也不得被通用 pass 删除。

## 错误语义

- direct API 错误：
  - `MultiBufferOptionError: memory_stage must be positive`
  - `MultiBufferOptionError: target must be non-empty`
  - `MultiBufferOptionError: unknown option: <name>`
  - `MultiBufferOptionError: memory-stage must be integer`
- `from_options({"memory-stage": "1"})` 是允许的公开正例；`memory-stage=0`、负数与非整数仍必须稳定失败。
- registry 包装错误：
  - `PassRegistryError: pass 'multi-buffer' option error: MultiBufferOptionError: <原因>`

## 公开导入

- canonical path：`kernel_gen.passes.memory.multi_buffer`
- package root re-export：`from kernel_gen.passes import MultiBufferPass`
- registry pass name：`multi-buffer`

## 使用示例

```python
from kernel_gen.passes.memory.multi_buffer import MultiBufferPass

pass_obj = MultiBufferPass(target="npu_demo")
pass_obj.apply(ctx, module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("multi-buffer", {"memory-stage": "4", "target": "npu_demo", "fold": "false"})
```

## 测试矩阵

| 用例 | 场景 | 断言 |
| --- | --- | --- |
| TC-MULTI-BUFFER-001 | direct API options | 构造参数、默认值、非正整数、`from_options` 与直接 `fold` option 失败边界稳定。 |
| TC-MULTI-BUFFER-002 | registry options | registry 透传 `memory-stage` / `target`，并由通用 `fold=false` 写回 pass 实例。 |
| TC-MULTI-BUFFER-003 | lhs/rhs 成对 ring 化 | loop 外 staging alloc/free 被删除，生成两个 `dma.make_ring/current_ring/advance_ring`，copy/matmul 使用 current slot，advance 位于 matmul 后。 |
| TC-MULTI-BUFFER-004 | missing free no-op | lhs/rhs 任一缺少 `dma.free` 时整对不改写。 |
| TC-MULTI-BUFFER-005 | free 早于 loop no-op | `dma.free` 早于 `symbol.for` 时不改写。 |
| TC-MULTI-BUFFER-006 | loop-internal alloc no-op | 旧 loop 内 alloc/free staging 形态不改写。 |
| TC-MULTI-BUFFER-007 | alias escape no-op | alloc 结果存在 view/reshape/subview 等额外 alias use 时不改写。 |
| TC-MULTI-BUFFER-008 | multiple free no-op | lhs/rhs 任一存在多 free 时整对不改写。 |
| TC-MULTI-BUFFER-009 | existing ring no-op | matmul operand 已来自 ring current slot 时整对不改写。 |
| TC-MULTI-BUFFER-010 | partial pair no-op | lhs-only / rhs-only partial pair 不改写。 |
| TC-MULTI-BUFFER-011 | nested region use no-op | staging alloc 在 nested `symbol.for` region 内存在额外 use 时整对不改写。 |
| TC-MULTI-BUFFER-012 | target same-space static num | `target=npu_demo` 下同一 space 按 lhs/rhs 对齐后 shape bytes 合计计算共享 num，优先于 `memory-stage`。 |
| TC-MULTI-BUFFER-013 | target different-space static num | `target=npu_demo` 下不同 space 各自按本 space capacity 与本 space 对齐后 slot bytes 计算 num。 |
| TC-MULTI-BUFFER-014 | target dynamic same-space num | 动态 shape 来自 kernel 参数，使用包含 1024 对齐的 `symbol.mul/add/floordiv` 计算共享 num，不使用 `symbol.get_dim`。 |
| TC-MULTI-BUFFER-015 | loop-local direct use | loop body 内 `dma.alloc -> dma.slice -> dma.free` direct use 改写为 `num=1` ring，consumer 使用 current slot。 |

## 验收命令

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py
```
