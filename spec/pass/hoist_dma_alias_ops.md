# hoist_dma_alias_ops

## 功能简介

- 定义 `hoist-dma-alias-ops` pass 的公开合同。
- 第一阶段只处理同一 block 内紧邻的 `dma.fill(%src, value)` 与 `%alias = dma.reshape(%src, ...)`。
- 合法改写为 `%alias = dma.reshape(%src, ...)` 位于 `dma.fill` 前，且 `dma.fill` target 改为 `%alias`。
- 实现必须用 xDSL pattern rewrite 基础设施组织第一阶段 rewrite；不得把本 pass 写成手工整段 ad hoc 遍历搬 op。
- 本 pass 不做 fold、combine、canonicalize，不跨 block、region 或控制流移动。

## API 列表

- `class HoistDmaAliasOpsPass(fold: bool = True)`
- `HoistDmaAliasOpsPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/hoist_dma_alias_ops.md`](../../spec/pass/hoist_dma_alias_ops.md)
- `功能实现`：[`kernel_gen/passes/hoist_dma_alias_ops.py`](../../kernel_gen/passes/hoist_dma_alias_ops.py)
- `test`：[`test/passes/test_hoist_dma_alias_ops.py`](../../test/passes/test_hoist_dma_alias_ops.py)

## 依赖

- `dma` 方言公开 op：
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- pass registry：
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
- npu-demo pipeline：
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)

## 目标

- 固定 pass 名称为 `hoist-dma-alias-ops`。
- 固定 canonical module path 为 `kernel_gen.passes.hoist_dma_alias_ops`。
- 固定 registry 构造入口 `build_registered_pass("hoist-dma-alias-ops")` 可返回 `HoistDmaAliasOpsPass`。
- 固定 `npu-demo-lowering` 两处 `SymbolLoopHoistPass` 后接入本 pass。

## 非目标

- 不新增 `hoist-ops` / `hoist_ops` pass 专属 option。
- 不公开 pattern getter。
- 不把 `HoistDmaAliasOpsPass` re-export 到 `kernel_gen.passes` package root。
- 不实现 `kernel.abs` / `kernel.relu`。
- 不实现 `dma.view` / `dma.subview` / `dma.deslice`。
- 不做 `dma.alloc -> dma.reshape` fold。
- 不做 `dma.view -> dma.reshape` combine。
- 不做 `dma.reshape -> dma.reshape` chain collapse。
- 不跨控制流移动。

## 行为

### 正例

输入：

```mlir
"dma.fill"(%flat, %zero) : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
%tile = "dma.reshape"(%flat, %c4, %c4)
  : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>,
     !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<4>>)
  -> !nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>
```

输出：

```mlir
%tile = "dma.reshape"(%flat, %c4, %c4)
  : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>,
     !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<4>>)
  -> !nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>
"dma.fill"(%tile, %zero) : (!nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
```

### no-op 边界

- `dma.fill` 与 `dma.reshape` 非紧邻时保持 no-op。
- `dma.reshape` source 不是前驱 `dma.fill` target 时保持 no-op。
- `dma.reshape` shape operand 不支配 `dma.fill` 时保持 no-op。
- `dma.fill` 与 `dma.reshape` 不在同一 block 时保持 no-op。
- `dma.alloc -> dma.reshape` 不 fold。
- `dma.reshape -> dma.reshape` 不 combine。
- 改写后 verifier 不通过时撤销本次改写并保持 module 原状。

## 公开导入

```python
from kernel_gen.passes.hoist_dma_alias_ops import HoistDmaAliasOpsPass
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

## pipeline

- `npu-demo-lowering` 两处 `SymbolLoopHoistPass()` 后必须紧跟 `HoistDmaAliasOpsPass()`。
- dump marker 验收只按 pass name 相对顺序，不绑定固定数字编号。

## 测试矩阵

| 用例 | 场景 | 断言 |
| --- | --- | --- |
| TC-HOIST-DMA-ALIAS-001 | 静态 `fill(flat); reshape(flat)` | `reshape` 上移到 `fill` 前，`fill` target 改为 alias result |
| TC-HOIST-DMA-ALIAS-002 | 动态 shape operand | shape 已支配 `fill` 时仍可上移 |
| TC-HOIST-DMA-ALIAS-003 | 非紧邻 | 保持 no-op |
| TC-HOIST-DMA-ALIAS-004 | source 不同 | 保持 no-op |
| TC-HOIST-DMA-ALIAS-005 | 跨 `scf.if` region | 保持 no-op |
| TC-HOIST-DMA-ALIAS-006 | 跨 `symbol.for` region | 保持 no-op |
| TC-HOIST-DMA-ALIAS-007 | shape 不支配 fill | 保持 no-op 且不产生部分改写 |
| TC-HOIST-DMA-ALIAS-008 | verifier 拒绝候选改写 | 撤销本次改写，module 文本保持原状，且不反复重试失败候选 |
| TC-HOIST-DMA-ALIAS-009 | `alloc -> reshape` | 不 fold |
| TC-HOIST-DMA-ALIAS-010 | `reshape -> reshape` | 不 combine |
| TC-HOIST-DMA-ALIAS-011 | registry | 默认构造、`fold=false`、未知专属 option 失败 |
| TC-HOIST-DMA-ALIAS-012 | pipeline | 两处 `symbol-loop-hoist -> hoist-dma-alias-ops -> cse -> canonicalize` |

## 验收命令

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q \
  test/passes/test_hoist_dma_alias_ops.py \
  test/passes/test_registry.py \
  test/passes/pipeline/test_npu_demo_lowering.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate \
python3 -m expectation.pass.hoist_dma_alias_ops
```
