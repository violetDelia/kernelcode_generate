# tile.md

## 功能简介

- 本页定义 tile family 在 `S7` 后的总合同：对外 pass 入口只保留 `build_registered_pass("tile-analysis")`、`build_registered_pass("tile-elewise")`、`build_registered_pass("tile-reduce")`。
- `kernel_gen.tile.common`、`kernel_gen.tile.analysis`、`kernel_gen.tile.elewise`、`kernel_gen.tile.reduce` 是 tile family 的唯一 logic/helper 落点；旧 `kernel_gen.passes.lowering.tile*` 只属于待清理消费者残留。
- `tile-analysis` 只写 `tile.analysis + tile.tile_exprs`；`tile-elewise` 与 `tile-reduce` 在该输入上继续生成 split-after-IR 结构，供 `gen_kernel(...)` 消费。
- 本页同时写清旧 module path、旧 importlib 字符串、旧 coverage include-module 的退场范围，供下游 `build/review` 直接按文档清理。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/tile/common.py`](../../../kernel_gen/tile/common.py)
  - [`kernel_gen/tile/analysis.py`](../../../kernel_gen/tile/analysis.py)
  - [`kernel_gen/tile/elewise.py`](../../../kernel_gen/tile/elewise.py)
  - [`kernel_gen/tile/reduce.py`](../../../kernel_gen/tile/reduce.py)
- `test`：
  - [`test/pass/test_lowering_tile.py`](../../../test/pass/test_lowering_tile.py)
  - [`test/pass/test_lowering_tile_private_helpers.py`](../../../test/pass/test_lowering_tile_private_helpers.py)
  - [`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
  - [`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
  - [`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)
  - [`test/script/test_python_coverage_check.py`](../../../test/script/test_python_coverage_check.py)

## 依赖

- Pass 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- Pass 执行器：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- tile-analysis 子合同：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
- tile-elewise 子合同：[`spec/pass/lowering/tile_elewise.md`](../../../spec/pass/lowering/tile_elewise.md)
- tile-reduce 子合同：[`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
- 函数级 codegen：[`spec/dsl/gen_kernel.md`](../../../spec/dsl/gen_kernel.md)

## 术语

- `tile family`：由 `tile-analysis`、`tile-elewise`、`tile-reduce` 组成的 lowering pass family。
- `tile.analysis`：tile-analysis 写入并由后续 tile pass 消费的 operand 角色矩阵。
- `tile.tile_exprs`：tile-analysis 写入并由后续 tile pass 更新的 tile 表达矩阵。
- `split-after-IR`：以 `tuner.param + symbol.for + dma.view` 为主的 after-IR 形态，供 `gen_kernel(...)` 直接消费。
- `tile helper`：位于 `kernel_gen.tile.common` 的共享错误、输入校验、plan、loop、view 与 rewrite helper。

## 目标

- 对外公开 pass 名只保留 `tile-analysis`、`tile-elewise`、`tile-reduce`。
- `tile-analysis` 的唯一职责是写入 `tile.analysis + tile.tile_exprs`。
- `tile-elewise` 负责 elementwise / broadcast / matmul / fc 的非 reduce 轴切分。
- `tile-reduce` 负责 `kernel.matmul` 的 reduce 轴切分与累加结构。
- tile family 的共享 helper 只保留在 `kernel_gen.tile.common`；analysis / elewise / reduce logic 分别落在 `kernel_gen.tile.analysis`、`kernel_gen.tile.elewise`、`kernel_gen.tile.reduce`。
- `gen_kernel(...)` 只消费 tile family 产出的 split-after-IR 结果，不重新推导 tile family analysis。
- `build/review` 需要同步清理旧 `kernel_gen.passes.lowering.tile*` 导入、旧字符串导入、旧 coverage include-module 口径。

## 限制与边界

- 本页不重新定义三个子 pass 的完整改写规则，具体行为以对应子 spec 为准。
- tile family 不新增新 pass 名，不恢复旧 `TilePass / KernelSplitPass / tile.step_value / kernel_split.tile_value` 文本。
- pass caller 的唯一公开入口是 registry 名称；`kernel_gen.tile.*` 只是 logic/helper 落点，不是新的 pass 名字。
- helper / rewrite consumer 只能依赖 `kernel_gen.tile.common`、`kernel_gen.tile.analysis`、`kernel_gen.tile.elewise`、`kernel_gen.tile.reduce`。
- 下列旧路径在 `S7 build` 完成后必须退出 tile family 的消费者矩阵：
  - `kernel_gen.passes.lowering.tile`
  - `kernel_gen.passes.lowering.tile_analysis`
  - `kernel_gen.passes.lowering.tile_elewise`
  - `kernel_gen.passes.lowering.tile_reduce`
- `test/pass/test_lowering_tile.py`、`test/dsl/test_gen_kernel.py`、`test/script/test_python_coverage_check.py` 中与 tile family 相关的 module path assert、`importlib.import_module(...)` 字符串与 `--include-module` 口径，必须与上述新路径保持一致。

## 公开接口

### `build_registered_pass("tile-analysis")`

功能说明：

- 构造 tile family 的 analysis-only `ModulePass`。

参数说明：

- `"tile-analysis" (str)`：registry 中的公开 pass 名。

使用示例：

```python
from kernel_gen.passes.registry import build_registered_pass

tile_analysis = build_registered_pass("tile-analysis")
```

返回与限制：

- 返回实现 `ModulePass` 协议的 pass 对象。
- 只写 `tile.analysis + tile.tile_exprs`，不生成 `symbol.for` 或 `dma.view`。

### `build_registered_pass("tile-elewise")`

功能说明：

- 构造 tile family 的 elewise-axis `ModulePass`。

参数说明：

- `"tile-elewise" (str)`：registry 中的公开 pass 名。

使用示例：

```python
tile_elewise = build_registered_pass("tile-elewise")
```

返回与限制：

- 返回实现 `ModulePass` 协议的 pass 对象。
- 只处理已有 analysis 结果且尚未切分的 elementwise / broadcast / matmul / fc。

### `build_registered_pass("tile-reduce")`

功能说明：

- 构造 tile family 的 reduce-axis `ModulePass`。

参数说明：

- `"tile-reduce" (str)`：registry 中的公开 pass 名。

使用示例：

```python
tile_reduce = build_registered_pass("tile-reduce")
```

返回与限制：

- 返回实现 `ModulePass` 协议的 pass 对象。
- 只处理已有 analysis 结果且尚未切分的 `kernel.matmul` reduce family op。

## 测试

- 测试文件：
  - [`test/pass/test_lowering_tile.py`](../../../test/pass/test_lowering_tile.py)
  - [`test/pass/test_lowering_tile_private_helpers.py`](../../../test/pass/test_lowering_tile_private_helpers.py)
  - [`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
  - [`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
  - [`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)
  - [`test/script/test_python_coverage_check.py`](../../../test/script/test_python_coverage_check.py)
- 执行命令：
  - `pytest -q test/pass/test_lowering_tile.py test/pass/test_lowering_tile_private_helpers.py`
  - `pytest -q test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py`
  - `pytest -q test/dsl/test_gen_kernel.py -k "tile or gen_kernel"`
  - `pytest -q test/script/test_python_coverage_check.py`
- 合同验收资产：
  - [`expectation/pass/tile`](../../../expectation/pass/tile)
- 测试目标：
  - 验证三个公开 pass 名都能通过 registry 构造。
  - 验证 tile family 的 logic/helper 落点已经转到 `kernel_gen.tile.*`。
  - 验证旧 `kernel_gen.passes.lowering.tile*` 不再出现在 tile family 的 helper 默认依赖、直接消费者导入或 coverage 过滤口径中。
  - 验证 `gen_kernel(...)` 继续消费 `tile.analysis + tile.tile_exprs + tuner.param + symbol.for + dma.view` 组合。

## 额外补充

### 实现落点矩阵

功能说明：

- 说明 tile family 的实现职责分层，帮助 `build` 把 logic rewrite 和旧路径清理对应到正确文件。

使用示例：

```python
from kernel_gen.tile.analysis import apply_tile_analysis
from kernel_gen.tile.elewise import apply_tile_elewise
from kernel_gen.tile.reduce import apply_tile_reduce
```

注意事项：

- `kernel_gen.tile.common` 负责共享错误、输入合同校验、tile plan、loop/view 组装与共用 rewrite helper。
- `kernel_gen.tile.analysis` 负责 analysis-only 逻辑。
- `kernel_gen.tile.elewise` 负责非 reduce 轴 rewrite。
- `kernel_gen.tile.reduce` 负责 matmul reduce rewrite。
- `kernel_gen.passes.lowering.tile*` 若在 `S7` 现场仍存在，只能视为待清理残留，不能继续被文档视为公开入口或 coverage 目标。
