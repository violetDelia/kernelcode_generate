"""core config tests.


功能说明:
- 覆盖 `kernel_gen.core.config` 中公共 target、dump_dir 配置底座的显式接口与类型约束。

API 列表:
- `test_target_round_trip() -> None`
- `test_dump_dir_round_trip() -> None`
- `test_config_setters_reject_invalid_types() -> None`
- `test_reset_config_restores_public_defaults() -> None`
- `test_snapshot_and_restore_config_round_trip() -> None`

使用示例:
- pytest -q test/core/test_config.py

关联文件:
- 功能实现: [kernel_gen/core/config.py](../../kernel_gen/core/config.py)
- Spec 文档: [spec/core/config.md](../../spec/core/config.md)
- 测试文件: [test/core/test_config.py](../../test/core/test_config.py)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kernel_gen.core.config import (
    CoreConfigSnapshot,
    get_dump_dir,
    get_target,
    reset_config,
    restore_config,
    set_dump_dir,
    set_target,
    snapshot_config,
)


def _reset_common_config() -> None:
    """重置公共配置测试现场。


    功能说明:
    - 在每条测试开始前恢复 `kernel_gen.core.config` 的默认配置状态。

    使用示例:
    - _reset_common_config()
    """

    reset_config()


@pytest.fixture(autouse=True)
def _reset_config_fixture() -> None:
    """为每条测试自动重置公共配置现场。


    功能说明:
    - 保证测试之间不会互相污染公共配置状态。

    使用示例:
    - pytest -q test/core/test_config.py
    """

    _reset_common_config()
    yield
    _reset_common_config()


# CCFG-001
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


# CCFG-001A
# 测试目的: 验证 dump_dir 配置通过公开 set/get 接口稳定往返。
# 使用示例: pytest -q test/core/test_config.py -k test_dump_dir_round_trip
# 对应功能实现文件路径: kernel_gen/core/config.py
# 对应 spec 文件路径: spec/core/config.md
# 对应测试文件路径: test/core/test_config.py
def test_dump_dir_round_trip(tmp_path: Path) -> None:
    set_dump_dir("dump")
    assert get_dump_dir() == Path("dump")

    set_dump_dir(tmp_path)
    assert get_dump_dir() == tmp_path

    set_dump_dir("")
    assert get_dump_dir() is None

    set_dump_dir(None)
    assert get_dump_dir() is None


# CCFG-002
# 测试目的: 验证公开配置 setter 对非法类型输入会稳定失败。
# 使用示例: pytest -q test/core/test_config.py -k test_config_setters_reject_invalid_types
# 对应功能实现文件路径: kernel_gen/core/config.py
# 对应 spec 文件路径: spec/core/config.md
# 对应测试文件路径: test/core/test_config.py
def test_config_setters_reject_invalid_types() -> None:
    with pytest.raises(TypeError, match="target must be str or None"):
        set_target(1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="dump_dir must be str, Path or None"):
        set_dump_dir(1)  # type: ignore[arg-type]


# CCFG-003
# 测试目的: 验证 reset_config 会恢复公开配置默认值。
# 使用示例: pytest -q test/core/test_config.py -k test_reset_config_restores_public_defaults
# 对应功能实现文件路径: kernel_gen/core/config.py
# 对应 spec 文件路径: spec/core/config.md
# 对应测试文件路径: test/core/test_config.py
def test_reset_config_restores_public_defaults() -> None:
    set_target("npu_demo")
    set_dump_dir("dump")

    reset_config()

    assert get_target() is None
    assert get_dump_dir() is None


# CCFG-004
# 测试目的: 验证 snapshot_config / restore_config 只保存并恢复公开 target 配置。
# 使用示例: pytest -q test/core/test_config.py -k test_snapshot_and_restore_config_round_trip
# 对应功能实现文件路径: kernel_gen/core/config.py
# 对应 spec 文件路径: spec/core/config.md
# 对应测试文件路径: test/core/test_config.py
def test_snapshot_and_restore_config_round_trip() -> None:
    set_target("cpu")
    set_dump_dir("dump")
    snapshot = snapshot_config()

    assert snapshot == CoreConfigSnapshot(target="cpu", dump_dir=Path("dump"))

    reset_config()
    restore_config(snapshot)

    assert get_target() == "cpu"
    assert get_dump_dir() == Path("dump")

    with pytest.raises(TypeError, match="snapshot must be CoreConfigSnapshot"):
        restore_config({"target": "npu_demo", "dump_dir": "dump"})  # type: ignore[arg-type]
