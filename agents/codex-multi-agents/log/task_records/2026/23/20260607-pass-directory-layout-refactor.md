时间：2026-06-07 03:18 +0800
经办人：神秘人
任务：pass-directory-layout-refactor / 管理员下发前记录
任务目标：为正式计划 `ARCHITECTURE/plan/pass_directory_layout_refactor.md` 创建并分发唯一计划级 `execute`，不拆分 S1-S5 子任务。
改动：
- 已读取根 `AGENTS.md`、`agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/任务记录约定.md`、`agents/standard/角色权限矩阵.md`、正式计划 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`、`TODO.md`、`agents/codex-multi-agents/agents-lists.md` 与守护回执。
- 核对下发前置：Draft 3-R1 两路 strict review 已通过；`agents/codex-multi-agents/log/talk.log:11261` 守护最终检验结论为通过，阻断项=无，最小需改项=无，待确认项=无。
- 核对正式计划已进入主仓 index：`git ls-files --stage -- ARCHITECTURE/plan/pass_directory_layout_refactor.md` 为 `100644 fed7a8d20170d2eb712fae3cbcff6637fba15ac5 0`；`git diff --cached --name-status -- ARCHITECTURE/plan/pass_directory_layout_refactor.md` 为 `A ARCHITECTURE/plan/pass_directory_layout_refactor.md`；回写后计划 `sha256=98ad7ddb26c4a4758a86e6e54591f105b4ee4ea83a9ffbea87e559c3b8d30ee5`。
- 核对当前 `TODO.md` 尚无本计划任务，计划列表尚无 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`；当前运行任务只有 `T-20260606-bd595479 / review / 提莫炖蘑菇`，并行数未超过 8。
- 已创建独立 worktree `/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`，分支 `task/pass-directory-layout-refactor`；已从主仓 index 机械检出同一正式计划对象到任务 worktree，并在任务 worktree 中 `git add -f ARCHITECTURE/plan/pass_directory_layout_refactor.md`，确保执行人可读正式计划。
- 已确认主仓存在无关现场：`ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md` 已暂存，`agents/codex-multi-agents/log/task_records/2026/23/20260604-dma-ring-dynamic-make-ring-operands.md` 有未暂存修改；本任务下发不纳入这些文件。
- 下发禁止修改面：`expectation/` 只读；不得修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`；若 execute 发现必须修改公开 API 或 `expectation/` 本体，必须停止并回报管理员转用户或架构师确认。
验证：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -plan-list`：退出码 0，尚无本计划条目。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing`：退出码 0，当前仅 `T-20260606-bd595479` 进行中。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file agents/codex-multi-agents/agents-lists.md -status`：退出码 0，`睡觉小分队`、`小李飞刀`、`金铲铲大作战`、`咯咯咯` 均为空闲 execute 角色；选择 `睡觉小分队` 承接本计划级 execute。
- `git worktree add -b task/pass-directory-layout-refactor /home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor HEAD`：退出码 0。
- `git checkout-index --force --prefix=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor/ ARCHITECTURE/plan/pass_directory_layout_refactor.md` 与 `git -C /home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor add -f ARCHITECTURE/plan/pass_directory_layout_refactor.md`：退出码 0。
自检：本轮仅做管理员下发准备、worktree 资产可读性补齐和记录；未修改功能实现、`spec/`、`test/`、`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、主仓 `TODO.md` 或 `DONE.md`；计划内公开 API 口径已有用户确认来源和守护通过记录；本计划只创建一个计划级 `execute`，不拆分 S1-S5。
结论：下发前置满足；下一步用任务脚本创建唯一计划级 `execute` 并 dispatch 给 `睡觉小分队`。

时间：2026-06-07 03:19 +0800
经办人：神秘人
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 管理员创建记录
任务目标：创建正式计划 `ARCHITECTURE/plan/pass_directory_layout_refactor.md` 的唯一计划级 `execute` 任务。
改动：
- 已用任务脚本创建 `T-20260607-3318f2e2`，任务类型为 `execute`，计划书为 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`，worktree 为 `/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`，记录文件为 `agents/codex-multi-agents/log/task_records/2026/23/20260607-pass-directory-layout-refactor.md`，依赖为 `None`。
- 任务目标写明：按正式计划收口 pass 实现、`spec` 和 pytest 目录到 `arch/kernel/memory/tuning`；保留旧公开 import path compat shim；同步 registry、pipeline、spec、tests；运行计划内 diff 反推 pytest、文本门禁和 12 个只读 `expectation` 合同验收；补齐执行前阅读、最小功能闭环、自检、`Diff 反推自测`、减法检查和结论。
- 创建时未拆分 S1-S5 子任务，未创建第二个计划级 execute。
验证：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -new ...`：退出码 0，输出 `OK: new T-20260607-3318f2e2`。
自检：本轮只更新任务状态与任务记录；未触碰功能实现、`spec/`、`test/`、`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、主仓 `TODO.md` 或 `DONE.md` 的手工编辑；`TODO.md` 变更由任务脚本生成。
结论：任务已创建；下一步 dispatch 给空闲计划级执行角色 `睡觉小分队`。

时间：2026-06-07 03:20 +0800
经办人：神秘人
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 管理员分发记录
任务目标：将唯一计划级 `execute` 分发给空闲执行角色，并同步任务状态与会话通知。
改动：
- 已将 `T-20260607-3318f2e2` dispatch 给 `睡觉小分队`。
- 分发消息已写清：本任务是唯一计划级 `execute`，不拆 S1-S5；执行目录为 `/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`；状态文件使用主仓绝对路径 `/home/lfr/kernelcode_generate/TODO.md`；记录写入该 worktree 下 `agents/codex-multi-agents/log/task_records/2026/23/20260607-pass-directory-layout-refactor.md`；禁止修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`；不得纳入主仓无关现场 `ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md` 与 `20260604-dma-ring` 记录。
- 分发消息已要求执行人运行计划内 diff 反推 pytest、文本门禁和 12 个只读 `expectation` 合同验收，并补齐执行前阅读、最小功能闭环、自检、`Diff 反推自测`、减法检查和结论。
- 分发消息已明确：若发现必须修改公开 API 或 `expectation/` 本体，停止并回报管理员转用户或架构师确认；完成后按 `execute -> review -> archive_acceptance -> merge/归档` 流转。
验证：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -dispatch -task_id T-20260607-3318f2e2 -to 睡觉小分队 -type execute -agents-list agents/codex-multi-agents/agents-lists.md ...`：退出码 0，输出 `OK: dispatch T-20260607-3318f2e2 -> 睡觉小分队`、`OK: replace 睡觉小分队 状态`、`OK: talk 神秘人 -> 睡觉小分队 (睡觉小分队)`。
自检：本轮通过任务脚本维护 `TODO.md` 与 `agents-lists.md`，未手工修改状态文件；未做实现、审查、合并或技术裁决；分发目标是空闲计划级 execute 角色；公开 API 与 `expectation/` 变更均已在消息中列为升级项。
结论：`T-20260607-3318f2e2` 已进入 `execute / 睡觉小分队 / 进行中`。

时间：2026-06-07 03:21 +0800
经办人：神秘人
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 管理员下发后核对
任务目标：核对任务状态、计划表、角色占用、worktree 资产和无关现场隔离。
改动：
- 核对 `TODO.md` 运行表：`T-20260607-3318f2e2` 已存在，任务类型 `execute`，计划书 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`，指派 `睡觉小分队`，状态 `进行中`。
- 核对计划表：`ARCHITECTURE/plan/pass_directory_layout_refactor.md` 为总任务数 1、已完成 0、待完成 1、状态 `进行中`；未拆分 S1-S5 子任务。
- 核对角色列表：`睡觉小分队` 已为 `busy`；并行任务数为 2，未超过最大并行数 8。
- 核对任务 worktree：`ARCHITECTURE/plan/pass_directory_layout_refactor.md` 已 staged，`sha256=98ad7ddb26c4a4758a86e6e54591f105b4ee4ea83a9ffbea87e559c3b8d30ee5`；本记录文件已在任务 worktree 中维护。
- 核对主仓无关现场仍独立：`ARCHITECTURE/plan/symbol_memory_query_reinterpret_operand_fold.md` 仍为已暂存无关计划，`agents/codex-multi-agents/log/task_records/2026/23/20260604-dma-ring-dynamic-make-ring-operands.md` 仍为未暂存无关修改；未纳入本任务 worktree 计划资产同步范围。
验证：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing`：退出码 0，运行表含 `T-20260607-3318f2e2 / execute / 睡觉小分队 / 进行中`。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -plan-list`：退出码 0，计划表含 `ARCHITECTURE/plan/pass_directory_layout_refactor.md | 1 | 0 | 1 | 进行中`。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file agents/codex-multi-agents/agents-lists.md -status`：退出码 0，`睡觉小分队` 状态为 `busy`。
- `git -C /home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor status --short --untracked-files=all -- ARCHITECTURE/plan/pass_directory_layout_refactor.md agents/codex-multi-agents/log/task_records/2026/23/20260607-pass-directory-layout-refactor.md`：显示正式计划已新增，记录文件已维护。
- `tail -n 8 agents/codex-multi-agents/log/talk.log`：可见 `神秘人 -> 睡觉小分队` 的分发消息。
自检：本轮仍只做管理员状态核对和记录；未执行 pytest，不替 execute 做验收；未修改 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md` 或计划外业务文件；`TODO.md` 与 `agents-lists.md` 仅由任务脚本维护。
结论：下发完成；当前阶段为 `execute`，责任角色为 `睡觉小分队`，下一步等待执行人按计划完成实现、spec、测试、合同验收和任务记录后回报管理员流转到 `review`。

时间：2026-06-07 12:06 +0800
经办人：睡觉小分队
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / execute 阶段阻塞记录
任务目标：按正式计划把 pass 实现、spec 与 pytest 目录收口到 `arch / kernel / memory / tuning`，保留旧 public import path compat shim，运行 pytest、文本门禁与 12 个只读 expectation；若发现必须修改公开 API、pipeline 行为或 expectation 本体，先记录并回报管理员 / 架构师。
执行前阅读记录：
- 已读根 `AGENTS.md`、`agents/standard/任务记录约定.md`、正式计划 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`、本任务前序记录、当前 `TODO.md` / talk 回执。
- 已核对管理员 2026-06-07 回执：旧任务 `T-20260605-0b33f547` 已 merge，属于历史残留；本轮只处理当前 TODO 中的 `T-20260607-3318f2e2`。
- 已核对正式计划禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、正式计划正文；本轮未修改这些禁止面。`ARCHITECTURE/plan/pass_directory_layout_refactor.md` 为管理员下发时已 staged 计划资产，sha256 仍为 `98ad7ddb26c4a4758a86e6e54591f105b4ee4ea83a9ffbea87e559c3b8d30ee5`。
改动：
- 实现目录：将计划范围内 root / 旧 family pass 移到新 canonical module path：
  - `kernel_gen/passes/arch/{arch_parallelize.py, attach_arch_information.py}`
  - `kernel_gen/passes/kernel/{kernel_aggregate.py, kernel_decompose.py}`
  - `kernel_gen/passes/memory/{memory_plan.py, memory_pool.py, multi_buffer.py}`
  - `kernel_gen/passes/tuning/outline_device_kernel.py`
- 新增 family package root：`kernel_gen/passes/arch/__init__.py`、`kernel_gen/passes/kernel/__init__.py`、`kernel_gen/passes/memory/__init__.py`。
- 旧 public import path 保留薄 compat shim：`kernel_gen/passes/arch_parallelize/__init__.py`、`kernel_gen/passes/arch_parallelize/arch_parallelize.py`、`kernel_gen/passes/{attach_arch_information,kernel_aggregate,kernel_decompose,memory_plan,memory_pool,multi_buffer,outline_device_kernel}.py`；shim 只 re-export 公开对象，不承载业务逻辑，不改写 `__module__`。
- 同步 registry / pipeline / package root：`kernel_gen/passes/registry.py`、`kernel_gen/passes/__init__.py`、`kernel_gen/passes/tuning/__init__.py`、`kernel_gen/passes/lowering/__init__.py`、`kernel_gen/pipeline/{npu_demo_lowering.py,cuda_sm86_lowering.py}` 改用新 canonical import；未改变 pass name、pipeline name、构造签名、Pass option、pipeline 顺序或错误文本。
- spec 目录同步到 `spec/pass/{arch,kernel,memory,tuning}`，更新 registry / pass_manager / pipeline / launch_kernel_cost_func 等路径说明；旧 direct path 只作为 compat 说明保留。
- pytest 目录同步到 `test/passes/{arch,kernel,memory,tuning}`，同步 pipeline / tool / DSL 测试中的实现路径引用，并补充 canonical / compat import identity 断言。
最小功能闭环：
- 新 canonical import path 均可 import，公开 class 的 `__module__` 指向新 canonical module。
- 旧 public import path shim 均可 import，并导出与 canonical module 相同的公开对象；旧 shim AST 扫描无 `FunctionDef` / `AsyncFunctionDef` / `ClassDef`。
- registry 与 pipeline 主路径不再从迁移范围旧 direct path 导入；已退场旧 tuning root path `kernel_gen.passes.dma_memory_hierarchy`、`kernel_gen.passes.kernel_pattern_attach`、`kernel_gen.passes.transform_apply` 未恢复。
- 本轮未修改 pass IR 改写语义；公开 pytest 对 pipeline 顺序、multi-buffer ring operands、registry、package root 和 compat path 的断言均通过。
验证：
- Import smoke：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ...` 核对 8 个新 canonical module 与 9 个旧 compat path，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/pipeline/cuda_sm86_lowering.py ...`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py test/passes/test_pattern_public_api_docs.py`：`85 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/arch test/passes/kernel test/passes/memory test/passes/tuning`：`202 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/pipeline/test_cuda_sm86_lowering.py`：`17 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes`：`609 passed, 1 warning`。
- 只读 expectation 运行环境说明：任务 worktree 不含 `expectation.pass` package，直接 `PYTHONPATH=.` 无法发现主仓 ignored expectation；按既有任务口径使用 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate`，确保优先加载任务 worktree 实现、只读加载主仓 expectation 资产；未修改 `expectation/`。
- 只读 expectation 通过 10 项：`expectation.pass.arch_parallelize`、`expectation.pass.attach_arch_information`、`expectation.pass.kernel_aggregate`、`expectation.pass.kernel_decompose`、`expectation.pass.memory_plan`、`expectation.pass.memory_pool`、`expectation.pass.outline_device_kernel`、`expectation.pass.dma_memory_hierarchy.basic`、`expectation.pass.kernel_pattern_attach`、`expectation.pass.transform_apply` 均 exit 0。
- 只读 expectation 失败 2 项：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit 1；失败摘要为 expectation 期望在第三段 `symbol-hoist-pipeline -> cse -> canonicalize` 后插入 `multi-buffer:memory_stage=2:target=npu_demo`，但当前实际顺序直接进入 `producer-consumer-analysis`。当前 `spec/pass/pipeline/npu_demo_lowering.md` 明确“不接入 `MultiBufferPass(memory_stage=3)` / 不包含 `multi-buffer` / 不得新增 pipeline option”，`test/passes/pipeline/test_npu_demo_lowering.py` 也断言 `"multi-buffer" not in markers`。若按 expectation 修复，需要改变公开 pipeline 顺序 / 行为，超出本计划“不改 pipeline 阶段顺序”的边界。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.multi_buffer`：exit 1；失败在 `matmul_ring_memory_stage`，expectation 仍匹配三操作数 `dma.make_ring(memory, num, offset)`。当前实现 / spec / pytest / dialect API 均为四操作数 `DmaMakeRingOp(memory, num, offset, shape_bytes, result_type)`，`test/passes/memory/test_multi_buffer.py` 锁定 `num/offset/shape_bytes`，且旧三操作数回退会冲掉已合并的 DMA dynamic make-ring 合同。
- 文本门禁：`rg -n "kernel_gen\\.passes\\.(arch_parallelize|attach_arch_information|kernel_aggregate|kernel_decompose|memory_plan|memory_pool|multi_buffer|outline_device_kernel)" kernel_gen/pipeline kernel_gen/passes/registry.py test/passes spec/pass kernel_gen/passes` 仅命中 compat shim、compat 测试与 compat 说明；registry / pipeline 主路径未命中旧 direct import。
- 已退场 tuning 旧路径门禁：`importlib.util.find_spec(...)` 核对 `kernel_gen.passes.dma_memory_hierarchy`、`kernel_gen.passes.kernel_pattern_attach`、`kernel_gen.passes.transform_apply` 均为 absent，退出码 0。
- 旧 shim AST 门禁：9 个 compat shim 无函数 / 类定义，退出码 0。
- private callable 扫描：`rg -n "^def _|^class _|^    def _" kernel_gen/passes/arch kernel_gen/passes/kernel kernel_gen/passes/memory kernel_gen/passes/tuning` 命中的是迁移文件原有 private helper / private class；本轮新增 family package root 和 compat shim 未新增 private callable，未新增跨文件非公开 API 调用。
- `git diff --check && git diff --cached --check`：退出码 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff --cached -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 均无输出；正式计划文件仅保留管理员下发时 staged 新增，sha256 与下发记录一致，本轮 execute 未改计划正文。
Diff 反推自测：
- 实现 / registry / pipeline / package root diff 反推：import smoke、`py_compile`、`test_registry.py`、`test_pass_manager.py`、pipeline pytest。
- spec / test 目录迁移 diff 反推：旧路径文本扫描、`test_pattern_public_api_docs.py`、分 family pytest、全量 `test/passes`。
- compat shim diff 反推：旧 shim AST 门禁、compat import identity pytest、旧 direct path 文本门禁。
- 合同验收不计入 diff 反推测试；失败项已单列为合同冲突。
减法检查：
- 新增 private callable：无。新增 `__init__.py` package root 和旧路径 shim 均无私有函数 / 类。
- 改动 private callable：未做算法级改写；迁移文件中的既有 private helper 只随文件 rehome 和路径说明同步保留。扫描结果显示大量既有 helper，因本计划是目录重构，不在本轮做大规模算法拆并；未新增小于 5 行有效代码的 private callable。
- 被替代旧逻辑：旧 direct module 中业务实现被新 canonical module 替代；旧路径保留薄 re-export shim，避免删除 public import path 造成兼容破坏。
- 保留旧逻辑依据：旧 public import path 是计划明确保留的 compat shim；已退场 tuning root path 计划明确不恢复。
自检：
- 接口：未修改 pass class 构造签名、`Pass.name`、registry pass name、pipeline name、pipeline option、稳定错误文本；新增 canonical import path 与旧 compat shim 符合计划公开 API 口径。
- 边界 / 异常：旧 direct path 可 import 且导出 canonical 对象；已退场 tuning 旧路径保持不可 import；pipeline unknown option / pass 顺序由既有 pytest 覆盖。
- 兼容：旧 compat path 仍可服务只读 expectation / 外部 caller；`__module__` 不伪装，保持 canonical path 可审计。
- 实现遗漏 / 冗余：registry、pipeline、package root、spec、pytest、tool / DSL 路径均已同步；旧 shim 无业务逻辑复制。
- 注释 / 文档：迁移实现文件和 shim 文件级说明已更新到新 spec/test/实现路径；spec `API 列表` 跟随新 canonical path 与 compat path 口径。
- 复用 / 函数粒度：没有新增隐藏 helper；未引入嵌套函数或跨文件私有 API 调用。
- 输入输出 / 资源 / 并发 / 性能：本轮为目录 / import / 文档 / 测试路径重构，不改变 IR 生命周期、资源分配、并发模型或 pass 算法复杂度。
- 测试有效性：全量 `test/passes` 通过，覆盖 registry、pipeline、family pass 行为、canonical/compat import；只读 expectation 的 10 项通过证明旧 direct import consumer 大多未破坏；2 项失败均指向计划 / expectation 合同冲突而非目录迁移实现失败。
结论：实现候选和 pytest / 静态门禁已收口，但计划列为必过的 12 个只读 expectation 中有 2 项与当前 spec / pytest / 已合并 DMA make-ring 合同冲突。当前 execute 不进入 `-next review`，不修改 `expectation/`，不改变 `npu-demo-lowering` pipeline 顺序，不回退 `dma.make_ring` 四操作数 API；需管理员转架构师裁定最小下一步：A=修订/更新相关 expectation 或计划验收口径；B=明确授权本任务改变 pipeline 行为与/或 make-ring 合同；C=其它收口方式。

时间：2026-06-07 12:12 +0800
经办人：守护最好的爱莉希雅
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / expectation 合同冲突架构裁定
任务目标：裁定 execute 阶段发现的 2 个只读 expectation 与当前计划边界 / 已合并公开合同冲突的最小处理口径。
改动：
- 裁定选择 A 的“调整本任务验收口径”分支：本任务不更新 `expectation/`，不改变 `npu-demo-lowering` pipeline 行为，不回退 `dma.make_ring` / `DmaMakeRingOp` 现行公开 API。
- `expectation.pass.pipeline.npu_demo_lowering` 当前失败要求新增 `multi-buffer:memory_stage=2:target=npu_demo` 阶段；这属于 `multi_buffer_emitc_runtime_ring` 专项计划范围，不属于本目录重构任务。`pass-directory-layout-refactor` 计划明确“不改 pipeline 阶段顺序 / pass option / 行为语义”，且候选 `spec/pass/pipeline/npu_demo_lowering.md` 与 `test/passes/pipeline/test_npu_demo_lowering.py` 均锁定当前 pipeline 不接入 `multi-buffer`。本任务不得为通过该 expectation 擅自改 pipeline。
- `expectation.pass.multi_buffer` 当前失败落在 `matmul_ring_memory_stage` 仍匹配三操作数 `dma.make_ring(memory, num, offset)`；当前实现 / spec / pytest 已按已合并 DMA make-ring 合同使用四操作数 `memory, num, offset, shape_bytes`。本任务不得为通过旧 expectation 回退公开 API 或 pass 输出。
- 上述 2 个 expectation 入口在本任务中改记为“外部合同漂移 / 非本任务当前阻断”，不作为 `T-20260607-3318f2e2` 进入 review 的阻断项；review 仍需复核它们的失败摘要确实分别落在“要求新增 multi-buffer pipeline 阶段”和“三操作数 make_ring 旧合同”，且不是本目录迁移候选 diff 引入的 import / shim / registry 破坏。
- 原计划其它 10 个只读 expectation 仍为本任务必过；pytest、静态门禁、敏感目录门禁、旧 shim AST 门禁、canonical / compat import smoke、Diff 反推自测仍需全部保持通过并记录。
- 是否需要用户确认：不需要。本裁定不新增 / 删除 / 重命名公开 API，不改变 pipeline 行为，不扩大 `expectation/` 授权，只是在已有计划禁止面下把两项后续外部合同漂移从本目录重构任务的当前必过验收中剥离。若任何角色希望在本任务中新增 `multi-buffer` pipeline 阶段、修改 `expectation/` 正文，或回退 / 调整 `DmaMakeRingOp` operands，则必须另行取得用户确认并修订对应计划。
验证：
- 只读复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：退出码 1；失败摘要为 constructed order 缺少 `multi-buffer:memory_stage=2:target=npu_demo`，实际从第三段 `cse -> canonicalize` 后直接进入 `producer-consumer-analysis`。
- 只读复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.multi_buffer`：退出码 1；失败摘要为 `matmul_ring_memory_stage` 匹配三操作数 `"dma.make_ring"(%backing, %num, %offset)` 失败。
- 已核对正式计划：本任务目标是不改 pass class 构造签名、registry pass name、pipeline name、pass option、返回值或稳定错误文本；`expectation/` 默认只读，发现本体必须修改时暂停回报。
自检：本裁定只追加任务记录并回执，不修改计划正文、功能实现、`spec`、测试、`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 或 `plan/1.md`；不创建任务，不替管理员流转状态。
结论：允许 execute 在保留上述 2 个外部合同漂移记录的前提下继续收口并流转 review；不得把这 2 项失败作为本任务当前阻断，也不得为通过它们修改 pipeline / API / expectation。review 必须按本裁定复核失败归因和剩余 10 项 expectation 通过情况。

时间：2026-06-07 12:11 +0800
经办人：睡觉小分队
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 阻塞回报与暂停确认
任务目标：按用户要求继续核对 TODO，并在有阻塞 / 疑问时通过脚本回报管理员 / 架构师，等待明确回复。
改动：
- 已将候选实现、spec、test、正式计划资产和本任务记录同批 staged；随后修复 staged `git diff --cached --check` 发现的两处迁移文件行尾空格，仅做格式清理。
- 已通过 `-talk` 回报管理员 `神秘人`：实现/spec/test 目录迁移候选已完成并 staged，pytest / 静态门禁通过，12 个只读 expectation 中 10 个通过、2 个合同冲突；当前不 `-next review`，不修改 `expectation/`，不改 pipeline 行为，不回退 make-ring API。
- 已通过 `-talk` 向 `大闸蟹` 发起架构裁定请求，并抄送 `守护最好的爱莉希雅`：请求裁定 A=修订 / 更新 expectation 或计划验收口径，B=明确授权改变 pipeline 行为和 / 或 make-ring 合同，C=其它收口方式。
- 已收到管理员 `神秘人` 回执：任务已按流程暂停；原因限定为计划必过 expectation 与当前 spec / pytest / 已合并合同口径冲突；裁定前不得修改 expectation、不得改变 `npu-demo-lowering` pipeline 行为、不得回退 make-ring API，也不得 `-next review`。
验证：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -talk -from 睡觉小分队 -to 神秘人 ...`：退出码 0，输出 `OK: talk 睡觉小分队 -> 神秘人 (神秘人)`。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -talk -from 睡觉小分队 -to 大闸蟹 ...`：退出码 0，输出 `OK: talk 睡觉小分队 -> 大闸蟹 (大闸蟹)`。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -talk -from 睡觉小分队 -to 守护最好的爱莉希雅 ...`：退出码 0，输出 `OK: talk 睡觉小分队 -> 守护最好的爱莉希雅 (守护最好的爱莉希雅)`。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing`：退出码 0，确认 `T-20260607-3318f2e2` 当前为 `execute / 睡觉小分队 / 暂停`。
- `tail -n 20 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`：可见本角色三条阻塞 / 裁定请求与管理员暂停回执。
- `git diff --cached --check`：行尾空格清理后退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/arch/attach_arch_information.py kernel_gen/passes/tuning/outline_device_kernel.py`：退出码 0。
自检：本轮只做阻塞记录、talk 回报、TODO 状态核对和格式门禁清理；未修改 `expectation/`，未改 pipeline 行为，未回退 make-ring API，未流转 review。候选 diff 保持 staged，等待架构裁定和管理员恢复 / 调整流转。
结论：当前任务暂停，等待架构裁定；裁定前不继续实现、不验收流转、不 `-next review`。

时间：2026-06-07 12:12 +0800
经办人：睡觉小分队
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 架构裁定接收记录
任务目标：记录大闸蟹对两个 expectation 合同冲突的裁定，并保持 execute 暂停等待计划负责人修订验收口径。
改动：
- 已收到 `大闸蟹` 架构裁定：选择 A，但具体为“修订计划验收口径”，不是由本任务修改 expectation。
- 裁定明确：本任务不得改变 `npu-demo-lowering` pipeline 行为，不得接入 `multi-buffer`，不得新增 pipeline option；不得回退或前推 `dma.make_ring` 公开合同；不得修改 `expectation/`。
- 裁定定位：`expectation.pass.pipeline.npu_demo_lowering` 与 `expectation.pass.multi_buffer` 两个失败入口属于共享 ignored expectation 在并行 / 后续计划中被更新后，与本目录重构计划“不改行为、不改 API、expectation 只读”的边界冲突。
- 当前阻断项：正式计划仍把这两个入口列为必过，需要计划负责人修订 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`，将它们从当前必过只读 expectation 列表移到“当前非必过 / 共享 expectation 基线冲突”记录，并写明不改变 pipeline / make_ring 合同、不修改 expectation；修订后需完成两路 strict review 与守护复验。
- 是否需要用户确认：架构裁定为不需要新增用户确认，因为本轮不新增公开 API、不扩大 expectation 授权、不修改 expectation，只修正计划验收入口与当前共享合同状态冲突。
验证：
- 只读核对 TODO：`T-20260607-3318f2e2` 已为 `execute / 睡觉小分队 / 暂停`。
- 候选 diff 仍保持 staged；`git diff --cached --check` 已通过；敏感目录 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 无 diff。
自检：本轮只记录架构裁定，不修改实现、spec、test、pipeline、API 或 expectation；不修改正式计划正文，等待计划负责人修订；不执行 `-next review`。
结论：继续暂停。下一步等待计划负责人完成正式计划验收口径修订、两路 strict review 与守护复验；管理员 / 架构明确恢复后，本 execute 只补记录并按修订口径流转 review。

时间：2026-06-07 12:48 +0800
经办人：睡觉小分队
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / Draft 4 口径恢复后执行收口
任务目标：按管理员恢复口径，只补任务记录并按 Draft 4 验收口径流转 review；不修改正式计划正文、`expectation/`、pipeline 行为或 `dma.make_ring` / `DmaMakeRingOp` 公开合同。
改动：
- 已核对 TODO：`T-20260607-3318f2e2` 已恢复为 `execute / 睡觉小分队 / 进行中`。
- 已核对计划真源：任务 worktree 内 `ARCHITECTURE/plan/pass_directory_layout_refactor.md` 仍为 Draft 3，`sha256=98ad7ddb26c4a4758a86e6e54591f105b4ee4ea83a9ffbea87e559c3b8d30ee5`，index blob 为 `fed7a8d20170d2eb712fae3cbcff6637fba15ac5`；主仓 indexed Draft 4 为当前正式真源，`sha256=0a6e6246b98327585734dd79f0ce95ae444666713dcc75a31b11de6a84966f62`，index blob 为 `ca4fc5ebf62340487b62c478035aecb56bb598fd`。本轮未同步、编辑或改写计划正文，只按管理员指定 Draft 4 口径验收。
- 本轮恢复后未修改功能实现、spec、pytest、pipeline、`expectation/` 或公开 API；只追加任务记录并复跑验收。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes`：`609 passed, 1 warning`。
- 当前必过 10 个只读 expectation 均通过，运行环境为 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate`：
  - `expectation.pass.arch_parallelize`：PASS
  - `expectation.pass.attach_arch_information`：PASS
  - `expectation.pass.kernel_aggregate`：PASS
  - `expectation.pass.kernel_decompose`：PASS
  - `expectation.pass.memory_plan`：PASS
  - `expectation.pass.memory_pool`：PASS
  - `expectation.pass.outline_device_kernel`：PASS
  - `expectation.pass.dma_memory_hierarchy.basic`：PASS
  - `expectation.pass.kernel_pattern_attach`：PASS
  - `expectation.pass.transform_apply`：PASS
- canonical / compat import smoke：8 个新 canonical module 的 class `__module__` 均指向 canonical path，9 个旧 compat path 均可 import，退出码 0，输出 `import smoke ok`。
- 旧 shim AST 门禁：9 个 compat shim 无 `FunctionDef` / `AsyncFunctionDef` / `ClassDef`，退出码 0，输出 `shim ast ok`。
- 旧 direct path 文本门禁：`rg -n "kernel_gen\\.passes\\.(arch_parallelize|attach_arch_information|kernel_aggregate|kernel_decompose|memory_plan|memory_pool|multi_buffer|outline_device_kernel)" kernel_gen/pipeline kernel_gen/passes/registry.py test/passes spec/pass kernel_gen/passes` 只命中 compat shim、compat 测试和 compat 说明；registry / pipeline 主路径未命中旧 direct import。
- 已退场 tuning 旧路径门禁：`kernel_gen.passes.dma_memory_hierarchy`、`kernel_gen.passes.kernel_pattern_attach`、`kernel_gen.passes.transform_apply` 均不可发现，退出码 0。
- `git diff --check && git diff --cached --check`：退出码 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff --cached -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 均无输出。
- private callable 扫描：`rg -n "^def _|^class _|^    def _" kernel_gen/passes/arch kernel_gen/passes/kernel kernel_gen/passes/memory kernel_gen/passes/tuning` 命中迁移文件原有 private helper / private class；本轮新增 family package root 与 compat shim 没有新增 private callable，未新增小于 5 行有效代码的 private callable。
- 非必过 / 共享 expectation 基线冲突复现：
  - `expectation.pass.pipeline.npu_demo_lowering`：exit 1，失败摘要为 actual pipeline 在第三段 `symbol-hoist-pipeline -> cse -> canonicalize` 后直接进入 `producer-consumer-analysis`，expected 额外要求 `multi-buffer:2:npu_demo` / `multi-buffer:memory_stage=2:target=npu_demo`。该失败与本目录迁移 diff 无关，按 Draft 4 口径为外部合同漂移。
  - `expectation.pass.multi_buffer`：exit 1，失败摘要为 `matmul_ring_memory_stage` 仍匹配三操作数 `"dma.make_ring"(%backing, %num, %offset)`；当前 dialect / spec / pytest 已为四操作数 `shape_bytes` 合同。该失败与本目录迁移 diff 无关，按 Draft 4 口径为外部合同漂移。
Diff 反推自测：
- 实现 / registry / pipeline / package root diff 反推：全量 `test/passes`、canonical / compat import smoke、旧 direct path 文本门禁、已退场旧路径门禁。
- spec / test 目录迁移 diff 反推：全量 `test/passes`、旧路径文本门禁、`test_pattern_public_api_docs.py` 已包含在全量测试中。
- compat shim diff 反推：旧 shim AST 门禁、compat import identity 测试、旧 direct path 文本门禁。
- 合同验收按 Draft 4 当前口径执行 10 个必过 expectation；两项共享 expectation 基线冲突单独记录，不作为本任务当前阻断。
减法检查：
- 新增 private callable：无。新增 package root 与旧路径 shim 均无私有函数 / 类。
- 改动 private callable：无算法级改写；迁移文件原有 private helper 随文件 rehome 保留。本轮恢复后未继续改动 helper。
- 被替代旧逻辑：旧 direct module 业务实现由新 canonical module 承载；旧路径只保留薄 re-export shim。
- 保留旧逻辑依据：旧 public import path 是计划明确保留的 compat shim；已退场 tuning root path 按计划不恢复。
自检：
- 接口 / 兼容：未修改 pass class 构造签名、`Pass.name`、registry pass name、pipeline name、pipeline option、错误文本或公开 API；新 canonical path 与旧 compat path 均可用。
- 边界 / 异常：已退场 tuning 旧路径保持不可 import；旧 shim 不承载业务逻辑；pipeline 顺序未改变。
- 实现遗漏 / 冗余：registry、pipeline、package root、spec、pytest、tool / DSL 路径均已同步；候选 diff 中无 `expectation/`、`.skills/`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 改动。
- 资源 / 并发 / 性能：本轮为目录、import、文档和测试路径重构，不改变 IR 生命周期、资源分配、并发模型或 pass 算法复杂度。
- 测试有效性：全量 `test/passes` 与当前 10 个必过 expectation 均通过；两项非必过失败已复现并归因到外部合同漂移，review 需复核该归因不是目录迁移 diff、import shim 或 registry 破坏造成。
结论：按 Draft 4 口径，execute 候选已收口，可流转 review。review 必须重点复核：两项非必过 expectation 失败归因不是本目录迁移候选 diff 造成；剩余 10 项 expectation、pytest、文本门禁、敏感目录门禁、canonical / compat import smoke 与旧 shim AST 门禁通过；任务 worktree 计划正文仍是 Draft 3，但本轮执行未修改计划正文并已按主仓 indexed Draft 4 口径验收。

时间：2026-06-07 12:50 +0800
经办人：睡觉小分队
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / Draft 4 计划同步确认
任务目标：按管理员补充口径核对任务 worktree 正式计划已由计划负责人同步到 Draft 4，并在不自行修改计划正文的前提下继续流转 review。
改动：
- 已收到管理员补充口径：大闸蟹确认 worktree 正式计划已由计划负责人同步；execute 不授权自行改计划书。
- 已核对任务 worktree `ARCHITECTURE/plan/pass_directory_layout_refactor.md` 为 Draft 4，`sha256=0a6e6246b98327585734dd79f0ce95ae444666713dcc75a31b11de6a84966f62`，worktree index 为 `100644 ca4fc5ebf62340487b62c478035aecb56bb598fd 0 ARCHITECTURE/plan/pass_directory_layout_refactor.md`。
- 本轮未修改计划正文，只读取 / 记录 Draft 4 口径；若后续 review 发现计划仍需改，应回报管理员转计划负责人。
验证：
- `sha256sum ARCHITECTURE/plan/pass_directory_layout_refactor.md`：输出 `0a6e6246b98327585734dd79f0ce95ae444666713dcc75a31b11de6a84966f62`。
- `git ls-files --stage -- ARCHITECTURE/plan/pass_directory_layout_refactor.md`：输出 `100644 ca4fc5ebf62340487b62c478035aecb56bb598fd 0 ARCHITECTURE/plan/pass_directory_layout_refactor.md`。
- `git diff --cached --check`：退出码 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff --cached -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 均无输出。
自检：本轮只核对和记录计划同步事实，不修改 `expectation/`、pipeline、make-ring API、实现、spec、pytest 或正式计划正文；上一条 12:48 记录中的 Draft 3 计划现场说明已被本条同步确认覆盖，当前可按 Draft 4 口径流转 review。
结论：Draft 4 同步前置已满足。execute 候选按 Draft 4 口径可流转 review；review 仍需复核两项非必过 expectation 失败归因与剩余 10 项 expectation / pytest / 文本门禁 / 敏感目录门禁 / import smoke / shim AST 门禁。

时间：2026-06-07 12:14 +0800
经办人：守护最好的爱莉希雅
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 裁定流程口径修正
任务目标：同步大闸蟹与管理员后续裁定，修正守护前一条回执中“可直接继续收口并流转 review”的流程表述。
改动：
- 技术裁定口径不变：不修改 `expectation/`，不改变 `npu-demo-lowering` pipeline 行为，不新增 `multi-buffer` pipeline 阶段 / pipeline option，不回退或前推 `dma.make_ring` / `DmaMakeRingOp` 公开合同。
- 流程口径以大闸蟹与管理员后续回执为准：当前任务继续保持暂停；不得继续实现、不得继续验收流转、不得 `-next review`。
- 最小下一步：由计划负责人修订 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`，将 `expectation.pass.pipeline.npu_demo_lowering` 与 `expectation.pass.multi_buffer` 从当前必过只读 expectation 列表移到“当前非必过 / 共享 expectation 基线冲突”记录，写明不改变 pipeline / make-ring 合同、不修改 expectation；修订后完成两路 strict review 与守护复验，再由管理员恢复 execute。
- 前一条守护记录中“允许 execute 在保留上述 2 个外部合同漂移记录的前提下继续收口并流转 review”的流程表述被本条修正覆盖，不再作为当前恢复依据。
验证：
- 已核对最新 talk.log：管理员明确 `T-20260607-3318f2e2` 当前为 `execute / 睡觉小分队 / 暂停`，在计划修订、strict review 与守护复验完成前不恢复、不流转 review。
自检：本轮只追加任务记录并将修正口径回执相关角色；未修改计划正文、功能实现、`spec`、测试、`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 或 `plan/1.md`。
结论：当前以“继续暂停，等待计划修订 + strict review + 守护复验 + 管理员恢复”为唯一流程口径。

时间：2026-06-07 12:51 +0800
经办人：睡觉小分队
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / execute 最终流转记录
任务目标：按管理员最新补充口径确认 Draft 4 已在任务 worktree 同步，并将 execute 候选流转 review。
改动：
- 已确认管理员最新回执覆盖前序暂停记录：任务已按大闸蟹 Draft 4 / 守护复验通过口径恢复 execute；worktree 正式计划已由计划负责人同步到 Draft 4。
- 当前最终计划现场为 `sha256=0a6e6246b98327585734dd79f0ce95ae444666713dcc75a31b11de6a84966f62`，index blob `ca4fc5ebf62340487b62c478035aecb56bb598fd`。
- 本 execute 未自行修改计划正文；只读取 / 记录 Draft 4 口径并按该口径收口。
验证：
- Draft 4 当前必过验收：`test/passes` 全量 `609 passed, 1 warning`；10 个必过只读 expectation 全部 PASS；canonical / compat import smoke PASS；旧 shim AST 门禁 PASS；旧 direct path 文本门禁 PASS；已退场 tuning 旧路径门禁 PASS；敏感目录门禁无输出；`git diff --cached --check` 通过。
- 非必过共享 expectation 基线冲突已复现并记录：`expectation.pass.pipeline_npu_demo_lowering` / `expectation.pass.pipeline.npu_demo_lowering` 要求新增 `multi-buffer:memory_stage=2:target=npu_demo`，`expectation.pass.multi_buffer` 仍匹配三操作数 `dma.make_ring`；两者均按 Draft 4 口径不作为当前阻断。
自检：未修改 `expectation/`，未改变 `npu-demo-lowering` pipeline，未接入 `multi-buffer`，未新增 pipeline option，未回退或前推 `dma.make_ring` / `DmaMakeRingOp` 合同；候选 diff 与记录已 staged，敏感目录无 diff。
结论：execute 候选按 Draft 4 口径收口完成，流转 review。review 必须复核两项非必过 expectation 失败不是目录迁移 diff、import shim 或 registry 破坏造成，并复核剩余 10 项 expectation、pytest、文本门禁、敏感目录门禁、canonical / compat import smoke 与旧 shim AST 门禁通过。

时间：2026-06-07 13:02 CST
经办人：提莫炖蘑菇
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / review
任务目标：审查 pass-directory-layout-refactor execute 候选，重点复核 Draft 4 口径下 10 个只读 expectation、pytest、文本门禁、敏感目录门禁、canonical / compat import smoke、旧 shim AST 门禁，以及非必过共享 expectation 失败归因。
审查结论：不通过，退回 execute。Draft 4 指定主验收与非必过 expectation 归因复核通过，但 diff 反推审查发现最小需改项。
最小需改项：
- 规格文档迁移后存在断链。对 staged diff 涉及的 `spec/pass/**` Markdown 目标做只读解析，发现 `missing_count=39`；典型位置包括 `spec/pass/kernel/kernel_aggregate.md:17`、`spec/pass/kernel/kernel_decompose.md:25`、`spec/pass/memory/memory_plan.md:21`、`spec/pass/memory/multi_buffer.md:19`、`spec/pass/tuning/dma_memory_hierarchy.md:20`、`spec/pass/tuning/kernel_pattern_attach.md:19`、`spec/pass/tuning/transform_apply.md:17`、`spec/pass/tuning/launch_kernel_cost_func.md:39`、`spec/pass/tuning/outline_device_kernel.md:38`、`spec/pass/pipeline/npu_demo_lowering.md:34`。这些链接随 spec 目录迁移后仍按旧相对层级解析，部分指向不存在的 `spec/spec/**`、`spec/pass/dialect/**`、已删除旧 root spec，或越出当前 worktree。最小修复：修正本次迁移触及 spec 文件中的断链，并运行本地链接解析检查。
- diff 反推测试 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_kernel_code_error_static_gate.py` 失败。失败摘要为 `test_production_kernel_code_error_static_gate` 命中新 canonical path：`kernel_gen/passes/kernel/kernel_aggregate.py:244`、`:286`、`:289` 的 `raise _kernel_aggregate_error`，`kernel_gen/passes/kernel/kernel_decompose.py:244` 的 `except ValueError`，`kernel_gen/passes/memory/memory_plan.py:466` 的 `except TypeError` / `except ValueError`。该测试文件在候选 diff 中被修改，且生产文件被迁移到新 canonical path 后门禁未对新路径保持等价通过。最小修复：让新 canonical 路径继续满足 KCE 静态门禁或同步门禁规则 / allowlist，并至少重跑该测试、相关工具测试与 `test/passes`。
验证：
- Draft 4 计划现场已核对：`sha256sum ARCHITECTURE/plan/pass_directory_layout_refactor.md` 输出 `0a6e6246b98327585734dd79f0ce95ae444666713dcc75a31b11de6a84966f62`；`git ls-files --stage -- ARCHITECTURE/plan/pass_directory_layout_refactor.md` 输出 index blob `ca4fc5ebf62340487b62c478035aecb56bb598fd`。
- latest main 已同步：`git fetch --prune origin` 后 `HEAD`、`origin/main`、`merge-base` 均为 `aec10c294cff71f1a2b4f05841f25db02808ff2b`，ahead / behind 为 `0 0`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes`：`609 passed, 1 warning`。
- 10 个 Draft 4 当前必过只读 expectation 全部 PASS：`expectation.pass.arch_parallelize`、`expectation.pass.attach_arch_information`、`expectation.pass.kernel_aggregate`、`expectation.pass.kernel_decompose`、`expectation.pass.memory_plan`、`expectation.pass.memory_pool`、`expectation.pass.outline_device_kernel`、`expectation.pass.dma_memory_hierarchy.basic`、`expectation.pass.kernel_pattern_attach`、`expectation.pass.transform_apply`。
- canonical / compat import smoke：8 个 canonical module 的 class `__module__` 均指向 canonical path，9 个旧 compat path 均可 import，输出 `import smoke ok`。
- 旧 shim AST 门禁：9 个 compat shim 无 `FunctionDef` / `AsyncFunctionDef` / `ClassDef`，输出 `shim ast ok`。
- 文本门禁：旧 direct import 文本只命中 compat shim、compat 测试和 compat/spec 说明，registry / pipeline 主路径未命中旧 direct import。
- 已退场 tuning 旧路径门禁：`kernel_gen.passes.dma_memory_hierarchy`、`kernel_gen.passes.kernel_pattern_attach`、`kernel_gen.passes.transform_apply` 均不可发现。
- `git diff --check && git diff --cached --check`：退出码 0。
- 敏感目录门禁：`.skills`、`expectation`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 的 status / unstaged diff / staged diff 均无输出。
- 非必过 / 共享 expectation 基线冲突复核：`expectation.pass.pipeline.npu_demo_lowering` 失败原因为 expected 要求额外 `multi-buffer:memory_stage=2:target=npu_demo` 阶段而 actual 未接入；`expectation.pass.pipeline_npu_demo_lowering` 失败原因为 legacy module 不存在；`expectation.pass.multi_buffer` 失败原因为仍匹配三操作数 `dma.make_ring`。三者均符合 Draft 4 的非必过 / 共享 expectation 基线冲突口径，不是目录迁移 diff、import shim 或 registry 破坏造成；review 不要求 execute 修改 `expectation/`、改变 npu-demo-lowering pipeline、接入 multi-buffer、新增 pipeline option 或回退 / 前推 `dma.make_ring` / `DmaMakeRingOp` 合同。
- 追加 diff 反推测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py test/passes/test_pattern_public_api_docs.py test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/pipeline/test_cuda_sm86_lowering.py`：`102 passed, 1 warning`。
- 追加 diff 反推测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py test/tools/test_dsl_cost_run.py test/tools/test_kernel_code_error_static_gate.py`：`112 passed, 1 failed, 2 warnings`，失败项为 `test/tools/test_kernel_code_error_static_gate.py::test_production_kernel_code_error_static_gate`。
- 私有 callable 边界复核：`python3 -m pytest -q test/repo_conformance/test_private_api_boundaries.py` 因迁移文件整体作为新增路径被静态门禁批量命中而失败；对 8 个旧实现文件与新 canonical 文件做 AST 去 docstring 对比，结果均为 `ast_without_docstrings_equal=True`，判断为 rehome 造成的机械性门禁暴露，不作为本轮主要算法缺陷，但 execute 后续应在记录中继续说明或同步门禁适配。
Diff 反推审查：
- 本候选同时迁移 implementation、spec、test、registry / pipeline import、compat shim 与工具测试；因此 review 在计划必过 `test/passes` 外追加了 touched pipeline / registry / docs 测试、工具 / DSL 路径测试、Markdown 链接解析、KCE 静态门禁、private API conformance 与 import / shim 门禁。
- 目录迁移本身保持业务实现 AST 等价，但 spec 链接与 KCE 静态门禁属于本次 diff 直接影响面，不能仅以计划列出的 pass 级验收替代。
减法审查：
- 旧 direct module 业务实现已由新 canonical module 承载；旧路径保留薄 re-export shim，AST 门禁确认 shim 不承载业务逻辑。
- 未发现 execute 新增 / 修改 `expectation/`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md` 或 `plan/1.md`。
- 未发现 registry / pipeline 继续依赖旧 direct import；未发现 npu-demo-lowering pipeline、多 buffer 接入、pipeline option 或 make-ring 合同被本候选改变。
自检：
- 已按 review 口径检查特殊情况、完整性、维护性、扩展性、测试有效性、非必过 expectation 归因、敏感目录和公开 API 边界。
- 本轮只追加任务记录；未修改 implementation、spec、test、expectation、计划正文或状态文件。
- 阻断项均为候选 diff 直接可修复问题，流程上应退回 execute；未要求 execute 修改计划正文或非本任务合同资产。
流转建议：使用 `-next -type execute` 退回 execute，任务目标为修复上述两项最小需改项并重跑 / 记录对应 diff 反推验收。

时间：2026-06-07 13:20 CST
经办人：小李飞刀
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / review 退回返工收口
任务目标：修复 review 13:02 退回的两项最小需改项：`spec/pass/**` Markdown 断链与新 canonical path 下 KCE 静态门禁失败；按 Draft 4 禁止面重跑并记录验收。
执行前阅读记录：
- 已按当前角色要求读取根 `AGENTS.md`、`agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、`agents/standard/任务记录约定.md`、`TODO.md` 当前 doing 状态、`ARCHITECTURE/plan/pass_directory_layout_refactor.md` Draft 4 和本记录中 13:02 review 退回项。
- 已确认同一任务重新流转到小李飞刀执行中，继续沿用本任务记录文件；不创建新任务，不修改 `expectation/`，不改变 `npu-demo-lowering` pipeline，不接入 `multi-buffer`，不新增 pipeline option，不回退或前推 `dma.make_ring` / `DmaMakeRingOp` 合同。
最新同步现场：
- 初始返工时 worktree 基线为 `aec10c294cff71f1a2b4f05841f25db02808ff2b`；收尾前发现 `origin/main` 已前进到 `ab530d8afa6ca8a70255e217bfe633b9ad51e3f0`，新增内容仅涉及 symbol memory query 任务记录、`kernel_gen/dialect/symbol/operation/memory_query.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py`，与本候选 pass 目录迁移文件无重叠。
- 已使用 `git stash push --include-untracked --message T-20260607-3318f2e2-pre-origin-main-ab530-sync`、`git merge --ff-only origin/main`、`git stash pop --index` 将本 worktree 快进到最新 main 并恢复 staged 候选；复核 `HEAD=origin/main=merge-base=ab530d8afa6ca8a70255e217bfe633b9ad51e3f0`。
改动：
- 修复 touched `spec/pass/**` Markdown 链接相对层级：`spec/pass/kernel/kernel_aggregate.md`、`spec/pass/kernel/kernel_decompose.md`、`spec/pass/memory/memory_plan.md`、`spec/pass/memory/multi_buffer.md`、`spec/pass/tuning/dma_memory_hierarchy.md`、`spec/pass/tuning/kernel_pattern_attach.md`、`spec/pass/tuning/transform_apply.md`、`spec/pass/tuning/launch_kernel_cost_func.md`、`spec/pass/tuning/outline_device_kernel.md`、`spec/pass/pipeline/npu_demo_lowering.md`。
- 修复 KCE 静态门禁：`kernel_gen/passes/kernel/kernel_aggregate.py` 的 `_kernel_aggregate_error(...) -> KernelCodeError` 改为直接返回 `KernelCodeError(...)`，使 `raise _kernel_aggregate_error(...)` 可被门禁识别；`test/tools/test_kernel_code_error_static_gate.py` 为新 canonical path 下的保守 fallback `except ValueError` / `except TypeError` 补充 allowlist，语义分别为 index lookup miss 阻止 fill 删除、auto-pad 候选构造失败跳过 unsupported rewrite。
最小功能闭环：
- Markdown 断链闭环：对 staged diff 触达的 `spec/pass/**/*.md` 解析 repo-local Markdown 链接并逐一检查目标存在，`missing_count=0`。
- KCE 门禁闭环：新 canonical production path 下 `kernel_aggregate` helper raise、`kernel_decompose` conservative `ValueError` fallback、`memory_plan` auto-pad `TypeError` / `ValueError` fallback 均被静态门禁接受，`test_kernel_code_error_static_gate.py` 全通过。
- Draft 4 行为闭环：未修改 expectation；未改变 `npu-demo-lowering` pipeline 顺序 / option；未接入 `multi-buffer`；未修改或回退 `dma.make_ring` / `DmaMakeRingOp` 合同。
验证：
- 链接解析检查：`python3 - <<'PY' ... git diff --cached --name-only --diff-filter=ACMR -- spec/pass/**/*.md ...`，结果 `checked_files=14 checked_links=108 missing_count=0`，退出码 0。
- KCE 静态门禁：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_kernel_code_error_static_gate.py`，`3 passed in 0.61s`。
- 相关工具测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py test/tools/test_kernel_code_error_static_gate.py`，`14 passed, 1 warning`。
- 相关 DSL / 工具组合测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py test/tools/test_dsl_cost_run.py test/tools/test_kernel_code_error_static_gate.py`，`113 passed, 2 warnings`。
- pass 全量测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes`，`609 passed, 1 warning`。
- 当前必过 10 个只读 expectation：在 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate` 下运行 `expectation.pass.arch_parallelize`、`expectation.pass.attach_arch_information`、`expectation.pass.kernel_aggregate`、`expectation.pass.kernel_decompose`、`expectation.pass.memory_plan`、`expectation.pass.memory_pool`、`expectation.pass.outline_device_kernel`、`expectation.pass.dma_memory_hierarchy.basic`、`expectation.pass.kernel_pattern_attach`、`expectation.pass.transform_apply`，全部 PASS。
- import smoke：8 个新 canonical module 的公开 class `__module__` 均指向 canonical path，9 个旧 compat path 均导出同一公开对象，输出 `import smoke ok`，退出码 0。
- shim AST：9 个 compat shim 无 `FunctionDef` / `AsyncFunctionDef` / `ClassDef`，输出 `shim ast ok`，退出码 0。
- 文本门禁：旧 direct import 文本在 `kernel_gen/pipeline` 与 `kernel_gen/passes/registry.py` 中命中 0；全域允许命中 41 条，均为 compat shim、compat 测试或 compat/spec 说明。
- 已退场 tuning 旧路径门禁：`kernel_gen.passes.dma_memory_hierarchy`、`kernel_gen.passes.kernel_pattern_attach`、`kernel_gen.passes.transform_apply` 均不可发现，输出 `retired path gate ok`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/kernel/kernel_aggregate.py test/tools/test_kernel_code_error_static_gate.py`：退出码 0。
- `git diff --check && git diff --cached --check`：退出码 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff --cached -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 均无输出。
- 私有 callable 只读扫描：`rg -n "^def _|^class _|^    def _" kernel_gen/passes/arch kernel_gen/passes/kernel kernel_gen/passes/memory kernel_gen/passes/tuning` 命中迁移文件原有 private helper / class；本轮返工未新增 private callable，也未新增跨文件私有 API 调用。13:02 review 已记录 `private_api_boundaries` 因整文件 rehome 机械暴露既有 helper 失败，本轮未扩大该面。
Diff 反推自测：
- `spec/pass/**` 链接修复反推：运行 staged touched spec Markdown 链接解析检查，覆盖本轮所有修复链接，结果 `missing_count=0`。
- KCE 修复反推：运行 KCE 静态门禁、工具测试、DSL / 工具组合测试和 `py_compile`，覆盖 `_kernel_aggregate_error` 直接返回、allowlist 新 canonical path 和相关生产路径。
- pass 目录迁移候选回归反推：运行全量 `test/passes`、import smoke、shim AST、旧 direct path 文本门禁、已退场 tuning 旧路径门禁，确认目录重构候选未回退。
- 合同验收不计入 diff 反推测试；已按 Draft 4 跑 10 个当前必过 expectation，全部 PASS。
减法检查：
- 新增 / 改动 private callable：本轮未新增 private callable；`_kernel_aggregate_error` 仅去掉临时变量，直接返回同一个 `KernelCodeError` 构造结果。
- 被替代旧逻辑：旧 direct module 业务实现仍由新 canonical module 承载，旧路径仍为薄 re-export shim；本轮没有恢复旧 root tuning path，也没有复制业务逻辑进 shim。
- 保留旧逻辑依据：13:02 review 要求修复断链与 KCE 门禁；本轮没有对 pass 算法、pipeline、make-ring 合同或 expectation 做行为改写。
自检：
- 接口：未新增、删除、重命名或修改公开 API；未修改 pass class 构造签名、registry pass name、pipeline name、pipeline option、返回值或稳定错误语义。
- 边界 / 异常：KCE 门禁用已注解返回 `KernelCodeError` 的 helper 与明确 allowlist 表达保守 fallback；没有使用 `hasattr/getattr/callable(getattr(...))` 上下文能力探测。
- 兼容：canonical import 与 compat import 均通过；已退场 tuning 旧路径仍不可 import；registry / pipeline 主路径无旧 direct import 命中。
- 实现遗漏 / 冗余：review 两项最小需改项均有直接修复和验收；未新增无关 refactor。
- 注释 / 规范：本轮未修改功能实现文件公开 API 列表结构；KCE helper 注释与语义保持一致，Markdown 文档链接已按新层级修正。
- 复用 / 函数粒度：未新增嵌套函数、未新增跨文件私有 API 调用、未新增小 helper。
- 输入输出 / 资源 / 并发 / 性能：本轮仅调整文档链接和静态门禁可识别形态，不改变 pass 输入输出、资源分配、并发模型或复杂度。
- 测试有效性：链接解析、KCE 静态门禁、工具 / DSL、全量 pass 测试、10 个 expectation、import smoke、shim AST、文本门禁、敏感目录门禁均在最新 `origin/main=ab530d8a` 基线上通过。
结论：review 退回的两项最小需改项已收口；Draft 4 禁止面保持不变；候选 diff 与本记录已 staged，可使用 `-next -type review` 流转复审。

时间：2026-06-07 13:25 CST
经办人：小李飞刀
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 流转后主线前进补充记录
任务目标：记录 execute 已流转 review 后发现 `origin/main` 再次前进且与当前候选存在文件重叠的流程事实。
改动：
- 已执行 `-next -type review`，任务已指派给 `提莫炖蘑菇` review，脚本自动回报 `神秘人`。
- `-next` 后最终只读复核发现 `origin/main` 从本轮验收基线 `ab530d8afa6ca8a70255e217bfe633b9ad51e3f0` 前进到 `81d753329a66ed338b846785622407f4a3e0554d`（`Merge context-first kernel cost shared code`）。
- 新主线提交触碰当前候选相关文件，包括 `kernel_gen/passes/registry.py`、`kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`spec/pass/registry.md`、`spec/pass/tuning/launch_kernel_cost_func.md`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/passes/test_registry.py`、`test/passes/tuning/test_launch_kernel_cost_func.py`、`test/tools/test_dsl_cost_run.py`。
- 当前任务状态已是 `review / 提莫炖蘑菇 / 进行中`，本角色未在 review 状态下擅自继续修改实现候选或重放主线。
验证：
- `git log --oneline HEAD..origin/main`：`81d75332 Merge context-first kernel cost shared code`。
- `git diff --name-only HEAD..origin/main`：确认存在上述重叠路径。
- 已用 `codex-multi-agents-tmux.sh -talk` 向 `神秘人` 发起确认，并二次追问明确回复：A=退回 execute 给小李飞刀重放 `81d75332` 并重跑验收；B=保持 review，由 reviewer 处理最新 main 同步 / 退回判断；C=其它安排。
- 已用 `codex-multi-agents-tmux.sh -talk` 同步当前 reviewer `提莫炖蘑菇`，提示返工验收基线为 `ab530d8a`，后续主线 `81d75332` 有重叠。
自检：本补充记录只追加流程事实，不修改 `expectation/`、pipeline、make-ring 合同、实现、spec、pytest 或 TODO 状态；不替管理员和 reviewer 作流程裁定。
结论：execute 返工已完成并流转 review；主线前进重叠已回报管理员和 reviewer，等待管理员 A/B/C 明确回复或 reviewer 按 review 阶段处理。

时间：2026-06-07 13:23 CST
经办人：提莫炖蘑菇
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 复审前置核对
任务目标：复审 pass-directory-layout-refactor review 退回返工候选，先核对最新主线、被审 diff、执行返工记录与覆盖风险。
审查结论：最小需改项，退回 execute。小李飞刀在 `ab530d8afa6ca8a70255e217bfe633b9ad51e3f0` 基线上的两项返工记录完整，但复审前置核对发现 `origin/main` 已前进到 `81d753329a66ed338b846785622407f4a3e0554d`，且最新主线触碰当前候选同名文件，review 不能基于旧基线继续给通过结论。
新增问题 / 范围扩大：
- 问题：当前候选 worktree `HEAD=ab530d8afa6ca8a70255e217bfe633b9ad51e3f0`，`origin/main=81d753329a66ed338b846785622407f4a3e0554d`，`merge-base=HEAD`，ahead / behind 为 `0 1`；最新主线提交 `81d75332 Merge context-first kernel cost shared code` 与当前 staged diff 重叠 `kernel_gen/passes/registry.py`、`kernel_gen/passes/tuning/__init__.py`、`spec/pass/registry.md`、`spec/pass/tuning/launch_kernel_cost_func.md`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/passes/test_registry.py`、`test/passes/tuning/test_launch_kernel_cost_func.py`、`test/tools/test_dsl_cost_run.py`；其中最新主线删除了 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`spec/pass/tuning/launch_kernel_cost_func.md`、`test/passes/tuning/test_launch_kernel_cost_func.py`，而当前候选仍在修改相关迁移后的路径 / 测试。
- 影响：execute 的验收结果是在 `ab530d8a` 基线上产生，不能证明候选与最新主线 `81d75332` 合并后的 registry、tuning pass、spec 链接、pipeline 测试和工具测试仍一致；review 若继续放行会掩盖覆盖 / 回退最新主线改动的风险。
- 最小返工动作：execute 将候选同步 / 重放到最新 `origin/main=81d753329a66ed338b846785622407f4a3e0554d`，解决上述重叠文件；特别核对 `launch_kernel_cost_func` 在最新主线已删除后的计划边界，若发现 Draft 4 计划仍需调整，应回报管理员转计划负责人，不得由 execute 自行改计划正文。
- 验收方式：在最新主线基线上重新记录 `HEAD=origin/main=merge-base` 或明确 ahead / behind 状态，重跑并记录 Markdown 链接解析、KCE 静态门禁、相关工具 / DSL 测试、`test/passes`、10 个 Draft 4 当前必过 expectation、canonical / compat import smoke、shim AST、旧路径文本门禁、已退场路径门禁、敏感目录门禁和 `git diff --check && git diff --cached --check`。
验证：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -status -doing`：确认 `T-20260607-3318f2e2` 当前为 `review / 提莫炖蘑菇 / 进行中`，worktree、计划书和记录文件与任务下发一致。
- `git fetch --prune origin && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：输出 `HEAD=ab530d8afa6ca8a70255e217bfe633b9ad51e3f0`、`origin/main=81d753329a66ed338b846785622407f4a3e0554d`、`merge-base=ab530d8afa6ca8a70255e217bfe633b9ad51e3f0`、ahead / behind `0 1`。
- `sha256sum ARCHITECTURE/plan/pass_directory_layout_refactor.md`：仍为 Draft 4 `0a6e6246b98327585734dd79f0ce95ae444666713dcc75a31b11de6a84966f62`；`git ls-files --stage -- ARCHITECTURE/plan/pass_directory_layout_refactor.md`：index blob `ca4fc5ebf62340487b62c478035aecb56bb598fd`。
- `comm -12 <(git diff --cached --name-only | sort) <(git diff --name-only HEAD..origin/main | sort)`：确认 9 个重叠路径，详见上方问题列表。
- `git diff --name-status HEAD..origin/main -- <重叠路径>`：确认最新主线对同名文件有 `M` 与 `D`，包括删除 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`spec/pass/tuning/launch_kernel_cost_func.md`、`test/passes/tuning/test_launch_kernel_cost_func.py`。
- 未继续复跑 pytest / expectation：原因是复审前置基线已不满足，且最新主线与候选存在同文件覆盖风险；在旧基线复跑不能证明最新主线合入后的行为，继续执行会产生误导性通过记录。
Diff 反推审查：
- 已读取当前 staged diff 文件列表与返工记录，确认本轮候选涉及 implementation rehome、spec/test 迁移、registry / pipeline import、compat shim、KCE 门禁和任务记录。
- 因最新主线同名文件重叠，diff 反推测试必须由 execute 在同步 `81d75332` 后重跑；review 本轮只记录基线风险，不替 execute 手动同步或改候选。
减法审查：
- 本轮复审前置核对未发现新的 `expectation/`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md` 或 `plan/1.md` 候选改动。
- 小李飞刀记录中的返工未新增 private callable，`_kernel_aggregate_error` 仅保持返回 `KernelCodeError`；但最新主线删除 / 修改了与候选相关旧路径，旧逻辑删除和保留依据需在 execute 重放后重新核对。
自检：
- 已按 review 前置要求同步 / 核对最新主线，并在发现覆盖风险后停止旧基线验收，避免给出不可靠通过结论。
- 本轮只追加任务记录；未修改业务实现、spec、测试、expectation、计划正文或任务状态文件。
- 该阻断为复审中新出现的主线基线问题，最小动作明确且由 execute 收口；不要求 execute 修改 `expectation/`、改变 npu-demo-lowering pipeline、接入 multi-buffer、新增 pipeline option 或回退 / 前推 `dma.make_ring` / `DmaMakeRingOp` 合同。
结论：退回 execute，先同步最新 `origin/main=81d753329a66ed338b846785622407f4a3e0554d` 并解决同名文件覆盖风险后再流转 review。

时间：2026-06-07 13:30 +0800
经办人：金铲铲大作战
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 最新主线重放与计划冲突阻塞记录
任务目标：按复审退回要求把候选同步 / 重放到最新 `origin/main=81d753329a66ed338b846785622407f4a3e0554d`，解决同名文件覆盖风险；若发现 Draft 4 计划需改，回报管理员转计划负责人，不自行修改计划正文。
执行前阅读记录：
- 已读根 `AGENTS.md`、`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`、`agents/standard/任务记录约定.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/expectation任务规则.md`。
- 已读正式计划 `ARCHITECTURE/plan/pass_directory_layout_refactor.md` Draft 4、本任务记录、当前 `TODO.md` 与提莫炖蘑菇 13:23 复审前置退回记录。
- 已核对禁止面：不修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`；若 Draft 4 计划需改，只回报管理员转计划负责人。
改动：
- 已把当前 staged 候选用 `git stash push --include-untracked -m "T-20260607-3318f2e2 before replay onto origin-main-81d75332"` 保存为可恢复快照，然后将任务分支从 `ab530d8afa6ca8a70255e217bfe633b9ad51e3f0` 快进到 `origin/main=81d753329a66ed338b846785622407f4a3e0554d`。
- 第一次 `git stash apply --index` 因重叠文件失败且未改工作树；随后 `git stash apply` 进入冲突状态，并已解决冲突：
  - `kernel_gen/passes/tuning/__init__.py`：保留最新主线删除 `LaunchKernelCostFuncPass` 的事实，同时保留本计划目录重构新增的 `outline_device_kernel` canonical 导出。
  - `test/tools/test_dsl_cost_run.py`：保留最新主线 “`LaunchKernelCostFuncPass` 下线后命名 pipeline 缺 cost sibling 稳定失败” 的测试语义，只把 `AttachArchInformationPass` import 收口到新 canonical path。
  - `spec/pass/tuning/launch_kernel_cost_func.md`、`test/passes/tuning/test_launch_kernel_cost_func.py`：按最新主线删除处理，未恢复已退场 spec/test；`kernel_gen/passes/tuning/launch_kernel_cost_func.py` 也仍不存在。
- 同步后发现 Draft 4 正文仍把已删除的 `launch_kernel_cost_func` 实现 / spec / test 列为目标范围和 API 清单，具体命中 `ARCHITECTURE/plan/pass_directory_layout_refactor.md:22`、`:64`、`:100`、`:277`、`:280`、`:314`、`:331`、`:348`、`:417-419`。该冲突属于计划正文与最新主线事实不一致；execute 无权自行修改计划正文。
验证：
- `git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main`：均为 `81d753329a66ed338b846785622407f4a3e0554d`，确认任务分支已对齐最新主线。
- `git status --short --branch --untracked-files=all`：无 unmerged paths；候选 diff 已恢复为 staged 状态。
- `git diff --check && git diff --cached --check`：退出码 0，确认冲突解决后无 whitespace / conflict-marker diff check 问题。
- `git ls-files --stage -- kernel_gen/passes/tuning/launch_kernel_cost_func.py spec/pass/tuning/launch_kernel_cost_func.md test/passes/tuning/test_launch_kernel_cost_func.py`：无输出，确认最新主线删除的实现 / spec / test 未被本轮恢复。
- `rg -n "launch_kernel_cost_func|LaunchKernelCostFuncPass|launch-kernel-cost-func" kernel_gen spec test ARCHITECTURE/plan/pass_directory_layout_refactor.md`：实现 / spec / test 侧只剩最新主线下线语义与旧名称失败测试；正式计划正文仍命中已删除目标范围，详见上方 line 证据。
- 未继续运行链接解析、KCE 静态门禁、工具 / DSL、`test/passes`、10 个 expectation、import smoke、shim AST、旧路径文本门禁、已退场路径门禁和敏感目录门禁：原因是同步后已发现 Draft 4 主目标范围仍引用 latest main 已删除文件；按任务要求需先回报管理员转计划负责人，不应在计划正文冲突未裁定时制造可流转验收记录。
最小功能闭环：
- 最新主线对齐与冲突解决已完成，候选不再覆盖恢复 `launch_kernel_cost_func` 已删除文件。
- 当前最小阻塞不是实现冲突，而是 Draft 4 计划正文仍要求 / 描述已删除资产；需计划负责人修订或明确该引用在本任务中如何处理后，execute 才能完整跑验收并 `-next review`。
Diff 反推自测：
- 已执行同步冲突后的 `git diff --check && git diff --cached --check`、删除路径 `git ls-files` 核对、旧 pass 文本扫描。
- 完整 diff 反推 pytest / expectation 暂缓，原因同上：计划目标范围与最新主线删除事实冲突，继续跑完整验收不能解决计划真源不一致。
减法检查：
- 新增 / 改动 private callable：本轮冲突解决没有新增或改动 private callable。
- 被替代旧逻辑：没有恢复 `LaunchKernelCostFuncPass`、其 spec 或 pytest；`tuning/__init__.py` 保留主线删除成本 pass 后的公开导出集合，并加入目录重构需要的 `outline_device_kernel` canonical 导出。
- 保留旧逻辑依据：旧 public compat shim 与目录重构候选仍按 Draft 4 既有口径保留；已退场 `launch_kernel_cost_func` 按 latest main 不恢复。
自检：
- 接口 / 公开 API：未新增未确认公开 API，未回退或前推 `dma.make_ring` / `DmaMakeRingOp`，未改变 `npu-demo-lowering` pipeline，未接入 `multi-buffer`，未新增 pipeline option。
- 边界 / 兼容：同步后没有 unmerged paths，没有恢复 latest main 删除的 `launch_kernel_cost_func` 实现 / spec / test。
- 实现遗漏 / 冗余：当前仍需计划负责人处理 Draft 4 stale 目标范围；execute 不越权修改正式计划正文。
- 注释 / 复用 / 函数粒度：本轮只做冲突收口，没有新增嵌套函数、跨文件私有 API 调用或小于 5 行 private callable。
- 测试有效性：已执行能证明同步冲突解决和删除文件未恢复的静态核对；完整验收需等待计划口径明确后再运行。
结论：候选已同步到最新 `origin/main=81d753329a66ed338b846785622407f4a3e0554d` 并解决冲突，但 Draft 4 仍列已删除 `launch_kernel_cost_func` 资产，属于任务明确要求回报管理员转计划负责人的计划正文冲突。当前不修改计划、不修改 `expectation/`、不 `-next review`，等待管理员 / 计划负责人明确下一步。

时间：2026-06-07 15:11 +0800
经办人：金铲铲大作战
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / Draft 5-R1 恢复 execute 收口
任务目标：按管理员恢复口径，以 Draft 5-R1 为真源在最新 `origin/main=374b1074ad7a84c70d1288515b8f49b4b847718d` 基线上继续 execute，确保不恢复已删除 `launch_kernel_cost_func` 资产，完成 pytest、10 项 expectation、文本门禁、敏感目录门禁、canonical / compat import smoke、旧 shim AST、Diff 反推自测、自检和减法检查，并流转 review。
执行前阅读记录：
- 已重新读取根 `AGENTS.md`、`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`、`agents/standard/任务记录约定.md`、`TODO.md` 当前 doing 状态、本任务记录、管理员 Draft 5-R1 恢复回执和 `ARCHITECTURE/plan/pass_directory_layout_refactor.md` 当前正文。
- 已核对 Draft 5-R1 计划真源：`sha256=5350d49c6d6affbca1dcd8618b89cbb9cd349a7a0fe9d3f37b86fa35fa4549bd`；本轮不授权 execute 自行修改计划正文。
- 已核对禁止面：不修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`；不恢复 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`spec/pass/tuning/launch_kernel_cost_func.md`、`test/passes/tuning/test_launch_kernel_cost_func.py`；不在 `kernel_gen/passes/tuning/__init__.py` 重新导出 `LaunchKernelCostFuncPass`；registry / docs / pytest 不重新要求该 pass；不改变 latest main 已有 `npu-demo-lowering` 行为、不新增 pipeline option、不改 `dma.make_ring` / `DmaMakeRingOp` 合同、不修改 expectation。
最新同步现场：
- 任务 worktree 已对齐最新主线：`HEAD=origin/main=merge-base=374b1074ad7a84c70d1288515b8f49b4b847718d`，ahead / behind 为 `0 0`。
- 已将此前候选重放到 `374b1074`，解决与 latest main 的 `multi_buffer.py`、`npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py` 冲突；冲突解决策略为保留 latest main 行为，只把 pass 目录迁移候选接到 canonical path。
改动：
- 保持 Draft 5-R1 pass 目录重构：新增 canonical families `kernel_gen/passes/arch`、`kernel_gen/passes/kernel`、`kernel_gen/passes/memory`、`kernel_gen/passes/tuning/outline_device_kernel.py`，旧 public import path 保留为薄 compat shim；对应 `spec/pass/**` 与 `test/passes/**` 迁移到同族目录。
- 保留 latest main 的 multi-buffer 行为：`MultiBufferPass` 默认 `memory_stage=2`、保留 `DmaMakeRingOp.shape_bytes` 当前主线合同；`kernel_gen/passes/memory/multi_buffer.py` 承载真实实现，`kernel_gen/passes/multi_buffer.py` 仅 re-export；`npu-demo-lowering` 仅 canonical import 化，保留 latest main 既有 `MultiBufferPass(memory_stage=2, target=target)` 位置和 pipeline 行为，没有新增 pipeline option。
- 保持 `launch_kernel_cost_func` 下线：未恢复实现 / spec / test 三个已删除文件，未在 tuning package 重新导出 `LaunchKernelCostFuncPass`，registry / pipeline / pipeline test 不再要求该 pass。
- 修复 private callable conformance 对 directory rehome 的误判：`test/repo_conformance/test_private_api_boundaries.py` 对 copy / rename 目标使用 HEAD 源文件对比计算 changed lines，并排除 docstring / 空白 / 纯括号逗号行，只对真实变更的有效代码行施加五行与私有调用链规则。
- 收口 private callable 门禁新增暴露：`test/passes/arch/test_arch_parallelize.py` 内联此前小于 5 行的路径 helper，避免迁移后因 rename 误判或短 helper 命中。
最小功能闭环：
- canonical 入口闭环：8 个 canonical pass module 的公开 class `__module__` 指向 canonical path，9 个 compat path 可 import 同一公开对象，旧 shim AST 不承载业务 `FunctionDef` / `AsyncFunctionDef` / `ClassDef`。
- latest main 边界闭环：`launch_kernel_cost_func` 三个已删除资产仍不存在，`LaunchKernelCostFuncPass` 没有被 package / registry / pipeline 重新引用。
- private API 闭环：copy / rename rehome 不再把整文件既有 private helper 当作本轮新增；真实新增 / 改动 helper 仍接受 `test/repo_conformance/test_private_api_boundaries.py` 扫描。
- Draft 5-R1 合同闭环：10 个当前必过 expectation 全部 PASS；`expectation.pass.pipeline.npu_demo_lowering` 与 `expectation.pass.multi_buffer` 仍按恢复回执为非必过 / 共享 expectation 基线冲突，未执行为当前阻断。
验证：
- 主线与计划真源：`git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main && sha256sum ARCHITECTURE/plan/pass_directory_layout_refactor.md` 输出 `HEAD=origin/main=merge-base=374b1074ad7a84c70d1288515b8f49b4b847718d`、ahead / behind `0 0`、计划 sha `5350d49c6d6affbca1dcd8618b89cbb9cd349a7a0fe9d3f37b86fa35fa4549bd`，退出码 0。
- pass 全量测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes`，`589 passed, 1 warning`，退出码 0。
- 工具 / DSL / private API 组合测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py test/tools/test_dsl_cost_run.py test/tools/test_kernel_code_error_static_gate.py test/repo_conformance/test_private_api_boundaries.py`，`111 passed, 2 warnings`，退出码 0。
- 当前必过 10 项 expectation：在 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate` 与 `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor` 下运行 `expectation.pass.arch_parallelize`、`expectation.pass.attach_arch_information`、`expectation.pass.kernel_aggregate`、`expectation.pass.kernel_decompose`、`expectation.pass.memory_plan`、`expectation.pass.memory_pool`、`expectation.pass.outline_device_kernel`、`expectation.pass.dma_memory_hierarchy.basic`、`expectation.pass.kernel_pattern_attach`、`expectation.pass.transform_apply`，全部退出码 0。
- Markdown 链接解析：对 staged touched `spec/pass/**/*.md` 解析 repo-local 链接，输出 `checked_files=15 checked_links=110 missing_count=0`，退出码 0。
- canonical / compat import smoke、旧 shim AST、已退场路径门禁：本地 Python 脚本输出 `import smoke ok`、`shim ast ok`、`retired paths absent`，退出码 0。
- `launch_kernel_cost_func` 已退场门禁：`test ! -e` 三个已删除文件，并扫描 `kernel_gen/passes/tuning/__init__.py`、`kernel_gen/passes/registry.py`、`kernel_gen/pipeline`、`test/passes/pipeline/test_npu_demo_lowering.py` 中无 `LaunchKernelCostFuncPass` / `launch_kernel_cost_func` 重新导入，输出 `launch_kernel_cost_func retired gate ok`，退出码 0。
- 旧路径文本门禁：registry / pipeline 无旧 direct import 命中；全域 legacy text 允许命中 `allowed_hits=41`，均为 compat shim、compat 测试或 compat/spec 说明类命中，退出码 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff --cached -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 均无输出。
- whitespace / conflict-marker 门禁：`git diff --check && git diff --cached --check` 退出码 0。
Diff 反推自测：
- implementation rehome 与 compat shim：反推 `pytest -q test/passes`、canonical / compat import smoke、旧 shim AST、已退场路径门禁，验证 pass 迁移后公开入口、registry / pipeline 调用和旧 compat path 行为。
- spec 迁移：反推 staged `spec/pass/**/*.md` Markdown link parser，验证目录层级调整后无断链。
- test / tool 更新：反推 `test/dsl/gen_kernel/test_gen_kernel.py`、`test/tools/test_dsl_cost_run.py`、`test/tools/test_kernel_code_error_static_gate.py`、`test/repo_conformance/test_private_api_boundaries.py` 组合 pytest，验证工具链、KCE 静态门禁和 private API 门禁在 latest main 重放后仍通过。
- registry / pipeline 变更：反推 `test/passes` 全量覆盖 `test/passes/test_registry.py`、pipeline tests、pass manager 和迁移后各 family 测试；同时用文本门禁确认 registry / pipeline 不依赖旧 direct import。
- 合同验收单列：10 项 expectation 全部 PASS；expectation 不计入 Diff 反推测试，不修改 expectation。
减法检查：
- 新增 / 改动 private helper 清单：`test/repo_conformance/test_private_api_boundaries.py` 中 `_PrivateApiBoundaryHelpers.current_diff_copy_sources(...)`、`changed_lines_between_texts(...)`、`function_effective_line_numbers(...)` 为本轮新增 helper，均超过 5 行有效代码；`changed_lines_for_path(...)`、`changed_private_callables(...)` 为本轮改动 helper。上述 helper 均位于当前文件内，不跨文件调用非公开 API，也不调用单下划线 private callable。
- 被替代旧逻辑：`changed_lines_for_path(...)` 原先对 copied / renamed Python 文件按整文件新增处理，导致 directory rehome 暴露既有 private helper；现改为以 git copy / rename source 为基准，只检查真实 changed effective lines。
- 删除 / 未删除处理：已内联删除 `test/passes/arch/test_arch_parallelize.py` 中小于 5 行路径 helper；未删除 old public compat shim，因为 Draft 5-R1 要求保留兼容 import path；未恢复 latest main 删除的 `launch_kernel_cost_func` 三个文件，删除路径门禁已通过。
- 保留旧逻辑依据：`npu-demo-lowering` latest main 已有 multi-buffer 阶段由其它任务合入，本轮只 canonical import 化，不改变 pipeline 行为；`DmaMakeRingOp.shape_bytes` 与 make-ring 当前主线合同不在本计划可改范围，保持不动。
自检：
- 接口 / 公开 API：未新增未确认公开 API；公开迁移入口、compat shim、registry / spec 路径按 Draft 5-R1 范围收口；未重新引入 `LaunchKernelCostFuncPass`；未修改 `dma.make_ring` / `DmaMakeRingOp` 合同。
- 边界 / 异常 / 兼容：保留 latest main pipeline 行为；canonical import 和 compat import 均通过；已退场 old root tuning paths 与 `launch_kernel_cost_func` 仍不可用；无 `hasattr/getattr/callable(getattr(...))` 上下文能力探测新增。
- 实现遗漏 / 冗余：review 指出的最新主线覆盖风险已通过重放到 `374b1074` 解决；Draft 5-R1 删除了 stale launch-kernel-cost-func 要求，本轮未自行改计划正文；未发现未收口冲突或未 staged 业务修改。
- 注释 / 复用 / 函数粒度：功能实现文件保留文件级说明和 API 列表；新增 conformance helper 服务同一测试文件内门禁逻辑，函数粒度独立且可测；未新增嵌套函数。
- 输入输出 / 资源 / 并发 / 性能：目录迁移、import shim 和静态门禁调整不改变 pass 输入输出、资源生命周期、并发模型或算法复杂度；private API diff 计算仅在 repo conformance pytest 中运行。
- 测试有效性：`test/passes`、工具 / DSL / private API 组合 pytest、10 项 expectation、链接解析、import smoke、shim AST、文本门禁、敏感目录门禁和 diff check 均在 `HEAD=origin/main=374b1074` 基线上通过，能覆盖本轮实际 diff。
结论：Draft 5-R1 execute 已在最新主线基线收口；禁止面保持不变，`expectation/` 与敏感目录无 diff，`launch_kernel_cost_func` 未恢复。候选 diff 与本记录可流转 review；下一阶段按计划级链路进入 `review`，不得直接 archive_acceptance 或 merge。

时间：2026-06-07 15:23 +0800
经办人：不要啊教练
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / Draft 5-R1 review 复审
结论：最小需改项，不通过；退回 execute。不得进入 archive_acceptance 或 merge。

发现：
- 阻断 `kernel_gen/passes/memory/__init__.py:15` 与 `kernel_gen/passes/memory/__init__.py:21`：新增 memory family package root 的文件级 `API 列表` 和使用示例仍写 `MultiBufferPass(memory_stage: int = 3, ...)` / `MultiBufferPass(memory_stage=3)`；但当前 canonical 实现 `kernel_gen/passes/memory/multi_buffer.py:10`、构造签名 `kernel_gen/passes/memory/multi_buffer.py:536`、`spec/pass/memory/multi_buffer.md:13`、pipeline spec 与 pytest 均已收口为默认 `memory_stage=2`。影响：计划目标点名的 latest main `multi-buffer` 行为与 spec/API 列表一致性未闭环，旧默认值会作为公开索引误导 root package caller，也违反实现文件规范中 `API 列表` 必须反映真实公开 API 的要求。最小返工动作：只修改 `kernel_gen/passes/memory/__init__.py`，把 line 15 的默认值和 line 21 示例从 `3` 改为 `2`，不改 pipeline 行为、不改 expectation、不扩大 diff。验收方式：重跑 `rg -n "memory_stage: int = 3|MultiBufferPass\\(memory_stage=3" kernel_gen/passes kernel_gen/pipeline spec/pass test/passes` 应无 active 命中；同时重跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py -x`、`git diff --check && git diff --cached --check`，并补记 Diff 反推自测。

审查范围：
- worktree：`/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`
- 被审 diff：staged diff，`git diff --cached --name-status` 共 67 个路径，覆盖 pass family canonical rehome、旧 public compat shim、spec/test 目录迁移、pipeline canonical import、registry docs/tests、private API boundary conformance 调整和任务记录。
- 计划书：`ARCHITECTURE/plan/pass_directory_layout_refactor.md`，`sha256=5350d49c6d6affbca1dcd8618b89cbb9cd349a7a0fe9d3f37b86fa35fa4549bd`，index blob `7e364fb2575c621e9121d78f69adb508ed55e330`。
- 禁止面：未修改 `.skills/`、`expectation/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`；未手工改任务状态；未直接 archive_acceptance / merge。

最新同步现场：
- `git fetch --prune origin && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：`HEAD=origin/main=merge-base=374b1074ad7a84c70d1288515b8f49b4b847718d`，ahead / behind `0 0`。
- 基线满足任务目标中 `latest origin/main=374b1074ad7a84c70d1288515b8f49b4b847718d` 的重放要求；未发现本轮覆盖风险。

执行记录核对：
- 执行记录包含执行前阅读、最新同步现场、最小功能闭环、验证、Diff 反推自测、减法检查、自检和结论。
- 执行记录声明的 `test/passes` 589、工具 / DSL / private API 111、10 项 expectation、链接解析、import smoke、shim AST、launch-kernel-cost-func 退役、文本门禁、敏感目录和 diff check 均有记录；本次 review 已复跑关键命令。
- 记录遗漏 / 未发现点：没有捕获新增 `kernel_gen/passes/memory/__init__.py` 中 `MultiBufferPass(memory_stage=3)` 旧默认残留，因此本轮不能通过。

验证：
- `git diff --check && git diff --cached --check`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes -x`：`589 passed, 1 warning`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py test/tools/test_dsl_cost_run.py test/tools/test_kernel_code_error_static_gate.py test/repo_conformance/test_private_api_boundaries.py -x`：`111 passed, 2 warnings`，退出码 0。
- 10 项 expectation：在 worktree-first `PYTHONPATH` 与 `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor` 下运行 `expectation.pass.arch_parallelize`、`expectation.pass.attach_arch_information`、`expectation.pass.kernel_aggregate`、`expectation.pass.kernel_decompose`、`expectation.pass.memory_plan`、`expectation.pass.memory_pool`、`expectation.pass.outline_device_kernel`、`expectation.pass.dma_memory_hierarchy.basic`、`expectation.pass.kernel_pattern_attach`、`expectation.pass.transform_apply`，全部退出码 0。
- Markdown 链接解析：staged touched markdown `checked_files=17 checked_links=110 missing_count=0`，退出码 0。
- canonical / compat import smoke：9 组 compat shim 与 canonical module 公开对象一致，输出 `compat shim smoke ok`，退出码 0。
- `launch_kernel_cost_func` 退役门禁：三个已删除文件均不存在；`kernel_gen/passes/tuning/__init__.py`、`kernel_gen/passes/registry.py`、`kernel_gen/pipeline`、`test/passes/pipeline/test_npu_demo_lowering.py` 无 `LaunchKernelCostFuncPass` / `launch_kernel_cost_func` / `launch-kernel-cost-func` 重新导入或要求，退出码 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- ...`、`git diff --cached -- ...` 均无输出。
- 旧默认值文本门禁：`rg -n "memory_stage: int = 3|MultiBufferPass\\(memory_stage=3"` 命中 active 文件 `kernel_gen/passes/memory/__init__.py:15`、`:21`；历史任务记录命中只作历史引用，不作为本轮 active diff 阻断来源。

Diff 反推审查：
- pass 目录 rehome / compat shim：用 `test/passes`、registry / pipeline tests、canonical / compat import smoke、退役路径门禁反推覆盖，确认旧 public path 为薄 shim，canonical import 已进入 registry / pipeline，且未恢复 `LaunchKernelCostFuncPass`。
- spec/test 目录迁移：用 Markdown link parser 覆盖 repo-local 链接；未发现断链。
- private API boundary / tools / KCE：用组合 pytest 覆盖 `test/repo_conformance/test_private_api_boundaries.py`、`test/tools/test_dsl_cost_run.py`、`test/tools/test_kernel_code_error_static_gate.py`、`test/dsl/gen_kernel/test_gen_kernel.py` 的实际 diff。
- multi-buffer latest main 行为：实现、spec、pipeline 和 pipeline test 均锁定 `MultiBufferPass(memory_stage=2, target=<pipeline target>)`，pipeline 行为未因 canonical rehome 改变；但 memory package root API 列表残留 `3`，形成当前唯一阻断。
- expectation 单列合同验收：10 项必过 expectation 全部通过；未运行非必过 pipeline / multi-buffer expectation；未修改 expectation。

减法审查：
- `launch_kernel_cost_func`：最新主线删除的实现 / spec / pytest 未恢复，tuning package、registry、pipeline 和 pipeline pytest 未重新要求 `LaunchKernelCostFuncPass`，退役语义仅保留在 registry/spec/test 的失败边界说明中。
- 旧 direct path：被 canonical family path 替代；旧路径保留为计划要求的 public compat shim，有 spec/test/import smoke 支撑，未作为新 canonical path 使用。
- private callable：`test/repo_conformance/test_private_api_boundaries.py` 已通过；copy / rename 目标按 HEAD source 计算 changed effective lines，未发现当前 diff 需要阻断的小于 5 行单下划线 private callable 或 private callable 调用 private callable。广域扫描中大量 private helper 链来自被 rehome 的既有实现和测试基线，不作为本轮新逻辑阻断；当前阻断是 active API 列表旧默认残留。
- 未删除 / 保留依据：compat shim 保留有 Draft 5-R1 计划依据；`MultiBufferPass(memory_stage=3)` 没有保留依据，应删除 active API 列表和示例中的旧文本。

自检：
- 已读取实际 diff、计划书、执行记录、角色 prompt、根 `AGENTS.md` 与审查规范；未只依赖执行摘要。
- 已同步最新主线并记录执行目录、基线和 merge-base。
- 已核对公开 API / API 列表、跨文件非公开 API、测试直连 private helper、上下文能力探测、非装饰器嵌套函数线索、expectation 权限和敏感目录。
- 已按实际 diff 复跑 pytest、expectation、Markdown、compat smoke、文本 / 退役 / 敏感 / diff check 门禁。
- 因存在明确可执行返工项，本轮结论只能为 `最小需改项`，不得进入 archive_acceptance 或 merge。

时间：2026-06-07 15:27 +0800
经办人：睡觉小分队
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / review 最小需改项返工
任务目标：修复 review 指出的唯一最小需改项：仅将 `kernel_gen/passes/memory/__init__.py` 中 `MultiBufferPass` 文件级 API 列表和使用示例残留的 `memory_stage=3` 改为 latest main 默认 `memory_stage=2`；不得改 pipeline 行为、不得修改 `expectation/`、不得扩大 diff。
执行前阅读记录：
- 已读最新 `TODO.md` doing 状态、本任务 review 记录、根 `AGENTS.md`、`agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md` 和本任务记录。
- 已核对当前任务为 `execute / 睡觉小分队 / 进行中`，目标为修复 `kernel_gen/passes/memory/__init__.py` 两处文档默认值残留。
改动：
- 仅修改 `kernel_gen/passes/memory/__init__.py` 两处文件级说明：
  - API 列表：`MultiBufferPass(memory_stage: int = 3, ...)` -> `MultiBufferPass(memory_stage: int = 2, ...)`
  - 使用示例：`MultiBufferPass(memory_stage=3)` -> `MultiBufferPass(memory_stage=2)`
- 未修改 pipeline、`expectation/`、`spec`、测试逻辑或 `DmaMakeRingOp` 合同。
验证：
- 旧默认值门禁：`rg -n "memory_stage: int = 3|MultiBufferPass\\(memory_stage=3" kernel_gen/passes kernel_gen/pipeline spec/pass test/passes` 无输出，退出码 1（无命中，符合预期）。
- 指定 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py -x`：`79 passed, 1 warning`，退出码 0。
- 格式门禁：`git diff --check && git diff --cached --check`：退出码 0。
- staged 旧默认值核对：`git diff --cached -- kernel_gen/passes/memory/__init__.py | rg -n "memory_stage: int = 3|MultiBufferPass\\(memory_stage=3"` 无输出，退出码 1（无命中，符合预期）。
Diff 反推自测：
- 本轮实际 diff 只触达 `kernel_gen/passes/memory/__init__.py` 文件级 API 列表与使用示例，因此反推运行 `test/passes/memory/test_multi_buffer.py` 锁定 `MultiBufferPass` 默认值行为，运行 `test/passes/test_registry.py` 锁定 registry / canonical / compat import 行为，并用旧默认值 `rg` 门禁确认 active 实现 / spec / pytest / pipeline 文本不再残留 `memory_stage=3` 公开默认值。
减法检查：
- 新增 / 改动 private callable：无。本轮只改文件级文档两行，不新增函数、类、helper 或跨文件调用。
- 被替代旧逻辑：无业务逻辑替代；只删除错误文档默认值 `3`，替换为当前公开默认值 `2`。
- 保留旧逻辑依据：未改任何旧 compat shim、pipeline 或 expectation；现有候选 diff 的 compat shim 保留依据仍为 Draft 5-R1 兼容要求。
自检：
- 接口 / API：未新增或修改公开 API；文档索引与当前 `MultiBufferPass(memory_stage: int = 2, ...)` 真实签名对齐。
- 边界 / 兼容：未改变 `npu-demo-lowering` pipeline，不接入新阶段，不新增 pipeline option，不回退或前推 `dma.make_ring` / `DmaMakeRingOp` 合同。
- 禁止面：未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`。
- 测试有效性：旧默认值门禁能在文档残留时失败；`test_multi_buffer.py` 覆盖默认 `memory_stage=2` 行为，`test_registry.py` 覆盖 canonical / compat import 与 registry 行为。
结论：review 最小需改项已按限定范围修复，指定验证通过；候选可重新流转 review。

时间：2026-06-07 15:33 CST
经办人：提莫炖蘑菇
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / 最小返工复审
任务目标：复审 pass-directory-layout-refactor 最小返工候选，重点核对 `kernel_gen/passes/memory/__init__.py` 中 `MultiBufferPass` 文件级 API 列表和使用示例已从 `memory_stage=3` 修正为 latest main 默认 `memory_stage=2`，并确认未改 pipeline 行为、未修改 `expectation/`、未扩大 diff。
审查结论：通过。未发现剩余阻断或最小需改项；计划级任务下一阶段应进入 `archive_acceptance / 计划书入档验收`，不得直接 merge。
发现：
- 无阻断发现。
审查范围：
- worktree：`/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`
- 计划书：`ARCHITECTURE/plan/pass_directory_layout_refactor.md`，Draft 5-R1，`sha256=5350d49c6d6affbca1dcd8618b89cbb9cd349a7a0fe9d3f37b86fa35fa4549bd`，index blob `7e364fb2575c621e9121d78f69adb508ed55e330`。
- 被审 diff：当前 staged diff 67 个路径；本轮最小返工点为 `kernel_gen/passes/memory/__init__.py` 文件级说明中的 `MultiBufferPass` 默认值文本。
- 禁止面：未发现 `.skills/`、`expectation/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 候选 diff。
最新同步现场：
- `git fetch --prune origin && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：`HEAD=origin/main=merge-base=374b1074ad7a84c70d1288515b8f49b4b847718d`，ahead / behind `0 0`。
执行记录核对：
- 已读取并核对 15:23 review 记录和 15:27 execute 返工记录。上一轮唯一阻断为 `kernel_gen/passes/memory/__init__.py` 中 active API 列表 / 示例残留 `memory_stage=3`；本轮执行记录只修复该文件两处文本，未声明修改 pipeline、`expectation/`、spec、测试逻辑或 make-ring 合同。
- 执行记录包含执行前阅读、改动、验证、`Diff 反推自测`、减法检查、自检和结论；本轮复审已复跑点名门禁与补充全量 pass / expectation 核验。
验证：
- `nl -ba kernel_gen/passes/memory/__init__.py`：line 15 为 `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`；line 21 为 `MultiBufferPass(memory_stage=2)`。
- `rg -n "memory_stage: int = 3|MultiBufferPass\\(memory_stage=3" kernel_gen/passes kernel_gen/pipeline spec/pass test/passes`：无输出，退出码 1，表示旧默认值 active 门禁无命中。
- `git diff --cached -- kernel_gen/passes/memory/__init__.py | rg -n "memory_stage: int = 3|MultiBufferPass\\(memory_stage=3|memory_stage: int = 2|MultiBufferPass\\(memory_stage=2"`：只命中新增 `memory_stage: int = 2` 与 `MultiBufferPass(memory_stage=2)`，未命中旧 `3`。
- `rg -n "class MultiBufferPass|def __init__|MultiBufferPass\\(" kernel_gen/passes/memory/multi_buffer.py kernel_gen/pipeline/npu_demo_lowering.py spec/pass/memory/multi_buffer.md spec/pass/pipeline/npu_demo_lowering.md test/passes/pipeline/test_npu_demo_lowering.py test/passes/memory/test_multi_buffer.py`：实现签名、spec、pipeline 和测试均指向默认 / pipeline 调用 `memory_stage=2`。
- `git diff --cached -- kernel_gen/pipeline/npu_demo_lowering.py kernel_gen/pipeline/cuda_sm86_lowering.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/pipeline/test_cuda_sm86_lowering.py`：pipeline 与 pipeline 测试 diff 仅为旧 direct import 到 canonical import 的替换；未新增 pipeline option，未重排 pipeline 行为。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py -x`：`79 passed, 1 warning`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes -x`：`589 passed, 1 warning`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py -x`：`4 passed`，退出码 0。
- 10 项 Draft 5-R1 当前必过 expectation：在 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate` 与 `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor` 下运行 `expectation.pass.arch_parallelize`、`expectation.pass.attach_arch_information`、`expectation.pass.kernel_aggregate`、`expectation.pass.kernel_decompose`、`expectation.pass.memory_plan`、`expectation.pass.memory_pool`、`expectation.pass.outline_device_kernel`、`expectation.pass.dma_memory_hierarchy.basic`、`expectation.pass.kernel_pattern_attach`、`expectation.pass.transform_apply`，全部 PASS。
- `git diff --check && git diff --cached --check`：退出码 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff --cached -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 均无输出。
Diff 反推审查：
- 本轮最小返工只改变 `kernel_gen/passes/memory/__init__.py` 文件级 API 列表和使用示例两处文本；反推测试为旧默认值 `rg` 门禁、`test/passes/memory/test_multi_buffer.py` 和 `test/passes/test_registry.py`。
- 为确认计划级候选没有因该返工引入回归，补跑全量 `test/passes`、private API conformance 与 10 项当前必过 expectation；均通过。
- `expectation` 作为合同验收单列，不计入 diff 反推测试；本轮未运行非必过 / 共享 baseline 冲突 expectation。
减法审查：
- 本轮未新增或改动 private callable；`test/repo_conformance/test_private_api_boundaries.py` 通过。
- 被替代旧文案：删除 active API 列表和示例中的旧默认值 `memory_stage=3`，替换为当前真实公开默认值 `memory_stage=2`；旧默认值无保留依据，active 范围文本门禁已无命中。
- pipeline、compat shim、`expectation/`、`DmaMakeRingOp` 和 make-ring 合同均未因本轮返工改变；`kernel_gen/pipeline` diff 仅为 canonical import 化。
自检：
- 已按 review 口径核对任务目标、计划书、worktree、记录文件、最新主线、执行记录、实际 diff、禁止修改面、公开 API 列表、测试有效性、减法检查和 private callable。
- 未发现跨文件非公开 API 使用、测试直连 private helper、上下文能力探测、非装饰器嵌套函数或 `expectation/` 越权改动与本轮返工相关的新问题。
- 因无剩余可执行返工项，本轮结论为通过；计划级链路下一步应续接 `archive_acceptance`。
结论：review 通过。可使用 `-next -type archive_acceptance` 进入计划书入档验收。

时间：2026-06-07 15:37 +0800
经办人：不要啊教练
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / archive_acceptance 计划书入档验收
任务目标：核对计划级 Draft 5-R1 review 通过后的入档记录、最新同步现场、10 项当前必过 expectation、`test/passes`、`private_api_boundaries`、旧默认值 `memory_stage=3` 文本门禁、canonical / compat import 与 shim AST、敏感目录空 diff、`git diff --check` / `git diff --cached --check` 和可归档性；通过后续接 merge，不直接执行 merge。
结论：通过。无阻断、无最小需改项；可按计划级链路从 `archive_acceptance` 续接 `merge`。

发现：
- 无阻断发现。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`
- `git fetch --prune origin && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：`HEAD=origin/main=merge-base=374b1074ad7a84c70d1288515b8f49b4b847718d`，ahead / behind `0 0`。
- 当前 worktree 只有 staged 候选 diff，无 unstaged diff；不存在同步冲突或覆盖风险。

计划书与记录核对：
- 计划书路径：`ARCHITECTURE/plan/pass_directory_layout_refactor.md`。
- 计划书 sha：`5350d49c6d6affbca1dcd8618b89cbb9cd349a7a0fe9d3f37b86fa35fa4549bd`；index blob `7e364fb2575c621e9121d78f69adb508ed55e330`。
- 任务记录包含 15:11 Draft 5-R1 execute 收口、15:23 review 不通过、15:27 execute 最小返工、15:33 review 通过记录；review 结论为通过，无剩余阻断 / 无最小需改项。
- 计划正文作为候选新增文件已在 staged diff 中；本轮 archive_acceptance 未发现需要由验收角色继续回写计划正文的事项，入档验收结论写入本任务记录并随候选同批交 merge。

验证：
- `git diff --check && git diff --cached --check`：退出码 0。
- 旧默认值文本门禁：`rg -n "memory_stage: int = 3|MultiBufferPass\\(memory_stage=3" kernel_gen/passes kernel_gen/pipeline spec/pass test/passes` 无输出，`rg_exit=1`，符合无命中预期。
- canonical / compat import 与 shim AST：9 组 compat shim 与 canonical module 公开对象一致；9 个旧 compat shim 文件不含业务 `FunctionDef` / `AsyncFunctionDef` / `ClassDef`，输出 `canonical/compat import smoke ok; shim ast ok`，退出码 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff --cached -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 均无输出。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes -x`：`589 passed, 1 warning`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py -x`：`4 passed`，退出码 0。
- `kernel_gen/passes/memory/__init__.py` 人工核对：line 15 为 `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`，line 21 示例为 `MultiBufferPass(memory_stage=2)`；上一轮阻断已收口。

合同验收：
- 当前必过 10 项 expectation 在 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate`、`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor` 下全部通过：
  - `python3 -m expectation.pass.arch_parallelize`
  - `python3 -m expectation.pass.attach_arch_information`
  - `python3 -m expectation.pass.kernel_aggregate`
  - `python3 -m expectation.pass.kernel_decompose`
  - `python3 -m expectation.pass.memory_plan`
  - `python3 -m expectation.pass.memory_pool`
  - `python3 -m expectation.pass.outline_device_kernel`
  - `python3 -m expectation.pass.dma_memory_hierarchy.basic`
  - `python3 -m expectation.pass.kernel_pattern_attach`
  - `python3 -m expectation.pass.transform_apply`
- 非必过 / 历史共享 expectation 基线冲突仍按 Draft 5 计划正文处理，未纳入当前阻断，且本轮未修改 `expectation/`。

Diff 反推审查：
- 计划级候选触达 pass implementation rehome、compat shim、registry / pipeline canonical import、spec/test 目录迁移、private API boundary conformance 和任务记录；本轮用 `test/passes` 覆盖 pass、registry、pipeline 与迁移后 tests，用 `test_private_api_boundaries.py` 覆盖 private API 门禁，用 10 项 expectation 单列合同验收。
- 针对上一轮最小返工，已用旧默认值 `rg` 门禁、`kernel_gen/passes/memory/__init__.py` staged diff 和 `test/passes` 复跑确认 active `memory_stage=3` 默认值残留已删除。
- canonical / compat import smoke 与 shim AST 覆盖旧 public import path 兼容和 shim 不承载业务逻辑的计划要求。

减法审查：
- 旧 direct path 被 canonical family path 替代；旧 public import path 只保留为 Draft 5-R1 要求的薄 compat shim，import smoke 与 shim AST 均通过。
- `launch_kernel_cost_func` 相关已退场资产未恢复；review 记录已核对 registry / pipeline / pytest 不重新要求该 pass。
- 本轮 archive_acceptance 无新增 / 改动 private callable；候选 private API conformance 通过。上一轮唯一旧文案 `MultiBufferPass(memory_stage=3)` 已被 `2` 替换，active 范围文本门禁无命中。

可归档性：
- 计划书、实现、spec、test、任务记录均作为 staged 候选存在；敏感目录和 `expectation/` 无 diff；`TODO.md` / `DONE.md` 未被手工修改。
- review 通过记录、返工闭环记录、当前入档验收记录齐备；当前验证基线与任务要求一致。
- 可交 merge 角色执行合入和最终归档；archive_acceptance 本人不直接 merge。

自检：
- 已核对任务 ID、任务类型、计划书、worktree、记录文件、禁止修改面、合同真源、latest main 基线和下一阶段责任。
- 已读取实际 staged diff 与最新任务记录，未只依赖口头回报。
- 已按 archive_acceptance 要求复跑 pytest、private API、10 项 expectation、文本门禁、canonical / compat import、shim AST、敏感目录和 diff check。
- 未修改实现、spec、测试、计划书、`expectation/`、标准文档或任务状态文件；只追加并 staged 本入档验收记录。

时间：2026-06-07 16:35 +0800
经办人：李白
任务：T-20260607-3318f2e2 / pass-directory-layout-refactor / merge
任务目标：合入已通过 review 与 archive_acceptance 的 pass-directory-layout-refactor Draft 5-R1 候选、任务记录和计划归档；合并前复核 latest main、staged 记录、敏感目录空 diff、`git diff --check` / `git diff --cached --check`。
合入来源与范围：
- worktree：`/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`。
- 合入基线：`HEAD=origin/main=merge-base=374b1074ad7a84c70d1288515b8f49b4b847718d`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- staged 任务记录：`agents/codex-multi-agents/log/task_records/2026/23/20260607-pass-directory-layout-refactor.md` 已在候选 diff 中。
- staged 候选范围：67 个路径，覆盖 pass family canonical rehome、public compat shim、registry / pipeline canonical import、spec/test 目录迁移、private API boundary conformance、工具测试、任务记录和计划归档。
- 禁止面：`.skills/`、`expectation/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 均无 status / unstaged diff / cached diff。
计划归档：
- 原路径：`ARCHITECTURE/plan/pass_directory_layout_refactor.md`。
- 归档目标：`agents/codex-multi-agents/log/task_records/done_plan/2026/pass_directory_layout_refactor.md`。
- 合并前 `git ls-files --stage -- ARCHITECTURE/plan/pass_directory_layout_refactor.md`：`100644 7e364fb2575c621e9121d78f69adb508ed55e330 0`，计划书已进入 index。
- 已执行 `git mv ARCHITECTURE/plan/pass_directory_layout_refactor.md agents/codex-multi-agents/log/task_records/done_plan/2026/pass_directory_layout_refactor.md`；本次提交不保留 `ARCHITECTURE/plan/pass_directory_layout_refactor.md`。
验证：
- `git fetch --prune origin`：退出码 0。
- `git diff --check && git diff --cached --check`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py -x`：`4 passed`，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes -x`：`589 passed, 1 warning`，退出码 0。
- 旧默认值门禁：`rg -n "memory_stage: int = 3|MultiBufferPass\\(memory_stage=3" kernel_gen/passes kernel_gen/pipeline spec/pass test/passes` 无输出，退出码 1，符合无命中预期。
- canonical / compat import 与 shim AST：本地 Python 脚本输出 `canonical/compat import smoke ok; shim ast ok`，退出码 0。
合同验收：
- 环境：`PYTHONDONTWRITEBYTECODE=1`，`PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor:/home/lfr/kernelcode_generate`，`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`。
- 当前必过 10 项 expectation 全部退出码 0：`expectation.pass.arch_parallelize`、`expectation.pass.attach_arch_information`、`expectation.pass.kernel_aggregate`、`expectation.pass.kernel_decompose`、`expectation.pass.memory_plan`、`expectation.pass.memory_pool`、`expectation.pass.outline_device_kernel`、`expectation.pass.dma_memory_hierarchy.basic`、`expectation.pass.kernel_pattern_attach`、`expectation.pass.transform_apply`。
冲突处理：
- 本轮 merge 前 `HEAD=origin/main`，候选已经在 latest main `374b1074` 上完成 review 与 archive_acceptance；未发生同步冲突。
- 若提交前 `origin/main` 前进，将重新同步并按合并规范复核；当前无未解决冲突、无 unstaged diff。
剩余风险：
- 非必过 / 历史共享 expectation 未纳入当前阻断；本轮不修改 `expectation/`。
- 计划级归档与任务记录已同批 staged，最终提交号在合并完成回报中说明。
结论：merge 前 gate 通过，可提交并推送 `main`，随后执行 `-done`，并按最新流程清理已完成任务 worktree / branch；若清理条件不满足，在回报中列出原因。
