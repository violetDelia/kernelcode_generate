# emit_context.md

## 功能简介

- 定义 `EmitCContext` 的稳定公开入口。
- 失败统一抛出 `KernelCodeError(ErrorModule.GEN_KERNEL, message)`；不再定义或导出上下文专属错误类。
- 负责：
  - emit 阶段命名状态
  - 节点 / value / type / attr / include 分发
  - target 相关 type / space 文本转换入口
- `EmitCContext` 只允许无参构造；target 等公开行为配置必须先通过 `kernel_gen.core.config` 设置。
- `EmitCContext` 只承载单次 emit 发射状态，不承载公开行为配置。

## API 列表

- `class EmitCContext()`
- `EmitCContext.create_or_get_name(value: SSAValue) -> str`
- `EmitCContext.allocate_name(prefix: str) -> str`
- `EmitCContext.lookup_cached_name(scope: str, key: CacheKey) -> str | None`
- `EmitCContext.bind_cached_name(scope: str, key: CacheKey, name: str) -> str`
- `EmitCContext.is_target(name: str) -> bool`
- `EmitCContext.target_entry(table: Mapping[str, T], default: T | None = None) -> T | None`
- `EmitCContext.emit_error(subject: str, reason: str) -> KernelCodeError`
- `EmitCContext.dispatch(obj: Operation | SSAValue | Attribute | str) -> str | None`
- `EmitCContext.dispatch_op(op: Operation) -> str | None`
- `EmitCContext.dispatch_value(value: SSAValue) -> str | None`
- `EmitCContext.dispatch_type(attr: Attribute | str) -> str`
- `EmitCContext.dispatch_attr(attr: Attribute | str) -> str | None`
- `EmitCContext.dispatch_include() -> str`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit_context.py`](../../../kernel_gen/dsl/gen_kernel/emit_context.py)
- `test`：[`test/dsl/gen_kernel/emit/test_package.py`](../../../test/dsl/gen_kernel/emit/test_package.py)

## 依赖

- [`spec/dsl/gen_kernel/emit/register.md`](../../../spec/dsl/gen_kernel/emit/register.md)
- [`spec/dsl/gen_kernel/emit/npu_demo.md`](../../../spec/dsl/gen_kernel/emit/npu_demo.md)

## 目标

- 提供统一上下文，避免在 target 实现中再维护平行类型 / `space` 转换壳。
- `space` 相关文本统一走 `dispatch_attr(...)` 的 target 注册，不再在 context 上公开独立 `space_*_to_c` 接口。
- `class EmitCContext()` 构造时从 `kernel_gen.core.config.get_target()` 读取 target 快照；target 未设置或不是非空字符串时必须失败。
- target 字符串不作为 `EmitCContext` 公开属性暴露；跨文件代码只能通过 `is_target(...)`、`target_entry(...)` 或更具体的公开方法访问 target 相关行为。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `EmitCContext` 只定义 emit 上下文，不承接函数级策略。
- `class EmitCContext()` 不接受 `target=`、`config=`、`indent=`、`naming=`、`type_converter=` 等公开关键字。
- 命名、局部缓存和转换状态统一收口到 context 单次状态；不得在 target 目录中维护第二套全局状态。
- 不公开可变状态字典；需要命名递增或局部名称缓存时，使用 `allocate_name(...)`、`lookup_cached_name(...)`、`bind_cached_name(...)`。
## API详细说明

### `class EmitCContext()`

- api：`class EmitCContext()`
- 参数：无。
- 返回值：`EmitCContext` 实例。
- 使用示例：

  ```python
  emit_c_context = EmitCContext()
  ```
- 功能说明：构造 `EmitCContext` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `EmitCContext.create_or_get_name(value: SSAValue) -> str`

- api：`EmitCContext.create_or_get_name(value: SSAValue) -> str`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.create_or_get_name(value=value)
  ```
- 功能说明：创建 `or_get_name`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `EmitCContext.allocate_name(prefix: str) -> str`

- api：`EmitCContext.allocate_name(prefix: str) -> str`
- 参数：
  - `prefix`：`prefix` 输入值，参与 `allocate_name` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.allocate_name(prefix=prefix)
  ```
- 功能说明：执行 `allocate_name`。
- 注意事项：输入 memory、offset、size、stride 和 dtype 必须符合 DMA operation 合同；非法组合必须稳定失败。

### `EmitCContext.lookup_cached_name(scope: str, key: CacheKey) -> str | None`

- api：`EmitCContext.lookup_cached_name(scope: str, key: CacheKey) -> str | None`
- 参数：
  - `scope`：作用域标识，指定 barrier、注册、查找或名字分配的有效范围；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `key`：查找键或注册键，用于定位 registry、映射表或缓存中的公开条目；类型 `CacheKey`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str | None`。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.lookup_cached_name(scope=scope, key=key)
  ```
- 功能说明：执行 `lookup_cached_name`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `EmitCContext.bind_cached_name(scope: str, key: CacheKey, name: str) -> str`

- api：`EmitCContext.bind_cached_name(scope: str, key: CacheKey, name: str) -> str`
- 参数：
  - `scope`：作用域标识，指定 barrier、注册、查找或名字分配的有效范围；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `key`：查找键或注册键，用于定位 registry、映射表或缓存中的公开条目；类型 `CacheKey`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.bind_cached_name(scope=scope, key=key, name=name)
  ```
- 功能说明：执行 `bind_cached_name`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `EmitCContext.is_target(name: str) -> bool`

- api：`EmitCContext.is_target(name: str) -> bool`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.is_target(name=name)
  ```
- 功能说明：执行 `is_target`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `EmitCContext.target_entry(table: Mapping[str, T], default: T | None = None) -> T | None`

- api：`EmitCContext.target_entry(table: Mapping[str, T], default: T | None = None) -> T | None`
- 参数：
  - `table`：表格或映射数据，用于注册、查找或展示公开条目；类型 `Mapping[str, T]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `default`：未显式传参时使用的默认值；类型 `T | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`T | None`。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.target_entry(table=table, default=None)
  ```
- 功能说明：执行 `target_entry`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `EmitCContext.emit_error(subject: str, reason: str) -> KernelCodeError`

- api：`EmitCContext.emit_error(subject: str, reason: str) -> KernelCodeError`
- 参数：
  - `subject`：被检查对象，作为断言、校验或比较的主体；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `reason`：失败原因或拒绝原因，用于解释当前接口不能继续处理的条件；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`KernelCodeError`。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.emit_error(subject=subject, reason=reason)
  ```
- 功能说明：生成 `error`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `EmitCContext.dispatch(obj: Operation | SSAValue | Attribute | str) -> str | None`

- api：`EmitCContext.dispatch(obj: Operation | SSAValue | Attribute | str) -> str | None`
- 参数：
  - `obj`：`obj` 输入值，参与 `dispatch` 的公开处理流程；类型 `Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str | None`。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.dispatch(obj=obj)
  ```
- 功能说明：执行 `dispatch`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `EmitCContext.dispatch_op(op: Operation) -> str | None`

- api：`EmitCContext.dispatch_op(op: Operation) -> str | None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str | None`。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.dispatch_op(op=op)
  ```
- 功能说明：执行 `dispatch_op`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `EmitCContext.dispatch_value(value: SSAValue) -> str | None`

- api：`EmitCContext.dispatch_value(value: SSAValue) -> str | None`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str | None`。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.dispatch_value(value=value)
  ```
- 功能说明：执行 `dispatch_value`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `EmitCContext.dispatch_type(attr: Attribute | str) -> str`

- api：`EmitCContext.dispatch_type(attr: Attribute | str) -> str`
- 参数：
  - `attr`：IR attribute，作为 emit、解析、打印或语义判断的输入属性；类型 `Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.dispatch_type(attr=attr)
  ```
- 功能说明：执行 `dispatch_type`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `EmitCContext.dispatch_attr(attr: Attribute | str) -> str | None`

- api：`EmitCContext.dispatch_attr(attr: Attribute | str) -> str | None`
- 参数：
  - `attr`：IR attribute，作为 emit、解析、打印或语义判断的输入属性；类型 `Attribute | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str | None`。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.dispatch_attr(attr=attr)
  ```
- 功能说明：执行 `dispatch_attr`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `EmitCContext.dispatch_include() -> str`

- api：`EmitCContext.dispatch_include() -> str`
- 参数：无。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  emit_c_context = emit_c_context
  result = emit_c_context.dispatch_include()
  ```
- 功能说明：执行 `dispatch_include`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

## 测试

- 测试文件：`test/dsl/gen_kernel/emit/test_package.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_package.py`

### 测试目标

- 验证 `spec/dsl/gen_kernel/emit_context.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-001 | 公开入口 | emit c public entry matches gen kernel for empty func | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_public_entry_matches_gen_kernel_for_empty_func`。 | 公开入口在“emit c public entry matches gen kernel for empty func”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_public_entry_matches_gen_kernel_for_empty_func` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-002 | 公开入口 | emit c public entry lowers func and single func module consistently | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_public_entry_lowers_func_and_single_func_module_consistently`。 | 公开入口在“emit c public entry lowers func and single func module consistently”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_public_entry_lowers_func_and_single_func_module_consistently` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-003 | 公开入口 | emit c package registers common op and value types | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_package_registers_common_op_and_value_types`。 | 公开入口在“emit c package registers common op and value types”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_package_registers_common_op_and_value_types` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-004 | 公开入口 | emit c context type helpers use target registry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_context_type_helpers_use_target_registry`。 | 公开入口在“emit c context type helpers use target registry”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_context_type_helpers_use_target_registry` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-005 | 公开入口 | emit c context type helpers dispatch npu demo type and space registry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry`。 | 公开入口在“emit c context type helpers dispatch npu demo type and space registry”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-005A | 公开入口 | emit c context public state and dispatch edges | 准备公开 context、cache key、SSA value、op、attr 与非法 memory type。 | 运行 `test_emit_c_context_public_state_and_dispatch_edges`。 | 公开缓存、缩进、target 查询、统一 dispatch 与错误语义稳定，不暴露内部状态字典。 | `test_emit_c_context_public_state_and_dispatch_edges` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-006 | 生成/编译 | emit c context reads core config target | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_context_reads_core_config_target`。 | 生成源码、IR 文本或编译结果体现“emit c context reads core config target”场景。 | `test_emit_c_context_reads_core_config_target` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-007 | 边界/异常 | emit c package value fast paths and legacy kernel add rejects | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects`。 | “emit c package value fast paths and legacy kernel add rejects”场景按公开错误语义失败或被拒绝。 | `test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-008 | pass 改写 | emit c op lowers arith add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_arith_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers arith add”场景。 | `test_emit_c_op_lowers_arith_add` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-009 | pass 改写 | emit c value lowers compare | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_value_lowers_compare`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c value lowers compare”场景。 | `test_emit_c_value_lowers_compare` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-010 | 生成/编译 | emit c value unbound block argument uses index | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_value_unbound_block_argument_uses_index`。 | 生成源码、IR 文本或编译结果体现“emit c value unbound block argument uses index”场景。 | `test_emit_c_value_unbound_block_argument_uses_index` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-011 | pass 改写 | emit c op lowers scf for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_scf_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers scf for”场景。 | `test_emit_c_op_lowers_scf_for` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-012 | pass 改写 | emit c op lowers memory access | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_memory_access`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers memory access”场景。 | `test_emit_c_op_lowers_memory_access` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-013 | 边界/异常 | emit c op rejects unsupported op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_rejects_unsupported_op`。 | “emit c op rejects unsupported op”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_rejects_unsupported_op` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-014 | 边界/异常 | emit c value rejects invalid dependency | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_value_rejects_invalid_dependency`。 | “emit c value rejects invalid dependency”场景按公开错误语义失败或被拒绝。 | `test_emit_c_value_rejects_invalid_dependency` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-015 | pass 改写 | emit c op lowers symbol add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_symbol_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers symbol add”场景。 | `test_emit_c_op_lowers_symbol_add` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-016 | 边界/异常 | emit c op rejects symbol add on non cpu | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_rejects_symbol_add_on_non_cpu`。 | “emit c op rejects symbol add on non cpu”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_rejects_symbol_add_on_non_cpu` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-017 | pass 改写 | emit c op lowers npu demo symbol const cast and to float | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol const cast and to float”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-018 | pass 改写 | emit c lowers npu demo plain symbol module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo plain symbol module without launch wrapper”场景。 | `test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-019 | pass 改写 | emit c lowers npu demo return only plain module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo return only plain module without launch wrapper”场景。 | `test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-020 | pass 改写 | emit c op lowers npu demo symbol binary and compare | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol binary and compare”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-021 | pass 改写 | emit c op lowers npu demo symbol queries | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_queries`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol queries”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_queries` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-022 | pass 改写 | emit c op lowers npu demo symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol for”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_for` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-023 | pass 改写 | emit c op lowers mlir gen NN add variants after pass | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_mlir_gen_nn_add_variants_after_pass`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers mlir gen NN add variants after pass”场景。 | `test_emit_c_op_lowers_mlir_gen_nn_add_variants_after_pass` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-024 | 生成/编译 | emit c op keeps NN add unsupported without prebound result or on non cpu | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu`。 | 生成源码、IR 文本或编译结果体现“emit c op keeps NN add unsupported without prebound result or on non cpu”场景。 | `test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-025 | 生成/编译 | emit c memory space template alloc | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_memory_space_template_alloc`。 | 生成源码、IR 文本或编译结果体现“emit c memory space template alloc”场景。 | `test_emit_c_memory_space_template_alloc` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-026 | 边界/异常 | emit c op lowers kernel family and rejects unsupported reduce kind | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind`。 | “emit c op lowers kernel family and rejects unsupported reduce kind”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-027 | pass 改写 | emit c lowers npu demo DMA alloc helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA alloc helper contract”场景。 | `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-028 | pass 改写 | emit c lowers npu demo DMA broadcast helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA broadcast helper contract”场景。 | `test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-029 | pass 改写 | emit c lowers npu demo DMA scalar broadcast as fill contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_scalar_broadcast_as_fill_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA scalar broadcast as fill contract”场景。 | `test_emit_c_lowers_npu_demo_dma_scalar_broadcast_as_fill_contract` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-030 | pass 改写 | emit c lowers cpu DMA broadcast helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_cpu_dma_broadcast_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers cpu DMA broadcast helper contract”场景。 | `test_emit_c_lowers_cpu_dma_broadcast_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-031 | pass 改写 | emit c lowers npu demo DMA misc helper contracts | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_misc_helper_contracts`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA misc helper contracts”场景。 | `test_emit_c_lowers_npu_demo_dma_misc_helper_contracts` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-032 | 生成/编译 | emit c private helper and context edges | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_private_helper_and_context_edges`。 | 生成源码、IR 文本或编译结果体现“emit c private helper and context edges”场景。 | `test_emit_c_private_helper_and_context_edges` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-033 | 生成/编译 | emit c private layout and operand helpers | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_private_layout_and_operand_helpers`。 | 生成源码、IR 文本或编译结果体现“emit c private layout and operand helpers”场景。 | `test_emit_c_private_layout_and_operand_helpers` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-034 | 边界/异常 | emit c private additional error matrix | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_private_additional_error_matrix`。 | “emit c private additional error matrix”场景按公开错误语义失败或被拒绝。 | `test_emit_c_private_additional_error_matrix` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-035 | pass 改写 | emit c lowers npu demo DMA indexed and fill helpers | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA indexed and fill helpers”场景。 | `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-036 | pass 改写 | emit c lowers npu demo DMA fill infinity literal | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_fill_infinity_literal`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA fill infinity literal”场景。 | `test_emit_c_lowers_npu_demo_dma_fill_infinity_literal` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-037 | pass 改写 | emit c op lowers passed mixed add pipeline with DMA fill | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers passed mixed add pipeline with DMA fill”场景。 | `test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-038 | pass 改写 | emit c op lowers DMA alloc and view | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_dma_alloc_and_view`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers DMA alloc and view”场景。 | `test_emit_c_op_lowers_dma_alloc_and_view` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-039 | pass 改写 | emit c op lowers img2col2d DMA loop pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_img2col2d_dma_loop_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers img2col2d DMA loop pipeline”场景。 | `test_emit_c_op_lowers_img2col2d_dma_loop_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-040 | 生成/编译 | emit c op assigns unique helper names for repeated DMA slice and deslice | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice`。 | 生成源码、IR 文本或编译结果体现“emit c op assigns unique helper names for repeated DMA slice and deslice”场景。 | `test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-041 | 公开入口 | emit c package registers tuner cost op | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_package_registers_tuner_cost_op`。 | 公开入口在“emit c package registers tuner cost op”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_package_registers_tuner_cost_op` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-042 | pass 改写 | emit c lowers npu demo tuner cost kernel add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel add”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-043 | pass 改写 | emit c lowers npu demo tuner cost kernel binary elewise | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel binary elewise”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-044 | pass 改写 | emit c lowers npu demo tuner cost kernel exp select reduce | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel exp select reduce”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-045 | pass 改写 | emit c lowers npu demo tuner cost kernel matmul | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel matmul”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-046 | pass 改写 | emit c lowers npu demo tuner cost kernel img2col2d | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel img2col2d”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-047 | pass 改写 | emit c lowers npu demo tuner cost DMA copy | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost DMA copy”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-048 | pass 改写 | emit c lowers npu demo tuner cost DMA slice and deslice | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost DMA slice and deslice”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-049 | pass 改写 | emit c lowers npu demo symbol add with tuner cost value | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo symbol add with tuner cost value”场景。 | `test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-050 | 边界/异常 | emit c rejects unknown npu demo tuner cost op name | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name`。 | “emit c rejects unknown npu demo tuner cost op name”场景按公开错误语义失败或被拒绝。 | `test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-051 | 边界/异常 | emit c preserves raw npu demo tuner cost kind and rejects invalid memory type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type`。 | “emit c preserves raw npu demo tuner cost kind and rejects invalid memory type”场景按公开错误语义失败或被拒绝。 | `test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-052 | pass 改写 | emit c lowers npu demo kernel context queries | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_kernel_context_queries`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo kernel context queries”场景。 | `test_emit_c_lowers_npu_demo_kernel_context_queries` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-053 | 生成/编译 | emit c maps NN space to template param | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_maps_nn_space_to_template_param`。 | 生成源码、IR 文本或编译结果体现“emit c maps NN space to template param”场景。 | `test_emit_c_maps_nn_space_to_template_param` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-054 | pass 改写 | emit c lowers npu demo slice deslice add pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo slice deslice add pipeline”场景。 | `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-CONTEXT-055 | pass 改写 | emit c lowers npu demo tiled matmul pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tiled matmul pipeline”场景。 | `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline` |
