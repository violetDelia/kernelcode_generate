时间：2026-04-08 12:54:14 +0800
经办人：金铲铲大作战
任务：T-20260408-cffe95b5
任务目标：取消 kernel_gen/passes/lowing 目录并同步修正相关引用。
改动：
- ARCHITECTURE/project_architecture.md：先行更新 lowing 路径引用为 lowering。
- kernel_gen/passes/lowing/__init__.py、kernel_gen/passes/lowing/nn_to_kernel.py：删除兼容入口并移除 lowing 目录。
- 说明：spec/pass/lowering 中 expectation 路径仍指向 expectation/pass/lowing，保持与现有脚本路径一致。
- 验证：本任务未要求测试，未执行验证命令。
结论：
- lowing 目录已移除，相关引用完成迁移；未执行测试。
时间：2026-04-08 12:58:13 +0800
经办人：提莫炖蘑菇
任务：T-20260408-cffe95b5
任务目标：复核 lowing 目录移除与引用更新一致性。
改动：
- 核查 `kernel_gen/passes/lowing/`：目录不存在（已移除）。
- 在允许范围内检索 `ARCHITECTURE/project_architecture.md`、`spec/**`、`kernel_gen/passes/lowering/**` 对 `lowing` 的引用：发现 `spec/pass/lowering/decompose_nn_softmax.md`、`spec/pass/lowering/buffer_results_to_out_params.md`、`spec/pass/lowering/memory_pool.md` 仍引用 `expectation/pass/lowing/*` 路径。
- `expectation/` 目录在该 worktree 中不存在，无法确认对应路径是否已迁移或删除。
结论：
- 不通过：规格文件仍保留 `expectation/pass/lowing/*` 引用，且 worktree 内无 `expectation/` 目录可核对，存在引用未更新或路径失配风险。需派生修复任务统一更新引用路径并补齐可核对证据。
时间：2026-04-08 13:17:21 +0800
经办人：小李飞刀
任务：T-20260408-cffe95b5
任务目标：统一修复 spec 中仍指向 expectation/pass/lowing 的引用，并补齐 expectation 目录与 lowering 路径证据。
改动：
- spec/pass/lowering/decompose_nn_softmax.md：expectation 链接与验证命令更新为 expectation/pass/lowering。
- spec/pass/lowering/buffer_results_to_out_params.md：expectation 验证命令与引用更新为 expectation/pass/lowering。
- spec/pass/lowering/memory_pool.md：expectation 验证命令更新为 expectation/pass/lowering。
- expectation/**：新增 expectation/pass/lowering 目录与对应脚本；补充 expectation/pass/lowing 旧路径 wrapper 转发到 lowering；补齐 expectation/utils/case_runner.py 依赖。
- 验证：无强制要求；已执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowering/decompose_nn_softmax.py`。
结论：
- spec 引用与 expectation 路径已对齐，worktree 内已可核对 lowering 脚本与旧路径兼容入口。

时间：2026-04-08 13:25:06 +0800
经办人：不要啊教练
任务：T-20260408-cffe95b5
任务目标：复核 spec 引用与 expectation 路径迁移一致，确认 lowering 脚本可用且旧路径 wrapper 可转发。
改动：
- 本次审查未修改代码。
- 复核 `spec/pass/lowering/{decompose_nn_softmax,buffer_results_to_out_params,memory_pool}.md`：expectation 引用与验证命令均已指向 `expectation/pass/lowering/**`，未再出现 `expectation/pass/lowing/**`。
- 复核 `expectation/pass/lowing/**`：旧路径脚本均通过 `runpy.run_path(...)` 转发到 `expectation/pass/lowering/**`。
- 验证命令1：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowering/decompose_nn_softmax.py`（exit=0；CASE-1/CASE-2 输出 before/after IR 正常）。
- 验证命令2：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/decompose_nn_softmax.py`（exit=0；确认旧路径可转发）。
结论：
- 通过：spec 引用、lowering 脚本与旧路径兼容 wrapper 一致；未发现额外改进点。
