# memory.md

用于定义符号内存对象 `Memory` 及其内存空间枚举，描述带空间属性的张量形态。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`规格小队`
- `spec`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
- `功能实现`：[`symbol_variable/memory.py`](../../symbol_variable/memory.py)

## 依赖约定

- `symbol_variable.symbol_shape.SymbolShape`：形状与步幅类型。
- `symbol_variable.symbol_dim.SymbolDim`：维度元素类型（由 `SymbolShape` 间接依赖）。
- `symbol_variable.type.NumericType`：数据类型。
- `symbol_variable.type.Farmat`：格式枚举（按实现命名）。
- `enum.Enum`、`dataclasses.dataclass`：用于空间元信息与枚举定义。

## 术语

- 内存空间：硬件或逻辑存储区域的抽象分类（如 GM/SM/LM）。
- 空间元信息：空间名称、对齐要求与最大容量描述。

## 功能边界

- 仅定义空间枚举与内存对象的结构化描述，不负责真实分配或回收。
- 不校验容量、对齐或空间有效性，仅提供元信息。
- 不实现跨空间迁移或拷贝策略。
- 本次仅完成 `convert_from_*` 输入清理的接口收敛，不新增额外工厂类或转换层。

## 兼容性

- `Memory` 保持与张量基类一致的 `shape/dtype/stride/format` 接口与语义。
- 默认空间为 `MemorySpace.GM`，以保证与现有默认逻辑兼容。
- `stride` 允许为 `None`，语义与基础张量一致。
- `NumericType` 与 `Farmat` 的定义模块仍为 `symbol_variable.type`；若 `symbol_variable` 顶层包补充导出，这属于便捷入口扩展，不改变 `Memory` 的类型契约。
- `Memory(...)` 作为唯一公开构造入口；不再保留 `Memory.convert_from_tensor` 这类公开转换方法。
- `shape` 与 `stride` 的输入规整通过构造器内部完成，不再要求调用方先执行 `convert_from_list`。

## convert_from_* 清理

### 统一接口

- 创建 `Memory` 统一使用 `Memory(shape, dtype, space=..., stride=..., format=...)`。
- 调用方若原先使用 `Memory.convert_from_tensor(tensor)`，迁移后应显式传入：
  - `shape=tensor.shape`
  - `dtype=tensor.dtype`
  - `stride=tensor.stride`
  - `format=tensor.format`
- `shape` 与 `stride` 应接受：
  - 已构造的 `SymbolShape`
  - 或任何可被 `SymbolShape(...)` 正常接收的可迭代输入

### 统一命名

- 公开 API 使用类型名 `Memory(...)` 作为唯一输入入口。
- 不再新增 `convert_from_tensor`、`convert_from_memory` 等公开转换工厂。
- 若实现仍需要规整逻辑，应使用私有 `_normalize_shape`、`_normalize_stride` 一类 `_normalize_*` 命名。

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
- 对类 Tensor 对象的适配由调用方解包字段后直接调用构造器完成，不再提供单独 `convert_from_tensor`。

## 返回与错误

### 成功返回

- `Memory` 构造返回内存对象。

### 失败返回

- 由 `SymbolShape`/`SymbolDim`/`NumericType` 的构造或校验抛出对应异常。
- `shape` 或 `stride` 输入不满足 `SymbolShape` 规范时，向上抛出对应异常。

## 测试

- 测试文件：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
- 执行命令：`pytest -q test/symbol_variable/test_memory.py`

### 测试目标

- `LocalSpaceMeta` 为冻结数据类（不可修改字段）。
- `MemorySpace` 枚举项与元信息字段可访问。
- `Memory` 初始化保持张量字段并设置 `space`。
- `__repr__` 输出包含空间名与张量字段表达。
- 验证 `Memory` 在包级导出补充 `NumericType` / `Farmat` 后仍保持相同构造语义。
- 验证统一构造入口可直接接收 tensor-like 对象解包后的字段，无需 `convert_from_tensor`。
- 验证 `shape`/`stride` 可直接接收 `SymbolShape` 或普通可迭代输入。
- `format` 语义明确为 `Farmat.Norm -> NCHW`、`Farmat.CLast -> NHWC`。
- 枚举别名满足：`Farmat.Norm is Farmat.NCHW`，`Farmat.CLast is Farmat.NHWC`。
- 枚举名称/表示：`Farmat.Norm.name == "NCHW"`，`repr(Farmat.Norm)` 包含 `Farmat.NCHW`。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 覆盖构造、表示、转换与错误分支。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| ME-001 | 构造 | 默认空间 | N/A | `Memory(shape, dtype)` | `space` 为 `GM` |
| ME-002 | 构造 | 指定空间 | N/A | `Memory(shape, dtype, space=MemorySpace.LM)` | `space` 为 `LM` |
| ME-003 | 表现 | repr | N/A | `repr(memory)` | 含 `Memory(GM,` 前缀 |
| ME-004 | 构造 | tensor-like 字段直入 | N/A | `Memory(t.shape, t.dtype, stride=t.stride, format=t.format)` | 形状/类型/步幅/格式一致 |
| ME-005 | 格式 | layout | N/A | `format` 语义检查 | `Farmat.Norm -> NCHW`、`Farmat.CLast -> NHWC` |
| ME-006 | 别名 | Farmat | N/A | `Farmat.Norm`/`Farmat.CLast` | 与 `NCHW/NHWC` 同一枚举值 |
| ME-007 | 元信息 | LocalSpaceMeta | N/A | 读取 `MemorySpace.GM.value` | 字段可访问，align=1024 |
| ME-008 | 清理 | convert_from_tensor 移除 | N/A | 以构造器替代 `Memory.convert_from_tensor` | 统一使用 `Memory(...)` 入口 |
| ME-009 | 规范化 | shape/stride 直入 | N/A | `Memory(SymbolShape([1, 2]), dtype, stride=SymbolShape([2, 1]))` | 可直接接受已归一化输入 |
