时间：2026-04-08 10:17:48 +0800
经办人：睡觉小分队
任务：T-20260408-47071895（memory_pool_pass_green_plan S3，spec 阶段）
任务目标：补齐 `MemoryPoolPass` 对 `symbol.for` 词法生命周期、loop-local reuse、offset 竞争规则与失败短语的公开合同，确保下游实现/测试有唯一可执行口径。
改动：
- 更新 `wt-20260408-memory-pool/spec/pass/lowering/memory_pool.md`：
  - 明确 `symbol.for` 的 `loop_bounds` 与 loop 内 alloc 生命周期区间规则（loop 内 alloc/free 均归一到 `[loop_begin, loop_end]`）。
  - 明确 slot 分配算法与 `offset_bytes_expr = size_bytes_expr * slot_index` 的确定性要求，并给出 loop-local 与 loop 外 alloc 的 offset 竞争示例（alloc2/alloc3 复用）。
  - 明确 `rewrite=True` 的 byte pool + typed `dma.view` 输出形态、view offset 规则与可静态求值时的越界拒绝口径。
  - 将原“拒绝路径”章节收敛到允许的章节结构下（新增 `额外补充/失败短语`），并补齐 `MemoryPool*` 失败短语列表与触发条件（禁止静默跳过）。
  - `测试` 章节仅保留 `pytest` 命令与用例清单，避免引用非依赖目录文件。
结论：S3 的 spec 收口已完成；建议派生后续【实现+补测】任务按本合同补齐/对齐 `MemoryPoolPass` 在 `symbol.for` 场景的行为验证与证据产出。
时间：2026-04-08 10:27:09 +0800
经办人：朽木露琪亚
任务：T-20260408-47071895（memory_pool_pass_green_plan S3，实现阶段）
任务目标：按 `spec/pass/lowering/memory_pool.md` 收口 `MemoryPoolPass` 在 `symbol.for` 生命周期、拒绝路径与验证证据上的实现状态，补齐 S3 expectation 入口并确认当前 pass/test 与规格一致。
改动：
- 新增 `wt-20260408-memory-pool/expectation/pass/lowing/memory_pool/loop_reuse.py`，覆盖 `symbol.for` loop-local reuse 正例，以及 `MemoryPoolEscapingAlloc`、`MemoryPoolUnsupportedNonLinearAlloc`、`MemoryPoolInvalidLifetime`、`MemoryPoolUnsupportedRegionEscape` 四类失败路径。
- 复核 `wt-20260408-memory-pool/kernel_gen/passes/lowering/memory_pool.py` 与 `wt-20260408-memory-pool/test/pass/test_memory_pool.py`，确认当前实现与测试已满足 S3 合同，本阶段无需再改 pass/test 代码。
- 验证命令：
  - `cd wt-20260408-memory-pool && pytest -q test/pass/test_memory_pool.py -k "symbol_for or escape or layout or invalid_lifetime"` -> `5 passed, 12 deselected in 0.24s`
  - `cd wt-20260408-memory-pool && PYTHONPATH=. python expectation/pass/lowing/memory_pool/loop_reuse.py` -> `CASE-1~5` 全部完成，exit=0；`CASE-1` 摘要包含 `alloc1 offset_bytes=0`、`alloc2 offset_bytes=32`、`alloc3 offset_bytes=32`
结论：S3 实现阶段已收口；当前 `MemoryPoolPass`、测试与 expectation 证据已对齐，可进入审查阶段重点复核 `symbol.for` 生命周期归一、offset 复用稳定性与四类拒绝路径是否与规格完全一致。
时间：2026-04-08 10:33:01 +0800
经办人：提莫炖蘑菇
任务：T-20260408-47071895（memory_pool_pass_green_plan S3，审查）
任务目标：复核 size mismatch 用例与 TC-MP-012 的注释/断言/实现一致性；复核验证命令证据与异常路径覆盖。
改动：
- 对照 `spec/pass/lowering/memory_pool.md`、`kernel_gen/passes/lowering/memory_pool.py` 与 `test/pass/test_memory_pool.py`：size mismatch 走 `MemoryPoolUnsupportedPoolBucket: size mismatch`，TC-MP-012 的生命周期重叠→不同 offset 规则与 view offset 计算一致。
- 运行 `PYTHONPATH=. python expectation/pass/lowing/memory_pool/loop_reuse.py`，`CASE-1~5` 完成，exit=0（摘要含 alloc1/alloc2/alloc3 offset_bytes=0/32/32）。
- 运行 `PYTHONPATH=. pytest -q test/pass/test_memory_pool.py -k "symbol_for or escape or layout or invalid_lifetime"` 触发 sympy SystemError（采集阶段失败）；补充以 `SYMPY_GMPY=0 PYTHONDONTWRITEBYTECODE=1` 复跑，exit=0（5 passed, 12 deselected）。
结论：不通过。默认验证命令在当前环境不可复现通过，需补齐环境约束或修复 sympy 兼容性；否则审查证据不可稳定复现。建议派生“实现/验证说明修复”任务，明确环境变量或修复依赖，确保无需额外设置即可稳定运行。
时间：2026-04-08 10:41:28 +0800
经办人：小李飞刀
任务：T-20260408-47071895（memory_pool sympy SystemError 修复，实现阶段）
任务目标：默认环境下运行 `pytest -q test/pass/test_memory_pool.py -k 'symbol_for or escape or layout or invalid_lifetime'` 不再触发 sympy `SystemError`，并确保 expectation 入口可稳定执行。
改动：
- 更新 `wt-20260408-memory-pool/expectation/pass/lowing/memory_pool/loop_reuse.py`：
  - 默认 `os.environ.setdefault("SYMPY_GMPY", "0")`，与测试侧一致，避免部分环境 sympy/gmpy 组合触发 `SystemError`（不覆盖外部显式设置）。
- 验证命令：
  - `cd wt-20260408-memory-pool && pytest -q test/pass/test_memory_pool.py -k "symbol_for or escape or layout or invalid_lifetime"` -> `5 passed, 12 deselected in 0.22s`
  - `cd wt-20260408-memory-pool && PYTHONPATH=. python expectation/pass/lowing/memory_pool/loop_reuse.py` -> exit=0（CASE-1~5）
结论：通过。默认执行无需额外手动环境设置即可稳定复现；建议进入审查阶段确认该 env default 是否可接受。

时间：2026-04-08 10:46:21 +0800
经办人：不要啊教练
任务：T-20260408-47071895（memory_pool_pass_green_plan S3，复审）
任务目标：从严复核 `SYMPY_GMPY` 默认设置的合理性（不覆盖外部显式设置），以及默认环境下 pytest 采集不再触发 sympy SystemError。
改动：
- 核对默认设置方式：
  - [`test/pass/test_memory_pool.py`](test/pass/test_memory_pool.py) 与 [`expectation/pass/lowing/memory_pool/loop_reuse.py`](expectation/pass/lowing/memory_pool/loop_reuse.py) 均使用 `os.environ.setdefault("SYMPY_GMPY", "0")`，仅在环境变量缺失时补默认值，不会覆盖外部显式设置。
  - [`kernel_gen/passes/lowering/memory_pool.py`](kernel_gen/passes/lowering/memory_pool.py) 未写入或修改环境变量，仅按需 import sympy（默认值由上游调用环境决定）。
- 复跑验证命令（默认环境）：
  - `cd wt-20260408-memory-pool && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_memory_pool.py`：exit=0；`17 passed in 0.23s`（包含采集阶段）。
  - `cd wt-20260408-memory-pool && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/memory_pool/loop_reuse.py`：exit=0（CASE-1~5 完成）。
- 对照规格要点：
  - [`spec/pass/lowering/memory_pool.md`](spec/pass/lowering/memory_pool.md) 描述的 `symbol.for` 生命周期归一、offset 复用与拒绝路径短语，仍由测试与 expectation 覆盖并可复现运行。
结论：
- 通过：`SYMPY_GMPY` 默认设置在测试/expectation 侧以 `setdefault` 方式实现，满足“不覆盖外部显式设置”的要求；默认环境下 pytest 采集与执行均不再触发 sympy SystemError，证据可复现。
- 漏洞排查结果（6 类）：
  - 输入校验绕过：未发现（仅增加默认环境变量兜底，不改变 pass 的输入校验逻辑）。
  - 类型/形状绕过：未发现（本次未改 verifier/rewriter）。
  - 边界越界：未发现（本次未改偏移与大小计算逻辑）。
  - 错误处理缺失：未发现（错误短语仍由既有测试/expectation 覆盖）。
  - 状态污染：已核对为“仅 setdefault 且仅用于测试/expectation 进程”，不覆盖外部显式设置；未见其它全局状态写入。
  - 资源释放问题：未发现（本次未引入新资源生命周期点）。
