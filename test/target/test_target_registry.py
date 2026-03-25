"""target registry tests.

创建者: 我不是牛马
最后一次更改: 我不是牛马

功能说明:
- 覆盖 target registry 的 JSON 加载、冲突校验与 arch op 支持矩阵行为。

使用示例:
- pytest -q test/target/test_target_registry.py

当前覆盖率信息:
- 不再要求覆盖率；本文件以功能测试闭环为准。

覆盖率命令:
- 不再要求覆盖率命令；本文件以功能测试闭环为准。

关联文件:
- 功能实现: kernel_gen/target/registry.py
- Spec 文档: spec/target/registry.md
- 测试文件: test/target/test_target_registry.py
"""

from __future__ import annotations

from pathlib import Path
import json
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.target import registry as target_registry


def _write_target_json(directory: Path, name: str, payload: dict[str, object]) -> Path:
    """写入单个 target JSON 文件。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 在临时目录中生成 `<name>.json` 并写入 payload。

    使用示例:
    - _write_target_json(tmp_path, "gpu", {"name": "gpu"})

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    path = directory / f"{name}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# TC-TGT-001
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 01:38:06 +0800
# 最近一次运行成功时间: 2026-03-26 01:38:06 +0800
# 测试目的: 验证加载合法 target JSON 并注册成功。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_loads_json_specs(tmp_path: Path) -> None:
    _write_target_json(
        tmp_path,
        "gpu_valid",
        {
            "name": "gpu_valid",
            "arch": {
                "supported_ops": ["arch.get_block_id", "arch.get_thread_id"],
                "unsupported_ops": [],
            },
        },
    )
    loaded = target_registry.load_targets(tmp_path)
    assert "gpu_valid" in loaded
    assert target_registry.is_arch_op_supported("gpu_valid", "arch.get_thread_id") is True
    assert target_registry.is_arch_op_supported("gpu_valid", "arch.get_block_num") is False


# TC-TGT-002
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 01:38:06 +0800
# 最近一次运行成功时间: 2026-03-26 01:38:06 +0800
# 测试目的: 验证非法字段、缺失 name 与文件名不匹配被拒绝。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
@pytest.mark.parametrize(
    ("file_name", "payload"),
    [
        ("missing_name", {"arch": {"supported_ops": ["arch.get_block_id"]}}),
        ("name_mismatch", {"name": "other_name"}),
        ("unknown_field", {"name": "unknown_field", "extra": 1}),
        ("invalid_name", {"name": "BadName"}),
        ("invalid_arch", {"name": "invalid_arch", "arch": "bad"}),
    ],
)
def test_target_registry_rejects_invalid_specs(
    tmp_path: Path,
    file_name: str,
    payload: dict[str, object],
) -> None:
    _write_target_json(tmp_path, file_name, payload)
    with pytest.raises(ValueError):
        target_registry.load_targets(tmp_path)


# TC-TGT-003
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 01:38:06 +0800
# 最近一次运行成功时间: 2026-03-26 01:38:06 +0800
# 测试目的: 验证 supported_ops/unsupported_ops 冲突时拒绝注册。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_rejects_conflicting_ops(tmp_path: Path) -> None:
    _write_target_json(
        tmp_path,
        "gpu_conflict",
        {
            "name": "gpu_conflict",
            "arch": {
                "supported_ops": ["arch.get_thread_id"],
                "unsupported_ops": ["arch.get_thread_id"],
            },
        },
    )
    with pytest.raises(ValueError):
        target_registry.load_targets(tmp_path)


# TC-TGT-004
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 01:38:06 +0800
# 最近一次运行成功时间: 2026-03-26 01:38:06 +0800
# 测试目的: 验证 cpu target 默认不支持 arch.get_thread_id。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_cpu_rejects_thread_id() -> None:
    assert target_registry.is_arch_op_supported("cpu", "arch.get_thread_id") is False
