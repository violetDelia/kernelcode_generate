# 2026-03-22 T-20260322-9bda4bbd 规格修正记录

- 时间：2026-03-22 21:44:48 +0800
- 角色：`李白`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-func-symbol-int-impl`
- 任务描述：收敛 `MGEN-016/017` 测试映射到符号函数签名用例。

## 结论

- 已完成。

## 改动文件

- `spec/dsl/mlir_gen.md`

## 变更摘要

- 将 `MGEN-016/017` 映射调整为 `test_symbol_scalar_function_uses_symbol_value_type_signature`，保持 expectation 场景映射一致。

## 测试

- 未复测（仅调整 spec 用例映射）。

## 下一步建议

- 申请复审：确认 `MGEN-016/017` 用例映射与 expectation/dsl/symbol.py 场景闭环一致。

# 2026-03-22 T-20260322-f6e12cc6 合并记录

- 时间：2026-03-22 20:18:34 +0800
- 角色：`小李飞刀`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-func-symbol-int`
- 任务描述：合并 symbol 函数签名约束说明相关 spec 变更。

## 合并结果

- 合入文件：
  - `spec/dialect/symbol.md`
  - `spec/dsl/mlir_gen.md`
- 提交号：`8ef1976`
- 合并说明：仅合并业务 spec 文件，未合入任何 task record 或其他非业务文件。

## 测试

- 未执行（spec 文档更新）。

## 清理结果

- `wt-20260322-dsl-symbol-func-symbol-int` 待清理（见回报）。

---

# T-20260322-c16b2765

## 基本信息

- 任务 ID：`T-20260322-c16b2765`
- 任务类型：`spec 收敛`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-func-symbol-int-impl`
- 记录人：`摸鱼小分队`
- 时间：`2026-03-22 22:45:00 +0800`

## 任务目标

- 仅修改 `spec/dsl/mlir_gen.md`，必要时最小修改 `spec/dialect/symbol.md`。
- 明确 `expectation/dsl/symbol.py` 对应纯 symbol 函数场景的参数/返回类型口径。
- 补充测试目标与映射，不改实现/测试。

## 本轮改动

- 更新 `spec/dsl/mlir_gen.md`：
  - 在 `依赖` 中补充 `spec/dialect/symbol.md` 与 `expectation/dsl/symbol.py`。
  - 将“纯符号标量函数暂不收敛”的旧口径收敛为正式要求：纯 symbol 标量函数的 `func.func` 输入与输出都必须使用 `!symbol.int<"expr">`。
  - 在 `build_func_op(...)` / `build_func_op_from_ast(...)` 的 `注意事项` 中补充：纯 symbol 标量函数不得 lowering 为 `i32/index` 等 builtin 标量类型，必须复用 `SymbolValueType`。
  - 在 `测试目标` 中补充 `expectation/dsl/symbol.py` 对应场景的签名约束。
  - 新增 `MGEN-016`、`MGEN-017`，明确纯 symbol 函数的参数/返回类型收敛目标，并与后续 expectation/test 闭环对应。
- 未修改 `spec/dialect/symbol.md`；当前 `!symbol.int<"expr">` 语义已足够承接本轮 `mlir_gen` 约束。

## 测试情况

- 未运行测试；本轮仅改 spec，不改实现/测试。

## 结论

- 已完成纯 symbol 函数签名口径的 spec 收敛。
- 当前 `mlir_gen` spec 已明确：`expectation/dsl/symbol.py` 对应链路的 `func.func` 输入与输出都必须为 `!symbol.int<"expr">`。

## 下一阶段建议

- 建议创建下一阶段实现/测试任务：收敛 `kernel_gen/dsl/mlir_gen.py` 与 `test/dsl/test_ast_visitor.py`，使纯 symbol 函数场景不再使用 `i32`，并补齐 `MGEN-016`、`MGEN-017` 对应测试。

---

# T-20260322-8fc25d61

## 基本信息

- 任务 ID：`T-20260322-8fc25d61`
- 任务类型：`实现/测试收敛`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-func-symbol-int-impl`
- 记录人：`朽木露琪亚`
- 时间：`2026-03-22 21:35:06 +0800`

## 任务目标

- 在 `spec/dsl/mlir_gen.md` 已收敛口径下，最小修复 `expectation/dsl/symbol.py` 链路。
- 使纯 symbol 标量函数生成的 `func.func` 输入与输出都使用 `!symbol.int<"expr">`。
- 不回退到 `i32`、`index` 等 builtin 标量类型，不扩张额外功能。

## 本轮改动

- 更新 `kernel_gen/dsl/mlir_gen.py`：
  - 新增纯 symbol 标量函数识别分支：当函数输入/输出均为 `ScalarArgAST(int)` 时，`func.func` 签名中的对应参数改为 `SymbolValueType.from_expr(<arg_name>)`。
  - 放宽“至少一个 tensor 输入”的约束，仅对纯 symbol 标量函数放行；其他路径保持原有约束。
  - 调整标量返回校验：纯 symbol 标量函数要求返回结果为 `SymbolValueType`，不再固定要求 `i32`。
- 新增 `expectation/dsl/symbol.py`：
  - 提供可直接执行的纯 symbol 标量函数基线脚本。
  - 运行后打印 `func.func @only_symbol(%0 : !symbol.int<"expr">) -> !symbol.int<"expr">`，并对输入/输出类型做断言。
- 更新 `test/dsl/test_ast_visitor.py`：
  - 保留原有混合 `tensor + int` 场景测试。
  - 新增 `test_symbol_scalar_function_uses_symbol_value_type_signature`，覆盖纯 symbol 标量函数输入/输出签名使用 `!symbol.int<"expr">` 的场景。
- 最小修正 `kernel_gen/dsl/__init__.py`：
  - 移除对当前 worktree 中不存在的 `emit_c.py`、`gen_kernel.py` 的导入与导出，避免 `kernel_gen.dsl` 包在 expectation 脚本和 pytest 收集阶段直接报 `ModuleNotFoundError`。

## 测试情况

- 执行：`python expectation/dsl/symbol.py`
  - 结果：通过。
  - 关键输出：`func.func @only_symbol(%0 : !symbol.int<"expr">) -> !symbol.int<"expr">`
- 执行：`pytest -q test/dsl/test_ast_visitor.py`
  - 结果：`47 passed in 0.31s`

## 结论

- 纯 symbol 标量函数链路已按 spec 收敛到 `!symbol.int<"expr">` 输入/输出口径。
- `expectation/dsl/symbol.py` 已可直接运行。
- 当前最小闭环已完成，未引入 `i32/index` 回退。

## 下一阶段建议

- 建议创建下一阶段复审任务，重点核对：
  - `kernel_gen/dsl/mlir_gen.py` 的纯 symbol 标量函数识别边界是否满足当前 spec；
  - `kernel_gen/dsl/__init__.py` 的导出收敛是否与 DSL 当前主线职责一致；
  - `expectation/dsl/symbol.py`、`test/dsl/test_ast_visitor.py` 与 `MGEN-016`、`MGEN-017` 的闭环是否可直接通过。

---

# 2026-03-22 T-20260322-9ec0c429 复审记录

- 时间：2026-03-22 22:23:16 +0800
- 角色：`不要啊教练`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-func-symbol-int-impl`
- 任务描述：复审纯 symbol 标量函数的 func.func 签名收敛与映射闭环。

## 结论

- 不通过。

## 复审文件

- `spec/dsl/mlir_gen.md`
- `kernel_gen/dsl/mlir_gen.py`
- `kernel_gen/dsl/__init__.py`
- `test/dsl/test_ast_visitor.py`
- `expectation/dsl/symbol.py`

## 一致性检查结果

- `expectation/dsl/symbol.py` 生成的 `func.func` 输入与输出均为 `!symbol.int<"expr">`，未回退为 `i32/index`。
- `kernel_gen/dsl/mlir_gen.py` 的纯 symbol 标量函数识别与返回类型校验符合 spec 口径。
- `kernel_gen/dsl/__init__.py` 仅导出 `parse_function`/`build_func_op` 等 DSL 主入口，未新增越界公开接口。

## 未通过原因（需改进）

1. `spec/dsl/mlir_gen.md` 的 `MGEN-016/017` 映射仍指向 `test_scalar_arg_lowering_in_signature`，但实际测试为 `test_symbol_scalar_function_uses_symbol_value_type_signature`，且前者覆盖的是 `i32` 标量路径。
   - 影响：测试目标与用例映射不闭环，违反 AGENTS.md 的测试清单一一对应要求。
   - 建议：将 `MGEN-016/017` 映射调整为 `test_symbol_scalar_function_uses_symbol_value_type_signature`（并保留 `expectation/dsl/symbol.py`），避免与 `MGEN-006` 的 `i32` 路径混淆。

## 测试

- 未复测（只读复审）。

## 下一步建议

- 建议创建 **spec 改进任务**：修正 `MGEN-016/017` 的测试映射后再复审。

---

# T-20260322-ce306303

## 基本信息

- 任务 ID：`T-20260322-ce306303`
- 任务类型：`spec 复审`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-func-symbol-int-impl`
- 记录人：`咯咯咯`
- 时间：`2026-03-22 22:31:42 +0800`

## 复审范围

- `spec/dsl/mlir_gen.md`
- `expectation/dsl/symbol.py`
- `kernel_gen/dsl/mlir_gen.py`
- `test/dsl/test_ast_visitor.py`

## 复审结论

- 结论：`通过`

## 核对要点

- `MGEN-016/017` 已映射到 `test_symbol_scalar_function_uses_symbol_value_type_signature`，并保留 `expectation/dsl/symbol.py` 作为场景基线。
- `expectation/dsl/symbol.py` 断言 `func.func` 输入/输出为 `SymbolValueType.from_expr("expr")`。
- `kernel_gen/dsl/mlir_gen.py` 在纯 symbol 标量函数场景使用 `SymbolValueType` 生成签名与返回类型。
- `test/dsl/test_ast_visitor.py` 中对应测试断言与 expectation 一致，形成闭环。

## 测试情况

- 未运行测试（只读复审）。

## 下一步建议

- 建议进入下一阶段任务或关闭本链路。

# 2026-03-22 T-20260322-ddd5b6c2 合并记录

- 时间：2026-03-22 21:49:10 +0800
- 角色：`小李飞刀`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-symbol-func-symbol-int-impl`
- 任务描述：合并 expectation/dsl/symbol.py 链路业务改动。

## 合并结果

- 合入文件：
  - `spec/dsl/mlir_gen.md`
  - `kernel_gen/dsl/mlir_gen.py`
  - `kernel_gen/dsl/__init__.py`
  - `test/dsl/test_ast_visitor.py`
- 未合入文件：
  - `expectation/dsl/symbol.py`（与主分支无差异，no-op）
- 提交号：`00836b2`
- 合并说明：仅合入业务文件，未合入 task record 或其他非业务文件。

## 测试

- 未执行（沿用既有复审通过结果）。

## 清理结果

- `wt-20260322-dsl-symbol-func-symbol-int-impl` 待清理（见回报）。
