# T-20260323-62cbfa9d

## 基本信息

- 任务 ID：`T-20260323-62cbfa9d`
- 任务目标：按 `spec/dsl/mlir_gen.md` 最新口径收敛 DSL 链路，使 `expectation/dsl/add_scalar.py` 可直接运行。
- 约束：不修改 `expectation/dsl/add_scalar.py`；范围收敛在直接相关 DSL 实现/测试链路。

## 实现记录

- 在 `kernel_gen/dsl/ast.py` 为 `_parse_function_impl` / `_parse_annotation_node` 增加最小 `runtime_table` 支持，使未注解形参可按运行时实参推断 `Memory`、`SymbolDim` 与整数标量。
- 在 `kernel_gen/dsl/mlir_gen.py` 收敛 `build_func_op(fn, *runtime_args)` 入口，移除对 `globals/builtins/config` 的外部依赖，并让签名推导真正基于 `runtime_args`。
- 在 `kernel_gen/dsl/mlir_gen.py` 扩展 `build_func_op_from_ast(func_ast, runtime_args=None)`，在传入 `runtime_args` 时按运行时值决定纯 symbol 标量函数输入类型。
- 在 `kernel_gen/dialect/symbol.py` 为 `SymbolValueType` 补齐 `get_value()` / `is_symbol()`，兼容 `expectation/dsl/add_scalar.py` 的公开调用方式。
- 在 `test/dsl/test_ast_visitor.py` 补充 `MGEN-001A`，并把纯 symbol 标量签名测试改为仅依赖 `runtime_args`。

## 变更文件

- `kernel_gen/dsl/ast.py`
- `kernel_gen/dsl/mlir_gen.py`
- `kernel_gen/dialect/symbol.py`
- `test/dsl/test_ast_visitor.py`

## 验证结果

- `python expectation/dsl/add_scalar.py`
  - 结果：通过
- `pytest -q test/dsl/test_ast_visitor.py`
  - 结果：`52 passed in 0.39s`

## 结论

- 当前 `add_scalar` 场景已按 spec 跑通：
  - 未注解形参可由 `runtime_args` 推断；
  - `SymbolDim("s")` 与常量 `2` 都会收敛为 `!symbol.int<"...">` 输入；
  - 纯 symbol 标量加法仍 lowering 为 `symbol.add`。

## 下一步建议

- 申请复审任务，重点核对：
  - `build_func_op` / `build_func_op_from_ast` 与 `spec/dsl/mlir_gen.md` 的 runtime_args 口径是否完全闭环；
  - `SymbolValueType.get_value()` / `is_symbol()` 是否需要补充到 dialect 侧显式测试。

## 复审记录（2026-03-23）

- 任务类型：只读复审 expectation/dsl/add_scalar.py 运行链路
- 结论：通过
- 复审范围：
  - `spec/dsl/mlir_gen.md`
  - `kernel_gen/dsl/ast.py`
  - `kernel_gen/dsl/mlir_gen.py`
  - `kernel_gen/dialect/symbol.py`
  - `test/dsl/test_ast_visitor.py`
  - `expectation/dsl/add_scalar.py`
- 核对要点：
  - `build_func_op(fn, *runtime_args)` 仅依赖运行时参数推导签名，`SymbolDim` 与常量 `int` 在纯 symbol 标量函数中均收敛为 `SymbolValueType`。
  - `SymbolValueType.get_value()` / `is_symbol()` 语义与 `add_scalar` 断言一致，数值常量返回 `int` 且 `is_symbol()` 为 `False`。
  - `test_build_func_op_uses_runtime_args_only` 覆盖 `SymbolDim("s") + 2` 产生 `SymbolValueType.from_expr("s"/"2")` 与 `symbol.add` 的链路。
- 测试：未复测（按要求只读复审）
- 下一步建议：若需更严格验证，可补跑 `python expectation/dsl/add_scalar.py`；否则可进入后续收口/合并阶段。

## 合并收尾记录（2026-03-23）

- 任务类型：主仓最小收口 / 合并收尾
- 业务提交：`8e38bef` `T-20260323-62cbfa9d-merge-expectation-dsl-add-scalar-run`
- 实际合入文件：
  - `kernel_gen/dsl/ast.py`
  - `kernel_gen/dsl/mlir_gen.py`
  - `kernel_gen/dialect/symbol.py`
- 核对结论：
  - `test/dsl/test_ast_visitor.py` 在当前 `main` 上无该链路额外差异，本次按 no-op 处理，未单独合入。
  - `expectation/dsl/add_scalar.py` 按任务要求未修改。
- 测试：未复测（本轮任务默认不复测，沿用既有记录中的通过结果）
- 下一步建议：可按需要发起一次只读复核，确认 `test/dsl/test_ast_visitor.py` 当前断言集合是否已完整覆盖 runtime_args 收敛口径。
