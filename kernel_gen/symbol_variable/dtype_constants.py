"""dtype constants for symbol_variable.

创建者: 睡觉小分队
最后一次更改: 榕

功能说明:
- 兼容导出 `kernel_gen.symbol_variable.type` 中的 dtype family 与 dtype promotion 常量。
- 本文件不再自维护任何 dtype 常量；新代码应直接从 `kernel_gen.symbol_variable.type` 导入。

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

from kernel_gen.symbol_variable.type import (
    ARITHMETIC_DTYPE_ORDER,
    ARITHMETIC_DTYPE_RANK,
    FLOAT_DTYPES,
    INT_DTYPES,
    NN_FLOAT_DTYPES,
)

__all__ = [
    "ARITHMETIC_DTYPE_ORDER",
    "ARITHMETIC_DTYPE_RANK",
    "FLOAT_DTYPES",
    "INT_DTYPES",
    "NN_FLOAT_DTYPES",
]
