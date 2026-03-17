# memory.md

用于定义符号内存对象 `Memory`、空间枚举 `MemorySpace` 。该模块用于描述带 `shape`、`stride`、`dtype`、`format` 和 `space` 的张量式内存对象，不负责真实内存分配。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`榕`
- `spec`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
- `功能实现`：[`python/symbol_variable/memory.py`](../../python/symbol_variable/memory.py)

## 依赖约定

- `python.symbol_variable.symbol_shape.SymbolShape`：用于表达 `shape` 与 `stride`。
- `python.symbol_variable.symbol_dim.SymbolDim`：`SymbolShape` 的元素类型。
- `python.symbol_variable.type.NumericType`：用于表达元素数据类型。
- `python.symbol_variable.type.Farmat`：用于表达张量布局格式。
- `enum.Enum`、`dataclasses.dataclass`：用于定义空间元信息与空间枚举。

## 术语

- 内存对象：带元信息的张量描述对象，不对应真实分配的物理缓冲区。
- 内存空间：硬件或逻辑存储区域的抽象分类，例如全局内存、共享内存、局部内存。
- 空间元信息：空间名称、对齐要求、最大容量等静态描述。
- 动态张量：`shape` 或 `stride` 中包含动态 `SymbolDim` 的 `Memory`。

## 功能边界

- 仅负责描述 `Memory` 的结构化元信息，不负责真实分配、释放或生命周期管理。
- 不负责容量校验、对齐校验或空间可用性判断，只暴露空间元信息。
- 不负责跨空间迁移、拷贝、同步与调度策略。
- 不负责广播、自动类型提升、约束求解或推导真实存储偏移。
- 对外公开的创建入口为 `Memory(shape, dtype, space=..., stride=..., format=...)`。

## 兼容性

- `Memory` 保持 `shape`、`dtype`、`stride`、`format`、`space` 五个核心属性的公开语义稳定。
- 默认空间为 `MemorySpace.GM`。
- `stride` 允许为 `None`，表示调用方未显式提供步幅信息。
- `shape` 与 `stride` 支持直接接收 `SymbolShape`，也支持接收可被 `SymbolShape(...)` 规范化的可迭代输入。
- `Memory` 的逐元素算术与比较语义与 [`spec/operation/nn.md`](../../spec/operation/nn.md) 保持一致；本文件只描述 `Memory` 侧的结构、入口和边界。

## 公开接口约束

### 构造入口

- 创建 `Memory` 统一使用 `Memory(shape, dtype, space=..., stride=..., format=...)`。
- `shape` 必须为 `SymbolShape` 或可被 `SymbolShape(...)` 正常接收的可迭代对象。
- `stride` 为 `None` 或可被 `SymbolShape(...)` 正常接收的可迭代对象。
- `dtype` 应为 `NumericType`。
- `space` 应为 `MemorySpace`。
- `format` 应为 `Farmat`。

使用示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

mem = Memory([1, 64, 56, 56], NumericType.Float32)
```

### 属性语义

- `shape`：张量形状，类型为 `SymbolShape`。
- `dtype`：张量元素类型，类型为 `NumericType`。
- `stride`：张量步幅，类型为 `SymbolShape | None`。
- `format`：张量布局格式，类型为 `Farmat`。
- `space`：张量所在空间，类型为 `MemorySpace`。

使用示例：

```python
from python.symbol_variable.memory import Memory, MemorySpace
from python.symbol_variable.type import Farmat, NumericType

mem = Memory(
    shape=[1, 64, 56, 56],
    dtype=NumericType.Float32,
    stride=[200704, 3136, 56, 1],
    format=Farmat.Norm,
    space=MemorySpace.GM,
)

assert mem.space is MemorySpace.GM
assert mem.format is Farmat.Norm
assert mem.shape.get_values() == [1, 64, 56, 56]
```

### 运算入口

- `Memory` 支持通过运算符重载参与逐元素算术与比较。
- 支持的算术糖接口包括：`+`、`-`、`*`、`/` 及其反向运算。
- 支持的比较糖接口包括：`==`、`!=`、`<`、`<=`、`>`、`>=`。
- 这些接口的合法性、输出语义和错误规则以 [`spec/operation/nn.md`](../../spec/operation/nn.md) 为准。

使用示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

lhs = Memory(["M", "N"], NumericType.Float32)
rhs = Memory(["M", "N"], NumericType.Float32)

sum_mem = lhs + rhs
cmp_mem = lhs < 0
```

## 功能

### LocalSpaceMeta

功能说明：

- 冻结数据类，用于描述单个空间的静态元信息。

字段：

- `name: str`：空间名称。
- `max_size: int | None`：最大容量，`None` 表示未指定。
- `align: int`：对齐要求，单位为字节。

使用示例：

```python
from python.symbol_variable.memory import LocalSpaceMeta

meta = LocalSpaceMeta(name="GM", max_size=None, align=1024)

assert meta.name == "GM"
assert meta.align == 1024
```

预期结果：

- `LocalSpaceMeta` 可作为不可变元信息对象使用。
- 允许 `max_size=None` 表示未指定容量。

### MemorySpace

功能说明：

- 内存空间枚举，枚举值为 `LocalSpaceMeta`。

枚举项：

- `GM`：全局内存，通常容量最大，默认创建空间。
- `SM`：共享内存，同一计算核中的执行单元可共享访问。
- `LM`：局部内存，执行单元私有内存。
- `TSM`：面向矩阵核心或专用计算单元的共享内存。
- `TLM`：面向矩阵核心或专用计算单元的局部内存。

默认元信息约束：

- `GM`/`SM`/`LM`/`TSM`/`TLM` 的默认元信息一致：`align=1024`、`max_size=None`。
- 上述默认值用于描述空间对齐与容量上限的静态属性，不执行运行期校验。

使用示例：

```python
from python.symbol_variable.memory import MemorySpace

gm_meta = MemorySpace.GM.value
sm_meta = MemorySpace.SM.value

assert gm_meta.name == "GM"
assert sm_meta.align == 1024
```

预期结果：

- 可通过 `MemorySpace.<SPACE>.value` 读取空间元信息。

### Memory

功能说明：

- 表示带 `shape`、`dtype`、`stride`、`format` 和 `space` 的内存对象。
- `shape` 和 `stride` 都保留符号维度信息，因此可表达动态张量。

#### 初始化

接口：`__init__(shape, dtype, space=MemorySpace.GM, stride=None, format=Farmat.Norm)`

功能说明：

- 规范化 `shape` 与 `stride`。
- 保存 `dtype`、`format` 与 `space`。
- 当 `stride is None` 时，仅表示“未显式提供步幅”；调用方可按行主序或其他规则解释。

使用示例：

```python
from python.symbol_variable.memory import Memory, MemorySpace
from python.symbol_variable.type import NumericType

mem = Memory(
    shape=["B", 128],
    dtype=NumericType.Float32,
    space=MemorySpace.SM,
)
```

预期结果：

- `shape` 被规范化为 `SymbolShape(["B", 128])`。
- `space` 为 `MemorySpace.SM`。
- `stride` 为 `None`。

#### 显式步幅构造

功能说明：

- 支持显式传入 `stride`，用于描述线性布局或任意自定义布局。

使用示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import Farmat, NumericType

mem = Memory(
    shape=[1, 64, 56, 56],
    dtype=NumericType.Float32,
    stride=[200704, 3136, 56, 1],
    format=Farmat.Norm,
)
```

预期结果：

- `shape` 与 `stride` 都被规范化为 `SymbolShape`。
- `format` 为 `Farmat.Norm`。

#### 动态张量构造

功能说明：

- 支持动态 `shape` 与动态 `stride`。

使用示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

mem = Memory(
    shape=["B", "C", "H", "W"],
    dtype=NumericType.Float32,
    stride=["C*H*W", "H*W", "W", 1],
)
```

预期结果：

- `Memory` 保留动态维度，不在前端阶段将其退化为静态值。

#### tensor-like 字段直入

功能说明：

- 若上游对象已拆出 `shape/dtype/stride/format` 字段，可直接使用公开构造入口创建 `Memory`。

使用示例：

```python
from python.symbol_variable.memory import Memory

class TensorLike:
    def __init__(self):
        self.shape = ["N", 64]
        self.dtype = NumericType.Float32
        self.stride = [64, 1]
        self.format = Farmat.Norm

t = TensorLike()
mem = Memory(t.shape, t.dtype, stride=t.stride, format=t.format)
```

预期结果：

- 调用方无需额外私有转换函数，即可通过公开构造入口完成适配。

#### 字符串表现

接口：`__repr__()`

功能说明：

- 返回包含 `space` 与张量元信息的稳定字符串表示。

使用示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

mem = Memory([1, 2], NumericType.Float32)
text = repr(mem)
```

预期结果：

- 返回形如 `Memory(GM,Tensor(shape=..., dtype=..., stride=..., format=...))` 的字符串。

#### 运算符重载

功能说明：

- 允许 `Memory` 直接通过 Python 运算符表达逐元素算术与比较。
- 输出仍为张量语义对象，不返回单个 Python 标量。

使用示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

A = Memory(["M", "N"], NumericType.Float32)
B = Memory(["M", "N"], NumericType.Float32)

C = A + B
D = A + 3
E = A == B
F = A < 0
```

预期结果：

- `C.shape == A.shape`
- `D.shape == A.shape`
- `E` 与 `F` 仍为张量语义对象

## 逐元素算术与比较约束

本节仅补充 `Memory` 侧边界；完整规则以 [`spec/operation/nn.md`](../../spec/operation/nn.md) 为准。

### 输入约束

- `Memory` 与 `Memory` 运算时，`shape` 必须完全一致，不支持广播。
- 当前阶段若未定义类型提升规则，则 `dtype` 需完全一致。
- `Memory` 与标量运算时，标量需与 `Memory.dtype` 兼容。
- `space`、`format` 与 `stride` 不参与逐元素合法性判断。

### 输出语义

- 算术运算输出张量语义结果，`shape` 与输入一致，动态维度不丢失。
- 比较运算输出张量语义结果，`shape` 与输入一致。
- 比较结果的语义是逐元素 `bool/predicate`；在当前 `Memory` 实现中，其具体 `dtype` 统一为 `NumericType.Int32`。
- 输出继承 `lhs` 的 `space`、`format` 与 `stride` 语义。
- 当前实现会克隆结果的 `shape/stride` 容器，避免与 `lhs` 共享可变元数据。

示例：

```python
lhs = Memory(["M", "N"], NumericType.Float32)
rhs = Memory(["M", "N"], NumericType.Float32)

cmp_result = lhs == rhs
assert cmp_result.shape.get_values() == ["M", "N"]
assert cmp_result.dtype is NumericType.Int32
```

### 错误规则

- `shape` 不一致：抛 `ValueError`。
- `dtype` 不兼容：抛 `TypeError`。
- 标量类型不支持：抛 `TypeError`。
- 非法链式表达式在首次非法处立即抛错。

## 返回与错误

### 成功返回

- `LocalSpaceMeta(...)` 返回不可变空间元信息对象。
- `MemorySpace.<SPACE>` 返回空间枚举项。
- `Memory(...)` 返回内存对象。
- 合法的逐元素算术与比较返回张量语义结果对象。

### 失败返回

- `shape` 或 `stride` 不满足 `SymbolShape` 规范时，向上抛出对应异常。
- `dtype`、`format` 或 `space` 类型不符合调用约定时，行为由实现决定，但不得 silently 修正为不相关类型。
- 运算输入不满足 [`spec/operation/nn.md`](../../spec/operation/nn.md) 的约束时，抛出对应 `TypeError` 或 `ValueError`。

## 测试

- 结构测试：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
- 相关运算规范测试：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- 结构测试命令：`pytest -q test/symbol_variable/test_memory.py`

### 测试目标

- 验证 `LocalSpaceMeta` 的冻结语义与字段可访问性。
- 验证 `MemorySpace` 枚举项与空间元信息稳定，至少覆盖 `GM` 默认 `align=1024`、`max_size=None`。
- 验证 `Memory` 默认空间、显式空间、显式步幅和动态形状构造行为。
- 验证 `shape` 与 `stride` 可直接接收 `SymbolShape` 或普通可迭代输入。
- 验证 `tensor-like` 字段直入能够通过公开构造入口完成。
- 验证 `__repr__` 包含空间与张量元信息。
- 逐元素算术与比较的行为、错误类型和链式约束由 [`spec/operation/nn.md`](../../spec/operation/nn.md) 的对应测试覆盖。

### 测试标准

- 对应测试全部通过，`pytest` 返回码为 `0`。
- `Memory` 的结构语义、空间语义和公开构造入口保持稳定。
