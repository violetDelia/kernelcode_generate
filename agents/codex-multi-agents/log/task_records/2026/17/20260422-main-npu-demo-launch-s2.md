时间：2026-04-23 03:42 +0800
经办人：jcc你莫辜负
任务：T-20260422-f94ed233
任务目标：按 ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md 的 S2 推进 pattern folding 接入现有 xdsl rewrite pass，收口静态 symbol/int 常量表达，不新增 standalone cleanup pass。
执行前阅读记录：已读 `TODO.md` 中 `T-20260422-f94ed233` 任务行、计划书 `main_npu_demo_pipeline_fold_cse_green_plan.md` 的 S2 正文、S1 记录、全局完成态 / 验收设计、`xdsl.pattern_rewriter` / `xdsl.interfaces` / `xdsl.folder` folding 源码，以及 `test/dialect/test_symbol_dialect.py`、`test/pass/nn_lowering/public_name.py`、`test/pass/test_pipeline_npu_demo_lowering.py`、`test/pass/nn_lowering/test_lowering_nn_lowering.py` 相关实现与测试。
最小功能闭环：在现有 `NnLoweringPass` rewrite driver 中启用 `folding_enabled=True, ctx=ctx`，并给 `symbol` dialect 补齐静态整数二元算术 fold / 常量物化能力，使 `symbol.add/sub/mul/div/floordiv` 的静态整数表达能够在现有 xdsl driver 内收口，动态 symbol 表达保守不折叠。
改动：
- 更新 [`kernel_gen/dialect/symbol.py`](</home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2/kernel_gen/dialect/symbol.py>)，新增静态 symbol.int 整数值提取 helper、给二元算术基类接入 `HasFolderInterface`、补 `fold()` 逻辑，以及补 `symbol.const` 的 `ConstantMaterializationInterface` 物化入口，保证折叠结果回落为 `symbol.const` 而不引入 standalone cleanup pass。
- 更新 [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](</home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py>)，把 `GreedyRewritePatternApplier` 改为显式传入 `ctx=ctx` 且开启 `folding_enabled=True`。
- 更新 [`test/dialect/test_symbol_dialect.py`](</home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2/test/dialect/test_symbol_dialect.py>)，新增静态算术 fold 回归与动态 symbol 不误折叠回归，覆盖 `Folder.try_fold(...)` 与 constant materialization 行为。
- 更新 [`test/pass/nn_lowering/public_name.py`](</home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2/test/pass/nn_lowering/public_name.py>)，把 driver 断言补齐到 `ctx` / `folding_enabled=True` / `dce_enabled=False`。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2:/home/lfr/kernelcode_generate pytest -q test/dialect/test_symbol_dialect.py` -> `60 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py` -> `4 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2:/home/lfr/kernelcode_generate pytest -q test/pass/test_pipeline_npu_demo_lowering.py` -> `3 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py` -> `43 passed, 53 warnings`
- `git -C /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2 diff --check` -> 通过
Diff 反推自测：按实际 diff 反推覆盖 `symbol` dialect 的 fold/materialization 逻辑、`NnLoweringPass.apply(...)` driver 传参、pipeline 顺序与 `nn_lowering` family 回归测试；`expectation` 未作为测试替代项参与本轮自测。
合同验收（如适用）：未执行。原因：本轮为 build 阶段的 folding 接入与回归测试，`expectation` 仅作为合同验收资产单列，不替代改动文件对应测试。
自检：已读完整 S2 阶段、全局完成态 / 验收设计与 S1 记录；未越权新增 standalone cleanup pass；静态 symbol/int fold 仅对可机械判定的常量表达生效，动态 symbol 保守返回 `None`；driver 已显式携带 `ctx` 且开启 folding；测试覆盖 API、边界、动态符号误折叠、复用与测试有效性，未发现已知回退。
结论：当前 build 已完成，请按流程执行 `-next` 流转到下游 review，并回报管理员。
流转补记：已按要求执行 `-next -type review -to 提莫炖蘑菇`，任务已续入 review，管理员摘要已发送；当前 TODO 中该任务保持进行中，后续由 review 继续核对动态 symbol 不误折叠与 expectation 单列口径。

时间：2026-04-23 03:52 +0800
经办人：提莫炖蘑菇
任务：T-20260422-f94ed233
任务目标：复核 `main_npu_demo_pipeline_fold_cse_green_plan.md` 的 S2，确认动态 symbol 不误折叠、`npu_demo` lowering driver `folding_enabled` 收口符合计划，并核对 `expectation` 仅作为合同验收资产单列。
执行前阅读记录：已复读 `TODO.md` 中 `T-20260422-f94ed233` 任务行、计划书 `main_npu_demo_pipeline_fold_cse_green_plan.md` 的 S2 正文、S1 记录、全局完成态 / 验收设计，以及 build 阶段记录中关于 `kernel_gen/dialect/symbol.py`、`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`、`test/dialect/test_symbol_dialect.py`、`test/pass/nn_lowering/public_name.py` 的实际 diff 和自检摘要。
最小功能闭环：在现有 `NnLoweringPass` rewrite driver 中启用 `folding_enabled=True, ctx=ctx`，由 `symbol` dialect 直接支持静态整数二元算术 fold 与常量物化，动态 symbol 表达保守不折叠，且不新增 standalone cleanup pass。
改动：本轮 review 未新增代码改动，仅按实际 diff 复核 build 阶段的折叠接入、driver 传参与回归测试。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2:/home/lfr/kernelcode_generate python3 -m pytest -q test/dialect/test_symbol_dialect.py test/pass/nn_lowering/public_name.py test/pass/test_pipeline_npu_demo_lowering.py test/pass/nn_lowering/test_lowering_nn_lowering.py` -> `110 passed, 53 warnings`
- `git -C /home/lfr/kernelcode_generate/wt-20260422-main-npu-demo-launch-s2 diff --check` -> 通过
Diff 反推审查：按 build 阶段实际 diff 复核 `kernel_gen/dialect/symbol.py` 的 `HasFolderInterface` / `ConstantMaterializationInterface` 接入、`symbol.add/sub/mul/div/floordiv` 的静态整数 fold、动态 symbol 保守返回 `None`、`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py` 的 `folding_enabled=True` 驱动收口，以及 `test/dialect/test_symbol_dialect.py` / `test/pass/nn_lowering/public_name.py` 的回归覆盖；同时确认 `expectation` 仅作为合同验收资产单列，没有替代对应 pytest。
合同验收（如适用）：未执行。本轮为 review，且 `expectation` 只作为合同验收资产单列，不替代对应测试。
自检：已核对 S2 正文、全局完成态 / 验收设计、S1 记录与 build 阶段真实自检；动态 symbol 仅在具备静态整数值时参与折叠，`_get_concrete_symbol_int_value(...)` 对动态值返回 `None`，不会把动态 symbol 误折叠为常量；driver 明确携带 `ctx` 且启用 folding，未见额外 cleanup pass 或旧 helper 回流；测试覆盖了 static fold、dynamic no-fold、driver 参数、pipeline 回归与 `git diff --check`，未发现新的功能回退。
可改进点：`test/dialect/test_symbol_dialect.py` 当前对动态 symbol 的显式 no-fold 回归主要覆盖 `symbol.add`，后续若继续扩展 `symbol.sub/mul/div/floordiv` 的动态分支参数化断言，可进一步把“动态 symbol 不折叠”做成全家族机械门禁，但这不影响当前结论。
结论：通过。S2 的动态 symbol 风险未见误折叠，`npu_demo` lowering driver 的 `folding_enabled` 收口与计划一致，`expectation` 仍保持为合同验收资产单列，当前 review 无需回退。

## Merge 收口

- `时间`：`2026-04-23 03:58 +0800`
- `经办人`：`李白`
- `任务`：`T-20260422-f94ed233（merge）`
- `执行前阅读记录`：再次核对 `TODO.md` 中 `T-20260422-f94ed233` 的任务行、`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md` 的 S2 正文、S1 记录、全局完成态 / 验收设计，以及本轮 build / review 记录中的真实 diff、自检与 `Diff 反推审查` 结论。
- `收口过程`：在最新主线基线上复核本轮工作树差异，确认本轮仅包含 `kernel_gen/dialect/symbol.py`、`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`、`test/dialect/test_symbol_dialect.py`、`test/pass/nn_lowering/public_name.py` 的收口内容和任务记录文件；`expectation` 仍保持为合同验收资产单列，没有作为 Diff 反推测试替代项，也未额外引入 standalone cleanup pass。
- `本轮范围`：`kernel_gen/dialect/symbol.py`、`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`、`test/dialect/test_symbol_dialect.py`、`test/pass/nn_lowering/public_name.py`、`agents/codex-multi-agents/log/task_records/2026/17/20260422-main-npu-demo-launch-s2.md`
- `真实结果`：本轮收口已对齐到真实 diff 与真实 pytest / review 证据；后续如 `-done` 将任务状态切走，可据此记录最终完成态。
