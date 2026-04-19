时间：2026-04-20 01:21 +0800
经办人：小李飞刀
任务：T-20260419-0319997f
任务目标：收口 npu_demo Kernel 实现与 emit_c Kernel family，修正 `kernel` family 在 `target=npu_demo` 下的函数签名与 `out-first` 公开口径，并继续去掉旧 Nn 公共成功口径。
改动：补建缺失的 `wt-20260419-emitc-api-s12-kernel-emitc-build` worktree；更新 `kernel_gen/dsl/gen_kernel.py`，让默认函数签名在推断可写 memory 参数时把 `kernel.*` 的 `out` operand 也计入，同时把“前置 `arg0/arg1/...` out 参数”识别收紧为“命名前缀 + 真实写路径”共同成立，避免 `kernel.binary_elewise(kind=\"add\")` 这类普通单函数 module 把输入参数误生成为 `Memory&`；更新 `test/dsl/test_gen_kernel.py`，新增 `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first`，锁住 `kernel_binary_add_case` 在 `target=npu_demo` 下必须生成 `Memory<TLM1, double>& arg0, const Memory<TLM1, int32_t>& arg1, const Memory<TLM1, int32_t>& arg2`，并通过 `npu_demo::add<...>(arg0, arg1, arg2)` 发射。当前 `include/npu_demo/npu_demo.h` 未重新聚合 `Nn.h`，本轮未再改 include 头。
验证：`python3 -m pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo_kernel_binary_signature_out_first or emits_npu_demo_body_level_kernel'` -> `2 passed`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel && echo EXPECTATION_OK` -> `EXPECTATION_OK`；`python3 -m pytest -q test/dsl/test_emit_c.py -k 'npu_demo and kernel'` -> `1 passed, 27 deselected`；`python3 -m pytest -q test/include/api/test_kernel.py` -> `3 passed`。补充核对：`python3 -m pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo'` -> `1 failed, 23 passed`，失败点是 `test_gen_kernel_compiles_npu_demo_tiled_matmul_source`，表现为 `slice(..., {i0, 0}, {16, 16}, {1, 1})` 仍未适配 `Vector` 口径，且生成源码里有重复 `S_INT c_16/c_1` 定义；该问题落在 S11/S后续 `gen_kernel + dma` 交界，不属于本轮 S12 的最小收口面。
结论：当前 build 已完成，任务日志已写入对应任务 worktree 的记录文件；下一步创建 review 任务并通知管理员推进。

时间：2026-04-20 01:24 +0800
经办人：提莫炖蘑菇
任务：T-20260419-0319997f
任务目标：复核 npu_demo Kernel family emit_c 签名修补与旧 Nn 成功口径收口结果
改动：完成本轮审查。问题列表：1）[P1] 文件/接口：[`ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md:794)。现象：S12 计划书的验收必过命令仍是 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel`。我在 `wt-20260419-emitc-api-s12-kernel-emitc-build` 下按原文执行，直接报 `ModuleNotFoundError: No module named 'expectation'`；当前通过结论依赖的是 build 记录里的替代命令 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate ...`。风险：这会导致计划书正文验收入口与当前 task-site 现场不一致，下游按计划书原文复验时仍无法直接复现通过结论。建议：把 S12 的 expectation 验收命令同步改成当前现场可执行入口，再回 review。
验证：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel`（在 `wt-20260419-emitc-api-s12-kernel-emitc-build` 下执行）-> `ModuleNotFoundError: No module named 'expectation'`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel` -> `exit 0`；`python3 -m pytest -q test/dsl/test_emit_c.py -k 'npu_demo and kernel'` -> `1 passed, 27 deselected, 8 warnings`；`python3 -m pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo_kernel_binary_signature_out_first or emits_npu_demo_body_level_kernel'` -> `2 passed, 57 deselected, 8 warnings`；`python3 -m pytest -q test/include/api/test_kernel.py` -> `3 passed`；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build diff --check` -> 通过。
结论：需修改。当前 `Kernel family` 的签名修补和旧 `Nn` 成功口径收口本身没有发现新的阻断项，但计划书 S12 的 expectation 验收入口还不是当前 task-site 可直接执行的命令；下一步建议创建 `spec` 任务，先把 S12 验收命令收口到当前现场口径，再回 review。

时间：2026-04-20 01:26 +0800
经办人：睡觉小分队
任务：T-20260419-0319997f
任务目标：把 npu_demo_emitc_include_api 计划书中 S12 的 expectation 验收命令收口为当前 task-site 可直接执行的具体入口。
改动：更新 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md`，把总验收区、`S12` 小节以及复用 `S12` 口径的 `S15` 复核段落中的 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel` 统一改成当前现场可直接执行的具体命令 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel`，并在 `S12` 小节补充“需在当前 task worktree 下执行”的说明；同步把计划书“最后一次更改”更新为 `睡觉小分队`。
验证：`rg -n "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=\\. python3 -m expectation\\.dsl\\.emit_c\\.npu_demo\\.kernel|wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation\\.dsl\\.emit_c\\.npu_demo\\.kernel|最后一次更改" /home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md` -> 仅命中新修改人与三处具体命令，旧 `PYTHONPATH=.` 写法已消失；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel`（在 `wt-20260419-emitc-api-s12-kernel-emitc-build` 下执行）-> `exit 0`；未执行 `pytest`，原因：本轮只调整计划书文字，不改实现与测试。
结论：当前 spec 已完成，任务日志已写入对应任务 worktree 的记录文件；下一步建议进入 review，复核 S12 的 expectation 验收命令已与当前 task-site 现场一致。

时间：2026-04-20 01:27 +0800
经办人：提莫炖蘑菇
任务：T-20260419-0319997f
任务目标：复核 S12 的 npu_demo kernel expectation 验收命令已统一收口为 wt-20260419-emitc-api-s12-kernel-emitc-build 当前 task-site 可直接执行的具体入口
改动：本轮仅做审查。复核 [`ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md) 总验收区、`S12` 小节和复用 `S12` 口径的 `S15` 复核段，确认三处 `npu_demo kernel expectation` 命令都已改成当前 worktree 的具体 task-site 写法，不再是 `PYTHONPATH=.` 的旧入口。按计划书原文在 `wt-20260419-emitc-api-s12-kernel-emitc-build` 下直接执行，命令可以复现通过。
验证：`rg -n "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=\\. python3 -m expectation\\.dsl\\.emit_c\\.npu_demo\\.kernel|wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation\\.dsl\\.emit_c\\.npu_demo\\.kernel" /home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md` -> 仅命中三处具体 task-site 命令，旧 `PYTHONPATH=.` 写法已消失；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel`（在 `wt-20260419-emitc-api-s12-kernel-emitc-build` 下执行）-> `exit 0`；`python3 -m pytest -q test/dsl/test_emit_c.py -k 'npu_demo and kernel'` -> `1 passed, 27 deselected, 8 warnings`；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build diff --check` -> 通过。
结论：审查通过。S12 的 npu_demo kernel expectation 验收命令已统一收口为当前 task-site 可直接执行的具体入口，并与 worktree 现场一致，可续接 `merge`。

时间：2026-04-20 01:37 +0800
经办人：提莫炖蘑菇
任务：T-20260419-0319997f
任务目标：复核 S12 的 npu_demo kernel expectation 验收命令已统一收口为 wt-20260419-emitc-api-s12-kernel-emitc-build 当前 task-site 可直接执行的具体入口
改动：本轮复审沿用最新计划书口径再次核对总验收区、S12 与复用 S12 口径的 S15 段，确认三处 expectation 命令都已经是当前 worktree 的具体 task-site 写法；同时确认当前现场没有 `expectation/` 目录，必须通过 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate` 追加主仓 expectation 资产，这与计划书正文说明一致。
验证：`test -d /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build/expectation; echo $?` -> `1`；`rg -n "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=\\. python3 -m expectation\\.dsl\\.emit_c\\.npu_demo\\.kernel|wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation\\.dsl\\.emit_c\\.npu_demo\\.kernel" /home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_emitc_include_api_green_plan.md` -> 仅命中三处 task-site 具体命令；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel` -> `exit 0`；`python3 -m pytest -q test/dsl/test_emit_c.py -k 'npu_demo and kernel'` -> `1 passed, 27 deselected, 8 warnings`；`python3 -m pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo_kernel_binary_signature_out_first or emits_npu_demo_body_level_kernel'` -> `2 passed, 57 deselected, 8 warnings`；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build diff --check` -> 通过。
结论：复审通过。S12 的 npu_demo kernel expectation 验收命令已经稳定收口为当前 task-site 可直接执行的具体入口，且与当前 worktree 现场一致，可续接 `merge`。

时间：2026-04-20 02:30 +0800
经办人：李白
任务：T-20260419-0319997f
任务目标：合并本轮已通过复审的 kernel family out-first 签名修补与对应 `test/dsl/test_gen_kernel.py` 回归。
改动：确认当前 worktree 待合并写集仅为 [`kernel_gen/dsl/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel.py) 与 [`test/dsl/test_gen_kernel.py`](../../../../../../test/dsl/test_gen_kernel.py)；当前基线仍是旧提交 `b4a7211`，而最新 `origin/main` 已前进到 `a5a55e7`，本轮需要先把本地合并结果重放到最新主线再推送。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build status --short --branch --untracked-files=all` -> 仅命中上述两份业务文件与当前记录文件；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build diff --stat -- kernel_gen/dsl/gen_kernel.py test/dsl/test_gen_kernel.py` -> 命中 2 个业务文件，合计 56 行变更；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build rev-parse --short HEAD` -> `b4a7211`，`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build rev-parse --short origin/main` -> `a5a55e7`。
结论：开始 merge，下一步提交当前写集并重放到最新主线，然后推送、执行 `-done`、再回报管理员。
