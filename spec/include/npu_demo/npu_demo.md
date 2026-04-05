# npu_demo

## 功能简介

定义 `npu_demo` 后端私有 include 规范，冻结 `KernelContext` 对 block/thread/subthread 的 id 与 count 查询接口，以及 `get_dynamic_memory` 内存查询接口，作为后端内部约定使用的最小上下文能力集。

## 文档信息

- 创建者：`jcc你莫辜负`
- 最后一次更改：`jcc你莫辜负`
- `spec`：[`spec/include/npu_demo/npu_demo.md`](../../../spec/include/npu_demo/npu_demo.md)
- `功能实现`：[`include/npu_demo/npu_demo.h`](../../../include/npu_demo/npu_demo.h)
- `test`：[`test/include/npu_demo/test_kernel_context.py`](../../../test/include/npu_demo/test_kernel_context.py)

## 依赖

- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：统一的 `Memory<T>` 视图类型语义。
- [`spec/operation/arch.md`](../../../spec/operation/arch.md)：`npu_demo` 的 id/count 固定值语义基线。

## 目标

- 冻结 `npu_demo::KernelContext` 的 `block_id/block_num/thread_id/thread_num/subthread_id/subthread_num` accessor 公开契约。
- 提供稳定的后端内部上下文查询接口，确保与 `npu_demo` 固定硬件模板一致。
- 定义 `KernelContext::get_dynamic_memory<T>(MemorySpace space)` 的返回语义与错误路径。

## 限制与边界

- 本规范是后端私有 include 合同，不作为公开 API 面向业务调用方。
- 不定义 `KernelContext` 的构造流程或生命周期管理。
- 不定义 launch/runtime wrapper。
- 后续如有 memory 参数，统一使用 `Memory<T>` 表达内存视图，不引入其他自定义内存类型。
- `get_dynamic_memory` 的模板参数仅允许元素类型，`space` 必须使用 `MemorySpace` 枚举值；不得把空间作为模板参数或出现空间模板化写法。
- 不定义 `.view<T>()` 或 `npu_demo::Memory` 等额外内存接口。
- `include/npu_demo/npu_demo.h` 作为 `npu_demo` 单入口头文件，需透传 `include/api/Memory.h` / `Dma.h` / `Nn.h` 的统一接口声明，并汇聚 `include/npu_demo/Core.h` / `Memory.h` / `Dma.h` / `Nn.h` 的后端实现；对应 `include/api` 头文件仅提供声明。

## 公开接口

### `npu_demo::KernelContext`

功能说明：

- 表示 `npu_demo` 后端的内核上下文数据，提供 block/thread/subthread 的 id 与 count 查询。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

void kernel_body(const npu_demo::KernelContext& ctx) {
    long long bid = ctx.block_id();
    long long bnum = ctx.block_num();
    (void)bid;
    (void)bnum;
}
```

注意事项：

- `KernelContext` 仅作为上下文访问对象，不定义构造或持有策略。

返回与限制：

- 返回类型：`npu_demo::KernelContext`。
- 返回语义：携带后端上下文信息。
- 限制条件：本规范不定义上下文创建与填充流程。

#### `block_id()`

功能说明：

- 返回当前 block 的 id。

参数说明：

- 无参数。

使用示例：

```cpp
long long bid = ctx.block_id();
```

注意事项：

- 返回值语义为 `int64`，当前以 `long long` 表达。

返回与限制：

- 返回类型：`long long`（语义等同 `int64`）。
- 返回语义：当前 block id。

#### `block_num()`

功能说明：

- 返回 block 总数。

参数说明：

- 无参数。

使用示例：

```cpp
long long bnum = ctx.block_num();
```

注意事项：

- 返回值语义为 `int64`，当前以 `long long` 表达。

返回与限制：

- 返回类型：`long long`（语义等同 `int64`）。
- 返回语义：block 数量。

#### `thread_id()`

功能说明：

- 返回当前 thread 的 id。

参数说明：

- 无参数。

使用示例：

```cpp
long long tid = ctx.thread_id();
```

注意事项：

- 返回值语义为 `int64`，当前以 `long long` 表达。

返回与限制：

- 返回类型：`long long`（语义等同 `int64`）。
- 返回语义：当前 thread id。

#### `thread_num()`

功能说明：

- 返回 thread 总数。

参数说明：

- 无参数。

使用示例：

```cpp
long long tnum = ctx.thread_num();
```

注意事项：

- 返回值语义为 `int64`，当前以 `long long` 表达。

返回与限制：

- 返回类型：`long long`（语义等同 `int64`）。
- 返回语义：thread 数量。

#### `subthread_id()`

功能说明：

- 返回当前 subthread 的 id。

参数说明：

- 无参数。

使用示例：

```cpp
long long sid = ctx.subthread_id();
```

注意事项：

- 返回值语义为 `int64`，当前以 `long long` 表达。

返回与限制：

- 返回类型：`long long`（语义等同 `int64`）。
- 返回语义：当前 subthread id。

#### `subthread_num()`

功能说明：

- 返回 subthread 总数。

参数说明：

- 无参数。

使用示例：

```cpp
long long snum = ctx.subthread_num();
```

注意事项：

- 返回值语义为 `int64`，当前以 `long long` 表达。

返回与限制：

- 返回类型：`long long`（语义等同 `int64`）。
- 返回语义：subthread 数量。

#### `get_dynamic_memory<T>(MemorySpace space)`

功能说明：

- 返回指定 `MemorySpace` 的动态内存视图，元素类型由模板参数 `T` 指定。

参数说明：

- `T`：元素类型模板参数。
- `space (MemorySpace)`：目标内存空间枚举值。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

void kernel_body(const npu_demo::KernelContext& ctx) {
    auto tsm_mem = ctx.get_dynamic_memory<float>(MemorySpace::TSM);
    auto tlm_mem = ctx.get_dynamic_memory<float>(MemorySpace::TLM);
    (void)tsm_mem;
    (void)tlm_mem;
}
```

注意事项：

- 模板参数仅用于元素类型；`space` 必须通过 `MemorySpace::TSM` / `MemorySpace::TLM` 等枚举值传入。
- 当 `space` 为 `MemorySpace::SM` 且硬件模板 `sm_memory_size=0` 时必须拒绝并抛错，错误消息需包含 `sm_memory_size=0`。

返回与限制：

- 返回类型：`Memory<T>`。
- 返回语义：
  - 当 `space=MemorySpace::TSM` 时，返回 `space=TSM`、`shape=[24576]`、`stride=[1]` 的 `Memory<T>`。
  - 当 `space=MemorySpace::TLM` 时，返回 `space=TLM`、`shape=[2048]`、`stride=[1]` 的 `Memory<T>`。
- 限制条件：
  - 当 `space=MemorySpace::SM` 且模板 `sm_memory_size=0` 时必须抛出错误；当 `space=MemorySpace::LM` 且模板 `lm_memory_size=0` 时同理。

## 测试

- 测试文件：[`test/include/npu_demo/test_kernel_context.py`](../../../test/include/npu_demo/test_kernel_context.py)
- 执行命令：`pytest -q test/include/npu_demo/test_kernel_context.py`
- 测试目标：
  - 验证 `KernelContext` 的 id/count accessor 能返回预置值。
  - 验证 `KernelContext.get_dynamic_memory<T>(MemorySpace::TSM)` 返回 `Memory<T>`，并固定 `shape/stride/space`。
  - 验证 `KernelContext.get_dynamic_memory<T>(MemorySpace::TLM)` 返回 `Memory<T>`，并固定 `shape/stride/space`。
  - 验证 `KernelContext.get_dynamic_memory<T>(MemorySpace::SM)` 在 `sm_memory_size=0` 时抛错并包含关键错误信息。
  - 验证 `KernelContext.get_dynamic_memory<T>(MemorySpace::LM)` 在 `lm_memory_size=0` 时抛错并包含关键错误信息。
- 功能与用例清单：
  - NPU-DEMO-KC-001：`KernelContext` 在预置 `block_id=1/block_num=6/thread_id=3/thread_num=8/subthread_id=0/subthread_num=1` 场景下返回对应值。（`test_npu_demo_kernel_context_exposes_id_and_count_accessors`）
  - NPU-DEMO-KC-002：`KernelContext.get_dynamic_memory<float>(MemorySpace::TSM)` 返回 `Memory<float>`，`space=TSM`，`shape=[24576]`，`stride=[1]`。（`test_npu_demo_kernel_context_returns_typed_tsm_memory`）
  - NPU-DEMO-KC-003：`KernelContext.get_dynamic_memory<float>(MemorySpace::TLM)` 返回 `Memory<float>`，`space=TLM`，`shape=[2048]`，`stride=[1]`。（`test_npu_demo_kernel_context_returns_typed_tlm_memory`）
  - NPU-DEMO-KC-004：`KernelContext.get_dynamic_memory<float>(MemorySpace::SM)` 因 `sm_memory_size=0` 抛错，错误消息包含 `sm_memory_size=0`。（`test_npu_demo_kernel_context_rejects_sm_when_size_zero`）
  - NPU-DEMO-KC-005：`KernelContext.get_dynamic_memory<float>(MemorySpace::LM)` 因 `lm_memory_size=0` 抛错，错误消息包含 `lm_memory_size=0`。（`test_npu_demo_kernel_context_rejects_lm_when_size_zero`）
