# arch.md

## 功能简介

- 定义 operation 层 `arch` helper API，提供执行维度查询、动态片上内存入口、barrier 与 kernel 启动描述的高层调用语义。
- 该层面向 Python/DSL 调用侧，统一约束 `get_block_id/get_block_num/get_thread_id/get_thread_num/get_subthread_id/get_subthread_num/get_dynamic_memory/barrier/launch_kernel` 的入参与返回，不重复定义新的 dialect 语义。
- operation 层只描述对外 helper 约定；底层 IR 形态、parse/print 与 verifier 约束统一复用 [`spec/dialect/arch.md`](../../spec/dialect/arch.md)。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/operation/arch.md`](../../spec/operation/arch.md)
- `功能实现`：[`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
- `test`：[`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)

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
- 为后续实现任务明确 `kernel_gen/operation/arch.py` 与 `test/operation/test_operation_arch.py` 的公开接口范围、错误边界与测试清单。

## 限制与边界

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
- `launch_kernel` 的公开调用形态固定为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`：四个 launch 字段位于下标，调用参数顺序固定为 `callee -> *args`；旧直调用 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 只允许作为兼容实现路径存在，不再属于公开合同。
- `launch_kernel` 仅允许关键字参数名 `callee/block/thread/subthread`；缺失前四个必填参数或传入未知关键字参数属于调用边界错误，必须抛出 `TypeError`。
- `launch_kernel[...]` 的 `callee` 只允许 Python 函数对象；不得接受字符串名、其他 callable、`Memory`、`SymbolDim` 或自由对象。
- `launch_kernel[...]` 的 `block/thread/subthread` 只允许 `int` 或 `SymbolDim`，且不得接受 `bool`；若输入为静态整数，必须满足 `> 0`；operation 层不得接受浮点、`Memory`、列表或其他运行时对象。
- operation 层与 dialect 层采用一一映射：`get_*` helper 分别映射到对应 `arch.get_*` op，`get_dynamic_memory` 映射到 `arch.get_dynamic_memory`，`barrier` 映射到 `arch.barrier`，`launch_kernel` 的支持性校验与 lowering 语义固定对应 `arch.launch`；不得通过其他 dialect 或 builtin op 绕过 `arch dialect`，也不得回退旧 launch op 命名。
- 当 target registry 设置了 current target 时，所有 `arch` helper 在调用前都必须执行支持性校验；若当前 target 不支持对应 `arch.*` op，必须抛出 `ValueError`，且错误信息应包含 op 名与 target 名。
- `get_block_num/get_thread_num/get_subthread_num` 在 target registry 提供对应硬件值时必须优先返回静态值；缺失时回退为各自 `SymbolDim("<name>")` 语义。
- `get_dynamic_memory(space)` 在 target registry 提供对应 `*_memory_size` 时必须优先使用静态 size；缺失时回退为动态 `[?]`。

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
- 当设置 current target 时必须通过 target registry 校验 `arch.get_block_id` 支持性；不支持时抛出 `ValueError`。

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
- 当设置 current target 时必须通过 target registry 校验 `arch.get_block_num` 支持性；不支持时抛出 `ValueError`。
- 当硬件 `block_num` 可用时必须优先返回静态值；缺失时回退 `SymbolDim("block_num")` 语义。

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
- 当设置 current target 时必须通过 target registry 校验 `arch.get_thread_id` 支持性；不支持时抛出 `ValueError`。

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
- 当设置 current target 时必须通过 target registry 校验 `arch.get_thread_num` 支持性；不支持时抛出 `ValueError`。
- 当硬件 `thread_num` 可用时必须优先返回静态值；缺失时回退 `SymbolDim("thread_num")` 语义。

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
- 当设置 current target 时必须通过 target registry 校验 `arch.get_subthread_id` 支持性；不支持时抛出 `ValueError`。

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
- 当设置 current target 时必须通过 target registry 校验 `arch.get_subthread_num` 支持性；不支持时抛出 `ValueError`。
- 当硬件 `subthread_num` 可用时必须优先返回静态值；缺失时回退 `SymbolDim("subthread_num")` 语义。

返回与限制：

- 返回类型：`SymbolDim`
- 限制：lowering 后结果语义必须固定对应 `!symbol.int<"subthread_num">`。

### `get_dynamic_memory(space)`

功能说明：

- 返回指定片上空间的运行期动态内存入口高层语义。
- lowering 后必须一一映射到 `arch.get_dynamic_memory`。

参数说明：

- `space (MemorySpace)`：目标片上空间，只允许 `MemorySpace.SM`、`MemorySpace.LM`、`MemorySpace.TSM`、`MemorySpace.TLM1`、`MemorySpace.TLM2`、`MemorySpace.TLM3`。

使用示例：

```python
from kernel_gen.symbol_variable.memory import MemorySpace

smem = get_dynamic_memory(MemorySpace.SM)
```

注意事项：

- 输入若不是 `MemorySpace`，必须抛出 `TypeError`。
- 输入若为 `MemorySpace.GM`，必须抛出 `ValueError`。
- 返回结果的公开语义必须是一维字节缓冲：`stride=[1]`、`dtype=NumericType.Int8`、`space=<输入空间>`；当 target registry 提供对应 `*_memory_size` 时 `shape=[size]`，缺失时回退 `shape=[?]`。
- operation 层不得公开承诺容量、对齐或多维 view 语义；这些约束由后续 DMA/view helper 单独承担。
- 当设置 current target 时必须通过 target registry 校验 `arch.get_dynamic_memory` 支持性；不支持时抛出 `ValueError`。
- `MemorySpace.TLM1/TLM2/TLM3` 为真实动态片上空间；若调用方需要 barrier 聚合可见域，应改用 `BarrierVisibility.TLM`，不得把二者混用。

返回与限制：

- 返回类型：`Memory`
- 限制：lowering 后结果必须对应 `!nn.memory<[?], [1], i8, #nn.space<space>>`，其中 `space` 与输入映射一致；若 operation 层持有静态 `shape=[size]`，该静态信息仅用于高层语义与类型推断，不改变 `arch.get_dynamic_memory` 的 IR 结果类型约束。

### `BarrierVisibility`

功能说明：

- 定义 `barrier(visibility, scope)` 的公开聚合可见域枚举。
- 当前稳定成员固定为 `BarrierVisibility.TSM` 与 `BarrierVisibility.TLM`。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.operation.arch import BarrierVisibility

visibility = BarrierVisibility.TLM
```

注意事项：

- `BarrierVisibility.TLM` 只表示 barrier 聚合可见域，固定覆盖 `MemorySpace.TLM1/TLM2/TLM3`，不等于真实 `MemorySpace`。
- `BarrierVisibility` 不用于 `get_dynamic_memory(space)` 的 `space` 参数；真实动态片上空间仍由 `MemorySpace` 表达。

返回与限制：

- 返回类型：`BarrierVisibility`
- 限制：公开成员固定为 `TSM/TLM`，不得扩成真实内存空间枚举。

### `BarrierScope`

功能说明：

- 定义 `barrier(visibility, scope)` 的公开同步范围枚举。
- 当前稳定成员固定为 `BarrierScope.BLOCK`、`BarrierScope.THREAD`、`BarrierScope.SUBTHREAD`、`BarrierScope.GLOBAL`。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.operation.arch import BarrierScope

scope = BarrierScope.THREAD
```

注意事项：

- operation 层允许四个公开 scope；具体 target 若不支持其中某项，必须通过 target registry 显式失败，不得静默降级。

返回与限制：

- 返回类型：`BarrierScope`
- 限制：公开成员固定为 `BLOCK/THREAD/SUBTHREAD/GLOBAL`。

### `barrier(*, visibility, scope)`

功能说明：

- 记录一次 barrier 同步请求的高层语义。
- target registry 支持性校验与 lowering 后的语义必须一一对应 `arch.barrier`。

参数说明：

- `visibility (list[BarrierVisibility] | tuple[BarrierVisibility, ...])`：必填；需要保证可见性的聚合可见域列表。
- `scope (BarrierScope)`：必填；同步范围。

使用示例：

```python
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier

barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)
```

注意事项：

- `visibility` 与 `scope` 都是必填关键字参数，不接受无参调用或位置参数。
- `visibility` 必须非空，元素必须全部为 `BarrierVisibility`，不得重复，且必须且只能包含 `TSM/TLM` 各一次。
- `scope` 必须是 `BarrierScope` 枚举成员。
- `barrier` 只描述同步请求，不负责数据搬运、事件管理或 target 私有副作用。
- 当设置 current target 时必须通过 target registry 校验 `arch.barrier` 支持性；不支持时抛出 `ValueError`。

返回与限制：

- 返回类型：`None`
- 限制：公开合同固定为 `barrier(*, visibility, scope)`，不得回退为无参 barrier。

### `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`

功能说明：

- 记录一次 kernel 启动请求的高层语义，包含 Python 函数对象 `callee`、block/thread/subthread/shared_memory_size 四层启动规模与尾部 kernel 实参。
- target registry 支持性校验与 lowering 后的语义必须一一对应 `arch.launch`。

参数说明：

- 下标参数顺序：`block -> thread -> subthread -> shared_memory_size`。
- 调用参数顺序：`callee -> *args`。
- `block (int | SymbolDim)`：必填，下标字段 `#1`；block 规模。
- `thread (int | SymbolDim)`：必填，下标字段 `#2`；thread 规模。
- `subthread (int | SymbolDim)`：必填，下标字段 `#3`；subthread 规模。
- `shared_memory_size (int | SymbolDim)`：必填，下标字段 `#4`；共享内存规模；静态整数必须 `>= 0`。
- `callee (function)`：必填，调用参数 `#1`；Python 函数对象。
- `*args (object)`：可选，位置参数；按原顺序透传给 `callee` 的 kernel 实参。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

def my_kernel(lhs, rhs, out):
    return None


launch_kernel[SymbolDim("GRID_X"), 128, 4, 0](my_kernel, "lhs", "rhs", "out")
```

注意事项：

- 四个 launch 字段必须全部在下标中给出；`callee` 与 `*args` 只允许按调用参数位置传入。
- 下标字段个数不是 `4`、或在公开入口上传入关键字参数时，必须抛出 `TypeError`，并在进入语义校验前失败。
- `callee` 只允许 Python 函数对象；字符串名称、其他 callable、`Memory`、`SymbolDim` 或自由对象都必须抛出 `TypeError`。
- `block/thread/subthread` 若不是 `int` 或 `SymbolDim`，必须抛出 `TypeError`；`bool` 不得沿用 Python `bool is int` 语义混入。
- 当 `block/thread/subthread` 为静态整数时，必须要求其大于 `0`；`0` 或负值必须抛出 `ValueError`。
- `shared_memory_size` 若不是 `int` 或 `SymbolDim`，必须抛出 `TypeError`；`bool` 不得沿用 Python `bool is int` 语义混入。
- 当 `shared_memory_size` 为静态整数时，必须要求其大于等于 `0`；负值必须抛出 `ValueError`。
- 当输入为 `SymbolDim` 时，operation 层只保留符号语义，不要求在 Python 运行期求值。
- operation 层 helper 只描述启动请求，不负责真正执行 kernel，也不返回事件、句柄或状态值。
- 当 `callee` 在 Python 中被调用时，`get_block_num/get_thread_num/get_subthread_num` 必须优先暴露本次 launch 的 extent 语义，再在 launch 外回退 target hardware 或符号值。
- 当设置 current target 时必须通过 target registry 校验 `arch.launch` 支持性；不支持时抛出 `ValueError`。

返回与限制：

- 返回类型：`None`
- 限制：lowering 后四个规模 operand 必须保持 `!symbol.int<"expr">` 语义，不得退化为 builtin `index` 或普通整数类型；尾部 `*args` 必须按原顺序传给 `@callee`，不得被重排或静默丢弃。

## 测试

- 测试文件：[`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)
- 执行命令：`pytest -q test/operation/test_operation_arch.py`
- 验收命令（barrier / launch 合同）：`pytest -q test/operation/test_operation_arch.py -k "barrier or launch_kernel"`
- 测试目标：
  - 验证六个执行维度查询 helper 的公开返回语义均为 `SymbolDim` 风格标量，并与 `arch dialect` 的固定结果语义一一对应。
  - 验证 `get_dynamic_memory(space)` 只接受允许的片上空间 `SM/LM/TSM/TLM1/TLM2/TLM3`，且返回一维动态字节 `Memory` 语义。
  - 验证 `BarrierVisibility` 的聚合语义、`barrier(*, visibility, scope)` 的关键字参数合同与 `arch.barrier` 支持性校验。
  - 验证 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 的函数对象、extent、尾部参数与 launched body 上下文语义。
  - 验证 `launch_kernel` 的参数列表/顺序/必填与默认值语义：公开入口只允许四个下标字段加 `callee, *args`，不允许缺字段、未知关键字或把 launch 字段写回调用参数。
  - 验证 operation helper 到 `arch dialect` 的映射边界清晰，不引入新的方言或非 `arch` lowering 路径。
  - 验证 target registry 硬件值优先生效，缺失时回退符号/动态语义。
  - 验证当前 target 不支持的 `arch.*` helper 调用必须报错，并覆盖 target registry 缺失关键字段时的显式错误路径。
- 功能与用例清单：
  - `TC-OP-ARCH-001`：`get_block_id()` 返回 `SymbolDim` 风格 block 索引语义，并映射 `TC-ARCH-001`。
  - `TC-OP-ARCH-002`：`get_block_num()` 返回 `SymbolDim` 风格 block 数量语义，并映射 `TC-ARCH-002`。
  - `TC-OP-ARCH-003`：`get_thread_id()` 返回 `SymbolDim` 风格 thread 索引语义，并映射 `TC-ARCH-003`。
  - `TC-OP-ARCH-004`：`get_thread_num()` 返回 `SymbolDim` 风格 thread 数量语义，并映射 `TC-ARCH-004`。
  - `TC-OP-ARCH-005`：`get_subthread_id()` 返回 `SymbolDim` 风格 subthread 索引语义，并映射 `TC-ARCH-005`。
  - `TC-OP-ARCH-006`：`get_subthread_num()` 返回 `SymbolDim` 风格 subthread 数量语义，并映射 `TC-ARCH-006`。
  - `TC-OP-ARCH-007`：`get_dynamic_memory(space)` 在 `SM/LM/TSM/TLM1/TLM2/TLM3` 六类片上空间都返回 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8` 的一维动态内存语义，并映射 `TC-ARCH-007`。
  - `TC-OP-ARCH-008`：`get_dynamic_memory(...)` 对非法空间或非法类型报错，并覆盖 `MemorySpace.GM` 错误路径；对应 `TC-ARCH-008` 的方言边界。
  - `TC-OP-ARCH-009`：`barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=...)` 接受合法聚合可见域与公开 scope 并返回 `None`。
  - `TC-OP-ARCH-010`：`barrier(...)` 对缺参、空列表、重复 `visibility`、错误元素类型与非法 `scope` 报错。
  - `TC-OP-ARCH-011`：`launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 接受合法 `function/int|SymbolDim` 输入与尾部 kernel 参数，并在 launched body 内暴露本次 launch extent。
  - `TC-OP-ARCH-012`：`launch_kernel[...]` 对字符串或非函数 `callee`、非法类型与静态 `<= 0` 的规模输入报错。
  - `TC-OP-ARCH-013`：`launch_kernel` 的公开入口固定为四个下标字段加 `callee, *args`；缺字段、未知关键字或把 launch 字段写进调用参数都必须在调用边界报 `TypeError`。
  - `TC-OP-ARCH-014`：实现若保留旧直调用 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 兼容路径，其行为不得改变 `launch_kernel[...]` 的公开语义，也不得反向扩回公开文档口径。
  - `TC-OP-ARCH-015`：target registry 提供硬件值时，launch 外的 `get_block_num()` / `get_thread_num()` / `get_subthread_num()` / `get_dynamic_memory()` 必须优先使用硬件值；launched body 内则优先暴露本次 launch extent。
  - `TC-OP-ARCH-016`：当当前 target 不支持某个 `arch.*` op 时，对应 helper 的 target registry 支持性校验必须抛出 `ValueError` 并包含 op 名称；本条覆盖 `get_block_num()` / `get_thread_num()` / `get_subthread_num()` / `get_dynamic_memory()` / `barrier()` / `launch_kernel()` 的错误路径。
  - `TC-OP-ARCH-017`：当当前 target registry 条目缺少 `arch_supported_ops/arch_unsupported_ops` 等必需字段时，arch query helper 必须返回显式 `missing required arch fields` 错误。
  - `TC-OP-ARCH-018`：当当前 target registry 条目缺少 `hardware` 关键字段时，`get_dynamic_memory()` 必须返回显式 `missing required hardware field` 错误。
