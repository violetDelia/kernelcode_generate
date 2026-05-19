# multi_buffer.md

## 功能简介

- 定义 `multi-buffer` pass 的公开合同。
- 本 pass 将 `LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}')` 生成的 matmul lhs/rhs staging buffer 生命周期改写为 DMA ring。
- v1 只处理同一 `symbol.for` 直接 body 内可证明的 `dma.alloc + dma.copy + kernel.matmul + dma.free` lhs/rhs 成对模式；其它结构保持 no-op。
- 本 pass 不插入 `arch.sign` / `arch.wait`，不做 core split，不处理任意 alias、跨 region control flow 或非 matmul op。

## API 列表

- `class MultiBufferPass(memory_stage: int = 3, fold: bool = True)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/multi_buffer.md`](../../spec/pass/multi_buffer.md)
- `功能实现`：[`kernel_gen/passes/multi_buffer.py`](../../kernel_gen/passes/multi_buffer.py)
- `test`：[`test/passes/test_multi_buffer.py`](../../test/passes/test_multi_buffer.py)

## 依赖

- DMA ring type/op：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- Kernel matmul op：[`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- Symbol loop op：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- pass registry：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- npu-demo-lowering pipeline：[`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)

## 目标

- 为 matmul lhs/rhs staging buffer 引入固定 `memory_stage` 的 ring 表达。
- 将目标 loop 内 `dma.alloc/free` 生命周期替换为 loop 外 backing storage + loop 内 `dma.current_ring` / `dma.advance_ring`。
- 为后续 core split 与 token/sign/wait 同步计划准备稳定 IR 形态。

## 非目标

- 不新增 pipeline option；`npu-demo-lowering` 固定调用 `MultiBufferPass(memory_stage=3)`。
- 不处理 lhs 或 rhs 单边缺失的 partial ring。
- 不处理 dynamic shape 字节数不可静态计算的 staging buffer。
- 不处理不在 `symbol.for` 直接 body 内的 matmul、sibling region use、alias escape、已有 ring、非 matmul、lhs/rhs partial pair 或多 free 生命周期；partial/accumulator buffer 不属于 lhs/rhs pair 时保持原生命周期，不被 ring 化。
- 不修改 `expectation/` 合同资产。

## 行为

### option

- `memory_stage` 直接构造参数必须为正整数。
- `from_options({})` 使用默认 `memory_stage=3`。
- `from_options({"memory-stage": "<int>"})` 使用指定 stage 数。
- `from_options(...)` 只接受 `memory-stage`；未知 option 或 `fold` 必须失败。
- registry 通用 `fold` option 由 [`spec/pass/registry.md`](../../spec/pass/registry.md) 剥离并写回 pass 实例，不属于本 pass 专属 options。

### 改写模式

- 输入必须位于同一 `symbol.for` 直接 body 内。
- lhs/rhs 两个 matmul operand 都必须来自 `DmaAllocOp`。
- 每个 alloc 的直接 use 集合必须且只能包含：
  - 唯一 `dma.copy` target use；
  - 当前 `kernel.matmul` 的对应 lhs/rhs operand use；
  - 唯一 `dma.free` source use。
- 生命周期顺序必须为 `alloc < copy < kernel.matmul < free`。
- lhs/rhs 任一候选不满足条件时，整对保持 no-op。

### 输出形态

- 每个可 ring 化 buffer 在 owner `symbol.for` 之前插入：
  - 一维 `i8` backing `dma.alloc`；
  - stage count `symbol.const`；
  - byte offset `symbol.const`；
  - shape bytes `symbol.const`；
  - `dma.make_ring`。
- 原 loop 内 alloc 位置附近插入 `dma.current_ring`，并用 current slot 替换 `dma.copy` target 与 `kernel.matmul` lhs/rhs operand。
- 当前 slot 最后一次 use 后插入 `dma.advance_ring`；其 result 表示推进后的 slot，本 pass v1 不消费该 result。
- 原 loop 内目标 `dma.alloc` 与匹配 `dma.free` 删除；`dma.copy` 和 `kernel.matmul` 保留。
- `dma.advance_ring` 具有副作用，即使 result 未使用也不得被通用 pass 删除。

## 错误语义

- direct API 错误：
  - `MultiBufferOptionError: memory_stage must be positive`
  - `MultiBufferOptionError: unknown option: <name>`
  - `MultiBufferOptionError: memory-stage must be integer`
- `from_options({"memory-stage": "1"})` 是允许的公开正例；`memory-stage=0`、负数与非整数仍必须稳定失败。
- registry 包装错误：
  - `PassRegistryError: pass 'multi-buffer' option error: MultiBufferOptionError: <原因>`

## 公开导入

- canonical path：`kernel_gen.passes.multi_buffer`
- package root re-export：`from kernel_gen.passes import MultiBufferPass`
- registry pass name：`multi-buffer`

## 使用示例

```python
from kernel_gen.passes.multi_buffer import MultiBufferPass

pass_obj = MultiBufferPass(memory_stage=3)
pass_obj.apply(ctx, module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("multi-buffer", {"memory-stage": "3", "fold": "false"})
```

## 测试矩阵

| 用例 | 场景 | 断言 |
| --- | --- | --- |
| TC-MULTI-BUFFER-001 | direct API options | 构造参数、默认值、非正整数、`from_options` 与直接 `fold` option 失败边界稳定。 |
| TC-MULTI-BUFFER-002 | registry options | registry 透传 `memory-stage`，并由通用 `fold=false` 写回 pass 实例。 |
| TC-MULTI-BUFFER-003 | lhs/rhs 成对 ring 化 | 生成两个 `dma.make_ring/current_ring/advance_ring`，loop 内不残留目标 `dma.alloc/free`，copy/matmul 使用 current slot，advance 位于 matmul 后，且不存在 stale slot use。 |
| TC-MULTI-BUFFER-004 | missing free no-op | lhs/rhs 任一缺少 `dma.free` 时整对不改写。 |
| TC-MULTI-BUFFER-005 | free 早于 compute no-op | `dma.free` 早于 `kernel.matmul` use 时不改写。 |
| TC-MULTI-BUFFER-006 | alias escape no-op | alloc 结果存在 view/reshape/subview 等额外 alias use 时不改写。 |
| TC-MULTI-BUFFER-007 | multiple free no-op | lhs/rhs 任一存在多 free 时整对不改写。 |
| TC-MULTI-BUFFER-008 | existing ring no-op | matmul operand 已来自 ring current slot 时整对不改写。 |
| TC-MULTI-BUFFER-009 | partial pair no-op | lhs-only / rhs-only partial pair 不改写。 |
| TC-MULTI-BUFFER-010 | non-direct body no-op | 不在 `symbol.for` 直接 body 内的 matmul 不改写。 |
| TC-MULTI-BUFFER-011 | non-matmul no-op | loop 内无 `kernel.matmul` 时保持 no-op。 |
| TC-MULTI-BUFFER-012 | accumulator alloc no-op | out/accumulator alloc 不属于 lhs/rhs pair 时不被 ring 化，合法 lhs/rhs pair 仍可改写。 |
| TC-MULTI-BUFFER-013 | nested region use no-op | staging alloc 在 nested `symbol.for` region 内存在额外 use 时整对不改写。 |
| TC-MULTI-BUFFER-014 | sibling region use no-op | staging alloc 在 `scf.if` sibling branch region 内存在额外 use 时整对不改写。 |

## 验收命令

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py
```
