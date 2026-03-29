# arch.md

## 功能简介

- 定义 operation 层 `arch` helper API，提供执行维度查询、动态片上内存入口与 kernel 启动描述的高层调用语义。
- 该层面向 Python/DSL 调用侧，统一约束 `get_block_id/get_block_num/get_thread_id/get_thread_num/get_subthread_id/get_subthread_num/get_dynamic_memory/launch_kernel` 的入参与返回，不重复定义新的 dialect 语义。
- operation 层只描述对外 helper 约定；底层 IR 形态、parse/print 与 verifier 约束统一复用 [`spec/dialect/arch.md`](../../spec/dialect/arch.md)。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/operation/arch.md`](../../spec/operation/arch.md)
- `功能实现`：[`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
- `test`：[`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)

## 依赖

- [`spec/dialect/arch.md`](../../spec/dialect/arch.md)：定义 `arch` 方言 op 的 IR 语义、固定结果类型与 verifier 约束。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：定义 `SymbolDim` 的公开语义，供执行维度 helper 返回与入参校验复用。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：定义 `Memory` / `MemorySpace` 的高层语义，供动态内存 helper 返回与空间映射复用。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：定义 `NumericType` / `Farmat`，供动态内存结果 dtype 与格式语义复用。
- [`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py)：operation helper 的唯一 dialect 映射目标。
- [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)：`SymbolDim` 运行时容器实现。
- [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)：`Memory` / `MemorySpace` 运行时容器实现。

## 目标

- 提供统一的 operation 层 `arch` helper 入口，使上层 Python/DSL 在不直接依赖 dialect op 类的前提下表达执行维度查询、动态片上内存入口与 kernel 启动描述。
- 明确 operation helper 与 `arch dialect` 的一一映射关系，避免在 operation 层引入与方言层不一致的附加语义。
- 为后续实现任务明确 `kernel_gen/operation/arch.py` 与 `test/operation/test_operation_arch.py` 的公开接口范围、错误边界与测试清单。

## 限制与边界

- 本文件只约束 `kernel_gen/operation/arch.py` 的公开 helper 语义，不约束 `kernel_gen/operation/__init__.py` 的包级导出；若后续需要包级导出，必须由实现阶段或独立任务显式补齐。
- operation 层 `arch` helper 只负责描述高层调用语义，不负责真实硬件调度、线程绑定、异步执行、同步原语、kernel 完成状态或返回值消费。
- operation 层不得定义新的执行维度类型体系；执行维度查询 helper 的公开返回统一复用 `SymbolDim` 语义，对应 lowering 必须映射到 `arch dialect` 的固定 `!symbol.int<"...">` 结果类型。
- `get_block_id/get_block_num/get_thread_id/get_thread_num/get_subthread_id/get_subthread_num` 均为无参 helper，不接受 axis、rank 或其他附加配置。
- `get_dynamic_memory(space)` 只描述“获取某个片上空间的运行期动态内存入口”；不负责容量估算、布局推导、分配策略、初始化填充或跨空间拷贝。
- `get_dynamic_memory(space)` 的公开结果语义必须收敛为一维动态字节缓冲：逻辑 shape 为 `[?]`、stride 为 `[1]`、dtype 为 `NumericType.Int8`、space 与输入一致；operation 层不得额外承诺容量、对齐或多维布局。
- `get_dynamic_memory(space)` 只允许片上空间 `MemorySpace.SM`、`MemorySpace.LM`、`MemorySpace.TSM`、`MemorySpace.TLM`；`MemorySpace.GM` 不属于动态片上内存入口范围，必须报错。
- `launch_kernel(name, block, thread, subthread)` 只描述一次启动请求，不返回新的 `Memory`、`SymbolDim` 或句柄对象；公开返回值固定为 `None`。
- `launch_kernel` 调用签名固定为 `launch_kernel(name, block, thread, subthread)`：参数顺序必须为 `name -> block -> thread -> subthread`，四个参数均为必填，不提供可选参数与默认值。
- `launch_kernel` 仅允许参数名 `name/block/thread/subthread`；缺失参数、额外位置参数或未知关键字参数属于调用边界错误，必须抛出 `TypeError`。
- `launch_kernel(...)` 的 `block/thread/subthread` 只允许 `int` 或 `SymbolDim`；若输入为静态整数，必须满足 `> 0`；operation 层不得接受浮点、`Memory`、列表或其他运行时对象。
- operation 层与 dialect 层采用一一映射：`get_*` helper 分别映射到对应 `arch.get_*` op，`get_dynamic_memory` 映射到 `arch.get_dynamic_memory`，`launch_kernel` 映射到 `arch.launch_kernel`；不得通过其他 dialect 或 builtin op 绕过 `arch dialect`。

## 公开接口

### `get_block_id()`

功能说明：

- 返回当前 block 的执行索引高层语义。
- lowering 后必须一一映射到 `arch.get_block_id`。

参数说明：

- 无参数。

使用示例：

```python
bid = get_block_id()
```

注意事项：

- operation 层返回值语义应表现为 `SymbolDim` 风格的执行维度标量，不得退化为 Python `int` 常量或其他标量封装。
- 公开 helper 不接受 axis、device 或 rank 参数。

返回与限制：

- 返回类型：`SymbolDim`
- 限制：lowering 后结果语义必须固定对应 `!symbol.int<"block_id">`。

### `get_block_num()`

功能说明：

- 返回当前 kernel 启动配置中的 block 数量高层语义。
- lowering 后必须一一映射到 `arch.get_block_num`。

参数说明：

- 无参数。

使用示例：

```python
bnum = get_block_num()
```

注意事项：

- operation 层返回值语义应表现为 `SymbolDim` 风格标量。
- 不接受额外配置参数。

返回与限制：

- 返回类型：`SymbolDim`
- 限制：lowering 后结果语义必须固定对应 `!symbol.int<"block_num">`。

### `get_thread_id()`

功能说明：

- 返回当前 block 内 thread 执行索引的高层语义。
- lowering 后必须一一映射到 `arch.get_thread_id`。

参数说明：

- 无参数。

使用示例：

```python
tid = get_thread_id()
```

注意事项：

- operation 层返回值语义应表现为 `SymbolDim` 风格标量。
- 不接受 axis、warp 或其他附加参数。

返回与限制：

- 返回类型：`SymbolDim`
- 限制：lowering 后结果语义必须固定对应 `!symbol.int<"thread_id">`。

### `get_thread_num()`

功能说明：

- 返回当前 block 内 thread 数量的高层语义。
- lowering 后必须一一映射到 `arch.get_thread_num`。

参数说明：

- 无参数。

使用示例：

```python
tnum = get_thread_num()
```

注意事项：

- operation 层返回值语义应表现为 `SymbolDim` 风格标量。
- 不接受额外配置参数。

返回与限制：

- 返回类型：`SymbolDim`
- 限制：lowering 后结果语义必须固定对应 `!symbol.int<"thread_num">`。

### `get_subthread_id()`

功能说明：

- 返回当前 thread 内 subthread 执行索引的高层语义。
- lowering 后必须一一映射到 `arch.get_subthread_id`。

参数说明：

- 无参数。

使用示例：

```python
stid = get_subthread_id()
```

注意事项：

- operation 层返回值语义应表现为 `SymbolDim` 风格标量。
- 不接受 lane、rank 或其他附加参数。

返回与限制：

- 返回类型：`SymbolDim`
- 限制：lowering 后结果语义必须固定对应 `!symbol.int<"subthread_id">`。

### `get_subthread_num()`

功能说明：

- 返回当前 thread 内 subthread 数量的高层语义。
- lowering 后必须一一映射到 `arch.get_subthread_num`。

参数说明：

- 无参数。

使用示例：

```python
stnum = get_subthread_num()
```

注意事项：

- operation 层返回值语义应表现为 `SymbolDim` 风格标量。
- 不接受额外配置参数。

返回与限制：

- 返回类型：`SymbolDim`
- 限制：lowering 后结果语义必须固定对应 `!symbol.int<"subthread_num">`。

### `get_dynamic_memory(space)`

功能说明：

- 返回指定片上空间的运行期动态内存入口高层语义。
- lowering 后必须一一映射到 `arch.get_dynamic_memory`。

参数说明：

- `space (MemorySpace)`：目标片上空间，只允许 `MemorySpace.SM`、`MemorySpace.LM`、`MemorySpace.TSM`、`MemorySpace.TLM`。

使用示例：

```python
from kernel_gen.symbol_variable.memory import MemorySpace

smem = get_dynamic_memory(MemorySpace.SM)
```

注意事项：

- 输入若不是 `MemorySpace`，必须抛出 `TypeError`。
- 输入若为 `MemorySpace.GM`，必须抛出 `ValueError`。
- 返回结果的公开语义必须是 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8`、`space=<输入空间>` 的一维动态字节缓冲。
- operation 层不得公开承诺容量、对齐或多维 view 语义；这些约束由后续 DMA/view helper 单独承担。

返回与限制：

- 返回类型：`Memory`
- 限制：lowering 后结果必须对应 `!nn.memory<[?], [1], i8, #nn.space<space>>`，其中 `space` 与输入映射一致。

### `launch_kernel(name, block, thread, subthread)`

功能说明：

- 记录一次 kernel 启动请求的高层语义，包含 kernel 名称与 block/thread/subthread 三层执行规模。
- lowering 后必须一一映射到 `arch.launch_kernel`。

参数说明：

- 参数列表与顺序：`(name, block, thread, subthread)`。
- `name (str)`：必填，参数序号 `#1`；kernel 名称，必须为非空字符串；默认值：无。
- `block (int | SymbolDim)`：必填，参数序号 `#2`；block 规模；默认值：无。
- `thread (int | SymbolDim)`：必填，参数序号 `#3`；thread 规模；默认值：无。
- `subthread (int | SymbolDim)`：必填，参数序号 `#4`；subthread 规模；默认值：无。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

launch_kernel("my_kernel", SymbolDim("GRID_X"), 128, 4)
```

注意事项：

- 四个参数全部为必填参数，且不定义可选参数与默认值。
- 允许按关键字调用（如 `launch_kernel(name="k", block=1, thread=1, subthread=1)`），但关键字名必须是 `name/block/thread/subthread`。
- 调用边界错误（缺失任一必填参数、传入额外位置参数、传入未知关键字参数）必须抛出 `TypeError`，并在进入语义校验前失败。
- `name` 为空字符串时必须抛出 `ValueError`。
- `block/thread/subthread` 若不是 `int` 或 `SymbolDim`，必须抛出 `TypeError`。
- 当 `block/thread/subthread` 为静态整数时，必须要求其大于 `0`；`0` 或负值必须抛出 `ValueError`。
- 当输入为 `SymbolDim` 时，operation 层只保留符号语义，不要求在 Python 运行期求值。
- operation 层 helper 只描述启动请求，不负责真正执行 kernel，也不返回事件、句柄或状态值。

返回与限制：

- 返回类型：`None`
- 限制：lowering 后三个规模 operand 必须保持 `!symbol.int<"expr">` 语义，不得退化为 builtin `index` 或普通整数类型。

## 测试

- 测试文件：[`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)
- 执行命令：`pytest -q test/operation/test_operation_arch.py`
- 验收命令（launch_kernel 参数规范）：`pytest -q test/operation/test_operation_arch.py -k launch_kernel`
- 测试目标：
  - 验证六个执行维度查询 helper 的公开返回语义均为 `SymbolDim` 风格标量，并与 `arch dialect` 的固定结果语义一一对应。
  - 验证 `get_dynamic_memory(space)` 只接受允许的片上空间，且返回一维动态字节 `Memory` 语义。
  - 验证 `launch_kernel(name, block, thread, subthread)` 的输入类型、非空名称与静态正整数约束。
  - 验证 `launch_kernel` 的参数列表/顺序/必填与默认值语义：仅允许 `(name, block, thread, subthread)` 四个参数，不允许缺参、多参与未知关键字。
  - 验证 operation helper 到 `arch dialect` 的映射边界清晰，不引入新的方言或非 `arch` lowering 路径。
- 功能与用例清单：
  - `TC-OP-ARCH-001`：`get_block_id()` 返回 `SymbolDim` 风格 block 索引语义，并映射 `TC-ARCH-001`。
  - `TC-OP-ARCH-002`：`get_block_num()` 返回 `SymbolDim` 风格 block 数量语义，并映射 `TC-ARCH-002`。
  - `TC-OP-ARCH-003`：`get_thread_id()` 返回 `SymbolDim` 风格 thread 索引语义，并映射 `TC-ARCH-003`。
  - `TC-OP-ARCH-004`：`get_thread_num()` 返回 `SymbolDim` 风格 thread 数量语义，并映射 `TC-ARCH-004`。
  - `TC-OP-ARCH-005`：`get_subthread_id()` 返回 `SymbolDim` 风格 subthread 索引语义，并映射 `TC-ARCH-005`。
  - `TC-OP-ARCH-006`：`get_subthread_num()` 返回 `SymbolDim` 风格 subthread 数量语义，并映射 `TC-ARCH-006`。
  - `TC-OP-ARCH-007`：`get_dynamic_memory(MemorySpace.SM)` 返回 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8`、`space=MemorySpace.SM` 的动态内存语义，并映射 `TC-ARCH-007`。
  - `TC-OP-ARCH-008`：`get_dynamic_memory(...)` 对非法空间或非法类型报错，并覆盖 `MemorySpace.GM` 错误路径；对应 `TC-ARCH-008` 的方言边界。
  - `TC-OP-ARCH-009`：`launch_kernel("my_kernel", block, thread, subthread)` 接受合法 `int | SymbolDim` 输入并返回 `None`，对应 `TC-ARCH-009`。
  - `TC-OP-ARCH-010`：`launch_kernel(...)` 对空名称、非法类型、静态 `<= 0` 的规模输入报错，并对应 `TC-ARCH-010`。
  - `TC-OP-ARCH-011`：`launch_kernel` 调用签名固定为 `(name, block, thread, subthread)`，四参均必填且无默认值；缺参/多参/未知关键字必须在调用边界报 `TypeError`。映射测试：`test_launch_kernel_call_signature_errors`。
  - `TC-OP-ARCH-012`：`launch_kernel` 关键字调用仅接受 `name/block/thread/subthread` 四个参数名，语义与位置调用一致。映射测试：`test_launch_kernel_keyword_call_success`。
