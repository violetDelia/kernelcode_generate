# Arch

## 功能简介

定义 include/api 层统一对外的架构/运行时 API 头文件规范（`include/api/Arch.h`），收口 `launch<block, thread, subthread, shared_memory_size>(callee, args...)` 的公开源码形态、`BarrierVisibility`/`BarrierScope` 枚举，以及后端 `KernelContext::thread_id()`、`KernelContext::thread_num()`、`KernelContext::barrier(visibility, scope)`、`KernelContext::get_dynamic_memory<Space, T>()` 与 free helper `thread_id()`、`thread_num()`、`get_dynamic_memory<Space>()` 必须遵守的命名与参数合同。

- `launch<block, thread, subthread, shared_memory_size>(callee, args...)`：公开 launch 入口，`callee` 必须是函数对象，不能是字符串。
- `BarrierVisibility`：公开可见域枚举，固定成员为 `TSM` 与 `TLM`；其中 `TLM` 表示聚合可见域，覆盖 `TLM1/TLM2/TLM3`。
- `BarrierScope`：公开同步范围枚举，稳定成员为 `BLOCK`、`THREAD`、`SUBTHREAD`、`GLOBAL`。
- `barrier(visibility, scope)`：公开同步接口名，`visibility` 与 `scope` 必填；不得退化为无参 barrier。

## API 列表

- `enum class BarrierVisibility { TSM, TLM }`
- `enum class BarrierScope { BLOCK, THREAD, SUBTHREAD, GLOBAL }`
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status launch(Callable&& callee, Args&&... args)`
- `class KernelContext`
- `KernelContext::thread_id() const -> long long`
- `KernelContext::thread_num() const -> long long`
- `KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`
- `template <MemorySpace Space, typename T> KernelContext::get_dynamic_memory() const -> Memory<Space, T>`
- `thread_id() -> S_INT`
- `thread_num() -> S_INT`
- `template <MemorySpace Space> get_dynamic_memory() -> DynamicMemoryRef<Space>`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md)
- `统一头文件`：[`include/api/Arch.h`](../../../include/api/Arch.h)
- `功能实现`：[`include/npu_demo/Arch.h`](../../../include/npu_demo/Arch.h)
- `test`：[`test/include/api/test_arch.py`](../../../test/include/api/test_arch.py)

## 依赖

- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一 `Status` / `StatusCode` 返回语义。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：统一 `MemorySpace` 枚举语义，提供 `TLM1/TLM2/TLM3` 三块实际空间定义。
- [`spec/include/npu_demo/npu_demo.md`](../../../spec/include/npu_demo/npu_demo.md)：后端私有 runtime 行为与 `KernelContext` 运行时视图由该层承接。
- [`spec/operation/arch.md`](../../../spec/operation/arch.md)：高层 helper 与 include/api 命名需保持一致。
- [`spec/dialect/arch.md`](../../../spec/dialect/arch.md)：`arch.launch` / `arch.barrier` 的 IR 语义与 include/api 源码形态保持同名职责映射。

## 目标

- 为后端无关的源码层提供统一的 launch / barrier 命名与最小类型边界。
- 明确 include/api 与后端私有 include 的职责拆分：include/api 只定义接口与最小语义，不承接线程实现、barrier 对象或具体 runtime。
- 明确 include/npu_demo 承接 runtime 行为，负责 `KernelContext` 的真实线程/同步实现、launch 注入与片上动态内存视图。
- 为后续 `include/npu_demo/Arch.h`、`test/include/api/test_arch.py` 与 `test/include/npu_demo/test_kernel_context.py` 提供稳定收敛目标。

## 限制与边界

- `include/api/Arch.h` 只声明公开接口，不得放入任何 `npu_demo` 或其他后端的线程创建、barrier 实现、固定硬件模板值或私有辅助函数。
- 本规范只冻结源码级 `launch` / `barrier` 公开合同，不定义 DSL/front-end、MLIR lowering、codegen 或 runtime 调度细节。
- include/api 只定义接口与最小语义；`KernelContext` 的真实线程索引、extent、barrier 共享对象、动态内存 backing store 与 launch 注入方式，都由 include/npu_demo 等后端私有层承接。
- `launch<block, thread, subthread, shared_memory_size>(...)` 的 `block/thread/subthread/shared_memory_size` 是编译期 launch extent，不是运行期位置参数。
- `callee` 的公开语义是“函数对象或等价可调用对象”；不得将 `"my_kernel"` 之类字符串名称暴露为长期稳定合同。
- `barrier(visibility, scope)` 的 `visibility` 元素类型必须是 `BarrierVisibility`；不得改成 `MemorySpace` 列表、字符串列表、自由文本或后端私有空间枚举。
- `BarrierScope` 公开成员允许后端实现做能力裁剪；若某后端暂不支持某个 scope，必须显式失败，不得静默降级为其他 scope。
- include/api 层不定义具体 `KernelContext` 的存储布局、生命周期、默认构造、线程绑定或注入方式；这些职责由后端私有 include 承接。
- `KernelContext::thread_id()` / `KernelContext::thread_num()` / `KernelContext::barrier(...)` / `KernelContext::get_dynamic_memory<Space, T>()` 是 include/api 层公开承诺的最小运行时接口面；后端可以补实现细节，但不得改名、改参数面或改成 target 私有别名。
- `thread_id()` / `thread_num()` / `get_dynamic_memory<Space>()` 是公开代码生成口径；后端必须保证它们可在已绑定 launch 上下文时直接调用。

## 公开接口

### `BarrierVisibility`

功能说明：

- 定义 `barrier(visibility, scope)` 的公开可见域枚举。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/api/Arch.h"

BarrierVisibility vis = BarrierVisibility::TLM;
```

注意事项：

- 当前稳定成员为 `BarrierVisibility::TSM` 与 `BarrierVisibility::TLM`。
- `BarrierVisibility::TLM` 表示聚合可见域，覆盖 `MemorySpace::TLM1`、`MemorySpace::TLM2`、`MemorySpace::TLM3`。
- `BarrierVisibility` 不用于 `Memory<Space, T>` 模板参数；实际内存空间仍由 `MemorySpace` 表达。

返回与限制：

- 返回类型：`BarrierVisibility`。
- 返回语义：表示 barrier 的可见域。
- 限制条件：不允许扩展额外公开成员或把 `TLM` 解释为独立真实内存空间。

### `BarrierScope`

功能说明：

- 定义公开同步范围枚举，供 `KernelContext::barrier(visibility, scope)` 使用。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/api/Arch.h"

BarrierScope scope = BarrierScope::GLOBAL;
```

注意事项：

- 当前稳定成员为 `BarrierScope::BLOCK`、`BarrierScope::THREAD`、`BarrierScope::SUBTHREAD`、`BarrierScope::GLOBAL`。
- `BLOCK` 表示当前 launch block 内同步；其余成员用于表达更细或更粗的公开范围，具体后端可显式拒绝。
- 本规范不定义字符串别名、整数常量别名或其他额外 scope 成员。

返回与限制：

- 返回类型：`BarrierScope`。
- 返回语义：表示 barrier 的同步范围。
- 限制条件：实现侧可以拒绝某个 scope，但不得改变公开成员名与既定语义。

### `launch<block, thread, subthread, shared_memory_size>(callee, args...)`

功能说明：

- 公开描述一次 kernel launch 请求，并把 `args...` 传递给 `callee`。
- 后端实现必须在 launched body 中注入与本次 launch 对应的运行时上下文视图。

参数说明：

- `block (template int)`：编译期 block extent，必须为正整数。
- `thread (template int)`：编译期 thread extent，必须为正整数。
- `subthread (template int)`：编译期 subthread extent，必须为正整数。
- `shared_memory_size (template int)`：编译期共享内存规模，必须为非负整数。
- `callee (callable)`：kernel body 对应的函数对象或等价可调用对象。
- `args...`：按原顺序转发给 `callee` 的 kernel 参数。

使用示例：

```cpp
#include "include/api/Arch.h"

Status status = launch<1, 4, 1, 0>(add_barrier_body, lhs, rhs, out);
```

注意事项：

- 公开调用形态固定为 `launch<block, thread, subthread, shared_memory_size>(callee, args...)`；不得改成 `launch(callee, block, thread, subthread, shared_memory_size, ...)`，也不得退回字符串 callee。
- `callee` 的公开合同是函数对象；后端实现可在调用时额外注入 `KernelContext&` 等运行时上下文，但调用方不显式传入该上下文参数。
- include/api 层只定义“存在这样一个 launch 入口”；具体线程模型、运行方式、barrier 共享对象与失败诊断由后端实现承担。
- 不支持 silent fallback：不合法或不受支持的 launch extent / callee 形态必须显式失败。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`StatusCode::kOk` 表示 launch 请求被成功承接；非 `kOk` 表示失败。
- 限制条件：失败时不得偷偷改成单线程、单 block 或忽略部分 extent。

### `KernelContext`

功能说明：

- 定义后端 launched body 中可见的最小运行时上下文接口面。
- include/api 层只冻结 `KernelContext::*` 运行时方法与 `thread_id()` / `thread_num()` / `get_dynamic_memory<Space>()` free helper 这些名称、参数面与最小返回语义。

参数说明：

- 无参数。

使用示例：

```cpp
long long tid = ctx.thread_id();
long long tnum = ctx.thread_num();
ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
auto tsm = ctx.get_dynamic_memory<TSM, float>();
S_INT tid2 = thread_id();
S_INT tnum2 = thread_num();
Memory<TSM, float> tsm2 = get_dynamic_memory<TSM>();
```

注意事项：

- include/api 只定义接口与最小语义，不定义 `KernelContext` 的存储布局、构造方式、线程绑定或动态内存分配策略。
- include/npu_demo 承接 runtime 行为，负责把当前 launch 的运行时视图注入到 `KernelContext` 中。
- 后端私有层可以增加内部辅助方法，但不得改写这里定义的公开方法名、参数顺序或最小返回语义。

返回与限制：

- 返回类型：`KernelContext`。
- 返回语义：表示 launched body 当前可见的运行时上下文视图。
- 限制条件：本规范只冻结公开接口面，不承诺具体实现细节。

### `KernelContext::thread_id()` / `KernelContext::thread_num()`

功能说明：

- 返回当前 launch 运行时视图中的线程索引与线程总数。

参数说明：

- 无参数。

使用示例：

```cpp
long long tid = ctx.thread_id();
long long tnum = ctx.thread_num();
```

注意事项：

- `KernelContext::thread_id()` 与 `KernelContext::thread_num()` 的公开语义是“当前 launch 的运行时值”，不是 target registry 常量，也不是编译期模板值的文本替身。
- include/api 不规定具体整数实现类型，只要求源码层维持稳定方法名与返回整型语义。

### `thread_id()` / `thread_num()`

功能说明：

- 返回当前 launch 运行时视图中的线程索引与线程总数，作为公开 free helper 供生成代码直接调用。

参数说明：

- 无参数。

使用示例：

```cpp
S_INT tid = thread_id();
S_INT tnum = thread_num();
```

注意事项：

- `thread_id()` / `thread_num()` 的公开语义与 `KernelContext::thread_id()` / `KernelContext::thread_num()` 一致，都表示当前 launch 的运行时值。
- 这组 free helper 的职责是隐藏活动上下文绑定细节；公开生成代码不得再硬编码 `ctx.` 前缀。

返回与限制：

- 返回类型：`S_INT`。
- 返回语义：分别表示当前线程索引与当前 launch 的线程总数。
- 限制条件：后端必须保证在已有活动 launch 上下文时可直接调用。

返回与限制：

- 返回类型：整型值，当前以 `long long` 表达。
- 返回语义：分别表示当前线程索引与当前 launch 的线程总数。
- 限制条件：后端不得把它们静默收缩为固定常量。

### `KernelContext::barrier(visibility, scope)`

功能说明：

- 定义后端 `KernelContext` 暴露同步接口时必须遵守的公开方法名与参数合同。
- 该接口表示“在当前 launch 上下文中，对 `visibility` 指定的 memory space 执行 `scope` 范围同步”。

参数说明：

- `visibility (std::initializer_list<BarrierVisibility> 或等价只读列表)`：需要保证可见性的可见域列表。
- `scope (BarrierScope)`：同步范围。

使用示例：

```cpp
ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
```

注意事项：

- 公开方法名固定为 `barrier`；不得改成 `sync`、`fence` 或无名副作用调用。
- `visibility` 与 `scope` 都是必填；不得定义无参 `barrier()` 作为稳定公开合同。
- `visibility` 不能为空；出现重复项、非法可见域或后端不支持的组合时必须显式失败。
- `BarrierVisibility::TLM` 表示聚合可见域，不等于真实 `MemorySpace::TLM`，并固定覆盖 `TLM1/TLM2/TLM3`。
- include/api 层不规定具体失败机制，但禁止静默降级为“忽略 barrier”或“忽略部分 visibility”。

返回与限制：

- 返回类型：`void`。
- 返回语义：在当前上下文执行一次带 `visibility / scope` 的同步动作。
- 限制条件：具体是否支持某个 `scope` / `visibility` 组合，由后端 spec 在不收缩公开参数面的前提下进一步约束。

### `KernelContext::get_dynamic_memory<Space, T>()`

功能说明：

- 定义 launched body 中访问片上动态内存视图的公开模板接口。
- include/api 只冻结 `get_dynamic_memory<Space, T>()` 这一模板入口，不在此层承诺具体 target 的容量、地址布局或 backing store。

参数说明：

- `Space (template MemorySpace)`：目标动态内存空间模板参数。
- `T (template type)`：元素类型模板参数。

使用示例：

```cpp
auto tsm = ctx.get_dynamic_memory<TSM, float>();
```

注意事项：

- `get_dynamic_memory<Space, T>()` 是 `KernelContext` 的公开成员模板，不得回退为自由函数或把 `Space` 改成运行时位置参数。
- include/api 只定义接口与最小语义；具体哪些 `Space` 合法、容量多少、失败条件如何表达，由 include/npu_demo 等后端私有层进一步收口。

### `get_dynamic_memory<Space>()`

功能说明：

- 返回指定片上空间的动态内存视图代理，作为公开 free helper 供生成代码直接调用。

参数说明：

- `Space`：目标片上空间模板参数。

使用示例：

```cpp
Memory<TSM, float> tsm = get_dynamic_memory<TSM>();
```

注意事项：

- 该 free helper 的公开语义与 `KernelContext::get_dynamic_memory<Space, T>()` 一致，但生成代码不再显式写 `ctx.`。
- 元素类型不再作为 free helper 模板参数显式传入，而是由赋值目标的 `Memory<Space, T>` 类型在转换阶段确定。
- 后端必须负责将 free helper 绑定到当前活动 launch 上下文。

返回与限制：

- 返回类型：可转换为 `Memory<Space, T>` 的公开代理对象。
- 返回语义：当前活动 launch 上下文中对应片上空间的动态内存视图。
- 限制条件：具体哪些 `Space` 合法、容量多少、失败条件如何表达，仍由后端私有层进一步收口。
- 返回值必须保持 `Memory<Space, T>` 语义，不得改成裸指针或 target 私有 buffer 类型作为公开合同。

## 测试

- 测试文件：[`test/include/api/test_arch.py`](../../../test/include/api/test_arch.py)
- 执行命令：`pytest -q test/include/api/test_arch.py`
- 测试目标：
  - 验证 `BarrierVisibility` 的稳定公开成员与聚合语义。
  - 验证 `BarrierScope` 的稳定公开成员与名称。
  - 验证 `launch<block, thread, subthread, shared_memory_size>(callee, args...)` 的公开源码形态与函数对象 callee 合同。
  - 验证 `KernelContext::thread_id()` / `KernelContext::thread_num()` / `KernelContext::barrier(...)` / `KernelContext::get_dynamic_memory<...>()` 的最小公开接口面。
  - 验证 include/api 头文件只声明公共接口，不混入 `npu_demo` 私有实现。
  - 验证 `barrier(visibility, scope)` 公开方法名与必填参数面不被回退。
- 功能与用例清单：
  - `test_include_api_arch_exports_public_launch_and_scope_contract`：锁定 `BarrierScope` 与 `launch<...>` 的公开符号面。
  - `test_include_api_arch_rejects_string_callee_contract`：锁定字符串 callee 不属于长期公开合同。
  - `test_include_api_arch_keeps_backend_impl_out_of_api_header`：锁定 `include/api/Arch.h` 不混入 `npu_demo` 私有实现。
