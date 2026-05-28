# cuda_sm86_lowering.md

## 功能简介

- 定义 `cuda-sm86-lowering` pipeline 的公开合同与 pass 顺序。
- 当前文件只公开 pipeline builder：`build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`。
- 该 pipeline 面向 `cuda_sm86` target，复用通用 NN / tile / tuning / outline 能力，并明确不接入 `MemoryPoolPass(rewrite=True)`，避免把 TLM fragment 改写为 dynamic byte pool。

## API 列表

- `build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

## 文档信息

- `spec`：[`spec/pass/pipeline/cuda_sm86_lowering.md`](../../../spec/pass/pipeline/cuda_sm86_lowering.md)
- `功能实现`：[`kernel_gen/pipeline/cuda_sm86_lowering.py`](../../../kernel_gen/pipeline/cuda_sm86_lowering.py)
- `test`：[`test/passes/pipeline/test_cuda_sm86_lowering.py`](../../../test/passes/pipeline/test_cuda_sm86_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- npu-demo pipeline 共享 pass：[`spec/pass/pipeline/npu_demo_lowering.md`](../../../spec/pass/pipeline/npu_demo_lowering.md)

## API详细说明

### `build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

- api：`build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
- 参数：
  - `options`：pipeline 选项字典；类型 `dict[str, str] | None`；默认值 `None`；当前仅允许 `target` 键，且合法值必须为 `"cuda_sm86"`。
- 返回值：`PassManager`。
- 使用示例：

  ```python
  from kernel_gen.pipeline import build_cuda_sm86_lowering_pipeline

  pm = build_cuda_sm86_lowering_pipeline({"target": "cuda_sm86"})
  lowered = pm.run(module)
  ```
- 功能说明：构造 `cuda-sm86-lowering` pipeline，并返回 `PassManager(name="cuda-sm86-lowering")`。
- 注意事项：
  - pipeline 名称必须固定为 `cuda-sm86-lowering`。
  - 只允许 `target` option；未知 option 必须失败。
  - `target` 只能为 `cuda_sm86`，不得回退到 `npu_demo` 或 `cpu`。
  - 公开顺序必须固定为：`InlinePass -> cse -> canonicalize -> DecompassPass -> NnLoweringPass -> MemoryPlanPass(insert_free=True, reuse=True, fold=False) -> SymbolHoistPipelinePass -> cse -> canonicalize -> TileAnalysisPass -> KernelPatternAttachPass -> TransformApplyPass -> MemoryPlanPass(insert_free=True, reuse=True, fold=False) -> SymbolHoistPipelinePass -> cse -> canonicalize -> KernelAggregatePass(matmul_acc=True) -> KernelDecomposePass -> MemoryPlanPass(insert_free=True, reuse=True, fold=False) -> SymbolHoistPipelinePass -> cse -> canonicalize -> ProducerConsumerAnalysisPass -> canonicalize -> ArchParallelizePass(target="cuda_sm86", parallel_level="block") -> AttachArchInformationPass(target="cuda_sm86") -> OutlineDeviceKernelPass -> TemplateNameInferPass`。
  - CUDA pipeline 内的 arch mapping 只在 standalone `ArchParallelizePass` 可证明支持的 IR 上生效；9 个现有 demo 中暂不支持的复杂 pattern region 由 pipeline 局部适配为保守 no-op，后续 generated source 仍由 `cuda_sm86` backend 承载具体 kernel，不改变 standalone `ArchParallelizePass` 公开失败合同。
  - 当前 pipeline 不包含 `MemoryPoolPass`；TLM1/TLM2/TLM3 不得通过 memory-pool 变成 `arch.get_dynamic_memory + dma.reinterpret` byte pool 形态。

## 测试

- 测试文件：`test/passes/pipeline/test_cuda_sm86_lowering.py`
- 执行命令：`pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py`

### 测试目标

- 验证公开 builder 与 registry 名称可构造。
- 验证非法 option 和非 CUDA target 按公开错误语义失败。
- 验证 pipeline 公开顺序和“不包含 memory-pool”边界。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CUDA-SM86-PIPELINE-001 | 公开入口 | 构造 builder 与 registry pipeline。 | 已导入 pipeline package。 | 运行 `test_cuda_sm86_lowering_pipeline_builds_pass_manager`。 | 返回 `PassManager(name="cuda-sm86-lowering")`，registry 可见同名 pipeline。 | `test_cuda_sm86_lowering_pipeline_builds_pass_manager` |
| TC-CUDA-SM86-PIPELINE-002 | 边界/异常 | 拒绝非 CUDA target 与未知 option。 | 准备非法 options。 | 运行 `test_cuda_sm86_lowering_pipeline_rejects_non_cuda_target`。 | 抛出 `KernelCodeError`。 | `test_cuda_sm86_lowering_pipeline_rejects_non_cuda_target` |
| TC-CUDA-SM86-PIPELINE-003 | pass 顺序 | 运行公开 pipeline 并记录 apply 顺序。 | monkeypatch 各公开 pass 的 `apply(...)`。 | 运行 `test_cuda_sm86_lowering_pipeline_order_has_no_memory_pool`。 | 顺序与 spec 一致，且不出现 `memory-pool`。 | `test_cuda_sm86_lowering_pipeline_order_has_no_memory_pool` |
