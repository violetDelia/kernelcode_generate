"""Expectation random helpers.

创建者: 榕
最后一次更改: 榕

功能说明:
- 提供 expectation 脚本中通用的随机整数生成能力。
- 提供 expectation 脚本中通用的随机非零整数生成能力。
- 提供 expectation 脚本中通用的随机字母字符串生成能力。

使用示例:
- from expectation.utils.random import get_random_int
- from expectation.utils.random import get_random_non_zero_int
- from expectation.utils.random import get_random_alpha_string
- value = get_random_int()
- non_zero = get_random_non_zero_int(-8, 8)
- name = get_random_alpha_string()

关联文件:
- 功能实现: expectation/utils/random.py
"""

from __future__ import annotations

import random
import string


def get_random_int(min_value: int = -1024, max_value: int = 1024) -> int:
    """返回指定闭区间内的随机整数。

    使用示例:
    - get_random_int()
    - get_random_int(0, 10)
    """
    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    return random.randint(min_value, max_value)


def get_random_non_zero_int(min_value: int = -1024, max_value: int = 1024) -> int:
    """返回指定闭区间内的随机非零整数。

    使用示例:
    - get_random_non_zero_int()
    - get_random_non_zero_int(-8, 8)
    """
    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    if min_value == 0 and max_value == 0:
        raise ValueError("range must include at least one non-zero integer")

    while True:
        value = random.randint(min_value, max_value)
        if value != 0:
            return value


def get_random_alpha_string(max_length: int = 10) -> str:
    """返回长度不超过 10 的随机字母字符串。

    字符串长度在 ``[1, max_length]`` 内随机选择，只包含英文字母。

    使用示例:
    - get_random_alpha_string()
    - get_random_alpha_string(6)
    """
    if max_length < 1 or max_length > 10:
        raise ValueError("max_length must be in [1, 10]")

    length = random.randint(1, max_length)
    letters = string.ascii_letters
    return "".join(random.choice(letters) for _ in range(length))


__all__ = [
    "get_random_alpha_string",
    "get_random_int",
    "get_random_non_zero_int",
]
