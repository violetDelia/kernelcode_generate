# reduce_softmax_lowering

## 功能简介

为 `nn.reduce_*` 提供单 op pattern lowering 入口，输出 `kernel.reduce` 形态，并补齐 `dma.alloc`；`nn.softmax` 不在本层直接 lowering。`nn.exp` 已由 `select_cast_lowering.py` 的单 op pattern 承接，本文件的兼容 helper 仍支持旧调用点处理 `nn.exp`。

## 文档信息

- 创建者：小李飞刀
- 最后一次更改：金铲铲大作战
- spec：[`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
- 功能实现：[`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
- test：[`test/pass/nn_lowering/reduce_sum.py`](test/pass/nn_lowering/reduce_sum.py)

## 依赖

- [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
- [`kernel_gen/dialect/dma.py`](kernel_gen/dialect/dma.py)
- [`kernel_gen/dialect/kernel.py`](kernel_gen/dialect/kernel.py)
- [`kernel_gen/dialect/nn.py`](kernel_gen/dialect/nn.py)

## 目标

- 为 reduce family 提供单 op pattern lowering 入口。
- 保留 exp / reduce 兼容 helper，避免旧调用点立即失效。
- 保持 `axis`、`keepdim` 等属性校验与输出一致。

## 限制与边界

- 主注册入口仅处理 `nn.reduce_sum`、`nn.reduce_min`、`nn.reduce_max` 与 direct `nn.softmax` 拒绝。
- 兼容 helper 仅处理具体 `NnExpOp`、`NnReduceSumOp`、`NnReduceMinOp`、`NnReduceMaxOp` 类型。
- reduce 仅支持单轴 `axes`，且 `keepdim` 需为 0/1。
- `nn.softmax` 需在进入本层前先完成分解；本文件不承诺 softmax 的 direct lowering。

## 公开接口

### `lower_reduce_softmax_family(block, op) -> bool`

- 功能说明：
  - 通过具体 op 类型识别并 lower exp / reduce family op。
  - 成功处理后返回 `True`，不匹配则返回 `False`。
- 参数说明：
  - `block(Block)`: 当前 op 所在 block。
  - `op(Operation)`: 待处理 op。
- 使用示例：
  - `handled = lower_reduce_softmax_family(block, op)`
- 注意事项：
  - 输入 op 不满足 shape 或属性约束时抛 `NnLoweringError`。
- 返回与限制：
  - `True` 表示已完成 lowering；`False` 表示不匹配。

### `reduce_softmax_patterns() -> list[RewritePattern]`

- 功能说明：
  - 返回 `NnReduceSumOp`、`NnReduceMinOp`、`NnReduceMaxOp` 与 direct `NnSoftmaxOp` 的具体 pattern。
  - `nn.softmax` pattern 只抛出 `NnLoweringError("nn.softmax must be decomposed before lower-nn")`。
- 使用示例：
  - `patterns = reduce_softmax_patterns()`
- 注意事项：
  - 不再注册 reduce/softmax family pattern；主 driver 按具体 op 类型命中。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py)
  - [`test/pass/nn_lowering/reduce_sum.py`](test/pass/nn_lowering/reduce_sum.py)
  - [`test/pass/nn_lowering/reduce_min.py`](test/pass/nn_lowering/reduce_min.py)
  - [`test/pass/nn_lowering/reduce_max.py`](test/pass/nn_lowering/reduce_max.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/exp.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/reduce_min.py test/pass/nn_lowering/reduce_max.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering.reduce`
- 测试目标：
  - 确认 exp / reduce family 的 lowering 结果与属性校验一致。
- 功能与用例清单：
  - `nn.exp` 正向改写为 `kernel.exp`
  - `nn.reduce_sum/min/max` 正向改写为 `kernel.reduce(kind=...)`
  - `nn.softmax` 需先由上游完成分解，不在本文件职责面内
