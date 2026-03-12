# generate_get_set.md

用于生成类的 getter/setter 方法，提供可选的自定义 get/set 行为。

## 文档信息

- 创建者：`李白`
- 最后一次更改：`李白`
- `spec`：[`spec/utils/generate_get_set.md`](../../spec/utils/generate_get_set.md)
- `test`：[`test/utils/test_generate_get_set.py`](../../test/utils/test_generate_get_set.py)
- `功能实现`：[`utils/generate_get_set.py`](../../utils/generate_get_set.py)

## 功能

### GENERATE_GET_SET

功能说明：

- 枚举占位，包含 `NOT_GENERATE` 与 `PLACE_HOLDER`。

### generate_get_set

接口：`generate_get_set(map, specified_get={}, specified_set={})`

功能说明：

- 返回类装饰器，为类的私有属性生成 `get_xxx`/`set_xxx` 方法。
- `map` 映射属性名到纯名称（如 `_name` -> `name`）。
- `specified_get`/`specified_set` 可提供自定义 get/set；若值为 `None` 则不生成对应方法。

参数约定：

- `map`：`dict[str, str]`
- `specified_get`：`dict[str, callable | None]`
- `specified_set`：`dict[str, callable | None]`

使用示例：

```python
from utils.generate_get_set import generate_get_set

@generate_get_set({"_x": "x"})
class Foo:
    def __init__(self):
        self._x = 1
```

注意事项：

- 默认 setter 会在赋值后进行类型一致性校验（实现中使用 `isinstance` 与原值比对）。
- 自定义 setter 逻辑由 `specified_set` 提供；实现路径存在对映射/可调用的调用细节限制。

## 返回与错误

### 成功返回

- 返回装饰后的类。

### 失败返回

- 非类对象将触发断言错误。
- setter 类型检查失败会回滚并抛 `TypeError`。
- 自定义 setter/getter 不符合实现调用方式时会触发运行时错误。

## 测试

- 测试文件：[`test/utils/test_generate_get_set.py`](../../test/utils/test_generate_get_set.py)
- 执行命令：`pytest -q test/utils/test_generate_get_set.py`

### 测试目标

- 生成 get/set 方法的存在性。
- `specified_get/ specified_set` 的生效路径。
- setter 类型校验与回滚行为。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| GS-001 | 生成 | 默认 | N/A | 装饰类 | get/set 存在 |
| GS-002 | 禁用 | not_get | specified_get= None | 装饰类 | 不生成 getter |
| GS-003 | 校验 | 类型不一致 | 初始值与新值类型不同 | set_xxx | 抛 TypeError |
