# Arch

## 功能简介

定义 include/api 层统一对外的架构/运行时 API 头文件规范（`include/api/Arch.h`），收口 `launch<block, thread, subthread>(callee, args...)` 的公开源码形态、`BarrierVisibility`/`BarrierScope` 枚举，以及后端 `KernelContext` 暴露 `barrier(visibility, scope)` 时必须遵守的命名与参数合同。

- `launch<block, thread, subthread>(callee, args...)`：公开 launch 入口，`callee` 必须是函数对象，不能是字符串。
- `BarrierVisibility`：公开可见域枚举，固定成员为 `TSM` 与 `TLM`；其中 `TLM` 表示聚合可见域，覆盖 `TLM1/TLM2/TLM3`。
- `BarrierScope`：公开同步范围枚举，稳定成员为 `BLOCK`、`THREAD`、`SUBTHREAD`、`GLOBAL`。
- `barrier(visibility, scope)`：公开同步接口名，`visibility` 与 `scope` 必填；不得退化为无参 barrier。

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
- [`spec/operation/arch.md`](../../../spec/operation/arch.md)：高层 helper 与 include/api 命名需保持一致。
- [`spec/dialect/arch.md`](../../../spec/dialect/arch.md)：`arch.launch` / `arch.barrier` 的 IR 语义与 include/api 源码形态保持同名职责映射。

## 目标

- 为后端无关的源码层提供统一的 launch / barrier 命名与最小类型边界。
- 明确 include/api 与后端私有 include 的职责拆分：include/api 只冻结公共接口名与参数合同，不承接线程实现、barrier 对象或具体 runtime。
- 为后续 `include/npu_demo/Arch.h`、`test/include/api/test_arch.py` 与 `test/include/npu_demo/test_kernel_context.py` 提供稳定收敛目标。

## 限制与边界

- `include/api/Arch.h` 只声明公开接口，不得放入任何 `npu_demo` 或其他后端的线程创建、barrier 实现、固定硬件模板值或私有辅助函数。
- 本规范只冻结源码级 `launch` / `barrier` 公开合同，不定义 DSL/front-end、MLIR lowering、codegen 或 runtime 调度细节。
- `launch<block, thread, subthread>(...)` 的 `block/thread/subthread` 是编译期 launch extent，不是运行期位置参数。
- `callee` 的公开语义是“函数对象或等价可调用对象”；不得将 `"my_kernel"` 之类字符串名称暴露为长期稳定合同。
- `barrier(visibility, scope)` 的 `visibility` 元素类型必须是 `BarrierVisibility`；不得改成 `MemorySpace` 列表、字符串列表、自由文本或后端私有空间枚举。
- `BarrierScope` 公开成员允许后端实现做能力裁剪；若某后端暂不支持某个 scope，必须显式失败，不得静默降级为其他 scope。
- include/api 层不定义具体 `KernelContext` 的存储布局、生命周期、默认构造、线程绑定或注入方式；这些职责由后端私有 include 承接。

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

### `launch<block, thread, subthread>(callee, args...)`

功能说明：

- 公开描述一次 kernel launch 请求，并把 `args...` 传递给 `callee`。
- 后端实现必须在 launched body 中注入与本次 launch 对应的运行时上下文视图。

参数说明：

- `block (template int)`：编译期 block extent，必须为正整数。
- `thread (template int)`：编译期 thread extent，必须为正整数。
- `subthread (template int)`：编译期 subthread extent，必须为正整数。
- `callee (callable)`：kernel body 对应的函数对象或等价可调用对象。
- `args...`：按原顺序转发给 `callee` 的 kernel 参数。

使用示例：

```cpp
#include "include/api/Arch.h"

Status status = launch<1, 4, 1>(add_barrier_body, lhs, rhs, out);
```

注意事项：

- 公开调用形态固定为 `launch<block, thread, subthread>(callee, args...)`；不得改成 `launch(callee, block, thread, subthread, ...)`，也不得退回字符串 callee。
- `callee` 的公开合同是函数对象；后端实现可在调用时额外注入 `KernelContext&` 等运行时上下文，但调用方不显式传入该上下文参数。
- include/api 层只定义“存在这样一个 launch 入口”；具体线程模型、运行方式、barrier 共享对象与失败诊断由后端实现承担。
- 不支持 silent fallback：不合法或不受支持的 launch extent / callee 形态必须显式失败。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`StatusCode::kOk` 表示 launch 请求被成功承接；非 `kOk` 表示失败。
- 限制条件：失败时不得偷偷改成单线程、单 block 或忽略部分 extent。

### `barrier(visibility, scope)`

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

## 测试

- 测试文件：[`test/include/api/test_arch.py`](../../../test/include/api/test_arch.py)
- 执行命令：`pytest -q test/include/api/test_arch.py`
- 测试目标：
  - 验证 `BarrierVisibility` 的稳定公开成员与聚合语义。
  - 验证 `BarrierScope` 的稳定公开成员与名称。
  - 验证 `launch<block, thread, subthread>(callee, args...)` 的公开源码形态与函数对象 callee 合同。
  - 验证 include/api 头文件只声明公共接口，不混入 `npu_demo` 私有实现。
  - 验证 `barrier(visibility, scope)` 公开方法名与必填参数面不被回退。
- 功能与用例清单：
  - `test_include_api_arch_exports_public_launch_and_scope_contract`：锁定 `BarrierScope` 与 `launch<...>` 的公开符号面。
  - `test_include_api_arch_rejects_string_callee_contract`：锁定字符串 callee 不属于长期公开合同。
  - `test_include_api_arch_keeps_backend_impl_out_of_api_header`：锁定 `include/api/Arch.h` 不混入 `npu_demo` 私有实现。
