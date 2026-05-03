# inline.md

## 功能简介

- 定义 `inline` pass 的公开合同：把 module 内可内联的本地 `func.call` 展平成调用点，并清理失效的 private helper。
- 首版只覆盖当前 `npu-demo-lowering` 需要的最小 module 内 helper 展平场景，不承诺通用跨 module inline。

## API 列表

- `class InlinePass()`
  - `name: str`
  - `apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/inline.md`](../../spec/pass/inline.md)
- `功能实现`：[`kernel_gen/passes/inline.py`](../../kernel_gen/passes/inline.py)
- `test`：[`test/passes/test_inline.py`](../../test/passes/test_inline.py)

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

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 只接受 `builtin.module` 输入。
- 仅处理 module 内本地 `func.call`，不处理外部声明或跨 module 调用。
- helper 必须是单 block 且 block 末尾为 `func.return`。
- 若 inline 之后仍残留可内联 local call，必须显式失败。
- 当前文件的公开 API 仅限 `InlinePass`；helper 展平、候选收集、private helper 清理都属于 `InlinePass` 的内部实现细节，不对外公开，也不得被跨文件实现或测试直连。
- 显式失败统一抛 `KernelCodeError`，并保持以下稳定错误前缀：
  - `InlineError: module must be builtin.module`
  - `InlineError: callee '<name>' must be a single-block func.func`
  - `InlineError: func.call arity mismatch for '<name>'`
  - `InlineError: func.call result arity mismatch for '<name>'`
  - `InlineError: unresolved func.call remains after inline`
- `build_registered_pass("inline")` 属于 registry 的公开 API，不属于本文件的专题公开 API；本文件只要求该名字能稳定构造出 `InlinePass`。
## API详细说明

### `class InlinePass()`

- api：`class InlinePass()`
- 参数：无。
- 返回值：`InlinePass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.inline import InlinePass

  pass_obj = InlinePass()
  ```
- 功能说明：构造 inline pass 对象，对 module 内可内联 helper 执行展平并清理失效的 private helper。
- 注意事项：公开执行入口固定为 xDSL `ModulePass.apply(ctx, module)`；不提供返回式 `run(module)` 执行入口；helper 展平、候选收集、private helper 清理都属于内部实现细节。

### `name: str`

- api：`name: str`
- 参数：无。
- 返回值：`str` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  from kernel_gen.passes.inline import InlinePass

  assert InlinePass.name == "inline"
  ```
- 功能说明：暴露当前 pass 的稳定公开名称。
- 注意事项：固定为 `"inline"`；不得作为可变配置入口使用。

### `apply(ctx: Context, module: ModuleOp) -> None`

- api：`apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from xdsl.context import Context

  from kernel_gen.passes.inline import InlinePass

  InlinePass().apply(Context(), module)
  ```
- 功能说明：对输入 `ModuleOp` 执行 inline，逐轮把本地 `func.call` 展平到调用点，并在 inline 完成后清理失效的 private helper。
- 注意事项：`apply(...)` 原地改写输入 `module` 并返回 `None`；`ctx` 仅作为 `ModulePass` 标准签名的一部分，该 pass 不额外定义 context 侧状态协议；当 module 内没有 `func.func` 或没有可内联的本地 `func.call` 时必须表现为 no-op；若 helper 不满足单 block / `func.return` 结尾 / 参数结果 arity 一致等条件，必须以 `KernelCodeError` 报出 `InlineError:` 前缀错误；不得恢复 `run(module)` 或引入第二套 inline 语义。

## 测试

- 测试文件：`test/passes/test_inline.py`
- 执行命令：`pytest -q test/passes/test_inline.py`

### 测试目标

- 验证 `spec/pass/inline.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-INLINE-001 | 公开入口 | inline expands private helper and cleans dead helper | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_inline_expands_private_helper_and_cleans_dead_helper`。 | 公开入口在“inline expands private helper and cleans dead helper”场景下可导入、构造、注册或按名称发现。 | `test_inline_expands_private_helper_and_cleans_dead_helper` |
| TC-PASS-INLINE-002 | 边界/异常 | inline rejects non module | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_inline_rejects_non_module`。 | “inline rejects non module”场景按公开错误语义失败或被拒绝。 | `test_inline_rejects_non_module` |
