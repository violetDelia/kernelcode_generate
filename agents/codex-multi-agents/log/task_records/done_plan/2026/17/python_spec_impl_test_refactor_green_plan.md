# python_spec_impl_test_refactor_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：[`spec/`](../../spec/)
- 目标 `API`：`kernel_gen` Python 公开 API、`pytest` / `coverage` 验收入口
- 目标 `test`：[`test/`](../../test/)
- 目标 `验收资产`：`pytest -q test`、`pytest --cov=kernel_gen --cov-branch`、`python3 -m expectation`
- 目标 `功能实现`：[`kernel_gen/`](../../kernel_gen/)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260422-python-refactor-baseline-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-refactor-baseline-s1.md` |
| S2 | S1 | `wt-20260422-python-spec-cleanup-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-spec-cleanup-s2.md` |
| S3 | S2 | `wt-20260422-python-core-reuse-s3` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-core-reuse-s3.md` |
| S4 | S3 | `wt-20260422-python-pass-pipeline-reuse-s4` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-pass-pipeline-reuse-s4.md` |
| S5 | S4 | `wt-20260422-python-dsl-tool-reuse-s5` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-dsl-tool-reuse-s5.md` |
| S6 | S5 | `wt-20260422-python-test-classify-s6` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-test-classify-s6.md` |
| S7 | S6 | `wt-20260422-python-coverage-warning-s7` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-coverage-warning-s7.md` |
| S8 终验修复 | S7 | `wt-20260422-python-final-expectation-repair-s8` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-final-expectation-repair-s8.md` |
| S9 终验修复二轮 | S8 | `wt-20260422-python-final-expectation-repair-s9` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-final-expectation-repair-s9.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`守护最好的爱莉希雅复评通过：coverage 临时产物口径已统一为 coverage/S*/coverage.json，S1/S7 已补 .gitignore 忽略 coverage/ 且生成物不应进入 git 跟踪的检查；S1-S7 拆分、S4/S5 边界、spec/test expectation 脱钩迁移记录、薄包装 omit 正反判定、S7 warning 与 expectation 失败归因均已清楚。睡觉小分队与金铲铲大作战的意见已回收，当前无最小阻断项。`

## 终验 / 复验 / 修复复核记录

- 结论人：`不适用`
- 结论：`不通过`
- 验证基线：`origin/main@60fde8c0d04878832afb36a081bae4b77e4ba294`
- 最小阻断项或通过摘要：`最新同步主目录执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation 退出码 1；最小阻断项为 expectation.dsl.mlir_gen.dialect.dma.copy 的 CASE-1/CASE-2 仍失败，以及 expectation.operation.nn.img2col2d 的 CASE-3 仍触发 SystemError: attempting to create PyCMethod with a METH_METHOD flag but no class。`
- 是否已创建修复任务：`否，本次仅按最终验收请求回写结论；不推进归档，待管理员按当前结论要求补建修复任务。`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`无`

### 守护最好的爱莉希雅最终验收（2026-04-22）

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`origin/main@e83e8aece39d768ccb52e0142e5b2891d651d49b`
- 执行目录：`/home/lfr/kernelcode_generate`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 e83e8aece39d768ccb52e0142e5b2891d651d49b，tracked 文件处于最新主线现场，仅存在无关未跟踪 worktree 目录，因此直接在主目录执行终验。`
- 全量 expectation 合同验收摘要：`find expectation -name __main__.py 发现 42 个入口；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. 逐入口 python3 -m 验收，34/42 通过，失败数 8。失败入口为 expectation、expectation.dsl.mlir_gen、expectation.dsl.mlir_gen.dialect.dma、expectation.execute_engine.npu_demo、expectation.execute_engine.npu_demo.default、expectation.pass.lowing.nn_lowering.element_binary、expectation.pass.lowing.nn_lowering.img2col、expectation.tools.dsl_run。`
- 最小阻断项：`expectation.dsl.mlir_gen.dialect.dma.copy 的 CASE-1/CASE-2 仍返回比较失败；expectation.tools.dsl_run 与 expectation.execute_engine.npu_demo/default 的 add/sub/mul/matmul 链路仍出现 ExecutionEngineError: compile_failed: compiler returned non-zero (1)；expectation.pass.lowing.nn_lowering.element_binary 的 CASE-truediv dynamic#3 仍因 run_ircheck_text exit_code=2 且 message="'SubPattern' object is not callable" 失败；expectation.pass.lowing.nn_lowering.img2col 仍以 exit=-11 段错误退出。`
- 是否满足归档前置条件：`否`
- 归档处理：`不推进归档。`

### 当前唯一最终验收修复任务（2026-04-22）

- 任务号：`T-20260422-258f5c25`
- worktree：`wt-20260422-python-final-expectation-repair-s8`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/17/20260422-python-final-expectation-repair-s8.md`
- 任务类型：`build`
- 创建原因：`最新主线 origin/main@e83e8aece39d768ccb52e0142e5b2891d651d49b 最终验收不通过，全量 expectation 合同验收 34/42 通过，失败 8。`
- 最小修复目标：`收口全量 expectation 合同验收失败，包括 dma.copy CASE-1/CASE-2 比较失败；dsl_run 与 execute_engine npu_demo/default 的 add/sub/mul/matmul 链路 compile_failed；nn_lowering element_binary CASE-truediv dynamic#3 因 SubPattern 相关回归失败；nn_lowering img2col exit=-11 段错误。`
- 记录要求：`build 记录必须包含 Diff 反推自测；review 记录必须包含 Diff 反推审查；expectation 作为合同验收资产单列，不得替代 diff 反推测试。`
- 任务依赖说明：`S7 已完成并进入 DONE，任务脚本不接受 DONE 任务作为 TODO 依赖项，因此 TODO 中依赖列为空；本计划正文明确记录该任务是 S7 终验后的唯一修复任务。`

### 守护最好的爱莉希雅最终验收复核（2026-04-22）

- 结论人：`守护最好的爱莉希雅`
- 结论：`通过`
- 验证基线：`origin/main@3dea907fa5f0acaa64e3bc74c40854a726a94129`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-python-final-verify-3dea907`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 3dea907fa5f0acaa64e3bc74c40854a726a94129，但主目录存在 tracked 本地改动 kernel_gen/dsl/gen_kernel.py 与 test/dsl/test_gen_kernel.py，故改用同一最新远端提交的干净 detached worktree 复核。`
- 全量 expectation 合同验收摘要：`最新远端现场 find expectation -name __main__.py 发现 3 个入口：expectation、expectation.pass.tile、expectation.pass.tile.reduce；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. 逐入口 python3 -m 验收，3/3 通过，失败数 0。`
- 最小阻断项：`无。`
- 是否满足归档前置条件：`是`
- 归档处理建议：`可进入归档流程。`

### 大闸蟹最终验收复核（2026-04-22）

- 结论人：`大闸蟹`
- 结论：`通过`
- 验证基线：`origin/main@3dea907fa5f0acaa64e3bc74c40854a726a94129`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-python-spec-final-check-dzx`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 3dea907fa5f0acaa64e3bc74c40854a726a94129。终验前检查到主目录存在 tracked 本地改动，且已有同提交 detached worktree 也有 tracked 日志改动，因此新建同一最新远端提交的干净 detached worktree 复核。`
- 计划正文回写说明：`最新远端执行目录不存在 ARCHITECTURE/plan/python_spec_impl_test_refactor_green_plan.md；本段写回主目录现有计划草案，用于记录本轮终验事实。`
- 全量 expectation 合同验收摘要：`最新远端现场 find expectation -name __main__.py 发现 3 个入口；expectation 根递归入口 discover_case_modules 发现 2 个实际 case 模块；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation，退出码 0，全量 expectation 合同验收通过。`
- 最小阻断项：`无。`
- 是否满足归档前置条件：`是`
- 归档处理建议：`可进入归档流程。`

### 守护最好的爱莉希雅最新主线最终验收（2026-04-22）

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`origin/main@ed56513c0b1c7c38e022e6d8e6225c338935a97c`
- 执行目录：`/home/lfr/kernelcode_generate`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 ed56513c0b1c7c38e022e6d8e6225c338935a97c，tracked 文件处于最新主线现场，仅存在无关未跟踪 worktree 目录，因此直接在主目录执行终验。`
- 全量 expectation 合同验收摘要：`find expectation -name __main__.py 发现 42 个入口；首次逐入口执行时 expectation.execute_engine.npu_demo.default 单入口 300 秒超时，随后用可继续执行脚本重跑并记录单入口失败后继续执行，最终 36/42 通过，失败数 6。失败入口为 expectation、expectation.dsl.mlir_gen、expectation.dsl.mlir_gen.dialect.dma、expectation.execute_engine.npu_demo.default、expectation.pass.lowing.nn_lowering、expectation.pass.tile.analysis。`
- 最小阻断项：`expectation.dsl.mlir_gen.dialect.dma.copy 的 CASE-1/CASE-2 仍返回比较失败；expectation.execute_engine.npu_demo.default 的 ADD CASE-1 仍出现 ExecutionEngineError: compile_failed: compiler returned non-zero (1)；expectation.pass.lowing.nn_lowering 的 img2col2d(dynamic) 仍因 lower-nn 阶段 attempting to create PyCMethod with a METH_METHOD flag but no class 失败；expectation.pass.tile.analysis 的 element_compare 仍因 IR 中 NumericType.Bool 无法解析为 attribute，CASE-eq-static/eq-dynamic/ge-static/gt-dynamic 失败。`
- 是否满足归档前置条件：`否`
- 归档处理：`不推进归档。`

### 当前唯一最终验收修复任务二轮（2026-04-22）

- 任务号：`T-20260422-ee60b3f6`
- worktree：`wt-20260422-python-final-expectation-repair-s9`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/17/20260422-python-final-expectation-repair-s9.md`
- 任务类型：`build`
- 创建原因：`最新主线 origin/main@ed56513c0b1c7c38e022e6d8e6225c338935a97c 最终验收不通过，全量 expectation 合同验收 36/42 通过，失败 6。`
- 最小修复目标：`收口全量 expectation 合同验收失败，包括 dma.copy CASE-1/CASE-2 比较失败；execute_engine.npu_demo.default ADD CASE-1 compile_failed；nn_lowering img2col2d(dynamic) 在 lower-nn 阶段报 attempting to create PyCMethod with a METH_METHOD flag but no class；tile.analysis element_compare 因 IR 中 NumericType.Bool 无法解析为 attribute 失败。`
- 记录要求：`build 记录必须包含 Diff 反推自测；review 记录必须包含 Diff 反推审查；expectation 作为合同验收资产单列，不得替代 diff 反推测试。`
- 任务依赖说明：`S8 已完成并进入 DONE，任务脚本不接受 DONE 任务作为 TODO 依赖项，因此 TODO 中依赖列为空；本计划正文明确记录该任务是 S8 修复合入后最新主线终验的当前唯一修复任务。`

### 守护最好的爱莉希雅最新主线最终验收复核（2026-04-22）

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`origin/main@60fde8c0d04878832afb36a081bae4b77e4ba294`
- 执行目录：`/home/lfr/kernelcode_generate`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 60fde8c0d04878832afb36a081bae4b77e4ba294，tracked 文件处于最新主线现场，仅存在无关未跟踪 worktree 目录，因此直接在主目录执行终验。`
- 全量 expectation 合同验收摘要：`已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation，退出码 1；最新保存日志为 /tmp/python_spec_impl_root_expectation_20260422.log，顶层 discover 失败 2 个 case。另逐入口扫描 find expectation -name __main__.py 发现 42 个入口，逐入口执行结果为 39/42 通过，失败入口为 expectation、expectation.dsl.mlir_gen、expectation.dsl.mlir_gen.dialect.dma，均被 dma.copy 及顶层 discover 暴露的模块级失败拖住。`
- 最小阻断项：`expectation.dsl.mlir_gen.dialect.dma.copy 的 CASE-1/CASE-2 仍返回比较失败；expectation.operation.nn.img2col2d 的 CASE-3 仍触发 SystemError: attempting to create PyCMethod with a METH_METHOD flag but no class。`
- 是否满足归档前置条件：`否`
- 归档处理：`不推进归档。`

### 大闸蟹终验修复复核（2026-04-22）

- 结论人：`大闸蟹`
- 结论：`通过`
- 验证基线：`origin/main@60fde8c0d04878832afb36a081bae4b77e4ba294`
- 执行目录：`/home/lfr/kernelcode_generate`
- 主目录同步检查：`修复前已在主目录完成 git fetch --prune，HEAD 与 origin/main 均为 60fde8c0d04878832afb36a081bae4b77e4ba294；本轮修复直接在该最新同步现场执行。`
- 修复摘要：`按用户确认的 dma.copy target-first 口径，修正 expectation/dsl/mlir_gen/dialect/dma/copy.py 的期望 IR，并同步 spec/dialect/dma.md、spec/operation/dma.md、spec/dsl/emit_mlir.md；修正 expectation/symbol_variable/symbol_dim.py 的 CASE-6 随机样本，将 static_c 限定为 2..16，避免除数为 1 使链式除法换序断言退化。`
- 全量 expectation 合同验收摘要：`已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation，退出码 0，日志 /tmp/expectation_full_after_dma_copy_symboldim_fix.log，全量 expectation 合同验收通过。补充单项压测：dma.copy 单项通过；symbol_dim 连续 50 次通过；get_subthread_num 连续 100 次通过；img2col2d 连续 20 次通过。`
- 最小阻断项：`无。`
- 是否满足归档前置条件：`是`
- 归档处理建议：`可进入归档流程。`

### 守护最好的爱莉希雅最终验收回报（2026-04-22）

- 结论人：`守护最好的爱莉希雅`
- 结论：`通过`
- 验证基线：`origin/main@60fde8c0d04878832afb36a081bae4b77e4ba294`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-python-final-origin-main`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch；主目录 HEAD 与 origin/main 均为 60fde8c0d04878832afb36a081bae4b77e4ba294，但主目录存在本地提示词/标准改动、expectation 删除项、spec 改动和未跟踪 worktree，因此改用同一最新远端提交的干净 detached worktree 终验。最新远端现场不包含本计划书文件，本段按管理员要求写回主目录现有计划正文。`
- 全量 expectation 合同验收摘要：`已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. timeout 900 python3 -m expectation，退出码 0；仅出现 tile.analysis 相关 Python SyntaxWarning，不影响合同验收结果。`
- 最小阻断项：`无。`
- 是否满足归档前置条件：`是`
- 归档处理建议：`可进入归档流程。`

## 计划目标

- 将 `expectation/` 明确定义为开发合同验收资产，而不是项目 `spec`、项目测试或覆盖率统计对象。
- 重构 `spec/`，去除重复、过时和把 expectation 写成项目资产的声明，保留每个 Python 模块真正需要的公开合同。
- 重构 `kernel_gen/` Python 实现，优先抽公共 helper、注册表、错误处理、类型/shape/memory 工具，减少重复逻辑。
- 精简并归类 `test/`，按模块、行为和边界失败路径组织 pytest，不再通过 test 文件名、导入或文本依赖 expectation。
- 对 Python 项目代码建立覆盖率验收：line coverage 不低于 95%，branch coverage 不低于 60%。
- 尽可能消除 pytest / coverage 运行中的项目自身 warning；第三方或环境 warning 必须有明确过滤理由，不能用宽泛过滤掩盖项目 warning。

## 当前基线

- 当前公开合同：`spec/` 下约 72 个 Markdown 文件，覆盖 analysis、dialect、dsl、execute_engine、operation、pass、symbol_variable、tools 等模块；部分 spec 与当前实现、测试或新计划口径存在重复描述。
- 当前公开 API：主要 Python 项目入口在 `kernel_gen/`，当前扫描约 114 个 Python 文件；`script/` 当前仅有 shell 脚本，`skills/` 下有协作基础设施脚本，不应默认计入 kernel 项目覆盖率。
- 当前实现入口：`kernel_gen/analysis`、`kernel_gen/dialect`、`kernel_gen/dsl`、`kernel_gen/execute_engine`、`kernel_gen/operation`、`kernel_gen/passes`、`kernel_gen/symbol_variable`、`kernel_gen/tools`。
- 当前测试与验收资产：`test/` 当前约 121 个 Python 测试文件；`expectation/` 当前约 278 个 Python 合同资产，并且已有顶层 `python3 -m expectation` 入口。
- 当前覆盖率配置：根目录有 `pytest.ini`，pytest-cov 可用；当前未发现根目录 `.coveragerc` 或独立 coverage 阈值脚本。
- 当前缺口或失败点：`spec/` 与 `test/` 中仍可能出现 `expectation / expatation` 命名、文本或导入；这会把合同验收资产误写成项目规范或测试依赖。
- 当前缺口或失败点：测试数量多但分类不完全稳定，部分测试与 expectation 资产语义重叠；覆盖率目标尚未被单独度量和强制检查。

## 方案比较与选型

- 不采用方案：把 `expectation/` 迁入项目测试体系，并用 expectation 通过情况替代 pytest 覆盖率。
- 不采用原因：用户已确认 expectation 不是项目文件，只是规范开发的验证函数；它不能替代 Python 项目测试和覆盖率。
- 不采用方案：只清理 spec 文本，不重构实现与测试。
- 不采用原因：用户目标同时包含 spec 去冗余、实现复用、测试精简归类、覆盖率和 warning 收口；只改 spec 无法解决重复实现和测试噪声。
- 不采用方案：把 C++ include / runtime 也纳入覆盖率和 warning 目标。
- 不采用原因：用户已确认本轮只考虑 Python 代码，C++ 代码不考虑。
- 采用方案：先建立 Python 覆盖率与 warning 基线，再按 spec、实现复用、测试分类、覆盖率补口顺序推进；expectation 只在计划终验与合同验收中单列运行。
- 最小公开接口：`pytest`、`coverage` 和新增覆盖率检查脚本；不新增业务 API。

## 公开 API 设计

- 公开入口：`script/check_python_coverage.py`
- 参数顺序：`--coverage-json, --line-min, --branch-min, --include-module`
- 参数类型：`Path, float, float, list[str]`
- 返回值：`process exit code`

```python
# 由 pytest-cov 生成 coverage/<task-id>/coverage.json 后执行。
python3 script/check_python_coverage.py \
  --coverage-json coverage/S7/coverage.json \
  --line-min 95 \
  --branch-min 60
```

```python
# 阶段内可只检查本阶段改动模块。
python3 script/check_python_coverage.py \
  --coverage-json coverage/S4/coverage.json \
  --include-module kernel_gen.passes \
  --line-min 95 \
  --branch-min 60
```

```text
line coverage >= 95.0 and branch coverage >= 60.0
```

- 公开约束：`spec/` 与 `test/` 不得出现 `expectation` 或 `expatation` 文本、导入、文件名、目录名。

```bash
rg -n "expectation|expatation" spec test
find spec test \( -iname '*expectation*' -o -iname '*expatation*' \) -print
```

```text
# 两条命令均不应输出有效命中。
```

## 完成态定义

- `expectation/` 保留为合同验收资产；不被 `spec/` 或 `test/` 引用，不被纳入 `--cov=kernel_gen` 覆盖率统计。
- Python 覆盖率统计源确认只包括 `kernel_gen/**/*.py`；`expectation/`、`test/`、`spec/`、`agents/`、`skills/` 不纳入本轮覆盖率阈值。
- `kernel_gen` 内纯转发/薄包装文件不计入 coverage 阈值；S1 必须生成明确 `coverage omit` 清单，逐项写清路径、排除理由和覆盖率影响，S7/终验按该清单验收。
- 纯转发/薄包装定义：文件只包含模块 docstring、注释、`from ... import ...`、`import ...`、`__all__`、类型检查保护导入、简单别名绑定；不包含分支、循环、异常捕获或转换、函数/类实现、注册副作用、默认值计算、路径解析、IR 构造、字符串拼接生成、环境读取、IO、warning 过滤或任何业务判断。
- 纯转发/薄包装反例：即使文件很短，只要包含 `if/for/while/try/except/with`、非平凡函数体、装饰器注册、错误类型转换、参数规整、兼容分支、动态导入、target/pipeline 选择、CLI 参数解析或返回值改写，就必须计入 coverage。
- `spec/` 中每个 Python 模块合同只保留公开行为、输入输出、错误边界、链接和示例，不重复实现细节，不把 expectation 写成项目测试或项目文件。
- `test/` 按模块归类，文件名、测试名、fixture、导入和断言文本不再出现 `expectation / expatation`。
- `kernel_gen/` 重复逻辑被收口到公共 helper 或注册结构；执行人必须在任务记录里列出被合并的重复逻辑和保留原因。
- Python 覆盖率命令在最新同步现场达到 line coverage >= 95%，branch coverage >= 60%。
- `pytest -q test` 通过；项目自身 warning 收敛为 0，第三方或环境 warning 若仍存在，必须在 `pytest.ini` 或记录文件中说明来源和过滤理由。
- 架构师终验 / 复验 / 修复复核时仍按仓库规则运行全量 `python3 -m expectation`，但该命令只作为合同验收，不替代 pytest 与 coverage；若 expectation 失败，S7 必须单列失败归因，区分合同资产缺口、环境依赖、项目实现回归。

## 验收设计

- 验收资产：`pytest -q test`
- 输入样例：全部 Python pytest。
- 锁定输出：全部 pytest 通过，且 warning 摘要不包含项目自身 warning。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test`
- 验收资产：`coverage json`
- 输入样例：`kernel_gen` Python 项目代码。
- 锁定输出：line coverage >= 95%，branch coverage >= 60%。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test --cov=kernel_gen --cov-branch --cov-report=term-missing --cov-report=json:coverage/S7/coverage.json`
- 必过命令：`python3 script/check_python_coverage.py --coverage-json coverage/S7/coverage.json --line-min 95 --branch-min 60`
- 验收资产：`spec/test expectation 残留扫描`
- 输入样例：`spec/` 与 `test/`。
- 锁定输出：无 `expectation / expatation` 文本、导入、文件名或目录名残留。
- 必过命令：`rg -n "expectation|expatation" spec test` 不应命中有效残留。
- 必过命令：`find spec test \( -iname '*expectation*' -o -iname '*expatation*' \) -print` 不应输出有效残留。
- 验收资产：`python3 -m expectation`
- 输入样例：全部合同验收资产。
- 锁定输出：全量合同验收通过；该结果不计入 coverage 目标。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation`
- Diff 反推验证：`执行与审查阶段必须按实际改动文件补跑对应 pytest、测试脚本或可作为测试运行的本地脚本；计划命令只是最低集合；expectation 合同验收单列，不算 diff 反推测试`
- 终验 expectation：`架构师终验 / 复验 / 终验修复复核时必须在最新同步现场运行全量 expectation 合同验收`

## 阶段拆分

### S1：Python 范围、覆盖率与 warning 基线

#### 阶段目标

- 建立本轮 Python 重构的可度量基线：覆盖率统计源、coverage json、branch coverage 读取方式、warning 分类和最低验收命令。

#### 目标 spec / API

- `spec/script/pytest_config.md`
- `公开 API：script/check_python_coverage.py`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation 合同输出、C++ include/runtime 行为、无关 agents/skills 基础设施`
- `合同真源：用户口径、本计划书、pytest.ini、coverage json`

#### 预期示例代码

```bash
PYTHONPATH=. pytest -q test --cov=kernel_gen --cov-branch --cov-report=json:coverage/S1/coverage.json
python3 script/check_python_coverage.py --coverage-json tests/fixtures/coverage/pass.json --line-min 95 --branch-min 60
```

#### 预期输出

```text
coverage/S1/coverage.json generated for current baseline
check_python_coverage.py correctly accepts passing fixture and rejects failing fixtures
```

#### 目标验收资产

- `script/check_python_coverage.py`：读取 coverage json 并分别检查 line / branch 阈值。
- `script/check_python_coverage.py`：支持 `--include-module`，阶段内可只检查 `kernel_gen.passes`、`kernel_gen.dsl` 等指定模块；不传时检查全量 `kernel_gen`。
- `test/script/test_python_coverage_check.py`：覆盖阈值通过、line 不足、branch 不足、json 缺字段等路径。
- `pytest.ini` 或 coverage 配置：明确 `testpaths`、`norecursedirs`、warning 策略和 coverage 源范围。
- `agents/codex-multi-agents/log/task_records/...`：记录当前 coverage baseline 数值与 warning 分类；S1 不要求真实全仓达到 line>=95、branch>=60。
- `coverage 生成物存放口径`：执行阶段生成的 `coverage.json`、HTML 报告和历史对比文件默认放在对应 worktree 的 `coverage/<task-id>/` 下，整个 `coverage/` 目录必须由 `.gitignore` 忽略且不提交；长期可追溯摘要写入对应任务记录文件；用于单测的极小 synthetic json fixture 才允许提交到 `test/fixtures/coverage/`。

#### 验收必过项目

- `pytest -q test/script/test_python_coverage_check.py test/script/test_pytest_config.py`
- `PYTHONPATH=. pytest -q test --cov=kernel_gen --cov-branch --cov-report=json:coverage/S1/coverage.json`
- `.gitignore` 必须包含对根目录 `coverage/` 的忽略规则，且 `coverage/S1/coverage.json` 不应进入 git 跟踪。
- `python3 script/check_python_coverage.py --coverage-json tests/fixtures/coverage/pass.json --line-min 95 --branch-min 60`
- `python3 script/check_python_coverage.py --coverage-json tests/fixtures/coverage/pass.json --include-module kernel_gen.passes --line-min 95 --branch-min 60`
- `python3 script/check_python_coverage.py --coverage-json tests/fixtures/coverage/line_fail.json --line-min 95 --branch-min 60` 应失败。
- `python3 script/check_python_coverage.py --coverage-json tests/fixtures/coverage/branch_fail.json --line-min 95 --branch-min 60` 应失败。
- `阶段覆盖要求：S1 只负责生成当前 coverage/S1/coverage.json、验证阈值检查脚本逻辑、记录 baseline 与 warning 分类；真实全仓 kernel_gen line>=95、branch>=60 只在 S7 与终验强制。`
- `薄包装处理要求：S1 必须列出 kernel_gen 内纯转发/薄包装文件的 coverage omit 清单；每个条目必须按本计划“纯转发/薄包装定义”写明路径、判断依据和覆盖率影响，禁止把含业务分支、错误处理或非平凡逻辑的文件加入 omit。`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：build`
- `任务目标：建立 Python 覆盖率、branch 覆盖率与 warning 基线，并提供可测试的覆盖率阈值检查入口。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-refactor-baseline-s1.md`

### S2：spec 去冗余与 expectation 脱钩

#### 阶段目标

- 重构 `spec/`，删除重复声明、过时路径和 `expectation / expatation` 残留，只保留 Python 项目公开合同和链接关系；现有引用不能简单删除，必须迁移为项目测试、公开行为或合同验收说明三类之一。

#### 目标 spec / API

- `spec/`
- `公开 API：不新增业务 API`

#### 禁止修改面 / 合同真源

- `禁止修改面：kernel_gen 实现行为、test 断言语义、expectation 合同资产`
- `合同真源：用户口径、本计划书、当前 kernel_gen 公开 API`

#### 预期示例代码

```markdown
## 关联文件

- spec: spec/dsl/gen_kernel.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel/
```

#### 预期输出

```text
spec 描述公开行为，不引用 expectation，不重复实现细节。
```

#### 目标验收资产

- `spec/README.md` 或现有索引：明确 spec 写法、模块索引和冗余声明收口方式。
- `spec/**.md`：删除 `expectation / expatation` 残留，补齐 `spec / test / 功能实现` 链接。
- `spec 迁移记录`：列出每个被删除或改写的 expectation/expatation 引用，说明迁移到项目测试、公开行为描述、或计划终验合同验收中的哪一类。
- 残留扫描：`rg -n "expectation|expatation" spec test` 对 `spec/` 不应命中有效残留。

#### 验收必过项目

- `rg -n "expectation|expatation" spec` 不应命中有效残留。
- `python3 - <<'PY'` 本地 spec 链接检查脚本或新增 pytest，确认 spec 中的本仓库相对链接存在。
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：清理 spec 冗余声明和 expectation 残留，保留 Python 项目公开合同与链接矩阵。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-spec-cleanup-s2.md`

### S3：核心 Python 实现复用

#### 阶段目标

- 收口 `kernel_gen/dialect`、`kernel_gen/operation`、`kernel_gen/symbol_variable`、`kernel_gen/common` 中重复的类型、shape、dtype、错误和 verifier 辅助逻辑。

#### 目标 spec / API

- `spec/dialect/`
- `spec/operation/`
- `spec/symbol_variable/`
- `公开 API：现有 kernel_gen dialect / operation / symbol_variable 入口保持兼容`

#### 禁止修改面 / 合同真源

- `禁止修改面：公开 op 名称、公开类型构造语义、现有错误边界`
- `合同真源：spec/dialect、spec/operation、spec/symbol_variable、test/dialect、test/operation、test/symbol_variable`

#### 预期示例代码

```python
from kernel_gen.operation import nn

out = nn.add(lhs, rhs)
```

#### 预期输出

```text
公开调用方式和 IR 输出保持兼容，内部重复校验逻辑被公共 helper 复用。
```

#### 目标验收资产

- `test/dialect/`：dialect verifier 与类型属性行为不变。
- `test/operation/`：operation DSL 输出和错误路径不变。
- `test/symbol_variable/`：symbol/memory/type 行为不变，测试文件名和内容不出现 expectation。
- 覆盖率报告：核心模块新增分支测试优先覆盖错误边界。

#### 验收必过项目

- `pytest -q test/dialect test/operation test/symbol_variable`
- `PYTHONPATH=. pytest -q test/dialect test/operation test/symbol_variable --cov=kernel_gen --cov-branch --cov-report=json:coverage/S3/coverage.json --cov-report=term-missing`
- `python3 script/check_python_coverage.py --coverage-json coverage/S3/coverage.json --include-module kernel_gen.dialect --include-module kernel_gen.operation --include-module kernel_gen.symbol_variable --line-min 95 --branch-min 60`
- `阶段覆盖要求：本阶段只要求改动模块的 diff / 模块级覆盖不回退；全仓 kernel_gen line>=95、branch>=60 只在 S7 与终验强制。若执行人选择阶段内跑全量 coverage，也可提前按 S7 阈值自检。`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：在核心 Python API 保持兼容的前提下，抽取并复用 dialect / operation / symbol_variable 的重复校验与类型工具。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-core-reuse-s3.md`

### S4：pass 与 pipeline 实现复用

#### 阶段目标

- 收口 `kernel_gen/passes` 与 `kernel_gen/passes/pipeline` 中重复的遍历、注册、错误转换和 pass 组合逻辑，避免本阶段同时混入 DSL、tools 和 execute_engine 兼容修补。

#### 目标 spec / API

- `spec/pass/`
- `公开 API：现有 pass 名称、pipeline builder、registry 入口保持兼容`

#### 禁止修改面 / 合同真源

- `禁止修改面：公开 pass 名称、pipeline 名称、ModulePass / PassManager 兼容边界`
- `合同真源：spec/pass、test/pass`

#### 预期示例代码

```python
from kernel_gen.passes.registry import build_registered_pass

pipeline_pass = build_registered_pass("npu-demo-lowering")
```

#### 预期输出

```text
公开 pass / pipeline 调用保持兼容，内部重复遍历、注册和错误转换走共享实现。
```

#### 目标验收资产

- `test/pass/`：pass 与 pipeline 行为不变。
- `spec/pass/`：不再重复实现细节，保留公开 pass 合同、失败边界和 pipeline 组合关系。
- `pass/pipeline 复用记录`：列出被合并的重复逻辑、保留未合并逻辑及原因。

#### 验收必过项目

- `pytest -q test/pass`
- `PYTHONPATH=. pytest -q test/pass --cov=kernel_gen --cov-branch --cov-report=json:coverage/S4/coverage.json --cov-report=term-missing`
- `python3 script/check_python_coverage.py --coverage-json coverage/S4/coverage.json --include-module kernel_gen.passes --line-min 95 --branch-min 60`
- `阶段覆盖要求：本阶段只要求改动模块的 diff / 模块级覆盖不回退；全仓 kernel_gen line>=95、branch>=60 只在 S7 与终验强制。若执行人选择阶段内跑全量 coverage，也可提前按 S7 阈值自检。`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：复用 pass / pipeline 层重复遍历、注册和错误处理逻辑，保持公开 pass 与 pipeline 入口兼容。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-pass-pipeline-reuse-s4.md`

### S5：DSL、execute_engine 与工具实现复用

#### 阶段目标

- 收口 `kernel_gen/dsl`、`kernel_gen/execute_engine`、`kernel_gen/tools` 中重复的错误转换、源码生成辅助、IR 文本比较和工具入口逻辑；不再混入 pass/pipeline 重构。

#### 目标 spec / API

- `spec/dsl/`
- `spec/execute_engine/`
- `spec/tools/`
- `公开 API：现有 dsl_run、emit_c/gen_kernel、ircheck、mlir_gen_compare 入口保持兼容`

#### 禁止修改面 / 合同真源

- `禁止修改面：dsl_run 参数顺序、emit_c/gen_kernel 公开导入、ircheck 匹配语义、mlir_gen_compare 输出语义`
- `合同真源：spec/dsl、spec/execute_engine、spec/tools、test/dsl、test/execute_engine、test/tools`

#### 预期示例代码

```python
from kernel_gen.tools.dsl_run import dsl_run
```

#### 预期输出

```text
公开 DSL / tool 调用保持兼容，内部重复错误转换和文本处理走共享实现。
```

#### 目标验收资产

- `test/dsl/`：AST、MLIR 生成、emit_c/gen_kernel 行为不变。
- `test/execute_engine/`：编译、目标注册、入口 shim 行为不变。
- `test/tools/`：dsl_run、ircheck、mlir_gen_compare 行为不变。
- `DSL/tool 复用记录`：列出被合并的重复逻辑、保留未合并逻辑及原因。

#### 验收必过项目

- `pytest -q test/dsl test/execute_engine test/tools`
- `PYTHONPATH=. pytest -q test/dsl test/execute_engine test/tools --cov=kernel_gen --cov-branch --cov-report=json:coverage/S5/coverage.json --cov-report=term-missing`
- `python3 script/check_python_coverage.py --coverage-json coverage/S5/coverage.json --include-module kernel_gen.dsl --include-module kernel_gen.execute_engine --include-module kernel_gen.tools --line-min 95 --branch-min 60`
- `阶段覆盖要求：本阶段只要求改动模块的 diff / 模块级覆盖不回退；全仓 kernel_gen line>=95、branch>=60 只在 S7 与终验强制。若执行人选择阶段内跑全量 coverage，也可提前按 S7 阈值自检。`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：复用 DSL / execute_engine / tools 层重复错误转换、源码辅助和文本处理逻辑，保持公开入口兼容。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-dsl-tool-reuse-s5.md`

### S6：pytest 精简归类与 expectation 脱钩

#### 阶段目标

- 按模块和行为重新归类 `test/`，删除重复测试，保留边界失败路径；确保 test 文件名、目录名、导入和文本不再出现 `expectation / expatation`。

#### 目标 spec / API

- `agents/standard/测试文件约定.md`
- `spec/script/pytest_config.md`
- `公开 API：pytest 目录、fixture 归属与 smoke/regression marker 约定`

#### 禁止修改面 / 合同真源

- `禁止修改面：通过删除测试降低实际行为覆盖；不得用 expectation 替代 pytest；不得把合同验收资产混入项目测试命名`
- `合同真源：test/、pytest.ini、本计划书`

#### 预期示例代码

```python
def test_softmax_rejects_negative_axis():
    ...
```

#### 预期输出

```text
测试名描述项目行为，不引用 expectation。
```

#### 目标验收资产

- `test/`：按模块归档，重复 case 删除或合并，测试名和文件名不出现 expectation。
- `pytest.ini`：必要 marker 和采集规则清楚。
- `fixture 归属记录`：公共 fixture、模块 fixture、smoke/regression 边界写清，避免与 expectation suite 混线。
- `测试迁移记录`：列出被 rename / rewrite / drop 的 expectation/expatation 命名测试及其新归属。
- 残留扫描：`rg` 与 `find` 对 `test/` 不应命中 expectation / expatation。

#### 验收必过项目

- `pytest -q test`
- `rg -n "expectation|expatation" test` 不应命中有效残留。
- `find test \( -iname '*expectation*' -o -iname '*expatation*' \) -print` 不应输出有效残留。
- `PYTHONPATH=. pytest -q test --cov=kernel_gen --cov-branch --cov-report=term-missing`
- `阶段覆盖要求：S6 只要求测试重组不降低行为覆盖、不引入 expectation 残留；全仓 kernel_gen line>=95、branch>=60 只在 S7 与终验强制。若执行人选择阶段内跑全量 coverage，也可提前按 S7 阈值自检。`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：精简并归类 pytest，删除 spec/test 对 expectation 的命名和依赖残留，同时保持行为覆盖。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-test-classify-s6.md`

### S7：覆盖率、warning 与全链路收口

#### 阶段目标

- 在全仓最新 Python 现场收口覆盖率、warning、pytest、spec/test 残留扫描和全量 expectation 合同验收；本阶段单列 expectation 验收窗口与失败归因，不能让 expectation 替代 pytest 或 coverage。

#### 目标 spec / API

- `spec/script/pytest_config.md`
- `script/check_python_coverage.py`
- `公开 API：覆盖率、warning 与合同验收命令`

#### 禁止修改面 / 合同真源

- `禁止修改面：不得为满足覆盖率删除项目行为；不得通过宽泛 warning ignore 掩盖项目 warning；不得把 expectation 重新写入 spec/test`
- `合同真源：本计划书、pytest.ini、coverage json、python3 -m expectation`

#### 预期示例代码

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test --cov=kernel_gen --cov-branch --cov-report=term-missing --cov-report=json:coverage/S7/coverage.json
python3 script/check_python_coverage.py --coverage-json coverage/S7/coverage.json --line-min 95 --branch-min 60
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation
```

#### 预期输出

```text
pytest passed
line coverage >= 95.0
branch coverage >= 60.0
expectation passed
```

#### 目标验收资产

- 全量 pytest：`pytest -q test`
- 覆盖率：`coverage/S7/coverage.json` 与 `script/check_python_coverage.py`
- warning：pytest warning 摘要无项目自身 warning。
- warning 归因：项目自身 warning 必须修复；第三方或环境 warning 只能用窄范围过滤，并写清来源、触发命令和过滤理由。
- 合同验收：`python3 -m expectation`
- expectation 失败归因：若失败，必须分类为合同资产缺口、环境依赖或项目实现回归；不得把 expectation 失败当作 pytest/coverage 通过的替代说明。
- 残留扫描：`spec/` 与 `test/` 无 expectation / expatation。

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test --cov=kernel_gen --cov-branch --cov-report=term-missing --cov-report=json:coverage/S7/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S7/coverage.json --line-min 95 --branch-min 60`
- `.gitignore` 必须包含对根目录 `coverage/` 的忽略规则，且 `coverage/S7/coverage.json` 不应进入 git 跟踪。
- `rg -n "expectation|expatation" spec test` 不应命中有效残留。
- `find spec test \( -iname '*expectation*' -o -iname '*expatation*' \) -print` 不应输出有效残留。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口全量 pytest、coverage 阈值、warning、spec/test 残留扫描与全量 expectation 合同验收。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-coverage-warning-s7.md`

## 待确认项

- 问题：`覆盖率统计源是否只包括 kernel_gen/**/*.py？`
- 可选项：`A：只统计 kernel_gen；B：统计所有非 test/spec/expectation 的 Python 文件，包括 skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py；C：按模块逐步扩大统计源`
- 差异：`A 最符合当前项目代码边界，能把目标集中在 kernel 生成项目；B 会把协作基础设施脚本纳入本轮重构；C 更稳但验收口径更复杂。`
- 推荐项：`A：只统计 kernel_gen/**/*.py；agents/skills 基础设施保留自身测试，不纳入本轮覆盖率目标。`
- 当前状态：`已确认：用户选择 A，只统计 kernel_gen/**/*.py。`
- 问题：`kernel_gen 内纯转发/薄包装文件是否允许从 coverage 阈值统计中排除？`
- 可选项：`A：默认全部 kernel_gen 计入，不排除薄包装；B：允许排除纯 __all__ / import re-export / 兼容转发文件；C：按 S1 生成候选清单后再逐项确认`
- 差异：`A 最严格但可能拉低 line coverage；B 更贴近业务逻辑覆盖但容易扩大 omit；C 风险最小，先用数据决定。`
- 推荐项：`B：允许排除纯 __all__ / import re-export / 兼容转发文件，但 S1 必须生成逐项 omit 清单和影响分析。`
- 当前状态：`已确认：用户确认纯转发/薄包装文件不计入 coverage 阈值。`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：expectation 不是项目文件，只是规范开发的验证函数；spec/test 不应出现 expectation / expatation；只考虑 Python 代码，C++ 不考虑；覆盖率统计源只包括 kernel_gen/**/*.py；纯转发/薄包装文件不计入 coverage 阈值；coverage 临时生成物放在 coverage/<task-id>/ 并由 .gitignore 忽略；目标为 spec 去冗余、实现尽可能复用、测试精简归类、line coverage >= 95%、branch coverage >= 60%、尽可能消除 warning。`
- `未确认前处理要求：不适用；若后续互评或执行阶段出现 API、任务范围、验收口径、依赖顺序、保留/删除边界冲突，仍需先询问用户。`
- `若用户要求至少询问 3 人：本计划在推进前需补齐不少于 3 个对象的询问记录，并在出现不确定或分歧时交由用户裁决。`
- `询问记录 1：守护最好的爱莉希雅 / 复评通过：coverage 临时产物口径已统一为 coverage/S*/coverage.json，S1/S7 已补 .gitignore 忽略 coverage/ 且生成物不应进入 git 跟踪的检查；S1-S7 拆分、S4/S5 边界、spec/test expectation 脱钩迁移记录、薄包装 omit 正反判定、S7 warning 与 expectation 失败归因均已清楚`
- `询问记录 2：睡觉小分队 / 已回执：spec/test 清零 expectation/expatation 需要先做命名与归档迁移；pytest 精简归类需先定模块分层、fixture 归属和 smoke/regression 边界；warning 需先列项目自身与第三方来源并窄范围过滤；coverage 可执行但建议关注薄包装/转发层影响`
- `询问记录 3：金铲铲大作战 / 已回执：只统计 kernel_gen/**/*.py 合理；S4 原范围偏大，已拆成 pass/pipeline 与 DSL/tool 两段；S7 已补 expectation 独立验收窗口和失败归因规则`

## 参考资料

- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)：计划书结构、互评与终验要求。
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)：阶段正文模板。
- [`agents/standard/测试文件约定.md`](../../agents/standard/测试文件约定.md)：pytest 组织约定。
- [`pytest.ini`](../../pytest.ini)：当前 pytest 采集与 marker 配置。
- [`kernel_gen/`](../../kernel_gen/)：本轮 Python 项目实现统计源推荐范围。
- [`spec/`](../../spec/)：本轮 spec 去冗余目标。
- [`test/`](../../test/)：本轮 pytest 精简归类目标。
- [`expectation/`](../../expectation/)：合同验收资产；不属于项目 spec/test，也不计入覆盖率。
