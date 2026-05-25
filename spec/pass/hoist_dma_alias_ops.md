# hoist_dma_alias_ops

## 功能简介

- 定义 `hoist-dma-alias-ops` pass 的公开合同。
- 本 pass 使用 xDSL `RewritePattern` / `PatternRewriteWalker` 组织 rewrite，不使用手写整段 block 遍历。
- P2 `DmaAliasThroughWriteNoReadPattern` 负责把 full-cover alias 穿过 write-only / no-read writer，并把 writer target 改为 alias result。
- P1 `DmaAliasHoistPattern` 负责把 NoMemoryEffect alias descriptor 移到 operands 已支配的更早位置，不改写任何 writer target。
- P1 还负责在既有公开 pattern 框架内删除 broadcast source 上的 leading-unit `dma.reinterpret([N] -> [1,N])`，并把相关 writer target 与 `dma.broadcast` source 改回 flat source。
- 当前 alias op 范围固定为 `dma.reshape`、`dma.view` 与 `dma.reinterpret`。
- 不保留旧 `view + deslice` 连续维度分组，也不保留旧单 op pattern 兼容入口。

## API 列表

- `class DmaAliasThroughWriteNoReadPattern(module: ModuleOp)`
- `DmaAliasThroughWriteNoReadPattern.match_and_rewrite(op: Operation, rewriter: PatternRewriter) -> None`
- `class DmaAliasHoistPattern(module: ModuleOp)`
- `DmaAliasHoistPattern.match_and_rewrite(op: Operation, rewriter: PatternRewriter) -> None`
- `get_hoist_dma_alias_ops_pass_patterns(module: ModuleOp) -> list[RewritePattern]`
- `class HoistDmaAliasOpsPass(fold: bool = True)`
- `HoistDmaAliasOpsPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/hoist_dma_alias_ops.md`](../../spec/pass/hoist_dma_alias_ops.md)
- `功能实现`：[`kernel_gen/passes/hoist/dma_alias_ops.py`](../../kernel_gen/passes/hoist/dma_alias_ops.py)
- `test`：[`test/passes/test_hoist_dma_alias_ops.py`](../../test/passes/test_hoist_dma_alias_ops.py)

## 依赖

- `dma` 方言公开 op：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- pass registry：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- npu-demo pipeline：[`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)

## 目标

- 固定 pass 名称为 `hoist-dma-alias-ops`。
- 固定 canonical module path 为 `kernel_gen.passes.hoist.dma_alias_ops`。
- 固定 registry 构造入口 `build_registered_pass("hoist-dma-alias-ops")` 可返回 `HoistDmaAliasOpsPass`。
- 固定 public pattern getter 顺序为 through-write pattern 在前、pure hoist pattern 在后。
- 固定 standalone pass 的 registry / 手动 pipeline 使用合同；默认 `npu-demo-lowering` 由
  `symbol-hoist-pipeline` 承接本 pass 的 dma alias hoist pattern。

## 非目标

- 不新增 `hoist-ops` / `hoist_ops` pass 专属 option。
- 不把 pattern 或 getter re-export 到 `kernel_gen.passes` package root。
- 不把 `HoistDmaAliasOpsPass` re-export 到 `kernel_gen.passes` package root。
- 不保留 `DmaReshapeThroughFillPattern`。
- 不保留 `DmaViewDesliceGroupingPattern`。
- 不实现 `view + deslice` grouping，不生成用于 grouping 的额外 `dma.reshape`。
- 不做 `dma.alloc -> dma.reshape` fold。
- 不做 `dma.reshape -> dma.reshape` chain collapse。
- 不新增 `dma.subview` 行为。
- 不新增 `DmaBroadcastSourceAliasPattern` 或第三个公开 pattern class。
- 不改变 `dma.broadcast`、`dma.reinterpret` 的 dialect API 或 verifier API。
- 不跨任意 region 做 same-block 重排；仅允许 direct `symbol.for` body 内 loop-invariant alias 提到该 loop 前。

## 行为

### P2：`DmaAliasThroughWriteNoReadPattern`

#### 功能说明

- 匹配同一 block 内紧邻的 `writer; alias`。
- `alias` 必须是 `dma.reshape`、`dma.view` 或 `dma.reinterpret`。
- `writer.operands[0]` 必须等于 alias source。
- `get_effects(writer)` 必须证明 `writer.operands[0]` 有 `MemoryEffectKind.WRITE` 且没有 `MemoryEffectKind.READ`。
- `alias` 必须可证明 full-cover：
  - `dma.reshape`：source/result 同 space、同 element type、contiguous，numel 相等，shape operands exact 匹配 result shape。
  - `dma.view`：offset 全 `0`，logical stride 全 `1`，source/result shape 与 physical stride exact 相等。
  - `dma.reinterpret`：offset 为 `0`，非一维 i8 byte pool，source/result 同 space、同 element type、contiguous，numel 相等，shape/stride operands exact 匹配 result layout。
- rewrite 后 alias 移到 writer 前，writer target 改为 alias result。
- rewrite 后 `module.verify()` 失败时必须回滚 alias 位置和 writer target。

#### before

```mlir
"dma.fill"(%src, %zero) : (!nn.memory<...>, f32) -> ()
%alias = "dma.reshape"(%src, %m, %n) : (...) -> !nn.memory<...>
```

#### after

```mlir
%alias = "dma.reshape"(%src, %m, %n) : (...) -> !nn.memory<...>
"dma.fill"(%alias, %zero) : (!nn.memory<...>, f32) -> ()
```

#### 注意事项

- P2 不得按 `DmaFillOp` class 写死 writer 白名单；`dma.broadcast` 等公开 effect 为 WRITE/no-READ 的 writer 也可命中。
- writer 对同一 target 同时 READ/WRITE 时必须 no-op。
- byte-pool dtype-changing `dma.reinterpret` 必须 no-op。

### P1：`DmaAliasHoistPattern`

#### 功能说明

- 匹配 `dma.reshape`、`dma.view` 或 `dma.reinterpret`。
- same-block 场景把 alias 移到所有同 block operands 定义之后的最早合法位置。
- direct `symbol.for` body 场景中，若 alias 所有 operands 都支配该 `symbol.for`，可把 alias 提到 loop 前。
- P1 不修改任何 writer target。
- P1 删除 broadcast source leading-unit reinterpret 时例外：该场景不是纯位置移动，而是将 `dma.fill(alias)` 这类 write/no-read writer target 与 `dma.broadcast(dst, alias)` source 一并改回 flat source。
- P1 同 block 移动时只允许跨过不触碰 alias source 的 op；若区间内存在 READ/WRITE/unknown effect 触碰 source，则 no-op，避免绕过 P2 的 write/no-read 判定。

#### before

```mlir
"dma.fill"(%dst, %zero) : (!nn.memory<...>, f32) -> ()
%alias = "dma.view"(%src, %o0, %o1, %s0, %s1, %t0, %t1) : (...) -> !nn.memory<...>
```

#### after

```mlir
%alias = "dma.view"(%src, %o0, %o1, %s0, %s1, %t0, %t1) : (...) -> !nn.memory<...>
"dma.fill"(%dst, %zero) : (!nn.memory<...>, f32) -> ()
```

#### 注意事项

- alias 依赖 loop iterator、loop-carried block argument 或 loop body 内 SSA 时不得提出循环。
- alias source 被待跨越 writer 读/写时不得同 block 外提。
- P1 只改变 alias descriptor 的位置，不新增、删除或合并 alias op。

### Broadcast source leading-unit reinterpret 删除

#### 功能说明

- 匹配 `dma.reinterpret`，且 source/result 满足：
  - source 是 typed contiguous 一维 `[N]` memory。
  - result 是 typed contiguous 二维 `[1,N]` memory，stride 为 `[N,1]`。
  - offset 为 `0`。
  - source/result 同 space、同 element type，且不是一维 i8 byte pool dtype-changing reinterpret。
  - shape / stride operands exact 匹配 result layout。
- alias result 的所有 use 必须只属于以下两类：
  - `dma.broadcast` 的 source operand。
  - `get_effects(...)` 证明为 write/no-read 的 writer target operand。
- rewrite 后：
  - `dma.broadcast(dst, alias)` 改为 `dma.broadcast(dst, source)`。
  - `writer(alias, ...)` 改为 `writer(source, ...)`。
  - alias 无剩余 use 时删除该 `dma.reinterpret`。
- retarget 后每个被改写 op 必须自身 verifier 通过；若输入 module 原本可通过全模块 verifier，则 retarget 后全模块 verifier 也必须通过。
- 任一 unknown use、非 leading-unit shape、offset 非 0、byte-pool、dtype/space 不匹配、op verifier 失败或 module verifier 失败时必须完整 rollback / no-op。
- rank0 source 或其它无法构造 `[N] -> [1,N]` 证明的 source rank 必须 no-op，不得在维度检查前访问不存在的 shape/stride 条目。

#### before

```mlir
%alias = "dma.reinterpret"(%flat, %c0, %c1, %n, %n, %c1) : (...) -> !nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>
"dma.fill"(%alias, %zero) : (!nn.memory<...>, f32) -> ()
"dma.broadcast"(%dst, %alias) : (!nn.memory<...>, !nn.memory<...>) -> ()
```

#### after

```mlir
"dma.fill"(%flat, %zero) : (!nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
"dma.broadcast"(%dst, %flat) : (!nn.memory<...>, !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
```

#### 注意事项

- `[N] -> [2,N/2]`、`[N] -> [M,N]`、offset 非 0 和无法证明物理 index set 等价的 reinterpret 必须保留。
- 若某个 write/no-read writer target retarget 后与 `source` 的 rank、shape 或 verifier 合同不兼容，必须保留原 alias 与所有原 uses。
- 该行为归属既有 `DmaAliasHoistPattern`，不得新增第三个公开 pattern class。

## 公开导入

```python
from kernel_gen.passes.hoist.dma_alias_ops import HoistDmaAliasOpsPass
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

pass_obj = HoistDmaAliasOpsPass()
pass_obj.apply(ctx, module)

load_builtin_passes()
same_pass = build_registered_pass("hoist-dma-alias-ops")
```

## registry

- `build_registered_pass("hoist-dma-alias-ops")` 返回 `HoistDmaAliasOpsPass`。
- `build_registered_pass("hoist-dma-alias-ops", {"fold": "false"})` 返回 `fold=False` 的 pass。
- `build_registered_pass("hoist-dma-alias-ops", {"hoist-ops": "dma.fill"})` 必须失败：
  - `PassRegistryError: pass 'hoist-dma-alias-ops' does not accept options`
- `build_registered_pass("hoist-dma-alias-ops", {"hoist_ops": "dma.fill"})` 必须失败：
  - `PassRegistryError: pass 'hoist-dma-alias-ops' does not accept options`

## pipeline

- 默认 `npu-demo-lowering` 不再直接编排 standalone `SymbolLoopHoistPass()` 与
  `HoistDmaAliasOpsPass()`；相关 pattern 由 `SymbolHoistPipelinePass` 承接。
- standalone 手动 pipeline 仍可显式把 `SymbolLoopHoistPass()` 与
  `HoistDmaAliasOpsPass()` 相邻使用。
- dump marker 验收只按 pass name 相对顺序，不绑定固定数字编号。

## 测试

### 测试目标

- 验证公开 pattern API 只包含 `DmaAliasThroughWriteNoReadPattern` 与 `DmaAliasHoistPattern`。
- 验证 P2 使用公开 MemoryEffect，不写死 `dma.fill`。
- 验证 P1 可以跨过无关 writer，但不能跨过触碰 alias source 的 writer。
- 验证旧 `view/deslice grouping` 不再发生。
- 验证 broadcast source leading-unit `dma.reinterpret([N] -> [1,N])` 可删除，非 leading-unit、offset 非 0 和 retarget verifier 失败时 no-op。
- 验证 registry 默认构造、`fold=false` 与未知专属 option 失败。

### 测试矩阵

| 用例 | 场景 | 断言 |
| --- | --- | --- |
| TC-HOIST-DMA-ALIAS-001 | 公开 pattern API | `__all__` 与 getter 顺序只暴露 P2/P1 两个 pattern |
| TC-HOIST-DMA-ALIAS-002 | P2 静态源码门禁 | P2 class source 包含 `get_effects`、WRITE/READ、`operands[0]`，且不含 `DmaFillOp` |
| TC-HOIST-DMA-ALIAS-003 | P1 纯 view 外提 | `dma.view(%src)` 可跨过无关 `dma.fill(%dst)`，fill target 不变 |
| TC-HOIST-DMA-ALIAS-004 | P2 broadcast writer | scalar `dma.broadcast` 可作为 WRITE/no-READ writer 被 retarget |
| TC-HOIST-DMA-ALIAS-005 | READ/WRITE 同 target | `dma.broadcast(%flat, %flat)` 后的 alias 保持 no-op |
| TC-HOIST-DMA-ALIAS-006 | loop-invariant reinterpret | `dma.reinterpret` 可从 direct `symbol.for` body 提到 loop 前 |
| TC-HOIST-DMA-ALIAS-007 | byte-pool reinterpret | i8 pool 到 f32 typed memory 的 reinterpret 保持 no-op |
| TC-HOIST-DMA-ALIAS-008 | 删除 view/deslice grouping | 不新增 `dma.reshape` |
| TC-HOIST-DMA-ALIAS-009 | registry | 默认构造、`fold=false`、未知专属 option 失败 |
| TC-HOIST-DMA-ALIAS-010 | broadcast source leading-unit static/dynamic | `[56] -> [1,56]` 与 `[N] -> [1,N]` alias 删除，`dma.fill` / `dma.broadcast` 改回 flat source |
| TC-HOIST-DMA-ALIAS-011 | broadcast source 非 leading-unit | `[56] -> [2,28]` alias 保持 no-op |
| TC-HOIST-DMA-ALIAS-012 | broadcast source retarget rollback | write/no-read writer target retarget 后 verifier 失败时 alias 与 uses 完整保留 |
| TC-HOIST-DMA-ALIAS-013 | broadcast source rank0 source no-op | rank0 source `dma.reinterpret` 带 use 时保持 no-op 且 pass 不崩溃 |

### 测试命令

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/passes/test_hoist_dma_alias_ops.py \
  test/passes/test_registry.py \
  test/passes/pipeline/test_npu_demo_lowering.py \
  test/passes/test_pattern_public_api_docs.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate \
python3 -m expectation.pass.hoist_dma_alias_ops
```
