"""target registry private helper coverage tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `kernel_gen.target.registry` 的私有解析、校验与 registry 状态分支。
- 这些测试用于把 S5 execute / target scoped coverage 缺口收口到可验收状态。

使用示例:
- pytest -q test/target/test_target_registry_private_helpers.py

关联文件:
- 功能实现: kernel_gen/target/registry.py
- Spec 文档: spec/target/registry.md
- 测试文件: test/target/test_target_registry_private_helpers.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kernel_gen.target import registry as target_registry


@pytest.fixture()
def isolated_registry() -> None:
    """隔离 target registry 全局状态。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    功能说明:
    - 在测试前备份 target registry 状态，结束后完整恢复，避免相互污染。

    使用示例:
    - 测试内部可自由修改 `_TARGET_REGISTRY`

    关联文件:
    - 功能实现: kernel_gen/target/registry.py
    - 测试文件: test/target/test_target_registry_private_helpers.py
    """

    registry_snapshot = dict(target_registry._TARGET_REGISTRY)
    current_target_snapshot = target_registry._CURRENT_TARGET
    try:
        yield
    finally:
        target_registry._TARGET_REGISTRY.clear()
        target_registry._TARGET_REGISTRY.update(registry_snapshot)
        target_registry._CURRENT_TARGET = current_target_snapshot


def _write_json(path: Path, payload: object) -> None:
    """写入 JSON 文件辅助函数。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    功能说明:
    - 生成 target registry 私有 helper 测试所需的临时 JSON 文件。

    使用示例:
    - _write_json(tmp_path / "gpu.json", {"name": "gpu"})

    关联文件:
    - 功能实现: kernel_gen/target/registry.py
    - 测试文件: test/target/test_target_registry_private_helpers.py
    """

    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("name", ["", "BadName", "with-dash"])
def test_target_registry_validate_target_name_rejects_invalid_values(name: str) -> None:
    """覆盖 target 名称校验失败路径。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证非法 target 名称会触发 ValueError。

    对应功能实现文件路径: kernel_gen/target/registry.py
    对应 spec 文件路径: spec/target/registry.md
    对应测试文件路径: test/target/test_target_registry_private_helpers.py
    """

    with pytest.raises(ValueError):
        target_registry._validate_target_name(name)


def test_target_registry_validate_helpers_and_payload_parsers() -> None:
    """覆盖 arch / hardware / op parser 的常规与异常分支。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 supported / unsupported / hardware / ops 文本与 JSON 解析分支。

    对应功能实现文件路径: kernel_gen/target/registry.py
    对应 spec 文件路径: spec/target/registry.md
    对应测试文件路径: test/target/test_target_registry_private_helpers.py
    """

    spec = target_registry.TargetSpec("gpu", None, {"arch.get_thread_id"}, {"thread_num": 1})
    target_registry._validate_arch_ops(spec)
    target_registry._validate_op_set({"arch.get_block_id"}, "supported_ops", "gpu")
    target_registry._validate_hardware_map({"thread_num": 1}, "gpu")

    with pytest.raises(TypeError):
        target_registry._validate_arch_ops(
            target_registry.TargetSpec("gpu", ["arch.get_thread_id"], set(), {})
        )
    with pytest.raises(ValueError):
        target_registry._validate_arch_ops(
            target_registry.TargetSpec("gpu", {"arch.get_thread_id"}, {"arch.get_thread_id"}, {})
        )
    with pytest.raises(ValueError):
        target_registry._validate_op_set({1}, "supported_ops", "gpu")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        target_registry._validate_hardware_map({"unknown": 1}, "gpu")

    assert target_registry._parse_ops_list(["arch.get_thread_id"], "supported_ops", "gpu") == {
        "arch.get_thread_id"
    }
    with pytest.raises(ValueError):
        target_registry._parse_ops_list("bad", "supported_ops", "gpu")  # type: ignore[arg-type]

    supported, unsupported = target_registry._parse_arch_payload(
        {"supported_ops": ["arch.get_thread_id"], "unsupported_ops": []},
        "gpu",
    )
    assert supported == {"arch.get_thread_id"}
    assert unsupported == set()
    with pytest.raises(ValueError):
        target_registry._parse_arch_payload({"unknown": []}, "gpu")

    hardware = target_registry._parse_hardware_payload({"thread_num": 2}, "gpu")
    assert hardware["thread_num"] == 2
    with pytest.raises(ValueError):
        target_registry._parse_hardware_payload({"thread_num": "bad"}, "gpu")  # type: ignore[arg-type]

    assert target_registry._parse_ops_text("", "supported_ops", "gpu") == set()
    assert target_registry._parse_ops_text("arch.get_thread_id,arch.get_block_id", "supported_ops", "gpu") == {
        "arch.get_thread_id",
        "arch.get_block_id",
    }
    with pytest.raises(ValueError):
        target_registry._parse_ops_text("arch.get_thread_id,,", "supported_ops", "gpu")


def test_target_registry_branchy_parser_and_registration_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    isolated_registry: None,
) -> None:
    """覆盖 target registry 的额外解析与注册分支。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 parse / register / ensure 的边界分支，补齐 execute / target scoped coverage。

    对应功能实现文件路径: kernel_gen/target/registry.py
    对应 spec 文件路径: spec/target/registry.md
    对应测试文件路径: test/target/test_target_registry_private_helpers.py
    """

    assert target_registry._parse_target_spec({"name": "gpu"}, tmp_path / "gpu.json").name == "gpu"
    with pytest.raises(ValueError):
        target_registry._parse_target_spec({"name": "gpu", "arch": []}, tmp_path / "gpu.json")
    with pytest.raises(ValueError):
        target_registry._parse_target_spec({"name": "gpu", "hardware": []}, tmp_path / "gpu.json")
    with pytest.raises(TypeError):
        target_registry._validate_arch_ops(
            target_registry.TargetSpec("gpu", {"arch.get_thread_id"}, ["arch.get_block_id"], {})  # type: ignore[list-item]
        )
    with pytest.raises(ValueError):
        target_registry._validate_hardware_map({"thread_num": True}, "gpu")
    with pytest.raises(ValueError):
        target_registry._parse_hardware_payload({"unknown": 1}, "gpu")

    bad_txt = tmp_path / "bad.txt"
    bad_txt.write_text("name=gpu\nbadline\n", encoding="utf-8")
    with pytest.raises(ValueError):
        target_registry._parse_target_txt(bad_txt)

    bad_key_txt = tmp_path / "bad_key.txt"
    bad_key_txt.write_text("name=\n", encoding="utf-8")
    with pytest.raises(ValueError):
        target_registry._parse_target_txt(bad_key_txt)

    unknown_hw_txt = tmp_path / "unknown_hw.txt"
    unknown_hw_txt.write_text("name=unknown_hw\nhw.unknown=1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        target_registry._parse_target_txt(unknown_hw_txt)

    empty_ops_txt = tmp_path / "empty_ops.txt"
    empty_ops_txt.write_text("name=empty_ops\narch.supported_ops=arch.get_thread_id,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        target_registry._parse_target_txt(empty_ops_txt)

    target_registry._TARGET_REGISTRY.clear()
    default_cpu = target_registry.TargetSpec(
        "cpu",
        None,
        set(target_registry._DEFAULT_CPU_UNSUPPORTED_OPS),
        dict(target_registry._DEFAULT_CPU_HARDWARE),
    )
    target_registry._TARGET_REGISTRY["cpu"] = default_cpu
    gpu_spec = target_registry.TargetSpec("gpu", None, set(), {})
    target_registry._register_loaded_target(gpu_spec)
    target_registry._register_loaded_target(gpu_spec)

    override_cpu = target_registry.TargetSpec(
        "cpu",
        {"arch.get_block_id"},
        set(target_registry._DEFAULT_CPU_UNSUPPORTED_OPS),
        dict(target_registry._DEFAULT_CPU_HARDWARE),
    )
    target_registry._TARGET_REGISTRY["cpu"] = default_cpu
    target_registry._register_loaded_target(override_cpu)
    assert target_registry._TARGET_REGISTRY["cpu"].arch_supported_ops == {"arch.get_block_id"}

    missing_file = tmp_path / "missing_npu_demo.txt"
    monkeypatch.setattr(target_registry, "_NPU_DEMO_TARGET_FILE", missing_file)
    target_registry._TARGET_REGISTRY.clear()
    with pytest.raises(ValueError):
        target_registry._ensure_npu_demo_target()


def test_target_registry_json_and_txt_parsers_cover_error_paths(tmp_path: Path) -> None:
    """覆盖 JSON / TXT target 解析的错误分支。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 target JSON / TXT 解析的缺失 name、文件名不一致、重复 key 和未知 key 分支。

    对应功能实现文件路径: kernel_gen/target/registry.py
    对应 spec 文件路径: spec/target/registry.md
    对应测试文件路径: test/target/test_target_registry_private_helpers.py
    """

    json_path = tmp_path / "bad.json"
    json_path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        target_registry._read_target_json(json_path)

    _write_json(tmp_path / "array.json", [1, 2, 3])
    with pytest.raises(ValueError):
        target_registry._read_target_json(tmp_path / "array.json")

    data = {"name": "gpu", "arch": {"supported_ops": ["arch.get_thread_id"]}}
    with pytest.raises(ValueError):
        target_registry._parse_target_spec(data, tmp_path / "other.json")

    invalid_name_data = {"name": "BadName"}
    with pytest.raises(ValueError):
        target_registry._parse_target_spec(invalid_name_data, tmp_path / "BadName.json")

    txt_path = tmp_path / "gpu.txt"
    txt_path.write_text("name=gpu\nname=gpu2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        target_registry._parse_target_txt(txt_path)

    txt_path = tmp_path / "gpu2.txt"
    txt_path.write_text("name=gpu2\nunknown.key=1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        target_registry._parse_target_txt(txt_path)

    txt_path = tmp_path / "gpu3.txt"
    txt_path.write_text("arch.supported_ops=\n", encoding="utf-8")
    with pytest.raises(ValueError):
        target_registry._parse_target_txt(txt_path)


def test_target_registry_registry_state_and_queries(tmp_path: Path, isolated_registry: None) -> None:
    """覆盖 registry 状态变更、查询与冲突分支。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 register / load / query / current target 的边界与错误路径。

    对应功能实现文件路径: kernel_gen/target/registry.py
    对应 spec 文件路径: spec/target/registry.md
    对应测试文件路径: test/target/test_target_registry_private_helpers.py
    """

    cpu_like = target_registry.TargetSpec("cpu", None, {"arch.get_thread_id"}, {"thread_num": 1})
    target_registry._TARGET_REGISTRY.clear()
    target_registry.register_target(cpu_like)
    with pytest.raises(ValueError):
        target_registry.register_target(cpu_like)

    target_registry._TARGET_REGISTRY.clear()
    target_registry._TARGET_REGISTRY["cpu"] = target_registry.TargetSpec(
        "cpu",
        None,
        set(target_registry._DEFAULT_CPU_UNSUPPORTED_OPS),
        dict(target_registry._DEFAULT_CPU_HARDWARE),
    )
    target_registry._ensure_cpu_target()
    assert "cpu" in target_registry._TARGET_REGISTRY

    target_registry._TARGET_REGISTRY["npu_demo"] = target_registry.TargetSpec(
        "npu_demo",
        None,
        set(),
        {},
    )
    with pytest.raises(ValueError):
        target_registry._ensure_npu_demo_target()

    target_registry._TARGET_REGISTRY.clear()
    loaded = target_registry.load_targets(tmp_path)
    assert loaded == {}
    with pytest.raises(ValueError):
        target_registry.load_targets(tmp_path / "missing")
    with pytest.raises(ValueError):
        target_registry.load_targets(tmp_path / "not_dir")

    target_registry._TARGET_REGISTRY.clear()
    target_registry._TARGET_REGISTRY["gpu"] = target_registry.TargetSpec(
        "gpu",
        {"arch.get_thread_id"},
        set(),
        {"thread_num": 2},
    )
    assert target_registry.is_arch_op_supported("gpu", "arch.get_thread_id") is True
    assert target_registry.get_target_hardware("gpu", "thread_num") == 2
    assert target_registry.get_target_analysis_defaults("gpu") == {}
    assert target_registry._get_current_target() is None
    target_registry._set_current_target("gpu")
    try:
        assert target_registry._get_current_target() == "gpu"
        assert target_registry.get_current_target_hardware("thread_num") == 2
    finally:
        target_registry._set_current_target(None)

    with pytest.raises(ValueError):
        target_registry.is_arch_op_supported("missing", "arch.get_thread_id")
    with pytest.raises(ValueError):
        target_registry.get_target_hardware("missing", "thread_num")
    with pytest.raises(ValueError):
        target_registry.get_target_analysis_defaults("missing")
    with pytest.raises(ValueError):
        target_registry._set_current_target("missing")

    lhs = target_registry.TargetSpec("a", None, set(), {})
    rhs = target_registry.TargetSpec("a", None, set(), {})
    assert target_registry._same_target_spec(lhs, rhs) is True
    assert target_registry._is_default_cpu_spec(
        target_registry.TargetSpec(
            "cpu",
            None,
            set(target_registry._DEFAULT_CPU_UNSUPPORTED_OPS),
            dict(target_registry._DEFAULT_CPU_HARDWARE),
        )
    )
