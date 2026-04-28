# core/contracts

## 功能简介

提供 `kernel_gen` 内部可复用的类型、shape、dtype、错误模板与 verifier 辅助逻辑，供 `dialect`、`operation`、`symbol_variable` 等模块薄包装复用。

## API 列表

- `_ERROR_TEMPLATE: str`
- `raise_verify_error(scene: str, expected: str, *, actual: str = "不满足期望", action: str = "请按接口约束传参") -> None`
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

- 创建者：`金铲铲大作战`
- 最后一次更改：`榕`
- `spec`：[`spec/core/contracts.md`](../../spec/core/contracts.md)
- `test`：[`test/common/test_contracts.py`](../../test/common/test_contracts.py)
- `test`：[`test/common/test_errors.py`](../../test/common/test_errors.py)
- `功能实现`：[`kernel_gen/core/contracts.py`](../../kernel_gen/core/contracts.py)

## 公开接口

### `_ERROR_TEMPLATE: str`

功能说明：

- 提供统一错误模板字符串，保证错误信息字段顺序一致。
- 模板固定为：`"场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"`。

使用示例：

```python
from kernel_gen.core.contracts import _ERROR_TEMPLATE

message = _ERROR_TEMPLATE.format(
    scene="dma.alloc 参数校验",
    expected="shape must be a dimension sequence",
    actual="str",
    action="请按接口约束传参",
)
```

### `raise_verify_error(scene: str, expected: str, *, actual: str = "不满足期望", action: str = "请按接口约束传参") -> None`

功能说明：

- 按统一错误模板抛出 `VerifyException`。
- 用于各模块保持一致的 verifier 错误格式。

使用示例：

```python
from kernel_gen.core.contracts import raise_verify_error

raise_verify_error("dialect.kernel verifier", "lhs must be nn.memory")
```

### `verify_memory_type(value: Attribute, field_name: str, *, scene: str) -> NnMemoryType`

功能说明：

- 校验输入是否为 `NnMemoryType`。
- 通过后触发 `verify()` 以维持 dialect 既有合同。

### `verify_i64_attr(attr: IntegerAttr, field_name: str, *, scene: str) -> int`

功能说明：

- 校验 `IntegerAttr` 是否为 i64。
- 返回属性中的整数值，供上层继续施加边界约束。

### `verify_i64_attr_range(attr: IntegerAttr, field_name: str, *, min_value: int, max_value: int, scene: str) -> int`

功能说明：

- 校验 i64 属性值是否位于指定闭区间内。

### `verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool, scene: str) -> int`

功能说明：

- 校验 i64 属性是否满足正数或非负数约束。

### `verify_i64_attr_group(attrs: Sequence[IntegerAttr], *, allow_zero: bool, error_phrase: str, scene: str) -> list[int]`

功能说明：

- 校验一组 i64 属性，并统一返回整数列表。
- 适合 `kw/sw/dw` 这类需要组合校验的场景。

### `collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None`

功能说明：

- 仅当所有维度均为 `IntAttr` 时返回整数列表。
- 任一维度非静态整数时返回 `None`。

### `build_contiguous_stride(shape: Sequence[Attribute]) -> ArrayAttr[Attribute]`

功能说明：

- 根据静态 shape 生成连续行主序 stride。

### `dims_equal(lhs: Sequence[Attribute], rhs: Sequence[Attribute]) -> bool`

功能说明：

- 比较两个维度序列中的 `IntAttr` 与 `StringAttr` 值是否一致。

### `public_dim_values(dims: Sequence[Attribute]) -> list[int | str]`

功能说明：

- 将维度序列公开为可比较的 `int/str` 序列。
- 动态维度保持稳定字符串。

### `default_stride(shape: SymbolShape) -> SymbolShape`

功能说明：

- 按连续行主序生成 `SymbolShape` 默认 stride。

### `shape_numel(shape: SymbolShape) -> SymbolDim`

功能说明：

- 计算 `SymbolShape` 的元素总数表达式。

## 边界

- 旧 `common` 包已退场；调用方必须从 `kernel_gen.core.contracts` 导入本文件 API。
- 不再存在独立错误模板文件；统一错误模板归属 `kernel_gen.core.contracts._ERROR_TEMPLATE`。
- 调用方不得跨文件调用未列入 `API 列表` 的私有 helper。

## 测试

- 执行命令：`pytest -q test/common/test_contracts.py test/common/test_errors.py`
- 测试目标：
  - 验证公共 verifier helper 的错误与返回合同。
  - 验证 shape/stride/dims 公共计算口径稳定。
  - 验证 `_ERROR_TEMPLATE` 的固定文本与字段顺序。
