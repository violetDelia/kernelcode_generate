# register.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel.emit.register` 的公开注册与分发合同。
- 该模块是 backend 扩展 target-specific emit 行为的唯一公开入口。
- backend 模块路径固定为 `kernel_gen.dsl.gen_kernel.emit.<target>`；分发时按当前 target 自动加载。

## API 列表

- `emit_c_impl(*types: type[Any], target: str | None = None, override: bool = False) -> Callable[[OpHandler], OpHandler]`
- `emit_c_value_impl(*types: type[Any], target: str | None = None, override: bool = False) -> Callable[[ValueHandler], ValueHandler]`
- `emit_c_type_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[TypeHandler], TypeHandler]`
- `emit_c_attr_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[AttrHandler], AttrHandler]`
- `emit_c_include_impl(*, target: str, override: bool = False) -> Callable[[IncludeHandler], IncludeHandler]`
- `emit_c_name_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[NameHandler], NameHandler]`
- `dispatch_op(op: Operation, ctx: EmitCContext) -> str | None`
- `dispatch_op_for_target(op: Operation, ctx: EmitCContext, target: str) -> str | None`
- `dispatch_value(value: SSAValue, ctx: EmitCContext) -> str | None`
- `dispatch_type(attr: Any, ctx: EmitCContext) -> str | None`
- `dispatch_attr(attr: Any, ctx: EmitCContext) -> str | None`
- `dispatch_include(ctx: EmitCContext) -> str`
- `dispatch_name(value: SSAValue, ctx: EmitCContext) -> str | None`

## 文档信息

- `spec`：`spec/dsl/gen_kernel/emit/register.md`
- `功能实现`：`kernel_gen/dsl/gen_kernel/emit/register.py`
- `test`：`test/dsl/gen_kernel/emit/test_package.py`
- `test`：`test/dsl/gen_kernel/test_backend_loader.py`
- `test`：`test/dsl/gen_kernel/test_module_emitter.py`
- `test`：`test/dsl/gen_kernel/test_source_bundle.py`

## 依赖

- [`spec/core/config.md`](../../../../spec/core/config.md)
- [`spec/core/error.md`](../../../../spec/core/error.md)
- [`spec/dsl/gen_kernel/emit_context.md`](../../../../spec/dsl/gen_kernel/emit_context.md)
- [`spec/dsl/gen_kernel/source_product.md`](../source_product.md)
- [`spec/target/registry.md`](../../../target/registry.md)

## 目标

- 统一 op / value / type / attr / include / name 的注册入口。
- 保证 target backend 不存在或 handler 缺失时公开失败，不得 silent fallback 到 `cpu`。
- 允许 `ModuleOp` handler 返回单文件源码或多文件 `SourceProduct`。

## 模块边界

- 本模块之外不得新增平行注册器。
- target 名称只允许小写字母、数字和下划线；空字符串、路径片段、大小写变体和分隔符必须失败。
- 已注册 target 会触发 backend auto-load；未注册 target 不触发 backend auto-load，也不得 fallback 到 CPU。
- `override=False` 时重复注册同一 target/type 必须失败，稳定错误文本包含 `duplicate backend registration`。
- `dispatch_op_for_target(...)` 只查询指定 target 的注册表，不得回退到默认注册表或 CPU 注册表。
- backend 导入失败必须区分：
  - 已注册 target 的目标模块不存在：错误文本包含 `backend_not_found`。
  - 目标模块存在但内部导入失败：错误文本包含 `backend_import_failed`。
- `ModuleOp` handler 未注册时，错误文本必须包含 `backend_handler_not_found`。

## API详细说明

### `emit_c_impl(*types: type[Any], target: str | None = None, override: bool = False) -> Callable[[OpHandler], OpHandler]`

- 参数：
  - `types`：要注册的 operation 类型；允许一个或多个 `type`；必须显式传入。
  - `target`：target 名称；`None` 表示默认 op 注册表；非空时必须符合 target 命名规则。
  - `override`：是否允许覆盖同一 target/type 的已有 handler；默认 `False`。
- 返回值：装饰器，接收 handler 并返回原 handler。
- 功能说明：注册 operation handler；handler 签名为 `(op: Operation, ctx: EmitCContext) -> str | Mapping[str, str]`。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import ModuleOp

  from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl

  @emit_c_impl(ModuleOp, target="dummy_generic")
  def emit_module(op, ctx):
      return {"kernel.cpp": "void kernel() {}\\n"}
  ```
- 注意事项：返回 `Mapping[str, str]` 时按 `SourceProduct` 合同编码为多文件 SourceBundle aggregate string；非法返回类型必须以 `source_product_invalid` 失败。

### `emit_c_value_impl(*types: type[Any], target: str | None = None, override: bool = False) -> Callable[[ValueHandler], ValueHandler]`

- 参数：
  - `types`：要注册的 SSA value 类型。
  - `target`：target 名称；`None` 表示默认 value 注册表。
  - `override`：是否允许覆盖已有 handler。
- 返回值：装饰器，接收 handler 并返回原 handler。
- 功能说明：注册 SSA value handler；handler 签名为 `(value: SSAValue, ctx: EmitCContext) -> str`。
- 使用示例：

  ```python
  from xdsl.ir import BlockArgument

  from kernel_gen.dsl.gen_kernel.emit.register import emit_c_value_impl

  @emit_c_value_impl(BlockArgument, target="dummy_generic")
  def emit_argument(value, ctx):
      return ctx.create_or_get_name(value)
  ```
- 注意事项：handler 必须返回字符串；重复注册按 `override` 规则处理。

### `emit_c_type_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[TypeHandler], TypeHandler]`

- 参数：
  - `types`：要注册的 type attribute 类型。
  - `target`：target 名称；必须符合 target 命名规则。
  - `override`：是否允许覆盖已有 handler。
- 返回值：装饰器，接收 handler 并返回原 handler。
- 功能说明：注册 type attribute handler；handler 签名为 `(attr: Any, ctx: EmitCContext) -> str`。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import i32

  from kernel_gen.dsl.gen_kernel.emit.register import emit_c_type_impl

  @emit_c_type_impl(type(i32), target="dummy_generic")
  def emit_i32(attr, ctx):
      return "int32_t"
  ```
- 注意事项：注册器不校验 type 语义，只校验注册键与重复注册。

### `emit_c_attr_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[AttrHandler], AttrHandler]`

- 参数：
  - `types`：要注册的 attribute 类型。
  - `target`：target 名称；必须符合 target 命名规则。
  - `override`：是否允许覆盖已有 handler。
- 返回值：装饰器，接收 handler 并返回原 handler。
- 功能说明：注册普通 attribute handler。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import StringAttr

  from kernel_gen.dsl.gen_kernel.emit.register import emit_c_attr_impl

  @emit_c_attr_impl(StringAttr, target="dummy_generic")
  def emit_string(attr, ctx):
      return attr.data
  ```
- 注意事项：未注册 attribute 由调用方按公开错误语义处理。

### `emit_c_include_impl(*, target: str, override: bool = False) -> Callable[[IncludeHandler], IncludeHandler]`

- api：`emit_c_include_impl(*, target: str, override: bool = False) -> Callable[[IncludeHandler], IncludeHandler]`

- 参数：
  - `target`：target 名称；必须符合 target 命名规则。
  - `override`：是否允许覆盖已有 include handler。
- 返回值：装饰器，接收 handler 并返回原 handler。
- 功能说明：注册 target include handler；handler 签名为 `(ctx: EmitCContext) -> str`。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import emit_c_include_impl

  @emit_c_include_impl(target="dummy_generic")
  def emit_include(ctx):
      return "#include <dummy.h>\\n"
  ```
- 注意事项：未注册 include handler 时 `dispatch_include(...)` 返回空字符串。

### `emit_c_name_impl(*types: type[Any], target: str, override: bool = False) -> Callable[[NameHandler], NameHandler]`

- 参数：
  - `types`：要注册的 value 类型。
  - `target`：target 名称；必须符合 target 命名规则。
  - `override`：是否允许覆盖已有 name handler。
- 返回值：装饰器，接收 handler 并返回原 handler。
- 功能说明：注册 target-specific 命名 handler；handler 签名为 `(value: SSAValue, ctx: EmitCContext) -> str | None`。
- 使用示例：

  ```python
  from xdsl.ir import BlockArgument

  from kernel_gen.dsl.gen_kernel.emit.register import emit_c_name_impl

  @emit_c_name_impl(BlockArgument, target="dummy_generic")
  def emit_name(value, ctx):
      return ctx.create_or_get_name(value)
  ```
- 注意事项：返回 `None` 表示当前 handler 不处理该 value。

### `dispatch_op(op: Operation, ctx: EmitCContext) -> str | None`

- 参数：
  - `op`：待发射 operation。
  - `ctx`：公开 EmitC 上下文。
- 返回值：源码字符串或 `None`。
- 功能说明：按当前 target 自动加载 backend 并查找 operation handler。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import dispatch_op

  stmt = dispatch_op(op, ctx)
  ```
- 注意事项：`ModuleOp` handler 返回 `Mapping[str, str]` 时必须自动编码为 SourceBundle aggregate string。

### `dispatch_op_for_target(op: Operation, ctx: EmitCContext, target: str) -> str | None`

- 参数：
  - `op`：待发射 operation。
  - `ctx`：公开 EmitC 上下文。
  - `target`：显式查询的 target 名称。
- 返回值：源码字符串或 `None`。
- 功能说明：只查询指定 target 的 operation handler。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import dispatch_op_for_target

  stmt = dispatch_op_for_target(op, ctx, "dummy_generic")
  ```
- 注意事项：该函数不得 fallback 到 CPU 或默认 handler。

### `dispatch_value(value: SSAValue, ctx: EmitCContext) -> str | None`

- 参数：
  - `value`：待发射 SSA value。
  - `ctx`：公开 EmitC 上下文。
- 返回值：源码字符串或 `None`。
- 功能说明：按当前 target 自动加载 backend 并查找 value handler。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import dispatch_value

  expr = dispatch_value(value, ctx)
  ```
- 注意事项：未注册时返回 `None`。

### `dispatch_type(attr: Any, ctx: EmitCContext) -> str | None`

- 参数：
  - `attr`：待发射 type attribute。
  - `ctx`：公开 EmitC 上下文。
- 返回值：源码字符串或 `None`。
- 功能说明：按当前 target 自动加载 backend 并查找 type handler。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import dispatch_type

  type_text = dispatch_type(attr, ctx)
  ```
- 注意事项：未注册时返回 `None`。

### `dispatch_attr(attr: Any, ctx: EmitCContext) -> str | None`

- 参数：
  - `attr`：待发射 attribute。
  - `ctx`：公开 EmitC 上下文。
- 返回值：源码字符串或 `None`。
- 功能说明：按当前 target 自动加载 backend 并查找 attribute handler。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import dispatch_attr

  attr_text = dispatch_attr(attr, ctx)
  ```
- 注意事项：未注册时返回 `None`。

### `dispatch_include(ctx: EmitCContext) -> str`

- 参数：
  - `ctx`：公开 EmitC 上下文。
- 返回值：include 源码字符串；未注册时为空字符串。
- 功能说明：按当前 target 自动加载 backend 并查找 include handler。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import dispatch_include

  include_text = dispatch_include(ctx)
  ```
- 注意事项：该函数不合成默认 include。

### `dispatch_name(value: SSAValue, ctx: EmitCContext) -> str | None`

- 参数：
  - `value`：待命名 SSA value。
  - `ctx`：公开 EmitC 上下文。
- 返回值：源码名称或 `None`。
- 功能说明：按当前 target 自动加载 backend 并查找 name handler。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit.register import dispatch_name

  name = dispatch_name(value, ctx)
  ```
- 注意事项：未注册时返回 `None`。

## 测试

- 测试文件：`test/dsl/gen_kernel/test_backend_loader.py`
- 测试文件：`test/dsl/gen_kernel/test_module_emitter.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/test_backend_loader.py test/dsl/gen_kernel/test_module_emitter.py`

### 测试目标

- 验证 backend auto-load、target 校验、缺失 backend、导入失败和 handler 缺失错误语义。
- 验证重复注册默认失败、`override=True` 可覆盖。
- 验证 `ModuleOp` handler 可返回单文件源码或 SourceBundle。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TG-EMIT-REG-001 | backend 加载 | 已注册 target 的 backend 模块可自动导入。 | 注册 `dummy_generic` target。 | 调用 `emit_c(module_op, ctx)`。 | 返回 dummy backend 源码，不走 CPU fallback。 | `test_backend_loader_imports_registered_dummy_backend` |
| TG-EMIT-REG-002 | 错误语义 | target 未注册时不回退 CPU。 | 设置未注册 target。 | 调用 `emit_c(module_op, ctx)`。 | 抛出公开错误且不出现 CPU 源码。 | `test_backend_loader_rejects_unregistered_target_without_cpu_fallback` |
| TG-EMIT-REG-003 | 错误语义 | backend 模块不存在时拒绝生成。 | 注册 target 但不提供 backend 模块。 | 调用 `emit_c(module_op, ctx)`。 | 抛出 `KernelCodeError`，文本包含 `backend_not_found`。 | `test_backend_loader_distinguishes_missing_module` |
| TG-EMIT-REG-004 | 错误语义 | backend 模块内部导入失败。 | 提供会导入缺失依赖的 backend 模块。 | 调用 `emit_c(module_op, ctx)`。 | 抛出 `KernelCodeError`，文本包含 `backend_import_failed`。 | `test_backend_loader_distinguishes_backend_import_failure` |
| TG-EMIT-REG-005 | 错误语义 | backend 未注册 `ModuleOp` handler。 | backend 模块存在但无 handler。 | 调用 `emit_c(module_op, ctx)`。 | 抛出 `KernelCodeError`，文本包含 `backend_handler_not_found`。 | `test_backend_loader_distinguishes_missing_module_handler` |
| TG-EMIT-REG-006 | 注册边界 | 重复注册默认失败。 | 同一 target/type 已有 handler。 | 再次调用注册装饰器。 | 抛出 `KernelCodeError`，文本包含 `duplicate backend registration`。 | `test_emit_registry_duplicate_requires_explicit_override` |
| TG-EMIT-REG-007 | SourceProduct | `ModuleOp` handler 返回 `Mapping[str, str]`。 | backend handler 返回多个 artifact。 | 调用 `emit_c(module_op, ctx)`。 | 返回 SourceBundle aggregate string。 | `test_module_handler_returns_mapping_as_source_bundle` |
