# element_binary_lowering.md

## 功能简介

- 定义 element binary / compare family 的 lowering 责任边界与入口。
- 覆盖 `nn.add/sub/mul/div/truediv` 与 `nn.eq/ne/lt/le/gt/ge`，并输出 `kernel.binary_elewise`。

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

## 依赖

- [`spec/pass/lowering/nn_lowering.md`](../../../../spec/pass/lowering/nn_lowering.md)
- [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- [`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- [`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- [`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- [`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 以单一入口处理 element binary / compare family，并与 `nn_lowering` 总 spec 对齐。
- 保持 `kernel.binary_elewise(kind=...)` 的 kind 语义一致可查。

## 限制与边界

- 仅处理本 family 的 `nn` op；非本 family op 必须返回 `False` 且不改写。
- 本文件不得定义额外 `*Pass` 作为公开入口，执行由 `NnLoweringPass` 统一调度。
- 需要 `dma.broadcast` 桥接的 mixed compare 行为必须遵循总 spec 中的规则。
- `memory + memory` 的静态 add/sub 输出只要求收口到 `dma.alloc + kernel.binary_elewise + func.return`；不把 `symbol.get_dim` 视为必现前置行。
- 结果 shape 含符号维度时，才要求在 `dma.alloc` 前按 rank 顺序生成 `symbol.get_dim`。

## 公开接口

### `lower_element_binary_family(block: Block, op: Operation) -> bool`

功能说明：

- 对 element binary / compare family 执行 lowering。
- 处理成功时返回 `True` 并改写 op；不属于本 family 时返回 `False`。

参数说明：

- `block (Block)`：包含 `op` 的 block。
- `op (Operation)`：待判定的 `nn` op。

使用示例：

```python
if lower_element_binary_family(block, op):
    return
```

注意事项：

- kind 映射必须与总 spec 保持一致：
  - `nn.add/sub/mul/div/truediv` -> `kernel.binary_elewise(kind="add/sub/mul/div/div")`
  - `nn.eq/ne/lt/le/gt/ge` -> `kernel.binary_elewise(kind="eq/ne/lt/le/gt/ge")`
- 静态 `memory + memory` 的 add/sub case，ircheck 合同应从 `dma.alloc` 起锁定稳定顺序，而不是要求 `func.func` 后紧接 `symbol.get_dim`。
- 符号维度 case 的 ircheck 合同必须锁定 `symbol.get_dim(axis=0..n-1) -> dma.alloc -> kernel.binary_elewise -> func.return`。
- mixed compare 需要先物化 `dma.alloc + dma.broadcast`，再写入 `kernel.binary_elewise`。
- 任何空间、结果类型或 operand 校验失败必须抛出 `NnLoweringError`。

返回与限制：

- 返回 `bool`，表示是否完成本 family 的 lowering。

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
- 测试目标：
  - 验证 element binary / compare family 输出为 `kernel.binary_elewise` 且 kind 映射一致。
  - 验证 add/sub 静态 `memory + memory` case 的最小稳定输出为 `dma.alloc + kernel.binary_elewise + func.return`。
  - 验证 add/sub 符号维度 case 在 `dma.alloc` 前逐维生成 `symbol.get_dim`。
  - 验证 mixed compare 先物化 `dma.broadcast` 再写入 `kernel.binary_elewise`。
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
