# core/config

## 功能简介

- 定义项目级公共配置底座，统一承载显式公开的配置项与稳定读写接口。
- 当前阶段只新增公共配置文件，不替换现有模块里分散的 `config` 传递与读取逻辑。

## API 列表

- `set_target(value: str | None) -> None`
- `get_target() -> str | None`
- `set_reject_external_values(value: bool) -> None`
- `get_reject_external_values() -> bool`
- `set_allow_python_callee_calls(value: bool) -> None`
- `get_allow_python_callee_calls() -> bool`

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/core/config.md`](../../spec/core/config.md)
- `test`：[`test/core/test_config.py`](../../test/core/test_config.py)
- `功能实现`：[`kernel_gen/core/config.py`](../../kernel_gen/core/config.py)

## 依赖

- 无

## 公开接口

## 配置项说明

### `target`

设置说明：

- 用于显式声明当前调用链预期使用的目标名称。
- 推荐值示例：`cpu`、`npu_demo`。
- 传入 `None` 表示清空当前显式目标，让后续调用方自行决定默认目标或继续保持未指定状态。

示例：

```python
from kernel_gen.core.config import get_target, set_target

set_target("npu_demo")
assert get_target() == "npu_demo"

set_target(None)
assert get_target() is None
```

### `reject_external_values`

设置说明：

- 用于显式声明是否拒绝外部值注入。
- 设为 `True` 时，后续接入此配置的调用方应把未显式声明来源的外部值视为非法输入。
- 设为 `False` 时，表示当前未开启这条严格限制。

示例：

```python
from kernel_gen.core.config import (
    get_reject_external_values,
    set_reject_external_values,
)

set_reject_external_values(True)
assert get_reject_external_values() is True

set_reject_external_values(False)
assert get_reject_external_values() is False
```

### `allow_python_callee_calls`

设置说明：

- 用于显式声明是否允许 Python callee 调用路径。
- 设为 `True` 时，后续接入此配置的调用方可放开 Python 函数调用逻辑。
- 设为 `False` 时，表示当前未放开该路径。

示例：

```python
from kernel_gen.core.config import (
    get_allow_python_callee_calls,
    set_allow_python_callee_calls,
)

set_allow_python_callee_calls(True)
assert get_allow_python_callee_calls() is True

set_allow_python_callee_calls(False)
assert get_allow_python_callee_calls() is False
```

### `set_target(value: str | None) -> None`

功能说明：

- 设置公开 `target` 配置。
- 仅接受 `str` 或 `None`。
- 当你希望一次执行链路明确绑定到某个目标时，应先调用这个接口。

使用示例：

```python
from kernel_gen.core.config import get_target, set_target

set_target("npu_demo")
assert get_target() == "npu_demo"
```

### `get_target() -> str | None`

功能说明：

- 读取公开 `target` 配置。
- 返回 `None` 表示当前没有显式目标设置。

### `set_reject_external_values(value: bool) -> None`

功能说明：

- 设置公开 `reject_external_values` 配置。
- 仅接受 `bool`。
- 该接口只负责设置开关本身，不在当前阶段替换其他模块的实际校验逻辑。

### `get_reject_external_values() -> bool`

功能说明：

- 读取公开 `reject_external_values` 配置。
- `True` 表示当前选择了严格拒绝外部值模式。

### `set_allow_python_callee_calls(value: bool) -> None`

功能说明：

- 设置公开 `allow_python_callee_calls` 配置。
- 仅接受 `bool`。
- 该接口只负责设置开关本身，不在当前阶段替换其他模块的实际调用逻辑。

### `get_allow_python_callee_calls() -> bool`

功能说明：

- 读取公开 `allow_python_callee_calls` 配置。
- `True` 表示当前放开了 Python callee 调用路径。

## 限制与边界

- 本文件当前只定义公共配置底座，不负责替换现有模块里的 `config` 字典或读取逻辑。
- 未在本文件 `API 列表` 中显式列出的配置项，都不是公开配置。
- 配置项对外只能通过对应的 `set_xxx/get_xxx` 接口读写，不提供 `dict` 式任意 key 入口。
- `hardware` 不属于公共 `config` 底座职责；这类硬件结构化信息应放在 `target` 侧收口。
- 非公开 helper 仅允许存在于本文件内部，禁止跨文件调用。

## 测试

- 测试文件：[`test/core/test_config.py`](../../test/core/test_config.py)
- 执行命令：`pytest -q test/core/test_config.py`
- 测试目标：
  - 验证 `set_xxx/get_xxx` 公开接口的稳定行为。
  - 验证非法类型输入会稳定失败。
