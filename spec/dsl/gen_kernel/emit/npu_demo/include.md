# include.md

## 功能简介

- 定义 `target="npu_demo"` 的头文件文本注册合同。
- 当前负责把 include 文本收口到 `#include "include/npu_demo/npu_demo.h"` 与对应命名空间口径。

## API 列表

本文件不承载公开 API。

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/include.md`](../../../../../spec/dsl/gen_kernel/emit/npu_demo/include.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/npu_demo/include.py`](../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/include.py)
- `test`：[`test/dsl/gen_kernel/emit/test_package.py`](../../../../../test/dsl/gen_kernel/emit/test_package.py)

## 依赖

- [`spec/include/npu_demo/npu_demo.md`](../../../../../spec/include/npu_demo/npu_demo.md)
- [`spec/dsl/gen_kernel/emit/register.md`](../../../../../spec/dsl/gen_kernel/emit/register.md)

## 目标

- 固定 `npu_demo` 的 include 文本来源。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 头文件文本通过注册体系接入，不单独作为 package 公开 API 暴露。
- 文件内未列入公开 API 的注册函数与 helper 不得跨文件直接调用。

## API详细说明

本文件没有公开 API 详细条目；内部注册、目录组织与非公开 helper 边界见“额外补充”。

## 测试

- 测试文件：`test/dsl/gen_kernel/emit/test_package.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_package.py`

### 测试目标

- `npu_demo` include 文本稳定

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-001 | 公开入口 | emit c public entry matches gen kernel for empty func | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_public_entry_matches_gen_kernel_for_empty_func`。 | 公开入口在“emit c public entry matches gen kernel for empty func”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_public_entry_matches_gen_kernel_for_empty_func` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-002 | 公开入口 | emit c public entry lowers func and single func module consistently | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_public_entry_lowers_func_and_single_func_module_consistently`。 | 公开入口在“emit c public entry lowers func and single func module consistently”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_public_entry_lowers_func_and_single_func_module_consistently` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-003 | 公开入口 | emit c package registers common op and value types | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_package_registers_common_op_and_value_types`。 | 公开入口在“emit c package registers common op and value types”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_package_registers_common_op_and_value_types` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-004 | 公开入口 | emit c context type helpers use target registry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_context_type_helpers_use_target_registry`。 | 公开入口在“emit c context type helpers use target registry”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_context_type_helpers_use_target_registry` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-005 | 公开入口 | emit c context type helpers dispatch npu demo type and space registry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry`。 | 公开入口在“emit c context type helpers dispatch npu demo type and space registry”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-006 | 生成/编译 | emit c context reads core config target | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_context_reads_core_config_target`。 | 生成源码、IR 文本或编译结果体现“emit c context reads core config target”场景。 | `test_emit_c_context_reads_core_config_target` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-007 | 边界/异常 | emit c package value fast paths and legacy kernel add rejects | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects`。 | “emit c package value fast paths and legacy kernel add rejects”场景按公开错误语义失败或被拒绝。 | `test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-008 | pass 改写 | emit c op lowers arith add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_arith_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers arith add”场景。 | `test_emit_c_op_lowers_arith_add` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-009 | pass 改写 | emit c value lowers compare | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_value_lowers_compare`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c value lowers compare”场景。 | `test_emit_c_value_lowers_compare` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-010 | 生成/编译 | emit c value unbound block argument uses index | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_value_unbound_block_argument_uses_index`。 | 生成源码、IR 文本或编译结果体现“emit c value unbound block argument uses index”场景。 | `test_emit_c_value_unbound_block_argument_uses_index` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-011 | pass 改写 | emit c op lowers scf for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_scf_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers scf for”场景。 | `test_emit_c_op_lowers_scf_for` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-012 | pass 改写 | emit c op lowers memory access | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_memory_access`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers memory access”场景。 | `test_emit_c_op_lowers_memory_access` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-013 | 边界/异常 | emit c op rejects unsupported op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_rejects_unsupported_op`。 | “emit c op rejects unsupported op”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_rejects_unsupported_op` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-014 | 边界/异常 | emit c value rejects invalid dependency | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_value_rejects_invalid_dependency`。 | “emit c value rejects invalid dependency”场景按公开错误语义失败或被拒绝。 | `test_emit_c_value_rejects_invalid_dependency` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-015 | pass 改写 | emit c op lowers symbol add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_symbol_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers symbol add”场景。 | `test_emit_c_op_lowers_symbol_add` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-016 | 边界/异常 | emit c op rejects symbol add on non cpu | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_rejects_symbol_add_on_non_cpu`。 | “emit c op rejects symbol add on non cpu”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_rejects_symbol_add_on_non_cpu` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-017 | pass 改写 | emit c op lowers npu demo symbol const cast and to float | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol const cast and to float”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-018 | pass 改写 | emit c lowers npu demo plain symbol module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo plain symbol module without launch wrapper”场景。 | `test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-019 | pass 改写 | emit c lowers npu demo return only plain module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo return only plain module without launch wrapper”场景。 | `test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-020 | pass 改写 | emit c op lowers npu demo symbol binary and compare | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol binary and compare”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-021 | pass 改写 | emit c op lowers npu demo symbol queries | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_queries`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol queries”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_queries` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-022 | pass 改写 | emit c op lowers npu demo symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol for”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_for` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-023 | pass 改写 | emit c op lowers mlir gen NN add variants after pass | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_mlir_gen_nn_add_variants_after_pass`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers mlir gen NN add variants after pass”场景。 | `test_emit_c_op_lowers_mlir_gen_nn_add_variants_after_pass` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-024 | 生成/编译 | emit c op keeps NN add unsupported without prebound result or on non cpu | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu`。 | 生成源码、IR 文本或编译结果体现“emit c op keeps NN add unsupported without prebound result or on non cpu”场景。 | `test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-025 | 生成/编译 | emit c memory space template alloc | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_memory_space_template_alloc`。 | 生成源码、IR 文本或编译结果体现“emit c memory space template alloc”场景。 | `test_emit_c_memory_space_template_alloc` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-026 | 边界/异常 | emit c op lowers kernel family and rejects unsupported reduce kind | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind`。 | “emit c op lowers kernel family and rejects unsupported reduce kind”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-027 | pass 改写 | emit c lowers npu demo DMA alloc helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA alloc helper contract”场景。 | `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-028 | pass 改写 | emit c lowers npu demo DMA broadcast helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA broadcast helper contract”场景。 | `test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-029 | pass 改写 | emit c lowers npu demo DMA scalar broadcast as fill contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_scalar_broadcast_as_fill_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA scalar broadcast as fill contract”场景。 | `test_emit_c_lowers_npu_demo_dma_scalar_broadcast_as_fill_contract` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-030 | pass 改写 | emit c lowers cpu DMA broadcast helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_cpu_dma_broadcast_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers cpu DMA broadcast helper contract”场景。 | `test_emit_c_lowers_cpu_dma_broadcast_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-031 | pass 改写 | emit c lowers npu demo DMA misc helper contracts | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_misc_helper_contracts`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA misc helper contracts”场景。 | `test_emit_c_lowers_npu_demo_dma_misc_helper_contracts` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-032 | 生成/编译 | emit c private helper and context edges | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_private_helper_and_context_edges`。 | 生成源码、IR 文本或编译结果体现“emit c private helper and context edges”场景。 | `test_emit_c_private_helper_and_context_edges` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-033 | 生成/编译 | emit c private layout and operand helpers | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_private_layout_and_operand_helpers`。 | 生成源码、IR 文本或编译结果体现“emit c private layout and operand helpers”场景。 | `test_emit_c_private_layout_and_operand_helpers` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-034 | 边界/异常 | emit c private additional error matrix | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_private_additional_error_matrix`。 | “emit c private additional error matrix”场景按公开错误语义失败或被拒绝。 | `test_emit_c_private_additional_error_matrix` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-035 | pass 改写 | emit c lowers npu demo DMA indexed and fill helpers | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA indexed and fill helpers”场景。 | `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-036 | pass 改写 | emit c lowers npu demo DMA fill infinity literal | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_fill_infinity_literal`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA fill infinity literal”场景。 | `test_emit_c_lowers_npu_demo_dma_fill_infinity_literal` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-037 | pass 改写 | emit c op lowers passed mixed add pipeline with DMA fill | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers passed mixed add pipeline with DMA fill”场景。 | `test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-038 | pass 改写 | emit c op lowers DMA alloc and view | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_dma_alloc_and_view`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers DMA alloc and view”场景。 | `test_emit_c_op_lowers_dma_alloc_and_view` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-039 | pass 改写 | emit c op lowers img2col2d DMA loop pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_img2col2d_dma_loop_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers img2col2d DMA loop pipeline”场景。 | `test_emit_c_op_lowers_img2col2d_dma_loop_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-040 | 生成/编译 | emit c op assigns unique helper names for repeated DMA slice and deslice | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice`。 | 生成源码、IR 文本或编译结果体现“emit c op assigns unique helper names for repeated DMA slice and deslice”场景。 | `test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-041 | 公开入口 | emit c package registers tuner cost op | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_package_registers_tuner_cost_op`。 | 公开入口在“emit c package registers tuner cost op”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_package_registers_tuner_cost_op` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-042 | pass 改写 | emit c lowers npu demo tuner cost kernel add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel add”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-043 | pass 改写 | emit c lowers npu demo tuner cost kernel binary elewise | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel binary elewise”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-044 | pass 改写 | emit c lowers npu demo tuner cost kernel exp select reduce | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel exp select reduce”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-045 | pass 改写 | emit c lowers npu demo tuner cost kernel matmul | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel matmul”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-046 | pass 改写 | emit c lowers npu demo tuner cost kernel img2col2d | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel img2col2d”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-047 | pass 改写 | emit c lowers npu demo tuner cost DMA copy | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost DMA copy”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-048 | pass 改写 | emit c lowers npu demo tuner cost DMA slice and deslice | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost DMA slice and deslice”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-049 | pass 改写 | emit c lowers npu demo symbol add with tuner cost value | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo symbol add with tuner cost value”场景。 | `test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-050 | 边界/异常 | emit c rejects unknown npu demo tuner cost op name | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name`。 | “emit c rejects unknown npu demo tuner cost op name”场景按公开错误语义失败或被拒绝。 | `test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-051 | 边界/异常 | emit c preserves raw npu demo tuner cost kind and rejects invalid memory type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type`。 | “emit c preserves raw npu demo tuner cost kind and rejects invalid memory type”场景按公开错误语义失败或被拒绝。 | `test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-052 | pass 改写 | emit c lowers npu demo kernel context queries | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_kernel_context_queries`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo kernel context queries”场景。 | `test_emit_c_lowers_npu_demo_kernel_context_queries` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-053 | 生成/编译 | emit c maps NN space to template param | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_maps_nn_space_to_template_param`。 | 生成源码、IR 文本或编译结果体现“emit c maps NN space to template param”场景。 | `test_emit_c_maps_nn_space_to_template_param` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-054 | pass 改写 | emit c lowers npu demo slice deslice add pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo slice deslice add pipeline”场景。 | `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-NPU-DEMO-INCLUDE-055 | pass 改写 | emit c lowers npu demo tiled matmul pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tiled matmul pipeline”场景。 | `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline` |
