# core/contracts

## 功能简介

提供 `kernel_gen` 内部可复用的类型、shape、dtype 与 verifier 辅助逻辑，供 `dialect`、`operation`、`symbol_variable` 等模块薄包装复用。错误模板文字统一归属 [`kernel_gen.core.error`](error.md)。

## API 列表

- `raise_verify_error(scene: str, expected: str, *, actual: str = ERROR_ACTUAL, action: str = ERROR_ACTION) -> None`
- `verify_memory_type(value: Attribute, field_name: str, *, scene: str) -> NnMemoryType`
- `verify_i64_attr(attr: IntegerAttr, field_name: str, *, scene: str) -> int`
- `verify_i64_attr_range(attr: IntegerAttr, field_name: str, *, min_value: int, max_value: int, scene: str) -> int`
- `verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool, scene: str) -> int`
- `verify_i64_attr_group(attrs: Sequence[IntegerAttr], *, allow_zero: bool, error_phrase: str, scene: str) -> list[int]`
- `collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None`
- `build_contiguous_stride(shape: Sequence[Attribute]) -> ArrayAttr[Attribute]`
- `dims_equal(lhs: Sequence[Attribute], rhs: Sequence[Attribute]) -> bool`
- `public_dim_values(dims: Sequence[Attribute]) -> list[int | str]`
- `default_stride(shape: SymbolShape) -> SymbolShape`
- `shape_numel(shape: SymbolShape) -> SymbolDim`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/core/contracts.md`](../../spec/core/contracts.md)
- `test`：[`test/core/test_contracts.py`](../../test/core/test_contracts.py)
- `test`：[`test/core/test_error_template.py`](../../test/core/test_error_template.py)
- `功能实现`：[`kernel_gen/core/contracts.py`](../../kernel_gen/core/contracts.py)

## 依赖

- 无额外 spec 依赖。

## API详细说明

### `raise_verify_error(scene: str, expected: str, *, actual: str = ERROR_ACTUAL, action: str = ERROR_ACTION) -> None`

- api：`raise_verify_error(scene: str, expected: str, *, actual: str = ERROR_ACTUAL, action: str = ERROR_ACTION) -> None`
- 参数：
  - `scene`：`scene` 输入值，参与 `raise_verify_error` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `expected`：期望结果文本或对象，用于定义比较基线；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `actual`：实际结果文本或对象，用于和期望结果比较；类型 `str`；默认值 `ERROR_ACTUAL`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `action`：`action` 输入值，参与 `raise_verify_error` 的公开处理流程；类型 `str`；默认值 `ERROR_ACTION`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  raise_verify_error(scene=scene, expected=expected, actual=actual, action=action)
  ```
- 功能说明：执行 `raise_verify_error`。
- 注意事项：按统一错误模板抛出 `VerifyException`；默认 `actual` 与 `action` 文本来自 [`kernel_gen.core.error`](error.md)；调用方必须从 `kernel_gen.core.contracts` 导入，不得回退旧 `common` 包或跨文件调用私有 helper。

### `verify_memory_type(value: Attribute, field_name: str, *, scene: str) -> NnMemoryType`

- api：`verify_memory_type(value: Attribute, field_name: str, *, scene: str) -> NnMemoryType`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `field_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `scene`：`scene` 输入值，参与 `verify_memory_type` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`NnMemoryType`。
- 使用示例：

  ```python
  result = verify_memory_type(value=value, field_name=field_name, scene=scene)
  ```
- 功能说明：执行 `verify_memory_type`。
- 注意事项：只接受 `NnMemoryType`；校验通过后会触发该类型自身 `verify()`；失败时必须通过 `raise_verify_error(...)` 保持统一 verifier 错误格式。

### `verify_i64_attr(attr: IntegerAttr, field_name: str, *, scene: str) -> int`

- api：`verify_i64_attr(attr: IntegerAttr, field_name: str, *, scene: str) -> int`
- 参数：
  - `attr`：IR attribute，作为 emit、解析、打印或语义判断的输入属性；类型 `IntegerAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `field_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `scene`：`scene` 输入值，参与 `verify_i64_attr` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`int`，表示计数、维度或状态值。
- 使用示例：

  ```python
  result = verify_i64_attr(attr=attr, field_name=field_name, scene=scene)
  ```
- 功能说明：执行 `verify_i64_attr`。
- 注意事项：只接受 i64 `IntegerAttr`；返回属性中的 Python `int` 值；非 i64 输入必须按统一 verifier 错误模板失败。

### `verify_i64_attr_range(attr: IntegerAttr, field_name: str, *, min_value: int, max_value: int, scene: str) -> int`

- api：`verify_i64_attr_range(attr: IntegerAttr, field_name: str, *, min_value: int, max_value: int, scene: str) -> int`
- 参数：
  - `attr`：IR attribute，作为 emit、解析、打印或语义判断的输入属性；类型 `IntegerAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `field_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `min_value`：`min_value` 输入值，参与 `verify_i64_attr_range` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `max_value`：`max_value` 输入值，参与 `verify_i64_attr_range` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `scene`：`scene` 输入值，参与 `verify_i64_attr_range` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`int`，表示计数、维度或状态值。
- 使用示例：

  ```python
  result = verify_i64_attr_range(attr=attr, field_name=field_name, min_value=min_value, max_value=max_value, scene=scene)
  ```
- 功能说明：执行 `verify_i64_attr_range`。
- 注意事项：先按 `verify_i64_attr(...)` 校验 i64，再校验返回值位于闭区间 `[min_value, max_value]`；越界必须按统一 verifier 错误模板失败。

### `verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool, scene: str) -> int`

- api：`verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool, scene: str) -> int`
- 参数：
  - `attr`：IR attribute，作为 emit、解析、打印或语义判断的输入属性；类型 `IntegerAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `field_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `allow_zero`：`allow_zero` 输入值，参与 `verify_i64_attr_value` 的公开处理流程；类型 `bool`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `scene`：`scene` 输入值，参与 `verify_i64_attr_value` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`int`，表示计数、维度或状态值。
- 使用示例：

  ```python
  result = verify_i64_attr_value(attr=attr, field_name=field_name, allow_zero=allow_zero, scene=scene)
  ```
- 功能说明：执行 `verify_i64_attr_value`。
- 注意事项：先按 `verify_i64_attr(...)` 校验 i64；`allow_zero=True` 时允许 `0`，否则必须为正数；非法值必须按统一 verifier 错误模板失败。

### `verify_i64_attr_group(attrs: Sequence[IntegerAttr], *, allow_zero: bool, error_phrase: str, scene: str) -> list[int]`

- api：`verify_i64_attr_group(attrs: Sequence[IntegerAttr], *, allow_zero: bool, error_phrase: str, scene: str) -> list[int]`
- 参数：
  - `attrs`：IR attribute 集合，作为 emit、解析、打印或语义判断的输入属性组；类型 `Sequence[IntegerAttr]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `allow_zero`：`allow_zero` 输入值，参与 `verify_i64_attr_group` 的公开处理流程；类型 `bool`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `error_phrase`：`error_phrase` 输入值，参与 `verify_i64_attr_group` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `scene`：`scene` 输入值，参与 `verify_i64_attr_group` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`list[int]`。
- 使用示例：

  ```python
  result = verify_i64_attr_group(attrs=attrs, allow_zero=allow_zero, error_phrase=error_phrase, scene=scene)
  ```
- 功能说明：执行 `verify_i64_attr_group`。
- 注意事项：逐项校验输入 `attrs` 并统一返回整数列表；任一元素非法时使用 `error_phrase` 作为公开期望短语并按统一 verifier 错误模板失败。

### `collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None`

- api：`collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None`
- 参数：
  - `dims`：维度列表，定义符号形状或内存对象的各轴大小；类型 `Sequence[Attribute]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`list[int] | None`。
- 使用示例：

  ```python
  result = collect_int_dims(dims=dims)
  ```
- 功能说明：执行 `collect_int_dims`。
- 注意事项：仅当所有维度均为 `IntAttr` 时返回整数列表；任一维度非静态整数时返回 `None`，不得抛错替代该分支。

### `build_contiguous_stride(shape: Sequence[Attribute]) -> ArrayAttr[Attribute]`

- api：`build_contiguous_stride(shape: Sequence[Attribute]) -> ArrayAttr[Attribute]`
- 参数：
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `Sequence[Attribute]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ArrayAttr[Attribute]`。
- 使用示例：

  ```python
  result = build_contiguous_stride(shape=shape)
  ```
- 功能说明：构建 `contiguous_stride`。
- 注意事项：只面向静态 shape 生成连续行主序 stride；若 shape 中存在非静态维度，调用方必须先按自身 API 边界处理，不得依赖本接口做动态 stride 推导。

### `dims_equal(lhs: Sequence[Attribute], rhs: Sequence[Attribute]) -> bool`

- api：`dims_equal(lhs: Sequence[Attribute], rhs: Sequence[Attribute]) -> bool`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `Sequence[Attribute]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `Sequence[Attribute]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  result = dims_equal(lhs=lhs, rhs=rhs)
  ```
- 功能说明：执行 `dims_equal`。
- 注意事项：只比较两个维度序列中的公开 `IntAttr` 与 `StringAttr` 值；长度或公开值不一致时返回 `False`，不得抛错替代普通不等分支。

### `public_dim_values(dims: Sequence[Attribute]) -> list[int | str]`

- api：`public_dim_values(dims: Sequence[Attribute]) -> list[int | str]`
- 参数：
  - `dims`：维度列表，定义符号形状或内存对象的各轴大小；类型 `Sequence[Attribute]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`list[int | str]`。
- 使用示例：

  ```python
  result = public_dim_values(dims=dims)
  ```
- 功能说明：执行 `public_dim_values`。
- 注意事项：输出只包含公开可比较的 `int | str`；动态维度必须保持稳定字符串表达，不得暴露内部 attribute 对象。

### `default_stride(shape: SymbolShape) -> SymbolShape`

- api：`default_stride(shape: SymbolShape) -> SymbolShape`
- 参数：
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `SymbolShape`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`SymbolShape`。
- 使用示例：

  ```python
  result = default_stride(shape=shape)
  ```
- 功能说明：执行 `default_stride`。
- 注意事项：按连续行主序生成 `SymbolShape` 默认 stride；输入 shape 的维度表达必须由 `SymbolShape` 自身公开合同承接。

### `shape_numel(shape: SymbolShape) -> SymbolDim`

- api：`shape_numel(shape: SymbolShape) -> SymbolDim`
- 参数：
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `SymbolShape`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`SymbolDim`。
- 使用示例：

  ```python
  result = shape_numel(shape=shape)
  ```
- 功能说明：执行 `shape_numel`。
- 注意事项：返回 `SymbolDim` 元素总数表达式；不得在本接口内引入额外符号化简、范围分析或非 `SymbolDim` 返回类型。


## 额外补充

### 模块级补充

- 旧 `common` 包已退场；调用方必须从 `kernel_gen.core.contracts` 导入本文件 API。
- 统一错误模板文字归属 `kernel_gen.core.error`；本文件不再承载 `ERROR_TEMPLATE`。
- 调用方不得跨文件调用未列入 `API 列表` 的私有 helper。

## 测试

- 测试文件：
  - `test/core/test_contracts.py`
  - `test/core/test_error.py`
  - `test/core/test_error_template.py`
- 执行命令：`pytest -q test/core/test_contracts.py test/core/test_error_template.py`

### 测试目标

- 验证 `spec/core/contracts.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证 Memory/DMA 参数、布局、搬运或 verifier 行为。
- 验证 SymbolDim、shape、stride、axis 或 symbol IR 语义。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CORE-CONTRACTS-001 | 边界/异常 | verify memory type success and failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_verify_memory_type_success_and_failure`。 | “verify memory type success and failure”场景按公开错误语义失败或被拒绝。 | `test_verify_memory_type_success_and_failure` |
| TC-CORE-CONTRACTS-002 | 边界/异常 | verify i64 attr family | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_verify_i64_attr_family`。 | 输出、返回值或状态变化与场景描述一致。 | `test_verify_i64_attr_family` |
| TC-CORE-CONTRACTS-003 | 内存/DMA | collect dims and stride helpers | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_collect_dims_and_stride_helpers`。 | 内存类型、布局、搬运结果或 verifier 行为体现“collect dims and stride helpers”场景。 | `test_collect_dims_and_stride_helpers` |
| TC-CORE-CONTRACTS-004 | 符号语义 | dims equal | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_dims_equal`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“dims equal”场景。 | `test_dims_equal` |
| TC-CORE-CONTRACTS-005 | 公开入口 | public dim values default stride shape numel | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_public_dim_values_default_stride_shape_numel`。 | 公开入口在“public dim values default stride shape numel”场景下可导入、构造、注册或按名称发现。 | `test_public_dim_values_default_stride_shape_numel` |
| TC-CORE-CONTRACTS-006 | 边界/异常 | error module values | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_error_module_values`。 | “error module values”场景按公开错误语义失败或被拒绝。 | `test_error_module_values` |
| TC-CORE-CONTRACTS-007 | 边界/异常 | error kind values | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_error_kind_values`。 | “error kind values”场景按公开错误语义失败或被拒绝。 | `test_error_kind_values` |
| TC-CORE-CONTRACTS-008 | 边界/异常 | error template text values | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_error_template_text_values`。 | “error template text values”场景按公开错误语义失败或被拒绝。 | `test_error_template_text_values` |
| TC-CORE-CONTRACTS-009 | 边界/异常 | kernel code error methods and str | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_code_error_methods_and_str`。 | “kernel code error methods and str”场景按公开错误语义失败或被拒绝。 | `test_kernel_code_error_methods_and_str` |
| TC-CORE-CONTRACTS-010 | 边界/异常 | kernel code error factory | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_code_error_factory`。 | “kernel code error factory”场景按公开错误语义失败或被拒绝。 | `test_kernel_code_error_factory` |
| TC-CORE-CONTRACTS-011 | 边界/异常 | kernel code error string normalization | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_code_error_string_normalization`。 | “kernel code error string normalization”场景按公开错误语义失败或被拒绝。 | `test_kernel_code_error_string_normalization` |
| TC-CORE-CONTRACTS-012 | 边界/异常 | kernel code error rejects unknown kind or module | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_code_error_rejects_unknown_kind_or_module`。 | “kernel code error rejects unknown kind or module”场景按公开错误语义失败或被拒绝。 | `test_kernel_code_error_rejects_unknown_kind_or_module` |
| TC-CORE-CONTRACTS-013 | 边界/异常 | error template literal | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_error_template_literal`。 | “error template literal”场景按公开错误语义失败或被拒绝。 | `test_error_template_literal` |
| TC-CORE-CONTRACTS-014 | 边界/异常 | error template format | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_error_template_format`。 | “error template format”场景按公开错误语义失败或被拒绝。 | `test_error_template_format` |
