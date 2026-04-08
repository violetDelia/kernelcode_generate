# decompose_nn_softmax.md

## 功能简介

- 定义 `decompose-nn-softmax` pass 的公开合同。
- 该 pass 仅负责把 `func.func` 中的 `nn.softmax` 固定展开为可继续 lower 的 `nn` 方言链。
- 展开链固定为 `nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/decompose_nn_softmax.md`](../../../spec/pass/lowering/decompose_nn_softmax.md)
- `功能实现`：[`kernel_gen/passes/lowering/decompose_nn_softmax.py`](../../../kernel_gen/passes/lowering/decompose_nn_softmax.py)
- `test`：[`test/pass/test_decompose_nn_softmax.py`](../../../test/pass/test_decompose_nn_softmax.py)
- `expectation`：[`expectation/pass/lowering/decompose_nn_softmax.py`](../../../expectation/pass/lowering/decompose_nn_softmax.py)

## 依赖

- [`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- [`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- [`kernel_gen/dialect/nn.py`](../../../kernel_gen/dialect/nn.py)

## 目标

- 新增 `DecomposeNnSoftmaxPass`。
- 固定 pass 名字为 `decompose-nn-softmax`。
- 固定 softmax 分解链与分解顺序，不允许实现自由选择等价组合。
- 固定 `axis` 先在 pass 内规整为非负下标，再写入 `nn.reduce_max` 与 `nn.reduce_sum` 的 `axes=[...]`。
- 固定 `nn.reduce_max` 与 `nn.reduce_sum` 都使用 `keepdim=true`。
- 固定两个 `nn.broadcast` 的结果类型都与原 `nn.softmax.result` 完全一致。

## 限制与边界

- 只负责 `nn.softmax -> nn.*` 分解，不直接 lower 到 `kernel.*`。
- 不修改 `dsl/mlir_gen` 的 helper 入口形式；前端仍然生成 `nn.softmax`。
- 不扩 `kernel.softmax`、后端 runtime、stream 或 target 相关能力。

## 公开接口

### `class DecomposeNnSoftmaxError(ValueError)`

- 功能说明：`decompose-nn-softmax` pass 的显式错误类型。
- 参数说明：
  - `message: str`：错误文本。
- 使用示例：`raise DecomposeNnSoftmaxError("DecomposeNnSoftmaxError: normalized axis out of range")`
- 返回与限制：抛错即终止当前 pass。

### `class DecomposeNnSoftmaxPass(Pass)`

- 功能说明：把 `ModuleOp` 中的 `nn.softmax` 分解为固定 7 段 `nn` 方言链。
- 参数说明：无。
- 使用示例：

```python
from kernel_gen.passes.lowering.decompose_nn_softmax import DecomposeNnSoftmaxPass

module = DecomposeNnSoftmaxPass().run(module)
```

- 注意事项：
  - 输入必须是 `builtin.module`。
  - 仅改写 `func.func` 的函数体。
  - pass 运行后，不得保留被命中的 `nn.softmax`。
- 返回与限制：返回改写后的同一 `ModuleOp`。

## 最小改写合同

### 基本分解链

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

- `nn.softmax` 被完整移除。
- `nn.truediv.result` 替换原 `nn.softmax.result` 的所有使用。
- 两个 `nn.broadcast.result` 与最终 `nn.truediv.result` 类型都与原 `nn.softmax.result` 完全一致。

### 负轴规整

- 若 `axis < 0`，必须按 `rank + axis` 规整为非负下标。
- 规整后的 `axis` 必须用于 `nn.reduce_max` 与 `nn.reduce_sum` 的 `axes=[...]`。

示例：

```text
axis = -1, rank = 3  => normalized_axis = 2
```

### 失败路径：axis 越界

- 若规整后的 `axis` 不在 `[0, rank)`，pass 必须显式失败。
- 错误文本必须包含：

```text
DecomposeNnSoftmaxError: normalized axis out of range
```

### 失败路径：softmax 结果类型不匹配

- 若 `nn.softmax.result` 的 `shape/stride` 与输入不一致，pass 必须显式失败。
- 错误文本必须包含：

```text
DecomposeNnSoftmaxError: result type must match input shape and stride
```

## 验证要求

- `pytest -q test/pass/test_decompose_nn_softmax.py`
- `PYTHONPATH=. python expectation/pass/lowering/decompose_nn_softmax.py`

## 使用示例

```python
from kernel_gen.passes.lowering.decompose_nn_softmax import DecomposeNnSoftmaxPass
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.pass_manager import PassManager

pm = PassManager(name="lowering")
pm.add_pass(DecomposeNnSoftmaxPass())
pm.add_pass(LowerNnToKernelPass())
pm.add_pass(BufferResultsToOutParamsPass())
module = pm.run(module)
```
