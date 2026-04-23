# tile_analysis.md

## 功能简介

- `tile-analysis` 的唯一公开 pass 入口是 `build_registered_pass("tile-analysis")`。
- 该 pass 只负责写入 `tile.analysis` 与 `tile.tile_exprs`，不生成 `symbol.for`、`dma.view` 或其他 tile 改写结构。
- `kernel_gen.tile.analysis` 是 analysis logic 的唯一落点；旧 `kernel_gen.passes.lowering.tile_analysis` 只属于待清理消费者残留。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
- `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/tile/analysis.py`](../../../kernel_gen/tile/analysis.py)
  - [`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
- `test`：
  - [`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)

## 依赖

- Pass 管理抽象：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- Pass / pipeline 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `tile` 总览：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- `tuner.param` 与符号类型：[`spec/dialect/tuner.md`](../../../spec/dialect/tuner.md)
- 共享 helper 落点：[`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
- analysis logic 落点：[`kernel_gen/tile/analysis.py`](../../../kernel_gen/tile/analysis.py)

## 术语

- `tile-analysis`：tile family 的 analysis-only 入口。
- `tile.analysis`：analysis 阶段生成的 operand 角色矩阵。
- `tile.tile_exprs`：analysis 阶段生成的 tile 表达式占位信息。

## 目标

- 保持公开名字固定为 `tile-analysis`。
- 只写 `tile.analysis` 与 `tile.tile_exprs`。
- 不生成 `symbol.for`、`dma.view`、`dma.fill` 或其他 tile rewrite 结构。
- analysis 主逻辑固定落在 `kernel_gen.tile.analysis.apply_tile_analysis(module)`。
- 旧 `kernel_gen.passes.lowering.tile_analysis` 不再作为 pass caller、测试导入或字符串导入的合同入口。

## 限制与边界

- 输入必须是 `builtin.module`。
- 仅处理满足 tile analysis 输入合同的 lowered kernel IR。
- 若输入仍残留 `nn.*` 或 memory-return ABI，必须显式失败。
- 不承诺执行 tile rewrite，不承诺生成 loop/view/helper。
- helper / logic consumer 只能依赖 `kernel_gen.tile.analysis` 与 `kernel_gen.tile.common`；不得继续把 `kernel_gen.passes.lowering.tile_analysis` 当作导入目标。

## 公开接口

### `build_registered_pass("tile-analysis")`

功能说明：

- 构造 `tile-analysis` 的公开 `ModulePass` 实例。

参数说明：

- `"tile-analysis" (str)`：registry 中的公开 pass 名。

使用示例：

```python
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from kernel_gen.passes.registry import build_registered_pass

module = ModuleOp([])
build_registered_pass("tile-analysis").apply(Context(), module)
```

返回与限制：

- 返回实现 `ModulePass` 协议的 pass 对象。
- `apply(...)` 只执行 analysis 标注，不返回新对象。

## 测试

- 测试文件：
  - [`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)
- 执行命令：
  - `pytest -q test/pass/test_lowering_tile_analysis.py`
  - `pytest -q test/dsl/test_gen_kernel.py -k "tile_analysis or tile or gen_kernel"`
- 测试目标：
  - `tile-analysis` 可通过 registry 构造为 `ModulePass`。
  - `tile-analysis` 只写 `tile.analysis` 与 `tile.tile_exprs`。
  - 旧 `kernel_gen.passes.lowering.tile_analysis` 不再被测试或 codegen 文本当作直接导入路径。

## 额外补充

### `apply_tile_analysis(module)`

功能说明：

- 这是 `kernel_gen.tile.analysis` 中承接 analysis 主逻辑的实现落点，供 pass 壳或测试 helper 复用。

使用示例：

```python
from kernel_gen.tile.analysis import apply_tile_analysis

apply_tile_analysis(module)
```

注意事项：

- 这里定义的是 logic 落点，不改变公开 pass 名。
- 下游若需要直接导入 analysis logic，只能依赖 `kernel_gen.tile.analysis`，不能继续依赖旧 lowering module path。
