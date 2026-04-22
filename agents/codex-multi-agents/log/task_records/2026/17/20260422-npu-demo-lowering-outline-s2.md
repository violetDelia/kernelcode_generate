时间：2026-04-22 04:17
经办人：金铲铲大作战
任务：T-20260422-ee586cde
任务目标：推进 npu_demo_lowering_outline_device_kernel_green_plan.md 的 S2，收口 launch extent=1/1/1 的 body / wrapper 源码生成与 dsl_run / execute_engine 前置链路
改动：`kernel_gen/dsl/gen_kernel.py` 收口 npu_demo module 级 helper/body/wrapper 发射与 target registry 取 extent；`kernel_gen/tools/dsl_run.py` 对 npu_demo wrapper 模块改为优先执行 body 函数；`kernel_gen/execute_engine/entry_shim_builder.py` 补齐 `KernelContext&` body 桥接；`test/dsl/test_gen_kernel.py` 修正 barrier fixture 的 deslice 目标/源顺序并同步 `launch<1, 1, 1>` / fail-fast 文案；联动验证了 `kernel_gen/passes/attach_arch_information.py`、`kernel_gen/passes/inline.py` 及其对应 spec/test、pass registry 与 npu_demo lowering pipeline 迁移文件。
验证：`pytest -q test/pass/test_pass_registry.py` -> `31 passed, 1 warning`；`pytest -q test/pass/test_pipeline_npu_demo_lowering.py` -> `3 passed, 1 warning`；`pytest -q test/pass/test_attach_arch_information.py` -> `2 passed, 1 warning`；`pytest -q test/pass/test_inline.py` -> `2 passed, 1 warning`；`pytest -q test/dsl/test_gen_kernel.py` -> `64 passed, 15 warnings`；`pytest -q test/tools/test_dsl_run.py::test_dsl_run_numpy_output` -> `1 passed, 2 warnings`；`pytest -q test/tools/test_dsl_run.py::test_dsl_run_pass_manager_with_list_real_args` -> `1 passed, 2 warnings`；`pytest -q test/tools/test_dsl_run.py::test_dsl_run_supports_tiled_matmul_kernel_on_npu_demo` -> `1 passed, 2 warnings`；`python3 -m expectation.execute_engine.npu_demo.default` -> 通过；`git diff --check` -> 通过
Diff 反推自测：改动文件按实际 diff 反推到 `kernel_gen/dsl/gen_kernel.py`、`kernel_gen/tools/dsl_run.py`、`kernel_gen/execute_engine/entry_shim_builder.py`、`kernel_gen/passes/attach_arch_information.py`、`kernel_gen/passes/inline.py`、`kernel_gen/passes/registry.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/dsl/gen_kernel.md`、`spec/pass/*.md`、`test/dsl/test_gen_kernel.py`、`test/tools/test_dsl_run.py`、`test/pass/test_pass_registry.py`、`test/pass/test_pipeline_npu_demo_lowering.py`、`test/pass/test_attach_arch_information.py`、`test/pass/test_inline.py`；反推执行的测试覆盖了对应改动文件的 pytest 用例与本轮新增 pass 用例，未把 expectation 计入 diff 反推测试。
合同验收（如适用）：`python3 -m expectation.execute_engine.npu_demo.default` 通过，作为合同验收资产单列；不替代改动文件对应测试。
结论：build 已完成，`Diff 反推自测` 与合同验收均通过；已按 TODO.md 续接 review。

## review

时间：2026-04-22 02:34:16 +0800

经办人：不要啊教练

任务：T-20260422-ee586cde

任务目标：复评 npu_demo_lowering_outline_device_kernel_green_plan.md 的 fail-fast 边界是否机械可判

审查口径：`Diff 反推审查`。已核对本轮 build 记录包含 `Diff 反推自测`，并且 expectation 仅作为合同验收资产单列，不替代改动文件对应测试。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_attach_arch_information.py test/pass/test_pipeline_npu_demo_lowering.py test/dsl/test_gen_kernel.py -k 'attach_arch_information or npu_demo_launch or only_kernel'` -> `9 passed, 60 deselected, 1 warning`
- 最小复现：`AttachArchInformationPass(target="npu_demo").run(...)` 在包含两个非 declaration `func.func` 的 module 上会静默落到首个函数并写回 launch extent，没有对 `root 函数不唯一` 触发显式失败

结论：`需修改`

原因：
- `spec/pass/attach_arch_information.md` 仍把 entry func 定义为“首个非 declaration 的 func.func”，与计划书里要求的 `root 函数不唯一` 机械失败边界不一致。
- `kernel_gen/passes/attach_arch_information.py` 当前实现会静默选择首个函数，未把多 root 作为稳定失败。
- `kernel_gen/tools/dsl_run.py` 在 `npu_demo` wrapper 候选不唯一时会回退到首个普通函数，尚未把“唯一 arch.launch wrapper”这一前提收成机械失败边界。

建议：
- 收紧 `attach-arch-information` 的入口选择与测试，补齐多 root / 缺 target / 缺硬件字段的显式失败用例。
- 收紧 `dsl_run` 的 wrapper 选择逻辑，补齐多 wrapper 失败用例，避免静默回退。
- `only-kernel=true` 的拒绝口径已明确，当前不构成问题。

## build

时间：2026-04-22 11:17:49 +0800

经办人：金铲铲大作战

任务：T-20260422-ee586cde

任务目标：收紧 `attach_arch_information` 与 `dsl_run` 的机械失败边界，禁止 npu_demo root / wrapper 静默回退

改动：`kernel_gen/passes/attach_arch_information.py` 改为要求 module 中唯一非 declaration `func.func`，否则显式失败；`kernel_gen/tools/dsl_run.py` 改为要求 `npu_demo` lowered module 中唯一 `arch.launch` wrapper，否则显式失败；`spec/pass/attach_arch_information.md`、`spec/tools/dsl_run.md` 同步唯一性边界；`test/pass/test_attach_arch_information.py`、`test/tools/test_dsl_run.py` 补齐多 root / 无唯一 wrapper 负例

验证：`python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/passes/attach_arch_information.py /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/tools/dsl_run.py /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/test/pass/test_attach_arch_information.py /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/test/tools/test_dsl_run.py` -> 通过；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/test/pass/test_attach_arch_information.py /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/test/tools/test_dsl_run.py -k 'attach_arch_information or npu_demo or only_kernel'` -> `11 passed, 11 deselected, 12 warnings`；`git diff --check` -> 通过

Diff 反推自测：改动文件按实际 diff 反推到 `kernel_gen/passes/attach_arch_information.py`、`kernel_gen/tools/dsl_run.py`、`spec/pass/attach_arch_information.md`、`spec/tools/dsl_run.md`、`test/pass/test_attach_arch_information.py`、`test/tools/test_dsl_run.py`；反推执行的测试覆盖了对应改动文件的 pytest 用例与本轮新增负例，未把 expectation 计入 diff 反推测试

合同验收（如适用）：`python3 -m expectation.execute_engine.npu_demo.default` 通过，作为合同验收资产单列；不替代改动文件对应测试

结论：build 已完成，`Diff 反推自测` 与合同验收均通过；已按 TODO.md 续接 review

## review

时间：2026-04-22 11:30:00 +0800

经办人：提莫炖蘑菇

任务：`T-20260422-ee586cde`

审查口径：`Diff 反推审查`

审查结果：

- 已按实际 diff 复核 [kernel_gen/dsl/gen_kernel.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/dsl/gen_kernel.py)、[kernel_gen/execute_engine/entry_shim_builder.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/execute_engine/entry_shim_builder.py)、[kernel_gen/passes/__init__.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/passes/__init__.py)、[kernel_gen/passes/pipeline/__init__.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/passes/pipeline/__init__.py)、[kernel_gen/passes/pipeline/npu_demo_lowering.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/passes/pipeline/npu_demo_lowering.py)、[kernel_gen/passes/registry.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/passes/registry.py)、[kernel_gen/tools/dsl_run.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/kernel_gen/tools/dsl_run.py)、[spec/dsl/gen_kernel.md](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/spec/dsl/gen_kernel.md)、[spec/pass/README.md](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/spec/pass/README.md)、[spec/pass/pipeline/README.md](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/spec/pass/pipeline/README.md)、[spec/pass/pipeline/npu_demo_lowering.md](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/spec/pass/pipeline/npu_demo_lowering.md)、[spec/pass/registry.md](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/spec/pass/registry.md)、[spec/tools/dsl_run.md](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/spec/tools/dsl_run.md)、[test/dsl/test_gen_kernel.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/test/dsl/test_gen_kernel.py)、[test/pass/test_pass_registry.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/test/pass/test_pass_registry.py)、[test/pass/test_pipeline_npu_demo_lowering.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/test/pass/test_pipeline_npu_demo_lowering.py)、[test/tools/test_dsl_run.py](/home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2/test/tools/test_dsl_run.py)；`attach_arch_information` 与 `dsl_run` 的唯一性边界已收口，`npu-demo-lowering` pipeline 的公开入口与 `expectation` 合同资产边界保持稳定，未拿 `expectation` 替代改动文件对应测试

验证：

- `pytest -q test/pass/test_pass_registry.py test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/test_inline.py test/dsl/test_gen_kernel.py test/tools/test_dsl_run.py` -> `122 passed, 29 warnings`
- `git diff --check` -> 通过

结论：`通过`，本轮 build 的机械失败边界与公开入口兼容性已通过 review 复核；`expectation` 仅作为合同验收资产单列

## merge 记录

- 时间：`2026-04-22 11:42`
- 经办人：`李白`
- 任务：`T-20260422-ee586cde`
- 任务目标：完成 merge 收口与同步确认
- 改动：当前 worktree 仅保留本任务记录与 npu-demo lowering outline 收口改动；本轮在已通过 Diff 反推审查 的基础上补写 merge 收口记录，不扩大修改面
- 验证：`timeout 60 git -C /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2 fetch origin` -> 通过；`git -C /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2 status --short --untracked-files=all` -> 仅当前任务相关文件待提交；`git -C /home/lfr/kernelcode_generate/wt-20260422-npu-demo-lowering-outline-s2 diff --check` -> 通过
- Diff 反推自测 / Diff 反推审查：沿用已写入 build / review 记录中的结论；本轮 merge 不新增测试，只收口提交与同步
- 合同验收（如适用）：本轮 expectation 仍仅作为合同验收资产单列，不新增 expectation 验收
- 结论：merge 收口已完成，待提交并推送

## merge 完成

- 时间：`2026-04-22 12:03`
- 经办人：`李白`
- 任务：`T-20260422-ee586cde`
- 提交：`80cb0e9`
- 推送：已同步到 `origin/main`
- 主目录同步：`git -C /home/lfr/kernelcode_generate merge --ff-only origin/main` 已完成，主目录已快进到 `80cb0e9`
- 状态：任务 worktree 仅保留本任务记录与收口结果，`-done` 待执行
- Diff 反推自测 / Diff 反推审查：沿用已写入 build / review 记录中的结论；本轮 merge 不新增测试
- 合同验收（如适用）：`expectation` 仍仅作为合同验收资产单列
- 结论：merge 已完成，等待任务状态切换与回报
