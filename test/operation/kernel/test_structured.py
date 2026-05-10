"""kernel operation structured tests.


功能说明:
- 覆盖 `kernel.matmul`、`kernel.img2col1d` 与 `kernel.img2col2d` 公开 API。
- 测试 out-first 写回语义和静态/符号参数边界。

使用示例:
- pytest -q test/operation/kernel/test_structured.py

关联文件:
- 功能实现: kernel_gen/operation/kernel/structured.py
- Spec 文档: spec/operation/kernel.md
- 测试文件: test/operation/kernel/test_structured.py
"""

from __future__ import annotations

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation import kernel
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType


# TC-OP-KERNEL-STRUCTURED-001
# 功能说明: 验证 matmul out-first 语义与 mixed-space 支持。
# 测试目的: matmul 不接受 memoryspace 参数，输出 shape 必须为 [lhs.M, rhs.N]。
# 使用示例: pytest -q test/operation/kernel/test_structured.py -k matmul
# 对应功能实现文件路径: kernel_gen/operation/kernel/structured.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_structured.py
def test_kernel_matmul_supports_mixed_space_and_rejects_non_api_memoryspace() -> None:
    m_dim = SymbolDim("M")
    k_dim = SymbolDim("K")
    n_dim = SymbolDim("N")
    out = Memory([m_dim, n_dim], NumericType.Float32, space=MemorySpace.TSM)
    lhs = Memory([m_dim, k_dim], NumericType.Float32, space=MemorySpace.TLM1)
    rhs = Memory([k_dim, n_dim], NumericType.Float32, space=MemorySpace.TLM2)

    assert kernel.matmul(out, lhs, rhs) is None

    with pytest.raises(TypeError, match="memoryspace"):
        kernel.matmul(out, lhs, rhs, memoryspace=MemorySpace.TSM)
    with pytest.raises(KernelCodeError, match="contracting"):
        kernel.matmul(out, lhs, Memory([SymbolDim("Q"), n_dim], NumericType.Float32))


# TC-OP-KERNEL-STRUCTURED-002
# 功能说明: 验证 img2col1d 静态和符号参数。
# 测试目的: 输出 shape/stride/space 必须匹配公开 img2col1d 公式。
# 使用示例: pytest -q test/operation/kernel/test_structured.py -k img2col1d
# 对应功能实现文件路径: kernel_gen/operation/kernel/structured.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_structured.py
def test_kernel_img2col1d_validates_expected_out_memory() -> None:
    input_value = Memory([2, 3, SymbolDim("W")], NumericType.Float32, space=MemorySpace.SM, format=Farmat.Norm)
    k_dim = SymbolDim("K")
    out_w = ((SymbolDim("W") + 1 + 1 - (k_dim - 1) - 1) // 1) + 1
    out = Memory([2, 3, k_dim, out_w], NumericType.Float32, space=MemorySpace.SM)

    assert kernel.img2col1d(out, input_value, k=k_dim, s=1, d=1, p_left=1, p_right=1) is None

    with pytest.raises(KernelCodeError, match="shape"):
        kernel.img2col1d(Memory([2, 3, k_dim, SymbolDim("BAD")], NumericType.Float32, space=MemorySpace.SM), input_value, k=k_dim)


# TC-OP-KERNEL-STRUCTURED-003
# 功能说明: 验证 img2col2d 静态和符号参数。
# 测试目的: 输出 shape/stride/space 必须匹配公开 img2col2d 公式。
# 使用示例: pytest -q test/operation/kernel/test_structured.py -k img2col2d
# 对应功能实现文件路径: kernel_gen/operation/kernel/structured.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_structured.py
def test_kernel_img2col2d_validates_expected_out_memory() -> None:
    input_value = Memory([2, 3, SymbolDim("H"), SymbolDim("W")], NumericType.Float32, space=MemorySpace.LM, format=Farmat.Norm)
    kh_dim = SymbolDim("KH")
    kw_dim = SymbolDim("KW")
    out_h = ((SymbolDim("H") + 1 + 1 - (kh_dim - 1) - 1) // 1) + 1
    out_w = ((SymbolDim("W") + 2 + 2 - (kw_dim - 1) - 1) // 1) + 1
    out = Memory([2, 3, kh_dim, kw_dim, out_h, out_w], NumericType.Float32, space=MemorySpace.LM)

    assert kernel.img2col2d(out, input_value, kh=kh_dim, kw=kw_dim, ph=1, pw=1, pl=2, pr=2) is None

    with pytest.raises(KernelCodeError, match="format"):
        kernel.img2col2d(Memory([2, 3, kh_dim, kw_dim, out_h, out_w], NumericType.Float32), Memory([2, 3, 8, 8], NumericType.Float32, format=Farmat.CLast), kh=3, kw=3)
