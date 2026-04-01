时间：2026-04-02 06:26:32 +0800
任务：T-20260402-ae3fe509
任务目标：在 `wt-20260402-nn-add-impl-g1` 中仅修改 `kernel_gen/dsl/gen_kernel.py` 与 `test/dsl/test_gen_kernel.py`，使 direct-return `nn.add` 在 `target=cpu` 下仅支持 `memory+memory`、`memory+const(i32)`、`memory+symbol.int` 三条路径，并生成 `cpu::add(..., out)`；保持 `unique-use + func.return + direct bind to out` 的硬门禁，多 use 或无法直接绑定 `out` 继续 `unsupported op`；不改 `emit_c/spec/expectation`。
改动：
- 核对任务前置：
  - `worktree=/home/lfr/kernelcode_generate/wt-20260402-nn-add-impl-g1` 可访问。
  - 已用主仓任务表 `/home/lfr/kernelcode_generate/TODO.md` 执行 `-status -doing`，确认当前我名下仅 `T-20260402-ae3fe509` 在进行中。
  - 已按要求向管理员同步“已开始处理、当前无其他进行中任务、无阻塞”。
- 更新 `wt-20260402-nn-add-impl-g1/kernel_gen/dsl/gen_kernel.py`：
  - 新增 `NnAddOp` 导入。
  - 在 `gen_body()` 中引入 direct-return `nn.add` 特化判定：
    - 仅当 `target=cpu`
    - 返回类型为 `NnMemoryType`
    - `nn.add.result` 的唯一 use 为当前 `func.return`
    - 即 `unique-use + func.return + direct bind to out`
    时，才把 `nn.add.result` 预绑定为 `out` 并复用现有 `emit_c_op(nn.add, ctx)` 生成 `cpu::add(..., out);`。
  - 在对应 `func.return` 处对 direct-return `nn.add` 特化路径跳过通用 `out = value_name;` 回写，避免退化成 generic fallback。
  - 非上述路径保持现有行为，因此 `multi-use`、无法直接绑定 `out`、或非 cpu target 仍继续触发 `target=cpu: nn.add: unsupported op`。
- 更新 `wt-20260402-nn-add-impl-g1/test/dsl/test_gen_kernel.py`：
  - 新增 `NnAddOp` 导入。
  - 新增 direct-return `nn.add` 的四个函数级用例：
    - `test_gen_kernel_supports_direct_return_nn_add_memory_memory_on_cpu`
    - `test_gen_kernel_supports_direct_return_nn_add_memory_const_on_cpu`
    - `test_gen_kernel_supports_direct_return_nn_add_memory_symbol_on_cpu`
    - `test_gen_kernel_rejects_nn_add_specialization_on_multi_use`
  - 分别锁定：
    - `memory + memory -> cpu::add(lhs, rhs, out);`
    - `memory + const(i32) -> cpu::add(lhs, 1, out);`
    - `memory + symbol.int -> cpu::add(lhs, bias, out);`
    - `multi-use` 继续报 `target=cpu: nn.add: unsupported op`
  - 并明确 direct-return 成功路径不再出现 generic `out = ...;`。
- 验证：
  - `pytest -q wt-20260402-nn-add-impl-g1/test/dsl/test_gen_kernel.py`（exit 0，`16 passed in 0.29s`）
  - `git -C wt-20260402-nn-add-impl-g1 diff --check -- kernel_gen/dsl/gen_kernel.py test/dsl/test_gen_kernel.py`（exit 0）
结论：
- `完成`。
- 影响范围仅：
  - `wt-20260402-nn-add-impl-g1/kernel_gen/dsl/gen_kernel.py`
  - `wt-20260402-nn-add-impl-g1/test/dsl/test_gen_kernel.py`
  - 当前记录文件
- 测试情况：已运行 `test/dsl/test_gen_kernel.py` 全量用例，结果 `16 passed`。
- 阻塞点：无。
- 下一步建议：新建唯一后续审查任务，在同一 `worktree` 中只读复核 `kernel_gen/dsl/gen_kernel.py` 与 `test/dsl/test_gen_kernel.py` 是否与已合并 `gen_kernel` spec 一致，重点核对三条 direct-return `nn.add` 白名单路径与 `unique-use + func.return + direct bind to out` 硬门禁。

时间：2026-04-02 06:30:59 +0800
任务：T-20260402-cbf45832
任务目标：在 `wt-20260402-nn-add-impl-g1` 中只读复核 `kernel_gen/dsl/gen_kernel.py` 与 `test/dsl/test_gen_kernel.py` 是否与已合并 `gen_kernel` spec 一致。
改动：
- 静态对照 `wt-20260402-nn-add-impl-g1/spec/dsl/gen_kernel.md`、`wt-20260402-nn-add-impl-g1/kernel_gen/dsl/gen_kernel.py`、`wt-20260402-nn-add-impl-g1/test/dsl/test_gen_kernel.py`。
- 复核实现：
  - `kernel_gen/dsl/gen_kernel.py` 第 162-173 行把 direct-return 特化门禁收敛为 `target=cpu + func.return 单返回值 + owner 为 NnAddOp + result.has_one_use() + unique use 就是当前 return`。
  - `kernel_gen/dsl/gen_kernel.py` 第 190-198 行在 direct-return 命中时跳过 generic `out = ...;` 回写，避免退化为 generic fallback。
  - `kernel_gen/dsl/gen_kernel.py` 第 210-215 行只在命中上述硬门禁时预绑定 `nn.add.result -> out`，随后仍复用 `emit_c_op(nn.add, ctx)`，因此 operand 白名单继续受 `emit_c` 约束。
- 复核测试：
  - `test/dsl/test_gen_kernel.py` 第 479-549 行已覆盖 `memory+memory`、`memory+const(i32)`、`memory+symbol.int` 三条 direct-return 成功路径，并断言不出现 `out = ` generic 回写。
  - `test/dsl/test_gen_kernel.py` 第 563-575 行已覆盖 multi-use 继续报 `target=cpu: nn.add: unsupported op`。
- 额外只读复现：
  - `const(i32)+memory` direct-return -> `EmitCError target=cpu: nn.add: unsupported op`
  - `symbol.int+memory` direct-return -> `EmitCError target=cpu: nn.add: unsupported op`
  - `target=gpu` direct-return -> `EmitCError target=gpu: nn.add: unsupported op`
- 验证：
  - `pytest -q test/dsl/test_gen_kernel.py -k 'nn_add'`（exit 0，`4 passed, 12 deselected in 0.26s`）
  - `pytest -q test/dsl/test_gen_kernel.py`（exit 0，`16 passed in 0.27s`）
  - `git diff -- kernel_gen/dsl/gen_kernel.py test/dsl/test_gen_kernel.py`
结论：
- `通过`。
- 漏洞排查结果：
  - 未发现把 reverse mixed operand 组合误放行到 direct-return 成功路径。
  - 未发现 `unique-use + func.return + direct bind to out` 被弱化。
  - 未发现退化为 `out = tmp`、`return tmp` 或 non-cpu silent fallback。
- 下一步建议：进入合并阶段，仅合并 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py` 与本链路记录文件。

时间：2026-04-02 06:35:53 +0800
任务：T-20260402-6dbc5c55
任务目标：在 `wt-20260402-nn-add-impl-g1` 按最小范围合入 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py` 与对应任务记录；不改 `emit_c/spec/expectation`；合并后完成 cleanup 与状态同步。
改动：
- 合并范围确认：
  - `git -C wt-20260402-nn-add-impl-g1 status --short` 仅显示 `kernel_gen/dsl/gen_kernel.py` 与 `test/dsl/test_gen_kernel.py` 为已修改；未发现超出授权范围的其他未提交改动。
  - 链路记录文件沿主仓路径 `agents/codex-multi-agents/log/task_records/2026/14/20260402-nn-add-impl-g1.md` 维护，本次合并同步带上该记录文件。
- 合入主仓内容：
  - 在 `kernel_gen/dsl/gen_kernel.py` 并入 direct-return `nn.add` 特化：
    - 仅在 `target=cpu`
    - `func.return` 单返回值
    - `owner` 为 `NnAddOp`
    - `result.has_one_use()`
    - unique use 就是当前 `func.return`
    时，预绑定 `nn.add.result -> out` 并跳过 generic `out = ...;` 回写，复用现有 `emit_c_op(nn.add, ctx)` 发射 `cpu::add(..., out);`。
  - 在 `test/dsl/test_gen_kernel.py` 追加 `GK-013~016`，覆盖 `memory+memory`、`memory+const(i32)`、`memory+symbol.int` 三条 direct-return 成功路径，以及 multi-use 继续 `unsupported op` 的硬门禁。
  - 本次未修改 `emit_c/spec/expectation`。
- 验证：
  - `pytest -q test/dsl/test_gen_kernel.py`（exit 0，`16 passed in 0.26s`）
  - `git diff --check -- kernel_gen/dsl/gen_kernel.py test/dsl/test_gen_kernel.py`（exit 0）
  - 补充说明：首次重跑时出现一次环境级导入异常；按同链路命令立即复跑后恢复正常并稳定通过，最终以复跑通过结果作为本次验收依据。
- cleanup：
  - `git worktree remove --force wt-20260402-nn-add-impl-g1`（exit 0）
  - `git branch -D wt-20260402-nn-add-impl-g1`（exit 0）
  - `git worktree list --porcelain` 复核后，授权 `worktree` 已移除，且未波及其他活跃 worktree。
结论：
- 已完成合并收口；本次仅合入 `kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_gen_kernel.py` 与当前链路记录文件。
- 测试情况：`test/dsl/test_gen_kernel.py` 全量通过，结果 `16 passed`。
- 阻塞点：无。
- 下一步建议：该链路已收口，无需继续派生后续任务；如需后续调整 `emit_c/spec/expectation`，应由管理员单独分发新任务。
