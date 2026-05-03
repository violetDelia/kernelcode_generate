# register.md

## 功能简介

- 定义 `emit` 层的公开注册器与 dispatch 合同。
- 该模块是当前唯一允许下游扩展 target-specific emit 行为的公开入口。

## API 列表

- `emit_c_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str | None = None)`
- `emit_c_value_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str | None = None)`
- `emit_c_type_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`
- `emit_c_attr_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`
- `emit_c_include_impl(target: str)`
- `emit_c_name_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`
- `dispatch_op(op, ctx: EmitCContext)`
- `dispatch_op_for_target(op, ctx: EmitCContext, target: str)`
- `dispatch_value(value, ctx: EmitCContext)`
- `dispatch_type(attr, ctx: EmitCContext)`
- `dispatch_attr(attr, ctx: EmitCContext)`
- `dispatch_include(ctx: EmitCContext)`
- `dispatch_name(value, ctx: EmitCContext)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/gen_kernel/emit/register.md`](../../../../spec/dsl/gen_kernel/emit/register.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/register.py`](../../../../kernel_gen/dsl/gen_kernel/emit/register.py)
- `test`：[`test/dsl/gen_kernel/emit/test_package.py`](../../../../test/dsl/gen_kernel/emit/test_package.py)

## 依赖

- [`spec/dsl/gen_kernel/emit_context.md`](../../../../spec/dsl/gen_kernel/emit_context.md)

## 目标

- 统一 target / type / attr / include 的注册入口。
- 避免在 target 目录之外维护第二套 dispatch 机制。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本模块之外不得新增平行注册器。
- 注册器以外的 helper 不构成公开 API。
## API详细说明

### `emit_c_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str | None = None)`

- api：`emit_c_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str | None = None)`
- 参数：
  - `types`：类型对象集合，定义当前 API 需要处理或注册的一组类型语义；类型 `type[Operation] | type[BlockArgument] | type[Attribute] | type[str]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`emit_c_impl` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = emit_c_impl(types=types, target=None)
  ```
- 功能说明：生成 `c_impl`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `emit_c_value_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str | None = None)`

- api：`emit_c_value_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str | None = None)`
- 参数：
  - `types`：类型对象集合，定义当前 API 需要处理或注册的一组类型语义；类型 `type[Operation] | type[BlockArgument] | type[Attribute] | type[str]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`emit_c_value_impl` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = emit_c_value_impl(types=types, target=None)
  ```
- 功能说明：生成 `c_value_impl`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `emit_c_type_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`

- api：`emit_c_type_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`
- 参数：
  - `types`：类型对象集合，定义当前 API 需要处理或注册的一组类型语义；类型 `type[Operation] | type[BlockArgument] | type[Attribute] | type[str]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`emit_c_type_impl` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = emit_c_type_impl(types=types, target=target)
  ```
- 功能说明：生成 `c_type_impl`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `emit_c_attr_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`

- api：`emit_c_attr_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`
- 参数：
  - `types`：类型对象集合，定义当前 API 需要处理或注册的一组类型语义；类型 `type[Operation] | type[BlockArgument] | type[Attribute] | type[str]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`emit_c_attr_impl` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = emit_c_attr_impl(types=types, target=target)
  ```
- 功能说明：生成 `c_attr_impl`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `emit_c_include_impl(target: str)`

- api：`emit_c_include_impl(target: str)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`emit_c_include_impl` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = emit_c_include_impl(target=target)
  ```
- 功能说明：生成 `c_include_impl`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `emit_c_name_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`

- api：`emit_c_name_impl(*types: type[Operation] | type[BlockArgument] | type[Attribute] | type[str], target: str)`
- 参数：
  - `types`：类型对象集合，定义当前 API 需要处理或注册的一组类型语义；类型 `type[Operation] | type[BlockArgument] | type[Attribute] | type[str]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`emit_c_name_impl` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = emit_c_name_impl(types=types, target=target)
  ```
- 功能说明：生成 `c_name_impl`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `dispatch_op(op, ctx: EmitCContext)`

- api：`dispatch_op(op, ctx: EmitCContext)`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `Operation | SSAValue | Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`dispatch_op` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = dispatch_op(op=op, ctx=ctx)
  ```
- 功能说明：执行 `dispatch_op`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `dispatch_op_for_target(op, ctx: EmitCContext, target: str)`

- api：`dispatch_op_for_target(op, ctx: EmitCContext, target: str)`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `Operation | SSAValue | Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`dispatch_op_for_target` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = dispatch_op_for_target(op=op, ctx=ctx, target=target)
  ```
- 功能说明：执行 `dispatch_op_for_target`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `dispatch_value(value, ctx: EmitCContext)`

- api：`dispatch_value(value, ctx: EmitCContext)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `Operation | SSAValue | Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`dispatch_value` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = dispatch_value(value=value, ctx=ctx)
  ```
- 功能说明：执行 `dispatch_value`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `dispatch_type(attr, ctx: EmitCContext)`

- api：`dispatch_type(attr, ctx: EmitCContext)`
- 参数：
  - `attr`：IR attribute，作为 emit、解析、打印或语义判断的输入属性；类型 `Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`dispatch_type` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = dispatch_type(attr=attr, ctx=ctx)
  ```
- 功能说明：执行 `dispatch_type`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `dispatch_attr(attr, ctx: EmitCContext)`

- api：`dispatch_attr(attr, ctx: EmitCContext)`
- 参数：
  - `attr`：IR attribute，作为 emit、解析、打印或语义判断的输入属性；类型 `Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`dispatch_attr` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = dispatch_attr(attr=attr, ctx=ctx)
  ```
- 功能说明：执行 `dispatch_attr`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `dispatch_include(ctx: EmitCContext)`

- api：`dispatch_include(ctx: EmitCContext)`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`dispatch_include` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = dispatch_include(ctx=ctx)
  ```
- 功能说明：执行 `dispatch_include`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `dispatch_name(value, ctx: EmitCContext)`

- api：`dispatch_name(value, ctx: EmitCContext)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `Operation | SSAValue | Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`dispatch_name` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  result = dispatch_name(value=value, ctx=ctx)
  ```
- 功能说明：执行 `dispatch_name`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

## 测试

- 测试文件：`test/dsl/gen_kernel/emit/test_package.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_package.py`

### 测试目标

- 验证 `spec/dsl/gen_kernel/emit/register.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-001 | 公开入口 | emit c public entry matches gen kernel for empty func | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_public_entry_matches_gen_kernel_for_empty_func`。 | 公开入口在“emit c public entry matches gen kernel for empty func”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_public_entry_matches_gen_kernel_for_empty_func` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-002 | 公开入口 | emit c public entry lowers func and single func module consistently | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_public_entry_lowers_func_and_single_func_module_consistently`。 | 公开入口在“emit c public entry lowers func and single func module consistently”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_public_entry_lowers_func_and_single_func_module_consistently` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-003 | 公开入口 | emit c package registers common op and value types | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_package_registers_common_op_and_value_types`。 | 公开入口在“emit c package registers common op and value types”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_package_registers_common_op_and_value_types` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-004 | 公开入口 | emit c context type helpers use target registry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_context_type_helpers_use_target_registry`。 | 公开入口在“emit c context type helpers use target registry”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_context_type_helpers_use_target_registry` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-005 | 公开入口 | emit c context type helpers dispatch npu demo type and space registry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry`。 | 公开入口在“emit c context type helpers dispatch npu demo type and space registry”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-006 | 生成/编译 | emit c context reads core config target | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_context_reads_core_config_target`。 | 生成源码、IR 文本或编译结果体现“emit c context reads core config target”场景。 | `test_emit_c_context_reads_core_config_target` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-007 | 边界/异常 | emit c package value fast paths and legacy kernel add rejects | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects`。 | “emit c package value fast paths and legacy kernel add rejects”场景按公开错误语义失败或被拒绝。 | `test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-008 | pass 改写 | emit c op lowers arith add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_arith_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers arith add”场景。 | `test_emit_c_op_lowers_arith_add` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-009 | pass 改写 | emit c value lowers compare | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_value_lowers_compare`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c value lowers compare”场景。 | `test_emit_c_value_lowers_compare` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-010 | 生成/编译 | emit c value unbound block argument uses index | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_value_unbound_block_argument_uses_index`。 | 生成源码、IR 文本或编译结果体现“emit c value unbound block argument uses index”场景。 | `test_emit_c_value_unbound_block_argument_uses_index` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-011 | pass 改写 | emit c op lowers scf for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_scf_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers scf for”场景。 | `test_emit_c_op_lowers_scf_for` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-012 | pass 改写 | emit c op lowers memory access | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_memory_access`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers memory access”场景。 | `test_emit_c_op_lowers_memory_access` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-013 | 边界/异常 | emit c op rejects unsupported op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_rejects_unsupported_op`。 | “emit c op rejects unsupported op”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_rejects_unsupported_op` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-014 | 边界/异常 | emit c value rejects invalid dependency | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_value_rejects_invalid_dependency`。 | “emit c value rejects invalid dependency”场景按公开错误语义失败或被拒绝。 | `test_emit_c_value_rejects_invalid_dependency` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-015 | pass 改写 | emit c op lowers symbol add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_symbol_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers symbol add”场景。 | `test_emit_c_op_lowers_symbol_add` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-016 | 边界/异常 | emit c op rejects symbol add on non cpu | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_rejects_symbol_add_on_non_cpu`。 | “emit c op rejects symbol add on non cpu”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_rejects_symbol_add_on_non_cpu` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-017 | pass 改写 | emit c op lowers npu demo symbol const cast and to float | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol const cast and to float”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-018 | pass 改写 | emit c lowers npu demo plain symbol module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo plain symbol module without launch wrapper”场景。 | `test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-019 | pass 改写 | emit c lowers npu demo return only plain module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo return only plain module without launch wrapper”场景。 | `test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-020 | pass 改写 | emit c op lowers npu demo symbol binary and compare | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol binary and compare”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-021 | pass 改写 | emit c op lowers npu demo symbol queries | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_queries`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol queries”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_queries` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-022 | pass 改写 | emit c op lowers npu demo symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol for”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_for` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-023 | pass 改写 | emit c op lowers mlir gen NN add variants after pass | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_mlir_gen_nn_add_variants_after_pass`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers mlir gen NN add variants after pass”场景。 | `test_emit_c_op_lowers_mlir_gen_nn_add_variants_after_pass` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-024 | 生成/编译 | emit c op keeps NN add unsupported without prebound result or on non cpu | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu`。 | 生成源码、IR 文本或编译结果体现“emit c op keeps NN add unsupported without prebound result or on non cpu”场景。 | `test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-025 | 生成/编译 | emit c memory space template alloc | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_memory_space_template_alloc`。 | 生成源码、IR 文本或编译结果体现“emit c memory space template alloc”场景。 | `test_emit_c_memory_space_template_alloc` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-026 | 边界/异常 | emit c op lowers kernel family and rejects unsupported reduce kind | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind`。 | “emit c op lowers kernel family and rejects unsupported reduce kind”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-027 | pass 改写 | emit c lowers npu demo DMA alloc helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA alloc helper contract”场景。 | `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-028 | pass 改写 | emit c lowers npu demo DMA broadcast helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA broadcast helper contract”场景。 | `test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-029 | pass 改写 | emit c lowers npu demo DMA scalar broadcast as fill contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_scalar_broadcast_as_fill_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA scalar broadcast as fill contract”场景。 | `test_emit_c_lowers_npu_demo_dma_scalar_broadcast_as_fill_contract` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-030 | pass 改写 | emit c lowers cpu DMA broadcast helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_cpu_dma_broadcast_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers cpu DMA broadcast helper contract”场景。 | `test_emit_c_lowers_cpu_dma_broadcast_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-031 | pass 改写 | emit c lowers npu demo DMA misc helper contracts | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_misc_helper_contracts`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA misc helper contracts”场景。 | `test_emit_c_lowers_npu_demo_dma_misc_helper_contracts` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-032 | 生成/编译 | emit c private helper and context edges | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_private_helper_and_context_edges`。 | 生成源码、IR 文本或编译结果体现“emit c private helper and context edges”场景。 | `test_emit_c_private_helper_and_context_edges` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-033 | 生成/编译 | emit c private layout and operand helpers | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_private_layout_and_operand_helpers`。 | 生成源码、IR 文本或编译结果体现“emit c private layout and operand helpers”场景。 | `test_emit_c_private_layout_and_operand_helpers` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-034 | 边界/异常 | emit c private additional error matrix | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_private_additional_error_matrix`。 | “emit c private additional error matrix”场景按公开错误语义失败或被拒绝。 | `test_emit_c_private_additional_error_matrix` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-035 | pass 改写 | emit c lowers npu demo DMA indexed and fill helpers | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA indexed and fill helpers”场景。 | `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-036 | pass 改写 | emit c lowers npu demo DMA fill infinity literal | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_fill_infinity_literal`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA fill infinity literal”场景。 | `test_emit_c_lowers_npu_demo_dma_fill_infinity_literal` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-037 | pass 改写 | emit c op lowers passed mixed add pipeline with DMA fill | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers passed mixed add pipeline with DMA fill”场景。 | `test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-038 | pass 改写 | emit c op lowers DMA alloc and view | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_dma_alloc_and_view`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers DMA alloc and view”场景。 | `test_emit_c_op_lowers_dma_alloc_and_view` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-039 | pass 改写 | emit c op lowers img2col2d DMA loop pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_img2col2d_dma_loop_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers img2col2d DMA loop pipeline”场景。 | `test_emit_c_op_lowers_img2col2d_dma_loop_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-040 | 生成/编译 | emit c op assigns unique helper names for repeated DMA slice and deslice | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice`。 | 生成源码、IR 文本或编译结果体现“emit c op assigns unique helper names for repeated DMA slice and deslice”场景。 | `test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-041 | 公开入口 | emit c package registers tuner cost op | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_package_registers_tuner_cost_op`。 | 公开入口在“emit c package registers tuner cost op”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_package_registers_tuner_cost_op` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-042 | pass 改写 | emit c lowers npu demo tuner cost kernel add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel add”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-043 | pass 改写 | emit c lowers npu demo tuner cost kernel binary elewise | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel binary elewise”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-044 | pass 改写 | emit c lowers npu demo tuner cost kernel exp select reduce | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel exp select reduce”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-045 | pass 改写 | emit c lowers npu demo tuner cost kernel matmul | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel matmul”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-046 | pass 改写 | emit c lowers npu demo tuner cost kernel img2col2d | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel img2col2d”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-047 | pass 改写 | emit c lowers npu demo tuner cost DMA copy | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost DMA copy”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-048 | pass 改写 | emit c lowers npu demo tuner cost DMA slice and deslice | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost DMA slice and deslice”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-049 | pass 改写 | emit c lowers npu demo symbol add with tuner cost value | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo symbol add with tuner cost value”场景。 | `test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-050 | 边界/异常 | emit c rejects unknown npu demo tuner cost op name | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name`。 | “emit c rejects unknown npu demo tuner cost op name”场景按公开错误语义失败或被拒绝。 | `test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-051 | 边界/异常 | emit c preserves raw npu demo tuner cost kind and rejects invalid memory type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type`。 | “emit c preserves raw npu demo tuner cost kind and rejects invalid memory type”场景按公开错误语义失败或被拒绝。 | `test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-052 | pass 改写 | emit c lowers npu demo kernel context queries | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_kernel_context_queries`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo kernel context queries”场景。 | `test_emit_c_lowers_npu_demo_kernel_context_queries` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-053 | 生成/编译 | emit c maps NN space to template param | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_maps_nn_space_to_template_param`。 | 生成源码、IR 文本或编译结果体现“emit c maps NN space to template param”场景。 | `test_emit_c_maps_nn_space_to_template_param` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-054 | pass 改写 | emit c lowers npu demo slice deslice add pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo slice deslice add pipeline”场景。 | `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-REGISTER-055 | pass 改写 | emit c lowers npu demo tiled matmul pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tiled matmul pipeline”场景。 | `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline` |
