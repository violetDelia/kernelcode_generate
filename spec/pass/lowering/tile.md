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

## analysis 结果文本合同

- `tile.analysis` 必须是二维列表：外层按 operand 顺序排列，内层按该 operand 的维度顺序排列。
- 每个维度位置只输出角色标签，不输出具体维度值。
- 角色标签只允许使用：`elewise`、`expand`、`reduce`。

示例：

```text
"dma.broadcast"(%out, %src)
  {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]}
```

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

## tile-only 改写合同（elementwise / broadcast）

- 适用 option：`tile-only=true, tile-elewise=true, tile-reduce=false`。
- 适用输入：
  - `kernel.binary_elewise`：必须携带 `tile.analysis`，operand 数固定为 3（lhs/rhs/out）。
  - `dma.broadcast`：必须携带 `tile.analysis`，operand 数固定为 2（out/src 或 src/out 以 op 定义为准）。
- 改写目标：
  - 仅对 `tile.analysis` 中标注为 `elewise` 的维度生成 `symbol.for`。
  - `expand` 维不生成本维度循环；对应维度在 `dma.view` 中使用常量 0 或 1（按原 op 语义）。
  - 每个 `elewise` 维生成一个 `tuner.param`，类型为 `!symbol.int<"...">`。
  - 常量统一通过 `symbol.const` 生成；不得出现 `tile.step_value`、`tile.symbol_literal`。
  - `symbol.for` 的迭代变量必须以 `!symbol.iter<start/end/step>` 形式传递给 `dma.view`，并与 `iter = #symbol.iter<...>` 保持一致。
  - `dma.view` 对每个 operand 生成一份；view 的 shape/stride 以 `tuner.param` 与 `symbol.get_dim` 组合得到。
  - 改写后的 op：
    - `kernel.binary_elewise`：保留 `kind/space`，operand 替换为 view 结果，结果写入 view 的 out。
    - `dma.broadcast`：operand 替换为 view 结果。
  - 改写完成后必须移除 `tile.analysis` 属性。
- 维度数量约束：
  - 若 `tile.analysis` 仅包含 1 个 `elewise` 维，则只生成 1 层 `symbol.for` 与 1 个 `tuner.param`。
  - 若包含 2 个 `elewise` 维，则生成 2 层 `symbol.for` 与 2 个 `tuner.param`。

示例（broadcast）：

```text
// COMPILE_ARGS: --pass "tile={tile-only=true,tile-elewise=true,tile-reduce=false}"

"dma.broadcast"(%out, %src)
  {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]}
```

## 测试

- 测试文件：`test/pass/test_lowering_tile.py`
- 执行命令：
  - `pytest -q test/pass/test_lowering_tile.py`
- 运行前提：
  - expectation 以 worktree 版本为准时，在 worktree 根目录执行上述命令。
  - expectation 以主仓版本为准时，在主仓根目录执行命令，并将 worktree 路径置于 `PYTHONPATH` 前置，例如：
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python -m expectation.pass.tile.analysis`
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/pass/tile/analysis_only.py`
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python expectation/pass/tile/tile_only/element_binary.py`
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python expectation/pass/tile/tile_only/broadcast.py`
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python -m expectation.pass.tile.tile_only`
- 测试目标：
  - 验证单入口行为与公开 option 组合。
  - 验证 `analysis-only` 与 `tile-only` 互斥的拒绝路径。
  - 验证 analysis 目录入口可运行（以主仓 expectation 与 worktree 代码联动为准）：
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python -m expectation.pass.tile.analysis`
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/pass/tile/analysis_only.py`
  - 验证 tile-only 目录入口与子用例可运行（以主仓 expectation 与 worktree 代码联动为准）：
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python expectation/pass/tile/tile_only/element_binary.py`
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python expectation/pass/tile/tile_only/broadcast.py`
    - `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s3:/home/lfr/kernelcode_generate python -m expectation.pass.tile.tile_only`
- 功能与用例清单：
  - `test_tile_analysis_only_true`
  - `test_tile_analysis_only_false`
  - `test_tile_analysis_only_invalid_value`
  - `test_tile_analysis_only_and_tile_only_conflict`
