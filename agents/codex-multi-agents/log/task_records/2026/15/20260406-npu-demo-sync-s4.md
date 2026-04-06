时间：2026-04-06 09:45 +0800
经办人：睡觉小分队
任务：T-20260406-30fa897c（npu_demo_parallel_add_sync_green_plan#S4 spec-only）
任务目标：
- 冻结 `gen_kernel(target="npu_demo")` 的完整源码合同：从“仅 body-level 骨架”升级为“launch wrapper + body kernel”的受控 `builtin.module` 子集。
- 明确 body 需生成 `ctx.barrier(...)`，wrapper 需生成 `npu_demo::launch<1, 4, 1>(...)`；并锁定失败边界（禁止 silent fallback）。
改动：
- 更新 `spec/dsl/gen_kernel.md`：补齐 `target="npu_demo"` 的受控 module 输入域、双函数输出形态、barrier/launch 的机械可判定约束；补齐非法样例与必须报错口径；同步更新测试目标与 GK 用例映射（标注为下游待补）。
- gate 证据（本阶段允许失败，失败原因=实现/补测缺口）：
  - `cd wt-20260406-npu-demo-sync-s4 && pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'`：exit=5（无匹配用例，输出 `41 deselected`）
  - `cd wt-20260406-npu-demo-sync-s4 && python expectation/dsl/gen_kernel/npu_demo_add_barrier`：exit=2（文件不存在：`expectation/dsl/gen_kernel/npu_demo_add_barrier`）
结论：
- spec 已按计划书 S4 冻结 `target="npu_demo"` 的完整源码合同；当前 gate 未绿属于实现/测试/expectation 缺口，需派生唯一后续任务“实现+补测”联动落地。

时间：2026-04-06 12:43 +0800
经办人：小李飞刀
任务：T-20260406-daef2300（npu_demo_parallel_add_sync_green_plan#S4-实现+补测）
任务目标：
- 在 `gen_kernel(target="npu_demo")` 落地受控 `builtin.module` 双函数输出：固定生成 `add+barrier` body 与 `launch<1, 4, 1>` wrapper。
- 补齐 `test/dsl/test_gen_kernel.py` 的 `-k 'npu_demo and barrier'` 命中用例，并新增 expectation `expectation/dsl/gen_kernel/npu_demo_add_barrier`。
改动：
- 更新 `kernel_gen/dsl/gen_kernel.py`：新增 `ModuleOp` 入口与 `npu_demo` 受控 module 发射逻辑，固定收口 body/wrapper 分类、launch callee 校验、`1/4/1` extent 校验、双 barrier 可见性/作用域校验，以及 `thread/view/slice/barrier/add/deslice` 骨架输出。
- 更新 `test/dsl/test_gen_kernel.py`：新增 `FakeSymbolValueOp` 与 `_make_npu_demo_add_barrier_module(...)`，补 3 条 `npu_demo + barrier` 测试，覆盖双函数源码形态、编译 smoke、missing body fail-fast。
- 新增 `expectation/dsl/gen_kernel/npu_demo_add_barrier`：独立构造受控 module，并对 `gen_kernel(...)` 输出做整串精确比对。
改动文件：
- `kernel_gen/dsl/gen_kernel.py`
- `test/dsl/test_gen_kernel.py`
- `expectation/dsl/gen_kernel/npu_demo_add_barrier`
- `agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s4.md`
验证命令：
- `cd wt-20260406-npu-demo-sync-s4 && PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'`
- `cd wt-20260406-npu-demo-sync-s4 && PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier`
退出码：
- `0`
- `0`
关键输出：
- `3 passed, 41 deselected in 0.67s`
- expectation 打印完整源码且与预期整串一致，无 AssertionError。
已知风险：
- 当前实现按 S4 冻结合同仅接受固定 `add+barrier` 受控 module 子集；若后续扩展更多 body 形态，需要新增独立任务扩展 matcher/expectation，不应在本任务内放宽。
下一步建议：
- 派生唯一后续任务做审查，重点检查失败短语稳定性、受控 module 子集边界，以及 expectation 是否足以覆盖源码次序与 launch/barrier 细节。
结论：
- 本任务实现与补测已完成，S4 gate 全绿，可进入审查阶段。

时间：2026-04-06 10:29 +0800
经办人：不要啊教练
任务：T-20260406-24b969ba（npu_demo_parallel_add_sync_green_plan#S4-审查）
任务目标：
- 从严核对 `gen_kernel(target="npu_demo")` 是否严格限制受控 `builtin.module`（launch wrapper + body）子集，禁止 silent fallback。
- 复核 body/wrapper 形态、双 `ctx.barrier(...)`、禁止 `ctx.sync_threads(...)` 等失败边界与错误短语是否具备稳定证据。
- 核对 expectation 输出与测试覆盖是否足够、记录中 gate/证据是否完整。
改动：
- 仅追加本次审查记录；未修改 spec / 实现 / 测试。
结论：需修改

两轮核对（按审查规范）：
- 第 1 轮（可执行性证据）：复跑 gate，确认当前实现与正例/expectation 可复现（exit=0）。
- 第 2 轮（边界/一致性证据）：核对 spec↔test 映射与负例/诊断覆盖，发现证据缺口与范围污染风险。

问题清单：
- P1：变更集范围不干净/存在合并漏文件风险。
  - 现象：`git diff --name-only` 存在未暂存的越界修改（含他人 agent 文件与历史 task_records），且 `spec/dsl/gen_kernel.md` 仍为未暂存修改状态。
  - 风险：合并时容易漏掉应合入的 spec 修订，或误把无关文件带入变更集；也会降低复现与回滚可靠性。
  - 建议：实现方必须先清理 worktree（仅保留本链路允许文件），并确保 `git diff --name-only`/`--cached` 范围严格可控；`spec/dsl/gen_kernel.md` 如需更新必须纳入追踪并与测试名一致。
- P1：spec/test 映射不闭环（S4 “待补测试映射”与现状冲突）。
  - 现象：`spec/dsl/gen_kernel.md` 仍写明 “S4 下游待补测试映射/不写成当前已存在可执行测试”，且 GK-017/018 的映射用例名与实际已落地用例名不一致（当前已新增 GK-S4-001..003）。
  - 风险：spec 与事实不一致会导致验收口径漂移；后续审查无法仅凭 spec 确认覆盖闭环。
  - 建议：更新 spec：移除“待补”措辞，将 GK-017/018 映射到实际用例名（或按计划统一重命名用例/条目），并确保测试目标与 gate 可复现一致。
- P1：失败边界/错误短语“稳定性”证据不足（负例覆盖不足）。
  - 现象：当前仅覆盖一条受控 module 负例（wrapper 引用缺失 body symbol）；实现中多条 fail-fast 错误短语未被测试锁定（如：module 顶层非 func、func 数量不为 2、wrapper 非 `arch.launch + func.return`、callee 非 flat、extent 非静态或非 `1/4/1`、barrier scope/visibility 不合法、`target!=npu_demo` 的 module 输入拒绝等）。
  - 风险：回归时可能出现 silent fallback/弱约束放宽、或诊断短语漂移导致定位困难；与 S4 冻结“失败边界短语稳定”口径不满足。
  - 建议：补齐一组负例门禁，逐条锁定关键错误短语（至少覆盖上述类别），并明确“不改变 IR/无副作用”的 fail-fast 行为（对 ModuleOp 输入直接失败）。

漏洞排查结果（最小集）：
- 输入校验绕过：实现对受控 module 做严格结构校验，但缺少测试锁定 → 判定证据不足（需补测）。
- 类型/形状绕过：wrapper/body 签名与固定 pipeline 有显式校验，但缺少负例证据（需补测）。
- 边界越界：本阶段为代码生成合同，主要风险为错误输入被接受并生成错误源码；现有负例不足（需补测）。
- 错误处理缺失：存在稳定短语设计，但未被测试覆盖（需补测）。
- 状态污染：审查未发现显式全局状态写入；但 worktree 污染带来合并状态风险（需清理）。
- 资源释放问题：不适用（纯源码生成链路）；无额外发现。

验证命令：
- `cd wt-20260406-npu-demo-sync-s4 && git diff --name-only --cached`
- `cd wt-20260406-npu-demo-sync-s4 && git diff --name-only`
- `cd wt-20260406-npu-demo-sync-s4 && PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'`
- `cd wt-20260406-npu-demo-sync-s4 && PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier`
退出码：
- `0`
- `0`
关键输出：
- `3 passed, 41 deselected in 0.53s`
- expectation 脚本输出完整源码并通过整串一致性断言（无 AssertionError）。

下一步建议：
- 派生唯一后续“实现+补测+清理”任务：清理越界 diff；对齐 `spec/dsl/gen_kernel.md` 的 S4 映射闭环；补齐受控 module 的 fail-fast 负例门禁并锁定关键错误短语；复跑本阶段 gate（pytest + expectation）并提供 `git diff --name-only` 证据。

时间：2026-04-06 10:41 +0800
经办人：小李飞刀
任务：T-20260406-7c485cd2（npu_demo_parallel_add_sync_green_plan#S4-实现修复）
任务目标：
- 清理 `wt-20260406-npu-demo-sync-s4` 的越界 diff，确保 `git diff --name-only` 与 `git diff --cached --name-only` 仅保留 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py`、`spec/dsl/gen_kernel.md`、`expectation/dsl/gen_kernel/npu_demo_add_barrier` 与记录文件。
- 对齐 `spec/dsl/gen_kernel.md` 的 GK-017/GK-018 测试映射，并补齐受控 `builtin.module` 的 fail-fast 负例门禁与关键错误短语。
改动：
- 恢复 worktree 中与当前链路无关的脏改，当前 diff 范围已收敛到 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py`、`spec/dsl/gen_kernel.md`、`expectation/dsl/gen_kernel/npu_demo_add_barrier` 与记录文件。
- 更新 `kernel_gen/dsl/gen_kernel.py`：`_npu_demo_module_funcs(...)` 先拒绝 module 顶层非 `func.func`，再校验函数数量，保证顶层非 func 的错误短语优先稳定。
- 更新 `test/dsl/test_gen_kernel.py`：扩展 `_make_npu_demo_add_barrier_module(...)` 以构造负例；新增 `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries`，覆盖 module 顶层非 func、func!=2、wrapper 非 `arch.launch+return`、callee 非 flat、extent 非静态/非 `1/4/1`、barrier scope/visibility 非法、以及 `target!=npu_demo` 的 module 输入拒绝。
- 更新 `spec/dsl/gen_kernel.md`：移除 S4 “待补测试映射”措辞，对齐 GK-017/GK-018 到实际用例名，并补充 `GK-S4-003` 的 fail-fast 验收映射。
改动文件：
- `kernel_gen/dsl/gen_kernel.py`
- `test/dsl/test_gen_kernel.py`
- `spec/dsl/gen_kernel.md`
- `expectation/dsl/gen_kernel/npu_demo_add_barrier`
- `agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s4.md`
验证命令：
- `cd wt-20260406-npu-demo-sync-s4 && git diff --name-only && git diff --cached --name-only`
- `cd wt-20260406-npu-demo-sync-s4 && PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'`
- `cd wt-20260406-npu-demo-sync-s4 && PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier`
退出码：
- `0`
- `0`
- `0`
关键输出：
- `git diff --name-only` 为空；`git diff --cached --name-only` 仅剩 `agents/codex-multi-agents/log/task_records/2026/15/20260406-npu-demo-sync-s4.md`、`expectation/dsl/gen_kernel/npu_demo_add_barrier`、`kernel_gen/dsl/gen_kernel.py`、`spec/dsl/gen_kernel.md`、`test/dsl/test_gen_kernel.py`。
- `12 passed, 41 deselected in 0.59s`
- expectation 打印源码并与冻结输出整串一致，无 AssertionError。
已知风险：
- 当前 fail-fast 门禁仍按 S4 冻结的 `add+barrier` 受控子集收口；若后续要放宽到更多 `npu_demo` body 形态，需新开任务同步扩展 matcher、spec 与 expectation。
下一步建议：
- 派生唯一后续审查任务，重点复核新增错误短语是否与 spec 文案完全对齐，以及 diff 收敛后 staged/unstaged 文件是否均满足合并边界。
结论：
- T-20260406-7c485cd2 已完成；越界 diff 已清理，S4 fail-fast 负例门禁已补齐，当前 gate 全绿，可进入复审。

时间：2026-04-06 10:50 +0800
经办人：不要啊教练
任务：T-20260406-3cb915ea（npu_demo_parallel_add_sync_green_plan-S4-审查）
任务目标：
- 从严复核 diff 边界：`git diff --name-only`/`--cached` 仅允许 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py`、`spec/dsl/gen_kernel.md`、`expectation/dsl/gen_kernel/npu_demo_add_barrier` + 记录文件。
- 复核受控 `builtin.module` 的 fail-fast 负例门禁与关键错误短语稳定性是否被测试锁定。
- 复核 `spec/dsl/gen_kernel.md` 中 GK-017/GK-018 映射与实际用例（GK-S4-001..004）是否闭环，且记录中的 gate 证据可复跑。
改动：
- 仅追加本次审查记录；未修改 spec / 实现 / 测试。
结论：通过

两轮核对（按审查规范）：
- 第 1 轮（范围/污染）：`git diff --name-only` 为空；`git diff --name-only --cached` 仅包含允许文件 + 记录文件，满足合并边界要求。
- 第 2 轮（合同/证据）：复跑 gate（pytest + expectation）均 exit=0；并核对 spec↔test 映射与 fail-fast 负例覆盖已闭环。

核对要点结论：
- diff 边界：通过。
- fail-fast 负例与错误短语稳定：通过（`test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries` 已覆盖顶层非 func、func!=2、wrapper 形态、callee flat、extent 静态/`1/4/1`、barrier scope/visibility、以及非 npu_demo target 拒绝等关键短语）。
- spec 映射闭环：通过（`spec/dsl/gen_kernel.md` 的 GK-017/GK-018 已映射到已落地测试用例名，并补充 `GK-S4-003` 的 fail-fast 映射）。
- 记录与 gate 证据：通过（本次复跑结果与记录可复现一致）。

验证命令：
- `cd wt-20260406-npu-demo-sync-s4 && git diff --name-only`
- `cd wt-20260406-npu-demo-sync-s4 && git diff --name-only --cached`
- `cd wt-20260406-npu-demo-sync-s4 && PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo and barrier'`
- `cd wt-20260406-npu-demo-sync-s4 && PYTHONPATH=. python expectation/dsl/gen_kernel/npu_demo_add_barrier`
退出码：
- `0`
- `0`
关键输出：
- `12 passed, 41 deselected in 0.61s`
- expectation 脚本执行成功（exit=0），输出源码与冻结 EXPECTED 整串一致（无 AssertionError）。

下一步建议：
- 派生唯一后续“合并收口”任务给李白：仅合入本链路允许文件 + 记录文件；合并前再核对 `git diff --name-only --cached` 范围，避免误带无关文件。
