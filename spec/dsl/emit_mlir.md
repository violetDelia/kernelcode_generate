# emit_mlir.md

## 功能简介

- 定义 AST 节点到 MLIR op/value 的转换规则。
- 为 `ast_visitor` 提供可调用的节点发射接口。
- 不负责 AST 解析与遍历，不负责 MLIR 文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`李白`
- `spec`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `功能实现`：[`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- AST 节点定义：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- arch 查询结果类型：[`spec/dialect/arch.md`](../../spec/dialect/arch.md)

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
- 当 DSL AST 表达 `alloc`、`copy`、`cast`、`view`、`reshape`、`flatten`、`load`、`store`、`slice`、`deslice` 这组 DMA helper 调用时，`emit_mlir` 必须按对应 memory 语义 lowering；其中 `flatten` 公开上视为一维 `reshape` 语义，不要求生成独立 dialect op。
- 当 `CompareExprAST(op="ne")` 来自 `lhs != rhs` 入口且两侧为 `nn.memory` 时，必须 lowering 为 `nn.ne`；允许按隐式 broadcast 规则插入 `nn.broadcast`，若无法广播必须报错 `Implicit broadcast dimension mismatch`，若 element type 不一致必须报错 `Binary op operands must have the same element_type`。
- `free` 必须作为语句型 helper 处理，不产生新的 SSA 结果，也不承诺生成独立的 `dma.free` op。
- `ArchQueryAST(query_name="get_block_id")` 必须 lowering 为单个 `arch.get_block_id`，并保持结果类型为 `!symbol.int<"block_id">`。
- `ArchQueryAST(query_name="get_block_num")` 必须 lowering 为单个 `arch.get_block_num`，并保持结果类型为 `!symbol.int<"block_num">`。
- `ArchQueryAST(query_name="get_subthread_id")` 必须 lowering 为单个 `arch.get_subthread_id`，并保持结果类型为 `!symbol.int<"subthread_id">`。
- `ArchQueryAST(query_name="get_subthread_num")` 必须 lowering 为单个 `arch.get_subthread_num`，并保持结果类型为 `!symbol.int<"subthread_num">`。
- `ArchQueryAST(query_name="get_thread_id")` 必须 lowering 为单个 `arch.get_thread_id`，并保持结果类型为 `!symbol.int<"thread_id">`。

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
- 当 `CompareExprAST` 的两侧均为 `!symbol.int<"expr">` 时，`eq` 必须 lowering 为 `symbol.eq`，`ge` 必须 lowering 为 `symbol.ge`，两者结果类型均为 `i1`；其余 symbol 比较操作符必须报错 `Unsupported symbol compare op`。
- 当 `CompareExprAST` 进入 memory 路径时，`lhs/rhs` 必须为 `nn.memory` 类型且 `element_type`/`space` 一致；必要时执行隐式 broadcast。若 `element_type`/`space` 不一致或 broadcast 失败，必须报错并保留位置（例如 `Binary op operands must have the same element_type`、`Binary op operands must have the same space`、`Implicit broadcast dimension mismatch`）。memory 路径的比较结果 element type 必须为 `i1`，并保持与 broadcast 对齐后的 shape/space 一致。
- 当 tensor `truediv` 两侧 dtype 不一致时，必须按固定优先级决议目标 dtype，并在 lowering 中插入 `dma.cast`；`nn.truediv` 的结果类型必须与决议 dtype 一致。
- DMA helper 的公开 lowering 约束如下：
  - `alloc(...)`：lowering 为 `dma.alloc`，返回新的 memory value。
  - `copy(...)`：lowering 为 `dma.copy`，返回目标 memory value。
  - `cast(...)`：lowering 为 `dma.cast`，返回转换后 memory value。
  - `view(...)`：lowering 为 `dma.view`，返回视图 memory value。
  - `reshape(...)`：lowering 为 `dma.reshape`，返回重排后的 memory value。
  - `flatten(...)`：按一维 `reshape` 语义 lowering，返回一维 memory value。
  - `load(...)` / `slice(...)`：lowering 为读取类 DMA op，返回读取结果。
  - `store(...)` / `deslice(...)`：lowering 为写回类 DMA op，作为语句执行。
  - `free(...)`：作为语句执行，不产生新的 SSA 返回值。

节点映射示例：

- `ConstAST`：生成常量或等价字面量 op/value。
- `BinaryExprAST(add/sub/mul/div/floordiv)`：生成对应的二元算术 op。
- `CompareExprAST(eq/ne/lt/le/gt/ge)`：在 memory 路径生成对应 `nn` 比较 op（结果 `element_type` 为 `i1`），必要时隐式 broadcast；在 symbol 路径仅支持 `eq/ge`，分别生成 `symbol.eq/symbol.ge`。
- `LoadAST`：生成张量读取相关 op/value；当携带 `sizes` 时发射 `dma.slice`。
- `StoreAST`：生成张量写入相关 op；当携带 `sizes` 时发射 `dma.deslice`。
- `CallAST(alloc/copy/cast/view/reshape/flatten)`：生成对应 DMA memory 结果。
- `CallAST(free)`：作为无返回值语句处理。
- `ForAST`：当来源于 `LoopRange(start, end, step)` 且边界为 symbol 整数时，生成 `symbol.for`；循环体内若包含 `dma.slice` / `dma.deslice`，其 DMA 标量 operand 直接使用 `!symbol.int<"expr">` value，不生成 `arith.index_cast`。
- `ArchQueryAST(query_name="get_block_id")`：生成 `arch.get_block_id`，返回 `!symbol.int<"block_id">`。
- `ArchQueryAST(query_name="get_block_num")`：生成 `arch.get_block_num`，返回 `!symbol.int<"block_num">`。
- `ArchQueryAST(query_name="get_subthread_id")`：生成 `arch.get_subthread_id`，返回 `!symbol.int<"subthread_id">`。
- `ArchQueryAST(query_name="get_subthread_num")`：生成 `arch.get_subthread_num`，返回 `!symbol.int<"subthread_num">`。
- `ArchQueryAST(query_name="get_thread_id")`：生成 `arch.get_thread_id`，返回 `!symbol.int<"thread_id">`。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 覆盖常见表达式与语句节点的发射结果。
  - 覆盖 `lhs != rhs` 到 `CompareExprAST(op="ne")` 的 memory lowering：`nn.ne` 结果为 `i1`，并支持 implicit broadcast。
  - 覆盖 `CompareExprAST(op="ne")` memory 路径在不可 broadcast 与 element type 不一致时的错误分支与诊断文案。
  - 覆盖 `LoopRange` -> `symbol.for` 与 `it`/DMA operand 直接保持 `symbol.int` 的发射规则。
  - 覆盖 DMA helper 调用的 lowering 结果与语句/表达式边界：`alloc/copy/cast/view/reshape/flatten` 产生 memory 结果，`free` 为无返回值语句。
  - 覆盖 `ArchQueryAST(query_name="get_block_id")` lowering 为 `arch.get_block_id` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_block_num")` lowering 为 `arch.get_block_num` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_subthread_id")` lowering 为 `arch.get_subthread_id` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_subthread_num")` lowering 为 `arch.get_subthread_num` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_thread_id")` lowering 为 `arch.get_thread_id` 的最小查询路径。
  - 覆盖不支持节点的错误路径。
- 功能与用例清单：
  - EMIT-001：二元表达式节点生成对应 op/value。（`test_emit_context_reuses_cached_value`）
  - EMIT-002：比较表达式节点在 memory 路径生成对应 op/value。（`test_emit_mlir_compare_expr_emits_eq`）
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
  - EMIT-015：`alloc(...)` lowering 为 `dma.alloc` 并返回 memory 结果。（`test_emit_mlir_dma_alloc_lowering`）
  - EMIT-016：`copy(...)` lowering 为 `dma.copy` 并返回目标 memory 结果。（`test_emit_mlir_dma_copy_lowering`）
  - EMIT-017：`cast(...)` lowering 为 `dma.cast` 并返回转换后的 memory 结果。（`test_emit_mlir_dma_cast_lowering`）
  - EMIT-018：`view(...)` lowering 为 `dma.view` 并返回视图 memory 结果。（`test_emit_mlir_dma_view_lowering`）
  - EMIT-019：`reshape(...)` lowering 为 `dma.reshape` 并返回重排后的 memory 结果。（`test_emit_mlir_dma_reshape_lowering`）
  - EMIT-020：`flatten(...)` 以一维 `reshape` 语义 lowering，返回一维 memory 结果。（`test_emit_mlir_dma_flatten_lowering`）
  - EMIT-021：`free(...)` 作为无返回值语句执行，不产生新的 SSA 结果。（`test_emit_mlir_dma_free_statement`）
  - EMIT-022：`ArchQueryAST(query_name="get_block_id")` lowering 为单个 `arch.get_block_id`，并返回 `!symbol.int<"block_id">`。（`test_emit_mlir_lowers_arch_get_block_id_query`）
  - EMIT-023：`ArchQueryAST(query_name="get_block_num")` lowering 为单个 `arch.get_block_num`，并返回 `!symbol.int<"block_num">`。（`test_emit_mlir_lowers_arch_get_block_num_query`）
  - EMIT-024：纯 symbol 标量 `>=` 比较在 emit 阶段 lowering 为 `symbol.ge` 且结果为 `i1`；对 symbol 路径中除 `eq/ge` 以外的比较操作符报错 `Unsupported symbol compare op`。（`test_emit_mlir_infer_expr_type_branches`、`test_emit_mlir_lower_expr_unknown_and_symbol_errors`、`test_emit_mlir_lowers_symbol_ge`）
  - EMIT-025：`ArchQueryAST(query_name="get_subthread_id")` lowering 为单个 `arch.get_subthread_id`，并返回 `!symbol.int<"subthread_id">`。（`test_emit_mlir_lowers_arch_get_subthread_id_query`）
  - EMIT-026：`ArchQueryAST(query_name="get_thread_id")` lowering 为单个 `arch.get_thread_id`，并返回 `!symbol.int<"thread_id">`。（`test_emit_mlir_lowers_arch_get_thread_id_query`）
  - EMIT-027：`ArchQueryAST(query_name="get_subthread_num")` lowering 为单个 `arch.get_subthread_num`，并返回 `!symbol.int<"subthread_num">`。（`test_emit_mlir_lowers_arch_get_subthread_num_query`）
  - EMIT-002A：`CompareExprAST(op="ne")` 在 memory 路径必须生成 compare op（必要时带 `nn.broadcast`），结果 element type 为 `i1`。（`test_emit_mlir_binary_compare_broadcast_rhs`）
  - EMIT-002B：`CompareExprAST(op="ne")` memory 路径在不可 broadcast 或 element type/space 不一致时必须报错并保持固定诊断文案。（`test_emit_mlir_compare_memory_mismatch_reports_diagnostics`）
  - EMIT-028：tensor `truediv` mixed dtype promotion 需插入 `dma.cast`，且 `nn.truediv` 结果类型与决议 dtype 一致。（`test_tensor_truediv_dtype_promotion_lowering`）
