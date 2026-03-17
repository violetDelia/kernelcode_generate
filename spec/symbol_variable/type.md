# type.md

用于定义基础数据类型枚举 `NumericType` 和张量布局格式枚举 `Farmat`，并约束 `python.symbol_variable.type` 的公开导入边界。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`榕`
- `spec`：[`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)
- `test`：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- `功能实现`：[`python/symbol_variable/type.py`](../../python/symbol_variable/type.py)

## 功能边界

- 仅定义 `NumericType` 与 `Farmat` 两个枚举类型。
- 仅约束 `python.symbol_variable.type` 的公开导入、`__all__` 与 `import *` 边界。
- 不负责内存对象、张量对象或其他模块的运行时语义。
- 不提供工厂函数、转换函数或其他辅助 API。

## 依赖约定

- `enum.Enum`：用于定义枚举。

## 唯一入口约束

- `python.symbol_variable.type` 是该模块 API 的唯一有效入口。
- 旧路径 `symbol_variable.type` 不再兼容。

使用示例：

```python
from python.symbol_variable.type import NumericType, Farmat

dtype = NumericType.Float32
layout = Farmat.Norm
```

预期结果：

- 导入成功。
- `NumericType` 与 `Farmat` 可直接用于构造和比较。

反例示例：

```python
import importlib

importlib.import_module("symbol_variable.type")
```

预期结果：

- 导入失败，并抛出 `ModuleNotFoundError`。

## 公开导出

- 模块对外仅暴露 `NumericType` 与 `Farmat`。
- 模块必须显式定义 `__all__ = ["NumericType", "Farmat"]`。
- `Enum`、`annotations` 等实现细节不属于公开导出。

使用示例：

```python
import python.symbol_variable.type as type_module

assert type_module.__all__ == ["NumericType", "Farmat"]
```

`import *` 示例：

```python
namespace = {}
exec("from python.symbol_variable.type import *", {}, namespace)

assert sorted(namespace) == ["Farmat", "NumericType"]
```

行为约束：

- 当公开符号发生变化时，必须同步更新 `__all__`。
- `from python.symbol_variable.type import *` 的暴露范围必须严格等于 `__all__`。

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

### Farmat

功能说明：

- 表示张量布局格式枚举。
- `NCHW` 与 `NHWC` 是底层布局值。
- `Norm` 与 `CLast` 是公开兼容别名：
  - `Farmat.Norm is Farmat.NCHW`
  - `Farmat.CLast is Farmat.NHWC`

使用示例：

```python
from python.symbol_variable.type import Farmat

assert Farmat.Norm is Farmat.NCHW
assert Farmat.CLast is Farmat.NHWC
```

布局判断示例：

```python
from python.symbol_variable.type import Farmat

layout = Farmat.CLast

assert layout.value == "NHWC"
assert layout.name == "NHWC"
```

别名表现示例：

```python
from python.symbol_variable.type import Farmat

assert repr(Farmat.Norm) == "<Farmat.NCHW: 'NCHW'>"
assert repr(Farmat.CLast) == "<Farmat.NHWC: 'NHWC'>"
```

预期结果：

- `Farmat` 的别名关系、`name` 和 `repr` 行为遵循 Python `Enum` 的别名规则。

## 兼容性

- `NumericType` 的有符号整型、无符号整型和浮点成员名称和值保持稳定。
- `Farmat.Norm` 与 `Farmat.CLast` 保持对 `NCHW` 与 `NHWC` 的别名语义。
- `Farmat` 的 `name` 与 `repr` 行为保持与 Python `Enum` 别名规则一致。

## 返回与错误

### 成功返回

- 导入模块后可访问约定的枚举类型与成员。
- 访问 `__all__` 与执行 `import *` 时，仅返回约定公开符号。

### 失败返回

- 若枚举定义缺失或模块导出不完整，导入阶段抛出 `ImportError` 或 `AttributeError`。
- 若调用方尝试导入旧路径 `symbol_variable.type`，抛出 `ModuleNotFoundError`。

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
