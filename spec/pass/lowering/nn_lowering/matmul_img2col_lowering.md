# matmul_img2col_lowering

## 功能简介

- 统一处理 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d` 的 lowering 逻辑。
- 输出固定为 `kernel.matmul`、`kernel.img2col1d`、`kernel.img2col2d`，并通过 `dma.alloc` 创建结果 memory。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](../../../../spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/matmul.py`](../../../../test/pass/nn_lowering/matmul.py)
  - [`test/pass/nn_lowering/img2col1d.py`](../../../../test/pass/nn_lowering/img2col1d.py)
  - [`test/pass/nn_lowering/img2col2d.py`](../../../../test/pass/nn_lowering/img2col2d.py)

## 依赖

- 公共 helper：[`kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`](../../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py)
- NN dialect：[`kernel_gen/dialect/nn.py`](../../../../kernel_gen/dialect/nn.py)
- Kernel dialect：[`kernel_gen/dialect/kernel.py`](../../../../kernel_gen/dialect/kernel.py)
- DMA dialect：[`kernel_gen/dialect/dma.py`](../../../../kernel_gen/dialect/dma.py)
- Symbol dialect：[`kernel_gen/dialect/symbol.py`](../../../../kernel_gen/dialect/symbol.py)

## 目标

- 将 `nn.matmul` lower 为 `kernel.matmul`，结果由 `dma.alloc` 创建；若输出包含符号维度，需从输入插入 `symbol.get_dim` 并作为 `dma.alloc` 的 dynamic shape。
- 将 `nn.img2col1d/nn.img2col2d` lower 为对应的 `kernel.img2col*`，参数必须为 `symbol.int`；若输出含符号维度，需使用 `symbol.get_dim` 与 `symbol` 算术构造 `dma.alloc` 的 dynamic shape。
- 提供单一入口 `lower_matmul_img2col_family` 用于 family 分发。

## 限制与边界

- 仅处理 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d`；其他 op 必须返回 `False`。
- `nn.matmul` 仅支持 rank-2 memory，且 stride 必须为连续布局。
- `nn.img2col1d/2d` 的动态参数必须是 `!symbol.int<"...">`，不接受 `i32/index` 或整数 attribute 直接作为 operand。

## 公开接口

### `lower_matmul_img2col_family(block, op) -> bool`

功能说明：

- 若 op 属于 matmul/img2col family，则完成 lowering 并返回 `True`。
- 不匹配则返回 `False`。

参数说明：

- `block(Block)`：op 所在 block。
- `op(Operation)`：待处理 op。

使用示例：

```python
handled = lower_matmul_img2col_family(block, op)
```

注意事项：

- 当 op 参数或 shape/stride 不满足要求时需抛出 `NnLoweringError`。

返回与限制：

- `True` 表示已处理；`False` 表示未匹配。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/matmul.py`](../../../../test/pass/nn_lowering/matmul.py)
  - [`test/pass/nn_lowering/img2col1d.py`](../../../../test/pass/nn_lowering/img2col1d.py)
  - [`test/pass/nn_lowering/img2col2d.py`](../../../../test/pass/nn_lowering/img2col2d.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/matmul.py test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/matmul.py`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering.img2col`
- 测试目标：
  - 验证 `nn.matmul` -> `kernel.matmul` 的 lowering 目标与输出 memory 约束。
  - 验证 `nn.img2col1d/nn.img2col2d` -> `kernel.img2col*` 的 lowering 目标与 `symbol.int` 参数约束。
