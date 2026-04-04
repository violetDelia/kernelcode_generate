# buffer_results_to_out_params.md

## 功能简介

- 定义 `buffer-results-to-out-params` pass 的公开合同。
- 该 pass 在 IR 层把 `func.func` 中作为函数返回值返回的 `memory` 结果，改写成函数最前置的输入 out 参数。
- 当前公开口径已经收口到：模块内可解析的 `func.call` 会同步改写成“caller 显式 out 实参 + 零 result `func.call`”；但仍不在本轮完成多结果/mixed returns 或 `gen_kernel` 最终闭环。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- `功能实现`：
  - [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](../../../kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../../kernel_gen/passes/lowering/__init__.py)
- `test`：[`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)

## 依赖

- [`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- [`kernel_gen/passes/pass_manager.py`](../../../kernel_gen/passes/pass_manager.py)
- lowered IR 中的 `func.func` / `func.return` / `func.call`

## 目标

- 新增 `BufferResultsToOutParamsPass`
- 固定公开名字：`buffer-results-to-out-params`
- 把函数返回中的 `memory` 结果改写成最前置输入 out 参数
- 明确写死多个 output 的前置顺序合同：
  - 第 1 个 output -> `arg0`
  - 第 2 个 output -> `arg1`
  - 依次类推

## 限制与边界

- 本轮只收口 pass 自身合同和最小实现骨架。
- 当前公开范围要求支持：
  - 单个 `memory` 返回值
  - 模块内可解析的单结果 `func.call` 同步改写
- 当前仍不要求支持：
  - 多个 `memory` 返回值的完整重写
  - `memory + scalar` 混合返回
  - 下游 `gen_kernel` 闭环
- 对于当前未覆盖而又无法安全同步改写的场景，必须显式报错，不允许静默保留双口径。

## 必须禁止的旧口径

- 不允许只改 `func.func` 输入/输出签名，不改 `func.return`
- 不允许把前置 out 参数和同一个 `memory` 返回值同时保留在函数合同里
- 不允许对 external declaration 做半改写
- 不允许把已经可同步改写成功的模块内 caller/callee 继续写成必须失败
- 不允许先改 callee 签名和 `func.return`，再把 caller 静默留在旧 `func.call -> memory result` 口径

## 公开接口

### `class BufferResultsToOutParamsError(ValueError)`

- 功能说明：pass 的显式错误类型。
- 参数说明：
  - `message: str`：错误文本。
- 使用示例：`raise BufferResultsToOutParamsError("external declaration is not supported")`
- 注意事项：所有“半改半留必须失败”的场景都应统一抛出该错误。
- 返回与限制：抛错即终止当前 pass。

### `class BufferResultsToOutParamsPass(Pass)`

- 功能说明：将函数返回中的 `memory` 结果改写为最前置 out 参数。
- 参数说明：无。
- 使用示例：

```python
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass

module = BufferResultsToOutParamsPass().run(module)
```

- 注意事项：
  - pass 以 `ModuleOp` 为输入。
  - 当前公开范围若遇到 external declaration、无法安全同步改写的 callsite、多个或混合返回等未覆盖场景，必须显式报错。
- 返回与限制：返回改写后的同一 `ModuleOp`。

## 最小改写合同

### 单个 memory result

改写前：

```text
func.func @single(%src: !nn.memory<...>) -> (!nn.memory<...>) {
  ...
  func.return %0
}
```

改写后：

```text
func.func @single(%arg0: !nn.memory<...>, %src: !nn.memory<...>) {
  ...
  func.return
}
```

必须满足：

- 新 out 参数前置到最前面
- 新前置参数名固定为 `arg0`
- 原 `memory` 返回类型从 `function_type.outputs` 中移除
- `func.return` 变为空 return

### 多个 outputs 的固定顺序

- 虽然本轮最小骨架不要求真正完成多个 output 改写，但合同必须先写死：
  - 第 1 个 `memory` output -> `arg0`
  - 第 2 个 `memory` output -> `arg1`
  - 依次类推
- 禁止多 output 场景未来再引入其他前置顺序或双口径并存。

### external declaration

- 若函数是 external declaration 且返回值中包含 `memory`，pass 必须显式失败。
- 错误消息必须包含 `external declaration` 或等价关键字。

### 模块内 callsite 同步改写

- 若模块内存在可解析的 `caller + callee`，且 callee 命中单个 `memory` 返回值改写，pass 必须同步把 caller 侧旧 `func.call` 改写成“显式 out 实参 + 零 result `func.call`”。
- caller 侧必须先补 out buffer，并把旧 memory call result SSA 全量替换为 caller 显式 out buffer。
- 当前公开成功口径下，不再把这类模块内可解析 callsite 写成必须失败。

改写前：

```text
%0 = func.call @add(%lhs, %rhs) : (...) -> (!nn.memory<...>)
use %0
```

改写后：

```text
%out = dma.alloc ...
func.call @add(%out, %lhs, %rhs) : (...) -> ()
use %out
```

必须满足：

- 新 `func.call` 第一个实参固定传 caller 侧显式 out buffer
- 旧 memory call result SSA 不再存在
- caller 对旧 result 的后续使用必须改绑到 caller 侧 out buffer

## 测试

- 测试文件：[`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 验证命令：
  - `pytest -q test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or external_declaration or callsite or pipeline_position'`
  - `PYTHONPATH=. python expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py`

## 功能与用例清单

- `BROTP-001`：单个 `memory` 返回值会被改写为最前置 `arg0`，并清空 `func.return`。（`test_rewrite_single_memory_result_to_front_out_param`）
- `BROTP-002`：external declaration 不允许半改写，必须显式报错。（`test_rewrite_rejects_external_declaration`）
- `BROTP-003`：模块内 caller/callee 会同步改写成“caller 显式 out 实参 + 零 result `func.call`”，旧 memory call result SSA 不再可被消费。（`test_rewrite_callsite_replaces_old_memory_result_ssa`）
- `BROTP-004`：在 lowering pipeline 中，`BufferResultsToOutParamsPass` 固定运行在 `LowerNnToKernelPass` 之后。（`test_pass_manager_runs_lower_then_buffer_results_to_out_params`、`test_pipeline_position_pass_manager_runs_lower_then_buffer_results_to_out_params`）
- `BROTP-005`：ignored expectation smoke `callsite_rewrite.py` 锁死“callee 的 memory result -> 前置 arg0；caller 补 out 实参；`func.call` 零 memory result”的 `O2` 公开口径。（`expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py`）
