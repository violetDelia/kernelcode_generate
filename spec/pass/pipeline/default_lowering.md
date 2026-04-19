# default_lowering.md

## 功能简介

- 定义默认 lowering pipeline 的公开合同与 pass 顺序。
- 公开 builder：`build_default_lowering_pipeline()`。
- 收口默认 pipeline 对最小 `nn.add` memory-return 输入的黑盒可观察行为。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/pipeline/default_lowering.md`](../../../spec/pass/pipeline/default_lowering.md)
- `功能实现`：[`kernel_gen/passes/pipeline/default_lowering.py`](../../../kernel_gen/passes/pipeline/default_lowering.py)
- `test`：[`test/pass/test_pipeline_default_lowering.py`](../../../test/pass/test_pipeline_default_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `nn -> kernel/dma` lowering：[`spec/pass/lowering/nn_lowering.md`](../../../spec/pass/lowering/nn_lowering.md)
- memory-return ABI 改写：[`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- DMA memory hierarchy lowering：[`spec/pass/lowering/dma_memory_hierarchy.md`](../../../spec/pass/lowering/dma_memory_hierarchy.md)
- `nn` 分解预处理：[`spec/pass/decompass.md`](../../../spec/pass/decompass.md)
- host launch outline：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)

## 术语

- `default-lowering`：默认 pipeline 名称。
- `lower-nn`：`NnLoweringPass` 的唯一公开 pass 名称。

## 目标

- 提供可复用的默认 lowering pipeline 构造器。
- 明确 pass 顺序，保证后续工具与测试有一致入口。
- 明确默认 pipeline 的黑盒结果应收口为前置 `out` 参数 ABI 与 `kernel.binary_elewise(kind="add")` 产物。

## 限制与边界

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

## 公开接口

### `build_default_lowering_pipeline() -> PassManager`

功能说明：

- 构造默认 lowering pipeline，并返回 `PassManager`。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.passes.pipeline import build_default_lowering_pipeline

pm = build_default_lowering_pipeline()
module = pm.run(module)
```

注意事项：

- pipeline 名称为 `default-lowering`。
- pass 顺序必须为：
  1. `DecompassPass`
  2. `NnLoweringPass`
  3. `BufferResultsToOutParamsPass`
  4. `LowerDmaMemoryHierarchyPass`
- 顺序说明、诊断文案与黑盒录制文本必须使用 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy`，不得继续使用 `lower-nn-to-kernel` 作为默认 pipeline 顺序口径。
- `default-lowering remains unchanged`：不得在 builder、顺序说明、黑盒 expectation 或测试命令中隐式插入 `outline-device-kernel`。
- 对最小 `nn.add` memory-return 输入运行该 pipeline 时，调用方应看到前置 `out` 参数 ABI、`kernel.binary_elewise(kind="add")` 与 `dma.slice / dma.deslice` 链；这属于默认 pipeline 的公开黑盒行为。

返回与限制：

- 返回 `PassManager` 实例。
- 真实运行整条 pipeline 时，调用方必须保证 DMA memory hierarchy 所需 target 环境已准备就绪。

## 额外补充

- 黑盒最小链路的公开验收点：
  - 输入为 `nn.add` 的 memory-return `func.func` 时，输出函数必须变为 `3` 个输入、`0` 个输出。
  - 结果 IR 中至少应存在一个 `kernel.binary_elewise(kind="add")`。
  - 结果 IR 中应存在与 local memory hierarchy 对应的 `dma.slice` / `dma.deslice`。
- 失败边界的公开验收点：
  - 若把 `BufferResultsToOutParamsPass` 排在 `NnLoweringPass` 之前，必须显式失败。
  - 若输入包含当前不支持的 `nn` op，必须继续抛出 `NnLoweringError`，不得静默产出不合法 IR。
  - 若调用方需要 `outline-device-kernel`，必须在默认 pipeline 之外显式追加；当前任务链的正式验收只依赖 `pytest` 与顺序口径检查，架构侧 black-box runner 仅作补充对照。

## 测试

- 测试文件：[`test/pass/test_pipeline_default_lowering.py`](../../../test/pass/test_pipeline_default_lowering.py)
- 执行命令：
  - `pytest -q test/pass/test_pipeline_default_lowering.py`
  - `rg -n "decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy" spec/pass/pipeline/default_lowering.md`
- 测试目标：
  - pipeline 名称与 pass 顺序可验证。
  - builder 返回 `PassManager`。
  - 黑盒最小链路可验证前置 `out` 参数 ABI、`kernel.binary_elewise(kind="add")` 与 `dma.slice / dma.deslice`。
  - 顺序错误与不支持 op 的失败边界可验证。
  - `default-lowering remains unchanged`，不把 `outline-device-kernel` 混入默认 pipeline。
  - 当前任务链的正式验收不依赖 `worktree` 内本地 `expectation` 副本；若现场具备架构侧 runner，可另做补充对照。
- 功能与用例清单：
  - `test_default_lowering_pipeline_builds_pass_manager`
  - `test_default_lowering_pipeline_pass_order`
  - `CASE-0`：顺序错误时显式失败。
  - `CASE-1`：默认 pipeline 顺序录制为 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy`。
  - `CASE-2`：`nn.add` 黑盒结果收口为前置 `out` 参数 ABI 与 `kernel.binary_elewise(kind="add")`。
  - `CASE-3`：不支持的 `nn` op 显式失败。
