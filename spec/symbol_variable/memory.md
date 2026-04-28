# memory.md

## 功能简介

定义 Python 侧内存元信息容器 `Memory`，以及它依赖的 `LocalSpaceMeta`、`MemorySpace`。本模块只描述 `shape`、`stride`、`dtype`、`format`、`space` 这些结构化属性，不负责真实分配、容量校验、调度、拷贝或 IR type 定义。

## API 列表

- `class LocalSpaceMeta(name: str, max_size: int | None, align: int)`
- `class MemorySpace(Enum)`
- `class Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`
- `Memory.get_shape(self) -> list[int | str]`
- `Memory.get_stride(self) -> list[int | SymbolDim]`
- `Memory.get_type(self) -> NumericType`
- `Memory.get_space(self) -> MemorySpace`
- `Memory.get_format(self) -> Farmat`
- `Memory.clone(self, dtype: NumericType | None = None, space: MemorySpace | None = None) -> Memory`
- `Memory.__repr__(self) -> str`
- `Memory.__str__(self) -> str`
- `Memory.__add__(self, other: object) -> Memory`
- `Memory.__radd__(self, other: object) -> Memory`
- `Memory.__sub__(self, other: object) -> Memory`
- `Memory.__rsub__(self, other: object) -> Memory`
- `Memory.__mul__(self, other: object) -> Memory`
- `Memory.__rmul__(self, other: object) -> Memory`
- `Memory.__truediv__(self, other: object) -> Memory`
- `Memory.__rtruediv__(self, other: object) -> Memory`
- `Memory.__floordiv__(self, other: object) -> Memory`
- `Memory.__rfloordiv__(self, other: object) -> Memory`
- `Memory.__eq__(self, other: object) -> Memory`
- `Memory.__lt__(self, other: object) -> Memory`
- `Memory.__gt__(self, other: object) -> Memory`

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)、[`test/symbol_variable/test_memory_operation.py`](../../test/symbol_variable/test_memory_operation.py)、[`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
- `功能实现`：[`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)

## 依赖

- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)：`shape/stride` 容器语义。
- [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)：包级导出边界。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：`NumericType` 与 `Farmat` 语义。
- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：单个整型维度、步幅、偏移进入 IR 时的语义归属。
- [`spec/operation/nn.md`](../../spec/operation/nn.md)：逐元素算术和比较的来源语义。

## 边界

- 只定义 Python 侧 memory 元信息，不定义 memory type、dma result type 或其他 IR type。
- 不负责广播、约束求解、真实地址偏移推导、空间可用性判断和生命周期管理。
- `shape`、`stride` 的单个分量若进入 IR，统一复用 [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)。
- 本文件不重复定义 `SymbolDim` 算术规则，也不重复定义 `SymbolShape` 容器接口。
- 当前文件内允许存在 `_clone_with_dtype`、`_clone_shape_like` 等辅助函数，但它们只服务 `Memory.clone(...)` 与运算实现，不属于公开 API；其他模块与测试不得跨文件直连。

## 公开合同

### `LocalSpaceMeta`

- 不可变数据类，字段为 `name`、`max_size`、`align`。
- 只表示空间静态元信息；`max_size=None` 表示未指定。

示例：

```python
from kernel_gen.symbol_variable.memory import LocalSpaceMeta

meta = LocalSpaceMeta(name="GM", max_size=None, align=1024)
```

### `MemorySpace`

- 公开成员：`GM`、`SM`、`LM`、`TSM`、`TLM1`、`TLM2`、`TLM3`。
- 每个枚举值都是一个 `LocalSpaceMeta`。
- 旧别名 `MemorySpace.TLM` 不属于公开成员。

示例：

```python
from kernel_gen.symbol_variable.memory import MemorySpace

align = MemorySpace.GM.value.align
```

### `Memory(shape, dtype=NumericType.Float32, space=MemorySpace.GM, stride=None, format=Farmat.Norm)`

- `shape` 与显式 `stride` 都走 `SymbolShape(...)` 归一化。
- `dtype=None` 时默认 `NumericType.Float32`。
- `stride=None` 时按连续行主序生成默认步幅。
- 显式 `stride` 的 rank 必须与 `shape` 一致，否则抛 `ValueError("Stride rank mismatch with shape")`。

示例：

```python
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

mem = Memory(["B", 128], NumericType.Float32, space=MemorySpace.SM)
```

### `Memory.clone(dtype=None, space=None)`

- 返回一个新的 `Memory`，默认继承原对象的 `shape`、`stride`、`dtype`、`space` 与 `format`。
- `dtype is None` 时沿用原 `dtype`；传入 `NumericType` 时只覆盖结果 `dtype`。
- `space is None` 时沿用原 `space`；传入 `MemorySpace` 时只覆盖结果 `space`。
- 返回值必须复制 `shape/stride` 的公开元信息，避免与原对象共享同一 `SymbolShape` / `SymbolDim` 实例。
- `format` 固定继承原对象；`clone(...)` 不提供 `format` 或 `stride` 的公开覆写入口。
- `dtype` 非 `NumericType|None` 或 `space` 非 `MemorySpace|None` 时必须抛出 `TypeError`。
- `_clone_with_dtype(...)` 与 `_clone_shape_like(...)` 只允许作为当前文件内实现步骤存在，不得被其他模块或测试当作稳定入口调用。

示例：

```python
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

mem = Memory(["M", "N"], NumericType.Float32, space=MemorySpace.GM, stride=["N", 1])
cloned = mem.clone(dtype=NumericType.Int32, space=MemorySpace.SM)

assert cloned.get_shape() == ["M", "N"]
assert cloned.get_type() is NumericType.Int32
assert cloned.get_space() is MemorySpace.SM
assert cloned.get_format() is mem.get_format()
```

### 默认 `stride`

- 最后一维恒为 `1`。
- 其余维度为后续维度长度的乘积。
- 动态分量保持 `SymbolDim` 乘法表达式，不额外做字符串归一。

例子：

- `shape=[D]` -> `stride=[1]`
- `shape=[D0, D1]` -> `stride=[D1, 1]`
- `shape=[M, K, N]` -> `stride=[K*N, N, 1]`

### 元信息读取

- `get_shape()`：返回序列化后的公开 `shape`，静态分量为 `int`，动态分量为 `str`。
- `get_stride()`：返回 `stride` 列表，静态分量为 `int`，动态分量保留 `SymbolDim`。
- `get_type()`、`get_space()`、`get_format()`：直接返回记录的元信息。

### `shape/stride` 比较口径

- 默认按语义等价比较，不按底层表达式节点顺序比较。
- 静态分量按整数值比较。
- 动态分量允许等价表达式视为同一公开语义，例如 `8*N` 与 `N*8`。
- `get_shape()` 与 `get_stride()` 仍保留各自当前公开序列化文本，不强制把等价表达式改写成同一字符串。
- 只有其他 spec 显式声明要做结构级比较时，调用方才可要求内部表达式完全一致。

### 文本表示

- `repr(memory)` 返回 `Memory(<space>,Tensor(shape=..., dtype=..., stride=..., format=...))`
- `str(memory)` 复用 `repr(memory)`

## 运算合同

### 逐元素算术

适用方法：

- `__add__` / `__radd__`
- `__sub__` / `__rsub__`
- `__mul__` / `__rmul__`
- `__truediv__` / `__rtruediv__`
- `__floordiv__` / `__rfloordiv__`

规则：

- 支持 `Memory op Memory` 和 `Memory op int/bool`。
- `bool` 按 `int` 处理。
- `Memory op Memory` 要求 `shape` 语义等价。
- 结果继承 `shape`、`stride`、`space`、`format`。
- 结果 `dtype` 按 [`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py) 中 `ARITHMETIC_DTYPE_RANK` 的顺序提升。
- 不支持的标量类型抛 `TypeError("Unsupported scalar type for Memory operation")`。

### 逐元素比较

适用方法：

- `__eq__`
- `__lt__`
- `__gt__`

规则：

- 支持 `Memory op Memory` 和 `Memory op int/bool`。
- `Memory op Memory` 既要求 `shape` 语义等价，也要求 `dtype` 完全一致。
- 比较结果的 `dtype` 固定为 `NumericType.Bool`。

## 测试分层

- [`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)：构造、元信息读取、默认步幅、文本表示、`Memory.clone(...)` 的 dtype/space 覆写与元数据独立性。
- [`test/symbol_variable/test_memory_operation.py`](../../test/symbol_variable/test_memory_operation.py)：逐元素算术、比较、异常路径，以及经公开路径触发的 clone 保真行为。
- [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)：与 symbol dialect 的相邻边界。
