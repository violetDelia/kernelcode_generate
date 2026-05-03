# npu_demo_lowering.md

## 功能简介

- 定义 `npu-demo-lowering` pipeline 的公开合同与 pass 顺序。
- 当前文件只公开 pipeline builder：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`。
- 该 pipeline 面向 `npu_demo` 的 pass/pipeline 正向链路，固定为最小可执行 lowering 组合，并在末尾输出可供 `gen_kernel(...)` / `emit_c(...)` 消费的 host wrapper + device body + 默认 cost function IR。
- registry 名称 `npu-demo-lowering` 仍属于 [`spec/pass/registry.md`](../../../spec/pass/registry.md) 的公开入口；当前文件不额外公开 builder 之外的模块级 helper。

## API 列表

- `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/pipeline/npu_demo_lowering.md`](../../../spec/pass/pipeline/npu_demo_lowering.md)
- `功能实现`：[`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
- `test`：[`test/passes/pipeline/test_npu_demo_lowering.py`](../../../test/passes/pipeline/test_npu_demo_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `inline` 公开入口：[`spec/pass/inline.md`](../../../spec/pass/inline.md)
- xdsl `cse`：`xdsl.transforms.common_subexpression_elimination.CommonSubexpressionElimination`
- `decompass` 公开入口：[`spec/pass/decompass.md`](../../../spec/pass/decompass.md)
- `nn` lowering：[`spec/pass/lowering/nn_lowering/spec.md`](../../../spec/pass/lowering/nn_lowering/spec.md)
- `symbol-loop-hoist`：[`spec/pass/symbol_loop_hoist.md`](../../../spec/pass/symbol_loop_hoist.md)
- `tile-analysis`：[`spec/pass/tile/analysis.md`](../../../spec/pass/tile/analysis.md)
- `symbol-buffer-hoist`：[`spec/pass/symbol_buffer_hoist.md`](../../../spec/pass/symbol_buffer_hoist.md)
- `attach-arch-information` 公开入口：[`spec/pass/attach_arch_information.md`](../../../spec/pass/attach_arch_information.md)
- `outline-device-kernel` 公开入口：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)
- `launch-kernel-cost-func` 公开入口：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../spec/pass/tuning/launch_kernel_cost_func.md)

## 术语

- `npu-demo-lowering`：`npu_demo` 目标的公开 pipeline 名称。
- `inline`：该 pipeline 的首个内联/展开阶段。
- `cse`：公共子表达式消除阶段；本 pipeline 中第一次紧跟 `inline`，第二次紧跟 `symbol-loop-hoist`。
- `lower-nn`：`NnLoweringPass` 的公开 pass 名称。
- `symbol-loop-hoist`：`SymbolLoopHoistPass` 的公开 pass 名称。
- `tile-analysis`：`TileAnalysisPass` 的公开 pass 名称；本 pipeline 中紧跟 `symbol-loop-hoist` 后置 `cse`，只补充 tile 分析属性。
- `symbol-buffer-hoist`：`SymbolBufferHoistPass` 的公开 pass 名称。
- `attach-arch-information`：在 outline 前为目标函数附加 launch / shared memory 等 arch 元信息的阶段。
- `outline-device-kernel`：将带 arch 元信息的函数 outline 成 host wrapper + device body 的阶段。
- `launch-kernel-cost-func`：在 pipeline 末尾为 outlined device body 生成 sibling cost function 的阶段，默认 `cost_kind` 为 `DMA|MAC`。

## 目标

- 提供一条不依赖 `tile` 的最小公开 pipeline，供本轮 `pytest` 与 standalone 验收链直接复用。
- 明确 `symbol-loop-hoist` 在无 `symbol.for` 时可以 no-op，因此可安全加入该最小 pipeline。
- 明确 `tile-analysis` 位于 `symbol-loop-hoist` 后置 `cse` 之后、`symbol-buffer-hoist` 之前，只记录 tile 分析结果，不生成 tile 循环。
- 明确 `symbol-buffer-hoist` 位于 `tile-analysis` 之后，对 `symbol.for` 内安全 `dma.alloc` 做 buffer 外提；无可外提 buffer 时保持 no-op。
- 明确该 pipeline 的最终输出为 host wrapper + device body + `_cost_DMA_*` / `_cost_MAC_*` sibling cost function IR，供 `gen_kernel(...)` 直接消费。
- 当输入 DSL callable 除 `lhs/rhs/out` 外还包含公开 `SymbolDim` tile / shape 参数时，pipeline 输出的 host wrapper、device body 与 sibling cost function 必须继续保留这些 trailing `!symbol.int` 参数，供 `gen_kernel(...)` 直接消费。
- 保持 `default-lowering` 作为独立公开 builder，不与本 pipeline 混用。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- builder 必须返回 `PassManager`。
- builder 必须通过 `register_pipeline("npu-demo-lowering")` 注册。
- builder 允许 `options={"target": "npu_demo"}`，空字典与 `None` 表示默认 target；`only-kernel`、`only_kernel` 或其他选项都必须显式失败。
- 当前文件允许存在用于 pass 顺序、默认 target 或错误文本规整的当前文件内 helper，但这些 helper 不是公开 API；实现、其他模块与测试不得跨文件直连。
- 公开顺序必须固定为：
  1. `InlinePass`
  2. `CommonSubexpressionElimination`
  3. `DecompassPass`
  4. `NnLoweringPass`
  5. `SymbolLoopHoistPass`
  6. `CommonSubexpressionElimination`
  7. `TileAnalysisPass`
  8. `SymbolBufferHoistPass`
  9. `AttachArchInformationPass`
  10. `OutlineDeviceKernelPass`
  11. `LaunchKernelCostFuncPass`
- 该 pipeline 不包含 `tile-elewise`、`tile-reduce`、`buffer-results-to-out-params` 或 `lower-dma-memory-hierarchy`。
- 若输入 module 中不存在 `symbol.for`，`SymbolLoopHoistPass` 必须保持 no-op。
- 若输入 module 中不存在可安全外提的 `dma.alloc`，`SymbolBufferHoistPass` 必须保持 no-op。
- builder 会把默认 `target` 收口为 `npu_demo`。
## API详细说明

### `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

- api：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
- 参数：
  - `options`：pipeline 选项字典；类型 `dict[str, str] | None`；默认值 `None`；当前仅允许 `target` 键；`None` 与空字典表示使用默认 target `"npu_demo"`。
- 返回值：`PassManager`。
- 使用示例：

  ```python
  from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline

  pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
  module = pm.run(module)
  ```
- 功能说明：构造 `npu-demo-lowering` pipeline，并返回 `PassManager`。
- 注意事项：pipeline 名称必须固定为 `npu-demo-lowering`；pass 顺序必须固定为 `inline -> cse -> decompass -> lower-nn -> symbol-loop-hoist -> cse -> tile-analysis -> symbol-buffer-hoist -> attach-arch-information -> outline-device-kernel -> launch-kernel-cost-func`；`cse` 必须紧跟 `inline`，第二个 `cse` 必须紧跟 `symbol-loop-hoist`；`tile-analysis` 只添加 `tile.analysis` / `tile.tile_exprs` 等分析属性，不生成 `symbol.for` 或 `dma.view`；pipeline 中的 `LaunchKernelCostFuncPass` 使用 pass 默认 `cost_kind="DMA|MAC"`，builder 不新增 cost kind 选项；`only-kernel`、`only_kernel` 或其他未知 options 输入必须显式失败。

## 测试

- 测试文件：`test/passes/pipeline/test_npu_demo_lowering.py`
- 执行命令：`pytest -q test/passes/pipeline/test_npu_demo_lowering.py`

### 测试目标

- 验证 `spec/pass/pipeline/npu_demo_lowering.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-001 | pass 改写 | npu demo lowering pipeline builds pass manager | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_npu_demo_lowering_pipeline_builds_pass_manager`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“npu demo lowering pipeline builds pass manager”场景。 | `test_npu_demo_lowering_pipeline_builds_pass_manager` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-002 | pass 改写 | npu demo lowering pipeline pass order | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_npu_demo_lowering_pipeline_pass_order`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“npu demo lowering pipeline pass order”场景。 | `test_npu_demo_lowering_pipeline_pass_order` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-003 | 边界/异常 | npu demo lowering pipeline rejects unknown option | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_npu_demo_lowering_pipeline_rejects_unknown_option`。 | “npu demo lowering pipeline rejects unknown option”场景按公开错误语义失败或被拒绝。 | `test_npu_demo_lowering_pipeline_rejects_unknown_option` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-004 | 公开入口 | npu demo lowering pipeline supports kernel contract style public chain | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain`。 | 公开入口在“npu demo lowering pipeline supports kernel contract style public chain”场景下可导入、构造、注册或按名称发现。 | `test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain` |
