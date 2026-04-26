# common/errors

## 功能简介

提供统一的错误模板字符串，供 `kernel_gen` 各模块生成一致的参数校验与边界错误消息。

## API 列表

- `_ERROR_TEMPLATE`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/common/errors.md`](../../spec/common/errors.md)
- `test`：[`test/common/test_errors.py`](../../test/common/test_errors.py)
- `功能实现`：[`kernel_gen/common/errors.py`](../../kernel_gen/common/errors.py)

## 依赖

- `kernel_gen.symbol_variable.type.NumericType`（仅作为调用方构造错误信息时的上下文，不在本文件定义）

## 公开接口

### `_ERROR_TEMPLATE`

功能说明：

- 提供统一错误模板字符串，保证错误信息字段顺序一致。

参数说明：

- 通过 `str.format` 传入以下字段：
  - `scene(str)`：错误发生场景。
  - `expected(str)`：期望条件。
  - `actual(str)`：实际值或类型。
  - `action(str)`：建议动作。

使用示例：

```python
from kernel_gen.common.errors import _ERROR_TEMPLATE

message = _ERROR_TEMPLATE.format(
    scene="dma.alloc 参数校验",
    expected="shape must be a dimension sequence",
    actual="str",
    action="请按接口约束传参",
)
```

注意事项：

- 模板字符串必须保持为：`"场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"`。
- 仅模板集中到 `common/errors.py`；各模块的 `scene/action` 仍由调用方定义。

返回与限制：

- 返回类型为 `str`；必须包含上述四个字段替换结果。

## 测试

- 测试文件：[`test/common/test_errors.py`](../../test/common/test_errors.py)
- 执行命令：`pytest -q test/common/test_errors.py`
- 测试目标：
  - 验证 `_ERROR_TEMPLATE` 的固定文本与字段顺序。
  - 验证 `.format` 传参后输出可用于错误消息。
- 功能与用例清单：
  - `CE-001`：模板文本保持一致。
  - `CE-002`：字段替换后输出符合预期结构。
