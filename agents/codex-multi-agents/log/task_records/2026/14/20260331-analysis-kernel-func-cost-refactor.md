
时间：2026-03-31 20:25:18 +0800
任务：T-20260331-8bd7af21
任务目标：在 /home/lfr/kernelcode_generate/wt-20260331-analysis-s3 收口 AnalyzeFuncCostPass 与 analyze_function 的统计来源与 unknown-op 策略，补跨模块等价回归测试；仅实现+测试，不改 spec。
改动：
- 在 wt-20260331-analysis-s3/kernel_gen/analysis/analysis.py 为 Operation 增加 read_mask，并在 analyze_function 中支持读取该字段；_to_symbol/_size_symbol 改为基于 SymbolDim 生成符号，避免符号不一致。
- 在 wt-20260331-analysis-s3/kernel_gen/passes/analysis/func_cost.py 将 nn.* elementwise/broadcast/matmul 统计统一转发到 analysis.analyze_function，并新增桥接辅助函数以构造 analysis.Operation（含常量 operand read_mask=False）。未知 op 仍保持 warn+skip。
- 在 wt-20260331-analysis-s3/test/pass/test_analysis_func_cost.py 新增跨模块一致性回归：func_cost 汇总结果与 analyze_function 对齐；未知 op 跳过后仍保持一致。
- 在 wt-20260331-analysis-s3/test/analysis/test_analysis.py 更新符号断言与最近运行时间戳，适配 SymbolDim 符号生成。
验证：
- cd /home/lfr/kernelcode_generate/wt-20260331-analysis-s3 && PYTHONPATH=. pytest -q test/pass/test_analysis_func_cost.py（exit code=0，11 passed）
- cd /home/lfr/kernelcode_generate/wt-20260331-analysis-s3 && PYTHONPATH=. pytest -q test/analysis/test_analysis.py（exit code=0，17 passed）
备注：当前 worktree 中 spec/pass/pass_manager.md 与 test/pass/test_pass_manager.py 处于已修改状态，为既有改动，本任务未触碰。
结论：实现与测试已完成，func_cost 统计来源与 analyze_function 对齐，unknown-op 策略保持 warn+skip，无阻塞。建议进入审查。
