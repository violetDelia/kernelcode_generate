# nn.md

用于定义 `Memory` 的逐元素算术、比较、`broadcast` 与 `matmul` 高层运算规范。该层独立于具体前端语法，可被普通 Python 代码、语义构造层或其他上层接口直接复用。

## 功能简介

- 为 `python/operation/nn.py` 定义稳定的高层运算 API 语义。
- 覆盖逐元素算术、逐元素比较（支持隐式 `broadcast`）、显式 `broadcast`，以及二维 `matmul` 的输入输出约束、错误规则和返回语义。
- 明确高层 `operation/nn` 与下游 `nn dialect` 的分层关系，不在本层引入 IR 细节。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `关联类型`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- `功能实现`：[`python/operation/nn.py`](../../python/operation/nn.py)

## 依赖

- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：定义 `Memory` 的 `shape`、`stride`、`dtype`、`space` 基础语义。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：定义下游 `nn dialect` 的类型、op verifier 与方言层约束。
- [`python/operation/nn.py`](../../python/operation/nn.py)：当前高层 API 实现文件；本 spec 以其为直接实现目标。

## 设计目标

- 为 `Memory` 提供统一、稳定的逐元素运算（含隐式 `broadcast`）、显式 `broadcast` 与 `matmul` 高层语义。
- 明确运算输入约束、输出语义、类型合法性与错误规则。
- 保留动态 `shape/stride` 信息，使运算结果仍可表达动态张量。
- 让运算层可被上层系统直接复用，而不把运算规则散落在多个模块中。

## 限制与边界

- 逐元素算术与比较支持隐式广播，但只允许遵守与 `broadcast` 相同的尾维对齐与 singleton dim 扩张规则；不支持任意维重排、隐式转置或把 `?` 当作通配符。
- `matmul` 当前只定义二维矩阵乘，不支持 batch matmul、broadcast matmul、隐式转置或带 bias 融合。
- 不在本阶段定义归约、卷积等其他高阶算子。
- 不在本阶段引入隐式自动类型提升的复杂规则。
- 不负责 AST、IR、lowering 等上层结构设计。

## 术语

- `Memory`：带 `shape`、`stride`、`dtype`、`memory_level` 等元信息的张量描述对象。
- 张量语义结果：可继续参与后续运算、并至少暴露 `shape`、`stride`、`dtype` 的结果对象。
- 标量：与 `dtype` 体系兼容的单值输入，例如 `int`，后续可扩展到更多数值类型。
- `bool`：逐元素比较的概念性真值语义。
- `predicate`：本 spec 对比较结果语义的描述，强调其表示真假而不是普通算术值。
- `NumericType.Int32`：当前 `Memory`/`python.operation.nn` 实现与测试中用于承载比较结果的具体 `dtype`；在本层它承担 predicate 载体角色。
- `broadcast`：显式把一个 `Memory` 扩张为给定目标 `shape` 的高层 API，不改变 `dtype` 与 `space`。
- `implicit broadcast`：在逐元素算术或比较中，如果两个 `Memory` 的 `shape` 不完全一致但满足广播兼容规则，高层 API 概念上先把一侧或两侧扩张到共同目标 `shape`，再执行原始逐元素 op；该过程属于高层语义，不要求调用方显式写出 `broadcast(...)`。
- singleton dim：在 `broadcast` 中可被扩张的静态维度 `1`。
- `matmul`：二维矩阵乘，要求 `lhs.shape=[M, K]`、`rhs.shape=[K, N]`，结果 `shape=[M, N]`。
- contracting dim：`matmul` 中被约束为相等的收缩维，即左操作数最后一维与右操作数第一维。

## 设计原则

- 运算层只定义“什么可以算、怎么算、何时报错”，不绑定具体前端表示。
- 至少一侧操作数必须具有 `Memory` 张量语义；本文不定义纯标量和纯标量之间的运算接口。
- `Memory` 与 `Memory` 的逐元素运算在高层 API 中支持隐式 broadcast；若两侧 `shape` 不完全一致但满足广播兼容规则，则按共同目标 `shape` 计算结果。
- `broadcast` 仍是独立高层 API；即使逐元素 op 支持隐式 broadcast，上层在需要复用扩张结果、显式表达语义或跨多步组合时，仍可显式调用 `broadcast`。
- `matmul` 只接受 `Memory` 与 `Memory`，不接受标量参与，也不隐式插入转置、reshape 或空间搬运。
- 所有计算在执行前都必须先通过类型合法性检查。
- 运算结果必须保留输入的动态维度信息，不得在前端阶段退化为静态常量。
- 比较操作返回逐元素比较结果，其结果仍是张量语义对象，而不是单个 Python `bool`。
- 当前 Python 运算层没有独立的 `bool/predicate` `NumericType`；因此比较结果在 API、实现与测试中的具体 `dtype` 契约统一为 `NumericType.Int32`。
- `broadcast` 在高层 API 只定义用户侧张量扩张语义；若后续 lower 到 `nn dialect`，方言侧 `nn.broadcast` 的 IR 结构、verifier 与 parse/print 约束必须由 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 单独定义。
- 若逐元素高层语义触发隐式 broadcast，lowering 到 `nn dialect` 时必须先显式物化为一个或多个 `nn.broadcast`，再生成原始 `nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge`；不得把隐式 broadcast 直接塞进方言层二元 op。
- `matmul` 在高层 API 只定义用户侧语义；若后续 lower 到 `nn dialect`，方言侧 `nn.matmul` 的 IR 结构、verifier 与 parse/print 约束必须由 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 单独定义。
- 必须提供独立的 nn API 实现层 `python/operation/nn.py`，并提供对应测试 `test/operation/test_operation_nn.py`，不可仅在 `python/symbol_variable/memory.py` 内承载语义。

## 支持的操作

### 算术操作

#### `add(lhs, rhs)`

功能说明：

- 表示逐元素加法。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

C = add(A, B)
D = add(A, 3)
```

语义：

- `C.shape == ["M", "N"]`
- `D.shape == ["M", "N"]`

### 广播操作

#### `broadcast(value, shape)`

功能说明：

- 表示显式广播。
- 用于把一个 `Memory` 从原 `shape` 扩张为给定目标 `shape`，供后续逐元素运算或其他上层语义复用。

参数说明：

- `value`：待广播的输入，必须为 `Memory`。
- `shape`：目标 `shape`，必须是与 `Memory.shape` 同口径的维度序列。

使用示例：

```python
from python.operation.nn import broadcast
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

value = Memory(shape=[1, "N"], dtype=NumericType.Float32)

out = broadcast(value, ["M", "N"])
```

注意事项：

- `broadcast` 只定义显式广播；逐元素算术/比较虽然支持隐式 broadcast，但显式 `broadcast` 仍用于复用扩张结果、跨多步组合或在分层边界上显式表达广播语义。
- 本层不规定零步幅复用、物化复制或其他底层实现策略；只规定用户可观察到的张量语义。

返回与限制：

- 返回新的 `Memory` 结果对象。
- `out.shape == shape`。
- `out.dtype == value.dtype`。
- `out.space == value.space`。
- `out.stride` 可由实现返回兼容的广播布局信息或 `None`，但不得伪造与目标 rank 不一致的步幅信息。

#### `sub(lhs, rhs)`

功能说明：

- 表示逐元素减法。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

C = sub(A, B)
D = sub(A, 1)
```

语义：

- `C.shape == ["M", "N"]`
- `D.shape == ["M", "N"]`

#### `mul(lhs, rhs)`

功能说明：

- 表示逐元素乘法。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

C = mul(A, B)
D = mul(A, 2)
```

语义：

- `C.shape == ["M", "N"]`
- `D.shape == ["M", "N"]`

#### `truediv(lhs, rhs)`

功能说明：

- 表示逐元素除法。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

C = truediv(A, B)
D = truediv(A, 2)
```

语义：

- `C.shape == ["M", "N"]`
- `D.shape == ["M", "N"]`

### 矩阵乘操作

#### `matmul(lhs, rhs)`

功能说明：

- 表示二维矩阵乘。
- 用于表达 `lhs[M, K] @ rhs[K, N] -> result[M, N]` 的高层张量语义。

参数说明：

- `lhs`：左操作数，必须为二维 `Memory`。
- `rhs`：右操作数，必须为二维 `Memory`。

使用示例（目标 API 形态，当前 `main` 尚未实现）：

```python
from python.operation.nn import matmul
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

lhs = Memory(shape=["M", "K"], dtype=NumericType.Float32)
rhs = Memory(shape=["K", "N"], dtype=NumericType.Float32)

out = matmul(lhs, rhs)
```

注意事项：

- 当前 `matmul` 只定义二维 `Memory x Memory` 语义。
- 不支持标量参与、batch 维、广播、隐式转置或空间转换。
- 当前根上的 [`python/operation/nn.py`](../../python/operation/nn.py) 与 [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py) 尚未提供 `matmul`；本节先定义后续实现与测试必须满足的契约。

返回与限制：

- 返回新的 `Memory` 结果对象。
- `out.shape == ["M", "N"]`。
- `out.dtype` 继承兼容后的输入 `dtype`；当前若未定义类型提升，则要求 `lhs.dtype == rhs.dtype` 且结果继承该 `dtype`。
- `out.space` 继承输入空间；当前要求 `lhs.space == rhs.space`。
- `out.stride` 可由实现按兼容布局规则决定，但不得丢失 rank 与动态维度信息。

### 比较操作

#### `eq(lhs, rhs)`

功能说明：

- 表示逐元素相等比较。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

CMP = eq(A, B)
```

语义：

- `CMP.shape == ["M", "N"]`
- `CMP.dtype is NumericType.Int32`
- `CMP.dtype` 的语义是 predicate，而不是普通算术 `Int32`

#### `ne(lhs, rhs)`

功能说明：

- 表示逐元素不等比较。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

CMP = ne(A, B)
```

#### `lt(lhs, rhs)`

功能说明：

- 表示逐元素小于比较。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")

CMP = lt(A, 0)
```

#### `le(lhs, rhs)`

功能说明：

- 表示逐元素小于等于比较。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")

CMP = le(A, 0)
```

#### `gt(lhs, rhs)`

功能说明：

- 表示逐元素大于比较。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

CMP = gt(A, B)
```

#### `ge(lhs, rhs)`

功能说明：

- 表示逐元素大于等于比较。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

CMP = ge(A, B)
```

## 输入约束

### Memory 与 Memory

- `lhs` 与 `rhs` 均为 `Memory` 或等价的张量语义对象。
- `lhs.shape` 与 `rhs.shape` 可以完全一致，也可以满足与 `broadcast` 相同的尾维对齐与 singleton dim 扩张规则。
- 若两侧需要隐式 broadcast，则共同目标 `shape` 按尾维对齐规则推导，结果 `shape` 等于该共同目标 `shape`。
- `lhs.dtype` 与 `rhs.dtype` 必须可兼容；若当前阶段未定义类型提升规则，则要求二者完全一致。
- `lhs.stride` 与 `rhs.stride` 可以不同；布局差异不影响本层逐元素语义合法性。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

C = add(A, B)
```

### Memory 与标量

- 支持 `Memory` 与数值标量进行二元运算。
- 第一阶段至少支持 `int`；后续可按 `dtype` 体系扩展到 `float` 等数值类型。
- 标量类型必须与 `Memory.dtype` 兼容；不兼容时抛 `TypeError`。
- 标量参与运算时，结果 `shape` 与 `stride` 继承 `Memory`。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")

B = add(A, 3)
C = mul(A, 2)
```

### 链式表达式

- 链式表达式按从左到右逐步求值。
- 每一步的中间结果都必须仍然满足本规范中的输入约束、shape 规则与 dtype 规则。

示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

C = add(add(A, 3), B)
```

### `matmul`

- `lhs` 与 `rhs` 必须都是 `Memory`。
- `lhs.rank == 2` 且 `rhs.rank == 2`。
- `lhs.shape == [M, K]`，`rhs.shape == [K, N]`；其中 contracting dim `K` 必须语义一致。
- 当前阶段不支持 `Memory` 与标量的 `matmul`，也不支持纯标量乘法映射为 `matmul`。
- `lhs.dtype` 与 `rhs.dtype` 必须兼容；若当前阶段未定义类型提升规则，则要求二者完全一致。
- 当前高层 API 不负责跨空间搬运；若显式携带 `space`，则要求 `lhs.space == rhs.space`。

示例：

```python
lhs = Memory(shape=["M", "K"], dtype=NumericType.Float32)
rhs = Memory(shape=["K", "N"], dtype=NumericType.Float32)

out = matmul(lhs, rhs)
```

### `broadcast`

- `value` 必须为 `Memory`。
- `shape` 必须是与 `Memory.shape` 同口径的目标维度序列。
- 目标 `shape` 的 rank 必须大于或等于 `value.rank`。
- 广播按尾维对齐。
- 对齐后的每一维只有两种合法情形：
  - `value` 的该维与目标维语义一致。
  - `value` 的该维是静态整数 `1`，允许扩张到任意目标维。
- 若目标 `shape` 比输入多出前置维，这些维被视为新增广播维。
- `broadcast` 不改变 `dtype` 与 `space`；当前高层 API 不负责隐式类型转换或跨空间搬运。
- `?` 仅在与同为 `?` 的维度比较时视为直接一致；它不是“可匹配任意非 1 维”的通配符。

示例（目标 API 形态，当前 `main` 尚未实现）：

```python
value = Memory(shape=[1, "N"], dtype=NumericType.Float32)

out = broadcast(value, ["M", "N"])
```

## 类型合法性规则

- 算术操作只接受 `Memory` 或受支持的数值标量类型作为输入。
- 比较操作只接受 `Memory` 或受支持的数值标量类型作为输入。
- `broadcast` 只接受 `Memory` 作为输入值，以及合法的目标 `shape` 描述。
- 不支持的 Python 对象类型，例如 `str`、`list`、`dict`、任意无数值语义的自定义对象，必须抛 `TypeError`。
- 若 `Memory.dtype` 为空，可在实现中延后推导；但在未完成推导前，不得默认所有类型都合法。
- `Memory + scalar`、`Memory - scalar`、`Memory * scalar`、`Memory / scalar` 都必须检查标量与 `Memory.dtype` 的兼容性。
- `Memory + Memory`、`Memory == Memory` 等双张量运算都必须检查两侧 `dtype` 是否可兼容。
- `broadcast` 的目标 `shape` 若不是合法维度序列，必须抛 `TypeError` 或 `ValueError`，且实现需保持错误口径一致。
- 链式表达式只要某一步类型不合法，整个表达式立即失败。

## Shape 规则

- 逐元素算术与比较支持隐式 broadcast。
- 若两个张量语义对象的 `shape` 完全一致，则直接执行二元逐元素运算。
- 若两个张量语义对象的 `shape` 不完全一致，但满足与 `broadcast` 相同的尾维对齐与 singleton dim 扩张规则，则概念上先隐式 broadcast 到共同目标 `shape`，再执行原始逐元素运算。
- “完全一致”指逐维表达式语义一致，例如 `[A, B]` 与 `[A, B]` 一致，`[A, B]` 与 `[B, A]` 不一致，`[A, B]` 与 `[A, C]` 不一致。
- 对于 rank 不同的双张量逐元素运算，较小 rank 的一侧按前置维补 singleton 参与尾维对齐；这只定义高层语义，不要求实现物化复制。
- 若对齐后的某一维既不相等，也不存在静态 `1` 可扩张，则隐式 broadcast 失败并报错。
- 对链式表达式按从左到右的中间结果逐步判定；只要每一步都满足 shape 规则，则最终结果合法。
- `broadcast` 使用尾维对齐规则，而不是逐元素运算的“整体 shape 严格相等”规则。
- `broadcast(value, target_shape)` 只有在每个对齐维都满足“相等”或“输入维是静态 1”时才合法。
- `broadcast` 若目标 rank 小于输入 rank，或存在非 singleton 的不兼容维，必须失败。
- `matmul` 不使用逐元素 shape 相等规则，而使用二维收缩规则：`lhs.shape=[M, K]`、`rhs.shape=[K, N]`、`result.shape=[M, N]`。
- `matmul` 若任一输入不是二维，或 contracting dim 不一致，必须失败。

错误示例：

- `tensor([A, B]) + tensor([A, C])`：错误，第二维不一致。
- `tensor([A, B]) + tensor([A])`：错误，rank 不一致。
- `tensor([A, B]) + tensor([B, A])`：错误，shape 顺序不同。
- `tensor([A, B]) + 3 + tensor([A, C])`：错误，最后一步 shape 不一致。
- `broadcast(tensor([M, N]), [N])`：错误，目标 rank 小于输入 rank。
- `broadcast(tensor([M, N]), [M, K])`：错误，第二维既不相等也不是 singleton dim。
- `broadcast(tensor([1, N]), [M, N])`：合法，第一维从 `1` 扩张到 `M`。
- `add(tensor([1, B]), tensor([A, B]))`：合法，高层语义下先把左侧隐式 broadcast 到 `[A, B]`。
- `eq(tensor([B]), tensor([A, B]))`：合法，高层语义下把左侧按前置 singleton 参与隐式 broadcast，结果 `shape=[A, B]`。
- `matmul(tensor([M, K]), tensor([Q, N]))`：错误，contracting dim 不一致。
- `matmul(tensor([B, M, K]), tensor([K, N]))`：错误，当前阶段不支持 batch matmul。

## Dtype 规则

- 算术操作输出 `dtype` 默认继承输入 `dtype`，或由受控的显式类型规则决定。
- 比较操作在语义上输出 `bool/predicate`。
- 在当前 `python.operation.nn` 与 `Memory` 实现中，比较结果没有独立的 `bool` 类型载体，因此具体 `dtype` 固定为 `NumericType.Int32`。
- 若两个输入 `dtype` 不兼容，应抛出 `TypeError`。
- 若 `Memory + scalar` 中 scalar 类型与 `Memory.dtype` 不兼容，应抛出 `TypeError`。
- 链式表达式中的中间结果也必须满足后续运算的 `dtype` 合法性。
- `broadcast` 保持 `value.dtype` 不变，不引入新的类型提升规则。
- `matmul` 的两个输入 `dtype` 也必须兼容；若当前阶段未定义类型提升，则要求两侧 `dtype` 完全一致。
- `matmul` 输出 `dtype` 继承兼容后的输入 `dtype`，不单独引入 accumulator dtype 或混合精度规则。

## 输出语义

### 算术操作输出

- 输出为张量语义结果对象，可继续参与后续算术或比较运算。
- 若输入 `shape` 完全一致，则输出 `shape` 继承输入张量的 `shape`；若触发隐式 broadcast，则输出 `shape` 为共同目标 `shape`。
- 输出 `stride` 继承输入张量的 `stride`，或由实现按兼容规则确定，但不得丢失 rank 与动态维度信息。
- 若输入 `shape` 中包含符号维度，如 `[A, B]`，输出应保持共同结果中的对应符号维度。

示例：

- `tensor([A, B]) + tensor([A, B]) -> tensor([A, B])`
- `tensor([A, B]) + 1 -> tensor([A, B])`
- `tensor([A, B]) + 3 + tensor([A, B]) -> tensor([A, B])`

### 比较操作输出

- 输出为逐元素比较后的张量语义结果，不是单个标量 `bool`。
- 若输入 `shape` 完全一致，则输出 `shape` 与输入相同；若触发隐式 broadcast，则输出 `shape` 为共同目标 `shape`。
- 输出 `dtype` 的语义为 predicate。
- 当前实现/测试的具体契约为 `NumericType.Int32`。

示例：

- `eq(tensor([A, B]), tensor([A, B])) -> tensor([A, B], dtype=NumericType.Int32)`

### `broadcast` 输出

- 输出为新的张量语义结果对象，可继续参与后续算术、比较、`broadcast` 或其他上层语义组合。
- 输出 `shape` 为目标 `shape`。
- 输出 `dtype` 与输入 `value.dtype` 相同。
- 输出 `space` 与输入 `value.space` 相同。
- 输出 `stride` 不要求简单继承输入；实现可选择兼容的广播布局信息或 `None`，但不得丢失目标 rank 与动态维度信息。

### `matmul` 输出

- 输出为新的张量语义结果对象，可继续参与后续逐元素运算、比较或其他上层语义组合。
- 输出 `shape` 为 `[M, N]`，其中 `M` 来自左操作数第一维，`N` 来自右操作数第二维。
- 输出 `dtype` 继承兼容后的输入 `dtype`。
- 输出 `space` 继承输入空间；当前要求 `lhs.space == rhs.space`，且结果空间不隐式变化。
- 输出 `stride` 不要求简单继承左/右输入任一侧；实现可返回兼容布局或 `None`，但不得伪造与结果 rank 不一致的步幅信息。

## 独立使用示例

```python
from python.operation.nn import add, broadcast, eq
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

X = Memory(shape=["A", "B"], dtype=NumericType.Float32)
Y = Memory(shape=["A", "B"], dtype=NumericType.Float32)
S = Memory(shape=[1, "B"], dtype=NumericType.Float32)

Z = add(add(X, 3), Y)
IB = add(X, S)
B = broadcast(S, ["A", "B"])
CMP = eq(X, Y)
```

语义约束：

- `Z.shape == ["A", "B"]`
- `IB.shape == ["A", "B"]`
- `B.shape == ["A", "B"]`
- `CMP.shape == ["A", "B"]`
- `CMP.dtype is NumericType.Int32`
- `CMP.dtype` 在语义上表示 predicate，而不是普通算术 `Int32`
- 若 `Y.shape == ["A", "C"]`，则运算失败
- 若 `S.shape == [2, "B"]`，则 `broadcast(S, ["A", "B"])` 失败
- 若 `X.dtype` 与 `Y.dtype` 不兼容，或标量类型不兼容，则运算失败

## 与上层系统的关系

- 上层前端可以直接复用本规范中的算术与比较规则。
- 上层前端可以直接复用本规范中的 `broadcast` 语义，而不必自行定义一套不同的尾维对齐规则。
- 上层前端可以直接复用本规范中的 `matmul` 语义，而不必自行重新定义二维矩阵乘的 shape/dtype/space 规则。
- 若上层需要构造 AST 或 IR，应捕获本层语义，而不是重新定义另一套 shape/dtype 规则。
- 上层系统不得改变本层关于“逐元素 op 允许隐式 broadcast、`matmul` 不允许隐式 broadcast”和“先检查类型合法性”的基本约束。

## 与 `nn dialect broadcast` 的分层关系

- `operation/nn.broadcast` 负责定义用户侧高层 API 语义，包括尾维对齐、singleton dim 扩张、返回 `Memory` 语义和错误规则。
- `nn dialect broadcast` 的 op 名称、operand/result type、verifier、parse/print round-trip 约束由 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 定义，并作为方言层落地载体。
- `operation/nn` 不得在本层直接引入 xDSL op、attribute 或 verifier 细节；它只提供高层张量扩张语义，不承担方言表示。

## 与 lowering 的分层关系

- `operation/nn` 允许逐元素算术与比较在高层语义中使用隐式 broadcast。
- `nn dialect` 的二元逐元素 op 不承载隐式 broadcast；若上游存在 broadcast-compatible 但 shape 不相等的双张量逐元素运算，lowering 必须先显式插入一个或多个 `nn.broadcast`，再生成原始二元 op。
- lowering 对隐式 broadcast 的展开必须保持与本文件 `broadcast` 相同的尾维对齐和 singleton dim 扩张规则，不得自行引入另一套兼容性判断。
- 若某个逐元素表达式无法按本文件规则推导共同目标 `shape`，lowering 必须在进入 `nn dialect` 前失败，而不是生成一个依赖方言层“隐式广播”的非法 op。

## 与 `nn dialect matmul` 的分层关系

- `operation/nn.matmul` 负责定义用户侧高层 API 语义，包括输入 rank、contracting dim、返回 `Memory` 语义和错误规则。
- 未来若引入 `nn dialect matmul`，其 op 名称、operand/result type、verifier、parse/print round-trip 约束必须在 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 中单独定义。
- `operation/nn` 不得在本层直接引入 xDSL op、attribute 或 verifier 细节；它只提供高层语义，不承担方言表示。
- 当前 `main` 上的 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 尚未定义 `nn.matmul`；因此 `matmul` 链路目前仅完成高层 API 契约，尚未形成与方言层、实现层、测试层的一一闭环。

## 返回与错误

### 成功返回

- 算术操作返回张量语义结果；若输入 `shape` 完全一致，则结果 `shape` 与输入一致；若触发隐式 broadcast，则结果 `shape` 为共同目标 `shape`。
- 比较操作返回张量语义结果；若输入 `shape` 完全一致，则结果 `shape` 与输入一致；若触发隐式 broadcast，则结果 `shape` 为共同目标 `shape`；语义上为 predicate，当前具体 `dtype` 为 `NumericType.Int32`。
- `broadcast` 返回张量语义结果，`shape` 为目标 `shape`，`dtype/space` 保持输入值不变。

### 失败返回

- 输入类型不支持时抛 `TypeError`。
- 两个张量语义对象无法按隐式 broadcast 规则推导共同目标 `shape` 时抛 `ValueError`。
- `dtype` 不兼容时抛 `TypeError`。
- 链式表达式任一步的输入类型不合法时抛 `TypeError`。
- `broadcast` 的输入值不是 `Memory` 时抛 `TypeError`。
- `broadcast` 的目标 `shape` 不是合法维度序列时抛 `TypeError` 或 `ValueError`。
- `broadcast` 的目标 rank 小于输入 rank 时抛 `ValueError`。
- `broadcast` 存在非 singleton 的不兼容维时抛 `ValueError`。
- `matmul` 任一输入不是 `Memory` 时抛 `TypeError`。
- `matmul` 任一输入 rank 不是 2 时抛 `ValueError`。
- `matmul` 的 contracting dim 不一致时抛 `ValueError`。
- `matmul` 的 `dtype` 不兼容时抛 `TypeError`。
- `matmul` 的 `space` 不一致时抛 `ValueError`。

## 测试

- 测试文件：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- 执行命令：`pytest -q test/operation/test_operation_nn.py`

### 测试目标

- 验证运算层可独立于任意上层接口被直接调用。
- 验证 `Memory + Memory` 在 shape 完全一致或可按隐式 broadcast 对齐时都可参与逐元素运算。
- 验证 `Memory + scalar` 保持原 `shape`。
- 验证逐元素隐式 broadcast 复用 `broadcast` 的尾维对齐、singleton dim 扩张与前置维插入规则。
- 验证 `broadcast` 的尾维对齐、singleton dim 扩张和前置维插入规则。
- 验证链式表达式如 `A + 3 + B` 在每一步都执行 shape 与类型合法性检查。
- 验证比较操作输出保持相同 `shape`，且语义上为 predicate、当前具体 `dtype` 为 `NumericType.Int32`。
- 验证 `eq/lt/gt/ne/le/ge` 等比较 API 的比较结果口径一致。
- 验证纯标量输入（两侧均非 `Memory`）抛 `TypeError`。
- 验证比较别名 API（`ne/le/ge`）返回 `NumericType.Int32` 且 shape 保持一致。
- 验证运算链路不依赖 `SymbolList/ SymbolShape` 已移除的 `convert_from_list` 入口，且 stride 可正常保持。
- 验证 shape 不一致与类型不兼容时稳定报错。
- 当前根上已通过 `OP-IB-001..004` 覆盖双张量逐元素隐式 broadcast 的正向与关键反向路径。
- 当前根上测试尚未覆盖 `matmul`；后续实现/测试任务需补齐 `matmul` 的正向与反向用例。

### 测试标准

- 所有 shape 校验路径可稳定复现。
- 所有类型合法性错误路径可稳定复现。
- 动态 shape 在运算结果中不丢失。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 当前测试映射 |
|---|---|---|---|---|---|---|
| OP-001 | 独立调用 | 普通 Python 中使用 | `X.shape=[A,B]`, `Y.shape=[A,B]` | `add(X, Y)` | 返回 shape=`[A,B]` 的动态结果 | `test_nn_add_memory` |
| OP-002 | 算术 | 同 shape 相加 | `lhs.shape=[A,B]`, `rhs.shape=[A,B]` | `lhs + rhs` 或 `add(lhs, rhs)` | 返回 shape=`[A,B]` 的动态结果 | `test_nn_other_arithmetic` |
| OP-003 | 算术 | shape 不一致 | `lhs.shape=[A,B]`, `rhs.shape=[A,C]` | `add(lhs, rhs)` | 抛 `ValueError` | `test_nn_shape_mismatch` |
| OP-004 | 算术 | rank 不一致 | `lhs.shape=[A,B]`, `rhs.shape=[A]` | `add(lhs, rhs)` | 抛 `ValueError` | `test_nn_rank_mismatch` |
| OP-005 | 算术 | Memory 与标量 | `lhs.shape=[A,B]`, `lhs.dtype=float32` | `add(lhs, 1)` | 返回 shape=`[A,B]` 的动态结果 | `test_nn_add_scalar` |
| OP-006 | 算术 | 链式表达式 | `lhs.shape=[A,B]`, `rhs.shape=[A,B]` | `add(add(lhs, 3), rhs)` | 返回 shape=`[A,B]` 的动态结果 | `test_nn_chain_expression` |
| OP-007 | 类型 | 标量类型不合法 | `lhs.dtype=float32` | `add(lhs, "3")` | 抛 `TypeError` | `test_nn_scalar_type_error` |
| OP-008 | 类型 | Memory dtype 不兼容 | `lhs.dtype=float32`, `rhs.dtype=int32` | `add(lhs, rhs)` | 抛 `TypeError` | `test_nn_dtype_mismatch` |
| OP-009 | 比较 | 同 shape 比较 | `lhs.shape=[A,B]`, `rhs.shape=[A,B]` | `eq(lhs, rhs)` | 返回 shape=`[A,B]` 且 dtype=`NumericType.Int32` 的结果；其语义为 predicate | `test_nn_compare_predicate` |
| OP-010 | 比较 | shape 顺序不同 | `lhs.shape=[A,B]`, `rhs.shape=[B,A]` | `eq(lhs, rhs)` | 抛 `ValueError` | `test_nn_compare_shape_order` |
| OP-011 | 类型 | 纯标量输入 | `lhs=1`, `rhs=2` | `add(lhs, rhs)` | 抛 `TypeError` | `test_nn_scalar_only_error` |
| OP-012 | 比较 | 别名 API | `lhs.shape=[A]`, `rhs.shape=[A]` | `ne/le/ge(lhs, rhs)` | 返回 `NumericType.Int32` 且 shape 保持一致 | `test_nn_compare_alias` |
| OP-013 | 兼容 | 去除 convert_from_list | `lhs.shape=[N,32]`, `lhs.stride=[C,1]` | `add(lhs, rhs)` | 不依赖 `convert_from_list`，且结果 stride 不为空并保持为 `["C", 1]` | `test_nn_operation_does_not_require_convert_from_list` |
| OP-BC-001 | `broadcast` | 基础 singleton 扩张 | `value.shape=[1,N]` | `broadcast(value, [M,N])` | 返回 `shape=[M,N]`、`dtype/space` 保持不变的结果 | `test_nn_broadcast_success` |
| OP-BC-002 | `broadcast` | 插入前置维 | `value.shape=[N]` | `broadcast(value, [M,N])` | 返回 `shape=[M,N]` 的结果 | `test_nn_broadcast_prepend_dimension` |
| OP-BC-003 | `broadcast` | 非 singleton 不兼容维 | `value.shape=[M,N]` | `broadcast(value, [M,K])` | 抛 `ValueError` | `test_nn_broadcast_dimension_mismatch` |
| OP-BC-004 | `broadcast` | 目标 rank 更小 | `value.shape=[M,N]` | `broadcast(value, [N])` | 抛 `ValueError` | `test_nn_broadcast_rank_error` |
| OP-BC-005 | `broadcast` | 非 Memory 输入非法 | `value=1` | `broadcast(value, [M,N])` | 抛 `TypeError` | `test_nn_broadcast_non_memory_error` |
| OP-BC-006 | `broadcast` | 非法目标 shape 描述 | `value.shape=[1,N]` | `broadcast(value, "MN")` | 抛 `TypeError` 或 `ValueError` | `test_nn_broadcast_invalid_shape_error` |

### 逐元素隐式 `broadcast` 测试清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 当前测试映射 |
|---|---|---|---|---|---|---|
| OP-IB-001 | 隐式 `broadcast` | singleton dim 扩张 | `lhs.shape=[1,B]`, `rhs.shape=[A,B]` | `add(lhs, rhs)` | 返回 `shape=[A,B]` 的结果 | `test_nn_add_implicit_broadcast_singleton` |
| OP-IB-002 | 隐式 `broadcast` | 前置维插入 | `lhs.shape=[B]`, `rhs.shape=[A,B]` | `add(lhs, rhs)` | 返回 `shape=[A,B]` 的结果 | `test_nn_add_implicit_broadcast_prepend_dimension` |
| OP-IB-003 | 隐式 `broadcast` | 比较运算复用广播规则 | `lhs.shape=[1,B]`, `rhs.shape=[A,B]` | `eq(lhs, rhs)` | 返回 `shape=[A,B]` 且 `dtype=NumericType.Int32` 的结果 | `test_nn_compare_implicit_broadcast` |
| OP-IB-004 | 隐式 `broadcast` | 非兼容维仍报错 | `lhs.shape=[A,B]`, `rhs.shape=[A,C]`, `B != C` | `add(lhs, rhs)` | 抛 `ValueError` | `test_nn_add_implicit_broadcast_mismatch` |

### `matmul` 待补测试清单

当前 [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py) 尚无 `matmul` 对应用例；以下为后续实现/测试任务必须补齐的建议清单。

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
|---|---|---|---|---|---|---|
| OP-MM-001 | `matmul` | 基础二维矩阵乘 | `lhs.shape=[M,K]`, `rhs.shape=[K,N]`, `lhs.dtype==rhs.dtype` | `matmul(lhs, rhs)` | 返回 `shape=[M,N]`、`dtype` 继承输入、`space` 保持一致的结果 | `test_nn_matmul_success` |
| OP-MM-002 | `matmul` | contracting dim 不一致 | `lhs.shape=[M,K]`, `rhs.shape=[Q,N]`, `K != Q` | `matmul(lhs, rhs)` | 抛 `ValueError` | `test_nn_matmul_contracting_dim_mismatch` |
| OP-MM-003 | `matmul` | 非二维输入 | `lhs.shape=[B,M,K]`, `rhs.shape=[K,N]` | `matmul(lhs, rhs)` | 抛 `ValueError` | `test_nn_matmul_rank_error` |
| OP-MM-004 | `matmul` | 标量输入非法 | `lhs=Memory([M,K], ...)`, `rhs=1` | `matmul(lhs, rhs)` | 抛 `TypeError` | `test_nn_matmul_scalar_operand_error` |
| OP-MM-005 | `matmul` | dtype 不兼容 | `lhs.dtype=float32`, `rhs.dtype=int32` | `matmul(lhs, rhs)` | 抛 `TypeError` | `test_nn_matmul_dtype_mismatch` |
| OP-MM-006 | `matmul` | space 不一致 | `lhs.space=GM`, `rhs.space=SM` | `matmul(lhs, rhs)` | 抛 `ValueError` | `test_nn_matmul_space_mismatch` |
