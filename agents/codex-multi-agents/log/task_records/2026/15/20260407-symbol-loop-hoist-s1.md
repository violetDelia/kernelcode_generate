# 20260407-symbol-loop-hoist-s1

时间：2026-04-07 09:10:00 +0800
经办人：朽木露琪亚
任务：T-20260407-5a079a21（symbol_loop_hoist_green_plan-S1-收口）
任务目标：
- 新增 `symbol-loop-hoist` pass，仅处理 `symbol.for`，把 loop 内仅依赖 loop 外 SSA 的对象外提到 `symbol.for` 之前。
- 新增并补齐以下交付物：`spec/pass/lowering/symbol_loop_hoist.md`、`kernel_gen/passes/lowering/symbol_loop_hoist.py`、`test/pass/test_symbol_loop_hoist.py`、`expectation/pass/lowing/symbol_loop_hoist/basic.py`。
- 在 `PassManager` 增补 `symbol-loop-hoist` 的顺序约束，并补对应测试用例。
改动：进行中（记录文件创建）
结论：进行中（待补齐实现/测试/验证命令证据）

时间：2026-04-07 09:35:00 +0800
经办人：朽木露琪亚
任务：T-20260407-5a079a21（symbol_loop_hoist_green_plan-S1-收口）
任务目标：
- 完成 `symbol-loop-hoist` 的 spec+实现+测试+expectation，并补齐 `PassManager` 顺序约束与测试证据。
改动：
- 新增 spec：`spec/pass/lowering/symbol_loop_hoist.md`
- 新增实现：`kernel_gen/passes/lowering/symbol_loop_hoist.py`
- 新增测试：`test/pass/test_symbol_loop_hoist.py`
- 新增 expectation：`expectation/pass/lowing/symbol_loop_hoist/basic.py`
- 修改 `PassManager` 顺序约束与测试：
  - `kernel_gen/passes/pass_manager.py`
  - `test/pass/test_pass_manager.py`
验证命令与结果摘要：
- `pytest -q test/pass/test_symbol_loop_hoist.py`：exit=0（4 passed）
- `pytest -q test/pass/test_pass_manager.py -k "symbol_loop_hoist or split or dma"`：exit=0（9 passed, 8 deselected）
- `PYTHONPATH=. python expectation/pass/lowing/symbol_loop_hoist/basic.py`：exit=0（打印 before/after IR，after 中 invariant ops 移到 `symbol.for` 之前）
结论：
- 已按计划书 S1 完成收口交付物与验证证据；`PassManager` 已加入 `symbol-loop-hoist` 与 `kernel-split/lower-dma-memory-hierarchy` 的顺序约束，并有用例覆盖。

时间：2026-04-07 10:00:00 +0800
经办人：不要啊教练
任务：T-20260407-5c465e82（symbol_loop_hoist_green_plan-S1-审查）
任务目标：
- 复核 `symbol-loop-hoist` 的 spec/实现/测试/expectation 一致性，以及 `PassManager` 的顺序约束与测试覆盖是否形成可复现证据链。
改动：
- 仅审查与复跑验证命令；未修改 spec/实现/测试。
- `git diff --name-only`（工作区未提交差异）显示仅：
  - `kernel_gen/passes/pass_manager.py`
  - `test/pass/test_pass_manager.py`
结论：需修改

问题清单：
- P1（spec/实现一致性）`spec/pass/lowering/symbol_loop_hoist.md` 的“失败短语”列表包含多条前缀（`SymbolLoopHoistDependsOnLoopIV` / `SymbolLoopHoistAllocReuseUnsafe` / `SymbolLoopHoistAllocDependsOnLoopIV` / `SymbolLoopHoistDominanceError` 等），但在 `kernel_gen/passes/lowering/symbol_loop_hoist.py` 中未找到对应显式失败分支（当前仅看到 `SymbolLoopHoistSideEffectOp` / `SymbolLoopHoistAllocLifetimeUnsafe` / `SymbolLoopHoistFixedReadSourceMutated` / `SymbolLoopHoistFixedReadResultRewritten` / `SymbolLoopHoistVerifierError` 相关抛错路径）。风险：spec 合同与实现行为不一致，后续读者可能误判“哪些场景会显式失败/哪些场景只是 no-op”，也会导致测试目标无法闭环。建议：二选一收敛口径（更新 spec 仅列出当前实现可触发且承诺稳定的短语；或补齐实现让 spec 中列出的短语都可触发，并补测试锁定）。
- P1（测试覆盖）`test/pass/test_symbol_loop_hoist.py` 目前仅锁定了 `SymbolLoopHoistSideEffectOp` 与 `SymbolLoopHoistVerifierError` 两条失败前缀；但实现里已有 `AllocLifetimeUnsafe` / `FixedReadSourceMutated` / `FixedReadResultRewritten`，spec 也明确要求这些短语可稳定匹配。风险：错误文案/拒绝路径回归时难以被及时发现。建议：新增最小负例分别触发并断言上述三条前缀。
- P2（元信息完整性）`test/pass/test_symbol_loop_hoist.py` 文件头 “当前覆盖率信息” 仍为 `待补充`。风险：与仓库对文件头元信息的约定不一致，影响可维护性与审计。建议：补齐该字段（或按统一格式给出当前覆盖率与生成方式）。

漏洞排查结果（本次基于代码与测试的静态复核）：
- 输入校验绕过：未见明确绕过点，但 spec/实现对“显式失败 vs no-op”的边界不一致，可能掩盖异常输入场景。
- 类型/形状绕过：外提白名单主要覆盖符号/shape 构造；缺少对更多拒绝路径的测试锁定，回归检测不足。
- 边界越界：未发现直接越界写入相关实现；但涉及 `dma.alloc` 生命周期与只读窗口假设，需更充分的负例覆盖降低回归风险。
- 错误处理缺失：存在（spec 承诺的错误短语未全部可触发/未全部有测试）。
- 状态污染：未发现全局状态写入；但 pass 为就地改写，若顺序约束误用应保证 fail-fast（目前 PassManager 已在 run 前做顺序检查）。
- 资源释放问题：实现对 “alloc 在 loop 内 free” 有显式拒绝，但缺少对应测试用例锁定错误短语。

验证命令（复跑）与关键输出：
- `PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py`：exit=0（`4 passed in 0.25s`）
- `PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k "symbol_loop_hoist or split or dma"`：exit=0（`9 passed, 8 deselected in 0.25s`）
- `PYTHONPATH=. python expectation/pass/lowing/symbol_loop_hoist/basic.py`：exit=0（打印 before/after；after 中 `symbol.get_dim`/`dma.alloc`/`dma.slice` 均出现在 `symbol.for` 之前，loop 体为空）

下一步建议：
- 派生唯一“改进 spec/实现/测试”任务：收敛失败短语合同并补齐负例测试覆盖（至少覆盖 `AllocLifetimeUnsafe` / `FixedReadSourceMutated` / `FixedReadResultRewritten`），同时补齐 `test/pass/test_symbol_loop_hoist.py` 文件头覆盖率字段；复核通过后再进入合并收口。

时间：2026-04-07 10:15:00 +0800
经办人：朽木露琪亚
任务：T-20260407-9ad8d679（symbol_loop_hoist_green_plan-S1-收口修复）
任务目标：
- 对齐 `symbol-loop-hoist` 的失败短语合同（spec 与实现一致）。
- 增补 `test/pass/test_symbol_loop_hoist.py` 负例，稳定断言 `AllocLifetimeUnsafe` / `FixedReadSourceMutated` / `FixedReadResultRewritten`。
- 补齐 `test/pass/test_symbol_loop_hoist.py` 文件头覆盖率字段。
改动：
- 更新 spec（收敛失败短语列表，仅保留当前实现/PassManager 可稳定触发的前缀，并补齐用例清单）：
  - `spec/pass/lowering/symbol_loop_hoist.md`
- 增补负例与覆盖率字段：
  - `test/pass/test_symbol_loop_hoist.py`
验证命令与结果摘要：
- `PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py`：exit=0（7 passed）
- `PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist`：exit=0（3 passed, 14 deselected）
- `PYTHONPATH=. pytest -q --cov=kernel_gen.passes.lowering.symbol_loop_hoist --cov-branch --cov-report=term-missing test/pass/test_symbol_loop_hoist.py`：exit=0（覆盖率 80%）
结论：
- spec 的失败短语合同已与实现对齐；负例测试已补齐并锁定关键短语；测试文件头覆盖率字段已补齐并给出复现命令。

时间：2026-04-07 10:30:00 +0800
经办人：不要啊教练
任务：T-20260407-46cda3b8（symbol_loop_hoist_green_plan-S1-复审）
任务目标：
- 复核 T-20260407-9ad8d679 的修复是否已收敛失败短语合同，并补齐 `TC-SLH-004..007` 负例与 `test/pass/test_symbol_loop_hoist.py` 文件头覆盖率字段。
改动：
- 仅复审与复跑验证命令；未修改 spec/实现/测试。
结论：通过

复核要点与结论：
- 失败短语合同已收敛：`spec/pass/lowering/symbol_loop_hoist.md` 的失败短语列表已与 `kernel_gen/passes/lowering/symbol_loop_hoist.py` / `kernel_gen/passes/pass_manager.py` 实际显式失败路径一致（并且在测试中有稳定匹配覆盖）。
- 负例用例已补齐：`test/pass/test_symbol_loop_hoist.py` 已新增并标注 `TC-SLH-004..007`，分别稳定断言：
  - `SymbolLoopHoistAllocLifetimeUnsafe`
  - `SymbolLoopHoistFixedReadResultRewritten`
  - `SymbolLoopHoistFixedReadSourceMutated`
  - `SymbolLoopHoistVerifierError`
- 文件头覆盖率字段已补齐：`test/pass/test_symbol_loop_hoist.py` 文件头 “当前覆盖率信息” 不再为占位文本，且给出可复现的覆盖率命令。

验证命令（复跑）与关键输出：
- `PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py`：exit=0（`7 passed in 0.30s`）
- `PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist`：exit=0（`3 passed, 14 deselected in 0.24s`）
