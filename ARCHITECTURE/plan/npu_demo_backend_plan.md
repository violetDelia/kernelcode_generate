# npu_demo_backend_plan.md

## 进度
更新日期：2026-03-31
更新规则：每个任务块进入新子阶段后立即更新本段。

| 任务 | 依赖 | 记录文件 | worktree | 当前进度 |
| --- | --- | --- | --- | --- |
| A0 | 无 |  |  |  |
| A1 | A0 |  |  |  |
| O1 | A0 |  |  |  |
| D1 | A1、O1 |  |  |  |
| M1 | D1 |  |  |  |
| M2 | M1 |  |  |  |
| T1 | A0 |  |  |  |
| T2 | A0 |  |  |  |
| R1 | A0 |  |  |  |
| R2 | A0 |  |  |  |
| C1 | A0 |  |  |  |
| R3 | C1 |  |  |  |
| C2 | R3 |  |  |  |
| E0 | C2 |  |  |  |
| E1 | E0 |  |  |  |
| G1 | E1 |  |  |  |

## 功能说明

- 本计划基于当前仓库实现重新拟定，用来把 `npu_demo` 从“已有 include/spec 基线”推进到“能够生成 body-level kernel 源码”的最终目标。
- 下文只以当前实现为起点描述已具备能力、最终目标和剩余 gap；管理员后续分发应直接按本计划推进。
- 当前最关键的判断是：`npu_demo` 的 include 层和 `KernelContext` 已经存在并有测试，但 `emit_c/gen_kernel` 还没有接住 `npu_demo` 目标。

## 使用示例

- 管理员先确认 `KernelContext` 基线已经通过，再按“本轮收口顺序”推进。
- 若执行者回报以下命令通过，说明 `npu_demo` include 层不是当前阻塞：

```bash
PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py
```

- 若执行者在 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 与 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 中仍检不出 `npu_demo`、`KernelContext`、`get_dynamic_memory`、目标式 `slice(target, source, ...)` 相关生成逻辑，则当前阻塞仍在代码生成侧。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/npu_demo_backend_plan.md`](../../ARCHITECTURE/plan/npu_demo_backend_plan.md)
- `spec`：
  - [`spec/include/api/Core.md`](../../spec/include/api/Core.md)
  - [`spec/include/api/Dma.md`](../../spec/include/api/Dma.md)
  - [`spec/operation/dma.md`](../../spec/operation/dma.md)
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md)
  - [`spec/target/registry.md`](../../spec/target/registry.md)
- `功能实现`：
  - [`include/npu_demo/npu_demo.h`](../../include/npu_demo/npu_demo.h)
  - [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
- `test`：
  - [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)
  - [`test/target/test_target_registry.py`](../../test/target/test_target_registry.py)
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)

## 当前实现基线

### 已具备

- [`include/npu_demo/npu_demo.h`](../../include/npu_demo/npu_demo.h) 已经提供 `KernelContext`、`block/thread/subthread` accessor 与 `get_dynamic_memory<T>(MemorySpace::TSM/TLM)`。
- [`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md) 已经对应写入 include 合同。
- `slice` 的分层口径已经在现有规格中收敛为：
  - include/api：`slice(target, source, offset, size, stride)`
  - operation：`slice(source, offset, size, stride, space) -> Memory`
  - DSL lowering：`dma.alloc + dma.slice(target, source, ...)`

### 当前断点

1. [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 当前没有 `npu_demo` 目标专用文本生成逻辑，无法生成 `KernelContext`、`ctx.thread_id()`、`ctx.get_dynamic_memory<T>(...)`、目标式 `slice(target, source, ...)` 等代码片段。

2. [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 当前没有 `npu_demo` body-level kernel 骨架拼装逻辑，无法落出 `npu_demo::KernelContext& ctx` 签名和对应循环骨架。

3. [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py) 已支持通用硬件字段，但当前没有专门锁定 `npu_demo` 固定模板的测试入口；`pytest -q test/target/test_target_registry.py -k 'npu_demo or integer_literal or unsupported'` 当前没有命中 `npu_demo` 专项 case。

## 最终目标

- `gen_kernel(target="npu_demo")` 能生成 body-level kernel 源码。
- 生成源码必须显式包含：
  - `npu_demo::KernelContext& ctx`
  - `ctx.thread_id()`、`ctx.thread_num()`
  - `ctx.get_dynamic_memory<float>(MemorySpace::TSM/TLM)` 或等价元素类型
  - `Vector`
  - `view(`
  - `slice(target, source, offset, size, stride)`
  - `deslice(`
  - `add(`
- 生成源码不得回退到 `.view<T>()`、`load<...>`、`store<...>`、表达式式 `slice(source, ...)`、`launch(` 或 `barrier`。

## 本轮边界

- 不再回到 include/api 或 `KernelContext` 基础访问器层重复开任务。
- 不把 `npu_demo` 目标退回 `xpu_sim/cpu_xpu_sim` 风格旁路。
- 不在本轮扩展 host wrapper、runtime launch、`arch.launch_kernel` 或 `barrier`。

## 本轮收口顺序

1. 在 [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py) 与对应测试中补齐 `npu_demo` 固定硬件模板与能力矩阵入口，锁定 `6/8/1/0/0/24576/2048` 这组硬件值及不支持项。
2. 在 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 增加 `npu_demo` 目标文本映射，覆盖 `get_shape/get_stride`、`ctx.thread_id/thread_num`、`get_dynamic_memory`、`view/slice/deslice/add`。
3. 在 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 固定 `npu_demo` kernel body 骨架，让函数签名、局部 buffer、循环结构与目标式 `slice` 一次落地。
4. 在 `emit_c/gen_kernel` 收口后，再补源码级机械检查和最小 smoke 验证。

## 管理员执行口径

- 当前分发重点必须落在 `target registry + emit_c + gen_kernel`；不要再把资源投入到 `KernelContext` include 基础能力。
- `npu_demo` 代码生成必须沿当前 `slice` 分层口径推进；任何把 `slice(source, ...)` 重新写回生成源码的做法都不属于本计划范围。
- `emit_c` 与 `gen_kernel` 应连续推进；前者明确文本映射，后者完成函数级骨架，二者不可割裂。

## 本轮验收口径

- include 基线继续保持通过：

```bash
PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py
```

预期：退出码为 `0`。

- target registry 必须新增并通过 `npu_demo` 专项测试，至少锁定：
  - `block_num=6`
  - `thread_num=8`
  - `subthread_num=1`
  - `sm_memory_size=0`
  - `lm_memory_size=0`
  - `tsm_memory_size=24576`
  - `tlm_memory_size=2048`

- `emit_c/gen_kernel` 必须新增并通过 `npu_demo` 专项测试，生成源码至少能机械命中：
  - `npu_demo::KernelContext& ctx`
  - `ctx.thread_id()`
  - `ctx.thread_num()`
  - `ctx.get_dynamic_memory<float>(MemorySpace::TSM)`
  - `ctx.get_dynamic_memory<float>(MemorySpace::TLM)`
  - `slice(target, source, offset, size, stride)`
  - `deslice(`
  - `add(`

- 生成源码中不得出现：
  - `.view<`
  - `load<`
  - `store<`
  - `auto tile = slice(source`
  - `launch(`
  - `arch.launch_kernel`
  - `barrier`

## 当前最直接的下一步

- 先在 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 增加 `npu_demo` 目标文本映射；这是当前 `npu_demo` 从 include 基线走向最终 kernel 源码的第一道硬断点。
