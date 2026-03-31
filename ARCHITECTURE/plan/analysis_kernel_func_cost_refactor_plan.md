# analysis_kernel_func_cost_refactor_plan.md

## 进度
更新日期：2026-04-01
更新规则：每个任务块进入新子阶段后立即更新本段。

| 任务 | 依赖 | 记录文件 | worktree | 当前进度 |
| --- | --- | --- | --- | --- |
| S1 | 无 |  |  |  |
| S2 | S1 |  |  |  |
| S3 | S1 |  |  |  |
| I1 | — |  |  |  |

## 功能说明

- 本计划基于当前仓库实现重新拟定，用来收敛 `analysis` 主链的真实剩余工作，而不是继续把它当作“从零设计新接口”的规格计划。
- `## 进度` 段仅保留管理员后续填写入口；从本节开始的“当前实现复核”和“本轮收口顺序”才是本轮管理员分发的依据。
- 当前主线不是“缺 spec”，而是“`analyze_kernel(...)` 已进仓、`func_cost` pass 方向已写进测试与 spec，但链路仍有运行时回归和包路径缺口”。

## 使用示例

- 管理员先阅读“当前实现复核”，再按“本轮收口顺序”放行实现或测试收口任务。
- 若执行者回报 `PYTHONPATH=. pytest -q test/analysis/test_analysis.py -k 'test_analyze_kernel_chain_value_traffic or test_analyze_kernel_compare_i1_uses_predicate_size'` 仍报 `NameError: func not defined`，则说明主入口尚未恢复，不得提前关闭 analysis 主线。
- 若执行者回报 `PYTHONPATH=. pytest -q test/pass/test_analysis_func_cost.py -k 'test_func_cost_attach_attrs or test_func_cost_matches_analyze_kernel_on_same_func'` 仍在 collection 阶段报 `ModuleNotFoundError: No module named 'kernel_gen.passes.analysis'`，则说明 pass 包路径仍未补齐，不得把失败归因为统计公式错误。

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
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- `test`：
  - [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
  - [`test/pass/test_analysis_func_cost.py`](../../test/pass/test_analysis_func_cost.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)

## 当前实现复核

### 已落地

- [`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py) 已经包含 `analyze_kernel(...)`、`KernelOpCost`、`ValueTraffic`、`attach_attrs` 等新主线实现，不再是“目标接口名尚未落地”的状态。
- [`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py) 已经写入围绕 `value_traffic`、`predicate_size`、`unknown op -> skip + warning` 的新主线测试。
- `analyze_function(...)` 仍保留在实现中，当前仓库处于“兼容接口与主入口并存、尚未完成最终收口”的状态。

### 当前断点

1. `analyze_kernel(...)` 入口存在真实回归。实测命令：

```bash
PYTHONPATH=. pytest -q test/analysis/test_analysis.py -k 'test_analyze_kernel_chain_value_traffic or test_analyze_kernel_compare_i1_uses_predicate_size'
```

当前失败点是 `kernel_gen/analysis/analysis.py` 中 `func` 未定义，报错为 `NameError: func not defined`。

2. `AnalyzeFuncCostPass` 不是“公式未统一”，而是包路径尚未补齐。实测命令：

```bash
PYTHONPATH=. pytest -q test/pass/test_analysis_func_cost.py -k 'test_func_cost_attach_attrs or test_func_cost_matches_analyze_kernel_on_same_func'
```

当前在 collection 阶段直接失败，错误为 `ModuleNotFoundError: No module named 'kernel_gen.passes.analysis'`。

3. 因为 `func_cost` pass 包尚未建好，当前阶段不能把 pass 侧失败误判成“统计口径不一致”；现阶段首先是导入链与实现文件缺失。

### 计划基线

- 当前仓库已经具备可推进到最终目标的主入口、测试样例与规格骨架。
- 当前最需要的不是再起一轮接口命名讨论，而是让已存在的新入口和 pass 适配器真正可运行。

## 本轮计划目标

- 恢复 `analyze_kernel(...)` 的可执行状态，使新主线分析测试重新通过。
- 补齐 `kernel_gen.passes.analysis` 包路径和 `AnalyzeFuncCostPass` 实现落点，使 pass 侧测试至少能完成导入和执行。
- 在不删除兼容接口的前提下，把“主入口优先、兼容接口保留”的口径重新写清。

## 本轮非目标

- 不再发起第二轮公开接口重命名。
- 不在本轮扩展跨函数全局分析、缓存模型、并行模型或硬件性能模型。
- 不要求本轮移除 `analyze_function(...)`；兼容接口只需降为兼容路径，不作为新的实现阻塞项。

## 管理员执行口径

- 先修主入口，再修 pass；在 `analyze_kernel(...)` 仍报运行时错误时，不得提前关闭 analysis 主线。
- pass 侧以“能导入、能运行、结果复用 `analyze_kernel(...)`”为第一阶段收口标准，不接受单独造第二套统计公式。
- 若执行者试图为绕过现状新增平行分析入口、平行 summary 结构或第二套总量公式，应直接退回。

## 本轮收口顺序

1. 修复 [`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py) 中 `analyze_kernel(...)` 的运行时回归，并先恢复 `test/analysis` 新主线用例。
2. 新增 `kernel_gen/passes/analysis/` 包路径和 `func_cost.py` 落点，让 [`test/pass/test_analysis_func_cost.py`](../../test/pass/test_analysis_func_cost.py) 能完成导入、执行，并复用 `analyze_kernel(...)`。
3. 在实现闭环后，再回写 [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)、[`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md) 与 [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)，把“主入口优先、兼容接口保留”的现状写实。

## 本轮验收口径

- `analyze_kernel` 主入口恢复：

```bash
PYTHONPATH=. pytest -q test/analysis/test_analysis.py -k 'test_analyze_kernel_chain_value_traffic or test_analyze_kernel_compare_i1_uses_predicate_size'
```

预期：退出码为 `0`，且不再出现 `NameError: func not defined`。

- `func_cost` pass 包路径与主链复用恢复：

```bash
PYTHONPATH=. pytest -q test/pass/test_analysis_func_cost.py -k 'test_func_cost_attach_attrs or test_func_cost_matches_analyze_kernel_on_same_func'
```

预期：测试可正常 collection 并执行；若失败，也必须进入断言阶段，而不是停留在 `ModuleNotFoundError`。

- 口径重新写实：
  - [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md) 必须明确 `analyze_kernel(...)` 为当前主入口。
  - [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md) 必须明确 `AnalyzeFuncCostPass` 复用 `analyze_kernel(...)`。
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md) 必须明确分析结果归属 pass 实例，不新增 manager 第二返回值。

## 当前最直接的下一步

- 先修 [`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py) 中 `analyze_kernel(...)` 的 `func` 引用错误；这是当前整条 analysis 新主线最前面的硬阻塞。
