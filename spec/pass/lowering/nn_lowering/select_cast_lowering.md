# select_cast_lowering.md

## 功能简介

- 规范 `nn.select` 与 `nn.cast` 的 lowering 行为与边界。
- 结果 memory 由 `dma.alloc` 创建，并写入 `kernel.select` 或 `dma.cast`。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/select.py`](../../../test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](../../../test/pass/nn_lowering/cast.py)

## 依赖

- 总规范：[`spec/pass/lowering/nn_lowering.md`](../../../spec/pass/lowering/nn_lowering.md)
- 工具函数：[`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- NN dialect：[`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../spec/dialect/symbol.md)

## 目标

- 以稳定的 family helper 处理 `nn.select` 与 `nn.cast`。
- 输出 memory 必须显式分配，并在 `kernel.select` 或 `dma.cast` 中消费。

## 限制与边界

- 仅处理 `nn.select` 与 `nn.cast`；其他 op 必须返回 `False`。
- `nn.select`：
  - operand 数量必须为 3，`cond/lhs/rhs` 都必须是 `nn.memory`。
  - 结果类型必须为 `nn.memory`。
  - `cond.element_type` 必须是 `i1`。
  - `cond/lhs/rhs/out` 的 `shape/stride/space` 必须一致；`lhs/rhs/out` 的 `element_type` 必须一致。
  - 结果 `shape` 不允许包含 `?`。
  - `dma.alloc` 的 `dynamic_shape` 必须逐维由 `symbol.get_dim` 从 `lhs` 读取。
- `nn.cast`：
  - operand 数量必须为 1。
  - `input` 与结果都必须是 `nn.memory`。
  - `input` 与结果的 `shape/stride/space` 必须一致；`element_type` 可变化也可相同。
  - 结果 `shape` 不允许包含 `?`。
  - `dma.alloc` 的 `dynamic_shape` 必须逐维由 `symbol.get_dim` 从 `input` 读取。
  - lower 结果必须包含 `dma.cast(out, input)` 形态的 op（out + source，无返回值），且 `out` 为 `dma.alloc` 结果。
  - 若触发以下条件必须抛出 `NnLoweringError`：
    - `input` 不是 `nn.memory`：`nn.cast input must be nn.memory`
    - `input` 与结果 rank 不一致：`nn select/cast operand/result rank mismatch`
    - 结果 `shape` 含 `?`：`nn select/cast result shape must not contain '?'`
    - `dma.cast` 校验失败：`dma.cast shape mismatch` / `dma.cast stride mismatch` / `dma.cast space mismatch`
- 若 `dma.alloc`、`kernel.select` 或 `dma.cast` 校验失败，必须抛出 `NnLoweringError` 并中止当前 op 的处理。

## 公开接口

### `lower_select_cast_family(block: Block, op: Operation) -> bool`

功能说明：

- 处理 `nn.select` 与 `nn.cast` 的 lowering。
- 成功处理返回 `True`，非本 family op 返回 `False`。

参数说明：

- `block(Block)`：当前 IR block。
- `op(Operation)`：待处理 op。

使用示例：

```python
handled = lower_select_cast_family(block, op)
```

注意事项：

- 非本 family op 必须直接返回 `False`。
- 发生类型或布局不一致时抛出 `NnLoweringError`。

返回与限制：

- 返回 `bool`。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/select.py`](../../../test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](../../../test/pass/nn_lowering/cast.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/select.py`
  - `pytest -q test/pass/nn_lowering/cast.py`
- 测试目标：
  - `nn.select` lower 为 `dma.alloc + kernel.select`。
  - `nn.cast` lower 为 `dma.alloc + dma.cast`。
  - 输出 memory 由 `dma.alloc` 创建，lowering 后不再出现 `nn.*` op。
