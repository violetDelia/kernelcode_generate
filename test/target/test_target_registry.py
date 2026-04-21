"""target registry tests.

创建者: 我不是牛马
最后一次更改: 朽木露琪亚

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


def _write_target_txt(directory: Path, name: str, lines: list[str]) -> Path:
    """写入单个 target TXT 文件。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 在临时目录中生成 `<name>.txt` 并写入 lines。

    使用示例:
    - _write_target_txt(tmp_path, "cpu", ["name=cpu"])

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    path = directory / f"{name}.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
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


# TC-TGT-005
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-28 03:22:36 +0800
# 最近一次运行成功时间: 2026-03-28 03:22:36 +0800
# 测试目的: 验证加载合法 target TXT 并读取硬件参数。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_loads_txt_specs(tmp_path: Path) -> None:
    _write_target_txt(
        tmp_path,
        "cpu_txt_valid",
        [
            "name=cpu_txt_valid",
            "arch.supported_ops=arch.get_thread_id,arch.get_block_num",
            "arch.unsupported_ops=",
            "hw.thread_num=8",
            "hw.block_num=1024",
            "hw.tlm1_memory_size=64",
            "hw.tlm2_memory_size=32",
            "hw.tlm3_memory_size=16",
        ],
    )
    loaded = target_registry.load_targets(tmp_path)
    assert "cpu_txt_valid" in loaded
    assert target_registry.is_arch_op_supported("cpu_txt_valid", "arch.get_thread_id") is True
    assert target_registry.get_target_hardware("cpu_txt_valid", "thread_num") == 8
    assert target_registry.get_target_hardware("cpu_txt_valid", "tlm1_memory_size") == 64
    assert target_registry.get_target_hardware("cpu_txt_valid", "tlm2_memory_size") == 32
    assert target_registry.get_target_hardware("cpu_txt_valid", "tlm3_memory_size") == 16
    assert target_registry.get_target_hardware("cpu_txt_valid", "sm_memory_size") is None


# TC-TGT-006
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-28 03:22:36 +0800
# 最近一次运行成功时间: 2026-03-28 03:22:36 +0800
# 测试目的: 验证 json/txt 混合目录可同时加载。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_loads_mixed_formats(tmp_path: Path) -> None:
    _write_target_json(
        tmp_path,
        "gpu_mix",
        {
            "name": "gpu_mix",
            "arch": {"supported_ops": ["arch.get_thread_id"], "unsupported_ops": []},
            "hardware": {"thread_num": 256},
        },
    )
    _write_target_txt(
        tmp_path,
        "cpu_mix",
        [
            "name=cpu_mix",
            "arch.supported_ops=",
            "arch.unsupported_ops=",
            "hw.thread_num=1",
        ],
    )
    loaded = target_registry.load_targets(tmp_path)
    assert set(loaded.keys()) >= {"gpu_mix", "cpu_mix"}
    assert target_registry.get_target_hardware("gpu_mix", "thread_num") == 256
    assert target_registry.get_target_hardware("cpu_mix", "thread_num") == 1


# TC-TGT-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 04:20:32 +0800
# 最近一次运行成功时间: 2026-03-28 04:20:32 +0800
# 测试目的: 验证默认目录 kernel_gen/target/targets 可加载且 cpu.txt 可覆盖内置 cpu。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_loads_default_cpu_directory() -> None:
    default_dir = REPO_ROOT / "kernel_gen" / "target" / "targets"
    assert default_dir.is_dir()
    assert (default_dir / "cpu.txt").is_file()
    assert (default_dir / "npu_demo.txt").is_file()
    loaded = target_registry.load_targets(default_dir)
    assert "cpu" in loaded
    assert "npu_demo" in loaded
    assert loaded["cpu"].arch_supported_ops is None
    assert target_registry.is_arch_op_supported("cpu", "arch.get_thread_id") is False
    assert target_registry.is_arch_op_supported("cpu", "arch.get_block_num") is True
    assert target_registry.get_target_hardware("cpu", "thread_num") == 1
    assert target_registry.is_arch_op_supported("npu_demo", "arch.launch") is True
    assert target_registry.get_target_hardware("npu_demo", "thread_num") == 1


# TC-TGT-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 04:20:32 +0800
# 最近一次运行成功时间: 2026-03-28 04:20:32 +0800
# 测试目的: 验证默认目录重复加载不会触发 cpu 冲突。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_default_directory_idempotent_load() -> None:
    default_dir = REPO_ROOT / "kernel_gen" / "target" / "targets"
    assert default_dir.is_dir()
    target_registry.load_targets(default_dir)
    loaded = target_registry.load_targets(default_dir)
    assert "cpu" in loaded


# TC-TGT-007
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-28 03:22:36 +0800
# 最近一次运行成功时间: 2026-03-28 03:22:36 +0800
# 测试目的: 验证 TXT 未知 key 与非整数硬件值被拒绝。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
@pytest.mark.parametrize(
    ("file_name", "lines"),
    [
        ("bad_key", ["name=bad_key", "arch.supported_ops=", "unknown.key=1"]),
        ("bad_hw", ["name=bad_hw", "arch.supported_ops=", "hw.thread_num=1.5"]),
    ],
)
def test_target_registry_rejects_txt_invalid_fields(
    tmp_path: Path,
    file_name: str,
    lines: list[str],
) -> None:
    _write_target_txt(tmp_path, file_name, lines)
    with pytest.raises(ValueError):
        target_registry.load_targets(tmp_path)


# TC-TGT-008
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-28 03:22:36 +0800
# 最近一次运行成功时间: 2026-03-28 03:22:36 +0800
# 测试目的: 验证 current target 硬件读取行为。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_current_target_hardware() -> None:
    assert target_registry.get_current_target_hardware("thread_num") is None
    spec = target_registry.TargetSpec(
        name="current_hw",
        arch_supported_ops=None,
        arch_unsupported_ops=set(),
        hardware={"thread_num": 4},
    )
    target_registry.register_target(spec)
    target_registry._set_current_target("current_hw")
    try:
        assert target_registry.get_current_target_hardware("thread_num") == 4
        assert target_registry.get_current_target_hardware("sm_memory_size") is None
    finally:
        target_registry._set_current_target(None)


# TC-TGT-011
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 测试目的: 验证 npu_demo 文件化固定 target 的能力矩阵与硬件值可直接查询。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_npu_demo_template() -> None:
    assert target_registry.is_arch_op_supported("npu_demo", "arch.get_block_id") is True
    assert target_registry.is_arch_op_supported("npu_demo", "arch.get_thread_id") is True
    assert target_registry.is_arch_op_supported("npu_demo", "arch.get_thread_num") is True
    assert target_registry.is_arch_op_supported("npu_demo", "arch.get_dynamic_memory") is True

    assert target_registry.get_target_hardware("npu_demo", "block_num") == 1
    assert target_registry.get_target_hardware("npu_demo", "thread_num") == 1
    assert target_registry.get_target_hardware("npu_demo", "subthread_num") == 1
    assert target_registry.get_target_hardware("npu_demo", "sm_memory_size") == 0
    assert target_registry.get_target_hardware("npu_demo", "lm_memory_size") == 0
    assert target_registry.get_target_hardware("npu_demo", "tsm_memory_size") == 24576
    assert target_registry.get_target_hardware("npu_demo", "tlm1_memory_size") == 1024
    assert target_registry.get_target_hardware("npu_demo", "tlm2_memory_size") == 512
    assert target_registry.get_target_hardware("npu_demo", "tlm3_memory_size") == 512


# TC-TGT-011A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 npu_demo 文件化固定 target 同时暴露 analysis 默认参数。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_npu_demo_analysis_defaults() -> None:
    defaults = target_registry.get_target_analysis_defaults("npu_demo")

    assert defaults["path_bandwidth"]["GM->LM"] == 64
    assert defaults["path_bandwidth"]["GM->SM"] == 96
    assert defaults["path_bandwidth"]["GM->TSM"] == 32
    assert defaults["path_bandwidth"]["TSM->TLM"] == 16
    assert defaults["path_latency_ns"]["GM->LM"] == 20
    assert defaults["path_latency_ns"]["GM->SM"] == 18
    assert defaults["path_latency_ns"]["GM->TSM"] == 24
    assert defaults["path_latency_ns"]["TSM->TLM"] == 8
    assert defaults["theoretical_compute"]["scalar"] == 1
    assert defaults["theoretical_compute"]["vector"] == 8
    assert defaults["theoretical_compute"]["tensor"] == 64


# TC-TGT-012
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 测试目的: 验证 npu_demo 对未启用能力与接口域外能力查询固定返回未启用。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_npu_demo_rejects_unsupported_ops() -> None:
    assert target_registry.is_arch_op_supported("npu_demo", "arch.launch_kernel") is False
    assert target_registry.is_arch_op_supported("npu_demo", "arch.unknown") is False
    assert target_registry.is_arch_op_supported("npu_demo", "launch") is False
    assert target_registry.is_arch_op_supported("npu_demo", "barrier") is False


# TC-TGT-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 06:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 06:05:00 +0800
# 测试目的: 验证 npu_demo 内置模板收口为 launch/barrier 已启用且硬件数值表示 capability upper bound。
# 对应功能实现文件路径: kernel_gen/target/registry.py
# 对应 spec 文件路径: spec/target/registry.md
def test_target_registry_npu_demo_supports_launch_and_barrier_caps() -> None:
    assert target_registry.is_arch_op_supported("npu_demo", "arch.launch") is True
    assert target_registry.is_arch_op_supported("npu_demo", "arch.barrier") is True
    assert target_registry.is_arch_op_supported("npu_demo", "arch.launch_kernel") is False
    assert target_registry.is_arch_op_supported("npu_demo", "launch") is False
    assert target_registry.is_arch_op_supported("npu_demo", "barrier") is False

    assert target_registry.get_target_hardware("npu_demo", "block_num") == 1
    assert target_registry.get_target_hardware("npu_demo", "thread_num") == 1
    assert target_registry.get_target_hardware("npu_demo", "subthread_num") == 1
    assert target_registry.get_target_hardware("npu_demo", "sm_memory_size") == 0
    assert target_registry.get_target_hardware("npu_demo", "lm_memory_size") == 0
    assert target_registry.get_target_hardware("npu_demo", "tsm_memory_size") == 24576
    assert target_registry.get_target_hardware("npu_demo", "tlm1_memory_size") == 1024
    assert target_registry.get_target_hardware("npu_demo", "tlm2_memory_size") == 512
    assert target_registry.get_target_hardware("npu_demo", "tlm3_memory_size") == 512
