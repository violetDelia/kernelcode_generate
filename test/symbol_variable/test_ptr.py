"""ptr module tests.


功能说明:
- 覆盖 `kernel_gen.symbol_variable.ptr` 的 P1 最小公开语义。
- 锁定 `Ptr(dtype)`、`ptr.dtype`、`repr(ptr)` 以及缺参/多参失败边界。

覆盖率信息:
- 当前覆盖率: `100%`（`kernel_gen.symbol_variable.ptr`，2026-04-09 +0800）
- 达标判定: 已达到 `95%` 覆盖率达标线。

覆盖率命令:
- `pytest -q --cov=kernel_gen.symbol_variable.ptr --cov-report=term-missing --cov-fail-under=95 test/symbol_variable/test_ptr.py`

使用示例:
- pytest -q test/symbol_variable/test_ptr.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/ptr.py
- Spec 文档: spec/symbol_variable/ptr.md
- 测试文件: test/symbol_variable/test_ptr.py
"""

from __future__ import annotations

import pytest
from xdsl.dialects.builtin import f32


# PTR-001
# 测试目的: 验证 Ptr 保留公开 pointee dtype，并输出稳定的 `Ptr(f32)` 文本。
# 使用示例: pytest -q test/symbol_variable/test_ptr.py -k test_ptr_preserves_pointee_dtype
# 对应功能实现文件路径: kernel_gen/symbol_variable/ptr.py
# 对应 spec 文件路径: spec/symbol_variable/ptr.md
# 对应测试文件路径: test/symbol_variable/test_ptr.py
def test_ptr_preserves_pointee_dtype() -> None:
    from kernel_gen.symbol_variable.ptr import Ptr

    ptr = Ptr(f32)

    assert ptr.dtype is f32
    assert repr(ptr) == "Ptr(f32)"


# PTR-002
# 测试目的: 验证 Ptr 缺少 dtype 参数时抛出固定 TypeError。
# 使用示例: pytest -q test/symbol_variable/test_ptr.py -k test_ptr_rejects_missing_dtype
# 对应功能实现文件路径: kernel_gen/symbol_variable/ptr.py
# 对应 spec 文件路径: spec/symbol_variable/ptr.md
# 对应测试文件路径: test/symbol_variable/test_ptr.py
def test_ptr_rejects_missing_dtype() -> None:
    from kernel_gen.symbol_variable.ptr import Ptr

    with pytest.raises(TypeError, match="Ptr requires exactly one dtype"):
        Ptr()


# PTR-003
# 测试目的: 验证 Ptr 多传参数时抛出固定 TypeError。
# 使用示例: pytest -q test/symbol_variable/test_ptr.py -k test_ptr_rejects_extra_args
# 对应功能实现文件路径: kernel_gen/symbol_variable/ptr.py
# 对应 spec 文件路径: spec/symbol_variable/ptr.md
# 对应测试文件路径: test/symbol_variable/test_ptr.py
def test_ptr_rejects_extra_args() -> None:
    from kernel_gen.symbol_variable.ptr import Ptr

    with pytest.raises(TypeError, match="Ptr requires exactly one dtype"):
        Ptr(f32, f32)


# PTR-004
# 测试目的: 验证 Ptr 不是 Memory，也不是 SymbolDim。
# 使用示例: pytest -q test/symbol_variable/test_ptr.py -k test_ptr_is_not_memory_or_symbol_dim
# 对应功能实现文件路径: kernel_gen/symbol_variable/ptr.py
# 对应 spec 文件路径: spec/symbol_variable/ptr.md
# 对应测试文件路径: test/symbol_variable/test_ptr.py
def test_ptr_is_not_memory_or_symbol_dim() -> None:
    from kernel_gen.symbol_variable.memory import Memory
    from kernel_gen.symbol_variable.ptr import Ptr
    from kernel_gen.symbol_variable.symbol_dim import SymbolDim
    from kernel_gen.symbol_variable.type import NumericType

    ptr = Ptr(f32)
    mem = Memory([1], NumericType.Float32)
    dim = SymbolDim("N")

    assert not isinstance(ptr, Memory)
    assert not isinstance(ptr, SymbolDim)
    assert ptr.__class__ is not mem.__class__
    assert ptr.__class__ is not dim.__class__
