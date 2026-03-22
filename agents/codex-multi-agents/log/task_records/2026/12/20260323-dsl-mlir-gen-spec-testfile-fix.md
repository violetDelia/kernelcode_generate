# 2026-03-23 T-20260323-ae381917

- 任务 ID：`T-20260323-ae381917`
- 任务类型：`spec`
- worktree：`main`（当前任务未实际使用独立 worktree）
- 记录人：`摸鱼小分队`
- 时间：`2026-03-23`

## 变更文件

- `spec/dsl/mlir_gen.md`

## 处理结果

- 最小修正 `spec/dsl/mlir_gen.md` 的测试链路描述，明确当前仓内并不存在独立的 `test/dsl/test_mlir_gen.py`。
- 将 `mlir_gen` 链路测试收敛为仓内实际承载文件 [`test/dsl/test_ast_visitor.py`](../../../../test/dsl/test_ast_visitor.py)，并在文档信息与测试章节中显式说明该文件当前承载 `MGEN-*` 用例。
- 将执行命令收敛为 `test/dsl/test_ast_visitor.py` 中 `mlir_gen` 相关子集的 `-k` 过滤命令，避免继续以整份 `ast_visitor` 测试文件笼统代表 `mlir_gen` 链路。
- 补充测试目标中的运行时参数错误路径说明，并在功能与用例清单中补齐 `MGEN-019` 与现有三个对应测试函数的映射。

## 测试

- 未运行测试（本轮仅改 spec，按任务要求不修改实现、测试与 expectation）。

## 结论

- 已完成本轮最小 spec 修正，`mlir_gen` 的测试文件、执行命令与 `MGEN-*` 映射已按仓内实际测试文件现状收敛。

## 剩余缺口

- 当前仓内仍未独立拆分 `test/dsl/test_mlir_gen.py`；`mlir_gen`、`ast_visitor`、`emit_mlir` 仍共用 `test/dsl/test_ast_visitor.py`。
- 若后续希望彻底实现“物理文件级”的 `test_mlir_gen` 收敛，还需单独发起测试文件拆分任务。

## 下一阶段建议

- 建议发起复审任务，确认 `spec/dsl/mlir_gen.md` 的测试链路描述与仓内实际 `MGEN-*` 用例完全一致。
- 若用户要求独立测试文件，再拆一个实现/测试任务，将 `mlir_gen` 用例从 `test/dsl/test_ast_visitor.py` 中拆分为单独的 `test_mlir_gen.py`。
