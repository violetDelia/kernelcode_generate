时间：2026-04-06 09:41:30 +0800
经办人：咯咯咯
任务：T-20260406-91488ecd（dma_memory_hierarchy_lowering_green_plan#S4 spec任务）
任务目标：在 `spec/pass/lowering/dma_memory_hierarchy/spec.md` 补 dynamic shape / symbol 透传与显式失败边界，并在允许范围内同步实现与测试，锁定匿名 `?` 与目标缺失 `SM/LM` 的失败口径。
改动：
- 更新 `spec/pass/lowering/dma_memory_hierarchy/spec.md`：新增 staging `dma.alloc(dynamic_shape=...)` 必须来自显式 symbol 来源的合同；明确匿名 `?` 且无可恢复 shape 来源时必须以包含 `dynamic_shape` 的错误短语失败；补充 `COV-DMH-009` / `COV-DMH-010` 测试映射，并把窗口链路 wording 同步到当前 unit stride 合同。
- 更新 `kernel_gen/passes/lowering/dma_memory_hierarchy.py`：在 full-window 路径构造 `symbol.get_dim` 前显式拒绝匿名 `?` 维度，报错短语固定为 `dynamic_shape must come from explicit symbol source; anonymous '?' dimension is unsupported in lower-dma-memory-hierarchy`。
- 更新 `test/pass/test_dma_memory_hierarchy.py`：新增 `test_dma_memory_hierarchy_symbol_shape_passthrough` 与 `test_dma_memory_hierarchy_rejects_anonymous_dynamic_shape`，覆盖显式 symbol 正例与匿名 `?` 坏例。
- 收口的合同：full-window staging 仅允许从显式 `shape` 条目经 `symbol.get_dim` 构造 `dynamic_shape`；window staging 允许直接复用 `dma.view.shape` 等现成 SSA shape 来源；目标缺失 `SM/LM` 容量继续显式失败。
- 边界：本次不扩 `dma` dialect/verifier 的 stride 语义；hierarchy 新路径继续固定 unit stride，不引入非 `1` 或符号 stride。
- 拒绝路径：匿名 `?` 无显式 shape 来源时报 `dynamic_shape`；target 缺失 `SM/LM` 容量时报 `SM/LM`；输入残留 `nn.*` 仍按既有合同失败。
- 引用文件：`ARCHITECTURE/plan/dma_memory_hierarchy_lowering_green_plan.md`、`spec/pass/lowering/dma_memory_hierarchy/spec.md`、`kernel_gen/passes/lowering/dma_memory_hierarchy.py`、`test/pass/test_dma_memory_hierarchy.py`。
结论：
- `PYTHONPATH=. pytest -q test/pass/test_dma_memory_hierarchy.py` 已通过，结果为 `7 passed in 0.27s`。
- 本次任务已完成 S4 收口：spec / 实现 / test 对 `dynamic_shape` 来源、匿名 `?` 坏例与 `SM/LM` 失败边界的口径已一致。
- 下游影响：后续审查需重点确认 `COV-DMH-009` / `COV-DMH-010` 与错误短语稳定性，以及 S3/S4 合同未再回退。
- 下一步建议：派生唯一审查任务，对本次 `spec/pass/lowering/dma_memory_hierarchy/spec.md`、`kernel_gen/passes/lowering/dma_memory_hierarchy.py`、`test/pass/test_dma_memory_hierarchy.py` 的一致性进行复核。
时间：2026-04-06 09:45 +0800
经办人：提莫炖蘑菇
任务：T-20260406-c95b9d1e（dma_memory_hierarchy_lowering_green_plan-S4-审查）
任务目标：复核 S4 动态 shape/匿名 ?/SM-LM 失败边界的 spec/实现/测试一致性，核对 COV-DMH-009/010 映射，并复跑 gate。
改动：
- 核对文件范围与一致性：`spec/pass/lowering/dma_memory_hierarchy/spec.md`、`kernel_gen/passes/lowering/dma_memory_hierarchy.py`、`test/pass/test_dma_memory_hierarchy.py`。
- COV-DMH-009/010 映射核对：spec 表中用例 ID 与测试 `test_dma_memory_hierarchy_symbol_shape_passthrough` / `test_dma_memory_hierarchy_rejects_anonymous_dynamic_shape` 一致。
- 失败边界核对：实现中 `_build_full_window_operands` 对匿名 `?` 维度立即报错（含 `dynamic_shape` 关键字）；`_require_sm_lm_support` 对目标缺失 SM/LM 明确报错（含 `SM/LM` 关键字）；测试分别用 `match="dynamic_shape"` / `match="SM/LM"` 覆盖。
- 复跑 gate 并记录输出。
结论：
- 审查通过：spec/实现/测试一致，COV-DMH-009/010 覆盖与映射成立；匿名 `?` 与 SM/LM 缺失均 fail-fast 且关键字稳定。
问题清单：
- 无。
风险：
- 已核对动态 shape/匿名 `?`/SM-LM 失败边界；未发现静默降级或错误短语漂移风险。
验证命令：
- `PYTHONPATH=. pytest -q test/pass/test_dma_memory_hierarchy.py`
关键输出：
- `7 passed in 0.26s`
下一步建议：
- 派生唯一合并任务（提交 S4 收口变更）。
