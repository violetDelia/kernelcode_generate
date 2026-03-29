# arch.md

## 功能简介

- 定义 `arch` dialect 的硬件执行维度查询与内核启动描述接口。
- 该方言只覆盖 block/thread/subthread 三层执行索引、执行规模查询、动态内存入口与启动描述，不负责实际调度、同步、循环或 memory 读写语义。
- 执行维度标量统一使用 `!symbol.int<"expr">` 表达，以便与现有 `symbol`、`dma`、`dsl` 链路保持一致。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/dialect/arch.md`](../../spec/dialect/arch.md)
- `功能实现`：[`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py)
- 包级导出例外：[`kernel_gen/dialect/__init__.py`](../../kernel_gen/dialect/__init__.py)
- `test`：[`test/dialect/test_arch_dialect.py`](../../test/dialect/test_arch_dialect.py)

## 依赖

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：提供执行维度标量统一使用的 `!symbol.int<"expr">` 类型语义。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：提供 `NnMemoryType` 与 `NnMemorySpaceAttr` 的文本与校验规则。
- [`kernel_gen/dialect/__init__.py`](../../kernel_gen/dialect/__init__.py)：共享 `kernel_gen.dialect` 包入口；本 spec 只约束其中 `arch` 相关公开导出，`nn` 导出边界仍由各自 spec 单独约束。

## 目标

- 为 block/thread/subthread 三层硬件执行维度提供统一、可打印、可校验的 IR 查询接口。
- 为动态片上内存入口提供独立 op，避免其他方言重复定义“运行期动态内存句柄”的文本与 verifier 规则。
- 为后续实现提供最小可落地的 `parse/print`、类型约束、错误路径与测试清单。

## 限制与边界

- `arch` dialect 只定义执行维度查询、动态内存入口与启动描述；不定义网格调度策略、同步原语、kernel body、memory copy 或张量算术。
- `arch.get_block_id`、`arch.get_block_num`、`arch.get_thread_id`、`arch.get_thread_num`、`arch.get_subthread_id`、`arch.get_subthread_num` 都是无 operand、单结果 op。
- 上述查询 op 的结果类型必须分别固定为 `!symbol.int<"block_id">`、`!symbol.int<"block_num">`、`!symbol.int<"thread_id">`、`!symbol.int<"thread_num">`、`!symbol.int<"subthread_id">`、`!symbol.int<"subthread_num">`，不得改写为 builtin `index`、普通整数或其他符号表达。
- `arch.get_dynamic_memory` 只描述“获取某个 memory space 对应的动态 memory 入口”；不负责容量求值、分配策略或布局推导。
- `arch.get_dynamic_memory` 的结果类型当前统一为一维动态字节缓冲：`!nn.memory<[?], [1], i8, #nn.space<space>>`。
- `arch.get_dynamic_memory` 的 `memory_space` 只允许 `shared`、`local`、`tsm`、`tlm`；`global` 不属于动态片上内存入口范围，必须报错。
- `arch.launch_kernel` 只描述一次 kernel 启动请求，不定义返回值、region、异步句柄或启动完成语义。
- `arch.launch_kernel` 的 `block`、`thread`、`subthread` operand 必须为 `!symbol.int<"expr">`，且表达启动维度的正整数规模；负值、零值与非整型 symbol 标量不属于合法公开语义。
- 本文件只约束公开 IR 形式与 verifier 边界；不承诺 host/runtime 如何消费这些 op。
- `kernel_gen/dialect/__init__.py` 属于共享包入口文件，是本 spec “每个 spec 原则上只对应一个源文件”的例外；本文件只定义该包入口中 `Arch`、`ArchGetBlockIdOp`、`ArchGetBlockNumOp`、`ArchGetThreadIdOp`、`ArchGetThreadNumOp`、`ArchGetSubthreadIdOp`、`ArchGetSubthreadNumOp`、`ArchGetDynamicMemoryOp`、`ArchLaunchKernelOp` 这些 `arch` 公开符号的导出边界，不延伸约束同文件中的 `nn` 导出。

## operation API 映射

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
| `launch_kernel(name, block, thread, subthread)` | `arch.launch_kernel` | kernel 启动描述。 |

## 公开接口

### arch.get_block_id

功能说明：

- 返回当前 block 的执行索引。
- 结果类型固定为 `!symbol.int<"block_id">`。

参数说明：

- 无参数。

使用示例：

```text
%bid = arch.get_block_id : !symbol.int<"block_id">
```

注意事项：

- `parse/print` 必须保持无 operand、单结果形式。
- verifier 必须拒绝任何非 `!symbol.int<"block_id">` 的结果类型声明。

返回与限制：

- 返回类型：`!symbol.int<"block_id">`
- 限制：不接受自定义结果类型或附加属性。

### arch.get_block_num

功能说明：

- 返回当前 kernel launch 的 block 数量。
- 结果类型固定为 `!symbol.int<"block_num">`。

参数说明：

- 无参数。

使用示例：

```text
%bnum = arch.get_block_num : !symbol.int<"block_num">
```

注意事项：

- `parse/print` 必须保持无 operand、单结果形式。
- verifier 必须拒绝任何非 `!symbol.int<"block_num">` 的结果类型声明。

返回与限制：

- 返回类型：`!symbol.int<"block_num">`
- 限制：不接受 builtin `index` 或其他自定义 symbol 表达。

### arch.get_thread_id

功能说明：

- 返回当前 block 内 thread 的执行索引。
- 结果类型固定为 `!symbol.int<"thread_id">`。

参数说明：

- 无参数。

使用示例：

```text
%tid = arch.get_thread_id : !symbol.int<"thread_id">
```

注意事项：

- `parse/print` 必须保持无 operand、单结果形式。
- verifier 必须拒绝任何非 `!symbol.int<"thread_id">` 的结果类型声明。

返回与限制：

- 返回类型：`!symbol.int<"thread_id">`
- 限制：不接受 builtin `index` 或其他自定义 symbol 表达。

### arch.get_thread_num

功能说明：

- 返回当前 block 内 thread 数量。
- 结果类型固定为 `!symbol.int<"thread_num">`。

参数说明：

- 无参数。

使用示例：

```text
%tnum = arch.get_thread_num : !symbol.int<"thread_num">
```

注意事项：

- `parse/print` 必须保持无 operand、单结果形式。
- verifier 必须拒绝任何非 `!symbol.int<"thread_num">` 的结果类型声明。

返回与限制：

- 返回类型：`!symbol.int<"thread_num">`
- 限制：不接受 builtin `index` 或其他自定义 symbol 表达。

### arch.get_subthread_id

功能说明：

- 返回当前 thread 内 subthread 的执行索引。
- 结果类型固定为 `!symbol.int<"subthread_id">`。

参数说明：

- 无参数。

使用示例：

```text
%stid = arch.get_subthread_id : !symbol.int<"subthread_id">
```

注意事项：

- `parse/print` 必须保持无 operand、单结果形式。
- verifier 必须拒绝任何非 `!symbol.int<"subthread_id">` 的结果类型声明。

返回与限制：

- 返回类型：`!symbol.int<"subthread_id">`
- 限制：不接受 builtin `index` 或其他自定义 symbol 表达。

### arch.get_subthread_num

功能说明：

- 返回当前 thread 内 subthread 数量。
- 结果类型固定为 `!symbol.int<"subthread_num">`。

参数说明：

- 无参数。

使用示例：

```text
%stnum = arch.get_subthread_num : !symbol.int<"subthread_num">
```

注意事项：

- `parse/print` 必须保持无 operand、单结果形式。
- verifier 必须拒绝任何非 `!symbol.int<"subthread_num">` 的结果类型声明。

返回与限制：

- 返回类型：`!symbol.int<"subthread_num">`
- 限制：不接受 builtin `index` 或其他自定义 symbol 表达。

### arch.get_dynamic_memory(memory_space)

功能说明：

- 获取指定 memory space 的动态 memory 入口。
- 结果用于后续 memory 视图或子视图构造，表示“运行期提供的一段一维动态字节缓冲”。

参数说明：

- `memory_space(#nn.space<...>)`：动态 memory 所在空间，仅允许 `shared`、`local`、`tsm`、`tlm`。

使用示例：

```text
%smem = arch.get_dynamic_memory #nn.space<shared> : !nn.memory<[?], [1], i8, #nn.space<shared>>
```

注意事项：

- `parse/print` 必须同时打印 `memory_space` 与结果类型。
- verifier 必须校验结果类型为 `!nn.memory<[?], [1], i8, #nn.space<space>>`，其中 `space` 必须与 `memory_space` 属性一致。
- verifier 必须拒绝 `global` space、非一维结果、非 `i8` 元素类型、非单位 stride，或 `shape/stride/space` 与属性不一致的结果类型。

返回与限制：

- 返回类型：`!nn.memory<[?], [1], i8, #nn.space<space>>`
- 限制：当前只描述字节级动态 memory 入口，不描述容量、对齐或多维布局。

### arch.launch_kernel(name, block, thread, subthread)

功能说明：

- 描述一次 kernel 启动请求，记录 kernel 名称与 block/thread/subthread 三层启动规模。
- 该 op 不返回 SSA 结果，只作为启动描述存在。

参数说明：

- `name(str)`：kernel 入口名，必须为非空字符串。
- `block(!symbol.int<"expr">)`：block 维度。
- `thread(!symbol.int<"expr">)`：thread 维度。
- `subthread(!symbol.int<"expr">)`：subthread 维度。

使用示例：

```text
arch.launch_kernel "my_kernel", %block, %thread, %subthread : !symbol.int<"grid_x">, !symbol.int<"block_x">, !symbol.int<"subthread_x">
```

注意事项：

- `parse/print` 必须打印 `name` 属性与三个 operand 的类型列表。
- verifier 必须拒绝空字符串名称。
- verifier 必须拒绝任一 operand 不是 `!symbol.int<"expr">` 的情况。
- verifier 必须拒绝可静态判定为 `0` 或负值的 `block/thread/subthread` 输入；无法静态判定正负的符号表达可保留到后续阶段处理。
- 该 op 不定义 region、结果值、async token 或 device 选择属性。

返回与限制：

- 返回类型：无返回值。
- 限制：当前只支持单一三层启动配置；不支持多维网格、stream、事件或额外 launch 属性。

## 测试

- 测试文件：[`test/dialect/test_arch_dialect.py`](../../test/dialect/test_arch_dialect.py)
- 执行命令：`pytest -q test/dialect/test_arch_dialect.py`

### 测试目标

- 验证六个执行维度查询 op 的固定结果类型与无 operand 文本形式。
- 验证 `arch.get_dynamic_memory` 的 `space`、结果类型、parse/print 与 verifier 边界。
- 验证 `arch.launch_kernel` 的名称、operand 类型、静态非法规模与无结果约束。
- 验证 `arch` dialect 文本能够完成 parse/print round-trip。
- 验证 `kernel_gen.dialect` 包级入口已导出 `arch` 公共符号。

### 功能与用例清单

| 用例 ID | 功能 | 对应测试 |
| --- | --- | --- |
| TC-ARCH-001 | `arch.get_block_id` 固定返回 `!symbol.int<"block_id">` | `test_arch_get_block_id_result_type` |
| TC-ARCH-002 | `arch.get_block_num` 固定返回 `!symbol.int<"block_num">` | `test_arch_get_block_num_result_type` |
| TC-ARCH-003 | `arch.get_thread_id` 固定返回 `!symbol.int<"thread_id">` | `test_arch_get_thread_id_result_type` |
| TC-ARCH-004 | `arch.get_thread_num` 固定返回 `!symbol.int<"thread_num">` | `test_arch_get_thread_num_result_type` |
| TC-ARCH-005 | `arch.get_subthread_id` 固定返回 `!symbol.int<"subthread_id">` | `test_arch_get_subthread_id_result_type` |
| TC-ARCH-006 | `arch.get_subthread_num` 固定返回 `!symbol.int<"subthread_num">` | `test_arch_get_subthread_num_result_type` |
| TC-ARCH-007 | `arch.get_dynamic_memory` 合法路径 | `test_arch_get_dynamic_memory_success` |
| TC-ARCH-008 | `arch.get_dynamic_memory` 非法 `memory_space`/结果类型被拒绝 | `test_arch_get_dynamic_memory_verify_errors` |
| TC-ARCH-009 | `arch.launch_kernel` 合法路径 | `test_arch_launch_kernel_success` |
| TC-ARCH-010 | `arch.launch_kernel` 拒绝空名称、非 `symbol.int` operand 与静态非法规模 | `test_arch_launch_kernel_verify_errors` |
| TC-ARCH-011 | `arch` 方言 parse/print round-trip | `test_arch_parse_print_round_trip` |
| TC-ARCH-012 | `kernel_gen.dialect` 包级入口导出 `arch` 公共符号 | `test_arch_package_exports` |
