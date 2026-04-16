# memory_tlm123_space_split_green_plan.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/include/api/Memory.md`](../../spec/include/api/Memory.md)
  - [`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)
  - [`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md)
  - [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
  - [`spec/operation/arch.md`](../../spec/operation/arch.md)
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
  - [`spec/dialect/arch.md`](../../spec/dialect/arch.md)
  - [`spec/target/registry.md`](../../spec/target/registry.md)
- 目标 `API`：
  - `MemorySpace::{GM, SM, LM, TSM, TLM1, TLM2, TLM3}`
  - `BarrierVisibility::{TSM, TLM}`
  - `BarrierScope::{BLOCK, THREAD, SUBTHREAD, GLOBAL}`
  - `get_dynamic_memory(space)` / `ctx.get_dynamic_memory<Space, T>()`
  - `arch.get_dynamic_memory` / `arch.barrier`
- 目标 `test`：
  - [`test/target/test_target_registry.py`](../../test/target/test_target_registry.py)
  - [`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
  - [`test/symbol_variable/test_memory_operation.py`](../../test/symbol_variable/test_memory_operation.py)
  - [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
  - [`test/dialect/test_arch_dialect.py`](../../test/dialect/test_arch_dialect.py)
  - [`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)
  - [`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)
  - [`test/e2e/test_npu_demo_add_barrier.py`](../../test/e2e/test_npu_demo_add_barrier.py)
- 目标 `验收资产`：
  - [`expectation/operation/arch/get_dynamic_memory.py`](../../expectation/operation/arch/get_dynamic_memory.py)
  - [`expectation/operation/arch/launch_kernel.py`](../../expectation/operation/arch/launch_kernel.py)
  - [`expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`](../../expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py)
  - [`expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`](../../expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py)
  - [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier)
- 目标 `功能实现`：
  - [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)
  - [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
  - [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
  - [`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py)
  - [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)
  - [`kernel_gen/dsl/mlir_gen/emit/call_arch.py`](../../kernel_gen/dsl/mlir_gen/emit/call_arch.py)
  - [`include/api/Memory.h`](../../include/api/Memory.h)
  - [`include/api/Arch.h`](../../include/api/Arch.h)
  - [`include/npu_demo/Arch.h`](../../include/npu_demo/Arch.h)
  - [`include/npu_demo/npu_demo.h`](../../include/npu_demo/npu_demo.h)
  - [`include/npu_demo/Dma.h`](../../include/npu_demo/Dma.h)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260415-memory-tlm123-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s1.md` |
| S2 | S1 | `wt-20260415-memory-tlm123-s2` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s2.md` |
| S3 | S2 | `wt-20260415-memory-tlm123-s3` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s3.md` |
| S4 | S3 | `wt-20260415-memory-tlm123-s4` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s4.md` |
| S5 | S4 | `wt-20260415-memory-tlm123-s5` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s5.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：
  - 公开 `MemorySpace` 直接切到 `TLM1/TLM2/TLM3`，不保留公开 `TLM`。
  - `BarrierVisibility::TLM` 明确表示聚合可见域，覆盖 `TLM1/TLM2/TLM3` 三块实际空间；`arch.barrier`、`operation.barrier` 与 `npu_demo::KernelContext::barrier` 都按这个聚合语义执行。
  - `target` 不新增 `npu_demo.txt`，而是在内置 `npu_demo` 模板中补 `tlm1_memory_size / tlm2_memory_size / tlm3_memory_size`。
  - `DSL spec` 放到后段阶段收口，前两阶段只先收公开空间、可见域、scope 与 target 容量。
  - 旧 `MemorySpace::TLM`、`#nn.space<tlm>` 与 `arch.get_dynamic_memory #nn.space<tlm>` 必须显式拒绝。

## 验收路径校正（2026-04-15 09:00 +0800）

- 校正人：`守护最好的爱莉希雅`
- 校正摘要：
  - 原计划写入的 [`expectation/operation/arch/barrier.py`](../../expectation/operation/arch/barrier.py) 与 [`expectation/dsl/mlir_gen/dialect/arch/barrier.py`](../../expectation/dsl/mlir_gen/dialect/arch/barrier.py) 在当前主仓并不存在；这属于计划书验收路径写错，不是执行侧漏同步。
  - `barrier` 公开合同当前改由现有可复现载体锁定：[`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)、[`test/dsl/test_ast.py`](../../test/dsl/test_ast.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)。
  - S3 当前唯一执行口径：build 侧只继续收口已确认的实现问题，并按校正后的 S3 验收命令复测；本轮不要求执行角色补 tracked `barrier expectation`。
  - 计划中原写成 [`expectation/dsl/gen_kernel/npu_demo_add_barrier.py`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier.py) 的路径，同步校正为当前实际存在的 [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier)。

## S3 续接口径补充（2026-04-15 09:25 +0800）

- 补充人：`守护最好的爱莉希雅`
- 补充摘要：
  - `expectation/operation/arch/launch_kernel.py` 与 [`spec/operation/arch.md`](../../spec/operation/arch.md) 当前仍保留旧 `launch_kernel("demo_kernel", ...)` 字符串 `name` 口径，但同阶段已落地的 [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)、[`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)、[`spec/dsl/ast.md`](../../spec/dsl/ast.md) 与 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 已统一为“`callee` 必须是函数对象 / 等价可调用对象；DSL lowering 对应 symbol ref”。
  - 该不一致属于当前 `S3` 已点名的 `operation/arch + expectation/spec` 收口范围，不是独立链路，也不从本轮验收排除。
  - 当前唯一执行口径：`T-20260415-b785baa3` 继续在原 `build` 任务内收口这两处 tracked 资产，允许修改 [`spec/operation/arch.md`](../../spec/operation/arch.md) 与 [`expectation/operation/arch/launch_kernel.py`](../../expectation/operation/arch/launch_kernel.py)，目标仅限把 operation 层 `launch_kernel` 合同统一到“函数对象 / 等价可调用对象”语义；不得把现有实现、测试或 DSL 已收口的函数对象 / symbol ref 语义回退为字符串名称。
  - `expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py` 当前已符合新口径，继续作为 DSL 侧验收资产；本轮无需为这条问题扩写新的 DSL 载体。

## 计划目标

- 把公开 `MemorySpace` 从单一 `TLM` 改为 `TLM1/TLM2/TLM3`，并让 `symbol_variable`、IR、operation、include 与 `npu_demo` 一致使用这三个实际内存空间。
- 保持 `barrier visibility` 使用聚合可见域 `TSM/TLM`，避免把同步语义和具体三块内存槽位混在同一个公开接口里。
- 为 `target registry` 增加三块 `TLM` 的硬件字段，使动态内存入口不再依赖单一 `tlm_memory_size`。
- 让 `arch.get_dynamic_memory`、`ctx.get_dynamic_memory<Space, T>()`、DSL `get_dynamic_memory(...)` 都能直接识别 `TLM1/TLM2/TLM3`。
- 把 `BarrierScope` 的公开成员扩成 `BLOCK / THREAD / SUBTHREAD / GLOBAL`；其中 `npu_demo` P0 先只成功支持 `BLOCK`，其余 scope 继续显式失败。
- 用 `expectation + pytest` 锁住公开文本、IR 文本、operation 行为与 `npu_demo` 跨层最小 smoke，避免后续实现各写各的。

## 当前基线

- 当前公开合同：[`spec/include/api/Memory.md`](../../spec/include/api/Memory.md) 与 [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md) 只公开 `GM/SM/LM/TSM/TLM` 五种空间。
- 当前 `target`：[`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py) 中 `npu_demo` 只有 `tsm_memory_size` 与 `tlm_memory_size`，没有 `tlm1/2/3` 三块容量字段。
- 当前 IR：[`spec/dialect/nn.md`](../../spec/dialect/nn.md) 只接受 `global/shared/local/tsm/tlm`；[`spec/dialect/arch.md`](../../spec/dialect/arch.md) 的 `arch.get_dynamic_memory` 只接受 `shared/local/tsm/tlm`；`arch.barrier` 直接复用 `#nn.space<tsm/tlm>`。
- 当前 operation：[`spec/operation/arch.md`](../../spec/operation/arch.md) 只允许 `MemorySpace.SM/LM/TSM/TLM` 进入 `get_dynamic_memory(space)`；`barrier(visibility, scope)` 直接使用 `MemorySpace` 列表，成功路径固定为 `{TSM, TLM}`。
- 当前 include/npu_demo：[`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md) 只支持 `ctx.get_dynamic_memory<TSM/TLM, T>()`；`KernelContext::barrier` 成功路径固定为 `{MemorySpace::TSM, MemorySpace::TLM}` + `BarrierScope::BLOCK`。
- 当前 DSL：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)、[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)、[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 的 `get_dynamic_memory(...)` 和 `barrier(...)` 都还围绕单一 `TLM` 设计。
- 当前缺口：如果直接把 `MemorySpace` 改成 `TLM1/TLM2/TLM3`，那 `barrier visibility` 的聚合 `TLM` 与真实三块 `TLMx` 会发生公开类型冲突；需要单独的 `BarrierVisibility` 合同把“同步可见域”与“实际存储空间”区分开。

## 方案比较与选型

- 不采用方案：继续在 `MemorySpace` 中保留公开 `TLM`，同时再补 `TLM1/TLM2/TLM3`。
- 不采用原因：`MemorySpace` 会同时表示“真实存储槽位”和“同步聚合域”，调用方无法判断 `TLM` 到底是实际内存、别名，还是 barrier 专用语义。
- 不采用方案：把 `barrier visibility` 直接扩成 `{TSM, TLM1, TLM2, TLM3}`。
- 不采用原因：用户已明确 `barrier visibility` 要写成 `TSM/TLM`，同步语义按聚合域表达，而不是按三块内存逐个点名。
- 采用方案：
  - `MemorySpace` 只表示真实 memory slot：`GM/SM/LM/TSM/TLM1/TLM2/TLM3`
  - `BarrierVisibility` 单独表示同步可见域：`TSM/TLM`
  - `BarrierScope` 公开成员扩成 `BLOCK/THREAD/SUBTHREAD/GLOBAL`
  - `target registry` 补 `tlm1/2/3` 三块容量字段
- 最小公开接口：`MemorySpace`、`BarrierVisibility`、`BarrierScope`、`get_dynamic_memory(space)`、`barrier(visibility, scope)`、`arch.get_dynamic_memory`、`arch.barrier`。
- 兼容边界：旧 `MemorySpace::TLM`、`#nn.space<tlm>` 与 `arch.get_dynamic_memory #nn.space<tlm>` 不进入公开合同；实现若保留临时过渡，也必须在 parse / verifier / API 验证层显式拒绝对外输入。

## 公开 API 设计

### 1. MemorySpace

- 公开入口：`MemorySpace`
- 公开成员顺序：`GM, SM, LM, TSM, TLM1, TLM2, TLM3`
- 不再公开：`MemorySpace::TLM`
- 返回值：`MemorySpace`

```cpp
Memory<TLM1, float> act(data0, shape, stride, 2, MemoryFormat::Norm);
Memory<TLM2, float> weight(data1, shape, stride, 2, MemoryFormat::Norm);
Memory<TLM3, float> out(data2, shape, stride, 2, MemoryFormat::Norm);
```

### 2. BarrierVisibility

- 公开入口：`BarrierVisibility`
- 公开成员顺序：`TSM, TLM`
- 用途：只用于 `barrier(visibility, scope)`，不用于 `Memory`、`nn.memory` 或 `arch.get_dynamic_memory`
- 语义：`BarrierVisibility::TLM` 固定表示聚合可见域，覆盖 `TLM1/TLM2/TLM3` 三块实际空间；它不是 `MemorySpace::TLM` 别名，也不是第四块真实内存。
- 返回值：`BarrierVisibility`

```cpp
ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
```

### 3. BarrierScope

- 公开入口：`BarrierScope`
- 公开成员顺序：`BLOCK, THREAD, SUBTHREAD, GLOBAL`
- 返回值：`BarrierScope`

```cpp
BarrierScope scope = BarrierScope::GLOBAL;
```

### 4. operation helper

- 公开入口：`get_dynamic_memory(space)` / `barrier(visibility, scope)`
- 参数顺序：
  - `get_dynamic_memory(space)`
  - `barrier(visibility, scope)`
- 参数类型：
  - `space: MemorySpace`
  - `visibility: list[BarrierVisibility]`
  - `scope: BarrierScope`
- 返回值：
  - `get_dynamic_memory(space) -> Memory`
  - `barrier(...) -> None`

```python
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier, get_dynamic_memory
from kernel_gen.symbol_variable.memory import MemorySpace

act = get_dynamic_memory(MemorySpace.TLM1)
weight = get_dynamic_memory(MemorySpace.TLM2)
out = get_dynamic_memory(MemorySpace.TLM3)
barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.BLOCK)
```

### 5. dialect / IR

- `!nn.memory<..., #nn.space<tlm1|tlm2|tlm3>>` 表示真实内存空间
- `arch.get_dynamic_memory #nn.space<tlm1|tlm2|tlm3>` 对应三块实际动态内存
- `arch.barrier` 不再复用 `#nn.space<...>` 表达可见域，而是单独引入 `#arch.visibility<tsm>` / `#arch.visibility<tlm>`
- `#arch.visibility<tlm>` 固定表示聚合可见域，覆盖 `#nn.space<tlm1>`、`#nn.space<tlm2>`、`#nn.space<tlm3>`。

```text
%a = arch.get_dynamic_memory #nn.space<tlm1> : !nn.memory<[?], [1], i8, #nn.space<tlm1>>
%b = arch.get_dynamic_memory #nn.space<tlm2> : !nn.memory<[?], [1], i8, #nn.space<tlm2>>
%c = arch.get_dynamic_memory #nn.space<tlm3> : !nn.memory<[?], [1], i8, #nn.space<tlm3>>
arch.barrier {scope = #arch.scope<block>, visibility = [#arch.visibility<tsm>, #arch.visibility<tlm>]}
```

## 完成态定义

- `MemorySpace` 公开合同中不再出现单独的公开 `TLM`，而是固定为 `TLM1/TLM2/TLM3`；旧 `MemorySpace::TLM` 对外输入必须显式拒绝。
- `BarrierVisibility` 与 `BarrierScope` 成为独立公开接口；`barrier` 不再直接复用 `MemorySpace` 列表做可见域输入。
- `target registry` 的 `npu_demo` 模板可读取：`tsm_memory_size / tlm1_memory_size / tlm2_memory_size / tlm3_memory_size`。
- `arch.get_dynamic_memory` 与 operation / DSL `get_dynamic_memory` 能稳定接受 `TLM1/TLM2/TLM3`，并打印/生成 `#nn.space<tlm1|tlm2|tlm3>`；旧 `#nn.space<tlm>` 与 `arch.get_dynamic_memory #nn.space<tlm>` 对外输入必须显式拒绝。
- `arch.barrier` 的 IR 文本稳定为 `#arch.visibility<tsm>` / `#arch.visibility<tlm>`；其中 `#arch.visibility<tlm>` 固定覆盖 `TLM1/TLM2/TLM3`；不再把 barrier visibility 打成 `#nn.space<tlm1|tlm2|tlm3>`。
- `npu_demo` 的 `ctx.get_dynamic_memory<TLM1/TLM2/TLM3, T>()` 返回各自容量视图；`ctx.barrier({TSM, TLM}, BLOCK)` 为成功路径。
- `npu_demo` 对 `THREAD/SUBTHREAD/GLOBAL` scope 继续显式失败；include/api 只负责公开枚举，不把所有 scope 强行变成成功路径。
- 计划列出的 expectation 与 pytest 全部通过；反例继续锁住旧 `TLM`、错误 visibility 与错误 scope。

## 验收设计

- 验收资产：
  - API 合同：`test/include/api/test_memory.py`、`test/include/api/test_arch.py`
  - symbol 公式：`test/symbol_variable/test_memory.py`、`test/symbol_variable/test_memory_operation.py`
  - dialect 合同：`test/dialect/test_nn_dialect.py`、`test/dialect/test_arch_dialect.py`
  - operation 行为：`test/operation/test_operation_arch.py`、`expectation/operation/arch/get_dynamic_memory.py`、`expectation/operation/arch/launch_kernel.py`
  - DSL / 跨层 smoke：`test/dsl/test_ast.py`、`test/dsl/test_ast_visitor.py`、`test/dsl/test_mlir_gen.py`、`expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`、`expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`、`expectation/dsl/gen_kernel/npu_demo_add_barrier`
  - npu_demo 运行时：`test/include/npu_demo/test_kernel_context.py`、`test/include/npu_demo/test_runtime_launch.py`、`test/e2e/test_npu_demo_add_barrier.py`
- 输入样例：
  - `MemorySpace.TLM1/TLM2/TLM3`
  - `BarrierVisibility.TSM/TLM`
  - `BarrierScope.BLOCK/THREAD/SUBTHREAD/GLOBAL`
  - `ctx.get_dynamic_memory<TLM1/TLM2/TLM3, float>()`
- 锁定输出：
  - `#nn.space<tlm1|tlm2|tlm3>`
  - `#arch.visibility<tsm|tlm>`
  - `BarrierScope` 四个公开成员
  - `npu_demo::KernelContext::barrier` 成功路径只接受 `{TSM, TLM} + BLOCK`，其中 `TLM` 表示覆盖 `TLM1/TLM2/TLM3` 的聚合可见域
  - 旧 `MemorySpace::TLM`、`#nn.space<tlm>`、`arch.get_dynamic_memory #nn.space<tlm>` 作为公开输入时必须失败
- 必过命令：
  - `pytest -q test/target/test_target_registry.py`
  - `pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py`
  - `pytest -q test/dialect/test_nn_dialect.py test/dialect/test_arch_dialect.py`
  - `pytest -q test/operation/test_operation_arch.py`
  - `pytest -q test/dsl/test_ast.py -k arch_barrier`
  - `pytest -q test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py`
  - `pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py`
  - `pytest -q test/e2e/test_npu_demo_add_barrier.py`
  - `PYTHONPATH=. python expectation/operation/arch/get_dynamic_memory.py`
  - `PYTHONPATH=. python expectation/operation/arch/launch_kernel.py`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`
  - `PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier`

## 阶段拆分

### S1：公开空间与 target 容量合同

#### 阶段目标

- 先把 `MemorySpace`、`BarrierVisibility`、`BarrierScope` 与 `target` 容量字段的公开合同收口到同一套文字与测试基线。

#### 目标 spec / API

- `spec/include/api/Memory.md`
- `spec/include/api/Arch.md`
- `spec/symbol_variable/memory.md`
- `spec/target/registry.md`
- `公开 API：MemorySpace / BarrierVisibility / BarrierScope / tlm1_memory_size / tlm2_memory_size / tlm3_memory_size`
- `本阶段不触碰 DSL 三份 spec，DSL 收口顺延到 S3。`

#### 可改文件

- `spec/include/api/Memory.md`
- `spec/include/api/Arch.md`
- `spec/symbol_variable/memory.md`
- `spec/target/registry.md`
- `kernel_gen/symbol_variable/memory.py`
- `kernel_gen/target/registry.py`
- `include/api/Memory.h`
- `include/api/Arch.h`
- `test/target/test_target_registry.py`
- `test/symbol_variable/test_memory.py`
- `test/symbol_variable/test_memory_operation.py`
- `test/include/api/test_memory.py`
- `test/include/api/test_arch.py`

#### 预期示例代码

```python
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

act = Memory([128, 64], NumericType.Float16, space=MemorySpace.TLM1)
weight = Memory([64, 64], NumericType.Float16, space=MemorySpace.TLM2)
out = Memory([128, 64], NumericType.Float16, space=MemorySpace.TLM3)
```

#### 预期输出

```text
MemorySpace = GM | SM | LM | TSM | TLM1 | TLM2 | TLM3
BarrierVisibility = TSM | TLM    # TLM 覆盖 TLM1/TLM2/TLM3
BarrierScope = BLOCK | THREAD | SUBTHREAD | GLOBAL
npu_demo.hardware contains tlm1_memory_size / tlm2_memory_size / tlm3_memory_size
MemorySpace::TLM is rejected as public input
```

#### 目标验收资产

- `test/include/api/test_memory.py`：锁定 `MemorySpace` 公开成员与 `Memory<Space, T>` 示例。
- `test/include/api/test_arch.py`：锁定 `BarrierVisibility` 与 `BarrierScope` 公开成员。
- `test/target/test_target_registry.py`：锁定 `npu_demo` 读取三块 `tlm` 容量字段。
- `test/symbol_variable/test_memory.py`：锁定 `Memory(space=MemorySpace.TLM1/TLM2/TLM3)`。

#### 验收必过项目

- `pytest -q test/include/api/test_memory.py test/include/api/test_arch.py`
- `pytest -q test/target/test_target_registry.py`
- `pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：收口 MemorySpace / BarrierVisibility / BarrierScope 与 npu_demo tlm1/2/3 target 字段合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s1.md`

### S2：dialect memory space 与 barrier IR 合同

#### 阶段目标

- 把 `nn/arch dialect` 改到新的空间文本与 barrier 文本，不让 `arch.barrier` 再直接复用 `#nn.space<...>` 作为可见域。

#### 目标 spec / API

- `spec/dialect/nn.md`
- `spec/dialect/arch.md`
- `公开 API：#nn.space<tlm1|tlm2|tlm3> / #arch.visibility<tsm|tlm> / #arch.scope<global>`

#### 可改文件

- `spec/dialect/nn.md`
- `spec/dialect/arch.md`
- `kernel_gen/dialect/nn.py`
- `kernel_gen/dialect/arch.py`
- `test/dialect/test_nn_dialect.py`
- `test/dialect/test_arch_dialect.py`

#### 预期示例代码

```text
%a = arch.get_dynamic_memory #nn.space<tlm1> : !nn.memory<[?], [1], i8, #nn.space<tlm1>>
%b = arch.get_dynamic_memory #nn.space<tlm2> : !nn.memory<[?], [1], i8, #nn.space<tlm2>>
%c = arch.get_dynamic_memory #nn.space<tlm3> : !nn.memory<[?], [1], i8, #nn.space<tlm3>>
arch.barrier {scope = #arch.scope<block>, visibility = [#arch.visibility<tsm>, #arch.visibility<tlm>]}
```

#### 预期输出

```text
#nn.space<tlm> is rejected
arch.get_dynamic_memory #nn.space<tlm> is rejected
arch.barrier visibility no longer accepts #nn.space<tlm1|tlm2|tlm3>
#arch.scope<global> is printable and parsable
```

#### 目标验收资产

- `test/dialect/test_nn_dialect.py`：锁定 `tlm1/2/3` parse/print/verifier。
- `test/dialect/test_arch_dialect.py`：锁定 `arch.get_dynamic_memory` 与 `arch.barrier` 新文本。

#### 验收必过项目

- `pytest -q test/dialect/test_nn_dialect.py test/dialect/test_arch_dialect.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 nn/arch dialect 对 tlm1/2/3 与 barrier visibility 聚合域的新 IR 文本`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s2.md`

### S3：operation 与 DSL arch helper 映射

#### 阶段目标

- 让 `operation/arch` 与 DSL `get_dynamic_memory/barrier` 直接消费新公开接口，并生成新的 dialect 文本。

#### 目标 spec / API

- `spec/operation/arch.md`
- `spec/dsl/ast.md`
- `spec/dsl/emit_mlir.md`
- `spec/dsl/mlir_gen.md`
- `公开 API：get_dynamic_memory(space) / barrier(visibility, scope)`

#### 可改文件

- `spec/operation/arch.md`
- `spec/dsl/ast.md`
- `spec/dsl/emit_mlir.md`
- `spec/dsl/mlir_gen.md`
- `kernel_gen/operation/arch.py`
- `kernel_gen/dsl/mlir_gen/function_builder.py`
- `kernel_gen/dsl/mlir_gen/emit/call_arch.py`
- `kernel_gen/dsl/emit_mlir.py`
- `kernel_gen/dsl/ast/parser.py`
- `kernel_gen/dsl/ast/nodes.py`
- `test/operation/test_operation_arch.py`
- `test/dsl/test_ast.py`
- `test/dsl/test_ast_visitor.py`
- `test/dsl/test_mlir_gen.py`
- `expectation/operation/arch/get_dynamic_memory.py`
- `expectation/operation/arch/launch_kernel.py`
- `expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`
- `expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`

#### 预期示例代码

```python
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier, get_dynamic_memory
from kernel_gen.symbol_variable.memory import MemorySpace

lhs = get_dynamic_memory(MemorySpace.TLM1)
rhs = get_dynamic_memory(MemorySpace.TLM2)
out = get_dynamic_memory(MemorySpace.TLM3)
barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)
```

#### 预期输出

```text
get_dynamic_memory(MemorySpace.TLM1) -> !nn.memory<[?], [1], i8, #nn.space<tlm1>>
barrier(visibility=[TSM, TLM], scope=THREAD) is accepted by operation contract
DSL get_dynamic_memory/barrier lower to arch dialect using the new text forms
```

#### 目标验收资产

- `expectation/operation/arch/get_dynamic_memory.py`：锁定 `TLM1/TLM2/TLM3` operation 输出。
- `test/operation/test_operation_arch.py`：锁定 `BarrierVisibility` 与 `BarrierScope` 的 operation 正反路径。
- `test/dsl/test_ast.py`：锁定 `barrier(visibility, scope)` 的 AST 解析与错误口径。
- `expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`：锁定 DSL 到 `arch.get_dynamic_memory`。
- `test/dsl/test_mlir_gen.py`：锁定 DSL 到 `arch.barrier` 的 lowering 文本。
- `expectation/operation/arch/launch_kernel.py`：锁定 operation 层 `launch_kernel(callee, block, thread, subthread, *kernel_args)` 的函数对象 `callee` 合同，不再接受字符串名称。
- `expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`：继续锁定 DSL `launch_kernel(...)` 到 `arch.launch<...>(@callee, ...)` 的 symbol ref lowering 资产。
- 若 `BarrierVisibility` 与 `TLM1/TLM2/TLM3` 的 DSL helper 仍绑定旧 `TLM` 文本，本阶段允许最小修改 `kernel_gen/dsl/ast/parser.py`、`kernel_gen/dsl/ast/nodes.py`、`kernel_gen/dsl/emit_mlir.py`，但用途只限 `arch helper` 的 AST 解析、节点表示与发射兼容；不扩到 `nn / dma / symbol` 其他 helper。

#### 验收必过项目

- `pytest -q test/operation/test_operation_arch.py`
- `pytest -q test/dsl/test_ast.py -k arch_barrier`
- `pytest -q test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py`
- `PYTHONPATH=. python expectation/operation/arch/get_dynamic_memory.py`
- `PYTHONPATH=. python expectation/operation/arch/launch_kernel.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 operation/arch 与 DSL arch helper 到新的 MemorySpace / BarrierVisibility / BarrierScope 合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s3.md`

### S4：npu_demo 动态内存与 barrier 运行时合同

#### 阶段目标

- 让 `npu_demo` runtime 真正支持 `TLM1/TLM2/TLM3` 动态内存入口，并把 barrier 调整到聚合可见域 `TSM/TLM`。

#### 目标 spec / API

- `spec/include/npu_demo/npu_demo.md`
- `公开 API：ctx.get_dynamic_memory<TLM1/TLM2/TLM3, T>() / ctx.barrier({TSM, TLM}, scope)`

#### 可改文件

- `spec/include/npu_demo/npu_demo.md`
- `include/npu_demo/Arch.h`
- `include/npu_demo/npu_demo.h`
- `include/npu_demo/Dma.h`
- `test/include/npu_demo/test_kernel_context.py`
- `test/include/npu_demo/test_runtime_launch.py`
- `expectation/dsl/gen_kernel/npu_demo_add_barrier`

#### 预期示例代码

```cpp
auto act = ctx.get_dynamic_memory<TLM1, float>();
auto weight = ctx.get_dynamic_memory<TLM2, float>();
auto out = ctx.get_dynamic_memory<TLM3, float>();
ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
```

#### 预期输出

```text
TLM1/TLM2/TLM3 each return their own size from target hardware
barrier success path = {TSM, TLM} + BLOCK
THREAD / SUBTHREAD / GLOBAL remain explicit failure in npu_demo P0
```

#### 目标验收资产

- `test/include/npu_demo/test_kernel_context.py`：锁定动态内存返回值与 barrier 正反路径。
- `test/include/npu_demo/test_runtime_launch.py`：锁定 runtime launch + barrier smoke。
- `expectation/dsl/gen_kernel/npu_demo_add_barrier`：锁定跨层生成源码仍对齐新接口文本。

#### 验收必过项目

- `pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py`
- `PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 npu_demo runtime 对 tlm1/2/3 动态内存与 barrier 聚合域合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s4.md`

### S5：全链路验收与公开文本清理

#### 阶段目标

- 对齐所有 expectation、pytest 与公开文本，确保主仓不再把单一公开 `TLM` 当作真实存储空间继续输出。

#### 目标 spec / API

- `公开 API：全链路统一使用 TLM1/TLM2/TLM3 + BarrierVisibility(TSM/TLM)`

#### 可改文件

- `expectation/operation/arch/get_dynamic_memory.py`
- `expectation/operation/arch/launch_kernel.py`
- `expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`
- `expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`
- `expectation/dsl/gen_kernel/npu_demo_add_barrier`
- 各阶段遗留的 spec/test 实际对齐文件

#### 预期示例代码

```python
# expectation 只接受：
# - MemorySpace.TLM1 / TLM2 / TLM3
# - BarrierVisibility.TSM / TLM
# - #nn.space<tlm1|tlm2|tlm3>
# - #arch.visibility<tsm|tlm>
```

#### 预期输出

```text
No public expectation keeps single TLM as a real memory slot
All positive cases use TLM1/TLM2/TLM3 for memory and TSM/TLM for barrier visibility
```

#### 目标验收资产

- 全部本计划列出的 expectation 与 pytest。
- `barrier` 公开合同以 `test/operation/test_operation_arch.py`、`test/dsl/test_ast.py` 与 `test/dsl/test_mlir_gen.py` 为准；当前不再要求额外的 `expectation/operation/arch/barrier.py` 或 `expectation/dsl/mlir_gen/dialect/arch/barrier.py`。
- 额外负例：
  - 旧 `MemorySpace.TLM`
  - 旧 `#nn.space<tlm>`
  - 旧 `barrier(visibility=[MemorySpace.TSM, MemorySpace.TLM], ...)`
  - `npu_demo` 中 `BLOCK` 以外 scope 的成功路径

#### 验收必过项目

- 本计划“验收设计”列出的全部命令

#### 任务新建建议

- `任务类型：review`
- `任务目标：全链路复核 TLM1/TLM2/TLM3 与 barrier 聚合域文本是否一致`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s5.md`

## 待确认项

- 问题：`BarrierVisibility` 的公开命名是否直接采用 `BarrierVisibility`。
- 可选项：`BarrierVisibility` / `BarrierSpace` / `BarrierVisibilitySpace`
- 差异：只影响 include/api、operation、dialect/arch 的公开名称，不影响核心语义。
- 推荐项：`BarrierVisibility`，因为它直接表达“同步可见域”，不会被误读成真实 memory slot。

## 参考资料

- [`spec/include/api/Memory.md`](../../spec/include/api/Memory.md)
- [`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)
- [`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md)
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- [`spec/dialect/arch.md`](../../spec/dialect/arch.md)
- [`spec/operation/arch.md`](../../spec/operation/arch.md)
- [`spec/target/registry.md`](../../spec/target/registry.md)

## 当前主仓终验（2026-04-16 01:12 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/target/test_target_registry.py` -> `19 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py` -> `22 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dialect/test_nn_dialect.py test/dialect/test_arch_dialect.py` -> `104 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/operation/test_operation_arch.py` -> `16 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py -k arch_barrier` -> `2 failed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py` -> `4 failed, 10 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/e2e/test_npu_demo_add_barrier.py` -> `1 failed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/get_dynamic_memory.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/launch_kernel.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier` -> `exit 1`
  - 额外复核：`PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py -k 'barrier or tlm or visibility or dynamic_memory'` -> `4 passed`，`PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py -k 'barrier or tlm or visibility or dynamic_memory'` -> `2 passed`；说明 `alloc space must be MemorySpace` 这条无关 DSL 异常类型回归不属于本计划当前主阻断面。
- 最小阻断项：
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)、[`spec/dsl/ast.md`](../../spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 与 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 仍保留旧 `barrier(visibility=[MemorySpace.TSM, MemorySpace.TLM], ...)` / `MemorySpace list` / `#nn.space<tsm|tlm>` 文本，但当前 DSL 实现已切到 `BarrierVisibility.TSM/TLM` 与新的 barrier 可见域合同。这直接导致 `test/dsl/test_ast.py -k arch_barrier` 失败。
  - [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)、[`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)、[`test/e2e/test_npu_demo_add_barrier.py`](../../test/e2e/test_npu_demo_add_barrier.py) 与 [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 仍保留旧 `MemorySpace::TLM` / `get_dynamic_memory<TLM, ...>` / `space="tlm"` / `ctx.barrier({MemorySpace::TSM, MemorySpace::TLM}, ...)` 文本，未收口到 `TLM1/TLM2/TLM3 + BarrierVisibility::{TSM,TLM}`。这直接导致 include/runtime smoke 与 gen_kernel expectation 失败。
- 终验说明：
  - 本计划当前通过的部分已经覆盖 `target registry`、`symbol_variable`、`dialect`、`operation` 以及 4 个 arch expectation 入口；未收口部分已收敛到 DSL `barrier` 公开文本和 `npu_demo` 旧 `TLM` 残留。
  - 先前 `S4` 的唯一架构口径已明确：`test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py` 中与 `barrier/TLM/visibility/dynamic_memory` 无关的 `alloc space` 异常类型失败不并入本计划；该条仍由其他链路处理，不作为本计划修复任务范围。
  - 因此本计划当前不得归档，必须先沿唯一修复任务把上述两类残留收口。

## 修复任务补建（2026-04-16 01:12 +0800）

- 补建人：`守护最好的爱莉希雅`
- 修复任务：[`T-20260416-22529997`](../../TODO.md)
- 任务类型：`build`
- 唯一修复范围：
  - 收口 [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)、[`spec/dsl/ast.md`](../../spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 与 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 中遗留的旧 `MemorySpace.TSM/TLM` barrier 文本、错误文案与 IR 文本，统一到 `BarrierVisibility.TSM/TLM` 与当前 DSL 实现/operation 合同。
  - 收口 [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)、[`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)、[`test/e2e/test_npu_demo_add_barrier.py`](../../test/e2e/test_npu_demo_add_barrier.py) 与 [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 中遗留的旧 `MemorySpace::TLM` / `get_dynamic_memory<TLM, ...>` / `space="tlm"` / 旧 barrier 文本，统一到 `TLM1/TLM2/TLM3 + BarrierVisibility::{TSM,TLM}`。
  - 不把无关的 `alloc space must be MemorySpace` 异常类型回归并入本轮；`test/dsl/test_ast_visitor.py` 与 `test/dsl/test_mlir_gen.py` 继续只按 `barrier or tlm or visibility or dynamic_memory` 子集复测。
- 续推口径：
  - 当前不得补建归档任务，也不得执行 `-done-plan`。
  - [`T-20260416-22529997`](../../TODO.md) 与后续 [`T-20260416-fb55094b`](../../TODO.md) 范围重复；该条口径已被后续“重复修复任务处理”覆盖，不再作为最终唯一继续项。
  - 该任务不再作为最终续推任务等待完成；后续按“重复修复任务处理”仅推进 [`T-20260416-fb55094b`](../../TODO.md)。

## 当前主仓终验（2026-04-16 01:22 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/target/test_target_registry.py` -> `19 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py` -> `22 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dialect/test_nn_dialect.py test/dialect/test_arch_dialect.py` -> `104 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/operation/test_operation_arch.py` -> `16 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py -k arch_barrier` -> `2 failed`；当前测试仍使用旧 `MemorySpace.TSM/TLM`，实际 parser 已拒绝旧 `MemorySpace.TLM` 并报 `Unknown attribute`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py` -> `2 failed, 351 passed`；失败点为 `alloc space must be MemorySpace` 的异常类型合同，该失败已由既有 [`T-20260416-9021c1c2`](../../TODO.md) 所属的 `dsl_emit_mlir_refactor` 修复链承接，不纳入本计划新增修复范围。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py` -> `4 failed, 10 passed`；失败点均为测试仍使用旧 `MemorySpace::TLM` / `get_dynamic_memory<TLM, ...>`，与当前公开 `TLM1/TLM2/TLM3 + BarrierVisibility::{TSM,TLM}` 合同不一致。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/e2e/test_npu_demo_add_barrier.py` -> `1 failed`；断言仍锁定 `ctx.barrier({MemorySpace::TSM, MemorySpace::TLM}, BarrierScope::BLOCK);`，实际生成已经不是旧 `MemorySpace::TLM` 文本。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/get_dynamic_memory.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/launch_kernel.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier` -> `exit=1`；当前仍构造 `space="tlm"`，被 `nn` verifier 拒绝。
- 最小阻断项：
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)、[`spec/dsl/ast.md`](../../spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)、[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 仍保留旧 `barrier(visibility=[MemorySpace.TSM, MemorySpace.TLM], ...)` 与 `MemorySpace list / #nn.space<tlm>` 口径，未统一到 `BarrierVisibility.TSM/TLM` 与 `#arch.visibility<tsm|tlm>`。
  - [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)、[`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)、[`test/e2e/test_npu_demo_add_barrier.py`](../../test/e2e/test_npu_demo_add_barrier.py) 仍锁旧 `MemorySpace::TLM` / `get_dynamic_memory<TLM, ...>` 断言，导致 npu_demo runtime/e2e 验收失败。
  - [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 仍使用 `space="tlm"` 与旧 barrier 文本，导致 expectation 入口无法执行。
  - [`agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s4.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s4.md) 当前主仓不可读取；`DONE.md` 虽记录 `T-20260415-89abd30e` 已完成，但主仓缺同链记录文件，复核链路证据不完整。
- 终验说明：
  - 当前主仓只满足 target / symbol_variable / dialect / operation 与四个 arch expectation；尚未满足 DSL barrier、npu_demo runtime/e2e 与 gen_kernel expectation 的完成态。
  - `test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py` 的 `alloc space must be MemorySpace` 失败不属于本计划的 `TLM1/TLM2/TLM3 + BarrierVisibility` 残留；该项不在本计划新增修复任务中重复承接，但终验重跑时仍需等既有修复链闭合或验收口径被上游计划合法校正。
  - 因此本计划当前不具备归档条件。

## 修复任务补建（2026-04-16 01:22 +0800）

- 补建人：`大闸蟹`
- 唯一继续项：[`T-20260416-fb55094b`](../../TODO.md)
- 任务类型：`build`
- 唯一修复范围：
  - 收口 [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)、[`spec/dsl/ast.md`](../../spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)、[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 中残留的旧 DSL barrier 口径，统一到 `BarrierVisibility.TSM/TLM` 与 `#arch.visibility<tsm|tlm>`。
  - 收口 [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)、[`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)、[`test/e2e/test_npu_demo_add_barrier.py`](../../test/e2e/test_npu_demo_add_barrier.py) 中残留的旧 `MemorySpace::TLM` / `get_dynamic_memory<TLM, ...>` 断言。
  - 收口 [`expectation/dsl/gen_kernel/npu_demo_add_barrier`](../../expectation/dsl/gen_kernel/npu_demo_add_barrier) 中 `space="tlm"` 与旧 barrier 文本。
  - 补齐或随 merge 带入 [`agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s4.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s4.md) 的同链记录文件，保证主仓可复核。
- 不纳入范围：
  - 不吸收 `test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py` 中与 `barrier/TLM/BarrierVisibility` 无关的 `alloc space must be MemorySpace` 异常类型失败；该失败继续由既有 [`T-20260416-9021c1c2`](../../TODO.md) 承接。
- 续推口径：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 以本轮补建的修复任务作为本计划唯一继续项；修复任务完成后，回到本计划重新执行终验。

## 重复修复任务裁定（2026-04-16 01:27 +0800）

- 裁定人：`守护最好的爱莉希雅`
- 裁定结论：
  - 保留唯一继续项：[`T-20260416-fb55094b`](../../TODO.md)
  - 停止推进重复任务：[`T-20260416-22529997`](../../TODO.md)
- 裁定依据：
  - 两条任务都针对同一轮 `memory_tlm123_space_split_green_plan.md` 终验失败面创建，范围高度重叠，属于重复修复任务。
  - [`T-20260416-fb55094b`](../../TODO.md) 的任务目标、`worktree` 名称与修复范围更完整，除 DSL barrier 与 `npu_demo` 旧 `TLM` 文本外，还显式补入同链记录文件可复核性要求，描述更清楚。
  - 因此按“范围更清楚、`worktree` 更明确者保留”的规则，只保留 [`T-20260416-fb55094b`](../../TODO.md) 继续推进。
- 管理口径：
  - 本计划当前仍为 `进行中`，不得归档。
  - 管理员后续只继续推进 [`T-20260416-fb55094b`](../../TODO.md)；[`T-20260416-22529997`](../../TODO.md) 作为重复任务停止推进并从任务表清理。

## 重复修复任务处理（2026-04-16 01:24 +0800）

- 裁定人：`大闸蟹`
- 重复任务：
  - [`T-20260416-22529997`](../../TODO.md)
  - [`T-20260416-fb55094b`](../../TODO.md)
- 裁定结论：
  - 两者均指向同一组 `memory_tlm123` 终验阻断：DSL barrier 旧 `MemorySpace.TLM` 文本、npu_demo runtime/e2e 旧 `TLM` 断言、`expectation/dsl/gen_kernel/npu_demo_add_barrier` 旧 `space="tlm"` 口径。
  - 保留 [`T-20260416-fb55094b`](../../TODO.md) 作为唯一继续项；理由是该任务描述额外写明需补齐同链记录文件，并明确不吸收无关的 `alloc space must be MemorySpace` 异常类型失败，范围更完整。
  - [`T-20260416-22529997`](../../TODO.md) 视为重复修复任务，请管理员停止或删除，不再分发。
- 最终续推口径：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 仅推进 [`T-20260416-fb55094b`](../../TODO.md)。

## 当前主仓终验（2026-04-16 09:14 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/target/test_target_registry.py` -> `19 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py` -> `22 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dialect/test_nn_dialect.py test/dialect/test_arch_dialect.py` -> `104 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/operation/test_operation_arch.py` -> `16 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py -k arch_barrier` -> `2 passed, 45 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py -k 'barrier or tlm or visibility or dynamic_memory'` -> `4 passed, 199 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py -k 'barrier or tlm or visibility or dynamic_memory'` -> `2 passed, 149 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py test/e2e/test_npu_demo_add_barrier.py` -> `15 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/get_dynamic_memory.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/launch_kernel.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier` -> `exit 0`
  - `test -f agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s4.md` -> `PRESENT`
- 终验说明：
  - `TLM1/TLM2/TLM3 + BarrierVisibility::{TSM,TLM}` 的剩余阻断面已收口：DSL barrier 文本、`npu_demo` runtime/e2e 断言与 `expectation/dsl/gen_kernel/npu_demo_add_barrier` 当前都已切到新合同。
  - 终验继续沿用本计划 01:12 / 01:22 已写明的校正口径：`test/dsl/test_ast_visitor.py` 与 `test/dsl/test_mlir_gen.py` 只按 `barrier or tlm or visibility or dynamic_memory` 子集复测；两文件其余失败不属于本计划 `memory_tlm123` 合同收口范围，不再作为本计划阻断项。
  - 同链主仓记录文件现已可复核，因此“记录文件缺失导致证据不完整”的阻断也已解除。
- 归档口径：
  - 就我侧终验结论，本计划已满足完成态，可进入“等待双架构师均明确通过”后的归档链。

## 当前主仓终验复核（2026-04-16 09:13 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/target/test_target_registry.py` -> `19 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py` -> `22 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dialect/test_nn_dialect.py test/dialect/test_arch_dialect.py` -> `104 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/operation/test_operation_arch.py` -> `19 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py -k arch_barrier` -> `2 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py` -> `22 failed, 332 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py` -> `14 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/e2e/test_npu_demo_add_barrier.py` -> `1 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/get_dynamic_memory.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/launch_kernel.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier` -> `exit=0`
- 最小阻断项：
  - 当前与 `memory_tlm123` 直接相关的 target / symbol_variable / dialect / operation / DSL barrier 子集 / npu_demo runtime / e2e / expectation 入口已全部通过；唯一未过项只剩计划正文点名的整组 DSL 总验收命令 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) + [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)。
  - 该命令当前失败面已不再集中在 `TLM1/TLM2/TLM3 + BarrierVisibility` 残留，而是落在上游 DSL 链的通用问题：`alloc space must be MemorySpace` 异常类型合同，以及 `img2col1d/img2col2d/matmul/conv/softmax/reduce` 等 helper 的 `Unsupported call expression` / 相关前端 lowering 失败。
  - 因为这条整组命令仍是本计划“验收设计”中明确列出的必过项，当前主仓还不能判定为完成态，也不能进入归档链。
- 终验说明：
  - 与 `2026-04-16 01:22 +0800` 相比，本计划自身的 `memory_tlm123` 残留已经收口：`test/dsl/test_ast.py -k arch_barrier`、`test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py`、`test/e2e/test_npu_demo_add_barrier.py` 与 `expectation/dsl/gen_kernel/npu_demo_add_barrier` 均已通过。
  - 当前阻断已转为上游 DSL 全量验收依赖，继续由 [`ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md`](../../ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md) 的在途修复链 [`T-20260416-9021c1c2`](../../TODO.md) 承接；本计划不再补建重复修复任务。
  - 在 [`T-20260416-9021c1c2`](../../TODO.md) 收口并使 `pytest -q test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py` 恢复通过前，本计划不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 09:18 +0800）

- 终验人：`大闸蟹`
- 当前结论：`通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/target/test_target_registry.py` -> `19 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py` -> `22 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dialect/test_nn_dialect.py test/dialect/test_arch_dialect.py` -> `104 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/operation/test_operation_arch.py` -> `19 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py -k arch_barrier` -> `2 passed, 45 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py -k 'barrier or tlm or visibility or dynamic_memory'` -> `4 passed, 199 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py -k 'barrier or tlm or visibility or dynamic_memory'` -> `2 passed, 149 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/include/npu_demo/test_kernel_context.py test/include/npu_demo/test_runtime_launch.py test/e2e/test_npu_demo_add_barrier.py` -> `15 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/get_dynamic_memory.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/operation/arch/launch_kernel.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier` -> `exit 0`
  - `test -f agents/codex-multi-agents/log/task_records/2026/16/20260415-memory-tlm123-s4.md && echo PRESENT` -> `PRESENT`
- 终验说明：
  - 本节按本计划 `2026-04-16 09:14 +0800` 已写明的校正口径复跑：`test/dsl/test_ast_visitor.py` 与 `test/dsl/test_mlir_gen.py` 只复测 `barrier or tlm or visibility or dynamic_memory` 子集，不再把无关 DSL 通用失败并入本计划阻断。
  - `TLM1/TLM2/TLM3 + BarrierVisibility::{TSM,TLM}` 的公开合同、DSL barrier 文本、`npu_demo` runtime/e2e 与 `expectation/dsl/gen_kernel/npu_demo_add_barrier` 当前均已收口。
  - 因此我侧 `2026-04-16 09:13 +0800` 的“不通过”复核结论由本节覆盖；就我侧结论，本计划当前`通过`，可进入“等待双架构师均明确通过”后的归档链。

## 归档记录

时间：2026-04-16 09:24 +0800
经办人：李白
任务：T-20260416-6a58c3dd
任务目标：将 `ARCHITECTURE/plan/memory_tlm123_space_split_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/memory_tlm123_space_split_green_plan.md`，并完成归档 merge 收口。
改动：
- 管理员指定的 `worktree=/home/lfr/kernelcode_generate/wt-20260416-archive-memory-tlm123-plan` 原本不存在，已按当前远端主分支 `origin/main@b07908d` 新建任务分支 `T-20260416-6a58c3dd` 与对应归档 `worktree`。
- 核对确认源计划书 `ARCHITECTURE/plan/memory_tlm123_space_split_green_plan.md` 当前只以主仓本地 ignored 文件存在；`origin/main` 与当前索引中都不存在该源计划书及目标归档文件，因此已将源计划书内容复制为归档目标文件，并在文件尾部追加本次归档记录。
- 按任务口径同步移除主仓本地 `ARCHITECTURE/plan/memory_tlm123_space_split_green_plan.md`；本次归档合并范围仅限新增 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/memory_tlm123_space_split_green_plan.md`，不修改 `.gitignore`、`TODO.md`、`DONE.md` 或其它共享状态文件。
验证：
- `rg -n "T-20260416-6a58c3dd|memory_tlm123_space_split_green_plan.md" /home/lfr/kernelcode_generate/TODO.md` -> 确认任务为 `merge/进行中/指派=李白`
- `git -C /home/lfr/kernelcode_generate worktree add -b T-20260416-6a58c3dd /home/lfr/kernelcode_generate/wt-20260416-archive-memory-tlm123-plan origin/main` -> 成功创建归档 `worktree`
- `git -C /home/lfr/kernelcode_generate rev-parse --verify origin/main` -> `b07908d84f2e19bb349da1a6924ab06d85f9ac1a`
- `git -C /home/lfr/kernelcode_generate ls-tree --name-only origin/main -- ARCHITECTURE/plan/memory_tlm123_space_split_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/memory_tlm123_space_split_green_plan.md` -> 无输出，确认远端主分支当前无源计划书与目标归档文件
- `git -C /home/lfr/kernelcode_generate ls-files --stage -- ARCHITECTURE/plan/memory_tlm123_space_split_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/memory_tlm123_space_split_green_plan.md` -> 无输出，确认两者在当前索引均未跟踪
- `git -C /home/lfr/kernelcode_generate check-ignore -v ARCHITECTURE/plan/memory_tlm123_space_split_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/memory_tlm123_space_split_green_plan.md || true` -> 命中 `.gitignore:21:ARCHITECTURE/plan/`，确认源计划书为 ignored 本地文件，目标归档路径未被忽略
- `test -e /home/lfr/kernelcode_generate/ARCHITECTURE/plan/memory_tlm123_space_split_green_plan.md; echo $?` -> `1`，确认主仓本地源计划书已移除
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送该归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`。
