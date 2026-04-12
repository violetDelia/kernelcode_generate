# tile.md

## 功能简介

- 定义 `TilePass` 的公开合同：在单函数 IR 上先做 analysis，再按 analysis 结果进行 tile 改写。
- analysis 阶段只输出 `tile.analysis` 与参数推导辅助信息；tile 改写阶段产出 `tuner.param + scf.for + dma.view` 的显式结构。
- 公开 option 组合仅收口计划书 S1 覆盖的最小集合；其余组合不承诺支持。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- `功能实现`：[`kernel_gen/passes/lowering/tile.py`](../../../kernel_gen/passes/lowering/tile.py)
- `test`：[`test/pass/test_lowering_tile.py`](../../../test/pass/test_lowering_tile.py)

## 依赖

- Pass 管理抽象：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- `nn -> kernel` lowering：[`spec/pass/lowering/nn_lowering.md`](../../../spec/pass/lowering/nn_lowering.md)
- out-param ABI 收口：[`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- `dma` 视图与 alloc：[`spec/dialect/dma.md`](../../../spec/dialect/dma.md)
- `symbol` loop：[`spec/dialect/symbol.md`](../../../spec/dialect/symbol.md)
- `tuner.param`：[`spec/dialect/tuner.md`](../../../spec/dialect/tuner.md)
- `nn.memory` 类型：[`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- `kernel.*` 算子：[`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)

## 术语

- `analysis-only`：仅运行 analysis 阶段并停止改写。
- `tile-only`：先运行 analysis 阶段，再进入 tile 改写阶段。
- `tile.analysis`：analysis 阶段生成的角色标签矩阵，按 operand 与维度顺序输出。

## 目标

- 保持单公开 pass：`TilePass`，名字固定为 `tile`。
- 固定 analysis 与 tile 改写的前后顺序。
- 明确 analysis-only 与 tile-only 的互斥关系。
- 公开 option 组合仅覆盖计划书 S1 所列最小集合。

## 限制与边界

- 输入必须已完成 `NnLoweringPass -> BufferResultsToOutParamsPass`；若残留 `nn.*` 或 memory-return ABI，必须失败。
- `analysis-only` 与 `tile-only` 同时为 `true` 必须报 `TilePassInvalidOption`。
- `analysis-only` 与 `tile-only` 的 value 只接受 `true/false` 字符串。
- 除下述公开组合外，其他 option 组合未承诺支持，行为未定义。

## 公开接口

### `class TilePass(Pass)`

功能说明：

- 表示 tile pass。
- 通过 `run(module)` 在单函数 IR 上执行 analysis 与 tile 改写。
- 支持 `from_options(options)` 解析公开 option。

参数说明：

- `name (str)`：固定为 `"tile"`。

使用示例：

```python
from kernel_gen.passes.lowering.tile import TilePass

analysis_pass = TilePass.from_options(
    {
        "analysis-only": "true",
        "tile-elewise": "true",
        "tile-reduce": "false",
    }
)
module = analysis_pass.run(module)

rewrite_pass = TilePass.from_options(
    {
        "tile-only": "true",
        "tile-elewise": "true",
        "tile-reduce": "false",
    }
)
module = rewrite_pass.run(module)
```

注意事项：

- 不新增或拆分函数。
- `analysis-only=true` 时仅输出 analysis 结果与参数推导，不生成 `scf.for` / `dma.view`。
- `tile-only=true` 时先运行 analysis，再进入 tile 改写阶段。

返回与限制：

- 返回改写后的 module。
- 不满足输入合同或 option 组合非法时必须报错，不得静默跳过。

### `TilePass.run(module)`

功能说明：

- 对输入 module 执行 analysis 与 tile 改写。

参数说明：

- `module (builtin.module)`：满足 tile 输入合同的 IR module。

使用示例：

```text
func.func @vec_add(%arg0: !nn.memory<[M, N], f32, #layout, #GM>,
                   %arg1: !nn.memory<[M, N], f32, #layout, #GM>,
                   %arg2: !nn.memory<[M, N], f32, #layout, #GM>) {
  %0 = kernel.add %arg0, %arg1 outs(%arg2)
  func.return
}
```

返回与限制：

- 返回完成改写后的 module。

### `TilePass.from_options(options: dict[str, str]) -> TilePass`

功能说明：

- 从 `options` 构造 `TilePass`。

参数说明：

- `options (dict[str, str])`：选项字典。

使用示例：

```python
pass_obj = TilePass.from_options({"analysis-only": "true", "tile-elewise": "true", "tile-reduce": "false"})
module = pass_obj.run(module)
```

注意事项：

- `analysis-only=true` 与 `tile-only=true` 同时出现必须报 `TilePassInvalidOption`。
- `analysis-only` 与 `tile-only` 仅接受 `true/false`。

返回与限制：

- 返回 `TilePass` 实例。

## 额外补充

- 公开 option 组合：
  - `analysis-only=true, tile-elewise=true, tile-reduce=false`
  - `tile-only=true, tile-elewise=true, tile-reduce=false`
  - `tile-only=true, tile-elewise=true, tile-reduce=true`
  - 本轮只收口以上组合；其余组合未承诺支持。
- 公开行为：
  - `analysis-only=true` 时：允许 `tile.analysis`/`tuner.param`/`symbol.get_dim`，不允许 `scf.for`/`dma.view`。
  - `tile-only=true` 时：analysis 先执行，再生成 `tuner.param + scf.for + dma.view`，改写后 `tile.analysis` 不再保留。

## 测试

- 测试文件：`test/pass/test_lowering_tile.py`
- 执行命令：`pytest -q test/pass/test_lowering_tile.py`
- 测试目标：
  - 验证单入口行为与公开 option 组合。
  - 验证 `analysis-only` 与 `tile-only` 互斥的拒绝路径。
- 功能与用例清单：
  - `test_tile_analysis_only_true`
  - `test_tile_analysis_only_false`
  - `test_tile_analysis_only_invalid_value`
  - `test_tile_analysis_only_and_tile_only_conflict`
