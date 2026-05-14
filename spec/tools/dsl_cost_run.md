# dsl_cost_run

## 功能简介

- 定义 `dsl_cost_run(func_obj, real_args, pipeline, cost_kind)` 的公开工具入口。
- 该入口只面向 `target="npu_demo"`，在 `mlir_gen -> pipeline -> gen_kernel -> ExecutionEngine` 链路上选择 `_cost_<cost_kind>_*` sibling cost function 并返回真实 `int` cost。
- `dsl_cost_run(...)` 不改变 `dsl_run(...)` 的返回模型，不给 `dsl_run(...)` 增加 `cost_kind` 参数，也不在缺少 cost sibling 时 fallback 到普通 kernel。

## API 列表

- `dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`

## 文档信息

- `spec`：[`spec/tools/dsl_cost_run.md`](../../spec/tools/dsl_cost_run.md)
- `功能实现`：[`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)、[`kernel_gen/tools/__init__.py`](../../kernel_gen/tools/__init__.py)
- `test`：[`test/tools/test_dsl_cost_run.py`](../../test/tools/test_dsl_cost_run.py)、[`test/tools/test_package.py`](../../test/tools/test_package.py)

## 依赖

- DSL 解析：[`spec/dsl/ast/mlir_gen.md`](../../spec/dsl/ast/mlir_gen.md)
- 源码生成：[`spec/dsl/gen_kernel/gen_kernel.md`](../../spec/dsl/gen_kernel/gen_kernel.md)
- 执行引擎：[`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md)
- pass / pipeline：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)、[`spec/pass/registry.md`](../../spec/pass/registry.md)
- cost pass：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../spec/pass/tuning/launch_kernel_cost_func.md)

## API详细说明

### `dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`

- api：`dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`
- 参数：
  - `func_obj`：DSL callable；类型 `Callable[..., DslFunctionReturn]`；无默认值。
  - `real_args`：运行期真实实参；类型 `tuple[RuntimeRealArg, ...] | list[RuntimeRealArg]`；校验规则与 `dsl_run(...)` 一致。
  - `pipeline`：pipeline 名称或 `PassManager`；类型 `str | PassManager`；校验规则与 `dsl_run(...)` 一致。
  - `cost_kind`：成本统计视角；类型 `str`；无默认值；只接受 `DMA1`、`DMA2`、`DMA3`、`DMA4`、`MAC`、`VECTOR1`、`VECTOR2`。
- 返回值：`int`，对应 `_cost_<cost_kind>_<device body>` 的 `S_INT` 返回值。
- 使用示例：

  ```python
  import numpy as np

  from kernel_gen.core.config import set_target
  from kernel_gen.operation import store
  from kernel_gen.tools import dsl_cost_run

  def add_kernel(out, lhs, rhs):
      store(out, lhs + rhs, [0], [128], [1])

  out = np.zeros((128,), dtype=np.int32)
  lhs = np.arange(128, dtype=np.int32)
  rhs = np.arange(128, dtype=np.int32)
  set_target("npu_demo")
  cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")
  assert isinstance(cost, int)
  ```
- 功能说明：生成并执行 npu_demo cost sibling function，返回该 sibling 的真实成本值。
- 注意事项：
  - `cost_kind` 必须显式提供；本接口不提供默认值。
  - `DMA1/DMA2/DMA3/DMA4` 返回同一 cost function 内匹配 DMA helper 的有效字节总和取整结果，即 `ceil(total_matching_bytes / 64)`。
  - DMA 聚合只允许通过 `dsl_cost_run(...)` 生成源码中的本地 raw-bytes helper 完成；生成源码和 include 公开层不得跨文件调用 `npu_demo::cost::detail` 非公开聚合状态。
  - target 只能是 `npu_demo`；其他 target 必须失败，固定短语为 `DslCostRunInvalidTarget: dsl_cost_run only supports target 'npu_demo'`。
  - 非法 `cost_kind` 必须失败，固定短语为 `DslCostRunInvalidCostKind: cost_kind must be one of ['DMA', 'MAC']`；`DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 仍作为 npu_demo 七类 kind 兼容执行。
  - lowering 后缺少 `_cost_<cost_kind>_*` sibling 必须失败，固定短语前缀为 `DslCostRunMissingCostFunction:`。
  - 执行失败必须抛 `KernelCodeError(ErrorModule.TOOLS, ...)`，固定短语为 `DslCostRunExecutionFailed: cost wrapper execution failed`。
  - 捕获 C++ `S_INT` 返回值所需的 wrapper 只属于 `kernel_gen/tools/dsl_run.py` 当前文件内部实现，不是公开 include、执行引擎或测试 API。

## 测试

- 测试文件：
  - `test/tools/test_dsl_cost_run.py`
  - `test/tools/test_package.py`
- 执行命令：
  - `pytest -q test/tools/test_dsl_cost_run.py test/tools/test_package.py`

### 测试目标

- 验证包根与模块入口可公开导入。
- 验证 `VECTOR1` 返回真实非零成本，`DMA1/DMA2` 按同一 cost function 内匹配 DMA 总字节数统一取整，`VECTOR2` 返回 `0`。
- 验证 DMA 聚合生成源码不依赖 `npu_demo::cost::detail` 非公开 helper。
- 验证 rank=2 `store(...)` 写回可通过 `dsl_cost_run(...)` 编译执行，且普通写回行不再使用裸 `{..}` layout。
- 验证旧 `compute` kind 按公开错误语义失败。
- 验证缺少 `_cost_<kind>_*` sibling 时按 `DslCostRunMissingCostFunction` 失败，且不 fallback 到普通 kernel。
- 验证非 `npu_demo` target 按 `DslCostRunInvalidTarget` 失败。
- 验证 `numpy.ndarray` 与 `torch.Tensor` 混用运行参数仍可通过公开入口返回 cost。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-TOOLS-DSL-COST-RUN-001 | 执行结果 | VECTOR1 cost | 准备 npu_demo add kernel 与公开真实参数。 | 运行 `test_dsl_cost_run_returns_public_vector1_cost`。 | 返回 `int` 且非零。 | `test_dsl_cost_run_returns_public_vector1_cost` |
| TC-TOOLS-DSL-COST-RUN-002 | 执行结果 | DMA aggregate cost | 准备两路 GM->TSM slice 与一路 TSM->GM store，且单路字节数不能整除 64 的 npu_demo add kernel。 | 运行 `test_dsl_cost_run_returns_dma1_aggregate_cost`。 | `DMA1` 返回 `ceil((lhs_bytes + rhs_bytes) / 64)`，`DMA2` 返回 `ceil(out_bytes / 64)`。 | `test_dsl_cost_run_returns_dma1_aggregate_cost` |
| TC-TOOLS-DSL-COST-RUN-003 | 边界/异常 | DMA aggregate source avoids private detail | 开启 `dump_dir` 并运行 DMA1 cost。 | 运行 `test_dsl_cost_run_dma_source_avoids_non_public_detail_helpers`。 | 生成源码不出现 `npu_demo::cost::detail`、`reset_dma_cost_accumulator` 或 `finalize_dma_cost_accumulator`。 | `test_dsl_cost_run_dma_source_avoids_non_public_detail_helpers` |
| TC-TOOLS-DSL-COST-RUN-003A | 执行结果 | rank2 store layout compiles | 准备 rank=2 显式 `slice + add + store` kernel。 | 运行 `test_dsl_cost_run_compiles_rank2_store_vector_layout`。 | `DMA1/DMA2` 返回公开公式成本，生成源码中的普通 `store(...)` 行不再使用裸 `{..}` layout，并可真实编译执行。 | `test_dsl_cost_run_compiles_rank2_store_vector_layout` |
| TC-TOOLS-DSL-COST-RUN-004 | 执行结果 | VECTOR2 cost | 准备 npu_demo add kernel 与公开真实参数。 | 运行 `test_dsl_cost_run_returns_zero_for_vector2_reserved_kind`。 | 返回 `0`。 | `test_dsl_cost_run_returns_zero_for_vector2_reserved_kind` |
| TC-TOOLS-DSL-COST-RUN-005 | 边界/异常 | 旧 kind | 传入旧 `compute` kind。 | 运行 `test_dsl_cost_run_rejects_old_cost_kind`。 | 按 `DslCostRunInvalidCostKind` 失败。 | `test_dsl_cost_run_rejects_old_cost_kind` |
| TC-TOOLS-DSL-COST-RUN-006 | 边界/异常 | 缺少 cost sibling 且禁止 fallback | 准备不包含 `LaunchKernelCostFuncPass` 的公开 `PassManager` 链路。 | 运行 `test_dsl_cost_run_rejects_missing_cost_sibling_without_fallback`。 | 按 `DslCostRunMissingCostFunction` 失败，输出参数保持原值，不 fallback 到普通 kernel。 | `test_dsl_cost_run_rejects_missing_cost_sibling_without_fallback` |
| TC-TOOLS-DSL-COST-RUN-007 | 边界/异常 | 非 npu_demo target | 通过公开 target 配置设置 `target="cpu"`。 | 运行 `test_dsl_cost_run_rejects_non_npu_demo_target`。 | 按 `DslCostRunInvalidTarget` 失败。 | `test_dsl_cost_run_rejects_non_npu_demo_target` |
| TC-TOOLS-DSL-COST-RUN-008 | 执行结果 | ndarray + torch 混用参数 | 准备 `torch.Tensor` 输出、`numpy.ndarray` 输入和 `torch.Tensor` 输入。 | 运行 `test_dsl_cost_run_accepts_numpy_torch_mixed_real_args`。 | 返回 `int` 且为当前 vector cost 公式的非零结果。 | `test_dsl_cost_run_accepts_numpy_torch_mixed_real_args` |
| TC-TOOLS-DSL-COST-RUN-009 | 公开入口 | 包根导入 | 从 `kernel_gen.tools` 导入 `dsl_cost_run`。 | 运行 `test_tools_package_supports_direct_dsl_cost_run_import`。 | 包根公开入口可达。 | `test_tools_package_supports_direct_dsl_cost_run_import` |
