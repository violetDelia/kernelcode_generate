# 20260529 matmul effective view fill elimination revert

## 合并前记录

时间：2026-05-29 04:22 +0800
经办人：大闸蟹
任务：matmul-effective-view-fill-elimination-revert
任务目标：完整回退提交 `e8a08b619053780ae4b80d56dbe700d5323530cd`（`merge matmul effective view fill elimination`），并合并当前主仓。

改动：
- 删除 `e8a08b61` 新增的任务记录 `agents/codex-multi-agents/log/task_records/2026/25/20260528-matmul-effective-view-fill-elimination.md`。
- 回退三条 matmul demo 的 effective-view / dynamic-acc 累加形态，恢复 `fill + partial matmul + add`。
- 回退 `LowerDmaMemoryHierarchyPass(apply_op="matmul{...}")` 到三 operand、copy-only staging、旧错误文本。
- 同步 `spec/pass/lowering/dma_memory_hierarchy/spec.md`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`、`test/passes/test_dma_memory_hierarchy.py`。
- 修正 `test/passes/pipeline/test_npu_demo_lowering.py` 中两个公开 pipeline/source 断言，使其匹配完整回退后的公开 IR 形态。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel/matmul/inputs_static_tile_static.py kernel/matmul/inputs_static_tile_dynamic.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel_gen/passes/tuning/dma_memory_hierarchy.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/passes/test_dma_memory_hierarchy.py`：14 passed, 1 warning，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/passes/test_kernel_decompose.py`：12 passed, 1 warning，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/dsl/gen_kernel/emit/test_package.py -k dynamic_acc`：1 passed, 72 deselected, 2 warnings，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`：4 passed, 1 warning，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：10 passed, 1 warning，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/kernel/test_runner.py`：3 passed, 1 warning，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，absent/present bias 数值校验通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：exit=0，absent/present bias 数值校验通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：exit=0，absent/present bias 数值校验通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.dma_memory_hierarchy`：exit=0；作为只读观察资产运行，当前与回退后合同一致。
- `git diff --check`：exit=0。
- `git diff -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：均无输出。

合并范围：
- `agents/codex-multi-agents/log/task_records/2026/25/20260528-matmul-effective-view-fill-elimination.md` 删除。
- `agents/codex-multi-agents/log/task_records/2026/25/20260529-matmul-effective-view-fill-elimination-revert.md` 新增。
- `kernel/matmul/inputs_dynamic_tile_dynamic.py`
- `kernel/matmul/inputs_static_tile_dynamic.py`
- `kernel/matmul/inputs_static_tile_static.py`
- `kernel_gen/passes/tuning/dma_memory_hierarchy.py`
- `spec/pass/lowering/dma_memory_hierarchy/spec.md`
- `test/kernel/test_matmul_symbolic_memory_genkernel.py`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/passes/test_dma_memory_hierarchy.py`

自检：
- 接口：未新增公开 API；`LowerDmaMemoryHierarchyPass` 恢复三 operand apply-op 合同。
- 边界：dynamic acc dialect / emit / decompose targeted gate 通过，未回退最新主线的 dynamic acc 通用合同。
- 兼容性：matmul 三条 demo 和 pipeline pytest 均通过。
- 敏感目录：expectation、.skills、agents/standard、AGENTS.md、TODO.md、DONE.md 未纳入候选 diff。
- 残余风险：本次是完整回退 `e8a08b61`，因此删除该提交新增任务记录；不删除其它历史记录。

结论：回退 diff 和验证已收口，可提交并推送。
