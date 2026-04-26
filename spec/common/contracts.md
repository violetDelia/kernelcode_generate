# common/contracts

## 功能简介

提供 `kernel_gen` 内部可复用的类型、shape、dtype、错误与 verifier 辅助逻辑，供 `dialect`、`operation`、`symbol_variable` 等模块薄包装复用。

## API 列表

- `raise_verify_error(scene: str, expected: str, *, actual: str = "不满足期望", action: str = "请按接口约束传参") -> None`
- `verify_memory_type(value: Attribute, field_name: str, *, scene: str) -> NnMemoryType`
- `verify_i64_attr(attr: IntegerAttr, field_name: str, *, scene: str) -> int`
- `verify_i64_attr_range(attr: IntegerAttr, field_name: str, *, min_value: int, max_value: int, scene: str) -> int`
- `verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool, scene: str) -> int`
- `verify_i64_attr_group(attrs: Sequence[IntegerAttr], *, allow_zero: bool, error_phrase: str, scene: str) -> list[int]`
- `collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None`
- `build_contiguous_stride(shape: Sequence[int]) -> list[int]`
- `dims_equal(lhs: Attribute, rhs: Attribute) -> bool`
- `public_dim_values(shape: SymbolShape) -> list[int | str]`
- `default_stride(shape: SymbolShape) -> SymbolShape`
- `shape_numel(shape: SymbolShape) -> SymbolDim`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/common/contracts.md`](../../spec/common/contracts.md)
- `test`：[`test/common/test_contracts.py`](../../test/common/test_contracts.py)
- `功能实现`：[`kernel_gen/common/contracts.py`](../../kernel_gen/common/contracts.py)

## 依赖

- [`kernel_gen/common/errors.py`](../../kernel_gen/common/errors.py)
- [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)
- [`kernel_gen/symbol_variable/symbol_shape.py`](../../kernel_gen/symbol_variable/symbol_shape.py)
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)（仅在 `verify_memory_type` 运行时延迟导入）

## Helper 边界

- 公开 API 仅包含 `API 列表` 中列出的 12 个函数。
- `_ERROR_TEMPLATE`、`_ERROR_ACTION`、`_ERROR_ACTUAL` 等模块常量属于当前文件内部实现细节，不属于跨文件公开接口。
- 调用方只应通过 `raise_verify_error(...)`、`verify_*`、`collect_*`、`build_*`、`dims_equal(...)`、`public_dim_values(...)`、`default_stride(...)` 与 `shape_numel(...)` 访问本模块能力。

## 公开接口

### `raise_verify_error(scene: str, expected: str, *, actual: str = "不满足期望", action: str = "请按接口约束传参") -> None`

功能说明：

- 按统一错误模板抛出 `VerifyException`。
- 用于各模块保持一致的 verifier 错误格式。

使用示例：

```python
from kernel_gen.common.contracts import raise_verify_error

raise_verify_error("dialect.kernel verifier", "lhs must be nn.memory")
```

### `verify_memory_type(value: Attribute, field_name: str, *, scene: str) -> NnMemoryType`

功能说明：

- 校验输入是否为 `NnMemoryType`。
- 通过后触发 `verify()` 以维持 dialect 既有合同。

使用示例：

```python
from kernel_gen.common.contracts import verify_memory_type

memory_type = verify_memory_type(op.lhs.type, "lhs", scene="dialect.kernel verifier")
```

### `verify_i64_attr(attr: IntegerAttr, field_name: str, *, scene: str) -> int`

功能说明：

- 校验 `IntegerAttr` 是否为 i64。
- 返回属性中的整数值，供上层继续施加边界约束。

使用示例：

```python
from kernel_gen.common.contracts import verify_i64_attr

axis = verify_i64_attr(axis_attr, "axis", scene="dialect.nn verifier")
```

### `verify_i64_attr_range(attr: IntegerAttr, field_name: str, *, min_value: int, max_value: int, scene: str) -> int`

功能说明：

- 校验 i64 属性值是否位于指定闭区间内。

使用示例：

```python
from kernel_gen.common.contracts import verify_i64_attr_range

axis = verify_i64_attr_range(attr, "axis", min_value=-2, max_value=1, scene="dialect.kernel verifier")
```

### `verify_i64_attr_value(attr: IntegerAttr, field_name: str, *, allow_zero: bool, scene: str) -> int`

功能说明：

- 校验 i64 属性是否满足正数或非负数约束。

使用示例：

```python
from kernel_gen.common.contracts import verify_i64_attr_value

kw = verify_i64_attr_value(attr, "kw", allow_zero=False, scene="dialect.nn verifier")
```

### `verify_i64_attr_group(attrs: Sequence[IntegerAttr], *, allow_zero: bool, error_phrase: str, scene: str) -> list[int]`

功能说明：

- 校验一组 i64 属性，并统一返回整数列表。
- 适合 `kw/sw/dw` 这类需要组合校验的场景。

使用示例：

```python
from kernel_gen.common.contracts import verify_i64_attr_group

values = verify_i64_attr_group(attrs, allow_zero=False, error_phrase="kw-sw-dw must be positive", scene="dialect.nn verifier")
```

### `collect_int_dims(dims: Sequence[Attribute]) -> list[int] | None`

功能说明：

- 仅当所有维度均为 `IntAttr` 时返回整数列表。
- 任一维度非静态整数时返回 `None`。

使用示例：

```python
from kernel_gen.common.contracts import collect_int_dims

dims = collect_int_dims(shape.data)
```

### `build_contiguous_stride(shape: Sequence[int]) -> list[int]`

功能说明：

- 根据静态 shape 生成连续行主序 stride。

使用示例：

```python
from kernel_gen.common.contracts import build_contiguous_stride

stride = build_contiguous_stride([2, 3, 4])
```

### `dims_equal(lhs: Attribute, rhs: Attribute) -> bool`

功能说明：

- 比较 `IntAttr` 与 `StringAttr` 的值是否一致。

使用示例：

```python
from kernel_gen.common.contracts import dims_equal

assert dims_equal(IntAttr(2), IntAttr(2))
```

### `public_dim_values(shape: SymbolShape) -> list[int | str]`

功能说明：

- 将 `SymbolShape` 公开为可比较的 `int/str` 序列。
- 动态维度保持 `SymbolDim.get_value()` 的稳定字符串。

使用示例：

```python
from kernel_gen.common.contracts import public_dim_values

values = public_dim_values(shape)
```

### `default_stride(shape: SymbolShape) -> SymbolShape`

功能说明：

- 按连续行主序生成 `SymbolShape` 默认 stride。

使用示例：

```python
from kernel_gen.common.contracts import default_stride

stride = default_stride(shape)
```

### `shape_numel(shape: SymbolShape) -> SymbolDim`

功能说明：

- 计算 `SymbolShape` 的元素总数表达式。

使用示例：

```python
from kernel_gen.common.contracts import shape_numel

numel = shape_numel(shape)
```

## 测试

- 测试文件：[`test/common/test_contracts.py`](../../test/common/test_contracts.py)
- 执行命令：`pytest -q test/common/test_contracts.py`
- 测试目标：
  - 验证公共 verifier helper 的错误与返回合同。
  - 验证 shape/stride/dims 公共计算口径稳定。
- 功能与用例清单：
  - `CC-001`：`verify_memory_type` 的成功与失败路径。
  - `CC-002`：`verify_i64_attr*` 家族的成功与边界路径。
  - `CC-003`：`collect_int_dims` 与 `build_contiguous_stride` 的静态计算结果。
  - `CC-004`：`dims_equal` 的值比较结果。
  - `CC-005`：`public_dim_values` / `default_stride` / `shape_numel` 的公开序列化结果。
