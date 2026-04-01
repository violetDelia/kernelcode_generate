时间：2026-04-02 03:57:18 +0800
任务：T-20260402-5ccd827b
任务目标：按 `ARCHITECTURE/plan/analysis_kernel_func_cost_refactor_plan.md` 的 `S2` 执行 spec 任务；仅修改 `spec/pass/analysis/func_cost.md`，冻结 `AnalyzeFuncCostPass` 的包装层合同，不改 `spec/analysis/analysis_kernel.md`、`spec/pass/pass_manager.md`、实现或测试。
改动：
- 核对任务前置：
  - `worktree=/home/lfr/kernelcode_generate/wt-20260402-analysis-kernel-s2` 可访问。
  - 当前无其他由我并行进行中的任务。
  - 已按要求向管理员同步当前进展：暂时无阻塞，继续仅按 `S2` 边界推进。
- 只读核对实现与测试：
  - `kernel_gen/passes/analysis/func_cost.py` 已明确 `AnalyzeFuncCostPass.run(module)` 逐函数调用 `analyze_kernel(...)`，并通过 `_to_func_cost_summary(...)` 适配 summary。
  - `test/pass/test_analysis_func_cost.py` 已落地 `test_func_cost_attach_attrs` 与 `test_func_cost_matches_analyze_kernel_on_same_func`，可作为本次包装层合同的机械映射基线。
结论：
- 任务进行中，当前无阻塞；下一步仅修改 `spec/pass/analysis/func_cost.md` 收口包装层合同。
时间：2026-04-02 04:22:25 +0800
任务：T-20260402-5ccd827b
任务目标：按 `S2` 边界完成 `AnalyzeFuncCostPass` 的包装层合同收口；仅修改 `spec/pass/analysis/func_cost.md`，不提前进入 `S3`、实现或测试修改。
改动：
- 更新 `spec/pass/analysis/func_cost.md`：
  - 在 `功能简介`、`目标`、`限制与边界` 中明确 `AnalyzeFuncCostPass` 只是 `analyze_kernel(...)` 的 pass 包装层，不维护第二套统计公式，统计口径、支持范围与 unknown-op 行为均沿用 [`spec/analysis/analysis_kernel.md`](../../../spec/analysis/analysis_kernel.md)。
  - 在 `统计口径` 中明确“同一个 `func.func` + 相同 `predicate_size/dtype_size_overrides/args`”下，`AnalyzeFuncCostPass.get_summary(func_name)` 的 `total_compute/total_read_bytes/total_write_bytes` 必须与 `analyze_kernel(func_op, ...)` 一致。
  - 在 `AnalyzeFuncCostPass`、`AnalyzeFuncCostPass.run(module)`、`AnalyzeFuncCostPass.get_summary(func_name)`、`AnalyzeFuncCostPass.all_summaries()` 的公开接口说明中写清：
    - `run(module)` 逐个 `func.func` 调用 `analyze_kernel(...)`；
    - `attach_attrs=True` 时，`func.func` 上可观察到 `analysis.compute`、`analysis.read_bytes`、`analysis.write_bytes`；
    - summary 查询来自 pass 实例缓存，而非第二返回值或第二套公式。
  - 在测试目标与功能用例清单中补齐包装层专属映射，显式覆盖：
    - `test_func_cost_attach_attrs`
    - `test_func_cost_matches_analyze_kernel_on_same_func`
  - 同步保留 `test_func_cost_skips_unknown_op_with_warning` 的 `func_cost skip ...` 可观察告警口径。
- 验证：
  - `rg -n "AnalyzeFuncCostPass|analyze_kernel|attach attrs|compute|read_bytes|write_bytes" spec/pass/analysis/func_cost.md`（exit 0）
  - `git -C /home/lfr/kernelcode_generate/wt-20260402-analysis-kernel-s2 diff --check -- spec/pass/analysis/func_cost.md`（exit 0）
结论：
- `完成`。
- 影响范围仅 `wt-20260402-analysis-kernel-s2/spec/pass/analysis/func_cost.md` 与当前链路记录文件；未修改 `spec/analysis/analysis_kernel.md`、`spec/pass/pass_manager.md`、实现或测试文件。
- 测试情况：本任务为 spec-only，未运行 `pytest`；已完成文档关键词校验与 diff 格式校验。
- 下一步建议：新建唯一后续任务，进入 `S2` 复审阶段，在同一 worktree 与记录文件中只读复核 `AnalyzeFuncCostPass` 的包装层合同是否与 `kernel_gen/passes/analysis/func_cost.py` 及 `test/pass/test_analysis_func_cost.py` 一致，再决定是否进入 `S3` 或后续实现链路。
时间：2026-04-02 04:27:18 +0800
任务：T-20260402-6a9996bf
任务目标：复审 `S2` spec；仅只读复核 `spec/pass/analysis/func_cost.md` 是否已将 `AnalyzeFuncCostPass` 收口为 `analyze_kernel(...)` 的包装层合同，并确认 `attach_attrs`、`func_cost skip` 告警、`test_func_cost_attach_attrs`、`test_func_cost_matches_analyze_kernel_on_same_func` 的映射与 `kernel_gen/passes/analysis/func_cost.py`、`test/pass/test_analysis_func_cost.py` 一致；不改 `S3`、实现或测试。
改动：
- 核对任务前置：
  - `worktree=/home/lfr/kernelcode_generate/wt-20260402-analysis-kernel-s2` 可访问。
  - 已用主仓任务表 `/home/lfr/kernelcode_generate/TODO.md` 执行 `-status -doing`，确认当前我名下仅 `T-20260402-6a9996bf` 在进行中。
  - 已按要求向管理员同步“已开始处理、当前无其他进行中任务、无阻塞”。
- 只读复核范围：
  - `wt-20260402-analysis-kernel-s2/spec/pass/analysis/func_cost.md`
  - `wt-20260402-analysis-kernel-s2/kernel_gen/passes/analysis/func_cost.py`
  - `wt-20260402-analysis-kernel-s2/test/pass/test_analysis_func_cost.py`
  - `ARCHITECTURE/plan/analysis_kernel_func_cost_refactor_plan.md`
  - 当前链路记录文件
- 复核要点：
  - `AnalyzeFuncCostPass` 是否明确写成逐函数调用 `analyze_kernel(...)` 的包装层，而非独立统计引擎。
  - `attach_attrs=True` 的 `analysis.compute/read_bytes/write_bytes` 回写口径是否与实现和测试一致。
  - unknown-op 是否通过重发主入口 warning 并统一为 `func_cost skip ...` 前缀暴露，而不是第二套告警策略。
  - `test_func_cost_attach_attrs` 与 `test_func_cost_matches_analyze_kernel_on_same_func` 是否在 spec 中有明确映射，且与实现/测试一致。
- 复核命令：
  - `rg -n "attach_attrs|func_cost skip|get_summary|all_summaries|analyze_kernel|test_func_cost_attach_attrs|test_func_cost_matches_analyze_kernel_on_same_func|warning" spec/pass/analysis/func_cost.md kernel_gen/passes/analysis/func_cost.py test/pass/test_analysis_func_cost.py`（exit 0）
  - `pytest -q test/pass/test_analysis_func_cost.py -k 'test_func_cost_attach_attrs or test_func_cost_matches_analyze_kernel_on_same_func or test_func_cost_skips_unknown_op_with_warning'`（exit 0，`3 passed, 7 deselected in 0.28s`）
  - `git -C /home/lfr/kernelcode_generate/wt-20260402-analysis-kernel-s2 diff --check -- spec/pass/analysis/func_cost.md`（exit 0）
- 复审结果：
  - `spec/pass/analysis/func_cost.md` 已将 `AnalyzeFuncCostPass` 明确收口为 `analyze_kernel(...)` 的包装层，统计口径、支持范围与 unknown-op 行为都回指主入口合同，没有再单独维护第二套公式。
  - `attach_attrs=True` 的 `analysis.compute`、`analysis.read_bytes`、`analysis.write_bytes` 在 spec、实现和 `test_func_cost_attach_attrs` 中一致。
  - `func_cost skip ...` 告警前缀在 spec、实现 `_rewrite_kernel_warning/_reemit_kernel_warnings`、以及 `test_func_cost_skips_unknown_op_with_warning` 中一致。
  - `test_func_cost_attach_attrs`、`test_func_cost_matches_analyze_kernel_on_same_func` 在 spec 的测试目标与用例表中都有明确映射，且与实现/测试行为一致。
  - 本次复审未发现必须修改项。
结论：
- `通过`。
- 复审结论：
  - `AnalyzeFuncCostPass` 已正确收口为 `analyze_kernel(...)` 的包装层合同。
  - `attach_attrs`、`func_cost skip` 告警与两个关键测试映射均与实现、测试一致。
  - 当前剩余风险主要是本次只重跑了 `S2` 关键测试子集，未覆盖 `test/pass/test_analysis_func_cost.py` 全量用例；但这不影响本轮 `S2` 复审结论。
- 下一步建议：新建唯一后续任务，进入 `S3 spec任务`，仅修改 `spec/pass/pass_manager.md`，冻结 `pass_manager` 对 analysis pass 的单返回路径合同，并沿用新的 `S3` worktree 与独立任务分发。
