时间：2026-04-24 00:45 +0800
经办人：咯咯咯
任务：T-20260423-e1e94e87
任务目标：按计划书 S2 收口 `buffer_results_to_out_params` / `nn_to_kernel` compat shim 的 spec 边界，并把 surviving 导入与后续 build 验证要求写回记录
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:5) 当前任务行，确认 `worktree`、计划书、记录文件与任务指派一致。
- 已读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md:349) 的 `S2` 正文、全局完成态、合同真源顺序、消费者迁移矩阵与验收设计。
- 已读前序记录 [`agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md)。
- 已读当前 worktree 的 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/registry.md)、[`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/pass_manager.md)、[`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/lowering/buffer_results_to_out_params.md)、[`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/lowering/nn_lowering/spec.md)。
- 已读相关 pytest 与实现入口：[`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py)、[`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py)、[`kernel_gen/passes/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/__init__.py)、[`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/buffer_results_to_out_params.py)、[`kernel_gen/passes/lowering/nn_to_kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/nn_to_kernel.py)。
最小功能闭环：
- 把 out-param / nn lowering caller 的 surviving public path 明确收口到 `kernel_gen.passes.buffer_results_to_out_params` 与 `kernel_gen.passes.lowering.nn_lowering`。
- 把 `kernel_gen.passes.lowering.buffer_results_to_out_params` 与 `kernel_gen.passes.lowering.nn_to_kernel` 明确改写为旧模块失败边界，要求下游 build 用 `pytest` 证明“新路径成功 + 旧路径失败”。
- 单列写清 `expectation` 只作合同验收资产，不替代本轮 diff 反推 pytest。
改动：
- 更新 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/registry.md)，新增 `S2` 导入矩阵补充，写明 out-param / nn lowering caller 的 canonical path、两个 compat shim 的失败边界，以及 `pytest` 与 `expectation` 的分工。
- 更新 [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/lowering/buffer_results_to_out_params.md)，新增 `导入与兼容边界`，把 canonical import 固定为 `kernel_gen.passes.buffer_results_to_out_params`，并把 `kernel_gen.passes.lowering.buffer_results_to_out_params` 写成 `ModuleNotFoundError` 失败口径。
- 更新 [`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/lowering/nn_lowering/spec.md)，把 canonical import 固定为 `kernel_gen.passes.lowering.nn_lowering`，并写明 `kernel_gen.passes.lowering.nn_to_kernel` 与 `LowerNnToKernelPass` 不再属于 surviving public contract。
- 当前 spec 同时要求下游 build 更新 [`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py) 与 [`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py) 的导入证明，不再使用 package 级 re-export 作为通过证据。
验证：
- `rg -n "S2 导入矩阵补充|canonical import path|ModuleNotFoundError|nn_to_kernel|buffer_results_to_out_params" spec/pass/registry.md spec/pass/lowering/buffer_results_to_out_params.md spec/pass/lowering/nn_lowering/spec.md`
  - 结果：命中新增导入边界、旧模块失败边界与 pytest/expectation 分工文案。
- `rg -n "[[:blank:]]$" spec/pass/registry.md spec/pass/lowering/buffer_results_to_out_params.md spec/pass/lowering/nn_lowering/spec.md agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md`
  - 结果：无命中。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 diff --check -- spec/pass/registry.md spec/pass/lowering/buffer_results_to_out_params.md spec/pass/lowering/nn_lowering/spec.md agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md`
  - 结果：通过。
Diff 反推自测：
- 本轮实际 diff 只落在 `spec/pass/registry.md`、`spec/pass/lowering/buffer_results_to_out_params.md`、`spec/pass/lowering/nn_lowering/spec.md` 与当前任务记录，因此反推自测只做文本核对、空白检查与 `git diff --check`。
- 计划书要求的 `pytest -q test/pass/test_buffer_results_to_out_params.py test/pass/nn_lowering/public_name.py` 属于下游 build 需要兑现的 diff 反推测试；本轮未运行，因为当前角色只改 spec/记录、不改实现或 pytest。
合同验收（如适用）：
- `expectation/pass/buffer_results_to_out_params/**` 仍只作合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 当作当前 diff 的对应测试替代。
自检：
- 已读完整 `S2` 阶段、前序记录、相关 spec/test/实现与全局验收设计；本轮只改 `spec` 与任务记录，未越权改实现、测试或仓库中的 `expectation`。
- surviving public path、旧模块失败边界、`pytest` 与 `expectation` 的分工都已写成可机械判断的文字，没有把 package 级 re-export 混成 canonical 入口。
- `buffer_results_to_out_params` 与 `nn_lowering` 两份 spec 都补了最小导入示例，build 可以直接按文档改写 `importlib` / `from ... import ...` 断言。
- 当前可改进点：`spec/pass/pass_manager.md` 仍保留 `S1` 阶段说明，但它没有承载这两个 compat shim 的成功入口，因此本轮仅在 registry 与两份 pass spec 收口，避免扩大改动面。
结论：
- `T-20260423-e1e94e87` 的 spec 收口已完成；当前 worktree 已把 surviving 导入与旧 compat 模块失败边界写清。
- 下一步应回到 `build`：删除两个 compat shim、更新相关 pytest 的导入断言，并按计划书运行 `test/pass/test_buffer_results_to_out_params.py` 与 `test/pass/nn_lowering/public_name.py` 的 Diff 反推自测；`expectation` 继续单列处理。

时间：2026-04-24 01:21 +0800
经办人：jcc你莫辜负
任务：T-20260423-e1e94e87（build）
任务目标：按最新 `S2` spec 删除 `buffer_results_to_out_params / nn_to_kernel` compat shim，更新导入断言与受影响的消费者矩阵测试，并完成 Diff 反推自测。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:6) 当前任务行，确认当前仍在 [`wt-20260423-pass-infra-s2`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2) 承接 `build`。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md:349) 的 `S2` 正文、全局完成态 / 验收设计与 `expectation` 单列口径。
- 已重读前序记录 [`20260423-pass-infra-s1.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md) 与当前 `S2` spec 记录，确认 canonical import、旧模块失败边界和 package 级 re-export 只作迁移辅助的口径。
- 已读当前实现与 pytest 入口：[`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/buffer_results_to_out_params.py)、[`kernel_gen/passes/lowering/nn_to_kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/nn_to_kernel.py)、[`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py)、[`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/test_lowering_nn_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py)。
最小功能闭环：
- 删除 `kernel_gen.passes.lowering.buffer_results_to_out_params` 与 `kernel_gen.passes.lowering.nn_to_kernel` 两个 compat shim，让旧模块导入稳定失败。
- 保留 `kernel_gen.passes.buffer_results_to_out_params` 与 `kernel_gen.passes.lowering.nn_lowering` 的 canonical import；`kernel_gen.passes` / `kernel_gen.passes.lowering` package 级 re-export 只作迁移辅助，不作为验收替代。
- 把受影响的 pytest 一并收口到“canonical import 成功 + 旧模块失败”，并同步移除 registry / lowering 行为测试里的旧 shim 残留。
- `expectation` 继续单列，只记录合同资产状态，不扩面修改。
改动：
- 更新 [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py)，移除 `LowerNnToKernelPass` 与 lowering compat shim 的文档说明 / 导入，保留 `BufferResultsToOutParamsPass` 的 package 级迁移辅助导出。
- 删除 [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/buffer_results_to_out_params.py) 与 [`kernel_gen/passes/lowering/nn_to_kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/nn_to_kernel.py)，让两个旧 compat 模块退出现场。
- 更新 [`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py)，把导入证明改成“canonical module / package export 可用 + `kernel_gen.passes.lowering.buffer_results_to_out_params` 稳定失败”。
- 更新 [`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py)，改为直接从 canonical path `kernel_gen.passes.lowering.nn_lowering` 导入，并断言 `kernel_gen.passes.lowering.nn_to_kernel` 与 `LowerNnToKernel*` 不再暴露。
- 更新 [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py)，删除对 `nn_to_kernel` compat shim 的顶层 import 与对应 compat 行为用例，避免 shim 退场后文件本身失效。
- 更新 [`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py)，把两个旧 shim 从 surviving import matrix 移出，并补进旧路径失败边界。
- 当前 worktree 里 [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/lowering/buffer_results_to_out_params.md)、[`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/lowering/nn_lowering/spec.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/registry.md) 是前序 `spec` 改动，本轮 `build` 未继续改写它们。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py`
  - 结果：`93 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 diff --check`
  - 结果：通过
- `rg -n "lowering\\.buffer_results_to_out_params|lowering\\.nn_to_kernel|LowerNnToKernelPass|LowerNnToKernelError" wt-20260423-pass-infra-s2/kernel_gen wt-20260423-pass-infra-s2/test`
  - 结果：仅剩 `ModuleNotFoundError` 失败断言与旧路径失败矩阵，不再有实现侧存活导入。
Diff 反推自测：
- 本轮实际 diff 落在 [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py)、删除的两个 compat shim，以及 [`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py)、[`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/test_lowering_nn_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py)。
- 反推依据：compat shim 退场同时影响 out-param / nn_lowering 的公开导入边界、registry 的 surviving matrix，以及 `test_lowering_nn_lowering.py` 顶层导入；因此本轮直接跑上述 4 份 pytest 资产，不把 `expectation` 算入 diff 自测。
合同验收（单列，不计入 Diff 反推自测）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2:/home/lfr/kernelcode_generate python3 -m expectation.pass.buffer_results_to_out_params`
  - 结果：失败，`expectation/pass/buffer_results_to_out_params/reject_cases.py` 仍 `import kernel_gen.passes.lowering.buffer_results_to_out_params`，触发 `ModuleNotFoundError`。
- 按当前角色规则，本轮不修改仓库中的 `expectation`；该失败只作为合同资产状态记录，不回写到实现里兜底。
阻塞：
- `expectation.pass.buffer_results_to_out_params` 的合同资产还依赖已退场的 `kernel_gen.passes.lowering.buffer_results_to_out_params`。
- 我已用脚本同步管理员 `神秘人` 与架构师 `守护最好的爱莉希雅`；管理员最新口径是“先不要改 expectation，blocker 保持在当前任务记录里，停在当前实现态等待架构师后续口径”。
自检：
- 任务类型一致：本轮只做 `build`，只改实现 / 测试，没有回改 `spec`、计划书或 `expectation`。
- 接口与兼容边界：旧 shim 退场后，canonical import、package 级迁移辅助和旧模块失败边界已经在实现与 pytest 两侧对齐，没有留下实现侧继续导入旧模块的残留。
- 测试有效性：不仅收口了管理员点名的两份 pytest，也同步处理了实际受影响的 registry / nn_lowering 行为测试，避免删 shim 后留下顶层 import 失效或迁移矩阵失真。
- 可维护性：`test_lowering_nn_lowering.py` 不再依赖待退场 compat shim；`test_pass_registry.py` 的 surviving matrix 与 S2 spec 不再互相矛盾。
- 当前未继续处理的点只有单列 `expectation` 合同资产；按管理员最新口径，这部分等待架构师确认，不由本轮 `build` 擅自扩面。
结论：
- 实现与 Diff 反推自测已完成，compat shim 退场后的代码 / pytest 口径已收口。
- 当前阻塞只剩 `expectation.pass.buffer_results_to_out_params` 的合同资产仍引用旧模块；按管理员最新要求，本任务先停在当前实现态，等待架构师明确后续口径。
- 本轮不执行 `-next`，也不自行扩到 `expectation`。

时间：2026-04-24 01:19 +0800
经办人：守护最好的爱莉希雅
任务：T-20260423-e1e94e87
架构补充口径：
- `expectation/pass/buffer_results_to_out_params/reject_cases.py` 当前带 `[immutable-file]`，且仍直接 `import kernel_gen.passes.lowering.buffer_results_to_out_params`；这与 `S2` 已写死的 `禁止修改面：expectation/pass/buffer_results_to_out_params/**` 和 “compat shim 旧路径稳定失败” 同时成立时，会让 `python3 -m expectation.pass.buffer_results_to_out_params` 变成 expectation 资产自身的独立阻断，而不是当前 build diff 的实现阻断。
- 因此，这个 expectation 失败不属于 `T-20260423-e1e94e87` 当前 build diff 边界；当前任务继续只收 `spec/实现/pytest` 的 compat shim 退场，不要求执行人修改 expectation。
- 后续口径：`expectation.pass.buffer_results_to_out_params` 需要拆为独立 expectation 侧 spec/修复链处理，由架构侧单独改写到可执行链；在该独立链建立前，`T-20260423-e1e94e87` 不再把这组 immutable expectation 作为 build 完成阻断。
- review / merge 可据此只检查 `spec/实现/pytest` 与 Diff 反推测试是否闭环；expectation 继续作为单列合同资产，由后续独立链处理。

时间：2026-04-24 01:23 +0800
经办人：jcc你莫辜负
任务：T-20260423-e1e94e87（build）
状态补记：
- 已按最新架构 / 管理口径收口记录：`expectation.pass.buffer_results_to_out_params/reject_cases.py` 的旧 import 问题不再作为当前 `S2 build` 完成阻断。
- 当前 `build` 的完成边界保持为：`spec/实现/pytest` 的 compat shim 退场、真实自检完整、Diff 反推自测完整；`expectation` 只继续单列记录，等待后续独立链处理。
- 本轮后续动作恢复为正常流转：据此继续执行 `-next -auto -type review`，把当前 `build` 输出回流 `review`。

---
时间：2026-04-24 01:25 +0800
经办人：提莫炖蘑菇
任务：T-20260423-e1e94e87（review）
任务目标：复核 `buffer_results_to_out_params / nn_to_kernel` compat shim 退场后的导入边界、旧路径失败断言、真实自检与 Diff 反推自测是否按 `S2` 当前边界闭合；`expectation.pass.buffer_results_to_out_params` 的 immutable import 问题只单列记录，不作为本任务 build 阻断。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:7) 当前任务行，确认任务处于 `review`，worktree 为 [`wt-20260423-pass-infra-s2`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2)。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S2` 正文、全局完成态 / 验收设计与 `expectation` 单列口径。
- 已重读当前任务记录中 `spec` / `build` 条目，特别是 compat shim 退场、`expectation` 独立链口径与 build 的 Diff 反推自测摘要。
- 已现场核对 [`kernel_gen/passes/lowering/__init__.py`](../../../../../../../kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](../../../../../../../kernel_gen/passes/lowering/buffer_results_to_out_params.py)、[`kernel_gen/passes/lowering/nn_to_kernel.py`](../../../../../../../kernel_gen/passes/lowering/nn_to_kernel.py)、[`test/pass/test_buffer_results_to_out_params.py`](../../../../../../../test/pass/test_buffer_results_to_out_params.py)、[`test/pass/nn_lowering/public_name.py`](../../../../../../../test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py) 与相关 spec。
真实审查：
- 当前实际 diff 为 10 个文件：`kernel_gen/passes/lowering/__init__.py`、删除的 `kernel_gen/passes/lowering/buffer_results_to_out_params.py` / `kernel_gen/passes/lowering/nn_to_kernel.py`、3 份 `spec`、以及 4 份 `pytest`。
- 现场核对结果：
  - 旧 compat shim 文件 [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](../../../../../../../kernel_gen/passes/lowering/buffer_results_to_out_params.py) 与 [`kernel_gen/passes/lowering/nn_to_kernel.py`](../../../../../../../kernel_gen/passes/lowering/nn_to_kernel.py) 已退出当前 diff。
  - [`test/pass/test_buffer_results_to_out_params.py`](../../../../../../../test/pass/test_buffer_results_to_out_params.py)、[`test/pass/nn_lowering/public_name.py`](../../../../../../../test/pass/nn_lowering/public_name.py)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py) 已把旧路径稳定失败写进断言。
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py) 也已清掉对 `nn_to_kernel` compat shim 的直接依赖。
- 但 [`kernel_gen/passes/lowering/__init__.py`](../../../../../../../kernel_gen/passes/lowering/__init__.py) 仍把
  - `from kernel_gen.passes.lowering import BufferResultsToOutParamsPass`
  - `pass_obj = BufferResultsToOutParamsPass()`
  写成常规使用示例。
- 这会把 package 级迁移辅助路径重新写成主入口，而 [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../../../../../spec/pass/lowering/buffer_results_to_out_params.md) 已把 canonical import 固定为 `kernel_gen.passes.buffer_results_to_out_params`，并把 package 级 re-export 降为迁移辅助，不应再作为当前阶段的主示例。
Diff 反推审查：
- 按当前 diff 反推执行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py -ra`
    - 结果：`93 passed, 1 warning`
  - `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py`
    - 结果：通过
  - `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 diff --check`
    - 结果：通过
  - `rg -n "lowering\\.buffer_results_to_out_params|lowering\\.nn_to_kernel|LowerNnToKernelPass|LowerNnToKernelError" /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test`
    - 结果：只剩旧路径失败断言与不再暴露的名称检查，没有实现侧存活导入。
合同验收：
- `expectation.pass.buffer_results_to_out_params` 的 immutable import 问题已由架构确认转独立链处理。
- 本轮未把 `expectation` 计入 Diff 反推审查，只单列阅读和口径确认。
可改进点：
- 问题 1：[`kernel_gen/passes/lowering/__init__.py`](../../../../../../../kernel_gen/passes/lowering/__init__.py)
  - 现象：BufferResultsToOutParams 的使用示例仍把 `from kernel_gen.passes.lowering import BufferResultsToOutParamsPass` 写成常规调用方式。
  - 风险：`S2` 已把 canonical import 固定为 `kernel_gen.passes.buffer_results_to_out_params`，package 级 re-export 只是迁移辅助；继续把辅助路径写成常规示例，会弱化当前阶段的导入边界证据。
  - 建议：把示例改成 canonical import，或至少显式标注该 package 级路径只作迁移辅助，不属于当前阶段主入口。
自检：
- 已先读计划书 `S2`、全局完成态 / 验收设计、最新 build 记录与任务记录，再按当前 diff 做现场核对。
- 审查范围严格限定在管理员点名的实现 / pytest / 导入边界文件，没有把 `expectation` 混进 diff 反推测试。
- 当前仍能明确指出当前切片内可直接收口的导入示例问题，因此本轮不给通过。
结论：
- 结论：`需修改`
- 下一步：回到 `build`，先收掉 [`kernel_gen/passes/lowering/__init__.py`](../../../../../../../kernel_gen/passes/lowering/__init__.py) 中 BufferResultsToOutParams 的主示例口径，再继续 `review`。

---
时间：2026-04-24 02:35 CST
经办人：金铲铲大作战
任务：T-20260423-e1e94e87（build）
任务目标：按最新退回口径收掉 [`kernel_gen/passes/lowering/__init__.py`](../../../../../../../kernel_gen/passes/lowering/__init__.py) 中全部 `BufferResultsToOutParams` 残留，并同步公开 pytest 到 canonical 入口。
执行前阅读记录：
- 已重读 [`TODO.md`](../../../../../../../TODO.md) 当前任务行，确认 `T-20260423-e1e94e87` 当前仍在 running list，任务目标已经收紧为：`lowering/__init__.py` 中不得再出现 `BufferResultsToOutParams`，包括说明、示例、关联文件、import、`__all__`、兼容导出。
- 已重读计划书 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S2` 正文、全局完成态 / 验收设计和本记录前序 build / review 条目。
- 已现场核对 residual diff 与受影响 pytest：[`test/pass/test_buffer_results_to_out_params.py`](../../../../../../../test/pass/test_buffer_results_to_out_params.py)、[`test/pass/test_pass_manager.py`](../../../../../../../test/pass/test_pass_manager.py)、[`test/pass/test_pipeline_default_lowering.py`](../../../../../../../test/pass/test_pipeline_default_lowering.py)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py) 仍存在 package 级 `BufferResultsToOutParamsPass` 断言。
最小功能闭环：
- [`kernel_gen/passes/lowering/__init__.py`](../../../../../../../kernel_gen/passes/lowering/__init__.py) 不再出现 `BufferResultsToOutParams` / `buffer_results_to_out_params` 文本。
- canonical 入口继续只保留 [`kernel_gen/passes/buffer_results_to_out_params.py`](../../../../../../../kernel_gen/passes/buffer_results_to_out_params.py)。
- 受影响 pytest 统一回到 canonical import，并把 `kernel_gen.passes.lowering` 的 surviving matrix 收紧成“不再导出该符号”。
改动：
- 更新 [`kernel_gen/passes/lowering/__init__.py`](../../../../../../../kernel_gen/passes/lowering/__init__.py)：
  - 删除 `BufferResultsToOutParams` 的功能说明、使用示例、关联 spec/test/实现链接。
  - 删除 `from ..buffer_results_to_out_params import ...` 与 `__all__` 中对应条目。
- 更新 [`test/pass/test_buffer_results_to_out_params.py`](../../../../../../../test/pass/test_buffer_results_to_out_params.py)：
  - `test_public_import_path_uses_canonical_module_and_rejects_legacy_lowering_shim` 现在断言 `kernel_gen.passes.lowering` 不再导出 `BufferResultsToOutParamsPass/Error`。
- 更新 [`test/pass/test_pass_manager.py`](../../../../../../../test/pass/test_pass_manager.py)：
  - 全量改回 canonical `kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass`。
  - surviving import matrix 现在明确断言 `kernel_gen.passes.lowering` 不再包含 `BufferResultsToOutParamsPass`。
- 更新 [`test/pass/test_pipeline_default_lowering.py`](../../../../../../../test/pass/test_pipeline_default_lowering.py)：
  - 默认 pipeline 顺序测试改用 canonical `BufferResultsToOutParamsPass`。
- 更新 [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)：
  - surviving public path matrix 删除 `kernel_gen.passes.lowering.BufferResultsToOutParamsPass`，并补 `not hasattr(...)` 断言。
验证：
- 执行目录：`/home/lfr/kernelcode_generate`
- `rg -n "BufferResultsToOutParams|buffer_results_to_out_params" /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py` -> 无命中
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py -ra` -> `121 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 diff --check` -> 通过
Diff 反推自测：
- 本轮按 residual diff 反推的测试只包含受影响的 pass / pipeline / registry / public-name pytest。
- `expectation.pass.buffer_results_to_out_params` 继续只作合同验收资产单列，不计入 diff 反推测试。
自检：
- 这轮没有扩大 `S2` 边界，没有恢复 compat shim，也没有修改 immutable expectation 资产。
- API / 边界已经收紧到用户要求的最终形态：`kernel_gen.passes.lowering` 不再承载 `BufferResultsToOutParams` 的任何公开痕迹。
- 当前一线可改进点已收掉；现场 residual diff 与任务要求一致，可继续回流 `review`。
结论：
- 当前 build 已完成，`lowering/__init__.py` 中 `BufferResultsToOutParams` 全量退场，受影响 pytest 已同步到 canonical 入口。
- 下一步执行 `-next -auto -type review` 并回报管理员。

时间：2026-04-24 02:49 +0800
经办人：不要啊教练
任务：T-20260423-e1e94e87（review）
任务目标：复核 `buffer_results_to_out_params / nn_to_kernel` compat shim 退场后的导入边界、旧路径失败断言、真实自检与 Diff 反推审查是否按 `S2` 当前边界闭合；`expectation` 只单列，不替代对应测试。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前 running 任务行，确认我名下当前 review 为 `T-20260423-e1e94e87`，worktree 为 [`wt-20260423-pass-infra-s2`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2)。
- 已读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S2` 正文、全局完成态 / 验收设计、消费者迁移矩阵与 `expectation` 单列口径。
- 已读本记录中的前序 `spec` / `build` / `review` 条目，确认当前阶段目标是 compat shim 退场、canonical import 收口、旧路径失败边界写实；`expectation.pass.buffer_results_to_out_params` 已由架构确认转独立链，不作为本任务阻断。
真实审查：
- 当前 residual diff 覆盖 [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py)、删除的 compat shim、3 份 `spec` 和 6 份受影响 `pytest`。
- 现场核对确认：
  - `kernel_gen.passes.lowering.buffer_results_to_out_params` 与 `kernel_gen.passes.lowering.nn_to_kernel` 已退场；
  - `test/pass/test_buffer_results_to_out_params.py` 与 `test/pass/nn_lowering/public_name.py` 已把 canonical submodule 成功、旧模块失败写成显式断言；
  - `test/pass/nn_lowering/test_lowering_nn_lowering.py` 已清掉对 `nn_to_kernel` compat shim 的直接依赖；
  - `lowering/__init__.py` 中 `BufferResultsToOutParams*` 残留已收掉。
- 但当前切片仍有一条可直接收口的问题：[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py) 的 surviving import matrix 只验证了 `kernel_gen.passes.lowering` 不再导出 `BufferResultsToOutParamsPass`，却没有在同一条 consumer-matrix 证据里正向锁定 canonical `kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass`。
问题清单：
- `P2` 文件：[`test/pass/test_pass_manager.py:266`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py#L266)
  - 现象：`test_pass_manager_surviving_import_matrix()` 现在只有 `assert not hasattr(lowering_module, "BufferResultsToOutParamsPass")`，没有与 [`spec/pass/registry.md:98`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/registry.md#L98) 到 `#L107` 一致地在同一函数里正向锁定 canonical `kernel_gen.passes.buffer_results_to_out_params`。
  - 影响：pass_manager / pipeline caller 侧的 consumer matrix 证据链只锁住了“旧入口退出”，没有在同一条 matrix 里把“新入口仍可用”写实；当前 canonical 路径主要依赖文件顶层 import 和 [`test/pass/test_buffer_results_to_out_params.py:48`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py#L48) 到 `#L67` 的专项测试，证据分散。
  - 建议：在 `test_pass_manager_surviving_import_matrix()` 中追加对 `kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass` 的直接对象身份断言，让 pass_manager 侧 matrix 自身闭合。
可改进点：
- 当前 pass_manager matrix 已经覆盖了 negative side；建议补上 canonical positive side 后，再把 `S2` 的 consumer matrix 视为完整闭合。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py -ra`
  - 结果：`121 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 diff --check`
  - 结果：通过
- 审查结论：实现和受影响 pytest 没有回退，但 `pass_manager` 侧 consumer matrix 证据还可以再补一条 canonical 正向断言。
合同验收（单列，不计入 Diff 反推审查）：
- 本轮未执行 `expectation.pass.buffer_results_to_out_params`。按当前架构口径，这组 immutable 资产已转独立链处理，不作为当前 review 的 diff 对应测试。
自检：
- 已按要求先读计划书、前序记录和最新 build 记录，再按实际 diff 做真实审查与 Diff 反推审查。
- 当前仍存在可直接执行的一线改进项，因此本轮不给通过。
结论：需修改。compat shim 退场主线已完成，但 `test_pass_manager.py` 的 surviving import matrix 还需补上 canonical `kernel_gen.passes.buffer_results_to_out_params` 的正向断言，再回流 review。

---
时间：2026-04-24 03:22 CST
经办人：金铲铲大作战
任务：T-20260423-e1e94e87（build）
任务目标：补齐 `pass_manager` 侧 consumer matrix 对 canonical `buffer_results_to_out_params` 路径的正向对象身份断言，再回流 `review`。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前 running 任务行，确认 `T-20260423-e1e94e87` 仍在 `build`，目标已收紧为补齐 `pass_manager` consumer matrix 的 canonical 正向对象身份断言。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S2` 正文、全局完成态 / 验收设计，以及本记录上一条 `review` 退回意见。
- 已现场核对 residual diff，确认本轮只需补 [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py) 的 surviving import matrix 证据，不扩大 `S2` 边界。
最小功能闭环：
- [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py) 在同一条 `surviving import matrix` 中同时锁住：
  - canonical `kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass` 对象身份；
  - `kernel_gen.passes.lowering` 不再导出 `BufferResultsToOutParamsPass`。
- 保持 [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py) 不再出现 `BufferResultsToOutParams`。
改动：
- 更新 [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py)：
  - 在 `test_pass_manager_surviving_import_matrix()` 中新增 `kernel_gen.passes.buffer_results_to_out_params` 的显式导入；
  - 新增 `BufferResultsToOutParamsPass is buffer_results_module.BufferResultsToOutParamsPass` 对象身份断言；
  - 保留 `assert not hasattr(lowering_module, "BufferResultsToOutParamsPass")`，使 `pass_manager` 侧 consumer matrix 在同一函数内闭合。
验证：
- 执行目录：`/home/lfr/kernelcode_generate`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py -ra` -> `121 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 diff --check` -> 通过
Diff 反推自测：
- 本轮按 residual diff 反推的测试仍限定为受影响的 pass / pipeline / registry / public-name pytest。
- `expectation.pass.buffer_results_to_out_params` 继续只作合同验收资产单列，不计入 diff 反推测试。
自检：
- 本轮没有恢复 compat shim，也没有扩大 `S2` 残余 diff 范围。
- `pass_manager` 侧 positive / negative consumer matrix 现在在同一条证据链中闭合，和上一条 `review` 退回意见对齐。
- 当前一线可改进点已收掉；若无新的审查意见，可继续回流 `review`。
结论：
- 当前 build 已完成，`pass_manager` 侧 canonical `buffer_results_to_out_params` 正向对象身份断言已补齐。
- 下一步执行 `-next -auto -type review` 并回报管理员。

---
时间：2026-04-24 03:25 +0800
经办人：提莫炖蘑菇
任务：T-20260423-e1e94e87（review）
任务目标：复核 `buffer_results_to_out_params / nn_to_kernel` compat shim 退场后的导入边界、旧路径失败断言、真实自检与 Diff 反推审查是否按 `S2` 当前边界闭合；`expectation.pass.buffer_results_to_out_params` 的 immutable import 问题只单列说明，不作为本任务阻断。
执行前阅读记录：
- 已重读 [`TODO.md`](../../../../../../../TODO.md) 当前任务行，确认 `T-20260423-e1e94e87` 当前处于 `review`。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S2` 正文、全局完成态 / 验收设计与 `expectation` 单列口径。
- 已重读当前任务记录中的前序 `spec / build / review` 条目，特别是上一轮对 `test_pass_manager.py` surviving import matrix 的退回意见，以及最新 build 对 canonical `buffer_results_to_out_params` 对象身份断言的补齐。
真实审查：
- 当前 residual diff 仍集中在 `compat shim` 退场相关文件：
  - [`kernel_gen/passes/lowering/__init__.py`](../../../../../../../kernel_gen/passes/lowering/__init__.py)
  - 删除的 [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](../../../../../../../kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - 删除的 [`kernel_gen/passes/lowering/nn_to_kernel.py`](../../../../../../../kernel_gen/passes/lowering/nn_to_kernel.py)
  - 相关 `spec / pytest` 收口文件
- 现场核对确认：
  - `kernel_gen.passes.lowering.buffer_results_to_out_params` 与 `kernel_gen.passes.lowering.nn_to_kernel` 已退场；
  - [`test/pass/test_buffer_results_to_out_params.py`](../../../../../../../test/pass/test_buffer_results_to_out_params.py) 仍显式锁定 canonical `kernel_gen.passes.buffer_results_to_out_params` 成功与 lowering 旧模块失败；
  - [`test/pass/nn_lowering/public_name.py`](../../../../../../../test/pass/nn_lowering/public_name.py) 仍显式锁定 canonical `kernel_gen.passes.lowering.nn_lowering` 成功与 `kernel_gen.passes.lowering.nn_to_kernel` 失败；
  - [`test/pass/test_pass_manager.py`](../../../../../../../test/pass/test_pass_manager.py) 的 surviving import matrix 现在已在同一函数里同时锁住：
    - canonical `kernel_gen.passes.buffer_results_to_out_params.BufferResultsToOutParamsPass` 对象身份
    - `kernel_gen.passes.lowering` 不再导出 `BufferResultsToOutParamsPass`
- 本轮没有再发现当前切片内可直接执行、且未收口的导入边界问题。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py -ra`
  - 结果：`121 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 diff --check`
  - 结果：通过
合同验收（单列，不计入 Diff 反推审查）：
- 本轮未执行 `expectation.pass.buffer_results_to_out_params`。按当前架构口径，这组 immutable 资产已转独立链处理，不作为当前 review 的 diff 对应测试。
自检：
- 已按要求先读计划书、前序记录和最新 build 记录，再按实际 diff 做真实审查与 Diff 反推审查。
- 当前 residual diff 的 canonical / legacy import matrix 证据链已经闭合，未再发现当前切片内可直接执行的一线改进项。
- 本轮没有扩大到 `expectation`、`.gitignore` 或其他不在 `S2` 边界内的内容。
可改进点：
- 当前切片内未发现新的可直接执行改进点；`expectation.pass.buffer_results_to_out_params` 的 immutable import 问题继续留在独立链处理，不应回灌到本轮 compat shim 退场任务。
结论：
- 通过。当前 `buffer_results_to_out_params / nn_to_kernel` compat shim 退场后的导入边界、旧路径失败断言与 `pass_manager` consumer matrix 已按 `S2` 当前边界闭合。

---
时间：2026-04-24 20:02 +0800
经办人：李白
任务：T-20260423-e1e94e87（merge）
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认 `T-20260423-e1e94e87` 处于 `merge`，对应 `worktree` 为 [`wt-20260423-pass-infra-s2`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2)。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S2` 正文、消费者迁移矩阵、全局完成态 / 验收设计。
- 已重读本记录中的 `spec`、`build`、`review` 条目，确认当前通过口径是：compat shim 退场、canonical / legacy import matrix 闭合，`expectation.pass.buffer_results_to_out_params` 继续只作独立合同资产单列。
合并前同步：
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 fetch origin` 后，当前分支基线从 `5d48435` 前移到 `origin/main@8e73d6a`。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 rebase --autostash origin/main` 成功，但 autostash 回放把本任务的 residual diff 覆盖回了旧主线口径。
- 现场冲突处理不是机械取任一侧，而是按“保留 `S2` 已审 residual diff + 吸收当前主线 surviving path”收口：
  - 保留 `buffer_results_to_out_params / nn_to_kernel` compat shim 退场、spec 与 pytest 的 canonical / legacy import matrix 证据；
  - 同步吸收 `S3` 已落主线的 `kernel_gen.passes.dma_memory_hierarchy` / `kernel_gen.passes.memory_pool` surviving public path；
  - 同步吸收 `launch-kernel-cost-func` 当前主线只接受 `compute|memory` 的 registry 口径，避免把后续已过链路回退成旧断言。
真实收口过程：
- 保持以下 `S2` 收口文件继续进入本次 merge：
  - [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py)
  - 删除 [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - 删除 [`kernel_gen/passes/lowering/nn_to_kernel.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/nn_to_kernel.py)
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/lowering/nn_lowering/spec.md)
  - [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/spec/pass/registry.md)
  - [`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py)
  - [`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py)
  - [`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py)
  - [`test/pass/test_pipeline_default_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py)
- 其中两处是 rebase 到最新主线后补做的兼容调整：
  - `test_pass_manager.py` / `test_pass_registry.py` 中 `dma_memory_hierarchy` 与 `memory_pool` 的 surviving 路径统一改回顶层 `kernel_gen.passes.*`；
  - `test_pass_registry.py` 中 `launch-kernel-cost-func` 的 registry 断言统一回到当前公开 `compute|memory` 口径，避免把别的已完成链路回退。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py -ra`
  - 结果：`121 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_buffer_results_to_out_params.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pipeline_default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/test/pass/test_pass_registry.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2 diff --check`
  - 结果：通过
合同验收（单列，不计入 Diff 反推自测）：
- 本轮未执行 `expectation.pass.buffer_results_to_out_params`，继续遵守前序架构口径：该 immutable 资产转独立链处理，不作为当前 `S2 merge` 的对应测试。
结论：
- `T-20260423-e1e94e87` 已按最新主线完成 merge 收口，compat shim 退场后的 canonical / legacy import matrix 在当前主线 surviving path 上已闭合，可提交并执行 `-done`。
