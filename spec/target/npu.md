# npu.md

用于定义 NPU 目标的静态配置信息。

## 文档信息

- 创建者：`李白`
- 最后一次更改：`李白`
- `spec`：[`spec/target/npu.md`](../../spec/target/npu.md)
- `test`：[`test/target/test_npu_info.py`](../../test/target/test_npu_info.py)
- `功能实现`：[`target/npu/info.py`](../../target/npu/info.py)

## 功能

### cluster_num

功能说明：

- 表示 NPU 集群数量的常量配置。
- 供 `Target` 初始化使用。

当前值：`12`。

使用示例：

```python
from target.npu import info

assert info.cluster_num == 12
```

## 返回与错误

- 常量定义，无运行时错误分支。

## 测试

- 测试文件：[`test/target/test_npu_info.py`](../../test/target/test_npu_info.py)
- 执行命令：`pytest -q test/target/test_npu_info.py`

### 测试目标

- `cluster_num` 存在且值为 `12`。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| NPU-001 | 常量 | cluster_num | N/A | 读取变量 | 值为 12 |
