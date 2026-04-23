时间：2026-04-24 02:03 +0800
经办人：jcc你莫辜负
任务：T-20260424-78a40d80（build）
任务目标：继续清理 `main_npu_demo_pipeline_fold_cse` 计划的旧 `launch_kernel` 直调用兼容表述；仅收口 [`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)、[`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md) 与 [`kernel_gen/dsl/ast/parser.py`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py) 中仍保留的旧直调用文本，统一到 `launch_kernel[...]` 公开入口。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:4) 当前任务行。
- 已读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的计划正文、终验失败摘要、全局完成态 / 验收设计，以及本轮唯一修复任务说明。
- 已读前序 [`20260424-main-npu-demo-final-repair-s2.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/agents/codex-multi-agents/log/task_records/2026/17/20260424-main-npu-demo-final-repair-s2.md)，确认 S2 已把公开入口改成 `launch_kernel[...]`，当前只剩 4 个文件中的旧直调用说明文本待清理。
- 现场核对发现 `TODO.md` 指定的 `worktree` 路径原先不存在；本轮先以 `e7cde08`（S2 完成态）创建 `/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3`，再在该现场继续推进，避免把改动写到主仓或其他现场。
最小功能闭环：
- 这轮只改 4 个文件中的文案 / 说明，不改 `launch_kernel` 实现行为。
- 公开合同与说明文本统一只保留 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`。
- 当前切片内不再把旧直调用 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 写成公开入口、兼容入口或正文并列表述。
改动：
- 更新 [`kernel_gen/dsl/ast/parser.py`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py)：`_parse_launch_kernel_call(...)` 的函数说明与使用示例只保留 `launch_kernel[...]` 公开入口，不再并列旧直调用说明。
- 更新 [`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)：删除 `launch_kernel` 公开 DSL 入口段落末尾的旧直调用兼容句，收紧为单一公开入口说明。
- 更新 [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md)：删除 lowering 规则段落中对旧直调用兼容路径的正文说明。
- 更新 [`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)：去掉公开调用形态里的旧直调用兼容描述，并把 `TC-OP-ARCH-014` 收紧为“公开语义、示例与错误路径不得回退为旧直调用写法”。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/test/dsl/test_ast.py -k 'launch_kernel or barrier' -ra` -> `4 passed, 43 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/test/dsl/test_ast_visitor.py -k 'launch_kernel' -ra` -> `3 passed, 200 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/test/dsl/ast/test_parser_private_helpers.py -k 'test_parser_private_helpers_call_and_function_contracts' -ra` -> `1 passed, 5 deselected, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py` -> 通过
- `python3 - <<'PY' ...` 本地检查脚本确认 4 个目标文件中 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 与 `兼容旧直调用` / `兼容路径` 文本均已不存在 -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3 diff --check` -> 通过
Diff 反推自测：
- 实际 diff 只覆盖 1 个 parser 说明文件和 3 个 spec 文件，因此自测按“parser 公开入口语义是否仍稳定 + 文本口径是否已从旧直调用收回”反推为 AST / AST visitor / parser private helper 三组 `pytest`，再配合本地检查脚本核对这 4 个文件的目标文本。
- 本轮没有把 `expectation` 当作 diff 对应测试替代；`expectation` 继续只作合同验收资产单列。
合同验收资产（单列）：
- 本轮未执行 `expectation`。当前 diff 只涉及 spec / parser 说明文本，且任务口径明确不把无关 `expectation` 链路扩进本轮 build。
自检：
- 边界：只改任务点名的 4 个文件，没有扩到实现行为、runtime、`expectation` 或其他现场。
- API / 文案一致性：`spec/operation/arch.md`、`spec/dsl/ast.md`、`spec/dsl/mlir_gen.md` 与 `kernel_gen/dsl/ast/parser.py` 现在都只把 `launch_kernel[...]` 写成公开入口，未发现当前切片内继续并列旧直调用的残留。
- 测试有效性：本轮代码改动只在 parser 说明文本，相关 `pytest` 已覆盖 AST 入口、visitor 链路与 parser helper 主链；文案残留则由本地检查脚本直接锁定。
- 可维护性：保留单一公开入口后，下游 review 不需要再在 spec / parser 之间做双口径解释。
结论：本轮 build 已完成，记录已写入当前 worktree；下一步执行 `-next -auto -type review` 并回报管理员。

时间：2026-04-24 18:01 +0800
经办人：不要啊教练
任务：T-20260424-78a40d80（review）
任务目标：复核 S3 修复是否已把 `spec/operation/arch.md`、`spec/dsl/ast.md`、`spec/dsl/mlir_gen.md` 与 `kernel_gen/dsl/ast/parser.py` 中旧 `launch_kernel` 直调用说明收回为 `launch_kernel[...]` 单一公开入口。
执行前阅读记录：
- 已阅读 [`TODO.md`](../../../../../../../TODO.md) 中 `T-20260424-78a40d80` 任务行，确认当前 worktree 为 [`wt-20260424-main-npu-demo-final-repair-s3`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3)，任务类型为 `review`。
- 已阅读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](../../../../../../../ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的当前修复口径、全局完成态 / 验收设计与 2026-04-24 双架构终验阻断摘要，确认当前唯一修复目标只收 4 个文件中的旧 `launch_kernel` 直调用说明文本。
- 已阅读前序记录 [`20260424-main-npu-demo-final-repair-s2.md`](../../../../../../../agents/codex-multi-agents/log/task_records/2026/17/20260424-main-npu-demo-final-repair-s2.md) 与本 worktree 的 build 记录，确认 S2 已把公开入口统一到 `launch_kernel[...]`，本轮只继续清理剩余说明文本。
真实审查：
- 当前实际 diff 只包含 [`spec/operation/arch.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)、[`spec/dsl/ast.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md)、[`kernel_gen/dsl/ast/parser.py`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py)。
- 我现场核对后确认，这 4 个目标文件内已经清掉 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 这一旧直调用写法，公开口径统一为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`；build 记录里的文本检查结论与现场一致。
- 但当前 diff 仍留有一条可执行问题：3 个发生实际修改的 spec 文件头部 `最后一次更改` 元数据没有同步更新，仍停在旧修改者，和本轮实际编辑事实不一致。
问题清单：
- `P2` 文件/接口：[`spec/operation/arch.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)、[`spec/dsl/ast.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md)
  - 现象：这 3 个 spec 文件在本轮实际发生了文本改动，但文件头 `最后一次更改` 仍分别写着旧值 `睡觉小分队`。
  - 影响：文档公开元数据与当前实际修改者不一致，后续追踪“这轮是谁改了公开合同文本”时会产生误导。
  - 建议：把这 3 个文件头的 `最后一次更改` 更新为本轮实际修改者，再回流 review。
可改进点：
- build 记录中的本地检查脚本已经能锁住“旧直调用文本是否仍存在”，这一点是有效的；但若后续继续做文档修复，建议把文件头元数据同步检查也纳入同一个脚本，避免文本正文改了而元数据停在旧状态。
Diff 反推审查：
- 被审 diff 文件：[`spec/operation/arch.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)、[`spec/dsl/ast.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md)、[`kernel_gen/dsl/ast/parser.py`](../../../../../../../wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py)
- 复跑命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q test/dsl/test_ast.py -k 'launch_kernel or barrier' -ra` -> `4 passed, 43 deselected, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q test/dsl/test_ast_visitor.py -k 'launch_kernel' -ra` -> `3 passed, 200 deselected, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q test/dsl/ast/test_parser_private_helpers.py -k 'test_parser_private_helpers_call_and_function_contracts' -ra` -> `1 passed, 5 deselected, 1 warning`
  - `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py` -> 通过
  - `python3 - <<'PY' ...` 文本检查脚本确认 4 个目标文件都包含 `launch_kernel[...]` 且不再包含旧直调用全文字串 -> `boundary-text-checks-passed`
  - `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3 diff --check` -> 通过
- 审查结论：目标文本收口已完成，diff 对应测试也都通过；当前未闭合点是 3 个 spec 文件头元数据没有同步更新。
合同验收（单列，不计入 Diff 反推审查）：
- 本轮未执行 `expectation`。当前 diff 只涉及 spec / parser 说明文本，且任务要求明确 `expectation` 只作为合同验收资产单列，不替代 diff 对应测试。
自检：
- 已按任务要求写清真实审查、Diff 反推审查与可改进点；已核对 build 记录中 `执行前阅读记录`、`最小功能闭环`、`自检` 与 `Diff 反推自测` 字段齐全。
- 当前仍存在明确可执行的一线改进项，即 spec 文件头元数据未同步；按当前审查口径，结论只能为 `需修改`。
结论：需修改。当前 4 个文件的旧 `launch_kernel` 直调用说明已经收回到 `launch_kernel[...]` 单一公开入口，但 3 个发生实际修改的 spec 文件头 `最后一次更改` 仍停在旧值，需先把文档元数据同步到本轮修改事实，再回流 review。

时间：2026-04-24 02:08 +0800
经办人：睡觉小分队
任务：T-20260424-78a40d80（spec）
任务目标：按最新 review 退回点补齐 [`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)、[`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md) 文件头 `最后一次更改` 元数据，并把任务续回 `review`。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:7) 当前任务行，确认 `worktree`、计划书和记录文件与当前指派一致。
- 已读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 当前修复口径与验收设计，确认这轮只收 3 个 `spec` 文件头元数据，不再扩写正文或实现。
- 已读本记录中最新 build / review 条目，确认 `launch_kernel[...]` 公开入口统一、AST/parser 相关 `pytest` 与文本检查都已通过，当前唯一未闭合点是 3 个 `spec` 文件头 `最后一次更改` 仍停在旧值。
- 已现场核对 [`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)、[`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md) 当前文件头，三者的 `最后一次更改` 均为旧值 `睡觉小分队`。
最小功能闭环：
- 仅把 3 个实际改动过的 `spec` 文件头 `最后一次更改` 同步到本轮实际修改者 `jcc你莫辜负`。
- 不改 `launch_kernel[...]` 正文、不改 [`kernel_gen/dsl/ast/parser.py`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py)、不重跑与当前 diff 无关的 `pytest`。
改动：
- 更新 [`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md) 文件头，把 `最后一次更改` 从 `睡觉小分队` 改为 `jcc你莫辜负`。
- 更新 [`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md) 文件头，把 `最后一次更改` 从 `睡觉小分队` 改为 `jcc你莫辜负`。
- 更新 [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md) 文件头，把 `最后一次更改` 从 `睡觉小分队` 改为 `jcc你莫辜负`。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3 diff --check -- spec/operation/arch.md spec/dsl/ast.md spec/dsl/mlir_gen.md agents/codex-multi-agents/log/task_records/2026/17/20260424-main-npu-demo-final-repair-s3.md`
  - 结果：通过。
- `python3` 断言脚本核对 3 个目标 `spec` 文件都包含 `最后一次更改：\`jcc你莫辜负\``
  - 结果：`metadata-check-passed`
Diff 反推自测：
- 本轮实际 diff 只落在 3 个 `spec` 文件头元数据与当前任务记录，因此反推自测只做文件头断言脚本与 `git diff --check`，没有扩跑 AST / parser `pytest`。
- AST / parser 相关 `pytest` 与文本检查已由本记录中的上一轮 build / review 条目覆盖；当前 diff 未触及对应正文和实现。
合同验收（如适用）：
- 本轮未执行 `expectation`，也未把 `expectation` 计入当前 diff 的对应检查。
自检：
- 已按要求先读计划书、最新任务记录与 review 退回点，再按当前 diff 最小范围处理，没有越界改正文、实现或测试。
- 3 个 `spec` 文件头现在与本轮实际修改者一致；当前切片内未再留下“正文已改、元数据仍停旧值”的不一致状态。
- 当前检查方式与 diff 范围匹配，build / review 已通过的 AST / parser `pytest` 没有被重复当作本轮元数据修复的对应测试。
结论：本轮 `spec` 修复已完成，任务记录已追加到当前 `worktree`；下一步执行 `-next -auto -type review` 并回报管理员继续推进。

时间：2026-04-24 02:34 +0800
经办人：不要啊教练
任务：T-20260424-78a40d80（review）
任务目标：复核 `spec/operation/arch.md`、`spec/dsl/ast.md`、`spec/dsl/mlir_gen.md` 文件头 `最后一次更改` 已同步到本轮实际修改者，且 `launch_kernel[...]` 单一公开入口口径仍保持不变。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 中 `T-20260424-78a40d80` 当前任务行，确认任务仍处于 `review`，当前 `worktree`、计划书和记录文件一致。
- 已重读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 当前 S3 修复口径、全局完成态与验收设计，确认本轮只复核 3 个 `spec` 文件头元数据与 `launch_kernel[...]` 单一公开入口文案是否保持不变。
- 已重读本记录中的上一轮 `review` 与最新 `spec` 条目，确认上一轮唯一退回点是 3 个 `spec` 文件头 `最后一次更改` 未同步，最新 `spec` 已把该元数据统一改为 `jcc你莫辜负` 并续回 `review`。
真实审查：
- 现场 diff 仍只覆盖 [`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)、[`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md)、[`kernel_gen/dsl/ast/parser.py`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py) 与当前任务记录。
- 我已现场核对 3 个 `spec` 文件头，`最后一次更改` 现在都为 `jcc你莫辜负`，与本轮正文实际修改者保持一致；上一轮指出的元数据不一致已收住。
- 我再次核对了这 4 个目标文件的正文文本，没有发现旧 `launch_kernel(callee, block, thread, subthread, shared_memory_size, *args)` 直调用说明回流；公开口径仍统一为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`。
- 本轮没有再看到当前切片内可直接执行的一线改进项。
可改进点：
- 本轮复核范围内未发现新的可执行问题。
Diff 反推审查：
- 被审 diff 文件：[`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)、[`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md)、[`kernel_gen/dsl/ast/parser.py`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py)
- 复跑命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q test/dsl/test_ast.py -k 'launch_kernel or barrier' -ra` -> `4 passed, 43 deselected, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q test/dsl/test_ast_visitor.py -k 'launch_kernel' -ra` -> `3 passed, 200 deselected, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3:/home/lfr/kernelcode_generate pytest -q test/dsl/ast/test_parser_private_helpers.py -k 'test_parser_private_helpers_call_and_function_contracts' -ra` -> `1 passed, 5 deselected, 1 warning`
  - `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py` -> 通过
  - 本地文本检查脚本确认 4 个目标文件都包含 `launch_kernel[...]`，且不再包含旧直调用全文字串 -> `boundary-text-checks-passed`
  - `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3 diff --check` -> 通过
- 审查结论：当前 diff 对应的文档与 parser 文本口径一致，相关 AST / parser 验证通过，上一轮退回点已修复。
合同验收（单列，不计入 Diff 反推审查）：
- 本轮未执行 `expectation`。当前 diff 只涉及 `spec` / parser 说明文本，相关 `expectation` 继续只作合同验收资产单列，不替代 diff 对应测试。
自检：
- 已按要求写清执行前阅读记录、真实审查、Diff 反推审查、可改进点与合同验收单列状态。
- 已再次核对 build 与 spec 记录中的自检 / Diff 反推字段完整，当前 review 结论与现场 diff、测试和文本检查一致。
结论：通过。3 个 `spec` 文件头 `最后一次更改` 已同步到本轮实际修改者，`launch_kernel[...]` 单一公开入口口径保持不变，当前切片内未发现新的可执行问题。

---
时间：2026-04-24 18:17 +0800
经办人：李白
任务：T-20260424-78a40d80（merge）
任务目标：按最新通过的 review 结论合并 main_npu_demo S3 最后一轮 spec / parser 文本收口结果，并在最新主线之上完成同步确认。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认本任务状态为 `merge`，worktree、计划书和记录文件一致。
- 已重读 [`ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/main_npu_demo_pipeline_fold_cse_green_plan.md) 的当前修复口径、全局完成态 / 验收设计与前序记录。
- 已重读本记录中的最新 build / review 条目，确认记录已包含 `执行前阅读记录`、`最小功能闭环`、`自检`、`Diff 反推自测`、`Diff 反推审查`，且 `expectation` 只作合同验收资产单列。
合并前同步：
- `timeout 60 git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3 fetch origin` -> 已完成。
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3 rebase --autostash origin/main` -> 已完成，当前 worktree 已同步到 `origin/main@737badc`。
- 同步后 residual diff 只包含 [`kernel_gen/dsl/ast/parser.py`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/kernel_gen/dsl/ast/parser.py)、[`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/dsl/mlir_gen.md)、[`spec/operation/arch.md`](/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3/spec/operation/arch.md)。
真实收口过程：
- 已核对当前 diff 与计划书修复口径一致：公开文本只保留 `launch_kernel[...]` 单一入口，旧直调用说明已从当前切片收回。
- 已核对前序记录中的 diff 反推测试围绕 AST / parser 与对应 spec 边界展开，没有把 `expectation` 当作对应测试替代。
- 本轮 merge 不追加实现行为或测试口径，只把已通过 review 的 residual diff 收到主线。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3 diff --check` -> 通过
合同验收：
- `expectation` 继续只作为合同验收资产单列；本轮 merge 未执行 `expectation`，也未把它计入 diff 反推测试。
结论：
- 当前修复 diff 已按最新 review 结论完成收口，可进入提交、推送与 `-done` 流程。
