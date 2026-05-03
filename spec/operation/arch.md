# arch.md

## 功能简介

- 定义 operation 层 `arch` helper API，提供执行维度查询、动态片上内存入口、barrier 与 kernel 启动描述的高层调用语义。
- 该层面向 Python/DSL 调用侧，统一约束 `get_block_id/get_block_num/get_thread_id/get_thread_num/get_subthread_id/get_subthread_num/get_dynamic_memory/barrier/launch_kernel` 的入参与返回，不重复定义新的 dialect 语义。
- operation 层只描述对外 helper 约定；底层 IR 形态、parse/print 与 verifier 约束统一复用 [`spec/dialect/arch.md`](../../spec/dialect/arch.md)。

## API 列表

- `get_block_id() -> SymbolDim`
- `get_block_num() -> SymbolDim`
- `get_thread_id() -> SymbolDim`
- `get_thread_num() -> SymbolDim`
- `get_subthread_id() -> SymbolDim`
- `get_subthread_num() -> SymbolDim`
- `get_dynamic_memory(space: MemorySpace) -> Memory`
- `class BarrierVisibility()`
- `class BarrierScope()`
- `barrier(*, visibility: list[BarrierVisibility] | tuple[BarrierVisibility, ...], scope: BarrierScope) -> None`
- `launch_kernel[block: int | SymbolDim, thread: int | SymbolDim, subthread: int | SymbolDim, shared_memory_size: int | SymbolDim](callee: FunctionType, *args: KernelArgument) -> None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/operation/arch.md`](../../spec/operation/arch.md)
- `功能实现`：[`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
- `test`：[`test/operation/test_arch.py`](../../test/operation/test_arch.py)

## 依赖

- [`spec/dialect/arch.md`](../../spec/dialect/arch.md)：定义 `arch` 方言 op 的 IR 语义、固定结果类型与 verifier 约束。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：定义 `SymbolDim` 的公开语义，供执行维度 helper 返回与入参校验复用。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：定义 `Memory` / `MemorySpace` 的高层语义，供动态内存 helper 返回与空间映射复用。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：定义 `NumericType` / `Farmat`，供动态内存结果 dtype 与格式语义复用。
- [`spec/target/registry.md`](../../spec/target/registry.md)：定义 current target 支持性校验与硬件字段读取规则。
- [`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py)：operation helper 的唯一 dialect 映射目标。
- [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)：`SymbolDim` 运行时容器实现。
- [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)：`Memory` / `MemorySpace` 运行时容器实现。
- [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)：operation helper 所依赖的 target registry 查询实现。

## 目标

- 提供统一的 operation 层 `arch` helper 入口，使上层 Python/DSL 在不直接依赖 dialect op 类的前提下表达执行维度查询、动态片上内存入口、barrier 与 kernel 启动描述。
- 明确 operation helper 与 `arch dialect` 的一一映射关系，避免在 operation 层引入与方言层不一致的附加语义。
- 为后续实现任务明确 `kernel_gen/operation/arch.py` 与 `test/operation/test_arch.py` 的公开接口范围、错误边界与测试清单。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只约束 `kernel_gen/operation/arch.py` 的公开 helper 语义，不约束 `kernel_gen/operation/__init__.py` 的包级导出；若后续需要包级导出，必须由实现阶段或独立任务显式补齐。
- operation 层 `arch` helper 只负责描述高层调用语义，不负责真实硬件调度、线程绑定、异步执行、同步原语、kernel 完成状态或返回值消费。
- operation 层不得定义新的执行维度类型体系；执行维度查询 helper 的公开返回统一复用 `SymbolDim` 语义，对应 lowering 必须映射到 `arch dialect` 的固定 `!symbol.int<"...">` 结果类型。
- `get_block_id/get_block_num/get_thread_id/get_thread_num/get_subthread_id/get_subthread_num` 均为无参 helper，不接受 axis、rank 或其他附加配置。
- `get_dynamic_memory(space)` 只描述“获取某个片上空间的运行期动态内存入口”；不负责容量估算、布局推导、分配策略、初始化填充或跨空间拷贝。
- `get_dynamic_memory(space)` 的公开结果语义必须收敛为一维字节缓冲：当 target registry 提供对应硬件 size 时逻辑 shape 为 `[size]`，缺失时回退为 `[?]`；stride 固定为 `[1]`、dtype 固定为 `NumericType.Int8`、space 与输入一致；operation 层不得额外承诺容量、对齐或多维布局。
- `get_dynamic_memory(space)` 只允许片上空间 `MemorySpace.SM`、`MemorySpace.LM`、`MemorySpace.TSM`、`MemorySpace.TLM1`、`MemorySpace.TLM2`、`MemorySpace.TLM3`；`MemorySpace.GM` 不属于动态片上内存入口范围，必须报错。
- `BarrierVisibility` 的公开聚合可见域固定为 `TSM` 与 `TLM`：其中 `BarrierVisibility.TLM` 只表示 barrier 可见域，固定覆盖真实内存空间 `MemorySpace.TLM1/TLM2/TLM3`，不得回退为旧的单一聚合 TLM memory space 写法。
- `barrier(*, visibility, scope)` 只描述一次同步请求，不返回新的 `Memory`、`SymbolDim`、句柄或状态对象；公开返回值固定为 `None`。
- `barrier` 采用关键字参数调用，`visibility/scope` 均为必填；`visibility` 只允许 `list[BarrierVisibility]` 或 `tuple[BarrierVisibility, ...]`，且必须且只能包含 `TSM/TLM` 各一次；`scope` 只允许 `BarrierScope.BLOCK/THREAD/SUBTHREAD/GLOBAL`。
- `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 只描述一次启动请求，不返回新的 `Memory`、`SymbolDim` 或句柄对象；公开返回值固定为 `None`。
- `launch_kernel` 的公开调用形态固定为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`：四个 launch 字段位于下标，调用参数顺序固定为 `callee -> *args`。
- `launch_kernel` 仅允许关键字参数名 `callee/block/thread/subthread`；缺失前四个必填参数或传入未知关键字参数属于调用边界错误，必须抛出 `KernelCodeError`。
- `launch_kernel[...]` 的 `callee` 只允许 Python 函数对象；不得接受字符串名、其他 callable、`Memory`、`SymbolDim` 或自由对象。
- `launch_kernel[...]` 的 `block/thread/subthread` 只允许 `int` 或 `SymbolDim`，且不得接受 `bool`；若输入为静态整数，必须满足 `> 0`；operation 层不得接受浮点、`Memory`、列表或其他运行时对象。
- operation 层与 dialect 层采用一一映射：`get_*` helper 分别映射到对应 `arch.get_*` op，`get_dynamic_memory` 映射到 `arch.get_dynamic_memory`，`barrier` 映射到 `arch.barrier`，`launch_kernel` 的支持性校验与 lowering 语义固定对应 `arch.launch`；不得通过其他 dialect 或 builtin op 绕过 `arch dialect`，也不得回退旧 launch op 命名。
- 当 target registry 设置了 current target 时，所有 `arch` helper 在调用前都必须执行支持性校验；若当前 target 不支持对应 `arch.*` op，必须抛出 `KernelCodeError`，且错误信息应包含 op 名与 target 名。
- `get_block_num/get_thread_num/get_subthread_num` 在 target registry 提供对应硬件值时必须优先返回静态值；缺失时回退为各自 `SymbolDim("<name>")` 语义。
- `get_dynamic_memory(space)` 在 target registry 提供对应 `*_memory_size` 时必须优先使用静态 size；缺失时回退为动态 `[?]`。

## API详细说明

### `get_block_id() -> SymbolDim`

- api：`get_block_id() -> SymbolDim`
- 参数：无。
- 返回值：`SymbolDim`，公开值为 `"block_id"`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import get_block_id

  bid = get_block_id()
  assert bid.get_value() == "block_id"
  ```
- 功能说明：返回当前 block 的执行索引高层语义。
- 注意事项：不接受 axis、device、rank 或其他附加参数；lowering 后必须一一映射到 `arch.get_block_id`；当设置 current target 时必须通过 target registry 校验 `arch.get_block_id` 支持性，不支持时抛出 `KernelCodeError`。

### `get_block_num() -> SymbolDim`

- api：`get_block_num() -> SymbolDim`
- 参数：无。
- 返回值：`SymbolDim`，硬件值可用时承载静态 block 数量，缺失时公开值为 `"block_num"`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import get_block_num

  bnum = get_block_num()
  ```
- 功能说明：返回当前 kernel 启动配置中的 block 数量高层语义。
- 注意事项：不接受额外配置参数；target registry 提供硬件 `block_num` 时必须优先返回静态值，缺失时回退 `SymbolDim("block_num")`；lowering 后必须一一映射到 `arch.get_block_num`。

### `get_thread_id() -> SymbolDim`

- api：`get_thread_id() -> SymbolDim`
- 参数：无。
- 返回值：`SymbolDim`，公开值为 `"thread_id"`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import get_thread_id

  tid = get_thread_id()
  assert tid.get_value() == "thread_id"
  ```
- 功能说明：返回当前 block 内 thread 执行索引的高层语义。
- 注意事项：不接受 axis、warp 或其他附加参数；lowering 后必须一一映射到 `arch.get_thread_id`；当设置 current target 时必须通过 target registry 校验 `arch.get_thread_id` 支持性，不支持时抛出 `KernelCodeError`。

### `get_thread_num() -> SymbolDim`

- api：`get_thread_num() -> SymbolDim`
- 参数：无。
- 返回值：`SymbolDim`，硬件值可用时承载静态 thread 数量，缺失时公开值为 `"thread_num"`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import get_thread_num

  tnum = get_thread_num()
  ```
- 功能说明：返回当前 block 内 thread 数量的高层语义。
- 注意事项：不接受额外配置参数；target registry 提供硬件 `thread_num` 时必须优先返回静态值，缺失时回退 `SymbolDim("thread_num")`；lowering 后必须一一映射到 `arch.get_thread_num`。

### `get_subthread_id() -> SymbolDim`

- api：`get_subthread_id() -> SymbolDim`
- 参数：无。
- 返回值：`SymbolDim`，公开值为 `"subthread_id"`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import get_subthread_id

  stid = get_subthread_id()
  assert stid.get_value() == "subthread_id"
  ```
- 功能说明：返回当前 thread 内 subthread 执行索引的高层语义。
- 注意事项：不接受 lane、rank 或其他附加参数；lowering 后必须一一映射到 `arch.get_subthread_id`；当设置 current target 时必须通过 target registry 校验 `arch.get_subthread_id` 支持性，不支持时抛出 `KernelCodeError`。

### `get_subthread_num() -> SymbolDim`

- api：`get_subthread_num() -> SymbolDim`
- 参数：无。
- 返回值：`SymbolDim`，硬件值可用时承载静态 subthread 数量，缺失时公开值为 `"subthread_num"`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import get_subthread_num

  stnum = get_subthread_num()
  ```
- 功能说明：返回当前 thread 内 subthread 数量的高层语义。
- 注意事项：不接受额外配置参数；target registry 提供硬件 `subthread_num` 时必须优先返回静态值，缺失时回退 `SymbolDim("subthread_num")`；lowering 后必须一一映射到 `arch.get_subthread_num`。

### `get_dynamic_memory(space: MemorySpace) -> Memory`

- api：`get_dynamic_memory(space: MemorySpace) -> Memory`
- 参数：
  - `space`：动态片上内存所在空间；类型 `MemorySpace`；无默认值，调用方必须显式提供；只允许 `MemorySpace.SM`、`MemorySpace.LM`、`MemorySpace.TSM`、`MemorySpace.TLM1`、`MemorySpace.TLM2`、`MemorySpace.TLM3`；不允许 `None`、字符串、`MemorySpace.GM` 或其他对象，非法值必须抛出 `KernelCodeError`。
- 返回值：`Memory`，一维字节缓冲；`stride=[1]`，`dtype=NumericType.Int8`，`space` 与输入一致，`shape` 在 target registry 提供 `*_memory_size` 时为 `[size]`，缺失时回退为动态符号大小。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import get_dynamic_memory
  from kernel_gen.symbol_variable.memory import MemorySpace

  smem = get_dynamic_memory(MemorySpace.SM)
  ```
- 功能说明：返回指定片上空间的运行期动态内存入口高层语义。
- 注意事项：本接口不承诺容量、对齐或多维 view 语义；`MemorySpace.TLM1/TLM2/TLM3` 是真实动态片上空间，barrier 聚合可见域应使用 `BarrierVisibility.TLM`；lowering 后必须一一映射到 `arch.get_dynamic_memory`。

### `class BarrierVisibility()`

- api：`class BarrierVisibility()`
- 参数：无公开构造参数；调用方通过稳定枚举成员 `BarrierVisibility.TSM` 与 `BarrierVisibility.TLM` 使用。
- 返回值：`BarrierVisibility` 枚举类型；成员类型为 `BarrierVisibility`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import BarrierVisibility

  visibility = BarrierVisibility.TLM
  ```
- 功能说明：定义 `barrier(visibility, scope)` 的公开聚合可见域。
- 注意事项：稳定成员固定为 `TSM` 与 `TLM`；`BarrierVisibility.TLM` 表示聚合可见域，覆盖真实 `MemorySpace.TLM1/TLM2/TLM3`，不得作为 `get_dynamic_memory(space)` 的真实内存空间输入。

### `class BarrierScope()`

- api：`class BarrierScope()`
- 参数：无公开构造参数；调用方通过稳定枚举成员 `BarrierScope.BLOCK`、`BarrierScope.THREAD`、`BarrierScope.SUBTHREAD` 与 `BarrierScope.GLOBAL` 使用。
- 返回值：`BarrierScope` 枚举类型；成员类型为 `BarrierScope`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import BarrierScope

  scope = BarrierScope.THREAD
  ```
- 功能说明：定义 `barrier(visibility, scope)` 的公开同步范围。
- 注意事项：稳定成员固定为 `BLOCK`、`THREAD`、`SUBTHREAD` 与 `GLOBAL`；具体 target 若不支持某个 scope，必须通过 target registry 显式失败，不得静默降级。

### `barrier(*, visibility: list[BarrierVisibility] | tuple[BarrierVisibility, ...], scope: BarrierScope) -> None`

- api：`barrier(*, visibility: list[BarrierVisibility] | tuple[BarrierVisibility, ...], scope: BarrierScope) -> None`
- 参数：
  - `visibility`：需要保证可见性的聚合可见域列表；类型 `list[BarrierVisibility] | tuple[BarrierVisibility, ...]`；无默认值，调用方必须显式提供；必须且只能包含 `BarrierVisibility.TSM` 与 `BarrierVisibility.TLM` 各一次；不允许 `None`、空列表、重复项或非 `BarrierVisibility` 元素。
  - `scope`：同步范围；类型 `BarrierScope`；无默认值，调用方必须显式提供；不允许 `None` 或非 `BarrierScope`。
- 返回值：`None`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier

  barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)
  ```
- 功能说明：记录一次 barrier 同步请求的高层语义。
- 注意事项：`visibility` 与 `scope` 都是必填关键字参数，不接受无参调用或位置参数；本接口不负责数据搬运、事件管理或 target 私有副作用；当设置 current target 时必须通过 target registry 校验 `arch.barrier` 支持性，不支持时抛出 `KernelCodeError`。

### `launch_kernel[block: int | SymbolDim, thread: int | SymbolDim, subthread: int | SymbolDim, shared_memory_size: int | SymbolDim](callee: FunctionType, *args: KernelArgument) -> None`

- api：`launch_kernel[block: int | SymbolDim, thread: int | SymbolDim, subthread: int | SymbolDim, shared_memory_size: int | SymbolDim](callee: FunctionType, *args: KernelArgument) -> None`
- 参数：
  - `block`：下标字段 `#1`，block 规模；类型 `int | SymbolDim`；无默认值；不允许 `bool`、`None`、浮点、`Memory`、列表或其他对象；静态 `int` 必须 `> 0`。
  - `thread`：下标字段 `#2`，thread 规模；类型 `int | SymbolDim`；无默认值；不允许 `bool`、`None`、浮点、`Memory`、列表或其他对象；静态 `int` 必须 `> 0`。
  - `subthread`：下标字段 `#3`，subthread 规模；类型 `int | SymbolDim`；无默认值；不允许 `bool`、`None`、浮点、`Memory`、列表或其他对象；静态 `int` 必须 `> 0`。
  - `shared_memory_size`：下标字段 `#4`，共享内存规模；类型 `int | SymbolDim`；无默认值；不允许 `bool`、`None`、浮点、`Memory`、列表或其他对象；静态 `int` 必须 `>= 0`。
  - `callee`：调用参数 `#1`，Python 函数对象；类型 `FunctionType`；无默认值；不允许字符串名、其他 callable、`Memory`、`SymbolDim` 或自由对象。
  - `args`：尾部 kernel 实参；类型 `tuple[KernelArgument, ...]`；默认空元组；按原顺序透传给 `callee`，元素允许 `Memory | SymbolDim | int | float | str | bool | None`。
- 返回值：`None`。
- 使用示例：

  ```python
  from kernel_gen.operation.arch import launch_kernel
  from kernel_gen.symbol_variable.symbol_dim import SymbolDim

  def my_kernel(lhs: str, rhs: str, out: str) -> None:
      return None

  launch_kernel[SymbolDim("GRID_X"), 128, 4, 0](my_kernel, "lhs", "rhs", "out")
  ```
- 功能说明：记录一次 kernel 启动请求的高层语义，包含函数对象、四层启动规模与尾部 kernel 实参。
- 注意事项：四个 launch 字段必须全部在下标中给出；下标字段个数不是 `4`、或在公开入口上传入未知关键字参数时，必须抛出 `KernelCodeError`；本接口不负责真正执行设备 kernel，也不返回事件、句柄或状态值；当 `callee` 在 Python 中被调用时，`get_block_num/get_thread_num/get_subthread_num` 必须优先暴露本次 launch 的 extent 语义；当设置 current target 时必须通过 target registry 校验 `arch.launch` 支持性，不支持时抛出 `KernelCodeError`。

## 测试

- 测试文件：`test/operation/test_arch.py`
- 执行命令：
  - `pytest -q test/operation/test_arch.py`
  - `pytest -q test/operation/test_arch.py -k "barrier or launch_kernel"`

### 测试目标

- 验证 `spec/operation/arch.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开执行入口的返回值、输出或状态变化符合预期。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证 Memory/DMA 参数、布局、搬运或 verifier 行为。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-OPERATION-ARCH-001 | 执行结果 | `get_block_id()` 返回 `SymbolDim` 风格 block 索引语义，并映射 `TC-ARCH-001`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `TC-OP-ARCH-001`。 | 命令返回码、输出、执行结果或状态变更体现“`get_block_id()` 返回 `SymbolDim` 风格 block 索引语义，并映射 `TC-ARCH-001`。”场景。 | `TC-OP-ARCH-001` |
| TC-OPERATION-ARCH-002 | 执行结果 | `get_block_num()` 返回 `SymbolDim` 风格 block 数量语义，并映射 `TC-ARCH-002`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `TC-OP-ARCH-002`。 | 命令返回码、输出、执行结果或状态变更体现“`get_block_num()` 返回 `SymbolDim` 风格 block 数量语义，并映射 `TC-ARCH-002`。”场景。 | `TC-OP-ARCH-002` |
| TC-OPERATION-ARCH-003 | 执行结果 | `get_thread_id()` 返回 `SymbolDim` 风格 thread 索引语义，并映射 `TC-ARCH-003`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `TC-OP-ARCH-003`。 | 命令返回码、输出、执行结果或状态变更体现“`get_thread_id()` 返回 `SymbolDim` 风格 thread 索引语义，并映射 `TC-ARCH-003`。”场景。 | `TC-OP-ARCH-003` |
| TC-OPERATION-ARCH-004 | 执行结果 | `get_thread_num()` 返回 `SymbolDim` 风格 thread 数量语义，并映射 `TC-ARCH-004`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `TC-OP-ARCH-004`。 | 命令返回码、输出、执行结果或状态变更体现“`get_thread_num()` 返回 `SymbolDim` 风格 thread 数量语义，并映射 `TC-ARCH-004`。”场景。 | `TC-OP-ARCH-004` |
| TC-OPERATION-ARCH-005 | 执行结果 | `get_subthread_id()` 返回 `SymbolDim` 风格 subthread 索引语义，并映射 `TC-ARCH-005`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `TC-OP-ARCH-005`。 | 命令返回码、输出、执行结果或状态变更体现“`get_subthread_id()` 返回 `SymbolDim` 风格 subthread 索引语义，并映射 `TC-ARCH-005`。”场景。 | `TC-OP-ARCH-005` |
| TC-OPERATION-ARCH-006 | 执行结果 | `get_subthread_num()` 返回 `SymbolDim` 风格 subthread 数量语义，并映射 `TC-ARCH-006`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `TC-OP-ARCH-006`。 | 命令返回码、输出、执行结果或状态变更体现“`get_subthread_num()` 返回 `SymbolDim` 风格 subthread 数量语义，并映射 `TC-ARCH-006`。”场景。 | `TC-OP-ARCH-006` |
| TC-OPERATION-ARCH-007 | 执行结果 | `get_dynamic_memory(space)` 在 `SM/LM/TSM/TLM1/TLM2/TLM3` 六类片上空间都返回 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8` 的一维动态内存语义，并映射 `TC-ARCH-007`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `TC-OP-ARCH-007`。 | 命令返回码、输出、执行结果或状态变更体现“`get_dynamic_memory(space)` 在 `SM/LM/TSM/TLM1/TLM2/TLM3` 六类片上空间都返回 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8` 的一维动态内存语义，并映射 `TC-ARCH-007`。”场景。 | `TC-OP-ARCH-007` |
| TC-OPERATION-ARCH-008 | 边界/异常 | `get_dynamic_memory(...)` 对非法空间或非法类型报错，并覆盖 `MemorySpace.GM` 错误路径；对应 `TC-ARCH-008` 的方言边界。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-OP-ARCH-008`。 | “`get_dynamic_memory(...)` 对非法空间或非法类型报错，并覆盖 `MemorySpace.GM` 错误路径；对应 `TC-ARCH-008` 的方言边界。”场景按公开错误语义失败或被拒绝。 | `TC-OP-ARCH-008` |
| TC-OPERATION-ARCH-009 | 执行结果 | `barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=...)` 接受合法聚合可见域与公开 scope 并返回 `None`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `TC-OP-ARCH-009`。 | 命令返回码、输出、执行结果或状态变更体现“`barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=...)` 接受合法聚合可见域与公开 scope 并返回 `None`。”场景。 | `TC-OP-ARCH-009` |
| TC-OPERATION-ARCH-010 | 边界/异常 | `barrier(...)` 对缺参、空列表、重复 `visibility`、错误元素类型与非法 `scope` 报错。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-OP-ARCH-010`。 | “`barrier(...)` 对缺参、空列表、重复 `visibility`、错误元素类型与非法 `scope` 报错。”场景按公开错误语义失败或被拒绝。 | `TC-OP-ARCH-010` |
| TC-OPERATION-ARCH-011 | 内存/DMA | `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 接受合法 `function/int\ | SymbolDim` 输入与尾部 kernel 参数，并在 launched body 内暴露本次 launch extent。 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `TC-OP-ARCH-011`。 | 内存类型、布局、搬运结果或 verifier 行为与场景描述一致。 |
| TC-OPERATION-ARCH-012 | 边界/异常 | `launch_kernel[...]` 对字符串或非函数 `callee`、非法类型与静态 `<= 0` 的规模输入报错。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-OP-ARCH-012`。 | “`launch_kernel[...]` 对字符串或非函数 `callee`、非法类型与静态 `<= 0` 的规模输入报错。”场景按公开错误语义失败或被拒绝。 | `TC-OP-ARCH-012` |
| TC-OPERATION-ARCH-013 | 边界/异常 | `launch_kernel` 的公开入口固定为四个下标字段加 `callee, *args`；缺字段、未知关键字或把 launch 字段写进调用参数都必须在调用边界报 `KernelCodeError`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-OP-ARCH-013`。 | “`launch_kernel` 的公开入口固定为四个下标字段加 `callee, *args`；缺字段、未知关键字或把 launch 字段写进调用参数都必须在调用边界报 `KernelCodeError`。”场景按公开错误语义失败或被拒绝。 | `TC-OP-ARCH-013` |
| TC-OPERATION-ARCH-014 | 公开入口 | `launch_kernel[...]` 的公开语义、示例与错误路径不得回退为旧直调用写法。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-OP-ARCH-014`。 | 公开入口在“`launch_kernel[...]` 的公开语义、示例与错误路径不得回退为旧直调用写法。”场景下可导入、构造、注册或按名称发现。 | `TC-OP-ARCH-014` |
| TC-OPERATION-ARCH-015 | 公开入口 | target registry 提供硬件值时，launch 外的 `get_block_num()` / `get_thread_num()` / `get_subthread_num()` / `get_dynamic_memory()` 必须优先使用硬件值；launched body 内则优先暴露本次 launch extent。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-OP-ARCH-015`。 | 公开入口在“target registry 提供硬件值时，launch 外的 `get_block_num()` / `get_thread_num()` / `get_subthread_num()` / `get_dynamic_memory()` 必须优先使用硬件值；launched body 内则优先暴露本次 launch extent。”场景下可导入、构造、注册或按名称发现。 | `TC-OP-ARCH-015` |
| TC-OPERATION-ARCH-016 | 边界/异常 | 当当前 target 不支持某个 `arch.*` op 时，对应 helper 的 target registry 支持性校验必须抛出 `KernelCodeError` 并包含 op 名称；本条覆盖 `get_block_num()` / `get_thread_num()` / `get_subthread_num()` / `get_dynamic_memory()` / `barrier()` / `launch_kernel()` 的错误路径。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-OP-ARCH-016`。 | “当当前 target 不支持某个 `arch.*` op 时，对应 helper 的 target registry 支持性校验必须抛出 `KernelCodeError` 并包含 op 名称；本条覆盖 `get_block_num()` / `get_thread_num()` / `get_subthread_num()` / `get_dynamic_memory()` / `barrier()` / `launch_kernel()` 的错误路径。”场景按公开错误语义失败或被拒绝。 | `TC-OP-ARCH-016` |
