时间：2026-04-06 00:25:55 +0800
经办人：咯咯咯
任务：T-20260406-84773268
任务目标：按 `ARCHITECTURE/plan/kernel_split_pass_green_plan.md#S1` 在 `spec/pass/lowering/kernel_split.md` 冻结 kernel split pass 的公开合同，明确 `tuner.param` 驱动 tile、单函数合同、中间值物化规则、失败边界与错误短语。
改动：新增 `spec/pass/lowering/kernel_split.md`；冻结 `KernelSplitPass` 的公开名称为 `kernel-split`，并约束 split marker 写法为 `kernel_split = { axis = <i64>, tile = "<TILE_NAME>" }`；明确 `kernel_split.tile` 负责声明 tile 名称，由 pass 在函数体内插入或复用同名 `tuner.param` 作为 tile 因子；明确切分后必须保持单个 `func.func`，禁止新增 `func.func` / `func.call` / helper 函数承接 tile；明确中间值仅在同一 split body 内可保留为 SSA，跨 stage / 写回边界 / 多次 `outs` 工作区必须物化为 carry memory；固定失败边界与关键短语为 `KernelSplitMissingTrigger`、`KernelSplitMissingTileParam`、`KernelSplitRequiresLoweredKernelIR`、`KernelSplitRequiresOutParamsABI`、`KernelSplitAxisMismatch`、`KernelSplitUnexpectedFuncExtraction`、`KernelSplitIntermediateMaterializationError`、`KernelSplitDeadCarryMemory`、`KernelSplitVerifierError`；执行 gate `pytest -q test/pass/test_lowering_kernel_split.py`，结果为失败：仓库中缺少该测试文件，`pytest` 返回 `ERROR: file or directory not found: test/pass/test_lowering_kernel_split.py`。
结论：spec 已按 S1 收口完成；本次仅修改 `spec/pass/lowering/kernel_split.md` 与记录文件。gate 未通过的原因是目标测试文件在当前仓库中不存在，且本任务边界不允许补测；需在后续审查中显式核对该测试缺口并决定后续实现/补测链路。
时间：2026-04-06 00:34:30 +0800
经办人：不要啊教练
任务：T-20260406-a2245d20
任务目标：从严审查 `spec/pass/lowering/kernel_split.md` 的公开合同完整性，并核对 gate/证据是否足以支撑 S1 通过。
改动：
- 范围核对：`git status --short` 仅出现 `spec/pass/lowering/kernel_split.md` 与同链记录文件，符合 spec-only 任务边界，未发现额外越界文件。
- 合同审查：spec 已显式冻结 `kernel_split = { axis = <i64>, tile = "<TILE_NAME>" }` 触发写法、`tuner.param` 驱动 tile、单函数合同、中间值 SSA / carry memory 物化规则，以及 `KernelSplitMissingTrigger` / `KernelSplitMissingTileParam` / `KernelSplitRequiresLoweredKernelIR` / `KernelSplitRequiresOutParamsABI` / `KernelSplitAxisMismatch` / `KernelSplitUnexpectedFuncExtraction` / `KernelSplitIntermediateMaterializationError` / `KernelSplitDeadCarryMemory` / `KernelSplitVerifierError` 等失败关键字；针对本轮关注点，公开合同本身未发现新增歧义。
- 证据核对：spec 文档把 gate 固定为 `pytest -q test/pass/test_lowering_kernel_split.py`，但当前 worktree 中 `test/pass/test_lowering_kernel_split.py` 不存在；同时 `kernel_gen/passes/lowering/kernel_split.py` 也不存在，spec 中“功能实现/测试文件”链接尚无对应实体文件，当前无法形成可复现 gate 证据。
- 风险评估：由于实现与测试文件均缺失，当前无法验证输入校验绕过、类型/形状绕过、边界越界、错误处理缺失、状态污染、资源释放问题等 6 类风险是否被实现与测试覆盖；证据链存在 P1 缺口。
结论：需修改。问题列表：
- 文件/接口：`spec/pass/lowering/kernel_split.md` / `kernel_gen/passes/lowering/kernel_split.py` / `test/pass/test_lowering_kernel_split.py`；现象：spec 已冻结合同，但引用的实现文件与 gate 测试文件在当前仓库均不存在，导致 `pytest -q test/pass/test_lowering_kernel_split.py` 不可执行；风险：S1 无法提供可复现验证证据，后续实现可能偏离已冻结错误短语与单函数/物化合同；建议：派生唯一“实现+补测”任务，允许新增 `kernel_gen/passes/lowering/kernel_split.py`、`test/pass/test_lowering_kernel_split.py`，必要时最小同步 `spec/pass/lowering/kernel_split.md` 与同链记录，并以 `pytest -q test/pass/test_lowering_kernel_split.py` 形成首个可执行 gate；优先级：P1。
- 漏洞排查结果：因缺少实现与测试，6 类风险均无法闭环验证，当前不得判定通过。
- 改进建议：无额外建议；当前唯一必须项是补齐实现与测试证据链。
时间：2026-04-06 01:00:41 +0800
经办人：小李飞刀
任务：T-20260406-f021bcd7
任务目标：在 `wt-20260406-kernel-split-s1` 补齐 `kernel_gen/passes/lowering/kernel_split.py` 与 `test/pass/test_lowering_kernel_split.py`，按非计划书实现+补测任务执行，并确保实现/测试严格对齐已冻结 `spec/pass/lowering/kernel_split.md` 合同与 gate `pytest -q test/pass/test_lowering_kernel_split.py`。
改动：新增 `kernel_gen/passes/lowering/kernel_split.py`，实现 `KernelSplitPass` / `KernelSplitError`、`kernel_split` marker 解析、`tuner.param` bridge、`symbol.for` 显式 split body 重写，以及 `KernelSplitMissingTrigger` / `KernelSplitMissingTileParam` / `KernelSplitRequiresLoweredKernelIR` / `KernelSplitRequiresOutParamsABI` / `KernelSplitAxisMismatch` / `KernelSplitUnexpectedFuncExtraction` / `KernelSplitIntermediateMaterializationError` / `KernelSplitDeadCarryMemory` / `KernelSplitVerifierError` 等关键短语；新增 `test/pass/test_lowering_kernel_split.py`，补齐 9 个测试覆盖 `tuner.param` 驱动 tile、单函数显式 split body、非法 tile、func.call、未物化中间值、残留 `nn.*`、dead carry、缺少 trigger、axis 越界等路径；同步在测试文件头记录覆盖率命令结果 `pytest --cov=kernel_gen.passes.lowering.kernel_split --cov-report=term-missing -q test/pass/test_lowering_kernel_split.py` 为 `91%`（`9 passed`）；执行 gate `pytest -q test/pass/test_lowering_kernel_split.py`，结果 `9 passed`、exit=0。
结论：T-20260406-f021bcd7 已完成实现与补测；当前 worktree 具备可复现 gate 证据，后续需进入唯一复审任务继续从严核对错误短语、边界覆盖与 diff 范围。
时间：2026-04-06 01:28:59 +0800
经办人：提莫炖蘑菇
任务：T-20260406-9cd524f9
任务目标：按 `ARCHITECTURE/plan/kernel_split_pass_green_plan.md#S1` 审查 `spec/pass/lowering/kernel_split.md`、`kernel_gen/passes/lowering/kernel_split.py`、`test/pass/test_lowering_kernel_split.py` 一致性，复核边界/异常路径与潜在漏洞，并验证 gate 证据。
改动：
- 范围核对：仅 `spec/pass/lowering/kernel_split.md`、`kernel_gen/passes/lowering/kernel_split.py`、`test/pass/test_lowering_kernel_split.py` 与同链记录文件处于变更集。
- 一致性核对：spec 规定的 `kernel_split` marker、`tuner.param` 驱动、单函数合同、carry memory 物化与错误关键字已在实现/测试中出现并可定位。
- gate 复跑：`PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py`，`9 passed`，exit=0。
结论：需修改。
问题清单：
- [P1] 文件/接口：`kernel_gen/passes/lowering/kernel_split.py`；现象：输入合同仅拒绝 `nn.*` 与 `func.call`，未拒绝其他非 `kernel/dma/func` 子集 op；风险：与 spec“已 lower 到 kernel/dma/func 子集”合同不一致，存在输入校验绕过与语义漂移；建议：补齐非允许 op 的显式拒绝（含错误短语稳定），并新增对应负例测试。
- [P1] 文件/接口：`kernel_gen/passes/lowering/kernel_split.py`；现象：`axis` 校验仅基于首个 `nn.memory` 参数，未验证其它 memory 参数维度一致性；风险：多 `nn.memory` 且 rank 不一致时可能接受非法轴并生成错误 split loop；建议：对所有 `nn.memory` 参数执行一致性校验（rank/axis），或明确 spec 以固定参考 memory，并补测覆盖。
- [P2] 文件/接口：`test/pass/test_lowering_kernel_split.py`；现象：缺少 `axis < 0`、`axis` 非 int、函数无 `nn.memory` 参数等边界负例；风险：边界行为未被回归锁定；建议：补充最小负例测试并固定错误短语。
漏洞排查结果：
- 输入校验绕过：未闭环（存在非允许 op 未拒绝路径）。
- 类型/形状绕过：未闭环（多 memory rank 一致性未校验）。
- 边界越界：部分覆盖（axis 超界有测，负值/非 int 未测）。
- 错误处理缺失：未发现新增异常路径缺口。
- 状态污染：未发现证据。
- 资源释放问题：不适用（纯 IR 变换）。
验证命令：`PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py`
关键输出：`9 passed in 0.38s`
下一步建议：派生唯一“实现+补测修复”任务，补齐输入合同校验与边界负例测试，修复后复审再考虑合并。
时间：2026-04-06 01:48:50 +0800
经办人：提莫炖蘑菇
任务：T-20260406-e7dedbb9
任务目标：按 `ARCHITECTURE/plan/kernel_split_pass_green_plan.md#S1` 复审 `kernel_split` 输入合同补强（allowlist、multi-nn.memory 一致性、axis 边界负例）与 gate 证据。
改动：
- 范围核对：仅 `spec/pass/lowering/kernel_split.md`、`kernel_gen/passes/lowering/kernel_split.py`、`test/pass/test_lowering_kernel_split.py` 与同链记录文件处于变更集。
- 逻辑核对：实现新增 allowlist（`kernel/dma/func.return + tuner.param/symbol.get_dim`）、多 `nn.memory` rank/axis 一致性校验、axis 非法/无 memory fail-fast；测试新增 TC-KS-010~014 覆盖 unsupported op、rank 不一致、axis<0、axis 非 int、无 memory。
- gate 复跑：`PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py`，`14 passed`，exit=0。
结论：需修改。
问题清单：
- [P1] 文件/接口：`spec/pass/lowering/kernel_split.md` vs `kernel_gen/passes/lowering/kernel_split.py`；现象：spec 前置条件仅声明输入为 `kernel/dma/func` 子集，但实现/测试允许 `symbol.get_dim`（用于 `dma.alloc` 动态 shape）与 `tuner.param` 作为输入 op；风险：spec/实现/测试合同不一致，输入校验边界不清，后续链路可能误判允许子集；建议：在 spec 明确允许 `symbol.get_dim`/`tuner.param` 作为输入桥接 op（或反向收紧实现/测试，改用 symbol 字面量并拒绝 symbol.get_dim），并同步错误短语说明。
漏洞排查结果：
- 输入校验绕过：存在合同口径不一致（允许子集定义不清），未闭环。
- 类型/形状绕过：已覆盖（多 `nn.memory` rank/axis 一致性校验 + 负例）。
- 边界越界：已覆盖（axis 越界/负值/非 int/无 memory 负例）。
- 错误处理缺失：未发现新增缺口。
- 状态污染：未发现证据。
- 资源释放问题：不适用（纯 IR 变换）。
验证命令：`PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py`
关键输出：`14 passed in 0.32s`
下一步建议：派生唯一“spec 修订或实现收紧”任务，明确允许子集口径并同步实现/测试，修复后再复审合并。
时间：2026-04-06 01:42:29 +0800
经办人：小李飞刀
任务：T-20260406-3f6cd60a
任务目标：按 `ARCHITECTURE/plan/kernel_split_pass_green_plan.md#S1` 修复 `KernelSplitPass` 输入合同校验缺口，补齐“拒绝非 kernel/dma/func 允许子集 op、多 `nn.memory` rank/axis 一致性、axis<0/非 int/无 nn.memory”边界负例，并保持 gate `PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py` 全绿。
改动：更新 `kernel_gen/passes/lowering/kernel_split.py`：新增输入 allowlist fail-fast，除 `kernel.*` / `dma.*` / `func.return` 外，仅允许 split 所需 `tuner.param` 与 `symbol.get_dim`；对其它 op 统一抛 `KernelSplitRequiresLoweredKernelIR`。同时把 axis 推导从“首个 `nn.memory`”改为“收集全部 `nn.memory` 参数并校验 rank/axis 一致性”，对无 `nn.memory`、负轴、非整型轴、跨参数 rank 不一致或越界统一抛 `KernelSplitAxisMismatch`。更新 `test/pass/test_lowering_kernel_split.py`：把 `dma.alloc` 测试构造改为真实 `symbol.get_dim` dynamic_shape，新增 5 条负例覆盖 unsupported op、multi-memory rank mismatch、axis<0、axis 非 int、无 `nn.memory` 参数，并把文件头覆盖率信息更新为 `94%` / `14 passed`。
结论：T-20260406-3f6cd60a 已完成实现与补测；gate `PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py` 结果为 `14 passed`、exit=0，附加覆盖率命令 `PYTHONPATH=. pytest --cov=kernel_gen.passes.lowering.kernel_split --cov-report=term-missing -q test/pass/test_lowering_kernel_split.py` 结果为 `94%`、`14 passed`、exit=0。改动文件：`kernel_gen/passes/lowering/kernel_split.py`、`test/pass/test_lowering_kernel_split.py`、`agents/codex-multi-agents/log/task_records/2026/14/20260406-kernel-split-s1.md`。验证命令：`PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py`；退出码：`0`；关键输出：`14 passed in 0.34s`。验证命令：`PYTHONPATH=. pytest --cov=kernel_gen.passes.lowering.kernel_split --cov-report=term-missing -q test/pass/test_lowering_kernel_split.py`；退出码：`0`；关键输出：`kernel_gen/passes/lowering/kernel_split.py 94%`、`14 passed in 0.78s`。已知风险：`tuner.param` / `symbol.get_dim` 被视为 split 所需桥接辅助 op，后续审查需继续核对该 allowlist 与冻结 spec 口径是否完全一致。下一步建议：派生唯一审查任务，重点复核新增 fail-fast allowlist、多 memory rank/axis 一致性错误短语与 14 条测试证据是否足以支撑通过。

时间：2026-04-06 01:52:07 +0800
经办人：咯咯咯
任务：T-20260406-2a7112f3
任务目标：修复 `spec/pass/lowering/kernel_split.md` 的输入允许子集合同，使其与同链实现/测试对 `tuner.param` / `symbol.get_dim` 作为 bridge op 的口径保持一致。
改动：
- 选择最小改动方案 A：扩展 spec 的“允许输入子集”，显式纳入 `tuner.param` / `symbol.get_dim`。
- 在术语中新增 `bridge op` 定义，明确二者仅用于 tile 参数或动态 shape 的桥接辅助，不改变核心 split 作用对象。
- 在限制与边界、前置条件、`run(module)` 参数说明与注意事项中同步允许子集口径：核心计算/搬运 op 仍限定为 `kernel.*` / `dma.*` / `func.return`，仅额外允许 `tuner.param` / `symbol.get_dim` 保留输入。
- 保持错误短语不变，仅把 `KernelSplitRequiresLoweredKernelIR` 的失败口径补全为“除 `tuner.param` / `symbol.get_dim` 外仍存在未满足允许子集的 op”。
结论：spec 已与同链实现/测试的 allowlist 口径对齐；本次仅修改 `spec/pass/lowering/kernel_split.md` 与记录文件，未改实现、未改测试、未运行 pytest（spec-only）。
收口的合同：
- `KernelSplitPass` 输入允许子集固定为：`kernel.*` / `dma.*` / `func.return` 核心子集，加上仅作桥接用途的 `tuner.param` / `symbol.get_dim`。
- `tuner.param` / `symbol.get_dim` 不是核心 split 作用对象；前者用于 tile 参数桥接，后者用于动态 shape 维度桥接。
- 对除上述桥接 op 之外的其它非允许子集 op，仍统一以 `KernelSplitRequiresLoweredKernelIR` 失败。
边界：
- 不改动 `kernel_gen/passes/lowering/kernel_split.py` 与 `test/pass/test_lowering_kernel_split.py`。
- 不新增新的 bridge op，也不放宽 `func.*` 为任意 `func` 方言 op；公开合同仍只接受 `func.return`。
拒绝路径：
- 输入残留 `nn.*` 时必须以 `KernelSplitRequiresLoweredKernelIR` 失败。
- 输入包含除 `tuner.param` / `symbol.get_dim` 外的其它非允许子集 op 时，仍必须以 `KernelSplitRequiresLoweredKernelIR` 失败。
引用文件：
- `spec/pass/lowering/kernel_split.md`
- `kernel_gen/passes/lowering/kernel_split.py`
- `test/pass/test_lowering_kernel_split.py`
- `agents/codex-multi-agents/log/task_records/2026/14/20260406-kernel-split-s1.md`
下游影响：
- 后续审查可直接按 bridge op allowlist 复核 spec/实现/测试一致性，无需再把 `symbol.get_dim` / `tuner.param` 视为合同外输入。
下一步建议：
- 派生唯一审查任务，复核 bridge op allowlist、错误短语与 14 条 gate 证据是否一致。

时间：2026-04-06 02:02:17 +0800
经办人：提莫炖蘑菇
任务：T-20260406-da64cc98
任务目标：按 `ARCHITECTURE/plan/kernel_split_pass_green_plan.md#S1` 复核 bridge op allowlist（`tuner.param` / `symbol.get_dim`）与 `KernelSplitRequiresLoweredKernelIR` 错误口径在 spec/实现/测试间的一致性，并核对 gate 证据。
改动：
- 范围核对：`git diff --name-only --cached` 仅包含 `spec/pass/lowering/kernel_split.md`、`kernel_gen/passes/lowering/kernel_split.py`、`test/pass/test_lowering_kernel_split.py` 与同链记录文件；`git diff --name-only` 仅包含实现/测试文件。
- 一致性核对：spec 已显式允许 `tuner.param` / `symbol.get_dim` 作为 bridge op；实现 `_is_allowed_input_contract_op` 同步允许 `kernel.*`/`dma.*`/`func.return` + `tuner.param`/`symbol.get_dim`，并对其他 op 统一抛 `KernelSplitRequiresLoweredKernelIR`；测试覆盖 `unsupported op` 与 `nn.*` 负例并匹配同一关键短语。
- 注释与示例核对：`kernel_split.py` 与测试文件均包含中文功能说明/使用示例/关联文件信息，未发现与实现不一致处。
- gate 复跑：`PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py`，`14 passed`，exit=0。
结论：通过。
问题清单：无。
漏洞排查结果：
- 输入校验绕过：已覆盖（allowlist + unsupported op 负例）。
- 类型/形状绕过：已覆盖（多 `nn.memory` rank/axis 一致性校验与负例）。
- 边界越界：已覆盖（axis 超界/负值/非 int/无 memory 负例）。
- 错误处理缺失：未发现新增缺口（错误短语统一由 `KernelSplitError` 抛出）。
- 状态污染：未发现证据（纯 IR 变换）。
- 资源释放问题：不适用（无资源持有）。
改进建议：未发现额外改进点。
验证命令：`PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py`
关键输出：`14 passed in 0.32s`
下一步建议：派生唯一“合并”任务，完成 S1 收口合并。

时间：2026-04-06 02:04:57 +0800
经办人：李白
任务：T-20260406-8fcb4910（kernel_split_pass_green_plan-S1-合并收口）
任务目标：合并 kernel_split S1 的 spec/实现/测试收口变更到 main，并复跑 gate 确认通过；完成后 push(main) 并 cleanup（worktree remove + branch delete）。
改动：合入文件范围（仅以下文件）：
- `kernel_gen/passes/lowering/kernel_split.py`
- `spec/pass/lowering/kernel_split.md`
- `test/pass/test_lowering_kernel_split.py`
- `agents/codex-multi-agents/log/task_records/2026/14/20260406-kernel-split-s1.md`
证据：
- `git diff --name-only`：
  - agents/codex-multi-agents/log/task_records/2026/14/20260406-kernel-split-s1.md
  - kernel_gen/passes/lowering/kernel_split.py
  - spec/pass/lowering/kernel_split.md
  - test/pass/test_lowering_kernel_split.py
- gate：
  - `PYTHONPATH=. pytest -q test/pass/test_lowering_kernel_split.py`
  - 关键输出：`14 passed in 0.32s`；exit=0
结论：gate 通过，可合并收口；合并提交/push/cleanup 证据由合并执行补齐。
