"""Type definitions for symbol variable.

创建者: 小李飞刀
最后一次更改: 榕

功能说明:
- 提供数值类型与格式枚举及其公开导出边界。

使用示例:
- from python.symbol_variable.type import NumericType, Farmat
- NumericType.Float32
- NumericType.Int8
- NumericType.Uint8
- NumericType.BFloat16
- Farmat.Norm

关联文件:
- spec: spec/symbol_variable/type.md
- test: test/symbol_variable/test_type.py
- 功能实现: python/symbol_variable/type.py
"""

from __future__ import annotations

from enum import Enum

__all__ = ["NumericType", "Farmat"]


class NumericType(Enum):
    """数值类型枚举。

    创建者: 小李飞刀
    最后一次更改: 榕

    功能说明:
    - 提供常用数值类型标识。

    使用示例:
    - NumericType.Float32
    - NumericType.BFloat16

    关联文件:
    - spec: spec/symbol_variable/type.md
    - test: test/symbol_variable/test_type.py
    - 功能实现: python/symbol_variable/type.py
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


class Farmat(Enum):
    """格式枚举（按实现命名）。

    创建者: 小李飞刀
    最后一次更改: 榕

    功能说明:
    - 约定 c last=NHWC、c not last=NCHW。

    使用示例:
    - Farmat.Norm
    - Farmat.CLast

    关联文件:
    - spec: spec/symbol_variable/type.md
    - test: test/symbol_variable/test_type.py
    - 功能实现: python/symbol_variable/type.py
    """

    NHWC = "NHWC"
    NCHW = "NCHW"
    Norm = NCHW
    CLast = NHWC
