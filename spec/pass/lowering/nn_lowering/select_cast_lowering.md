# select_cast_lowering.md

## 功能简介

- 规范 `nn.select`、`nn.cast` 与 `nn.exp` 的 lowering 行为与边界。
- 结果 memory 由 `dma.alloc` 创建，并写入 `kernel.select`、`dma.cast` 或 `kernel.exp`。
- 模块级公开入口只保留 `select_cast_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## API 列表

- `select_cast_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/select.py`](../../../../test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](../../../../test/pass/nn_lowering/cast.py)
  - [`test/pass/nn_lowering/exp.py`](../../../../test/pass/nn_lowering/exp.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)

## 依赖

- 总规范：[`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- 工具函数：[`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- NN dialect：[`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 通过 `select_cast_patterns()` 提供 `nn.select`、`nn.cast`、`nn.exp` 的单 op `RewritePattern` 集合。
- 输出 memory 必须显式分配，并在 `kernel.select`、`dma.cast` 或 `kernel.exp` 中消费。
- 保持 `nn.exp` 已迁入本模块，不再由 reduce family 兼容 helper 承接。

## 限制与边界

- 仅覆盖 `nn.select`、`nn.cast`、`nn.exp`。
- 模块级 surviving 接口只允许 `select_cast_patterns()`；`lower_select_cast_family` 不属于公开入口。
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
  - 若触发以下条件必须抛出 `KernelCodeError`：
    - `input` 不是 `nn.memory`：`nn.cast input must be nn.memory`
    - `input` 与结果 rank 不一致：`nn select/cast operand/result rank mismatch`
    - 结果 `shape` 含 `?`：`nn select/cast result shape must not contain '?'`
    - `dma.cast` 校验失败：`dma.cast shape mismatch` / `dma.cast stride mismatch` / `dma.cast space mismatch`
- `nn.exp`：
  - 必须 lower 为 `dma.alloc + kernel.exp`。
  - 输入与输出的 `shape/stride/element_type/space` 必须一致，否则抛出 `KernelCodeError`。
- 若 `dma.alloc`、`kernel.select`、`dma.cast` 或 `kernel.exp` 校验失败，必须抛出 `KernelCodeError` 并中止当前 op 的处理。

## 公开接口

### `select_cast_patterns() -> list[RewritePattern]`

功能说明：

- 返回 `nn.select`、`nn.cast`、`nn.exp` 的有序 pattern 列表。
- 供 `nn_lowering_patterns()` 直接拼接到主 driver 中。

参数说明：

- 无。

使用示例：

```python
from kernel_gen.passes.lowering.nn_lowering.select_cast_lowering import (
    select_cast_patterns,
)

patterns = select_cast_patterns()
```

注意事项：

- 返回顺序固定为 `select -> cast -> exp`。
- `_lower_select_op(...)`、`_lower_cast_op(...)`、`_lower_exp_op(...)` 只属于内部共享 helper，不属于公开合同。
- 返回列表中不得保留 `lower_select_cast_family` 兼容入口。

返回与限制：

- 返回可直接传入 `GreedyRewritePatternApplier` 的 `RewritePattern` 列表。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/select.py`](../../../../test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](../../../../test/pass/nn_lowering/cast.py)
  - [`test/pass/nn_lowering/exp.py`](../../../../test/pass/nn_lowering/exp.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/select.py`
  - `pytest -q test/pass/nn_lowering/cast.py`
  - `pytest -q test/pass/nn_lowering/exp.py`
  - `pytest -q test/pass/nn_lowering/public_name.py -k patterns`
  - `pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -k "select or cast or exp"`
- 测试目标：
  - `nn.select` lower 为 `dma.alloc + kernel.select`。
  - `nn.cast` lower 为 `dma.alloc + dma.cast`。
  - `nn.exp` lower 为 `dma.alloc + kernel.exp`。
  - 输出 memory 由 `dma.alloc` 创建，lowering 后不再出现对应 `nn.*` op。
  - 主 driver 的 pattern 顺序已不再包含 select/cast family dispatcher。
- 功能与用例清单：
  - `test_lower_select_to_kernel_select`
  - `test_lower_cast_to_dma_cast`
  - `test_lower_cast_bfloat16_to_dma_cast`
  - `test_nn_lowering_exp_static`
  - `test_nn_lowering_exp_dynamic`
  - `test_nn_lowering_exp_shape_mismatch`
  - `test_lower_cast_preserves_symbol_dim`
  - `test_select_preserves_symbol_dim`
