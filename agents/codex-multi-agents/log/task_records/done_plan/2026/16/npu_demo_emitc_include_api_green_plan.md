# npu_demo_emitc_include_api_green_plan.md

## 文档信息

- 创建者：`榕`
- 最后一次更改：`睡觉小分队`
- 目标 `spec`：
  - [`spec/include/api/Core.md`](../../spec/include/api/Core.md)
  - [`spec/include/api/Memory.md`](../../spec/include/api/Memory.md)
  - [`spec/include/api/Dma.md`](../../spec/include/api/Dma.md)
  - [`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)
  - 新增 [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md)
  - [`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- 目标 `API`：
  - [`include/api/Core.h`](../../include/api/Core.h)
  - [`include/api/Memory.h`](../../include/api/Memory.h)
  - [`include/api/Dma.h`](../../include/api/Dma.h)
  - [`include/api/Arch.h`](../../include/api/Arch.h)
  - 新增 [`include/api/Kernel.h`](../../include/api/Kernel.h)
  - 删除 [`include/api/Nn.h`](../../include/api/Nn.h)
- 目标 `test`：
  - [`test/include/api/test_core.py`](../../test/include/api/test_core.py)
  - [`test/include/api/test_memory.py`](../../test/include/api/test_memory.py)
  - [`test/include/api/test_dma.py`](../../test/include/api/test_dma.py)
  - [`test/include/api/test_arch.py`](../../test/include/api/test_arch.py)
  - `test/include/api/test_kernel.py`（由执行者补齐）
  - [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)
  - [`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 目标 `验收资产`：
  - [`expectation/dsl/emit_c/npu_demo`](../../expectation/dsl/emit_c/npu_demo)
  - [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier)
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)
- 目标 `功能实现`：
  - [`include/npu_demo/Core.h`](../../include/npu_demo/Core.h)
  - [`include/npu_demo/Memory.h`](../../include/npu_demo/Memory.h)
  - [`include/npu_demo/Dma.h`](../../include/npu_demo/Dma.h)
  - [`include/npu_demo/Arch.h`](../../include/npu_demo/Arch.h)
  - [`include/npu_demo/Kernel.h`](../../include/npu_demo/Kernel.h)
  - [`include/npu_demo/npu_demo.h`](../../include/npu_demo/npu_demo.h)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260419-emitc-api-s1-core-memory-dma-spec` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s1-core-memory-dma-spec.md` |
| S2 | 无 | `wt-20260419-emitc-api-s2-arch-spec` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s2-arch-spec.md` |
| S3 | 无 | `wt-20260419-emitc-api-s3-kernel-spec` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s3-kernel-spec.md` |
| S4 | S1 | `wt-20260419-emitc-api-s4-core-memory-dma-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s4-core-memory-dma-build.md` |
| S5 | S2 | `wt-20260419-emitc-api-s5-arch-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s5-arch-build.md` |
| S6 | S3 | `wt-20260419-emitc-api-s6-kernel-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s6-kernel-build.md` |
| S7 | S4 | `wt-20260419-emitc-api-s7-core-memory-dma-review` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s7-core-memory-dma-review.md` |
| S8 | S5 | `wt-20260419-emitc-api-s8-arch-review` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s8-arch-review.md` |
| S9 | S6 | `wt-20260419-emitc-api-s9-kernel-review` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s9-kernel-review.md` |
| S10 | S7 | `wt-20260419-emitc-api-s10-dma-emitc-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s10-dma-emitc-build.md` |
| S11 | S8 | `wt-20260419-emitc-api-s11-arch-gen-kernel-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s11-arch-gen-kernel-build.md` |
| S12 | S9 | `wt-20260419-emitc-api-s12-kernel-emitc-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s12-kernel-emitc-build.md` |
| S13 | S7 | `wt-20260419-emitc-api-s13-symbol-emitc-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s13-symbol-emitc-build.md` |
| S14 | S10,S13 | `wt-20260419-emitc-api-s14-dma-symbol-review` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s14-dma-symbol-review.md` |
| S15 | S11,S12 | `wt-20260419-emitc-api-s15-arch-kernel-review` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s15-arch-kernel-review.md` |
| S16 | S14,S15 | `wt-20260419-emitc-api-s16-execute-engine-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s16-execute-engine-build.md` |
| S17 | S16 | `wt-20260419-emitc-api-s17-execute-engine-review` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s17-execute-engine-review.md` |
| S18 | S14,S15,S17 | `wt-20260419-emitc-api-s18-cleanup-build` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s18-cleanup-build.md` |
| S19 | S18 | `wt-20260419-emitc-api-s19-final-review` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s19-final-review.md` |

## 并行约束

- `S1 / S2 / S3` 可并行。
- `S4 / S5 / S6` 可并行。
- `S10 / S11 / S12 / S13` 可并行。
- `S16` 必须等待 `S14` 与 `S15` 都完成，确保 execute_engine 依赖的 DMA、Arch、Kernel、Symbol 链路都已过 review。

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`任务已收口到 19 个阶段，仍保持 spec/build/review 主链；S1-S3、S4-S6、S10-S13 可并行，S16 串在 S14/S15 之后、S18 再串 S17，依赖关系合理。公开 API、expectation 真源、include/api 与 include/npu_demo 的分层清楚，旧公开名残留消费者已点名并分类，按当前版本可直接建任务推进。`

## 计划目标

- 以 `spec/include/api` 定义唯一公开接口，去掉当前 `emit_c` 未覆盖的公开旧接口。
- 删除 `include/api/Nn.h` 与对应公开 spec，建立 `Kernel` 作为 kernel dialect emit 的唯一公共 API 承载层。
- 统一 `Memory / Dma / Arch / Kernel` 四层公开接口的参数顺序、模板顺序、输出参数语义与查询口径。
- 让 [`expectation/dsl/emit_c/npu_demo`](../../expectation/dsl/emit_c/npu_demo)、[`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 与 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 成为黑盒合同真源。
- 让 `emit_c.py` 与 `gen_kernel.py` 只消费 `include/api` 的统一接口，不再维护公开行为上的 target 特判。
- 把 npu_demo 的 runtime、launch、barrier、dynamic memory 与其他 target 特性收口在 `include/npu_demo` 私有实现层。

## 当前基线

- 当前公开合同：
  - [`spec/include/api`](../../spec/include/api) 已存在 `Core / Memory / Dma / Arch / Nn`，但没有 `Kernel`，且 `Nn` 与实际 kernel dialect emit 口径不一致。
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 仍保留旧的 `npu_demo` 节点级 helper 说明，包含部分旧顺序和旧 helper 约束。
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 仍把 `target="npu_demo"` 受控 `builtin.module` 收口为严格 `body + wrapper` 双函数输入。
- 当前公开 API：
  - [`include/api/Nn.h`](../../include/api/Nn.h) 仍占用公共计算接口命名，但当前 `emit_c/npu_demo/kernel` expectation 已明显转向 kernel dialect helper 口径。
  - [`include/api/Dma.h`](../../include/api/Dma.h) 与 [`include/api/Memory.h`](../../include/api/Memory.h) 需要和 expectation 中的 `target-first / source-first / get_shape / get_stride / 成员式 view` 对齐。
- 当前实现入口：
  - [`include/npu_demo`](../../include/npu_demo) 现有 `Core / Memory / Dma / Nn / Arch / npu_demo.h`，但 helper 形态、模板顺序、参数顺序、查询口径仍不稳定。
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 对 `npu_demo` 的支持范围明显小于 expectation，并且仍存在旧 helper 文本、旧参数顺序和 target 特判。
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 仍强依赖 `body + wrapper` 双函数 module，和当前大量 `emit_c` expectation 的单函数模块不兼容。
- 当前测试与验收资产：
  - [`expectation/dsl/emit_c/npu_demo`](../../expectation/dsl/emit_c/npu_demo) 已形成 `dma / kernel / symbol` 三个 family 的合同文本。
  - [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 已锁定 npu_demo 双函数主骨架。
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 已开始表达“真编译 + 真执行”合同。
- 当前缺口或失败点：
  - 公开 API、expectation、include/npu_demo、emit_c/gen_kernel 四层口径仍未统一。
  - 旧 helper 名、旧参数顺序和旧 target 特判仍残留在 expectation 之外的黑盒路径。
  - `include/api/Nn` 与实际 kernel dialect emit 目标之间存在名称和职责冲突。
  - `view` 的公开口径已在 expectation 中收口为 `source.view<T>(...)`，但 spec/include/api/emit_c 还未统一。
  - 旧公开名残留消费者尚未全部收口，当前至少包含：
    - [`test/pass/test_dma_memory_hierarchy.py`](../../test/pass/test_dma_memory_hierarchy.py)：当前直接构造并锁 `kernel.add`，本计划归类为“改写到新公共合同”；不保留旧公开成功口径。
    - [`test/pass/test_lowering_kernel_split.py`](../../test/pass/test_lowering_kernel_split.py)：当前仍生成 `kernel.add` 单函数 IR，本计划归类为“改写到新公共合同”；不保留旧公开成功口径。
    - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)：当前含 `kernel.add`、旧 `NnAddOp` 成功链路与旧 helper 文本，本计划归类为“主体改写到新公共合同，仅保留显式标注的缺口暴露用例”。
    - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)：当前仍有围绕旧公开名的清理断言与历史成功路径口径，本计划归类为“主体改写到新公共合同，仅保留显式标注的缺口暴露用例”。
    - 若执行阶段再检出其他直接依赖旧 `kernel.add/sub/...`、`kernel.cast`、`kernel.softmax` 或旧 `Nn` 公共 API 的消费者，统一按本分类规则收口，不得遗漏在链路之外。

## 方案比较与选型

- 不采用方案：继续让 `include/npu_demo` 直接定义公开 helper，然后由 `emit_c/gen_kernel` 按 target 自由发射。
- 不采用原因：这会继续保留“公开 API 在 include/npu_demo，expectation 在 emit_c，gen_kernel 再自己特判”的三轨口径，后续无法稳定删除旧接口。
- 不采用方案：保留 `include/api/Nn.h`，同时新增 `Kernel.h`，让两套公共计算接口并存。
- 不采用原因：这会让 `kernel dialect emit` 的公开目标长期维护双轨命名，review 无法判断到底哪套才是合同真源。
- 采用方案：`spec/include/api` 先定义唯一公开接口；`include/api` 对齐之；`include/npu_demo` 仅承接 target 运行时与实现；`emit_c/gen_kernel` 只消费公开接口。
- 最小公开接口：
  - `Core`：`Status`、`StatusCode`、`Vector`
  - `Memory`：`Memory<Space, T>`、`rank()`、`get_shape(axis)`、`get_stride(axis)`、`view<T>(...)`、`reshape(...)`
  - `Dma`：`alloc / copy / broadcast / transpose / fill / free / load / store / cast / slice / deslice`
  - `Arch`：`launch`、`KernelContext`、`barrier`、`get_dynamic_memory`
  - `Kernel`：本轮 `emit_c/npu_demo/kernel` 中已经进入合同真源的全部 helper

## 公开 API 设计

### Core / Memory / Dma

- 公开入口：
  - `Status`
  - `StatusCode`
  - `Vector`
  - `Memory<Space, T>`
  - `slice(target, source, offset, size, stride)`
  - `deslice(target, source, offset, size, stride)`
- 参数顺序：
  - `view`：成员式 `source.view<T>(offset, size, stride)`；当前 emit_c expectation 文本验收允许发射为 `source.view(offset, size, stride)` 的成员式调用形态
  - `reshape`：成员式 `source.reshape(shape)`，本轮不扩展模板参数
  - `slice/deslice/load/store/copy/broadcast/transpose/cast`：`target/dst-first`
- 参数类型：
  - `Memory` 统一为 `Memory<Space, T>`
  - `offset / size / stride / shape / perm` 使用 `Vector` 或稳定的 initializer-list 口径，由 `spec/include/api` 写死
- 返回值：
  - `view<T>` / `reshape(...)` 返回 `Memory<Space, T>` 或当前 expectation 对应结果 memory
  - 其余 `Dma` helper 返回 `Status`

```cpp
Memory<GM, float> tile = source.view<float>({offset}, {size}, {stride});
Status st = slice(dst, source, {offset}, {size}, {stride});
Status st2 = deslice(dst, source, {offset}, {size}, {stride});
```

### Arch

- 公开入口：
  - `launch<block, thread, subthread>(callee, args...)`
  - `BarrierVisibility`
  - `BarrierScope`
  - `KernelContext::thread_id()`
  - `KernelContext::thread_num()`
  - `KernelContext::barrier(visibility, scope)`
  - `KernelContext::get_dynamic_memory<Space, T>()`
- 参数顺序：
  - `launch<block, thread, subthread>(callee, args...)`
  - `barrier(visibility, scope)`
- 返回值：
  - `launch(...) -> Status`
  - `thread_id/thread_num -> S_INT`
  - `get_dynamic_memory<Space, T>() -> Memory<Space, T>`

```cpp
Status status = launch<1, 4, 1>(kernel_body, lhs, rhs, out);
ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
auto tsm = ctx.get_dynamic_memory<TSM, float>();
```

### Kernel

- 公开入口：
  - 删除 [`include/api/Nn.h`](../../include/api/Nn.h)
  - 新增 [`include/api/Kernel.h`](../../include/api/Kernel.h)
  - 本轮仅保留 `emit_c/npu_demo/kernel` 真源中已进入合同的 helper：
    - `add`
    - `sub`
    - `mul`
    - `truediv`
    - `eq`
    - `ne`
    - `lt`
    - `le`
    - `gt`
    - `ge`
    - `exp`
    - `select`
    - `reduce_sum`
    - `reduce_min`
    - `matmul`
    - `img2col1d`
    - `img2col2d`
- 参数顺序：
  - 一律 `out-first`
- 模板顺序：
  - 优先 `space`
  - 再 `type`
  - 多输入时按 operand 顺序排列
- 返回值：
  - 统一 `Status`

```cpp
npu_demo::add<Space, InType, OutType>(out, lhs, rhs);
npu_demo::select<Space, InType, OutType>(out, cond, lhs, rhs);
npu_demo::matmul<LhsSpace, RhsSpace, OutSpace, LhsType, RhsType, OutType>(out, lhs, rhs);
```

### npu_demo 私有层

- [`include/npu_demo`](../../include/npu_demo) 只承接：
  - launch 运行时
  - barrier 运行时
  - dynamic memory runtime
  - target 特性
  - `include/api` 声明的具体实现
- `emit_c/gen_kernel` 不得再绕过 `include/api` 自己发明新的公开 helper。

## 完成态定义

- `spec/include/api` 中公开接口只保留本轮 `emit_c` 真源覆盖到的集合；超出范围的公开旧接口已删除或降为私有层。
- [`include/api/Nn.h`](../../include/api/Nn.h) 与对应 spec 已删除；`Kernel` 成为 kernel dialect emit 的唯一公共 API 承载层。
- `Memory` 查询与视图接口收口为：
  - `rank()`
  - `get_shape(axis)`
  - `get_stride(axis)`
  - `source.view<T>(...)`
  - `source.reshape(...)`
- `slice/deslice`、`load/store/copy/broadcast/transpose/cast` 等 helper 的参数顺序与 expectation 完全一致，不再存在旧顺序兼容。
- [`expectation/dsl/emit_c/npu_demo`](../../expectation/dsl/emit_c/npu_demo) 中纳入真源范围的 case 全部通过。
- [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 与 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 都按黑盒合同通过。
- `emit_c.py` 与 `gen_kernel.py` 不再保留公开行为上的旧 target 特判与旧 helper 别名。

## 验收设计

- 合同真源顺序：`expectation > spec > test 文字说明 > 当前实现`
- 第一层验收：公开 API
  - `pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_arch.py`
  - `pytest -q test/include/api/test_kernel.py`（由执行者在 `S6` 补齐）
- 第二层验收：npu_demo helper / runtime
  - `pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py`
- 第三层验收：emit_c expectation
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.dsl.emit_c.npu_demo.dma`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.dsl.emit_c.npu_demo.symbol`
- 第四层验收：gen_kernel 黑盒合同
  - `script/run-npu-demo-s11-add-barrier-expectation.sh`（在对应 task-site 执行）
  - `pytest -q test/dsl/test_gen_kernel.py`
- 第五层验收：execute_engine 真链路
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/execute_engine/npu_demo/matmul.py`
- 第六层验收：全量代码生成回归
  - `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`

## 阶段拆分

### S1：冻结 Core / Memory / Dma 公共接口

#### 阶段目标

- 冻结 `Core / Memory / Dma` 的唯一公开接口、参数顺序与删除边界。

#### 目标 spec / API

- [`spec/include/api/Core.md`](../../spec/include/api/Core.md)
- [`spec/include/api/Memory.md`](../../spec/include/api/Memory.md)
- [`spec/include/api/Dma.md`](../../spec/include/api/Dma.md)
- `公开 API：Status / StatusCode / Vector / Memory<Space, T> / view<T> / reshape / slice / deslice / Dma helper`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/dsl/emit_c/npu_demo/`（本阶段不改 expectation 文本）
- `合同真源：expectation/dsl/emit_c/npu_demo/dma/*.py、expectation/dsl/emit_c/npu_demo/symbol/get_dim.py、expectation/dsl/emit_c/npu_demo/symbol/get_stride.py`

#### 预期示例代码

```cpp
Memory<GM, float> tile = source.view<float>({offset}, {size}, {stride});
Status st = slice(dst, source, {offset}, {size}, {stride});
Status st2 = deslice(dst, source, {offset}, {size}, {stride});
```

#### 预期输出

```text
spec/include/api/Core|Memory|Dma 已明确:
- Status / StatusCode / Vector
- Memory<Space, T>
- get_shape(axis) / get_stride(axis)
- source.view<T>(...)
- slice/deslice target-first
```

#### 目标验收资产

- `spec/include/api/Core.md`
- `spec/include/api/Memory.md`
- `spec/include/api/Dma.md`

#### 验收必过项目

- `rg -n "view<|get_shape\\(|get_stride\\(|slice\\(target, source|deslice\\(target, source" spec/include/api/Core.md spec/include/api/Memory.md spec/include/api/Dma.md`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：冻结 Core / Memory / Dma 公共接口与删除边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s1-core-memory-dma-spec.md`

### S2：冻结 Arch 公共接口

#### 阶段目标

- 冻结 `launch / KernelContext / barrier / get_dynamic_memory` 的唯一公开接口和职责分层。

#### 目标 spec / API

- [`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)
- `公开 API：launch / BarrierVisibility / BarrierScope / KernelContext`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/dsl/gen_kernel/npu_demo_add_barrier`
- `合同真源：expectation/dsl/gen_kernel/npu_demo_add_barrier、expectation/dsl/emit_c/npu_demo/symbol/for_loop.py`

#### 预期示例代码

```cpp
Status st = launch<1, 4, 1>(kernel_body, lhs, rhs, out);
ctx.thread_id();
ctx.thread_num();
ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
auto tsm = ctx.get_dynamic_memory<TSM, float>();
```

#### 预期输出

```text
spec/include/api/Arch.md 已明确:
- include/api 只定义接口与最小语义
- include/npu_demo 承接 runtime 行为
```

#### 目标验收资产

- `spec/include/api/Arch.md`

#### 验收必过项目

- `rg -n "launch<|KernelContext::thread_id|KernelContext::thread_num|KernelContext::barrier|get_dynamic_memory<" spec/include/api/Arch.md`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：冻结 Arch 公共接口与 include/api vs include/npu_demo 分层`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s2-arch-spec.md`

### S3：删除 Nn 公共层并建立 Kernel 公共接口

#### 阶段目标

- 删除 `include/api/Nn.h` 和对应 spec，建立 `Kernel` 作为 kernel dialect emit 的唯一公共 API 承载层。

#### 目标 spec / API

- 删除 [`spec/include/api/Nn.md`](../../spec/include/api/Nn.md)
- 删除 [`include/api/Nn.h`](../../include/api/Nn.h)
- 新增 [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md)
- 新增 [`include/api/Kernel.h`](../../include/api/Kernel.h)

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/dsl/emit_c/npu_demo/kernel/*.py`
- `合同真源：expectation/dsl/emit_c/npu_demo/kernel/*.py`

#### 预期示例代码

```cpp
npu_demo::add<Space, InType, OutType>(out, lhs, rhs);
npu_demo::select<Space, InType, OutType>(out, cond, lhs, rhs);
npu_demo::matmul<LhsSpace, RhsSpace, OutSpace, LhsType, RhsType, OutType>(out, lhs, rhs);
```

#### 预期输出

```text
include/api/Nn.h 已删除
include/api/Kernel.h 已成为 kernel dialect emit 的唯一公共承载层
```

#### 目标验收资产

- `spec/include/api/Kernel.md`
- `expectation/dsl/emit_c/npu_demo/kernel/*.py`

#### 验收必过项目

- `rg -n "include/api/Nn.h|spec/include/api/Nn.md" ARCHITECTURE/plan spec include/api`
- `rg -n "Kernel.h|Kernel.md" spec/include/api include/api`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：删除 Nn 公共层并建立 Kernel 公共接口`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s3-kernel-spec.md`

### S4：对齐 include/api 的 Core / Memory / Dma 头文件

#### 阶段目标

- 让 `include/api/Core.h`、`Memory.h`、`Dma.h` 和 `S1` spec 以及 expectation 完全对齐。

#### 目标 spec / API

- [`include/api/Core.h`](../../include/api/Core.h)
- [`include/api/Memory.h`](../../include/api/Memory.h)
- [`include/api/Dma.h`](../../include/api/Dma.h)

#### 禁止修改面 / 合同真源

- `禁止修改面：include/npu_demo`
- `合同真源：spec/include/api/Core.md、spec/include/api/Memory.md、spec/include/api/Dma.md`

#### 预期示例代码

```cpp
Memory<GM, float> tile = source.view<float>({offset}, {size}, {stride});
long long n = source.get_shape(0);
long long s = source.get_stride(0);
Status st = slice(dst, source, {offset}, {size}, {stride});
```

#### 预期输出

```text
include/api/Core|Memory|Dma 与 spec 一致，且旧公共接口已从头文件删掉
```

#### 目标验收资产

- [`test/include/api/test_core.py`](../../test/include/api/test_core.py)
- [`test/include/api/test_memory.py`](../../test/include/api/test_memory.py)
- [`test/include/api/test_dma.py`](../../test/include/api/test_dma.py)

#### 验收必过项目

- `pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：对齐 include/api 的 Core / Memory / Dma，并删除旧公共入口`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s4-core-memory-dma-build.md`

### S5：对齐 include/api 的 Arch 头文件

#### 阶段目标

- 让 `include/api/Arch.h` 和 `S2` spec 对齐，只保留公开接口，不混入 npu_demo runtime 细节。

#### 目标 spec / API

- [`include/api/Arch.h`](../../include/api/Arch.h)

#### 禁止修改面 / 合同真源

- `禁止修改面：include/npu_demo/Arch.h`
- `合同真源：spec/include/api/Arch.md`

#### 预期示例代码

```cpp
Status st = launch<1, 4, 1>(kernel_body, lhs, rhs, out);
ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
```

#### 预期输出

```text
include/api/Arch.h 只保留接口名、参数面和最小语义
```

#### 目标验收资产

- [`test/include/api/test_arch.py`](../../test/include/api/test_arch.py)

#### 验收必过项目

- `pytest -q test/include/api/test_arch.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：对齐 include/api/Arch.h 与公开分层`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s5-arch-build.md`

### S6：建立 include/api/Kernel.h 并清空 Nn 公共层

#### 阶段目标

- 把 kernel dialect emit 的公共 helper 从 `Nn` 迁到 `Kernel`，并建立最小测试入口。

#### 目标 spec / API

- [`include/api/Kernel.h`](../../include/api/Kernel.h)
- `test/include/api/test_kernel.py`（由执行者补齐）

#### 禁止修改面 / 合同真源

- `禁止修改面：include/npu_demo/Kernel.h`
- `合同真源：spec/include/api/Kernel.md、expectation/dsl/emit_c/npu_demo/kernel/*.py`

#### 预期示例代码

```cpp
Status st = npu_demo::exp<Space, InType, OutType>(out, input);
Status st2 = npu_demo::reduce_sum<Space, InType, OutType>(out, input, axis);
```

#### 预期输出

```text
Kernel 公共 API 已建立，Nn 公共层不再承担 kernel dialect emit helper
```

#### 目标验收资产

- `test/include/api/test_kernel.py`（新增）
- `expectation/dsl/emit_c/npu_demo/kernel/*.py`

#### 验收必过项目

- `pytest -q test/include/api/test_kernel.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：建立 include/api/Kernel.h 并删除 Nn 公共层`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s6-kernel-build.md`

### S7：复核 Core / Memory / Dma 公共接口

#### 阶段目标

- 复核 `S4` 结果，确保接口删减、参数顺序和 expectation 口径一致。

#### 目标 spec / API

- `公开 API：Core / Memory / Dma`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation`
- `合同真源：spec/include/api/Core.md、spec/include/api/Memory.md、spec/include/api/Dma.md`

#### 预期示例代码

```cpp
slice(dst, source, {offset}, {size}, {stride});
deslice(dst, source, {offset}, {size}, {stride});
```

#### 预期输出

```text
旧公共接口已删，target-first/source-first 口径一致
```

#### 目标验收资产

- `pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py`

#### 验收必过项目

- `pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核 Core / Memory / Dma 公开接口与删旧边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s7-core-memory-dma-review.md`

### S8：复核 Arch 公共接口

#### 阶段目标

- 复核 `S5`，确保 `include/api` 与 `include/npu_demo` 职责没有交叉。

#### 目标 spec / API

- `公开 API：launch / KernelContext / barrier / get_dynamic_memory`

#### 禁止修改面 / 合同真源

- `禁止修改面：include/npu_demo`
- `合同真源：spec/include/api/Arch.md`

#### 预期输出

```text
include/api 不再承接 runtime 行为
```

#### 目标验收资产

- `pytest -q test/include/api/test_arch.py`

#### 验收必过项目

- `pytest -q test/include/api/test_arch.py`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核 Arch 分层和运行时接口边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s8-arch-review.md`

### S9：复核 Kernel 公共接口

#### 阶段目标

- 复核 `Kernel.h` 已成为唯一公共层，`Nn` 公共层已删，且 expectation 口径一致。

#### 目标 spec / API

- `公开 API：Kernel helper`

#### 禁止修改面 / 合同真源

- `禁止修改面：include/npu_demo`
- `合同真源：spec/include/api/Kernel.md、expectation/dsl/emit_c/npu_demo/kernel/*.py`

#### 预期输出

```text
公共计算 helper 只保留 Kernel 层
```

#### 目标验收资产

- `pytest -q test/include/api/test_kernel.py`

#### 验收必过项目

- `pytest -q test/include/api/test_kernel.py`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核 Kernel 公共接口与 Nn 删除边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s9-kernel-review.md`

### S10：收口 npu_demo Dma 实现与 emit_c DMA

#### 阶段目标

- 让 `include/npu_demo/Dma.h` 与 `emit_c/npu_demo/dma` 逐条对齐。

#### 目标 spec / API

- [`include/npu_demo/Dma.h`](../../include/npu_demo/Dma.h)
- `公开 API：Dma helper 已在 include/api 定义，本阶段只实现/发射`

#### 禁止修改面 / 合同真源

- `禁止修改面：spec/include/api/Dma.md`
- `合同真源：expectation/dsl/emit_c/npu_demo/dma/*.py`
- `执行澄清：S10 的实现收口以实际只读 expectation 正文为准；当前 emit_c 黑盒文本冻结的是成员式 source.view(...) 调用，以及 target-first 的 slice/deslice helper + brace-list offset/size/stride 参数形态，不允许为迁就旧 helper 文本回退实现。`

#### 预期示例代码

```cpp
Status st = slice(dst, source, {offset}, {size}, {stride});
Status st2 = deslice(dst, source, {offset}, {size}, {stride});
Memory<GM, float> tile = source.view({offset}, {size}, {stride});
```

#### 预期输出

```text
emit_c 与 include/npu_demo/Dma.h 不再出现旧 helper 顺序、旧别名或旧 target 特判
```

#### 目标验收资产

- [`expectation/dsl/emit_c/npu_demo/dma`](../../expectation/dsl/emit_c/npu_demo/dma)
- [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)
- [`test/include/api/test_dma.py`](../../test/include/api/test_dma.py)

#### 验收必过项目

- `cd /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s10-dma-emitc-build && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s10-dma-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.dma`
- `pytest -q test/include/npu_demo/test_kernel_context.py -k "slice or deslice or fill or load or store"`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 include/npu_demo/Dma.h 与 emit_c DMA 合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s10-dma-emitc-build.md`

### S11：收口 npu_demo Arch 实现与 gen_kernel add_barrier 骨架

#### 阶段目标

- 让 `include/npu_demo/Arch.h`、`gen_kernel.py` 与 `npu_demo_add_barrier` 黑盒合同对齐。

#### 目标 spec / API

- [`include/npu_demo/Arch.h`](../../include/npu_demo/Arch.h)
- [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)

#### 禁止修改面 / 合同真源

- `禁止修改面：spec/include/api/Arch.md`
- `合同真源：expectation/dsl/gen_kernel/npu_demo_add_barrier`

#### 预期输出

```text
body + wrapper / launch<1,4,1> / ctx.thread_id / ctx.thread_num / ctx.barrier / get_dynamic_memory 全部与黑盒 expectation 一致
```

#### 目标验收资产

- [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier)
- `script/run-npu-demo-s11-add-barrier-expectation.sh`
- [`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)

#### 验收必过项目

- `script/run-npu-demo-s11-add-barrier-expectation.sh`（在对应 task-site 执行）
- `pytest -q test/include/npu_demo/test_runtime_launch.py test/dsl/test_gen_kernel.py -k "npu_demo_add_barrier or launch_wrapper"`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 include/npu_demo/Arch.h 与 gen_kernel add_barrier 骨架`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s11-arch-gen-kernel-build.md`

### S12：收口 npu_demo Kernel 实现与 emit_c Kernel

#### 阶段目标

- 让 `include/npu_demo/Kernel.h` 与 `emit_c/npu_demo/kernel` 合同对齐。

#### 目标 spec / API

- [`include/npu_demo/Kernel.h`](../../include/npu_demo/Kernel.h)
- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)

#### 禁止修改面 / 合同真源

- `禁止修改面：spec/include/api/Kernel.md`
- `合同真源：expectation/dsl/emit_c/npu_demo/kernel/*.py`

#### 预期示例代码

```cpp
npu_demo::add<Space, InType, OutType>(out, lhs, rhs);
npu_demo::reduce_sum<Space, InType, OutType>(out, input, axis);
npu_demo::matmul<LhsSpace, RhsSpace, OutSpace, LhsType, RhsType, OutType>(out, lhs, rhs);
```

#### 预期输出

```text
kernel emit 不再通过 Nn 公共层；全部通过 Kernel 公共层发射
```

#### 目标验收资产

- [`expectation/dsl/emit_c/npu_demo/kernel`](../../expectation/dsl/emit_c/npu_demo/kernel)
- [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel`
- `上述 npu_demo kernel expectation 命令需在当前 task worktree /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build 下执行；当前现场无 expectation/ 目录时，只通过 PYTHONPATH 追加主仓 expectation 资产。`
- `pytest -q test/dsl/test_emit_c.py -k "npu_demo and kernel"`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 include/npu_demo/Kernel.h 与 emit_c Kernel 合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s12-kernel-emitc-build.md`

### S13：收口 emit_c Symbol 扩展

#### 阶段目标

- 让 `symbol.const/cast/to_float/get_dim/get_stride/for` 的 `emit_c/npu_demo` 文本行为稳定下来。

#### 目标 spec / API

- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- `公开 API：无新增 include/api；本阶段只收 emitter 文本合同`

#### 禁止修改面 / 合同真源

- `禁止修改面：include/api`
- `合同真源：expectation/dsl/emit_c/npu_demo/symbol/*.py`

#### 预期输出

```text
S_INT / bool / get_shape(axis) / get_stride(axis) / for (...) 骨架与 expectation 一致
```

#### 目标验收资产

- [`expectation/dsl/emit_c/npu_demo/symbol`](../../expectation/dsl/emit_c/npu_demo/symbol)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.symbol`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 emit_c Symbol 文本合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s13-symbol-emitc-build.md`

### S14：复核 DMA + Symbol emit 合同

#### 阶段目标

- 复核 `S10` 与 `S13`，重点核查 `target-first`、`symbol` 展开、旧 helper 别名残留和稳定变量名。

#### 目标 spec / API

- `公开 API：Dma / Symbol emit 文本合同`

#### 禁止修改面 / 合同真源

- `禁止修改面：spec/include/api/Dma.md、spec/include/api/Memory.md`
- `合同真源：expectation/dsl/emit_c/npu_demo/dma/*.py、expectation/dsl/emit_c/npu_demo/symbol/*.py`

#### 目标验收资产

- `expectation/dsl/emit_c/npu_demo/dma`
- `expectation/dsl/emit_c/npu_demo/symbol`
- `test/include/npu_demo/test_kernel_context.py`

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.dsl.emit_c.npu_demo.dma`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.dsl.emit_c.npu_demo.symbol`
- `上述 DMA/Symbol expectation 命令需在当前 task worktree 下执行；若现场无 expectation/ 目录，只通过 PYTHONPATH 追加主仓 expectation 资产。`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核 DMA / Symbol emit 文本合同、旧顺序与旧别名残留`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s14-dma-symbol-review.md`

### S15：复核 Arch / Kernel codegen 黑盒合同

#### 阶段目标

- 复核 `S11` 与 `S12`，重点核查 `body + wrapper`、`launch`、`barrier`、dynamic memory、`deslice(target, source, ...)`、`Kernel.h` 公共 helper、模板顺序与 `out-first`。

#### 目标验收资产

- `expectation/dsl/gen_kernel/npu_demo_add_barrier`
- `script/run-npu-demo-s11-add-barrier-expectation.sh`
- `expectation/dsl/emit_c/npu_demo/kernel`
- `test/include/npu_demo/test_runtime_launch.py`
- `test/include/api/test_kernel.py`
- `test/dsl/test_emit_c.py`
- `test/dsl/test_gen_kernel.py`

#### 验收必过项目

- `script/run-npu-demo-s11-add-barrier-expectation.sh`（在对应 task-site 执行）
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel`
- `pytest -q test/dsl/test_gen_kernel.py -k "npu_demo"`
- `pytest -q test/dsl/test_emit_c.py -k "kernel and npu_demo"`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核 Arch / Kernel codegen 黑盒合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s15-arch-kernel-review.md`

### S16：收口 execute_engine npu_demo matmul 真链路

#### 阶段目标

- 让 `execute_engine/npu_demo/matmul.py` 成为最终真合同：前端空间不退化、lower 到 `kernel.matmul`、真编译、真执行。
- 本阶段必须等待 `S14` 与 `S15` 通过，确保 execute_engine 依赖的 DMA、Symbol、Arch、Kernel codegen 链都已过 review。

#### 目标 spec / API

- [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)
- `公开 API：无新增 include/api；本阶段只收 execute 真链路`

#### 禁止修改面 / 合同真源

- `禁止修改面：spec/include/api`
- `合同真源：expectation/execute_engine/npu_demo/matmul.py`

#### 目标验收资产

- [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 execute_engine npu_demo matmul 真编译真执行链`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s16-execute-engine-build.md`

### S17：复核 execute_engine 真链路

#### 阶段目标

- 复核 `S16`，重点核查不回退、不 dry-run、不降级到 CPU。

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核 execute_engine npu_demo matmul 真链路`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s17-execute-engine-review.md`

### S18：清理旧接口、旧 target 特判与全量回归

#### 阶段目标

- 清理公开行为层面的旧接口、旧 helper 别名、旧 target 特判，并完成全量回归。
- 本阶段必须显式处理旧公开名残留消费者，并分类为“删除 / 改写 / 保留为缺口暴露”。

#### 目标 spec / API

- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
- `公开 API：只消费 include/api 的统一接口`

#### 禁止修改面 / 合同真源

- `禁止修改面：已通过 review 的 expectation 文本`
- `合同真源：expectation/dsl/emit_c/npu_demo、expectation/dsl/gen_kernel/npu_demo_add_barrier、expectation/execute_engine/npu_demo/matmul.py`

#### 预期输出

```text
emit_c / gen_kernel 不再保留公开行为上的旧 target 特判
旧公共接口和旧 helper 别名已从实现和黑盒路径清理
旧公开名残留消费者已按分类处理完毕
```

#### 目标验收资产

- `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`
- `pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_arch.py test/include/api/test_kernel.py`
- `pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo`

#### 旧公开名残留消费者分类

- `改写到新公共合同`：
  - [`test/pass/test_dma_memory_hierarchy.py`](../../test/pass/test_dma_memory_hierarchy.py)
  - [`test/pass/test_lowering_kernel_split.py`](../../test/pass/test_lowering_kernel_split.py)
- `主体改写到新公共合同，仅保留显式缺口暴露用例`：
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- `若执行阶段发现其他直接依赖旧 kernel.add/sub/...、kernel.cast、kernel.softmax 或旧 Nn API 的消费者`：
  - 统一并入本阶段分类处理
  - 不得在任务外静默遗留

#### 验收必过项目

- `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo`

#### 任务新建建议

- `任务类型：build`
- `任务目标：清理旧公共接口、旧 helper 别名、旧 target 特判并完成全量回归`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s18-cleanup-build.md`

### S19：最终复核与归档口径收口

#### 阶段目标

- 复核全链路结果，明确“必须直接通过”的 expectation 与“允许作为缺口暴露”的资产清单，并形成归档口径。

#### 目标验收资产

- `S18` 的全部回归资产

#### 验收必过项目

- `S18` 全部命令通过
- `缺口清单` 与 `必过清单` 已写入记录

#### 任务新建建议

- `任务类型：review`
- `任务目标：最终复核全链路通过情况、缺口清单与归档口径`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-emitc-api-s19-final-review.md`

## 复核结论（2026-04-20 06:35:07 +0800）

- 复核人：`守护最好的爱莉希雅`
- 复核结论：`不通过`
- 验证基线：
  - 当前主线分支：`main`
  - 当前主线 `HEAD`：`19ac0a05af8313a7ca476d4f77e24bbc76444208`
  - 本轮按计划书顶层完成态与验收设计，在最新主线现场直接复跑。
- 本轮复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_arch.py test/include/api/test_kernel.py test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py` -> `34 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma` -> `exit 1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.symbol` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. bash script/run-npu-demo-s11-add-barrier-expectation.sh` -> `exit 2`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/execute_engine/npu_demo/matmul.py` -> `exit 1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/script/test_run_emitc_npu_demo_expectation.py` -> `89 passed`
- 最小阻断项：
  - [`expectation/dsl/emit_c/npu_demo/dma/slice.py`](../../expectation/dsl/emit_c/npu_demo/dma/slice.py) 的 rank3 两条 expectation 仍未通过；当前 `python3 -m expectation.dsl.emit_c.npu_demo.dma` 卡在：
    - `CASE-dma-slice-symbol-body-rank3`
    - `CASE-dma-slice-symbol-args-rank3`
  - [`script/run-npu-demo-s11-add-barrier-expectation.sh`](../../script/run-npu-demo-s11-add-barrier-expectation.sh) 仍在尝试执行旧路径 `/home/lfr/expectation/dsl/gen_kernel/npu_demo_add_barrier`，未收口到当前仓库路径。
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 在当前主线现场仍直接依赖 `torch`，复跑时报 `RuntimeError: expectation/execute_engine/npu_demo/matmul.py requires torch`，导致计划书正文点名的 execute_engine 真链路验收无法通过。
- 必要摘要：
  - 当前主线下 `include/api` 子集测试、`emit_c npu_demo kernel`、`emit_c npu_demo symbol`、以及 `test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/script/test_run_emitc_npu_demo_expectation.py` 都已通过。
  - 归档前置条件仍被 `dma slice` expectation、`S11 add-barrier` 脚本旧路径，以及 `execute_engine matmul` 的环境依赖三项阻断，当前不能给出“通过”结论。

## 复核结论（2026-04-20 06:49:58 +0800）

- 复核人：`大闸蟹`
- 复核结论：`不通过`
- 验证基线：
  - 最新主线提交：`origin/main@b826419c5a4a7ab6c91bab56a6bf416c400bacdb`
  - 当前主仓执行目录存在未提交本地改动且本地 `main` 落后 `origin/main`；为避免脏现场污染，本轮实际复验使用同级干净只读 `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp`
- 实际复跑结果：
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_arch.py test/include/api/test_kernel.py test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py` -> `34 passed`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo` -> `exit 1`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp:/home/lfr/kernelcode_generate bash script/run-npu-demo-s11-add-barrier-expectation.sh` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp && python3 -m pytest -q test/script/test_run_npu_demo_s11_add_barrier_expectation.py` -> `3 passed`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp && pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py` -> `87 passed`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-archive-check-temp:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/matmul.py` -> `exit 1`
- 最小阻断项：
  - [`expectation/dsl/emit_c/npu_demo/dma/slice.py`](../../expectation/dsl/emit_c/npu_demo/dma/slice.py) 的 rank3 两条 expectation 在最新主线干净现场仍未通过：
    - `CASE-dma-slice-symbol-body-rank3`
    - `CASE-dma-slice-symbol-args-rank3`
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 在最新主线干净现场仍直接依赖 `torch`；当前机器缺少该依赖，入口处抛出 `RuntimeError: expectation/execute_engine/npu_demo/matmul.py requires torch`，导致计划书正文点名的 execute_engine 真链路验收无法通过。
- 必要摘要：
  - `include/api + include/npu_demo` pytest、`S11 add_barrier` 脚本与脚本测试、以及 `test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py` 在最新主线干净现场都已通过，`S11` 旧路径问题已不再构成阻断。
  - 当前归档前置条件只剩 `dma slice` rank3 expectation 与 `execute_engine matmul` 环境依赖两项阻断，仍不能给出“通过”结论。

## 当前唯一修复任务（2026-04-20 06:37:34 +0800）

- 任务号：`T-20260420-52693f49`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-emitc-api-s20-repair`
- 记录文件：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/16/20260420-emitc-api-s20-repair.md`
- 最小修复目标：
  - 收口 [`expectation/dsl/emit_c/npu_demo/dma/slice.py`](../../expectation/dsl/emit_c/npu_demo/dma/slice.py) 的 rank3 两条 expectation，使 `python3 -m expectation.dsl.emit_c.npu_demo.dma` 恢复通过。
  - 修正 [`script/run-npu-demo-s11-add-barrier-expectation.sh`](../../script/run-npu-demo-s11-add-barrier-expectation.sh) 仍调用旧路径 `/home/lfr/expectation/dsl/gen_kernel/npu_demo_add_barrier` 的问题，收口到当前仓库路径。
  - 去除 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 对 `torch` 的直接硬依赖，或同步补齐当前主线可执行的真链路回归口径。
- 保持已通过的 `include/api` 子集测试、`emit_c npu_demo kernel/symbol`，以及 `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/script/test_run_emitc_npu_demo_expectation.py` 不回退。

## 复核结论（2026-04-20 07:58:00 +0800）

- 复核人：`守护最好的爱莉希雅`
- 复核结论：`不通过`
- 验证基线：
  - 当前主线分支：`main`
  - 当前主线 `HEAD`：`b826419c5a4a7ab6c91bab56a6bf416c400bacdb`
  - 本轮直接在最新主线现场复跑，不再使用旧 `worktree` 现场代替结论。
- 本轮复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma` -> `exit 1`
  - `bash script/run-npu-demo-s11-add-barrier-expectation.sh` -> `exit 0`
  - `python3 script/run_execute_engine_npu_demo_matmul_expectation.py` -> `exit 0`
  - `pytest -q test/script/test_run_npu_demo_s11_add_barrier_expectation.py test/script/test_run_execute_engine_npu_demo_matmul_expectation.py` -> `5 passed`
  - `pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_arch.py test/include/api/test_kernel.py test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/script/test_run_emitc_npu_demo_expectation.py` -> `123 passed`
- 最小阻断项：
  - [`expectation/dsl/emit_c/npu_demo/dma/slice.py`](../../expectation/dsl/emit_c/npu_demo/dma/slice.py) 的 rank3 两条 expectation 在当前主线仍未通过：
    - `CASE-dma-slice-symbol-body-rank3`
    - `CASE-dma-slice-symbol-args-rank3`
- 必要摘要：
  - 先前阻断项中的 `S11 add-barrier` 旧路径问题和 `execute_engine matmul` 的 `torch` 直接依赖问题，在当前主线现场都已消除。
  - 当前归档前置条件只剩 `emit_c npu_demo dma slice` 的 rank3 两条 expectation；在这两条 case 收口前，仍不能给出“通过”结论。

## 复核补充说明（2026-04-20 08:00:20 +0800）

- 补充人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 与另一位架构师口径对齐后的最小阻断项：
  - [`expectation/dsl/emit_c/npu_demo/dma/slice.py`](../../expectation/dsl/emit_c/npu_demo/dma/slice.py) 的 rank3 两条 expectation 在最新主线干净现场仍未通过：
    - `CASE-dma-slice-symbol-body-rank3`
    - `CASE-dma-slice-symbol-args-rank3`
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 在最新主线干净现场直跑时仍直接依赖 `torch`。
- 任务口径：
  - 旧修复任务 `T-20260420-52693f49` 已完成，但当前主线现场仍残留 blocker。
  - 因此当前唯一修复任务已续建为 `T-20260420-65ae01d2`，继续收口上述 blocker，直到这两项都从最新主线现场消除。

## 当前唯一修复任务（2026-04-20 08:15:29 +0800）

- 任务号：`T-20260420-65ae01d2`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-emitc-api-s21-repair`
- 记录文件：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/16/20260420-emitc-api-s21-repair.md`
- 最小修复目标：
  - 优先收口 [`expectation/dsl/emit_c/npu_demo/dma/slice.py`](../../expectation/dsl/emit_c/npu_demo/dma/slice.py) 的 rank3 两条 expectation，使 `python3 -m expectation.dsl.emit_c.npu_demo.dma` 恢复通过。
  - 同步收口 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 在最新主线干净现场直跑时的 `torch` 依赖阻断。
  - 保持已通过的 `include/api` 子集测试、`emit_c npu_demo kernel/symbol`、`S11 add-barrier` 脚本与脚本测试，以及 `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/script/test_run_emitc_npu_demo_expectation.py` 不回退。

## 最终验收结论（2026-04-20 08:19:45 +0800）

- 验收人：`守护最好的爱莉希雅`
- 验收结论：`通过`
- 验证基线：
  - 最新主线提交：`main@4df73c2198d0d9af064cd75e869c3761a47ad8e4`
  - 当前主仓执行目录未同步到该提交；为避免未同步主仓影响结论，本轮最终验收使用干净只读 `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp`
  - `expectation` 资产仍以主仓只读目录为合同真源，执行时使用 `PYTHONPATH=<worktree>:<repo_root>` 组合最新主线实现与主仓验收资产
- 本轮复跑结果：
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.dma` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp:/home/lfr/kernelcode_generate bash script/run-npu-demo-s11-add-barrier-expectation.sh` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp:/home/lfr/kernelcode_generate python3 script/run_execute_engine_npu_demo_matmul_expectation.py` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp && pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_arch.py test/include/api/test_kernel.py test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/script/test_run_emitc_npu_demo_expectation.py` -> `123 passed`
- 必要摘要：
  - 最新主线 `main@4df73c2` 下，先前阻断的 `dma.slice` rank3 两条 expectation、`S11 add-barrier` 入口路径，以及 `execute_engine matmul` 的 `torch` 依赖问题均已消除。
  - 计划书正文点名的三条验证链路和聚合 pytest 已全部通过，当前已满足归档前置条件。

## 最终验收结论（2026-04-20 08:36:08 +0800）

- 验收人：`大闸蟹`
- 验收结论：`通过`
- 验证基线：
  - 最新主线提交：`main@4df73c2198d0d9af064cd75e869c3761a47ad8e4`
  - 当前主仓执行目录未同步到该提交；为避免未同步主仓影响结论，本轮最终验收使用干净只读 `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp`
  - `expectation` 资产仍以主仓只读目录为合同真源，执行时使用 `PYTHONPATH=<worktree>:<repo_root>` 组合最新主线实现与主仓验收资产
- 本轮复跑结果：
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.dma` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp:/home/lfr/kernelcode_generate bash script/run-npu-demo-s11-add-barrier-expectation.sh` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp:/home/lfr/kernelcode_generate python3 script/run_execute_engine_npu_demo_matmul_expectation.py` -> `exit 0`
  - `cd /home/lfr/kernelcode_generate/wt-20260420-emitc-api-final-check-temp && pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_arch.py test/include/api/test_kernel.py test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/script/test_run_emitc_npu_demo_expectation.py` -> `123 passed`
- 必要摘要：
  - 我在同一基线和同一只读 `worktree` 上复跑，结果与守护最好的爱莉希雅回写结论一致，没有发现回退。
  - `dma.slice` rank3 expectation、`S11 add-barrier` 入口路径，以及 `execute_engine matmul` 真链路都已在最新主线收口。
  - 当前已满足归档前置条件，可进入唯一归档任务链。

## 待确认项

- 当前无额外待确认项。

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：`
  - 不在此次 `emit_c` 中的公开接口删除掉。
  - `emit_c / gen_kernel` 只按照 `include/api` 的公开接口做；`npu_demo` 只定义非公开 API 与 target 特性。
  - `view` 固定为 `source.view<T>(...)`，当前 `T` 先与 `source` 元素类型保持一致；以后再扩展。
  - `reshape` 本轮不额外上模板扩展，只按当前 expectation 收口。
  - 删除 `include/api/Nn.h`，kernel dialect emit 的公共接口进入 `Kernel.h`，dma 同理进入 `Dma.h`。
- `未确认前处理要求：不得自行补假设`
- `若用户要求至少询问 3 人：已满足，且在推进前完成不少于 3 个对象的询问记录`
- `询问记录 1：提莫炖蘑菇 / agents/codex-multi-agents/log/talk.log / 提醒四层口径不同步是最大风险，要求按 include/api -> include/npu_demo -> emit_c -> gen_kernel -> execute_engine 的顺序逐层 gate，并明确必过 expectation 与缺口 expectation 分开管理`
- `询问记录 2：大闸蟹 / agents/codex-multi-agents/log/talk.log / 认可按 spec/include/api -> expectation -> include/npu_demo -> emit_c/gen_kernel 的方向，建议按 4 段拆并要求先拍板公开 helper、统一消费 include/api、合同真源目录`
- `询问记录 3：睡觉小分队 / agents/codex-multi-agents/log/talk.log / 建议先冻结 Core/Memory/Dma、Arch、Kernel 三组公开接口，再优先锁定 npu_demo_add_barrier、dma slice/deslice、execute_engine matmul 三条 expectation 真源`

## 参考资料

- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)
- [`ARCHITECTURE/plan/kernel_binary_elewise_only_green_plan.md`](./kernel_binary_elewise_only_green_plan.md)
- [`ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md`](./operation_mlir_gen_expectation_green_plan.md)
