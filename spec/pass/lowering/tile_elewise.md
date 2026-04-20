# tile_elewise.md

## 功能简介

- `tile-elewise` 是 tile family 中面向 elementwise / broadcast / matmul / fc 的公开 `ModulePass`。
- 它消费已有的 `tile.analysis` 与 `tile.tile_exprs` 输入合同，按可切分的 elewise 轴生成 `symbol.for` + `dma.view` 结构。
- 它不会回退到旧 `TilePass` / `KernelSplitPass` 的桥接合同，不生成 `tile.step_value` / `kernel_split.tile_value`。
- 生成后的公开输出仍必须保留 `tile.analysis + tile.tile_exprs`，其中 `tile.tile_exprs` 仅在真实切分轴上写入 tile 名称。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/tile_elewise.md`](../../../spec/pass/lowering/tile_elewise.md)
- `功能实现`：[`kernel_gen/passes/lowering/tile_elewise.py`](../../../kernel_gen/passes/lowering/tile_elewise.py)
- `test`：[`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
- `expectation`：[`expectation/pass/tile/elewise`](../../../expectation/pass/tile/elewise)

## 依赖

- tile family 索引页：
  - [`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- tile-analysis 先行合同：
  - [`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
  - [`kernel_gen/passes/lowering/tile_analysis.py`](../../../kernel_gen/passes/lowering/tile_analysis.py)
- 后端源码生成：
  - [`spec/dsl/gen_kernel.md`](../../../spec/dsl/gen_kernel.md)
  - [`kernel_gen/dsl/gen_kernel.py`](../../../kernel_gen/dsl/gen_kernel.py)

## 目标

- 面向已经 lower 完成、且带有 `tile.analysis` / `tile.tile_exprs` 的单函数 IR，生成 elementwise / broadcast / matmul / fc 的 tile loop 改写。
- 保留 rewritten op 的 `tile.analysis` 与 `tile.tile_exprs`，让 expectation 能直接把它们当作验收资产。
- 以 `tuner.param : !symbol.int<"...">` 作为 tile 因子公开形态，供下游 `gen_kernel(...)` 直接读取。
- 保持 `symbol.for` 显式分块，不引入旧桥接 op 或函数抽取式 helper。

## 限制与边界

- 输入必须是 `builtin.module`，且内部函数必须满足当前 tile 输入合同。
- 仅接受单块 `func.func` 的 tile 输入。
- 不得生成 `tile.step_value`、`kernel_split.tile_value`、`kernel_split.symbol_literal` 或旧 `TilePass` 公开桥接文本。
- tile-elewise 只消费 elewise 轴；reduce 轴保持不切分。
- 生成结果必须可被 `expectation/pass/tile/elewise` 目录级黑盒复现。

## 公开接口

### `class TileElewisePass`

功能说明：

- 提供 `tile-elewise` 的公开 `ModulePass` 入口。
- 以当前 tile family 的公开输出合同为准，只对 `func.func` 进行 tile-elewise 改写。

使用示例：

```python
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from kernel_gen.passes.lowering.tile_elewise import TileElewisePass

TileElewisePass().apply(Context(), ModuleOp([]))
```

注意事项：

- `apply(...)` 不应调用 `module.verify()`，因为 tile-elewise 输出会保留 `tuner.param : !symbol.int<"...">` 这一公开合同。
- 若函数体中缺少 `tile.analysis`，应显式失败而不是静默回退到旧合同。

返回与限制：

- `apply(...)` 返回 `None`，通过就地改写 `ModuleOp` 体现结果。

## 验收口径

- `expectation/pass/tile/elewise` 是该子合同的黑盒真源。
- `pytest` 验证应覆盖 registry、pass manager、gen_kernel 与 tile-elewise 改写本身。
- 若需要确认行为、接口或验收边界，询问架构师。

## 相关文件

- `tile-analysis` 实现：[`kernel_gen/passes/lowering/tile_analysis.py`](../../../kernel_gen/passes/lowering/tile_analysis.py)
- `tile-elewise` 实现：[`kernel_gen/passes/lowering/tile_elewise.py`](../../../kernel_gen/passes/lowering/tile_elewise.py)
- `tile-elewise` 测试：[`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
- `tile-elewise` expectation：[`expectation/pass/tile/elewise`](../../../expectation/pass/tile/elewise)
