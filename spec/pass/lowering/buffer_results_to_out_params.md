# buffer_results_to_out_params.md

## 功能简介

- 定义 `buffer-results-to-out-params` pass 的公开合同。
- 该 pass 在 IR 层把 `func.func` 中作为函数返回值返回的 `memory` 结果，改写成函数最前置的输入 out 参数。
- 首版只收口 pass 自身合同与最小骨架，不在本轮完成 `func.call` 全量同步改写或 `gen_kernel` 最终闭环。

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
- 本轮最小骨架只要求支持：
  - 单个 `memory` 返回值
  - 无外部声明
  - 无需要同步改写的 `func.call`
- 本轮不要求支持：
  - 多个 `memory` 返回值的完整重写
  - `memory + scalar` 混合返回
  - 模块内 `func.call` 全量同步改写
  - 下游 `gen_kernel` 闭环
- 对于本轮未覆盖但会导致“半改半留”的场景，必须显式报错，不允许静默保留双口径。

## 必须禁止的旧口径

- 不允许只改 `func.func` 输入/输出签名，不改 `func.return`
- 不允许把前置 out 参数和同一个 `memory` 返回值同时保留在函数合同里
- 不允许对 external declaration 做半改写
- 不允许在 callsite 尚未同步改写时，先改单个 `func.func` 形成半改半留
- 不允许先改 callee 签名和 `func.return`，再把 caller 继续留在旧 `func.call -> memory result` 口径

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
  - 本轮最小骨架若遇到 external declaration、未完成 callsite 同步的目标函数、模块内未同步改写的 `func.call`、多个或混合返回等未覆盖场景，必须显式报错。
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

### 未同步改写的 callsite

- 若模块内存在 `func.call` / `call-like` 仍消费“待改写 callee 的旧 memory result SSA”，而本轮又未实现 callsite 同步改写，pass 必须显式失败。
- 该失败是 `O1` 的正式硬门禁，不允许解释为“先改 callee，caller 留给后续任务处理”。
- 错误消息必须包含 `callsite rewrite` 或等价关键字。

## 测试

- 测试文件：[`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 验证命令：
  - `pytest -q test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or external_declaration or unrewritten_callsite'`

## 功能与用例清单

- `BROTP-001`：单个 `memory` 返回值会被改写为最前置 `arg0`，并清空 `func.return`。（`test_rewrite_single_memory_result_to_front_out_param`）
- `BROTP-002`：external declaration 不允许半改写，必须显式报错。（`test_rewrite_rejects_external_declaration`）
- `BROTP-003`：模块内存在未同步改写的 `func.call` 时，pass 不允许只改 callee；必须显式报 `callsite rewrite` 错误。（`test_rewrite_rejects_unrewritten_callsite`）
