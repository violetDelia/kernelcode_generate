# AST MLIR 生成入口

## 功能简介

- `kernel_gen.dsl.ast.mlir_gen` 提供 AST 架构下唯一公开 MLIR 生成入口。
- `mlir_gen(fn, *runtime_args)` 返回 xDSL `ModuleOp`，不是字符串，也不是 `ModuleAST`。

## API 列表

- `mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/mlir_gen.md`
- `功能实现`：`kernel_gen/dsl/ast/mlir_gen.py`
- `test`：`test/dsl/ast/test_mlir_gen.py`

## 依赖

- `spec/dsl/ast/parser.md`：生成 `ModuleAST`。
- `spec/dsl/ast/nodes/basic.md`：`ModuleAST.emit_mlir(ctx, None)`。
- xDSL `ModuleOp`：公开返回值类型。

## API详细说明

### `mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`

- api：`mlir_gen(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg) -> ModuleOp`
- 参数：
  - `fn`：Python DSL 函数；必须可调用。
  - `runtime_args`：显式运行时参数；数量不得少于函数形参数量。
- 返回值：xDSL `ModuleOp`。
- 使用示例：

  ```python
  module_op = mlir_gen(kernel, lhs, rhs)
  ```
- 功能说明：固定执行 `parse(fn, *runtime_args).emit_mlir(ctx, None)`，其中 `ctx` 由本入口创建。
- 注意事项：不接受 `globals`、`builtins`、`config` 参数；缺少 runtime arg 必须报 `mlir_gen requires explicit runtime args for <fn>: expected <n>, got <m>`。

## 测试

- 测试文件：`test/dsl/ast/test_mlir_gen.py`
- 执行命令：`pytest -q test/dsl/ast/test_mlir_gen.py`

### 测试目标

- `mlir_gen(...)` 返回 `ModuleOp` 并生成合法函数。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-MLIR-GEN-001 | 边界/异常 | MLIR gen requires runtime args | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_requires_runtime_args`。 | “MLIR gen requires runtime args”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_requires_runtime_args` |
| TC-DSL-AST-MLIR-GEN-002 | 公开入口 | MLIR gen returns module with root func | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_returns_module_with_root_func`。 | 公开入口在“MLIR gen returns module with root func”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_returns_module_with_root_func` |
| TC-DSL-AST-MLIR-GEN-003 | 符号语义 | MLIR gen reports reduce max axis out of range | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_mlir_gen_reports_reduce_max_axis_out_of_range`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“MLIR gen reports reduce max axis out of range”场景。 | `test_mlir_gen_reports_reduce_max_axis_out_of_range` |
| TC-DSL-AST-MLIR-GEN-004 | 执行结果 | MLIR gen accepts runtime driven memory placeholder annotation | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_mlir_gen_accepts_runtime_driven_memory_placeholder_annotation`。 | 命令返回码、输出、执行结果或状态变更体现“MLIR gen accepts runtime driven memory placeholder annotation”场景。 | `test_mlir_gen_accepts_runtime_driven_memory_placeholder_annotation` |
| TC-DSL-AST-MLIR-GEN-005 | 执行结果 | MLIR gen accepts runtime driven symbol placeholder annotation | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_mlir_gen_accepts_runtime_driven_symbol_placeholder_annotation`。 | 命令返回码、输出、执行结果或状态变更体现“MLIR gen accepts runtime driven symbol placeholder annotation”场景。 | `test_mlir_gen_accepts_runtime_driven_symbol_placeholder_annotation` |
| TC-DSL-AST-MLIR-GEN-006 | 内存/DMA | MLIR gen supports kernel contract metadata assert and shape unpack | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_mlir_gen_supports_kernel_contract_metadata_assert_and_shape_unpack`。 | 内存类型、布局、搬运结果或 verifier 行为体现“MLIR gen supports kernel contract metadata assert and shape unpack”场景。 | `test_mlir_gen_supports_kernel_contract_metadata_assert_and_shape_unpack` |
| TC-DSL-AST-MLIR-GEN-007 | 公开入口 | MLIR gen supports kernel contract loop local rebinding | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_supports_kernel_contract_loop_local_rebinding`。 | 公开入口在“MLIR gen supports kernel contract loop local rebinding”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_supports_kernel_contract_loop_local_rebinding` |
| TC-DSL-AST-MLIR-GEN-008 | 执行结果 | MLIR gen uses runtime args for symbol signature | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_mlir_gen_uses_runtime_args_for_symbol_signature`。 | 命令返回码、输出、执行结果或状态变更体现“MLIR gen uses runtime args for symbol signature”场景。 | `test_mlir_gen_uses_runtime_args_for_symbol_signature` |
| TC-DSL-AST-MLIR-GEN-009 | 公开入口 | MLIR gen supports multiple return values | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_supports_multiple_return_values`。 | 公开入口在“MLIR gen supports multiple return values”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_supports_multiple_return_values` |
| TC-DSL-AST-MLIR-GEN-010 | 内存/DMA | MLIR gen supports DMA alloc helper with symbol shape args | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_mlir_gen_supports_dma_alloc_helper_with_symbol_shape_args`。 | 内存类型、布局、搬运结果或 verifier 行为体现“MLIR gen supports DMA alloc helper with symbol shape args”场景。 | `test_mlir_gen_supports_dma_alloc_helper_with_symbol_shape_args` |
| TC-DSL-AST-MLIR-GEN-011 | 边界/异常 | MLIR gen rejects DMA alloc helper with non contiguous stride | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_rejects_dma_alloc_helper_with_non_contiguous_stride`。 | “MLIR gen rejects DMA alloc helper with non contiguous stride”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_rejects_dma_alloc_helper_with_non_contiguous_stride` |
| TC-DSL-AST-MLIR-GEN-012 | 执行结果 | MLIR gen mixed dtype return annotation uses body result type | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_mlir_gen_mixed_dtype_return_annotation_uses_body_result_type`。 | 命令返回码、输出、执行结果或状态变更体现“MLIR gen mixed dtype return annotation uses body result type”场景。 | `test_mlir_gen_mixed_dtype_return_annotation_uses_body_result_type` |
| TC-DSL-AST-MLIR-GEN-013 | 公开入口 | MLIR gen supports flatten return annotation | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_supports_flatten_return_annotation`。 | 公开入口在“MLIR gen supports flatten return annotation”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_supports_flatten_return_annotation` |
| TC-DSL-AST-MLIR-GEN-014 | 解析/打印 | MLIR gen matches public parse function | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_mlir_gen_matches_public_parse_function`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_mlir_gen_matches_public_parse_function` |
| TC-DSL-AST-MLIR-GEN-015 | 公开入口 | MLIR gen lowers public tensor axis access | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_lowers_public_tensor_axis_access`。 | 公开入口在“MLIR gen lowers public tensor axis access”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_lowers_public_tensor_axis_access` |
| TC-DSL-AST-MLIR-GEN-016 | 公开入口 | MLIR gen lowers public DMA helpers | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_lowers_public_dma_helpers`。 | 公开入口在“MLIR gen lowers public DMA helpers”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_lowers_public_dma_helpers` |
| TC-DSL-AST-MLIR-GEN-017 | 边界/异常 | MLIR gen reports public broadcast mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_reports_public_broadcast_mismatch`。 | “MLIR gen reports public broadcast mismatch”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_reports_public_broadcast_mismatch` |
| TC-DSL-AST-MLIR-GEN-018 | 公开入口 | MLIR gen lowers public DMA fill helper | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_lowers_public_dma_fill_helper`。 | 公开入口在“MLIR gen lowers public DMA fill helper”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_lowers_public_dma_fill_helper` |
| TC-DSL-AST-MLIR-GEN-019 | 生成/编译 | module ast emit MLIR matches MLIR gen entry | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_module_ast_emit_mlir_matches_mlir_gen_entry`。 | 生成源码、IR 文本或编译结果体现“module ast emit MLIR matches MLIR gen entry”场景。 | `test_module_ast_emit_mlir_matches_mlir_gen_entry` |
| TC-DSL-AST-MLIR-GEN-020 | 生成/编译 | MLIR gen emits python callee call | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_mlir_gen_emits_python_callee_call`。 | 生成源码、IR 文本或编译结果体现“MLIR gen emits python callee call”场景。 | `test_mlir_gen_emits_python_callee_call` |
| TC-DSL-AST-MLIR-GEN-021 | 生成/编译 | MLIR gen emits supported closure callee | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_mlir_gen_emits_supported_closure_callee`。 | 生成源码、IR 文本或编译结果体现“MLIR gen emits supported closure callee”场景。 | `test_mlir_gen_emits_supported_closure_callee` |
| TC-DSL-AST-MLIR-GEN-022 | 边界/异常 | MLIR gen rejects invalid dynamic memory in root | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_rejects_invalid_dynamic_memory_in_root`。 | “MLIR gen rejects invalid dynamic memory in root”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_rejects_invalid_dynamic_memory_in_root` |
| TC-DSL-AST-MLIR-GEN-023 | 公开入口 | MLIR gen reuses repeated python callee call | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_reuses_repeated_python_callee_call`。 | 公开入口在“MLIR gen reuses repeated python callee call”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_reuses_repeated_python_callee_call` |
| TC-DSL-AST-MLIR-GEN-024 | 公开入口 | MLIR gen binds python callee argument from DSL node | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_binds_python_callee_argument_from_dsl_node`。 | 公开入口在“MLIR gen binds python callee argument from DSL node”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_binds_python_callee_argument_from_dsl_node` |
| TC-DSL-AST-MLIR-GEN-025 | 生成/编译 | MLIR gen emits transitive python callees in first use order | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_mlir_gen_emits_transitive_python_callees_in_first_use_order`。 | 生成源码、IR 文本或编译结果体现“MLIR gen emits transitive python callees in first use order”场景。 | `test_mlir_gen_emits_transitive_python_callees_in_first_use_order` |
| TC-DSL-AST-MLIR-GEN-026 | 边界/异常 | MLIR gen rejects recursive python callee | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_rejects_recursive_python_callee`。 | “MLIR gen rejects recursive python callee”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_rejects_recursive_python_callee` |
| TC-DSL-AST-MLIR-GEN-027 | 边界/异常 | MLIR gen rejects python callee result assignment | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_rejects_python_callee_result_assignment`。 | “MLIR gen rejects python callee result assignment”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_rejects_python_callee_result_assignment` |
| TC-DSL-AST-MLIR-GEN-028 | 边界/异常 | MLIR gen rejects python callee value return | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_rejects_python_callee_value_return`。 | “MLIR gen rejects python callee value return”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_rejects_python_callee_value_return` |
| TC-DSL-AST-MLIR-GEN-029 | 边界/异常 | MLIR gen rejects python callee in value contexts | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_rejects_python_callee_in_value_contexts`。 | “MLIR gen rejects python callee in value contexts”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_rejects_python_callee_in_value_contexts` |
| TC-DSL-AST-MLIR-GEN-030 | 解析/打印 | MLIR gen uses runtime args over shadowed parse env names | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_mlir_gen_uses_runtime_args_over_shadowed_parse_env_names`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_mlir_gen_uses_runtime_args_over_shadowed_parse_env_names` |
| TC-DSL-AST-MLIR-GEN-031 | 执行结果 | MLIR gen globals cannot replace runtime args | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_mlir_gen_globals_cannot_replace_runtime_args`。 | 命令返回码、输出、执行结果或状态变更体现“MLIR gen globals cannot replace runtime args”场景。 | `test_mlir_gen_globals_cannot_replace_runtime_args` |
| TC-DSL-AST-MLIR-GEN-032 | 边界/异常 | MLIR gen rejects builtins external value reference | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_rejects_builtins_external_value_reference`。 | “MLIR gen rejects builtins external value reference”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_rejects_builtins_external_value_reference` |
| TC-DSL-AST-MLIR-GEN-033 | 边界/异常 | module ast emit MLIR requires context | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_module_ast_emit_mlir_requires_context`。 | “module ast emit MLIR requires context”场景按公开错误语义失败或被拒绝。 | `test_module_ast_emit_mlir_requires_context` |
| TC-DSL-AST-MLIR-GEN-034 | 生成/编译 | module ast emit MLIR returns module op | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_module_ast_emit_mlir_returns_module_op`。 | 生成源码、IR 文本或编译结果体现“module ast emit MLIR returns module op”场景。 | `test_module_ast_emit_mlir_returns_module_op` |
| TC-DSL-AST-MLIR-GEN-035 | 公开入口 | MLIR gen lowers NN matmul public helper | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_lowers_nn_matmul_public_helper`。 | 公开入口在“MLIR gen lowers NN matmul public helper”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_lowers_nn_matmul_public_helper` |
| TC-DSL-AST-MLIR-GEN-036 | 内存/DMA | MLIR gen reuses bound memory expr with symbol axis arithmetic | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_mlir_gen_reuses_bound_memory_expr_with_symbol_axis_arithmetic`。 | 内存类型、布局、搬运结果或 verifier 行为体现“MLIR gen reuses bound memory expr with symbol axis arithmetic”场景。 | `test_mlir_gen_reuses_bound_memory_expr_with_symbol_axis_arithmetic` |
| TC-DSL-AST-MLIR-GEN-037 | 边界/异常 | parse function public error path stays ast parse error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_function_public_error_path_stays_ast_parse_error`。 | “parse function public error path stays ast parse error”场景按公开错误语义失败或被拒绝。 | `test_parse_function_public_error_path_stays_ast_parse_error` |
| TC-DSL-AST-MLIR-GEN-038 | pass 改写 | MLIR gen lowers symbolic loop and DMA chain | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_mlir_gen_lowers_symbolic_loop_and_dma_chain`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“MLIR gen lowers symbolic loop and DMA chain”场景。 | `test_mlir_gen_lowers_symbolic_loop_and_dma_chain` |
| TC-DSL-AST-MLIR-GEN-039 | 符号语义 | MLIR gen normalizes softmax default axis to last dimension | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_mlir_gen_normalizes_softmax_default_axis_to_last_dimension`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“MLIR gen normalizes softmax default axis to last dimension”场景。 | `test_mlir_gen_normalizes_softmax_default_axis_to_last_dimension` |
| TC-DSL-AST-MLIR-GEN-040 | 符号语义 | MLIR gen normalizes softmax negative axis to positive axis | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_mlir_gen_normalizes_softmax_negative_axis_to_positive_axis`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“MLIR gen normalizes softmax negative axis to positive axis”场景。 | `test_mlir_gen_normalizes_softmax_negative_axis_to_positive_axis` |
