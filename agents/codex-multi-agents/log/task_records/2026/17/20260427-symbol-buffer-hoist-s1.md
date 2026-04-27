时间：2026-04-27 22:02
经办人：睡觉小分队
任务：T-20260427-799dca63
任务目标：先收 `symbol-buffer-hoist` 的正式 `spec` 与 `registry` 公开面，为下游 `build` 固定公开 API、失败边界和 `pytest` 口径
执行前阅读记录：已读 `TODO.md` 本任务行、[`ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`](../../../../../../../ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 的 `S1` / 完成态 / 验收设计、[`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)、[`spec/pass/symbol_loop_hoist.md`](../../../../../../../spec/pass/symbol_loop_hoist.md)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)、[`expectation/pass/symbol_buffer_hoist/__main__.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/__main__.py)、[`expectation/pass/symbol_buffer_hoist/basic.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/basic.py)、[`expectation/pass/symbol_buffer_hoist/shape_depends_on_loop_carried.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/shape_depends_on_loop_carried.py)；任务点名的 `wt-20260427-symbol-buffer-hoist-s1` 初始不存在，本轮已补建后继续执行
最小功能闭环：新增 [`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md) 收口 pass 名称、公开 API、输入 staging / output scratch / loop-carried shape 三条边界与共享错误口径；更新 [`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md) 补 `symbol-buffer-hoist` 的内建 pass 说明、canonical public path 和 registry 构造示例；不改实现、`pytest` 或 `expectation`
改动：
- 新建 [`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)，把 `SymbolBufferHoistPass`、`DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()` 的公开签名、公开导入面、共享 `PassContractError` 边界和最小改写合同写成单一口径
- 更新 [`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)，补充 `symbol-buffer-hoist` 的内建 pass 说明、`kernel_gen.passes.symbol_buffer_hoist` canonical path、`test_pass_registry.py` 机械验收职责和 `build_registered_pass("symbol-buffer-hoist")` 示例
- 明确本轮不承诺 `kernel_gen.passes.lowering.symbol_buffer_hoist` 之类额外 compat path；下游 `pytest` 只能通过公开 API 观察行为
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1 diff --check`：通过
- `python3` 文本断言脚本：通过；已确认 `API 列表` 紧跟 `功能简介`、`SymbolBufferHoistPass.apply(...)` 与 `DmaAllocInSymbolForHoistPattern.match_and_rewrite(...)` 签名存在、`spec/pass/symbol_buffer_hoist.md` 不包含 `expectation/` 路径、`registry.md` 已出现 `symbol-buffer-hoist` 内建 pass 说明 / canonical path / registry builder 示例
- `rg -n "symbol-buffer-hoist|symbol_buffer_hoist|SymbolBufferHoistPass|DmaAllocInSymbolForHoistPattern" spec/pass/symbol_buffer_hoist.md spec/pass/registry.md`：命中新写入的公开边界与验收说明
Diff 反推自测：本轮 diff 只涉及 [`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)、[`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md) 与当前记录；反推验证采用 `git diff --check` + `python3` 文本断言脚本 + `rg` 关键字核对；未跑 `pytest`，原因：本轮仅做 `spec`，公开 API 对应实现和测试文件仍由下游 `build` 补齐
合同验收（如适用）：未执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist`；原因：本轮只做 `spec`，`expectation/pass/symbol_buffer_hoist/**` 继续只读，合同验收留给下游 `build/review` 单列
自检：已读完整阶段与前序只读资产；只改 `spec` 与任务记录，未越权改实现、测试或 `expectation`；`API 列表` 已紧跟 `功能简介`，公开签名、参数顺序、共享错误口径、输入 staging / output scratch / loop-carried shape 边界、包根 re-export 与 registry 名称都已写清；同时已明确文件内 helper 不是公开 API，后续实现与测试不得跨文件直连；当前文档可直接指导下游 `build` 实现和 `pytest`
结论：当前 `spec` 已完成并写入任务记录；下一步按 `TODO.md` 创建下游 `build` 任务，由实现侧补 `kernel_gen/passes/symbol_buffer_hoist.py`、包导出、registry 接线与只围绕公开 API 的 `pytest`
后续建议：
- `build` 只应新增 `kernel_gen.passes.symbol_buffer_hoist` 子模块、`kernel_gen.passes.SymbolBufferHoistPass` 包根 re-export 和 `build_registered_pass("symbol-buffer-hoist")` 接线，不要顺手再加 `lowering.symbol_buffer_hoist`
- `test/pass/test_symbol_buffer_hoist.py` 只通过 `SymbolBufferHoistPass`、`DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()` 与 registry builder 观察行为，不要直连文件内 helper
- `expectation/pass/symbol_buffer_hoist/**` 继续只读，作为 `build/review` 的合同验收资产单列

时间：2026-04-27 22:06
经办人：金铲铲大作战
任务：T-20260427-799dca63
任务目标：按最新 spec 实现 `symbol-buffer-hoist` pass、包导出、registry 接线与只验证公开 API 的 `pytest`，并单列 `expectation.pass.symbol_buffer_hoist` 合同验收
执行前阅读记录：已读 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`](../../../../../../../ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 的 `S1` / 完成态 / 验收设计、前序任务记录、[`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)、[`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)、[`kernel_gen/passes/symbol_loop_hoist.py`](../../../../../../../kernel_gen/passes/symbol_loop_hoist.py)、[`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)、[`test/pass/test_symbol_loop_hoist.py`](../../../../../../../test/pass/test_symbol_loop_hoist.py)、[`expectation/pass/symbol_buffer_hoist/__main__.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/__main__.py)
最小功能闭环：新增 [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py) 公开 `SymbolBufferHoistPass` / `DmaAllocInSymbolForHoistPattern` / `get_symbol_buffer_hoist_patterns()`，接通 [`kernel_gen/passes/__init__.py`](../../../../../../../kernel_gen/passes/__init__.py) 包根导出与 [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py) 的 `symbol-buffer-hoist` 内建注册，再用 [`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py) 与 [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py) 只从公开入口验证 input staging / output scratch / loop-carried shape / registry 构造与失败前缀
改动：
- 新增 [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py)，实现 `DmaAllocInSymbolForHoistPattern.match_and_rewrite(...)`、`get_symbol_buffer_hoist_patterns()` 与 `SymbolBufferHoistPass.apply(...) / run(...)`；只在当前文件内新增 helper，未跨文件调用非公开 API
- 更新 [`kernel_gen/passes/__init__.py`](../../../../../../../kernel_gen/passes/__init__.py)，补 `SymbolBufferHoistPass`、`DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()` 的包根公开导出与文件级 `API 列表`
- 更新 [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)，把 `symbol-buffer-hoist` 纳入 `load_builtin_passes()` 内建 pass 列表
- 新增 [`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py)，只通过 `kernel_gen.passes.symbol_buffer_hoist`、`kernel_gen.passes`、`kernel_gen.passes.registry` 的公开入口验证行为；测试夹具已改用公开 `SymbolConstOp` / `SymbolYieldOp` 构造，不直连文件内 helper
- 更新 [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)，补 `symbol-buffer-hoist` 的 canonical path / 包根对象身份与旧 `kernel_gen.passes.lowering.symbol_buffer_hoist` fail-fast 断言
验证：
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/kernel_gen/passes/symbol_buffer_hoist.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/kernel_gen/passes/__init__.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_symbol_buffer_hoist.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_pass_registry.py`：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1 diff --check`：通过
Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_symbol_buffer_hoist.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_pass_registry.py -ra`：`43 passed, 1 warning`
合同验收（如适用）：
- 指定命令 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist` 在 `wt-20260427-symbol-buffer-hoist-s1` 内执行结果：失败；原因是该 worktree 不含 `expectation/` 目录，报 `ModuleNotFoundError: No module named 'expectation'`
- 为了用主仓只读 `expectation` 验证本轮代码，补跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`：失败；当前只剩 2 个 immutable 合同资产问题
- `pass-symbol_buffer_hoist-output_scratch-1`：资产文本把 `dma.deslice` 写成 `(%out, %buf, ...)`，在现行 `dma.deslice(source, target, ...)` verifier 下触发 `SymbolBufferHoistVerifierError: dma.deslice result must match target type`
- `pass-symbol_buffer_hoist-shape_depends_on_loop_carried-1`：资产 IR 自身的 `!symbol.int<"...">` 名称不一致，解析阶段即报 `operand is used with type symbol.int<...>, but has been previously used or defined with type symbol.int<...>`
自检：
- 本轮实现文件都已补文件级 `API 列表`，只列公开 API 与签名
- 当前文件之外未调用任何非公开 API；测试也只通过公开包根 / 子模块 / registry 入口观察行为
- `symbol-buffer-hoist` 的 input staging、output scratch、loop-carried shape、非 module 输入与 verifier 前缀都已有公开 `pytest` 覆盖
- 未修改 `expectation/**`；合同验收失败已按 immutable 资产现状单列，没有拿它替代 diff 反推测试
结论：`symbol-buffer-hoist` 的实现、包导出、registry 接线和公开 `pytest` 已完成；当前剩余差异只在 immutable `expectation.pass.symbol_buffer_hoist` 资产本身，已如实单列

时间：2026-04-27 22:27
经办人：提莫炖蘑菇
任务：T-20260427-799dca63
任务目标：复核 `symbol-buffer-hoist` pass、包导出、registry 接线、公开 `pytest` 与合同验收结果。

真实审查：
- 已复核 [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py)、[`kernel_gen/passes/__init__.py`](../../../../../../../kernel_gen/passes/__init__.py)、[`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)、[`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)、[`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)、[`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py) 与只读合同资产 [`expectation/pass/symbol_buffer_hoist/__main__.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/__main__.py)、[`expectation/pass/symbol_buffer_hoist/basic.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/basic.py)、[`expectation/pass/symbol_buffer_hoist/shape_depends_on_loop_carried.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/shape_depends_on_loop_carried.py)。
- 实现 / 包导出 / registry / 公开 `pytest` 这部分本身是闭合的：包根可导入 `SymbolBufferHoistPass`、`DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()`，`build_registered_pass("symbol-buffer-hoist")` 也能返回正确实例。
- 但合同验收没有收口。实际执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist` 失败，不是记录里写的“只剩 immutable 资产两处语义问题”这么简单。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_symbol_buffer_hoist.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_pass_registry.py -ra`
  - 结果：`43 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：失败
  - 失败 1：`pass-symbol_buffer_hoist-basic-1` 与 `pass-symbol_buffer_hoist-output_scratch-1` 实际报 `PassRegistryError: unknown pass 'symbol-buffer-hoist'`
  - 失败 2：`pass-symbol_buffer_hoist-shape_depends_on_loop_carried-1` 仍报输入 IR 自身的 `!symbol.int<...>` 名称不一致解析失败
- `git -C /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1 diff --check`
  - 结果：通过

可改进点 / 阻断项：
- 当前不能给 `通过`，因为计划书把 `python3 -m expectation.pass.symbol_buffer_hoist` 列为 `S1` 验收必过项，但现场没有通过。
- 且 build 记录里把合同验收失败归因为“当前只剩 2 个 immutable 资产问题”并不准确：前两条正例实际先撞到的是 `unknown pass 'symbol-buffer-hoist'`。这说明当前合同验收入口并没有可靠地在本轮 worktree 实现上完成 pass 接线验证，不能算验收闭环。
- 在不允许修改 `expectation/**` 的前提下，至少要先把“当前验收命令如何绑定到本轮 worktree 实现”说明清楚，并修正任务记录中的失败归因；否则这轮 review 不能放行。

自检：
- 已按实际 diff 反推公开 `pytest` 与合同验收命令。
- 已额外检查本轮实现/测试未新增跨文件非公开 API 直连，未发现新的这类问题。
- 本轮未修改 `expectation/**`，只把失败现场如实写回。

结论：
- `需修改`
- 原因：`pytest` 虽然通过，但计划书列出的 `expectation.pass.symbol_buffer_hoist` 合同验收未通过，且失败归因与现场不一致，当前不能进入 `merge`。

时间：2026-04-27 22:15
经办人：金铲铲大作战
任务：T-20260427-799dca63
任务目标：校正 `expectation.pass.symbol_buffer_hoist` 合同验收的真实失败归因，并确认当前是否仍存在可由本轮 `build` 收口的实现缺口
执行前阅读记录：已读 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`](../../../../../../../ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 的 `S1` / 验收设计、前序 `spec/build/review` 记录、只读合同资产 [`expectation/pass/symbol_buffer_hoist/__main__.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/__main__.py) / [`basic.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/basic.py) / [`shape_depends_on_loop_carried.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/shape_depends_on_loop_carried.py)、以及当前 worktree 的 [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py) / [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py) / [`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py)
最小功能闭环：不再扩改实现；只把合同验收拆成两层现场重新核对：一层是计划书点名命令 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist` 的首个失败；另一层是在同一 Python 进程里强制优先加载本 worktree `kernel_gen` 后，immutable 合同资产本身还剩什么失败
改动：
- 未改实现、测试、`spec` 或 `expectation`
- 仅补当前记录，把合同验收失败拆成“执行入口先落到主仓 `kernel_gen`”与“强制切到 worktree 代码后仍存在 immutable 资产问题”两层结论，避免再把两类失败混成一个归因
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：失败
  - 首个失败：`pass-symbol_buffer_hoist-basic-1` 与 `pass-symbol_buffer_hoist-output_scratch-1` 都先报 `PassRegistryError: unknown pass 'symbol-buffer-hoist'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：仍失败
  - 失败现象与上条一致；在 `python -m expectation...` 场景下，repo root 的 `''` 仍排在 `sys.path[0]`，先解析到主仓 [`kernel_gen/tools/ircheck.py`](../../../../../../../kernel_gen/tools/ircheck.py) 与 [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)
- `python3` 进程内手动 `sys.path[:0]=[worktree, repo_root]` 后分别执行 [`expectation/pass/symbol_buffer_hoist/basic.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/basic.py) / [`shape_depends_on_loop_carried.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/shape_depends_on_loop_carried.py) 的 case
  - 结果：`basic._case_1` 通过，`unknown pass` 消失
  - 剩余失败 1：`basic._case_output_scratch` 报 `SymbolBufferHoistVerifierError: dma.deslice result must match target type`
  - 剩余失败 2：`shape._case_1` 仍报输入 IR 自身 `!symbol.int<...>` 名称不一致导致的解析失败
- `git -C /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1 diff --check`
  - 结果：通过
Diff 反推自测：
- 本轮 diff 只涉及当前记录；反推验证采用两条合同验收命令、一个 `python3` 进程内 `sys.path` 强制优先 worktree 的 case 复现脚本、以及 `git diff --check`
- 未追加 `pytest`，原因：实现与公开 `pytest` 部分上轮已通过，本轮只补合同验收失败归因与阻塞定位
合同验收（如适用）：
- 计划书点名命令 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist` 当前不通过，且首个失败就是 `unknown pass 'symbol-buffer-hoist'`
- 在不修改 immutable `expectation/**` 的前提下，强制让合同资产吃到本 worktree 代码后，仍剩两处 immutable 资产问题：
  - `output_scratch` case 的 `dma.deslice` 合同文本与当前 verifier 口径不一致
  - `shape_depends_on_loop_carried` case 的输入 IR 自身符号类型名不一致
自检：
- 本轮未越权改 `expectation/**`、主仓实现或无关文件
- 未新增公开接口，也未再跨文件调用非公开 API
- 失败归因已拆成“执行入口问题”和“immutable 资产问题”两层，和现场一致
- 现阶段若继续靠 `build` 改实现，无法消除 repo root `python -m expectation...` 先解析主仓 `kernel_gen` 的问题；若去改 root 仓或 `expectation/**`，都超出当前任务允许范围
结论：
- 当前任务阻塞，不能继续 `-next`
- 已确认 `symbol-buffer-hoist` 实现与公开 `pytest` 本身无新增失败；当前剩余问题是合同验收入口如何绑定本 worktree 代码，以及 immutable 合同资产自身两处失败
- 下一步需用脚本向管理员/架构师回报，请他们确认：是接受当前记录为“实现闭合但合同验收入口受限”，还是调整验收命令/归属，再继续推进

时间：2026-04-27 22:39
经办人：大闸蟹
任务：T-20260427-799dca63
任务目标：对当前 blocker 给出架构裁定，明确本任务应按哪一层失败作为结论
执行前阅读记录：已重读 [`ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`](../../../../../../../ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 的 `S1` / 验收设计 / 合同真源顺序、`TODO.md` 本任务行，以及本记录内 `build / review / blocker` 三轮结论
架构裁定：
- 本任务结论按“第二层失败归因”判定，不按 repo root 直接执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist` 的首个 `unknown pass 'symbol-buffer-hoist'` 判定。
- 原因：该首个失败反映的是合同验收入口在当前 worktree 场景下先解析到主仓 `kernel_gen` 的执行现场绑定问题，不是当前 `symbol-buffer-hoist` 实现本体是否闭合的直接证据；当前 build 无权修改 `expectation/**`，也无权改写计划书点名命令本身。
- 对本任务真正有信息量的层是“在同一 Python 进程里强制优先加载本 worktree `kernel_gen` 后”的结果：`basic` 输入 staging 正例已通过，剩余失败收敛为 immutable 合同资产本身的两处问题：
  - `output_scratch` case 的 `dma.deslice` verifier 失败
  - `shape_depends_on_loop_carried` case 的输入 IR 解析失败
- 因此，`T-20260427-799dca63` 当前应记为：实现与公开 `pytest` 已闭合；剩余阻塞属于“只读 expectation 合同资产 / 验收归属”问题，不继续算作当前 build 需要收掉的实现失败。
- 继续推进口径：不接受“当前 build 必须把计划书点名命令打到全绿”这一要求；应调整验收归属，把 `python3 -m expectation.pass.symbol_buffer_hoist` 从本 build 的必过项改为计划层只读合同验收，由后续计划修订/终验统一处理。若需要形成唯一后续动作，应补建一条 `spec` 性质的修复任务，只处理计划口径与只读合同资产归属说明，不再回到本 build 扩改实现。
结论：
- 本任务当前结论按第二层失败归因执行
- `unknown pass 'symbol-buffer-hoist'` 不再作为本 build 的实现失败
- 当前 build 不继续消化 immutable `expectation` 失败；后续如需推进，只能走计划口径修订或唯一 `spec` 修复任务

时间：2026-04-27 22:17
经办人：金铲铲大作战
任务：T-20260427-799dca63
任务目标：根据管理员回复继续补清 `unknown pass` 与 immutable 合同资产失败的边界，并保持任务停在 `build`
改动：
- 未改实现、测试、`spec` 或 `expectation`
- 仅补阻塞说明：把 `unknown pass 'symbol-buffer-hoist'` 明确归到“repo root 执行 `python -m expectation...` 时先解析主仓 `kernel_gen`”这一层，不再把它写成 worktree `symbol-buffer-hoist` 未注册
- 记录管理员最新口径：不改 `expectation`，不自行改计划书点名命令，不把“实现闭合但合同入口受限”直接当作完成
验证：
- 管理员回复：保持 `T-20260427-799dca63` 在 `build`；继续把 `unknown pass` 的加载路径问题与 immutable `expectation` 失败分别写清
- 现场证据已在上一条记录中具备：
  - `python3 -m expectation.pass.symbol_buffer_hoist` 从 repo root 先命中主仓 [`kernel_gen/tools/ircheck.py`](../../../../../../../kernel_gen/tools/ircheck.py) / [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)，因此首个失败是 `unknown pass 'symbol-buffer-hoist'`
  - 在同一 Python 进程里手动把 worktree 插到 `sys.path[:0]` 后，[`expectation/pass/symbol_buffer_hoist/basic.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/basic.py) 的 `basic._case_1` 可通过，说明 worktree [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py) 与 [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py) 的注册链本身是通的
  - 同一强制 worktree 场景下剩余失败固定为 immutable 资产两处：`output_scratch` 的 `dma.deslice` verifier 失败与 `shape_depends_on_loop_carried` 输入 IR 解析失败
Diff 反推自测：
- 本轮 diff 只涉及当前记录；反推验证为管理员回复核对 + 上一条记录中的三组复现命令与 `git diff --check`
合同验收（如适用）：
- 当前仍不通过，且失败需拆成两层理解：
  - 第一层：计划书点名命令在 repo root 先落到主仓 `kernel_gen`，首个失败是 `unknown pass 'symbol-buffer-hoist'`
  - 第二层：若强制使用 worktree `kernel_gen`，`unknown pass` 消失，但 immutable 合同资产还剩 `output_scratch` verifier 失败与 `loop-carried shape` 解析失败
自检：
- 已按管理员要求把“加载路径问题”和“immutable 资产问题”分开写清
- 未越权改 `expectation/**`、计划书或主仓实现
- 当前记录已能支持架构师裁定：是继续按现命令收口，还是调整验收归属/计划口径
结论：
- `T-20260427-799dca63` 继续保持 `build`
- 未收到架构师新口径前，不继续 `-next`，也不越界改 `expectation`

时间：2026-04-27 22:24
经办人：守护最好的爱莉希雅
任务：T-20260427-799dca63
任务目标：为当前合同验收失败确定统一架构归因口径，明确本任务应按哪一层失败记结论
执行前阅读记录：已读 [`ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`](../../../../../../../ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 的合同真源顺序 / 验收设计 / S1 正文、[`TODO.md`](../../../../../../../TODO.md) 当前任务行，以及本记录中 22:15 / 22:17 的两轮阻塞说明
改动：
- 未改实现、测试、`spec` 或 `expectation`
- 仅补统一口径：repo root 执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist` 先报 `unknown pass 'symbol-buffer-hoist'`，属于执行现场优先命中主仓 `kernel_gen` 的现场差异，不作为本任务最终失败归因
- 明确本任务结论应以正确实现现场为准：若在同一 Python 进程内强制优先加载当前 worktree 的 `kernel_gen` 后，`unknown pass` 消失，则最终失败应记在仍未通过的 immutable 合同验收资产层
验证：
- 计划书合同真源顺序已写明：`spec/pass/symbol_buffer_hoist.md > pytest > expectation > 当前实现`
- 计划书验收设计仍保留 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist`
- 本记录前序复现已证明：worktree 代码场景下 `basic._case_1` 可通过，`unknown pass` 不再出现；剩余失败固定为 immutable 资产两处：
  - `basic._case_output_scratch` 的 verifier 失败
  - `shape_depends_on_loop_carried._case_1` 的输入 IR 解析失败
合同验收（如适用）：
- 当前任务结论不再按 repo root 的 `unknown pass 'symbol-buffer-hoist'` 记失败
- 当前任务结论按 immutable `expectation/pass/symbol_buffer_hoist/**` 在正确实现现场下仍未通过记失败
自检：
- 本轮只补任务链口径，没有越权改 `expectation/**`
- 失败层级已经从“现场导入路径差异”与“只读合同资产自身失败”两类中拆清，后续管理员/架构复核可直接沿此口径判断
结论：
- `T-20260427-799dca63` 当前应按“实现与公开 pytest 已闭合，但 immutable expectation 合同验收资产在正确实现现场仍失败”记结论
- 若继续推进，应围绕该只读合同资产失败的归属与后续处理方式询问管理员/用户；不再把 repo root `unknown pass` 作为本任务的最终失败归因

时间：2026-04-27 22:19
经办人：金铲铲大作战
任务：T-20260427-799dca63
任务目标：按最新架构裁定收束本轮 `build` 结论，并把任务从 `build` 续回 `review`
执行前阅读记录：已读管理员回复、[`ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`](../../../../../../../ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 验收设计、以及本记录中 22:15 / 22:17 / 22:24 / 22:39 的 blocker 与架构裁定条目
最小功能闭环：不再扩改实现；只把本轮 `build` 结论收束为“实现与公开 `pytest` 已闭合，剩余是 immutable 合同资产 / 验收归属问题”，然后把任务按当前状态续回 `review`
改动：
- 未改实现、测试、`spec` 或 `expectation`
- 仅补本条 `build` 结论：接受两位架构师裁定，不再把 repo root `python -m expectation.pass.symbol_buffer_hoist` 先报的 `unknown pass 'symbol-buffer-hoist'` 记作本任务最终失败
- 本轮 `build` 结束口径改为：当前 worktree 的 [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py) / [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py) 与公开 `pytest` 已闭合；剩余只读合同资产失败继续单列
验证：
- 架构裁定复核：
  - [大闸蟹](/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-s1.md) 22:39 条目：本任务结论按第二层失败归因执行
  - [守护最好的爱莉希雅](/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-s1.md) 22:24 条目：repo root `unknown pass` 不作为本任务最终失败归因
- `git -C /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1 diff --check -- agents/codex-multi-agents/log/task_records/2026/17/20260427-symbol-buffer-hoist-s1.md`
  - 结果：通过
Diff 反推自测：
- 本轮 diff 只涉及当前记录；反推验证为两位架构师裁定条目核对 + `git diff --check`
- 未追加 `pytest` 或合同验收命令，原因：实现与公开 `pytest` 结果未变化，本轮只收束任务结论与续流依据
合同验收（如适用）：
- 保持上一轮分层结论不变：
  - repo root 直接执行时，首个失败是加载路径问题导致的 `unknown pass 'symbol-buffer-hoist'`
  - 在正确实现现场下，剩余失败是 immutable `expectation/pass/symbol_buffer_hoist/**` 的 `output_scratch` verifier 失败与 `loop-carried shape` 解析失败
- 按当前架构口径，这些只读合同资产问题继续单列，不再算作本轮 `build` 未收口的实现失败
自检：
- 已按管理员与架构师口径把本轮 `build` 结论收束到正确层级
- 未越权改 `expectation/**`、计划书或主仓实现
- 当前记录已足够支持 reviewer 继续复核：实现与公开 `pytest` 闭合，剩余仅是合同资产 / 验收归属问题
结论：
- 当前 `build` 已完成，应按最新架构口径续回 `review`
- 下一步执行 `-next -auto -type review`，由 review 继续基于当前记录复核

时间：2026-04-27 22:52
经办人：提莫炖蘑菇
任务：T-20260427-799dca63
任务目标：按最新架构裁定复核 `symbol-buffer-hoist` 实现、公开 `pytest` 与合同验收归因。

真实审查：
- 已按最新架构裁定复核 [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py)、[`kernel_gen/passes/__init__.py`](../../../../../../../kernel_gen/passes/__init__.py)、[`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)、[`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)、[`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)、[`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py) 以及只读合同资产 [`expectation/pass/symbol_buffer_hoist/basic.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/basic.py)、[`expectation/pass/symbol_buffer_hoist/shape_depends_on_loop_carried.py`](../../../../../../../expectation/pass/symbol_buffer_hoist/shape_depends_on_loop_carried.py)。
- 本轮实现/测试没有新增跨文件非公开 API 直连；公开入口仍收口在 `kernel_gen.passes.symbol_buffer_hoist`、`kernel_gen.passes` 包根和 `build_registered_pass("symbol-buffer-hoist")`。
- 最新架构口径要求：repo root 直接执行 `python -m expectation.pass.symbol_buffer_hoist` 先报的 `unknown pass 'symbol-buffer-hoist'` 不作为本任务最终失败归因；当前 review 只核对“正确实现现场”下的第二层归因是否与记录一致。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_symbol_buffer_hoist.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_pass_registry.py -ra`
  - 结果：`43 passed, 1 warning`
- `python3` 进程内强制 `sys.path[:0] = [worktree, repo_root]` 后分别执行：
  - `expectation.pass.symbol_buffer_hoist.basic._case_1` -> `PASS`
  - `expectation.pass.symbol_buffer_hoist.basic._case_output_scratch` -> 失败，`SymbolBufferHoistVerifierError: dma.deslice result must match target type`
  - `expectation.pass.symbol_buffer_hoist.shape_depends_on_loop_carried._case_1` -> 失败，输入 IR 解析阶段 `!symbol.int<...>` 名称不一致
- `git -C /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1 diff --check`
  - 结果：通过

合同验收归因：
- 按本任务最新架构裁定，`unknown pass 'symbol-buffer-hoist'` 属于 repo root 现场优先命中主仓 `kernel_gen` 的执行入口差异，不再作为本任务最终失败归因。
- 在正确实现现场下，合同验收剩余失败确实只收敛为两项 immutable 资产问题：
  - `output_scratch` case 的 `dma.deslice` verifier 失败
  - `loop-carried shape` case 的输入 IR 解析失败
- 这两项继续单列为只读合同资产 / 验收归因问题，不再算当前 build 未收口的实现失败。

自检：
- 已按最新 review 规则补查实现文件 `API 列表`、公开 spec 索引、公开测试入口与跨文件非公开 API 使用。
- 本轮未修改 `expectation/**`，也未把 `expectation` 当作 diff 反推测试替代品。

结论：
- `通过`
- 原因：`symbol-buffer-hoist` 的实现、包导出、registry 接线与公开 `pytest` 已闭合；当前剩余失败按最新架构裁定归入 immutable 合同资产 / 验收入口问题，不再阻断本任务 `review`

时间：2026-04-27 23:44 +0800
经办人：李白
任务：T-20260427-799dca63
任务目标：合并 `symbol_buffer_hoist` S1 已通过复审的实现、包导出、registry 接线与公开 `pytest` 收口；合同验收剩余失败按最新架构裁定仅单列为 immutable 资产 / 验收归因问题。
执行前阅读记录：已核对 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 中 T-20260427-799dca63 当前任务行、[`ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_buffer_hoist_green_plan.md) 的 S1 阶段与验收设计、前序 build/review/架构裁定记录，以及当前 worktree diff 中的 [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py)、[`kernel_gen/passes/__init__.py`](../../../../../../../kernel_gen/passes/__init__.py)、[`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)、[`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)、[`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)、[`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)。
最小功能闭环：只合并当前 worktree 已通过复审的 `symbol_buffer_hoist` 实现与公开测试边界，不扩展到计划层修文或 `expectation` 资产处理。若当前 worktree 基线落后 latest `origin/main`，则仅把这组 reviewed residual diff 重放到最新主线，不混入其它链路变更。

时间：2026-04-27 23:48 +0800
经办人：李白
任务：T-20260427-799dca63
任务目标：完成 `symbol_buffer_hoist` S1 merge 收口并把 reviewed residual diff 回放到 latest `origin/main`。
改动：
- 先将旧基线 `6667542536a6264f1a62bdc8d271dbf334628cfc` 上的 reviewed residual diff 固化为本地快照提交，再以 `git rebase --onto origin/main 6667542536a6264f1a62bdc8d271dbf334628cfc` 回放到 latest `origin/main@09901095d9d6bc20f8fd0390065c90e4d0ba45d0`。
- 回放未产生跨范围冲突；最终保留的 merge 边界仍只在计划书 S1 指定模块：
  - [`kernel_gen/passes/symbol_buffer_hoist.py`](../../../../../../../kernel_gen/passes/symbol_buffer_hoist.py)
  - [`kernel_gen/passes/__init__.py`](../../../../../../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)
  - [`spec/pass/symbol_buffer_hoist.md`](../../../../../../../spec/pass/symbol_buffer_hoist.md)
  - [`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)
  - [`test/pass/test_symbol_buffer_hoist.py`](../../../../../../../test/pass/test_symbol_buffer_hoist.py)
  - [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)
  - 当前任务记录文件
- 未修改 `expectation/**`；immutable 合同验收问题继续沿用前序 review / 架构裁定单列。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1:/home/lfr/kernelcode_generate python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_symbol_buffer_hoist.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_pass_registry.py -ra`
  - 结果：`43 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/kernel_gen/passes/symbol_buffer_hoist.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/kernel_gen/passes/__init__.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_symbol_buffer_hoist.py /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1/test/pass/test_pass_registry.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260427-symbol-buffer-hoist-s1 diff --check`
  - 结果：通过
Diff 反推自测：
- 本轮 merge 的实际 diff 对应测试仍是公开 `pytest`：
  - `test/pass/test_symbol_buffer_hoist.py`
  - `test/pass/test_pass_registry.py`
- `expectation` 未作为 diff 反推测试；相关剩余失败继续只按 immutable 合同验收 / 验收归因问题单列。
合同验收（如适用）：
- 继承本记录 22:52 review 结论与两位架构裁定：
  - repo root `unknown pass 'symbol-buffer-hoist'` 不作为本任务最终失败归因
  - 正确实现现场下剩余失败只收敛为 immutable `expectation/pass/symbol_buffer_hoist/**` 资产问题
- 本轮 merge 未改这些只读资产，也未把其失败重新算回实现未收口。
自检：
- 已确认回放后没有把 `symbol_buffer_hoist` 公开入口、包导出、registry 接线或公开 `pytest` 边界回退到旧主线状态。
- 已确认 merge 只带入 S1 residual diff，没有混入计划外实现、`expectation` 写入或其他任务链改动。
结论：
- merge 收口完成，可直接提交、`push origin/main` 并执行 `-done`。
