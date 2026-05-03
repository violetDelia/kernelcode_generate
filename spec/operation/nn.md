# nn.md

## 功能简介

用于定义 `Memory` 高层运算规范，覆盖逐元素算术、比较、激活函数（含 `exp`）、归约（`reduce_sum` / `reduce_min` / `reduce_max`）、显式 `broadcast` / `broadcast_to`、`softmax`、全连接 `fc`、二维 `matmul` 与二维 `conv`。本层只描述可调用语义、结果元信息约束与错误规则。

## API 列表

- `add(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `sub(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `mul(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `truediv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `floordiv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`
- `eq(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `ne(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `lt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `le(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `gt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `ge(lhs: CompareOperand, rhs: CompareOperand) -> Memory`
- `relu(value: Memory) -> Memory`
- `leaky_relu(value: Memory, alpha: int | float = 0.01) -> Memory`
- `sigmoid(value: Memory) -> Memory`
- `tanh(value: Memory) -> Memory`
- `hard_sigmoid(value: Memory, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory`
- `exp(value: Memory) -> Memory`
- `reduce_sum(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`
- `reduce_min(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`
- `reduce_max(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`
- `broadcast(value: Memory, target: Memory) -> Memory`
- `broadcast_to(source: Memory, target_shape: Sequence[int | str | SymbolDim] | SymbolShape, space: MemorySpace) -> Memory`
- `transpose(value: Memory, perm: Sequence[int]) -> Memory`
- `softmax(value: Memory, axis: int = -1) -> Memory`
- `fc(value: Memory, weight: Memory, bias: Memory | None = None) -> Memory`
- `matmul(lhs: Memory, rhs: Memory, memoryspace: MemorySpace | None = None) -> Memory`
- `conv(value: Memory, weight: Memory, bias: Memory | None = None, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`
- `img2col1d(value: Memory, kw: int | SymbolDim, sw: int | SymbolDim = 1, dw: int | SymbolDim = 1, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`
- `img2col2d(value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `功能实现`：
  - [`kernel_gen/operation/nn/__init__.py`](../../kernel_gen/operation/nn/__init__.py)
  - [`kernel_gen/operation/nn/common.py`](../../kernel_gen/operation/nn/common.py)
  - [`kernel_gen/operation/nn/broadcast.py`](../../kernel_gen/operation/nn/broadcast.py)
  - [`kernel_gen/operation/nn/elementwise_binary.py`](../../kernel_gen/operation/nn/elementwise_binary.py)
  - [`kernel_gen/operation/nn/elementwise_compare.py`](../../kernel_gen/operation/nn/elementwise_compare.py)
  - [`kernel_gen/operation/nn/activation.py`](../../kernel_gen/operation/nn/activation.py)
  - [`kernel_gen/operation/nn/exp.py`](../../kernel_gen/operation/nn/exp.py)
  - [`kernel_gen/operation/nn/reduction.py`](../../kernel_gen/operation/nn/reduction.py)
  - [`kernel_gen/operation/nn/fc.py`](../../kernel_gen/operation/nn/fc.py)
  - [`kernel_gen/operation/nn/matmul.py`](../../kernel_gen/operation/nn/matmul.py)
  - [`kernel_gen/operation/nn/conv.py`](../../kernel_gen/operation/nn/conv.py)
  - [`kernel_gen/operation/nn/img2col.py`](../../kernel_gen/operation/nn/img2col.py)
  - [`kernel_gen/operation/nn/softmax.py`](../../kernel_gen/operation/nn/softmax.py)
  - [`kernel_gen/operation/nn/transpose.py`](../../kernel_gen/operation/nn/transpose.py)
  - [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py)
- `test`：[`test/operation/nn/test_package.py`](../../test/operation/nn/test_package.py)

## 依赖

- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：定义 `Memory` 的 `shape`/`stride`/`dtype`/`space` 基础语义。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：定义 `NumericType` 与 `Farmat` 的公开枚举语义，比较结果中的 `NumericType.Bool` 以该文档为准。
- [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py)：定义 `kernel_gen.operation` 包级稳定导出集合，供本文件锁定顶层导出边界复用。

## 目标

- 提供 `Memory` 的逐元素算术与比较高层语义。
- 提供常用激活函数的输入输出约束与错误规则。
- 提供显式 `broadcast` / `broadcast_to`、`softmax`、`exp`、`reduce_sum` / `reduce_min` / `reduce_max`、全连接 `fc`、二维 `matmul` 与二维 `conv` 的输入输出约束与错误规则。
- 提供 `img2col1d` / `img2col2d` 的高层语义锚点，并与 `nn dialect` 的结构化合同建立引用关系。
- 保持与下游 `nn dialect` 的分层：本层作为用户直接使用的接口，不受限于IR的表达。

## 术语

### family 划分与导出说明

- 本文件的阅读主轴固定为：`逐元素 -> broadcast -> structured -> reduction`；公开合同按 family 理解，不按当前单文件实现的自然书写顺序理解。
- `kernel_gen.operation.nn` 负责承载完整 `nn` 高层语义；`kernel_gen.operation` 只暴露一组稳定、克制的顶层 helper，不等价于 `nn` 子模块的全集。

| family | `kernel_gen.operation.nn` 稳定入口 | `kernel_gen.operation` 顶层稳定导出 | 说明 |
| --- | --- | --- | --- |
| `逐元素` | `add / sub / mul / truediv / floordiv / eq / ne / lt / le / gt / ge / relu / leaky_relu / sigmoid / tanh / hard_sigmoid / exp` | `add / sub / mul / truediv / eq / ne / lt / le / gt / ge` | 算术与比较允许上提到顶层；激活与 `exp` 保持子模块入口 |
| `broadcast` | `broadcast / broadcast_to / transpose` | `无` | 继续作为 `kernel_gen.operation.nn` 子模块 helper，不进入顶层 |
| `structured` | `softmax / fc / matmul / conv / img2col1d / img2col2d` | `matmul` | `matmul` 是当前唯一上提到顶层的 structured helper |
| `reduction` | `reduce_sum / reduce_min / reduce_max` | `无` | 归约族继续保持子模块入口 |

### nn 类型提升规则（算术算子统一口径）

- 统一优先级（低精度 -> 高精度）为：`Int8`、`Uint8`、`Int16`、`Uint16`、`Int32`、`Uint32`、`Int64`、`Uint64`、`Float16`、`BFloat16`、`Float32`、`Float64`。
- `Memory/Memory` 路径按上述优先级选择顺序更靠后的类型（高优先级）。
- `Memory/标量` 路径中，标量按 `NumericType.Int32` 参与同一优先级决议，再选择顺序更靠后的类型。
- 适用范围：`add`、`sub`、`mul`、`truediv`、`floordiv`、`matmul`。
- 整数与浮点混合时，结果必须提升到浮点，并取浮点侧更高优先级类型。
- 反例与边界：
  - 比较算子（`eq/ne/lt/le/gt/ge`）不使用该提升规则，结果 `dtype` 固定为 `NumericType.Bool`。
  - `broadcast` / `broadcast_to` / `transpose` 不做算术类型提升，结果 `dtype` 由接口约束决定。
  - 纯标量路径复用 Python/SymbolDim 算术语义，不纳入 `Memory` 类型提升决议。
  - 不支持的 `dtype`（不在优先级列表或 `NumericType.Bool` 参与算术提升）必须抛出 `KernelCodeError`。

## API详细说明

### `add(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- api：`add(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- 功能说明：

- 逐元素加法。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
from kernel_gen.operation.nn import add
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType

A = Memory(["M", "N"], NumericType.Int32)
B = Memory([1, "N"], NumericType.Int32)
C = add(A, B)

lhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.CLast)
rhs = Memory(["M", "N"], NumericType.Int32, stride=["N", 1], format=Farmat.Norm)
D = add(lhs, rhs)
E = add(1, SymbolDim("N"))

assert C.get_shape() == ["M", "N"]
assert D.get_format() is Farmat.Norm
assert D.get_stride()[1] == 1
assert E.get_value() == "N + 1"
```

- 注意事项：

- `Memory` 与 `Memory` 可触发隐式 broadcast；广播规则为尾维对齐，较低 rank 一侧按前置维补 `1` 后参与比较。
- 对齐后的任一维若既不相等，也不包含 `1`，必须抛出 `KernelCodeError`。
- `Memory/Memory` 路径的 `dtype` 按固定优先级决议：`Int8`、`Uint8`、`Int16`、`Uint16`、`Int32`、`Uint32`、`Int64`、`Uint64`、`Float16`、`BFloat16`、`Float32`、`Float64`；结果选择顺序更靠后的类型。
- `Memory/标量` 路径标量视作 `NumericType.Int32`，结果 `dtype` 按相同优先级选择顺序更靠后的类型。
- 当两侧 `shape`、`dtype`、`format`、`stride` 一致时，结果保持原有 `Memory` 描述。
- 当 `format` 或 `stride` 任一不一致时，结果必须回落到默认布局：`format=Farmat.Norm`，`stride` 使用连续行主序默认步幅。
- 默认步幅与其字符串化口径沿用 [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：公开接口继续通过 `Memory.get_stride()` 返回步幅分量，`str` / `repr` 继续使用 `Shape(...)` 序列化表示。
- 标量与 `Memory` 运算必须检查 `dtype` 兼容性。

- 返回值：

- 返回 `Memory` 语义结果。
- `shape` 为输入一致时的原 `shape`，或隐式广播的共同目标 `shape`。
- `Memory/Memory` 路径返回的 `dtype` 必须满足上述固定优先级决议。
- 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果，不再参与 `Memory` 广播与 `dtype` 提升。
- 纯标量路径仍只接受合法标量类型；非法标量类型必须抛出 `KernelCodeError`。

### `sub(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- api：`sub(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- 功能说明：

- 逐元素减法。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
C = sub(A, B)
D = sub(A, 1)
```

- 注意事项：

- 规则同 `add`。

- 返回值：

- 返回 `Memory` 语义结果。
- 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。

### `mul(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- api：`mul(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- 功能说明：

- 逐元素乘法。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
C = mul(A, B)
D = mul(A, 2)
```

- 注意事项：

- 规则同 `add`。

- 返回值：

- 返回 `Memory` 语义结果。
- 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。

### `truediv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- api：`truediv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- 功能说明：

- 逐元素除法。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
C = truediv(A, B)
D = truediv(A, 2)
```

- 注意事项：

- 规则同 `add`。

- 返回值：

- 返回 `Memory` 语义结果。
- 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。

### `floordiv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- api：`floordiv(lhs: BinaryOperand, rhs: BinaryOperand) -> ArithmeticResult`

- 功能说明：

- 逐元素整除。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
C = floordiv(A, B)
D = floordiv(A, 2)
```

- 注意事项：

- 复用 `add` 的隐式 broadcast、固定 `dtype` 优先级与标量参与规则。
- 当 `format` 或 `stride` 任一不一致时，结果必须回落到默认布局：`format=Farmat.Norm`，`stride` 使用连续行主序默认步幅。
- 当两侧都为纯标量时，复用 Python/SymbolDim 的整除语义。

- 返回值：

- 返回 `Memory` 语义结果。
- 当两侧都为纯标量时，返回 Python 标量或 `SymbolDim` 算术结果。

### `eq(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- api：`eq(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- 功能说明：

- 逐元素相等比较。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
CMP = eq(A, B)
```

- 注意事项：

- 比较结果语义为 predicate。
- 比较结果 `dtype` 固定为 `NumericType.Bool`。
- 复用 `add` 的隐式 broadcast 规则；与标量比较时，标量按目标 `shape` 逐元素广播。
- lowering 约束（机械写死）：若本层语义触发了 broadcast，则 `dsl/mlir_gen` 必须在进入方言前显式生成 `broadcast/broadcast_to`（memory+memory）或在 pass 中插入 `dma.broadcast`（memory+symbol/const）；`kernel.compare family` 不允许隐式 broadcast，也不允许直接接收非 memory operand。

- 返回值：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `ne(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- api：`ne(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- 功能说明：

- 逐元素不等比较。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
CMP = ne(A, B)
```

- 注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。
- 规则同 `eq`（含隐式 broadcast 的语义与 lowering 显式化约束）。
- 规则同 `eq`（含隐式 broadcast 的语义与 lowering 显式化约束）。

- 返回值：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `lt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- api：`lt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- 功能说明：

- 逐元素小于比较。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
CMP = lt(A, 0)
```

- 注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。
- 规则同 `eq`（含隐式 broadcast 的语义与 lowering 显式化约束）。
- 规则同 `eq`（含隐式 broadcast 的语义与 lowering 显式化约束）。

- 返回值：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `le(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- api：`le(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- 功能说明：

- 逐元素小于等于比较。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
CMP = le(A, 0)
```

- 注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。
- 规则同 `eq`（含隐式 broadcast 的语义与 lowering 显式化约束）。

- 返回值：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `gt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- api：`gt(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- 功能说明：

- 逐元素大于比较。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
CMP = gt(A, B)
```

- 注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。

- 返回值：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `ge(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- api：`ge(lhs: CompareOperand, rhs: CompareOperand) -> Memory`

- 功能说明：

- 逐元素大于等于比较。

- 参数：

- `lhs` (`Memory|numeric`)：左操作数。
- `rhs` (`Memory|numeric`)：右操作数。

- 使用示例：

```python
CMP = ge(A, B)
```

- 注意事项：

- 结果语义为 predicate。
- 结果 `dtype` 固定为 `NumericType.Bool`。

- 返回值：

- 返回 `Memory` 语义结果，`dtype` 为 `NumericType.Bool`。

### `relu(value: Memory) -> Memory`

- api：`relu(value: Memory) -> Memory`

- 功能说明：

- 逐元素 ReLU 激活。

- 参数：

- `value` (`Memory`)：待激活输入。

- 使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = relu(value)
```

- 注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `KernelCodeError`。
- 数值语义：`relu(x) = max(x, 0)`，`x == 0` 时返回 `0`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

- 返回值：

- 返回 `Memory` 语义结果。

### `leaky_relu(value: Memory, alpha: int | float = 0.01) -> Memory`

- api：`leaky_relu(value: Memory, alpha: int | float = 0.01) -> Memory`

- 功能说明：

- 逐元素 Leaky ReLU 激活。

- 参数：

- `value` (`Memory`)：待激活输入。
- `alpha` (`int|float`)：负半轴斜率，默认 `0.01`。

- 使用示例：

```python
value = Memory(["M", "N"], NumericType.Float16)
out = leaky_relu(value, alpha=0.2)
```

- 注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `KernelCodeError`。
- `alpha` 仅接受 `int|float`，不接受 `bool` 或 `SymbolDim`；非数值或 `NaN/Inf` 触发 `KernelCodeError`。
- 数值语义：`x >= 0` 时返回 `x`，`x < 0` 时返回 `alpha * x`；`x == 0` 时返回 `0`。当 `alpha == 0` 时退化为 `relu`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

- 返回值：

- 返回 `Memory` 语义结果。

### `sigmoid(value: Memory) -> Memory`

- api：`sigmoid(value: Memory) -> Memory`

- 功能说明：

- 逐元素 Sigmoid 激活。

- 参数：

- `value` (`Memory`)：待激活输入。

- 使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = sigmoid(value)
```

- 注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `KernelCodeError`。
- 数值语义：`sigmoid(x) = 1 / (1 + exp(-x))`，大幅正/负输入分别趋近 `1/0`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

- 返回值：

- 返回 `Memory` 语义结果。

### `tanh(value: Memory) -> Memory`

- api：`tanh(value: Memory) -> Memory`

- 功能说明：

- 逐元素 Tanh 激活。

- 参数：

- `value` (`Memory`)：待激活输入。

- 使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = tanh(value)
```

- 注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `KernelCodeError`。
- 数值语义：`tanh(x) = (exp(x) - exp(-x)) / (exp(x) + exp(-x))`，大幅正/负输入分别趋近 `1/-1`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

- 返回值：

- 返回 `Memory` 语义结果。

### `hard_sigmoid(value: Memory, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory`

- api：`hard_sigmoid(value: Memory, alpha: int | float = 0.2, beta: int | float = 0.5) -> Memory`

- 功能说明：

- 逐元素 Hard Sigmoid 激活。

- 参数：

- `value` (`Memory`)：待激活输入。
- `alpha` (`int|float`)：线性项系数，默认 `0.2`。
- `beta` (`int|float`)：线性项偏置，默认 `0.5`。

- 使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = hard_sigmoid(value, alpha=0.2, beta=0.5)
```

- 注意事项：

- 仅支持 `Memory` 输入，`value.dtype` 必须为浮点类型；否则抛出 `KernelCodeError`。
- `alpha`/`beta` 仅接受 `int|float`，不接受 `bool` 或 `SymbolDim`；非数值或 `NaN/Inf` 触发 `KernelCodeError`。
- 数值语义：`hard_sigmoid(x) = clamp(alpha * x + beta, 0, 1)`，边界处输出被截断到 `[0, 1]`。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

- 返回值：

- 返回 `Memory` 语义结果。

### `exp(value: Memory) -> Memory`

- api：`exp(value: Memory) -> Memory`

- 功能说明：

- 逐元素指数函数，计算 `e^x`。

- 参数：

- `value` (`Memory`)：待计算输入。

- 使用示例：

```python
value = Memory(["M", "N"], NumericType.Float32)
out = exp(value)
```

- 注意事项：

- `value` 必须为 `Memory`，否则抛出 `KernelCodeError`。
- `value.dtype` 必须为浮点类型：`Float16`、`BFloat16`、`Float32`、`Float64`；其他类型必须抛出 `KernelCodeError`。
- 数值语义：`exp(x)` 与自然指数函数一致；输入很大时可能产生溢出，是否截断或特殊值处理由后端实现负责，本层仅约束接口与返回元信息。
- 输出 `shape`/`dtype`/`space`/`format`/`stride` 均继承 `value`。

- 返回值：

- 返回 `Memory` 语义结果。

### `reduce_sum(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`

- api：`reduce_sum(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`

- 功能说明：

- 对输入按指定轴执行求和归约。

- 参数：

- `value` (`Memory`)：待归约输入。
- `axis` (`None|int|Sequence[int]`)：归约轴；`None` 表示归约全部轴。
- `keepdim` (`bool`)：是否保留被归约轴，默认 `False`。

- 使用示例：

```python
value = Memory([2, 3, 4], NumericType.Float32)
all_sum = reduce_sum(value)
dim1_sum = reduce_sum(value, axis=1, keepdim=True)
```

- 注意事项：

- `value` 必须为 `Memory`，否则抛出 `KernelCodeError`。
- `axis` 仅允许 `None`、`int` 或 `Sequence[int]`，且不允许 `bool`；其他类型必须抛出 `KernelCodeError`。
- 当 `axis` 为序列时，元素必须全为整数且不允许重复；空序列必须抛出 `KernelCodeError`。
- 允许负轴索引；归一化后轴索引必须满足 `0 <= axis < rank`，越界必须抛出 `KernelCodeError`。
- `keepdim` 必须为 `bool`，否则抛出 `KernelCodeError`。
- 输出 `dtype` 与 `value.dtype` 保持一致；`space` 继承 `value.space`。
- 当归约后得到空 `shape`（全部轴归约且 `keepdim=False`）时，输出使用 rank-1 单元素形状 `[1]` 表示标量结果。
- 输出 `format` 固定为 `Farmat.Norm`，`stride` 使用连续行主序默认步幅。

- 返回值：

- 返回 `Memory` 语义结果。
- `keepdim=True` 时，被归约轴对应维度为 `1`；`keepdim=False` 时移除被归约轴。

### `reduce_min(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`

- api：`reduce_min(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`

- 功能说明：

- 对输入按指定轴执行最小值归约。

- 参数：

- `value` (`Memory`)：待归约输入。
- `axis` (`None|int|Sequence[int]`)：归约轴；`None` 表示归约全部轴。
- `keepdim` (`bool`)：是否保留被归约轴，默认 `False`。

- 使用示例：

```python
value = Memory([2, 3, 4], NumericType.Float32)
all_min = reduce_min(value)
dim2_min = reduce_min(value, axis=[2], keepdim=False)
```

- 注意事项：

- `value`、`axis`、`keepdim` 的类型与边界规则与 `reduce_sum` 一致。
- 额外边界：若被归约轴在静态形状上可判定为 `0`（空归约域），必须抛出 `KernelCodeError`。
- 输出 `dtype` 与 `value.dtype` 保持一致；`space` 继承 `value.space`。
- 当归约后得到空 `shape`（全部轴归约且 `keepdim=False`）时，输出使用 rank-1 单元素形状 `[1]` 表示标量结果。
- 输出 `format` 固定为 `Farmat.Norm`，`stride` 使用连续行主序默认步幅。

- 返回值：

- 返回 `Memory` 语义结果。
- `keepdim=True` 时，被归约轴对应维度为 `1`；`keepdim=False` 时移除被归约轴。

### `reduce_max(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`

- api：`reduce_max(value: Memory, axis: int | Sequence[int] | None = None, keepdim: bool = False) -> Memory`

- 功能说明：

- 对输入按指定轴执行最大值归约。

- 参数：

- `value` (`Memory`)：待归约输入。
- `axis` (`None|int|Sequence[int]`)：归约轴；`None` 表示归约全部轴。
- `keepdim` (`bool`)：是否保留被归约轴，默认 `False`。

- 使用示例：

```python
value = Memory([2, 3, 4], NumericType.Float32)
all_max = reduce_max(value)
dim0_max = reduce_max(value, axis=0, keepdim=True)
```

- 注意事项：

- `value`、`axis`、`keepdim` 的类型与边界规则与 `reduce_sum` 一致。
- 额外边界：若被归约轴在静态形状上可判定为 `0`（空归约域），必须抛出 `KernelCodeError`。
- 输出 `dtype` 与 `value.dtype` 保持一致；`space` 继承 `value.space`。
- 当归约后得到空 `shape`（全部轴归约且 `keepdim=False`）时，输出使用 rank-1 单元素形状 `[1]` 表示标量结果。
- 输出 `format` 固定为 `Farmat.Norm`，`stride` 使用连续行主序默认步幅。

- 返回值：

- 返回 `Memory` 语义结果。
- `keepdim=True` 时，被归约轴对应维度为 `1`；`keepdim=False` 时移除被归约轴。

### `broadcast(value: Memory, target: Memory) -> Memory`

- api：`broadcast(value: Memory, target: Memory) -> Memory`

- 功能说明：

- 显式广播，把 `value` 扩张到目标 `target`。

- 参数：

- `value` (`Memory`)：待广播输入。
- `target` (`Memory`)：目标输出描述，提供结果的 `shape`、`dtype`、`space`、`stride` 与 `format`。

- 使用示例：

```python
value = Memory(shape=[1, "N"], dtype=NumericType.Float32)
target = Memory(shape=["M", "N"], dtype=NumericType.Float32, stride=["N", 1], format=Farmat.Norm)
out = broadcast(value, target)
```

- 注意事项：

- 广播使用尾维对齐与 singleton dim 扩张规则。
- `value` 与 `target` 都必须为 `Memory`；任一类型不满足时必须抛出 `KernelCodeError`。
- `target.rank` 小于 `value.rank` 或存在非 singleton 维度不兼容时必须抛出 `KernelCodeError`。
- 成功路径下，结果必须完整对齐 `target` 描述，而不是仅继承 `value` 的 `dtype` 或 `space`。

- 返回值：

- 返回 `Memory` 语义结果。
- `out.shape == target.shape`。
- `out.dtype == target.dtype`。
- `out.space == target.space`。
- `out.format == target.format`。
- `out.stride == target.stride`。

### `broadcast_to(source: Memory, target_shape: Sequence[int | str | SymbolDim] | SymbolShape, space: MemorySpace) -> Memory`

- api：`broadcast_to(source: Memory, target_shape: Sequence[int | str | SymbolDim] | SymbolShape, space: MemorySpace) -> Memory`

- 功能说明：

- 将 `source` 显式广播到目标 `target_shape` 并返回指定 `space` 的 `Memory` 结果。
- `target_shape` 必须是维度列表，不接受 `Memory` 作为目标描述。

- 参数：

- `source` (`Memory`)：待广播输入。
- `target_shape` (`Sequence[int|SymbolDim|str]`)：目标形状维度列表。
- `space` (`MemorySpace`)：目标内存空间。

- 使用示例：

```python
source = Memory([1, SymbolDim("N")], NumericType.Float32, space=MemorySpace.GM)
out = broadcast_to(source, [SymbolDim("M"), "N"], MemorySpace.LM)
# 目标合同：out.shape == [M, N]，out.dtype == f32，out.space == LM
```

- 注意事项：

- `source` 必须为 `Memory`；`target_shape` 必须为维度列表且每一维为 `int|SymbolDim|str`；`space` 必须为 `MemorySpace`。
- `str` 维度表示符号维名称/占位，由上游符号环境解析；operation 层不要求推导出具体数值。
- `target_shape` 为维度列表而非 `Memory`；`broadcast_to(value, target)` 不再作为公开合同。
- 广播规则：尾维对齐；`target_shape.rank < source.rank` 或任一对齐维不满足 `source_dim == 1` 或 `source_dim == target_dim` 时必须抛出 `KernelCodeError`。
- 当维度包含 `SymbolDim` 时，输出维度严格等于 `target_shape`；兼容性检查仍按上述对齐规则逐维验证，不得以“由实现推导”替代。
- 非法例：`broadcast_to(source, [SymbolDim("N")], MemorySpace.LM)` 目标 rank 小于 `source.rank` 时必须显式报错。

- 返回值：

- 返回 `Memory` 语义结果。
- `out.shape == target_shape`。
- `out.dtype == source.dtype`。
- `out.space == space`。
- `out.format == Farmat.Norm`。
- `out.stride` 等价于 `Memory(target_shape, source.dtype, space=space, format=Farmat.Norm).get_stride()`（连续行主序默认 stride 语义沿用 `Memory` 规范）。

### `transpose(value: Memory, perm: Sequence[int]) -> Memory`

- api：`transpose(value: Memory, perm: Sequence[int]) -> Memory`

- 功能说明：

- 按 `perm` 置换维度顺序，返回新的 `Memory` 结果。

- 参数：

- `value` (`Memory`)：待转置输入。
- `perm` (`Sequence[int]`)：轴置换顺序，长度必须与 `value.rank` 一致。

- 使用示例：

```python
value = Memory(shape=["M", "N", "K"], dtype=NumericType.Float32)
out = transpose(value, perm=[1, 0, 2])
```

- 注意事项：

- `perm` 必须是 `0..rank-1` 的排列，且不允许重复索引。
- `value` 必须为 `Memory`，`perm` 必须为整数序列。

- 返回值：

- 返回 `Memory` 语义结果。
- `out.shape` 按 `perm` 重排。
- `out.stride` 按 `out.shape` 生成默认连续 stride；`transpose` 表示物化搬运，不返回 source 的非连续视图。
- `out.dtype` 与 `out.space` 继承自 `value`。

### `softmax(value: Memory, axis: int = -1) -> Memory`

- api：`softmax(value: Memory, axis: int = -1) -> Memory`

- 功能说明：

- 沿给定轴对输入执行 softmax 归一化，返回概率分布语义的 `Memory` 结果。

- 参数：

- `value` (`Memory`)：待归一化输入。
- `axis` (`int`)：归一化轴，默认 `-1`（最后一维）。

- 使用示例：

```python
value = Memory(shape=["M", "N"], dtype=NumericType.Float32)
out = softmax(value)
out_last_dim = softmax(value, axis=1)
```

- 注意事项：

- `value` 必须为 `Memory`，否则抛出 `KernelCodeError`。
- `value.dtype` 必须为浮点类型：`Float16`、`BFloat16`、`Float32`、`Float64`；其他类型必须抛出 `KernelCodeError`。
- `axis` 必须为整数且不允许 `bool`；非法类型必须抛出 `KernelCodeError`。
- 允许负轴索引；归一化后的 `axis` 必须满足 `-rank <= axis < rank`，越界必须抛出 `KernelCodeError`；因此 rank 为 `0` 的输入（若上游构造）始终无法通过 axis 校验。
- 数值稳定性要求：实现必须采用“减去该轴最大值后再指数化”的等价语义，即 `exp(x - max(x)) / sum(exp(x - max(x)))`，避免直接对原值指数化。
- 与现有 nn 算子兼容：`softmax` 输出仍为 `Memory`，可直接作为 `add/sub/mul/truediv/floordiv/compare` 的输入。
- 与 `nn dialect` 的映射边界：operation 层固定高层语义与异常口径；dialect 层只固定结构化字段与 verifier，见 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 的 `nn.softmax` 小节。
- 与 lowering 链路的机械边界：`softmax` 的高层输出合同保持不变，但 `nn.softmax` 不允许由 `NnLoweringPass` 直降旧 softmax kernel op；进入该 pass 前必须先分解为 `nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。

- 返回值：

- 返回 `Memory` 语义结果。
- `out.shape == value.shape`。
- `out.dtype == value.dtype`。
- `out.space == value.space`。
- `out.format == value.format`。
- `out.stride == value.stride`。

### `fc(value: Memory, weight: Memory, bias: Memory | None = None) -> Memory`

- api：`fc(value: Memory, weight: Memory, bias: Memory | None = None) -> Memory`

- 功能说明：

- 全连接（fully connected）运算，对输入末维与权重输入特征维执行线性变换；`bias` 为可选项。

- 参数：

- `value` (`Memory`)：输入张量，`rank >= 2`，末维表示输入特征维 `in_features`。
- `weight` (`Memory`)：权重张量，`rank == 2`，形状为 `[out_features, in_features]`。
- `bias` (`Memory|None`)：可选偏置，默认 `None`；提供时必须与输出特征维对齐（`shape == [out_features]`）。

- 使用示例：

```python
value = Memory(shape=["B", "T", "K"], dtype=NumericType.Float32)
weight = Memory(shape=["N", "K"], dtype=NumericType.Float32)
out = fc(value, weight)
bias = Memory(shape=["N"], dtype=NumericType.Float32)
out_with_bias = fc(value, weight, bias=bias)
```

- 注意事项：

- `value` 与 `weight` 必须为 `Memory`，否则抛出 `KernelCodeError`。
- `bias` 仅允许为 `None` 或 `Memory`，其他类型必须抛出 `KernelCodeError`。
- `value.rank < 2` 或 `weight.rank != 2` 必须抛出 `KernelCodeError`。
- 维度约束：`value.shape[-1]` 必须与 `weight.shape[1]` 一致；不一致必须抛出 `KernelCodeError`。
- `bias` 提供时必须满足 `bias.rank == 1` 且 `bias.shape[0] == weight.shape[0]`（与输出特征维对齐）；不满足必须抛出 `KernelCodeError`。
- `value.space` 与 `weight.space` 必须一致；`bias` 提供时其 `space` 也必须一致，不一致必须抛出 `KernelCodeError`。
- `dtype` 决议沿用 `add` 的固定优先级规则（低精度 -> 高精度，整浮混合取浮点）；`bias` 提供时其 `dtype` 必须与结果 `dtype` 兼容，否则抛出 `KernelCodeError`。
- 批维处理规则：除末维外，`value` 的前缀维度按原顺序保留到输出。
- 与现有 nn 算子兼容：`fc` 输出仍为 `Memory`，可直接作为逐元素算术、比较、`matmul` 等算子的输入。
- decomposition（机械写死）：`dsl/mlir_gen` 不得生成独立的 `fc` 方言 op；必须将 `fc` 分解为 raw `nn.matmul`（以及可选的 bias add）后再进入后续 lowering 链路。

- 返回值：

- 返回 `Memory` 语义结果。
- 设 `value.shape = [d0, d1, ..., d{n-1}, in_features]`、`weight.shape = [out_features, in_features]`，则 `out.shape = [d0, d1, ..., d{n-1}, out_features]`。
- `out.dtype` 按固定优先级规则（低精度 -> 高精度，整浮混合取浮点）决议。
- `out.space == value.space`。
- `out.format == Farmat.Norm`。
- `out.stride` 使用连续行主序默认步幅。

### `matmul(lhs: Memory, rhs: Memory, memoryspace: MemorySpace | None = None) -> Memory`

- api：`matmul(lhs: Memory, rhs: Memory, memoryspace: MemorySpace | None = None) -> Memory`

- 功能说明：

- 二维矩阵乘。

- 参数：

- `lhs` (`Memory`)：左操作数，`rank == 2`。
- `rhs` (`Memory`)：右操作数，`rank == 2`。
- `memoryspace` (`MemorySpace|None`)：结果空间覆盖参数；为 `None` 时沿用输入共同 `space`，显式传入时仅覆盖结果 `space`。

- 使用示例：

```python
lhs = Memory(shape=["M", "K"], dtype=NumericType.Float32)
rhs = Memory(shape=["K", "N"], dtype=NumericType.Float32)
out = matmul(lhs, rhs)
tmp = matmul(lhs, rhs, memoryspace=MemorySpace.SM)
```

- 注意事项：

- 仅支持二维 `Memory x Memory`。
- 不支持 batch、广播或隐式转置。
- `lhs.space` 与 `rhs.space` 必须一致；即使显式传入 `memoryspace`，输入两侧的 `space` 仍必须先满足一致性。
- `dtype` 按与 `add` 相同的固定优先级决议，选择顺序更靠后的类型。
- 结果 `format` 固定回落为 `Farmat.Norm`。
- 结果 `stride` 固定为连续行主序默认步幅，即 `[rhs.shape[1], 1]`；符号维场景下继续复用 `Memory` 默认 stride 语义与序列化口径。

- 返回值：

- 返回 `Memory` 语义结果。
- `out.shape == ["M", "N"]`。
- `out.dtype` 按固定优先级决议并选择顺序更靠后的类型。
- `out.space` 在 `memoryspace is None` 时继承输入共同 `space`，否则取显式传入的 `memoryspace`。
- `out.format == Farmat.Norm`。
- `out.stride == [rhs.shape[1], 1]`。

### `conv(value: Memory, weight: Memory, bias: Memory | None = None, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`

- api：`conv(value: Memory, weight: Memory, bias: Memory | None = None, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`

- 功能说明：

- 二维卷积（NCHW），返回新的 `Memory` 描述。

- 参数：

- `value` (`Memory`)：输入特征图，shape 为 `[N, C_in, H, W]`。
- `weight` (`Memory`)：卷积核权重，shape 为 `[C_out, C_in, K_h, K_w]`。
- `bias` (`Memory|None`)：可选偏置，省略时不执行偏置加法；提供时必须与 `C_out` 对齐。
- `sh`/`sw` (`int|SymbolDim`)：stride，高度/宽度方向，必须为正数。
- `dh`/`dw` (`int|SymbolDim`)：dilation，高度/宽度方向，必须为正数。
- `ph`/`pw`/`pl`/`pr` (`int|SymbolDim`)：padding，分别为上/下/左/右，必须为非负数。

- 使用示例：

```python
value = Memory([1, 3, 32, 32], NumericType.Float32)
weight = Memory([8, 3, 3, 3], NumericType.Float32)
out = conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

bias = Memory([8], NumericType.Float32)
out = conv(value, weight, bias=bias, sh=2, sw=2, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
```

- 注意事项：

- `value`/`weight` 必须为 `Memory` 且 rank=4，否则抛出 `KernelCodeError`。
- `value.shape[1]` 必须与 `weight.shape[1]` 一致，否则抛出 `KernelCodeError`。
- `value.dtype` 与 `weight.dtype` 必须一致；`value.space` 与 `weight.space` 必须一致。
- `bias` 省略时不参与计算；提供时必须为 `Memory` 且 rank=1，`bias.shape == [C_out]`，且 `bias.dtype`/`bias.space` 与输出一致，否则抛出 `KernelCodeError`。
- 输出高宽按公式计算：
  - `H_out = floor((H + ph + pw - dh * (K_h - 1) - 1) / sh) + 1`
  - `W_out = floor((W + pl + pr - dw * (K_w - 1) - 1) / sw) + 1`
- 当 `H_out` 或 `W_out` 为确定整数且不为正时，必须抛出 `KernelCodeError`。
- decomposition（机械写死）：`dsl/mlir_gen` 不得生成独立的 `conv` 方言 op；必须将 `conv` 分解为 raw `nn.img2col2d + nn.matmul`（以及必要 attrs）后再进入后续 lowering 链路。

- 返回值：

- 返回 `Memory` 语义结果。
- `out.shape == [N, C_out, H_out, W_out]`，`C_out` 取自 `weight.shape[0]`。
- `out.dtype == value.dtype`，`out.space == value.space`。
- `out.format == Farmat.Norm`，`out.stride` 为连续行主序默认步幅（沿用 `Memory` 默认 stride 语义与序列化口径）。

### `img2col1d(value: Memory, kw: int | SymbolDim, sw: int | SymbolDim = 1, dw: int | SymbolDim = 1, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`

- api：`img2col1d(value: Memory, kw: int | SymbolDim, sw: int | SymbolDim = 1, dw: int | SymbolDim = 1, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`

- 功能说明：

- 一维窗口展开高层接口语义锚点：把 rank-3 输入 `Memory` 按滑窗重排为结构化列块表示。

- 参数：

- `value` (`Memory`)：输入特征图，`Farmat.Norm` 形态为 `[N, C, W]`，`Farmat.CLast` 形态为 `[N, W, C]`。
- `kw` (`int|SymbolDim`)：卷积核宽度，必须为正数（不建议使用 `bool`）。
- `sw` (`int|SymbolDim`)：宽度步长，必须为正数（不建议使用 `bool`）。
- `dw` (`int|SymbolDim`)：宽度膨胀，必须为正数（不建议使用 `bool`）。
- `pl`/`pr` (`int|SymbolDim`)：左/右 padding，必须为非负数（不建议使用 `bool`）。

- 使用示例：

```python
value = Memory([1, 16, 32], NumericType.Float32, format=Farmat.Norm)
cols = img2col1d(value, kw=3, sw=1, dw=1, pl=1, pr=1)
```

- 注意事项：

- `value` 必须为 `Memory` 且 rank=3，否则抛出 `KernelCodeError`。
- `value.format` 仅支持 `Farmat.Norm`/`Farmat.CLast`；其他格式必须抛出 `KernelCodeError`。
- `kw/sw/dw` 必须为正数，`pl/pr` 必须为非负数；`bool` 作为参数类型不在支持范围内，实现可选择抛出 `KernelCodeError`。
- 输出宽度按公式计算：
  - `W_out = floor((W + pl + pr - dw * (kw - 1) - 1) / sw) + 1`
  - 当参与维度为 `SymbolDim` 且无法静态取整时，保留符号表达：`W_out = (W + pl + pr - dw * (kw - 1) - 1) / sw + 1`。
- 当 `W_out` 为确定整数且不为正时，必须抛出 `KernelCodeError`。
- 与方言合同关系：lowering 后对应 `nn.img2col1d`，IR 结构与 verifier 规则见 [`spec/dialect/nn.md`](../../spec/dialect/nn.md)；方言规范不复写本节高层 shape/错误语义。

- 返回值：

- 返回 `Memory` 语义结果。
- `value.format == Farmat.Norm` 时，`out.shape == [N, C, kw, W_out]`。
- `value.format == Farmat.CLast` 时，`out.shape == [N, W_out, kw, C]`。
- `out.dtype == value.dtype`，`out.space == value.space`。
- `out.format == Farmat.Norm`，`out.stride` 为连续行主序默认步幅。

### `img2col2d(value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`

- api：`img2col2d(value: Memory, kh: int | SymbolDim, kw: int | SymbolDim, sh: int | SymbolDim = 1, sw: int | SymbolDim = 1, dh: int | SymbolDim = 1, dw: int | SymbolDim = 1, ph: int | SymbolDim = 0, pw: int | SymbolDim = 0, pl: int | SymbolDim = 0, pr: int | SymbolDim = 0) -> Memory`

- 功能说明：

- 二维窗口展开高层接口语义锚点：把 rank-4 输入 `Memory` 按滑窗重排为结构化列块表示。

- 参数：

- `value` (`Memory`)：输入特征图，`Farmat.Norm` 形态为 `[N, C, H, W]`，`Farmat.CLast` 形态为 `[N, H, W, C]`。
- `kh`/`kw` (`int|SymbolDim`)：卷积核高/宽，必须为正数（不建议使用 `bool`）。
- `sh`/`sw` (`int|SymbolDim`)：步长高/宽，必须为正数（不建议使用 `bool`）。
- `dh`/`dw` (`int|SymbolDim`)：膨胀高/宽，必须为正数（不建议使用 `bool`）。
- `ph`/`pw`/`pl`/`pr` (`int|SymbolDim`)：上/下/左/右 padding，必须为非负数（不建议使用 `bool`）。

- 使用示例：

```python
value = Memory([1, 3, 5, 5], NumericType.Float32, format=Farmat.Norm)
cols = img2col2d(value, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)
```

- 注意事项：

- `value` 必须为 `Memory` 且 rank=4，否则抛出 `KernelCodeError`。
- `value.format` 仅支持 `Farmat.Norm`/`Farmat.CLast`；其他格式必须抛出 `KernelCodeError`。
- `kh/kw/sh/sw/dh/dw` 必须为正数，`ph/pw/pl/pr` 必须为非负数；`bool` 作为参数类型不在支持范围内，实现可选择抛出 `KernelCodeError`。
- 输出尺寸按以下公式计算：
  - `H_out = floor((H + ph + pw - dh * (kh - 1) - 1) / sh) + 1`
  - `W_out = floor((W + pl + pr - dw * (kw - 1) - 1) / sw) + 1`
  - 当参与维度为 `SymbolDim` 且无法静态取整时，保留符号表达：`H_out = (H + ph + pw - dh * (kh - 1) - 1) / sh + 1`，`W_out = (W + pl + pr - dw * (kw - 1) - 1) / sw + 1`。
- 当 `H_out` 或 `W_out` 为确定整数且不为正时，必须抛出 `KernelCodeError`。
- 与方言合同关系：lowering 后对应 `nn.img2col2d`，IR 结构与 verifier 规则见 [`spec/dialect/nn.md`](../../spec/dialect/nn.md)；方言规范不复写本节高层 shape/错误语义。

- 返回值：

- 返回 `Memory` 语义结果。
- `value.format == Farmat.Norm` 时，`out.shape == [N, C, kh, kw, H_out, W_out]`。
- `value.format == Farmat.CLast` 时，`out.shape == [N, H_out, W_out, kh, kw, C]`。
- `out.dtype == value.dtype`，`out.space == value.space`。
- `out.format == Farmat.Norm`，`out.stride` 为连续行主序默认步幅。

## 额外补充

### 职责矩阵与 lowering 目标面（机械写死）

- 本文件定义 “用户可调用语义合同”：shape/axis/参数校验、输出 `Memory` 元信息与错误边界。
- `operation/nn` 允许表述“隐式 broadcast”的高层语义，但不得把该隐式语义转嫁给 `kernel` 层兜底；进入方言链路前必须显式化 broadcast/transpose/structured op 的目标面。

| 高层语义入口 | 进入方言后的最小承载 | pass lowering 目标面 |
| --- | --- | --- |
| 逐元素算术/比较（含隐式 broadcast 语义） | `nn.*` 逐元素 op + 必要时显式 `nn.broadcast` | `kernel.*`（compare/mixed compare 见下） |
| `broadcast(value, target)` / `broadcast_to(source, target_shape, space)` | `nn.broadcast`（目标 shape 由 result type 承载） | `dma.broadcast` |
| `transpose(value, perm)` | `nn.transpose` | `dma.transpose` |
| `exp` | `nn.exp` | `kernel.exp` |
| `reduce_sum/min/max` | `nn.reduce_*` | `kernel.reduce_*` |
| `softmax` | `nn.softmax` | 先分解为 `nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`，再分别 lower 到 `dma/kernel` |
| `matmul` | `nn.matmul` | `kernel.matmul` |
| `img2col1d/img2col2d` | `nn.img2col1d/nn.img2col2d` | `kernel.img2col1d/kernel.img2col2d` |
| `conv` | raw `nn.img2col2d + nn.matmul (+ attrs)` | 继续落入 `img2col/matmul` 的 lowering 主链 |
| `fc` | raw `nn.matmul`（+ 可选 bias add） | 继续落入 `matmul` 的 lowering 主链 |

### mixed compare 的显式化要求

- `memory + memory` compare：若本层语义需要 broadcast，则必须在进入方言前插入显式 `broadcast/broadcast_to`，保证 compare 发生时两侧均为同 shape 的 memory。
- `memory + symbol/const` compare：必须在 pass 中使用 `dma.alloc + dma.broadcast` 先物化 scalar/symbol 到 temporary memory，然后再进入 `kernel.compare family`；禁止 `kernel` compare 直接接收非 memory operand。

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 逐元素算术支持隐式广播，仅允许尾维对齐与 singleton dim 扩张。
- 逐元素比较在 operation 层允许复用相同的隐式广播语义；但进入 `nn/dma/kernel` 方言链路前必须显式化广播（见“额外补充/职责矩阵与 lowering 目标面”），禁止在 `kernel` 层保留“隐式 broadcast 的 compare”。
- `transpose` 仅支持 `Memory` 输入与显式轴置换，不支持标量或隐式转置。
- `fc` 仅定义“输入末维 × 权重输入特征维”的全连接语义；`bias` 为可选参数。
- `matmul` 仅定义二维矩阵乘，不支持 batch、广播或隐式转置。
- `softmax` 仅支持 `Memory` 输入，默认沿最后一维归一化，不负责跨算子融合或近似策略选择。
- `exp` 与激活函数同层，输入必须是浮点 `Memory`，不定义自动 cast 策略。
- `reduce_sum` / `reduce_min` / `reduce_max` 只定义按轴归约语义，不定义跨算子融合、并行调度或设备特化策略。
- `softmax` 在 operation 层定义默认参数、负轴归一化、数值稳定语义与错误边界；对应 dialect 层仅承接结构化 `nn.softmax` 合同（operand/result/axis/space verifier），不在 dialect 层重复高层数值语义全文。
- `conv` 仅覆盖二维卷积，不支持 group、batch/broadcast 或隐式转置。
- `img2col` 高层接口按维度拆分为 `img2col1d` 与 `img2col2d` 语义锚点；禁止继续使用笼统公开名 `img2col` 作为稳定对外规范名。
- 与 `nn dialect` 的分层关系：本层定义高层 shape/参数/错误语义，方言层仅定义 `nn.img2col1d` / `nn.img2col2d` 的 IR 字段与 verifier 合同（见 [`spec/dialect/nn.md`](../../spec/dialect/nn.md)）。
- 不定义归约以外的统计类算子（如 `mean` / `var` / `argmax` / `argmin`）。
- 不引入超出本文规则的复杂自动类型提升；`dtype` 兼容性需显式检查。
- 不负责 AST/IR/lowering 设计。
- 激活函数仅支持 `Memory` 输入；输出 `shape`/`dtype`/`space`/`format`/`stride` 继承输入，仅允许浮点 `dtype`（`Float16`/`BFloat16`/`Float32`/`Float64`）。
- `kernel_gen.operation.nn` 是本组稳定包入口；当前实现已完整组织到 `common / broadcast / elementwise_binary / elementwise_compare / activation / exp / reduction / fc / matmul / conv / img2col / softmax / transpose` 子模块下。旧私有文件 `_nn_common / _nn_broadcast / _nn_elementwise / _nn_reduction / _nn_structured` 已删除，不再保留兼容导入路径。
- `kernel_gen.operation` 顶层稳定导出只保留经过包级聚合的子集：`add / sub / mul / truediv / eq / ne / lt / le / gt / ge / matmul`；`floordiv`、激活、`broadcast`、`transpose`、`softmax`、`fc`、`conv`、`img2col1d`、`img2col2d` 与归约族均继续通过 `kernel_gen.operation.nn` 访问，不在本轮顺手上提到顶层。

## 测试

- 测试文件：`test/operation/nn/test_package.py`
- 执行命令：
  - `pytest -q test/operation/nn/test_package.py`
  - `pytest -q test/operation/nn/test_package.py -k activation`
  - `pytest -q test/operation/nn/test_package.py -k "test_nn_add_memory or test_nn_other_arithmetic or test_nn_floordiv_rules or test_nn_matmul_success or test_nn_dtype_mismatch or test_nn_matmul_dtype_mismatch"`

### 测试目标

- 验证逐元素算术/比较的成功路径、链式表达式、标量参与规则与错误规则。
- 验证 `nn.md` 的 family 口径仍以 `逐元素 / broadcast / structured / reduction` 为主轴理解，不回退到“按单文件实现顺序罗列”的阅读方式。
- 验证 `kernel_gen.operation` 顶层导出继续只暴露克制子集；`img2col1d/img2col2d`、`transpose` 等 helper 不回流到顶层。
- 验证 `nn.add` 在同形状输入时保持原有 `Memory` 描述。
- 验证显式 `broadcast(value, target)` 与 `broadcast_to(source, target_shape, space)` 的尾维对齐、前置维扩张、目标对齐与错误规则。
- 验证逐元素隐式 broadcast 的 singleton dim / 前置维扩张与错误规则。
- 验证 nn 算术算子（`add/sub/mul/truediv/floordiv/matmul`）遵循统一 OP-TP 类型提升规则。
- 验证 `Memory/Memory` 路径按固定优先级选择更靠后类型，`Memory/标量` 路径按 `Int32` 参与决议。
- 验证整浮 mixed dtype 参与算术时提升到浮点并取浮点侧更高优先级类型，以及 `format/stride` 不一致时回落默认布局。
- 验证比较算子与 `broadcast` 路径不适用算术类型提升规则。
- 验证 `fc(value, weight, bias=None)` 的输入/权重约束、可选 `bias` 对齐规则、批维保留与输出 shape 推导。
- 验证 `fc` 的非法输入与报错规则：参数类型、rank、特征维不匹配、`bias` 维度不对齐、`space` 不一致。
- 验证 `matmul(lhs, rhs, memoryspace=None)` 的二维输入约束、`memoryspace` 覆盖、结果 `format/stride` 口径与错误规则。
- 验证 `softmax(value, axis=-1)` 的 axis 默认值/负轴归一化、输入 dtype 约束、数值稳定性语义要求与错误路径。
- 验证 `exp(value)` 的浮点输入约束、输出元信息继承与错误路径。
- 验证 `reduce_sum` / `reduce_min` / `reduce_max` 的 axis 规范化、`keepdim` 规则与输出 shape 推导。
- 验证 `reduce_min` / `reduce_max` 的空归约域错误路径（静态可判定维度为 `0`）。
- 验证比较结果使用 `NumericType.Bool` 作为 predicate 载体。
- 验证 nn 操作不依赖已移除的旧 shape 规范化入口。
- 验证 `img2col1d` 在 `Farmat.Norm/Farmat.CLast` 形态下的结构化输出形状与参数校验规则（`Norm -> NCHW`，`CLast -> NWC`）。
- 验证 `img2col2d` 在 `Farmat.Norm/Farmat.CLast` 形态下的结构化输出形状与参数校验规则（`Norm -> NCHW`，`CLast -> NHWC`）。
- 验证 `conv` 的参数校验、输出形状公式与 bias 可选对齐规则。
- 验证激活函数的输入输出约束、参数规则与错误路径。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-OP-001 | 内存/DMA | `add` 基础逐元素运算 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_add_memory`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`add` 基础逐元素运算”场景。 | `test_nn_add_memory` |
| TC-OP-002 | 公开入口 | `sub`/`mul`/`truediv` 逐元素算术可调用 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_other_arithmetic`。 | 公开入口在“`sub`/`mul`/`truediv` 逐元素算术可调用”场景下可导入、构造、注册或按名称发现。 | `test_nn_other_arithmetic` |
| TC-OP-002A | 边界/异常 | `sub` 支持标量反向调用，且 `dtype` 决议与 `add` 一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_sub_reverse_and_dtype_mismatch`。 | “`sub` 支持标量反向调用，且 `dtype` 决议与 `add` 一致”场景按公开错误语义失败或被拒绝。 | `test_nn_sub_reverse_and_dtype_mismatch` |
| TC-OP-002B | 内存/DMA | `sub` 在 `format/stride` 不一致时回落默认布局 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_sub_format_fallback`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`sub` 在 `format/stride` 不一致时回落默认布局”场景。 | `test_nn_sub_format_fallback` |
| TC-OP-003 | 边界/异常 | shape 不一致报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_shape_mismatch`。 | “shape 不一致报错”场景按公开错误语义失败或被拒绝。 | `test_nn_shape_mismatch` |
| TC-OP-004 | 边界/异常 | rank 不一致报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_rank_mismatch`。 | “rank 不一致报错”场景按公开错误语义失败或被拒绝。 | `test_nn_rank_mismatch` |
| TC-OP-005 | 内存/DMA | `Memory + scalar` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_add_scalar`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`Memory + scalar`”场景。 | `test_nn_add_scalar` |
| TC-OP-005A | 内存/DMA | `Memory + bool scalar` 仍走标量路径并保持 `Memory` 结果描述 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_add_bool_scalar`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`Memory + bool scalar` 仍走标量路径并保持 `Memory` 结果描述”场景。 | `test_nn_add_bool_scalar` |
| TC-OP-006 | 公开入口 | 链式表达式保持形状与 dtype | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_chain_expression`。 | 公开入口在“链式表达式保持形状与 dtype”场景下可导入、构造、注册或按名称发现。 | `test_nn_chain_expression` |
| TC-OP-007 | 边界/异常 | 非法标量类型报 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_scalar_type_error`。 | “非法标量类型报 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_scalar_type_error` |
| TC-OP-008 | 边界/异常 | `add` 的不支持 `dtype` 输入触发 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_dtype_invalid_error`。 | “`add` 的不支持 `dtype` 输入触发 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_dtype_invalid_error` |
| TC-OP-009 | 公开入口 | 比较结果使用 `NumericType.Bool` 作为 predicate 载体 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_compare_predicate`。 | 公开入口在“比较结果使用 `NumericType.Bool` 作为 predicate 载体”场景下可导入、构造、注册或按名称发现。 | `test_nn_compare_predicate` |
| TC-OP-010 | 边界/异常 | 比较时 shape 顺序不同报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_compare_shape_order`。 | “比较时 shape 顺序不同报错”场景按公开错误语义失败或被拒绝。 | `test_nn_compare_shape_order` |
| TC-OP-011 | 边界/异常 | 纯标量输入复用 Python/SymbolDim 算术语义，非法标量类型仍报 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_scalar_only_error`。 | “纯标量输入复用 Python/SymbolDim 算术语义，非法标量类型仍报 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_scalar_only_error` |
| TC-OP-012 | 公开入口 | `ne`/`le`/`ge` 比较别名可调用，且结果 `dtype` 为 `NumericType.Bool` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_compare_alias`。 | 公开入口在“`ne`/`le`/`ge` 比较别名可调用，且结果 `dtype` 为 `NumericType.Bool`”场景下可导入、构造、注册或按名称发现。 | `test_nn_compare_alias` |
| TC-OP-013 | 内存/DMA | 同布局的 `Memory/Memory add` 保持原有 `Memory` 描述，且不依赖已移除的旧 shape 规范化入口 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_operation_does_not_require_convert_from_list`。 | 内存类型、布局、搬运结果或 verifier 行为体现“同布局的 `Memory/Memory add` 保持原有 `Memory` 描述，且不依赖已移除的旧 shape 规范化入口”场景。 | `test_nn_operation_does_not_require_convert_from_list` |
| TC-OP-017 | 公开入口 | `floordiv` 复用逐元素算术规则、支持标量并在布局不一致时回落默认布局 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_floordiv_rules`。 | 公开入口在“`floordiv` 复用逐元素算术规则、支持标量并在布局不一致时回落默认布局”场景下可导入、构造、注册或按名称发现。 | `test_nn_floordiv_rules` |
| TC-OP-TP-001 | 边界/异常 | nn 算术统一类型优先级按 `Int8` 到 `Float64`，`Memory/Memory` 结果选择顺序更靠后类型 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_dtype_mismatch`, `test_nn_matmul_dtype_mismatch`。 | “nn 算术统一类型优先级按 `Int8` 到 `Float64`，`Memory/Memory` 结果选择顺序更靠后类型”场景按公开错误语义失败或被拒绝。 | `test_nn_dtype_mismatch`, `test_nn_matmul_dtype_mismatch` |
| TC-OP-TP-002 | 边界/异常 | 整数与浮点 mixed dtype 的算术结果必须提升到浮点并取浮点侧更高优先级类型 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_dtype_mismatch`, `test_nn_sub_reverse_and_dtype_mismatch`, `test_nn_floordiv_rules`, `test_nn_matmul_dtype_mismatch`。 | “整数与浮点 mixed dtype 的算术结果必须提升到浮点并取浮点侧更高优先级类型”场景按公开错误语义失败或被拒绝。 | `test_nn_dtype_mismatch`, `test_nn_sub_reverse_and_dtype_mismatch`, `test_nn_floordiv_rules`, `test_nn_matmul_dtype_mismatch` |
| TC-OP-TP-003 | 边界/异常 | `Memory/标量` 路径按 `Int32` 参与类型决议，再选择顺序更靠后类型 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_dtype_mismatch`, `test_nn_floordiv_rules`。 | “`Memory/标量` 路径按 `Int32` 参与类型决议，再选择顺序更靠后类型”场景按公开错误语义失败或被拒绝。 | `test_nn_dtype_mismatch`, `test_nn_floordiv_rules` |
| TC-OP-TP-004 | 边界/异常 | OP-TP 规则仅适用于算术算子（`add/sub/mul/truediv/floordiv/matmul`） | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_other_arithmetic`, `test_nn_sub_reverse_and_dtype_mismatch`, `test_nn_floordiv_rules`, `test_nn_matmul_success`。 | “OP-TP 规则仅适用于算术算子（`add/sub/mul/truediv/floordiv/matmul`）”场景按公开错误语义失败或被拒绝。 | `test_nn_other_arithmetic`, `test_nn_sub_reverse_and_dtype_mismatch`, `test_nn_floordiv_rules`, `test_nn_matmul_success` |
| TC-OP-TP-005 | 公开入口 | 比较算子与显式广播路径不适用 OP-TP：比较结果固定 `Bool`，broadcast 结果对齐 target 描述 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_compare_predicate`, `test_nn_compare_alias`, `test_nn_broadcast_success`。 | 公开入口在“比较算子与显式广播路径不适用 OP-TP：比较结果固定 `Bool`，broadcast 结果对齐 target 描述”场景下可导入、构造、注册或按名称发现。 | `test_nn_compare_predicate`, `test_nn_compare_alias`, `test_nn_broadcast_success` |
| TC-OP-TP-006 | 边界/异常 | 不支持的 dtype 参与算术提升或非法标量输入必须抛错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_dtype_invalid_error`, `test_nn_scalar_type_error`。 | “不支持的 dtype 参与算术提升或非法标量输入必须抛错”场景按公开错误语义失败或被拒绝。 | `test_nn_dtype_invalid_error`, `test_nn_scalar_type_error` |
| TC-OP-EXP-001 | 公开入口 | `img2col1d` / `img2col2d` 继续可从 `kernel_gen.operation.nn` package-root 直接获取，且 `kernel_gen.operation` 顶层不顺手暴露 `img2col1d` / `img2col2d` / 旧 `img2col` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_img2col_public_exports`。 | 公开入口在“`img2col1d` / `img2col2d` 继续可从 `kernel_gen.operation.nn` package-root 直接获取，且 `kernel_gen.operation` 顶层不顺手暴露 `img2col1d` / `img2col2d` / 旧 `img2col`”场景下可导入、构造、注册或按名称发现。 | `test_nn_img2col_public_exports` |
| TC-OP-EXP-002 | 公开入口 | `transpose` 继续可从 `kernel_gen.operation.nn` package-root 直接获取，且 `kernel_gen.operation` 顶层不顺手暴露 `transpose` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_transpose_exported_at_package_root`。 | 公开入口在“`transpose` 继续可从 `kernel_gen.operation.nn` package-root 直接获取，且 `kernel_gen.operation` 顶层不顺手暴露 `transpose`”场景下可导入、构造、注册或按名称发现。 | `test_nn_transpose_exported_at_package_root` |
| TC-OP-ACT-001 | 执行结果 | `relu`/`sigmoid`/`tanh`/`hard_sigmoid` 输出 `shape/dtype/space/stride/format` 继承输入 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_activation_basic`。 | 命令返回码、输出、执行结果或状态变更体现“`relu`/`sigmoid`/`tanh`/`hard_sigmoid` 输出 `shape/dtype/space/stride/format` 继承输入”场景。 | `test_nn_activation_basic` |
| TC-OP-ACT-002 | 公开入口 | `leaky_relu` 的 `alpha` 参数规则与边界行为 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_activation_leaky_relu_alpha`。 | 公开入口在“`leaky_relu` 的 `alpha` 参数规则与边界行为”场景下可导入、构造、注册或按名称发现。 | `test_nn_activation_leaky_relu_alpha` |
| TC-OP-ACT-003 | 边界/异常 | 激活函数的非 `Memory` 输入、非浮点 `dtype` 与无效参数报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_activation_invalid_input`。 | “激活函数的非 `Memory` 输入、非浮点 `dtype` 与无效参数报错”场景按公开错误语义失败或被拒绝。 | `test_nn_activation_invalid_input` |
| TC-OP-EXP-001 | 内存/DMA | `exp` 仅接受浮点 `Memory` 输入并继承输入元信息 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_exp_basic`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`exp` 仅接受浮点 `Memory` 输入并继承输入元信息”场景。 | `test_nn_exp_basic` |
| TC-OP-EXP-002 | 边界/异常 | `exp` 对非 `Memory` 或非浮点 `dtype` 输入报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_exp_invalid_input`。 | “`exp` 对非 `Memory` 或非浮点 `dtype` 输入报错”场景按公开错误语义失败或被拒绝。 | `test_nn_exp_invalid_input` |
| TC-OP-RD-001 | 内存/DMA | `reduce_sum` 的 `axis=None/int/Sequence[int]` 归约规则与 shape 推导 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_reduce_sum_shape_contract`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`reduce_sum` 的 `axis=None/int/Sequence[int]` 归约规则与 shape 推导”场景。 | `test_nn_reduce_sum_shape_contract` |
| TC-OP-RD-002 | 边界/异常 | `reduce_sum` 的 `axis` 类型错误、越界、重复轴与空序列报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_reduce_sum_axis_error`。 | “`reduce_sum` 的 `axis` 类型错误、越界、重复轴与空序列报错”场景按公开错误语义失败或被拒绝。 | `test_nn_reduce_sum_axis_error` |
| TC-OP-RD-003 | 执行结果 | `reduce_min` / `reduce_max` 的 `keepdim` 规则与输出元信息口径 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_reduce_min_max_keepdim_contract`。 | 命令返回码、输出、执行结果或状态变更体现“`reduce_min` / `reduce_max` 的 `keepdim` 规则与输出元信息口径”场景。 | `test_nn_reduce_min_max_keepdim_contract` |
| TC-OP-RD-004 | 边界/异常 | `reduce_min` / `reduce_max` 在静态空归约域时报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_reduce_min_max_empty_extent_error`。 | “`reduce_min` / `reduce_max` 在静态空归约域时报错”场景按公开错误语义失败或被拒绝。 | `test_nn_reduce_min_max_empty_extent_error` |
| TC-OP-BC-001 | 执行结果 | `broadcast` / `broadcast_to` 可通过 singleton dim 扩张并返回与 `target` 完全一致的描述 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_broadcast_success`。 | 命令返回码、输出、执行结果或状态变更体现“`broadcast` / `broadcast_to` 可通过 singleton dim 扩张并返回与 `target` 完全一致的描述”场景。 | `test_nn_broadcast_success` |
| TC-OP-BC-002 | 符号语义 | `broadcast` / `broadcast_to` 支持前置维扩张并保持 `target` 描述 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_nn_broadcast_prepend_dimension`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`broadcast` / `broadcast_to` 支持前置维扩张并保持 `target` 描述”场景。 | `test_nn_broadcast_prepend_dimension` |
| TC-OP-BC-003 | 边界/异常 | `broadcast` / `broadcast_to` 维度不兼容报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_broadcast_dimension_mismatch`。 | “`broadcast` / `broadcast_to` 维度不兼容报错”场景按公开错误语义失败或被拒绝。 | `test_nn_broadcast_dimension_mismatch` |
| TC-OP-BC-004 | 边界/异常 | `broadcast` / `broadcast_to` 目标 rank 更小时报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_broadcast_rank_error`。 | “`broadcast` / `broadcast_to` 目标 rank 更小时报错”场景按公开错误语义失败或被拒绝。 | `test_nn_broadcast_rank_error` |
| TC-OP-BC-005 | 边界/异常 | `broadcast` / `broadcast_to` 非 `Memory` 输入报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_broadcast_non_memory_error`。 | “`broadcast` / `broadcast_to` 非 `Memory` 输入报错”场景按公开错误语义失败或被拒绝。 | `test_nn_broadcast_non_memory_error` |
| TC-OP-BC-006 | 边界/异常 | `broadcast` 非 `Memory` target 报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_broadcast_target_type_error`。 | “`broadcast` 非 `Memory` target 报错”场景按公开错误语义失败或被拒绝。 | `test_nn_broadcast_target_type_error` |
| TC-OP-IB-001 | 符号语义 | 算术支持 singleton dim 隐式 broadcast | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_nn_add_implicit_broadcast_singleton`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“算术支持 singleton dim 隐式 broadcast”场景。 | `test_nn_add_implicit_broadcast_singleton` |
| TC-OP-IB-002 | 符号语义 | 算术支持前置维隐式 broadcast | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_nn_add_implicit_broadcast_prepend_dimension`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“算术支持前置维隐式 broadcast”场景。 | `test_nn_add_implicit_broadcast_prepend_dimension` |
| TC-OP-IB-003 | 公开入口 | 比较运算复用隐式 broadcast | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_compare_implicit_broadcast`。 | 公开入口在“比较运算复用隐式 broadcast”场景下可导入、构造、注册或按名称发现。 | `test_nn_compare_implicit_broadcast` |
| TC-OP-IB-004 | 边界/异常 | 隐式 broadcast 维度不兼容报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_add_implicit_broadcast_mismatch`。 | “隐式 broadcast 维度不兼容报错”场景按公开错误语义失败或被拒绝。 | `test_nn_add_implicit_broadcast_mismatch` |
| TC-OP-014 | 边界/异常 | `add` 的 `Memory/Memory` 结果 `dtype` 按固定优先级（低精度 -> 高精度）决议 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_dtype_mismatch`。 | “`add` 的 `Memory/Memory` 结果 `dtype` 按固定优先级（低精度 -> 高精度）决议”场景按公开错误语义失败或被拒绝。 | `test_nn_dtype_mismatch` |
| TC-OP-015 | 公开入口 | `add` 在 `format` 不一致时回落默认布局 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_add_format_fallback`。 | 公开入口在“`add` 在 `format` 不一致时回落默认布局”场景下可导入、构造、注册或按名称发现。 | `test_nn_add_format_fallback` |
| TC-OP-016 | 内存/DMA | `add` 在 `stride` 不一致时回落默认布局，默认 stride 与序列化口径沿用 `Memory` 规范 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_add_stride_fallback`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`add` 在 `stride` 不一致时回落默认布局，默认 stride 与序列化口径沿用 `Memory` 规范”场景。 | `test_nn_add_stride_fallback` |
| TC-OP-016A | 内存/DMA | `add` 默认 stride 分量的序列化口径保持稳定 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_add_stride_dim_serialization`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`add` 默认 stride 分量的序列化口径保持稳定”场景。 | `test_nn_add_stride_dim_serialization` |
| TC-OP-FC-001 | 执行结果 | `fc` 支持 `bias=None`，输出保留输入批维并将末维替换为 `out_features` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_fc_without_bias`。 | 命令返回码、输出、执行结果或状态变更体现“`fc` 支持 `bias=None`，输出保留输入批维并将末维替换为 `out_features`”场景。 | `test_nn_fc_without_bias` |
| TC-OP-FC-002 | 执行结果 | `fc` 的 `bias` 为可选参数；提供时必须与输出特征维对齐（`shape == [out_features]`） | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_fc_with_optional_bias`。 | 命令返回码、输出、执行结果或状态变更体现“`fc` 的 `bias` 为可选参数；提供时必须与输出特征维对齐（`shape == [out_features]`）”场景。 | `test_nn_fc_with_optional_bias` |
| TC-OP-FC-003 | 边界/异常 | `fc` 的 `value/weight` 类型非法或 `bias` 非 `Memory | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_fc_type_error`。 | “`fc` 的 `value/weight` 类型非法或 `bias` 非 `Memory”场景按公开错误语义失败或被拒绝。 | `test_nn_fc_type_error` |
| TC-OP-FC-004 | 边界/异常 | `fc` 的 `rank` 约束（`value.rank >= 2`、`weight.rank == 2`）不满足时报 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_fc_rank_error`。 | “`fc` 的 `rank` 约束（`value.rank >= 2`、`weight.rank == 2`）不满足时报 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_fc_rank_error` |
| TC-OP-FC-005 | 边界/异常 | `fc` 输入特征维与权重输入特征维不一致时报 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_fc_feature_mismatch`。 | “`fc` 输入特征维与权重输入特征维不一致时报 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_fc_feature_mismatch` |
| TC-OP-FC-006 | 边界/异常 | `fc` 的 `bias` 维度不对齐（非 1D 或长度不等于 `out_features`）时报 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_fc_bias_shape_error`。 | “`fc` 的 `bias` 维度不对齐（非 1D 或长度不等于 `out_features`）时报 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_fc_bias_shape_error` |
| TC-OP-FC-007 | 边界/异常 | `fc` 输入 `space` 不一致时报 `KernelCodeError`，并保持与现有 nn 算子链式兼容 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_fc_space_mismatch`, `test_nn_fc_chain_compatibility`。 | “`fc` 输入 `space` 不一致时报 `KernelCodeError`，并保持与现有 nn 算子链式兼容”场景按公开错误语义失败或被拒绝。 | `test_nn_fc_space_mismatch`, `test_nn_fc_chain_compatibility` |
| TC-OP-MM-001 | 内存/DMA | `matmul(lhs, rhs, memoryspace=None)` 成功路径：结果 shape/dtype/space/format/stride 收敛到公开口径 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_matmul_success`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`matmul(lhs, rhs, memoryspace=None)` 成功路径：结果 shape/dtype/space/format/stride 收敛到公开口径”场景。 | `test_nn_matmul_success` |
| TC-OP-MM-002 | 内存/DMA | `matmul` 显式 `memoryspace` 仅覆盖结果 `space` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_matmul_space_override`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`matmul` 显式 `memoryspace` 仅覆盖结果 `space`”场景。 | `test_nn_matmul_space_override` |
| TC-OP-MM-003 | 边界/异常 | `matmul` contracting dim 不一致报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_matmul_contracting_dim_mismatch`。 | “`matmul` contracting dim 不一致报错”场景按公开错误语义失败或被拒绝。 | `test_nn_matmul_contracting_dim_mismatch` |
| TC-OP-MM-004 | 边界/异常 | `matmul` 非二维输入报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_matmul_rank_error`。 | “`matmul` 非二维输入报错”场景按公开错误语义失败或被拒绝。 | `test_nn_matmul_rank_error` |
| TC-OP-MM-005 | 边界/异常 | `matmul` 标量输入非法 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_matmul_scalar_operand_error`。 | “`matmul` 标量输入非法”场景按公开错误语义失败或被拒绝。 | `test_nn_matmul_scalar_operand_error` |
| TC-OP-MM-006 | 边界/异常 | `matmul` 的 `dtype` 按固定优先级决议并选择顺序更靠后类型 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_matmul_dtype_mismatch`。 | “`matmul` 的 `dtype` 按固定优先级决议并选择顺序更靠后类型”场景按公开错误语义失败或被拒绝。 | `test_nn_matmul_dtype_mismatch` |
| TC-OP-MM-007 | 边界/异常 | `matmul` 输入 `space` 不一致报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_matmul_space_mismatch`。 | “`matmul` 输入 `space` 不一致报错”场景按公开错误语义失败或被拒绝。 | `test_nn_matmul_space_mismatch` |
| TC-OP-SM-001 | 内存/DMA | `softmax` 默认 `axis=-1`，结果保持输入 `shape/dtype/space/format/stride` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_nn_softmax_default_axis`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`softmax` 默认 `axis=-1`，结果保持输入 `shape/dtype/space/format/stride`”场景。 | `test_nn_softmax_default_axis` |
| TC-OP-SM-002 | 符号语义 | `softmax` 支持负轴并归一化到合法维度 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_nn_softmax_negative_axis`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`softmax` 支持负轴并归一化到合法维度”场景。 | `test_nn_softmax_negative_axis` |
| TC-OP-SM-003 | 边界/异常 | `softmax` 的 `axis` 非整数或为 `bool` 时报 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_softmax_axis_type_error`。 | “`softmax` 的 `axis` 非整数或为 `bool` 时报 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_softmax_axis_type_error` |
| TC-OP-SM-004 | 边界/异常 | `softmax` 的 `axis` 越界时报 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_softmax_axis_out_of_range`。 | “`softmax` 的 `axis` 越界时报 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_softmax_axis_out_of_range` |
| TC-OP-SM-005 | 边界/异常 | `softmax` 非浮点 `dtype` 输入报 `KernelCodeError` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_nn_softmax_dtype_error`。 | “`softmax` 非浮点 `dtype` 输入报 `KernelCodeError`”场景按公开错误语义失败或被拒绝。 | `test_nn_softmax_dtype_error` |
| TC-OP-SM-006 | 公开入口 | `softmax` 限定数值稳定语义为 `exp(x - max(x)) / sum(exp(x - max(x)))` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_softmax_numerical_stability_contract`。 | 公开入口在“`softmax` 限定数值稳定语义为 `exp(x - max(x)) / sum(exp(x - max(x)))`”场景下可导入、构造、注册或按名称发现。 | `test_nn_softmax_numerical_stability_contract` |
| TC-OP-IMG2COL-001 | 执行结果 | `img2col1d` 在 `Farmat.Norm/CLast` 下输出结构化形状 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_img2col1d_contract`。 | 命令返回码、输出、执行结果或状态变更体现“`img2col1d` 在 `Farmat.Norm/CLast` 下输出结构化形状”场景。 | `test_nn_img2col1d_contract` |
| TC-OP-IMG2COL-002 | 执行结果 | `img2col2d` 在 `Farmat.Norm/CLast` 下输出结构化形状 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_img2col2d_contract`。 | 命令返回码、输出、执行结果或状态变更体现“`img2col2d` 在 `Farmat.Norm/CLast` 下输出结构化形状”场景。 | `test_nn_img2col2d_contract` |
| TC-OP-CONV-001 | 公开入口 | `conv` 基础路径与参数校验（含可选 bias 对齐） | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_conv_basic`。 | 公开入口在“`conv` 基础路径与参数校验（含可选 bias 对齐）”场景下可导入、构造、注册或按名称发现。 | `test_nn_conv_basic` |
