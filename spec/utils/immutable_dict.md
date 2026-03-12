# immutable_dict.md

用于定义不可覆盖/不可删除键的字典类型 `ImmutableDict`。

## 文档信息

- 创建者：`李白`
- 最后一次更改：`李白`
- `spec`：[`spec/utils/immutable_dict.md`](../../spec/utils/immutable_dict.md)
- `test`：[`test/utils/test_immutable_dict.py`](../../test/utils/test_immutable_dict.py)
- `功能实现`：[`utils/immutable_dict.py`](../../utils/immutable_dict.py)

## 功能

### 构造

功能说明：

- 继承 `dict`，初始化后维护 `key_set`。
- `key_set` 初始为空，仅记录后续通过 `__setitem__` 写入的键。

### 写入限制

接口：`__setitem__(key, value)`

功能说明：

- 若 `key` 不在 `key_set`，允许写入并记录。
- 若 `key` 已存在于 `key_set`，抛出 `KeyError("Key already exists!")`。

注意：

- 通过构造函数初始化的键不会自动写入 `key_set`，因此首次覆盖这些键时不会被阻止（实现行为）。

### 删除限制

接口：

- `__delitem__`
- `pop`
- `clear`

功能说明：

- 删除相关操作统一抛出异常。
- `clear_all()` 为唯一允许清空全部键的接口。

## 返回与错误

### 成功返回

- 允许写入时返回 `None`。
- `clear_all()` 返回 `None`。

### 失败返回

- 重复写入抛 `KeyError`。
- 删除类操作抛 `KeyError` 或 `Exception`（实现行为）。

## 测试

- 测试文件：[`test/utils/test_immutable_dict.py`](../../test/utils/test_immutable_dict.py)
- 执行命令：`pytest -q test/utils/test_immutable_dict.py`

### 测试目标

- 首次写入允许，重复写入报错。
- 删除与 pop/clear 抛错。
- `clear_all` 可清空。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| IM-001 | 写入 | 新键 | N/A | `d["a"]=1` | 成功 |
| IM-002 | 写入 | 重复键 | 已写入 a | `d["a"]=2` | 抛 KeyError |
| IM-003 | 删除 | del | 已有键 | `del d["a"]` | 抛 KeyError |
| IM-004 | 清空 | clear_all | 已有键 | `clear_all()` | 成功 |
