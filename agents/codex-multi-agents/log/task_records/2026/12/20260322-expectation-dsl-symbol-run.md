# 2026-03-22 T-20260322-e83d6531 实现记录

- 时间：2026-03-22 23:55:33 +0800
- 角色：`我不是牛马`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-expectation-dsl-symbol-run`
- 任务描述：跑通 `expectation/dsl/symbol.py`，确保纯 symbol 函数场景可运行，并保持 `add lowering = symbol.add`、`func.func` 输入/输出为 `!symbol.int<"expr">`。

## 变更文件

- `expectation/dsl/symbol.py`

## 处理过程

- 基线执行 `python expectation/dsl/symbol.py` 失败，原因是目标文件不存在。
- 在授权 worktree 中最小补齐 `expectation/dsl/symbol.py`，复用现有 DSL pure symbol lowering 主线：
  - `only_symbol(s: int) -> int`
  - 函数体使用 `s + s`
  - 由 `build_func_op(only_symbol)` 直接作为验收入口
- 首次补齐后再次执行 expectation，定位到函数内 docstring 会被 DSL 解析为函数体首条语句，并在 lowering 时触发 `Unsupported constant type`；随后移除函数体 docstring，改为函数前注释，保持 DSL 可解析。

## 测试

- 命令：`python expectation/dsl/symbol.py`
- 结果：通过
- 命令：`pytest -q test/dsl/test_ast_visitor.py -k 'symbol_scalar_function or lowers_add_to_symbol_add'`
- 结果：`2 passed, 46 deselected`
- 命令：`pytest -q test/dsl/test_ast_visitor.py`
- 结果：`48 passed`

## 结论

- 当前 `expectation/dsl/symbol.py` 已可运行。
- 直接相关 DSL 测试保持通过，纯 symbol 场景仍满足：
  - `func.func` 输入/输出为 `!symbol.int<"expr">`
  - `add` lowering 为 `symbol.add`

## 下一步建议

- 可创建复审任务，重点核对 `expectation/dsl/symbol.py` 与 `spec/dsl/mlir_gen.md`、`spec/dialect/symbol.md` 的 expectation 闭环。

---

# T-20260322-80991958

## 基本信息

- 任务 ID：`T-20260322-80991958`
- 任务类型：`复审`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-expectation-dsl-symbol-run`
- 记录人：`咯咯咯`
- 时间：`2026-03-23 00:12:09 +0800`

## 复审范围

- `expectation/dsl/symbol.py`
- `spec/dsl/mlir_gen.md`
- `spec/dialect/symbol.md`

## 复审结论

- 结论：`需修改`

## 问题清单

1. `expectation/dsl/symbol.py` 仅调用 `build_func_op(only_symbol)`，未断言 `func.func` 输入/输出为 `!symbol.int<"expr">`，也未校验 `symbol.add` 是否生成，无法证明与 `MGEN-016/017/018` 的 expectation 闭环一致。
   - 影响：无法在 expectation 层面验证“纯 symbol add lowering 为 symbol.add、签名保持 !symbol.int<...>”的关键要求，复审无法确认闭环。
   - 建议修正：在 expectation 脚本中补齐最小断言：
     - 使用 `SymbolValueType.from_expr("...")` 检查 `func_op.function_type.inputs/outputs`；
     - 遍历 `func_op.body` 断言存在 `SymbolAddOp` 或打印文本包含 `symbol.add`。

## 测试情况

- 未运行测试（只读复审）。

## 下一步建议

- 申请最小改进任务：补齐 expectation 中的签名与 `symbol.add` 断言后再复审。

# T-20260322-7c353c69

## 基本信息

- 任务 ID：`T-20260322-7c353c69`
- 任务类型：`最小改进`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-expectation-dsl-symbol-run`
- 记录人：`摸鱼小分队`
- 时间：`2026-03-23 00:08:00 +0800`

## 变更文件

- `expectation/dsl/symbol.py`

## 处理结果

- 为 `build_func_op(only_symbol)` 结果补齐最小断言：
  - 断言 `func.func` 输入为 `SymbolValueType.from_expr("s")`
  - 断言输出列表长度为 `1`，且输出类型为 `SymbolValueType`
  - 断言函数体中存在唯一一个 `SymbolAddOp`
  - 断言打印文本包含 `symbol.add` 与 `-> !symbol.int<...>`，证明纯 symbol add 已 lowering 为 `symbol.add`，且返回保持 `!symbol.int<"expr">`
- 未改实现与测试，未扩展到其他 DSL 链路。

## 执行结果

- 命令：`python expectation/dsl/symbol.py`
- 结果：通过

## 结论

- expectation 层已补齐最小自校验，可直接证明纯 symbol 函数场景的 `func.func` 输入/输出保持 `!symbol.int<"expr">`，且纯 symbol add lowering 为 `symbol.add`。

## 下一步建议

- 申请复审，确认 `expectation/dsl/symbol.py` 与 `spec/dsl/mlir_gen.md`、`spec/dialect/symbol.md` 的 expectation 闭环。

## 补充修正（用户口径更新）

- 按用户更正，将 expectation 场景从“函数参数直接视为 symbol int”修正为“函数输入来源于 `SymbolDim("expr")`，但 lowering 后 `func.func` 输入类型必须为 `!symbol.int<"expr">`”。
- `expectation/dsl/symbol.py` 现使用：
  - `expr = SymbolDim("expr")`
  - `build_func_op(only_symbol, globals={"expr": expr, "__builtins__": __builtins__})`
- 断言已同步收敛为：
  - 输入列表等于 `[SymbolValueType.from_expr("expr")]`
  - 输出仍为单个 `SymbolValueType`
  - 文本包含 `symbol.add` 与 `!symbol.int<...>`，证明 symbol dim 输入 lowering 后不会把函数签名保留为 symbol dim

## 补充执行结果

- 命令：`python expectation/dsl/symbol.py`
- 结果：通过

---

# 2026-03-23 T-20260322-537f1ee9 复审记录

- 时间：2026-03-23 00:18:00 +0800
- 角色：`朽木露琪亚`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-expectation-dsl-symbol-run`
- 任务描述：只读复审 `expectation/dsl/symbol.py` 更正链路，核对其是否按 `spec/dsl/mlir_gen.md` 与 `spec/dialect/symbol.md` 收敛。

## 结论

- 通过。

## 复审文件

- `expectation/dsl/symbol.py`
- `spec/dsl/mlir_gen.md`
- `spec/dialect/symbol.md`
- `kernel_gen/dsl/ast.py`
- `kernel_gen/dsl/mlir_gen.py`
- `kernel_gen/dsl/emit_mlir.py`

## 一致性检查结果

- `expectation/dsl/symbol.py` 已按用户口径把输入来源收敛为 `SymbolDim("expr")`：
  - 文件中定义 `expr = SymbolDim("expr")`；
  - `build_func_op(...)` 调用显式传入 `globals={"expr": expr, "__builtins__": __builtins__}`。
- AST 解析与 `mlir_gen` 主线一致：
  - `kernel_gen/dsl/ast.py` 会把全局环境中的 `SymbolDim` 名称解析为 `ScalarArgAST(name=..., value_type=int)`；
  - `kernel_gen/dsl/mlir_gen.py` 对纯 symbol 标量函数入参统一降为 `SymbolValueType.from_expr(item.name)`，不会退回 builtin `i32/index`。
- expectation 已显式断言 `func.func` 输入类型为 `!symbol.int<"expr">`：
  - `inputs == [SymbolValueType.from_expr("expr")]`。
- expectation 已保持输出位于 `symbol dialect` 的 `SymbolValueType`，且打印文本中包含 `-> !symbol.int<...>`，与 `spec/dsl/mlir_gen.md` 对纯 symbol 返回保持 `!symbol.int<"...">` 的要求一致。
- 纯 symbol 加法 lowering 已与 `spec/dialect/symbol.md` 一致：
  - `kernel_gen/dsl/emit_mlir.py` 对两个 `SymbolValueType` 操作数的 `add` 发射 `SymbolAddOp`；
  - expectation 同时断言函数体中存在唯一一个 `SymbolAddOp`，且打印文本包含 `symbol.add`。

## 测试

- 本轮未复测。
- 说明：任务要求默认不复测；本次以 expectation 脚本、spec、实现与已有记录中的执行结果为准完成只读复审。

## 下一步建议

- 当前链路无需继续补 expectation 改进任务。
- 若后续继续扩展纯 symbol 标量运算，可单独创建新任务补齐 `symbol.sub` / `symbol.mul` expectation 场景，避免与本轮 `symbol.add` 基线混合。
# 2026-03-22 T-20260322-2ae694f3 合并记录

- 时间：2026-03-22 23:20:01 +0800
- 角色：`李白`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-expectation-dsl-symbol-run`
- 任务描述：合并 expectation/dsl/symbol.py 运行闭环链路（仅业务文件）。

## 合入结果

- 结论：与 main 无差异，未产生提交。
- 对比文件：
  - `expectation/dsl/symbol.py`

## 测试

- 未运行（任务要求默认不复测）。

---
