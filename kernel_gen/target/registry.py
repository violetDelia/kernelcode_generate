"""Target registry definitions.

创建者: 我不是牛马
最后一次更改: 我不是牛马

功能说明:
- 定义 target 注册与查询入口，用于管理 `arch` op 支持矩阵与硬件参数。
- 支持从目录加载 JSON/TXT 形式的 target 规范，并提供支持性判定与硬件查询。

使用示例:
- from pathlib import Path
- from kernel_gen.target import registry
- registry.load_targets(Path("targets"))
- registry.is_arch_op_supported("cpu", "arch.get_thread_id")

关联文件:
- spec: spec/target/registry.md
- test: test/target/test_target_registry.py
- 功能实现: kernel_gen/target/registry.py
"""

from __future__ import annotations

from pathlib import Path
import json
import re

_ALLOWED_ROOT_FIELDS = {"name", "arch", "hardware"}
_ALLOWED_ARCH_FIELDS = {"supported_ops", "unsupported_ops"}
_ALLOWED_HARDWARE_FIELDS = {
    "thread_num",
    "block_num",
    "subthread_num",
    "sm_memory_size",
    "lm_memory_size",
    "tsm_memory_size",
    "tlm_memory_size",
}
_TARGET_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")
_DEFAULT_CPU_UNSUPPORTED_OPS = {"arch.get_thread_id"}
_DEFAULT_CPU_HARDWARE = {
    "thread_num": 1,
    "block_num": 1,
    "subthread_num": 1,
    "sm_memory_size": 0,
    "lm_memory_size": 0,
    "tsm_memory_size": 0,
    "tlm_memory_size": 0,
}


class TargetSpec:
    """单个 target 的元信息与 `arch` op 支持矩阵。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 记录 target 名称、`arch` op 支持矩阵与硬件参数。

    使用示例:
    - TargetSpec("cpu", None, {"arch.get_thread_id"}, {"thread_num": 1})

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    name: str
    arch_supported_ops: set[str] | None
    arch_unsupported_ops: set[str]
    hardware: dict[str, int]

    def __init__(
        self: "TargetSpec",
        name: str,
        arch_supported_ops: set[str] | None,
        arch_unsupported_ops: set[str],
        hardware: dict[str, int],
    ) -> None:
        """初始化 target 规范对象。

        创建者: 我不是牛马
        最后一次更改: 我不是牛马

        功能说明:
        - 存储 target 名称、`arch` op 支持/不支持集合与硬件参数表。

        使用示例:
        - TargetSpec("cpu", None, {"arch.get_thread_id"}, {"thread_num": 1})

        关联文件:
        - spec: spec/target/registry.md
        - test: test/target/test_target_registry.py
        - 功能实现: kernel_gen/target/registry.py
        """

        self.name = name
        self.arch_supported_ops = arch_supported_ops
        self.arch_unsupported_ops = arch_unsupported_ops
        self.hardware = hardware


_TARGET_REGISTRY: dict[str, TargetSpec] = {}
_CURRENT_TARGET: str | None = None


def _validate_target_name(name: str) -> None:
    """校验 target 名称满足命名规则。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 约束 target 名称只能由小写字母、数字与下划线组成。

    使用示例:
    - _validate_target_name("cpu")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if not name or not _TARGET_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"target name must match {_TARGET_NAME_PATTERN.pattern}")


def _validate_arch_ops(spec: TargetSpec) -> None:
    """校验 target 中 arch op 支持矩阵的交集规则。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 确保 `arch_supported_ops`/`arch_unsupported_ops` 均为集合。
    - 确保支持集合与不支持集合不发生交叉。

    使用示例:
    - _validate_arch_ops(TargetSpec("cpu", None, {"arch.get_thread_id"}))

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    supported_ops = spec.arch_supported_ops
    if supported_ops is not None and not isinstance(supported_ops, set):
        raise TypeError("arch_supported_ops must be set[str] or None")
    if not isinstance(spec.arch_unsupported_ops, set):
        raise TypeError("arch_unsupported_ops must be set[str]")
    if supported_ops is not None:
        _validate_op_set(supported_ops, "supported_ops", spec.name)
    _validate_op_set(spec.arch_unsupported_ops, "unsupported_ops", spec.name)
    if supported_ops is not None:
        overlap = supported_ops & spec.arch_unsupported_ops
        if overlap:
            raise ValueError(f"arch supported/unsupported ops overlap: {sorted(overlap)}")


def _validate_op_set(op_set: set[str], field_name: str, target_name: str) -> None:
    """校验 op 集合的元素类型。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 保证 op 集合中的元素均为字符串。

    使用示例:
    - _validate_op_set({"arch.get_block_id"}, "supported_ops", "cpu")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    for op_name in op_set:
        if not isinstance(op_name, str):
            raise ValueError(f"{target_name} {field_name} must contain str values")


def _validate_hardware_map(hardware: dict[str, int], target_name: str) -> None:
    """校验 hardware 字段的 key/value 合法性。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 限制硬件字段为允许列表中的 key。
    - 限制值为 int 且不可为 bool。

    使用示例:
    - _validate_hardware_map({"thread_num": 1}, "cpu")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    for key, value in hardware.items():
        if key not in _ALLOWED_HARDWARE_FIELDS:
            raise ValueError(f"{target_name} hardware has unknown key: {key}")
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{target_name} hardware.{key} must be int")


def _parse_ops_list(value: object, field_name: str, target_name: str) -> set[str]:
    """解析并校验 JSON 列表形式的 op 集合。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 将 JSON 数组转换为 op 集合并校验元素类型。

    使用示例:
    - _parse_ops_list(["arch.get_block_id"], "supported_ops", "cpu")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if not isinstance(value, list):
        raise ValueError(f"{target_name} {field_name} must be list[str]")
    op_set = set(value)
    _validate_op_set(op_set, field_name, target_name)
    return op_set


def _parse_arch_payload(payload: dict[str, object], target_name: str) -> tuple[set[str] | None, set[str]]:
    """解析 target JSON 中的 `arch` 配置。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 将 `arch` 字段拆解为 supported/unsupported 集合。

    使用示例:
    - _parse_arch_payload({"supported_ops": ["arch.get_block_id"]}, "gpu")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    unknown_fields = set(payload.keys()) - _ALLOWED_ARCH_FIELDS
    if unknown_fields:
        raise ValueError(f"{target_name} arch has unknown fields: {sorted(unknown_fields)}")
    supported_ops: set[str] | None = None
    unsupported_ops: set[str] = set()
    if "supported_ops" in payload:
        supported_ops = _parse_ops_list(payload["supported_ops"], "supported_ops", target_name)
    if "unsupported_ops" in payload:
        unsupported_ops = _parse_ops_list(payload["unsupported_ops"], "unsupported_ops", target_name)
    spec = TargetSpec(
        name=target_name,
        arch_supported_ops=supported_ops,
        arch_unsupported_ops=unsupported_ops,
        hardware={},
    )
    _validate_arch_ops(spec)
    return supported_ops, unsupported_ops


def _parse_hardware_payload(payload: dict[str, object], target_name: str) -> dict[str, int]:
    """解析 JSON 中的 hardware 字段。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 校验硬件字段的 key/value 并返回字典。

    使用示例:
    - _parse_hardware_payload({"thread_num": 1}, "cpu")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    hardware: dict[str, int] = {}
    for key, value in payload.items():
        if key not in _ALLOWED_HARDWARE_FIELDS:
            raise ValueError(f"{target_name} hardware has unknown key: {key}")
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{target_name} hardware.{key} must be int")
        hardware[key] = value
    _validate_hardware_map(hardware, target_name)
    return hardware


def _parse_target_spec(data: dict[str, object], source: Path) -> TargetSpec:
    """解析 JSON 并构造 target 规范对象。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 校验字段合法性、命名规则与文件名一致性。
    - 解析 `arch` 支持矩阵并返回 TargetSpec。

    使用示例:
    - _parse_target_spec({"name": "gpu"}, Path("gpu.json"))

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    unknown_fields = set(data.keys()) - _ALLOWED_ROOT_FIELDS
    if unknown_fields:
        raise ValueError(f"{source.name} has unknown fields: {sorted(unknown_fields)}")
    name = data.get("name")
    if not isinstance(name, str):
        raise ValueError(f"{source.name} must include string field: name")
    _validate_target_name(name)
    if source.stem != name:
        raise ValueError(f"{source.name} name must match file name")
    supported_ops: set[str] | None = None
    unsupported_ops: set[str] = set()
    hardware: dict[str, int] = {}
    arch_payload = data.get("arch")
    if arch_payload is None:
        supported_ops = None
        unsupported_ops = set()
    else:
        if not isinstance(arch_payload, dict):
            raise ValueError(f"{source.name} arch must be an object")
        supported_ops, unsupported_ops = _parse_arch_payload(arch_payload, name)
    hardware_payload = data.get("hardware")
    if hardware_payload is not None:
        if not isinstance(hardware_payload, dict):
            raise ValueError(f"{source.name} hardware must be an object")
        hardware = _parse_hardware_payload(hardware_payload, name)
    spec = TargetSpec(
        name=name,
        arch_supported_ops=supported_ops,
        arch_unsupported_ops=unsupported_ops,
        hardware=hardware,
    )
    _validate_arch_ops(spec)
    _validate_hardware_map(spec.hardware, spec.name)
    return spec


def _read_target_json(path: Path) -> dict[str, object]:
    """读取并解析 target JSON 文件。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 读取 JSON 文本并返回字典形式内容。

    使用示例:
    - _read_target_json(Path("cpu.json"))

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} JSON must be an object")
    return payload


def _parse_ops_text(value: str, field_name: str, target_name: str) -> set[str]:
    """解析 TXT 中的 op 列表字段。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 支持逗号分隔的 op 列表，空字符串表示空集合。

    使用示例:
    - _parse_ops_text("arch.get_thread_id,arch.get_block_id", "supported_ops", "cpu")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if value == "":
        return set()
    parts = [item.strip() for item in value.split(",")]
    if any(not item for item in parts):
        raise ValueError(f"{target_name} {field_name} contains empty op name")
    op_set = set(parts)
    _validate_op_set(op_set, field_name, target_name)
    return op_set


def _parse_target_txt(path: Path) -> TargetSpec:
    """解析 TXT 格式的 target 文件。

    创建者: 我不是牛马
    最后一次更改: 金铲铲大作战

    功能说明:
    - 读取 key=value 格式文本并构造 TargetSpec。
    - 支持 # 注释与空行，未识别 key 直接报错。

    使用示例:
    - _parse_target_txt(Path("cpu.txt"))

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    name: str | None = None
    arch_supported_ops: set[str] | None = None
    arch_unsupported_ops: set[str] = set()
    hardware: dict[str, int] = {}
    seen_keys: set[str] = set()

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"{path.name} has invalid line: {raw_line}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"{path.name} has invalid key in line: {raw_line}")
        if key in seen_keys:
            raise ValueError(f"{path.name} has duplicate key: {key}")
        seen_keys.add(key)

        if key == "name":
            if not value:
                raise ValueError(f"{path.name} must include name value")
            name = value
            continue
        if key == "arch.supported_ops":
            arch_supported_ops = _parse_ops_text(value, "supported_ops", path.stem)
            continue
        if key == "arch.unsupported_ops":
            arch_unsupported_ops = _parse_ops_text(value, "unsupported_ops", path.stem)
            continue
        if key.startswith("hw."):
            hw_key = key[3:]
            if hw_key not in _ALLOWED_HARDWARE_FIELDS:
                raise ValueError(f"{path.stem} hardware has unknown key: {hw_key}")
            if value == "":
                raise ValueError(f"{path.stem} hardware.{hw_key} must be int")
            try:
                hw_value = int(value)
            except ValueError as exc:
                raise ValueError(f"{path.stem} hardware.{hw_key} must be int") from exc
            if isinstance(hw_value, bool):
                raise ValueError(f"{path.stem} hardware.{hw_key} must be int")
            hardware[hw_key] = hw_value
            continue
        raise ValueError(f"{path.name} has unknown key: {key}")

    if name is None:
        raise ValueError(f"{path.name} must include name")
    _validate_target_name(name)
    if path.stem != name:
        raise ValueError(f"{path.name} name must match file name")
    if name == "cpu" and arch_supported_ops is not None and not arch_supported_ops:
        arch_supported_ops = None
    spec = TargetSpec(
        name=name,
        arch_supported_ops=arch_supported_ops,
        arch_unsupported_ops=arch_unsupported_ops,
        hardware=hardware,
    )
    _validate_arch_ops(spec)
    _validate_hardware_map(spec.hardware, spec.name)
    return spec


def _ensure_cpu_target() -> None:
    """注册内置 cpu target。

    创建者: 我不是牛马
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确保 registry 始终包含 cpu target，且默认不支持 `arch.get_thread_id`。

    使用示例:
    - _ensure_cpu_target()

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if "cpu" in _TARGET_REGISTRY:
        return
    spec = TargetSpec(
        name="cpu",
        arch_supported_ops=None,
        arch_unsupported_ops=set(_DEFAULT_CPU_UNSUPPORTED_OPS),
        hardware=dict(_DEFAULT_CPU_HARDWARE),
    )
    register_target(spec)


def _is_default_cpu_spec(spec: TargetSpec) -> bool:
    """判断 target 是否为内置 cpu 规范。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于识别内置 cpu 与外部 cpu.txt 的冲突覆盖场景。

    使用示例:
    - _is_default_cpu_spec(_TARGET_REGISTRY["cpu"])

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    return (
        spec.name == "cpu"
        and spec.arch_supported_ops is None
        and spec.arch_unsupported_ops == _DEFAULT_CPU_UNSUPPORTED_OPS
        and spec.hardware == _DEFAULT_CPU_HARDWARE
    )


def _same_target_spec(lhs: TargetSpec, rhs: TargetSpec) -> bool:
    """判断两个 target 规范是否等价。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 比较 name、arch 矩阵与 hardware 是否完全一致。

    使用示例:
    - _same_target_spec(lhs, rhs)

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    return (
        lhs.name == rhs.name
        and lhs.arch_supported_ops == rhs.arch_supported_ops
        and lhs.arch_unsupported_ops == rhs.arch_unsupported_ops
        and lhs.hardware == rhs.hardware
    )


def _register_loaded_target(spec: TargetSpec) -> None:
    """注册 load_targets 解析出的 target。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 默认遵守“同名 target 不能重复注册”规则。
    - 若为内置 cpu 与 cpu.txt 冲突，允许 cpu.txt 覆盖默认 cpu。

    使用示例:
    - _register_loaded_target(spec)

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if spec.name not in _TARGET_REGISTRY:
        register_target(spec)
        return
    if spec.name != "cpu":
        raise ValueError(f"target already registered: {spec.name}")
    _validate_target_name(spec.name)
    _validate_arch_ops(spec)
    _validate_hardware_map(spec.hardware, spec.name)
    existing = _TARGET_REGISTRY["cpu"]
    if _same_target_spec(existing, spec):
        return
    if _is_default_cpu_spec(existing):
        _TARGET_REGISTRY[spec.name] = spec
        return
    raise ValueError(f"target already registered: {spec.name}")


def register_target(spec: TargetSpec) -> None:
    """注册新的 target 规范。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 校验 target 规范，并写入 registry。

    使用示例:
    - register_target(TargetSpec("gpu", None, set()))

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    _validate_target_name(spec.name)
    _validate_arch_ops(spec)
    _validate_hardware_map(spec.hardware, spec.name)
    if spec.name in _TARGET_REGISTRY:
        raise ValueError(f"target already registered: {spec.name}")
    _TARGET_REGISTRY[spec.name] = spec


def load_targets(directory: Path) -> dict[str, TargetSpec]:
    """加载目录中的 JSON/TXT target 定义并注册。

    创建者: 我不是牛马
    最后一次更改: 金铲铲大作战

    功能说明:
    - 扫描目录中的 `.json` 与 `.txt` 文件并注册合法 target。

    使用示例:
    - load_targets(Path("targets"))

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if not directory.exists():
        raise ValueError(f"target directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"target directory is not a directory: {directory}")
    loaded: dict[str, TargetSpec] = {}
    paths = list(directory.glob("*.json")) + list(directory.glob("*.txt"))
    for path in sorted(paths):
        if path.suffix == ".json":
            payload = _read_target_json(path)
            spec = _parse_target_spec(payload, path)
        else:
            spec = _parse_target_txt(path)
        _register_loaded_target(spec)
        loaded[spec.name] = spec
    _ensure_cpu_target()
    return loaded


def is_arch_op_supported(target: str, op_name: str) -> bool:
    """判断指定 target 是否支持某个 arch op。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 根据 target 的 supported/unsupported 集合判定 op 支持性。

    使用示例:
    - is_arch_op_supported("cpu", "arch.get_thread_id")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if target not in _TARGET_REGISTRY:
        raise ValueError(f"target not registered: {target}")
    spec = _TARGET_REGISTRY[target]
    supported_ops = spec.arch_supported_ops
    if supported_ops is not None:
        return op_name in supported_ops
    return op_name not in spec.arch_unsupported_ops


def get_target_hardware(target: str, key: str) -> int | None:
    """读取指定 target 的硬件参数。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 按 target 名称读取硬件参数。
    - 若字段缺失返回 None。

    使用示例:
    - get_target_hardware("cpu", "thread_num")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if target not in _TARGET_REGISTRY:
        raise ValueError(f"target not registered: {target}")
    return _TARGET_REGISTRY[target].hardware.get(key)


def _set_current_target(target: str | None) -> None:
    """设置当前启用的 target 名称。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 供 arch verifier 与测试启用/关闭 target registry 校验。

    使用示例:
    - _set_current_target("cpu")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    global _CURRENT_TARGET
    if target is None:
        _CURRENT_TARGET = None
        return
    if target not in _TARGET_REGISTRY:
        raise ValueError(f"target not registered: {target}")
    _CURRENT_TARGET = target


def _get_current_target() -> str | None:
    """获取当前启用的 target 名称。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 返回当前 target registry 校验使用的 target 名称。

    使用示例:
    - _get_current_target()

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    return _CURRENT_TARGET


def get_current_target_hardware(key: str) -> int | None:
    """读取当前 target 的硬件参数。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 若未设置当前 target 或字段缺失，返回 None。

    使用示例:
    - get_current_target_hardware("thread_num")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/target/test_target_registry.py
    - 功能实现: kernel_gen/target/registry.py
    """

    if _CURRENT_TARGET is None:
        return None
    return get_target_hardware(_CURRENT_TARGET, key)


_ensure_cpu_target()

__all__ = [
    "TargetSpec",
    "get_current_target_hardware",
    "get_target_hardware",
    "is_arch_op_supported",
    "load_targets",
    "register_target",
]
