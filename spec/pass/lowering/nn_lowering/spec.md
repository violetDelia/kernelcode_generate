# nn_lowering

## 功能简介

- 定义将 `nn` dialect IR lower 到 `dma/kernel` dialect IR 的 pass 规范。
- 结果 Memory 必须由 `dma.alloc` 创建，并由 `kernel/dma` op 写入 `outs(...)`。
- 主 driver 只通过 `PatternRewriteWalker(GreedyRewritePatternApplier(nn_lowering_patterns()))` 调度单 op `RewritePattern`；family 级 dispatcher helper 不属于公开合同。

## API 列表

- `class NnLoweringPass()`
- `NnLoweringPass.apply(ctx: Context, module: ModuleOp) -> None`
- `nn_lowering_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/nn_lowering/spec.md`](../../../../spec/pass/lowering/nn_lowering/spec.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
- `test`：
  - [`test/passes/lowering/nn_lowering/test_public_name.py`](../../../../test/passes/lowering/nn_lowering/test_public_name.py)
  - [`test/passes/lowering/nn_lowering/test_nn_lowering.py`](../../../../test/passes/lowering/nn_lowering/test_nn_lowering.py)
  - [`test/passes/lowering/nn_lowering/test_asset_cases.py`](../../../../test/passes/lowering/nn_lowering/test_asset_cases.py)

## 依赖

- Pass 管理：[`spec/pass/pass_manager.md`](../../../../spec/pass/pass_manager.md)
- 工具函数：[`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- Element binary / compare：[`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
- Select / cast / exp：[`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
- DMA structured：[`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](../../../../spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
- Matmul / img2col：[`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](../../../../spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
- Reduce / softmax：[`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
- NN dialect：[`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../../../spec/dialect/symbol.md)

## 目标

- 提供唯一 canonical import path `kernel_gen.passes.lowering.nn_lowering.NnLoweringPass`，并保持 `name == "lower-nn"`。
- 将 `nn_lowering` family 收口为“共享 helper + 单 op `RewritePattern` + 薄 `NnLoweringPass.apply(...)`”。
- 将 family 子模块的 surviving 模块级接口收口为 `*_patterns()`；`lower_*_family` 不再属于公开入口。
- 将支持的 `nn` op lower 为 `kernel/dma` op，输出 Memory 通过 `dma.alloc` 显式创建。
- 输出 module 不应再包含 `nn` op。
- 明确 `kernel.binary_elewise` 与 `kernel.reduce` 的公开合同已就绪，并在测试中验证可用性。
- `lower-nn` 为唯一公开 pass 名称，对外不再保留旧名入口。

## API详细说明

### `class NnLoweringPass()`

- api：`class NnLoweringPass()`
- 参数：无。
- 返回值：`NnLoweringPass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass

  pass_obj = NnLoweringPass()
  ```
- 功能说明：表示 `nn -> kernel/dma` lowering pass。
- 注意事项：固定公开名称为 `"lower-nn"`；公开执行入口固定为 `apply(ctx, module)`；不再保留 `run(module)` 兼容入口；若出现不支持的 op 或校验失败，必须抛出 `KernelCodeError`。

### `NnLoweringPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`NnLoweringPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from xdsl.context import Context

  from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass

  NnLoweringPass().apply(Context(), module)
  ```
- 功能说明：对输入 module 执行 `nn -> kernel/dma` lowering，并原地改写 `module`。
- 注意事项：`module` 不是 `builtin.module` 时必须抛出 `KernelCodeError`；`apply(...)` 必须直接消费 `nn_lowering_patterns()` 返回的顺序化 pattern 列表，构造 `PatternRewriteWalker(GreedyRewritePatternApplier(...))`，不得回退为手写 `while progress` 或 family 分发循环；返回 `None`。

### `nn_lowering_patterns() -> list[RewritePattern]`

- api：`nn_lowering_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  from kernel_gen.passes.lowering.nn_lowering import nn_lowering_patterns

  patterns = nn_lowering_patterns()
  ```
- 功能说明：返回 `lower-nn` 主 driver 使用的有序 pattern 列表。
- 注意事项：将 element binary、select/cast/exp、dma structured、matmul/img2col、reduce/softmax reject 组合为同一条 rewrite 主链；返回顺序必须稳定，且 `_RejectUnsupportedNnOpPattern` 必须位于最后；列表中不得再出现 family dispatcher 占位 pattern 名称，例如 `_LowerElementBinaryFamilyPattern`、`_LowerDmaStructuredFamilyPattern`、`_LowerMatmulImg2colFamilyPattern`、`_LowerReduceSoftmaxFamilyPattern`；返回值可直接传入 `GreedyRewritePatternApplier`。

## 额外补充

- 文件职责与 child spec 边界：
  - `nn_lowering.py`：唯一公开 pass、`nn_lowering_patterns()`、顶层 driver 顺序、错误汇总。
  - `nn_lowering_utility.py`：公共校验与 helper（module/space/result/operand 等）。
  - `element_binary_lowering.py`：`element_binary_patterns()` 与 element binary / compare 共享构造逻辑。
  - `select_cast_lowering.py`：`select_cast_patterns()`，覆盖 `nn.select` / `nn.cast` / `nn.exp`。
  - `dma_structured_lowering.py`：`dma_structured_patterns()`，覆盖 `nn.broadcast` / `nn.transpose`。
  - `matmul_img2col_lowering.py`：`matmul_img2col_patterns()`，覆盖 `nn.matmul` / `nn.img2col1d` / `nn.img2col2d`。
  - `reduce_softmax_lowering.py`：`reduce_softmax_patterns()`，覆盖 `nn.reduce_*` 与 direct `nn.softmax` 拒绝。
- `nn_lowering` family 的 surviving 模块级接口只包括：
  - `NnLoweringPass`
  - `KernelCodeError`
  - `nn_lowering_patterns()`
  - 各 child 模块的 `*_patterns()`
- `lower_*_family` 只属于待清理的旧 helper 名称，不能作为 build/review 的通过证据。

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 公开构造入口固定为 `build_registered_pass("lower-nn")` 与 `kernel_gen.passes.lowering.nn_lowering.NnLoweringPass`。
- `NnLoweringPass.apply(...)` 必须直接使用 `nn_lowering_patterns()` 构造 `PatternRewriteWalker(GreedyRewritePatternApplier(...))`，不得回退为手写 `while progress` 或 family 分发循环。
- `nn_lowering_patterns()` 的注册顺序固定为：
  - `element_binary_patterns()`
  - `select_cast_patterns()`
  - `dma_structured_patterns()`
  - `matmul_img2col_patterns()`
  - `reduce_softmax_patterns()`
  - `_RejectUnsupportedNnOpPattern`
- caller 的 canonical public path 固定为：

```python
from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
```

- `kernel_gen.passes.lowering.nn_to_kernel` 属于旧 compat 模块；导入必须以 `ModuleNotFoundError` 失败。
- `LowerNnToKernelPass` / `LowerNnToKernelError` 不再属于 surviving public contract；package 级 re-export 不能作为验收入口。
- family 子模块的 surviving 模块级接口只允许 `*_patterns()`；`lower_*_family`、`_Lower*FamilyPattern` 占位名与 `parent_block + has_done_action` dispatcher 路径都不属于公开合同或验收证据。
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
  - `out` 必须由 `dma.alloc` 创建；输入与输出的 `shape/stride/element_type/space` 必须一致，否则抛出 `KernelCodeError`。
- `nn.reduce_sum/min/max` lowering 规则：
  - 目标 op 固定为 `kernel.reduce`，`kind` 取值分别为 `"sum" / "min" / "max"`。
  - `axis/keepdim` 直接继承 `nn.reduce_*` 的语义；`out` 仅消费已有结果 memory，不得改写为 `kernel.reduce_sum/min/max`。
  - `out` 的 `shape/stride/element_type/space` 必须满足 reduce 合同，否则抛出 `KernelCodeError`。
- `nn.softmax` 不在 `lower-nn` 内直接 lowering：
  - 进入本 pass 前必须先由上游 helper/分解 pass 展开为公开稳定链路。
  - 若仍直接命中 `nn.softmax`，必须抛出 `KernelCodeError`，错误信息需明确要求“先分解再进入 lower-nn”。
- `nn.matmul` lowering 规则：
  - 目标 op 固定为 `kernel.matmul`，并把结果写入 `out` operand。
  - 动态维度只能来源于 `symbol.get_dim` 或显式 `!symbol.int<"...">`；不允许把 `i32/index` 直接作为动态维度来源。
  - `out` 的 `shape/stride/element_type/space` 必须与 matmul 合同一致，否则抛出 `KernelCodeError`。
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
- 遇到不支持的 op、结果类型非法、缺失 `nn.space`、operand 数量不匹配或 kernel 校验失败时，必须抛出 `KernelCodeError` 并终止。

## 测试

- 测试文件：
  - `test/passes/lowering/nn_lowering/test_asset_cases.py`
  - `test/passes/lowering/nn_lowering/test_nn_lowering.py`
  - `test/passes/lowering/nn_lowering/test_public_name.py`
- 执行命令：
  - `pytest -q test/passes/lowering/nn_lowering/test_public_name.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py`
  - `pytest -q test/passes/lowering/nn_lowering/test_asset_cases.py`
  - `pytest -q test/passes/nn_lowering`

### 测试目标

- 验证 `spec/pass/lowering/nn_lowering/spec.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-NNL-001 | 公开入口 | `NnLoweringPass` 公开名称 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_lowering_pass_public_name`。 | 公开入口在“`NnLoweringPass` 公开名称”场景下可导入、构造、注册或按名称发现。 | `test_nn_lowering_pass_public_name` |
| TC-PASS-NNL-002 | 公开入口 | canonical import 成功、旧 compat 模块失败 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_lowering_pass_public_exports`。 | 公开入口在“canonical import 成功、旧 compat 模块失败”场景下可导入、构造、注册或按名称发现。 | `test_nn_lowering_pass_public_exports` |
| TC-PASS-NNL-003 | 边界/异常 | `nn_lowering_patterns()` 通过公开 `*_patterns()` 组合且 reject-last 规则稳定 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_lowering_patterns_compose_public_family_exports`。 | “`nn_lowering_patterns()` 通过公开 `*_patterns()` 组合且 reject-last 规则稳定”场景按公开错误语义失败或被拒绝。 | `test_nn_lowering_patterns_compose_public_family_exports` |
| TC-PASS-NNL-004 | pass 改写 | `NnLoweringPass.apply(...)` 直接使用 pattern driver | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_apply_uses_pattern_driver`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`NnLoweringPass.apply(...)` 直接使用 pattern driver”场景。 | `test_nn_lowering_apply_uses_pattern_driver` |
| TC-PASS-NNL-005 | pass 改写 | collectable 公开资产入口可直接执行当前已纳入的非 `test_*.py` helper / boundary case | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_nn_lowering_asset_case`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“collectable 公开资产入口可直接执行当前已纳入的非 `test_*.py` helper / boundary case”场景。 | `test_nn_lowering_asset_case` |
| TC-PASS-NNL-010 | pass 改写 | `nn.add` lowering 为 `kernel.binary_elewise(kind="add")` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_add_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn.add` lowering 为 `kernel.binary_elewise(kind="add")`”场景。 | `test_lower_add_to_kernel` |
| TC-PASS-NNL-011 | pass 改写 | `nn.truediv` lowering 为 `kernel.binary_elewise(kind="div")` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_div_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn.truediv` lowering 为 `kernel.binary_elewise(kind="div")`”场景。 | `test_lower_div_to_kernel` |
| TC-PASS-NNL-012 | pass 改写 | `nn.reduce_min` lowering 为 `kernel.reduce(kind="min")` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_reduce_min_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn.reduce_min` lowering 为 `kernel.reduce(kind="min")`”场景。 | `test_lower_reduce_min_to_kernel` |
| TC-PASS-NNL-013 | pass 改写 | `nn.reduce_sum` lowering 为 `kernel.reduce(kind="sum")` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_reduce_sum_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn.reduce_sum` lowering 为 `kernel.reduce(kind="sum")`”场景。 | `test_lower_reduce_sum_to_kernel` |
| TC-PASS-NNL-014 | pass 改写 | `nn.reduce_max` lowering 为 `kernel.reduce(kind="max")` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_reduce_max_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn.reduce_max` lowering 为 `kernel.reduce(kind="max")`”场景。 | `test_lower_reduce_max_to_kernel` |
| TC-PASS-NNL-020 | 边界/异常 | direct `nn.softmax` 需先分解后再进入 `lower-nn` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_lower_softmax_requires_decompass`。 | “direct `nn.softmax` 需先分解后再进入 `lower-nn`”场景按公开错误语义失败或被拒绝。 | `test_lower_softmax_requires_decompass` |
| TC-PASS-NNL-021 | pass 改写 | `nn.matmul` lowering 目标为 `kernel.matmul` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_matmul_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn.matmul` lowering 目标为 `kernel.matmul`”场景。 | `test_lower_matmul_to_kernel` |
| TC-PASS-NNL-022 | pass 改写 | `nn.img2col1d` lowering 目标为 `kernel.img2col1d` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_img2col1d_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn.img2col1d` lowering 目标为 `kernel.img2col1d`”场景。 | `test_lower_img2col1d_to_kernel` |
| TC-PASS-NNL-023 | pass 改写 | `nn.img2col2d` lowering 目标为 `kernel.img2col2d` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_lower_img2col2d_to_kernel`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`nn.img2col2d` lowering 目标为 `kernel.img2col2d`”场景。 | `test_lower_img2col2d_to_kernel` |
