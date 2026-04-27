"""core config tests.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 覆盖 `kernel_gen.core.config` 中公共配置底座的显式 `set_xxx/get_xxx` 接口与类型约束。

API 列表:
- `test_target_round_trip() -> None`
- `test_bool_configs_round_trip() -> None`
- `test_config_setters_reject_invalid_types() -> None`

使用示例:
- pytest -q test/core/test_config.py

关联文件:
- 功能实现: [kernel_gen/core/config.py](../../kernel_gen/core/config.py)
- Spec 文档: [spec/core/config.md](../../spec/core/config.md)
- 测试文件: [test/core/test_config.py](../../test/core/test_config.py)
"""

from __future__ import annotations

import pytest

from kernel_gen.core.config import (
    get_allow_python_callee_calls,
    get_reject_external_values,
    get_target,
    set_allow_python_callee_calls,
    set_reject_external_values,
    set_target,
)


def _reset_common_config() -> None:
    """重置公共配置测试现场。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 在每条测试开始前恢复 `kernel_gen.core.config` 的默认配置状态。

    使用示例:
    - _reset_common_config()
    """

    set_target(None)
    set_reject_external_values(False)
    set_allow_python_callee_calls(False)


@pytest.fixture(autouse=True)
def _reset_config_fixture() -> None:
    """为每条测试自动重置公共配置现场。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 保证测试之间不会互相污染公共配置状态。

    使用示例:
    - pytest -q test/core/test_config.py
    """

    _reset_common_config()
    yield
    _reset_common_config()


# CCFG-001
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 target 配置通过公开 set/get 接口稳定往返。
# 使用示例: pytest -q test/core/test_config.py -k test_target_round_trip
# 对应功能实现文件路径: kernel_gen/core/config.py
# 对应 spec 文件路径: spec/core/config.md
# 对应测试文件路径: test/core/test_config.py
def test_target_round_trip() -> None:
    set_target("npu_demo")
    assert get_target() == "npu_demo"

    set_target(None)
    assert get_target() is None


# CCFG-002
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证两个公开 bool 配置通过显式 set/get 接口稳定往返。
# 使用示例: pytest -q test/core/test_config.py -k test_bool_configs_round_trip
# 对应功能实现文件路径: kernel_gen/core/config.py
# 对应 spec 文件路径: spec/core/config.md
# 对应测试文件路径: test/core/test_config.py
def test_bool_configs_round_trip() -> None:
    set_reject_external_values(True)
    set_allow_python_callee_calls(True)

    assert get_reject_external_values() is True
    assert get_allow_python_callee_calls() is True

    set_reject_external_values(False)
    set_allow_python_callee_calls(False)

    assert get_reject_external_values() is False
    assert get_allow_python_callee_calls() is False


# CCFG-003
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证公开配置 setter 对非法类型输入会稳定失败。
# 使用示例: pytest -q test/core/test_config.py -k test_config_setters_reject_invalid_types
# 对应功能实现文件路径: kernel_gen/core/config.py
# 对应 spec 文件路径: spec/core/config.md
# 对应测试文件路径: test/core/test_config.py
def test_config_setters_reject_invalid_types() -> None:
    with pytest.raises(TypeError, match="target must be str or None"):
        set_target(1)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="reject_external_values must be bool"):
        set_reject_external_values(1)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="allow_python_callee_calls must be bool"):
        set_allow_python_callee_calls(1)  # type: ignore[arg-type]
