# npu_demo_lowering.md

## 功能简介

- 定义 `npu-demo-lowering` pipeline 的公开合同与 pass 顺序。
- 当前文件只公开 pipeline builder：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`。
- 该 pipeline 面向 `npu_demo` 的 pass/pipeline 正向链路，固定为最小可执行 lowering 组合，并在末尾输出可供 `gen_kernel(...)` / `emit_c(...)` 消费的 host wrapper + device body + 默认 cost function IR。
- registry 名称 `npu-demo-lowering` 仍属于 [`spec/pass/registry.md`](../../../spec/pass/registry.md) 的公开入口；当前文件不额外公开 builder 之外的模块级 helper。

## API 列表

- `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/pipeline/npu_demo_lowering.md`](../../../spec/pass/pipeline/npu_demo_lowering.md)
- `功能实现`：[`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
- `test`：[`test/pass/test_pipeline_npu_demo_lowering.py`](../../../test/pass/test_pipeline_npu_demo_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `inline` 公开入口：[`spec/pass/inline.md`](../../../spec/pass/inline.md)
- `decompass` 公开入口：[`spec/pass/decompass.md`](../../../spec/pass/decompass.md)
- `nn` lowering：[`spec/pass/lowering/nn_lowering/spec.md`](../../../spec/pass/lowering/nn_lowering/spec.md)
- `symbol-loop-hoist`：[`spec/pass/symbol_loop_hoist.md`](../../../spec/pass/symbol_loop_hoist.md)
- `symbol-buffer-hoist`：[`spec/pass/symbol_buffer_hoist.md`](../../../spec/pass/symbol_buffer_hoist.md)
- `attach-arch-information` 公开入口：[`spec/pass/attach_arch_information.md`](../../../spec/pass/attach_arch_information.md)
- `outline-device-kernel` 公开入口：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)
- `launch-kernel-cost-func` 公开入口：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../spec/pass/tuning/launch_kernel_cost_func.md)

## 术语

- `npu-demo-lowering`：`npu_demo` 目标的公开 pipeline 名称。
- `inline`：该 pipeline 的首个内联/展开阶段。
- `lower-nn`：`NnLoweringPass` 的公开 pass 名称。
- `symbol-loop-hoist`：`SymbolLoopHoistPass` 的公开 pass 名称。
- `symbol-buffer-hoist`：`SymbolBufferHoistPass` 的公开 pass 名称。
- `attach-arch-information`：在 outline 前为目标函数附加 launch / shared memory 等 arch 元信息的阶段。
- `outline-device-kernel`：将带 arch 元信息的函数 outline 成 host wrapper + device body 的阶段。
- `launch-kernel-cost-func`：在 pipeline 末尾为 outlined device body 生成 sibling cost function 的阶段，默认 `cost_kind` 为 `DMA|MAC`。

## 目标

- 提供一条不依赖 `tile` 的最小公开 pipeline，供本轮 `pytest` 与 standalone 验收链直接复用。
- 明确 `symbol-loop-hoist` 在无 `symbol.for` 时可以 no-op，因此可安全加入该最小 pipeline。
- 明确 `symbol-buffer-hoist` 位于 `symbol-loop-hoist` 之后，对 `symbol.for` 内安全 `dma.alloc` 做 buffer 外提；无可外提 buffer 时保持 no-op。
- 明确该 pipeline 的最终输出为 host wrapper + device body + `_cost_DMA_*` / `_cost_MAC_*` sibling cost function IR，供 `gen_kernel(...)` 直接消费。
- 当输入 DSL callable 除 `lhs/rhs/out` 外还包含公开 `SymbolDim` tile / shape 参数时，pipeline 输出的 host wrapper、device body 与 sibling cost function 必须继续保留这些 trailing `!symbol.int` 参数，供 `gen_kernel(...)` 直接消费。
- 保持 `default-lowering` 作为独立公开 builder，不与本 pipeline 混用。

## 限制与边界

- builder 必须返回 `PassManager`。
- builder 必须通过 `register_pipeline("npu-demo-lowering")` 注册。
- builder 允许 `options={"target": "npu_demo"}`，空字典与 `None` 表示默认 target；`only-kernel`、`only_kernel` 或其他选项都必须显式失败。
- 当前文件允许存在用于 pass 顺序、默认 target 或错误文本规整的当前文件内 helper，但这些 helper 不是公开 API；实现、其他模块与测试不得跨文件直连。
- 公开顺序必须固定为：
  1. `InlinePass`
  2. `DecompassPass`
  3. `NnLoweringPass`
  4. `SymbolLoopHoistPass`
  5. `SymbolBufferHoistPass`
  6. `AttachArchInformationPass`
  7. `OutlineDeviceKernelPass`
  8. `LaunchKernelCostFuncPass`
- 该 pipeline 不包含 `tile`、`buffer-results-to-out-params` 或 `lower-dma-memory-hierarchy`。
- 若输入 module 中不存在 `symbol.for`，`SymbolLoopHoistPass` 必须保持 no-op。
- 若输入 module 中不存在可安全外提的 `dma.alloc`，`SymbolBufferHoistPass` 必须保持 no-op。
- builder 会把默认 `target` 收口为 `npu_demo`。

## 公开接口

### `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

功能说明：

- 构造 `npu-demo-lowering` pipeline，并返回 `PassManager`。

参数说明：

- `options (dict[str, str] | None)`：可选选项字典；当前允许 `{"target": "npu_demo"}`，空字典与 `None` 表示使用默认 target。

使用示例：

```python
from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline

pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
module = pm.run(module)
```

注意事项：

- pipeline 名称必须固定为 `npu-demo-lowering`。
- pass 顺序必须固定为 `inline -> decompass -> lower-nn -> symbol-loop-hoist -> symbol-buffer-hoist -> attach-arch-information -> outline-device-kernel -> launch-kernel-cost-func`。
- 该 pipeline 是本轮 `pass/pipeline` 公开主合同，不要求 `tile` 先行。
- pipeline 中的 `LaunchKernelCostFuncPass` 使用 pass 默认 `cost_kind="DMA|MAC"`，builder 不新增 cost kind 选项。
- 该 pipeline 不接受 `only-kernel` 选项；任何 options 输入都必须显式失败。

返回与限制：

- 返回 `PassManager` 实例。

## 测试

- 测试文件：[`test/pass/test_pipeline_npu_demo_lowering.py`](../../../test/pass/test_pipeline_npu_demo_lowering.py)
- 执行命令：`pytest -q test/pass/test_pipeline_npu_demo_lowering.py`
- 测试目标：
  - builder 返回 `PassManager`
  - pipeline 名称为 `npu-demo-lowering`
  - pass 顺序固定为 `inline -> decompass -> lower-nn -> symbol-loop-hoist -> symbol-buffer-hoist -> attach-arch-information -> outline-device-kernel -> launch-kernel-cost-func`
  - `symbol-loop-hoist` 在无 `symbol.for` 时可安全加入该 pipeline
  - `symbol-buffer-hoist` 位于 `symbol-loop-hoist` 之后，且无可外提 buffer 时可安全 no-op
  - pipeline 输出 host wrapper + device body + `_cost_DMA_*` / `_cost_MAC_*` sibling cost function IR
  - pipeline 输出的 wrapper/body/cost function 会保留 trailing `!symbol.int` tile / shape 参数，供 `gen_kernel(...)` 直接发射
  - `only-kernel` / `only_kernel` options 显式失败
  - registry 透传 `npu-demo-lowering` 时只经由公开 builder，不依赖当前文件内非公开 helper
