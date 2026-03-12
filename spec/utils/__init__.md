# utils __init__.md

用于定义 utils 子包导出内容。

## 文档信息

- 创建者：`李白`
- 最后一次更改：`李白`
- `spec`：[`spec/utils/__init__.md`](../../spec/utils/__init__.md)
- `test`：[`test/utils/test_utils_init.py`](../../test/utils/test_utils_init.py)
- `功能实现`：[`utils/__init__.py`](../../utils/__init__.py)

## 功能

### 导出接口

功能说明：

- 从 `module_query` 导出 `has_callable`、`get_py_file_vars`。
- 从 `immutable_dict` 导出 `ImmutableDict`。
- 从 `generate_get_set` 导出 `generate_get_set`。

使用示例：

```python
from utils import ImmutableDict, has_callable
```

## 返回与错误

- 导出行为无显式错误分支。

## 测试

- 测试文件：[`test/utils/test_utils_init.py`](../../test/utils/test_utils_init.py)
- 执行命令：`pytest -q test/utils/test_utils_init.py`

### 测试目标

- 导出对象存在性。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| UI-001 | 导出 | 主要符号 | N/A | `from utils import ...` | 导入成功 |
