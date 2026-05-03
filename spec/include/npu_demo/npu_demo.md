# npu_demo

## 功能简介

定义 `npu_demo` 后端私有 include/runtime 规范，明确 `KernelContext` 的运行时视图语义、`KernelContext::barrier(visibility, scope)` 的同步契约、`npu_demo::launch<block, thread, subthread, shared_memory_size>(callee, args...)` 的后端承接位置，以及 `thread_id()`、`thread_num()`、`barrier(...)`、`get_dynamic_memory<Space>()` free helper 的活动上下文绑定行为。
同时定义 `include/npu_demo/npu_demo.h` 的 public function namespace 总合同：面向调用方的后端函数入口统一放在 `namespace npu_demo`，基础类型继续沿用 `include/api` 的公开类型边界。

- `KernelContext` 是由 `launch` 创建并绑定到当前线程的运行时上下文视图，不再是生成源码 body 签名中的显式参数。
- `thread_num()` / `block_num()` / `subthread_num()` 返回本次 launch 的 extent，而不是 target registry 的固定模板值；`shared_memory_size` 作为 launch metadata 以编译期模板参数承接。
- `include/npu_demo/npu_demo.h` 作为单入口头文件，需透传 `include/api/Memory.h` / `Dma.h` / `Kernel.h` / `Arch.h` / `cost/*.h` 的统一声明，并汇聚 `include/npu_demo/Core.h` / `Memory.h` / `Dma.h` / `Kernel.h` / `Arch.h` / `cost/*.h` 的后端实现。
- `npu_demo::add/sub/mul/...`、`npu_demo::launch(...)`、`npu_demo::build_contiguous_stride(...)`、`npu_demo::view(...)`、`npu_demo::alloc(...)`、`npu_demo::fill(...)`、`npu_demo::slice(...)`、`npu_demo::deslice(...)`、`npu_demo::transpose(...)`、`npu_demo::broadcast(...)` 以及 `npu_demo::cost::add/copy/...` 是 public function 的唯一成功消费方向；`detail` 只服务实现内部。

## API 列表

- `namespace npu_demo`
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status npu_demo::launch(Callable&& callee, Args&&... args)`
- `class npu_demo::KernelContext`
- `KernelContext::block_id() const -> long long`
- `KernelContext::block_num() const -> long long`
- `KernelContext::thread_id() const -> long long`
- `KernelContext::thread_num() const -> long long`
- `KernelContext::subthread_id() const -> long long`
- `KernelContext::subthread_num() const -> long long`
- `KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`
- `template <MemorySpace Space, typename T> KernelContext::get_dynamic_memory() const -> Memory<Space, T>`
- `npu_demo::thread_id() -> S_INT`
- `npu_demo::thread_num() -> S_INT`
- `npu_demo::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) -> void`
- `template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`
- `void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`
- `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::view(const Memory<Space, T>& source, long long offset, long long size, long long stride)`
- `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
- `namespace npu_demo::cost`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/npu_demo/npu_demo.md`](../../../spec/include/npu_demo/npu_demo.md)
- `功能实现`：[`include/npu_demo/npu_demo.h`](../../../include/npu_demo/npu_demo.h)、[`include/npu_demo/Memory.h`](../../../include/npu_demo/Memory.h)、[`include/npu_demo/Dma.h`](../../../include/npu_demo/Dma.h)、[`include/npu_demo/Arch.h`](../../../include/npu_demo/Arch.h)、[`include/npu_demo/Kernel.h`](../../../include/npu_demo/Kernel.h)、[`include/npu_demo/cost/Core.h`](../../../include/npu_demo/cost/Core.h)、[`include/npu_demo/cost/Dma.h`](../../../include/npu_demo/cost/Dma.h)、[`include/npu_demo/cost/Kernel.h`](../../../include/npu_demo/cost/Kernel.h)
- `test`：[`test/include/api/test_memory.py`](../../../test/include/api/test_memory.py)、[`test/include/api/test_dma.py`](../../../test/include/api/test_dma.py)、[`test/include/npu_demo/test_kernel_context.py`](../../../test/include/npu_demo/test_kernel_context.py)、[`test/include/npu_demo/test_runtime_launch.py`](../../../test/include/npu_demo/test_runtime_launch.py)、[`test/include/npu_demo/test_public_namespace.py`](../../../test/include/npu_demo/test_public_namespace.py)、[`test/include/api/test_arch.py`](../../../test/include/api/test_arch.py)、[`test/include/api/test_kernel.py`](../../../test/include/api/test_kernel.py)、`test/include/api/test_cost.py`、`test/include/npu_demo/test_cost.py`、[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)、[`test/target/test_registry.py`](../../../test/target/test_registry.py)

## 依赖

- [`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md)：统一 `launch` / `BarrierScope` / `barrier(visibility, scope)` 公开合同。
- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一 `Status` / `StatusCode` 语义。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：统一 `Memory<Space, T>`、`MemorySpace`、`MemoryFormat`、`npu_demo::build_contiguous_stride(...)` 与成员式 `view<T>` / `reshape` 语义。
- [`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md)：统一 `npu_demo::alloc/slice/deslice/transpose` 对 `Memory<Space, T>` 的公开职责。
- [`spec/include/api/Kernel.md`](../../../spec/include/api/Kernel.md)：统一 `Kernel` helper 公共接口职责。
- [`spec/include/api/cost/Core.md`](../../../spec/include/api/cost/Core.md)：统一 `npu_demo::cost::CostKind` 与 `S_INT` 成本返回语义。
- [`spec/include/api/cost/Dma.md`](../../../spec/include/api/cost/Dma.md)：统一 `npu_demo::cost::copy/slice/deslice` 的公共合同。
- [`spec/include/api/cost/Kernel.md`](../../../spec/include/api/cost/Kernel.md)：统一 `npu_demo::cost::add/matmul/...` 的公共合同。
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)：定义 `gen_kernel(target="npu_demo")` 的单入口源码与 compile-only 合同。
- [`spec/target/registry.md`](../../../spec/target/registry.md)：定义 `npu_demo` 的 launch 能力上限与片上空间容量来源。

## 目标

- 冻结 `include/api/Arch.h` 与 `include/npu_demo/Arch.h` 的职责边界：前者只声明公共接口，后者提供 `npu_demo` 的真实线程/同步实现。
- 冻结 `include/npu_demo/npu_demo.h` 的单入口聚合边界：对外只聚合 `Core / Memory / Dma / Arch / Kernel / cost` 六类公共接口及其后端实现，不再聚合公开 `Nn` 层。
- 明确后端 public function 的消费方向：调用方经 `npu_demo::` 访问函数入口，不能把 `npu_demo::detail` 或旧 `*_detail` 名称当作公开合同。
- 明确基础类型边界：`Status`、`StatusCode`、`Vector`、`Memory`、`MemorySpace` 等类型暂不整体迁入 `namespace npu_demo`。
- 冻结 `KernelContext` 的运行时视图合同，确保 launched body 读取到的是当前 launch 的 `block/thread/subthread` 维度与索引。
- 冻结 `npu_demo` P0 路径对 `launch + barrier + dynamic memory` 的最小成功子集，为后续实现/补测提供唯一稳定口径。
- 明确 `include/npu_demo/npu_demo.h` 也是 `gen_kernel(target="npu_demo")` 的唯一 compile-only 头文件：同一翻译单元里的 wrapper/body kernel 与 sibling cost function 只需 `#include "include/npu_demo/npu_demo.h"` 和 `using namespace npu_demo;` 即可消费 `launch`、活动上下文 free helper、`Memory` 与 `cost::*`。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本规范是后端私有 include/runtime 合同，不面向业务侧直接公开；业务侧只经由生成源码或后端封装间接消费。
- `include/npu_demo/npu_demo.h` 只聚合当前公共 API 与后端实现；`include/api/Nn.h` 不再属于可聚合的公开层。
- `include/npu_demo/npu_demo.h` 必须继续包含 `include/api/cost/*.h` 与 `include/npu_demo/cost/*.h`；`npu_demo::cost` 是当前公开子命名空间的一部分。
- `include/api/Arch.h` 只冻结名称、参数面与最小返回语义；真实线程启动、barrier 共享对象与运行时注入必须由 [`include/npu_demo/Arch.h`](../../../include/npu_demo/Arch.h) 承接。
- public function 必须位于 `namespace npu_demo`；基础类型与 enum 可以继续来自 `include/api` 全局公开类型。
- `npu_demo::detail` 只用于实现内部复用；公开测试、spec 示例、生成源码不得直接消费 `npu_demo::detail` 或 `*_detail` 名称。
- `include/npu_demo/npu_demo.h` 是唯一聚合入口，不新增第二套 target include。
- `Kernel` family 的公开 helper 名、模板顺序与参数顺序由 [`spec/include/api/Kernel.md`](../../../spec/include/api/Kernel.md) 冻结；`npu_demo` 只负责承接实现，不得重新发明旧 `Nn` 公共别名。
- `cost` family 的公开 helper 名、模板顺序与参数顺序由 [`spec/include/api/cost/Core.md`](../../../spec/include/api/cost/Core.md)、[`spec/include/api/cost/Dma.md`](../../../spec/include/api/cost/Dma.md)、[`spec/include/api/cost/Kernel.md`](../../../spec/include/api/cost/Kernel.md) 冻结；`npu_demo` 只负责承接默认实现，不得额外引入 `kind2/kind3` 或 target 私有成本命名。
- `gen_kernel(target="npu_demo")` 生成的完整源码若同时包含普通 kernel function 与 `_cost_DMA1_*` / `_cost_DMA2_*` / `_cost_DMA3_*` / `_cost_DMA4_*` / `_cost_MAC_*` / `_cost_VECTOR1_*` / `_cost_VECTOR2_*` sibling cost function，仍只允许依赖本头文件；不得额外要求包含 `include/npu_demo/cost/*.h`、`include/api/cost/*.h` 或额外 `using namespace npu_demo::cost;`。
- `KernelContext` 只表示当前 launched body 的运行时视图；生成源码不得再显式声明 `npu_demo::KernelContext& ctx` 参数，不要求公开默认构造、复制持久化或脱离 launch 生命周期独立使用。
- P0 launch 子集固定为：`block=1`、`subthread=1`、`shared_memory_size=0`、`2 <= thread <= registry.hardware.thread_num`；不支持的 extent 必须显式失败，禁止静默回退到单线程或忽略部分 extent。
- `block_num()` / `thread_num()` / `subthread_num()` 的公开语义是“当前 launch 值”；`target.registry` 中的 `block_num/thread_num/subthread_num` 只作为能力上限与容量校验基线，不再直接等于 launched body 中可见的当前值。
- `KernelContext::barrier(visibility, scope)` 在 `npu_demo` P0 仅支持 `visibility={BarrierVisibility::TSM, BarrierVisibility::TLM}` 且两者各出现一次，并要求 `scope=BarrierScope::BLOCK`；其他组合必须显式失败。
- `get_dynamic_memory<Space>()` 只覆盖当前 `npu_demo` 片上空间入口：`TSM/TLM1/TLM2/TLM3` 返回运行时视图，`SM/LM` 因容量为 `0` 必须显式失败，`GM` 不属于该接口输入域。
- 本文件不定义 DSL/front-end、MLIR lowering、codegen 细节，也不承诺超出 P0 launch 子集的多 block / 多 subthread runtime 行为。
## API详细说明

### `namespace npu_demo`

- api：`namespace npu_demo`
- 参数：无。
- 返回值：命名空间本身不提供运行时返回值；命名空间内公开函数、类型与子命名空间按本文件 `API 列表` 消费。
- 使用示例：

  ```cpp
  using namespace npu_demo;
  ```
- 功能说明：定义 `include/npu_demo/npu_demo.h` 聚合后的公开函数命名空间。
- 注意事项：public function 必须位于 `namespace npu_demo`；`npu_demo::cost` 是该命名空间下的公开子命名空间；`npu_demo::detail` 只允许实现内部使用，公开测试、spec 示例与生成源码不得直接消费 `npu_demo::detail` 或 `*_detail` 名称；基础类型继续沿用 `include/api` 层公开类型，不因函数迁移而整体改名。

### `template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status npu_demo::launch(Callable&& callee, Args&&... args)`

- api：`template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status npu_demo::launch(Callable&& callee, Args&&... args)`
- 参数：
  - `callee`：被调用函数名或符号引用，指定 call/launch 类操作的目标；类型 `Callable&&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `Args&&...`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
  static void kernel_body(long long* thread_nums) {
      thread_nums[npu_demo::thread_id()] = npu_demo::thread_num();
  }

  long long thread_nums[4] = {0, 0, 0, 0};
  Status status = npu_demo::launch<1, 4, 1, 0>(kernel_body, thread_nums);
  ```
- 功能说明：启动一次 `npu_demo` kernel 执行，并把当前 launch 上下文绑定为线程可见的活动上下文。
- 注意事项：公开源码形态固定为 `launch<block, thread, subthread, shared_memory_size>(callee, args...)`；`callee` 必须是函数对象或等价可调用对象，字符串 callee 不属于合法公开合同；生成源码中的 `callee` 对应 kernel body 不再显式声明 `npu_demo::KernelContext& ctx` 参数，运行时仍兼容手写 callee 显式接收 `npu_demo::KernelContext&` 首参；P0 下 `block` 与 `subthread` 固定为 `1`，`thread` 必须落在 `[2, registry.hardware.thread_num]`；失败时不得静默降级为单线程或无 barrier 的串行执行。

### `class npu_demo::KernelContext`

- api：`class npu_demo::KernelContext`
- 参数：无。
- 返回值：`npu_demo` 实例。
- 使用示例：

  ```cpp
  static void kernel_body(npu_demo::KernelContext& ctx) {
      long long tid = ctx.thread_id();
      long long tnum = ctx.thread_num();
      (void)tid;
      (void)tnum;
  }
  ```
- 功能说明：表示 launched body 内可见的运行时上下文视图。
- 注意事项：`KernelContext` 的公开职责是读取当前 launch 运行时视图，不是固定硬件模板常量容器；创建、注入与生命周期由 `npu_demo::launch<...>` 负责；脱离当前 launch 生命周期后的行为不作为稳定运行时承诺。

### `KernelContext::block_id() const -> long long`

- api：`KernelContext::block_id() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto bid = ctx.block_id();
```
- 功能说明：返回当前 launch 的 block 索引。
- 注意事项：返回值以 `0` 为起点，并满足 `0 <= block_id() < block_num()`；P0 路径固定为 `block_num()==1`。

### `KernelContext::block_num() const -> long long`

- api：`KernelContext::block_num() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto blocks = ctx.block_num();
```
- 功能说明：返回当前 launch 的 block extent。
- 注意事项：返回当前 launch 的 `block` 模板值，而不是 registry 固定模板值；P0 路径固定为 `1`。

### `KernelContext::thread_id() const -> long long`

- api：`KernelContext::thread_id() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto tid = ctx.thread_id();
```
- 功能说明：返回当前 launch 的 thread 索引。
- 注意事项：返回值以 `0` 为起点，并满足 `0 <= thread_id() < thread_num()`；不得返回与本次 launch 无关的固定常量。

### `KernelContext::thread_num() const -> long long`

- api：`KernelContext::thread_num() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto threads = ctx.thread_num();
```
- 功能说明：返回当前 launch 的 thread extent。
- 注意事项：返回本次 `launch<1, thread, 1, 0>` 中的 `thread` 模板值，而不是 registry 的固定上限值。

### `KernelContext::subthread_id() const -> long long`

- api：`KernelContext::subthread_id() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto sid = ctx.subthread_id();
```
- 功能说明：返回当前 launch 的 subthread 索引。
- 注意事项：返回值以 `0` 为起点，并满足 `0 <= subthread_id() < subthread_num()`；P0 路径固定为 `subthread_id()==0`。

### `KernelContext::subthread_num() const -> long long`

- api：`KernelContext::subthread_num() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto subthreads = ctx.subthread_num();
```
- 功能说明：返回当前 launch 的 subthread extent。
- 注意事项：返回当前 launch 的 `subthread` 模板值，而不是 registry 固定模板值；P0 路径固定为 `1`。

### `KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`

- api：`KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`
- 参数：
  - `visibility`：可见性标识，指定 barrier、符号或公开对象的可见范围；类型 `std::initializer_list<BarrierVisibility>`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `scope`：作用域标识，指定 barrier、注册、查找或名字分配的有效范围；类型 `BarrierScope`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`void`。
- 使用示例：

  ```cpp
  ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
  ```
- 功能说明：在当前 launch block 内执行一次带 `visibility / scope` 的同步。
- 注意事项：`visibility` 与 `scope` 都是必填；`npu_demo` P0 仅支持 `visibility={BarrierVisibility::TSM, BarrierVisibility::TLM}` 且两者各出现一次，并要求 `scope=BarrierScope::BLOCK`；空 `visibility`、重复项、缺失 `TSM/TLM`、混入非法 `BarrierVisibility` 枚举值，或 `scope=BarrierScope::THREAD` 都必须显式失败。

### `template <MemorySpace Space, typename T> KernelContext::get_dynamic_memory() const -> Memory<Space, T>`

- api：`template <MemorySpace Space, typename T> KernelContext::get_dynamic_memory() const -> Memory<Space, T>`
- 参数：无。
- 返回值：`Memory<Space, T>`。
- 使用示例：

  ```cpp
  Memory<TSM, float> tsm = ctx.get_dynamic_memory<TSM, float>();
  ```
- 功能说明：返回指定片上空间的运行时动态内存视图。
- 注意事项：`Space` 与元素类型 `T` 通过模板参数显式传入；P0 下 `TSM/TLM1/TLM2/TLM3` 返回固定容量视图，`SM/LM` 因容量为 `0` 必须显式失败，`GM` 不属于该接口输入域；返回对象的底层分配地址、所有权或跨 launch 复用策略不作为公开合同。

### `npu_demo::thread_id() -> S_INT`

- api：`npu_demo::thread_id() -> S_INT`
- 参数：无。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  S_INT tid = npu_demo::thread_id();
  ```
- 功能说明：通过当前 launch 活动上下文返回线程索引。
- 注意事项：语义与 `KernelContext::thread_id()` 一致；该 free helper 供生成代码直接调用，不要求生成源码显式持有 `KernelContext&`。

### `npu_demo::thread_num() -> S_INT`

- api：`npu_demo::thread_num() -> S_INT`
- 参数：无。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  S_INT tnum = npu_demo::thread_num();
  ```
- 功能说明：通过当前 launch 活动上下文返回线程总数。
- 注意事项：语义与 `KernelContext::thread_num()` 一致；该 free helper 供生成代码直接调用，不要求生成源码显式持有 `KernelContext&`。

### `npu_demo::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) -> void`

- api：`npu_demo::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) -> void`
- 参数：
  - `visibility`：可见性标识，指定 barrier、符号或公开对象的可见范围；类型 `std::initializer_list<BarrierVisibility>`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `scope`：作用域标识，指定 barrier、注册、查找或名字分配的有效范围；类型 `BarrierScope`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`void`。
- 使用示例：

  ```cpp
  npu_demo::barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
  ```
- 功能说明：通过当前 launch 活动上下文执行一次 block-scope 同步。
- 注意事项：参数合同与 `KernelContext::barrier(...)` 一致；该 free helper 供生成代码直接调用，不要求生成源码显式持有 `KernelContext&`。

### `template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`

- api：`template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`
- 参数：无。
- 返回值：`DynamicMemoryRef<Space>`。
- 使用示例：

  ```cpp
  Memory<TSM, float> tsm = npu_demo::get_dynamic_memory<TSM>();
  ```
- 功能说明：通过当前 launch 活动上下文返回指定片上空间的动态内存代理。
- 注意事项：`Space` 通过模板参数显式传入；元素类型由赋值目标的 `Memory<Space, T>` 决定；可用空间与失败边界与 `KernelContext::get_dynamic_memory<Space, T>()` 一致。

### `void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`

- api：`void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`
- 参数：
  - `shape`：输入形状数组；类型 `const long long*`；调用方必须提供至少 `rank` 个元素；各维度必须为正整数。
  - `rank`：形状维度数量；类型 `unsigned long long`；调用方必须显式提供；`rank=0` 不作为稳定输入。
  - `out_stride`：输出 stride 数组；类型 `long long*`；调用方必须提供至少 `rank` 个可写元素。
- 返回值：`void`。
- 使用示例：

  ```cpp
  long long shape[2] = {2, 3};
  long long stride[2] = {0, 0};
  npu_demo::build_contiguous_stride(shape, 2, stride);
  ```
- 功能说明：按行优先连续布局为指定形状生成 stride。
- 注意事项：该接口只生成连续 stride，不分配内存；`shape` 与 `out_stride` 必须指向有效数组，且二者长度不得小于 `rank`。

### `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::view(const Memory<Space, T>& source, long long offset, long long size, long long stride)`

- api：`template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::view(const Memory<Space, T>& source, long long offset, long long size, long long stride)`
- 参数：
  - `source`：源 `Memory` 视图；类型 `const Memory<Space, T>&`；调用方必须显式提供。
  - `offset`：一维起始偏移；类型 `long long`；必须落在 `source` 的线性可访问范围内。
  - `size`：一维视图元素数；类型 `long long`；必须为正整数。
  - `stride`：一维视图步长；类型 `long long`；必须为正整数。
- 返回值：`Memory<Space, T>`。
- 使用示例：

  ```cpp
  Memory<GM, float> row = npu_demo::view(line, 1, 2, 1);
  ```
- 功能说明：为一维 `Memory` 构造子视图。
- 注意事项：该 free helper 只承接当前一维公开子集；更完整的多维 `view` 语义由 `Memory::view<ViewT>(offset, size, stride)` 成员接口定义。

### `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`

- api：`template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- 参数：
  - `shape`：目标 memory 的形状列表；类型 `std::initializer_list<long long>`；调用方必须显式提供；元素必须为正整数。
  - `stride`：目标 memory 的 stride 列表；类型 `std::initializer_list<long long>`；调用方必须显式提供；长度必须与 `shape` 一致。
  - `format`：内存布局格式；类型 `MemoryFormat`；默认值 `MemoryFormat::Norm`。
- 返回值：`Memory<Space, T>`。
- 使用示例：

  ```cpp
  auto tile = npu_demo::alloc<TSM, float>({2}, {1}, MemoryFormat::Norm);
  ```
- 功能说明：构造指定空间、元素类型、形状、stride 与格式的 `Memory` 视图。
- 注意事项：该接口只承接当前后端公开分配入口；真实所有权和底层缓冲区策略由后端实现决定，不作为额外公开合同。

### `template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`

- api：`template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `const T&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
  auto tile = npu_demo::alloc<TSM, float>({2}, {1}, MemoryFormat::Norm);
  Status status = npu_demo::fill(tile, 0.0f);
  ```
- 功能说明：把 `value` 写入 `target` 覆盖范围。
- 注意事项：输入 memory、dtype 与 value 类型必须符合 DMA operation 合同；非法组合必须稳定返回失败状态。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- 参数：
  - `target`：目标 memory；类型 `Memory<TargetSpace, T>&`；承接切片结果。
  - `source`：源 memory；类型 `const Memory<SourceSpace, T>&`；提供读取数据。
  - `offset`：切片起点；类型 `const Vector&`；rank 必须与 `source` / `target` 可承接维度一致。
  - `size`：切片大小；类型 `const Vector&`；rank 必须与 `offset` 一致。
  - `stride`：切片步长；类型 `const Vector&`；rank 必须与 `offset` 一致。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
  Status status = npu_demo::slice(tile, line, Vector{1}, Vector{2}, Vector{1});
  ```
- 功能说明：从 `source` 按 `offset/size/stride` 读取子区域并写入 `target`。
- 注意事项：输入 memory、offset、size、stride 和 dtype 必须符合 DMA operation 合同；非法组合必须稳定返回失败状态。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- 参数：
  - `target`：目标 memory；类型 `Memory<TargetSpace, T>&`；承接写回结果。
  - `source`：源 memory；类型 `const Memory<SourceSpace, T>&`；提供待写回数据。
  - `offset`：写回起点；类型 `const Vector&`；rank 必须与 `target` / `source` 可承接维度一致。
  - `size`：写回区域大小；类型 `const Vector&`；rank 必须与 `offset` 一致。
  - `stride`：写回步长；类型 `const Vector&`；rank 必须与 `offset` 一致。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
  Status status = npu_demo::deslice(target, tile, Vector{1}, Vector{2}, Vector{1});
  ```
- 功能说明：把 `source` 按 `offset/size/stride` 写回到 `target` 的子区域。
- 注意事项：输入 memory、offset、size、stride 和 dtype 必须符合 DMA operation 合同；非法组合必须稳定返回失败状态。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `Memory<TargetSpace, TargetType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, SourceType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `perm`：维度排列序列，定义输出维度从输入维度读取的顺序；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
  Status status = npu_demo::transpose(transposed, matrix, Vector{1, 0});
  ```
- 功能说明：按 `perm` 将 `source` 转置到 `target`。
- 注意事项：输入 shape、dtype、space 与 `perm` 必须符合 transpose operation 合同；`perm` 必须是源 rank 的有效排列；非法组合必须稳定返回失败状态。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `Memory<TargetSpace, TargetType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, SourceType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
  Status status = npu_demo::broadcast<TSM, TSM, float, float>(target, source);
  ```
- 功能说明：按广播规则把 `source` 写入 `target`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定返回失败状态。

### `namespace npu_demo::cost`

- api：`namespace npu_demo::cost`
- 参数：无。
- 返回值：命名空间本身不提供运行时返回值；命名空间内 helper 按 `spec/include/api/cost/*.md` 消费。
- 使用示例：

  ```cpp
  S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::VECTOR1>(out, lhs, rhs);
  S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::DMA1>(tile, source);
  ```
- 功能说明：承接 `npu_demo` 后端的公开成本 helper 子命名空间。
- 注意事项：`npu_demo::cost` 是当前公开子命名空间；生成源码可在 `using namespace npu_demo;` 后使用 `cost::...`；不得引入 `kind2/kind3` 或 target 私有成本命名；`dsl_cost_run(...)` 的 DMA 聚合不得依赖跨文件 `npu_demo::cost::detail` 非公开状态。

## 测试

- 测试文件：
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/include/api/test_arch.py`
  - `test/include/api/test_dma.py`
  - `test/include/api/test_memory.py`
  - `test/include/npu_demo/test_kernel_context.py`
  - `test/include/npu_demo/test_cost.py`
  - `test/include/npu_demo/test_public_namespace.py`
  - `test/include/npu_demo/test_runtime_launch.py`
  - `test/target/test_registry.py`
- 执行命令：
  - `pytest -q test/include/api/test_memory.py test/include/api/test_dma.py`
  - `pytest -q test/include/api/test_arch.py`
  - `pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py`
  - `pytest -q test/include/npu_demo/test_cost.py`
  - `pytest -q test/include/npu_demo/test_public_namespace.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tuner_cost or cost_function or npu_demo"`
  - `pytest -q test/target/test_registry.py -k "npu_demo and launch"`

### 测试目标

- 验证 `spec/include/npu_demo/npu_demo.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证公开执行入口的返回值、输出或状态变化符合预期。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-001 | 公开入口 | 锁定 `include/api/Arch.h` 的公开 launch/barrier 接口面。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_include_api_arch_exports_public_launch_and_scope_contract`。 | 公开入口在“锁定 `include/api/Arch.h` 的公开 launch/barrier 接口面。”场景下可导入、构造、注册或按名称发现。 | `test_include_api_arch_exports_public_launch_and_scope_contract` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-002 | 执行结果 | 锁定 `KernelContext` 的 `block/thread/subthread` 查询返回当前 launch 值。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_npu_demo_kernel_context_runtime_view_tracks_launch_extent`。 | 命令返回码、输出、执行结果或状态变更体现“锁定 `KernelContext` 的 `block/thread/subthread` 查询返回当前 launch 值。”场景。 | `test_npu_demo_kernel_context_runtime_view_tracks_launch_extent` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-003 | 边界/异常 | 锁定 barrier 的 `visibility / scope` 参数合同。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_npu_demo_kernel_context_barrier_requires_visibility_and_block_scope`。 | “锁定 barrier 的 `visibility / scope` 参数合同。”场景按公开错误语义失败或被拒绝。 | `test_npu_demo_kernel_context_barrier_requires_visibility_and_block_scope` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-004 | 边界/异常 | 锁定 `block!=1`、`subthread!=1`、`thread<2` 或 `thread>8` 的显式失败边界。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_npu_demo_launch_rejects_unsupported_extent_without_fallback`。 | “锁定 `block!=1`、`subthread!=1`、`thread<2` 或 `thread>8` 的显式失败边界。”场景按公开错误语义失败或被拒绝。 | `test_npu_demo_launch_rejects_unsupported_extent_without_fallback` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-005 | 公开入口 | 锁定 `npu_demo::` public function 最小正向消费。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_npu_demo_public_namespace_smoke_compiles_vector_kernel_and_launch`。 | 公开入口在“锁定 `npu_demo::` public function 最小正向消费。”场景下可导入、构造、注册或按名称发现。 | `test_npu_demo_public_namespace_smoke_compiles_vector_kernel_and_launch` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-006 | 公开入口 | 锁定 `Memory/Dma` public function 只通过 `npu_demo::` 正向消费，未限定的全局 helper 不作为成功路径。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_npu_demo_public_namespace_memory_dma_helpers`。 | 公开入口在“锁定 `Memory/Dma` public function 只通过 `npu_demo::` 正向消费，未限定的全局 helper 不作为成功路径。”场景下可导入、构造、注册或按名称发现。 | `test_npu_demo_public_namespace_memory_dma_helpers` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-007 | 生成/编译 | 锁定 `include/npu_demo/npu_demo.h` 对 `gen_kernel` 输出的 wrapper/body kernel + sibling cost function 模块仍是单入口 compile-only 头文件。 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_cost_function_module`。 | 生成源码、IR 文本或编译结果体现“锁定 `include/npu_demo/npu_demo.h` 对 `gen_kernel` 输出的 wrapper/body kernel + sibling cost function 模块仍是单入口 compile-only 头文件。”场景。 | `test_gen_kernel_compiles_npu_demo_cost_function_module` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-008 | 公开入口 | 锁定 registry 的 `arch.launch` / `arch.barrier` 能力开关与 `thread_num=8` 上限语义。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_npu_demo_supports_launch_and_barrier_caps`。 | 公开入口在“锁定 registry 的 `arch.launch` / `arch.barrier` 能力开关与 `thread_num=8` 上限语义。”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_npu_demo_supports_launch_and_barrier_caps` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-009 | 边界/异常 | 锁定 cost DMA include 不依赖跨文件非公开 detail 聚合状态。 | 读取公开 include 文本。 | 运行 `test_npu_demo_cost_dma_has_no_cross_file_detail_accumulator`。 | `include/npu_demo/cost/Core.h` 不承载 DMA 聚合状态，`include/npu_demo/cost/Dma.h` 不包含或调用该非公开状态。 | `test_npu_demo_cost_dma_has_no_cross_file_detail_accumulator` |
