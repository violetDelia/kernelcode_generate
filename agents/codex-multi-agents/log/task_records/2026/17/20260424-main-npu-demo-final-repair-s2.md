时间：2026-04-24 00:37
经办人：睡觉小分队
任务：T-20260424-2e64ba19
任务目标：按 `ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md` 的唯一修复任务，收口 `spec/dsl/gen_kernel.md` 的旧三字段 `arch.launch` 示例，并把 `spec/dsl/ast.md`、`spec/dsl/mlir_gen.md`、`spec/operation/arch.md` 与 `kernel_gen/dsl/ast/parser.py` 的 `launch_kernel[...]` 公开入口写成同一口径。
执行前阅读记录：已读 `TODO.md` 当前任务行、`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md` 的计划正文 / 当前基线 / 完成态定义 / 验收设计 / 终验与复验记录；已读 `kernel_gen/dsl/ast/parser.py` 与 `kernel_gen/operation/arch.py` 的 `launch_kernel` 现状；已复核仓库根目录 `AGENTS.md` 与 `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`。任务指定 worktree 不存在，本轮先创建 `/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2` 再推进。
最小功能闭环：4 份 spec 全部改为以下标式 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 作为公开入口；旧直调用只保留为兼容实现说明，不再作为公开合同；`spec/dsl/gen_kernel.md` 的 `missing_body` 失败示例改成四字段 `arch.launch<%b, %t, %s, %smem>`。
改动：
- 更新 `spec/dsl/ast.md`：把 `launch_kernel(...)` 的公开 DSL 入口、`ArchLaunchKernelAST` 功能说明、测试目标与 `AST-014O` 用例统一改为下标式入口；补一句说明旧直调用仅为兼容实现路径，不再属于公开合同。
- 更新 `spec/dsl/mlir_gen.md`：把 `launch_kernel[...]` 的 lowering 规则、测试目标与 `MGEN-037A` 用例统一改为下标式入口；旧直调用只保留为兼容说明。
- 更新 `spec/operation/arch.md`：把 operation 层公开入口、参数说明、示例、测试目标和 `TC-OP-ARCH-011~014` 改为 `launch_kernel[...]`；把旧直调用降为兼容实现说明，不再作为公开 API。
- 更新 `spec/dsl/gen_kernel.md`：把 `missing_body` 错误示例中的 `arch.launch<%b, %t, %s>` 改为四字段 `arch.launch<%b, %t, %s, %smem>`。
- 只读核对 `kernel_gen/dsl/ast/parser.py` 与 `kernel_gen/operation/arch.py`：两者当前都以下标式入口为主口径，旧直调用仅作兼容实现；本轮未改实现文件。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 diff --check` -> 通过。
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 status --short` -> 仅命中 `spec/dsl/ast.md`、`spec/dsl/gen_kernel.md`、`spec/dsl/mlir_gen.md`、`spec/operation/arch.md` 四个 spec 文件。
Diff 反推自测：本轮实际 diff 为 `spec/dsl/ast.md`、`spec/dsl/mlir_gen.md`、`spec/operation/arch.md`、`spec/dsl/gen_kernel.md`。按改动面执行本地 `python3` 断言脚本，逐项检查 `launch_kernel[...]` 是否成为 3 份 spec 的公开入口、`kernel_gen/dsl/ast/parser.py` 是否也以下标式写作公开入口、旧直调用是否只剩兼容说明、以及 `gen_kernel.md` 是否已清掉三字段 `arch.launch<%b, %t, %s>(@missing_body, ...)` 示例；结果通过。
合同验收（如适用）：当前 worktree 现场无法直接导入 `expectation` 包，已改为主仓只读执行相关合同资产：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.operation.arch` -> 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.mlir_gen.dialect.arch` -> 通过。
自检：已读完整计划阶段、完成态、验收设计与终验/复验结论；仅改当前任务点名的 4 个 spec 文件，未改实现、测试或 expectation；`launch_kernel[...]` 公开入口、旧直调用兼容说明、四字段 `arch.launch` 示例和与 `parser.py`/`operation/arch.py` 的对照关系都已写清；未发现本轮改动范围内的参数顺序歧义、旧三字段残留或公开入口双口径问题。
结论：本轮修复已完成，任务记录已写入当前 worktree；下一步执行 `-next -auto -type review` 并回报管理员。

---
时间：2026-04-24 15:40 +0800
经办人：提莫炖蘑菇
任务：T-20260424-2e64ba19（review）
任务目标：复核唯一修复任务是否已清掉 `gen_kernel` 旧三字段 `arch.launch` 示例，并将 `spec/dsl/ast.md`、`spec/dsl/mlir_gen.md`、`spec/operation/arch.md` 与 parser 公开入口统一到 `launch_kernel[...]`。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:7) 中 `T-20260424-2e64ba19` 当前任务行。
- 已重读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的最新修复口径、全局完成态 / 验收设计和前序记录。
- 已重读当前 worktree 任务记录，以及 [`spec/dsl/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel.md)、[`spec/dsl/ast.md`](../../../../../../../spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)、[`spec/operation/arch.md`](../../../../../../../spec/operation/arch.md)、[`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py) 的现场内容。
真实审查：
- 当前 diff 只落在 4 个 spec 文件：[spec/dsl/ast.md](../../../../../../../spec/dsl/ast.md)、[spec/dsl/gen_kernel.md](../../../../../../../spec/dsl/gen_kernel.md)、[spec/dsl/mlir_gen.md](../../../../../../../spec/dsl/mlir_gen.md)、[spec/operation/arch.md](../../../../../../../spec/operation/arch.md)。
- 我逐项核对后确认：
  - [`spec/dsl/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel.md) 中旧三字段 `arch.launch<%b, %t, %s>(@missing_body, ...)` 示例已经清掉，现场改成了四字段 `arch.launch<%b, %t, %s, %smem>(@missing_body, ...)`。
  - [`spec/dsl/ast.md`](../../../../../../../spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)、[`spec/operation/arch.md`](../../../../../../../spec/operation/arch.md) 的公开入口都已改成 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`。
- 但 [`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py) 的说明文本还没有完全收齐：
  - [`kernel_gen/dsl/ast/parser.py:1487`](../../../../../../../kernel_gen/dsl/ast/parser.py:1487) 仍写着“解析 `launch_kernel[...]` / `launch_kernel(...)` 启动描述”，会把两种形态并列显示成当前入口说明。
  - [`kernel_gen/dsl/ast/parser.py:1622`](../../../../../../../kernel_gen/dsl/ast/parser.py:1622) 仍写着“将 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 解析为 `ArchLaunchKernelAST`”，没有明确标成兼容路径说明。
- 这两处都不是实现错误，但它们会让“spec 已把公开入口收成 `launch_kernel[...]`，parser 只保留旧直调用兼容”的口径重新出现双写法。
Diff 反推审查：
- 按当前实际 diff，我执行了本地检查脚本与格式检查：
  - `python3 - <<'PY' ...` 检查 `spec/dsl/gen_kernel.md` 是否已去掉旧三字段 `@missing_body` 示例、4 份 spec 是否都写成 `launch_kernel[...]`、以及 `parser.py` 是否仍保留旧直调用说明。
  - 输出结果：
    - `gen_kernel_old_three_field_missing_body_absent=True`
    - `gen_kernel_new_four_field_missing_body_present=True`
    - `spec/dsl/ast.md_public_subscript_present=True`
    - `spec/dsl/mlir_gen.md_public_subscript_present=True`
    - `spec/operation/arch.md_public_subscript_present=True`
    - `parser_subscript_doc_present=True`
    - `parser_old_direct_call_doc_present=True`
  - `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 diff --check` -> 通过
- 这组结果说明：当前 diff 对应的 4 份 spec 已收齐，但 parser 现场说明仍保留旧直调用说明文本。
合同验收：
- `expectation` 只作为合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 计入 Diff 反推审查。
可改进点：
- 问题 1：[`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py:1487)、[`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py:1622)
  - 现象：parser 的函数说明仍把 `launch_kernel(...)` 与 `launch_kernel[...]` 并列描述，且 `_parse_dma_call` 的 helper 说明仍直接写旧直调用形态。
  - 风险：这会把“旧直调用只作兼容实现”重新写回当前入口说明，和本轮 spec 已统一的公开口径不一致。
  - 建议：把 parser 里这两处说明改成“公开入口是 `launch_kernel[...]`，旧直调用只作兼容路径”。
自检：
- 已先读计划书最新修复口径、前序记录与 build 记录，再按当前 diff 做现场核对，没有只复述 build 摘要。
- 已把审查范围限定在当前 diff 点名的 4 个 spec 文件及用户要求补查的 parser 说明，没有扩到无关实现与测试。
- 当前仍能明确指出当前切片内可直接处理的问题；按当前审查口径，本轮不能给通过。
结论：
- 结论：`需修改`
- 下一步：退回 `build`。先把 [`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py) 中两处旧直调用说明改成兼容路径表述，再回到 `review`。

---
时间：2026-04-24 00:44 +0800
经办人：jcc你莫辜负
任务：T-20260424-2e64ba19
任务目标：按最新 review 退回口径补齐 `kernel_gen/dsl/ast/parser.py` 的说明文本，把 `launch_kernel[...]` 明确为公开入口，旧直调用只保留为兼容路径说明。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:8) 当前任务行，确认本轮类型为 `build`，worktree 为 `wt-20260424-main-npu-demo-final-repair-s2`。
- 已读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的计划正文、全局完成态 / 验收设计与终验修复口径。
- 已读当前任务记录中的前序 build / review 条目，并现场核对 [`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py)、[`spec/dsl/ast.md`](../../../../../../../spec/dsl/ast.md)、[`spec/dsl/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel.md)、[`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)、[`spec/operation/arch.md`](../../../../../../../spec/operation/arch.md)。
最小功能闭环：当前 diff 中 4 份 spec 已把公开口径收成 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`；本轮只补 parser 说明文本，使实现侧说明也明确“公开入口是下标式，旧直调用只作兼容路径”，不扩大到其他实现或 expectation。
改动：
- 更新 [`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py)：
  - 将 `_parse_launch_kernel_call(...)` 的函数说明从并列“`launch_kernel[...]` / `launch_kernel(...)`”改成“解析 `launch_kernel[...]` 公开入口，并兼容旧直调用启动描述”。
  - 将 `_parse_launch_kernel_call(...)` 的功能说明改为“公开 DSL 入口固定为 `launch_kernel[...]`，旧直调用 `launch_kernel(...)` 仅作兼容路径”。
  - 将 `_parse_dma_call(...)` 的 helper 说明从“将 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 解析为 `ArchLaunchKernelAST`”改成“将公开入口 `launch_kernel[...]` 解析为 `ArchLaunchKernelAST`，旧直调用仅作兼容路径且不属于公开合同”。
- 本轮未改 `expectation`、测试文件或其他实现逻辑；当前 worktree 里的 4 份 spec 改动沿用前序 build 结果，只补 parser 说明文本缺口。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 status --short` -> 当前 diff 为 `kernel_gen/dsl/ast/parser.py` 加前序已存在的 4 份 spec 与记录文件。
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/kernel_gen/dsl/ast/parser.py` -> 通过。
- `python3 - <<'PY' ...` -> `spec/parser boundary checks passed`；已确认 4 份 spec 都以 `launch_kernel[...]` 作为公开入口、`spec/dsl/gen_kernel.md` 已清掉旧三字段 `arch.launch<%b, %t, %s>(@missing_body, ...)` 示例、`parser.py` 已写明旧直调用只作兼容路径且不再保留旧并列表述。
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 diff --check` -> 通过。
Diff 反推自测：按当前实际 diff 反推，当前 review 面覆盖 `kernel_gen/dsl/ast/parser.py` 与 4 份 spec，因此自测同时覆盖 parser/AST 相关回归和 spec/parser 文案一致性检查，不把 `expectation` 算进 diff 反推测试。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/test/dsl/test_ast.py -k 'launch_kernel or barrier'` -> `4 passed, 43 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/test/dsl/test_ast_visitor.py -k 'launch_kernel'` -> `3 passed, 200 deselected, 1 warning`
- `python3 - <<'PY' ...` -> `spec/parser boundary checks passed`
合同验收（如适用）：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2:/home/lfr/kernelcode_generate python3 -m expectation.operation.arch` -> 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.arch` -> 通过。
自检：
- 已读完整任务行、计划书正文、完成态 / 验收设计和前序记录，本轮执行内容与 `build` 退回口径一致，没有混做 review 或 merge。
- 只改了 `kernel_gen/dsl/ast/parser.py` 的说明文本，没有越权改 `expectation`、计划书或其他角色文件。
- 当前 diff 对应的 parser/AST 回归、spec/parser 一致性检查和相关合同验收都已单列完成；`expectation` 未计入 Diff 反推自测。
- 公开入口、兼容路径、四字段 `arch.launch` 示例与 parser 说明现在一致，未发现当前切片内继续可直接修的同类残留。
结论：本轮 build 已完成，任务记录已写入当前 worktree；下一步执行 `-next -auto -type review` 并回报管理员。

---
时间：2026-04-24 00:48 +0800
经办人：提莫炖蘑菇
任务：T-20260424-2e64ba19（review）
任务目标：复核 parser 说明文本是否已把 `launch_kernel[...]` 固定为公开入口、旧直调用只保留兼容路径，并确认当前 diff 的 AST/parser 回归与相关 arch 合同验收已单列收口。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:7) 中当前任务行，确认任务仍处于 `review`。
- 已重读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的计划正文、完成态定义、验收设计与前序修复记录。
- 已重读当前任务记录中的 build / review 往返条目，并现场核对 [`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py)、[`spec/dsl/ast.md`](../../../../../../../spec/dsl/ast.md)、[`spec/dsl/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel.md)、[`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)、[`spec/operation/arch.md`](../../../../../../../spec/operation/arch.md) 的最新内容。
真实审查：
- 当前实际 diff 只覆盖 5 个文件：[kernel_gen/dsl/ast/parser.py](../../../../../../../kernel_gen/dsl/ast/parser.py)、[spec/dsl/ast.md](../../../../../../../spec/dsl/ast.md)、[spec/dsl/gen_kernel.md](../../../../../../../spec/dsl/gen_kernel.md)、[spec/dsl/mlir_gen.md](../../../../../../../spec/dsl/mlir_gen.md)、[spec/operation/arch.md](../../../../../../../spec/operation/arch.md)。
- 现场核对结果：
  - [`spec/dsl/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel.md) 已清掉旧三字段 `arch.launch<%b, %t, %s>(@missing_body, ...)` 示例，并统一为四字段 `arch.launch<%b, %t, %s, %smem>(@missing_body, ...)`。
  - [`spec/dsl/ast.md`](../../../../../../../spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)、[`spec/operation/arch.md`](../../../../../../../spec/operation/arch.md) 已统一将公开入口写成 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`，旧直调用只作为兼容路径说明。
  - [`kernel_gen/dsl/ast/parser.py`](../../../../../../../kernel_gen/dsl/ast/parser.py) 中 `_parse_launch_kernel_call(...)` 与 `_parse_dma_call(...)` 的说明文本也已同步：公开入口固定为 `launch_kernel[...]`，旧直调用仅作兼容路径，不再与公开入口并列描述。
Diff 反推审查：
- 按当前 diff 反推执行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/test/dsl/test_ast.py -k 'launch_kernel or barrier' -ra` -> `4 passed, 43 deselected, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/test/dsl/test_ast_visitor.py -k 'launch_kernel' -ra` -> `3 passed, 200 deselected, 1 warning`
  - `python3 - <<'PY' ...` 本地检查脚本结果：
    - `gen_kernel_old_three_field_missing_body_absent=True`
    - `gen_kernel_new_four_field_missing_body_present=True`
    - `spec_ast_public_subscript_present=True`
    - `spec_mlir_gen_public_subscript_present=True`
    - `spec_operation_arch_public_subscript_present=True`
    - `parser_public_subscript_doc_present=True`
    - `parser_compat_only_doc_present=True`
    - `parser_old_parallel_title_absent=True`
  - `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 diff --check` -> 通过
合同验收：
- `expectation` 本轮只作为合同验收资产单列说明。
- 相关 arch expectation 已在前序 build 记录中单列通过，但本轮未把 `expectation` 计入 Diff 反推审查。
可改进点：
- 当前切片内未再发现可直接执行、且会影响结论的残留项。
自检：
- 已先读计划书阶段正文、完成态、验收设计和前序记录，再按最新实际 diff 做现场复核，没有只复述 build 摘要。
- 审查范围严格限定在当前 5 个 diff 文件及其直接对应的 AST/parser 回归，没有把 `expectation` 混入 diff 反推测试。
- 当前没有继续可执行的一线问题，因此本轮可结束 review。
结论：
- 结论：`通过`
- 下一步：推进 `merge`。

---
时间：2026-04-24 17:25 +0800
经办人：李白
任务：T-20260424-2e64ba19（merge）
任务目标：按最新通过的 review 结论合并 `launch_kernel[...]` 公开入口与相关 spec / parser 说明收口结果，并在最新主线之上完成同步确认。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认本任务状态为 `merge`，worktree、计划书、记录文件与指派一致。
- 已重读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的当前修复口径、全局完成态 / 验收设计与前序记录。
- 已重读本记录中的最新 build / review 条目，确认记录已包含 `执行前阅读记录`、`最小功能闭环`、`自检`、`Diff 反推自测`、`Diff 反推审查`，且 `expectation` 只作合同验收资产单列。
合并前同步：
- `timeout 60 git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 fetch origin` -> 已完成。
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 rebase --autostash origin/main` -> 已完成，当前 worktree 位于 `origin/main@5d48435` 之上。
- 同步后 residual diff 只包含 [`kernel_gen/dsl/ast/parser.py`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/kernel_gen/dsl/ast/parser.py)、[`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/spec/dsl/ast.md)、[`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/spec/dsl/gen_kernel.md)、[`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/spec/dsl/mlir_gen.md)、[`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2/spec/operation/arch.md)。
真实收口过程：
- 已核对当前 diff 与计划书修复口径一致：`spec` 与 parser 说明统一到 `launch_kernel[...]` 公开入口，旧直调用只保留兼容路径说明。
- 已核对前序记录中的 diff 反推测试围绕 AST/parser 与相关 spec 边界展开，没有把 `expectation` 当作对应测试替代。
- 本轮 merge 不追加实现或测试口径，只把已通过 review 的 residual diff 收到主线。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2 diff --check` -> 通过
合同验收：
- `expectation` 继续只作为合同验收资产单列；本轮 merge 未执行 `expectation`，也未把它计入 diff 反推测试。
结论：
- 当前修复 diff 已按最新 review 结论完成收口，可进入提交、推送与 `-done` 流程。
