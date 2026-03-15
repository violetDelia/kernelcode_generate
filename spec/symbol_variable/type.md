# type.md

用于定义 `python.symbol_variable.type` 模块中的类型枚举与导出边界。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/symbol_variable/type.md`](../../spec/symbol_variable/type.md)
- `test`：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- `功能实现`：[`python/symbol_variable/type.py`](../../python/symbol_variable/type.py)

## 依赖约定

- `enum.Enum`：用于枚举定义。

## 功能边界

- 仅定义 `NumericType` 与 `Farmat` 两个枚举类型。
- 不负责内存对象与包入口导出逻辑。
- 模块不提供工厂函数、转换函数或其他运行时辅助工具。
- 不再兼容旧路径 `symbol_variable.type`。

## 公开导出

- 模块对外暴露：
  - `NumericType`
  - `Farmat`
- 模块应显式定义 `__all__ = ["NumericType", "Farmat"]`。
- `from python.symbol_variable.type import *` 的暴露范围应严格等于 `__all__`。
- `Enum`、`annotations` 或其他实现细节不属于公开导出。

## 功能

### NumericType

功能说明：

- 表示数值类型枚举。

枚举项：

- `Int32 = "int32"`
- `Float32 = "float32"`

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

## 兼容性

- `NumericType.Int32` 与 `NumericType.Float32` 的名称和值保持稳定。
- `Farmat.Norm` 与 `Farmat.CLast` 继续作为 `NCHW` 与 `NHWC` 的别名使用。
- `Farmat` 的 `name` 与 `repr` 行为遵循 Python `Enum` 别名规则。
## 返回与错误

## 返回与错误

### 成功返回

- 导入模块后可访问约定的枚举类型与成员。

### 失败返回

- 若枚举定义缺失或模块导出不完整，导入阶段抛出 `ImportError` 或 `AttributeError`。

## 测试

- 测试文件：[`test/symbol_variable/test_type.py`](../../test/symbol_variable/test_type.py)
- 执行命令：`pytest -q test/symbol_variable/test_type.py`

### 测试目标

- 验证 `NumericType` 枚举项可访问且值稳定。
- 验证 `Farmat.Norm -> NCHW`、`Farmat.CLast -> NHWC`。
- 验证 `Farmat` 别名对象、`name` 与 `repr` 行为稳定。
- 验证模块显式 `__all__` 仅包含 `NumericType` 与 `Farmat`。
- 验证 `import *` 仅暴露 `NumericType` 与 `Farmat`，不泄露实现细节。

### 测试标准

- 全部测试用例通过，`pytest` 返回码为 0。
- 枚举值、别名关系与导出边界稳定。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TY-001 | 枚举 | NumericType | N/A | 访问 `NumericType.Float32` | 值为 `"float32"` |
| TY-002 | 枚举 | Farmat 映射 | N/A | 访问 `Farmat.Norm`、`Farmat.CLast` | 分别映射到 `NCHW`、`NHWC` |
| TY-003 | 别名 | Farmat | N/A | 检查 `Farmat.Norm is Farmat.NCHW` | 为 `True` |
| TY-004 | 导出 | 模块导出范围 | N/A | 导入 `NumericType`、`Farmat` | 导入成功 |
| TY-005 | 导出 | import * | N/A | 执行 `from python.symbol_variable.type import *` | 仅暴露 `NumericType` 与 `Farmat` |
