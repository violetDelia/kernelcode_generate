# transform_apply.md

## 功能简介

- 定义 `transform-apply` pass 的公开合同。
- 该 pass 读取 pattern 函数上的 `kernel.transform_pipeline: StringAttr`，在函数级 clone 上执行 pipeline 字符串描述的 pass / pipeline，成功后删除该 attr。
- 失败路径必须保持原 module 不变，避免半应用 transform。

## API 列表

- `class TransformApplyPass(fold: bool = True)`
- `TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass`
- `TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/transform_apply.md`](../../spec/pass/transform_apply.md)
- `功能实现`：[`kernel_gen/passes/tuning/transform_apply.py`](../../kernel_gen/passes/tuning/transform_apply.py)
- `test`：[`test/passes/test_transform_apply.py`](../../test/passes/test_transform_apply.py)

## 依赖

- [`spec/pass/registry.md`](registry.md)
- [`spec/tools/ircheck.md`](../tools/ircheck.md)

## 目标

- registry name 固定为 `transform-apply`。
- canonical Python 路径固定为 `kernel_gen.passes.tuning.transform_apply` 或 tuning package root `kernel_gen.passes.tuning.TransformApplyPass`；旧根模块 `kernel_gen.passes.transform_apply` 不保留兼容。
- `from_options({})` 成功；任何未知 option 必须失败，错误文本包含 `transform-apply options`。
- 只消费顶层 `func.func` 的 `kernel.transform_pipeline` 标准 `StringAttr`；空字符串或非字符串必须失败。
- pipeline 字符串支持 `--pass <name-or-name{options}>` 与 `--pipeline <name-or-name{options}>`。
- `--pass canonicalize` 由本 pass 局部解析到 xDSL `CanonicalizePass`，不要求全局 registry 注册 `canonicalize`。
- 其它 pass / pipeline 必须经公开 registry 构造；未知名称、非法 option 或 pass 执行失败必须归一为 `transform-apply` 失败文本。
- pipeline 字符串语法错误必须失败，错误文本包含 `transform-apply pipeline syntax`。
- 成功后必须移除 `kernel.transform_pipeline` attr；失败时原 module 必须保持不变。
- 本 pass 不公开 pipeline parser helper，不允许测试或外部调用方跨文件调用私有 helper。

## API 详细说明

### `class TransformApplyPass(fold: bool = True)`

- api：`class TransformApplyPass(fold: bool = True)`
- 参数：
  - `fold`：pass manager 通用折叠开关；类型 `bool`；默认值 `True`；不允许 `None`；本 pass 不读取该值决定 transform 语义，非法类型由 Python dataclass / 调用方约束处理。
- 返回值：`TransformApplyPass` 实例；公开字段 `name` 固定为 `transform-apply`；构造本身不修改 IR。
- 使用示例：

  ```python
  from kernel_gen.passes.tuning import TransformApplyPass

  pass_obj = TransformApplyPass()
  ```
- 功能说明：构造可由 pass manager、registry 或 npu-demo pipeline 使用的 transform apply pass。
- 注意事项：`fold` 仅保持 pass 通用构造惯例；本 pass 第一阶段不定义专属 option，不公开 pipeline parser helper。

### `TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass`

- api：`TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass`
- 参数：
  - `options`：registry 透传的 pass 专属 option 字典；类型 `dict[str, str]`；无默认值，调用方必须显式提供；不允许 `None`；必须为空字典，任何 key 都必须失败。
- 返回值：空 `options` 时返回新的 `TransformApplyPass`；非空 `options` 抛出 `KernelCodeError(ErrorModule.PASS, ...)`，错误文本包含 `transform-apply options unknown: <name>`。
- 使用示例：

  ```python
  from kernel_gen.passes.tuning import TransformApplyPass

  pass_obj = TransformApplyPass.from_options({})
  ```
- 功能说明：供 `spec/pass/registry.md` 定义的公开 registry 按统一入口构造 `transform-apply`。
- 注意事项：`fold` 是 registry 通用 option，不属于本方法的 `options`；未知专属 option 的稳定错误前缀必须保留为 `transform-apply options`。

### `TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL `Context`；无默认值，调用方必须显式提供；不允许 `None`；用于执行目标 pass 的公开 `apply(ctx, module)` 入口。
  - `module`：xDSL `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None`；必须是 builtin module 或可由 `ensure_builtin_module(...)` 接受的 module。
- 返回值：`None`；成功时原地更新 `module`，删除目标函数上的 `kernel.transform_pipeline` attr；失败时原 `module` 必须保持不变。
- 使用示例：

  ```python
  from xdsl.context import Context
  from kernel_gen.passes.tuning import TransformApplyPass

  TransformApplyPass().apply(Context(), module)
  ```
- 功能说明：查找顶层 `func.func` 上的 `kernel.transform_pipeline: StringAttr`，在函数级 clone 中执行 `--pass` / `--pipeline` step sequence，所有目标成功后一次性提交。
- 注意事项：只消费非空字符串 attr；语法类解析失败必须包含 `transform-apply pipeline syntax`；registry 构造或 step 执行失败必须继续归一到 `transform-apply step <kind> '<name>' failed`；`--pass canonicalize` 是本 pass 内置公开 step resolver，不注册到全局 registry；旧根模块 `kernel_gen.passes.transform_apply` 不保留兼容。

## 测试

- 测试文件：`test/passes/test_transform_apply.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py`
- 执行命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py -k 'kernel_pattern_passes'`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or transform_apply or kernel_pattern_attach or static_dump_uses_pool_without_multi_buffer'`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<taskwt>:/home/lfr/kernelcode_generate python3 -m expectation.pass.transform_apply`

### 测试目标

- 验证 `TransformApplyPass` 新 canonical Python 路径可达，旧根模块稳定失败。
- 验证 `TransformApplyPass.apply(...)` 成功消费 `kernel.transform_pipeline`、删除 attr，并在失败时保持 module 回滚。
- 验证 `TransformApplyPass.from_options(...)` 与 registry 构造入口拒绝未知专属 option。
- 验证 npu-demo lowering pipeline 使用 `transform-apply` 公开 pass name，并在 `kernel-pattern-attach` 后按顺序执行。
- 单列主仓只读 expectation 合同验收，确认 transform-apply 公开 IR 合同继续通过。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-TRANSFORM-APPLY-001 | 公开路径 | tuning canonical module 与 package root 可导入，旧根模块不可导入 | Python import 环境包含仓库根目录 | 运行 `test_transform_apply_public_import_path_rehomed` | `kernel_gen.passes.tuning.transform_apply` 与 `kernel_gen.passes.tuning.TransformApplyPass` 指向同一类；`kernel_gen.passes.transform_apply` 抛出 `ModuleNotFoundError` | `test_transform_apply_public_import_path_rehomed` |
| TC-PASS-TRANSFORM-APPLY-002 | attr 消费 | 目标函数携带 `kernel.transform_pipeline = "--pass canonicalize"` | 输入 module 含单个公开 `func.func` pattern | 运行 `test_transform_apply_consumes_canonicalize_pipeline_attr` | pass 成功执行，输出 IR 不再包含 `kernel.transform_pipeline` | `test_transform_apply_consumes_canonicalize_pipeline_attr` |
| TC-PASS-TRANSFORM-APPLY-003 | 失败回滚 | pipeline 引用未知 pass | 执行前先打印 module 文本 | 运行 `test_transform_apply_rolls_back_on_invalid_pipeline` | 抛出包含 `transform-apply` 的 `KernelCodeError`，失败后 module 文本与执行前完全一致 | `test_transform_apply_rolls_back_on_invalid_pipeline` |
| TC-PASS-TRANSFORM-APPLY-004 | 语法错误 | pipeline 字符串缺少 step 参数 | 目标函数携带非法 `kernel.transform_pipeline` | 运行 `test_transform_apply_reports_pipeline_syntax_error` | 抛出包含 `transform-apply pipeline syntax` 的 `KernelCodeError`，失败后 module 不变 | `test_transform_apply_reports_pipeline_syntax_error` |
| TC-PASS-TRANSFORM-APPLY-005 | step 失败归一 | transform step 执行下游 pass 失败 | 目标函数使用会触发下游 pass 失败的公开 IR | 运行 `test_transform_apply_wraps_step_execution_failure` | 错误文本包含 `transform-apply step pass '<name>' failed`，不泄漏为未归一异常 | `test_transform_apply_wraps_step_execution_failure` |
| TC-PASS-TRANSFORM-APPLY-006 | registry option | registry / from_options 传入未知专属 option | `load_builtin_passes()` 已加载内置 pass | 运行 `test_transform_apply_rejects_unknown_options` 与 `test_build_registered_kernel_pattern_passes_reject_unknown_options` | `from_options` 与 registry 均失败，错误文本包含 `transform-apply options unknown` | `test_transform_apply_rejects_unknown_options`、`test_build_registered_kernel_pattern_passes_reject_unknown_options` |
| TC-PASS-TRANSFORM-APPLY-007 | pipeline 顺序 | npu-demo lowering 中 `kernel-pattern-attach -> transform-apply` 顺序稳定 | 使用公开 pipeline builder 构造 pass manager | 运行 `test_npu_demo_lowering_pipeline_pass_order` | pass order 包含 `kernel-pattern-attach` 后紧跟 `transform-apply`，顶层不直接接入 standalone `lower-dma-memory-hierarchy` | `test_npu_demo_lowering_pipeline_pass_order` |
| TC-PASS-TRANSFORM-APPLY-008 | 合同验收 | 主仓只读 expectation transform-apply 合同 | `PYTHONPATH=<taskwt>:/home/lfr/kernelcode_generate`，任务 worktree 代码优先 | 运行 `python3 -m expectation.pass.transform_apply` | `passes-transform_apply-basic-*` case 全部通过 | `python3 -m expectation.pass.transform_apply` |
