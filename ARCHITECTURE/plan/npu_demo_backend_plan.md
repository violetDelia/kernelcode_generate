# npu_demo_backend_plan.md

## 进度

- 更新日期：2026-03-31
- 更新规则：每个任务块进入新子阶段后立即更新本段。
- 当前结论：`npu_demo v1` 只冻结 body-level codegen 契约，不支持 `barrier`，不支持任何 `launch*`，不支持 `arch.launch_kernel`，不生成 host wrapper，不复用 `include/cpu/*`。
- 当前新增硬约束：`slice` 在不同分层允许不同签名，但必须把桥接职责写死，不能再笼统写成“同名同签名”。
- 当前硬件模板：`block_num=6`、`thread_num=8`、`subthread_num=1`、`sm_memory_size=0`、`lm_memory_size=0`、`tsm_memory_size=24576`、`tlm_memory_size=2048`。
- 当前阶段策略：实现阶段已放行；并行数 ≤ 8；一人一任务；当前按管理员规则不向 `小李飞刀` 分发新任务。
- 任务状态总览（按任务块）：
- `A0`：spec 完成（T-20260330-6f21e158 + T-20260330-a9e703ad，main=a1a80b4）；同步确认完成（T-20260330-1cb2d126）；实现完成（T-20260330-e4ec5a57）；复审通过（T-20260331-b44cc342）；合并完成（T-20260331-a646980f，main=c260960）；同步确认完成（T-20260331-f3823426）；cleanup 完成（T-20260331-845f083b）；封板同步确认完成（T-20260331-80b72ad9）。
  - `A1`：spec 完成（T-20260330-0cb27b07）。
  - `O1`：spec 完成（T-20260330-d0ab9f64）。
  - `D1`：spec 完成（T-20260330-6e4ca3f0）；实现完成（T-20260330-07e90b30）；复审通过（T-20260331-5fceb412）；合并完成（T-20260331-058f726b，main=77389df，cleanup 已完成）。
  - `M1`：spec 完成（T-20260330-4791790f）；实现完成（T-20260330-c40da050）；复审通过（T-20260331-0c404010）；合并完成（T-20260331-8067ac72，commit=68f2f10，fetch origin 成功，cleanup 已完成）。
  - `M2`：合并完成（T-20260330-38a75f4a → T-20260330-cbabec01，main=5d09200）。
  - `T1`：spec 完成（T-20260330-d8ba09d2）。
  - `T2`：spec 完成（T-20260330-77d9bf6c）。
  - `R1`：spec 完成（T-20260330-68861281）。
  - `R2`：spec 完成（T-20260330-cee8c1ca）。
- `C1`：spec 完成（T-20260330-b0309048）；复审完成（T-20260330-ef12719c）；实现完成（T-20260330-c72fe0a3）；复审不通过（T-20260330-a39afe85）；修复完成（T-20260331-3ee6a889，已补齐 invalid MemorySpace 负例）；复审通过（T-20260331-e77d9fdd）；合并完成（T-20260331-9b4f1525，main=26fcc4a）。
  - `R3`：spec 完成（T-20260330-d88b210a），复审不通过（T-20260330-e368343a），修复完成（T-20260330-6feffe36）；实现完成（T-20260330-d8b00849）；复审通过（T-20260331-1e2b7f1b）；合并完成（T-20260331-d51e1ca7，commit=b0890ba，cleanup 已完成）；同步确认失败（单次 `git fetch origin` 超时，不影响完成判定）。
- `C2`：spec 完成（T-20260330-7f99487d），复审不通过（T-20260330-bdad1d15），修复完成（T-20260330-91f21c6d）；补齐测试完成（T-20260330-f031a2f5）；复审通过（T-20260331-2839635f）；合并完成（T-20260331-77ade68d，main=7f23e71，cleanup 已完成）。
  - `E0`：spec 完成（T-20260330-d1ef3ab8）；实现完成（T-20260330-9d65ffda）；复审通过（T-20260331-4c7f60d7）；合并完成（T-20260331-28f97731，commit=a0a7e18，fetch origin 成功，cleanup 已完成）。
  - `E1`：spec 完成（T-20260331-3fa2f68b）；实现完成（T-20260331-361b680c）；复审通过（T-20260331-8aa3e0b3）；合并完成（T-20260331-079fe721，commit=c803230，单次 `git fetch origin` 超时，不影响完成判定，cleanup 已完成）。
  - `G1`：spec 完成（T-20260331-120d5a2f）；实现/测试完成（T-20260331-6c11d56a）；复审不通过（T-20260331-cf2a6505，npu_demo 骨架签名绕过 `gen_signature/type mapping`，硬编码 `Memory<float>` 存在类型回归风险）；实现修复完成（T-20260331-9c50615e）；二次复审不通过（T-20260331-38e11ec3，spec 仍写死 `Memory<float>` 且缺少 GK-012A 映射）；spec 收敛完成（T-20260331-8c27baa5）；三次复审不通过（T-20260331-8a0bcc61，GK-014/GK-015/GK-016 拒绝路径与测试名映射仍缺）；当前进入二次 spec 收敛链路（T-20260331-e4ac99b9）。
- 当前执行中（npu_demo）：`G1` spec 收敛（T-20260331-e4ac99b9）。
- 当前外部前置阻塞：无（实现阶段已放行）。
- 当前建议推进顺序：先完成 `G1` 的 spec/test 可追溯性收敛（T-20260331-e4ac99b9）；随后立即回到复审链路确认 spec/实现/测试重新一致，再进入合并/同步确认；当前 `npu_demo` 剩余主链仍聚焦 `G1`。

## 功能简介

定义 `npu_demo` 新后端第一阶段的 `spec` 推进计划。目标不是端到端 launch，而是先把“最终生成的 kernel body 应该长什么样”冻结下来，并把关键桥接点拆成管理员可直接分发的单文件 `spec任务`。

本计划重点解决两个容易漂移的点：

1. `slice` 的分层职责不同：
   - include/api 层：`slice(target, source, offset, size, stride)`
   - operation 层：`out = slice(source, offset, size, stride, space)`
   - dialect / DSL lowering：自动补 `alloc(target)`，再生成目标式 `dma.slice(target, source, ...)`
2. `npu_demo` 只做 body-level helper / codegen：
   - 保留 `Memory<T>`、`Vector`、`view/slice/deslice`、`add`
   - 新增 `npu_demo::KernelContext`
   - 新增 `ctx.get_dynamic_memory<T>(MemorySpace::TSM/TLM)`
   - 不引入 `launch/runtime wrapper`

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/npu_demo_backend_plan.md`](../../ARCHITECTURE/plan/npu_demo_backend_plan.md)
- `spec`：
  - [`spec/include/api/Core.md`](../../spec/include/api/Core.md)
  - [`spec/include/api/Memory.md`](../../spec/include/api/Memory.md)
  - [`spec/include/api/Dma.md`](../../spec/include/api/Dma.md)
  - [`spec/include/api/Nn.md`](../../spec/include/api/Nn.md)
  - [`spec/operation/dma.md`](../../spec/operation/dma.md)
  - [`spec/operation/arch.md`](../../spec/operation/arch.md)
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - `spec/target/npu_demo.md`（计划新增）
  - [`spec/target/registry.md`](../../spec/target/registry.md)
  - `spec/include/npu_demo/npu_demo.md`（计划新增）
- `功能实现`：
  - [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
  - [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
  - [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
  - [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - `include/api/Core.h`（计划新增或对齐）
  - `include/api/Dma.h`（计划新增或对齐）
  - `include/npu_demo/*`（计划新增）
- `test`：
  - [`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)
  - [`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)
  - [`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/target/test_target_registry.py`](../../test/target/test_target_registry.py)
  - `test/include/npu_demo/test_npu_demo.py`（计划新增）

## 采纳的关键约束

这份计划已经吸收了现有会话里其他同事的两类有效意见，并把它们改成了可执行的边界：

- `view(source, offset, size, stride)` 与 `deslice(source, target, offset, size, stride)` 可以在 include/api 与 operation 层保持同名同责。
- `slice` 不能再写成“各层签名完全相同”：include/api 是目标式 helper，operation 是表达式式 helper，DSL lowering 负责补 `alloc` 后桥接到目标式 `dma.slice`。
- `npu_demo v1` 只冻结 body-level/helper 契约，不承诺 launch/runtime/context 构造来源。
- 稳定源码必须避免 `.view<T>()`、`load<...>`、`store<...>`、`memory<rank, type>`、`npu_demo::Memory` 这类旧口径或占位词。

## 第一阶段最终目的

- 让 `gen_kernel(target="npu_demo")` 生成一个可由外部调用的 kernel body C++ 函数。
- 让该函数显式出现 `npu_demo::KernelContext& ctx`、`Memory<T>`、`Vector`、`view/slice/deslice`、`add`、`get_shape/get_stride`、`ctx.thread_id()/ctx.thread_num()`、`ctx.get_dynamic_memory<T>(...)`。
- 让管理员后续分发时不需要先读实现代码，也能知道每个 `spec任务` 该改什么、不该改什么、何时才能继续下一步。

## 第一阶段非目标

- 不支持 `barrier`
- 不支持 `arch.launch_kernel`
- 不支持任何 `launch(...)`、`LaunchConfig`、`LaunchContext`、host wrapper、runtime launch
- 不承诺性能、时序、并发行为与真实 NPU 等价
- 不公开 `npu_demo::Memory`
- 不公开 `.view<T>()`、`load<...>`、`store<...>`、`std::vector`、`std::array`
- 不把 `SM/LM` 当作可用片上空间；第一阶段 `SM/LM=0` 必须走拒绝路径

## 稳定分层边界

### include/api 层

- `view(source, offset, size, stride) -> Memory<T>`
- `slice(target, source, offset, size, stride) -> Status`
- `deslice(source, target, offset, size, stride) -> Status`
- `Vector` 无模板参数，元素固定为 `int64`
- `Memory<T>` 上的统一查询接口是 `get_shape(axis)`、`get_stride(axis)`

### operation 层

- `view(source, offset, size, stride) -> Memory`
- `slice(source, offset, size, stride, space) -> Memory`
- `deslice(source, target, offset, size, stride) -> None`
- operation 层允许用户用“表达式式 `slice(...)`”写 DSL；但这不代表 include/api 层也必须是表达式式签名。

### dialect / DSL lowering 层

- `view(...)` 直接 lower 为 `dma.view`
- `slice(source, offset, size, stride, space)` 必须 lower 为两步：
  1. `tmp = dma.alloc(size, dtype=source.dtype, space=space or source.space)`
  2. `dma.slice(tmp, source, offset, size, stride)`
- `deslice(source, target, offset, size, stride)` 直接 lower 为 `dma.deslice(source, target, ...)`
- `slice(...)` 表达式在 DSL 侧返回的 SSA 值，就是自动补出的 `tmp`

## 唯一金标源码骨架

下面这段不是“仓库现有实现”，而是第一阶段最终要生成到的结构金标。允许变量名、排版、局部缓冲区偏移值不同；不允许把结构改回 `load/store/.view<T>()` 或表达式式 `slice(...)`。

```cpp
#include "include/api/Core.h"
#include "include/api/Memory.h"
#include "include/api/Dma.h"
#include "include/api/Nn.h"
#include "include/npu_demo/npu_demo.h"

void add_npu_demo_kernel(
    npu_demo::KernelContext& ctx,
    Memory<float>& lhs,
    Memory<float>& rhs,
    Memory<float>& result) {
  const long long n = lhs.get_shape(0);
  const long long thread_id = ctx.thread_id();
  const long long thread_num = ctx.thread_num();

  auto tsm = ctx.get_dynamic_memory<float>(MemorySpace::TSM);
  auto tlm = ctx.get_dynamic_memory<float>(MemorySpace::TLM);

  long long lhs_local_offset_buf[1] = {0};
  long long rhs_local_offset_buf[1] = {16};
  long long out_local_offset_buf[1] = {0};
  long long tile_size_buf[1] = {16};
  long long unit_stride_buf[1] = {1};

  Vector lhs_local_offset(lhs_local_offset_buf, 1);
  Vector rhs_local_offset(rhs_local_offset_buf, 1);
  Vector out_local_offset(out_local_offset_buf, 1);
  Vector tile_size(tile_size_buf, 1);
  Vector unit_stride(unit_stride_buf, 1);

  auto lhs_tile = view(tsm, lhs_local_offset, tile_size, unit_stride);
  auto rhs_tile = view(tsm, rhs_local_offset, tile_size, unit_stride);
  auto out_tile = view(tlm, out_local_offset, tile_size, unit_stride);

  for (long long i = thread_id; i < n; i += thread_num) {
    long long gm_offset_buf[1] = {i};
    Vector gm_offset(gm_offset_buf, 1);

    slice(lhs_tile, lhs, gm_offset, tile_size, unit_stride);
    slice(rhs_tile, rhs, gm_offset, tile_size, unit_stride);
    add(lhs_tile, rhs_tile, out_tile);
    deslice(out_tile, result, gm_offset, tile_size, unit_stride);
  }
}
```

### 金标必须包含的片段

- `npu_demo::KernelContext& ctx`
- `Memory<float>& lhs` / `rhs` / `result`
- `lhs.get_shape(0)`
- `ctx.thread_id()` 与 `ctx.thread_num()`
- `ctx.get_dynamic_memory<float>(MemorySpace::TSM)`
- `ctx.get_dynamic_memory<float>(MemorySpace::TLM)`
- `Vector`
- `view(`
- `slice(`，且调用形态是 `slice(target, source, offset, size, stride)`
- `deslice(`
- `add(`
- `for (long long i = thread_id; i < n; i += thread_num)`

### 金标禁止出现的片段

- `.view<`
- `load<`
- `store<`
- `auto tile = slice(source, ... )`
- `npu_demo::Memory`
- `memory<rank, type>`
- `std::vector`
- `std::array`
- `launch(`
- `arch.launch_kernel`
- `barrier`

## 当前断点

1. [`spec/include/api/Dma.md`](../../spec/include/api/Dma.md) 已对齐目标式 `slice(target, source, ...)`；本计划、提示词与记忆文件也已同步到新口径。当前剩余断点从 `operation` 层开始。
2. [`spec/operation/dma.md`](../../spec/operation/dma.md) 仍把 `slice` 当作与 include 层同签名的自然延伸，没有显式冻结“表达式式 `slice(...)` + lowering 自动补 alloc”的桥接。
3. [`spec/dialect/dma.md`](../../spec/dialect/dma.md) 仍以结果式 `dma.slice` 为主，没有冻结目标式 `dma.slice(target, source, ...)`。
4. [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 与 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 仍把 `slice(...)` 视为直接返回 `DmaSliceOp` 结果，没有写出自动 `alloc` 的 lowering 契约。
5. [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 与 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 还没有把 `npu_demo` 的金标源码固定到目标式 `slice(target, source, ...)`。

## 管理规则

- 本计划只写给管理员分发用的 `spec任务`，不直接给执行者派单。
- 每个任务默认只改 `1` 个 `md` 文件。
- 同一 `md` 文件上的多个任务只能串行；不同 `md` 文件上的任务，在依赖满足时可并行。
- 依赖统一写成硬门禁：`未满足则不得开始`。
- 验收统一写成：`测试函数名 + 输入 + 预期输出/预期报错`。
- 由于管理员当前新规是“每次完成后只能新建 1 个后续任务”，下面的并行图表示“逻辑上可并行”，不表示管理员必须同时分发多个任务。

## 任务总览

| 任务 ID | 可改文件 | 目标 | READY_IF | 下游 |
| --- | --- | --- | --- | --- |
| A0 | [`spec/include/api/Core.md`](../../spec/include/api/Core.md) | 固定 `Vector` 为无模板、固定 `int64` 的统一坐标类型 | 无 | A1 E0 G1 |
| A1 | [`spec/include/api/Dma.md`](../../spec/include/api/Dma.md) | 冻结 include 层 `slice(target, source, offset, size, stride)` | A0 DONE | O1 D1 E1 G1 |
| O1 | [`spec/operation/dma.md`](../../spec/operation/dma.md) | 冻结 operation 层 `slice(source, offset, size, stride, space) -> Memory`，并写清 lowering 自动补 `alloc` | A1 DONE | D1 M1 M2 |
| D1 | [`spec/dialect/dma.md`](../../spec/dialect/dma.md) | 冻结目标式 `dma.slice(target, source, offsets, sizes, strides)` 与 operation->dialect 映射 | O1 DONE | M1 M2 E1 |
| M1 | [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) | 冻结 `slice(...)` 在 emit_mlir 链路中自动 `alloc + dma.slice` 的规则 | D1 DONE | E1 |
| M2 | [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) | 冻结 `slice(...)` 在 build_func_op/mlir_gen 链路中自动 `alloc + dma.slice` 的规则 | D1 DONE | E1 |
| T1 | `spec/target/npu_demo.md` | 新增 `npu_demo` target 身份、能力矩阵与硬件模板 | 无 | T2 R1 |
| T2 | [`spec/target/registry.md`](../../spec/target/registry.md) | 冻结 `npu_demo` 注册模板与硬件字段校验 | T1 DONE | R1 R2 |
| R1 | [`spec/operation/arch.md`](../../spec/operation/arch.md) | 冻结 `block/thread/subthread` 查询 helper | T2 DONE | R2 C1 E0 |
| R2 | [`spec/operation/arch.md`](../../spec/operation/arch.md) | 冻结 `get_dynamic_memory` 与 `SM/LM=0` 拒绝路径 | R1 DONE | C2 E1 |
| C1 | `spec/include/npu_demo/npu_demo.md` | 冻结 `KernelContext` 的 id/count accessor | R1 DONE | C2 E0 G1 |
| C2 | `spec/include/npu_demo/npu_demo.md` | 冻结 `ctx.get_dynamic_memory<T>(MemorySpace::TSM/TLM)` | R2 DONE 且 C1 DONE | E1 G1 |
| E0 | [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) | 冻结 `get_shape/get_stride`、`ctx.thread_id/thread_num` 到 `npu_demo` C++ 文本的映射 | A0 DONE 且 R1 DONE 且 C1 DONE | E1 G1 |
| E1 | [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) | 冻结 `view/slice/deslice/add/get_dynamic_memory` 到 `npu_demo` C++ 文本的映射，并拒绝旧口径 | M1 DONE 且 M2 DONE 且 R2 DONE 且 C2 DONE 且 E0 DONE | G1 |
| G1 | [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) | 冻结 `npu_demo` kernel body 金标源码骨架与禁止项 | A1 DONE 且 C2 DONE 且 E1 DONE | 后续实现/测试链路 |

## 逻辑并行图

### 车道 1：DMA `slice` 桥接链

`A0 -> A1 -> O1 -> D1 -> M1`

`D1 -> M2`

说明：
- `M1` 与 `M2` 在 `D1 DONE` 后可逻辑并行，因为分别改不同文件。
- `A1/O1/D1` 不能并行，因为是跨层同一概念的冻结链，必须先把公开签名说清，再写映射。

### 车道 2：`npu_demo` target / arch / include 链

`T1 -> T2 -> R1 -> R2`

`R1 -> C1`

`R2 + C1 -> C2`

说明：
- `C1` 与 `R2` 可逻辑并行，因为分别冻结 `KernelContext` 访问器与 `get_dynamic_memory` 语义来源。
- `C2` 必须等 `R2` 与 `C1` 都完成，否则 `get_dynamic_memory<T>(space)` 的可见行为和上下文宿主都不完整。

### 车道 3：`emit_c / gen_kernel` 收口链

`A0 + R1 + C1 -> E0`

`M1 + M2 + R2 + C2 + E0 -> E1`

`A1 + C2 + E1 -> G1`

说明：
- `E0` 先冻结“基础 helper 文本形态”，避免 `E1` 同时混写 metadata helper 和 DMA helper。
- `G1` 必须最后做，因为它要引用 `slice` 的最终源码形态、`KernelContext` 形态和 `emit_c` 的禁止项口径。

## 任务明细

### A0. 在 `spec/include/api/Core.md` 固定 `Vector`

- `任务类型`：`spec任务`
- `可改文件`：[`spec/include/api/Core.md`](../../spec/include/api/Core.md)
- `目标`：明确 `Vector` 没有模板参数、元素固定为 `int64`、不依赖标准库。
- `边界`：不定义 `slice/deslice/view` 的业务职责。
- `注意事项`：不能再把 `Vector<T>`、`std::vector<long long>`、`std::array<long long, N>` 写成稳定公开名。
- `依赖`：无。
- `下游需要覆盖层`：`spec/include/api/Dma.md`、`spec/dsl/emit_c.md`、`spec/dsl/gen_kernel.md`。
- `验收标准`：
  - `test_api_core_vector_uses_fixed_int64_without_template_parameter`
    - 输入：`long long coords_buf[3] = {5, 0, 7}`，构造 `Vector coords(coords_buf, 3)`。
    - 预期输出：文档明确 `coords.size() == 3`、`coords[0] == 5`；公开契约中不存在 `Vector<T>`、`Vector<long long>`、`std::vector`、`std::array`。
- `验证命令`：

```bash
rg -n 'Vector<T>|Vector<long long>|std::vector|std::array' spec/include/api/Core.md -S
```

### A1. 在 `spec/include/api/Dma.md` 冻结 include 层目标式 `slice`

- `任务类型`：`spec任务`
- `可改文件`：[`spec/include/api/Dma.md`](../../spec/include/api/Dma.md)
- `目标`：新增并冻结 `slice(target, source, offset, size, stride)` 的公开合同。
- `边界`：不把 `slice` 写回表达式式返回值；不让 include/api 层隐式分配 `target`。
- `注意事项`：必须明确 `target.shape == size`，返回值是 `Status`，不是 `Memory<T>`。
- `依赖`：`A0 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`spec/operation/dma.md`、`spec/dialect/dma.md`、`spec/dsl/emit_c.md`、`spec/dsl/gen_kernel.md`。
- `验收标准`：
  - `test_api_dma_slice_reads_source_region_into_preallocated_target`
    - 输入：`target` 为 `shape=[16]` 的 `Memory<float>`，`source` 为 rank=1 的 `Memory<float>`，`offset=[32]`，`size=[16]`，`stride=[1]`。
    - 预期输出：文档明确签名是 `slice(target, source, offset, size, stride)`，返回 `StatusCode::kOk`；文档中不存在 `slice(source, ...) -> Memory<T>` 的 include/api 公开签名。
- `验证命令`：

```bash
rg -n 'slice\(target, source, offset, size, stride\)|slice\(source, offset, size, stride\)' spec/include/api/Dma.md -S
```

### O1. 在 `spec/operation/dma.md` 冻结表达式式 `slice`

- `任务类型`：`spec任务`
- `可改文件`：[`spec/operation/dma.md`](../../spec/operation/dma.md)
- `目标`：明确 `slice(source, offset, size, stride, space) -> Memory` 是用户侧表达式式 helper，并写清 lowering 自动补 `alloc(target)`。
- `边界`：不要求 operation 层与 include/api 层同签名；不把 `target` 暴露给用户侧 operation 签名。
- `注意事项`：必须显式写出“operation.slice 的结果值，在 lowering 后对应自动分配的 `target`”；不能只写“语义等价于 load”。
- `依赖`：`A1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`spec/dialect/dma.md`、`spec/dsl/emit_mlir.md`、`spec/dsl/mlir_gen.md`。
- `验收标准`：
  - `test_operation_dma_slice_returns_memory_and_declares_lowering_alloc_bridge`
    - 输入：`source` 为 rank=1 的 `Memory<float>`，`offset=[32]`，`size=[16]`，`stride=[1]`，`space=MemorySpace.TSM`。
    - 预期输出：文档明确 `slice(source, offset, size, stride, space)` 返回 `shape=[16]`、`space=TSM` 的 `Memory<float>`；并明确 lowering 时必须先创建 `alloc(shape=[16], dtype=float, space=TSM)`，再桥接到目标式 `dma.slice(target, source, ...)`。
- `验证命令`：

```bash
rg -n '### slice\(source, offsets, sizes, strides=None, space=None\)|lowering|alloc|dma.slice\(target, source' spec/operation/dma.md -S
```

### D1. 在 `spec/dialect/dma.md` 冻结目标式 `dma.slice`

- `任务类型`：`spec任务`
- `可改文件`：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- `目标`：把 `dma.slice` 冻结为目标式 op：`dma.slice(target, source, offsets, sizes, strides)`。
- `边界`：不再把 `dma.slice` 写成“结果式返回 op”；不把隐式分配留在 dialect 层。
- `注意事项`：必须把 operation->dialect 映射写成：`operation.slice(...) -> dma.alloc + dma.slice(target, source, ...)`。
- `依赖`：`O1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`spec/dsl/emit_mlir.md`、`spec/dsl/mlir_gen.md`、`spec/dsl/emit_c.md`。
- `验收标准`：
  - `test_dma_dialect_slice_uses_explicit_target_operand`
    - 输入：`target` 为 `!nn.memory<[16],[1],f32,#nn.space<TSM>>`，`source` 为 `!nn.memory<[128],[1],f32,#nn.space<GM>>`，`offsets=[!symbol.int<"32">]`，`sizes=[!symbol.int<"16">]`，`strides=[!symbol.int<"1">]`。
    - 预期输出：文档明确 `dma.slice` 不返回新的 memory result；切片结果写入 `target`；operation 层表达式返回值来自前置 `dma.alloc` 的结果，而不是 `dma.slice` 自身返回值。
- `验证命令`：

```bash
rg -n 'dma.slice\(target, source|operation.slice\(.*\)-> dma.alloc \+ dma.slice|不返回新的 memory result' spec/dialect/dma.md -S
```

### M1. 在 `spec/dsl/emit_mlir.md` 冻结 `slice` 的 emit 规则

- `任务类型`：`spec任务`
- `可改文件`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `目标`：写清 DSL 中表达式式 `slice(...)` 在 emit_mlir 链路中必须先发射 `dma.alloc`，再发射目标式 `dma.slice(target, source, ...)`。
- `边界`：不改 `view/deslice` 的基本职责；不引入 `launch/barrier`。
- `注意事项`：必须写出“表达式返回值绑定到自动分配的 target SSA 值”，否则实现侧容易误回退到结果式 `DmaSliceOp`。
- `依赖`：`D1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`kernel_gen/dsl/emit_mlir.py`、`test/dsl/test_emit_mlir.py`。
- `验收标准`：
  - `test_emit_mlir_slice_expression_lowers_to_alloc_then_target_slice`
    - 输入：DSL 函数体中 `tile = slice(src, [32], [16], [1], MemorySpace.TSM)`。
    - 预期输出：MLIR 中先出现一个 `dma.alloc` 结果 `%tile`，随后出现 `dma.slice %tile, %src, ...`；表达式 `tile` 绑定的是 `%tile`，不是 `dma.slice` 的结果值。
- `验证命令`：

```bash
rg -n 'slice\(\.\.\.\).*dma.alloc|dma.slice %|表达式返回值绑定到 alloc 结果|DmaSliceOp 不直接作为表达式结果' spec/dsl/emit_mlir.md -S
```

### M2. 在 `spec/dsl/mlir_gen.md` 冻结 `slice` 的 build_func_op 规则

- `任务类型`：`spec任务`
- `可改文件`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `目标`：把 `build_func_op(...)` / `build_func_op_from_ast(...)` 中的 `slice(...)` lowering 规则冻结为 `dma.alloc + dma.slice(target, source, ...)`。
- `边界`：不把这条规则写成 emit_mlir 专属特例；必须是 mlir_gen 链路正式契约。
- `注意事项`：必须写出 build_func_op 中返回值、局部变量与 `alloc` 结果的绑定规则。
- `依赖`：`D1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`kernel_gen/dsl/mlir_gen.py`、`test/dsl/test_mlir_gen.py`。
- `验收标准`：
  - `test_build_func_op_slice_expression_lowers_to_alloc_then_target_slice`
    - 输入：Python DSL 函数 `def f(src: Memory) -> Memory: return slice(src, [32], [16], [1], MemorySpace.TSM)`。
    - 预期输出：生成的 `func.func` 中先出现 `dma.alloc`，后出现 `dma.slice(target, source, ...)`；`func.return` 返回的是前面 `dma.alloc` 的结果 SSA 值。
- `验证命令`：

```bash
rg -n 'build_func_op.*slice|dma.alloc|dma.slice\(target, source|func.return 返回 alloc 结果' spec/dsl/mlir_gen.md -S
```

### T1. 新增 `spec/target/npu_demo.md`

- `任务类型`：`spec任务`
- `可改文件`：`spec/target/npu_demo.md`
- `目标`：定义 `npu_demo` 的 target 身份、支持能力与固定硬件模板。
- `边界`：不写 launch/runtime；不把 `barrier`、`arch.launch_kernel` 写进 supported。
- `注意事项`：硬件值必须写成整数文字，不得写 `24*1024`。
- `依赖`：无。
- `下游需要覆盖层`：`spec/target/registry.md`、`spec/operation/arch.md`。
- `验收标准`：
  - `test_target_npu_demo_declares_static_hardware_template`
    - 输入：`block_num=6`、`thread_num=8`、`subthread_num=1`、`sm_memory_size=0`、`lm_memory_size=0`、`tsm_memory_size=24576`、`tlm_memory_size=2048`。
    - 预期输出：文档明确这些字段存在；`arch.launch_kernel` 与 `arch.barrier` 明确为不支持项。
- `验证命令`：

```bash
rg -n 'block_num=6|thread_num=8|subthread_num=1|sm_memory_size=0|lm_memory_size=0|tsm_memory_size=24576|tlm_memory_size=2048|arch.launch_kernel|arch.barrier' spec/target/npu_demo.md -S
```

### T2. 在 `spec/target/registry.md` 冻结 `npu_demo` 注册模板

- `任务类型`：`spec任务`
- `可改文件`：[`spec/target/registry.md`](../../spec/target/registry.md)
- `目标`：增加 `npu_demo` 的注册模板与硬件字段校验规则。
- `边界`：不引入与 `npu_demo` 无关的新字段。
- `注意事项`：必须明确 `hw.*` 只能是整数文字；表达式型文字必须拒绝。
- `依赖`：`T1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`kernel_gen/target/registry.py`、`test/target/test_target_registry.py`。
- `验收标准`：
  - `test_registry_rejects_non_literal_npu_demo_hardware_value`
    - 输入：`hw.tsm_memory_size=24*1024`。
    - 预期输出：文档要求抛 `ValueError`，错误消息包含 `must be integer literal`。
  - `test_registry_marks_launch_and_barrier_as_unsupported_on_npu_demo`
    - 输入：`arch.unsupported_ops=arch.launch_kernel,arch.barrier`。
    - 预期输出：文档明确这两个 op 在 `npu_demo` 上返回 `False`。
- `验证命令`：

```bash
rg -n 'must be integer literal|arch.unsupported_ops|arch.launch_kernel|arch.barrier' spec/target/registry.md -S
```

### R1. 在 `spec/operation/arch.md` 冻结 id/count helper

- `任务类型`：`spec任务`
- `可改文件`：[`spec/operation/arch.md`](../../spec/operation/arch.md)
- `目标`：增加 `get_block_num/get_thread_num/get_subthread_num` 在 `npu_demo` 上的回退语义。
- `边界`：不新增 `barrier`；不新增 `launch_kernel` 成功路径。
- `注意事项`：必须写成确定值 `SymbolDim(6/8/1)`，不能写成“由后端自定”。
- `依赖`：`T2 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`spec/include/npu_demo/npu_demo.md`、`spec/dsl/emit_c.md`。
- `验收标准`：
  - `test_operation_arch_counts_return_npu_demo_static_values`
    - 输入：current target=`npu_demo`。
    - 预期输出：`get_block_num()==SymbolDim(6)`、`get_thread_num()==SymbolDim(8)`、`get_subthread_num()==SymbolDim(1)`。
- `验证命令`：

```bash
rg -n 'get_block_num|get_thread_num|get_subthread_num|SymbolDim\(6\)|SymbolDim\(8\)|SymbolDim\(1\)' spec/operation/arch.md -S
```

### R2. 在 `spec/operation/arch.md` 冻结 `get_dynamic_memory`

- `任务类型`：`spec任务`
- `可改文件`：[`spec/operation/arch.md`](../../spec/operation/arch.md)
- `目标`：定义 `get_dynamic_memory(MemorySpace.TSM/TLM)` 成功路径，以及 `SM/LM=0` 的拒绝路径。
- `边界`：不新增 `GM` 成功路径；不新增 `barrier`。
- `注意事项`：必须写清 `TSM` 返回 `shape=[24576]`，`TLM` 返回 `shape=[2048]`，`stride=[1]`。
- `依赖`：`R1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`spec/include/npu_demo/npu_demo.md`、`spec/dsl/emit_c.md`。
- `验收标准`：
  - `test_operation_arch_get_dynamic_memory_returns_tsm_view_on_npu_demo`
    - 输入：current target=`npu_demo`，调用 `get_dynamic_memory(MemorySpace.TSM)`。
    - 预期输出：返回 `space=TSM`、`shape=[24576]`、`stride=[1]` 的 `Memory` 视图。
  - `test_operation_arch_get_dynamic_memory_rejects_sm_when_size_is_zero`
    - 输入：current target=`npu_demo`，调用 `get_dynamic_memory(MemorySpace.SM)`。
    - 预期输出：抛 `ValueError`，错误消息包含 `sm_memory_size=0`。
- `验证命令`：

```bash
rg -n 'TSM|TLM|24576|2048|sm_memory_size=0|lm_memory_size=0' spec/operation/arch.md -S
```

### C1. 新增 `spec/include/npu_demo/npu_demo.md` 中的 `KernelContext`

- `任务类型`：`spec任务`
- `可改文件`：`spec/include/npu_demo/npu_demo.md`
- `目标`：冻结 `npu_demo::KernelContext` 的 `block_id/block_num/thread_id/thread_num/subthread_id/subthread_num` accessor。
- `边界`：不写构造流程；不写 launch/runtime wrapper。
- `注意事项`：这是 backend 私有 include 合同；参数 memory 类型仍统一使用 `Memory<T>`。
- `依赖`：`R1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`spec/dsl/emit_c.md`、`spec/dsl/gen_kernel.md`。
- `验收标准`：
  - `test_npu_demo_kernel_context_exposes_id_and_count_accessors`
    - 输入：一个预置 `block_id=1, block_num=6, thread_id=3, thread_num=8, subthread_id=0, subthread_num=1` 的 `KernelContext`。
    - 预期输出：对应 accessor 返回 `1/6/3/8/0/1`。
- `验证命令`：

```bash
rg -n 'KernelContext|block_id\(|block_num\(|thread_id\(|thread_num\(|subthread_id\(|subthread_num\(' spec/include/npu_demo/npu_demo.md -S
```

### C2. 在 `spec/include/npu_demo/npu_demo.md` 冻结 `get_dynamic_memory<T>(space)`

- `任务类型`：`spec任务`
- `可改文件`：`spec/include/npu_demo/npu_demo.md`
- `目标`：定义 `template<typename T> Memory<T> get_dynamic_memory(MemorySpace space)`。
- `边界`：不写 `.view<T>()`；不写 `npu_demo::Memory`；不允许 `get_dynamic_memory<TSM>()` 这类空间模板化写法。
- `注意事项`：模板参数只能是元素类型，`space` 必须走 `MemorySpace` 枚举值。
- `依赖`：`R2 DONE` 且 `C1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`spec/dsl/emit_c.md`、`spec/dsl/gen_kernel.md`。
- `验收标准`：
  - `test_npu_demo_kernel_context_returns_typed_tsm_memory`
    - 输入：调用 `ctx.get_dynamic_memory<float>(MemorySpace::TSM)`。
    - 预期输出：返回 `Memory<float>`，`space=TSM`，`shape=[24576]`，`stride=[1]`。
  - `test_npu_demo_kernel_context_rejects_sm_when_size_zero`
    - 输入：调用 `ctx.get_dynamic_memory<float>(MemorySpace::SM)`。
    - 预期输出：抛错误，消息包含 `sm_memory_size=0`。
- `验证命令`：

```bash
rg -n 'get_dynamic_memory<.*>\(MemorySpace::TSM\)|get_dynamic_memory<.*>\(MemorySpace::TLM\)|get_dynamic_memory<TSM>' spec/include/npu_demo/npu_demo.md -S
```

### E0. 在 `spec/dsl/emit_c.md` 冻结基础 helper 映射

- `任务类型`：`spec任务`
- `可改文件`：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
- `目标`：先单独冻结 `get_shape/get_stride` 与 `ctx.thread_id/thread_num` 的文本映射。
- `边界`：不在本任务写 `slice/view/deslice/get_dynamic_memory/add`。
- `注意事项`：这是为了把 `emit_c` 拆成更细的两个任务，避免一个任务同时改 metadata helper 与 DMA helper。
- `依赖`：`A0 DONE` 且 `R1 DONE` 且 `C1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`kernel_gen/dsl/emit_c.py`、`test/dsl/test_emit_c.py`。
- `验收标准`：
  - `test_emit_c_npu_demo_emits_memory_shape_and_stride_queries`
    - 输入：`target="npu_demo"` 下发射 `lhs.get_shape(0)` 与 `lhs.get_stride(0)`。
    - 预期输出：生成文本包含 `lhs.get_shape(0)` 与 `lhs.get_stride(0)`。
  - `test_emit_c_npu_demo_emits_thread_helpers`
    - 输入：`target="npu_demo"` 下发射 `get_thread_id()` 与 `get_thread_num()`。
    - 预期输出：生成文本包含 `ctx.thread_id()` 与 `ctx.thread_num()`。
- `验证命令`：

```bash
rg -n 'get_shape\(|get_stride\(|ctx\.thread_id\(|ctx\.thread_num\(' spec/dsl/emit_c.md -S
```

### E1. 在 `spec/dsl/emit_c.md` 冻结 DMA/helper 到 `npu_demo` 源码的映射

- `任务类型`：`spec任务`
- `可改文件`：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
- `目标`：冻结 `view/slice/deslice/add/get_dynamic_memory` 到 `npu_demo` C++ 文本的映射。
- `边界`：明确拒绝 `.view<T>()`、`load<...>`、`store<...>`、`launch`、`barrier`。
- `注意事项`：`slice` 的生成文本必须是 `slice(target, source, offset, size, stride)`，不能再输出表达式式 `slice(source, ...)`。
- `依赖`：`M1 DONE` 且 `M2 DONE` 且 `R2 DONE` 且 `C2 DONE` 且 `E0 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`kernel_gen/dsl/emit_c.py`、`test/dsl/test_emit_c.py`、`spec/dsl/gen_kernel.md`。
- `验收标准`：
  - `test_emit_c_npu_demo_emits_typed_dynamic_memory_query`
    - 输入：`target="npu_demo"` 下发射 `get_dynamic_memory(MemorySpace.TSM)`，结果类型为 `float`。
    - 预期输出：生成文本包含 `ctx.get_dynamic_memory<float>(MemorySpace::TSM)`。
  - `test_emit_c_npu_demo_emits_target_form_slice`
    - 输入：发射目标式 `dma.slice`，其 `target` 是本地 tile，`source` 是全局 memory，`offset=[32]`，`size=[16]`，`stride=[1]`。
    - 预期输出：生成文本包含 `slice(target, source, offset, size, stride)`；不包含 `auto tile = slice(source, ...)`。
  - `test_emit_c_npu_demo_emits_view_deslice_and_add`
    - 输入：发射 `dma.view`、`dma.deslice`、`nn.add`。
    - 预期输出：生成文本分别包含 `view(`、`deslice(`、`add(`。
  - `test_emit_c_npu_demo_rejects_legacy_tokens`
    - 输入：检查 `npu_demo` 段落。
    - 预期输出：文档明确 `.view<`、`load<`、`store<`、`launch`、`barrier` 是第一阶段禁止项。
- `验证命令`：

```bash
rg -n 'ctx\.get_dynamic_memory<|view\(|slice\(target, source|deslice\(|add\(|\.view<|load<|store<|launch|barrier' spec/dsl/emit_c.md -S
```

### G1. 在 `spec/dsl/gen_kernel.md` 冻结 `npu_demo` 金标源码骨架

- `任务类型`：`spec任务`
- `可改文件`：[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- `目标`：把本计划里的 `npu_demo` 金标 kernel body 缩写成规范正文中的“唯一目标形态 + 禁止项”。
- `边界`：不写 host wrapper；不写 launch；不写 barrier。
- `注意事项`：必须把 `slice(target, source, ...)` 的目标式形态写入金标；不能再沿用 `auto tile = slice(source, ...)` 旧骨架。
- `依赖`：`A1 DONE` 且 `C2 DONE` 且 `E1 DONE`。未满足则不得开始。
- `下游需要覆盖层`：`kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py`。
- `验收标准`：
  - `test_gen_kernel_npu_demo_emits_body_level_gold_skeleton`
    - 输入：一个逐元素 add 的 `npu_demo` kernel。
    - 预期输出：生成源码同时包含 `npu_demo::KernelContext& ctx`、`Memory<float>& lhs`、`Memory<float>& rhs`、`Memory<float>& result`、`lhs.get_shape(0)`、`ctx.thread_id()`、`ctx.thread_num()`、`ctx.get_dynamic_memory<float>(MemorySpace::TSM)`、`ctx.get_dynamic_memory<float>(MemorySpace::TLM)`、`Vector`、`view(`、`slice(target, source, offset, size, stride)`、`deslice(`、`add(`、`for (long long i = thread_id; i < n; i += thread_num)`。
  - `test_gen_kernel_npu_demo_rejects_forbidden_legacy_tokens`
    - 输入：对金标生成源码执行负向检查。
    - 预期输出：源码中不包含 `.view<`、`load<`、`store<`、`auto tile = slice(source`、`npu_demo::Memory`、`launch(`、`arch.launch_kernel`、`barrier`。
- `验证命令`：

```bash
rg -n 'npu_demo::KernelContext& ctx|Memory<float>& lhs|Memory<float>& rhs|Memory<float>& result|lhs.get_shape\(0\)|ctx\.thread_id\(|ctx\.thread_num\(|ctx\.get_dynamic_memory<float>\(MemorySpace::TSM\)|ctx\.get_dynamic_memory<float>\(MemorySpace::TLM\)|Vector|view\(|slice\(target, source, offset, size, stride\)|deslice\(|add\(|for \(long long i = thread_id; i < n; i \+= thread_num\)|\.view<|load<|store<|auto tile = slice\(source|npu_demo::Memory|launch\(|arch.launch_kernel|barrier' spec/dsl/gen_kernel.md -S
```

## 自检结果

- 已把 `slice` 的三层签名拆清：include/api、operation、dialect/DSL lowering 不再混写。
- 已把 `operation.slice(...)` 到 `dma.alloc + dma.slice(target, source, ...)` 的桥接写成独立任务链。
- 已把 `emit_c` 拆成 `E0/E1` 两个单文件任务，避免一个任务同时收敛 metadata helper 与 DMA helper。
- 已把 `npu_demo` 的 kernel body 金标改成目标式 `slice(target, source, ...)`，删除了旧的表达式式 `slice(source, ...)` 金标。
- 仍然保留了逻辑并行图，但明确说明了管理员当前新规下只能按 READY 队列逐次放行。
- 当前文本里不再把说明性占位词写成仓库已存在公开接口。
