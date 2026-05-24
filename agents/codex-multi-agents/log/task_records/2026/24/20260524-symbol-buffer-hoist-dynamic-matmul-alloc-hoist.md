时间：2026-05-24 21:15 +0800
经办人：神秘人
任务：T-20260524-192177b2 / symbol-buffer-hoist-dynamic-matmul-alloc-hoist / 管理员补建 worktree
任务目标：补齐已分发 execute 任务的 worktree 与记录落点，使执行人可在独立 worktree 中修复 SymbolBufferHoistPass 动态 matmul loop-local acc/tmp/lhs/rhs scratch dma.alloc/dma.free 成对外提。
改动：已创建 worktree `/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist`，分支 `task/symbol-buffer-hoist-dynamic-matmul-alloc-hoist`，基线 `origin/main@264798461c3830ab6abcfa026ef7be199b25d2f3`。本记录文件作为任务链记录，后续 execute/review/merge 按同一路径追加。
验证：`git fetch --prune origin` 成功；创建前 `git worktree list` 无该 worktree，`git branch --list task/symbol-buffer-hoist-dynamic-matmul-alloc-hoist` 无输出；创建后 worktree HEAD 为 `264798461c3830ab6abcfa026ef7be199b25d2f3`。管理员未执行 pytest/expectation。
自检：本次只补齐任务基础设施，不修改实现、spec、测试、expectation、.skills 或 agents/standard。任务仍按 TODO 当前 `execute / 金铲铲大作战 / 进行中` 续接；execute 候选 diff 中 expectation/.skills/agents/standard 必须为空。
结论：worktree 与记录落点已补齐，可通知金铲铲大作战继续 execute。

时间：2026-05-24 21:31 +0800
经办人：金铲铲大作战
任务：T-20260524-192177b2 / symbol-buffer-hoist-dynamic-matmul-alloc-hoist / execute
任务目标：让 SymbolBufferHoistPass 将动态 matmul loop-local acc/tmp/lhs/rhs scratch `dma.alloc/dma.free` 成对外提到 enclosing loops 外，`dma.fill`、`kernel.matmul` 与 `kernel.binary_elewise` 保持循环语义位置；同步 `spec/pass/symbol_buffer_hoist.md` 与公开 pytest；只读跑通主仓 `expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`。
改动：
- 执行前阅读记录：已读取最新个人提示词、`AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`、主仓 `TODO.md` 当前任务行、任务记录、`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py`、`kernel_gen/passes/symbol_buffer_hoist.py` 与主仓只读 expectation 真源。
- 最新同步现场：管理员补建基线为 `origin/main@264798461c3830ab6abcfa026ef7be199b25d2f3`；execute 中先对齐到 `dd3d4e9bd8331b67cfbe857b4331c1b398c9d61f`，验证后发现 `origin/main` 前进到 `403a05870b763a4ad8ba2869e4f6220ef5eabd90`，已执行 `git fetch origin --prune`、`git stash push --include-untracked -m T-20260524-192177b2-pre-review-sync`、`git merge --ff-only origin/main`、`git stash pop`，无冲突；当前 `HEAD = origin/main = merge-base = 403a05870b763a4ad8ba2869e4f6220ef5eabd90`。
- 最小功能闭环：latest main 的 `SymbolBufferHoistPass` 已满足目标 expectation；本轮未改实现，新增公开 pytest 固化动态 matmul 三层 loop 中 acc/tmp/lhs/rhs 四个 scratch alloc/free 外提结果，并确认 fill/matmul/binary 仍在原循环内捕获外提 buffer。
- `spec/pass/symbol_buffer_hoist.md`：新增动态 matmul acc/tmp/lhs/rhs loop-local scratch 正例说明，补 `TC-PASS-SYMBOL-BUFFER-HOIST-029`，明确四个 alloc/free 外提、计算 op 保留循环语义位置的测试映射。
- `test/passes/test_symbol_buffer_hoist.py`：新增 `build_dynamic_matmul_loop_local_scratch_module()` 和 `test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs`，只通过公开 `SymbolBufferHoistPass().apply(...)` 验证行为，不直连跨文件非公开 helper。
验证：
- `python3 -m py_compile test/passes/test_symbol_buffer_hoist.py kernel_gen/passes/symbol_buffer_hoist.py`：退出码 0。
- `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs test/passes/test_symbol_buffer_hoist.py -k 'dynamic_matmul or fixed_point_nested_loop_dynamic or acc_buffer'`：退出码 0，`3 passed, 39 deselected, 1 warning`；锁定新增动态 matmul、既有 dynamic nested 与 acc buffer 外提相关行为。
- `pytest -q test/passes/test_symbol_buffer_hoist.py`：退出码 0，`42 passed, 1 warning`；覆盖 symbol-buffer-hoist 公开 pass 正反例矩阵。
- `pytest -q test/passes/test_registry.py -k symbol_buffer_hoist`：退出码 0，`1 passed, 57 deselected, 1 warning`；确认 registry 公开入口未回退。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`：退出码 0；输出 `[pass-symbol_buffer_hoist-dynamic_matmul_alloc-upper_bound_scratch-1]`。
- `sha256sum /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`：`fb04b2f803d4fee285cfb507bf8aef8c901d59e0ed81823548c1114320d09458`，与任务目标一致。
- 导入边界证明：`expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` 来自 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`；`kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist/kernel_gen/passes/symbol_buffer_hoist.py`。
- `git diff --check`：退出码 0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` 均无输出。
- 静态边界扫描：`git diff --unified=0 -- '*.py' | rg '^\+\s*(def _|async def _|class _|\s+def _)' || true` 无输出；`git diff -- '*.py' | rg 'hasattr\(|getattr\(|callable\(' || true` 无输出；AST 扫描 `test/passes/test_symbol_buffer_hoist.py` 未发现新增嵌套函数。
Diff 反推自测：
- 改动文件 `test/passes/test_symbol_buffer_hoist.py` 反推 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs` 与整文件 `pytest -q test/passes/test_symbol_buffer_hoist.py`，验证新增 case 与既有矩阵均通过。
- 改动文件 `spec/pass/symbol_buffer_hoist.md` 反推测试表中的公开 pytest 名称，已通过新增目标 pytest 与整组 symbol-buffer-hoist pytest；expectation 作为合同验收单列，不替代 Diff 反推 pytest。
- 相关公开注册入口由 `pytest -q test/passes/test_registry.py -k symbol_buffer_hoist` 补充验证，确认 spec 中公开 pass 名称未回退。
减法检查：
- 新增 / 改动 private callable 清单：无；本轮新增的 `build_dynamic_matmul_loop_local_scratch_module()` 非下划线私有 callable，且仅位于测试文件内构造公开 pytest 输入。
- 被替代旧逻辑及处理结果：未替代实现逻辑；latest main 已满足主仓合同，本轮只补 spec 与公开 pytest 证据链，避免无必要改动实现。
- 保留旧逻辑依据：`kernel_gen/passes/symbol_buffer_hoist.py` 现有 lifecycle / fixed-point 逻辑已通过目标 expectation 与新增 pytest；无需删除或改写。
- 删除 / 未删除验证：`git diff --unified=0 -- '*.py' | rg '^\+\s*(def _|async def _|class _|\s+def _)' || true` 无新增 private callable；无旧测试删除。
自检：
- 允许范围：只修改 `spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py` 与本任务记录；未修改 expectation、.skills、agents/standard。
- 公开 API：未新增或修改公开 API、pipeline option、错误语义或 package export。
- 边界与异常：新增 pytest 明确 acc/tmp/lhs/rhs 四个 scratch 都外提，M/N/K loop body 不残留 alloc/free，fill/matmul/binary 继续留在循环内并引用外提 buffer；可在实现只外提部分 buffer、误移动计算 op、或 free 顺序错误时失败。
- 兼容性与维护性：实现不动，测试通过公开 pass 入口观察 IR 结构；未引入跨文件非公开 API 使用、ctx 能力探测或嵌套函数。
- 资源、并发、性能：本轮只补测试/spec，不改变运行时代码路径。
结论：execute 目标已闭合，最新主线现场验证通过，可按流程续接 review；review 重点核对新增动态 matmul scratch pytest 的有效性、spec TC-029 映射、主仓只读 expectation 导入边界与敏感目录空 diff。

时间：2026-05-24 21:41 CST
经办人：提莫炖蘑菇
任务：T-20260524-192177b2 / symbol-buffer-hoist-dynamic-matmul-alloc-hoist / review
任务目标：复审 SymbolBufferHoistPass 动态 matmul acc/tmp/lhs/rhs scratch alloc/free 外提公开 pytest/spec、主仓只读 expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc、相关 pytest、git diff check 与敏感目录门禁。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist`。
- `git fetch --prune origin`：exit=0。
- fetch 后核对：`HEAD=403a05870b763a4ad8ba2869e4f6220ef5eabd90`，`origin/main=403a05870b763a4ad8ba2869e4f6220ef5eabd90`，`merge-base=403a05870b763a4ad8ba2869e4f6220ef5eabd90`，`ahead/behind=0/0`。
- 当前候选 diff：`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py`、本任务记录；无 latest-main 覆盖风险。

发现：
1. 问题 -> 新增测试构造 helper `test/passes/test_symbol_buffer_hoist.py:1260` 使用 `build_dynamic_matmul_loop_local_scratch_module()` 非下划线命名，但该文件顶部说明 `API 列表` 没有公开测试 helper，且功能说明明确“只通过公开入口观察行为，不直连文件内 helper”。该函数不是 `pytest` 测试入口，也不是 spec 定义的公开 API，属于本文件内测试构造 helper。
   影响 -> 以公开形态新增非 API helper，会绕过当前私有 callable 命名 / 减法审查口径，并形成可被其它测试或跨文件误用的事实入口；后续静态门禁难以区分它是公开测试资产还是内部构造辅助。
   最小返工动作 -> 将该 helper 改为 `_build_dynamic_matmul_loop_local_scratch_module()`，同步测试调用与 docstring 示例；或若执行人认为它必须是公开测试构造入口，先补用户确认并同步文件级 API 列表 / spec 测试资产说明。
   验收方式 -> 复跑 `pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs`、整文件 `test/passes/test_symbol_buffer_hoist.py`、`python3 -m py_compile test/passes/test_symbol_buffer_hoist.py`、`git diff --check`，并记录当前 diff 新增非 test 非下划线 helper 已清零或有公开依据。

Diff 反推审查：
- `spec/pass/symbol_buffer_hoist.md`：新增 TC-029 与正例说明，能映射到新增 pytest 名称；语义与主仓 `expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` 一致。
- `test/passes/test_symbol_buffer_hoist.py`：新增正例确实通过公开 `SymbolBufferHoistPass().apply(Context(), module)` 观察行为，断言四个 alloc/free 被外提且 fill/matmul/binary 留在 loop 内；但新增构造 helper 命名不符合内部 helper 边界，需收口。
- `kernel_gen/passes/symbol_buffer_hoist.py`：本轮未改实现；latest main 行为由新增 pytest 与主仓只读 expectation 验证，未发现需扩大实现修改范围。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs test/passes/test_symbol_buffer_hoist.py -k 'dynamic_matmul or fixed_point_nested_loop_dynamic or acc_buffer'`：exit=0，`3 passed, 39 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py`：exit=0，`42 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_registry.py -k symbol_buffer_hoist`：exit=0，`1 passed, 57 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`：exit=0，输出 `[pass-symbol_buffer_hoist-dynamic_matmul_alloc-upper_bound_scratch-1]`。
- 导入边界证明：`expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` 来自 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`；`kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist/kernel_gen/passes/symbol_buffer_hoist.py`。
- `sha256sum /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`：`fb04b2f803d4fee285cfb507bf8aef8c901d59e0ed81823548c1114320d09458`。
- `python3 -m py_compile test/passes/test_symbol_buffer_hoist.py kernel_gen/passes/symbol_buffer_hoist.py && git diff --check && git diff --cached --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` 均无输出。
- 静态边界扫描：`git diff --unified=0 -- '*.py' | rg '^\+\s*(def _|async def _|class _|\s+def _)' || true` 无输出；`git diff -- '*.py' | rg 'hasattr\(|getattr\(|callable\(' || true` 无输出；`git diff -- '*.py' | rg 'importlib|__import__|object\b' || true` 无输出。

减法审查：
- 新增 / 改动 private callable：未新增单下划线 private callable；但新增非测试入口 helper `build_dynamic_matmul_loop_local_scratch_module()` 未使用单下划线，保留依据不足。
- 旧逻辑替代：本轮不替代实现逻辑，主要补齐 spec 和公开 pytest；latest main 已满足目标 expectation。
- 保留旧逻辑：`kernel_gen/passes/symbol_buffer_hoist.py` 未改，目标 pytest 与主仓 expectation 证明其现有 fixed-point / lifecycle 行为满足本任务目标。

执行记录核对：
- 已记录执行前阅读、最新同步现场、最小功能闭环、Diff 反推自测、减法检查、自检、主仓 expectation 导入边界和敏感目录空 diff。
- 执行记录认为新增 helper“非下划线私有 callable，且仅位于测试文件内构造公开 pytest 输入”；该保留依据不足以放行，因为它不是测试入口，也未列为公开 API。

自检：
- 特殊情况：当前阻断只针对本轮新增 helper，不把历史同类测试 helper 作为本任务阻断。
- 完整性：已核对 spec 映射、pytest 有效性、expectation 只读合同、registry、diff check、敏感目录和静态扫描。
- 维护性：测试构造 helper 若继续以公开形态存在，会削弱后续私有边界审查的一致性。
- 测试有效性：新增 pytest 的行为断言有效，但 helper 边界未收口。

结论：最小需改项。不得进入 merge；需回 execute 收口新增测试 helper 的公开 / 私有边界后复审。

时间：2026-05-24 21:47 CST
经办人：睡觉小分队
任务：T-20260524-192177b2 / symbol-buffer-hoist-dynamic-matmul-alloc-hoist / execute 返工
任务目标：修复 review 最小需改项，将 `test/passes/test_symbol_buffer_hoist.py` 中新增动态 matmul 构造 helper 收口为单下划线私有 helper，同步调用与 docstring，并复跑指定 pytest、py_compile、主仓只读 expectation、diff check 与敏感目录门禁。

执行前阅读记录：
- 已读最新个人提示词、`AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/测试文件约定.md`、本任务记录和 review 退回意见。
- 已核对主仓 `TODO.md` 当前任务行：T-20260524-192177b2 当前为 `execute / 睡觉小分队 / 进行中`，worktree `/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist`，记录文件为本文件。
- 当前执行目录：`/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist`；分支：`task/symbol-buffer-hoist-dynamic-matmul-alloc-hoist`；HEAD：`403a05870b763a4ad8ba2869e4f6220ef5eabd90`。

返工收口：
- review 阻断：新增测试构造 helper `build_dynamic_matmul_loop_local_scratch_module()` 不是 pytest 入口，也未列入文件级 API 列表，应收口为本文件私有 helper，或补用户确认公开依据。
- 实际修复：将 helper 改名为 `_build_dynamic_matmul_loop_local_scratch_module()`，同步 docstring 使用示例和测试调用。
- 额外边界收口：该 helper 改为私有后，内部不再调用 `_memory_type(...)` / `_const_symbol(...)` 等私有 callable，改用公开 `NnMemoryType(...)`、`SymbolExprAttr.from_expr(...)`、`NnMemorySpaceAttr.from_name(...)`、`SymbolConstOp(...)` 直接构造，避免私有 helper 套私有 helper。
- 未新增公开 API，未修改实现行为，未修改 `expectation/`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`。

最小功能闭环：
- 测试构造 helper 现在是本测试文件内部私有 helper，调用方仅为同文件公开 pytest。
- 动态 matmul acc/tmp/lhs/rhs scratch alloc/free 外提断言保持不变，仍通过公开 `SymbolBufferHoistPass().apply(Context(), module)` 入口观察行为。
- 主仓只读合同验收仍使用 `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate`，确保 `expectation` 来自主仓、`kernel_gen` 来自任务 worktree。

验证：
- `python3 -m py_compile test/passes/test_symbol_buffer_hoist.py kernel_gen/passes/symbol_buffer_hoist.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs`：exit=0，`1 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py`：exit=0，`42 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`：exit=0，输出 `[pass-symbol_buffer_hoist-dynamic_matmul_alloc-upper_bound_scratch-1]`。
- `sha256sum /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`：`fb04b2f803d4fee285cfb507bf8aef8c901d59e0ed81823548c1114320d09458`。
- 导入边界证明：`expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` 来自 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`；`kernel_gen.passes.symbol_buffer_hoist` 来自 `/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist/kernel_gen/passes/symbol_buffer_hoist.py`。
- `git diff --check && git diff --cached --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均无输出。
- 静态边界扫描：`git diff -- '*.py' | rg 'hasattr\\(|getattr\\(|callable\\(' || true` 无输出；`git diff -- '*.py' | rg 'VerifyException' || true` 无输出。
- 私有 helper 核对脚本：`_build_dynamic_matmul_loop_local_scratch_module` 有效顶层语句数 `32`，且 `private_calls=[]`；满足不少于 5 行有效代码且不调用其它 private callable。

Diff 反推自测：
- 改动 `test/passes/test_symbol_buffer_hoist.py`：反推目标 pytest、整文件 pytest、py_compile、私有 helper 静态核对，覆盖新增 helper 命名边界、调用更新和原动态 matmul 行为断言。
- 改动 `spec/pass/symbol_buffer_hoist.md` 属于上一轮候选 diff，保留并继续由整文件 pytest 与目标 expectation 证明 TC-029 映射仍有效。
- `expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` 作为合同验收单列，不替代 Diff 反推 pytest。

减法检查：
- 新增 / 改动 private callable：`_build_dynamic_matmul_loop_local_scratch_module()`；有效顶层语句数 `32`，存在必要性是复用较长动态 matmul M/N/K 三层 loop 构造，内联到测试函数会显著降低断言可读性。
- private callable 套 private callable：已消除；该 helper 不调用 `_memory_type`、`_const_symbol` 或其它单下划线 callable，静态脚本输出 `private_calls=[]`。
- 被替代旧逻辑及处理结果：非下划线 `build_dynamic_matmul_loop_local_scratch_module()` 已删除，`rg "build_dynamic_matmul_loop_local_scratch_module|_build_dynamic_matmul_loop_local_scratch_module" test/passes/test_symbol_buffer_hoist.py -n` 仅剩私有 helper 定义、docstring 示例和同文件测试调用。
- 保留旧逻辑依据：原测试行为断言和 spec TC-029 不变；latest main 实现仍由 pytest 与主仓只读 expectation 证明满足目标。

自检：
- 接口：未新增公开 API，未把测试构造 helper 写入文件级 API 列表；新增 helper 已收为单下划线私有。
- 边界：测试仍只通过公开 `SymbolBufferHoistPass` 入口验证行为，不跨文件调用非公开 helper。
- 异常与兼容：未改实现错误语义或 pass 行为；无 `VerifyException` 新增使用。
- 实现遗漏：review 指出的 helper 命名、调用与 docstring 已同步；私有套私有风险已额外消除。
- 冗余与复用：保留 helper 是因为构造体量较大且服务单个复杂正例；未新增短小 private callable。
- 注释准确性：docstring 示例已改为 `_build_dynamic_matmul_loop_local_scratch_module()`。
- 输入/输出与测试有效性：目标 pytest 在 helper 断裂、命名未同步或外提行为回退时会失败；整文件 pytest 覆盖既有矩阵未回退。
- 资源/并发/性能：仅测试代码和 spec 变更，不影响运行时路径。

结论：review 最小需改项已修复，execute 返工闭环，可续接 review。

时间：2026-05-24 21:42 CST
经办人：提莫炖蘑菇
任务：T-20260524-192177b2 / 状态流转
任务目标：按 review 最小需改项退回 `execute`，并回报管理员。
改动：
- 未修改业务代码、spec、测试、expectation、.skills 或 agents/standard。
- 已在主仓执行 `-next -auto -type execute`，退回执行收口。
验证：
- 命令：`bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -next -auto -task_id T-20260524-192177b2 -from 提莫炖蘑菇 -type execute -message "execute；任务目标：修复 review 最小需改项，将 test/passes/test_symbol_buffer_hoist.py 中新增的动态 matmul 构造 helper 收口为单下划线私有 helper并同步调用/docstring，或补用户确认与文件级 API 列表公开依据；复跑新增目标 pytest、整文件 symbol_buffer_hoist pytest、py_compile、git diff check、主仓只读 expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc 与敏感目录空 diff；任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist.md" -agents-list agents/codex-multi-agents/agents-lists.md`
- 结果：exit=0；`OK: next T-20260524-192177b2`、`OK: auto-dispatch T-20260524-192177b2 -> 睡觉小分队`、`OK: talk 提莫炖蘑菇 -> 睡觉小分队`、`OK: talk 提莫炖蘑菇 -> 神秘人`。
- TODO 核对：`rg -n "T-20260524-192177b2" TODO.md` 显示任务类型为 `execute`、指派为 `睡觉小分队`、状态为 `进行中`。
自检：
- 流程：review 不通过已回 execute，未进入 merge。
- 记录：已写清最新同步现场、发现、Diff 反推审查、验证、减法审查、自检和最小返工动作。
结论：T-20260524-192177b2 已退回 `execute / 睡觉小分队 / 进行中`。

时间：2026-05-24 21:50 CST
经办人：提莫炖蘑菇
任务：T-20260524-192177b2 / symbol-buffer-hoist-dynamic-matmul-alloc-hoist / review 复审
任务目标：复审 `test/passes/test_symbol_buffer_hoist.py` 动态 matmul 构造 helper 已收口为单下划线私有 helper、无私有套私有、pytest / py_compile / 主仓只读 expectation / git diff check / 敏感目录空 diff 与任务记录。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist`。
- `git fetch --prune origin`：exit=0。
- fetch 后核对：`HEAD=403a05870b763a4ad8ba2869e4f6220ef5eabd90`，`origin/main=403a05870b763a4ad8ba2869e4f6220ef5eabd90`，`merge-base=403a05870b763a4ad8ba2869e4f6220ef5eabd90`，`ahead/behind=0/0`。
- 当前候选 diff：`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py`、本任务记录；无 latest-main 覆盖风险。

复审结论：
- 前次阻断已收口：`build_dynamic_matmul_loop_local_scratch_module()` 已改为 `_build_dynamic_matmul_loop_local_scratch_module()`，docstring 示例和测试调用均同步为单下划线私有 helper。
- 私有函数审查：独立 AST 核验 `_build_dynamic_matmul_loop_local_scratch_module` 有效代码行 `55`，`private_calls=[]`，满足不少于 5 行有效代码且不调用其它 private callable。
- 公开 API / 测试边界：未新增公开 API，未改 `SymbolBufferHoistPass` 行为入口；新增测试仍通过公开 `SymbolBufferHoistPass().apply(Context(), module)` 观察行为，没有跨文件直连非公开 helper。

Diff 反推审查：
- `test/passes/test_symbol_buffer_hoist.py`：返修仅收口新增构造 helper 的私有命名和内部构造方式；目标 pytest 与整文件 pytest 能锁定 helper 调用同步、动态 matmul alloc/free 外提、计算 op 保留循环内。
- `spec/pass/symbol_buffer_hoist.md`：TC-029 与新增 pytest 名称一致，仍映射动态 matmul acc/tmp/lhs/rhs scratch alloc/free 成对外提完成态。
- `kernel_gen/passes/symbol_buffer_hoist.py`：本轮未改实现，行为由公开 pytest 与主仓只读 expectation 复验。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs`：exit=0，`1 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py`：exit=0，`42 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`：exit=0，输出 `[pass-symbol_buffer_hoist-dynamic_matmul_alloc-upper_bound_scratch-1]`。
- `python3 -m py_compile test/passes/test_symbol_buffer_hoist.py kernel_gen/passes/symbol_buffer_hoist.py && git diff --check && git diff --cached --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均无输出。
- 独立 AST 核验：`name=_build_dynamic_matmul_loop_local_scratch_module`、`effective_lines=55`、`private_calls=[]`。
- 导入边界证明：`expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` 来自 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`；`kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist/kernel_gen/passes/symbol_buffer_hoist.py`。
- `sha256sum /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`：`fb04b2f803d4fee285cfb507bf8aef8c901d59e0ed81823548c1114320d09458`。
- 静态扫描：`git diff -- '*.py' | rg 'hasattr\(|getattr\(|callable\(|VerifyException|__import__|object\b' || true` 无输出。

减法审查：
- 被替代旧逻辑：非下划线测试构造 helper 已删除；`rg` 仅剩 `_build_dynamic_matmul_loop_local_scratch_module` 定义、docstring 示例、同文件测试调用和历史记录引用。
- 新增 / 改动 private callable：`_build_dynamic_matmul_loop_local_scratch_module()`；有效代码行 `55`，无 private-call-private。
- 保留依据：helper 承载动态 matmul M/N/K 三层 loop、四类 scratch、fill/matmul/binary/free 构造，直接内联会降低测试断言可读性；当前作为同文件私有 helper 保留依据充分。

执行记录核对：
- 返工记录包含执行前阅读、最小功能闭环、Diff 反推自测、减法检查、自检、主仓只读 expectation 导入边界和敏感目录空 diff。
- 前次 review 的唯一阻断项已按最小动作修复，未扩大任务范围。

自检：
- 特殊情况：历史同文件非下划线测试 helper 未作为本任务阻断；本轮只复审新增/改动 helper。
- 完整性：已核对 helper 命名、私有套私有、pytest、expectation、diff check、敏感目录和记录完整性。
- 维护性：新增 helper 现在符合内部 helper 边界，后续跨文件误用风险降低。
- 测试有效性：目标 pytest 会在 helper调用未同步、alloc/free 未外提或计算 op 被错误移动时失败。

结论：复审通过。该任务为非计划级 review，可按流程续接 `merge`；不得修改 `expectation/.skills/agents/standard`。

时间：2026-05-24 21:58 +0800
经办人：李白
任务：T-20260524-192177b2 / symbol-buffer-hoist-dynamic-matmul-alloc-hoist / merge
任务目标：合入已复审通过的 symbol-buffer-hoist 动态 matmul alloc/free 外提 spec、公开 pytest 与同批任务记录，保持 `expectation/.skills/agents/standard` 空 diff。

merge 前同步与范围核对：
- 已按李白角色提示词、`AGENTS.md`、`agents/standard/合并规范.md` 与 `agents/standard/任务记录约定.md` 执行，只做合并与同步确认，不补实现、不改测试口径。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist`。
- `git fetch --prune origin` 后核对：主仓 `HEAD=origin/main=403a05870b763a4ad8ba2869e4f6220ef5eabd90`；任务 worktree `HEAD=origin/main=merge-base=403a05870b763a4ad8ba2869e4f6220ef5eabd90`，ahead/behind=`0/0`，无 latest-main 覆盖风险。
- 合并候选文件：`spec/pass/symbol_buffer_hoist.md`、`test/passes/test_symbol_buffer_hoist.py` 与本任务记录。
- 候选 diff 不包含实现改动；execute 记录说明 latest main 的 `SymbolBufferHoistPass` 已满足目标 expectation，本轮只补 spec 与公开 pytest 证据链。
- 禁止修改面核对：`expectation/`、`.skills/`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`ARCHITECTURE/plan` 均无候选 diff；ignored `.pytest_cache` / `__pycache__` 为验证产物，不纳入提交。

Diff 反推自测与合并门禁：
- `python3 -m py_compile test/passes/test_symbol_buffer_hoist.py kernel_gen/passes/symbol_buffer_hoist.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_dynamic_matmul_loop_local_scratch_allocs`：exit=0，`1 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_symbol_buffer_hoist.py`：exit=0，`42 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`：exit=0，输出 `[pass-symbol_buffer_hoist-dynamic_matmul_alloc-upper_bound_scratch-1]`。
- `sha256sum /home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`：`fb04b2f803d4fee285cfb507bf8aef8c901d59e0ed81823548c1114320d09458`。
- 导入边界证明：首次未设置 `PYTHONPATH` 的 `importlib.util.find_spec(...)` 命令因找不到 `expectation.pass` 失败；随后按任务口径使用 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist:/home/lfr/kernelcode_generate` 重跑成功，确认 `expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py`，`kernel_gen.passes.symbol_buffer_hoist` 来自任务 worktree。
- `git diff --check && git diff --cached --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan` 均无输出。
- 私有 helper 核验：`_build_dynamic_matmul_loop_local_scratch_module` 有效语句数 `33`，`private_calls=[]`；静态扫描 `git diff -- '*.py' | rg 'hasattr\\(|getattr\\(|callable\\(|VerifyException|__import__|object\\b' || true` 无输出。

真实收口结论：
- 复审结论为通过；前次阻断的非下划线测试 helper 已收口为单下划线私有 helper，且无 private-call-private。
- 本次 merge 只合入已复审通过的 spec、公开 pytest 和任务记录；不合入 `expectation/.skills/agents/standard` 或状态文件。
- 最小阻断项：无。

时间：2026-05-24 21:51 CST
经办人：提莫炖蘑菇
任务：T-20260524-192177b2 / 状态流转
任务目标：按复审通过结论续接 `merge`，并回报管理员。
改动：
- 未修改业务代码、spec、测试、expectation、.skills 或 agents/standard。
- 已在主仓执行 `-next -auto -type merge`。
验证：
- 命令：`bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -next -auto -task_id T-20260524-192177b2 -from 提莫炖蘑菇 -type merge -message "merge；任务目标：合入已复审通过的 symbol-buffer-hoist 动态 matmul alloc/free 外提 spec/公开 pytest 与任务记录，保持 expectation/.skills/agents/standard 空 diff；任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260524-symbol-buffer-hoist-dynamic-matmul-alloc-hoist.md" -agents-list agents/codex-multi-agents/agents-lists.md`
- 结果：exit=0；`OK: next T-20260524-192177b2`、`OK: auto-dispatch T-20260524-192177b2 -> 李白`、`OK: talk 提莫炖蘑菇 -> 李白`、`OK: talk 提莫炖蘑菇 -> 神秘人`。
- TODO 核对：`rg -n "T-20260524-192177b2" TODO.md` 显示任务类型为 `merge`、指派为 `李白`、状态为 `进行中`。
自检：
- 流程：非计划级 review 通过后续接 merge；本人未承接合并。
- 记录：已写清复审结论、验证命令、Diff 反推审查、减法审查、敏感目录空 diff和下一阶段。
结论：T-20260524-192177b2 已续接 `merge / 李白 / 进行中`。
