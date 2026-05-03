# element_binary_lowering.md

## 功能简介

- 定义 element binary / compare family 的 lowering 责任边界。
- 覆盖 `nn.add/sub/mul/div/truediv` 与 `nn.eq/ne/lt/le/gt/ge`，并输出 `kernel.binary_elewise`。
- 模块级公开入口只保留 `element_binary_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## API 列表

- `element_binary_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
- `test`：
  - [`test/passes/lowering/nn_lowering/test_element_binary_add.py`](../../../../test/passes/lowering/nn_lowering/test_element_binary_add.py)
  - [`test/passes/lowering/nn_lowering/test_element_binary_sub.py`](../../../../test/passes/lowering/nn_lowering/test_element_binary_sub.py)
  - [`test/passes/lowering/nn_lowering/test_element_binary_mul.py`](../../../../test/passes/lowering/nn_lowering/test_element_binary_mul.py)
  - [`test/passes/lowering/nn_lowering/test_element_binary_div.py`](../../../../test/passes/lowering/nn_lowering/test_element_binary_div.py)
  - [`test/passes/lowering/nn_lowering/test_element_binary_truediv.py`](../../../../test/passes/lowering/nn_lowering/test_element_binary_truediv.py)
  - [`test/passes/lowering/nn_lowering/test_element_compare_eq.py`](../../../../test/passes/lowering/nn_lowering/test_element_compare_eq.py)
  - [`test/passes/lowering/nn_lowering/test_element_compare_ne.py`](../../../../test/passes/lowering/nn_lowering/test_element_compare_ne.py)
  - [`test/passes/lowering/nn_lowering/test_element_compare_lt.py`](../../../../test/passes/lowering/nn_lowering/test_element_compare_lt.py)
  - [`test/passes/lowering/nn_lowering/test_element_compare_le.py`](../../../../test/passes/lowering/nn_lowering/test_element_compare_le.py)
  - [`test/passes/lowering/nn_lowering/test_element_compare_gt.py`](../../../../test/passes/lowering/nn_lowering/test_element_compare_gt.py)
  - [`test/passes/lowering/nn_lowering/test_element_compare_ge.py`](../../../../test/passes/lowering/nn_lowering/test_element_compare_ge.py)
  - [`test/passes/lowering/nn_lowering/test_public_name.py`](../../../../test/passes/lowering/nn_lowering/test_public_name.py)
  - [`test/passes/lowering/nn_lowering/test_asset_cases.py`](../../../../test/passes/lowering/nn_lowering/test_asset_cases.py)

## 依赖

- [`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- [`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- [`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- [`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- [`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 通过 `element_binary_patterns()` 提供 element binary / compare family 的单 op `RewritePattern` 集合。
- 为每个受支持 op 固定一个独立 pattern，并复用共享构造 helper 生成 `kernel.binary_elewise(kind=...)`。
- 保持 mixed scalar / mixed compare 的桥接路径与 `nn_lowering` 总 spec 一致。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 仅覆盖 `nn.add`、`nn.sub`、`nn.mul`、`nn.div`、`nn.truediv`、`nn.eq`、`nn.ne`、`nn.lt`、`nn.le`、`nn.gt`、`nn.ge`。
- 本模块不得定义额外 `*Pass` 作为公开入口，执行由 `NnLoweringPass` 统一调度。
- 模块级 surviving 接口只允许 `element_binary_patterns()`；`lower_element_binary_family` 不属于公开入口，外部 caller 不得继续依赖 `block/op -> bool` family 分发。
- 每个 op 都必须由对应的 `@op_type_rewrite_pattern` 独立匹配；不得回退为按字符串名分发的 family placeholder pattern。
- 需要 `dma.broadcast` 桥接的 mixed compare 行为必须遵循总 spec 中的规则。
- `memory + memory` 的静态 add/sub 输出只要求收口到 `dma.alloc + kernel.binary_elewise + func.return`；不把 `symbol.get_dim` 视为必现前置行。
- 结果 shape 含符号维度时，才要求在 `dma.alloc` 前按 rank 顺序生成 `symbol.get_dim`。
- mixed scalar element binary 需要先物化 `dma.alloc + dma.fill`，再写入 `kernel.binary_elewise`；该路径禁止回退为 `dma.broadcast`。
- 任何空间、结果类型或 operand 校验失败必须抛出 `KernelCodeError`。
## API详细说明

### `element_binary_patterns() -> list[RewritePattern]`

- api：`element_binary_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering.element_binary_lowering import (
      element_binary_patterns,
  )

  patterns = element_binary_patterns()
  ```
- 功能说明：返回 element binary / compare family 的有序 pattern 列表，供 `nn_lowering_patterns()` 直接拼接到主 driver 中。
- 注意事项：返回顺序固定为 `add -> sub -> mul -> div -> truediv -> eq -> ne -> lt -> le -> gt -> ge`；`_lower_typed_element_binary_pattern(...)` 与 `_lower_element_binary_op(...)` 只属于内部共享 helper，不属于公开合同；返回列表中不得出现 family dispatcher pattern 或 `lower_element_binary_family` 兼容入口；返回值可直接传入 `GreedyRewritePatternApplier`。

## 测试

- 测试文件：
  - `test/passes/lowering/nn_lowering/test_asset_cases.py`
  - `test/passes/lowering/nn_lowering/test_element_binary_add.py`
  - `test/passes/lowering/nn_lowering/test_element_binary_div.py`
  - `test/passes/lowering/nn_lowering/test_element_binary_mul.py`
  - `test/passes/lowering/nn_lowering/test_element_binary_sub.py`
  - `test/passes/lowering/nn_lowering/test_element_binary_truediv.py`
  - `test/passes/lowering/nn_lowering/test_element_compare_eq.py`
  - `test/passes/lowering/nn_lowering/test_element_compare_ge.py`
  - `test/passes/lowering/nn_lowering/test_element_compare_gt.py`
  - `test/passes/lowering/nn_lowering/test_element_compare_le.py`
  - `test/passes/lowering/nn_lowering/test_element_compare_lt.py`
  - `test/passes/lowering/nn_lowering/test_element_compare_ne.py`
  - `test/passes/lowering/nn_lowering/test_nn_lowering.py`
  - `test/passes/lowering/nn_lowering/test_public_name.py`
- 执行命令：
  - `pytest -q test/passes/lowering/nn_lowering/test_element_binary_add.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_binary_sub.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_binary_mul.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_binary_div.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_binary_truediv.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_compare_eq.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_compare_ne.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_compare_lt.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_compare_le.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_compare_gt.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_element_compare_ge.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k "element_binary_public or compare_public"`
  - `pytest -q test/passes/lowering/nn_lowering/test_public_name.py -k patterns`
  - `pytest -q test/passes/lowering/nn_lowering/test_asset_cases.py -k "element_binary or element_compare"`

### 测试目标

- 验证 `spec/pass/lowering/nn_lowering/element_binary_lowering.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-001 | pass 改写 | `test_lower_add_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_add_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_add_to_kernel_binary_elewise`”场景。 | `test_lower_add_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-002 | pass 改写 | `test_lower_sub_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_sub_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_sub_to_kernel_binary_elewise`”场景。 | `test_lower_sub_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-003 | pass 改写 | `test_lower_mul_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_mul_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_mul_to_kernel_binary_elewise`”场景。 | `test_lower_mul_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-004 | pass 改写 | `test_lower_div_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_div_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_div_to_kernel_binary_elewise`”场景。 | `test_lower_div_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-005 | pass 改写 | `test_lower_truediv_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_truediv_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_truediv_to_kernel_binary_elewise`”场景。 | `test_lower_truediv_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-006 | pass 改写 | `test_lower_eq_mixed_compare_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_eq_mixed_compare_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_eq_mixed_compare_to_kernel_binary_elewise`”场景。 | `test_lower_eq_mixed_compare_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-007 | pass 改写 | `test_lower_ne_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_ne_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_ne_to_kernel_binary_elewise`”场景。 | `test_lower_ne_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-008 | pass 改写 | `test_lower_lt_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_lt_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_lt_to_kernel_binary_elewise`”场景。 | `test_lower_lt_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-009 | pass 改写 | `test_lower_le_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_le_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_le_to_kernel_binary_elewise`”场景。 | `test_lower_le_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-010 | pass 改写 | `test_lower_gt_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_gt_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_gt_to_kernel_binary_elewise`”场景。 | `test_lower_gt_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-011 | pass 改写 | `test_lower_ge_to_kernel_binary_elewise` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_ge_to_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_lower_ge_to_kernel_binary_elewise`”场景。 | `test_lower_ge_to_kernel_binary_elewise` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-012 | pass 改写 | `test_nn_lowering_asset_case` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_asset_case`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_asset_case`”场景。 | `test_nn_lowering_asset_case` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-013 | pass 改写 | `test_lower_element_binary_public_dynamic_scalar_and_symbol_matrix` | 准备动态 shape、左侧 scalar、symbol.const/symbol.add 前置链等公开 IR 输入。 | 通过公开 `NnLoweringPass.apply(...)` 运行 lowering。 | 动态 shape 生成 `symbol.get_dim`，mixed scalar 走 `dma.fill`，symbol 前置链规范化后不残留 `nn.*`。 | `test_lower_element_binary_public_dynamic_scalar_and_symbol_matrix` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-014 | pass 改写 | `test_lower_compare_public_left_scalar_matrix` | 准备左侧 scalar、右侧 memory 的公开 compare IR 输入。 | 通过公开 `NnLoweringPass.apply(...)` 运行 lowering。 | mixed compare scalar 走 `dma.broadcast`，不混入 `dma.fill`。 | `test_lower_compare_public_left_scalar_matrix` |
| TC-PASS-LOWERING-NN-LOWERING-ELEMENT-BINARY-LOWERING-015 | 边界/异常 | `test_lower_element_binary_public_error_matrix` | 准备无 memory、rank 不匹配、`?` result shape、scalar 类型不匹配与 compare 输出类型非法输入。 | 通过公开 `NnLoweringPass.apply(...)` 运行 lowering。 | 按稳定 `KernelCodeError` 文本拒绝非法 element binary / compare 输入。 | `test_lower_element_binary_public_error_matrix` |
