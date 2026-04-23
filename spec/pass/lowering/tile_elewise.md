# tile_elewise.md

## 功能简介

- `tile-elewise` 是 tile family 中面向 elementwise / broadcast / matmul / fc 的公开 `ModulePass`。
- 它消费已有 `tile.analysis` 与 `tile.tile_exprs`，按可切分的非 reduce 轴生成 `symbol.for + dma.view` 结构。
- `kernel_gen.tile.elewise` 是 elewise rewrite 的唯一 logic 落点；旧 `kernel_gen.passes.lowering.tile_elewise` 只属于待清理消费者残留。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/tile_elewise.md`](../../../spec/pass/lowering/tile_elewise.md)
- `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/tile/elewise.py`](../../../kernel_gen/tile/elewise.py)
  - [`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
- `test`：
  - [`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)

## 依赖

- tile family 总览：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- tile-analysis 先行合同：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
- 共享 helper 落点：[`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
- elewise rewrite 落点：[`kernel_gen/tile/elewise.py`](../../../kernel_gen/tile/elewise.py)
- 后端源码生成：[`spec/dsl/gen_kernel.md`](../../../spec/dsl/gen_kernel.md)

## 目标

- 面向已经 lower 完成、且带有 `tile.analysis / tile.tile_exprs` 的单函数 IR，生成 elementwise / broadcast / matmul / fc 的非 reduce 轴 tile rewrite。
- 保留 rewritten op 的 `tile.analysis` 与 `tile.tile_exprs`，让下游 `gen_kernel(...)` 直接读取该合同。
- 以 `tuner.param : !symbol.int<"...">` 作为 tile 因子公开形态，供下游 `gen_kernel(...)` 直接读取。
- 保持 `symbol.for` 显式分块，不恢复旧桥接 op、旧 helper function 或旧 module path。
- 旧 `kernel_gen.passes.lowering.tile_elewise` 不再作为 pass caller、测试导入或字符串导入的合同入口。

## 限制与边界

- 输入必须是 `builtin.module`，且内部函数满足当前 tile 输入合同。
- 仅接受单块 `func.func` 的 tile 输入。
- 不得生成历史桥接 op 或历史桥接文本。
- `tile-elewise` 只消费非 reduce 轴；reduce 轴保持不切分。
- helper / logic consumer 只能依赖 `kernel_gen.tile.elewise` 与 `kernel_gen.tile.common`；不得继续把 `kernel_gen.passes.lowering.tile_elewise` 当作导入目标。

## 公开接口

### `build_registered_pass("tile-elewise")`

功能说明：

- 构造 `tile-elewise` 的公开 `ModulePass` 实例。

参数说明：

- `"tile-elewise" (str)`：registry 中的公开 pass 名。

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

- 返回实现 `ModulePass` 协议的 pass 对象。
- 通过就地改写 `ModuleOp` 体现结果。

## 测试

- 测试文件：
  - [`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)
- 执行命令：
  - `pytest -q test/pass/test_lowering_tile_elewise.py`
  - `pytest -q test/dsl/test_gen_kernel.py -k "tile_elewise or tile or gen_kernel"`
- 测试目标：
  - `tile-elewise` 可通过 registry 构造为 `ModulePass`。
  - `tile-elewise` 只消费已有 `tile.analysis + tile.tile_exprs` 的目标 op。
  - 输出继续保留 `tile.analysis + tile.tile_exprs`，并通过 `tuner.param + symbol.for + dma.view` 表达切分结果。
  - `gen_kernel(...)` 可继续消费 `tile-elewise` 的 split-after-IR 输出，且不再依赖旧 `kernel_gen.passes.lowering.tile_elewise` 或 `kernel_gen.passes.lowering.tile` 字符串。

## 额外补充

### `apply_tile_elewise(module)`

功能说明：

- 这是 `kernel_gen.tile.elewise` 中承接 elewise rewrite 主逻辑的实现落点，供 pass 壳或测试 helper 复用。

使用示例：

```python
from kernel_gen.tile.elewise import apply_tile_elewise

apply_tile_elewise(module)
```

注意事项：

- 这里定义的是 logic 落点，不改变公开 pass 名。
- 下游若需要直接导入 rewrite logic，只能依赖 `kernel_gen.tile.elewise`，不能继续依赖旧 lowering module path。
