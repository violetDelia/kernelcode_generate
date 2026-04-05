# kernel_split.md

## 功能简介

- 定义 `KernelSplitPass` 的公开合同：把已完成 `nn -> kernel` 与 out-param 收口的函数级 IR，重写为单函数内的显式 tile 遍历结构。
- 固定 tile 因子的唯一公开来源为 `tuner.param`，不允许在 spec 中把 tile size 写成固定整数常量。
- 固定切分后的承接方式：保留原 `func.func`，在函数体内组织 split body / tile loop，并明确中间值的 SSA 保留与 carry memory 物化规则。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/lowering/kernel_split.md`](../../../spec/pass/lowering/kernel_split.md)
- `功能实现`：[`kernel_gen/passes/lowering/kernel_split.py`](../../../kernel_gen/passes/lowering/kernel_split.py)
- `test`：[`test/pass/test_lowering_kernel_split.py`](../../../test/pass/test_lowering_kernel_split.py)

## 依赖

- Pass 管理抽象：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- `nn -> kernel` lowering：[`spec/pass/lowering/nn_to_kernel.md`](../../../spec/pass/lowering/nn_to_kernel.md)
- out-param ABI 收口：[`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- `tuner.param` 语义：[`spec/dialect/tuner.md`](../../../spec/dialect/tuner.md)

## 术语

- `entry func`：切分前后的同一个入口 `func.func`；P0 不允许为切分结果新增额外 `func.func` 或 `func.call`。
- `tile axis`：被切分的唯一主轴；P0 仅允许单一非负轴，不允许负轴或多轴联合切分。
- `tile param`：`tuner.param` 返回的 `!symbol.dim<"...">` 符号维度值，用于表达 tile 大小。
- `bridge op`：`tuner.param` 与 `symbol.get_dim`；仅允许作为 tile 参数或动态 shape 的桥接辅助 op，不属于本 pass 的核心 split 作用对象。
- `split marker`：显式声明某个函数需要执行 kernel split 的公开触发标记。
- `carry memory`：在同一 `func.func` 内跨 tile stage 传递中间结果的显式 memory 承接物。

## 目标

- 冻结 `KernelSplitPass` 的正式公开名称、输入/输出合同、split 触发方式与错误边界。
- 固定 `tuner.param` 到 tile 因子的桥接规则：由 split marker 声明 tile 名称，由 pass 在目标函数体内插入或复用同名 `tuner.param`。
- 固定切分后的 IR 形态：仍保留单个入口函数，在函数体内显式表达 tile loop / split body，并保证跨阶段值传递是显式 SSA 或显式 carry memory。

## 限制与边界

- 本 pass 只接受已经完成 `LowerNnToKernelPass -> BufferResultsToOutParamsPass` 的函数级 IR；若仍残留 `nn.*` 或旧 `memory return` ABI，必须失败。
- 输入允许子集固定为：核心计算/搬运 op 只能是 `kernel.*` / `dma.*` / `func.return`，并且只额外允许 `tuner.param` / `symbol.get_dim` 作为 bridge op；bridge op 仅用于 tile 参数或动态 shape 承接，不改变核心 split 作用对象。
- split 触发必须来自函数属性 `kernel_split = { axis = <i64>, tile = "<TILE_NAME>" }`；`axis` 必须为单一非负整数，`tile` 必须符合 `tuner.param` 的合法命名规则。
- 运行 `KernelSplitPass` 时，若 module 内没有任何 `kernel_split` 标记函数，必须失败，错误关键字固定为 `KernelSplitMissingTrigger`。
- tile 因子的唯一公开来源是 `tuner.param`；不允许把 step / tile size 固化为整数字面量，也不允许由 pass 参数或隐藏全局状态替代。
- 切分后必须保持单函数合同：不得新增 `func.func`、`func.call`、helper 函数或其它函数抽取结果承接 tile。
- P0 仅允许单一主轴切分；负轴、多轴联合切分、自动选择切分轴、自动并行、自动 DMA hierarchy、自动双缓冲均不在本 pass 公开合同内。
- 同一 tile stage 内、且生产者与所有消费者都位于同一显式 split body 中的中间值，可以保留为 SSA；一旦值跨 stage、跨切片写回边界、或需要在后续阶段继续读写，必须物化为显式 carry memory。
- carry memory 必须在同一 `func.func` 内创建、被后续 stage 消费，并在 tile 迭代结束前写回最终目标或完成最终消费；不允许留下未消费的 carry memory。
- 本 spec 只冻结显式 IR 合同与错误短语，不冻结具体切分算法、tile 搜索策略或 allocator 选型。

## 公开接口

### `class KernelSplitPass(Pass)`

功能说明：

- 表示 kernel split pass。
- 通过 `run(module)` 对带 `kernel_split` 标记的函数执行显式 tile 化切分。

参数说明：

- `name (str)`：固定为 `"kernel-split"`。

使用示例：

```python
from kernel_gen.passes.lowering.kernel_split import KernelSplitPass

pass_obj = KernelSplitPass()
module = pass_obj.run(module)
```

```text
func.func @vec_add_exp(%arg0: !nn.memory<[B, M], f32, #layout, #GM>,
                       %arg1: !nn.memory<[B, M], f32, #layout, #GM>,
                       %arg2: !nn.memory<[B, M], f32, #layout, #GM>)
    attributes { kernel_split = { axis = 1 : i64, tile = "TILE_M" } } {
  %0 = kernel.add %arg0, %arg1 outs(%arg2)
  %1 = kernel.exp %arg2 outs(%arg2)
  func.return
}
```

注意事项：

- `KernelSplitPass` 只处理带 `kernel_split` 标记的 `func.func`。
- `kernel_split.tile` 负责声明 tile 名称；pass 必须在目标函数体内插入或复用同名 `tuner.param : !symbol.dim<"...">`，并以该符号值作为 tile loop 的 step。
- `kernel_split.axis` 负责声明唯一主轴；若不存在、为负值、超出目标维度范围，或试图表达多轴切分，必须失败。
- 切分结果必须仍位于原 `func.func` 函数体内；不允许抽取 helper 函数承接 split body。

前置条件：

- 输入 `module` 必须是可遍历的 `builtin.module`。
- 被切分函数必须已完成 `LowerNnToKernelPass -> BufferResultsToOutParamsPass`，且其核心计算已 lower 为 `kernel.* / dma.* / func.return` 子集；若存在额外 op，则仅允许 `tuner.param` / `symbol.get_dim` 作为 bridge op 保留。

后置条件：

- 每个被切分函数都仍是原入口 `func.func`，并在函数体内显式包含 tile loop / split body。
- 每个被切分函数都必须出现与 split marker 对应的 `tuner.param`。

返回与限制：

- 返回完成切分后的 module。
- 遇到任一不满足公开合同的函数时必须抛错，不能静默跳过或回退为未切分形态。

### `KernelSplitPass.run(module)`

功能说明：

- 对输入 module 执行 kernel split。
- 将目标函数重写为单函数内显式 tile 遍历结构，并根据中间值生存范围决定使用 SSA 还是 carry memory。

参数说明：

- `module (builtin.module)`：包含已 lower 到 `kernel/dma/func.return` 核心子集、并且只额外允许 `tuner.param` / `symbol.get_dim` 作为 bridge op 的 IR module。

使用示例：

```text
%tile_m = tuner.param : !symbol.dim<"TILE_M">
scf.for %i = %c0 to %M step %tile_m {
  %lhs = dma.slice %arg0[%i][%tile_m]
  %rhs = dma.slice %arg1[%i][%tile_m]
  %out = dma.slice %arg2[%i][%tile_m]
  %0 = kernel.add %lhs, %rhs outs(%out)
  %1 = kernel.exp %out outs(%out)
}
```

```text
%tile_m = tuner.param : !symbol.dim<"TILE_M">
%carry = dma.alloc ...
scf.for %i = %c0 to %M step %tile_m {
  %a_tile = dma.slice %a[%i, 0][%tile_m, %K]
  %out_tile = dma.slice %out[%i, 0][%tile_m, %N]
  %0 = kernel.matmul %a_tile, %b outs(%carry)
  %1 = kernel.add %carry, %bias outs(%carry)
  dma.deslice %carry into %out_tile
}
```

注意事项：

- split marker 的公开写法固定为 `kernel_split = { axis = <i64>, tile = "<TILE_NAME>" }`。
- `tuner.param` 的公开桥接规则固定为：`kernel_split.tile` 声明名字，pass 插入或复用 `%tile = tuner.param : !symbol.dim<"<TILE_NAME>">`，并把该 SSA 值用作 tile loop / split body 的步长或等价边界值。
- `symbol.get_dim` 只允许作为 `dma.alloc` 等动态 shape 承接所需的维度桥接 op；它可以出现在输入 IR 中，但不得替代 `kernel.*` 成为核心 split 作用对象，也不得改变错误短语或触发条件。
- 同一 split body 内、且仅在当前 tile 内完成消费的中间值可以保留为 SSA；以下情况必须物化为 carry memory：
  - 值会在后续 stage 继续被读写；
  - 值需要作为多个后续 `kernel.*` 的 `outs` / in-place 工作区；
  - 值需要在 stage 末尾通过 `dma.deslice` 或等价写回动作落到输出 tile；
  - 值无法在 verifier 层稳定表示为单一 SSA 生命周期。
- carry memory 的创建、消费与最终写回都必须位于同一 `func.func` 中；若创建后未被消费或未完成最终写回，必须失败。
- `run(module)` 的失败边界与错误关键字固定如下：
  - 缺少任何 `kernel_split` 标记：`KernelSplitMissingTrigger`
  - 缺少或非法 `tile` 名称、无法生成合法 `tuner.param`：`KernelSplitMissingTileParam`
  - 输入仍残留 `nn.*`，或除 `tuner.param` / `symbol.get_dim` 外仍存在未满足允许子集的 op：`KernelSplitRequiresLoweredKernelIR`
  - 输入仍使用旧 `memory return` ABI：`KernelSplitRequiresOutParamsABI`
  - `axis` 缺失、为负值、超范围或与目标轴不匹配：`KernelSplitAxisMismatch`
  - 通过新增 `func.func` / `func.call` 承接切分：`KernelSplitUnexpectedFuncExtraction`
  - 需要跨阶段传递的值既不是合法 SSA 也未物化为 carry memory：`KernelSplitIntermediateMaterializationError`
  - 生成了未被消费的 carry memory：`KernelSplitDeadCarryMemory`
  - 切分后 IR 不再满足 verifier：`KernelSplitVerifierError`

前置条件：

- `module` 中被切分函数必须可识别目标轴维度，并能在当前函数体内合法插入 `tuner.param` 与显式 split body。

后置条件：

- 若执行成功，结果 IR 中不再存在“需要切分但仍以整块 kernel 形态执行”的目标函数。
- 若中间值跨 stage 传递，结果 IR 必须包含显式 carry memory 承接并完成最终消费。

返回与限制：

- 返回切分后的 module。
- 不允许以“静默不切分”“回退为常量 tile”“抽取 helper 函数”“隐式重算中间值”的方式伪造成功。

## 测试

- 测试文件：[`test/pass/test_lowering_kernel_split.py`](../../../test/pass/test_lowering_kernel_split.py)
- 执行命令：`pytest -q test/pass/test_lowering_kernel_split.py`
- 测试目标：
  - 验证 split 后的 tile 因子由 `tuner.param` 驱动，而不是固定整数字面量。
  - 验证切分结果保持单个入口函数，并在函数体内显式出现 split body / tile loop。
  - 验证 `tuner.param` / `symbol.get_dim` 仅作为 bridge op 被允许保留输入，不改变核心 split 作用对象与失败关键字。
  - 验证中间值物化规则：可保留为 SSA 的值不被强制落地，需要跨 stage 传递的值必须显式物化为 carry memory。
  - 验证缺少 trigger、缺少 `tuner.param`、轴不匹配、helper 函数抽取、未物化中间值、dead carry memory、lowering/verifier 失败等错误路径的关键短语稳定。
- 功能与用例清单：

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| TC-KS-001 | tile 因子只能来自 `tuner.param` | `test_kernel_split_pass_uses_tuner_param_tiles` |
| TC-KS-002 | 切分后保持单函数并生成显式 split body | `test_kernel_split_pass_keeps_single_func_and_emits_split_body` |
| TC-KS-003 | 缺少 `tuner.param` 桥接时失败并包含 `KernelSplitMissingTileParam` | `test_kernel_split_pass_rejects_missing_tuner_param` |
| TC-KS-004 | 不允许新增 `func.func` / `func.call` 承接切分 | `test_kernel_split_pass_rejects_new_func_generation` |
| TC-KS-005 | 未物化的跨阶段中间值失败并包含 `KernelSplitIntermediateMaterializationError` | `test_kernel_split_pass_rejects_unmaterialized_intermediate` |
| TC-KS-006 | 输入残留 `nn.*` 时失败并包含 `KernelSplitRequiresLoweredKernelIR` | `test_kernel_split_pass_rejects_non_lowered_nn_ops` |
| TC-KS-007 | dead carry memory 失败并包含 `KernelSplitDeadCarryMemory` | `test_kernel_split_pass_rejects_dead_carry_memory` |
| TC-KS-008 | module 内缺少 split marker 时失败并包含 `KernelSplitMissingTrigger` | `test_kernel_split_pass_rejects_missing_trigger` |
| TC-KS-009 | `axis` 非法或与目标轴不匹配时失败并包含 `KernelSplitAxisMismatch` | `test_kernel_split_pass_rejects_axis_mismatch` |
