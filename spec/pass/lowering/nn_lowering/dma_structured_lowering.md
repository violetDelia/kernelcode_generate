# dma_structured_lowering.md

## 功能简介

- 定义 `nn_lowering` 中 dma structured family 的拆分规范。
- 负责 `nn.broadcast` / `nn.transpose` 的 lowering 语义。
- 模块级公开入口只保留 `dma_structured_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## API 列表

- `dma_structured_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](../../../../spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](../../../../test/pass/nn_lowering/test_nn_lowering_private_helpers.py)

## 依赖

- 总规范：[`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- NN dialect：[`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 通过 `dma_structured_patterns()` 提供 `nn.broadcast` / `nn.transpose` 的单 op `RewritePattern` 集合。
- 保证 broadcast/transpose 的输出由 `dma.alloc` 创建并写入。
- 动态维度必须来源于 `symbol.get_dim` 或已有 `symbol.int`，禁止引入新的符号维度。

## 限制与边界

- 仅覆盖 `nn.broadcast`、`nn.transpose`。
- `nn.broadcast` 必须 lower 为 `dma.alloc + dma.broadcast`。
- `nn.transpose` 必须 lower 为 `dma.alloc + dma.transpose`，并校验 `perm`。
- 广播若引入新的符号维度，必须报错且错误信息包含 `NnLoweringBroadcastSymbolDimNotFromSource`。
- 模块级 surviving 接口只允许 `dma_structured_patterns()`；`lower_dma_structured_family` 不属于公开入口。
- 每个 op 都必须由独立的 `@op_type_rewrite_pattern` 处理，不再通过 `block/op -> bool` family 分发。

## 公开接口

### `dma_structured_patterns() -> list[RewritePattern]`

功能说明：

- 返回 dma structured family 的有序 pattern 列表。
- 供 `nn_lowering_patterns()` 直接拼接到主 driver 中。

参数说明：

- 无。

使用示例：

```python
from kernel_gen.passes.lowering.nn_lowering.dma_structured_lowering import (
    dma_structured_patterns,
)

patterns = dma_structured_patterns()
```

注意事项：

- 返回顺序固定为 `nn.broadcast` pattern 在前、`nn.transpose` pattern 在后。
- 内部 helper 可复用 `symbol.get_dim` / `dma.alloc` 构造逻辑，但这些 helper 不属于公开接口。
- 返回列表中不得保留 `lower_dma_structured_family` 兼容入口。

返回与限制：

- 返回可直接传入 `GreedyRewritePatternApplier` 的 `RewritePattern` 列表。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](../../../../test/pass/nn_lowering/test_nn_lowering_private_helpers.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k "broadcast or transpose"`
  - `pytest -q test/pass/nn_lowering/public_name.py -k patterns`
  - `pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k dma_structured`
- 测试目标：
  - 验证 broadcast/transpose 的改写目标为 `dma.*`。
  - 验证 broadcast 的符号维与 shape 约束报错。
  - 验证主 driver 的 pattern 顺序已不再包含 dma structured family dispatcher。
- 功能与用例清单：
  - `test_lower_broadcast_dma`
  - `test_lower_transpose_to_kernel`
  - `test_lower_broadcast_with_symbol_dim`
  - `test_lower_broadcast_with_implicit_expand`
  - `test_lower_broadcast_rejects_unknown_dim`
  - `test_lower_transpose_dynamic`
  - `test_lower_broadcast_rejects_invalid_shape`
  - `test_broadcast_rejects_invalid_scalar`
  - `test_dma_structured_lowering_helpers`
