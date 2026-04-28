# decompass.md

## 功能简介

- 定义 `decompass` pass 的公开合同。
- `decompass` 在 `func.func` 内按固定 pattern 分解 `nn.softmax`。
- 第一版内置 `nn.softmax` 分解链：`nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。

## API 列表

- `DecompassPass`
  - `—— apply(ctx: Context, module: ModuleOp)`
  - `—— run(module: ModuleOp) -> ModuleOp`
- `NnSoftmaxDecompPattern`
  - `—— match_and_rewrite(op: NnSoftmaxOp, rewriter: PatternRewriter)`
- `get_decompass_pass_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/decompass.md`](../../../spec/pass/decompass.md)
- `功能实现`：[`kernel_gen/passes/decompass.py`](../../../kernel_gen/passes/decompass.py)
- `test`：[`test/pass/decompass/test_softmax.py`](../../../test/pass/decompass/test_softmax.py)

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

## 限制与边界

- `decompass` 仅负责 `nn.* -> nn.*` 分解，不直接 lower 到 `kernel.*`。
- 当前固定只覆盖 `nn.softmax`。
- 不提供通用 decompass register；若后续支持其它 `nn.*` 分解，需继续按“一 op 一 pattern”扩展。
- 显式失败统一使用 `kernel_gen.core.error.KernelCodeError(ErrorModule.PASS, message)`。
- 当前文件级公开 API 只包含 `DecompassPass`、`NnSoftmaxDecompPattern` 与 `get_decompass_pass_patterns()`；分解校验与结果类型构造逻辑不额外暴露文件级 helper，跨文件实现与测试不得直连内部步骤。
- 不修改 `dsl/mlir_gen` 的 helper 入口形式。
- 不扩后端 runtime、stream 或 target 相关能力。
- 当前任务链的正式验收只依赖 `spec`、公开导入路径与 `pytest`；若现场额外具备架构侧 black-box runner，只作为补充对照，不要求当前任务携带本地测试副本。

## 公开接口

### 失败类型

- 功能说明：使用 `kernel_gen.core.error.KernelCodeError` 表示显式失败。
- 参数说明：
  - `message: str`：错误文本。
- 使用示例：`raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "normalized axis out of range")`
- 返回与限制：抛错即终止当前 pass。

### `class DecompassPass(Pass)`

- 功能说明：对 `ModuleOp` 执行固定 `nn.softmax` 分解规则。
- 参数说明：无。
- 使用示例：

```python
from kernel_gen.passes.decompass import DecompassPass

module = DecompassPass().run(module)
```

- 注意事项：
  - 输入必须是 `builtin.module`。
  - 仅改写 `func.func` 的函数体。
  - 命中的 `nn.softmax` 会被替换为其分解链。
- 返回与限制：返回改写后的同一 `ModuleOp`。

### `class NnSoftmaxDecompPattern(RewritePattern)`

- 功能说明：`decompass` 内部固定使用的 `nn.softmax` 单 op pattern。
- 参数说明：无。
- 使用示例：

```python
from kernel_gen.passes.decompass import NnSoftmaxDecompPattern

pattern = NnSoftmaxDecompPattern()
```

- 返回与限制：
  - 仅匹配 `NnSoftmaxOp`。
  - 不承担其它 `nn.*` 的通用注册或动态分发。

### `get_decompass_pass_patterns()`

- 功能说明：返回 `decompass` pass 当前使用的公开 pattern 列表。
- 参数说明：无。
- 使用示例：

```python
from kernel_gen.passes.decompass import get_decompass_pass_patterns

patterns = get_decompass_pass_patterns()
```

- 返回与限制：
  - 当前返回值固定为只含一个 `NnSoftmaxDecompPattern` 的列表。
  - `DecompassPass.apply()` 必须通过该函数组装 pattern，不在 `apply()` 内手写重复列表。

## 最小改写合同

### `nn.softmax` 分解链

改写前：

```text
%0 = "nn.softmax"(%src) {axis = 1 : i64, space = #nn.space<global>} : (...) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
```

改写后：

```text
%max = "nn.reduce_max"(%src) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : ...
%max_full = "nn.broadcast"(%max) {space = #nn.space<global>} : ...
%shift = "nn.sub"(%src, %max_full) {space = #nn.space<global>} : ...
%exp = "nn.exp"(%shift) {space = #nn.space<global>} : ...
%sum = "nn.reduce_sum"(%exp) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : ...
%sum_full = "nn.broadcast"(%sum) {space = #nn.space<global>} : ...
%out = "nn.truediv"(%exp, %sum_full) {space = #nn.space<global>} : ...
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

## 验证要求

- `pytest -q test/pass/decompass/test_softmax.py`
- `pytest -q test/pass/test_pass_manager.py -k "decompass"`
- `rg -n --glob '!spec/pass/decompass.md' "kernel_gen\\.passes\\.lowering\\.decompass|spec/pass/lowering/decompass|test/pass/test_decompose_nn_softmax" kernel_gen spec test`

## 使用示例

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
