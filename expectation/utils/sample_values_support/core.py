"""Expectation sample-value shared random core.

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 提供 `expectation` 公共采样使用的模块级随机源。
- 提供单值与多值候选选择 helper，供标量采样与类型采样模块复用。

使用示例:
- `_choose_random_item((1, 2, 3), exclude=(1,))`
- `_choose_random_items(2, (1, 2, 3), unique=True)`

关联文件:
- spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
- test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
- 功能实现: [`expectation/utils/sample_values_support/core.py`](expectation/utils/sample_values_support/core.py)
- 功能实现: [`expectation/utils/sample_values.py`](expectation/utils/sample_values.py)
"""

from __future__ import annotations

from collections.abc import Sequence
import random
from typing import TypeVar

ChoiceT = TypeVar("ChoiceT")

_RNG = random.Random()


def _filter_population(
    population: Sequence[ChoiceT],
    *,
    exclude: Sequence[ChoiceT] | None = None,
) -> tuple[ChoiceT, ...]:
    """返回应用排除规则后的候选集合。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 将任意 `Sequence` 规范化为元组候选池。
    - 支持按 `exclude` 过滤不允许的候选项。

    使用示例:
    - `_filter_population((1, 2, 3), exclude=(2,))`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/core.py`](expectation/utils/sample_values_support/core.py)
    """

    candidates = tuple(population)
    if exclude:
        excluded = set(exclude)
        candidates = tuple(item for item in candidates if item not in excluded)
    if not candidates:
        raise ValueError("population must contain at least one selectable item")
    return candidates


def _choose_random_item(
    population: Sequence[ChoiceT],
    *,
    exclude: Sequence[ChoiceT] | None = None,
) -> ChoiceT:
    """从候选集合中选择一个随机元素。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 基于模块级随机生成器选择单个元素。
    - 支持通过 `exclude` 过滤不允许的候选项。

    使用示例:
    - `_choose_random_item((1, 2, 3), exclude=(1,))`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/core.py`](expectation/utils/sample_values_support/core.py)
    """

    return _RNG.choice(_filter_population(population, exclude=exclude))


def _choose_random_items(
    count: int,
    population: Sequence[ChoiceT],
    *,
    exclude: Sequence[ChoiceT] | None = None,
    unique: bool = False,
) -> tuple[ChoiceT, ...]:
    """从候选集合中选择指定数量的随机元素。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 支持重复采样与唯一采样两种模式。
    - 当 `unique=True` 时，返回结果中不会出现重复元素。

    使用示例:
    - `_choose_random_items(2, (1, 2, 3), unique=True)`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/core.py`](expectation/utils/sample_values_support/core.py)
    """

    if count < 1:
        raise ValueError("count must be >= 1")

    candidates = _filter_population(population, exclude=exclude)
    if unique:
        if count > len(candidates):
            raise ValueError("unique count exceeds candidate size")
        chosen: list[ChoiceT] = []
        while len(chosen) < count:
            candidate = _RNG.choice(candidates)
            if candidate not in chosen:
                chosen.append(candidate)
        return tuple(chosen)

    return tuple(_RNG.choice(candidates) for _ in range(count))


__all__ = [
    "_RNG",
    "_choose_random_item",
    "_choose_random_items",
    "_filter_population",
]
