# analysis_kernel_func_cost_refactor_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `/wt-20260402-analysis-kernel-s1` | `20260402-analysis-kernel-s1.md` | `已建档（2026-04-02 02:55:41 +0800，T-20260402-87887b8d）；spec完成（2026-04-02 02:59:52 +0800，T-20260402-87887b8d，睡觉小分队）；审查完成（需修改，2026-04-02 03:06:15 +0800，T-20260402-f6e4e8b6，不要啊教练）；改进spec完成（2026-04-02 03:22:53 +0800，T-20260402-69de88d6，咯咯咯）；复审完成（需修改，2026-04-02 03:28:11 +0800，T-20260402-b7106bf1，不要啊教练）；再次改进spec完成（2026-04-02 03:32:46 +0800，T-20260402-74ae6ab7，jcc你莫辜负）；再次复审完成（需修改，2026-04-02 03:41:34 +0800，T-20260402-00d218b6，不要啊教练）；再次改进spec完成（2026-04-02 03:47:00 +0800，T-20260402-fc88f184，咯咯咯）；再次复审完成（2026-04-02 03:51:43 +0800，T-20260402-28f0cbce，咯咯咯）；已合并（2026-04-02 03:55:24 +0800，T-20260402-33823158，李白）` |
| `S2` | `S1` | `/wt-20260402-analysis-kernel-s2` | `20260402-analysis-kernel-s2.md` | `已建档（2026-04-02 03:57:18 +0800，T-20260402-5ccd827b）；spec完成（2026-04-02 04:23:07 +0800，T-20260402-5ccd827b，咯咯咯）；复审完成（2026-04-02 04:28:10 +0800，T-20260402-6a9996bf，jcc你莫辜负）；已合并（2026-04-02 05:20:53 +0800，T-20260402-46b41dce，李白）` |
| `S3` | `S1、S2` | `/wt-20260402-analysis-kernel-s3` | `20260402-analysis-kernel-s3.md` | `已建档（2026-04-02 05:25:21 +0800，T-20260402-420f45cf）；spec完成（2026-04-02 05:28:42 +0800，T-20260402-420f45cf，咯咯咯）；复审完成（2026-04-02 05:32:41 +0800，T-20260402-8172b532，提莫炖蘑菇）；已合并（2026-04-02 05:36:32 +0800，T-20260402-a4126551，李白）` |
| `I*` | `S1、S2、S3` |  |  | `当前无新增任务；已按计划书口径验收通过（2026-04-02，大闸蟹）。` |

## 功能说明

- 为 `analysis_kernel` / `func_cost` 主线提供当前可执行计划。
- 本计划只保留当前范围、单文件任务和机械验收口径。

## 使用示例

- 管理员先阅读“目标终态”，确认执行者知道主入口、pass 包装层和 pass manager 的职责边界。
- 再按 `S1 -> S2 -> S3` 顺序分发任务；每个任务只改一个 `md` 文件。
- 相关文档约定明确后，再按“`analysis -> pass/analysis -> pass_manager -> 审查/复审/合并`”顺序推进实现链路。

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

## 当前范围

- 只收口 `analyze_kernel(...)` 主入口、`AnalyzeFuncCostPass` 包装层与 `pass_manager` 的交接边界。
- 只收口当前测试里已经出现的行为：
  - `value_traffic`
  - `compare i1` 的 `predicate size`
  - `unknown op -> skip + warning`
  - pass attach attrs
  - pass 复用主入口而不是维护第二套公式
- 不在本轮收口：
  - 跨函数全局分析
  - 新的硬件性能模型
  - 第二套 summary 结构
  - `pass_manager.run(...)` 的多返回值协议

## 目标终态

- `analyze_kernel(...)` 是公开主入口。
- `AnalyzeFuncCostPass` 只是 `analyze_kernel(...)` 的 pass 包装层，不维护第二套统计公式。
- `pass_manager` 继续使用单一返回路径；分析结果通过 pass 实例、func attrs 或 module 内可观测状态承接，而不是 manager 额外返回第二个对象。

## 计划任务

### `S1`

- `任务类型`：`实现 analyze_kernel 主入口说明功能`
- `目标`：在 [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md) 明确 `analyze_kernel(...)` 的主入口合同。
- `任务示例`：
  - `S1 任务：仅修改 spec/analysis/analysis_kernel.md，把 analyze_kernel(func_op) 写成当前唯一主入口。`
  - `文档里应给出接近以下示例：summary = analyze_kernel(func_op)；summary.op_costs[0].op_name == "nn.add"；unknown op 只产生 warning，不中止分析。`
  - `文档里不得把 analyze_function(...) 重新写成与 analyze_kernel(...) 并列的长期主入口。`
- `边界`：
  - 只改 [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)
  - 不改 [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)
  - 不改 [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - 不改实现、测试
- `注意事项`：
  - 必须写清主入口签名和输入对象类型
  - 必须写清 `unknown op -> skip + warning`
  - 必须写清 `compare i1` 的统计口径
  - 不能把 `analyze_function(...)` 重新写成长期并列主入口
- `依赖`：`无`
- `可改文件`：[`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)
- `下游需要覆盖层`：
  - `analysis`
  - `pass/analysis`
  - `pass_manager`
- `验证命令`：
  - `rg -n "analyze_kernel|unknown op|warning|predicate size|value_traffic" spec/analysis/analysis_kernel.md`
- `验收标准`：
  - `test_analyze_kernel_chain_value_traffic`：输入包含链式 `nn.add` 的 `func.func`；预期 `value_traffic` 与链式中间值读写统计可机械判断一致。
  - `test_analyze_kernel_compare_i1_uses_predicate_size`：输入包含比较 op；预期 `i1` 结果按 predicate size 计入。
  - `test_analyze_kernel_skips_unknown_op_with_warning`：输入包含未知 op；预期分析继续完成，且 warning 中包含 unknown op 信息。

### `S2`

- `任务类型`：`实现 AnalyzeFuncCostPass 包装层说明功能`
- `目标`：在 [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md) 明确 `AnalyzeFuncCostPass` 的包装层合同。
- `任务示例`：
  - `S2 任务：仅修改 spec/pass/analysis/func_cost.md，把 AnalyzeFuncCostPass 写成 analyze_kernel(...) 的 pass 包装层。`
  - `文档里应给出接近以下示例：同一个 func_op 先 analyze_kernel(func_op)，再跑 AnalyzeFuncCostPass，二者 compute/read_bytes/write_bytes 必须一致。`
  - `文档里不得写“pass 内部维护独立公式”“pass 与主入口统计口径可独立演进”。`
- `边界`：
  - 只改 [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)
  - 不改 [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)
  - 不改 [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - 不改实现、测试
- `注意事项`：
  - 必须明确 `AnalyzeFuncCostPass` 复用 `analyze_kernel(...)`
  - 必须明确 attach attrs 的可观察结果
  - 不能写成“pass 维护第二套统计公式”
- `依赖`：`S1 已完成`
- `可改文件`：[`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)
- `下游需要覆盖层`：
  - `pass/analysis`
  - `pass_manager`
- `验证命令`：
  - `rg -n "AnalyzeFuncCostPass|analyze_kernel|attach attrs|compute|read_bytes|write_bytes" spec/pass/analysis/func_cost.md`
- `验收标准`：
  - `test_func_cost_attach_attrs`：输入单个 `func.func`；预期 pass 运行后目标 attrs 存在且值可机械判断。
  - `test_func_cost_matches_analyze_kernel_on_same_func`：输入同一个 `func.func`；预期 pass 与 `analyze_kernel(...)` 的总量口径一致。

### `S3`

- `任务类型`：`实现 pass_manager 单返回路径说明功能`
- `目标`：在 [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md) 明确 `pass_manager` 对分析 pass 的单返回路径合同。
- `任务示例`：
  - `S3 任务：仅修改 spec/pass/pass_manager.md，把分析 pass 在 manager 中的承接方式写清。`
  - `文档里应明确：run(module) 仍返回单一 module；分析结果通过 pass/attrs 可观察。`
  - `文档里不得出现 new_module, summary = pass_manager.run(module) 这类双返回示例。`
- `边界`：
  - 只改 [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - 不改 [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)
  - 不改 [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)
  - 不改实现、测试
- `注意事项`：
  - 必须明确 `run(...)` 仍是单返回路径
  - 必须明确分析结果不经由 manager 第二返回值传出
  - 不能写成“manager 自动汇总所有分析结果并额外返回”
- `依赖`：`S1、S2 已完成`
- `可改文件`：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- `下游需要覆盖层`：
  - `pass_manager`
- `验证命令`：
  - `rg -n "run\\(|single return|analysis result|pass instance|attrs" spec/pass/pass_manager.md`
- `验收标准`：
  - `test_pass_manager_runs_analysis_pass_without_second_return`：输入包含分析 pass 的 manager；预期 `run(...)` 保持单返回路径。
  - `test_pass_manager_preserves_analysis_side_effects`：输入同上；预期分析结果通过 pass/attrs 可观察，而不是 manager 第二返回值。

## 推荐收口顺序

1. 先完成 [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md) 的文档收口。
2. 再完成 [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md) 的文档收口。
3. 再完成 [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md) 的文档收口。
4. 然后实现 [`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py) 与 `test/analysis/test_analysis.py`。
5. 再实现 `pass/analysis` 包装层与 `test/pass/test_analysis_func_cost.py`。
6. 最后补 `test/pass/test_pass_manager.py`、审查、复审与合并。

## 统一验收口径

### 主入口 gate

- `pytest -q test/analysis/test_analysis.py -k 'test_analyze_kernel_chain_value_traffic or test_analyze_kernel_compare_i1_uses_predicate_size'`
- 预期：退出码为 `0`，且不再出现主入口运行时错误。

### pass gate

- `pytest -q test/pass/test_analysis_func_cost.py -k 'test_func_cost_attach_attrs or test_func_cost_matches_analyze_kernel_on_same_func'`
- 预期：退出码为 `0`，且不再停留在导入失败阶段。

### manager gate

- `pytest -q test/pass/test_pass_manager.py`
- 预期：退出码为 `0`，且不要求 manager 额外返回第二个 summary 对象。

### 不得写成终态的内容

- `analyze_function(...)` 与 `analyze_kernel(...)` 长期双主入口。
- `AnalyzeFuncCostPass` 独立统计一套新公式。
- `pass_manager.run(...) -> (module, summary)`。

## 当前验收结论

- 通过。
- 代表性命令：
  - `pytest -q test/analysis/test_analysis.py -k 'test_analyze_kernel_chain_value_traffic or test_analyze_kernel_compare_i1_uses_predicate_size'`
  - `pytest -q test/pass/test_analysis_func_cost.py -k 'test_func_cost_attach_attrs or test_func_cost_matches_analyze_kernel_on_same_func'`
  - `pytest -q test/pass/test_pass_manager.py`
- 当前判断：本轮计划要求的主入口、pass 包装层和 manager 单返回路径已经达到计划终态。

## 建议新增任务

- 当前无新增任务。
- 若后续要继续推进，只建议另立新计划，不在本计划下追加实现链。

## 当前最直接的下一步

- 当前无下一步；本轮计划已可视为验收通过。
