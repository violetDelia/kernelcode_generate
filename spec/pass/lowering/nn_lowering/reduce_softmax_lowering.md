# reduce_softmax_lowering.md

## 功能简介

- 为 `nn.reduce_*` 提供单 op pattern lowering 入口，输出 `kernel.reduce` 形态，并补齐 `dma.alloc`。
- 对 direct `nn.softmax` 提供稳定拒绝路径，要求先由上游完成分解。
- 模块级公开入口只保留 `reduce_softmax_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/test_reduce_lowering.py`](../../../../test/pass/nn_lowering/test_reduce_lowering.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](../../../../test/pass/nn_lowering/test_nn_lowering_private_helpers.py)

## 依赖

- [`spec/pass/lowering/nn_lowering.md`](../../../../spec/pass/lowering/nn_lowering.md)
- [`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- [`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- [`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)

## 目标

- 通过 `reduce_softmax_patterns()` 提供 reduce family 与 softmax reject 的单 op `RewritePattern` 集合。
- 保持 `axis`、`keepdim` 等属性校验与输出一致。
- 保持 `nn.exp` 已迁入 `select_cast_lowering.py`，不再由本模块承接。

## 限制与边界

- 主注册入口仅覆盖 `nn.reduce_sum`、`nn.reduce_min`、`nn.reduce_max` 与 direct `nn.softmax` 拒绝。
- `nn.reduce_*` 仅支持单轴 `axes`，且 `keepdim` 需为 0/1。
- `nn.softmax` 需在进入本层前先完成分解；本文件不承诺 softmax 的 direct lowering。
- 模块级 surviving 接口只允许 `reduce_softmax_patterns()`；`lower_reduce_softmax_family` 不属于公开入口。
- 每个 reduce op 与 softmax reject 都必须由独立的 `@op_type_rewrite_pattern` 处理，不再通过 family dispatcher 做名称分发。

## 公开接口

### `reduce_softmax_patterns() -> list[RewritePattern]`

功能说明：

- 返回 `nn.reduce_sum`、`nn.reduce_min`、`nn.reduce_max` 与 direct `nn.softmax` 拒绝 pattern 的有序列表。
- 供 `nn_lowering_patterns()` 直接拼接到主 driver 中。

参数说明：

- 无。

使用示例：

```python
from kernel_gen.passes.lowering.nn_lowering.reduce_softmax_lowering import (
    reduce_softmax_patterns,
)

patterns = reduce_softmax_patterns()
```

注意事项：

- `nn.softmax` pattern 只负责抛出 `NnLoweringError("nn.softmax must be decomposed before lower-nn")`。
- 返回列表中不得保留 `lower_reduce_softmax_family` 兼容入口。
- `nn.exp` 不属于本模块的 pattern 列表。

返回与限制：

- 返回可直接传入 `GreedyRewritePatternApplier` 的 `RewritePattern` 列表。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/test_reduce_lowering.py`](../../../../test/pass/nn_lowering/test_reduce_lowering.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](../../../../test/pass/nn_lowering/test_nn_lowering_private_helpers.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/test_reduce_lowering.py`
  - `pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k softmax`
  - `pytest -q test/pass/nn_lowering/public_name.py -k patterns`
  - `pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k "reduce or softmax"`
- 测试目标：
  - 确认 reduce family 的 lowering 结果与属性校验一致。
  - 确认 direct `nn.softmax` 稳定报错，提示必须先完成分解。
  - 确认主 driver 的 pattern 顺序已不再包含 reduce family dispatcher。
- 功能与用例清单：
  - `test_nn_lowering_reduce_ircheck`
  - `test_nn_lowering_reduce_shape_mismatch`
  - `test_lower_softmax_requires_decompass`
  - `test_select_reduce_softmax_additional_branches`
