# template_name_constraints

## 功能简介

- 定义 operation 到 template-name graph constraint 的公开注册与构造合同。
- 注册表只保存约束规格或 builder；不得分配 template name，不得写 IR。
- 当前文件内解析 helper 不是公开 API，测试与实现不得跨文件直连。

## API 列表

- `class TemplateValueRef(kind: Literal["operand", "result"], index: int)`
- `class SameSpec(lhs: TemplateValueRef, rhs: TemplateValueRef)`
- `class VerifyOnlySpec(item: TemplateValueRef)`
- `TemplateConstraintBuilder = Callable[[Operation], tuple[TemplateNameConstraint, ...]]`
- `register_template_constraints(op_name: str, constraints: tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder) -> None`
- `get_template_constraints(op_name: str) -> tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder`
- `build_template_constraints(op: Operation) -> tuple[TemplateNameConstraint, ...]`

## 文档信息

- `spec`：[`spec/pass/template_name_constraints.md`](../../spec/pass/template_name_constraints.md)
- `功能实现`：[`kernel_gen/passes/template_name_constraints.py`](../../kernel_gen/passes/template_name_constraints.py)
- `test`：[`test/passes/test_template_name_constraints.py`](../../test/passes/test_template_name_constraints.py)

## 目标

- 约束规格只引用公开 `operand` / `result` 序号。
- `build_template_constraints(op)` 对已注册 op 生成 `Same` / `VerifyOnly` graph constraint。
- 携带 memory operand/result 的未知 op 必须稳定失败，不允许隐式跳过。
- 不携带 memory operand/result 的未知 op 返回空约束。
- 重复注册同名 op 必须失败。

## API 详细说明

### `class TemplateValueRef(kind: Literal["operand", "result"], index: int)`

- 功能：描述 operation 中一个公开 operand/result 位置。
- 错误：`kind` 非 `operand/result` 或 index 越界时由构造约束阶段稳定失败。

### `class SameSpec(lhs: TemplateValueRef, rhs: TemplateValueRef)`

- 功能：声明两个引用位置在具体 op 上应构造 `Same`。

### `class VerifyOnlySpec(item: TemplateValueRef)`

- 功能：声明一个引用位置在具体 op 上应构造 `VerifyOnly`。

### `register_template_constraints(op_name: str, constraints: tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder) -> None`

- 功能：注册完整 op 名到约束规格或动态 builder。
- 错误：空 op name、重复注册、非 tuple 且非 callable 的 constraints 必须稳定失败。

### `get_template_constraints(op_name: str) -> tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder`

- 功能：读取已注册约束。
- 错误：空 op name 或未注册 op name 必须稳定失败，不得返回隐藏 no-op。

### `build_template_constraints(op: Operation) -> tuple[TemplateNameConstraint, ...]`

- 功能：把静态 spec 或 builder 转换成 graph constraint。
- 错误：引用位置不存在、引用值不是 `NnMemoryType`、未知 memory op 均必须稳定失败。

## 测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_constraints.py`
