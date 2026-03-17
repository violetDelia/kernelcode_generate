# memory.md

用于定义符号内存对象 `Memory` 及其内存空间枚举，描述带空间属性的张量形态。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
- `功能实现`：[`python/symbol_variable/memory.py`](../../python/symbol_variable/memory.py)

## 依赖约定

- `python.symbol_variable.symbol_shape.SymbolShape`：形状与步幅类型。
- `python.symbol_variable.symbol_dim.SymbolDim`：维度元素类型（由 `SymbolShape` 间接依赖）。
- `python.symbol_variable.type.NumericType`：数据类型。
- `python.symbol_variable.type.Farmat`：格式枚举（按实现命名）。
- `enum.Enum`、`dataclasses.dataclass`：用于空间元信息与枚举定义。

## Compat 说明

- 迁移后不再兼容旧路径 `symbol_variable.memory`，不提供 compat 转发模块。

## 术语

- 内存空间：硬件或逻辑存储区域的抽象分类（如 GM/SM/LM）。
- 空间元信息：空间名称、对齐要求与最大容量描述。
- `bool`：逐元素比较的概念性真值语义。
- `predicate`：spec 层对比较结果的语义描述，强调其表示逐元素真假而非普通算术值。
- `NumericType.Int32`：当前 `python/symbol_variable/memory.py` 实现与 `test/operation/test_memory_operation.py` 测试中用于承载比较结果的具体 `dtype`；在本模块中它承担 predicate 载体角色，而不是独立 `bool` 类型。

## 功能边界

- 仅定义空间枚举与内存对象的结构化描述，不负责真实分配或回收。
- 不校验容量、对齐或空间有效性，仅提供元信息。
- 不实现跨空间迁移或拷贝策略。
- 对外提供 `Memory(...)` 作为内存对象构造入口。

## 兼容性

- `Memory` 保持与张量基类一致的 `shape/dtype/stride/format` 接口与语义。
- 默认空间为 `MemorySpace.GM`，以保证与现有默认逻辑兼容。
- `stride` 允许为 `None`，语义与基础张量一致。
- `Memory(...)` 作为公开构造入口。
- `shape` 与 `stride` 的输入规整通过构造器内部完成，不再要求调用方先执行 `convert_from_list`。
- 当前 Python 层没有独立的 `bool/predicate` `NumericType`；因此比较结果在 `Memory` API 中统一落为 `NumericType.Int32`。
- 本文件中的 `bool` / `predicate` 表述用于说明比较语义；落实到当前 `Memory` 实现与测试时，具体契约以 `NumericType.Int32` 为准。

## 公开接口约束

### 构造入口

- 创建 `Memory` 统一使用 `Memory(shape, dtype, space=..., stride=..., format=...)`。
- `shape` 与 `stride` 应接受：
  - 已构造的 `SymbolShape`
  - 或任何可被 `SymbolShape(...)` 正常接收的可迭代输入

### 命名约束

- 公开 API 使用类型名 `Memory(...)` 作为唯一输入入口。
- 若实现仍需要规整逻辑，应使用私有 `_normalize_shape`、`_normalize_stride` 一类 `_normalize_*` 命名。
- 逐元素算术/比较遵循 [`spec/operation/nn.md`](../../spec/operation/nn.md) 规范；本文件仅补充 Memory 侧的边界与约束。

## 功能

### LocalSpaceMeta

功能说明：

- 冻结数据类，描述单个空间的元信息。

字段：

- `name: str`：空间名称。
- `max_size: int | None`：最大容量，允许为 `None` 表示未指定。
- `align: int`：对齐要求（以字节为单位）。

### MemorySpace

功能说明：

- 内存空间枚举，枚举值为 `LocalSpaceMeta`。

枚举项（示例实现）：

- `GM` / `SM` / `LM` / `TSM` / `TLM`
- `align` 默认为 `1024`，`max_size` 默认为 `None`。

### Memory

功能说明：

- 增加 `space` 属性以描述所在空间，其余字段与张量对象保持一致。

#### 初始化

接口：`__init__(shape, dtype, space=MemorySpace.GM, stride=None, format=Farmat.Norm)`

功能说明：

- 初始化 `shape/dtype/stride/format` 与张量对象一致。
- `shape` 统一规范化为 `SymbolShape` 语义。
- 记录 `space`。
- `stride=None` 时保持 `None`；否则按与 `shape` 一致的规则规范化。
- `format` 约定：`Farmat.Norm -> NCHW`，`Farmat.CLast -> NHWC`。

#### 字符串表现

接口：`__repr__()`

功能说明：返回 `Memory(<space name>,<tensor repr>)`。

#### 统一构造入口

接口：`Memory(shape, dtype, space=MemorySpace.GM, stride=None, format=Farmat.Norm)`

功能说明：

- 由原始 `shape/stride` 数据或现成 `SymbolShape` 直接构造 `Memory`。
- 对类 Tensor 对象的适配由调用方解包字段后直接调用构造器完成。

## 逐元素算术与比较运算规范

本节用于将 `Memory` 的逐元素算术/比较约束与 `spec/operation/nn.md` 对齐，并补充 Memory 侧边界。

### 适用范围

- 至少一侧操作数为 `Memory`。
- 支持 `Memory` 与 `Memory`、`Memory` 与数值标量（阶段一至少支持 `int`）。
- 不支持广播；`shape` 必须严格一致。

### 输入约束

- `Memory` 与 `Memory`：`shape` 完全一致，否则抛 `ValueError`。
- `dtype` 需可兼容；未定义类型提升规则时要求一致，不兼容抛 `TypeError`。
- 标量需与 `Memory.dtype` 兼容，否则抛 `TypeError`。
- 不支持 `str/list/dict` 等无数值语义类型，抛 `TypeError`。

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

- 输入类型不支持：`TypeError`。
- `shape` 不一致：`ValueError`。
- `dtype` 不兼容：`TypeError`。
- 链式表达式任一步非法：立即抛错并终止。

## 返回与错误

### 成功返回

- `Memory` 构造返回内存对象。

### 失败返回

- 由 `SymbolShape`/`SymbolDim`/`NumericType` 的构造或校验抛出对应异常。
- `shape` 或 `stride` 输入不满足 `SymbolShape` 规范时，向上抛出对应异常。

## 测试

- 测试文件：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
- 运算测试：[`test/operation/test_memory_operation.py`](../../test/operation/test_memory_operation.py)
- 执行命令：`pytest -q test/symbol_variable/test_memory.py test/operation/test_memory_operation.py`

### 测试目标

- `LocalSpaceMeta` 为冻结数据类（不可修改字段）。
- `MemorySpace` 枚举项与元信息字段可访问。
- `Memory` 初始化保持张量字段并设置 `space`。
- `stride` 为显式列表或 `SymbolShape` 时可直接接受并规整。
- 动态 `shape/stride` 输入保持动态维度语义不丢失。
- `__repr__` 输出包含空间名与张量字段表达。
- 验证统一构造入口可直接接收 tensor-like 对象解包后的字段。
- 验证 `shape`/`stride` 可直接接收 `SymbolShape` 或普通可迭代输入。
- `format` 语义明确为 `Farmat.Norm -> NCHW`、`Farmat.CLast -> NHWC`。
- 枚举别名满足：`Farmat.Norm is Farmat.NCHW`，`Farmat.CLast is Farmat.NHWC`。
- 枚举名称/表示：`Farmat.Norm.name == "NCHW"`，`repr(Farmat.Norm)` 包含 `Farmat.NCHW`。
- 逐元素算术/比较符合 `spec/operation/nn.md`：shape 严格一致、dtype 兼容、错误类型稳定。
- 比较结果 `dtype` 契约与当前实现/测试一致：语义上是 predicate，具体返回 `NumericType.Int32`。
- 运算结果元数据与 `lhs` 不别名共享。
- 逐元素错误分支覆盖：shape 不一致、dtype 不兼容、标量类型不支持。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 覆盖构造、表示、转换与错误分支。

### 功能与用例清单

以测试函数为准建立一一对应关系；`ME-*` 编号在本 spec 中唯一，不复用。

| 用例 ID | 对应测试函数 | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|---|
| ME-001 | `test_default_space` | 构造 | 默认空间 | N/A | `Memory(shape, dtype)` | `space` 为 `GM` |
| ME-002 | `test_custom_space` | 构造 | 指定空间 | N/A | `Memory(shape, dtype, space=MemorySpace.LM)` | `space` 为 `LM` |
| ME-003 | `test_repr` | 表现 | repr | N/A | `repr(memory)` | 含 `Memory(GM,` 前缀及张量字段表达 |
| ME-004 | `test_construct_from_tensor_fields` | 构造 | tensor-like 字段直入 | N/A | `Memory(t.shape, t.dtype, stride=t.stride, format=t.format)` | 形状/类型/步幅/格式一致 |
| ME-005 | `test_explicit_stride_list` | 构造 | 显式 stride 列表 | N/A | `Memory([2, 3], dtype, stride=[3, 1])` | `stride` 规整为 `SymbolShape` |
| ME-006 | `test_dynamic_shape_stride` | 构造 | 动态 shape/stride | N/A | `Memory(["N", 32], dtype, stride=["C", 1])` | 动态维度保持为字符串符号 |
| ME-007 | `test_shape_stride_accept_symbol_shape` | 规范化 | shape/stride 直入 | N/A | `Memory(SymbolShape([1, "N"]), dtype, stride=SymbolShape([2, 1]))` | 直接接受已归一化输入 |
| ME-008 | `test_format_mapping` | 格式 | layout 与别名 | N/A | 检查 `Farmat.Norm` / `Farmat.CLast` | `Norm -> NCHW`、`CLast -> NHWC`，且与 `NCHW/NHWC` 为同一枚举值 |
| ME-009 | `test_space_meta` | 元信息 | `LocalSpaceMeta` / `MemorySpace` | N/A | 读取 `MemorySpace.GM.value` | 字段可访问，`align=1024`，且 `LocalSpaceMeta` 冻结 |
| ME-010 | `test_memory_add_memory` | 运算 | Memory + Memory | `shape` 相同 | `lhs + rhs` | 返回 `Memory`，`shape` 保持一致，`dtype` 继承 `lhs` |
| ME-011 | `test_memory_add_scalar` | 运算 | Memory + scalar | `dtype` 兼容 | `mem + 1` / `1 + mem` | `shape` 保持一致，`dtype` 继承原值 |
| ME-012 | `test_memory_metadata_independent` | 运算 | 元数据独立性 | `stride` 非空 | `result = mem + 1` 后修改 `result.shape/stride` | 结果元数据不复用原对象 |
| ME-013 | `test_memory_compare_predicate` | 运算 | 比较结果 | `shape` 相同 | `lhs == rhs`、`lhs < 1` | 结果 `shape` 保持一致，语义上为 predicate，具体 `dtype` 为 `NumericType.Int32` |
| ME-014 | `test_memory_shape_mismatch` | 错误 | shape 不一致 | `shape` 不同 | `lhs + rhs` | 抛 `ValueError` |
| ME-015 | `test_memory_dtype_mismatch` | 错误 | dtype 不兼容 | `dtype` 不同 | `lhs + rhs` | 抛 `TypeError` |
| ME-016 | `test_memory_scalar_type_error` | 错误 | 标量类型不支持 | N/A | `mem + "1"` | 抛 `TypeError` |
