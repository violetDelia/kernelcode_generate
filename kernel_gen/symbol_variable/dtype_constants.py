"""dtype constants for symbol_variable.

创建者: 睡觉小分队
最后一次更改: 金铲铲大作战

功能说明:
- 提供常用 dtype 集合常量与 dtype 促销顺序常量，避免各模块重复维护同一组 NumericType。

使用示例:
- from kernel_gen.symbol_variable.dtype_constants import (
    ARITHMETIC_DTYPE_ORDER,
    ARITHMETIC_DTYPE_RANK,
    FLOAT_DTYPES,
    INT_DTYPES,
    NN_FLOAT_DTYPES,
  )
- assert NumericType.Float32 in FLOAT_DTYPES

关联文件:
- spec: spec/symbol_variable/dtype_constants.md
- test: test/symbol_variable/test_dtype_constants.py
- 功能实现: kernel_gen/symbol_variable/dtype_constants.py
"""

from __future__ import annotations

from typing import Final

from kernel_gen.symbol_variable.type import NumericType

__all__ = [
    "ARITHMETIC_DTYPE_ORDER",
    "ARITHMETIC_DTYPE_RANK",
    "FLOAT_DTYPES",
    "INT_DTYPES",
    "NN_FLOAT_DTYPES",
]

ARITHMETIC_DTYPE_ORDER: Final[tuple[NumericType, ...]] = (
    NumericType.Int8,
    NumericType.Uint8,
    NumericType.Int16,
    NumericType.Uint16,
    NumericType.Int32,
    NumericType.Uint32,
    NumericType.Int64,
    NumericType.Uint64,
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
)
ARITHMETIC_DTYPE_RANK: Final[dict[NumericType, int]] = {
    dtype: index for index, dtype in enumerate(ARITHMETIC_DTYPE_ORDER)
}

FLOAT_DTYPES = {
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
}

INT_DTYPES = {
    NumericType.Int8,
    NumericType.Int16,
    NumericType.Int32,
    NumericType.Int64,
    NumericType.Uint8,
    NumericType.Uint16,
    NumericType.Uint32,
    NumericType.Uint64,
}

NN_FLOAT_DTYPES = {
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
}
