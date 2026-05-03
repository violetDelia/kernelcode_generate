# matmul_img2col_lowering.md

## 功能简介

- 统一处理 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d` 的 lowering 逻辑。
- 输出固定为 `kernel.matmul`、`kernel.img2col1d`、`kernel.img2col2d`，并通过 `dma.alloc` 创建结果 memory。
- 模块级公开入口只保留 `matmul_img2col_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## API 列表

- `matmul_img2col_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](../../../../spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
- `test`：
  - [`test/passes/lowering/nn_lowering/test_matmul.py`](../../../../test/passes/lowering/nn_lowering/test_matmul.py)
  - [`test/passes/lowering/nn_lowering/test_img2col1d.py`](../../../../test/passes/lowering/nn_lowering/test_img2col1d.py)
  - [`test/passes/lowering/nn_lowering/test_img2col2d.py`](../../../../test/passes/lowering/nn_lowering/test_img2col2d.py)
  - [`test/passes/lowering/nn_lowering/test_public_name.py`](../../../../test/passes/lowering/nn_lowering/test_public_name.py)
  - [`test/passes/lowering/nn_lowering/test_asset_cases.py`](../../../../test/passes/lowering/nn_lowering/test_asset_cases.py)

## 依赖

- 总规范：[`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- 公共 helper：[`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- NN dialect：[`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 将 `nn.matmul` lower 为 `kernel.matmul`，结果由 `dma.alloc` 创建；若输出包含符号维度，需从输入插入 `symbol.get_dim` 并作为 `dma.alloc` 的 dynamic shape。
- 将 `nn.img2col1d/nn.img2col2d` lower 为对应的 `kernel.img2col*`，参数必须为 `symbol.int`；若输出含符号维度，需使用 `symbol.get_dim` 与 `symbol` 算术构造 `dma.alloc` 的 dynamic shape。
- `img2col1d/img2col2d` 动态输出 extent 的文本必须沿用 `SymbolDim` 字符串口径；`(expr // stride) + 1` 以 `//` 形式保留，不得回退为 `floor(expr/stride) + 1`。
- 通过 `matmul_img2col_patterns()` 提供单 op `RewritePattern` 集合。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 仅覆盖 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d`。
- `nn.matmul` 仅支持 rank-2 memory，且 stride 必须为连续布局。
- `nn.img2col1d/2d` 的动态参数必须是 `!symbol.int<"...">`，不接受 `i32/index` 或整数 attribute 直接作为 operand。
- 模块级 surviving 接口只允许 `matmul_img2col_patterns()`；`lower_matmul_img2col_family` 不属于公开入口。
- 每个 op 都必须由独立的 `@op_type_rewrite_pattern` 处理，不再通过 family dispatcher 做名称分发。
## API详细说明

### `matmul_img2col_patterns() -> list[RewritePattern]`

- api：`matmul_img2col_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering.matmul_img2col_lowering import (
      matmul_img2col_patterns,
  )

  patterns = matmul_img2col_patterns()
  ```
- 功能说明：返回 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d` 的有序 pattern 列表，供 `nn_lowering_patterns()` 直接拼接到主 driver 中。
- 注意事项：返回顺序固定为 `matmul -> img2col1d -> img2col2d`；输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；`build_*` 或 `_lower_*` 共享 helper 只属于内部实现，不属于公开合同；返回列表中不得保留 `lower_matmul_img2col_family` 兼容入口；返回值可直接传入 `GreedyRewritePatternApplier`。

## 测试

- 测试文件：
  - `test/passes/lowering/nn_lowering/test_asset_cases.py`
  - `test/passes/lowering/nn_lowering/test_img2col1d.py`
  - `test/passes/lowering/nn_lowering/test_img2col2d.py`
  - `test/passes/lowering/nn_lowering/test_matmul.py`
  - `test/passes/lowering/nn_lowering/test_public_name.py`
- 执行命令：
  - `pytest -q test/passes/lowering/nn_lowering/test_asset_cases.py -k "matmul or img2col"`
  - `pytest -q test/passes/lowering/nn_lowering/test_matmul.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_img2col1d.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_img2col2d.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_public_name.py -k patterns`

### 测试目标

- 验证 `spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-001 | pass 改写 | `test_nn_lowering_matmul_target` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_matmul_target`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_matmul_target`”场景。 | `test_nn_lowering_matmul_target` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-002 | pass 改写 | `test_nn_lowering_matmul_inside_symbol_for` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_matmul_inside_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_matmul_inside_symbol_for`”场景。 | `test_nn_lowering_matmul_inside_symbol_for` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-003 | pass 改写 | `test_nn_lowering_img2col1d_target` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_img2col1d_target`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_img2col1d_target`”场景。 | `test_nn_lowering_img2col1d_target` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-004 | pass 改写 | `test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names`”场景。 | `test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-005 | pass 改写 | `test_nn_lowering_img2col2d_target` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_img2col2d_target`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_img2col2d_target`”场景。 | `test_nn_lowering_img2col2d_target` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-006 | pass 改写 | `test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names`”场景。 | `test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-007 | pass 改写 | `test_nn_lowering_asset_case` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_asset_case`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_nn_lowering_asset_case`”场景。 | `test_nn_lowering_asset_case` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-008 | pass 改写 | `test_nn_lowering_matmul_dynamic_output_dims` | 通过公开 `NnMatmulOp` 与 `NnLoweringPass` 构造动态输出维度和符号 stride 的 matmul 输入。 | 运行 `test_nn_lowering_matmul_dynamic_output_dims`。 | 动态输出维度通过 `symbol.get_dim` 接入 `dma.alloc`，并输出 `kernel.matmul`；符号 stride 在非全静态 stride 场景下不触发静态连续性拒绝。 | `test_nn_lowering_matmul_dynamic_output_dims` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-009 | 边界/异常 | `test_nn_lowering_matmul_public_error_matrix` | 通过公开 `NnMatmulOp` 与 `NnLoweringPass` 构造非 memory operand、rank、contracting dim、输出 shape 与 stride 错误。 | 运行 `test_nn_lowering_matmul_public_error_matrix`。 | 非法 matmul 输入按公开 `KernelCodeError` 语义失败。 | `test_nn_lowering_matmul_public_error_matrix` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-010 | 边界/异常 | `test_nn_lowering_img2col1d_public_error_matrix` | 通过公开 `NnImg2col1dOp` 与 `NnLoweringPass` 构造非法参数类型、静态源轴动态输出和非法结果 rank。 | 运行 `test_nn_lowering_img2col1d_public_error_matrix`。 | 非法 img2col1d 输入按公开 `KernelCodeError` 语义失败。 | `test_nn_lowering_img2col1d_public_error_matrix` |
| TC-PASS-LOWERING-NN-LOWERING-MATMUL-IMG2COL-LOWERING-011 | 边界/异常 | `test_nn_lowering_img2col2d_public_error_matrix` | 通过公开 `NnImg2col2dOp` 与 `NnLoweringPass` 构造非法参数类型、静态源轴动态输出和非法结果 rank。 | 运行 `test_nn_lowering_img2col2d_public_error_matrix`。 | 非法 img2col2d 输入按公开 `KernelCodeError` 语义失败。 | `test_nn_lowering_img2col2d_public_error_matrix` |
