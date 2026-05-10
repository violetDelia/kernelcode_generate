"""kernel operation elementwise tests.


功能说明:
- 覆盖 `kernel_gen.operation.kernel` out-first binary elewise 公开 API。
- 测试只通过 `kernel_gen.operation.kernel` 子模块调用公开 helper。

使用示例:
- pytest -q test/operation/kernel/test_elementwise.py

关联文件:
- 功能实现: kernel_gen/operation/kernel/elementwise.py
- Spec 文档: spec/operation/kernel.md
- 测试文件: test/operation/kernel/test_elementwise.py
"""

from __future__ import annotations

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation import kernel
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


# TC-OP-KERNEL-ELEWISE-001
# 功能说明: 验证 out-first 算术 helper 成功路径。
# 测试目的: 锁定 add/sub/mul/div/truediv 返回 None 且不创建新 Memory。
# 使用示例: pytest -q test/operation/kernel/test_elementwise.py -k arithmetic
# 对应功能实现文件路径: kernel_gen/operation/kernel/elementwise.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_elementwise.py
def test_kernel_arithmetic_helpers_are_out_first_and_return_none() -> None:
    shape = [SymbolDim("M"), SymbolDim("N")]
    out = Memory(shape, NumericType.Float32, space=MemorySpace.TSM)
    lhs = Memory(shape, NumericType.Float32, space=MemorySpace.TSM)
    rhs = Memory(shape, NumericType.Float32, space=MemorySpace.TSM)

    assert kernel.add(out, lhs, rhs) is None
    assert kernel.sub(out, lhs, rhs) is None
    assert kernel.mul(out, lhs, rhs) is None
    assert kernel.div(out, lhs, rhs) is None
    assert kernel.truediv(out, lhs, rhs) is None
    assert kernel.binary_elewise(out, lhs, rhs, kind=kernel.KernelBinaryElewiseKind.ADD) is None


# TC-OP-KERNEL-ELEWISE-002
# 功能说明: 验证 compare helper 的 Bool out 合同。
# 测试目的: compare 允许 lhs/rhs dtype 不同，但 out 必须是 Bool。
# 使用示例: pytest -q test/operation/kernel/test_elementwise.py -k compare
# 对应功能实现文件路径: kernel_gen/operation/kernel/elementwise.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_elementwise.py
def test_kernel_compare_helpers_require_bool_out_and_allow_input_dtype_mismatch() -> None:
    shape = [4, 8]
    out = Memory(shape, NumericType.Bool, space=MemorySpace.GM)
    lhs = Memory(shape, NumericType.Float32, space=MemorySpace.GM)
    rhs = Memory(shape, NumericType.Int32, space=MemorySpace.GM)

    assert kernel.eq(out, lhs, rhs) is None
    assert kernel.ne(out, lhs, rhs) is None
    assert kernel.lt(out, lhs, rhs) is None
    assert kernel.le(out, lhs, rhs) is None
    assert kernel.gt(out, lhs, rhs) is None
    assert kernel.ge(out, lhs, rhs) is None

    with pytest.raises(KernelCodeError, match="Bool"):
        kernel.eq(Memory(shape, NumericType.Float32), lhs, rhs)


# TC-OP-KERNEL-ELEWISE-003
# 功能说明: 验证错误边界。
# 测试目的: 字符串 kind、layout 不一致和 arithmetic dtype 不一致必须拒绝。
# 使用示例: pytest -q test/operation/kernel/test_elementwise.py -k rejects
# 对应功能实现文件路径: kernel_gen/operation/kernel/elementwise.py
# 对应 spec 文件路径: spec/operation/kernel.md
# 对应测试文件路径: test/operation/kernel/test_elementwise.py
def test_kernel_binary_elewise_rejects_non_api_kind_and_mismatched_metadata() -> None:
    out = Memory([2, 3], NumericType.Float32)
    lhs = Memory([2, 3], NumericType.Float32)
    rhs = Memory([2, 3], NumericType.Float32)

    with pytest.raises(KernelCodeError, match="KernelBinaryElewiseKind"):
        kernel.binary_elewise(out, lhs, rhs, kind="add")
    with pytest.raises(KernelCodeError, match="shape"):
        kernel.add(out, lhs, Memory([2, 4], NumericType.Float32))
    with pytest.raises(KernelCodeError, match="dtype"):
        kernel.add(out, lhs, Memory([2, 3], NumericType.Int32))
