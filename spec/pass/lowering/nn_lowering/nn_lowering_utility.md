# nn_lowering_utility.md

## 功能简介

- 定义 `nn_lowering` 的公共校验与辅助入口，统一 module、space、result 与 operand 数量的检查逻辑。

## API 列表

- `ensure_module_op(module: Operation) -> ModuleOp`
- `ensure_space_attr(op: Operation) -> NnMemorySpaceAttr`
- `ensure_single_result(op: Operation) -> NnMemoryType`
- `ensure_operand_count(op: Operation, expected: int) -> None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`](../../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py)
- `test`：
  - [`test/passes/lowering/nn_lowering/test_public_name.py`](../../../../test/passes/lowering/nn_lowering/test_public_name.py)

## 依赖

- [`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- [`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)

## 目标

- 让 `nn_lowering` 的错误行为可机械匹配，避免重复实现校验逻辑。
- 为各 family lowering 提供统一入口，减少分散的错误短语与分支。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 仅用于 `nn_lowering` 目录内的 lowering 逻辑，不作为公开 pass 或独立命令入口。
- 失败时必须抛出 `KernelCodeError`，并保持错误短语与本文件一致。
## API详细说明

### `ensure_module_op(module: Operation) -> ModuleOp`

- api：`ensure_module_op(module: Operation) -> ModuleOp`
- 参数：
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ModuleOp`。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering.nn_lowering_utility import ensure_module_op

  module_op = ensure_module_op(module)
  ```
- 功能说明：校验输入为 `builtin.module`，并确保 `module.ops` 可遍历。
- 注意事项：非 `builtin.module` 必须抛出 `KernelCodeError("module must be builtin.module")`；`module.ops` 不可遍历时必须抛出 `KernelCodeError("module ops must be iterable")`。

### `ensure_space_attr(op: Operation) -> NnMemorySpaceAttr`

- api：`ensure_space_attr(op: Operation) -> NnMemorySpaceAttr`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`NnMemorySpaceAttr`。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering.nn_lowering_utility import ensure_space_attr

  space = ensure_space_attr(op)
  ```
- 功能说明：获取并校验 `nn` op 的 `space` attribute。
- 注意事项：非 `NnMemorySpaceAttr` 时必须抛出 `KernelCodeError("nn op must provide nn.space attribute")`。

### `ensure_single_result(op: Operation) -> NnMemoryType`

- api：`ensure_single_result(op: Operation) -> NnMemoryType`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`NnMemoryType`。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering.nn_lowering_utility import ensure_single_result

  result_type = ensure_single_result(op)
  ```
- 功能说明：校验 `nn` op 仅有单个结果且类型为 `nn.memory`。
- 注意事项：结果数量不为 1 时必须抛出 `KernelCodeError("nn op must have exactly one result")`；结果类型非 `NnMemoryType` 时必须抛出 `KernelCodeError("nn op result must be nn.memory")`。

### `ensure_operand_count(op: Operation, expected: int) -> None`

- api：`ensure_operand_count(op: Operation, expected: int) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `Operation`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `expected`：期望结果文本或对象，用于定义比较基线；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering.nn_lowering_utility import ensure_operand_count

  ensure_operand_count(op, 2)
  ```
- 功能说明：校验 `nn` op 的 operand 数量。
- 注意事项：数量不匹配时必须抛出 `KernelCodeError("nn op {op.name} expects {expected} operands, got {actual}")`。

## 测试

- 测试文件：`test/passes/lowering/nn_lowering/test_public_name.py`
- 执行命令：`pytest -q test/passes/lowering/nn_lowering/test_public_name.py`

### 测试目标

- 验证 `spec/pass/lowering/nn_lowering/nn_lowering_utility.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-LOWERING-NN-LOWERING-NN-LOWERING-UTILITY-001 | 公开入口 | `test_nn_lowering_pass_public_name` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_lowering_pass_public_name`。 | 公开入口在“`test_nn_lowering_pass_public_name`”场景下可导入、构造、注册或按名称发现。 | `test_nn_lowering_pass_public_name` |
| TC-PASS-LOWERING-NN-LOWERING-NN-LOWERING-UTILITY-002 | 公开入口 | `test_nn_lowering_pass_public_exports` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_lowering_pass_public_exports`。 | 公开入口在“`test_nn_lowering_pass_public_exports`”场景下可导入、构造、注册或按名称发现。 | `test_nn_lowering_pass_public_exports` |
