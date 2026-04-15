# arch.md

## 功能简介

- 定义 operation 层 `arch` helper API，提供执行维度查询、动态片上内存入口、barrier 与 kernel 启动描述的高层调用语义。
- 该层面向 Python/DSL 调用侧，统一约束 `get_block_id/get_block_num/get_thread_id/get_thread_num/get_subthread_id/get_subthread_num/get_dynamic_memory/barrier/launch_kernel` 的入参与返回，不重复定义新的 dialect 语义。
- operation 层只描述对外 helper 约定；底层 IR 形态、parse/print 与 verifier 约束统一复用 [`spec/dialect/arch.md`](../../spec/dialect/arch.md)。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`咯咯咯`
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
- `get_dynamic_memory(space)` 的公开结果语义必须收敛为一维字节缓冲：当 current target 已启用且 target registry 提供对应硬件 size 时逻辑 shape 为 `[size]`；未启用 current target 时允许动态回退为 `[?]`；若 current target 已启用但缺少对应 `hardware.*_memory_size` 字段，必须抛出 `ValueError`；stride 固定为 `[1]`、dtype 固定为 `NumericType.Int8`、space 与输入一致；operation 层不得额外承诺容量、对齐或多维布局。
- `get_dynamic_memory(space)` 只允许片上空间 `MemorySpace.SM`、`MemorySpace.LM`、`MemorySpace.TSM`、`MemorySpace.TLM1`、`MemorySpace.TLM2`、`MemorySpace.TLM3`；`MemorySpace.GM` 不属于动态片上内存入口范围，必须报错。
- `barrier(visibility, scope)` 只描述一次同步请求，不返回新的 `Memory`、`SymbolDim`、句柄对象或状态值；公开返回值固定为 `None`。
- `barrier` 的 `visibility` 只接受 `BarrierVisibility.TSM` 与 `BarrierVisibility.TLM` 两个聚合可见域，且必须恰好各出现一次；该枚举不等价于真实 `MemorySpace`，其中 `BarrierVisibility.TLM` 固定表示对 `TLM1/TLM2/TLM3` 三块真实空间的聚合可见域。
- `barrier` 的 `scope` 只接受公开 `BarrierScope` 枚举成员；不接受字符串、整数或其他临时 scope 约定。
- `launch_kernel(callee, block, thread, subthread, *args)` 只描述一次启动请求，不返回新的 `Memory`、`SymbolDim` 或句柄对象；公开返回值固定为 `None`。
- `launch_kernel` 调用签名固定为 `callee -> block -> thread -> subthread -> *args`；前四个参数均为必填，不提供默认值，尾部 `*args` 保留 kernel 位置参数顺序。
- `launch_kernel` 仅允许参数名 `callee/block/thread/subthread`；缺失参数、未知关键字参数或错误位置参数数量属于调用边界错误，必须抛出 `TypeError`。
- `launch_kernel(...)` 的 `callee` 必须是 Python 函数对象；不得接受字符串名称、`Memory`、`SymbolDim`、任意 callable 包装器或其他运行时对象。
- `launch_kernel(...)` 的 `block/thread/subthread` 只允许 `int` 或 `SymbolDim`，并显式拒绝 `bool`；若输入为静态整数，必须满足 `> 0`；operation 层不得接受浮点、`Memory`、列表或其他运行时对象。
- operation 层与 dialect 层采用一一映射：`get_*` helper 分别映射到对应 `arch.get_*` op，`get_dynamic_memory` 映射到 `arch.get_dynamic_memory`，`barrier` 映射到 `arch.barrier`，`launch_kernel` 映射到 `arch.launch`；不得通过其他 dialect 或 builtin op 绕过 `arch dialect`。
- 当 target registry 设置了 current target 时，所有 `arch` helper 在调用前都必须执行支持性校验；若当前 target 不支持对应 `arch.*` op，必须抛出 `ValueError`，且错误信息应包含 op 名与 target 名。
- `get_block_num/get_thread_num/get_subthread_num` 在 launch 外侧遵循同一规则：当 current target 已启用且 target registry 提供对应硬件值时必须优先返回静态设备值；未启用 current target 时允许动态回退为各自 `SymbolDim("<name>")`；若 current target 已启用但缺少对应 `hardware.<field>`，必须抛出 `ValueError`。
- `get_dynamic_memory(space)` 在 current target 已启用且 target registry 提供对应 `*_memory_size` 时必须优先使用静态 size；未启用 current target 时允许动态回退为 `[?]`；若 current target 已启用但缺少对应 `hardware.*_memory_size`，必须抛出 `ValueError`。
- `get_block_num/get_thread_num/get_subthread_num` 在 `launch_kernel(...)` 的 Python launched body 内，必须优先返回本次 launch 的 `block/thread/subthread` extent 语义；离开 launch 上下文后才恢复为“静态设备值优先、未启用 current target 时动态回退、缺字段时报错”的常规规则。

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
- 当 current target 已启用且硬件 `block_num` 可用时必须优先返回静态值；未启用 current target 时回退 `SymbolDim("block_num")` 语义；若 current target 已启用但缺少 `hardware.block_num`，必须抛出 `ValueError`。

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
- 当 current target 已启用且硬件 `thread_num` 可用时必须优先返回静态值；未启用 current target 时回退 `SymbolDim("thread_num")` 语义；若 current target 已启用但缺少 `hardware.thread_num`，必须抛出 `ValueError`。

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
- 当 current target 已启用且硬件 `subthread_num` 可用时必须优先返回静态值；未启用 current target 时回退 `SymbolDim("subthread_num")` 语义；若 current target 已启用但缺少 `hardware.subthread_num`，必须抛出 `ValueError`。

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
- 返回结果的公开语义必须是一维字节缓冲：`stride=[1]`、`dtype=NumericType.Int8`、`space=<输入空间>`；当 current target 已启用且 target registry 提供对应 `*_memory_size` 时 `shape=[size]`；未启用 current target 时动态回退 `shape=[?]`；若 current target 已启用但缺少对应 `hardware.*_memory_size`，必须抛出 `ValueError`。
- operation 层不得公开承诺容量、对齐或多维 view 语义；这些约束由后续 DMA/view helper 单独承担。
- 当设置 current target 时必须通过 target registry 校验 `arch.get_dynamic_memory` 支持性；不支持时抛出 `ValueError`。

返回与限制：

- 返回类型：`Memory`
- 限制：lowering 后结果必须对应 `!nn.memory<[?], [1], i8, #nn.space<space>>`，其中 `space` 与输入映射一致；若 operation 层持有静态 `shape=[size]`，该静态信息仅用于高层语义与类型推断，不改变 `arch.get_dynamic_memory` 的 IR 结果类型约束。

### `barrier(visibility, scope)`

功能说明：

- 记录一次 operation 层 barrier 请求，显式表达同步可见域与聚合 scope。
- lowering 后必须一一映射到 `arch.barrier`。

参数说明：

- `visibility (list[BarrierVisibility] | tuple[BarrierVisibility, ...])`：公开聚合可见域集合；当前只接受 `BarrierVisibility.TSM` 与 `BarrierVisibility.TLM`，且必须恰好各出现一次。
- `scope (BarrierScope)`：同步范围枚举；仅接受公开 `BarrierScope` 成员。

使用示例：

```python
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier

barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)
```

注意事项：

- `BarrierVisibility` 是 operation 层聚合可见域，不等同于真实 `MemorySpace`；其中 `BarrierVisibility.TLM` 固定覆盖 `TLM1/TLM2/TLM3` 三块真实空间。
- `visibility` 不得为空、不得包含重复项，也不得缺少 `TSM` 或 `TLM` 任何一项。
- `scope` 只接受 `BarrierScope` 枚举成员。
- operation 层 helper 只描述同步请求，不负责事件、句柄、异步状态或 kernel 完成通知。
- 当设置 current target 时必须通过 target registry 校验 `arch.barrier` 支持性；不支持时抛出 `ValueError`。

返回与限制：

- 返回类型：`None`
- 限制：lowering 后必须继续保持 “`TSM` + 聚合 `TLM`” 的公开语义，不得在 operation 层把 `BarrierVisibility.TLM` 展开成多个用户可见参数。

### `launch_kernel(callee, block, thread, subthread, *args)`

功能说明：

- 记录一次 kernel 启动请求的高层语义，包含 Python 函数对象、block/thread/subthread 三层执行规模与尾部 kernel 实参。
- lowering 后必须一一映射到 `arch.launch`。

参数说明：

- 参数列表与顺序：`(callee, block, thread, subthread, *args)`。
- `callee (function)`：必填，参数序号 `#1`；Python 函数对象；默认值：无。
- `block (int | SymbolDim)`：必填，参数序号 `#2`；block 规模；默认值：无。
- `thread (int | SymbolDim)`：必填，参数序号 `#3`；thread 规模；默认值：无。
- `subthread (int | SymbolDim)`：必填，参数序号 `#4`；subthread 规模；默认值：无。
- `*args (object)`：可选尾部位置参数；保持传入顺序并原样转交给 `callee`。

使用示例：

```python
from kernel_gen.operation.arch import launch_kernel
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

def kernel_body(lhs, rhs, out):
    pass

launch_kernel(kernel_body, SymbolDim("GRID_X"), 128, 4, "lhs", "rhs", "out")
```

注意事项：

- 前四个参数全部为必填参数，且不定义默认值；尾部只允许通过 `*args` 继续传入 kernel 参数。
- 允许按关键字调用（如 `launch_kernel(callee=kernel_body, block=4, thread=2, subthread=1)`），但关键字名必须是 `callee/block/thread/subthread`。
- 调用边界错误（缺失任一必填参数、传入未知关键字参数）必须抛出 `TypeError`，并在进入语义校验前失败。
- `callee` 若不是 Python 函数对象，必须抛出 `TypeError`。
- `block/thread/subthread` 若不是 `int` 或 `SymbolDim`，或传入 `bool`，必须抛出 `TypeError`。
- 当 `block/thread/subthread` 为静态整数时，必须要求其大于 `0`；`0` 或负值必须抛出 `ValueError`。
- 当输入为 `SymbolDim` 时，operation 层只保留符号语义，不要求在 Python 运行期求值。
- operation 层 helper 只描述启动请求，不负责真正执行 kernel，也不返回事件、句柄或状态值。
- 在 Python launched body 内，`get_block_num/get_thread_num/get_subthread_num` 必须优先暴露本次 launch 的 extent 语义；离开 body 后恢复常规查询语义。
- 当设置 current target 时必须通过 target registry 校验 `arch.launch` 支持性；不支持时抛出 `ValueError`。

返回与限制：

- 返回类型：`None`
- 限制：lowering 后三个规模 operand 必须保持 `!symbol.int<"expr">` 语义，不得退化为 builtin `index` 或普通整数类型。

## 测试

- 测试文件：[`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)
- 执行命令：`pytest -q test/operation/test_operation_arch.py`
- 验收命令（barrier / launch 参数规范）：`pytest -q test/operation/test_operation_arch.py -k 'barrier or launch_kernel'`
- 测试目标：
  - 验证六个执行维度查询 helper 的公开返回语义均为 `SymbolDim` 风格标量，并与 `arch dialect` 的固定结果语义一一对应。
  - 验证 `get_dynamic_memory(space)` 只接受允许的片上空间，且返回一维动态字节 `Memory` 语义。
  - 验证 `barrier(visibility, scope)` 的聚合可见域、去重规则与 scope 校验。
  - 验证 `launch_kernel(callee, block, thread, subthread, *args)` 的输入类型、显式拒绝 `bool`、静态正整数约束与尾部参数转交语义。
  - 验证 `launch_kernel` 的参数列表/顺序/必填与默认值语义：仅允许 `(callee, block, thread, subthread)` 四个必填入口和尾部 `*args`，不允许缺参与未知关键字。
  - 验证 operation helper 到 `arch dialect` 的映射边界清晰，不引入新的方言或非 `arch` lowering 路径。
  - 验证 launched body 内查询优先使用本次 launch extent，launch 外侧仍保持“静态设备值优先、未启用 current target 时动态回退、缺字段时报错”的语义。
  - 验证当前 target 不支持的 `arch.*` helper 调用必须报错。
- 功能与用例清单：
  - `TC-OP-ARCH-001`：`get_block_id()` 返回 `SymbolDim` 风格 block 索引语义，并映射 `TC-ARCH-001`。
  - `TC-OP-ARCH-002`：`get_block_num()` 返回 `SymbolDim` 风格 block 数量语义，并映射 `TC-ARCH-002`。
  - `TC-OP-ARCH-003`：`get_thread_id()` 返回 `SymbolDim` 风格 thread 索引语义，并映射 `TC-ARCH-003`。
  - `TC-OP-ARCH-004`：`get_thread_num()` 返回 `SymbolDim` 风格 thread 数量语义，并映射 `TC-ARCH-004`。
  - `TC-OP-ARCH-005`：`get_subthread_id()` 返回 `SymbolDim` 风格 subthread 索引语义，并映射 `TC-ARCH-005`。
  - `TC-OP-ARCH-006`：`get_subthread_num()` 返回 `SymbolDim` 风格 subthread 数量语义，并映射 `TC-ARCH-006`。
  - `TC-OP-ARCH-007`：当未启用 current target 时，`get_dynamic_memory(MemorySpace.SM)` 返回 `shape=[?]`、`stride=[1]`、`dtype=NumericType.Int8`、`space=MemorySpace.SM` 的动态内存语义，并映射 `TC-ARCH-007`。
  - `TC-OP-ARCH-008`：`get_dynamic_memory(...)` 对非法空间或非法类型报错，并覆盖 `MemorySpace.GM` 错误路径；对应 `TC-ARCH-008` 的方言边界。
  - `TC-OP-ARCH-009`：`barrier(...)` 接受合法 `visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM]` 与任一公开 `BarrierScope` 并返回 `None`。
  - `TC-OP-ARCH-010`：`barrier(...)` 对缺参、非法 `visibility`、重复项、缺项或非法 `scope` 报错。
  - `TC-OP-ARCH-011`：`launch_kernel(callee, block, thread, subthread, *args)` 接受合法 `int | SymbolDim` extent 与尾部 kernel args，并在 launched body 内暴露本次 launch extent。
  - `TC-OP-ARCH-012`：`launch_kernel(...)` 对字符串 `callee`、非法类型、`bool`、静态 `<= 0` 的规模输入报错。
  - `TC-OP-ARCH-013`：`launch_kernel` 调用签名固定为 `(callee, block, thread, subthread)` 四个必填入口；缺参或未知关键字必须在调用边界报 `TypeError`。
  - `TC-OP-ARCH-014`：`launch_kernel` 关键字调用仅接受 `callee/block/thread/subthread` 四个参数名，语义与位置调用一致。
  - `TC-OP-ARCH-015`：target registry 提供硬件值时，launch 外侧的 `get_block_num()` / `get_thread_num()` / `get_subthread_num()` / `get_dynamic_memory()` 必须优先使用硬件值；launched body 内数量类查询则优先返回本次 launch extent。
  - `TC-OP-ARCH-016`：当当前 target 不支持某个 `arch.*` op 时，对应 helper 的 target registry 支持性校验必须抛出 `ValueError` 并包含 op 名称；本条覆盖 `barrier` / `launch_kernel` 与查询类 helper 的错误路径。
  - `TC-OP-ARCH-017`：当 current target 已启用但缺少 `block_num/thread_num/subthread_num/sm_memory_size` 等必需 `hardware` 字段时，`get_block_num()` / `get_thread_num()` / `get_subthread_num()` / `get_dynamic_memory(MemorySpace.SM)` 必须抛出包含 `hardware.<field>` 的 `ValueError`。映射测试：`test_query_helpers_reject_missing_target_hardware_fields`。
