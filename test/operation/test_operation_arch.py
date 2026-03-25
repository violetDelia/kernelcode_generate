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
