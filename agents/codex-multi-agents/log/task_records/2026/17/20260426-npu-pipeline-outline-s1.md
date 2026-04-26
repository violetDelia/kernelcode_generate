时间：2026-04-26 21:32 +0800
经办人：睡觉小分队
任务：T-20260426-dbabb1e3
任务目标：按 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md` 的 S1 收 `pass/pipeline + gen_kernel/emit` 的合同分层、公开 API 与非公开 helper 边界，并记录本轮 `pytest` / standalone 验收链现状；不改 `expectation`，不扩到 `dsl_run` / `execute_engine`。
执行前阅读记录：已读根仓 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 正文 / 全局完成态 / 验收设计、[`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../spec/pass/pipeline/npu_demo_lowering.md)、[`spec/pass/attach_arch_information.md`](../../../../../../spec/pass/attach_arch_information.md)、[`spec/pass/outline_device_kernel.md`](../../../../../../spec/pass/outline_device_kernel.md)、[`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../spec/dsl/gen_kernel/gen_kernel.md)、[`spec/dsl/gen_kernel/emit.md`](../../../../../../spec/dsl/gen_kernel/emit.md)、对应 `test/pass/*` / `test/dsl/gen_kernel/*` / `kernel_gen/passes/*` / `kernel_gen/dsl/gen_kernel/*` 实现与测试；任务点名 `worktree` 初始不存在，已按配置分支 `main` 在提交 `1477e823` 上补建当前 `worktree`。
最小功能闭环：5 份 `spec` 已把本轮允许实现与允许测试依赖的公开 API 集合统一到 `build_npu_demo_lowering_pipeline(...)`、`AttachArchInformationPass`、`OutlineDeviceKernelPass`、`gen_kernel(...)`、`emit_c(...) / emit_c_op(...) / emit_c_value(...)`；`KernelEmitter`、`kernel_emitter.py`、outline pattern/getter、pipeline 当前文件内 helper 均明确为非公开；standalone outline 验收链与本轮 `pytest` 链已单列。
改动：
- 更新 [`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../spec/pass/pipeline/npu_demo_lowering.md)，把当前文件公开面收成 `build_npu_demo_lowering_pipeline(...)`，补写 registry 名 `npu-demo-lowering` 属于 `spec/pass/registry.md`、当前文件内 helper 非公开、输出 IR 由 `gen_kernel(...)` / `emit_c(...)` 消费。
- 更新 [`spec/pass/attach_arch_information.md`](../../../../../../spec/pass/attach_arch_information.md)，把 `API 列表` 改成公开类与方法签名简表，并写清仅 `AttachArchInformationPass` 属于当前文件公开 API。
- 更新 [`spec/pass/outline_device_kernel.md`](../../../../../../spec/pass/outline_device_kernel.md)，把当前文件公开面从 `PassContractError + pattern + getter + pass` 缩成 `OutlineDeviceKernelPass`，移除 `default-lowering` 侧测试入口，改写为 standalone / `npu-demo-lowering` 双场景边界。
- 更新 [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../spec/dsl/gen_kernel/gen_kernel.md)，把公开 API 收成 `GenKernelError(message: str)` 与 `gen_kernel(obj: object, ctx: EmitCContext) -> str`，并明确 `KernelEmitter` / `kernel_emitter.py` helper 不再是公开 API。
- 更新 [`spec/dsl/gen_kernel/emit.md`](../../../../../../spec/dsl/gen_kernel/emit.md)，补齐 `emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)` 的签名，明确 `_dispatch_target`、target 私有 helper、`KernelEmitter` 与 `kernel_emitter.py` helper 不是公开 API。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check`：通过。
- `pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_pass_registry.py test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/emit/test_emit.py`
  - 结果：`175 passed, 15 warnings in 2.56s`。
  - 警告：xDSL `irdl_options list` 弃用告警与 `kernel_gen/passes/tile/elewise.py` 的 `IntegerAttr.from_int_and_width(...)` 弃用告警；本轮 `spec` 未改实现，先原样记录。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`
  - 结果：通过。
Diff 反推自测：
- 本轮 diff 直接涉及 5 份 `spec`，对应的实际公开链路与计划书点名测试为 `test/pass/test_pipeline_npu_demo_lowering.py`、`test/pass/test_attach_arch_information.py`、`test/pass/outline_device_kernel/test_outline_device_kernel.py`、`test/pass/test_pass_registry.py`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/dsl/gen_kernel/emit/test_emit.py`；已按这组文件执行 `pytest`，结果通过。
- `git diff --check` 已通过，用于补充校验文档改动的文本完整性。
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`：通过。
- 说明：`expectation.pass.outline_device_kernel` 只作为合同资产单列，不计入 `Diff 反推自测`。
真实自检：
- 只修改了当前任务点名的 5 份 `spec`，未改实现、测试或任何 `expectation` 文件。
- `API 列表` 都已紧跟在“功能简介”后，并改为签名简表；当前文件允许存在但不属于公开 API 的 helper 也已写清。
- 已核对现有实现 / 测试中的非公开 API 直连现状，并确认这些现状与本轮新合同不一致，需要下游 `build` 继续对齐：
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 仍直接导入 `OutlineDeviceKernelFuncPattern` 与 `get_outline_device_kernel_pass_patterns(...)`。
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 仍直接导入 `kernel_gen.dsl.gen_kernel.kernel_emitter`、实例化 `KernelEmitter`，并断言多个 `_` 前缀 helper。
  - [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py) 仍直接导入 `kernel_emitter` 并 monkeypatch `KernelEmitter`。
  - [`test/pass/test_pass_registry.py`](../../../../../../test/pass/test_pass_registry.py) 仍通过 `_reset_registry_for_test` 直连 registry 私有 helper。
- 邻近但未纳入本轮 `Diff 反推自测` 的 [`test/pass/test_pass_manager.py`](../../../../../../test/pass/test_pass_manager.py) 也存在 `_reset_registry_for_test` 直连，已一并记录给下游参考。
- 当前 `spec` 侧没有未决文字歧义；下游主要工作是让实现导出面与上述测试入口同新合同对齐。
结论：当前 S1 `spec` 已完成，可续到 `build`。下游需要按本轮 `spec` 调整实现导出与 `pytest` 入口，重点去掉测试对 `OutlineDeviceKernelFuncPattern`、`get_outline_device_kernel_pass_patterns(...)`、`KernelEmitter`、`kernel_emitter.py` 私有 helper 与 `_reset_registry_for_test` 的跨文件直连。

时间：2026-04-26 22:20 +0800
经办人：jcc你莫辜负
任务：T-20260426-dbabb1e3
任务目标：按 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md` 的 S1，把 `npu-demo-lowering / attach-arch-information / outline-device-kernel / gen_kernel emit` 的公开 API 与非公开 helper 收口到最新 `spec`，去掉 `pytest` 对跨文件非公开入口的直连，并补齐本轮 `build` 的真实自检、`Diff 反推自测` 与 standalone 合同验收。
执行前阅读记录：已读根仓 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 正文 / 全局完成态 / 验收设计、同文件内前序 `spec` 记录，以及当前 `worktree` 中的 [`kernel_gen/passes/outline_device_kernel.py`](../../../../../../kernel_gen/passes/outline_device_kernel.py)、[`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py)、[`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py)、[`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)、[`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)、[`test/pass/test_pass_registry.py`](../../../../../../test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](../../../../../../test/pass/test_pass_manager.py)、[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)、[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 当前现场。
最小功能闭环：当前 `build` 只收 4 个实现文件和 5 个测试文件，把公开入口固定为 `OutlineDeviceKernelPass`、`gen_kernel(...)`、`emit_c(...) / emit_c_op(...) / emit_c_value(...)`；outline pattern/getter、`KernelEmitter`、`kernel_emitter.py` helper 与 `_reset_registry_for_test` 不再作为跨文件可依赖入口；对应 `pytest` 只经由公开入口断言，standalone 只复跑 `expectation.pass.outline_device_kernel` 作为合同资产。
改动：
- 更新 [`kernel_gen/passes/outline_device_kernel.py`](../../../../../../kernel_gen/passes/outline_device_kernel.py)，补齐文件级 `API 列表`，把 `OutlineDeviceKernelFuncPattern` / `get_outline_device_kernel_pass_patterns(...)` 改为当前文件内部 `_OutlineDeviceKernelFuncPattern` / `_get_outline_device_kernel_pass_patterns(...)`，并把 `__all__` 收成 `["OutlineDeviceKernelPass"]`。
- 更新 [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py)，移除 package export 对 outline pattern/getter 的再导出，保留 `OutlineDeviceKernelPass` 作为 package 公开入口，并同步文件头 `API 列表`。
- 更新 [`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py) 和 [`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py)，补齐文件级 `API 列表`，移除 `KernelEmitter` 的包根 / 模块公开导出，只保留 `GenKernelError`、`gen_kernel(...)` 以及 package 级 `EmitCContext` / `EmitCError` / `emit_c*` 入口。
- 更新 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)，不再导入 outline pattern/getter，改为验证 `__all__` 与公开边界只剩 `OutlineDeviceKernelPass`。
- 更新 [`test/pass/test_pass_registry.py`](../../../../../../test/pass/test_pass_registry.py) 和 [`test/pass/test_pass_manager.py`](../../../../../../test/pass/test_pass_manager.py)，把 `_reset_registry_for_test` 直连替换为当前测试文件内的公开 `importlib.reload(...)` 隔离 helper。
- 更新 [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)，删除对 `kernel_emitter` 的 monkeypatch，改为通过 `emit_c(...)` / `gen_kernel(...)` 黑盒比较单函数 `func.func` 与单函数 `builtin.module` 的一致行为。
- 更新 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)，移除对 `KernelEmitter`、`kernel_emitter.py` 私有 helper 和 `gen_kernel_entry_module.__getattr__` 的直接调用；把包根 / 模块公开边界断言收成 `__all__` 与缺失入口检查，并删去不再允许的私有 helper 测试块。
验证：
- `python3 -m py_compile kernel_gen/dsl/gen_kernel/__init__.py kernel_gen/dsl/gen_kernel/gen_kernel.py kernel_gen/passes/outline_device_kernel.py kernel_gen/passes/__init__.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/dsl/gen_kernel/emit/test_emit.py test/dsl/gen_kernel/test_gen_kernel.py`：通过。
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check`：通过。
Diff 反推自测：
- `pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_attach_arch_information.py test/pass/test_pipeline_npu_demo_lowering.py`
  - 结果：`66 passed, 1 warning in 0.40s`。
- `pytest -q test/dsl/gen_kernel/emit/test_emit.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：`114 passed, 9 warnings in 2.35s`。
- 说明：本轮 `Diff 反推自测` 只包含 `pytest`；`py_compile` 与 `git diff --check` 仅作补充校验，不并入 `Diff 反推自测`。
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`
  - 结果：通过。
- 说明：`expectation.pass.outline_device_kernel` 只作为合同资产单列，不计入 `Diff 反推自测`。
真实自检：
- 已核对本轮改动没有新增 `spec` 未定义的公开接口；实现文件新增的只有当前文件内 helper 重命名，不引入跨文件新公开面。
- 已核对本轮改动没有写入、移动、重命名任何 `expectation` 文件；standalone 合同验收只读执行。
- 已核对改动后的 5 个测试文件不再通过跨文件直连 `OutlineDeviceKernelFuncPattern`、`get_outline_device_kernel_pass_patterns(...)`、`KernelEmitter`、`kernel_emitter.py` helper 或 `_reset_registry_for_test` 完成断言。
- 已核对实现文件头 `API 列表` 与当前 `spec` 一致：`kernel_gen/dsl/gen_kernel/__init__.py`、`kernel_gen/dsl/gen_kernel/gen_kernel.py`、`kernel_gen/passes/outline_device_kernel.py`、`kernel_gen/passes/__init__.py` 都已同步。
- 风险复查：`test/tools/test_ircheck_runner.py` 与 `test/tools/test_ircheck_cli.py` 仍保留 `_reset_registry_for_test` 直连，但不在本轮点名 `diff` / 计划书 S1 收口边界内，先不外扩。
结论：当前 S1 `build` 已完成，可续到 `review`。下游重点是复核公开导出是否完全对齐最新 `spec`，以及本轮删减私有 helper 测试后，现有公开链路用例是否仍足够覆盖回归面。

时间：2026-04-26 22:57 +0800
经办人：提莫炖蘑菇
任务：T-20260426-dbabb1e3
任务目标：复核 S1 公开 API / 非公开 helper / pytest / standalone 验收链收口结果。
执行前阅读记录：已读根仓 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 正文 / 全局完成态 / 验收设计、当前任务记录内 `spec/build` 前序记录，以及当前 `worktree` residual diff 对应的 [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py)、[`kernel_gen/passes/outline_device_kernel.py`](../../../../../../kernel_gen/passes/outline_device_kernel.py)、[`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py)、[`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)、[`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../spec/pass/pipeline/npu_demo_lowering.md)、[`spec/pass/attach_arch_information.md`](../../../../../../spec/pass/attach_arch_information.md)、[`spec/pass/outline_device_kernel.md`](../../../../../../spec/pass/outline_device_kernel.md)、[`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../spec/dsl/gen_kernel/gen_kernel.md)、[`spec/dsl/gen_kernel/emit.md`](../../../../../../spec/dsl/gen_kernel/emit.md)、[`test/pass/test_pass_registry.py`](../../../../../../test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](../../../../../../test/pass/test_pass_manager.py)、[`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)、[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)、[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py) 现场。
真实审查：
- 当前 standalone 合同验收链仍成立：`expectation.pass.outline_device_kernel` 可通过，且本轮没有改写任何 `expectation` 文件。
- `outline-device-kernel` 侧的旧 pattern/getter 公开面已经从测试入口撤出；[`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 现在只验证 `OutlineDeviceKernelPass` 的公开边界，这部分没有回退。
- 但 residual diff 里仍存在 2 个当前切片内可直接修正的问题：
  - [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py) 的文件级 `API 列表` 仍是裸名称清单，如 `Pass`、`PassManager`、`InlinePass`、`AttachArchInformationPass`、`OutlineDeviceKernelPass` 等都没有参数签名，和当前“实现文件改动必须同步维护文件级 API 简表，且列公开 API 与参数签名”的规则不一致。
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 仍跨文件直连非公开 API `kernel_gen.execute_engine.compiler._run_compiler_command(...)`：
    - [`test/dsl/gen_kernel/test_gen_kernel.py:612`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L612)
    - [`test/dsl/gen_kernel/test_gen_kernel.py:629`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L629)
    - [`test/dsl/gen_kernel/test_gen_kernel.py:669`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L669)
    - [`test/dsl/gen_kernel/test_gen_kernel.py:686`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L686)
    - [`test/dsl/gen_kernel/test_gen_kernel.py:831`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L831)
    - [`test/dsl/gen_kernel/test_gen_kernel.py:834`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L834)
    - [`test/dsl/gen_kernel/test_gen_kernel.py:891`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L891)
- 上述第 2 点命中最新审查硬规则：“测试不得跨当前文件直连非公开 API”，不能以“只为编译复用 / 当前能跑”为理由放行。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/emit/test_emit.py -ra`
  - 结果：`180 passed, 9 warnings in 2.30s`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/passes/__init__.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/passes/outline_device_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/dsl/gen_kernel/__init__.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/dsl/gen_kernel/gen_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/test_gen_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/emit/test_emit.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check`
  - 结果：通过
Diff 反推审查：
- 当前 diff 涉及 `pass/pipeline` 与 `gen_kernel/emit` 的 spec / 实现 / pytest，因此按 residual diff 反推执行：
  - `test/pass/test_pipeline_npu_demo_lowering.py`
  - `test/pass/test_attach_arch_information.py`
  - `test/pass/outline_device_kernel/test_outline_device_kernel.py`
  - `test/pass/test_pass_registry.py`
  - `test/pass/test_pass_manager.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/dsl/gen_kernel/emit/test_emit.py`
- 上述 `pytest` 结果通过，但不改变“测试仍跨文件直连非公开 API”的审查结论。
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`
  - 结果：通过
- 说明：`expectation.pass.outline_device_kernel` 只作为合同资产单列，不计入 `Diff 反推审查`。
可改进点：
- 先把 [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py) 的文件级 `API 列表` 改成签名索引，再让 `build` 记录中的“文件头 API 列表已同步”与现场一致。
- 把 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 的本地编译辅助断言改成只验证 `gen_kernel(...)` 公开输出与可编译结果，不再 monkeypatch 或调用 `compiler._run_compiler_command(...)`。
结论：`需修改`。当前 standalone 合同验收与 diff 反推 pytest 都是绿的，但 residual diff 仍命中文件级 API 简表缺签名、测试跨文件直连非公开 API 两个硬性问题，不能进入 `merge`。

时间：2026-04-26 22:30 +0800
经办人：小李飞刀
任务：T-20260426-dbabb1e3
任务目标：按 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md` 的当前 build 边界，修复 `kernel_gen/passes/__init__.py` 文件级 API 简表缺少签名，以及 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 跨文件直连 `compiler._run_compiler_command(...)` 非公开 API 的问题；不改 `expectation`，不扩到无关资产。
执行前阅读记录：已重读根仓 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 正文 / 全局完成态 / 验收设计、本记录内前序 `spec/build/review` 条目，以及被点名的 [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py) 与 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 当前现场。
最小功能闭环：只收两处 review 退回项：1）`kernel_gen.passes` package 根文件头 `API 列表` 改成带参数签名的快速索引；2）`test_gen_kernel.py` 的本地编译路径改为当前测试文件内 `_run_local_compile_command(...)` 统一入口，不再直连当前文件之外的非公开编译 helper。
改动：
- 更新 [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py)：
  - 把文件级 `API 列表` 从裸名称清单改成带签名的索引，补齐 `Pass.run(...)`、`Pass.apply(...)`、`PassManager.add_pass(...)`、`PassManager.extend(...)`、`PassManager.run(...)` 以及各公开 class / pattern getter 的签名。
- 更新 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)：
  - 删除 `from kernel_gen.execute_engine import compiler as compiler_module`。
  - 新增当前测试文件内 `_run_local_compile_command(command: list[str]) -> subprocess.CompletedProcess[str]`。
  - `_compile_and_run(...)`、`_compile_only(...)`、`_compile_and_run_npu_demo_add_barrier_source(...)` 全部改为调用当前文件内 helper。
  - 相关函数说明与回归测试同步改为“当前文件内统一编译入口”口径；不再 monkeypatch 或调用当前文件之外的非公开编译 API。
验证：
- `pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/dsl/gen_kernel/test_gen_kernel.py -ra`
  - 结果：`132 passed, 9 warnings in 2.47s`
  - 警告：xDSL `irdl_options list` 弃用告警，以及 `kernel_gen/passes/tile/elewise.py` 里 `IntegerAttr.from_int_and_width(...)` 的弃用告警；本轮未触达这些实现。
- `python3 -m py_compile kernel_gen/passes/__init__.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check`
  - 结果：通过
- `rg -n "compiler_module|_run_compiler_command" test/dsl/gen_kernel/test_gen_kernel.py kernel_gen/passes/__init__.py`
  - 结果：无命中
Diff 反推自测：
- 本轮 diff 直接涉及 `kernel_gen/passes/__init__.py` 与 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)；对应公开链路和包根导入消费面回归执行：
  - `test/pass/test_pipeline_npu_demo_lowering.py`
  - `test/pass/test_attach_arch_information.py`
  - `test/pass/outline_device_kernel/test_outline_device_kernel.py`
  - `test/pass/test_pass_registry.py`
  - `test/pass/test_pass_manager.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
- 以上 `pytest` 结果通过；`py_compile`、`rg` 与 `git diff --check` 仅作补充校验，不计入 `Diff 反推自测`。
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`
  - 结果：通过
- 说明：`expectation.pass.outline_device_kernel` 只作为合同资产单列，不计入 `Diff 反推自测`。
真实自检：
- 未修改、移动、重命名或新建任何 `expectation` 文件。
- 未新增 `spec` 未定义的公开接口；`kernel_gen/passes/__init__.py` 只补文件头签名索引，没有扩大公开导出集合。
- 已核对 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 不再直连当前文件之外的非公开 `compiler._run_compiler_command(...)`；当前保留的 monkeypatch 只作用于本测试文件内 `_run_local_compile_command(...)`，不触碰产品代码的外部私有入口。
- 已核对这轮没有回退 `gen_kernel(...)`、`emit_c(...)`、`OutlineDeviceKernelPass` 等既有公开链路的 `pytest` 与合同验收结果。
结论：当前 review 退回项已收口，可续到 `review`。

时间：2026-04-26 22:53 +0800
经办人：jcc你莫辜负
任务：T-20260426-dbabb1e3
任务目标：复核 [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py) 的 API 简表签名索引，以及 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 本地编译 helper 的公开边界收口结果；确认当前 residual diff 是否还能继续收紧。
执行前阅读记录：已读根仓 [`TODO.md`](../../../../../../TODO.md) 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 / 全局完成态 / 验收设计、本记录内前序 `spec/build/review` 条目，以及当前 `worktree` 中的 [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../spec/dsl/gen_kernel/gen_kernel.md)、[`spec/dsl/gen_kernel/emit_context.md`](../../../../../../spec/dsl/gen_kernel/emit_context.md)、[`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py)、[`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)、[`kernel_gen/dsl/gen_kernel/emit_context.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit_context.py)、[`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py)、[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 当前现场与 residual diff。
改动：
- 本轮只追加复审记录，未修改实现、测试、`spec` 或任何 `expectation` 文件。
- 已确认前一轮 build 的两个退回点已经收口：
  - [`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py) 的文件级 `API 列表` 已改成带签名索引。
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 已删除对 `kernel_gen.execute_engine.compiler._run_compiler_command(...)` 的跨文件直连，编译路径改为当前测试文件内 `_run_local_compile_command(...)`。
- 但当前 residual diff 里仍有 1 个本任务边界内、可直接执行的改进点：
  - [`test/dsl/gen_kernel/test_gen_kernel.py:1017`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L1017)、[`test/dsl/gen_kernel/test_gen_kernel.py:1036`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L1036)-[`1044`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L1044)、[`test/dsl/gen_kernel/test_gen_kernel.py:1071`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py#L1071) 仍直接断言 `gen_kernel_entry_module.__all__`、`gen_kernel_module.__all__`、`emit_context_module.__all__`。
  - 这些 `__all__` 断言没有进入 [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../spec/dsl/gen_kernel/gen_kernel.md) 的 `API 列表`、[`spec/dsl/gen_kernel/emit_context.md`](../../../../../../spec/dsl/gen_kernel/emit_context.md) 的 `API 列表`，也不在 [`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py) / [`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py) 文件级公开 `API 列表` 中；当前公开合同只定义可导入符号和可调用入口，不定义模块元数据列表值。
  - 这意味着 `test_gen_kernel` 还在把未进入合同的模块元数据当成公开面。应改成只验证公开导入行为与公开对象可达性，例如 `from ... import *` 的结果集、直接 attribute 可达性、旧入口不可导入等，而不是锁 `__all__` 的具体列表顺序和值。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/dsl/gen_kernel/emit/test_emit.py test/dsl/gen_kernel/test_gen_kernel.py -ra`
  - 结果：`180 passed, 9 warnings in 2.69s`
- `python3 -m py_compile kernel_gen/passes/__init__.py test/dsl/gen_kernel/test_gen_kernel.py && git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check`
  - 结果：通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`
  - 结果：通过
Diff 反推审查：
- 当前 residual diff 涉及 `pass/pipeline` 与 `gen_kernel/emit` 的 `spec / 实现 / pytest`，按实际 diff 反推审查并执行：
  - `test/pass/test_pipeline_npu_demo_lowering.py`
  - `test/pass/test_attach_arch_information.py`
  - `test/pass/outline_device_kernel/test_outline_device_kernel.py`
  - `test/pass/test_pass_registry.py`
  - `test/pass/test_pass_manager.py`
  - `test/dsl/gen_kernel/emit/test_emit.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
- 上述 `pytest` 结果通过；`py_compile` 与 `git diff --check` 仅作补充校验，不计入 `Diff 反推审查`。
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`
  - 结果：通过
- 说明：`expectation.pass.outline_device_kernel` 只作为合同资产单列，不计入 `Diff 反推审查`。
自检：
- 已逐项复核这轮点名的 `API` 简表签名索引和本地编译 helper 边界；未越权改 `expectation`、未新增 `spec` 未定义的公开入口、未把跨文件非公开 `API` 问题放过。
- 特殊情况、异常、兼容和测试有效性已检查；本轮 `pytest` 虽全绿，但仍能明确指出 `test_gen_kernel` 使用 `__all__` 断言未入合同的模块元数据，这属于当前 diff 内可直接收紧的问题。
- 审查记录已按实际 diff 反推补齐；当前结论仅基于可执行问题，不依赖泛泛建议。
结论：`需修改`。前一轮 build 退回的“签名索引缺失”和“跨文件直连非公开编译 helper”已收口，但 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 仍把 `__all__` 当公开合同；请下一轮 build 把这些断言改成只验证 `spec` 已定义的公开导入行为与公开对象可达性，再回流 `review`。

时间：2026-04-26 23:40 +0800
经办人：金铲铲大作战
任务：T-20260426-dbabb1e3
任务目标：按 review 结论收紧 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 中未入 `spec/API 列表` 的 `__all__` 断言，改成只验证 `gen_kernel` 包根、[`gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py) 与 [`emit_context.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit_context.py) 的公开导入行为和公开对象可达性；不改实现文件，不改 `expectation`。
执行前阅读记录：已重读根仓 [`TODO.md`](../../../../../../TODO.md) 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 / 全局完成态 / 验收设计、本记录内前序 `spec/build/review` 条目，以及当前现场的 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)、[`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py)、[`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)、[`kernel_gen/dsl/gen_kernel/emit_context.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit_context.py)。
最小功能闭环：只收 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 的 3 处 `__all__` 断言，改成公开 `import` 行为与公开对象可达性检查；保留旧入口 `KernelEmitter`、`gen_signature`、`gen_body` 的不可导入 / 不可达边界，不扩到实现导出面。
改动：
- 更新 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)：
  - 文件头 `最后一次更改` 同步为 `金铲铲大作战`。
  - `test_gen_kernel_entry_module_hides_internal_emitter_entry()` 不再断言 `gen_kernel_entry_module.__all__`，改为只验证 `GenKernelError` / `gen_kernel` 可公开导入且 `KernelEmitter` 不可导入。
  - `test_gen_kernel_is_the_package_public_entry()` 不再断言 `gen_kernel_module.__all__` 与 `emit_context_module.__all__`，改为只验证包根 `import *` 的公开结果集、`gen_kernel.py` / `emit_context.py` 的公开对象可达性，以及旧 `gen_signature` / `gen_body` 不进入公开结果集。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate pytest -q test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/emit/test_emit.py -ra`
  - 结果：`114 passed, 9 warnings in 3.14s`
  - 警告：xDSL `irdl_options list` 弃用告警，以及 [`kernel_gen/passes/tile/elewise.py`](../../../../../../kernel_gen/passes/tile/elewise.py) 里的 `IntegerAttr.from_int_and_width(...)` 弃用告警；本轮未触达这些实现。
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check`
  - 结果：通过
Diff 反推自测：
- 本轮 diff 只涉及 [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)，对应公开入口与相邻公开发射链回归执行：
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/dsl/gen_kernel/emit/test_emit.py`
- 上述 `pytest` 结果通过；`py_compile` 与 `git diff --check` 仅作补充校验，不计入 `Diff 反推自测`。
合同验收（如适用）：
- 本轮未执行 `expectation`。
- 说明：当前 diff 只收公开测试边界，不涉及实现或合同资产内容变化；`expectation` 继续只作合同验收资产单列，不计入 `Diff 反推自测`。
真实自检：
- 未修改、移动、重命名或新建任何 `expectation` 文件。
- 未新增 `spec` 未定义的公开接口，也未回退当前 `spec / pytest` 已定义的包根公开入口。
- 当前改动只验证 `spec` 已定义的公开导入行为与公开对象可达性，不再把 `__all__` 这种未入合同的模块元数据当成公开 API。
- 测试没有跨文件调用非公开 API；旧入口的边界断言只保留“不可导入 / 不可达”的公开失败面。
结论：本轮 review 退回项已收口，可续到 `review`。

时间：2026-04-26 23:59 +0800
经办人：不要啊教练
任务：T-20260426-dbabb1e3
任务目标：复核 `test_gen_kernel.py` 去掉未入 `spec/API` 列表的 `__all__` 断言后，S1 residual diff 的公开测试边界是否已完全收口；重点检查 `gen_kernel/emit` 与 `outline-device-kernel` 相关测试是否仍直连未定义公开接口。
执行前阅读记录：已读根仓 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 正文 / 当前基线 / 公开 API 设计 / 完成态、当前任务记录内前序 `spec/build/review` 条目，以及当前现场的 [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../spec/dsl/gen_kernel/gen_kernel.md)、[`spec/dsl/gen_kernel/emit.md`](../../../../../../spec/dsl/gen_kernel/emit.md)、[`spec/dsl/gen_kernel/emit/register.md`](../../../../../../spec/dsl/gen_kernel/emit/register.md)、[`spec/pass/outline_device_kernel.md`](../../../../../../spec/pass/outline_device_kernel.md)、[`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py)、[`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)、[`kernel_gen/passes/outline_device_kernel.py`](../../../../../../kernel_gen/passes/outline_device_kernel.py)、[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)、[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)、[`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)、[`test/pass/test_pass_registry.py`](../../../../../../test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](../../../../../../test/pass/test_pass_manager.py) 当前现场。
真实审查：
- [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 这轮 build 目标已经达成：此前未入合同的 `__all__` 断言已移除，当前只验证 `kernel_gen.dsl.gen_kernel` 包根、[`gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py) 与 [`emit_context.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit_context.py) 的公开导入行为和公开对象可达性。
- [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py) 仍直接使用 `kernel_gen.dsl.gen_kernel.emit.register`，但 [`spec/dsl/gen_kernel/emit/register.md`](../../../../../../spec/dsl/gen_kernel/emit/register.md) 已把注册器与 dispatch 明确定义为公开 API，因此这条不构成当前阻断。
- 当前 residual diff 的阻断点转移到 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)：
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py:136`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py#L136) 仍直接断言 `direct_module.__all__ == ["OutlineDeviceKernelPass"]`。
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py:157`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py#L157) 仍直接经 `direct_module.PassContractError` 观测当前文件模块命名空间。
- 以上两点都不在 [`spec/pass/outline_device_kernel.md`](../../../../../../spec/pass/outline_device_kernel.md) 的 `API 列表` 中。该 `spec` 已明确“当前文件级公开 API 只包含 `OutlineDeviceKernelPass`；pattern、候选收集、属性规整与 wrapper/device 改写步骤不额外暴露文件级 helper，跨文件实现与测试不得直连这些内部步骤”，同时也没有把 `__all__` 或当前文件模块上的 `PassContractError` 定义成稳定公开面。
- 因此，虽然 `pytest` 全绿，这轮 residual diff 仍命中“测试直连未定义公开接口 / 模块元数据”的硬规则，不能通过。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/emit/test_emit.py -ra`
  - 结果：`180 passed, 9 warnings in 3.37s`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/passes/__init__.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/passes/outline_device_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/dsl/gen_kernel/__init__.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/dsl/gen_kernel/gen_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/test_gen_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/emit/test_emit.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check`
  - 结果：通过
合同验收（如适用）：
- 本轮未重复执行 `expectation.pass.outline_device_kernel`；前序 build 记录已单列通过，本轮只复核 residual diff 的公开测试边界，不把 `expectation` 计入 `Diff 反推审查`。
可改进点：
- 把 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 中对 `direct_module.__all__` 的断言改成只验证 [`spec/pass/outline_device_kernel.md`](../../../../../../spec/pass/outline_device_kernel.md) 已定义的公开导入行为，例如 `OutlineDeviceKernelPass` 可导入、旧 pattern/getter 不可达。

时间：2026-04-26 23:54 +0800
经办人：jcc你莫辜负
任务：T-20260426-dbabb1e3
任务目标：复核 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 是否已去掉对 `direct_module.__all__` 与 `direct_module.PassContractError` 的直连，只保留 `spec` 已定义的 `OutlineDeviceKernelPass` 公开导入与不可达边界断言。
执行前阅读记录：已读根仓 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 / 完成态 / 验收设计、当前任务记录前序 `spec/build/review` 条目，以及当前现场的 [`spec/pass/outline_device_kernel.md`](../../../../../../spec/pass/outline_device_kernel.md)、[`kernel_gen/passes/outline_device_kernel.py`](../../../../../../kernel_gen/passes/outline_device_kernel.py)、[`kernel_gen/passes/__init__.py`](../../../../../../kernel_gen/passes/__init__.py)、[`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)。
改动：本轮为 `review`，未改实现或测试文件；已逐项核对 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 当前内容，确认：
- 原先对 `direct_module.__all__` 的断言已删除。
- 原先对 `direct_module.PassContractError` 的直连已删除。
- 当前文件只保留 `OutlineDeviceKernelPass` 的公开可达断言，以及旧 pattern/getter 在 direct/compat 模块上的不可达边界断言。
- `PassContractError` 仅作为 [`kernel_gen.passes`](../../../../../../kernel_gen/passes/__init__.py) 的共享公开错误类型在失败路径测试中使用，和 [`spec/pass/outline_device_kernel.md`](../../../../../../spec/pass/outline_device_kernel.md) 当前口径一致。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -ra`
  - 结果：`14 passed, 1 warning in 0.21s`
- `python3 -m py_compile test/pass/outline_device_kernel/test_outline_device_kernel.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check -- test/pass/outline_device_kernel/test_outline_device_kernel.py`
  - 结果：通过
- `rg -n "direct_module\\.__all__|direct_module\\.PassContractError" test/pass/outline_device_kernel/test_outline_device_kernel.py`
  - 结果：无命中
Diff 反推审查：
- 本轮审查 diff 聚焦 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 的公开边界回改；已按该文件直接反推执行 `pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -ra`，并辅以 `py_compile`、`git diff --check` 与 `rg` 文本核对。
- `pytest` 中唯一警告为 xDSL `irdl_options list` deprecation warning，不是这轮回改引入的问题。
合同验收（如适用）：
- 本轮未重复执行 `expectation.pass.outline_device_kernel`；原因：当前 diff 只收测试公开边界，且前序 `build` 记录已单列通过。`expectation` 继续只作合同资产，不计入 `Diff 反推审查`。
自检：
- 已逐行复核目标文件与对应 `spec`、实现导出面、共享错误类型口径；特殊情况、边界、可维护性和测试有效性已检查。
- 本轮未越权改任何文件；未发现这次回改范围内仍可直接指出的一线可执行问题。
- 审查已按实际 diff 反推；当前断言只验证 `spec` 已定义的公开导入行为和不可达边界，没有再把模块元数据当成公开合同。
结论：通过，可续到 `merge`。
- 去掉经 `direct_module.PassContractError` 观测当前文件模块命名空间的断言；如果需要锁共享错误类型，应只经 [`kernel_gen.passes`](../../../../../../kernel_gen/passes/__init__.py) 这个已定义公开 package-root 入口观测。
结论：`需修改`。`test_gen_kernel.py` 的 `__all__` 边界返修已收口，但同一 residual diff 里的 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 仍把未入 `spec/API 列表` 的模块元数据与当前文件模块命名空间当成公开测试入口，不能进入 `merge`。

---

时间：2026-04-26 23:03:57 +0800
经办人：朽木露琪亚
任务：T-20260426-dbabb1e3 / S1 build 复修
任务目标：去掉 [test/pass/outline_device_kernel/test_outline_device_kernel.py](/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py) 对 `direct_module.__all__` 与 `direct_module.PassContractError` 的直连，只保留 [spec/pass/outline_device_kernel.md](/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/spec/pass/outline_device_kernel.md) 已定义的 `OutlineDeviceKernelPass` 公开导入 / 不可达边界断言。
执行前阅读记录：
- 已核对 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认 `T-20260426-dbabb1e3` 当前为 `build / 朽木露琪亚 / 进行中`。
- 已重读 [ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 正文、全局完成态 / 验收设计、当前任务记录中前序 build / review 结论。
- 已复核 [spec/pass/outline_device_kernel.md](/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/spec/pass/outline_device_kernel.md)、[kernel_gen/passes/outline_device_kernel.py](/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/passes/outline_device_kernel.py) 与 [test/pass/outline_device_kernel/test_outline_device_kernel.py](/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py) 当前现场，确认当前文件级公开 API 只包含 `OutlineDeviceKernelPass`，`PassContractError` 属于 `kernel_gen.passes` 共享公开 API，不是当前文件独立入口。
最小功能闭环：
- `test_outline_device_kernel_public_entry_hides_internal_pattern_helpers()` 只验证 `OutlineDeviceKernelPass` 可达，以及内部 pattern helper 不可达。
- `test_outline_device_kernel_lowering_compat_import_matches_rehome_entry()` 只验证 direct / compat / package 三个公开导入路径对 `OutlineDeviceKernelPass` 的一致性，以及内部 helper 不可达。
- 不改实现文件，不改 `expectation`，不扩大到其它 pass / gen_kernel 资产。
改动：
- 更新 [test/pass/outline_device_kernel/test_outline_device_kernel.py](/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - 删除 `from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelFuncPattern, get_outline_device_kernel_pass_patterns` 这组未入当前文件 `spec/API 列表` 的直连导入。
  - 将 `test_outline_device_kernel_public_entry_hides_internal_pattern_helpers()` 改为断言 `direct_module.OutlineDeviceKernelPass is OutlineDeviceKernelPass`，并通过 `AttributeError` 锁定 `OutlineDeviceKernelFuncPattern` / `get_outline_device_kernel_pass_patterns` 不可达。
  - 将 `test_outline_device_kernel_lowering_compat_import_matches_rehome_entry()` 改为只校验 `compat_module` / `direct_module` / `package_module` 对 `OutlineDeviceKernelPass` 的公开导入一致性，并移除 `direct_module.PassContractError` 直连断言。
  - 同步更新两段测试头注释的 `最后一次更改` 与功能说明，使其与当前公开边界保持一致。
Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -ra` -> `14 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py` -> 通过
- `rg -n "direct_module\\.__all__|direct_module\\.PassContractError" /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py` -> 无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check` -> 通过
真实自检：
- 本轮只改测试文件，没有新增任何 `spec` 未定义的公开 API，也没有回退 `OutlineDeviceKernelPass` 现有公开导入路径。
- 测试边界已收紧到 `spec` 明确承认的 `OutlineDeviceKernelPass` 可导入性和内部 helper 不可达性，不再把模块元数据 `__all__` 或当前文件模块命名空间上的 `PassContractError` 当成公开合同。
- 未修改、移动、重命名或新建任何 `expectation` 文件；`expectation` 继续只读。
- 未跨文件调用非公开 API；保留的 `PassContractError` 断言只用于真正的错误路径测试，并通过 `kernel_gen.passes` 共享公开入口观测。
合同验收（如适用）：
- 本轮未执行 `expectation`。
- 原因：当前 diff 只收 `outline_device_kernel` 公开测试边界；`expectation` 继续只作合同验收资产单列，不计入 `Diff 反推自测`。
结论：
- review 退回的 `direct_module.__all__` 与 `direct_module.PassContractError` 直连问题已收口。
- 当前 worktree 可按 TODO 继续流转到下一轮 `review`。

时间：2026-04-26 23:59 +0800
经办人：李白
任务：T-20260426-dbabb1e3
任务目标：把 `wt-20260426-npu-pipeline-outline-s1` 上已通过 review 的 S1 residual diff 重放到 latest `origin/main`，完成 `outline-device-kernel / gen_kernel` 合同收口改动的 merge、推送和状态收尾。
执行前阅读记录：已重读根仓 [`TODO.md`](../../../../../../TODO.md) 当前任务行、[`ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md) 的 S1 / 全局完成态 / 验收设计、本记录内前序 `spec/build/review` 条目，以及当前 `worktree` 的实际 residual diff 和 `origin/main` 最新基线。
最小功能闭环：以 `origin/main@f4cee804ce075ee88197a6858e80748eaec2a13f` 为 merge 现场，重放原基线 `1477e823977b720e92b297400eb279e796b08271` 上的 S1 residual diff；冲突只允许收口到任务点名的 `gen_kernel` 包根 / 模块公开合同，不扩到 `dsl_run`、`execute_engine` 或任何 `expectation` 写入。
改动：
- 在 `/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1` 内执行 `stash -> detach origin/main -> stash pop` 重放；实际冲突只有：
  - [`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py)
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
- 解决 [`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../kernel_gen/dsl/gen_kernel/__init__.py) 冲突时，保留 package-root 公开入口为 `gen_kernel(...)`、`emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)`、`EmitCContext`、`EmitCError`、`GenKernelError`，不把 `KernelEmitter` 回退成公开 API。
- 解决 [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../spec/dsl/gen_kernel/gen_kernel.md) 冲突时，保留当前文件只定义 `kernel_gen.dsl.gen_kernel.gen_kernel` 模块合同，公开 `API 列表` 只包含 `GenKernelError(message: str)` 与 `gen_kernel(obj: object, ctx: EmitCContext) -> str`，并明确 `KernelEmitter` / `kernel_emitter.py` helper 不是公开 API。
- 其余 residual diff 直接沿用已通过 review 的现场，不新增额外实现、测试或合同资产改动。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pipeline_npu_demo_lowering.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_attach_arch_information.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/test_gen_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/emit/test_emit.py -ra`
  - 结果：`180 passed, 9 warnings in 3.62s`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`
  - 结果：通过
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/dsl/gen_kernel/__init__.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/dsl/gen_kernel/gen_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/passes/__init__.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/kernel_gen/passes/outline_device_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/pass/outline_device_kernel/test_outline_device_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/test_gen_kernel.py /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1/test/dsl/gen_kernel/emit/test_emit.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1 diff --check`
  - 结果：通过
Diff 反推自测：
- 本轮实际 diff 涉及 `kernel_gen/dsl/gen_kernel/*`、`kernel_gen/passes/outline_device_kernel.py`、`kernel_gen/passes/__init__.py`、对应 `spec/pass/*`、`spec/dsl/gen_kernel/*`、以及 `test/pass/*` / `test/dsl/gen_kernel/*`；对应公开链路已按以下测试反推执行：
  - `test/pass/test_pipeline_npu_demo_lowering.py`
  - `test/pass/test_attach_arch_information.py`
  - `test/pass/outline_device_kernel/test_outline_device_kernel.py`
  - `test/pass/test_pass_registry.py`
  - `test/pass/test_pass_manager.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/dsl/gen_kernel/emit/test_emit.py`
- 上述 `pytest` 已通过；`py_compile` 与 `git diff --check` 仅作补充校验，不计入 `Diff 反推自测`。
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-npu-pipeline-outline-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`：通过。
- 说明：`expectation.pass.outline_device_kernel` 只作为合同资产单列，不计入 `Diff 反推自测`；本轮 merge 未修改任何 `expectation` 文件。
真实自检：
- replay 冲突只收在任务点名的 `gen_kernel` 包根 / 模块合同，没有把 `KernelEmitter`、outline pattern/getter 或其他内部 helper 回退成公开 API。
- 本轮 merge 不涉及 `expectation` 写入，也未引入 `dsl_run` / `execute_engine` 范围外改动。
- root 仓同步只会在 `push` 后执行 `fetch` / 安全 `ff-only`；若被现有本地状态挡住，只记录阻塞，不覆盖。
结论：当前 `worktree` 上的 S1 residual diff 已完成 merge 收口，可提交、推送并执行 `-done`。
