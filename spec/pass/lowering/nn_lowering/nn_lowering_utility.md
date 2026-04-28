# nn_lowering_utility.md

## 功能简介

- 定义 `nn_lowering` 的公共校验与辅助入口，统一 module、space、result 与 operand 数量的检查逻辑。

## API 列表

- `ensure_module_op(module: Operation) -> ModuleOp`
- `ensure_space_attr(op: Operation) -> NnMemorySpaceAttr`
- `ensure_single_result(op: Operation) -> NnMemoryType`
- `ensure_operand_count(op: Operation, expected: int) -> None`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`](../../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py)
- `test`：
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)

## 依赖

- [`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- [`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)

## 目标

- 让 `nn_lowering` 的错误行为可机械匹配，避免重复实现校验逻辑。
- 为各 family lowering 提供统一入口，减少分散的错误短语与分支。

## 限制与边界

- 仅用于 `nn_lowering` 目录内的 lowering 逻辑，不作为公开 pass 或独立命令入口。
- 失败时必须抛出 `KernelCodeError`，并保持错误短语与本文件一致。

## 公开接口

### `ensure_module_op(module: Operation) -> ModuleOp`

功能说明：

- 校验输入为 `builtin.module`，并确保 `module.ops` 可遍历。

参数说明：

- `module (Operation)`：待校验对象。

使用示例：

```python
module_op = ensure_module_op(module)
```

注意事项：

- 非 `builtin.module` 必须抛出 `KernelCodeError("module must be builtin.module")`。
- `module.ops` 不可遍历时必须抛出 `KernelCodeError("module ops must be iterable")`。

返回与限制：

- 返回 `ModuleOp`。

### `ensure_space_attr(op: Operation) -> NnMemorySpaceAttr`

功能说明：

- 获取并校验 `nn` op 的 `space` attribute。

参数说明：

- `op (Operation)`：`nn` op。

使用示例：

```python
space = ensure_space_attr(op)
```

注意事项：

- 非 `NnMemorySpaceAttr` 时必须抛出 `KernelCodeError("nn op must provide nn.space attribute")`。

返回与限制：

- 返回 `NnMemorySpaceAttr`。

### `ensure_single_result(op: Operation) -> NnMemoryType`

功能说明：

- 校验 `nn` op 仅有单个结果且类型为 `nn.memory`。

参数说明：

- `op (Operation)`：`nn` op。

使用示例：

```python
result_type = ensure_single_result(op)
```

注意事项：

- 结果数量不为 1 时必须抛出 `KernelCodeError("nn op must have exactly one result")`。
- 结果类型非 `NnMemoryType` 时必须抛出 `KernelCodeError("nn op result must be nn.memory")`。

返回与限制：

- 返回 `NnMemoryType`。

### `ensure_operand_count(op: Operation, expected: int) -> None`

功能说明：

- 校验 `nn` op 的 operand 数量。

参数说明：

- `op (Operation)`：`nn` op。
- `expected (int)`：期望 operand 数量。

使用示例：

```python
ensure_operand_count(op, 2)
```

注意事项：

- 数量不匹配时必须抛出 `KernelCodeError("nn op {op.name} expects {expected} operands, got {actual}")`。

返回与限制：

- 无返回值。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/public_name.py`
- 测试目标：
  - 验证 `NnLoweringPass` / `KernelCodeError` 的公开入口可被稳定导出。
- 功能与用例清单：
  - `test_nn_lowering_pass_public_name`
  - `test_nn_lowering_pass_public_exports`
