# dsl_run_tool_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`榕`
- 目标 `spec`：
  - [`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
  - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
  - [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md)
- 目标 `API`：
  - [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
  - [`kernel_gen/tools/__init__.py`](../../kernel_gen/tools/__init__.py)
  - [`kernel_gen/passes/pipeline/__init__.py`](../../kernel_gen/passes/pipeline/__init__.py)
  - [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py)
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
- 目标 `test`：
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../test/pass/test_pipeline_npu_demo_lowering.py)
- 目标 `验收资产`：
  - [`expectation/tools/dsl_run`](../../expectation/tools/dsl_run)
  - `pytest -q test/tools/test_dsl_run.py`
  - `pytest -q test/pass/test_pass_manager.py`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.tools.dsl_run`
- 目标 `功能实现`：
  - [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
  - [`kernel_gen/tools/__init__.py`](../../kernel_gen/tools/__init__.py)
  - [`kernel_gen/passes/pipeline/__init__.py`](../../kernel_gen/passes/pipeline/__init__.py)
  - [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py)
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/execute_engine/execution_engine.py`](../../kernel_gen/execute_engine/execution_engine.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `待重建` | `待重建` |

## 评审摘要

- 评审结论：`通过`
- 评审人：
  - `大闸蟹：通过`
  - `守护最好的爱莉希雅：通过`
- 结论摘要：`新增 npu-demo-lowering 并把 dsl_run 正向 expectation/pytest 切到它，这个边界清楚；symbol-loop-hoist 在无 symbol.for 时 no-op 的合同合适；default-lowering 保留公开 builder 但不再承担 dsl_run 正向合同，这个拆分合理。按当前版本可直接重建任务推进。`

## 终验 / 复验 / 修复复核记录

- 结论人：`榕`
- 结论：`双架构师通过，待重建任务`
- 验证基线：`main@2026-04-21`
- 最小阻断项或通过摘要：`当前主线已明确为“新增 npu-demo-lowering pipeline，并让 expectation/tools/dsl_run 正向用例从 default-lowering 切换到该 pipeline”。双架构师已确认：default-lowering 保留公开 builder，但不再承担 dsl_run 正向合同；symbol-loop-hoist 在无 symbol.for 时 no-op，可以安全进入新 pipeline。下一步按最新正文重建任务。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 另一位架构师补充重点：`本轮 repair 只沿 test/tools/test_dsl_run.py::test_dsl_run_contract_files_exist 这一条旧路径断言收口，不扩展修改面。`

## 当前修复任务状态（2026-04-21 03:19:52 +0800）

- 已吸收旧 repair：`T-20260421-ab5d55e9`
  - 旧 `worktree`：`/home/lfr/kernelcode_generate/wt-20260421-dsl-run-tool-s8-repair`
  - 旧记录文件：[`agents/codex-multi-agents/log/task_records/2026/16/20260421-dsl-run-tool-s8-repair.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260421-dsl-run-tool-s8-repair.md)
  - `DONE` 已记录其完成；为避免与当前 repair 冲突，不再复用该任务号。
- 当前唯一修复任务：`T-20260421-b88f4de5`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260421-dsl-run-tool-s9-repair`
- 记录文件：[`agents/codex-multi-agents/log/task_records/2026/16/20260421-dsl-run-tool-s9-repair.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260421-dsl-run-tool-s9-repair.md)
- 最小修复目标：
  - 仅继续收口 [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 中 `test_dsl_run_contract_files_exist` 的旧 expectation 根目录 `/home/lfr` 断言，使合同文件存在性检查对齐当前主线布局。
  - 恢复 `pytest -q test/tools/test_dsl_run.py` 全绿。
  - 同时保持：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run -> exit 0`
    - `pytest -q test/pass/test_pass_manager.py -> 19 passed`
    - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
    不回退。

## 复验结论（2026-04-21 02:31:09 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@aa6eede4b6d16f32306bafe47195d382f26db612`
  - 按管理员最新口径，直接在已同步到 `origin/main` 的主仓现场复验
- 最新最小阻断项：
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 的 `test_dsl_run_contract_files_exist` 仍锁旧共享根目录 `SHARED_ROOT=/home/lfr`，当前断言 `assert (SHARED_ROOT / "expectation/tools/dsl_run/add.py").is_file()` 失败
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run -> exit 0`
  - `pytest -q test/pass/test_pass_manager.py -> 19 passed`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
  - `pytest -q test/tools/test_dsl_run.py -> 1 failed, 10 passed`
  - 当前实现、pipeline、正向 expectation 与大部分 pytest 已收口；剩余阻断已经收敛为 `test_dsl_run_contract_files_exist` 这一条旧路径断言，因此仍未满足归档前置条件

## 复验结论（2026-04-21 02:42:43 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@923512b9f0acaab98ccab831dee23e6d3bd94471`
  - 按管理员最新口径，直接在已同步到最新主线的主仓现场复验
- 最新最小阻断项：
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 的 `test_dsl_run_contract_files_exist` 仍锁旧共享根目录 `SHARED_ROOT=/home/lfr`，当前断言 `assert (SHARED_ROOT / "expectation/tools/dsl_run/add.py").is_file()` 继续失败
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run -> exit 0`
  - `pytest -q test/pass/test_pass_manager.py -> 19 passed`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
  - `pytest -q test/tools/test_dsl_run.py -> 1 failed, 10 passed`
  - 当前 `dsl_run` 工具、`npu-demo-lowering` pipeline 与正向 expectation 已通过；主线仍只剩合同文件存在性检查这一条旧共享根目录断言未收口，因此尚不满足归档前置条件

## 复验结论（2026-04-21 02:49:46 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@b41aedbd7d3abe644af568ab4a346727dc95ef83`
  - 按管理员最新口径，直接在已同步到最新主线的主仓现场复验
- 最新最小阻断项：
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 的 `test_dsl_run_contract_files_exist` 仍锁旧 expectation 根目录 `/home/lfr`；当前断言 `assert (EXPECTATION_ROOT / "expectation/tools/dsl_run/add.py").is_file()` 继续失败
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run -> exit 0`
  - `pytest -q test/pass/test_pass_manager.py -> 19 passed`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
  - `pytest -q test/tools/test_dsl_run.py -> 1 failed, 10 passed`
  - 与上一轮相比，阻断已收敛为同一条合同文件存在性检查，只是测试变量名已从 `SHARED_ROOT` 调整为 `EXPECTATION_ROOT`；其实际指向仍是旧共享根目录 `/home/lfr`，因此当前仍未满足归档前置条件

## 复验结论（2026-04-21 02:56:26 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@751858a78a79ebd6d75a49252a14c7f23959561f`
  - 按管理员最新口径，直接在已同步到最新主线的主仓现场复验
- 最新最小阻断项：
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 的 `test_dsl_run_contract_files_exist` 仍锁旧 expectation 根目录 `/home/lfr`；当前断言 `assert (EXPECTATION_ROOT / "expectation/tools/dsl_run/add.py").is_file()` 继续失败
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run -> exit 0`
  - `pytest -q test/pass/test_pass_manager.py -> 19 passed`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
  - `pytest -q test/tools/test_dsl_run.py -> 1 failed, 10 passed`
  - 最新主线已吸收 `T-20260421-f2b4a1c7`，但合同文件存在性检查仍残留旧 `/home/lfr` expectation 根目录假设；因此当前仍未满足归档前置条件

## 复验结论（2026-04-21 03:02:40 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@4a706d0259d9e46fbad1af508b504285275481ce`
  - 按管理员最新口径，直接在已同步到最新主线的主仓现场复验
- 最新最小阻断项：
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 的 `test_dsl_run_contract_files_exist` 仍锁旧 expectation 根目录 `/home/lfr`；当前断言 `assert (EXPECTATION_ROOT / "expectation/tools/dsl_run/add.py").is_file()` 继续失败
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run -> exit 0`
  - `pytest -q test/pass/test_pass_manager.py -> 19 passed`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
  - `pytest -q test/tools/test_dsl_run.py -> 1 failed, 10 passed`
  - 最新主线已吸收 `T-20260421-a093be13`，但合同文件存在性检查仍残留旧 `/home/lfr` expectation 根目录假设；因此当前仍未满足归档前置条件

## 复验结论（2026-04-21 03:10:38 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@13953609525bffda3e3f1ce20b98cf1e1b6a8c6e`
  - 按管理员最新口径，直接在已同步到最新主线的主仓现场复验
- 最新最小阻断项：
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 的 `test_dsl_run_contract_files_exist` 仍锁旧 expectation 根目录 `/home/lfr`；当前断言 `assert (EXPECTATION_ROOT / "expectation/tools/dsl_run/add.py").is_file()` 继续失败
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run -> exit 0`
  - `pytest -q test/pass/test_pass_manager.py -> 19 passed`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
  - `pytest -q test/tools/test_dsl_run.py -> 1 failed, 10 passed`
  - 最新主线已吸收 `T-20260421-f9046f7b`，但合同文件存在性检查仍残留旧 `/home/lfr` expectation 根目录假设；因此当前仍未满足归档前置条件

## 复验结论（2026-04-21 03:58:33 +0800）

- 验收结论：`通过`
- 验证基线：
  - `origin/main@276917f51213268907613dfdaca28572c1cceffa`
  - 管理员允许直接更新主仓后复验；但主仓现场当时存在未提交改动且落后 `origin/main` 1 个提交，因此本轮改用干净 detached worktree `/home/lfr/kernelcode_generate/wt-20260421-dsl-run-final-check` 复验
  - 最新主线不包含 `expectation/` 目录，因此 expectation 真源按 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-dsl-run-final-check:/home/lfr/kernelcode_generate` 以 `worktree-first + 主仓 expectation` 口径执行
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.tools.dsl_run -> exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_manager.py -> 21 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/tools/test_dsl_run.py -> 11 passed`
  - `test_dsl_run_contract_files_exist` 已对齐当前主线布局，不再锁旧 `/home/lfr` expectation 根目录
  - 当前 `dsl_run` 工具、`npu-demo-lowering` pipeline、正向 expectation 与 pytest 子集均已通过，已满足归档前置条件

## 复验结论（2026-04-21 04:01:34 +0800）

- 验收结论：`通过`
- 验证基线：
  - `origin/main@276917f51213268907613dfdaca28572c1cceffa`
  - 主仓当前存在未提交改动且落后 `origin/main` 1 个提交，因此本轮继续使用干净 detached worktree [`wt-20260421-dsl-run-final-check`](/home/lfr/kernelcode_generate/wt-20260421-dsl-run-final-check) 复验；该 worktree 当前 `HEAD` 即 `276917f51213268907613dfdaca28572c1cceffa`
  - expectation 真源按 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-dsl-run-final-check:/home/lfr/kernelcode_generate` 以 `worktree-first + 主仓 expectation` 口径执行
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.tools.dsl_run -> exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/tools/test_dsl_run.py -> 11 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_manager.py -> 21 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/pass/test_pipeline_npu_demo_lowering.py -> 2 passed`
  - 与前一位架构师结论一致；本轮再次确认 `dsl_run` 工具、`npu-demo-lowering` pipeline、正向 expectation 与 pytest 子集均已通过，当前已满足归档前置条件

## 输入摘要

- 目标：收口 `dsl_run(func, real_args, pipeline, emitcconfig)` 的正向工具合同，并为 `npu_demo` 目标新增一条独立公开 pipeline。
- 不做什么：
  - 本轮不支持 DSL 值返回。
  - 本轮不自动注入 target 当前态，不为调用方偷偷设置 `sm_memory_size/lm_memory_size`。
  - 本轮不修改 `decompass`、`lower-nn`、`symbol-loop-hoist` 的核心业务目标，只收口其在新 pipeline 中的公开边界。
  - 本轮不要求 `default-lowering` 承担 `dsl_run` 的正向入口职责。
- 当前痛点：
  - [`expectation/tools/dsl_run/add.py`](../../expectation/tools/dsl_run/add.py) 正向合同仍使用 `pipeline="default-lowering"`。
  - 当前 `default-lowering` 正向路径仍会触发历史 opt-in pass 相关前置条件，导致 `expectation.tools.dsl_run` 与 `pytest` 的真实运行前提分叉。
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py) 里对 `symbol-loop-hoist` 仍有“必须先经 tile materialize symbol.for”的排序假设，不适合直接放入新的最小 `npu_demo` pipeline。
- 完成后最想看到的例子：`dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))` 直接执行成功；`symbol-loop-hoist` 在没有 `symbol.for` 时静默 no-op；`default-lowering` 不再是这条工具合同的正向依赖。

## 计划目标

- 保持 `dsl_run(func, real_args, pipeline, emitcconfig)` 作为唯一公开工具入口。
- 新增公开 pipeline：`npu-demo-lowering`。
- 固定 `npu-demo-lowering` pass 顺序为：
  1. `DecompassPass`
  2. `NnLoweringPass`
  3. `SymbolLoopHoistPass`
- 明确 `SymbolLoopHoistPass` 的新公共边界：
  - 当输入 IR 中不存在 `symbol.for` 时，必须 `no-op`
  - 不再要求前面必须先有 `tile`
- 让 `expectation/tools/dsl_run` 与 `test/tools/test_dsl_run.py` 的正向合同切换到 `npu-demo-lowering`，不再把 `default-lowering` 作为默认正向入口。
- 保留 `default-lowering` 现有公开名字与 builder，不把本轮 `dsl_run` 合同与其历史链路强绑定。

## 当前基线

- 当前公开工具合同：
  - [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)、[`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)、[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 已存在。
  - [`expectation/tools/dsl_run/add.py`](../../expectation/tools/dsl_run/add.py) 与 [`expectation/tools/dsl_run/invalid_contract.py`](../../expectation/tools/dsl_run/invalid_contract.py) 已存在并定义真源。
- 当前 pipeline 资产：
  - [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py) 已注册 `default-lowering`。
  - `kernel_gen/passes/pipeline` 下尚无 `npu-demo-lowering` 对应 builder。
  - [`spec/pass/pipeline`](../../spec/pass/pipeline) 下尚无 `npu_demo_lowering.md`。
- 当前失败点：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run` 当前失败于 `ADD` 正向用例，原因是 expectation 把 `"default-lowering"` 当成默认正向 pipeline，而该链路的现实前提已超出 dsl_run 最小工具合同。
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 当前通过，但依赖 `_use_dsl_run_test_target()`；这与正向 expectation 的公开前提不一致。
- 当前排序缺口：
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py) 仍要求 `symbol-loop-hoist` 先有 `tile` materialize `symbol.for`，否则拒绝执行；这与用户已确认的新 `npu-demo-lowering` 口径冲突。

## 合同真源顺序

- `expectation/tools/dsl_run > spec/tools/dsl_run.md + spec/pass/pipeline/npu_demo_lowering.md + spec/pass/pass_manager.md > test/tools/test_dsl_run.py + test/pass/test_pipeline_npu_demo_lowering.py + test/pass/test_pass_manager.py > 当前实现`

## 方案比较与选型

- 不采用方案：继续让 `dsl_run` 正向 expectation 使用 `default-lowering`，再通过 `_use_dsl_run_test_target()` 或内部隐式 target 准备来抹平差异。
  - 原因：这会继续把默认工具合同绑到历史 pipeline 前置条件上，让 expectation 与公开工具边界分叉。
- 不采用方案：把 `symbol-loop-hoist` 从新 pipeline 中移除，等后续 tile family 收口后再加。
  - 原因：用户已明确希望新的 `npu_demo` pipeline 包含 `decompass + lower-nn + symbol-loop-hoist` 三个 pass。
- 采用方案：
  - 新增 `npu-demo-lowering` pipeline，并让 `dsl_run` 正向 expectation / pytest 改用它。
  - `default-lowering` 保持公开 builder 存在，但不再作为 `dsl_run` 正向合同的默认路径。
  - `SymbolLoopHoistPass` 明确改成“无 `symbol.for` 时 no-op”，从而可安全进入 `npu-demo-lowering`。

## 公开 API 设计

- 公开工具入口：[`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py) 中的 `dsl_run`
- 公开 pipeline builder：
  - 现有：[`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py) 中的 `build_default_lowering_pipeline`
  - 新增：[`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py) 中的 `build_npu_demo_lowering_pipeline`
- 新 pipeline 注册名：
  - `"npu-demo-lowering"`
- 参数顺序：
  - `dsl_run(func, real_args, pipeline, emitcconfig)`
- 参数类型：
  - `func: Callable[..., object]`
  - `real_args: tuple[object, ...] | list[object]`
  - `pipeline: str | PassManager`
  - `emitcconfig: EmitCContext`
- `DslRunResult` 字段保持不变：
  - `func_op`
  - `module`
  - `source`
  - `compiled_kernel`
  - `execute_result`
  - `runtime_args`
- 公开行为：
  - `dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))` 是本轮唯一正向黑盒合同。
  - `npu-demo-lowering` 的 pass 顺序固定为 `decompass -> lower-nn -> symbol-loop-hoist`。
  - `SymbolLoopHoistPass` 在没有 `symbol.for` 时必须 no-op，不得因缺少 `tile` 而报错。
  - `dsl_run` 仍接受其他字符串 pipeline 或现成 `PassManager`；但这些不再是本轮正向 expectation 真源。
  - 若 DSL 函数存在值返回，必须显式失败。

```python
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.tools.dsl_run import dsl_run


def add_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    store(lhs + rhs, out, [0], [6], [1])


result = dsl_run(
    add_kernel,
    (out_tensor, lhs_tensor, rhs_array),
    "npu-demo-lowering",
    EmitCContext(target="npu_demo"),
)
assert result.execute_result.ok is True
```

## 完成态定义

- `kernel_gen.tools.dsl_run.dsl_run(...)` 公开接口保持不变。
- `kernel_gen/passes/pipeline/npu_demo_lowering.py` 已存在并注册 `"npu-demo-lowering"`。
- `npu-demo-lowering` 的顺序固定为 `DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass`。
- `SymbolLoopHoistPass` 在无 `symbol.for` 输入时为 `no-op`，不再依赖 `tile` 作为前置。
- [`expectation/tools/dsl_run/add.py`](../../expectation/tools/dsl_run/add.py) 与 [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py) 的正向用例已切换到 `"npu-demo-lowering"`。
- `spec/tools/dsl_run.md` 不再把 `default-lowering` 写成默认正向入口。
- `default-lowering` 仍保留公开 builder，但不再承担本轮 dsl_run 正向合同。

## 验收设计

- 验收资产：
  - [`expectation/tools/dsl_run`](../../expectation/tools/dsl_run)
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../test/pass/test_pipeline_npu_demo_lowering.py)
- 锁定输出：
  - `dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))` 真实执行成功
  - `out` 被 kernel 结果写回
  - `result.execute_result.ok is True`
  - `npu-demo-lowering` 顺序固定为 `decompass -> lower-nn -> symbol-loop-hoist`
  - `symbol-loop-hoist` 在无 `symbol.for` 时 no-op
- 必过命令：
  - `pytest -q test/tools/test_dsl_run.py`
  - `pytest -q test/pass/test_pass_manager.py`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.tools.dsl_run`

## 阶段拆分

### S1：dsl_run 与 npu-demo-lowering 合同收口

#### 阶段目标

- 新增 `npu-demo-lowering` pipeline，并让 `dsl_run` 的正向 expectation / pytest 切换到这条 pipeline。
- 同时收口 `SymbolLoopHoistPass` 在新 pipeline 中的最小公共边界：无 `symbol.for` 时 `no-op`。
- 保留 `default-lowering` 公开 builder，但把它从本轮 dsl_run 正向黑盒合同中移出。

#### 目标 spec / API

- [`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
- [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
- [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
- [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- [`spec/pass/registry.md`](../../spec/pass/registry.md)
- [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
- [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
- [`kernel_gen/tools/__init__.py`](../../kernel_gen/tools/__init__.py)
- [`kernel_gen/passes/pipeline/__init__.py`](../../kernel_gen/passes/pipeline/__init__.py)
- [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py)
- [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
- [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
- [`expectation/tools/dsl_run`](../../expectation/tools/dsl_run)
- [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
- [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- [`test/pass/test_pipeline_npu_demo_lowering.py`](../../test/pass/test_pipeline_npu_demo_lowering.py)

#### 禁止修改面 / 合同真源

- `禁止修改面：无额外禁止面；除 immutable 内容外，执行人可自由修改与 dsl_run / npu-demo-lowering / symbol-loop-hoist 直接相关的实现、spec、测试与必要辅助文件`
- `合同真源：expectation/tools/dsl_run > spec/tools/dsl_run.md + spec/pass/pipeline/npu_demo_lowering.md + spec/pass/pass_manager.md > test/tools/test_dsl_run.py + test/pass/test_pipeline_npu_demo_lowering.py + test/pass/test_pass_manager.py`

#### 预期示例代码

```python
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.tools.dsl_run import dsl_run


def add_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    store(lhs + rhs, out, [0], [6], [1])


result = dsl_run(
    add_kernel,
    (out_tensor, lhs_tensor, rhs_array),
    "npu-demo-lowering",
    EmitCContext(target="npu_demo"),
)
```

#### 预期输出

```text
- result.execute_result.ok == True
- result.source 包含 include/npu_demo/npu_demo.h
- out_tensor 被写成 add 结果
- npu-demo-lowering 顺序为 decompass -> lower-nn -> symbol-loop-hoist
- 没有 symbol.for 时，symbol-loop-hoist 不报错、不改写、直接 no-op
```

#### 目标验收资产

- [`expectation/tools/dsl_run`](../../expectation/tools/dsl_run)
- [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
- [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- [`test/pass/test_pipeline_npu_demo_lowering.py`](../../test/pass/test_pipeline_npu_demo_lowering.py)

#### 验收必过项目

- `pytest -q test/tools/test_dsl_run.py`
- `pytest -q test/pass/test_pass_manager.py`
- `pytest -q test/pass/test_pipeline_npu_demo_lowering.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.tools.dsl_run`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：新增 npu-demo-lowering pipeline，切换 dsl_run 正向 expectation / pytest 到该 pipeline，并把 symbol-loop-hoist 收口为无 symbol.for 时 no-op`
- `记录文件：待管理员创建`

## 待确认项

- `无`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：`
  - 接口固定为 `dsl_run(func, real_args, pipeline, emitcconfig)`
  - `real_args` 至少支持 `torch.Tensor` 与 `numpy.ndarray`
  - 内部需要有 `tensor -> Memory` 的规整类
  - 当前不支持 DSL 值返回
  - `pipeline` 同时接受注册名字符串与现成 `PassManager`
  - `emitcconfig` 固定为 [`EmitCContext`](../../kernel_gen/dsl/emit_c.py)
  - `dsl_run` 正向工具合同不再使用 `default-lowering`
  - 新增 `npu-demo-lowering` pipeline，公开顺序为 `decompass -> lower-nn -> symbol-loop-hoist`
  - `symbol-loop-hoist` 在没有 `symbol.for` 时直接 `no-op`
  - `BufferResultsToOutParamsPass` 与 `LowerDmaMemoryHierarchyPass` 都不属于这条新 pipeline
  - `expectation/tools/dsl_run` 为唯一工具合同真源，旧 `dsl_execute` 路径不再保留
- `未确认前处理要求：不适用`
- `询问记录 1：2026-04-21 已向小李飞刀发起实现收口视角询问；已收到最小需改项：若切换到新 pipeline，需要同步点名清掉 gen_kernel/emit_c 对旧 bridge 的残留假设，并明确 PassManager 中旧 tile 顺序约束的迁移边界。`
- `询问记录 2：2026-04-21 已向睡觉小分队发起 spec/合同边界视角询问；已收到最小需改项：若 default-lowering 不再承接 dsl_run 正向路径，则 spec/tools/dsl_run.md 与 pipeline spec 必须明确各自责任边界，避免工具合同与默认 pipeline 继续重叠。`
- `询问记录 3：2026-04-21 已向提莫炖蘑菇发起 review/任务推进视角询问；已收到最小需改项：最终必过命令需采用 worktree-first 环境，且 expectation 真源、计划书命令、实际 task-site 入口必须一致。`

## 参考资料

- [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
- [`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
- [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
- [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py)
- [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
- [`expectation/tools/dsl_run/add.py`](../../expectation/tools/dsl_run/add.py)
- [`expectation/tools/dsl_run/invalid_contract.py`](../../expectation/tools/dsl_run/invalid_contract.py)
- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)
