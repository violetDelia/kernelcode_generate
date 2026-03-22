# emit_mlir.md

## 功能简介

- 定义 AST 节点到 MLIR op/value 的转换规则。
- 为 `ast_visitor` 提供可调用的节点发射接口。
- 不负责 AST 解析与遍历，不负责 MLIR 文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `功能实现`：[`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- AST 节点定义：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)

## 术语

- `EmitContext`：发射上下文，包含 builder、类型映射与符号表。
- `MLIR Value`：MLIR SSA value 的抽象表示。

## 目标

- 将 AST 表达式节点转换为 MLIR value。
- 将 AST 语句节点转换为 MLIR op 或控制流结构。
- 保证同一节点生成的 value 可被上游复用。

## 限制与边界

- 不解析 Python 函数，不遍历 AST。
- 不做优化、常量折叠或后端特化。
- 不生成 MLIR 文本；文本输出由上游调用方负责。
- 当 `ForAST` 来自 `LoopRange(start, end, step)` 且边界与循环变量保持 symbol 整数语义时，必须 lowering 为 `symbol.for`，不得回退为 `scf.for`；其循环块参数 `it` 必须为 `!symbol.int<"expr">`。
- 在上述 `LoopRange` 场景中，循环变量以及传入 `dma.slice` / `dma.deslice` 的 `offsets`、`sizes`、`strides` 等 DMA 标量 operand 必须直接复用 `!symbol.int<"expr">` value，不得插入 `arith.index_cast`；若循环变量 `it` 退化为 `index`、普通整数或浮点类型，应视为 lowering 违规。

## 公开接口

### `EmitContext(builder, symbols, types, config=None)`

功能说明：

- 封装发射所需的构建器、符号表与类型映射。

参数说明：

- `builder` (`object`)：MLIR 构建器或等价接口。
- `symbols` (`dict`)：变量名到 MLIR value 的映射。
- `types` (`object`)：类型映射或类型系统入口。
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
- `LoopRange` 触发的 `ForAST` 必须走 `symbol.for` 分支，并保持 symbol 整数值直接作为 DMA operand 传递。

节点映射示例：

- `ConstAST`：生成常量或等价字面量 op/value。
- `BinaryExprAST(add/sub/mul/div)`：生成对应的二元算术 op。
- `CompareExprAST(eq/ne/lt/le/gt/ge)`：生成对应的比较 op。
- `LoadAST`：生成张量读取相关 op/value；当携带 `sizes` 时发射 `dma.slice`。
- `StoreAST`：生成张量写入相关 op；当携带 `sizes` 时发射 `dma.deslice`。
- `ForAST`：当来源于 `LoopRange(start, end, step)` 且边界为 symbol 整数时，生成 `symbol.for`；循环体内若包含 `dma.slice` / `dma.deslice`，其 DMA 标量 operand 直接使用 `!symbol.int<"expr">` value，不生成 `arith.index_cast`。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 覆盖常见表达式与语句节点的发射结果。
  - 覆盖 `LoopRange` -> `symbol.for` 与 `it`/DMA operand 直接保持 `symbol.int` 的发射规则。
  - 覆盖不支持节点的错误路径。
- 功能与用例清单：
  - EMIT-001：二元表达式节点生成对应 op/value。（`test_emit_context_reuses_cached_value`）
  - EMIT-002：比较表达式节点生成对应 op/value。（`test_emit_mlir_compare_expr_emits_eq`）
  - EMIT-003：不支持节点抛出错误并携带位置信息。（`test_emit_mlir_unsupported_node_reports_location`）
  - EMIT-004：`TensorAST` 可通过符号表直接解析。（`test_emit_mlir_tensor_uses_symbol_table`）
  - EMIT-005：`LoadAST` 生成 `dma.load`。（`test_load_ast_lowering_rejected`）
  - EMIT-006：`StoreAST` 生成 `dma.store`。（`test_store_ast_lowering_rejected`）
  - EMIT-007：非 unit stride 抛出可定位错误。（`test_load_ast_lowering_raises_lowering_error`）
  - EMIT-008：索引 rank mismatch 抛出可定位错误。（`test_load_ast_index_rank_mismatch_reports_location`）
  - EMIT-009：`StoreAST` 输入非 memory 抛出错误。（`test_store_ast_lowering_raises_lowering_error`）
  - EMIT-010：`ForAST` 在 `LoopRange` 场景下 lowering 为 `symbol.for`，循环块参数 `it` 与循环体内相关 DMA operand 直接复用 `!symbol.int<"...">`，不生成 `arith.index_cast`。（`test_emit_mlir_symbolic_for_loop_avoids_index_cast`）
  - EMIT-011：循环变量表初始化与非法配置报错路径。（`test_emit_mlir_loop_vars_validation`）
  - EMIT-012：索引解析与 rank mismatch 的错误路径。（`test_emit_mlir_index_expr_rejections`）
  - EMIT-013：默认 stride 推导遇到未知 attr 的分支。（`test_emit_mlir_default_stride_handles_unknown_attr`）
  - EMIT-014：`ForAST` lowering 会保留循环结构并在循环体内生成 `dma.load`。（`test_for_ast_lowering_emits_loads`）
