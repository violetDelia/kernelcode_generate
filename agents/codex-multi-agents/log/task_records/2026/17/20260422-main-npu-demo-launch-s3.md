时间：2026-04-23 12:14 +0800
经办人：金铲铲大作战
任务：T-20260422-fdaf38a1
任务目标：S3：main.py host/kernel 输出与 npu_demo 运行链路收口；按 `ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md` 的 S3 执行。目标是让 `main.py` 默认走 `dsl_run + npu-demo-lowering + gen_kernel + execute_engine`，输出 `host/kernel/source` 区段，host 中发射 `npu_demo::launch<1, 1, 1, 0>`，真实编译执行并通过 torch 校验，同时保留 `dsl_run/gen_kernel` 四字段 `arch.launch` 入口与旧三字段残留扫描。

执行前阅读记录：
- 已读 [`TODO.md`](../../../../../TODO.md) 中 `T-20260422-fdaf38a1` 任务行，确认本轮 worktree 为 [`wt-20260422-main-npu-demo-launch-s3`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3)。
- 已读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的 S3 正文、S1/S2 记录、全局完成态 / 验收设计和协同记录，确认本阶段要求 `main.py` 输出 `[LOWERED IR]` / `[HOST SOURCE]` / `[KERNEL SOURCE]` / `[SOURCE]` / `[EXECUTE]` / `[CHECK]`，host 中出现 `npu_demo::launch<1, 1, 1, 0>(...)`，并真实编译执行通过 torch 校验。

改动：
- 更新 [`main.py`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/main.py)，改为直接从 `dsl_run(...)` 返回的完整 `source` 中按函数名切出 `[HOST SOURCE]` 与 `[KERNEL SOURCE]`；不再对 wrapper 单独走旧 `gen_kernel(...)` 发射，避免 `arch.launch` 在旧 `emit_c` 路径里报 unsupported op。
- 更新 [`test/test_main_npu_demo_pipeline.py`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/test/test_main_npu_demo_pipeline.py)，把 main 端到端回归从“重新发射函数”改为“从完整 source 截取函数段”，并继续锁住 `[LOWERED IR]` / `[HOST SOURCE]` / `[KERNEL SOURCE]` / `[SOURCE]` / `[EXECUTE]` / `[CHECK]` 以及 `npu_demo::launch<1, 1, 1, 0>` 文本。

真实自检：
- 端到端链路已经真实跑通：`dsl_run(...)` 的 lowered module 与完整 source 都能生成，`result.execute_result.ok` 为真，数值校验与 `torch.matmul` 对齐。
- 这轮问题本质上是展示层重新调用旧 `gen_kernel(...)` 去发射 wrapper，撞上了旧 `emit_c` 不支持 `arch.launch` 的边界；现在改成对真实 source 做文本切分，避免把展示逻辑和发射逻辑重新耦合。
- main.py 仍保持最小展示入口，不新增 standalone pass，也没有把 `expectation` 当作测试替代。
- `main.py` 受仓内 `.gitignore` 影响不显示在 `git status`，但 worktree 文件已实际更新并通过运行验证。

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/main.py` -> 通过，输出包含 `[LOWERED IR]` / `[HOST SOURCE]` / `[KERNEL SOURCE]` / `[SOURCE]` / `[EXECUTE]` / `[CHECK]`，host 中出现 `npu_demo::launch<1, 1, 1, 0>(matmul_kernel_device, arg0, arg1, arg2);`，kernel 中出现 `static void matmul_kernel_device(npu_demo::KernelContext& ctx, ...)`，并完成 torch 校验。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/test/test_main_npu_demo_pipeline.py` -> `2 passed, 3 warnings`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/main.py /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/test/test_main_npu_demo_pipeline.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3 diff --check` -> 通过

expectation：
- 本轮未执行 expectation；仅作为合同验收资产单列，不替代改动文件对应测试。

结论：
- S3 的 main.py host/kernel 输出与 npu_demo 运行链路收口已完成，展示逻辑不再依赖 wrapper 重新发射，真实执行链路与 torch 校验通过。请按流程推进 `-next` 到 review。
