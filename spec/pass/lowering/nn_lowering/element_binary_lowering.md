# element_binary_lowering.md

## 功能简介

- 定义 element binary / compare family 的 lowering 责任边界。
- 覆盖 `nn.add/sub/mul/div/truediv` 与 `nn.eq/ne/lt/le/gt/ge`，并输出 `kernel.binary_elewise`。
- 模块级公开入口只保留 `element_binary_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/element_binary_add.py`](../../../../test/pass/nn_lowering/element_binary_add.py)
  - [`test/pass/nn_lowering/element_binary_sub.py`](../../../../test/pass/nn_lowering/element_binary_sub.py)
  - [`test/pass/nn_lowering/element_binary_mul.py`](../../../../test/pass/nn_lowering/element_binary_mul.py)
  - [`test/pass/nn_lowering/element_binary_div.py`](../../../../test/pass/nn_lowering/element_binary_div.py)
  - [`test/pass/nn_lowering/element_binary_truediv.py`](../../../../test/pass/nn_lowering/element_binary_truediv.py)
  - [`test/pass/nn_lowering/element_compare_eq.py`](../../../../test/pass/nn_lowering/element_compare_eq.py)
  - [`test/pass/nn_lowering/element_compare_ne.py`](../../../../test/pass/nn_lowering/element_compare_ne.py)
  - [`test/pass/nn_lowering/element_compare_lt.py`](../../../../test/pass/nn_lowering/element_compare_lt.py)
  - [`test/pass/nn_lowering/element_compare_le.py`](../../../../test/pass/nn_lowering/element_compare_le.py)
  - [`test/pass/nn_lowering/element_compare_gt.py`](../../../../test/pass/nn_lowering/element_compare_gt.py)
  - [`test/pass/nn_lowering/element_compare_ge.py`](../../../../test/pass/nn_lowering/element_compare_ge.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](../../../../test/pass/nn_lowering/test_nn_lowering_private_helpers.py)

## 依赖

- [`spec/pass/lowering/nn_lowering.md`](../../../../spec/pass/lowering/nn_lowering.md)
- [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- [`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- [`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- [`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- [`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 通过 `element_binary_patterns()` 提供 element binary / compare family 的单 op `RewritePattern` 集合。
- 为每个受支持 op 固定一个独立 pattern，并复用共享构造 helper 生成 `kernel.binary_elewise(kind=...)`。
- 保持 mixed scalar / mixed compare 的桥接路径与 `nn_lowering` 总 spec 一致。

## 限制与边界

- 仅覆盖 `nn.add`、`nn.sub`、`nn.mul`、`nn.div`、`nn.truediv`、`nn.eq`、`nn.ne`、`nn.lt`、`nn.le`、`nn.gt`、`nn.ge`。
- 本模块不得定义额外 `*Pass` 作为公开入口，执行由 `NnLoweringPass` 统一调度。
- 模块级 surviving 接口只允许 `element_binary_patterns()`；`lower_element_binary_family` 不属于公开入口，外部 caller 不得继续依赖 `block/op -> bool` family 分发。
- 每个 op 都必须由对应的 `@op_type_rewrite_pattern` 独立匹配；不得回退为按字符串名分发的 family placeholder pattern。
- 需要 `dma.broadcast` 桥接的 mixed compare 行为必须遵循总 spec 中的规则。
- `memory + memory` 的静态 add/sub 输出只要求收口到 `dma.alloc + kernel.binary_elewise + func.return`；不把 `symbol.get_dim` 视为必现前置行。
- 结果 shape 含符号维度时，才要求在 `dma.alloc` 前按 rank 顺序生成 `symbol.get_dim`。
- mixed scalar element binary 需要先物化 `dma.alloc + dma.fill`，再写入 `kernel.binary_elewise`；该路径禁止回退为 `dma.broadcast`。
- 任何空间、结果类型或 operand 校验失败必须抛出 `NnLoweringError`。

## 公开接口

### `element_binary_patterns() -> list[RewritePattern]`

功能说明：

- 返回 element binary / compare family 的有序 pattern 列表。
- 供 `nn_lowering_patterns()` 直接拼接到主 driver 中。

参数说明：

- 无。

使用示例：

```python
from kernel_gen.passes.lowering.nn_lowering.element_binary_lowering import (
    element_binary_patterns,
)

patterns = element_binary_patterns()
```

注意事项：

- 返回顺序固定为 `add -> sub -> mul -> div -> truediv -> eq -> ne -> lt -> le -> gt -> ge`。
- `_lower_typed_element_binary_pattern(...)` 与 `_lower_element_binary_op(...)` 只属于内部共享 helper，不属于公开合同。
- 返回列表中不得出现 family dispatcher pattern 或 `lower_element_binary_family` 兼容入口。

返回与限制：

- 返回可直接传入 `GreedyRewritePatternApplier` 的 `RewritePattern` 列表。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/element_binary_add.py`](../../../../test/pass/nn_lowering/element_binary_add.py)
  - [`test/pass/nn_lowering/element_binary_sub.py`](../../../../test/pass/nn_lowering/element_binary_sub.py)
  - [`test/pass/nn_lowering/element_binary_mul.py`](../../../../test/pass/nn_lowering/element_binary_mul.py)
  - [`test/pass/nn_lowering/element_binary_div.py`](../../../../test/pass/nn_lowering/element_binary_div.py)
  - [`test/pass/nn_lowering/element_binary_truediv.py`](../../../../test/pass/nn_lowering/element_binary_truediv.py)
  - [`test/pass/nn_lowering/element_compare_eq.py`](../../../../test/pass/nn_lowering/element_compare_eq.py)
  - [`test/pass/nn_lowering/element_compare_ne.py`](../../../../test/pass/nn_lowering/element_compare_ne.py)
  - [`test/pass/nn_lowering/element_compare_lt.py`](../../../../test/pass/nn_lowering/element_compare_lt.py)
  - [`test/pass/nn_lowering/element_compare_le.py`](../../../../test/pass/nn_lowering/element_compare_le.py)
  - [`test/pass/nn_lowering/element_compare_gt.py`](../../../../test/pass/nn_lowering/element_compare_gt.py)
  - [`test/pass/nn_lowering/element_compare_ge.py`](../../../../test/pass/nn_lowering/element_compare_ge.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](../../../../test/pass/nn_lowering/test_nn_lowering_private_helpers.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/element_binary_add.py`
  - `pytest -q test/pass/nn_lowering/element_binary_sub.py`
  - `pytest -q test/pass/nn_lowering/element_binary_mul.py`
  - `pytest -q test/pass/nn_lowering/element_binary_div.py`
  - `pytest -q test/pass/nn_lowering/element_binary_truediv.py`
  - `pytest -q test/pass/nn_lowering/element_compare_eq.py`
  - `pytest -q test/pass/nn_lowering/element_compare_ne.py`
  - `pytest -q test/pass/nn_lowering/element_compare_lt.py`
  - `pytest -q test/pass/nn_lowering/element_compare_le.py`
  - `pytest -q test/pass/nn_lowering/element_compare_gt.py`
  - `pytest -q test/pass/nn_lowering/element_compare_ge.py`
  - `pytest -q test/pass/nn_lowering/public_name.py -k patterns`
  - `pytest -q test/pass/nn_lowering/test_nn_lowering_private_helpers.py -k element_binary`
- 测试目标：
  - 验证每个 element binary / compare op 都由独立 pattern 处理，且 kind 映射一致。
  - 验证 add/sub 静态 `memory + memory` case 的最小稳定输出为 `dma.alloc + kernel.binary_elewise + func.return`。
  - 验证 add/sub 符号维度 case 在 `dma.alloc` 前逐维生成 `symbol.get_dim`。
  - 验证 mixed scalar element binary 先物化 `dma.fill`，mixed compare 先物化 `dma.broadcast`。
  - 验证 `public_name.py` 中的主 driver 顺序已不再包含 family dispatcher pattern。
- 功能与用例清单：
  - `test_lower_add_to_kernel_binary_elewise`
  - `test_lower_sub_to_kernel_binary_elewise`
  - `test_lower_mul_to_kernel_binary_elewise`
  - `test_lower_div_to_kernel_binary_elewise`
  - `test_lower_truediv_to_kernel_binary_elewise`
  - `test_lower_eq_mixed_compare_to_kernel_binary_elewise`
  - `test_lower_ne_to_kernel_binary_elewise`
  - `test_lower_lt_to_kernel_binary_elewise`
  - `test_lower_le_to_kernel_binary_elewise`
  - `test_lower_gt_to_kernel_binary_elewise`
  - `test_lower_ge_to_kernel_binary_elewise`
  - `test_element_binary_lowering_helpers`
