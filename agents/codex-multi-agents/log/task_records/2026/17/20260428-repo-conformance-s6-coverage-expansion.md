# 20260428-repo-conformance-s6-coverage-expansion

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`李白`
- 任务：`T-20260428-97772af4`
- 任务类型：`merge`
- 对应计划书：[`ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md)

## 执行前阅读记录

- 已阅读 [`ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) 中 S6 `覆盖率 98 / 70 与重复测试收口` 阶段、`完成态定义`、`验收设计`。
- 已核对本 worktree 当前 residual diff、`spec/script/python_coverage_check.md`、`spec/script/python_coverage_omit.md`、`test/script/test_python_coverage_check.py`、`test/script/test_python_coverage_omit.py`、`kernel_gen/dsl/mlir_gen/function_builder.py`、`kernel_gen/dsl/mlir_gen/module_builder.py`、`kernel_gen/dsl/mlir_gen/emit/core.py` 等当前低覆盖公开模块。
- 已确认 `expectation` 只读，不作为本轮改动面。

## 最小功能闭环

- 让 `script/check_python_coverage.py` 正确读取 omit manifest，并把 omit 规则应用到全量 gate 与 `--include-module` scoped gate。
- 对只通过公开包根 / 公开 facade 验收的内部 split 文件，在 `spec/script/python_coverage_omit.md` 与对应实现文件头中统一收口。
- 对 `function_builder` 等低覆盖公开模块补齐只走公开 API 的有效测试；不得新增无效测试。
- 在全量 `coverage run --branch --source=kernel_gen -m pytest -q test` 基线上验证 line `>=98`、branch `>=70`。

## 改动

- 按用户与管理员最新明确口径，直接以 `merge` 收口当前 coverage 专项 residual diff，不再继续 build/review。
- 在 `origin/main@db9ee1a98fd7ba9618f2ff1c3086114681ef24be` 上回放当前 worktree staged diff，明确排除未跟踪产物 [`repo_s6_cov_after.json`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/repo_s6_cov_after.json)。
- `rebase` 冲突集中在 8 个文件：
  - [`kernel_gen/dsl/gen_kernel/gen_kernel.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/kernel_gen/dsl/gen_kernel/gen_kernel.py)
  - [`kernel_gen/dsl/gen_kernel/kernel_emitter.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/kernel_gen/dsl/gen_kernel/kernel_emitter.py)
  - [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/kernel_gen/dsl/mlir_gen/emit/call_nn.py)
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/kernel_gen/dsl/mlir_gen/function_builder.py)
  - [`kernel_gen/tools/dsl_run.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/kernel_gen/tools/dsl_run.py)
  - [`spec/execute_engine/execute_engine_api.md`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/spec/execute_engine/execute_engine_api.md)
  - [`spec/script/python_coverage_check.md`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/spec/script/python_coverage_check.md)
  - [`test/script/test_python_coverage_check.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/script/test_python_coverage_check.py)
- 冲突处理原则：
  - 保留本轮 coverage 专项的实质变化：`omit manifest`、`--include-module` scoped gate、精确 repo file module 路径、先 omit 再聚合/过滤的测试与 spec 收口。
  - 不回退当前主线已收住的 `kernel_gen.dsl.gen_kernel` package-root 公开边界；`KernelEmitter` 继续作为 package-root 可达公开类型保留。
  - 对纯 metadata 冲突按当前 residual diff 保留本轮最后一次更改信息。

## 验证

- `timeout 60 git fetch origin`：通过。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile ...`：通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD:/home/lfr/kernelcode_generate python3 -m pytest -q test/script/test_python_coverage_check.py test/script/test_python_coverage_omit.py test/dsl/ast/test_package.py test/dsl/ast/test_parser.py test/dsl/gen_kernel/test_gen_kernel.py test/dsl/test_package_api.py test/include/api/test_dma.py -ra`：`171 passed, 9 warnings`。
- `git diff --check`：通过。

## Diff 反推自测

- 依据实际 diff 反推，覆盖率专项本轮直接相关的公开回归面为：
  - coverage CLI / omit 合同：
    - [`test/script/test_python_coverage_check.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/script/test_python_coverage_check.py)
    - [`test/script/test_python_coverage_omit.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/script/test_python_coverage_omit.py)
  - `dsl/mlir_gen/gen_kernel` 公开边界：
    - [`test/dsl/ast/test_package.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/dsl/ast/test_package.py)
    - [`test/dsl/ast/test_parser.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/dsl/ast/test_parser.py)
    - [`test/dsl/gen_kernel/test_gen_kernel.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/dsl/gen_kernel/test_gen_kernel.py)
    - [`test/dsl/test_package_api.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/dsl/test_package_api.py)
  - include 公开边界未回退：
    - [`test/include/api/test_dma.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/include/api/test_dma.py)
- 自测结果：`171 passed, 9 warnings`；未把 `expectation` 计入 diff 反推测试。

## 合同验收

- 本轮未执行 `expectation`。
- 原因：本任务口径明确 `expectation` 只读，且 `Diff 反推测试` 不计入 `expectation`。

## 真实自检

- 已检查本次 merge 未把未跟踪产物 [`repo_s6_cov_after.json`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/repo_s6_cov_after.json) 误纳入主线。
- 已检查冲突解法没有回退 `KernelEmitter` package-root 公开导出、`dsl_run`/`execute_engine_api` 既有公开文档口径，且 `call_nn.py` 文件级 API 列表继续收回为内部拆分实现。
- 已检查 `spec/script/python_coverage_check.md`、[`script/check_python_coverage.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/script/check_python_coverage.py) 与 [`test/script/test_python_coverage_check.py`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/test/script/test_python_coverage_check.py) 对 omit 先行语义一致。

## 结论

- 本轮 coverage 专项 residual diff 已在最新 `origin/main` 基线上完成收口，可提交并推送。

---

时间：2026-04-28 22:06:02 +0800
经办人：李白
任务：T-20260428-97772af4
任务目标：按用户最新明确口径，直接以 `merge` 收口当前 coverage 专项 residual diff，并保持 `expectation` 不改
执行前阅读记录：已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[`AGENTS.md`](/home/lfr/kernelcode_generate/AGENTS.md)、[`agents/codex-multi-agents/agents/李白/李白.prompt.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents/李白/李白.prompt.md)、[`agents/standard/任务记录约定.md`](/home/lfr/kernelcode_generate/agents/standard/任务记录约定.md) 以及当前记录已有内容；已核对当前 worktree staged residual diff 只涉及 `kernel_gen/core/mlir_gen/dsl_run/coverage` 相关实现、`spec`、公开 `pytest` 与当前记录，未包含 `expectation` 写入；另有未跟踪产物 [`repo_s6_cov_after.json`](/home/lfr/kernelcode_generate/wt-20260428-repo-conformance-s6-coverage-expansion/repo_s6_cov_after.json) 仅作本地结果文件，不纳入主线提交。
最小功能闭环：将当前 worktree 已形成的 staged residual diff 回放到最新 `origin/main`，跑最小必要验证（`py_compile`、变更相关公开 `pytest`、`git diff --check`），补齐本轮 merge 记录，与业务改动同一次提交推到 `main`；不扩大到 `expectation` 或无关 worktree。
