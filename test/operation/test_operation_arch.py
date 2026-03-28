"""arch operation API tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

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
# 测试目的: 验证 get_dynamic_memory 在 SM/LM/TSM/TLM 四类片上空间均返回一维动态字节 Memory 语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_get_dynamic_memory_returns_dynamic_int8_memory
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_get_dynamic_memory_returns_dynamic_int8_memory() -> None:
    for space in (
        MemorySpace.SM,
        MemorySpace.LM,
        MemorySpace.TSM,
        MemorySpace.TLM,
    ):
        result = get_dynamic_memory(space)

        assert isinstance(result, Memory)
        assert result.get_shape() == ["?"]
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 launch_kernel 接受合法 int | SymbolDim 输入并返回 None。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_kernel_accepts_valid_extents
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_kernel_accepts_valid_extents() -> None:
    result = launch_kernel("my_kernel", SymbolDim("GRID_X"), 128, 4)

    assert result is None


# TC-OP-ARCH-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 21:41:11 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:11 +0800
# 测试目的: 验证 launch_kernel 对空名称、非法类型与静态非正规模报错。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_kernel_rejects_invalid_arguments
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_kernel_rejects_invalid_arguments() -> None:
    with pytest.raises(ValueError, match="name must not be empty"):
        launch_kernel("", 1, 1, 1)
    with pytest.raises(TypeError, match="name must be str"):
        launch_kernel(1, 1, 1, 1)
    with pytest.raises(TypeError, match="block must be int or SymbolDim"):
        launch_kernel("my_kernel", "1", 1, 1)
    with pytest.raises(TypeError, match="thread must be int or SymbolDim"):
        launch_kernel("my_kernel", 1, object(), 1)
    with pytest.raises(TypeError, match="subthread must be int or SymbolDim"):
        launch_kernel("my_kernel", 1, 1, [])
    with pytest.raises(ValueError, match="block must be > 0"):
        launch_kernel("my_kernel", 0, 1, 1)
    with pytest.raises(ValueError, match="thread must be > 0"):
        launch_kernel("my_kernel", 1, -1, 1)
    with pytest.raises(ValueError, match="subthread must be > 0"):
        launch_kernel("my_kernel", 1, 1, 0)


# TC-OP-ARCH-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 02:04:02 +0800
# 最近一次运行成功时间: 2026-03-28 02:04:02 +0800
# 测试目的: 验证 launch_kernel 调用签名固定为四参且未知关键字/缺参/多参报 TypeError。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_kernel_call_signature_errors
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_kernel_call_signature_errors() -> None:
    with pytest.raises(TypeError):
        launch_kernel("my_kernel", 1, 1)
    with pytest.raises(TypeError):
        launch_kernel("my_kernel", 1, 1, 1, 1)
    with pytest.raises(TypeError):
        launch_kernel(name="my_kernel", block=1, thread=1, subthread=1, grid=1)


# TC-OP-ARCH-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 02:04:02 +0800
# 最近一次运行成功时间: 2026-03-28 02:04:02 +0800
# 测试目的: 验证 launch_kernel 关键字调用仅允许 name/block/thread/subthread 且语义一致。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_launch_kernel_keyword_call_success
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_launch_kernel_keyword_call_success() -> None:
    result = launch_kernel(thread=2, subthread=1, block=4, name="my_kernel")

    assert result is None


# TC-OP-ARCH-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 13:56:08 +0800
# 最近一次运行成功时间: 2026-03-28 13:56:08 +0800
# 测试目的: 验证 target registry 硬件值优先、生效与缺失回退语义。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_arch_queries_prefer_target_hardware_with_fallback
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_arch_queries_prefer_target_hardware_with_fallback() -> None:
    spec = target_registry.TargetSpec(
        name="op_arch_hw_fallback",
        arch_supported_ops=None,
        arch_unsupported_ops=set(),
        hardware={"block_num": 256, "thread_num": 128, "sm_memory_size": 4096},
    )
    target_registry.register_target(spec)
    target_registry._set_current_target("op_arch_hw_fallback")
    try:
        block_num = get_block_num()
        thread_num = get_thread_num()
        subthread_num = get_subthread_num()
        smem = get_dynamic_memory(MemorySpace.SM)
        lmem = get_dynamic_memory(MemorySpace.LM)

        assert block_num.get_value() == 256
        assert thread_num.get_value() == 128
        assert subthread_num.get_value() == "subthread_num"
        assert smem.get_shape() == [4096]
        assert smem.get_stride() == [1]
        assert smem.dtype is NumericType.Int8
        assert smem.space is MemorySpace.SM
        assert lmem.get_shape() == ["?"]
        assert lmem.get_stride() == [1]
        assert lmem.dtype is NumericType.Int8
        assert lmem.space is MemorySpace.LM
    finally:
        target_registry._set_current_target(None)


# TC-OP-ARCH-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 13:56:08 +0800
# 最近一次运行成功时间: 2026-03-28 13:56:08 +0800
# 测试目的: 验证 target registry 白名单限制下的不支持 op 触发错误。
# 使用示例: pytest -q test/operation/test_operation_arch.py -k test_arch_queries_reject_unsupported_target_ops
# 对应功能实现文件路径: kernel_gen/operation/arch.py
# 对应 spec 文件路径: spec/operation/arch.md
# 对应测试文件路径: test/operation/test_operation_arch.py
def test_arch_queries_reject_unsupported_target_ops() -> None:
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
        with pytest.raises(ValueError, match="arch.launch_kernel"):
            launch_kernel("kernel", 1, 1, 1)
    finally:
        target_registry._set_current_target(None)
