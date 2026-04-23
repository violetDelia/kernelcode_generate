时间：2026-04-23 12:14 +0800
经办人：金铲铲大作战
任务：T-20260422-fdaf38a1
任务目标：S3：main.py host/kernel 输出与 npu_demo 运行链路收口；按 `ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md` 的 S3 执行。目标是让 `main.py` 默认走 `dsl_run + npu-demo-lowering + gen_kernel + execute_engine`，输出 `host/kernel/source` 区段，host 中发射 `npu_demo::launch<1, 1, 1, 0>`，真实编译执行并通过 torch 校验，同时保留 `dsl_run/gen_kernel` 四字段 `arch.launch` 入口与旧三字段残留扫描。

执行前阅读记录：
- 已读 [`TODO.md`](../../../../../../TODO.md) 中 `T-20260422-fdaf38a1` 任务行，确认本轮 worktree 为 [`wt-20260422-main-npu-demo-launch-s3`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3)。
- 已读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的 S3 正文、S1/S2 记录、全局完成态 / 验收设计和协同记录，确认本阶段要求 `main.py` 输出 `[LOWERED IR]` / `[HOST SOURCE]` / `[KERNEL SOURCE]` / `[SOURCE]` / `[EXECUTE]` / `[CHECK]`，host 中出现 `npu_demo::launch<1, 1, 1, 0>(...)`，并真实编译执行通过 torch 校验。

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

---

## review

时间：2026-04-23 13:10 +0800
经办人：不要啊教练
任务：T-20260422-fdaf38a1
任务目标：S3：main.py host/kernel 输出与 npu_demo 运行链路收口；按 `ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md` 的 S3 执行。目标是让 `main.py` 默认走 `dsl_run + npu-demo-lowering + gen_kernel + execute_engine`，输出 `host/kernel/source` 区段，host 中发射 `npu_demo::launch<1, 1, 1, 0>`，真实编译执行并通过 torch 校验，同时保留 `dsl_run/gen_kernel` 四字段 `arch.launch` 入口与旧三字段残留扫描。

执行前阅读记录：
- 已读 [`TODO.md`](../../../../../../TODO.md) 中 `T-20260422-fdaf38a1` 任务行，确认本轮 worktree 为 [`wt-20260422-main-npu-demo-launch-s3`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3)。
- 已读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的 S3 正文、S1/S2 记录、全局完成态 / 验收设计和协同记录，确认本阶段要求 `main.py` 输出 `[LOWERED IR]` / `[HOST SOURCE]` / `[KERNEL SOURCE]` / `[SOURCE]` / `[EXECUTE]` / `[CHECK]`，host 中出现 `npu_demo::launch<1, 1, 1, 0>(...)`，并真实编译执行通过 torch 校验。
- 已读本轮 build 记录，确认执行人已补齐 `Diff 反推自测`，并已在记录中写明 `main.py` 现在直接切分真实 `dsl_run(...)` 的完整 `source`，不再对 wrapper 再次走旧 `gen_kernel(...)` 发射。

最小功能闭环：
- `main.py` 能从同一次 `dsl_run(...)` 结果中稳定提取 `[HOST SOURCE]` 与 `[KERNEL SOURCE]`，并保持 `[LOWERED IR]` / `[SOURCE]` / `[EXECUTE]` / `[CHECK]` 的展示顺序。
- host 段展示 `npu_demo::launch<1, 1, 1, 0>(matmul_kernel_device, ...)`，kernel 段展示 `static void matmul_kernel_device(npu_demo::KernelContext& ctx, ...)`，与当前 S3 合同一致。
- 展示层不再重走旧 `gen_kernel(...)` 发射面，避免把 `arch.launch` 回退到旧 `emit_c` 不支持的路径。

自检：
- 复核 `main.py` 的 `_select_npu_demo_source_functions(...)`、`_strip_npu_demo_prelude(...)` 与 `_extract_npu_demo_function_source(...)`，确认它们只承担展示切分，不引入新的 IR 变换职责。
- 复核 `test/test_main_npu_demo_pipeline.py` 的两个回归：一个锁定端到端输出与 torch 校验，一个锁定 helper 对唯一 wrapper / kernel 的机械识别与截取。
- 复核安全与边界：未发现输入校验绕过、类型/形状绕过、边界越界、错误处理缺失、状态污染或资源释放问题；`_select_npu_demo_source_functions(...)` 在结构不符合 S3 目标时会显式失败。
- 复核可维护性：展示切分逻辑集中在 `main.py`，测试覆盖了输出结构与 helper 行为，未引入额外职责混杂。

Diff 反推审查：
- 被审实际改动文件：[`main.py`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/main.py)、[`test/test_main_npu_demo_pipeline.py`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/test/test_main_npu_demo_pipeline.py)。
- 反推出的测试命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/test/test_main_npu_demo_pipeline.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3:/home/lfr/kernelcode_generate python3 /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/main.py`
  - `git -C /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3 diff --check`
- 核验结果：
  - `pytest` 结果：`2 passed, 3 warnings`
  - `main.py` 结果：输出包含 `[LOWERED IR]` / `[HOST SOURCE]` / `[KERNEL SOURCE]` / `[SOURCE]` / `[EXECUTE]` / `[CHECK]`，并完成 torch 校验
  - `diff --check` 结果：通过
- `expectation`：本轮未额外执行；仅作为合同验收资产单列，不计入 diff 反推测试。

漏洞排查结果：
- 输入校验绕过：未发现。
- 类型/形状绕过：未发现。
- 边界越界：未发现。
- 错误处理缺失：未发现。
- 状态污染：未发现。
- 资源释放问题：未发现。

可改进点：
- 未发现额外改进点。

结论：通过。

expectation：
- 本轮未执行 expectation；仅作为合同验收资产单列，不替代改动文件对应测试。

结论：
- S3 的 main.py host/kernel 输出与 npu_demo 运行链路收口已完成，展示逻辑不再依赖 wrapper 重新发射，真实执行链路与 torch 校验通过。请按流程推进 `-next` 到 review。

---

## merge

时间：2026-04-23 13:42 +0800
经办人：李白
任务：T-20260422-fdaf38a1
任务目标：S3 review 通过后进入 merge，将 `main.py` 的 host/kernel 输出与 npu_demo 运行链路收口结果并入主线。

执行前核对：
- 已再次读取 [`TODO.md`](../../../../../../TODO.md) 中 `T-20260422-fdaf38a1` 的任务行，确认当前仍是本条 merge。
- 已再次核对 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的 S3 正文、全局完成态 / 验收设计和前序记录，确认这轮收口目标仍是 `main.py` 的 `[LOWERED IR]` / `[HOST SOURCE]` / `[KERNEL SOURCE]` / `[SOURCE]` / `[EXECUTE]` / `[CHECK]` 展示链路，以及 host 中的 `npu_demo::launch<1, 1, 1, 0>`。
- 已复核本轮 build / review 记录，确认它们都写明了 `Diff 反推自测` 与 `Diff 反推审查`，且 `expectation` 仅作为合同验收资产单列。

本次收口范围：
- [`main.py`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/main.py)
- [`test/test_main_npu_demo_pipeline.py`](/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s3/test/test_main_npu_demo_pipeline.py)
- 本任务记录本身

结果：
- 已将上述改动收口进当前 worktree，对应内容已并入主线提交。
- 最终对外行为保持不变：`main.py` 仍从真实 `dsl_run(...)` 结果中切分出 host/kernel 段，真实执行链路和 torch 校验均通过。
- `expectation` 仍只作为合同验收资产单列，不替代改动文件对应测试。

结论：通过。
