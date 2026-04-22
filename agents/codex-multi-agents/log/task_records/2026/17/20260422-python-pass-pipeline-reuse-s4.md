时间：2026-04-22 10:02
经办人：金铲铲大作战
任务：T-20260422-efe8cd63
任务目标：推进 python_spec_impl_test_refactor_green_plan.md 的 S4，复用 pass / pipeline 层重复遍历、注册和错误处理逻辑，保持公开 pass 与 pipeline 入口兼容
改动：在 [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py) 中新增 `_build_pass_manager_from_passes`、`_build_pass_name_positions`、`_validate_pass_order_constraints`，把 `PassManager.run(...)` 的顺序约束校验收口为单一 helper，并保留 `symbol-loop-hoist`、`lower-dma-memory-hierarchy`、`tile family` 与 `buffer-results-to-out-params` 的原有错误短语；在 [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py) 中新增 `_register_registry_entry`、`_build_registered_pass_instance`、`_build_registered_pipeline_manager`，统一 pass / pipeline 的重复注册、options 构造与错误转换逻辑；让 [kernel_gen/passes/pipeline/default_lowering.py](kernel_gen/passes/pipeline/default_lowering.py) 与 [kernel_gen/passes/pipeline/npu_demo_lowering.py](kernel_gen/passes/pipeline/npu_demo_lowering.py) 复用 `_build_pass_manager_from_passes`，保持公开 pipeline builder 名称与顺序不变
验证：`python3 -m py_compile kernel_gen/passes/pass_manager.py kernel_gen/passes/registry.py kernel_gen/passes/pipeline/default_lowering.py kernel_gen/passes/pipeline/npu_demo_lowering.py` -> 通过；`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4:/home/lfr/kernelcode_generate PYTHONDONTWRITEBYTECODE=1 pytest -q /home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4/test/pass/test_pipeline_npu_demo_lowering.py` -> `55 passed, 1 warning`；`git -C /home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4 diff --check` -> 通过
Diff 反推自测：按实际 diff 反推到 `kernel_gen/passes/pass_manager.py`、`kernel_gen/passes/registry.py`、`kernel_gen/passes/pipeline/default_lowering.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`；反推执行的测试覆盖了 pass order 校验、registry 注册与构造、default / npu-demo pipeline 的公开顺序与 `PassManager` 兼容行为，未将 `expectation` 计入 diff 反推测试
合同验收（如适用）：本轮未单列 expectation 合同验收资产；expectation 仅作为合同验收资产单列，不替代改动文件对应测试
结论：build 已完成，pass / pipeline 层重复控制流已收口且公开入口行为未回退；按 TODO.md 续接 review

复审时间：2026-04-22
经办人：提莫炖蘑菇
任务：T-20260422-efe8cd63
Diff 反推审查：已按实际 diff 复核 [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)、[kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)、[kernel_gen/passes/pipeline/default_lowering.py](kernel_gen/passes/pipeline/default_lowering.py)、[kernel_gen/passes/pipeline/npu_demo_lowering.py](kernel_gen/passes/pipeline/npu_demo_lowering.py)；公共 helper 仅抽取重复控制流与注册/构造样板，`PassManager.run(...)` 的顺序约束、registry 的重复注册与构造错误短语、公开 pipeline 名称与顺序均保持不变；`expectation` 仅作为合同验收资产单列，不替代对应测试
验证：`pytest -q test/pass/test_pass_manager.py test/pass/test_pass_registry.py test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py` -> `55 passed, 1 warning`；`git diff --check` -> 通过
结论：通过，pass / pipeline 复用层收口完成，公开入口与回归验证均正常

时间：2026-04-22 10:12
经办人：李白
任务：T-20260422-efe8cd63
任务目标：完成 merge 收口与同步确认
改动：当前 worktree 仅保留本任务记录与 pass / pipeline 复用层改动；本轮在已通过 Diff 反推审查 的基础上补写 merge 收口记录，不扩大修改面
验证：`timeout 60 git -C /home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4 fetch origin` -> 通过；`git -C /home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4 status --short --untracked-files=all` -> 仅当前任务相关文件待提交；`git -C /home/lfr/kernelcode_generate/wt-20260422-python-pass-pipeline-reuse-s4 diff --check` -> 通过
Diff 反推自测 / Diff 反推审查：沿用已写入 build / review 记录中的结论；本轮 merge 不新增测试，只收口提交与同步
合同验收（如适用）：本轮无对应 expectation 合同资产
结论：merge 收口已完成，待提交并推送
