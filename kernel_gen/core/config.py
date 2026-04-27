"""Project-wide common config definitions.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 定义项目级公共配置底座，统一承载显式公开的配置项与稳定读写接口。
- 当前阶段只新增公共配置文件，不替换现有模块里分散的 `config` 传递与读取逻辑。
- 当前公开配置项及其设置语义如下：
  - `target`：设置当前调用链预期使用的目标名称，例如 `cpu`、`npu_demo`；传 `None` 表示清空显式目标，让后续调用方自行决定默认目标。
  - `reject_external_values`：设置是否拒绝外部值注入；为 `True` 时，后续接入此配置的调用方应对未显式声明来源的外部值走严格拒绝逻辑。
  - `allow_python_callee_calls`：设置是否允许 Python callee 调用；为 `True` 时，后续接入此配置的调用方可放开 Python 函数调用路径。

配置项说明:
- `target`
  - 设置说明：用于显式绑定当前执行链路的目标名称。
  - 典型值：`cpu`、`npu_demo`。
  - 清空方式：`set_target(None)`。
  - 示例：
    - `set_target("cpu")`
    - `set_target("npu_demo")`
- `reject_external_values`
  - 设置说明：用于显式声明后续调用链是否要走“严格拒绝外部值”模式。
  - 典型值：`True`、`False`。
  - 示例：
    - `set_reject_external_values(True)`
    - `set_reject_external_values(False)`
- `allow_python_callee_calls`
  - 设置说明：用于显式声明后续调用链是否允许 Python callee 调用路径。
  - 典型值：`True`、`False`。
  - 示例：
    - `set_allow_python_callee_calls(True)`
    - `set_allow_python_callee_calls(False)`

API 列表:
- `set_target(value: str | None) -> None`
- `get_target() -> str | None`
- `set_reject_external_values(value: bool) -> None`
- `get_reject_external_values() -> bool`
- `set_allow_python_callee_calls(value: bool) -> None`
- `get_allow_python_callee_calls() -> bool`

使用示例:
- from kernel_gen.core.config import get_target, set_target
- set_target("npu_demo")
- assert get_target() == "npu_demo"
- from kernel_gen.core.config import get_reject_external_values, set_reject_external_values
- set_reject_external_values(True)
- assert get_reject_external_values() is True

关联文件:
- spec: [spec/core/config.md](../../spec/core/config.md)
- test: [test/core/test_config.py](../../test/core/test_config.py)
- 功能实现: [kernel_gen/core/config.py](../../kernel_gen/core/config.py)
"""

from __future__ import annotations

__all__ = [
    "set_target",
    "get_target",
    "set_reject_external_values",
    "get_reject_external_values",
    "set_allow_python_callee_calls",
    "get_allow_python_callee_calls",
]

_target: str | None = None
_reject_external_values: bool = False
_allow_python_callee_calls: bool = False


def set_target(value: str | None) -> None:
    """设置公开 target 配置。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 更新项目公共配置中的 `target`。
    - 仅接受 `str` 或 `None`。
    - 推荐用于把一次执行链路明确绑定到某个目标，例如把后续 DSL/代码生成流程固定到 `cpu` 或 `npu_demo`。
    - 传 `None` 表示撤销当前显式目标设置，恢复到“未指定目标”的状态。

    使用示例:
    - set_target("cpu")
    - assert get_target() == "cpu"
    - set_target(None)
    - assert get_target() is None
    """

    global _target
    if value is not None and not isinstance(value, str):
        raise TypeError("target must be str or None")
    _target = value


def get_target() -> str | None:
    """读取公开 target 配置。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 返回当前公共配置中的 `target` 值。
    - 返回 `None` 表示当前没有显式目标设置。

    使用示例:
    - set_target("npu_demo")
    - assert get_target() == "npu_demo"
    - set_target(None)
    - assert get_target() is None
    """

    return _target


def set_reject_external_values(value: bool) -> None:
    """设置公开 reject_external_values 配置。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 更新项目公共配置中的 `reject_external_values`。
    - 仅接受 `bool`。
    - 适合在需要严格限制外部值渗入时开启；后续接入此配置的调用方应把 `True` 视作严格模式。

    使用示例:
    - set_reject_external_values(True)
    - assert get_reject_external_values() is True
    - set_reject_external_values(False)
    - assert get_reject_external_values() is False
    """

    global _reject_external_values
    if not isinstance(value, bool):
        raise TypeError("reject_external_values must be bool")
    _reject_external_values = value


def get_reject_external_values() -> bool:
    """读取公开 reject_external_values 配置。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 返回当前公共配置中的 `reject_external_values` 值。
    - `True` 表示当前选择了严格拒绝外部值的模式，`False` 表示未开启该限制。

    使用示例:
    - set_reject_external_values(True)
    - assert get_reject_external_values() is True
    - set_reject_external_values(False)
    - assert get_reject_external_values() is False
    """

    return _reject_external_values


def set_allow_python_callee_calls(value: bool) -> None:
    """设置公开 allow_python_callee_calls 配置。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 更新项目公共配置中的 `allow_python_callee_calls`。
    - 仅接受 `bool`。
    - 适合在 DSL 到 IR 的前端调用链中显式控制是否允许 Python callee 调用路径。

    使用示例:
    - set_allow_python_callee_calls(True)
    - assert get_allow_python_callee_calls() is True
    - set_allow_python_callee_calls(False)
    - assert get_allow_python_callee_calls() is False
    """

    global _allow_python_callee_calls
    if not isinstance(value, bool):
        raise TypeError("allow_python_callee_calls must be bool")
    _allow_python_callee_calls = value


def get_allow_python_callee_calls() -> bool:
    """读取公开 allow_python_callee_calls 配置。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 返回当前公共配置中的 `allow_python_callee_calls` 值。
    - `True` 表示允许 Python callee 调用，`False` 表示当前未放开该路径。

    使用示例:
    - set_allow_python_callee_calls(True)
    - assert get_allow_python_callee_calls() is True
    - set_allow_python_callee_calls(False)
    - assert get_allow_python_callee_calls() is False
    """

    return _allow_python_callee_calls
