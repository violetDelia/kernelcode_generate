# mlir_gen.md

## 功能简介

- 定义 DSL 到结构化 MLIR IR 的生成约束。
- 约束 `FunctionAST -> builtin.module -> func.func -> nn.*` 的结构、顺序与结果类型。
- 文本输出入口由 `spec/dsl/emit_mlir.md` 单独约束，本文件不重复定义。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- [`spec/dsl/ast.md`](../../spec/dsl/ast.md)：提供 AST 数据结构。
- [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)：定义 `visit_to_nn_ir(...)` 的入口与诊断规则。
- [`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)：结构化 IR 生成的实现入口。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：目标方言的 op/type/attribute 语义与 verifier 规则。
- [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)：下游文本输出入口；本文件提供其结构化 IR 基线。

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
- 当前项目没有单独暴露名为 `mlir_gen(...)` 的公共 Python API；结构化 IR 生成入口为 `visit_to_nn_ir(...)`。

### 结构化 IR 生成约束

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

### 错误规则

- AST 生成失败：由上游 `ast_visitor` 抛出 `AstVisitorError`。
- Lowering 或结构化 IR 生成失败：`visit_to_nn_ir(...)` 必须抛出带定位信息的 `AstVisitorError`。
- 本层不得 silently 跳过无法生成 IR 的节点；任何生成失败都必须通过上游入口暴露错误。

## 公开接口

### `visit_to_nn_ir(callable, globals=None, builtins=None, config=None)`

功能说明：

- 接收 DSL 可调用对象并生成结构化 IR（`builtin.module`）。
- 该接口的入口与诊断规则由 `spec/dsl/ast_visitor.md` 定义，本文件只约束输出结构。

参数说明：

- `callable`
  - 输入类型：受 `spec/dsl/ast_visitor.md` 约束的 Python 可调用对象。
  - 含义：作为 DSL 入口进行 AST 构建与结构化 IR 生成。
- `globals`
  - 输入类型：`dict | None`。
  - 含义：传递给 `ast_visitor` 的全局符号表。
- `builtins`
  - 输入类型：`dict | None`。
  - 含义：传递给 `ast_visitor` 的内建符号表。
- `config`
  - 输入类型：`dict | None`。
  - 含义：传递给 `ast_visitor` 的行为配置。

使用示例：

```python
module = visit_to_nn_ir(add)
```

扩展示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

A = Memory(["N", 32], NumericType.Float32, stride=["C", 1])
B = Memory(["N", 32], NumericType.Float32, stride=["C", 1])

def func_B(A, B):
    C = A + B
    return C

module = visit_to_nn_ir(func_B)
```

示例对应的结构化文本语义：

```mlir
builtin.module {
  func.func @func_B(%arg0: !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>, %arg1: !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>> {
    %0 = "nn.add"(%arg0, %arg1) {space = #nn.space<global>} : (!nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>, !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>
  }
}
```

注意事项：

- 结构化 IR 的语义约束以本文件与 `spec/dialect/nn.md` 为准。
- 文本输出由 `spec/dsl/emit_mlir.md` 约束，本文件不定义文本格式细节。
- 示例强调“函数 -> `func.func` -> op / value”的结构与约束，不要求文本细节必须和当前 printer 的空格、换行完全一致。
- 示例中使用 `nn.add` 只是因为这是当前已有实现，不表示 `mlir_gen` 只能输出 `nn` dialect。
- 具体文本细节以当前 printer 输出为准，但结构必须满足本 spec。

返回与限制：

- 返回 `builtin.module` 对象。
- module 必须包含与输入函数同名的 `func.func`，并满足本文件的结构化 IR 约束。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试目标

- 验证 `visit_to_nn_ir(...)` 能生成包含 `func.func` 与目标 `nn.*` op 的 `builtin.module`。
- 验证标量参数会进入 `func.func` 签名并降低为基础标量类型。
- 验证多语句 lowering 保持源码依赖顺序，并对重复表达式复用 SSA value。

### 功能与用例清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| MGEN-001 | `visit_to_nn_ir(...)` 必须生成包含 `func.func` 与当前表达式对应 `nn.*` op 的 `builtin.module` | `test_visit_to_nn_ir_builds_module` |
| MGEN-002 | 标量参数必须进入 `func.func` 签名并 lowering 为 `i32` | `test_scalar_arg_lowering_in_signature` |
| MGEN-003 | 多语句 lowering 必须保持 SSA 顺序并复用已生成 value | `test_multi_statement_ssa_order_and_reuse` |
