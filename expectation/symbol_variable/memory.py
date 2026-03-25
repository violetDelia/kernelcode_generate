"""Memory expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 描述 Memory 在不同 rank 下的默认 stride、shape 序列化与字符串表示的目标行为。
- 覆盖纯整数 shape、纯 symbol shape 以及整数和 symbol 混合 shape 的场景。

使用示例:
- python expectation/symbol_variable/memory.py

关联文件:
- spec: spec/symbol_variable/memory.md
- test: test/symbol_variable/test_memory.py
- 功能实现: kernel_gen/symbol_variable/memory.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.random import (  # noqa: E402
    get_random_alpha_string,
    get_random_non_zero_int,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace  # noqa: E402
from kernel_gen.symbol_variable.symbol_dim import SymbolDim  # noqa: E402
from kernel_gen.symbol_variable.type import Farmat, NumericType  # noqa: E402


def assert_memory_layout(
    mem: Memory,
    shape_values: list[int | str],
    stride_values: list[int | str],
    dtype: NumericType,
    space: MemorySpace = MemorySpace.GM,
    format_value: Farmat = Farmat.Norm,
) -> None:
    """断言 Memory 的基础元信息符合预期。"""

    assert mem.get_shape() == shape_values
    assert mem.get_stride() == stride_values
    assert mem.get_type() is dtype
    assert mem.get_space() is space
    assert mem.get_format() is format_value


rank1_dim = get_random_non_zero_int(1, 8)
rank2_dim0 = get_random_non_zero_int(1, 8)
rank2_dim1 = get_random_non_zero_int(1, 8)
rank4_dim0 = get_random_non_zero_int(1, 8)
rank4_dim2 = get_random_non_zero_int(1, 8)
rank4_dim3 = get_random_non_zero_int(1, 8)

rank3_sym0 = get_random_alpha_string()
rank3_sym1 = get_random_alpha_string()
rank3_sym2 = get_random_alpha_string()
rank4_sym1 = get_random_alpha_string()


# rank-1 纯整数 shape：最后一维默认 stride 固定为 1。
rank1_mem = Memory([rank1_dim], NumericType.Float32)
assert_memory_layout(
    rank1_mem,
    [rank1_dim],
    [1],
    NumericType.Float32,
)

# rank-2 纯整数 shape：默认 stride 为 [dim1, 1]。
rank2_mem = Memory([rank2_dim0, rank2_dim1], NumericType.Int32)
assert_memory_layout(
    rank2_mem,
    [rank2_dim0, rank2_dim1],
    [rank2_dim1, 1],
    NumericType.Int32,
)


# rank-3 纯 symbol shape：默认 stride 保持符号乘法表达式。
rank3_mem = Memory([rank3_sym0, rank3_sym1, rank3_sym2], NumericType.Float32)
assert_memory_layout(
    rank3_mem,
    [rank3_sym0, rank3_sym1, rank3_sym2],
    [
        SymbolDim(rank3_sym1) * SymbolDim(rank3_sym2),
        rank3_sym2,
        1,
    ],
    NumericType.Float32,
)


# rank-4 整数和 symbol 混合 shape：默认 stride 需要正确传播动态表达式。
rank4_mem = Memory(
    [rank4_dim0, rank4_sym1, rank4_dim2, rank4_dim3],
    NumericType.Float32,
    space=MemorySpace.SM,
    format=Farmat.CLast,
)
rank4_stride0 =SymbolDim(rank4_sym1) * SymbolDim(rank4_dim2) * SymbolDim(rank4_dim3)

rank4_stride1 = SymbolDim(rank4_dim2) * SymbolDim(rank4_dim3)
assert_memory_layout(
    rank4_mem,
    [rank4_dim0, rank4_sym1, rank4_dim2, rank4_dim3],
    [rank4_stride0, rank4_stride1, rank4_dim3, 1],
    NumericType.Float32,
    space=MemorySpace.SM,
    format_value=Farmat.CLast,
)


# 默认 dtype：未显式传入 dtype 时，目标行为应默认为 Float32。
default_dtype_mem = Memory([rank2_dim0, rank2_dim1])
assert_memory_layout(
    default_dtype_mem,
    [rank2_dim0, rank2_dim1],
    [rank2_dim1, 1],
    NumericType.Float32,
)


# 非法 stride：整数 shape 下，stride 的 rank 与 shape 不一致时应报错。
try:
    Memory([rank2_dim0, rank2_dim1], NumericType.Float32, stride=[rank2_dim1])
except ValueError:
    pass
else:
    raise AssertionError("expected ValueError for integer-shape stride rank mismatch")


# 非法 stride：symbol shape 下，stride 的 rank 与 shape 不一致时应报错。
try:
    Memory([rank3_sym0, rank3_sym1, rank3_sym2], NumericType.Float32, stride=[rank3_sym1, 1])
except ValueError:
    pass
else:
    raise AssertionError("expected ValueError for symbol-shape stride rank mismatch")
