# tile.md

## 功能简介

- 定义 `TilePass` 的公开合同：将完成 `nn -> kernel` 与 out-param 收口后的单函数 IR 改写为显式 `symbol.for` + `dma.view` 结构。
- elementwise 按 memory rank 生成多层 loop；matmul 按 M/N/K 三维生成 loop；reduce 明确拒绝。
- tile 因子仅来自 `tuner.param`，并通过明确的 step bridge 进入 loop step。
- 支持 `analysis-only` 选项：仅插入 `tuner.param` 与 `symbol.get_dim` 等维度推导 helper，不生成 `symbol.for` / `dma.view`。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`咯咯咯`
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

- `tile param`：`tuner.param` 的 `!symbol.dim<"...">` 结果，用于声明 tile 名称。
- `step bridge`：`tile.step_value`，用于把 `!symbol.dim<"...">` 转成 `!symbol.int<"...">`。
- `carry memory`：跨 tile stage 传递中间值时显式物化的 `dma.alloc`。

## 目标

- 保持单函数合同，不新增 `func.call` 或额外 `func.func`。
- 明确 elementwise 与 matmul 的 loop 结构与 view 生成规则。
- 固定错误短语，便于测试与上层逻辑稳定匹配。
- 提供 `analysis-only` 选项，用于仅保留分析与参数推导结果。

## 限制与边界

- 输入必须已完成 `NnLoweringPass -> BufferResultsToOutParamsPass`；若残留 `nn.*` 或 memory-return ABI，必须失败。
- 输入允许子集为：`kernel.*` / `dma.*` / `func.return`，并只额外允许 `tuner.param` 与 `symbol.get_dim` 作为桥接 op。
- `func.call` 不允许出现在 tile 处理范围内。
- `analysis-only=true` 不改变输入合同：输入不满足约束时仍需按相同错误短语失败。
- `analysis-only` 仅允许 `true` 或 `false` 两个字符串值；除 `analysis-only` 以外的 option key 必须报错。
- elementwise 要求所有参与的 `nn.memory` rank 一致；不一致报 `TilePassRankMismatch`。
- matmul 仅支持 rank=2，且 `[M,K] x [K,N] -> [M,N]` 必须一致；不一致报 `TilePassRankMismatch`。
- reduce 类 `kernel.reduce_*` 明确不支持，报 `TilePassUnsupportedOp`。
- 跨 stage 中间值必须来自 `dma.alloc`；否则报 `TilePassRequiresLoweredKernelIR`。
- 写入但未被后续 stage 消费的 `dma.alloc` 视为无效 carry memory，报 `TilePassDeadCarryMemory`。
- 错误关键字必须包含：
  - `TilePassRankMismatch`
  - `TilePassDuplicateTileParam`
  - `TilePassUnsupportedOp`
  - `TilePassRequiresLoweredKernelIR`
  - `TilePassDeadCarryMemory`
  - `TilePassInvalidOption`

## 公开接口

### `class TilePass(Pass)`

功能说明：

- 表示 tile pass。
- 通过 `run(module)` 对满足输入合同的 `func.func` 执行 tile loop 改写。
- 支持 `from_options(options)` 解析 `analysis-only`。

参数说明：

- `name (str)`：固定为 `"tile"`。

使用示例：

```python
from kernel_gen.passes.lowering.tile import TilePass

pass_obj = TilePass()
module = pass_obj.run(module)
analysis_only_pass = TilePass.from_options({"analysis-only": "true"})
module = analysis_only_pass.run(module)
```

注意事项：

- 只处理 `func.func`，不会新增或拆分函数。
- 不依赖额外属性作为触发条件。
- `analysis-only=true` 时保留原有 `kernel.*` 计算，仅插入 `tuner.param` 与维度推导 helper；不生成 `symbol.for` / `dma.view`。

返回与限制：

- 返回改写后的 module。
- 任一函数不满足输入合同时必须报错，不得静默跳过。

### `TilePass.run(module)`

功能说明：

- 对输入 module 执行 tile loop 改写。

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

- 返回完成 loop 改写后的 module。
- 错误短语需包含指定关键字。

### `TilePass.from_options(options: dict[str, str]) -> TilePass`

功能说明：

- 从 `options` 构造 `TilePass`。
- 仅支持 `analysis-only=true|false`。

参数说明：

- `options (dict[str, str])`：选项字典。

使用示例：

```python
pass_obj = TilePass.from_options({"analysis-only": "true"})
module = pass_obj.run(module)
```

注意事项：

- `options` 为空时等价于 `TilePass()`。
- key 不是 `analysis-only` 或 value 不是 `true/false` 时必须抛出 `TilePassInvalidOption`。

返回与限制：

- 返回 `TilePass` 实例。

## 测试

- 测试文件：`test/pass/test_lowering_tile.py`
- 执行命令：`pytest -q test/pass/test_lowering_tile.py`
- 测试目标：
  - 覆盖 elementwise/matmul 成功路径的 loop/view 结构。
  - 覆盖 reduce 不支持、rank mismatch、重复 tile、输入合同与 dead carry 等错误路径。
  - 覆盖 `analysis-only=true|false` 的公开行为与非法值拒绝路径。
- 功能与用例清单：
  - `test_tile_elementwise_builds_nested_loops`
  - `test_tile_matmul_builds_mnk_loops`
  - `test_tile_rejects_reduce_kernel_ops`
  - `test_tile_rejects_duplicate_tile_names`
  - `test_tile_rejects_nn_input_ops`
  - `test_tile_rejects_dead_carry_memory`
  - `test_tile_rejects_rank_mismatch`
  - `test_tile_analysis_only_true`
  - `test_tile_analysis_only_false`
  - `test_tile_analysis_only_invalid_value`
