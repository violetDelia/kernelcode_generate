# emitc_case_runner.md

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/tools/emitc_case_runner.md`](../../spec/tools/emitc_case_runner.md)
- `功能实现`：[`kernel_gen/tools/emitc_case_runner.py`](../../kernel_gen/tools/emitc_case_runner.py)
- `test`：[`test/tools/test_emitc_case_runner.py`](../../test/tools/test_emitc_case_runner.py)

## 功能简介

- `emitc_case_runner` 是面向 `expectation/dsl/emit_c/**` 与对应 pytest 的轻量 helper。
- 它负责把带 `COMPILE_ARGS` / `CHECK` 头的 case 文本收成最小执行流程：提取 IR、按允许集合做预处理、执行 `emit_c(target="npu_demo")`、再做源码片段断言。
- 公开稳定入口只有 `run_emitc_case(...)`；文件内其余 helper 不对外，不得跨文件调用。

## API 列表

- `run_emitc_case(case_text: str, *, source_path: str, op_name: str | None = None, expected_snippets: list[str], forbidden_snippets: list[str] | None = None) -> str`

## 公开接口

### `run_emitc_case(case_text: str, *, source_path: str, op_name: str | None = None, expected_snippets: list[str], forbidden_snippets: list[str] | None = None) -> str`

功能说明：

- 从 `case_text` 中提取头部 `COMPILE_ARGS` 与输入 `builtin.module` 文本。
- 当前只接受：
  - 未声明 `COMPILE_ARGS`
  - `// COMPILE_ARGS: --pass no-op`
  - `// COMPILE_ARGS: --pass buffer-results-to-out-params`
- 对输入 module 执行允许的最小预处理后，调用 `emit_c(module, EmitCContext(target="npu_demo"))`。
- 依次校验 `expected_snippets` 必须存在、`forbidden_snippets` 必须不存在。
- 返回最终生成的源码字符串，供 expectation 与 pytest 继续做补充断言。

参数说明：

- `case_text: str`
  - 含 `COMPILE_ARGS` / `CHECK` 注释头与输入 IR 正文的完整 case 文本。
- `source_path: str`
  - 当前 case 的稳定来源标识；错误消息必须包含该值。
- `op_name: str | None = None`
  - 可选的语义标签；传入非空字符串时追加到错误消息中。
- `expected_snippets: list[str]`
  - 生成源码中必须出现的片段集合。
- `forbidden_snippets: list[str] | None = None`
  - 生成源码中禁止出现的片段集合。

返回值：

- `str`
  - `emit_c(target="npu_demo")` 生成的完整源码文本。

使用示例：

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

## 失败边界

- `source_path == ""`：`ValueError("source_path must be non-empty")`
- `op_name == ""`：`ValueError("op_name must be non-empty when provided")`
- `expected_snippets` 与 `forbidden_snippets` 同时为空：`ValueError("expected_snippets and forbidden_snippets cannot both be empty")`
- `case_text` 中没有有效输入 IR：`ValueError("emit_c expectation case must contain input IR")`
- `COMPILE_ARGS` 超出允许集合：抛稳定 `ValueError`
- `emit_c(...)` 执行失败：沿用底层异常，不在本 helper 内重包
- 片段断言失败：抛 `AssertionError`，错误消息必须包含 `source_path`

## 边界与约束

- 本专题只承接 `run_emitc_case(...)`，不承接 `emit_c / emit_c_op / emit_c_value` 的公开合同；后者由 [`spec/dsl/gen_kernel/emit.md`](../../spec/dsl/gen_kernel/emit.md) 单独定义。
- `test/tools/test_emitc_case_runner.py` 与 `expectation/dsl/emit_c/npu_demo/**` 允许跨文件调用 `run_emitc_case(...)`，因为它已在本文件与本 spec 中定义为公开 API。
- 文件内 helper（如 `extract_compile_args` 对应的实现细节）不对外，不得被其他模块或测试直接导入。

## 依赖

- emit 核心：[`spec/dsl/gen_kernel/emit.md`](../../spec/dsl/gen_kernel/emit.md)
- 执行目标上下文：[`spec/dsl/gen_kernel/emit_context.md`](../../spec/dsl/gen_kernel/emit_context.md)
- pass 预处理：[`spec/pass/buffer_results_to_out_params.md`](../../spec/pass/buffer_results_to_out_params.md)

## 测试

- 测试文件：[`test/tools/test_emitc_case_runner.py`](../../test/tools/test_emitc_case_runner.py)
- 执行命令：`pytest -q test/tools/test_emitc_case_runner.py`
- 覆盖目标：
  - `run_emitc_case(...)` 的最小 `COMPILE_ARGS` 集合
  - plain module 与 symbol case 的 `npu_demo` 源码生成
  - `buffer-results-to-out-params` 预处理链路
  - `expected_snippets` / `forbidden_snippets` 合同
