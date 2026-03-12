# module_query.md

用于提供模块反射工具：检查可调用对象与读取 Python 文件变量。

## 文档信息

- 创建者：`李白`
- 最后一次更改：`李白`
- `spec`：[`spec/utils/module_query.md`](../../spec/utils/module_query.md)
- `test`：[`test/utils/test_module_query.py`](../../test/utils/test_module_query.py)
- `功能实现`：[`utils/module_query.py`](../../utils/module_query.py)

## 功能

### has_callable

接口：`has_callable(cls, name)`

功能说明：

- 返回对象 `cls` 是否具备名为 `name` 的可调用属性。

返回值：`bool`。

使用示例：

```python
from utils.module_query import has_callable

has_callable(str, "upper")  # True
```

### get_py_file_vars

接口：`get_py_file_vars(py_file_path)`

功能说明：

- 读取指定 `.py` 文件并执行模块加载。
- 返回文件中所有非 `__` 前缀变量的字典。

参数约定：

- `py_file_path`：`str | Path`

使用示例：

```python
from utils.module_query import get_py_file_vars

vars = get_py_file_vars("/path/to/info.py")
```

注意事项：

- 会执行目标文件，可能产生副作用。

## 返回与错误

### 成功返回

- `has_callable` 返回 `bool`。
- `get_py_file_vars` 返回 `dict[str, Any]`。

### 失败返回

- 文件不存在时抛 `FileNotFoundError`。
- 非 `.py` 文件时抛 `ValueError`。
- 文件执行时异常会向上抛出。

## 测试

- 测试文件：[`test/utils/test_module_query.py`](../../test/utils/test_module_query.py)
- 执行命令：`pytest -q test/utils/test_module_query.py`

### 测试目标

- `has_callable` 正确判断可调用。
- `get_py_file_vars` 能读取变量。
- 文件不存在与后缀错误路径异常。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| MQ-001 | callable | 正常 | N/A | `has_callable(str,"upper")` | True |
| MQ-002 | vars | 读取文件 | 文件存在 | `get_py_file_vars` | 返回 dict |
| MQ-003 | 异常 | 文件缺失 | N/A | `get_py_file_vars(missing)` | 抛 FileNotFoundError |
| MQ-004 | 异常 | 非 .py | N/A | `get_py_file_vars("a.txt")` | 抛 ValueError |
