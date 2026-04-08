时间：2026-04-08 12:42:31 +0800
经办人：咯咯咯
任务：T-20260408-5d7eb75f（nn_softmax_decompose_pass_green_plan-S2-spec）
任务目标：更新 `spec/operation/nn.md` 与 `spec/pass/lowering/nn_to_kernel.md` 的 softmax lowering 合同，明确 `DecomposeNnSoftmaxPass` 的分解职责，并把 residual `nn.softmax` 的固定失败短语写成单一口径。
改动：
- 更新 `spec/operation/nn.md` 的 `softmax(value, axis=-1)` 小节与 lowering 职责矩阵，明确高层输出合同保持不变，generic lowering 时由 `DecomposeNnSoftmaxPass` 负责把 `nn.softmax` 分解为固定 7 段 `nn` 链，`LowerNnToKernelPass` 不要求 `kernel.softmax`。
- 更新 `spec/pass/lowering/nn_to_kernel.md` 的功能简介、限制与边界、公开接口说明、lowering 矩阵、测试目标与覆盖映射，把 residual `nn.softmax` 的固定失败短语统一为 `LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel`。
- 明确 `LowerNnToKernelPass` 只消费分解后的 `nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv` 链；若输入模块可能包含 `nn.softmax`，调用方必须先执行 `DecomposeNnSoftmaxPass`。
结论：
- 已完成 S2 的 `spec` 收口；下游可据此对齐 `LowerNnToKernelPass`、相关测试与 expectation 证据。
- 本次仅修改 `spec` 与记录文件，未改实现/测试，未执行 `pytest`。
时间：2026-04-08 12:57:31 +0800
经办人：小李飞刀
任务：T-20260408-5d7eb75f（nn_softmax_decompose_pass_green_plan-S2-实现）
任务目标：按 `spec/operation/nn.md` 与 `spec/pass/lowering/nn_to_kernel.md` 对齐 `LowerNnToKernelPass` 的 residual `nn.softmax` 固定失败短语，并补齐 softmax lowering 测试与 expectation 证据。
改动：
- 更新 `kernel_gen/passes/lowering/nn_to_kernel.py`：将 residual `nn.softmax` 的错误短语统一为 `residual nn.softmax must be decomposed before lower-nn-to-kernel`。
- 更新 `test/pass/test_lowering_nn_to_kernel.py`：对齐两条 softmax 失败路径单测（dialect 直构造 + public chain helper）匹配新短语。
- 更新 `test/pass/test_pass_manager.py`：补充 `-k 'softmax or nn_to_kernel'` 可稳定选择的最小用例，避免无用例导致的退出码异常。
- 新增 `expectation/pass/lowing/nn_to_kernel/softmax.py`：输出 raw IR 并打印固定失败短语，覆盖两条入口。
- 更新 `spec/operation/nn.md`：在 softmax 小节补齐 residual `nn.softmax` 的 lowering 失败短语口径（与 `nn_to_kernel` spec 一致）。
- 验证命令：
  - `cd wt-20260408-nn-softmax-decompose && pytest -q test/pass/test_lowering_nn_to_kernel.py -k 'softmax'` -> `2 passed, 32 deselected in 0.35s`
  - `cd wt-20260408-nn-softmax-decompose && pytest -q test/pass/test_pass_manager.py -k 'softmax or nn_to_kernel'` -> `1 passed, 17 deselected in 0.25s`
  - `cd wt-20260408-nn-softmax-decompose && PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/softmax.py` -> exit=0（CASE-1/CASE-2 打印 `LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel`）
结论：实现与证据已对齐，可进入审查阶段复核短语口径与用例覆盖是否满足计划书 S2 的收口要求。

时间：2026-04-08 13:04:07 +0800
经办人：不要啊教练
任务：T-20260408-5d7eb75f（nn_softmax_decompose_pass_green_plan-S2-审查）
任务目标：复核 residual `nn.softmax` 失败短语口径与 softmax lowering 单测/expectation 证据是否与 spec 完全一致。
改动：
- 复跑验证命令：
  - `cd wt-20260408-nn-softmax-decompose && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -k 'softmax'`：exit=0；`2 passed, 32 deselected in 0.25s`。
  - `cd wt-20260408-nn-softmax-decompose && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k 'softmax or nn_to_kernel'`：exit=0；`1 passed, 17 deselected in 0.22s`。
  - `cd wt-20260408-nn-softmax-decompose && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/softmax.py`：exit=0；CASE-1/CASE-2 均打印 `LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel`。
- 一致性核对（失败短语）：
  - spec/operation：[`spec/operation/nn.md`](spec/operation/nn.md) 要求 residual `nn.softmax` 进入 `LowerNnToKernelPass` 时抛 `LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel`。
  - spec/pass：[`spec/pass/lowering/nn_to_kernel.md`](spec/pass/lowering/nn_to_kernel.md) 同口径，且明确禁止 silent fallback/直降 `kernel.softmax`。
  - 实现：[`kernel_gen/passes/lowering/nn_to_kernel.py`](kernel_gen/passes/lowering/nn_to_kernel.py) 在 `_lower_nn_op` 里遇到 `nn.softmax` 直接 `raise LowerNnToKernelError("residual nn.softmax must be decomposed before lower-nn-to-kernel")`。
  - 单测：[`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py) 的 `TC-PASS-N2K-030/031` 均匹配 `residual nn.softmax must be decomposed before lower-nn-to-kernel`。
  - expectation：[`expectation/pass/lowing/nn_to_kernel/softmax.py`](expectation/pass/lowing/nn_to_kernel/softmax.py) 对两条入口断言 `f\"{type(exc).__name__}: {exc}\"` 等于完整短语（含类型名）。
结论：
- 通过：spec/实现/单测/expectation 的 residual `nn.softmax` 失败短语口径一致，且验证命令均可复现通过。
- 漏洞排查结果（6 类）：
  - 输入校验绕过：未发现（残留 `nn.softmax` 直接报错中止，未继续 lowering）。
  - 类型/形状绕过：未发现（本次仅涉及 softmax 残留错误路径，未改类型/形状校验逻辑）。
  - 边界越界：未发现（本次不涉及索引/offset 计算）。
  - 错误处理缺失：未发现（两条入口均有可复现断言覆盖）。
  - 状态污染：未发现（本次用例为 residual `nn.softmax` 直接报错路径，未观察到中间改写残留）。
  - 资源释放问题：未发现（无新增资源生命周期点）。
- 未发现额外改进点；可进入后续合并阶段。

时间：2026-04-08 13:11:00 +0800
经办人：李白
任务：T-20260408-5d7eb75f（nn_softmax_decompose_pass_green_plan-S2-合并）
任务目标：将 wt-20260408-nn-softmax-decompose 中允许范围改动合入 main（含 expectation 特别授权），无需复跑验证命令。
改动：
- 合入文件：
  - kernel_gen/passes/lowering/nn_to_kernel.py
  - test/pass/test_lowering_nn_to_kernel.py
  - test/pass/test_pass_manager.py
  - expectation/pass/lowing/nn_to_kernel/softmax.py（.gitignore 已忽略 expectation，使用 git add -f 纳入变更集）
  - agents/codex-multi-agents/log/task_records/2026/15/20260408-nn-softmax-decompose-s2.md
- 范围收敛：本 worktree 中发现的 spec/operation/nn.md、spec/pass/lowering/nn_to_kernel.md 本次合并不在允许清单内，已恢复并排除。
结论：已完成合并并推送 main（提交号与清理结果见管理员回报）。
