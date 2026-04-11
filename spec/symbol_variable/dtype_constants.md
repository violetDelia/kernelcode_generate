# symbol_variable/dtype_constants

## 功能简介

定义 `NumericType` 的常用 dtype 集合常量，供 `operation` 与 `dialect` 模块共享使用，避免重复定义。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/symbol_variable/dtype_constants.md`](../../spec/symbol_variable/dtype_constants.md)
- `test`：[`test/symbol_variable/test_dtype_constants.py`](../../test/symbol_variable/test_dtype_constants.py)
- `功能实现`：[`kernel_gen/symbol_variable/dtype_constants.py`](../../kernel_gen/symbol_variable/dtype_constants.py)

## 依赖

- [`kernel_gen.symbol_variable.type.NumericType`](../../kernel_gen/symbol_variable/type.py)

## 公开接口

### `FLOAT_DTYPES`

功能说明：

- 统一浮点 dtype 集合。

参数说明：

- `set[NumericType]`，包含：
  - `NumericType.Float16`
  - `NumericType.BFloat16`
  - `NumericType.Float32`
  - `NumericType.Float64`

使用示例：

```python
from kernel_gen.symbol_variable.dtype_constants import FLOAT_DTYPES
from kernel_gen.symbol_variable.type import NumericType

assert NumericType.Float16 in FLOAT_DTYPES
```

注意事项：

- 仅包含浮点 dtype；不包含 `NumericType.Bool`。

返回与限制：

- 返回类型为 `set[NumericType]`。

### `INT_DTYPES`

功能说明：

- 统一整数 dtype 集合。

参数说明：

- `set[NumericType]`，包含：
  - `NumericType.Int8`
  - `NumericType.Int16`
  - `NumericType.Int32`
  - `NumericType.Int64`
  - `NumericType.Uint8`
  - `NumericType.Uint16`
  - `NumericType.Uint32`
  - `NumericType.Uint64`

使用示例：

```python
from kernel_gen.symbol_variable.dtype_constants import INT_DTYPES
from kernel_gen.symbol_variable.type import NumericType

assert NumericType.Uint32 in INT_DTYPES
```

注意事项：

- 不包含浮点 dtype；不包含 `NumericType.Bool`。

返回与限制：

- 返回类型为 `set[NumericType]`。

### `NN_FLOAT_DTYPES`

功能说明：

- `nn` 系列算子约束的浮点 dtype 集合，语义与 `FLOAT_DTYPES` 一致。

参数说明：

- `set[NumericType]`，内容与 `FLOAT_DTYPES` 相同。

使用示例：

```python
from kernel_gen.symbol_variable.dtype_constants import NN_FLOAT_DTYPES
from kernel_gen.symbol_variable.type import NumericType

assert NumericType.BFloat16 in NN_FLOAT_DTYPES
```

注意事项：

- `NN_FLOAT_DTYPES` 与 `FLOAT_DTYPES` 需保持一致，避免出现双重来源。

返回与限制：

- 返回类型为 `set[NumericType]`。

## 测试

- 测试文件：[`test/symbol_variable/test_dtype_constants.py`](../../test/symbol_variable/test_dtype_constants.py)
- 执行命令：`pytest -q test/symbol_variable/test_dtype_constants.py`
- 测试目标：
  - 验证 `FLOAT_DTYPES` 与 `INT_DTYPES` 集合内容。
  - 验证 `NN_FLOAT_DTYPES` 与 `FLOAT_DTYPES` 一致。
- 功能与用例清单：
  - `DC-001`：浮点 dtype 集合正确。
  - `DC-002`：整数 dtype 集合正确。
  - `DC-003`：`NN_FLOAT_DTYPES` 与 `FLOAT_DTYPES` 一致。
