"""SymbolDim expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 描述 SymbolDim 在静态整数、动态符号以及混合表达式上的目标行为。
- 补充加、减、乘、除、整除的期望结果。

使用示例:
- python expectation/symbol_variable/symbol_dim.py

关联文件:
- spec: spec/symbol_variable/symbol_dim.md
- test: test/symbol_variable/test_symbol_dim.py
- 功能实现: kernel_gen/symbol_variable/symbol_dim.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.random import (  # noqa: E402
    get_random_alpha_string,
    get_random_int,
    get_random_non_zero_int,
)
from kernel_gen.symbol_variable.symbol_dim import SymbolDim  # noqa: E402


random1 = get_random_non_zero_int()
random2 = get_random_non_zero_int()
random3 = get_random_non_zero_int()

s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
s3 = get_random_alpha_string()

random1_dim = SymbolDim(random1)
random2_dim = SymbolDim(random2)
random3_dim = SymbolDim(random3)
s1_dim = SymbolDim(s1)
s2_dim = SymbolDim(s2)
s3_dim = SymbolDim(s3)


# 静态整数维度仍应被识别为非动态值。
random_static_dim = SymbolDim(get_random_int())
assert random_static_dim.is_dynamic() is False


# 加法：覆盖静态+静态、静态+符号、符号链式求和。
r1_plus_r2 = random1_dim + random2_dim
assert r1_plus_r2.is_dynamic() is False
assert r1_plus_r2.get_value() == random1 + random2

r1_plus_s1 = random1_dim + s1_dim
assert r1_plus_s1.is_dynamic() is True
assert r1_plus_s1.get_value() == (SymbolDim(random1) + SymbolDim(s1)).get_value()

s1_plus_s2_plus_s3 = s1_dim + s2_dim + s3_dim
assert s1_plus_s2_plus_s3.is_dynamic() is True
assert s1_plus_s2_plus_s3 == SymbolDim(s1) + SymbolDim(s2) + SymbolDim(s3)


# 减法：覆盖静态差值、静态与符号混合、符号链式相减。
r1_minus_r2 = random1_dim - random2_dim
assert r1_minus_r2.is_dynamic() is False
assert r1_minus_r2.get_value() == random1 - random2

r1_minus_s1 = random1_dim - s1_dim
assert r1_minus_s1.is_dynamic() is True
assert r1_minus_s1.get_value() == (SymbolDim(s1 - SymbolDim(-random1))).get_value()

s1_minus_s2_minus_s3 = s1_dim - s2_dim - s3_dim
assert s1_minus_s2_minus_s3.is_dynamic() is True
assert s1_minus_s2_minus_s3 == SymbolDim(s1) - SymbolDim(s3) - SymbolDim(s2)


# 乘法：结果应在纯整数时保持静态，含符号时转为动态表达式。
r1_mul_r2 = random1_dim * random2_dim
assert r1_mul_r2.is_dynamic() is False
assert r1_mul_r2.get_value() == random1 * random2

r1_mul_s1 = random1_dim * s1_dim
assert r1_mul_s1.is_dynamic() is True
assert r1_mul_s1.get_value() == (SymbolDim(s1) * SymbolDim(random1)).get_value()

s1_mul_s2_mul_s3 = s1_dim * s2_dim * s3_dim
assert s1_mul_s2_mul_s3.is_dynamic() is True
assert s1_mul_s2_mul_s3 == SymbolDim(s2) * SymbolDim(s1) * SymbolDim(s3)


# 除法：验证静态结果、符号结果以及链式表达式的结合顺序。
r1_div_r2 = random1_dim / random2_dim
assert r1_div_r2.is_dynamic() is False
assert r1_div_r2.get_value() == random1 / random2

r1_div_s1 = random1_dim / s1_dim
assert r1_div_s1.is_dynamic() is True
assert r1_div_s1.get_value() == (SymbolDim(random1) / SymbolDim(s1)).get_value()

s1_div_s2_div_r3 = s1_dim / s2_dim / random3_dim
assert s1_div_s2_div_r3.is_dynamic() is True
assert s1_div_s2_div_r3 != SymbolDim(s1) / SymbolDim(random3) / SymbolDim(s2)


# 整除：覆盖纯整数整除与符号整除的目标行为。
r1_floordiv_r2 = random1_dim // random2_dim
assert r1_floordiv_r2.is_dynamic() is False
assert r1_floordiv_r2.get_value() == random1 // random2

r1_floordiv_s1 = random1_dim // s1_dim
assert r1_floordiv_s1.is_dynamic() is True
assert r1_floordiv_s1.get_value() == (SymbolDim(random1) // SymbolDim(s1)).get_value()

s1_floordiv_s2_floordiv_r3 = s1_dim // s2_dim // random3_dim
assert s1_floordiv_s2_floordiv_r3.is_dynamic() is True
assert s1_floordiv_s2_floordiv_r3 == SymbolDim(s1) // SymbolDim(s2) // SymbolDim(
    random3
)
assert s1_floordiv_s2_floordiv_r3 != SymbolDim(s1) // SymbolDim(random3) // SymbolDim(
    s2
)


# 混合计算：同时覆盖加减乘除优先级与动态性传播。
mixed_expr = random1_dim + s1_dim - random2_dim * s2_dim / random3_dim
assert mixed_expr.is_dynamic() is True
assert (
    mixed_expr.get_value()
    == (
        SymbolDim(random1)
        + SymbolDim(s1)
        - SymbolDim(random2) * SymbolDim(s2) / SymbolDim(random3)
    ).get_value()
)


# 浮点限制：不支持浮点初始化，也不支持与浮点数混合计算。
try:
    SymbolDim(1.5)
except NotImplementedError:
    pass
else:
    raise AssertionError("expected NotImplementedError for float constructor input")

for float_value in [1.5, -2.25, 0.5]:
    try:
        _ = random1_dim + float_value
    except NotImplementedError:
        pass
    else:
        raise AssertionError("expected NotImplementedError for float add operand")

    try:
        _ = random1_dim - float_value
    except NotImplementedError:
        pass
    else:
        raise AssertionError("expected NotImplementedError for float sub operand")

    try:
        _ = random1_dim * float_value
    except NotImplementedError:
        pass
    else:
        raise AssertionError("expected NotImplementedError for float mul operand")

    try:
        _ = random1_dim / float_value
    except NotImplementedError:
        pass
    else:
        raise AssertionError("expected NotImplementedError for float div operand")

    try:
        _ = random1_dim // float_value
    except NotImplementedError:
        pass
    else:
        raise AssertionError("expected NotImplementedError for float floordiv operand")
