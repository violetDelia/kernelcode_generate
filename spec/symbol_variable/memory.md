# memory.md

## 功能简介

用于定义符号内存对象 `Memory`、空间枚举 `MemorySpace` 与元信息 `LocalSpaceMeta`。该模块用于描述带 `shape`、`stride`、`dtype`、`format` 和 `space` 的张量式内存对象，不负责真实内存分配。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)、[`test/operation/test_memory_operation.py`](../../test/operation/test_memory_operation.py)
- `功能实现`：[`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)

## 依赖

- [`kernel_gen/symbol_variable/symbol_shape.py`](../../kernel_gen/symbol_variable/symbol_shape.py)：`SymbolShape` 定义与构造。
- [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)：`SymbolDim` 维度元素类型。
- [`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py)：`NumericType`/`Farmat` 类型与格式枚举。
- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)：`SymbolShape` 语义。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：`NumericType`/`Farmat` 语义。
- [`spec/operation/nn.md`](../../spec/operation/nn.md)：逐元素算术与比较规则来源（`Memory` 仅复用语义）。

## 限制与边界

- 仅负责描述 `Memory` 的结构化元信息，不负责真实分配、释放或生命周期管理。
- 不负责容量校验、对齐校验或空间可用性判断，只暴露空间元信息。
- 不负责跨空间迁移、拷贝、同步与调度策略。
- 不负责广播、自动类型提升、约束求解或推导真实存储偏移。
- 对外公开的创建入口为 `Memory(shape, dtype, space=..., stride=..., format=...)`。

## 公开接口

### LocalSpaceMeta

功能说明：

- 冻结数据类，用于描述单个空间的静态元信息。

参数说明：

- `name: str`：空间名称。
- `max_size: int | None`：最大容量，`None` 表示未指定。
- `align: int`：对齐要求，单位为字节。

使用示例：

```python
from kernel_gen.symbol_variable.memory import LocalSpaceMeta

meta = LocalSpaceMeta(name="GM", max_size=None, align=1024)
```

注意事项：

- 允许 `max_size=None` 表示未指定容量。

返回与限制：

- 返回不可变元信息对象（`LocalSpaceMeta`）。

### MemorySpace

功能说明：

- 内存空间枚举，枚举值为 `LocalSpaceMeta`。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.memory import MemorySpace

gm_meta = MemorySpace.GM.value
```

注意事项：

- 当前定义 `GM`/`SM`/`LM`/`TSM`/`TLM` 五种空间。
- 默认元信息一致：`align=1024`、`max_size=None`。

返回与限制：

- `MemorySpace.<SPACE>.value` 返回对应 `LocalSpaceMeta`。
- 返回类型为 `LocalSpaceMeta`。

### Memory

功能说明：

- 表示带 `shape`、`dtype`、`stride`、`format` 和 `space` 的内存对象。
- `shape` 与 `stride` 可包含动态 `SymbolDim`。

参数说明：

- 类型自身不接收参数；实例化参数与规则见 `__init__`。

使用示例：

```python
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

mem = Memory([1, 2], NumericType.Float32)
```

注意事项：

- `Memory` 的公开构造入口是 `Memory(...)`，行为由 `__init__` 约束。
- 逐元素算术与比较的规则在 `运算符重载` 小节中说明。
- `__init__` 是统一构造入口；显式步幅、动态维度、tensor-like 直入等内容仅用于说明常见使用场景，不引入额外公开构造 API。

返回与限制：

- `Memory(...)` 返回 `Memory` 实例。

#### __init__(shape, dtype, space=MemorySpace.GM, stride=None, format=Farmat.Norm)

功能说明：

- `Memory` 的统一公开构造入口。
- 负责规范化 `shape`、`stride`、`dtype`、`space` 与 `format`，生成可用于后续逐元素运算与表示的 `Memory` 实例。

参数说明：

- `shape`：`SymbolShape` 或可被 `SymbolShape(...)` 规范化的可迭代对象。
- `dtype`：`NumericType`。
- `space`：`MemorySpace`。
- `stride`：`None` 或可被 `SymbolShape(...)` 规范化的可迭代对象。
- `format`：`Farmat`。

使用示例：

```python
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

mem = Memory(
    shape=["B", 128],
    dtype=NumericType.Float32,
    space=MemorySpace.SM,
)
```

注意事项：

- `stride is None` 表示未显式提供步幅。
- `shape` 与 `stride` 接收 `SymbolShape` 或可迭代输入。

返回与限制：

- 返回 `Memory` 实例（`Memory`）。
- 规范化失败时向上抛出 `SymbolShape` 或 `SymbolDim` 相关异常。

#### 显式步幅构造

功能说明：

- 支持显式传入 `stride`，用于描述线性布局或自定义布局。

参数说明：

- 同 `__init__`，但 `stride` 为显式列表。

使用示例：

```python
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import Farmat, NumericType

mem = Memory(
    shape=[1, 64, 56, 56],
    dtype=NumericType.Float32,
    stride=[200704, 3136, 56, 1],
    format=Farmat.Norm,
)
```

注意事项：

- `shape` 与 `stride` 均会规范化为 `SymbolShape`。

返回与限制：

- 返回 `Memory` 实例（`Memory`）。

#### 动态张量构造

功能说明：

- 支持动态 `shape` 与动态 `stride`。

参数说明：

- 同 `__init__`。

使用示例：

```python
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

mem = Memory(
    shape=["B", "C", "H", "W"],
    dtype=NumericType.Float32,
    stride=["C*H*W", "H*W", "W", 1],
)
```

注意事项：

- 动态维度不在前端阶段退化为静态值。

返回与限制：

- 返回 `Memory` 实例（`Memory`）。

#### tensor-like 字段直入

功能说明：

- 若上游对象已拆出 `shape/dtype/stride/format` 字段，可直接使用公开构造入口创建 `Memory`。

参数说明：

- 同 `__init__`。

使用示例：

```python
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import Farmat, NumericType

class TensorLike:
    def __init__(self):
        self.shape = ["N", 64]
        self.dtype = NumericType.Float32
        self.stride = [64, 1]
        self.format = Farmat.Norm

t = TensorLike()
mem = Memory(t.shape, t.dtype, stride=t.stride, format=t.format)
```

注意事项：

- 调用方无需额外私有转换函数。

返回与限制：

- 返回 `Memory` 实例（`Memory`）。

#### __repr__()

功能说明：

- 返回包含 `space` 与张量元信息的稳定字符串表示。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

mem = Memory([1, 2], NumericType.Float32)
text = repr(mem)
```

注意事项：

- 返回形如 `Memory(GM,Tensor(shape=..., dtype=..., stride=..., format=...))` 的字符串。

返回与限制：

- 返回 `str`。

#### 运算符重载

功能说明：

- 允许 `Memory` 直接通过 Python 运算符表达逐元素算术与比较。

参数说明：

- `lhs (Memory)`：左操作数，为当前 `Memory` 实例。
- `rhs (Memory | int)`：右操作数；支持 `Memory` 或 `int` 标量（`bool` 视作 `int`）。
- `lhs`/`rhs` 均为 `Memory` 时：`shape` 必须完全一致。
- `rhs` 为标量时：标量需与 `lhs.dtype` 兼容。

使用示例：

```python
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

lhs = Memory(["M", "N"], NumericType.Float32)
rhs = Memory(["M", "N"], NumericType.Float32)

sum_mem = lhs + rhs
cmp_mem = lhs < 0
```

注意事项：

- 当前阶段不支持广播，`shape` 不一致抛 `ValueError`。
- 类型不兼容或标量类型不支持时抛 `TypeError`。
- 比较结果的 `dtype` 统一为 `NumericType.Int32`。
- 输出继承 `lhs` 的 `space`、`format` 与 `stride` 语义。

返回与限制：

- 算术/比较返回张量语义对象（`Memory`），`shape` 与输入一致。
- 规则细节以 [`spec/operation/nn.md`](../../spec/operation/nn.md) 为准。

## 测试

- 测试文件：
  - [`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
  - [`test/operation/test_memory_operation.py`](../../test/operation/test_memory_operation.py)
- 执行命令：
  - `pytest -q test/symbol_variable/test_memory.py`
  - `pytest -q test/operation/test_memory_operation.py`

### 测试目标

- 验证 `LocalSpaceMeta` 的冻结语义与字段可访问性。
- 验证 `MemorySpace` 枚举项与空间元信息稳定。
- 验证 `Memory` 默认空间、显式空间、显式步幅和动态形状构造行为。
- 验证 `shape` 与 `stride` 可直接接收 `SymbolShape` 或普通可迭代输入。
- 验证 `tensor-like` 字段直入能够通过公开构造入口完成。
- 验证 `__repr__` 包含空间与张量元信息。
- 验证运算符重载覆盖算术、比较与错误路径（形状不一致、dtype 不兼容、标量类型非法）。
- 验证运算符重载结果元数据独立（对应 `ME-012`）。
- 验证比较结果 `dtype` 为 `NumericType.Int32`（对应 `ME-013`）。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 对应测试 |
|---|---|---|---|---|---|---|
| ME-001 | 默认空间 | 省略 space | N/A | `Memory([1, 2], NumericType.Float32)` | `space` 为 `MemorySpace.GM` | `test_default_space` |
| ME-002 | 显式空间 | 指定 space | N/A | `Memory([1, 2], NumericType.Float32, space=MemorySpace.SM)` | `space` 为 `MemorySpace.SM` | `test_custom_space` |
| ME-003 | 表现 | repr | N/A | `repr(Memory([1, 2], NumericType.Float32))` | 包含 `Memory(GM,Tensor(...))` 信息 | `test_repr` |
| ME-004 | 构造 | tensor-like 字段直入 | N/A | `Memory(t.shape, t.dtype, stride=t.stride, format=t.format)` | 构造成功 | `test_construct_from_tensor_fields` |
| ME-005 | 构造 | 显式步幅列表 | N/A | `stride=[200704, 3136, 56, 1]` | `shape`/`stride` 规范化 | `test_explicit_stride_list` |
| ME-006 | 构造 | 动态 shape/stride | N/A | `shape=["B", "C"]`/`stride=["C", 1]` | 动态维度保留 | `test_dynamic_shape_stride` |
| ME-007 | 构造 | shape/stride 接收 SymbolShape | N/A | `Memory(SymbolShape(...), NumericType.Float32, stride=SymbolShape(...))` | 接收成功 | `test_shape_stride_accept_symbol_shape` |
| ME-008 | 默认格式 | 省略 format | N/A | `Memory([1, 2], NumericType.Float32)` | `format` 为 `Farmat.Norm` | `test_default_format` |
| ME-009 | 空间元信息 | 枚举元信息 | N/A | `MemorySpace.GM.value` | `align=1024`、`max_size=None` | `test_space_meta` |
| ME-010 | 运算符 | `Memory + Memory` | N/A | `lhs + rhs` | shape/dtype/space 继承约束成立 | `test_memory_add_memory` |
| ME-011 | 运算符 | `Memory + scalar` | N/A | `mem + 1` / `1 + mem` | 返回 `Memory` 且 shape/dtype 一致 | `test_memory_add_scalar` |
| ME-012 | 运算符 | 结果元信息独立 | N/A | `mem + 1` | 结果 `shape/stride` 独立，不复用原引用 | `test_memory_metadata_independent` |
| ME-013 | 运算符 | 比较 predicate | N/A | `lhs == rhs` / `lhs < 1` | `dtype` 为 `NumericType.Int32` | `test_memory_compare_predicate` |
| ME-014 | 运算符 | 形状不一致 | N/A | `lhs + rhs` | 抛 `ValueError` | `test_memory_shape_mismatch` |
| ME-015 | 运算符 | dtype 不兼容 | N/A | `lhs + rhs` | 抛 `TypeError` | `test_memory_dtype_mismatch` |
| ME-016 | 运算符 | 标量类型非法 | N/A | `mem + \"1\"` | 抛 `TypeError` | `test_memory_scalar_type_error` |
