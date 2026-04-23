时间：2026-04-23 23:08 +0800
经办人：守护最好的爱莉希雅
任务：T-20260423-9b323ce3
任务目标：main_npu_demo_pipeline_fold_cse 终验修复补充架构口径；明确 `expectation.dsl.mlir_gen.dialect.dma.view`、`expectation.execute_engine.npu_demo.default.fa_online_softmax`、`expectation.tools.ircheck.emitc_single_ops_true` 三类阻断中，哪些属于真实实现回归，哪些属于合同资产自身不一致，不允许执行人通过迎合旧资产改坏公开实现口径。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 中 `T-20260423-9b323ce3` 任务行，确认本轮 worktree 为 [`wt-20260423-main-npu-demo-final-repair`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair)。
- 已读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的终验记录，确认当前计划最小阻断项包含 `dma.view CASE-2`、`fa_online_softmax` 与 `emitc_single_ops_true`。
- 已读 [`expectation/execute_engine/npu_demo/default/__main__.py`](/home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/default/__main__.py)、[`expectation/tools/ircheck/emitc_single_ops_true.py`](/home/lfr/kernelcode_generate/expectation/tools/ircheck/emitc_single_ops_true.py)、[`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)、[`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py) 与当前 expectation 目录现场。
最小功能闭环：
- 给执行人一个单一、可执行的架构裁定：`dma.view CASE-2` 继续按真实实现/合同收口；`fa_online_softmax` 缺源文件与 `emitc_single_ops_true` 的 `const Memory& out` 文本都视为合同资产不一致，不作为当前实现需迎合的目标。
改动：
- 新增本条任务记录，补充两点架构裁定。
- 裁定 1：`expectation.execute_engine.npu_demo.default.fa_online_softmax` 当前不是“实现与 expectation 不符”，而是 expectation 目录自身前后不一致。现场已确认 [`expectation/execute_engine/npu_demo/default/__main__.py`](/home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/default/__main__.py) 仍 import `fa_online_softmax`，但仓库中不存在 [`expectation/execute_engine/npu_demo/default/fa_online_softmax.py`](/home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/default/fa_online_softmax.py)。同时 `__pycache__` 里仍保留 `fa_online_softmax.cpython-312.pyc`，此前终验里出现的 `Unknown input reference` 属于旧缓存残留，不应再作为当前实现收口目标。
- 裁定 2：[`expectation/tools/ircheck/emitc_single_ops_true.py`](/home/lfr/kernelcode_generate/expectation/tools/ircheck/emitc_single_ops_true.py) 中 `CASE-DMA-FILL`、`CASE-DMA-SLICE`、`CASE-KERNEL-BINARY-ADD` 等文本把首个 out 参数写成 `const Memory&`，与 [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md) 和 [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py) 已明确锁定的“前置 out 参数必须是可写引用”公开合同冲突。该 expectation 还是 `[immutable-file]`，执行人不得以修改实现去迎合这份旧文本；正确方向是保持实现对齐 spec/test，把该 expectation 冲突记为架构侧合同资产修正项。
- 当前任务执行口径：jcc你莫辜负继续收 `dma.view CASE-2` 的真实实现/合同问题，以及 `deslice/out-param` 的真实回退；不需要、也不允许为了缺失的 `fa_online_softmax` 源文件或 `emitc_single_ops_true` 的旧签名去改实现。
验证：
- `test -f /home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/default/fa_online_softmax.py` -> 失败，确认源文件不存在。
- `find /home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/default/__pycache__ -maxdepth 1 -type f | rg 'fa_online_softmax'` -> 命中 `fa_online_softmax.cpython-312.pyc`，确认目录存在旧缓存。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ... import expectation.execute_engine.npu_demo.default.__main__ ... PY` -> `ModuleNotFoundError: No module named 'expectation.execute_engine.npu_demo.default.fa_online_softmax'`，确认当前主仓现场已不能导入该 expectation。
- `rg -n "void fill_case\\(|void slice_case\\(|void kernel_binary_add_case\\(" expectation/tools/ircheck/emitc_single_ops_true.py` -> 命中 `const Memory& arg0` 旧文本。
- `rg -n "Memory<MemorySpace::GM, int32_t>& arg0|out-first|可写引用" spec/dsl/gen_kernel.md test/dsl/test_gen_kernel.py` -> 命中当前公开合同与测试，确认首个 out 参数为可写引用。
自检：
- 已读完整任务上下文，只补充架构口径，没有混入实现或测试修复。
- 结论直接对应当前两类分歧：一类是 expectation 源文件缺失 + 旧缓存残留，一类是 expectation 文本与 spec/test 公开 ABI 冲突；未把合同资产问题错误地下沉为实现改动目标。
- 当前裁定可直接指导 build：实现只收真实回归，合同资产冲突由架构侧后续修正，不再让执行人猜测“应改实现还是应改 expectation”。
结论：
- 架构口径已收口：`dma.view CASE-2` 与 `deslice/out-param` 继续按实现修；`fa_online_softmax` 缺源文件、`emitc_single_ops_true` 的 `const Memory& out` 文本都按合同资产不一致处理，不要求执行人改实现迎合。下一步由 jcc你莫辜负按该口径继续 build；如需改 expectation，由架构侧另行处理。

---

时间：2026-04-23 22:39 +0800
经办人：jcc你莫辜负
任务：T-20260423-9b323ce3
任务目标：按终验修复口径只收真实实现问题：修复 `buffer-results-to-out-params` 对 `dma.deslice` 的 out-param 回退，并补足对应 IR/源码回归；`expectation` 只作为合同验收资产单列。
执行前阅读记录：
- 已再次核对 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:4) 的 `T-20260423-9b323ce3` 任务行，确认本轮仍在 [`wt-20260423-main-npu-demo-final-repair`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair) 处理。
- 已读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的计划正文、终验失败摘要与全局完成态/验收设计，并复核前序记录 [`20260422-main-npu-demo-launch-s1.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260422-main-npu-demo-launch-s1.md)、[`20260422-main-npu-demo-launch-s2.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260422-main-npu-demo-launch-s2.md)、[`20260422-main-npu-demo-launch-s3.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260422-main-npu-demo-launch-s3.md)。
- 已读本记录上一条架构裁定，确认 `fa_online_softmax` 与 `emitc_single_ops_true` 里的旧 ABI 文本不属于当前实现修复目标；只继续处理 `deslice/out-param` 真回退，并保留 `dma.view CASE-2` 的现场证据。
最小功能闭环：
- 让 `buffer-results-to-out-params` 在处理 `func.return %deslice_result` 时，不只替换 result SSA，还同步把 [`dma.deslice`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/dialect/dma.py) 的真实写回 `target` operand 改成前置 `arg0`；随后用 pass 级回归和 `gen_kernel(...)` 黑盒源码回归共同锁住 out-first ABI。
改动：
- 在 [`kernel_gen/passes/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py) 新增 `_rewrite_side_effect_result_target(...)`，对 `dma.deslice.result` 这类“result 表示更新后 target、真实写回落在 target operand”的场景，先把 `target` operand 改到新 out 参数，再统一做 `replace_all_uses_with(...)`。
- 在 [`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py) 新增 `test_rewrite_deslice_result_retargets_writeback_to_front_out_param`，锁定 pass 改写后 `DmaDesliceOp.target == func_op.args[0]`，避免只改 return SSA、不改写回目标的半修状态再次出现。
- 在 [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py) 新增 `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param`，锁定 CPU 源码签名恢复为可写 `arg0`，并要求写回文本为 `arg0.at(...) = src.at(...)`，不再回退到旧的 `target.at(...)`。
验证：
- `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 - <<'PY' ... build_func_op(kernel, Memory([4, 4], NumericType.Float64)) ... PY` -> 输出 `func.func @kernel(... ) -> !nn.memory<[2, 2], [8, 1], f64, #nn.space<global>>`，确认 `dma.view CASE-2` 当前实现现场仍是 `[8,1]`。
- 通过临时 Python 复现实例确认：修复前 `gen_kernel(_rewrite_func(deslice_case), _ctx())` 会生成 `const Memory<...>& arg0` + `target.at(...) = src.at(...)`；修复后新回归锁定为 `Memory<...>& arg0` + `arg0.at(...) = src.at(...)`。
Diff 反推自测：
- `pytest -q test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or mixed_memory_and_scalar_results_preserves_scalar_return or deslice_result_retargets_writeback_to_front_out_param'` -> `3 passed`
- `pytest -q test/dsl/test_gen_kernel.py -k 'accepts_rewritten_single_output_function or rewritten_deslice_memory_result_uses_front_out_param'` -> `3 passed`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair diff --check` -> 通过
合同验收资产（不计入 Diff 反推自测）：
- `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.tools.ircheck.emitc_single_ops_true` -> 仍失败 `5 cases`；其中 `CASE-DMA-DESLICE` 已从“实现写旧 target”收口为 expectation 仍在查找旧文本 `arg2.at(...) = arg1.at(...)`，与架构裁定一致；其余 `fill/slice/kernel_binary_add/view` 仍是 expectation 旧文本问题。
- `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo.default` -> 仍报 `ModuleNotFoundError: expectation.execute_engine.npu_demo.default.fa_online_softmax`，符合“expectation 目录自身缺源文件”的架构裁定。
- `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.dma.view` -> 仍只失败 `CASE-2`；现场再次确认当前实现输出为 `!nn.memory<[2, 2], [8, 1], f64, #nn.space<global>>`，即静态 stride 真实值仍是 `[8,1]`，该失败不属于本轮 `deslice/out-param` diff 引入回退。
自检：
- API/兼容性：本次没有改动 [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md) 已锁定的 out-first ABI，而是让实现重新对齐既有 `arg0` 可写语义；`fill/slice/kernel_binary_add` 的公开合同未被动到。
- 边界/异常：修改范围仅覆盖 `DmaDesliceOp` 这类 result/target 分离的写回 op，没有扩大到无现场证据的其他 op，避免在终验修复阶段引入泛化副作用。
- 复用/粒度：把特殊处理单独收在 `_rewrite_side_effect_result_target(...)`，没有把 `DmaDesliceOp` 分支散落到主循环里，后续若再出现同类 aliasing op，可在同一 helper 内扩展。
- 可维护性/冗余：当前 helper 仍是 `dma.deslice` 特化；如果未来新增更多“result 与 target 分离”的 DMA 写回 op，建议补一个更通用的 aliasing-result 抽象，而不是继续堆 `isinstance` 分支。这一点属于后续可改进项，但不阻断本轮最小修复。
- 测试有效性：本轮同时补了 pass IR 回归和最终源码回归，能直接覆盖这次真实失败链路；没有把 `expectation` 旧文本纳入实现回归判断，避免把合同资产问题误记成实现 bug。
结论：
- 本轮真实实现修复已完成：`buffer-results-to-out-params` 不再把 `dma.deslice` 留在“前置了 out-param，但实际仍写旧 target”状态，`gen_kernel` 的 out-first ABI 也恢复为既有可写 `arg0`。
- 剩余阻断里，`fa_online_softmax` 缺源文件、`emitc_single_ops_true` 的旧 ABI 文本、`dma.view CASE-2` expectation 不一致都属于合同资产侧问题，不是本轮 diff 引入或遗留的实现回退。下一步可按流程进入 review；若后续要改 expectation，应由架构侧另行派单处理。

时间：2026-04-23 23:59 CST
经办人：不要啊教练
任务：T-20260423-9b323ce3
任务目标：复核终验修复对 dma.deslice out-param 的实现与记录，并确认剩余 expectation 失败是否都属于合同资产问题
执行前阅读记录：已读 `TODO.md` 当前任务行、`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md` 的终验/复验记录与全局完成态/验收设计、当前 worktree 任务记录前序条目、`kernel_gen/passes/buffer_results_to_out_params.py`、`test/pass/test_buffer_results_to_out_params.py`、`test/dsl/test_gen_kernel.py` 以及相关 expectation 入口 `expectation.tools.ircheck.emitc_single_ops_true`、`expectation.execute_engine.npu_demo.default`、`expectation.dsl.mlir_gen.dialect.dma.view`。
改动：
- 真实审查：逐项核对 `buffer-results-to-out-params` 新增 `_rewrite_side_effect_result_target(...)` 是否真的把 `dma.deslice` 的真实写回 target 改到前置 out 参数，并复核 pass 级与 `gen_kernel(...)` 级新增测试是否覆盖了“return SSA 被替换但 operand 仍写旧 target”这条失败链。
- 问题 1：当前记录把 `expectation.dsl.mlir_gen.dialect.dma.view` 的 `CASE-2` 统称为“合同资产问题”，但根因证据写得不够精确。现场 expectation 文件 [`expectation/dsl/mlir_gen/dialect/dma/view.py:85-90`](/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view.py:85) 把 `CASE_2_RESULT_IR` 的 dtype 固定写成了 `f32`，而现场生成 IR 为 `!nn.memory<[2, 2], [8, 1], i32, ...>`，失败并不是记录里概括的“stride 仍是 [8,1]”，而是 expectation 自己把 dtype 写死了。若不把这一点写清，后续接手人仍无法机械判断 `CASE-2` 为什么属于合同资产问题。
- 可改进点：在 build 记录里把 `dma.view CASE-2` 的合同资产根因补成可直接复现的证据链，至少写清 `CASE_2_RESULT_IR` 固定 `f32` 与现场生成 IR 的真实 dtype 不一致，而不是只写“实现现场仍是 [8,1]”。
验证：
- `python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or mixed_memory_and_scalar_results_preserves_scalar_return or deslice_result_retargets_writeback_to_front_out_param'`
  - 结果：`3 passed, 11 deselected, 1 warning`
- `python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py -k 'accepts_rewritten_single_output_function or rewritten_deslice_memory_result_uses_front_out_param'`
  - 结果：`3 passed, 63 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair diff --check`
  - 结果：通过
Diff 反推审查：
- 被审 diff 文件：`kernel_gen/passes/buffer_results_to_out_params.py`、`test/pass/test_buffer_results_to_out_params.py`、`test/dsl/test_gen_kernel.py`。
- 反推依据：实现 diff 只改了 `dma.deslice` 写回 target 的重写逻辑和对应 pass / 源码回归，因此复跑新增 pass 子集和 `gen_kernel` 子集，不扩大到未触及的 `dsl_run` / `execute_engine` 主链。
- 复核证据：[`kernel_gen/passes/buffer_results_to_out_params.py:501-530`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py:501) 现在会在替换 return SSA 之前先把 `DmaDesliceOp.target` 改成 `new_out_arg`；[`test/pass/test_buffer_results_to_out_params.py:480-517`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py:480) 直接锁定 pass 改写后的 `rewritten_deslice.target == func_op.args[0]`；[`test/dsl/test_gen_kernel.py:1062-1086`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py:1062) 继续锁定最终源码必须写 `arg0.at(...) = src.at(...)`。
- 未覆盖项：本轮 diff 未改 `main.py` / `dsl_run` / `execute_engine`，因此没有额外扩跑这些 pytest；剩余 expectation 单列为合同验收。
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.tools.ircheck.emitc_single_ops_true`
  - 结果：失败 5 cases；`CASE-DMA-DESLICE` 现为 expectation 仍查找旧文本 `arg2.at(...) = arg1.at(...)`，`CASE-DMA-FILL` / `CASE-DMA-SLICE` / `CASE-KERNEL-BINARY-ADD` 仍查找旧的 `const Memory& arg0` 签名，符合合同资产问题判断。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo.default`
  - 结果：`ModuleNotFoundError: expectation.execute_engine.npu_demo.default.fa_online_softmax`；现场也确认 [`expectation/execute_engine/npu_demo/default/fa_online_softmax.py`](/home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/default/fa_online_softmax.py) 缺失，只剩 `__pycache__/fa_online_softmax.cpython-312.pyc`，符合合同资产问题判断。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.dma.view`
  - 结果：失败 `CASE-2`；现场生成 IR 为 `!nn.memory<[2, 2], [8, 1], i32, #nn.space<local>>`，而 expectation 把 [`expectation/dsl/mlir_gen/dialect/dma/view.py:85-90`](/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view.py:85) 的 `CASE_2_RESULT_IR` 固定写成 `f32`。这说明它属于合同资产问题，但当前 build 记录没有把这个根因写精确。
自检：已逐行审查本轮实现与新增测试，确认 `dma.deslice` out-param 真回退已修复；特殊情况、边界、测试有效性和剩余合同验收入口都已核对。`fa_online_softmax` 与 `emitc_single_ops_true` 的合同资产问题证据充分，但 `dma.view CASE-2` 虽然也属于合同资产问题，当前任务记录对根因的描述还不够机械可判，按当前审查口径不能给通过。
结论：需修改。实现修复本身成立，但任务记录还应补清 `dma.view CASE-2` 属于 expectation 固定 `f32` 导致的合同资产问题，而不是笼统写成“现场还是 [8,1]”；建议回到 build 补齐这条根因证据后再复审。

时间：2026-04-23 23:33 CST
经办人：金铲铲大作战
任务：T-20260423-9b323ce3
任务目标：按 review 退回口径补清 `dma.view CASE-2` 的合同资产根因，并确认 `dma.deslice out-param` 修复与现有验证不回退
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前 `T-20260423-9b323ce3` 任务行、[`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的终验/复验设计，以及本 worktree 任务记录前序 build/review 条目。
- 已重读 [`expectation/dsl/mlir_gen/dialect/dma/view.py`](/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view.py)、[`kernel_gen/passes/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py)、[`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py) 与 [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py)，确认这轮只补记录，不扩大实现范围。
最小功能闭环：
- 把 `dma.view CASE-2` 为什么属于合同资产问题写成可机械复现的证据链：Expectation 把 `CASE_2_RESULT_IR` 固定成 `f32`，而现场 `build_func_op(...)` 的真实结果类型会跟 `CASE_2_SOURCE_IR` 的随机 `CASE_DTYPE` 同源，本轮复跑得到的是 `!nn.memory<[2, 2], [8, 1], i8, #nn.space<tlm1>>`；因此失败根因是 dtype 被错误写死，不是本轮 `deslice/out-param` 实现回退。
改动：
- 本轮没有修改产品代码或测试代码，只补写本条任务记录，收紧 `dma.view CASE-2` 的合同资产根因描述。
- 具体补充口径：
- [`expectation/dsl/mlir_gen/dialect/dma/view.py:85-90`](/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view.py:85) 把 `CASE_2_RESULT_IR` 固定写成 `nn_memory_type_ir((2, 2), "f32", CASE_SOURCE_SPACE, strides=("8", "1"))`。
- 同场景下，`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 - <<'PY' ... from kernel_gen.dsl.mlir_gen import build_func_op ... from expectation.dsl.mlir_gen.dialect.dma.view import dma_view_kernel_case_2, CASE_2_RUNTIME_ARGS ... print(build_func_op(dma_view_kernel_case_2, *CASE_2_RUNTIME_ARGS)) ... PY` 本轮输出的真实 IR 为 `func.func @dma_view_kernel_case_2(%0: !nn.memory<[4, 4], [4, 1], i8, #nn.space<tlm1>>) -> !nn.memory<[2, 2], [8, 1], i8, #nn.space<tlm1>>`。
- 结合 review 上一轮现场出现的 `i32` 结果，可以确认 `CASE-2` 的真实 dtype 并不固定，而是跟 `CASE_2_SOURCE_IR`/`CASE_DTYPE` 同源；唯一固定且错误的是 expectation 里的 `"f32"`。
- 所以 `CASE-2` 失败点是 expectation 把 dtype 锁死成了 `f32`，而不是记录里之前概括的“现场还是 [8,1]”。`[8,1]` 恰好是实现与合同一致的部分，不是这次失败根因。
Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or mixed_memory_and_scalar_results_preserves_scalar_return or deslice_result_retargets_writeback_to_front_out_param'`  
  结果：`3 passed, 11 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py -k 'accepts_rewritten_single_output_function or rewritten_deslice_memory_result_uses_front_out_param'`  
  结果：`3 passed, 63 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair diff --check`  
  结果：通过
合同验收（单列，不计入 Diff 反推自测）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.dma.view`  
  结果：仍失败 `CASE-2`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 - <<'PY' ... from kernel_gen.dsl.mlir_gen import build_func_op ... from expectation.dsl.mlir_gen.dialect.dma.view import dma_view_kernel_case_2, CASE_2_RUNTIME_ARGS ... print(build_func_op(dma_view_kernel_case_2, *CASE_2_RUNTIME_ARGS)) ... PY`  
  结果：本轮真实结果类型为 `!nn.memory<[2, 2], [8, 1], i8, #nn.space<tlm1>>`，证明结果 dtype 跟 `CASE_DTYPE` 同源，而不是固定 `f32`
真实自检：
- API/兼容性：这轮没有再动 [`buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py) 和已有回归，只补记录精度，避免把合同资产问题误写成实现行为问题。
- 边界/异常：`dma.view CASE-2` 的根因已经收敛到单一点位，即 expectation 的 `CASE_2_RESULT_IR` dtype 固定错误；`stride=[8,1]` 不是异常点，继续作为实现正确性的证据保留；真实 dtype 会跟 `CASE_DTYPE` 随机变化，这正是 expectation 不能把它写死成 `f32` 的原因。
- 测试有效性：本轮 diff 只新增记录，因此仍按当前 residual diff 复跑 `deslice/out-param` 两组真实回归；Expectation 继续只单列为合同验收资产，没有替代对应 pytest。
- 可改进点：若后续要真正修掉 `CASE-2` 合同资产，应由 expectation 侧另派单，把 [`expectation/dsl/mlir_gen/dialect/dma/view.py`](/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view.py) 的 `CASE_2_RESULT_IR` 从固定 `f32` 改回跟 `CASE_2_SOURCE_IR` 同源 dtype；这不属于本轮实现修复边界。
结论：
- `dma.deslice out-param` 的真实实现修复与现有回归未回退。
- `dma.view CASE-2` 现已在任务记录中明确收敛为合同资产问题：Expectation 固定 `f32`，现场实现实际发的是跟 `CASE_DTYPE` 同源的随机 dtype，本轮复跑为 `i8`；失败根因不是 stride `[8,1]`。

时间：2026-04-24 00:11 CST
经办人：不要啊教练
任务：T-20260423-9b323ce3
任务目标：复核终验修复记录已明确 dma.view CASE-2 属于 expectation 固定 f32 导致的合同资产问题，并确认 dma.deslice out-param 修复与现有验证未回退
执行前阅读记录：已读 `TODO.md` 当前任务行、`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md` 的终验/复验设计、当前 worktree 任务记录最新 build/review 条目、`kernel_gen/passes/buffer_results_to_out_params.py`、`test/pass/test_buffer_results_to_out_params.py`、`test/dsl/test_gen_kernel.py`、`expectation.dsl.mlir_gen.dialect.dma.view` 与 `expectation.tools.ircheck.emitc_single_ops_true`。
改动：
- 真实审查：复核最新 build 记录已把 `dma.view CASE-2` 的根因改成 expectation 固定 `f32`，并重新确认 `dma.deslice` 的实现修复和两组 diff 反推 pytest 没有回退。
- 问题 1：当前 build 记录虽然已把 `expectation.dsl.mlir_gen.dialect.dma.view` 的 `CASE-2` 根因写实，但它仍沿用“剩余 expectation failures 都属于合同资产问题”的总括结论，却没有把 `expectation.tools.ircheck.emitc_single_ops_true` 里的 `CASE-DMA-VIEW` 根因补成同等精度的证据链。
- 现场证据：`run_ircheck_text(CASE_TEXT_DMA_VIEW, ..., emitc_target="cpu")` 现在返回的 `actual_ir` 是 `long long view_offset0 = (0 * arg1.stride()[0]) + (0 * arg1.stride()[1]);`、`arg0_shape` / `arg0_stride` / `Memory<...> arg0(...)`，而 expectation 仍要求 [`expectation/tools/ircheck/emitc_single_ops_true.py:77-80`](/home/lfr/kernelcode_generate/expectation/tools/ircheck/emitc_single_ops_true.py:77) 的旧文本 `long long view_offset0 = 0;`、`v0_shape` / `v0_stride` / `Memory<...> v0(...)`。这说明 `CASE-DMA-VIEW` 也属于 expectation 旧文本问题，但当前任务记录没有把它写清，只写了笼统的“其余仍是 expectation 旧文本问题”。
- 可改进点：若要继续维持“剩余 expectation failures 均为合同资产问题”这条总结，记录里至少应把 `CASE-DMA-VIEW` 的现场 mismatch 一并补成可复现证据，而不是只精确到 `dma.view CASE-2` 一项。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or mixed_memory_and_scalar_results_preserves_scalar_return or deslice_result_retargets_writeback_to_front_out_param'`
  - 结果：`3 passed, 11 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py -k 'accepts_rewritten_single_output_function or rewritten_deslice_memory_result_uses_front_out_param'`
  - 结果：`3 passed, 63 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair diff --check`
  - 结果：通过
Diff 反推审查：
- 被审 residual diff 文件仍为：`kernel_gen/passes/buffer_results_to_out_params.py`、`test/pass/test_buffer_results_to_out_params.py`、`test/dsl/test_gen_kernel.py`，以及本轮补写的任务记录。
- 反推依据：产品 diff 未变化，因此继续复跑 `deslice/out-param` 两组 pytest，确认修复未回退；对合同资产侧补充核对 `expectation.dsl.mlir_gen.dialect.dma.view` 与 `expectation.tools.ircheck.emitc_single_ops_true` 的现场失败根因是否已在记录中写成机械可判。
- 复核证据：`dma.view CASE-2` 的 `f32` 固定问题已写回 build 记录；但 `CASE-DMA-VIEW` 目前只在 expectation 入口里能现场复现，任务记录还没落下对应 mismatch 证据。
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.tools.ircheck.emitc_single_ops_true`
  - 结果：仍失败 5 cases；其中 `CASE-DMA-VIEW` 当前 message 为 `CHECK-NEXT not found ... 'long long view_offset0 = 0;'`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 - <<'PY' ... run_ircheck_text(CASE_TEXT_DMA_VIEW, ...) ... PY`
  - 结果：`actual_ir` 为 `long long view_offset0 = (0 * arg1.stride()[0]) + (0 * arg1.stride()[1]);`、`arg0_shape/arg0_stride/arg0(...)`，可直接证明 expectation 还在查旧文本。
自检：已复核 `dma.deslice` out-param 修复未回退，`dma.view CASE-2` 的 `f32` 根因也已被 build 记录收实；但当前任务链若要声称“剩余 expectation failures 均为合同资产问题”，对 `emitc_single_ops_true` 的 `CASE-DMA-VIEW` 仍缺少同等精度的记录证据。按现行审查口径，这仍是可执行改进点，不能判通过。
结论：需修改。`dma.deslice` 修复和 `dma.view CASE-2` 记录都已收住，但请继续把 `CASE-DMA-VIEW` 的现场 mismatch 一并写进任务记录，再复审。

时间：2026-04-24 00:25 CST
经办人：金铲铲大作战
任务：T-20260423-9b323ce3
任务目标：补清终验修复记录中 `emitc_single_ops_true` 的 `CASE-DMA-VIEW` 现场 mismatch 证据，并保持 `dma.view CASE-2` 根因记录与 `dma.deslice out-param` 验证不回退
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前 `T-20260423-9b323ce3` 任务行、[`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的终验/复验设计，以及本 worktree 任务记录最新 build/review 条目。
- 已重读 [`expectation/tools/ircheck/emitc_single_ops_true.py`](/home/lfr/kernelcode_generate/expectation/tools/ircheck/emitc_single_ops_true.py)、[`kernel_gen/tools/ircheck.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/tools/ircheck.py)、[`kernel_gen/passes/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py) 和当前 residual diff 对应测试，确认这轮只补记录证据，不扩实现范围。
最小功能闭环：
- 把 `emitc_single_ops_true` 的 `CASE-DMA-VIEW` 写成可机械复现的合同资产 mismatch：Expectation 仍查旧文本 `view_offset0 = 0;`、`v0_shape/v0_stride/v0(...)`，而现场 `run_ircheck_text(...)` 的 `actual_ir` 已变成偏移公式、`arg0_shape/arg0_stride` 和 `Memory<...> arg0(...)`。
改动：
- 本轮没有修改产品代码或测试代码，只补写本条任务记录，收紧 `CASE-DMA-VIEW` 的现场 mismatch 证据。
- 具体补充口径：
- [`expectation/tools/ircheck/emitc_single_ops_true.py:77-80`](/home/lfr/kernelcode_generate/expectation/tools/ircheck/emitc_single_ops_true.py:77) 当前仍要求：
  - `long long view_offset0 = 0;`
  - `long long v0_shape[2] = {2, 2};`
  - `long long v0_stride[2] = {2, 1};`
  - `Memory<MemorySpace::GM, float> v0(const_cast<float*>(arg1.data()) + view_offset0, 2, v0_shape, v0_stride, arg1.format());`
- 同场景下，`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 - <<'PY' ... from expectation.tools.ircheck.emitc_single_ops_true import CASE_TEXT_DMA_VIEW ... from kernel_gen.tools.ircheck import run_ircheck_text ... print(result.actual_ir) ... PY` 现场返回的 `actual_ir` 为：
  - `long long view_offset0 = (0 * arg1.stride()[0]) + (0 * arg1.stride()[1]);`
  - `long long arg0_shape[2] = {2, 2};`
  - `long long arg0_stride[2] = {1, 1};`
  - `Memory<MemorySpace::GM, float> arg0(const_cast<float*>(arg1.data()) + view_offset0, 2, arg0_shape, arg0_stride, arg1.format());`
- 因而 `CASE-DMA-VIEW` 当前失败并不是 `dma.deslice out-param` 修复引入的回退，而是 expectation 仍在匹配旧的 view 文本形态；`CHECK-NEXT` 首个失败点就是 `long long view_offset0 = 0;`。
Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or mixed_memory_and_scalar_results_preserves_scalar_return or deslice_result_retargets_writeback_to_front_out_param'`  
  结果：`3 passed, 11 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py -k 'accepts_rewritten_single_output_function or rewritten_deslice_memory_result_uses_front_out_param'`  
  结果：`3 passed, 63 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair diff --check`  
  结果：通过
合同验收（单列，不计入 Diff 反推自测）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.tools.ircheck.emitc_single_ops_true`  
  结果：仍失败 `5 cases`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 - <<'PY' ... result = run_ircheck_text(CASE_TEXT_DMA_VIEW, source_path='expectation/tools/ircheck/emitc_single_ops_true.py#dma_view', emitc_target='cpu') ... print(result.failed_check) ... print(result.message) ... print(result.actual_ir) ... PY`  
  结果：`failed_check` 为 `CHECK-NEXT 'long long view_offset0 = 0;'`；`actual_ir` 如上，证明 `CASE-DMA-VIEW` 仍在查旧文本
真实自检：
- API/兼容性：这轮没有改 [`buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py) 或 `gen_kernel` 相关实现，只补合同资产证据，避免把 expectation 旧文本问题继续混写成实现回退。
- 边界/异常：`CASE-DMA-VIEW` 的首个失败点已经收敛到固定文本 `view_offset0 = 0;`；同时现场 `actual_ir` 还展示了局部变量命名和 stride 文本都已与 expectation 脱节，这足够支撑“旧文本 expectation”判断。
- 测试有效性：本轮 diff 只新增记录，因此继续按当前 residual diff 复跑 `deslice/out-param` 两组真实回归；Expectation 继续只单列为合同验收资产，没有替代对应 pytest。
- 可改进点：若后续要真正修掉 `CASE-DMA-VIEW` 合同资产，应由 expectation 侧另派单，把 [`expectation/tools/ircheck/emitc_single_ops_true.py`](/home/lfr/kernelcode_generate/expectation/tools/ircheck/emitc_single_ops_true.py) 中 view case 的旧 `CHECK-NEXT` 文本改成当前 `actual_ir` 口径；这不属于本轮实现修复边界。
结论：
- `dma.deslice out-param` 的真实实现修复与现有回归未回退。
- `dma.view CASE-2` 的 `f32` 固定根因记录保持有效。
- `emitc_single_ops_true` 的 `CASE-DMA-VIEW` 现已在任务记录中明确收敛为合同资产旧文本问题：Expectation 仍查 `view_offset0 = 0; v0_shape/v0_stride/v0(...)`，而现场 `actual_ir` 已经是偏移公式加 `arg0_shape/arg0_stride/arg0(...)`。

---
任务：T-20260423-9b323ce3
任务目标：复核终验修复记录已补清 `emitc_single_ops_true` 的 `CASE-DMA-VIEW` 现场 mismatch 证据，并确认 `dma.view CASE-2` 根因记录与 `dma.deslice out-param` 验证未回退
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前 `T-20260423-9b323ce3` 任务行、[`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的终验/复验设计，以及本 worktree 任务记录最新 build/review 条目。
- 已重读 [`expectation/dsl/mlir_gen/dialect/dma/view.py`](/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view.py)、[`expectation/tools/ircheck/emitc_single_ops_true.py`](/home/lfr/kernelcode_generate/expectation/tools/ircheck/emitc_single_ops_true.py)、[`kernel_gen/passes/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py)、[`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py) 和 [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py)，确认这轮 review 只复核记录补写与 residual diff 回归，不扩实现范围。
真实审查：
- 本轮 build 已把 `emitc_single_ops_true` 的 `CASE-DMA-VIEW` 收敛为可机械复现的合同资产 mismatch：[`expectation/tools/ircheck/emitc_single_ops_true.py:77`](/home/lfr/kernelcode_generate/expectation/tools/ircheck/emitc_single_ops_true.py:77) 仍固定检查 `view_offset0 = 0; v0_shape/v0_stride/v0(...)`，而现场 `run_ircheck_text(...)` 的 `actual_ir` 已明确变成偏移公式、`arg0_shape/arg0_stride` 和 `Memory<...> arg0(...)`。
- [`expectation/dsl/mlir_gen/dialect/dma/view.py:85`](/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view.py:85) 仍把 `CASE_2_RESULT_IR` 的 dtype 固定写成 `f32`；build 记录已补清当前现场 IR 为 `!nn.memory<[2, 2], [8, 1], i8, #nn.space<tlm1>>`，因此 `dma.view CASE-2` 的根因记录没有回退。
- [`kernel_gen/passes/buffer_results_to_out_params.py:501`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py:501)、[`test/pass/test_buffer_results_to_out_params.py:480`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py:480) 和 [`test/dsl/test_gen_kernel.py:1062`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py:1062) 对 `dma.deslice out-param` 的实现与黑盒源码回归仍然锁定在前置 `arg0` 写回，未见回退。
Diff 反推审查：
- 本轮 residual diff 仍聚焦 [`kernel_gen/passes/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/kernel_gen/passes/buffer_results_to_out_params.py)、[`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py) 与 [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py)；记录补写没有引入新的代码改动。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or mixed_memory_and_scalar_results_preserves_scalar_return or deslice_result_retargets_writeback_to_front_out_param'`
  结果：`3 passed, 11 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py -k 'accepts_rewritten_single_output_function or rewritten_deslice_memory_result_uses_front_out_param'`
  结果：`3 passed, 63 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair diff --check`
  结果：通过
合同验收（单列，不计入 Diff 反推审查）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.tools.ircheck.emitc_single_ops_true`
  结果：仍失败 `5 cases`；其中 `CASE-DMA-VIEW` 的首个失败点已在记录中明确为旧 `CHECK-NEXT 'long long view_offset0 = 0;'`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo.default`
  结果：仍报 `ModuleNotFoundError: expectation.execute_engine.npu_demo.default.fa_online_softmax`，保持既有合同资产结论。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.dma.view`
  结果：仍失败 `CASE-2`；与记录中的 `f32` 固定根因一致。
真实自检：
- API/兼容性：本轮没有改实现，只复核记录精度与 residual diff 回归；现有 `dma.deslice out-param` 行为和源码合同未回退。
- 边界/异常：`CASE-DMA-VIEW` 与 `dma.view CASE-2` 现在都已经落到具体 expectation 文本/类型常量，不再是笼统的“合同资产问题”表述。
- 测试有效性：Diff 反推审查继续只覆盖实际 residual diff 对应 pytest；`expectation` 只单列为合同验收资产，没有替代改动文件对应测试。
- 可改进点：本轮目标要求的记录补写与回归核对已闭环，未发现新的、仍应在当前切片继续处理的一线可执行问题；其余 expectation 修复应保持单独任务处理。
结论：
- 通过。本轮终验修复记录已补清 `emitc_single_ops_true` 的 `CASE-DMA-VIEW` 现场 mismatch 证据，`dma.view CASE-2` 的固定 `f32` 根因记录保持有效，且 `dma.deslice out-param` 的实现与验证未回退。

## 最终 merge 收口（2026-04-24 00:50 CST）

### 收口前确认
- 已再次阅读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 中 `T-20260423-9b323ce3` 当前 `merge` 任务行，确认本次就是把终验修复记录与实现收口并入最新主线。
- 已再次阅读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的终验/复验设计和前序记录，确认当前只收 `buffer-results-to-out-params` 的 `dma.deslice out-param` 修复与其对应记录，不再扩大范围。
- 已再次复核本 worktree 里最后一版 review 结论：`dma.deslice out-param` 的实现已收住，`dma.view CASE-2` 与 `emitc_single_ops_true CASE-DMA-VIEW` 仍属于 expectation 合同资产问题，不要求改实现迎合。

### 实际收口
- 先把 worktree 合到最新 `origin/main`，再把当前 residual diff 保持在这三份代码文件上：
  - [`kernel_gen/passes/buffer_results_to_out_params.py`](../../../../../../../kernel_gen/passes/buffer_results_to_out_params.py)
  - [`test/pass/test_buffer_results_to_out_params.py`](../../../../../../../test/pass/test_buffer_results_to_out_params.py)
  - [`test/dsl/test_gen_kernel.py`](../../../../../../../test/dsl/test_gen_kernel.py)
- 同步补写了当前任务记录的最终收口段，保留真实收口过程和当前验证结果，没有再引入其他实现文件。

### Diff 反推自测
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/pass/test_buffer_results_to_out_params.py -k 'single_memory_result or mixed_memory_and_scalar_results_preserves_scalar_return or deslice_result_retargets_writeback_to_front_out_param'`
  - 结果：`3 passed, 11 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair/test/dsl/test_gen_kernel.py -k 'accepts_rewritten_single_output_function or rewritten_deslice_memory_result_uses_front_out_param'`
  - 结果：`3 passed, 63 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-main-npu-demo-final-repair diff --check`
  - 结果：通过

### 最终结论
- 本轮终验修复记录已与真实收口过程一致，`dma.deslice out-param` 的实现与回归证据未回退。
- `expectation` 仍只作为合同验收资产单列，不计入本任务的 diff 反推测试。
- 当前任务可按 `done` 流程结束。
