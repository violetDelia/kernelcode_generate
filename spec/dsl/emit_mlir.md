# emit_mlir.md

## 功能简介

用于定义 `python/dsl/ast_visitor.py::emit_mlir` 的文本输出入口规范。该接口位于 DSL 链路最外层，负责把上游已生成的结构化 IR 序列化为 MLIR 风格文本，不重复定义 AST 构建、结构化 IR 生成或 `nn dialect` 本身的语义。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- `python/dsl/ast_visitor.py::visit_to_nn_ir` 在可调用输入路径上生成结构化 IR。
- `xdsl.printer.Printer` 负责 MLIR 风格文本输出。
- [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md) 约束受限 Python 函数入口、源码解析与诊断包装行为。
- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 约束结构化 IR 的生成链路、`func.func` 组织方式与 SSA/value 语义。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 约束当前目标 dialect 的 op/type/attribute 文本语义与 verifier 边界。

## 目标

- 为 DSL 对外提供统一的 MLIR 文本输出入口。
- 明确“可调用对象 -> 结构化 IR -> 文本输出”和“已有 module/op -> 直接打印”两条路径。
- 与 `mlir_gen` 保持一致分层：`mlir_gen` 负责结构化 IR 生成约束，`emit_mlir` 负责文本序列化。

## 限制与边界

- 不定义受限 Python 语法子集；相关规则由 [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md) 约束。
- 不定义表达式到 `nn.*` op 的 lowering 或结构化 IR 生成细节；相关规则由 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 约束。
- 不定义 `nn dialect` 的 verifier、parse/print 或类型系统细节；相关规则由 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 约束。
- 不做 canonicalization、优化、自动补全缺失属性或修复非法 IR。
- 文本格式以 `xdsl.printer.Printer` 当前输出为准；本文件只约束必须保留的结构语义，不约束空格、换行或 SSA 编号细节。

## 公开接口

### `emit_mlir(value, globals=None, builtins=None, config=None)`

功能说明：

- 对外输出 MLIR 风格文本。
- 当 `value` 为可调用对象时，必须先走 `visit_to_nn_ir(...)` 生成结构化 IR，再打印文本。
- 当 `value` 已是可打印的 IR/module 对象时，必须直接打印，不再重新解析 Python 函数或重做结构化 IR 生成。

参数说明：

- `value`
  - 受 [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md) 支持范围约束的 Python 函数，或已由上游链路生成、可被 `Printer.print_op(...)` 直接打印的 IR/module 对象。
- `globals`/`builtins`/`config`
  - 仅在 `value` 为可调用对象时参与 `visit_to_nn_ir(...)`。
  - 若 `value` 不是可调用对象，不解释其语义。

使用示例：

```python
def add(
    x: "Tensor[f32, 2, 2]",
    y: "Tensor[f32, 2, 2]",
) -> "Tensor[f32, 2, 2]":
    return x + y

text = emit_mlir(add)
```

```python
module = visit_to_nn_ir(add)
text = emit_mlir(module)
```

注意事项：

- 若 `value` 为可调用对象，则错误传播必须沿用 `visit_to_nn_ir(...)` 的规则，包括源码不可获取的 `OSError`/`TypeError` 与 AST/lowering 失败时的 `AstVisitorError`。
- 若 `value` 不是可调用对象但也不是 `Printer.print_op(...)` 可接受的对象，则直接暴露底层类型错误或打印错误，不做包装。
- 输入 IR 自身不满足上游语义约束时不负责修复，错误由上游 verifier、构造链路或 printer 暴露。

返回与限制：

- 返回值必须为 `str`。
- 返回文本必须反映当前结构化 IR 中的 `func.func`、`func.return` 与已生成的 `nn.*` op/type 信息。
- 对同一个结构化 IR，不要求固定 SSA 名称或固定换行格式，但必须保持语义等价的结构化文本。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 覆盖 `emit_mlir(callable)` 的文本输出入口。
  - 确认输出文本包含 `func.func` 与当前表达式对应的 `nn.*` op 文本。
  - 与 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 保持一致分层：结构化 IR 的生成正确性由上游链路负责，本文件只认领文本输出入口的直接覆盖。
- 功能与用例清单：

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| EMIT-001 | `emit_mlir(callable)` 输出必须包含 `func.func` 与当前表达式对应的 `nn.*` op 文本 | `test_emit_mlir_output` |
