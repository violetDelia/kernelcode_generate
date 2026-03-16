# type.md

用于定义 `python.symbol_variable.type` 模块中的类型枚举、公开导出边界与唯一入口约束。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)
- `test`：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- `功能实现`：[`python/symbol_variable/type.py`](../../python/symbol_variable/type.py)

## 功能边界

- 仅定义 `NumericType` 与 `Farmat` 两个枚举类型。
- 仅约束 `python.symbol_variable.type` 的公开导入、`__all__` 与 `import *` 边界。
- 不负责内存对象、包入口导出或其他模块的运行时语义。
- 不提供工厂函数、转换函数或其他运行时辅助工具。

## 依赖约定

- `enum.Enum`：用于枚举定义。

## 唯一入口约束

- `python.symbol_variable.type` 是该模块 API 的唯一有效入口。
- 旧路径 `symbol_variable.type` 不得作为导入入口存在。

使用示例：

```python
from python.symbol_variable.type import NumericType, Farmat
```

预期结果：

- 导入成功。
- `NumericType` 与 `Farmat` 可直接用于下游构造与比较。

反例示例：

```python
import importlib

importlib.import_module("symbol_variable.type")
```

预期结果：

- 导入失败，并抛出 `ModuleNotFoundError`。

## 公开导出

- 模块对外仅暴露：
  - `NumericType`
  - `Farmat`
- 模块必须显式定义 `__all__ = ["NumericType", "Farmat"]`。
- `Enum`、`annotations` 或其他实现细节不属于公开导出。

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

- 当模块公开符号发生变更时，必须同步更新 `__all__`。
- `from python.symbol_variable.type import *` 的暴露范围必须严格等于 `__all__`。

## API

### NumericType

功能说明：

- 表示数值类型枚举。

枚举项：

- `Int32 = "int32"`
- `Float32 = "float32"`

使用示例：

```python
from python.symbol_variable.type import NumericType

assert NumericType.Int32.value == "int32"
assert NumericType.Float32.value == "float32"
```

预期结果：

- 调用方可通过 `NumericType` 访问稳定的数值类型枚举值。

### Farmat

功能说明：

- 表示布局格式枚举。
- `NCHW` 与 `NHWC` 为基础枚举值。
- `Norm` 与 `CLast` 为别名入口。

枚举项与语义：

- `NCHW = "NCHW"`
- `NHWC = "NHWC"`
- `Norm is NCHW`
- `CLast is NHWC`

使用示例：

```python
from python.symbol_variable.type import Farmat

assert Farmat.Norm is Farmat.NCHW
assert Farmat.CLast is Farmat.NHWC
assert Farmat.Norm.name == "NCHW"
```

预期结果：

- `Norm` 与 `CLast` 按别名行为工作。
- `name` 与 `repr` 遵循 Python `Enum` 别名规则。

## 兼容性

- `NumericType.Int32` 与 `NumericType.Float32` 的名称和值保持稳定。
- `Farmat.Norm` 与 `Farmat.CLast` 继续作为 `NCHW` 与 `NHWC` 的别名使用。
- `Farmat` 的 `name` 与 `repr` 行为遵循 Python `Enum` 别名规则。

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

- 验证 `NumericType` 枚举项可访问且值稳定。
- 验证 `Farmat.Norm -> NCHW`、`Farmat.CLast -> NHWC`。
- 验证 `Farmat` 别名对象、`name` 与 `repr` 行为稳定。
- 验证模块显式 `__all__` 仅包含 `NumericType` 与 `Farmat`。
- 验证 `import *` 仅暴露 `NumericType` 与 `Farmat`，不泄露实现细节。
- 验证旧路径 `symbol_variable.type` 不可导入，并抛出 `ModuleNotFoundError`。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 枚举值、别名关系、导出边界与唯一入口约束稳定。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TY-001 | 枚举 | NumericType | N/A | 访问 `NumericType.Float32` | 值为 `"float32"` |
| TY-002 | 枚举 | Farmat 映射 | N/A | 访问 `Farmat.Norm`、`Farmat.CLast` | 分别映射到 `NCHW`、`NHWC` |
| TY-003 | 别名 | Farmat | N/A | 检查 `Farmat.Norm is Farmat.NCHW` | 为 `True` |
| TY-004 | 导出 | `__all__` 边界 | N/A | 读取 `python.symbol_variable.type.__all__` | 严格等于 `["NumericType", "Farmat"]` |
| TY-005 | 导出 | `import *` 边界 | N/A | 执行 `from python.symbol_variable.type import *` | 仅暴露 `NumericType` 与 `Farmat` |
| TY-006 | 错误 | 旧路径导入 | N/A | `importlib.import_module("symbol_variable.type")` | 抛 `ModuleNotFoundError` |
