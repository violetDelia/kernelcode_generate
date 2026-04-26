# symbol_shape.md

## 功能简介

用于定义 `SymbolShape` / `SymbolList` 的容器合同。本文只收三件事：输入如何规整为 `SymbolDim`，列表访问与赋值如何工作，公开序列化输出什么。

## API 列表

- `class SymbolList(shapes: Iterable[object])`
  - `__repr__() -> str`
  - `__len__() -> int`
  - `__iter__() -> Iterator[SymbolDim]`
  - `__reversed__() -> Iterator[SymbolDim]`
  - `__getitem__(key: int | slice) -> SymbolDim | list[SymbolDim]`
  - `__setitem__(key: int | slice, value: object) -> None`
  - `get_shape() -> list[SymbolDim]`
  - `get_values() -> list[int | str]`
  - `to_symbols() -> list[int | str]`
- `class SymbolShape(shapes: Iterable[object])`
  - `__repr__() -> str`

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)
- `test`：[`test/symbol_variable/test_symbol_shape.py`](../../test/symbol_variable/test_symbol_shape.py)
- `功能实现`：[`kernel_gen/symbol_variable/symbol_shape.py`](../../kernel_gen/symbol_variable/symbol_shape.py)

## 依赖

- [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)：单个分量的构造与公开值规则。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：`SymbolDim` 语义来源。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`shape/stride` 进入 `Memory` 后的消费规则。

## 限制与边界

- 只负责容器化保存、访问、切片赋值和序列化，不负责广播、推导或约束求解。
- 对外唯一的规整入口是 `SymbolShape(shapes)`。
- 内部元素始终是 `SymbolDim`。
- `__getitem__` 只支持 `int` / `slice`。
- `__setitem__` 的 `slice` 赋值必须接收可迭代对象，并逐项规整为 `SymbolDim`。
- 索引越界统一抛 `IndexError("下标超出范围")`。
- `slice` 赋值异常边界复用 `SymbolDim(...)`：
  - 不可转换对象收敛为 `TypeError("切片赋值元素无法转换为 SymbolDim")`
  - 浮点输入保持 `NotImplementedError`

## 公开接口

### `class SymbolList(shapes: Iterable[object])`

功能：

- 把可迭代输入规整为 `SymbolDim` 列表。
- 对外提供列表访问、切片赋值与公开序列化能力。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_shape import SymbolList

symbol_list = SymbolList(["N", 32, "64"])
```

返回：

- `SymbolList`

#### `__repr__() -> str`

功能：

- 返回 `List(d0, d1, ...)` 形式的公开文本。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_shape import SymbolList

assert repr(SymbolList([1, 2])) == "List(1, 2)"
```

#### `__len__() -> int`

功能：

- 提供标准列表长度能力。

使用示例：

```python
symbol_list = SymbolList([1, 2, 3])
assert len(symbol_list) == 3
```

#### `__iter__() -> Iterator[SymbolDim]`

功能：

- 提供正向迭代能力。

使用示例：

```python
symbol_list = SymbolList([1, 2, 3])
assert [dim.get_value() for dim in symbol_list] == [1, 2, 3]
```

#### `__reversed__() -> Iterator[SymbolDim]`

功能：

- 提供反向迭代能力。

使用示例：

```python
symbol_list = SymbolList([1, 2, 3])
assert [dim.get_value() for dim in reversed(symbol_list)] == [3, 2, 1]
```

#### `__getitem__(key: int | slice) -> SymbolDim | list[SymbolDim]`

功能：

- `int` 索引读取单个 `SymbolDim`
- `slice` 读取返回 `list[SymbolDim]`

使用示例：

```python
symbol_list = SymbolList([1, "N", 32])
first = symbol_list[0]
part = symbol_list[1:3]
```

约束：

- `key` 非 `int` / `slice` 抛 `TypeError`

#### `__setitem__(key: int | slice, value: object) -> None`

功能：

- `int` / `slice` 赋值都会先规整为 `SymbolDim`

使用示例：

```python
symbol_list = SymbolList([1, "N", 32])
symbol_list[0] = 64
symbol_list[1:3] = ["M", 128]
```

约束：

- `key` 非 `int` / `slice` 抛 `TypeError`
- `slice` 赋值传入非可迭代对象抛 `TypeError`

#### `get_shape() -> list[SymbolDim]`

功能：

- 返回内部 `SymbolDim` 列表的拷贝。

使用示例：

```python
symbol_list = SymbolList([1, "N"])
copied = symbol_list.get_shape()
```

约束：

- 外部修改返回值不影响内部状态。

#### `get_values() -> list[int | str]`

功能：

- 把内部维度序列化为 `list[int | str]`。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_shape import SymbolList

assert SymbolList(["N", 32]).get_values() == ["N", 32]
```

约束：

- 静态维度输出 `int`
- 动态维度输出 `SymbolDim.get_value()` 对应的公开文本

#### `to_symbols() -> list[int | str]`

功能：

- 复用 `get_values()` 的序列化规则。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_shape import SymbolList

assert SymbolList(["N", "32"]).to_symbols() == ["N", 32]
```

约束：

- 静态维度输出 `int`
- 动态维度输出 `SymbolDim.get_value()` 对应的公开文本

### `class SymbolShape(shapes: Iterable[object])`

功能：

- 作为具体 shape 容器对外使用。
- 继承 `SymbolList` 的构造、索引、迭代和序列化能力。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_shape import SymbolShape

shape = SymbolShape(["N", 32, 64])
cloned = SymbolShape(shape)
```

返回：

- `SymbolShape`

#### `__repr__() -> str`

功能：

- 返回 `Shape(d0, d1, ...)` 形式的公开文本。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_shape import SymbolShape

assert repr(SymbolShape([1, 2])) == "Shape(1, 2)"
```

## 测试分层

| 目标 | 用例 |
|---|---|
| 构造与规整 | [`test_init_accepts_symbol_dim_and_int`](../../test/symbol_variable/test_symbol_shape.py)、[`test_construct_from_existing_shape`](../../test/symbol_variable/test_symbol_shape.py) |
| 公开序列化 | [`test_get_values`](../../test/symbol_variable/test_symbol_shape.py)、[`test_get_values_keeps_public_floordiv_text`](../../test/symbol_variable/test_symbol_shape.py)、[`test_to_symbols`](../../test/symbol_variable/test_symbol_shape.py) |
| 访问与赋值 | [`test_getitem_slice`](../../test/symbol_variable/test_symbol_shape.py)、[`test_setitem_converts`](../../test/symbol_variable/test_symbol_shape.py)、[`test_setitem_slice_converts`](../../test/symbol_variable/test_symbol_shape.py) |
| 异常边界 | [`test_getitem_out_of_range`](../../test/symbol_variable/test_symbol_shape.py)、[`test_invalid_index_type`](../../test/symbol_variable/test_symbol_shape.py)、[`test_slice_assign_non_iterable`](../../test/symbol_variable/test_symbol_shape.py)、[`test_slice_assign_invalid_item`](../../test/symbol_variable/test_symbol_shape.py)、[`test_slice_assign_float_item_reuses_symbol_dim_error`](../../test/symbol_variable/test_symbol_shape.py) |
| 容器行为 | [`test_get_shape_copy`](../../test/symbol_variable/test_symbol_shape.py)、[`test_iteration`](../../test/symbol_variable/test_symbol_shape.py)、[`test_repr`](../../test/symbol_variable/test_symbol_shape.py)、[`test_list_repr`](../../test/symbol_variable/test_symbol_shape.py) |
