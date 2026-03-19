# emit_mlir.md

用于定义 `python/dsl/ast_visitor.py::emit_mlir` 的文本输出入口规范。该接口处于 DSL 链路的最外层，只负责接收可打印对象并输出 MLIR 风格文本，不重复定义 AST 构建、IR 生成或 `nn dialect` 本身的语义。

## 功能简介

- 定义 `emit_mlir(value, globals=None, builtins=None, config=None)` 的公开契约。
- 明确 `emit_mlir` 在 DSL 分层中的职责：复用上游 AST/IR 生成链路，并将结果交给 `xdsl.printer.Printer` 输出文本。
- 约束输入类型、返回值、错误传播与测试映射。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `关联 Visitor`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `关联 MLIR 生成`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)

## 依赖

- 依赖 `python/dsl/ast_visitor.py::visit_to_nn_ir` 在可调用输入路径上先生成结构化 IR。
- 依赖 `xdsl.printer.Printer` 输出 MLIR 风格文本。
- 依赖 `spec/dsl/ast_visitor.md` 约束受限 Python 函数入口与诊断包装行为。
- 依赖 `spec/dsl/mlir_gen.md` 约束结构化 IR 的生成链路与 `func.func` / SSA 组织方式。
- 依赖 `spec/dialect/nn.md` 约束当前 `nn dialect` 的 op/type 文本语义与 verifier 边界。

## 目标

- 为 DSL 对外提供统一的 MLIR 文本输出入口。
- 明确“可调用对象 -> AST/IR 生成 -> 文本输出”和“已有 module -> 直接打印”两条路径。
- 统一 `emit_mlir` 与 `mlir_gen` 的分层口径：前者负责文本序列化入口，后者负责结构化 IR 生成约束。

## 限制与边界

- 本文件不定义受限 Python 语法子集；相关规则由 [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md) 约束。
- 本文件不定义表达式到 `nn.*` op 的 lowering 细节；相关结构化 IR 生成链路由 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 约束。
- 本文件不定义 `nn dialect` 的 verifier、parse/print 或类型系统细节；相关规则由 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 约束。
- `emit_mlir` 不做 canonicalization、优化、补全缺失属性或自动修复非法 IR。
- 文本格式以 `xdsl.printer.Printer` 当前输出为准；本文件只约束必须保留的结构语义，不约束空格、换行或 SSA 编号细节。

## 公开接口

### `emit_mlir(value, globals=None, builtins=None, config=None)`

功能说明：

- 对外输出 MLIR 风格文本。
- 当 `value` 为可调用对象时，必须先走 `visit_to_nn_ir(...)` 生成结构化 IR，再打印文本。
- 当 `value` 已是可打印的 IR/module 对象时，必须直接打印，不再重复解析 Python 函数或重做 lowering。

输入约束：

- `value` 支持两类输入：
  - 受 [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md) 支持范围约束的 Python 函数。
  - 已由上游链路生成、可被 `Printer.print_op(...)` 直接打印的 IR/module 对象。
- `globals`、`builtins`、`config` 仅在 `value` 为可调用对象时参与 `visit_to_nn_ir(...)`。
- 若 `value` 不是可调用对象，`emit_mlir` 不得尝试解释 `globals`、`builtins`、`config` 的语义。

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

处理流程：

1. 若 `value` 为可调用对象，调用 `visit_to_nn_ir(value, globals=..., builtins=..., config=...)`。
2. 将得到的 module/op 传给 `Printer.print_op(...)`。
3. 返回打印得到的字符串。

返回约束：

- 返回值必须为 `str`。
- 返回文本必须反映当前结构化 IR 的 `func.func`、`func.return` 与已生成的 `nn.*` op/type 信息。
- 对同一个结构化 IR，`emit_mlir` 不要求固定 SSA 名称或固定换行格式，但必须保持语义等价的结构化文本。

错误规则：

- 若 `value` 为可调用对象，则 `emit_mlir` 必须沿用 `visit_to_nn_ir(...)` 的错误传播规则：
  - 源码不可获取时，传播 `OSError` / `TypeError`。
  - AST 构建或上游 lowering 失败时，传播带诊断的 `AstVisitorError`。
- 若 `value` 不是可调用对象但也不是 `Printer.print_op(...)` 可接受的对象，`emit_mlir` 不做包装，直接暴露底层类型错误或打印错误。
- 若输入 IR 自身不满足上游语义约束，`emit_mlir` 不负责修复；错误由上游 verifier、构造链路或 printer 暴露。

## 分层关系

- `ast_visitor`
  - 负责受限 Python 函数的 AST 构建、诊断包装与 `visit_to_nn_ir(...)` 入口。
- `mlir_gen`
  - 负责结构化 IR 的组织规则，包括 `func.func`、SSA 顺序与表达式对应 op/value 的生成约束。
- `emit_mlir`
  - 只负责把“可调用对象或已构造 IR”转换为最终文本，不新增新的语义判断。
- `nn dialect`
  - 负责当前目标 op/type/attribute 的语义、文本表示和 verifier 约束。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试目标

- 覆盖 `emit_mlir(callable)` 的文本输出入口。
- 确认输出文本包含 `func.func` 与当前表达式对应的 `nn.*` op 文本。
- 与 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 保持分层一致：结构化 IR 的生成正确性由上游链路负责，本文件只认领文本输出入口的直接覆盖。

### 测试映射

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| EMIT-001 | `emit_mlir(callable)` 输出必须包含 `func.func` 与当前表达式对应的 `nn.*` op 文本 | `test_emit_mlir_output` |

### 当前测试缺口

- `emit_mlir(module)` 直入打印路径当前没有独立回归测试；若后续继续维护该公开输入路径，应补一条“先调用 `visit_to_nn_ir` 得到 module，再调用 `emit_mlir(module)`”的独立用例。
- `emit_mlir(callable)` 的错误传播当前主要由 `visit_to_nn_ir(...)` 的共享测试间接约束，尚无直接针对 `emit_mlir(...)` 的异常传播用例。
