# type.md

用于定义 `symbol_variable/type.py` 的导出边界与 `import *` 暴露范围。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)
- `test`：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- `功能实现`：[`symbol_variable/type.py`](../../symbol_variable/type.py)

## 依赖约定

- `enum.Enum`：用于数值类型与格式枚举定义。

## 功能边界

- 仅定义并导出类型枚举，不引入其他模块级工具函数。
- 仅控制 `symbol_variable/type.py` 的导出边界，不扩展到包级 `__init__` 的统一导出策略。
- 不涉及 `Farmat` 命名迁移或重命名方案，仅限定导出范围。

## 导出边界规范

### 显式 __all__

- 模块必须显式定义 `__all__`。
- `__all__` 仅包含需要对外暴露的符号名。
- 当前必须暴露的符号：
  - `NumericType`
  - `Farmat`
- `__all__` 之外的名称在 `from symbol_variable.type import *` 时不可被导入。

### import * 暴露范围

- `from symbol_variable.type import *` 只应导入 `__all__` 中列出的符号。
- 不应通过 `import *` 暴露 `Enum` 或其他实现细节。

## 兼容性

- `NumericType` 与 `Farmat` 的名称与可用性保持不变。
- 仅限制导出范围，不改变枚举值或行为。

## 测试

- 测试文件：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- 执行命令：`pytest -q test/symbol_variable/test_type.py`

### 测试目标

- `__all__` 存在且为可迭代序列。
- `__all__` 精确包含 `NumericType` 与 `Farmat`。
- `import *` 仅导出 `__all__` 中列出的符号。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 导出边界稳定，避免新增符号被误导出。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TY-001 | 导出 | __all__ 定义 | N/A | 读取 `__all__` | 包含 `NumericType` 与 `Farmat` |
| TY-002 | 导出 | import * | N/A | `from symbol_variable.type import *` | 仅导入 `NumericType`、`Farmat` |
| TY-003 | 兼容 | 枚举可用 | N/A | 访问 `NumericType.Float32` | 正常可用 |
