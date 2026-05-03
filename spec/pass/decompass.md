# decompass.md

## 功能简介

- 定义 `decompass` pass 的公开合同。
- `decompass` 在 `func.func` 内按固定 pattern 分解 `nn.softmax`。
- 第一版内置 `nn.softmax` 分解链：`nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。

## API 列表

- `class DecompassPass(fold: bool = True)`
- `DecompassPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class NnSoftmaxDecompPattern()`
- `NnSoftmaxDecompPattern.match_and_rewrite(op: NnSoftmaxOp, rewriter: PatternRewriter) -> None`
- `get_decompass_pass_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/decompass.md`](../../../spec/pass/decompass.md)
- `功能实现`：[`kernel_gen/passes/decompass.py`](../../../kernel_gen/passes/decompass.py)
- `test`：[`test/passes/decompass/test_softmax.py`](../../../test/passes/decompass/test_softmax.py)

## 依赖

- [`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- [`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- [`kernel_gen/dialect/nn.py`](../../../kernel_gen/dialect/nn.py)

## 目标

- 新增 `DecompassPass`。
- 提供 `get_decompass_pass_patterns()` 公开 pattern 组装入口。
- 固定 pass 名字为 `decompass`。
- 固定内置 `nn.softmax` 分解链与顺序，不允许实现自由选择等价组合。
- 固定 `axis` 只接受 `[0, rank)` 范围内的非负下标；负轴与越界轴都必须显式失败。
- 固定 `nn.reduce_max` 与 `nn.reduce_sum` 使用 `keepdim=true`。
- 固定两个 `nn.broadcast` 结果类型都与原 `nn.softmax.result` 一致。

## API详细说明

### `class DecompassPass(fold: bool = True)`

- api：`class DecompassPass(fold: bool = True)`
- 参数：
  - `fold`：是否允许 pattern walker 执行 folding；类型 `bool`；默认值 `True`。
- 返回值：`DecompassPass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.decompass import DecompassPass

  pass_obj = DecompassPass(fold=True)
  ```
- 功能说明：构造对 `ModuleOp` 执行固定 `nn.softmax` 分解规则的 pass。
- 注意事项：公开执行入口固定为 xDSL `ModulePass.apply(ctx, module)`；不提供单 pass `run(...)` 兼容入口；不承担其它 `nn.*` 的通用注册或动态分发。

### `DecompassPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`DecompassPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from xdsl.context import Context

  from kernel_gen.passes.decompass import DecompassPass

  DecompassPass().apply(Context(), module)
  ```
- 功能说明：对 `ModuleOp` 执行固定 `nn.softmax` 分解规则。
- 注意事项：输入必须是 `builtin.module`；仅改写 `func.func` 的函数体；命中的 `nn.softmax` 会被替换为固定分解链；显式失败统一抛 `KernelCodeError`。

### `class NnSoftmaxDecompPattern()`

- api：`class NnSoftmaxDecompPattern()`
- 参数：无。
- 返回值：`NnSoftmaxDecompPattern` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.decompass import NnSoftmaxDecompPattern

  pattern = NnSoftmaxDecompPattern()
  ```
- 功能说明：构造 `decompass` 内部固定使用的 `nn.softmax` 单 op pattern。
- 注意事项：仅匹配 `NnSoftmaxOp`；不承担其它 `nn.*` 的通用注册或动态分发；分解校验与结果类型构造逻辑不额外暴露文件级 helper。

### `NnSoftmaxDecompPattern.match_and_rewrite(op: NnSoftmaxOp, rewriter: PatternRewriter) -> None`

- api：`NnSoftmaxDecompPattern.match_and_rewrite(op: NnSoftmaxOp, rewriter: PatternRewriter) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `NnSoftmaxOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rewriter`：公开 rewrite 对象，用于替换、插入或删除 IR operation；类型 `PatternRewriter`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from kernel_gen.passes.decompass import NnSoftmaxDecompPattern

  pattern = NnSoftmaxDecompPattern()
  ```
- 功能说明：使用 `NnSoftmaxDecompPattern` 匹配目标 operation 并执行 rewrite。
- 注意事项：原 `nn.softmax` 被移除，`nn.truediv.result` 替换原 `nn.softmax.result` 的全部使用；两个 `nn.broadcast.result` 与 `nn.truediv.result` 类型都必须与原 `nn.softmax.result` 一致；`axis` 为负数或越界时必须以 `normalized axis out of range` 显式失败；`nn.softmax.result` 的 `shape/stride` 与输入不一致时必须以 `result type must match input shape and stride` 显式失败。

### `get_decompass_pass_patterns() -> list[RewritePattern]`

- api：`get_decompass_pass_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker

  from kernel_gen.passes.decompass import get_decompass_pass_patterns

  patterns = get_decompass_pass_patterns()
  walker = PatternRewriteWalker(GreedyRewritePatternApplier(patterns, ctx=ctx))
  ```
- 功能说明：返回 `decompass` pass 当前使用的公开 pattern 列表。
- 注意事项：当前返回值固定为只含一个 `NnSoftmaxDecompPattern` 的列表；`DecompassPass.apply()` 必须通过该函数组装 pattern，不在 `apply()` 内手写重复列表。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `decompass` 仅负责 `nn.* -> nn.*` 分解，不直接 lower 到 `kernel.*`。
- 当前固定只覆盖 `nn.softmax`。
- 显式失败统一使用 `kernel_gen.core.error.KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, message)`。
- 当前文件级公开 API 只包含 `DecompassPass`、`NnSoftmaxDecompPattern` 与 `get_decompass_pass_patterns()`；分解校验与结果类型构造逻辑不额外暴露文件级 helper，跨文件实现与测试不得直连内部步骤。
- 不修改 `dsl/mlir_gen` 的 helper 入口形式。
- 不扩后端 runtime、stream 或 target 相关能力。
- 当前任务链的正式验收只依赖 `spec`、公开导入路径与 `pytest`；若现场额外具备架构侧 black-box runner，只作为补充对照，不要求当前任务携带本地测试副本。

### 最小改写合同

### `nn.softmax` 分解链

改写前：

```text
%0 = "nn.softmax"(%src) {axis = 1 : i64, space = #nn.space<global>} : (value) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
```

改写后：

```text
%max = "nn.reduce_max"(%src) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : value
%max_full = "nn.broadcast"(%max) {space = #nn.space<global>} : value
%shift = "nn.sub"(%src, %max_full) {space = #nn.space<global>} : value
%exp = "nn.exp"(%shift) {space = #nn.space<global>} : value
%sum = "nn.reduce_sum"(%exp) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : value
%sum_full = "nn.broadcast"(%sum) {space = #nn.space<global>} : value
%out = "nn.truediv"(%exp, %sum_full) {space = #nn.space<global>} : value
```

必须满足：

- 原 `nn.softmax` 被移除。
- `nn.truediv.result` 替换原 `nn.softmax.result` 的全部使用。
- 两个 `nn.broadcast.result` 与 `nn.truediv.result` 类型都与原 `nn.softmax.result` 一致。

### 失败路径

- `axis` 为负数或越界时必须报错：

```text
normalized axis out of range
```

- `nn.softmax.result` 的 `shape/stride` 与输入不一致时必须报错：

```text
result type must match input shape and stride
```

### 验证要求

- `pytest -q test/passes/decompass/test_softmax.py`
- `pytest -q test/passes/test_pass_manager.py -k "decompass"`
- `rg -n --glob '!spec/pass/decompass.md' "kernel_gen\\.passes\\.lowering\\.decompass|spec/pass/lowering/decompass|test/passes/test_decompose_nn_softmax" kernel_gen spec test`

### 使用示例

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.passes.pass_manager import PassManager

pm = PassManager(name="lowering")
pm.add_pass(DecompassPass())
pm.add_pass(NnLoweringPass())
pm.add_pass(BufferResultsToOutParamsPass())
module = pm.run(module)
```

## 测试

- 测试文件：`test/passes/decompass/test_softmax.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/decompass/test_softmax.py`

### 测试目标

- 验证本文件 `API 列表` 中公开 API 的稳定行为、边界和错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-DECOMPASS-001 | 公开入口 | public import path exposes decompass pattern API | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_public_import_path_exposes_decompass_pattern_api`。 | 公开入口在“public import path exposes decompass pattern API”场景下可导入、构造、注册或按名称发现。 | `test_public_import_path_exposes_decompass_pattern_api` |
| TC-PASS-DECOMPASS-002 | 公开入口 | public pattern API returns single softmax pattern | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_public_pattern_api_returns_single_softmax_pattern`。 | 公开入口在“public pattern API returns single softmax pattern”场景下可导入、构造、注册或按名称发现。 | `test_public_pattern_api_returns_single_softmax_pattern` |
| TC-PASS-DECOMPASS-003 | 公开入口 | decompose softmax into fixed NN chain | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_decompose_softmax_into_fixed_nn_chain`。 | 公开入口在“decompose softmax into fixed NN chain”场景下可导入、构造、注册或按名称发现。 | `test_decompose_softmax_into_fixed_nn_chain` |
| TC-PASS-DECOMPASS-004 | 边界/异常 | decompose softmax rejects negative axis | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_decompose_softmax_rejects_negative_axis`。 | “decompose softmax rejects negative axis”场景按公开错误语义失败或被拒绝。 | `test_decompose_softmax_rejects_negative_axis` |
| TC-PASS-DECOMPASS-005 | 边界/异常 | decompose softmax rejects normalized axis out of range | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_decompose_softmax_rejects_normalized_axis_out_of_range`。 | “decompose softmax rejects normalized axis out of range”场景按公开错误语义失败或被拒绝。 | `test_decompose_softmax_rejects_normalized_axis_out_of_range` |
| TC-PASS-DECOMPASS-006 | 边界/异常 | decompose softmax rejects result type mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_decompose_softmax_rejects_result_type_mismatch`。 | “decompose softmax rejects result type mismatch”场景按公开错误语义失败或被拒绝。 | `test_decompose_softmax_rejects_result_type_mismatch` |
| TC-PASS-DECOMPASS-007 | pass 改写 | decompass uses single softmax pattern | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_decompass_uses_single_softmax_pattern`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“decompass uses single softmax pattern”场景。 | `test_decompass_uses_single_softmax_pattern` |
