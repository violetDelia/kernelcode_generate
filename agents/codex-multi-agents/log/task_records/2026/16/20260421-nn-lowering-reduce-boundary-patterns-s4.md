时间：2026-04-21 21:31 +0800
经办人：金铲铲大作战
任务：T-20260421-6e366827 / nn_lowering_op_pattern S4
任务目标：收口 exp/reduce/softmax 边界 pattern，并完成 nn_lowering 全链路验收。
改动：
- 更新 `kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`：移除主 driver 中的 reduce/softmax family pattern，新增 `_LowerNnReduceSumPattern`、`_LowerNnReduceMinPattern`、`_LowerNnReduceMaxPattern` 与 `_RejectNnSoftmaxPattern`，全部通过具体 `Nn*Op` 类型和 `@op_type_rewrite_pattern` 命中；保留 `lower_reduce_softmax_family(...)` 兼容 helper，但改为按具体 Python 类型识别，避免主链路按 op 名称分派。
- 更新 `test/pass/nn_lowering/public_name.py`：注册顺序断言改为 reduce_sum/min/max 与 softmax 具体 pattern，并断言旧 `_LowerReduceSoftmaxFamilyPattern`、`_RejectSoftmaxPattern` 不再出现。
- 更新 `test/pass/nn_lowering/reduce_min.py`、`test/pass/nn_lowering/reduce_max.py`：将 pytest 文本证据中的 `kernel.reduce` 参数顺序同步为当前实现与根目录 expectation 一致的 `out, input`。
- 更新 `spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`：说明 reduce/softmax 主入口改为具体 pattern，`nn.exp` 由 select/cast/exp pattern 承接，兼容 helper 保留给旧调用点。
验证：
- `python3 -m py_compile kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/reduce_min.py test/pass/nn_lowering/reduce_max.py` -> 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4 pytest -q test/pass/nn_lowering/exp.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/reduce_min.py test/pass/nn_lowering/reduce_max.py test/pass/nn_lowering/public_name.py` -> `15 passed, 17 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering.exp` -> 通过，输出 CASE-exp-static / CASE-exp-dynamic。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering.reduce` -> 通过，输出 reduce_sum/min/max 静态与符号维度 CASE。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering` -> 通过，输出 nn_lowering 全目录 CASE。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4 pytest -q test/pass/nn_lowering` -> `42 passed, 60 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4 pytest -q test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py` -> `28 passed, 27 warnings`。
- `git diff --check` -> 通过，无输出。
结论：当前 build 已完成，S4 exp/reduce/softmax 边界 pattern 已按具体 op 类型收口，nn_lowering expectation 与 pytest 全链路验收通过；下一步按 TODO.md 创建 review 任务并通知管理员推进。

时间：2026-04-21 21:47 +0800
经办人：金铲铲大作战
任务：T-20260421-6e366827 / nn_lowering_op_pattern S4
任务目标：修复 nn_lowering S4 reduce keepdim=-1 仍被放行的问题并补齐负例验证。
改动：
- 收紧 `kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py` 中 `_ensure_reduce_keepdim(...)` 的取值范围，仅允许 `0/1`，不再接受 `-1`。
- 在 `test/pass/nn_lowering/test_lowering_nn_lowering.py` 新增 `test_reduce_min_rejects_keepdim_negative_one`，显式覆盖 `keepdim=-1` 的拒绝路径；保留既有非整数 `keepdim` 负例。
验证：
- `python3 -m py_compile kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py test/pass/nn_lowering/test_lowering_nn_lowering.py` -> 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4 pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'reduce_min_rejects_keepdim_negative_one or reduce_min_rejects_bad_keepdim or reduce_keepdim_validation'` -> `3 passed, 40 deselected`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4 pytest -q test/pass/nn_lowering` -> `43 passed, 62 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering.reduce` -> 通过。
结论：keepdim=-1 已不再被放行，负例验证已补齐；当前 build 继续保持通过，后续仍按 TODO.md 续接 review。

时间：2026-04-21 21:44
经办人：不要啊教练
任务：T-20260421-6e366827
任务目标：复核 S4 exp/reduce/softmax 边界 pattern 收口、pytest 与 expectation 全链路验证记录
改动：复核 `kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`、`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`、`test/pass/nn_lowering/public_name.py`、`test/pass/nn_lowering/reduce_min.py`、`test/pass/nn_lowering/reduce_max.py`；确认注册顺序、spec 说明、pytest 证据与 expectation 命令整体对齐，但 `_ensure_reduce_keepdim` 仍接受 `keepdim=-1`，与 spec/test 明确的 `0/1` 约束不一致。
验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/exp.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/reduce_min.py test/pass/nn_lowering/reduce_max.py test/pass/nn_lowering/public_name.py` -> `15 passed, 17 warnings`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering.exp` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering.reduce` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering` -> `42 passed, 60 warnings`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py` -> `28 passed, 27 warnings`；`git -C /home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4 diff --check` -> 通过；自定义最小复现：`keepdim=-1` 的 `NnReduceMinOp` 经 `NnLoweringPass().run(module)` 后未报错并继续 lower。
结论：需修改；建议转成独立 build 任务，收紧 `_ensure_reduce_keepdim` 对 `keepdim=-1` 的放行并补一条负例回归。

时间：2026-04-21 21:48
经办人：不要啊教练
任务：T-20260421-6e366827
任务目标：复核 nn_lowering S4 reduce keepdim=-1 修复与负例验证记录
改动：复核 `kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`，确认 `_ensure_reduce_keepdim(...)` 已收紧为仅接受 `0/1`；复核 `test/pass/nn_lowering/test_lowering_nn_lowering.py` 新增 `test_reduce_min_rejects_keepdim_negative_one`，负例覆盖已到位；`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`、`test/pass/nn_lowering/public_name.py`、`test/pass/nn_lowering/reduce_min.py`、`test/pass/nn_lowering/reduce_max.py` 与当前实现一致。
验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'reduce_min_rejects_keepdim_negative_one or reduce_min_rejects_bad_keepdim or reduce_keepdim_validation'` -> `3 passed, 40 deselected`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering` -> `43 passed, 62 warnings`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering.reduce` -> 通过；`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py /home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4/test/pass/nn_lowering/reduce_min.py /home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4/test/pass/nn_lowering/reduce_max.py` -> 通过；`git -C /home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4 diff --check` -> 通过。
结论：通过；当前修复与负例验证记录齐备，可进入 merge。

时间：2026-04-21 21:49 +0800
经办人：李白
任务：T-20260421-6e366827
任务目标：合并已通过复核的 nn_lowering S4 reduce keepdim=-1 修复与负例验证改动。
改动：合并前核对任务 worktree `/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-reduce-boundary-patterns-s4`，当前待纳入范围为 `kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`、`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`、`test/pass/nn_lowering/public_name.py`、`test/pass/nn_lowering/reduce_min.py`、`test/pass/nn_lowering/reduce_max.py`、`test/pass/nn_lowering/test_lowering_nn_lowering.py` 与当前任务记录文件。前一轮 review 已确认 `_ensure_reduce_keepdim(...)` 仅允许 `0/1`，新增 `test_reduce_min_rejects_keepdim_negative_one`，且 `spec`、pytest 与 expectation 一致。当前 worktree HEAD 为 `444e0bab5c9df995191b4f704de2c995452ad4b1`，本地 `origin/main` 为 `8fb4898d6eae034eda4a087e4b32b532a2d19939`，下一步先在该 worktree 执行 `timeout 60 git fetch origin`，再将改动重放到最新主线。
验证：
- `git status --short` -> 仅 6 个业务文件与当前任务记录文件待处理。
- `git diff --name-only` -> 命中上述 6 个业务文件。
- `git diff --stat` -> 6 个业务文件改动合计 178 行新增、56 行删除。
- `rg -n "T-20260421-6e366827|nn-lowering-reduce-boundary-patterns-s4|nn_lowering_op_pattern_refactor_green_plan" TODO.md DONE.md` -> 当前任务在 TODO 中为 merge 且指派李白。
结论：合并前记录已写入，下一步执行 `timeout 60 git fetch origin` 并按最新 `origin/main` 完成收口。

时间：2026-04-21 21:50 +0800
经办人：李白
任务：T-20260421-6e366827
任务目标：完成 nn_lowering S4 reduce keepdim=-1 修复与负例验证改动的 merge 同步确认。
改动：已在任务 worktree 执行 `timeout 60 git fetch origin`，并将当前提交重放到最新 `origin/main`。当前最终提交为 `129c9695ad8a47fd5c04fe27bd21250bccf31b5a`，父提交为 `8fb4898d6eae034eda4a087e4b32b532a2d19939`。本次合并保留 `_ensure_reduce_keepdim(...)` 仅允许 `0/1` 的修复、`test_reduce_min_rejects_keepdim_negative_one` 的负例回归，以及 `spec`、`public_name.py`、`reduce_min.py`、`reduce_max.py` 与实现的一致性。
验证：
- `git diff --check` -> 通过，无输出。
- `git status --short` -> 仅记录文件处于待提交状态，业务文件已纳入提交。
- `git rev-parse HEAD && git rev-parse origin/main` -> `129c9695ad8a47fd5c04fe27bd21250bccf31b5a` / `8fb4898d6eae034eda4a087e4b32b532a2d19939`。
结论：当前 merge 已完成，待把这次完成记录 amend 到同一次提交后执行 push、主仓同步、`-done` 与回报。
