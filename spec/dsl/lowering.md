# lowering.md

用于定义 `python/dsl/lowering.py` 的 lowering 规则规范，描述从 DSL AST 到 `nn dialect` IR 的行为边界。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- `关联 AST`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现`：[`python/dsl/lowering.py`](../../python/dsl/lowering.py)

## 范围与目标

- 描述 AST lowering 到 `nn dialect` IR 的规则与约束。
- 描述高层逐元素隐式 broadcast 在 lowering 阶段如何展开为显式 `nn.broadcast`。
- 不定义 AST 的解析；AST 结构见 `spec/dsl/ast.md`。
- 不覆盖 MLIR 文本输出（见 `spec/dsl/mlir_gen.md`）。

## 入口

### `lower_to_nn_ir(function_ast)`

功能说明：

- 将 `FunctionAST` 转换为 `xdsl.dialects.builtin.ModuleOp`。
- 函数体生成 `func.func`，并在函数体中生成 `nn.*` op。
- 当高层逐元素表达式依赖隐式 broadcast 时，lowering 必须先生成显式 `nn.broadcast`，再生成对应 `nn.*` 二元 op。

使用示例：

```python
module = lower_to_nn_ir(func_ast)
```

返回约束：

- Module 中只包含单个 `func.func`。
- 返回值类型由 AST 表达式推断与返回注解校验决定。

## AST 支持范围

- 允许的表达式节点：
  - `BinaryExprAST`
  - `CompareExprAST`
  - `TensorAST`
  - `ScalarArgAST`
  - `ConstAST` 仅用于校验占位（当前不支持 lowering）
- `LoadAST`/`StoreAST` 在当前阶段禁止 lowering：不得生成 IR，遇到即报错。
- 函数体不能为空。
- 语句顺序保留，`return` 对应的表达式必须位于最后一条语句。

## 类型与内存映射

### 数值类型

- `NumericType.Float32` -> `f32`
- `NumericType.Int32` -> `i32`
- 其他类型必须抛 `LoweringError`。

### 内存类型

- `Memory.shape` 生成 `ArrayAttr`。
- `Memory.stride` 若为空则使用默认连续 stride；遇到动态维度以 `"?"` 填充。
- `Memory.space` 映射规则：
  - `GM` -> `global`
  - `SM` -> `shared`
  - `LM` -> `local`
  - `TSM` -> `shared`
  - `TLM` -> `local`

### 比较表达式返回类型

- `CompareExprAST` 返回 `nn.memory<i1>`，shape/stride/space 与操作数一致。

## 约束与错误

- 函数必须至少包含一个输入参数，否则抛 `LoweringError("Function has no inputs")`。
- 至少包含一个张量输入，否则抛 `LoweringError("At least one tensor input is required")`。
- 标量参数仅支持 `int`，其他类型抛错。
- 函数体表达式若包含 `ConstAST`，必须抛 `LoweringError("Constant expressions are not supported")`。
- 二元算术：
  - 仅支持 `add/sub/mul/div`。
  - 操作数必须同为 `nn.memory` 且类型一致。
  - 若两个张量操作数 `shape` 完全一致，则直接 lowering 为对应 `nn.add/sub/mul/truediv`。
  - 若两个张量操作数 `shape` 不完全一致，但满足 [`spec/operation/nn.md`](../../spec/operation/nn.md) 中逐元素隐式 broadcast 规则，则必须先把一侧或两侧显式 lowering 为 `nn.broadcast`，再生成原始二元 op。
- 比较表达式：
  - 仅支持 `eq/ne/lt/le/gt/ge`。
  - 操作数必须同为 `nn.memory` 且类型一致。
  - 若两个张量操作数需要隐式 broadcast，则也必须先显式生成 `nn.broadcast`，再 lowering 为 `nn.eq/ne/lt/le/gt/ge`。
- 未知输入引用、未知表达式类型必须抛 `LoweringError`。
- 遇到 `LoadAST`/`StoreAST` 必须抛 `LoweringError`，且不得生成任何 IR。
- 若逐元素表达式无法按 [`spec/operation/nn.md`](../../spec/operation/nn.md) 推导共同 broadcast 目标 `shape`，必须抛 `LoweringError`，不得依赖 `nn dialect` 去做隐式 broadcast。

## 返回类型约束

- 仅支持单一返回值。
- 若存在返回注解：
  - 注解为 `Tensor`：需与推断出的 `nn.memory` 完全一致。
  - 注解为 `int`：需与推断出的 `i32` 一致。
- 若无返回注解，使用表达式推断结果作为函数返回类型。

## 多语句 SSA 行为

- lowering 按语句顺序生成 SSA。
- 使用表达式对象的 `id` 作为缓存键复用 SSA value。
- 对同一表达式的多次引用必须复用已生成的 SSA value。
- 对于 `a = x + y; b = a * y; return b + a` 这类多语句函数，lowering 生成的 op 顺序必须与源码依赖顺序一致：先生成 `a` 对应 op，再生成 `b` 对应 op，最后生成返回表达式对应 op；其中 `a` 的重复引用必须直接复用首次生成的 SSA value。

## 隐式 `broadcast` lowering 规则

- 本节只约束“高层逐元素隐式 broadcast”进入 `nn dialect` 的展开方式；不改变 [`spec/operation/nn.md`](../../spec/operation/nn.md) 中的高层兼容性判断。
- 若逐元素表达式的两个张量操作数 `shape` 完全一致，lowering 可直接生成对应 `nn.*` 二元 op。
- 若逐元素表达式的两个张量操作数 `shape` 不完全一致，但满足高层隐式 broadcast 规则，lowering 必须：
  - 先推导共同目标 `shape`；
  - 为需要扩张的一侧或两侧生成 `nn.broadcast`；
  - 再以 broadcast 后的结果生成原始 `nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge`。
- lowering 不得把“shape 广播兼容但不完全相等”的两个 operand 直接送入 `nn.add/eq/...`，因为 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 明确禁止二元 op 隐式 broadcast。
- 若需要隐式 broadcast 的表达式无法推导共同目标 `shape`，必须抛 `LoweringError` 并保留源位置信息。

示例（目标 lowering 形态，当前 `main` 尚未实现）：

```python
def add_bias(x: "Tensor[f32, M, N]", b: "Tensor[f32, 1, N]") -> "Tensor[f32, M, N]":
    return x + b
```

目标 IR 语义：

```text
%b1 = "nn.broadcast"(%b) ... -> !nn.memory<[M, N], ...>
%r = "nn.add"(%x, %b1) ...
```

## 错误包装

- `LoweringError` 应携带 `SourceLocation`；上层 `ast_visitor` 需将其转换为 `AstVisitorError` 诊断。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试映射

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| AV-003B | 标量参数 lowering 至 `func.func` 签名 | `test_scalar_arg_lowering_in_signature` |
| AV-003D | lowering 失败转为带定位诊断的 `AstVisitorError` | `test_lowering_failure_reports_diagnostics` |
| AV-003G | `ConstAST` 进入 lowering 必须失败并保留诊断位置 | `test_constant_lowering_reports_diagnostics` |
| AV-003I | 返回注解与推断类型不一致时 lowering 必须失败并保留诊断位置 | `test_return_type_mismatch_reports_diagnostics` |
| AV-003K | 多语句 SSA 顺序与 value 复用 | `test_multi_statement_ssa_order_and_reuse` |
| AV-003L | `LoadAST` 进入 lowering 必须抛 `LoweringError`，且不得生成任何 IR | `test_load_ast_lowering_rejected`; `test_load_ast_lowering_raises_lowering_error` |
| AV-003M | `StoreAST` 进入 lowering 必须抛 `LoweringError`，且不得生成任何 IR | `test_store_ast_lowering_rejected`; `test_store_ast_lowering_raises_lowering_error` |
| AV-003N | 双张量逐元素 singleton dim 隐式 broadcast 必须 lowering 为 `nn.broadcast + nn.add` | `test_tensor_binary_implicit_broadcast_lowering` |
| AV-003O | 前置维隐式 broadcast 必须 lowering 为 `nn.broadcast + nn.add` | `test_tensor_binary_prepend_broadcast_lowering` |
| AV-003P | 比较表达式隐式 broadcast 必须 lowering 为 `nn.broadcast + nn.eq` | `test_compare_implicit_broadcast_lowering` |
| AV-003Q | 不可广播的逐元素表达式必须抛 `LoweringError` 并保留位置 | `test_tensor_binary_implicit_broadcast_mismatch_reports_diagnostics` |

### Load/Store 用例分层

- `test_*_lowering_rejected` 与 `test_*_lowering_raises_lowering_error` 当前都覆盖 `LoadAST`/`StoreAST` 进入 `lower_to_nn_ir` 后由 lowering 层抛出 `LoweringError` 的拒绝路径。
- 两组用例的区别主要体现在命名侧重点：前者强调节点被拒绝，后者强调入口调用最终以 `LoweringError` 失败。
- 两组用例当前存在重复；若后续要精简测试，可各自合并为一条 `LoadAST` 用例和一条 `StoreAST` 用例，但需继续保留对应异常类型与入口行为的回归覆盖。
