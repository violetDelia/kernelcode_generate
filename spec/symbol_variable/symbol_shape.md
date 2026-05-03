# symbol_shape.md

## 功能简介

用于定义 `SymbolShape` / `SymbolList` 的容器合同。本文只收三件事：输入如何规整为 `SymbolDim`，列表访问与赋值如何工作，公开序列化输出什么。

## API 列表

- `class SymbolList(shapes: SymbolShapeValues)`
  - `__repr__() -> str`
  - `__len__() -> int`
  - `__iter__() -> Iterator[SymbolDim]`
  - `__reversed__() -> Iterator[SymbolDim]`
  - `__getitem__(key: int | slice) -> SymbolDim | list[SymbolDim]`
  - `__setitem__(key: int | slice, value: SymbolShapeAssignment) -> None`
  - `get_shape() -> list[SymbolDim]`
  - `get_values() -> list[int | str]`
  - `to_symbols() -> list[int | str]`
- `class SymbolShape(shapes: SymbolShapeValues)`
  - `__repr__() -> str`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)
- `test`：[`test/symbol_variable/test_symbol_shape.py`](../../test/symbol_variable/test_symbol_shape.py)
- `功能实现`：[`kernel_gen/symbol_variable/symbol_shape.py`](../../kernel_gen/symbol_variable/symbol_shape.py)

## 依赖

- [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)：单个分量的构造与公开值规则。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：`SymbolDim` 语义来源。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`shape/stride` 进入 `Memory` 后的消费规则。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 只负责容器化保存、访问、切片赋值和序列化，不负责广播、推导或约束求解。
- 对外规整入口是 `SymbolList(shapes)` 与 `SymbolShape(shapes)`；具体 shape 容器优先使用 `SymbolShape`。
- 内部元素始终是 `SymbolDim`。
- `__getitem__` 只支持 `int` / `slice`。
- `__setitem__` 的 `slice` 赋值必须接收可迭代对象，并逐项规整为 `SymbolDim`。
- 索引越界统一抛 `IndexError("下标超出范围")`。
- `slice` 赋值异常边界复用 `SymbolDim(...)`：
  - 不可转换对象收敛为 `TypeError("切片赋值元素无法转换为 SymbolDim")`
  - 浮点输入保持 `NotImplementedError`

## API详细说明

### `class SymbolList(shapes: SymbolShapeValues)`

- api：`class SymbolList(shapes: SymbolShapeValues)`
- 参数：
  - `shapes`：形状序列；类型 `SymbolShapeValues`；无默认值；不允许 None；每个元素必须能构造为 SymbolDim。
- 返回值：`SymbolList` 实例。
- 使用示例：

  ```python
    from kernel_gen.symbol_variable.symbol_shape import SymbolList

    value = SymbolList(shapes=[1, "N"])
    ```
- 功能说明：构造 `SymbolList`，统一保存符号维度列表。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `__repr__() -> str`

- api：`__repr__() -> str`
- 参数：无。
- 返回值：`str`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    text = repr(symbol_list)
    ```
- 功能说明：执行 `__repr__`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `__len__() -> int`

- api：`__len__() -> int`
- 参数：无。
- 返回值：`int`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    length = len(symbol_list)
    ```
- 功能说明：执行 `__len__`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `__iter__() -> Iterator[SymbolDim]`

- api：`__iter__() -> Iterator[SymbolDim]`
- 参数：无。
- 返回值：`Iterator[SymbolDim]`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    values = list(symbol_list)
    ```
- 功能说明：执行 `__iter__`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `__reversed__() -> Iterator[SymbolDim]`

- api：`__reversed__() -> Iterator[SymbolDim]`
- 参数：无。
- 返回值：`Iterator[SymbolDim]`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    values = list(reversed(symbol_list))
    ```
- 功能说明：执行 `__reversed__`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `__getitem__(key: int | slice) -> SymbolDim | list[SymbolDim]`

- api：`__getitem__(key: int | slice) -> SymbolDim | list[SymbolDim]`
- 参数：
  - `key`：索引键；类型 `int | slice`；无默认值；不允许 None；必须是 int 或 slice。
- 返回值：`SymbolDim | list[SymbolDim]`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    first = symbol_list[0]
    ```
- 功能说明：执行 `__getitem__`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `__setitem__(key: int | slice, value: SymbolShapeAssignment) -> None`

- api：`__setitem__(key: int | slice, value: SymbolShapeAssignment) -> None`
- 参数：
  - `key`：索引键；类型 `int | slice`；无默认值；不允许 None；必须是 int 或 slice。
  - `value`：输入值；类型 `SymbolShapeAssignment`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
- 返回值：无返回值；调用成功表示对应 AST、IR 或 runtime 动作已完成。
- 使用示例：

  ```python
    symbol_list[0] = "M"
    ```
- 功能说明：执行 `__setitem__`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `get_shape() -> list[SymbolDim]`

- api：`get_shape() -> list[SymbolDim]`
- 参数：无。
- 返回值：`list[SymbolDim]`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    result = symbol_list.get_shape()
    ```
- 功能说明：执行 `get_shape`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `get_values() -> list[int | str]`

- api：`get_values() -> list[int | str]`
- 参数：无。
- 返回值：`list[int | str]`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    result = symbol_list.get_values()
    ```
- 功能说明：执行 `get_values`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `to_symbols() -> list[int | str]`

- api：`to_symbols() -> list[int | str]`
- 参数：无。
- 返回值：`list[int | str]`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    result = symbol_list.to_symbols()
    ```
- 功能说明：执行 `to_symbols`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `class SymbolShape(shapes: SymbolShapeValues)`

- api：`class SymbolShape(shapes: SymbolShapeValues)`
- 参数：
  - `shapes`：形状序列；类型 `SymbolShapeValues`；无默认值；不允许 None；每个元素必须能构造为 SymbolDim。
- 返回值：`SymbolShape` 实例。
- 使用示例：

  ```python
    from kernel_gen.symbol_variable.symbol_shape import SymbolShape

    value = SymbolShape(shapes=[1, "N"])
    ```
- 功能说明：构造 `SymbolShape`，统一保存符号维度列表。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

### `__repr__() -> str`

- api：`__repr__() -> str`
- 参数：无。
- 返回值：`str`；失败路径按本 API 的 `注意事项` 处理。
- 使用示例：

  ```python
    text = repr(symbol_list)
    ```
- 功能说明：执行 `__repr__`，读取或更新符号形状列表的公开行为。
- 注意事项：元素统一规整为 `SymbolDim`；切片、迭代和 repr 只暴露公开维度值，不暴露内部 sympy 可变状态。

## 测试

- 测试文件：`test/symbol_variable/test_symbol_shape.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/symbol_variable/test_symbol_shape.py`

### 测试目标

- 验证本文件 `API 列表` 中公开 API 的稳定行为、边界和错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-001 | 符号语义 | init accepts symbol dim and int | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_init_accepts_symbol_dim_and_int`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“init accepts symbol dim and int”场景。 | `test_init_accepts_symbol_dim_and_int` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-002 | 公开入口 | public serialization paths | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_public_serialization_paths`。 | 公开入口在“public serialization paths”场景下可导入、构造、注册或按名称发现。 | `test_public_serialization_paths` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-003 | 公开入口 | repr variants | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_repr_variants`。 | 公开入口在“repr variants”场景下可导入、构造、注册或按名称发现。 | `test_repr_variants` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-004 | 内存/DMA | construct from existing shape returns equivalent copy | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_construct_from_existing_shape_returns_equivalent_copy`。 | 内存类型、布局、搬运结果或 verifier 行为体现“construct from existing shape returns equivalent copy”场景。 | `test_construct_from_existing_shape_returns_equivalent_copy` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-005 | 内存/DMA | get shape returns copy | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_get_shape_returns_copy`。 | 内存类型、布局、搬运结果或 verifier 行为体现“get shape returns copy”场景。 | `test_get_shape_returns_copy` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-006 | 公开入口 | iteration protocol | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_iteration_protocol`。 | 公开入口在“iteration protocol”场景下可导入、构造、注册或按名称发现。 | `test_iteration_protocol` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-007 | 边界/异常 | getitem errors and slice access | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_getitem_errors_and_slice_access`。 | “getitem errors and slice access”场景按公开错误语义失败或被拒绝。 | `test_getitem_errors_and_slice_access` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-008 | 公开入口 | int setitem converts and checks range | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_int_setitem_converts_and_checks_range`。 | 公开入口在“int setitem converts and checks range”场景下可导入、构造、注册或按名称发现。 | `test_int_setitem_converts_and_checks_range` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-009 | 内存/DMA | slice setitem converts values | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_slice_setitem_converts_values`。 | 内存类型、布局、搬运结果或 verifier 行为体现“slice setitem converts values”场景。 | `test_slice_setitem_converts_values` |
| TC-SYMBOL-VARIABLE-SYMBOL-SHAPE-010 | 边界/异常 | slice setitem rejects invalid inputs | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_slice_setitem_rejects_invalid_inputs`。 | “slice setitem rejects invalid inputs”场景按公开错误语义失败或被拒绝。 | `test_slice_setitem_rejects_invalid_inputs` |
