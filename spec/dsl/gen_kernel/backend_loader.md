# backend_loader.md

## 功能简介

- 定义 `gen_kernel.emit` backend 自动加载合同。
- backend target 与 Python 模块一一对应：`target="abc"` 加载 `kernel_gen.dsl.gen_kernel.emit.abc`。
- 自动加载只发生在公开 emit dispatch 路径中，不要求调用方手工导入 backend 模块。

## API 列表

- `emit_c(obj: SSAValue | Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`
- `emit_c_op(op: Operation, ctx: EmitCContext) -> str`
- `emit_c_value(value: SSAValue, ctx: EmitCContext) -> str`
- `dispatch_op(op: Operation, ctx: EmitCContext) -> str | None`
- `dispatch_value(value: SSAValue, ctx: EmitCContext) -> str | None`
- `dispatch_type(attr: Any, ctx: EmitCContext) -> str | None`
- `dispatch_attr(attr: Any, ctx: EmitCContext) -> str | None`
- `dispatch_include(ctx: EmitCContext) -> str`
- `dispatch_name(value: SSAValue, ctx: EmitCContext) -> str | None`

## 文档信息

- `spec`：`spec/dsl/gen_kernel/backend_loader.md`
- `功能实现`：`kernel_gen/dsl/gen_kernel/emit/__init__.py`
- `功能实现`：`kernel_gen/dsl/gen_kernel/emit/register.py`
- `test`：`test/dsl/gen_kernel/test_backend_loader.py`

## 依赖

- [`spec/core/config.md`](../../core/config.md)
- [`spec/dsl/gen_kernel/emit.md`](emit.md)
- [`spec/dsl/gen_kernel/emit/register.md`](emit/register.md)
- [`spec/target/registry.md`](../../target/registry.md)

## 目标

- 让第三方 target 可以通过公开 target registry + backend 模块注册 emit 行为。
- 禁止 unknown target 隐式回退到 CPU。
- 保证 backend 缺失、导入失败和 handler 缺失错误可机械区分。

## 模块边界

- target 名称必须满足 `[a-z0-9_]+`。
- 已注册 target 会触发 backend auto-load；未注册 target 不触发 backend auto-load，也不得 fallback 到 CPU。
- 未设置当前 target 时，以 core config 默认 target 为准。
- `cpu` 与 `npu_demo` 是内置 backend；其它 backend 只有被 dispatch 使用时才自动导入。
- backend 模块可以注册 op/value/type/attr/include/name handler，也可以注册 compile strategy。

## API详细说明

### `emit_c(obj: SSAValue | Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`

- 参数：
  - `obj`：待生成源码的 SSA value、operation、函数或 module；必须显式传入。
  - `ctx`：公开 EmitC 上下文；必须显式传入。
- 返回值：生成后的源码文本。
- 功能说明：统一源码生成入口；当 `obj` 是 `ModuleOp` 时，通过当前 target 的 `emit_c_impl(ModuleOp, target=...)` handler 发射。
- 使用示例：

  ```python
  from kernel_gen.core.config import set_target
  from kernel_gen.dsl.gen_kernel.emit import emit_c
  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

  set_target("dummy_generic")
  source = emit_c(module_op, EmitCContext())
  ```
- 注意事项：已注册 target 的 backend 缺失或 `ModuleOp` handler 缺失必须公开失败；未注册 target 不触发 backend auto-load，调用侧继续按 unsupported 语义失败，不得 fallback 到 CPU。

### `dispatch_op(op: Operation, ctx: EmitCContext) -> str | None`

- 参数：
  - `op`：待分发 operation。
  - `ctx`：公开 EmitC 上下文。
- 返回值：handler 返回的源码文本，或未命中时返回 `None`。
- 功能说明：按当前 target 自动导入 backend 并查找 operation handler。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import dispatch_op

  stmt = dispatch_op(op, ctx)
  ```
- 注意事项：`ModuleOp` handler 返回 `Mapping[str, str]` 时编码为 SourceBundle aggregate string。

## 测试

- 测试文件：`test/dsl/gen_kernel/test_backend_loader.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/test_backend_loader.py`

### 测试目标

- 验证 backend auto-load 正常路径。
- 验证 unknown target 不 fallback。
- 验证 `backend_not_found`、`backend_import_failed`、`backend_handler_not_found` 三类错误。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TG-BACKEND-001 | 自动加载 | 已注册 target 有 backend 模块。 | 注册 target 并提供 backend 模块。 | 调用 `emit_c(module_op, ctx)`。 | backend 模块自动加载并返回目标源码。 | `test_backend_loader_imports_registered_dummy_backend` |
| TG-BACKEND-002 | 错误语义 | target 未注册。 | 设置未注册 target。 | 调用 `emit_c(module_op, ctx)`。 | 抛出公开错误且不出现 CPU 源码。 | `test_backend_loader_rejects_unregistered_target_without_cpu_fallback` |
| TG-BACKEND-003 | 错误语义 | backend 模块不存在。 | 注册 target，不提供模块。 | 调用 `emit_c(module_op, ctx)`。 | 抛出 `backend_not_found`。 | `test_backend_loader_distinguishes_missing_module` |
| TG-BACKEND-004 | 错误语义 | backend 内部导入失败。 | backend 模块导入缺失依赖。 | 调用 `emit_c(module_op, ctx)`。 | 抛出 `backend_import_failed`。 | `test_backend_loader_distinguishes_backend_import_failure` |
| TG-BACKEND-005 | 错误语义 | backend 未注册 `ModuleOp` handler。 | backend 模块存在但无 handler。 | 调用 `emit_c(module_op, ctx)`。 | 抛出 `backend_handler_not_found`。 | `test_backend_loader_distinguishes_missing_module_handler` |
| TG-BACKEND-006 | 显式 target 查询 | default registry 存在同类 handler。 | 注册默认 op handler，指定 target 未注册该 op handler。 | 调用 `dispatch_op_for_target(op, ctx, target)`。 | 返回 `None`，不会返回默认 handler 文本。 | `test_dispatch_op_for_target_does_not_read_default_registry` |
