# memory.md

## 功能简介

定义 Python 侧内存元信息容器 `Memory`，以及它依赖的 `LocalSpaceMeta`、`MemorySpace`。本模块只描述 `shape`、`stride`、`dtype`、`format`、`space` 这些结构化属性，不负责真实分配、容量校验、调度、拷贝或 IR type 定义。

## API 列表

- `class LocalSpaceMeta(name: str, max_size: int | None, align: int)`
- `class MemorySpace(Enum)`
- `class Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`
- `Memory.get_shape(self) -> list[SymbolDim]`
- `Memory.get_stride(self) -> list[int | SymbolDim]`
- `Memory.get_type(self) -> NumericType`
- `Memory.get_space(self) -> MemorySpace`
- `Memory.get_format(self) -> Farmat`
- `Memory.clone(self, dtype: NumericType | None = None, space: MemorySpace | None = None) -> Memory`
- `Memory.__repr__(self) -> str`
- `Memory.__str__(self) -> str`
- `Memory.__add__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__radd__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__sub__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__rsub__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__mul__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__rmul__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__truediv__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__rtruediv__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__floordiv__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__rfloordiv__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__eq__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__lt__(self, other: MemoryBinaryOperand) -> Memory`
- `Memory.__gt__(self, other: MemoryBinaryOperand) -> Memory`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)、[`test/symbol_variable/test_memory_operation.py`](../../test/symbol_variable/test_memory_operation.py)、[`test/dialect/test_symbol.py`](../../test/dialect/test_symbol.py)
- `功能实现`：[`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)

## 依赖

- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)：`shape/stride` 容器语义。
- [`spec/symbol_variable/__init__.md`](../../spec/symbol_variable/__init__.md)：包级导出边界。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：`NumericType` 与 `Farmat` 语义。
- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：单个整型维度、步幅、偏移进入 IR 时的语义归属。
- [`spec/operation/nn.md`](../../spec/operation/nn.md)：逐元素算术和比较的来源语义。

## API详细说明

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
- 返回值：`list[SymbolDim]`；每个维度保持为公开 `SymbolDim` 对象，静态维度以 `SymbolDim(int)` 表达，动态维度以 `SymbolDim(str)` 或符号表达表达。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.memory import Memory
  from kernel_gen.symbol_variable.symbol_dim import SymbolDim

  memory = Memory(["M", 32])
  m_dim, n_dim = memory.get_shape()
  assert m_dim == SymbolDim("M")
  assert n_dim == SymbolDim(32)
  ```
- 功能说明：读取 `shape`，支持 Python 与 DSL 中的解包、索引和符号表达继续参与计算。
- 注意事项：不提供 `get_shape(dim)` 或 `getshape(dim)` 带参公开入口；调用方需要 int/str 文本时应显式对维度调用 `get_value()` 或 `str(...)`。

### `Memory.get_stride(self) -> list[int | SymbolDim]`

- api：`Memory.get_stride(self) -> list[int | SymbolDim]`
- 参数：无。
- 返回值：`list[int | SymbolDim]`。
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

### `Memory.__repr__(self) -> str`

- api：`Memory.__repr__(self) -> str`
- 参数：无。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  memory = memory
  result = memory.__repr__()
  ```
- 功能说明：返回调试表示文本。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__str__(self) -> str`

- api：`Memory.__str__(self) -> str`
- 参数：无。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  memory = memory
  result = memory.__str__()
  ```
- 功能说明：返回用户可读文本。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__add__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__add__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__add__(other=other)
  ```
- 功能说明：执行 `__add__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__radd__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__radd__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__radd__(other=other)
  ```
- 功能说明：执行 `__radd__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__sub__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__sub__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__sub__(other=other)
  ```
- 功能说明：执行 `__sub__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__rsub__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__rsub__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__rsub__(other=other)
  ```
- 功能说明：执行 `__rsub__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__mul__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__mul__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__mul__(other=other)
  ```
- 功能说明：执行 `__mul__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__rmul__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__rmul__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__rmul__(other=other)
  ```
- 功能说明：执行 `__rmul__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__truediv__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__truediv__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__truediv__(other=other)
  ```
- 功能说明：执行 `__truediv__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__rtruediv__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__rtruediv__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__rtruediv__(other=other)
  ```
- 功能说明：执行 `__rtruediv__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__floordiv__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__floordiv__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__floordiv__(other=other)
  ```
- 功能说明：执行 `__floordiv__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__rfloordiv__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__rfloordiv__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__rfloordiv__(other=other)
  ```
- 功能说明：执行 `__rfloordiv__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__eq__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__eq__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__eq__(other=other)
  ```
- 功能说明：执行 `__eq__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__lt__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__lt__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__lt__(other=other)
  ```
- 功能说明：执行 `__lt__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `Memory.__gt__(self, other: MemoryBinaryOperand) -> Memory`

- api：`Memory.__gt__(self, other: MemoryBinaryOperand) -> Memory`
- 参数：
  - `self`：当前实例；类型为当前类实例；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，除非该 API 明确说明会修改输入。
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `MemoryBinaryOperand`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory`。
- 使用示例：

  ```python
  memory = memory
  result = memory.__gt__(other=other)
  ```
- 功能说明：执行 `__gt__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。


## 额外补充

### API 注意事项补充

- 只定义 Python 侧 memory 元信息，不定义 memory type、dma result type 或其他 IR type。
- 不负责广播、约束求解、真实地址偏移推导、空间可用性判断和生命周期管理。
- `shape`、`stride` 的单个分量若进入 IR，统一复用 [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)。
- 本文件不重复定义 `SymbolDim` 算术规则，也不重复定义 `SymbolShape` 容器接口。
- 当前文件内允许存在 `_clone_with_dtype`、`_clone_shape_like` 等辅助函数，但它们只服务 `Memory.clone(...)` 与运算实现，不属于公开 API；其他模块与测试不得跨文件直连。

### 公开合同

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

assert [dim.get_value() for dim in cloned.get_shape()] == ["M", "N"]
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

- `get_shape()`：返回公开 `SymbolDim` 列表，静态分量为 `SymbolDim(int)`，动态分量为 `SymbolDim(str)` 或符号表达。
- `get_stride()`：返回 `stride` 列表，静态分量为 `int`，动态分量保留 `SymbolDim`。
- `get_type()`、`get_space()`、`get_format()`：直接返回记录的元信息。

### `shape/stride` 比较口径

- 默认按语义等价比较，不按底层表达式节点顺序比较。
- 静态分量按整数值比较。
- 动态分量允许等价表达式视为同一公开语义，例如 `8*N` 与 `N*8`。
- `get_shape()` 与 `get_stride()` 仍保留各自当前公开表达，不强制把等价表达式改写成同一字符串。
- 只有其他 spec 显式声明要做结构级比较时，调用方才可要求内部表达式完全一致。

### 文本表示

- `repr(memory)` 返回 `Memory(<space>,Tensor(shape=..., dtype=..., stride=..., format=...))`
- `str(memory)` 复用 `repr(memory)`

### 运算合同

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

#

## 测试

- 测试文件：
  - `test/dialect/test_symbol.py`
  - `test/symbol_variable/test_memory.py`
  - `test/symbol_variable/test_memory_operation.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/symbol_variable/test_memory.py`

### 测试目标

- 验证本文件 `API 列表` 中公开 API 的稳定行为、边界和错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SYMBOL-VARIABLE-MEMORY-001 | 解析/打印 | symbol expr attr round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-002 | 边界/异常 | symbol expr attr rejects empty expr | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_expr_attr_rejects_empty_expr`。 | “symbol expr attr rejects empty expr”场景按公开错误语义失败或被拒绝。 | `test_symbol_expr_attr_rejects_empty_expr` |
| TC-SYMBOL-VARIABLE-MEMORY-003 | 解析/打印 | symbol value type round trip for integer only semantics | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYMBOL-VARIABLE-MEMORY-004 | 解析/打印 | symbol iter type round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_iter_type_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_iter_type_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-005 | 符号语义 | symbol const op verify success | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_const_op_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol const op verify success”场景。 | `test_symbol_const_op_verify_success` |
| TC-SYMBOL-VARIABLE-MEMORY-006 | 解析/打印 | symbol const op round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_const_op_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_const_op_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-007 | 符号语义 | symbol binary arith fold constant operands | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_binary_arith_fold_constant_operands`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol binary arith fold constant operands”场景。 | `test_symbol_binary_arith_fold_constant_operands` |
| TC-SYMBOL-VARIABLE-MEMORY-008 | 边界/异常 | symbol binary arith fold rejects dynamic operands | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_binary_arith_fold_rejects_dynamic_operands`。 | “symbol binary arith fold rejects dynamic operands”场景按公开错误语义失败或被拒绝。 | `test_symbol_binary_arith_fold_rejects_dynamic_operands` |
| TC-SYMBOL-VARIABLE-MEMORY-009 | 边界/异常 | symbol const op rejects mismatched type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_const_op_rejects_mismatched_type`。 | “symbol const op rejects mismatched type”场景按公开错误语义失败或被拒绝。 | `test_symbol_const_op_rejects_mismatched_type` |
| TC-SYMBOL-VARIABLE-MEMORY-010 | 解析/打印 | memory scalar components round trip through symbol dialect | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_memory_scalar_components_round_trip_through_symbol_dialect`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_memory_scalar_components_round_trip_through_symbol_dialect` |
| TC-SYMBOL-VARIABLE-MEMORY-011 | 边界/异常 | symbol value type rejects unsupported legacy text forms | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_value_type_rejects_unsupported_legacy_text_forms`。 | “symbol value type rejects unsupported legacy text forms”场景按公开错误语义失败或被拒绝。 | `test_symbol_value_type_rejects_unsupported_legacy_text_forms` |
| TC-SYMBOL-VARIABLE-MEMORY-012 | 符号语义 | symbol value type equality depends on expr only | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_value_type_equality_depends_on_expr_only`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol value type equality depends on expr only”场景。 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYMBOL-VARIABLE-MEMORY-013 | 边界/异常 | symbol verifier rejects illegal expression characters | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_verifier_rejects_illegal_expression_characters`。 | “symbol verifier rejects illegal expression characters”场景按公开错误语义失败或被拒绝。 | `test_symbol_verifier_rejects_illegal_expression_characters` |
| TC-SYMBOL-VARIABLE-MEMORY-014 | 符号语义 | symbol arith ops verify success | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_arith_ops_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol arith ops verify success”场景。 | `test_symbol_arith_ops_verify_success` |
| TC-SYMBOL-VARIABLE-MEMORY-015 | 符号语义 | symbol dim arithmetic preserves operand precedence | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_dim_arithmetic_preserves_operand_precedence`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol dim arithmetic preserves operand precedence”场景。 | `test_symbol_dim_arithmetic_preserves_operand_precedence` |
| TC-SYMBOL-VARIABLE-MEMORY-016 | 解析/打印 | symbol arith ops round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_arith_ops_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_arith_ops_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-017 | 边界/异常 | symbol arith ops reject non symbol int types | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_reject_non_symbol_int_types`。 | “symbol arith ops reject non symbol int types”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_reject_non_symbol_int_types` |
| TC-SYMBOL-VARIABLE-MEMORY-018 | 边界/异常 | symbol arith ops reject malformed signatures | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_reject_malformed_signatures`。 | “symbol arith ops reject malformed signatures”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_reject_malformed_signatures` |
| TC-SYMBOL-VARIABLE-MEMORY-019 | 边界/异常 | symbol arith ops error messages include context | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_error_messages_include_context`。 | “symbol arith ops error messages include context”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_error_messages_include_context` |
| TC-SYMBOL-VARIABLE-MEMORY-020 | 符号语义 | symbol compare ops verify success | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_compare_ops_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol compare ops verify success”场景。 | `test_symbol_compare_ops_verify_success` |
| TC-SYMBOL-VARIABLE-MEMORY-021 | 解析/打印 | symbol compare ops round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_compare_ops_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_compare_ops_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-022 | 边界/异常 | symbol compare ops reject non symbol int operands | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_compare_ops_reject_non_symbol_int_operands`。 | “symbol compare ops reject non symbol int operands”场景按公开错误语义失败或被拒绝。 | `test_symbol_compare_ops_reject_non_symbol_int_operands` |
| TC-SYMBOL-VARIABLE-MEMORY-023 | 边界/异常 | symbol compare ops reject non i1 result | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_compare_ops_reject_non_i1_result`。 | “symbol compare ops reject non i1 result”场景按公开错误语义失败或被拒绝。 | `test_symbol_compare_ops_reject_non_i1_result` |
| TC-SYMBOL-VARIABLE-MEMORY-024 | 边界/异常 | symbol compare ops reject malformed signatures | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_compare_ops_reject_malformed_signatures`。 | “symbol compare ops reject malformed signatures”场景按公开错误语义失败或被拒绝。 | `test_symbol_compare_ops_reject_malformed_signatures` |
| TC-SYMBOL-VARIABLE-MEMORY-025 | 边界/异常 | symbol compare ops error messages include context | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_compare_ops_error_messages_include_context`。 | “symbol compare ops error messages include context”场景按公开错误语义失败或被拒绝。 | `test_symbol_compare_ops_error_messages_include_context` |
| TC-SYMBOL-VARIABLE-MEMORY-026 | 符号语义 | symbol to float verify success | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_to_float_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol to float verify success”场景。 | `test_symbol_to_float_verify_success` |
| TC-SYMBOL-VARIABLE-MEMORY-027 | 解析/打印 | symbol to float round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_to_float_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_to_float_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-028 | 边界/异常 | symbol to float rejects invalid types | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_to_float_rejects_invalid_types`。 | “symbol to float rejects invalid types”场景按公开错误语义失败或被拒绝。 | `test_symbol_to_float_rejects_invalid_types` |
| TC-SYMBOL-VARIABLE-MEMORY-029 | 解析/打印 | symbol cast round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_cast_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_cast_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-030 | 边界/异常 | symbol cast rejects invalid types | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_cast_rejects_invalid_types`。 | “symbol cast rejects invalid types”场景按公开错误语义失败或被拒绝。 | `test_symbol_cast_rejects_invalid_types` |
| TC-SYMBOL-VARIABLE-MEMORY-031 | 符号语义 | symbol to int verify success for integer variants | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_to_int_verify_success_for_integer_variants`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol to int verify success for integer variants”场景。 | `test_symbol_to_int_verify_success_for_integer_variants` |
| TC-SYMBOL-VARIABLE-MEMORY-032 | 解析/打印 | symbol to int round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_to_int_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_to_int_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-033 | 边界/异常 | symbol to int rejects invalid types | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_to_int_rejects_invalid_types`。 | “symbol to int rejects invalid types”场景按公开错误语义失败或被拒绝。 | `test_symbol_to_int_rejects_invalid_types` |
| TC-SYMBOL-VARIABLE-MEMORY-034 | 符号语义 | symbol ptr type verify success | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_ptr_type_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol ptr type verify success”场景。 | `test_symbol_ptr_type_verify_success` |
| TC-SYMBOL-VARIABLE-MEMORY-035 | 解析/打印 | symbol ptr type round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_ptr_type_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_ptr_type_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-036 | 边界/异常 | symbol ptr type rejects symbol value dtype | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_ptr_type_rejects_symbol_value_dtype`。 | “symbol ptr type rejects symbol value dtype”场景按公开错误语义失败或被拒绝。 | `test_symbol_ptr_type_rejects_symbol_value_dtype` |
| TC-SYMBOL-VARIABLE-MEMORY-037 | 边界/异常 | symbol ptr type rejects non type dtype | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_ptr_type_rejects_non_type_dtype`。 | “symbol ptr type rejects non type dtype”场景按公开错误语义失败或被拒绝。 | `test_symbol_ptr_type_rejects_non_type_dtype` |
| TC-SYMBOL-VARIABLE-MEMORY-038 | 内存/DMA | symbol get dim reads static dim from memory type | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_dim_reads_static_dim_from_memory_type`。 | 内存类型、布局、搬运结果或 verifier 行为体现“symbol get dim reads static dim from memory type”场景。 | `test_symbol_get_dim_reads_static_dim_from_memory_type` |
| TC-SYMBOL-VARIABLE-MEMORY-039 | 符号语义 | symbol get dim folds static dim to const attr | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_get_dim_folds_static_dim_to_const_attr`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol get dim folds static dim to const attr”场景。 | `test_symbol_get_dim_folds_static_dim_to_const_attr` |
| TC-SYMBOL-VARIABLE-MEMORY-040 | 内存/DMA | symbol get dim reads symbolic dim from memory type | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_dim_reads_symbolic_dim_from_memory_type`。 | 内存类型、布局、搬运结果或 verifier 行为体现“symbol get dim reads symbolic dim from memory type”场景。 | `test_symbol_get_dim_reads_symbolic_dim_from_memory_type` |
| TC-SYMBOL-VARIABLE-MEMORY-041 | 内存/DMA | symbol get stride reads static stride from memory type | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_stride_reads_static_stride_from_memory_type`。 | 内存类型、布局、搬运结果或 verifier 行为体现“symbol get stride reads static stride from memory type”场景。 | `test_symbol_get_stride_reads_static_stride_from_memory_type` |
| TC-SYMBOL-VARIABLE-MEMORY-042 | 内存/DMA | symbol get stride folds static stride to const attr | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_stride_folds_static_stride_to_const_attr`。 | 内存类型、布局、搬运结果或 verifier 行为体现“symbol get stride folds static stride to const attr”场景。 | `test_symbol_get_stride_folds_static_stride_to_const_attr` |
| TC-SYMBOL-VARIABLE-MEMORY-043 | 内存/DMA | symbol get stride reads symbolic stride from memory type | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_stride_reads_symbolic_stride_from_memory_type`。 | 内存类型、布局、搬运结果或 verifier 行为体现“symbol get stride reads symbolic stride from memory type”场景。 | `test_symbol_get_stride_reads_symbolic_stride_from_memory_type` |
| TC-SYMBOL-VARIABLE-MEMORY-044 | 边界/异常 | symbol get dim rejects invalid axis | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_get_dim_rejects_invalid_axis`。 | “symbol get dim rejects invalid axis”场景按公开错误语义失败或被拒绝。 | `test_symbol_get_dim_rejects_invalid_axis` |
| TC-SYMBOL-VARIABLE-MEMORY-045 | 边界/异常 | symbol get stride rejects invalid axis | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_get_stride_rejects_invalid_axis`。 | “symbol get stride rejects invalid axis”场景按公开错误语义失败或被拒绝。 | `test_symbol_get_stride_rejects_invalid_axis` |
| TC-SYMBOL-VARIABLE-MEMORY-046 | 边界/异常 | symbol get dim rejects non memory type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_get_dim_rejects_non_memory_type`。 | “symbol get dim rejects non memory type”场景按公开错误语义失败或被拒绝。 | `test_symbol_get_dim_rejects_non_memory_type` |
| TC-SYMBOL-VARIABLE-MEMORY-047 | 边界/异常 | symbol get stride rejects unknown entry | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_get_stride_rejects_unknown_entry`。 | “symbol get stride rejects unknown entry”场景按公开错误语义失败或被拒绝。 | `test_symbol_get_stride_rejects_unknown_entry` |
| TC-SYMBOL-VARIABLE-MEMORY-048 | 符号语义 | symbol for accepts symbol int bounds and iter arg | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_for_accepts_symbol_int_bounds_and_iter_arg`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“symbol for accepts symbol int bounds and iter arg”场景。 | `test_symbol_for_accepts_symbol_int_bounds_and_iter_arg` |
| TC-SYMBOL-VARIABLE-MEMORY-049 | 解析/打印 | symbol for round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_for_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_for_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-050 | 边界/异常 | symbol for rejects non symbol int operands | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_rejects_non_symbol_int_operands`。 | “symbol for rejects non symbol int operands”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_rejects_non_symbol_int_operands` |
| TC-SYMBOL-VARIABLE-MEMORY-051 | 边界/异常 | symbol for rejects zero step | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_rejects_zero_step`。 | “symbol for rejects zero step”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_rejects_zero_step` |
| TC-SYMBOL-VARIABLE-MEMORY-052 | 边界/异常 | symbol for rejects invalid region shape | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_rejects_invalid_region_shape`。 | “symbol for rejects invalid region shape”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_rejects_invalid_region_shape` |
| TC-SYMBOL-VARIABLE-MEMORY-053 | 边界/异常 | symbol for parse rejects malformed text | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_parse_rejects_malformed_text`。 | “symbol for parse rejects malformed text”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_parse_rejects_malformed_text` |
| TC-SYMBOL-VARIABLE-MEMORY-054 | 边界/异常 | symbol for error messages include context | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_error_messages_include_context`。 | “symbol for error messages include context”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_error_messages_include_context` |
| TC-SYMBOL-VARIABLE-MEMORY-055 | 解析/打印 | symbol for loop carried symbol int round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_for_loop_carried_symbol_int_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_for_loop_carried_symbol_int_round_trip` |
| TC-SYMBOL-VARIABLE-MEMORY-056 | 边界/异常 | symbol for rejects invalid loop carried symbol int | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_rejects_invalid_loop_carried_symbol_int`。 | “symbol for rejects invalid loop carried symbol int”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_rejects_invalid_loop_carried_symbol_int` |
| TC-SYMBOL-VARIABLE-MEMORY-057 | 公开入口 | default space | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_default_space`。 | 公开入口在“default space”场景下可导入、构造、注册或按名称发现。 | `test_default_space` |
| TC-SYMBOL-VARIABLE-MEMORY-058 | 公开入口 | custom space | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_custom_space`。 | 公开入口在“custom space”场景下可导入、构造、注册或按名称发现。 | `test_custom_space` |
| TC-SYMBOL-VARIABLE-MEMORY-059 | 公开入口 | tlm123 spaces and legacy tlm absent | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_tlm123_spaces_and_legacy_tlm_absent`。 | 公开入口在“tlm123 spaces and legacy tlm absent”场景下可导入、构造、注册或按名称发现。 | `test_tlm123_spaces_and_legacy_tlm_absent` |
| TC-SYMBOL-VARIABLE-MEMORY-060 | 公开入口 | repr | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_repr`。 | 公开入口在“repr”场景下可导入、构造、注册或按名称发现。 | `test_repr` |
| TC-SYMBOL-VARIABLE-MEMORY-061 | 公开入口 | construct from tensor fields | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_construct_from_tensor_fields`。 | 公开入口在“construct from tensor fields”场景下可导入、构造、注册或按名称发现。 | `test_construct_from_tensor_fields` |
| TC-SYMBOL-VARIABLE-MEMORY-062 | 内存/DMA | explicit stride list | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_explicit_stride_list`。 | 内存类型、布局、搬运结果或 verifier 行为体现“explicit stride list”场景。 | `test_explicit_stride_list` |
| TC-SYMBOL-VARIABLE-MEMORY-063 | 内存/DMA | dynamic shape stride | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_dynamic_shape_stride`。 | 内存类型、布局、搬运结果或 verifier 行为体现“dynamic shape stride”场景。 | `test_dynamic_shape_stride` |
| TC-SYMBOL-VARIABLE-MEMORY-064 | 公开入口 | dynamic shape public values use symbol dim get value | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dynamic_shape_public_values_use_symbol_dim_get_value`。 | 公开入口在“dynamic shape public values use symbol dim get value”场景下可导入、构造、注册或按名称发现。 | `test_dynamic_shape_public_values_use_symbol_dim_get_value` |
| TC-SYMBOL-VARIABLE-MEMORY-065 | 内存/DMA | shape stride accept symbol shape | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_shape_stride_accept_symbol_shape`。 | 内存类型、布局、搬运结果或 verifier 行为体现“shape stride accept symbol shape”场景。 | `test_shape_stride_accept_symbol_shape` |
| TC-SYMBOL-VARIABLE-MEMORY-066 | 公开入口 | default format | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_default_format`。 | 公开入口在“default format”场景下可导入、构造、注册或按名称发现。 | `test_default_format` |
| TC-SYMBOL-VARIABLE-MEMORY-067 | 公开入口 | space meta | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_space_meta`。 | 公开入口在“space meta”场景下可导入、构造、注册或按名称发现。 | `test_space_meta` |
| TC-SYMBOL-VARIABLE-MEMORY-068 | 内存/DMA | default stride generated row major | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_default_stride_generated_row_major`。 | 内存类型、布局、搬运结果或 verifier 行为体现“default stride generated row major”场景。 | `test_default_stride_generated_row_major` |
| TC-SYMBOL-VARIABLE-MEMORY-069 | 内存/DMA | default stride symbolic expression repr | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_default_stride_symbolic_expression_repr`。 | 内存类型、布局、搬运结果或 verifier 行为体现“default stride symbolic expression repr”场景。 | `test_default_stride_symbolic_expression_repr` |
| TC-SYMBOL-VARIABLE-MEMORY-070 | 内存/DMA | default stride symbolic expression from strings | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_default_stride_symbolic_expression_from_strings`。 | 内存类型、布局、搬运结果或 verifier 行为体现“default stride symbolic expression from strings”场景。 | `test_default_stride_symbolic_expression_from_strings` |
| TC-SYMBOL-VARIABLE-MEMORY-071 | 内存/DMA | clone with dtype preserves symbolic stride expression | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_clone_with_dtype_preserves_symbolic_stride_expression`。 | 内存类型、布局、搬运结果或 verifier 行为体现“clone with dtype preserves symbolic stride expression”场景。 | `test_clone_with_dtype_preserves_symbolic_stride_expression` |
| TC-SYMBOL-VARIABLE-MEMORY-072 | 内存/DMA | memory clone overrides dtype and space | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_clone_overrides_dtype_and_space`。 | 内存类型、布局、搬运结果或 verifier 行为体现“memory clone overrides dtype and space”场景。 | `test_memory_clone_overrides_dtype_and_space` |
| TC-SYMBOL-VARIABLE-MEMORY-073 | 公开入口 | memory clone defaults preserve public metadata | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_memory_clone_defaults_preserve_public_metadata`。 | 公开入口在“memory clone defaults preserve public metadata”场景下可导入、构造、注册或按名称发现。 | `test_memory_clone_defaults_preserve_public_metadata` |
| TC-SYMBOL-VARIABLE-MEMORY-074 | 边界/异常 | memory clone rejects invalid public overrides | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_clone_rejects_invalid_public_overrides`。 | “memory clone rejects invalid public overrides”场景按公开错误语义失败或被拒绝。 | `test_memory_clone_rejects_invalid_public_overrides` |
| TC-SYMBOL-VARIABLE-MEMORY-075 | 公开入口 | memory shape match uses symbol dim public values | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_memory_shape_match_uses_symbol_dim_public_values`。 | 公开入口在“memory shape match uses symbol dim public values”场景下可导入、构造、注册或按名称发现。 | `test_memory_shape_match_uses_symbol_dim_public_values` |
| TC-SYMBOL-VARIABLE-MEMORY-076 | 内存/DMA | memory binary arithmetic preserves lhs metadata | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_binary_arithmetic_preserves_lhs_metadata`。 | 内存类型、布局、搬运结果或 verifier 行为体现“memory binary arithmetic preserves lhs metadata”场景。 | `test_memory_binary_arithmetic_preserves_lhs_metadata` |
| TC-SYMBOL-VARIABLE-MEMORY-077 | 内存/DMA | memory repr and str share same text | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_repr_and_str_share_same_text`。 | 内存类型、布局、搬运结果或 verifier 行为体现“memory repr and str share same text”场景。 | `test_memory_repr_and_str_share_same_text` |
| TC-SYMBOL-VARIABLE-MEMORY-078 | 内存/DMA | memory scalar arithmetic promotes to int32 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_scalar_arithmetic_promotes_to_int32`。 | 内存类型、布局、搬运结果或 verifier 行为体现“memory scalar arithmetic promotes to int32”场景。 | `test_memory_scalar_arithmetic_promotes_to_int32` |
| TC-SYMBOL-VARIABLE-MEMORY-079 | 内存/DMA | memory metadata independent | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_metadata_independent`。 | 内存类型、布局、搬运结果或 verifier 行为体现“memory metadata independent”场景。 | `test_memory_metadata_independent` |
| TC-SYMBOL-VARIABLE-MEMORY-080 | 内存/DMA | memory compare returns bool dtype | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_compare_returns_bool_dtype`。 | 内存类型、布局、搬运结果或 verifier 行为体现“memory compare returns bool dtype”场景。 | `test_memory_compare_returns_bool_dtype` |
| TC-SYMBOL-VARIABLE-MEMORY-081 | 边界/异常 | memory shape mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_shape_mismatch`。 | “memory shape mismatch”场景按公开错误语义失败或被拒绝。 | `test_memory_shape_mismatch` |
| TC-SYMBOL-VARIABLE-MEMORY-082 | 边界/异常 | memory dtype mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_dtype_mismatch`。 | “memory dtype mismatch”场景按公开错误语义失败或被拒绝。 | `test_memory_dtype_mismatch` |
| TC-SYMBOL-VARIABLE-MEMORY-083 | 边界/异常 | memory scalar type error and supported int64 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_scalar_type_error_and_supported_int64`。 | “memory scalar type error and supported int64”场景按公开错误语义失败或被拒绝。 | `test_memory_scalar_type_error_and_supported_int64` |
| TC-SYMBOL-VARIABLE-MEMORY-084 | 内存/DMA | memory operation preserves tlm123 space | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_operation_preserves_tlm123_space`。 | 内存类型、布局、搬运结果或 verifier 行为体现“memory operation preserves tlm123 space”场景。 | `test_memory_operation_preserves_tlm123_space` |
