"""`nn_lowering` expectation 的随机样本辅助。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 为 `expectation/pass/lowing/nn_lowering` 目录下的 expectation 提供统一的随机静态维度、随机符号名、
  随机 element type 与随机 memory space 辅助。
- 目标是让 expectation 用例不再依赖固定的数字或固定符号名，同时仍保持输出合同可比对。

使用示例:
- `from _random_utils import random_static_dims, random_space_attr_ir`
- `dims = random_static_dims(2, min_value=2, max_value=16)`
- `symbols = random_symbol_names(3)`
- `space = random_space_attr_ir()`
- `dtype = random_float_dtype_ir()`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/nn_lowering`](test/pass/nn_lowering)
- 功能实现: [`expectation/pass/lowing/nn_lowering/_random_utils.py`](expectation/pass/lowing/nn_lowering/_random_utils.py)
"""

from __future__ import annotations

from expectation.utils.random_utils import memory_space_ir_name, numeric_type_ir
from expectation.utils.sample_values import (
    get_random_alpha_strings,
    get_random_arithmetic_numeric_type,
    get_random_float_numeric_type,
    get_random_memory_space,
    get_random_numeric_types,
    get_random_non_zero_ints,
)
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType

_ARITHMETIC_DTYPES = (
    NumericType.Int8,
    NumericType.Int16,
    NumericType.Int32,
    NumericType.Int64,
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
)
_FLOAT_DTYPES = (
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
)
_CAST_DTYPES = _ARITHMETIC_DTYPES


def random_static_dims(
    count: int,
    *,
    min_value: int = 2,
    max_value: int = 16,
) -> tuple[int, ...]:
    """返回指定数量的随机正静态维度。"""

    return get_random_non_zero_ints(count, min_value=min_value, max_value=max_value)


def random_symbol_names(
    count: int,
    *,
    max_length: int = 6,
) -> tuple[str, ...]:
    """返回指定数量、互不重复的随机大写符号名。"""

    return get_random_alpha_strings(count, max_length=max_length, unique=True, uppercase=True)


def random_space_name(
    candidates: tuple[MemorySpace, ...] | None = None,
) -> str:
    """返回随机 `#nn.space<...>` 的内部名字。"""

    return memory_space_ir_name(get_random_memory_space(candidates))


def random_space_attr_ir(
    candidates: tuple[MemorySpace, ...] | None = None,
) -> str:
    """返回随机 `#nn.space<...>` 文本。"""

    return f"#nn.space<{random_space_name(candidates)}>"


def random_arithmetic_dtype_ir() -> str:
    """返回随机算术 dtype 的 IR 文本。"""

    return numeric_type_ir(get_random_arithmetic_numeric_type(_ARITHMETIC_DTYPES))


def random_float_dtype_ir() -> str:
    """返回随机浮点 dtype 的 IR 文本。"""

    return numeric_type_ir(get_random_float_numeric_type(_FLOAT_DTYPES))


def random_cast_dtype_pair_irs() -> tuple[str, str]:
    """返回一组不同的可 cast dtype IR 文本。"""

    src, dst = get_random_numeric_types(2, _CAST_DTYPES, unique=True)
    return numeric_type_ir(src), numeric_type_ir(dst)

__all__ = [
    "random_arithmetic_dtype_ir",
    "random_cast_dtype_pair_irs",
    "random_float_dtype_ir",
    "random_space_attr_ir",
    "random_space_name",
    "random_static_dims",
    "random_symbol_names",
]
