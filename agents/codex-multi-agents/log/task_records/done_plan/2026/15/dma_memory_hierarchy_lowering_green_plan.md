# dma_memory_hierarchy_lowering_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260405-dma-memory-hierarchy-s1` | `20260405-dma-memory-hierarchy-s1.md` | `已合并（commit 27871e8，T-20260406-0386d594，李白；gate exit=0）。` |
| `S2` | `S1` | `wt-20260405-dma-hierarchy-s2` | `20260405-dma-hierarchy-s2.md` | `已合并（merge_commit=bfb208c；record_fixup=dd2ec1b；T-20260406-7fd13d77，李白；gate exit=0）。` |
| `S3` | `S1` | `wt-20260405-dma-hierarchy-s3` | `20260405-dma-hierarchy-s3.md` | `已合并（merge_commit=a0f8d4c；T-20260406-fc1257e7，李白；gate exit=0）。` |
| `S4` | `S2、S3` | `wt-20260405-dma-hierarchy-s4` | `20260405-dma-hierarchy-s4.md` | `已合并（merge_commit=6b1c6be；T-20260406-9443f7a5，李白；gate exit=0）。` |
| `S5` | `S4` | `wt-20260405-dma-hierarchy-s5` | `20260405-dma-hierarchy-s5.md` | `已合并（merge_commit=4451be1；T-20260406-8593bd14，李白；gate exit=0）。` |
| `S6` | `S5` | `wt-20260405-dma-hierarchy-s6` | `20260405-dma-hierarchy-s6.md` | `已合并（merge_commit=0d9c604；T-20260406-0c140a7f，李白；gate exit=0）。` |

## 功能说明

- 本计划用于新增一个独立 lowering pass，把当前仍停留在 `GM` 上的 `kernel/dma` IR，改写为显式的分层数据搬运链：输入侧 `GM -> SM -> LM`，输出侧 `LM -> SM -> GM`。
- 本计划冻结一个额外硬约束：**本 pass 新增的分层搬运统一用 `dma.slice` / `dma.deslice` 表示**；不额外要求把输入里已有的 `dma.copy`、`dma.load`、`dma.store` 全量改写掉。
- 也就是说：整块搬运只是新增 `slice/deslice` 的特例——用全尺寸 `sizes`、零 `offsets`、单位 `strides` 表达，而不是为新路径单独引入 `dma.copy`。
- 该 pass 的职责是“显式化分层搬运路径”，不是自动找 tile、自动并行化、自动插 barrier、自动双缓冲，也不是直接 codegen。
- 本文件只给计划，不直接修改 `spec / 实现 / test`。
- 分工约束补充如下：
  - 任务默认按 `spec任务` 分发，但执行时允许联动修改 `spec / 功能实现 / test`，不能机械理解成“只改 spec”。
  - 每个 `spec任务` 都是同一条任务链的起点，任务书必须覆盖其后的 `实现/重构 -> 审查（含复审） -> 合并`。
  - `大闸蟹` 只在整个计划全部任务完成并合并后，进行统一的架构师验收；不对单个 `S*` 任务逐个验收。

## 范围与非目标

### 范围

- `spec`
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md)
  - 允许新增：[`spec/pass/lowering/dma_memory_hierarchy/spec.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/dma_memory_hierarchy/spec.md)
  - [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md)
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/spec/dialect/dma.md)
  - [`spec/dialect/kernel.md`](/home/lfr/kernelcode_generate/spec/dialect/kernel.md)
  - [`spec/operation/dma.md`](/home/lfr/kernelcode_generate/spec/operation/dma.md)
  - [`spec/symbol_variable/memory.md`](/home/lfr/kernelcode_generate/spec/symbol_variable/memory.md)
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/spec/analysis/analysis_engine.md)
- `功能实现`
  - 允许新增：[`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/dma_memory_hierarchy.py)
  - [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/pass_manager.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/dialect/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/dma.py)
  - [`kernel_gen/analysis/memory/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/__init__.py)
  - [`kernel_gen/analysis/memory/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/dma.py)
- `test`
  - 允许新增：[`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/test/pass/test_dma_memory_hierarchy.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/test/pass/test_pass_manager.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)

### 非目标

- 不在本 pass 中引入 tile 搜索、loop 生成、parallel mapping、double buffering、async token、event、barrier、stream 或 launch 语义。
- 不把“全量 DMA canonicalization”纳入本 pass；本轮只要求该 pass 新增的层级搬运主语义使用 `dma.slice` / `dma.deslice`。
- 不在本 pass 中重新 lower `nn.*`；输入必须是已经过 `nn_to_kernel` 的 `kernel/dma/func` IR。
- 不在本 pass 中改写函数 ABI；caller/callee 的 out-param 合同仍由 [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md) 负责。
- 不把 `TSM/TLM` 目标特化混入本轮 `P0` 主合同；本计划先冻结通用 `GM/SM/LM` 分层语义。若目标没有 `SM/LM`，必须显式失败，而不是静默改成别的层级。
- 不通过保留 `GM` 直连 `kernel.*` operand / out 的方式伪造“搬运已完成”；处理过的链路里，`kernel.*` 必须只消费/写回 `LM`。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`神秘人 (2026-04-06)`
- `文档`：[`agents/codex-multi-agents/log/task_records/done_plan/2026/15/dma_memory_hierarchy_lowering_green_plan.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/done_plan/2026/15/dma_memory_hierarchy_lowering_green_plan.md)
- `spec`：
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md)
  - [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md)
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/spec/dialect/dma.md)
  - [`spec/operation/dma.md`](/home/lfr/kernelcode_generate/spec/operation/dma.md)
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/spec/analysis/analysis_engine.md)
- `功能实现`：
  - [`kernel_gen/passes/pass_manager.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/dialect/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/dma.py)
  - [`kernel_gen/analysis/memory/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/dma.py)
- `test`：
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/test/pass/test_pass_manager.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)

## 外部参考

- 仅作分层职责校准，不替代仓库内 spec：
  - MLIR Passes：<https://mlir.llvm.org/docs/Passes/>
  - MLIR Bufferization：<https://mlir.llvm.org/docs/Bufferization/>
  - MLIR NVGPU Dialect：<https://mlir.llvm.org/docs/Dialects/NVGPU/>
- 本轮只吸收三点共识，不直接照搬外部实现：
  - “计算 lowering”和“快存 promotion / copy insertion”分层处理，不把所有职责塞进一个 pass。
  - 分层搬运必须显式出现在 IR 中，而不是靠后端偷偷猜测。
  - 不支持的层级或容量约束必须 fail fast，不能静默 fallback。

## 当前设计状态

### 已有稳定前置

- [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md) 已冻结 `nn -> kernel` lowering，输出为 `kernel.* + dma.alloc + func`。
- [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md) 已冻结函数返回 memory 的 out-param 改写合同。
- [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/spec/dialect/dma.md) 已冻结 `dma.slice(target, source, ...)` 的目标式语义，以及 `dma.deslice(source, target, ...)` 的写回语义。
- [`spec/include/api/Dma.md`](/home/lfr/kernelcode_generate/spec/include/api/Dma.md) 与 `emit_c/gen_kernel` 当前也已经把 `slice/deslice` 作为稳定 helper 名称，这和“新增分层搬运统一用 `slice/deslice` 表示”的新约束是对齐的。

### 当前真实缺口

| 层级 | 当前状态 | 真实缺口 |
| --- | --- | --- |
| `pass spec` | `缺失` | 没有定义“GM 上 kernel/dma IR 如何被系统性改写成 GM->SM->LM / LM->SM->GM” |
| `pass impl` | `缺失` | `kernel_gen/passes/lowering/` 当前只有 `nn_to_kernel` 与 `buffer_results_to_out_params` |
| `pipeline` | `缺失` | 默认 lowering pipeline 还没有第三个 DMA hierarchy pass |
| `analysis` | `半缺失` | `dma.slice` 已纳入公开统计，但 `dma.deslice` 仍是 `skip + warning`，与未来 writeback 主路径冲突 |
| `target policy` | `存在冲突` | 当前 `npu_demo` 只有 `TSM/TLM` 动态容量，没有 `SM/LM`；本计划若先做通用 `SM/LM` pass，则 `npu_demo` 暂时不能直接启用 |

### 关键设计判断

- 这个 pass 不应塞进 [`kernel_gen/passes/lowering/nn_to_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/nn_to_kernel.py)。
  - `nn_to_kernel` 的职责是语义 lowering；
  - 本 pass 的职责是 memory hierarchy promotion / staging insertion。
- 本 pass 的最小输入合同应当是：
  - `nn.*` 已经 lower 成 `kernel.*`
  - 函数 ABI 已经 out-param 化
  - 可见结果 buffer 仍在 `GM`
- 本 pass 的最小输出合同应当是：
  - 读路径：`GM -> SM -> LM`
  - 算路径：`kernel.*` 只在 `LM` 上执行
  - 写路径：`LM -> SM -> GM`
  - 搬运 op 只使用 `dma.slice / dma.deslice`

## 设计原则

- 所有新增分层搬运统一写成目标式 `slice/deslice`：
  - 读：`dma.slice(target, source, offsets, sizes, strides)`
  - 写：`dma.deslice(source, target, offsets, sizes, strides)`
- 整块搬运不是新语义，而是新增 `slice/deslice` 的特例：
  - `offsets = [0, ...]`
  - `sizes = source.shape`
  - `strides = [1, ...]`
- 处理过的 `kernel.*` op 只能看见 `LM` memory：
  - 输入若原本在 `GM`，先 `GM -> SM -> LM`
  - 输出若最终要回到 `GM`，先在 `LM` 生成 temporary，再 `LM -> SM -> GM`
- 动态 shape / symbol 不能丢：
  - staging `dma.alloc` 所需的 `dynamic_shape` 必须来自已有显式 symbol 值；
  - 若只有匿名 `?` 且无法恢复为显式 SSA 形状来源，必须显式失败。
- 不允许静默 shortcut：
  - 不允许读路径直接 `GM -> LM`
  - 不允许写路径直接 `LM -> GM`
  - 不允许保留 `kernel.*` 的 `GM` operand / out
- window 化与整块化走同一表示：
  - window 读写保留原 `offsets/sizes`（`strides` 仍受当前方言约束：必须是 unit stride）
  - 整块读写只是在这些参数上取“全量窗口”

## P0 目标合同

### Pass 公开名字与位置

- 新 pass 名字固定为：`lower-dma-memory-hierarchy`
- 建议执行顺序固定为：

```python
pm.add_pass(LowerNnToKernelPass())
pm.add_pass(BufferResultsToOutParamsPass())
pm.add_pass(LowerDmaMemoryHierarchyPass())
```

- 本 pass 不能跳到 `nn_to_kernel` 前面。
- 本 pass 的输入必须已经没有 `nn.*`，且需要有明确的 GM 可见 output buffer。

### 读路径合同

对每个要参与 `kernel.*` 计算的 `GM` operand，pass 必须显式生成：

```text
%sm = dma.alloc ... space=SM
%lm = dma.alloc ... space=LM
dma.slice(%sm, %gm, full_or_window_offsets, full_or_window_sizes, unit_strides)
dma.slice(%lm, %sm, zero_offsets, full_or_window_sizes, unit_strides)
```

- 第一个 `dma.slice` 负责 `GM -> SM`
- 第二个 `dma.slice` 负责 `SM -> LM`
- 对整块搬运，`full_or_window_*` 取整块范围
- 对窗口搬运：保留原 `offsets/sizes`，`strides` 仍为 `unit_strides`

### 算路径合同

处理后的 `kernel.*` 必须只引用 `LM` memory：

```text
%out_lm = dma.alloc ... space=LM
kernel.add ins(%lhs_lm, %rhs_lm) outs(%out_lm) space=#nn.space<local>
```

- `kernel.*` 的 `space` 必须改为 `LM`
- 输入、输出都不能继续是 `GM` 或 `SM`

### 写路径合同

对每个最终要落回 `GM` 的结果，pass 必须显式生成：

```text
%out_sm = dma.alloc ... space=SM
dma.deslice(%out_lm, %out_sm, zero_offsets, result_sizes, unit_strides)
dma.deslice(%out_sm, %out_gm, full_or_window_offsets, result_sizes, unit_strides)
```

- 第一个 `dma.deslice` 负责 `LM -> SM`
- 第二个 `dma.deslice` 负责 `SM -> GM`
- 若结果对应窗口写回，第二个 `dma.deslice` 必须保留原写回 `offsets/sizes`（`strides` 仍为 unit stride）
- 若结果是整块输出，第二个 `dma.deslice` 仍用全量窗口，而不是单独引入 `dma.copy`

### 输出 IR 形态合同

- 处理后的 IR 允许继续包含：
  - `dma.alloc`
  - `dma.slice`
  - `dma.deslice`
  - `kernel.*`
  - `func.*`
- 本 pass 新增的 hierarchy 搬运路径不允许使用以下 op 作为主搬运语义：
  - `dma.copy`
  - `dma.load`
  - `dma.store`
- 若输入里原本就存在这些 op：
  - 本轮不要求 pass 统一正规化它们；
  - 但本 pass 不能继续新增同类 op 来表达 `GM -> SM -> LM` 或 `LM -> SM -> GM`。

## P1 预留目标

- 若后续需要适配 `npu_demo`，可以新增同族目标策略：
  - `GM -> TSM -> TLM`
  - `TLM -> TSM -> GM`
- 但这必须作为单独 spec / 任务处理，不能在本轮 `SM/LM` pass 里偷偷混入。
- 若后续需要 async / double buffer，也必须单独起 pass 或单独扩展本 pass spec；本轮不预留隐式行为。

## 完成定义

- 新增 [`spec/pass/lowering/dma_memory_hierarchy/spec.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/dma_memory_hierarchy/spec.md)，并与 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md) 的顺序合同一致。
- 新增 [`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/dma_memory_hierarchy.py)，并从 [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/__init__.py) 导出。
- `test/pass/test_dma_memory_hierarchy.py` 至少覆盖：
  - 整块读路径 `GM -> SM -> LM`
  - 整块写路径 `LM -> SM -> GM`
  - window 读写路径保留 `offsets/sizes`（`strides` 为 unit stride）
  - `kernel.*` 最终只消费 `LM`
  - 新增 hierarchy 路径不引入 `dma.copy/load/store`
  - 动态 symbol shape 可透传到 staging alloc
  - 无法恢复匿名 `?` 时显式失败
  - target 无 `SM/LM` 容量时显式失败
- 若 [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/spec/analysis/analysis_engine.md) 仍把 `dma.deslice` 视为 `skip + warning`，则本计划不算完成；analysis 必须至少把 `dma.deslice` 纳入正式 writeback 路径统计。
- 以下 gate 全部通过：

```bash
pytest -q test/pass/test_dma_memory_hierarchy.py
pytest -q test/pass/test_pass_manager.py -k 'dma_memory_hierarchy'
pytest -q test/analysis/test_analysis.py -k 'dma_deslice or dma_memory_hierarchy'
```

- 仅当全部 `S*` 任务都完成并合并后，整个计划才进入 `待架构师验收`。

## 计划任务

### `S1`

- `任务类型`：`spec任务（允许联动 spec / 实现 / test）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：新增 [`spec/pass/lowering/dma_memory_hierarchy/spec.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/dma_memory_hierarchy/spec.md)，冻结 pass 名字、执行顺序、输入/输出合同，以及“本 pass 新增搬运统一用 `slice/deslice` 表示”的主边界。
- `需要收口的合同`：
  - pass 名字固定为 `lower-dma-memory-hierarchy`
  - 顺序固定为 `LowerNnToKernelPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`
  - 本 pass 新增的搬运主语义只允许 `dma.slice / dma.deslice`
  - `kernel.*` 最终只允许 `LM` operand / out
- `代码示例`：

```python
pm.add_pass(LowerNnToKernelPass())
pm.add_pass(BufferResultsToOutParamsPass())
pm.add_pass(LowerDmaMemoryHierarchyPass())
```

```text
%sm = dma.alloc ... space=SM
%lm = dma.alloc ... space=LM
dma.slice(%sm, %gm, offsets, sizes, strides)
dma.slice(%lm, %sm, %zero_offsets, sizes, %unit_strides)
```

- `可改文件`：
  - 允许新增：[`spec/pass/lowering/dma_memory_hierarchy/spec.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/dma_memory_hierarchy/spec.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md)
- `验收标准`：
  - spec 明确写清“新增 hierarchy 搬运”遵循 slice/deslice-only 合同
  - spec 明确写清整块搬运也是新增 slice/deslice 特例
  - spec 明确写清 target 无 `SM/LM` 时必须失败

### `S2`

- `任务类型`：`spec任务（允许联动 spec / 实现 / test）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：实现 pass 骨架与 kernel operand/out staging 重写，让逐元素 `kernel.*` 真正变成 `LM` 计算。
- `需要收口的合同`：
  - 每个 `GM` 输入都要先 `GM -> SM -> LM`
  - 每个 `GM` 输出都要先落 `LM` temporary
  - `kernel.*` 的 `space` 改成 `LM`
- `代码示例`：

```text
# 改写前
kernel.add ins(%lhs_gm, %rhs_gm) outs(%out_gm) space=#nn.space<global>
```

```text
# 改写后
%lhs_sm = dma.alloc ... space=SM
%lhs_lm = dma.alloc ... space=LM
%rhs_sm = dma.alloc ... space=SM
%rhs_lm = dma.alloc ... space=LM
%out_lm = dma.alloc ... space=LM
dma.slice(%lhs_sm, %lhs_gm, full_offsets, full_sizes, unit_strides)
dma.slice(%lhs_lm, %lhs_sm, zero_offsets, full_sizes, unit_strides)
dma.slice(%rhs_sm, %rhs_gm, full_offsets, full_sizes, unit_strides)
dma.slice(%rhs_lm, %rhs_sm, zero_offsets, full_sizes, unit_strides)
kernel.add ins(%lhs_lm, %rhs_lm) outs(%out_lm) space=#nn.space<local>
```

- `可改文件`：
  - 允许新增：[`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/dma_memory_hierarchy.py)
  - [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/__init__.py)
  - [`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/test/pass/test_dma_memory_hierarchy.py)
- `验收标准`：
  - pass 输出中处理过的 `kernel.*` 只看见 `LM`
  - 不允许留下 `kernel.*` 直接读/写 `GM`
  - 本 pass 新增的全量路径不引入 `dma.copy`

### `S3`

- `任务类型`：`spec任务（允许联动 spec / 实现 / test）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：实现 window 化读写，并约束本 pass 新增的层级搬运统一使用 `slice/deslice`；不承担现有 `dma` op 的全量正规化。
- `需要收口的合同`：
  - 本 pass 新增的整块路径用 `slice/deslice` 特例表达
  - 本 pass 不新增 `dma.load` / `dma.store` 作为 hierarchy 搬运
  - window 读写保留原 `offsets/sizes`；本 pass 新增 hierarchy 路径的 `strides` 统一为 unit stride（当前仅 `1`，不引入非 `1` 或符号 stride 语义）
- `代码示例`：

```text
# 整块读（新路径不引入 dma.copy）
%sm = dma.alloc ...
%lm = dma.alloc ...
dma.slice(%sm, %gm_src, zero_offsets, full_sizes, unit_strides)
dma.slice(%lm, %sm, zero_offsets, full_sizes, unit_strides)
```

```text
# 窗口写回
%sm = dma.alloc ...
dma.deslice(%lm_tile, %sm, zero_offsets, tile_sizes, unit_strides)
dma.deslice(%sm, %gm_out, orig_offsets, tile_sizes, unit_strides)
```

- `可改文件`：
  - [`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/dma_memory_hierarchy.py)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/spec/dialect/dma.md)
  - [`spec/operation/dma.md`](/home/lfr/kernelcode_generate/spec/operation/dma.md)
  - [`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/test/pass/test_dma_memory_hierarchy.py)
- `验收标准`：
  - 本 pass 新增路径没有 `dma.copy/load/store`
  - window 参数保持一致（`offsets/sizes` 保留；`strides` 为 unit stride）
  - 整块路径严格用 full-window `slice/deslice` 表示

### `S4`

- `任务类型`：`spec任务（允许联动 spec / 实现 / test）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：补动态 shape / symbol 透传与显式失败边界。
- `需要收口的合同`：
  - staging `dma.alloc` 的 `dynamic_shape` 必须从已有显式 symbol 来源构造
  - 匿名 `?` 且无可恢复来源时必须失败
  - target `SM/LM` 容量缺失时必须失败
- `代码示例`：

```text
# 允许：有显式 symbol 来源
%M = symbol.dim %src, 0
%sm = dma.alloc(%M, %N) : !nn.memory<[?, ?], ... #nn.space<shared>>
```

```text
# 禁止：只有匿名 ?，没有 shape SSA 来源
%sm = dma.alloc(?) ...   # 必须失败，不能静默填 1 或保留不可执行状态
```

- `可改文件`：
  - [`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/dma_memory_hierarchy.py)
  - [`spec/pass/lowering/dma_memory_hierarchy/spec.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/dma_memory_hierarchy/spec.md)
  - [`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/test/pass/test_dma_memory_hierarchy.py)
- `验收标准`：
  - symbol shape 正例可通过
  - 匿名 `?` 坏例显式失败
  - 失败短语锁定 `dynamic_shape` / `SM` / `LM` 关键字之一

### `S5`

- `任务类型`：`spec任务（允许联动 spec / 实现 / test）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：把 pass 接入 pass 包与 pass_manager，并补顺序门禁。
- `需要收口的合同`：
  - lowering package 导出 `LowerDmaMemoryHierarchyPass`
  - `PassManager` 能手工注册并按顺序执行
  - 若本 pass 放在 `BufferResultsToOutParamsPass` 之前，必须显式失败
- `代码示例`：

```python
pm = PassManager(name="lowering")
pm.add_pass(LowerNnToKernelPass())
pm.add_pass(BufferResultsToOutParamsPass())
pm.add_pass(LowerDmaMemoryHierarchyPass())
module = pm.run(module)
```

- `可改文件`：
  - [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/pass_manager.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/pass_manager.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/test/pass/test_pass_manager.py)
  - [`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/test/pass/test_dma_memory_hierarchy.py)
- `验收标准`：
  - 顺序正确时通过
  - 顺序错误时 fail fast
  - 错误不允许被静默吞掉

### `S6`

- `任务类型`：`spec任务（允许联动 spec / 实现 / test）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：补 analysis 对 `dma.deslice` 的正式承接，避免 writeback 主路径落到 `skip + warning`。
- `需要收口的合同`：
  - `dma.deslice` 纳入正式 `memory_items / memory_totals_by_path`
  - writeback path 以 `source.space -> target.space` 归一
  - `LM->SM`、`SM->GM` 这两段 writeback 可机械读取
- `代码示例`：

```text
%sm = dma.alloc ... space=SM
dma.deslice(%lm_out, %sm, zero_offsets, sizes, unit_strides)
dma.deslice(%sm, %gm_out, orig_offsets, sizes, unit_strides)
```

- `可改文件`：
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/spec/analysis/analysis_engine.md)
  - [`kernel_gen/analysis/memory/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/__init__.py)
  - [`kernel_gen/analysis/memory/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/dma.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)
- `验收标准`：
  - `dma.deslice` 不再走 `skip + warning`
  - `LM->SM`、`SM->GM` 路径和字节量可读
  - 新 pass 产物进入 analysis 后不丢 writeback 统计
