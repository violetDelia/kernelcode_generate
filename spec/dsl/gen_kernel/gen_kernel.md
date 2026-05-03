# gen_kernel.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel` 目录在源码生成层的公开入口合同。
- 本轮新增的公开能力只有 `dsl_gen_kernel(...)` callable 入口；现有 `gen_kernel(obj, ctx)` 必须继续作为稳定 IR / op 源码生成入口保留。
- `dsl_gen_kernel(...)` 必须复用公开 `mlir_gen(...) + gen_kernel(...)` 链路，不允许在当前目录外跨文件直连 parser、module-builder 或 `kernel_emitter.py` 非公开 helper 来复制第二套 emitter。
- 包根 `kernel_gen.dsl.gen_kernel` 继续承接 sibling spec 已定义的 `EmitCContext`、`emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)` 与 `KernelEmitter`；本文件只展开 `gen_kernel(...)` 与新增 `dsl_gen_kernel(...)` 这组入口。
- 失败统一抛出 `KernelCodeError(ErrorModule.GEN_KERNEL, message)`；不再定义或导出源码生成专属错误类。
- 当前文件内若保留参数归一化、目标默认值或兼容失败 helper，它们都只属于文件内实现细节，不属于公开 API。

## API 列表

- `gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str`
- `dsl_gen_kernel(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg, ctx: EmitCContext) -> str`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/__init__.py`](../../../kernel_gen/dsl/gen_kernel/__init__.py)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)
- `test`：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- `test`：[`test/dsl/test_package.py`](../../../test/dsl/test_package.py)

## 依赖

- [`spec/dsl/gen_kernel/kernel_emitter.md`](../../../spec/dsl/gen_kernel/kernel_emitter.md)
- [`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- [`spec/dsl/gen_kernel/emit.md`](../../../spec/dsl/gen_kernel/emit.md)

## 目标

- 为 `kernel_gen.dsl.gen_kernel` 包根新增 `dsl_gen_kernel(...)` callable 公开入口。
- 保持 `kernel_gen.dsl.gen_kernel` 包根导出与当前实现、pytest 一致。
- 保持 `gen_kernel(...)` 为源码级主入口，不回退到旧 `gen_signature` / `gen_body` 双接口。
- 避免在本模块内再维护第二份 emit 逻辑或 target 特化逻辑。
- 让 pass/pipeline 输出的 host wrapper + device body 双函数 IR 统一经由 `gen_kernel(...)` 消费，不要求调用方感知内部 emitter 拆分。
- `kernel_gen.core.config.dump_dir` 非空时，`gen_kernel(...)` 必须把最终源码同步写入 `dump_dir/source.cpp`；调用方只负责设置 dump 目录，不再自行重复写源码。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本模块不定义节点级 emit 细节；这些由 `emit/` 子系统负责。
- `dsl_gen_kernel(...)` 只接受 Python DSL callable + `runtime_args`；实现必须先调用公开 `mlir_gen(fn, *runtime_args)` 生成 `builtin.module`，再调用公开 `gen_kernel(module_or_func, ctx)` 生成源码。
- `gen_kernel(...)` 继续只消费 op / `func.func` / 受控 `builtin.module` IR；`dsl_gen_kernel(...)` 不是 `gen_kernel(...)` 的别名模式，也不能接管 `dsl_run`、`ircheck` 这类已有 IR 路径消费者。
- `dump_dir` 只控制诊断落盘，不改变 `gen_kernel(...)` 的返回值、target 选择或源码内容；为空时不得创建 `source.cpp`。
- 本文件当前允许实现的公开入口只有 `gen_kernel(...)` 与 `dsl_gen_kernel(...)`；除 sibling spec 已单独定义的包根 re-export 外，不得再新增平行 callable 别名或隐藏快捷入口。
- 若输入为普通 op，只允许直接委托节点级 `emit_c_op(...)`。
- `KernelEmitter`、`kernel_emitter.py` 内的 `_` 前缀 helper、`mlir_gen` 子系统的 parse-env / module-builder 私有 helper，以及 `emit_include()` 都不是当前文件公开 API；实现、其他模块与测试不得把它们当成稳定跨文件入口。
- package-root 仍必须稳定拒绝 `gen_signature` / `gen_body` 这类旧公开名；新增 `dsl_gen_kernel(...)` 不得回退这条 legacy 拒绝合同。
## API详细说明

### `gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str`

- api：`gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str`
- 参数：
  - `obj`：`obj` 输入值，参与 `gen_kernel` 的公开处理流程；类型 `GenKernelInput`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  result = gen_kernel(obj=obj, ctx=ctx)
  ```
- 功能说明：执行 `gen_kernel`。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `dsl_gen_kernel(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg, ctx: EmitCContext) -> str`

- api：`dsl_gen_kernel(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg, ctx: EmitCContext) -> str`
- 参数：
  - `fn`：可调用对象，作为 DSL 构建、执行或包装入口的主体；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `runtime_args`：运行期实参序列，与 DSL 函数形参按顺序对应；类型 `DslRuntimeArg`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `EmitCContext`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  result = dsl_gen_kernel(fn=fn, runtime_args=runtime_args, ctx=ctx)
  ```
- 功能说明：执行 `dsl_gen_kernel`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/dsl/test_package.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py`

### 测试目标

- 验证 `spec/dsl/gen_kernel/gen_kernel.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-001 | 生成/编译 | gen kernel dump dir writes source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_dump_dir_writes_source`。 | 生成源码、IR 文本或编译结果体现“gen kernel dump dir writes source”场景。 | `test_gen_kernel_dump_dir_writes_source` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-002 | 公开入口 | gen kernel public modules exist and old legacy loader path is gone | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone`。 | 公开入口在“gen kernel public modules exist and old legacy loader path is gone”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-003 | pass 改写 | tile gen kernel paths use kernel gen tile modules | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_gen_kernel_paths_use_kernel_gen_tile_modules`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile gen kernel paths use kernel gen tile modules”场景。 | `test_tile_gen_kernel_paths_use_kernel_gen_tile_modules` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-004 | 生成/编译 | gen kernel local compile helpers delegate local compile runner | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_local_compile_helpers_delegate_local_compile_runner`。 | 生成源码、IR 文本或编译结果体现“gen kernel local compile helpers delegate local compile runner”场景。 | `test_gen_kernel_local_compile_helpers_delegate_local_compile_runner` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-005 | 生成/编译 | gen kernel returns target source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_returns_target_source`。 | 生成源码、IR 文本或编译结果体现“gen kernel returns target source”场景。 | `test_gen_kernel_returns_target_source` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-006 | 边界/异常 | gen kernel converts emit error to gen kernel error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_converts_emit_error_to_gen_kernel_error`。 | “gen kernel converts emit error to gen kernel error”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_converts_emit_error_to_gen_kernel_error` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-007 | 生成/编译 | gen kernel entry module hides internal emitter entry | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_entry_module_hides_internal_emitter_entry`。 | 生成源码、IR 文本或编译结果体现“gen kernel entry module hides internal emitter entry”场景。 | `test_gen_kernel_entry_module_hides_internal_emitter_entry` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-008 | 公开入口 | gen kernel is the package public entry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_is_the_package_public_entry`。 | 公开入口在“gen kernel is the package public entry”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_is_the_package_public_entry` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-009 | 公开入口 | DSL gen kernel matches public MLIR gen plus gen kernel path | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path`。 | 公开入口在“DSL gen kernel matches public MLIR gen plus gen kernel path”场景下可导入、构造、注册或按名称发现。 | `test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-010 | 生成/编译 | gen kernel has no legacy double interface | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_has_no_legacy_double_interface`。 | 生成源码、IR 文本或编译结果体现“gen kernel has no legacy double interface”场景。 | `test_gen_kernel_has_no_legacy_double_interface` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-011 | 生成/编译 | gen kernel delegates single op input to emit c | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_delegates_single_op_input_to_emit_c`。 | 生成源码、IR 文本或编译结果体现“gen kernel delegates single op input to emit c”场景。 | `test_gen_kernel_delegates_single_op_input_to_emit_c` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-012 | 生成/编译 | gen kernel uses mutable memory inputs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_uses_mutable_memory_inputs`。 | 生成源码、IR 文本或编译结果体现“gen kernel uses mutable memory inputs”场景。 | `test_gen_kernel_uses_mutable_memory_inputs` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-013 | 生成/编译 | gen kernel accepts rewritten single output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_single_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten single output function”场景。 | `test_gen_kernel_accepts_rewritten_single_output_function` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-014 | 生成/编译 | gen kernel rewritten deslice memory result uses front out param | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param`。 | 生成源码、IR 文本或编译结果体现“gen kernel rewritten deslice memory result uses front out param”场景。 | `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-015 | 生成/编译 | gen kernel uses default arg names when missing attrs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_uses_default_arg_names_when_missing_attrs`。 | 生成源码、IR 文本或编译结果体现“gen kernel uses default arg names when missing attrs”场景。 | `test_gen_kernel_uses_default_arg_names_when_missing_attrs` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-016 | 生成/编译 | gen kernel emits ops in order | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_ops_in_order`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits ops in order”场景。 | `test_gen_kernel_emits_ops_in_order` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-017 | 生成/编译 | gen kernel delegates to emit c for non return ops | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_delegates_to_emit_c_for_non_return_ops`。 | 生成源码、IR 文本或编译结果体现“gen kernel delegates to emit c for non return ops”场景。 | `test_gen_kernel_delegates_to_emit_c_for_non_return_ops` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-018 | 生成/编译 | gen kernel handles func return and out binding in main flow | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_handles_func_return_and_out_binding_in_main_flow`。 | 生成源码、IR 文本或编译结果体现“gen kernel handles func return and out binding in main flow”场景。 | `test_gen_kernel_handles_func_return_and_out_binding_in_main_flow` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-019 | 边界/异常 | kernel emitter public dispatch error boundaries | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_emitter_public_dispatch_error_boundaries`。 | “kernel emitter public dispatch error boundaries”场景按公开错误语义失败或被拒绝。 | `test_kernel_emitter_public_dispatch_error_boundaries` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-020 | 公开入口 | kernel emitter public include and type dispatch | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_kernel_emitter_public_include_and_type_dispatch`。 | 公开入口在“kernel emitter public include and type dispatch”场景下可导入、构造、注册或按名称发现。 | `test_kernel_emitter_public_include_and_type_dispatch` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-021 | 生成/编译 | gen kernel assembles loop body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_assembles_loop_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel assembles loop body”场景。 | `test_gen_kernel_assembles_loop_body` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-022 | 边界/异常 | gen kernel propagates emit error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_propagates_emit_error`。 | “gen kernel propagates emit error”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_propagates_emit_error` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-023 | 边界/异常 | gen kernel rejects unsupported return form | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_unsupported_return_form`。 | “gen kernel rejects unsupported return form”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_unsupported_return_form` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-024 | 生成/编译 | gen kernel supports float32 scalar and memory | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_supports_float32_scalar_and_memory`。 | 生成源码、IR 文本或编译结果体现“gen kernel supports float32 scalar and memory”场景。 | `test_gen_kernel_supports_float32_scalar_and_memory` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-025 | 生成/编译 | gen kernel preserves function and arg names | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_preserves_function_and_arg_names`。 | 生成源码、IR 文本或编译结果体现“gen kernel preserves function and arg names”场景。 | `test_gen_kernel_preserves_function_and_arg_names` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-026 | 生成/编译 | gen kernel supports symbol scalar return | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_supports_symbol_scalar_return`。 | 生成源码、IR 文本或编译结果体现“gen kernel supports symbol scalar return”场景。 | `test_gen_kernel_supports_symbol_scalar_return` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-027 | 边界/异常 | gen kernel rejects symbol scalar return on non cpu | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu`。 | “gen kernel rejects symbol scalar return on non cpu”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-028 | pass 改写 | gen kernel supports lowered NN add memory memory on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory memory on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-029 | pass 改写 | gen kernel supports lowered NN add memory const on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory const on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-030 | pass 改写 | gen kernel supports lowered NN add memory symbol on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory symbol on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-031 | 生成/编译 | gen kernel accepts rewritten single output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_single_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten single output function”场景。 | `test_gen_kernel_accepts_rewritten_single_output_function` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-032 | 生成/编译 | gen kernel accepts rewritten mixed output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_mixed_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten mixed output function”场景。 | `test_gen_kernel_accepts_rewritten_mixed_output_function` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-033 | pass 改写 | rewritten pipeline has no memory return abi left | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_rewritten_pipeline_has_no_memory_return_abi_left`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“rewritten pipeline has no memory return abi left”场景。 | `test_rewritten_pipeline_has_no_memory_return_abi_left` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-034 | 边界/异常 | gen kernel rejects lowered IR without buffer results to out params | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params`。 | “gen kernel rejects lowered IR without buffer results to out params”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-035 | 边界/异常 | rewritten pipeline fails on half rewritten IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_rewritten_pipeline_fails_on_half_rewritten_ir`。 | “rewritten pipeline fails on half rewritten IR”场景按公开错误语义失败或被拒绝。 | `test_rewritten_pipeline_fails_on_half_rewritten_ir` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-036 | 生成/编译 | gen kernel emits npu demo body level kernel | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_body_level_kernel`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo body level kernel”场景。 | `test_gen_kernel_emits_npu_demo_body_level_kernel` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-037 | 生成/编译 | gen kernel emits npu demo kernel binary signature out first | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo kernel binary signature out first”场景。 | `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-038 | 生成/编译 | gen kernel emits npu demo DMA alloc module | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_dma_alloc_module`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo DMA alloc module”场景。 | `test_gen_kernel_emits_npu_demo_dma_alloc_module` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-039 | 生成/编译 | gen kernel compiles npu demo source with single include | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_source_with_single_include`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo source with single include”场景。 | `test_gen_kernel_compiles_npu_demo_source_with_single_include` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-040 | pass 改写 | gen kernel compiles npu demo tiled matmul source | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_npu_demo_tiled_matmul_source`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles npu demo tiled matmul source”场景。 | `test_gen_kernel_compiles_npu_demo_tiled_matmul_source` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-041 | pass 改写 | gen kernel emits npu demo memory pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_npu_demo_memory_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits npu demo memory pipeline”场景。 | `test_gen_kernel_emits_npu_demo_memory_pipeline` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-042 | 边界/异常 | gen kernel rejects npu demo body level kernel with unknown body op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op`。 | “gen kernel rejects npu demo body level kernel with unknown body op”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-043 | 边界/异常 | gen kernel rejects npu demo body level kernel with nonempty body | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body`。 | “gen kernel rejects npu demo body level kernel with nonempty body”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-044 | pass 改写 | gen kernel black box lowered add and npu demo contracts | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel black box lowered add and npu demo contracts”场景。 | `test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-045 | pass 改写 | gen kernel compiles and runs lowered NN add variants on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles and runs lowered NN add variants on cpu”场景。 | `test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-046 | pass 改写 | gen kernel emits tile codegen single function tile loop | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_tile_codegen_single_function_tile_loop`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits tile codegen single function tile loop”场景。 | `test_gen_kernel_emits_tile_codegen_single_function_tile_loop` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-047 | 边界/异常 | gen kernel rejects tile codegen missing tuner param | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_missing_tuner_param`。 | “gen kernel rejects tile codegen missing tuner param”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_missing_tuner_param` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-048 | 边界/异常 | gen kernel rejects tile codegen missing loop | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_missing_loop`。 | “gen kernel rejects tile codegen missing loop”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_missing_loop` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-049 | 边界/异常 | gen kernel rejects tile codegen with helper call | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_with_helper_call`。 | “gen kernel rejects tile codegen with helper call”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_with_helper_call` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-050 | 边界/异常 | gen kernel rejects legacy split tuner param contract | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_legacy_split_tuner_param_contract`。 | “gen kernel rejects legacy split tuner param contract”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_legacy_split_tuner_param_contract` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-051 | pass 改写 | gen kernel emits tile elewise cpu source for elementwise and broadcast | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits tile elewise cpu source for elementwise and broadcast”场景。 | `test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-052 | 生成/编译 | gen kernel emits npu demo launch wrapper and barrier body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo launch wrapper and barrier body”场景。 | `test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-053 | 生成/编译 | gen kernel compiles npu demo launch wrapper and barrier body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo launch wrapper and barrier body”场景。 | `test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-054 | 生成/编译 | gen kernel emits npu demo cost functions for compute and memory | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo cost functions for compute and memory”场景。 | `test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-055 | 生成/编译 | gen kernel compiles npu demo cost function module | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_cost_function_module`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo cost function module”场景。 | `test_gen_kernel_compiles_npu_demo_cost_function_module` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-056 | pass 改写 | gen kernel compiles outlined npu demo launch module | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_outlined_npu_demo_launch_module`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles outlined npu demo launch module”场景。 | `test_gen_kernel_compiles_outlined_npu_demo_launch_module` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-057 | 生成/编译 | gen kernel npu demo add barrier runtime smoke | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_npu_demo_add_barrier_runtime_smoke`。 | 生成源码、IR 文本或编译结果体现“gen kernel npu demo add barrier runtime smoke”场景。 | `test_gen_kernel_npu_demo_add_barrier_runtime_smoke` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-058 | 边界/异常 | gen kernel rejects npu demo barrier wrapper missing body symbol | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol`。 | “gen kernel rejects npu demo barrier wrapper missing body symbol”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-059 | 边界/异常 | gen kernel rejects npu demo barrier fail fast boundaries | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries`。 | “gen kernel rejects npu demo barrier fail fast boundaries”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-060 | 公开入口 | DSL package public exports | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_package_public_exports`。 | 公开入口在“DSL package public exports”场景下可导入、构造、注册或按名称发现。 | `test_dsl_package_public_exports` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-061 | 边界/异常 | gen kernel package public exports and legacy rejection | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_package_public_exports_and_legacy_rejection`。 | “gen kernel package public exports and legacy rejection”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_package_public_exports_and_legacy_rejection` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-062 | 公开入口 | MLIR gen package public exports | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_package_public_exports`。 | 公开入口在“MLIR gen package public exports”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_package_public_exports` |
| TC-DSL-GEN-KERNEL-GEN-KERNEL-063 | 边界/异常 | removed legacy DSL facades reject import | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_removed_legacy_dsl_facades_reject_import`。 | “removed legacy DSL facades reject import”场景按公开错误语义失败或被拒绝。 | `test_removed_legacy_dsl_facades_reject_import` |
