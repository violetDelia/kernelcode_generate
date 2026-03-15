# package_api.md

用于定义 `symbol_variable/__init__.py` 的包级统一导出策略，并约束顶层导入 API 的兼容性边界。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`规格小队`
- `spec`：[`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
- `test`：[`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
- `功能实现`：[`symbol_variable/__init__.py`](../../symbol_variable/__init__.py)

## 重构目标

- 为 `symbol_variable/__init__.py` 建立明确的包级统一导出策略。
- 统一说明哪些类型属于包级公共入口，减少调用方在多个子模块之间分散导入。
- 明确是否补充导出 `NumericType` 与 `Farmat`，并给出兼容性约束。
- 将包级导出策略限制在“显式命名导入”范围内，不扩展到 `__all__` 细节或 `Farmat` 迁移方案。

## 功能边界

- 仅约束 `symbol_variable/__init__.py` 的显式顶层导出行为。
- 不重命名 `Farmat`，不讨论 `Format` 替代方案，不涉及枚举迁移路线。
- 不规定 `from symbol_variable import *` 的行为细节。
- 不改变 `SymbolDim`、`SymbolShape`、`Memory`、`NumericType`、`Farmat` 的实际定义模块。

## 导出策略

### 统一入口

- `symbol_variable` 顶层包应作为常用符号变量类型的统一导入入口。
- 调用方应可通过 `from symbol_variable import ...` 直接导入以下公共类型：
  - `SymbolDim`
  - `SymbolList`
  - `SymbolShape`
  - `LocalSpaceMeta`
  - `MemorySpace`
  - `Memory`
  - `NumericType`
  - `Farmat`

### NumericType / Farmat 结论

- 本次导出策略要求在 `symbol_variable/__init__.py` 中补充导出 `NumericType` 与 `Farmat`。
- 补充导出属于包级便捷入口扩展，不改变两者的定义位置；其定义模块仍为 `symbol_variable.type`。
- `Memory` 相关调用既可继续使用 `from symbol_variable.type import NumericType, Farmat`，也可使用新的包级导入入口。

### 命名原则

- 包级顶层仅暴露稳定、常用、面向调用方的类型名。
- 顶层导出的命名必须与原类型定义名一致，不引入别名或二次命名。
- 包级导出不应暴露内部辅助函数、私有实现细节或迁移过渡名称。

## 兼容性

- 现有导入路径 `symbol_variable.symbol_dim`、`symbol_variable.symbol_shape`、`symbol_variable.memory`、`symbol_variable.type` 保持可用。
- 现有代码若继续从 `symbol_variable.type` 导入 `NumericType`、`Farmat`，应保持兼容，不要求迁移。
- 新增包级导出后，`from symbol_variable import NumericType, Farmat` 应返回与 `symbol_variable.type` 中完全相同的对象身份。
- 包级新增导出为增量兼容改动，不得影响现有 `Memory`、`SymbolDim`、`SymbolShape` 的导入与使用。

## 使用示例

```python
from symbol_variable import (
    SymbolDim,
    SymbolShape,
    Memory,
    MemorySpace,
    NumericType,
    Farmat,
)

dim = SymbolDim("N")
shape = SymbolShape([dim, 32])
mem = Memory(shape, NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm)
```

## 返回与错误

### 成功返回

- `from symbol_variable import SymbolDim, SymbolShape, SymbolList, Memory, MemorySpace, LocalSpaceMeta, NumericType, Farmat` 成功导入。
- 导入得到的对象与各自定义模块中的对象保持身份一致。

### 失败返回

- 若顶层未按约定补充导出，显式包级导入缺失名称时触发 `ImportError`。
- 若错误地导出了不同对象副本，会导致身份断言失败，视为实现不符合 spec。

## 测试

- 测试文件：[`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
- 执行命令：`pytest -q test/symbol_variable/test_package_api.py`

### 测试目标

- 验证现有包级导出 `SymbolDim`、`SymbolShape`、`SymbolList`、`Memory`、`MemorySpace`、`LocalSpaceMeta` 可正常导入。
- 验证新增包级导出 `NumericType`、`Farmat` 可正常导入。
- 验证包级导入得到的 `NumericType`、`Farmat` 与 `symbol_variable.type` 中的定义对象身份一致。
- 验证补充导出 `NumericType`、`Farmat` 后，不影响 `Memory` 等现有顶层导入与构造使用。
- 验证旧路径 `from symbol_variable.type import NumericType, Farmat` 继续可用。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 明确覆盖“现有导出保持不变”和“新增导出可用”两类兼容性要求。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| PA-001 | 导出 | 现有公共类型 | N/A | `from symbol_variable import SymbolDim, SymbolShape, SymbolList, Memory, MemorySpace, LocalSpaceMeta` | 导入成功 |
| PA-002 | 导出 | 新增顶层枚举 | N/A | `from symbol_variable import NumericType, Farmat` | 导入成功 |
| PA-003 | 兼容 | 枚举身份一致 | N/A | 比较顶层导入与 `symbol_variable.type` 定义 | `is` 为 True |
| PA-004 | 兼容 | 旧路径保留 | N/A | `from symbol_variable.type import NumericType, Farmat` | 导入成功 |
| PA-005 | 集成 | 顶层导入后构造 Memory | N/A | 使用顶层 `Memory/NumericType/Farmat/MemorySpace` 构造对象 | 构造成功，行为不变 |
