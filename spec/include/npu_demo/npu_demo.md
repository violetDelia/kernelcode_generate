# npu_demo

## 功能简介

定义 `npu_demo` 后端私有 include/runtime 规范，冻结 `KernelContext` 的运行时视图语义、`KernelContext::barrier(visibility, scope)` 的同步契约、`npu_demo::launch<block, thread, subthread>(callee, args...)` 的后端承接位置，以及 `get_dynamic_memory<T>(space)` 的片上内存入口行为。

- `KernelContext` 是由 `launch` 注入到 kernel body 的运行时上下文视图，不再是固定常量容器。
- `thread_num()` / `block_num()` / `subthread_num()` 返回本次 launch 的 extent，而不是 target registry 的固定模板值。
- `include/npu_demo/npu_demo.h` 作为单入口头文件，需透传 `include/api/Memory.h` / `Dma.h` / `Nn.h` / `Arch.h` 的统一声明，并汇聚 `include/npu_demo/Core.h` / `Memory.h` / `Dma.h` / `Nn.h` / `Arch.h` 的后端实现。

## 文档信息

- 创建者：`jcc你莫辜负`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/include/npu_demo/npu_demo.md`](../../../spec/include/npu_demo/npu_demo.md)
- `功能实现`：[`include/npu_demo/npu_demo.h`](../../../include/npu_demo/npu_demo.h)、[`include/npu_demo/Arch.h`](../../../include/npu_demo/Arch.h)
- `test`：[`test/include/npu_demo/test_kernel_context.py`](../../../test/include/npu_demo/test_kernel_context.py)、[`test/include/api/test_arch.py`](../../../test/include/api/test_arch.py)、[`test/target/test_target_registry.py`](../../../test/target/test_target_registry.py)

## 依赖

- [`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md)：统一 `launch` / `BarrierScope` / `barrier(visibility, scope)` 公开合同。
- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一 `Status` / `StatusCode` 语义。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：统一 `Memory<T>`、`MemorySpace`、`MemoryFormat` 语义。
- [`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md)：统一 `view/slice/deslice` 对 `Memory<T>` 的公开职责。
- [`spec/include/api/Nn.md`](../../../spec/include/api/Nn.md)：统一 `add` 等逐元素接口职责。
- [`spec/target/registry.md`](../../../spec/target/registry.md)：定义 `npu_demo` 的 launch 能力上限与片上空间容量来源。

## 目标

- 冻结 `include/api/Arch.h` 与 `include/npu_demo/Arch.h` 的职责边界：前者只声明公共接口，后者承接 `npu_demo` 的真实线程/同步实现。
- 冻结 `KernelContext` 的运行时视图合同，确保 launched body 读取到的是当前 launch 的 `block/thread/subthread` 维度与索引。
- 冻结 `npu_demo` P0 路径对 `launch + barrier + dynamic memory` 的最小成功子集，为后续实现/补测提供唯一稳定口径。

## 限制与边界

- 本规范是后端私有 include/runtime 合同，不面向业务侧直接公开；业务侧只经由生成源码或后端封装间接消费。
- `include/api/Arch.h` 只冻结名称、参数面与最小返回语义；真实线程启动、barrier 共享对象与运行时注入必须由 [`include/npu_demo/Arch.h`](../../../include/npu_demo/Arch.h) 承接。
- `KernelContext` 只表示当前 launched body 的运行时视图；不要求公开默认构造、复制持久化或脱离 launch 生命周期独立使用。
- P0 launch 子集固定为：`block=1`、`subthread=1`、`2 <= thread <= registry.hardware.thread_num`；不支持的 extent 必须显式失败，禁止静默回退到单线程或忽略部分 extent。
- `block_num()` / `thread_num()` / `subthread_num()` 的公开语义是“当前 launch 值”；`target.registry` 中的 `block_num/thread_num/subthread_num` 只作为能力上限与容量校验基线，不再直接等于 launched body 中可见的当前值。
- `KernelContext::barrier(visibility, scope)` 在 `npu_demo` P0 仅支持 `visibility={MemorySpace::TSM, MemorySpace::TLM}` 且两者各出现一次，并要求 `scope=BarrierScope::BLOCK`；其他组合必须显式失败。
- `get_dynamic_memory<T>(space)` 只覆盖当前 `npu_demo` 片上空间入口：`TSM/TLM` 返回运行时视图，`SM/LM` 因容量为 `0` 必须显式失败，`GM` 不属于该接口输入域。
- 本文件不定义 DSL/front-end、MLIR lowering、codegen 细节，也不承诺超出 P0 launch 子集的多 block / 多 subthread runtime 行为。

## 公开接口

### `npu_demo::launch<block, thread, subthread>(callee, args...)`

功能说明：

- 启动一次 `npu_demo` kernel 执行，并把当前 launch 上下文注入给 `callee`。
- `callee` 对应的 kernel body 必须以 `npu_demo::KernelContext&` 作为首个参数。

参数说明：

- `block (template int)`：编译期 block extent。
- `thread (template int)`：编译期 thread extent。
- `subthread (template int)`：编译期 subthread extent。
- `callee (callable)`：kernel body 对应的函数对象。
- `args...`：按原顺序转发给 `callee` 的 kernel 参数。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

static void add_barrier_body(
    npu_demo::KernelContext& ctx,
    const Memory<float>& lhs,
    const Memory<float>& rhs,
    Memory<float>& out) {
    long long tid = ctx.thread_id();
    (void)tid;
    ctx.barrier({MemorySpace::TSM, MemorySpace::TLM}, BarrierScope::BLOCK);
}

Status status = npu_demo::launch<1, 4, 1>(add_barrier_body, lhs, rhs, out);
```

注意事项：

- 公开源码形态固定为 `launch<block, thread, subthread>(callee, args...)`；不得回退为字符串 callee 或运行期 extent 位置参数。
- `callee` 必须是函数对象或等价可调用对象；`"add_barrier_body"` 之类字符串不属于合法公开合同。
- `launch` 必须把同一 block 内线程绑定到同一个 barrier 共享对象上，使 `ctx.barrier(...)` 真正同步本次 launch 的参与线程。
- P0 下 `block` 与 `subthread` 固定为 `1`，`thread` 必须落在 `[2, registry.hardware.thread_num]`；超出能力或不属于 P0 子集时必须显式失败。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`StatusCode::kOk` 表示 launch 请求已被承接；非 `kOk` 表示失败。
- 限制条件：失败时不得静默降级为单线程或无 barrier 的串行执行。

### `npu_demo::KernelContext`

功能说明：

- 表示 launched body 内可见的运行时上下文视图。
- 提供 `block/thread/subthread` 的索引与 extent 查询、片上动态内存入口，以及 block-scope barrier。

参数说明：

- 无参数。

使用示例：

```cpp
static void kernel_body(npu_demo::KernelContext& ctx) {
    long long tid = ctx.thread_id();
    long long tnum = ctx.thread_num();
    (void)tid;
    (void)tnum;
}
```

注意事项：

- `KernelContext` 的公开职责是“读取当前 launch 运行时视图”；不是固定硬件模板常量容器。
- `KernelContext` 的创建、注入与生命周期由 `npu_demo::launch<...>` 负责。

返回与限制：

- 返回类型：`npu_demo::KernelContext`。
- 返回语义：承载当前 launch 的上下文信息。
- 限制条件：脱离当前 launch 生命周期后的行为不在本规范覆盖范围内。

#### `block_id()` / `block_num()` / `thread_id()` / `thread_num()` / `subthread_id()` / `subthread_num()`

功能说明：

- 返回当前 launch 的 block/thread/subthread 索引与 extent。

参数说明：

- 无参数。

使用示例：

```cpp
long long bid = ctx.block_id();
long long bnum = ctx.block_num();
long long tid = ctx.thread_id();
long long tnum = ctx.thread_num();
```

注意事项：

- 返回值语义统一为 `int64`，当前以 `long long` 表达。
- `block_id()` / `thread_id()` / `subthread_id()` 必须是以 `0` 为起点的当前执行索引，分别满足 `0 <= id < num`。
- `block_num()` / `thread_num()` / `subthread_num()` 必须返回当前 launch 的 extent，而不是 registry 的固定模板值。
- `npu_demo` 的 P0 路径固定为 `block_num()==1`、`subthread_num()==1`，`thread_num()` 返回本次 `launch<1, thread, 1>` 中的 `thread` 模板值。

返回与限制：

- 返回类型：`long long`（语义等同 `int64`）。
- 返回语义：当前 launch 上下文对应的索引或 extent。
- 限制条件：不得继续返回固定 `block_id=1`、`thread_id=3`、`thread_num=8` 之类与 launch 无关的常量模板值。

#### `barrier(visibility, scope)`

功能说明：

- 在当前 launch block 内执行一次带 `visibility / scope` 的同步。

参数说明：

- `visibility (std::initializer_list<MemorySpace>)`：需要保证可见性的片上空间列表。
- `scope (BarrierScope)`：同步范围。

使用示例：

```cpp
ctx.barrier({MemorySpace::TSM, MemorySpace::TLM}, BarrierScope::BLOCK);
```

注意事项：

- `visibility` 与 `scope` 都是必填；不得退化为无参 barrier。
- `npu_demo` P0 仅支持 `visibility={TSM, TLM}` 且两者各出现一次，并要求 `scope=BarrierScope::BLOCK`。
- 空 `visibility`、重复 space、缺失 `TSM/TLM`、混入 `SM/LM/GM`，或 `scope=BarrierScope::THREAD` 都必须显式失败。

返回与限制：

- 返回类型：`void`。
- 返回语义：对当前 block 的参与线程执行一次同步。
- 限制条件：不得把非法参数静默当作“无 barrier”或“自动修正后的 barrier”。

#### `get_dynamic_memory<T>(MemorySpace space)`

功能说明：

- 返回指定片上空间的运行时动态内存视图，元素类型由模板参数 `T` 指定。

参数说明：

- `T`：元素类型模板参数。
- `space (MemorySpace)`：目标片上空间。

使用示例：

```cpp
Memory<float> tsm = ctx.get_dynamic_memory<float>(MemorySpace::TSM);
Memory<float> tlm = ctx.get_dynamic_memory<float>(MemorySpace::TLM);
```

注意事项：

- 模板参数只表达元素类型；`space` 必须显式通过 `MemorySpace` 枚举值传入。
- P0 下 `MemorySpace::TSM` 与 `MemorySpace::TLM` 分别返回 `shape=[24576]`、`shape=[2048]`，`stride=[1]`，`format=MemoryFormat::Norm`，`space` 与输入一致的 `Memory<T>`。
- `MemorySpace::SM` / `MemorySpace::LM` 因容量为 `0` 必须显式失败；错误消息或诊断至少需要指向对应的 `*_memory_size=0` 约束。
- `MemorySpace::GM` 不属于该接口输入域。

返回与限制：

- 返回类型：`Memory<T>`。
- 返回语义：返回当前 launch 可见的片上空间视图。
- 限制条件：本规范不要求公开底层分配地址、所有权或跨 launch 复用策略。

## 测试

- 测试文件：[`test/include/api/test_arch.py`](../../../test/include/api/test_arch.py)、[`test/include/npu_demo/test_kernel_context.py`](../../../test/include/npu_demo/test_kernel_context.py)、[`test/target/test_target_registry.py`](../../../test/target/test_target_registry.py)
- 执行命令：
  - `pytest -q test/include/api/test_arch.py`
  - `pytest -q test/include/npu_demo/test_kernel_context.py -k "runtime or barrier"`
  - `pytest -q test/target/test_target_registry.py -k "npu_demo and launch"`
- 测试目标：
  - 验证 `include/api/Arch.h` 与 `include/npu_demo/Arch.h` 的职责边界。
  - 验证 `KernelContext` 查询返回当前 launch 值，而非旧的固定模板常量。
  - 验证 `ctx.barrier({TSM, TLM}, BarrierScope::BLOCK)` 的参数合同与显式失败边界。
  - 验证 `npu_demo::launch<1, thread, 1>(...)` 的函数对象 callee、launch extent 校验与 `thread_num()` 运行时视图。
  - 验证 `get_dynamic_memory<T>(TSM/TLM)` 返回固定容量视图，`SM/LM` 因零容量显式失败。
- 功能与用例清单：
  - `test_include_api_arch_exports_public_launch_and_scope_contract`：锁定 `include/api/Arch.h` 的公开 launch/barrier 接口面。
  - `test_npu_demo_kernel_context_runtime_view_tracks_launch_extent`：锁定 `KernelContext` 的 `block/thread/subthread` 查询返回当前 launch 值。
  - `test_npu_demo_kernel_context_barrier_requires_visibility_and_block_scope`：锁定 barrier 的 `visibility / scope` 参数合同。
  - `test_npu_demo_launch_rejects_unsupported_extent_without_fallback`：锁定 `block!=1`、`subthread!=1`、`thread<2` 或 `thread>8` 的显式失败边界。
  - `test_target_registry_npu_demo_supports_launch_and_barrier_caps`：锁定 registry 的 `arch.launch` / `arch.barrier` 能力开关与 `thread_num=8` 上限语义。
