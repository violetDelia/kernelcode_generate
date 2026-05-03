"""Project-wide common config definitions.


功能说明:
- 定义项目级公共行为配置底座，统一承载显式公开的 target、dump_dir 配置与稳定读写接口。
- 当前公开配置项及其设置语义如下：
  - `target`：设置当前调用链预期使用的目标名称，例如 `cpu`、`npu_demo`；传 `None` 表示清空显式目标，让后续调用方自行决定默认目标。
  - `dump_dir`：设置 DSL/Pass 诊断产物根目录；传 `None` 表示关闭诊断落盘。
- 外部值拒绝与 Python callee 调用均为固定默认行为，不再作为公开配置项。

配置项说明:
- `target`
  - 设置说明：用于显式绑定当前执行链路的目标名称。
  - 典型值：`cpu`、`npu_demo`。
  - 清空方式：`set_target(None)`。
  - 示例：
    - `set_target("cpu")`
    - `set_target("npu_demo")`
- `dump_dir`
  - 设置说明：用于启用 DSL/Pass 诊断产物落盘。
  - 典型值：`"dump"`、`Path("dump")`。
  - 清空方式：`set_dump_dir(None)` 或 `set_dump_dir("")`。
  - 示例：
    - `set_dump_dir("dump")`
    - `set_dump_dir(Path("dump"))`

API 列表:
- `set_target(value: str | None) -> None`
- `get_target() -> str | None`
- `set_dump_dir(value: str | Path | None) -> None`
- `get_dump_dir() -> Path | None`
- `reset_config() -> None`
- `CoreConfigSnapshot(target: str | None, dump_dir: Path | None)`
- `snapshot_config() -> CoreConfigSnapshot`
- `restore_config(snapshot: CoreConfigSnapshot) -> None`

使用示例:
- from kernel_gen.core.config import get_dump_dir, get_target, set_dump_dir, set_target
- set_target("npu_demo")
- assert get_target() == "npu_demo"
- set_dump_dir("dump")
- assert get_dump_dir() == Path("dump")

关联文件:
- spec: [spec/core/config.md](../../spec/core/config.md)
- test: [test/core/test_config.py](../../test/core/test_config.py)
- 功能实现: [kernel_gen/core/config.py](../../kernel_gen/core/config.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "CoreConfigSnapshot",
    "set_target",
    "get_target",
    "set_dump_dir",
    "get_dump_dir",
    "reset_config",
    "snapshot_config",
    "restore_config",
]

_target: str | None = None
_dump_dir: Path | None = None


@dataclass(frozen=True)
class CoreConfigSnapshot:
    """公开配置快照。


    功能说明:
    - 保存 `kernel_gen.core.config` 中的公开 target 与 dump_dir 配置。
    - 不承载运行时临时状态、解析环境、EmitC 名字表或任意扩展 key。

    使用示例:
    - snapshot = snapshot_config()
    - restore_config(snapshot)
    """

    target: str | None
    dump_dir: Path | None


def set_target(value: str | None) -> None:
    """设置公开 target 配置。


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


def set_dump_dir(value: str | Path | None) -> None:
    """设置公开 dump_dir 配置。


    功能说明:
    - 更新项目公共配置中的 `dump_dir`。
    - 仅接受 `str`、`Path` 或 `None`。
    - 非空时启用 DSL/Pass 诊断产物落盘，具体子目录结构由调用工具定义。
    - 传 `None` 或空字符串表示关闭诊断落盘。

    使用示例:
    - set_dump_dir("dump")
    - assert get_dump_dir() == Path("dump")
    - set_dump_dir(None)
    - assert get_dump_dir() is None
    """

    global _dump_dir
    if value is not None and not isinstance(value, (str, Path)):
        raise TypeError("dump_dir must be str, Path or None")
    if value is None or (isinstance(value, str) and value.strip() == ""):
        _dump_dir = None
        return
    _dump_dir = Path(value)


def get_dump_dir() -> Path | None:
    """读取公开 dump_dir 配置。


    功能说明:
    - 返回当前公共配置中的 `dump_dir` 值。
    - 返回 `None` 表示当前未启用诊断产物落盘。

    使用示例:
    - set_dump_dir("dump")
    - assert get_dump_dir() == Path("dump")
    """

    return _dump_dir


def reset_config() -> None:
    """恢复公开配置默认值。


    功能说明:
    - 将 `target` 与 `dump_dir` 恢复为 `None`。
    - 只影响公开行为配置，不处理任何单次生成状态。

    使用示例:
    - set_target("npu_demo")
    - set_dump_dir("dump")
    - reset_config()
    - assert get_target() is None
    - assert get_dump_dir() is None
    """

    global _target, _dump_dir
    _target = None
    _dump_dir = None


def snapshot_config() -> CoreConfigSnapshot:
    """保存当前公开配置。


    功能说明:
    - 返回不可变 `CoreConfigSnapshot`。
    - 用于工具入口临时设置 target 后恢复调用前配置。

    使用示例:
    - snapshot = snapshot_config()
    - set_target("cpu")
    - restore_config(snapshot)
    """

    return CoreConfigSnapshot(target=_target, dump_dir=_dump_dir)


def restore_config(snapshot: CoreConfigSnapshot) -> None:
    """恢复公开配置快照。


    功能说明:
    - 将 `snapshot_config()` 返回的快照恢复为当前公开配置。
    - 拒绝非 `CoreConfigSnapshot` 入参，避免任意 dict 重新成为公开配置入口。

    使用示例:
    - snapshot = snapshot_config()
    - set_target("npu_demo")
    - restore_config(snapshot)
    """

    if not isinstance(snapshot, CoreConfigSnapshot):
        raise TypeError("snapshot must be CoreConfigSnapshot")
    global _target, _dump_dir
    _target = snapshot.target
    _dump_dir = snapshot.dump_dir
