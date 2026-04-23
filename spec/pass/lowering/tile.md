# tile.md

## 功能简介

- 本页是 tile family 的总览/索引页，不承载历史兼容入口的完整公开合同。
- 当前已经完成并对外收口的子合同是 `tile-analysis`、`tile-elewise` 与 `tile-reduce`。
- 三个子合同均以独立子 spec、registry 名称、实现入口与 pytest 用例作为公开合同资产。
- tile family 的共享 helper 与真实改写落点位于 `kernel_gen.tile.*`，不再把 `kernel_gen.passes.lowering.tile` 当作长期共享实现入口。
- 需要具体行为定义时，优先进入子 spec；本页只定义公开 pass family 的索引、边界与最小调用方式。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- `功能实现`：
  - [`kernel_gen/passes/lowering/tile_analysis.py`](../../../kernel_gen/passes/lowering/tile_analysis.py)
  - [`kernel_gen/passes/lowering/tile_elewise.py`](../../../kernel_gen/passes/lowering/tile_elewise.py)
  - [`kernel_gen/passes/lowering/tile_reduce.py`](../../../kernel_gen/passes/lowering/tile_reduce.py)
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
- `历史桥接 op`：拆分前用于在 tile/codegen 间转交 tile 因子的旧公开文本。
- `tile helper`：位于 `kernel_gen.tile.common` 的共享错误、输入校验、plan、loop 与 view 组装 helper。

## 目标

- 对外公开 pass 名只保留 `tile-analysis`、`tile-elewise`、`tile-reduce`。
- `tile-analysis` 只写入 `tile.analysis + tile.tile_exprs`，不生成切分结构。
- `tile-elewise` 消费 analysis 结果并切分 elewise 轴。
- `tile-reduce` 消费 analysis 结果并切分 `kernel.matmul` reduce 轴。
- tile family 的公开输出统一保持 `tile.analysis + tile.tile_exprs`。
- 分块因子统一由 `tuner.param : !symbol.int<"...">` 表示，循环结构统一由 `symbol.for` 表示。
- 公开构造入口固定为 registry 名称；具体 `ModulePass` 壳与共享 helper 分层属于实现细节。
- tile family 的共享 helper、analysis 标注与 rewrite 实际落点固定为 `kernel_gen.tile.common`、`kernel_gen.tile.analysis`、`kernel_gen.tile.elewise`、`kernel_gen.tile.reduce`。

## 限制与边界

- 本页不重新定义三个子 pass 的完整行为，具体改写规则以对应子 spec 为准。
- 历史兼容 pass 不再是公开 pass family 合同的一部分。
- 历史桥接 op 名称不再作为公开输入或输出合同。
- `tile-elewise` 与 `tile-reduce` 必须在已有 `tile.analysis + tile.tile_exprs` 的输入上工作；缺失 analysis 结果时必须显式失败。
- `gen_kernel(...)` 只消费 tile family 收口后的 split-after-IR 结果，不负责重新推导 tile family analysis。
- 直接依赖 `kernel_gen.passes.lowering.tile`、`kernel_gen.passes.lowering.tile_analysis`、`kernel_gen.passes.lowering.tile_elewise`、`kernel_gen.passes.lowering.tile_reduce` 的具体 module path 不属于公开合同。
- `kernel_gen.passes.lowering.tile.py` 不应再同时承担共享 helper 与最终 rewrite 的双重职责。

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

- 返回 `TileAnalysisPass`。
- 不生成 `symbol.for` 或 `dma.view`。

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

- 返回 `TileElewisePass`。
- 只处理已有 analysis 结果且尚未切分的 elewise family op。

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

- 返回 `TileReducePass`。
- 只处理已有 analysis 结果且尚未切分的 `kernel.matmul` reduce family op。

## 测试

- 测试文件：
  - [`test/pass/test_lowering_tile.py`](../../../test/pass/test_lowering_tile.py)
  - [`test/pass/test_lowering_tile_private_helpers.py`](../../../test/pass/test_lowering_tile_private_helpers.py)
  - [`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
  - [`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
  - [`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)
  - [`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)
- 执行命令：
  - `pytest -q test/pass/test_lowering_tile.py`
  - `pytest -q test/pass/test_lowering_tile_private_helpers.py`
  - `pytest -q test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py`
  - `pytest -q test/dsl/test_gen_kernel.py -k "tile or gen_kernel"`
- 测试目标：
  - 验证三个公开 pass 名都能通过 registry 构造为 `ModulePass`。
  - 验证共享 helper 已从旧 mixed path 收口到 `kernel_gen.tile.*`，不再把 `kernel_gen.passes.lowering.tile` 当作长期共享入口。
  - 验证历史公开 pass 名与历史桥接 op 不再作为 tile family 输出合同。
  - 验证 `tile-elewise` 与 `tile-reduce` 只消费已有 analysis 结果并保持 split-after-IR 合同。
  - 验证 `gen_kernel(...)` 仍可消费 `tile.analysis + tile.tile_exprs + tuner.param + symbol.for + dma.view` 的输出组合。

## 额外补充

### 实现落点矩阵

功能说明：

- `kernel_gen.passes.lowering.tile_analysis.py`、`tile_elewise.py`、`tile_reduce.py` 负责公开 `ModulePass` 壳与 registry 对接。
- `kernel_gen.tile.common.py` 负责共享错误类型、输入合同校验、tile plan、loop/view 组装与共用 rewrite helper。
- `kernel_gen.tile.analysis.py`、`elewise.py`、`reduce.py` 分别承接 analysis-only、elewise rewrite 与 matmul reduce rewrite 的真实实现。

使用示例：

```python
from kernel_gen.tile.common import TilePassError
from kernel_gen.tile.common import _plan_tile_ops
```

注意事项：

- 这里定义的是实现落点，不改变公开 pass 名。
- `kernel_gen.passes.lowering.tile.py` 如仍保留薄桥接，也不再作为共享 helper 的默认依赖路径。
