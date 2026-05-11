"""kernel operation activation tests.


功能说明:
- 覆盖 `kernel.exp` out-first 公开 API。
- 验证 dtype、shape、stride 与 space 边界。

使用示例:
- pytest -q test/operation/kernel/test_activation.py

关联文件:
- 功能实现: kernel_gen/operation/kernel/activation.py
- Spec 文档: spec/operation/kernel.md
- 测试文件: test/operation/kernel/test_activation.py
"""

from __future__ import annotations

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation import kernel
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


# TC-OP-KERNEL-ACTIVATION-001
# 功能说明: 验证 exp out-first 语义。
# 测试目的: exp 不创建新 Memory，out/input 元信息合法时返回 None。
# 使用示例: pytest -q test/operation/kernel/test_activation.py -k exp_out_first
# 对应功能实现文件路径: kernel_gen/operation/kernel/activation.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_activation.py
def test_kernel_exp_is_out_first_and_returns_none() -> None:
    shape = [SymbolDim("M"), SymbolDim("N")]
    out = Memory(shape, NumericType.Float32, space=MemorySpace.TSM)
    input_value = Memory(shape, NumericType.Float32, space=MemorySpace.TSM)

    assert kernel.exp(out, input_value) is None


# TC-OP-KERNEL-ACTIVATION-002
# 功能说明: 验证 exp 拒绝非法 metadata。
# 测试目的: dtype、shape、space 不一致或非浮点 dtype 都必须失败。
# 使用示例: pytest -q test/operation/kernel/test_activation.py -k exp_rejects
# 对应功能实现文件路径: kernel_gen/operation/kernel/activation.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_activation.py
def test_kernel_exp_rejects_invalid_metadata() -> None:
    out = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    input_value = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)

    with pytest.raises(KernelCodeError, match="shape"):
        kernel.exp(out, Memory([2, 4], NumericType.Float32))
    with pytest.raises(KernelCodeError, match="space"):
        kernel.exp(out, Memory([2, 3], NumericType.Float32, space=MemorySpace.SM))
    with pytest.raises(KernelCodeError, match="dtype"):
        kernel.exp(out, Memory([2, 3], NumericType.Float16))
    with pytest.raises(KernelCodeError, match="float"):
        kernel.exp(Memory([2, 3], NumericType.Int32), Memory([2, 3], NumericType.Int32))
    with pytest.raises(KernelCodeError, match="Memory"):
        kernel.exp(out, "bad")

    assert kernel.exp(out, input_value) is None
