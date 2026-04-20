时间：2026-04-21 00:20:00 +0800
经办人：金铲铲大作战
任务：T-20260421-3f4b68f2
任务目标：先修正 worktree 侧 `kernel_gen/tools/ircheck.py` 对 numeric SSA 的归一不足，恢复 `expectation.pass.buffer_results_to_out_params.single_output` 与目录入口的基础命中。
改动：更新 worktree 侧 `kernel_gen/tools/ircheck.py` 的 `_normalize_ir(...)`，去掉 numeric SSA `%0/%1` 的冒号后空格归一，只保留命名 SSA 与 `kernel.img2col1d` 的最小格式归一。
验证：`python3 -m expectation.pass.buffer_results_to_out_params.single_output`、`python3 -m expectation.pass.buffer_results_to_out_params`、`pytest -q test/tools/test_ircheck_runner.py test/tools/test_ircheck_matcher.py`、`pytest -q test/pass/test_buffer_results_to_out_params.py`、`pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py`
结论：build 已完成，按当前口径先续入审查链路，等待 review 复核是否真正收口。

时间：2026-04-21 00:23:00 +0800
经办人：提莫炖蘑菇
任务：T-20260421-3f4b68f2
任务目标：复核 build 结果，确认 `expectation.pass.buffer_results_to_out_params.single_output` 的 `CHECK-NEXT` 仍未和当前主线 `ModulePass` 输出对齐。
改动：未修改实现；仅复核黑盒失败点，发现 `func.func @copy(%0 : ...)` 与 expectation 仍写作 `func.func @copy(%0: ...)`，说明 numeric SSA 归一口径仍需继续收口。
验证：`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params.single_output`
结论：当前 build 仍需修复 `ircheck.py` numeric SSA 归一不足，待小李飞刀继续处理。

时间：2026-04-21 00:30:50 +0800
经办人：小李飞刀
任务：T-20260421-3f4b68f2
任务目标：回退主仓残留并继续修正 worktree 侧 `kernel_gen/tools/ircheck.py` 对 numeric SSA 的归一不足，恢复 `single_output` 与目录入口通过，并保持其余验收链路不回退。
改动：
- 已回退主仓根下误落的 `kernel_gen/tools/ircheck.py` 改动，并删除主仓根误落的任务记录文件，保证常规日志仍留在 worktree。
- worktree 侧 `kernel_gen/tools/ircheck.py` 仅对命名 SSA 保留 `name :` 兼容归一，不再把 numeric SSA `%0/%1` 改成 `%0 :`。
- worktree 侧 `test/tools/test_ircheck_runner.py` 新增 numeric SSA 签名回归用例，直接锁定 `func.func @copy(%0:` 的黑盒口径。
验证：
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check/kernel_gen/tools/ircheck.py /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check/test/tools/test_ircheck_runner.py`
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params.single_output`
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params`
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/tools/test_ircheck_runner.py -k 'numeric_ssa_signature_keeps_colon_tight or reg_alias_matches_ssa_ids or module_pass_ok'`
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/pass/test_buffer_results_to_out_params.py`
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && git diff --check`
结论：build 已完成，`single_output` 与目录入口已恢复通过，任务日志已写回对应 worktree；下一步按流程续接 `review`。

时间：2026-04-21 00:34:31 +0800
经办人：不要啊教练
任务：T-20260421-3f4b68f2
任务目标：复核 `expectation/pass/buffer_results_to_out_params/single_output.py` 的 CASE-1/CASE-2 与当前 worktree 侧 `ModulePass` 输出是否一致。
改动：未修改实现或测试；复核了 `single_output.py` 的静态/动态单输出两个 case，并对照 worktree 侧 `kernel_gen/tools/ircheck.py` 的实际输出，确认 `func.func @copy(%0: ...)`、`func.call @copy(%1, %0)` 与期望文本一致。
验证：
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params.single_output`
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params`
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate python3 - <<'PY' ... run_ircheck_text(...) ... PY`
- `cd /home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check && git diff --check`
结论：通过；CASE-1/CASE-2 与当前 worktree 的 `ModulePass` 输出一致，可以续接下一阶段。

时间：2026-04-21 00:36:25 +0800
经办人：李白
任务：T-20260421-3f4b68f2
任务目标：合并已通过复核的 buffer_results_to_out_params single_output CASE-1/CASE-2 与当前 worktree ModulePass 输出一致性修复结果
改动：接手实际存在的 merge 现场 `/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check`，收口 `kernel_gen/tools/ircheck.py` 的 numeric SSA 归一修正与 `test/tools/test_ircheck_runner.py` 的回归用例；本轮日志按任务约定写回同一记录文件
验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params.single_output` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/tools/test_ircheck_runner.py -k 'numeric_ssa_signature_keeps_colon_tight or reg_alias_matches_ssa_ids or module_pass_ok'` -> `3 passed, 37 deselected, 8 warnings`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/pass/test_buffer_results_to_out_params.py` -> `13 passed, 8 warnings`；`git diff --check` -> 通过
结论：已合并，待提交并执行 -done
