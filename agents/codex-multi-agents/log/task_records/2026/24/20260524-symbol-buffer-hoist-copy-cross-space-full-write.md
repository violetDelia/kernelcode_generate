# 20260524-symbol-buffer-hoist-copy-cross-space-full-write

时间：2026-05-24 20:22 CST
经办人：守护最好的爱莉希雅
任务：symbol-buffer-hoist `dma.copy` cross-space full-write expectation 同步与后续任务建议
任务目标：按用户明确授权，在 `expectation/pass/symbol_buffer_hoist/kernel_lifecycle.py` 增加一条合同 case，并请求管理员创建后续修复任务让该功能正常。
改动：
- 用户确认口径：`dma.copy(target, source)` 在 target/source shape、stride、dtype 相同，仅 memory space 不同时，仍应视为对 target 的完整写入。
- 授权 expectation scope：仅修改 `expectation/pass/symbol_buffer_hoist/kernel_lifecycle.py`。
- 新增 case：`pass-symbol_buffer_hoist-kernel_lifecycle-copy_cross_space_full_write-1`。
- case 语义：loop 内 `%buf = dma.alloc -> #nn.space<tlm1>`，随后 `dma.copy(%buf, %src_tsm)`，再由 `kernel.matmul` 读取 `%buf`；期望 `symbol-buffer-hoist` 将 `%buf` 与唯一 `dma.free` 成对外提到 loop 前后。
- hash：
  - 修改前 `kernel_lifecycle.py` sha256：`a1d9441f1a544ea850c8a08d02e03cc8dce2451bc527a0d0faf2be7c7d12e65b`
  - 修改后 `kernel_lifecycle.py` sha256：`7966fc0fa86e641c22aedc9664ac2b20c4879c9a9e14546413333ec69c2aab31`
验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/pass/symbol_buffer_hoist/kernel_lifecycle.py`
  - 结果：exit=0，语法通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist.kernel_lifecycle`
  - 结果：exit=1，预期红点。
  - 失败 case：`pass-symbol_buffer_hoist-kernel_lifecycle-copy_cross_space_full_write-1`。
  - 失败摘要：`CHECK not found`，期望 alloc 已在 `symbol.for` 前，但当前实现仍保留在 loop 内。
- `git diff --name-only -- expectation .skills agents/standard` 与 `git diff --cached --name-only -- expectation .skills agents/standard`
  - 结果：均无输出；`expectation/` 为主仓 ignored 合同资产，本次按用户/架构授权直接更新本地合同真源。
自检：
- 本轮未修改实现、spec、测试或任务状态文件；只更新用户点名的 expectation 合同 case，并记录 hash 与当前红点。
- 新 case 不新增公开 API；后续实现应优先收口 `symbol-buffer-hoist` 内部 full-write 判定，避免扩大 pass 公开签名、registry option 或错误文本。
- 后续 execute 任务必须按实际 diff 补 `pytest`，不能只依赖 expectation；并保持 `expectation/.skills/agents/standard` 未授权 diff 为空。
结论：
- expectation 已按用户授权补齐，当前红点符合预期。
- 建议管理员创建唯一 execute 任务：修复 `SymbolBufferHoistPass` 的 `dma.copy` full-write 判定，使 target/source shape、stride、dtype 相同但 memory space 不同时仍能证明 target 完整写；同步 `spec/pass/symbol_buffer_hoist.md` 和公开 pytest；跑通 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.kernel_lifecycle` 以及相关 `pytest` / `git diff --check` / 敏感目录门禁。

时间：2026-05-24 20:49 CST
经办人：金铲铲大作战
任务：T-20260524-749821ae / symbol-buffer-hoist-copy-cross-space-full-write execute
任务目标：修复 `SymbolBufferHoistPass` 的 `dma.copy` cross-space full-write 判定，同步 `spec/pass/symbol_buffer_hoist.md` 与公开 pytest，跑通主仓只读 `expectation.pass.symbol_buffer_hoist.kernel_lifecycle`、相关 pytest、`git diff --check` 和敏感目录门禁。
执行前阅读记录：
- 已读个人提示词：`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`。
- 已读标准：根 `AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`。
- 已读任务记录前序：本文件 2026-05-24 20:22 架构侧 expectation 同步记录，确认用户授权只限 `expectation/pass/symbol_buffer_hoist/kernel_lifecycle.py`，execute 候选 diff 不得包含 `expectation/.skills/agents/standard`。
- 已读实现 / spec / 测试：`kernel_gen/passes/symbol_buffer_hoist.py`、`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py`。
- latest main 核对：`git fetch origin --prune` 后 `HEAD=origin/main=merge-base=6bd6e5d9782f92261741a8d46abddd6fd3371617`；开工前仅本任务记录文件未跟踪。
最小功能闭环：
- 实现：将 `_memory_types_match(...)` 从整段类型文本相等改为比较 `shape/stride/element_type`，并通过 `require_same_space=True` 默认保持 alias full-cover 的同 space 约束。
- 实现：`DmaCopyOp` target WRITE 的 full-write 判定调用 `_memory_types_match(..., require_same_space=False)`，与 `dma.copy` verifier 的公开合同对齐，允许 source/target memory space 不同但 layout/dtype 相同时证明 target root 完整写。
- spec：在 `spec/pass/symbol_buffer_hoist.md` 明确 `dma.copy(target=buf, source=other)` target/source shape、stride、element_type 相同时可跨 space 证明 target root 完整 reset，alias full-cover 仍要求同 space；新增 `TC-PASS-SYMBOL-BUFFER-HOIST-028`。
- pytest：新增 `test_symbol_buffer_hoist_hoists_alloc_when_copy_cross_space_full_write_resets_kernel_read`，只通过公开 `SymbolBufferHoistPass` 入口验证 cross-space copy reset 后 alloc/free 成对外提。
改动：
- `kernel_gen/passes/symbol_buffer_hoist.py`：收口 `dma.copy` full-write 判定并更新函数注释。
- `spec/pass/symbol_buffer_hoist.md`：补公开行为说明与测试矩阵。
- `test/passes/test_symbol_buffer_hoist.py`：新增公开 pytest 用例与测试 module 构造。
Diff 反推自测：
- `python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py`
  - 结果：exit=0；覆盖本轮实现与测试语法。
- `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_copy_cross_space_full_write_resets_kernel_read`
  - 结果：exit=0，`1 passed, 1 warning`；断言 cross-space `dma.copy` target 被识别为 full write，alloc/free 外提，copy 与后续 kernel read 留在 loop 内并捕获外提 buffer。
- `pytest -q test/passes/test_symbol_buffer_hoist.py`
  - 结果：exit=0，`41 passed, 1 warning`；覆盖 `symbol-buffer-hoist` 既有正反例未回退。
- `pytest -q test/passes/test_registry.py -k symbol_buffer_hoist`
  - 结果：exit=0，`1 passed, 57 deselected, 1 warning`；覆盖 registry 公开入口未回退。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-copy-cross-space-full-write:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.kernel_lifecycle`
  - 结果：exit=0；主仓只读合同入口通过，包含架构侧新增 `pass-symbol_buffer_hoist-kernel_lifecycle-copy_cross_space_full_write-1`。
- 导入边界证明：
  - `expectation.pass.symbol_buffer_hoist.kernel_lifecycle` 来自 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/kernel_lifecycle.py`。
  - `kernel_gen.passes.symbol_buffer_hoist` 来自 `/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-copy-cross-space-full-write/kernel_gen/passes/symbol_buffer_hoist.py`。
静态与敏感目录门禁：
- `git diff --check`
  - 结果：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`
  - 结果：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`
  - 结果：无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：无输出。
- ctx 能力探测扫描：`git diff --name-only -- '*.py' | xargs -r rg -n 'hasattr\\(ctx|hasattr\\([^,]+, "emit_barrier"|getattr\\(ctx|getattr\\([^,]+, "emit_barrier"|callable\\(getattr'`
  - 结果：无输出。
- 嵌套函数 AST 扫描：`kernel_gen/passes/symbol_buffer_hoist.py`、`test/passes/test_symbol_buffer_hoist.py`
  - 结果：`nested-scan-complete`，无嵌套函数。
减法检查：
- 新增 private callable：无。
- 新增测试构造函数 `build_copy_cross_space_full_write_module()` 未使用下划线私有名，带函数注释，用于公开 pytest 构造输入 IR。
- 改动 private callable：`_memory_types_match(lhs, rhs, *, require_same_space=True)`。
  - 为什么不能内联：alias full-cover 与 copy full-write 都需要同一套 layout/dtype 比较，内联会让 `dma.reshape/view/subview/copy` 四处重复 shape/stride/element_type 比较并增加回退风险。
  - 替代旧逻辑：删除 `str(lhs_type) == str(rhs_type)` 的整段类型文本比较；该旧逻辑把 memory space 纳入 `dma.copy` full-write 判定，导致 cross-space copy 被误判为非完整写。
  - 有效代码：AST 顶层有效语句数为 5；函数体内不调用其它 private callable，已移除原 `_memory_type_of(...)` 调用。
  - 保留旧逻辑依据：alias full-cover 默认 `require_same_space=True`，继续保留原有同 space 安全边界；`_memory_type_of(...)` 仍被 `dma.deslice` 和 alias 其它证明路径使用，本轮不删除。
- 改动调用点：`_write_use_covers_root(...)` 中 `DmaCopyOp` target WRITE 切换为 `require_same_space=False`，未新增 private callable、未新增跨文件非公开 API 调用。
自检：
- 公开 API：未新增 / 删除 / 重命名公开 API，未改 pass 名称、registry、参数、错误文本或 expectation 文件。
- 边界：只放宽 `dma.copy` target/source memory space 不同但 shape/stride/element_type 相同的 full-write 证明；alias full-cover 仍要求同 space，避免扩大 view/reshape/subview/reinterpret root 覆盖语义。
- 异常与兼容：非 `NnMemoryType` 或 layout/dtype 不一致仍保守返回 False；既有 no-op 与 partial write 反例由整份 pytest 覆盖。
- 实现质量：比较逻辑集中在当前文件内 helper，注释同步当前真实语义；没有新增 ctx 能力探测、嵌套函数或跨文件非公开 API。
- 测试有效性：新增 pytest 若实现仍按整段类型文本比较会失败；主仓只读 expectation 新 case 已通过，Diff 反推 pytest 覆盖实现、spec 和 registry 相关公开入口。
结论：
- T-20260524-749821ae execute 已完成；候选 diff 仅包含 `kernel_gen/passes/symbol_buffer_hoist.py`、`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py` 与本任务记录。
- `expectation/.skills/agents/standard` 候选 diff 为空；可按流程流转 review。

时间：2026-05-24 20:57 CST
经办人：提莫炖蘑菇
任务：T-20260524-749821ae / symbol-buffer-hoist-copy-cross-space-full-write review
任务目标：复审 `SymbolBufferHoistPass` 的 `dma.copy` cross-space full-write 判定、spec/公开 pytest、主仓只读 `expectation.pass.symbol_buffer_hoist.kernel_lifecycle`、`git diff --check` 与敏感目录门禁。
审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-copy-cross-space-full-write`。
- `git fetch origin` 后核对：`HEAD=6bd6e5d9782f92261741a8d46abddd6fd3371617`，`origin/main=6bd6e5d9782f92261741a8d46abddd6fd3371617`，`merge-base=6bd6e5d9782f92261741a8d46abddd6fd3371617`，ahead/behind=`0/0`。
- 当前候选 diff：`kernel_gen/passes/symbol_buffer_hoist.py`、`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py`；本任务记录文件为未跟踪记录文件。
真实审查：
- 实现审查：`_memory_types_match(lhs, rhs, *, require_same_space=True)` 默认仍要求 `shape/stride/element_type/space` 一致，`DmaCopyOp` target WRITE 单独传 `require_same_space=False`，与 `dma.copy` verifier 只校验 shape/stride/element_type 的公开合同一致；`dma.reshape/view/subview/reinterpret` 等 alias full-cover 路径仍走默认 same-space 边界，没有把 cross-space 放宽扩散到 alias 证明。
- lifecycle 审查：`_write_use_covers_root(...)` 只在 `DmaCopyOp` target operand `use.index == 0` 时放宽 space，source READ 仍由公开 `MemoryEffect` 参与数据事件；copy 后 `kernel.*` read 被 full-write 支配时可外提 alloc/free，未改变 partial write、unknown effect、read-before-write 和 nested branch 反例。
- spec 审查：`spec/pass/symbol_buffer_hoist.md` 已在行为说明与 `TC-PASS-SYMBOL-BUFFER-HOIST-028` 中明确 copy cross-space full-write 口径，并单列 alias full-cover 仍需同 space。
- pytest 审查：新增 `test_symbol_buffer_hoist_hoists_alloc_when_copy_cross_space_full_write_resets_kernel_read` 通过公开 `SymbolBufferHoistPass().apply(...)` 观测行为，未跨文件直连非公开 API；测试断言 alloc/free 外提、copy source 保持 loop 外 source arg、copy target 与后续 kernel read 使用外提 buffer。
- 公开 API / 非公开 API 边界：本轮未新增、删除、重命名公开 API，未修改 pass 名称、registry、参数、错误文本或 expectation 文件；测试没有新增跨文件非公开 API 调用。
Diff 反推审查：
- 本轮 diff 直接修改 pass 判定、spec 合同和公开 pytest，因此复跑新增目标 pytest、整份 `test/passes/test_symbol_buffer_hoist.py`、registry 子集、py_compile、主仓只读 expectation 和 diff/sensitive gate。
- `python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py`
  - 结果：exit=0。
- `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_copy_cross_space_full_write_resets_kernel_read`
  - 结果：exit=0，`1 passed, 1 warning`。
- `pytest -q test/passes/test_symbol_buffer_hoist.py`
  - 结果：exit=0，`41 passed, 1 warning`。
- `pytest -q test/passes/test_registry.py -k symbol_buffer_hoist`
  - 结果：exit=0，`1 passed, 57 deselected, 1 warning`。
主仓只读 expectation 合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-copy-cross-space-full-write:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.kernel_lifecycle`
  - 结果：exit=0；包含 `pass-symbol_buffer_hoist-kernel_lifecycle-copy_cross_space_full_write-1`。
- 导入边界证明：`expectation.pass.symbol_buffer_hoist.kernel_lifecycle` 来自 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/kernel_lifecycle.py`；`kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree 的 `kernel_gen/passes/symbol_buffer_hoist.py`。
- 主仓 expectation hash：`7966fc0fa86e641c22aedc9664ac2b20c4879c9a9e14546413333ec69c2aab31  /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/kernel_lifecycle.py`。
静态与敏感目录门禁：
- `git diff --check && git diff --cached --check`
  - 结果：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`
  - 结果：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`
  - 结果：无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：无输出。
- ctx 能力探测 AST 扫描：无 `hasattr(ctx, ...)`、`getattr(ctx, ...)`、`callable(getattr(...))` 命中。
- 嵌套函数 AST 扫描：无新增非装饰器嵌套函数。
- 跨文件 private import 扫描：无新增私有导入。
减法审查：
- 本轮改动的 private callable 为 `_memory_types_match(...)`；有效顶层语句数为 5，不调用其它 private callable。
- 该 helper 保留有必要性：同一比较逻辑同时服务 alias full-cover 与 copy full-write，且 copy 需要显式关闭 same-space 约束；内联会增加 alias/copy 分支不一致风险。
- 旧 `str(lhs_type) == str(rhs_type)` 被替换是必要修复：该旧逻辑把 memory space 也纳入 `dma.copy` full-write 判定，和用户确认的 cross-space copy full-write 口径冲突。
审查结论：
- 通过。未发现需要退回 execute 的实现/spec/test/导入边界/敏感目录问题。
- 该任务为普通修复任务，review 通过后可按候选范围进入 merge；merge 仍需保持 `expectation/.skills/agents/standard` 无未授权 diff，并只合入本轮候选文件与同批任务记录。

时间：2026-05-24 21:09 +0800
经办人：李白
任务：T-20260524-749821ae / symbol-buffer-hoist-copy-cross-space-full-write merge
任务目标：按 review 通过范围合入 `SymbolBufferHoistPass` 的 `dma.copy` cross-space full-write 修复、spec、公开 pytest 与同批任务记录。
合并前阅读与同步：
- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md` 与 `agents/standard/任务记录约定.md`。
- 主仓执行目录：`/home/lfr/kernelcode_generate`；任务 worktree：`/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-copy-cross-space-full-write`。
- `git fetch --prune origin` 后核对：主仓与任务 worktree 均为 `HEAD=origin/main=merge-base=6bd6e5d9782f92261741a8d46abddd6fd3371617`，任务分支为 `task/symbol-buffer-hoist-copy-cross-space-full-write`，无 ahead/behind 或同步冲突。
- 主仓初次状态曾出现 3 个未跟踪任务记录文件，其中同名 `20260524-symbol-buffer-hoist-copy-cross-space-full-write.md` 与 worktree 记录 hash 不同；`diff -u` 显示主仓同名未跟踪记录只是 worktree 记录前 28 行前缀，worktree 记录包含后续 execute/review 完整记录。准备备份移走该同名未跟踪记录时，该文件已不存在；复核 `git status --short --untracked-files=all` 与 `ls` 确认主仓不再有同名覆盖风险。其它无关未跟踪记录未纳入本任务。
合入范围核对：
- 实现：`kernel_gen/passes/symbol_buffer_hoist.py`
- spec：`spec/pass/symbol_buffer_hoist.md`
- 测试：`test/passes/test_symbol_buffer_hoist.py`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/24/20260524-symbol-buffer-hoist-copy-cross-space-full-write.md`
- `git diff --name-status` 与 `git ls-files --others --exclude-standard` 在任务 worktree 中仅显示上述 3 个候选文件与本任务记录；本轮不合入 `expectation/`、`.skills/`、`agents/standard/`、`TODO.md`、`DONE.md` 或 `ARCHITECTURE/plan`。
Diff 反推 merge 复核：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/symbol_buffer_hoist.py test/passes/test_symbol_buffer_hoist.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_copy_cross_space_full_write_resets_kernel_read`：exit=0，`1 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py`：exit=0，`41 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py -k symbol_buffer_hoist`：exit=0，`1 passed, 57 deselected, 1 warning`。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-copy-cross-space-full-write:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.kernel_lifecycle`：exit=0，包含 `copy_cross_space_full_write` case。
- `expectation` 仅作为主仓只读合同入口执行；本 merge 候选 diff 不包含 `expectation/` 改动。
静态与敏感目录核对：
- `git diff --check`：exit=0。
- `git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard TODO.md DONE.md ARCHITECTURE/plan`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard TODO.md DONE.md ARCHITECTURE/plan`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard TODO.md DONE.md ARCHITECTURE/plan`：空。
- ctx 能力探测扫描：无 `hasattr(ctx, ...)`、`getattr(ctx, ...)`、`callable(getattr(...))` 命中。
- 嵌套函数 AST 扫描：无新增非装饰器嵌套函数。
- 跨文件 private import 扫描：无新增私有导入。
- private callable 扫描命中已审查的 `_memory_types_match(lhs, rhs, *, require_same_space=True)` 签名变更；该 helper 已在 execute `减法检查` 与 review `减法审查` 中说明必要性、旧逻辑替代、无 private callable 调用。merge 复核 AST：函数体为 docstring + 5 个可执行顶层语句，无 private callable 调用，因此不作为未审查阻断。
冲突处理：
- 无文本冲突；任务 worktree 与 `origin/main` 同基线，可将候选 diff 与本记录同批提交后 fast-forward 主仓。
缓存处理：
- 测试后删除任务 worktree 中 `__pycache__` 与 `.pytest_cache`；未删除或修改 `expectation/.skills` 合同资产。
剩余风险：
- 无当前 merge 阻断。`expectation/pass/symbol_buffer_hoist/kernel_lifecycle.py` 的授权合同同步记录已在本任务记录前序中保留，但该文件不是本次 execute/merge 候选 diff，未随本任务提交。
结论：
- merge 前核对通过；下一步将暂存上述 4 个文件，同批提交、快进主仓、push，并执行 `-done`。
