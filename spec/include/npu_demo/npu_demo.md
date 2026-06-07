# npu_demo

## 功能简介

定义 `npu_demo` 后端私有 include/runtime 规范，明确 opaque `KernelContext` 的传递语义、`npu_demo::barrier(visibility, scope)` 的同步契约、`npu_demo::launch<block, thread, subthread, shared_memory_size, name>(ctx, args...)` 的后端承接位置，以及 `thread_id()`、`thread_num()`、`barrier(...)`、`get_dynamic_memory<Space>()` free helper 的活动上下文绑定行为。
同时定义 `include/npu_demo/npu_demo.h` 的 public function namespace 总合同：面向调用方的后端函数入口统一放在 `namespace npu_demo`，基础类型继续沿用 `include/api` 的公开类型边界。

- `KernelContext` 是 host wrapper 显式物化并传入 launch/body/helper 链路的 opaque context；运行时查询、同步与动态内存访问不作为成员 API 暴露。
- `thread_num()` / `block_num()` / `subthread_num()` 返回本次 launch 的 extent，而不是 target registry 的固定模板值；`shared_memory_size` 作为 launch metadata 以编译期模板参数承接。
- `include/npu_demo/npu_demo.h` 作为单入口头文件，需透传 `include/api/Memory.h` / `Dma.h` / `Kernel.h` / `Arch.h` / `Trance.h` / `cost/*.h` 的统一声明，并汇聚 `include/npu_demo/Core.h` / `Memory.h` / `Dma.h` / `Kernel.h` / `Arch.h` / `Trance.h` / `cost/*.h` 的后端实现。
- `npu_demo::add/sub/mul/truediv/min/max/...`、`npu_demo::launch(...)`、`npu_demo::block_id()`、`npu_demo::build_contiguous_stride(...)`、`npu_demo::alloc(...)`、`npu_demo::fill(...)`、`npu_demo::slice(...)`、`npu_demo::deslice(...)`、`npu_demo::transpose(...)`、`npu_demo::store(...)`、`npu_demo::load(...)`、`npu_demo::broadcast(...)`、`npu_demo::DmaRing`、`npu_demo::make_ring(...)` 以及 `npu_demo::cost::add/min/max/copy/slice/deslice/...` 是 public function/type 的唯一成功消费方向；DMA / Kernel helper 均为 context-first 形态，`detail` 只服务实现内部。
- `TRANCE` block 目录模式下，`npu_demo::launch(...)` 每个 block worker 必须写入独立 `block_XXXX.log`，文件实现由 trace 模块公开入口承接。

## API 列表

- `namespace npu_demo`
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status npu_demo::launch(Context& ctx, Args&&... args)`
- `class npu_demo::KernelContext`
- `npu_demo::KernelContext::KernelContext()`
- `npu_demo::block_id() -> S_INT`
- `npu_demo::thread_id() -> S_INT`
- `npu_demo::thread_num() -> S_INT`
- `npu_demo::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) -> void`
- `template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`
- `void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`
- `template <MemorySpace Space, typename T, typename Context> Memory<Space, T> npu_demo::alloc(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename SlotT, typename BackingT> class npu_demo::DmaRing`
- `npu_demo::DmaRing.current() const -> Memory<Space, SlotT>`
- `npu_demo::DmaRing.advance() -> Memory<Space, SlotT>`
- `template <typename SlotT, MemorySpace Space, typename BackingT> DmaRing<Space, SlotT, BackingT> npu_demo::make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename T, typename Context> Status npu_demo::fill(Context& ctx, Memory<Space, T>& target, const T& value)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> Status npu_demo::slice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> Status npu_demo::deslice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status npu_demo::transpose(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status npu_demo::store(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status npu_demo::load(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status npu_demo::broadcast(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::min(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `namespace npu_demo::cost`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::slice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::deslice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::min(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::max(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/npu_demo/npu_demo.md`](../../../spec/include/npu_demo/npu_demo.md)
- `功能实现`：[`include/npu_demo/npu_demo.h`](../../../include/npu_demo/npu_demo.h)、[`include/npu_demo/Memory.h`](../../../include/npu_demo/Memory.h)、[`include/npu_demo/Dma.h`](../../../include/npu_demo/Dma.h)、[`include/npu_demo/Arch.h`](../../../include/npu_demo/Arch.h)、[`include/npu_demo/Trance.h`](../../../include/npu_demo/Trance.h)、[`include/npu_demo/Kernel.h`](../../../include/npu_demo/Kernel.h)、[`include/npu_demo/cost/Core.h`](../../../include/npu_demo/cost/Core.h)、[`include/npu_demo/cost/Dma.h`](../../../include/npu_demo/cost/Dma.h)、[`include/npu_demo/cost/Kernel.h`](../../../include/npu_demo/cost/Kernel.h)
- `test`：[`test/include/api/test_memory.py`](../../../test/include/api/test_memory.py)、[`test/include/api/test_dma.py`](../../../test/include/api/test_dma.py)、[`test/include/npu_demo/test_kernel_context.py`](../../../test/include/npu_demo/test_kernel_context.py)、[`test/include/npu_demo/test_runtime_launch.py`](../../../test/include/npu_demo/test_runtime_launch.py)、[`test/include/npu_demo/test_public_namespace.py`](../../../test/include/npu_demo/test_public_namespace.py)、[`test/include/api/test_arch.py`](../../../test/include/api/test_arch.py)、[`test/include/api/test_kernel.py`](../../../test/include/api/test_kernel.py)、`test/include/api/test_cost.py`、`test/include/npu_demo/test_cost.py`、[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)、[`test/target/test_registry.py`](../../../test/target/test_registry.py)

## 依赖

- [`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md)：统一 `launch` / `BarrierScope` / `barrier(visibility, scope)` 公开合同。
- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一 `Status` / `StatusCode` 语义。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：统一 `Memory<Space, T>`、`MemorySpace`、`MemoryFormat`、`npu_demo::build_contiguous_stride(...)` 与成员式 `view<T>` / `reshape` 语义。
- [`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md)：统一 `npu_demo::alloc/slice/deslice/transpose` 对 `Memory<Space, T>` 的公开职责，以及 `DmaRing` / `make_ring` runtime ring 合同。
- [`spec/include/api/Kernel.md`](../../../spec/include/api/Kernel.md)：统一 `Kernel` helper 公共接口职责。
- [`spec/include/api/Trance.md`](../../../spec/include/api/Trance.md)：统一 runtime trance sink、入口打印、参数打印和文件回退语义。
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
- 冻结 `npu_demo` block-only 路径对 `launch + barrier + dynamic memory` 的最小成功子集，为后续实现/补测提供唯一稳定口径。
- 明确 `include/npu_demo/npu_demo.h` 也是 `gen_kernel(target="npu_demo")` 的唯一 compile-only 头文件：同一翻译单元里的 wrapper/body kernel 与 sibling cost function 只需 `#include "include/npu_demo/npu_demo.h"` 和 `using namespace npu_demo;` 即可消费 `launch`、活动上下文 free helper、`Memory` 与 `cost::*`。
- 明确 `gen_kernel(target="npu_demo")` 生成的 multi-buffer ring 必须经 `npu_demo::make_ring<SlotT>(...)` 创建 runtime `DmaRing`，并使用 `.current()` / `.advance()` 成员接口访问 slot；不得直接调用 `npu_demo::detail` 或用固定零 offset view 替代 cursor ring。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本规范是后端私有 include/runtime 合同，不面向业务侧直接公开；业务侧只经由生成源码或后端封装间接消费。
- `include/npu_demo/npu_demo.h` 只聚合当前公共 API 与后端实现；`include/api/Nn.h` 不再属于可聚合的公开层。
- `include/npu_demo/npu_demo.h` 必须继续包含 `include/api/cost/*.h` 与 `include/npu_demo/cost/*.h`；`npu_demo::cost` 是当前公开子命名空间的一部分。
- `include/npu_demo/npu_demo.h` 必须继续包含 `include/api/Trance.h` 与 `include/npu_demo/Trance.h`；`TRANCE` 未开启时该聚合不得引入 runtime 日志副作用。
- `include/api/Arch.h` 只冻结名称、参数面与最小返回语义；真实线程启动、barrier 共享对象与运行时注入必须由 [`include/npu_demo/Arch.h`](../../../include/npu_demo/Arch.h) 承接。
- public function 必须位于 `namespace npu_demo`；基础类型与 enum 可以继续来自 `include/api` 全局公开类型。
- `npu_demo::detail` 只用于实现内部复用；公开测试、spec 示例、生成源码不得直接消费 `npu_demo::detail` 或 `*_detail` 名称。
- `include/npu_demo/npu_demo.h` 是唯一聚合入口，不新增第二套 target include。
- `Kernel` family 的公开 helper 名、模板顺序与参数顺序由 [`spec/include/api/Kernel.md`](../../../spec/include/api/Kernel.md) 冻结；`npu_demo` 只负责承接 context-first 实现，不得重新发明旧 `Nn` 公共别名；`min/max` 与其它 same-shape binary helper 一样在 `ctx` 后使用 out-first 参数顺序。
- `cost` family 的公开 helper 名、模板顺序与参数顺序由 [`spec/include/api/cost/Core.md`](../../../spec/include/api/cost/Core.md)、[`spec/include/api/cost/Dma.md`](../../../spec/include/api/cost/Dma.md)、[`spec/include/api/cost/Kernel.md`](../../../spec/include/api/cost/Kernel.md) 冻结；`npu_demo` 只负责承接默认实现，不得额外引入 `kind2/kind3` 或 target 私有成本命名；`cost::min/max` 必须与 `cost::add/sub/mul/truediv` 保持同一模板与参数形态。
- `gen_kernel(target="npu_demo")` 生成的完整源码若同时包含普通 kernel function 与 `_cost_DMA1_*` / `_cost_DMA2_*` / `_cost_DMA3_*` / `_cost_DMA4_*` / `_cost_MAC_*` / `_cost_VECTOR1_*` / `_cost_VECTOR2_*` sibling cost function，仍只允许依赖本头文件；不得额外要求包含 `include/npu_demo/cost/*.h`、`include/api/cost/*.h` 或额外 `using namespace npu_demo::cost;`。
- `gen_kernel(target="npu_demo")` 生成的 rank 1..8 layout 参数可使用 brace-list 绑定 `Vector`，形如 `{...} /*shape*/`、`{...} /*stride*/`、`{...} /*offset*/`、`{...} /*size*/`；rank >8 按公开错误失败。
- `gen_kernel(target="npu_demo")` 生成的 multi-buffer ring 必须使用 `npu_demo::make_ring<SlotT>(...)`、`.current()` 与 `.advance()`；不得把 ring current/advance 降级为固定 `{0}` offset view。
- `KernelContext` 是 context-first launch/body/helper 链路中的 opaque kernel context；host wrapper 负责默认构造，body 显式接收 `npu_demo::KernelContext& ctx` 首参，但运行时查询、同步与动态内存不走成员函数。
- block-only launch 子集固定为：`1 <= block <= registry.hardware.block_num`、`thread=1`、`subthread=1`、`shared_memory_size=0`；不支持的 extent 必须显式失败，禁止静默回退到单线程或忽略部分 extent。
- `thread_num()` 的公开语义是“当前 launch 值”；`target.registry` 中的 `block_num/thread_num/subthread_num` 只作为能力上限与容量校验基线，不再直接等于 launched body 中可见的当前值。
- `npu_demo::barrier(visibility, scope)` 在当前 block-only 子集仅支持 `visibility={BarrierVisibility::TSM, BarrierVisibility::TLM}` 且两者各出现一次，并要求 `scope=BarrierScope::BLOCK`；其他组合必须显式失败。
- `get_dynamic_memory<Space>()` 只覆盖当前 `npu_demo` 片上空间入口：`TSM/TLM1/TLM2/TLM3` 返回带可写 backing 的运行时视图，可继续通过 `Memory::view<T>(...)` 切成 typed tile 并被 `slice/fill` 等公开 helper 写入；`SM/LM` 因容量为 `0` 必须显式失败，`GM` 不属于该接口输入域。
- `TRANCE` 开启且 `KG_TRANCE_DIR_PATH` 非空时，`npu_demo::launch(...)` 必须先通过 `kernelcode::trance::prepare_block_trace_dir(KG_TRANCE_DIR_PATH)` 创建目录并清理旧 `block_*.log`，再在每个 block worker 内通过 `kernelcode::trance::ScopedBlockTranceSink(...)` 写入 header、launch template 和 forwarded args；`Arch.h` 不得直接拼路径、遍历目录或调用 trace detail helper。
- `TRANCE` block 文件模式必须生成 `dump_dir/<kernel name>/trance/block_0000.log`、`block_0001.log` 等实际 block 文件，不生成 `<entry>_trace.txt`、`<kernel name>_trace.txt` 或 `summary.log`。
- 本文件不定义 DSL/front-end、MLIR lowering 或 codegen 细节；多 thread / 多 subthread runtime 行为不属于本轮稳定成功子集。
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

### `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status npu_demo::launch(Context& ctx, Args&&... args)`

- api：`template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status npu_demo::launch(Context& ctx, Args&&... args)`
- 参数：
  - `ctx`：上下文对象；类型 `Context&`；无默认值，调用方必须显式提供；按引用传入，供 `name(ctx, args...)` 调用。
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `Args&&...`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
  static void kernel_body(npu_demo::KernelContext& ctx, long long* block_ids) {
      (void)ctx;
      block_ids[npu_demo::block_id()] = npu_demo::block_id();
  }

  npu_demo::KernelContext ctx;
  long long block_ids[2] = {-1, -1};
  Status status = npu_demo::launch<2, 1, 1, 0, kernel_body>(ctx, block_ids);
  ```
- 功能说明：启动一次 `npu_demo` kernel 执行，并把当前 launch 上下文绑定为线程可见的活动上下文。
- 注意事项：公开源码形态固定为 `launch<block, thread, subthread, shared_memory_size, name>(ctx, args...)`；`name` 必须是可用 `Context&` 首参与 `args...` 调用的函数对象或等价可调用对象，字符串 callee 不属于合法公开合同；不保留无 ctx callable fallback；block-only 子集下 `block` 必须落在 `[1, registry.hardware.block_num]`，`thread` 固定为 `1`，`subthread` 固定为 `1`；失败时不得静默降级为单线程或无 barrier 的串行执行；`TRANCE` block 目录模式下，launch template/args 日志必须写入每个 block 文件。

### `class npu_demo::KernelContext`

- api：`class npu_demo::KernelContext`
- 参数：无。
- 返回值：`npu_demo` 实例。
- 使用示例：

  ```cpp
  static void kernel_body(npu_demo::KernelContext& ctx) {
      (void)ctx;
      S_INT tid = npu_demo::thread_id();
      S_INT tnum = npu_demo::thread_num();
  }
  ```
- 功能说明：表示可传入 npu_demo launch/body/helper 链路的 opaque kernel context。
- 注意事项：`KernelContext` 不公开运行时查询、同步或动态内存成员函数；创建、注入与生命周期由 host wrapper 和 `npu_demo::launch<...>` 负责；脱离当前 launch 生命周期后的行为不作为稳定运行时承诺。

### `npu_demo::block_id() -> S_INT`

- api：`npu_demo::block_id() -> S_INT`
- 参数：无。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  S_INT bid = npu_demo::block_id();
  ```
- 功能说明：通过当前 launch 活动上下文返回 block 索引。
- 注意事项：该 free helper 供生成代码直接调用，不要求生成源码通过 context 成员读取运行时索引。

### `npu_demo::thread_id() -> S_INT`

- api：`npu_demo::thread_id() -> S_INT`
- 参数：无。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  S_INT tid = npu_demo::thread_id();
  ```
- 功能说明：通过当前 launch 活动上下文返回线程索引。
- 注意事项：该 free helper 供生成代码直接调用，不要求生成源码通过 context 成员读取运行时索引。

### `npu_demo::thread_num() -> S_INT`

- api：`npu_demo::thread_num() -> S_INT`
- 参数：无。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  S_INT tnum = npu_demo::thread_num();
  ```
- 功能说明：通过当前 launch 活动上下文返回线程总数。
- 注意事项：该 free helper 供生成代码直接调用，不要求生成源码通过 context 成员读取运行时 extent。

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
- 注意事项：该 free helper 供生成代码直接调用，不要求生成源码通过 context 成员执行同步；当前 block-only 子集仅支持 `visibility={BarrierVisibility::TSM, BarrierVisibility::TLM}` 且两者各出现一次，并要求 `scope=BarrierScope::BLOCK`。

### `template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`

- api：`template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`
- 参数：无。
- 返回值：`DynamicMemoryRef<Space>`。
- 使用示例：

  ```cpp
  Memory<TSM, float> tsm = npu_demo::get_dynamic_memory<TSM>();
  ```
- 功能说明：通过当前 launch 活动上下文返回指定片上空间的动态内存代理。
- 注意事项：`Space` 通过模板参数显式传入；元素类型由赋值目标的 `Memory<Space, T>` 决定；可用空间、可写 backing 与失败边界由当前活动上下文和后端 free helper 统一收口。

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

### `npu_demo::alloc/fill/slice/deslice/transpose/store/load/broadcast`

- api：按本文件 `API 列表` 中的 context-first DMA helper 签名消费；详细参数、错误语义与 generated source brace-list-to-Vector 绑定以 [`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md) 为真源。
- 参数：`ctx` 为显式上下文首参，后续 `target/source/layout/value` 参数按 [`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md) 对应 API 定义。
- 返回值：`alloc` 返回 `Memory<Space, T>`；其余 DMA helper 返回 `Status`。
- 使用示例：

  ```cpp
  npu_demo::KernelContext ctx;
  auto tile = npu_demo::alloc<TSM, float>(ctx, {2}, {1}, MemoryFormat::Norm);
  Status filled = npu_demo::fill(ctx, tile, 0.0f);
  Status copied = npu_demo::slice(ctx, tile, source, {0}, {2}, {1});
  ```
- 功能说明：聚合并承接 `include/api/Dma.h` 中公开的 context-first DMA helper。
- 注意事项：`npu_demo::view` 自由函数不属于当前公开聚合 API；`view/reshape` 由 `Memory` 成员接口承接。

### `template <MemorySpace Space, typename SlotT, typename BackingT> class npu_demo::DmaRing`

- api：`template <MemorySpace Space, typename SlotT, typename BackingT> class npu_demo::DmaRing`
- 参数：模板参数 `Space` 为 backing 与 slot 所在 memory space；`SlotT` 为 slot 元素类型；`BackingT` 为 backing 元素类型。
- 返回值：类型定义；对象由 `npu_demo::make_ring(...)` 返回。
- 使用示例：

```cpp
unsigned char storage[128] = {};
Memory<TSM, unsigned char> backing(storage, {128}, {1});
auto ring = npu_demo::make_ring<float>(backing, 2, 64, {4, 4}, {4, 1});
```
- 功能说明：表示 runtime multi-buffer ring 对象，持有 backing、cursor 与单个 slot layout。
- 注意事项：公开方法只包含 `current()` 与 `advance()`；不公开 default constructor、cursor accessor、num accessor 或 offset accessor；copy / move constructor 与 assignment 不作为稳定 public API。

### `npu_demo::DmaRing.current() const -> Memory<Space, SlotT>`

- api：`npu_demo::DmaRing.current() const -> Memory<Space, SlotT>`
- 参数：无。
- 返回值：`Memory<Space, SlotT>`。
- 使用示例：

```cpp
Memory<TSM, float> current = ring.current();
```
- 功能说明：返回当前 cursor 对应的 typed slot view，不推进 cursor。
- 注意事项：返回 view 使用 `make_ring` 提供的 shape/stride/format，起始地址按 byte offset 计算。

### `npu_demo::DmaRing.advance() -> Memory<Space, SlotT>`

- api：`npu_demo::DmaRing.advance() -> Memory<Space, SlotT>`
- 参数：无。
- 返回值：`Memory<Space, SlotT>`。
- 使用示例：

```cpp
Memory<TSM, float> next = ring.advance();
```
- 功能说明：先推进 cursor，再返回推进后对应的 typed slot view。
- 注意事项：cursor 必须按 `num` 回绕；`advance()` 的返回值不是推进前 slot。

### `template <typename SlotT, MemorySpace Space, typename BackingT> DmaRing<Space, SlotT, BackingT> npu_demo::make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`

- api：`template <typename SlotT, MemorySpace Space, typename BackingT> DmaRing<Space, SlotT, BackingT> npu_demo::make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- 参数：
  - `backing`：一维 byte backing memory；类型 `Memory<Space, BackingT>&`；无默认值。
  - `num`：ring stage 数；类型 `S_INT`；必须为正整数。
  - `offset_bytes`：相邻 stage 的 byte 间距；类型 `S_INT`；必须大于等于单个 slot 的 byte span。
  - `shape`：单个 typed slot 的 shape；类型 `std::initializer_list<long long>`；rank 必须为 1..8。
  - `stride`：单个 typed slot 的 stride；类型 `std::initializer_list<long long>`；长度必须等于 rank。
  - `format`：slot memory format；类型 `MemoryFormat`；默认 `MemoryFormat::Norm`。
- 返回值：`DmaRing<Space, SlotT, BackingT>`。
- 使用示例：

```cpp
unsigned char storage[128] = {};
Memory<TSM, unsigned char> backing(storage, {128}, {1});
auto ring = npu_demo::make_ring<float>(backing, 2, 64, {4, 4}, {4, 1});
```
- 功能说明：根据 byte backing memory 创建 runtime DMA ring；shape/stride 描述单个 typed slot，offset_bytes 描述相邻 stage 的 byte 间距。
- 注意事项：factory 必须校验 backing 非空、一维 byte backing、rank、shape、stride、num、offset 与 backing 容量；普通 context-first DMA helper 的 layout 参数仍以 `Vector` 为真源，本 factory 的 initializer-list shape/stride 只服务 runtime ring 构造。

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

### `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::min/max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::min/max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：`ctx` 为显式上下文首参，`out`、`lhs`、`rhs` 的顺序、模板参数与 same-shape 约束以 [`spec/include/api/Kernel.md`](../../../spec/include/api/Kernel.md) 为真源。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
  Status status = npu_demo::max(ctx, out, lhs, rhs);
  ```
- 功能说明：聚合并承接 `include/api/Kernel.h` 中公开的逐元素 `min/max` helper。
- 注意事项：`include/npu_demo/npu_demo.h` 必须让公开命名空间可直接消费 `npu_demo::min/max`；不得要求调用方依赖 `npu_demo::detail` 或旧 `Nn` 公共别名。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::min/max(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::min/max(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：`out`、`lhs`、`rhs` 的顺序、模板参数与 `CostKind` 尾参约束以 [`spec/include/api/cost/Kernel.md`](../../../spec/include/api/cost/Kernel.md) 为真源。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  S_INT max_cost = npu_demo::cost::max<GM, float, float, VECTOR1>(out, lhs, rhs);
  ```
- 功能说明：聚合并承接 `include/api/cost/Kernel.h` 中公开的逐元素 `min/max` 成本 helper。
- 注意事项：`include/npu_demo/npu_demo.h` 必须让生成源码在 `using namespace npu_demo;` 后可直接消费 `cost::min/max`；不得引入额外 include、`using namespace npu_demo::cost;` 或 target 私有成本命名。

## 测试

- 测试文件：
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/include/api/test_arch.py`
  - `test/include/api/test_trance.py`
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
  - `pytest -q test/include/api/test_trance.py`
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
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-004 | 边界/异常 | 锁定 `block > 2`、`thread != 1` 或 `subthread != 1` 的显式失败边界。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_npu_demo_launch_rejects_unsupported_extent_without_fallback`。 | “锁定 `block > 2`、`thread != 1` 或 `subthread != 1` 的显式失败边界。”场景按公开错误语义失败或被拒绝。 | `test_npu_demo_launch_rejects_unsupported_extent_without_fallback` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-005 | 公开入口 | 锁定 `npu_demo::` public function 最小正向消费。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_npu_demo_public_namespace_smoke_compiles_vector_kernel_and_launch`。 | 公开入口在“锁定 `npu_demo::` public function 最小正向消费。”场景下可导入、构造、注册或按名称发现。 | `test_npu_demo_public_namespace_smoke_compiles_vector_kernel_and_launch` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-005A | 公开入口 | 锁定 `npu_demo::min/max` public namespace 正向消费。 | 包含 `include/npu_demo/npu_demo.h` 并构造 same-shape vector memory。 | 运行 `test_npu_demo_public_namespace_smoke_compiles_vector_kernel_and_launch`。 | `npu_demo::min/max` 可经聚合头文件直接调用，不依赖 `detail` 或旧 `Nn` 名称。 | `test_npu_demo_public_namespace_smoke_compiles_vector_kernel_and_launch` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-006 | 公开入口 | 锁定 `Memory/Dma` public function 只通过 `npu_demo::` 正向消费，未限定的全局 helper 不作为成功路径。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_npu_demo_public_namespace_memory_dma_helpers`。 | 公开入口在“锁定 `Memory/Dma` public function 只通过 `npu_demo::` 正向消费，未限定的全局 helper 不作为成功路径。”场景下可导入、构造、注册或按名称发现。 | `test_npu_demo_public_namespace_memory_dma_helpers` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-006A | 公开入口 | 锁定 `DmaRing` / `make_ring` 经 `include/npu_demo/npu_demo.h` 正向消费。 | 包含聚合头，构造一维 byte backing 与 typed slot layout。 | 运行 `test_npu_demo_public_namespace_memory_dma_helpers`。 | `npu_demo::make_ring<float>(...)` 可经聚合头构造 ring，`.current()` / `.advance()` 可返回 typed slot view。 | `test_npu_demo_public_namespace_memory_dma_helpers` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-007 | 生成/编译 | 锁定 `include/npu_demo/npu_demo.h` 对 `gen_kernel` 输出的 wrapper/body kernel + sibling cost function 模块仍是单入口 compile-only 头文件。 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_cost_function_module`。 | 生成源码、IR 文本或编译结果体现“锁定 `include/npu_demo/npu_demo.h` 对 `gen_kernel` 输出的 wrapper/body kernel + sibling cost function 模块仍是单入口 compile-only 头文件。”场景。 | `test_gen_kernel_compiles_npu_demo_cost_function_module` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-008 | 公开入口 | 锁定 registry 的 `arch.launch` / `arch.barrier` 能力开关与 `block_num=2/thread_num=1` 上限语义。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_npu_demo_supports_launch_and_barrier_caps`。 | 公开入口在“锁定 registry 的 `arch.launch` / `arch.barrier` 能力开关与 `block_num=2/thread_num=1` 上限语义。”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_npu_demo_supports_launch_and_barrier_caps` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-009 | 边界/异常 | 锁定 cost DMA include 不依赖跨文件非公开 detail 聚合状态。 | 读取公开 include 文本。 | 运行 `test_npu_demo_cost_dma_has_no_cross_file_detail_accumulator`。 | `include/npu_demo/cost/Core.h` 不承载 DMA 聚合状态，`include/npu_demo/cost/Dma.h` 不包含或调用该非公开状态。 | `test_npu_demo_cost_dma_has_no_cross_file_detail_accumulator` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-009A | 公开入口 | 锁定 `npu_demo::cost::min/max` public namespace 正向消费。 | 包含 `include/npu_demo/npu_demo.h` 并构造 same-shape vector memory。 | 运行 `test_npu_demo_public_header_aggregates_cost_family`。 | `npu_demo::cost::min/max` 可经聚合头文件直接调用，模板与参数顺序和 `include/api/cost/Kernel.h` 一致。 | `test_npu_demo_public_header_aggregates_cost_family` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-010 | 执行结果 | 单入口头文件聚合 runtime trance，`TRANCE` 开启时输出 Memory 与 launch 参数。 | include `include/npu_demo/npu_demo.h`，传 `-DTRANCE`，构造 `Memory<GM, float>` 并作为 forwarded arg 执行 `npu_demo::launch<2, 1, 1, 0, kernel_body>(ctx, ...)`。 | 运行 `test_npu_demo_trance_stdout_memory_and_launch_format`。 | stdout 包含 launch `template=<block=2, thread=1, subthread=1, shared_memory_size=0>`、`arg0 = KernelContext`、`arg1 = mem[...] [2, 3] [3, 1] f32 GM` 与 `arg2 = 7`。 | `test_npu_demo_trance_stdout_memory_and_launch_format` |
| TC-INCLUDE-NPU-DEMO-NPU-DEMO-011 | 执行结果 | 单入口头文件聚合 runtime trance block 文件模式。 | include `include/npu_demo/npu_demo.h`，传 `-DTRANCE` 与 `KG_TRANCE_DIR_PATH`，执行 `npu_demo::launch<2, 1, 1, 0, kernel_body>(ctx)`。 | 运行 `test_npu_demo_launch_trance_block_logs_are_per_block_files`。 | `block_0000.log` 与 `block_0001.log` 存在并包含对应 header 与 launch 参数，旧额外 `block_*.log` 会被清理。 | `test_npu_demo_launch_trance_block_logs_are_per_block_files` |
