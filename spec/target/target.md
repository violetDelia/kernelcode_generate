# target.md

用于定义目标硬件抽象与全局 target 管理。

## 文档信息

- 创建者：`李白`
- 最后一次更改：`李白`
- `spec`：[`spec/target/target.md`](../../spec/target/target.md)
- `test`：[`test/target/test_target.py`](../../test/target/test_target.py)
- `功能实现`：[`target/target.py`](../../target/target.py)

## 依赖约定

- `get_py_file_vars`：[`utils/module_query.py`](../../utils/module_query.py)
- `target/npu/info.py`：[`target/npu/info.py`](../../target/npu/info.py)

## 功能

### Target 构造

功能说明：

- 通过字符串名称加载目标配置。
- 当前支持 `npu`。
- 读取目标配置文件中的变量，初始化 `cluster_num`。

参数约定：

- `str`：目标名称字符串，默认 `"npu"`。

使用示例：

```python
from target.target import Target

t = Target("npu")
```

### 获取 cluster_num

接口：`get_cluster_num()`

功能说明：返回当前目标配置中的 `cluster_num`。

### 全局 Target 管理

接口：

- `get_current_target()`：返回全局 `_Target`。
- `get_target(str)`：构造并返回指定 target。
- `set_target(target)`：设置全局 `_Target`，支持传入 `Target` 或 `str`。

功能说明：

- `_Target` 在模块加载时初始化为 `Target()`。
- `set_target` 若入参为 `str`，内部调用 `get_target`。

## 返回与错误

### 成功返回

- `Target` 构造返回目标实例。
- `get_current_target/get_target` 返回 `Target`。
- `get_cluster_num` 返回 `int`。

### 失败返回

- 当传入未支持的目标字符串时抛出 `ValueError`。
- 目标配置文件缺失或变量缺失时由 `get_py_file_vars` 抛出异常。

## 测试

- 测试文件：[`test/target/test_target.py`](../../test/target/test_target.py)
- 执行命令：`pytest -q test/target/test_target.py`

### 测试目标

- `Target("npu")` 初始化正确。
- `get_cluster_num` 返回配置值。
- `set_target` 支持字符串与实例。
- 未知 target 字符串触发 `ValueError`。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TG-001 | 构造 | npu | info.py 存在 | `Target("npu")` | cluster_num 正确 |
| TG-002 | getter | cluster_num | N/A | `get_cluster_num()` | 返回 int |
| TG-003 | set_target | str | N/A | `set_target("npu")` | 全局更新 |
| TG-004 | 异常 | 未知 target | N/A | `Target("xxx")` | 抛 ValueError |
