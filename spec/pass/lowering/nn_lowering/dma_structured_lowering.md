# dma_structured_lowering.md

## 功能简介

- 定义 `nn_lowering` 中 dma structured family 的拆分规范。
- 负责 `nn.broadcast` / `nn.transpose` 的 lowering 语义。
- 模块级公开入口只保留 `dma_structured_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## API 列表

- `dma_structured_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](../../../../spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
- `test`：
  - [`test/passes/lowering/nn_lowering/test_nn_lowering.py`](../../../../test/passes/lowering/nn_lowering/test_nn_lowering.py)
  - [`test/passes/lowering/nn_lowering/test_public_name.py`](../../../../test/passes/lowering/nn_lowering/test_public_name.py)

## 依赖

- 总规范：[`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- NN dialect：[`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 通过 `dma_structured_patterns()` 提供 `nn.broadcast` / `nn.transpose` 的单 op `RewritePattern` 集合。
- 保证 broadcast/transpose 的输出由 `dma.alloc` 创建并写入。
- 动态维度必须来源于 `symbol.get_dim` 或已有 `symbol.int`，禁止引入新的符号维度。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 仅覆盖 `nn.broadcast`、`nn.transpose`。
- `nn.broadcast` 必须 lower 为 `dma.alloc + dma.broadcast`。
- `nn.transpose` 必须 lower 为 `dma.alloc + dma.transpose`，并校验 `perm`；输出 memory stride 必须保持物化后的默认连续布局。
- 广播若引入新的符号维度，必须报错且错误信息包含 `NnLoweringBroadcastSymbolDimNotFromSource`。
- 模块级 surviving 接口只允许 `dma_structured_patterns()`；`lower_dma_structured_family` 不属于公开入口。
- 每个 op 都必须由独立的 `@op_type_rewrite_pattern` 处理，不再通过 `block/op -> bool` family 分发。
## API详细说明

### `dma_structured_patterns() -> list[RewritePattern]`

- api：`dma_structured_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering.dma_structured_lowering import (
      dma_structured_patterns,
  )

  patterns = dma_structured_patterns()
  ```
- 功能说明：返回 dma structured family 的有序 pattern 列表，供 `nn_lowering_patterns()` 直接拼接到主 driver 中。
- 注意事项：返回顺序固定为 `nn.broadcast` pattern 在前、`nn.transpose` pattern 在后；内部 helper 可复用 `symbol.get_dim` / `dma.alloc` 构造逻辑，但这些 helper 不属于公开接口；返回列表中不得保留 `lower_dma_structured_family` 兼容入口；返回值可直接传入 `GreedyRewritePatternApplier`。

## 测试

- 测试文件：
  - `test/passes/lowering/nn_lowering/test_nn_lowering.py`
  - `test/passes/lowering/nn_lowering/test_public_name.py`
- 执行命令：
  - `pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k "broadcast or transpose"`
  - `pytest -q test/passes/lowering/nn_lowering/test_public_name.py -k patterns`

### 测试目标

- 验证 `spec/pass/lowering/nn_lowering/dma_structured_lowering.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-001 | pass 改写 | `test_lower_broadcast_dma` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_broadcast_dma`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_broadcast_dma`”场景。 | `test_lower_broadcast_dma` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-002 | pass 改写 | `test_lower_transpose_to_kernel` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_transpose_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_transpose_to_kernel`”场景。 | `test_lower_transpose_to_kernel` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-003 | pass 改写 | `test_lower_broadcast_with_symbol_dim` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_broadcast_with_symbol_dim`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_broadcast_with_symbol_dim`”场景。 | `test_lower_broadcast_with_symbol_dim` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-004 | pass 改写 | `test_lower_broadcast_with_implicit_expand` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_broadcast_with_implicit_expand`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_broadcast_with_implicit_expand`”场景。 | `test_lower_broadcast_with_implicit_expand` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-005 | 边界/异常 | `test_lower_broadcast_rejects_unknown_dim` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_lower_broadcast_rejects_unknown_dim`。 | “`test_lower_broadcast_rejects_unknown_dim`”场景按公开错误语义失败或被拒绝。 | `test_lower_broadcast_rejects_unknown_dim` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-006 | pass 改写 | `test_lower_transpose_dynamic` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_transpose_dynamic`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_transpose_dynamic`”场景。 | `test_lower_transpose_dynamic` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-007 | 边界/异常 | `test_lower_broadcast_rejects_invalid_shape` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_lower_broadcast_rejects_invalid_shape`。 | “`test_lower_broadcast_rejects_invalid_shape`”场景按公开错误语义失败或被拒绝。 | `test_lower_broadcast_rejects_invalid_shape` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-008 | 边界/异常 | `test_broadcast_rejects_invalid_scalar` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_broadcast_rejects_invalid_scalar`。 | “`test_broadcast_rejects_invalid_scalar`”场景按公开错误语义失败或被拒绝。 | `test_broadcast_rejects_invalid_scalar` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-009 | pass 改写 | `test_lower_broadcast_public_dynamic_dim_and_scalar_matrix` | 准备包含 block symbol、已有 `symbol.get_dim`、source 符号复用和 scalar operand 的公开 IR 输入。 | 通过公开 `NnLoweringPass.apply(...)` 运行 lowering。 | 生成 `dma.alloc + dma.broadcast`，动态维度来源于 block 参数、既有 symbol SSA 或 source `symbol.get_dim`，int/symbol scalar operand 不被误拒绝。 | `test_lower_broadcast_public_dynamic_dim_and_scalar_matrix` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-010 | 边界/异常 | `test_lower_broadcast_public_error_matrix` | 准备 rank、symbol 来源、operand 类型和 operand 数量非法的公开 IR 输入。 | 通过公开 `NnLoweringPass.apply(...)` 运行 lowering。 | 按稳定 `KernelCodeError` 文本拒绝非法 broadcast 输入。 | `test_lower_broadcast_public_error_matrix` |
| TC-PASS-LOWERING-NN-LOWERING-DMA-STRUCTURED-LOWERING-011 | 边界/异常 | `test_lower_transpose_public_error_matrix` | 准备 operand 类型、perm、rank 与符号来源非法的公开 IR 输入。 | 通过公开 `NnLoweringPass.apply(...)` 运行 lowering。 | 按稳定 `KernelCodeError` 文本拒绝非法 transpose 输入。 | `test_lower_transpose_public_error_matrix` |
