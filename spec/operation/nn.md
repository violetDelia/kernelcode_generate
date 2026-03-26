# nn.md

## 功能简介

用于定义 `Memory` 高层运算规范，覆盖逐元素算术、比较、显式 `broadcast` / `broadcast_to` 与二维 `matmul`。本层只描述可调用语义、结果元信息约束与错误规则。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `功能实现`：[`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
- `test`：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)

## 依赖

- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：定义 `Memory` 的 `shape`/`stride`/`dtype`/`space` 基础语义。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：定义 `NumericType` 与 `Farmat` 的公开枚举语义，比较结果中的 `NumericType.Bool` 以该文档为准。

## 目标

- 提供 `Memory` 的逐元素算术与比较高层语义。
- 提供显式 `broadcast` / `broadcast_to` 与二维 `matmul` 的输入输出约束与错误规则。
- 保持与下游 `nn dialect` 的分层：本层作为用户直接使用的接口，不受限于IR的表达。

## 限制与边界

- 逐元素算术/比较支持隐式广播，仅允许尾维对齐与 singleton dim 扩张。
- `transpose` 仅支持 `Memory` 输入与显式轴置换，不支持标量或隐式转置。
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
- `Memory/Memory` 路径的 `dtype` 按固定优先级决议：`Int8`、`Uint8`、`Int16`、`Uint16`、`Int32`、`Uint32`、`Int64`、`Uint64`、`Float16`、`BFloat16`、`Float32`、`Float64`；结果选择顺序更靠前的类型。
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
- `dtype` 按与 `add` 相同的固定优先级决议。
- 结果 `format` 固定回落为 `Farmat.Norm`。
- 结果 `stride` 固定为连续行主序默认步幅，即 `[rhs.shape[1], 1]`；符号维场景下继续复用 `Memory` 默认 stride 语义与序列化口径。

返回与限制：

- 返回 `Memory` 语义结果。
- `out.shape == ["M", "N"]`。
- `out.dtype` 按固定优先级决议。
- `out.space` 在 `memoryspace is None` 时继承输入共同 `space`，否则取显式传入的 `memoryspace`。
- `out.format == Farmat.Norm`。
- `out.stride == [rhs.shape[1], 1]`。

## 测试

- 测试文件：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- 执行命令：`pytest -q test/operation/test_operation_nn.py`

### 测试目标

- 验证逐元素算术/比较的成功路径、链式表达式、标量参与规则与错误规则。
- 验证 `nn.add` 在同形状输入时保持原有 `Memory` 描述。
- 验证显式 `broadcast(value, target)` / `broadcast_to(value, target)` 的尾维对齐、前置维扩张、target 对齐与错误规则。
- 验证逐元素隐式 broadcast 的 singleton dim / 前置维扩张与错误规则。
- 验证 `nn.add` / `nn.floordiv` 的 `dtype` 固定优先级决议，以及 `format/stride` 不一致时回落默认布局。
- 验证 `matmul(lhs, rhs, memoryspace=None)` 的二维输入约束、`memoryspace` 覆盖、结果 `format/stride` 口径与错误规则。
- 验证比较结果使用 `NumericType.Bool` 作为 predicate 载体。
- 验证 nn 操作不依赖已移除的旧 shape 规范化入口。

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
| OP-014 | `add` 的 `Memory/Memory` 结果 `dtype` 按固定优先级决议 | `test_nn_dtype_mismatch` |
| OP-015 | `add` 在 `format` 不一致时回落默认布局 | `test_nn_add_format_fallback` |
| OP-016 | `add` 在 `stride` 不一致时回落默认布局，默认 stride 与序列化口径沿用 `Memory` 规范 | `test_nn_add_stride_fallback` |
| OP-016A | `add` 默认 stride 分量的序列化口径保持稳定 | `test_nn_add_stride_dim_serialization` |
| OP-MM-001 | `matmul(lhs, rhs, memoryspace=None)` 成功路径：结果 shape/dtype/space/format/stride 收敛到公开口径 | `test_nn_matmul_success` |
| OP-MM-002 | `matmul` 显式 `memoryspace` 仅覆盖结果 `space` | `test_nn_matmul_space_override` |
| OP-MM-003 | `matmul` contracting dim 不一致报错 | `test_nn_matmul_contracting_dim_mismatch` |
| OP-MM-004 | `matmul` 非二维输入报错 | `test_nn_matmul_rank_error` |
| OP-MM-005 | `matmul` 标量输入非法 | `test_nn_matmul_scalar_operand_error` |
| OP-MM-006 | `matmul` 的 `dtype` 按固定优先级决议 | `test_nn_matmul_dtype_mismatch` |
| OP-MM-007 | `matmul` 输入 `space` 不一致报错 | `test_nn_matmul_space_mismatch` |
