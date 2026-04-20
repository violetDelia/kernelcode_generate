# tile_analysis.md

## 功能简介

- 定义 `tile-analysis` 的公开 `ModulePass` 合同。
- 该 pass 只负责 analysis 标注，不生成 tile 改写结构。
- 目录级黑盒入口固定为 `python -m expectation.pass.tile.analysis`。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
- `功能实现`：[`kernel_gen/passes/lowering/tile_analysis.py`](../../../kernel_gen/passes/lowering/tile_analysis.py)
- `test`：[`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)

## 依赖

- Pass 管理抽象：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- Pass / pipeline 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `tile` 总览：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- `tuner.param` 与符号类型：[`spec/dialect/tuner.md`](../../../spec/dialect/tuner.md)
- `tile-analysis` expectation 入口：
  - [`expectation/pass/tile/analysis`](../../../expectation/pass/tile/analysis)

## 术语

- `tile-analysis`：tile family 的 analysis-only 公开入口。
- `tile.analysis`：analysis 阶段生成的角色矩阵。
- `tile.tile_exprs`：analysis 阶段生成的 tile 表达式占位信息。

## 目标

- 保持公开名字固定为 `tile-analysis`。
- 只写 `tile.analysis` 与 `tile.tile_exprs`。
- 不生成 `symbol.for`、`dma.view`、`tile.step_value` 或其他 tile 改写结构。
- 作为 `ModulePass` 通过 `apply(ctx, module)` 执行。

## 限制与边界

- 输入必须是 `builtin.module`。
- 仅处理满足 tile analysis 输入合同的单函数 IR。
- 若输入仍残留 `nn.*` 或 memory-return ABI，必须失败。
- 不承诺执行 tile 改写，不承诺生成 loop/view/helper。

## 公开接口

### `class TileAnalysisPass(ModulePass)`

功能说明：

- 执行 tile-analysis 的 analysis-only 阶段。

参数说明：

- `name (str)`：固定为 `"tile-analysis"`。

使用示例：

```python
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from kernel_gen.passes.lowering.tile_analysis import TileAnalysisPass

module = ModuleOp([])
TileAnalysisPass().apply(Context(), module)
```

返回与限制：

- `apply(...)` 只执行 analysis 标注，不返回新对象。

## 测试

- 测试文件：[`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
- 执行命令：
  - `pytest -q test/pass/test_lowering_tile_analysis.py`
  - `PYTHONPATH=. python -m expectation.pass.tile.analysis`
- 测试目标：
  - `TileAnalysisPass` 可作为 `ModulePass` 由 registry 构造。
  - `tile-analysis` 只写 `tile.analysis` 与 `tile.tile_exprs`。
  - 目录级 expectation 入口可稳定执行。
