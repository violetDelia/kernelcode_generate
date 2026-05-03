# attach_arch_information.md

## 功能简介

- 定义 `attach-arch-information` pass 的公开合同：从 target registry 读取 launch extent 与 `shared_memory_size`，并把 `launch_block / launch_thread / launch_subthread / shared_memory_size` 写回入口 `func.func`。
- 该 pass 不承担 outline 逻辑，只负责把 IR 级 launch 信息补齐到后续 `outline-device-kernel` 可消费的状态。
- 当前文件只公开 `AttachArchInformationPass` 的构造、registry 构造与 `apply(ctx, module)` 入口；当前文件内校验、属性规整和错误前缀拼接 helper 若存在，均不属于公开 API。
- 不再提供单 pass `run(module)` 兼容入口；实现与测试都必须走 xdsl `ModulePass.apply(ctx, module)`。

## API 列表

- `class AttachArchInformationPass(target: str = "npu_demo")`
- `AttachArchInformationPass.from_options(options: dict[str, str]) -> AttachArchInformationPass`
- `AttachArchInformationPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/attach_arch_information.md`](../../../spec/pass/attach_arch_information.md)
- `功能实现`：[`kernel_gen/passes/attach_arch_information.py`](../../../kernel_gen/passes/attach_arch_information.py)
- `test`：[`test/passes/test_attach_arch_information.py`](../../../test/passes/test_attach_arch_information.py)

## 依赖

- Pass 管理与执行：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- pass 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- pass 公共错误：[`kernel_gen/passes/common.py`](../../../kernel_gen/passes/common.py)
- target 注册中心：[`spec/target/registry.md`](../../../spec/target/registry.md)
- `func.func` / `launch_*` IR 语义：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)

## 术语

- `entry func`：module 中唯一的非 declaration `func.func`，作为 attach 的默认入口。
- `launch extent`：从 target registry 读取的 `block_num / thread_num / subthread_num / sm_memory_size` 四层 launch 数值。

## 目标

- 为入口函数补齐 `launch_block / launch_thread / launch_subthread / shared_memory_size`。
- 让 `npu_demo` 的 launch extent 统一从 `kernel_gen/target/targets/npu_demo.txt` 读取。
- 若入口已存在 launch 属性，则必须与 target registry 的 extent 完全一致。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 只接受 `builtin.module` 输入。
- 只对 module 中唯一的 non-declaration `func.func` 生效；缺失或多个时必须显式失败，不得静默选择首个函数。
- 四项 launch 属性必须同时存在；部分存在时必须显式失败。
- `launch_block / launch_thread / launch_subthread / shared_memory_size` 仅写回 `func.func attributes`，不扩展 `arch.launch` 形状。
- 当前文件的公开 API 只有 `AttachArchInformationPass`；不得跨文件调用当前文件模块级 helper、常量或错误文本规整步骤。
- `AttachArchInformationPass.apply(ctx, module)` 是面向业务调用方、pytest、registry 与 `PassManager` 的唯一稳定执行入口。
- `apply(ctx, module)` 即使暂时不消费 `ctx` 里的业务信息，也不得通过 `del ctx` 或其他显式丢弃语句把该协议形参写成“已废弃入口”。
- 所有预期失败统一抛出 [`KernelCodeError`](../../../kernel_gen/passes/common.py)，错误消息仍以 `AttachArchInformationError:` 前缀开头，供测试做稳定匹配。
## API详细说明

### `class AttachArchInformationPass(target: str = "npu_demo")`

- api：`class AttachArchInformationPass(target: str = "npu_demo")`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；默认值 `"npu_demo"`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`AttachArchInformationPass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.attach_arch_information import AttachArchInformationPass

  pass_obj = AttachArchInformationPass(target="npu_demo")
  ```
- 功能说明：按目标名构造 attach-arch-information pass 实例。
- 注意事项：`target` 必须是已注册 target；不得恢复 `run(module)` 或其他返回式兼容入口；实例内部校验、属性规整和错误前缀拼接 helper 不属于公开 API。

### `AttachArchInformationPass.from_options(options: dict[str, str]) -> AttachArchInformationPass`

- api：`AttachArchInformationPass.from_options(options: dict[str, str]) -> AttachArchInformationPass`
- 参数：
  - `options`：pass registry 传入的字符串选项；类型 `dict[str, str]`；无默认值，调用方必须显式提供；支持 `target` 键，缺失时使用 `"npu_demo"`。
- 返回值：`AttachArchInformationPass`。
- 使用示例：

  ```python
  from kernel_gen.passes.attach_arch_information import AttachArchInformationPass

  pass_obj = AttachArchInformationPass.from_options({"target": "npu_demo"})
  ```
- 功能说明：通过 registry options 构造 pass 实例。
- 注意事项：该入口用于 registry / `PassManager` 构造路径；非法选项必须按公开错误语义处理。

### `AttachArchInformationPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`AttachArchInformationPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from xdsl.context import Context

  from kernel_gen.passes.attach_arch_information import AttachArchInformationPass

  AttachArchInformationPass(target="npu_demo").apply(Context(), module)
  ```
- 功能说明：对模块执行 `AttachArchInformationPass` pass。
- 注意事项：对业务调用方、pytest、registry 与 `PassManager` 暴露稳定执行入口；原地写回入口 `func.func` 的 launch 属性并返回 `None`；只接受 `builtin.module` 输入；即使暂时不消费 `ctx` 里的业务信息，也不得通过 `del ctx` 或其他显式丢弃语句把该协议形参写成“已废弃入口”。

## 测试

- 测试文件：
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_attach_arch_information.py`
  - `test/passes/test_registry.py`
- 执行命令：`pytest -q test/passes/test_attach_arch_information.py test/passes/test_registry.py -k 'attach_arch_information or attach-arch-information'`

### 测试目标

- 验证 `spec/pass/attach_arch_information.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-ATTACH-ARCH-INFORMATION-001 | pass 改写 | npu demo lowering pipeline builds pass manager | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_npu_demo_lowering_pipeline_builds_pass_manager`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“npu demo lowering pipeline builds pass manager”场景。 | `test_npu_demo_lowering_pipeline_builds_pass_manager` |
| TC-PASS-ATTACH-ARCH-INFORMATION-002 | pass 改写 | npu demo lowering pipeline pass order | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_npu_demo_lowering_pipeline_pass_order`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“npu demo lowering pipeline pass order”场景。 | `test_npu_demo_lowering_pipeline_pass_order` |
| TC-PASS-ATTACH-ARCH-INFORMATION-003 | 边界/异常 | npu demo lowering pipeline rejects unknown option | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_npu_demo_lowering_pipeline_rejects_unknown_option`。 | “npu demo lowering pipeline rejects unknown option”场景按公开错误语义失败或被拒绝。 | `test_npu_demo_lowering_pipeline_rejects_unknown_option` |
| TC-PASS-ATTACH-ARCH-INFORMATION-004 | 公开入口 | npu demo lowering pipeline supports kernel contract style public chain | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain`。 | 公开入口在“npu demo lowering pipeline supports kernel contract style public chain”场景下可导入、构造、注册或按名称发现。 | `test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain` |
| TC-PASS-ATTACH-ARCH-INFORMATION-005 | 公开入口 | public import path exposes attach arch information pass only | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_public_import_path_exposes_attach_arch_information_pass_only`。 | 公开入口在“public import path exposes attach arch information pass only”场景下可导入、构造、注册或按名称发现。 | `test_public_import_path_exposes_attach_arch_information_pass_only` |
| TC-PASS-ATTACH-ARCH-INFORMATION-006 | 公开入口 | attach arch information writes registry launch extents | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_attach_arch_information_writes_registry_launch_extents`。 | 公开入口在“attach arch information writes registry launch extents”场景下可导入、构造、注册或按名称发现。 | `test_attach_arch_information_writes_registry_launch_extents` |
| TC-PASS-ATTACH-ARCH-INFORMATION-007 | 边界/异常 | attach arch information rejects partial launch attrs | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_attach_arch_information_rejects_partial_launch_attrs`。 | “attach arch information rejects partial launch attrs”场景按公开错误语义失败或被拒绝。 | `test_attach_arch_information_rejects_partial_launch_attrs` |
| TC-PASS-ATTACH-ARCH-INFORMATION-008 | 边界/异常 | attach arch information rejects multiple entry funcs | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_attach_arch_information_rejects_multiple_entry_funcs`。 | “attach arch information rejects multiple entry funcs”场景按公开错误语义失败或被拒绝。 | `test_attach_arch_information_rejects_multiple_entry_funcs` |
| TC-PASS-ATTACH-ARCH-INFORMATION-009 | 边界/异常 | register pass duplicate fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_register_pass_duplicate_fails`。 | “register pass duplicate fails”场景按公开错误语义失败或被拒绝。 | `test_register_pass_duplicate_fails` |
| TC-PASS-ATTACH-ARCH-INFORMATION-010 | 边界/异常 | register pipeline duplicate fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_register_pipeline_duplicate_fails`。 | “register pipeline duplicate fails”场景按公开错误语义失败或被拒绝。 | `test_register_pipeline_duplicate_fails` |
| TC-PASS-ATTACH-ARCH-INFORMATION-011 | 公开入口 | build registered pass unknown | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_unknown`。 | 公开入口在“build registered pass unknown”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_unknown` |
| TC-PASS-ATTACH-ARCH-INFORMATION-012 | 公开入口 | build registered pass not constructible | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_not_constructible`。 | 公开入口在“build registered pass not constructible”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_not_constructible` |
| TC-PASS-ATTACH-ARCH-INFORMATION-013 | 公开入口 | build registered pipeline unknown | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pipeline_unknown`。 | 公开入口在“build registered pipeline unknown”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pipeline_unknown` |
| TC-PASS-ATTACH-ARCH-INFORMATION-014 | 公开入口 | build registered pipeline must return pass manager | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pipeline_must_return_pass_manager`。 | 公开入口在“build registered pipeline must return pass manager”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pipeline_must_return_pass_manager` |
| TC-PASS-ATTACH-ARCH-INFORMATION-015 | 公开入口 | list registered are sorted | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_list_registered_are_sorted`。 | 公开入口在“list registered are sorted”场景下可导入、构造、注册或按名称发现。 | `test_list_registered_are_sorted` |
| TC-PASS-ATTACH-ARCH-INFORMATION-016 | 公开入口 | build registered outline device kernel pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_outline_device_kernel_pass`。 | 公开入口在“build registered outline device kernel pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_outline_device_kernel_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-017 | 公开入口 | build registered tile analysis pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_tile_analysis_pass`。 | 公开入口在“build registered tile analysis pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_tile_analysis_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-018 | 公开入口 | build registered tile reduce pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_tile_reduce_pass`。 | 公开入口在“build registered tile reduce pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_tile_reduce_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-019 | 公开入口 | build registered tile elewise pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_tile_elewise_pass`。 | 公开入口在“build registered tile elewise pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_tile_elewise_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-020 | 公开入口 | registry surviving public paths match consumer matrix | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_registry_surviving_public_paths_match_consumer_matrix`。 | 公开入口在“registry surviving public paths match consumer matrix”场景下可导入、构造、注册或按名称发现。 | `test_registry_surviving_public_paths_match_consumer_matrix` |
| TC-PASS-ATTACH-ARCH-INFORMATION-021 | 公开入口 | build registered NN lowering pass is module pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_nn_lowering_pass_is_module_pass`。 | 公开入口在“build registered NN lowering pass is module pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_nn_lowering_pass_is_module_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-022 | 公开入口 | build registered launch kernel cost func pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_launch_kernel_cost_func_pass`。 | 公开入口在“build registered launch kernel cost func pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_launch_kernel_cost_func_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-023 | 公开入口 | build registered launch kernel cost func default kind | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_launch_kernel_cost_func_default_kind`。 | 公开入口在“build registered launch kernel cost func default kind”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_launch_kernel_cost_func_default_kind` |
| TC-PASS-ATTACH-ARCH-INFORMATION-024 | 边界/异常 | build registered launch kernel cost func rejects invalid kind | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_launch_kernel_cost_func_rejects_invalid_kind`。 | “build registered launch kernel cost func rejects invalid kind”场景按公开错误语义失败或被拒绝。 | `test_build_registered_launch_kernel_cost_func_rejects_invalid_kind` |
| TC-PASS-ATTACH-ARCH-INFORMATION-025 | 公开入口 | build registered module pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_module_pass`。 | 公开入口在“build registered module pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_module_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-026 | 公开入口 | build registered module pass with options | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_module_pass_with_options`。 | 公开入口在“build registered module pass with options”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_module_pass_with_options` |
| TC-PASS-ATTACH-ARCH-INFORMATION-027 | 公开入口 | build registered buffer results to out params pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_buffer_results_to_out_params_pass`。 | 公开入口在“build registered buffer results to out params pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_buffer_results_to_out_params_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-028 | 公开入口 | build registered decompass pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_decompass_pass`。 | 公开入口在“build registered decompass pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_decompass_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-029 | 公开入口 | build registered inline pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_inline_pass`。 | 公开入口在“build registered inline pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_inline_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-030 | 公开入口 | build registered pass accepts universal fold option | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_accepts_universal_fold_option`。 | 公开入口在“build registered pass accepts universal fold option”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_accepts_universal_fold_option` |
| TC-PASS-ATTACH-ARCH-INFORMATION-031 | 边界/异常 | build registered pass rejects invalid fold option | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_pass_rejects_invalid_fold_option`。 | “build registered pass rejects invalid fold option”场景按公开错误语义失败或被拒绝。 | `test_build_registered_pass_rejects_invalid_fold_option` |
| TC-PASS-ATTACH-ARCH-INFORMATION-032 | 公开入口 | build registered attach arch information pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_attach_arch_information_pass`。 | 公开入口在“build registered attach arch information pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_attach_arch_information_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-033 | 边界/异常 | registry old lowering paths fail fast | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_registry_old_lowering_paths_fail_fast`。 | “registry old lowering paths fail fast”场景按公开错误语义失败或被拒绝。 | `test_registry_old_lowering_paths_fail_fast` |
| TC-PASS-ATTACH-ARCH-INFORMATION-034 | 边界/异常 | registry retired analysis pass name fails fast | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_registry_retired_analysis_pass_name_fails_fast`。 | “registry retired analysis pass name fails fast”场景按公开错误语义失败或被拒绝。 | `test_registry_retired_analysis_pass_name_fails_fast` |
| TC-PASS-ATTACH-ARCH-INFORMATION-035 | 公开入口 | build registered symbol buffer hoist pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_symbol_buffer_hoist_pass`。 | 公开入口在“build registered symbol buffer hoist pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_symbol_buffer_hoist_pass` |
| TC-PASS-ATTACH-ARCH-INFORMATION-036 | 公开入口 | build registered npu demo lowering pipeline | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_npu_demo_lowering_pipeline`。 | 公开入口在“build registered npu demo lowering pipeline”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_npu_demo_lowering_pipeline` |
| TC-PASS-ATTACH-ARCH-INFORMATION-037 | pass 改写 | load builtin passes is idempotent | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_load_builtin_passes_is_idempotent`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“load builtin passes is idempotent”场景。 | `test_load_builtin_passes_is_idempotent` |
| TC-PASS-ATTACH-ARCH-INFORMATION-038 | pass 改写 | load builtin passes after reload registers default lowering | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_load_builtin_passes_after_reload_registers_default_lowering`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“load builtin passes after reload registers default lowering”场景。 | `test_load_builtin_passes_after_reload_registers_default_lowering` |
| TC-PASS-ATTACH-ARCH-INFORMATION-039 | 公开入口 | build registered npu demo lowering pipeline with options | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_npu_demo_lowering_pipeline_with_options`。 | 公开入口在“build registered npu demo lowering pipeline with options”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_npu_demo_lowering_pipeline_with_options` |
| TC-PASS-ATTACH-ARCH-INFORMATION-040 | 边界/异常 | build registered npu demo lowering pipeline rejects unknown option | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_npu_demo_lowering_pipeline_rejects_unknown_option`。 | “build registered npu demo lowering pipeline rejects unknown option”场景按公开错误语义失败或被拒绝。 | `test_build_registered_npu_demo_lowering_pipeline_rejects_unknown_option` |
| TC-PASS-ATTACH-ARCH-INFORMATION-041 | 公开入口 | build registered pass with options | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_with_options`。 | 公开入口在“build registered pass with options”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_with_options` |
| TC-PASS-ATTACH-ARCH-INFORMATION-042 | 公开入口 | build registered pass options not supported | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_options_not_supported`。 | 公开入口在“build registered pass options not supported”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_options_not_supported` |
| TC-PASS-ATTACH-ARCH-INFORMATION-043 | 边界/异常 | build registered pass option error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_pass_option_error`。 | “build registered pass option error”场景按公开错误语义失败或被拒绝。 | `test_build_registered_pass_option_error` |
| TC-PASS-ATTACH-ARCH-INFORMATION-044 | 公开入口 | build registered pipeline with options | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pipeline_with_options`。 | 公开入口在“build registered pipeline with options”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pipeline_with_options` |
| TC-PASS-ATTACH-ARCH-INFORMATION-045 | 公开入口 | build registered pipeline options not supported | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pipeline_options_not_supported`。 | 公开入口在“build registered pipeline options not supported”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pipeline_options_not_supported` |
| TC-PASS-ATTACH-ARCH-INFORMATION-046 | 边界/异常 | build registered pipeline option error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_pipeline_option_error`。 | “build registered pipeline option error”场景按公开错误语义失败或被拒绝。 | `test_build_registered_pipeline_option_error` |
