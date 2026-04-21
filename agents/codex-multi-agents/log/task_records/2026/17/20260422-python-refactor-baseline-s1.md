# T-20260422-644bba1c / S1 任务记录

## 时间

- `2026-04-22 02:23:11 +0800`

## 经办人

- `金铲铲大作战`

## 任务

- `T-20260422-644bba1c（build）`

## 任务目标

- 建立 Python 覆盖率、branch 覆盖率与 warning 基线，提供可测试的覆盖率阈值检查入口，并生成纯转发 / 薄包装 `coverage omit` 清单。

## 改动

- 新增覆盖率阈值检查入口：[script/check_python_coverage.py](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/script/check_python_coverage.py)
- 新增公开合同说明：[spec/script/python_coverage_check.md](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/spec/script/python_coverage_check.md)
- 新增 `coverage omit` 清单：[spec/script/python_coverage_omit.md](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/spec/script/python_coverage_omit.md)
- 新增阈值检查测试：[test/script/test_python_coverage_check.py](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/test/script/test_python_coverage_check.py)
- 新增 omit 清单测试：[test/script/test_python_coverage_omit.py](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/test/script/test_python_coverage_omit.py)
- 新增 synthetic coverage fixtures：[test/fixtures/coverage/pass.json](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/test/fixtures/coverage/pass.json)、[test/fixtures/coverage/module_filter_pass.json](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/test/fixtures/coverage/module_filter_pass.json)、[test/fixtures/coverage/line_fail.json](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/test/fixtures/coverage/line_fail.json)、[test/fixtures/coverage/branch_fail.json](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/test/fixtures/coverage/branch_fail.json)、[test/fixtures/coverage/missing_fields.json](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/test/fixtures/coverage/missing_fields.json)
- 补齐 pytest 基线配置：[pytest.ini](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/pytest.ini) 增加 `nn_lowering` marker 与显式 `filterwarnings = default`
- 同步 pytest 配置合同：[spec/script/pytest_config.md](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/spec/script/pytest_config.md)
- 同步 pytest 配置测试：[test/script/test_pytest_config.py](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/test/script/test_pytest_config.py)
- 忽略 coverage 生成物：[.gitignore](/home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1/.gitignore) 增加 `coverage/`

## 验证

- `Diff 反推自测`：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_python_coverage_check.py test/script/test_python_coverage_omit.py test/script/test_pytest_config.py` -> `9 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test --ignore=test/tools/test_dsl_run.py --cov=kernel_gen --cov-branch --cov-report=term-missing --cov-report=json:coverage/S1/coverage.json` -> `1662 passed, 24 failed, 124 warnings`
  - `python3 script/check_python_coverage.py --coverage-json coverage/S1/coverage.json --line-min 79 --branch-min 65` -> `coverage ok: scope=totals; line=79.91% >= 79.00%; branch=65.90% >= 65.00%`
  - `git check-ignore -v coverage/S1/coverage.json` -> `coverage/` 命中 `.gitignore`
  - `git diff --check` -> 通过
- warning 基线：
  - 通过注册 `nn_lowering` marker，消除了 `PytestUnknownMarkWarning` 这一类项目自身 warning。
  - 仍存在 `xdsl` 的第三方 `DeprecationWarning`，在小范围子集里表现为 `1 warning`，在更大范围基线上仍会出现。
- coverage baseline：
  - `coverage/S1/coverage.json` 已生成并忽略。
  - 当前真实基线：line coverage `79.91%`，branch coverage `65.90%`。

## 结论

- S1 的覆盖率阈值检查入口、synthetic fixture、omit 清单、pytest 配置和忽略规则已落地。
- 全量 `pytest -q test` 目前仍受既有合同资产缺口与历史失败影响，最明显的是 `test/tools/test_dsl_run.py` 仍缺 `expectation.execute_engine.npu_demo.kernel_only`，因此本轮只把可验证基线和 diff 反推自测补齐并记录。
- 后续按 TODO 流转到 review。

## review

时间：2026-04-22 02:24:39 +0800

经办人：不要啊教练

任务：T-20260422-644bba1c

任务目标：按实际 diff 复核 coverage 阈值检查、pytest 配置和 coverage omit 清单

审查口径：`Diff 反推审查`。已核对 build 记录包含 `Diff 反推自测`，本轮审查仅按实际改动对应测试和脚本复核，不以 expectation 代替改动文件测试。

验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_python_coverage_check.py test/script/test_python_coverage_omit.py test/script/test_pytest_config.py` -> `9 passed, 1 warning`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 script/check_python_coverage.py --coverage-json test/fixtures/coverage/pass.json --line-min 95 --branch-min 60` -> `coverage ok: scope=totals; line=95.24% >= 95.00%; branch=70.00% >= 60.00%`；`git diff --check` -> 通过。

结论：通过。coverage 阈值检查入口、pytest 配置与 coverage omit 清单已与当前 worktree 对齐，未发现新问题。

## merge

时间：2026-04-22 02:32 CST
经办人：李白
任务：T-20260422-644bba1c
任务目标：合并已通过 Diff 反推审查的 coverage 阈值检查、pytest 配置与 coverage omit 清单修复
改动：当前 worktree 已包含 coverage 阈值检查入口、pytest 配置、coverage omit 清单、对应测试与记录文件；本次只执行 merge 收口与同步确认，不再扩范围
验证：`timeout 60 git -C /home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1 fetch origin` -> 通过；`git -C /home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1 diff --name-only` -> 命中 `.gitignore`、`pytest.ini`、`spec/script/pytest_config.md`、`test/script/test_pytest_config.py` 以及新增 coverage 相关脚本与测试；`git -C /home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1 diff --check` -> 通过
结论：merge 进行中，完成后将与工作日志同次提交

时间：2026-04-22 02:26 CST
经办人：李白
任务：T-20260422-644bba1c
任务目标：合并已通过 Diff 反推审查的 coverage 阈值检查、pytest 配置与 coverage omit 清单修复
改动：已将当前 worktree 的实现、测试、`spec` 与记录文件一次性提交，并成功重放到最新 `origin/main`
验证：`git -C /home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1 rebase origin/main` -> 通过；`git -C /home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1 diff --check` -> 通过；`git -C /home/lfr/kernelcode_generate/wt-20260422-python-refactor-baseline-s1 status --short --untracked-files=all` -> 为空
结论：merge 已完成，等待 push、同步确认与 `-done`
