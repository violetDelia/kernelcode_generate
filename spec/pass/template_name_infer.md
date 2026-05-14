# template_name_infer

## 功能简介

- 定义 `template-name-infer` pass 的公开合同。
- 该 pass 对每个 `func.func` 建立 template-name graph，统一求解并写回 `NnMemoryType.template_name`。
- pass 不写 op 专属大分支；op 语义必须由 `template_name_constraints` 注册表承载。

## API 列表

- `class TemplateNameInferPass(fold: bool = True)`
- `TemplateNameInferPass.from_options(options: dict[str, str]) -> TemplateNameInferPass`
- `TemplateNameInferPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/template_name_infer.md`](../../spec/pass/template_name_infer.md)
- `功能实现`：[`kernel_gen/passes/template_name_infer.py`](../../kernel_gen/passes/template_name_infer.py)
- `test`：[`test/passes/test_template_name_infer.py`](../../test/passes/test_template_name_infer.py)

## 依赖

- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- [`spec/pass/template_name_graph.md`](../../spec/pass/template_name_graph.md)
- [`spec/pass/template_name_constraints.md`](../../spec/pass/template_name_constraints.md)
- [`spec/pass/template_name_default_constraints.md`](../../spec/pass/template_name_default_constraints.md)
- [`spec/pass/registry.md`](../../spec/pass/registry.md)

## 目标

- registry key 固定为 `template-name-infer`。
- 函数签名 memory block argument 是默认命名 seed；普通中间 memory result 没有显式 name 且不与 seed family 相连时保持无 template name。
- pass 只写回 `template_name`，不得改变 shape、stride、element_type 或 space。
- 写回函数参数后必须同步 `func.func` function type。
- 未注册 memory op 必须稳定失败，暴露默认约束漏项。
- `from_options({})` 成功；非空 options 必须稳定失败。

## API 详细说明

### `class TemplateNameInferPass(fold: bool = True)`

- 功能：构造 template-name 推导 pass。
- 注意事项：`fold` 是 pass manager 通用选项；本 pass 不定义专属 option。

### `TemplateNameInferPass.from_options(options: dict[str, str]) -> TemplateNameInferPass`

- 功能：供 pass registry 根据 options 构造实例。
- 错误：`options` 非空必须报 `TemplateNameInferPassError: unknown options: ...`。

### `TemplateNameInferPass.apply(ctx: Context, module: ModuleOp) -> None`

- 功能：注册默认约束，遍历每个 `func.func`，求解并写回 template name。
- 错误：未知 memory op、同 family 冲突 name、非法 template name 均必须稳定失败。

## 测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_infer.py`
