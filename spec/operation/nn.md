# nn.md

## 功能简介

用于定义 `python/operation/nn.py` 的高层运算规范，覆盖 `Memory` 的逐元素算术、比较、显式 `broadcast` 与二维 `matmul`。本层只描述可调用语义与错误规则，不引入 IR 细节。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `功能实现`：[`python/operation/nn.py`](../../python/operation/nn.py)
- `test`：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)

## 依赖

- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：定义 `Memory` 的 `shape`/`stride`/`dtype`/`space` 基础语义。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：定义 `nn dialect` 的 op/type/verifier 约束，作为下游方言承载。
- [`python/operation/nn.py`](../../python/operation/nn.py)：当前高层 API 实现文件。

## 目标

- 提供 `Memory` 的逐元素算术与比较高层语义。
- 提供显式 `broadcast` 与二维 `matmul` 的输入输出约束与错误规则。
- 保持与下游 `nn dialect` 的分层：本层只定义 API 语义，不承载 IR 细节。

## 限制与边界

- 逐元素算术/比较支持隐式广播，仅允许尾维对齐与 singleton dim 扩张。
- `matmul` 仅定义二维矩阵乘，不支持 batch、广播或隐式转置。
- 不定义归约、卷积等其他算子。
- 不引入复杂自动类型提升规则；`dtype` 兼容性需显式检查。
- 不负责 AST/IR/lowering 设计。

## 公开接口

### `add(lhs, rhs)`

功能说明：

- 逐元素加法。

参数说明：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

使用示例：

```python
A = Memory(shape=["M", "N"], dtype="float32")
B = Memory(shape=["M", "N"], dtype="float32")

C = add(A, B)
D = add(A, 3)
```

注意事项：

- `Memory` 与 `Memory` 可触发隐式 broadcast。
- 标量与 `Memory` 运算必须检查 `dtype` 兼容性。

返回与限制：

- 返回 `Memory` 语义结果。
- `shape` 为输入一致时的原 `shape`，或隐式广播的共同目标 `shape`。

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
- 当前实现以 `NumericType.Int32` 承载 predicate。

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Int32`。

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

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Int32`。

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

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Int32`。

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

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Int32`。

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

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Int32`。

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

返回与限制：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Int32`。

### `broadcast(value, shape)`

功能说明：

- 显式广播，把 `Memory` 扩张到目标 `shape`。

参数说明：

- `value` (`Memory`)：待广播输入。
- `shape` (sequence)：目标 `shape` 维度序列。

使用示例：

```python
value = Memory(shape=[1, "N"], dtype=NumericType.Float32)
out = broadcast(value, ["M", "N"])
```

注意事项：

- 广播使用尾维对齐与 singleton dim 扩张规则。
- 不改变 `dtype` 与 `space`。

返回与限制：

- 返回 `Memory` 语义结果。
- `out.shape == shape`。
- `out.dtype == value.dtype`。
- `out.space == value.space`。

### `matmul(lhs, rhs)`

功能说明：

- 二维矩阵乘。

参数说明：

- `lhs` (`Memory`)：左操作数，`rank == 2`。
- `rhs` (`Memory`)：右操作数，`rank == 2`。

使用示例：

```python
lhs = Memory(shape=["M", "K"], dtype=NumericType.Float32)
rhs = Memory(shape=["K", "N"], dtype=NumericType.Float32)
out = matmul(lhs, rhs)
```

注意事项：

- 仅支持二维 `Memory x Memory`。
- 不支持 batch、广播或隐式转置。
- `dtype` 与 `space` 需兼容。

返回与限制：

- 返回 `Memory` 语义结果。
- `out.shape == ["M", "N"]`。
- `out.dtype` 继承兼容后的输入 `dtype`。
- `out.space` 继承输入空间（要求一致）。

## 测试

- 测试文件：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- 执行命令：`pytest -q test/operation/test_operation_nn.py`

### 测试目标

- 验证逐元素算术/比较的输入合法性、隐式广播与错误规则。
- 验证显式 `broadcast` 的尾维对齐与 singleton 扩张规则。
- 验证 `matmul` 的二维输入约束与错误规则。
- 验证比较结果使用 `NumericType.Int32` 作为 predicate 载体。

### 功能与用例清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| OP-001 | `add` 基础逐元素运算 | `test_nn_add_memory` |
| OP-005 | `Memory + scalar` | `test_nn_add_scalar` |
| OP-003 | shape 不一致报错 | `test_nn_shape_mismatch` |
| OP-BC-001 | `broadcast` singleton 扩张 | `test_nn_broadcast_success` |
| OP-MM-001 | `matmul` 成功路径 | `test_nn_matmul_success` |
| OP-009 | 比较结果 predicate 载体 | `test_nn_compare_predicate` |
