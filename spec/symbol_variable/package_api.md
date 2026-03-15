# package_api.md

用于描述 `python.symbol_variable.__init__.py` 的包入口导出策略，以单文件 spec 方式约束公开 API 与 `__all__`/`import *` 语义。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
- `test`：[`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
- `功能实现`：[`python/symbol_variable/__init__.py`](../../python/symbol_variable/__init__.py)

## 范围与目标

- 定义包级入口暴露的公共类型集合，确保 `python.symbol_variable` 为唯一有效导入入口。
- 约束 `__all__` 与 `import *` 的暴露语义，防止包入口导出出现重复或遗漏。
- 不再兼容旧路径 `symbol_variable.*`。

## 公共导出

- 包入口必须直接导出（并实质上返回）同一对象的：
  - `LocalSpaceMeta`
  - `Memory`
  - `MemorySpace`
  - `NumericType`
  - `Farmat`
  - `SymbolDim`
  - `SymbolList`
  - `SymbolShape`
- `__all__` 严格等于上述集合；`from python.symbol_variable import *` 的结果与 `__all__` 一致。
- 不得额外曝光实现细节、辅助函数或不同命名的导出。

## import 语义

- 推荐呼叫者使用：
  - `from python.symbol_variable import SymbolDim, Memory`
  - `from python.symbol_variable.type import NumericType, Farmat`
- 包入口的导出必须与 `python.symbol_variable.symbol_dim` 等子模块中的对象保持身份一致，即 `is` 比较结果为 `True`。

## 兼容性 & 约束验证

- 包入口导出集合必须在 `test_package_api.py` 中得到验证。
- 当 `python.symbol_variable` 导出集合扩展时，必须同步更新 `__all__` 与 `test_package_api.py`。
- 任何对 `python.symbol_variable` 的 `import *` 都不应曝光 `Enum`、`typing`、`xdsl` 等非约定符号。
- 旧路径 `symbol_variable.*` 不再作为兼容入口提供。

## 测试

- 推荐执行：`pytest -q test/symbol_variable/test_package_api.py`

### 测试目标

- `test_package_api.py` 验证包入口导出集合与 `__all__`、`import *` 行为一致。
- `test_package_api.py` 验证顶层导出的对象身份等价于 `python.symbol_variable.symbol_dim` / `...symbol_shape` / `...memory` 中的实例。

### 测试标准

- 所有测试通过，`pytest` 返回码 0。
- 包入口导出集合与对象一致性明确定义且自动回归。
