# reduce_softmax_lowering.md

## 功能简介

- 为 `nn.reduce_*` 提供单 op pattern lowering 入口，输出 `kernel.reduce` 形态，并补齐 `dma.alloc`。
- 对 direct `nn.softmax` 提供稳定拒绝路径，要求先由上游完成分解。
- 模块级公开入口只保留 `reduce_softmax_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## API 列表

- `reduce_softmax_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
- `test`：
  - [`test/passes/lowering/nn_lowering/test_reduce_lowering.py`](../../../../test/passes/lowering/nn_lowering/test_reduce_lowering.py)
  - [`test/passes/lowering/nn_lowering/test_nn_lowering.py`](../../../../test/passes/lowering/nn_lowering/test_nn_lowering.py)
  - [`test/passes/lowering/nn_lowering/test_public_name.py`](../../../../test/passes/lowering/nn_lowering/test_public_name.py)

## 依赖

- [`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- [`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- [`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- [`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)

## 目标

- 通过 `reduce_softmax_patterns()` 提供 reduce family 与 softmax reject 的单 op `RewritePattern` 集合。
- 保持 `axis`、`keepdim` 等属性校验与输出一致。
- 保持 `nn.exp` 已迁入 `select_cast_lowering.py`，不再由本模块承接。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 主注册入口仅覆盖 `nn.reduce_sum`、`nn.reduce_min`、`nn.reduce_max` 与 direct `nn.softmax` 拒绝。
- `nn.reduce_*` 仅支持单轴 `axes`，且 `keepdim` 需为 0/1。
- `nn.softmax` 需在进入本层前先完成分解；本文件不承诺 softmax 的 direct lowering。
- 模块级 surviving 接口只允许 `reduce_softmax_patterns()`；`lower_reduce_softmax_family` 不属于公开入口。
- 每个 reduce op 与 softmax reject 都必须由独立的 `@op_type_rewrite_pattern` 处理，不再通过 family dispatcher 做名称分发。
## API详细说明

### `reduce_softmax_patterns() -> list[RewritePattern]`

- api：`reduce_softmax_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering.reduce_softmax_lowering import (
      reduce_softmax_patterns,
  )

  patterns = reduce_softmax_patterns()
  ```
- 功能说明：返回 `nn.reduce_sum`、`nn.reduce_min`、`nn.reduce_max` 与 direct `nn.softmax` 拒绝 pattern 的有序列表，供 `nn_lowering_patterns()` 直接拼接到主 driver 中。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；`nn.softmax` pattern 只负责抛出 `KernelCodeError("nn.softmax must be decomposed before lower-nn")`；返回列表中不得保留 `lower_reduce_softmax_family` 兼容入口；`nn.exp` 不属于本模块的 pattern 列表；返回值可直接传入 `GreedyRewritePatternApplier`。

## 测试

- 测试文件：
  - `test/passes/lowering/nn_lowering/test_nn_lowering.py`
  - `test/passes/lowering/nn_lowering/test_public_name.py`
  - `test/passes/lowering/nn_lowering/test_reduce_lowering.py`
- 执行命令：
  - `pytest -q test/passes/lowering/nn_lowering/test_reduce_lowering.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py -k "reduce or softmax"`
  - `pytest -q test/passes/lowering/nn_lowering/test_public_name.py -k patterns`

### 测试目标

- 验证 `spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-LOWERING-NN-LOWERING-REDUCE-SOFTMAX-LOWERING-001 | pass 改写 | `test_nn_lowering_reduce_ircheck` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_reduce_ircheck`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_reduce_ircheck`”场景。 | `test_nn_lowering_reduce_ircheck` |
| TC-PASS-LOWERING-NN-LOWERING-REDUCE-SOFTMAX-LOWERING-002 | 边界/异常 | `test_nn_lowering_reduce_shape_mismatch` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_lowering_reduce_shape_mismatch`。 | “`test_nn_lowering_reduce_shape_mismatch`”场景按公开错误语义失败或被拒绝。 | `test_nn_lowering_reduce_shape_mismatch` |
| TC-PASS-LOWERING-NN-LOWERING-REDUCE-SOFTMAX-LOWERING-003 | 边界/异常 | `test_lower_softmax_requires_decompass` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_lower_softmax_requires_decompass`。 | “`test_lower_softmax_requires_decompass`”场景按公开错误语义失败或被拒绝。 | `test_lower_softmax_requires_decompass` |
| TC-PASS-LOWERING-NN-LOWERING-REDUCE-SOFTMAX-LOWERING-004 | 公开入口 | `test_reduce_axes_validation` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_reduce_axes_validation`。 | 公开入口在“`test_reduce_axes_validation`”场景下可导入、构造、注册或按名称发现。 | `test_reduce_axes_validation` |
| TC-PASS-LOWERING-NN-LOWERING-REDUCE-SOFTMAX-LOWERING-005 | 符号语义 | `test_reduce_keepdim_validation` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_reduce_keepdim_validation`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`test_reduce_keepdim_validation`”场景。 | `test_reduce_keepdim_validation` |
| TC-PASS-LOWERING-NN-LOWERING-REDUCE-SOFTMAX-LOWERING-006 | 边界/异常 | `test_softmax_requires_decompass_before_axis_validation` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_softmax_requires_decompass_before_axis_validation`。 | “`test_softmax_requires_decompass_before_axis_validation`”场景按公开错误语义失败或被拒绝。 | `test_softmax_requires_decompass_before_axis_validation` |
