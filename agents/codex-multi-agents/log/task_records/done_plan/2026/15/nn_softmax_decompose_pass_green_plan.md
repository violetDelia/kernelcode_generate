# nn_softmax_decompose_pass_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260408-nn-softmax-decompose` | `agents/codex-multi-agents/log/task_records/2026/15/20260408-nn-softmax-decompose-s1.md` | `已合并收口（T-20260408-c6721174；详见记录文件）` |
| `S2` | `S1` | `wt-20260408-nn-softmax-decompose` | `agents/codex-multi-agents/log/task_records/2026/15/20260408-nn-softmax-decompose-s2.md` | `已合并收口（T-20260408-5d7eb75f；详见记录文件）` |
| `S3` | `S1`、`S2` | `wt-20260408-nn-softmax-decompose` | `agents/codex-multi-agents/log/task_records/2026/15/20260408-nn-softmax-decompose-s3.md` | `已合并收口（T-20260408-09373156；详见记录文件）` |

## 计划目标

- 新增一个专门的 `DecomposeNnSoftmaxPass`，把 `nn.softmax` 固定分解为一条可继续 lowering 的 `nn` 方言链。
- 保持 `dsl/mlir_gen` 的 helper 入口不变：`build_func_op(...)` 仍然生成 `nn.softmax`，不在前端直接展开。
- 把默认 pass 顺序改为：`DecomposeNnSoftmaxPass -> LowerNnToKernelPass -> BufferResultsToOutParamsPass`。
- 让通用链路不再依赖尚未落地的 `kernel.softmax`；softmax 的 generic 路径改走 `reduce/broadcast/exp/div` 组合。
- 保持 softmax 的公开语义不变：输出 `shape/stride/dtype/space/format` 与输入一致，数值稳定语义仍为 `exp(x - max(x)) / sum(exp(x - max(x)))`。

## 当前基线（2026-04-07）

- 当前高层语义已经定义了 `softmax`：
  - [`spec/operation/nn.md`](spec/operation/nn.md)
  - [`spec/dialect/nn.md`](spec/dialect/nn.md)
- 当前 `dsl/mlir_gen` 已能生成 `nn.softmax`：
  - [`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](expectation/dsl/mlir_gen/dialect/nn/softmax.py)
  - [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- 当前 `nn_to_kernel` 规范仍写成 `nn.softmax -> kernel.softmax`：
  - [`spec/pass/lowering/nn_to_kernel.md`](spec/pass/lowering/nn_to_kernel.md)
  - [`expectation/pass/lowing/nn_to_kernel/softmax.py`](expectation/pass/lowing/nn_to_kernel/softmax.py)
- 当前仓库没有落地 `kernel.softmax` 的方言实现与通用 lowering：
  - [`kernel_gen/dialect/kernel.py`](kernel_gen/dialect/kernel.py)
  - [`kernel_gen/passes/lowering/nn_to_kernel.py`](kernel_gen/passes/lowering/nn_to_kernel.py)
- 因此，softmax 在当前通用 lowering 链路中仍缺一段可执行的中间 pass。

## 讨论结论

### 计划目标

- 新 pass 只解决一件事：把 `nn.softmax` 明确分解成 `nn.reduce_max + nn.broadcast + nn.sub + nn.exp + nn.reduce_sum + nn.broadcast + nn.truediv`。
- 分解后的 IR 仍停留在 `nn` 方言层，后续继续交给 `LowerNnToKernelPass` 处理。
- 这次不扩成“softmax 融合优化”或“按后端选择直接 kernel.softmax / 分解链二选一”的专题。

### 是否有更合理的方案

- 不采用“继续等待 `kernel.softmax` 实现完成”的方案。
  - 原因：softmax 的 generic 语义已经可以由现有 `nn` 基元表达，先补分解 pass 更短、更稳。
- 不采用“在 `dsl/mlir_gen` 直接把 helper 展开成多个 `nn` op”的方案。
  - 原因：这会把高层语义 helper 与 pass 职责混在一起，后续前端测试和 pass 测试都不清晰。
- 不采用“把 softmax 分解逻辑塞进 `LowerNnToKernelPass`”的方案。
  - 原因：`LowerNnToKernelPass` 的职责是 `nn -> dma/kernel`，不应该同时承担高层语义展开。
- 不采用“先新增 `kernel.softmax` 再补后端代码生成”的方案。
  - 原因：这条路径需要同时扩 `kernel` 方言、lowering、kernel gen 与后端实现，范围更大。

### 依赖

- softmax 高层语义：
  - [`spec/operation/nn.md`](spec/operation/nn.md)
- `nn` 方言结构化 op：
  - [`spec/dialect/nn.md`](spec/dialect/nn.md)
- pass 顺序与执行器：
  - [`spec/pass/pass_manager.md`](spec/pass/pass_manager.md)
- 下游 lowering：
  - [`spec/pass/lowering/nn_to_kernel.md`](spec/pass/lowering/nn_to_kernel.md)
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](spec/pass/lowering/buffer_results_to_out_params.md)

### 验证合理性

- `dsl/mlir_gen` 侧必须继续证明：helper 入口生成的仍是 `nn.softmax`，而不是前端直接展开。
- 新 pass 必须证明：运行后 `nn.softmax` 消失，替换为固定的 7 段链路，且结果类型与原 `nn.softmax.result` 完全一致。
- `axis=-1` 或其他负轴输入时，分解 pass 必须先把 `axis` 规整为非负轴，再写入 `reduce_*` 的 `axes=[...]`。
- `reduce_max` 与 `reduce_sum` 必须固定使用 `keepdim=true`，这样后续 `nn.broadcast` 才能机械恢复到原输出形状。
- `LowerNnToKernelPass` 必须证明：softmax 经过分解后可继续 lower 为 `kernel.reduce_max/kernel.exp/kernel.reduce_sum/kernel.div + dma.broadcast + dma.alloc`，且不再依赖 `kernel.softmax`。
- 若调用方未先跑 `DecomposeNnSoftmaxPass` 就把 `nn.softmax` 直接送进 `LowerNnToKernelPass`，必须显式失败并给出固定短语。
- 验证顺序固定为：
  1. `pytest -q test/pass/test_decompose_nn_softmax.py`
  2. `pytest -q test/pass/test_pass_manager.py -k "softmax or decompose_nn_softmax"`
  3. `pytest -q test/pass/test_lowering_nn_to_kernel.py -k softmax`
  4. `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/softmax.py`
  5. `PYTHONPATH=. python expectation/pass/lowing/decompose_nn_softmax.py`
- 上述顺序中任一命令失败，当前阶段不得继续进入下一阶段。

### 可维护性

- softmax 分解逻辑集中在一个 pass 内，不让前端 helper、`nn_to_kernel`、后端代码生成分别各写一版。
- 分解链只使用已经存在的公开 `nn` 方言原语，后续若想替换成更强的融合路径，也只需替换这一层。
- expectation 与 pytest 分为三层：
  1. `dsl/mlir_gen`：只验证 `nn.softmax` 入口
  2. `decompose pass`：只验证分解前后
  3. `nn_to_kernel`：验证“分解后 softmax 链”可以继续 lower

## 固定合同（草案）

- pass 名称：`decompose-nn-softmax`
- Python 入口：`DecomposeNnSoftmaxPass`
- spec 文件：`spec/pass/lowering/decompose_nn_softmax.md`
- 作用对象：`func.func` 内的 `nn.softmax`
- 输入形态：`nn.softmax %input {axis = <i64>, space = #nn.space<...>}`
- 输出形态：使用同一个结果类型，重写成下面固定链路：
  1. `nn.reduce_max(..., axes=[normalized_axis], keepdim=true)`
  2. `nn.broadcast(...)`
  3. `nn.sub(...)`
  4. `nn.exp(...)`
  5. `nn.reduce_sum(..., axes=[normalized_axis], keepdim=true)`
  6. `nn.broadcast(...)`
  7. `nn.truediv(...)`
- `normalized_axis` 必须落在 `[0, rank)` 内。
- 两个 `nn.broadcast` 的结果类型都必须与原 `nn.softmax` 的结果类型完全一致。
- `nn.reduce_max` 与 `nn.reduce_sum` 的 `result.shape` 必须与 `keepdim=true` 规则一致。
- pass 运行后，module 中不得残留被本 pass 命中的 `nn.softmax`。
- 若 `LowerNnToKernelPass` 仍遇到 `nn.softmax`，必须报错：
  - `LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel`
- 若 `axis` 规整后落在合法范围外，`DecomposeNnSoftmaxPass` 必须报错：
  - `DecomposeNnSoftmaxError: normalized axis out of range`

## 前后 IR 示例（目标形态草案）

### 示例 1：静态 shape softmax 分解

输入 IR：

```text
func.func @softmax_kernel(%src: !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>> {
  %0 = "nn.softmax"(%src) {axis = 1 : i64, space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  func.return %0 : !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
}
```

预期输出：

```text
func.func @softmax_kernel(%src: !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>> {
  %max = "nn.reduce_max"(%src) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, 1], [1, 1], f32, #nn.space<global>>
  %max_full = "nn.broadcast"(%max) {space = #nn.space<global>} : (!nn.memory<[B, 1], [1, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  %shift = "nn.sub"(%src, %max_full) {space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>, !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  %exp = "nn.exp"(%shift) {space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  %sum = "nn.reduce_sum"(%exp) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, 1], [1, 1], f32, #nn.space<global>>
  %sum_full = "nn.broadcast"(%sum) {space = #nn.space<global>} : (!nn.memory<[B, 1], [1, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  %out = "nn.truediv"(%exp, %sum_full) {space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>, !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  func.return %out : !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
}
```

说明：

- `nn.softmax` 不再保留。
- `reduce_max` 与 `reduce_sum` 固定 `keepdim=true`。
- 两个 `broadcast` 的目标结果类型都与原 softmax 结果类型完全一致。

### 示例 2：负轴 softmax 分解

输入 IR：

```text
func.func @softmax_last_dim(%src: !nn.memory<[B, T, C], [T*C, C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, T, C], [T*C, C, 1], f32, #nn.space<global>> {
  %0 = "nn.softmax"(%src) {axis = -1 : i64, space = #nn.space<global>} : (!nn.memory<[B, T, C], [T*C, C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, T, C], [T*C, C, 1], f32, #nn.space<global>>
  func.return %0 : !nn.memory<[B, T, C], [T*C, C, 1], f32, #nn.space<global>>
}
```

预期输出：

```text
%max = "nn.reduce_max"(%src) {axes = [2 : i64], keepdim = true, space = #nn.space<global>} : ...
%max_full = "nn.broadcast"(%max) {space = #nn.space<global>} : ...
%shift = "nn.sub"(%src, %max_full) {space = #nn.space<global>} : ...
%exp = "nn.exp"(%shift) {space = #nn.space<global>} : ...
%sum = "nn.reduce_sum"(%exp) {axes = [2 : i64], keepdim = true, space = #nn.space<global>} : ...
%sum_full = "nn.broadcast"(%sum) {space = #nn.space<global>} : ...
%out = "nn.truediv"(%exp, %sum_full) {space = #nn.space<global>} : ...
```

说明：

- `axis=-1` 必须先规整为 `2`，再写入 `reduce_*`。
- 结果类型仍与原 softmax 一致，不允许在分解过程中改变 shape 或 stride。

### 示例 3：未先分解就进入 `LowerNnToKernelPass`

输入 IR：

```text
func.func @softmax_kernel(%src: !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>> {
  %0 = "nn.softmax"(%src) {axis = 1 : i64, space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  func.return %0 : !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
}
```

预期输出：

```text
LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel
```

### 示例 4：失败路径（分解结果类型不一致）

输入 IR：

```text
func.func @softmax_bad_result(%src: !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>> {
  %0 = "nn.softmax"(%src) {axis = 1 : i64, space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [1, C], f32, #nn.space<global>>
  func.return %0 : !nn.memory<[B, C], [1, C], f32, #nn.space<global>>
}
```

预期输出：

```text
DecomposeNnSoftmaxError: result type must match input shape and stride
```

### 示例 5：失败路径（axis 规整越界）

输入 IR：

```text
func.func @softmax_axis_bad(%src: !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>> {
  %0 = "nn.softmax"(%src) {axis = 3 : i64, space = #nn.space<global>} : (!nn.memory<[B, C], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  func.return %0 : !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
}
```

预期输出：

```text
DecomposeNnSoftmaxError: normalized axis out of range
```

## 任务拆分

### `S1`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：补齐 `DecomposeNnSoftmaxPass` 本体及其直接验证资产，并把 softmax 分解链固定下来。
- `边界`：
  - 只定义 `nn.softmax` 的分解 pass，不扩 `kernel.softmax` 后端专用快速路径。
  - 不改 `dsl/mlir_gen` 的 helper 入口形式。
- `注意事项`：
  - 分解链必须固定；不要写成“可由实现自行选择若干等价组合”。
  - `axis` 需要在 pass 内规整为非负下标。
- `规格文件`：
  - [`spec/pass/lowering/decompose_nn_softmax.md`](spec/pass/lowering/decompose_nn_softmax.md)
- `功能实现`：
  - [`kernel_gen/passes/lowering/decompose_nn_softmax.py`](kernel_gen/passes/lowering/decompose_nn_softmax.py)
- `测试文件`：
  - [`test/pass/test_decompose_nn_softmax.py`](test/pass/test_decompose_nn_softmax.py)
- `expectation 文件`：
  - [`expectation/pass/lowing/decompose_nn_softmax.py`](expectation/pass/lowing/decompose_nn_softmax.py)
- `预期示例代码`：

```python
pm = PassManager(name="lowering")
pm.add_pass(DecomposeNnSoftmaxPass())
pm.add_pass(LowerNnToKernelPass())
pm.add_pass(BufferResultsToOutParamsPass())
module = pm.run(module)
```

- `预期输出`：
  - 计划文本必须明确 `DecomposeNnSoftmaxPass` 的输出链为 `reduce_max -> broadcast -> sub -> exp -> reduce_sum -> broadcast -> truediv`。
  - 计划文本必须明确 `DecomposeNnSoftmaxPass` 运行后不再保留被命中的 `nn.softmax`。
  - 计划文本必须明确 `axis` 规整越界时报 `DecomposeNnSoftmaxError: normalized axis out of range`。
- `验收必过项目`：
  - `pytest -q test/pass/test_decompose_nn_softmax.py`
  - `PYTHONPATH=. python expectation/pass/lowing/decompose_nn_softmax.py`

### `S2`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：更新 softmax 的 lowering 合同，并让 `LowerNnToKernelPass` 对 residual `nn.softmax` 给出固定失败短语。
- `边界`：
  - 不改变 `softmax(...)` 高层输出合同。
  - 不改 `fc/conv` 的现有 decomposition 路径。
- `注意事项`：
  - `operation/nn` 只写高层语义与 decomposition 责任，不要写成具体实现代码。
  - `nn_to_kernel` 只写“分解后如何继续 lower”，不要把分解逻辑塞回 `nn_to_kernel`。
- `规格文件`：
  - [`spec/pass/lowering/nn_to_kernel.md`](spec/pass/lowering/nn_to_kernel.md)
  - [`spec/operation/nn.md`](spec/operation/nn.md)
- `功能实现`：
  - [`kernel_gen/passes/lowering/nn_to_kernel.py`](kernel_gen/passes/lowering/nn_to_kernel.py)
- `测试文件`：
  - [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- `expectation 文件`：
  - [`expectation/pass/lowing/nn_to_kernel/softmax.py`](expectation/pass/lowing/nn_to_kernel/softmax.py)
- `预期示例代码`：

```python
value = Memory(shape=["B", "C"], dtype=NumericType.Float32)
out = softmax(value, axis=1)
```

- `预期输出`：
  - `operation/nn` 必须写明 softmax 的通用分解等价式：`exp(x - max(x)) / sum(exp(x - max(x)))`。
  - `nn_to_kernel` 必须写明默认路径不再要求 `kernel.softmax`。
  - `nn_to_kernel` 必须写明 residual `nn.softmax` 的显式失败短语：`LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel`。
- `验收必过项目`：
  - `pytest -q test/pass/test_lowering_nn_to_kernel.py -k softmax`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/softmax.py`

### `S3`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：对齐 pass 顺序、方言职责和前端 expectation，让 softmax 的前端入口与 lowering 顺序形成完整链路。
- `边界`：
  - `nn` 方言仍保留 `nn.softmax` 结构化 op。
  - 不要求删除 [`spec/dialect/kernel.md`](spec/dialect/kernel.md) 里的 `kernel.softmax` 条目。
- `注意事项`：
  - `nn.softmax` 仍然是合法输入 op；“是否分解”是 pass 责任，不是方言责任。
  - expectation 要分成“前端仍生成 `nn.softmax`”和“decompose pass 消去 `nn.softmax`”两层，不要混写。
- `规格文件`：
  - [`spec/pass/pass_manager.md`](spec/pass/pass_manager.md)
  - [`spec/dialect/nn.md`](spec/dialect/nn.md)
- `功能实现`：
  - [`kernel_gen/passes/pass_manager.py`](kernel_gen/passes/pass_manager.py)
- `测试文件`：
  - [`test/pass/test_pass_manager.py`](test/pass/test_pass_manager.py)
  - [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- `expectation 文件`：
  - [`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](expectation/dsl/mlir_gen/dialect/nn/softmax.py)
- `预期示例代码`：

```python
func_op = build_func_op(softmax_kernel, value)
module = PassManager(name="lowering").run(module)
```

- `预期输出`：
  - `dsl/mlir_gen` expectation 继续要求生成 `nn.softmax`
  - 新 pass expectation 要求 `nn.softmax` 被分解成固定 7 段链路
  - `nn_to_kernel` expectation 要求最终 IR 中不出现 `kernel.softmax`
  - `pass_manager` 侧必须固定 `DecomposeNnSoftmaxPass -> LowerNnToKernelPass -> BufferResultsToOutParamsPass`
- `验收必过项目`：
  - `pytest -q test/pass/test_pass_manager.py -k "softmax or decompose_nn_softmax"`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/softmax.py`

## 自检结论

- 目标已收口到“新增 softmax 分解 pass”，没有把范围扩到 `kernel.softmax` 后端实现。
- 任务拆分按文件边界收成 `3` 步，每步只改 `1~2` 个 `md` 文件，管理员可以直接继续分发。
- 示例代码、预期输出、验证命令都已写成可机械判定的形式。
- 方案与当前仓库现状一致：保留 `nn.softmax` 前端入口，把分解职责放到 lowering 链中单独一层。

## 评审摘要（2026-04-07）

- `评审结论`：已评审通过
- `评审人`：`大闸蟹`、`守护最好的爱莉希雅`
- `结论摘要`：
  - `S1~S3` 已统一为“收口任务（规格+实现+测试）”，并绑定 `spec/实现/test/expectation` 文件。
  - 验证顺序已固定为 `test_decompose_nn_softmax -> test_pass_manager -> test_lowering_nn_to_kernel -k softmax -> 两条 expectation`。
  - 失败短语已固定为 `LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel` 与 `DecomposeNnSoftmaxError: normalized axis out of range`。

## 最终验收摘要（2026-04-09）

- `验收结论`：通过
- `评审人`：`大闸蟹`、`守护最好的爱莉希雅`
- `结论摘要`：
  - `进度`：`S1~S3` 均已合并收口，当前计划链路完整。
  - `证据`：`agents/codex-multi-agents/log/task_records/2026/15/20260408-nn-softmax-decompose-s1.md`、`agents/codex-multi-agents/log/task_records/2026/15/20260408-nn-softmax-decompose-s2.md`、`agents/codex-multi-agents/log/task_records/2026/15/20260408-nn-softmax-decompose-s3.md` 的实现、审查、复核记录均已通过。
  - `复核`：当前主仓执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_decompose_nn_softmax.py test/pass/test_pass_manager.py -k 'softmax or decompose_nn_softmax' test/pass/test_lowering_nn_to_kernel.py -k softmax`，结果为 `7 passed`。
  - `阻断项`：无。
