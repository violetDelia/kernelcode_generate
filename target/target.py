"""Target implementation.

创建者: 大哥大
最后一次更改: 大哥大

功能说明:
- 提供 Target 类与全局 target 管理。

使用示例:
- t = Target("npu")

关联文件:
- spec: spec/target/target.md
- test: test/target/test_target.py
- 功能实现: target/target.py
"""

from __future__ import annotations

from dataclasses import dataclass

from utils.module_query import get_py_file_vars


@dataclass
class Target:
    name: str = "npu"
    cluster_num: int | None = None

    def __post_init__(self) -> None:
        self._load_target_info(self.name)

    def _load_target_info(self, name: str) -> None:
        if name != "npu":
            raise ValueError(f"Unknown target: {name}")
        info_vars = get_py_file_vars("target/npu/info.py")
        if "cluster_num" not in info_vars:
            raise KeyError("cluster_num not found in target info")
        self.cluster_num = info_vars["cluster_num"]

    def get_cluster_num(self) -> int:
        assert self.cluster_num is not None
        return int(self.cluster_num)


def get_target(name: str) -> Target:
    return Target(name)


def set_target(target: Target | str) -> None:
    global _Target
    if isinstance(target, str):
        _Target = get_target(target)
    else:
        _Target = target


def get_current_target() -> Target:
    return _Target


_Target = Target()
