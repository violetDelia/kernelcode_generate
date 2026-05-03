# symbol_variable/dtype_constants

## 功能简介

兼容导出 `kernel_gen.symbol_variable.type` 中的 dtype family 与 arithmetic promotion 常量。新代码应直接从 `kernel_gen.symbol_variable.type` 导入；本文件不再自维护 dtype 常量。

## API 列表

- `FLOAT_DTYPES: set[NumericType]`
- `ARITHMETIC_DTYPE_ORDER: tuple[NumericType, ...]`
- `ARITHMETIC_DTYPE_RANK: dict[NumericType, int]`
- `INT_DTYPES: set[NumericType]`
- `NN_FLOAT_DTYPES: set[NumericType]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/dtype_constants.md`](../../spec/symbol_variable/dtype_constants.md)
- `test`：[`test/symbol_variable/test_dtype_constants.py`](../../test/symbol_variable/test_dtype_constants.py)
- `功能实现`：[`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py)
- `兼容实现`：[`kernel_gen/symbol_variable/dtype_constants.py`](../../kernel_gen/symbol_variable/dtype_constants.py)

## 依赖

- [`kernel_gen.symbol_variable.type`](../../kernel_gen/symbol_variable/type.py)：提供 `NumericType`、`FLOAT_DTYPES`、`INT_DTYPES`、`ARITHMETIC_DTYPE_ORDER`、`ARITHMETIC_DTYPE_RANK`、`NN_FLOAT_DTYPES` 真源。

## API详细说明

### `FLOAT_DTYPES: set[NumericType]`

- api：`FLOAT_DTYPES: set[NumericType]`
- 参数：无。
- 返回值：`set[NumericType]`，包含 `NumericType.Float16`、`NumericType.BFloat16`、`NumericType.Float32` 与 `NumericType.Float64`。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.dtype_constants import FLOAT_DTYPES
  from kernel_gen.symbol_variable.type import NumericType

  assert NumericType.Float16 in FLOAT_DTYPES
  ```
- 功能说明：兼容导出浮点 dtype 集合。
- 注意事项：仅包含浮点 dtype，不包含 `NumericType.Bool`；该对象必须与 `kernel_gen.symbol_variable.type.FLOAT_DTYPES` 保持同一对象身份。

### `ARITHMETIC_DTYPE_ORDER: tuple[NumericType, ...]`

- api：`ARITHMETIC_DTYPE_ORDER: tuple[NumericType, ...]`
- 参数：无。
- 返回值：`tuple[NumericType, ...]`，按 arithmetic promotion 稳定顺序排列。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.dtype_constants import ARITHMETIC_DTYPE_ORDER

  assert ARITHMETIC_DTYPE_ORDER[0].name == "Int8"
  ```
- 功能说明：兼容导出 arithmetic promotion 的稳定 dtype 顺序。
- 注意事项：顺序必须与 `kernel_gen.symbol_variable.type.ARITHMETIC_DTYPE_ORDER` 保持一致；变更 promotion 规则时必须同步 `Memory` 与 `nn` 相关实现和测试。

### `ARITHMETIC_DTYPE_RANK: dict[NumericType, int]`

- api：`ARITHMETIC_DTYPE_RANK: dict[NumericType, int]`
- 参数：无。
- 返回值：`dict[NumericType, int]`，键集合与 `ARITHMETIC_DTYPE_ORDER` 一致。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.dtype_constants import ARITHMETIC_DTYPE_RANK
  from kernel_gen.symbol_variable.type import NumericType

  assert ARITHMETIC_DTYPE_RANK[NumericType.Float32] > ARITHMETIC_DTYPE_RANK[NumericType.Int32]
  ```
- 功能说明：兼容导出由 `ARITHMETIC_DTYPE_ORDER` 派生的 dtype 优先级映射。
- 注意事项：必须与 `ARITHMETIC_DTYPE_ORDER` 保持一致；不得在本文件自维护独立 rank 字典。

### `INT_DTYPES: set[NumericType]`

- api：`INT_DTYPES: set[NumericType]`
- 参数：无。
- 返回值：`set[NumericType]`，包含 `NumericType.Int8`、`NumericType.Int16`、`NumericType.Int32`、`NumericType.Int64`、`NumericType.Uint8`、`NumericType.Uint16`、`NumericType.Uint32` 与 `NumericType.Uint64`。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.dtype_constants import INT_DTYPES
  from kernel_gen.symbol_variable.type import NumericType

  assert NumericType.Uint32 in INT_DTYPES
  ```
- 功能说明：兼容导出整数 dtype 集合。
- 注意事项：不包含浮点 dtype，不包含 `NumericType.Bool`；该对象必须与 `kernel_gen.symbol_variable.type.INT_DTYPES` 保持同一对象身份。

### `NN_FLOAT_DTYPES: set[NumericType]`

- api：`NN_FLOAT_DTYPES: set[NumericType]`
- 参数：无。
- 返回值：`set[NumericType]`，内容与 `FLOAT_DTYPES` 相同。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.dtype_constants import NN_FLOAT_DTYPES
  from kernel_gen.symbol_variable.type import NumericType

  assert NumericType.BFloat16 in NN_FLOAT_DTYPES
  ```
- 功能说明：兼容导出 `nn` 系列算子约束的浮点 dtype 集合。
- 注意事项：必须与 `FLOAT_DTYPES` 保持一致，并复用 `kernel_gen.symbol_variable.type.FLOAT_DTYPES`；本文件仅做兼容 re-export。

## 测试

- 测试文件：`test/symbol_variable/test_dtype_constants.py`
- 执行命令：`pytest -q test/symbol_variable/test_dtype_constants.py`

### 测试目标

- 验证 `spec/symbol_variable/dtype_constants.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SYMBOL-VARIABLE-DTYPE-CONSTANTS-001 | 公开入口 | 浮点 dtype 集合正确。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `DC-001`。 | 公开入口在“浮点 dtype 集合正确。”场景下可导入、构造、注册或按名称发现。 | `DC-001` |
| TC-SYMBOL-VARIABLE-DTYPE-CONSTANTS-002 | 公开入口 | 整数 dtype 集合正确。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `DC-002`。 | 公开入口在“整数 dtype 集合正确。”场景下可导入、构造、注册或按名称发现。 | `DC-002` |
| TC-SYMBOL-VARIABLE-DTYPE-CONSTANTS-003 | 公开入口 | `NN_FLOAT_DTYPES` 与 `FLOAT_DTYPES` 一致。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `DC-003`。 | 公开入口在“`NN_FLOAT_DTYPES` 与 `FLOAT_DTYPES` 一致。”场景下可导入、构造、注册或按名称发现。 | `DC-003` |
| TC-SYMBOL-VARIABLE-DTYPE-CONSTANTS-004 | 公开入口 | `dtype_constants` 复用 `type.py` 的 dtype family 真源。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `DC-003A`。 | 公开入口在“`dtype_constants` 复用 `type.py` 的 dtype family 真源。”场景下可导入、构造、注册或按名称发现。 | `DC-003A` |
| TC-SYMBOL-VARIABLE-DTYPE-CONSTANTS-005 | 公开入口 | arithmetic dtype 顺序与 rank 映射正确。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `DC-004`。 | 公开入口在“arithmetic dtype 顺序与 rank 映射正确。”场景下可导入、构造、注册或按名称发现。 | `DC-004` |
