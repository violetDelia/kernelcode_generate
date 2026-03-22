# 2026-03-22 T-20260322-986df5db 合并记录

- 时间：2026-03-22 22:59:30 +0800
- 角色：`李白`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-expectation-add`
- 任务描述：合并 DSL pure symbol expectation add 链路到主分支（仅业务文件）。

## 合入文件

- `spec/dsl/mlir_gen.md`
- `kernel_gen/dsl/emit_mlir.py`
- `test/dsl/test_ast_visitor.py`

## 测试

- 未运行（任务要求默认不复测）。

## 结果

- 主分支提交：`cbb81544979c390a711a0e6843177a933035c473`

---

# 2026-03-22 T-20260322-15649d1f 实现记录

- 时间：2026-03-22 23:44:20 +0800
- 角色：`我不是牛马`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-expectation-add`
- 任务描述：根据 `spec/dsl/mlir_gen.md` 与 `spec/dialect/symbol.md` 收敛 `expectation/dsl/symbol.py` 纯 symbol 场景，使 add lowering 落到 `symbol.add`。

## 变更文件

- `expectation/dsl/symbol.py`
- `kernel_gen/dsl/emit_mlir.py`
- `test/dsl/test_ast_visitor.py`

## 实现说明

- 新增 `expectation/dsl/symbol.py`，收敛为纯 symbol 标量函数 `only_symbol(s: int) -> int`，函数体仅保留 `s + s` 场景，避免扩展到额外 symbol 常量/转换链路。
- 在 `kernel_gen/dsl/emit_mlir.py` 中为纯 `!symbol.int<"...">` 二元加法补齐最小 lowering：
  - 类型推导时，`BinaryExprAST(op="add")` 的两个 `SymbolValueType` 操作数会生成新的 `SymbolValueType` 结果。
  - 发射时生成 `symbol.add`，不再错误走 `nn.add`/`nn.memory` 路径。
- 在 `test/dsl/test_ast_visitor.py` 中补充 `test_symbol_scalar_function_lowers_add_to_symbol_add`，直接覆盖纯 symbol 函数 body 中的 `symbol.add` lowering。

## 测试

- 命令：`python expectation/dsl/symbol.py`
- 结果：通过
- 命令：`pytest -q test/dsl/test_ast_visitor.py -k 'symbol_scalar_function'`
- 结果：`2 passed, 46 deselected`
- 命令：`pytest -q test/dsl/test_ast_visitor.py`
- 结果：`48 passed`

## 剩余缺口

- 当前仅为任务要求补齐纯 symbol `add` 场景；`sub/mul`、symbol 常量参与 DSL lowering 等能力未扩展，保持现有边界。

## 下一步建议

- 申请复审任务，重点核对 `expectation/dsl/symbol.py`、`kernel_gen/dsl/emit_mlir.py`、`test/dsl/test_ast_visitor.py` 与 `spec/dsl/mlir_gen.md` / `spec/dialect/symbol.md` 的闭环一致性。

# T-20260322-e8138059

## 基本信息

- 任务 ID：`T-20260322-e8138059`
- 任务类型：`复审`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-expectation-add`
- 记录人：`不要啊教练`
- 时间：`2026-03-22 22:51:54 +0800`

## 审查目标

- 复核 `expectation/dsl/symbol.py`、`kernel_gen/dsl/emit_mlir.py`、`test/dsl/test_ast_visitor.py` 是否与 `spec/dsl/mlir_gen.md`、`spec/dialect/symbol.md` 闭环一致。
- 重点确认纯 symbol 场景 add lowering 为 `symbol.add`，且 `func.func` 输入/输出保持 `!symbol.int<"expr">`。
- 默认不复测。

## 审查结论

- 结论：`需修改`

## 问题清单

1. `spec/dsl/mlir_gen.md` 未包含纯 symbol add lowering 的测试目标映射（MGEN-018），但 `test/dsl/test_ast_visitor.py` 已新增 `test_symbol_scalar_function_lowers_add_to_symbol_add` 并标注为 MGEN-018。
   - 位置：`spec/dsl/mlir_gen.md` “测试”章节的测试目标/功能与用例清单。
   - 原因：spec 测试清单与实际测试用例不一致，违反映射闭环要求。
   - 建议：在 `spec/dsl/mlir_gen.md` 的测试目标与功能与用例清单中补充 MGEN-018，明确纯 symbol 标量加法 lowering 为 `symbol.add` 的覆盖，并映射到 `test_symbol_scalar_function_lowers_add_to_symbol_add`。

## 通过项

- `expectation/dsl/symbol.py` 的纯 symbol 场景使用 `s + s`，`emit_mlir.py` 在 symbol 标量二元加法时生成 `SymbolAddOp`，与 `spec/dialect/symbol.md` 中 `symbol.add` 语义一致。
- `test_symbol_scalar_function_uses_symbol_value_type_signature` 验证 `func.func` 的 `!symbol.int<"...">` 输入/输出口径，与 `spec/dsl/mlir_gen.md` 的 MGEN-016/017 一致。

## 测试情况

- 未运行测试（只读复审）。

## 下一阶段建议

- 申请 spec 修正任务：补齐 `spec/dsl/mlir_gen.md` 中 MGEN-018 的测试目标与用例映射，并说明纯 symbol add lowering 为 `symbol.add` 的闭环要求。

# T-20260322-14a2217d

## 基本信息

- 任务 ID：`T-20260322-14a2217d`
- 任务类型：`spec 修正`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-expectation-add`
- 记录人：`摸鱼小分队`
- 时间：`2026-03-22 23:59:00 +0800`

## 变更文件

- `spec/dsl/mlir_gen.md`

## 处理结果

- 在 `spec/dsl/mlir_gen.md` 的“测试目标”中补充纯 symbol 标量加法 lowering 为 `symbol.add` 的目标描述。
- 在“功能与用例清单”中新增 `MGEN-018`，显式映射到 `test/dsl/test_ast_visitor.py::test_symbol_scalar_function_lowers_add_to_symbol_add`，并关联 `expectation/dsl/symbol.py`。
- 未改实现与测试，未扩展到其他 DSL 链路。

## 测试情况

- 未复测（本轮仅最小修正 spec，任务要求不改实现/测试）。

## 结论

- 已完成本轮最小 spec 修正，`spec/dsl/mlir_gen.md` 与现有测试 `test_symbol_scalar_function_lowers_add_to_symbol_add` 的映射已闭环。

## 下一阶段建议

- 申请复审，重点核对 `spec/dsl/mlir_gen.md` 与 `test/dsl/test_ast_visitor.py` 的 `MGEN-018` 映射闭环。

---

# T-20260322-d642643d

## 基本信息

- 任务 ID：`T-20260322-d642643d`
- 任务类型：`复审`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-expectation-add`
- 记录人：`咯咯咯`
- 时间：`2026-03-22 23:46:12 +0800`

## 复审范围

- `spec/dsl/mlir_gen.md`
- `test/dsl/test_ast_visitor.py`

## 复审结论

- 结论：`通过`

## 核对要点

- `MGEN-018` 已补齐并映射到 `test_symbol_scalar_function_lowers_add_to_symbol_add`，表述与测试一致。
- `MGEN-016/017` 仍保持映射到 `test_symbol_scalar_function_uses_symbol_value_type_signature`，未被改动或覆盖。

## 测试情况

- 未运行测试（只读复审）。

## 下一阶段建议

- 建议进入下一阶段或关闭本链路。
