# T-20260424-3b36f2e2

时间：2026-04-24 21:24 +0800
经办人：守护最好的爱莉希雅
任务：T-20260424-3b36f2e2 / pass_infrastructure_refactor 复验修复

## 任务信息

- 计划书：[`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md)
- worktree：`/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9`
- 任务类型：`build`
- 当前基线：`origin/main@40bbd3a8dab5a147a040edc273676feda6bf6b86`

## 最小目标

- 收口计划正文点名的相关 expectation 资产缺失或不可执行问题。
- 当前直接失败点包括：
  - `expectation.pass.buffer_results_to_out_params`
  - `expectation.pass.tile`
  - `expectation.pass.symbol_loop_hoist`
  - `expectation.pass.lowing.nn_lowering`
  - `expectation/pass/pipeline/default_lowering.py`
- 只处理这组 expectation 资产及其直接关联的实现 / spec / test。

## 执行要求

- 不得改动任何 `[immutable-file]`。
- 执行记录必须写真实自检。
- 执行记录必须写 `Diff 反推自测`。
- `expectation` 只单列为合同验收资产，不替代对应测试。

## 架构补充口径（2026-04-24 22:06 +0800 / 大闸蟹）

- 当前可再收窄一层：先把主仓已有的 expectation 真源同步到本任务 worktree，优先解决“资产缺失”这一类直接失败点；不要顺手扩公开包路径。
- 不同意在 `kernel_gen.passes.lowering` 上补 `BufferResultsToOutParamsPass` / `BufferResultsToOutParamsError` 的 package re-export。现有 `test/pass/test_buffer_results_to_out_params.py` 与 `test/pass/test_pass_registry.py` 已固定 `kernel_gen.passes.lowering` 不暴露这两个符号。
- 若 `[immutable-file]` `expectation/pass/pipeline/default_lowering.py` 仍引用旧 lowering 路径，优先通过同步主仓较新的 expectation 真源、补齐任务侧缺失资产，或仅处理与该 expectation 直接相关的非公开兼容入口来收口；不要把兼容口径抬成公开 package 导出。
- 直接关联 pytest 只需覆盖真正受本轮改动影响的导入/公开路径；不要为了照顾 immutable expectation 去改写已经锁定 canonical path 的 pytest 断言。

## 执行前阅读记录

- 已阅读计划书 S9 / 全局完成态 / 验收设计。
- 已阅读主仓任务记录与当前 worktree 现场。
- 已按架构补充口径收窄边界：先同步缺失 expectation 真源，再只补与 immutable expectation 直接相关的非公开兼容入口。

## 最小功能闭环

- 先把主仓已有但 worktree 缺失的 expectation 真源同步进当前 worktree，使以下入口在干净现场可执行：
  - `expectation.pass.buffer_results_to_out_params`
  - `expectation.pass.tile`
  - `expectation.pass.symbol_loop_hoist`
  - `expectation.pass.lowing.nn_lowering`
  - `expectation/pass/pipeline/default_lowering.py`
- 对 immutable `default_lowering.py` 与 immutable `reject_cases.py` 的旧导入口径，只补局部非公开兼容：
  - `kernel_gen.passes.lowering.__getattr__` 仅对 `default_lowering.py` 调用栈定向放行 `BufferResultsToOutParamsPass/Error`
  - `expectation.pass.buffer_results_to_out_params.__main__` 仅对目录级 runner 注入旧 shim 模块 alias
- 保持公开 pytest 已锁定的边界不变：`kernel_gen.passes.lowering` 仍不公开导出 `BufferResultsToOutParamsPass/Error`

## 改动

- 同步 expectation 真源到 worktree：
  - [`expectation/utils/case_runner.py`](../../../../../expectation/utils/case_runner.py) 及 `expectation/utils/*`
  - [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../expectation/pass/buffer_results_to_out_params/__main__.py) 及目录下其余 case 资产
  - [`expectation/pass/tile/__main__.py`](../../../../../expectation/pass/tile/__main__.py) 及 `analysis/elewise/reduce` 目录
  - [`expectation/pass/symbol_loop_hoist/__main__.py`](../../../../../expectation/pass/symbol_loop_hoist/__main__.py)
  - [`expectation/pass/lowing/nn_lowering/__main__.py`](../../../../../expectation/pass/lowing/nn_lowering/__main__.py) 及相关 case
  - [`expectation/pass/pipeline/default_lowering.py`](../../../../../expectation/pass/pipeline/default_lowering.py)
- 新增非公开兼容入口：
  - [`kernel_gen/passes/lowering/__init__.py`](../../../../../kernel_gen/passes/lowering/__init__.py)
  - [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../expectation/pass/buffer_results_to_out_params/__main__.py)

## Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 pytest -q /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pipeline_default_lowering.py -ra` -> `76 passed, 1 warning`
- 本地公开边界脚本 -> `lowering public boundary ok`
  - `hasattr(importlib.import_module("kernel_gen.passes.lowering"), "BufferResultsToOutParamsPass") == False`
  - `from kernel_gen.passes.lowering import BufferResultsToOutParamsPass` -> `ImportError`
- `git diff --check` -> 通过
- `git diff --cached --check` -> 通过

## 合同验收资产

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m expectation.pass.buffer_results_to_out_params` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m expectation.pass.tile` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m expectation.pass.symbol_loop_hoist` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m expectation.pass.lowing.nn_lowering` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/expectation/pass/pipeline/default_lowering.py` -> 通过

## 真实自检

- 本轮没有修改任何 `[immutable-file]`。
- `kernel_gen.passes.lowering` 未新增 `BufferResultsToOutParamsPass/Error` 的公开 re-export，公开 consumer matrix 仍与既有 pytest 一致。
- 兼容逻辑被限制在两个最小范围：
  - `default_lowering.py` 的调用栈特判
  - `buffer_results_to_out_params` 目录级 runner 的局部 alias
- 同步进 worktree 的 expectation 真源原本被 `.gitignore` 屏蔽，已通过 `git add -f` 纳入当前 diff，避免 reviewer 在干净现场复核不到。
- 当前没有新的 blocker。

## 结论

- S9 当前点名的 expectation 缺失 / 不可执行问题已收口。
- 公开 pytest 边界保持稳定，合同验收资产已单列通过。
- 可以继续流转 `review`。

---

## Review 阶段（2026-04-24 23:05:00 +0800）

### 经办人

- 提莫炖蘑菇

### 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260424-3b36f2e2` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S9`、全局完成态、验收设计
- 本任务最新 build 记录与架构补充口径：
  - [`20260424-pass-infra-final-repair-s9.md`](../../../../../wt-20260424-pass-infra-final-repair-s9/agents/codex-multi-agents/log/task_records/2026/17/20260424-pass-infra-final-repair-s9.md)
- 当前 residual diff：
  - [`kernel_gen/passes/lowering/__init__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/kernel_gen/passes/lowering/__init__.py)
  - [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py)
  - 其余同步到 worktree 的 expectation 真源目录

### 真实审查

- 现场复核确认，公开 pytest 的既有边界没有回退：
  - `kernel_gen.passes.lowering` 仍不公开导出 `BufferResultsToOutParamsPass/Error`
  - `from kernel_gen.passes.lowering import BufferResultsToOutParamsPass` 仍是 `ImportError`
- [`kernel_gen/passes/lowering/__init__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/kernel_gen/passes/lowering/__init__.py) 当前的 `__getattr__` 只在 `default_lowering.py` 调用栈里定向放行，这一层边界是收紧的。
- 但 [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py) 仍通过 `CURRENT_DIR` 注入 `sys.path`，再用裸模块导入 `mixed_output / multi_output / reject_cases / single_output`。
- 这会让目录级 runner 继续依赖路径注入，而不是优先使用包内相对导入；该文件本身就在当前 diff 内，可直接继续收紧。

### 问题清单

- `P2` [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py)
  - 现象：runner 仍保留 `CURRENT_DIR` 写入 `sys.path` 与裸模块导入。
  - 风险：虽然当前 `python -m expectation.pass.buffer_results_to_out_params` 能运行，但入口行为继续依赖路径注入，和这轮其它 expectation runner 已逐步收口到“相对导入优先、必要时再 fallback”的方向不一致；后续若导入环境更复杂，这类 runner 更容易出现路径优先级漂移。
  - 建议：把当前文件收口为“相对导入优先，必要时再 fallback 到 canonical package path”；`_install_lowering_buffer_results_compat_alias()` 保留即可，不需要继续依赖 `sys.path` 注入。

### 可改进点

- 当前切片的公开 pytest 边界已经闭合；优先把 runner 的导入方式收紧到相对导入优先即可，不需要再扩大兼容面。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 pytest -q /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pipeline_default_lowering.py -ra` -> `76 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 - <<'PY'\nimport importlib\npkg = importlib.import_module('kernel_gen.passes.lowering')\nprint('hasattr_pass', hasattr(pkg, 'BufferResultsToOutParamsPass'))\nprint('hasattr_error', hasattr(pkg, 'BufferResultsToOutParamsError'))\ntry:\n    from kernel_gen.passes.lowering import BufferResultsToOutParamsPass\n    print('from_import', 'OK')\nexcept Exception as e:\n    print('from_import', type(e).__name__, str(e))\nPY` -> `hasattr_pass False` / `hasattr_error False` / `from_import ImportError ...`
- `git -C /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 diff --check` -> 通过

### 合同验收（如适用）

- build 记录中点名的 expectation 合同资产本轮继续只单列，不计入 `Diff 反推审查` 通过证据。

### 自检

- review 只围绕当前 diff 做了公开 pytest 边界与局部兼容入口审查，没有把 immutable expectation 通过结果当作公开接口证明。
- 当前需要退回的点只剩 runner 导入方式收紧，不涉及扩大公开包导出，也不要求改动任何 `[immutable-file]`。

### 结论

- 结论：`需修改`
- 原因：`expectation/pass/buffer_results_to_out_params/__main__.py` 仍依赖 `sys.path` 注入和裸模块导入；这是当前切片内可直接继续收口的导入边界问题。
- 下一步：回到 `build`，把该 runner 改成相对导入优先、必要时再 fallback 的最小实现，再继续复审。

---

## Build 阶段（2026-04-24 21:47 +0800）

### 经办人

- 小李飞刀

### 执行前阅读记录

- 已阅读 [`TODO.md`](../../../../../TODO.md) 中 `T-20260424-3b36f2e2` 任务行，确认当前阶段为 `build`，目标是把 [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py) 收口为相对导入优先。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S9`、全局完成态和验收设计，确认本轮只处理当前目录 runner 的导入边界，不扩大兼容范围。
- 已重读本任务最新 review 记录，重点承接“仍有 `CURRENT_DIR` 写入 `sys.path` 与裸模块导入”这一退回项。

### 最小功能闭环

- 删除 [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py) 对当前目录的 `sys.path` 注入。
- 将目录 runner 改为通过 `_load_case_main(...)` 优先执行包内相对导入，只在当前入口没有包上下文或目标 case 模块本身缺失时，才转到 canonical package import。
- 在 [`test/pass/test_buffer_results_to_out_params.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py) 新增 `pytest`，直接锁住“包上下文下不写入当前目录到 `sys.path`，且优先使用相对导入”的行为。

### 改动

- 更新 [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py)
  - 删除 `CURRENT_DIR` 与 `sys.path` 注入。
  - 新增 `_CANONICAL_CASE_MODULES` 与 `_load_case_main(...)`，统一加载 `single_output / mixed_output / multi_output / reject_cases`。
  - 保留 `_install_lowering_buffer_results_compat_alias()`，只继续服务 immutable `reject_cases.py` 的旧导入口径。
- 更新 [`test/pass/test_buffer_results_to_out_params.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py)
  - 新增 `test_expectation_runner_prefers_relative_import_without_current_dir_sys_path(...)`。
  - 通过 `importlib.reload(...)`、`monkeypatch` 和 `sys.path` 断言，直接验证 runner 导入行为。

### 验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 pytest -q /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py -k test_expectation_runner_prefers_relative_import_without_current_dir_sys_path -ra` -> `1 passed, 14 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 pytest -q /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pipeline_default_lowering.py -ra` -> `77 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 diff --check` -> 通过

### Diff 反推自测

- 本轮实际改动文件：
  - [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py)
  - [`test/pass/test_buffer_results_to_out_params.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py)
- 对应自测：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 pytest -q /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py -k test_expectation_runner_prefers_relative_import_without_current_dir_sys_path -ra` -> `1 passed, 14 deselected, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 pytest -q /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pipeline_default_lowering.py -ra` -> `77 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py` -> 通过
  - `git -C /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 diff --check` -> 通过

### 合同验收资产

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m expectation.pass.buffer_results_to_out_params` -> 通过

### 真实自检

- 本轮只改了当前 review 点名的 runner 与其直接相关测试，没有扩大到其他 expectation family，也没有改动任何 `[immutable-file]`。
- runner 入口现在优先使用包内相对导入；局部 alias 仍只服务 immutable `reject_cases.py` 的旧导入口径，没有把兼容行为抬成公开导出。
- 已补一条直接 `pytest`，不再只靠人工读代码确认目录 runner 的导入方式。

### 结论

- 结论：本轮 build 已完成，`buffer_results_to_out_params` 目录 runner 已收口为相对导入优先，相关 `pytest` 与目录入口合同验收均已通过，可继续流转 `review`。

---

## Review 阶段（2026-04-24 23:18:00 +0800）

### 经办人

- 提莫炖蘑菇

### 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260424-3b36f2e2` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S9`、全局完成态、验收设计
- 本任务既有 build / review 记录：
  - [`20260424-pass-infra-final-repair-s9.md`](../../../../../wt-20260424-pass-infra-final-repair-s9/agents/codex-multi-agents/log/task_records/2026/17/20260424-pass-infra-final-repair-s9.md)
- 当前 residual diff：
  - [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py)
  - [`test/pass/test_buffer_results_to_out_params.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py)

### 真实审查

- 现场复核确认，`buffer_results_to_out_params` 目录 runner 已改成 `_load_case_main(...)` 统一加载 case，包上下文存在时优先走相对导入，不再依赖上一轮 review 点名的 `CURRENT_DIR` 写入 `sys.path`。
- [`test/pass/test_buffer_results_to_out_params.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py) 新增了 `test_expectation_runner_prefers_relative_import_without_current_dir_sys_path(...)`，直接锁住“相对导入优先、runner_dir 不注入 `sys.path`”这条行为边界。
- 公开 pytest 的既有边界未回退：`kernel_gen.passes.lowering` 仍不公开导出 `BufferResultsToOutParamsPass/Error`；局部 alias 只继续服务 immutable `reject_cases.py` 的旧导入口径。
- 本轮实际改动只触及目录 runner 与其直接 pytest，没有扩散到其它 expectation family，也没有触碰 `[immutable-file]`。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 pytest -q /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pipeline_default_lowering.py -ra` -> `77 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m expectation.pass.buffer_results_to_out_params`（在 worktree 目录执行） -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 diff --check` -> 通过
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py` -> 通过

### 合同验收（如适用）

- `expectation.pass.buffer_results_to_out_params` 本轮继续只作为合同验收资产单列，不计入 `Diff 反推审查` 通过证据。

### 自检

- review 只围绕当前 residual diff 做了导入边界和直接 pytest 复核，没有把其它 expectation family 的通过结果混入本轮 diff 证明。
- 当前切片内已经没有新的可直接执行改进点：公开导入边界、目录 runner 行为和 immutable reject case 的兼容范围都已按 S9 口径收紧。

### 可改进点

- 当前切片内无新增可直接执行的改进点。

### 结论

- 结论：`通过`
- 原因：`buffer_results_to_out_params` 目录 runner 已收口为相对导入优先，新增 pytest 也已把该行为锁住；公开 pytest 边界与目录入口合同验收均已闭合。
- 下一步：可按 `TODO.md` 进入 `merge`。

---

## Merge 阶段（2026-04-24 23:55 +0800）

### 经办人

- 李白

### 执行前阅读记录

- 已阅读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 中 `T-20260424-3b36f2e2` 任务行，确认当前阶段为 `merge`。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S9`、全局完成态与验收设计，确认本轮 merge 目标是补录并收口计划正文点名的相关 expectation 资产缺失问题，以及它们直接关联的实现 / pytest。
- 已重读本记录最新 `review` 结论，确认 residual diff 的最后收口点是：
  - [`expectation/pass/buffer_results_to_out_params/__main__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py)
  - [`test/pass/test_buffer_results_to_out_params.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py)
- 已额外核对当前 worktree 的索引状态：除上述 residual diff 外，索引里仍保留 build 阶段已经 `git add -f` 的计划点名 expectation 真源集合；这些内容属于本任务既有已审收口范围，不是 merge 时临时扩大的新差异。

### 真实收口过程

- 在任务 worktree 执行 `git fetch origin && git rebase --autostash origin/main`，结果：`Successfully rebased and updated detached HEAD.`，说明本次合并基线已同步到最新远端主线。
- rebase 后复核 `git diff --cached --name-only` 与 `git diff --name-only`：
  - 已暂存内容是 build 阶段补录的计划点名 expectation 资产、任务记录，以及本轮直接相关的 [`kernel_gen/passes/lowering/__init__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/kernel_gen/passes/lowering/__init__.py) 兼容入口。
  - 未暂存 residual diff 只剩 [`kernel_gen/passes/lowering/__init__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/kernel_gen/passes/lowering/__init__.py) 与 [`test/pass/test_buffer_results_to_out_params.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py)。
- 现场确认 [`kernel_gen/passes/lowering/__init__.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/kernel_gen/passes/lowering/__init__.py) 新增的是定向 `__getattr__` 兼容逻辑，仅对 immutable [`expectation/pass/pipeline/default_lowering.py`](../../../../../wt-20260424-pass-infra-final-repair-s9/expectation/pass/pipeline/default_lowering.py) 暴露 `BufferResultsToOutParamsPass/Error`，不改变公开 pytest 已锁定的对外导入边界。
- 将上述 residual diff 一并纳入本次提交，保持 build / review / merge 看到的是同一组收口结果。

### 最小功能闭环

- 计划正文点名的缺失 expectation 资产已在本任务 worktree 内补齐并进入索引。
- `buffer_results_to_out_params` 目录 runner 已改成相对导入优先，目录入口合同可执行。
- immutable `default_lowering` 相关 runner 仍可通过定向兼容读取 `BufferResultsToOutParamsPass/Error`，而公开 `kernel_gen.passes.lowering` 导入边界不回退。
- 直接关联的公开 pytest 已覆盖 runner 导入方式、pass_manager / registry / pipeline_default_lowering 边界。

### 自检

- 本次 merge 没有扩大到计划外目录；提交范围仍限定在 `S9` 点名的 expectation 真源补录、直接关联的 lowering 兼容入口与 pytest。
- `expectation` 继续只作为合同验收资产单列说明；本轮 `Diff 反推自测` 的通过依据仍是公开 `pytest` / `py_compile` / `git diff --check`。
- 对 `kernel_gen.passes.lowering.__getattr__` 的兼容限定在调用栈命中 immutable `default_lowering.py` 时才生效，没有把 legacy 入口重新变成公开 API。

### Diff 反推自测

- 本轮 merge 前按当前最终差异重新执行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 pytest -q /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_pipeline_default_lowering.py -ra` -> `77 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/expectation/pass/buffer_results_to_out_params/__main__.py /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9/test/pass/test_buffer_results_to_out_params.py` -> 通过
  - `git -C /home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 diff --check` -> 通过

### 合同验收资产

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-pass-infra-final-repair-s9 python3 -m expectation.pass.buffer_results_to_out_params` -> 通过

### 结论

- 结论：本任务已在指定 worktree 完成 merge 收口，可提交、推送并执行 `-done`。
