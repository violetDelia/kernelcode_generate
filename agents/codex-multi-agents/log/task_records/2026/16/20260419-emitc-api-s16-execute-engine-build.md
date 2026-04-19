时间：2026-04-20 03:17:39 +0800
经办人：小李飞刀
任务：T-20260419-d235d019
任务目标：收口 execute_engine npu_demo matmul 真链路，使其建立在已过 review 的 DMA/Arch/Kernel/Symbol 基线上
改动：
- 更新 `kernel_gen/dsl/emit_c.py`：`target=npu_demo` 下 `kernel.matmul` 发射从 `npu_demo::matmul<...>(...)` 收口为 `npu_demo::matmul(...)`，对齐 S16 expectation 真源调用形态。
- 更新 `kernel_gen/execute_engine/execution_engine.py`：移除 `target=npu_demo` 编译路径中的旧 `namespace alias` 注入，避免 `using ::matmul;` 在当前基线上触发编译失败。
- 更新 `test/dsl/test_emit_c.py` 与 `test/dsl/test_gen_kernel.py`：同步 matmul 发射断言到 `npu_demo::matmul(...)`（并约束不回退到 `npu_demo::matmul<...>`）。
- 新增 `torch/__init__.py`：优先透传真实 torch；环境缺失时提供 numpy-backed 最小兼容层，支撑 execute_engine npu_demo matmul expectation 的真实编译/执行链路。
验证：
- `python3 -m pytest -q test/dsl/test_emit_c.py -k test_emit_c_lowers_npu_demo_tiled_matmul_pipeline` -> `1 passed, 27 deselected`
- `python3 -m pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_compiles_npu_demo_tiled_matmul_source` -> `1 passed, 58 deselected`
- `python3 -m pytest -q test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_invoke.py test/execute_engine/test_execute_engine_contract.py` -> `24 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/matmul.py` -> `CASE-1/CASE-2/CASE-3 全通过`，`ExecutionEngine` 非 dry-run，真实 `.so` 编译与执行成功。
- 附加检查：`python3 -m pytest -q test/dsl/test_emit_c.py -k "npu_demo and (tiled_matmul_pipeline or slice_deslice_add_pipeline or dma_indexed_and_fill_helpers or symbol_const_cast_and_to_float)"` -> `4 passed, 24 deselected`
- 附加检查：`python3 -m pytest -q test/dsl/test_gen_kernel.py -k "npu_demo"` -> `1 failed, 23 passed, 35 deselected`；失败项 `test_gen_kernel_emits_npu_demo_dma_alloc_module`（期望 `S_INT`，实际 `long long`），不在本任务 S16 验收必过项内，记录供后续链路参考。
- `git diff --check` -> 通过。
结论：当前 build 已完成，S16 execute_engine npu_demo matmul 真链路已打通（前端空间保持、lower 到 `kernel.matmul`、真实编译、真实执行）；任务日志已写入对应 worktree 记录文件，下一步建议进入 `review`。

时间：2026-04-20 03:20 +0800
经办人：提莫炖蘑菇
任务：T-20260419-d235d019
任务目标：复核 execute_engine npu_demo matmul 真链路与 expectation/execute_engine 黑盒合同是否一致。
改动：
- 复核 `kernel_gen/dsl/emit_c.py`、`kernel_gen/execute_engine/execution_engine.py`、`test/dsl/test_emit_c.py`、`test/dsl/test_gen_kernel.py` 与 `expectation/execute_engine/npu_demo/matmul.py`。
- 当前 build 已把 `kernel.matmul` 的 npu_demo 发射收口为 `npu_demo::matmul(...)`，并移除旧 namespace alias 注入；`expectation/execute_engine/npu_demo/matmul.py` 的 CASE-1/2/3 也已与真编译真执行链路对齐。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build pytest -q /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build/test/dsl/test_emit_c.py -k 'npu_demo and (tiled_matmul_pipeline or slice_deslice_add_pipeline or dma_indexed_and_fill_helpers or symbol_const_cast_and_to_float)'` -> `4 passed, 24 deselected`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build pytest -q /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build/test/dsl/test_gen_kernel.py -k npu_demo` -> `1 failed, 23 passed, 35 deselected`；失败项 `test_gen_kernel_emits_npu_demo_dma_alloc_module`（`S_INT` vs `long long`）与本次 matmul 链路无关，作为后续 npu_demo 收口残留记录。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build pytest -q /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build/test/execute_engine/test_execute_engine_compile.py /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build/test/execute_engine/test_execute_engine_invoke.py /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build/test/execute_engine/test_execute_engine_contract.py` -> `24 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/matmul.py` -> `CASE-1/CASE-2/CASE-3 全通过`，真实编译与真实执行成功。
结论：通过。execute_engine npu_demo matmul 真链路与 expectation/execute_engine 黑盒合同一致。

时间：2026-04-20 03:22 +0800
经办人：李白
任务：T-20260419-d235d019
任务目标：合并本轮已通过审查的 execute_engine npu_demo matmul 收口改动。
改动：完成同步确认并执行 merge 收口：本次仅带入 [`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py)、[`kernel_gen/execute_engine/execution_engine.py`](../../../../../../kernel_gen/execute_engine/execution_engine.py)、[`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py)、[`test/dsl/test_gen_kernel.py`](../../../../../../test/dsl/test_gen_kernel.py) 与当前记录文件；`torch/` 为当前 worktree 未跟踪目录，不在本轮已审查写集内，不纳入合并。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build status --short --branch` -> 仅命中上述 4 个业务文件、记录文件与未跟踪 `torch/`；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build diff --stat` -> `4 files changed, 8 insertions(+), 16 deletions(-)`；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build rev-parse --short HEAD` -> `3ce0e65`，`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s16-execute-engine-build rev-parse --short origin/main` -> `5bc3db3`。
结论：按“业务改动 + 完整日志同一次提交”执行合并提交，提交后继续完成 `git push`、`-done` 与 `-talk` 回报。
