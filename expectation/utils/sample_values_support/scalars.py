"""Expectation sample-value scalar helpers.

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 提供 expectation 公共复用的随机整数、随机非零整数与随机字母字符串采样。
- 提供批量采样入口，减少 `_random_utils` 和 family helper 内的重复逻辑。

使用示例:
- `get_random_non_zero_int(2, 8)`
- `get_random_alpha_strings(3, max_length=6, unique=True, uppercase=True)`

关联文件:
- spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
- test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
- 功能实现: [`expectation/utils/sample_values_support/scalars.py`](expectation/utils/sample_values_support/scalars.py)
- 功能实现: [`expectation/utils/sample_values.py`](expectation/utils/sample_values.py)
"""

from __future__ import annotations

import string

from .core import _RNG, _choose_random_items


def get_random_int(min_value: int = -1024, max_value: int = 1024) -> int:
    """返回指定闭区间内的随机整数。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 使用共享随机源在 `[min_value, max_value]` 闭区间内采样。
    - 适用于 expectation 中的普通整数随机样本。

    使用示例:
    - `value = get_random_int(-8, 8)`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/scalars.py`](expectation/utils/sample_values_support/scalars.py)
    """

    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    return _RNG.randint(min_value, max_value)


def get_random_ints(
    count: int,
    *,
    min_value: int = -1024,
    max_value: int = 1024,
    unique: bool = False,
) -> tuple[int, ...]:
    """返回指定数量的随机整数样本。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 支持一次生成多个整数样本。
    - `unique=True` 时要求结果互不重复。

    使用示例:
    - `values = get_random_ints(3, min_value=1, max_value=8, unique=True)`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/scalars.py`](expectation/utils/sample_values_support/scalars.py)
    """

    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    population = tuple(range(min_value, max_value + 1))
    return _choose_random_items(count, population, unique=unique)


def get_random_non_zero_int(min_value: int = -1024, max_value: int = 1024) -> int:
    """返回指定闭区间内的随机非零整数。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 使用共享随机源在闭区间内反复采样，直到命中非零值。
    - 适用于 shape、stride、步长等不能为零的 expectation 参数。

    使用示例:
    - `step = get_random_non_zero_int(1, 8)`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/scalars.py`](expectation/utils/sample_values_support/scalars.py)
    """

    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    if min_value == 0 and max_value == 0:
        raise ValueError("range must include at least one non-zero integer")

    while True:
        value = _RNG.randint(min_value, max_value)
        if value != 0:
            return value


def get_random_non_zero_ints(
    count: int,
    *,
    min_value: int = -1024,
    max_value: int = 1024,
    unique: bool = False,
) -> tuple[int, ...]:
    """返回指定数量的随机非零整数样本。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 支持一次生成多个非零整数样本。
    - `unique=True` 时要求结果互不重复。

    使用示例:
    - `dims = get_random_non_zero_ints(2, min_value=2, max_value=16)`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/scalars.py`](expectation/utils/sample_values_support/scalars.py)
    """

    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    population = tuple(value for value in range(min_value, max_value + 1) if value != 0)
    if not population:
        raise ValueError("range must include at least one non-zero integer")
    return _choose_random_items(count, population, unique=unique)


def get_random_alpha_string(max_length: int = 10, *, uppercase: bool = False) -> str:
    """返回长度不超过 `max_length` 的随机字母字符串。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 从英文字母集合中生成随机字符串。
    - `uppercase=True` 时结果统一转为大写。

    使用示例:
    - `name = get_random_alpha_string(6, uppercase=True)`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/scalars.py`](expectation/utils/sample_values_support/scalars.py)
    """

    if max_length < 1 or max_length > 10:
        raise ValueError("max_length must be in [1, 10]")

    length = _RNG.randint(1, max_length)
    letters = string.ascii_letters
    value = "".join(_RNG.choice(letters) for _ in range(length))
    return value.upper() if uppercase else value


def get_random_alpha_strings(
    count: int,
    *,
    max_length: int = 10,
    unique: bool = False,
    uppercase: bool = False,
) -> tuple[str, ...]:
    """返回指定数量的随机字母字符串样本。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 支持一次生成多个随机名字/符号名。
    - `unique=True` 时要求结果互不重复。
    - `uppercase=True` 时结果统一转为大写。

    使用示例:
    - `symbols = get_random_alpha_strings(3, max_length=6, unique=True, uppercase=True)`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/scalars.py`](expectation/utils/sample_values_support/scalars.py)
    """

    if count < 1:
        raise ValueError("count must be >= 1")

    values: list[str] = []
    while len(values) < count:
        candidate = get_random_alpha_string(max_length, uppercase=uppercase)
        if not unique or candidate not in values:
            values.append(candidate)
    return tuple(values)


__all__ = [
    "get_random_alpha_string",
    "get_random_alpha_strings",
    "get_random_int",
    "get_random_ints",
    "get_random_non_zero_int",
    "get_random_non_zero_ints",
]
