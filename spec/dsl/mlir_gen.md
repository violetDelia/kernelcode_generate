# mlir_gen.md

## 功能简介

- 定义 DSL 到结构化 MLIR IR 的生成约束。
- 约束 `FunctionAST -> builtin.module -> func.func -> nn.*` 这条链路的结构、顺序与结果类型。
- 不定义 `emit_mlir` 文本输出接口；文本输出入口由 `spec/dsl/emit_mlir.md` 单独约束。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `关联 AST`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `关联 ast_visitor`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `关联文本输出`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)
- [immutable]`功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/mlir_gen.py)

## 依赖

- AST 数据结构：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 入口与诊断：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- 目标方言：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- 文本序列化入口见 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)，但该文件是本层的下游消费者，不反向定义本层规则。

## 目标

- 提供稳定的结构化 IR 生成约束。
- 明确 `visit_to_nn_ir(...)` 产物必须满足的 module、`func.func`、block argument、SSA 与 `func.return` 规则。
- 为下游 `emit_mlir` 文本输出提供唯一的结构化 IR 基线。

## 限制与边界

- 不负责 Python AST 解析与 AST 构建，入口规则由 `ast_visitor` 约束。
- 不重复定义 AST 前端注解解析、名称绑定和诊断细节；相关规则由 `ast_visitor` 约束。
- 不定义 `emit_mlir` 的输入输出、参数和文本错误传播；相关规则由 `spec/dsl/emit_mlir.md` 约束。
- 不做优化、融合、bufferization 或后端生成。
- 不替代 `nn dialect` 的 verifier 规则；不自动修正非法 IR。

## 入口归属

- 当前项目没有单独暴露名为 `mlir_gen(...)` 的公共 Python API。
- 结构化 IR 的外部入口是 [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md) 中定义的 `visit_to_nn_ir(...)`。
- `emit_mlir(...)` 的接口定义、参数语义和文本输出规则只在 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 中维护，本文件不再重复定义。

使用示例：

```python
module = visit_to_nn_ir(add)
```

## 结构化 IR 生成约束

### module 与 `func.func`

- `visit_to_nn_ir(...)` 产物必须为 `builtin.module`。
- module 中必须包含与输入函数同名的 `func.func`。
- `func.func` 的参数顺序必须与 Python 函数签名顺序一致。
- `func.func` 的返回类型必须与上游 AST/lowering 推断结果一致。

### block argument 与结果类型

- 张量参数必须 lowering 为 `!nn.memory<...>`。
- 标量参数必须 lowering 为对应的基础标量类型；当前 `int` 参数为 `i32`。
- 返回值若为张量，必须保持 `!nn.memory<...>` 类型；若为标量，则保持对应标量类型。

### SSA 与语句顺序

- 表达式对应的 `nn.*` op 必须按源码依赖顺序出现在函数体中。
- 同一表达式对象被多次引用时，必须复用已生成的 SSA value，而不是重新生成等价 op。
- `func.return` 必须消费当前返回表达式对应的 SSA value，且作为函数体终结语句。

### 文本输出关系

- 本层只负责保证结构化 IR 满足上述约束。
- 结构化 IR 进入 `Printer.print_op(...)` 后的文本输出行为，由 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 约束。

## [immutable]示例

DSL 输入示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

A = Memory(["N", 32], NumericType.Float32, stride=["C", 1])
B = Memory(["N", 32], NumericType.Float32, stride=["C", 1])

def func_B(A, B):
    C = A + B
    return C
```

期望的结构化文本语义示例：

```mlir
builtin.module {
  func.func @func_B(%arg0: !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>, %arg1: !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>> {
    %0 = "nn.add"(%arg0, %arg1) {space = #nn.space<global>} : (!nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>, !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>
  }
}
```

说明：

- 这里强调的是“函数 -> `func.func` -> op / value”的结构与约束，不要求文本细节必须和当前 printer 的空格、换行完全一致。
- 示例中使用 `nn.add` 只是因为这是当前已有实现，不表示 `mlir_gen` 只能输出 `nn` dialect。
- 具体文本细节以当前 printer 输出为准，但结构必须满足本 spec。

## 错误规则

- AST 生成失败：由上游 `ast_visitor` 抛出 `AstVisitorError`。
- Lowering 或结构化 IR 生成失败：`visit_to_nn_ir(...)` 必须抛出带定位信息的 `AstVisitorError`。
- 本层不定义“输入不是可打印 module”的错误，因为那属于 `emit_mlir(...)` 的文本输出职责。
- 本层不得 silently 跳过无法生成 IR 的节点；任何生成失败都必须通过上游入口暴露错误。

## 测试

- 主要测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试目标

- 验证 `visit_to_nn_ir(...)` 能生成包含 `func.func` 与目标 `nn.*` op 的 `builtin.module`。
- 验证标量参数会进入 `func.func` 签名并降低为基础标量类型。
- 验证多语句 lowering 保持源码依赖顺序，并对重复表达式复用 SSA value。

### 测试映射

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| MGEN-001 | `visit_to_nn_ir(...)` 必须生成包含 `func.func` 与当前表达式对应 `nn.*` op 的 `builtin.module` | `test_visit_to_nn_ir_builds_module` |
| MGEN-002 | 标量参数必须进入 `func.func` 签名并 lowering 为 `i32` | `test_scalar_arg_lowering_in_signature` |
| MGEN-003 | 多语句 lowering 必须保持 SSA 顺序并复用已生成 value | `test_multi_statement_ssa_order_and_reuse` |

### 测试归属边界

- `test_emit_mlir_output`
  - 归 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)，用于验证文本输出，不再复用到本文件编号。
- `test_globals_and_builtins_annotation_entry` 与 `test_unknown_name_reports_diagnostics`
  - 归 [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)，用于验证 AST 前端入口与诊断。
- `test_constant_lowering_reports_diagnostics`、`test_return_type_mismatch_reports_diagnostics`、`test_tensor_binary_implicit_broadcast_lowering`
  - 归 lowering 相关 spec，用于验证 lowering 规则本身，而不是本文件的结构化 IR 基线编号。

## 测试标准

- `pytest -q test/dsl/test_ast_visitor.py` 返回码必须为 `0`。
- 生成的 module 必须至少稳定包含 `func.func`、`func.return` 和与源码表达式对应的目标 op。
- 新增会影响 module 结构、参数签名或 SSA 生成顺序的能力时，必须同步更新本文件测试清单。

## 兼容性

- 本 spec 绑定当前项目的结构化 IR 生成层，而不是文本输出入口。
- 若未来把结构化 IR 生成逻辑迁移到独立模块，例如 `python/dsl/mlir_gen.py`，需保持本文件定义的 module / `func.func` / SSA 约束不变。
- 若 `nn.memory` 的结构或 verifier 规则发生变化，需同步更新 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 与本文件中的结构约束。
- 若后续引入新的目标 dialect，本文件应补充“AST/表达式 -> 结构化 op/value”的生成规则；文本输出接口仍应由 `emit_mlir.md` 单独维护。
