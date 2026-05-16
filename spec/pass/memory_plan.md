# memory_plan.md

## 功能简介

- 定义 `memory-plan` pass 的公开合同。
- 第一阶段只在显式 `insert-free=true` 时为受控 `dma.alloc` 结果补插 `dma.free`。
- 本 pass 与 `memory-pool` 无关，不做 pool rewrite、alignment、backing memory 合并或默认 pipeline 接入。

## API 列表

- `class MemoryPlanPass(insert_free: bool = False, fold: bool = True)`
- `MemoryPlanPass.from_options(options: dict[str, str]) -> MemoryPlanPass`
- `MemoryPlanPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/memory_plan.md`](../../spec/pass/memory_plan.md)
- `功能实现`：[`kernel_gen/passes/memory_plan.py`](../../kernel_gen/passes/memory_plan.py)
- `test`：[`test/passes/test_memory_plan.py`](../../test/passes/test_memory_plan.py)

## 依赖

- `dma` 方言公开 op：
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- pass registry：
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
- pass manager：
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)

## 目标

- 通过 `memory-plan={insert-free=true}` 给缺少释放点的 owned `dma.alloc` 补齐 `dma.free`。
- 已存在合法 `dma.free` 时保持 no-op，不重复插入。
- 对 free 早于后续 use、重复 free、所有权逃逸或 unsupported control flow 给出稳定错误。

## 非目标

- 不进入 `default-lowering` 或 `npu-demo-lowering`。
- 不处理完整 ownership indicator、retain、branch、region-branch、跨函数所有权或多块 CFG。
- 不复用、调用或改变 `memory-pool` 的 summary / rewrite 语义。
- 不管理函数参数、block 参数、`func.call` 返回 memory 或未知 memory-producing op 的 ownership。

## 行为

### option

- `insert-free=false`：pass no-op，不做生命周期检查。
- `insert-free=true`：执行生命周期分析并补插缺失 `dma.free`。
- `fold` 是 registry 通用 option，由 [`spec/pass/registry.md`](../../spec/pass/registry.md) 解析；`MemoryPlanPass.from_options(...)` 不解析 `fold`。

### 管理对象

- 只管理当前 module 内由 `dma.alloc` 产生的 owned memory。
- 支持 alloc 所在 owner block 为单块 `func.func` body 或单块 `symbol.for` body。
- alloc 的最后一次有效 use 若位于嵌套 `symbol.for` 内，free 插入到 owner block 中承载该 nested use 的 ancestor `symbol.for` 之后。

### alias closure

- `dma.view` result alias `source`。
- `dma.reshape` result alias `source`。
- `dma.subview` result alias `source`。
- `dma.deslice` result alias `target` operand，不 alias `source` operand。
- 其它 memory-producing op 不纳入 alias closure；若使用 alloc alias 且无法证明 ownership，必须失败。

### free 插入

- 缺少 `dma.free` 时，在 alias closure 的最后一次非 free use 后插入 `dma.free`。
- 若 alloc 没有非 free use，则在 `dma.alloc` 后插入 `dma.free`。
- 已有合法 `dma.free` 且位于所有非 free use 之后时不重复插入。

## 错误语义

- direct API 错误：
  - `MemoryPlanOptionError: unknown option '<name>'`
  - `MemoryPlanOptionError: insert-free expects bool`
  - `MemoryPlanInvalidLifetime: dma.free appears before last use`
  - `MemoryPlanInvalidLifetime: multiple dma.free for same allocation`
  - `MemoryPlanUnsupportedCall: func.call returning nn.memory requires ownership modelling`
  - `MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region`
  - `MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region`
- registry 包装错误：
  - `PassRegistryError: pass 'memory-plan' option error: MemoryPlanOptionError: unknown option '<name>'`
  - `PassRegistryError: pass 'memory-plan' option error: MemoryPlanOptionError: insert-free expects bool`

## 公开导入

- canonical path：`kernel_gen.passes.memory_plan`
- package root re-export：`from kernel_gen.passes import MemoryPlanPass`
- registry pass name：`memory-plan`

## 使用示例

```python
from kernel_gen.passes.memory_plan import MemoryPlanPass

pass_obj = MemoryPlanPass(insert_free=True, fold=False)
pass_obj.apply(ctx, module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("memory-plan", {"insert-free": "true", "fold": "false"})
```

## 测试矩阵

| 用例 | 场景 | 断言 |
| --- | --- | --- |
| TC-MPLAN-001 | 静态 alloc 缺少 free | 最后 use 后插入 `dma.free` |
| TC-MPLAN-002 | 动态 alloc 缺少 free | 动态 shape operand 保留，最后 use 后插入 `dma.free` |
| TC-MPLAN-003 | 已有合法 free | 不重复插入 |
| TC-MPLAN-004 | free 早于后续 use | 报 `MemoryPlanInvalidLifetime: dma.free appears before last use` |
| TC-MPLAN-004A | free 早于 alias 后续 use | alias closure 继续使用时报 `MemoryPlanInvalidLifetime: dma.free appears before last use` |
| TC-MPLAN-005 | 重复 free | 报 `MemoryPlanInvalidLifetime: multiple dma.free for same allocation` |
| TC-MPLAN-006 | view/reshape/subview alias | alias 最后 use 后插入 free |
| TC-MPLAN-007 | deslice target alias | result alias target，source 不归入 target alias closure |
| TC-MPLAN-008 | nested symbol.for | inner alloc free 在 inner body 末尾，outer alloc free 在 nested use 后 |
| TC-MPLAN-008A | nested symbol.for 内 use-after-free | 同一 nested anchor 内 free 早于后续 use 时失败 |
| TC-MPLAN-008B | nested symbol.for 内释放外层 alloc | nested body 内 free 不能作为 owner-block alloc 的合法最终释放 |
| TC-MPLAN-009 | call operand | call 后插入 free |
| TC-MPLAN-010 | memory-return call | 报 `MemoryPlanUnsupportedCall: func.call returning nn.memory requires ownership modelling` |
| TC-MPLAN-011 | return/yield escape | 报 `MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region` |
| TC-MPLAN-012 | scf.if/scf.for | 报 `MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region` |

## 验收命令

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_registry.py
```

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260516-memory-plan-insert-free \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260516-memory-plan-insert-free:/home/lfr/kernelcode_generate \
python3 -m expectation.pass.memory_plan
```
