# memory_plan.md

## 功能简介

- 定义 `memory-plan` pass 的公开合同。
- 第一阶段只在显式 `insert-free=true` 时为受控 `dma.alloc` 结果补插 `dma.free`。
- 原型阶段在显式 `insert-free=true,reuse=true` 时允许同一受支持 owner block 内
  类型完全一致且生命周期不重叠的 `dma.alloc` 做保守复用。
- 显式 `auto-pad=true` 时允许把可证明 static upper bound 的 dynamic tail `dma.alloc`
  改写为 padded backing alloc + 保留原 logical type 的 `dma.reinterpret` alias。
- 本 pass 与 `memory-pool` 的 rewrite 语义分离，不做 pool rewrite、alignment 或 backing memory 合并；`npu-demo-lowering` 以 `MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True)` 固定调用本 pass 补齐生命周期、启用 padded backing / logical alias 改写并启用保守复用。

## API 列表

- `class MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False, auto_pad: bool = False)`
- `MemoryPlanPass.from_options(options: dict[str, str]) -> MemoryPlanPass`
- `MemoryPlanPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/memory/memory_plan.md`](memory_plan.md)
- `功能实现`：[`kernel_gen/passes/memory/memory_plan.py`](../../../kernel_gen/passes/memory/memory_plan.py)
- `test`：[`test/passes/memory/test_memory_plan.py`](../../../test/passes/memory/test_memory_plan.py)

## 依赖

- `dma` 方言公开 op：
  - [`spec/dialect/dma.md`](../../dialect/dma.md)
- pass registry：
  - [`spec/pass/registry.md`](../registry.md)
- pass manager：
  - [`spec/pass/pass_manager.md`](../pass_manager.md)

## 目标

- 通过 `memory-plan={insert-free=true}` 给缺少释放点的 owned `dma.alloc` 补齐 `dma.free`。
- 通过 `memory-plan={insert-free=true,reuse=true}` 在保守可证明时复用生命周期不重叠的 owned `dma.alloc`。
- 通过 `memory-plan={auto-pad=true}` 把 dynamic tail logical alloc 物化为 padded backing，并让 consumer 继续使用 logical alias。
- 已存在合法 `dma.free` 时保持 no-op，不重复插入。
- 对 free 早于后续 use、重复 free、所有权逃逸或 unsupported control flow 给出稳定错误。

## 非目标

- `default-lowering` 不接入本 pass；`npu-demo-lowering` 固定以 `insert_free=True, reuse=True, fold=False, auto_pad=True` 调用，不新增 memory-plan 专属 pipeline option。
- `npu-demo-lowering` 固定开启既有 `auto_pad` 能力，但不新增 `auto-pad` / `auto_pad` pipeline option，也不改变固定 pipeline 顺序。
- `auto_pad` 不删除已有 fill、不改变 `dma.deslice` partial-write 语义、不改变 `kernel.matmul` consumer 语义。
- 不处理完整 ownership indicator、retain、region-branch、跨函数所有权或多块 CFG；仅支持本文件明确列出的单块 `scf.if` branch-local alloc/free/reuse 形态。
- 不复用、调用或改变 `memory-pool` 的 summary / rewrite 语义。
- 不管理函数参数、block 参数、`func.call` 返回 memory 或未知 memory-producing op 的 ownership。
- 不跨 region、跨 unsupported CFG 或跨无法证明 use/free 顺序的 owner block 复用内存。

## 行为

### option

- `insert-free=false`：pass no-op，不做生命周期检查。
- `insert-free=true`：执行生命周期分析并补插缺失 `dma.free`。
- `reuse=false`：默认行为，不做 alloc 复用。
- `reuse=true`：仅在 `insert-free=true` 时启用保守 linear-scan 复用；单独开启 `reuse=true` 仍保持 no-op。
- `auto-pad` 取 false：默认行为，不做 padded backing rewrite。
- `auto-pad=true`：在 lifecycle 分析与 `insert-free` 补齐之前尝试执行 padded backing rewrite；候选无法证明或无法物化时对当前 alloc no-op。
- `fold` 是 registry 通用 option，由 [`spec/pass/registry.md`](../registry.md) 解析；`MemoryPlanPass.from_options(...)` 不解析 `fold`。

### 管理对象

- 只管理当前 module 内由 `dma.alloc` 产生的 owned memory。
- 支持 alloc 所在 owner block 为单块 `func.func` body、单块 `symbol.for` body 或单块 `scf.if` then/else branch body。
- alloc 的最后一次有效 use 若位于嵌套 `symbol.for` 内，free 插入到 owner block 中承载该 nested use 的 ancestor `symbol.for` 之后。
- alloc 的最后一次有效 use 若位于 owner block 中单块 `scf.if` 分支内，free 插入到 owner block 中承载该 nested use 的 `scf.if` 之后。
- `scf.if` 分支内新建 `dma.alloc` 支持 branch-local 生命周期建模：free 只能插入同一 branch block，同一 branch 内类型完全一致且生命周期不重叠的 alloc 可以复用；不得跨 then/else branch 或跨 if 外 owner block 复用。

### alias closure

- `dma.view` result alias `source`。
- `dma.reshape` result alias `source`。
- `dma.subview` result alias `source`。
- `dma.reinterpret` result alias `source`。
- `dma.deslice` 是目标式写回 op，不产生 result；target 生命周期读取 source use，但 source 不归入 target alias closure。
- 其它 memory-producing op 不纳入 alias closure；若使用 alloc alias 且无法证明 ownership，必须失败。

### free 插入

- 缺少 `dma.free` 时，在 alias closure 的最后一次非 free use 后插入 `dma.free`。
- 若 alloc 没有非 free use，则在 `dma.alloc` 后插入 `dma.free`。
- 已有合法 `dma.free` 且位于所有非 free use 之后时不重复插入。

### memory reuse

- 仅当 `insert-free=true` 且 `reuse=true` 时执行。
- 只在同一 supported owner block 内做线性扫描复用。
- `scf.if` then/else 分支分别作为独立 supported owner block；同一分支内部可复用，互斥分支之间不得复用。
- 只复用 result type 完全一致的 `dma.alloc`，即 space、dtype、rank、shape、stride 均相同。
- 前一个 alloc 的合法 free 必须早于后一个 alloc，才可将后一个 alloc 的 use 改写为前一个 alloc。
- 复用成功时删除前一个 alloc 的旧 free 与后一个 alloc，保留后一个生命周期末尾的 free。
- 遇到 escape、unsupported CFG、未知 producing、free-before-use、重复 free 或跨 region 不可证明 use 时沿用既有错误或保守 no-op。

### auto_pad rewrite

- 仅当 `auto-pad=true` 时执行，且执行顺序早于 `insert-free` 生命周期补齐。
- 只处理 row-major contiguous `NnMemoryType` 的 `dma.alloc`。
- 若 logical shape 某维是 `min(TILE, EXTENT - iter<0,EXTENT,TILE>)`，该维 padded backing upper bound 为 `TILE`。
- 非 tail 维度保持原 logical shape；匿名 `?` 或找不到支配当前 alloc 的 shape/stride operand 时，当前 alloc 保守 no-op。
- rewrite 成功时，原 logical alloc：
  - 替换为 padded backing `dma.alloc`，backing shape 使用每个维度的 upper bound / 原维度，backing stride 使用 row-major contiguous stride；
  - 紧跟一个 `dma.reinterpret(backing, offset=0, logical_shape, logical_stride)`，result type 保留原 alloc 的 logical `NnMemoryType`；
  - 普通 consumer 改写为继续使用 logical alias，不直接读取 padded backing；
  - 已有 direct `dma.free(%logical)` 重定向为 `dma.free(%backing)`。
- 无法证明、无法物化 operand 或生成的 backing / alias verifier 不通过时，不抛出新的 auto_pad 稳定错误，只对当前候选 no-op。
- `insert-free=true` 与 `auto-pad=true` 同时开启时，后续 lifecycle 分析以 backing alloc 及其 logical alias closure 为管理对象。

## 错误语义

- direct API 错误：
  - `MemoryPlanOptionError: unknown option '<name>'`
  - `MemoryPlanOptionError: insert-free expects bool`
  - `MemoryPlanOptionError: reuse expects bool`
  - `MemoryPlanOptionError: auto-pad expects bool`
  - `MemoryPlanInvalidLifetime: dma.free appears before last use`
  - `MemoryPlanInvalidLifetime: multiple dma.free for same allocation`
  - `MemoryPlanUnsupportedCall: func.call returning nn.memory requires ownership modelling`
  - `MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region`
  - `MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region`
- registry 包装错误：
  - `PassRegistryError: pass 'memory-plan' option error: MemoryPlanOptionError: unknown option '<name>'`
  - `PassRegistryError: pass 'memory-plan' option error: MemoryPlanOptionError: insert-free expects bool`
  - `PassRegistryError: pass 'memory-plan' option error: MemoryPlanOptionError: reuse expects bool`
  - `PassRegistryError: pass 'memory-plan' option error: MemoryPlanOptionError: auto-pad expects bool`

## 公开导入

- canonical path：`kernel_gen.passes.memory.memory_plan`
- package root re-export：`from kernel_gen.passes import MemoryPlanPass`
- registry pass name：`memory-plan`

## 使用示例

```python
from kernel_gen.passes.memory.memory_plan import MemoryPlanPass

pass_obj = MemoryPlanPass(insert_free=True, fold=False, reuse=True, auto_pad=True)
pass_obj.apply(ctx, module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("memory-plan", {"insert-free": "true", "reuse": "true", "auto-pad": "true", "fold": "false"})
```

## 测试矩阵

| 用例 | 场景 | 断言 |
| --- | --- | --- |
| TC-MPLAN-001 | 静态 alloc 缺少 free | 最后 use 后插入 `dma.free` |
| TC-MPLAN-002 | 动态 alloc 缺少 free | 动态 shape operand 保留，最后 use 后插入 `dma.free` |
| TC-MPLAN-002A | auto_pad dynamic tail alloc | 改写为 padded backing `dma.alloc` + logical `dma.reinterpret`，consumer 使用 logical alias |
| TC-MPLAN-002B | auto_pad 已有 direct free | 释放目标从 logical alias 重定向到 backing |
| TC-MPLAN-002C | auto_pad unknown shape | 当前 alloc 保守 no-op，不生成 `dma.reinterpret` |
| TC-MPLAN-002D | auto_pad START 非 0 tail | `min(T, END - iter<START,END,T>)` 可推导 padded backing 上界 `T` |
| TC-MPLAN-002E | auto_pad 乘积 tail | `K * min(T, tail)` 在 `K*T` SSA 可见时改写为 padded backing |
| TC-MPLAN-002F | auto_pad `min(A, B)` | `A` 可作为正上界时使用 `A` 作为 padded backing shape |
| TC-MPLAN-002G | auto_pad dynamic matmul effective tile | `symbol-buffer-hoist` 后 padded backing 外提，`kernel.matmul` 继续消费 logical alias，不直接读取 padded backing |
| TC-MPLAN-002H | npu-demo-lowering 固定 auto_pad | 三段 `MemoryPlanPass` 均以 `auto_pad=True` 构造，matmul pipeline dump 中 padded backing / logical alias 与 alloc/free 外提语义可观察 |
| TC-MPLAN-003 | 已有合法 free | 不重复插入 |
| TC-MPLAN-003A | reuse 类型一致且生命周期不重叠 | 删除后一个 alloc 与前一个旧 free，保留最终 free |
| TC-MPLAN-003B | reuse 类型不一致 | 保守 no-op，两个 alloc/free 都保留 |
| TC-MPLAN-004 | free 早于后续 use | 报 `MemoryPlanInvalidLifetime: dma.free appears before last use` |
| TC-MPLAN-004A | free 早于 alias 后续 use | alias closure 继续使用时报 `MemoryPlanInvalidLifetime: dma.free appears before last use` |
| TC-MPLAN-005 | 重复 free | 报 `MemoryPlanInvalidLifetime: multiple dma.free for same allocation` |
| TC-MPLAN-006 | view/reshape/subview/reinterpret alias | alias 最后 use 后插入 free |
| TC-MPLAN-007 | deslice target writeback | target 写回不让 source 归入 target alias closure |
| TC-MPLAN-008 | nested symbol.for | inner alloc free 在 inner body 末尾，outer alloc free 在 nested use 后 |
| TC-MPLAN-008A | nested symbol.for 内 use-after-free | 同一 nested anchor 内 free 早于后续 use 时失败 |
| TC-MPLAN-008B | nested symbol.for 内释放外层 alloc | nested body 内 free 不能作为 owner-block alloc 的合法最终释放 |
| TC-MPLAN-009 | call operand | call 后插入 free |
| TC-MPLAN-010 | memory-return call | 报 `MemoryPlanUnsupportedCall: func.call returning nn.memory requires ownership modelling` |
| TC-MPLAN-011 | return/yield escape | 报 `MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region` |
| TC-MPLAN-012 | scf.for 内 alloc | 报 `MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region` |
| TC-MPLAN-012A | scf.if branch-local alloc | 在同一 branch block 末尾插入 `dma.free` |
| TC-MPLAN-012B | owner block alloc 在 scf.if 分支内 use | `dma.free` 插入到 `scf.if` 后 |
| TC-MPLAN-012C | scf.if 同一 branch 内类型一致 alloc 复用 | 只复用同一 branch 内生命周期不重叠 alloc，不跨 branch |
| TC-MPLAN-012D | scf.if 互斥分支 alloc | then/else branch 分别保留独立 alloc/free，不做跨分支复用 |
| TC-MPLAN-012E | scf.if branch-local alloc 经 `scf.yield` 逃逸 | 报 `MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region` |

## 验收命令

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_memory_plan.py test/passes/test_registry.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=. \
python3 -m expectation.pass.memory_plan
```
