# inline.md

## 功能简介

- 定义 `inline` pass 的公开合同：把 module 内可内联的本地 `func.call` 展平成调用点，并清理失效的 private helper。
- 首版只覆盖当前 `npu-demo-lowering` 需要的最小 module 内 helper 展平场景，不承诺通用跨 module inline。

## API 列表

- `class InlinePass()`
  - `name: str`
  - `apply(ctx: Context, module: ModuleOp) -> None`
  - `run(module: ModuleOp) -> ModuleOp`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/pass/inline.md`](../../spec/pass/inline.md)
- `功能实现`：[`kernel_gen/passes/inline.py`](../../kernel_gen/passes/inline.py)
- `test`：[`test/pass/test_inline.py`](../../test/pass/test_inline.py)

## 依赖

- Pass 管理与执行：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- pass 注册表：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- 共享错误类型：[`kernel_gen/passes/common.py`](../../kernel_gen/passes/common.py)
- `func.call` / `func.return` IR 语义：[`spec/dialect/func.md`](../../spec/dialect/func.md)

## 术语

- `inlineable helper`：满足单 block、非 declaration、以 `func.return` 结尾的本地 `func.func`。
- `private helper`：`sym_visibility = private` 的 helper 函数；若不再被引用，应在 inline 后清理。

## 目标

- 把当前 module 内可内联 helper 展平到调用点。
- 保持 SSA 映射稳定，inline 后调用点结果继续指向原返回值。
- 清理已失效的 private helper，避免 module 中残留死函数。

## 限制与边界

- 只接受 `builtin.module` 输入。
- 仅处理 module 内本地 `func.call`，不处理外部声明或跨 module 调用。
- helper 必须是单 block 且 block 末尾为 `func.return`。
- 若 inline 之后仍残留可内联 local call，必须显式失败。
- 当前文件的公开 API 仅限 `InlinePass`；helper 展平、候选收集、private helper 清理都属于 `InlinePass` 的内部实现细节，不对外公开，也不得被跨文件实现或测试直连。
- 显式失败统一抛 `PassContractError`，并保持以下稳定错误前缀：
  - `InlineError: module must be builtin.module`
  - `InlineError: callee '<name>' must be a single-block func.func`
  - `InlineError: func.call arity mismatch for '<name>'`
  - `InlineError: func.call result arity mismatch for '<name>'`
  - `InlineError: unresolved func.call remains after inline`
- `build_registered_pass("inline")` 属于 registry 的公开 API，不属于本文件的专题公开 API；本文件只要求该名字能稳定构造出 `InlinePass`。

## 公开接口

### `class InlinePass()`

功能说明：

- 对 module 内可内联 helper 执行展平，并清理失效的 private helper。
- 通过 `apply(ctx, module)` 走 xDSL `ModulePass` 主入口，通过 `run(module)` 保持 legacy `Pass` 调用兼容。

参数说明：

- 无构造参数。

使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.inline import InlinePass

pass_obj = InlinePass()
pass_obj.apply(Context(), module)
module = pass_obj.run(module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("inline")
pass_obj.apply(ctx, module)
```

返回与限制：

- `apply(...)` 原地改写输入 `module`，返回 `None`。
- `run(module)` 返回被原地改写后的同一 `ModuleOp`。

#### `name: str`

功能说明：

- 暴露当前 pass 的稳定公开名称。

使用示例：

```python
from kernel_gen.passes.inline import InlinePass

assert InlinePass.name == "inline"
```

返回与限制：

- 固定为 `"inline"`。

#### `apply(ctx: Context, module: ModuleOp) -> None`

功能说明：

- 对输入 `ModuleOp` 执行 inline。
- 逐轮把本地 `func.call` 展平到调用点，并更新 SSA 映射。
- 在 inline 完成后清理失效的 private helper。

参数说明：

- `ctx: Context`：xDSL pass 上下文。
- `module: ModuleOp`：待处理的模块。

使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.inline import InlinePass

InlinePass().apply(Context(), module)
```

注意事项：

- `ctx` 仅作为 `ModulePass` 标准签名的一部分；该 pass 不额外定义 context 侧状态协议。
- 当 module 内没有 `func.func` 或没有可内联的本地 `func.call` 时，必须表现为 no-op。
- 若 helper 不满足单 block / `func.return` 结尾 / 参数结果 arity 一致等条件，必须以 `PassContractError` 报出 `InlineError:` 前缀错误。

返回与限制：

- 返回 `None`。
- 显式失败统一抛 `PassContractError`。

#### `run(module: ModuleOp) -> ModuleOp`

功能说明：

- 提供 legacy `Pass.run(target)` 兼容入口。
- 内部语义必须与 `apply(Context(), module)` 完全一致。

参数说明：

- `module: ModuleOp`：待处理的模块。

使用示例：

```python
from kernel_gen.passes.inline import InlinePass

module = InlinePass().run(module)
```

注意事项：

- `run(module)` 不得绕过 `apply(...)` 主路径，也不得引入第二套 inline 语义。

返回与限制：

- 返回被原地改写后的同一 `ModuleOp`。
- 显式失败统一抛 `PassContractError`。

## 测试

- 测试文件：[`test/pass/test_inline.py`](../../test/pass/test_inline.py)
- 执行命令：`pytest -q test/pass/test_inline.py`
- 测试目标：
  - `InlinePass` 可展开本地 helper
  - inline 后 private helper 会被清理
  - 非 module 输入显式失败并走 `PassContractError`
  - registry 仍能通过 `build_registered_pass("inline")` 构造 `InlinePass`
