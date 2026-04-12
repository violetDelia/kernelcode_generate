# select_cast_lowering.md

## 功能简介

- 定义 `nn.select` / `nn.cast` family 的 lowering 责任边界与入口。
- `nn.select` lower 为 `kernel.select`，`nn.cast` lower 为 `dma.cast`（out 形式）。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/select.py`](../../../../test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](../../../../test/pass/nn_lowering/cast.py)

## 依赖

- [`spec/pass/lowering/nn_lowering.md`](../../../../spec/pass/lowering/nn_lowering.md)
- [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- [`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- [`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- [`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)

## 目标

- 以单一入口处理 `nn.select` / `nn.cast`，并与 `nn_lowering` 总 spec 对齐。

## 限制与边界

- 仅处理 `nn.select` / `nn.cast`；其他 op 必须返回 `False` 且不改写。
- 本文件不得定义额外 `*Pass` 作为公开入口，执行由 `NnLoweringPass` 统一调度。

## 公开接口

### `lower_select_cast_family(block: Block, op: Operation) -> bool`

功能说明：

- 对 `nn.select` / `nn.cast` family 执行 lowering。
- 处理成功时返回 `True` 并改写 op；不属于本 family 时返回 `False`。

参数说明：

- `block (Block)`：包含 `op` 的 block。
- `op (Operation)`：待判定的 `nn` op。

使用示例：

```python
if lower_select_cast_family(block, op):
    return
```

注意事项：

- `nn.select` 必须 lower 为 `dma.alloc + kernel.select`。
- `nn.cast` 必须 lower 为 `dma.alloc + dma.cast`（out 形式）。
- 任何空间、结果类型或 operand 校验失败必须抛出 `NnLoweringError`。

返回与限制：

- 返回 `bool`，表示是否完成本 family 的 lowering。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/select.py`](../../../../test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](../../../../test/pass/nn_lowering/cast.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/select.py`
  - `pytest -q test/pass/nn_lowering/cast.py`
- 测试目标：
  - 验证 `nn.select` lower 为 `dma.alloc + kernel.select`。
  - 验证 `nn.cast` lower 为 `dma.alloc + dma.cast`。
- 功能与用例清单：
  - `test_lower_select_to_kernel_select`
  - `test_lower_cast_to_kernel_cast`
