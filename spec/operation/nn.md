# nn.md

用于定义 `Memory` 的逐元素算术与比较运算规范。该层独立于具体前端语法，可被普通 Python 代码、语义构造层或其他上层接口直接复用。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/operation/nn.md`](../../spec/operation/memory.md)
- `关联类型`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/operation/test_operation_nn.py`](../../test/operation/test_memory_operation.py)
- `功能实现`：[`python/operation/nn.py`](../../python/operation/memory.py)

## 设计目标

- 为 `Memory` 提供统一、稳定的逐元素运算语义。
- 明确运算输入约束、输出语义、类型合法性与错误规则。
- 保留动态 `shape/stride` 信息，使运算结果仍可表达动态张量。
- 让运算层可被上层系统直接复用，而不把运算规则散落在多个模块中。

## 非目标

- 不支持广播。
- 不在本阶段定义归约、矩阵乘、卷积等高阶算子。
- 不在本阶段引入隐式自动类型提升的复杂规则。
- 不负责 AST、IR、lowering 等上层结构设计。

## 术语

- `Memory`：带 `shape`、`stride`、`dtype`、`memory_level` 等元信息的张量描述对象。
- 张量语义结果：可继续参与后续运算、并至少暴露 `shape`、`stride`、`dtype` 的结果对象。
- 标量：与 `dtype` 体系兼容的单值输入，例如 `int`，后续可扩展到更多数值类型。

## 设计原则

- 运算层只定义“什么可以算、怎么算、何时报错”，不绑定具体前端表示。
- 至少一侧操作数必须具有 `Memory` 张量语义；本文不定义纯标量和纯标量之间的运算接口。
- `Memory` 与 `Memory` 的逐元素运算要求 `shape` 严格一致，不支持广播。
- 所有计算在执行前都必须先通过类型合法性检查。
- 运算结果必须保留输入的动态维度信息，不得在前端阶段退化为静态常量。
- 比较操作返回逐元素比较结果，其结果仍是张量语义对象，而不是单个 Python `bool`。
- 必须提供独立的 nn API 实现层 `python/operation/nn.py`，并提供对应测试 `test/operation/test_operation_nn.py`，不可仅在 `symbol_variable/memory.py` 内承载语义。

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
- `CMP.dtype == "bool"` 或等价 predicate 类型

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
- `lhs.shape` 必须与 `rhs.shape` 完全一致。
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

## 类型合法性规则

- 算术操作只接受 `Memory` 或受支持的数值标量类型作为输入。
- 比较操作只接受 `Memory` 或受支持的数值标量类型作为输入。
- 不支持的 Python 对象类型，例如 `str`、`list`、`dict`、任意无数值语义的自定义对象，必须抛 `TypeError`。
- 若 `Memory.dtype` 为空，可在实现中延后推导；但在未完成推导前，不得默认所有类型都合法。
- `Memory + scalar`、`Memory - scalar`、`Memory * scalar`、`Memory / scalar` 都必须检查标量与 `Memory.dtype` 的兼容性。
- `Memory + Memory`、`Memory == Memory` 等双张量运算都必须检查两侧 `dtype` 是否可兼容。
- 链式表达式只要某一步类型不合法，整个表达式立即失败。

## Shape 规则

- 不支持广播。
- 仅当两个张量语义对象的 `shape` 完全一致时，才允许二元逐元素运算。
- “完全一致”指逐维表达式语义一致，例如 `[A, B]` 与 `[A, B]` 一致，`[A, B]` 与 `[B, A]` 不一致，`[A, B]` 与 `[A, C]` 不一致。
- 对链式表达式按从左到右的中间结果逐步判定；只要每一步都满足 shape 规则，则最终结果合法。

错误示例：

- `tensor([A, B]) + tensor([A, C])`：错误，第二维不一致。
- `tensor([A, B]) + tensor([A])`：错误，rank 不一致。
- `tensor([A, B]) + tensor([B, A])`：错误，shape 顺序不同。
- `tensor([A, B]) + 3 + tensor([A, C])`：错误，最后一步 shape 不一致。

## Dtype 规则

- 算术操作输出 `dtype` 默认继承输入 `dtype`，或由受控的显式类型规则决定。
- 比较操作输出 `dtype` 为 `bool` 或等价 predicate 类型。
- 若两个输入 `dtype` 不兼容，应抛出 `TypeError`。
- 若 `Memory + scalar` 中 scalar 类型与 `Memory.dtype` 不兼容，应抛出 `TypeError`。
- 链式表达式中的中间结果也必须满足后续运算的 `dtype` 合法性。

## 输出语义

### 算术操作输出

- 输出为张量语义结果对象，可继续参与后续算术或比较运算。
- 输出 `shape` 继承输入张量的 `shape`。
- 输出 `stride` 继承输入张量的 `stride`，或由实现按兼容规则确定，但不得丢失 rank 与动态维度信息。
- 若输入 `shape` 中包含符号维度，如 `[A, B]`，输出也保持 `[A, B]`。

示例：

- `tensor([A, B]) + tensor([A, B]) -> tensor([A, B])`
- `tensor([A, B]) + 1 -> tensor([A, B])`
- `tensor([A, B]) + 3 + tensor([A, B]) -> tensor([A, B])`

### 比较操作输出

- 输出为逐元素比较后的张量语义结果，不是单个标量 `bool`。
- 输出 `shape` 与输入 `shape` 相同。
- 输出 `dtype` 建议为 `bool` 或后端可接受的 predicate 类型。

示例：

- `eq(tensor([A, B]), tensor([A, B])) -> tensor([A, B], dtype=bool)`

## 独立使用示例

```python
from operation.memory import add, eq
from symbol_variable.memory import Memory

X = Memory(shape=["A", "B"], dtype="float32")
Y = Memory(shape=["A", "B"], dtype="float32")

Z = add(add(X, 3), Y)
CMP = eq(X, Y)
```

语义约束：

- `Z.shape == ["A", "B"]`
- `CMP.shape == ["A", "B"]`
- `CMP.dtype == "bool"` 或等价 predicate 类型
- 若 `Y.shape != ["A", "B"]`，则运算失败
- 若 `X.dtype` 与 `Y.dtype` 不兼容，或标量类型不兼容，则运算失败

## 与上层系统的关系

- 上层前端可以直接复用本规范中的算术与比较规则。
- 若上层需要构造 AST 或 IR，应捕获本层语义，而不是重新定义另一套 shape/dtype 规则。
- 上层系统不得改变本层关于“严格 shape 一致”和“先检查类型合法性”的基本约束。

## 返回与错误

### 成功返回

- 算术操作返回张量语义结果，`shape` 与输入一致。
- 比较操作返回张量语义结果，`shape` 与输入一致，`dtype` 为 `bool` / predicate。

### 失败返回

- 输入类型不支持时抛 `TypeError`。
- 两个张量语义对象的 `shape` 不一致时抛 `ValueError`。
- `dtype` 不兼容时抛 `TypeError`。
- 链式表达式任一步的输入类型不合法时抛 `TypeError`。

## 测试

- 测试文件：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- 执行命令：`pytest -q test/operation/test_operation_nn.py`

### 测试目标

- 验证运算层可独立于任意上层接口被直接调用。
- 验证 `Memory + Memory` 的 shape 严格匹配规则。
- 验证 `Memory + scalar` 保持原 `shape`。
- 验证链式表达式如 `A + 3 + B` 在每一步都执行 shape 与类型合法性检查。
- 验证比较操作输出保持相同 `shape`，且结果类型为布尔语义。
- 验证 shape 不一致与类型不兼容时稳定报错。

### 测试标准

- 所有 shape 校验路径可稳定复现。
- 所有类型合法性错误路径可稳定复现。
- 动态 shape 在运算结果中不丢失。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| OP-001 | 独立调用 | 普通 Python 中使用 | `X.shape=[A,B]`, `Y.shape=[A,B]` | `add(X, Y)` | 返回 shape=`[A,B]` 的动态结果 |
| OP-002 | 算术 | 同 shape 相加 | `lhs.shape=[A,B]`, `rhs.shape=[A,B]` | `lhs + rhs` 或 `add(lhs, rhs)` | 返回 shape=`[A,B]` 的动态结果 |
| OP-003 | 算术 | shape 不一致 | `lhs.shape=[A,B]`, `rhs.shape=[A,C]` | `add(lhs, rhs)` | 抛 `ValueError` |
| OP-004 | 算术 | rank 不一致 | `lhs.shape=[A,B]`, `rhs.shape=[A]` | `add(lhs, rhs)` | 抛 `ValueError` |
| OP-005 | 算术 | Memory 与标量 | `lhs.shape=[A,B]`, `lhs.dtype=float32` | `add(lhs, 1)` | 返回 shape=`[A,B]` 的动态结果 |
| OP-006 | 算术 | 链式表达式 | `lhs.shape=[A,B]`, `rhs.shape=[A,B]` | `add(add(lhs, 3), rhs)` | 返回 shape=`[A,B]` 的动态结果 |
| OP-007 | 类型 | 标量类型不合法 | `lhs.dtype=float32` | `add(lhs, "3")` | 抛 `TypeError` |
| OP-008 | 类型 | Memory dtype 不兼容 | `lhs.dtype=float32`, `rhs.dtype=int32` | `add(lhs, rhs)` | 抛 `TypeError` |
| OP-009 | 比较 | 同 shape 比较 | `lhs.shape=[A,B]`, `rhs.shape=[A,B]` | `eq(lhs, rhs)` | 返回 shape=`[A,B]` 且 dtype=`bool` 的结果 |
| OP-010 | 比较 | shape 顺序不同 | `lhs.shape=[A,B]`, `rhs.shape=[B,A]` | `eq(lhs, rhs)` | 抛 `ValueError` |
