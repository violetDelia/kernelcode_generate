# dma_memory_hierarchy

## 功能简介

- 定义 `lower-dma-memory-hierarchy` pass：把仍停留在 `GM` 的 `kernel/dma` IR 显式改写成 `GM -> SM -> LM` / `LM -> SM -> GM` 的分层搬运路径。
- 本 pass 新增的 hierarchy 搬运统一使用 `dma.slice / dma.deslice` 表达，不引入 `dma.copy/load/store` 作为主语义。
- staging `dma.alloc` 的 `dynamic_shape` 必须来自已有显式 symbol 来源；匿名 `?` 且无可恢复来源时必须显式失败。
- 不负责 tile 搜索、并行化、double buffer、barrier、async、codegen 等后续阶段职责。

## API 列表

- `class LowerDmaMemoryHierarchyPass(fold: bool = True)`
- `LowerDmaMemoryHierarchyPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/dma_memory_hierarchy/spec.md`](../../../../spec/pass/lowering/dma_memory_hierarchy/spec.md)
- `功能实现`：[`kernel_gen/passes/dma_memory_hierarchy.py`](../../../../kernel_gen/passes/dma_memory_hierarchy.py)
- `test`：[`test/passes/test_dma_memory_hierarchy.py`](../../../../test/passes/test_dma_memory_hierarchy.py)

## 依赖

- Pass 管理器：[`spec/pass/pass_manager.md`](../../../../spec/pass/pass_manager.md)
- pass registry：[`spec/pass/registry.md`](../../../../spec/pass/registry.md)
- `nn -> kernel` lowering：[`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- `memory-return` ABI 收口：[`spec/pass/buffer_results_to_out_params.md`](../../buffer_results_to_out_params.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)

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

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本 pass 只能位于 `NnLoweringPass` 与 `BufferResultsToOutParamsPass` 之后，且输入不得包含 `nn.*`。
- 不改写函数 ABI；caller/callee 的 out-param 合同仍由 `BufferResultsToOutParamsPass` 负责。
- 本 pass 新增的 hierarchy 搬运不得使用 `dma.copy` / `dma.load` / `dma.store`；若输入中已有这些 op，本 pass 不要求重写，但也不得用它们表达新增的层级主语义。
- 读路径必须是 `GM -> SM -> LM`，写路径必须是 `LM -> SM -> GM`；不允许直连 `GM -> LM` 或 `LM -> GM`。
- 若输入/输出使用窗口视图，`GM -> SM` 读入与 `SM -> GM` 写回必须保留该窗口的原始 `offsets/sizes`，并继续使用 unit stride；只有 `SM -> LM` 与 `LM -> SM` 两段允许正规化为 `zero offsets + unit strides`。
- 处理后的 `kernel.*` operand/out 只允许 `LM` memory；不得保留 `GM/SM` 作为计算或写回空间。
- staging `dma.alloc` 的 `dynamic_shape` 必须来自已有显式 symbol 来源：full-window 路径只能使用 `symbol.get_dim` 从显式 shape 条目取值，window 路径只能使用 `dma.view.shape` 等现成 SSA shape 操作数；匿名 `?` 且无可恢复来源时必须显式失败。
- 目标不支持 `SM` 或 `LM` 时必须显式失败，禁止静默降级；失败短语必须包含 `dynamic_shape` / `SM` / `LM` 关键字之一。
- 公开导入入口固定为 `kernel_gen.passes.dma_memory_hierarchy`；`kernel_gen.passes.lowering.dma_memory_hierarchy` 不再属于公开合同，必须以 `ModuleNotFoundError` 失败。

### `class LowerDmaMemoryHierarchyPass(Pass)`

- 功能说明：

- 表示 DMA memory hierarchy lowering pass。
- 通过 `apply(ctx, module)` 执行原地改写。

- 参数：

- `name (str)`：固定为 `"lower-dma-memory-hierarchy"`。

- 使用示例：

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.passes.pass_manager import PassManager

pm = PassManager(name="lowering")
pm.add_pass(NnLoweringPass())
pm.add_pass(BufferResultsToOutParamsPass())
pm.add_pass(LowerDmaMemoryHierarchyPass())
module = pm.run(module)
```

- 注意事项：

- pass 顺序必须固定为 `NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。
- 新增 hierarchy 搬运必须使用 `dma.slice / dma.deslice`；整块搬运是全量窗口特例（`offsets=0`、`sizes=shape`、`strides=1`）。
- 处理后的 `kernel.*` 只允许 `LM` memory 作为 operand/out。
- staging `dma.alloc` 的 `dynamic_shape` 只能来自显式 symbol 来源；若 full-window 输入含匿名 `?`，`apply` 必须显式失败而不是静默补默认值。

前置条件：

- 输入 `module` 已完成 `nn -> kernel` lowering，且 out-param ABI 已收口。
- `module` 中 `kernel.*` 的可见输入/输出仍在 `GM`。

后置条件：

- 输出 module 中 `kernel.*` operand/out 全部为 `LM`。
- 读路径明确包含 `GM -> SM -> LM` 的 `dma.slice` 链路，写路径明确包含 `LM -> SM -> GM` 的 `dma.deslice` 链路。

- 返回值：

- 原地改写输入 module，返回 `None`。
- 遇到不满足输入合同或目标缺失 `SM/LM` 时必须抛出错误并中止。

### `LowerDmaMemoryHierarchyPass.apply(Context(), module)`

- 功能说明：

- 对输入 module 执行 DMA hierarchy lowering。
- 为 `GM` 上的计算 operand/out 构造 `SM/LM` staging，并插入 `dma.slice / dma.deslice`。

- 参数：

- `module (builtin.module)`：包含 `kernel/dma/func` 的 IR module。

- 使用示例：

```python
pass_obj = LowerDmaMemoryHierarchyPass()
pass_obj.apply(Context(), module)
```

- 注意事项：

- 读路径示例（整块窗口）：

```text
%sm = dma.alloc value space=SM
%lm = dma.alloc value space=LM
dma.slice(%sm, %gm, zero_offsets, full_sizes, unit_strides)
dma.slice(%lm, %sm, zero_offsets, full_sizes, unit_strides)
```

- 写路径示例（整块窗口）：

```text
%sm = dma.alloc value space=SM
dma.deslice(%sm, %lm, zero_offsets, full_sizes, unit_strides)
dma.deslice(%gm, %sm, zero_offsets, full_sizes, unit_strides)
```

- 窗口读路径中，`GM -> SM` 的 `dma.slice` 必须保留输入窗口的原始 `offsets/sizes` 并使用 unit stride；后续 `SM -> LM` 的 `dma.slice` 必须使用 `zero_offsets + window_sizes + unit_strides`。
- 窗口写路径中，`LM -> SM` 的 `dma.deslice` 必须使用 `zero_offsets + result_sizes + unit_strides`；最终 `SM -> GM` 的 `dma.deslice` 必须保留输出窗口的原始 `offsets/sizes` 并使用 unit stride。
- full-window 路径中，`dma.alloc` 的 `dynamic_shape` 必须通过 `symbol.get_dim` 从显式 shape 条目构造；若某一轴只有匿名 `?` 且无额外 SSA 形状来源，必须以包含 `dynamic_shape` 的错误短语失败。

前置条件：

- `module` 必须是可遍历的 `builtin.module`；无法遍历或不满足输入合同必须失败。

后置条件：

- 若成功完成，module 中不存在仍以 `GM/SM` 作为 `kernel.*` operand/out 的路径。

- 返回值：

- 返回改写后的 module。
- 不支持的输入或目标缺失 `SM/LM` 时必须显式失败，禁止静默降级。

## API详细说明

### `class LowerDmaMemoryHierarchyPass(fold: bool = True)`

- api：`class LowerDmaMemoryHierarchyPass(fold: bool = True)`
- 参数：无。
- 返回值：`LowerDmaMemoryHierarchyPass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass

  pass_obj = LowerDmaMemoryHierarchyPass()
  assert pass_obj.name == "lower-dma-memory-hierarchy"
  ```
- 功能说明：执行 `LowerDmaMemoryHierarchyPass`。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `LowerDmaMemoryHierarchyPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`LowerDmaMemoryHierarchyPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass

  LowerDmaMemoryHierarchyPass().apply(ctx=ctx, module=module)
  ```
- 功能说明：对模块执行 `LowerDmaMemoryHierarchyPass` pass。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：
  - `test/passes/test_dma_memory_hierarchy.py`
  - `test/passes/test_pass_manager.py`
  - `test/passes/test_registry.py`
- 执行命令：`pytest -q test/passes/test_dma_memory_hierarchy.py`

### 测试目标

- 验证 `spec/pass/lowering/dma_memory_hierarchy/spec.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 Memory/DMA 参数、布局、搬运或 verifier 行为。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-COV-DMH-001 | 内存/DMA | 读路径 `GM -> SM -> LM` 使用 `dma.slice` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback`。 | 内存类型、布局、搬运结果或 verifier 行为体现“读路径 `GM -> SM -> LM` 使用 `dma.slice`”场景。 | `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback` |
| TC-COV-DMH-002 | 内存/DMA | 写路径 `LM -> SM -> GM` 使用 `dma.deslice` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback`。 | 内存类型、布局、搬运结果或 verifier 行为体现“写路径 `LM -> SM -> GM` 使用 `dma.deslice`”场景。 | `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback` |
| TC-COV-DMH-003 | 内存/DMA | `kernel.*` 仅使用 `LM` operand/out | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`kernel.*` 仅使用 `LM` operand/out”场景。 | `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback` |
| TC-COV-DMH-004 | 内存/DMA | 禁止新增 `dma.copy/load/store` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback`。 | 内存类型、布局、搬运结果或 verifier 行为体现“禁止新增 `dma.copy/load/store`”场景。 | `test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback` |
| TC-COV-DMH-005 | 边界/异常 | 目标缺失 `SM/LM` 必须失败 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_memory_hierarchy_requires_sm_lm`。 | “目标缺失 `SM/LM` 必须失败”场景按公开错误语义失败或被拒绝。 | `test_dma_memory_hierarchy_requires_sm_lm` |
| TC-COV-DMH-006 | 内存/DMA | LM-only 输入不插入 staging（no-op） | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_memory_hierarchy_lm_only_is_noop`。 | 内存类型、布局、搬运结果或 verifier 行为体现“LM-only 输入不插入 staging（no-op）”场景。 | `test_dma_memory_hierarchy_lm_only_is_noop` |
| TC-COV-DMH-007 | 边界/异常 | 输入残留 `nn.*` 必须显式失败 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_memory_hierarchy_rejects_nn_ops_in_input`。 | “输入残留 `nn.*` 必须显式失败”场景按公开错误语义失败或被拒绝。 | `test_dma_memory_hierarchy_rejects_nn_ops_in_input` |
| TC-COV-DMH-008 | 内存/DMA | 窗口链路中 `GM -> SM` / `SM -> GM` 保留原窗口 `offsets/sizes` 并使用 unit stride，`SM -> LM` / `LM -> SM` 使用 `zero offsets + unit strides` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dma_memory_hierarchy_window_offsets_and_unit_strides`。 | 内存类型、布局、搬运结果或 verifier 行为体现“窗口链路中 `GM -> SM` / `SM -> GM` 保留原窗口 `offsets/sizes` 并使用 unit stride，`SM -> LM` / `LM -> SM` 使用 `zero offsets + unit strides`”场景。 | `test_dma_memory_hierarchy_window_offsets_and_unit_strides` |
| TC-COV-DMH-009 | pass 改写 | 显式 symbol shape 可透传到 staging `dma.alloc(dynamic_shape=...)` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_dma_memory_hierarchy_symbol_shape_passthrough`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“显式 symbol shape 可透传到 staging `dma.alloc(dynamic_shape=...)`”场景。 | `test_dma_memory_hierarchy_symbol_shape_passthrough` |
| TC-COV-DMH-010 | 边界/异常 | 匿名 `?` 且无可恢复 shape 来源时必须以 `dynamic_shape` 失败 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dma_memory_hierarchy_rejects_anonymous_dynamic_shape`。 | “匿名 `?` 且无可恢复 shape 来源时必须以 `dynamic_shape` 失败”场景按公开错误语义失败或被拒绝。 | `test_dma_memory_hierarchy_rejects_anonymous_dynamic_shape` |
