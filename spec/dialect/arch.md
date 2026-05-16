# arch.md

## 功能简介

- 定义 `arch` dialect 的硬件执行维度查询、barrier 与内核启动描述接口。
- 该方言只覆盖 block/thread/subthread/shared_memory_size 四层执行索引、执行规模查询、动态内存入口、barrier 与启动描述，不负责实际调度、循环或 memory 读写语义。
- 执行维度标量统一使用 `!symbol.int<#symbol.expr<expr>>` 表达，以便与现有 `symbol`、`dma`、`dsl` 链路保持一致。

## API 列表

- `class ArchScopeAttr(scope: StringAttr)`
- `ArchScopeAttr.from_name(name: str) -> ArchScopeAttr`
- `class ArchVisibilityAttr(visibility: StringAttr)`
- `ArchVisibilityAttr.from_name(name: str) -> ArchVisibilityAttr`
- `class ArchGetBlockIdOp(result_type: Attribute | None = None)`
- `class ArchGetBlockNumOp(result_type: Attribute | None = None)`
- `class ArchGetThreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetThreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetDynamicMemoryOp(memory_space: NnMemorySpaceAttr, result_type: Attribute | None = None)`
- `class ArchBarrierOp(scope: ArchScopeAttr, visibility: ArrayAttr[Attribute])`
- `class ArchLaunchOp(callee: str | Attribute, block: SSAValue | Operation, thread: SSAValue | Operation, subthread: SSAValue | Operation, shared_memory_size: SSAValue | Operation, args: Sequence[SSAValue | Operation] = ())`
- `ArchLaunchKernelOp: type[ArchLaunchOp] = ArchLaunchOp`
- `class Arch(Dialect)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dialect/arch.md`](../../spec/dialect/arch.md)
- `功能实现`：[`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py)
- 包级导出例外：[`kernel_gen/dialect/__init__.py`](../../kernel_gen/dialect/__init__.py)
- `test`：[`test/dialect/test_arch.py`](../../test/dialect/test_arch.py)

## 依赖

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：提供执行维度标量统一使用的 `!symbol.int<#symbol.expr<expr>>` 类型语义。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：提供 `NnMemoryType` 与 `NnMemorySpaceAttr` 的文本与校验规则。
- [`kernel_gen/dialect/__init__.py`](../../kernel_gen/dialect/__init__.py)：共享 `kernel_gen.dialect` 包入口；本 spec 只约束其中 `arch` 相关公开导出，`nn` 导出边界仍由各自 spec 单独约束。

## 目标

- 为 block/thread/subthread/shared_memory_size 四层硬件执行维度提供统一、可打印、可校验的 IR 查询接口。
- 为动态片上内存入口提供独立 op，避免其他方言重复定义“运行期动态内存句柄”的文本与 verifier 规则。
- 为 barrier 提供独立 op，固定同步范围与聚合可见域文本。
- 为后续实现提供最小可落地的 `parse/print`、类型约束、错误路径与测试清单。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `arch` dialect 只定义执行维度查询、动态内存入口、barrier 与启动描述；不定义网格调度策略、kernel body、memory copy 或张量算术。
- `arch.get_block_id`、`arch.get_block_num`、`arch.get_thread_id`、`arch.get_thread_num`、`arch.get_subthread_id`、`arch.get_subthread_num` 都是无 operand、单结果 op。
- 上述查询 op 的结果类型必须分别固定为 `!symbol.int<#symbol.expr<block_id>>`、`!symbol.int<#symbol.expr<block_num>>`、`!symbol.int<#symbol.expr<thread_id>>`、`!symbol.int<#symbol.expr<thread_num>>`、`!symbol.int<#symbol.expr<subthread_id>>`、`!symbol.int<#symbol.expr<subthread_num>>`，不得改写为 builtin `index`、普通整数或其他符号表达。
- `arch.get_dynamic_memory` 只描述“获取某个 memory space 对应的动态 memory 入口”；不负责容量求值、分配策略或布局推导。
- `arch.get_dynamic_memory` 的默认结果类型当前统一为一维 named-capacity 字节缓冲：`!nn.memory<[SM_SIZE], [1], i8, #nn.space<shared>>`、`!nn.memory<[LM_SIZE], [1], i8, #nn.space<local>>`、`!nn.memory<[TSM_SIZE], [1], i8, #nn.space<tsm>>`、`!nn.memory<[TLM1_SIZE], [1], i8, #nn.space<tlm1>>`、`!nn.memory<[TLM2_SIZE], [1], i8, #nn.space<tlm2>>`、`!nn.memory<[TLM3_SIZE], [1], i8, #nn.space<tlm3>>`。
- `arch.get_dynamic_memory` 对 `tsm/tlm1/tlm2/tlm3` 允许 pass 将 named-capacity shape 特化为正静态字节容量，例如 `!nn.memory<[2097152], [1], i8, #nn.space<tsm>>`；`shared/local` 仍只接受 named-capacity 结果类型。
- `arch.get_dynamic_memory` 的 `memory_space` 只允许 `shared`、`local`、`tsm`、`tlm1`、`tlm2`、`tlm3`；`global` 与旧 `tlm` 不属于动态片上内存入口范围，必须报错。
- `arch.barrier` 只描述同步请求；不负责数据搬运、事件管理或 target 私有副作用。
- `arch.barrier` 的 `scope` 只允许 `block/thread/subthread/global`，`visibility` 必须且只能包含 `#arch.visibility<tsm>` 与 `#arch.visibility<tlm>` 各一次。
- `arch.launch` 只描述一次 kernel 启动请求，不定义返回值、region、异步句柄或启动完成语义。
- `arch.launch` 的 `block`、`thread`、`subthread`、`shared_memory_size` operand 必须为 `!symbol.int<#symbol.expr<expr>>`，其中前三者表达正整数启动规模，`shared_memory_size` 表达非负共享内存规模；负值、零值与非整型 symbol 标量不属于合法公开语义。
- 本文件只约束公开 IR 形式与 verifier 边界；不承诺 host/runtime 如何消费这些 op。
- `kernel_gen/dialect/__init__.py` 属于共享包入口文件，是本 spec “每个 spec 原则上只对应一个源文件”的例外；本文件只定义该包入口中 `Arch`、`ArchGetBlockIdOp`、`ArchGetBlockNumOp`、`ArchGetThreadIdOp`、`ArchGetThreadNumOp`、`ArchGetSubthreadIdOp`、`ArchGetSubthreadNumOp`、`ArchGetDynamicMemoryOp`、`ArchLaunchOp` / `ArchLaunchKernelOp` 这些 `arch` 公开符号的导出边界，不延伸约束同文件中的 `nn` 导出。

### operation API 映射

对照 [`spec/operation/arch.md`](../../spec/operation/arch.md)，operation 层 helper 与 `arch dialect` op 的对应关系如下。

| operation API | dialect op | 说明 |
| --- | --- | --- |
| `get_block_id()` | `arch.get_block_id` | block 索引查询。 |
| `get_block_num()` | `arch.get_block_num` | block 数量查询。 |
| `get_thread_id()` | `arch.get_thread_id` | thread 索引查询。 |
| `get_thread_num()` | `arch.get_thread_num` | thread 数量查询。 |
| `get_subthread_id()` | `arch.get_subthread_id` | subthread 索引查询。 |
| `get_subthread_num()` | `arch.get_subthread_num` | subthread 数量查询。 |
| `get_dynamic_memory(space)` | `arch.get_dynamic_memory` | 动态片上内存入口。 |
| `barrier(visibility=[...], scope=...)` | `arch.barrier` | 同步请求。 |
| `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` | `arch.launch` | kernel 启动描述。 |

## API详细说明

### `class ArchScopeAttr(scope: StringAttr)`

- api：`class ArchScopeAttr(scope: StringAttr)`
- 参数：
  - `scope`：作用域标识，指定 barrier、注册、查找或名字分配的有效范围；类型 `StringAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchScopeAttr` 实例。
- 使用示例：

  ```python
  arch_scope_attr = ArchScopeAttr(scope=scope)
  ```
- 功能说明：定义 `ArchScopeAttr` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `ArchScopeAttr.from_name(name: str) -> ArchScopeAttr`

- api：`ArchScopeAttr.from_name(name: str) -> ArchScopeAttr`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchScopeAttr`。
- 使用示例：

  ```python
  arch_scope_attr = arch_scope_attr
  result = arch_scope_attr.from_name(name=name)
  ```
- 功能说明：执行 `from_name`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class ArchVisibilityAttr(visibility: StringAttr)`

- api：`class ArchVisibilityAttr(visibility: StringAttr)`
- 参数：
  - `visibility`：可见性标识，指定 barrier、符号或公开对象的可见范围；类型 `StringAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchVisibilityAttr` 实例。
- 使用示例：

  ```python
  arch_visibility_attr = ArchVisibilityAttr(visibility=visibility)
  ```
- 功能说明：定义 `ArchVisibilityAttr` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `ArchVisibilityAttr.from_name(name: str) -> ArchVisibilityAttr`

- api：`ArchVisibilityAttr.from_name(name: str) -> ArchVisibilityAttr`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchVisibilityAttr`。
- 使用示例：

  ```python
  arch_visibility_attr = arch_visibility_attr
  result = arch_visibility_attr.from_name(name=name)
  ```
- 功能说明：执行 `from_name`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class ArchGetBlockIdOp(result_type: Attribute | None = None)`

- api：`class ArchGetBlockIdOp(result_type: Attribute | None = None)`
- 参数：
  - `result_type`：类型对象或类型名称；类型 `Attribute | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchGetBlockIdOp` 实例。
- 使用示例：

  ```python
  arch_get_block_id_op = ArchGetBlockIdOp(result_type=None)
  ```
- 功能说明：定义 `ArchGetBlockIdOp` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ArchGetBlockNumOp(result_type: Attribute | None = None)`

- api：`class ArchGetBlockNumOp(result_type: Attribute | None = None)`
- 参数：
  - `result_type`：类型对象或类型名称；类型 `Attribute | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchGetBlockNumOp` 实例。
- 使用示例：

  ```python
  arch_get_block_num_op = ArchGetBlockNumOp(result_type=None)
  ```
- 功能说明：定义 `ArchGetBlockNumOp` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ArchGetThreadIdOp(result_type: Attribute | None = None)`

- api：`class ArchGetThreadIdOp(result_type: Attribute | None = None)`
- 参数：
  - `result_type`：类型对象或类型名称；类型 `Attribute | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchGetThreadIdOp` 实例。
- 使用示例：

  ```python
  arch_get_thread_id_op = ArchGetThreadIdOp(result_type=None)
  ```
- 功能说明：定义 `ArchGetThreadIdOp` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ArchGetThreadNumOp(result_type: Attribute | None = None)`

- api：`class ArchGetThreadNumOp(result_type: Attribute | None = None)`
- 参数：
  - `result_type`：类型对象或类型名称；类型 `Attribute | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchGetThreadNumOp` 实例。
- 使用示例：

  ```python
  arch_get_thread_num_op = ArchGetThreadNumOp(result_type=None)
  ```
- 功能说明：定义 `ArchGetThreadNumOp` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ArchGetSubthreadIdOp(result_type: Attribute | None = None)`

- api：`class ArchGetSubthreadIdOp(result_type: Attribute | None = None)`
- 参数：
  - `result_type`：类型对象或类型名称；类型 `Attribute | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchGetSubthreadIdOp` 实例。
- 使用示例：

  ```python
  arch_get_subthread_id_op = ArchGetSubthreadIdOp(result_type=None)
  ```
- 功能说明：定义 `ArchGetSubthreadIdOp` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ArchGetSubthreadNumOp(result_type: Attribute | None = None)`

- api：`class ArchGetSubthreadNumOp(result_type: Attribute | None = None)`
- 参数：
  - `result_type`：类型对象或类型名称；类型 `Attribute | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchGetSubthreadNumOp` 实例。
- 使用示例：

  ```python
  arch_get_subthread_num_op = ArchGetSubthreadNumOp(result_type=None)
  ```
- 功能说明：定义 `ArchGetSubthreadNumOp` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ArchGetDynamicMemoryOp(memory_space: NnMemorySpaceAttr, result_type: Attribute | None = None)`

- api：`class ArchGetDynamicMemoryOp(memory_space: NnMemorySpaceAttr, result_type: Attribute | None = None)`
- 参数：
  - `memory_space`：内存空间标识，定义输出或中间对象所在的公开 memory space；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `Attribute | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchGetDynamicMemoryOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
  from kernel_gen.dialect.nn import NnMemorySpaceAttr

  arch_get_dynamic_memory_op = ArchGetDynamicMemoryOp(
      memory_space=NnMemorySpaceAttr.from_name("shared"),
      result_type=None,
  )
  ```
- 功能说明：获取指定片上 memory space 的动态 backing memory 入口。
- 注意事项：`memory_space` 只允许 `shared/local/tsm/tlm1/tlm2/tlm3`；默认 `result_type=None` 时按 space 生成 named-capacity 一维 `i8` memory；显式 `result_type` 必须匹配同一 space、`[<CAPACITY>]` shape、`[1]` stride 与 `i8` element type；`tsm/tlm1/tlm2/tlm3` 的 `<CAPACITY>` 可为 named capacity 或正静态整数，`shared/local` 只接受 named capacity。

### `class ArchBarrierOp(scope: ArchScopeAttr, visibility: ArrayAttr[Attribute])`

- api：`class ArchBarrierOp(scope: ArchScopeAttr, visibility: ArrayAttr[Attribute])`
- 参数：
  - `scope`：作用域标识，指定 barrier、注册、查找或名字分配的有效范围；类型 `ArchScopeAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `visibility`：可见性标识，指定 barrier、符号或公开对象的可见范围；类型 `ArrayAttr[Attribute]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchBarrierOp` 实例。
- 使用示例：

  ```python
  arch_barrier_op = ArchBarrierOp(scope=scope, visibility=visibility)
  ```
- 功能说明：定义 `ArchBarrierOp` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ArchLaunchOp(callee: str | Attribute, block: SSAValue | Operation, thread: SSAValue | Operation, subthread: SSAValue | Operation, shared_memory_size: SSAValue | Operation, args: Sequence[SSAValue | Operation] = ())`

- api：`class ArchLaunchOp(callee: str | Attribute, block: SSAValue | Operation, thread: SSAValue | Operation, subthread: SSAValue | Operation, shared_memory_size: SSAValue | Operation, args: Sequence[SSAValue | Operation] = ())`
- 参数：
  - `callee`：被调用函数名或符号引用，指定 call/launch 类操作的目标；类型 `str | Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `block`：IR block 或结构化代码块，作为 rewrite、遍历或构建的作用对象；类型 `SSAValue | Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `thread`：`thread` 输入值，参与 `ArchLaunchOp` 的公开处理流程；类型 `SSAValue | Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `subthread`：`subthread` 输入值，参与 `ArchLaunchOp` 的公开处理流程；类型 `SSAValue | Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `shared_memory_size`：大小或容量值；类型 `SSAValue | Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `Sequence[SSAValue | Operation]`；默认值 `()`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArchLaunchOp` 实例。
- 使用示例：

  ```python
  arch_launch_op = ArchLaunchOp(callee=callee, block=block, thread=thread, subthread=subthread, shared_memory_size=shared_memory_size, args=args)
  ```
- 功能说明：定义 `ArchLaunchOp` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `ArchLaunchKernelOp: type[ArchLaunchOp] = ArchLaunchOp`

- api：`ArchLaunchKernelOp: type[ArchLaunchOp] = ArchLaunchOp`
- 参数：无。
- 返回值：`ArchLaunchOp` 类型对象。
- 使用示例：

  ```python
  from kernel_gen.dialect.arch import ArchLaunchKernelOp

  value = ArchLaunchKernelOp
  ```
- 功能说明：提供 `ArchLaunchOp` 的兼容公开别名。
- 注意事项：该别名只保持导入兼容，不定义独立 op、独立 verifier 或独立文本语法。

### `class Arch(Dialect)`

- api：`class Arch(Dialect)`
- 参数：无。
- 返回值：`Arch` 实例。
- 使用示例：

  ```python
  arch = Arch()
  ```
- 功能说明：定义 `Arch` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

## 测试

- 测试文件：`test/dialect/test_arch.py`
- 执行命令：`pytest -q test/dialect/test_arch.py`

### 测试目标

- 验证六个执行维度查询 op 的固定结果类型与无 operand 文本形式。
- 验证 `arch.get_dynamic_memory` 的 `space`、named-capacity 结果类型、parse/print 与 verifier 边界。
- 验证 `arch.launch` 的名称、operand 类型、静态非法规模与无结果约束。
- 验证 `arch` dialect 文本能够完成 parse/print round-trip。
- 验证 `kernel_gen.dialect` 包级入口已导出 `arch` 公共符号。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-ARCH-001 | 执行结果 | `arch.get_block_id` 固定返回 `!symbol.int<#symbol.expr<block_id>>` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_arch_get_block_id_result_type`。 | 命令返回码、输出、执行结果或状态变更体现“`arch.get_block_id` 固定返回 `!symbol.int<#symbol.expr<block_id>>`”场景。 | `test_arch_get_block_id_result_type` |
| TC-ARCH-002 | 执行结果 | `arch.get_block_num` 固定返回 `!symbol.int<#symbol.expr<block_num>>` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_arch_get_block_num_result_type`。 | 命令返回码、输出、执行结果或状态变更体现“`arch.get_block_num` 固定返回 `!symbol.int<#symbol.expr<block_num>>`”场景。 | `test_arch_get_block_num_result_type` |
| TC-ARCH-003 | 执行结果 | `arch.get_thread_id` 固定返回 `!symbol.int<#symbol.expr<thread_id>>` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_arch_get_thread_id_result_type`。 | 命令返回码、输出、执行结果或状态变更体现“`arch.get_thread_id` 固定返回 `!symbol.int<#symbol.expr<thread_id>>`”场景。 | `test_arch_get_thread_id_result_type` |
| TC-ARCH-004 | 执行结果 | `arch.get_thread_num` 固定返回 `!symbol.int<#symbol.expr<thread_num>>` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_arch_get_thread_num_result_type`。 | 命令返回码、输出、执行结果或状态变更体现“`arch.get_thread_num` 固定返回 `!symbol.int<#symbol.expr<thread_num>>`”场景。 | `test_arch_get_thread_num_result_type` |
| TC-ARCH-005 | 执行结果 | `arch.get_subthread_id` 固定返回 `!symbol.int<#symbol.expr<subthread_id>>` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_arch_get_subthread_id_result_type`。 | 命令返回码、输出、执行结果或状态变更体现“`arch.get_subthread_id` 固定返回 `!symbol.int<#symbol.expr<subthread_id>>`”场景。 | `test_arch_get_subthread_id_result_type` |
| TC-ARCH-006 | 执行结果 | `arch.get_subthread_num` 固定返回 `!symbol.int<#symbol.expr<subthread_num>>` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_arch_get_subthread_num_result_type`。 | 命令返回码、输出、执行结果或状态变更体现“`arch.get_subthread_num` 固定返回 `!symbol.int<#symbol.expr<subthread_num>>`”场景。 | `test_arch_get_subthread_num_result_type` |
| TC-ARCH-007 | 内存/DMA | `arch.get_dynamic_memory` 合法路径 | 准备 `shared/tlm1/tlm2/tlm3` 等公开 memory space。 | 运行 `test_arch_get_dynamic_memory_success`、`test_arch_get_dynamic_memory_supports_tlm123` 与 `test_arch_get_dynamic_memory_accepts_specialized_static_capacity`。 | verifier 接受合法 space，并打印对应 `SM_SIZE/TLM1_SIZE/TLM2_SIZE/TLM3_SIZE` named capacity；`tsm/tlm1/tlm2/tlm3` 也接受 target 特化后的正静态容量。 | `test_arch_get_dynamic_memory_success` / `test_arch_get_dynamic_memory_supports_tlm123` / `test_arch_get_dynamic_memory_accepts_specialized_static_capacity` |
| TC-ARCH-008 | 边界/异常 | `arch.get_dynamic_memory` 非法 `memory_space`/结果类型被拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_arch_get_dynamic_memory_verify_errors`。 | “`arch.get_dynamic_memory` 非法 `memory_space`/结果类型被拒绝”场景按公开错误语义失败或被拒绝。 | `test_arch_get_dynamic_memory_verify_errors` |
| TC-ARCH-009 | 公开入口 | `arch.launch` 合法路径 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_arch_launch_kernel_success`。 | 公开入口在“`arch.launch` 合法路径”场景下可导入、构造、注册或按名称发现。 | `test_arch_launch_kernel_success` |
| TC-ARCH-010 | 边界/异常 | `arch.launch` 拒绝空名称、非 `symbol.int` operand 与静态非法规模 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_arch_launch_kernel_verify_errors`。 | “`arch.launch` 拒绝空名称、非 `symbol.int` operand 与静态非法规模”场景按公开错误语义失败或被拒绝。 | `test_arch_launch_kernel_verify_errors` |
| TC-ARCH-011 | 解析/打印 | `arch` 方言 parse/print round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_arch_parse_print_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_arch_parse_print_round_trip` |
| TC-ARCH-012 | 公开入口 | `kernel_gen.dialect` 包级入口导出 `arch` 公共符号 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_arch_package_exports`。 | 公开入口在“`kernel_gen.dialect` 包级入口导出 `arch` 公共符号”场景下可导入、构造、注册或按名称发现。 | `test_arch_package_exports` |
