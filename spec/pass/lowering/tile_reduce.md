# tile_reduce.md

## 功能简介

- `tile-reduce` 是 tile family 中面向 `kernel.matmul` reduce 轴的公开 `ModulePass`。
- 它消费已有 `tile.analysis` 与 `tile.tile_exprs` 输入合同，在外层 elewise 轴和内层 reduce 轴生成 `symbol.for + dma.view + dma.fill + dma.alloc` 结构。
- 生成后的 `kernel.matmul` 与累加 `kernel.binary_elewise` 继续保留在同一 `func.func` 中，供后续 codegen 按 split-after-IR 结果处理。
- 公开 `ModulePass` 壳与 reduce rewrite helper 分层实现：registry 对接保留在 `kernel_gen.passes.lowering.tile_reduce`，真实 rewrite 落点位于 `kernel_gen.tile.reduce` 与 `kernel_gen.tile.common`。

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
- `功能实现`：
  - [`kernel_gen/passes/lowering/tile_reduce.py`](../../../kernel_gen/passes/lowering/tile_reduce.py)
  - [`kernel_gen/tile/reduce.py`](../../../kernel_gen/tile/reduce.py)
  - [`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
- `test`：
  - [`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)
  - [`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pass_manager.py`](../../../test/pass/test_pass_manager.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)

## 依赖

- tile family 索引页：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- tile-analysis 先行合同：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
- analysis helper 落点：[`kernel_gen/tile/analysis.py`](../../../kernel_gen/tile/analysis.py)
- 共享 helper 落点：[`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
- reduce rewrite 落点：[`kernel_gen/tile/reduce.py`](../../../kernel_gen/tile/reduce.py)
- 后端源码生成：[`spec/dsl/gen_kernel.md`](../../../spec/dsl/gen_kernel.md)
- pass registry：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- pass manager：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)

## 术语

- `tile-reduce`：reduce 轴切分公开入口，名称固定为 `"tile-reduce"`。
- `tile.analysis`：上游 analysis 生成的 operand 角色矩阵。
- `tile.tile_exprs`：当前 pass 写回的 tile 表达矩阵，形状必须与 `tile.analysis` 一致。
- `TILE_R*`：reduce 轴 tile 因子名称，类型为 `!symbol.int<"...">`。

## 目标

- 保持公开 pass 名称固定为 `tile-reduce`，并通过 registry 可构造。
- 仅处理已经完成 analysis 标注的 `kernel.matmul`。
- 对 matmul 生成两层输出 tile 循环与一层 reduce tile 循环。
- 对输出 tile 先执行 `dma.fill`，再在 reduce 循环内执行 tiled matmul 和累加。
- rewritten matmul 必须继续保留 `tile.analysis + tile.tile_exprs`，其中 matmul 的三个 operand 行均写入输出 tile 表达。
- 不生成历史桥接 op；tile 因子只通过 `tuner.param : !symbol.int<"...">` 与 `symbol.for` 公开。
- 公开构造入口固定为 `build_registered_pass("tile-reduce")`；具体 pass shell module path 不属于公开合同。

## 限制与边界

- 输入必须是 `builtin.module`。
- 当前只承诺单 block `func.func`。
- 输入函数必须已经满足 tile family 的 lowered kernel IR 合同。
- 缺少 `tile.analysis` 的 matmul 必须显式失败，不得静默跳过。
- `tile-reduce` 只负责 reduce 改写，不负责重新推导 analysis。
- 当前 pass 不承诺处理 `kernel.reduce`、`kernel.reduce_min` 或其他 reduce op。
- `kernel_gen.passes.lowering.tile_reduce` 只承担公开 `ModulePass` 壳与 registry 对接；共享 helper 与 reduce rewrite 实现依赖应落在 `kernel_gen.tile.reduce` 与 `kernel_gen.tile.common`。

## 公开接口

### `class TileReducePass(ModulePass)`

功能说明：

- 提供 `tile-reduce` 的公开 `ModulePass` 入口。
- 遍历 `builtin.module` 内的 `func.func`，对满足条件的 `kernel.matmul` 执行 reduce tile 改写。

参数说明：

- `name (str)`：固定为 `"tile-reduce"`。
- `apply(ctx, module)`：接收 xdsl `Context` 与 `ModuleOp`，通过就地改写体现结果。

使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.registry import build_registered_pass

build_registered_pass("tile-analysis").apply(Context(), module)
build_registered_pass("tile-reduce").apply(Context(), module)
```

注意事项：

- `apply(...)` 不返回新对象。
- 生成的 `tuner.param` 结果类型必须是 `!symbol.int<"...">`。
- `tile.tile_exprs` 必须与 `tile.analysis` 同形状。

返回与限制：

- 返回 `None`。
- 非 `builtin.module` 输入必须报错。

## 额外补充

### 输出合同：matmul reduce 改写

功能说明：

- 对 out-first `kernel.matmul(out, lhs, rhs)` 输入，输出必须保留单个 rewritten `kernel.matmul`。
- 输出 tile 循环使用 `TILE_D0/TILE_D1` 或对应输入分析给出的前缀；reduce 循环使用 `TILE_R0`。
- out tile 通过 `dma.view` 切出，并在 reduce 循环前执行一次 `dma.fill`。
- reduce 循环内切出 lhs/rhs tile，分配临时 tile memory，执行 tiled matmul，再用 `kernel.binary_elewise(kind = "add")` 累加到 out tile。

使用示例：

```mlir
%tile_d0 = tuner.param : !symbol.int<"TILE_D0">
%tile_d1 = tuner.param : !symbol.int<"TILE_D1">
%tile_r0 = tuner.param : !symbol.int<"TILE_R0">
symbol.for %d0 = %c0 to %m step %tile_d0 {
  symbol.for %d1 = %c0 to %n step %tile_d1 {
    "dma.fill"(%out_tile, %zero) : (...) -> ()
    symbol.for %r0 = %c0 to %k step %tile_r0 {
      "kernel.matmul"(%tmp, %lhs_tile, %rhs_tile) {
        tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]],
        tile.tile_exprs = [["TILE_D0", "TILE_D1"], ["TILE_D0", "TILE_D1"], ["TILE_D0", "TILE_D1"]]
      } : (...) -> ()
      "kernel.binary_elewise"(%out_tile, %tmp, %out_tile) {kind = "add"} : (...) -> ()
    }
  }
}
```

注意事项：

- `tile.tile_exprs` 记录的是 rewritten matmul 当前输出 tile 表达，而不是 reduce-only 表达。
- `TILE_R0` 只作为 reduce 循环步长与 reduce tile view 尺寸使用。
- 当前 pass 不额外生成 helper 函数或跨函数调用。

## 测试

- 测试文件：
  - [`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)
  - [`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pass_manager.py`](../../../test/pass/test_pass_manager.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)
- 执行命令：
  - `pytest -q test/pass/test_lowering_tile_reduce.py`
  - `pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py`
  - `pytest -q test/dsl/test_gen_kernel.py`
- 测试目标：
  - 验证 `TileReducePass` 可作为 `ModulePass` 由 registry 构造。
  - 验证 `tile-reduce` 对 `kernel.matmul` 生成输出轴与 reduce 轴切分结构。
  - 验证 rewritten `kernel.matmul` 继续保留 `tile.analysis + tile.tile_exprs`。
  - 验证 `gen_kernel(...)` 可消费 `tuner.param + symbol.for + dma.view` 组成的 split-after-IR 输入，而不依赖旧 mixed helper path。
