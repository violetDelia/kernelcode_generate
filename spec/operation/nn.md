# nn.md

## 功能简介

用于定义 `Memory` 高层运算规范，覆盖逐元素算术、比较、激活函数、显式 `broadcast` / `broadcast_to`、`softmax`、全连接 `fc`、二维 `matmul` 与二维 `conv`。本层只描述可调用语义、结果元信息约束与错误规则。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `功能实现`：[`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
- `test`：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)

## 依赖

- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：定义 `Memory` 的 `shape`/`stride`/`dtype`/`space` 基础语义。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：定义 `NumericType` 与 `Farmat` 的公开枚举语义，比较结果中的 `NumericType.Bool` 以该文档为准。

## 目标

- 提供 `Memory` 的逐元素算术与比较高层语义。
- 提供常用激活函数的输入输出约束与错误规则。
- 提供显式 `broadcast` / `broadcast_to`、`softmax`、全连接 `fc`、二维 `matmul` 与二维 `conv` 的输入输出约束与错误规则。
- 保持与下游 `nn dialect` 的分层：本层作为用户直接使用的接口，不受限于IR的表达。

## 限制与边界

- 逐元素算术/比较支持隐式广播，仅允许尾维对齐与 singleton dim 扩张。
- `transpose` 仅支持 `Memory` 输入与显式轴置换，不支持标量或隐式转置。
- `fc` 仅定义“输入末维 × 权重输入特征维”的全连接语义；`bias` 为可选参数。
- `matmul` 仅定义二维矩阵乘，不支持 batch、广播或隐式转置。
- `softmax` 仅支持 `Memory` 输入，默认沿最后一维归一化，不负责跨算子融合或近似策略选择。
- `conv` 仅覆盖二维卷积，不支持 group、batch/broadcast 或隐式转置。
- 不定义归约等其他算子。
- 不引入超出本文规则的复杂自动类型提升；`dtype` 兼容性需显式检查。
- 不负责 AST/IR/lowering 设计。
- 激活函数仅支持 `Memory` 输入；输出 `shape`/`dtype`/`space`/`format`/`stride` 继承输入，仅允许浮点 `dtype`（`Float16`/`BFloat16`/`Float32`/`Float64`）。

## nn 类型提升规则（算术算子统一口径）

- 统一优先级（低精度 -> 高精度）为：`Int8`、`Uint8`、`Int16`、`Uint16`、`Int32`、`Uint32`、`Int64`、`Uint64`、`Float16`、`BFloat16`、`Float32`、`Float64`。
- `Memory/Memory` 路径按上述优先级选择顺序更靠后的类型（高优先级）。
- `Memory/标量` 路径中，标量按 `NumericType.Int32` 参与同一优先级决议，再选择顺序更靠后的类型。
- 适用范围：`add`、`sub`、`mul`、`truediv`、`floordiv`、`matmul`。
- 整数与浮点混合时，结果必须提升到浮点，并取浮点侧更高优先级类型。
- 反例与边界：
  - 比较算子（`eq/ne/lt/le/gt/ge`）不使用该提升规则，结果 `dtype` 固定为 `NumericType.Bool`。
  - `broadcast` / `broadcast_to` / `transpose` 不做算术类型提升，结果 `dtype` 由接口约束决定。
  - 纯标量路径复用 Python/SymbolDim 算术语义，不纳入 `Memory` 类型提升决议。
  - 不支持的 `dtype`（不在优先级列表或 `NumericType.Bool` 参与算术提升）必须抛出 `TypeError`。

## 公开接口

### `add(lhs, rhs)`

功能说明：

- 逐元素加法。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
from kernel_gen.operation.nn import add
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import Farmat, NumericType

A = Memory(["M", "N"], NumericType.Int32)
B = Memory([1, "N"], NumericType.Int32)
C = add(A, B)

lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.CLast)
rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.Norm)
D = add(lhs, rhs)

assert C.get_shape() == ["M", "N"]
assert D.get_format() is Farmat.Norm
assert D.get_stride()[1] == 1
```

注意事项：

- `Memory` 与 `Memory` 可触发隐式 broadcast；广播规则为尾维对齐，较低 rank 一侧按前置维补 `1` 后参与比较。
- 对齐后的任一维若既不相等，也不包含 `1`，必须抛出 `ValueError`。
- `Memory/Memory` 路径的 `dtype` 按固定优先级决议：`Int8`、`Uint8`、`Int16`、`Uint16`、`Int32`、`Uint32`、`Int64`、`Uint64`、`Float16`、`BFloat16`、`Float32`、`Float64`；结果选择顺序更靠后的类型。
- `Memory/标量` 路径标量视作 `NumericType.Int32`，结果 `dtype` 按相同优先级选择顺序更靠后的类型。
- 当两侧 `shape`、`dtype`、`format`、`stride` 一致时，结果保持原有 `Memory` 描述。
- 当 `format` 或 `stride` 任一不一致时，结果必须回落到默认布局：`format=Farmat.Norm`，`stride` 使用连续行主序默认步幅。
- 默认步幅与其字符串化口径沿用 [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：公开接口继续通过 `Memory.get_stride()` 返回步幅分量，`str` / `repr` 继续使用 `Shape(...)` 序列化表示。
- 标量与 `Memory` 运算必须检查 `dtype` 兼容性。

返回与限制：

- 返回 `Memory` 语义结果。
- `shape` 为输入一致时的原 `shape`，或隐式广播的共同目标 `shape`。
- `Memory/Memory` 路径返回的 `dtype` 必须满足上述固定优先级决议。
- 纯标量输入必须抛出 `TypeError`。

### `sub(lhs, rhs)`

功能说明：

- 逐元素减法。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
C = sub(A, B)
D = sub(A, 1)
```

注意事项：

- 规则同 `add`。

返回与限制：

- 返回 `Memory` 语义结果。

### `mul(lhs, rhs)`

功能说明：

- 逐元素乘法。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
C = mul(A, B)
D = mul(A, 2)
```

注意事项：

- 规则同 `add`。

返回与限制：

- 返回 `Memory` 语义结果。

### `truediv(lhs, rhs)`

功能说明：

- 逐元素除法。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
C = truediv(A, B)
D = truediv(A, 2)
```

注意事项：

- 规则同 `add`。

返回与限制：

- 返回 `Memory` 语义结果。

### `floordiv(lhs, rhs)`

功能说明：

- 逐元素整除。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
C = floordiv(A, B)
D = floordiv(A, 2)
```

注意事项：

- 复用 `add` 的隐式 broadcast、固定 `dtype` 优先级与标量参与规则。
- 当 `format` 或 `stride` 任一不一致时，结果必须回落到默认布局：`format=Farmat.Norm`，`stride` 使用连续行主序默认步幅。
- 纯标量输入必须抛出 `TypeError`。

返回与限制：

- 返回 `Memory` 语义结果。

### `eq(lhs, rhs)`

功能说明：

- 逐元素相等比较。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
CMP = eq(A, B)
```

注意事项：

- 比较结果语义为 predicate。
- 比较结果 `dtype` 固定为 `NumericType.Bool`。
- 复用 `add` 的隐式 broadcast 规则；与标量比较时，结果 `shape` 保持 `Memory` 的目标 `shape`。

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `ne(lhs, rhs)`

功能说明：

- 逐元素不等比较。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
CMP = ne(A, B)
```

注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `lt(lhs, rhs)`

功能说明：

- 逐元素小于比较。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
CMP = lt(A, 0)
```

注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `le(lhs, rhs)`

功能说明：

- 逐元素小于等于比较。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
CMP = le(A, 0)
```

注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `gt(lhs, rhs)`

功能说明：

- 逐元素大于比较。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
CMP = gt(A, B)
```

注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `ge(lhs, rhs)`

功能说明：

- 逐元素大于等于比较。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
CMP = ge(A, B)
```

注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `relu(value)`

功能说明：

- 逐元素 ReLU 激活。

参数说明：

- `value` (`Memory`)：待激活输入。

使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = relu(value)
```

注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `TypeError`。
- 数值语义：`relu(x) = max(x, 0)`，`x == 0` 时返回 `0`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

返回与限制：

- 返回 `Memory` 语义结果。

### `leaky_relu(value, alpha=0.01)`

功能说明：

- 逐元素 Leaky ReLU 激活。

参数说明：

- `value` (`Memory`)：待激活输入。
- `alpha` (`int|float`)：负半轴斜率，默认 `0.01`。

使用示例：

```python
value = Memory(["M", "N"], NumericType.Float16)
out = leaky_relu(value, alpha=0.2)
```

注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `TypeError`。
- `alpha` 仅接受 `int|float`，不接受 `bool` 或 `SymbolDim`；非数值或 `NaN/Inf` 触发 `TypeError`/`ValueError`。
- 数值语义：`x >= 0` 时返回 `x`，`x < 0` 时返回 `alpha * x`；`x == 0` 时返回 `0`。当 `alpha == 0` 时退化为 `relu`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

返回与限制：

- 返回 `Memory` 语义结果。

### `sigmoid(value)`

功能说明：

- 逐元素 Sigmoid 激活。

参数说明：

- `value` (`Memory`)：待激活输入。

使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = sigmoid(value)
```

注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `TypeError`。
- 数值语义：`sigmoid(x) = 1 / (1 + exp(-x))`，大幅正/负输入分别趋近 `1/0`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

返回与限制：

- 返回 `Memory` 语义结果。

### `tanh(value)`

功能说明：

- 逐元素 Tanh 激活。

参数说明：

- `value` (`Memory`)：待激活输入。

使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = tanh(value)
```

注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `TypeError`。
- 数值语义：`tanh(x) = (exp(x) - exp(-x)) / (exp(x) + exp(-x))`，大幅正/负输入分别趋近 `1/-1`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

返回与限制：

- 返回 `Memory` 语义结果。

### `hard_sigmoid(value, alpha=0.2, beta=0.5)`

功能说明：

- 逐元素 Hard Sigmoid 激活。

参数说明：

- `value` (`Memory`)：待激活输入。
- `alpha` (`int|float`)：线性项系数，默认 `0.2`。
- `beta` (`int|float`)：线性项偏置，默认 `0.5`。

使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = hard_sigmoid(value, alpha=0.2, beta=0.5)
```

注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `TypeError`。
- `alpha`/`beta` 仅接受 `int|float`，不接受 `bool` 或 `SymbolDim`；非数值或 `NaN/Inf` 触发 `TypeError`/`ValueError`。
- 数值语义：`hard_sigmoid(x) = clamp(alpha * x + beta, 0, 1)`，边界处输出被截断到 `[0, 1]`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

返回与限制：

- 返回 `Memory` 语义结果。

### `broadcast(value, target)`

功能说明：

- 显式广播，把 `value` 扩张到目标 `target`。

参数说明：

- `value` (`Memory`)：待广播输入。
- `target` (`Memory`)：目标输出描述，提供结果的 `shape`、`dtype`、`space`、`stride` 与 `format`。

使用示例：

```python
value = Memory(shape=[1, "N"], dtype=NumericType.Float32)
target = Memory(shape=["M", "N"], dtype=NumericType.Float32, stride=["N", 1], format=Farmat.Norm)
out = broadcast(value, target)
```

注意事项：

- 广播使用尾维对齐与 singleton dim 扩张规则。
- `value` 与 `target` 都必须为 `Memory`；任一类型不满足时必须抛出 `TypeError`。
- `target.rank` 小于 `value.rank` 或存在非 singleton 维度不兼容时必须抛出 `ValueError`。
- 成功路径下，结果必须完整对齐 `target` 描述，而不是仅继承 `value` 的 `dtype` 或 `space`。

返回与限制：

- 返回 `Memory` 语义结果。
- `out.shape == target.shape`。
- `out.dtype == target.dtype`。
- `out.space == target.space`。
- `out.format == target.format`。
- `out.stride == target.stride`。

### `broadcast_to(value, target)`

功能说明：

- `broadcast` 的等价公开别名，使用相同的显式目标 `Memory` 描述。

参数说明：

- `value` (`Memory`)：待广播输入。
- `target` (`Memory`)：目标输出描述。

使用示例：

```python
value = Memory(shape=[1, "N"], dtype=NumericType.Float32)
target = Memory(shape=["M", "N"], dtype=NumericType.Float32, stride=["N", 1], format=Farmat.Norm)
out = broadcast_to(value, target)
```

注意事项：

- 公开语义、错误路径与返回结果约束与 `broadcast(value, target)` 完全一致。

返回与限制：

- 返回 `Memory` 语义结果，且完整对齐 `target` 描述。

### `transpose(value, perm)`

功能说明：

- 按 `perm` 置换维度顺序，返回新的 `Memory` 结果。

参数说明：

- `value` (`Memory`)：待转置输入。
- `perm` (`Sequence[int]`)：轴置换顺序，长度必须与 `value.rank` 一致。

使用示例：

```python
value = Memory(shape=["M", "N", "K"], dtype=NumericType.Float32)
out = transpose(value, perm=[1, 0, 2])
```

注意事项：

- `perm` 必须是 `0..rank-1` 的排列，且不允许重复索引。
- `value` 必须为 `Memory`，`perm` 必须为整数序列。

返回与限制：

- 返回 `Memory` 语义结果。
- `out.shape` 按 `perm` 重排。
- 若 `value.stride` 存在，`out.stride` 按相同 `perm` 重排。
- `out.dtype` 与 `out.space` 继承自 `value`。

### `softmax(value, axis=-1)`

功能说明：

- 沿给定轴对输入执行 softmax 归一化，返回概率分布语义的 `Memory` 结果。

参数说明：

- `value` (`Memory`)：待归一化输入。
- `axis` (`int`)：归一化轴，默认 `-1`（最后一维）。

使用示例：

```python
value = Memory(shape=["M", "N"], dtype=NumericType.Float32)
out = softmax(value)
out_last_dim = softmax(value, axis=1)
```

注意事项：

- `value` 必须为 `Memory`，否则抛出 `TypeError`。
- `value.dtype` 必须为浮点类型：`Float16`、`BFloat16`、`Float32`、`Float64`；其他类型必须抛出 `TypeError`。
- `axis` 必须为整数且不允许 `bool`；非法类型必须抛出 `TypeError`。
- 允许负轴索引；归一化后的 `axis` 必须满足 `-rank <= axis < rank`，越界必须抛出 `ValueError`。
- 数值稳定性要求：实现必须采用“减去该轴最大值后再指数化”的等价语义，即 `exp(x - max(x)) / sum(exp(x - max(x)))`，避免直接对原值指数化。
- 与现有 nn 算子兼容：`softmax` 输出仍为 `Memory`，可直接作为 `add/sub/mul/truediv/floordiv/compare` 的输入。

返回与限制：

- 返回 `Memory` 语义结果。
- `out.shape == value.shape`。
- `out.dtype == value.dtype`。
- `out.space == value.space`。
- `out.format == value.format`。
- `out.stride == value.stride`。

### `fc(value, weight, bias=None)`

功能说明：

- 全连接（fully connected）运算，对输入末维与权重输入特征维执行线性变换；`bias` 为可选项。

参数说明：

- `value` (`Memory`)：输入张量，`rank >= 2`，末维表示输入特征维 `in_features`。
- `weight` (`Memory`)：权重张量，`rank == 2`，形状为 `[out_features, in_features]`。
- `bias` (`Memory|None`)：可选偏置，默认 `None`；提供时必须与输出特征维对齐（`shape == [out_features]`）。

使用示例：

```python
value = Memory(shape=["B", "T", "K"], dtype=NumericType.Float32)
weight = Memory(shape=["N", "K"], dtype=NumericType.Float32)
out = fc(value, weight)
bias = Memory(shape=["N"], dtype=NumericType.Float32)
out_with_bias = fc(value, weight, bias=bias)
```

注意事项：

- `value` 与 `weight` 必须为 `Memory`，否则抛出 `TypeError`。
- `bias` 仅允许为 `None` 或 `Memory`，其他类型必须抛出 `TypeError`。
- `value.rank < 2` 或 `weight.rank != 2` 必须抛出 `ValueError`。
- 维度约束：`value.shape[-1]` 必须与 `weight.shape[1]` 一致；不一致必须抛出 `ValueError`。
- `bias` 提供时必须满足 `bias.rank == 1` 且 `bias.shape[0] == weight.shape[0]`（与输出特征维对齐）；不满足必须抛出 `ValueError`。
- `value.space` 与 `weight.space` 必须一致；`bias` 提供时其 `space` 也必须一致，不一致必须抛出 `ValueError`。
- `dtype` 决议沿用 `add` 的固定优先级规则（低精度 -> 高精度，整浮混合取浮点）；`bias` 提供时其 `dtype` 必须与结果 `dtype` 兼容，否则抛出 `TypeError`。
- 批维处理规则：除末维外，`value` 的前缀维度按原顺序保留到输出。
- 与现有 nn 算子兼容：`fc` 输出仍为 `Memory`，可直接作为逐元素算术、比较、`matmul` 等算子的输入。

返回与限制：

- 返回 `Memory` 语义结果。
- 设 `value.shape = [d0, d1, ..., d{n-1}, in_features]`、`weight.shape = [out_features, in_features]`，则 `out.shape = [d0, d1, ..., d{n-1}, out_features]`。
- `out.dtype` 按固定优先级规则（低精度 -> 高精度，整浮混合取浮点）决议。
- `out.space == value.space`。
- `out.format == Farmat.Norm`。
- `out.stride` 使用连续行主序默认步幅。

### `matmul(lhs, rhs, memoryspace=None)`

功能说明：

- 二维矩阵乘。

参数说明：

- `lhs` (`Memory`)：左操作数，`rank == 2`。
- `rhs` (`Memory`)：右操作数，`rank == 2`。
- `memoryspace` (`MemorySpace|None`)：结果空间覆盖参数；为 `None` 时沿用输入共同 `space`，显式传入时仅覆盖结果 `space`。

使用示例：

```python
lhs = Memory(shape=["M", "K"], dtype=NumericType.Float32)
rhs = Memory(shape=["K", "N"], dtype=NumericType.Float32)
out = matmul(lhs, rhs)
tmp = matmul(lhs, rhs, memoryspace=MemorySpace.SM)
```

注意事项：

- 仅支持二维 `Memory x Memory`。
- 不支持 batch、广播或隐式转置。
- `lhs.space` 与 `rhs.space` 必须一致；即使显式传入 `memoryspace`，输入两侧的 `space` 仍必须先满足一致性。
- `dtype` 按与 `add` 相同的固定优先级决议，选择顺序更靠后的类型。
- 结果 `format` 固定回落为 `Farmat.Norm`。
- 结果 `stride` 固定为连续行主序默认步幅，即 `[rhs.shape[1], 1]`；符号维场景下继续复用 `Memory` 默认 stride 语义与序列化口径。

返回与限制：

- 返回 `Memory` 语义结果。
- `out.shape == ["M", "N"]`。
- `out.dtype` 按固定优先级决议并选择顺序更靠后的类型。
- `out.space` 在 `memoryspace is None` 时继承输入共同 `space`，否则取显式传入的 `memoryspace`。
- `out.format == Farmat.Norm`。
- `out.stride == [rhs.shape[1], 1]`。

### `conv(value, weight, bias=None, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)`

功能说明：

- 二维卷积（NCHW），返回新的 `Memory` 描述。

参数说明：

- `value` (`Memory`)：输入特征图，shape 为 `[N, C_in, H, W]`。
- `weight` (`Memory`)：卷积核权重，shape 为 `[C_out, C_in, K_h, K_w]`。
- `bias` (`Memory|None`)：可选偏置，省略时不执行偏置加法；提供时必须与 `C_out` 对齐。
- `sh`/`sw` (`int|SymbolDim`)：stride，高度/宽度方向，必须为正数。
- `dh`/`dw` (`int|SymbolDim`)：dilation，高度/宽度方向，必须为正数。
- `ph`/`pw`/`pl`/`pr` (`int|SymbolDim`)：padding，分别为上/下/左/右，必须为非负数。

使用示例：

```python
value = Memory([1, 3, 32, 32], NumericType.Float32)
weight = Memory([8, 3, 3, 3], NumericType.Float32)
out = conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

bias = Memory([8], NumericType.Float32)
out = conv(value, weight, bias=bias, sh=2, sw=2, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
```

注意事项：

- `value`/`weight` 必须为 `Memory` 且 rank=4，否则抛出 `TypeError`/`ValueError`。
- `value.shape[1]` 必须与 `weight.shape[1]` 一致，否则抛出 `ValueError`。
- `value.dtype` 与 `weight.dtype` 必须一致；`value.space` 与 `weight.space` 必须一致。
- `bias` 省略时不参与计算；提供时必须为 `Memory` 且 rank=1，`bias.shape == [C_out]`，且 `bias.dtype`/`bias.space` 与输出一致，否则抛出 `TypeError`/`ValueError`。
- 输出高宽按公式计算：
  - `H_out = floor((H + ph + pw - dh * (K_h - 1) - 1) / sh) + 1`
  - `W_out = floor((W + pl + pr - dw * (K_w - 1) - 1) / sw) + 1`
- 当 `H_out` 或 `W_out` 为确定整数且不为正时，必须抛出 `ValueError`。

返回与限制：

- 返回 `Memory` 语义结果。
- `out.shape == [N, C_out, H_out, W_out]`，`C_out` 取自 `weight.shape[0]`。
- `out.dtype == value.dtype`，`out.space == value.space`。
- `out.format == Farmat.Norm`，`out.stride` 为连续行主序默认步幅（沿用 `Memory` 默认 stride 语义与序列化口径）。

## 测试

- 测试文件：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- 执行命令：`pytest -q test/operation/test_operation_nn.py`
- 验收命令（激活函数）：`pytest -q test/operation/test_operation_nn.py -k activation`
- 验收命令（算术与 matmul）：`pytest -q test/operation/test_operation_nn.py -k "test_nn_add_memory or test_nn_other_arithmetic or test_nn_floordiv_rules or test_nn_matmul_success or test_nn_dtype_mismatch or test_nn_matmul_dtype_mismatch"`

### 测试目标

- 验证逐元素算术/比较的成功路径、链式表达式、标量参与规则与错误规则。
- 验证 `nn.add` 在同形状输入时保持原有 `Memory` 描述。
- 验证显式 `broadcast(value, target)` / `broadcast_to(value, target)` 的尾维对齐、前置维扩张、target 对齐与错误规则。
- 验证逐元素隐式 broadcast 的 singleton dim / 前置维扩张与错误规则。
- 验证 nn 算术算子（`add/sub/mul/truediv/floordiv/matmul`）遵循统一 OP-TP 类型提升规则。
- 验证 `Memory/Memory` 路径按固定优先级选择更靠后类型，`Memory/标量` 路径按 `Int32` 参与决议。
- 验证整浮 mixed dtype 参与算术时提升到浮点并取浮点侧更高优先级类型，以及 `format/stride` 不一致时回落默认布局。
- 验证比较算子与 `broadcast` 路径不适用算术类型提升规则。
- 验证 `fc(value, weight, bias=None)` 的输入/权重约束、可选 `bias` 对齐规则、批维保留与输出 shape 推导。
- 验证 `fc` 的非法输入与报错规则：参数类型、rank、特征维不匹配、`bias` 维度不对齐、`space` 不一致。
- 验证 `matmul(lhs, rhs, memoryspace=None)` 的二维输入约束、`memoryspace` 覆盖、结果 `format/stride` 口径与错误规则。
- 验证 `softmax(value, axis=-1)` 的 axis 默认值/负轴归一化、输入 dtype 约束、数值稳定性语义要求与错误路径。
- 验证比较结果使用 `NumericType.Bool` 作为 predicate 载体。
- 验证 nn 操作不依赖已移除的旧 shape 规范化入口。
- 验证 `img2col` 输出形状与参数校验规则。
- 验证 `conv` 的参数校验、输出形状公式与 bias 可选对齐规则。
- 验证激活函数的输入输出约束、参数规则与错误路径。

### 功能与用例清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| OP-001 | `add` 基础逐元素运算 | `test_nn_add_memory` |
| OP-002 | `sub`/`mul`/`truediv` 逐元素算术可调用 | `test_nn_other_arithmetic` |
| OP-002A | `sub` 支持标量反向调用，且 `dtype` 决议与 `add` 一致 | `test_nn_sub_reverse_and_dtype_mismatch` |
| OP-002B | `sub` 在 `format/stride` 不一致时回落默认布局 | `test_nn_sub_format_fallback` |
| OP-003 | shape 不一致报错 | `test_nn_shape_mismatch` |
| OP-004 | rank 不一致报错 | `test_nn_rank_mismatch` |
| OP-005 | `Memory + scalar` | `test_nn_add_scalar` |
| OP-005A | `Memory + bool scalar` 仍走标量路径并保持 `Memory` 结果描述 | `test_nn_add_bool_scalar` |
| OP-006 | 链式表达式保持形状与 dtype | `test_nn_chain_expression` |
| OP-007 | 非法标量类型报 `TypeError` | `test_nn_scalar_type_error` |
| OP-008 | `add` 的不支持 `dtype` 输入触发 `TypeError` | `test_nn_dtype_invalid_error` |
| OP-009 | 比较结果使用 `NumericType.Bool` 作为 predicate 载体 | `test_nn_compare_predicate` |
| OP-010 | 比较时 shape 顺序不同报错 | `test_nn_compare_shape_order` |
| OP-011 | 纯标量输入报 `TypeError` | `test_nn_scalar_only_error` |
| OP-012 | `ne`/`le`/`ge` 比较别名可调用，且结果 `dtype` 为 `NumericType.Bool` | `test_nn_compare_alias` |
| OP-013 | 同布局的 `Memory/Memory add` 保持原有 `Memory` 描述，且不依赖已移除的旧 shape 规范化入口 | `test_nn_operation_does_not_require_convert_from_list` |
| OP-017 | `floordiv` 复用逐元素算术规则、支持标量并在布局不一致时回落默认布局 | `test_nn_floordiv_rules` |
| OP-TP-001 | nn 算术统一类型优先级按 `Int8` 到 `Float64`，`Memory/Memory` 结果选择顺序更靠后类型 | `test_nn_dtype_mismatch`, `test_nn_matmul_dtype_mismatch` |
| OP-TP-002 | 整数与浮点 mixed dtype 的算术结果必须提升到浮点并取浮点侧更高优先级类型 | `test_nn_dtype_mismatch`, `test_nn_sub_reverse_and_dtype_mismatch`, `test_nn_floordiv_rules`, `test_nn_matmul_dtype_mismatch` |
| OP-TP-003 | `Memory/标量` 路径按 `Int32` 参与类型决议，再选择顺序更靠后类型 | `test_nn_dtype_mismatch`, `test_nn_floordiv_rules` |
| OP-TP-004 | OP-TP 规则仅适用于算术算子（`add/sub/mul/truediv/floordiv/matmul`） | `test_nn_other_arithmetic`, `test_nn_sub_reverse_and_dtype_mismatch`, `test_nn_floordiv_rules`, `test_nn_matmul_success` |
| OP-TP-005 | 比较算子与显式广播路径不适用 OP-TP：比较结果固定 `Bool`，broadcast 结果对齐 target 描述 | `test_nn_compare_predicate`, `test_nn_compare_alias`, `test_nn_broadcast_success` |
| OP-TP-006 | 不支持的 dtype 参与算术提升或非法标量输入必须抛错 | `test_nn_dtype_invalid_error`, `test_nn_scalar_type_error` |
| OP-ACT-001 | `relu`/`sigmoid`/`tanh`/`hard_sigmoid` 输出 `shape/dtype/space/stride/format` 继承输入 | `test_nn_activation_basic` |
| OP-ACT-002 | `leaky_relu` 的 `alpha` 参数规则与边界行为 | `test_nn_activation_leaky_relu_alpha` |
| OP-ACT-003 | 激活函数的非 `Memory` 输入、非浮点 `dtype` 与无效参数报错 | `test_nn_activation_invalid_input` |
| OP-BC-001 | `broadcast` / `broadcast_to` 可通过 singleton dim 扩张并返回与 `target` 完全一致的描述 | `test_nn_broadcast_success` |
| OP-BC-002 | `broadcast` / `broadcast_to` 支持前置维扩张并保持 `target` 描述 | `test_nn_broadcast_prepend_dimension` |
| OP-BC-003 | `broadcast` / `broadcast_to` 维度不兼容报错 | `test_nn_broadcast_dimension_mismatch` |
| OP-BC-004 | `broadcast` / `broadcast_to` 目标 rank 更小时报错 | `test_nn_broadcast_rank_error` |
| OP-BC-005 | `broadcast` / `broadcast_to` 非 `Memory` 输入报错 | `test_nn_broadcast_non_memory_error` |
| OP-BC-006 | `broadcast` / `broadcast_to` 非 `Memory` target 报错 | `test_nn_broadcast_target_type_error` |
| OP-IB-001 | 算术支持 singleton dim 隐式 broadcast | `test_nn_add_implicit_broadcast_singleton` |
| OP-IB-002 | 算术支持前置维隐式 broadcast | `test_nn_add_implicit_broadcast_prepend_dimension` |
| OP-IB-003 | 比较运算复用隐式 broadcast | `test_nn_compare_implicit_broadcast` |
| OP-IB-004 | 隐式 broadcast 维度不兼容报错 | `test_nn_add_implicit_broadcast_mismatch` |
| OP-014 | `add` 的 `Memory/Memory` 结果 `dtype` 按固定优先级（低精度 -> 高精度）决议 | `test_nn_dtype_mismatch` |
| OP-015 | `add` 在 `format` 不一致时回落默认布局 | `test_nn_add_format_fallback` |
| OP-016 | `add` 在 `stride` 不一致时回落默认布局，默认 stride 与序列化口径沿用 `Memory` 规范 | `test_nn_add_stride_fallback` |
| OP-016A | `add` 默认 stride 分量的序列化口径保持稳定 | `test_nn_add_stride_dim_serialization` |
| OP-FC-001 | `fc` 支持 `bias=None`，输出保留输入批维并将末维替换为 `out_features` | `test_nn_fc_without_bias` |
| OP-FC-002 | `fc` 的 `bias` 为可选参数；提供时必须与输出特征维对齐（`shape == [out_features]`） | `test_nn_fc_with_optional_bias` |
| OP-FC-003 | `fc` 的 `value/weight` 类型非法或 `bias` 非 `Memory|None` 时抛 `TypeError` | `test_nn_fc_type_error` |
| OP-FC-004 | `fc` 的 `rank` 约束（`value.rank >= 2`、`weight.rank == 2`）不满足时报 `ValueError` | `test_nn_fc_rank_error` |
| OP-FC-005 | `fc` 输入特征维与权重输入特征维不一致时报 `ValueError` | `test_nn_fc_feature_mismatch` |
| OP-FC-006 | `fc` 的 `bias` 维度不对齐（非 1D 或长度不等于 `out_features`）时报 `ValueError` | `test_nn_fc_bias_shape_error` |
| OP-FC-007 | `fc` 输入 `space` 不一致时报 `ValueError`，并保持与现有 nn 算子链式兼容 | `test_nn_fc_space_mismatch`, `test_nn_fc_chain_compatibility` |
| OP-MM-001 | `matmul(lhs, rhs, memoryspace=None)` 成功路径：结果 shape/dtype/space/format/stride 收敛到公开口径 | `test_nn_matmul_success` |
| OP-MM-002 | `matmul` 显式 `memoryspace` 仅覆盖结果 `space` | `test_nn_matmul_space_override` |
| OP-MM-003 | `matmul` contracting dim 不一致报错 | `test_nn_matmul_contracting_dim_mismatch` |
| OP-MM-004 | `matmul` 非二维输入报错 | `test_nn_matmul_rank_error` |
| OP-MM-005 | `matmul` 标量输入非法 | `test_nn_matmul_scalar_operand_error` |
| OP-MM-006 | `matmul` 的 `dtype` 按固定优先级决议并选择顺序更靠后类型 | `test_nn_matmul_dtype_mismatch` |
| OP-MM-007 | `matmul` 输入 `space` 不一致报错 | `test_nn_matmul_space_mismatch` |
| OP-SM-001 | `softmax` 默认 `axis=-1`，结果保持输入 `shape/dtype/space/format/stride` | `test_nn_softmax_default_axis` |
| OP-SM-002 | `softmax` 支持负轴并归一化到合法维度 | `test_nn_softmax_negative_axis` |
| OP-SM-003 | `softmax` 的 `axis` 非整数或为 `bool` 时报 `TypeError` | `test_nn_softmax_axis_type_error` |
| OP-SM-004 | `softmax` 的 `axis` 越界时报 `ValueError` | `test_nn_softmax_axis_out_of_range` |
| OP-SM-005 | `softmax` 非浮点 `dtype` 输入报 `TypeError` | `test_nn_softmax_dtype_error` |
| OP-SM-006 | `softmax` 限定数值稳定语义为 `exp(x - max(x)) / sum(exp(x - max(x)))` | `test_nn_softmax_numerical_stability_contract` |
| OP-IMG2COL-001 | `img2col` 输出形状与参数校验规则 | `test_nn_img2col_basic` |
| OP-CONV-001 | `conv` 基础路径与参数校验（含可选 bias 对齐） | `test_nn_conv_basic` |
