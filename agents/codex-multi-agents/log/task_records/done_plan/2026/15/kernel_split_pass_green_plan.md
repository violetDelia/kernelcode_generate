# kernel_split_pass_green_plan.md

## 进度（本地视图）

- 更新时间：`2026-04-06`
- 说明：进度以 `TODO.md` 与任务链记录为准；本段仅用于快速定位当前处于哪个 S 阶段。

| S 阶段 | 状态 | 任务/责任人 | 关键证据 |
| --- | --- | --- | --- |
| S1 | 已合并收口 | `T-20260406-8fcb4910` / 李白 | `merge_commit=48c2425`；gate：`pytest -q test/pass/test_lowering_kernel_split.py` → `14 passed`；记录：`agents/codex-multi-agents/log/task_records/2026/14/20260406-kernel-split-s1.md` |
| S2 | 已合并收口 | `T-20260406-b94920ab` / 李白 | `merge_commit=cf02845`；gate：`pytest -q test/pass/test_pass_manager.py` → `13 passed`；记录：`agents/codex-multi-agents/log/task_records/2026/14/20260406-kernel-split-s2.md` |
| S3 | 已合并收口 | `T-20260406-18a68e9e` / 李白 | `merge_commit=39fa1a0`；gate：`pytest -q test/dsl/test_gen_kernel.py` → `41 passed`；记录：`agents/codex-multi-agents/log/task_records/2026/15/20260406-kernel-split-s3.md` |

## 功能说明

- 本计划用于新增“kernel 切分”pass 的规格说明与下游桥接规则，不直接依赖当前实现是否已支持。
- 本计划参考外部编译器里“显式 split / tile + tuning knob”的常见做法：MLIR Transform Dialect 的 `loop.split` / tiling 思路，以及 TVM `split` / `define_split` 用调优参数表达切分因子的做法。
- 目标是先冻结稳定合同：pass 作用对象、`tuner.param` 驱动的动态 tile 合同、单函数内切分后的 IR 形态、分段执行与中间值承接规则、失败边界与 pipeline 顺序。
- 本计划只拆 `spec任务`，用于交给管理员后续统一推进实现、审查、复审与合并；本文件不是实现提交。

## 范围与非目标

### 范围

- 新增 `spec/pass/lowering/kernel_split.md`。
- 更新 `spec/pass/pass_manager.md` 中默认 lowering 链的推荐顺序与插入位置。
- 更新 `spec/dsl/gen_kernel.md` 中 split 后单函数源码形态的黑盒合同。
- 复用既有 `tuner.param` 作为动态 tile 因子的公开 IR 表达，不新增新的 tuning dialect/op。

### 非目标

- 不在本计划内定义自动并行、自动双缓冲、自动 DMA hierarchy。
- 不在本计划内新增新的 dialect op；切分只能通过 pass 重写既有 `func` / `kernel` / `dma` IR 表达，并复用已有 `tuner.param`。
- 不在本计划内把“循环切分”“数据块切分”“左右半区切分”混写成同一语义；本计划只定义“kernel 级切分 + tile 参数化”。
- 不在本计划内直接实现 pass、测试或 expectation 文件。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`神秘人 (2026-04-06)`
- `spec`：
  - [`agents/codex-multi-agents/log/task_records/done_plan/2026/15/kernel_split_pass_green_plan.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/done_plan/2026/15/kernel_split_pass_green_plan.md)
  - [`spec/pass/lowering/kernel_split.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/kernel_split.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md)
  - [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)
  - [`spec/dialect/tuner.md`](/home/lfr/kernelcode_generate/spec/dialect/tuner.md)
- `test`：
  - [`test/pass/test_lowering_kernel_split.py`](/home/lfr/kernelcode_generate/test/pass/test_lowering_kernel_split.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/test/pass/test_pass_manager.py)
  - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py)
- `功能实现`：
  - [`kernel_gen/passes/lowering/kernel_split.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/kernel_split.py)
  - [`kernel_gen/passes/pass_manager.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/dsl/gen_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/gen_kernel.py)

## 当前结构与判断

- 当前正式 lowering pass 只有 `LowerNnToKernelPass` 与 `BufferResultsToOutParamsPass`，默认链路也只公开这两个 pass，见 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md) 与 [`kernel_gen/passes/pass_manager.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/pass_manager.py)。
- 当前仓库没有正式 `kernel split` pass 规格，也没有“单个 kernel 在同一函数内被显式切分并保留 tile 执行结构”的公开合同。
- 当前仓库已经有 `tuner.param`，并且其返回类型是 `!symbol.dim<"name">`，适合作为 tile 因子的符号承接；但还没有任何 pass 把它正式接入切分合同，见 [`spec/dialect/tuner.md`](/home/lfr/kernelcode_generate/spec/dialect/tuner.md)。
- 若直接实现而不先冻结规格，最容易漂移的点有三类：
  - 切分发生在什么层：`nn` 阶段、`kernel` 阶段，还是 codegen 阶段。
  - tile 因子从哪里来：硬编码常量、pass 参数，还是 `tuner.param`。
  - 切分后如何承接：在同一 `func.func` 内生成显式 tile 循环 / 分段块，还是拆成多个 `func.func`。

## 计划默认口径

- P0 默认把 `kernel split` 定义为：对已经完成 `nn_to_kernel` 与 `buffer_results_to_out_params` 的函数级 IR 做 tile 化切分。
- P0 默认 tile 大小不在 spec 中写死为常量；必须通过 `tuner.param : !symbol.dim<"...">` 表达。
- P0 默认输出形态定义为：保留原 `func.func`，在函数体内引入显式 tile 循环 / 分段块 / 中间承接 memory。
- P0 默认跨边界值传递方式定义为：同一函数内的显式 SSA / out params / 中间 memory；禁止隐式重算或隐藏状态。
- P0 默认执行语义定义为：同一函数内基于 `tuner.param` 组织 tile 遍历，并串行执行各切分阶段；不在本轮引入并行调度语义。
- P0 默认触发方式不做自动代价模型决定；必须由公开合同指定的显式机制触发。
- P0 默认外部调优系统只负责给 `tuner.param` 赋值或搜索空间，不直接改写 pass 语义。
- P0 推荐 `KernelSplitPass` 作为“显式开启”的 pass，而不是直接塞进默认 lowering builder；原因是切分会改变函数体结构与 codegen 形态，必须由调用方或 pipeline 明确声明。

## 术语与默认定义

- `entry func`：切分前后的同一个 kernel 入口函数；P0 不允许生成新的 `func.func`。
- `tile stage`：切分后仍位于同一函数内、只处理单个 tile 或单个阶段工作集的代码片段。
- `tile axis`：参与切分的逻辑轴；P0 只允许切分单一主轴，不允许多轴联合切分。
- `tile param`：由 `tuner.param` 产生的 `!symbol.dim<"...">` 符号值，用于表示 tile 大小，不要求在 spec 层有具体整数。
- `carry memory`：在同一函数内跨阶段传递的中间 memory；若中间值不能稳定保留为 SSA，就必须显式物化为 memory。
- `split marker`：说明性占位概念，表示“该函数或该阶段需要切分”；正式写法由 `spec/pass/lowering/kernel_split.md` 冻结。

## 输入输出合同

### 输入 IR 合同

- 输入对象必须是已经过 `LowerNnToKernelPass -> BufferResultsToOutParamsPass` 的 `func.func`。
- 输入函数内的核心计算必须已 lower 为 `kernel.*` / `dma.*` / `func.*` 子集；P0 不接受仍残留 `nn.*` 的函数直接做 kernel split。
- 输入函数必须存在可识别的切分主轴；该主轴的 tile 大小只能来自 `tuner.param`。
- 输入函数的输出必须已是显式 out params 或合法标量返回；P0 不接受旧 `memory return` ABI。

### 输出 IR 合同

- 输出必须仍是单个合法 `func.func` 子集，且可继续进入 `gen_kernel(...)`。
- 输出必须包含：
  - 原入口函数。
  - 至少一个与 tile 因子相关的 `tuner.param`。
  - 显式 tile 遍历结构或等价分段结构。
- 输出不得包含：
  - 新增的 `func.func` / `func.call` 作为切分承接物。
  - 重新退回到 `nn.*` 的 op。
  - 未被消费的中间 carry memory。

## 详细示例

### 示例 A：单函数内单阶段 tile 切分

切分前伪 IR：

```text
func.func @vec_add_exp(
    %arg0: !nn.memory<[B, M], f32, #layout, #GM>,
    %arg1: !nn.memory<[B, M], f32, #layout, #GM>,
    %arg2: !nn.memory<[B, M], f32, #layout, #GM>) {
  %0 = kernel.add %arg0, %arg1 outs(%arg2)
  %1 = kernel.exp %arg2 outs(%arg2)
  func.return
}
```

切分后目标形态：

```text
func.func @vec_add_exp(
    %arg0: !nn.memory<[B, M], f32, #layout, #GM>,
    %arg1: !nn.memory<[B, M], f32, #layout, #GM>,
    %arg2: !nn.memory<[B, M], f32, #layout, #GM>) {
  %tile_m = tuner.param : !symbol.dim<"TILE_M">
  scf.for %i = %c0 to %M step %tile_m {
    %lhs = dma.slice %arg0[%i][%tile_m]
    %rhs = dma.slice %arg1[%i][%tile_m]
    %out = dma.slice %arg2[%i][%tile_m]
    %0 = kernel.add %lhs, %rhs outs(%out)
    %1 = kernel.exp %out outs(%out)
  }
  func.return
}
```

说明：

- 这个例子锁定“单函数内显式 tile 循环”的最小形态。
- `tuner.param` 只负责表达 tile 因子，不负责求值。
- 函数体内的循环形式可以是 `scf.for` 或等价合法 IR，但必须是“显式 tile 遍历”，不能偷写成实现内部隐式循环。

### 示例 B：单函数内两阶段切分并带 carry memory

切分前伪 IR：

```text
func.func @matmul_bias_relu(
    %a: !nn.memory<[M, K], f32, #layout, #GM>,
    %b: !nn.memory<[K, N], f32, #layout, #GM>,
    %bias: !nn.memory<[N], f32, #layout, #GM>,
    %out: !nn.memory<[M, N], f32, #layout, #GM>) {
  %0 = kernel.matmul %a, %b outs(%out)
  %1 = kernel.add %out, %bias outs(%out)
  %2 = kernel.max %out, %zero outs(%out)
  func.return
}
```

切分后目标形态：

```text
func.func @matmul_bias_relu(...) {
  %tile_m = tuner.param : !symbol.dim<"TILE_M">
  %carry = dma.alloc_dynamic_shape ...
  scf.for %i = %c0 to %M step %tile_m {
    %a_tile = dma.slice %a[%i, 0][%tile_m, %K]
    %out_tile = dma.slice %out[%i, 0][%tile_m, %N]
    %0 = kernel.matmul %a_tile, %b outs(%carry)
    %1 = kernel.add %carry, %bias outs(%carry)
    %2 = kernel.max %carry, %zero outs(%carry)
    dma.deslice %carry into %out[%i, 0][%tile_m, %N]
  }
  func.return
}
```

说明：

- 这个例子锁定“同一函数内跨阶段中间值必须显式承接”的规则。
- 若阶段间的中间结果无法稳定保留为 SSA，就必须物化为 carry memory。
- 这种物化必须在 spec 中写清是谁创建、谁消费、谁回收；不能留给实现自由发挥。

## 外部参考与取舍

- MLIR Transform Dialect 支持把迭代域拆成多个部分，并对各部分施加不同变换；这说明“先显式 split，再由后续步骤消费 split 结果”是可维护的公开合同。
- MLIR 的 tiling/transform 思路把“切分动作”和“后续调度/代码生成”分层，不建议在一个 pass 里同时塞入切分、代码生成和调优逻辑。
- TVM 的 `split` 与 `define_split` 把切分因子当作独立调优参数，而不是把 tile 常量烘焙进算子定义；这与当前仓库已有 `tuner.param` 的设计是相容的。
- 因此本计划选择：`kernel split pass` 只消费 `tuner.param` 表达的动态 tile 因子，不在 spec 中写死 `tile=32/64/...` 这类常量，也不把切分承接为新的函数。

## 示例

### 切分前

```python
def fused_kernel(a, b, out):
    tmp = add(a, b)
    tmp2 = exp(tmp)
    store(tmp2, out)
```

### 切分后目标形态

```python
def fused_kernel(a, b, out):
    tile_m = tuner_param("TILE_M")
    stage0_tmp = alloc(...)
    for tile_begin in range(0, m, tile_m):
        lhs = slice(a, tile_begin, tile_m, 1)
        rhs = slice(b, tile_begin, tile_m, 1)
        out_tile = slice(out, tile_begin, tile_m, 1)
        add(lhs, rhs, stage0_tmp)
        exp(stage0_tmp, stage0_tmp)
        deslice(stage0_tmp, out_tile)
```

- `tuner_param("TILE_M")` 是说明性写法；正式 IR 承接物必须是 `tuner.param : !symbol.dim<"TILE_M">`。
- 不生成新的函数；切分后仍然只有一个入口函数。
- 中间结果必须有显式承接物；不能依赖“实现阶段隐式重算”。

## S1

- `任务类型`：`spec任务`
- `目标`：在 `spec/pass/lowering/kernel_split.md` 新增 kernel split pass 的公开合同。
- `边界`：
  - 只定义“切分 kernel”，不定义 loop split、DMA hierarchy split。
  - 只定义 pass 的输入/输出 IR、`tuner.param` 到 tile 因子的桥接规则与失败边界，不定义具体算法实现细节。
  - 不要求自动选择切分点；P0 必须基于显式触发机制。
- `注意事项`：
  - 必须明确 pass 作用对象是“完成 `LowerNnToKernelPass -> BufferResultsToOutParamsPass` 之后的函数级 IR”。
  - 必须明确 tile 因子的唯一公开来源是 `tuner.param`；不得在该 spec 中把 tile size 写成固定整数。
  - 必须明确切分后仍保留单个原函数，不允许新增子函数承接 tile。
  - 必须明确中间值的物化规则：哪些值可直接保留为 SSA，哪些值必须物化为 memory。
  - 必须明确失败边界：缺少 split 触发、缺少必需的 `tuner.param`、tile 维度与目标轴不匹配、跨边界值不可物化、切分后结果不再满足 verifier 时，抛什么错误与关键短语。
- `依赖`：
  - 依赖现有 [`spec/dialect/tuner.md`](/home/lfr/kernelcode_generate/spec/dialect/tuner.md) 中 `tuner.param` 的公开合同，不新增新的 tuning op。
  - 依赖 `LowerNnToKernelPass -> BufferResultsToOutParamsPass` 先把 ABI 与 out params 形态收口。
- `可改文件`：
  - `spec/pass/lowering/kernel_split.md`
- `下游需要覆盖层`：
  - `pass`
  - `test/pass`
  - `expectation/pass`
- `示例代码`：

```python
from kernel_gen.passes.lowering.kernel_split import KernelSplitPass

pass_obj = KernelSplitPass()
module = pass_obj.run(module)
```

```text
%tile_m = tuner.param : !symbol.dim<"TILE_M">
scf.for %i = %c0 to %M step %tile_m {
  %lhs = dma.slice %arg0[%i][%tile_m]
  %rhs = dma.slice %arg1[%i][%tile_m]
  %out = dma.slice %arg2[%i][%tile_m]
  %0 = kernel.add %lhs, %rhs outs(%out)
}
```

```text
// 非法：缺少 tile param
scf.for %i = %c0 to %M step %c64 {
  %lhs = dma.slice %arg0[%i][%c64]
}
```
- `验证命令`：
  - `pytest -q test/pass/test_lowering_kernel_split.py`
- `验收标准`：
  - `test_kernel_split_pass_uses_tuner_param_tiles`: 输入为带 split 触发的 kernel 函数，输出必须出现 `tuner.param` 驱动的 tile 因子，不能把 tile size 直接固化为整数常量。
  - `test_kernel_split_pass_keeps_single_func_and_emits_split_body`: 输出必须保持单个入口函数，并在函数体内出现显式 split body / tile 循环。
  - `test_kernel_split_pass_rejects_missing_tuner_param`: 需要 tile 因子却缺少 `tuner.param` 时必须报错，错误关键字固定为 `KernelSplitMissingTileParam` 或等价冻结短语。
  - `test_kernel_split_pass_rejects_new_func_generation`: 若 pass 通过新增 `func.func` / `func.call` 承接 split，必须报错或判定不符合规范，错误关键字固定为 `KernelSplitUnexpectedFuncExtraction` 或等价冻结短语。
  - `test_kernel_split_pass_rejects_unmaterialized_intermediate`: 若切分后需要跨阶段传递的值既不是合法 SSA，也没有显式 memory 承接，必须报错，错误关键字固定为 `KernelSplitIntermediateMaterializationError` 或等价冻结短语。
  - `test_kernel_split_pass_rejects_non_lowered_nn_ops`: 若输入函数仍含 `nn.*`，必须报错，错误关键字固定为 `KernelSplitRequiresLoweredKernelIR` 或等价冻结短语。
  - `test_kernel_split_pass_rejects_dead_carry_memory`: 若切分生成了 carry memory 但后续 stage 或输出未消费，必须报错，错误关键字固定为 `KernelSplitDeadCarryMemory` 或等价冻结短语。

### S1 需要冻结的规格点

- `KernelSplitPass` 的正式名称。
- split 触发方式的公开写法。
- 单函数内 split body / tile loop 的公开结构写法。
- tile 主轴如何声明，是否允许负轴或多轴。
- `tuner.param` 命名规则，例如 `TILE_M` / `TILE_N` / `TILE_K`。
- `carry memory` 的创建与销毁职责。
- 失败边界属于哪一层报错：`build_func_op`、pass `run(module)`、还是 `gen_kernel(...)`。

## S2

- `任务类型`：`spec任务`
- `目标`：在 `spec/pass/pass_manager.md` 冻结 kernel split pass 在默认 lowering pipeline 中的位置与依赖顺序。
- `边界`：
  - 只定义 pass 顺序，不定义 pass 业务逻辑。
  - 不提前把后续 DMA hierarchy、analysis 或 codegen 细节写进 pass_manager 规范。
- `注意事项`：
  - 必须明确 `KernelSplitPass` 不能运行在 `BufferResultsToOutParamsPass` 之前，避免 ABI 与返回口径双重改写。
  - 若后续需要 DMA hierarchy pass，P0 推荐 `KernelSplitPass` 运行在其之前；这里要写成顺序约束，而不是实现建议。
  - 必须明确默认 lowering 链是否将该 pass 设为“默认开启”还是“显式开启”；两者只能选一个。
  - 必须明确 `KernelSplitPass` 依赖的 `tuner.param` 是“输入 IR 预先存在”还是“由 pass 在切分时插入”；P0 推荐由 pass 插入具名 `tuner.param`，避免调用方手工拼装。
  - 必须明确该 pass 只重写当前函数体，不得在 pipeline 中额外引入新的函数抽取阶段。
- `依赖`：
  - `S1` 合并。
- `可改文件`：
  - `spec/pass/pass_manager.md`
- `下游需要覆盖层`：
  - `pass`
  - `test/pass`
- `示例代码`：

```python
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.kernel_split import KernelSplitPass

pm = PassManager(name="split-lowering")
pm.add_pass(LowerNnToKernelPass())
pm.add_pass(BufferResultsToOutParamsPass())
pm.add_pass(KernelSplitPass())
module = pm.run(module)
```

```python
# 非法顺序示意
pm = PassManager(name="bad-order")
pm.add_pass(KernelSplitPass())
pm.add_pass(BufferResultsToOutParamsPass())
```
- `验证命令`：
  - `pytest -q test/pass/test_pass_manager.py`
- `验收标准`：
  - `test_default_lowering_pipeline_orders_kernel_split_after_out_params`: 默认或推荐 pipeline 中，`KernelSplitPass` 必须位于 `BufferResultsToOutParamsPass` 之后。
  - `test_kernel_split_pipeline_materializes_tuner_params_before_codegen`: `KernelSplitPass` 完成后，进入 codegen 前必须已经得到合法的 `tuner.param`-based tile 表达。
  - `test_kernel_split_pipeline_rejects_wrong_order`: 若显式构造错误顺序，必须报错或在规范中明确禁止，错误关键字固定为 `KernelSplitOrderError` 或等价冻结短语。
  - `test_kernel_split_pipeline_requires_explicit_enable`: 若 P0 选择“显式开启”，则默认 `build_default_lowering_pass_manager()` 不得自动插入 `KernelSplitPass`；测试必须机械验证这一点。
  - `test_kernel_split_pipeline_keeps_single_function_contract`: pipeline 说明必须明确 split 后仍是单函数合同，不得与其它 pass 组合成“自动抽取子函数”的效果。

### S2 需要冻结的顺序口径

- `KernelSplitPass` 是否进入默认 lowering builder。
- 若不进入默认 builder，推荐的公开构造入口叫什么。
- `KernelSplitPass` 与后续 `dma memory hierarchy`、`analysis`、`gen_kernel` 的先后约束。
- pipeline 中 `tuner.param` 的来源是在 split pass 内生成，还是在 split pass 前由其它 pass/前端生成。

## S3

- `任务类型`：`spec任务`
- `目标`：在 `spec/dsl/gen_kernel.md` 冻结 split 后单函数 IR 的代码生成合同。
- `边界`：
  - 只定义 `gen_kernel(...)` 对 split 后 IR 的黑盒输出合同，不定义 `emit_c` 的内部 helper 细节。
  - 不要求在本轮定义 host launch、多 stream、并行调度。
- `注意事项`：
  - 必须明确源码输出仍然是单个函数定义，不额外生成 tile helper 函数。
  - 必须明确函数体里是基于 `tuner.param` 对应的 tile 因子组织分块执行，而不是把 tile 大小烘焙成固定字面量。
  - 必须明确 split 后若 IR 缺失 `tuner.param` / 显式分块结构 / 中间承接对象时，`gen_kernel(...)` 如何失败，禁止静默 fallback 回未切分源码。
- `依赖`：
  - `S1` 合并。
  - `S2` 合并。
- `可改文件`：
  - `spec/dsl/gen_kernel.md`
- `下游需要覆盖层`：
  - `gen_kernel`
  - `test/dsl`
  - `expectation/dsl`
- `示例代码`：

```cpp
void vec_add_exp(
    const Memory<float>& arg0,
    const Memory<float>& arg1,
    Memory<float>& arg2) {
    long long tile_m = ctx.tuner_param("TILE_M");
    auto tmp = alloc(...);
    for (long long i = 0; i < M; i += tile_m) {
        auto lhs = slice(arg0, i, tile_m, 1);
        auto rhs = slice(arg1, i, tile_m, 1);
        auto out = slice(arg2, i, tile_m, 1);
        add(lhs, rhs, tmp);
        exp(tmp, tmp);
        deslice(tmp, out);
    }
}
```

```cpp
// 非法：tile 被硬编码，不再体现 tuner.param
for (long long i = 0; i < M; i += 64) {
    auto lhs = slice(arg0, i, 64, 1);
    auto rhs = slice(arg1, i, 64, 1);
    add(lhs, rhs, arg2);
}
```
- `验证命令`：
  - `pytest -q test/dsl/test_gen_kernel.py`
- `验收标准`：
  - `test_gen_kernel_emits_single_split_function`: 输入为 split 后 IR，输出源码必须保持单个函数定义，切分逻辑位于函数体内。
  - `test_gen_kernel_emits_tuner_backed_tile_exprs`: 输出源码中的 tile 相关表达必须来源于 `tuner.param` 对应的符号/变量，不得只出现固定 tile 整数字面量。
  - `test_gen_kernel_emits_in_function_split_sequence`: 源码必须显式表现分块遍历与阶段顺序，不得静默退化成未切分实现。
  - `test_gen_kernel_rejects_malformed_split_ir`: split IR 缺少必要组成时必须报错，错误关键字固定为 `KernelSplitMalformed` 或等价冻结短语。
  - `test_gen_kernel_rejects_unexpected_helper_function_extraction`: 若源码生成阶段试图把 split 结果额外抽成 helper 函数，必须报错或判定不符合规范，错误关键字固定为 `KernelSplitUnexpectedHelperFunction` 或等价冻结短语。

### S3 需要冻结的代码生成点

- 单函数签名保持规则。
- `tuner.param` 在目标源码中的映射形式。
- 函数体内循环或分块调度结构的公开形态。
- malformed split IR 的统一错误类型与短语。

## 风险与明确不做

- 本计划不把“算子融合”和“kernel 切分”混成同一 pass；输入若仍是高层 fusion/helper，必须先 lower。
- 本计划不要求一次支持所有 kernel；P0 可以只支持逐元素、简单 reduce 或结构稳定的 matmul 子集，但支持集必须在 `spec/pass/lowering/kernel_split.md` 明写。
- 本计划不要求 `tuner.param` 在当前阶段就拥有运行时取值接口；P0 只冻结 IR 合同与源码占位口径。
- 本计划不允许 silent fallback：无法切分时必须明确报错，不能静默退回原单 kernel 并假装成功。

## 完成定义

- `spec/pass/lowering/kernel_split.md` 已合并，并冻结：
  - pass 名称
  - 输入/输出 IR
  - 触发方式
  - `tuner.param` 到 tile 因子的桥接规则
  - 单函数内 split body 组织
  - 中间值承接规则
  - 失败边界与错误短语
- `spec/pass/pass_manager.md` 已合并，并冻结 kernel split 在 lowering pipeline 中的位置。
- `spec/dsl/gen_kernel.md` 已合并，并冻结 split 后 IR 的代码生成黑盒合同。
- 以上三项全部完成后，本计划才进入“可推进实现”的状态。
