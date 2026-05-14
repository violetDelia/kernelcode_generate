# kernel_emitter.md

## 功能简介

- 定义 `KernelEmitter` 的函数级 / module 级源码生成合同。
- 该模块负责：
  - `func.func` 的签名与函数体组织
  - `builtin.module` 的受控 module 组织
  - `target="npu_demo"` 的 wrapper/body 骨架收口

## API 列表

- `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`
- `class KernelEmitter(ctx: EmitCContext, emit_op: Callable[[Operation, EmitCContext], str] = emit_c_op)`
- `KernelEmitter.emit(op_or_func: Operation | func.FuncOp | ModuleOp) -> str`
- `KernelEmitter.emit_include() -> str`
- `KernelEmitter.emit_op(op: Operation) -> str`
- `KernelEmitter.emit_type(attr: Attribute | str) -> str`
- `KernelEmitter.emit_attr(attr: Attribute | str) -> str`
- `KernelEmitter.emit_value(value: SSAValue) -> str`
- `KernelEmitter.emit_func(func_op: func.FuncOp) -> str`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/gen_kernel/kernel_emitter.md`](../../../spec/dsl/gen_kernel/kernel_emitter.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/kernel_emitter.py`](../../../kernel_gen/dsl/gen_kernel/kernel_emitter.py)
- `test`：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- [`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- [`spec/dsl/gen_kernel/emit.md`](../../../spec/dsl/gen_kernel/emit.md)
- [`spec/core/error.md`](../../../spec/core/error.md)：公开错误类型 `KernelCodeError`。
- [`spec/include/npu_demo/npu_demo.md`](../../../spec/include/npu_demo/npu_demo.md)

## 目标

- 让 `KernelEmitter` 成为唯一函数级 emitter。
- 保持公开方法最小集合稳定，其余逻辑留在内部 helper。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 除 `API 列表` 列出的公开方法外，其余函数 / 方法都属于内部实现细节。
- launch wrapper 识别、tile contract fail-fast、默认 return 收尾等逻辑不得作为公开 API 暴露。
- 生成源码签名中所有 `Memory` 参数统一使用非 `const` 引用；不得再按读写语义扫描 IR 并拆分 `const Memory&` / `Memory&` 两套形态。
- `NnMemoryType` 参数携带 `template_name` 时，`KernelEmitter` 必须按函数签名首次出现顺序生成 `template <typename T1, ...>`，并在 wrapper、device body 与 body-level kernel 签名中输出 `Memory<space, Tn>&`。
- 无 template name 的函数不得输出模板头，继续使用真实 element dtype fallback。
- EmitC / KernelEmitter 不生成 `kg_execute_entry`、concrete template 实例化集合或 dtype dispatcher；这些只属于 execute_engine compile shim。
- `npu_demo` launch wrapper 中的 launch extent 来自 wrapper IR 内独立 `symbol.const`；源码发射必须生成独立 `constexpr S_INT` 名称并把这些名称传入 `npu_demo::launch<...>`，不得直接把 extent 折成模板字面量。
- `tile.analysis` / `tile.tile_exprs` 在 `npu_demo` 发射链路中只视为 IR 分析元数据，不得单独触发 CPU tile codegen 校验；只有真实 `tuner.param : !symbol.int<...>` tile codegen 结构才触发 tile codegen 路径。
- 非公开 helper 必须使用 `_` 前缀，且不得跨文件直接调用。
## API详细说明

### `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`

- api：`class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`
- 参数：
  - `kind`：错误类别；类型 `ErrorKind | str`；无默认值；不允许 `None`；非法值按 [`spec/core/error.md`](../../../spec/core/error.md) 的公开错误合同处理。
  - `module`：错误来源模块；类型 `ErrorModule | str`；无默认值；不允许 `None`；非法值按 [`spec/core/error.md`](../../../spec/core/error.md) 的公开错误合同处理。
  - `message`：稳定错误消息；类型 `str`；无默认值；不允许空字符串。
- 返回值：`KernelCodeError` 实例。
- 使用示例：

  ```python
  from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

  err = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.CODEGEN, "unsupported kernel op")
  ```
- 功能说明：定义 `KernelEmitter` 失败路径使用的公开错误类型。
- 注意事项：`KernelCodeError` 的定义与构造语义以 [`spec/core/error.md`](../../../spec/core/error.md) 为准；本文件不得新增模块级专属错误类。

### `class KernelEmitter(ctx: EmitCContext, emit_op: Callable[[Operation, EmitCContext], str] = emit_c_op)`

- api：`class KernelEmitter(ctx: EmitCContext, emit_op: Callable[[Operation, EmitCContext], str] = emit_c_op)`
- 参数：
  - `ctx`：公开 `EmitCContext` 上下文，提供源码生成所需的配置、命名状态和 target 选项；调用方必须显式传入。
  - `emit_op`：单个 operation 的源码生成分发函数；默认使用公开 `emit_c_op`。
- 返回值：`KernelEmitter` 实例。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
  from kernel_gen.dsl.gen_kernel.kernel_emitter import KernelEmitter

  emitter = KernelEmitter(EmitCContext())
  ```
- 功能说明：构造函数级 / module 级源码生成器。
- 注意事项：实例内部缓存、状态字典和派生字段不作为外部可变入口；`__init__` 只通过 `KernelEmitter(...)` 构造入口承接，不单列为独立公开 API。

### `KernelEmitter.emit(op_or_func: Operation | func.FuncOp | ModuleOp) -> str`

- api：`KernelEmitter.emit(op_or_func: Operation | func.FuncOp | ModuleOp) -> str`
- 参数：
  - `op_or_func`：待生成源码的 IR 对象；类型 `Operation | func.FuncOp | ModuleOp`；调用方必须显式传入，不允许 `None`。
- 返回值：`str`，生成后的源码文本或源码片段。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
  from kernel_gen.dsl.gen_kernel.kernel_emitter import KernelEmitter

  emitter = KernelEmitter(EmitCContext())
  source = emitter.emit(module_op)
  ```
- 功能说明：按输入类型分发函数级、module 级或单 operation 源码生成。
- 注意事项：只按注册表和公开上下文分发；未注册或不支持的输入必须返回空结果或抛出公开错误。

### `KernelEmitter.emit_include() -> str`

- api：`KernelEmitter.emit_include() -> str`
- 参数：无。
- 返回值：`str`，当前 target 需要的 C/C++ include 文本。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
  from kernel_gen.dsl.gen_kernel.kernel_emitter import KernelEmitter

  emitter = KernelEmitter(EmitCContext())
  include_text = emitter.emit_include()
  ```
- 功能说明：生成当前 target 对应的 include 区块。
- 注意事项：include 集合由 `EmitCContext` 的公开配置决定；不得在调用侧绕过 `KernelEmitter` 直接拼接 target 专属 include。

### `KernelEmitter.emit_op(op: Operation) -> str`

- api：`KernelEmitter.emit_op(op: Operation) -> str`
- 参数：
  - `op`：待生成源码片段的 IR operation；类型 `Operation`；调用方必须显式传入，不允许 `None`。
- 返回值：`str`，单个 operation 对应的源码片段。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
  from kernel_gen.dsl.gen_kernel.kernel_emitter import KernelEmitter

  emitter = KernelEmitter(EmitCContext())
  op_text = emitter.emit_op(op)
  ```
- 功能说明：生成单个 IR operation 的源码片段。
- 注意事项：只按公开 emit registry 与上下文分发；未注册或不支持的 operation 必须返回空结果或抛出公开错误。

### `KernelEmitter.emit_type(attr: Attribute | str) -> str`

- api：`KernelEmitter.emit_type(attr: Attribute | str) -> str`
- 参数：
  - `attr`：待生成 C/C++ 类型文本的 IR type attribute 或已归一文本；类型 `Attribute | str`；调用方必须显式传入。
- 返回值：`str`，C/C++ 类型文本。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import f32

  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
  from kernel_gen.dsl.gen_kernel.kernel_emitter import KernelEmitter

  emitter = KernelEmitter(EmitCContext())
  type_text = emitter.emit_type(f32)
  ```
- 功能说明：生成 IR type attribute 对应的 C/C++ 类型文本。
- 注意事项：只按公开 type emit registry 与上下文分发；未注册类型必须返回空结果或抛出公开错误。

### `KernelEmitter.emit_attr(attr: Attribute | str) -> str`

- api：`KernelEmitter.emit_attr(attr: Attribute | str) -> str`
- 参数：
  - `attr`：待生成源码文本的 IR attribute 或已归一文本；类型 `Attribute | str`；调用方必须显式传入。
- 返回值：`str`，attribute 对应的源码文本。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import StringAttr

  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
  from kernel_gen.dsl.gen_kernel.kernel_emitter import KernelEmitter

  emitter = KernelEmitter(EmitCContext())
  attr_text = emitter.emit_attr(StringAttr("kernel"))
  ```
- 功能说明：生成 IR attribute 对应的源码文本。
- 注意事项：只按公开 attr emit registry 与上下文分发；未注册 attribute 必须返回空结果或抛出公开错误。

### `KernelEmitter.emit_value(value: SSAValue) -> str`

- api：`KernelEmitter.emit_value(value: SSAValue) -> str`
- 参数：
  - `value`：需要生成源码名称的 SSA value；类型 `SSAValue`；调用方必须显式传入，不允许 `None`。
- 返回值：`str`，SSA value 在源码中的稳定名称。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
  from kernel_gen.dsl.gen_kernel.kernel_emitter import KernelEmitter

  emitter = KernelEmitter(EmitCContext())
  value_name = emitter.emit_value(value)
  ```
- 功能说明：生成 SSA value 在源码中的稳定名称。
- 注意事项：命名与缓存状态由 `EmitCContext` 承载；调用侧不得直接访问 emitter 内部缓存。

### `KernelEmitter.emit_func(func_op: func.FuncOp) -> str`

- api：`KernelEmitter.emit_func(func_op: func.FuncOp) -> str`
- 参数：
  - `func_op`：待生成源码的函数级 IR operation；类型 `func.FuncOp`；调用方必须显式传入，不允许 `None`。
- 返回值：`str`，函数源码文本。
- 使用示例：

  ```python
  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
  from kernel_gen.dsl.gen_kernel.kernel_emitter import KernelEmitter

  emitter = KernelEmitter(EmitCContext())
  source = emitter.emit_func(func_op)
  ```
- 功能说明：生成 `func.func` 对应的函数源码文本。
- 注意事项：函数级生成只处理单个 `func.FuncOp`；module include、跨函数组织和 wrapper 选择由 `emit(...)` 承接。

## 测试

- 测试文件：`test/dsl/gen_kernel/test_gen_kernel.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py`

### 测试目标

- 验证 `spec/dsl/gen_kernel/kernel_emitter.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-001 | 生成/编译 | gen kernel dump dir writes source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_dump_dir_writes_source`。 | 生成源码、IR 文本或编译结果体现“gen kernel dump dir writes source”场景。 | `test_gen_kernel_dump_dir_writes_source` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-002 | 公开入口 | gen kernel public modules exist and old legacy loader path is gone | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone`。 | 公开入口在“gen kernel public modules exist and old legacy loader path is gone”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-003 | pass 改写 | tile gen kernel paths use kernel gen tile modules | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_gen_kernel_paths_use_kernel_gen_tile_modules`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile gen kernel paths use kernel gen tile modules”场景。 | `test_tile_gen_kernel_paths_use_kernel_gen_tile_modules` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-004 | 生成/编译 | gen kernel local compile helpers delegate local compile runner | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_local_compile_helpers_delegate_local_compile_runner`。 | 生成源码、IR 文本或编译结果体现“gen kernel local compile helpers delegate local compile runner”场景。 | `test_gen_kernel_local_compile_helpers_delegate_local_compile_runner` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-005 | 生成/编译 | gen kernel returns target source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_returns_target_source`。 | 生成源码、IR 文本或编译结果体现“gen kernel returns target source”场景。 | `test_gen_kernel_returns_target_source` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-006 | 边界/异常 | gen kernel converts emit error to gen kernel error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_converts_emit_error_to_gen_kernel_error`。 | “gen kernel converts emit error to gen kernel error”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_converts_emit_error_to_gen_kernel_error` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-007 | 生成/编译 | gen kernel entry module hides internal emitter entry | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_entry_module_hides_internal_emitter_entry`。 | 生成源码、IR 文本或编译结果体现“gen kernel entry module hides internal emitter entry”场景。 | `test_gen_kernel_entry_module_hides_internal_emitter_entry` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-008 | 公开入口 | gen kernel is the package public entry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_is_the_package_public_entry`。 | 公开入口在“gen kernel is the package public entry”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_is_the_package_public_entry` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-009 | 公开入口 | DSL gen kernel matches public MLIR gen plus gen kernel path | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path`。 | 公开入口在“DSL gen kernel matches public MLIR gen plus gen kernel path”场景下可导入、构造、注册或按名称发现。 | `test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-010 | 生成/编译 | gen kernel has no legacy double interface | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_has_no_legacy_double_interface`。 | 生成源码、IR 文本或编译结果体现“gen kernel has no legacy double interface”场景。 | `test_gen_kernel_has_no_legacy_double_interface` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-011 | 生成/编译 | gen kernel delegates single op input to emit c | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_delegates_single_op_input_to_emit_c`。 | 生成源码、IR 文本或编译结果体现“gen kernel delegates single op input to emit c”场景。 | `test_gen_kernel_delegates_single_op_input_to_emit_c` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-012 | 生成/编译 | gen kernel uses mutable memory inputs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_uses_mutable_memory_inputs`。 | 生成源码、IR 文本或编译结果体现“gen kernel uses mutable memory inputs”场景。 | `test_gen_kernel_uses_mutable_memory_inputs` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-013 | 生成/编译 | gen kernel accepts rewritten single output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_single_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten single output function”场景。 | `test_gen_kernel_accepts_rewritten_single_output_function` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-014 | 生成/编译 | gen kernel rewritten deslice memory result uses front out param | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param`。 | 生成源码、IR 文本或编译结果体现“gen kernel rewritten deslice memory result uses front out param”场景。 | `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-015 | 生成/编译 | gen kernel uses default arg names when missing attrs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_uses_default_arg_names_when_missing_attrs`。 | 生成源码、IR 文本或编译结果体现“gen kernel uses default arg names when missing attrs”场景。 | `test_gen_kernel_uses_default_arg_names_when_missing_attrs` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-016 | 生成/编译 | gen kernel emits ops in order | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_ops_in_order`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits ops in order”场景。 | `test_gen_kernel_emits_ops_in_order` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-017 | 生成/编译 | gen kernel delegates to emit c for non return ops | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_delegates_to_emit_c_for_non_return_ops`。 | 生成源码、IR 文本或编译结果体现“gen kernel delegates to emit c for non return ops”场景。 | `test_gen_kernel_delegates_to_emit_c_for_non_return_ops` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-018 | 生成/编译 | gen kernel handles func return and out binding in main flow | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_handles_func_return_and_out_binding_in_main_flow`。 | 生成源码、IR 文本或编译结果体现“gen kernel handles func return and out binding in main flow”场景。 | `test_gen_kernel_handles_func_return_and_out_binding_in_main_flow` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-019 | 边界/异常 | kernel emitter public dispatch error boundaries | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_emitter_public_dispatch_error_boundaries`。 | “kernel emitter public dispatch error boundaries”场景按公开错误语义失败或被拒绝。 | `test_kernel_emitter_public_dispatch_error_boundaries` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-020 | 公开入口 | kernel emitter public include and type dispatch | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_kernel_emitter_public_include_and_type_dispatch`。 | 公开入口在“kernel emitter public include and type dispatch”场景下可导入、构造、注册或按名称发现。 | `test_kernel_emitter_public_include_and_type_dispatch` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-021 | 生成/编译 | gen kernel assembles loop body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_assembles_loop_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel assembles loop body”场景。 | `test_gen_kernel_assembles_loop_body` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-022 | 边界/异常 | gen kernel propagates emit error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_propagates_emit_error`。 | “gen kernel propagates emit error”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_propagates_emit_error` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-023 | 边界/异常 | gen kernel rejects unsupported return form | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_unsupported_return_form`。 | “gen kernel rejects unsupported return form”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_unsupported_return_form` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-024 | 生成/编译 | gen kernel supports float32 scalar and memory | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_supports_float32_scalar_and_memory`。 | 生成源码、IR 文本或编译结果体现“gen kernel supports float32 scalar and memory”场景。 | `test_gen_kernel_supports_float32_scalar_and_memory` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-025 | 生成/编译 | gen kernel preserves function and arg names | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_preserves_function_and_arg_names`。 | 生成源码、IR 文本或编译结果体现“gen kernel preserves function and arg names”场景。 | `test_gen_kernel_preserves_function_and_arg_names` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-026 | 生成/编译 | gen kernel supports symbol scalar return | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_supports_symbol_scalar_return`。 | 生成源码、IR 文本或编译结果体现“gen kernel supports symbol scalar return”场景。 | `test_gen_kernel_supports_symbol_scalar_return` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-027 | 边界/异常 | gen kernel rejects symbol scalar return on non cpu | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu`。 | “gen kernel rejects symbol scalar return on non cpu”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-028 | pass 改写 | gen kernel supports lowered NN add memory memory on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory memory on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-029 | pass 改写 | gen kernel supports lowered NN add memory const on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory const on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-030 | pass 改写 | gen kernel supports lowered NN add memory symbol on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory symbol on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-031 | 生成/编译 | gen kernel accepts rewritten single output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_single_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten single output function”场景。 | `test_gen_kernel_accepts_rewritten_single_output_function` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-032 | 生成/编译 | gen kernel accepts rewritten mixed output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_mixed_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten mixed output function”场景。 | `test_gen_kernel_accepts_rewritten_mixed_output_function` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-033 | pass 改写 | rewritten pipeline has no memory return abi left | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_rewritten_pipeline_has_no_memory_return_abi_left`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“rewritten pipeline has no memory return abi left”场景。 | `test_rewritten_pipeline_has_no_memory_return_abi_left` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-034 | 边界/异常 | gen kernel rejects lowered IR without buffer results to out params | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params`。 | “gen kernel rejects lowered IR without buffer results to out params”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-035 | 边界/异常 | rewritten pipeline fails on half rewritten IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_rewritten_pipeline_fails_on_half_rewritten_ir`。 | “rewritten pipeline fails on half rewritten IR”场景按公开错误语义失败或被拒绝。 | `test_rewritten_pipeline_fails_on_half_rewritten_ir` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-036 | 生成/编译 | gen kernel emits npu demo body level kernel | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_body_level_kernel`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo body level kernel”场景。 | `test_gen_kernel_emits_npu_demo_body_level_kernel` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-037 | 生成/编译 | gen kernel emits npu demo kernel binary signature out first | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo kernel binary signature out first”场景。 | `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-038 | 生成/编译 | gen kernel emits npu demo DMA alloc module | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_dma_alloc_module`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo DMA alloc module”场景。 | `test_gen_kernel_emits_npu_demo_dma_alloc_module` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-039 | 生成/编译 | gen kernel compiles npu demo source with single include | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_source_with_single_include`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo source with single include”场景。 | `test_gen_kernel_compiles_npu_demo_source_with_single_include` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-040 | pass 改写 | gen kernel compiles npu demo tiled matmul source | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_npu_demo_tiled_matmul_source`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles npu demo tiled matmul source”场景。 | `test_gen_kernel_compiles_npu_demo_tiled_matmul_source` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-041 | pass 改写 | gen kernel emits npu demo memory pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_npu_demo_memory_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits npu demo memory pipeline”场景。 | `test_gen_kernel_emits_npu_demo_memory_pipeline` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-042 | 边界/异常 | gen kernel rejects npu demo body level kernel with unknown body op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op`。 | “gen kernel rejects npu demo body level kernel with unknown body op”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-043 | 边界/异常 | gen kernel rejects npu demo body level kernel with nonempty body | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body`。 | “gen kernel rejects npu demo body level kernel with nonempty body”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-044 | pass 改写 | gen kernel black box lowered add and npu demo contracts | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel black box lowered add and npu demo contracts”场景。 | `test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-045 | pass 改写 | gen kernel compiles and runs lowered NN add variants on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles and runs lowered NN add variants on cpu”场景。 | `test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-046 | pass 改写 | gen kernel emits tile codegen single function tile loop | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_tile_codegen_single_function_tile_loop`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits tile codegen single function tile loop”场景。 | `test_gen_kernel_emits_tile_codegen_single_function_tile_loop` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-047 | 边界/异常 | gen kernel rejects tile codegen missing tuner param | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_missing_tuner_param`。 | “gen kernel rejects tile codegen missing tuner param”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_missing_tuner_param` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-048 | 边界/异常 | gen kernel rejects tile codegen missing loop | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_missing_loop`。 | “gen kernel rejects tile codegen missing loop”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_missing_loop` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-049 | 边界/异常 | gen kernel rejects tile codegen with helper call | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_with_helper_call`。 | “gen kernel rejects tile codegen with helper call”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_with_helper_call` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-050 | 边界/异常 | gen kernel rejects legacy split tuner param contract | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_legacy_split_tuner_param_contract`。 | “gen kernel rejects legacy split tuner param contract”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_legacy_split_tuner_param_contract` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-051 | pass 改写 | gen kernel emits tile elewise cpu source for elementwise and broadcast | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits tile elewise cpu source for elementwise and broadcast”场景。 | `test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-052 | 生成/编译 | gen kernel emits npu demo launch wrapper and barrier body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo launch wrapper and barrier body”场景。 | `test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-053 | 生成/编译 | gen kernel compiles npu demo launch wrapper and barrier body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo launch wrapper and barrier body”场景。 | `test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-054 | 生成/编译 | gen kernel emits npu demo cost functions for compute and memory | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo cost functions for compute and memory”场景。 | `test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-055 | 生成/编译 | gen kernel compiles npu demo cost function module | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_cost_function_module`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo cost function module”场景。 | `test_gen_kernel_compiles_npu_demo_cost_function_module` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-056 | pass 改写 | gen kernel compiles outlined npu demo launch module | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_outlined_npu_demo_launch_module`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles outlined npu demo launch module”场景。 | `test_gen_kernel_compiles_outlined_npu_demo_launch_module` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-057 | 生成/编译 | gen kernel npu demo add barrier runtime smoke | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_npu_demo_add_barrier_runtime_smoke`。 | 生成源码、IR 文本或编译结果体现“gen kernel npu demo add barrier runtime smoke”场景。 | `test_gen_kernel_npu_demo_add_barrier_runtime_smoke` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-058 | 边界/异常 | gen kernel rejects npu demo barrier wrapper missing body symbol | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol`。 | “gen kernel rejects npu demo barrier wrapper missing body symbol”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-059 | 边界/异常 | gen kernel rejects npu demo barrier fail fast boundaries | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries`。 | “gen kernel rejects npu demo barrier fail fast boundaries”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-060 | 边界/异常 | gen kernel rejects tile codegen public malformed matrix | 准备包含 legacy bridge、malformed tuner.param 或非 CPU target 的公开 IR 输入。 | 运行 `test_gen_kernel_rejects_tile_codegen_public_malformed_matrix`。 | tile codegen 公开合同外输入均按 `KernelCodeError` fail-fast，不静默生成源码。 | `test_gen_kernel_rejects_tile_codegen_public_malformed_matrix` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-061 | 生成/编译 | gen kernel emits npu demo launch wrapper with symbol args | 准备带 trailing `!symbol.int` 参数的 `npu_demo` body/wrapper module。 | 运行 `test_gen_kernel_emits_npu_demo_launch_wrapper_with_symbol_args`。 | body 使用 `S_INT` 参数，wrapper 使用公开签名类型，并把符号参数透传到 `npu_demo::launch`。 | `test_gen_kernel_emits_npu_demo_launch_wrapper_with_symbol_args` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-062 | 边界/异常 | gen kernel rejects npu demo body level signature boundaries | 准备不满足 `ctx + Memory -> Memory` 的 `npu_demo` 单函数输入。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_signature_boundaries`。 | 非 ctx 首参、非 Memory 源参数或 element type 不匹配均不会进入 body-level kernel 特化，并按公开 memory-return 拒绝语义失败。 | `test_gen_kernel_rejects_npu_demo_body_level_signature_boundaries` |
| TC-DSL-GEN-KERNEL-KERNEL-EMITTER-063 | 边界/异常 | gen kernel handles npu demo plain module public boundaries | 准备 `npu_demo` 单函数 plain module、helper-only module、缺 return module 与缺 body launch module。 | 运行 `test_gen_kernel_handles_npu_demo_plain_module_public_boundaries`。 | 普通可发射函数成功；helper-only、缺 return 与缺 body launch 均按公开错误语义 fail-fast。 | `test_gen_kernel_handles_npu_demo_plain_module_public_boundaries` |
