# emitc_case_runner.md

## 功能简介

- `emitc_case_runner` 是面向 `expectation/dsl/emit_c/**` 与对应 pytest 的轻量 helper。
- 它负责把带 `COMPILE_ARGS` / `CHECK` 头的 case 文本收成最小执行流程：提取 IR、按允许集合做预处理、执行 `emit_c(target="npu_demo")`、再做源码片段断言。
- 公开稳定入口只有 `run_emitc_case(...)`；文件内其余 helper 不对外，不得跨文件调用。

## API 列表

- `run_emitc_case(case_text: str, *, source_path: str, op_name: str | None = None, expected_snippets: list[str], forbidden_snippets: list[str] | None = None) -> str`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/tools/emitc_case_runner.md`](../../spec/tools/emitc_case_runner.md)
- `功能实现`：[`kernel_gen/tools/emitc_case_runner.py`](../../kernel_gen/tools/emitc_case_runner.py)
- `test`：[`test/tools/test_emitc_case_runner.py`](../../test/tools/test_emitc_case_runner.py)

## 依赖

- emit 核心：[`spec/dsl/gen_kernel/emit.md`](../../spec/dsl/gen_kernel/emit.md)
- 执行目标上下文：[`spec/dsl/gen_kernel/emit_context.md`](../../spec/dsl/gen_kernel/emit_context.md)
- pass 预处理：[`spec/pass/buffer_results_to_out_params.md`](../../spec/pass/buffer_results_to_out_params.md)

## 额外补充

- 本专题只定义 `run_emitc_case(...)`，不定义 `emit_c(...)`、`emit_c_op(...)` 或 `emit_c_value(...)` 的公开合同；后者由 [`spec/dsl/gen_kernel/emit.md`](../../spec/dsl/gen_kernel/emit.md) 单独定义。
- 文件内 helper 只服务 `run_emitc_case(...)` 实现，不对外公开；实现、测试与 `expectation` 不得跨文件导入或断言这些 helper。

## API详细说明

### `run_emitc_case(case_text: str, *, source_path: str, op_name: str | None = None, expected_snippets: list[str], forbidden_snippets: list[str] | None = None) -> str`

- api：`run_emitc_case(case_text: str, *, source_path: str, op_name: str | None = None, expected_snippets: list[str], forbidden_snippets: list[str] | None = None) -> str`
- 参数：
  - `case_text`：含 `COMPILE_ARGS` / `CHECK` 注释头与输入 IR 正文的完整 case 文本；类型 `str`；无默认值，调用方必须显式提供；不允许 `None`；空文本或不含有效输入 IR 时必须抛出稳定 `ValueError`。
  - `source_path`：当前 case 的稳定来源标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空字符串；错误消息必须包含该值。
  - `op_name`：可选语义标签；类型 `str | None`；默认值 `None`；允许 `None`，但不允许空字符串。
  - `expected_snippets`：生成源码中必须出现的片段集合；类型 `list[str]`；无默认值，调用方必须显式提供；不允许 `None`，且不能与 `forbidden_snippets` 同时为空。
  - `forbidden_snippets`：生成源码中禁止出现的片段集合；类型 `list[str] | None`；默认值 `None`；允许 `None`，但不能与 `expected_snippets` 同时为空。
- 返回值：`str`，表示 `set_target("npu_demo") + emit_c(module, EmitCContext())` 生成的完整源码文本。
- 使用示例：

  ```python
  from kernel_gen.tools.emitc_case_runner import run_emitc_case

  source = run_emitc_case(
      case_text=case_text,
      source_path="inline#kernel_add",
      op_name="tuner.cost.kernel.add",
      expected_snippets=["cost::add<GM, float, float, compute>"],
      forbidden_snippets=["tuner.cost("],
  )
  assert "cost::add" in source
  ```
- 功能说明：提取 `case_text` 中的输入 `builtin.module`，按允许集合执行最小预处理，临时设置 `core.config.target="npu_demo"`，调用 `emit_c(module, EmitCContext())`，再校验源码片段。
- 注意事项：
  - 当前只接受未声明 `COMPILE_ARGS`、`// COMPILE_ARGS: --pass no-op`、`// COMPILE_ARGS: --pass buffer-results-to-out-params`。
  - `source_path == ""` 必须抛出 `ValueError("source_path must be non-empty")`。
  - `op_name == ""` 必须抛出 `ValueError("op_name must be non-empty when provided")`。
  - `expected_snippets` 与 `forbidden_snippets` 同时为空时必须抛出 `ValueError("expected_snippets and forbidden_snippets cannot both be empty")`。
  - `case_text` 中没有有效输入 IR 时必须抛出 `ValueError("emit_c expectation case must contain input IR")`。
  - `COMPILE_ARGS` 超出允许集合时必须抛出稳定 `ValueError`。
  - `emit_c(...)` 执行失败时沿用底层异常，不在本接口内重新包装。
  - 片段断言失败时抛出 `AssertionError`，错误消息必须包含 `source_path`。
  - `test/tools/test_emitc_case_runner.py` 与 `expectation/dsl/emit_c/npu_demo/**` 只能通过 `run_emitc_case(...)` 观察公开行为。

## 测试

- 测试文件：`test/tools/test_emitc_case_runner.py`
- 执行命令：`pytest -q test/tools/test_emitc_case_runner.py`

### 测试目标

- 验证 `tools/emitc_case_runner` 的公开 API、边界与错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-TOOLS-EMITC-CASE-RUNNER-001 | pass 改写 | run emitc case lowers npu demo tuner cost kernel add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_emitc_case_lowers_npu_demo_tuner_cost_kernel_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run emitc case lowers npu demo tuner cost kernel add”场景。 | `test_run_emitc_case_lowers_npu_demo_tuner_cost_kernel_add` |
| TC-TOOLS-EMITC-CASE-RUNNER-002 | 边界/异常 | run emitc case rejects unsupported compile args | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_emitc_case_rejects_unsupported_compile_args`。 | “run emitc case rejects unsupported compile args”场景按公开错误语义失败或被拒绝。 | `test_run_emitc_case_rejects_unsupported_compile_args` |
| TC-TOOLS-EMITC-CASE-RUNNER-003 | pass 改写 | run emitc case lowers plain symbol cast module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_emitc_case_lowers_plain_symbol_cast_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run emitc case lowers plain symbol cast module without launch wrapper”场景。 | `test_run_emitc_case_lowers_plain_symbol_cast_module_without_launch_wrapper` |
| TC-TOOLS-EMITC-CASE-RUNNER-004 | pass 改写 | run emitc case lowers return only plain module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_emitc_case_lowers_return_only_plain_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run emitc case lowers return only plain module without launch wrapper”场景。 | `test_run_emitc_case_lowers_return_only_plain_module_without_launch_wrapper` |
| TC-TOOLS-EMITC-CASE-RUNNER-005 | 生成/编译 | run emitc case applies buffer results to out params before emit c | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_emitc_case_applies_buffer_results_to_out_params_before_emit_c`。 | 生成源码、IR 文本或编译结果体现“run emitc case applies buffer results to out params before emit c”场景。 | `test_run_emitc_case_applies_buffer_results_to_out_params_before_emit_c` |
| TC-TOOLS-EMITC-CASE-RUNNER-006 | 生成/编译 | run emitc case allows forbidden only contract | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_emitc_case_allows_forbidden_only_contract`。 | 生成源码、IR 文本或编译结果体现“run emitc case allows forbidden only contract”场景。 | `test_run_emitc_case_allows_forbidden_only_contract` |
