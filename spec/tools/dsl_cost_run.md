# dsl_cost_run

## 功能简介

- 定义 `dsl_cost_run(func_obj, real_args, pipeline, cost_kind)` 的公开工具入口。
- 该入口只面向 `target="npu_demo"`，在 `mlir_gen -> pipeline -> gen_kernel(codegen_mode="cost") -> ExecutionEngine` 链路上生成 cost host，捕获 summary string，并返回指定 `cost_kind` 的真实 `int` cost。
- `dsl_cost_run(...)` 不改变 `dsl_run(...)` 的返回模型，不给 `dsl_run(...)` 增加 `cost_kind` 参数，也不依赖 `_cost_<kind>_*` sibling function。
- `dsl_cost_run(...)` 执行前会保存公开 config 快照，生成/编译期间临时设置 `codegen_mode="cost"`，结束后恢复调用前配置。
- `real_args` 校验复用 `dsl_run(...)` 规则，支持 torch/numpy memory、Python / numpy integer scalar、Python / numpy floating scalar 与合法 memory absent `None`。

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

## API详细说明

### `dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`

- api：`dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`
- 参数：
  - `func_obj`：DSL callable；类型 `Callable[..., DslFunctionReturn]`；无默认值。
  - `real_args`：运行期真实实参；类型 `tuple[RuntimeRealArg, ...] | list[RuntimeRealArg]`；校验规则与 `dsl_run(...)` 一致，包含普通 float / numpy floating scalar 支持、bool 拒绝与 `tile_*` 正整数限制。
  - `pipeline`：pipeline 名称或 `PassManager`；类型 `str | PassManager`；校验规则与 `dsl_run(...)` 一致。
  - `cost_kind`：成本统计视角；类型 `str`；无默认值；只接受 `DMA1`、`DMA2`、`DMA3`、`DMA4`、`MAC`、`VECTOR1`、`VECTOR2`。
- 返回值：`int`，对应 generated cost host summary JSON 中 `cost_kind` 的整数值。
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
  assert cost == 128
  ```
- 功能说明：执行 npu_demo cost mode host，捕获 `npu_demo::format_cost_summary(ctx.summary())` 生成的 JSON summary，并返回指定 kind 的整数成本值。
- 注意事项：
  - `cost_kind` 必须显式提供；本接口不提供默认值。
  - 当前入口不查找、不生成也不调用 `_cost_<kind>_*` sibling；缺少旧 sibling 不构成失败条件。
  - target 只能是 `npu_demo`；其他 target 必须失败，固定短语为 `DslCostRunInvalidTarget: dsl_cost_run only supports target 'npu_demo'`。
  - 非法 `cost_kind` 必须失败，固定短语为 `DslCostRunInvalidCostKind: cost_kind must be one of ['DMA1', 'DMA2', 'DMA3', 'DMA4', 'MAC', 'VECTOR1', 'VECTOR2']`；旧 `"DMA"` 聚合 kind 不再合法。
  - `DMA1/DMA2/DMA3/DMA4` 的 summary 值为 matching raw bytes 汇总后统一 `ceil(total_matching_bytes / 64)`；`VECTOR1` 按元素数累计，`MAC` 与其它 kind 按 `CostContext` 公开累计值返回。
  - generated cost host 必须以 `<wrapper>_cost` 命名，末尾参数为 `std::string& __kg_cost_summary`；body helper 或 host launch 返回非 `StatusCode::kOk` 时必须 fail-fast，不得继续写入 partial / 0 summary；全部成功后才通过 `npu_demo::format_cost_summary(ctx.summary())` 写入完整 JSON summary。
  - 执行引擎只在 npu_demo generated cost summary companion 场景支持 `capture_function_output=True`；summary 为空、非 JSON、缺 key、非整数值、unsupported helper、capture companion 失败或 entry 返回非零时，`dsl_cost_run(...)` 必须抛 `KernelCodeError(ErrorModule.TOOLS, ...)`，固定短语为 `DslCostRunExecutionFailed: cost summary capture failed`。
  - `dump_dir` 非空时，`99-cost-source.cpp` 诊断源码写入 `dump_dir/<kernel name>/99-cost-source.cpp`；该源码不得包含 `_cost_VECTOR1_`、`_cost_DMA`、`tuner.cost` 或 generated source 对 `npu_demo::detail` 的直接引用。

## 测试

- 测试文件：
  - `test/tools/test_dsl_cost_run.py`
  - `test/tools/test_package.py`
- 执行命令：
  - `pytest -q test/tools/test_dsl_cost_run.py test/tools/test_package.py`

### 测试目标

- 验证包根与模块入口可公开导入。
- 验证命名 npu-demo pipeline 与不生成旧 sibling 的自定义 pipeline 均通过 cost mode summary capture 返回 `int` cost。
- 验证旧 `compute` kind 与旧 `"DMA"` 聚合 kind 均按公开错误语义失败。
- 验证非 `npu_demo` target 按 `DslCostRunInvalidTarget` 失败。
- 验证 `numpy.ndarray` 与 `torch.Tensor` 混用运行参数仍可通过公开入口执行 cost mode。
- 验证普通 float 与 numpy floating scalar 通过 real_args 绑定层后可执行 cost mode。
- 验证 dump 中 `99-cost-source.cpp` 使用 `CostContext`、`std::string& __kg_cost_summary` 与 `format_cost_summary(...)`，并且不残留旧 sibling / tuner.cost 主路径。
- 验证 generated cost host 对 helper / launch status 做 fail-fast，且 summary capture 空文本、非 JSON、缺 key 或非整数值均按固定公开错误失败。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-TOOLS-DSL-COST-RUN-001 | 执行结果 | named pipeline cost mode summary | 准备 npu_demo add kernel 与公开真实参数。 | 运行 `test_dsl_cost_run_named_pipeline_returns_vector1_cost`。 | 返回 `VECTOR1 == 128`，业务输出保持原值，调用前 `codegen_mode` 被恢复。 | `test_dsl_cost_run_named_pipeline_returns_vector1_cost` |
| TC-TOOLS-DSL-COST-RUN-002 | 边界/异常 | 旧 kind | 传入旧 `compute` 或 `"DMA"` kind。 | 运行 `test_dsl_cost_run_rejects_old_cost_kind`。 | 按 `DslCostRunInvalidCostKind` exact seven-kind 文本失败。 | `test_dsl_cost_run_rejects_old_cost_kind` |
| TC-TOOLS-DSL-COST-RUN-003 | 执行结果 | custom pipeline without old sibling | 准备不生成 `_cost_<kind>_*` sibling 的公开 `PassManager` 链路。 | 运行 `test_dsl_cost_run_custom_pipeline_returns_cost_without_sibling`。 | 通过 cost mode summary capture 返回 `VECTOR1 == 128`，不依赖旧 sibling。 | `test_dsl_cost_run_custom_pipeline_returns_cost_without_sibling` |
| TC-TOOLS-DSL-COST-RUN-004 | 边界/异常 | 非 npu_demo target | 通过公开 target 配置设置 `target="cpu"`。 | 运行 `test_dsl_cost_run_rejects_non_npu_demo_target`。 | 按 `DslCostRunInvalidTarget` 失败。 | `test_dsl_cost_run_rejects_non_npu_demo_target` |
| TC-TOOLS-DSL-COST-RUN-005 | 执行结果 | ndarray + torch 混用参数 | 准备 `torch.Tensor` 输出、`numpy.ndarray` 输入和 `torch.Tensor` 输入。 | 运行 `test_dsl_cost_run_accepts_numpy_torch_mixed_real_args`。 | 参数校验通过并返回 `VECTOR1 == 128`，业务输出保持原值。 | `test_dsl_cost_run_accepts_numpy_torch_mixed_real_args` |
| TC-TOOLS-DSL-COST-RUN-006 | 执行结果 | float scalar 参数 | 准备带普通 `float` 形参的 kernel，并传入 Python / numpy floating scalar。 | 运行 `test_dsl_cost_run_accepts_float_runtime_scalar`。 | 参数绑定层放行并返回 `VECTOR1 == 128`，失败文本不出现。 | `test_dsl_cost_run_accepts_float_runtime_scalar` |
| TC-TOOLS-DSL-COST-RUN-007 | 生成/编译 | dump cost source | 设置 `dump_dir` 并执行公开 add kernel cost run。 | 运行 `test_dsl_cost_run_dump_writes_cost_source_and_no_old_sibling`。 | `99-cost-source.cpp` 包含 cost host summary sink 与 formatter 调用，且不含旧 sibling / `tuner.cost` / generated `npu_demo::detail`。 | `test_dsl_cost_run_dump_writes_cost_source_and_no_old_sibling` |
| TC-TOOLS-DSL-COST-RUN-008 | 边界/异常 | unsupported helper / invalid summary | 准备 generated cost source status 检查 fake engine 与非法 summary 文本。 | 运行 `test_dsl_cost_run_maps_unsupported_cost_helper_to_capture_failure` 与 `test_dsl_cost_run_rejects_invalid_summary_capture`。 | helper/launch capture failure、空 summary、非 JSON、缺 key 与非整数值均按 `DslCostRunExecutionFailed: cost summary capture failed` 失败。 | `test_dsl_cost_run_maps_unsupported_cost_helper_to_capture_failure`, `test_dsl_cost_run_rejects_invalid_summary_capture` |
| TC-TOOLS-DSL-COST-RUN-009 | 公开入口 | 包根导入 | 从 `kernel_gen.tools` 导入 `dsl_cost_run`。 | 运行 `test_tools_package_supports_direct_dsl_cost_run_import`。 | 包根公开入口可达。 | `test_tools_package_supports_direct_dsl_cost_run_import` |
