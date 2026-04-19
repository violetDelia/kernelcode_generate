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

## 依赖

- Pass 管理：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- NN dialect：[`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../spec/dialect/symbol.md)

## 目标

- 提供唯一公开入口 `NnLoweringPass`，并保持 `name == "lower-nn"`。
- 将支持的 `nn` op lower 为 `kernel/dma` op，输出 Memory 通过 `dma.alloc` 显式创建。
- 输出 module 不应再包含 `nn` op。
- 明确 `kernel.binary_elewise` 与 `kernel.reduce` 的公开合同已就绪，并在测试中验证可用性。
- `lower-nn` 为唯一公开 pass 名称，对外不再保留旧名入口。

## 限制与边界

- 仅支持以下 `nn` op 的 lowering：
  - 逐元素：`nn.add`/`nn.sub`/`nn.mul`/`nn.div`/`nn.truediv`、`nn.eq`/`nn.ne`/`nn.lt`/`nn.le`/`nn.gt`/`nn.ge`、`nn.select`、`nn.cast`
  - 结构化：`nn.broadcast`、`nn.transpose`、`nn.exp`、`nn.reduce_sum`/`nn.reduce_min`/`nn.reduce_max`、`nn.matmul`、`nn.img2col1d`/`nn.img2col2d`
- `nn.truediv` 与 `nn.div` 在 pass 层统一 lower 为 `kernel.binary_elewise(kind="div")`。
- `nn.broadcast` / `nn.transpose` 必须 lower 为 `dma.broadcast` / `dma.transpose`。
- `nn.exp` / `nn.reduce_*` / `nn.matmul` / `nn.img2col*` 必须 lower 为具名 `kernel.*` op。
- `nn` 逐元素/比较类 op 必须 lower 为 `kernel.binary_elewise`，`kind` 与原 op 语义一致。
- `nn` 逐元素/比较类 op 的结果 memory 分配规则：
  - 当结果 `shape` 全为静态整型维度时，`dma.alloc` 可直接使用空的 dynamic shape operand；此时 lowering 不要求先出现 `symbol.get_dim`。
  - 当结果 `shape` 含符号维度时，必须按结果 rank 逐维生成 `symbol.get_dim`，并在 `dma.alloc` 之前按顺序传入这些符号值。
- `nn.exp` lowering 规则：
  - 目标 op 固定为 `kernel.exp`，并把结果写入 `out` operand。
  - `out` 必须由 `dma.alloc` 创建；输入与输出的 `shape/stride/element_type/space` 必须一致，否则抛出 `NnLoweringError`。
- `nn.reduce_sum/min/max` lowering 规则：
  - 目标 op 固定为 `kernel.reduce`，`kind` 取值分别为 `"sum" / "min" / "max"`。
  - `axis/keepdim` 直接继承 `nn.reduce_*` 的语义；`out` 仅消费已有结果 memory，不得改写为 `kernel.reduce_sum/min/max`。
  - `out` 的 `shape/stride/element_type/space` 必须满足 reduce 合同，否则抛出 `NnLoweringError`。
- `nn.softmax` 不在 `lower-nn` 内直接 lowering：
  - 进入本 pass 前必须先由上游 helper/分解 pass 展开为公开稳定链路。
  - 若仍直接命中 `nn.softmax`，必须抛出 `NnLoweringError`，错误信息需明确要求“先分解再进入 lower-nn”。
- `nn.matmul` lowering 规则：
  - 目标 op 固定为 `kernel.matmul`，并把结果写入 `out` operand。
  - 动态维度只能来源于 `symbol.get_dim` 或显式 `!symbol.int<"...">`；不允许把 `i32/index` 直接作为动态维度来源。
  - `out` 的 `shape/stride/element_type/space` 必须与 matmul 合同一致，否则抛出 `NnLoweringError`。
- `nn.img2col1d/nn.img2col2d` lowering 规则：
  - 目标 op 固定为 `kernel.img2col1d` / `kernel.img2col2d`。
  - `kw/kh/sw/sh/dw/dh/pl/pr/ph/pw` 在进入 lowering 时必须是 `!symbol.int<"...">` 值；不接受 `i32/index` 或整数 attribute 直接作为 operand。
  - 动态输出维度必须由 `symbol.get_dim` 或显式 `!symbol.int<"...">` 组合得出。
- `nn` 结果 Memory 必须通过 `dma.alloc` 显式创建；不允许隐式分配或省略输出写入。
- 动态符号维的 broadcast 约束：
  - `result.shape` 中的每个符号维必须能在 `input.shape` 中找到同名维度。
  - 不支持把 singleton 维扩张为“新引入的符号维”；违反时必须报错，错误信息必须包含关键短语 `NnLoweringBroadcastSymbolDimNotFromSource`。
- mixed compare 的桥接规则：
  - `memory + memory` compare：直接 lower 为 `kernel.binary_elewise(kind=...)`，且 `shape/stride/space/element_type` 必须一致。
  - `memory + symbol/const` compare：必须先用 `dma.alloc + dma.broadcast` 物化为 temporary memory，再进行 compare；禁止 `kernel` 比较 op 直接接收非 memory operand。
- element binary mixed operand 的桥接规则：
  - `memory + memory` 的静态 add/sub case，应以 `dma.alloc + kernel.binary_elewise + func.return` 作为最小稳定输出序列。
  - `memory + symbol/const` 的 element binary（如 add/sub/mul/div/truediv）必须先物化 `dma.alloc + dma.fill` temporary memory，再执行 `kernel.binary_elewise`；不允许回退为 `dma.broadcast`。
  - 结果含符号维度时，允许在 `dma.alloc` 前按 rank 顺序生成 `symbol.get_dim` 以构造 dynamic shape operand，但 mixed scalar binary 的物化路径仍固定为 `dma.fill`。
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

- 文件职责与 child spec 边界：
  - `nn_lowering.py`：唯一公开 pass、调度顺序、顶层遍历、错误汇总。
  - `nn_lowering_utility.py`：公共校验与 helper（module/space/result/operand 等）。
  - `element_binary_lowering.py`：`nn.add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge` 的 lowering。
  - `select_cast_lowering.py`：`nn.select` / `nn.cast` 的 lowering。
  - 对应 child spec：`nn_lowering_utility.md`、`element_binary_lowering.md`、`select_cast_lowering.md`。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/public_name.py`](../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/public_name.py`
  - `pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py`
  - `pytest -q test/pass/nn_lowering`
- 测试目标：
  - 验证 `NnLoweringPass` 的公开名字与导出路径稳定（以 `public_name.py` 为稳定入口）。
  - 验证 `NnLoweringError` 与 `NnLoweringPass` 的公共导出可用。
  - 验证 `kernel.binary_elewise` 与 `kernel.reduce` 在 lowering 输出中可解析与可校验。
  - 验证 add/sub 的静态 `memory + memory` lowering 不把 `symbol.get_dim` 作为必现前置行。
  - 验证 add/sub 的符号维度 lowering 在 `dma.alloc` 前按维度生成 `symbol.get_dim`。
  - 验证 `nn.exp` -> `kernel.exp` 的 lowering 目标与输出消费链路。
  - 验证 `nn.reduce_sum/min/max` -> `kernel.reduce(kind=...)` 的 lowering 目标与 `axis/keepdim` 传递。
  - 验证 direct `nn.softmax` 会被拒绝，并提示需先完成分解。
  - 验证 `nn.matmul` -> `kernel.matmul` 的 lowering 目标与输出 memory 约束。
  - 验证 `nn.img2col1d/nn.img2col2d` -> `kernel.img2col1d/kernel.img2col2d` 的 lowering 目标与 symbol.int operand 约束。
- 功能与用例清单：

| 用例 ID | 功能 | 对应测试 |
| --- | --- | --- |
| TC-PASS-NNL-001 | `NnLoweringPass` 公开名称 | `test_nn_lowering_pass_public_name` |
| TC-PASS-NNL-002 | `NnLoweringError` 导出可用 | `test_nn_lowering_pass_public_exports` |
| TC-PASS-NNL-010 | `nn.add` lowering 为 `kernel.binary_elewise(kind="add")` | `test_lower_add_to_kernel` |
| TC-PASS-NNL-011 | `nn.truediv` lowering 为 `kernel.binary_elewise(kind="div")` | `test_lower_div_to_kernel` |
| TC-PASS-NNL-012 | `nn.reduce_min` lowering 为 `kernel.reduce(kind="min")` | `test_lower_reduce_min_to_kernel` |
| TC-PASS-NNL-013 | `nn.reduce_sum` lowering 为 `kernel.reduce(kind="sum")` | `test_lower_reduce_sum_to_kernel` |
| TC-PASS-NNL-014 | `nn.reduce_max` lowering 为 `kernel.reduce(kind="max")` | `test_lower_reduce_max_to_kernel` |
| TC-PASS-NNL-020 | direct `nn.softmax` 需先分解后再进入 `lower-nn` | `test_lower_softmax_requires_decompass` |
| TC-PASS-NNL-021 | `nn.matmul` lowering 目标为 `kernel.matmul` | `test_lower_matmul_to_kernel` |
| TC-PASS-NNL-022 | `nn.img2col1d` lowering 目标为 `kernel.img2col1d` | `test_lower_img2col1d_to_kernel` |
| TC-PASS-NNL-023 | `nn.img2col2d` lowering 目标为 `kernel.img2col2d` | `test_lower_img2col2d_to_kernel` |
