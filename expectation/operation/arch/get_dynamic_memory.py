"""Arch get_dynamic_memory expectation.

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 验证 `arch.get_dynamic_memory` 返回片上空间的动态 `Memory` 描述。
- 验证 target 提供硬件容量时，shape 优先使用硬件值。
- 验证非法空间或不支持 target 时显式报错。

使用示例:
- python expectation/operation/arch/get_dynamic_memory.py

关联文件:
- spec: spec/operation/arch.md
- test: test/operation/test_operation_arch.py
- 功能实现: kernel_gen/operation/arch.py
"""
# Case 列表:
# - Case-1: 参数合法：默认调用 get_dynamic_memory(on-chip space)，返回一维动态 shape 的 int8 Memory。
# - Case-2: 参数合法：target 提供硬件容量时，shape 优先使用硬件值。
# - Case-3: 参数非法：space 非法或 target 不支持 arch.get_dynamic_memory 时，应显式报错。

from pathlib import Path
import sys

import pytest

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.arch import get_dynamic_memory
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.target import registry as target_registry
from expectation.utils.case_runner import raise_if_failures, run_case

def _case_1() -> None:
    print("[CASE-1] 参数合法：默认调用 get_dynamic_memory，返回一维动态 int8 Memory。")
    result = get_dynamic_memory(MemorySpace.TSM)
    assert isinstance(result, Memory)
    assert result.get_shape() == ["?"]
    assert result.get_stride() == [1]
    assert result.get_type() is NumericType.Int8
    assert result.get_space() is MemorySpace.TSM


def _case_2() -> None:
    print("[CASE-2] 参数合法：target 提供硬件容量时，shape 优先使用硬件值。")
    spec = target_registry.TargetSpec(
        "expect_arch_get_dynamic_memory_hw",
        {"arch.get_dynamic_memory"},
        set(),
        {"sm_memory_size": 4096, "lm_memory_size": 2048},
    )
    target_registry.register_target(spec)
    target_registry._set_current_target("expect_arch_get_dynamic_memory_hw")
    try:
        smem = get_dynamic_memory(MemorySpace.SM)
        lmem = get_dynamic_memory(MemorySpace.LM)
        assert smem.get_shape() == [4096]
        assert lmem.get_shape() == [2048]
        assert smem.get_stride() == [1]
        assert lmem.get_stride() == [1]
    finally:
        target_registry._set_current_target(None)


def _case_3() -> None:
    print("[CASE-3] 参数非法：非法空间或不支持 target 时，应显式报错。")
    with pytest.raises(TypeError):
        get_dynamic_memory("SM")
    with pytest.raises(ValueError):
        get_dynamic_memory(MemorySpace.GM)

    spec = target_registry.TargetSpec(
        "expect_arch_get_dynamic_memory_gate",
        None,
        {"arch.get_dynamic_memory"},
        {},
    )
    target_registry.register_target(spec)
    target_registry._set_current_target("expect_arch_get_dynamic_memory_gate")
    try:
        with pytest.raises(ValueError, match="arch.get_dynamic_memory"):
            get_dynamic_memory(MemorySpace.SM)
    finally:
        target_registry._set_current_target(None)


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1)
    run_case(failures, "CASE-2", _case_2)
    run_case(failures, "CASE-3", _case_3)
    raise_if_failures("arch get_dynamic_memory expectation", failures)


if __name__ == "__main__":
    main()
