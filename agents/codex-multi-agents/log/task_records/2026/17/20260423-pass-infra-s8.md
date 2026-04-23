# T-20260423-acccf628

## 时间

- 2026-04-24 07:28:59 +0800

## 经办人

- 睡觉小分队

## 任务

- `T-20260423-acccf628`
- `pass-infra-S8-spec`

## 任务目标

- 按 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8` 收口 analysis family 退场的 `spec/doc` 边界，写清旧路径稳定失败、registry 构造失败和文档入口清理点。

## 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260423-acccf628` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8`、全局完成态、验收设计
- `S1-S7` 记录：
  - [`20260423-pass-infra-s1.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md)
  - [`20260423-pass-infra-s2.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md)
  - [`20260423-pass-infra-s3.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s3.md)
  - [`20260423-pass-infra-s4.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s4.md)
  - [`20260423-pass-infra-s5.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s5.md)
  - [`20260423-pass-infra-s6.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s6.md)
  - [`20260423-pass-infra-s7.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s7.md)
- analysis 相关现状：
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_engine.md)
  - [`spec/analysis/analysis_kernel.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_kernel.md)
  - [`spec/pass/analysis/func_cost.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/analysis/func_cost.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
  - [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
- 相关实现/测试只读核对：
  - [`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/analysis/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/analysis/__init__.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/analysis/test_analysis.py)
  - [`test/pass/test_analysis_func_cost.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_analysis_func_cost.py)

## 最小功能闭环

- 删除 analysis family 的 3 份独立 `spec`，不再保留活跃公开合同：
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_engine.md)
  - [`spec/analysis/analysis_kernel.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_kernel.md)
  - [`spec/pass/analysis/func_cost.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/analysis/func_cost.md)
- 在 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md) 写清旧 import path 稳定失败，且 `build_registered_pass("analyze-func-cost")` 必须失败。
- 在 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)、[`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)、[`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md) 清掉 analysis family 的活跃说明与链接。

## 改动

- 删除：
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_engine.md)
  - [`spec/analysis/analysis_kernel.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_kernel.md)
  - [`spec/pass/analysis/func_cost.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/analysis/func_cost.md)
- 修改 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
  - 增加 `kernel_gen.analysis`、`kernel_gen.passes.analysis` 与 `kernel_gen.passes.analysis.func_cost` 的旧路径稳定失败边界
  - 明确 `build_registered_pass("analyze-func-cost")` 必须失败
  - 将这条失败口径挂到 `test/pass/test_pass_registry.py` 的验收描述
- 修改 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)
  - 删掉 `AnalyzeFuncCostPass` 示例和 analysis 单返回说明
  - 保留与当前 surviving pass family 有关的排序、返回值和错误传播边界
- 修改 [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
  - 删除对 `spec/analysis/analysis_engine.md` 的依赖说明
  - 将 `dma.slice` 的路径描述改写为方言层自身语义，不再引用 analysis 编号
- 修改 [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
  - 删掉 analysis family 依赖入口
  - 删掉 `kernel_gen/analysis/` 模块行
  - 将 `kernel_gen` 总述收口到当前仍存活的模块范围

## 验证

- `git diff --check`
- `rg -n "analysis_engine|analysis_kernel|AnalyzeFuncCostPass|kernel_gen\\.analysis|kernel_gen\\.passes\\.analysis|func_cost" spec ARCHITECTURE/project_architecture.md`

## Diff 反推自测

- `python3` 文本断言脚本：
  - 断言 3 个 analysis spec 文件已删除
  - 断言 [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)、[`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)、[`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md) 不再含活跃 analysis family 说明
  - 断言 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md) 已写入旧路径稳定失败与 `analyze-func-cost` 构造失败

## 合同验收（如适用）

- `expectation/**` 在 `S8` 只作合同资产单列，本轮未执行，也未改写。

## 自检

- 本轮只改 `spec/doc`，未碰实现和测试；analysis family 的活跃合同入口已从 `spec/` 与总览文档中移除。
- `registry` 已补旧路径与旧 pass 名失败边界，避免下游只删文档却继续把 retired family 当公开入口。
- `pass_manager` 只保留当前 surviving pass family 的行为说明，未顺手改 lowering 顺序、tile 边界或 pipeline 合同。
- 未跑 `pytest`；按 `S8` 的 diff 反推，analysis 退场后的实现/test 删除与 registry/pass_manager pytest 由下游 `build` 继续完成。
- 当前 worktree 原本不带 `ARCHITECTURE/plan` 与这条任务记录目录；本轮按主仓计划书与 `TODO` 读入上下文，并在 worktree 内补齐记录文件。

## 结论

- `spec` 阶段已完成，analysis family 的文档入口和 registry 失败边界已收口；下一步进入 `build`，继续删除实现/test 残留并补对应 `pytest`。

---

## Build 阶段（2026-04-24 16:55:00 +0800）

### 经办人

- 金铲铲大作战

### 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260423-acccf628` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8`、全局完成态、验收设计
- 本 worktree 既有 spec 记录：
  - [`20260423-pass-infra-s8.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md)
- 当前实现 / 测试现场：
  - [`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py)
  - [`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py)
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)

### 最小功能闭环

- 删除 analysis family 的实现 / 测试残留，使当前 worktree 不再保留：
  - `kernel_gen.analysis.*`
  - `kernel_gen.passes.analysis.*`
  - `test/analysis/*`
  - `test/pass/test_analysis_func_cost.py`
- 补齐 build 记录中的 inherited residual diff 清单，使其覆盖当前 worktree 里仍带着的 analysis 退场文档面：
  - `ARCHITECTURE/project_architecture.md`
  - `spec/dialect/dma.md`
  - `spec/pass/registry.md`
  - `spec/analysis/*.md`
- 让 [`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py) 不再注册 `AnalyzeFuncCostPass`，并使 `build_registered_pass("analyze-func-cost")` 稳定失败。
- 同步 [`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py) 和 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md) 的 analysis 退场 fail-fast 边界。

### 改动

- 删除 analysis family 实现残留：
  - [`kernel_gen/analysis/analysis.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/analysis.py)
  - [`kernel_gen/analysis/compute/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/compute/__init__.py)
  - [`kernel_gen/analysis/compute/kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/compute/kernel.py)
  - [`kernel_gen/analysis/compute/nn.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/compute/nn.py)
  - [`kernel_gen/analysis/compute/symbol.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/compute/symbol.py)
  - [`kernel_gen/analysis/memory/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/memory/__init__.py)
  - [`kernel_gen/analysis/memory/dma.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/memory/dma.py)
  - [`kernel_gen/analysis/memory/nn.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/memory/nn.py)
  - [`kernel_gen/passes/analysis/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/analysis/__init__.py)
  - [`kernel_gen/passes/analysis/func_cost.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/analysis/func_cost.py)
- 删除 analysis family 文档残留：
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_engine.md)
  - [`spec/analysis/analysis_kernel.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_kernel.md)
  - [`spec/pass/analysis/func_cost.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/analysis/func_cost.md)
- 删除 analysis family 测试残留：
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/analysis/test_analysis.py)
  - [`test/analysis/test_analysis_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/analysis/test_analysis_private_helpers.py)
  - [`test/analysis/test_analysis_submodule_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/analysis/test_analysis_submodule_private_helpers.py)
  - [`test/pass/test_analysis_func_cost.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_analysis_func_cost.py)
- 修改 inherited analysis 退场文档残留：
  - [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
    - 删除 `kernel_gen/analysis/` 模块行和 analysis family 依赖入口
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
    - 删除对 `spec/analysis/analysis_engine.md` 的依赖说明
    - 将 `dma.slice` 路径描述改写为方言层自身语义
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
    - 增加 `kernel_gen.analysis`、`kernel_gen.passes.analysis` 与 `kernel_gen.passes.analysis.func_cost` 的旧路径稳定失败边界
    - 明确 `build_registered_pass(\"analyze-func-cost\")` 必须失败
- 修改 [`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py)
  - 删除 `AnalyzeFuncCostPass` import
  - 删除 `load_builtin_passes()` 中的 `AnalyzeFuncCostPass` 注册
- 修改 [`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py)
  - 增加 analysis family 旧路径 fail-fast 用例
  - 增加 `analyze-func-cost` registry 构造失败用例
  - 为 worktree-only fail-fast 验证补 `sys.path / sys.modules` 隔离 helper，避免主仓根目录 fallback 污染结果
- 修改 [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py)
  - 增加 analysis family 旧路径 fail-fast 用例
  - 为 worktree-only fail-fast 验证补 `sys.path / sys.modules` 隔离 helper
- 修改 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)
  - 把 analysis family 旧路径加入稳定失败列表

### Diff 反推自测

- 执行目录：`/home/lfr/kernelcode_generate`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py -ra` -> `60 passed, 1 warning`
- 本地 import 边界脚本：
  - 断言 `kernel_gen.analysis`、`kernel_gen.analysis.compute`、`kernel_gen.analysis.memory`、`kernel_gen.passes.analysis`、`kernel_gen.passes.analysis.func_cost` 在 worktree-only 路径下全部 `ModuleNotFoundError`
  - 输出：`analysis import boundary ok`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8 diff --check` -> 通过

### 合同验收（如适用）

- `expectation/**` 本轮未执行。
- 原因：analysis family 退场只涉及实现删除、registry/pass_manager import 失败边界与对应 pytest；当前 diff 没有可对应的 expectation 合同资产。

### 真实自检

- 这轮真正的风险点不是“代码没删干净”，而是 worktree 测试进程会从主仓根目录 fallback import 旧 analysis 模块，导致 fail-fast 用例失真。
- 已通过两层收口解决：
  - 物理删除 worktree 内的 analysis 实现、测试与空目录，避免 namespace package 残留
  - 在 fail-fast pytest 中临时隔离主仓 fallback 路径和父包缓存，只验证当前 worktree 自己的公开边界
- 本轮没有改 pass_manager 逻辑，也没有顺手改 pipeline 顺序或 tile 相关合同，只围绕 analysis 退场边界收口。
- build 记录原先漏列了 inherited spec/doc residual 与 `__init__.py` 删除面；本轮已补齐到和当前 `git status` 一致，不再只剩局部实现 / pytest 视角。
- 当前剩余 warning 仅来自 xdsl 上游 `irdl_options list`，不是这轮 diff 引入。

### 结论

- `T-20260423-acccf628` 的 build 已完成：
  - analysis family 实现 / 测试残留已删除
  - `analyze-func-cost` registry 入口已退场
  - registry / pass_manager 的旧 analysis import path fail-fast 边界已由 spec + pytest 锁定
- 下一步可按 `TODO.md` 流转到 `review`。

---

## Review 阶段（2026-04-24 20:45:00 +0800）

### 经办人

- 不要啊教练

### 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260423-acccf628` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8`、全局完成态、验收设计
- 本任务前序记录：[`20260423-pass-infra-s8.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md)
- 当前 residual diff 与对应文件：
  - [`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py)
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)
  - [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
  - [`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py)

### 真实审查

- 现场复核确认：analysis family 的实现与测试残留已经删除，`kernel_gen.analysis*` 与 `kernel_gen.passes.analysis*` 在 worktree-only 路径下都稳定 `ModuleNotFoundError`。
- `build_registered_pass("analyze-func-cost")` 现场复核已稳定报 `PassRegistryError: unknown pass 'analyze-func-cost'`。
- [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md) 与 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md) 已补上旧 analysis path fail-fast 列表，主路径行为与 pytest 一致。
- 当前没有发现实现或测试回退；问题落在任务记录的证据链完整性。

### 问题清单

- `P2` [`20260423-pass-infra-s8.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md)
  - 现象：build 记录的 `改动` 清单没有覆盖完整 residual diff。当前 diff 里实际还包含 [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)、[`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)、以及被删除的 `kernel_gen/analysis/*/__init__.py`、`spec/analysis/*.md` 等条目，但 build 记录没有一并列出。
  - 风险：下游只看任务记录时，会误判这轮实际改动范围，只看到 `registry/pass_manager` 与部分测试，漏掉 analysis 退场相关文档与包入口删除。
  - 建议：补齐任务记录中的 `改动` 清单，至少把 residual diff 中的文档删除/更新和 `__init__.py` 删除面写全，再继续流转。

### 可改进点

- 这轮功能主线已经闭合，优先补任务记录完整性即可，不需要再扩展实现或测试范围。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py -ra` -> `60 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8:/home/lfr/kernelcode_generate python3 - <<'PY'\nfrom kernel_gen.passes.registry import build_registered_pass\ntry:\n    build_registered_pass('analyze-func-cost')\n    print('BUILD_OK')\nexcept Exception as e:\n    print(type(e).__name__, str(e))\nPY` -> `PassRegistryError PassRegistryError: unknown pass 'analyze-func-cost'`

---

## Review 阶段（2026-04-24 21:35:00 +0800）

### 经办人

- 提莫炖蘑菇

### 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260423-acccf628` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8`、全局完成态、验收设计
- 本任务既有 spec/build/review 记录：
  - [`20260423-pass-infra-s8.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md)
- 当前 residual diff 与关键文件：
  - [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
  - [`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py)
  - [`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py)

### 真实审查

- 现场确认 build 修复后的 residual diff 已与任务记录的 `改动` 清单一致；analysis family 的实现、测试、spec/doc 退场边界没有再遗漏到记录之外。
- [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)、[`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md) 的文件头 `最后一次更改` 元数据已经补齐到当前 build 执行人。
- analysis family 的 5 条旧 import path 在 worktree-only 路径下均稳定 `ModuleNotFoundError`；`build_registered_pass("analyze-func-cost")` 也继续稳定失败，说明 S8 的 fail-fast 边界没有被这轮记录修复回退。
- 当前 residual diff 内没有再发现属于本切片、且可直接执行的新增修正项；唯一残留 warning 仍是 xDSL 上游 `irdl_options list` 弃用告警，不属于本仓本轮 diff。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py -ra` -> `60 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8:/home/lfr/kernelcode_generate python3 - <<'PY'\nimport importlib\nmods=[\n  'kernel_gen.analysis',\n  'kernel_gen.analysis.compute',\n  'kernel_gen.analysis.memory',\n  'kernel_gen.passes.analysis',\n  'kernel_gen.passes.analysis.func_cost',\n]\nfor name in mods:\n    try:\n        importlib.import_module(name)\n        print(name, 'IMPORT_OK')\n    except Exception as e:\n        print(name, type(e).__name__, str(e))\nPY` -> 5 条 `ModuleNotFoundError`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8 diff --check` -> 通过
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py` -> 通过

### 合同验收（如适用）

- `expectation/**` 本轮仍未执行，也未计入 `Diff 反推审查`。
- 原因：当前切片只涉及 analysis family 退场后的 registry/pass_manager/spec/doc 残留与 fail-fast 边界，没有对应 expectation 合同资产。

### 自检

- 我重新对照了 `S8` 的完成态与当前 residual diff，确认这轮 build 只是补齐记录和 3 个文档文件头元数据，没有把 analysis family 的删除边界重新放宽。
- review 复跑覆盖了当前仍存活的直接 pytest 入口和 worktree-only import fail-fast 边界，没有依赖主仓 fallback。
- 当前任务记录已能机械描述 residual diff 全量范围，下游 merge 不再需要额外反推“这轮到底改了哪些文件”。

### 可改进点

- 当前切片内无新增可直接执行的改进点；analysis family 退场边界、记录证据链与 metadata 修复已经闭合。

### 结论

- `T-20260423-acccf628` 的 `review` 通过：
  - analysis family 的实现 / 测试 / spec/doc 退场边界未回退；
  - registry / pass_manager 的旧路径 fail-fast 与 `analyze-func-cost` 构造失败保持稳定；
  - 任务记录与 residual diff 已对齐，metadata 修复也已收口。
- 下一步可按 `TODO.md` 进入 `merge`。
- worktree-only import 边界复核脚本：`kernel_gen.analysis`、`kernel_gen.analysis.compute`、`kernel_gen.analysis.memory`、`kernel_gen.passes.analysis`、`kernel_gen.passes.analysis.func_cost` 全部 `ModuleNotFoundError`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8 diff --check` -> 通过

### 合同验收单列

- 本轮未执行 `expectation/**`。
- 原因：analysis family 退场只涉及实现删除、registry/pass_manager import 失败边界与对应 pytest，当前 diff 没有可对应的 expectation 合同资产。

### 自检

- 已核对 build 记录包含 `执行前阅读记录`、`最小功能闭环`、`Diff 反推自测` 与 `真实自检`。
- 已按实际 residual diff 复核主路径、失败路径与 registry 构造失败。
- 已明确写出当前仍可执行的一线改进点，结论不判通过。

### 结论

- `需修改`：实现与 pytest 已收口，但任务记录的 `改动` 清单还未覆盖完整 residual diff；应先补齐记录证据链，再继续流转。

---

## Build 复修（2026-04-24 21:20:00 +0800）

### 经办人

- 金铲铲大作战

### 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260423-acccf628` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8`、全局完成态、验收设计
- 本任务前序记录与 review 退回点：
  - [`20260423-pass-infra-s8.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md)

### 最小功能闭环

- 不再改实现或测试。
- 只补齐 build 记录中的 `改动` 清单，使其覆盖完整 residual diff：
  - [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_engine.md)
  - [`spec/analysis/analysis_kernel.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/analysis/analysis_kernel.md)
  - [`spec/pass/analysis/func_cost.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/analysis/func_cost.md)
  - [`kernel_gen/analysis/compute/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/compute/__init__.py)
  - [`kernel_gen/analysis/memory/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/analysis/memory/__init__.py)
  - [`kernel_gen/passes/analysis/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/analysis/__init__.py)

### 改动

- 修改 [`20260423-pass-infra-s8.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md)
  - 补齐 inherited spec/doc residual 条目
  - 补齐 `kernel_gen/analysis/*/__init__.py` 与 `kernel_gen/passes/analysis/__init__.py` 删除面
  - 将 build 记录中的 `改动` 清单补到与当前 residual diff 一致

### Diff 反推自测

- 执行目录：`/home/lfr/kernelcode_generate`
- 本地记录完整性脚本：
  - 断言任务记录已包含
    - `ARCHITECTURE/project_architecture.md`
    - `spec/dialect/dma.md`
    - `spec/pass/registry.md`
    - `spec/analysis/analysis_engine.md`
    - `spec/analysis/analysis_kernel.md`
    - `spec/pass/analysis/func_cost.md`
    - `kernel_gen/analysis/compute/__init__.py`
    - `kernel_gen/analysis/memory/__init__.py`
    - `kernel_gen/passes/analysis/__init__.py`
  - 输出：`record residual diff coverage ok`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8 diff --check` -> 通过

### 合同验收（如适用）

- 本轮未执行 `expectation/**`。
- 原因：当前 diff 只修改任务记录，不涉及实现、测试或合同资产内容。

### 真实自检

- 这轮唯一目标是补齐任务记录和实际 residual diff 的映射关系，不应再重复修改实现 / pytest。
- 复核结果表明 reviewer 点名的缺口已经补齐，记录现在能覆盖文档删除面、`__init__.py` 删除面和 inherited spec/doc residual。
- 本轮没有扩大任务边界，也没有把 `expectation` 混入 diff 反推测试。

### 结论

- `T-20260423-acccf628` 当前 build 只剩记录修补项，现已完成；可以继续回流 `review`。

---

## Review 复审（2026-04-24 21:35:00 +0800）

### 经办人

- 不要啊教练

### 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260423-acccf628` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8`、全局完成态、验收设计
- 本任务前序记录与最新 build 复修记录：[`20260423-pass-infra-s8.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md)
- 当前 residual diff 与对应文件：
  - [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/pass_manager.md)
  - [`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py)
  - [`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py)

### 真实审查

- 复核确认：build 记录里的 residual diff 改动清单已经补齐，覆盖了 reviewer 上一轮点名的 `project_architecture`、`dma spec`、`registry spec`、`spec/analysis` 删除面和 analysis 包 `__init__.py` 删除面。
- 主路径与失败边界没有回退：analysis family 旧导入路径仍稳定失败，`build_registered_pass("analyze-func-cost")` 仍稳定报 `PassRegistryError`。
- 当前剩余问题不在实现和 pytest，而在 residual diff 中文档元数据没有同步到本轮实际修改者。

### 问题清单

- `P2` [project_architecture.md:25](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md:25) [dma.md:10](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md:10) [registry.md:12](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md:12)
  - 现象：这 3 个文件都在当前 residual diff 里发生了实际内容变更，但文件头 `最后一次更改` 仍停在旧值 `睡觉小分队`。
  - 风险：任务链已经把 analysis family 退场写进这些文档，若元数据不更新，后续追查“本轮是谁改了公开合同/总览文档”会出现误导。
  - 建议：把这 3 个文件头的 `最后一次更改` 同步到本轮实际修改者，再继续流转。

### 可改进点

- 这轮主路径已经闭合，优先补文档元数据即可，不需要再扩展实现或测试范围。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py -ra` -> `60 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8:/home/lfr/kernelcode_generate python3 - <<'PY'\nfrom kernel_gen.passes.registry import build_registered_pass\ntry:\n    build_registered_pass('analyze-func-cost')\n    print('BUILD_OK')\nexcept Exception as e:\n    print(type(e).__name__, str(e))\nPY` -> `PassRegistryError PassRegistryError: unknown pass 'analyze-func-cost'`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8 diff --check` -> 通过

### 合同验收单列

- 本轮未执行 `expectation/**`。
- 原因：analysis family 退场只涉及实现删除、registry/pass_manager import 失败边界与对应 pytest，当前 diff 没有可对应的 expectation 合同资产。

### 自检

- 已核对 build 复修记录补齐了上一轮点名的 residual diff 证据链。
- 已按当前 residual diff 复核主路径、失败路径、registry 构造失败和文档元数据。
- 已明确写出当前仍可执行的一线改进点，结论不判通过。

### 结论

- `需修改`：实现、pytest 和任务记录都已收口，但 residual diff 中的 [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)、[`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md) 文件头 `最后一次更改` 仍未同步到本轮实际修改者，应先补齐元数据再继续流转。

---

## Build 复修（2026-04-24 21:55:00 +0800）

### 经办人

- 金铲铲大作战

### 执行前阅读记录

- [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 的 `T-20260423-acccf628` 任务行
- [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8`、全局完成态、验收设计
- 本任务前序记录与最新 review 退回点：
  - [`20260423-pass-infra-s8.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s8.md)

### 最小功能闭环

- 不改实现、不改 pytest。
- 只把 residual diff 中 3 份文档头部 `最后一次更改` 同步到本轮实际修改者：
  - [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)

### 改动

- 修改 [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)
  - 文件头 `最后一次更改`：`睡觉小分队` -> `金铲铲大作战`
- 修改 [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)
  - 文件头 `最后一次更改`：`睡觉小分队` -> `金铲铲大作战`
- 修改 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md)
  - 文件头 `最后一次更改`：`睡觉小分队` -> `金铲铲大作战`

### Diff 反推自测

- 执行目录：`/home/lfr/kernelcode_generate`
- 本地元数据校验脚本：
  - 断言 [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)、[`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md) 均包含 `最后一次更改：\`金铲铲大作战\``
  - 输出：`metadata header ok`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8 diff --check` -> 通过

### 合同验收（如适用）

- 本轮未执行 `expectation/**`。
- 原因：当前 diff 只修改文档头部元数据，不涉及实现、测试或合同资产。

### 真实自检

- 这轮唯一任务是补齐 3 份 residual diff 文档的 `最后一次更改`，不能顺手扩大到实现、spec 文本主体或 pytest。
- 现场 reviewer 点名的元数据缺口已补齐，且与本轮实际修改者一致。
- 本轮没有引入新的逻辑、接口或合同变化，风险只在元数据遗漏，现已收口。

### 结论

- `T-20260423-acccf628` 当前只剩文档头部元数据修补项，现已完成；可以继续回流 `review`。

---

## Merge 收口（2026-04-24 07:49 +0800）

### 经办人

- 李白

### 执行前阅读记录

- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认 `T-20260423-acccf628` 已进入 `merge`。
- 已重读计划书 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S8`、全局完成态 / 验收设计，以及当前任务记录中的前序 `spec/build/review` 条目。
- 已核对当前 worktree residual diff，确认本轮实际待合并范围包括 analysis family 退场对应的实现删除、registry/pass_manager fail-fast 收口、相关 spec/doc 更新、直接消费者测试收口和任务记录本身。

### 真实收口过程

- 已在 worktree 内先执行 `git fetch origin`，再以 `rebase --autostash origin/main` 将当前分支重放到最新主线；本轮 rebase 无冲突，autostash 已自动恢复。
- 已按最新 review 结论复核现场边界：analysis family 相关实现、spec、doc 与测试删除/收口已经闭合；`build_registered_pass("analyze-func-cost")` 的 fail-fast 边界与 registry/pass_manager 文档一致。
- 当前 merge 只收 `S8` 已通过审查的 residual diff，不带入 `expectation` 或其他非本任务边界文件。

### 验证

- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/test/pass/test_pass_manager.py`
  - 结果：通过。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8 diff --check`
  - 结果：通过。
- 已复核前序 build/review 记录中的最小直接证据链：
  - `pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py -ra` -> `60 passed, 1 warning`
  - `python3 - <<'PY' ... build_registered_pass('analyze-func-cost') ... PY` -> `PassRegistryError PassRegistryError: unknown pass 'analyze-func-cost'`
  - 元数据校验脚本确认 [`ARCHITECTURE/project_architecture.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/ARCHITECTURE/project_architecture.md)、[`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/dialect/dma.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8/spec/pass/registry.md) 的 `最后一次更改` 已同步到本轮实际修改者。

### Diff 反推自测

- 当前 merge 自身不新增逻辑，只对已通过 review 的 `S8` residual diff 做最终合并确认；现场重新执行了：
  - `python3 -m py_compile ...`
  - `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s8 diff --check`
- 同时保留前序 build/review 记录中的 `pytest` 子集、registry fail-fast 脚本与元数据校验结果作为本轮 diff 的已审通过依据。

### 合同验收（单列）

- 本轮未执行 `expectation/**`；analysis family 退场不涉及对应 expectation 合同资产，本次 merge 也不把 `expectation` 计入 `Diff 反推自测`。

### 自检

- 已按 merge 口径核对 `TODO`、计划书 `S8`、前序记录、现场 diff、重放结果与最小现场校验，没有发现新的阻断。
- 当前实际合并边界与 review 通过结论一致，未带入额外实现、未审合同资产或无关文件。

### 结论

- `merge` 完成，可提交、推送并执行 `-done`。
