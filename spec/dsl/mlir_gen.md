# mlir_gen.md

## 功能简介

- 综合 AST 解析、AST 遍历与节点发射规则，将 Python 函数转换为 MLIR `func.func` op。
- 统一约束函数签名、参数与返回值的生成规则。
- 不生成 module，不负责文本打印。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `功能实现`：[`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)、[`python/dsl/mlir_gen.py`](../../python/dsl/mlir_gen.py)（统一规范覆盖两条实现入口）
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)（当前仓内 `mlir_gen` 链路测试承载文件，尚未独立拆分为 `test_mlir_gen.py`）

## 依赖

- AST 节点与解析入口：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 遍历访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- 节点发射规则：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- 符号值类型语义：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- 纯 symbol 函数场景基线：[`expectation/dsl/symbol.py`](../../expectation/dsl/symbol.py)
- 整型标量加法 expectation 基线：[`expectation/dsl/mlir_gen/add_scalar.py`](../../expectation/dsl/mlir_gen/add_scalar.py)
- `LoopRange` + DMA 切片场景基线：[`expectation/dsl/for_loop.py`](../../expectation/dsl/for_loop.py)

## 目标

- 以统一入口生成 `func.func` op。
- 保证函数签名、参数顺序与返回类型与 AST 一致。
- 使用函数实际接收的运行时参数推导 `func.func` 输入签名。
- 为上层打印或封装提供稳定的 func op 结果。
- 为 `expectation/dsl/mlir_gen/add_scalar.py` 这类整型标量函数场景定义稳定的 `func.func` / `symbol.add` lowering 口径。

## 限制与边界

- 不生成 `builtin.module`。
- 不负责 MLIR 文本打印或后端代码生成。
- 不定义节点级发射细节，节点发射规则由 `emit_mlir` 约束。
- 不做优化或自动修复非法 IR。
- `build_func_op` 只接收目标函数与运行时参数，不再接收 `globals`、`builtins`、`config` 一类额外解析参数。
- 运行时参数必须按目标函数形参顺序传入；数量不一致、顺序不一致或类型无法映射时必须报错。
- 运行时参数的类型 lowering 必须基于“实际传入的参数对象”决定，而不是基于额外配置推断。
- 当运行时参数为 `SymbolDim("s")` 这类 symbol 标量时，对应的 `func.func` 输入必须 lowering 为 `!symbol.int<"s">`；若为常量 symbol，例如 `SymbolDim(1)`，则必须 lowering 为 `!symbol.int<"1">`。
- 当运行时参数是 Python `int` 且函数场景属于 symbol 整型标量运算时，对应的 `func.func` 输入必须 lowering 为携带具体整数值的 `SymbolValueType`，不得退回 `i32`、`index` 或其他 builtin 标量类型；若整数值为负数，对外字符串口径必须与 acceptance gate 一致，直接表现为十进制负数字面量，例如 `symbol.int<-7>`。
- 当函数体仅包含 `for` 循环且没有 `return` 时，输出 `func.func` 允许零返回值。
- 当 `ForAST` 来源于 `LoopRange(start, end, step)` 且循环边界保持 symbol 整数语义时，lowering 后必须生成 `symbol.for`，不得退回 `scf.for`；其循环块参数 `it` 必须为 `!symbol.int<"expr">`。
- `LoopRange` 场景中的循环变量以及传入 `dma.slice` / `dma.deslice` 的 `offsets`、`sizes`、`strides` 等 DMA 标量 operand，必须直接保持 `!symbol.int<"expr">` 语义传递，不得额外生成 `arith.index_cast`。
- 对于纯 symbol 标量函数（仅符号标量入参/返回），函数签名中的输入与输出必须统一使用 `!symbol.int<"expr">`，不得降级为 `i32`、`index` 或其他 builtin 标量类型。
- `expectation/dsl/symbol.py` 对应的函数场景属于纯 symbol 标量函数：其生成结果中的 `func.func` 输入与输出都必须落在 `symbol dialect` 的 `!symbol.int<"expr">` 上。
- `expectation/dsl/mlir_gen/add_scalar.py` 对应的函数场景属于整型标量 runtime-arg lowering：`build_func_op(add, lhs, rhs)` 中的 `lhs`、`rhs` 为普通 Python `int` 时，生成结果中的 `func.func` 输入必须为携带具体整数值的 `SymbolValueType`，函数体必须生成 `symbol.add`，并保持结果值语义与 `lhs + rhs` 一致；若 `lhs` 或 `rhs` 为负数，必须仍能稳定 lowering，且 `str(SymbolValueType)` 的对外表现必须保持十进制负数字面量口径。
- `expectation/dsl/mlir_gen/add_scalar.py` 在后续实现阶段的运行成功口径为：`python expectation/dsl/mlir_gen/add_scalar.py` 可直接运行成功，且其对 `FuncOp`、输入 `SymbolValueType`、`SymbolAddOp` 与结果值语义的断言全部成立；本阶段只定义该口径，不修改 expectation 文件。
- 如需 `builtin.module` 封装，由调用方完成。

## 公开接口

### `build_func_op(fn, *runtime_args)`

功能说明：

- 解析 Python 函数并生成 `func.func` op。
- 内部依次调用 `parse_function(...)`、`AstVisitor` 与 `emit_mlir`。
- `func.func` 的输入签名由 `runtime_args` 的实际值语义决定。

参数说明：

- `fn` (`callable`)：受限 Python 函数。
- `runtime_args` (`tuple[object, ...]`)：目标函数实际传入的运行时参数，顺序必须与 `fn` 的形参顺序一致。

使用示例：

```python
func_op = build_func_op(add, A, B)
```

```python
s = SymbolDim("s")
func_op = build_func_op(only_symbol, s)
```

注意事项：

- 解析失败或发射失败必须抛出可定位的错误。
- 不允许通过 `globals`、`builtins`、`config` 或其他额外参数改变函数签名推导行为。
- `runtime_args` 的个数必须与函数形参数量一致。
- 张量类运行时参数应按其对应 spec lowering 为项目内的 memory type。
- `SymbolDim("s")` 这类运行时参数必须 lowering 为 `!symbol.int<"s">`；`SymbolDim(1)` 这类常量 symbol 必须 lowering 为 `!symbol.int<"1">`。
- 当 `runtime_args` 为普通 Python `int` 且对应 `expectation/dsl/mlir_gen/add_scalar.py` 这类整型标量函数时，输入参数必须 lowering 为携带该整数值的 `SymbolValueType`，而不是 builtin 整数类型；负数实参的对外字符串表示必须保持 `symbol.int<-3>` 这类十进制负数字面量形式。
- 允许 `for` 循环内包含 `dma.slice`/`dma.deslice` 相关语义；当循环来自 `LoopRange` 且边界为 symbol 整数时，必须保留 `symbol.for` 结构，且迭代变量 `it` 不能退化为 `index`、`i32`、浮点或其他非 `SymbolValueType`。
- 当 `fn` 对应 `expectation/dsl/symbol.py` 这类纯 symbol 标量函数时，输入参数与返回值都必须 lowering 为 `!symbol.int<"expr">`。
- 当 `fn` 对应 `expectation/dsl/mlir_gen/add_scalar.py` 这类整型标量加法函数时，函数体中的标量加法必须 lowering 为 `symbol.add`，且结果类型保持为携带具体整数值的 `SymbolValueType`。
- 纯 symbol 标量函数的参数/返回类型必须复用 `spec/dialect/symbol.md` 中定义的 `SymbolValueType`，不能退回 builtin 整数类型。
- `LoopRange` 场景中传给 `dma.slice` / `dma.deslice` 的标量 operand 必须直接复用 `!symbol.int<"expr">` value，不允许通过 `arith.index_cast` 做中间桥接。

返回与限制：

- 返回 `func.func` op。
- 不返回 module。

### `build_func_op_from_ast(func_ast, runtime_args)`

功能说明：

- 基于已构建的 `FunctionAST` 生成 `func.func` op。
- 不重复解析 Python 源码。
- `func.func` 的输入签名由 `runtime_args` 的实际值语义决定。

参数说明：

- `func_ast` (`FunctionAST`)：函数 AST。
- `runtime_args` (`tuple[object, ...] | list[object]`)：目标函数实际传入的运行时参数，顺序必须与 `func_ast.inputs` 一致。

使用示例：

```python
func_ast = parse_function(add)
func_op = build_func_op_from_ast(func_ast, [A, B])
```

注意事项：

- 输入 AST 必须满足 `ast.md` 的结构约束。
- `runtime_args` 必须与 `func_ast.inputs` 一一对应。
- 若 `runtime_args` 中存在 `SymbolDim("s")` 这类 symbol 标量，对应输入必须 lowering 为 `!symbol.int<"s">`。
- 若 AST 仅包含符号标量输入/输出，则生成的 `func.func` 签名必须保持 `!symbol.int<"expr">` 输入与返回，不得改写为 builtin 标量类型。

返回与限制：

- 返回 `func.func` op。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)（当前仓内 `mlir_gen` 链路实际承载文件；`test_mlir_gen` 尚未独立拆分）
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py -k 'test_build_func_op or test_visit_to_nn_ir_builds_module or test_emit_mlir_output or test_scalar_arg_lowering_in_signature or test_symbol_scalar_function_uses_symbol_value_type_signature or test_symbol_scalar_function_lowers_add_to_symbol_add or test_invalid_tensor_return_annotation_reports_diagnostics or test_constant_lowering_reports_diagnostics or test_return_type_mismatch_reports_diagnostics or test_multi_statement_ssa_order_and_reuse or test_build_func_op_supports_symbolic_for_loop_dma_without_return or test_tensor_binary_implicit_broadcast_lowering or test_tensor_binary_prepend_broadcast_lowering or test_compare_implicit_broadcast_lowering or test_tensor_binary_implicit_broadcast_mismatch_reports_diagnostics or test_build_func_op_add_scalar_runtime_ints_lower_to_symbol_value_type'`；`python expectation/dsl/mlir_gen/add_scalar.py`（后续实现阶段的 expectation 验收命令，本阶段只定义成功口径）
- 测试目标：
  - 明确当前仓内未独立存在 `test/dsl/test_mlir_gen.py`；`mlir_gen` 链路测试由 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 中的 `MGEN-*` 用例实际承载。
  - 验证 `build_func_op(...)` 生成 `func.func`。
  - 验证 `build_func_op(fn, *runtime_args)` 仅通过运行时参数推导输入签名。
  - 验证 `build_func_op(...)` 缺少运行时参数、运行时实参数量不匹配，以及额外 `globals/builtins` 调用方式的错误路径。
  - 验证函数签名与返回值类型与 AST 一致。
  - 通过测试辅助封装验证 `func.func` 的结构输出（不改变本模块的边界）。
  - 覆盖无返回 `for` 循环与 `slice/deslice` 的生成能力，并要求 `LoopRange` lowering 为 `symbol.for`，且循环迭代变量 `it` 保持 `!symbol.int<"...">`。
  - 验证 `expectation/dsl/symbol.py` 对应的纯 symbol 函数场景会生成 `!symbol.int<"...">` 输入与 `!symbol.int<"...">` 返回。
  - 验证纯 symbol 标量加法在 lowering 后生成 `symbol.add`，不退回 builtin 算术或其他 dialect op。
  - 验证 `expectation/dsl/mlir_gen/add_scalar.py` 对应的整型标量函数场景中，`build_func_op(add, lhs, rhs)` 会把 Python `int` 实参 lowering 为携带具体整数值的 `SymbolValueType` 输入，并生成满足 expectation 断言的 `symbol.add` 结果。
  - 验证 `expectation/dsl/mlir_gen/add_scalar.py` 中随机出现的负数 Python `int` 实参不会导致 lowering 失败；负值的 `SymbolValueType.__str__` 必须保持 `symbol.int<-3>` 这类十进制负数字面量口径，且 `get_value()` 可还原原始负数值。
  - 明确 `expectation/dsl/mlir_gen/add_scalar.py` 保持只读；后续实现阶段以 `python expectation/dsl/mlir_gen/add_scalar.py` 运行成功作为 acceptance gate。
  - 验证 `expectation/dsl/for_loop.py` 对应场景生成 `symbol.for + dma.slice/dma.deslice`，且循环相关 lowering 不生成 `arith.index_cast`。
- 功能与用例清单：
  - MGEN-001：`build_func_op(...)` 返回 `func.func`。（`test_build_func_op_returns_func_op`）
  - MGEN-001A：`build_func_op(...)` 只接收 `fn + runtime_args`，不依赖额外上下文参数推导签名。（`test_build_func_op_uses_runtime_args_only`）
  - MGEN-002：参数顺序与 AST 一致。（`test_build_func_op_from_ast_preserves_arg_order`）
  - MGEN-003：返回值类型与 AST 对齐。（`test_build_func_op_return_type_matches_annotation`）
  - MGEN-004：经测试辅助封装后 module 含 `func.func`/`nn` op。（`test_visit_to_nn_ir_builds_module`）
  - MGEN-005：经测试辅助打印文本包含 `func.func`/`nn`。（`test_emit_mlir_output`）
  - MGEN-006：标量参数 lowering 为 `func.func` 标量输入。（`test_scalar_arg_lowering_in_signature`）
  - MGEN-007：Tensor 返回注解不匹配时报错。（`test_invalid_tensor_return_annotation_reports_diagnostics`）
  - MGEN-008：常量返回 lowering 失败时报错。（`test_constant_lowering_reports_diagnostics`）
  - MGEN-009：返回类型不匹配时报错。（`test_return_type_mismatch_reports_diagnostics`）
  - MGEN-010：多语句 SSA 顺序与复用。（`test_multi_statement_ssa_order_and_reuse`）
  - MGEN-011：逐元素二元隐式 broadcast。（`test_tensor_binary_implicit_broadcast_lowering`）
  - MGEN-012：前置维度隐式 broadcast。（`test_tensor_binary_prepend_broadcast_lowering`）
  - MGEN-013：比较表达式隐式 broadcast。（`test_compare_implicit_broadcast_lowering`）
  - MGEN-014：不可 broadcast 报错与定位。（`test_tensor_binary_implicit_broadcast_mismatch_reports_diagnostics`）
  - MGEN-015：`expectation/dsl/for_loop.py` 对应的 `LoopRange + slice/deslice + 无 return` 场景生成 `symbol.for + dma.slice/dma.deslice`，且循环迭代变量 `it` 与 DMA operand 直接保持 `!symbol.int<"...">`，不生成 `arith.index_cast`。（`test_build_func_op_supports_symbolic_for_loop_dma_without_return`、`expectation/dsl/for_loop.py`）
  - MGEN-016：`expectation/dsl/symbol.py` 的纯 symbol 函数参数 lowering 为 `func.func` 的 `!symbol.int<"...">` 输入。（`test_symbol_scalar_function_uses_symbol_value_type_signature`、`expectation/dsl/symbol.py`）
  - MGEN-017：`expectation/dsl/symbol.py` 的纯 symbol 函数返回 lowering 为 `func.func` 的 `!symbol.int<"...">` 输出。（`test_symbol_scalar_function_uses_symbol_value_type_signature`、`expectation/dsl/symbol.py`）
  - MGEN-018：纯 symbol 标量加法 lowering 为 `symbol.add`。（`test_symbol_scalar_function_lowers_add_to_symbol_add`、`expectation/dsl/symbol.py`）
  - MGEN-019：`build_func_op` 的运行时参数为必填且只接受 `fn + runtime_args`；省略实参、实参数量不匹配或试图以 `globals/builtins` 替代时必须报错。（`test_build_func_op_requires_explicit_runtime_args`、`test_build_func_op_rejects_runtime_arg_count_mismatch`、`test_build_func_op_globals_and_builtins_cannot_replace_runtime_args`）
  - MGEN-020：`expectation/dsl/mlir_gen/add_scalar.py` 场景中，`build_func_op(add, lhs, rhs)` 对普通 Python `int` runtime args 的 lowering 必须产出携带具体整数值的 `SymbolValueType` 输入；若实参包含负数，其对外字符串表示必须保持 `symbol.int<-3>` 这类十进制负数字面量口径，并在函数体内生成满足 expectation 断言的 `symbol.add` 结果。当前 pytest 映射基线由 `test_build_func_op_add_scalar_runtime_ints_lower_to_symbol_value_type` 承载，最终验收以 `expectation/dsl/mlir_gen/add_scalar.py` 只读运行成功为准。（`test_build_func_op_add_scalar_runtime_ints_lower_to_symbol_value_type`、`expectation/dsl/mlir_gen/add_scalar.py`）
