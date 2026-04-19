# dma_memory_hierarchy.md

## 功能简介

- 定义 `lower-dma-memory-hierarchy` pass：把仍停留在 `GM` 的 `kernel/dma` IR 显式改写成 `GM -> SM -> LM` / `LM -> SM -> GM` 的分层搬运路径。
- 本 pass 新增的 hierarchy 搬运统一使用 `dma.slice / dma.deslice` 表达，不引入 `dma.copy/load/store` 作为主语义。
- staging `dma.alloc` 的 `dynamic_shape` 必须来自已有显式 symbol 来源；匿名 `?` 且无可恢复来源时必须显式失败。
- 不负责 tile 搜索、并行化、double buffer、barrier、async、codegen 等后续阶段职责。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/dma_memory_hierarchy.md`](../../../spec/pass/lowering/dma_memory_hierarchy.md)
- `功能实现`：[`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](../../../kernel_gen/passes/lowering/dma_memory_hierarchy.py)
- `test`：[`test/pass/test_dma_memory_hierarchy.py`](../../../test/pass/test_dma_memory_hierarchy.py)

## 依赖

- Pass 管理器：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- `nn -> kernel` lowering：[`spec/pass/lowering/nn_lowering.md`](../../../spec/pass/lowering/nn_lowering.md)
- `memory-return` ABI 收口：[`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../spec/dialect/dma.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)

## 术语

- `GM`：global memory（全局存储）
- `SM`：shared memory（片上共享存储）
- `LM`：local memory（本地存储）

## 目标

- 固定 pass 名称与顺序边界：`NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。
- 强制 `kernel.*` 计算仅在 `LM` 上发生，读写路径显式拆成 `GM -> SM -> LM` 与 `LM -> SM -> GM`。
- 新增 hierarchy 搬运统一用 `dma.slice / dma.deslice`，整块搬运只是 `slice/deslice` 的全量窗口特例。
- 冻结窗口链路口径：`GM -> SM` 与 `SM -> GM` 必须保留原窗口 `offsets/sizes`，并继续使用 unit stride；`SM -> LM` 与 `LM -> SM` 必须改写为 `zero offsets + unit strides`。
- 冻结 dynamic shape 口径：staging `dma.alloc` 只能消费已有显式 symbol 来源；匿名 `?` 且无可恢复来源必须失败。

## 限制与边界

- 本 pass 只能位于 `NnLoweringPass` 与 `BufferResultsToOutParamsPass` 之后，且输入不得包含 `nn.*`。
- 不改写函数 ABI；caller/callee 的 out-param 合同仍由 `BufferResultsToOutParamsPass` 负责。
- 本 pass 新增的 hierarchy 搬运不得使用 `dma.copy` / `dma.load` / `dma.store`；若输入中已有这些 op，本 pass 不要求重写，但也不得用它们表达新增的层级主语义。
- 读路径必须是 `GM -> SM -> LM`，写路径必须是 `LM -> SM -> GM`；不允许直连 `GM -> LM` 或 `LM -> GM`。
- 若输入/输出使用窗口视图，`GM -> SM` 读入与 `SM -> GM` 写回必须保留该窗口的原始 `offsets/sizes`，并继续使用 unit stride；只有 `SM -> LM` 与 `LM -> SM` 两段允许正规化为 `zero offsets + unit strides`。
- 处理后的 `kernel.*` operand/out 只允许 `LM` memory；不得保留 `GM/SM` 作为计算或写回空间。
- staging `dma.alloc` 的 `dynamic_shape` 必须来自已有显式 symbol 来源：full-window 路径只能使用 `symbol.get_dim` 从显式 shape 条目取值，window 路径只能使用 `dma.view.shape` 等现成 SSA shape 操作数；匿名 `?` 且无可恢复来源时必须显式失败。
- 目标不支持 `SM` 或 `LM` 时必须显式失败，禁止静默降级；失败短语必须包含 `dynamic_shape` / `SM` / `LM` 关键字之一。

## 公开接口

### `class LowerDmaMemoryHierarchyPass(Pass)`

功能说明：

- 表示 DMA memory hierarchy lowering pass。
- 通过 `run(module)` 执行改写。

参数说明：

- `name (str)`：固定为 `"lower-dma-memory-hierarchy"`。

使用示例：

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.passes.pass_manager import PassManager

pm = PassManager(name="lowering")
pm.add_pass(NnLoweringPass())
pm.add_pass(BufferResultsToOutParamsPass())
pm.add_pass(LowerDmaMemoryHierarchyPass())
module = pm.run(module)
```

注意事项：

- pass 顺序必须固定为 `NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。
- 新增 hierarchy 搬运必须使用 `dma.slice / dma.deslice`；整块搬运是全量窗口特例（`offsets=0`、`sizes=shape`、`strides=1`）。
- 处理后的 `kernel.*` 只允许 `LM` memory 作为 operand/out。
- staging `dma.alloc` 的 `dynamic_shape` 只能来自显式 symbol 来源；若 full-window 输入含匿名 `?`，`run` 必须显式失败而不是静默补默认值。

前置条件：

- 输入 `module` 已完成 `nn -> kernel` lowering，且 out-param ABI 已收口。
- `module` 中 `kernel.*` 的可见输入/输出仍在 `GM`。

后置条件：

- 输出 module 中 `kernel.*` operand/out 全部为 `LM`。
- 读路径明确包含 `GM -> SM -> LM` 的 `dma.slice` 链路，写路径明确包含 `LM -> SM -> GM` 的 `dma.deslice` 链路。

返回与限制：

- 返回改写后的 module（可原地修改或返回新对象，以实现为准）。
- 遇到不满足输入合同或目标缺失 `SM/LM` 时必须抛出错误并中止。

### `LowerDmaMemoryHierarchyPass.run(module)`

功能说明：

- 对输入 module 执行 DMA hierarchy lowering。
- 为 `GM` 上的计算 operand/out 构造 `SM/LM` staging，并插入 `dma.slice / dma.deslice`。

参数说明：

- `module (builtin.module)`：包含 `kernel/dma/func` 的 IR module。

使用示例：

```python
pass_obj = LowerDmaMemoryHierarchyPass()
module = pass_obj.run(module)
```

注意事项：

- 读路径示例（整块窗口）：

```text
%sm = dma.alloc ... space=SM
%lm = dma.alloc ... space=LM
dma.slice(%sm, %gm, zero_offsets, full_sizes, unit_strides)
dma.slice(%lm, %sm, zero_offsets, full_sizes, unit_strides)
```

- 写路径示例（整块窗口）：

```text
%sm = dma.alloc ... space=SM
dma.deslice(%lm, %sm, zero_offsets, full_sizes, unit_strides)
dma.deslice(%sm, %gm, zero_offsets, full_sizes, unit_strides)
```

- 窗口读路径中，`GM -> SM` 的 `dma.slice` 必须保留输入窗口的原始 `offsets/sizes` 并使用 unit stride；后续 `SM -> LM` 的 `dma.slice` 必须使用 `zero_offsets + window_sizes + unit_strides`。
- 窗口写路径中，`LM -> SM` 的 `dma.deslice` 必须使用 `zero_offsets + result_sizes + unit_strides`；最终 `SM -> GM` 的 `dma.deslice` 必须保留输出窗口的原始 `offsets/sizes` 并使用 unit stride。
- full-window 路径中，`dma.alloc` 的 `dynamic_shape` 必须通过 `symbol.get_dim` 从显式 shape 条目构造；若某一轴只有匿名 `?` 且无额外 SSA 形状来源，必须以包含 `dynamic_shape` 的错误短语失败。

前置条件：

- `module` 必须是可遍历的 `builtin.module`；无法遍历或不满足输入合同必须失败。

后置条件：

- 若成功完成，module 中不存在仍以 `GM/SM` 作为 `kernel.*` operand/out 的路径。

返回与限制：

- 返回改写后的 module。
- 不支持的输入或目标缺失 `SM/LM` 时必须显式失败，禁止静默降级。

## 测试

- 测试文件：[`test/pass/test_dma_memory_hierarchy.py`](../../../test/pass/test_dma_memory_hierarchy.py)
- 执行命令：`pytest -q test/pass/test_dma_memory_hierarchy.py`
- 测试目标：
  - 验证读路径 `GM -> SM -> LM` 与写路径 `LM -> SM -> GM` 通过 `dma.slice / dma.deslice` 表达。
  - 验证处理后的 `kernel.*` 只消费/写回 `LM`。
  - 验证新增 hierarchy 搬运不引入 `dma.copy/load/store`。
  - 验证目标缺失 `SM/LM` 时显式失败。
  - 验证输入残留 `nn.*` 时显式失败。
  - 验证窗口链路中 `GM -> SM` / `SM -> GM` 保留原窗口 `offsets/sizes` 且保持 unit stride，而 `SM -> LM` / `LM -> SM` 固定为 `zero offsets + unit strides`。
  - 验证显式 symbol shape 可透传到 staging `dma.alloc(dynamic_shape=...)`。
  - 验证匿名 `?` 且无可恢复 shape 来源时显式失败，并包含 `dynamic_shape` 关键字。
- 功能与用例清单：

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| COV-DMH-001 | 读路径 `GM -> SM -> LM` 使用 `dma.slice` | `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback` |
| COV-DMH-002 | 写路径 `LM -> SM -> GM` 使用 `dma.deslice` | `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback` |
| COV-DMH-003 | `kernel.*` 仅使用 `LM` operand/out | `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback` |
| COV-DMH-004 | 禁止新增 `dma.copy/load/store` | `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback` |
| COV-DMH-005 | 目标缺失 `SM/LM` 必须失败 | `test_dma_memory_hierarchy_requires_sm_lm` |
| COV-DMH-006 | LM-only 输入不插入 staging（no-op） | `test_dma_memory_hierarchy_lm_only_is_noop` |
| COV-DMH-007 | 输入残留 `nn.*` 必须显式失败 | `test_dma_memory_hierarchy_rejects_nn_ops_in_input` |
| COV-DMH-008 | 窗口链路中 `GM -> SM` / `SM -> GM` 保留原窗口 `offsets/sizes` 并使用 unit stride，`SM -> LM` / `LM -> SM` 使用 `zero offsets + unit strides` | `test_dma_memory_hierarchy_window_offsets_and_unit_strides` |
| COV-DMH-009 | 显式 symbol shape 可透传到 staging `dma.alloc(dynamic_shape=...)` | `test_dma_memory_hierarchy_symbol_shape_passthrough` |
| COV-DMH-010 | 匿名 `?` 且无可恢复 shape 来源时必须以 `dynamic_shape` 失败 | `test_dma_memory_hierarchy_rejects_anonymous_dynamic_shape` |
