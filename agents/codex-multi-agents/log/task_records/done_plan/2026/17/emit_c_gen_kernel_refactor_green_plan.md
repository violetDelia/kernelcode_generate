# emit_c_gen_kernel_refactor_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)、[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- 目标 `API`：`kernel_gen.dsl.gen_kernel`
- 目标 `test`：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)、[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)、[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
- 目标 `验收资产`：`pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`、`pytest -q test/tools/test_dsl_run.py`、`python3 -m expectation.execute_engine.npu_demo.kernel_only`
- 目标 `功能实现`：`kernel_gen/dsl/gen_kernel/`

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260421-emitc-entry-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260421-emitc-entry-s1.md` |
| S2 | S1 | `wt-20260421-emitc-op-type-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260421-emitc-op-type-s2.md` |
| S3 | S2 | `wt-20260421-emitc-function-module-s3` | `agents/codex-multi-agents/log/task_records/2026/17/20260421-emitc-function-module-s3.md` |
| S4 | S3 | `wt-20260421-gen-kernel-wrapper-s4` | `agents/codex-multi-agents/log/task_records/2026/17/20260421-gen-kernel-wrapper-s4.md` |
| S5 终验修复 | S4 | `wt-20260422-emitc-gen-kernel-final-repair` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-emitc-gen-kernel-final-repair.md` |
| S6 终验修复二轮 | S5 | `wt-20260422-emitc-gen-kernel-final-repair-2` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-emitc-gen-kernel-final-repair-2.md` |
| S7 终验修复三轮 | S6 | `wt-20260422-emitc-gen-kernel-final-repair-3` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-emitc-gen-kernel-final-repair-3.md` |
| S8 终验修复四轮 | S7 | `wt-20260422-emitc-gen-kernel-final-repair-4` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-emitc-gen-kernel-final-repair-4.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`守护最好的爱莉希雅已按删除 kernel_gen/dsl/emit_c.py 的最新口径复评通过；睡觉小分队已给出 spec/API 补充意见并确认 kernel_gen.dsl.gen_kernel 包根、emit_c(obj, ctx) 单一入口、emit_c_op/emit_c_value 窄接口和 gen_kernel 兼容包装关系写清；金铲铲大作战已给出实现可执行性补充意见，认为 S1-S4 依赖、旧导入迁移、残留扫描和 pytest / dsl_run / expectation 验收组合足以覆盖迁移与回归边界。`

## 终验 / 复验 / 修复复核记录

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`origin/main@544a78965aa714071aba8f2b533f1bff4b574709`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-emitc-gen-kernel-final-verify`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch；主目录 HEAD=ec0e19758d5591e05d17d790d3a5c55e5442d9a3，origin/main=544a78965aa714071aba8f2b533f1bff4b574709，且主目录存在本地改动并落后 origin/main 2 个提交，故未 fast-forward，改用最新远端 detached worktree 终验。`
- 全量合同验收摘要：`find expectation -name __main__.py` 在最新远端现场发现 2 个入口；执行全量入口 `python3 -m expectation.pass.tile` 与 `python3 -m expectation.pass.tile.reduce` 均失败，失败数 2/2。
- 最小阻断项或通过摘要：`expectation.pass.tile` 导入 `expectation.pass.tile.analysis` 失败；`expectation.pass.tile.reduce` 导入 `expectation.utils.case_runner` 失败。按最新规定，全量 expectation 未通过，不能给出计划通过结论。
- 是否已创建修复任务：`是，T-20260422-61dc6b36`
- 修复任务创建人：`守护最好的爱莉希雅`
- 另一位架构师补充重点：`无`

### 大闸蟹终验复核（2026-04-22）

- 结论人：`大闸蟹`
- 结论：`不通过`
- 验证基线：`origin/main@544a78965aa714071aba8f2b533f1bff4b574709`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-emit-c-final-check-temp`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD=ec0e19758d5591e05d17d790d3a5c55e5442d9a3，origin/main=544a78965aa714071aba8f2b533f1bff4b574709，主目录落后 origin/main 2 个提交且存在本地改动，未直接快进，改用最新远端 detached worktree 终验。`
- 计划正文回写说明：`最新远端执行目录不存在 ARCHITECTURE/plan/emit_c_gen_kernel_refactor_green_plan.md，ARCHITECTURE/plan 目录也不存在；本段写回主目录现有计划草案，用于记录本轮终验事实。`
- 全量合同验收摘要：`最新远端执行目录中 find expectation -name __main__.py 仅发现 expectation/pass/tile/__main__.py 与 expectation/pass/tile/reduce/__main__.py；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile 与 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile.reduce，结果均失败，失败数 2/2。`
- 最小阻断项：`最新远端执行目录缺失本计划书路径，无法在最新远端现场完成同路径正文回写；expectation.pass.tile 导入 expectation.pass.tile.analysis 失败，expectation.pass.tile.reduce 导入 expectation.utils.case_runner 失败。按终验规则，全量 expectation 未通过时不能给出通过结论。`
- 是否满足归档前置条件：`否`
- 后续处理建议：`先将本计划书与对应完成链路同步到 origin/main，并修复最新远端 expectation 可发现入口的导入缺口；之后重新执行计划终验。`

### 上一轮终验修复任务（2026-04-22）

- 任务号：`T-20260422-61dc6b36`
- worktree：`wt-20260422-emitc-gen-kernel-final-repair`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/17/20260422-emitc-gen-kernel-final-repair.md`
- 任务类型：`build`
- 最小修复目标：`在最新远端现场修复全量 expectation 合同验收失败；expectation.pass.tile.analysis 已按用户确认删除，不应补回，需改为收口 expectation.pass.tile 聚合入口仍引用已删除 analysis 资产的问题，并收口 expectation.pass.tile.reduce 缺 expectation.utils.case_runner。`
- 记录要求：`build 记录必须包含 Diff 反推自测；review 记录必须包含 Diff 反推审查；expectation 作为合同验收资产单列，不得替代 diff 反推测试。`

### 守护最好的爱莉希雅最终终验复核（2026-04-22）

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`origin/main@60433b048ed1b3fc7e715fd5a0384c3e8dbfef8f`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-emitc-gen-kernel-final-recheck-60433b`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch；主目录 HEAD=ec0e19758d5591e05d17d790d3a5c55e5442d9a3，origin/main=60433b048ed1b3fc7e715fd5a0384c3e8dbfef8f，主目录落后 origin/main 3 个提交且存在本地改动，未直接快进，改用最新远端 detached worktree 终验。`
- 计划正文回写说明：`最新远端执行目录不存在 ARCHITECTURE/plan/emit_c_gen_kernel_refactor_green_plan.md，本段写回主目录现有计划草案，用于记录本轮终验事实。`
- 全量合同验收摘要：`最新远端执行目录中 find expectation -name __main__.py 发现 2 个入口：expectation.pass.tile 与 expectation.pass.tile.reduce；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. 逐入口 python3 -m 验收，失败数 2/2。`
- 最小阻断项：`expectation.pass.tile 聚合入口仍引用用户已确认删除的 expectation.pass.tile.analysis，导致入口非零退出；expectation.pass.tile.reduce 导入 expectation.utils.case_runner 所在包 expectation.utils 失败。按终验规则，全量 expectation 未通过时不能给出通过结论。`
- 是否满足归档前置条件：`否`
- 归档处理：`不推进归档。`
- 修复任务状态：`T-20260422-61dc6b36 已合入至最新远端基线 60433b048ed1b3fc7e715fd5a0384c3e8dbfef8f，但本轮复核显示同一组全量 expectation 导入阻断仍存在，需要继续按管理员规则处理修复。`

### 大闸蟹最终终验复核（2026-04-22）

- 结论人：`大闸蟹`
- 结论：`不通过`
- 验证基线：`origin/main@60433b048ed1b3fc7e715fd5a0384c3e8dbfef8f`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-emitc-gen-kernel-final-check-60433b-dzx`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD=ec0e19758d5591e05d17d790d3a5c55e5442d9a3，origin/main=60433b048ed1b3fc7e715fd5a0384c3e8dbfef8f，主目录落后 origin/main 3 个提交且存在本地改动，未直接快进，改用最新远端 detached worktree 终验。`
- 计划正文回写说明：`最新远端执行目录不存在 ARCHITECTURE/plan/emit_c_gen_kernel_refactor_green_plan.md，无法在验证现场同路径回写；本段写回主目录现有计划草案，用于记录本轮终验事实。`
- 全量合同验收摘要：`最新远端执行目录中 find expectation -name __main__.py 仅发现 2 个入口：expectation/pass/tile/__main__.py 与 expectation/pass/tile/reduce/__main__.py；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile 与 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile.reduce，结果均失败，失败数 2/2。`
- 最小阻断项：`expectation.pass.tile 聚合入口仍引用用户已确认删除的 expectation.pass.tile.analysis，导致入口非零退出；expectation.pass.tile.reduce 导入 expectation.utils.case_runner 失败。按终验规则，全量 expectation 未通过时不能给出通过结论。`
- 是否满足归档前置条件：`否`
- 归档处理：`不推进归档。`
- 修复任务状态：`T-20260422-61dc6b36 已合入至最新远端基线 60433b048ed1b3fc7e715fd5a0384c3e8dbfef8f，但本轮复核仍复现相同 expectation 导入阻断；需要继续按管理员规则处理修复。`

### 上一轮终验修复任务二轮（2026-04-22）

- 任务号：`T-20260422-f44845c6`
- worktree：`wt-20260422-emitc-gen-kernel-final-repair-2`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/17/20260422-emitc-gen-kernel-final-repair-2.md`
- 任务类型：`build`
- 创建原因：`T-20260422-61dc6b36 已合入，但最新远端 origin/main@60433b048ed1b3fc7e715fd5a0384c3e8dbfef8f 仍复现全量 expectation 导入阻断。用户已确认 expectation.pass.tile.analysis 是已删除资产，不应视为需补回的缺陷。`
- 最小修复目标：`在最新远端现场收口 expectation.pass.tile 聚合入口仍引用已删除 analysis 资产的问题，并收口 expectation.utils.case_runner 缺失，确保 python3 -m expectation.pass.tile 与 python3 -m expectation.pass.tile.reduce 可导入并通过。`
- 记录要求：`build 记录必须包含 Diff 反推自测；review 记录必须包含 Diff 反推审查；expectation 作为合同验收资产单列，不得替代 diff 反推测试。`
- 任务依赖说明：`任务脚本不接受已移入 DONE 的 T-20260422-61dc6b36 作为 TODO 依赖项，因此 TODO 中依赖列为空；本计划正文明确记录该任务是 T-20260422-61dc6b36 合入后的二轮终验修复。`

### 守护最好的爱莉希雅最新主线终验复核（2026-04-22）

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`origin/main@f5bfc65e462e63d4e58780f222a5f68a3ee13a67`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-emitc-gen-kernel-final-recheck-f5bfc65`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch；主目录 HEAD=ec0e19758d5591e05d17d790d3a5c55e5442d9a3，origin/main=f5bfc65e462e63d4e58780f222a5f68a3ee13a67，主目录落后 origin/main 4 个提交且存在本地改动，未直接快进，改用最新远端 detached worktree 终验。`
- 计划正文回写说明：`最新远端执行目录不存在 ARCHITECTURE/plan/emit_c_gen_kernel_refactor_green_plan.md，无法在验证现场同路径回写；本段写回主目录现有计划草案，用于记录本轮终验事实。`
- 全量合同验收摘要：`最新远端执行目录中 find expectation -name __main__.py 发现 2 个入口：expectation.pass.tile 与 expectation.pass.tile.reduce；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. 逐入口 python3 -m 验收，失败数 2/2。`
- 最小阻断项：`expectation.pass.tile 聚合入口仍引用用户已确认删除的 expectation.pass.tile.analysis，导致入口非零退出；expectation.pass.tile.reduce 导入 expectation.utils.case_runner 时缺少 expectation.utils 包。按终验规则，全量 expectation 未通过时不能给出通过结论。`
- 是否满足归档前置条件：`否`
- 归档处理：`不推进归档。`
- 修复任务状态：`T-20260422-f44845c6 已合入至最新远端基线 f5bfc65e462e63d4e58780f222a5f68a3ee13a67，但本轮复核仍复现 expectation.pass.tile.analysis 与 expectation.utils.case_runner 相关导入阻断；需要继续按管理员规则处理修复。`

### 当前唯一终验修复任务三轮（2026-04-22）

- 任务号：`T-20260422-808a1002`
- worktree：`wt-20260422-emitc-gen-kernel-final-repair-3`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/17/20260422-emitc-gen-kernel-final-repair-3.md`
- 任务类型：`build`
- 创建原因：`T-20260422-f44845c6 已合入，但最新远端 origin/main@f5bfc65e462e63d4e58780f222a5f68a3ee13a67 仍复现全量 expectation 导入阻断。`
- 最小修复目标：`收口 expectation.pass.tile 聚合入口仍引用已删除 expectation.pass.tile.analysis 的问题，并收口 expectation.pass.tile.reduce 导入 expectation.utils.case_runner 时缺少 expectation.utils 包的问题，确保 python3 -m expectation.pass.tile 与 python3 -m expectation.pass.tile.reduce 可导入并通过。`
- 记录要求：`build 记录必须包含 Diff 反推自测；review 记录必须包含 Diff 反推审查；expectation 作为合同验收资产单列，不得替代 diff 反推测试。`
- 任务依赖说明：`T-20260422-f44845c6 已在 DONE，任务脚本不接受 DONE 任务作为 TODO 依赖项，因此 TODO 中依赖列为空；本计划正文明确记录该任务是 T-20260422-f44845c6 合入后的三轮终验修复。`

### 大闸蟹本地修复补充（2026-04-22）

- 用户确认：`expectation.pass.tile.analysis` 已删除，不属于需补回缺陷；修复方向应为聚合入口不再引用该已删除目录。
- 本地修复：[`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py) 已收口为动态发现当前有效的 `elewise` / `reduce` 子目录入口，不再静态导入 `analysis`。
- 本地验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile`、`python3 -m expectation.pass.tile.elewise`、`python3 -m expectation.pass.tile.reduce`、`python3 expectation/pass/tile/__main__.py` 均通过。
- 其他 case 检查：`elewise` / `reduce` 有效子目录的相对导入检查通过；扫描未发现有效入口继续引用 `expectation.pass.tile.analysis`。
- 说明：本段只记录当前工作目录中的 expectation 修复事实，不替代最新主线现场的计划终验；归档前仍需按规则在最新同步现场运行全量 expectation 合同验收。

### 大闸蟹最新主线终验复核（2026-04-22）

- 结论人：`大闸蟹`
- 结论：`不通过`
- 验证基线：`origin/main@d86f9189f1376a36d754eb0b4b082a57462615a2`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260422-emitc-gen-kernel-final-recheck-d86f918-dzx`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 d86f9189f1376a36d754eb0b4b082a57462615a2，但主目录存在本地改动，故改用同一最新提交的干净 detached worktree 复核。`
- 全量 expectation 合同验收摘要：`最新同步现场无 expectation.__main__ 根入口；find expectation -name __main__.py 仅发现 expectation/pass/tile/__main__.py 与 expectation/pass/tile/reduce/__main__.py。已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile 与 python3 -m expectation.pass.tile.reduce，失败数 2/2。`
- 最小阻断项：`expectation.pass.tile 聚合入口仍静态导入用户已确认删除的 expectation.pass.tile.analysis；这不是 analysis 缺失缺陷，而是聚合入口仍引用已删除资产。expectation.pass.tile.reduce 仍因缺少 expectation.utils / expectation.utils.case_runner 导入失败。`
- 是否满足归档前置条件：`否`
- 归档处理：`不推进归档。`

### 当前唯一终验修复任务四轮（2026-04-22）

- 任务号：`T-20260422-ffb4bf50`
- worktree：`wt-20260422-emitc-gen-kernel-final-repair-4`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/17/20260422-emitc-gen-kernel-final-repair-4.md`
- 任务类型：`build`
- 创建原因：`T-20260422-808a1002 已完成 merge，最新合并提交 d86f918 后，emit_c_gen_kernel_refactor_green_plan 复核仍不通过。`
- 最小修复目标：`收口 expectation.pass.tile 聚合入口仍引用已删除 expectation.pass.tile.analysis 的问题，并收口 expectation.pass.tile.reduce 导入 expectation.utils.case_runner 时缺少 expectation.utils 包的问题，确保 python3 -m expectation.pass.tile 与 python3 -m expectation.pass.tile.reduce 可导入并通过。`
- 记录要求：`build 记录必须包含 Diff 反推自测；review 记录必须包含 Diff 反推审查；expectation 作为合同验收资产单列，不得替代 diff 反推测试。`
- 任务依赖说明：`T-20260422-808a1002 已完成 merge，任务脚本不接受 DONE 任务作为 TODO 依赖项，因此 TODO 中依赖列为空；本计划正文明确记录该任务是 d86f918 合入后的四轮终验修复。`

### 守护最好的爱莉希雅最新主线终验复核（2026-04-22）

- 结论人：`守护最好的爱莉希雅`
- 结论：`通过`
- 验证基线：`origin/main@c66b403855d1b884ac4fcd9023e73086566134e7`
- 执行目录：`/home/lfr/kernelcode_generate`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 c66b403855d1b884ac4fcd9023e73086566134e7，tracked 文件已处于最新主线现场，仅存在无关未跟踪 worktree 目录，因此直接在主目录执行终验。`
- 全量 expectation 合同验收摘要：`find expectation -name __main__.py 发现 42 个入口；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. 逐入口 python3 -m 验收，42/42 通过，失败数 0。`
- 最小阻断项：`无。此前 expectation.pass.tile 静态引用已删除 expectation.pass.tile.analysis、expectation.pass.tile.reduce 缺 expectation.utils.case_runner 的阻断已在最新主线收口。`
- 是否满足归档前置条件：`是`
- 归档处理建议：`可进入归档流程。`

### 大闸蟹最新主线终验复核（2026-04-22）

- 结论人：`大闸蟹`
- 结论：`通过`
- 验证基线：`origin/main@c66b403855d1b884ac4fcd9023e73086566134e7`
- 执行目录：`/home/lfr/kernelcode_generate`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 c66b403855d1b884ac4fcd9023e73086566134e7，tracked 文件已处于最新主线现场，仅存在无关未跟踪 worktree 目录，因此直接在主目录执行终验。`
- 全量 expectation 合同验收摘要：`find expectation -name __main__.py 发现 42 个入口；expectation 根递归入口 discover_case_modules 发现 194 个实际 case 模块；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation，退出码 0，全量 expectation 合同验收通过。`
- 最小阻断项：`无。此前 expectation.pass.tile 静态引用已删除 expectation.pass.tile.analysis、expectation.pass.tile.reduce 缺 expectation.utils.case_runner 的阻断已在最新主线收口。`
- 是否满足归档前置条件：`是`
- 归档处理建议：`可进入归档流程。`

## 计划目标

- 新增公开入口 `emit_c(obj, ctx)`，由 `emit_c` 统一负责 target / dialect / op / type / `func.func` / `builtin.module` 源码生成。
- 保留 `gen_kernel(op_or_func, ctx)` 作为兼容入口，但实现上只调用 `emit_c(op_or_func, ctx)`，不再保留独立 target 或函数级发射逻辑。
- 抽出 `EmitCContext` 的状态实现，并统一从 `kernel_gen.dsl.gen_kernel` 包根对外导出；不保留 `kernel_gen/dsl/emit_c.py` 兼容文件。
- 将当前 `gen_kernel.py` 内的 npu_demo launch/body/wrapper、body-level kernel、CPU conv2d tiled、tile codegen 校验与默认函数体遍历迁入 `emit_c` 内部源码发射层。
- 不改变 IR 语义、不改变 lowering / pipeline 顺序、不新增后端 helper 公开合同；本轮只重排 codegen 职责与公开入口。

## 当前基线

- 当前公开合同：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 主要定义单 op / value 片段发射；[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 定义完整函数与 npu_demo module 源码生成。
- 当前公开 API：`kernel_gen.dsl.emit_c` 导出 `EmitCContext`、`EmitCError`、`emit_c_op`、`emit_c_value`；`kernel_gen.dsl.gen_kernel` 导出 `GenKernelError`、`gen_kernel`。
- 当前实现入口：[`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 已包含大量 target/op 片段规则；[`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 仍包含 `_KernelEmitter`、函数策略、type/space 翻译、npu_demo 专项、tile 专项与 CPU conv 专项。
- 当前 spec 缺口：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 与 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 仍会把 `kernel_gen/dsl/emit_c.py` 或 `kernel_gen.dsl.emit_c` 写成公开实现或导入口径；执行阶段必须改为只承认 `kernel_gen.dsl.gen_kernel` 包根导出。
- 当前删除边界：本轮完成后不保留 `kernel_gen/dsl/emit_c.py` 文件，旧 `kernel_gen.dsl.emit_c` 导入必须迁移到 `kernel_gen.dsl.gen_kernel`。
- 当前旧导入消费面：`kernel_gen/tools/ircheck.py`、`kernel_gen/tools/dsl_run.py`、[`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)、[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)、[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)、[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)、`expectation/tools/dsl_run/*`、`expectation/execute_engine/npu_demo/kernel_only/*`、`expectation/execute_engine/npu_demo/default/*` 等仍可能引用旧 `kernel_gen.dsl.emit_c`，执行阶段必须同步迁移。
- 当前测试与验收资产：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py) 覆盖片段发射；[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 覆盖完整函数、npu_demo module、tile codegen 和错误路径；`dsl_run` 与 execute_engine expectation 间接消费 `gen_kernel`。
- 当前缺口或失败点：`gen_kernel.py` 承担过多 emit_c 职责，导致 target/type/op 翻译与函数级源码策略分散；新增 target 或 dialect 规则时需要同时理解两层实现，维护边界不清楚；当前还缺少按 dialect/op 注册的发射结构。

## 方案比较与选型

- 不采用方案：只在内部把 `gen_kernel` 调用改薄，但不新增公开 `emit_c(obj, ctx)`。
- 不采用原因：用户已确认需要新增公开 `emit_c(obj, ctx)`，且希望 `gen_kernel` 只调用 emitc 实现。
- 不采用方案：只新增 `kernel_gen/dsl/emit_c_impl/` 内部目录。
- 不采用原因：用户已指定希望 `gen_kernel`、`emit_context`、`emit_c_register` 与 dialect 发射模块整合在一个文件夹中。
- 采用方案：把 `kernel_gen/dsl/gen_kernel.py` 迁成 `kernel_gen/dsl/gen_kernel/` 包；包内放置 `gen_kernel.py`、`emit_context.py`、`emit_c/` 子包与注册装饰器；删除 `kernel_gen/dsl/emit_c.py`，不保留旧兼容导出文件。
- 最小公开接口：`emit_c(obj, ctx) -> str`，其中 `obj` 可为单 op、`func.func` 或受控 `builtin.module`；内部 op 发射通过 `@emit_c_impl(<op type>)` 注册。

## 目标目录结构

```text
kernel_gen/dsl/
  gen_kernel/                    # 本轮 codegen 主实现目录
    __init__.py                  # 公开导出：GenKernelError / gen_kernel / EmitCContext / EmitCError / emit_c / emit_c_op / emit_c_value
    gen_kernel.py                # gen_kernel 兼容包装与错误转换
    emit_context.py              # EmitCContext 状态实现
    emit_c/
      __init__.py                # emit_c / emit_c_op / emit_c_value 统一入口
      register.py                # emit_c_impl 注册装饰器与 dispatch
      types.py                   # type / space 文本转换
      function.py                # func.func / builtin.module / npu_demo / tile / CPU conv 策略
      symbol.py                  # symbol dialect 发射实现
      kernel.py                  # kernel dialect 发射实现
      dma.py                     # dma dialect 发射实现
      nn.py                      # nn dialect 发射实现
      arch.py                    # arch dialect 发射实现
      arith.py                   # arith dialect 发射实现
      scf.py                     # scf / symbol.for 循环发射实现
```

- `kernel_gen/dsl/gen_kernel.py` 文件与 `kernel_gen/dsl/gen_kernel/` 目录不能长期并存；执行阶段必须完成包式迁移并保持 `import kernel_gen.dsl.gen_kernel` 结果为新包。
- `kernel_gen/dsl/emit_c.py` 不再保留；执行阶段必须同步迁移仓内所有 `kernel_gen.dsl.emit_c` 导入。
- 用户草稿中的 `emict / emictc` 统一按本仓库公开命名收口为 `emit_c`；内部装饰器命名为 `emit_c_impl`。
- dialect 模块中使用注册装饰器，例如 `@emit_c_impl(SymbolAddOp)`，随后 `emit_c(symbol_add_op, ctx)` 可通过注册表找到对应实现。

## 公开 API 设计

- 单一源码发射入口：`emit_c(obj, ctx)`
- 参数顺序：`obj, ctx`
- 参数类型：`obj: object`，`ctx: EmitCContext`
- 返回值：`str`
- 错误类型：直接调用 `emit_c(...)` 时抛 `EmitCError`；通过 `gen_kernel(...)` 调用时保持旧公开错误类型 `GenKernelError`。
- 窄接口：`emit_c_op(op, ctx)` 只服务单 op 片段发射，内部必须走与 `emit_c(...)` 相同的注册表与 `EmitCContext`，不是第二套实现入口。
- 窄接口：`emit_c_value(value, ctx)` 只服务 value 右值表达式发射，内部必须走与 `emit_c(...)` 相同的命名、type 与 dispatch 规则，不能形成独立旧入口。
- 兼容包装：`gen_kernel(op_or_func, ctx)` 保持历史函数名和参数顺序，只调用 `emit_c(op_or_func, ctx)` 并做错误类型转换；它不是新的实现分支。
- 错误转换规则：`gen_kernel(...)` 调用 `emit_c(...)` 时必须捕获 `EmitCError` 并转换为 `GenKernelError`，不得向旧调用方泄漏 `EmitCError`；legacy 私有入口/属性拒绝仍保持旧 `AttributeError` 公开行为。
- 公开导入规则：以上全部从 `kernel_gen.dsl.gen_kernel` 包根导入；`kernel_gen.dsl.emit_c` 与 `kernel_gen/dsl/emit_c.py` 不再作为公开导入或实现路径。

```python
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c
from kernel_gen.dsl.gen_kernel import gen_kernel

ctx = EmitCContext(target="npu_demo")
source = emit_c(module_op, ctx)
legacy_source = gen_kernel(module_op, EmitCContext(target="npu_demo"))
assert legacy_source == source
```

```python
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op, emit_c_value

ctx = EmitCContext(target="cpu")
stmt = emit_c_op(op, ctx)
expr = emit_c_value(value, ctx)
```

## 完成态定义

- `kernel_gen.dsl.gen_kernel.__all__` 包含 `GenKernelError`、`gen_kernel`、`EmitCContext`、`EmitCError`、`emit_c`、`emit_c_op`、`emit_c_value`。
- `kernel_gen.dsl.emit_c` 不再作为公开模块存在；仓内引用必须迁移。
- [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 与 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 的文档信息、公开接口、示例导入、功能实现链接全部改为 `kernel_gen.dsl.gen_kernel` 包根与 `kernel_gen/dsl/gen_kernel/` 目录，不再出现有效旧公开导入口径。
- `emit_c(func_op, ctx)` 与 `gen_kernel(func_op, ctx)` 对同一合法输入输出一致。
- `emit_c(module_op, EmitCContext(target="npu_demo"))` 输出与旧 `gen_kernel` npu_demo module 合同一致，包括 include、body、wrapper 与 launch 调用。
- `kernel_gen/dsl/gen_kernel/gen_kernel.py` 不再保存 `_KernelEmitter`、type/space 翻译、npu_demo 专项、tile 专项或 CPU conv 专项实现；这些逻辑迁入 `kernel_gen/dsl/gen_kernel/emit_c/`。
- `gen_kernel(...)` 对旧调用方只暴露 `GenKernelError` 作为 codegen 失败类型；内部 `EmitCError` 必须被转换。
- 新公开导入路径统一为 `kernel_gen.dsl.gen_kernel`；旧 `kernel_gen.dsl.emit_c` 导入删除，不作为兼容目标。
- 旧导入残留扫描必须不命中有效旧导入：`rg -n "kernel_gen\\.dsl\\.emit_c|from kernel_gen\\.dsl\\.emit_c|import kernel_gen\\.dsl\\.emit_c" kernel_gen test spec expectation script ARCHITECTURE`。

## 验收设计

- 验收资产：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
- 输入样例：单 op、`func.func`、受控 npu_demo `builtin.module`。
- 锁定输出：`emit_c(...)` 公开入口、op/value 片段兼容、错误类型与源码关键片段。
- 验收资产：[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 输入样例：rewrite 后 CPU function、tile after-IR function、npu_demo module、CPU conv 专项。
- 锁定输出：`gen_kernel(...)` 兼容入口输出不变，错误仍表现为 `GenKernelError`。
- 验收资产：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)、[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- 输入样例：文档信息、公开接口、示例导入、功能实现链接。
- 锁定输出：只保留 `kernel_gen.dsl.gen_kernel` 包根公开导入口径，并写清 `emit_c` 是单一源码发射入口、`emit_c_op` / `emit_c_value` 是窄接口、`gen_kernel` 是兼容包装。
- 验收资产：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)、`python3 -m expectation.execute_engine.npu_demo.kernel_only`
- 输入样例：`dsl_run + npu-demo-lowering + EmitCContext(target="npu_demo")`。
- 锁定输出：execute_engine 链路仍可生成源码、编译并执行。
- 必过命令：`pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`
- 必过命令：`pytest -q test/tools/test_dsl_run.py`
- 必过命令：`python3 -m expectation.execute_engine.npu_demo.kernel_only`
- 必过命令：`rg -n "kernel_gen\\.dsl\\.emit_c|from kernel_gen\\.dsl\\.emit_c|import kernel_gen\\.dsl\\.emit_c" kernel_gen test spec expectation script ARCHITECTURE` 不应命中有效旧导入。

## 阶段拆分

### S1：包式目录与公开入口收口

#### 阶段目标

- 将 `kernel_gen/dsl/gen_kernel.py` 迁为 `kernel_gen/dsl/gen_kernel/` 包，新增 `emit_c(obj, ctx)` 公开入口，并把 `EmitCContext` 的状态实现迁入 `emit_context.py`，同时删除旧 `kernel_gen/dsl/emit_c.py` 导入路径。

#### 目标 spec / API

- `spec/dsl/emit_c.md`
- `spec/dsl/gen_kernel.md`
- `公开 API：emit_c(obj, ctx)`、`EmitCContext`

#### 禁止修改面 / 合同真源

- `禁止修改面：.skills、无关 pass / lowering / include 运行时实现`
- `合同真源：spec/dsl/emit_c.md、spec/dsl/gen_kernel.md、test/dsl/test_emit_c.py、test/dsl/test_gen_kernel.py`

#### 预期示例代码

```python
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c

source = emit_c(func_op, EmitCContext(target="cpu"))
```

#### 预期输出

```text
emit_c(func_op, ctx) returns the same source text as gen_kernel(func_op, ctx) for the minimal covered function case.
```

#### 目标验收资产

- `test/dsl/test_emit_c.py`：新增 `emit_c` 公开导出与最小 `func.func` 成功样例。
- `test/dsl/test_gen_kernel.py`：确认 `gen_kernel` 旧导出不变。
- `spec/dsl/emit_c.md`：文档信息、功能实现链接与示例导入改为 `kernel_gen.dsl.gen_kernel` 包根，不再把 `kernel_gen/dsl/emit_c.py` 写成实现文件。
- `spec/dsl/gen_kernel.md`：公开 API 说明改为 `gen_kernel` 是兼容包装，`emit_c` 是单一源码发射入口，二者不再表达为并行实现入口。
- 目录检查：`kernel_gen/dsl/gen_kernel/` 存在，`kernel_gen/dsl/gen_kernel.py` 已完成包式迁移后不再作为主要实现文件存在。
- 导入迁移检查：`kernel_gen/tools/ircheck.py`、`kernel_gen/tools/dsl_run.py`、`test/dsl/test_emit_c.py`、`test/dsl/test_gen_kernel.py`、`test/tools/test_dsl_run.py` 必须改用 `kernel_gen.dsl.gen_kernel`。

#### 验收必过项目

- `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py -k "emit_c or public or gen_kernel_public"`
- `rg -n "kernel_gen\\.dsl\\.emit_c|from kernel_gen\\.dsl\\.emit_c|import kernel_gen\\.dsl\\.emit_c" kernel_gen test spec expectation script ARCHITECTURE` 不应命中有效旧导入。

#### 任务新建建议

- `任务类型：build`
- `任务目标：完成 gen_kernel 包式目录、emit_c(obj, ctx) 公开入口、上下文模块与导出兼容测试。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260421-emitc-entry-s1.md`

### S2：type / space / op 发射迁移

#### 阶段目标

- 把 type/space 翻译和 op/value 片段发射整理到 `kernel_gen/dsl/gen_kernel/emit_c/`，通过 `register.py` 与 `@emit_c_impl(<op type>)` 注册接入，移除旧 `gen_kernel.py` 中重复的 type/space 规则。

#### 目标 spec / API

- `spec/dsl/emit_c.md`
- `spec/dsl/gen_kernel.md`
- `公开 API：emit_c_op(op, ctx)`、`emit_c_value(value, ctx)`、`emit_c(obj, ctx)`

#### 禁止修改面 / 合同真源

- `禁止修改面：无关 dialect 定义、无关 operation DSL、include 运行时实现`
- `合同真源：test/dsl/test_emit_c.py、test/dsl/test_gen_kernel.py`

#### 预期示例代码

```python
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op

stmt = emit_c_op(kernel_binary_elewise_op, EmitCContext(target="npu_demo"))
```

#### 预期输出

```text
npu_demo::add<...>(out, lhs, rhs);
```

#### 目标验收资产

- `test/dsl/test_emit_c.py`：覆盖原有 op/value 片段输出不变。
- `test/dsl/test_gen_kernel.py`：覆盖函数签名 type/space 输出不变。
- 注册结构检查：`symbol.py`、`kernel.py`、`dma.py` 至少使用 `@emit_c_impl(...)` 接入，后续 dialect 模块按同一方式扩展。

#### 验收必过项目

- `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：把 type/space 与 op/value 发射迁入 kernel_gen/dsl/gen_kernel/emit_c/ 注册结构，并保持旧输出一致。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260421-emitc-op-type-s2.md`

### S3：函数与 module 策略迁移

#### 阶段目标

- 把 `_KernelEmitter` 现有职责迁入 `kernel_gen/dsl/gen_kernel/emit_c/function.py`，覆盖默认函数、npu_demo module、npu_demo body-level、CPU conv2d tiled 与 tile codegen。

#### 目标 spec / API

- `spec/dsl/emit_c.md`
- `spec/dsl/gen_kernel.md`
- `公开 API：emit_c(obj, ctx)`

#### 禁止修改面 / 合同真源

- `禁止修改面：不改 lowering pass 顺序；不新增 pipeline；不改变 IR 合法输入集合`
- `合同真源：test/dsl/test_gen_kernel.py、test/tools/test_dsl_run.py、expectation.execute_engine.npu_demo.kernel_only`

#### 预期示例代码

```python
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c

source = emit_c(npu_demo_module, EmitCContext(target="npu_demo"))
```

#### 预期输出

```text
#include "include/npu_demo/npu_demo.h"

static void <body>(npu_demo::KernelContext& ctx, ...)
void <wrapper>(...) { npu_demo::launch<1, 4, 1>(<body>, ...); }
```

#### 目标验收资产

- `test/dsl/test_emit_c.py`：直接验证 `emit_c(func/module)`。
- `test/dsl/test_gen_kernel.py`：保持原 `gen_kernel` 黑盒样例全部通过。
- `test/dsl/test_gen_kernel.py`：分别覆盖 npu_demo launch/body/wrapper、tile codegen、CPU conv2d tiled 三条子链，不能只依赖总包通过。
- `test/tools/test_dsl_run.py`：确认工具链仍通过 `gen_kernel` 兼容入口生成源码。

#### 验收必过项目

- `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/tools/test_dsl_run.py`
- `rg -n "_KernelEmitter|_emit_npu_demo_launch|_emit_cpu_conv2d_img2col2d_tiled|_validate_tile_codegen_contract|_type_to_c_for_target" kernel_gen/dsl/gen_kernel/gen_kernel.py` 不应命中迁移后仍留在兼容包装层的函数级实现。

#### 任务新建建议

- `任务类型：build`
- `任务目标：把函数/module 源码策略迁入 kernel_gen/dsl/gen_kernel/emit_c/function.py，并让 emit_c 直接覆盖完整源码生成。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260421-emitc-function-module-s3.md`

### S4：gen_kernel 兼容包装收口与全链路验收

#### 阶段目标

- 收缩 `kernel_gen/dsl/gen_kernel/gen_kernel.py` 为兼容包装层，统一调用 `emit_c(op_or_func, ctx)`，并完成全链路验收。

#### 目标 spec / API

- `spec/dsl/gen_kernel.md`
- `公开 API：gen_kernel(op_or_func, ctx)`、`GenKernelError`

#### 禁止修改面 / 合同真源

- `禁止修改面：不得删除 gen_kernel 公开入口；不得破坏 GenKernelError 公开错误类型`
- `合同真源：test/dsl/test_gen_kernel.py、test/tools/test_dsl_run.py、expectation.execute_engine.npu_demo.kernel_only`

#### 预期示例代码

```python
from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel

source = gen_kernel(module_op, EmitCContext(target="npu_demo"))
```

#### 预期输出

```text
gen_kernel(...) calls emit_c(...) and preserves the existing source text and GenKernelError contract.
```

#### 目标验收资产

- `test/dsl/test_gen_kernel.py`：确认包根 `__all__` 包含 `GenKernelError`、`gen_kernel`、`EmitCContext`、`EmitCError`、`emit_c`、`emit_c_op`、`emit_c_value`，legacy 属性拒绝不变，错误类型不变。
- `test/dsl/test_gen_kernel.py`：新增或保留 `EmitCError -> GenKernelError` 转换断言，确保旧调用方不会看到 `EmitCError`。
- `spec/dsl/emit_c.md`、`spec/dsl/gen_kernel.md`：复查公开 API、示例导入、功能实现链接与职责描述，不得继续把 `kernel_gen.dsl.emit_c` 或 `kernel_gen/dsl/emit_c.py` 当作公开入口。
- `test/tools/test_dsl_run.py`：确认工具链不需要改公开调用口径。
- `python3 -m expectation.execute_engine.npu_demo.kernel_only`：确认 execute_engine 正向链路继续可执行。
- `spec/tools/dsl_run.md`、`expectation/tools/dsl_run/*`、`expectation/execute_engine/npu_demo/kernel_only/*`、`expectation/execute_engine/npu_demo/default/*`：旧 `kernel_gen.dsl.emit_c` 文本与导入必须同步迁移到 `kernel_gen.dsl.gen_kernel`。

#### 验收必过项目

- `pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py`
- `pytest -q test/tools/test_dsl_run.py`
- `python3 -m expectation.execute_engine.npu_demo.kernel_only`
- `rg -n "kernel_gen\\.dsl\\.emit_c|from kernel_gen\\.dsl\\.emit_c|import kernel_gen\\.dsl\\.emit_c" kernel_gen test spec expectation script ARCHITECTURE` 不应命中有效旧导入。

#### 任务新建建议

- `任务类型：build`
- `任务目标：把 kernel_gen/dsl/gen_kernel/gen_kernel.py 收成兼容包装层并跑通 full codegen / dsl_run / execute_engine 验收链。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260421-gen-kernel-wrapper-s4.md`

## 待确认项

- 问题：`若互评认为 emit_c(obj, ctx) 不应直接覆盖完整源码层，是否回退到只做内部迁移？`
- 可选项：`继续完整源码层 / 只做内部迁移`
- 差异：`完整源码层会形成新的公开主入口；内部迁移只改善实现结构。`
- 推荐项：`继续完整源码层；该口径已由用户确认。`
- 当前状态：`已确认，除非互评提出新冲突，否则不再作为待用户确认项。`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：新增 emit_c(obj, ctx)；实现集中到用户指定的 gen_kernel 包式目录结构；npu_demo launch、tile codegen、CPU conv 等函数级专项全部迁入 emit_c；EmitCContext 实现抽到 emit_context.py；冲突或不确定项交由用户裁决。`
- `未确认前处理要求：若后续互评或执行阶段出现 API、任务范围、验收口径、依赖顺序、保留/删除边界冲突，不得通知管理员推进，必须先询问用户。`
- `若用户要求至少询问 3 人：用户历史口径要求新建任务默认不少于 3 人询问；本计划在建任务前需补齐不少于 3 个对象的询问记录。`
- `询问记录 1：守护最好的爱莉希雅 / 复评通过：删除 kernel_gen/dsl/emit_c.py、统一 kernel_gen.dsl.gen_kernel 包根导出、S1-S4、旧导入消费面和残留扫描验收均认可`
- `询问记录 2：睡觉小分队 / spec/API 补充意见已回收：最新正文已把 kernel_gen.dsl.gen_kernel 包根、emit_c(obj, ctx) 单一入口、emit_c_op/emit_c_value 窄接口和 gen_kernel 兼容包装关系写清，旧导入口径已明确删除`
- `询问记录 3：金铲铲大作战 / 实现可执行性补充意见已回收：最新 plan 已统一到 kernel_gen.dsl.gen_kernel 包根，删除 kernel_gen/dsl/emit_c.py、旧导入迁移、S1-S4 依赖和残留扫描验收都已写清；pytest / dsl_run / expectation / rg 组合足以覆盖迁移与回归边界`

## 参考资料

- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)：计划书结构、互评与终验要求。
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)：阶段正文模板。
- [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)：当前 op/value 片段发射合同。
- [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)：当前函数/module 源码生成合同。
- [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)：片段发射回归资产。
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)：完整源码生成回归资产。
- [`plan/emic_new_struc.md`](../../plan/emic_new_struc.md)：用户指定的目标目录结构草稿。
