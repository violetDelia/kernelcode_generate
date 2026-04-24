"""Expectation sample-value type and space helpers.

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 提供 expectation 公共复用的 `NumericType` 与 `MemorySpace` 采样入口。
- 提供批量采样与片上空间采样，收口 DMA、DSL 和 pass expectation 的重复类型选择逻辑。

使用示例:
- `dtype = get_random_arithmetic_numeric_type()`
- `spaces = get_random_memory_spaces(2, unique=True)`
- `onchip = get_random_onchip_memory_space()`

关联文件:
- spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
- test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
- 功能实现: [`expectation/utils/sample_values_support/types.py`](expectation/utils/sample_values_support/types.py)
- 功能实现: [`expectation/utils/sample_values.py`](expectation/utils/sample_values.py)
"""

from __future__ import annotations

from collections.abc import Sequence

from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType

from .core import _choose_random_item, _choose_random_items

_FLOAT_NUMERIC_TYPES = (
    NumericType.Float16,
    NumericType.BFloat16,
    NumericType.Float32,
    NumericType.Float64,
)
_NON_FLOAT_NUMERIC_TYPES = tuple(dtype for dtype in NumericType if dtype not in _FLOAT_NUMERIC_TYPES)
_ARITHMETIC_NUMERIC_TYPES = tuple(dtype for dtype in NumericType if dtype is not NumericType.Bool)
_ONCHIP_MEMORY_SPACES = (
    MemorySpace.SM,
    MemorySpace.LM,
    MemorySpace.TSM,
    MemorySpace.TLM1,
    MemorySpace.TLM2,
    MemorySpace.TLM3,
)


def get_random_numeric_type(
    candidates: Sequence[NumericType] | None = None,
    *,
    exclude: Sequence[NumericType] | None = None,
) -> NumericType:
    """返回一个伪随机 `NumericType`。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 默认从全部 `NumericType` 中采样。
    - 支持通过 `candidates` 或 `exclude` 约束采样范围。

    使用示例:
    - `get_random_numeric_type()`
    - `get_random_numeric_type(exclude=(NumericType.Bool,))`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/types.py`](expectation/utils/sample_values_support/types.py)
    """

    population = tuple(candidates) if candidates is not None else tuple(NumericType)
    return _choose_random_item(population, exclude=exclude)


def get_random_numeric_types(
    count: int,
    candidates: Sequence[NumericType] | None = None,
    *,
    exclude: Sequence[NumericType] | None = None,
    unique: bool = False,
) -> tuple[NumericType, ...]:
    """返回指定数量的伪随机 `NumericType` 样本。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 支持一次选取多个 `NumericType`。
    - `unique=True` 时要求结果互不重复。

    使用示例:
    - `dtypes = get_random_numeric_types(3, unique=True)`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/types.py`](expectation/utils/sample_values_support/types.py)
    """

    population = tuple(candidates) if candidates is not None else tuple(NumericType)
    return _choose_random_items(count, population, exclude=exclude, unique=unique)


def get_random_float_numeric_type(
    candidates: Sequence[NumericType] | None = None,
    *,
    exclude: Sequence[NumericType] | None = None,
) -> NumericType:
    """返回一个伪随机浮点 `NumericType`。"""

    population = tuple(candidates) if candidates is not None else _FLOAT_NUMERIC_TYPES
    return get_random_numeric_type(population, exclude=exclude)


def get_random_float_numeric_types(
    count: int,
    candidates: Sequence[NumericType] | None = None,
    *,
    exclude: Sequence[NumericType] | None = None,
    unique: bool = False,
) -> tuple[NumericType, ...]:
    """返回指定数量的伪随机浮点 `NumericType` 样本。"""

    population = tuple(candidates) if candidates is not None else _FLOAT_NUMERIC_TYPES
    return get_random_numeric_types(count, population, exclude=exclude, unique=unique)


def get_random_non_float_numeric_type(
    candidates: Sequence[NumericType] | None = None,
    *,
    exclude: Sequence[NumericType] | None = None,
) -> NumericType:
    """返回一个伪随机非浮点 `NumericType`。"""

    population = tuple(candidates) if candidates is not None else _NON_FLOAT_NUMERIC_TYPES
    return get_random_numeric_type(population, exclude=exclude)


def get_random_non_float_numeric_types(
    count: int,
    candidates: Sequence[NumericType] | None = None,
    *,
    exclude: Sequence[NumericType] | None = None,
    unique: bool = False,
) -> tuple[NumericType, ...]:
    """返回指定数量的伪随机非浮点 `NumericType` 样本。"""

    population = tuple(candidates) if candidates is not None else _NON_FLOAT_NUMERIC_TYPES
    return get_random_numeric_types(count, population, exclude=exclude, unique=unique)


def get_random_arithmetic_numeric_type(
    candidates: Sequence[NumericType] | None = None,
    *,
    exclude: Sequence[NumericType] | None = None,
) -> NumericType:
    """返回一个伪随机算术 `NumericType`。"""

    population = tuple(candidates) if candidates is not None else _ARITHMETIC_NUMERIC_TYPES
    return get_random_numeric_type(population, exclude=exclude)


def get_random_arithmetic_numeric_types(
    count: int,
    candidates: Sequence[NumericType] | None = None,
    *,
    exclude: Sequence[NumericType] | None = None,
    unique: bool = False,
) -> tuple[NumericType, ...]:
    """返回指定数量的伪随机算术 `NumericType` 样本。"""

    population = tuple(candidates) if candidates is not None else _ARITHMETIC_NUMERIC_TYPES
    return get_random_numeric_types(count, population, exclude=exclude, unique=unique)


def get_random_memory_space(
    candidates: Sequence[MemorySpace] | None = None,
    *,
    exclude: Sequence[MemorySpace] | None = None,
) -> MemorySpace:
    """返回一个伪随机 `MemorySpace`。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 默认从全部 `MemorySpace` 中采样。
    - 支持通过 `candidates` 或 `exclude` 约束采样范围。

    使用示例:
    - `space = get_random_memory_space(exclude=(MemorySpace.GM,))`

    关联文件:
    - spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
    - test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
    - 功能实现: [`expectation/utils/sample_values_support/types.py`](expectation/utils/sample_values_support/types.py)
    """

    population = tuple(candidates) if candidates is not None else tuple(MemorySpace)
    return _choose_random_item(population, exclude=exclude)


def get_random_memory_spaces(
    count: int,
    candidates: Sequence[MemorySpace] | None = None,
    *,
    exclude: Sequence[MemorySpace] | None = None,
    unique: bool = False,
) -> tuple[MemorySpace, ...]:
    """返回指定数量的伪随机 `MemorySpace` 样本。"""

    population = tuple(candidates) if candidates is not None else tuple(MemorySpace)
    return _choose_random_items(count, population, exclude=exclude, unique=unique)


def get_random_onchip_memory_space(
    *,
    exclude: Sequence[MemorySpace] | None = None,
) -> MemorySpace:
    """返回一个随机片上 `MemorySpace`。"""

    return get_random_memory_space(_ONCHIP_MEMORY_SPACES, exclude=exclude)


def get_random_onchip_memory_spaces(
    count: int,
    *,
    exclude: Sequence[MemorySpace] | None = None,
    unique: bool = False,
) -> tuple[MemorySpace, ...]:
    """返回指定数量的随机片上 `MemorySpace` 样本。"""

    return get_random_memory_spaces(count, _ONCHIP_MEMORY_SPACES, exclude=exclude, unique=unique)


def random_dma_space() -> MemorySpace:
    """返回 DMA expectation 可用的随机 `MemorySpace`。"""

    return get_random_memory_space()


__all__ = [
    "get_random_arithmetic_numeric_type",
    "get_random_arithmetic_numeric_types",
    "get_random_float_numeric_type",
    "get_random_float_numeric_types",
    "get_random_memory_space",
    "get_random_memory_spaces",
    "get_random_non_float_numeric_type",
    "get_random_non_float_numeric_types",
    "get_random_numeric_type",
    "get_random_numeric_types",
    "get_random_onchip_memory_space",
    "get_random_onchip_memory_spaces",
    "random_dma_space",
]
