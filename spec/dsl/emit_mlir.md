# emit_mlir.md

## 功能简介

- 定义 AST 节点到 MLIR op/value 的转换规则。
- 为 `ast_visitor` 提供可调用的节点发射接口。
- 不负责 AST 解析与遍历，不负责 MLIR 文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `功能实现`：[`kernel_gen/dsl/lowering.py`](../../kernel_gen/dsl/lowering.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- AST 节点定义：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)

## 术语

- `EmitContext`：发射上下文，包含 builder、类型映射、符号表与诊断容器。
- `MLIR Value`：MLIR SSA value 的抽象表示。

## 目标

- 将 AST 表达式节点转换为 MLIR value。
- 将 AST 语句节点转换为 MLIR op 或控制流结构。
- 保证同一节点生成的 value 可被上游复用。

## 限制与边界

- 不解析 Python 函数，不遍历 AST。
- 不做优化、常量折叠或后端特化。
- 不生成 MLIR 文本；文本输出由上游调用方负责。

## 公开接口

### `EmitContext(builder, symbols, types, diagnostics=None, config=None)`

功能说明：

- 封装发射所需的构建器、符号表与类型映射。

参数说明：

- `builder` (`object`)：MLIR 构建器或等价接口。
- `symbols` (`dict`)：变量名到 MLIR value 的映射。
- `types` (`object`)：类型映射或类型系统入口。
- `diagnostics` (`list|None`)：诊断容器（可选）。
- `config` (`dict|None`)：可选配置。

使用示例：

```python
ctx = EmitContext(builder=builder, symbols={}, types=types, config={"keep_location": True})
```

注意事项：

- `symbols` 必须在遍历过程中保持一致性。

返回与限制：

- 返回上下文实例，用于发射函数调用。

### `emit_mlir(node, ctx)`

功能说明：

- 将单个 AST 节点转换为 MLIR op/value。
- 该函数按节点类型分发到对应的发射规则。

参数说明：

- `node` (`object`)：AST 节点。
- `ctx` (`EmitContext`)：发射上下文。

使用示例：

```python
value = emit_mlir(expr_ast, ctx)
```

注意事项：

- 表达式节点应返回 MLIR value。
- 语句节点可返回 `None` 或返回生成的 op（以实现为准）。
- 不支持的节点必须抛出可定位的错误。

返回与限制：

- 表达式节点返回 MLIR value。
- 语句节点返回 `None` 或 op 对象（以实现为准）。

## 额外补充

- `emit_mlir` 必须覆盖 AST 中每一种节点类型。
- 默认使用当前项目的目标 dialect（例如 `nn`），但节点到 op 的映射必须清晰可追踪。

节点映射示例：

- `ConstAST`：生成常量或等价字面量 op/value。
- `BinaryExprAST(add/sub/mul/div)`：生成对应的二元算术 op。
- `CompareExprAST(eq/ne/lt/le/gt/ge)`：生成对应的比较 op。
- `LoadAST`：生成张量读取相关 op/value。
- `StoreAST`：生成张量写入相关 op。
- `ForAST`：生成循环控制流结构。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 覆盖常见表达式与语句节点的发射结果。
  - 覆盖不支持节点的错误路径。
- 功能与用例清单：
  - EMIT-001：二元表达式节点生成对应 op/value。
  - EMIT-002：比较表达式节点生成对应 op/value。
  - EMIT-003：不支持节点抛出错误并携带位置信息。
