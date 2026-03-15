# package_api.md

用于描述 `python.symbol_variable.__init__.py` 的包入口导出策略，以单文件 spec 方式约束公开导入 API、`__all__` 与 `import *` 语义。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
- `test`：[`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
- `功能实现`：[`python/symbol_variable/__init__.py`](../../python/symbol_variable/__init__.py)

## 功能边界

- 仅定义 `python.symbol_variable` 包入口的公开导入与导出边界。
- 仅约束包入口直接暴露哪些对象、`__all__` 包含哪些符号，以及 `import *` 应暴露什么。
- 不定义 `SymbolDim`、`SymbolShape`、`Memory`、`NumericType`、`Farmat` 的内部行为；这些语义由各自模块 spec 单独描述。
- 不为旧路径 `symbol_variable` 或其旧子模块提供兼容入口。

## 依赖约定

- `python.symbol_variable.symbol_dim`：导出 `SymbolDim`。
- `python.symbol_variable.symbol_shape`：导出 `SymbolList`、`SymbolShape`。
- `python.symbol_variable.memory`：导出 `LocalSpaceMeta`、`Memory`、`MemorySpace`。
- `python.symbol_variable.type`：导出 `NumericType`、`Farmat`。

## 公开导出

- 包入口必须直接导出以下符号：
  - `LocalSpaceMeta`
  - `Memory`
  - `MemorySpace`
  - `NumericType`
  - `Farmat`
  - `SymbolDim`
  - `SymbolList`
  - `SymbolShape`
- `__all__` 必须严格等于上述集合。
- `from python.symbol_variable import *` 的暴露结果必须严格等于 `__all__`。
- 包入口不得额外暴露实现细节、辅助函数或未约定名称。

使用示例：

```python
from python.symbol_variable import Memory, NumericType, SymbolDim

dim = SymbolDim("N")
mem = Memory([dim, 32], NumericType.Float32)
```

预期结果：

- `Memory`、`NumericType`、`SymbolDim` 可直接从 `python.symbol_variable` 导入。
- 这些对象与各自子模块中的公开对象保持同一身份。

## 导入 API

### 包入口导入

- 调用方应通过 `python.symbol_variable` 访问包级公开对象。

使用示例：

```python
from python.symbol_variable import (
    Farmat,
    LocalSpaceMeta,
    Memory,
    MemorySpace,
    NumericType,
    SymbolDim,
    SymbolList,
    SymbolShape,
)
```

预期结果：

- 上述导入全部成功。
- 导入对象可直接用于下游构造、比较与类型判断。

### 子模块对象同一性

- 包入口重新导出的对象必须与子模块中的对象保持身份一致，即 `is` 比较结果为 `True`。

使用示例：

```python
from python.symbol_variable import Memory as PackageMemory
from python.symbol_variable.memory import Memory as ModuleMemory

assert PackageMemory is ModuleMemory
```

行为约束：

- 包入口不得重新包装对象。
- 包入口不得导出与子模块不同名但语义重复的新对象。

### `__all__`

- `python.symbol_variable.__all__` 必须列出全部且仅有的公开导出符号。

使用示例：

```python
import python.symbol_variable as package_module

assert package_module.__all__ == [
    "Farmat",
    "LocalSpaceMeta",
    "Memory",
    "MemorySpace",
    "NumericType",
    "SymbolDim",
    "SymbolList",
    "SymbolShape",
]
```

行为约束：

- 当包入口导出集合发生变更时，必须同步更新 `__all__`。

### `import *`

- `from python.symbol_variable import *` 仅暴露 `__all__` 中约定的公开符号。

使用示例：

```python
namespace = {}
exec("from python.symbol_variable import *", {}, namespace)

assert sorted(namespace) == [
    "Farmat",
    "LocalSpaceMeta",
    "Memory",
    "MemorySpace",
    "NumericType",
    "SymbolDim",
    "SymbolList",
    "SymbolShape",
]
```

行为约束：

- `Enum`、`typing`、`xdsl` 或其他实现依赖不属于 `import *` 暴露范围。

## 唯一入口约束

- `python.symbol_variable` 是 `symbol_variable` 包级 API 的唯一有效入口。
- 旧路径 `symbol_variable` 不得作为导入入口存在。
- 旧子模块路径不得作为导入入口存在，包括但不限于：
  - `symbol_variable.symbol_dim`
  - `symbol_variable.symbol_shape`
  - `symbol_variable.memory`
  - `symbol_variable.type`

使用示例：

```python
import importlib

importlib.import_module("python.symbol_variable")
```

预期结果：

- 导入成功。

反例示例：

```python
import importlib

importlib.import_module("symbol_variable")
importlib.import_module("symbol_variable.symbol_dim")
```

预期结果：

- 以上旧路径导入均失败，并抛出 `ModuleNotFoundError`。

## 返回与错误

### 成功返回

- `import python.symbol_variable` 成功后，可访问约定的全部公开导出。
- 通过包入口导入的对象与子模块公开对象身份一致。

### 失败返回

- 若包入口漏导出约定符号，导入或属性访问阶段抛出 `ImportError` 或 `AttributeError`。
- 若调用方尝试导入旧路径 `symbol_variable` 或旧子模块路径，抛出 `ModuleNotFoundError`。

## 测试

- 测试文件：[`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
- 执行命令：`pytest -q test/symbol_variable/test_package_api.py`

### 测试目标

- 验证 `python.symbol_variable` 顶层导入可用。
- 验证包入口导出的对象与子模块对象身份一致。
- 验证顶层导出的类型可直接参与 `Memory` 构造。
- 验证 `python.symbol_variable.__all__` 与公开导出集合一致。
- 验证 `from python.symbol_variable import *` 仅暴露约定公开符号。
- 验证旧路径 `symbol_variable` 不可导入。
- 验证旧子模块路径 `symbol_variable.symbol_dim`、`symbol_variable.symbol_shape`、`symbol_variable.memory`、`symbol_variable.type` 不可导入。

### 测试标准

- 所有测试通过，`pytest` 返回码为 0。
- 包入口导出集合、对象一致性、唯一入口约束与错误类型稳定。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| PM-001 | 导入 | 包入口导入 | N/A | `from python.symbol_variable import Memory, SymbolDim` | 导入成功 |
| PM-002 | 导出 | 对象同一性 | N/A | 比较包入口与子模块中的 `Memory`/`SymbolDim` | `is` 为 `True` |
| PM-003 | 构造 | 顶层导出参与构造 | N/A | `Memory([1, 2], NumericType.Float32, format=Farmat.Norm)` | 构造成功 |
| PM-004 | 导出 | `__all__` 边界 | N/A | 读取 `python.symbol_variable.__all__` | 严格等于公开导出集合 |
| PM-005 | 导出 | `import *` 边界 | N/A | 执行 `from python.symbol_variable import *` | 仅暴露公开导出集合 |
| PM-006 | 错误 | 旧包路径导入 | N/A | `importlib.import_module("symbol_variable")` | 抛 `ModuleNotFoundError` |
| PM-007 | 错误 | 旧子模块路径导入 | N/A | `importlib.import_module("symbol_variable.symbol_dim")` 等 | 抛 `ModuleNotFoundError` |
