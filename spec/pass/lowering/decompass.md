# decompass.md

## 功能简介

- 定义 `decompass` pass 的公开合同。
- `decompass` 在 `func.func` 内按注册规则分解 `nn.*` op。
- 第一版内置 `nn.softmax` 分解链：`nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/decompass.md`](../../../spec/pass/lowering/decompass.md)
- `功能实现`：[`kernel_gen/passes/lowering/decompass.py`](../../../kernel_gen/passes/lowering/decompass.py)
- `test`：[`test/pass/test_decompose_nn_softmax.py`](../../../test/pass/test_decompose_nn_softmax.py)

## 依赖

- [`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- [`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- [`kernel_gen/dialect/nn.py`](../../../kernel_gen/dialect/nn.py)

## 目标

- 新增 `DecompassPass`。
- 固定 pass 名字为 `decompass`。
- 提供 `register_decompass_rewrite(op_name, rewrite)` 注册接口，用于扩展其它 `nn.*` 分解。
- 固定内置 `nn.softmax` 分解链与顺序，不允许实现自由选择等价组合。
- 固定 `axis` 先规整为非负下标，再写入 `nn.reduce_max` 与 `nn.reduce_sum` 的 `axes=[...]`。
- 固定 `nn.reduce_max` 与 `nn.reduce_sum` 使用 `keepdim=true`。
- 固定两个 `nn.broadcast` 结果类型都与原 `nn.softmax.result` 一致。

## 限制与边界

- `decompass` 仅负责 `nn.* -> nn.*` 分解，不直接 lower 到 `kernel.*`。
- 默认内置分解仅覆盖 `nn.softmax`。
- 其它 op 的分解仅通过注册接口扩展。
- 不修改 `dsl/mlir_gen` 的 helper 入口形式。
- 不扩后端 runtime、stream 或 target 相关能力。

## 公开接口

### `class DecompassError(ValueError)`

- 功能说明：`decompass` 的显式错误类型。
- 参数说明：
  - `message: str`：错误文本。
- 使用示例：`raise DecompassError("DecompassError: normalized axis out of range")`
- 返回与限制：抛错即终止当前 pass。

### `class DecompassPass(Pass)`

- 功能说明：对 `ModuleOp` 执行已注册分解规则。
- 参数说明：无。
- 使用示例：

```python
from kernel_gen.passes.lowering.decompass import DecompassPass

module = DecompassPass().run(module)
```

- 注意事项：
  - 输入必须是 `builtin.module`。
  - 仅改写 `func.func` 的函数体。
  - 命中的已注册 op 会被替换为其分解链。
- 返回与限制：返回改写后的同一 `ModuleOp`。

### `register_decompass_rewrite(op_name, rewrite)`

- 功能说明：注册 decompass 的自定义分解规则。
- 参数说明：
  - `op_name: str`：待分解 op 名字（例如 `nn.exp`）。
  - `rewrite: Callable[[Operation, Block], None]`：分解回调。
- 使用示例：

```python
from kernel_gen.passes.lowering.decompass import register_decompass_rewrite

def rewrite_exp(op, block):
    op.result.replace_by(op.input)
    block.erase_op(op)

register_decompass_rewrite("nn.exp", rewrite_exp)
```

- 返回与限制：
  - `op_name` 去空白后不能为空，否则抛 `DecompassError: op name must be non-empty`。
  - 同名规则按最新注册覆盖。

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

- `axis` 规整越界时必须报错：

```text
DecompassError: normalized axis out of range
```

- `nn.softmax.result` 的 `shape/stride` 与输入不一致时必须报错：

```text
DecompassError: result type must match input shape and stride
```

## 验证要求

- `pytest -q test/pass/test_decompose_nn_softmax.py`
- `pytest -q test/pass/test_pass_manager.py -k "decompass"`

## 使用示例

```python
from kernel_gen.passes.lowering.decompass import DecompassPass
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.pass_manager import PassManager

pm = PassManager(name="lowering")
pm.add_pass(DecompassPass())
pm.add_pass(NnLoweringPass())
pm.add_pass(BufferResultsToOutParamsPass())
module = pm.run(module)
```
