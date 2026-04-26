# matmul_img2col_lowering.md

## 功能简介

- 统一处理 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d` 的 lowering 逻辑。
- 输出固定为 `kernel.matmul`、`kernel.img2col1d`、`kernel.img2col2d`，并通过 `dma.alloc` 创建结果 memory。
- 模块级公开入口只保留 `matmul_img2col_patterns()`；family dispatcher helper 不属于 surviving 公开合同。

## API 列表

- `matmul_img2col_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](../../../../spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
- `test`：
  - [`test/pass/nn_lowering/matmul.py`](../../../../test/pass/nn_lowering/matmul.py)
  - [`test/pass/nn_lowering/img2col1d.py`](../../../../test/pass/nn_lowering/img2col1d.py)
  - [`test/pass/nn_lowering/img2col2d.py`](../../../../test/pass/nn_lowering/img2col2d.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_asset_cases.py`](../../../../test/pass/nn_lowering/test_nn_lowering_asset_cases.py)

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
- 通过 `matmul_img2col_patterns()` 提供单 op `RewritePattern` 集合。

## 限制与边界

- 仅覆盖 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d`。
- `nn.matmul` 仅支持 rank-2 memory，且 stride 必须为连续布局。
- `nn.img2col1d/2d` 的动态参数必须是 `!symbol.int<"...">`，不接受 `i32/index` 或整数 attribute 直接作为 operand。
- 模块级 surviving 接口只允许 `matmul_img2col_patterns()`；`lower_matmul_img2col_family` 不属于公开入口。
- 每个 op 都必须由独立的 `@op_type_rewrite_pattern` 处理，不再通过 family dispatcher 做名称分发。

## 公开接口

### `matmul_img2col_patterns() -> list[RewritePattern]`

功能说明：

- 返回 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d` 的有序 pattern 列表。
- 供 `nn_lowering_patterns()` 直接拼接到主 driver 中。

参数说明：

- 无。

使用示例：

```python
from kernel_gen.passes.lowering.nn_lowering.matmul_img2col_lowering import (
    matmul_img2col_patterns,
)

patterns = matmul_img2col_patterns()
```

注意事项：

- 返回顺序固定为 `matmul -> img2col1d -> img2col2d`。
- `build_*` 或 `_lower_*` 共享 helper 只属于内部实现，不属于公开合同。
- 返回列表中不得保留 `lower_matmul_img2col_family` 兼容入口。

返回与限制：

- 返回可直接传入 `GreedyRewritePatternApplier` 的 `RewritePattern` 列表。

## 测试

- 测试文件：
  - [`test/pass/nn_lowering/matmul.py`](../../../../test/pass/nn_lowering/matmul.py)
  - [`test/pass/nn_lowering/img2col1d.py`](../../../../test/pass/nn_lowering/img2col1d.py)
  - [`test/pass/nn_lowering/img2col2d.py`](../../../../test/pass/nn_lowering/img2col2d.py)
  - [`test/pass/nn_lowering/public_name.py`](../../../../test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_asset_cases.py`](../../../../test/pass/nn_lowering/test_nn_lowering_asset_cases.py)
- 执行命令：
  - `pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k "matmul or img2col"`
  - `pytest -q test/pass/nn_lowering/public_name.py -k patterns`
- 测试目标：
  - 验证 `nn.matmul` -> `kernel.matmul` 的 lowering 目标与输出 memory 约束。
  - 验证 `nn.img2col1d/nn.img2col2d` -> `kernel.img2col*` 的 lowering 目标与 `symbol.int` 参数约束。
  - 验证主 driver 的 pattern 顺序已不再包含 matmul/img2col family dispatcher。
  - `img2col1d/2d accepts_noncanonical_symbol_names` 继续由各自资产文件单独维护，不纳入 collectable 公开入口。
- 功能与用例清单：
  - `test_nn_lowering_matmul_target`
  - `test_nn_lowering_matmul_inside_symbol_for`
  - `test_nn_lowering_img2col1d_target`
  - `test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names`
  - `test_nn_lowering_img2col2d_target`
  - `test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names`
  - `test_nn_lowering_asset_case`
