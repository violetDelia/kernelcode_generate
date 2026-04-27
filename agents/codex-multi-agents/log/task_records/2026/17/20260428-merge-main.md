# T-20260428-540bcf8c / 主仓当前更改 merge

## 任务信息
- 任务状态: `merge`
- worktree: [`/home/lfr/kernelcode_generate`](/home/lfr/kernelcode_generate)
- 记录文件: [`agents/codex-multi-agents/log/task_records/2026/17/20260428-merge-main.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260428-merge-main.md)

## 执行前阅读记录
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 中 `T-20260428-540bcf8c` 当前任务行，确认本轮目标是收主仓工作区当前改动并推送到 `main`。
- 已核对当前主仓 `git status --short --untracked-files=all`，确认当前候选范围为：
  - [`agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md)
  - [`agents/standard/协作执行通用规则.md`](/home/lfr/kernelcode_generate/agents/standard/协作执行通用规则.md)
  - [`agents/standard/计划书标准.md`](/home/lfr/kernelcode_generate/agents/standard/计划书标准.md)
  - [`kernel_gen/core/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/core/__init__.py)
  - [`kernel_gen/core/config.py`](/home/lfr/kernelcode_generate/kernel_gen/core/config.py)
  - [`kernel_gen/core/error.py`](/home/lfr/kernelcode_generate/kernel_gen/core/error.py)
  - [`spec/core/config.md`](/home/lfr/kernelcode_generate/spec/core/config.md)
  - [`spec/core/error.md`](/home/lfr/kernelcode_generate/spec/core/error.md)
  - [`test/core/test_config.py`](/home/lfr/kernelcode_generate/test/core/test_config.py)
  - [`test/core/test_error.py`](/home/lfr/kernelcode_generate/test/core/test_error.py)
- 已确认 [`wt-20260426-repo-conformance-s6-coverage/`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s6-coverage/) 是独立临时 worktree 目录，不属于本轮主仓 merge 范围。
- 已核对 `kernel_gen/core/`、`spec/core/`、`test/core/` 中的真实文件集合，只收源码 / spec / pytest 文件，不收 `__pycache__` 等临时产物。
- 已执行 `git fetch origin`，当前主仓 `HEAD` 与 `origin/main` 一致，均为 `403b92db60f899f89844f241673056a51454c585`。

## 最小功能闭环
- 本轮主仓收口分为两部分：
  - 标准与角色规则文档的审查 / 终验口径修正。
  - `kernel_gen.core` 公共 `config / error` 底座及其对应 `spec / pytest` 落地。
- 合并后主线应同时满足：
  - `kernel_gen.core` 公开源码、`spec/core`、`test/core` 一起进入主线。
  - 不把临时 worktree 目录、`__pycache__`、其他未跟踪产物误并入主线。

## 真实自检
- 当前主仓候选改动中不包含 `expectation` 文件，本轮不会触碰 `expectation`。
- 当前未发现需要收口的其他已跟踪改动；本轮边界固定为 3 个规则文档、2 个 `spec/core` 文档、3 个 `kernel_gen/core` 源码文件、2 个 `test/core` pytest 文件与当前任务记录。
- 当前主仓没有独立 secondary worktree；本轮直接以主仓现有 diff 做收口，不把其他 worktree 目录带入提交。

## Diff 反推自测
- `python3 -m py_compile /home/lfr/kernelcode_generate/kernel_gen/core/__init__.py /home/lfr/kernelcode_generate/kernel_gen/core/config.py /home/lfr/kernelcode_generate/kernel_gen/core/error.py /home/lfr/kernelcode_generate/test/core/test_config.py /home/lfr/kernelcode_generate/test/core/test_error.py`
- `python3 -m pytest -q /home/lfr/kernelcode_generate/test/core/test_config.py /home/lfr/kernelcode_generate/test/core/test_error.py -ra`
- `git -C /home/lfr/kernelcode_generate diff --cached --check`
- 结果：
  - `py_compile` 通过。
  - `pytest` 结果为 `9 passed in 0.01s`。
  - staged `diff --check` 通过。

## merge
- 时间：2026-04-28 16:38 +0800
- 经办人：李白
- 任务：T-20260428-540bcf8c
- 任务目标：合并主仓工作区当前改动并推送到 `main`。

### 本次收口范围
- [`agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md)
- [`agents/standard/协作执行通用规则.md`](/home/lfr/kernelcode_generate/agents/standard/协作执行通用规则.md)
- [`agents/standard/计划书标准.md`](/home/lfr/kernelcode_generate/agents/standard/计划书标准.md)
- [`kernel_gen/core/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/core/__init__.py)
- [`kernel_gen/core/config.py`](/home/lfr/kernelcode_generate/kernel_gen/core/config.py)
- [`kernel_gen/core/error.py`](/home/lfr/kernelcode_generate/kernel_gen/core/error.py)
- [`spec/core/config.md`](/home/lfr/kernelcode_generate/spec/core/config.md)
- [`spec/core/error.md`](/home/lfr/kernelcode_generate/spec/core/error.md)
- [`test/core/test_config.py`](/home/lfr/kernelcode_generate/test/core/test_config.py)
- [`test/core/test_error.py`](/home/lfr/kernelcode_generate/test/core/test_error.py)
- [`agents/codex-multi-agents/log/task_records/2026/17/20260428-merge-main.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260428-merge-main.md)

### 排除项
- [`wt-20260426-repo-conformance-s6-coverage/`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s6-coverage/) 未纳入 staged 结果，不进入本轮主线提交。
- `kernel_gen/core/__pycache__/` 与 `test/core/__pycache__/` 等临时产物未纳入 staged 结果。

## 结论
- 当前主仓改动已完成边界确认和最小验证，可直接提交、推送并执行 `-done`。
