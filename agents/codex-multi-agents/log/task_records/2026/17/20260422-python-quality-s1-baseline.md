# T-20260422-854cafe4 / S1 任务记录

## 时间

- `2026-04-22 22:52:07 +0800`

## 经办人

- `金铲铲大作战`

## 任务

- `T-20260422-854cafe4（build）`

## 执行前阅读记录

- 已阅读 `TODO.md` 中 `T-20260422-854cafe4` 任务行，确认本轮 worktree 为 [`wt-20260422-python-quality-s1-baseline`](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline)。
- 已阅读 [`ARCHITECTURE/plan/python_quality_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/python_quality_refactor_green_plan.md) 的 S1 正文、完成态定义与验收设计，确认本阶段只建立 Python 覆盖率 / warning 基线、spec/test/实现/expectation 依赖基线和 coverage 门禁，不做批量业务重构。
- 已复核上一轮同类 S1 记录 [`20260422-python-refactor-baseline-s1.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260422-python-refactor-baseline-s1.md)，沿用“真实自检 + Diff 反推自测 + coverage baseline + 依赖清单”的记录结构。

## 任务目标

- 建立 Python 覆盖率、branch 覆盖率与 warning 基线，提供可测试的覆盖率阈值检查入口，并生成纯转发 / 薄包装 `coverage omit` 清单。

## 改动

- 新增公共 case 汇总 helper：[kernel_gen/tools/case_runner.py](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/kernel_gen/tools/case_runner.py)
- 公开 `case_runner` 到工具包根：[kernel_gen/tools/__init__.py](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/kernel_gen/tools/__init__.py)
- 新增公开合同说明：[spec/tools/case_runner.md](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/spec/tools/case_runner.md)
- 新增产品侧测试：[test/tools/test_case_runner.py](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/tools/test_case_runner.py)
- 移除旧的 expectation 产品测试入口：[test/tools/test_expectation_case_runner.py](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/tools/test_expectation_case_runner.py)
- 新增 synthetic coverage fixtures：[test/fixtures/coverage/pass.json](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/fixtures/coverage/pass.json)、[test/fixtures/coverage/module_filter_pass.json](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/fixtures/coverage/module_filter_pass.json)、[test/fixtures/coverage/line_fail.json](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/fixtures/coverage/line_fail.json)、[test/fixtures/coverage/branch_fail.json](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/fixtures/coverage/branch_fail.json)、[test/fixtures/coverage/missing_fields.json](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/fixtures/coverage/missing_fields.json)
- 继续沿用并验证覆盖率检查入口：[script/check_python_coverage.py](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/script/check_python_coverage.py)

## 代码质量检查矩阵自检

- API 一致性：`run_case(...)` 与 `raise_if_failures(...)` 只提供稳定、单职责的工具层接口；未引入 expectation 路径或额外分支。
- 边界：`case_name` 为空与 `case_fn` 非 callable 时显式报错；失败列表为空与非空的分支都覆盖到。
- 错误模型：异常汇总格式稳定，case 名称、异常类型和异常消息都保留；没有把普通异常吞掉。
- 模块边界：`kernel_gen.tools.case_runner` 只依赖标准库，不反向依赖 `test/` 或 expectation。
- 依赖方向：产品 `test/` 不再直接 import expectation；旧的 expectation 入口测试已从产品测试树剥离。
- 复用：`run_case(...)` / `raise_if_failures(...)` 作为通用 helper，可被后续 case 驱动测试复用。
- 函数粒度：两个 helper 仍保持最小职责，不再继续拆成无意义小函数。
- 可读性：新 helper 与测试文件均补齐中文功能说明、使用示例与关联链接。
- 注释示例：`spec/tools/case_runner.md` 与 `kernel_gen/tools/case_runner.py` 均补了可执行示例。
- 兼容债：`test/tools/test_expectation_case_runner.py` 作为 expectation 依赖残留已删除，避免继续把 expectation 写进产品测试树。
- 测试质量：新增测试直接断言工具行为与失败消息，不依赖 expectation 合同资产替代产品测试。
- 可演进性：`case_runner` 已迁入 `kernel_gen.tools`，可供后续 `ircheck` / `dsl_run` / case 化测试进一步复用。

## Diff 反推自测

- `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/tools/test_case_runner.py /home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/script/test_python_coverage_check.py /home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/test/script/test_python_coverage_omit.py` -> `12 passed, 1 warning`
- `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q test` -> `1736 passed, 95 warnings`
- `coverage erase`
- `coverage run --branch --source=kernel_gen -m pytest -q test`
- `coverage json -o coverage/S1/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S1/coverage.json --line-min 79 --branch-min 65` -> `coverage ok: scope=totals; line=81.07% >= 79.00%; branch=67.18% >= 65.00%`
- `git check-ignore -v coverage/S1/coverage.json` -> `coverage/` 命中 `.gitignore`
- `git diff --check` -> 通过

## baseline / 审计结果

- coverage baseline 已生成：[`coverage/S1/coverage.json`](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/coverage/S1/coverage.json)
- 当前 baseline：line coverage `81.07%`，branch coverage `67.18%`
- warning baseline：本轮全量 pytest 仍存在第三方 / 现有实现 deprecation warnings，共 `95` 条；未再出现产品自身的 `PytestUnknownMarkWarning`

## 依赖与重复候选

- expectation 依赖候选：`test/tools/test_expectation_case_runner.py` 已从产品测试树剥离；`kernel_gen` / `test` / `script` 中不再存在 expectation import。
- 仍需后续收口的 `kernel_gen` expectation 兼容 / 文档候选：[`kernel_gen/tools/ircheck.py`](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/kernel_gen/tools/ircheck.py)、[`kernel_gen/tools/dsl_run.py`](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/kernel_gen/tools/dsl_run.py)、[`kernel_gen/dsl/mlir_gen/emit/__init__.py`](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/kernel_gen/dsl/mlir_gen/emit/__init__.py)、[`kernel_gen/passes/lowering/tile_analysis.py`](/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline/kernel_gen/passes/lowering/tile_analysis.py)
- 重复测试候选：`test/pass/nn_lowering/reduce_{sum,min,max}.py`、`test/dialect/test_nn_dialect.py` vs `test/operation/test_operation_nn_{broadcast,structured,reduction}.py`、`test/pass/test_pass_manager.py` 中重复的 symbol_loop_hoist 断言、`test/dsl/test_emit_mlir.py` vs `test/dsl/test_ast_visitor.py` 中重复的 matmul / broadcast lowering 断言
- `expectation/tools` 可迁移能力清单：case 收集与失败汇总已迁入 `kernel_gen.tools.case_runner`；`ircheck`、`mlir_gen_compare`、`dsl_run` 的稳定公开行为仍可继续分拆成 `kernel_gen.tools` / `test.tools` 的更薄 helper

## 结论

- S1 基线已建立：coverage / branch baseline、warning baseline、coverage fixture、coverage checker fixture、omit 清单口径、expectation 依赖清单和重复测试候选均已记录。
- 产品测试树已清理掉 expectation 直接依赖，`pytest -q test` 通过。
- `kernel_gen` 中仍存在少量 expectation 兼容 / 文档痕迹，已作为后续阶段候选项单列，不在本轮继续扩范围。
- 按 TODO.md 继续流转到 review。

## review

时间：2026-04-22 22:57 +0800

经办人：提莫炖蘑菇

任务：T-20260422-854cafe4

任务目标：复核本轮质量基线与 case runner 迁移收口结果

改动：按实际 diff 复核 `kernel_gen/tools/__init__.py`、`kernel_gen/tools/case_runner.py`、`spec/tools/case_runner.md`、`test/tools/test_case_runner.py` 与删除的 `test/tools/test_expectation_case_runner.py`；确认产品测试树已从 expectation 依赖迁出，`kernel_gen.tools.case_runner` 已成为可复用公开 helper，`spec/test/实现` 三者链路对齐

验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline:/home/lfr/kernelcode_generate python3 -m pytest -q test/tools/test_case_runner.py test/tools/test_dsl_run.py` -> `24 passed, 13 warnings`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.analysis` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline:/home/lfr/kernelcode_generate python3 -m expectation` -> 通过；`git diff --check` -> 通过；`git diff --cached --check` -> 通过

Diff 反推审查：被审 diff 为 `kernel_gen/tools/__init__.py`、`kernel_gen/tools/case_runner.py`、`spec/tools/case_runner.md`、`test/tools/test_case_runner.py`，并确认 `test/tools/test_expectation_case_runner.py` 已删除；复跑的实际命令为 `pytest -q test/tools/test_case_runner.py test/tools/test_dsl_run.py`、`python3 -m expectation.pass.tile.analysis`、`python3 -m expectation.pass.tile`、`python3 -m expectation`、`git diff --check`、`git diff --cached --check`；`rg -n "from expectation|import expectation|expectation\\." kernel_gen test script` 与 `rg -n "test_expectation_case_runner" kernel_gen test script` 均无命中。`expectation` 仅作为合同验收资产单列，不计入 diff 反推测试

代码质量矩阵审查：API 一致性上，`run_case(...)` / `raise_if_failures(...)` 维持单职责、稳定导出；边界上，`case_name` 空值与 `case_fn` 非 callable 已显式拒绝；异常模型上，普通异常被收集并保留类型与消息，`KeyboardInterrupt/SystemExit` 未被吞掉但建议后续补显式回归；模块边界上，`kernel_gen.tools.case_runner` 仅依赖标准库，不反向依赖 `test/` 或 expectation；依赖方向上，产品测试树已去掉 expectation 直接导入；复用上，helper 可供后续 IR/tool case 化测试复用；函数粒度上，两层 helper 切分清晰；可读性与注释示例基本到位；兼容债上，旧 expectation 产品测试入口已删除；测试有效性上，新测试可在 helper 失效时直接失败。可改进点：`spec/tools/case_runner.md` 可再补一个通过 `from kernel_gen.tools import run_case` 的公开导入示例，进一步强调产品入口；`run_case` 的 BaseException 非吞掉语义建议后续补显式用例

合同验收（如适用）：`python3 -m expectation.pass.tile.analysis`、`python3 -m expectation.pass.tile` 与 `python3 -m expectation` 均通过，作为本轮 expectation 合同验收资产单列

结论：通过。case runner 已迁入 `kernel_gen.tools`，产品测试树不再直接依赖 expectation，删除旧 expectation 测试入口的收口合理，未发现新的阻断项，可进入 merge

## merge

时间：2026-04-22 23:00 +0800

经办人：李白

任务：T-20260422-854cafe4

合并内容：把 case_runner 公开 helper、spec 说明、产品测试与旧 expectation 产品测试入口收口到主线；仅保留 expectation 作为合同验收资产，不再让产品测试树直接依赖 expectation。

验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-quality-s1-baseline:/home/lfr/kernelcode_generate python3 -m pytest -q test/tools/test_case_runner.py test/tools/test_dsl_run.py` -> `24 passed, 13 warnings`；`rg -n "from expectation|import expectation|expectation\\." kernel_gen test script` -> 无命中；`git diff --check` 与 `git diff --cached --check` 均通过。

Diff 反推自测：已按实际 diff 复核 `kernel_gen/tools/__init__.py`、`kernel_gen/tools/case_runner.py`、`spec/tools/case_runner.md`、`test/tools/test_case_runner.py` 与删除的 `test/tools/test_expectation_case_runner.py`，本次 merge 仅收口这批已通过审查的改动。

Diff 反推审查：沿用 `T-20260422-854cafe4` review 记录中的实际审查结论，确认产品测试树已从 expectation 依赖迁出，`kernel_gen.tools.case_runner` 已成为可复用公开 helper，`spec/test/实现` 三者链路对齐；本轮未再引入新的 expectation 直接依赖。

结论：准备进入提交与同步。
