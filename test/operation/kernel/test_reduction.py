"""kernel operation reduction tests.


功能说明:
- 覆盖 `kernel.reduce` out-first 公开 API。
- 验证 `KernelReduceKind`、axis、keepdim 与输出 shape 合同。

使用示例:
- pytest -q test/operation/kernel/test_reduction.py

关联文件:
- 功能实现: kernel_gen/operation/kernel/reduction.py
- Spec 文档: spec/operation/kernel.md
- 测试文件: test/operation/kernel/test_reduction.py
"""

from __future__ import annotations

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation import kernel
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


# TC-OP-KERNEL-REDUCTION-001
# 功能说明: 验证 reduce out-first 语义和 kind 矩阵。
# 测试目的: sum/min/max 使用 enum kind，合法输出 shape 返回 None。
# 使用示例: pytest -q test/operation/kernel/test_reduction.py -k reduce_out_first
# 对应功能实现文件路径: kernel_gen/operation/kernel/reduction.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_reduction.py
def test_kernel_reduce_is_out_first_and_supports_public_kinds() -> None:
    input_value = Memory([SymbolDim("B"), SymbolDim("N")], NumericType.Float32, space=MemorySpace.TSM)
    keepdim_out = Memory([SymbolDim("B"), 1], NumericType.Float32, space=MemorySpace.TSM)
    squeezed_out = Memory([SymbolDim("B")], NumericType.Float32, space=MemorySpace.TSM)

    assert kernel.reduce(keepdim_out, input_value, kind=kernel.KernelReduceKind.MAX, axis=1, keepdim=True) is None
    assert kernel.reduce(squeezed_out, input_value, kind=kernel.KernelReduceKind.SUM, axis=1) is None
    assert kernel.reduce(squeezed_out, input_value, kind=kernel.KernelReduceKind.MIN, axis=1, keepdim=False) is None


# TC-OP-KERNEL-REDUCTION-002
# 功能说明: 验证 reduce 拒绝非法合同。
# 测试目的: 非 enum kind、非法 axis/keepdim、shape/dtype/space mismatch 均失败。
# 使用示例: pytest -q test/operation/kernel/test_reduction.py -k reduce_rejects
# 对应功能实现文件路径: kernel_gen/operation/kernel/reduction.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_reduction.py
def test_kernel_reduce_rejects_invalid_contract() -> None:
    input_value = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    out = Memory([2], NumericType.Float32, space=MemorySpace.GM)

    with pytest.raises(KernelCodeError, match="KernelReduceKind"):
        kernel.reduce(out, input_value, kind="sum", axis=1)
    with pytest.raises(KernelCodeError, match="axis"):
        kernel.reduce(out, input_value, kind=kernel.KernelReduceKind.SUM, axis=-1)
    with pytest.raises(KernelCodeError, match="keepdim"):
        kernel.reduce(out, input_value, kind=kernel.KernelReduceKind.SUM, axis=1, keepdim=1)
    with pytest.raises(KernelCodeError, match="shape"):
        kernel.reduce(Memory([3], NumericType.Float32), input_value, kind=kernel.KernelReduceKind.SUM, axis=1)
    with pytest.raises(KernelCodeError, match="dtype"):
        kernel.reduce(Memory([2], NumericType.Float16), input_value, kind=kernel.KernelReduceKind.SUM, axis=1)
    with pytest.raises(KernelCodeError, match="space"):
        kernel.reduce(Memory([2], NumericType.Float32, space=MemorySpace.SM), input_value, kind=kernel.KernelReduceKind.SUM, axis=1)
