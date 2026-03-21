# mlir_gen.md

## 功能简介

- 综合 AST 解析、AST 遍历与节点发射规则，将 Python 函数转换为 MLIR `func.func` op。
- 统一约束函数签名、参数与返回值的生成规则。
- 不生成 module，不负责文本打印。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `功能实现`：[`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)、[`python/dsl/mlir_gen.py`](../../python/dsl/mlir_gen.py)（统一规范覆盖两条实现入口）
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- AST 节点与解析入口：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 遍历访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- 节点发射规则：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)

## 目标

- 以统一入口生成 `func.func` op。
- 保证函数签名、参数顺序与返回类型与 AST 一致。
- 为上层打印或封装提供稳定的 func op 结果。

## 限制与边界

- 不生成 `builtin.module`。
- 不负责 MLIR 文本打印或后端代码生成。
- 不定义节点级发射细节，节点发射规则由 `emit_mlir` 约束。
- 不做优化或自动修复非法 IR。
- 当函数体仅包含 `for` 循环且没有 `return` 时，输出 `func.func` 允许零返回值。
- 如需 `builtin.module` 封装，由调用方完成。

## 公开接口

### `build_func_op(fn, globals=None, builtins=None, config=None)`

功能说明：

- 解析 Python 函数并生成 `func.func` op。
- 内部依次调用 `parse_function(...)`、`AstVisitor` 与 `emit_mlir`。

参数说明：

- `fn` (`callable`)：受限 Python 函数。
- `globals` (`dict|None`)：注解解析上下文（可选）。
- `builtins` (`dict|None`)：注解解析上下文（可选）。
- `config` (`dict|None`)：行为配置（可选）。

使用示例：

```python
func_op = build_func_op(add)
```

注意事项：

- 解析失败或发射失败必须抛出可定位的错误。
- 允许 `for` 循环内包含 `dma.slice`/`dma.deslice` 相关语义（由 `emit_mlir` 负责具体发射）。

返回与限制：

- 返回 `func.func` op。
- 不返回 module。

### `build_func_op_from_ast(func_ast, config=None)`

功能说明：

- 基于已构建的 `FunctionAST` 生成 `func.func` op。
- 不重复解析 Python 源码。

参数说明：

- `func_ast` (`FunctionAST`)：函数 AST。
- `config` (`dict|None`)：行为配置（可选）。

使用示例：

```python
func_ast = parse_function(add)
func_op = build_func_op_from_ast(func_ast)
```

注意事项：

- 输入 AST 必须满足 `ast.md` 的结构约束。

返回与限制：

- 返回 `func.func` op。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 验证 `build_func_op(...)` 生成 `func.func`。
  - 验证函数签名与返回值类型与 AST 一致。
  - 通过测试辅助封装验证 `func.func` 的结构输出（不改变本模块的边界）。
  - 覆盖无返回 `for` 循环与 `slice/deslice` 的生成能力。
- 功能与用例清单：
  - MGEN-001：`build_func_op(...)` 返回 `func.func`。（`test_build_func_op_returns_func_op`）
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
  - MGEN-015：LoopRange + slice/deslice + 无 return 场景生成 DMA IR。（`test_build_func_op_supports_symbolic_for_loop_dma_without_return`）
