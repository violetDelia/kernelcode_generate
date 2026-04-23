# tile_elewise.md

## 功能简介

- `tile-elewise` 是 tile family 中面向 elementwise / broadcast / matmul / fc 的公开 `ModulePass`。
- 它消费已有的 `tile.analysis` 与 `tile.tile_exprs` 输入合同，按可切分的 elewise 轴生成 `symbol.for` + `dma.view` 结构。
- 它不会回退到历史桥接合同，不生成历史桥接 op。
- 生成后的公开输出仍必须保留 `tile.analysis + tile.tile_exprs`，其中 `tile.tile_exprs` 仅在真实切分轴上写入 tile 名称。
- 公开 `ModulePass` 壳与 rewrite helper 分层实现：registry 对接保留在 `kernel_gen.passes.lowering.tile_elewise`，真实 rewrite 落点位于 `kernel_gen.tile.elewise` 与 `kernel_gen.tile.common`。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/tile_elewise.md`](../../../spec/pass/lowering/tile_elewise.md)
- `功能实现`：
  - [`kernel_gen/passes/lowering/tile_elewise.py`](../../../kernel_gen/passes/lowering/tile_elewise.py)
  - [`kernel_gen/tile/elewise.py`](../../../kernel_gen/tile/elewise.py)
  - [`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
- `test`：
  - [`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)

## 依赖

- tile family 索引页：
  - [`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- tile-analysis 先行合同：
  - [`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
  - [`kernel_gen/tile/analysis.py`](../../../kernel_gen/tile/analysis.py)
- 共享 helper 落点：
  - [`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
- elewise rewrite 落点：
  - [`kernel_gen/tile/elewise.py`](../../../kernel_gen/tile/elewise.py)
- 后端源码生成：
  - [`spec/dsl/gen_kernel.md`](../../../spec/dsl/gen_kernel.md)
  - [`kernel_gen/dsl/gen_kernel.py`](../../../kernel_gen/dsl/gen_kernel.py)

## 目标

- 面向已经 lower 完成、且带有 `tile.analysis` / `tile.tile_exprs` 的单函数 IR，生成 elementwise / broadcast / matmul / fc 的 tile loop 改写。
- 保留 rewritten op 的 `tile.analysis` 与 `tile.tile_exprs`，让下游测试和 codegen 能直接读取该合同。
- 以 `tuner.param : !symbol.int<"...">` 作为 tile 因子公开形态，供下游 `gen_kernel(...)` 直接读取。
- 保持 `symbol.for` 显式分块，不引入旧桥接 op 或函数抽取式 helper。
- 公开构造入口固定为 `build_registered_pass("tile-elewise")`；具体 pass shell module path 不属于公开合同。

## 限制与边界

- 输入必须是 `builtin.module`，且内部函数必须满足当前 tile 输入合同。
- 仅接受单块 `func.func` 的 tile 输入。
- 不得生成历史桥接 op 或历史公开桥接文本。
- tile-elewise 只消费 elewise 轴；reduce 轴保持不切分。
- `kernel_gen.passes.lowering.tile_elewise` 只承担公开 `ModulePass` 壳与 registry 对接；共享 helper 与 rewrite 实现依赖应落在 `kernel_gen.tile.elewise` 与 `kernel_gen.tile.common`。

## 公开接口

### `class TileElewisePass(ModulePass)`

功能说明：

- 提供 `tile-elewise` 的公开 `ModulePass` 入口。
- 以当前 tile family 的公开输出合同为准，只对 `func.func` 进行 tile-elewise 改写。

参数说明：

- `name (str)`：固定为 `"tile-elewise"`。
- `apply(ctx, module)`：接收 xdsl `Context` 与 `ModuleOp`，通过就地改写体现结果。

使用示例：

```python
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from kernel_gen.passes.registry import build_registered_pass

build_registered_pass("tile-elewise").apply(Context(), ModuleOp([]))
```

注意事项：

- `apply(...)` 不应调用 `module.verify()`，因为 tile-elewise 输出会保留 `tuner.param : !symbol.int<"...">` 这一公开合同。
- 若函数体中缺少 `tile.analysis`，应显式失败而不是静默回退到旧合同。

返回与限制：

- `apply(...)` 返回 `None`，通过就地改写 `ModuleOp` 体现结果。

## 测试

- 测试文件：[`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
- 测试文件：[`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)
- 执行命令：`pytest -q test/pass/test_lowering_tile_elewise.py`
- 执行命令：`pytest -q test/dsl/test_gen_kernel.py -k "tile_elewise or gen_kernel"`
- 测试目标：
  - 验证 `TileElewisePass` 可作为 `ModulePass` 由 registry 构造。
  - 验证 `tile-elewise` 只消费已有 `tile.analysis + tile.tile_exprs` 的目标 op。
  - 验证输出继续保留 `tile.analysis + tile.tile_exprs`，并通过 `tuner.param + symbol.for + dma.view` 表达切分结果。
  - 验证 `gen_kernel(...)` 可继续消费 `tile-elewise` 的 split-after-IR 输出，而不依赖旧 mixed helper path。
