"""Type definitions for symbol variable.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供数值类型与格式枚举，并显式限定导出范围。

使用示例:
- from symbol_variable.type import NumericType, Farmat
- NumericType.Float32
- Farmat.Norm

关联文件:
- spec: spec/symbol_variable/type.md
- test: test/symbol_variable/test_type.py
- 功能实现: symbol_variable/type.py
"""

from __future__ import annotations

from enum import Enum

__all__ = ["NumericType", "Farmat"]


class NumericType(Enum):
    """数值类型枚举。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 提供常用数值类型标识。

    使用示例:
    - NumericType.Float32

    关联文件:
    - spec: spec/symbol_variable/type.md
    - test: test/symbol_variable/test_type.py
    - 功能实现: symbol_variable/type.py
    """

    Int32 = "int32"
    Float32 = "float32"


class Farmat(Enum):
    """格式枚举（按实现命名）。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 约定 c last=NHWC、c not last=NCHW。

    使用示例:
    - Farmat.Norm
    - Farmat.CLast

    关联文件:
    - spec: spec/symbol_variable/type.md
    - test: test/symbol_variable/test_type.py
    - 功能实现: symbol_variable/type.py
    """

    NHWC = "NHWC"
    NCHW = "NCHW"
    Norm = NCHW
    CLast = NHWC
