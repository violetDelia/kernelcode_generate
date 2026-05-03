"""Type definitions for symbol variable.


功能说明:
- 提供数值类型与格式枚举及其公开导出边界。

API 列表:
- `class NumericType(Enum)`
- `class Farmat(Enum)`
- `FLOAT_DTYPES`
- `INT_DTYPES`
- `ARITHMETIC_DTYPE_ORDER`
- `ARITHMETIC_DTYPE_RANK`
- `NN_FLOAT_DTYPES`
- `is_integer_dtype(dtype: NumericType) -> bool`
- `is_float_dtype(dtype: NumericType) -> bool`

使用示例:
- from kernel_gen.symbol_variable.type import NumericType, Farmat
- NumericType.Float32
- NumericType.Int8
- NumericType.Uint8
- NumericType.BFloat16
- Farmat.Norm

关联文件:
- spec: spec/symbol_variable/type.md
- test: test/symbol_variable/test_type.py
- 功能实现: kernel_gen/symbol_variable/type.py
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    "NumericType",
    "Farmat",
    "FLOAT_DTYPES",
    "INT_DTYPES",
    "ARITHMETIC_DTYPE_ORDER",
    "ARITHMETIC_DTYPE_RANK",
    "NN_FLOAT_DTYPES",
    "is_integer_dtype",
    "is_float_dtype",
]


class NumericType(Enum):
    """数值类型枚举。


    功能说明:
    - 提供常用数值类型标识。

    使用示例:
    - NumericType.Float32
    - NumericType.BFloat16

    关联文件:
    - spec: spec/symbol_variable/type.md
    - test: test/symbol_variable/test_type.py
    - 功能实现: kernel_gen/symbol_variable/type.py
    """

    Int8 = "int8"
    Int16 = "int16"
    Int32 = "int32"
    Int64 = "int64"
    Uint8 = "uint8"
    Uint16 = "uint16"
    Uint32 = "uint32"
    Uint64 = "uint64"
    Float16 = "float16"
    BFloat16 = "bf16"
    Float32 = "float32"
    Float64 = "float64"
    Bool = "bool"


class Farmat(Enum):
    """格式枚举（按实现命名）。


    功能说明:
    - 仅公开 Norm 与 CLast 两种布局语义。

    使用示例:
    - Farmat.Norm
    - Farmat.CLast

    关联文件:
    - spec: spec/symbol_variable/type.md
    - test: test/symbol_variable/test_type.py
    - 功能实现: kernel_gen/symbol_variable/type.py
    """

    Norm = "Norm"
    CLast = "CLast"


INT_DTYPES: Final[set[NumericType]] = {
    NumericType.Int8,
    NumericType.Int16,
    NumericType.Int32,
    NumericType.Int64,
    NumericType.Uint8,
    NumericType.Uint16,
    NumericType.Uint32,
    NumericType.Uint64,
}

FLOAT_DTYPES: Final[set[NumericType]] = {
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
}


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

NN_FLOAT_DTYPES: Final[set[NumericType]] = FLOAT_DTYPES


def is_integer_dtype(dtype: NumericType) -> bool:
    """判断 dtype 是否属于公开整数 family。


    功能说明:
    - 只接受 `NumericType` 输入。
    - 覆盖有符号与无符号整数成员。

    使用示例:
    - is_integer_dtype(NumericType.Int32)

    关联文件:
    - spec: spec/symbol_variable/type.md
    - test: test/symbol_variable/test_type.py
    - 功能实现: kernel_gen/symbol_variable/type.py
    """
    if not isinstance(dtype, NumericType):
        raise TypeError("dtype must be NumericType")
    return dtype in INT_DTYPES


def is_float_dtype(dtype: NumericType) -> bool:
    """判断 dtype 是否属于公开浮点 family。


    功能说明:
    - 只接受 `NumericType` 输入。
    - 覆盖 `Float16/BFloat16/Float32/Float64` 四个公开成员。

    使用示例:
    - is_float_dtype(NumericType.Float32)

    关联文件:
    - spec: spec/symbol_variable/type.md
    - test: test/symbol_variable/test_type.py
    - 功能实现: kernel_gen/symbol_variable/type.py
    """
    if not isinstance(dtype, NumericType):
        raise TypeError("dtype must be NumericType")
    return dtype in FLOAT_DTYPES
