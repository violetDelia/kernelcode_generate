# template_name_graph

## 功能简介

- 定义 `nn.memory.template_name` 推导使用的纯 graph 求解合同。
- 本文件只承载 SSA value、Same / VerifyOnly 约束、solution 与 union-find 求解；不得读取 pass registry，不得写 IR。
- 当前文件内 helper 不是公开 API，调用方只能使用下列 API 列表。

## API 列表

- `class TemplateNameValue(value: SSAValue, op: Operation, kind: Literal["operand", "result", "block_arg"], index: int)`
- `class Same(lhs: TemplateNameValue, rhs: TemplateNameValue)`
- `class VerifyOnly(item: TemplateNameValue)`
- `class TemplateNameSolution(names: Mapping[SSAValue, str])`
- `TemplateNameSolution.name_of(value: SSAValue) -> str | None`
- `class TemplateNameGraph()`
- `TemplateNameGraph.add_value(item: TemplateNameValue) -> None`
- `TemplateNameGraph.add_constraint(constraint: TemplateNameConstraint) -> None`
- `TemplateNameGraph.add_constraints(constraints: Sequence[TemplateNameConstraint]) -> None`
- `TemplateNameGraph.add_signature_seed(item: TemplateNameValue) -> None`
- `TemplateNameGraph.solve() -> TemplateNameSolution`

## 文档信息

- `spec`：[`spec/pass/template_name_graph.md`](../../spec/pass/template_name_graph.md)
- `功能实现`：[`kernel_gen/passes/template_name_graph.py`](../../kernel_gen/passes/template_name_graph.py)
- `test`：[`test/passes/test_template_name_graph.py`](../../test/passes/test_template_name_graph.py)

## 目标

- `Same` 约束把两个真实 `SSAValue` 合并到同一 template family。
- `VerifyOnly` 只校验该 value 可承载合法 template name，不建立等价关系。
- 已有非空 template name 优先；同一 family 出现多个不同 name 必须稳定失败。
- 无已有 name 且包含 signature seed 的 family 按首次出现顺序生成 `T1/T2/...`。
- 无已有 name 且不包含 signature seed 的 family 不进入 `TemplateNameSolution.names`。

## API 详细说明

### `class TemplateNameValue(value: SSAValue, op: Operation, kind: Literal["operand", "result", "block_arg"], index: int)`

- 功能：描述参与求解的真实 memory SSA value 与来源位置。
- 错误：`value.type` 非 `NnMemoryType` 时必须由 `TemplateNameGraph.add_value(...)` 稳定失败。

### `class Same(lhs: TemplateNameValue, rhs: TemplateNameValue)`

- 功能：声明两个 value 属于同一 template family。
- 错误：同一 family 内多个显式 name 不一致时由 `solve()` 报 `TemplateNameGraphError: conflicting template_name...`。

### `class VerifyOnly(item: TemplateNameValue)`

- 功能：只让 value 进入校验域，不合并 family。

### `class TemplateNameGraph()`

- 功能：收集 value、约束与 signature seed，并生成稳定 `TemplateNameSolution`。
- 注意事项：graph 不写 IR；写回职责只属于 `TemplateNameInferPass`。

## 测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_graph.py`
