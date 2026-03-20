# symbol_shape.md

## 功能简介

用于描述静态或动态的形状信息，提供统一的形状输入归一化入口与列表式访问行为。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)
- `test`：[`test/symbol_variable/test_symbol_shape.py`](../../test/symbol_variable/test_symbol_shape.py)
- `功能实现`：[`python/symbol_variable/symbol_shape.py`](../../python/symbol_variable/symbol_shape.py)

## 依赖

- `python/symbol_variable/symbol_dim.py`：[`SymbolDim`](../../python/symbol_variable/symbol_dim.py) 的定义与校验规则来源。
- `spec/symbol_variable/symbol_dim.md`：[`SymbolDim`](../../spec/symbol_variable/symbol_dim.md) 语义约束。

## 限制与边界

- 仅负责形状容器的保存、访问与序列化，不负责广播、约束求解或形状推导。
- `SymbolShape(shapes)` 是对外唯一的形状输入归一化入口。
- 容器不变量：内部存储的元素必须为 `SymbolDim`。
- 输入元素通过 `SymbolDim(...)` 统一包装，支持 `SymbolDim`、`int` 及 `SymbolDim` 可接受的输入类型。
- `__getitem__` 支持 `int` 与 `slice`；`__setitem__` 对 `slice` 赋值需逐项规范化。
- `int` 索引越界统一抛 `IndexError("下标超出范围")`。
- `slice` 赋值若传入不可迭代对象或包含无法转换的元素，抛 `TypeError`。
- 若实现需要复用输入规整逻辑，应使用 `_normalize_*` 私有命名。

## 公开接口

### SymbolShape

功能说明：

- 具体形状类型，继承 `SymbolList`，提供列表式访问与序列化能力。
- 公开创建方式为 `SymbolShape(shapes)`。

#### __init__(shapes)

参数说明：

- `shapes`：可迭代对象，元素为 `SymbolDim` 或可被 `SymbolDim(...)` 接收的值。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

shape = SymbolShape(["N", 32, 64])
```

注意事项：

- 传入元素会按 `SymbolDim(...)` 规则规范化并保存。
- `SymbolShape(existing_shape)` 允许以已有 `SymbolShape` 构造等价新对象。

返回与限制：

- 返回 `SymbolShape` 实例。
- 规范化失败时向上抛出 `SymbolDim` 对应异常。

#### __repr__()

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

assert repr(SymbolShape([1, 2])) == "Shape(1, 2)"
```

注意事项：

- 返回值为稳定字符串格式 `Shape(d0, d1, ...)`。

返回与限制：

- 返回 `str`。

#### get_shape()

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

shape = SymbolShape([1, 2])
copy_list = shape.get_shape()
```

注意事项：

- 返回浅拷贝，外部修改不影响内部列表。

返回与限制：

- 返回 `List[SymbolDim]`。

#### get_values()

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

values = SymbolShape(["N", 32]).get_values()
```

注意事项：

- 动态维度返回 `str(dim.get_symbol())`，静态维度返回 `int(dim.get_symbol())`。

返回与限制：

- 返回 `List[int | str]`。

#### __len__()

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

assert len(SymbolShape([1, 2, 3])) == 3
```

注意事项：

- 以维度数量为长度。

返回与限制：

- 返回 `int`。

#### __iter__()

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

for dim in SymbolShape([1, 2]):
    _ = dim
```

注意事项：

- 迭代返回 `SymbolDim` 元素。

返回与限制：

- 返回迭代器。

#### __reversed__()

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

for dim in reversed(SymbolShape([1, 2])):
    _ = dim
```

注意事项：

- 反向迭代 `SymbolDim` 元素。

返回与限制：

- 返回迭代器。

#### __getitem__(key)

参数说明：

- `key`：`int` 或 `slice`。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

shape = SymbolShape([1, "N", 3])
_ = shape[0]
_ = shape[0:2]
```

注意事项：

- `int` 索引越界抛 `IndexError("下标超出范围")`。
- `slice` 返回 `List[SymbolDim]`。

返回与限制：

- `int` 索引返回 `SymbolDim`，`slice` 返回 `List[SymbolDim]`。
- `key` 非 `int`/`slice` 抛 `TypeError`。

#### __setitem__(key, value)

参数说明：

- `key`：`int` 或 `slice`。
- `value`：`int`/`SymbolDim`/可迭代对象（当 `key` 为 `slice`）。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

shape = SymbolShape([1, "N", 32])
shape[0] = 64
shape[1:3] = ["M", 128]
```

注意事项：

- `int` 索引赋值通过 `SymbolDim(value)` 规范化。
- `slice` 赋值要求可迭代并逐项规范化。

返回与限制：

- 无返回值。
- `int` 索引越界抛 `IndexError("下标超出范围")`。
- `slice` 赋值若传入不可迭代对象或存在非法元素，抛 `TypeError`。
- `key` 非 `int`/`slice` 抛 `TypeError`。

### SymbolList

功能说明：

- 对外公开的形状列表类型，提供列表行为与序列化能力。
- `SymbolList` 为基类，`SymbolShape` 继承 `SymbolList`。

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolList

symbols = SymbolList(["N", 32])
```

注意事项：

- `SymbolList` 的序列化能力由 `to_symbols()` 提供。

返回与限制：

- 返回 `SymbolList` 实例。

#### to_symbols()

功能说明：

- 将形状序列化为 `int`/`str` 列表。

参数说明：

- 无参数。

使用示例：

```python
from python.symbol_variable.symbol_shape import SymbolShape

symbols = SymbolShape(["N", 32]).to_symbols()
```

注意事项：

- 返回规则与 `get_values()` 一致。

返回与限制：

- 返回 `List[int | str]`。

## 测试

- 测试文件：[`test/symbol_variable/test_symbol_shape.py`](../../test/symbol_variable/test_symbol_shape.py)
- 执行命令：`pytest -q test/symbol_variable/test_symbol_shape.py`

### 测试目标

- 构造：支持 `SymbolDim`、`int` 及 `SymbolDim` 可接受的输入。
- 验证公开输入归一化入口为 `SymbolShape(shapes)`。
- 列表行为：`len`、迭代、反向迭代、`repr`。
- 索引访问：`int` 索引越界错误信息一致。
- 赋值：`int` 索引赋值会转换为 `SymbolDim`；`slice` 赋值会逐项转换为 `SymbolDim`。
- `slice` 赋值不可迭代对象触发 `TypeError`。
- `slice` 赋值存在元素无法转换触发 `TypeError`。
- `get_shape()` 返回拷贝，外部修改不影响内部。
- 序列化：动态维度输出 `str`，静态维度输出 `int`。
- `SymbolShape(existing_shape)` 可构造等价的新形状对象。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 对应测试 |
|---|---|---|---|---|---|---|
| SS-001 | 构造 | SymbolDim/int | N/A | `SymbolShape([SymbolDim("N"), 32])` | 构造成功 | `test_init_accepts_symbol_dim_and_int` |
| SS-002 | 序列化 | 动态/静态 | N/A | `get_values()` | 动态为 str，静态为 int | `test_get_values` |
| SS-003 | 访问 | 越界 | N/A | `shape[99]` | 抛 `IndexError("下标超出范围")` | `test_getitem_out_of_range` |
| SS-004 | 访问 | slice 索引 | N/A | `shape[0:1]` | 返回 `List[SymbolDim]` | `test_getitem_slice` |
| SS-005 | 赋值 | slice 索引 | N/A | `shape[0:2] = [1, "N"]` | 逐项转为 `SymbolDim` | `test_setitem_slice_converts` |
| SS-006 | 访问 | get_shape 拷贝 | N/A | `get_shape()` | 修改返回值不影响内部 | `test_get_shape_copy` |
| SS-007 | 异常 | 非法索引类型 | N/A | `shape["x"]` | 抛 `TypeError` | `test_invalid_index_type` |
| SS-008 | 异常 | slice 不可迭代 | N/A | `shape[0:1] = 1` | 抛 `TypeError`（不可迭代对象） | `test_slice_assign_non_iterable` |
| SS-009 | 异常 | slice 元素非法 | N/A | `shape[0:1] = [object()]` | 抛 `TypeError`（元素类型不合法） | `test_slice_assign_invalid_item` |
| SS-010 | 赋值 | slice 元素为数字字符串 | N/A | `shape[0:1] = ["1"]` | 维度解析为静态数字 | `test_slice_assign_digit_string` |
| SS-012 | 赋值 | int 索引 | N/A | `shape[0] = 64` | 转为 `SymbolDim` | `test_setitem_converts` |
| SS-013 | 表现 | Shape repr | N/A | `repr(SymbolShape([1, 2]))` | 返回 `Shape(1, 2)` | `test_repr` |
| SS-014 | 表现 | List repr | N/A | `repr(SymbolList([1, 2]))` | 返回 `List(1, 2)` | `test_list_repr` |
| SS-015 | 构造 | 由已有 SymbolShape 创建 | N/A | `SymbolShape(SymbolShape([1, 2]))` | 构造等价的新对象 | `test_construct_from_existing_shape` |
| SS-016 | 迭代 | for-in 迭代 | N/A | `for dim in shape:` | 可遍历 `SymbolDim` | `test_iteration` |
