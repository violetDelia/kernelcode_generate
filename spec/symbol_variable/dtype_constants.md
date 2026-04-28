# symbol_variable/dtype_constants

## 功能简介

兼容导出 `kernel_gen.symbol_variable.type` 中的 dtype family 与 arithmetic promotion 常量。新代码应直接从 `kernel_gen.symbol_variable.type` 导入；本文件不再自维护 dtype 常量。

## API 列表

- `FLOAT_DTYPES`
- `ARITHMETIC_DTYPE_ORDER`
- `ARITHMETIC_DTYPE_RANK`
- `INT_DTYPES`
- `NN_FLOAT_DTYPES`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`榕`
- `spec`：[`spec/symbol_variable/dtype_constants.md`](../../spec/symbol_variable/dtype_constants.md)
- `test`：[`test/symbol_variable/test_dtype_constants.py`](../../test/symbol_variable/test_dtype_constants.py)
- `功能实现`：[`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py)
- `兼容实现`：[`kernel_gen/symbol_variable/dtype_constants.py`](../../kernel_gen/symbol_variable/dtype_constants.py)

## 依赖

- [`kernel_gen.symbol_variable.type`](../../kernel_gen/symbol_variable/type.py)：提供 `NumericType`、`FLOAT_DTYPES`、`INT_DTYPES`、`ARITHMETIC_DTYPE_ORDER`、`ARITHMETIC_DTYPE_RANK`、`NN_FLOAT_DTYPES` 真源。

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
- 该对象必须与 `kernel_gen.symbol_variable.type.FLOAT_DTYPES` 保持同一对象身份；本文件仅做兼容 re-export。

返回与限制：

- 返回类型为 `set[NumericType]`。

### `ARITHMETIC_DTYPE_ORDER`

功能说明：

- 定义 arithmetic promotion 的稳定顺序。
- 该顺序同时供 `Memory` dtype promotion 与 `nn` family dtype promotion 共享。

参数说明：

- `tuple[NumericType, ...]`，顺序为：
  - `NumericType.Int8`
  - `NumericType.Uint8`
  - `NumericType.Int16`
  - `NumericType.Uint16`
  - `NumericType.Int32`
  - `NumericType.Uint32`
  - `NumericType.Int64`
  - `NumericType.Uint64`
  - `NumericType.Float16`
  - `NumericType.BFloat16`
  - `NumericType.Float32`
  - `NumericType.Float64`

使用示例：

```python
from kernel_gen.symbol_variable.dtype_constants import ARITHMETIC_DTYPE_ORDER

assert ARITHMETIC_DTYPE_ORDER[0].name == "Int8"
```

注意事项：

- 顺序是公共合同；若变更 promotion 规则，必须同步更新 `memory` 与 `nn` 相关实现与测试。

返回与限制：

- 返回类型为 `tuple[NumericType, ...]`。

### `ARITHMETIC_DTYPE_RANK`

功能说明：

- 由 `ARITHMETIC_DTYPE_ORDER` 派生的 dtype 优先级映射。
- 用于 `Memory` 与 `nn` family 的 dtype promotion 决议，避免各模块自维护 rank 字典。

参数说明：

- `dict[NumericType, int]`，键与 `ARITHMETIC_DTYPE_ORDER` 一致。

使用示例：

```python
from kernel_gen.symbol_variable.dtype_constants import ARITHMETIC_DTYPE_RANK
from kernel_gen.symbol_variable.type import NumericType

assert ARITHMETIC_DTYPE_RANK[NumericType.Float32] > ARITHMETIC_DTYPE_RANK[NumericType.Int32]
```

注意事项：

- `ARITHMETIC_DTYPE_RANK` 必须与 `ARITHMETIC_DTYPE_ORDER` 保持一致。

返回与限制：

- 返回类型为 `dict[NumericType, int]`。

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
- 该对象必须与 `kernel_gen.symbol_variable.type.INT_DTYPES` 保持同一对象身份。

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
- 该对象必须复用 `kernel_gen.symbol_variable.type.FLOAT_DTYPES`；本文件仅做兼容 re-export。

返回与限制：

- 返回类型为 `set[NumericType]`。

## 测试

- 测试文件：[`test/symbol_variable/test_dtype_constants.py`](../../test/symbol_variable/test_dtype_constants.py)
- 执行命令：`pytest -q test/symbol_variable/test_dtype_constants.py`
- 测试目标：
  - 验证 `FLOAT_DTYPES` 与 `INT_DTYPES` 集合内容。
  - 验证 `NN_FLOAT_DTYPES` 与 `FLOAT_DTYPES` 一致。
  - 验证 `dtype_constants` 中的 dtype family 与 promotion 常量复用 `type.py` 的公开真源。
  - 验证 `ARITHMETIC_DTYPE_ORDER` / `ARITHMETIC_DTYPE_RANK` 的排序与映射关系。
- 功能与用例清单：
  - `DC-001`：浮点 dtype 集合正确。
  - `DC-002`：整数 dtype 集合正确。
  - `DC-003`：`NN_FLOAT_DTYPES` 与 `FLOAT_DTYPES` 一致。
  - `DC-003A`：`dtype_constants` 复用 `type.py` 的 dtype family 真源。
  - `DC-004`：arithmetic dtype 顺序与 rank 映射正确。
