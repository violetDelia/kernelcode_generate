# runner.md

## 功能简介

- 定义 [`kernel/runner.py`](../../kernel/runner.py) 的 demo 执行入口。
- 统一提供 `dsl_run -> npu-demo-lowering -> execute` 的真实执行链，以及 `mlir_gen -> npu-demo-lowering -> gen_kernel` 的源码生成链。
- 统一把诊断产物写入 `kernel/dump/<case_name>/`，并把最终源码镜像为 `source.cpp`。
- runtime trance kernel log 开关只来自 [`spec/core/config.md`](../core/config.md) 的 `set_trance_enabled(...)`；runner 不新增同义入口参数。
- 本文件只定义 runner API，不定义 `expectation/kernel` 合同资产矩阵；`expectation` 仍只读。

## API 列表

- `KERNEL_DUMP_ROOT: Path`
- `class KernelTorchDemoResult(case_name: str, dsl_result: DslRunResult, max_abs_diff: float, atol: float, rtol: float)`
- `run_torch_demo(case_name: str, kernel_fn: Callable[..., Memory | SymbolDim | int | float | bool | str | None], real_args: tuple[torch.Tensor | np.ndarray | int, ...] | list[torch.Tensor | np.ndarray | int], output: torch.Tensor | np.ndarray, expected: torch.Tensor | np.ndarray, *, atol: float = 1e-4, rtol: float = 1e-4) -> KernelTorchDemoResult`
- `run_lowering_demo(case_name: str, kernel_fn: Callable[..., Memory | SymbolDim | int | str | None], *compile_args: Memory | SymbolDim | int | str) -> tuple[ModuleOp, str]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/kernel/runner.md`](../../spec/kernel/runner.md)
- `功能实现`：[`kernel/runner.py`](../../kernel/runner.py)
- `test`：[`test/kernel/test_runner.py`](../../test/kernel/test_runner.py)

## 依赖

- [`spec/core/config.md`](../core/config.md)：target 与 dump_dir 全局配置。
- [`spec/dsl/ast/mlir_gen.md`](../dsl/ast/mlir_gen.md)：`mlir_gen(...)` 生成入口。
- [`spec/dsl/gen_kernel/gen_kernel.md`](../dsl/gen_kernel/gen_kernel.md)：`gen_kernel(...)` 源码生成入口。
- [`spec/tools/dsl_run.md`](../tools/dsl_run.md)：真实执行入口；`run_torch_demo(...)` 通过该入口继承 runtime trance 执行日志语义。
- [`spec/pass/pipeline/npu_demo_lowering.md`](../pass/pipeline/npu_demo_lowering.md)：`npu-demo-lowering` pipeline。
- [`spec/symbol_variable/memory.md`](../symbol_variable/memory.md)：runner callable 可接受的 `Memory` 参数。
- [`spec/symbol_variable/symbol_dim.md`](../symbol_variable/symbol_dim.md)：runner callable 可接受的 `SymbolDim` 参数。

## API详细说明

### `KERNEL_DUMP_ROOT: Path`

- api：`KERNEL_DUMP_ROOT: Path`
- 参数：无。
- 返回值：`Path` 常量值。
- 使用示例：

  ```python
  from kernel.runner import KERNEL_DUMP_ROOT

  dump_root = KERNEL_DUMP_ROOT
  ```
- 功能说明：定义 runner 默认诊断根目录。
- 注意事项：路径固定为 `kernel/dump`；调用方不得把它作为可变配置入口。

### `class KernelTorchDemoResult(case_name: str, dsl_result: DslRunResult, max_abs_diff: float, atol: float, rtol: float)`

- api：`class KernelTorchDemoResult(case_name: str, dsl_result: DslRunResult, max_abs_diff: float, atol: float, rtol: float)`
- 参数：
  - `case_name`：demo case 名称；类型 `str`；必填；用于定位 dump 子目录和错误消息。
  - `dsl_result`：`dsl_run(...)` 返回结果；类型 `DslRunResult`；必填；保存 IR、源码、编译与执行结果。
  - `max_abs_diff`：输出与参考结果的最大绝对误差；类型 `float`；必填。
  - `atol`：绝对误差容忍阈值；类型 `float`；必填。
  - `rtol`：相对误差容忍阈值；类型 `float`；必填。
- 返回值：`KernelTorchDemoResult` 实例。
- 使用示例：

  ```python
  result = KernelTorchDemoResult(
      case_name="matmul/static_shape",
      dsl_result=dsl_result,
      max_abs_diff=0.0,
      atol=1e-4,
      rtol=1e-4,
  )
  ```
- 功能说明：记录 torch/numpy demo 的真实执行结果摘要。
- 注意事项：`dsl_result` 必须来自同一 case 的 `dsl_run(...)` 调用。

### `run_torch_demo(case_name: str, kernel_fn: Callable[..., Memory | SymbolDim | int | float | bool | str | None], real_args: tuple[torch.Tensor | np.ndarray | int, ...] | list[torch.Tensor | np.ndarray | int], output: torch.Tensor | np.ndarray, expected: torch.Tensor | np.ndarray, *, atol: float = 1e-4, rtol: float = 1e-4) -> KernelTorchDemoResult`

- api：`run_torch_demo(case_name: str, kernel_fn: Callable[..., Memory | SymbolDim | int | float | bool | str | None], real_args: tuple[torch.Tensor | np.ndarray | int, ...] | list[torch.Tensor | np.ndarray | int], output: torch.Tensor | np.ndarray, expected: torch.Tensor | np.ndarray, *, atol: float = 1e-4, rtol: float = 1e-4) -> KernelTorchDemoResult`
- 参数：
  - `case_name`：demo case 名称；类型 `str`；必填；可包含 `/` 分层，最终会规整为相对 dump 路径。
  - `kernel_fn`：DSL kernel callable；类型 `Callable[..., Memory | SymbolDim | int | str | None]`；必填。
  - `real_args`：运行期真实实参；类型 `tuple[torch.Tensor | np.ndarray | int, ...] | list[torch.Tensor | np.ndarray | int]`；必填；顺序必须与 `kernel_fn` 的运行期参数一致；整数标量用于 runtime tile、stride、padding 等 DSL 标量形参，`float` 与 `bool` 由 `dsl_run(...)` 公开校验拒绝。
  - `output`：执行后读取的输出张量；类型 `torch.Tensor | np.ndarray`；必填。
  - `expected`：参考结果张量；类型 `torch.Tensor | np.ndarray`；必填。
  - `atol`：绝对误差容忍阈值；类型 `float`；默认值 `1e-4`。
  - `rtol`：相对误差容忍阈值；类型 `float`；默认值 `1e-4`。
- 返回值：`KernelTorchDemoResult`。
- 使用示例：

  ```python
  result = run_torch_demo(
      "matmul/static_shape",
      matmul_kernel,
      (out, lhs, rhs),
      out,
      lhs @ rhs,
  )
  ```
- 功能说明：执行 DSL kernel，并校验运行结果与 torch/numpy 参考输出一致。
- 注意事项：`output` 与 `expected` 仅接受 torch tensor 或 numpy ndarray；`real_args` 额外允许整数运行期标量并透传给 `dsl_run(...)`；`case_name` 不能为空。

### `run_lowering_demo(case_name: str, kernel_fn: Callable[..., Memory | SymbolDim | int | str | None], *compile_args: Memory | SymbolDim | int | str) -> tuple[ModuleOp, str]`

- api：`run_lowering_demo(case_name: str, kernel_fn: Callable[..., Memory | SymbolDim | int | str | None], *compile_args: Memory | SymbolDim | int | str) -> tuple[ModuleOp, str]`
- 参数：
  - `case_name`：demo case 名称；类型 `str`；必填；可包含 `/` 分层，最终会规整为相对 dump 路径。
  - `kernel_fn`：DSL kernel callable；类型 `Callable[..., Memory | SymbolDim | int | float | bool | str | None]`；必填。
  - `compile_args`：编译期符号、内存或标量实参；类型 `Memory | SymbolDim | int | str`；可变参数；顺序必须与 `kernel_fn` 签名一致；整数标量用于公开 compile-time 常量或 runtime symbol placeholder 对应值，不接受 `float` 或 `bool`。
- 返回值：`tuple[ModuleOp, str]`，依次为 lowering 后 module 与生成的源码文本。
- 使用示例：

  ```python
  module, source = run_lowering_demo(
      "matmul/static_shape",
      matmul_kernel,
      lhs,
      rhs,
      out,
  )
  ```
- 功能说明：生成 IR、运行 `npu-demo-lowering`，再生成源码文本。
- 注意事项：该入口不编译或执行源码；需要真实运行时使用 `run_torch_demo(...)`；若需要表达 runtime stride/dilation/padding/tile，应优先传入 `SymbolDim` 作为编译期形参，并由 `dsl_run(...)` / `run_torch_demo(...)` 用整数 `real_args` 绑定真实值。

## 测试

- 测试文件：`test/kernel/test_runner.py`。
- 执行命令：`pytest -q test/kernel/test_runner.py`。

### 测试目标

- 验证 runner 能完成 DSL lowering、源码生成、编译执行和输出比对。
- 验证 runner 只通过本 spec 定义的公开 API 暴露 demo 入口。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-KERNEL-RUNNER-001 | 生成/编译 | `run_lowering_demo(...)` 完成 `mlir_gen -> npu-demo-lowering -> gen_kernel` 链路并写出 `source.cpp` | 准备公开 DSL kernel callable、`Memory`/`SymbolDim`/标量运行期参数和隔离 dump 目录。 | 新增并运行 `pytest -q test/kernel/test_runner.py::test_run_lowering_demo_generates_source_and_dump`。 | 返回 lowering 后 `ModuleOp` 与源码文本，dump 子目录存在并包含 `source.cpp`。 | 建议新增 `test/kernel/test_runner.py::test_run_lowering_demo_generates_source_and_dump` |
| TC-KERNEL-RUNNER-002 | 执行结果 | `run_torch_demo(...)` 完成 `dsl_run -> npu-demo-lowering -> execute` 链路并比对 torch/numpy 参考输出 | 准备公开 DSL kernel callable、真实 `torch.Tensor` 或 `np.ndarray` 实参、输出张量与参考张量。 | 新增并运行 `pytest -q test/kernel/test_runner.py::test_run_torch_demo_executes_and_checks_output`。 | 返回 `KernelTorchDemoResult`，`max_abs_diff` 不超过 `atol + rtol * abs(expected)` 对应容忍范围。 | 建议新增 `test/kernel/test_runner.py::test_run_torch_demo_executes_and_checks_output` |
| TC-KERNEL-RUNNER-003 | 边界/异常 | `run_torch_demo(...)` 拒绝空 `case_name` 或非 tensor/ndarray 真实实参 | 准备空 case 名称或非法 `real_args` 元素，并保持其他参数为公开可构造对象。 | 新增并运行 `pytest -q test/kernel/test_runner.py::test_run_torch_demo_rejects_invalid_public_inputs`。 | 非法输入按公开错误语义失败，不写入误导性 dump 产物。 | 建议新增 `test/kernel/test_runner.py::test_run_torch_demo_rejects_invalid_public_inputs` |
| TC-KERNEL-RUNNER-004 | 执行结果 | `run_torch_demo(...)` 接受 runtime scalar tile | 准备公开 DSL kernel callable、真实张量和 `int` tile 标量。 | 运行 `pytest -q test/kernel/test_runner.py::test_run_torch_demo_accepts_runtime_scalar_tile`。 | runner 透传标量到 `dsl_run(...)`，执行结果与参考输出一致。 | `test/kernel/test_runner.py::test_run_torch_demo_accepts_runtime_scalar_tile` |
