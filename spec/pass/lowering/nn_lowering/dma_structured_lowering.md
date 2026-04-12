# dma_structured_lowering.md

## 功能简介

- 定义 `nn_lowering` 中 dma_structured family 的拆分规范。
- 负责 `nn.broadcast` / `nn.transpose` 的 lowering 语义。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](../../../../spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
- `test`：[`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)

## 依赖

- 总规范：[`spec/pass/lowering/nn_lowering.md`](../../../../spec/pass/lowering/nn_lowering.md)
- NN dialect：[`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 提供 `lower_dma_structured_family` 入口，集中处理 dma_structured family lowering。
- 保证 broadcast/transpose 的输出由 `dma.alloc` 创建并写入。
- 动态维度必须来源于 `symbol.get_dim` 或已有 `symbol.int`，禁止引入新的符号维度。

## 限制与边界

- 仅处理 `nn.broadcast`、`nn.transpose`；其他 op 必须返回 `False`。
- `nn.broadcast` 必须 lower 为 `dma.alloc + dma.broadcast`。
- `nn.transpose` 必须 lower 为 `dma.alloc + dma.transpose`，并校验 `perm`。
- 广播若引入新的符号维度，必须报错且错误信息包含 `NnLoweringBroadcastSymbolDimNotFromSource`。

## 公开接口

### `lower_dma_structured_family(block: Block, op: Operation) -> bool`

功能说明：

- 对 dma_structured family 的 op 执行 lowering。

参数说明：

- `block(Block)`：当前 op 所在的 block。
- `op(Operation)`：待处理的 nn op。

使用示例：

```python
from kernel_gen.passes.lowering.nn_lowering.dma_structured_lowering import lower_dma_structured_family

if lower_dma_structured_family(block, op):
    return
```

注意事项：

- 仅处理本 family 的 op；其它 op 必须返回 `False`。
- 若校验失败，必须抛出 `NnLoweringError`。

返回与限制：

- 返回 `True` 表示已完成 lowering；`False` 表示不处理该 op。

## 测试

- 测试文件：[`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k "broadcast or transpose"`
- 测试目标：
  - 验证 broadcast/transpose 的改写目标为 dma.*。
  - 验证 broadcast 的符号维与 shape 约束报错。
- 功能与用例清单：
  - `test_lower_broadcast_dma`
  - `test_lower_transpose_to_kernel`
  - `test_lower_broadcast_with_symbol_dim`
  - `test_lower_broadcast_with_implicit_expand`
  - `test_lower_broadcast_rejects_unknown_dim`
  - `test_lower_transpose_dynamic`
  - `test_lower_broadcast_rejects_invalid_shape`
  - `test_broadcast_rejects_invalid_scalar`
