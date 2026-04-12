# nn_lowering.md

## 功能简介

- 定义将 `nn` dialect IR lower 到 `dma/kernel` dialect IR 的 pass 规范。
- 结果 Memory 必须由 `dma.alloc` 创建，并由 `kernel/dma` op 写入 `outs(...)`。
- 该 pass 只负责 op rewrite，不承担高层 helper 分解或跨函数优化。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/lowering/nn_lowering.md`](../../../spec/pass/lowering/nn_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/public_name.py`](../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/test_lowering_nn_to_kernel.py`](../../../test/pass/test_lowering_nn_to_kernel.py)

## 依赖

- Pass 管理：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- NN dialect：[`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../spec/dialect/symbol.md)

## 目标

- 提供新的公开入口 `NnLoweringPass`，并保持 `name == "lower-nn"`。
- 将支持的 `nn` op lower 为 `kernel/dma` op，输出 Memory 通过 `dma.alloc` 显式创建。
- 输出 module 不应再包含 `nn` op。
- 明确 `kernel.binary_elewise` 与 `kernel.reduce` 的公开合同已就绪，并在测试中验证可用性。
- `lower-nn` 为公开 pass 名称；`lower-nn-to-kernel` 仅用于历史兼容与命名回归测试，不作为 expectation 执行入口。

## 限制与边界

- 仅支持以下 `nn` op 的 lowering：
  - 逐元素：`nn.add`/`nn.sub`/`nn.mul`/`nn.div`/`nn.truediv`、`nn.eq`/`nn.ne`/`nn.lt`/`nn.le`/`nn.gt`/`nn.ge`、`nn.select`、`nn.cast`
  - 结构化：`nn.broadcast`、`nn.broadcast_to`、`nn.transpose`、`nn.exp`、`nn.softmax`、`nn.reduce_sum`/`nn.reduce_min`/`nn.reduce_max`、`nn.matmul`、`nn.img2col1d`/`nn.img2col2d`
- `nn.truediv` 与 `nn.div` 在 pass 层统一 lower 为 `kernel.binary_elewise(kind="div")`。
- `nn.broadcast` / `nn.broadcast_to` 必须 lower 为 `dma.broadcast`。
- `nn.transpose` 必须 lower 为 `dma.transpose`。
- `nn.exp` / `nn.softmax` / `nn.reduce_*` / `nn.matmul` / `nn.img2col*` 必须 lower 为具名 `kernel.*` op。
- `nn` 结果 Memory 必须通过 `dma.alloc` 显式创建；不允许隐式分配或省略输出写入。
- broadcast / broadcast_to 的动态符号维约束：
  - `result.shape` 中的每个符号维必须能在 `input.shape` 中找到同名维度，或来自显式 `symbol.get_dim` 的结果。
  - 不支持把 singleton 维扩张为“新引入的符号维”；违反时必须报错，错误信息必须包含关键短语 `LowerNnToKernelBroadcastSymbolDimNotFromSource`。
  - `dma.alloc` 的动态维顺序必须与结果类型一致，并复用 `input.shape` 对应的符号维或 `symbol.get_dim` 结果。
- transpose 的动态维约束：
  - `dma.alloc` 的动态维顺序必须与结果类型一致，并按 `perm` 顺序从输入维度取值。
  - `perm` 必须覆盖输入 rank 且与输出 rank 一致；不一致时必须报错。
- mixed compare 的桥接规则：
  - `memory + memory` compare：直接 lower 为 `kernel` 比较类 op，且 `shape/stride/space/element_type` 必须一致。
  - `memory + symbol/const` compare：必须先用 `dma.alloc + dma.broadcast` 物化为 temporary memory，再进行 compare；禁止 `kernel` 比较 op 直接接收非 memory operand。
- 遇到不支持的 op、结果类型非法、缺失 `nn.space`、operand 数量不匹配或 kernel 校验失败时，必须抛出 `NnLoweringError` 并终止。

## 公开接口

### `class NnLoweringPass(Pass)`

功能说明：

- 表示 `nn -> kernel/dma` lowering pass。
- 通过 `run(module)` 执行 lowering。

参数说明：

- `name(str)`：固定为 `"lower-nn"`。

使用示例：

```python
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass

module = NnLoweringPass().run(module)
```

注意事项：

- pass 仅对 `func.func` 中的 `nn` op 生效。
- 输出 Memory 由 `dma.alloc` 创建，并作为 `kernel/dma` op 的 `out` operand。

返回与限制：

- 返回 lowering 后的 module。
- 若出现不支持的 op 或校验失败，必须抛出 `NnLoweringError`。

### `NnLoweringPass.run(module)`

功能说明：

- 对输入 module 执行 `nn -> kernel/dma` lowering。

参数说明：

- `module (builtin.module)`：包含 `func.func` 的 IR module。

使用示例：

```python
module = NnLoweringPass().run(module)
```

注意事项：

- `module` 不是 `builtin.module` 时必须抛出 `NnLoweringError`。
- 若 module 无 `func.func`，允许直接返回原 module。

返回与限制：

- 返回 lowering 后的 module。

### `class NnLoweringError(ValueError)`

功能说明：

- 表示 `nn_lowering` 过程中的错误类型。

参数说明：

- `message(str)`：错误信息。

使用示例：

```python
raise NnLoweringError("module must be builtin.module")
```

注意事项：

- 对底层异常应保留可诊断信息。

返回与限制：

- 该错误用于终止 pass。

### `ensure_module_op(module)`

功能说明：

- 校验并返回 `builtin.module` 类型的 module。

参数说明：

- `module(Operation)`：待校验对象。

使用示例：

```python
module_op = ensure_module_op(module)
```

注意事项：

- `module` 不是 `builtin.module` 或 `module.ops` 不可遍历时必须抛出 `NnLoweringError`。

返回与限制：

- 返回 `ModuleOp`。

## 额外补充

- S2 可改清单（仅收口 element binary / compare / select / cast family）：
  - `kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`
  - `test/pass/nn_lowering/element_binary_*.py`
  - `test/pass/nn_lowering/element_compare_*.py`
  - `test/pass/nn_lowering/select.py`
  - `test/pass/nn_lowering/cast.py`
  - `test/pass/nn_lowering/public_name.py`
  - `test/pass/test_lowering_nn_to_kernel.py`
- expectation 入口：统一使用 `lower-nn` pass；`lower-nn-to-kernel` 仅用于兼容性验证与命名回归测试。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/public_name.py`](../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/test_lowering_nn_to_kernel.py`](../../../test/pass/test_lowering_nn_to_kernel.py)
  - [`test/pass/nn_lowering/element_binary_add.py`](../../../test/pass/nn_lowering/element_binary_add.py)
  - [`test/pass/nn_lowering/element_binary_sub.py`](../../../test/pass/nn_lowering/element_binary_sub.py)
  - [`test/pass/nn_lowering/element_binary_mul.py`](../../../test/pass/nn_lowering/element_binary_mul.py)
  - [`test/pass/nn_lowering/element_binary_div.py`](../../../test/pass/nn_lowering/element_binary_div.py)
  - [`test/pass/nn_lowering/element_binary_truediv.py`](../../../test/pass/nn_lowering/element_binary_truediv.py)
  - [`test/pass/nn_lowering/element_compare_eq.py`](../../../test/pass/nn_lowering/element_compare_eq.py)
  - [`test/pass/nn_lowering/element_compare_ne.py`](../../../test/pass/nn_lowering/element_compare_ne.py)
  - [`test/pass/nn_lowering/element_compare_lt.py`](../../../test/pass/nn_lowering/element_compare_lt.py)
  - [`test/pass/nn_lowering/element_compare_le.py`](../../../test/pass/nn_lowering/element_compare_le.py)
  - [`test/pass/nn_lowering/element_compare_gt.py`](../../../test/pass/nn_lowering/element_compare_gt.py)
  - [`test/pass/nn_lowering/element_compare_ge.py`](../../../test/pass/nn_lowering/element_compare_ge.py)
  - [`test/pass/nn_lowering/select.py`](../../../test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](../../../test/pass/nn_lowering/cast.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/public_name.py`
  - `pytest -q test/pass/test_lowering_nn_to_kernel.py -k rename`
  - `pytest -q test/pass/test_lowering_nn_to_kernel.py -k public_contract`
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
  - `pytest -q test/pass/nn_lowering/select.py`
  - `pytest -q test/pass/nn_lowering/cast.py`
- 测试目标：
  - 验证 `NnLoweringPass` 的公开名字与导出路径稳定。
  - 验证 `NnLoweringError` 与 `NnLoweringPass` 的公共导出可用。
  - 验证 `NnLoweringPass` 在公共入口层面可见且可调用。
  - 验证 `kernel.binary_elewise` 与 `kernel.reduce` 的公开合同可解析与可校验。
  - 验证 element binary/compare/select/cast family 的 lowering 目标一致，且 `nn.div/nn.truediv` 统一使用 `kernel.binary_elewise(kind="div")`。
- 功能与用例清单：

| 用例 ID | 功能 | 对应测试 |
| --- | --- | --- |
| TC-PASS-NNL-001 | `NnLoweringPass` 公开名称 | `test_nn_lowering_pass_public_name` |
| TC-PASS-NNL-002 | `NnLoweringError` 导出可用 | `test_nn_lowering_pass_public_exports` |
| TC-PASS-N2K-031 | `nn_lowering` 入口暴露 | `test_rename_exposes_nn_lowering_pass` |
| TC-PASS-NNL-S2-001 | element binary add/sub/mul lower 为 `kernel.binary_elewise` | `element_binary_add.py` / `element_binary_sub.py` / `element_binary_mul.py` |
| TC-PASS-NNL-S2-002 | `nn.div`/`nn.truediv` lower 为 `kernel.binary_elewise(kind="div")` | `element_binary_div.py` / `element_binary_truediv.py` |
| TC-PASS-NNL-S2-003 | element compare lower 为 `kernel.binary_elewise` | `element_compare_eq.py` / `element_compare_ne.py` / `element_compare_lt.py` / `element_compare_le.py` / `element_compare_gt.py` / `element_compare_ge.py` |
| TC-PASS-NNL-S2-004 | `nn.select`/`nn.cast` lower 为 `dma.alloc + kernel.select/dma.cast` | `select.py` / `cast.py` |
