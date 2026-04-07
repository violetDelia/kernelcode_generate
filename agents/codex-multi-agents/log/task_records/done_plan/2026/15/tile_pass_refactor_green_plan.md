# tile_pass_refactor_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260407-tile-pass-s1` | `agents/codex-multi-agents/log/task_records/2026/15/20260407-tile-pass-s1.md` | `已合并收口（merge_commit=7c4c86c；T-20260407-c4444a0c，李白；push(main)=exit=0）` |

## 计划目标

- 将现有 `KernelSplitPass` 重构为 `TilePass`。
- 公开名称、Python 入口、spec、test、expectation、pass 顺序说明统一改为 `tile` / `TilePass`。
- 取消通过函数属性 `kernel_split = { axis, tile }` 触发切分的做法。
- 改为由 `TilePass` 按算子类型插入或复用所需的 `tuner.param`，并将其桥接得到的 `symbol.int` 作为 `symbol.for` 的 `step`。
- `elementwise` 按 memory 的 rank 自动展开切分维度：`rank = N` 就需要 `N` 个 tile 参数，并生成 `N` 层 `symbol.for`。
- `matmul` 单独按 `M/N/K` 三个维度切分，要求存在三组 tile 参数，并生成三层循环。
- `reduce` 在本次重构中显式标为暂不支持。
- 仍保持单函数内显式切分，不新建函数，不新增 `func.call`，中间值继续沿用 SSA / carry memory 的现有承接口径。

## 当前基线（2026-04-07）

- 当前仓库已有：
  - [`spec/pass/lowering/kernel_split.md`](spec/pass/lowering/kernel_split.md)
  - [`kernel_gen/passes/lowering/kernel_split.py`](kernel_gen/passes/lowering/kernel_split.py)
  - [`test/pass/test_lowering_kernel_split.py`](test/pass/test_lowering_kernel_split.py)
  - [`expectation/pass/lowing/kernel_split.py`](expectation/pass/lowing/kernel_split.py)
- 当前公开合同依赖函数属性 `kernel_split = { axis = <i64>, tile = "<TILE_NAME>" }`。
- 当前 `tuner.param` 只负责提供 tile 名称对应的符号值，本身不是“从 `kernel.*` 直接扩成 tile loop + view”的公开合同。
- 当前实现没有公开“按 memory rank 自动生成多层 tile loop”的合同。
- 当前实现没有公开“`matmul` 按 `M/N/K` 三维切分”的合同。

## 讨论结论

### 计划目标

- 这次重构只做两件事：
  1. `kernel_split` 全量改名为 `tile`
  2. 切分步长改由 `TilePass` 插入或复用的 `tuner.param` 驱动，不再依赖 `kernel_split` 属性
- 这次重构的切分规则固定为：
  - `elementwise`：按 memory rank 切分
  - `matmul`：按 `M/N/K` 切分
  - `reduce`：暂不支持
- 不把本次重构扩成“自动选择最优切分策略”的专题。
- 不把本次重构扩成“多轴 tile / 自动并行 / 自动 hierarchy / 自动 double buffer”的专题。

### 是否有更合理的方案

- 不采用“保留 `kernel_split` 旧名，再额外并存 `tile` 新名”的方案。
  - 原因：双名称会让 spec、测试、错误短语和 expectation 长期两套口径并存，后续维护成本高。
- 不采用“继续用属性声明 axis/tile，只把 pass 名字改掉”的方案。
  - 原因：这不能满足“由 `tuner.param` 默认驱动 step”的目标，只是表面改名。
- 不采用“pass 参数直接传 tile 大小”的方案。
  - 原因：这会绕开 `tuner.param`，与当前项目对调参入口的公开口径相冲突。
- 不采用“由调用方再额外显式给 axis 列表”的方案。
  - 原因：`elementwise` 和 `matmul` 已经有稳定的结构规则，继续把 axis 暴露给调用方只会让公开接口变复杂。

### 依赖

- 输入前提：
  - [`spec/pass/lowering/nn_to_kernel.md`](spec/pass/lowering/nn_to_kernel.md)
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/dialect/tuner.md`](spec/dialect/tuner.md)
- 推荐顺序：
  - `LowerNnToKernelPass -> BufferResultsToOutParamsPass -> TilePass -> SymbolLoopHoistPass -> LowerDmaMemoryHierarchyPass`
- 下游需要同步改名或引用更新的内容：
  - [`spec/pass/lowering/kernel_split.md`](spec/pass/lowering/kernel_split.md)
  - [`kernel_gen/passes/lowering/kernel_split.py`](kernel_gen/passes/lowering/kernel_split.py)
  - [`test/pass/test_lowering_kernel_split.py`](test/pass/test_lowering_kernel_split.py)
  - [`expectation/pass/lowing/kernel_split.py`](expectation/pass/lowing/kernel_split.py)
  - [`ARCHITECTURE/plan/symbol_loop_hoist_green_plan.md`](ARCHITECTURE/plan/symbol_loop_hoist_green_plan.md)

### 验证合理性

- 成功路径必须同时验证：
  - pass 名称已改为 `tile`
  - 输入可以只有目标 `kernel.*` op，不要求事先写好 `tuner.param`
  - after IR 中出现由 `tuner.param` 驱动的 `symbol.for step`
  - after IR 中不再依赖 `kernel_split` 属性
  - after IR 仍保持单函数
  - `elementwise rank = N` 时，after IR 中出现 `N` 层循环
  - `matmul` 时，after IR 中出现 `M/N/K` 三层循环
  - `elementwise` 成功路径中，after IR 至少出现对应输入/输出的 `dma.view`，并在 loop body 内消费这些 view 版本
- 失败路径必须明确验证：
  - 缺少足够的 tile 参数生成条件
  - `tuner.param` 候选不唯一
  - `elementwise` 参与切分的 memory rank 不一致
  - 输入仍残留 `nn.*`
  - 非法中间值承接 / dead carry memory
  - `reduce` 进入 `TilePass` 时显式报不支持
- expectation 需要打印 before/after IR，直接看到切分前后变化。
- 测试命令按固定顺序执行，并覆盖这几类场景：
  1. `pytest -q test/pass/test_lowering_tile.py -k "elementwise or matmul or reduce or duplicate or nn_input or dead_carry"`
  2. `pytest -q test/pass/test_pass_manager.py -k "tile or symbol_loop_hoist or dma_memory_hierarchy"`
  3. `PYTHONPATH=. python expectation/pass/lowing/tile.py`
  4. `PYTHONPATH=. python expectation/pass/lowing/tile/__main__.py`

### 可维护性

- 统一只保留 `tile` 这一个公开名，避免旧名长期残留。
- 错误短语统一从 `KernelSplit*` 迁移到 `TilePass*`，后续新增 case 继续沿用这一组前缀。
- expectation 与 pytest 都按新名重建，避免“代码已改名但验证资产仍沿用旧名”的混乱状态。
- `elementwise` 与 `matmul` 分支规则固定写入 spec，后续新增算子先归类到这两类之一；不属于这两类的先显式拒绝。

## 固定合同（草案）

- pass 名称：`tile`
- Python 入口：`TilePass`
- spec 文件：`spec/pass/lowering/tile.md`
- expectation 文件：`expectation/pass/lowing/tile.py`
- test 文件：`test/pass/test_lowering_tile.py`
- 作用对象：已完成 `nn -> kernel` 与 out-param 收口的单函数 IR
- `tuner.param` 是 tile step 的唯一公开来源；`TilePass` 负责插入或复用这些参数
- 不再读取 `kernel_split = { axis, tile }` 属性
- `elementwise`：按代表性 memory 的 rank 切分；`rank = N` 需要 `N` 个互不重复的 tile 参数，生成 `N` 层循环
- `matmul`：按 `M/N/K` 三个维度切分；需要 `TILE_M / TILE_N / TILE_K`
- 同一个函数内，每个被切分维度只能绑定一个唯一的 tile 参数名；禁止重复复用同名 `tuner.param` 充当多个维度的 step
- `elementwise` 成功重写后的最小结构为：`tuner.param* -> tile.step_value* -> symbol.for* -> dma.view(lhs/rhs/out) -> kernel.add`
- `matmul` 成功重写后的最小结构为：`tuner.param* -> tile.step_value* -> symbol.for* -> dma.view(lhs/rhs/out) -> kernel.matmul`
- `reduce`：暂不支持，进入 pass 必须显式报错
- 切分后仍保持单函数合同
- 中间值继续沿用现有 `SSA / carry memory` 规则，不在本次重构中改变
- 失败短语固定为：
  - `TilePassRankMismatch`
  - `TilePassDuplicateTileParam`
  - `TilePassUnsupportedOp`
  - `TilePassRequiresLoweredKernelIR`
  - `TilePassDeadCarryMemory`

## 前后 IR 示例（目标形态草案）

### 示例 1：成功路径

输入 IR：

```text
func.func @add_kernel(%lhs: !nn.memory<[B, M], i32, #layout, #GM>,
                      %rhs: !nn.memory<[B, M], i32, #layout, #GM>,
                      %out: !nn.memory<[B, M], i32, #layout, #GM>) {
  %0 = kernel.add %lhs, %rhs outs(%out)
  func.return
}
```

预期输出：

```text
func.func @add_kernel(%lhs: !nn.memory<[B, M], i32, #layout, #GM>,
                      %rhs: !nn.memory<[B, M], i32, #layout, #GM>,
                      %out: !nn.memory<[B, M], i32, #layout, #GM>) {
  %tile_b = tuner.param : !symbol.dim<"TILE_B">
  %tile_m = tuner.param : !symbol.dim<"TILE_M">
  %step_b = tile.step_value %tile_b : !symbol.dim<"TILE_B"> -> !symbol.int<"TILE_B">
  %step_m = tile.step_value %tile_m : !symbol.dim<"TILE_M"> -> !symbol.int<"TILE_M">
  symbol.for %ib = %lb_b to %ub_b step %step_b : ... {
    symbol.for %im = %lb_m to %ub_m step %step_m : ... {
      %lhs_tile = dma.view %lhs [...] -> !nn.memory<[tile_b, tile_m], i32, #layout, #GM>
      %rhs_tile = dma.view %rhs [...] -> !nn.memory<[tile_b, tile_m], i32, #layout, #GM>
      %out_tile = dma.view %out [...] -> !nn.memory<[tile_b, tile_m], i32, #layout, #GM>
      %1 = kernel.add %lhs_tile, %rhs_tile outs(%out_tile)
    }
  }
  func.return
}
```

说明：

- `step` 由 `tuner.param` 驱动。
- `elementwise rank = 2`，因此生成两层循环。
- `TILE_B` 与 `TILE_M` 必须是两个不同的参数名，不能复用。
- loop body 至少要把 `lhs/rhs/out` 重写成 tile 对应的 `dma.view` 后再做 `kernel.add`。
- 不再依赖 `kernel_split` 属性。
- 仍保持单函数内显式 `symbol.for`。

### 示例 2：`matmul` 成功路径

输入 IR：

```text
func.func @matmul_kernel(%lhs: !nn.memory<[M, K], f16, #layout, #GM>,
                         %rhs: !nn.memory<[K, N], f16, #layout, #GM>,
                         %out: !nn.memory<[M, N], f16, #layout, #GM>) {
  %0 = kernel.matmul %lhs, %rhs outs(%out)
  func.return
}
```

预期输出：

```text
func.func @matmul_kernel(...) {
  %tile_m = tuner.param : !symbol.dim<"TILE_M">
  %tile_n = tuner.param : !symbol.dim<"TILE_N">
  %tile_k = tuner.param : !symbol.dim<"TILE_K">
  %step_m = tile.step_value %tile_m : !symbol.dim<"TILE_M"> -> !symbol.int<"TILE_M">
  %step_n = tile.step_value %tile_n : !symbol.dim<"TILE_N"> -> !symbol.int<"TILE_N">
  %step_k = tile.step_value %tile_k : !symbol.dim<"TILE_K"> -> !symbol.int<"TILE_K">
  symbol.for %im = %lb_m to %ub_m step %step_m : ... {
    symbol.for %in = %lb_n to %ub_n step %step_n : ... {
      symbol.for %ik = %lb_k to %ub_k step %step_k : ... {
        %lhs_tile = dma.view %lhs [...] -> !nn.memory<[tile_m, tile_k], f16, #layout, #GM>
        %rhs_tile = dma.view %rhs [...] -> !nn.memory<[tile_k, tile_n], f16, #layout, #GM>
        %out_tile = dma.view %out [...] -> !nn.memory<[tile_m, tile_n], f16, #layout, #GM>
        %1 = kernel.matmul %lhs_tile, %rhs_tile outs(%out_tile)
      }
    }
  }
  func.return
}
```

说明：

- `matmul` 固定按 `M/N/K` 三维切分。
- `TILE_M / TILE_N / TILE_K` 必须互不重复。
- loop body 至少要把 `lhs/rhs/out` 重写成 tile 对应的 `dma.view` 后再做 `kernel.matmul`。
- 不再读取 `kernel_split` 属性。

### 示例 3：失败路径（无法推导 elementwise tile 维度）

输入 IR：

```text
func.func @add_kernel(%lhs: !nn.memory<[B, M], i32, #layout, #GM>,
                      %rhs: !nn.memory<[B], i32, #layout, #GM>,
                      %out: !nn.memory<[B, M], i32, #layout, #GM>) {
  %0 = kernel.add %lhs, %rhs outs(%out)
  func.return
}
```

预期输出：

```text
TilePassRankMismatch: function add_kernel requires the same memory rank across tiled elementwise operands
```

### 示例 4：失败路径（`reduce` 暂不支持）

输入 IR：

```text
func.func @reduce_kernel(%x: !nn.memory<[B, M], f32, #layout, #GM>,
                         %out: !nn.memory<[B], f32, #layout, #GM>) {
  %tile_b = tuner.param : !symbol.dim<"TILE_B">
  %tile_m = tuner.param : !symbol.dim<"TILE_M">
  %0 = kernel.reduce_sum %x outs(%out) {axis = 1}
  func.return
}
```

预期输出：

```text
TilePassUnsupportedOp: reduce family is not supported by TilePass yet
```

### 示例 5：失败路径（tile 参数重名）

输入 IR：

```text
func.func @add_kernel(%lhs: !nn.memory<[B, M], i32, #layout, #GM>,
                      %rhs: !nn.memory<[B, M], i32, #layout, #GM>,
                      %out: !nn.memory<[B, M], i32, #layout, #GM>) {
  %tile_b_0 = tuner.param : !symbol.dim<"TILE_B">
  %tile_b_1 = tuner.param : !symbol.dim<"TILE_B">
  %0 = kernel.add %lhs, %rhs outs(%out)
  func.return
}
```

预期输出：

```text
TilePassDuplicateTileParam: function add_kernel requires unique tuner.param names per tiled axis
```

### 示例 6：失败路径（输入仍残留 `nn.*`）

输入 IR：

```text
func.func @nn_add_kernel(%lhs: !nn.memory<[B, M], i32, #layout, #GM>,
                         %rhs: !nn.memory<[B, M], i32, #layout, #GM>,
                         %out: !nn.memory<[B, M], i32, #layout, #GM>) {
  %0 = nn.add %lhs, %rhs outs(%out)
  func.return
}
```

预期输出：

```text
TilePassRequiresLoweredKernelIR: function nn_add_kernel still contains nn.* input
```

### 示例 7：失败路径（dead carry memory）

输入 IR：

```text
func.func @bad_tile_kernel(%lhs: !nn.memory<[B, M], i32, #layout, #GM>,
                           %rhs: !nn.memory<[B, M], i32, #layout, #GM>,
                           %out: !nn.memory<[B, M], i32, #layout, #GM>) {
  %tmp = kernel.add %lhs, %rhs outs(%out)
  %unused = dma.alloc (%c1, %c1) : !nn.memory<[1, 1], i32, #layout, #GM>
  func.return
}
```

预期输出：

```text
TilePassDeadCarryMemory: function bad_tile_kernel contains dead carry memory after tiling
```

## 计划任务

### `S1`

- `任务类型`：`收口任务（spec+实现+测试+expectation）`
- `任务目标`：
  - 新增 [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
  - 新增 [`kernel_gen/passes/lowering/tile.py`](kernel_gen/passes/lowering/tile.py)
  - 新增 [`test/pass/test_lowering_tile.py`](test/pass/test_lowering_tile.py)
  - 新增 [`expectation/pass/lowing/tile.py`](expectation/pass/lowing/tile.py)
  - 新增 [`expectation/pass/lowing/tile/__main__.py`](expectation/pass/lowing/tile/__main__.py)
  - 将现有 `kernel_split` 逻辑整体迁移到 `tile`
- `重点内容`：
  - 统一从 `kernel_split` 改名到 `tile`
  - 写清 `TilePass` 如何插入或复用 `tuner.param -> symbol.int step`
  - `elementwise` 按 memory rank 生成多层循环
  - `matmul` 按 `M/N/K` 生成三层循环
  - `elementwise` / `matmul` 都要求在 loop body 中先构造 tile 对应的 `dma.view`
  - 每个被切分维度必须绑定唯一 tile 参数名
  - `reduce` 显式报不支持
  - 成功路径与失败路径都按新错误短语收口
  - `nn.*` 输入与 dead carry memory 都要在 pytest 和 expectation 中绑定固定短语
- `不采用的做法`：
  - 不保留双名称长期并存
  - 不保留属性触发作为完成态
  - 不把 tile size 改为 pass 参数或隐藏全局配置
- `示例代码`：

```python
from kernel_gen.passes.lowering.tile import TilePass

module = TilePass().run(module)
```

- `预期输出`：

```text
命中: class TilePass(Pass)
命中: tuner.param-derived tile step
命中: elementwise rank=2 -> two nested symbol.for
命中: elementwise rank=2 -> three dma.view before kernel.add
命中: elementwise rank mismatch -> TilePassRankMismatch
命中: matmul -> M/N/K nested symbol.for
命中: matmul -> three dma.view before kernel.matmul
命中: duplicate tile param -> TilePassDuplicateTileParam
命中: reduce -> TilePassUnsupportedOp
命中: nn.* input -> TilePassRequiresLoweredKernelIR
命中: dead carry memory -> TilePassDeadCarryMemory
禁止: kernel_split = { axis = ..., tile = ... } 作为公开触发条件
```

- `必须测试通过项目`：
  1. `pytest -q test/pass/test_lowering_tile.py -k "elementwise or matmul or reduce or duplicate or nn_input or dead_carry"`
  2. `pytest -q test/pass/test_pass_manager.py -k "tile or symbol_loop_hoist or dma_memory_hierarchy"`
  3. `PYTHONPATH=. python expectation/pass/lowing/tile.py`
  4. `PYTHONPATH=. python expectation/pass/lowing/tile/__main__.py`
- `完成标准`：
  - 新 spec、实现、pytest、expectation 同时切到 `tile`
  - `elementwise` 与 `matmul` 两类规则都能独立验证
  - 重复 tile 参数名的拒绝路径稳定
  - `reduce`、`nn.*` 输入、dead carry memory 的拒绝路径稳定
  - pass 顺序说明和 `test_pass_manager.py` 一致
  - 旧 `kernel_split` 公开口径不再作为主合同

## 评审摘要

- 评审结论：`已评审通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 评审时间：`2026-04-07`
- 六项摘要：
  - `目标`：通过；`KernelSplitPass -> TilePass` 的改名与行为收口清晰，公开合同统一到 `tile / TilePass`。
  - `边界`：通过；去掉属性触发，`elementwise` 按 memory rank 切分，`matmul` 按 `M/N/K` 切分，`reduce` 暂不支持，且保持单函数。
  - `依赖顺序`：通过；`LowerNnToKernelPass -> BufferResultsToOutParamsPass -> TilePass -> SymbolLoopHoistPass -> LowerDmaMemoryHierarchyPass` 自洽。
  - `验证命令`：通过；已补固定顺序，覆盖 `test_lowering_tile`、`test_pass_manager`、`expectation/pass/lowing/tile.py` 与目录入口。
  - `失败短语`：通过；`TilePassRankMismatch / TilePassDuplicateTileParam / TilePassUnsupportedOp / TilePassRequiresLoweredKernelIR / TilePassDeadCarryMemory` 已固定。
  - `不可改文件`：通过；沿用仓库默认 `immutable` 规则，无额外豁免。

## 双架构师最终验收摘要（2026-04-07）

- 最终验收结论：`通过（可归档 done_plan）`。
- 核对依据：
  - `S1` 已合并收口：`merge_commit=7c4c86c`。
  - `agents/codex-multi-agents/log/task_records/2026/15/20260407-tile-pass-s1.md` 显示最终复审通过。
  - `pytest -q test/pass/test_lowering_tile.py -k "elementwise or matmul or reduce or duplicate or nn_input or dead_carry"`、`pytest -q test/pass/test_pass_manager.py -k "tile or symbol_loop_hoist or dma_memory_hierarchy"` 均 `exit=0`。
  - `PYTHONPATH=. python expectation/pass/lowing/tile.py`、`PYTHONPATH=. python expectation/pass/lowing/tile/__main__.py` 均 `exit=0`；`test_lowering_kernel_split` 兼容入口验证通过。
- 阻断项：`无`。
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`。

## 文档信息

- 创建者：`大闸蟹`
- 最后修改人：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/tile_pass_refactor_green_plan.md`](ARCHITECTURE/plan/tile_pass_refactor_green_plan.md)
- `spec`：
  - [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
  - [`spec/dialect/tuner.md`](spec/dialect/tuner.md)
  - 迁移参考：[`spec/pass/lowering/kernel_split.md`](spec/pass/lowering/kernel_split.md)
- `test`：
  - [`test/pass/test_lowering_tile.py`](test/pass/test_lowering_tile.py)
  - [`test/pass/test_pass_manager.py`](test/pass/test_pass_manager.py)
  - 迁移参考：[`test/pass/test_lowering_kernel_split.py`](test/pass/test_lowering_kernel_split.py)
- `功能实现`：
  - [`kernel_gen/passes/lowering/tile.py`](kernel_gen/passes/lowering/tile.py)
  - 迁移参考：[`kernel_gen/passes/lowering/kernel_split.py`](kernel_gen/passes/lowering/kernel_split.py)
