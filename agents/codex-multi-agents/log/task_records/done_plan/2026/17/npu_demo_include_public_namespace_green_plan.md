# npu_demo_include_public_namespace_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/include/api/Core.md`](../../spec/include/api/Core.md)
  - [`spec/include/api/Memory.md`](../../spec/include/api/Memory.md)
  - [`spec/include/api/Dma.md`](../../spec/include/api/Dma.md)
  - [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md)
  - [`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)
  - [`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- 目标 `API`：
  - [`include/api/Core.h`](../../include/api/Core.h)
  - [`include/api/Memory.h`](../../include/api/Memory.h)
  - [`include/api/Dma.h`](../../include/api/Dma.h)
  - [`include/api/Kernel.h`](../../include/api/Kernel.h)
  - [`include/api/Arch.h`](../../include/api/Arch.h)
  - [`include/npu_demo/Core.h`](../../include/npu_demo/Core.h)
  - [`include/npu_demo/Memory.h`](../../include/npu_demo/Memory.h)
  - [`include/npu_demo/Dma.h`](../../include/npu_demo/Dma.h)
  - [`include/npu_demo/Kernel.h`](../../include/npu_demo/Kernel.h)
  - [`include/npu_demo/Arch.h`](../../include/npu_demo/Arch.h)
  - [`include/npu_demo/npu_demo.h`](../../include/npu_demo/npu_demo.h)
- 目标 `test`：
  - [`test/include/api/test_core.py`](../../test/include/api/test_core.py)
  - [`test/include/api/test_memory.py`](../../test/include/api/test_memory.py)
  - [`test/include/api/test_dma.py`](../../test/include/api/test_dma.py)
  - [`test/include/api/test_kernel.py`](../../test/include/api/test_kernel.py)
  - [`test/include/api/test_arch.py`](../../test/include/api/test_arch.py)
  - [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)
  - [`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)
  - `test/include/npu_demo/test_public_namespace.py`（由执行者补齐）
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 目标 `验收资产`：
  - [`expectation/dsl/emit_c/npu_demo`](../../expectation/dsl/emit_c/npu_demo)
  - [`expectation/execute_engine/npu_demo`](../../expectation/execute_engine/npu_demo)
  - `pytest -q test/include/api test/include/npu_demo`
- 目标 `功能实现`：
  - [`include/npu_demo`](../../include/npu_demo)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1 / T-20260421-29b0c3ba` | `无` | `wt-20260421-npu-demo-core-vector-public-namespace-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260421-npu-demo-core-vector-public-namespace-s1.md` |
| `S2 / T-20260421-9a5f4867` | `T-20260421-29b0c3ba` | `wt-20260421-npu-demo-dma-memory-public-namespace-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260421-npu-demo-dma-memory-public-namespace-s2.md` |
| `S3 / T-20260421-b437ed7f` | `T-20260421-9a5f4867` | `wt-20260421-npu-demo-codegen-public-namespace-s3` | `agents/codex-multi-agents/log/task_records/2026/17/20260421-npu-demo-codegen-public-namespace-s3.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`通过。Vector{...} 已按用户最新口径收到 1..4 个 long long 固定参数构造函数承接，未发现旧上限残留；禁止 <initializer_list> / std::initializer_list / 标准库容器 / 标准库工具类型 / 堆分配 / 动态扩容的边界清楚。函数入口迁入 npu_demo::、基础类型暂不整体迁移、S1-S3 拆分可推进。`

## 终验 / 复验 / 修复复核记录

- 结论人：`不适用`
- 结论：`不适用`
- 验证基线：`不适用`
- 最小阻断项或通过摘要：`计划阶段尚未进入终验`
- 是否已创建修复任务：`不适用`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`无`

## 输入摘要

- 目标：重构 [`include/npu_demo`](../../include/npu_demo) 的函数实现与调用口径，让公开函数统一进入 `namespace npu_demo`。
- 不做什么：本轮不把 `Status`、`StatusCode`、`Vector`、`Memory`、`MemorySpace` 等基础类型整体迁移到 `npu_demo::`；这些类型继续沿用当前 `include/api` 的公开类型边界。
- 当前痛点：`Kernel` family 已主要以 `npu_demo::add/sub/mul/...` 暴露，但 `Dma` / `Memory` 中仍有全局函数实现与 `npu_demo_dma_detail`、`npu_demo_memory_detail` 这类可被外部直接命中的 helper 名。
- 完成后用户最想看到的例子：生成源码和手写源码都通过 `npu_demo::slice(...)`、`npu_demo::deslice(...)`、`npu_demo::alloc(...)`、`npu_demo::add(...)` 等公开入口调用；`Vector shape{2, 3}` 可直接用于 `shape/offset/stride` 参数。

## 计划目标

- 公开函数统一收口到 `namespace npu_demo`：
  - `npu_demo::build_contiguous_stride`
  - `npu_demo::view`
  - `npu_demo::alloc`
  - `npu_demo::slice`
  - `npu_demo::deslice`
  - 现有 `npu_demo::add/sub/mul/truediv/eq/ne/lt/le/gt/ge/exp/select/reduce_sum/reduce_min/matmul/img2col*`
  - `npu_demo::launch`
- 全局函数入口不再作为成功合同保留；执行阶段应迁移 include/api 声明、include/npu_demo 实现、codegen 输出与测试消费者。
- 非公开 helper 尽量收进 `npu_demo::detail` 或文件内私有辅助结构；生成源码、expectation 与公开测试不得直接消费 `detail` 或 `*_detail` 名字。
- 实现侧应尽量避免标准库容器与标准库工具类型；`Vector{...}` 本轮按不使用标准库头文件、不使用堆分配的高性能口径收口。
- `Vector` 新增花括号调用语法：
  - `Vector values{1, 2, 3}`
  - `Vector values = {1, 2, 3}`
  - 该语法必须由 `1..4` 个 `long long` 固定参数构造函数承接，内部复制到 `Vector` 自身的内联存储。
  - 不得包含 `<initializer_list>`、`std::initializer_list`、标准库容器、标准库工具类型、堆分配或动态扩容。
  - 本轮容量上限按用户确认的数组长度最多 `4` 收口；超过 `4` 个元素不属于合法公开调用。
- 保持当前 `include/npu_demo/npu_demo.h` 单入口聚合，不新增第二套 target include。

## 当前基线

- 当前公开合同：
  - [`spec/include/api/Core.md`](../../spec/include/api/Core.md) 明确 `Vector` 仅支持外部 buffer 视图，尚未支持花括号调用语法。
  - [`spec/include/api/Dma.md`](../../spec/include/api/Dma.md)、[`spec/include/api/Memory.md`](../../spec/include/api/Memory.md) 仍允许部分全局函数形态。
  - [`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md) 只写清单入口聚合和 runtime 语义，没有把“npu_demo 公开函数必须位于 `namespace npu_demo`”写成总合同。
- 当前公开 API：
  - [`include/api/Core.h`](../../include/api/Core.h) 中 `Vector` 只有 `Vector(long long*, size)` 与 `Vector(const long long*, size)`。
  - [`include/api/Dma.h`](../../include/api/Dma.h) 中 `alloc/slice/deslice` 等声明尚未统一到 `npu_demo::`。
  - [`include/api/Memory.h`](../../include/api/Memory.h) 中 `build_contiguous_stride` 与 `view` 仍是全局函数/成员混合口径。
- 当前实现入口：
  - [`include/npu_demo/Core.h`](../../include/npu_demo/Core.h) 只实现 pointer-view 版本 `Vector`。
  - [`include/npu_demo/Dma.h`](../../include/npu_demo/Dma.h) 中 `alloc/slice/deslice` 当前是全局模板函数，内部 helper 在 `npu_demo_dma_detail`。
  - [`include/npu_demo/Memory.h`](../../include/npu_demo/Memory.h) 中 `build_contiguous_stride`、free `view` 和 `Memory` 成员实现仍在全局类型体系下，内部 helper 在 `npu_demo_memory_detail`。
  - [`include/npu_demo/Kernel.h`](../../include/npu_demo/Kernel.h) 已有 `namespace npu_demo` 与 `namespace npu_demo::detail`，可作为本轮 public/detail 分层参考。
- 当前测试与验收资产：
  - [`test/include/api/test_core.py`](../../test/include/api/test_core.py) 只覆盖 pointer-view `Vector`。
  - [`test/include/api/test_dma.py`](../../test/include/api/test_dma.py)、[`test/include/api/test_memory.py`](../../test/include/api/test_memory.py) 仍可能接受全局 helper 调用。
  - [`expectation/dsl/emit_c/npu_demo`](../../expectation/dsl/emit_c/npu_demo) 与 [`expectation/execute_engine/npu_demo`](../../expectation/execute_engine/npu_demo) 是生成源码最终调用形态的合同真源。
- 当前缺口或失败点：
  - 全局函数、`npu_demo::` 函数与 detail helper 三类名字混在头文件中，调用方容易绕过公开接口。
  - `Vector{...}` 无法直接表达 shape/offset/stride，导致生成源码和手写测试不得不先创建临时数组。
  - `detail` 名字没有统一边界，后续 codegen 可能误把 helper 当作公开入口消费。

## 合同真源顺序

- `expectation/dsl/emit_c/npu_demo + expectation/execute_engine/npu_demo > spec/include/api/* + spec/include/npu_demo/npu_demo.md + spec/dsl/* > test/include/* + test/dsl/* > 当前实现`

## 方案比较与选型

- 不采用方案：继续保留全局函数入口，同时新增 `npu_demo::` wrapper。
  - 原因：这会让生成源码和手写调用长期存在两套成功路径，无法判断哪一套才是公开合同。
- 不采用方案：把所有基础类型也整体迁移到 `npu_demo::`。
  - 原因：本轮用户点名的是函数实现归入 `npu_demo`；全类型迁移会牵涉 `Memory<GM, T>`、`Status`、`MemorySpace` 与大量已有生成源码，范围过大。
- 不采用方案：花括号调用语法背后保存临时对象首地址。
  - 原因：临时对象生命周期结束后会产生悬垂指针，不满足可用的 `Vector{...}` 合同。
- 采用方案：
  - 基础类型继续由 `include/api` 定义；
  - 所有 public function 入口进入 `namespace npu_demo`；
  - 旧全局函数成功路径删除或改成编译失败；
  - `Vector` 增加 `1..4` 个 `long long` 固定参数重载，支持 `Vector{...}` 与 `Vector values = {...}`；
  - `Vector{...}` 内部使用内联存储，不使用标准库容器和堆分配；
  - pointer-view 构造保持不变；
  - helper 统一放入 `npu_demo::detail`，并从 spec、expectation、生成源码与公开测试中消除直接消费。
- 最小公开接口：
  - `Vector{...}`
  - `npu_demo::build_contiguous_stride(...)`
  - `npu_demo::alloc(...)`
  - `npu_demo::slice(...)`
  - `npu_demo::deslice(...)`
  - `npu_demo::view(...)`
  - `npu_demo::add/sub/mul/truediv/...`
  - `npu_demo::launch(...)`

## 公开 API 设计

- 公开入口：`include/npu_demo/npu_demo.h`
- 参数顺序：
  - `npu_demo::alloc<Space, T>(shape, stride, format)`
  - `npu_demo::slice(target, source, offset, size, stride)`
  - `npu_demo::deslice(target, source, offset, size, stride)`
  - `npu_demo::view(source, offset, size, stride)`
  - `npu_demo::add<Space, InType, OutType>(out, lhs, rhs)`
  - `npu_demo::launch<block, thread, subthread>(callee, args...)`
- 参数类型：
  - `shape/offset/size/stride` 接受 `Vector`；`Vector` 支持 pointer-view 与花括号调用语法两类构造。
  - `Vector{...}` 由 `1..4` 个 `long long` 固定参数构造函数承接，不依赖 `<initializer_list>` 或 `std::initializer_list`。
  - `alloc` 后续应优先接受 `Vector`；若继续保留 `{...}` 直接传参，只允许作为向 `Vector` 的同类固定参数构造收口，不新增标准库容器依赖。
- 返回值：
  - `Vector` 构造返回 owned 或 view 语义对象；
  - `npu_demo::alloc(...)` 返回 `Memory<Space, T>`；
  - `npu_demo::slice/deslice/add/.../launch` 返回 `Status`；
  - `npu_demo::view(...)` 返回对应 `Memory` view。

```cpp
#include "include/npu_demo/npu_demo.h"

Vector shape{8, 16};
Vector stride{16, 1};
Memory<GM, float> out(out_data, shape.data(), stride.data(), shape.size());

auto tile = npu_demo::alloc<TSM, float>({8, 16}, {16, 1}, MemoryFormat::Norm);
Status copied = npu_demo::slice(tile, out, Vector{0, 0}, Vector{8, 16}, Vector{1, 1});
Status written = npu_demo::deslice(out, tile, Vector{0, 0}, Vector{8, 16}, Vector{1, 1});
```

```cpp
#include "include/npu_demo/npu_demo.h"

Status st = npu_demo::add<GM, float, float>(out, lhs, rhs);
Status launched = npu_demo::launch<1, 4, 1>(kernel_body, out, lhs, rhs);
```

## 完成态定义

- `include/npu_demo` 中面向调用方的函数入口统一位于 `namespace npu_demo`。
- 全局 `alloc/slice/deslice/view/build_contiguous_stride` 不再作为成功调用合同保留。
- `npu_demo::detail` 是唯一允许的 helper 命名空间；`npu_demo_dma_detail`、`npu_demo_memory_detail` 等外部可直接命中的 helper 名不再作为公开可消费名字存在。
- `Vector` 支持 pointer-view 与 `Vector{...}` 两类构造；`Vector{...}` 使用内联存储，`data()` 在 `Vector` 对象生命周期内有效。
- `Vector{...}` 不使用标准库容器、不使用堆分配；本轮最多支持 `4` 个元素。
- 生成源码中不出现全局 `slice(`、`deslice(`、`alloc(`、`view(` 作为 npu_demo helper 调用；应出现 `npu_demo::slice(`、`npu_demo::deslice(`、`npu_demo::alloc(` 或成员式公开调用。
- 公开测试不得直接调用 `npu_demo::detail` 或 `*_detail` helper；若需要测试 helper 行为，必须通过 public function 间接覆盖。
- 现有 `expectation/dsl/emit_c/npu_demo` 与 `expectation/execute_engine/npu_demo` 仍能通过。

## 验收设计

- 验收资产：
  - [`test/include/api/test_core.py`](../../test/include/api/test_core.py)：新增 `Vector{...}` 编译运行用例。
  - `test/include/npu_demo/test_public_namespace.py`：新增 public namespace smoke，断言 `npu_demo::slice/deslice/alloc/add/launch` 可编译，旧全局函数不作为成功路径。
  - [`expectation/dsl/emit_c/npu_demo`](../../expectation/dsl/emit_c/npu_demo)：锁定生成源码调用 `npu_demo::` 公开入口。
  - [`expectation/execute_engine/npu_demo`](../../expectation/execute_engine/npu_demo)：锁定真实编译执行链不回退。
- 输入样例：
  - `Vector shape{2, 3};`
  - `npu_demo::slice(tile, source, Vector{0}, Vector{16}, Vector{1});`
  - `npu_demo::add<GM, float, float>(out, lhs, rhs);`
- 锁定输出：
  - C++ 片段编译运行通过。
  - 生成源码命中 `npu_demo::` 前缀。
  - 生成源码不命中 `npu_demo::detail`、`npu_demo_dma_detail`、`npu_demo_memory_detail`。
- 必过命令：
  - `pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_kernel.py test/include/api/test_arch.py`
  - `pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py test/include/npu_demo/test_public_namespace.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo`
  - `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`

## 阶段拆分

### S1：Core / Vector 花括号调用与 public namespace 总合同

#### 阶段目标

- 收口 `Vector` 花括号调用合同，并把 `npu_demo` public function namespace 规则写入 spec 与最小编译测试。

#### 目标 spec / API

- `spec/include/api/Core.md`
- `spec/include/npu_demo/npu_demo.md`
- `include/api/Core.h`
- `include/npu_demo/Core.h`
- `公开 API：Vector{...} / include/npu_demo/npu_demo.h`

#### 禁止修改面 / 合同真源

- `禁止修改面：不做基础类型整体 npu_demo:: 迁移，不新增第二套 include 入口`
- `合同真源：spec/include/api/Core.md + spec/include/npu_demo/npu_demo.md + test/include/api/test_core.py`

#### 预期示例代码

```cpp
#include "include/npu_demo/npu_demo.h"

Vector dims{2, 3, 4};
if (dims.size() != 3 || dims[1] != 3) {
    return 1;
}
```

#### 预期输出

```text
Vector{...} copies values into inline storage and keeps data() valid for the Vector lifetime.
```

#### 目标验收资产

- `pytest -q test/include/api/test_core.py`
- `test/include/npu_demo/test_public_namespace.py` 中新增最小 public namespace 编译用例。

#### 验收必过项目

- `Vector{1, 2, 3}` 与 `Vector values = {1, 2, 3}` 都可编译运行。
- `Vector{...}` 不引入 `<initializer_list>`、`std::vector`、`std::array`、堆分配或动态扩容。
- `Vector(long long*, size)` 与 `Vector(const long long*, size)` 旧构造继续可用。
- spec 明确 public function 应位于 `namespace npu_demo`，detail 不作为消费目标。

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：收口 Vector 花括号调用与 npu_demo public function namespace 总合同，补齐最小编译测试。`
- `记录文件：待管理员创建（npu-demo-core-vector-public-namespace-s1.md）`

### S2：Memory / Dma 函数迁入 npu_demo public namespace

#### 阶段目标

- 将 `Memory/Dma` 相关公开函数迁到 `npu_demo::`，并把 helper 收进非公开消费边界。

#### 目标 spec / API

- `spec/include/api/Memory.md`
- `spec/include/api/Dma.md`
- `spec/include/npu_demo/npu_demo.md`
- `include/api/Memory.h`
- `include/api/Dma.h`
- `include/npu_demo/Memory.h`
- `include/npu_demo/Dma.h`
- `公开 API：npu_demo::build_contiguous_stride / npu_demo::view / npu_demo::alloc / npu_demo::slice / npu_demo::deslice`

#### 禁止修改面 / 合同真源

- `禁止修改面：不保留旧全局函数成功路径，不让公开测试直接消费 detail helper`
- `合同真源：spec/include/api/Memory.md + spec/include/api/Dma.md + test/include/api/test_memory.py + test/include/api/test_dma.py`

#### 预期示例代码

```cpp
#include "include/npu_demo/npu_demo.h"

Vector shape{4};
Vector stride{1};
Memory<GM, float> src(src_data, shape.data(), stride.data(), shape.size());
auto dst = npu_demo::alloc<TSM, float>({4}, {1}, MemoryFormat::Norm);
Status st = npu_demo::slice(dst, src, Vector{0}, Vector{4}, Vector{1});
```

#### 预期输出

```text
npu_demo::alloc / npu_demo::slice / npu_demo::deslice compile and run.
Generated or test source no longer depends on global alloc/slice/deslice.
```

#### 目标验收资产

- `pytest -q test/include/api/test_memory.py test/include/api/test_dma.py`
- `pytest -q test/include/npu_demo/test_public_namespace.py`

#### 验收必过项目

- `npu_demo::slice/deslice` 支持 `Vector{...}` 参数。
- `npu_demo_dma_detail` 与 `npu_demo_memory_detail` 不再作为公开可消费名字出现在 spec、expectation 或生成源码中。
- 旧全局 helper 成功路径不再写入测试正向用例。

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：把 Memory/Dma 公开函数迁入 npu_demo::，收口 detail 边界，并保持 include/api 与 include/npu_demo 测试通过。`
- `记录文件：待管理员创建（npu-demo-dma-memory-public-namespace-s2.md）`

### S3：codegen / expectation / execute_engine 消费口径同步

#### 阶段目标

- 让 `emit_c/gen_kernel/execute_engine` 只消费 `npu_demo::` public function，并完成黑盒链路验收。

#### 目标 spec / API

- `spec/dsl/emit_c.md`
- `spec/dsl/gen_kernel.md`
- `spec/include/api/Kernel.md`
- `spec/include/api/Arch.md`
- `include/npu_demo/Kernel.h`
- `include/npu_demo/Arch.h`
- `kernel_gen/dsl/emit_c.py`
- `kernel_gen/dsl/gen_kernel.py`
- `公开 API：npu_demo::add/sub/mul/... + npu_demo::launch`

#### 禁止修改面 / 合同真源

- `禁止修改面：不让 codegen 直接发射 detail helper，不把旧全局 helper 作为兼容成功输出`
- `合同真源：expectation/dsl/emit_c/npu_demo + expectation/execute_engine/npu_demo`

#### 预期示例代码

```cpp
#include "include/npu_demo/npu_demo.h"

npu_demo::slice(tile, source, Vector{0}, Vector{16}, Vector{1});
npu_demo::add<GM, float, float>(out, lhs, rhs);
npu_demo::launch<1, 4, 1>(kernel_body, out, lhs, rhs);
```

#### 预期输出

```text
Generated npu_demo source uses npu_demo:: public functions and does not emit detail helper names.
```

#### 目标验收资产

- [`expectation/dsl/emit_c/npu_demo`](../../expectation/dsl/emit_c/npu_demo)
- [`expectation/execute_engine/npu_demo`](../../expectation/execute_engine/npu_demo)
- `test/dsl/test_emit_c.py`
- `test/dsl/test_gen_kernel.py`

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo`
- `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`
- `pytest -q test/include/api test/include/npu_demo`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：同步 emit_c/gen_kernel/execute_engine 到 npu_demo:: public function，完成黑盒验收。`
- `记录文件：待管理员创建（npu-demo-codegen-public-namespace-s3.md）`

## 待确认项

- 问题：`无`
- 可选项：`不适用`
- 差异：`用户已确认高性能优先；Vector{...} 采用固定参数重载 + 内联存储，不使用标准库容器、不使用堆分配，容量上限 4。`
- 推荐项：`不适用`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：include/npu_demo 里面的函数实现全部进入 npu_demo 公开接口，尽可能隐藏非公开接口；Vector 支持 Vector{...}，并按高性能优先选择固定参数重载 + 内联存储，不使用标准库容器、不使用堆分配，容量上限 4。`
- `未确认前处理要求：不适用`
- `若用户要求至少询问 3 人：无`
- `询问记录 1：上一版已通过 -talk 发起互评；对象=守护最好的爱莉希雅；结果=上一版通过，但用户新增高性能与标准库约束后正文已更新`
- `询问记录 2：已通过 -talk 发起高性能版本互评；对象=守护最好的爱莉希雅；结果=上一高性能版本通过，但用户已更新为数组长度最多 4，该结论不再作为当前版本推进依据`
- `询问记录 3：已通过 -talk 发起 1..4 版本复评；对象=守护最好的爱莉希雅；结果=通过。Vector{...} 收到 1..4 个 long long 固定参数构造函数承接，禁止 <initializer_list> / std::initializer_list / 标准库容器 / 标准库工具类型 / 堆分配 / 动态扩容，S1-S3 可推进`

## 参考资料

- [`include/api/Core.h`](../../include/api/Core.h)：当前 `Vector` 声明与旧构造。
- [`include/npu_demo/Core.h`](../../include/npu_demo/Core.h)：当前 `Vector` 方法实现。
- [`include/npu_demo/Dma.h`](../../include/npu_demo/Dma.h)：当前全局 `alloc/slice/deslice` 与 `npu_demo_dma_detail` helper。
- [`include/npu_demo/Memory.h`](../../include/npu_demo/Memory.h)：当前全局 `build_contiguous_stride/view` 与 `npu_demo_memory_detail` helper。
- [`include/npu_demo/Kernel.h`](../../include/npu_demo/Kernel.h)：已有 `npu_demo::` public function 与 `npu_demo::detail` 分层参考。
- [`agents/codex-multi-agents/log/task_records/done_plan/2026/16/npu_demo_emitc_include_api_green_plan.md`](../../agents/codex-multi-agents/log/task_records/done_plan/2026/16/npu_demo_emitc_include_api_green_plan.md)：上一轮 include/api 与 npu_demo 分层收口计划。
