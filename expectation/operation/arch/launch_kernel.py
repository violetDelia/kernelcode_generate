"""Arch launch_kernel expectation.

创建者: 大闸蟹
最后一次更改: 朽木露琪亚

功能说明:
- 验证 operation 层 `launch_kernel` 接受合法函数对象 `callee`、执行规模与尾部 kernel 实参并返回 `None`。
- 验证字符串 `callee`、非法 extent 类型、静态非正规模与 target 不支持 `arch.launch` 时显式报错。

使用示例:
- python expectation/operation/arch/launch_kernel.py

关联文件:
- spec: spec/operation/arch.md
- test: test/operation/test_operation_arch.py
- 功能实现: kernel_gen/operation/arch.py
"""
# Case 列表:
# - Case-1: 参数合法：launch_kernel 接受合法函数对象 callee、执行规模与尾部 kernel 实参并返回 None。
# - Case-2: 参数非法：字符串/非法 callee、规模类型或正数约束不满足，或 target 不支持 arch.launch 时，应显式报错。

from pathlib import Path
import sys

import pytest

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.arch import get_block_num, get_subthread_num, get_thread_num, launch_kernel
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.target import registry as target_registry
from expectation.utils.case_runner import raise_if_failures, run_case

def _case_1() -> None:
    print("[CASE-1] 参数合法：launch_kernel 接受合法函数对象 callee、执行规模与尾部 kernel 实参并返回 None。")
    captured: dict[str, object] = {}

    def demo_kernel(lhs: object, rhs: object, out: object) -> None:
        captured["args"] = (lhs, rhs, out)
        captured["block"] = get_block_num().get_value()
        captured["thread"] = get_thread_num().get_value()
        captured["subthread"] = get_subthread_num().get_value()

    result = launch_kernel(demo_kernel, SymbolDim("GRID_X"), 128, 4, "lhs", "rhs", "out")
    assert result is None
    assert captured["args"] == ("lhs", "rhs", "out")
    assert captured["block"] == "GRID_X"
    assert captured["thread"] == 128
    assert captured["subthread"] == 4


def _case_2() -> None:
    print("[CASE-2] 参数非法：字符串/非法 callee、规模类型或正数约束不满足时，应显式报错。")

    def demo_kernel() -> None:
        return None

    with pytest.raises(TypeError):
        launch_kernel("demo_kernel", 1, 1, 1)
    with pytest.raises(TypeError):
        launch_kernel(object(), 1, 1, 1)
    with pytest.raises(TypeError):
        launch_kernel(demo_kernel, "1", 1, 1)
    with pytest.raises(ValueError):
        launch_kernel(demo_kernel, 0, 1, 1)
    with pytest.raises(ValueError):
        launch_kernel(demo_kernel, 1, -1, 1)

    spec = target_registry.TargetSpec(
        name="expect_arch_launch_gate",
        arch_supported_ops={"arch.get_block_id"},
        arch_unsupported_ops=set(),
        hardware={},
    )
    target_registry.register_target(spec)
    target_registry._set_current_target("expect_arch_launch_gate")
    try:
        with pytest.raises(ValueError, match="arch.launch"):
            launch_kernel(demo_kernel, 1, 1, 1)
    finally:
        target_registry._set_current_target(None)


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1)
    run_case(failures, "CASE-2", _case_2)
    raise_if_failures("arch launch_kernel expectation", failures)


if __name__ == "__main__":
    main()
