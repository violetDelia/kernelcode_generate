时间：2026-04-22 14:28 +0800
经办人：金铲铲大作战
任务：T-20260422-258f5c25
任务目标：修复 python_spec_impl_test_refactor_green_plan 最新主线终验失败的 expectation 资产与其公共运行依赖，收口 expectation.pass.tile.reduce 入口可执行性，并保持 expectation 仅作为合同验收资产单列，不替代对应测试
改动：新增 `expectation/utils/case_runner.py`，恢复 expectation case 的统一收集/汇总入口；新增 `expectation/pass/tile/_random_shared.py`，补回 tile-reduce expectation 共享的 dtype、space、memory IR 与固定 rank-3 静态/动态维度 helper；新增 `test/tools/test_expectation_case_runner.py`，覆盖 case runner 与 shared helper 的基础行为；保持 `expectation/pass/tile/reduce/fc.py` 与 `expectation/pass/tile/reduce/matmul.py` 的合同文本不变，仅恢复其运行依赖
验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate pytest -q test/tools/test_expectation_case_runner.py` -> `7 passed, 1 warning`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.reduce` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate python3 -m expectation` -> 通过；`git diff --check` -> 通过；`git diff --cached --check` -> 通过
Diff 反推自测：按实际 diff 反推覆盖了 `expectation/utils/case_runner.py`、`expectation/pass/tile/_random_shared.py` 与 `test/tools/test_expectation_case_runner.py`；`expectation` 仅作为合同验收资产单列，不纳入 diff 反推测试
合同验收（如适用）：`python3 -m expectation.pass.tile.reduce` 与 `python3 -m expectation` 均通过，作为本轮 expectation 合同验收资产单列
结论：build 已完成，expectation 入口与其共享运行依赖已恢复，可进入 review
时间：2026-04-22 14:32 +0800
经办人：提莫炖蘑菇
任务：T-20260422-258f5c25
任务目标：按实际 diff 复审 expectation 入口与共享运行依赖恢复结果
改动：复核 `expectation/utils/case_runner.py`、`expectation/pass/tile/_random_shared.py` 与 `test/tools/test_expectation_case_runner.py`；确认 `expectation.pass.tile.reduce` 依赖的 case runner / shared helper 已补齐，tile-reduce 的合同文本未被改坏，`python3 -m expectation.pass.tile.reduce` 与 `python3 -m expectation` 可在当前 worktree 正常启动
验证：`python3 -m pytest -q test/tools/test_expectation_case_runner.py` -> `7 passed, 1 warning`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.reduce` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate python3 -m expectation` -> 通过；`git diff --check` -> 通过；`git diff --cached --check` -> 通过
 Diff 反推审查：按实际 diff 复核了 `expectation/utils/case_runner.py`、`expectation/pass/tile/_random_shared.py` 与 `test/tools/test_expectation_case_runner.py`；`expectation` 仅作为合同验收资产单列，不替代对应测试
合同验收（如适用）：`python3 -m expectation.pass.tile.reduce` 与 `python3 -m expectation` 均通过，作为本轮 expectation 合同验收资产单列
结论：通过，expectation 入口与其共享运行依赖已恢复，tile-reduce 合同文本保持稳定，未发现新增阻断项

时间：2026-04-22 14:33 +0800
经办人：李白
任务：T-20260422-258f5c25
任务目标：按当前 worktree 完成 expectation 入口与共享运行依赖恢复结果的 merge 收口
改动：将 `expectation/utils/case_runner.py`、`expectation/pass/tile/_random_shared.py`、`test/tools/test_expectation_case_runner.py` 的 review 通过收口并入当前主线；`expectation` 入口与共享运行依赖保持可执行，tile-reduce 合同文本仍只作为合同资产单列
验证：`git diff --check` -> 通过；前序 build / review 已记录 `pytest` 与 `python3 -m expectation*` 结果并保持有效，本轮 merge 仅做主线同步收口
Diff 反推自测：merge 阶段未新增代码路径，仅延续当前 worktree 已完成的 diff 反推自测与 review 结论；`expectation` 仍仅作为合同验收资产单列，不纳入 diff 反推测试
Diff 反推审查：沿用 review 既有结论，确认当前 worktree 的改动已与最新主线完成同步收口
合同验收（如适用）：未单列 expectation 合同验收；本轮 merge 以 `git diff --check` 与既有 diff 反推结论为准
结论：merge 已完成，记录已补齐
复审时间：2026-04-22 14:41 +0800
复审经办人：不要啊教练
复审目标：按实际 diff 完成 Diff 反推审查，确认 expectation 仅作为合同验收资产单列，不替代对应测试
Diff 反推审查：重点核对 `expectation/utils/case_runner.py`、`expectation/pass/tile/_random_shared.py`、`test/tools/test_expectation_case_runner.py`、`expectation/pass/tile/reduce/__main__.py`、`expectation/pass/tile/__main__.py`；确认 `case_runner` 统一汇总入口与 tile-reduce 入口本身可运行，但新引入的 `expectation/pass/tile/_random_shared.py` 只补了 tile-reduce 所需常量，未兼容既有 tile-elewise 入口所需的 `ARITH_DTYPE` / `ARITH_DTYPE_IR`，导致 `python3 -m expectation.pass.tile` 与 `python3 -m expectation.pass.tile.elewise` 直接 ImportError，tile 家族目录入口仍未闭合
验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate pytest -q test/tools/test_expectation_case_runner.py` -> `7 passed, 1 warning`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.reduce` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate python3 -m expectation` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile` -> 失败，`ImportError: cannot import name 'ARITH_DTYPE' from 'expectation.pass.tile._random_shared'`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-final-expectation-repair-s8:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.elewise` -> 失败，失败原因同上；`git diff --check` -> 通过
合同验收（如适用）：`python3 -m expectation.pass.tile.reduce` 与 `python3 -m expectation` 仍通过，但 tile 家族目录入口本身未恢复，`expectation` 仅作为合同验收资产单列，不计入 Diff 反推测试
结论：需修改
