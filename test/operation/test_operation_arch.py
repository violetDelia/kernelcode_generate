"""arch operation API tests.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `kernel_gen/operation/arch.py` 的执行维度查询、动态内存入口与 kernel 启动 helper。

使用示例:
- pytest -q test/operation/test_operation_arch.py

当前覆盖率信息:
- 不再要求覆盖率；本文件以功能测试闭环为准。

覆盖率命令:
- 不再要求覆盖率命令；本文件以功能测试闭环为准。

关联文件:
- 功能实现: kernel_gen/operation/arch.py
- Spec 文档: spec/operation/arch.md
- 测试文件: test/operation/test_operation_arch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.arch import (
    BarrierScope,
    BarrierVisibility,
    barrier,
    get_block_id,
    get_block_num,
    get_dynamic_memory,
    get_subthread_id,
    get_subthread_num,
    get_thread_id,
    get_thread_num,
    launch_kernel,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.target import registry as target_registry


# TC-OP-ARCH-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 get_block_id 返回 SymbolDim 风格 block 索引语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_block_id_returns_symbol_dim
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_block_id_returns_symbol_dim() -> None:
    result = get_block_id()

    assert isinstance(result, SymbolDim)
    assert result.get_value() == "block_id"


# TC-OP-ARCH-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 get_block_num 返回 SymbolDim 风格 block 数量语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_block_num_returns_symbol_dim
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_block_num_returns_symbol_dim() -> None:
    result = get_block_num()

    assert isinstance(result, SymbolDim)
    assert result.get_value() == "block_num"


# TC-OP-ARCH-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 get_thread_id 返回 SymbolDim 风格 thread 索引语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_thread_id_returns_symbol_dim
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_thread_id_returns_symbol_dim() -> None:
    result = get_thread_id()

    assert isinstance(result, SymbolDim)
    assert result.get_value() == "thread_id"


# TC-OP-ARCH-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 get_thread_num 返回 SymbolDim 风格 thread 数量语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_thread_num_returns_symbol_dim
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_thread_num_returns_symbol_dim() -> None:
    result = get_thread_num()

    assert isinstance(result, SymbolDim)
    assert result.get_value() == "thread_num"


# TC-OP-ARCH-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 get_subthread_id 返回 SymbolDim 风格 subthread 索引语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_subthread_id_returns_symbol_dim
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_subthread_id_returns_symbol_dim() -> None:
    result = get_subthread_id()

    assert isinstance(result, SymbolDim)
    assert result.get_value() == "subthread_id"


# TC-OP-ARCH-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 get_subthread_num 返回 SymbolDim 风格 subthread 数量语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_subthread_num_returns_symbol_dim
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_subthread_num_returns_symbol_dim() -> None:
    result = get_subthread_num()

    assert isinstance(result, SymbolDim)
    assert result.get_value() == "subthread_num"


# TC-OP-ARCH-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 get_dynamic_memory 在 SM/LM/TSM/TLM1/TLM2/TLM3 六类片上空间均返回一维动态字节 Memory 语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_dynamic_memory_returns_dynamic_int8_memory
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_dynamic_memory_returns_dynamic_int8_memory() -> None:
    expected_shapes = {
        MemorySpace.SM: ["SM_SIZE"],
        MemorySpace.LM: ["LM_SIZE"],
        MemorySpace.TSM: ["TSM_SIZE"],
        MemorySpace.TLM1: ["TLM1_SIZE"],
        MemorySpace.TLM2: ["TLM2_SIZE"],
        MemorySpace.TLM3: ["TLM3_SIZE"],
    }
    for space in (
        MemorySpace.SM,
        MemorySpace.LM,
        MemorySpace.TSM,
        MemorySpace.TLM1,
        MemorySpace.TLM2,
        MemorySpace.TLM3,
    ):
        result = get_dynamic_memory(space)

        assert isinstance(result, Memory)
        assert result.get_shape() == expected_shapes[space]
        assert result.get_stride() == [1]
        assert result.dtype is NumericType.Int8
        assert result.space is space


# TC-OP-ARCH-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 get_dynamic_memory 对非法空间类型与 GM 空间报错。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_dynamic_memory_rejects_invalid_space
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_dynamic_memory_rejects_invalid_space() -> None:
    with pytest.raises(TypeError, match="space must be MemorySpace"):
        get_dynamic_memory("SM")
    with pytest.raises(ValueError, match="space must be on-chip MemorySpace"):
        get_dynamic_memory(MemorySpace.GM)


# TC-OP-ARCH-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:47:21 +0800
# 最近一次运行成功时间: 2026-04-06 03:47:21 +0800
# 测试目的: 验证 barrier 接受合法 visibility/scope 并返回 None。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_barrier_accepts_valid_arguments
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_barrier_accepts_valid_arguments() -> None:
    for scope in BarrierScope:
        result = barrier(
            visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM],
            scope=scope,
        )
        assert result is None


# TC-OP-ARCH-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:47:21 +0800
# 最近一次运行成功时间: 2026-04-06 03:47:21 +0800
# 测试目的: 验证 barrier 对缺参、非法 visibility 与非法 scope 报错。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_barrier_rejects_invalid_arguments
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_barrier_rejects_invalid_arguments() -> None:
    with pytest.raises(TypeError):
        barrier()
    with pytest.raises(TypeError):
        barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM])
    with pytest.raises(TypeError):
        barrier(scope=BarrierScope.BLOCK)
    with pytest.raises(TypeError, match="visibility must be list\\[BarrierVisibility\\] or tuple\\[BarrierVisibility, \\.\\.\\.\\]"):
        barrier(visibility="TSM/TLM", scope=BarrierScope.BLOCK)
    with pytest.raises(TypeError, match="visibility items must be BarrierVisibility"):
        barrier(visibility=[BarrierVisibility.TSM, "TLM"], scope=BarrierScope.BLOCK)
    with pytest.raises(ValueError, match="visibility must not be empty"):
        barrier(visibility=[], scope=BarrierScope.BLOCK)
    with pytest.raises(ValueError, match="visibility must not contain duplicates"):
        barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TSM], scope=BarrierScope.BLOCK)
    with pytest.raises(ValueError, match="visibility must contain TSM and TLM exactly once"):
        barrier(visibility=[BarrierVisibility.TSM], scope=BarrierScope.BLOCK)
    with pytest.raises(TypeError, match="scope must be BarrierScope"):
        barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope="block")


# TC-OP-ARCH-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:47:21 +0800
# 最近一次运行成功时间: 2026-04-06 03:47:21 +0800
# 测试目的: 验证 launch_kernel 接受函数对象、合法 extent 与尾部 kernel args，且 launched body 查询返回本次 launch extent。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_kernel_accepts_valid_extents_and_kernel_args
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_kernel_accepts_valid_extents_and_kernel_args() -> None:
    captured: dict[str, object] = {}

    def add_barrier_body(lhs: object, rhs: object, out: object) -> None:
        captured["args"] = (lhs, rhs, out)
        captured["block"] = get_block_num().get_value()
        captured["thread"] = get_thread_num().get_value()
        captured["subthread"] = get_subthread_num().get_value()

    result = launch_kernel(add_barrier_body, SymbolDim("GRID_X"), 128, 4, "lhs", "rhs", "out")

    assert result is None
    assert captured["args"] == ("lhs", "rhs", "out")
    assert captured["block"] == "GRID_X"
    assert captured["thread"] == 128
    assert captured["subthread"] == 4


# TC-OP-ARCH-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:47:21 +0800
# 最近一次运行成功时间: 2026-04-06 03:47:21 +0800
# 测试目的: 验证 launch_kernel 对字符串 callee、非法类型与静态非正规模报错。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_kernel_rejects_invalid_arguments
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_kernel_rejects_invalid_arguments() -> None:
    def kernel_body() -> None:
        raise AssertionError("unsupported launch must fail before body execution")

    with pytest.raises(TypeError, match="callee must be function object"):
        launch_kernel("my_kernel", 1, 1, 1)
    with pytest.raises(TypeError, match="callee must be function object"):
        launch_kernel(object(), 1, 1, 1)
    with pytest.raises(TypeError, match="block must be int or SymbolDim"):
        launch_kernel(kernel_body, "1", 1, 1)
    with pytest.raises(TypeError, match="thread must be int or SymbolDim"):
        launch_kernel(kernel_body, 1, object(), 1)
    with pytest.raises(TypeError, match="subthread must be int or SymbolDim"):
        launch_kernel(kernel_body, 1, 1, [])
    with pytest.raises(ValueError, match="block must be > 0"):
        launch_kernel(kernel_body, 0, 1, 1)
    with pytest.raises(ValueError, match="thread must be > 0"):
        launch_kernel(kernel_body, 1, -1, 1)
    with pytest.raises(ValueError, match="subthread must be > 0"):
        launch_kernel(kernel_body, 1, 1, 0)


# TC-OP-ARCH-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:47:21 +0800
# 最近一次运行成功时间: 2026-04-06 03:47:21 +0800
# 测试目的: 验证 launch_kernel 调用签名固定为 callee/block/thread/subthread + 尾部位置 args，且未知关键字/缺参报 TypeError。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_kernel_call_signature_errors
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_kernel_call_signature_errors() -> None:
    def kernel_body() -> None:
        return None

    with pytest.raises(TypeError):
        launch_kernel(kernel_body, 1, 1)
    with pytest.raises(TypeError):
        launch_kernel(block=1, thread=1, subthread=1)
    with pytest.raises(TypeError):
        launch_kernel(callee=kernel_body, block=1, thread=1, subthread=1, grid=1)


# TC-OP-ARCH-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:47:21 +0800
# 最近一次运行成功时间: 2026-04-06 03:47:21 +0800
# 测试目的: 验证 launch_kernel 关键字调用仅允许 callee/block/thread/subthread 且语义一致。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_kernel_keyword_call_success
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_kernel_keyword_call_success() -> None:
    captured: list[str] = []

    def kernel_body() -> None:
        captured.append("called")

    result = launch_kernel(thread=2, subthread=1, block=4, callee=kernel_body)

    assert result is None
    assert captured == ["called"]


# TC-OP-ARCH-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:47:21 +0800
# 最近一次运行成功时间: 2026-04-06 03:47:21 +0800
# 测试目的: 验证无 launch 上下文时查询优先走硬件值，而 launched body 中 block/thread/subthread 数量语义切换为本次 launch extent。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_queries_and_memory_prefer_launch_or_hardware_context
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_queries_and_memory_prefer_launch_or_hardware_context() -> None:
    spec = target_registry.TargetSpec(
        name="op_arch_hw_fallback",
        arch_supported_ops={
            "arch.get_block_num",
            "arch.get_thread_num",
            "arch.get_subthread_num",
            "arch.get_dynamic_memory",
            "arch.launch",
        },
        arch_unsupported_ops=set(),
        hardware={"block_num": 256, "thread_num": 128, "subthread_num": 32, "sm_memory_size": 4096},
    )
    target_registry.register_target(spec)
    target_registry._set_current_target("op_arch_hw_fallback")
    try:
        block_num = get_block_num()
        thread_num = get_thread_num()
        subthread_num = get_subthread_num()
        smem = get_dynamic_memory(MemorySpace.SM)
        captured: dict[str, object] = {}

        def launched_body() -> None:
            captured["block"] = get_block_num().get_value()
            captured["thread"] = get_thread_num().get_value()
            captured["subthread"] = get_subthread_num().get_value()
            captured["smem_shape"] = get_dynamic_memory(MemorySpace.SM).get_shape()

        launch_kernel(launched_body, SymbolDim("GRID_X"), 8, SymbolDim("SUBTHREAD_X"))

        assert block_num.get_value() == 256
        assert thread_num.get_value() == 128
        assert subthread_num.get_value() == 32
        assert smem.get_shape() == [4096]
        assert smem.get_stride() == [1]
        assert smem.dtype is NumericType.Int8
        assert smem.space is MemorySpace.SM
        assert captured["block"] == "GRID_X"
        assert captured["thread"] == 8
        assert captured["subthread"] == "SUBTHREAD_X"
        assert captured["smem_shape"] == [4096]
    finally:
        target_registry._set_current_target(None)


# TC-OP-ARCH-016
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 03:47:21 +0800
# 最近一次运行成功时间: 2026-04-06 03:47:21 +0800
# 测试目的: 验证 target registry 白名单限制下 barrier 与 launch 等不支持 helper 触发错误。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_barrier_and_launch_helpers_reject_unsupported_target_ops
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_barrier_and_launch_helpers_reject_unsupported_target_ops() -> None:
    spec = target_registry.TargetSpec(
        name="op_arch_support_gate",
        arch_supported_ops={"arch.get_block_id"},
        arch_unsupported_ops=set(),
        hardware={},
    )
    target_registry.register_target(spec)
    target_registry._set_current_target("op_arch_support_gate")
    try:
        assert get_block_id().get_value() == "block_id"
        with pytest.raises(ValueError, match="arch.get_block_num"):
            get_block_num()
        with pytest.raises(ValueError, match="arch.get_thread_id"):
            get_thread_id()
        with pytest.raises(ValueError, match="arch.get_thread_num"):
            get_thread_num()
        with pytest.raises(ValueError, match="arch.get_subthread_num"):
            get_subthread_num()
        with pytest.raises(ValueError, match="arch.get_dynamic_memory"):
            get_dynamic_memory(MemorySpace.SM)
        with pytest.raises(ValueError, match="arch.barrier"):
            barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.BLOCK)
        with pytest.raises(ValueError, match="arch.launch"):
            launch_kernel(lambda: None, 1, 1, 1)
    finally:
        target_registry._set_current_target(None)


# TC-OP-ARCH-017
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 09:05:00 +0800
# 最近一次运行成功时间: 2026-04-16 09:05:00 +0800
# 测试目的: 验证 target registry 缺少 arch 支持矩阵关键字段时，arch query helper 返回显式错误。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_arch_queries_reject_target_registry_entries_missing_arch_fields
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_arch_queries_reject_target_registry_entries_missing_arch_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken_target = type("BrokenTargetSpec", (), {"hardware": {}})()
    monkeypatch.setitem(target_registry._TARGET_REGISTRY, "op_arch_missing_arch_fields", broken_target)
    target_registry._set_current_target("op_arch_missing_arch_fields")
    try:
        with pytest.raises(ValueError, match="missing required arch fields"):
            get_block_id()
    finally:
        target_registry._set_current_target(None)


# TC-OP-ARCH-018
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 09:05:00 +0800
# 最近一次运行成功时间: 2026-04-16 09:05:00 +0800
# 测试目的: 验证 target registry 缺少 hardware 关键字段时，动态内存 helper 返回显式错误。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_dynamic_memory_rejects_target_registry_entries_missing_hardware_field
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_dynamic_memory_rejects_target_registry_entries_missing_hardware_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken_target = type(
        "BrokenHardwareTargetSpec",
        (),
        {"arch_supported_ops": None, "arch_unsupported_ops": set()},
    )()
    monkeypatch.setitem(target_registry._TARGET_REGISTRY, "op_arch_missing_hardware_field", broken_target)
    target_registry._set_current_target("op_arch_missing_hardware_field")
    try:
        with pytest.raises(ValueError, match="missing required hardware field: sm_memory_size"):
            get_dynamic_memory(MemorySpace.SM)
    finally:
        target_registry._set_current_target(None)


# TC-OP-ARCH-019
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-15 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-15 00:00:00 +0800
# 测试目的: 验证启用 target registry 后，数量类 helper 与动态内存在缺失必需 hardware 字段时抛出稳定错误。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_query_helpers_reject_missing_target_hardware_fields
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_query_helpers_reject_missing_target_hardware_fields() -> None:
    spec = target_registry.TargetSpec(
        name="op_arch_missing_hw_field",
        arch_supported_ops={
            "arch.get_block_num",
            "arch.get_thread_num",
            "arch.get_subthread_num",
            "arch.get_dynamic_memory",
        },
        arch_unsupported_ops=set(),
        hardware={},
    )
    target_registry.register_target(spec)
    target_registry._set_current_target("op_arch_missing_hw_field")
    try:
        with pytest.raises(ValueError, match=r"hardware\.block_num"):
            get_block_num()
        with pytest.raises(ValueError, match=r"hardware\.thread_num"):
            get_thread_num()
        with pytest.raises(ValueError, match=r"hardware\.subthread_num"):
            get_subthread_num()
        with pytest.raises(ValueError, match=r"hardware\.sm_memory_size"):
            get_dynamic_memory(MemorySpace.SM)
    finally:
        target_registry._set_current_target(None)
