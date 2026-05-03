# emit.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel.emit` package 的公开 API、参数、返回值与注意事项。
- 负责节点级 emit、target 注册和 dispatch。
- `func.func` / `builtin.module` 的完整源码组织仍经由当前目录中的 `KernelEmitter` 协作完成，但该 helper 不属于本 package 的公开 API。

## API 列表

- `emit_c(obj: EmitCInput, ctx: EmitCContext) -> str`
- `emit_c_op(op: Operation, ctx: EmitCContext) -> str`
- `emit_c_value(value: SSAValue, ctx: EmitCContext) -> str`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/gen_kernel/emit.md`](../../../spec/dsl/gen_kernel/emit.md)
- `功能实现`：
  - [`kernel_gen/dsl/gen_kernel/emit/__init__.py`](../../../kernel_gen/dsl/gen_kernel/emit/__init__.py)
  - [`kernel_gen/dsl/gen_kernel/emit/register.py`](../../../kernel_gen/dsl/gen_kernel/emit/register.py)
  - [`kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py`](../../../kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py`](../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py)
- `test`：[`test/dsl/gen_kernel/emit/test_package.py`](../../../test/dsl/gen_kernel/emit/test_package.py)

## 依赖

- [`spec/dsl/gen_kernel/emit/register.md`](../../../spec/dsl/gen_kernel/emit/register.md)
- [`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- [`spec/dsl/gen_kernel/emit/cpu/__init__.md`](../../../spec/dsl/gen_kernel/emit/cpu/__init__.md)
- [`spec/dsl/gen_kernel/emit/npu_demo.md`](../../../spec/dsl/gen_kernel/emit/npu_demo.md)

## 目标

- 把 `emit` package 的公开面限定在 3 个发射入口。
- 保持 target-specific 实现仅通过注册体系接入。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 不公开 target 目录中的私有实现 helper。
- 不得把 type、space、include 再拆成平行公开工具模块。
- 注册器与 dispatch 合同单独定义在 [`spec/dsl/gen_kernel/emit/register.md`](../../../spec/dsl/gen_kernel/emit/register.md)。
- `_dispatch_target`、target-specific helper、`KernelEmitter` 与 `kernel_emitter.py` 中的辅助步骤都不是当前 package 公开 API；实现、其他模块与测试不得跨文件直连。
- `symbol.min` 在 `cpu` 与 `npu_demo` target 下必须通过注册体系发射为 C/C++ 三目表达式 `((lhs) < (rhs) ? (lhs) : (rhs))` 语义，不新增公开 helper 或 target-specific 公共入口。
- `target="npu_demo"` 的 `dma.alloc` 发射必须以 `DmaAllocOp.dynamic_shape` 绑定运行期符号值，并从 result memory type 重建完整 shape 与默认连续 stride；只提供部分动态 shape operand 时，静态维度仍必须进入 helper 参数。
- 上述 target-specific 注册函数和布局辅助函数均不是公开 API；测试只能通过 `emit_c(...)`、`emit_c_op(...)` 或 `emit_c_value(...)` 观察。

## API详细说明

### `emit_c(obj: EmitCInput, ctx: EmitCContext) -> str`

- api：`emit_c(obj: EmitCInput, ctx: EmitCContext) -> str`
- 参数：
  - `obj`：`obj` 输入值，参与 `emit_c` 的公开处理流程；类型 `EmitCInput`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  result = emit_c(obj=obj, ctx=ctx)
  ```
- 功能说明：生成 `c`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `emit_c_op(op: Operation, ctx: EmitCContext) -> str`

- api：`emit_c_op(op: Operation, ctx: EmitCContext) -> str`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  result = emit_c_op(op=op, ctx=ctx)
  ```
- 功能说明：生成 `c_op`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `emit_c_value(value: SSAValue, ctx: EmitCContext) -> str`

- api：`emit_c_value(value: SSAValue, ctx: EmitCContext) -> str`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  result = emit_c_value(value=value, ctx=ctx)
  ```
- 功能说明：生成 `c_value`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

## 测试

- 测试文件：`test/dsl/gen_kernel/emit/test_package.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_package.py`

### 测试目标

- 验证 `spec/dsl/gen_kernel/emit.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-GEN-KERNEL-EMIT-001 | 公开入口 | emit c public entry matches gen kernel for empty func | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_public_entry_matches_gen_kernel_for_empty_func`。 | 公开入口在“emit c public entry matches gen kernel for empty func”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_public_entry_matches_gen_kernel_for_empty_func` |
| TC-DSL-GEN-KERNEL-EMIT-002 | 公开入口 | emit c public entry lowers func and single func module consistently | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_public_entry_lowers_func_and_single_func_module_consistently`。 | 公开入口在“emit c public entry lowers func and single func module consistently”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_public_entry_lowers_func_and_single_func_module_consistently` |
| TC-DSL-GEN-KERNEL-EMIT-003 | 公开入口 | emit c package registers common op and value types | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_package_registers_common_op_and_value_types`。 | 公开入口在“emit c package registers common op and value types”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_package_registers_common_op_and_value_types` |
| TC-DSL-GEN-KERNEL-EMIT-004 | 公开入口 | emit c context type helpers use target registry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_context_type_helpers_use_target_registry`。 | 公开入口在“emit c context type helpers use target registry”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_context_type_helpers_use_target_registry` |
| TC-DSL-GEN-KERNEL-EMIT-005 | 公开入口 | emit c context type helpers dispatch npu demo type and space registry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry`。 | 公开入口在“emit c context type helpers dispatch npu demo type and space registry”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry` |
| TC-DSL-GEN-KERNEL-EMIT-006 | 生成/编译 | emit c context reads core config target | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_context_reads_core_config_target`。 | 生成源码、IR 文本或编译结果体现“emit c context reads core config target”场景。 | `test_emit_c_context_reads_core_config_target` |
| TC-DSL-GEN-KERNEL-EMIT-007 | 边界/异常 | emit c package value fast paths and legacy kernel add rejects | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects`。 | “emit c package value fast paths and legacy kernel add rejects”场景按公开错误语义失败或被拒绝。 | `test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects` |
| TC-DSL-GEN-KERNEL-EMIT-008 | pass 改写 | emit c op lowers arith add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_arith_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers arith add”场景。 | `test_emit_c_op_lowers_arith_add` |
| TC-DSL-GEN-KERNEL-EMIT-009 | pass 改写 | emit c value lowers compare | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_value_lowers_compare`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c value lowers compare”场景。 | `test_emit_c_value_lowers_compare` |
| TC-DSL-GEN-KERNEL-EMIT-010 | 生成/编译 | emit c value unbound block argument uses index | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_value_unbound_block_argument_uses_index`。 | 生成源码、IR 文本或编译结果体现“emit c value unbound block argument uses index”场景。 | `test_emit_c_value_unbound_block_argument_uses_index` |
| TC-DSL-GEN-KERNEL-EMIT-011 | pass 改写 | emit c op lowers scf for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_scf_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers scf for”场景。 | `test_emit_c_op_lowers_scf_for` |
| TC-DSL-GEN-KERNEL-EMIT-012 | pass 改写 | emit c op lowers memory access | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_memory_access`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers memory access”场景。 | `test_emit_c_op_lowers_memory_access` |
| TC-DSL-GEN-KERNEL-EMIT-013 | 边界/异常 | emit c op rejects unsupported op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_rejects_unsupported_op`。 | “emit c op rejects unsupported op”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_rejects_unsupported_op` |
| TC-DSL-GEN-KERNEL-EMIT-014 | 边界/异常 | emit c value rejects invalid dependency | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_value_rejects_invalid_dependency`。 | “emit c value rejects invalid dependency”场景按公开错误语义失败或被拒绝。 | `test_emit_c_value_rejects_invalid_dependency` |
| TC-DSL-GEN-KERNEL-EMIT-015 | pass 改写 | emit c op lowers symbol add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_symbol_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers symbol add”场景。 | `test_emit_c_op_lowers_symbol_add` |
| TC-DSL-GEN-KERNEL-EMIT-016 | 边界/异常 | emit c op rejects symbol add on non cpu | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_rejects_symbol_add_on_non_cpu`。 | “emit c op rejects symbol add on non cpu”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_rejects_symbol_add_on_non_cpu` |
| TC-DSL-GEN-KERNEL-EMIT-017 | pass 改写 | emit c op lowers npu demo symbol const cast and to float | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol const cast and to float”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float` |
| TC-DSL-GEN-KERNEL-EMIT-018 | pass 改写 | emit c lowers npu demo plain symbol module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo plain symbol module without launch wrapper”场景。 | `test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper` |
| TC-DSL-GEN-KERNEL-EMIT-019 | pass 改写 | emit c lowers npu demo return only plain module without launch wrapper | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo return only plain module without launch wrapper”场景。 | `test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper` |
| TC-DSL-GEN-KERNEL-EMIT-020 | pass 改写 | emit c op lowers npu demo symbol binary and compare | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol binary and compare”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare` |
| TC-DSL-GEN-KERNEL-EMIT-021 | pass 改写 | emit c op lowers npu demo symbol queries | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_queries`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol queries”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_queries` |
| TC-DSL-GEN-KERNEL-EMIT-022 | pass 改写 | emit c op lowers npu demo symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers npu demo symbol for”场景。 | `test_emit_c_op_lowers_npu_demo_symbol_for` |
| TC-DSL-GEN-KERNEL-EMIT-023 | pass 改写 | emit c op lowers mlir gen NN add variants after pass | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_mlir_gen_nn_add_variants_after_pass`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers mlir gen NN add variants after pass”场景。 | `test_emit_c_op_lowers_mlir_gen_nn_add_variants_after_pass` |
| TC-DSL-GEN-KERNEL-EMIT-024 | 生成/编译 | emit c op keeps NN add unsupported without prebound result or on non cpu | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu`。 | 生成源码、IR 文本或编译结果体现“emit c op keeps NN add unsupported without prebound result or on non cpu”场景。 | `test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu` |
| TC-DSL-GEN-KERNEL-EMIT-025 | 生成/编译 | emit c memory space template alloc | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_memory_space_template_alloc`。 | 生成源码、IR 文本或编译结果体现“emit c memory space template alloc”场景。 | `test_emit_c_memory_space_template_alloc` |
| TC-DSL-GEN-KERNEL-EMIT-026 | 边界/异常 | emit c op lowers kernel family and rejects unsupported reduce kind | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind`。 | “emit c op lowers kernel family and rejects unsupported reduce kind”场景按公开错误语义失败或被拒绝。 | `test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind` |
| TC-DSL-GEN-KERNEL-EMIT-027 | pass 改写 | emit c lowers npu demo DMA alloc helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA alloc helper contract”场景。 | `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-028 | pass 改写 | emit c lowers npu demo DMA broadcast helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA broadcast helper contract”场景。 | `test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-029 | pass 改写 | emit c lowers npu demo DMA scalar broadcast as fill contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_scalar_broadcast_as_fill_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA scalar broadcast as fill contract”场景。 | `test_emit_c_lowers_npu_demo_dma_scalar_broadcast_as_fill_contract` |
| TC-DSL-GEN-KERNEL-EMIT-030 | pass 改写 | emit c lowers cpu DMA broadcast helper contract | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_cpu_dma_broadcast_helper_contract`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers cpu DMA broadcast helper contract”场景。 | `test_emit_c_lowers_cpu_dma_broadcast_helper_contract` |
| TC-DSL-GEN-KERNEL-EMIT-031 | pass 改写 | emit c lowers npu demo DMA misc helper contracts | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_misc_helper_contracts`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA misc helper contracts”场景。 | `test_emit_c_lowers_npu_demo_dma_misc_helper_contracts` |
| TC-DSL-GEN-KERNEL-EMIT-032 | 生成/编译 | emit c private helper and context edges | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_private_helper_and_context_edges`。 | 生成源码、IR 文本或编译结果体现“emit c private helper and context edges”场景。 | `test_emit_c_private_helper_and_context_edges` |
| TC-DSL-GEN-KERNEL-EMIT-033 | 生成/编译 | emit c private layout and operand helpers | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_private_layout_and_operand_helpers`。 | 生成源码、IR 文本或编译结果体现“emit c private layout and operand helpers”场景。 | `test_emit_c_private_layout_and_operand_helpers` |
| TC-DSL-GEN-KERNEL-EMIT-034 | 边界/异常 | emit c private additional error matrix | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_private_additional_error_matrix`。 | “emit c private additional error matrix”场景按公开错误语义失败或被拒绝。 | `test_emit_c_private_additional_error_matrix` |
| TC-DSL-GEN-KERNEL-EMIT-035 | pass 改写 | emit c lowers npu demo DMA indexed and fill helpers | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA indexed and fill helpers”场景。 | `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers` |
| TC-DSL-GEN-KERNEL-EMIT-036 | pass 改写 | emit c lowers npu demo DMA fill infinity literal | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_dma_fill_infinity_literal`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo DMA fill infinity literal”场景。 | `test_emit_c_lowers_npu_demo_dma_fill_infinity_literal` |
| TC-DSL-GEN-KERNEL-EMIT-037 | pass 改写 | emit c op lowers passed mixed add pipeline with DMA fill | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers passed mixed add pipeline with DMA fill”场景。 | `test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill` |
| TC-DSL-GEN-KERNEL-EMIT-038 | pass 改写 | emit c op lowers DMA alloc and view | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_dma_alloc_and_view`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers DMA alloc and view”场景。 | `test_emit_c_op_lowers_dma_alloc_and_view` |
| TC-DSL-GEN-KERNEL-EMIT-039 | pass 改写 | emit c op lowers img2col2d DMA loop pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_img2col2d_dma_loop_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c op lowers img2col2d DMA loop pipeline”场景。 | `test_emit_c_op_lowers_img2col2d_dma_loop_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-040 | 生成/编译 | emit c op assigns unique helper names for repeated DMA slice and deslice | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice`。 | 生成源码、IR 文本或编译结果体现“emit c op assigns unique helper names for repeated DMA slice and deslice”场景。 | `test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice` |
| TC-DSL-GEN-KERNEL-EMIT-041 | 公开入口 | emit c package registers tuner cost op | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_emit_c_package_registers_tuner_cost_op`。 | 公开入口在“emit c package registers tuner cost op”场景下可导入、构造、注册或按名称发现。 | `test_emit_c_package_registers_tuner_cost_op` |
| TC-DSL-GEN-KERNEL-EMIT-042 | pass 改写 | emit c lowers npu demo tuner cost kernel add | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel add”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add` |
| TC-DSL-GEN-KERNEL-EMIT-043 | pass 改写 | emit c lowers npu demo tuner cost kernel binary elewise | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel binary elewise”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise` |
| TC-DSL-GEN-KERNEL-EMIT-044 | pass 改写 | emit c lowers npu demo tuner cost kernel exp select reduce | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel exp select reduce”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce` |
| TC-DSL-GEN-KERNEL-EMIT-045 | pass 改写 | emit c lowers npu demo tuner cost kernel matmul | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel matmul”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul` |
| TC-DSL-GEN-KERNEL-EMIT-046 | pass 改写 | emit c lowers npu demo tuner cost kernel img2col2d | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost kernel img2col2d”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d` |
| TC-DSL-GEN-KERNEL-EMIT-047 | pass 改写 | emit c lowers npu demo tuner cost DMA copy | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost DMA copy”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy` |
| TC-DSL-GEN-KERNEL-EMIT-048 | pass 改写 | emit c lowers npu demo tuner cost DMA slice and deslice | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tuner cost DMA slice and deslice”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice` |
| TC-DSL-GEN-KERNEL-EMIT-049 | pass 改写 | emit c lowers npu demo symbol add with tuner cost value | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo symbol add with tuner cost value”场景。 | `test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value` |
| TC-DSL-GEN-KERNEL-EMIT-050 | 边界/异常 | emit c rejects unknown npu demo tuner cost op name | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name`。 | “emit c rejects unknown npu demo tuner cost op name”场景按公开错误语义失败或被拒绝。 | `test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name` |
| TC-DSL-GEN-KERNEL-EMIT-051 | 边界/异常 | emit c preserves raw npu demo tuner cost kind and rejects invalid memory type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type`。 | “emit c preserves raw npu demo tuner cost kind and rejects invalid memory type”场景按公开错误语义失败或被拒绝。 | `test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type` |
| TC-DSL-GEN-KERNEL-EMIT-052 | pass 改写 | emit c lowers npu demo kernel context queries | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_kernel_context_queries`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo kernel context queries”场景。 | `test_emit_c_lowers_npu_demo_kernel_context_queries` |
| TC-DSL-GEN-KERNEL-EMIT-053 | 生成/编译 | emit c maps NN space to template param | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_emit_c_maps_nn_space_to_template_param`。 | 生成源码、IR 文本或编译结果体现“emit c maps NN space to template param”场景。 | `test_emit_c_maps_nn_space_to_template_param` |
| TC-DSL-GEN-KERNEL-EMIT-054 | pass 改写 | emit c lowers npu demo slice deslice add pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo slice deslice add pipeline”场景。 | `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-055 | pass 改写 | emit c lowers npu demo tiled matmul pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“emit c lowers npu demo tiled matmul pipeline”场景。 | `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline` |
| TC-DSL-GEN-KERNEL-EMIT-056 | pass 改写 | emit c lowers npu demo symbol min as ternary | 准备包含 `symbol.min` 的公开 IR 输入。 | 运行 `test_emit_c_op_lowers_npu_demo_symbol_min_as_ternary`。 | 生成源码使用三目表达式表达 `min(lhs, rhs)`，不新增公开 helper。 | `test_emit_c_op_lowers_npu_demo_symbol_min_as_ternary` |
| TC-DSL-GEN-KERNEL-EMIT-057 | pass 改写 | emit c lowers npu demo DMA alloc dynamic shape and stride | 准备带部分动态 shape 与 `min(...)` 维度的 `dma.alloc` IR。 | 运行 `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract`。 | 源码 helper 参数包含完整 shape 与默认连续 stride，动态维度映射到已发射 C++ 变量。 | `test_emit_c_lowers_npu_demo_dma_alloc_helper_contract` |
