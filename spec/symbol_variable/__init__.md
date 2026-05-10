# __init__.md

## 功能简介

用于定义 `kernel_gen.symbol_variable` 包入口的稳定导出集合。本文只回答三件事：包入口暴露哪些名字、这些名字与子模块对象是否同一、哪些路径明确不再支持。

## API 列表

- `kernel_gen.symbol_variable: ModuleType`
- `class SymbolDim(value: int | str | Expr | Symbol)`
- `class SymbolList(shapes: list[int | str | SymbolDim])`
- `class SymbolShape(shapes: list[int | str | SymbolDim])`
- `class LocalSpaceMeta(name: str, max_size: int | None, align: int)`
- `class Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`
- `Memory.get_shape(self) -> list[SymbolDim]`
- `Memory.get_stride(self) -> list[int | SymbolDim] | None`
- `Memory.get_type(self) -> NumericType`
- `Memory.get_space(self) -> MemorySpace`
- `Memory.get_format(self) -> Farmat`
- `Memory.clone(self, dtype: NumericType | None = None, space: MemorySpace | None = None) -> Memory`
- `class MemorySpace(Enum)`
- `class NumericType(Enum)`
- `class Farmat(Enum)`
- `kernel_gen.symbol_variable.type.FLOAT_DTYPES: set[NumericType]`
- `kernel_gen.symbol_variable.type.INT_DTYPES: set[NumericType]`
- `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_ORDER: tuple[NumericType, ...]`
- `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_RANK: dict[NumericType, int]`
- `kernel_gen.symbol_variable.type.NN_FLOAT_DTYPES: set[NumericType]`
- `kernel_gen.symbol_variable.type.is_integer_dtype(dtype: NumericType) -> bool`
- `kernel_gen.symbol_variable.type.is_float_dtype(dtype: NumericType) -> bool`
- `class kernel_gen.symbol_variable.ptr.Ptr(dtype: Attribute)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/__init__.md`](../../spec/symbol_variable/__init__.md)
- `test`：[`test/symbol_variable/test_package.py`](../../test/symbol_variable/test_package.py)
- `功能实现`：[`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py)

## 依赖

- 无额外 spec 依赖。

## API详细说明

### `kernel_gen.symbol_variable: ModuleType`

- api：`kernel_gen.symbol_variable: ModuleType`
- 参数：无。
- 返回值：当前 package 根导出的公开对象集合；只包含 API 列表中声明的名称。
- 使用示例：

  ```python
  import kernel_gen.symbol_variable as symbol_variable

  memory_cls = symbol_variable.Memory
  ```
- 功能说明：公开 `kernel_gen.symbol_variable` 包根导入路径。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class SymbolDim(value: int | str | Expr | Symbol)`

- api：`class SymbolDim(value: int | str | Expr | Symbol)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `int | str | Expr | Symbol`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`SymbolDim` 实例。
- 使用示例：

  ```python
  symbol_dim = SymbolDim(value=value)
  ```
- 功能说明：构造 `SymbolDim` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolList(shapes: list[int | str | SymbolDim])`

- api：`class SymbolList(shapes: list[int | str | SymbolDim])`
- 参数：
  - `shapes`：形状序列集合，定义多个张量、内存或符号对象的维度大小；类型 `list[int | str | SymbolDim]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
- 返回值：`SymbolList` 实例。
- 使用示例：

  ```python
  symbol_list = SymbolList(shapes=shapes)
  ```
- 功能说明：构造 `SymbolList` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolShape(shapes: list[int | str | SymbolDim])`

- api：`class SymbolShape(shapes: list[int | str | SymbolDim])`
- 参数：
  - `shapes`：形状序列集合，定义多个张量、内存或符号对象的维度大小；类型 `list[int | str | SymbolDim]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
- 返回值：`SymbolShape` 实例。
- 使用示例：

  ```python
  symbol_shape = SymbolShape(shapes=shapes)
  ```
- 功能说明：构造 `SymbolShape` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class LocalSpaceMeta(name: str, max_size: int | None, align: int)`

- api：`class LocalSpaceMeta(name: str, max_size: int | None, align: int)`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `max_size`：本地空间容量上限，`None` 表示不声明固定上限；类型 `int | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `align`：对齐粒度，用于内存、缓冲区或地址计算的对齐约束；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`LocalSpaceMeta` 实例。
- 使用示例：

  ```python
  local_space_meta = LocalSpaceMeta(name=name, max_size=max_size, align=align)
  ```
- 功能说明：定义 `LocalSpaceMeta` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`

- api：`class Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`
- 参数：
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `ShapeLike`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `NumericType | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `MemorySpace`；默认值 `MemorySpace.GM`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `ShapeLike | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `format`：内存格式或输出格式，定义当前对象的布局或文本输出形式；类型 `Farmat`；默认值 `Farmat.Norm`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory` 实例。
- 使用示例：

  ```python
  memory = Memory(shape=shape, dtype=None, space=space, stride=None, format=format)
  ```
- 功能说明：定义 `Memory` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Memory.get_shape(self) -> list[SymbolDim]`

- api：`Memory.get_shape(self) -> list[SymbolDim]`
- 参数：无。
- 返回值：`list[SymbolDim]`。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable import Memory, SymbolDim

  memory = Memory(["M", 32])
  m_dim, n_dim = memory.get_shape()
  assert m_dim == SymbolDim("M")
  assert n_dim == SymbolDim(32)
  ```
- 功能说明：从包根导出的 `Memory` 读取 `shape`，返回值可用于解包和索引。
- 注意事项：包根不额外提供 `get_shape(dim)` 或 `getshape(dim)`；形状单轴读取通过 `memory.get_shape()[axis]` 完成。

### `Memory.get_stride(self) -> list[int | SymbolDim] | None`

- api：`Memory.get_stride(self) -> list[int | SymbolDim] | None`
- 参数：无。
- 返回值：`list[int | SymbolDim] | None`。
- 使用示例：

  ```python
  memory = memory
  result = memory.get_stride()
  ```
- 功能说明：读取 `stride`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `Memory.get_type(self) -> NumericType`

- api：`Memory.get_type(self) -> NumericType`
- 参数：无。
- 返回值：`NumericType`。
- 使用示例：

  ```python
  memory = memory
  result = memory.get_type()
  ```
- 功能说明：读取 `type`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `Memory.get_space(self) -> MemorySpace`

- api：`Memory.get_space(self) -> MemorySpace`
- 参数：无。
- 返回值：`MemorySpace`。
- 使用示例：

  ```python
  memory = memory
  result = memory.get_space()
  ```
- 功能说明：读取 `space`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `Memory.get_format(self) -> Farmat`

- api：`Memory.get_format(self) -> Farmat`
- 参数：无。
- 返回值：`Farmat`。
- 使用示例：

  ```python
  memory = memory
  result = memory.get_format()
  ```
- 功能说明：读取 `format`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `Memory.clone(self, dtype: NumericType | None = None, space: MemorySpace | None = None) -> Memory`

- api：`Memory.clone(self, dtype: NumericType | None = None, space: MemorySpace | None = None) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `NumericType | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `MemorySpace | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.clone(dtype=None, space=None)
  ```
- 功能说明：复制 `clone`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class MemorySpace(Enum)`

- api：`class MemorySpace(Enum)`
- 参数：无。
- 返回值：`MemorySpace` 枚举类型对象。
- 使用示例：

  ```python
  memory_space = MemorySpace()
  ```
- 功能说明：定义 `MemorySpace` 公开枚举类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class NumericType(Enum)`

- api：`class NumericType(Enum)`
- 参数：无。
- 返回值：`NumericType` 枚举类型对象。
- 使用示例：

  ```python
  numeric_type = NumericType()
  ```
- 功能说明：定义 `NumericType` 公开枚举类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class Farmat(Enum)`

- api：`class Farmat(Enum)`
- 参数：无。
- 返回值：`Farmat` 枚举类型对象。
- 使用示例：

  ```python
  farmat = Farmat()
  ```
- 功能说明：定义 `Farmat` 公开枚举类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `kernel_gen.symbol_variable.type.FLOAT_DTYPES: set[NumericType]`

- api：`kernel_gen.symbol_variable.type.FLOAT_DTYPES: set[NumericType]`
- 参数：无。
- 返回值：`set[NumericType]`。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.type import FLOAT_DTYPES, NumericType

  assert NumericType.Float32 in FLOAT_DTYPES
  ```
- 功能说明：公开 `kernel_gen.symbol_variable.type.FLOAT_DTYPES` 包根导入路径。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `kernel_gen.symbol_variable.type.INT_DTYPES: set[NumericType]`

- api：`kernel_gen.symbol_variable.type.INT_DTYPES: set[NumericType]`
- 参数：无。
- 返回值：`set[NumericType]`。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.type import INT_DTYPES, NumericType

  assert NumericType.Int32 in INT_DTYPES
  ```
- 功能说明：公开 `kernel_gen.symbol_variable.type.INT_DTYPES` 包根导入路径。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_ORDER: tuple[NumericType, ...]`

- api：`kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_ORDER: tuple[NumericType, ...]`
- 参数：无。
- 返回值：`tuple[NumericType, ...]`。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_ORDER

  assert ARITHMETIC_DTYPE_ORDER[0].name == "Int8"
  ```
- 功能说明：公开 `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_ORDER` 包根导入路径。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_RANK: dict[NumericType, int]`

- api：`kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_RANK: dict[NumericType, int]`
- 参数：无。
- 返回值：`dict[NumericType, int]`。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_RANK, NumericType

  assert ARITHMETIC_DTYPE_RANK[NumericType.Float32] > ARITHMETIC_DTYPE_RANK[NumericType.Int32]
  ```
- 功能说明：公开 `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_RANK` 包根导入路径。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `kernel_gen.symbol_variable.type.NN_FLOAT_DTYPES: set[NumericType]`

- api：`kernel_gen.symbol_variable.type.NN_FLOAT_DTYPES: set[NumericType]`
- 参数：无。
- 返回值：`set[NumericType]`。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.type import NN_FLOAT_DTYPES, NumericType

  assert NumericType.Float32 in NN_FLOAT_DTYPES
  ```
- 功能说明：公开 `kernel_gen.symbol_variable.type.NN_FLOAT_DTYPES` 包根导入路径。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `kernel_gen.symbol_variable.type.is_integer_dtype(dtype: NumericType) -> bool`

- api：`kernel_gen.symbol_variable.type.is_integer_dtype(dtype: NumericType) -> bool`
- 参数：
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `NumericType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  type = type
  result = type.is_integer_dtype(dtype=dtype)
  ```
- 功能说明：执行 `is_integer_dtype`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `kernel_gen.symbol_variable.type.is_float_dtype(dtype: NumericType) -> bool`

- api：`kernel_gen.symbol_variable.type.is_float_dtype(dtype: NumericType) -> bool`
- 参数：
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `NumericType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  type = type
  result = type.is_float_dtype(dtype=dtype)
  ```
- 功能说明：执行 `is_float_dtype`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `class kernel_gen.symbol_variable.ptr.Ptr(dtype: Attribute)`

- api：`class kernel_gen.symbol_variable.ptr.Ptr(dtype: Attribute)`
- 参数：
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Ptr` 实例。
- 使用示例：

  ```python
  ptr = ptr
  result = ptr.Ptr(dtype=dtype)
  ```
- 功能说明：构造 `Ptr` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。


## 额外补充

### 关联模块

| 模块 | 公开对象 |
|---|---|
| [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py) | `SymbolDim` |
| [`kernel_gen/symbol_variable/symbol_shape.py`](../../kernel_gen/symbol_variable/symbol_shape.py) | `SymbolList`、`SymbolShape` |
| [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py) | `LocalSpaceMeta`、`Memory`、`MemorySpace` |
| [`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py) | `NumericType`、`Farmat`；`FLOAT_DTYPES`、`INT_DTYPES`、`ARITHMETIC_DTYPE_ORDER`、`ARITHMETIC_DTYPE_RANK`、`NN_FLOAT_DTYPES`、`is_integer_dtype`、`is_float_dtype` 仅子模块入口 |
| [`kernel_gen/symbol_variable/ptr.py`](../../kernel_gen/symbol_variable/ptr.py) | `Ptr`，只保留子模块入口 |

### 包入口合同

### 稳定导出集合

包入口只导出以下名称：

- `Farmat`
- `LocalSpaceMeta`
- `Memory`
- `MemorySpace`
- `NumericType`
- `SymbolDim`
- `SymbolList`
- `SymbolShape`

- 使用示例：

```python
from kernel_gen.symbol_variable import Memory, NumericType, SymbolDim

mem = Memory([SymbolDim("N"), 32], NumericType.Float32)
```

约束：

- `from kernel_gen.symbol_variable import Name` 只承诺上面这组名称可稳定导入。
- `from kernel_gen.symbol_variable import *` 只能暴露上面的集合。
- 包入口不额外暴露 `Ptr`、实现细节或旧兼容名字。
- `kernel_gen.symbol_variable.type.FLOAT_DTYPES`、`kernel_gen.symbol_variable.type.INT_DTYPES`、`kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_ORDER`、`kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_RANK`、`kernel_gen.symbol_variable.type.NN_FLOAT_DTYPES`、`kernel_gen.symbol_variable.type.is_integer_dtype` 与 `kernel_gen.symbol_variable.type.is_float_dtype` 若存在，也只允许通过子模块入口导入；包入口不重导出这些 dtype family / promotion 入口。

### 对象同一性

包入口重导出的对象必须与各自子模块中的对象保持同一性，不允许包层再包装一层。

- 使用示例：

```python
from kernel_gen.symbol_variable import Memory as PackageMemory
from kernel_gen.symbol_variable.memory import Memory as ModuleMemory

assert PackageMemory is ModuleMemory
```

### 仅子模块入口

`Ptr` 继续作为子模块 API 存在，但不进入包入口导出集合。`FLOAT_DTYPES`、`INT_DTYPES`、`ARITHMETIC_DTYPE_ORDER`、`ARITHMETIC_DTYPE_RANK`、`NN_FLOAT_DTYPES`、`is_integer_dtype` 与 `is_float_dtype` 也属于同类“仅子模块入口”的公开接口。

- 使用示例：

```python
from kernel_gen.symbol_variable.ptr import Ptr
from kernel_gen.symbol_variable.type import ARITHMETIC_DTYPE_ORDER, FLOAT_DTYPES, INT_DTYPES, is_float_dtype, is_integer_dtype
```

### 旧路径禁用

以下导入路径不是公开入口：

- `symbol_variable`
- `symbol_variable.symbol_dim`
- `symbol_variable.symbol_shape`
- `symbol_variable.memory`
- `symbol_variable.type`

- 使用示例：

```python
import kernel_gen.symbol_variable as symbol_variable

assert symbol_variable.Memory is not None
```

约束：

- 旧路径导入必须失败。
- 包入口唯一有效前缀是 `kernel_gen.symbol_variable`。

#

## 测试

- 测试文件：`test/symbol_variable/test_package.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/symbol_variable/test_package.py`

### 测试目标

- 验证本文件 `API 列表` 中公开 API 的稳定行为、边界和错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SYMBOL-VARIABLE-001 | 公开入口 | python symbol variable imports | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_python_symbol_variable_imports`。 | 公开入口在“python symbol variable imports”场景下可导入、构造、注册或按名称发现。 | `test_python_symbol_variable_imports` |
| TC-SYMBOL-VARIABLE-002 | 公开入口 | legacy import disabled | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_legacy_import_disabled`。 | 公开入口在“legacy import disabled”场景下可导入、构造、注册或按名称发现。 | `test_legacy_import_disabled` |
| TC-SYMBOL-VARIABLE-003 | 公开入口 | legacy submodule import disabled | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_legacy_submodule_import_disabled`。 | 公开入口在“legacy submodule import disabled”场景下可导入、构造、注册或按名称发现。 | `test_legacy_submodule_import_disabled` |
| TC-SYMBOL-VARIABLE-004 | 公开入口 | python package type exports | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_python_package_type_exports`。 | 公开入口在“python package type exports”场景下可导入、构造、注册或按名称发现。 | `test_python_package_type_exports` |
| TC-SYMBOL-VARIABLE-005 | 公开入口 | package type construct memory | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_package_type_construct_memory`。 | 公开入口在“package type construct memory”场景下可导入、构造、注册或按名称发现。 | `test_package_type_construct_memory` |
| TC-SYMBOL-VARIABLE-006 | 公开入口 | python package exports match public contract | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_python_package_exports_match_public_contract`。 | 公开入口在“python package exports match public contract”场景下可导入、构造、注册或按名称发现。 | `test_python_package_exports_match_public_contract` |
| TC-SYMBOL-VARIABLE-007 | 公开入口 | python package import star exports only public names | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_python_package_import_star_exports_only_public_names`。 | 公开入口在“python package import star exports only public names”场景下可导入、构造、注册或按名称发现。 | `test_python_package_import_star_exports_only_public_names` |
