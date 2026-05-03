# default_lowering.md

## 功能简介

- 定义默认 lowering pipeline 的公开合同与 pass 顺序。
- 公开 builder：`build_default_lowering_pipeline()`。
- 收口默认 pipeline 对最小 `nn.add` memory-return 输入的黑盒可观察行为。

## API 列表

- `build_default_lowering_pipeline() -> PassManager`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/pipeline/default_lowering.md`](../../../spec/pass/pipeline/default_lowering.md)
- `功能实现`：[`kernel_gen/passes/pipeline/default_lowering.py`](../../../kernel_gen/passes/pipeline/default_lowering.py)
- `test`：[`test/passes/pipeline/test_default_lowering.py`](../../../test/passes/pipeline/test_default_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `nn -> kernel/dma` lowering：[`spec/pass/lowering/nn_lowering/spec.md`](../../../spec/pass/lowering/nn_lowering/spec.md)
- memory-return ABI 改写：[`spec/pass/buffer_results_to_out_params.md`](../buffer_results_to_out_params.md)
- DMA memory hierarchy lowering：[`spec/pass/lowering/dma_memory_hierarchy/spec.md`](../../../spec/pass/lowering/dma_memory_hierarchy/spec.md)
- `nn` 分解预处理：[`spec/pass/decompass.md`](../../../spec/pass/decompass.md)
- host launch outline：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)

## 术语

- `default-lowering`：默认 pipeline 名称。
- `lower-nn`：`NnLoweringPass` 的唯一公开 pass 名称。

## 目标

- 提供可复用的默认 lowering pipeline 构造器。
- 明确 pass 顺序，保证后续工具与测试有一致入口。
- 明确默认 pipeline 的黑盒结果应收口为前置 `out` 参数 ABI 与 `kernel.binary_elewise(kind="add")` 产物。

## API详细说明

### `build_default_lowering_pipeline() -> PassManager`

- api：`build_default_lowering_pipeline() -> PassManager`
- 参数：无。
- 返回值：`PassManager`。
- 使用示例：

  ```python
  from kernel_gen.passes.pipeline import build_default_lowering_pipeline

  pm = build_default_lowering_pipeline()
  module = pm.run(module)
  ```
- 功能说明：构造默认 lowering pipeline，并返回 `PassManager`。
- 注意事项：pipeline 名称为 `default-lowering`；pass 顺序必须为 `DecompassPass -> NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`；顺序说明、诊断文案与黑盒录制文本必须使用 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy`；不得继续使用 `lower-nn-to-kernel` 作为默认 pipeline 顺序口径；不得在 builder、顺序说明、黑盒验收或测试命令中隐式插入 `outline-device-kernel`；真实运行整条 pipeline 时，调用方必须保证 DMA memory hierarchy 所需 target 环境已准备就绪。

## 额外补充

- 黑盒最小链路的公开验收点：
  - 输入为 `nn.add` 的 memory-return `func.func` 时，输出函数必须变为 `3` 个输入、`0` 个输出。
  - 结果 IR 中至少应存在一个 `kernel.binary_elewise(kind="add")`。
  - 结果 IR 中应存在与 local memory hierarchy 对应的 `dma.slice` / `dma.deslice`。
- 失败边界的公开验收点：
  - 若把 `BufferResultsToOutParamsPass` 排在 `NnLoweringPass` 之前，必须显式失败。
  - 若输入包含当前不支持的 `nn` op，必须继续抛出 `KernelCodeError`，不得静默产出不合法 IR。
  - 若调用方需要 `outline-device-kernel`，必须在默认 pipeline 之外显式追加；当前任务链的正式验收只依赖 `pytest` 与顺序口径检查，架构侧 black-box runner 仅作补充对照。

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- builder 必须返回 `PassManager`。
- builder 必须通过 `register_pipeline("default-lowering")` 注册。
- registry 只负责注册与查询，不承载 builder 实现。
- 默认 pipeline 的公开 pass 顺序必须固定为：
  1. `DecompassPass`
  2. `NnLoweringPass`
  3. `BufferResultsToOutParamsPass`
  4. `LowerDmaMemoryHierarchyPass`
- 默认 pipeline 的公开口径必须使用 `NnLoweringPass` / `lower-nn`；`LowerNnToKernelPass` / `lower-nn-to-kernel` 只属于 lowering 层兼容入口，不得作为 `default-lowering` 的验收文案或黑盒顺序描述。
- `default-lowering remains unchanged`：`outline-device-kernel` 不属于默认 pipeline，调用方若需要 host launch outline，必须显式追加 standalone pass。
- 对最小 `nn.add` memory-return 输入执行整条 pipeline 后，结果必须满足：
  - 原 `func.func` ABI 改写为前置 `out` 参数，函数返回值清空。
  - 函数体内不再残留 `nn.add` 等原始 `nn` op。
  - 计算节点收口为 `kernel.binary_elewise(kind="add")`。
  - `LowerDmaMemoryHierarchyPass` 产生的 `dma.slice / dma.deslice` 链必须包裹上述 kernel 计算。
- builder 不负责吞掉下游 pass 抛出的异常；遇到不支持的 `nn` op 时，错误应由 `NnLoweringPass` 继续显式抛出。

## 测试

- 测试文件：`test/passes/pipeline/test_default_lowering.py`
- 执行命令：`pytest -q test/passes/pipeline/test_default_lowering.py`

### 测试目标

- 验证 `spec/pass/pipeline/default_lowering.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-PIPELINE-DEFAULT-LOWERING-001 | pass 改写 | `test_default_lowering_pipeline_builds_pass_manager` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_default_lowering_pipeline_builds_pass_manager`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_default_lowering_pipeline_builds_pass_manager`”场景。 | `test_default_lowering_pipeline_builds_pass_manager` |
| TC-PASS-PIPELINE-DEFAULT-LOWERING-002 | pass 改写 | `test_default_lowering_pipeline_pass_order` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_default_lowering_pipeline_pass_order`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_default_lowering_pipeline_pass_order`”场景。 | `test_default_lowering_pipeline_pass_order` |
| TC-PASS-PIPELINE-DEFAULT-LOWERING-003 | 公开入口 | 顺序错误时显式失败。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `CASE-0`。 | 公开入口在“顺序错误时显式失败。”场景下可导入、构造、注册或按名称发现。 | `CASE-0` |
| TC-PASS-PIPELINE-DEFAULT-LOWERING-004 | pass 改写 | 默认 pipeline 顺序录制为 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy`。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `CASE-1`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“默认 pipeline 顺序录制为 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy`。”场景。 | `CASE-1` |
| TC-PASS-PIPELINE-DEFAULT-LOWERING-005 | 公开入口 | `nn.add` 黑盒结果收口为前置 `out` 参数 ABI 与 `kernel.binary_elewise(kind="add")`。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `CASE-2`。 | 公开入口在“`nn.add` 黑盒结果收口为前置 `out` 参数 ABI 与 `kernel.binary_elewise(kind="add")`。”场景下可导入、构造、注册或按名称发现。 | `CASE-2` |
| TC-PASS-PIPELINE-DEFAULT-LOWERING-006 | 公开入口 | 不支持的 `nn` op 显式失败。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `CASE-3`。 | 公开入口在“不支持的 `nn` op 显式失败。”场景下可导入、构造、注册或按名称发现。 | `CASE-3` |
