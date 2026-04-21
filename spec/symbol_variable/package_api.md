# package_api.md

## 功能简介

用于描述 `kernel_gen.symbol_variable.__init__.py` 的包入口导出策略，并给出 `spec/symbol_variable` 的模块职责与测试分层总览。本文档只收口“从哪里导入、包入口暴露什么、哪些边界归包层负责”，不重复定义各对象内部语义。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`大闸蟹`
- `spec`：[`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
- `test`：[`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
- `功能实现`：[`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py)

## 依赖

- [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)：`SymbolDim` 定义。
- [`kernel_gen/symbol_variable/symbol_shape.py`](../../kernel_gen/symbol_variable/symbol_shape.py)：`SymbolList`/`SymbolShape` 定义。
- [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)：`Memory`/`MemorySpace`/`LocalSpaceMeta` 定义。
- [`kernel_gen/symbol_variable/ptr.py`](../../kernel_gen/symbol_variable/ptr.py)：`Ptr` 定义。
- [`kernel_gen/symbol_variable/type.py`](../../kernel_gen/symbol_variable/type.py)：`NumericType`/`Farmat` 定义。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：`SymbolDim` 语义。
- [`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)：`SymbolShape` 语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory` 语义。
- [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md)：`Ptr` 语义。
- [`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)：`NumericType`/`Farmat` 语义。

## 模块职责总览

| 模块 | 当前稳定入口 | 本层负责内容 | 主测试 | 交叉验证 |
|---|---|---|---|---|
| `package_api.md` | `kernel_gen.symbol_variable` | 包入口导入/导出、`__all__`、`import *`、legacy 路径禁用 | [`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py) | N/A |
| `type.md` | `kernel_gen.symbol_variable.type` 与 `kernel_gen.symbol_variable` 重导出 | `NumericType` / `Farmat` 枚举语义与模块级导出边界 | [`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py) | [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py) |
| `symbol_dim.md` | `kernel_gen.symbol_variable.symbol_dim` | 单个整数维度/符号表达与基础算术语义 | [`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py) | [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py) |
| `symbol_shape.md` | `kernel_gen.symbol_variable.symbol_shape` | 形状容器规整、访问、切片赋值与序列化 | [`test/symbol_variable/test_symbol_shape.py`](../../test/symbol_variable/test_symbol_shape.py) | [`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py) |
| `memory.md` | `kernel_gen.symbol_variable.memory` 与 `kernel_gen.symbol_variable` 重导出 | `Memory` / `MemorySpace` / `LocalSpaceMeta` 元信息容器与逐元素算术/比较元数据规则 | [`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)、[`test/symbol_variable/test_memory_operation.py`](../../test/symbol_variable/test_memory_operation.py) | [`expectation/symbol_variable/memory.py`](../../expectation/symbol_variable/memory.py)、[`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py) |
| `ptr.md` | `kernel_gen.symbol_variable.ptr` | `Ptr(dtype)` 的 submodule 公开语义 | [`test/symbol_variable/test_ptr.py`](../../test/symbol_variable/test_ptr.py) | N/A |

## 限制与边界

- 仅定义 `kernel_gen.symbol_variable` 包入口的公开导入与导出边界。
- 仅约束包入口直接暴露哪些对象、`__all__` 包含哪些符号，以及 `import *` 应暴露什么。
- 不定义 `Ptr`、`SymbolDim`、`SymbolShape`、`Memory`、`NumericType`、`Farmat` 的内部行为；这些语义由各自模块 spec 描述。
- 当前包入口不导出 `Ptr`；`Ptr` 的公开语义与导入路径由 [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md) 独立负责。
- 不为旧路径 `symbol_variable` 或其旧子模块提供兼容入口。

## 公开接口

### 包入口导出

功能说明：

- 包入口必须直接导出以下符号：
  - `LocalSpaceMeta`
  - `Memory`
  - `MemorySpace`
  - `NumericType`
  - `Farmat`
  - `SymbolDim`
  - `SymbolList`
  - `SymbolShape`

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable import Memory, NumericType, SymbolDim

dim = SymbolDim("N")
mem = Memory([dim, 32], NumericType.Float32)
```

注意事项：

- `__all__` 必须严格等于上述集合。
- `from kernel_gen.symbol_variable import *` 的暴露结果必须严格等于 `__all__`。
- 包入口不得额外暴露实现细节或未约定名称。
- `Ptr` 当前不是包入口导出成员；若调用方需要 `Ptr`，应走 [`kernel_gen.symbol_variable.ptr`](../../kernel_gen/symbol_variable/ptr.py)。

返回与限制：

- 对外仅暴露约定符号集合。

### 包入口导入

功能说明：

- 调用方应通过 `kernel_gen.symbol_variable` 访问包级公开对象。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable import (
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

注意事项：

- 导入对象可直接用于下游构造、比较与类型判断。

返回与限制：

- 导入成功后可访问全部公开导出对象。

### 子模块对象同一性

功能说明：

- 包入口重新导出的对象必须与子模块中的对象保持身份一致。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable import Memory as PackageMemory
from kernel_gen.symbol_variable.memory import Memory as ModuleMemory

assert PackageMemory is ModuleMemory
```

注意事项：

- 包入口不得重新包装对象。
- 包入口不得导出与子模块不同名但语义重复的新对象。

返回与限制：

- `is` 比较结果为 `True`。

### 子模块保留接口

功能说明：

- 某些对象当前只保留 submodule 入口，不属于包入口导出集合。
- 当前最明确的例子是 `Ptr`：语义由 [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md) 定义，但不经 `kernel_gen.symbol_variable` 重导出。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.symbol_variable.ptr import Ptr
from xdsl.dialects.builtin import f32

ptr = Ptr(f32)
```

注意事项：

- 包入口公开集合以 `__all__` 为准，不因为子模块存在就自动导出。
- `Ptr` 的对象职责边界在 [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md) 中定义。
- 包级 spec 不重复承诺 `Ptr` 与 `Memory` / `SymbolDim` 的对象行为。

返回与限制：

- 包入口必须明确区分“已重导出对象”和“仅子模块可用对象”。

### __all__

功能说明：

- `kernel_gen.symbol_variable.__all__` 必须列出全部且仅有的公开导出符号。

参数说明：

- 无参数。

使用示例：

```python
import kernel_gen.symbol_variable as package_module

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

注意事项：

- 当包入口导出集合发生变更时，必须同步更新 `__all__`。

返回与限制：

- `__all__` 必须与公开导出集合完全一致。

### import *

功能说明：

- `from kernel_gen.symbol_variable import *` 仅暴露 `__all__` 中约定的公开符号。

参数说明：

- 无参数。

使用示例：

```python
namespace = {}
exec("from kernel_gen.symbol_variable import *", {}, namespace)
```

注意事项：

- `Enum`、`typing`、`xdsl` 或其他实现依赖不属于 `import *` 暴露范围。

返回与限制：

- 暴露结果必须严格等于 `__all__`。

### 唯一入口约束

功能说明：

- `kernel_gen.symbol_variable` 是 `symbol_variable` 包级 API 的唯一有效入口。

参数说明：

- 无参数。

使用示例：

```python
import importlib

importlib.import_module("kernel_gen.symbol_variable")
```

注意事项：

- 旧路径 `symbol_variable` 及其旧子模块路径不得作为导入入口存在。

返回与限制：

- 旧路径导入必须抛出 `ModuleNotFoundError`。

## 测试

- 测试文件：[`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
- expectation 入口测试：[`test/symbol_variable/test_expectation_suite.py`](../../test/symbol_variable/test_expectation_suite.py)
- expectation 目录入口：[`expectation/symbol_variable/__main__.py`](../../expectation/symbol_variable/__main__.py)
- 执行命令：`pytest -q test/symbol_variable/test_package_api.py`
- 执行命令：`pytest -q test/symbol_variable/test_expectation_suite.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.symbol_variable`

### 测试目标

- 验证 `kernel_gen.symbol_variable` 顶层导入可用。
- 验证包入口导出的对象与子模块对象身份一致。
- 验证顶层导出的类型可直接参与 `Memory` 构造。
- 验证 `kernel_gen.symbol_variable.__all__` 与公开导出集合一致。
- 验证 `from kernel_gen.symbol_variable import *` 仅暴露约定公开符号。
- 验证旧路径 `symbol_variable` 不可导入。
- 验证旧子模块路径 `symbol_variable.symbol_dim`、`symbol_variable.symbol_shape`、`symbol_variable.memory`、`symbol_variable.type` 不可导入。
- 验证 `expectation.symbol_variable` 目录级入口可运行 `symbol_dim` 与 `memory` 两组公开合同。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 对应测试 |
|---|---|---|---|---|---|---|
| PM-001 | 导入 | 包入口导入 | N/A | `from kernel_gen.symbol_variable import Memory, SymbolDim` | 导入成功 | `test_python_symbol_variable_imports` |
| PM-002 | 错误 | 旧包路径导入 | N/A | `importlib.import_module("symbol_variable")` | 抛 `ModuleNotFoundError` | `test_legacy_import_disabled` |
| PM-003 | 错误 | 旧子模块路径导入 | N/A | `importlib.import_module("symbol_variable.symbol_dim")` 等 | 抛 `ModuleNotFoundError` | `test_legacy_submodule_import_disabled` |
| PM-004 | 导出 | 对象同一性 | N/A | 比较包入口与子模块中的 `Memory`/`SymbolDim` | `is` 为 `True` | `test_python_package_type_exports` |
| PM-005 | 构造 | 顶层导出参与构造 | N/A | `Memory([1, 2], NumericType.Float32, format=Farmat.Norm)` | 构造成功 | `test_package_type_construct_memory` |
| PM-006 | 导出 | `__all__` 边界 | N/A | 读取 `kernel_gen.symbol_variable.__all__` | 严格等于公开导出集合 | `test_python_package_all_boundary` |
| PM-007 | 导出 | `import *` 边界 | N/A | 执行 `from kernel_gen.symbol_variable import *` | 仅暴露公开导出集合 | `test_python_package_import_star_exports_only_public_names` |
| PM-008 | expectation | 目录入口 | N/A | `python -m expectation.symbol_variable` | `symbol_dim` 与 `memory` expectation 全部通过 | `test_symbol_variable_expectation_package_entrypoint` |
