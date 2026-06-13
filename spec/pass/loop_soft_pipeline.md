# loop_soft_pipeline.md

## 功能简介

- 定义 `loop-soft-pipeline` pass 的公开合同。
- `LoopSoftPipelinePass` 在可证明的 ring-backed matmul preload loop 上生成 `prologue -> steady loop -> epilogue` 软流水结构。
- 当前阶段只处理单个 `symbol.for` 直接 body 内 A/B 两路 `dma.copy -> kernel.matmul -> dma.advance_ring` 局部形态。
- 静态 single-tile loop 退化为 `prologue copy -> epilogue matmul`；无法静态证明至少一个 tile 的动态边界保持 no-op。
- 不支持结构、静态 zero-trip loop 与动态未知 trip 保持 no-op；本 pass 不生成 `arch.sign` / `arch.wait`，不做 core split，不新增 runtime event。
- 改写时必须清理旧 producer/consumer event attr，后续由 `ProducerConsumerAnalysisPass` 重新分析。

## API 列表

- `class LoopSoftPipelinePass(fold: bool = True)`
- `LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass`
- `LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`
- registry pass name：`loop-soft-pipeline`

## 文档信息

- `spec`：`spec/pass/loop_soft_pipeline.md`
- `功能实现`：`kernel_gen/passes/schedule/loop_soft_pipeline.py`
- `test`：`test/passes/schedule/test_loop_soft_pipeline.py`
- `expectation`：主仓只读合同资产 `expectation/pass/loop_soft_pipeline/**`
- 公开 API 确认来源：计划级任务 `T-20260613-bac54fd8` 与计划书 `ARCHITECTURE/plan/loop_soft_pipeline_ring_aware_producer_consumer.md`。

## 公开入口

- canonical path：`kernel_gen.passes.schedule.loop_soft_pipeline`
- registry pass name：`loop-soft-pipeline`
- 不新增 package re-export：
  - `kernel_gen.passes.LoopSoftPipelinePass` 不属于本轮公开入口。
  - `kernel_gen.passes.schedule.LoopSoftPipelinePass` 不属于本轮公开入口。
- 不公开 `LoopSoftPipelinePassError`。
- 不公开共享 `ring_cursor_analysis` API。

## 依赖

- DMA ring op/type：`spec/dialect/dma.md`
- Kernel matmul op：`spec/dialect/kernel.md`
- Symbol loop/op：`spec/dialect/symbol.md`
- pass registry：`spec/pass/registry.md`
- producer/consumer 后续分析：`spec/pass/producer_consumer_analysis.md`
- npu-demo lowering pipeline：`spec/pass/pipeline/npu_demo_lowering.md`

## 目标

- 将 multi-buffer apply 生成的 A/B ring staging loop 改写为软流水形态。
- 在原 loop 前 preload 第一 tile。
- 在 steady loop 中计算当前 tile、advance ring cursor、preload 下一 tile。
- 在 loop 后用最后一个已 preload tile 生成 epilogue matmul。
- 保持多 tile 输出 IR 可由 ring-aware `producer-consumer-analysis` 标注 `loop_first` / `loop_carried` / `after_loop` 事件；single-tile 退化输出使用普通 `productor` / `consumer`。

## 合同

### 候选结构

- 候选必须是非声明 `func.func` 内的单个 `symbol.for`。
- loop body 必须是单 block，且只有一个 block argument。
- loop 不得携带 loop-carried result 或 init。
- loop body 内必须恰有一个 `kernel.matmul`。
- matmul 的 lhs/rhs operand 必须分别来自 matmul 前两个 ring-backed `dma.copy` target。
- copy target 必须来自 `dma.current_ring` 或其 `dma.reinterpret` alias 链。
- matmul 后必须存在覆盖 A/B target ring 的 `dma.advance_ring`。
- matmul 依赖的 symbol setup op 与 preload copy 依赖 op 必须都能在 loop body 内按 SSA 闭包定位。

### 改写结果

- 原 loop 前插入 preload copy 闭包，使用原 loop start 作为迭代值。
- steady loop 上界为最后一个实际迭代起点，计算公式为 `start + ((end - start - 1) floordiv step) * step`；该上界是 exclusive end，用于保留动态 tail 的合法迭代点。
- steady loop body 顺序固定为：
  - 当前 tile matmul setup；
  - `kernel.matmul`；
  - ring cursor `dma.advance_ring`；
  - `iter + step`；
  - 下一 tile preload copy 闭包。
- 原 loop 后插入 epilogue matmul setup 与 `kernel.matmul`，使用 steady loop 上界作为迭代值。
- 克隆的 op 不得保留旧 `productor` / `consumer` 或控制流分类 event attr。
- `dma.advance_ring` 只用于 cursor 推进，不因本 pass 生成同步或 event attr。
- 静态 trip count 恰为 1 时，不生成 steady loop、boundary op、`dma.advance_ring` 或 preload next；仅保留 prologue preload 与 epilogue matmul。

### no-op 边界

- unsupported 结构保持原状。
- 静态可判定 zero-trip 或非正 step loop 保持原状。
- 动态边界无法静态证明至少一个 tile 时保持原状；本版本不构造 guard。
- pass 专属 option 为空；未知 option 必须失败。

## API详细说明

### `class LoopSoftPipelinePass(fold: bool = True)`

- api：`class LoopSoftPipelinePass(fold: bool = True)`
- 参数：
  - `fold`：通用 pass 后 folding 开关；类型 `bool`；默认值 `True`。
- 返回值：`LoopSoftPipelinePass` 实例。
- 功能说明：构造 loop soft pipeline pass。
- 使用示例：

```python
from kernel_gen.passes.schedule.loop_soft_pipeline import LoopSoftPipelinePass

pass_obj = LoopSoftPipelinePass(fold=False)
```

- 注意事项：
  - 不接受模式选择、ring 分析策略或同步策略构造参数。
  - 当前文件之外不得调用本 pass 的内部候选识别、依赖闭包或 clone helper。

### `LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass`

- api：`LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass`
- 参数：
  - `options`：pass 专属 options；类型 `dict[str, str]`；当前只接受空字典。
- 返回值：`LoopSoftPipelinePass` 实例。
- 功能说明：为 registry 构造入口提供 pass 专属 option 解析。
- 使用示例：

```python
pass_obj = LoopSoftPipelinePass.from_options({})
```

- 注意事项：
  - `fold` 是 registry 通用 option，由 `build_registered_pass(...)` 先拆分并写入 pass 实例。
  - 未知 option 必须以 `KernelCodeError` 失败，错误文本包含 `unknown option: <name>`。

### `LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL context；类型 `Context`。
  - `module`：待改写 module；类型 `ModuleOp`。
- 返回值：`None`；原地改写 IR。
- 功能说明：遍历 `builtin.module` 中每个非声明 `func.func`，对可证明候选执行 soft-pipeline 改写。
- 使用示例：

```python
LoopSoftPipelinePass().apply(ctx, module)
```

- 注意事项：
  - 必须只使用公开 dialect op/type 与公开 pass API。
  - 不能通过跨文件非公开 helper 实现 ring cursor 分析。
  - 不支持结构必须 no-op，不得生成半改写 IR。

## 测试

- 测试文件：`test/passes/schedule/test_loop_soft_pipeline.py`
- 执行命令：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/schedule/test_loop_soft_pipeline.py
```

### 测试目标

- 验证 canonical import path 与公开 API。
- 验证 A/B ring preload loop 改写为 prologue / steady / epilogue。
- 验证静态 single-tile loop 退化为 prologue preload 与 epilogue matmul。
- 验证旧 producer/consumer event attr 被清理。
- 验证 unsupported、static zero-trip 与动态未知 trip no-op。
- 验证未知 pass 专属 option 失败。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-LOOP-SOFT-PIPELINE-001 | soft pipeline 改写 | A/B ring preload loop | 准备 `dma.current_ring -> dma.copy -> kernel.matmul -> dma.advance_ring` IR。 | 运行 `LoopSoftPipelinePass.apply(...)`。 | 输出 4 条 copy、2 条 matmul，结构顺序为 prologue copy、steady matmul/advance/preload next、epilogue matmul。 | `test_loop_soft_pipeline_rewrites_ring_preload_to_prologue_steady_epilogue` |
| TC-LOOP-SOFT-PIPELINE-001A | single-tile 退化 | `N == 1` 且 K 维正数 | 准备 `0 < K <= TILE_K` 的静态单 tile loop。 | 运行 `LoopSoftPipelinePass.apply(...)`。 | 输出仅保留 prologue preload 与 epilogue matmul，不生成 steady loop、boundary op 或 loop_* event attr。 | `test_loop_soft_pipeline_single_tile_degenerates_to_prologue_epilogue` |
| TC-LOOP-SOFT-PIPELINE-002 | event 清理 | 输入已有旧 event attr | 准备带 `productor` / `consumer` 的候选 IR。 | 运行 pass。 | 输出不残留旧 producer/consumer attr。 | `test_loop_soft_pipeline_clears_stale_producer_consumer_events` |
| TC-LOOP-SOFT-PIPELINE-003 | side-effect preload | copy source 由 `dma.deslice` 写入 | 准备 staging source ring，copy 前由 `dma.deslice` 写入 source memory。 | 运行 pass。 | prologue 与 steady preload next 都保留对应 `dma.deslice`，再执行 `dma.copy`。 | `test_loop_soft_pipeline_clones_preload_source_writes` |
| TC-LOOP-SOFT-PIPELINE-004 | no-op | unsupported、静态 zero-trip 与动态未知 trip | 准备非 ring RHS、静态 zero-trip loop 与无法证明正 trip 的动态边界。 | 运行 pass。 | IR 保持原结构，不插入 `symbol.sub` / `symbol.add`，动态未知 trip 不生成无条件 prologue。 | `test_loop_soft_pipeline_unsupported_and_zero_trip_keep_original_shape` / `test_loop_soft_pipeline_dynamic_unknown_trip_keeps_original_shape` |
| TC-LOOP-SOFT-PIPELINE-005 | options | 未知 option | 调用 `LoopSoftPipelinePass.from_options({"mode": "strict"})`。 | 构造 pass。 | 按 `unknown option: mode` 失败。 | `test_loop_soft_pipeline_from_options_rejects_unknown_options` |

## 合同验收

- 主仓只读合同资产：`expectation/pass/loop_soft_pipeline/**`。
- execute / review / merge 不得修改、复制、新建、删除或同步 expectation 文件。
- 验收命令：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate \
python3 -m expectation.pass.loop_soft_pipeline
```

- 记录必须写清 `expectation.*` 来自主仓、`kernel_gen.*` 来自任务 worktree。
