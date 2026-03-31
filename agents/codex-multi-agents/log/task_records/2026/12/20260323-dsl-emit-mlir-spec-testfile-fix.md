# 2026-03-23 T-20260323-e048f3a6

- 任务 ID：`T-20260323-e048f3a6`
- 任务类型：`spec`
- 记录人：`睡觉小分队`
- 时间：`2026-03-23`
- worktree：`/home/lfr/kernelcode_generate/wt-20260323-dsl-emit-mlir-spec-testfile-fix`

## 变更文件

- `spec/dsl/emit_mlir.md`

## 处理结果

- 最小修正 `spec/dsl/emit_mlir.md` 的测试链路描述，明确当前仓内并不存在独立的 `test/dsl/test_emit_mlir.py`。
- 将 `emit_mlir` 链路测试收敛为仓内实际承载文件 [`test/dsl/test_ast_visitor.py`](../../../../test/dsl/test_ast_visitor.py)，并在文档信息与测试章节中显式说明该文件当前承载 `EMIT-*` 用例。
- 将执行命令收敛为 `test/dsl/test_ast_visitor.py` 中 `emit_mlir` 相关子集的 `-k` 过滤命令，避免继续用整份测试文件笼统代表 `emit_mlir` 链路。
- 补充测试目标中对 `EmitContext`、`loop_vars`、索引解析与默认 stride 推导辅助分支的覆盖说明。
- 在功能与用例清单中补齐 `EMIT-011`、`EMIT-012`、`EMIT-013` 与现有测试函数的映射。

## 测试

- 未运行测试（本轮仅改 spec，按任务要求不修改实现、测试与 expectation）。

## 结论

- 已完成本轮最小 spec 修正，`emit_mlir` 的测试文件、执行命令与 `EMIT-*` 映射已按仓内实际测试承载现状收敛。

## 剩余缺口

- 当前仓内仍未独立拆分 `test/dsl/test_emit_mlir.py`；`emit_mlir`、`ast_visitor`、`mlir_gen` 仍共用 `test/dsl/test_ast_visitor.py`。
- 若后续要求“物理文件级”的 `test_emit_mlir` 收敛，还需单独发起测试文件拆分任务。

## 下一阶段建议

- 建议发起复审任务，确认 `spec/dsl/emit_mlir.md` 的测试链路描述与仓内实际 `EMIT-*` 用例完全一致。
- 若用户要求独立测试文件，再拆一个实现/测试任务，将 `emit_mlir` 用例从 `test/dsl/test_ast_visitor.py` 中拆分为单独的 `test_emit_mlir.py`。

---

# 2026-03-23 T-20260323-emit-mlir-spec-testfile-review

- 任务 ID：`T-20260323-emit-mlir-spec-testfile-review`
- 任务类型：`复审`
- 记录人：`李白`
- 时间：`2026-03-23`
- worktree：`/home/lfr/kernelcode_generate/wt-20260323-dsl-emit-mlir-spec-testfile-fix`

## 复审范围

- `spec/dsl/emit_mlir.md`
- `test/dsl/test_ast_visitor.py`（仅核对用例映射与命令口径）

## 结论

- 结论：`需修改`

## 问题清单

1. `spec/dsl/emit_mlir.md` 的测试目标与 `EMIT-010` 断言与当前测试不一致。
   - 位置：`spec/dsl/emit_mlir.md` “测试目标”第 3 条与 `EMIT-010` 的用例描述。
   - 现状：文档描述 `LoopRange` -> `symbol.for` 且 DMA operand 直接保持 `!symbol.int`、不生成 `arith.index_cast`。
   - 实际测试：`test_for_ast_lowering_emits_loads` 断言 `scf.ForOp`，并显式容许 `_unwrap_index_cast`。
   - 影响：测试目标/用例映射与当前测试实现不一致，无法自洽。
   - 期望：二选一修正。
     - 方向 A：调整 `spec/dsl/emit_mlir.md` 的测试目标与 `EMIT-010` 描述，反映当前 `scf.for` + index_cast 行为；
     - 方向 B：保留现有 spec 目标，补齐测试覆盖 `symbol.for` 与 `symbol.int` 直传行为，并更新用例映射。

## 通过项

- `emit_mlir` 测试文件承载关系、执行命令与 `EMIT-001..013` 的用例映射在文件名与函数名层面一致。

## 测试

- 未运行（复审任务默认不复测）。

## 下一步建议

- 申请修正任务：按上述方向 A/B 之一收敛 `spec/dsl/emit_mlir.md` 测试目标与 `EMIT-010` 描述，确保与实际测试闭环一致。
