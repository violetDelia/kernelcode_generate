# type.md

 [immutable]用于定义基础数据类型枚举 `NumericType` 和张量布局格式枚举 `Farmat`。

## [immutable]文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`榕`
- `spec`：[`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)
- `test`：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- `功能实现`：[`python/symbol_variable/type.py`](../../python/symbol_variable/type.py)

## 功能边界

- [immutable]仅定义 `NumericType` 与 `Farmat` 两个枚举类型。
- [immutable]不负责内存对象、张量对象或其他模块的运行时语义。
- [immutable]不提供工厂函数、转换函数或其他辅助 API。

## 依赖约定

- `enum.Enum`：用于定义枚举。
- `python.symbol_variable.type`：作为 `NumericType` 与 `Farmat` 的唯一有效导入入口。

## 目标与非目标

### 目标

- 为数值类型和张量布局格式提供稳定、可枚举、可比较的公开常量集合。
- 明确模块级公开导出边界，包括 `__all__` 与 `import *` 的可见符号。
- 约束 `Farmat` 的别名语义，确保调用方可稳定使用语义化名称 `Norm` 与 `CLast`。

### 非目标

- 不在当前模块中定义 dtype 推导、类型提升、布局转换或字符串解析逻辑。
- 不为旧路径 `symbol_variable.type` 提供兼容层、转发模块或弃用包装。
- 不扩展到量化类型、复数类型、稀疏布局或其他未在当前实现中公开的枚举成员。

## API

### NumericType

功能说明：

- 表示数值类型枚举。
- 当前公开成员仅包括：
  - `Int8 = "int8"`
  - `Int16 = "int16"`
  - `Int32 = "int32"`
  - `Int64 = "int64"`
  - `Uint8 = "uint8"`
  - `Uint16 = "uint16"`
  - `Uint32 = "uint32"`
  - `Uint64 = "uint64"`
  - `Float16 = "float16"`
  - `BFloat16 = "bf16"`
  - `Float32 = "float32"`
  - `Float64 = "float64"`

使用示例：

```python
from python.symbol_variable.type import NumericType

assert NumericType.Int8.value == "int8"
assert NumericType.Int16.value == "int16"
assert NumericType.Int32.value == "int32"
assert NumericType.Int64.value == "int64"
assert NumericType.Uint8.value == "uint8"
assert NumericType.Uint16.value == "uint16"
assert NumericType.Uint32.value == "uint32"
assert NumericType.Uint64.value == "uint64"
assert NumericType.Float16.value == "float16"
assert NumericType.BFloat16.value == "bf16"
assert NumericType.Float32.value == "float32"
assert NumericType.Float64.value == "float64"
assert NumericType.Int32 is not NumericType.Float32
```

成员访问示例：

```python
from python.symbol_variable.type import NumericType

dtype = NumericType.Float16

assert dtype.name == "Float16"
assert dtype.value == "float16"
```

预期结果：

- 调用方可通过 `NumericType` 访问稳定的数值类型标识。
- `NumericType` 成员支持 `is` 与 `==` 比较，语义与标准 `Enum` 一致。

行为约束：

- 成员名称和值必须一一对应，不允许同义别名。
- 当前公开成员分为三组：
  - 有符号整型：`Int8`、`Int16`、`Int32`、`Int64`
  - 无符号整型：`Uint8`、`Uint16`、`Uint32`、`Uint64`
  - 浮点类型：`Float16`、`BFloat16`、`Float32`、`Float64`
- 未在本节列出的 dtype 不属于当前 spec 范围。

### Farmat

功能说明：

- 表示张量布局格式枚举。
- [immutable]当前公开成员包括：
  - `Norm`
  - `CLast`
- [immutable]`Norm` 表示通道维不在最后一维的常见布局别名。
- [immutable]`CLast` 表示通道维位于最后一维的常见布局别名。

## 导出边界

- 模块显式公开导出仅包括 `NumericType` 与 `Farmat`。
- `from python.symbol_variable.type import *` 的结果必须严格受 `__all__` 控制。
- `Enum`、`annotations` 或其他实现细节不属于公开 API。

使用示例：

```python
namespace = {}
exec("from python.symbol_variable.type import *", {}, namespace)

assert sorted(namespace) == ["Farmat", "NumericType"]
```

预期结果：

- 调用方通过 `import *` 仅获得约定的两个公开枚举类型。

## 唯一入口约束

- `python.symbol_variable.type` 是当前模块的唯一有效导入入口。
- 旧路径 `symbol_variable.type` 不提供兼容入口。

使用示例：

```python
import importlib

importlib.import_module("python.symbol_variable.type")
```

预期结果：

- 导入成功。

反例示例：

```python
import importlib

importlib.import_module("symbol_variable.type")
```

预期结果：

- 导入失败，并抛出 `ModuleNotFoundError`。

## 返回与错误

### 成功返回

- 成功导入模块后，调用方可访问 `NumericType` 与 `Farmat` 两个公开枚举。
- 成功访问枚举成员后，可读取 `.name`、`.value`，并参与身份比较。

### 失败返回

- 若调用方导入旧路径 `symbol_variable.type`，抛出 `ModuleNotFoundError`。
- 若调用方访问未定义枚举成员，行为遵循 Python `Enum` 默认规则，抛出 `AttributeError` 或 `KeyError`。

## 兼容性

- `NumericType` 的有符号整型、无符号整型和浮点成员名称和值保持稳定。
- `Farmat` 的 `name` 与 `repr` 行为保持与 Python `Enum` 别名规则一致。
- 模块公开导出边界保持稳定，避免调用方因 `__all__` 漂移而获得额外符号。


## 测试

- 测试文件：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- 执行命令：`pytest -q test/symbol_variable/test_type.py`

### 测试目标

- 验证 `NumericType` 的公开成员、名称和值稳定。
- 验证 `Farmat` 的别名关系以及 `name`、`repr` 等公开行为稳定。
- 验证模块显式 `__all__` 仅包含 `NumericType` 与 `Farmat`。
- 验证 `import *` 仅暴露约定公开符号，不泄露实现细节。
- 验证旧路径 `symbol_variable.type` 不可导入，并抛出 `ModuleNotFoundError`。

### 测试标准

- 对应测试全部通过，`pytest` 返回码为 `0`。
- 枚举值、别名关系、导出边界与唯一入口约束保持一致。

### 测试用例清单

| 用例 ID | 对应测试 | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|---|
| TY-001 | `test_numeric_type_values` | `NumericType` 成员值 | 校验公开 dtype 值稳定 | 已成功导入 `python.symbol_variable.type` | 读取各 `NumericType` 成员的 `.value` | 与约定字符串完全一致 |
| TY-003 | `test_python_type_module_all_boundary` | 模块导出边界 | 校验 `__all__` 内容 | 已成功导入模块对象 | 读取 `python.symbol_variable.type.__all__` | 严格等于 `["NumericType", "Farmat"]` |
| TY-004 | `test_python_type_import_star_exports_only_public_names` | `import *` 暴露范围 | 校验 `import *` 不泄露实现细节 | 已成功导入模块 | 执行 `from python.symbol_variable.type import *` | 仅暴露 `Farmat` 与 `NumericType` |
| TY-005 | `test_numeric_type_member_access` | `NumericType` 成员访问 | 校验成员名称可稳定访问 | 已成功导入 `NumericType` | 读取多个成员的 `.name` | 与约定成员名一致 |
| TY-006 | `test_legacy_type_import_disabled` | 唯一入口约束 | 校验旧路径已禁用 | Python 导入环境已初始化 | 执行 `importlib.import_module("symbol_variable.type")` | 抛出 `ModuleNotFoundError` |
