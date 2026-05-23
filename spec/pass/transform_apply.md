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
- `功能实现`：[`kernel_gen/passes/transform_apply.py`](../../kernel_gen/passes/transform_apply.py)
- `test`：[`test/passes/test_transform_apply.py`](../../test/passes/test_transform_apply.py)

## 依赖

- [`spec/pass/registry.md`](registry.md)
- [`spec/tools/ircheck.md`](../tools/ircheck.md)

## 目标

- registry name 固定为 `transform-apply`。
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

- 功能：构造 transform apply pass。
- 注意事项：`fold` 是 pass manager 通用选项；本 pass 不定义专属 option。

### `TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass`

- 功能：供 pass registry 根据 options 构造实例。
- 错误：非空 `options` 必须失败，错误文本包含 `transform-apply options`。

### `TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None`

- 功能：对所有携带 `kernel.transform_pipeline` 的顶层函数应用 transform，并在全部成功后提交到原 module。
- 错误：任何解析、构造、执行或目标函数消失错误必须抛出 `KernelCodeError(ErrorModule.PASS, ...)`，错误文本以前缀 `transform-apply` 开头。
- 注意事项：语法类解析失败必须包含 `transform-apply pipeline syntax`，registry 构造或执行失败必须继续归一到 `transform-apply` 前缀并保留 step 归属。

## 测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<taskwt>:/home/lfr/kernelcode_generate python3 -m expectation.pass.transform_apply`
