# analysis_kernel_func_cost_refactor_plan.md

## 进度

- 更新日期：2026-03-31
- 更新规则：每个任务块进入新子阶段后立即更新本段。
- 当前状态：计划已进入“spec -> 实现/测试 -> 审查/复审 -> 合并”收口阶段；`S1/S2/S3` 审查均已发现主仓实现/测试与 spec 不一致，现已分别回退到修复链路；`I1` 的“已收口”判断需以主仓补齐 `func_cost` pass、pass_manager 测试映射与单一来源口径后再确认，不再按已完全封板处理。
- 现状盘点：
  - [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md) 已完成 `analyze_kernel(...)` 单函数公开契约冻结，对应 `S1` 已落盘；后续不应再按旧 `analyze_function(...)` 口径回退。
  - [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md) 已完成“AnalyzeFuncCostPass 与 analyze_kernel 共用单一公式来源”的冻结文本，对应 `S2` 已落盘。
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md) 已完成 `analysis/func_cost` 接入前置条件、查询口径与失败归因补充，对应 `S3` 已落盘。
- 当前外部阻塞：无。当前执行中：`S2` 实现修复（T-20260331-cc6f4c8b）、`S3` 二次实现修复（T-20260331-8bd7af21）。
- 当前建议推进顺序：优先收口 `S3` 的单一来源回退修复并立即进入复审；并行推进 `S2` 实现修复；待 `analysis.py/test_analysis.py/func_cost pass/test_pass_manager.py` 与计划口径统一后，再推进 `S2` 复审与后续合并链路。
- `S1`：spec 完成（T-20260331-a19cb7c0）；审查不通过（T-20260331-fe1b6bb0，主仓 `analysis.py/test_analysis.py` 仍有 legacy 链路，且缺少 `kernel_gen/passes/analysis/func_cost.py`）；实现完成（T-20260331-2f324e99）；复审通过（T-20260331-ee7f67ed）；当前待接续 `S2` 复审链路（T-20260331-a490d648，待实现完成后放行）。
- `S2`：spec 完成（T-20260331-84d12e5e）；审查不通过（T-20260331-55a67bcd，`func_cost` 仍未统一到 `analyze_kernel` 单一来源，`FuncCostSummary(op_costs/value_traffic)` 与 `args` 位次透传未闭环）；当前进入实现/测试修复链路（T-20260331-cc6f4c8b）。
- `S3`：spec 完成（T-20260331-8d3bc03b）；审查不通过（T-20260331-42f67fe2，`test_pass_manager.py` 缺少 TC-PASS-006~008，且 `analysis_kernel` 公开口径/value_traffic 未对齐）；实现/测试收敛完成（T-20260331-022e06d6）；复审通过（T-20260331-6c2f09ba）；合并前同步复审不通过（T-20260331-a668b955，`func_cost` 仍绕过 `analyze_function(...)` 走私有 `_analyze_func()`，缺少跨模块等价测试）；当前进入二次实现/测试修复链路（T-20260331-8bd7af21）。
- `I1`：实现完成（T-20260331-e5aa2ac1）；审查不通过（T-20260331-2ed46e6a，公开契约仍漂移回 `analyze_function`）；spec 修复完成（T-20260331-836e1c50）；实现/测试侧修复完成（T-20260331-53d17e66）；复审不通过（T-20260331-a1572cc8，缺少 `analyze_function` deprecated 兼容别名专测）；测试补强完成（T-20260331-bc8b13ba）；复审通过（T-20260331-a2f2a476）；合并完成（T-20260331-cd7ccec9，commit=440dbc8，fetch origin 成功，cleanup 已完成）；当前需结合 `S1` 回退结论重新确认主仓是否已完整具备 `func_cost` pass 闭环。

## 功能说明

- 本计划用于重构 [`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py) 对应的公开契约，并持续推进到实现、审查与合并闭环。
- 目标不是继续沿用旧的 `MemoryRef / Operation / analyze_function(...)` 模型，而是收敛为“输入 `func.func`，输出结构化分析摘要”的单函数分析模型。
- 目标产物是一份管理员可直接据此推进的计划书：先冻结边界，再允许实现与测试进入闭环。
- 文档中出现的 `analyze_kernel(...)` 为**目标接口名**，当前主仓未实现；管理员在分发时不得把它误认为现有可调用 API。

## 使用示例

- 管理员阅读本文件后，只按 `BLOCKER / READY_IF / DISPATCH_RULE / CLOSE_IF / FAIL_ROUTING` 决定是否放行对应 spec 任务。
- 执行者完成 spec 任务时，必须同时回报：修改文件列表、`rg` 验收命令、退出码，以及该 spec 绑定的测试函数名与预期输入/输出。
- 在 `S1` 未完成前，不得分发任何基于 `analyze_kernel(...)` 的实现任务。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/analysis_kernel_func_cost_refactor_plan.md`](../../ARCHITECTURE/plan/analysis_kernel_func_cost_refactor_plan.md)
- `spec`：
  - [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)
  - [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- `功能实现`：
  - [`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py)
  - [`kernel_gen/passes/analysis/func_cost.py`](../../kernel_gen/passes/analysis/func_cost.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- `test`：
  - [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
  - [`test/pass/test_analysis_func_cost.py`](../../test/pass/test_analysis_func_cost.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)

## 计划目标

- 将 analysis 公开入口统一为“单个 `func.func` 分析”，而不是旧的手工拼 `MemoryRef / Operation` 序列。
- 让 pass 层 `AnalyzeFuncCostPass` 成为同一分析模型的 module 级批处理适配器，而不是第二套公式来源。
- 明确“各个 memory / SSA 值的搬运量”是公开结果的一部分，不再只返回总量。
- 将未知 op 的处理统一为 `skip + warning`，把 fatal error 留给输入非法与统计前置条件不满足。

## 非目标

- 不在本计划中推进任何实现代码重写。
- 不在本计划中补 runtime、lowering、优化、缓存模型、并行模型或硬件性能模型。
- 不扩展为跨函数全局分析。
- 不把旧 `analyze_add / analyze_eq / analyze_matmul_op / analyze_function` 继续维持为主公开接口；它们若保留，只能作为 `legacy / deprecated` 说明存在。

## 当前真实断点

1. [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md) 仍以 `MemoryRef / Operation / AnalysisSummary / analyze_function(...)` 为主，和“输入 `func.func`、返回结构化摘要”的目标不一致。
2. [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py) 当前全部通过，但它验证的是旧模型，不足以证明新目标已闭环。
3. [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md) 与 [`test/pass/test_analysis_func_cost.py`](../../test/pass/test_analysis_func_cost.py) 已经表达了较新的方向，但主仓当前缺失 [`kernel_gen/passes/analysis/func_cost.py`](../../kernel_gen/passes/analysis/func_cost.py) 与 `kernel_gen/passes/analysis/__init__.py`，导致该链路当前是“契约存在、实现缺失”。
4. 现状下，`func_cost` 相关失败首先应归因为“实现缺失 / 契约未落地”，不能直接当成算法统计公式已错。

## 目标公开契约草案

### 目标入口

- 目标入口名：`analyze_kernel(func_op, args=None, *, predicate_size=1, dtype_size_overrides=None, attach_attrs=False)`
- 这里只是**目标契约名**，不是当前实现承诺。

### 目标输入边界

- `func_op`：只接受 `func.FuncOp`。
- `args`：仅用于补充函数参数位次上的运行时语义信息；必须按参数位次对齐，不允许按名字对齐。
- `predicate_size`：比较结果 `i1` 的写回字节优先来源。
- `dtype_size_overrides`：类型字节数覆盖表；若同时出现 `i1`，优先级低于 `predicate_size`。
- `attach_attrs`：若开启，允许把汇总结果回写到 `func.func` 属性，但这不改变返回摘要结构。

### 参数语义冻结

- `func_op`
  - 含义：被分析的单个 `func.FuncOp`。
  - 禁止输入：`ModuleOp`、Python callable、其它 wrapper。
- `args`
  - 含义：与 `func_op` 参数位次一一对齐的运行时语义补充信息。
  - 规则：`args[0]` 只对应 `%arg0`，`args[1]` 只对应 `%arg1`；不允许按参数名绑定。
  - 说明：示例中的 `runtime_a`、`runtime_b` 只是占位名字，不是计划额外引入的新公开类型名。
- `predicate_size`
  - 含义：比较结果 `i1` 的写回字节数。
  - 规则：若比较类 op 输出 `i1`，写流量必须优先按 `predicate_size` 统计。
- `dtype_size_overrides`
  - 含义：类型字节数覆盖表，例如 `{\"f32\": 4, \"i64\": 8}`。
  - 规则：仅在类型字节数推导阶段生效；对比较结果 `i1`，优先级低于 `predicate_size`。
- `attach_attrs`
  - 含义：是否把汇总统计附加到 `func.FuncOp.attributes`。
  - 规则：`False` 只返回摘要；`True` 允许附加属性，但不改变返回摘要结构。

### 目标输出结构

- 返回值：`summary` 结构体。
- 必须包含以下字段：
  - `func_name`
  - `op_costs`
  - `value_traffic`
  - `total_compute`
  - `total_read_bytes`
  - `total_write_bytes`
- `op_costs` 中每条记录至少包含：
  - `op_index`
  - `op_name`
  - `compute`
  - `read_bytes`
  - `write_bytes`
- `value_traffic` 中每条记录至少包含：
  - `value_key`
  - `read_bytes`
  - `write_bytes`
- `value_key` 稳定命名规则必须冻结：
  - 函数参数使用 `arg0`、`arg1`、`arg2` ...
  - 第 `i` 个被统计 op 的第 `j` 个结果使用 `op{i}.result{j}`

### 目标失败边界

- `func_op` 不是 `func.FuncOp`：抛 `AnalysisError`。
- `args` 不是 iterable：抛 `AnalysisError`。
- `args` 长度与函数参数位次不一致：抛 `AnalysisError`。
- 缺失必要类型信息、无法推导字节大小、或统计前置条件不满足：抛 `AnalysisError`。
- 未识别 op：`skip + warning`，不抛错，不计入总量。

## 管理执行规则

- 本计划以 spec 为起点，但管理员必须继续推进实现、审查与合并，不能停留在 spec 完成状态。
- 管理员可据此后续生成实现任务，但实现任务必须晚于 `S1`，且不得越过依赖顺序。
- 若执行者在 spec 冻结过程中试图新增别名入口、平行数据结构名或第二套分析公式，应直接退回。
- spec 任务的关闭条件以“文档命中 + 绑定测试函数定义完整”为准，不以代码是否已实现为准。

## 任务依赖

- `S1`：无前置，必须首先完成。
- `S2`：依赖 `S1`。
- `S3`：依赖 `S1`。
- `S2` 与 `S3`：在 `S1 DONE` 后可并行。
- 任意实现任务：依赖 `S2 DONE` 与 `S3 DONE`。

## 任务清单

### S1. 冻结单函数分析公开契约

- 目标文件：[`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)
- 目标：把该 spec 从旧的 `MemoryRef / Operation / analyze_function(...)` 模型重写为“输入 `func.FuncOp`、输出结构化摘要”的单函数分析契约。
- 边界：本任务只改一个 spec 文件，不改实现、不改测试。
- 不得做：
  - 不得把 `MemoryRef`、`Operation`、`AnalysisSummary` 继续写成主公开接口。
  - 不得把 `analyze_add / analyze_eq / analyze_matmul_op / analyze_function` 写成推荐入口。
  - 不得把 `args` 解释成按参数名绑定。
- 示例：

```python
summary = analyze_kernel(
    func_op,
    args=[runtime_a, runtime_b],
    predicate_size=2,
    dtype_size_overrides={"f32": 4, "i1": 8},
    attach_attrs=False,
)
```

- `BLOCKER`：none
- `READY_IF`：[`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md) 当前未被其他在途任务占用
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 文档完成条件：
  - spec 中必须出现唯一目标入口签名 `analyze_kernel(func_op, args=None, *, predicate_size=1, dtype_size_overrides=None, attach_attrs=False)`。
  - spec 中必须明确 `func_op` 只接受 `func.FuncOp`。
  - spec 中必须明确 `args` 仅按参数位次对齐。
  - spec 中必须明确 `unknown op -> skip + warning`。
  - spec 中必须明确 `predicate_size` 优先于 `dtype_size_overrides["i1"]`。
  - spec 中必须明确 `value_traffic` 的字段与稳定 `value_key` 命名规则。
  - spec 中必须把 `MemoryRef / Operation / analyze_function` 明确降为 `legacy / deprecated`。
- 下游必须绑定的测试函数：
  - `test_analyze_kernel_nn_add_symbolic_shape`
    - 输入：`func @main(%arg0: !nn.memory<[A,B],...,f32>, %arg1: !nn.memory<[A,B],...,f32>) -> !nn.memory<[A,B],...,f32>`，body 为 `nn.add(%arg0, %arg1)`。
    - 预期输出：`summary.func_name == "main"`；`summary.total_compute == A*B`；`summary.total_read_bytes == 2*A*B*4`；`summary.total_write_bytes == A*B*4`；`summary.op_costs[0].op_name == "nn.add"`。
  - `test_analyze_kernel_tensor_plus_const`
    - 输入：`func` 内部为 `nn.add(memory, const)`。
    - 预期输出：`summary.total_compute == A*B`；`summary.total_read_bytes == A*B*4`；常量不计读流量。
  - `test_analyze_kernel_chain_value_traffic`
    - 输入：`nn.add` 后接 `nn.mul` 的同函数链。
    - 预期输出：`summary.value_traffic` 至少包含 `arg0`、`arg1`、`arg2`、`op0.result0`、`op1.result0` 五条记录；其中 `op0.result0.write_bytes == A*B*4`，`op0.result0.read_bytes == A*B*4`。
  - `test_analyze_kernel_matmul_formula`
    - 输入：`lhs=[M,K]`、`rhs=[K,N]` 的 `nn.matmul`。
    - 预期输出：`summary.total_compute == 2*M*N*K`；`summary.total_read_bytes == (M*K + K*N)*4`；`summary.total_write_bytes == M*N*4`。
  - `test_analyze_kernel_dma_load_tracks_source_and_result`
    - 输入：包含一次 `dma.load` 的函数。
    - 预期输出：`summary.value_traffic` 同时记录源值读流量与结果值写流量；`summary.total_compute == 0`。
  - `test_analyze_kernel_rejects_non_func_input`
    - 输入：传入 `ModuleOp`。
    - 预期输出：抛 `AnalysisError`，消息包含 `func.FuncOp`。
  - `test_analyze_kernel_rejects_non_iterable_args`
    - 输入：`args=object()`。
    - 预期输出：抛 `AnalysisError`，消息包含 `args must be iterable`。
  - `test_analyze_kernel_rejects_args_length_mismatch`
    - 输入：两参数函数只给一个 `args` 元素。
    - 预期输出：抛 `AnalysisError`，消息包含 `args length mismatch`。
  - `test_analyze_kernel_unknown_op_warns_and_skips`
    - 输入：函数中混有一个未知 op 与一个 `nn.add`。
    - 预期输出：触发 `UserWarning`，消息包含未知 op 名；总量只统计 `nn.add`。
  - `test_analyze_kernel_compare_i1_uses_predicate_size`
    - 输入：`nn.eq` 输出 `i1`，`predicate_size=2`，`dtype_size_overrides={"i1": 8}`。
    - 预期输出：比较结果写回按 `2` 字节计，不按 `8` 字节计。
- 验收命令：

```bash
rg -n 'analyze_kernel\(func_op, args=None, \*, predicate_size=1, dtype_size_overrides=None, attach_attrs=False\)' spec/analysis/analysis_kernel.md -S
rg -n 'func\.FuncOp|按参数位次|skip \+ warning|predicate_size|value_traffic|arg0|op0\.result0|legacy|deprecated' spec/analysis/analysis_kernel.md -S
```

- `CLOSE_IF`：上述 2 条命令退出码均为 `0`
- `FAIL_ROUTING`：若 spec 仍存在双入口或旧模型仍是主接口，退回 `analysis_kernel spec`，不得放行 `S2/S3`

### S2. 冻结 func_cost pass 与 analyze_kernel 的单一公式来源

- 目标文件：[`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)
- 目标：把 `AnalyzeFuncCostPass` 明确为“module 级批处理适配器”，逐函数复用 `analyze_kernel(...)` 的同一套统计口径与返回结构，不再允许平行公式来源。
- 边界：本任务只改一个 spec 文件，不改实现、不改测试。
- 不得做：
  - 不得再定义第二套与 `analysis_kernel.md` 不一致的统计公式。
  - 不得把 `FuncCostSummary` 写成只保留总量、没有 `value_traffic` 的缩水结构。
  - 不得把未知 op 策略改回 fatal。
- 示例：

```python
pm = PassManager(name="analysis")
pass_obj = AnalyzeFuncCostPass(predicate_size=2, attach_attrs=True)
pm.add_pass(pass_obj)
module = pm.run(module)
summary = pass_obj.get_summary("main")
```

- `BLOCKER`：`S1`
- `READY_IF`：`S1 CLOSE_IF=true`
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 文档完成条件：
  - spec 中必须明确 `AnalyzeFuncCostPass` 对 module 内每个 `func.func` 调用与 `S1` 相同的分析模型。
  - spec 中必须明确 pass 查询结果与 `analyze_kernel(...)` 在同一函数上的字段一致：`func_name / op_costs / value_traffic / total_compute / total_read_bytes / total_write_bytes`。
  - spec 中必须明确未知 op 仍为 `skip + warning`。
  - spec 中必须明确 `attach_attrs=True` 只是附加属性，不改变摘要结构。
  - spec 中必须明确 `args` 若存在，也按参数位次传入下层分析。
- 下游必须绑定的测试函数：
  - `test_func_cost_nn_add_symbolic_shape`
    - 输入：含单个 `nn.add` 的 `ModuleOp`。
    - 预期输出：`summary.total_compute == A*B`；`summary.total_read_bytes == 2*A*B*4`；`summary.total_write_bytes == A*B*4`。
  - `test_func_cost_tensor_plus_const`
    - 输入：`nn.add(memory, const)`。
    - 预期输出：常量不计读流量；`summary.total_read_bytes == A*B*4`。
  - `test_func_cost_chain_accumulate`
    - 输入：单函数内两条逐元素 op。
    - 预期输出：`summary.total_compute`、`total_read_bytes`、`total_write_bytes` 为两 op 对应字段逐项求和。
  - `test_func_cost_matmul_formula`
    - 输入：`nn.matmul(lhs=[M,K], rhs=[K,N])`。
    - 预期输出：`summary.total_compute == 2*M*N*K`。
  - `test_func_cost_dma_memory_traffic`
    - 输入：包含 DMA op 的函数。
    - 预期输出：`summary.value_traffic` 中同时出现源值读流量和目标值写流量。
  - `test_func_cost_dma_sizes_smaller_than_shape`
    - 输入：DMA 的 size operand 小于源 memory 完整 shape。
    - 预期输出：`summary.total_read_bytes` 与 `summary.total_write_bytes` 按 size operand 计，不按 full shape 计。
  - `test_func_cost_skips_unknown_op_with_warning`
    - 输入：未知 op 与支持 op 混排。
    - 预期输出：触发 `UserWarning`；总量仅累加支持 op。
  - `test_func_cost_attach_attrs`
    - 输入：`attach_attrs=True`。
    - 预期输出：`func.attributes` 中至少出现 `analysis.compute`、`analysis.read_bytes`、`analysis.write_bytes`，且其字符串值等于摘要总量。
  - `test_func_cost_compare_i1_uses_predicate_size`
    - 输入：比较结果 `i1`，`predicate_size=2`。
    - 预期输出：比较结果写回按 `2` 字节计。
  - `test_func_cost_matches_analyze_kernel_on_same_func`
    - 输入：对同一个 `func.func` 同时执行 `analyze_kernel(...)` 与 `AnalyzeFuncCostPass`。
    - 预期输出：两者在 `op_costs` 长度、`value_traffic` 记录数、`total_compute`、`total_read_bytes`、`total_write_bytes` 上完全一致。
- 验收命令：

```bash
rg -n 'AnalyzeFuncCostPass|analyze_kernel|value_traffic|skip \+ warning|attach_attrs|analysis\.compute|analysis\.read_bytes|analysis\.write_bytes' spec/pass/analysis/func_cost.md -S
rg -n 'test_func_cost_matches_analyze_kernel_on_same_func|按参数位次' spec/pass/analysis/func_cost.md -S
```

- `CLOSE_IF`：上述 2 条命令退出码均为 `0`
- `FAIL_ROUTING`：若 `func_cost` 仍保留第二套统计口径或缺失 `value_traffic`，退回 `func_cost spec`，不得分发实现

### S3. 冻结 pass_manager 对分析 pass 的结果归属规则

- 目标文件：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- 目标：补充分析 pass 的通用规则，明确“分析结果保存在 pass 实例中，`PassManager.run(target)` 仍只返回 target，不额外返回 summary”。
- 边界：本任务只改一个 spec 文件，不改实现、不改测试。
- 不得做：
  - 不得把 `PassManager.run(...)` 改写成 tuple 返回。
  - 不得把“analysis 结果查询”定义成管理器的第二返回值。
  - 不得要求分析 pass 必须改写 IR 才算成功。
- 示例：

```python
pm = PassManager(name="analysis")
pass_obj = AnalyzeFuncCostPass()
pm.add_pass(pass_obj)
result = pm.run(module)
summary = pass_obj.get_summary("main")
assert result is module
```

- `BLOCKER`：`S1`
- `READY_IF`：`S1 CLOSE_IF=true`
- `DISPATCH_RULE`：`ONLY_IF READY_IF=true`
- 文档完成条件：
  - spec 中必须明确分析 pass 允许“返回原 target + 在实例内保存结果”。
  - spec 中必须明确 `PassManager.run(target)` 的公开返回值仍只有 target。
  - spec 中必须明确管理器不要求分析 pass 改写 IR。
  - spec 中必须明确分析结果查询是 pass 自身职责，而不是 `PassManager` 职责。
- 下游必须绑定的测试函数：
  - `test_pass_manager_allows_analysis_pass_returning_original_target`
    - 输入：一个只在实例内记录摘要、`run(target)` 返回原 target 的分析 pass。
    - 预期输出：`pm.run(obj) is obj`。
  - `test_pass_manager_analysis_result_queryable_from_pass_instance`
    - 输入：运行带分析结果缓存的 pass。
    - 预期输出：`pass_obj.get_summary("main")` 返回预设摘要对象；不需要从 `PassManager` 返回值取 summary。
  - `test_pass_manager_does_not_require_analysis_pass_to_rewrite_ir`
    - 输入：不改写 target 的分析 pass。
    - 预期输出：`pm.run(target)` 不抛错，且返回原 target。
- 验收命令：

```bash
rg -n 'analysis pass|实例内保存结果|run\(target\).*返回.*target|不要求.*改写 IR|get_summary' spec/pass/pass_manager.md -S
```

- `CLOSE_IF`：上述命令退出码为 `0`
- `FAIL_ROUTING`：若 spec 仍暗示 `run()` 需要第二返回值或 IR 改写，退回 `pass_manager spec`

## 管理员收口规则

- 只有在 `S1 DONE` 后，管理员才可放行 `S2`、`S3`。
- 只有在 `S2 DONE` 且 `S3 DONE` 后，管理员才可创建实现任务。
- 若后续实现阶段发现测试或实现想绕过 `S1` 的 `value_key` 命名规则、未知 op 策略、`predicate_size` 优先级或 `func.FuncOp` 输入边界，应先回滚到 spec 层修订，不得在实现层私自改口径。

## 当前建议的后续顺序

1. 先完成 `S1`，把单函数分析契约彻底收敛。
2. 在 `S1` 封板后并行推进 `S2` 与 `S3`。
3. 等 `S2/S3` 都封板后，再由管理员基于该 spec 生成实现任务，而不是现在直接改 [`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py)。
