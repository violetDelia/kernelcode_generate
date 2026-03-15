# symbol_shape.md

用于定义符号形状（SymbolShape/列表容器）的表达、访问与序列化规则。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)
- `test`：[`test/symbol_variable/test_symbol_shape.py`](../../test/symbol_variable/test_symbol_shape.py)
- `功能实现`：[`symbol_variable/symbol_shape.py`](../../symbol_variable/symbol_shape.py)

## 依赖约定

- `symbol_variable.symbol_dim.SymbolDim`：维度元素类型。
- `typing`：仅用于类型标注。

## 术语

- 形状列表：由多个 `SymbolDim` 组成的有序列表。
- 动态维度：`SymbolDim.is_dynamic()` 为 `True` 的维度。

## 功能边界

- 仅负责形状容器的保存、访问与基本序列化。
- 不负责广播、约束求解、形状推导或算子语义。
- 不改变 `SymbolDim` 的内部符号表达式，仅进行包装与传递。

## 重构目标

- 保持容器不变量：`shape` 内所有元素必须为 `SymbolDim`。
- 明确切片赋值的输入约束，避免写入非 `SymbolDim` 导致的运行期错误。
- 明确 `get_shape()` 的返回约束，避免外部直接破坏内部状态。
- 修复因容器不变量被破坏导致的 `AttributeError` 风险（例如 `get_values()` 调用 `is_dynamic()` 时遇到非 `SymbolDim`）。

## 兼容性

- 对外接口保持列表式使用体验（`len`、迭代、索引）。
- 输入元素通过 `SymbolDim` 统一包装，支持 `SymbolDim` 与 `int`，并沿用 `SymbolDim` 对其他输入类型的支持与错误规则。
- `__getitem__` 支持 int 与 slice；`__setitem__` 对 slice 赋值需遵守本 spec 的规范化规则。
- 索引越界（int）统一抛 `IndexError("下标超出范围")`。

## 功能

### _SymbolList

功能说明：

- 内部基类，保存 `shape: List[SymbolDim]` 并提供序列行为。

#### 初始化

接口：`__init__(shapes: List[SymbolDim | int])`

功能说明：

- 遍历输入列表。
- `SymbolDim` 直接保存。
- 非 `SymbolDim` 通过 `SymbolDim(value)` 转换并保存。

使用示例：

```python
from symbol_variable.symbol_shape import SymbolShape
from symbol_variable.symbol_dim import SymbolDim

shape = SymbolShape([SymbolDim("N"), 32, 64])
```

#### 列表行为

接口：

- `__repr__()`：返回 `List(d0, d1, ...)`。
- `__len__()`：返回维度数量。
- `__iter__()`：迭代各 `SymbolDim`。
- `__reversed__()`：反向迭代各 `SymbolDim`。
- `__getitem__(key)`：
  - `int` 索引越界抛 `IndexError("下标超出范围")`。
  - `slice` 返回 `List[SymbolDim]`。
- `__setitem__(key, value)`：
  - `int` 索引越界抛 `IndexError("下标超出范围")`。
  - `int` 索引赋值会执行 `SymbolDim(value)`。
  - `slice` 赋值接受可迭代对象，逐项按 `SymbolDim` 可接受类型执行 `SymbolDim(v)` 规范化并写入。
  - `slice` 赋值若 value 不可迭代，抛 `TypeError`（不可迭代对象）。
  - `slice` 赋值若存在元素无法转换为 `SymbolDim`，抛 `TypeError`（元素类型不合法）。
  - 非 `int`/`slice` 的 key 抛 `TypeError`。

#### 形状访问

接口：`get_shape()`

功能说明：返回 `List[SymbolDim]` 的浅拷贝（不暴露内部可变列表）。

#### 形状序列化

接口：`get_values()`

功能说明：

- 对每个维度：
  - 动态维度返回 `str(dim.get_symbol())`。
  - 静态维度返回 `int(dim.get_symbol())`。

### SymbolList

功能说明：

- 对外公开的形状列表类型，提供额外的转换/序列化能力。

#### 列表转换

接口：`convert_from_list(shapes)`

功能说明：

- `shapes` 若为 `SymbolShape`，直接返回。
- 其他情况返回 `SymbolShape(shapes)`。

#### 序列化

接口：`to_symbols()`

功能说明：

- 与 `get_values()` 相同的序列化规则。

### SymbolShape

功能说明：

- 具体形状类型，继承 `SymbolList`。

#### 初始化

接口：`__init__(shapes)`

功能说明：同 `_SymbolList.__init__`。

#### 字符串表现

接口：`__repr__()`

功能说明：返回 `Shape(d0, d1, ...)`。

## 返回与错误

### 成功返回

- 构造返回 `SymbolShape` 或 `SymbolList`。
- `get_shape` 返回 `List[SymbolDim]`。
- `get_values`/`to_symbols` 返回 `List[int | str]`。

### 失败返回

- `SymbolDim` 构造失败时向上抛出对应异常（如 `ValueError`、`TypeError`）。
- `__getitem__` / `__setitem__` int 索引越界抛 `IndexError("下标超出范围")`。
- `__setitem__` 非 `int`/`slice` key 抛 `TypeError`。
- `slice` 赋值若 value 不可迭代，抛 `TypeError`（不可迭代对象）。
- `slice` 赋值若存在元素无法转换为 `SymbolDim`，抛 `TypeError`（元素类型不合法）。

## 测试

- 测试文件：[`test/symbol_variable/test_symbol_shape.py`](../../test/symbol_variable/test_symbol_shape.py)
- 执行命令：`pytest -q test/symbol_variable/test_symbol_shape.py`

### 测试目标

- 构造：支持 `SymbolDim`、`int` 及 `SymbolDim` 可接受的输入。
- 列表行为：`len`、迭代、反向迭代、`repr`。
- 索引访问：int 索引越界错误信息一致。
- 赋值：int 索引赋值会转换为 `SymbolDim`；slice 赋值会逐项转换为 `SymbolDim`。
- slice 赋值不可迭代对象触发 `TypeError`（不可迭代对象）。
- slice 赋值存在元素无法转换触发 `TypeError`（元素类型不合法）。
- `get_shape()` 返回拷贝，外部修改不应影响内部。
- 序列化：动态维度输出 `str`，静态维度输出 `int`。
- `convert_from_list` 对 `SymbolShape` 返回自身。
- 容器不变量保持，`get_values()` 不因非 `SymbolDim` 触发 `AttributeError`。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 覆盖构造、访问、序列化与异常分支。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| SS-001 | 构造 | SymbolDim/int | N/A | `SymbolShape([SymbolDim("N"), 32])` | 构造成功 |
| SS-002 | 序列化 | 动态/静态 | N/A | `get_values()` | 动态为 str，静态为 int |
| SS-003 | 访问 | 越界 | N/A | `shape[99]` | 抛 `IndexError("下标超出范围")` |
| SS-004 | 赋值 | int 索引 | N/A | `shape[0] = 64` | 转为 `SymbolDim` |
| SS-005 | 赋值 | slice 索引 | N/A | `shape[0:2] = [1, "N"]` | 逐项转为 `SymbolDim` |
| SS-006 | 异常 | slice 不可迭代 | N/A | `shape[0:1] = 1` | 抛 `TypeError`（不可迭代对象） |
| SS-007 | 异常 | slice 元素非法 | N/A | `shape[0:1] = [object()]` | 抛 `TypeError`（元素类型不合法） |
| SS-008 | 访问 | get_shape 拷贝 | N/A | `get_shape()` | 修改返回值不影响内部 |
| SS-009 | 转换 | convert_from_list | N/A | `SymbolList.convert_from_list(shape)` | 返回自身 |
| SS-010 | 表现 | repr | N/A | `repr(SymbolShape([1,2]))` | 返回 `Shape(1, 2)` |
