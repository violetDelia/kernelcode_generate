# tile_reduce.md

## 功能简介

- 定义 `tile-reduce` 的公开 `ModulePass` 合同。
- 该 pass 只收口 `kernel.matmul` 的 reduction 轴，保留 `tile.analysis + tile.tile_exprs` 作为新合同证据。
- 目录级黑盒入口固定为 `python -m expectation.pass.tile.reduce`。

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
- `功能实现`：[`kernel_gen/passes/lowering/tile_reduce.py`](../../../kernel_gen/passes/lowering/tile_reduce.py)
- `test`：[`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)

## 依赖

- Pass 管理抽象：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- Pass / pipeline 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `tile` 总览：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- `tile-analysis` 子合同：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
- `tuner.param` 与符号类型：[`spec/dialect/tuner.md`](../../../spec/dialect/tuner.md)
- `tile-reduce` expectation 入口：
  - [`expectation/pass/tile/reduce`](../../../expectation/pass/tile/reduce)

## 术语

- `tile-reduce`：tile family 的 reduction-only 公开入口。
- `tile.analysis`：analysis 阶段生成的角色矩阵。
- `tile.tile_exprs`：analysis 阶段生成的 tile 表达式占位信息；`tile-reduce` 只会把 reduction 轴映射到具体 tile 名称。
- `tuner.param : !symbol.int<"...">`：`tile-reduce` 在 reduction loop 上使用的局部 tile bridge。

## 目标

- 保持公开名字固定为 `tile-reduce`。
- 只 lower `kernel.matmul` 的 reduction 轴，不修改 elewise 轴的公开合同。
- 仅消费 `tile.analysis + tile.tile_exprs`，并将 reduction 位置写成 `TILE_R*` 类 tile 名称。
- 生成 `symbol.for + dma.view + dma.fill` 的收口结构，且不再生成 `tile.step_value` / `kernel_split.tile_value`。
- 作为 `ModulePass` 通过 `apply(ctx, module)` 执行。

## 限制与边界

- 输入必须是 `builtin.module`。
- 仅处理已完成 lowering 的单函数 IR；若仍残留 `nn.*`、memory-return ABI 或未完成的 matmul analysis，则必须失败。
- 若 `kernel.matmul` 已经带有非空 `tile.tile_exprs`，视为已经被收口，必须失败。
- 不承诺执行 `dma.broadcast` / `kernel.binary_elewise` 的结构改写。

## 公开接口

### `class TileReducePass(ModulePass)`

功能说明：

- 执行 tile-reduce 的 reduction-only 阶段。

参数说明：

- `name (str)`：固定为 `"tile-reduce"`。

使用示例：

```python
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from kernel_gen.passes.lowering.tile_reduce import TileReducePass

module = ModuleOp([])
TileReducePass().apply(Context(), module)
```

返回与限制：

- `apply(...)` 只执行 reduction 收口，不返回新对象。

## 测试

- 测试文件：[`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)
- 执行命令：
  - `pytest -q test/pass/test_lowering_tile_reduce.py`
  - `PYTHONPATH=. python -m expectation.pass.tile.reduce`
- 测试目标：
  - `TileReducePass` 可作为 `ModulePass` 由 registry 构造。
  - `tile-reduce` 只 lower `kernel.matmul` 的 reduction 轴，并保留 `tile.analysis + tile.tile_exprs`。
  - `tuner.param` 使用 `!symbol.int<"...">` 黑盒口径。
  - 目录级 expectation 入口可稳定执行。
